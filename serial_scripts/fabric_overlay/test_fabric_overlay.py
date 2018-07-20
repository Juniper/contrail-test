import test
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest

class TestFabricOverlayBasic(BaseFabricTest):
    @classmethod
    def setUpClass(cls):
        super(TestFabricOverlayBasic, cls).setUpClass()

    @classmethod
    def setup_testcase(cls):
        fabric_dict = cls.inputs.fabrics[0]
        cls.fabric = cls.create_fabric(namespaces=fabric_dict['namespaces'],
                                    creds=fabric_dict['credentials'], cleanup=False)
        exec_id, cls.devices = cls.discover(cls.fabric, cleanup=False)
        assert cls.devices, 'No devices been discovered'
        exec_id, cls.interfaces = cls.onboard(cls.devices, cleanup=False)
        assert cls.interfaces['logical'], 'Failed to onboard devices %s'%devices
        cls.configure_underlay(devices)

    @classmethod
    def tearDownClass(cls):
        '''
        if getattr(cls, 'devices', None) and cls.interfaces.get('logical'):
            cls.cleanup_onboard(cls.devices, cls.interfaces)
        if getattr(cls, 'devices', None):
            cls.cleanup_discover(cls.fabric, cls.devices)
        if getattr(cls, 'fabric', None):
            cls.cleanup_fabric(cls.fabric)
        '''
        super(TestFabricOverlayBasic, cls).tearDownClass()

    @preposttest_wrapper
    def test_fabric_sanity(self):
        # Start - From here till End will be moved to setupclass/teardownclass
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric = self.create_fabric(namespaces=fabric_dict['namespaces'],
                                    creds=fabric_dict['credentials'])
        exec_id, devices = self.discover(fabric)
        assert devices, 'No devices been discovered'
        exec_id, interfaces = self.onboard(devices)
        assert interfaces['logical'], 'Failed to onboard devices %s'%devices
        self.configure_underlay(devices)
        self.assign_roles(devices)
        # End

        vn = self.create_vn()
        bms_data = self.inputs.bms_data.keys()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        bms1 = self.create_bms(bms_name=bms_data[0], vn_fixture=vn, security_groups=[self.default_sg.uuid])

        bms2 = self.create_bms(bms_name=bms_data[1], vn_fixture=vn, security_groups=[self.default_sg.uuid])
        vm1.wait_till_vm_is_up()
        assert vm1.ping_with_certainty(bms1.bms_ip)
        assert vm1.ping_with_certainty(bms2.bms_ip)
        assert bms1.ping_with_certainty(bms2.bms_ip)

