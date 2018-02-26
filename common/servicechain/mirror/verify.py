import os
from time import sleep
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from tcutils.util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from config import ConfigSvcMirror
from common.servicechain.verify import VerifySvcChain
from common.ecmp.ecmp_verify import ECMPVerify
from common.floatingip.config import CreateAssociateFip
from random import randint
from tcutils.tcpdump_utils import *

class VerifySvcMirror(ConfigSvcMirror, VerifySvcChain, ECMPVerify):

    def verify_svc_mirroring(self, *args, **kwargs):
        ret_dict = self.config_svc_mirroring(*args, **kwargs)
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        if self.inputs.is_ci_setup():
            return self.verify_mirroring(si_fixture, left_vm_fixture,
                                         right_vm_fixture)
        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                       right_vm_fixture, 'icmp')
        return ret_dict
    # end verify_svc_mirroring

    def _verify_proto_based_mirror(self, si_fixture, left_vm_fixture,
                                  right_vm_fixture, proto, dest_ip=None,
                                  replies=True):
        '''
        For icmp and udp traffic
        '''
        if not dest_ip:
            dest_ip = right_vm_fixture.vm_ip

        svm = self.get_svms_in_si(si_fixture)

        sessions = self.tcpdump_on_all_analyzer(si_fixture)

        if self.inputs.pcap_on_vm:
            vm_fix_pcap_pid_files = sessions[0]
            sessions = sessions[1]

        svm = self.get_svms_in_si(si_fixture)
        for svm_name, (session, pcap) in sessions.items():
            if proto == 'icmp':
                count = 5
                if replies:
                    count += 5
                errmsg = "Ping to right VM ip %s from left VM %s" % (
                    dest_ip, 'failed' if replies else 'passed')
                result = left_vm_fixture.ping_to_ip(dest_ip)
                assert result if replies else not result, errmsg
            elif proto == 'udp':
                sport = 8001
                dport = 9001
                sent, recv = self.verify_traffic(left_vm_fixture, right_vm_fixture,
                                                 proto, sport=sport, dport=dport)
                errmsg = "UDP traffic with src port %s and dst port %s failed" % (
                    sport, dport)
                assert sent and recv == sent, errmsg
                count = sent
            # end if
            if replies and si_fixture.service_mode == 'transparent' and \
                left_vm_fixture.vm_node_ip != right_vm_fixture.vm_node_ip:
                count = count * 2
            if proto == 'icmp':
                if not self.inputs.pcap_on_vm:
                    assert self.verify_icmp_mirror(svm_name, session, pcap, count)
                else:
                    svm_list = si_fixture._svm_list
                    self.pcap_on_all_vms_and_verify_mirrored_traffic(src_vm_fix=left_vm_fixture,
                            dst_vm_fix=right_vm_fixture,
                            svm_fixtures=svm_list,
                            count=count)
                    break

            elif proto == 'udp':
                if not self.inputs.pcap_on_vm:
                    assert self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')
                else:
                    output, mirror_pkt_count = self.stop_tcpdump(None, None, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files, pcap_on_vm=True)
                    errmsg = "%s UDP Packets mirrored to the analyzer VM %s,"\
                         "Expected %s packets" % (
                             mirror_pkt_count, svm_list, count)
                    if mirror_pkt_count < count:
                        self.logger.error(errmsg)
                        assert False, errmsg
                    self.logger.info("%s UDP packets are mirrored to the analyzer "
                                     "service VM '%s', tcpdump on VM", mirror_pkt_count, svm_list)
                    return True

        return
    # end verify_proto_based_mirror

    def verify_svc_mirroring_with_floating_ip(self, *args, **kwargs):
        """Validate the service mirrroring with flaoting IP
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Assosciate vm2 with floating IP
           3. Create the policy rule for ICMP/UDP and attach to vn's
           4. Send the traffic from vm1 to vm2(floating ip) and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
        ret_dict = self.config_svc_mirroring(*args, **kwargs)
        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']


        fip_pool_name = get_random_name('testpool')

        si_fq_name = [ si_fixture.fq_name_str ]
        rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': left_vn_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': left_vn_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name[0]}}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': left_vn_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': left_vn_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name[0]}}
                       }
                      ]
        policy_fixture.update_policy_api(rules)

        fip_fixture = self.config_fip(
            left_vn_fixture.vn_id, pool_name=fip_pool_name)
        fip_ca = self.useFixture(CreateAssociateFip(self.inputs, fip_fixture,
                                                         left_vn_fixture.vn_id,
                                                         right_vm_fixture.vm_id))
        fip = right_vm_fixture.vnc_lib_h.floating_ip_read(id=fip_ca.fip_id).\
            get_floating_ip_address()

        assert self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                    right_vm_fixture, 'icmp', dest_ip=fip)

    def verify_svc_mirror_with_deny(self):
        """Validate the service chaining mirroring with deny rule
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Create the policy rule for ICMP/UDP with deny rule and attach to vn's
           4. Cretae the dynamic policy with rule to mirror the pkts to analyzer and attach to VN's
           5. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           Ping from should fail, only the pkts from vm1 should get mirrored.
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
        ret_dict = self.config_svc_mirroring()
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']
        dynamic_policy_name = get_random_name("mirror_policy")
        rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': left_vn_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': right_vn_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'deny',
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': left_vn_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': right_vn_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'deny',
                       }]
        policy_fixture.update_policy_api(rules)
        si_fq_name = si_fixture.fq_name_str
        rules[0]['action_list'] = {'simple_action': 'pass',
                                   'mirror_to': {
                                       'analyzer_name': si_fq_name}}
        rules[1]['action_list'] = rules[0]['action_list']
        dynamic_policy_fixture = self.config_policy(
            dynamic_policy_name, rules)
        vn1_dynamic_policy_fix = self.attach_policy_to_vn(
            dynamic_policy_fixture, left_vn_fixture, policy_type='dynamic')
        vn2_dynamic_policy_fix = self.attach_policy_to_vn(
            dynamic_policy_fixture, right_vn_fixture, policy_type='dynamic')
        result, msg = self.validate_vn(left_vn_fixture.vn_fq_name)
        assert result, msg
        result, msg = self.validate_vn(right_vn_fixture.vn_fq_name)
        assert result, msg
        self.verify_si(si_fixture)

        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                        right_vm_fixture, 'icmp', replies=False)
        return True
    # end verify_svc_mirror_with_deny

    def verify_icmp_mirror_on_all_analyzer(self, sessions, left_vm_fix, right_vm_fix, expectation=True):
        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fix.vm_ip
        if not expectation:
            errmsg = "Ping to right VM ip %s from left VM passed, Expected to fail" % right_vm_fix.vm_ip
        assert left_vm_fix.ping_to_ip(
            right_vm_fix.vm_ip, expectation=expectation), errmsg

        count = 10
        if not expectation:
            count = 0
        if left_vm_fix.vm_node_ip != right_vm_fix.vm_node_ip:
            count = count * 2
        for svm_name, (session, pcap) in sessions.items():
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_icmp_mirror(self, svm_name, session, pcap, exp_count):
        mirror_pkt_count = self.stop_tcpdump(session, pcap)
        errmsg = "%s ICMP Packets mirrored to the analyzer VM %s,"\
                 "Expected %s packets" % (
                     mirror_pkt_count, svm_name, exp_count)
        if mirror_pkt_count < exp_count:
            self.logger.error(errmsg)
            assert False, errmsg
        self.logger.info("%s ICMP packets are mirrored to the analyzer "
                         "service VM '%s'", mirror_pkt_count, svm_name)

        return True

    def verify_udp_mirror_on_all_analyzer(self, sessions, left_vm_fix, right_vm_fix, expectation=True):
        return self.verify_l4_mirror_on_all_analyzer(sessions, left_vm_fix, right_vm_fix, proto='udp', expectation=True)

    def verify_tcp_mirror_on_all_analyzer(self, sessions, left_vm_fix, right_vm_fix, expectation=True):
        return self.verify_l4_mirror_on_all_analyzer(sessions, left_vm_fix, right_vm_fix, proto='tcp', expectation=True)

    def verify_l4_mirror_on_all_analyzer(self, sessions, left_vm_fix, right_vm_fix, proto, expectation=True):
        # Install traffic package in VM
        left_vm_fix.install_pkg("Traffic")
        right_vm_fix.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(left_vm_fix, right_vm_fix,
                                         proto, sport=sport, dport=dport)
        errmsg = "'%s' traffic with src port %s and dst port %s failed" % (
            proto, sport, dport)
        count = sent
        if not expectation:
            count = 0
            errmsg = "'%s' traffic with src port %s and dst port %s passed; Expected to fail" % (
                proto, sport, dport)
        if left_vm_fix.vm_node_ip != right_vm_fix.vm_node_ip:
            count = count * 2
        assert sent and recv == sent, errmsg
        for svm_name, (session, pcap) in sessions.items():
            assert self.verify_l4_mirror(svm_name, session, pcap, exp_count, proto)

        return True

    def verify_l4_mirror(self, svm_name, session, pcap, exp_count, proto):
        mirror_pkt_count = self.stop_tcpdump(session, pcap)
        errmsg = "%s '%s' Packets mirrored to the analyzer VM, "\
                 "Expected %s packets" % (mirror_pkt_count, proto, exp_count)
        assert mirror_pkt_count == exp_count, errmsg
        self.logger.info("%s '%s' packets are mirrored to the analyzer "
                         "service VM '%s'", mirror_pkt_count, proto, svm_name)
        return True

    @retry(delay=2, tries=6)
    def verify_mirroring(self, si_fix, src_vm, dst_vm, mirr_vm=None):
        result = True
        if mirr_vm:
            svm = mirr_vm.vm_obj
        else:
            svms = self.get_svms_in_si(si_fix)
            svm = svms[0]
        if svm.status == 'ACTIVE':
            svm_name = svm.name
            host = self.get_svm_compute(svm_name)
            if mirr_vm:
                tapintf = self.get_svm_tapintf(svm_name)
            else:
               tapintf = self.get_bridge_svm_tapintf(svm_name, 'left')
            session = ssh(host['host_ip'], host['username'], host['password'])
            cmd = 'sudo tcpdump -nni %s -c 5 > /tmp/%s_out.log' % (tapintf, tapintf)
            execute_cmd(session, cmd, self.logger)
            assert src_vm.ping_with_certainty(dst_vm.vm_ip)
            sleep(10)
            output_cmd = 'sudo cat /tmp/%s_out.log' % tapintf
            out, err = execute_cmd_out(session, output_cmd, self.logger)
            print out
            if '8099' in out:
                self.logger.info('Mirroring action verified')
            else:
                result = False
                self.logger.warning('No mirroring action seen')
        return result

    @retry(delay=2, tries=6)
    def verify_port_mirroring(self, src_vm, dst_vm, mirr_vm, vlan=None, parent=False):
        result = True
        svm = mirr_vm.vm_obj
        if svm.status == 'ACTIVE':
            svm_name = svm.name
            host = self.get_svm_compute(svm_name)
            tapintf = self.get_svm_tapintf(svm_name)
        # Intf mirroring enabled on either sub intf or parent port
        exp_count = 10
        if parent:
            # Intf mirroring enabled on both sub intf and parent port
            exp_count = 20
        if self.inputs.pcap_on_vm:
            vm_fix_pcap_pid_files = start_tcpdump_for_vm_intf(
                None, [mirr_vm], None, filters='udp port 8099', pcap_on_vm=True)
        else:
            session = ssh(host['host_ip'], host['username'], host['password'])
            pcap = self.start_tcpdump(session, tapintf, vlan=vlan)
        src_ip = src_vm.vm_ip
        dst_ip = dst_vm.vm_ip
        if vlan:
            sub_intf = 'eth0.' + str(vlan)
            cmds = "/sbin/ifconfig " + sub_intf + " | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'"
            src_ip = src_vm.run_cmd_on_vm(cmds=[cmds]).values()[0]
            dst_ip = dst_vm.run_cmd_on_vm(cmds=[cmds]).values()[0]
        assert src_vm.ping_with_certainty(dst_ip, count=5, size='1200')
        #lets wait 10 sec for tcpdump to capture all the packets
        sleep(10)
        self.logger.info('Ping from %s to %s executed with c=5, expected mirrored packets 5 Ingress,5 Egress count = 10'
            % (src_ip, dst_ip))
        filters = '| grep \"length [1-9][2-9][0-9][0-9][0-9]*\"'
        if self.inputs.pcap_on_vm:
            output, mirror_pkt_count = stop_tcpdump_for_vm_intf(
                None, None, None, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files, filters=filters, verify_on_all=True)
            mirror_pkt_count = int(mirror_pkt_count[0])
        else:
            mirror_pkt_count = self.stop_tcpdump(session, pcap, filters)
        errmsg = "%s ICMP Packets mirrored to the analyzer VM %s,"\
                 "Expected %s packets" % (
                     mirror_pkt_count, svm_name, exp_count)
        if mirror_pkt_count < exp_count:
            self.logger.error(errmsg)
            assert False, errmsg

        self.logger.info("%s ICMP packets are mirrored to the analyzer "
                         "service VM '%s'", mirror_pkt_count, svm_name)
        return result
    # end verify_port_mirroring

    def verify_policy_delete_add(self, svc_chain_info):
        left_vn_policy_fix = svc_chain_info['left_vn_policy_fix']
        right_vn_policy_fix = svc_chain_info['right_vn_policy_fix']
        left_vn_fixture = svc_chain_info['left_vn_fixture']
        right_vn_fixture = svc_chain_info['right_vn_fixture']
        policy_fixture = svc_chain_info['policy_fixture']
        left_vm_fixture = svc_chain_info['left_vm_fixture']
        right_vm_fixture = svc_chain_info['right_vm_fixture']
        si_fixture = svc_chain_info['si_fixture']
        # Delete policy
        self.detach_policy(left_vn_policy_fix)
        self.detach_policy(right_vn_policy_fix)
        self.unconfig_policy(policy_fixture)
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % right_vm_fixture.vm_ip
        assert not left_vm_fixture.ping_to_ip(
            right_vm_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        # Create policy again
        policy_fixture = self.config_policy(policy_fixture.policy_name,
                                            policy_fixture.input_rules_list)
        self.attach_policy_to_vn(policy_fixture, left_vn_fixture)
        self.attach_policy_to_vn(policy_fixture, right_vn_fixture)
        assert self.verify_si(si_fixture)

        # Verify ICMP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_to_ip(
            right_vm_fixture.vm_ip), errmsg
        #TODO
        # Check this with Ankit 
        for svm_name, (session, pcap) in sessions.items():
            count = 10
            if left_vm_fixture.vm_node_ip != right_vm_fixture.vm_node_ip:
                count = count * 2
            assert self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_add_new_vns(self, svc_chain_info):
        left_vn_policy_fix = svc_chain_info['left_vn_policy_fix']
        right_vn_policy_fix = svc_chain_info['right_vn_policy_fix']
        policy_fixture = svc_chain_info['policy_fixture']
        left_vm_fixture = svc_chain_info['left_vm_fixture']
        right_vm_fixture = svc_chain_info['right_vm_fixture']
        si_fixture = svc_chain_info['si_fixture']

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
        new_left_vm_fix = self.config_vm(vn_fix=new_left_vn_fix, vm_name=new_left_vm)
        new_right_vm_fix = self.config_vm(vn_fix=new_right_vn_fix, vm_name=new_right_vm)
        assert new_left_vm_fix.verify_on_setup()
        assert new_right_vm_fix.verify_on_setup()
        # Wait for VM's to come up
        assert new_left_vm_fix.wait_till_vm_is_up()
        assert new_right_vm_fix.wait_till_vm_is_up()

        # Add rule to policy to allow traffic from new left_vn to right_vn
        # through SI
        mirror_fq_name = si_fixture.fq_name_str
        rules = [{'direction': '<>',
                               'protocol': 'icmp',
                               'source_network': new_left_vn,
                               'src_ports': [0, 65535],
                               'dest_network': new_right_vn,
                               'dst_ports': [0, 65535],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': mirror_fq_name}}
                               },
                               {'direction': '<>',
                               'protocol': 'icmp6',
                               'source_network': new_left_vn,
                               'src_ports': [0, 65535],
                               'dest_network': new_right_vn,
                               'dst_ports': [0, 65535],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': mirror_fq_name}}
                               }]
        policy_fixture.input_rules_list.extend(rules)
        policy_fixture.update_policy_api(policy_fixture.input_rules_list)

        # Create new policy with rule to allow traffic from new VN's
        self.attach_policy_to_vn(policy_fixture, new_left_vn_fix)
        self.attach_policy_to_vn(policy_fixture, new_right_vn_fix)
        assert self.verify_si(si_fixture)

        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                        right_vm_fixture, 'icmp')
        self._verify_proto_based_mirror(si_fixture, new_left_vm_fix,
                                        new_right_vm_fix, 'icmp')
        return True

    def verify_svc_mirroring_unidirection(self):
        """Validate the service chaining datapath with unidirection traffic
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Create the policy rule for ICMP/UDP with 'unidirection rule' and attach to vn's
           4. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           Pinf from vm1 to vm2 should fail. Only the pkts from vm1 should get mirrored.
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
        ret_dict = self.config_svc_mirroring()
        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']

        si_fq_name = si_fixture.fq_name_str
        rules = [{'direction': '>',
                       'protocol': 'icmp',
                       'source_network': left_vn_fixture.vn_name,
                       'src_ports': [0, 65535],
                       'dest_network': right_vn_fixture.vn_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name}}
                       },
                       {'direction': '>',
                       'protocol': 'icmp6',
                       'source_network': left_vn_fixture.vn_name,
                       'src_ports': [0, 65535],
                       'dest_network': right_vn_fixture.vn_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name}}
                       },
                       {'direction': '<>',
                       'protocol': 'any',
                       'source_network': 'any',
                       'src_ports': [0, 65535],
                       'dest_network': 'any',
                       'dst_ports': [0, 65535],
                       'simple_action': 'deny',
                       'action_list': {'simple_action': 'deny'}
                       }
                      ]
        policy_fixture.update_policy_api(rules)

        # Verify ICMP traffic mirror
        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                        right_vm_fixture, 'icmp', replies=False)
        return True

    def verify_attach_detach_policy_with_svc_mirroring(self):
        """Validate the detach and attach policy with SI doesn't block traffic"""

        ret_dict = self.verify_svc_mirroring(service_mode='in-network')
        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']

        # Verify ICMP traffic mirror
        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                        right_vm_fixture, 'icmp')

        # detach the policy and attach again to both the network
        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])

        vn1_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)

        # Verify ICMP traffic mirror
        self._verify_proto_based_mirror(si_fixture, left_vm_fixture,
                                        right_vm_fixture, 'icmp')
        return True

    def verify_detach_attach_diff_policy_with_mirroring(self):
        """validate attaching a policy with analyzer and detaching again removes all the routes and does not impact other policies"""
        ret_dict = self.config_svc_mirroring()
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']

        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])
        self.unconfig_policy(policy_fixture)

        policy_name1 = get_random_name('pol1')
        policy_name2 = get_random_name('pol-analyzer')
        si_fq_name = si_fixture.fq_name_str
        rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': left_vn_fixture.vn_fq_name,
                        'src_ports': [0, 65535],
                        'dest_network': right_vn_fixture.vn_fq_name,
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': left_vn_fixture.vn_fq_name,
                        'src_ports': [0, 65535],
                        'dest_network': right_vn_fixture.vn_fq_name,
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': si_fq_name}}
                        }
                       ]

        pol1_fixture = self.config_policy(policy_name1, rules1)
        pol_analyzer_fixture = self.config_policy(policy_name2, rules2)

        vn1_policy_fix = self.attach_policy_to_vn(pol1_fixture, left_vn_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, right_vn_fixture)

        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip), errmsg

        self.detach_policy(vn1_policy_fix)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step2"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(vn2_policy_fix)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, right_vn_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step3"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(vn2_policy_fix)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, right_vn_fixture)
        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 passed in step4"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(vn2_policy_fix)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step5"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg

        vn2_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, right_vn_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step6"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg
    # end  verify_detach_attach_diff_policy_with_mirroring

    def verify_detach_attach_policy_change_rules(self):
        ret_dict = self.config_svc_mirroring(service_mode='in-network')
        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']

        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])
        self.unconfig_policy(policy_fixture)

        policy_name1 = get_random_name('pol1')
        policy_name2 = get_random_name('pol-analyzer')
        si_fq_name = si_fixture.fq_name_str

        rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': left_vn_fixture.vn_fq_name,
                        'src_ports': [0, 65535],
                        'dest_network': right_vn_fixture.vn_fq_name,
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': left_vn_fixture.vn_fq_name,
                        'src_ports': [0, 65535],
                        'dest_network': right_vn_fixture.vn_fq_name,
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': si_fq_name}}
                        }
                       ]

        pol1_fixture = self.config_policy(policy_name1, rules1)
        pol_analyzer_fixture = self.config_policy(
            policy_name2, rules2)
        vn1_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, left_vn_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, right_vn_fixture)

        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg

        self.detach_policy(vn1_policy_fix)
        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step2"
        assert right_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip), errmsg

        # change policy rules to rules1 and Verify no ICMP traffic b/w VN1 and
        # VN2
        data = {
            'policy': {'entries': pol1_fixture.policy_obj['policy']['entries']}}
        pol_analyzer_fixture.update_policy(
            pol_analyzer_fixture.policy_obj['policy']['id'], data)
        errmsg = "Ping b/w VN1 and VN2 success in step3"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(vn2_policy_fix)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, right_vn_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step5"
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip, expectation=False), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip, expectation=False), errmsg
    # end verify_detach_attach_policy_change_rules


    def verify_policy_order_change(self):
        ret_dict = self.config_svc_mirroring(service_mode='in-network')
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']

        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])
        self.unconfig_policy(policy_fixture)
        si_fq_name = si_fixture.fq_name_str

        policy_name1 = get_random_name('pol1')
        policy_name2 = get_random_name('pol-analyzer')

        rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': 'any',
                        'src_ports': [0, 65535],
                        'dest_network': 'any',
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': left_vn_fixture.vn_fq_name,
                        'src_ports': [0, 65535],
                        'dest_network': right_vn_fixture.vn_fq_name,
                        'dst_ports': [0, 65535],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': si_fq_name}}
                        }
                       ]

        pol1_fixture = self.config_policy(policy_name1, rules1)
        pol_analyzer_fixture = self.config_policy(
            policy_name2, rules2)
        vn1_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, left_vn_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, right_vn_fixture)

        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        assert left_vm_fixture.ping_to_ip(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_to_ip(
            left_vm_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = 20
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(vn1_policy_fix)
        self.detach_policy(vn2_policy_fix)
        vn1_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, left_vn_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, right_vn_fixture)
        vn1_policy_a_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, left_vn_fixture)
        vn2_policy_a_fix = self.attach_policy_to_vn(
            pol_analyzer_fixture, right_vn_fixture)
        vn1_seq_num = {}
        vn2_seq_num = {}
        vn1_seq_num[policy_name1] = self.get_seq_num(
            left_vn_fixture, policy_name1)
        vn1_seq_num[policy_name2] = self.get_seq_num(
            left_vn_fixture, policy_name2)
        vn2_seq_num[policy_name1] = self.get_seq_num(
            right_vn_fixture, policy_name1)
        vn2_seq_num[policy_name2] = self.get_seq_num(
            right_vn_fixture, policy_name2)

        # Verify ICMP traffic b/w VN1 and VN2 but no mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step2"
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        assert left_vm_fixture.ping_to_ip(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_to_ip(
            left_vm_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            if vn1_seq_num[policy_name2] < vn1_seq_num[policy_name1] or vn2_seq_num[policy_name2] < vn2_seq_num[policy_name1]:
                self.logger.info(
                    '%s is assigned first. Mirroring expected' % policy_name2)
                count = 20
            else:
                self.logger.info(
                    '%s is assigned first. No mirroring expected' % policy_name1)
                count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(vn1_policy_fix)
        vn1_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, left_vn_fixture)
        self.detach_policy(vn2_policy_fix)
        vn2_policy_fix = self.attach_policy_to_vn(
            pol1_fixture, right_vn_fixture)

        vn1_seq_num[policy_name1] = self.get_seq_num(
            left_vn_fixture, policy_name1)
        vn1_seq_num[policy_name2] = self.get_seq_num(
            left_vn_fixture, policy_name2)
        vn2_seq_num[policy_name1] = self.get_seq_num(
            right_vn_fixture, policy_name1)
        vn2_seq_num[policy_name2] = self.get_seq_num(
            right_vn_fixture, policy_name2)

        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step3 and step4"
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_with_certainty(
            left_vm_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            if vn1_seq_num[policy_name2] < vn1_seq_num[policy_name1] or vn2_seq_num[policy_name2] < vn2_seq_num[policy_name1]:
                self.logger.info(
                    '%s is assigned first. Mirroring expected' % policy_name2)
                count = 20
            else:
                self.logger.info(
                    '%s is assigned first. No mirroring expected' % policy_name1)
                count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(vn1_policy_fix)
        self.detach_policy(vn2_policy_fix)

        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step5"
        sessions = self.tcpdump_on_all_analyzer(si_fixture)
        assert left_vm_fixture.ping_to_ip(
            right_vm_fixture.vm_ip), errmsg
        assert right_vm_fixture.ping_to_ip(
            left_vm_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = 20
            assert self.verify_icmp_mirror(svm_name, session, pcap, count)
    # end verify_policy_order_change

    def get_seq_num(self, vn_fix, pol_name):
        vn_obj = self.vnc_lib.virtual_network_read(
            id=vn_fix.vn_id)
        for net_pol_ref in vn_obj.get_network_policy_refs():
            if net_pol_ref['to'][-1] == pol_name:
                vn_seq_num = net_pol_ref['attr'].sequence.major
        return vn_seq_num

    def cleanUp(self):
        super(VerifySvcMirror, self).cleanUp()

    def start_tcpdump(self, session, tap_intf, vlan=None,  vm_fixtures=[], pcap_on_vm=False):
        if not pcap_on_vm:
            pcap = '/tmp/mirror-%s_%s.pcap' % (tap_intf, get_random_name())
            cmd = 'rm -f %s' % pcap
            execute_cmd(session, cmd, self.logger)
            assert check_pcap_file_exists(session, pcap, expect=False),'pcap file still exists'
            filt_str = 'udp port 8099'
            if vlan:
                filt_str = 'greater 1200'
            cmd = "sudo tcpdump -ni %s -U %s -w %s" % (tap_intf, filt_str, pcap)
            self.logger.info("Starting tcpdump to capture the mirrored packets.")
            execute_cmd(session, cmd, self.logger)
            assert check_pcap_file_exists(session, pcap),'pcap file does not exist'
            return pcap
        else:
            pcap = '/tmp/%s.pcap' % (get_random_name())
            cmd_to_tcpdump = [ 'tcpdump -ni %s udp port 8099 -w %s 1>/dev/null 2>/dev/null' % (tap_intf, pcap) ]
            pidfile = pcap + '.pid'
            vm_fix_pcap_pid_files =[]
            for vm_fixture in vm_fixtures:
                vm_fixture.run_cmd_on_vm(cmds=cmd_to_tcpdump, as_daemon=True, pidfile=pidfile, as_sudo=True)
                vm_fix_pcap_pid_files.append((vm_fixture, pcap, pidfile))
            return vm_fix_pcap_pid_files

    def stop_tcpdump(self, session, pcap, filt='', vm_fix_pcap_pid_files=[], pcap_on_vm=False):
        self.logger.debug("Waiting for the tcpdump write to complete.")
        sleep(2)
        if not pcap_on_vm:
            cmd = 'sudo kill $(ps -ef|grep tcpdump | grep %s| awk \'{print $2}\')' %pcap
            execute_cmd(session, cmd, self.logger)
            execute_cmd(session, 'sync', self.logger)
            sleep(3)
            cmd = 'sudo tcpdump -n -r %s %s | wc -l' % (pcap, filt)
            out, err = execute_cmd_out(session, cmd, self.logger)
            count = int(out.strip('\n'))
            cmd = 'sudo tcpdump -n -r %s' % pcap
            #TODO
            # Temporary for debugging
            execute_cmd(session, cmd, self.logger)
            return count
        else:
            output = []
            pkt_count = []
            for vm_fix, pcap, pidfile in vm_fix_pcap_pid_files:
                cmd_to_output  = 'tcpdump -nr %s %s' % (pcap, filt)
                cmd_to_kill = 'cat %s | xargs kill ' % (pidfile)
                count = cmd_to_output + '| wc -l'
                vm_fix.run_cmd_on_vm(cmds=[cmd_to_kill], as_sudo=True)
                sleep(2)
                vm_fix.run_cmd_on_vm(cmds=[cmd_to_output], as_sudo=True)
                output.append(vm_fix.return_output_cmd_dict[cmd_to_output])
                vm_fix.run_cmd_on_vm(cmds=[count], as_sudo=True)
                pkt_count_list = vm_fix.return_output_cmd_dict[count].split('\n')
                try:
                    pkts = pkt_count_list[2]
                except:
                    pkts = pkt_count_list[1]
                pkts = int(pkts)
                pkt_count.append(pkts)
                total_pkts = sum(pkt_count)
            return output, total_pkts

    def pcap_on_all_vms_and_verify_mirrored_traffic(
        self, src_vm_fix, dst_vm_fix, svm_fixtures, count, filt='', tap='eth0', expectation=True):
            vm_fix_pcap_pid_files = self.start_tcpdump(None, tap_intf=tap, vm_fixtures= svm_fixtures, pcap_on_vm=True)
            assert src_vm_fix.ping_with_certainty(
                dst_vm_fix.vm_ip, expectation=expectation)
            output, total_pkts = self.stop_tcpdump(
                None, pcap=tap, filt=filt, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files, pcap_on_vm=True)
            if count > total_pkts:
                errmsg = "%s ICMP Packets mirrored to the analyzer VM,"\
                    "Expected %s packets, tcpdump on VM" % (
                     total_pkts, count)
                self.logger.error(errmsg)
                assert False, errmsg
            else:
                self.logger.info("Mirroring verified using tcpdump on the VM, Expected = Mirrored = %s " % (total_pkts))
            return True
    # end pcap_on_all_vms_and_verify_mirrored_traffic
