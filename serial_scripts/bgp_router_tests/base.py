import test_v1
from control_node import CNFixture

class BaseBgpRouterTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseBgpRouterTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.ops_inspect = cls.connections.ops_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseBgpRouterTest, cls).tearDownClass()
    # end tearDownClass
    
    def get_cn_fixture(self):
        self.bgp_ip=self.inputs.bgp_ips[0]
        self.hostname = self.inputs.host_data[self.bgp_ip]['name']
        self.control_ip = self.inputs.host_data[self.bgp_ip]['host_control_ip']
        self.cn_user = self.inputs.host_data[self.control_ip]['username']
        self.cn_password = self.inputs.host_data[self.control_ip]['password']
        self.router_type = 'contrail'
        cn_fixture = self.useFixture(
            CNFixture(
                connections=self.connections,
                router_name=self.hostname,
                router_ip=self.control_ip,
                router_type=self.router_type,
                inputs=self.inputs))
        return cn_fixture

#end BaseBgpRouterTest class

