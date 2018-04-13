from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.svc_health_check.base import BaseHC
import test
import time
from common import isolated_creds

class TestSvcHC(BaseHC, VerifySvcFirewall):

    @test.attr(type=['sanity','vcenter'])
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
            'Created a rule to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['sudo iptables --flush'])
        si_fixture.svm_list[0].run_cmd_on_vm(
            cmds=['sudo iptables -A FORWARD -i eth1 -o eth2 -j REJECT'])
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Flushing the iptables on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['sudo iptables --flush'])
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
    # end test_svc_hc_e2e_fail_svm

    
    @preposttest_wrapper
    def test_svc_trans_segment_hc_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='transparent',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='segment')
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Enabling bridging on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_trans_segment_right_hc_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='transparent',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='segment')
        si_fixture.associate_hc(hc_fixture.uuid, 'right')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig eth1 down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Enabling bridging on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig eth1 up'], as_sudo=True)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

    @preposttest_wrapper
    def test_svc_trans_segment_left_hc_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='transparent',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='segment')
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig eth1 down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Enabling bridging on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig eth1 up'], as_sudo=True)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

    @preposttest_wrapper
    def test_svc_trans_segment_scale_hc_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='transparent',
                                         create_svms=True, max_inst=10)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='segment')
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. Traffic should still go through because of ecmp')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)

        si_fixture.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)

        si_fixture.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[3].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[4].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[5].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[6].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[7].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[8].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)

        si_fixture.svm_list[9].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)

        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Enabling bridging on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[3].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[4].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[5].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[6].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[7].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[8].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[9].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

    @preposttest_wrapper
    def test_svc_trans_segment_serial_hc_fail_svm(self):
        ret_dict = self.verify_svc_chain(service_mode='transparent',
                                         create_svms=True, max_inst=3, svc_chain_type = 'serial')
        si_fixture = ret_dict['si_fixture']
        si_fixture2 = ret_dict['si_fixture2']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='segment')
        si_fixture.associate_hc(hc_fixture.uuid, 'right')
        si_fixture2.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        self.addCleanup(si_fixture2.disassociate_hc, hc_fixture.uuid)

        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        si_fixture.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        si_fixture.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        time.sleep(delay)

        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        self.logger.info(
            'Enabling bridging on SVM. This should cause HC to restore the SVC, by restoring leaked routes')
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)

        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

        si_fixture2.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        time.sleep(delay)
        si_fixture2.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        si_fixture2.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service down'], as_sudo=True)
        time.sleep(delay)

        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        si_fixture2.svm_list[0].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture2.svm_list[1].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)
        si_fixture2.svm_list[2].run_cmd_on_vm(cmds=['ifconfig br-service up'], as_sudo=True)

        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]

    @preposttest_wrapper
    def test_svc_hc_http(self):
        ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        hc_fixture = self.create_hc(
            hc_type='end-to-end', probe_type='HTTP', http_url='http://' + right_vm_fixture.vm_ip)
        self.logger.info(
            'Starting webserver on %s' % right_vm_fixture.vm_name)
        right_vm_fixture.start_webserver(listen_port=80)
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
        self.logger.info(
            'Stopping webserver on %s' % right_vm_fixture.vm_name)
        right_vm_fixture.stop_webserver()
        delay = ((hc_fixture.delay + hc_fixture.timeout)
                 * hc_fixture.max_retries) + 1
        self.logger.info('Will sleep for %ss for HC to kick in' % delay)
        time.sleep(delay)
        assert not self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False)
        self.logger.info(
            'Restarting webserver on %s' % right_vm_fixture.vm_name)
        right_vm_fixture.start_webserver(listen_port=80)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        # end test_svc_hc_http
