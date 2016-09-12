from base import PerfBaseIxia
import time
from tcutils.wrappers import preposttest_wrapper
import test

class PerfIxiaTest(PerfBaseIxia):

    @classmethod
    def setUpClass(cls):
        super(PerfIxiaTest, cls).setUpClass()

    #@preposttest_wrapper
    #def test_spirent_back_to_back(self):
    #    return self.run_spirent_perf_test('vivek-BackToBack1','TCP','v4',2,1)

    @preposttest_wrapper
    def test_spirent_flow_KVM(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Flow_KVM','TCP','v4',2,1)

    @preposttest_wrapper
    def test_spirent_flow_scale_KVM(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Flow_Scale_KVM','TCP','v4',2,1)

    @preposttest_wrapper
    def test_spirent_Throughput_KVM(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Throughput_KVM','TCP','v4',2,3)

    @preposttest_wrapper
    def test_spirent_Throughput_KVM_Jumbo(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Throughput_KVM_Jumbo','TCP','v4',2,3)

    @preposttest_wrapper
    def test_spirent_Throughput_KVM_SC(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Throughput_KVM_SC','TCP','v4',2,3)

'''
    @preposttest_wrapper
    def test_spirent_flow_DPDK(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Flow_DPDK','TCP','v4',2,1)

    @preposttest_wrapper
    def test_spirent_flow_scale_DPDK(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Flow_Scale_DPDK','TCP','v4',2,1)

    @preposttest_wrapper
    def test_spirent_Throughput_DPDK(self):
        return self.run_spirent_perf_test('Contrail_Perf2-Throughput_DPDK_SC','TCP','v4',2,1)

'''
#end PerfIxiaTest





