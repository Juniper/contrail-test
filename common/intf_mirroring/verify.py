import os
from time import sleep
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from tcutils.util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out

from common.servicechain.mirror.verify import VerifySvcMirror
from random import randint
from common.openstack_libs import network_exception as exceptions

from vnc_api.gen.resource_xsd import MirrorActionType
from vnc_api.gen.resource_xsd import InterfaceMirrorType
from vnc_api.gen.resource_xsd import VirtualMachineInterfacePropertiesType

class VerifyIntfMirror(VerifySvcMirror):

    def verify_intf_mirroring(self):
        """Validate the interface mirroring
           Test steps:
           1. Create vn1/vm1, vn2/vm2, vn1/mirror_vm
           2. Create the policy rule for ICMP/UDP and attach to vn's
           3. Enable intf mirroring on vm1's port of vn1
           3. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to mirror_vm the analyzer
           Pass criteria :
            Pkts(based on direction) getting mirrored to mirror_vm
        """
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2]
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]
        self.vm1_name = get_random_name("vm1")
        self.vm2_name = get_random_name("vm2")
        self.mirror_vm_name = get_random_name("mirror_vm")
        self.analyzer_name = "default-domain:" + self.inputs.project_name + \
            ":" + self.mirror_vm_name
        self.routing_instance = self.vn1_fq_name + ':' + self.vn1_name
        self.analyzer_port = 8099
        image_name = 'ubuntu-traffic'
        self.vn1_subnets = vn1_subnets
        self.vn2_subnets = vn2_subnets
        self.policy_name = get_random_name("mirror_policy")
        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)

        self.rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn2_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       }]
        self.rules.append({'direction': '<>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [0, -1],
                               'dest_network': self.vn2_name,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass'}
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
        compute_3 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        if len(host_list) > 2:
            compute_3 = host_list[2]

        self.vm1_fixture = self.config_vm(
            self.vn1_fixture, self.vm1_name, node_name=compute_1, image_name=image_name)
        self.vm2_fixture = self.config_vm(
            self.vn2_fixture, self.vm2_name, node_name=compute_2, image_name=image_name)
        self.mirror_vm_fixture = self.config_vm(
            self.vn1_fixture, self.mirror_vm_name, node_name=compute_3, image_name=image_name)
        self.mirror_vm_ip = self.mirror_vm_fixture.get_vm_ips(self.vn1_fq_name)[0] 
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        assert self.mirror_vm_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(self.vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.mirror_vm_fixture.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg
        self.vnc = self.vm1_fixture.vnc_lib_h
        tap_intf = self.vm1_fixture.get_tap_intf_of_vm()[0]['uuid']
        vmi1_tap = self.vnc.virtual_machine_interface_read(id=tap_intf)
        analyzer_ip_address = self.mirror_vm_ip
        analyzer_name = self.analyzer_name
        routing_instance = self.routing_instance
        self.enable_intf_mirroring(self.vnc, vmi1_tap, analyzer_ip_address, analyzer_name, routing_instance)
        return self.verify_mirroring(None, self.vm1_fixture, self.vm2_fixture, self.mirror_vm_fixture)

    def enable_intf_mirroring(self, vnc, tap, analyzer_ip_address, analyzer_name, routing_instance,
                             direction='both', udp_port=8099,  encapsulation=None):
        prop_obj = tap.get_virtual_machine_interface_properties()
        if not prop_obj:
            prop_obj = VirtualMachineInterfacePropertiesType()
        interface_mirror = prop_obj.get_interface_mirror()
        if not interface_mirror:
            mirror_to = MirrorActionType(analyzer_name, None, analyzer_ip_address, routing_instance, udp_port)
            interface_mirror = InterfaceMirrorType(direction, mirror_to)
            prop_obj.set_interface_mirror(interface_mirror)
            tap.set_virtual_machine_interface_properties(prop_obj)
            tap = vnc.virtual_machine_interface_update(tap)
        else:
            mirror_to = interface_mirror.get_mirror_to()
            self.logger.info("interface_mirror obj already present")
    # end enable_intf_mirrroing

    def cleanUp(self):
        super(VerifyIntfMirror, self).cleanUp()
