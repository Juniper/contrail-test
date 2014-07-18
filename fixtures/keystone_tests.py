from keystoneclient.v2_0 import client as keystone_client
from keystoneclient import exceptions as ks_exceptions
from common import log as logging
from util import retry

LOG = logging.getLogger(__name__)

class KeystoneCommands():

    '''Handle all tenant managements'''

    def __init__(self, username=None, password=None, tenant=None, auth_url=None, token=None, endpoint=None):

        if token:
            self.keystone = keystoneclient.Client(
                token=token, endpoint=endpoint)
        else:
            self.keystone = keystone_client.Client(
                username=username, password=password, tenant_name=tenant, auth_url=auth_url)
            #import pdb;pdb.set_trace()

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
#                user = x
#        import pdb;pdb.set_trace()
#        return user

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

    @retry(delay=3, tries=5)
    def delete_user(self, user):

        user = self.get_user_dct(user)
        try:
            self.keystone.users.delete(user)
            return True
        except ks_exceptions.ClientException, e:
            # TODO Remove this workaround 
            if 'Unable to add token to revocation list' in str(e):
                LOG.warn('Exception %s while deleting user' % (
                    str(e)))
                return False
    # end delete_user

    def update_user_tenant(self, user, tenant):

        user = self.get_user_dct(user)
        tenant = self.get_tenant_dct(tenant)
        self.keystone.users.update_tenant(user, tenant)

    def user_list(self, tenant_id=None, limit=None, marker=None):

        return self.keystone.users.list()
