import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from user_test import UserFixture
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from project.base import BaseProjectTest
import test
from tcutils.util import get_random_name
from vnc_api.vnc_api import NoIdError

class TestProjectBasic(BaseProjectTest):

    @classmethod
    def setUpClass(cls):
        super(TestProjectBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestProjectBasic, cls).tearDownClass()

    @test.attr(type=['sanity', 'ci_sanity', 'suite1'])
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
            connections=self.admin_connections,
            username=self.inputs.admin_username, 
            password=self.inputs.admin_password))
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=self.inputs.admin_username,
            password=self.inputs.admin_password,
            project_name=project_name,
            connections=self.admin_connections))
        user_fixture.add_user_to_tenant(project_name,
            self.inputs.admin_username,
            'admin')
        assert project_fixture_obj.verify_on_setup()

        # Check if the default SG is present in it
        try:
            secgroup = self.vnc_lib.security_group_read(
                fq_name=[u'default-domain', project_name, 'default'])
            self.logger.info('Default SG is present in the new project')
        except NoIdError:
            assert False, "Default SG is not created in project %s" % (project_name)
        return result
    # end test_project_add_delete

