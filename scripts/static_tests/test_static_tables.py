#import traffic_tests
import sys
import os
import fixtures
import testtools
import unittest
import time
from vn_test import *
from vnc_api import vnc_api as my_vnc_api
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from common.servicechain.verify import VerifySvcChain 
from common.policy.config import ConfigPolicy
#sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
#from traffic.core.stream import Stream
#from traffic.core.profile import create, ContinuousProfile, ContinuousSportRange
#from traffic.core.helpers import Host
#from traffic.core.helpers import Sender, Receiver
from base import StaticTableBase 
from fabric.state import connections as fab_connections
from common import isolated_creds
import inspect
import test 

class TestStaticTables(StaticTableBase, VerifySvcFirewall):
    
    @classmethod
    def setUpClass(cls):
        super(TestStaticTables, cls).setUpClass()

    def runTest(self):
        pass    
    #end runTest

    def setUp(self):
        super(TestStaticTables, self).setUp()
        self.config_basic()
 
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_interface_static_table(self):

        #self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)

        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        self.add_interface_route_table()

        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        self.detach_policy(self.vn1_policy_fix)
        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        (domain, project, vn) = self.vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[self.vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = self.vm1_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=self.vm2_fixture.vm_ip, prefix='32')['path_list'][0]['nh']['mc_list']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info('Route found in the Agent %s' % vm2_fixture.vm_node_ip)

        if (len(next_hops) != 3):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')

        self.vn1_policy_fix = self.attach_policy_to_vn(self.pol1_fixture, self.vn1_fix)
        return True

    # end test_static_table

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_network_table(self):

        sport = 8001
        dport = 9001

        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        self.add_network_table_to_vn()

        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        self.detach_policy(self.vn1_policy_fix)
        self.verify_traffic(
            self.vm1_fixture, self.vm2_fixture, 'udp', sport=sport, dport=dport)

        self.vnc_lib.virtual_network_update(vn_rt_obj)
        (domain, project, vn) = self.vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[self.vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = self.vm1_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=self.vm2_fixture.vm_ip, prefix='32')['path_list'][0]['nh']['mc_list']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info('Route found in the Agent %s' % vm2_fixture.vm_node_ip)

        if (len(next_hops) != 3):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')
        self.vn1_policy_fix = self.attach_policy_to_vn(self.pol1_fixture, self.vn1_fix)
        return True

    def test_with_neutron_router(self):
        self.test_interop_with_neutron_router()

    # end test_network_table

