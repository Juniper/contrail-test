from common.dsnat.base import BaseDSNAT
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from security_group import SecurityGroupFixture
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds
from test import attr

class TestDSNAT(BaseDSNAT):

    @attr(type=['sanity'])
    @preposttest_wrapper
    def test_dsnat_basic(self):
        '''
            create a VN and enable fabric SNAT
            launch two VMs in that VN
            verify ping between the VN and ping to the external IP
            disable fabric SNAT
            verify that the ping the external IP fails
        '''

        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn_fixture = self.create_vn_enable_fabric_snat()

        test_vm1 = self.create_vm(vn_fixture, get_random_name('test_vm1'),
                                 image_name='ubuntu')
        test_vm2 = self.create_vm(vn_fixture, get_random_name('test_vm2'),
                                 image_name='ubuntu')
        assert test_vm1.wait_till_vm_is_up()
        assert test_vm2.wait_till_vm_is_up()
        
        assert test_vm1.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)
        assert test_vm2.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)

        assert test_vm1.ping_with_certainty(test_vm2.vm_ip)
        #with DSNAT enabled on VN, verify the ping to the external IP
        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        assert test_vm1.ping_with_certainty(cfgm_ip)

        self.logger.info("disable fabric SNAT, and verify the ping to the external IP and inter VN")
        self.vnc_h.set_fabric_snat(vn_fixture.uuid, False)
        assert vn_fixture.verify_routing_instance_snat()
        assert not test_vm1.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name), (
            'FIP list of VMI expected to be empty')

        assert test_vm1.ping_with_certainty(test_vm2.vm_ip)
        assert test_vm1.ping_with_certainty(cfgm_ip,expectation=False)


    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_with_different_forwarding_mode(self):
        '''
           Create a VN, and enable fabric SNAT
           Launch two VMs on VN, in such a way that two VMs on different compute nodes
           set the forwarding mode of the  VN from default to l2 or l3 or l2_l3
           And verify the ping  with Jumbo packets to both inter VM IP and Fabric IP
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture, node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture, node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        forwarding_modes = ['l3', 'l2_l3']
        for mode in forwarding_modes:
            #set VN forwarding mode  and verify
            self.set_vn_forwarding_mode(vn1_fixture, forwarding_mode=mode)

            assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip, size='2000'), (
                'Ping failed between VNs')

            assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_node_data_ip), (
                'Ping failed to fabric IP, VM2 node ip')


    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_with_sg(self):
        '''
            create a VN and enable fabric SNAT
            launch two VMs in that VN
            configure a security group with rule to allow only TCP and apply it to VM1 VMI
            verify that the ping to the external IP and between VM fails
            apply default sg to VM1
            verify that the both ping succeeds
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        self.logger.info("Launch VM on different compute nodes")
        test_vm1 = self.create_vm(vn_fixture, get_random_name('test_vm1'),
                                 image_name='ubuntu',
                                 node_name=vm1_node_name)
        test_vm2 = self.create_vm(vn_fixture, get_random_name('test_vm2'),
                                 image_name='ubuntu',
                                 node_name=vm2_node_name)

        assert test_vm1.wait_till_vm_is_up()
        assert test_vm2.wait_till_vm_is_up()
        
        assert test_vm1.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)
        assert test_vm2.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)

        # Get the default security group object 
        default_sg = self.get_default_sg(connections=self.connections)

        self.logger.info("Create a security group with rule to allow only TCP")
        self.sg_allow_tcp = 'sec_group_allow_tcp' + '_' + get_random_name()
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_fixture = self.create_security_group(connections = self.connections,
            name=self.sg_allow_tcp, rules = rule)

        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg

        self.logger.info("Apply the same to the VM1 and verify the ping fails")
        self.vnc_h.set_security_group(test_vm1.uuid, [secgrp_fixture.uuid])

        assert test_vm1.ping_with_certainty(test_vm2.vm_ip, expectation=False)
        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        assert test_vm1.ping_with_certainty(cfgm_ip,expectation=False)

        self.logger.info("Apply the default security group and verify ping works again")
        self.vnc_h.set_security_group(test_vm1.uuid, [default_sg.get_sg_id()])
        assert test_vm1.ping_with_certainty(test_vm2.vm_ip)
        assert test_vm1.ping_with_certainty(cfgm_ip)


    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_with_policy(self):
        '''
           Create two VNs , and enable fabric SNAT on both of them
           Launch two VMs , one on each VN, in such a way that two VMs on different compute nodes
           configure allow ICMP policy between the VNs, and verify the ping between VN
           Update the same policy to deny ICMP and verify ping between VN fails
           configure allow TCP policy between the VN1 and ip-fabric
           verify the ping beteen the VNs and VN1 and ip-fabric
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()
        vn2_fixture = self.create_vn_enable_fabric_snat()

        policy_name = get_random_name('test-dsnat-policy')
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_fixture.vn_name,
                'dest_network': vn2_fixture.vn_name,
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'tcp',
                'source_network': vn1_fixture.vn_name,
                'dest_network': vn2_fixture.vn_name,
            },
        ]

        self.logger.info("Create policy to allow ICMP between VN1 and VN2")
        policy_fixture = self.setup_policy_between_vns(vn1_fixture,
            vn2_fixture, rules)

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        vm1_fixture = self.create_vm(vn1_fixture, node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn2_fixture, node_name=vm2_node_name)

        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn2_fixture.vn_fq_name)

        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip), (
            'Ping failed between VNs with allow-policy')

        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        assert vm1_fixture.ping_with_certainty(cfgm_ip), (
            'Ping failed to external IP with allow-policy')

        # Deny the same traffic and verify
        policy_id = policy_fixture.get_id()
        rules[0]['simple_action'] = 'deny'
        policy_entries = policy_fixture.get_entries()
        policy_entries.policy_rule[0].action_list.simple_action = 'deny'
        p_rules = policy_entries
        policy_fixture.update_policy(policy_id, p_rules)
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
            expectation=False), ('Ping passed between VNs with deny-policy')
        assert vm1_fixture.ping_with_certainty(cfgm_ip), (
            'Ping failed to external IP with allow-policy')

        #Remove the policy
        self.detach_policy_from_vn(policy_fixture, vn1_fixture)
        self.detach_policy_from_vn(policy_fixture, vn2_fixture)

        #Get the ip-fabric object
        fabric_vn = self.get_ip_fabric_vn_fixture()

        #create the policy between VN1 and ip-fabric and verify the ping to the external IP
        action_list={}
        action_list['simple_action'] = 'pass'
        rules = [
              {
                  'direction':'<>',
                  'action_list': action_list,
                  'protocol':'tcp',
                  'source_network':vn1_fixture.vn_name,
                  'dest_network':fabric_vn.vn_fq_name,
                  'src_ports':'any',
                  'dst_ports':'any'
              },
              {
                  'direction':'<>',
                  'action_list': {'simple_action': 'deny'},
                  'protocol':'icmp',
                  'source_network':vn1_fixture.vn_name,
                  'dest_network':fabric_vn.vn_fq_name,
                  'src_ports':'any',
                  'dst_ports':'any'
              },
        ]
        vn_policy_fix = self.create_policy_attach_to_vn(vn1_fixture, rules)
        vn1_fixture.update_vn_object()
        policy_fix = self.vnc_h.network_policy_read(
            id=vn1_fixture.policy_objs[0]['policy']['id'])
        policy_fix.policy_fq_name = policy_fix.fq_name
        policy_fix.policy_name = policy_fix.name

        self.attach_policy_to_vn(policy_fix, fabric_vn)
        assert vm1_fixture.ping_with_certainty(self.inputs.cfgm_ip, expectation=False), (
            'Ping passed to external IP with allow-tcp-policy')


    @skip_because(min_nodes=2)
    @attr(type=['sanity'])
    @preposttest_wrapper
    def test_dsnat_bug_1749695(self):
        '''
           Testcase to verify the bug 1749695
           create test VN , associate a policy to allow all traffic between VN and ip fabric
           associate the policy to the test VN and fabric VN
           set the test VN fabric mode as l3
           verify the ping succeeds for intra VN and to the fabric IP
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        vm1_fixture = self.create_vm(vn1_fixture, node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture, node_name=vm2_node_name)

        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        #Get the ip-fabric object
        fabric_vn = self.get_ip_fabric_vn_fixture()

        #create the policy between VN1 and ip-fabric and verify the ping to the external IP
        action_list={}
        action_list['simple_action'] = 'pass'
        rules = [
              {
                  'direction':'<>',
                  'action_list': action_list,
                  'protocol':'any',
                  'source_network':vn1_fixture.vn_name,
                  'dest_network':fabric_vn.vn_fq_name,
                  'src_ports':'any',
                  'dst_ports':'any'
              },
        ]
        vn_policy_fix = self.create_policy_attach_to_vn(vn1_fixture, rules)
        vn1_fixture.update_vn_object()
        policy_fix = self.vnc_h.network_policy_read(
            id=vn1_fixture.policy_objs[0]['policy']['id'])
        policy_fix.policy_fq_name = policy_fix.fq_name
        policy_fix.policy_name = policy_fix.name

        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        self.attach_policy_to_vn(policy_fix, fabric_vn)
        assert vm1_fixture.ping_with_certainty(cfgm_ip), (
            'Ping to external IP failed with allow-any-policy')

        #set VN forwarding mode as l3 and verify
        self.set_vn_forwarding_mode(vn1_fixture, forwarding_mode='l3')

        assert vm1_fixture.ping_with_certainty(cfgm_ip), (
            'Ping to fabric IP failed with allow-any-policy')

        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip), (
            'Ping to VM IP, %s,  passed with allow-any-policy' %vm2_fixture.vm_ip)


    @preposttest_wrapper
    def test_dsnat_with_floating_ip(self):
        '''
           Test to verify the associated floating ip is higher precedence than the fabric ip
           create a test VN, enable SNAT and launch a VM
           create a floating ip and associate the VM created on test VN
           launch a VM on floating network,
           configure interface route table for the external ip prefix and bind it to the 
                VMI of VM launched in floating network
           Verify ping from test VM  to the external IP fails
           unbind the interface table from the VMI of VM launched in floating network
           Verify ping from test VM to the external IP succeeds
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn_fixture = self.create_vn_enable_fabric_snat()

        self.logger.info("Launch a test vm on a fabric SNAT enabled VN")
        test_vm1 = self.create_vm(vn_fixture, get_random_name('test_vm1'),
                                 image_name='ubuntu')
        assert test_vm1.wait_till_vm_is_up()

        self.logger.info("Create a floating ip virtual network")
        fvn_name = get_random_name('dsnat_fvn')
        fvn_subnets = [get_random_cidr()]
        floating_vn = self.create_vn(fvn_name, fvn_subnets)
        
        self.logger.info("Launch a VM on the floating virtual network")
        fvn_vm1 = self.create_vm(floating_vn, get_random_name('dsnat_fvm'),
                                 image_name='ubuntu')
        assert fvn_vm1.wait_till_vm_is_up()

        fip_fixture = self.create_floatingip_pool(floating_vn, get_random_name('dsnat_fip'))

        self.logger.info("Associate a FIP to the test VM VMI")
        fip_id = fip_fixture.create_and_assoc_fip(
            floating_vn.vn_id, test_vm1.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        assert test_vm1.verify_fabric_ip_as_floating_ip(vn_fixture.vn_fq_name)
    
        self.logger.info("Create interface router table with external ip prefix,\
            and bind the route table to the VM created on the floating network")
        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        prefixes = []
        prefixes.append(cfgm_ip+'/32')
        intf_route_table_obj = self.vnc_h.create_interface_route_table(\
                               get_random_name('dsnat_rt'),
                               parent_obj=self.project.project_obj,
                               prefixes=prefixes)
        self.vnc_h.bind_vmi_to_interface_route_table(fvn_vm1.vmi_ids[floating_vn.vn_fq_name],
                                                     intf_route_table_obj)

        self.logger.info("Verifies that the floating ip preffered and the packet \
            hits the static route that is created by interface route table")
        assert test_vm1.ping_with_certainty(cfgm_ip, expectation=False)

        self.logger.info("Unbind the route table from the VMI of VM created on the floating network")
        self.vnc_h.unbind_vmi_from_interface_route_table(fvn_vm1.vmi_ids[floating_vn.vn_fq_name],
                                                     intf_route_table_obj)

        self.logger.info("Verifies the ping to the external IP routes through the fabric IP")
        assert test_vm1.ping_with_certainty(cfgm_ip)

    @preposttest_wrapper
    def test_dsnat_through_floatingvn(self):
        '''
            create a VN, say FVN, for floating ip pool , enable SNAT and create a floating ip
            create test VN, say tvn and a launch a VM
            associate the floating IP to the test VM
            verify the ping to the Fabric IP or external IP from test VM
        '''
        self.logger.info("Create VN, for floating ip pool and enable SNAT")
        fvn_fixture = self.create_vn_enable_fabric_snat()

        self.logger.info("Launch a vm on a fabric SNAT enabled VN")
        fvn_vm1 = self.create_vm(fvn_fixture, get_random_name('fvn_vm1'),
                                 image_name='ubuntu')

        self.logger.info("Create a floating ip from the same VN")
        fip_fixture = self.create_floatingip_pool(fvn_fixture, get_random_name('dsnat_fip'))

        self.logger.info("Create test VN")
        tvn_name = get_random_name('dsnat_tvn')
        tvn_subnets = [get_random_cidr()]
        tvn_fix = self.create_vn(tvn_name, tvn_subnets)
        assert tvn_fix.verify_on_setup()

        self.logger.info("Launch a VM on the test virtual network")
        test_vm1 = self.create_vm(tvn_fix, tvn_name,
                                 image_name='ubuntu')
        assert fvn_vm1.wait_till_vm_is_up()
        assert test_vm1.wait_till_vm_is_up()

        self.logger.info("Associate a FIP to the test VM VMI")
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, test_vm1.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        self.logger.info("Verifies the ping to the external IP \
             from floating VN, routes through the fabric IP")
        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        assert fvn_vm1.ping_with_certainty(cfgm_ip)

        self.logger.info("Verifies the ping to the external IP \
             from test VM, routes through the floating VN")
        assert test_vm1.ping_with_certainty(cfgm_ip)

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_dsnat_with_secondary_ip(self):
        '''
           Launch two VMs, in a VN, enabled with SNAT
           config AAP in active-active mode between the VMs
           verify the ping to fabric IP, with secondary IP as source
        '''
        self.logger.info("Create VN, enable FABRIC SNAT and verify its routing instance")
        vn1_fixture = self.create_vn_enable_fabric_snat()

        vm1_node_name = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm2_node_name = self.inputs.host_data[self.inputs.compute_ips[1]]['name']

        #Launch VM on different compute nodes
        vm1_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm1'),
                                     image_name='cirros',
                                     node_name=vm1_node_name)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     get_random_name('dsnat-vm2'),
                                     image_name='cirros',
                                     node_name=vm2_node_name)

        #Verify VM is Active
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)
        assert vm2_fixture.verify_fabric_ip_as_floating_ip(vn1_fixture.vn_fq_name)

        self.logger.info('Configure AAP on both the VMs')
        vIP = self.configure_aap_for_port_list(vn1_fixture, [vm1_fixture, vm2_fixture])

        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        self.logger.info('Ping fabric IP with source IP as %s' %vIP)
        cfgm_ip = self.inputs.get_host_data_ip(self.inputs.cfgm_names[0])
        assert vm1_fixture.ping_with_certainty(other_opt='-I '+vIP, ip=cfgm_ip),\
            ('Ping failed from vIP to fabric IP')
