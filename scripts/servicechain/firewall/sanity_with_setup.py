import os
import fixtures
import testtools
import unittest

from connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from time import sleep
from servicechain.config import ConfigSvcChain
from servicechain.verify import VerifySvcChain
from servicechain.firewall.verify import VerifySvcFirewall


class SvcMonSanityFixture(testtools.TestCase, ResourcedTestCase, VerifySvcFirewall):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(SvcMonSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(SvcMonSanityFixture, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
        """Validate the service chaining in network  datapath"""
        return self.verify_svc_in_network_datapath()

    @preposttest_wrapper
    def test_svc_monitor_datapath(self):
        """Validate the service chaining transparent mode datapath with one
        service instance"""
        return self.verify_svc_transparent_datapath()

    @preposttest_wrapper
    def test_svc_transparent_with_3_instance(self):
        """Validate the service chaining transparent mode datapath with three
        service instance"""
        return self.verify_svc_transparent_datapath(si_count=3)


# end TestSanityFixture
