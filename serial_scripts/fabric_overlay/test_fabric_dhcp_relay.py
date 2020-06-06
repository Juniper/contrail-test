from __future__ import absolute_import
import test
import random
from netaddr import *
from builtins import str
from tcutils.util import skip_because
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest

class TestFabricDHCPRelay(BaseFabricTest):
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
            if len(self.get_bms_nodes()) > 1:
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
        bms_fixtures = list(); bms_vns = dict()
        bms_nodes = self.get_bms_nodes()

        dhcp_server_vn = self.create_vn()
        vn2 = self.create_vn()
        vn3 = self.create_vn()
        dhcp_server_bms = self.create_bms(bms_nodes[0],
            tor_port_vlan_tag=21, vn_fixture=dhcp_server_vn)
        lr = self.create_logical_router([dhcp_server_vn, vn2, vn3],
            dhcp_relay_servers=[dhcp_server_bms.bms_ip])
        self.start_dhcp_server(dhcp_server_bms, [vn2, vn3])
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
        self.start_dhcp_server(dhcp_server_bms, [vn2, vn3])
        assert bms1.run_dhclient(expectation=False)
        lr.update(dhcp_relay_servers=[old_server_ip, new_server_ip])
        self.sleep(60)
        assert bms1.run_dhclient()
        lr.update(dhcp_relay_servers=[new_server_ip])
        self.sleep(60)
        assert bms1.run_dhclient()
        dhcp_server_vn_2 = self.create_vn()
        lr.add_interface([dhcp_server_vn_2.vn_id])
        self.addCleanup(lr.remove_interface, [dhcp_server_vn_2.vn_id])
        dhcp_server_bms_2 = self.create_bms(bms_nodes[0],
            vlan_id=22, vn_fixture=dhcp_server_vn_2,
            bond_name=dhcp_server_bms.bond_name,
            port_group_name=dhcp_server_bms.port_group_name)
        self.start_dhcp_server(dhcp_server_bms_2, [vn2, vn3])
        lr.update(dhcp_relay_servers=[new_server_ip, dhcp_server_bms_2.bms_ip])
        self.sleep(60)
        assert bms1.run_dhclient()
        self.stop_dhcp_server(dhcp_server_bms)
        assert bms1.run_dhclient()
