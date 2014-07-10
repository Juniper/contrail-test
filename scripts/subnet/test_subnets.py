# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from subnet.base import BaseSubnetTest
import test

class TestSubnets(BaseSubnetTest):

    @classmethod
    def setUpClass(cls):
        super(TestSubnets, cls).setUpClass()

    def runTest(self):
        pass

    @classmethod
    def tearDownClass(cls):
        super(TestSubnets, cls).tearDownClass()

#    @test.attr(type='abcd')
    @preposttest_wrapper
    def test_subnet_host_routes(self):
        '''Validate host_routes parameter in subnet
        Create a VN with subnet having a host-route
        Create a VM using that subnet
        Check the route table in the VM
        
        '''
        result = True
        vn1_name = 'vn30'
        dest_ip = '8.8.8.8'
        destination = dest_ip + '/32'
        nh = '30.1.1.10'
        vn1_subnets = [{'cidr': '30.1.1.0/24',
                       'host_routes': [{'destination': destination,
                                       'nexthop': nh},
                                       {'destination': '0.0.0.0/0',
                                       'nexthop': '30.1.1.1'}],
                       }]
        vn1_vm1_name = 'vm1'
        vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            vn_name=vn1_name,
            inputs=self.inputs,
            subnets=vn1_subnets))
        vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            vn_obj=vn1_fixture.obj,
            vm_name=vn1_vm1_name, ))
        vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        cmd_output = output.values()[0]
        assert dest_ip in cmd_output, "Host route not seen in Routetable"
        self.logger.info('Host routes are seen on the VM..ok')
    # end test_subnet_host_routes
