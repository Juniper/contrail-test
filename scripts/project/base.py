import test_v1
from common.connections import ContrailConnections
from common import isolated_creds

class BaseProjectTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseProjectTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
			    logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseProjectTest, cls).tearDownClass()
    #end tearDownClass 

    def is_test_applicable(self):
        if not self.inputs.admin_username or \
               self.inputs.admin_password or \
               self.inputs.admin_tenant or \
               self.inputs.tenant_isolation :
            return (False, 'Need admin credentials and access to '
                'create projects')
        return (True, None)
    # end is_test_applicable

