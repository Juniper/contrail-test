import test_v1
from common.connections import ContrailConnections
from common import isolated_creds

class BaseDiscoveryTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseDiscoveryTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.ds_obj = cls.connections.ds_verification_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDiscoveryTest, cls).tearDownClass()
    #end tearDownClass 

