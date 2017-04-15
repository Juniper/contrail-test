import sys
import os
import fixtures
import testtools
import unittest
from vn_test import *
from tcutils.wrappers import preposttest_wrapper
from base import StaticRouteTableBase 
from common import isolated_creds
import test 
from common.servicechain.firewall.verify import VerifySvcFirewall

class TestStaticRouteTables(StaticRouteTableBase, VerifySvcFirewall):
    
    @classmethod
    def setUpClass(cls):
        super(TestStaticRouteTables, cls).setUpClass()

    def setUp(self):
        super(TestStaticRouteTables, self).setUp()
        self.config_basic()
 
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_interface_static_table(self):
        """
        Description: Validate interface static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating interface static table betn left and right vm
                    3.  Apply static table to the middle ports. 
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        self.add_interface_route_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
        self.addCleanup(self.delete_int_route_table)
        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        self.check_route_in_agent(expected_next_hops = 1)
        self.add_interface_route_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
        self.addCleanup(self.delete_int_v6_route_table)
        sport = 8001
        dport = 9001
        self.verify_traffic(
            self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)

        self.check_route_in_agent(expected_next_hops = 1, v6 = True)
    #end test_static_table

    @preposttest_wrapper
    def test_add_delete_interface_static_table(self):

        """
        Description: Validate adding/deleting interface static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating interface static table betn left and right vm
                    3.  Apply static table to the middle ports. Delete the static table. Create it new and reapply 
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        for i in range(1,5):
            self.add_interface_route_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            sport = 8001
            dport = 9001
            self.unbind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            self.bind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            self.verify_traffic(
                self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1)
            self.unbind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            self.delete_int_route_table()

            self.add_interface_route_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            sport = 8001
            dport = 9001
            self.unbind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            self.bind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            self.verify_traffic(
                self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1, v6 = True)
            self.unbind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            self.delete_int_v6_route_table()

    #end test_add_delete_static_table

    @preposttest_wrapper
    def test_bind_unbind_interface_static_table(self):
        """
        Description: Validate bind/unbind interface static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating interface static table betn left and right vm
                    3.  Apply static table to the middle ports.Unbind the table, rebind it to ports.
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        self.add_interface_route_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
        for i in range(1,5):
            sport = 8001
            dport = 9001
            self.unbind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            self.bind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
            self.verify_traffic(
                self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1)
        self.unbind_interface_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
        self.delete_int_route_table()

        self.add_interface_route_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
        for i in range(1,5):
            sport = 8001
            dport = 9001
            self.unbind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            self.bind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
            self.verify_traffic(
                self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1, v6 = True)
        self.unbind_interface_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
        self.delete_int_v6_route_table()

    #end test_bind_unbind_interface_static_table

    @preposttest_wrapper
    def test_add_delete_network_static_table(self):
        """
        Description: Validate add/delete network static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating network static table betn left and right vm
                    3.  Apply static table to the middle ports.Delete the table. Create it fresh and reapply.
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        for i in range(1,5):
            self.add_network_table_to_vn(self.vn1_fixture, self.vn2_fixture)
            sport = 8001
            dport = 9001
            self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)
            self.bind_network_table(self.vn1_fixture, self.vn2_fixture)
            self.verify_traffic(
                self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1)
            self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)
            self.del_nw_route_table()

            self.add_network_table_to_vn(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            sport = 8001
            dport = 9001
            self.unbind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            self.bind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            self.verify_traffic(
                self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1, v6 = True)
            self.unbind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            self.del_nw_v6_route_table()

    #end test_add_delete_static_table

    @preposttest_wrapper
    def test_bind_unbind_network_static_table(self):
        """
        Description: Validate bind/unbind network static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating network static table betn left and right vm
                    3.  Apply static table to the middle ports.Unbind the table, rebind it. 
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        self.add_network_table_to_vn(self.vn1_fixture, self.vn2_fixture)
        for i in range(1,5):
            sport = 8001
            dport = 9001
            self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)
            self.bind_network_table(self.vn1_fixture, self.vn2_fixture)
            self.verify_traffic(
                self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1)
        self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)
        self.del_nw_route_table()

        self.add_network_table_to_vn(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
        for i in range(1,5):
            sport = 8001
            dport = 9001
            self.unbind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            self.bind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
            self.verify_traffic(
                self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)

            self.check_route_in_agent(expected_next_hops = 1, v6 = True)
        self.unbind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture)
        self.del_nw_v6_route_table()

    #end test_bind_unbind_network_static_table

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_network_route_table(self):
        """
        Description: Validate network static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating network static table betn left and right vm
                    3.  Apply static table to the middle ports. 
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """
        sport = 8001
        dport = 9001
        self.add_network_table_to_vn(self.vn1_fixture, self.vn2_fixture)
        self.addCleanup(self.del_nw_route_table)
        self.verify_traffic(
            self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        self.check_route_in_agent(expected_next_hops = 1)
        self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)

        sport = 8001
        dport = 9001
        self.add_network_table_to_vn(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
        self.addCleanup(self.del_nw_v6_route_table)
        self.verify_traffic(
            self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)
        self.check_route_in_agent(expected_next_hops = 1, v6 = True)
        self.unbind_network_table(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)

    @preposttest_wrapper
    def test_with_neutron_router(self):
        """
        Description: Validate interop of neutron router with static table 
        Test steps:
                    1.  Creating vm's - vm1 and vm2 and middle vm in networks vn1 and vn2.
                    2.  Creating interface and network static table betn left and right vm and neutron router
                    3.  Apply static table to the middle ports. 
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and route should be in the agent 
        """

        self.add_network_table_to_vn(self.vn1_fixture, self.vn2_fixture)
        self.add_interface_route_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
        self.neutron_router_test()
        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)
        self.check_route_in_agent(expected_next_hops = 1)

        self.add_network_table_to_vn(self.vn1_v6_fixture, self.vn2_v6_fixture, v6 = True)
        self.add_interface_route_table(self.vn1_v6_fixture, self.vn2_v6_fixture, self.vm1_v6_fixture, v6 = True)
        self.neutron_router_test(v6 = True)
        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.left_v6_vm_fixture, self.right_v6_vm_fixture, 'udp', sport=sport, dport=dport)
        self.check_route_in_agent(expected_next_hops = 1, v6 = True)

    # end test_network_table

