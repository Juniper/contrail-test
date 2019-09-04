import test
import uuid
import copy
import random
from netaddr import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.dci_base import BaseDCIFabric 
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *

class TestFabricDCI(BaseDCIFabric):
    @preposttest_wrapper
    def test_fabric_dci_basic(self):
        self.config_2_dc(dc_asn=64512)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        #self.setup_bare_metal()
        #for bms in self.get_bms_nodes():
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = '00:e0:81:ce:80:60', fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = 'a0:42:3f:01:af:76',fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = '122.195.137.3')

    @preposttest_wrapper
    def test_fabric_dci_inter_asn(self):
        self.config_2_dc(dc_asn=64515)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        #self.setup_bare_metal()
        #for bms in self.get_bms_nodes():
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = '00:e0:81:ce:80:60',fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = 'a0:42:3f:01:af:76',fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = '122.195.137.3')
