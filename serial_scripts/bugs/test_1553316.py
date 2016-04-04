import test
import unittest
from tcutils.wrappers import preposttest_wrapper
from vn_test import MultipleVNFixture
from physical_router_fixture import PhysicalRouterFixture
from common import isolated_creds
from common.neutron.base import BaseNeutronTest 
from jnpr.junos import Device
import os
import sys
import test
from vn_test import VNFixture

class Test1553316(BaseNeutronTest, test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(Test1553316, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__,
                                                          cls.inputs, ini_file=cls.ini_file,
                                                          logger=cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
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
        if len(self.inputs.ext_routers) < 1:            
            return (False, 'Atleast 1 mx is needed')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(Test1553316, self).setUp()

    @test.attr(type=['sanity'])
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
        mx_handle = Device(host=router_params['mgmt_ip'], user=router_params['ssh_username'],password=router_params['ssh_password'])
        mx_handle.open(gather_facts=False)
        cmd = 'show configuration groups __contrail__ routing-instances _contrail_l3_5_%s' % vn1_name
        cli_output = mx_handle.cli(cmd) 
        if 'invalid command' in cli_output:
            self.logger.error('Bug 1553316 present. v6 CIDR config not pushed to mx')
            return False
        return True 

    #end test_create_v6
