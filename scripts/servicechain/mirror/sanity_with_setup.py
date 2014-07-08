"""Servcie chain mirroring sanity tests."""
import os

import unittest
import fixtures
import testtools
from testresources import ResourcedTestCase

from connections import ContrailConnections
from sanity_resource import SolnSetupResource
from contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from servicechain.mirror.verify import VerifySvcMirror


class SvcMirrorSanityFixture(testtools.TestCase, ResourcedTestCase, VerifySvcMirror):

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
        self.agent_inspect = self.connections.agent_inspect

    def setUp(self):
        super(SvcMirrorSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    @preposttest_wrapper
    def test_svc_mirroring(self):
        """Validate the service chain mirroring"""
        return self.verify_svc_mirroring()

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMirrorSanityFixture, self).cleanUp()

    def tearDown(self):
        print "Tearing down Mirror test"
        super(SvcMirrorSanityFixture, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

if __name__ == '__main__':
    unittest.main()
