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
from base import BackupRestoreBaseTest

class TestBackupRestore(BackupRestoreBaseTest,VerifyFeatureTestCases):
    ''' backup and restore the configurations '''

    @classmethod
    def setUpClass(cls):
        super(TestBackupRestore, cls).setUpClass()
        cls.res.setUp(cls.inputs , cls.connections, cls.logger)
        
    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(TestBackupRestore, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def test_fiptraffic_before_backup(self):
        ''' Test to create policy, security group  and floating ip rules on common resources and checking if they work fine
        '''
        return self.verify_config_before_feature_test()
    #end test_fiptraffic_before_backup

    @preposttest_wrapper
    def test_to_backup_restore(self):
        '''Test to backup and restore all the configurations and data'''
        result = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        with settings(
            host_string='%s@%s' % (
                username, self.inputs.cfgm_ips[0]),
                password = password, warn_only=True, abort_on_prompts=False, debug=True):

            fab_path = os.environ.get('FABRIC_UTILS_PATH', '/opt/contrail/utils')
            backup_cmd = "cd " +fab_path +";fab backup_data " 
            restore_cmd = "cd " +fab_path +";fab restore_data " 
            reset_cmd = "cd " +fab_path +";fab reset_config "
            
            self.logger.info("Starting backup")
            status = run(backup_cmd)
            self.logger.debug("LOG for fab backup_data : %s" % status)
            assert not(status.return_code), 'Failed while running  backup_data'
            result = result and not(status.return_code)
            self.logger.info("Backup completed")
            
            self.logger.info("Starting reset config")
            status = run(reset_cmd)
            self.logger.debug("LOG for fab reset_config : %s" % status)
            assert not(status.return_code), 'Failed while running reset_config'
            result = result and not(status.return_code)
            self.logger.info("Reset configuration completed")
            
            self.logger.info("Starting restore")
            status = run(restore_cmd)
            self.logger.debug("LOG for fab restore_data: %s" % status)
            assert not(status.return_code), 'Failed while running restore_data'
            result=result and not(status.return_code)
            self.logger.info("Restore of data and configuration completed")  
        return result
    #end test_backup_restore   
    
    @preposttest_wrapper
    def test_traffic_after_restore(self):
        '''Test to test traffic after restore using previouly defined  policy and floating ip and then adding new policy,fip to new resources also  validate service chaining in network  datapath and security group
        '''
        return self.verify_config_after_feature_test()
    #end test_traffic_after_restore        
