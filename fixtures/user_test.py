import os
import fixtures
import uuid
import fixtures

from common.connections import ContrailConnections
from tcutils.util import retry
from time import sleep
from tcutils.util import get_dashed_uuid

from common.openstack_libs import ks_client as ksclient
from common.openstack_libs import ks_exceptions
from common.openstack_libs import keystoneclient

class UserFixture(fixtures.Fixture):

    def __init__(self, connections, username=None, password=None, tenant=None, role='admin', token=None, endpoint=None):
        self.inputs= connections.inputs
        self.connections= connections
        self.logger = self.inputs.logger
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter, However we satisfy the test infra
            # with dummy fixture objects
            return
        insecure = bool(os.getenv('OS_INSECURE', True))
        if not self.inputs.ha_setup:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        else:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://%s:5000/v2.0' % (self.inputs.auth_ip)
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
                username=self.inputs.stack_user, password=self.inputs.stack_password,
                tenant_name=self.inputs.project_name, auth_url=self.auth_url,
                insecure=insecure)
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

    def add_user_to_tenant(self, tenant, user, role):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        configure_role = True
        kuser = self.get_user_dct(user)
        krole = self.get_role_dct(role)
        ktenant = self.get_tenant_dct(tenant)
        roles = self.get_role_for_user(user, tenant)
        if roles:
            for r in roles:
                if r.name == role:
                    configure_role = False
                    self.logger.info("Already user %s as %s role in tenant %s" 
                        %(user, role, tenant))
                    break
        if configure_role:
            self.keystone.tenants.add_user(ktenant, kuser, krole)

    def remove_user_from_tenant(self, tenant, user, role):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
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
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
        try:
            ks_project = self.keystone.tenants.find(name=self.inputs.project_name)
            if ks_project:
                self.project_id = get_dashed_uuid(ks_project.id)
                self.logger.debug(
                    'Project %s already present. Check user %s exist' %
                    (self.inputs.project_name, self.username))
                if self.get_user_dct(self.username):
                    self.logger.info('User %s already exists, skipping creation' %
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
                    if self.get_tenant_dct(self.tenant):
                        self.logger.info('Tenant %s exists, associate user %s..' % (self.tenant, self.username))
                        self.add_user_to_tenant(self.tenant, self.username, self.role)
        except ks_exceptions.NotFound, e:
            self.logger.info('Project %s not found, skip creating user %s' % (
                self.project_name, self.username))
    # end setUp

    def cleanUp(self):
        super(UserFixture, self).cleanUp()
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return
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
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return True
        result = True
        if not self.get_user_dct(self.username):
            result &= False
            self.logger.error('Verification of user %s in keystone '
                              'failed!! ' % (self.username))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    def verify_on_cleanup(self):
        if self.inputs.orchestrator == 'vcenter':
            # No concept of user in vcenter
            return True
        result = True
        if self.get_user_dct(self.username):
            result &= False
            self.logger.error('User %s is still present in Keystone' % (
                self.username))
        return result
    # end verify_on_cleanup
# end UserFixture
