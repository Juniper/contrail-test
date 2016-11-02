from time import sleep
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.servicechain.mirror.verify import VerifySvcMirror
from common.servicechain.mirror.config import ConfigSvcMirror
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify


class VerifySvcFirewall(VerifySvcMirror):

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

        vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        si_count = 3
        st_name = get_random_name("tcp_svc_template")
        si_prefix = "tcp_bridge_"
        policy_name = get_random_name("allow_tcp")
        if in_net:
            st_name = get_random_name("in_tcp_svc_template")
            si_prefix = "in_tcp_bridge_"
            policy_name = get_random_name("in_allow_tcp")
            tcp_st_fixture, tcp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            tcp_st_fixture, tcp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count)
        action_list = self.chain_si(si_count, si_prefix)
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

        self.verify_si(tcp_si_fixtures)

        st_name = get_random_name("udp_svc_template")
        si_prefix = "udp_bridge_"
        policy_name = get_random_name("allow_udp")
        if in_net:
            st_name = get_random_name("in_udp_svc_template")
            si_prefix = "in_udp_bridge_"
            policy_name = get_random_name("in_allow_udp")
            udp_st_fixture, udp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            udp_st_fixture, udp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count)
        action_list = self.chain_si(si_count, si_prefix)
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
        self.verify_si(udp_si_fixtures)

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
            tcp_st_fixture, tcp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count,
                left_vn_fixture=vn1_fixture, right_vn_fixture=vn2_fixture)
        else:
            tcp_st_fixture, tcp_si_fixtures = self.config_st_si(
                st_name, si_prefix, si_count)
        action_list = self.chain_si(si_count, si_prefix)
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

    def verify_svc_transparent_datapath(
            self, si_count=1, svc_scaling=False, max_inst=1,
            svc_mode='transparent',
            flavor=None, proto='any', src_ports=[0, -1],
            dst_ports=[0, -1], svc_img_name=None, ci=False, st_version=1,
            mgmt_vn_name=None,
            mgmt_vn_subnets=[],
            mgmt_vn_fixture=None,
            left_vn_name=None,
            left_vn_subnets=[],
            left_vn_fixture=None,
            right_vn_name=None,
            right_vn_subnets=[],
            right_vn_fixture=None,
            left_vm_name=None,
            left_vm_fixture=None,
            right_vm_name=None,
            right_vm_fixture=None,
            image_name=None):
        """Validate the service chaining datapath"""
        if not image_name:
            if ci and self.inputs.get_af() == 'v4':
                image_name = 'cirros-0.3.0-x86_64-uec'
            else:
                image_name = 'ubuntu-traffic'

        mgmt_vn_name = mgmt_vn_name or get_random_name("mgmt_vn")
        mgmt_vn_subnets = mgmt_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        mgmt_vn_fixture = mgmt_vn_fixture or self.config_vn(
            mgmt_vn_name, mgmt_vn_subnets)

        # Left
        left_vn_name = left_vn_name or get_random_name('bridge_vn1')
        left_vn_subnets = left_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        left_vn_fixture = left_vn_fixture or \
                              self.config_vn(left_vn_name, left_vn_subnets)

        # Right 
        right_vn_name = right_vn_name or get_random_name('bridge_vn2')
        rght_vn_subnets = right_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        right_vn_fixture = right_vn_fixture or \
                               self.config_vn(right_vn_name, right_vn_subnets)

        # End VMs
        left_vm_name = left_vm_name or get_random_name('bridge_vm1')
        right_vm_name = right_vm_name or get_random_name('bridge_vm2')
        left_vm_fixture = left_vm_fixture or self.config_and_verify_vm(
            left_vm_name, vn_fix=left_vn_fixture, image_name=image_name)
        right_vm_fixture = right_vm_fixture or self.config_and_verify_vm(
            right_vm_name, vn_fix=right_vn_fixture, image_name=image_name)

        # SI
        if_list = []
        st_name = get_random_name('service_template_1')
        si_prefix = get_random_name('bridge_si') + '_'
        policy_name = get_random_name('policy_transparent')
        if st_version == 1:
            (mgmt_vn, left_vn, right_vn) = (None, None, None)
        else:
            (mgmt_vn, left_vn, right_vn) = (mgmt_vn_fixture,
                                            left_vn_fixture,
                                            right_vn_fixture)

        st_fixture, si_fixtures = self.config_st_si(
            st_name, si_prefix, si_count, svc_scaling, max_inst,
            svc_mode=svc_mode, flavor=flavor, project=self.inputs.project_name,
            svc_img_name=svc_img_name, st_version=st_version, mgmt_vn_fixture=mgmt_vn,
            left_vn_fixture=left_vn, right_vn_fixture=right_vn)
        action_list = self.chain_si(
            si_count, si_prefix, self.inputs.project_name)

        rules = [
            {
                'direction': '<>',
                'protocol': proto,
                'source_network': left_vn_name,
                'src_ports': src_ports,
                'dest_network': right_vn_name,
                'dst_ports': dst_ports,
                'simple_action': None,
                'action_list': {'apply_service': action_list}
            },
        ]
        policy_fixture = self.config_policy(policy_name, rules)

        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)

        result, msg = self.validate_vn(
            left_vn_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            right_vn_name, project_name=self.inputs.project_name)
        assert result, msg

        if proto not in ['any', 'icmp']:
            self.logger.info('Will skip Ping test')
        else:
            # Ping from left VM to right VM
            errmsg = "Ping to Right VM %s from Left VM failed" % right_vm_fixture.vm_ip
            assert left_vm_fixture.ping_with_certainty(
                right_vm_fixture.vm_ip, count='3'), errmsg
        ret_dict = {
            'st_fixture' : st_fixture,
            'si_fixtures': si_fixtures,
            'policy_fixture' : policy_fixture,
            'left_vn_policy_fix' : left_vn_policy_fix,
            'right_vn_policy_fix' : right_vn_policy_fix,
            'left_vn_fixture' : left_vn_fixture,
            'right_vn_fixture' : right_vn_fixture,
            'left_vm_fixture' : left_vm_fixture,
            'right_vm_fixture' : right_vm_fixture,
        }
        return ret_dict
    # end verify_svc_transparent_datapath

    def verify_svc_in_network_datapath(self, si_count=1, svc_scaling=False,
                                       max_inst=1, svc_mode='in-network-nat',
                                       flavor=None,
                                       static_route=[None, None, None],
                                       ordered_interfaces=True,
                                       svc_img_name=None,
                                       ci=False, st_version=1,
                                       mgmt_vn_name=None,
                                       mgmt_vn_subnets=[],
                                       mgmt_vn_fixture=None,
                                       left_vn_name=None,
                                       left_vn_subnets=[],
                                       left_vn_fixture=None,
                                       right_vn_name=None,
                                       right_vn_subnets=[],
                                       right_vn_fixture=None,
                                       left_vm_name=None,
                                       left_vm_fixture=None,
                                       right_vm_name=None,
                                       right_vm_fixture=None,
                                       image_name=None):
        """Validate the service chaining in network  datapath"""

        if not image_name:
            if ci and self.inputs.get_af() == 'v4' and self.inputs.orchestrator != 'vcenter':
                image_name = 'cirros-0.3.0-x86_64-uec'
            else:
                image_name = 'ubuntu-traffic'

        mgmt_vn_name = mgmt_vn_name or get_random_name("mgmt_vn")
        mgmt_vn_subnets = mgmt_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        mgmt_vn_fixture = mgmt_vn_fixture or self.config_vn(
                              mgmt_vn_name, mgmt_vn_subnets)

        # Left
        left_vn_name = left_vn_name or get_random_name('in_network_vn1')
        left_vn_subnets = left_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        left_vn_fixture = left_vn_fixture or \
                              self.config_vn(left_vn_name, left_vn_subnets)

        # Right 
        right_vn_name = right_vn_name or get_random_name('in_network_vn2')
        rght_vn_subnets = right_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        right_vn_fixture = right_vn_fixture or \
                               self.config_vn(right_vn_name, right_vn_subnets)

        # VMs
        left_vm_name = left_vm_name or get_random_name('in_network_vm1')
        right_vm_name = right_vm_name or get_random_name('in_network_vm2')

        left_vm_fixture = left_vm_fixture or self.config_and_verify_vm(
            left_vm_name, vn_fix=left_vn_fixture, image_name=image_name)
        right_vm_fixture = right_vm_fixture or self.config_and_verify_vm(
            right_vm_name, vn_fix=right_vn_fixture, image_name=image_name)

        # SIs
        if_list = [['management', False, False],
                     ['left', True, False], ['right', True, False]]
        for entry in static_route:
            if entry != 'None':
                if_list[static_route.index(entry)][2] = True
        st_name = get_random_name("in_net_svc_template_1")
        si_prefix = get_random_name("in_net_svc_instance") + "_"

        policy_name = get_random_name("policy_in_network")
        st_fixture, si_fixtures = self.config_st_si(
            st_name, si_prefix, si_count, svc_scaling, max_inst,
            mgmt_vn_fixture=mgmt_vn_fixture, left_vn_fixture=left_vn_fixture,
            right_vn_fixture=right_vn_fixture, svc_mode=svc_mode,
            flavor=flavor, static_route=static_route,
            ordered_interfaces=ordered_interfaces, svc_img_name=svc_img_name,
            project=self.inputs.project_name, st_version=st_version)
        action_list = self.chain_si(
            si_count, si_prefix, self.inputs.project_name)
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': left_vn_fixture.vn_fq_name,
                'src_ports': [0, -1],
                'dest_network': right_vn_fixture.vn_fq_name,
                'dst_ports': [0, -1],
                'simple_action': None,
                'action_list': {'apply_service': action_list}
            },
        ]
        if self.inputs.orchestrator == 'vcenter':
            rules[0]['src_ports'] = 'any'
            rules[0]['dst_ports'] = 'any'
            rules[0]['simple_action'] = 'pass'

        policy_fixture = self.config_policy(policy_name, rules)

        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)

        result, msg = self.validate_vn(
            left_vn_fixture.vn_name, project_name=left_vn_fixture.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            right_vn_fixture.vn_name, project_name=right_vn_fixture.project_name,
            right_vn=True)
        assert result, msg

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        ret_dict = {
            'st_fixture' : st_fixture,
            'si_fixtures': si_fixtures,
            'policy_fixture' : policy_fixture,
            'left_vn_policy_fix' : left_vn_policy_fix,
            'right_vn_policy_fix' : right_vn_policy_fix,
            'left_vm_fixture' : left_vm_fixture,
            'right_vm_fixture' : right_vm_fixture,
            'left_vn_fixture' : left_vn_fixture,
            'right_vn_fixture' : right_vn_fixture,
        }
        return ret_dict
    # end verify_svc_in_network_datapath


    def verify_multi_inline_svc(self,
            si_list=[('transparent', 1), ('in-network', 1), ('in-network-nat', 1)],
            flavor=None,
            ordered_interfaces=True,
            st_version=1,
            svc_img_name=None,
            mgmt_vn_name=None,
            mgmt_vn_subnets=[],
            mgmt_vn_fixture=None,
            left_vn_name=None,
            left_vn_subnets=[],
            left_vn_fixture=None,
            right_vn_name=None,
            right_vn_subnets=[],
            right_vn_fixture=None,
            left_vm_name=None,
            left_vm_fixture=None,
            right_vm_name=None,
            right_vm_fixture=None):
        """Validate in-line multi service chaining in network  datapath"""

        mgmt_vn_name = mgmt_vn_name or get_random_name("mgmt_vn")
        mgmt_vn_subnets = mgmt_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        mgmt_vn_fixture = mgmt_vn_fixture or self.config_vn(
                              mgmt_vn_name, mgmt_vn_subnets)

        # Left
        left_vn_name = left_vn_name or get_random_name('in_network_vn1')
        left_vn_subnets = left_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        left_vn_fixture = left_vn_fixture or \
                              self.config_vn(left_vn_name, left_vn_subnets)

        # Right 
        right_vn_name = right_vn_name or get_random_name('in_network_vn2')
        rght_vn_subnets = right_vn_subnets or \
                              [get_random_cidr(af=self.inputs.get_af())]
        right_vn_fixture = right_vn_fixture or \
                               self.config_vn(right_vn_name, right_vn_subnets)

        # VMs
        left_vm_name = left_vm_name or get_random_name('in_network_vm1')
        right_vm_name = right_vm_name or get_random_name('in_network_vm2')

        left_vm_fixture = left_vm_fixture or self.config_and_verify_vm(
            left_vm_name, vn_fix=left_vn_fixture)
        right_vm_fixture = right_vm_fixture or self.config_and_verify_vm(
            right_vm_name, vn_fix=right_vn_fixture)

        action_list = []
        policy_name = get_random_name("policy_in_network")
        si_fixture_list = []
        st_fixture_list = []
        for si in si_list:
            if st_version == 1:
                (mgmt_vn, left_vn, right_vn) = (None, None, None)
            else:
                (mgmt_vn, left_vn, right_vn) = (mgmt_vn_fixture.vn_fq_name,
                                                left_vn_fixture.vn_fq_name,
                                                right_vn_fixture.vn_fq_name)
            if_list = [['management', False, False],
                       ['left', True, False], ['right', True, False]]
            svc_scaling = False
            si_count = 1
            st_name = get_random_name(
                ("multi_sc_") + si[0] + "_" + str(si_list.index(si)) + ("_st"))
            si_prefix = get_random_name(
                ("multi_sc_") + si[0] + "_" + str(si_list.index(si)) + ("_si")) + "_"
            max_inst = si[1]
            if max_inst > 1:
                svc_scaling = True
            svc_mode = si[0]
            (mgmt_vn, left_vn, right_vn) = (
                None, left_vn_fixture.vn_fq_name, right_vn_fixture.vn_fq_name)
            if svc_mode == 'transparent':
                (mgmt_vn, left_vn, right_vn) = (None, None, None)
            if st_version == 2:
                (mgmt_vn, left_vn, right_vn) = (mgmt_vn_fixture,
                                                left_vn_fixture,
                                                right_vn_fixture)
            st_fixture, si_fixtures = self.config_st_si(
                self.st_name, si_prefix, si_count, svc_scaling, max_inst,
                mgmt_vn_fixture=mgmt_vn, left_vn_fixture=left_vn,
                right_vn_fixture=right_vn, svc_mode=svc_mode, flavor=flavor,
                ordered_interfaces=ordered_interfaces,
                project=self.inputs.project_name,
                svc_img_name=svc_img_name, st_version=st_version)
            action_step = self.chain_si(
                si_count, si_prefix, self.inputs.project_name)
            action_list += action_step
            si_fixture_list.append(si_fixtures)
            st_fixture_list.append(st_fixture)
            index += 1
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': left_vn_name,
                'src_ports': [0, -1],
                'dest_network': right_vn_name,
                'dst_ports': [0, -1],
                'simple_action': None,
                'action_list': {'apply_service': action_list}
            },
        ]
        policy_fixture = self.config_policy(policy_name, rules)

        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)

        left_vm_fixture = left_vm_fixture or self.config_and_verify_vm(
            left_vm_name, vn_fix=left_vn_fixture)
        right_vm_fixture = right_vm_fixture or self.config_and_verify_vm(
            right_vm_name, vn_fix=right_vn_fixture)

        result, msg = self.validate_vn(
            left_vn_fixture.vn_name, project_name=left_vn_fixture.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            right_vn_fixture.vn_name, project_name=right_vn_fixture.project_name,
            right_vn=True)
        assert result, msg

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
        ret_dict = {
            'st_fixture_list' : st_fixture_list,
            'si_fixture_list': si_fixture_list,
            'policy_fixture' : policy_fixture,
            'left_vn_policy_fix' : left_vn_policy_fix,
            'right_vn_policy_fix' : right_vn_policy_fix,
            'left_vm_fixture' : left_vm_fixture,
            'right_vm_fixture' : right_vm_fixture,
            'left_vn_fixture' : left_vn_fixture,
            'right_vn_fixture' : right_vn_fixture,
        }
        return ret_dict
    # end verify_multi_inline_svc

    def verify_policy_delete_add(self, si_test_dict):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        si_fixtures = si_test_dict['si_fixtures']

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
                                            policy_fixture.rules)
        left_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, left_vn_fixture)
        right_vn_policy_fix = self.attach_policy_to_vn(
            policy_fixture, right_vn_fixture)
        self.verify_si(si_fixtures)

        # Wait for the existing flow entry to age
        time.sleep(40)

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
        si_fixtures = si_test_dict['si_fixtures']

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
                    'source_network': self.vn1_name,
                    'src_ports': [8000, 8000],
                    'dest_network': self.vn2_name,
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
        self.verify_si(si_fixtures)

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
        si_fixtures = si_test_dict['si_fixtures']
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
        new_left_vm_fix = self.config_vm(new_left_vn_fix, new_left_vm)
        new_right_vm_fix = self.config_vm(new_right_vn_fix, new_right_vm)
        # Wait for VM's to come up
        new_left_vm_fix.wait_till_vm_is_up()
        new_right_vm_fix.wait_till_vm_is_up()

        # Add rule to policy to allow traffic from new left_vn to right_vn
        # through SI
        action_list = policy_fixture.rules_list[0]['action_list']
        new_rule = {'direction': '<>',
                    'protocol': 'any',
                    'source_network': new_left_vn,
                    'src_ports': [0, -1],
                    'dest_network': new_right_vn,
                    'dst_ports': [0, -1],
                    'simple_action': None,
                    'action_list': {'apply_service': action_list}
                    }
        rules = policy_fixture.rules_list
        rules.append(new_rule)

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

        self.verify_si(si_fixtures)

        # Ping from left VM to right VM
        sleep(5)
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
                    'simple_action': None,
                    'action_list': {'apply_service': action_list}
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
        self.verify_si(si_fixtures)

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
        self.verify_si(si_fixtures)

        self.logger.info(
            "Icmp traffic with allow all after deleting the new left and right VN.")
        errmsg = "Ping to right VM ip %s from left VM failed" % right_vm_fixture.vm_ip
        assert left_vm_fixture.ping_with_certainty(
            right_vm_fixture.vm_ip), errmsg
    # end verify_add_new_vns

    def verify_add_new_vms(self):
        left_vn_policy_fix = si_test_dict['left_vn_policy_fix']
        right_vn_policy_fix = si_test_dict['right_vn_policy_fix']
        policy_fixture = si_test_dict['policy_fixture']
        left_vm_fixture = si_test_dict['left_vm_fixture']
        right_vm_fixture = si_test_dict['right_vm_fixture']
        si_fixtures = si_test_dict['si_fixtures']

        # Launch VMs in new left and right VN's
        new_left_vm = 'new_left_bridge_vm'
        new_right_vm = 'new_right_bridge_vm'
        new_left_vm_fix = self.config_vm(left_vn_fixture, new_left_vm)
        new_right_vm_fix = self.config_vm(right_vm_fixture, new_right_vm)
        # Wait for VM's to come up
        assert new_left_vm_fix.wait_till_vm_is_up()
        assert new_right_vm_fix.wait_till_vm_is_up()

        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % new_right_vm_fix.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            new_right_vm_fix.vm_ip), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
        assert new_left_vm_fix.ping_with_certainty(
            self.vm2_fixture.vm_ip), errmsg

        errmsg = "Ping to right VM ip %s from left VM failed" % self.vm2_fixture.vm_ip
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
        self.verify_si(si_fixtures)

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
        self, si_count=1, svc_scaling=False, max_inst=1,
            firewall_svc_mode='in-network', mirror_svc_mode='transparent', flavor='contrail_flavor_2cpu', vn1_subnets=None, vn2_subnets=None):
        """Validate the service chaining in network  datapath"""

        vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn1")
        vn1_name = vn1_fq_name.split(':')[2]
        vn1_subnets = [
            vn1_subnets or get_random_cidr(af=self.inputs.get_af())]
        vm1_name = get_random_name("in_network_vm1")
        vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("in_network_vn2")
        vn2_name = vn2_fq_name.split(':')[2]
        vn2_subnets = [
            vn2_subnets or get_random_cidr(af=self.inputs.get_af())]
        vm2_name = get_random_name("in_network_vm2")
        action_list = []
        firewall_st_name = get_random_name("svc_firewall_template_1")
        firewall_si_prefix = get_random_name("svc_firewall_instance") + "_"
        mirror_st_name = get_random_name("svc_mirror_template_1")
        mirror_si_prefix = get_random_name("svc_mirror_instance") + "_"
        policy_name = get_random_name("policy_in_network")
        vn1_fixture = self.config_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.config_vn(vn2_name, vn2_subnets)
        if firewall_svc_mode == 'transparent':
            if_list = []
            st_fixture, firewall_si_fixtures = self.config_st_si(
                firewall_st_name,
                firewall_si_prefix, si_count,
                svc_scaling, max_inst,
                left_vn_fixture=None, right_vn_fixture=None,
                svc_img_name='tiny_trans_fw',
                svc_mode=firewall_svc_mode, flavor=flavor, project=self.inputs.project_name)
        if firewall_svc_mode == 'in-network'or firewall_svc_mode == 'in-network-nat':
            st_fixture, firewall_si_fixtures = self.config_st_si(
                firewall_st_name,
                firewall_si_prefix, si_count,
                svc_scaling, max_inst,
                left_vn_fixture=vn1_fixture,
                right_vn_fixture=vn2_fixture,
                svc_img_name='ubuntu-in-net',
                svc_mode=firewall_svc_mode, flavor=flavor, project=self.inputs.project_name)
        action_list = self.chain_si(
            si_count, firewall_si_prefix, self.inputs.project_name)
        st_fixture, mirror_si_fixtures = self.config_st_si(
            mirror_st_name,
            mirror_si_prefix, si_count,
            left_vn_fixture=vn1_fixture,
            svc_type='analyzer',
            svc_mode=mirror_svc_mode, flavor=flavor, project=self.inputs.project_name)
        action_list += (self.chain_si(si_count,
                                           mirror_si_prefix, self.inputs.project_name))
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1_name,
                'src_ports': [0, -1],
                'dest_network': vn2_name,
                'dst_ports': [0, -1],
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

        vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        result, msg = self.validate_vn(
            vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.verify_si(firewall_si_fixtures)
        self.verify_si(mirror_si_fixtures)

        for si_fix in firewall_si_fixtures:
            svms = self.get_svms_in_si(si_fix, self.inputs.project_name)
        for svm in svms:
            svm_name = svm.name
            host = self.get_svm_compute(svm_name)
            svm_node_ip = host
        # Ping from left VM to right VM
        errmsg = "Ping to right VM ip %s from left VM failed" % vm2_fixture.vm_ip
        assert vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip), errmsg

        # Verify ICMP mirror
        sessions = self.tcpdump_on_all_analyzer(
            mirror_si_fixtures, mirror_si_prefix, si_count)
        errmsg = "Ping to right VM ip %s from left VM failed" % vm2_fixture.vm_ip
        assert vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip), errmsg
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
