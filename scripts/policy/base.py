import test_v1
from common import isolated_creds


class BasePolicyTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BasePolicyTest, cls).setUpClass()
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BasePolicyTest, cls).tearDownClass()
    # end tearDownClass
#end BasePolicyTest class

