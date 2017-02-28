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

            if compute_id == 1 and no_of_computes > 1:
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


    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 0, 0], sub_intf)

    def verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3(self, sub_intf=False):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in different VNs
        """
        compute_nodes  = self.get_compute_nodes(0, 1, 2)
        return self.verify_intf_mirroring(compute_nodes, [0, 1, 2], sub_intf)

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

    def create_sub_intf(self, vn_fix_uuid, intf_type, vlan=101, mac_address=None):

        parent_port_vn_subnets = [get_random_cidr(af=self.inputs.get_af())]
        parent_port_vn_name = get_random_name( intf_type + "_parent_port_vn")
        parent_port_vn_fixture = self.config_vn(parent_port_vn_name, parent_port_vn_subnets)
        parent_port = self.setup_vmi(parent_port_vn_fixture.uuid)
        port = self.setup_vmi(vn_fix_uuid,
                                       parent_vmi=parent_port.vmi_obj,
                                       vlan_id=vlan,
                                       api_type='contrail',
                                       mac_address=mac_address)
        return port
    # end get_sub_intf_port


    def verify_intf_mirroring(self, compute_nodes, vn_index_list, sub_intf=False):
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

        self.analyzer_port = 8099
        image_name = 'cirros'

        self.vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn3_subnets = [get_random_cidr(af=self.inputs.get_af())]


        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn1")
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn2")
        self.vn3_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn3")

        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vn3_name = self.vn3_fq_name.split(':')[2]

        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)
        self.vn3_fixture = self.config_vn(self.vn3_name, self.vn3_subnets)

        self.policy_name_vn1_vn2 = get_random_name("vn1_vn2_pass")
        self.policy_name_vn1_vn3 = get_random_name("vn1_vn3_pass")
        self.policy_name_vn2_vn3 = get_random_name("vn2_vn3_pass")

        self.rules_vn1_vn2 = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       }]

        self.rules_vn1_vn3 = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       }]

        self.rules_vn2_vn3 = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn2_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn2_name,
                       'src_ports': [0, 65535],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       }]

        self.rules_vn1_vn3.append({'direction': '<>',
                                'protocol': 'udp',
                                'source_network': self.vn1_name,
                                'src_ports': [0, 65535],
                                'dest_network': self.vn3_name,
                                'dst_ports': [0, 65535],
                                'simple_action': 'pass',
                                'action_list': {'simple_action': 'pass'}
                                }
                               )

        self.rules_vn2_vn3.append({'direction': '<>',
                                'protocol': 'udp',
                                'source_network': self.vn2_name,
                                'src_ports': [0, 65535],
                                'dest_network': self.vn3_name,
                                'dst_ports': [0, 65535],
                                'simple_action': 'pass',
                                'action_list': {'simple_action': 'pass'}
                                }
                               )

        self.rules_vn1_vn2.append({'direction': '<>',
                                'protocol': 'udp',
                                'source_network': self.vn1_name,
                                'src_ports': [0, 65535],
                                'dest_network': self.vn2_name,
                                'dst_ports': [0, 65535],
                                'simple_action': 'pass',
                                'action_list': {'simple_action': 'pass'}
                                }
                               )

        self.policy_fixture_vn1_vn2 = self.config_policy(self.policy_name_vn1_vn2, self.rules_vn1_vn2)
        self.policy_fixture_vn1_vn3 = self.config_policy(self.policy_name_vn1_vn3, self.rules_vn1_vn3)
        self.policy_fixture_vn2_vn3 = self.config_policy(self.policy_name_vn2_vn3, self.rules_vn2_vn3)

        self.vn1_v2_attach_to_vn1 = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn2, self.vn1_fixture)
        self.vn1_vn2_attach_to_vn2 = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn2, self.vn2_fixture)

        self.vn1_v3_attach_to_vn1 = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn3, self.vn1_fixture)
        self.vn1_v3_attach_to_vn3 = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn3, self.vn3_fixture)

        self.vn2_v3_attach_to_vn2 = self.attach_policy_to_vn(
            self.policy_fixture_vn2_vn3, self.vn2_fixture)
        self.vn2_v3_attach_to_vn3 = self.attach_policy_to_vn(
            self.policy_fixture_vn2_vn3, self.vn3_fixture)

        vn1_vmi_ref, vn2_vmi_ref, vn3_vmi_ref = None, None, None

        if vn_index_list[0] == 0:
           self.src_vn_fixture = self.vn1_fixture
           self.src_vn_fq_name = self.vn1_fq_name
           self.src_vn_name = self.vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               self.src_port = self.create_sub_intf(self.vn1_fixture.uuid, intf_type)

        elif vn_index_list[0] == 1:
           self.src_vn_fixture = self.vn2_fixture
           self.src_vn_fq_name = self.vn2_fq_name
           self.src_vn_name = self.vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               self.src_port = self.create_sub_intf(self.vn2_fixture.uuid, intf_type)
        else:
           self.src_vn_fixture = self.vn3_fixture
           self.src_vn_fq_name = self.vn3_fq_name
           self.src_vn_name = self.vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'src'
               self.src_port = self.create_sub_intf(self.vn3_fixture.uuid, intf_type)

        if vn_index_list[1] == 0:
           self.dst_vn_fixture = self.vn1_fixture
           self.dst_vn_fq_name = self.vn1_fq_name
           self.dst_vn_name = self.vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               self.dst_port = self.create_sub_intf(self.vn1_fixture.uuid, intf_type)

        elif vn_index_list[1] == 1:
           self.dst_vn_fixture = self.vn2_fixture
           self.dst_vn_fq_name = self.vn2_fq_name
           self.dst_vn_name = self.vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               self.dst_port = self.create_sub_intf(self.vn2_fixture.uuid, intf_type)
        else:
           self.dst_vn_fixture = self.vn3_fixture
           self.dst_vn_fq_name = self.vn3_fq_name
           self.dst_vn_name = self.vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'dst'
               self.dst_port = self.create_sub_intf(self.vn3_fixture.uuid, intf_type)

        if vn_index_list[2] == 0:
           self.analyzer_vn_fixture = self.vn1_fixture
           self.analyzer_vn_fq_name = self.vn1_fq_name
           self.analyzer_vn_name = self.vn1_fq_name.split(':')[2]
           vn1_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               self.analyzer_port = self.create_sub_intf(self.vn1_fixture.uuid, intf_type)

        elif vn_index_list[2] == 1:
           self.analyzer_vn_fixture = self.vn2_fixture
           self.analyzer_vn_fq_name = self.vn2_fq_name
           self.analyzer_vn_name = self.vn2_fq_name.split(':')[2]
           vn2_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               self.analyzer_port = self.create_sub_intf(self.vn2_fixture.uuid, intf_type)
        else:
           self.analyzer_vn_fixture = self.vn3_fixture
           self.analyzer_vn_fq_name = self.vn3_fq_name
           self.analyzer_vn_name = self.vn3_fq_name.split(':')[2]
           vn3_vmi_ref = True
           if sub_intf:
               intf_type = 'analyzer'
               self.analyzer_port = self.create_sub_intf(self.vn3_fixture.uuid, intf_type)

        self.src_vm_name = get_random_name("src_vm")
        self.dst_vm_name = get_random_name("dst_vm")
        self.analyzer_vm_name = get_random_name("analyzer_vm")

        self.analyzer_fq_name  = "default-domain:" + self.inputs.project_name + \
            ":" + self.analyzer_vm_name
        self.routing_instance = self.analyzer_vn_fq_name + ':' + self.analyzer_vn_name

        src_port_ids, dst_port_ids, analyzer_port_ids = [], [], []

        if sub_intf:
            src_port_ids.append(self.src_port.uuid)
            dst_port_ids.append(self.dst_port.uuid)
            analyzer_port_ids.append(self.analyzer_port.uuid)

        self.src_vm_fixture = self.create_vm(vn_objs=[self.src_vn_fixture.obj], vm_name=self.src_vm_name,
                                 image_name=image_name, node_name=src_compute, port_ids=src_port_ids)

        self.dst_vm_fixture = self.create_vm(vn_objs=[self.dst_vn_fixture.obj], vm_name=self.dst_vm_name,
                                 image_name=image_name, node_name=dst_compute, port_ids=dst_port_ids)

        self.analyzer_vm_fixture = self.create_vm(vn_objs=[self.analyzer_vn_fixture.obj], vm_name=self.analyzer_vm_name,
                                 image_name=image_name, node_name=analyzer_compute, port_ids=analyzer_port_ids)

        assert self.src_vm_fixture.verify_on_setup()
        assert self.dst_vm_fixture.verify_on_setup()
        assert self.analyzer_vm_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(self.src_vm_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.dst_vm_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.analyzer_vm_fixture.vm_obj)

        if vn1_vmi_ref:
            result, msg = self.validate_vn(
                self.vn1_name, project_name=self.inputs.project_name)
            assert result, msg
        if vn2_vmi_ref:
            result, msg = self.validate_vn(
                self.vn2_name, project_name=self.inputs.project_name)
            assert result, msg
        if vn3_vmi_ref:
            result, msg = self.validate_vn(
                self.vn3_name, project_name=self.inputs.project_name)
            assert result, msg

        self.src_vm_ip = self.src_vm_fixture.get_vm_ips(self.src_vn_fq_name)[0]
        self.dst_vm_ip = self.dst_vm_fixture.get_vm_ips(self.dst_vn_fq_name)[0]
        self.analyzer_vm_ip = self.analyzer_vm_fixture.get_vm_ips(self.analyzer_vn_fq_name)[0]

        self.logger.info("Compute/VM: SRC: %s / %s, -> DST: %s / %s => ANALYZER: %s / %s" %
            (src_compute, self.src_vm_ip, dst_compute, self.dst_vm_ip, analyzer_compute, self.analyzer_vm_ip))
 
        if not self._verify_intf_mirroring(self.src_vm_fixture, self.dst_vm_fixture, self.analyzer_vm_fixture, \
                self.src_vn_fq_name, self.dst_vn_fq_name, self.analyzer_vn_fq_name,
                self.analyzer_vm_ip, self.analyzer_fq_name, self.routing_instance) :
            result = result and False
        return result
    # end verify_intf_mirroring

    def _verify_intf_mirroring(self, src_vm_fixture, dst_vm_fixture, mirror_vm_fixture, src_vn_fq, dst_vn_fq, mirr_vn_fq,\
            analyzer_ip_address, analyzer_name, routing_instance):
        result = True

        src_vm_ip = src_vm_fixture.get_vm_ips(src_vn_fq)[0]
        dst_vm_ip = dst_vm_fixture.get_vm_ips(dst_vn_fq)[0]
        mirror_vm_ip = mirror_vm_fixture.get_vm_ips(mirr_vn_fq)[0]

        vnc = src_vm_fixture.vnc_lib_h

        tap_intf_uuid = src_vm_fixture.get_tap_intf_of_vm()[0]['uuid']
        tap_intf_obj = vnc.virtual_machine_interface_read(id=tap_intf_uuid)

        self.enable_intf_mirroring(vnc, tap_intf_obj, analyzer_ip_address, analyzer_name, routing_instance)

        self.logger.info("src vm ip %s -> dst vm ip %s => mirror vm ip %s" % (src_vm_ip, dst_vm_ip, mirror_vm_ip))
        if not self.verify_port_mirroring(src_vm_fixture, dst_vm_fixture, mirror_vm_fixture):
            result = result and False
            self.logger.error("Intf not mirrored")

        self.disable_intf_mirroring(vnc, tap_intf_obj)

        return result
    # end verify_intf_mirroring

    def enable_intf_mirroring(self, vnc, tap, analyzer_ip_address, analyzer_name, routing_instance,
                             direction='both', udp_port=8099,  encapsulation=None):
        prop_obj = tap.get_virtual_machine_interface_properties()
        if not prop_obj:
            prop_obj = VirtualMachineInterfacePropertiesType()
        interface_mirror = prop_obj.get_interface_mirror()
        if not interface_mirror:
            mirror_to = MirrorActionType(analyzer_name=analyzer_name, encapsulation=None, 
                analyzer_ip_address=analyzer_ip_address, routing_instance=routing_instance, udp_port=udp_port)
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
