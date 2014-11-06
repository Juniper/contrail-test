# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools

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
from tcutils.wrappers import preposttest_wrapper

from testresources import OptimisingTestSuite, TestResource, ResourcedTestCase


class SolnSetup(object):

    def __init__(self, test_resource):
        self.test_resource = test_resource

    def setUp(self):
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = ContrailTestInit(self.ini_file)
        self.inputs.setUp()
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        return self
    # end setUp

    def tearDown(self):
        pass

    def dirtied(self):
        self.test_resource.dirtied(self)


class _SolnSetupResource(TestResource):

    def make(self, dependencyresource):
        mysetup = SolnSetup(self)
        mysetup.setUp()
        return mysetup
    # end make

    def clean(self, mysetup):
        mysetup.tearDown()
    # end

SolnSetupResource = _SolnSetupResource()


class SolnTest(ResourcedTestCase, fixtures.TestWithFixtures):

    resources = [('mysetup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    # end

    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete

# end SolnTest
