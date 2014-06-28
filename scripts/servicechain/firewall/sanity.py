import os
import unittest
import fixtures
import testtools

from connections import ContrailConnections
from contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper

from servicechain.firewall.verify import VerifySvcFirewall


class SvcMonSanityFixture(testtools.TestCase, VerifySvcFirewall):

    def setUp(self):
        super(SvcMonSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMonSanityFixture, self).cleanUp()

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

if __name__ == '__main__':
    unittest.main()
