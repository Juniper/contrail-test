#Define environment variable FABRIC_UTILS_PATH and provide path to fabric_utils before running
import time
import os
from contrail_fixtures import *
import testtools
from tcutils.commands import *
from fabric.context_managers import settings
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
from fabric.api import run
from fabric.state import connections
import test
from upgrade.verify import VerifyFeatureTestCases
from base import ResetConfigBaseTest

class TestResetConfig(ResetConfigBaseTest,VerifyFeatureTestCases):
    ''' Reset all the configurations '''

    @classmethod
    def setUpClass(cls):
        super(TestResetConfig, cls).setUpClass()
        cls.res.setUp(cls.inputs , cls.connections, cls.logger)
    
    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def test_to_reset_config(self):
	'''
	1) Creates configurations and verify
        2) Reset all the Configurations
        3) Check all the configurations has been reset
        '''
        result = True
        self.inputs.fixture_cleanup = "no"
        self.verify_config_before_feature_test()
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        with settings(
            host_string='%s@%s' % (
                username, self.inputs.cfgm_ips[0]),
                password = password, warn_only=True, abort_on_prompts=False, debug=True): 
            fab_path = os.environ.get('FABRIC_UTILS_PATH', '/opt/contrail/utils')
            reset_cmd = "cd " +fab_path +";fab reset_config "
            self.logger.info("Starting reset configuration")
            status = run(reset_cmd)
            self.logger.debug("LOG for fab reset_config : %s" % status)
            assert not(status.return_code), 'Failed in running : fab reset_config'
            result = result and not(status.return_code)
            self.logger.info("Reset configuration completed")
            project_list = run("source /etc/contrail/openstackrc;keystone tenant-list")
            if self.project.project_name in project_list:
                assert False,'Failed to reset all the configurations'
            self.logger.info("Successfully all the configurations has been reset")
        return result
    #end test_to_reset_config
