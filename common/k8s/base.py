import test
from common.connections import ContrailConnections

class BaseK8sTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        cls.connections = ContrailConnections(cls.inputs,
                              project_name='default',
                              username=cls.inputs.admin_username,
                              password=cls.inputs.admin_password,
                              logger=cls.logger)
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.logger = cls.connections.logger

    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseK8sTest, cls).tearDownClass()
    # end tearDownClass

