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
from OpenSSL.rand import status
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
    #test_fiptraffic_before_backup

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
            
            backup_cmd = " cd /root/fabric-utils;fab backup_data " 
            restore_cmd = " cd /root/fabric-utils;fab restore_data " 
            reset_cmd = " cd /root/fabric-utils;fab reset_config "
            
            self.logger.info("==========STARTING BACKUP==========")
            status = run(backup_cmd)
            self.logger.debug("LOG for fab backup_data : %s" % status)
            assert not(status.return_code), 'Failed in running : cd /root/fabric-utils;fab backup_data'
            result = result and not(status.return_code)
            self.logger.info("==========BACKUP COMPLETED==========")
            
            self.logger.info("==========STARTING RESET CONFIGURATION==========")
            status = run(reset_cmd)
            self.logger.debug("LOG for fab reset_config : %s" % status)
            assert not(status.return_code), 'Failed in running : cd /root/fabric-utils;fab backup_data'
            result = result and not(status.return_code)
            self.logger.info("==========RESET CONFIGURATION COMPLETED==========")
            
            self.logger.info("==========STARTING RESTORE==========")
            restore_cmd = "cd /root/fabric-utils;fab restore_data " 
            status = run(restore_cmd)
            self.logger.debug("LOG for fab restore_data: %s" % status)
            assert not(status.return_code), 'Failed in running : cd /root/fabric-utils;fab backup_data'
            result=result and not(status.return_code)
            self.logger.info("==========RESTORE OF DATA AND CONFIGURATION COMPLETED==========")  
        return result
    #end test_backup_restore   
    
    @preposttest_wrapper
    def test_traffic_after_restore(self):
        '''Test to test traffic after restore using previouly defined  policy and floating ip and then adding new policy,fip to new resources also  validate service chaining in network  datapath and security group
        '''
        return self.verify_config_after_feature_test()
    #test_traffic_after_restore        
