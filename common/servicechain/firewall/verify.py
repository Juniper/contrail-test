import os
import re
from common.servicechain.verify import VerifySvcChain
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name

SVC_TYPE_PROPS = {
    'firewall': {'in-network-nat': 'tiny_nat_fw',
                 'in-network': 'tiny_in_net',
                 'transparent': 'tiny_trans_fw',
                 },
    'analyzer': {'transparent': 'analyzer',
                 'in-network' : 'analyzer',
                 }
}

class VerifySvcFirewall(VerifySvcChain):

    def verify_svc_span(self, in_net=False):
        vn1_name = get_random_name("left_vn")
        vn1_subnets = ['31.1.1.0/24']
        vm1_name = get_random_name('left_vm')
        vn2_name = get_random_name("right_vn")
        vn2_subnets = ['41.2.2.0/24']
        vm2_name = get_random_name('right_vm')
        if in_net:
            vn1_name = get_random_name("in_left_vn")
            vn1_subnets = ['32.1.1.0/24']
            vm1_name = get_random_name('in_left_vm')
            vn2_name = get_random_name("in_right_vn")
            vn2_subnets = ['42.2.2.0/24']
            vm2_name = get_random_name('in_right_vm')
        vn1_fixture = self.config_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.config_vn(vn2_name, vn2_subnets)

        vm1_fixture = self.config_vm(vm1_name, vn_fix=vn1_fixture)
        vm2_fixture = self.config_vm(vm2_name, vn_fix=vn2_fixture)
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        max_inst = 3
        st_name = get_random_name("tcp_svc_template")
        si_prefix = "tcp_bridge_"
        policy_name = get_random_name("allow_tcp")
        if in_net:
            st_name = get_random_name("in_tcp_svc_template")
            si_prefix = "in_tcp_bridge_"
            policy_name = get_random_name("in_allow_tcp")
            tcp_st_fixture, tcp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            tcp_st_fixture, tcp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst)
        action_list = [tcp_si_fixture.fq_name_str]
#        action_list = self.chain_si(si_count, si_prefix)
        # Update rule with specific port/protocol
        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'source_network': vn1_name,
                 'src_ports': [8000, 8000],
                 'dest_network': vn2_name,
                 'dst_ports': [9000, 9000],
                 'simple_action': None,
                 'action_list': {'apply_service': action_list}
                 }]

        # Create new policy with rule to allow traffci from new VN's
        tcp_policy_fixture = self.config_policy(policy_name, rule)

        self.verify_si(tcp_si_fixture)

        st_name = get_random_name("udp_svc_template")
        si_prefix = "udp_bridge_"
        policy_name = get_random_name("allow_udp")
        if in_net:
            st_name = get_random_name("in_udp_svc_template")
            si_prefix = "in_udp_bridge_"
            policy_name = get_random_name("in_allow_udp")
            udp_st_fixture, udp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            udp_st_fixture, udp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst)
        action_list = [udp_si_fixture.fq_name_str]
#        action_list = self.chain_si(si_count, si_prefix)
        # Update rule with specific port/protocol
        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'source_network': vn1_name,
                 'src_ports': [8001, 8001],
                 'dest_network': vn2_name,
                 'dst_ports': [9001, 9001],
                 'simple_action': None,
                 'action_list': {'apply_service': action_list}
                 }]

        # Create new policy with rule to allow traffci from new VN's
        udp_policy_fixture = self.config_policy(policy_name, rule)
        vn1_udp_policy_fix = self.attach_policy_to_vn(
            [tcp_policy_fixture, udp_policy_fixture], vn1_fixture)
        vn2_udp_policy_fix = self.attach_policy_to_vn(
            [tcp_policy_fixture, udp_policy_fixture], vn2_fixture)

        result, msg = self.validate_vn(vn1_name)
        assert result, msg
        result, msg = self.validate_vn(vn2_name)
        assert result, msg
        assert self.verify_si(udp_si_fixtures)

        # Install traffic package in VM
        vm1_fixture.install_pkg("Traffic")
        vm2_fixture.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'tcp', sport=sport, dport=dport)
        errmsg = "TCP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        self.delete_si_st(tcp_si_fixtures, tcp_st_fixture)

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'tcp', sport=sport, dport=dport)
        errmsg = "TCP traffic with src port %s and dst port %s passed; Expected to fail" % (
            sport, dport)
        assert sent and recv == 0, errmsg

        st_name = get_random_name("tcp_svc_template")
        si_prefix = "tcp_bridge_"
        policy_name = get_random_name("allow_tcp")
        if in_net:
            st_name = get_random_name("in_tcp_svc_template")
            si_prefix = "in_tcp_bridge_"
            policy_name = get_random_name("in_allow_tcp")
            tcp_st_fixture, tcp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            tcp_st_fixture, tcp_si_fixture = self.config_st_si(
                st_name, si_prefix, max_inst=max_inst)
        action_list = [tcp_si_fixture.fq_name_str]
