import test
from netaddr import *
import uuid
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress

class TestFabricOverlay(BaseFabricTest):
    @preposttest_wrapper
    def test_fabric_intravn_basic(self):
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_bms_movement(self):
        first_node = self.inputs.bms_data.keys()[0]
        second_node = self.inputs.bms_data.keys()[1]
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        node1_bms1 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn,
                         security_groups=[self.default_sg.uuid])
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh([node1_bms1, vm1])
        node1_bms1.update_vmi(self.inputs.bms_data[second_node].interfaces,
                         port_group_name=None)
        self.do_ping_test(node1_bms1, vm1.vm_ip, expectation=False)
        node2_bms1 = self.create_bms(bms_name=second_node,
                         port_fixture=node1_bms1.port_fixture)
        self.do_ping_test(node2_bms1, vm1.vm_ip)
        node1_bms1.cleanup_bms()
        node1_bms2 = self.create_bms(bms_name=first_node, vlan_id=10,
                         vn_fixture=vn,
                         security_groups=[self.default_sg.uuid])
        self.do_ping_mesh([vm1, node1_bms2, node2_bms1])
        node1_bms3 = self.create_bms(bms_name=first_node, vlan_id=20,
                         vn_fixture=vn,
                         security_groups=[self.default_sg.uuid],
                         port_group_name=node1_bms2.port_group_name)
        self.do_ping_mesh([vm1, node1_bms2, node1_bms3, node2_bms1])
        node1_bms3.update_vmi(self.inputs.bms_data[second_node].interfaces,
                         port_group_name=node2_bms1.port_group_name)
        self.do_ping_test(node1_bms3, vm1.vm_ip, expectation=False)
        node1_bms3.cleanup_bms()
        node2_bms2 = self.create_bms(bms_name=second_node,
                         port_fixture=node1_bms3.port_fixture)
        self.do_ping_mesh([vm1, node1_bms2, node2_bms2, node2_bms1])

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_with_multiple_subnets(self):
        ''' Create a VN with two /28 subnets
            Create 8 VMIs on the VN so that 1st subnet IPs are exhausted
            Add lifs with 6th and 7th VMIs
            Validate that the BMSs get IP from 2nd subnet and ping passes
        '''
        vn_subnets = [get_random_cidr('28'), get_random_cidr('28')]
        vn_fixture = self.create_vn(vn_subnets=vn_subnets, disable_dns=True)

        self.create_logical_router([vn_fixture])
        bms_data = self.inputs.bms_data.keys()
        bms1_fixture = self.create_bms(bms_name=bms_data[0],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid])
        vm1 = self.create_vm(vn_fixture=vn_fixture, image_name='cirros')
        for i in range(0, 4):
            port_fixture = self.setup_vmi(vn_fixture.uuid)
            if port_fixture.get_ip_addresses()[0] in IPNetwork(vn_subnets[1]):
                self.perform_cleanup(port_fixture)
                break
        bms2_fixture = self.create_bms(bms_name=bms_data[1],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid])
        vm2 = self.create_vm(vn_fixture=vn_fixture, image_name='cirros')

        self.do_ping_mesh(bms_fixtures+[vm1, vm2])
    # end test_with_multiple_subnets

    @preposttest_wrapper
    def test_intravn_tagged_bms(self):
        '''Validate ping between a KVM VM and a tagged BMS
        '''
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms, vlan_id=10,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])
    #end test_intravn_tagged_bms

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
        vn_fixture = self.create_vn(disable_dns=True)
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=10)
        bms2_fixture = self.create_bms(bms_name=bms_data[1],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid])

        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip)

        bms1_fixture.delete_vmi()
        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip, expectation=False)
        bms1_fixture.cleanup_bms()

        bms1_fixture.vlan_id = 20
        bms1_fixture.setUp()

        status, msg = bms1_fixture.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        bms1_fixture.verify_on_setup()
        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip)
    # end test_remove_add_instance

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_lag_add_remove_interface(self):
        lag_node = list(self.filter_bms_nodes('link_aggregation'))[0]
        other_nodes = set(self.inputs.bms_data.keys()) - set([lag_node])
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        other_bms = list()
        lag_bms = self.create_bms(bms_name=lag_node,
                vn_fixture=vn, security_groups=[self.default_sg.uuid])
        for node in other_nodes:
            other_bms.append(self.create_bms(bms_name=node,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        instances = [lag_bms] + other_bms + [vm1]
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)

        interface_to_detach = self.inputs.bms_data[lag_node].interfaces[0]
        other_interfaces = self.inputs.bms_data[lag_node].interfaces[1:]
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
        lag_bms.setup_bms(self.inputs.bms_data[lag_node].interfaces)
        lag_bms.is_lacp_up()
        status, msg = lag_bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @preposttest_wrapper
    def test_multihoming_add_remove_interface(self):
        mh_nodes = self.filter_bms_nodes('multi_homing')
        mh_node = list(mh_nodes)[0]
        # Check if we have BMS which has both lag and mh
        lag_nodes = self.filter_bms_nodes('link_aggregation')
        mh_lag_nodes = mh_nodes.intersection(lag_nodes)
        if mh_lag_nodes:
            mh_node = list(mh_lag_nodes)[0]

        other_nodes = set(self.inputs.bms_data.keys()) - set([mh_node])
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        other_bms = list()
        mh_bms = self.create_bms(bms_name=mh_node, vlan_id=10,
                vn_fixture=vn, security_groups=[self.default_sg.uuid])
        for node in other_nodes:
            other_bms.append(self.create_bms(bms_name=node,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        instances = [mh_bms] + other_bms + [vm1]
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)

        interface_to_detach = self.inputs.bms_data[mh_node].interfaces[0]
        other_interfaces = self.inputs.bms_data[mh_node].interfaces[1:]
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
        mh_bms.setup_bms(self.inputs.bms_data[mh_node].interfaces)
        mh_bms.is_lacp_up()
        status, msg = mh_bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    def _validate_multiple_vlan(self, bms_type):
        target_nodes = self.filter_bms_nodes(bms_type)
        target_node = list(target_nodes)[0]
        other_nodes = set(self.inputs.bms_data.keys()) - set([target_node])
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms = self.create_bms(bms_name=target_node, vlan_id=10,
              vn_fixture=vn, security_groups=[self.default_sg.uuid])
        instances = [bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=list(other_nodes)[0],
                vn_fixture=vn, security_groups=[self.default_sg.uuid])
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)
        bms_2 = self.create_bms(bms_name=target_node, vlan_id=20,
            port_group_name=bms.port_group_name,
            vn_fixture=vn, security_groups=[self.default_sg.uuid])
        instances.append(bms_2)
        self.do_ping_mesh(instances)
        bms_3 = self.create_bms(bms_name=target_node,
            port_group_name=bms.port_group_name,
            vn_fixture=vn, security_groups=[self.default_sg.uuid])
        instances.append(bms_3)
        other_vn = self.create_vn()
        bms_4 = self.create_bms(bms_name=target_node, vlan_id=30,
            port_group_name=bms.port_group_name,
            vn_fixture=vn, security_groups=[self.default_sg.uuid])
        instances.append(bms_4)
        self.do_ping_test(bms1, bms4.bms_ip, expectation=False)

        self.create_logical_router([vn, other_vn])
        self.do_ping_mesh(instances)

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @preposttest_wrapper
    def test_multihoming_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='multi_homing')

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_lag_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='link_aggregation')

    @skip_because(function='filter_bms_nodes', bms_type='single_interface')
    @preposttest_wrapper
    def test_single_interface_multiple_vlan(self):
        self._validate_multiple_vlan(bms_type='single_interface')

    @preposttest_wrapper
    def test_update_vlan_id(self):
        target_node = self.inputs.bms_data.keys()[0]
        other_nodes = set(self.inputs.bms_data.keys()) - set([target_node])
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms = self.create_bms(bms_name=target_node, vlan_id=10,
              vn_fixture=vn, security_groups=[self.default_sg.uuid])
        instances = [bms, vm1]
        if other_nodes:
            other_bms = self.create_bms(bms_name=list(other_nodes)[0],
                vn_fixture=vn, security_groups=[self.default_sg.uuid])
            instances.append(other_bms)
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(instances)
        bms.update_vlan_id(20)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)
        bms.update_vlan_id(None)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)
        bms.update_vlan_id(30)
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        self.do_ping_mesh(instances)

    @preposttest_wrapper
    def test_secgrp_subnet_allow_all(self):
        bms_fixtures = list()
        project = self.project
        sec_grp_name1 = 'sg1' #get_random_name(prefix='sec_grp')
        sec_grp_name2 = 'sg2' #get_random_name(prefix='sec_grp')
        vn = self.create_vn()
        vn_subnets = vn.vn_subnets
        vn_prefix = vn_subnets[0]['cidr'].split('/')[0]
        vn_prefix_len = int(vn_subnets[0]['cidr'].split('/')[1])
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        rule2 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': '0.0.0.0',
                                         'ip_prefix_len': '24'}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0',
                                         'ip_prefix_len': '24'}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        sg_test1 = self.create_sec_group(name=sec_grp_name1, entries=rule1)
        sg_test2 = self.create_sec_group(name=sec_grp_name2, entries=rule2)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros', sg_ids=[sg_test1.uuid])
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[sg_test2.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])


    @preposttest_wrapper
    def test_default_secgrp_subnet_allow_all(self):
        bms_fixtures = list()
        project = self.project
        sec_grp_name1 = 'sg1' #get_random_name(prefix='sec_grp')
        sec_grp_name2 = 'sg2' #get_random_name(prefix='sec_grp')
        vn = self.create_vn()
        vn_subnets = vn.vn_subnets
        vn_prefix = vn_subnets[0]['cidr'].split('/')[0]
        vn_prefix_len = int(vn_subnets[0]['cidr'].split('/')[1])
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        sg_test1 = self.create_sec_group(name=sec_grp_name1, entries=rule1)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros', sg_ids=[sg_test1.uuid])
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @preposttest_wrapper
    def test_secgrp_subnet_deny_all(self):
        bms_fixtures = list()
        project = self.project
        sec_grp_name1 = 'sg1' #get_random_name(prefix='sg') 
        sec_grp_name2 = 'sg2' #get_random_name(prefix='sg') 
        vn = self.create_vn()
        vn_instance = self.create_vn()
        vn_subnets = vn.vn_subnets
        vn_prefix = vn_subnets[0]['cidr'].split('/')[0]
        vn_prefix_len = int(vn_subnets[0]['cidr'].split('/')[1])
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        rule2 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': '0.0.0.0',
                                         'ip_prefix_len': '24'}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0',
                                         'ip_prefix_len': '24'}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        sg_test1 = self.create_sec_group(name=sec_grp_name1, entries=rule1)
        sg_test2 = self.create_sec_group(name=sec_grp_name2, entries=rule2)
        vm1 = self.create_vm(vn_fixture=vn_instance, image_name='cirros', sg_ids=[sg_test1.uuid])
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn_instance, security_groups=[sg_test2.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1], expectation=False)        


    @preposttest_wrapper
    def test_default_secgrp_subnet_deny_all(self):
        bms_fixtures = list()
        project = self.project
        sec_grp_name1 = 'sg1' #get_random_name(prefix='sg') 
        sec_grp_name2 = 'sg2' #get_random_name(prefix='sg') 
        vn = self.create_vn()
        vn_instance = self.create_vn()
        vn_subnets = vn.vn_subnets
        vn_prefix = vn_subnets[0]['cidr'].split('/')[0]
        vn_prefix_len = int(vn_subnets[0]['cidr'].split('/')[1])
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_1,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': vn_prefix,
                                         'ip_prefix_len': vn_prefix_len}}],
                  'rule_uuid': uuid_2,
                  'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'ethertype': 'IPv6'
                  }
                 ]
        sg_test1 = self.create_sec_group(name=sec_grp_name1, entries=rule1)
        vm1 = self.create_vm(vn_fixture=vn_instance, image_name='cirros', sg_ids=[sg_test1.uuid])
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn_instance, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1], expectation=False)        

    @skip_because(function='filter_bms_nodes', bms_type='link_aggregation')
    @preposttest_wrapper
    def test_bridge_domain_on_leaf(self):
        bms = list(self.filter_bms_nodes('link_aggregation'))[0]
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        bms1_intf = self.inputs.bms_data[bms].interfaces[:1]
        bms2_intf = self.inputs.bms_data[bms].interfaces[1:]
        bms1 = self.create_bms(bms_name=bms, vn_fixture=vn1,
               vlan_id=10, interfaces=bms1_intf,
               security_groups=[self.default_sg.uuid])
        bms2 = self.create_bms(bms_name=bms, vn_fixture=vn2,
               vlan_id=10, interfaces=bms2_intf,
               security_groups=[self.default_sg.uuid])
        new_ip = str(IPAddress(bms1.bms_ip) + 10)
        bms2.assign_static_ip(new_ip)
        self.do_ping_test(bms1, new_ip, expectation=False)

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
