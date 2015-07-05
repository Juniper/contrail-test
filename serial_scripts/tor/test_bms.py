# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time

from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.tor.base import *
from physical_router_fixture import PhysicalRouterFixture
import test
from tcutils.util import *


class TestTor(BaseTorTest):

    @classmethod
    def setUpClass(cls):
        super(TestTor, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestTor, cls).tearDownClass()

    def is_test_applicable(self):
        #if os.environ.get('MX_GW_TEST') != '1':
        #    return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        if len(self.inputs.tor_data.keys()) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)


    def one_kvm_one_bms_test(self, tor_id, vlan_id=0):
        '''Common test code for one kvm and one bms test
        '''
        vn1_fixture = self.create_vn(disable_dns=True)

        tor_dict, tor_1_info = self.get_tor_info(tor_id=tor_id)
        bms_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)
        bms_mac = '00:00:00:00:00:01'
        vm_mac = '00:00:00:00:00:0a'
        
        # BMS VMI
        vmis=[self.setup_vmi(vn1_fixture.uuid, 
                mac_address=bms_mac,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'], 
                            'ip_address': bms_ip,
                          }])
             ]

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     mac_address=vm_mac)
        vm1_fixture = self.create_vm(vn1_fixture, port_ids=[port1_obj['id']])
        self.setup_tor_port(tor_1_info.uuid, tor_dict, port_index=0, 
                            vlan_id=vlan_id, vmi_objs=vmis)
        bms_fixture = self.setup_bms(tor_dict, port_index=0, 
                                     ns_mac_address=bms_mac, vlan_id=vlan_id)
        
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(bms_ip),\
            self.logger.error('Unable to ping BMS IP %s from VM %s' % (
                bms_ip, vm1_fixture.vm_ip))
        self.logger.info('Ping from openstack VM to BMS IP passed')                          

        # Validate arps are learnt on the BMS/VM
        (ip1, mac1) = bms_fixture.get_arp_entry(ip_address=vm1_fixture.vm_ip)
        (ip2, mac2) = vm1_fixture.get_arp_entry(ip_address=bms_ip)
        assert mac2 == bms_mac, (
            "Arp of BMS IP %s in VM : %s. Expected : %s!" % (
                bms_ip, mac2, bms_mac))
        assert mac1 == vm_mac, (
            "Arp of VM IP %s in BMS : %s. Expected : %s!" % (
                vm1_fixture.vm_ip, mac1, vm_mac))


    @preposttest_wrapper
    def test_ping_between_kvm_vm_and_untagged_bms(self):
        '''Validate ping between a KVM VM and a untagged BMS

        '''
        self.one_kvm_one_bms_test(tor_id='1', vlan_id=0)

    # end test_ping_between_kvm_vm_and_untagged_bms

    @preposttest_wrapper
    def test_ping_between_kvm_vm_and_tagged_bms(self):
        '''Validate ping between a KVM VM and a tagged BMS

        '''
        self.one_kvm_one_bms_test(tor_id='2', vlan_id=10)

    # end test_ping_between_kvm_vm_and_tagged_bms

    @preposttest_wrapper
    def test_ping_between_two_tors_intra_vn(self):
        vlan_id = 0
        vn1_fixture = self.create_vn(disable_dns=True)

        tor1_dict, tor_1_info = self.get_tor_info(tor_id='1')
        tor2_dict, tor_2_info = self.get_tor_info(tor_id='2')
        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)
        bms1_mac = '00:00:00:00:00:01'
        bms2_mac = '00:00:00:00:00:02'

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid,
                mac_address=bms1_mac,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }],
                count=2)
        self.setup_tor_port(tor_1_info.uuid, tor1_dict, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vmis[0]])
        self.setup_tor_port(tor_2_info.uuid, tor2_dict, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(tor1_dict, port_index=0,
                                     ns_mac_address=bms1_mac)
        bms2_fixture = self.setup_bms(tor2_dict, port_index=0,
                                     ns_mac_address=bms2_mac)

        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Validate arps are learnt on the BMSs
        (ip1, mac1) = bms1_fixture.get_arp_entry(ip_address=bms2_ip)
        (ip2, mac2) = bms2_fixture.get_arp_entry(ip_address=bms1_ip)
        assert mac1==bms2_mac, (
            "Found %s instead of %s" % (mac1, bms2_mac))
        assert mac2==bms1_mac, (
            "Found %s instead of %s" % (mac2, bms1_mac))

    # end test_ping_between_two_tors_intra_vn


    @preposttest_wrapper
    def test_add_remove_vmi_from_tor_lif(self):
        '''Validate addition and removal of VMI from the ToR Lif

        Add a VMI(for BMS) to a ToR lif
        Check if BMS connectivity is fine
        Remove the VMI from the lif
        Check if BMS connectivity is broken
        Add the VMI back again
        Check if BMS connectivity is restored
        '''
        vlan_id = 1
        vn1_fixture = self.create_vn(disable_dns=True)

        tor1_dict, tor_1_info = self.get_tor_info(tor_id='1')
        tor2_dict, tor_2_info = self.get_tor_info(tor_id='2')
        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }],
                count=2)
        (pif1_obj, lif1_obj) = self.setup_tor_port(tor_1_info.uuid, tor1_dict,
            port_index=0, vlan_id=vlan_id, vmi_objs=[vmis[0]])
        (pif2_obj, lif2_obj) = self.setup_tor_port(tor_2_info.uuid, tor2_dict,
            port_index=0, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(tor1_dict, port_index=0,
                                     ns_mac_address=vmis[0].mac_address,
                                     vlan_id=vlan_id)
        bms2_fixture = self.setup_bms(tor2_dict, port_index=0,
                                     ns_mac_address=vmis[1].mac_address)

        # Remove first bms' vmi from lif
        lif1_obj.delete_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip, expectation=False)

        # Add the bms' vmi back to lif 
        lif1_obj.add_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_ping_between_two_tors_intra_vn

    @preposttest_wrapper
    def test_no_dhcp_for_unknown_bms(self):
        '''Validate that no dhcp succeeds for a BMS which is not mapped to a lif

        Do not add the BMS to the lif
        '''
        vlan_id = 1
        vn1_fixture = self.create_vn(disable_dns=True)

        tor1_dict, tor_1_info = self.get_tor_info(tor_id='1')
        tor2_dict, tor_2_info = self.get_tor_info(tor_id='2')
        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }],
                count=2)
        (pif1_obj, lif1_obj) = self.setup_tor_port(tor_1_info.uuid, tor1_dict,
            port_index=0, vlan_id=vlan_id, vmi_objs=[vmis[0]])
        (pif2_obj, lif2_obj) = self.setup_tor_port(tor_2_info.uuid, tor2_dict,
            port_index=0, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(tor1_dict, port_index=0,
                                     ns_mac_address=vmis[0].mac_address,
                                     vlan_id=vlan_id)
        bms2_fixture = self.setup_bms(tor2_dict, port_index=0,
                                     ns_mac_address=vmis[1].mac_address)

        # Remove first bms' vmi from lif
        lif1_obj.delete_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip, expectation=False)

        # Add the bms' vmi back to lif 
        lif1_obj.add_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_ping_between_two_tors_intra_vn

