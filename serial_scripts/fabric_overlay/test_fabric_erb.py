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
import time


class TestFabricERB(BaseFabricTest):
    enterprise_style = True

    def is_test_applicable(self):
        result, msg = super(TestFabricERB, self).is_test_applicable()
        if result is False:
            return False, msg

        msg = 'No device with erb_ucast_gw rb_role in the provided fabric topology'
        for device_dict in self.inputs.physical_routers_data.values():
            if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                break

        if len(self.get_bms_nodes(rb_role='erb_ucast_gw')) > 1:
            return True, None

        else:
            return False, msg

        return True, None

    def setUp(self):
        for device, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'leaf':
                if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                    self.rb_roles[device] = ['ERB-UCAST-Gateway']
            elif device_dict['role'] == 'spine':
                if not device_dict.get('rb_roles', []):
                    self.rb_roles[device] = ['lean', 'Route-Reflector']
        super(TestFabricERB, self).setUp()

    @skip_because(function='filter_bms_nodes', rb_role='erb_ucast_gw',
                  min_bms_count=1)
    @preposttest_wrapper
    def test_fabric_erb_intravn_basic(self):
        '''
           Create VN vn
           Create VM on vn
           Create BMS nodes in the same VN (vn)
           Check ping connectivity across all the instances
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros-0.4.0')
        for bms in self.get_bms_nodes(rb_role='erb_ucast_gw'):
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, vlan_id=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @preposttest_wrapper
    @skip_because(function='filter_bms_nodes', rb_role='erb_ucast_gw',
                  min_bms_count=1)
    def test_fabric_erb_intervn_basic(self):
        '''
           Create VN vn1
           Create VNs per BMS node
           Create Logical Router and add all the VNs
           Create VM on vn1
           Create untagged BMS instances on respective VNs
           Check ping connectivity across all the instances
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')

        bms_fixtures = list()
        bms_vns = dict()
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        bms_nodes = self.get_bms_nodes(rb_role='erb_ucast_gw')
        for bms in bms_nodes:
            bms_vns[bms] = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros-0.4.0')
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros-0.4.0')
        vlan = 3
        for bms in bms_nodes:
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                vlan_id=vlan,
                vn_fixture=bms_vns[bms]))
            vlan = vlan + 1

        erb_devices = list()
        for d in self.leafs:
            if 'erb_ucast_gw' in self.inputs.get_prouter_rb_roles(d.name):
                erb_devices.append(d)

        self.create_logical_router([vn1, vn2] + bms_vns.values(), vni=str(
            random.randint(0, 6000)), devices=erb_devices)
        vm1.wait_till_vm_is_up()
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])

    @preposttest_wrapper
    @skip_because(function='filter_bms_nodes', rb_role='erb_ucast_gw',
                  min_bms_count=2)
    def test_fabric_erb_restart(self):
        """
           Create VN vn1, vn2
           Create VNs per BMS node and reserve one bms node if more than 1
           Create Logical Router and add all the VNs
           Create VM1 on vn1, VM2 on vn2
           Create untagged BMS instances on respective VNs
           Check ping connectivity across all the instances
           Restart the API server and DM
           Check ping connectivity across all the instances
           Stop the DM
           Create the reserved BMS and extend the VN to Logical Router.
           Check ping connectivity between newly created BMS and VM - it should fail.
           Start the DM
           Check ping connectivity across all the instances
        """
        bms_fixtures = list()
        bms_vns = dict()
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        bms_nodes = self.get_bms_nodes(rb_role='erb_ucast_gw')

        for bms in bms_nodes:
            bms_vns[bms] = self.create_vn()

        vm1 = self.create_vm(vn_fixture=vn1, image_name='ubuntu')
        vm2 = self.create_vm(vn_fixture=vn2, image_name='ubuntu')
        vlan = 3

        reserved_bms_node = None
        if len(bms_nodes) > 1:
            reserved_bms_node = bms_nodes[0]

        for bms in bms_nodes[1:]:
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                vlan_id=vlan,
                vn_fixture=bms_vns[bms]))
            vlan = vlan + 1

        erb_devices = list()
        for d in self.leafs:
            if 'erb_ucast_gw' in self.inputs.get_prouter_rb_roles(d.name):
                erb_devices.append(d)

        lr = self.create_logical_router([vn1, vn2] + bms_vns.values(), vni=str(
            random.randint(0, 6000)), devices=erb_devices)
        vm1.wait_till_vm_is_up()
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])

        self.logger.debug('restart dm and api-server and verify ping')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')

        self.logger.debug('wait for dm and api-server to settle down')

        time.sleep(20)

        self.do_ping_mesh(bms_fixtures + [vm1, vm2])

        self.logger.debug('stop the device manager and do code changes.')

        self.inputs.stop_container(self.inputs.cfgm_ips, 'device-manager')
        self.addCleanup(self.start_containers, self.inputs.cfgm_ips, ['device-manager'])
        if reserved_bms_node:
            reserved_vn = bms_vns[reserved_bms_node]
            reserved_bms_node_fixture = self.create_bms(
                bms_name=reserved_bms_node,
                vlan_id=vlan,
                vn_fixture=reserved_vn)
            bms_fixtures.append(reserved_bms_node_fixture)

            lr.add_interface([reserved_vn.uuid])

            self.do_ping_mesh([reserved_bms_node_fixture]+[vm1],
                              expectation=False)

        self.inputs.start_container(self.inputs.cfgm_ips, 'device-manager')
        time.sleep(30)
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])
