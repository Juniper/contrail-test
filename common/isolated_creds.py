import project_test
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import os
import fixtures
from test import BaseTestCase
import time
from tcutils.util import get_random_name




class IsolatedCreds(fixtures.Fixture):

    def __init__(self, inputs, project_name=None, ini_file=None, logger=None,
                 username=None, password=None):

        self.username = None
        self.password = None
        self.inputs = inputs

        if inputs.tenant_isolation:
            self.project_name = get_random_name(project_name)
        else :
            self.project_name = project_name or inputs.stack_tenant
        if inputs.tenant_isolation and inputs.user_isolation:
            self.username = project_name
            self.password = project_name
        else:
            self.username = username or inputs.stack_user
            self.password = password or inputs.stack_password

        self.ini_file = ini_file
        self.logger = logger
        if self.inputs.orchestrator == 'vcenter':
            self.project_name = self.inputs.stack_tenant
            self.username = self.inputs.stack_user
            self.password = self.inputs.stack_password
    # end __init__

    def setUp(self):
        super(IsolatedCreds, self).setUp()
        self.connections= ContrailConnections(self.inputs, self.logger,
            username=self.username,
            password=self.password,
            project_name=self.project_name)
        self.vnc_lib= self.connections.vnc_lib
        self.auth = self.connections.auth

    def use_tenant(self, project_fixture):
        self.project = project_fixture

    def create_tenant(self, project_name):
        ''' Get a Project. Returns instance of ProjectFixture
            Creates the project if not found
        ''' 
        project = None
        try:
            project = project_test.ProjectFixture(
                project_name = project_name,
                auth=self.auth,
                vnc_lib_h= self.vnc_lib,
                username= self.username,
                password= self.password,
                connections= self.connections)
            project.setUp()
        except Exception as e:
            self.logger.exception("Exception while creating project")
        finally:
            return project
    # end create_tenant

    def delete_tenant(self, project_fixture):
        project_fixture.cleanUp()

    def get_inputs(self, project_fixture):
        project_inputs= ContrailTestInit(self.ini_file,
                            stack_user=project_fixture.project_username,
                            stack_password=project_fixture.project_user_password,
                            stack_tenant=self.project_name,logger = self.logger)
        return project_inputs

    def get_connections(self, project_inputs):
        self.project_connections= ContrailConnections(project_inputs,
                                    project_name=self.project_name,
                                    username=self.username,
                                    password=self.password,
                                    logger=self.logger)
        return self.project_connections

    def cleanUp(self):
        super(IsolatedCreds, self).cleanUp()

# end IsolatedCreds

class AdminIsolatedCreds(fixtures.Fixture):
    def __init__(self, inputs, admin_project_name=None, ini_file=None, logger=None,
        username=None, password=None):
        self.project_name = admin_project_name or inputs.admin_tenant
        self.username = username or inputs.admin_username
        self.password = password or inputs.admin_password
        self.inputs = inputs

        self.ini_file = ini_file
        self.logger = logger
        if self.inputs.orchestrator == 'vcenter':
            self.project_name = self.inputs.stack_tenant
            self.username = self.inputs.stack_user
            self.password = self.inputs.stack_password

    # end __init__

    def setUp(self):
        self.connections = ContrailConnections(self.inputs, self.logger,
            project_name=self.project_name,
            username=self.username,
            password=self.password)
        self.vnc_lib = self.connections.vnc_lib
        self.auth = self.connections.auth

    def delete_user(self, user):
        if self.inputs.orchestrator == 'vcenter':
            return
        if self.inputs.user_isolation:
            self.auth.delete_user(user)
    # end delete_user

    def create_and_attach_user_to_tenant(self, project_fixture, 
            username, password):
        project_fixture.set_user_creds(username, password)
        project_name = project_fixture.project_name
        if self.inputs.orchestrator == 'vcenter' or \
           not self.inputs.tenant_isolation:
            return
        if self.inputs.user_isolation:
            self.auth.create_user(username, password)
        self.auth.add_user_to_project(username, project_name)
        if self.inputs.admin_username:
            self.auth.add_user_to_project(self.inputs.admin_username,
                                          project_name)
        # Certain deployments uses neutron username/password for contrail too
        # So the neutron user has to be added to test tenant
        # for Service Chain v1 to launch VMs
        if self.inputs.neutron_username:
            self.auth.add_user_to_project(self.inputs.neutron_username,
                                          project_name, '_member_')
    # end create_and_attach_user_to_tenant

    def use_tenant(self, project_fixture):
        self.project = project_fixture

    def create_tenant(self, project_name):
        ''' Get a Project. Returns instance of ProjectFixture
            Creates the project if not found
        '''

        project = None
        try:
            project = project_test.ProjectFixture(
                project_name = project_name,
                auth=self.auth,
                vnc_lib_h= self.vnc_lib,
                username= self.username,
                password= self.password,
                connections= self.connections)
            project.setUp()
        except Exception as e:
            self.logger.exception("Exception while creating project")
        finally:
            return project
    # end create_tenant

    def delete_tenant(self, project_fixture):
        project_fixture.cleanUp()

    def get_inputs(self, project_fixture):
        project_inputs= ContrailTestInit(self.ini_file,
                            stack_user=project_fixture.project_username,
                            stack_password=project_fixture.project_user_password,
                            stack_tenant=self.project_name, logger = self.logger)
        return project_inputs

    def get_connections(self, project_inputs):
        self.project_connections= ContrailConnections(project_inputs,
                                    project_name=self.project_name,
                                    username=self.username,
                                    password=self.password,
                                    logger=self.logger)
        return self.project_connections
# end AdminIsolatedCreds
