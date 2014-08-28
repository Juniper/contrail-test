import os
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


class ProjectFixture(fixtures.Fixture):

    def __init__(self, vnc_lib_h, connections, project_name='admin', username=None, password=None, role='admin', option='api'):
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
        self.option = option
        self.tenant_dict = {}
        self.user_dict = {}
        self._create_user_set = {}
        self.auth_url = os.getenv('OS_AUTH_URL') or \
                            'http://' + self.inputs.openstack_ip + ':5000/v2.0'
        insecure = bool(os.getenv('OS_INSECURE',True))
        self.kc = ksclient.Client(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name,
            auth_url=self.auth_url,
            insecure=insecure)
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

    def _create_user_keystone(self):
        if not self.username:
            self.username = 'user-' + self.project_name
        if not self.password:
            self.password = 'contrail123'
        user_list = [(self.username, self.password, self.role)]
        user_pass = dict((n, p) for (n, p, r) in user_list)
        user_role = dict((n, r) for (n, p, r) in user_list)
        user_set = set([n for (n, p, r) in user_list])
        role_set = set([r for (n, p, r) in user_list])

        users = set([user.name for user in self.kc.users.list()])
        roles = set([user.name for user in self.kc.roles.list()])
        tenants = self.kc.tenants.list()
        admin_user = [x for x in self.kc.users.list() if x.name == 'admin'][0]
        admin_tenant = [x for x in tenants if x.name == 'admin'][0]

        self._create_user_set = user_set - users
        create_role_set = role_set - roles
        role_dict = dict((role.name, role) for role in self.kc.roles.list())

        for name in self._create_user_set:
            user = self.kc.users.create(
                name, user_pass[name], '', tenant_id=admin_tenant.id)
            self.logger.info('Created User:%s with Role:%s for Project:%s ' %
                             (name, user_role[name], self.project_name))
            self.kc.roles.add_user_role(
                user, role_dict[user_role[name]], self.tenant_dict[self.project_name])
        # configure admin with role 'Member' for non-admin tenants by default
        self.kc.roles.add_user_role(
            admin_user, role_dict['Member'], self.tenant_dict[self.project_name])

        self.user_dict = dict((user.name, user)
                              for user in self.kc.users.list())
    # end _create_user_keystone

    def _create_project_keystone(self):
        if self.project_name == 'admin':
            self.logger.info('Project admin already exist, no need to create')
            return self
        project_list_in_api_before_test = self.vnc_lib_h.projects_list()
        print "project list before test: %s" % project_list_in_api_before_test
        if self.project_name in str(project_list_in_api_before_test):
            self.logger.info('Project already present. Cleaning them')
            self.vnc_lib_h.project_delete(
                fq_name=["default-domain", self.project_name])
        else:
            self.logger.info('Proceed with creation of new project.')

        # create project using keystone
        self.kc.tenants.create(self.project_name)
        self.logger.info('Created Project:%s ' % (self.project_name))
        self.tenant_dict = dict((tenant.name, tenant)
                                for tenant in self.kc.tenants.list())
    # end _create_project_keystone

    def _delete_project_keystone(self):
        self.logger.info('Deleting Project %s' % self.project_fq_name)
        self.kc.tenants.delete(self.tenant_dict[self.project_name])
    # end _delete_project

    def _delete_user_keystone(self):
        for name in self._create_user_set:
            self.logger.info('Deleting User %s' % name)
            self.kc.users.delete(self.user_dict[name])
    # end _delete_user_keystone

    def setUp(self):
        super(ProjectFixture, self).setUp()
        try:
            self.project_obj = self.vnc_lib_h.project_read(
                fq_name=self.project_fq_name)
            if self.project_obj:
                self.already_present = True
                self.logger.debug(
                    'Project %s already present.Not creating it' %
                    self.project_fq_name)
                if self.project_name is not 'admin':
                    if not self.username:
                        self.username = 'user-' + self.project_name
                    if not self.password:
                        self.password = 'contrail123'
        except NoIdError, e:
            print "Project not found, creating it"
            if self.option == "keystone":
                self._create_project_keystone()
                self._create_user_keystone()
            else:
                self._create_project()  # TODO
            time.sleep(2)
            self.project_obj = self.vnc_lib_h.project_read(
                fq_name=self.project_fq_name)
        self.uuid = self.project_obj.uuid
        self.project_id = self.uuid
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
            if self.option == "keystone":
                self._delete_user_keystone()
                self._delete_project_keystone()
            else:
                self._delete_project()
            if self.verify_is_run:
                assert self.verify_on_cleanup()
        else:
            self.logger.debug('Skipping the deletion of Project %s' %
                              self.project_fq_name)

    # end cleanUp

    def get_project_connections(self, username=None, password=None):
        if not username:
            username = self.username or 'admin'
        if not password:
            password = self.password or 'contrail123'
        if not self.project_connections:
            self.project_connections = ContrailConnections(
                inputs=self.inputs,
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

    @retry(delay=5, tries=6)
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
