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

        self.add_interface_route_table(self.vn1_fixture, self.vn2_fixture, self.vm1_fixture)
        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        self.check_route_in_agent(expected_next_hops = 1)

    #end test_static_table

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_network_route_table(self):

        sport = 8001
        dport = 9001

        self.add_network_table_to_vn(self.vn1_fixture, self.vn2_fixture)

        self.verify_traffic(
            self.left_vm_fixture, self.right_vm_fixture, 'udp', sport=sport, dport=dport)

        self.check_route_in_agent(expected_next_hops = 1)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_with_neutron_router(self):
        self.test_interop_with_neutron_router()

    # end test_network_table

