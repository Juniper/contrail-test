import os
import fixtures
import testtools
import unittest

from testresources import ResourcedTestCase

from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from smgr.smgr_setup import SmgrSetupResource


class SmgrRegressionTests(testtools.TestCase, ResourcedTestCase,
                                   fixtures.TestWithFixtures):

    resources = [('base_setup', SmgrSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SmgrSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
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


    @preposttest_wrapper
    def test_reimage(self):
        """Verify reimage  using server manager  in a multinode setup"""
        self.logger.info("Verify reimage  using server manager  in a multinode setup")
        self.res.smgr_fix.reimage()

        return True

    @preposttest_wrapper
    def test_provision(self):
        """Verify provision  using server manager  in a multinode setup"""
        self.logger.info("Verify provision  using server manager  in a multinode setup")
        self.res.smgr_fix.provision()

        return True

