import os
import fixtures
import testtools

from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from common.contrail_test_init import ContrailTestInit
from performance.verify import PerformanceTest


class PerformanceSanity(testtools.TestCase, PerformanceTest):

    def setUp(self):
        super(PerformanceSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = ContrailTestInit(self.ini_file)
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect = self.connections.agent_inspect
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(PerformanceSanity, self).cleanUp()

    @preposttest_wrapper
    def test_performance_netperf_within_vn_TCP_STREAM(self):
        """Check the throughput between the VM's within the same VN for TCP_STREAM"""
        return self.test_check_netperf_within_vn(duration=60)

    @preposttest_wrapper
    def test_performance_netperf_within_vn_TCP_STREAM_with_MPLSoGRE(self):
        """Check the throughput between the VM's within the same VN for TCP_STREAM using MPLSoGRE"""
        return self.test_check_netperf_within_vn(encap='MPLSoGRE', duration=60)

    @preposttest_wrapper
    def test_performance_netperf_within_vn_TCP_RR(self):
        """TCP Request/Response test between the VM's within the same VN"""
        return self.test_check_netperf_within_vn(test_name='TCP_RR')

    @preposttest_wrapper
    def test_performance_netperf_within_vn_with_UDP_STREAM(self):
        """Check the throughput between the VM's within the same VN for UDP_STREAM"""
        return self.test_check_netperf_within_vn(test_name='UDP_STREAM', duration=60)

    @preposttest_wrapper
    def test_performance_netperf_within_vn_UDP_STREAM_with_MPLSoGRE(self):
        """Check the throughput between the VM's within the same VN for UDP_STREAM using MPLSoGRE"""
        return self.test_check_netperf_within_vn(encap='MPLSoGRE', duration=60)

    @preposttest_wrapper
    def test_performance_netperf_within_vn_UDP_RR(self):
        """UDP Request/Response test between the VM's within the same VN"""
        return self.test_check_netperf_within_vn(test_name='UDP_RR')

    @preposttest_wrapper
    def test_performance_netperf_in_diff_vn(self):
        """Check the throughput between the VM's different VN"""
        return self.test_check_netperf_within_vn(no_of_vn=2)

    @preposttest_wrapper
    def test_performance_ping_latency_within_vn(self):
        """Check the ping latency between the VM's within the same VN"""
        return self.test_ping_latency()

    @preposttest_wrapper
    def test_performance_ping_latency_within_vn_icmp_flood(self):
        """Check the ping latency between the VM's within the same VN"""
        return self.test_ping_latency(no_of_pkt=20)

    @preposttest_wrapper
    def test_flow_setup_within_vn_1000_flows(self):
        """Check the flow setup rate between the VM's within the same VN"""
        return self.test_check_flow_setup_within_vn(no_of_flows=1000, dst_port_min=1000, dst_port_max=2001,
                                                    src_port_min=10000, src_port_max=10000)

    @preposttest_wrapper
    def test_flow_setup_within_vn_20000_flows(self):
        """Check the flow setup rate between the VM's within the same VN"""
        return self.test_check_flow_setup_within_vn(no_of_flows=20000, dst_port_min=1000, dst_port_max=21000,
                                                    src_port_min=10000, src_port_max=10000)
if __name__ == '__main__':
    unittest.main()
