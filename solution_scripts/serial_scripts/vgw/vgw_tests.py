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
import fixtures
import testtools
import unittest

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
from testresources import ResourcedTestCase
from vgw_test_resource import SolnSetupResource
import traffic_tests
from vgw.verify import VerifyVgwCases


class TestVgwCases(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures, VerifyVgwCases):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_h = self.res.nova_h
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(TestVgwCases, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(TestVgwCases, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_vgw_with_fip_on_same_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM got FIP from VGW network
        '''
        return self.verify_vgw_with_fip(compute_type='same')

    @preposttest_wrapper
    def test_vgw_with_fip_on_different_node(self):
        '''Test VM is launched on the different compute node where VGW is configured and VM got FIP from VGW network
        '''
        return self.verify_vgw_with_fip(compute_type='different')

    @preposttest_wrapper
    def test_vgw_with_native_vm_on_same_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM is launched on VGW network
        '''
        return self.verify_vgw_with_native_vm(compute_type='same')

    @preposttest_wrapper
    def test_vgw_with_native_vm_on_different_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM is laucnhed on VGW network
        '''
        return self.verify_vgw_with_native_vm(compute_type='different')

    @preposttest_wrapper
    def test_vgw_with_multiple_subnet_for_single_vgw(self):
        '''Test VGW having multiple subnet is working properly
        '''
        return self.verify_vgw_with_multiple_subnet()

    @preposttest_wrapper
    def test_vgw_with_restart_of_vgw_node(self):
        '''Test VGW with restarting the VGW node
        '''
        return self.vgw_restart_of_vgw_node()
