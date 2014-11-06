import os
import fixtures
from keystoneclient.v2_0 import client as ksclient
from vnc_api.vnc_api import *
import uuid
import fixtures

from quantum_test import *
from vnc_api_test import *
from contrail_fixtures import *
from common.connections import ContrailConnections
from tcutils.util import retry
from time import sleep
from keystoneclient import exceptions as ks_exceptions
from tcutils.util import get_dashed_uuid


class ProjectFixture(fixtures.Fixture):

    def __init__(self, vnc_lib_h, connections, project_name=None,
                 username=None, password=None, role='admin', scale= False):
        self.inputs = connections.inputs
        if not project_name:
            project_name = self.inputs.stack_tenant
        self.vnc_lib_h = vnc_lib_h
        self.connections = connections
        self.project_name = project_name
        self.project_obj = None
        self.domain_name = 'default-domain'
        self.already_present = False
        self.logger = connections.inputs.logger
        self.project_fq_name = [self.domain_name, self.project_name]
        self.username = username
        self.password = password
        self.role = role
        self.tenant_dict = {}
        self.user_dict = {}
        self._create_user_set = {}
        insecure = bool(os.getenv('OS_INSECURE',True))
        if not self.inputs.ha_setup:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        else:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        self.kc = ksclient.Client(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name,
            auth_url=self.auth_url,
            insecure=insecure)
        self.project_connections = None
        self.api_server_inspects = self.connections.api_server_inspects
        self.verify_is_run = False
        self.scale = scale
    # end __init__

    def _create_project(self):
        project = Project(self.project_name)
        self.vnc_lib_h.project_create(project)
        project = self.vnc_lib_h.project_read(project.get_fq_name())
        self.logger.info('Created Project  %s ' %
                         (str(project.get_fq_name())))
        ipam = NetworkIpam('default-network-ipam', project, IpamType("dhcp"))
        self.vnc_lib_h.network_ipam_create(ipam)
        self.logger.info('Created network ipam')
   # end _create_project

    def _delete_project(self):
        self.vnc_lib_h.project_delete(fq_name=self.project_fq_name)
    # end _delete_project

    def _create_project_keystone(self):
        if self.project_name == self.inputs.stack_tenant:
            try:
                ks_project = self.kc.tenants.find(name=self.project_name)
                if ks_project:
                    self.already_present = True
                    self.project_id = get_dashed_uuid(ks_project.id)
                    self.logger.debug(
                        'Project %s already present.Not creating it' %
                        self.project_fq_name)
            except ks_exceptions.NotFound, e:
                self.logger.info('Project %s not found' % (
                    self.project_name))
                raise e
            self.project_obj = self.vnc_lib_h.project_read(id=self.project_id)
            self.uuid = self.project_id
            return self

        # create project using keystone
        self.logger.info('Proceed with creation of new project.')
        self.ks_project_id = self.kc.tenants.create(self.project_name).id
        self.logger.info('Created Project:%s, ID : %s ' % (self.project_name,
                                                           self.ks_project_id))
        self.project_id = get_dashed_uuid(self.ks_project_id)
        self.tenant_dict = dict((tenant.name, tenant)
                                for tenant in self.kc.tenants.list())
    # end _create_project_keystone

    def _delete_project_keystone(self):
        self.logger.info('Deleting Project %s' % self.project_fq_name)
        try:
            self.kc.tenants.delete(self.tenant_dict[self.project_name])
        except ks_exceptions.ClientException, e:
            # TODO Remove this workaround 
            if 'Unable to add token to revocation list' in str(e):
                self.logger.warn('Exception %s while deleting project' % (
                    str(e)))
    # end _delete_project

    def _reauthenticate_keystone(self):
        self.kc = ksclient.Client(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name,
            auth_url=self.auth_url)
    # end _reauthenticate_keystone

    def setUp(self):
        super(ProjectFixture, self).setUp()
        if self.scale:
            self._create_project_keystone()
        else:
            try:
                ks_project = self.kc.tenants.find(name=self.project_name)
                if ks_project:
                    self.already_present = True
                    self.project_id = get_dashed_uuid(ks_project.id)
                    self.logger.debug(
                        'Project %s already present.Not creating it' %
                        self.project_fq_name)
            except ks_exceptions.NotFound, e:
                self.logger.info('Project %s not found, creating it' % (
                    self.project_name))
                self._create_project_keystone()
                time.sleep(2)
        self.project_obj = self.vnc_lib_h.project_read(id=self.project_id)
        self.uuid = self.project_id
    # end setUp

    def getObj(self):
        return self.project_obj

    def cleanUp(self):
        super(ProjectFixture, self).cleanUp()
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
            self._reauthenticate_keystone()
            self._delete_project_keystone()
            if self.verify_is_run:
                assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping the deletion of Project %s' %
                              self.project_fq_name)

    # end cleanUp

    @retry(delay=2, tries=10)
    def check_no_project_references(self):
        vnc_project_obj = self.vnc_lib_h.project_read(id=self.project_id)
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

    def get_from_api_server(self):
        self.project_obj = self.vnc_lib_h.project_read(
            fq_name=self.project_fq_name)
        return self.project_obj

    @retry(delay=2, tries=10)
    def check_for_VN_in_api(self):
        self.project_obj = self.vnc_lib_h.project_read(
	    fq_name=self.project_fq_name)
        has_vns = self.project_obj.get_virtual_networks()
        if has_vns:
            self.logger.info("Following VNs exist in project: %s" %has_vns)
            return False
        else:
            self.logger.info("Don't see any VNs in the project %s" %self.project_fq_name)
            return True

    def get_project_connections(self, username=None, password=None):
        if not username:
            username = self.username or self.inputs.stack_user
        if not password:
            password = self.password or self.inputs.stack_password
        if not self.project_connections:
            self.project_connections = ContrailConnections(
                inputs=self.inputs,
                logger=self.logger,
                project_name=self.project_name,
                username=username,
                password=password)
        return self.project_connections
    # end get_project_connections

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
        result = True
        for api_s_inspect in self.api_server_inspects.values():
            cs_project_obj = api_s_inspect.get_cs_project(
                self.domain_name,
                self.project_name)
            if not cs_project_obj:
                self.logger.warn('Project %s not found in API Server %s'
                                 ' ' % (self.project_name, api_s_inspect._ip))
                result &= False
                return result
            if cs_project_obj['project']['uuid'] != self.project_id:
                self.logger.warn('Project id %s got from API Server is'
                                 ' not matching expected ID %s' % (
                                     cs_project_obj['project']['uuid'], self. project_id))
                result &= False
        if result:
            self.logger.info('Verification of project %s in API Server %s'
                             ' passed ' % (self.project_name, api_s_inspect._ip))
        return result
    # end verify_project_in_api_server

    @retry(delay=5, tries=12)
    def verify_project_not_in_api_server(self):
        result = True
        for api_s_inspect in self.api_server_inspects.values():
            cs_project_obj = api_s_inspect.get_cs_project(
                self.domain_name,
                self.project_name)
            self.logger.info("Check for project %s after deletion, got cs_project_obj %s" %
                (self.project_name, cs_project_obj))
            if cs_project_obj:
                self.logger.warn('Project %s is still found in API Server %s'
                                 'with ID %s ' % (self.project_name, api_s_inspect._ip,
                                                  cs_project_obj['project']['uuid']))
                result &= False
        if result:
            self.logger.info('Verification of project %s removal in API Server '
                             ' %s passed ' % (self.project_name, api_s_inspect._ip))
        return result
    # end verify_project_not_in_api_server

    def set_sec_group_for_allow_all(self, project_name, sg_name):
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_2
                  },
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

    def verify_on_cleanup(self):
        result = True
        if not self.verify_project_not_in_api_server():
            result &= False
            self.logger.error('Project %s is still present in API Server' % (
                self.project_name))
        return result
    # end verify_on_cleanup
# end ProjectFixture
