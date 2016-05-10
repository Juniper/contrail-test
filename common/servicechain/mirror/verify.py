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
from common.openstack_libs import network_exception as exceptions


class VerifySvcMirror(ConfigSvcMirror, VerifySvcChain, ECMPVerify):

    def verify_svc_mirroring(self, si_count=1, svc_mode='transparent', ci=False):
        """Validate the service chaining datapath
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Create the policy rule for ICMP/UDP and attach to vn's
           4. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn1_subnets = vn1_subnets
        self.vm1_name = get_random_name("in_network_vm1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn2_subnets = vn2_subnets
        self.vm2_name = get_random_name("in_network_vm2")

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name("st1")
        self.si_prefix = get_random_name("mirror_si") + "_"
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)
        if ci:
            svc_img_name = 'cirros-0.3.0-x86_64-uec'
            image_name = 'cirros-0.3.0-x86_64-uec'
        else:
            svc_img_name = "vsrx"
            image_name = 'ubuntu-traffic'
        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_fq_name, svc_type='analyzer', svc_mode=svc_mode, project=self.inputs.project_name, svc_img_name=svc_img_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)

        self.rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       }]
        if len(self.action_list) == 2:
            self.rules.append({'direction': '<>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [0, -1],
                               'dest_network': self.vn2_name,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': self.action_list[1]}}
                               }
                              )
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name=image_name)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2, image_name=image_name)
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)
        # Verify ICMP traffic mirror
        if ci:
            return self.verify_mirroring(self.si_fixtures, self.vm1_fixture, self.vm2_fixture)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 10
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        # One mirror instance
        if len(self.action_list) != 2:
            return True

        # Verify UDP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        # Install traffic package in VM
        self.vm1_fixture.install_pkg("Traffic")
        self.vm2_fixture.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(self.vm1_fixture, self.vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = sent
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[1], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = sent
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')

        return True

    def verify_svc_mirroring_with_floating_ip(self, si_count=1):
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

        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn1_subnets = vn1_subnets
        self.vm1_name = get_random_name("in_network_vm1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn2_subnets = vn2_subnets
        self.vm2_name = get_random_name("in_network_vm2")

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name("st1")
        self.si_prefix = get_random_name("mirror_si") + "_"
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        fip_pool_name = get_random_name('testpool')

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, svc_type='analyzer', left_vn=self.vn1_name, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)
        self.rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn1_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn1_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       }
                      ]
        if len(self.action_list) == 2:
            self.rules.append({'direction': '<>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [8001, 8001],
                               'dest_network': self.vn1_name,
                               'dst_ports': [9001, 9001],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': self.action_list[1]}}
                               }
                              )
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2)
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)

        self.fip_fixture = self.config_fip(
            self.vn1_fixture.vn_id, pool_name=fip_pool_name)
        self.fip_ca = self.useFixture(CreateAssociateFip(self.inputs, self.fip_fixture,
                                                         self.vn1_fixture.vn_id,
                                                         self.vm2_fixture.vm_id))
        fip = self.vm2_fixture.vnc_lib_h.floating_ip_read(id=self.fip_ca.fip_id).\
            get_floating_ip_address()

        # Verify ICMP traffic mirror
        # sessions = self.tcpdump_on_all_analyzer(self.si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(fip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 10
                if self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        # One mirror instance
        if len(self.action_list) != 2:
            return True

        # Verify UDP traffic mirror
        # sessions = self.tcpdump_on_all_analyzer(self.si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        # Install traffic package in VM
        self.vm1_fixture.install_pkg("Traffic")
        self.vm2_fixture.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(self.vm1_fixture, self.vm2_fixture,
                                         'udp', sport=sport, dport=dport, fip=fip)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = sent
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[1], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = sent
                if self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')

        return True

    def verify_svc_mirror_with_deny(self, si_count=1):
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
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn1_subnets = vn1_subnets
        self.vm1_name = get_random_name("in_network_vm1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn2_subnets = vn2_subnets
        self.vm2_name = get_random_name("in_network_vm2")

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name("st1")
        self.si_prefix = get_random_name("mirror_si") + "_"
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        self.dynamic_policy_name = get_random_name("mirror_policy")
        self.rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'deny',
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'deny',
                       }]
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2)
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, svc_type='analyzer', left_vn=self.vn1_name, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)

        dynamic_rules = [{'direction': '<>',
                          'protocol': 'icmp',
                          'source_network': self.vn1_name,
                          'src_ports': [0, -1],
                          'dest_network': self.vn2_name,
                          'dst_ports': [0, -1],
                          'simple_action': 'pass',
                          'action_list': {'simple_action': 'pass',
                                          'mirror_to': {'analyzer_name': self.action_list[0]}}
                          },
                          {'direction': '<>',
                          'protocol': 'icmp6',
                          'source_network': self.vn1_name,
                          'src_ports': [0, -1],
                          'dest_network': self.vn2_name,
                          'dst_ports': [0, -1],
                          'simple_action': 'pass',
                          'action_list': {'simple_action': 'pass',
                                          'mirror_to': {'analyzer_name': self.action_list[0]}}
                          }]
        dynamic_policy_fixture = self.config_policy(
            self.dynamic_policy_name, dynamic_rules)
        vn1_dynamic_policy_fix = self.attach_policy_to_vn(
            dynamic_policy_fixture, self.vn1_fixture, policy_type='dynamic')
        vn2_dynamic_policy_fix = self.attach_policy_to_vn(
            dynamic_policy_fixture, self.vn2_fixture, policy_type='dynamic')
        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 5
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_icmp_mirror_on_all_analyzer(self, sessions, left_vm_fix, right_vm_fix, expectation=True):
        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fix.vm_ip
        if not expectation:
            errmsg = "Ping to right VM ip %s from left VM passed, Expected to fail" % right_vm_fix.vm_ip
        assert left_vm_fix.ping_with_certainty(
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
            self.verify_l4_mirror(svm_name, session, pcap, exp_count, proto)

        return True

    @retry(delay=2, tries=6)
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
            svms = self.get_svms_in_si(si_fix[0], self.inputs.project_name)
            svm = svms[0]
        if svm.status == 'ACTIVE':
            svm_name = svm.name
            host = self.get_svm_compute(svm_name)
            if mirr_vm:
                tapintf = self.get_svm_tapintf(svm_name)
            else:
               tapintf = self.get_bridge_svm_tapintf(svm_name, 'left')
            session = ssh(host['host_ip'], host['username'], host['password'])
            cmd = 'tcpdump -nni %s -c 5 > /tmp/%s_out.log' % (tapintf, tapintf)
            execute_cmd(session, cmd, self.logger)
            assert src_vm.ping_with_certainty(dst_vm.vm_ip)
            sleep(10)
            output_cmd = 'cat /tmp/%s_out.log' % tapintf
            out, err = execute_cmd_out(session, output_cmd, self.logger)
            print out
            if '8099' in out:
                self.logger.info('Mirroring action verified')
            else:
                result = False
                self.logger.warning('No mirroring action seen')
        return result

    def verify_policy_delete_add(self, si_prefix, si_count=1):
        # Delete policy
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        # sessions = self.tcpdump_on_all_analyzer(si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        for svm_name, (session, pcap) in sessions.items():
            count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        # Create policy again
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)
        self.attach_policy_to_vn(self.policy_fixture, self.vn1_fixture)
        self.attach_policy_to_vn(self.policy_fixture, self.vn2_fixture)
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic mirror
        # sessions = self.tcpdump_on_all_analyzer(si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        svmname = si_prefix + str('2_1')
        for svm_name, (session, pcap) in sessions.items():
            count = 10
            if svm_name == svmname:
                count = 0
            if self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                count = count * 2
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_add_new_vns(self, si_prefix, si_count=1):
        # Delete policy
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)

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
        new_left_vm_fix = self.config_vm(new_left_vn_fix, new_left_vm)
        new_right_vm_fix = self.config_vm(new_right_vn_fix, new_right_vm)
        assert new_left_vm_fix.verify_on_setup()
        assert new_right_vm_fix.verify_on_setup()
        # Wait for VM's to come up
        self.nova_h.wait_till_vm_is_up(new_left_vm_fix.vm_obj)
        self.nova_h.wait_till_vm_is_up(new_right_vm_fix.vm_obj)

        # Add rule to policy to allow traffic from new left_vn to right_vn
        # through SI
        new_rule = {'direction': '<>',
                    'protocol': 'udp',
                    'source_network': new_left_vn,
                    'src_ports': [0, -1],
                    'dest_network': new_right_vn,
                    'dst_ports': [0, -1],
                    'simple_action': 'pass',
                    'action_list': {'simple_action': 'pass',
                                    'mirror_to': {'analyzer_name': self.action_list[0]}}
                    }
        self.rules.append(new_rule)
        if len(self.action_list) == 2:
            self.rules.append({'direction': '<>',
                               'protocol': 'icmp',
                               'source_network': new_left_vn,
                               'src_ports': [0, -1],
                               'dest_network': new_right_vn,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': self.action_list[1]}}
                               },
                               {'direction': '<>',
                               'protocol': 'icmp6',
                               'source_network': new_left_vn,
                               'src_ports': [0, -1],
                               'dest_network': new_right_vn,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': self.action_list[1]}}
                               }
                              )

        # Create new policy with rule to allow traffic from new VN's
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)
        self.attach_policy_to_vn(self.policy_fixture, self.vn1_fixture)
        self.attach_policy_to_vn(self.policy_fixture, self.vn2_fixture)
        self.attach_policy_to_vn(self.policy_fixture, new_left_vn_fix)
        self.attach_policy_to_vn(self.policy_fixture, new_right_vn_fix)
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic mirror between existing VN's
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        svmname = self.get_svms_in_si(
                     self.si_fixtures[0], self.inputs.project_name)[0].name
        for svm_name, (session, pcap) in sessions.items():
            count = 10
            if svm_name == svmname:
                count = 0
            if self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                count = count * 2
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        # Verify UDP traffic mirror between New VN's
        # sessions = self.tcpdump_on_all_analyzer(self.si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        # Install traffic package in VM
        new_left_vm_fix.install_pkg("Traffic")
        new_right_vm_fix.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(new_left_vm_fix, new_right_vm_fix,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
        svmname = self.get_svms_in_si(
                     self.si_fixtures[0], self.inputs.project_name)[0].name
        for svm_name, (session, pcap) in sessions.items():
            count = sent
            if svm_name == svmname:
                count = 0
            if new_left_vm_fix.vm_node_ip != new_right_vm_fix.vm_node_ip:
                count = count * 2
            self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')

        # One mirror instance
        if len(self.action_list) != 2:
            return True

        # Verify UDP traffic mirror traffic between existing VN's
        # sessions = self.tcpdump_on_all_analyzer(self.si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        # Install traffic package in VM
        self.vm1_fixture.install_pkg("Traffic")
        self.vm2_fixture.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(self.vm1_fixture, self.vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
        svmname = self.get_svms_in_si(
                     self.si_fixtures[0], self.inputs.project_name)[0].name
        for svm_name, (session, pcap) in sessions.items():
            count = sent
            if svm_name == svmname:
                count = 0
            if self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                count = count * 2
            self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')

        # Verify ICMP traffic mirror between new VN's
        # sessions = self.tcpdump_on_all_analyzer(si_prefix, si_count)
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            new_right_vm_fix.vm_ip), errmsg
        svmname = self.get_svms_in_si(
                     self.si_fixtures[0], self.inputs.project_name)[0].name
        for svm_name, (session, pcap) in sessions.items():
            count = 10
            if svm_name == svmname:
                count = 0
            if left_vm_fix.vm_node_ip != right_vm_fix.vm_node_ip:
                count = count * 2
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_svc_mirroring_unidirection(self, si_count=1, svc_mode='transparent'):
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
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn1_subnets = vn1_subnets
        self.vm1_name = get_random_name("in_network_vm1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn2_subnets = vn2_subnets
        self.vm2_name = get_random_name("in_network_vm2")

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name("st1")
        self.si_prefix = get_random_name("mirror_si") + "_"
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_name, svc_type='analyzer', svc_mode=svc_mode, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)

        self.rules = [{'direction': '>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       },
                       {'direction': '>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       }
                      ]
        if len(self.action_list) == 2:
            self.rules.append({'direction': '>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [0, -1],
                               'dest_network': self.vn2_name,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass',
                                               'mirror_to': {'analyzer_name': self.action_list[1]}}
                               }
                              )
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2)
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM passed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 5
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        # One mirror instance
        if len(self.action_list) != 2:
            return True

        # Verify UDP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        # Install traffic package in VM
        self.vm1_fixture.install_pkg("Traffic")
        self.vm2_fixture.install_pkg("Traffic")

        sport = 8001
        dport = 9001
        sent, recv = self.verify_traffic(self.vm1_fixture, self.vm2_fixture,
                                         'udp', sport=sport, dport=dport)
        errmsg = "UDP traffic with src port %s and dst port %s failed" % (
            sport, dport)
        assert sent and recv == sent, errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = sent
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[1], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = sent
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_l4_mirror(svm_name, session, pcap, count, 'udp')

        return True

    def verify_attach_detach_policy_with_svc_mirroring(self, si_count=1):
        """Validate the detach and attach policy with SI doesn't block traffic"""

        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn1_subnets = vn1_subnets
        self.vm1_name = get_random_name("in_network_vm1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn2_subnets = vn2_subnets
        self.vm2_name = get_random_name("in_network_vm2")

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name("st1")
        self.si_prefix = get_random_name("mirror_si") + "_"
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)
        svc_mode = 'in-network'

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_fq_name, svc_type='analyzer', svc_mode=svc_mode, project=self.inputs.project_name)
                                                              #svc_img_name=svc_img)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)
        self.rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': self.action_list[0]}}
                       }
                      ]

        self.policy_fixture = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2)
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 10
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        # detach the policy and attach again to both the network
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)

        # Verify ICMP traffic mirror
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            svm = {}
            svm = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svm_name == svm[0].name:
                count = 10
                if svc_mode == 'transparent' and self.vm1_fixture.vm_node_ip != self.vm2_fixture.vm_node_ip:
                    count = count * 2
                self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def verify_detach_attach_diff_policy_with_mirroring(self, si_count=1):
        """validate attaching a policy with analyzer and detaching again removes all the routes and does not impact other policies"""
        random_number = randint(700, 800)
        self.domain_name = "default-domain"
        self.project_name = self.inputs.project_name

        self.vn1_name = get_random_name("VN1%s" % si_count)
        self.vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vm1_name = get_random_name('VM-traffic')
        self.vn2_name = get_random_name("VN2%s" % si_count)
        self.vm2_name = get_random_name('VM-ubuntu')
        self.vn1_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn1_name])
        self.vn2_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn2_name])

        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name('st-analyzer-left')
        self.si_prefix = 'mirror_si_' + str(random_number)
        self.policy_name1 = get_random_name('pol1')
        self.policy_name2 = get_random_name('pol-analyzer')
        self.svc_mode = 'transparent'
        self.svc_type = 'analyzer'

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_fq_name, svc_type=self.svc_type, svc_mode=self.svc_mode, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)
        self.rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': self.vn1_name,
                        'src_ports': [0, -1],
                        'dest_network': self.vn2_name,
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        self.rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': self.vn1_name,
                        'src_ports': [0, -1],
                        'dest_network': self.vn2_name,
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': self.action_list[0]}}
                        }
                       ]

        self.pol1_fixture = self.config_policy(self.policy_name1, self.rules1)
        self.pol_analyzer_fixture = self.config_policy(
            self.policy_name2, self.rules2)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn2_fixture)

        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, image_name='ubuntu-traffic')
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, image_name='ubuntu')
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)
        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg

        self.detach_policy(self.vn1_policy_fix)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step2"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(self.vn2_policy_fix)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn2_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step3"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(self.vn2_policy_fix)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn2_fixture)
        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step4"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(self.vn2_policy_fix)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step5"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn2_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step6"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        return True

    def verify_detach_attach_policy_change_rules(self, si_count=1):
        random_number = randint(800, 900)
        self.domain_name = "default-domain"
        self.project_name = self.inputs.project_name

        self.vn1_name = get_random_name("VN1%s" % si_count)
        self.vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vm1_name = get_random_name('VM-traffic')
        self.vn2_name = get_random_name("VN2%s" % si_count)
        self.vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vm2_name = get_random_name('VM-ubuntu')

        self.vn1_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn1_name])
        self.vn2_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn2_name])
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name('st-analyzer-left')
        self.si_prefix = 'mirror_si_' + str(random_number)
        self.policy_name1 = get_random_name('pol1')
        self.policy_name2 = get_random_name('pol-analyzer')
        self.svc_mode = 'in-network'
        self.svc_type = 'analyzer'

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_fq_name, svc_type=self.svc_type, svc_mode=self.svc_mode, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)
        self.rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': self.vn1_name,
                        'src_ports': [0, -1],
                        'dest_network': self.vn2_name,
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        self.rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': self.vn1_name,
                        'src_ports': [0, -1],
                        'dest_network': self.vn2_name,
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': self.action_list[0]}}
                        }
                       ]

        self.pol1_fixture = self.config_policy(self.policy_name1, self.rules1)
        self.pol_analyzer_fixture = self.config_policy(
            self.policy_name2, self.rules2)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn2_fixture)

        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, image_name='ubuntu-traffic')
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, image_name='ubuntu')
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)

        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg

        self.detach_policy(self.vn1_policy_fix)
        # Verify ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 failed in step2"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg

        # change policy rules to rules1 and Verify no ICMP traffic b/w VN1 and
        # VN2
        data = {
            'policy': {'entries': self.pol1_fixture.policy_obj['policy']['entries']}}
        self.pol_analyzer_fixture.update_policy(
            self.pol_analyzer_fixture.policy_obj['policy']['id'], data)
        errmsg = "Ping b/w VN1 and VN2 success in step3"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        self.detach_policy(self.vn2_policy_fix)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn2_fixture)
        # Verify no ICMP traffic b/w VN1 and VN2
        errmsg = "Ping b/w VN1 and VN2 success in step5"
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip, expectation=False), errmsg

        return True

    def verify_policy_order_change(self, si_count=1):
        random_number = randint(901, 950)
        self.domain_name = "default-domain"
        self.project_name = self.inputs.project_name

        self.vn1_name = get_random_name("VN1%s" % si_count)
        self.vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vm1_name = get_random_name('VM-traffic')
        self.vn2_name = get_random_name("VN2%s" % si_count)
        self.vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vm2_name = get_random_name('VM-ubuntu')

        self.vn1_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn1_name])
        self.vn2_fq_name = ':'.join(
            [self.domain_name, self.project_name, self.vn2_name])

        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        si_count = si_count
        self.action_list = []
        self.if_list = []
        self.st_name = get_random_name('st-analyzer-left')
        self.si_prefix = 'mirror_si_' + str(random_number)
        self.policy_name1 = get_random_name('pol1')
        self.policy_name2 = get_random_name('pol-analyzer')
        self.svc_mode = 'transparent'
        self.svc_type = 'analyzer'

        self.st_fixture, self.si_fixtures = self.config_st_si(self.st_name,
                                                              self.si_prefix, si_count, left_vn=self.vn1_fq_name, svc_type=self.svc_type, svc_mode=self.svc_mode, project=self.inputs.project_name)
        self.action_list = self.chain_si(
            si_count, self.si_prefix, self.inputs.project_name)
        self.rules1 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': 'any',
                        'src_ports': [0, -1],
                        'dest_network': 'any',
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass'}
                        }
                       ]

        self.rules2 = [{'direction': '<>',
                        'protocol': 'any',
                        'source_network': self.vn1_name,
                        'src_ports': [0, -1],
                        'dest_network': self.vn2_name,
                        'dst_ports': [0, -1],
                        'simple_action': 'pass',
                        'action_list': {'simple_action': 'pass',
                                        'mirror_to': {'analyzer_name': self.action_list[0]}}
                        }
                       ]

        self.pol1_fixture = self.config_policy(self.policy_name1, self.rules1)
        self.pol_analyzer_fixture = self.config_policy(
            self.policy_name2, self.rules2)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn2_fixture)

        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, image_name='ubuntu-traffic')
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, image_name='ubuntu')
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(self.si_fixtures)
        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step1"
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = 20
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn2_fixture)
        self.vn1_policy_a_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn1_fixture)
        self.vn2_policy_a_fix = self.attach_policy_to_vn(
            self.pol_analyzer_fixture, self.vn2_fixture)
        vn1_seq_num = {}
        vn2_seq_num = {}
        vn1_seq_num[self.policy_name1] = self.get_seq_num(
            self.vn1_fixture, self.policy_name1)
        vn1_seq_num[self.policy_name2] = self.get_seq_num(
            self.vn1_fixture, self.policy_name2)
        vn2_seq_num[self.policy_name1] = self.get_seq_num(
            self.vn2_fixture, self.policy_name1)
        vn2_seq_num[self.policy_name2] = self.get_seq_num(
            self.vn2_fixture, self.policy_name2)

        # Verify ICMP traffic b/w VN1 and VN2 but no mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step2"
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            if vn1_seq_num[self.policy_name2] < vn1_seq_num[self.policy_name1] or vn2_seq_num[self.policy_name2] < vn2_seq_num[self.policy_name1]:
                self.logger.info(
                    '%s is assigned first. Mirroring expected' % self.policy_name2)
                count = 20
            else:
                self.logger.info(
                    '%s is assigned first. No mirroring expected' % self.policy_name1)
                count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(self.vn1_policy_fix)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn1_fixture)
        self.detach_policy(self.vn2_policy_fix)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.pol1_fixture, self.vn2_fixture)

        vn1_seq_num[self.policy_name1] = self.get_seq_num(
            self.vn1_fixture, self.policy_name1)
        vn1_seq_num[self.policy_name2] = self.get_seq_num(
            self.vn1_fixture, self.policy_name2)
        vn2_seq_num[self.policy_name1] = self.get_seq_num(
            self.vn2_fixture, self.policy_name1)
        vn2_seq_num[self.policy_name2] = self.get_seq_num(
            self.vn2_fixture, self.policy_name2)

        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step3 and step4"
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            if vn1_seq_num[self.policy_name2] < vn1_seq_num[self.policy_name1] or vn2_seq_num[self.policy_name2] < vn2_seq_num[self.policy_name1]:
                self.logger.info(
                    '%s is assigned first. Mirroring expected' % self.policy_name2)
                count = 20
            else:
                self.logger.info(
                    '%s is assigned first. No mirroring expected' % self.policy_name1)
                count = 0
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)

        # Verify ICMP traffic b/w VN1 and VN2 and mirror
        errmsg = "Ping b/w VN1 and VN2 failed in step5"
        sessions = self.tcpdump_on_all_analyzer(
            self.si_fixtures, self.si_prefix, si_count)
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg
        assert self.vm2_fixture.ping_with_certainty(
            self.vm1_fixture.vm_ip), errmsg
        for svm_name, (session, pcap) in sessions.items():
            count = 20
            self.verify_icmp_mirror(svm_name, session, pcap, count)

        return True

    def get_seq_num(self, vn_fix, pol_name):
        vn_obj = self.vnc_lib.virtual_network_read(
            id=vn_fix.vn_id)
        for net_pol_ref in vn_obj.get_network_policy_refs():
            if net_pol_ref['to'][-1] == pol_name:
                vn_seq_num = net_pol_ref['attr'].sequence.major
        return vn_seq_num

    def cleanUp(self):
        super(VerifySvcMirror, self).cleanUp()
