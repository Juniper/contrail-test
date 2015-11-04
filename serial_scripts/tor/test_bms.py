import os
import fixtures
import testtools
import time

from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.tor.base import *
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

        # Clear arps and check again
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_ping_between_two_tors_intra_vn

    @preposttest_wrapper
    def test_with_multiple_subnets(self):
        ''' Create a VN with two /29 subnets
            Create 5 VMIs on the VN so that 1st subnet IPs are exhausted
            Add lifs with 6th and 7th VMIs
            Validate that the BMSs get IP from 2nd subnet and ping passes
        '''
        vn_subnets = [ get_random_cidr('29'), get_random_cidr('29')]
        vn1_fixture = self.create_vn(vn_subnets=vn_subnets, disable_dns=True)
        port_fixtures = []
        for i in range(0, 7):
            port_fixtures.append(self.setup_vmi(vn1_fixture.uuid))

        self.setup_tor_port(self.tor1_fixture, port_index=0,
                            vmi_objs=[port_fixtures[5]])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
                            vmi_objs=[port_fixtures[6]])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
            ns_mac_address=port_fixtures[5].mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
            ns_mac_address=port_fixtures[6].mac_address)

        for bms in [bms1_fixture, bms2_fixture]:
            bms_ip = IPAddress(bms.info['inet_addr'])
            subnet_cidr = IPNetwork(vn_subnets[1])
            assert bms_ip in subnet_cidr, (
                'BMS does not seem to have got IP from second subnet'
                'BMS IP %s not in %s subnet' % (bms_ip, subnet_cidr))
            
        self.do_ping_test(bms1_fixture, bms1_fixture.info['inet_addr'],
                          bms2_fixture.info['inet_addr'])
    # end test_with_multiple_subnets

    @preposttest_wrapper
    def test_ovsdb_config_on_tor(self):
        ''' Associate VMI to a lif. Check that logical switch is created on ToR
            On disassociating VMI from lif, verify that the config
            is deleted from the tor
        '''
        result = True
        vn1_fixture = self.create_vn(disable_dns=True)
        (pif_fixture, lif_fixture) = self.setup_tor_port(self.tor1_fixture, 
            port_index=0)
        port_fixture = self.setup_vmi(vn1_fixture.uuid)
        lif_fixture.add_virtual_machine_interface(port_fixture.uuid)
        self.addCleanup(lif_fixture.delete_virtual_machine_interface,
            port_fixture.uuid)

        # Check on Tor that the logical switch has got created
        if not self.tor1_fixture.is_logical_switch_present(vn1_fixture.uuid):
            result = result and False

        lif_fixture.delete_virtual_machine_interface(port_fixture.uuid)
        if not self.tor1_fixture.is_logical_switch_present(vn1_fixture.uuid,
            expectation=False):
            result = result and False

        assert result, 'Logical Switch verification on ToR failed'
    # end test_ovsdb_config_removal_on_delete

    @preposttest_wrapper
    def test_two_vmis_on_lif(self):
        vn1_fixture = self.create_vn(disable_dns=True)

        # BMS VMI
        vmis=self.setup_vmis(vn1_fixture.uuid, count=3)
        (pif_fixture, lif_fixture) = self.setup_tor_port(
            self.tor1_fixture,
            vmi_objs=[vmis[0]])
        self.setup_tor_port(self.tor2_fixture, vmi_objs=[vmis[1]])

        bms1_fixture = self.setup_bms(self.tor1_fixture,
                                     ns_mac_address=vmis[0].mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture,
                                     ns_mac_address=vmis[1].mac_address)
        bms3_fixture = self.setup_bms(self.tor1_fixture,
                                     namespace='ns2',
                                     ns_mac_address=vmis[2].mac_address,
                                     verify=False)

        # Validate the DHCP for bms3 fails
        (dh_result, dhcp_output) = bms3_fixture.run_dhclient(timeout=60)
        assert not dh_result, (
            'BMS should not have got a DHCP IP, it seems to have got one!')

        # Add the VMI for bms3 to the lif and check that dhcp works
        self.add_vmi_to_lif(lif_fixture, vmis[2].uuid)
        (dh_result, dhcp_output) = bms3_fixture.run_dhclient()
        assert dh_result, 'DHCP failed : %s' % (dhcp_output)

        bms3_ip = bms3_fixture.info['inet_addr']
        bms3_mac = bms3_fixture.info['hwaddr']
        self.do_ping_test(bms3_fixture, bms3_ip,
                          bms2_fixture.info['inet_addr'])

        # Validate that MAC of bms3 is learnt on bms2
        self.validate_arp(bms2_fixture, ip_address=bms3_ip, 
            expected_mac=bms3_fixture.info['hwaddr'])
    # end  test_two_vmis_on_lif

    @preposttest_wrapper
    def test_dhcp_flood_for_unknown_mac(self):
        '''
            On a lif, add a BMS
            Have a second BMS on the tor port, but unknown to Contrail
            Validate that DHCP discover packets from unknown BMSs 
            are flooded in the VN, by monitoring the pkts on a VM and BMS
        '''
        vn1_fixture = self.create_vn(disable_dns=True)

        vmi1=self.setup_vmi(vn1_fixture.uuid)
        vmi2=self.setup_vmi(vn1_fixture.uuid)
        vmi3=self.setup_vmi(vn1_fixture.uuid)
        vm1_fixture = self.create_vm(vn1_fixture)

        (pif1_obj, lif1_obj) = self.setup_tor_port(self.tor1_fixture,
            vmi_objs=[vmi1])
        (pif2_obj, lif2_obj) = self.setup_tor_port(self.tor2_fixture,
            vmi_objs=[vmi2])
        bms1_fixture = self.setup_bms(self.tor1_fixture, 
                                     ns_mac_address=vmi1.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture,
                                     ns_mac_address=vmi2.mac_address)
        bms3_fixture = self.setup_bms(self.tor1_fixture,
                                     namespace='ns2',
                                     ns_mac_address=vmi3.mac_address,
                                     verify=False)

        vm1_fixture.wait_till_vm_is_up()
        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']
        (result, message) = self.validate_dhcp_forwarding(bms3_fixture,
            bms2_fixture)
        assert result, message
        (result, message) = self.validate_dhcp_forwarding(bms3_fixture,
            bms1_fixture)
        assert result, message
        (result, message) = self.validate_dhcp_forwarding(bms3_fixture,
            vm1_fixture)
        assert result, message
    # end test_dhcp_flood_for_unknown_mac

    @preposttest_wrapper
    def test_arp_proxy_by_vrouter_for_vms(self):
        '''
            Have two BMSis and a VM in a VN
            From BMS, arp for the VM.
            Validate that arp does not reach the VM or the other BMS
            But the BMS should get a arp reply(from TSN)
        '''
        vn1_fixture = self.create_vn(disable_dns=True)

        vmi1=self.setup_vmi(vn1_fixture.uuid)
        vmi2=self.setup_vmi(vn1_fixture.uuid)
        vm1_fixture = self.create_vm(vn1_fixture)

        (pif1_obj, lif1_obj) = self.setup_tor_port(self.tor1_fixture,
            vmi_objs=[vmi1])
        (pif2_obj, lif2_obj) = self.setup_tor_port(self.tor2_fixture,
            vmi_objs=[vmi2])
        bms1_fixture = self.setup_bms(self.tor1_fixture, 
                                     ns_mac_address=vmi1.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture,
                                     ns_mac_address=vmi2.mac_address)

        vm1_fixture.wait_till_vm_is_up()
        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']
        (result, message) = self.validate_arp_forwarding(bms1_fixture,
            vm1_fixture.vm_ip, vm1_fixture)
        assert not result, message
        (result, message) = self.validate_arp_forwarding(bms1_fixture,
            vm1_fixture.vm_ip, bms2_fixture)
        assert not result, message

    @preposttest_wrapper
    def test_unknown_unicast_forwarding(self):
        '''
        Have a VM and a BMS on each ToR in a UUF-enabled VN
        Ping each other and check arp/mac is learnt
        Clear the MACs of the BMSs on the ToRs while the arps on the hosts
            are still present
        Validate that later pings between them are fine
        '''
        vn1_fixture = self.create_vn(disable_dns=True)
        vn1_fixture.set_unknown_unicast_forwarding(True)
        vm1_fixture = self.create_vm(vn1_fixture)

        vmi1=self.setup_vmi(vn1_fixture.uuid)
        vmi2=self.setup_vmi(vn1_fixture.uuid)
        self.setup_tor_port(self.tor1_fixture, vmi_objs=[vmi1])
        self.setup_tor_port(self.tor2_fixture, vmi_objs=[vmi2])
        bms1_fixture = self.setup_bms(self.tor1_fixture, 
            ns_mac_address=vmi1.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture,
            ns_mac_address=vmi2.mac_address)
        assert vm1_fixture.wait_till_vm_is_up()

        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']

        # Add static arps of each other
        bms1_fixture.add_static_arp(vm1_fixture.vm_ip,
            vm1_fixture.mac_addr.values()[0])
        bms1_fixture.add_static_arp(bms2_ip, bms2_fixture.info['hwaddr'])
        bms2_fixture.add_static_arp(bms1_ip, bms1_fixture.info['hwaddr'])
        bms2_fixture.add_static_arp(vm1_fixture.vm_ip,
            vm1_fixture.mac_addr.values()[0])
        vm1_fixture.add_static_arp(bms2_ip, bms2_fixture.info['hwaddr'])
        vm1_fixture.add_static_arp(bms1_ip, bms1_fixture.info['hwaddr'])

        # Clear MACs of the BMSs on the ToRs and test ping
        self.tor1_fixture.clear_mac(vn1_fixture.uuid, vmi1.mac_address)

        self.do_ping_test(vm1_fixture, vm1_fixture.vm_ip, bms1_ip)
        self.tor1_fixture.clear_mac(vn1_fixture.uuid, vmi1.mac_address)
        self.tor2_fixture.clear_mac(vn1_fixture.uuid, vmi2.mac_address)
        self.do_ping_test(bms2_fixture, bms2_ip, bms1_ip)

        self.tor2_fixture.clear_mac(vn1_fixture.uuid, vmi2.mac_address)
        self.do_ping_test(vm1_fixture, vm1_fixture.vm_ip, bms2_ip)
        self.tor1_fixture.clear_mac(vn1_fixture.uuid, vmi1.mac_address)
        self.tor2_fixture.clear_mac(vn1_fixture.uuid, vmi2.mac_address)
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_unknown_unicast_forwarding
        

    @preposttest_wrapper
    def test_enable_disable_unknown_unicast_forwarding(self):
        ''' 
            Validate that UUF is disabled by default
            After enabling it, validate that these packets are flooded
        '''
        vn1_fixture = self.create_vn(disable_dns=True)
        vm1_fixture = self.create_vm(vn1_fixture)

        vmi1=self.setup_vmi(vn1_fixture.uuid)
        self.setup_tor_port(self.tor1_fixture, vmi_objs=[vmi1])
        bms1_fixture = self.setup_bms(self.tor1_fixture, 
            ns_mac_address=vmi1.mac_address)
        assert vm1_fixture.wait_till_vm_is_up()

        bms1_ip = bms1_fixture.info['inet_addr']

        # Add static arps of each other
        bms1_fixture.add_static_arp(vm1_fixture.vm_ip,
            vm1_fixture.mac_addr.values()[0])
        vm1_fixture.add_static_arp(bms1_ip, bms1_fixture.info['hwaddr'])

        # Clear MACs of the BMSs on the ToRs and check that ping fail
        self.tor1_fixture.clear_mac(vn1_fixture.uuid, vmi1.mac_address)
        self.do_ping_test(vm1_fixture, vm1_fixture.vm_ip, bms1_ip, 
            expectation=False)

        # Enable UUF and check that ping passes
        vn1_fixture.set_unknown_unicast_forwarding(True)
        self.tor1_fixture.clear_mac(vn1_fixture.uuid, vmi1.mac_address)
        self.do_ping_test(bms1_fixture, bms1_ip, vm1_fixture.vm_ip)
    # end test_enable_disable_unknown_unicast_forwarding

