import test
import unittest
from tcutils.wrappers import preposttest_wrapper
from vn_test import MultipleVNFixture
from physical_router_fixture import PhysicalRouterFixture
from common import isolated_creds
from serial_scripts.md5.base import Md5Base
from base import BaseDM
from common.neutron.base import BaseNeutronTest
from tcutils.contrail_status_check import *
import physical_device_fixture
from jnpr.junos import Device
from time import sleep
import os
import sys
import re
from vn_test import VNFixture

class TestDM(BaseDM, Md5Base, BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestDM, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj

    @classmethod
    def tearDownClass(cls):
        super(TestDM, cls).tearDownClass()

    def is_test_applicable(self):
        if not self.inputs.physical_routers_data.values():
           return (False, 'Physical routers data needs to be set in testbed.py to run this script')
        if len(self.inputs.ext_routers) < 1:
            return (False, 'Atleast 1 mx is needed')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(TestDM, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.config_basic()
            self.vn_index = self.vnc_lib.virtual_network_read(id = self.vn1_fixture.uuid).virtual_network_network_id
            uuid = self.vnc_lib.bgp_routers_list()
            self.uuid = str(uuid)
            self.list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', self.uuid)
        else:
            return

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_basic_dm(self):
        """
        Description: Verify basic config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        
        cmd = 'show configuration groups __contrail__'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        return True

    #end test_basic_dm

    @preposttest_wrapper
    def test_if_vn_pushed_using_dm(self):
        """
        Description: Verify VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_change_vtep(self):
        """
        Description: Change vtep config and push to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.change_vtep()
        cmd = 'show configuration groups __contrail__ routing-options dynamic-tunnels __contrail__ source-address'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not '10.20.30.40' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_nc_pushed_using_dm(self):
        """
        Description: Verify nc config is pushed to mx
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        self.remove_nc_config()
        cmd = 'show configuration groups __contrail__'
        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        self.add_nc_config()
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    '''
    @preposttest_wrapper
    def test_break_connectivity_to_mx(self):
        cmd = '/sbin/iptables -A OUTPUT -p tcp --dport 22 -j DROP'
        for node in self.inputs.cfgm_ips:
            dm_status = self.inputs.run_cmd_on_server(node, cmd)
        self.add_vn_to_device()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        try:
            self.does_mx_have_config(cmd)
            self.is_dm_removed()
        except AssertionError:
            self.logger.info("NO VN config found after port disable.")
        else:
            assert False, "VN config should not have been found. Failing"

        #self.send_traffic_between_vms()
        cmd = '/sbin/iptables -D OUTPUT -p tcp --dport 22 -j DROP'
        for node in self.inputs.cfgm_ips:
            dm_status = self.inputs.run_cmd_on_server(node, cmd)
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_vn_from_devices
        return True
    '''

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_external_group_pushed_to_mx(self):
        """
        Description: Verify external group is pushed to mx
        """

        cmd = 'show configuration groups __contrail__ protocols bgp group __contrail_external__'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_vn_from_devices
        return True
        
    @preposttest_wrapper
    def test_bind_unbind_vn_pushed_using_dm(self):
        """
        Description: Verify bind unbind VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.delete_vn_from_devices()

        self.does_mx_have_config(cmd)
        
        self.is_dm_removed()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        return True

    @preposttest_wrapper
    def test_add_delete_vn_pushed_using_dm(self):
        """
        Description: Verify add/delete VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.delete_vn_from_devices()

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        vn_delete = self.vnc_lib.virtual_network_delete(id=str(self.vn1_fixture.uuid))
        self.create_vn()
        self.add_vn_to_device()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_add_delete_device_using_dm(self):
        """
        Description: Verify add/delete device is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices()

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_physical_devices()
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.create_physical_dev()
        self.add_vn_to_device()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_bind_unbind_device_using_dm(self):
        """
        Description: Verify bind/unbind config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.unbind_dev_from_router()
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.bind_dev_to_router()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_restart_dm(self):
        """
        Description: Verify restart DM
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        for i in range(1, 10):
            for node in self.inputs.cfgm_ips:
                self.inputs.restart_service('contrail-device-manager', [node])
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (
                    error_nodes) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices
        return True
 
    @preposttest_wrapper
    def test_vn_change_forwarding_mode(self):
        """
        Description: Verify VN forwarding mode is pushed to mx
        """
        self.addCleanup(self.remove_global_vn_config)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.change_global_vn_config('l2')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        self.change_global_vn_config('l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        self.change_global_vn_config('l2_l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.change_vn_forwarding_mode('l2')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        self.change_vn_forwarding_mode('l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        self.change_vn_forwarding_mode('l2_l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_change_import_export_RT(self):
        """
        Description: Verify RT config is pushed to mx
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l2_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.add_vn_RT(value = '54321')
        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l2_%s_%s-import term t1 from community' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_added_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l3_%s_%s-import term t1 from community' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_added_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l2_%s_%s-export term t1 then' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_added_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l3_%s_%s-export term t1 then' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_added_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        self.del_vn_RT(value = '54321')
        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l2_%s_%s-import term t1 from community' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_removed_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l3_%s_%s-import term t1 from community' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_removed_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l2_%s_%s-export term t1 then' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_removed_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_l3_%s_%s-export term t1 then' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        self.check_policy_removed_on_mx(cmd, '54321')
        self.check_policy_added_on_mx(cmd, '98765')
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_vn_from_devices

        return True

    @preposttest_wrapper
    def test_dynamic_tunnels(self):
        """
        Description: Verify tunnel config is pushed to mx
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-options dynamic-tunnels __contrail__ destination-networks'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            for j in range(1,13):
                self.does_mx_have_config(cmd)
                self.is_dm_going_through()
                if any(bgp_node not in self.output_from_mx[i] for bgp_node in self.inputs.bgp_control_ips):
                    sleep(10)
                else:
                    break
                if j == 12:
                    assert False, "Tunnels not added after 120 sec"

        return True

    @preposttest_wrapper
    def test_multiple_subnets(self):
        """
        Description: Verify multiple VN config is pushed to mx
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        self.send_traffic_between_vms()

        self.vn1_fixture.add_subnet('10.1.1.0/24')
        cmd = 'show configuration groups __contrail__ interfaces irb unit %s family inet' % (self.vn_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            for j in range(1,13):
                self.does_mx_have_config(cmd)
                self.is_dm_going_through()
                if not '10.1.1' in self.output_from_mx[i]:
                    sleep(10)
                else:
                    break
                if j == 12:
                    assert False, "Multiple subnets not added after 120 sec"
        self.add_multiple_vns()
        self.send_traffic_with_multiple_vns()
        return True

    @preposttest_wrapper
    def test_logs_for_errors(self):
        """
        Description: Check for errors in DM logs 
        """
        for node in self.inputs.cfgm_ips:
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, node),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
                conrt = run('grep "error" /var/log/contrail/contrail-device-manager.log')
            self.logger.info("These are the errors found in node %s: %s" % (node, conrt))
        return True

    @preposttest_wrapper
    def test_changing_AS(self):
        """
        Description: Change AS using DM and confirm BGP status
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status
        self.add_vn_to_device()
        old_as = self.get_old_as()
        self.change_global_AS(100)
        self.verify_mx_AS_different()
        self.change_mx_AS(100)
        sleep(90)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.change_global_AS(old_as)
        self.change_mx_AS(old_as)
        sleep(90)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        return True

