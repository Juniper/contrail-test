import os
import fixtures
from vnc_api.vnc_api import *
import uuid
import fixtures

from quantum_test import *
from vnc_api_test import *
from contrail_fixtures import *
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.util import retry
from time import sleep
from openstack import OpenstackAuth
from vcenter import VcenterAuth


class ProjectFixture(fixtures.Fixture):

    def __init__(self, connections, auth=None, project_name=None,
                 username=None, password=None, role='admin',
                 domain_name=None, uuid=None):
        self.inputs = connections.inputs
        self.vnc_lib_h = connections.get_vnc_lib_h()
        self.logger = connections.logger
        self.connections = connections
        self.auth = auth
        self.project_name = project_name or self.inputs.stack_tenant
        self.domain_name = domain_name or self.connections.domain_name
        self.domain_id = self.connections.domain_id or 'default'
        self.uuid = uuid
        self.project_obj = None
        self.already_present = False
        self.project_fq_name = [self.domain_name, self.project_name]
        self.project_username = self.username = username
        self.project_user_password = self.password = password
        self.role = role
        self.user_dict = {}
        self._create_user_set = {}
        self.project_connections = dict()
        self.project_inputs = dict()
        self.api_server_inspects = self.connections.api_server_inspects
        self.verify_is_run = False
        if not self.auth:
            if self.inputs.orchestrator == 'openstack':
                
                if self.inputs.domain_isolation:
                    self.auth=OpenstackAuth(self.username, self.password,
                           self.project_name, self.inputs, 
                           self.logger,domain_name=self.domain_name)
                else:
                    self.auth = OpenstackAuth(self.inputs.admin_username,
                                    self.inputs.admin_password,
                                    self.inputs.admin_tenant, self.inputs, self.logger,
                                    domain_name=self.inputs.admin_domain)
            else: # vcenter
                self.auth = VcenterAuth(self.inputs.admin_username,
                              self.inputs.admin_password,
                              self.inputs.admin_tenant, self.inputs)
    # end __init__

    def read(self):
        if self.uuid:
            self.project_obj = self.vnc_lib_h.project_read(id=self.uuid)
            self.project_name = self.project_obj.name
            self.project_fq_name = self.project_obj.get_fq_name()
            self.already_present = True

    def _create_project(self):
        self.uuid = self.auth.create_project(self.project_name, self.domain_name)
        self.project_obj = self.vnc_lib_h.project_read(id=self.uuid)
        self.logger.info('Created Project:%s, ID : %s ' % (self.project_name,
                                                           self.uuid))
    # end _create_project

    def _delete_project(self):
        self.auth.delete_project(self.project_name)
        self.logger.info('Deleted project: %s, ID : %s ' % (self.project_name,
                                                            self.uuid))
    # end _delete_project

    def setUp(self):
        super(ProjectFixture, self).setUp()
        self.create()

    def create(self):
        self.uuid = self.uuid or self.auth.get_project_id(self.project_name, self.domain_id)
        if self.uuid:
            self.read()
            self.logger.info(
                    'Using existing project %s(%s)'%(
                    self.project_fq_name, self.uuid))
        elif self.project_name == self.inputs.stack_tenant:
             raise Exception('Project %s not found' % (self.project_name))
        else:
            self.logger.info('Project %s not found, creating it' % (
                self.project_name))
            self._create_project()
