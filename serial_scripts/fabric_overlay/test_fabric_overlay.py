import test
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest

class TestFabricOverlayBasic(BaseFabricTest):
    @classmethod
    def setUpClass(cls):
        super(TestFabricOverlayBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
#        if getattr(cls, 'fabric', None):
#            cls.cleanup_fabric(cls.fabric)
        super(TestFabricOverlayBasic, cls).tearDownClass()

    @preposttest_wrapper
    def test_fabric_sanity(self):
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric, devices, interfaces = self.onboard_existing_fabric(fabric_dict)
        assert interfaces, 'Failed to onboard existing fabric %s'%fabric_dict
        self.assign_roles(fabric, devices)

        bms_fixtures = list()

        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        assert self.do_ping_mesh(bms_fixtures+[vm1])
