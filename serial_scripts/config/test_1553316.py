import test_v1
import unittest
from tcutils.wrappers import preposttest_wrapper
from vn_test import MultipleVNFixture
from physical_router_fixture import PhysicalRouterFixture
from common import isolated_creds
from common.neutron.base import BaseNeutronTest 
import physical_device_fixture
from jnpr.junos import Device
from time import sleep
import os
import sys
from vn_test import VNFixture

class Test1553316(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(Test1553316, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj

    @classmethod
    def tearDownClass(cls):
        super(Test1553316, cls).tearDownClass()

    def is_test_applicable(self):
        if not self.inputs.physical_routers_data.values():
            return (False, 'Physical routers data needs to be set in testbed.py to run this script')
        if len(self.inputs.ext_routers) < 1:            
            return (False, 'Atleast 1 mx is needed')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(Test1553316, self).setUp()

    @preposttest_wrapper
    def test_create_v6(self):
        """
        Description: Verify v6 config is pushed to mx 
        """
        router_params = self.inputs.physical_routers_data.values()[0]
        self.phy_router_fixture = self.useFixture(PhysicalRouterFixture(
            router_params['name'], router_params['mgmt_ip'],
            model=router_params['model'],
            vendor=router_params['vendor'],
            asn=router_params['asn'],
            ssh_username=router_params['ssh_username'],
            ssh_password=router_params['ssh_password'],
            mgmt_ip=router_params['mgmt_ip'],
            connections=self.connections))

        vn1_name = "test_vnv6sr"
        vn1_net = ['2001::101:0/120']
        #vn1_fixture = self.config_vn(vn1_name, vn1_net)
        vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn1_name, inputs=self.inputs, subnets=vn1_net))
        assert vn1_fixture.verify_on_setup()
        self.extend_vn_to_physical_router(vn1_fixture, self.phy_router_fixture) 
        sleep(20)
        mx_handle = self.phy_router_fixture.get_connection_obj('juniper', 
                    host=router_params['mgmt_ip'], 
                    username=router_params['ssh_username'], 
                    password=router_params['ssh_password'], 
                    logger=[self.logger])
                
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_5_%s' % vn1_name
        cli_output = self.get_output_from_node(mx_handle, cmd)
        assert (not('invalid command' in cli_output)), "Bug 1553316 present. v6 CIDR config not pushed to mx"

        return True 

    #end test_create_v6

    def get_output_from_node(self, handle, cmd):
        return handle.handle.cli(cmd)
