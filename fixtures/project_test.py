import fixtures
from keystoneclient.v2_0 import client as ksclient
from vnc_api.vnc_api import *
import uuid
import fixtures

from quantum_test import *
from vnc_api_test import *
from contrail_fixtures import *
from connections import ContrailConnections
from util import retry
from time import sleep
from keystoneclient import exceptions as ks_exceptions
from util import get_dashed_uuid


class ProjectFixture(fixtures.Fixture):

    def __init__(self, vnc_lib_h, connections, project_name='admin', username=None, password=None, role='admin'):
        self.inputs = connections.inputs
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
        self.auth_url = 'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        self.kc = ksclient.Client(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name,
            auth_url=self.auth_url)
        self.project_connections = None
        self.api_server_inspects = self.connections.api_server_inspects
        self.verify_is_run = False
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
        if self.project_name == 'admin':
            self.logger.info('Project admin already exist, no need to create')
            return self

        project_list_in_api_before_test = self.vnc_lib_h.projects_list()

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
            self._reauthenticate_keystone()
            self._delete_project_keystone()
            if self.verify_is_run:
                assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping the deletion of Project %s' %
                              self.project_fq_name)

    # end cleanUp

    def get_from_api_server(self):
        self.project_obj = self.vnc_lib_h.project_read(
            fq_name=self.project_fq_name)
        return self.project_obj

    def get_project_connections(self, username=None, password=None):
        if not username:
            username = self.username or 'admin'
        if not password:
            password = self.password or 'contrail123'
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
                self.logger.warn('Project id %s got from API Server %s'
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
