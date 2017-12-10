import os
from time import sleep
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from tcutils.util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out

from common.servicechain.mirror.verify import VerifySvcMirror
from random import randint

from vnc_api.gen.resource_xsd import MirrorActionType
from vnc_api.gen.resource_xsd import InterfaceMirrorType
from vnc_api.gen.resource_xsd import VirtualMachineInterfacePropertiesType

class VerifyIntfMirror(VerifySvcMirror):


    def get_compute_nodes(self, src, dst, analyzer):
        host_list = []
        compute_nodes = []

        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])

        no_of_computes = len(host_list)

        for compute_id in [src, dst, analyzer]:
            if compute_id == 0:
                compute_nodes.append(host_list[0])

            if compute_id == 1:
                if no_of_computes > 1:
                    compute_nodes.append(host_list[1])
                else:
                    compute_nodes.append(host_list[0])

            if compute_id == 2:
                if no_of_computes > 2:
                    compute_nodes.append(host_list[2])
                elif no_of_computes == 2:
                    compute_nodes.append(host_list[1])
                else:
                    compute_nodes.append(host_list[0])

        self.logger.info("src compute %s -> dst compute %s => analyzer compute %s" %
            (compute_nodes[0], compute_nodes[1], compute_nodes[2]))
        return compute_nodes


    def verify_intf_mirroring_disable_enable_scenarios(self):
        """Validate the interface mirroring
        Verify sub/parent interface mirroring various enable/disable combinations
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3(sub_intf=True, parent_intf=True)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3(self, sub_intf=False, parent_intf=False, nic_mirror=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in different VNs
        """
        # When both sub_intf and parent_intf vars are set, verify disable/enable scenarios
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf, parent_intf, nic_mirror)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and dst in vn1, analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and analyzer in vn1, dst in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src in vn1, dst and analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 1], sub_intf)


    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in same VN
        """

        compute_nodes = self.get_compute_nodes(0, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in different VNs
        """

        compute_nodes = self.get_compute_nodes(0, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and dst in vn1, analyzer in vn2
        """

        compute_nodes = self.get_compute_nodes(0, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and analyzer in vn1, dst in vn2
        """

        compute_nodes = self.get_compute_nodes(0, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src in vn1, dst and analyzer in vn2
        """

        compute_nodes = self.get_compute_nodes(0, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 1], sub_intf)


    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in same VN
        """
        compute_nodes  = self.get_compute_nodes(0, 0, 1)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn3(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in different VNs
        """
        compute_nodes  = self.get_compute_nodes(0, 0, 1)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and dst in vn1, analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 0, 1)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and analyzer in vn1, dst in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 0, 1)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src in vn1, dst and analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 0, 1)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 1], sub_intf)


    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in same VN
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn3(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in different VNs
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and dst in vn1, analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and analyzer in vn1, dst in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src in vn1, dst and analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in same VN
        """
        compute_nodes  = self.get_compute_nodes(1, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(self, sub_intf=False):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in different VNs
        """
        compute_nodes  = self.get_compute_nodes(1, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf)

    def verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and dst in vn1, analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(1, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 1], sub_intf)

    def verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and analyzer in vn1, dst in vn2
        """
        compute_nodes  = self.get_compute_nodes(1, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(self, sub_intf=False):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src in vn1, dst and analyzer in vn2
        """
        compute_nodes  = self.get_compute_nodes(1, 0, 0)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 1], sub_intf)

    def create_sub_intf(self, vn_fix_uuid, intf_type, mac_address=None):

        vlan = self.vlan
        parent_port_vn_subnets = [get_random_cidr(af=self.inputs.get_af())]
        parent_port_vn_name = get_random_name( intf_type + "_parent_port_vn")
        parent_port_vn_fixture = self.config_vn(parent_port_vn_name, parent_port_vn_subnets)
        parent_port = self.setup_vmi(parent_port_vn_fixture.uuid)
        mac_address = parent_port.mac_address
        port = self.setup_vmi(vn_fix_uuid,
                                       parent_vmi=parent_port.vmi_obj,
                                       vlan_id=vlan,
                                       api_type='contrail',
                                       mac_address=mac_address)
        return port, parent_port, parent_port_vn_fixture
    # end get_sub_intf_port

    def create_policy_rule(self, src_vn, dst_vn):

        rules = [{'direction': '<>',
            'protocol': 'icmp',
            'source_network': src_vn,
            'src_ports': [0, 65535],
            'dest_network': dst_vn,
            'dst_ports': [0, 65535],
            'simple_action': 'pass',
            'action_list': {'simple_action': 'pass'}
            },
            {'direction': '<>',
            'protocol': 'icmp6',
            'source_network': src_vn,
            'src_ports': [0, 65535],
            'dest_network': dst_vn,
            'dst_ports': [0, 65535],
            'simple_action': 'pass',
            'action_list': {'simple_action': 'pass'}
            }]

        rules.append({'direction': '<>',
            'protocol': 'udp',
            'source_network': src_vn,
            'src_ports': [0, 65535],
            'dest_network': dst_vn,
            'dst_ports': [0, 65535],
            'simple_action': 'pass',
            'action_list': {'simple_action': 'pass'}
            })
        return rules
    # end create_policy_rule

    def verify_intf_mirroring(self, compute_nodes, vn_index_list, sub_intf=False, parent_intf=False, nic_mirror=False):
        """Validate the interface mirroring
           Test steps:
           1. Create vn1/vm1_vn1, vn1/vm2_vn1, vn1/mirror_vm_vn1,  vn2/vm2_vn2, vn2/mirror_vm_vn2, vn3/mirror_vm_vn3
           2. Create the policies vn1_vn2 and vn1_vn3 for ICMP/UDP and attach to vn's
           3. Enable intf mirroring on src vm's port and test the following cases:
               src vm in vn1, mirror vm in vn1, and dst vm in vn2
               src vm in vn1, mirror vm in vn3, and dst vm in vn2
               src vm, dst vm and mirror vm all are in vn1
               src vm in vn1, dst vm in vn2, and mirror vm in vn2
           4. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to mirror_vm the analyzer
           Pass criteria :
            Pkts(based on direction) getting mirrored to mirror_vm
        """
        result = True

        src_compute = compute_nodes[0]
        dst_compute = compute_nodes[1]
        analyzer_compute = compute_nodes[2]

        analyzer_port = 8099
        image_name = 'cirros' if not sub_intf else 'ubuntu-traffic'

        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn3_subnets = [get_random_cidr(af=self.inputs.get_af())]


        vn1_fq_name = self.connections.domain_name +":"  + self.inputs.project_name + \
            ":" + get_random_name("vn1")
        vn2_fq_name = self.connections.domain_name +":"  + self.inputs.project_name + \
            ":" + get_random_name("vn2")
        vn3_fq_name = self.connections.domain_name +":"  + self.inputs.project_name + \
            ":" + get_random_name("vn3")

        vn1_name = vn1_fq_name.split(':')[2]
        vn2_name = vn2_fq_name.split(':')[2]
        vn3_name = vn3_fq_name.split(':')[2]

        vn1_fixture = self.config_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.config_vn(vn2_name, vn2_subnets)
        vn3_fixture = self.config_vn(vn3_name, vn3_subnets)

        policy_name_vn1_vn2 = get_random_name("vn1_vn2_pass")
        policy_name_vn1_vn3 = get_random_name("vn1_vn3_pass")
        policy_name_vn2_vn3 = get_random_name("vn2_vn3_pass")

        rules_vn1_vn2 = self.create_policy_rule(vn1_name, vn2_name)
        rules_vn1_vn3 = self.create_policy_rule(vn1_name, vn3_name)
        rules_vn2_vn3 = self.create_policy_rule(vn2_name, vn3_name)

        policy_fixture_vn1_vn2 = self.config_policy(policy_name_vn1_vn2, rules_vn1_vn2)
        policy_fixture_vn1_vn3 = self.config_policy(policy_name_vn1_vn3, rules_vn1_vn3)
        policy_fixture_vn2_vn3 = self.config_policy(policy_name_vn2_vn3, rules_vn2_vn3)

        vn1_v2_attach_to_vn1 = self.attach_policy_to_vn(
            policy_fixture_vn1_vn2, vn1_fixture)
        vn1_vn2_attach_to_vn2 = self.attach_policy_to_vn(
            policy_fixture_vn1_vn2, vn2_fixture)

        vn1_v3_attach_to_vn1 = self.attach_policy_to_vn(
            policy_fixture_vn1_vn3, vn1_fixture)
        vn1_v3_attach_to_vn3 = self.attach_policy_to_vn(
            policy_fixture_vn1_vn3, vn3_fixture)

        vn2_v3_attach_to_vn2 = self.attach_policy_to_vn(
            policy_fixture_vn2_vn3, vn2_fixture)
        vn2_v3_attach_to_vn3 = self.attach_policy_to_vn(
            policy_fixture_vn2_vn3, vn3_fixture)

        vn1_vmi_ref, vn2_vmi_ref, vn3_vmi_ref = None, None, None

        self.vlan = 101

        if vn_index_list[0] == 0:
           src_vn_fixture = vn1_fixture
           src_vn_fq_name = vn1_fq_name
           src_vn_name = vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               src_port, src_parent_port, src_parent_port_vn_fixture = self.create_sub_intf(vn1_fixture.uuid, intf_type)

        elif vn_index_list[0] == 1:
           src_vn_fixture = vn2_fixture
           src_vn_fq_name = vn2_fq_name
           src_vn_name = vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               src_port, src_parent_port, src_parent_port_vn_fixture = self.create_sub_intf(vn2_fixture.uuid, intf_type)
        else:
           src_vn_fixture = vn3_fixture
           src_vn_fq_name = vn3_fq_name
           src_vn_name = vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               src_port, src_parent_port, src_parent_port_vn_fixture = self.create_sub_intf(vn3_fixture.uuid, intf_type)

        if vn_index_list[1] == 0:
           dst_vn_fixture = vn1_fixture
           dst_vn_fq_name = vn1_fq_name
           dst_vn_name = vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               dst_port, dst_parent_port, dst_parent_port_vn_fixture = self.create_sub_intf(vn1_fixture.uuid, intf_type)

        elif vn_index_list[1] == 1:
           dst_vn_fixture = vn2_fixture
           dst_vn_fq_name = vn2_fq_name
           dst_vn_name = vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               dst_port, dst_parent_port, dst_parent_port_vn_fixture = self.create_sub_intf(vn2_fixture.uuid, intf_type)
        else:
           dst_vn_fixture = vn3_fixture
           dst_vn_fq_name = vn3_fq_name
           dst_vn_name = vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               dst_port, dst_parent_port, dst_parent_port_vn_fixture = self.create_sub_intf(vn3_fixture.uuid, intf_type)

        if vn_index_list[2] == 0:
           analyzer_vn_fixture = vn1_fixture
           analyzer_vn_fq_name = vn1_fq_name
           analyzer_vn_name = vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               analyzer_port, analyzer_parent_port, analyzer_parent_port_vn_fixture = self.create_sub_intf(vn1_fixture.uuid, intf_type)

        elif vn_index_list[2] == 1:
           analyzer_vn_fixture = vn2_fixture
           analyzer_vn_fq_name = vn2_fq_name
           analyzer_vn_name = vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               analyzer_port, analyzer_parent_port, analyzer_parent_port_vn_fixture = self.create_sub_intf(vn2_fixture.uuid, intf_type)
        else:
           analyzer_vn_fixture = vn3_fixture
           analyzer_vn_fq_name = vn3_fq_name
           analyzer_vn_name = vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               analyzer_port, analyzer_parent_port, analyzer_parent_port_vn_fixture = self.create_sub_intf(vn3_fixture.uuid, intf_type)

        if parent_intf:
            policy_name_src_parent_vn_analyzer_vn = get_random_name("src_parent_to_analyzer_pass")
            policy_name_dst_parent_vn_analyzer_vn = get_random_name("dst_parent_to_analyzer_pass")

            src_parent_vn_name = src_parent_port_vn_fixture.vn_name
            dst_parent_vn_name = dst_parent_port_vn_fixture.vn_name

            rules_src_parent_vn_analyzer_vn = self.create_policy_rule(src_parent_vn_name, analyzer_vn_name)
            rules_dst_parent_vn_analyzer_vn = self.create_policy_rule(dst_parent_vn_name, analyzer_vn_name)

            policy_fixture_src_parent_vn_analyzer_vn = self.config_policy(
                policy_name_src_parent_vn_analyzer_vn, rules_src_parent_vn_analyzer_vn)
            policy_fixture_dst_parent_vn_analyzer_vn = self.config_policy(
                policy_name_dst_parent_vn_analyzer_vn, rules_dst_parent_vn_analyzer_vn)

            self.attach_policy_to_vn(
                policy_fixture_src_parent_vn_analyzer_vn, analyzer_vn_fixture)

            self.attach_policy_to_vn(
                policy_fixture_src_parent_vn_analyzer_vn, src_parent_port_vn_fixture)

            self.attach_policy_to_vn(
                policy_fixture_dst_parent_vn_analyzer_vn, analyzer_vn_fixture)

            self.attach_policy_to_vn(
                policy_fixture_dst_parent_vn_analyzer_vn,dst_parent_port_vn_fixture)

        src_vm_name = get_random_name("src_vm")
        dst_vm_name = get_random_name("dst_vm")
        analyzer_vm_name = get_random_name("analyzer_vm")

        analyzer_fq_name  = self.connections.domain_name +":"  + self.inputs.project_name + \
            ":" + analyzer_vm_name
        routing_instance = analyzer_vn_fq_name + ':' + analyzer_vn_name

        src_port_ids, dst_port_ids, analyzer_port_ids = [], [], []

        src_vn_objs = [src_vn_fixture.obj]
        dst_vn_objs = [dst_vn_fixture.obj]
        analyzer_vn_objs = [analyzer_vn_fixture.obj]

        if sub_intf:
            src_port_ids.append(src_parent_port.uuid)
            dst_port_ids.append(dst_parent_port.uuid)
            analyzer_port_ids.append(analyzer_parent_port.uuid)
            src_vn_objs = [src_parent_port_vn_fixture.obj]
            dst_vn_objs = [dst_parent_port_vn_fixture.obj]
            analyzer_vn_objs = [analyzer_parent_port_vn_fixture.obj]

        src_vm_fixture = self.create_vm(vn_objs=src_vn_objs, vm_name=src_vm_name,
            image_name=image_name, node_name=src_compute, port_ids=src_port_ids)

        dst_vm_fixture = self.create_vm(vn_objs=dst_vn_objs, vm_name=dst_vm_name,
            image_name=image_name, node_name=dst_compute, port_ids=dst_port_ids)

        analyzer_vm_fixture = self.create_vm(vn_objs=analyzer_vn_objs, vm_name=analyzer_vm_name,
            image_name=image_name, node_name=analyzer_compute, port_ids=analyzer_port_ids)

        assert src_vm_fixture.verify_on_setup()
        assert dst_vm_fixture.verify_on_setup()
        assert analyzer_vm_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(src_vm_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(dst_vm_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(analyzer_vm_fixture.vm_obj)
        if vn1_vmi_ref:
            result, msg = self.validate_vn(vn_fq_name=vn1_fq_name)
            assert result, msg
        if vn2_vmi_ref:
            result, msg = self.validate_vn(vn_fq_name=vn2_fq_name)
            assert result, msg
        if vn3_vmi_ref:
            result, msg = self.validate_vn(vn_fq_name=vn3_fq_name)

            assert result, msg

        if sub_intf:
            src_vm_ip = src_port.obj['fixed_ips'][0]['ip_address']
            dst_vm_ip = dst_port.obj['fixed_ips'][0]['ip_address']
            analyzer_vm_ip = analyzer_port.obj['fixed_ips'][0]['ip_address']
        else:
            src_vm_ip = src_vm_fixture.get_vm_ips(src_vn_fq_name)[0]
            dst_vm_ip = dst_vm_fixture.get_vm_ips(dst_vn_fq_name)[0]
            analyzer_vm_ip = analyzer_vm_fixture.get_vm_ips(analyzer_vn_fq_name)[0]

        self.logger.info("Compute/VM: SRC: %s / %s, -> DST: %s / %s => ANALYZER: %s / %s" %
            (src_compute, src_vm_ip, dst_compute, dst_vm_ip, analyzer_compute, analyzer_vm_ip))
        if parent_intf:
            parent_src_vm_ip = src_vm_fixture.get_vm_ips()[0]
            parent_dst_vm_ip = dst_vm_fixture.get_vm_ips()[0]
            parent_analyzer_vm_ip = analyzer_vm_fixture.get_vm_ips()[0]

        sport = None

        if sub_intf:
            intf_type = 'src'
            cmds = ['sudo vconfig add eth0 101','sudo ifconfig eth0.101 up','sudo udhcpc -i eth0.101']
            output = src_vm_fixture.run_cmd_on_vm(cmds = cmds)

            intf_type = 'dst'
            cmds = ['sudo vconfig add eth0 101','sudo ifconfig eth0.101 up','sudo udhcpc -i eth0.101']
            output = dst_vm_fixture.run_cmd_on_vm(cmds = cmds)

            intf_type = 'analyzer'
            cmds = ['sudo vconfig add eth0 101','sudo ifconfig eth0.101 up','sudo udhcpc -i eth0.101']
            output = analyzer_vm_fixture.run_cmd_on_vm(cmds = cmds)
            sport = src_port.vmi_obj

        if not self._verify_intf_mirroring(src_vm_fixture, dst_vm_fixture, analyzer_vm_fixture, \
                src_vn_fq_name, dst_vn_fq_name, analyzer_vn_fq_name,
                analyzer_vm_ip, analyzer_fq_name, routing_instance, src_port=sport, sub_intf=sub_intf, parent_intf=parent_intf, nic_mirror=nic_mirror):
            result = result and False

        return result
    # end verify_intf_mirroring

    def config_intf_mirroring(self, src_vm_fixture, analyzer_ip_address, analyzer_name, routing_instance, \
            src_port=None, sub_intf=False, parent_intf=False, nic_mirror=False):

        vnc = src_vm_fixture.vnc_lib_h
        vlan = None
        tap_intf_obj = None
        parent_tap_intf_obj = None
        vlan = None
        if not sub_intf:
            tap_intf_uuid = src_vm_fixture.get_tap_intf_of_vm()[0]['uuid']
            tap_intf_obj = vnc.virtual_machine_interface_read(id=tap_intf_uuid)
        else:
            tap_intf_obj = src_port
            vlan = self.vlan

        if parent_intf:
            parent_tap_intf_uuid = src_vm_fixture.get_tap_intf_of_vm()[0]['uuid']
            parent_tap_intf_obj = vnc.virtual_machine_interface_read(id=parent_tap_intf_uuid)
         
        if not nic_mirror:
            self.enable_intf_mirroring(vnc, tap_intf_obj, analyzer_ip_address, analyzer_name, routing_instance)
            if parent_intf:
                self.logger.info("Intf mirroring enabled on both sub intf port and parent port")
                self.enable_intf_mirroring(vnc, parent_tap_intf_obj, analyzer_ip_address, analyzer_name, routing_instance)
            return vnc, tap_intf_obj, parent_tap_intf_obj, vlan
        else:
            self.enable_intf_mirroring(vnc, tap_intf_obj, analyzer_ip_address=None, analyzer_name=analyzer_name, \
                routing_instance=None, udp_port=None, nic_assisted_mirroring=True, nic_assisted_mirroring_vlan=100)
            if src_vm_fixture.vm_obj.status == 'ACTIVE':
                host = self.get_svm_compute(src_vm_fixture.vm_obj.name)
            session = ssh(host['host_ip'], host['username'], host['password'])
            agent_physical_interface = src_vm_fixture.agent_inspect[host['host_ip']].get_agent_physical_interface()
            pcap = self.start_tcpdump(session, agent_physical_interface, vlan=100)
            src_vm_fixture.ping_with_certainty(mirror_vm_fixture.vm_ip, count=11, size='1400')
            filt = '-e | grep \"vlan 100\"'
            mirror_pkt_count = self.stop_tcpdump(session, pcap, filt)
            if mirror_pkt_count == 0:
                self.logger.error("Nic mirroring doesn't works correctly")
                result = result and False
            else:
                self.logger.info("Nic mirroring works correctly")
    # end config_intf_mirroring

    def _verify_intf_mirroring(self, src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, src_vn_fq, dst_vn_fq, mirr_vn_fq,\
            analyzer_ip_address, analyzer_name, routing_instance, src_port=None, sub_intf=False, parent_intf=False, nic_mirror=False):
        result = True
        vnc, tap_intf_obj, parent_tap_intf_obj, vlan = self.config_intf_mirroring(
            src_vm_fixture, analyzer_ip_address, analyzer_name, routing_instance, src_port=src_port, sub_intf=sub_intf, parent_intf=parent_intf, nic_mirror=nic_mirror)

        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, vlan=vlan, parent=parent_intf):
            result = result and False
            if parent:
                self.logger.error("Traffic mirroring from both the ports expected, failed from one or both")
            elif vlan:
                self.logger.error("Traffic mirroring from the sub intf port failed")
            else:
                self.logger.error("Intf mirroring not working")

        self.logger.info("Disabling intf mirroring on sub intf port")
        self.disable_intf_mirroring(vnc, tap_intf_obj)

        if parent_tap_intf_obj:
            self.logger.info("Disabling intf mirroring on parent intf port")
            self.disable_intf_mirroring(vnc, parent_tap_intf_obj)

        if parent_intf:
            if not self.verify_disable_enable_combinations(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, \
                    analyzer_ip_address, analyzer_name, routing_instance, src_port=src_port, sub_intf=sub_intf, parent_intf=parent_intf):
                result = result and False

        return result
    # end _verify_intf_mirroring

    def verify_disable_enable_combinations(self, src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, \
            analyzer_ip_address, analyzer_name, routing_instance, src_port=None, sub_intf=False, parent_intf=False):
        result = True
        vnc, tap_intf_obj, parent_tap_intf_obj, vlan = self.config_intf_mirroring(
            src_vm_fixture, analyzer_ip_address, analyzer_name, routing_instance, src_port=src_port, sub_intf=sub_intf, parent_intf=parent_intf)

        # Mirroring disabled on sub intf, but enabled on parent port, expect sub intf traffic to get mirrored via parent port
        self.disable_intf_mirroring(vnc, tap_intf_obj)
        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, vlan=vlan):
            result = result and False
            self.logger.error("Traffic stopped getting mirrored from parent port after disabling intf mirroring on sub intf port")
        else:
            self.logger.info("Traffic is getting mirrored from parent port as expected")

        self.logger.info("Enabling intf mirroring on sub intf, expect pkts to get mirrored from both the ports")
        self.enable_intf_mirroring(vnc, tap_intf_obj, analyzer_ip_address, analyzer_name, routing_instance)

        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, vlan=vlan, parent=parent_intf):
            result = result and False
            self.logger.error("Traffic is not getting mirrored from both parent port and sub intf")
        else:
            self.logger.info("Traffic is getting mirrored from both parent port and sub intf as expected")
        # Disable intf mirroring on parent port
        self.disable_intf_mirroring(vnc, parent_tap_intf_obj)

        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, vlan=vlan):
            result = result and False
            self.logger.error("Traffic stopped getting mirrored from sub intf after disabling intf mirroring on parent port")
        else:
            self.logger.info("Traffic is getting mirrored from sub intf as expected")

        # enable intf mirroring on parent port
        self.enable_intf_mirroring(vnc, parent_tap_intf_obj, analyzer_ip_address, analyzer_name, routing_instance)

        self.logger.info("Check traffic is getting mirrored from both the ports")

        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, vlan=vlan, parent=parent_intf):
            result = result and False
            self.logger.error("Traffic not is getting mirrored from both the ports")
        else:
            self.logger.info("Traffic is getting mirrored from both the ports as expected")

        self.disable_intf_mirroring(vnc, tap_intf_obj)
        self.disable_intf_mirroring(vnc, parent_tap_intf_obj)

        return result
    # end verify_disable_enable_combinations

    def enable_intf_mirroring(self, vnc, tap, analyzer_ip_address, analyzer_name, routing_instance,
                             direction='both', udp_port=8099,  encapsulation=None, \
                             nic_assisted_mirroring = None, nic_assisted_mirroring_vlan = None):
        prop_obj = tap.get_virtual_machine_interface_properties()
        if not prop_obj:
            prop_obj = VirtualMachineInterfacePropertiesType()
        interface_mirror = prop_obj.get_interface_mirror()
        if not interface_mirror:
            mirror_to = MirrorActionType(analyzer_name=analyzer_name, encapsulation=None, 
                analyzer_ip_address=analyzer_ip_address, routing_instance=routing_instance, udp_port=udp_port, nic_assisted_mirroring = nic_assisted_mirroring, nic_assisted_mirroring_vlan = nic_assisted_mirroring_vlan)
            interface_mirror = InterfaceMirrorType(direction, mirror_to)
            prop_obj.set_interface_mirror(interface_mirror)
            tap.set_virtual_machine_interface_properties(prop_obj)
            tap = vnc.virtual_machine_interface_update(tap)
        else:
            mirror_to = interface_mirror.get_mirror_to()
            self.logger.info("interface_mirror obj already present")
    # end enable_intf_mirrroing

    def disable_intf_mirroring(self, vnc, tap):
        prop_obj = tap.get_virtual_machine_interface_properties()
        if not prop_obj:
            self.logger.info("interface_mirror not enabled")
        else:
            self.logger.info("interface_mirror enabled..disabling it..")
            prop_obj.set_interface_mirror(None)
            tap.set_virtual_machine_interface_properties(prop_obj)
            tap = vnc.virtual_machine_interface_update(tap)
    # end disable_intf_mirrroing

    def cleanUp(self):
        super(VerifyIntfMirror, self).cleanUp()
