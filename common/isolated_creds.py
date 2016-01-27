import project_test
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import os
import fixtures
from test import BaseTestCase
import time
from tcutils.util import get_random_name

ADMIN_TENANT = 'admin'

class IsolatedCreds(fixtures.Fixture):

    def __init__(self,project_name, inputs, ini_file=None, logger=None,
                 username=None, password=None):

        self.inputs = inputs
        if (self.inputs.public_tenant == project_name):
            self.project_name = project_name
        else: 
            self.project_name = get_random_name(project_name) 
        if username:
            self.user = username
        else:
            self.user = project_name
        if password:
            self.password = password
        else:
            self.password = project_name
        self.ini_file = ini_file
        self.logger = logger
        if self.inputs.orchestrator == 'vcenter':
            self.project_name = self.inputs.stack_tenant
            self.user = self.inputs.stack_user
            self.password = self.inputs.stack_password

    def setUp(self):
        super(IsolatedCreds, self).setUp()
        self.connections= ContrailConnections(self.inputs, self.logger)
        self.vnc_lib= self.connections.vnc_lib
        self.auth = self.connections.auth

    def create_tenant(self): 

        self.project = None
        time.sleep(4)        
        try:
            self.project = project_test.ProjectFixture(project_name = self.project_name, auth=self.auth,
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
        if self.inputs.orchestrator == 'vcenter':
            return
        if user:
            user = user
	else:
	    user = self.user
        self.auth.delete_user(user)

    def create_and_attach_user_to_tenant(self,user = None , password=None):
        if self.inputs.orchestrator == 'vcenter':
            return
        user = user if user else self.user
        password = password if password else self.password
        self.auth.create_user(user,password)
        self.auth.add_user_to_project(user, self.project_name)
        self.auth.add_user_to_project('admin', self.project_name)
        time.sleep(4)

    def get_inputs(self):

        self.project_inputs= ContrailTestInit(self.ini_file,
                            stack_user=self.project.username,
                            stack_password=self.project.password,
                            project_fq_name=['default-domain',self.project_name],logger = self.logger)
        return self.project_inputs

    def get_conections(self):
        self.project_connections= ContrailConnections(self.project_inputs,
                                    project_name= self.project_name,
                                    username=self.project.username,
                                    password= self.project.password,
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
