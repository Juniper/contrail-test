import project_test
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from keystone_tests import KeystoneCommands
import os
import fixtures
from test import BaseTestCase
import time
from tcutils.util import get_random_name

ADMIN_TENANT = 'admin'

class IsolatedCreds(fixtures.Fixture):

    def __init__(self,project_name,inputs,ini_file = None ,logger = None):

#        self.project_name = project_name
        self.project_name = get_random_name(project_name) 
        self.user = project_name
        self.password = project_name
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
                                        connections= self.connections)
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
        insecure = bool(os.getenv('OS_INSECURE',True))
        try:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                                 'http://' + self.inputs.openstack_ip + ':5000/v2.0'
            self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
                                                   tenant= self.inputs.project_name, auth_url= auth_url, insecure=insecure)

        except Exception as e:
            self.logger.warn("Failed - Keystone client instance")
        self.key_stone_clients.delete_user(user)

    def create_and_attach_user_to_tenant(self):
        insecure = bool(os.getenv('OS_INSECURE',True))
        try:
            auth_url = os.getenv('OS_AUTH_URL') or \
                                 'http://' + self.inputs.openstack_ip + ':5000/v2.0'
            self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
                                                   tenant= self.inputs.project_name, auth_url= auth_url, insecure=insecure)
            try:
                self.key_stone_clients.create_user(self.user,self.password,email='',tenant_name=self.inputs.stack_tenant,enabled=True)
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
            
        self.project_connections= ContrailConnections(self.project_inputs,project_name= self.project_name,
				   username=self.project.username
                                  ,password= self.project.password,
                                   logger = self.logger)
        return self.project_connections

    def get_admin_inputs(self):

        admin = AdminCreds(ADMIN_TENANT , self.inputs , self.ini_file , self.logger)
        return admin.get_inputs()		

    def get_admin_connections(self):

        admin = AdminCreds(ADMIN_TENANT , self.inputs , self.ini_file , self.logger)
        return admin.get_conections()	
	
    def cleanUp(self):
        super(IsolatedCreds, self).cleanUp()

class AdminCreds(fixtures.Fixture):

    def __init__(self,project_name,inputs,ini_file = None ,logger = None):

        self.project_name = project_name
        self.user = project_name 
        self.password = project_name
        self.inputs = inputs
        self.ini_file = ini_file
        self.logger = logger

    def get_inputs(self):

        return self.inputs
 
    def get_conections(self): 
            
        connections= ContrailConnections(self.inputs,project_name= self.project_name,
				   username=self.inputs.stack_user
                                  ,password= self.inputs.stack_password,
                                   logger = self.logger)
        return connections
    
    def cleanUp(self):
        super(AdminCreds, self).cleanUp()
