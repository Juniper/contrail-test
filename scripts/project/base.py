import test
from common.connections import ContrailConnections
from common import isolated_creds

class BaseProjectTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseProjectTest, cls).setUpClass()

        cls.project = None
        cls.domain_name = None
        cls.admin_inputs = None
        cls.admin_connections = None
        if not cls.inputs.admin_username:
            # It is expected that is_test_applicable will not 
            # let the testcase run if admin_username is not set
            return
        if 'v3' in cls.inputs.auth_url:
            #If user wants to run tests in his allocated domain or Default domain
            if cls.inputs.domain_isolation:
                cls.domain_name = cls.__name__
        cls.admin_isolated_creds = isolated_creds.AdminIsolatedCreds(
                cls.inputs,
                domain_name=cls.inputs.admin_domain,
                ini_file=cls.ini_file,
                logger=cls.logger)
        cls.admin_isolated_creds.setUp()
        cls.admin_connections = cls.admin_isolated_creds.get_connections(
            cls.admin_inputs)
        if cls.inputs.domain_isolation:
            cls.admin_isolated_creds.create_domain(cls.domain_name)
        cls.connections = cls.admin_connections
        cls.vnc_lib = cls.admin_connections.vnc_lib
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

