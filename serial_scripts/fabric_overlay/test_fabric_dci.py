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

    def configure_fabric_for_dci_and_get_lrs(self):
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
        return lr, lr1

    def create_dci_between_fabrics(self):
        lr1, lr2 = self.configure_fabric_for_dci_and_get_lrs()
        dci_uuid = self.vnc_h.create_dci(get_random_name('dci'), lr1.uuid, lr2.uuid)
        sleep(10)
        return dci_uuid

    @preposttest_wrapper
    def test_fabric_dci_basic(self):
        dci_uuid = self.create_dci_between_fabrics()
        self.addCleanup(self.vnc_h.delete_dci, id=dci_uuid)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)

    @preposttest_wrapper
    def test_dci_negative_case(self):
        '''
          1. Create vn and vn1
          2. Create one bms in both the fabrics and associate it to the vns created.
          3. Create 2 LRs including one VN in each of them.
          4. Create DCI including both the LRs
          5. Check ping between the BMS
          6. Delete the DCI object created in step 4
          7. Check ping between the BMS and expect the ping to fail.
        '''
        dci_uuid = self.create_dci_between_fabrics()
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
        self.vnc_h.delete_dci(id=dci_uuid)
        sleep(10)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=False)

    @skip_because(bms=3)
    @preposttest_wrapper
    def test_stop_device_manager(self):
        '''
          1. Test dci basic case(ping between BMS1 and BMS2).
          2. Stop the device manager
          3. Create a new VN and include it in the existing LR in the fabric
          4. Associate third BMS, BMS3 that with the new VN
          5. Bring up device manager
          6. Check ping from BMS3 to BMS2
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        vn3 = self.create_vn()
        lr1, lr2 = self.configure_fabric_for_dci_and_get_lrs()
        dci_uuid = self.vnc_h.create_dci(get_random_name('dci'), lr1.uuid, lr2.uuid)
        self.addCleanup(self.vnc_h.delete_dci, id=dci_uuid)
        sleep(10)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
        self.inputs.stop_container(self.inputs.cfgm_ips, 'device-manager')
        try:
            fabric_bms_list = self.get_bms_nodes(devices=self.devices)
            fabric2_bms_list = self.get_bms_nodes(devices=self.devices2)
            fabric_bms_list.remove(self.bms1.name)
            fabric2_bms_list.remove(self.bms2.name)
            if len(fabric_bms_list) > 0:
                self.bms3 = self.create_bms(bms_name=fabric_bms_list[0],
                    vn_fixture=vn3, tor_port_vlan_tag=20, fabric_fixture=self.fabric)
                lr = lr1
                ping_to_bms = self.bms2
            else:
                self.bms3 = self.create_bms(bms_name=fabric2_bms_list[0],
                    vn_fixture=vn3, tor_port_vlan_tag=20, fabric_fixture=self.fabric2)
                ping_to_bms = self.bms1
                lr = lr2
            lr.add_interface([vn3.get_uuid()])
        finally:
            self.inputs.start_container(self.inputs.cfgm_ips, 'device-manager')
            sleep(60)
        assert self.bms3.ping_with_certainty(
            ping_to_bms.bms_ip, expectation=True)

    @preposttest_wrapper
    def test_fabric_dci_restart(self):
        dci_uuid = self.create_dci_between_fabrics()
        self.addCleanup(self.vnc_h.delete_dci, id=dci_uuid)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        assert self.bms1.ping_with_certainty(self.bms2.bms_ip)

class TestFabricDCI_EBGP(TestFabricDCI):
    dci_mode = 'ebgp'
    @classmethod
    def setUpClass(cls):
        super(TestFabricDCI_EBGP, cls).setUpClass()
        cls.dci_ebgp_asn = 64599
