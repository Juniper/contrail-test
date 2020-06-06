from __future__ import absolute_import
import test
import random
from netaddr import *
from builtins import str
from tcutils.util import skip_because, get_an_ip
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest

class TestFabricDHCPRelay(BaseFabricTest):
    rb_role = None
    enterprise_style = True
    server_leafs = None
    @classmethod
    def setUpClass(cls):
        super(TestFabricDHCPRelay, cls).setUpClass()
        cls.backup_csn_nodes = cls.inputs.get_csn()
        cls.inputs.set_csn([])

    @classmethod
    def tearDownClass(cls):
        cls.inputs.set_csn(cls.backup_csn_nodes)
        super(TestFabricDHCPRelay, cls).tearDownClass()

    def is_test_applicable(self):
        result, msg = super(TestFabricDHCPRelay,
                            self).is_test_applicable()
        if result:
            msg = 'Need atleast 2 BMS nodes'
            if len(self.get_bms_nodes(rb_role=self.rb_role)) > 1:
                return (True, None)
        return False, msg

    @preposttest_wrapper
    def test_dhcp_relay_same_lr(self):
        '''
           Create VN vn1, vn2, vn3
           Create Logical Router and add all the VNs
           Create untagged BMS instance on BMS1 of VN vn1
           Start DHCP server on BMS1 serving vn2 and vn3
           Create 2 BMS instances on BMS2 of vn2 and vn3
           Check if the instances can get ip via DHCP
           Add additional BMS instance, if available, and test multiple dhcp clients
           Change the DHCP server ip and see if dhcp fails
           Update the LR with both the old dhcp-server ip and new one
           Clients should be able to get dhcp ip
           Create another VN dhcp-server-vn-2
           Create a BMS instance on BMS1 of dhcp-server-vn-2
           Update the LR to point to both the dhcp-servers
           Clients should be able to get dhcp ip
           Delete the old dhcp server
           Clients should still be able to get dhcp ip from new server
        '''
        bms_nodes = self.get_bms_nodes(rb_role=self.rb_role)

        dhcp_server_vn = self.create_vn()
        vn2 = self.create_vn()
        vn3 = self.create_vn()
        dhcp_server_bms = self.create_bms(bms_nodes[0],
            tor_port_vlan_tag=21, vn_fixture=dhcp_server_vn, static_ip=True)
        lr = self.create_logical_router([dhcp_server_vn, vn2, vn3],
            dhcp_relay_servers=[dhcp_server_bms.bms_ip],
            devices=self.server_leafs)
        self.start_dhcp_server([vn2, vn3], dhcp_server_bms)
        bms1 = self.create_bms(bms_nodes[1], vlan_id=31,
            vn_fixture=vn2, external_dhcp_server=True)
        bms2 = self.create_bms(bms_nodes[1], vlan_id=32,
            vn_fixture=vn3, external_dhcp_server=True,
            bond_name=bms1.bond_name,
            port_group_name=bms1.port_group_name)
        self.do_ping_test(bms1, bms2.bms_ip)
        if len(bms_nodes) > 2:
            bms3 = self.create_bms(bms_nodes[2], tor_port_vlan_tag=31,
                vn_fixture=vn2, external_dhcp_server=True)
            self.do_ping_test(bms3, bms2.bms_ip)
            self.do_ping_test(bms3, bms1.bms_ip)
        old_server_ip = dhcp_server_bms.bms_ip
        new_server_ip = str(IPAddress(old_server_ip)+4)
        self.stop_dhcp_server(dhcp_server_bms)
        dhcp_server_bms.assign_static_ip(v4_ip=new_server_ip,
            v4_gw_ip=dhcp_server_bms.bms_gw_ip, flush=True)
        self.start_dhcp_server([vn2, vn3], dhcp_server_bms)
        assert bms1.run_dhclient(expectation=False)[0]
        lr.update(dhcp_relay_servers=[old_server_ip, new_server_ip])
        self.sleep(60)
        assert bms1.run_dhclient()[0]
        lr.update(dhcp_relay_servers=[new_server_ip])
        self.sleep(60)
        assert bms1.run_dhclient()[0]
        dhcp_server_vn_2 = self.create_vn()
        lr.add_interface([dhcp_server_vn_2.vn_id])
        self.addCleanup(lr.remove_interface, [dhcp_server_vn_2.vn_id])
        dhcp_server_bms_2 = self.create_bms(bms_nodes[0],
            vlan_id=22, vn_fixture=dhcp_server_vn_2,
            bond_name=dhcp_server_bms.bond_name, static_ip=True,
            port_group_name=dhcp_server_bms.port_group_name)
        self.start_dhcp_server([vn2, vn3], dhcp_server_bms_2)
        lr.update(dhcp_relay_servers=[new_server_ip, dhcp_server_bms_2.bms_ip])
        self.sleep(60)
        assert bms1.run_dhclient()[0]
        self.stop_dhcp_server(dhcp_server_bms)
        self.start_dhcp_server([vn2, vn3], dhcp_server_bms_2)
        assert bms1.run_dhclient()[0]
        lr.update(dhcp_relay_servers=[])
        self.sleep(60)
        assert bms1.run_dhclient(expectation=False)[0]
        lr.update(dhcp_relay_servers=[dhcp_server_bms_2.bms_ip])
        self.sleep(60)
        assert bms1.run_dhclient()[0]
        self.perform_cleanup(lr)
        self.sleep(60)
        assert bms1.run_dhclient(expectation=False)[0]

    @preposttest_wrapper
    def test_dhcp_relay_multiple_lr(self):
        '''
           Create VN relay_server_vn1, relay_server_vn2, vn1, vn2
           Create 2 Logical Routers and add respective VNs
           Create untagged BMS instances on BMS1 of VN relay_server_vn1, relay_server_vn2
           Start DHCP servers on BMS1 serving respective VNs
           Create 2 BMS instances on BMS2 of vn1 and vn2
           Check if the instances can get ip via DHCP
           Add additional BMS instance, if available, and test multiple dhcp clients
        '''
        bms_nodes = self.get_bms_nodes(rb_role=self.rb_role)
        dhcp_server_vn_1 = self.create_vn()
        dhcp_server_vn_2 = self.create_vn()
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        dhcp_server_bms_1 = self.create_bms(bms_nodes[0],
            tor_port_vlan_tag=2, vn_fixture=dhcp_server_vn_1)
        dhcp_server_bms_2 = self.create_bms(bms_nodes[0],
            vlan_id=3, vn_fixture=dhcp_server_vn_2,
            bond_name=dhcp_server_bms_1.bond_name,
            port_group_name=dhcp_server_bms_1.port_group_name)
        lr1 = self.create_logical_router([dhcp_server_vn_1, vn1],
            dhcp_relay_servers=[dhcp_server_bms_1.bms_ip],
            devices=self.server_leafs)
        lr2 = self.create_logical_router([dhcp_server_vn_2, vn2],
            dhcp_relay_servers=[dhcp_server_bms_2.bms_ip],
            devices=self.server_leafs)
        self.start_dhcp_server([vn1], dhcp_server_bms_1)
        self.start_dhcp_server([vn2], dhcp_server_bms_2)
        bms1 = self.create_bms(bms_nodes[1], vlan_id=5,
            vn_fixture=vn1, external_dhcp_server=True)
        bms2 = self.create_bms(bms_nodes[1], vlan_id=6,
            vn_fixture=vn2, external_dhcp_server=True,
            bond_name=bms1.bond_name,
            port_group_name=bms1.port_group_name)
        self.do_ping_test(bms1, dhcp_server_bms_1.bms_ip)
        self.do_ping_test(bms2, dhcp_server_bms_2.bms_ip)
        if len(bms_nodes) > 2:
            bms3_1 = self.create_bms(bms_nodes[2], tor_port_vlan_tag=5,
                vn_fixture=vn1, external_dhcp_server=True)
            bms3_2 = self.create_bms(bms_nodes[2], vlan_id=6,
                vn_fixture=vn2, external_dhcp_server=True,
                bond_name=bms3_1.bond_name,
                port_group_name=bms3_1.port_group_name)
            self.do_ping_test(bms3_1, bms1.bms_ip)
            self.do_ping_test(bms3_2, bms2.bms_ip)
        self.perform_cleanup(lr1)
        self.sleep(60)
        assert bms1.run_dhclient(expectation=False)[0]
        assert bms2.run_dhclient()[0]

    @preposttest_wrapper
    def test_dhcp_relay_default_inet(self):
        '''
           Create VNs vn1, vn2
           Create a Logical Router and add respective VNs
           Configure dhcp server on a BMS instance
           Configure the QFX server accordingly
           Create 2 BMS instances on BMS2 of vn1 and vn2
           Check if the instances can get ip via DHCP
           Add additional BMS instance, if available, and test multiple dhcp clients
        '''
        bms_nodes = self.get_bms_nodes(rb_role=self.rb_role)
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        dhcp_server_vn = '42.44.46.48/30'
        self.create_netns(bms_nodes[0], 'dhcp_test', dhcp_server_vn)
        lr1 = self.create_logical_router([vn1, vn2],
            dhcp_relay_servers=[get_an_ip(dhcp_server_vn, offset=2)],
            devices=self.server_leafs)
        self.start_dhcp_server([vn1, vn2], bms_node=bms_nodes[0])
        bms1 = self.create_bms(bms_nodes[1], vlan_id=5,
            vn_fixture=vn1, external_dhcp_server=True)
        bms2 = self.create_bms(bms_nodes[1], vlan_id=6,
            vn_fixture=vn2, external_dhcp_server=True,
            bond_name=bms1.bond_name,
            port_group_name=bms1.port_group_name)
        self.do_ping_test(bms1, bms2.bms_ip)
        if len(bms_nodes) > 2:
            bms3_1 = self.create_bms(bms_nodes[2], tor_port_vlan_tag=5,
                vn_fixture=vn1, external_dhcp_server=True)
            bms3_2 = self.create_bms(bms_nodes[2], vlan_id=6,
                vn_fixture=vn2, external_dhcp_server=True,
                bond_name=bms3_1.bond_name,
                port_group_name=bms3_1.port_group_name)
            self.do_ping_test(bms3_1, bms1.bms_ip)
            self.do_ping_test(bms3_2, bms2.bms_ip)
        self.perform_cleanup(lr1)
        self.sleep(60)
        assert bms1.run_dhclient(expectation=False)[0]

class TestSPStyleFabricDHCPRelay(TestFabricDHCPRelay):
    enterprise_style = False

class TestERBFabricDHCPRelay(TestFabricDHCPRelay):
    enterprise_style = True
    rb_role = 'erb_ucast_gw'
    def setUp(self):
        for device, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'leaf':
                if 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                    self.rb_roles[device] = ['ERB-UCAST-Gateway']
            elif device_dict['role'] == 'spine':
                self.rb_roles[device] = ['lean', 'Route-Reflector']
        super(TestERBFabricDHCPRelay, self).setUp()
        erb_leafs = list()
        for bms in self.get_bms_nodes(rb_role=self.rb_role):
            erb_leafs.extend(self.get_associated_prouters(bms))
        self.server_leafs = set(erb_leafs)
