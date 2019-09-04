import test
import uuid
import copy
import random
from netaddr import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.dci_base import BaseDCIFabric 
from tcutils.util import get_random_ip
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
        bms1_ip = get_random_ip(vn.vn_subnets[0]['cidr'])
        bms2_ip = get_random_ip(vn1.vn_subnets[0]['cidr'])
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[0].values()[1][0].values()[1], fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[1].values()[1][0].values()[1],fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1, bms1_ip, bms2_ip)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = bms2_ip)

    #this case is for ebgp where 2nd fabric is in another ASN
    @preposttest_wrapper
    def test_fabric_dci_inter_asn(self):
        self.config_2_dc(dc_asn=64515)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        bms1_ip = get_random_ip(vn.vn_subnets[0]['cidr'])
        bms2_ip = get_random_ip(vn1.vn_subnets[0]['cidr'])
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[0].values()[1][0].values()[1], fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[1].values()[1][0].values()[1],fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1, bms1_ip, bms2_ip)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = bms2_ip)

    @preposttest_wrapper
    def test_fabric_dci__ibgp_restart(self):
        self.config_2_dc(dc_asn=64512)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        bms1_ip = get_random_ip(vn.vn_subnets[0]['cidr'])
        bms2_ip = get_random_ip(vn1.vn_subnets[0]['cidr'])
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[0].values()[1][0].values()[1], fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[1].values()[1][0].values()[1],fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1, bms1_ip, bms2_ip)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = bms2_ip)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        assert bms_fixtures[0].ping(ip = bms2_ip)

    @preposttest_wrapper
    def test_fabric_dci_ebgp_restart(self):
        self.config_2_dc(dc_asn=64515)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vn1 = self.create_vn()
        bms1_ip = get_random_ip(vn.vn_subnets[0]['cidr'])
        bms2_ip = get_random_ip(vn1.vn_subnets[0]['cidr'])
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[0],
            vn_fixture=vn, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[0].values()[1][0].values()[1], fabric_fixture = self.fabric1))
        bms_fixtures.append(self.create_bms(bms_name=self.get_bms_nodes()[1],
            vn_fixture=vn1, tor_port_vlan_tag=10, bms_mac = self.inputs.inputs.bms_data.values()[1].values()[1][0].values()[1],fabric_fixture = self.fabric2))
        self.setup_bare_metal(vn, vn1, bms1_ip, bms2_ip)
        self.config_dci(vn, vn1)
        assert bms_fixtures[0].ping(ip = bms2_ip)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        assert bms_fixtures[0].ping(ip = bms2_ip)
