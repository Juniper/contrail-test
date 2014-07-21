import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from user_test import UserFixture
from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from project.base import BaseProjectTest
import test
from util import get_random_name

class TestProject(BaseProjectTest):

    @classmethod
    def setUpClass(cls):
        super(TestProject, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestProject, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_project_add_delete(self):
        ''' Validate that a new project can be added and deleted
            1. Create new tenant using keystone and verify it and default SG
            2. Delete tenant and verify
        Pass criteria: Step 1 and 2 should pass
        '''
        result = True
        project_name = get_random_name('project128')
        user_fixture= self.useFixture(UserFixture(
            connections=self.connections, username=self.inputs.stack_user,
            password=self.inputs.stack_password))
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        user_fixture.add_user_to_tenant(project_name, self.inputs.stack_user, 'admin')
        assert project_fixture_obj.verify_on_setup()

        # Check if the default SG is present in it
        connections = project_fixture_obj.get_project_connections()
        neutron_h = self.connections.quantum_fixture
        sgs = neutron_h.list_security_groups(name='default')
        assert len(sgs['security_groups']) == 1,\
            'Default SG is not created in project %s' % (project_name)
        self.logger.info('Default SG is present in the new project')
        return result
    # end test_project_add_delete