# end classs TestTor


class TestBMSInterVN(BaseTorTest):

    @classmethod
    def setUpClass(cls):
        super(TestBMSInterVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBMSInterVN, cls).tearDownClass()

    def is_test_applicable(self):
        #if os.environ.get('MX_GW_TEST') != '1':
        #    return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        if len(self.inputs.physical_routers_data.keys()) < 1 :
            return (False, 'Skipping Test. Alteast 1 physical router required',
                    'in the test cluster')
        if len(self.inputs.tor_data.keys()) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)

    def setUp(self):
        super(TestBMSInterVN, self).setUp()
        router_params = self.inputs.physical_routers_data.values()[0]
        self.phy_router_fixture = self.useFixture(PhysicalRouterFixture(
            router_params['name'], router_params['mgmt_ip'],
            model=router_params['model'],
            vendor=router_params['vendor'],
            asn=router_params['asn'],
            ssh_username=router_params['ssh_username'],
            ssh_password=router_params['ssh_password'],
            mgmt_ip=router_params['mgmt_ip'],
            tunnel_ip=router_params['tunnel_ip'],
            ports=router_params['ports'],
            connections=self.connections))

    def cleanUp(self):
        super(TestBMSInterVN, self).cleanUp()

    @preposttest_wrapper
    def test_ping_between_two_tors_inter_vn(self):
        ''' Create two vns
            Have two bmss in each of those vns
            Apply policy between vns to allow all traffic
            Validate ping between the bmss
            Validate arp of gateway IP on the bmss
        '''
        vlan_id = 0
        vn1_fixture = self.create_vn(disable_dns=True)
        vn2_fixture = self.create_vn(disable_dns=True)
        self.allow_all_traffic_between_vns(vn1_fixture, vn2_fixture)

        tor1_dict, tor_1_info = self.get_tor_info(tor_id='1')
        tor2_dict, tor_2_info = self.get_tor_info(tor_id='2')
        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn2_fixture.vn_subnet_objs[0]['cidr'],3)
        bms1_mac = '00:00:00:00:00:01'
        bms2_mac = '00:00:00:00:00:02'

        # BMS VMI
        vn1_vmi=self.setup_vmi(vn1_fixture.uuid,
                mac_address=bms1_mac,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }])
        vn2_vmi=self.setup_vmi(vn2_fixture.uuid,
                mac_address=bms2_mac,
                fixed_ips=[{'subnet_id': vn2_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms2_ip,
                          }])
        self.setup_tor_port(tor_1_info.uuid, tor1_dict, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vn1_vmi])
        self.setup_tor_port(tor_2_info.uuid, tor2_dict, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vn2_vmi])
        bms1_fixture = self.setup_bms(tor1_dict, port_index=0,
                                     ns_mac_address=bms1_mac)
        bms2_fixture = self.setup_bms(tor2_dict, port_index=0,
                                     ns_mac_address=bms2_mac)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_router(vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_router(vn2_fixture, self.phy_router_fixture)
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Validate that the GW Macs of the BMSs is the MX MAC
        bms1_gw_mac = bms1_fixture.get_gateway_mac()
        bms2_gw_mac = bms2_fixture.get_gateway_mac()
        assert bms1_gw_mac == bms2_gw_mac, (
            "BMS Gateway MACs mismatch! They are %s and %s" % (
                bms1_gw_mac, bms2_gw_mac))
            
    # end test_ping_between_two_tors_inter_vn
