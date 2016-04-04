from tcutils.commands import *
from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
from control_node import CNFixture
import base

class BgpRouterTest(base.BaseBgpRouterTest):
    
    @classmethod
    def setUpClass(cls):
        super(BgpRouterTest, cls).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BgpRouterTest, cls).tearDownClass()
    #end tearDownClass
    
    @preposttest_wrapper
    def test_control_node_bgp_peering(self):
        '''Control node should not be Active if it doesn't have bgp-router for self 
        1)delete bgp_router of control node
        2)check contrail-status for control-service  
        3)Test passed if control service is inactive with message No BGP configuration for self
        '''
        bgp_ip=self.inputs.bgp_ips[0]
        hostname = self.inputs.host_data[bgp_ip]['name']
        control_ip = self.inputs.host_data[bgp_ip]['host_control_ip']
        cn_user = self.inputs.host_data[control_ip]['username']
        cn_password = self.inputs.host_data[control_ip]['password']
        cn_status = 'contrail-status'
        router_type = 'contrail'
        check_str ='No BGP configuration for self'
        cn_fixture = self.useFixture(
            CNFixture(
                connections=self.connections,
                router_name=hostname,
                router_ip=control_ip,
                router_type=router_type,
                inputs=self.inputs))
        self.logger.info('Delete control node bgp peer %s' %control_ip)
        cn_fixture.del_cn_node(control_ip)
        output=self.inputs.run_cmd_on_server(control_ip,cn_status)
        if check_str not in output:
            cn_fixture.create_cn_node(control_ip,router_type)
            assert False,'Control node should not be Active if it does not have bgp-router for self.Test failed'
        cn_fixture.create_cn_node(control_ip,router_type)
        self.logger.info('Control service is inactive and has message No BGP configuration for self.Test Passed')  
    #end test_control_node_bgp_peering
    
    @preposttest_wrapper
    def test_bgp_peer_passive(self):
        pass
    
    @preposttest_wrapper
    def test_bgp_router_local_AS(self):
        pass
    