#            time.sleep(2)

    def get_uuid(self):
        return self.uuid

    def get_fq_name(self):
        return self.project_fq_name

    def getObj(self):
        return self.project_obj

    def cleanUp(self):
        super(ProjectFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify projects in case of vcenter')
            return
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if not self.check_no_project_references():
                self.logger.warn('One or more references still present' 
                    ', will not delete the project %s' % (self.project_name))
                return
            self.auth.reauth()
            self._delete_project()
            if self.verify_is_run or verify:
                assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping the deletion of Project %s' %
                              self.project_fq_name)

    # end cleanUp

    @retry(delay=2, tries=30)
    def check_no_project_references(self):
        vnc_project_obj = self.vnc_lib_h.project_read(id=self.uuid)
        vns = vnc_project_obj.get_virtual_networks()
        if vns:
            self.logger.warn('Project %s still has VNs %s before deletion' %(
                self.project_name, vns))
            return False
        vmis = vnc_project_obj.get_virtual_machine_interfaces()
        if vmis:
            self.logger.warn('Project %s still has VMIs %s before deletion' %(
                self.project_name, vmis))
            return False
        sgs = vnc_project_obj.get_security_groups()
        if len(sgs) > 1:
            self.logger.warn('Project %s still has SGs %s before deletion' %(
                self.project_name, sgs))
            return False
        return True
    # end check_no_project_references

    def get_project_connections(self, username=None, password=None):
        username = username or self.project_username or self.inputs.stack_user
        password = password or self.project_user_password or \
            self.inputs.stack_password
        inputs = self.get_inputs(username=username, password=password)
        if username not in self.project_connections:
            self.project_connections[username] = ContrailConnections(
                inputs=inputs,
                logger=self.logger,
                project_name=self.project_name,
                username=username,
                password=password,
                domain_name=self.domain_name)
        return self.project_connections[username]
    # end get_project_connections

    def get_inputs(self, username=None, password=None):
        username = username or self.project_username or self.inputs.stack_user
        password = password or self.project_user_password or self.inputs.stack_password
        if username not in self.project_inputs:
            self.project_inputs[username] = ContrailTestInit(self.inputs.ini_file,
                 stack_user=username,
                 stack_password=password,
                 stack_tenant=self.project_name,
                 logger=self.logger)
        return self.project_inputs[username]

    def verify_on_setup(self):
        result = True
        if not self.verify_project_in_api_server():
            result &= False
            self.logger.error('Verification of project %s in APIServer '
                              'failed!! ' % (self.project_name))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    @retry(delay=2, tries=6)
    def verify_project_in_api_server(self):
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify projects in case of vcenter')
            return True
        result = True
        for cfgm_ip in self.inputs.cfgm_ips:
            api_s_inspect = self.api_server_inspects[cfgm_ip]
            cs_project_obj = api_s_inspect.get_cs_project(
                self.domain_name,
                self.project_name)
            if not cs_project_obj:
                self.logger.debug('Project %s not found in API Server %s'
                                 ' ' % (self.project_name, api_s_inspect._ip))
                result &= False
                return result
            if cs_project_obj['project']['uuid'] != self.uuid:
                self.logger.warn('Project id %s got from API Server is'
                                 ' not matching expected ID %s' % (
                                     cs_project_obj['project']['uuid'], self.uuid))
                result &= False
        if result:
            self.logger.info('Verification of project %s in API Server %s'
                             ' passed ' % (self.project_name, api_s_inspect._ip))
        return result
    # end verify_project_in_api_server

    @retry(delay=10, tries=12)
    def verify_project_not_in_api_server(self):
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify projects in case of vcenter')
            return True
        result = True
        for cfgm_ip in self.inputs.cfgm_ips:
            api_s_inspect = self.api_server_inspects[cfgm_ip]
            cs_project_obj = api_s_inspect.get_cs_project(
                self.domain_name,
                self.project_name)
            self.logger.info("Check for project %s after deletion, got cs_project_obj %s" %
                (self.project_name, cs_project_obj))
            if cs_project_obj:
                self.logger.debug('Project %s is still found in API Server %s'
                                 'with ID %s ' % (self.project_name, api_s_inspect._ip,
                                                  cs_project_obj['project']['uuid']))
                result &= False
        if result:
            self.logger.info('Verification of project %s removal in API Server '
                             ' %s passed ' % (self.project_name, api_s_inspect._ip))
        return result
    # end verify_project_not_in_api_server

    def set_sec_group_for_allow_all(self, project_name=None, sg_name='default'):
        project_name = project_name or self.project_name
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        self.update_sec_group(project_name, sg_name, rule1)
    # end set_sec_group_for_allow_all

    def update_sec_group(self, project_name, sec_group_name, rules):
        def_sec_grp = self.vnc_lib_h.security_group_read(
            fq_name=[u'default-domain', project_name, sec_group_name])
        try:
            old_rules = def_sec_grp.get_security_group_entries(
            ).get_policy_rule()
        except AttributeError:
            old_rules = []
        self.logger.info(
            "Adding rules to the %s security group in Project %s" %
            (sec_group_name, project_name))
        self.set_sec_group(project_name, sec_group_name, rules)
        self.addCleanup(self.set_sec_group, project_name,
                        sec_group_name, old_rules)

    def set_sec_group(self, project_name, sec_group_name, rules):
        rule_list = PolicyEntriesType(policy_rule=rules)
        project_fq_name = [u'default-domain', project_name]
        sg_fq_name = [u'default-domain', project_name, sec_group_name]
        project = self.vnc_lib_h.project_read(fq_name=project_fq_name)
        def_sec_grp = self.vnc_lib_h.security_group_read(fq_name=sg_fq_name)
        def_sec_grp = SecurityGroup(
            name=sec_group_name, parent_obj=project, security_group_entries=rule_list)
        def_sec_grp.set_security_group_entries(rule_list)
        self.vnc_lib_h.security_group_update(def_sec_grp)

    @retry(delay=2, tries=10)
    def verify_on_cleanup(self):
        result = True
        if not self.verify_project_not_in_api_server():
            result &= False
            self.logger.error('Project %s is still present in API Server' % (
                self.project_name))
        return result
    # end verify_on_cleanup

    def set_user_creds(self, username, password):
        '''Set a user,password who is allowed to login to this project
        '''
        self.project_username = username
        self.project_user_password = password
    # end set_user_creds
# end ProjectFixture
