from __future__ import absolute_import
from builtins import str
from builtins import range
from .base import BaseDM
import test
from tcutils.wrappers import preposttest_wrapper
from vn_test import MultipleVNFixture
from physical_router_fixture import PhysicalRouterFixture
from lif_fixture import LogicalInterfaceFixture
from common import isolated_creds
from serial_scripts.md5.base import Md5Base
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
        try:
            if not list(self.inputs.dm_mx.values()):
                return (False, 'dm_mx env present, but no values in it. Please check.')
        except AttributeError:
                return (False, 'dm_mx env needs to be set in testbed.py to run this script')
        if len(self.inputs.ext_routers) < 1:
            return (False, 'Atleast 1 mx is needed')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(TestDM, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.check_dm = True
            self.config_basic()
            self.vn_index = self.vnc_lib.virtual_network_read(id = self.vn1_fixture.uuid).virtual_network_network_id
            self.v6_index = self.vnc_lib.virtual_network_read(id = self.vn2_fixture.uuid).virtual_network_network_id
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
        self.sleep(90)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        
        cmd = 'show configuration groups __contrail__'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        as_value = self.get_old_as()
        cmd = 'show configuration groups __contrail__ protocols bgp group _contrail_asn-%s' % as_value
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
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices()

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
       
        self.change_vtep()
        as_value = self.get_old_as()
        cmd = 'show configuration groups __contrail__ routing-options dynamic-tunnels _contrail_asn-%s source-address' % as_value
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not '10.20.30.40' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices()

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

    @preposttest_wrapper
    def test_break_connectivity_to_mx(self):
        for i in range(len(list(self.inputs.physical_routers_data.values()))):
            router_params = list(self.inputs.physical_routers_data.values())[i]

            cmd = '/sbin/iptables -A OUTPUT -d %s -j DROP' % router_params['mgmt_ip']
            for node in self.inputs.cfgm_ips:
                dm_status = self.inputs.run_cmd_on_server(node, cmd)
        self.add_vn_to_device()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        try:
            self.does_mx_have_config(cmd)
            self.is_dm_removed()
        except AssertionError:
            self.logger.info("NO VN config found after port disable.")
        else:
            assert False, "VN config should not have been found. Failing"

        self.send_traffic_between_vms()
        self.addCleanup(self.remove_iptable_config)

        for i in range(len(list(self.inputs.physical_routers_data.values()))):
            router_params = list(self.inputs.physical_routers_data.values())[i]

            cmd = '/sbin/iptables -D OUTPUT -d %s -j DROP' % router_params['mgmt_ip']
            for node in self.inputs.cfgm_ips:
                dm_status = self.inputs.run_cmd_on_server(node, cmd)

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.delete_vn_from_devices()
        return True

    @preposttest_wrapper
    def test_external_group_pushed_to_mx(self):
        """
        Description: Verify external group is pushed to mx
        """
        self.sleep(90)
        as_value = self.get_old_as()
        cmd = 'show configuration groups __contrail__ protocols bgp group _contrail_asn-%s' % as_value
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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)
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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.delete_vn_from_devices()
        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.vm1_fixture.delete()
        vn_delete = self.vnc_lib.virtual_network_delete(id=str(self.vn1_fixture.uuid))
        v6_delete = self.vnc_lib.virtual_network_delete(id=str(self.vn2_fixture.uuid))

        self.create_vn()
        self.add_vn_to_device()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

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

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.change_global_vn_config('l2')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        self.change_global_vn_config('l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        self.change_global_vn_config('l2_l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.change_vn_forwarding_mode('l2')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        self.change_vn_forwarding_mode('l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_removed()

        self.change_vn_forwarding_mode('l2_l3')
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l3-%s' % (self.vn2_name, self.v6_index)

        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn2_name, self.v6_index)

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
        self.add_vn_RT(value = '54321')
        self.send_traffic_between_vms()

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index) 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s' % (self.vn1_name, self.vn_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        self.add_vn_RT(value = '76543', mode = 'import')
        self.add_vn_RT(value = '65432', mode = 'export')
        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l2-%s-import term t1 from community' % (self.vn1_name, self.vn_index)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        assert self.check_policy_added_on_mx(cmd, '54321'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '76543'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy added with wrong RT'

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l3-%s-import term t1 from community' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_policy_added_on_mx(cmd, '54321'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '76543'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy added with wrong RT'

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l2-%s-export term t1 then' % (self.vn1_name, self.vn_index)
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_policy_added_on_mx(cmd, '54321'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy added with wrong RT'
        assert self.check_policy_added_on_mx(cmd, '65432'), 'Policy not added after 120 sec'

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l3-%s-export term t1 then' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        assert self.check_policy_added_on_mx(cmd, '54321'), 'Policy not added after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy added with wrong RT'
        assert self.check_policy_added_on_mx(cmd, '65432'), 'Policy not added after 120 sec'

        self.del_vn_RT(value = '54321')
        self.del_vn_RT(value = '76543', mode = 'import')
        self.del_vn_RT(value = '65432', mode = 'export')
        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l2-%s-import term t1 from community' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_policy_removed_on_mx(cmd, '54321'), 'Policy not deleted after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy not deleted after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy not deleted after 120 sec'

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l3-%s-import term t1 from community' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_policy_removed_on_mx(cmd, '54321'), 'Policy not deleted after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy not deleted after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy not deleted after 120 sec'
        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l2-%s-export term t1 then' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()

        assert self.check_policy_removed_on_mx(cmd, '54321'), 'Policy not deleted after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy not deleted after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy not deleted after 120 sec'

        cmd = 'show configuration groups __contrail__ policy-options policy-statement _contrail_%s-l3-%s-export term t1 then' % (self.vn1_name, self.vn_index)
 
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        assert self.check_policy_removed_on_mx(cmd, '54321'), 'Policy not deleted after 120 sec'
        assert self.check_policy_added_on_mx(cmd, '98765'), 'Policy not added after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '76543'), 'Policy not deleted after 120 sec'
        assert self.check_policy_removed_on_mx(cmd, '65432'), 'Policy not deleted after 120 sec'
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
        as_value = self.get_old_as()
        cmd = 'show configuration groups __contrail__ routing-options dynamic-tunnels _contrail_asn-%s destination-networks' % as_value
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

    '''
    @preposttest_wrapper
    def test_fip_vm(self):
        """
        Description: Check if FIP config is pushed 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status
        fip_pool_name = 'fip_dm_pool'
        # Adding further projects to floating IP.
        self.logger.info('Adding project %s to FIP pool %s' %
                         (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.assoc_project\
                        (self.inputs.project_name)
        fip_id = self.public_vn_obj.fip_fixture.create_and_assoc_fip(
            self.public_vn_obj.public_vn_fixture.vn_id, self.vm1_fixture.vm_id, project_obj)
        self.addCleanup(self.public_vn_obj.fip_fixture.disassoc_and_delete_fip, fip_id)

        assert self.public_vn_obj.fip_fixture.verify_fip(fip_id, self.vm1_fixture,
                self.public_vn_obj.public_vn_fixture)
        self.add_vn_to_device()
        cmd = 'show configuration groups __contrail__ firewall family inet filter redirect_to_public_vrf_filter_inet4 term term-_contrail_l3_%s_%s from destination-address' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not str(self.vn1_fixture.get_cidrs()[0]) in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)

        cmd = 'show configuration groups __contrail__ firewall family inet filter redirect_to_public_vrf_filter_inet4 term term-_contrail_l3_%s_%s then routing-instance' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not ('_contrail_l3_' + str(self.vn_index) + '_' + self.vn1_name) in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)

        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s routing-options static route 0.0.0.0/0 next-table' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not 'inet.0' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        self.logger.info(
            "BGP Peer configuraion done and trying to outside the VN cluster")

        if not self.vm1_fixture.ping_to_ip('8.8.8.8'):
            self.logger.error(
                "Ping packets to outside world not going through" )
            result = result and False
        else:
            self.logger.info(
                "Ping going through correctly")

    @preposttest_wrapper
    def test_scale_2k_vns(self):

        self.scale_vns()
        sleep(300)
        cmd = 'show configuration groups __contrail__ interfaces irb'
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not len(re.findall('unit', self.output_from_mx[0])) == 2000:
                return False, str(self.phy_router_fixture[i].name)
        for i in range(1, 10):
            for node in self.inputs.cfgm_ips:
                self.inputs.restart_service('contrail-device-manager', [node])
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (
                    error_nodes)
        for node in self.inputs.cfgm_ips:
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, node),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
                conrt = run('grep "error" /var/log/contrail/contrail-device-manager.log')
            self.logger.info("These are the errors found in node %s: %s" % (node, conrt))
        self.remove_nc_config()
        cmd = 'show configuration groups __contrail__'
        self.does_mx_have_config(cmd)

        self.is_dm_removed()
        self.add_nc_config()
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        self.delete_vn_from_devices()
        return True
    '''

    @preposttest_wrapper
    def test_mx_connected_to_bms(self):
        """
        Description: Verify VN config is pushed to mx
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        new_port = self.create_port(net_id=self.vn1_fixture.vn_id, mac_address='00:e0:81:cf:5c:00')
        for dev_fixture in list(self.phy_router_fixture.values()):
            phy_new_port = dev_fixture.add_physical_port('ge-0/0/6')
            logical_new_port = self.useFixture(LogicalInterfaceFixture(name='ge-0/0/6.0', pif_id=phy_new_port.uuid, vlan_id=100,vmi_ids=[new_port['id']], vn_obj=self.vn1_fixture.obj))
        cmd = 'show configuration groups __contrail__ interfaces ge-0/0/6 unit 0 vlan-id'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not '100' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_%s-l2-%s bridge-domains bd-%s' % (self.vn1_name, self.vn_index, self.vn_index)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        for i in range(len(self.output_from_mx)):
            if not 'ge-0/0/6.0' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        return True

