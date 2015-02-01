import os
import sys
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BaseRtFilterTest
from common import isolated_creds
import inspect

import test


class TestBasicRTFilter(BaseRtFilterTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicRTFilter, cls).setUpClass()

    @preposttest_wrapper
    def test_vn_rt_entry(self):
        '''
        Description:  Validate the entry of the VN's Route Target in the rt_group and  bgp.rtarget.0
         table on the control nodes
         Test steps:
                  1. Create a VM in a VN.
                  2. Check the rt_group and  bgp.rtarget.0 table on the control nodes.
         Pass criteria: The route target of the VN and the VM IP should be seen in the respective tab
         les.
         Maintainer : ganeshahv@juniper.net
         '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        route_target = vn1_fixture.rt_names[0]
        for bgp_ip in self.inputs.bgp_ips:
            assert self.verify_rt_group_entry(bgp_ip, route_target)
        self.logger.info(
            'Will create a VM and check that the dep_route is created in the rt_group table')
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                     flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        ip = vm1_fixture.vm_ip + '/32'
        active_ctrl_node = self.get_active_control_node(vm1_fixture)
        assert self.verify_rt_group_entry(active_ctrl_node, route_target)
        assert self.verify_dep_rt_entry(active_ctrl_node, route_target, ip)
        assert self.verify_rtarget_table_entry(active_ctrl_node, route_target)
        return True
    # end test_vn_rt_entry

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_user_def_rt_entry(self):
        '''
        Description: Validate the entry and deletion of the VN's user-added Route Target in the rt_g
        roup and  bgp.rtarget.0 table on the control nodes
        Test steps:
                  1. Create a VM in a VN.
                  2. Add a route-target entry to the VN.
                  3. Check the rt_group and  bgp.rtarget.0 table on the control nodes.
        Pass criteria: The system-defined, user-defined route target of the VN and the VM IP should 
        be seen in the respective tables.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        user_def_rt_num = get_random_rt()
        user_def_rt = "target:%s:%s" % (
            self.inputs.router_asn, user_def_rt_num)
        system_rt = vn1_fixture.rt_names[0]
        routing_instance = vn1_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the VN')
        vn1_fixture.add_route_target(
            routing_instance, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        rt_list = [user_def_rt, system_rt]
        for bgp_ip in self.inputs.bgp_ips:
            for rt in rt_list:
                assert self.verify_rt_group_entry(bgp_ip, rt)
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                     flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        ip = vm1_fixture.vm_ip + '/32'
        active_ctrl_node = self.get_active_control_node(vm1_fixture)
        for rt in rt_list:
            assert self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            assert self.verify_rtarget_table_entry(active_ctrl_node, rt)
        self.logger.info(
            'Will remove the user-defined RT to the VN and verify that the entry is removed from the tables')
        vn1_fixture.del_route_target(
            routing_instance, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        assert self.verify_rt_entry_removal(active_ctrl_node, user_def_rt)
        self.logger.info(
            'Will verify that the system generated RT is still seen in the control-nodes')
        assert self.verify_rt_group_entry(active_ctrl_node, system_rt)
        assert self.verify_dep_rt_entry(active_ctrl_node, system_rt, ip)
        assert self.verify_rtarget_table_entry(active_ctrl_node, system_rt)
        return True
    # end test_user_def_rt_entry

    @preposttest_wrapper
    def test_dep_routes_two_vns_with_same_rt(self):
        '''
        Description: Validate that dep_routes are seen in the RTGroup Table under the route-target w
            hich is common to two different networks
        Test steps:
                 1. Create 2 VNs and a VM in each.
                 2. Add the same RT-entry to both the VNs.
        Pass criteria: dep_routes are seen in the RTGroup Table under the route-target which is comm
            on to two different networks
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn2_name = get_random_name('vn40')
        vn1_subnets = [get_random_cidr()]
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn2_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        assert vn2_fixture.verify_on_setup()
        user_def_rt_num = '11111'
        user_def_rt = "target:%s:%s" % (
            self.inputs.router_asn, user_def_rt_num)
        system_rt1 = vn1_fixture.rt_names[0]
        system_rt2 = vn2_fixture.rt_names[0]
        routing_instance1 = vn1_fixture.ri_name
        routing_instance2 = vn2_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the two VNs')
        vn1_fixture.add_route_target(
            routing_instance1, self.inputs.router_asn, user_def_rt_num)
        vn2_fixture.add_route_target(
            routing_instance2, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                     flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.create_vm(vn2_fixture, vm_name=vn2_vm2_name,
                                     flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm2_fixture.wait_till_vm_is_up()
        ip1 = vm1_fixture.vm_ip + '/32'
        ip2 = vm2_fixture.vm_ip + '/32'
        active_ctrl_node = self.get_active_control_node(vm1_fixture)
        assert self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip1)
        assert self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip2)
        self.logger.info(
            'Will remove the user-defined RT on VN2 and verify that the entry is removed from the tables')
        self.logger.info('The entry for VM1 should still persist')
        vn2_fixture.del_route_target(
            routing_instance2, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        assert self.verify_dep_rt_entry_removal(
            active_ctrl_node, user_def_rt, ip2)
        assert self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip1)
        return True
    # end test_dep_routes_two_vns_with_same_rt
