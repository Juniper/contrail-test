import test
from common.connections import ContrailConnections
from common import isolated_creds

class BaseProjectTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseProjectTest, cls).setUpClass()

        cls.project = None
        cls.admin_inputs = None
        cls.admin_connections = None
        if not cls.inputs.admin_username:
            # It is expected that is_test_applicable will not 
            # let the testcase run if admin_username is not set
            return
        cls.admin_isolated_creds = isolated_creds.AdminIsolatedCreds(
                cls.inputs,
                ini_file=cls.ini_file,
                logger=cls.logger)
        cls.admin_isolated_creds.setUp()
        cls.admin_connections = cls.admin_isolated_creds.get_connections(
            cls.admin_inputs)
        cls.admin_project = cls.admin_isolated_creds.create_tenant(
            cls.admin_isolated_creds.project_name)
        cls.admin_inputs = cls.admin_isolated_creds.get_inputs(
            cls.admin_project)
        cls.admin_connections = cls.admin_isolated_creds.get_connections(
            cls.admin_inputs)

        cls.quantum_h = cls.admin_connections.quantum_h
        cls.nova_h = cls.admin_connections.nova_h
        cls.vnc_lib = cls.admin_connections.vnc_lib
        cls.agent_inspect = cls.admin_connections.agent_inspect
        cls.cn_inspect = cls.admin_connections.cn_inspect
        cls.analytics_obj = cls.admin_connections.analytics_obj
        cls.connections = cls.admin_connections
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseProjectTest, cls).tearDownClass()
    #end tearDownClass 

    def is_test_applicable(self):
        if not (self.inputs.admin_username or \
               self.inputs.admin_password or \
               self.inputs.admin_tenant or \
               self.inputs.tenant_isolation) :
            return (False, 'Need admin credentials and access to '
                'create projects')
        return (True, None)
    # end is_test_applicable

