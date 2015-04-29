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

from common.tor.base import BaseTorTest
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
        if len(self.inputs.tor_data.keys()) == 0 :
            return (False, 'Skipping Test. No ToRs seen in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)


    def one_kvm_one_bms_test(self, tor_id, vlan_id=0):
        '''Common test code for one kvm and one bms test
        '''
        vn1_fixture = self.create_vn(disable_dns=True)
        vm1_fixture = self.create_vm(vn1_fixture, 
                                     image_name='cirros-0.3.0-x86_64-uec')
        vm1_fixture.wait_till_vm_is_up()

        tor_dict, tor_1_info = self.get_tor_info(tor_id=tor_id)
        bms_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'])
        bms_mac = '00:00:00:00:00:01'
        
        # BMS VMI
        vmis=[self.setup_vmi(vn1_fixture.uuid, 
                mac_address=bms_mac,
                fixed_ips=[{'subnet_id': vn1_fixture.vn_subnet_objs[0]['id'], 
                            'ip_address': bms_ip,
                          }])
             ]
        self.setup_tor_port(tor_1_info.uuid, tor_dict, port_index=0, 
                            vlan_id=vlan_id, vmi_objs=vmis)
        bms_fixture = self.setup_bms(tor_dict, port_index=0, 
                                     ns_mac_address=bms_mac, vlan_id=vlan_id)
        retval,output = bms_fixture.run_dhclient()
        assert retval, "BMS did not seem to have got an IP"
        
        assert vm1_fixture.ping_with_certainty(bms_ip),\
            self.logger.error('Unable to ping BMS IP %s from VM %s' % (
                bms_ip, vm1_fixture.vm_ip))
        self.logger.info('Ping from openstack VM to BMS IP passed')                          

    #@preposttest_wrapper
    def test_ping_between_kvm_vm_and_untagged_bms(self):
        '''Validate ping between a KVM VM and a untagged BMS

        '''
        self.one_kvm_one_bms_test(tor_id='1', vlan_id=0)

    # end test_ping_between_kvm_vm_and_untagged_bms

    #@preposttest_wrapper
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
        retval,output = bms1_fixture.run_dhclient()
        assert retval, "BMS1 did not seem to have got an IP"
        retval,output = bms2_fixture.run_dhclient()
        assert retval, "BMS2 did not seem to have got an IP"

        self.validate_interface_ip(bms1_fixture, bms1_ip)
        self.validate_interface_ip(bms2_fixture, bms2_ip)

        assert bms1_fixture.ping_with_certainty(bms2_ip),\
            'Ping from BMS %s to BMS %s' % (
                bms1_ip, bms2_ip)
        self.logger.info('Ping test from BMS %s to BMS %s passed' % (bms1_ip,
                          bms2_ip))
