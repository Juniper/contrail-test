from tcutils.wrappers import preposttest_wrapper
import os
import sys
from base import ServerManagerTest
import test
import fixtures
#import logging
#import logging.config
#import logging.handlers
import unittest
import testtools
from common.contrail_test_init import ContrailTestInit
from smgr_common import SmgrFixture

class SmgrRegressionTests(ServerManagerTest):

#    def __init__(self, new):
#        super(SmgrRegressionTests, self).__init__()
#        self.logger = logging.getLogger()
#        self.logger.level = logging.DEBUG
#        self.logger.addHandler(logging.StreamHandler(sys.stdout))
#        if 'PARAMS_FILE' in os.environ:
#            self.ini_file = os.environ.get('PARAMS_FILE')
#        else:
#            self.ini_file = 'sanity_params.ini'
#
#        if 'TESTBED_FILE' in os.environ:
#            self.testbed_py = os.environ.get('TESTBED_FILE')
#        else:
#            self.testbed_py = 'testbed.py'
#
#        if 'SMGR_FILE' in os.environ:
#            self.smgr_file = os.environ.get('SMGR_FILE')
#        else:
#            self.smgr_file = 'smgr_input.ini'
#
#        self.inputs = '1' 
#        #self.inputs = self.useFixture(ContrailTestInit(self.ini_file, ))
#        #self.inputs = self.useFixture(
#        #    ContrailTestInit(
#        #        self.ini_file,
#        #        stack_user='admin',
#        #        stack_password='contrail123',
#        #        project_fq_name=[
#        #            'default-domain',
#        #            'demo'], logger=self.logger))
#        #self.logger = self.inputs.logger
#
#        self.logger.info("Configuring setup for smgr tests.")
##        import pdb;pdb.set_trace()
#        self.smgr_fixture = self.useFixture(SmgrFixture(self.inputs, testbed_py=self.testbed_py, smgr_config_ini=self.smgr_file, test_local=False))
#        self.logger.info("Adding Server  to smgr DB")
#        self.smgr_fixture.svrmgr_add_all()
#        print "SKIRANH.................................................completed init..............."
#    #resources = [('base_setup', SmgrSetupResource)]
##    logger = logging.getLogger()
##    logger.level = logging.DEBUG
##    logger.addHandler(logging.StreamHandler(sys.stdout))
#   #end init

    @classmethod
    def setUpClass(self):
        super(SmgrRegressionTests, self).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(self):
        super(SmgrRegressionTests, self).setUpClass()
    #end tearDownClass

    def runTest(self):
        pass


    #def setUp(self):
    #    super(SmgrRegressionTests, self).setUp()
    #    if 'PARAMS_FILE' in os.environ:
    #        self.ini_file = os.environ.get('PARAMS_FILE')
    #    else:
    #        self.ini_file = 'params.ini'
    #    self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
    #    self.logger = self.inputs.logger

    #def cleanUp(self):
    #    self.logger.info("Cleaning up Security group tests.")
    #    super(SmgrRegressionTests, self).cleanUp()
    #@preposttest_wrapper
    def test_setup_cluster(self):
        """Verify setup cluster using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.setup_cluster()
        #assert self.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True
    #@preposttest_wrapper
    def test_setup_cluster_with_no_pkg_during_reimage(self):
        """Verify setup cluster using server manager. Reimage with base os only."""
        self.logger.info("Verify setup cluster using server manager. Reimage with base os only. ")
        assert self.smgr_fixture.setup_cluster(no_reimage_pkg=True)
        return True

    #@preposttest_wrapper
    def test_restart(self):
        """Verify restart server using server Manager"""
        self.logger.info("Verify cluster_restart using server manager ")
        assert self.smgr_fixture.reimage(no_pkg=True, restart_only=True)
        return True

    #@preposttest_wrapper
    def test_node_add_delete(self):
        """Verify node add delete using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True

    #@preposttest_wrapper

