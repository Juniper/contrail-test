from tcutils.wrappers import preposttest_wrapper
import os
import sys
from base import ServerManagerTest
import test
import fixtures
import unittest
import testtools
from common.contrail_test_init import ContrailTestInit
from smgr_common import SmgrFixture
import smgr_upgrade_tests
from fabric.api import settings, run
import time
import pdb

class SmgrRegressionTests(ServerManagerTest):

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

    def test_setup_cluster(self):
        """Verify setup cluster using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.setup_cluster()
        return True

    def test_setup_cluster_with_no_pkg_during_reimage(self):
        """Verify setup cluster using server manager. Reimage with base os only."""
        self.logger.info("Verify setup cluster using server manager. Reimage with base os only. ")
        assert self.smgr_fixture.setup_cluster(no_reimage_pkg=True)
        return True

    def test_restart(self):
        """Verify restart server using server Manager"""
        self.logger.info("Verify cluster_restart using server manager ")
        assert self.smgr_fixture.reimage(no_pkg=True, restart_only=True)
        return True

    def test_node_add_delete(self):
        """Verify node add delete using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True

    def test_accross_release_upgrade(self):
        """Verify accross release upgrade using Server Manager"""
        self.logger.info("Verify accross release upgrade using Server Manager.")
        result=False
        SM_base_img=None
        SM_upgd_img=None
        AR_base_img=None
        AR_upgd_img=None
        try:
            SM_base_img=os.environ['SM_BASE_IMG']
            self.logger.info("%s" % SM_base_img)
        except:
            self.logger.error("SM_BASE_IMG is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False
        try:
            SM_upgd_img=os.environ['SM_UPGD_IMG']
            self.logger.info("%s" % SM_upgd_img)
        except:
            self.logger.error("SM_UPGD_IMG is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False

        try:
            AR_base_img=os.environ['AR_BASE_DEB']
            self.logger.info("%s" % AR_base_img)
        except:
            self.logger.error("AR_BASE_DEB is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False
        try:
            AR_upgd_img=os.environ['AR_UPGD_DEB']
            self.logger.info("%s" % AR_upgd_img)
        except:
            self.logger.error("AR_UPGD_DEB is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False

        if((SM_base_img is None) or (SM_base_img == SM_upgd_img)):
            self.logger.info("Running Across release test without SM upgrade")
            result=smgr_upgrade_tests.AR_upgrade_test_without_SM_upgrade(self)
        else:
            self.logger.info("Running Across release test with SM upgrade")
            result=smgr_upgrade_tests.AR_upgrade_test_with_SM_upgrade(self)
        return True

