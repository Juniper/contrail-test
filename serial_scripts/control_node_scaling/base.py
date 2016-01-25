import test_v1
from common import isolated_creds

class BaseBGPScaleTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseBGPScaleTest, cls).setUpClass()
        cls.inputs.set_af('v4')
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseBGPScaleTest, cls).tearDownClass()
    #end tearDownClass 

