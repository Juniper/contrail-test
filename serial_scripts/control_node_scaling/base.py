import test
import re
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture

class BaseBGPScaleTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseBGPScaleTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.inputs.set_af('v4')
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        #cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseBGPScaleTest, cls).tearDownClass()
    #end tearDownClass 

