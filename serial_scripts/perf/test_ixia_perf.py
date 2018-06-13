from base import PerfBase
import time
from tcutils.wrappers import preposttest_wrapper
import test

class PerfIxiaTest(PerfBase):

    @classmethod
    def setUpClass(cls):
        super(PerfIxiaTest, cls).setUpClass()

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_0PPS_latency_DPDK_4core(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_64_200_IMIX_dpdk_4ports_new.ixncfg',
                                   proto='TCP',family='v4',cores=3,si=2,image='dpdk_l2fwd_sleep3', zone='dpdk')

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_0PPS_jitter_DPDK_4core(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_64_200_IMIX_dpdk_4ports_new.ixncfg',
                                   proto='TCP',family='v4',cores=3,si=2,image='dpdk_l2fwd_sleep3', zone='dpdk')


    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_1460latency_DPDK_4core(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_1460_dpdk_4ports.ixncfg',
                                   proto='TCP',family='v4',cores=3,si=2,image='dpdk_l2fwd_sleep3', zone='dpdk',encap='MPLSoUDP')

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_1460jitter_DPDK_4core(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_1460_dpdk_4ports.ixncfg',
                                   proto='TCP',family='v4',cores=3,si=2,image='dpdk_l2fwd_sleep3', zone='dpdk',encap='MPLSoUDP')


    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_0PPS_jitter_DPDK_4core_v6(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_64_200_IMIX_dpdk_4ports_ipv6.ixncfg',
                                      proto='TCP',family='dual',cores=3,si=2,image='dpdk_l2fwd_sleep3',zone='dpdk')

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_0PPS_latency_DPDK_4core_v6(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_64_200_IMIX_dpdk_4ports_ipv6.ixncfg',
                                    proto='TCP',family='dual',cores=3,si=2,image='dpdk_l2fwd_sleep3',zone='dpdk')

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_1460_PPS_jitter_DPDK_4core_v6(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_1460_dpdk_4ports_ipv6.ixncfg',
                                    proto='TCP',family='dual',cores=3,si=2,image='dpdk_l2fwd_sleep3',zone=dpdk,encap='MPLSoUDP')

    @test.attr(type=['perf_DPDK','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_1460_PPS_latency_DPDK_4core_v6(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_1460_dpdk_4ports_ipv6.ixncfg',
                                    proto='TCP',family='dual',cores=3,si=2,image='dpdk_l2fwd_sleep3',zone=dpdk,encap='MPLSoUDP')

    @test.attr(type=['perf_KVM','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_latency_KVM(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_64_200_IMIX_kvm_4ports.ixncfg',
                                            proto='TCP',family='v4',cores=2,si=3,image='perf-ubuntu-1404')

    @test.attr(type=['perf_KVM','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_jitter_KVM(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_64_200_IMIX_kvm_4ports.ixncfg',
                                            proto='TCP',family='v4',cores=2,si=3,image='perf-ubuntu-1404')

    @test.attr(type=['perf_KVM','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_1460latency_KVM_4core_mplsoudp(self):
        return self.run_perf_tests(profile_name='pps_1_vms_latency_binary_1460_kvm_4ports.ixncfg',
                                            proto='TCP',family='v4',cores=2,si=3,image='perf-ubuntu-1404',encap='MPLSoUDP')

    @test.attr(type=['perf_KVM','perf_ixia'])
    @preposttest_wrapper
    def test_ixia_PPS_1460jitter_KVM_4core_mplsoudp(self):
        return self.run_perf_tests(profile_name='pps_1_vms_jitter_binary_1460_kvm_4ports.ixncfg',
                                            proto='TCP',family='v4',cores=2,si=3,image='perf-ubuntu-1404',encap='MPLSoUDP')


