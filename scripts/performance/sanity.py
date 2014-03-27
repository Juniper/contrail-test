import os
import fixtures
import testtools

from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from contrail_test_init import ContrailTestInit
from performance.verify import PerformanceTest 

class PerformanceSanity(testtools.TestCase, PerformanceTest):

    def setUp(self):
        super (PerformanceSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect= self.connections.agent_inspect
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj=self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(PerformanceSanity, self).cleanUp()

    @preposttest_wrapper
    def test_performance_netperf_within_vn(self):
        """Check the throughput between the VM's within the same VN"""
        return self.test_check_netperf_within_vn()

    @preposttest_wrapper
    def test_performance_netperf_in_diff_vn(self):
        """Check the throughput between the VM's different VN"""
        return self.test_check_netperf_within_vn(no_of_vn=2)

    @preposttest_wrapper
    def test_performance_ping_latency_within_vn(self):
        """Check the throughput between the VM's within the same VN"""
        return self.test_ping_latency()

if __name__ == '__main__':
    unittest.main()
