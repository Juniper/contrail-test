import fixtures
from keystoneclient.v2_0 import client as ksclient
from vnc_api.vnc_api import *

import fixtures

from quantum_test import *
from vnc_api_test import *
from contrail_fixtures import *
from connections import ContrailConnections

class ProjectFixture(fixtures.Fixture ):
    def __init__(self, vnc_lib_h, connections, project_name='admin', username = None, password = None, role= 'admin', option= 'api' ):
        self.inputs= connections.inputs
        self.vnc_lib_h= vnc_lib_h
        self.connections= connections
        self.project_name= project_name
        self.project_obj= None
        self.domain_name='default-domain'
        self.already_present= False
        self.logger= connections.inputs.logger
        self.project_fq_name=[self.domain_name, self.project_name]
        self.username= username
        self.password= password
        self.role= role
        self.option= option
        self.tenant_dict= {} 
        self.user_dict= {} 
        self._create_user_set= {}
        self.auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
        self.kc= ksclient.Client(
                    username= self.inputs.stack_user,
                    password= self.inputs.stack_password,
                    tenant_name= self.project_name,
                    auth_url= self.auth_url )
        self.project_connections = None
    #end __init__
    
    def _create_project(self):
        project=Project(self.project_name)
        self.vnc_lib_h.project_create(project)
        project = self.vnc_lib_h.project_read(project.get_fq_name())
        self.logger.info( 'Created Project  %s ' %( str(project.get_fq_name())) ) 
        ipam = NetworkIpam('default-network-ipam', project, IpamType("dhcp"))
        self.vnc_lib_h.network_ipam_create(ipam)
        self.logger.info(  'Created network ipam' )
   #end _create_project

    def _delete_project(self):
       self.vnc_lib_h.project_delete(fq_name= self.project_fq_name)
    #end _delete_project

    def _create_user_keystone(self):
        if not self.username:
            self.username= 'user-'+self.project_name
        if not self.password:
            self.password= 'contrail123'
        user_list = [(self.username, self.password, self.role)]
        user_pass = dict((n, p) for (n,p,r) in user_list)
        user_role = dict((n, r) for (n,p,r) in user_list)
        user_set = set([n for (n,p,r) in user_list])
        role_set = set([r for (n,p,r) in user_list])

        users = set([user.name for user in self.kc.users.list()])
        roles = set([user.name for user in self.kc.roles.list()])
        tenants = self.kc.tenants.list()
        admin_tenant = [x for x in tenants if x.name == 'admin'][0]

        self._create_user_set = user_set - users
        create_role_set = role_set - roles
        role_dict = dict((role.name, role) for role in self.kc.roles.list())

        for name in self._create_user_set:
            user = self.kc.users.create(name, user_pass[name], '', tenant_id=admin_tenant.id)
            self.logger.info('Created User:%s with Role:%s for Project:%s ' %(name, user_role[name], self.project_name))
            self.kc.roles.add_user_role(user, role_dict[user_role[name]], self.tenant_dict[self.project_name])

        self.user_dict = dict((user.name, user) for user in self.kc.users.list())
    #end _create_user_keystone 

    def _create_project_keystone(self):
        if self.project_name == 'admin':
            self.logger.info('Project admin already exist, no need to create')
            return self
        project_list_in_api_before_test= self.vnc_lib_h.projects_list()
        print "project list before test: %s" %project_list_in_api_before_test
        if self.project_name in str(project_list_in_api_before_test):
            self.logger.info('Project already present. Cleaning them')
            self.vnc_lib_h.project_delete(fq_name= ["default-domain", self.project_name])
        else:
            self.logger.info('Proceed with creation of new project.')
     
        # create project using keystone
        self.kc.tenants.create(self.project_name)
        self.logger.info('Created Project:%s ' %(self.project_name))
        self.tenant_dict = dict((tenant.name, tenant) for tenant in self.kc.tenants.list())
    #end _create_project_keystone

    def _delete_project_keystone(self):
       self.logger.info('Deleting Project %s'%self.project_fq_name)
       self.kc.tenants.delete(self.tenant_dict[self.project_name])
    #end _delete_project

    def _delete_user_keystone(self):
       for name in self._create_user_set:
           self.logger.info('Deleting User %s'%name)
           self.kc.users.delete(self.user_dict[name])
    #end _delete_user_keystone
    
    def setUp(self):
        super(ProjectFixture, self).setUp()
        try:
            self.project_obj = self.vnc_lib_h.project_read(fq_name = self.project_fq_name)
            if self.project_obj:
                 self.already_present= True
                 self.logger.debug('Project %s already present.Not creating it'%self.project_fq_name)
                 if self.project_name is not 'admin':
                     if not self.username:
                         self.username= 'user-'+self.project_name
                     if not self.password:
                         self.password= 'contrail123'
        except NoIdError,e:
            print "Project not found, creating it"
            if self.option == "keystone":
                self._create_project_keystone()
                self._create_user_keystone()
            else:
                self._create_project() #TODO
            self.project_obj = self.vnc_lib_h.project_read(fq_name = self.project_fq_name)
        self.uuid = self.project_obj.uuid
    #end setUp
    
    def cleanUp(self):
        super(ProjectFixture, self).cleanUp()
        do_cleanup= True
        if self.inputs.fixture_cleanup == 'no' : do_cleanup = False
        if self.already_present : do_cleanup= False
        if self.inputs.fixture_cleanup == 'force' : do_cleanup = True
        if do_cleanup:
            if self.option == "keystone":
                self._delete_user_keystone()
                self._delete_project_keystone()
            else:
                self._delete_project()
        else:
            self.logger.debug('Skipping the deletion of Project %s'%self.project_fq_name)

    #end cleanUp
    
    def get_project_connections(self,username=None, password=None):
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
    #end get_project_connections

#end ProjectFixture