#        action_list = self.chain_si(si_count, si_prefix)
        result, msg = self.validate_vn(vn1_name)
        assert result, msg
        result, msg = self.validate_vn(vn2_name)
        assert result, msg
        self.verify_si(tcp_si_fixtures)

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(vm1_fixture, vm2_fixture,
                                         'tcp', sport=sport, dport=dport)
        errmsg = "TCP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg


    def verify_multi_inline_svc(self, *args, **kwargs):
        ret_dict = self.config_multi_inline_svc(*args, **kwargs)
        proto = kwargs.get('proto', 'any')
        left_vn_fq_name = ret_dict.get('left_vn_fixture').vn_fq_name
        right_vn_fq_name = ret_dict.get('right_vn_fixture').vn_fq_name
        left_vm_fixture = ret_dict.get('left_vm_fixture')
        right_vm_fixture = ret_dict.get('right_vm_fixture')
        st_fixtures = ret_dict.get('st_fixtures')
        si_fixtures = ret_dict.get('si_fixtures')

        for i in range(len(st_fixtures)):
            assert st_fixtures[i].verify_on_setup(), 'ST Verification failed'
            assert si_fixtures[i].verify_on_setup(), 'SI Verification failed'

        result, msg = self.validate_vn(left_vn_fq_name)
        assert result, msg
        result, msg = self.validate_vn(right_vn_fq_name, right_vn=True)
        assert result, msg

        result, msg = self.validate_svc_action(
            left_vn_fq_name, si_fixtures[0], right_vm_fixture, src='left')
        assert result, msg
        if st_fixtures[0].service_mode != 'in-network-nat':
            result, msg = self.validate_svc_action(
                right_vn_fq_name, si_fixtures[0], left_vm_fixture, src='right')
            assert result, msg

        if proto not in ['any', 'icmp']:
            self.logger.info('Will skip Ping test')
        else:
            # Ping from left VM to right VM
            errmsg = "Ping to Right VM %s from Left VM failed" % right_vm_fixture.vm_ip
            assert left_vm_fixture.ping_with_certainty(
                right_vm_fixture.vm_ip, count='3'), errmsg
        return ret_dict
    # end verify_multi_inline_svc

    def verify_policy_delete_add(self, si_test_dict):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        si_fixture = si_test_dict['si_fixture']
        left_vn_fixture = si_test_dict['left_vn_fixture']
        right_vn_fixture = si_test_dict['right_vn_fixture']

        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.unconfig_policy(policy_fixture)
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg

        # Create policy again
        policy_fixture = self.config_policy(policy_fixture.policy_name,
                                            policy_fixture.rules_list)
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        assert self.verify_si(si_fixture)

        # Wait for the existing flow entry to age
        self.sleep(40)

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        return True
    # end verify_policy_delete_add

    def verify_protocol_port_change(self, si_test_dict, mode='transparent'):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        left_vn_fixture = si_test_dict['left_vn_fixture']
        right_vn_fixture = si_test_dict['right_vn_fixture']
        si_fixture = si_test_dict['si_fixture']

        # Install traffic package in VM
        left_vm_fixture.install_pkg("Traffic")
        right_vm_fixture.install_pkg("Traffic")

        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sport = 8000
        dport = 9001
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'tcp', sport=sport, dport=dport)
        errmsg = "TCP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.unconfig_policy(policy_fixture)

        # Update rule with specific port/protocol
        #action_list = {'apply_service': self.action_list}
        action_list = policy_fixture.rules_list[0]['action_list']
        new_rule = {'direction': '<>',
                    'protocol': 'tcp',
                    'source_network': si_test_dict['left_vn_fixture'].vn_fq_name,
                    'src_ports': [8000, 8000],
                    'dest_network': si_test_dict['right_vn_fixture'].vn_fq_name,
                    'dst_ports': [9001, 9001],
                    'simple_action': None,
                    'action_list': action_list
                    }
        rules = [new_rule]

        # Create new policy with rule to allow traffci from new VN's
        policy_fixture = self.config_policy(policy_fixture.policy_name, rules)

        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        assert self.verify_si(si_fixture)

        self.logger.debug("Send udp traffic; with policy rule %s", new_rule)
        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s passed; Expected to fail" % (
            sport, dport)
        assert sent and recv == 0, errmsg

        sport = 8000
        dport = 9001
        self.logger.debug("Send tcp traffic; with policy rule %s", new_rule)
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'tcp', sport=sport, dport=dport)
        errmsg = "TCP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
    # verify_protocol_port_change

    def verify_add_new_vns(self, si_test_dict):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        si_fixture = si_test_dict['si_fixture']
        left_vn_fixture = si_test_dict['left_vn_fixture']
        right_vn_fixture = si_test_dict['right_vn_fixture']
        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.unconfig_policy(policy_fixture)

        # Create one more left and right VN's
        new_left_vn = "new_left_bridge_vn"
        new_left_vn_net = [get_random_cidr(af=self.inputs.get_af())]
        new_right_vn = "new_right_bridge_vn"
        new_right_vn_net = [get_random_cidr(af=self.inputs.get_af())]
        new_left_vn_fix = self.config_vn(new_left_vn, new_left_vn_net)
        new_right_vn_fix = self.config_vn(new_right_vn, new_right_vn_net)

        # Launch VMs in new left and right VN's
        new_left_vm = 'new_left_bridge_vm'
        new_right_vm = 'new_right_bridge_vm'
        new_left_vm_fix = self.config_vm(new_left_vm, vn_fix=new_left_vn_fix)
        new_right_vm_fix = self.config_vm(new_right_vm, vn_fix=new_right_vn_fix)
        # Wait for VM's to come up
        new_left_vm_fix.wait_till_vm_is_up()
        new_right_vm_fix.wait_till_vm_is_up()

        # Add rule to policy to allow traffic from new left_vn to right_vn
        # through SI
        action_list = policy_fixture.input_rules_list[0]['action_list']
        new_rule = {'direction': '<>',
                    'protocol': 'any',
                    'source_network': new_left_vn,
                    'src_ports': [0, 65535],
                    'dest_network': new_right_vn,
                    'dst_ports': [0, 65535],
                    'simple_action': action_list.get('simple_action', None),
                    'action_list': action_list,
                    }
        rules = policy_fixture.input_rules_list
        rules.append(new_rule)

        # Create new policy with rule to allow traffic from new VN's
        policy_fixture = self.config_policy(policy_fixture.policy_name, rules)
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        # attach policy to new VN's
        new_policy_left_vn_fix = self.attach_policy_to_vn(
            policy_fixture, new_left_vn_fix)
        new_policy_right_vn_fix = self.attach_policy_to_vn(
            policy_fixture, new_right_vn_fix)

        self.verify_si(si_fixture)

        # Ping from left VM to right VM
        self.sleep(5)
        self.logger.info("Verfiy ICMP traffic between new VN's.")
        errmsg = "Ping to right VM ip %s from left VM failed" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            new_right_vm_fix.vm_ip), errmsg

        self.logger.info(
            "Verfiy ICMP traffic between new left VN and existing right VN.")
        errmsg = "Ping to right VM ip %s from left VM passed; \
                  Expected tp Fail" % right_vm_fixture.vm_ip
        assert new_left_vm_fix.ping_with_certainty(right_vm_fixture.vm_ip,
                                                   expectation=False), errmsg

        self.logger.info(
            "Verfiy ICMP traffic between existing VN's with allow all.")
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg

        self.logger.info(
            "Verfiy ICMP traffic between existing left VN and new right VN.")
        errmsg = "Ping to right VM ip %s from left VM passed; \
                  Expected to Fail" % new_right_vm_fix.vm_ip
        assert left_vm_fixture.ping_with_certainty(new_right_vm_fix.vm_ip,
                                                    expectation=False), errmsg

        # Ping between left VN's
        self.logger.info(
            "Verfiy ICMP traffic between new left VN and existing left VN.")
        errmsg = "Ping to left VM ip %s from another left VM in different VN \
                  passed; Expected to fail" % left_vm_fixture.vm_ip
        assert new_left_vm_fix.ping_with_certainty(left_vm_fixture.vm_ip,
                                                   expectation=False), errmsg

        self.logger.info(
            "Verfiy ICMP traffic between new right VN and existing right VN.")
        errmsg = "Ping to right VM ip %s from another right VM in different VN \
                  passed; Expected to fail" % right_vm_fixture.vm_ip
        assert new_right_vm_fix.ping_with_certainty(right_vm_fixture.vm_ip,
                                                    expectation=False), errmsg
        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.detach_policy(new_policy_left_vn_fix)
        self.detach_policy(new_policy_right_vn_fix)
        self.unconfig_policy(policy_fixture)

        # Add rule to policy to allow only tcp traffic from new left_vn to right_vn
        # through SI
        rules.remove(new_rule)
        udp_rule = {'direction': '<>',
                    'protocol': 'udp',
                    'source_network': new_left_vn,
                    'src_ports': [8000, 8000],
                    'dest_network': new_right_vn,
                    'dst_ports': [9000, 9000],
                    'simple_action': action_list['simple_action'],
                    'action_list': {'apply_service': action_list['apply_service']}
                    }
        rules.append(udp_rule)

        # Create new policy with rule to allow traffci from new VN's
        policy_fixture = self.config_policy(policy_fixture.policy_name, rules)
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        # attach policy to new VN's
        new_policy_left_vn_fix = self.attach_policy_to_vn(
            policy_fixture, new_left_vn_fix)
        new_policy_right_vn_fix = self.attach_policy_to_vn(
            policy_fixture, new_right_vn_fix)
        self.verify_si(si_fixture)

        # Ping from left VM to right VM with udp rule
        self.logger.info(
            "Verify ICMP traffic with allow udp only rule from new left VN to new right VN")
        errmsg = "Ping to right VM ip %s from left VM passed; Expected to fail" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(new_right_vm_fix.vm_ip,
                                                   expectation=False), errmsg
        # Install traffic package in VM
        left_vm_fixture.install_pkg("Traffic")
        right_vm_fixture.install_pkg("Traffic")
        new_left_vm_fix.install_pkg("Traffic")
        new_right_vm_fix.install_pkg("Traffic")

        self.logger.info(
            "Verify UDP traffic with allow udp only rule from new left VN to new right VN")
        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(new_left_vm_fix, new_right_vm_fix,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        self.logger.info("Verfiy ICMP traffic with allow all.")
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        self.logger.info("Verify UDP traffic with allow all")
        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        # Delete policy
        self.delete_vm(new_left_vm_fix)
        self.delete_vm(new_right_vm_fix)
        self.detach_policy(new_policy_left_vn_fix)
        self.detach_policy(new_policy_right_vn_fix)
        self.delete_vn(new_left_vn_fix)
        self.delete_vn(new_right_vn_fix)
        self.verify_si(si_fixture)

        self.logger.info(
            "Icmp traffic with allow all after deleting the new left and right VN.")
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
    # end verify_add_new_vns

    def verify_add_new_vms(self, si_test_dict):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        si_fixture = si_test_dict['si_fixture']
        left_vn_fixture = si_test_dict['left_vn_fixture']
        right_vn_fixture = si_test_dict['right_vn_fixture']

        # Launch VMs in new left and right VN's
        new_left_vm = 'new_left_bridge_vm'
        new_right_vm = 'new_right_bridge_vm'
        new_left_vm_fix = self.config_vm(new_left_vm, vn_fix=left_vn_fixture)
        new_right_vm_fix = self.config_vm(new_right_vm, vn_fix=right_vn_fixture)
        # Wait for VM's to come up
        assert new_left_vm_fix.wait_till_vm_is_up()
        assert new_right_vm_fix.wait_till_vm_is_up()

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            new_right_vm_fix.vm_ip), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed" % new_right_vm_fix.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            new_right_vm_fix.vm_ip), errmsg

        # Install traffic package in VM
        left_vm_fixture.install_pkg("Traffic")
        right_vm_fixture.install_pkg("Traffic")
        self.logger.debug("Send udp traffic; with policy rule allow all")
        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.unconfig_policy(policy_fixture)

        # Add rule to policy to allow traffic from new left_vn to right_vn
        # through SI
        action_list = policy_fixture.rules_list[0]['action_list']
        new_rule = {'direction': '<>',
                    'protocol': 'udp',
                    'source_network': left_vn_fixture.vn_name,
                    'src_ports': [8000, 8000],
                    'dest_network': right_vn_fixture.vn_name,
                    'dst_ports': [9000, 9000],
                    'simple_action': None,
                    'action_list': {'apply_service': action_list}
                    }
        rules = [new_rule]

        # Create new policy with rule to allow traffci from new VN's
        policy_fixture = self.config_policy(policy_fixture.policy_name, rules)
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        self.verify_si(si_fixture)

        # Install traffic package in VM
        new_left_vm_fix.install_pkg("Traffic")
        new_right_vm_fix.install_pkg("Traffic")

        self.logger.debug("Send udp traffic; with policy rule %s", new_rule)
        sport = 8000
        dport = 9000
        sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sent, recv = self.verify_traffic(left_vm_fixture, new_right_vm_fix,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sent, recv = self.verify_traffic(new_left_vm_fix, new_right_vm_fix,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        sent, recv = self.verify_traffic(new_left_vm_fix, right_vm_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed; Expected to fail" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            new_right_vm_fix.vm_ip, expectation=False), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed; Expected to fail" % self.vm2_fixture.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed; Expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg

        errmsg = "Ping to right VM ip %s from left VM passed; Expected to fail" % new_right_vm_fix.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            new_right_vm_fix.vm_ip, expectation=False), errmsg

    # end verify_add_new_vms

    def verify_firewall_with_mirroring(
        self, max_inst=1,
            firewall_svc_mode='in-network', mirror_svc_mode='transparent'):
        """Validate the service chaining in network  datapath"""

        #TODO
        # max_inst cannot be more than one in this method since
        # analyzer packet count verification logic needs to be updated when
        # in case of more than one mirror SVM
        max_inst = 1

        vn1_name = get_random_name('left_vn')
        vn2_name = get_random_name('right_vn')
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vm1_name = get_random_name("in_network_vm1")
        vm2_name = get_random_name("in_network_vm2")
        action_list = []
        firewall_st_name = get_random_name("svc_firewall_template_1")
        firewall_si_prefix = get_random_name("svc_firewall_instance")
        mirror_st_name = get_random_name("svc_mirror_template_1")
        mirror_si_prefix = get_random_name("svc_mirror_instance")
        policy_name = get_random_name("policy_in_network")

        mgmt_vn_fixture = self.config_vn(get_random_name('mgmt'),
                                         [get_random_cidr(af=self.inputs.get_af())])
        vn1_fixture = self.config_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.config_vn(vn2_name, vn2_subnets)
        vns = [mgmt_vn_fixture, vn1_fixture, vn2_fixture]

        st_fixture = self.config_st(firewall_st_name,
                                    service_type='firewall',
                                    service_mode=firewall_svc_mode,
                                    mgmt=getattr(mgmt_vn_fixture, 'vn_fq_name', None),
                                    left=vn1_fixture.vn_fq_name,
                                    right=vn2_fixture.vn_fq_name)
        svm_fixtures = self.create_service_vms(vns,
                                               service_mode=st_fixture.service_mode,
                                               service_type=st_fixture.service_type,
                                               max_inst=max_inst)
        firewall_si_fixture = self.config_si(firewall_si_prefix,
                                    st_fixture,
                                    max_inst=max_inst,
                                    mgmt_vn_fq_name=getattr(mgmt_vn_fixture, 'vn_fq_name', None),
                                    left_vn_fq_name=vn1_fixture.vn_fq_name,
                                    right_vn_fq_name=vn2_fixture.vn_fq_name,
                                    svm_fixtures=svm_fixtures)
        assert firewall_si_fixture.verify_on_setup()


        action_list = [firewall_si_fixture.fq_name_str]

        mirror_st_fixture = self.config_st(mirror_st_name,
                                           service_type='analyzer',
                                           service_mode=mirror_svc_mode,
                                           left=vn1_fixture.vn_fq_name)
        mirror_svm_fixtures = self.create_service_vms([vn1_fixture],
                                  service_mode=mirror_st_fixture.service_mode,
                                  service_type=mirror_st_fixture.service_type,
                                  max_inst=max_inst)
        mirror_si_fixture = self.config_si(mirror_si_prefix,
                                           mirror_st_fixture,
                                           max_inst=max_inst,
                                           left_vn_fq_name=vn1_fixture.vn_fq_name,
                                           svm_fixtures=mirror_svm_fixtures)
        assert mirror_si_fixture.verify_on_setup()
        action_list += [mirror_si_fixture.fq_name_str]
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1_name,
                'src_ports': [0, 65535],
                'dest_network': vn2_name,
                'dst_ports': [0, 65535],
                'simple_action': 'pass',
                'action_list': {'simple_action': 'pass',
                                'mirror_to': {'analyzer_name': action_list[1]},
                                'apply_service': action_list[:1]}
            },
        ]

        policy_fixture = self.config_policy(policy_name, rules)

        vn1_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn1_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn2_fixture)

        vm1_fixture = self.config_vm(vm1_name, vn_fix=vn1_fixture)
        vm2_fixture = self.config_vm(vm2_name, vn_fix=vn2_fixture)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        result, msg = self.validate_vn(vn1_fixture.vn_fq_name)
        assert result, msg
        result, msg = self.validate_vn(vn2_fixture.vn_fq_name)
        assert result, msg
        assert self.verify_si(firewall_si_fixture)
        assert self.verify_si(mirror_si_fixture)

        svms = self.get_svms_in_si(firewall_si_fixture)
        svm_node_ip = self.get_svm_compute(svms[0].name)['host_ip']
        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % vm2_fixture.vm_ip
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip), errmsg

        # Verify ICMP mirror
        sessions = self.tcpdump_on_all_analyzer(mirror_si_fixture,
                                                mirror_si_prefix)
        errmsg = "Ping to right VM ip %s from left VM failed" % vm2_fixture.vm_ip
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            if vm1_fixture.vm_node_ip == vm2_fixture.vm_node_ip:
                if firewall_svc_mode == 'transparent':
                    count = 20
                else:
                    count = 10
            if vm1_fixture.vm_node_ip != vm2_fixture.vm_node_ip:
                if firewall_svc_mode == 'in-network' and vm1_fixture.vm_node_ip == svm_node_ip:
                    count = 10
                else:
                    count = 20
            self.verify_icmp_mirror(svm_name, session, pcap, count)
    # end verify_firewall_with_mirroring

    def verify_ecmp_hash(self, vn_fixture=None, left_vm_fixture=None, right_vm_fixture=None, ecmp_hash='default'):
        """Verify ECMP configuration hash at Agent and control node """
        # Sleeping for 10 secs for route update to takes place for ecmp_hash
        # config fileds
        self.logger.info('Sleeping for 10 seconds for route update to takes place')
        self.sleep(10)
        self.verify_ecmp_hash_at_agent(ecmp_hash=ecmp_hash,vn_fixture=vn_fixture,
                                       left_vm_fixture=left_vm_fixture,
                                       right_vm_fixture=right_vm_fixture)
    # end verify_ecmp_hash

    def verify_ecmp_hash_at_agent(self, vn_fixture=None, left_vm_fixture=None, right_vm_fixture=None, ecmp_hash='default'):
        """Verify ECMP configuration hash """
         # Default ECMP hash with 5 tuple
        if ecmp_hash == 'default':
            ecmp_hash = {"source_ip": True, "destination_ip": True,
                         "source_port": True, "destination_port": True,
                         "ip_protocol": True}

        ecmp_hash_config=[]
        # ECMP Hash fileds displayed at agent is different from configured
        # values. Mapping is: source_ip : l3-source-address, destination_ip:
        # l3-destination-address etc..
        if 'source_ip' in ecmp_hash:
            ecmp_hash_config.append('l3-source-address')
        if 'destination_ip' in ecmp_hash:
            ecmp_hash_config.append('l3-destination-address')
        if 'source_port' in ecmp_hash:
            ecmp_hash_config.append('l4-source-port')
        if 'destination_port' in ecmp_hash:
            ecmp_hash_config.append('l4-destination-port')
        if 'ip_protocol' in ecmp_hash:
            ecmp_hash_config.append('l4-protocol')

        # Get the ECMP hash next hops at agent
        (domain, project, vn) = vn_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[left_vm_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = left_vm_fixture.get_matching_vrf( agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']

        # Get the ECMP Hashing fields at agent
        ecmp_hashing_fileds = inspect_h.get_vna_active_route(vrf_id=vn_vrf_id, ip=right_vm_fixture.vm_ip, prefix='32')['path_list'][0]['ecmp_hashing_fields']
        ecmp_hash_at_agent = ecmp_hashing_fileds.split(',')

        # Removing the empty elements
        ecmp_hash_at_agent = filter(None, ecmp_hash_at_agent)

        # Compare ECMP hash configured value with value programmed at agent
        if set(ecmp_hash_at_agent) == set(ecmp_hash_config):
            result =True
            self.logger.info('ECMP Hash is configured properly at Agent: {%s}' % ecmp_hashing_fileds)
        else:
            result = False
            assert result, 'ECMP Hash is incorrect at Agent. Configured ECMP Hash is: %s, ECMP Hash present at Agent is:%s' % (ecmp_hash_config, ecmp_hash_at_agent)
        return result
    # end verify_ecmp_hash_at_agent

