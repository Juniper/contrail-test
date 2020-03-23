from common.base import GenericTestBase

class RouteAggregateBase(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        super(RouteAggregateBase, cls).setUpClass()
        '''cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj'''
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(RouteAggregateBase, cls).tearDownClass()
    # end tearDownClass