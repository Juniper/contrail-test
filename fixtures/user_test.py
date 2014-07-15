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


class UserFixture(fixtures.Fixture):

    def __init__(self, vnc_lib_h, connections, username=None, password=None, tenant=None, role='admin', token=None, endpoint=None):
        self.inputs= connections.inputs
        self.vnc_lib_h= vnc_lib_h
        self.connections= connections
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.auth_url = 'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        self.already_present = False
        self.username = username 
        self.password = password 
        self.tenant = tenant
        self.role = role
        self.email = str(username) + "@example.com"
        self.token = token
        self.endpoint = endpoint
        self.verify_is_run = False
        if self.token:
            self.keystone = keystoneclient.Client(
                token=self.token, endpoint=self.endpoint)
        else:
            self.keystone = ksclient.Client(
                username=self.inputs.stack_user, password=self.inputs.stack_password, tenant_name=self.inputs.project_name, auth_url=self.auth_url)
    # end __init__

    def get_role_dct(self, role_name):

        all_roles = self.keystone.roles.list()
        for x in all_roles:
            if (x.name == role_name):
                return x
        return None

    def get_user_dct(self, user_name):

        all_users = self.keystone.users.list()
        for x in all_users:
            if (x.name == user_name):
                return x
        return None

    def get_tenant_dct(self, tenant_name):

        all_tenants = self.keystone.tenants.list()
        for x in all_tenants:
            if (x.name == tenant_name):
                return x
        return None

    def create_tenant_list(self, tenants=[]):

        for tenant in tenants:
            return_vlaue = self.keystone.tenants.create(tenant)

    def delete_tenant_list(self, tenants=[]):

        all_tenants = self.tenant_list()
        for tenant in tenants:
            for t in all_tenants:
                if (tenant == t.name):
                    self.keystone.tenants.delete(t)
                    break

    def update_tenant(self, tenant_id, tenant_name=None, description=None,
                      enabled=None):

        self.keystone.tenants.update(
            tenant_id, tenant_name=tenant_name, description=description, enabled=enabled)

    def add_user_to_tenant(self, tenant, user, role):

        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.tenants.add_user(tenant, user, role)

    def remove_user_from_tenant(self, tenant, user, role):

        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.tenants.remove_user(tenant, user, role)

    def tenant_list(self, limit=None, marker=None):

        return self.keystone.tenants.list()

    def create_roles(self, role):

        self.keystone.roles.create(role)

    def delete_roles(self, role):

        role = self.get_role_dct(role)
        self.keystone.roles.delete(role)

    def add_user_role(self, user_name, role_name, tenant_name=None):

        user = self.get_user_dct(user_name)
        role = self.get_role_dct(role_name)
        if tenant_name:
            tenant = self.get_tenant_dct(tenant_name)

        self.keystone.roles.add_user_role(user, role, tenant)

    def get_role_for_user(self, user, tenant_name=None):

        user = self.get_user_dct(user)
        if tenant_name:
            tenant = self.get_tenant_dct(tenant_name)
        return self.keystone.roles.roles_for_user(user, tenant)

    def remove_user_role(self, user, role, tenant=None):

        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        if tenant:
            tenant = self.get_tenant_dct(tenant)

        self.keystone.roles.remove_user_role(user, role, tenant)

    def roles_list(self):

        return self.keystone.roles.list()

    def create_user(self, user, password, email='', tenant_name=None, enabled=True):

        tenant_id = self.get_tenant_dct(tenant_name).id
        self.keystone.users.create(user, password, email, tenant_id, enabled)

    def delete_user(self, user):

        user = self.get_user_dct(user)
        self.keystone.users.delete(user)

    def update_user_tenant(self, user, tenant):

        user = self.get_user_dct(user)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.users.update_tenant(user, tenant)

    def user_list(self, tenant_id=None, limit=None, marker=None):

        return self.keystone.users.list()

    def _reauthenticate_keystone(self):
        if self.token:
            self.keystone = keystoneclient.Client(
                token=self.token, endpoint=self.endpoint)
        else:
            self.keystone = ksclient.Client(
                username=self.inputs.stack_user, password=self.inputs.stack_password, tenant_name=self.inputs.project_name, auth_url=self.auth_url)
    # end _reauthenticate_keystone

    def setUp(self):
        super(UserFixture, self).setUp()
        try:
            ks_project = self.keystone.tenants.find(name=self.inputs.project_name)
            if ks_project:
                self.project_id = get_dashed_uuid(ks_project.id)
                self.logger.debug(
                    'Project %s already present. Check user %s exist' %
                    (self.inputs.project_name, self.username))
                if self.get_user_dct(self.username):
                    self.logger.info('User %s already exist, skip creation' %
                    self.username)
                    self.already_present = True
                else:
                    try:
                        self.create_user(
                            self.username, self.password, email=self.email, tenant_name=self.inputs.project_name, enabled=True)
                        assert self.verify_on_setup()
                    except Exception as e:
                        self.logger.warn('User creation failed for exception %s...' % (e))
                #if test tenant already created, associate user to tenant
                if self.tenant:
                    if get_tenant_dct(self.tenant):
                        self.logger.info('Tenant %s exists, associate user %s..' % (self.teannt, self,username))
                        self.add_user_to_tenant(self.tenant, self.username, self.role)
        except ks_exceptions.NotFound, e:
            self.logger.info('Project %s not found, skip creating user %s' % (
                self.project_name, self.username))
    # end setUp

    def cleanUp(self):
        super(UserFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self._reauthenticate_keystone()
            self.logger.info('Deleting user %s' %self.username)
            self.delete_user(self.username)
            if self.verify_is_run:
                assert self.verify_on_cleanup()            
        else:
            self.logger.debug('Skipping the deletion of User %s' %
                              self.username)

    # end cleanUp

    def verify_on_setup(self):
        result = True
        if not self.get_user_dct(self.username):
            result &= False
            self.logger.error('Verification of user %s in keystone '
                              'failed!! ' % (self.username))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    def verify_on_cleanup(self):
        result = True
        if self.get_user_dct(self.username):
            result &= False
            self.logger.error('User %s is still present in Keystone' % (
                self.username))
        return result
    # end verify_on_cleanup
# end UserFixture
