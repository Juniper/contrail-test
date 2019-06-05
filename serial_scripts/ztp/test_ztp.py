import test
import time
from ztp_base import ZtpBaseTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because

class TestZtp(ZtpBaseTest):
    
    @preposttest_wrapper
    def test_ztp_workflow(self):
       
        #self.logger.info("Taking config backup for the devices")
        #self.backup_config()
        pass

        #self.logger.info("Restoring config from backup saved in step 1")
        #self.restore_config()

