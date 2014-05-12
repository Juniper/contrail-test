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
from evpn.verify import VerifyEvpnCases

class TestEvpnCases(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures,VerifyEvpnCases ):
    
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
    def test_with_vxlan_encap_l2_ipv6_multicast_traffic(self):
        '''Test l2 multicast with vxlan  encap
        '''
        return self.verify_l2_ipv6_multicast_traffic(encap='vxlan')
    
    @preposttest_wrapper
    def test_with_udp_encap_l2_ipv6_multicast_traffic(self): 
        '''Test l2 multicast with udp encap
        '''
        return self.verify_l2_ipv6_multicast_traffic(encap='udp')
    
    @preposttest_wrapper
    def test_with_gre_encap_l2_ipv6_multicast_traffic(self):
        '''Test l2 multicast with gre encap
        '''
        return self.verify_l2_ipv6_multicast_traffic(encap='gre')
     
    @preposttest_wrapper
    def test_with_vxlan_encap_l2l3_ipv6_multicast_traffic(self):
        '''Test l2 multicast with vxlan encap
        '''
        return self.verify_l2l3_ipv6_multicast_traffic(encap='vxlan')
 
    @preposttest_wrapper
    def test_with_udp_encap_l2l3_ipv6_multicast_traffic(self):
        '''Test l2 multicast with udp encap
        '''
        return self.verify_l2l3_ipv6_multicast_traffic(encap='udp')

    @preposttest_wrapper
    def test_with_gre_encap_l2l3_ipv6_multicast_traffic(self):
        '''Test l2l3 multicast with gre encap
        '''
        return self.verify_l2l3_ipv6_multicast_traffic(encap='gre')
    
    @preposttest_wrapper
    def test_with_vxlan_encap_change_of_l2_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2 to l2l3  with vxlan encap
        '''
        return self.verify_change_of_l2_vn_forwarding_mode(encap='vxlan')
 
    @preposttest_wrapper
    def test_with_gre_encap_change_of_l2_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2 to l2l3 with gre encap
        '''
        return self.verify_change_of_l2_vn_forwarding_mode(encap='gre')

    @preposttest_wrapper
    def test_with_udp_encap_change_of_l2_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2 to l2l3 with udp encap
        '''
        return self.verify_change_of_l2_vn_forwarding_mode(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_encap_change_of_l2l3_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2l3 to l2 with vxlan  encap
        '''
        return self.verify_change_of_l2l3_vn_forwarding_mode(encap='vxlan')

    @preposttest_wrapper
    def test_with_gre_encap_change_of_l2l3_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2l3 to l2 with gre  encap
        '''
        return self.verify_change_of_l2l3_vn_forwarding_mode(encap='gre')

    @preposttest_wrapper
    def test_with_udp_encap_change_of_l2l3_vn_forwarding_mode(self):
        '''Test to verify change of vn forwarding mode from l2l3 to l2 with udp  encap
        '''
        return self.verify_change_of_l2l3_vn_forwarding_mode(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_encap_to_verify_l2_vm_file_trf_by_scp(self):
        '''Test to verify scp of a file with vxlan encap
        '''
        return self.verify_l2_vm_file_trf_by_scp(encap='vxlan')
 
    @preposttest_wrapper
    def test_with_udp_encap_to_verify_l2_vm_file_trf_by_scp(self):
        '''Test to verify scp of a file with udp encap with l2 forwarding mode
        '''
        return self.verify_l2_vm_file_trf_by_scp(encap='udp')

    @preposttest_wrapper
    def test_with_gre_encap_to_verify_l2_vm_file_trf_by_scp(self):
        '''Test to verify scp of a file with gre encap with l2 forwarding mode
        '''
        return self.verify_l2_vm_file_trf_by_scp(encap='gre')
    
    @preposttest_wrapper
    def test_with_gre_encap_ipv6_ping_for_non_ip_communication (self):
        '''Test ping to to IPV6 link local address of VM to check non ip traffic communication using GRE (L2 Unicast)
        '''
        return self.verify_ipv6_ping_for_non_ip_communication(encap='gre')

    @preposttest_wrapper
    def test_with_udp_encap_ipv6_ping_for_non_ip_communication (self):
        '''Test ping to to IPV6 link local address of VM to check non ip traffic communication using UDP(L2 Unicast)
        '''
        return self.verify_ipv6_ping_for_non_ip_communication(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_encap_ipv6_ping_for_non_ip_communication (self):
        '''Test ping to to IPV6 link local address of VM to check non_ip traffic communication using VXLAN(L2 Unicast)
        '''
        return self.verify_ipv6_ping_for_non_ip_communication(encap='vxlan')

    @preposttest_wrapper
    def test_with_gre_encap_ipv6_ping_for_configured_ipv6_address (self):
        '''Test ping to to configured IPV6 address  of VM with encap gre
        '''
        return self.verify_ping_to_configured_ipv6_address(encap='gre')

    @preposttest_wrapper
    def test_with_udp_encap_ipv6_ping_for_configured_ipv6_address (self):
        '''Test ping to to configured IPV6 address  of VM with encap udp
        '''
        return self.verify_ping_to_configured_ipv6_address(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_encap_ipv6_ping_for_configured_ipv6_address (self):
        '''Test ping to to configured IPV6 address  of VM with encap VXLAN
        '''
        return self.verify_ping_to_configured_ipv6_address(encap='vxlan')

    @preposttest_wrapper
    def test_with_gre_encap_agent_restart (self):
        '''Test agent restart with GRE Encap
        '''
        return self.verify_epvn_with_agent_restart(encap='gre')

    @preposttest_wrapper
    def test_with_udp_encap_agent_restart (self):
        '''Test agent restart with UDP Encap
        '''
        return self.verify_epvn_with_agent_restart(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_encap_agent_restart (self):
        '''
         Description:Test agent restart with VXLAN Encap
             1. Configure VXLAN as highest priority
             2. Configure 2 VM under a VN configured with l2-l3 mode
             3. Check IPV6 (non ip) communication between them
             4. Restart the contrail-grouter service.
             5. Again check the  IPV6 (non ip) communication between them.
         Pass criteria:  Step 3 and 5 should pass
         Maintainer: chhandak@juniper.net 
        '''
        return self.verify_epvn_with_agent_restart(encap='vxlan')

    @preposttest_wrapper
    def test_with_gre_l2_mode (self):
        '''Test L2 forwarding mode with GRE Encap
        '''
        return self.verify_epvn_l2_mode(encap='gre')

    @preposttest_wrapper
    def test_with_udp_l2_mode (self):
        '''Test L2 forwarding mode with UDP Encap
        '''
        return self.verify_epvn_l2_mode(encap='udp')

    @preposttest_wrapper
    def test_with_vxlan_l2_mode (self):
        '''
          Description:  Verify IPv6 (non IP communication) between 2 VM which under a VN configured in L2 only mode
          Test Steps:
               1.VXLAN configured as highest encapsulation priority.
               2.Configured 2 VN . EVPN-MGMT-VN(configured with default l2-l3 mode ) and EVPN-L2-VN (configured with L2 only mode)
               3.Create 2 Vms. Both connected to all 2 VN. Connection with EVPN-MGMT-VN is only to access to VM
               4.Configured IPv6 address on interface which is connected L2 only vn
               5.Check the IPv6 communication between them.

         Pass criteria:  Step 5 should pass
         Maintainer: chhandak@juniper.net
        '''
        return self.verify_epvn_l2_mode(encap='vxlan') 
