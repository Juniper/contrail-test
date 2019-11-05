from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
from tcutils.util import skip_because
import test
import time
import random

class TestFabricDcGw(BaseFabricTest):
    def is_test_applicable(self):
        result, msg = super(TestFabricDcGw, self).is_test_applicable()
        if result:
            msg = 'No device with dc_gw rb_role in the provided fabric topology'
            for device_dict in list(self.inputs.physical_routers_data.values()):
                if 'dc_gw' in (device_dict.get('rb_roles') or []):
                    break
            else:
                return False, msg
            msg = 'No public subnets or public host specified in test inputs yaml'
            if self.inputs.public_subnets and self.inputs.public_host:
                return (True, None)
        return False, msg

    def setUp(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'dc_gw' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['DC-Gateway', 'Route-Reflector']
                    if 'qfx' in device_dict.get('model', 'qfx'):
                        self.rb_roles[device].append('CRB-Gateway')
                elif device_dict['role'] == 'leaf':
                    self.rb_roles[device] = ['DC-Gateway', 'CRB-Access']
        super(TestFabricDcGw, self).setUp()

    @preposttest_wrapper
    def itest_floating_ip(self):
        fip_ips = dict()
        bms_fixtures = list()
        public_vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1],
            router_external=True)
        fip_pool = self.create_fip_pool(public_vn.uuid)
        private_vn = self.create_vn()

        for spine in self.spines:
            prouter_details = self.inputs.physical_routers_data[spine.name]
            if prouter_details.get('model', '').startswith('mx'):
                spine.add_service_interface(prouter_details['si_port'])
                spine.add_virtual_network(public_vn.uuid)
                self.addCleanup(spine.delete_virtual_network, public_vn.uuid)
        vm = self.create_vm(vn_fixture=private_vn, image_name='cirros')

        for bms in list(self.inputs.bms_data.keys()):
            bms_fixture = self.create_bms(bms_name=bms, vn_fixture=private_vn)
            bms_fixtures.append(bms_fixture)
            fip_ips[bms_fixture.port_fixture.uuid], fip_id = \
                self.create_and_assoc_fip(fip_pool, vm_fixture=None,
                vmi_id=bms_fixture.port_fixture.uuid)
        fip_ips[vm.uuid], fip_id = self.create_and_assoc_fip(fip_pool, vm)
        self.check_vms_booted([vm])

        for fixture in bms_fixtures + [vm]:
            msg = 'ping from %s to %s failed'%(fixture.name,
                                               self.inputs.public_host)
            assert fixture.ping_with_certainty(self.inputs.public_host)

    @preposttest_wrapper
    def test_instance_on_public_network(self):
        bms_fixtures = list()
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        lr = self.create_logical_router([vn], is_public_lr=True)
        vm = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                tor_port_vlan_tag=10,
                vn_fixture=vn))
        self.check_vms_booted([vm])

        for fixture in bms_fixtures + [vm]:
            assert fixture.ping_with_certainty(self.inputs.public_host)
        self.do_ping_mesh(bms_fixtures + [vm])

    @preposttest_wrapper
    def test_update_vni(self):
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        lr = self.create_logical_router([vn], is_public_lr=True, vni=7777)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        vm2 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms1 = self.create_bms(
                bms_name=random.choice(self.get_bms_nodes()),
                tor_port_vlan_tag=10,
                vn_fixture=vn)
        self.check_vms_booted([vm1, vm2])

        for fixture in [bms1, vm1, vm2]:
            assert fixture.ping_with_certainty(self.inputs.public_host)
        self.do_ping_mesh([bms1, vm1, vm2])

        lr.set_vni(7788)
        self.sleep(90) # Wait for configs to be pushed to Spines
        for fixture in [bms1, vm1, vm2]:
            assert fixture.ping_with_certainty(self.inputs.public_host)
        self.do_ping_mesh([bms1, vm1, vm2])

    @preposttest_wrapper
    def test_private_and_public_vn_part_of_lr(self):
        bms_node = random.choice(self.get_bms_nodes())
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        priv_vn = self.create_vn()
        lr = self.create_logical_router([vn, priv_vn], is_public_lr=True, vni=7777)
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        vm2 = self.create_vm(vn_fixture=priv_vn, image_name='cirros')
        bms1 = self.create_bms(
                bms_name=bms_node,
                vn_fixture=vn,
                vlan_id=10)
        bms2 = self.create_bms(
                bms_name=bms_node,
                vn_fixture=priv_vn,
                port_group_name=bms1.port_group_name,
                bond_name=bms1.bond_name,
                vlan_id=20)
        self.check_vms_booted([vm1, vm2])
        for fixture in [bms1, vm1]:
            assert fixture.ping_with_certainty(self.inputs.public_host)
        self.do_ping_mesh([bms1, bms2, vm1, vm2])
        assert bms2.ping_with_certainty(self.inputs.public_host, expectation=False)
        assert vm2.ping_with_certainty(self.inputs.public_host, expectation=False)
