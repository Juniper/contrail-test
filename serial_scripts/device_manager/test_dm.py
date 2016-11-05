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
        else:
            return

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

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_if_vn_pushed_using_dm(self):
        """
        Description: Verify VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_%s_%s' % (self.vn_index, self.vn1_name)
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()

        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()
        self.delete_vn_from_devices()

        return True

    @preposttest_wrapper
    def test_bind_unbind_vn_pushed_using_dm(self):
        """
        Description: Verify bind unbind VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()

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
        self.delete_vn_from_devices()

        return True

    @preposttest_wrapper
    def test_add_delete_device_using_dm(self):
        """
        Description: Verify VN config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()

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
        self.delete_vn_from_devices()

        return True

    @preposttest_wrapper
    def test_bind_unbind_device_using_dm(self):
        """
        Description: Verify bind/unbind config is pushed to mx 
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()

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
        self.delete_vn_from_devices()

        return True

    @preposttest_wrapper
    def test_restart_dm(self):
        """
        Description: Verify restart DM
        """
        assert self.check_bgp_status(is_mx_present=True)
        assert self.check_tcp_status()

        self.add_vn_to_device()
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
        self.delete_vn_from_devices()
        return True
 

