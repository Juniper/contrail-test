import test
import fixtures
from common import isolated_creds


class BaseEncapTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseEncapTest, cls).setUpClass()
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
        #cls.connections= ContrailConnections(cls.inputs)
        cls.quantum_fixture = cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib = cls.connections.vnc_lib
#        cls.logger= cls.inputs.logger
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        # cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseEncapTest, cls).tearDownClass()
    # end tearDownClass
