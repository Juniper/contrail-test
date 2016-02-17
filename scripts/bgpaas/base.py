
import test
from common.connections import ContrailConnections
from common import isolated_creds
class BaseBGPTest(test.BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseBGPTest, cls).setUpClass()
        #cls.inputs.public_tenant = "Symantec.tenant.100"
        #project_name = cls.inputs.public_tenant
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
        #cls.isolated_creds = isolated_creds.IsolatedCreds(project_name, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.inputs.set_af('v4')
        cls.connections = cls.isolated_creds.get_conections() 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        #cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseBGPTest, cls).tearDownClass()
 
