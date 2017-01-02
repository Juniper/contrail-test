import os
from common.openstack_libs import ks_client as keystone_client
from common.openstack_libs import ks_exceptions
from common.openstack_libs import keystoneclient
from common import log_orig as contrail_logging
from tcutils.util import retry, get_dashed_uuid

class KeystoneCommands():

    '''Handle all tenant managements'''

    def __init__(self, username=None, password=None, tenant=None,
                 auth_url=None, token=None, endpoint=None,
                 insecure=True, region_name=None,
                 logger=None):

        self.logger = logger or contrail_logging.getLogger(__name__)
        if token:
            self.keystone = keystoneclient.Client(
                token=token, endpoint=endpoint)
        else:
            self.keystone = keystone_client.Client(
                username=username, password=password, tenant_name=tenant, auth_url=auth_url,
                insecure=insecure, region_name=region_name or 'RegionOne')

    def get_session(self):
        auth = keystoneclient.auth.identity.v2.Password(auth_url=self.keystone.auth_url,
            username=self.keystone.username, password=self.keystone.password, tenant_name=self.keystone.tenant_name)
        sess = keystoneclient.session.Session(auth=auth)
        return sess

    def get_handle(self):
        return self.keystone

    def get_role_dct(self, role_name):
        all_roles = self.roles_list()
        for x in all_roles:
            if (x.name == role_name):
                return x
        return None

    def get_user_dct(self, user_name):
        all_users = self.user_list()
        for x in all_users:
            if (x.name == user_name):
                return x
        return None

    def get_tenant_dct(self, tenant_name):
        all_tenants = self.tenant_list()
        for x in all_tenants:
            if (x.name == tenant_name):
                return x
        return None

    def create_project(self, name):
       return get_dashed_uuid(self.keystone.tenants.create(name).id)
 
    def delete_project(self, name, obj=None):
       if not obj:
           obj = self.keystone.tenants.find(name=name)
       self.keystone.tenants.delete(obj)

    def create_tenant_list(self, tenants=[]):
        for tenant in tenants:
            return_vlaue = self.create_project(tenant)

    def delete_tenant_list(self, tenants=[]):
        for tenant in tenants:
             self.delete_project(tenant)

    def update_tenant(self, tenant_id, tenant_name=None, description=None,
                      enabled=None):

        self.keystone.tenants.update(
            tenant_id, tenant_name=tenant_name, description=description, enabled=enabled)

    def add_user_to_tenant(self, tenant, user, role):
        ''' inputs have to be string '''
        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        self._add_user_to_tenant(tenant, user, role)

    def _add_user_to_tenant(self, tenant, user, role):
        ''' inputs could be id or obj '''
        try:
            self.keystone.tenants.add_user(tenant, user, role)
        except ks_exceptions.Conflict as e:
            if 'already has role' in str(e):
                self.logger.debug(str(e))
            else:
                self.logger.info(str(e))

    def remove_user_from_tenant(self, tenant, user, role):

        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.tenants.remove_user(tenant, user, role)

    def tenant_list(self, limit=None, marker=None):

        return self.keystone.tenants.list()

    def create_role(self, role):
        self.keystone.roles.create(role)

    def delete_role(self, role):
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

        tenant_id = self.get_tenant_dct(tenant_name).id if tenant_name else None
        self.keystone.users.create(user, password, email, tenant_id, enabled)

    @retry(delay=3, tries=5)
    def delete_user(self, user):

        user = self.get_user_dct(user)
        try:
            self.keystone.users.delete(user)
            return True
        except ks_exceptions.ClientException, e:
            # TODO Remove this workaround 
            if 'Unable to add token to revocation list' in str(e):
                self.logger.warn('Exception %s while deleting user' % (
                                 str(e)))
                return False
    # end delete_user

    def update_user_tenant(self, user, tenant):

        user = self.get_user_dct(user)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.users.update_tenant(user, tenant)

    def user_list(self, tenant_id=None, limit=None, marker=None):

        return self.keystone.users.list()

    def services_list(self, tenant_id=None, limit=None, marker=None):
        return self.keystone.services.list()

    def get_id(self):
        return get_dashed_uuid(self.keystone.auth_tenant_id)

    def get_project_id(self, name):
       try:
           obj =  self.keystone.tenants.find(name=name)
           return get_dashed_uuid(obj.id)
       except ks_exceptions.NotFound:
           return None

    def get_endpoint(self, service):
       ''' Given the service-name return the endpoint ip '''
       return self.keystone.service_catalog.get_urls(service_type=service)
