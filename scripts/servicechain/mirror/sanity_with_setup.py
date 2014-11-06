"""Servcie chain mirroring sanity tests."""
import os

import unittest
import fixtures
import testtools
from testresources import ResourcedTestCase

from common.connections import ContrailConnections
from sanity_resource import SolnSetupResource
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.mirror.verify import VerifySvcMirror


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
        """Validate the service chain mirroring
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Create the policy rule for ICMP/UDP and attach to vn's
           4. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
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
