import test
from common import isolated_creds


class BaseFlowTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseFlowTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.admin_inputs = cls.isolated_creds.get_admin_inputs()
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_fixture= cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseFlowTest, cls).tearDownClass()
    # end tearDownClass

#end BaseFlowTest class

