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

from vn_test import VNFixture


class TestTor(BaseTorTest):

    @classmethod
    def setUpClass(cls):
        super(TestTor, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestTor, cls).tearDownClass()


    def setUp(self):
        super(TestTor, self).setUp()
        [self.tor1_fixture, self.tor2_fixture] = self.setup_tors(count=2)

    def is_test_applicable(self):
        #if os.environ.get('MX_GW_TEST') != '1':
        #    return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        if len(self.get_available_devices('tor')) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)


    def one_kvm_one_bms_test(self, tor_id, vlan_id=0):
        '''Common test code for one kvm and one bms test
        '''
        vn1_fixture = self.create_vn(disable_dns=True)

        tor_mgmt_ip = self.tor1_fixture.mgmt_ip
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
        self.setup_tor_port(self.tor1_fixture, port_index=0, 
                            vlan_id=vlan_id, vmi_objs=vmis)
        bms_fixture = self.setup_bms(self.tor1_fixture, port_index=0, 
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

        vrouter_mac = '00:00:5e:00:01:00'
        vm1_gw_mac = vm1_fixture.get_gateway_mac()
        assert vrouter_mac == vm1_gw_mac, (
            "GW MAC of VM %s not right. Expected : %s, Got : %s" % (
                vm1_fixture.vm_name, vrouter_mac, vm1_gw_mac))


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
        '''
        Create two tagged BMSs on two TORs in the same VN
        Test ping between them
        Validate that the MACs are resolved correctly for each others' IP
        '''
        vlan_id = 0
        vn1_fixture = self.create_vn(disable_dns=True)

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
        self.setup_tor_port(self.tor1_fixture, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vmis[0]])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
                                     ns_mac_address=bms1_mac)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
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
        vlan_id = 10
        vn1_fixture = self.create_vn(disable_dns=True)

        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }],
                count=2)
        (pif1_obj, lif1_obj) = self.setup_tor_port(self.tor1_fixture,
            port_index=0, vlan_id=vlan_id, vmi_objs=[vmis[0]])
        (pif2_obj, lif2_obj) = self.setup_tor_port(self.tor2_fixture,
            port_index=0, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
                                     ns_mac_address=vmis[0].mac_address,
                                     vlan_id=vlan_id)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
                                     ns_mac_address=vmis[1].mac_address)

        # Remove first bms' vmi from lif
        lif1_obj.delete_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip, expectation=False)

        # Add the bms' vmi back to lif 
        lif1_obj.add_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_add_remove_vmi_from_tor_lif

    @preposttest_wrapper
    def test_no_dhcp_for_unknown_bms(self):
        '''Validate that no dhcp succeeds for a BMS which is not mapped to a lif

        Do not add the BMS to the lif
        '''
        vlan_id = 11
        vn1_fixture = self.create_vn(disable_dns=True)

        bms1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],3)
        bms2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'],4)

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'],
                            'ip_address': bms1_ip,
                          }],
                count=2)
        (pif1_obj, lif1_obj) = self.setup_tor_port(self.tor1_fixture,
            port_index=0, vlan_id=vlan_id, vmi_objs=[vmis[0]])
        (pif2_obj, lif2_obj) = self.setup_tor_port(self.tor2_fixture,
            port_index=0, vmi_objs=[vmis[1]])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
                                     ns_mac_address=vmis[0].mac_address,
                                     vlan_id=vlan_id)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
                                     ns_mac_address=vmis[1].mac_address)

        # Remove first bms' vmi from lif
        lif1_obj.delete_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip, expectation=False)

        # Add the bms' vmi back to lif 
        lif1_obj.add_virtual_machine_interface(vmis[0].uuid) 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_ping_between_two_tors_intra_vn

# end classs TestTor

