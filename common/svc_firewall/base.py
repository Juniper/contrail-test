from common.base import GenericTestBase
from common import create_public_vn

class BaseSvc_FwTest(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        super(BaseSvc_FwTest, cls).setUpClass()
        if cls.inputs.admin_username:
            public_creds = cls.admin_isolated_creds
        else:
            public_creds = cls.isolated_creds
        cls.public_vn_obj = create_public_vn.PublicVn(
            public_creds,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseSvc_FwTest, cls).tearDownClass()
    #end tearDownClass 

