from builtins import str
from builtins import range
import test
import uuid
import copy
import random
from netaddr import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *

class TestSPStyleFabric(BaseFabricTest):
    enterprise_style = False
    @preposttest_wrapper
    def test_fabric_intravn_basic(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='ubuntu')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, tor_port_vlan_tag=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @preposttest_wrapper
    def test_fabric_intravn_tagged(self):
        '''Validate ping between a KVM VM and a tagged BMS
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='ubuntu')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms, vlan_id=10,
                vn_fixture=vn))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    def _validate_pre_created_vpg(self, bms_type):
        if bms_type != 'single_interface':
            target_node = random.choice(self.get_bms_nodes(bms_type=bms_type))
            interfaces = self.inputs.bms_data[target_node]['interfaces']
        else:
            target_node = random.choice(self.get_bms_nodes())
            interfaces = self.inputs.bms_data[target_node]['interfaces'][:1]
        other_nodes = set(self.get_bms_nodes()) - set([target_node])
        vn = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn, vn2])
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        vpg = self.create_vpg(interfaces)
        bms = self.create_bms(bms_name=target_node, interfaces=interfaces,
                              port_group_name=vpg.name, vlan_id=10,
                              vn_fixture=vn)
        instances = [bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=list(other_nodes)[0],
                tor_port_vlan_tag=10, vn_fixture=vn)
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)
        bms_2 = self.create_bms(bms_name=target_node, vlan_id=20,
            bond_name=bms.bond_name, interfaces=interfaces,
            port_group_name=bms.port_group_name, vn_fixture=vn2)
        instances.append(bms_2)
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @preposttest_wrapper
    def test_multihoming_pre_created_vpg(self):
        self._validate_pre_created_vpg(bms_type='multi_homing')

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_lag_pre_created_vpg(self):
        self._validate_pre_created_vpg(bms_type='link_aggregation')

    @preposttest_wrapper
    def test_single_interface_pre_created_vpg(self):
        self._validate_pre_created_vpg(bms_type='single_interface')

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_bridge_domain_on_leaf_tagged(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn1, vn2])
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
               vlan_id=10, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)
        new_ip = str(IPAddress(IPNetwork(vn1.get_cidrs()[0]).value + 8))
        bms2.assign_static_ip(new_ip, flush=True)
        self.do_ping_test(bms1, new_ip, expectation=False)

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_different_vlan_same_vn_same_tor(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=20, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_both_tagged_and_untagged_same_vn_same_tor(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn1, vn2])
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               tor_port_vlan_tag=20, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)
        bms1_2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
                tor_port_vlan_tag=30, interfaces=bms1_intf,
                bond_name=bms1.bond_name,
                port_group_name=bms1.port_group_name)
        self.do_ping_mesh([bms1, bms2, bms1_2])

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_same_vn_same_vpg_different_vlan(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
        bms1_2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=20, bond_name=bms1.bond_name,
               interfaces=bms1_intf,
               port_group_name=bms1.port_group_name)
        self.do_ping_test(bms1, bms1_2.bms_ip, expectation=False)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)
        self.do_ping_test(bms2, bms1_2.bms_ip)
        self.do_ping_test(bms1, bms1_2.bms_ip, expectation=False)

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_same_vn_as_tagged_and_untagged_across_vpg(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               tor_port_vlan_tag=10, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)
        self.perform_cleanup(bms2)
        msg = 'BMS creation with different tagged and untagged vlans' + \
              ' should have'
        try:
            bms2 = self.create_bms(bms_name=bms, vn_fixture=vn1,
                   tor_port_vlan_tag=20, interfaces=bms2_intf)
            assert self.enterprise_style == False, msg + ' failed'
            self.do_ping_test(bms1, bms2.bms_ip)
        except BadRequest as e:
            assert self.enterprise_style == True, msg + ' passed'

    @preposttest_wrapper
    def test_restart_device_manager(self):
        bms_nodes = self.get_bms_nodes()
        vn1 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_nodes[0],
               tor_port_vlan_tag=10, vn_fixture=vn1)
        vm1.wait_till_vm_is_up()
        self.do_ping_test(bms1, vm1.vm_ip)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.sleep(90) #Wait to make sure if any config push happens to complete
        self.do_ping_test(bms1, vm1.vm_ip)
        if len(bms_nodes) > 1:
            bms2 = self.create_bms(bms_name=bms_nodes[1],
                tor_port_vlan_tag=10, vn_fixture=vn1)
            self.do_ping_mesh([bms1, bms2, vm1])

class TestFabricOverlay(TestSPStyleFabric):
    enterprise_style = True
    def test_different_vlan_same_vn_same_tor(self):
        raise self.skipTest('Feature not supported with EnterpriseStyle config')

    def test_bridge_domain_on_leaf_tagged(self):
        raise self.skipTest('Feature not supported with EnterpriseStyle config')

    def test_both_tagged_and_untagged_same_vn_same_tor(self):
        raise self.skipTest('Feature not supported with EnterpriseStyle config')

    def test_same_vn_same_vpg_different_vlan(self):
        raise self.skipTest('Feature not supported with EnterpriseStyle config')

    @preposttest_wrapper
    def test_vdns(self):
        bms_node = random.choice(self.get_bms_nodes())
        vdns = self.create_vdns()
        ipam = self.create_ipam(vdns_fixture=vdns)
        vn = self.create_vn(ipam_fq_name=ipam.fq_name)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_node,
            vn_fixture=vn, tor_port_vlan_tag=10)
        vm1.wait_till_vm_is_up()
        assert bms1.ping(vm1.vm_name)

    # Commenting this test till CEM-3959, running the same messes DM
    @skip_because(bms=2)
    @preposttest_wrapper
    def itest_bms_movement_1(self):
        bms_nodes = self.get_bms_nodes()
        first_node = bms_nodes[0]
        second_node = bms_nodes[1]
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        node1_bms1 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh([node1_bms1, vm1])
        node1_bms1.update_vmi(self.inputs.bms_data[second_node]['interfaces'],
                         port_group_name=None)
        self.do_ping_test(node1_bms1, vm1.vm_ip, expectation=False)
        node2_bms1 = self.create_bms(bms_name=second_node,
                         port_fixture=node1_bms1.port_fixture)
        self.do_ping_test(node2_bms1, vm1.vm_ip)
        node1_bms1.cleanup_bms()
        node1_bms2 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn)
        self.do_ping_mesh([vm1, node1_bms2, node2_bms1])
        node1_bms3 = self.create_bms(bms_name=first_node, vlan_id=20,
                         vn_fixture=vn,
                         port_group_name=node1_bms2.port_group_name)
        self.do_ping_mesh([vm1, node1_bms2, node1_bms3, node2_bms1])
        node1_bms3.update_vmi(self.inputs.bms_data[second_node]['interfaces'],
                         port_group_name=node2_bms1.port_group_name)
        self.do_ping_test(node1_bms3, vm1.vm_ip, expectation=False)
        node1_bms3.cleanup_bms()
        node2_bms2 = self.create_bms(bms_name=second_node,
                         port_fixture=node1_bms3.port_fixture)
        self.do_ping_mesh([vm1, node1_bms2, node2_bms2, node2_bms1])

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_bms_movement_2(self):
        bms_nodes = self.get_bms_nodes()
        first_node = bms_nodes[0]
        second_node = bms_nodes[1]
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        node1_bms1 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh([node1_bms1, vm1])

        vpg_fqname = node1_bms1.port_fixture.get_vpg_fqname()
        vpg_obj = self.vnc_h.read_virtual_port_group(fq_name=vpg_fqname)
        vpg_obj.del_virtual_machine_interface(
            node1_bms1.port_fixture.vmi_obj)
        self.vnc_h.update_obj(vpg_obj)
        self.vnc_h.delete_virtual_port_group(fq_name=vpg_fqname)

        node1_bms1.update_vmi(self.inputs.bms_data[second_node]['interfaces'],
                         port_group_name=None)
        self.do_ping_test(node1_bms1, vm1.vm_ip, expectation=False)
        node2_bms1 = self.create_bms(bms_name=second_node, vn_fixture=vn,
            tor_port_vlan_tag=40, port_fixture=node1_bms1.port_fixture)
        self.do_ping_test(node2_bms1, vm1.vm_ip)
        node1_bms1.cleanup_bms()
        node1_bms2 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn)
        self.do_ping_mesh([vm1, node1_bms2, node2_bms1])

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_with_multiple_subnets(self):
        ''' Create a VN with two /28 subnets
            Create 8 VMIs on the VN so that 1st subnet IPs are exhausted
            Add lifs with 6th and 7th VMIs
            Validate that the BMSs get IP from 2nd subnet and ping passes
        '''
        vn_subnets = [get_random_cidr('28'), get_random_cidr('28')]
        vn = self.create_vn(vn_subnets=vn_subnets)

        self.create_logical_router([vn])
        bms_data = self.get_bms_nodes()
        bms1_fixture = self.create_bms(bms_name=bms_data[0],
            tor_port_vlan_tag=10, vn_fixture=vn)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for i in range(0, 4):
            port_fixture = self.setup_vmi(vn.uuid)
            if port_fixture.get_ip_addresses()[0] in IPNetwork(vn_subnets[1]):
                self.perform_cleanup(port_fixture)
                break
        bms2_fixture = self.create_bms(bms_name=bms_data[1],
            tor_port_vlan_tag=10, vn_fixture=vn)
        vm2 = self.create_vm(vn_fixture=vn, image_name='cirros')

        vm2.wait_till_vm_is_up()
        self.do_ping_mesh([bms1_fixture, bms2_fixture, vm1, vm2])
    # end test_with_multiple_subnets

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_remove_add_instance(self):
        '''Validate removal and addition of VMI with different vlan tags
        Add a VMI(for BMS) to a ToR lif
        Check if BMS connectivity is fine
        Remove the VMI from the lif
        Check if BMS connectivity is broken
        Add the VMI back again
        Check if BMS connectivity is restored
        '''
        vn = self.create_vn(disable_dns=True)
        bms_data = self.get_bms_nodes()

        bms1_fixture = self.create_bms(bms_name=bms_data[0],
            tor_port_vlan_tag=10, vn_fixture=vn)
        bms2_fixture = self.create_bms(bms_name=bms_data[1],
            tor_port_vlan_tag=10, vn_fixture=vn)

        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip)

        bms1_fixture.delete_vmi()
        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip, expectation=False)
        bms1_fixture.cleanup_bms()

        bms1_fixture.vlan_id = 10
        bms1_fixture.setUp()

        status, msg = bms1_fixture.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        bms1_fixture.verify_on_setup()
        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip)
    # end test_remove_add_instance

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_lag_add_remove_interface(self):
        nodes = self.get_bms_nodes(bms_type='link_aggregation')
        lag_node = nodes[0]
        other_nodes = list(set(self.get_bms_nodes()) - set([lag_node]))
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        lag_bms = self.create_bms(bms_name=lag_node,
            tor_port_vlan_tag=10, vn_fixture=vn)
        instances = [lag_bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=other_nodes[0],
            tor_port_vlan_tag=10, vn_fixture=vn)
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)

        interface_to_detach = self.inputs.bms_data[lag_node]['interfaces'][0]
        other_interfaces = self.inputs.bms_data[lag_node]['interfaces'][1:]
        lag_bms.detach_physical_interface([interface_to_detach])
        lag_bms.is_lacp_up([interface_to_detach], expectation=False)
        lag_bms.is_lacp_up(other_interfaces, expectation=True)
        lag_bms.remove_interface_from_bonding([interface_to_detach])
        self.do_ping_mesh(instances)

        # Remove all the interfaces except the 1st index
        if len(other_interfaces) > 1:
            rest_interfaces = other_interfaces[1:]
            lag_bms.detach_physical_interface(rest_interfaces)
            lag_bms.is_lacp_up(other_interfaces,
                              expectation=False)
            lag_bms.cleanup_bms(other_interfaces)
            lag_bms.setup_bms(other_interfaces[:1])
            status, msg = lag_bms.run_dhclient()
            assert status, 'DHCP failed to fetch address'
            self.do_ping_mesh(instances)

        lag_bms.attach_physical_interface([interface_to_detach])
        lag_bms.cleanup_bms(other_interfaces[:1])
        lag_bms.setup_bms(self.inputs.bms_data[lag_node]['interfaces'])
        lag_bms.is_lacp_up()
        status, msg = lag_bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @preposttest_wrapper
    def test_multihoming_add_remove_interface(self):
        mh_nodes = self.get_bms_nodes(bms_type='multi_homing')
        mh_node = mh_nodes[0]
        # Check if we have BMS which has both lag and mh
        lag_nodes = self.get_bms_nodes(bms_type='link_aggregation')
        mh_lag_nodes = set(mh_nodes).intersection(set(lag_nodes))
        if mh_lag_nodes:
            mh_node = list(mh_lag_nodes)[0]

        other_nodes = list(set(self.get_bms_nodes()) - set([mh_node]))
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        mh_bms = self.create_bms(bms_name=mh_node, vlan_id=10, vn_fixture=vn)
        instances = [mh_bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=other_nodes[0],
                vlan_id=10, vn_fixture=vn)
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)

        interface_to_detach = self.inputs.bms_data[mh_node]['interfaces'][0]
        other_interfaces = self.inputs.bms_data[mh_node]['interfaces'][1:]
        mh_bms.detach_physical_interface([interface_to_detach])
        mh_bms.is_lacp_up([interface_to_detach], expectation=False)
        mh_bms.is_lacp_up(other_interfaces, expectation=True)
        mh_bms.remove_interface_from_bonding([interface_to_detach])
        self.do_ping_mesh(instances)

        if len(other_interfaces) > 1:
            # Remove all the interfaces except the 1st index
            rest_interfaces = other_interfaces[1:]
            mh_bms.detach_physical_interface(rest_interfaces)
            mh_bms.is_lacp_up(other_interfaces,
                              expectation=False)
            mh_bms.cleanup_bms(other_interfaces)
            mh_bms.setup_bms(other_interfaces[:1])
            status, msg = mh_bms.run_dhclient()
            assert status, 'DHCP failed to fetch address'
            self.do_ping_mesh(instances)

        mh_bms.attach_physical_interface([interface_to_detach])
        mh_bms.cleanup_bms(other_interfaces[:1])
        mh_bms.setup_bms(self.inputs.bms_data[mh_node]['interfaces'])
        mh_bms.is_lacp_up()
        status, msg = mh_bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    def _validate_multiple_vlan(self, bms_type):
        if bms_type != 'single_interface':
            target_node = random.choice(self.get_bms_nodes(bms_type=bms_type))
            interfaces = self.inputs.bms_data[target_node]['interfaces']
        else:
            target_node = random.choice(self.get_bms_nodes())
            interfaces = self.inputs.bms_data[target_node]['interfaces'][:1]
        other_nodes = set(self.get_bms_nodes()) - set([target_node])
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        vn3 = self.create_vn()
        self.create_logical_router([vn1, vn2, vn3])
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        bms = self.create_bms(bms_name=target_node, interfaces=interfaces,
                              vlan_id=10, vn_fixture=vn1)
        instances = [bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=list(other_nodes)[0],
                vlan_id=10, vn_fixture=vn1)
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)
        bms_2 = self.create_bms(bms_name=target_node, vlan_id=20,
            bond_name=bms.bond_name, interfaces=interfaces,
            port_group_name=bms.port_group_name, vn_fixture=vn2)
        instances.append(bms_2)
        self.do_ping_mesh(instances)
        bms_3 = self.create_bms(bms_name=target_node,
            tor_port_vlan_tag=40,
            bond_name=bms.bond_name, interfaces=interfaces,
            port_group_name=bms.port_group_name, vn_fixture=vn3)
        instances.append(bms_3)
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @preposttest_wrapper
    def test_multihoming_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='multi_homing')

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_lag_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='link_aggregation')

    @preposttest_wrapper
    def test_single_interface_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='single_interface')

    @preposttest_wrapper
    def test_update_vlan_id(self):
        target_node = random.choice(self.get_bms_nodes())
        other_nodes = set(self.get_bms_nodes()) - set([target_node])
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms = self.create_bms(bms_name=target_node, vlan_id=10, vn_fixture=vn)
        instances = [bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=list(other_nodes)[0],
                tor_port_vlan_tag=20, vn_fixture=vn)
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)
        bms.update_vlan_id(20)
        self.sleep(60)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)
        bms.update_vlan_id(None)
        self.sleep(60)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)
        bms.update_vlan_id(30)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_bridge_domain_on_leaf_untagged(self):
        bms = random.choice(self.get_bms_nodes(bms_type='link_aggregation'))
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn1, vn2])
        bms1_intf = self.inputs.bms_data[bms]['interfaces'][:1]
        bms2_intf = self.inputs.bms_data[bms]['interfaces'][1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               tor_port_vlan_tag=10, interfaces=bms1_intf)
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
               tor_port_vlan_tag=20, interfaces=bms2_intf)
        self.do_ping_test(bms1, bms2.bms_ip)
        new_ip = str(IPAddress(IPNetwork(vn1.get_cidrs()[0]).value + 8))
        bms2.assign_static_ip(new_ip, flush=True)
        self.do_ping_test(bms1, new_ip, expectation=False)

    @preposttest_wrapper
    def test_restart_api_server(self):
        bms_nodes = self.get_bms_nodes()
        vn1 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_nodes[0],
               tor_port_vlan_tag=10, vn_fixture=vn1)
        vm1.wait_till_vm_is_up()
        self.do_ping_test(bms1, vm1.vm_ip)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        self.sleep(90) #Wait to make sure if any config push happens to complete
        self.do_ping_test(bms1, vm1.vm_ip)
        if len(bms_nodes) > 1:
            bms2 = self.create_bms(bms_name=bms_nodes[1],
                tor_port_vlan_tag=10, vn_fixture=vn1)
            self.do_ping_mesh([bms1, bms2, vm1])
        #ToDo: Need to add test to stop couple of api-servers and validate DM
        #can work with just one and then start the rest and stop the active
        #cfgm. This would need changes to the test infra since the cfgm_ip
        #would become unreachable.

    @preposttest_wrapper
    def itest_restart_rabbitmq(self):
        bms_nodes = self.get_bms_nodes()
        vn1 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_nodes[0],
               tor_port_vlan_tag=10, vn_fixture=vn1)
        vm1.wait_till_vm_is_up()
        self.do_ping_test(bms1, vm1.vm_ip)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'config-rabbitmq')
        self.sleep(90) #Wait to make sure if any config push happens to complete
        self.do_ping_test(bms1, vm1.vm_ip)
        if len(bms_nodes) > 1:
            bms2 = self.create_bms(bms_name=bms_nodes[1],
                tor_port_vlan_tag=10, vn_fixture=vn1)
            self.do_ping_mesh([bms1, bms2, vm1])

    @preposttest_wrapper
    def test_csn_ha(self):
        bms_nodes = self.get_bms_nodes()
        csns = self.inputs.get_csn()
        self.addCleanup(self.inputs.start_container, csns, 'agent')
        vn1 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_nodes[0],
               tor_port_vlan_tag=10, vn_fixture=vn1)
        vm1.wait_till_vm_is_up()
        self.do_ping_test(bms1, vm1.vm_ip)
        self.inputs.stop_container([csns[0]], 'agent')
        self.do_ping_test(bms1, vm1.vm_ip)
        assert bms1.run_dhclient(expectation=len(csns) > 1)
        if len(csns) > 1:
            self.inputs.stop_container(csns, 'agent')
            assert bms1.run_dhclient(expectation=False)
        self.inputs.start_container([csns[0]], 'agent')
        assert bms1.run_dhclient()
        if len(bms_nodes) > 1:
            bms2 = self.create_bms(bms_name=bms_nodes[1],
               tor_port_vlan_tag=10, vn_fixture=vn1)
            self.do_ping_mesh([bms1, bms2, vm1])

    @preposttest_wrapper
    def test_negative_cases_2(self):
        vn1 = self.create_vn()
        bms_name = random.choice(self.get_bms_nodes())
        interfaces = copy.deepcopy(self.inputs.bms_data[bms_name]['interfaces'])
        try:
            interfaces[0]['tor_port'] = "xe-10/10/50"
            bms1 = self.create_bms(bms_name=bms_name, interfaces=interfaces,
                vn_fixture=vn1)
            assert False, "bms1 creation should have failed"
        except NoIdError as e:
            self.logger.info("Got NoIdError exception as expected during "
                             "creation of bms with non-existent PI")
        interfaces = copy.deepcopy(self.inputs.bms_data[bms_name]['interfaces'])
        try:
            interfaces[0]['tor'] = "ctest-qfxn"
            bms1 = self.create_bms(bms_name=bms_name, interfaces=interfaces,
                vn_fixture=vn1)
            assert False, "bms1 creation should have failed"
        except NoIdError as e:
            self.logger.info("Got NoIdError exception as expected during "
                             "creation of bms with non-existent PR")
        try:
            bms1 = self.create_bms(bms_name=bms_name,
                port_group_name="non-existing", vn_fixture=vn1)
            assert False, "bms1 creation should have failed"
        except NoIdError as e:
            self.logger.info("Got NoIdError exception as expected during "
                             "creation of bms with non-existent vpg")
        dummy_fabric = self.create_fabric()
        try:
            bms1 = self.create_bms(bms_name=bms_name,
                vn_fixture=vn1, fabric_fixture=dummy_fabric)
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of bms with wrong fabric info")

    @preposttest_wrapper
    def test_negative_cases_1(self):
        bms_nodes = self.get_bms_nodes()
        vn1 = self.create_vn()
        bms_name = bms_nodes[0]
        bms1 = self.create_bms(bms_name=bms_name,
               vlan_id=11, vn_fixture=vn1)
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        vm1.wait_till_vm_is_up()
        self.do_ping_test(bms1, vm1.vm_ip)
        try:
            bms2 = self.create_bms(bms_name=bms_name,
                bond_name=bms1.bond_name,
                vlan_id=12, vn_fixture=vn1)
            assert False, "bms2 creation should have failed"
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of second bms without vpg info")
        try:
            bms2 = self.create_bms(bms_name=bms_name,
                bond_name=bms1.bond_name, port_group_name=bms1.port_group_name,
                vlan_id=11, vn_fixture=vn1)
            assert False, "bms2 creation should have failed"
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of second bms with same vlan-id in vn")
        try:
            bms2 = self.create_bms(bms_name=bms_name,
                bond_name=bms1.bond_name, port_group_name="non-existing",
                vlan_id=13, vn_fixture=vn1)
            assert False, "bms2 creation should have failed"
        except NoIdError as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of second bms with non-existent vpg")
        try:
            dummy_vpg = self.create_vpg(bms1.interfaces)
            bms2 = self.create_bms(bms_name=bms_name,
                bond_name=bms1.bond_name,
                vlan_id=20, port_group_name=dummy_vpg.name,
                vn_fixture=vn1)
            assert False, "second vpg creation should have failed"
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of VPG with same interfaces info")
        dummy_fabric = self.create_fabric()
        try:
            bms2 = self.create_bms(bms_name=bms_name,
                bond_name=bms1.bond_name,
                port_group_name=bms1.port_group_name,
                vlan_id=30, fabric_fixture=dummy_fabric,
                vn_fixture=vn1)
            assert False, "bms2 creation should have failed"
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "creation of second bms with different fabric")

        if len(bms_nodes) > 1:
            other_bms = bms_nodes[1]
            interfaces = self.inputs.bms_data[other_bms]['interfaces']
            try:
                bms1.update_vmi(interfaces, bms1.port_group_name,
                                'non-existent')
                assert False, "bms1 update should have failed"
            except NoIdError as e:
                self.logger.info("Got BadRequest exception as expected during "
                    "update of bms1 with non-existent fabric")
            try:
                bms1.update_vmi(interfaces, bms1.port_group_name,
                                dummy_fabric.name)
                assert False, "bms1 update should have failed"
            except BadRequest as e:
                self.logger.info("Got BadRequest exception as expected during "
                    "update of bms1 with different fabric")
            other_node = self.create_bms(bms_name=other_bms, vn_fixture=vn1)
            try:
                bms1.attach_physical_interface(other_node.interfaces[:1])
                assert False, "bms1 update should have failed"
            except BadRequest as e:
                self.logger.info("Got BadRequest exception as expected during "
                    "update of bms1 with interface belonging to other bms")
            try:
                bms2 = self.create_bms(bms_name=bms_name,
                    bond_name=bms1.bond_name,
                    port_group_name=other_node.port_group_name)
                assert False, "bms2 creation should have failed"
            except BadRequest as e:
                self.logger.info("Got BadRequest exception as expected during "
                                 "creation of second bms with wrong vpg info")

        vpg_fqname = bms1.port_fixture.get_vpg_fqname()
        try:
            self.vnc_h.delete_virtual_port_group(fq_name=vpg_fqname)
            assert False, "VPG deletion should have failed"
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "deletion of vpg with VMI refs")
        self.do_ping_test(bms1, vm1.vm_ip)

        interfaces = bms1.interfaces
        bms1.attach_physical_interface(interfaces)
        self.do_ping_test(bms1, vm1.vm_ip)

        bms1.update_vmi([], bms1.port_group_name)
        self.sleep(90)
        self.do_ping_test(bms1, vm1.vm_ip)
        bms1.attach_physical_interface(interfaces)

    @skip_because(function='filter_bms_nodes', role='spine')
    @preposttest_wrapper
    def test_bms_on_spine(self):
        bms_nodes = self.get_bms_nodes(role='spine')
        leaf_bms = self.get_bms_nodes()[0]
        spine_bms = bms_nodes[0]
        devices = list()
        rb_roles = dict()
        for spine in self.spines:
            if self.is_bms_on_node(spine.name):
                devices.append(spine)
                rb_roles[spine.name] = ['CRB-Access', 'CRB-Gateway',
                                        'Route-Reflector']
        self.addCleanup(self.assign_roles, self.fabric, self.devices)
        self.assign_roles(self.fabric, devices, rb_roles=rb_roles)
        vlan = 10
        bms_fixtures = dict(); bms_vns = dict()
        vn = self.create_vn()
        for bms in bms_nodes+[leaf_bms]:
            bms_vns[bms] = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        self.create_logical_router([vn]+list(bms_vns.values()))
        sc1 = self.create_sc_profile(action='interface-shutdown',
                                     bandwidth=1, recovery_timeout=180)
        pp1 = self.create_port_profile(storm_control_profiles=[sc1.uuid])
        for bms in bms_nodes+[leaf_bms]:
            interfaces = None
            port_profiles = None
            if bms == spine_bms:
                spine_vlan = vlan
                interfaces = self.inputs.bms_data[bms]['interfaces'][:1]
                port_profiles = [pp1.uuid]
            bms_fixtures[bms] = self.create_bms(
                bms_name=bms,
                vn_fixture=bms_vns[bms],
                interfaces=interfaces,
                port_profiles=port_profiles,
                vlan_id=vlan)
            vlan = vlan + 10
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(list(bms_fixtures.values())+[vm1])
        bms_fixtures[spine_bms+'_2_'] = self.create_bms(bms_name=spine_bms,
            port_group_name=bms_fixtures[spine_bms].port_group_name,
            bond_name=bms_fixtures[spine_bms].bond_name,
            interfaces=bms_fixtures[spine_bms].interfaces,
            vn_fixture=vn, vlan_id=11)
        bms_fixtures[leaf_bms+'_2_'] = self.create_bms(bms_name=leaf_bms,
            port_group_name=bms_fixtures[leaf_bms].port_group_name,
            bond_name=bms_fixtures[leaf_bms].bond_name,
            vn_fixture=bms_vns[spine_bms], vlan_id=spine_vlan)
        self.do_ping_mesh(list(bms_fixtures.values())+[vm1])
        prouter = self.get_associated_prouters(spine_bms,
                                 bms_fixtures[spine_bms].interfaces)[0]
        assert sc1.validate_config_pushed([prouter],
                                          bms_fixtures[spine_bms].interfaces)
        assert prouter.validate_interfaces_status(
               [bms_fixtures[spine_bms].interfaces[0]['tor_port']], status='up')
        pid = bms_fixtures[spine_bms].send_broadcast_traffic()
        assert prouter.validate_interfaces_status(
               [bms_fixtures[spine_bms].interfaces[0]['tor_port']], 'down')
        bms_fixtures[spine_bms].stop_broadcast_traffic(pid)

    @preposttest_wrapper
    def test_storm_control_profile_w_traffic(self, rb_role=None):
        bms_fixtures = list()
        vn = self.create_vn()
        bms_nodes = self.get_bms_nodes(rb_role=rb_role)
        node = bms_nodes[0]
        interfaces = self.inputs.bms_data[node]['interfaces'][:1]
        sc1 = self.create_sc_profile(action='interface-shutdown',
                                     bandwidth=1, recovery_timeout=180)
        pp1 = self.create_port_profile(storm_control_profiles=[sc1.uuid])
        bms1 = self.create_bms(bms_name=node, vlan_id=10,
                               interfaces=interfaces, vn_fixture=vn,
                               port_profiles=[pp1.uuid])
        prouter = self.get_associated_prouters(node, interfaces)[0]
        assert sc1.validate_config_pushed([prouter], interfaces)
        assert prouter.validate_interfaces_status([interfaces[0]['tor_port']],
               status='up')
        pid = bms1.send_broadcast_traffic()
        assert prouter.validate_interfaces_status([interfaces[0]['tor_port']],
               status='down')
        bms1.stop_broadcast_traffic(pid)

    @skip_because(function='filter_bms_nodes', rb_role='erb_ucast_gw')
    @preposttest_wrapper
    def test_storm_control_profile_w_traffic_erb(self):
        rb_roles = dict()
        devices = list()
        for leaf in self.leafs:
            device_dict = self.inputs.physical_routers_data[leaf.name]
            if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                rb_roles[leaf.name] = ['ERB-UCAST-Gateway']
                devices.append(leaf)
        self.addCleanup(self.assign_roles, self.fabric, self.devices)
        self.assign_roles(self.fabric, devices, rb_roles=rb_roles)
        self.test_storm_control_profile_w_traffic(rb_role='erb_ucast_gw')

    @preposttest_wrapper
    def test_storm_control_profile_basic(self):
        bms_fixtures = list()
        vn = self.create_vn()
        bms_nodes = self.get_bms_nodes()
        lag_nodes = self.get_bms_nodes(bms_type='link_aggregation')
        mh_nodes = self.get_bms_nodes(bms_type='multi_homing')
        sc1 = self.create_sc_profile(action='interface-shutdown',
                                     bandwidth=1, recovery_timeout=60)
        pp1 = self.create_port_profile(storm_control_profiles=[sc1.uuid])
        pp2 = self.create_port_profile()
        sc2 = self.create_sc_profile(
            action='interface-shutdown',
            bandwidth=40, recovery_timeout=60,
            no_broadcast=True, no_multicast=True,
            no_unknown_unicast=True)
        pp2.add_storm_control_profiles([sc2.uuid])
        self.addCleanup(pp2.delete_storm_control_profiles, [sc2.uuid])
        if lag_nodes:
            lag_bms = self.create_bms(bms_name=lag_nodes[0],
                vn_fixture=vn, tor_port_vlan_tag=10, port_profiles=[pp1.uuid])
            lag_prouters = self.get_associated_prouters(lag_nodes[0])
            assert sc1.validate_config_pushed(lag_prouters, lag_bms.interfaces)
            pp = pp1; sc = sc1; bms = lag_bms; prouters = lag_prouters
        if mh_nodes:
            mh_bms = self.create_bms(bms_name=mh_nodes[0],
                vn_fixture=vn, vlan_id=10, port_profiles=[pp2.uuid])
            mh_prouters = self.get_associated_prouters(mh_nodes[0])
            assert sc2.validate_config_pushed(mh_prouters, mh_bms.interfaces)
            pp = pp2; sc = sc2; bms = mh_bms; prouters = mh_prouters
        other_nodes = set(bms_nodes) - set(lag_nodes or []) - set(mh_nodes or [])
#        other_nodes = bms_nodes
        if other_nodes:
            node = list(other_nodes)[0]
            interfaces = self.inputs.bms_data[node]['interfaces'][:1]
            single_bms = self.create_bms(bms_name=node, vlan_id=10,
                interfaces=interfaces,
                vn_fixture=vn)
            single_bms.add_port_profiles([pp1.uuid])
            single_prouters = self.get_associated_prouters(node, interfaces)
            assert sc1.validate_config_pushed(single_prouters, single_bms.interfaces)
            pp = pp1; sc = sc1; bms = single_bms; prouters = single_prouters
        if mh_nodes:
            assert sc2.validate_config_pushed(mh_prouters, mh_bms.interfaces)
        if lag_nodes:
            assert sc1.validate_config_pushed(lag_prouters, lag_bms.interfaces)
        pp.delete_storm_control_profiles([sc.uuid])
        assert sc.validate_config_pushed(prouters, bms.interfaces, exp=False)
        if lag_nodes and other_nodes:
            assert sc.validate_config_pushed(lag_prouters, lag_bms.interfaces, exp=False)
        pp.add_storm_control_profiles([sc.uuid])
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        if lag_nodes and other_nodes:
            assert sc.validate_config_pushed(lag_prouters, lag_bms.interfaces)
        bms.delete_port_profiles([pp.uuid])
        assert sc.validate_config_pushed(prouters, bms.interfaces, exp=False)
        bms.add_port_profiles([pp.uuid])
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        sc.update(action=list(), no_broadcast=False)
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        if lag_nodes and other_nodes:
            assert sc.validate_config_pushed(lag_prouters, lag_bms.interfaces)
        sc.update(no_multicast=False)
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        if lag_nodes and other_nodes:
            assert sc.validate_config_pushed(lag_prouters, lag_bms.interfaces)
        sc.update(no_registered_multicast=True)
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        sc.update(no_registered_multicast=False)
        sc.update(no_unregistered_multicast=True)
        assert sc.validate_config_pushed(prouters, bms.interfaces)
        try:
            sc.update(no_registered_multicast=True)
            assert False, 'cannot have multiple multicast options specified'
        except:
            pass

    @preposttest_wrapper
    def test_hw_inventory(self):
        devices = [device for device in self.devices if 'srx' not in device.model]
        for device in devices:
            assert len(device.get_hardware_inventorys()) == 1
        target_device = random.choice(devices)
        orig_hw_inventory = target_device.get_hardware_inventorys()
        self.fetch_hardware_inventory(self.fabric, [target_device])
        curr_hw_inventory = target_device.get_hardware_inventorys(refresh=True)
        assert orig_hw_inventory == curr_hw_inventory
        self.vnc_h.delete_hardware_inventory(id=orig_hw_inventory[0])
        self.fetch_hardware_inventory(self.fabric, [target_device])
        curr_hw_inventory = target_device.get_hardware_inventorys(refresh=True)
        assert len(curr_hw_inventory) == 1 and \
            curr_hw_inventory != orig_hw_inventory

#class TestBrownfieldUserWorkflow(BaseFabricTest):
    @preposttest_wrapper
    def test_rr_role_deletion(self):
        '''
        Testcase to validate add/deletion of RR role(CEM-9241).
        1. Remove RR role from dual spine.
        2. Ensure that neighbourship is proper.
        3. Addback RR role.
        '''
        mgmt_ip =list()
        if len(self.spines) > 1:

            bms_fixtures = list()
            vn = self.create_vn()
            vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
            for bms in self.get_bms_nodes()[:2]:
                bms_fixtures.append(self.create_bms(bms_name=bms,
                    vn_fixture=vn, tor_port_vlan_tag=10))
            vm1.wait_till_vm_is_up()
            # Validate bgp peers count is correct.
            spine = self.spines[0]
            bgp_peers = len(self.spines) + len(self.leafs) + len(self.inputs.bgp_ips) - 1
            count = int(spine.netconf.get_bgp_peer_count()['peer-count'])
            assert bgp_peers == count , "RR should form bgp session with all routers.\
                Expected session %s act %s "%(bgp_peers,count)

            rb_roles = dict()
            rb_roles[spine.name] = ['CRB-Gateway']
            # Remove RR role
            self.addCleanup(self.assign_roles, self.fabric, [spine])
            self.assign_roles(self.fabric, [spine], rb_roles=rb_roles)
            count = int(spine.netconf.get_bgp_peer_count()['peer-count'])
            exp_count = len(self.spines) - 1
            assert exp_count == count , "Spine should form session only with RR.\
                Expected session %s actual %s "%(exp_count, count)
            # Add RR role
            self.assign_roles(self.fabric, [spine])
            count = int(spine.netconf.get_bgp_peer_count()['peer-count'])
            assert bgp_peers == count , "RR should form bgp session with all routers.\
                Expected session %s act %s "%(bgp_peers, count)
            # Validate traffic
            self.do_ping_mesh(bms_fixtures+[vm1])
        else:
            raise self.skipTest("Skipping test. This test needs 2 spines.")

    @preposttest_wrapper
    def test_brownfield_user_workflow(self):

        '''
        Testcase to validate below work flow.Brownfield user workflow test(CEM-9241).
        1. Remove device from fabric.
        2. Add device to fabric.
        3. Reonboard device.
        4. Do basic traffic test with newly added device.
        '''
        def cleanup_reonboard(fabric_dict):
            fabric, self.devices, self.interfaces = self.onboard_existing_fabric(
                fabric_dict, enterprise_style=True, name=self.fabric.name,
                cleanup=False)
            self.singleton.devices = self.devices
            self.singleton.interfaces = self.interfaces
            self._populate_attrs()
            self.assign_roles(fabric, self.devices)

        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        fabName = self.fabric.name
        fabric_dict = copy.deepcopy(self.inputs.fabrics[0])
        self.addCleanup(cleanup_reonboard, copy.deepcopy(fabric_dict))

        #assert len(fabric_dict['namespaces']['management']) == len(self.devices),\
        #    "All devices are not onboarded"
        # Workflow to remove/add device.
        self.logger.info("Workflow to remove/Add device.")
        
        mgmt_ip =list()
        # Workflow to remove spine.
        if len(self.spines) > 1:
            spine = self.spines[0]
            self.cleanup_discover(self.fabric, [spine])
            mgmt_ip.append({'cidr' : str(spine.mgmt_ip + '/32')})
        # Workflow to remove leaf.
        leaf = self.leafs[0]
        self.logger.info("Remove device from fabric.")
        self.cleanup_discover(self.fabric, [leaf])
        mgmt_ip.append({'cidr' : str(leaf.mgmt_ip + '/32')})

        # Workflow to add leaf and spine
        self.logger.info("Add device to fabric.")

        fabric_dict['namespaces'].update({'management' : mgmt_ip})
        self.fabric, self.devices, self.interfaces = self.onboard_existing_fabric(
            fabric_dict, cleanup=False, enterprise_style=True, name=fabName)

        # Add roles to newly added devices.
        self.logger.info("Add roles to newly added devices.")
        self._populate_attrs()
        self.assign_roles(self.fabric, self.devices)

        # Reonboard devices
        self.logger.info("Workflow to reonboard device.")

        self.onboard([self.leafs[0]])

        # Validate basic traffic tests.
        self.logger.info("Validate basic traffic tests.")

        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros-0.4.0')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, tor_port_vlan_tag=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

class TestVxlanID(GenericTestBase):
    @preposttest_wrapper
    def test_check_vxlan_id_reuse(self):
        '''
            Create a VN X
            Create another VN Y and check that the VNid is the next number
            Delete the two Vns
            On creating a VN again, verify that Vxlan id of X is used
             (i.e vxlan id gets reused)
        '''
        vn1 = self.create_vn()
        vn2 = self.create_vn()

        vxlan_id1 = vn1.get_vxlan_id()
        vxlan_id2 = vn2.get_vxlan_id()

        assert vxlan_id2 == (vxlan_id1+1), (
            "Vxlan ID allocation is not incremental, "
            "Two VNs were seen to have vxlan ids %s, %s" % (
                vxlan_id1, vxlan_id2))
        # Delete the vns
        self.perform_cleanup(vn1)
        self.perform_cleanup(vn2)

        vn3_fixture = self.create_vn()
        assert vn3_fixture.verify_on_setup(), "VNFixture verify failed!"
        new_vxlan_id = vn3_fixture.get_vxlan_id()
        assert new_vxlan_id == vxlan_id1, (
            "Vxlan ID reuse does not seem to happen",
            "Expected : %s, Got : %s" % (vxlan_id1, new_vxlan_id))
        self.logger.info('Vxlan ids are reused..ok')
    # end test_check_vxlan_id_reuse
