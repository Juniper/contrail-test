from __future__ import absolute_import
# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'

# To run tests, you can do 'python -m testtools.run tests'.
# To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will
# try to pick params.ini in PWD

from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
import test
import random
from tcutils.util import skip_because

class TestHitlessUpgrade(BaseFabricTest):

    @classmethod
    def setUpClass(cls):
        super(TestHitlessUpgrade, cls).setUpClass()
        cls.swift_h = cls.connections.swift_h

    @classmethod
    def tearDownClass(cls):
        super(TestHitlessUpgrade, cls).tearDownClass()

    def create_device_image_object(self):
        hitless_upgrade_input = self.inputs.hitless_upgrade_input
        required_device_images = []
        for image in hitless_upgrade_input.get('image_upgrade_list', []):
            image_name = image.get('image')
            required_device_images.append(image_name)
        self.image_info = self.swift_h.get_object_uri(required_device_images)
        for image, info in self.image_info.items():
            supported_platforms = info.get('supported_platforms', '')
            file_uri = info.get('public_file_uri', None)
            device_family = info.get('device_family', 'junos-qfx')
            os_version = info.get('os_version', None)
            try:
                uuid = self.vnc_h.get_device_image(
                    ['default-global-system-config', image])
            except Exception as e:
                uuid = self.vnc_h.create_device_image(display_name=image,
                                               image_uri=file_uri,
                                               supported_platforms=supported_platforms,
                                               device_family=device_family,
                                               os_version=os_version)
                self.addCleanup(self.vnc_h.delete_device_image, fq_name=[
                                'default-global-system-config', image])
                self.logger.info("Device_Manager: create device image {}".format(uuid))
            finally:
                info['uuid'] = uuid

    @skip_because(function='filter_bms_nodes', bms_type='multi_homing')
    @skip_because(bms=2)
    @preposttest_wrapper
    def test_hitless_upgrade(self):
        self.create_device_image_object()
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        bms_nodes = self.get_bms_nodes()
        self.bms1 = self.create_bms(bms_name=bms_nodes[0],
                                tor_port_vlan_tag=10,
                                vn_fixture=vn1)
        self.bms2 = self.create_bms(bms_name=bms_nodes[1],
                                    tor_port_vlan_tag=20,
                                    vn_fixture=vn2)
        self.create_logical_router([vn1, vn2])
        assert self.bms1.ping_with_certainty(self.bms2.bms_ip, expectation=True)
        exec_id, status = \
            self.hitless_upgrade_strategy(self.devices,
                                fabric_uuid=self.fabric.uuid,
                                hitless_upgrade_input=self.inputs.hitless_upgrade_input)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.sleep(90)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        self.sleep(90)
        assert self.bms1.ping_with_certainty(
            self.bms2.bms_ip, expectation=True)
