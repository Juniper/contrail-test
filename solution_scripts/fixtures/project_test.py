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
from security_group import SecurityGroupFixture,get_secgrp_id_from_name


class ProjectFixture(fixtures.Fixture):
    def __init__(self, connections, project_name=None,
                 username=None, password=None, role='admin',
                 domain_name=None, uuid=None):
        self.inputs = connections.inputs
        if not project_name:
            project_name = self.inputs.stack_tenant
        self.connections = connections
        self.project_name = project_name
        self.domain_name = domain_name or self.inputs.domain_name
        self.logger = connections.inputs.logger
        self.username = username or self.inputs.stack_user
        self.password = password or self.inputs.stack_password
        self.role = role
        self.user_dict = {}
        self._create_user_set = {}
        self.auth = self.connections.get_auth_h()
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.already_present = False
        self.verify_is_run = False
        self.project_fq_name = [self.domain_name, self.project_name]
        if uuid:
            self.project_obj = self.vnc_lib_h.project_read(id=uuid)
            self.project_name = self.project_obj.name
            self.project_fq_name = self.project_obj.get_fq_name()
            self.uuid = uuid
    # end __init__

    def _create_project(self):
        if self.project_name == self.inputs.stack_tenant:
            self.uuid = self.auth.get_project_id(self.domain_name,
                                                 self.project_name)
            if not self.uuid:
                self.logger.info('Project %s not found' % (
                    self.project_name))
                raise Exception('Project %s not found' % (
                    self.project_name))

            self.already_present = True
            self.logger.debug(
                        'Project %s already present.Not creating it' %
                        self.project_fq_name)
            self.project_obj = self.vnc_lib_h.project_read(id=self.uuid)
            return

        self.connections.inputs.domain_name = self.domain_name
        self.connections.project_name = self.project_name

        self.logger.info('Proceed with creation of new project.')
        #if self.domain_name:
        #   try:
        #     dom_obj   = self.connections.vnc_lib.domain_read(fq_name=[self.domain_name])
        #   except:
        #d_obj     = Domain(self.domain_name)
        #     d_obj.set_domain_limits(gen.resource_xsd.DomainLimitsType.populate())
        #     d_obj.set_id_perms(gen.resource_xsd.IdPermsType.populate())
        #     d_obj.set_perms2(gen.resource_xsd.PermType2.populate())

        #domain_id = self.connections.vnc_lib.domain_create(d_obj)
        #sys.exit()
        #dom_obj   = self.connections.vnc_lib.domain_read(id=domain_id)
        #if self.domain_name:
        #pobj = Project(self.project_name,parent_obj=dom_obj)
        #else:
        #   pobj = Project(self.project_name)
        #pobj = Project(self.project_name)
        #self.uuid = self.connections.vnc_lib.project_create(pobj) 
        self.uuid = self.auth.create_project(self.project_name)
        self.logger.info('Created Project:%s, ID : %s ' % (self.project_name,
                                                           self.uuid))
    # end _create_project

    def _delete_project(self):
        self.logger.info('Deleting Project %s' % self.project_fq_name)
        self.auth.delete_project(self.project_name)
    # end _delete_project

    def setUp(self):
        super(ProjectFixture, self).setUp()
        self._create()

    def _create(self):
        self.uuid = self.auth.get_project_id(self.domain_name,
                                             self.project_name)
        if self.uuid:
            self.already_present = True
            self.logger.debug(
                    'Project %s already present.Not creating it' %
                    self.project_fq_name)
        else:
            self.logger.info('Project %s not found, creating it' % (
                self.project_name))
            self._create_project()
            time.sleep(2)
        self.project_obj = self.vnc_lib_h.project_read(id=self.uuid)
    # end setUp

    def get_uuid(self):
        return self.uuid

    def get_fq_name(self):
        return self.project_fq_name

    def getObj(self):
        return getattr(self, 'project_obj', None)

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

    @retry(delay=2, tries=10)
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
        if sgs and len(sgs) > 1:
            self.logger.warn('Project %s still has SGs %s before deletion' %(
                self.project_name, sgs))
            return False
        return True
    # end check_no_project_references

    def get_project_inputs(self, username=None, password=None):
        if not username:
            username = self.username
        if not password:
            password = self.password
        self.project_inputs= ContrailTestInit(self.inputs.ini_file,
                                     stack_user=username,
                                     stack_password=password,
                                     project_fq_name=['default-domain',self.project_name],
                                     logger = self.logger)
        self.project_inputs.setUp()
        return self.project_inputs

    def get_project_connections(self, username=None, password=None):
        if not username:
            username = self.username
        if not password:
            password = self.password
        project_inputs = self.get_project_inputs()
        if not getattr(self, 'project_connections', None):
            self.project_connections = ContrailConnections(
                inputs=project_inputs,
                logger=project_inputs.logger,
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
        if self.inputs.orchestrator == 'vcenter':
            self.logger.debug('No need to verify projects in case of vcenter')
            return True
        result = True
        api_server_inspect_handles = self.connections.get_api_server_inspect_handles()
        for api_s_inspect in api_server_inspect_handles.values():
            cs_project_obj = api_s_inspect.get_cs_project(self.domain_name,
                                                          self.project_name)
            if not cs_project_obj:
                self.logger.warn('Project %s not found in API Server %s'
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
        api_server_inspect_handles = self.connections.get_api_server_inspect_handles()
        for api_s_inspect in api_server_inspect_handles.values():
            cs_project_obj = api_s_inspect.get_cs_project(self.domain_name,
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

    def set_sec_group_for_allow_all(self, sg_name='default'):
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
        self.update_sec_group(sg_name, rule1)
    # end set_sec_group_for_allow_all

    def update_sec_group(self, sg_name, rules):
        vnc_lib_h = self.get_project_connections().get_vnc_lib_h()
        old_rules = vnc_lib_h.get_sg_rules(sg_name)
        self.logger.info(
            "Adding rules to the %s security group in Project %s" %
            (sg_name, self.project_name))
        vnc_lib_h.set_sg_rules(sg_name, rules)
        #self.addCleanup(vnc_lib_h.set_sg_rules, sg_name, old_rules)

    @retry(delay=2, tries=10)
    def verify_on_cleanup(self):
        result = True
        if not self.verify_project_not_in_api_server():
            result &= False
            self.logger.error('Project %s is still present in API Server' % (
                self.project_name))
        return result
    # end verify_on_cleanup
# end ProjectFixture
