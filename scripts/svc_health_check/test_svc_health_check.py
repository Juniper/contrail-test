from common.svc_health_check.base import BaseHC
from common.servicechain.firewall.verify import VerifySvcFirewall
from tcutils.wrappers import preposttest_wrapper
import test
import time
from common import isolated_creds
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name

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
    def test_svc_hc_link_local_attach_to_vmi(self):
        ''' test to attach a Svc HC to a VMI
            1. Create a VM in VN1
            2. Create a svc hc and attach to the VMI of VM1
            3. Verify that the SHC is found in the agent, and is active
        Maintainer : ankitja@juniper.net
        '''
        assert self.attach_to_vmi_common()


    def attach_to_vmi_common(self, hc_type='link-local'):
        # Only link-local type for non svmi
        vn_name = get_random_name('vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        vm1 = self.create_vm(vn_fixture, 'vm1',
                                    image_name='cirros')
        assert vm1.wait_till_vm_is_up()
        vm_port = vm1.vmi_ids[vm1.vn_fq_name]
        local_ip = vm1.vm_ip
        shc_fixture = self.create_hc(hc_type=hc_type)
        self.attach_shc_to_vmi(shc_fixture, vm1)
        self.addCleanup(self.detach_shc_from_vmi,
                        shc_fixture, vm1)
        assert vm1.verify_hc_in_agent()
        assert vm1.verify_hc_is_active()
        return True

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
        assert self.svc_hc_fail_svm_common()

    @preposttest_wrapper
    def test_svc_in_net_right_hc_link_local_fail_svm(self):
        ''' test to attach and validate link local svc hc to an in-net svc right VMI.
            1. Attach the SHC to the VMI of the SVM.
            2. Bring down the interface and validate the svc action
            3. Bring up the interface and validate the svc action 
        Maintainer : ankitja@juniper.net
        '''
        assert self.svc_hc_fail_svm_common(svc_mode='in-network', hc_type='link-local', intf='right' )
    @preposttest_wrapper
    def test_svc_in_net_left_hc_link_local_fail_svm(self):
        ''' test to attach and validate link local svc hc to an in-net svc left VMI.
            1. Attach the SHC to the VMI of the SVM.
            2. Bring down the interface and validate the svc action
            3. Bring up the interface and validate the svc action 
        Maintainer : ankitja@juniper.net
        '''
        assert self.svc_hc_fail_svm_common(svc_mode='in-network', hc_type='link-local', intf='left' )
    @preposttest_wrapper
    def test_svc_in_net_nat_left_hc_link_local_fail_svm(self):
        ''' test to attach and validate link local svc hc to an in-net-nat svc left VMI.
            1. Attach the SHC to the VMI of the SVM.
            2. Bring down the interface and validate the svc action
            3. Bring up the interface and validate the svc action 
        Maintainer : ankitja@juniper.net
        '''
        assert self.svc_hc_fail_svm_common(svc_mode='in-network-nat', hc_type='link-local', intf='left' )

    @preposttest_wrapper
    def test_svc_in_net_right_hc_end_to_end_fail_svm(self):
        ''' test to attach and validate end to endsvc hc to an in-net svc right VMI.
            1. Attach the SHC to the VMI of the SVM.
            2. Bring down the interface and validate the svc action
            3. Bring up the interface and validate the svc action 
        Maintainer : ankitja@juniper.net
        '''

        assert self.svc_hc_fail_svm_common(svc_mode='in-network', hc_type='end-to-end', intf='right' )

    def svc_hc_fail_svm_common(self, svc_mode='transparent', hc_type='segment', intf='right'):
        ret_dict = self.verify_svc_chain(service_mode=svc_mode,
                                         create_svms=True, max_inst=1)

        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        if hc_type == 'end-to-end':
            hc_fixture = self.create_hc(
                hc_type='end-to-end', http_url=right_vm_fixture.vm_ip)
        else:
            hc_fixture = self.create_hc(
                hc_type=hc_type)
        si_fixture.associate_hc(hc_fixture.uuid, intf)
        self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()
        if intf == 'left':
            vmi = 'eth1'
        else:
            vmi = 'eth2'
        self.logger.info(
            'Disabling bridging to stop forwarding on SVM. This should cause HC to fail the SVC, by withdrawing the leaked routes')
        local_ip = None
        for key in si_fixture.svm_list[0].local_ips:
            if key.find('mgmt') != -1:
                local_ip = si_fixture.svm_list[0].local_ips[key]
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig ' + vmi + ' down'], as_sudo=True, local_ip=local_ip)
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
        si_fixture.svm_list[0].run_cmd_on_vm(cmds=['ifconfig ' + vmi + ' up'], as_sudo=True, local_ip=local_ip)
        time.sleep(delay)
        assert si_fixture.verify_hc_is_active()
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=True)
        assert self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, 'left')[0]
        return True
    # end

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
