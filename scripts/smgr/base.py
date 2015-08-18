import test
import fixtures
import sys
import os
from common.contrail_test_init import ContrailTestInit
from smgr_common import SmgrFixture


class ServerManagerTest(test.BaseTestCase):


    @classmethod
    def setUpClass(self):
        super(ServerManagerTest, self).setUpClass()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'sanity_params.ini'

        if 'TESTBED_FILE' in os.environ:
            self.testbed_py = os.environ.get('TESTBED_FILE')
        else:
            self.testbed_py = 'testbed.py'

        if 'SMGR_FILE' in os.environ:
            self.smgr_file = os.environ.get('SMGR_FILE')
        else:
            self.smgr_file = 'smgr_input.ini'

        self.inputs = '1'
        self.logger.info("Configuring setup for smgr tests.")
        self.smgr_fixture = SmgrFixture(self.inputs, \
		testbed_py=self.testbed_py, \
		smgr_config_ini=self.smgr_file, \
		test_local=False,logger = self.logger)
        self.logger.info("Adding Server  to smgr DB")
        self.smgr_fixture.svrmgr_add_all()
        print ".................................................completed init..............."
 
    # end setUpClass

    @classmethod
    def tearDownClass(self):
        super(ServerManagerTest, self).tearDownClass()
    #end tearDownClass

    def verify(self):
        """verfiy common resources."""
        self.logger.debug("Verify the common resources")
        pass
     
    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
   #end remove_from_cleanups