# end classs TestTor

class TestVxlanID(BaseTorTest):
    @classmethod
    def setUpClass(cls):
        super(TestVxlanID, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVxlanID, cls).tearDownClass()

    def setUp(self):
        super(TestVxlanID, self).setUp()
        [self.tor1_fixture] = self.setup_tors(count=1)

    @preposttest_wrapper
    def test_diff_vns_but_same_vxlan_id(self):
        '''
            Create a VN and port
            Bind port to a lif and check BMS gets an IP
            Delete the port and VN 
            Repeat the above steps n times
            This makes sure that consecutive vns continue to 
            get applied on the ToR with same Vxlan id
            Refer Bug 1466731 
        
        '''
        iterations = 10
        old_vxlan_id = None
        for i in range(0, iterations):
            vn_fixture = self.create_vn(disable_dns=True,cleanup=False)
            current_vxlan_id = vn_fixture.get_vxlan_id()
            if not old_vxlan_id:
                old_vxlan_id = current_vxlan_id
                
            port_fixture = self.setup_vmi(vn_fixture.uuid, cleanup=False)
            (pif_fixture, lif_fixture) = self.setup_tor_port(
                self.tor1_fixture,
                port_index=0,
                vmi_objs=[port_fixture], cleanup=False)
            bms1_fixture = self.setup_bms(self.tor1_fixture,
                port_index=0,
                ns_mac_address=port_fixture.mac_address,
                cleanup=False, 
                verify=False)
            bms1_fixture.run_dhclient(timeout=20)
            bms_ip = bms1_fixture.info['inet_addr']
            bms1_fixture.cleanUp()
            lif_fixture.cleanUp()
            pif_fixture.cleanUp()
            port_fixture.cleanUp()
            vn_fixture.cleanUp()
            assert current_vxlan_id == old_vxlan_id, "Vxlan id reuse not \
                happening. Current : %s, Earlier : %s" % (current_vxlan_id, 
                                                          old_vxlan_id) 
            assert bms_ip, "BMS did not get an IP"
        # end for
    # end test_diff_vns_but_same_vxlan_id
                
    @preposttest_wrapper
    def test_check_vxlan_id_reuse(self):
        ''' 
            Create a VN X 
            Create another VN Y and check that the VNid is the next number 
            Delete the two Vns
            On creating a VN again, verify that Vxlan id of X is used
             (i.e vxlan id gets reused)
        '''
        vn1_name = get_random_name('vn')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn')
        vn2_subnets = [get_random_cidr()]

        # First VN
        vn1_obj = VNFixture(project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=vn1_name,
            subnets=vn1_subnets)
        vn1_obj.setUp()
        vxlan_id1 = vn1_obj.get_vxlan_id()

        # Second VN
        vn2_obj = VNFixture(project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=vn2_name,
            subnets=vn2_subnets)
        vn2_obj.setUp()
        vxlan_id2 = vn2_obj.get_vxlan_id()

        assert vxlan_id2 == (vxlan_id1+1), (
            "Vxlan ID allocation is not incremental, "
            "Two VNs were seen to have vxlan ids %s, %s" % (
                vxlan_id1, vxlan_id2))
        # Delete the vns
        vn1_obj.cleanUp()
        vn2_obj.cleanUp()

        vn3_fixture = self.create_vn()
        assert vn3_fixture.verify_on_setup(), "VNFixture verify failed!"
        new_vxlan_id = vn3_fixture.get_vxlan_id()
        assert new_vxlan_id == vxlan_id1, (
            "Vxlan ID reuse does not seem to happen",
            "Expected : %s, Got : %s" % (vxlan_id1, new_vxlan_id))
        self.logger.info('Vxlan ids are reused..ok')
    # end test_check_vxlan_id_reuse

