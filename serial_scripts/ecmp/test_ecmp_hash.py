'''
Script Description: Non-SI ecmp hash script with static tables

Where will it run: No restrictions, should run on single node and multi node

Which release supported: R3.1 onwards

Testing Summary:

There are 5 ECMP hash parameters, so there are 5 testcases for each parameter. The rest of the testcases deal with vrouter restart, schema restart and precedence among different hash configurables.

Testing Topology: 2 left vms, 3 ecmp vms, 2 right vms
Create relevant covering static routes on left and right sides. Change ecmp hash parameters on global, network and port levels and confirm which ecmp paths traffic takes.
'''

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
    # end runTest

    def is_test_applicable(self):
        return (True, None)

    def setUp(self):
        super(TestECMPHash, self).setUp()
        # Create VMs and static tables. Attach them to the ports on both sides.
        self.config_basic()
        # Initialize hit counters
        self.available_ecmp_paths = {}
        # Initialize global hash parameters to all possible hashables
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)

    @preposttest_wrapper
    def test_source_port(self):
        """
         Description: Validate source-port ECMP Hash parameter
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change source-port ECMP parameter, try ping and udp traffic between left-vm and right-vm.
         Pass criteria: With no source-port in calculations, traffic should not switch. With source-port in calculations, the total traffic hit count should equal the total sent count.
        """

        # Remove source-port in ECMP hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify if the hash values reflects in the introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        # Try different source-ports, making sure traffic doesn't switch each
        # time
        for i in range(8001, 8005):
            old_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport=i,
                dport='9001',
                protocol='udp')

            new_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport=i,
                dport='9001',
                protocol='udp')

            assert (old_path_taken == new_path_taken), \
                    'Source port not in ecmp calculation, yet traffic switches over'

        # Include source-port in ECMP hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.initialize_hit_counters()

        # Try with different source-ports now. Display switch statistics
        for i in range(8002, 8062):
            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport=i,
                dport='9001',
                protocol='udp')

        self.ecmp_stats_with_hit_count_check()

        # Revert the config back to default
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_source_port

    @preposttest_wrapper
    def test_destination_port(self):
        """
         Description: Validate destination ECMP Hash parameter
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change destination-port ECMP parameter, try ping and udp traffic between left-vm and right-vm.
         Pass criteria: With no destination-port in calculations, traffic should not switch. With destination-port in calculations, the total traffic hit count should equal the total sent count.
        """

        # Remove destination port from ECMP hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify hash reflects correctly in introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        # Try with different destination ports, making sure traffic doesn't
        # switch
        for i in range(9001, 9005):
            old_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport=i,
                protocol='udp')

            new_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport=i,
                protocol='udp')

            assert (old_path_taken == new_path_taken), \
                    'Destination port not in ecmp calculation, yet traffic switches over'

        # Include destination port back
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.initialize_hit_counters()

        # Try with different destination-ports now. Display switch statistics
        for i in range(9102, 9162):
            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport=i,
                protocol='udp')

        self.ecmp_stats_with_hit_count_check()

        # Revert back to default
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_destination_port

    @preposttest_wrapper
    def test_destination_ip(self):
        """
         Description: Validate destination-ip ECMP Hash parameters
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change destination-ip ECMP parameter, try ping and udp traffic between left-vm and right-vm.
         Pass criteria: With no destination-ip in calculations, traffic should not switch. With destination-ip in calculations, the total traffic hit count should equal the total sent count.
        """

        # Remove destination ip from ECMP hash
        ecmp_hashing_include_fields = {
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # verify if it reflects in introspect
        ecmp_hashing_include_fields = 'l3-source-address,l4-protocol,\
                                       l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        # try with different destination-ips, making sure traffic doesn't
        # switch
        for i in range(1, 3):
            old_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            new_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.vm4_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            assert (old_path_taken == new_path_taken), \
                    'Destination ip not in ecmp calculation, yet traffic switches over'

        # Include destination-ip back in hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.initialize_hit_counters()

        # Try with different destination-ips now, display switch statistics
        for i in range(1, 30):
            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.vm4_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

        self.ecmp_stats_with_hit_count_check()

        # Revert it back to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_destination_ip

    @preposttest_wrapper
    def test_source_ip(self):
        """
         Description: Validate source-ip ECMP Hash parameters
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change source-ip ECMP parameter, try ping and udp traffic between left-vm and right-vm.
         Pass criteria: With no source-ip in calculations, traffic should not switch. With source-ip in calculations, the total traffic hit count should equal the total sent count.
        """

        # Remove source-ip from hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify if it reflects in the introspect
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,\
                                       l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        # Try with different source-ips, making sure traffic doesn't switch
        for i in range(1, 3):
            old_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            new_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.vm3_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            assert (old_path_taken == new_path_taken), \
                    'Source ip not in ecmp calculation, yet traffic switches over'

        # Include source-ip back to hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.initialize_hit_counters()

        # Try with different source-ips now. Display switch statistics
        for i in range(1, 30):
            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            self.send_traffic_and_update_hit_count(
                sender=self.vm3_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

        self.ecmp_stats_with_hit_count_check()

        # Revert back to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_source_ip

    @preposttest_wrapper
    def test_l4_protocol(self):
        """
         Description: Validate l4-ptotocol ECMP Hash parameters
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change l4-protocol ECMP parameter, try ping and udp traffic between left-vm and right-vm.
         Pass criteria: With no l4-protocol in calculations, traffic should not switch. With l4-protocol in calculations, the total traffic hit count should equal the total sent count.
        """

        # Remove l4-protocol from hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify if it reflects in the introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-source-port,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        # Send traffic with udp and tcp alternatively, making sure traffic
        # doesn't switch
        for i in range(1, 5):
            old_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            new_path_taken = self.send_traffic_and_return_path_taken(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='tcp')

            assert (old_path_taken == new_path_taken), \
                    'Destination port not in ecmp calculation, yet traffic switches over'

        # Add l4-protocol back to hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.initialize_hit_counters()

        # Send traffic with udp and tcp alternatively now. Display switch
        # statistics
        for i in range(1, 30):
            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='udp')

            self.send_traffic_and_update_hit_count(
                sender=self.left_vm_fixture,
                receiver=self.right_vm_fixture,
                sport='8001',
                dport='9001',
                protocol='tcp')

        self.ecmp_stats_with_hit_count_check()

        # Revert it back to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_l4_protocol

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ecmp_hash_precedence(self):
        """
         Description: Validate precedence in ECMP Hash parameters
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Change global, network and port ECMP parameters, check their precedence.
         Pass criteria: Port ECMP > Network ECMP > Global ECMP.
        """

        # Send traffic to check for topology sanity
        sport = 8001
        dport = 9001
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Change global hash parameters
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True}
        self.config_all_hash(ecmp_hashing_include_fields)

        # Verify if it reflects in the introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Change network hash parameters
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True}
        self.update_hash_on_network(
            ecmp_hash=ecmp_hashing_include_fields,
            vn_fixture=self.vn1_fixture)

        # Verify if it reflects in the introspect and takes precedence
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,\
                                       l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Change port hash parameters
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify if it reflects in the introspect and takes precedence
        ecmp_hashing_include_fields = 'l3-destination-address,l4-destination-port,'
        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)

        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Revert it to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True

    # end test_ecmp_hash_precedence

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_vrouter(self):
        """
         Description: Validate traffic with ECMP Hash parameters after vrouter restart
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Restart vrouter. Send traffic.
         Pass criteria: Traffic should pass after restart.
        """

        # Configure hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify it reflects in the introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Restart vrouter
        for node in self.inputs.compute_ips:
            self.inputs.restart_service('supervisor-vrouter', [node])
            cluster_status, error_nodes = ContrailStatusChecker(
            ).wait_till_contrail_cluster_stable()
            assert cluster_status, 'Hash of error nodes and services : %s' % (
                error_nodes)

        # check for traffic now
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Restore to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_svc_in_network_restart_vrouter

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_schema(self):
        """
         Description: Validate traffic with ECMP Hash parameters after schema restart
         Test steps:
           1.   Creating vm's - left-vm and right-vm in networks vn1 and vn2.
           2.   Creating 3 instances with legs in vn1 and vn2
           3.   Create static table entries for right vm ip and left vm ip and apply it to ports of these 3 vm instances.
           4.   Restart schema. Send traffic.
         Pass criteria: Traffic should pass after restart.
        """

        # Configure hash
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm1_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm2_fixture)
        self.update_hash_on_port(
            ecmp_hash=ecmp_hashing_include_fields,
            vm_fixture=self.vm5_fixture)

        # Verify it reflects in the introspect
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,\
                                       l4-protocol,l4-source-port,l4-destination-port,'

        self.verify_if_hash_changed(
            self.vn1_fixture,
            self.vn2_fixture,
            self.left_vm_fixture,
            self.right_vm_fixture,
            ecmp_hashing_include_fields)
        sport = 8001
        dport = 9001
        self.check_all_ecmpinterfaces()
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Restart schema
        for node in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-schema', [node])
            cluster_status, error_nodes = ContrailStatusChecker(
            ).wait_till_contrail_cluster_stable()
            assert cluster_status, 'Hash of error nodes and services : %s' % (
                error_nodes)

        # Now send traffic and check
        self.verify_traffic(
            self.left_vm_fixture,
            self.right_vm_fixture,
            'udp',
            sport=sport,
            dport=dport)

        # Restore to defaults
        ecmp_hashing_include_fields = {
            "destination_ip": True,
            "destination_port": True,
            "hashing_configured": True,
            "ip_protocol": True,
            "source_ip": True,
            "source_port": True}

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_svc_in_network_restart_schema
# end class TestECMPHash
