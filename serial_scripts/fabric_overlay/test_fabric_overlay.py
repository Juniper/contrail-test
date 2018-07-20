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
        if getattr(cls, 'interfaces'):
            cls.cleanup_onboard(cls.devices, cls.interfaces)
        if getattr(cls, 'devices'):
            cls.cleanup_discover(cls.fabric, cls.devices)
        if getattr(cls, 'fabric'):
            cls.cleanup_fabric(cls.fabric)
        super(TestFabricOverlayBasic, cls).tearDownClass()

    @preposttest_wrapper
    def test_fabric_sanity(self):
        fabric_dict = self.inputs.fabrics[0]
        fabric = self.create_fabric(namespaces=fabric_dict['namespaces'],
                                    creds=fabric_dict['credentials'])
        exec_id, devices = self.discover(fabric)
        assert devices, 'No devices been discovered'
        exec_id, interfaces = self.onboard(devices)
        assert interfaces['logical'], 'Failed to onboard devices %s'%devices
        self.configure_underlay(devices)
