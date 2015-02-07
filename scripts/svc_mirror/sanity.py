"""Servcie chain mirroring sanity tests."""
import os
import unittest
import fixtures
import testtools

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.mirror.verify import VerifySvcMirror


class SvcMirrorSanityFixture(testtools.TestCase, VerifySvcMirror):

    def setUp(self):
        super(SvcMirrorSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect = self.connections.agent_inspect
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMirrorSanityFixture, self).cleanUp()

    @preposttest_wrapper
    def test_svc_mirroring(self):
        """Validate the service chain mirroring"""
        return self.verify_svc_mirroring()

    @preposttest_wrapper
    def test_in_network_svc_mirroring(self):
        """Validate the in network service chain mirroring"""
        return self.verify_svc_mirroring(svc_mode='in-network')


if __name__ == '__main__':
    unittest.main()
