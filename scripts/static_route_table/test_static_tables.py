from builtins import range
import sys
import os
import fixtures
import testtools
import unittest
from vn_test import *
from tcutils.wrappers import preposttest_wrapper
from common.static_route_table.base import StaticRouteTableBase 
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
 
    @test.attr(type=['sanity','vcenter'])
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

    #end test_bind_unbind_network_static_table

    @test.attr(type=['cb_sanity', 'sanity','vcenter'])
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

    # end test_network_table

