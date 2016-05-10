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

   def verify_intf_mirroring_1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs
        """
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
        src_compute = compute_1
        dst_compute = compute_2
        analyzer_compute = compute_3
        return self.verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute)        

   def verify_intf_mirroring_2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN
        """
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
        src_compute = compute_1
        dst_compute = compute_1
        analyzer_compute = compute_1
        return self.verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute)

   def verify_intf_mirroring_3(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN
        """
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
        src_compute = compute_1
        dst_compute = compute_1
        analyzer_compute = compute_2
        return self.verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute)

   def verify_intf_mirroring_4(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN
        """
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
        src_compute = compute_1
        dst_compute = compute_2
        analyzer_compute = compute_1
        return self.verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute)

   def verify_intf_mirroring_5(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN
        """
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
        src_compute = compute_1
        dst_compute = compute_2
        analyzer_compute = compute_2
        return self.verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute)

    def verify_intf_mirroring(self, src_compute, dst_compute, analyzer_compute):
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

        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn3_subnets = [get_random_cidr(af=self.inputs.get_af())]

        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn1")
        self.vn1_name = self.vn1_fq_name.split(':')[2] 
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn2")
        self.vn2_name = self.vn2_fq_name.split(':')[2]

        self.vn3_fq_name = "default-domain:" + self.inputs.project_name + \
            ":" + get_random_name("vn3")
        self.vn3_name = self.vn3_fq_name.split(':')[2]

        self.vm1_name_vn1 = get_random_name("vm1_vn1")
        self.vm2_name_vn2 = get_random_name("vm2_vn2")
        self.vm2_name_vn1 = get_random_name("vm2_vn1")

        self.mirror_vm_name_vn1 = get_random_name("mirror_vm_vn1")
        self.mirror_vm_name_vn2 = get_random_name("mirror_vm_vn2")
        self.mirror_vm_name_vn3 = get_random_name("mirror_vm_vn3")

        self.analyzer_name_vn1 = "default-domain:" + self.inputs.project_name + \
            ":" + self.mirror_vm_name_vn1
        self.routing_instance_vn1 = self.vn1_fq_name + ':' + self.vn1_name

        self.analyzer_name_vn3 = "default-domain:" + self.inputs.project_name + \
            ":" + self.mirror_vm_name_vn3
        self.routing_instance_vn3 = self.vn3_fq_name + ':' + self.vn3_name

        self.analyzer_name_vn2 = "default-domain:" + self.inputs.project_name + \
            ":" + self.mirror_vm_name_vn2
        self.routing_instance_vn2 = self.vn2_fq_name + ':' + self.vn2_name

        self.analyzer_port = 8099
        image_name = 'ubuntu-traffic'

        self.vn1_subnets = vn1_subnets
        self.vn2_subnets = vn2_subnets
        self.vn3_subnets = vn3_subnets

        self.policy_name_vn1_vn2 = get_random_name("vn1_vn2_pass")
        self.policy_name_vn1_vn3 = get_random_name("vn1_vn3_pass")

        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)
        self.vn3_fixture = self.config_vn(self.vn3_name, self.vn3_subnets)

        self.rules_vn1_vn2 = [{'direction': '<>',
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
        self.rules_vn1_vn2.append({'direction': '<>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [0, -1],
                               'dest_network': self.vn2_name,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass'}
                               }
                              )

        self.rules_vn1_vn3 = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': self.vn1_name,
                       'src_ports': [0, -1],
                       'dest_network': self.vn3_name,
                       'dst_ports': [0, -1],
                       'simple_action': 'pass',
                       'action_list': {'simple_action': 'pass'}
                       }]
        self.rules_vn1_vn3.append({'direction': '<>',
                               'protocol': 'udp',
                               'source_network': self.vn1_name,
                               'src_ports': [0, -1],
                               'dest_network': self.vn3_name,
                               'dst_ports': [0, -1],
                               'simple_action': 'pass',
                               'action_list': {'simple_action': 'pass'}
                               }
                              )
        self.policy_fixture_vn1_vn2 = self.config_policy(self.policy_name_vn1_vn2, self.rules_vn1_vn2)
        self.policy_fixture_vn1_vn3 = self.config_policy(self.policy_name_vn1_vn3, self.rules_vn1_vn3)

        self.policy_fixture_vn1_vn2 = self.config_policy(self.policy_name_vn1_vn2, self.rules_vn1_vn2)
        self.policy_fixture_vn1_vn3 = self.config_policy(self.policy_name_vn1_vn3, self.rules_vn1_vn3)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn2, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn2, self.vn2_fixture)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn3, self.vn1_fixture)
        self.vn3_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture_vn1_vn3, self.vn3_fixture)

        self.vm1_fixture_vn1 = self.config_vm(
            self.vn1_fixture, self.vm1_name_vn1, node_name=src_compute, image_name=image_name)

        self.vm2_fixture_vn2 = self.config_vm(
            self.vn2_fixture, self.vm2_name_vn2, node_name=dst_compute, image_name=image_name)

        self.mirror_vm_fixture_vn1 = self.config_vm(
            self.vn1_fixture, self.mirror_vm_name_vn1, node_name=analyzer_compute, image_name=image_name)
        self.mirror_vm_ip_vn1 = self.mirror_vm_fixture_vn1.get_vm_ips(self.vn1_fq_name)[0]

        self.vm2_fixture_vn1 = self.config_vm(
            self.vn1_fixture, self.vm2_name_vn1, node_name=dst_compute, image_name=image_name)
 
        self.mirror_vm_fixture_vn3 = self.config_vm(
           self.vn3_fixture, self.mirror_vm_name_vn3, node_name=analyzer_compute, image_name=image_name)
        self.mirror_vm_ip_vn3 = self.mirror_vm_fixture_vn3.get_vm_ips(self.vn3_fq_name)[0]

        self.mirror_vm_fixture_vn2 = self.config_vm(
           self.vn2_fixture, self.mirror_vm_name_vn2, node_name=analyzer_compute, image_name=image_name)
        self.mirror_vm_ip_vn3 = self.mirror_vm_fixture_vn3.get_vm_ips(self.vn3_fq_name)[0]
        self.mirror_vm_ip_vn2 = self.mirror_vm_fixture_vn2.get_vm_ips(self.vn2_fq_name)[0]

        assert self.vm1_fixture_vn1.verify_on_setup()
        assert self.vm2_fixture_vn2.verify_on_setup()
        assert self.vm2_fixture_vn1.verify_on_setup()
        assert self.mirror_vm_fixture_vn1.verify_on_setup()
        assert self.mirror_vm_fixture_vn3.verify_on_setup()
        assert self.mirror_vm_fixture_vn2.verify_on_setup()

        self.nova_h.wait_till_vm_is_up(self.vm1_fixture_vn1.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture_vn2.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.vm2_fixture_vn1.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.mirror_vm_fixture_vn1.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.mirror_vm_fixture_vn3.vm_obj)
        self.nova_h.wait_till_vm_is_up(self.mirror_vm_fixture_vn2.vm_obj)

        result, msg = self.validate_vn(
            self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(
            self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg

        self.logger.info("Verify Port mirroring when src vm in vn1, mirror vm in vn1 and dst vm in vn2..")
        if not self._verify_intf_mirroring(self.vm1_fixture_vn1, self.vm2_fixture_vn2, self.mirror_vm_fixture_vn1, \
                self.vn1_fq_name, self.vn2_fq_name, self.vn1_fq_name,
                self.mirror_vm_ip_vn1, self.analyzer_name_vn1, self.routing_instance_vn1) :
            result = result and False

        self.logger.info("Verify Port mirroring when src vm in vn1, mirror vm in vn3, and dst vm in vn2")
        if not self._verify_intf_mirroring(self.vm1_fixture_vn1, self.vm2_fixture_vn2, self.mirror_vm_fixture_vn3, \
                self.vn1_fq_name, self.vn2_fq_name, self.vn3_fq_name,
                self.mirror_vm_ip_vn3, self.analyzer_name_vn3, self.routing_instance_vn3) :
            result = result and False

        self.logger.info("Verify Port mirroring when src vm, dst vm and mirror vm all are in vn1")
        if not self._verify_intf_mirroring(self.vm1_fixture_vn1, self.vm2_fixture_vn1, self.mirror_vm_fixture_vn1, \
                self.vn1_fq_name, self.vn1_fq_name, self.vn1_fq_name,
                self.mirror_vm_ip_vn1, self.analyzer_name_vn1, self.routing_instance_vn1) :
            result = result and False

        self.logger.info("Verify Port mirroring when src vm in vn1, dst vm in vn2 and mirror vm in vn2")
        if not self._verify_intf_mirroring(self.vm1_fixture_vn1, self.vm2_fixture_vn2, self.mirror_vm_fixture_vn2, \
                self.vn1_fq_name, self.vn2_fq_name, self.vn2_fq_name,
                self.mirror_vm_ip_vn2, self.analyzer_name_vn2, self.routing_instance_vn2) :
            result = result and False
 
        return result

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
        if not self.verify_mirroring(None, src_vm_fixture, dst_vm_fixture, mirror_vm_fixture):
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
            mirror_to = MirrorActionType(analyzer_name, None, analyzer_ip_address, routing_instance, udp_port)
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
