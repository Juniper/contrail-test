from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from base import BaseHC
import test

class TestSvcHC(BaseHC, VerifySvcFirewall):

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_hc_basic(self):
        ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
                                         create_svms=True, max_inst=1)
        hc_fixture = self.create_hc()
        si_fixture = ret_dict['si_fixture']
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()
    # end test_svc_hc_basic

    @preposttest_wrapper
    def test_svc_hc_e2e_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='end-to-end', http_url=right_vm_fixture.vm_ip)
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Causing a ifdown on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['sudo ifconfig eth1 down'])
        assert si_fixture.verify_hc_is_not_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Causing a ifup. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['sudo ifconfig eth1 up'])
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
    # end test_svc_hc_e2e_fail_svm
