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
    enterprise_style = False

    def is_test_applicable(self):
        result, msg = super(TestFabricERB, self).is_test_applicable()
        if result is False:
            return False, msg
        msg = 'No device with erb_ucast_gw rb_role in the provided fabric topology'
        for device_dict in self.inputs.physical_routers_data.values():
            if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                break
        else:
            return False, msg

        return True, None

    def setUp(self):
        for device, device_dict in self.inputs.physical_routers_data.items():
            if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'leaf':
                    self.rb_roles[device] = ['ERB-UCAST-Gateway']
        super(TestFabricERB, self).setUp()

    @preposttest_wrapper
    def test_fabric_intravn_basic(self):
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
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, tor_port_vlan_tag=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    def test_fabric_intervn_basic(self):
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
        for bms in self.get_bms_nodes():
            bms_vns[bms] = self.create_vn()
        self.create_logical_router([vn1, vn2] + bms_vns.values(),
                                   devices=self.erb_devices)
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros')
        vlan = 3
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                tor_port_vlan_tag=vlan,
                vn_fixture=bms_vns[bms]))
            vlan = vlan + 1
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])

    @preposttest_wrapper
    def test_fabric_restart(self):
        '''
          Create VN vn
          Create VM on vn
          Create BMS nodes in the same VN (vn)
          Check ping connectivity across all the instances
          Restart the Containers and wait for settle down.
          Check ping connectivity across all the instances
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')

        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                                                vn_fixture=vn,
                                                tor_port_vlan_tag=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1])

        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')

        time.sleep(60)

        self.do_ping_mesh(bms_fixtures + [vm1])


