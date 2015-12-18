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
from scripts.rt_filter.base import BaseRtFilterTest
from common import isolated_creds
import inspect

import test


class TestBasicRTFilterRestart(BaseRtFilterTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicRTFilterRestart, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_rt_entry_persistence_across_restarts(self):
        '''
        Description: Validate the persistence of Route Target entry in the rt_group and bgp.rtarget.
        0 table on the control nodes
        across control-node/agent service restarts
        Test steps:
                 1. Create a VM in a VN.
                 2. Add a route-target entry to the VN.
                 3. Check the rt_group and  bgp.rtarget.0 table on the control nodes.
                 4. Restart the contrail-control amd contrail-vrouter services.
        Pass criteria: The system-defined, user-defined route target of the VN and the VM IP should 
            be seen in the respective tables, even after the restarts.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                     flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()

        user_def_rt_num = '11111'
        user_def_rt = "target:%s:%s" % (
            self.inputs.router_asn, user_def_rt_num)
        system_rt = vn1_fixture.rt_names[0]
        routing_instance = vn1_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the VN')
        vn1_fixture.add_route_target(
            routing_instance, self.inputs.router_asn, user_def_rt_num)
        sleep(10)
        ip = vm1_fixture.vm_ip + '/32'
        active_ctrl_node = self.get_active_control_node(vm1_fixture)

        rt_list = [user_def_rt, system_rt]
        self.logger.info(
            'Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            assert self.verify_rt_group_entry(active_ctrl_node, rt)
            assert self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            assert self.verify_rtarget_table_entry(active_ctrl_node, rt)

        self.logger.info(
            'Will restart contrail-vrouter service and check if the RT entries persist')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)
        self.logger.info(
            'Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            assert self.verify_rt_group_entry(active_ctrl_node, rt)
            assert self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            assert self.verify_rtarget_table_entry(active_ctrl_node, rt)

        self.logger.info(
            'Will restart contrail-control service and check if the RT entries persist')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)
        self.logger.info(
            'Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            assert self.verify_rt_group_entry(active_ctrl_node, rt)
            assert self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            assert self.verify_rtarget_table_entry(active_ctrl_node, rt)
        return True
    # end test_rt_entry_persistence_across_restarts

    @preposttest_wrapper
    def test_vpnv4_route_entry_only_on_RT_interest_receipt(self):
        '''
        Description: Validate the presence of route in the bgp.l3vpn.0 table only when a RT interest
         is generated
        Test steps:
                 0. Check env variable MX_GW_TEST is set to 1. This confirms MX presence in the setup.
                 1. Create a VM in a VN.
                 2, Enable control-node peering with MX.
                 3. Check that with RT-Filtering enabled, MX should be seen in the peers_interested list of the RT.
                 4. Disable RT_filter Address family between control-nodes and MX.
                 5. MX should be removed from the peers interested list after removing RT-filtering family.
                 6. Re-enable RT_filter Address family between control-nodes and MX
        Pass criteria: Mx should be seen in the peers_interested list
        Maintainer : ganeshahv@juniper.net
        '''
        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):

            vn1_name = get_random_name('vn30')
            vn1_subnets = [get_random_cidr()]
            vn1_vm1_name = get_random_name('vm1')
            vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                         flavor='contrail_flavor_small', image_name='ubuntu-traffic')
            assert vm1_fixture.wait_till_vm_is_up()
            result = True
            peers1 = []
            peers2 = []
            peers3 = []
            active_ctrl_node = self.get_active_control_node(vm1_fixture)
            system_rt = vn1_fixture.rt_names[0]
            self.logger.info('The system-generated RT is %s' % system_rt)
            ip = vm1_fixture.vm_ip + '/32'
            user_def_rt = "target:%s:%s" % (
                self.inputs.router_asn, self.inputs.mx_rt)
            routing_instance = vn1_fixture.ri_name
            self.logger.info('Will add RT %s to the RI %s' %
                             (user_def_rt, routing_instance))
            vn1_fixture.add_route_target(
                routing_instance, self.inputs.router_asn, self.inputs.mx_rt)
            sleep(10)
            active_ctrl_node = self.get_active_control_node(vm1_fixture)
            peers1 = self.cn_inspect[active_ctrl_node].get_cn_rtarget_group(
                user_def_rt)['peers_interested']
            self.logger.info(
                'There are %s peers interested in RT %s' % (len(peers1), user_def_rt))
            self.logger.info('They are %s' % peers1)
            if self.inputs.ext_routers[0][0] in peers1:
                self.remove_rt_filter_family()
                self.logger.info(
                    '*Will disable RT_filter Address family between control-nodes and MX*')
                sleep(10)
                peers2 = self.cn_inspect[active_ctrl_node].get_cn_rtarget_group(
                    user_def_rt)['peers_interested']
                self.logger.info('After disabling RT_filter, there are %s peers interested in RT %s' % (
                    len(peers2), user_def_rt))
                self.logger.info('They are %s' % peers2)
                if len(peers1) > len(peers2):
                    mx = list(set(peers1) - set(peers2))
                    self.logger.info(
                        '%s is removed from the peers_interested list' % mx)
                else:
                    result = False
                    assert result, 'Peers Interest List still remains the same'

                self.add_rt_filter_family()
                self.logger.info(
                    '*Will re-enable RT_filter Address family between control-nodes and MX*')
                sleep(10)
                peers3 = self.cn_inspect[active_ctrl_node].get_cn_rtarget_group(
                    user_def_rt)['peers_interested']
                self.logger.info(
                    'After re-enabling RT_filter, there are %s peers interested in RT %s' % (len(peers3), user_def_rt))
                self.logger.info('They are %s' % peers3)
                if len(peers3) > len(peers2):
                    mx = list(set(peers3) - set(peers2))
                    self.logger.info(
                        '%s is added back to the peers_interested list' % mx)
                else:
                    result = False
                    assert result, 'Peers Interest List still remains the same'
            else:
                self.logger.error('Peering with Mx not seen')
        else:
            self.logger.info("Skipping Test. Env variable MX_TEST is not set")
            raise self.skipTest(
                "Skipping Test. Env variable MX_TEST is not set.")
        return True
    # end test_vpnv4_route_entry_only_on_RT_interest_receipt

    @preposttest_wrapper
    def test_rt_entry_with_multiple_ctrl_nodes(self):
        '''
        Description: Validate that the dep_routes in the RTGroup Table and paths in the bgp.l3vpn.0 
            corresponding to the VM is seen only in the control_node, the VM's compute node has a session with.
        Test steps:
                 1. Have a setup with more than 2 control nodes.
                 2. Create a VN and a VM in it.
        Pass criteria: Check the dep_routes in the RTGroup Table and paths in the bgp.l3vpn.0 table 
            of the ctrl node that the compute node has a XMPP peering with.
        Maintainer : ganeshahv@juniper.net
        '''
        if len(self.inputs.bgp_ips) > 2:
            vn1_name = get_random_name('vn30')
            vn1_subnets = [get_random_cidr()]
            vn1_vm1_name = get_random_name('vm1')
            vn1_vm2_name = get_random_name('vm2')
            vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
            assert vn1_fixture.verify_on_setup()
            self.logger.info(
                'The RTGroup Table in all the control nodes will have the Route-Target Entry')
            route_target = vn1_fixture.rt_names[0]
            for bgp_ip in self.inputs.bgp_ips:
                assert self.verify_rt_group_entry(bgp_ip, route_target)
            self.logger.info(
                'Will create a VM and check that the dep_route is created in the rt_group table of the control nodes the VMs compute node has a XMPP seesion with')
            vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name,
                                         flavor='contrail_flavor_small', image_name='ubuntu-traffic')
            assert vm1_fixture.wait_till_vm_is_up()
            ip1 = vm1_fixture.vm_ip + '/32'
            for bgp_ip in vm1_fixture.get_control_nodes():
                ctrl_node = self.inputs.host_data[bgp_ip]['host_ip']
                assert self.verify_rt_group_entry(ctrl_node, route_target)
                assert self.verify_dep_rt_entry(ctrl_node, route_target, ip1)
                assert self.verify_rtarget_table_entry(ctrl_node, route_target)
            self.logger.info(
                'dep_route corresponding to the VM should not be in the rt_group table of the control nodes the VMs compute node has no XMPP session with')
            x = set(self.inputs.bgp_control_ips) - \
                set(vm1_fixture.get_control_nodes())
            other_ctrl_ips = list(x)
            for ctrl_ip in other_ctrl_ips:
                ctrl_node = self.inputs.host_data[ctrl_ip]['host_ip']
                assert self.verify_dep_rt_entry_removal(
                    ctrl_node, route_target, ip1)
            self.logger.info(
                'Will launch a second VM and verify that the dep_routes is now populated in the RTGroup Table in the control_node, the VMs compute node has a session with.')
            vm2_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm2_name,
                                         flavor='contrail_flavor_small', image_name='ubuntu-traffic')
            assert vm2_fixture.wait_till_vm_is_up()
            ip2 = vm2_fixture.vm_ip + '/32'
            for ip in vm2_fixture.get_control_nodes():
                ctrl_node = self.inputs.host_data[ip]['host_ip']
                assert self.verify_dep_rt_entry(ctrl_node, route_target, ip2)
            self.logger.info(
                'Now that both the VMs are associated with the same RT, we should see the dep_routes of both the VMs in the respective control nodes')
            a1 = vm1_fixture.get_control_nodes()
            b1 = vm2_fixture.get_control_nodes()
            c1 = list(set(a1+b1))
            for bgp_ip in c1:
                ctrl_node = self.inputs.host_data[bgp_ip]['host_ip']
                assert self.verify_dep_rt_entry(ctrl_node, route_target, ip1)
                assert self.verify_dep_rt_entry(ctrl_node, route_target, ip2)
            y = list(set(self.inputs.bgp_control_ips) - set(c1))
            if len(y) > 0:
                self.logger.info(
                    'dep_route corresponding to the VMs should not be in the rt_group table of the control nodes the VMs compute node has no XMPP session with')
                for ctrl_ip in other_ctrl_ips:
                    ctrl_node = self.inputs.host_data[ctrl_ip]['host_ip']
                    assert self.verify_dep_rt_entry_removal(
                        ctrl_node, route_target, ip1)
                    assert self.verify_dep_rt_entry_removal(
                        ctrl_node, route_target, ip2)
        else:
            self.logger.info(
                'WIll run this test in multiple control-node setup')
        return True
    # end test_rt_entry_with_multiple_ctrl_nodes
