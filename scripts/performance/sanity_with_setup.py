import os
import fixtures
import testtools

from contrail_test_init import *
from contrail_fixtures import *
from connections import ContrailConnections
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from tcutils.wrappers import preposttest_wrapper
from performance.verify import PerformanceTest


class PerformanceSanity(testtools.TestCase, ResourcedTestCase, PerformanceTest):
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
        self.cn_inspect = self.connections.cn_inspect

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(PerformanceSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(PerformanceSanity, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_netperf_within_vn(self):
        """Check the throughput between the VM's within the same VN"""
        return self.test_check_netperf_within_vn()

if __name__ == '__main__':
    unittest.main()
