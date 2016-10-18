import sys
import os
import fixtures
import testtools
import unittest
import time
from vn_test import *
from vnc_api_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from base import BaseECMPRestartTest 
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
from common import isolated_creds
import test
from tcutils.contrail_status_check import *
from tcutils.tcpdump_utils import *
from tcutils.commands import *
import re
from common.servicechain.firewall.verify import VerifySvcFirewall

class TestECMPHash(BaseECMPRestartTest, VerifySvcFirewall, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPHash, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    def is_test_applicable(self):
        return (True, None)

    def setUp(self):
        super(TestECMPHash, self).setUp()
        self.config_basic()
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)

    @preposttest_wrapper
    def test_ecmp_hash_precedence(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2 
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """

        sport = 8001
        dport = 9001
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True}
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True

    # end test_ecmp_hash_precedence

    @preposttest_wrapper
    def test_source_port(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces() 
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        old_path = self.get_which_path_is_being_taken()

        sport = 8002
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        new_path = self.get_which_path_is_being_taken() 

        assert (old_path == new_path), 'Source port not in ecmp calculation, yet traffic switches over'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'        
    
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        available_ecmp_paths = {} 
        available_ecmp_paths[self.current_tap[0]]=0
        available_ecmp_paths[self.current_tap[1]]=0
        available_ecmp_paths[self.current_tap[2]]=0

        for i in range(8002,8062):
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=i, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1

        assert (available_ecmp_paths[self.current_tap[0]] > 18 and available_ecmp_paths[self.current_tap[1]] > 18 and available_ecmp_paths[self.current_tap[2]] > 18), 'Traffic not distributed correctly across ecmp paths'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_source_port

    @preposttest_wrapper
    def test_destination_port(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """
        ecmp_hashing_include_fields = {"destination_ip": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        old_path = self.get_which_path_is_being_taken()

        sport = 8001
        dport = 9002
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        new_path = self.get_which_path_is_being_taken()

        assert (old_path == new_path), 'Destination port not in ecmp calculation, yet traffic switches over'
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        available_ecmp_paths = {}     
        available_ecmp_paths[self.current_tap[0]]=0
        available_ecmp_paths[self.current_tap[1]]=0
        available_ecmp_paths[self.current_tap[2]]=0
        
        for i in range(9102,9162):
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=i, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1

        assert (available_ecmp_paths[self.current_tap[0]] > 18 and available_ecmp_paths[self.current_tap[1]] > 18 and available_ecmp_paths[self.current_tap[2]] > 18), 'Traffic not distributed correctly across ecmp paths'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_destination_port

    @preposttest_wrapper
    def test_destination_ip(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """
        ecmp_hashing_include_fields = {"destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l4-protocol,l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        old_path = self.get_which_path_is_being_taken()

        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.vm4_fixture, 'udp', sport=sport, dport=dport)
        new_path = self.get_which_path_is_being_taken()

        assert (old_path == new_path), 'Destination ip not in ecmp calculation, yet traffic switches over'
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        available_ecmp_paths = {}     
        available_ecmp_paths[self.current_tap[0]]=0
        available_ecmp_paths[self.current_tap[1]]=0
        available_ecmp_paths[self.current_tap[2]]=0
        
        for i in range(1,30):
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.vm4_fixture, 'udp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1

        assert (available_ecmp_paths[self.current_tap[0]] > 18 and available_ecmp_paths[self.current_tap[1]] > 18 and available_ecmp_paths[self.current_tap[2]] > 18), 'Traffic not distributed correctly across ecmp paths'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_destination_ip

    @preposttest_wrapper
    def test_source_ip(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        old_path = self.get_which_path_is_being_taken()

        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.vm3_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        new_path = self.get_which_path_is_being_taken()

        assert (old_path == new_path), 'Destination ip not in ecmp calculation, yet traffic switches over'
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        available_ecmp_paths = {}
        available_ecmp_paths[self.current_tap[0]]=0
        available_ecmp_paths[self.current_tap[1]]=0
        available_ecmp_paths[self.current_tap[2]]=0

        for i in range(1,30):
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.vm3_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1

        assert (available_ecmp_paths[self.current_tap[0]] > 18 and available_ecmp_paths[self.current_tap[1]] > 18 and available_ecmp_paths[self.current_tap[2]] > 18), 'Traffic not distributed correctly across ecmp paths'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_source_ip

    @preposttest_wrapper
    def test_l4_protocol(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        old_path = self.get_which_path_is_being_taken()

        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'tcp', sport=sport, dport=dport)
        new_path = self.get_which_path_is_being_taken()

        assert (old_path == new_path), 'l4 protocol not in ecmp calculation, yet traffic switches over'
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)

        available_ecmp_paths = {}
        available_ecmp_paths[self.current_tap[0]]=0
        available_ecmp_paths[self.current_tap[1]]=0
        available_ecmp_paths[self.current_tap[2]]=0

        for i in range(1,30):
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1
            self.check_all_ecmpinterfaces()
            self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'tcp', sport=sport, dport=dport, count = 2)
            current_ecmp_path = self.get_which_path_is_being_taken()
            available_ecmp_paths[current_ecmp_path] += 1

        assert (available_ecmp_paths[self.current_tap[0]] > 18 and available_ecmp_paths[self.current_tap[1]] > 18 and available_ecmp_paths[self.current_tap[2]] > 18), 'Traffic not distributed correctly across ecmp paths'

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_l4_protocol

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_vrouter(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        for node in self.inputs.compute_ips:
             self.inputs.restart_service('supervisor-vrouter', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_svc_in_network_restart_vrouter

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_schema(self):
        """
         Description: Validate ECMP Hash
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating 4 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and apply it to ports of these 4 vm instances.
           4.   Checking for ECMP parameters, ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and traffic should reach vm2 from vm1.
        """

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(self.vn1_fixture, self.vn2_fixture, self.left_vm_fixture, self.right_vm_fixture, ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        for node in self.inputs.cfgm_ips:
             self.inputs.restart_service('contrail-schema', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic(self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_svc_in_network_restart_schema

