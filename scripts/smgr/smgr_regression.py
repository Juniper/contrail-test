import os
import fixtures
import testtools
import unittest


from testresources import ResourcedTestCase

#from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from smgr.smgr_setup import SmgrSetupResource


class SmgrRegressionTests(testtools.TestCase, ResourcedTestCase,
                                   fixtures.TestWithFixtures):

    resources = [('base_setup', SmgrSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SmgrSetupResource.getResource()
        self.inputs = self.res.inputs
        #self.connections = self.res.connections
        self.logger = self.inputs.logger

    def __del__(self):
        self.logger.debug("Unconfig the common resurces.")
        SmgrSetupResource.finishedWith(self.res)

    def setUp(self):
        super(SmgrRegressionTests, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        self.logger.debug("Tearing down SmgrRegressionTests.")
        super(SmgrRegressionTests, self).tearDown()
        SmgrSetupResource.finishedWith(self.res)

    def runTest(self):
        pass


    #@preposttest_wrapper
    def test_setup_cluster(self):
        """Verify setup cluster using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        #assert self.res.smgr_fixture.setup_cluster()
        assert self.res.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True

    #@preposttest_wrapper
    def test_setup_cluster_with_no_pkg_during_reimage(self):
        """Verify setup cluster using server manager. Reimage with base os only."""
        self.logger.info("Verify setup cluster using server manager. Reimage with base os only. ")
        assert self.res.smgr_fixture.setup_cluster(no_reimage_pkg=True)
        return True

    #@preposttest_wrapper
    def test_restart(self):
        """Verify restart server using server Manager"""
        self.logger.info("Verify cluster_restart using server manager ")
        assert self.res.smgr_fixture.reimage(no_pkg=True, restart_only=True)
        return True


    #@preposttest_wrapper
    def test_node_add_delete(self):
        """Verify node add delete using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.res.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True

