import os
import re
from common.openstack_libs import ks_identity
from common.openstack_libs import ks_session
from common.openstack_libs import ks_client
from common.openstack_libs import ks_exceptions
from common import log_orig as contrail_logging
from tcutils.util import retry, get_dashed_uuid

class KeystoneCommands():

    '''Handle all tenant managements'''

    def __init__(self, username=None, password=None, tenant=None,
                 domain_name=None, auth_url=None, insecure=True, region_name=None,
		 cert=None, key=None, cacert=None, version=None, logger=None, scope='domain'):
        self.sessions = dict()
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.project = tenant
        self.domain_name = domain_name or 'Default'
        self.cert = cert
        self.key = key
        self.cacert = cacert
        self.region_name = region_name
        self.insecure = insecure
        self.version = self.get_version(version)
        self.scope = scope
        self.keystone = self.get_client(self.scope)

    def get_version(self, version):
        if not version:
            pattern = 'http[s]?://(?P<ip>\S+):(?P<port>\d+)/*(?P<version>\S*)'
            version = re.match(pattern, self.auth_url).group('version')
        if 'v3' in version and not os.getenv('KSV2_IN_KSV3',False):
            version = 3
        else:
            version = 2
        return str(version)

    @property
    def session(self):
        return self.get_session(scope='project')

    def get_session(self, scope='project'):
        if scope in self.sessions:
            return self.sessions[scope]
        if self.version == '2':
            self.auth = ks_identity.v2.Password(auth_url=self.auth_url,
                                           username=self.username,
                                           password=self.password,
                                           tenant_name=self.project)
        elif self.version == '3':
            project_name = None if scope == 'domain' else self.project
            project_domain_name = None if scope == 'domain' else self.domain_name
            domain_name = self.domain_name if scope == 'domain' else None
            self.auth = ks_identity.v3.Password(auth_url=self.auth_url,
                                           username=self.username,
                                           password=self.password,
                                           project_name=project_name,
                                           domain_name=domain_name,
                                           user_domain_name=self.domain_name,
                                           project_domain_name=project_domain_name)
            
        self.sessions[scope] = ks_session.Session(auth=self.auth,
            verify=not self.insecure if self.insecure else self.cacert,
            cert=(self.cert, self.key))
        return self.sessions[scope]

    def get_client(self, scope='domain'):
        return ks_client.Client(version=self.version, session=self.get_session(scope),
                                      auth_url=self.auth_url, region_name=self.region_name)

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
    
    def get_group_dct(self,group_name):
        all_groups = self.group_list()
        for x in all_groups:
            if (x.name == group_name):
                return x
        return None
    
    def find_domain(self, domain_name):
        return self.keystone.domains.find(name=domain_name)

    def get_domain(self, domain_id):
        return self.keystone.domains.get(domain_id)

    def list_domains(self):
        return self.keystone.domains.list()

    def update_domain(self, domain_id, domain_name=None,
                      description=None, enabled=None):
        return self.keystone.domains.update(domain=domain_id, name=domain_name,
                                            description=description,
                                            enabled=enabled)

    def create_domain(self, domain_name):
        return get_dashed_uuid(self.keystone.domains.create(domain_name).id)

    def delete_domain(self, domain_name, domain_obj=None):
        if not domain_obj:
            domain_obj=self.find_domain(domain_name)
        self.update_domain(domain_id=domain_obj.id, enabled=False)
        return self.keystone.domains.delete(domain_obj)


    def create_project(self, project_name, domain_name='Default'):
        if self.version == '3':
            domain=self.find_domain(domain_name)
            return get_dashed_uuid(self.keystone.projects.create(name=project_name, domain=domain).id)
        else:
            return get_dashed_uuid(self.keystone.tenants.create(project_name).id)
 
    def delete_project(self, name, obj=None):
        if self.version == '3':
            if not obj:
               obj = self.keystone.projects.find(name=name)
            self.keystone.projects.delete(obj)
        else:
            if not obj:
               obj = self.keystone.tenants.find(name=name)
            self.keystone.tenants.delete(obj)

    def create_tenant_list(self, tenants=[]):
        for tenant in tenants:
            return_vlaue = self.create_project(project_name=tenant)

    def delete_tenant_list(self, tenants=[]):
        for tenant in tenants:
             self.delete_project(tenant)

    def update_tenant(self, tenant_id, tenant_name=None, description=None,
                      enabled=None):

        self.keystone.tenants.update(
            tenant_id, tenant_name=tenant_name, description=description, enabled=enabled)

    def add_user_to_domain(self, user, role, domain=None):
        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        domain=self.find_domain(domain)
        self.keystone.roles.grant(role, user=user, group=None, domain=domain)

    def add_user_to_tenant(self, tenant, user, role, domain=None):
        ''' inputs have to be string '''
        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        if self.version == '3':
            self.keystone.roles.grant(role, user=user, group=None, project=tenant)
        else:
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

    def add_group_to_domain(self, group, role, domain=None):
        ''' inputs have to be string '''
        group = self.get_group_dct(group)
        role = self.get_role_dct(role)
        if self.version == '3':
            domain=self.find_domain(domain)
            self.keystone.roles.grant(role, user=None, group=group, domain=domain)

    def add_group_to_tenant(self, tenant, group, role):
        ''' inputs have to be string '''
        group = self.get_group_dct(group)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        if self.version == '3':
            self.keystone.roles.grant(role, user=None, group=group, project=tenant)
    
    def remove_user_from_domain(self, user, role, domain):
        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        domain=self.find_domain(domain)
        self.keystone.roles.revoke(role, user=None, group=group, domain=domain)

    def remove_user_from_tenant(self, tenant, user, role):

        user = self.get_user_dct(user)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        if self.version == '3':
            self.keystone.roles.revoke(role, user=None, group=group, project=tenant)
        else:
            self.keystone.tenants.remove_user(tenant, user, role)
    
    def remove_group_from_domain(self, group, role, domain=None):
        group = self.get_group_dct(group)
        role = self.get_role_dct(role)
        if self.version == '3':
            domain=self.find_domain(domain)
            self.keystone.roles.revoke(role, user=None, group=group, domain=domain)
    
    def remove_group_from_tenant(self,tenant, group, role):
        group = self.get_group_dct(group)
        role = self.get_role_dct(role)
        tenant = self.get_tenant_dct(tenant)
        if self.version == '3':
            self.keystone.roles.revoke(role, user=None, group=group, project=tenant)

    def tenant_list(self, limit=None, marker=None):
        if self.version == '3':
            return self.keystone.projects.list()
        else:
            return self.keystone.tenants.list()
    
    def group_list(self,):
        return self.keystone.groups.list()

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

    def create_user(self, user, password, email='', tenant_name=None,
                    enabled=True, domain_name=None):
        if self.version == '3':
            project_id=self.get_tenant_dct(tenant_name).id
            domain_id=self.find_domain(domain_name).id
            self.keystone.users.create(user, domain_id, project_id, password, email, enabled=enabled)
        else:
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

    def get_domain_id(self, domain_name):        
       try:
           obj =  self.find_domain(domain_name=domain_name)
           return obj.id
       except ks_exceptions.NotFound: 
           return None

    def get_id(self):
        return get_dashed_uuid(self.session.get_project_id())

    def get_project_id(self, name, domain_id):
       try:
           if self.version == '3':
               domain_id = domain_id or  'default'
               obj =  self.keystone.projects.find(name=name, domain_id=domain_id)
           else:
               obj =  self.keystone.tenants.find(name=name)
           return get_dashed_uuid(obj.id)
       except ks_exceptions.NotFound:
           return None

    def get_endpoint(self, service, interface='public'):
        ''' Given the service-name return the endpoint ip '''
        return self.session.get_endpoint(auth=self.session.auth,
                                         service_type=service,
                                         interface=interface)

    def get_token(self):
        return self.session.get_token()

    def create_group(self,name,domain_name):
        domain=self.find_domain(domain_name)
        return self.keystone.groups.create(name=name, domain=domain)
    
    def delete_group(self,name):
        domain=self.find_domain(domain_name)
        return self.keystone.groups.delete(name=name)
    
    def add_user_to_group(self,user,group):
        user = self.get_user_dct(user)
        group = self.get_group_dct(group)
        self.keystone.users.add_to_group(user, group)

    def remove_user_from_group(self,user, group):
        user = self.get_user_dct(user)
        group = self.get_group_dct(group)
        self.keystone.users.remove_from_group(user, group)