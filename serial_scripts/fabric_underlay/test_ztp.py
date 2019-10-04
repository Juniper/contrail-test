from common.contrail_fabric.ztp_base import ZtpBaseTest
from tcutils.wrappers import preposttest_wrapper

class TestZtp(ZtpBaseTest):
    @preposttest_wrapper
    def test_ztp_basic(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        # Test Leafs
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms, vlan_id=10,
                vn_fixture=vn))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1])

        # Test Spines
        vn2 = self.create_vn()
        self.create_logical_router([vn, vn2])
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros')
        for bms in list(bms_fixtures):
            bms_fixtures.append(self.create_bms(bms_name=bms.name, vlan_id=20,
                vn_fixture=vn2, bond_name=bms.bond_name,
                port_group_name=bms.port_group_name))
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])
