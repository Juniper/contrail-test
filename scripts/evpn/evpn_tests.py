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
import fixtures
import testtools
import unittest

from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from evpn_test_resource import SolnSetupResource
import traffic_tests

class TestEvpnCases(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures ):
    
    resources = [('base_setup', SolnSetupResource)]
    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res= SolnSetupResource.getResource()
        self.inputs= self.res.inputs
        self.connections= self.res.connections
        self.logger= self.res.logger
        self.nova_fixture= self.res.nova_fixture
        self.agent_inspect= self.connections.agent_inspect
        self.cn_inspect= self.connections.cn_inspect
        self.analytics_obj=self.connections.analytics_obj
        self.vnc_lib= self.connections.vnc_lib
    
    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)
    
    def setUp(self):
        super (TestEvpnCases, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
    
    def tearDown(self):
        print "Tearing down test"
        super (TestEvpnCases, self).tearDown()
        SolnSetupResource.finishedWith(self.res)
    
    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def test_ipv6_ping_for_non_ip_communication (self):
        '''Test ping to to IPV6 link local address of VM to check non_ip traffic_communication(L2 Unicast)
        '''
        result= True
        out=self.connections.read_vrouter_config_evpn()
        if out == True:
            vn1_fixture= self.res.vn1_fixture
            vn2_fixture= self.res.vn2_fixture
            vn1_vm1_fixture= self.res.vn1_vm1_fixture
            vn1_vm2_fixture= self.res.vn1_vm2_fixture
            vm1_name= self.res.vn1_vm1_name
            vm2_name= self.res.vn1_vm2_name
            vn1_name= self.res.vn1_name
            vn1_subnets= self.res.vn1_subnets
            assert vn1_fixture.verify_on_setup()
            assert vn2_fixture.verify_on_setup()
            assert vn1_vm1_fixture.verify_on_setup()
            assert vn1_vm2_fixture.verify_on_setup()
            sleep(10)
            vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm()
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        else: 
            self.logger.error('EVPN is not getting enabled in global vrouter')
            assert out            
        return True
    #end test_ipv6_ping_for_non_ip_communication
  
    @preposttest_wrapper
    def test_ping_to_configured_ipv6_address (self):
        '''Configure IPV6 address to VM. Test IPv6 ping to that address.
        '''
        result= True
        vn1_vm1= '1001::1/64'
        vn1_vm2= '1001::2/64'
        out=self.connections.read_vrouter_config_evpn()
        if out == True:
            vn1_fixture= self.res.vn1_fixture
            vn2_fixture= self.res.vn2_fixture
            vn1_vm1_fixture= self.res.vn1_vm1_fixture
            vn1_vm2_fixture= self.res.vn1_vm2_fixture
            vm1_name= self.res.vn1_vm1_name
            vm2_name= self.res.vn1_vm2_name
            vn1_name= self.res.vn1_name
            vn1_subnets= self.res.vn1_subnets
            assert vn1_fixture.verify_on_setup()
            assert vn2_fixture.verify_on_setup()
            assert vn1_vm1_fixture.verify_on_setup()
            assert vn1_vm2_fixture.verify_on_setup()
            cmd_to_pass1=['ifconfig eth0 inet6 add %s' %(vn1_vm1)]
            vn1_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1)
            cmd_to_pass2=['ifconfig eth0 inet6 add %s' %(vn1_vm2)]
            vn1_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2)
            vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm(addr_type='global')
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm(addr_type='global')
            assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        else:
            self.logger.error('EVPN is not getting enabled in global vrouter')
            assert out
        return True
    #end test_ping_to_configured_ipv6_address

    @preposttest_wrapper
    def test_epvn_with_agent_restart (self):
        '''Restart the vrouter service and verify the impact on L2 route
        '''
        result= True
        out=self.connections.read_vrouter_config_evpn()
        if out == True:
            vn1_fixture= self.res.vn1_fixture
            vn2_fixture= self.res.vn2_fixture
            vn1_vm1_fixture= self.res.vn1_vm1_fixture
            vn1_vm2_fixture= self.res.vn1_vm2_fixture
            vm1_name= self.res.vn1_vm1_name
            vm2_name= self.res.vn1_vm2_name
            vn1_name= self.res.vn1_name
            vn1_subnets= self.res.vn1_subnets
            assert vn1_fixture.verify_on_setup()
            assert vn2_fixture.verify_on_setup()
            assert vn1_vm1_fixture.verify_on_setup()
            assert vn1_vm2_fixture.verify_on_setup()
            vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm()
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            self.logger.info('Checking the communication between 2 VM using ping6 to VM link local address from other VM')
            assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
            self.logger.info('Will restart compute  services now')
            for compute_ip in self.inputs.compute_ips:
                self.inputs.restart_service('contrail-vrouter',[compute_ip])
            sleep(10)
            self.logger.info('Verifying L2 route and other VM verification after restart')
            assert vn1_vm1_fixture.verify_on_setup()
            assert vn1_vm2_fixture.verify_on_setup()
            vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm()
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            self.logger.info('Checking the communication between 2 VM after vrouter restart')
            assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        else:
            self.logger.error('EVPN is not getting enabled in global vrouter')
            assert out
        return True
    #end test_ipv6_ping_for_non_ip_communication
#
