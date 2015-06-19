# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import unittest
import fixtures
import testtools
import traceback

from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import prepost_wrapper
from tcutils.poc import (TemplateTestCase, template, Call)
from test_arguments import *


class TestSanityFixture(testtools.TestCase, fixtures.TestWithFixtures):

    __metaclass__ = TemplateTestCase

#    @classmethod
    def setUp(self):
        super(TestSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
    # end setUpClass

    def cleanUp(self):
        super(TestSanityFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @template(env.test_vn_add_delete_params)
    @preposttest_wrapper
    def test_vn_add_delete(self, vn_name, vn_subnets):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    # end

# end TestSanityFixture
