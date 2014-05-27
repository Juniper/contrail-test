import project_test
from contrail_test_init import ContrailTestInit
from connections import ContrailConnections
from keystone_tests import KeystoneCommands
import os
import fixtures
from test import BaseTestCase
import time

class IsolatedCreds(fixtures.Fixture):

    def __init__(self,project_name,inputs,ini_file = None ,option='keystone',logger = None):

        self.project_name = project_name
        self.user = project_name
        self.password = project_name
        self.option = option
        self.inputs = inputs
        self.ini_file = ini_file
        self.logger = logger

    def setUp(self):
        super(IsolatedCreds, self).setUp()
        self.connections= ContrailConnections(self.inputs, self.logger)
        self.vnc_lib= self.connections.vnc_lib
       # self.logger= self.inputs.logger

    def create_tenant(self): 

        self.project = None
        time.sleep(4)        
        try:
            self.project = project_test.ProjectFixture(project_name = self.project_name,
					vnc_lib_h= self.vnc_lib,username= self.user,password= self.password,
                                        connections= self.connections, option= self.option)
            self.project.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s"%(e)) 
        finally:
            return self.project

    def delete_tenant(self):

        self.project.cleanUp()

    def delete_user(self,user=None):

        if user:
            user = user
	else:
	    user = self.user
        try:
            auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
            self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
                                                   tenant= self.inputs.project_name, auth_url= auth_url )

        except Exception as e:
            self.logger.warn("Failed - Keystone client instance")
        self.key_stone_clients.delete_user(user)

    def create_and_attach_user_to_tenant(self):

        try:
            auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
            self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
                                                   tenant= self.inputs.project_name, auth_url= auth_url )
            try:
                self.key_stone_clients.create_user(self.user,self.password,email='',tenant_name= 'admin',enabled=True)
            except:
                self.logger.info("%s user already created"%(self.user))

            try:
                self.key_stone_clients.add_user_to_tenant(self.project_name,self.user , 'admin')
            except Exception as e:
                self.logger.info("%s user already added to project"%(self.user))
            try:
                self.key_stone_clients.add_user_to_tenant(self.project_name,'admin' , 'admin')
            except Exception as e:
                self.logger.info("Admin user already added to project")
            time.sleep(4)
        except Exception as e:
            self.logger.info("Failed - Keystone client instance")

    def get_inputs(self):

        self.project_inputs= self.useFixture(ContrailTestInit(self.ini_file, 
                            stack_user=self.project.username,
                            stack_password=self.project.password,
                            project_fq_name=['default-domain',self.project_name],logger = self.logger))
        return self.project_inputs

    def get_conections(self): 
            
        self.project_connections= ContrailConnections(self.inputs,project_name= self.project_name,
				   username=self.project.username
                                  ,password= self.project.password,
                                   logger = self.logger)
        return self.project_connections
 
    def cleanUp(self):
        super(IsolatedCreds, self).cleanUp()

#    def cleanUp(self):
#        super(IsolatedCreds, self).cleanUp()
#        pass
   
			

#    def get_project_inputs_connections(self,project_name='admin',user = 'admin',password='contrail123'):
#        '''Returns objects of project fixture,inputs and conections'''
#
#        dct = {}
#
#        try:
#            project_fixture = self.useFixture(project_test.ProjectFixture(project_name = project_name,vnc_lib_h= self.vnc_lib,username=user,
#                                                password= password,connections= self.connections, option= 'keystone'))
#            dct['project'] = project_fixture
#
#            try:
#                import keystone_tests
#                auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
#                self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
#                                                       tenant= self.inputs.project_name, auth_url= auth_url )
#                self.key_stone_clients.add_user_to_tenant(project_name,user , 'admin')
#                self.key_stone_clients.add_user_to_tenant(project_name,'admin' , 'admin')
#            except Exception as e:
#                self.logger.info("User already added to project")
#
#            project_inputs= self.useFixture(ContrailTestInit(self.ini_file, stack_user=project_fixture.username,
#                                        stack_password=project_fixture.password,project_fq_name=['default-domain',project_name]))
#            dct['inputs'] = project_inputs
#
#            project_connections= ContrailConnections(project_inputs,project_name= project_name,username=project_fixture.username
#                                        ,password= project_fixture.password)
#            dct['connections'] = project_connections
#        except Exception as e:
#            self.logger.warn("Got exception in get_project_inputs_connections as %s"%(e))
#        finally:
#            return dct
#