class TestVxlanID(BaseTorTest):
    @classmethod
    def setUpClass(cls):
        super(TestVxlanID, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVxlanID, cls).tearDownClass()

    def test_check_vxlan_id_reuse(self):
        ''' 
            Create VN and delete it and note the vxlan id
            On creating a VN again, verify that the vxlan id 
            associated with it the same (i.e vxlan id gets reused)
        '''
        vn_name = get_random_name('vn')
        vn_subnets = [get_random_cidr()]
        vn_obj = VNFixture(project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=vn_name,
            subnets=vn_subnets)
        vn_obj.setUp()
        vxlan_id = vn_obj.get_vxlan_id()
        vn_obj.cleanUp()

        vn_fixture = self.create_vn()
        new_vxlan_id = vn_fixture.get_vxlan_id()
        assert new_vxlan_id == vxlan_id, (
            "Vxlan ID reuse does not seem to happen",
            "Expected : %s, Got : %s" % (vxlan_id, new_vxlan_id))
        self.logger.info('Vxlan ids are reused..ok')
    # end test_check_vxlan_id_reuse



class TestBMSInterVN(BaseTorTest):
    ''' Validate InterVN routing with BMSs
        This set of cases requires 2 ToRs with 1 BMS each and 1 Router(mx)
    '''

    @classmethod
    def setUpClass(cls):
        super(TestBMSInterVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBMSInterVN, cls).tearDownClass()

    def is_test_applicable(self):
        #if os.environ.get('MX_GW_TEST') != '1':
        #    return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        if len(self.get_available_devices('router')) < 1 :
            return (False, 'Skipping Test. Alteast 1 physical router required',
                    'in the test cluster')
        if len(self.get_available_devices('tor')) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)

    def setUp(self):
        super(TestBMSInterVN, self).setUp()
        [self.phy_router_fixture] = self.setup_routers(count=1)
        [self.tor1_fixture, self.tor2_fixture] = self.setup_tors(count=2)

    def cleanUp(self):
        super(TestBMSInterVN, self).cleanUp()

    def common_two_tors_inter_vn_test(self, vxlan_mode='automatic'):
        vlan_id = 0
        if vxlan_mode == 'automatic':
            vn1_vxlan_id = None
            vn2_vxlan_id = None
        else:
            vn1_vxlan_id = get_random_vxlan_id()
            vn2_vxlan_id = get_random_vxlan_id()
        vn1_fixture = self.create_vn(disable_dns=True, vxlan_id=vn1_vxlan_id)
        vn2_fixture = self.create_vn(disable_dns=True, vxlan_id=vn2_vxlan_id)
        self.allow_all_traffic_between_vns(vn1_fixture, vn2_fixture)

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
        self.setup_tor_port(self.tor1_fixture, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vn1_vmi])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
                            vlan_id=vlan_id, vmi_objs=[vn2_vmi])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
                                     ns_mac_address=bms1_mac)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
                                     ns_mac_address=bms2_mac)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_router(vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_router(vn2_fixture, self.phy_router_fixture)
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # TODO 
        # Add GW MAC verification once ncclient libraries are used to talk to MX
        #
        #bms1_gw_mac = bms1_fixture.get_gateway_mac()
        #bms2_gw_mac = bms2_fixture.get_gateway_mac()
        #assert bms1_gw_mac == bms2_gw_mac, (
        #    "BMS Gateway MACs mismatch! They are %s and %s" % (
        #        bms1_gw_mac, bms2_gw_mac))
            

    @preposttest_wrapper
    def test_ping_between_two_tors_inter_vn(self):
        ''' Create two vns
            VxLan ID allocation is automatic
            Have two bmss in each of those vns
            Apply policy between vns to allow all traffic
            Validate ping between the bmss
            Validate arp of gateway IP on the bmss
        '''
        self.common_two_tors_inter_vn_test(vxlan_mode='automatic')
            
    # end test_ping_between_two_tors_inter_vn

    @preposttest_wrapper
    def test_configured_vxlan_id_inter_vn(self):
        ''' Create two vns with Vxlan id in Configured mode
            Have two bmss in each of those vns
            Apply policy between vns to allow all traffic
            Validate ping between the bmss
            Validate arp of gateway IP on the bmss
        '''
        self.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.vnc_lib_fixture.set_vxlan_mode, 'automatic')
        self.common_two_tors_inter_vn_test(vxlan_mode='configured')

