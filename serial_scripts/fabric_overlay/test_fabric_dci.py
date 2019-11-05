import test
import random
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from time import sleep
from common.contrail_fabric.base import BaseFabricTest

class TestFabricDCI(BaseFabricTest):
    def is_test_applicable(self):
        result, msg = super(TestFabricDCI, self).is_test_applicable()
        if result is False:
            return False, msg
        msg = 'No device with dci_gw rb_role in the provided fabric topology'
        for device_dict in list(self.inputs.physical_routers_data.values()):
            if 'dci_gw' in (device_dict.get('rb_roles') or []):
                break
        else:
            return False, msg
        if len(self.inputs.fabrics) < 2:
            return False, 'DCI Gateway tests require atleast two fabrics'
        return True, msg

    def setUp(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'dci_gw' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['DCI-Gateway', 'DC-Gateway', 'Route-Reflector']
        super(TestFabricDCI, self).setUp()

    def config_and_validate_dci(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        self.bms1 = self.create_bms(bms_name=random.choice(
            self.get_bms_nodes(devices=self.devices)),
            vn_fixture=vn, tor_port_vlan_tag=10, fabric_fixture=self.fabric)
        self.bms2 = self.create_bms(bms_name=random.choice(
            self.get_bms_nodes(devices=self.devices2)),
            vn_fixture=vn1, tor_port_vlan_tag=10, fabric_fixture=self.fabric2)
        devices = list()
        for device in self.devices:
            if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
                 devices.append(device)
        lr = self.create_logical_router([vn], devices=devices)
        devices = list()
        for device in self.devices2:
            if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
                 devices.append(device)
        lr1 = self.create_logical_router([vn1], devices=devices)
        dci = self.vnc_h.create_dci(get_random_name('dci'), lr.uuid, lr1.uuid)
        self.addCleanup(self.vnc_h.delete_dci, id=dci)
        sleep(10)
        assert self.bms1.ping_with_certainty(self.bms2.bms_ip)

    @preposttest_wrapper
    def test_fabric_dci_basic(self):
        self.config_and_validate_dci()

    @preposttest_wrapper
    def test_fabric_dci_restart(self):
        self.config_and_validate_dci()
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        assert self.bms1.ping_with_certainty(self.bms2.bms_ip)

class TestFabricDCI_EBGP(TestFabricDCI):
    dci_mode = 'ebgp'
    @classmethod
    def setUpClass(cls):
        super(TestFabricDCI_EBGP, cls).setUpClass()
        cls.dci_ebgp_asn = 64599