class TwoToROneRouterBase(BaseTorTest):
    @classmethod
    def setUpClass(cls):
        super(TwoToROneRouterBase, cls).setUpClass()
        

    @classmethod
    def tearDownClass(cls):
        super(TwoToROneRouterBase, cls).tearDownClass()

    def is_test_applicable(self):
        if len(self.get_available_devices('router')) < 1 :
            return (False, 'Skipping Test. Alteast 1 physical router required',
                    'in the test cluster')
        if len(self.get_available_devices('tor')) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the '
                'Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the '
                'Test cluster')
        return (True, None)

    def setUp(self):
        super(TwoToROneRouterBase, self).setUp()
        [self.phy_router_fixture] = self.setup_routers(count=1)
        [self.tor1_fixture, self.tor2_fixture] = self.setup_tors(count=2)

# end TwoToROneRouterBase

class TestVxlanIDWithRouting(TwoToROneRouterBase):

    @classmethod
    def setUpClass(cls):
        super(TestVxlanIDWithRouting, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVxlanIDWithRouting, cls).tearDownClass()

    def setUp(self):
        super(TestVxlanIDWithRouting, self).setUp()

    @preposttest_wrapper
    def test_check_vxlan_id_update(self):
        '''
        Validate that routing works after VXLAN id change
        '''
        self.set_configured_vxlan_mode()

        vn1_vxlan_id = get_random_vxlan_id()
        vn2_vxlan_id = get_random_vxlan_id()
        vn1_fixture = self.create_vn(disable_dns=True, vxlan_id=vn1_vxlan_id)
        vn2_fixture = self.create_vn(disable_dns=True, vxlan_id=vn2_vxlan_id)
        self.allow_all_traffic_between_vns(vn1_fixture, vn2_fixture)

        # BMS VMI
        vn1_vmi_fixture = self.setup_vmi(vn1_fixture.uuid)
        vn2_vmi_fixture = self.setup_vmi(vn2_fixture.uuid)
        self.setup_tor_port(self.tor1_fixture, vmi_objs=[vn1_vmi_fixture])
        self.setup_tor_port(self.tor2_fixture, vmi_objs=[vn2_vmi_fixture])
        bms1_fixture = self.setup_bms(self.tor1_fixture,
            ns_mac_address=vn1_vmi_fixture.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture,
            ns_mac_address=vn2_vmi_fixture.mac_address)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_physical_router(vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_physical_router(vn2_fixture, self.phy_router_fixture)
        
        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Change Vxlan id of the two vns
        vn1_fixture.set_vxlan_id(get_random_vxlan_id())
        vn2_fixture.set_vxlan_id(get_random_vxlan_id())

        # Restart any ovswitch processes to handle the vnid change
        self.restart_openvwitches([self.tor1_fixture, self.tor2_fixture])
        time.sleep(5)

        # Do ping test again 
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
        # Clear arps and check again
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

    # end test_check_vxlan_id_update

# end TestVxlanIDWithRouting

class TestBasicBMSInterVN(TwoToROneRouterBase):
    ''' Validate InterVN routing with BMSs
        This set of cases requires 2 ToRs with 1 BMS each and 1 Router(mx)
    '''

    @classmethod
    def setUpClass(cls):
        super(TestBasicBMSInterVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicBMSInterVN, cls).tearDownClass()

    def setUp(self):
        super(TestBasicBMSInterVN, self).setUp()

    def cleanUp(self):
        super(TestBasicBMSInterVN, self).cleanUp()

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
        self.extend_vn_to_physical_router(vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_physical_router(vn2_fixture, self.phy_router_fixture)
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Clear arps and check again
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Check Gateway MAC on BMS is irb's MAC
        self.validate_bms_gw_mac(bms1_fixture, self.phy_router_fixture)
        self.validate_bms_gw_mac(bms2_fixture, self.phy_router_fixture)
    # end common_two_tors_inter_vn_test
            

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
        self.set_configured_vxlan_mode()
        self.common_two_tors_inter_vn_test(vxlan_mode='configured')

    @preposttest_wrapper
    def test_asn_and_rt_update(self):
        '''
            Setup routing between two bmss on two VNs
            Change RT and validate routing works
            Change ASN and validate routing works
        '''
        vn1_fixture = self.create_vn(disable_dns=True)
        vn2_fixture = self.create_vn(disable_dns=True)

        # BMS VMI
        vn1_vmi_fixture = self.setup_vmi(vn1_fixture.uuid)
        vn2_vmi_fixture = self.setup_vmi(vn2_fixture.uuid)
        self.setup_tor_port(self.tor1_fixture, vmi_objs=[vn1_vmi_fixture])
        self.setup_tor_port(self.tor2_fixture, vmi_objs=[vn2_vmi_fixture])
        bms1_fixture = self.setup_bms(self.tor1_fixture, 
            ns_mac_address=vn1_vmi_fixture.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture, 
            ns_mac_address=vn2_vmi_fixture.mac_address)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_physical_router(vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_physical_router(vn2_fixture, self.phy_router_fixture)

        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']
        common_rt = get_random_rt()
        vn1_fixture.add_route_target(route_target_number=common_rt)
        vn2_fixture.add_route_target(route_target_number=common_rt)
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Update ASN
        new_asn = get_random_asn()
        self.set_global_asn(new_asn)

        # Ping, Clear arps and check again
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_asn_and_rt_update

# end TestBasicBMSInterVN

class TestExtendedBMSInterVN(TwoToROneRouterBase):
    ''' Validate InterVN routing with BMSs
        This set of cases requires 2 ToRs with 1 BMS each and 1 Router(mx)
    '''

    @classmethod
    def setUpClass(cls):
        super(TestExtendedBMSInterVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestExtendedBMSInterVN, cls).tearDownClass()

    def setUp(self):
        super(TestExtendedBMSInterVN, self).setUp()
        self.vn1_fixture = self.create_vn(disable_dns=True)
        self.vn2_fixture = self.create_vn(disable_dns=True)
        self.allow_all_traffic_between_vns(self.vn1_fixture, self.vn2_fixture)

        # BMS VMI
        self.vn1_vmi_fixture = self.setup_vmi(self.vn1_fixture.uuid)
        self.vn2_vmi_fixture = self.setup_vmi(self.vn2_fixture.uuid)
        self.setup_tor_port(self.tor1_fixture, port_index=0,
                            vmi_objs=[self.vn1_vmi_fixture])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
                            vmi_objs=[self.vn2_vmi_fixture])
        self.bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
            ns_mac_address=self.vn1_vmi_fixture.mac_address)
        self.bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
            ns_mac_address=self.vn2_vmi_fixture.mac_address)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_physical_router(self.vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_physical_router(self.vn2_fixture, self.phy_router_fixture)

    # end setUp

    def cleanUp(self):
        super(TestExtendedBMSInterVN, self).cleanUp()

    def do_reachability_checks(self):
        bms1_ip = self.bms1_fixture.info['inet_addr']
        bms2_ip = self.bms2_fixture.info['inet_addr']
        self.do_ping_test(self.bms1_fixture, bms1_ip, bms2_ip)

        # Clear arps and check again
        self.clear_arps([self.bms1_fixture, self.bms2_fixture])
        self.do_ping_test(self.bms1_fixture, bms1_ip, bms2_ip)

        # Check Gateway MAC on BMS is irb's MAC
        self.validate_bms_gw_mac(self.bms1_fixture, 
                                 self.phy_router_fixture)
        self.validate_bms_gw_mac(self.bms2_fixture,
                                 self.phy_router_fixture)
    # end do_reachability_checks

    @preposttest_wrapper
    def test_routing_with_tor_agent_restarts(self):

        tor_agent_dicts = self.tor1_fixture.get_tor_agents_details()
        for tor_agent_dict in tor_agent_dicts:
            tor_agent_service = 'contrail-tor-agent-%s' % (
                tor_agent_dict['tor_agent_id'])
            # Assuming tor-agent node is same as TSN node
            tor_agent_node = self.get_mgmt_ip_of_node(
                tor_agent_dict['tor_tsn_ip'])
            self.inputs.restart_service(tor_agent_service, [tor_agent_node])
            self.do_reachability_checks()
    # end test_routing_with_tor_agent_restarts
            
    @preposttest_wrapper
    def test_routing_with_ovs_restarts(self):
        self.tor1_fixture.restart_ovs()
        self.do_reachability_checks()
        self.tor2_fixture.restart_ovs()
        self.do_reachability_checks()
    # end test_routing_with_ovs_restarts

    @preposttest_wrapper
    def test_routing_after_tsn_failover(self):
        '''
        On one of the tors, stop the current active tsn
        Check that the flood route on the tor moves to the other tsn
        '''
        tsn_ip1 = self.tor1_fixture.get_active_tor_agent_ip('host_control_ip')
        tsn_ip2 = self.tor1_fixture.get_backup_tor_agent_ip('host_control_ip')
        self.inputs.stop_service('supervisor-vrouter', [tsn_ip1]) 
        self.addCleanup(self.inputs.start_service, 'supervisor-vrouter',
            [tsn_ip1])
        time.sleep(5)
        new_tor1_tsn = self.tor1_fixture.get_remote_flood_vtep(
            self.vn1_fixture.uuid) 
        assert tsn_ip2 == new_tor1_tsn, (
            'TSN switchover didnt seem to happen, Expected : %s, Got : %s' %(
            tsn_ip2, new_tor1_tsn))
        self.do_reachability_checks()
        retval, output = self.bms1_fixture.run_dhclient()
        assert retval, output
        retval, output = self.bms2_fixture.run_dhclient()
        assert retval, output
        self.do_reachability_checks()
            
    # end test_routing_after_tsn_failover

class TestBMSWithExternalDHCPServer(TwoToROneRouterBase):
    ''' Validate BMS tests with external DHCP Server
        This set of cases requires 2 ToRs with 1 BMS each and 1 Router(mx)
    '''

    @classmethod
    def setUpClass(cls):
        super(TestBMSWithExternalDHCPServer, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBMSWithExternalDHCPServer, cls).tearDownClass()


    def setUp(self):
        super(TestBMSWithExternalDHCPServer, self).setUp()
        self.vn0_fixture = self.create_vn(disable_dns=True)
        self.vn1_fixture = self.create_vn(disable_dns=True,
            vn_subnets=['13.1.1.0/24'],
            enable_dhcp=False)
        self.vn2_fixture = self.create_vn(disable_dns=True)
        self.allow_all_traffic_between_vns(self.vn1_fixture, self.vn2_fixture)

        # Extend VNs to router
        self.phy_router_fixture.setup_physical_ports()
        self.extend_vn_to_physical_router(self.vn1_fixture, self.phy_router_fixture)
        self.extend_vn_to_physical_router(self.vn2_fixture, self.phy_router_fixture)

        # BMS VMI
        self.vn1_vmi1_fixture = self.setup_vmi(self.vn1_fixture.uuid)
        self.vn1_vmi2_fixture = self.setup_vmi(self.vn1_fixture.uuid)
        self.vn2_vmi_fixture = self.setup_vmi(self.vn2_fixture.uuid)
        self.dhcp_server_fixture = self.create_dhcp_server_vm(self.vn0_fixture,
            self.vn1_fixture)

    # end setUp

    def cleanUp(self):
        super(TestBMSWithExternalDHCPServer, self).cleanUp()

    @preposttest_wrapper
    def test_dhcp_behavior(self):
        self.setup_tor_port(self.tor1_fixture, port_index=0,
            vmi_objs=[self.vn1_vmi1_fixture])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
            vmi_objs=[self.vn1_vmi2_fixture])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
            ns_mac_address=self.vn1_vmi1_fixture.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
            ns_mac_address=self.vn1_vmi2_fixture.mac_address)

        # Do L2 reachability checks
        bms1_ip = bms1_fixture.info['inet_addr']
        bms2_ip = bms2_fixture.info['inet_addr']
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
        # Clear arps and check again
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
    # end test_dhcp_behavior

    @preposttest_wrapper
    def test_dhcp_forwarding_with_dhcp_disabled(self):
        self.setup_tor_port(self.tor1_fixture, port_index=0,
            vmi_objs=[self.vn1_vmi1_fixture])
        self.setup_tor_port(self.tor2_fixture, port_index=0,
            vmi_objs=[self.vn1_vmi2_fixture])
        bms1_fixture = self.setup_bms(self.tor1_fixture, port_index=0,
            ns_mac_address=self.vn1_vmi1_fixture.mac_address)
        bms2_fixture = self.setup_bms(self.tor2_fixture, port_index=0,
            ns_mac_address=self.vn1_vmi2_fixture.mac_address)
        self.validate_dhcp_forwarding(bms1_fixture, bms2_fixture)
    # end test_dhcp_forwarding_with_dhcp_disabled

