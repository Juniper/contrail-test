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

from vn_test import *
from vm_test import *
from port_fixture import PortFixture
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.neutron.base import BaseNeutronTest
import test
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
from floating_ip import FloatingIPFixture


class TestPorts(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestPorts, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPorts, cls).tearDownClass()

#    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    def test_ports_attach_detach(self):
        '''Validate port attach/detach operations
        Create a port in a VN
        Create a VM using that port
        Detach the port

        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        port_obj = self.create_port(net_id=vn1_fixture.vn_id)
        self.sleep(5)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros')
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        if not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
            self.logger.error('Ping to a attached port %s failed' %
                              (vm1_fixture.vm_ip))
            result = result and False
        time.sleep(5)
        vm1_fixture.interface_detach(port_id=port_obj['id'])
        # No need to delete the port. It gets deleted on detach

        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error(
                'VM %s is not ACTIVE(It is %s) after port-detach' %
                (vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False

        if not vm2_fixture.ping_with_certainty(
                vm1_fixture.vm_ip,
                expectation=False):
            self.logger.error('Ping to a detached port %s passed!' %
                              (vm1_fixture.vm_ip))
            result = result and False
        else:
            self.logger.info('Unable to ping to a detached port.. OK')

        # Now attach the interface again
        port_obj = self.create_port(net_id=vn1_fixture.vn_id)
        self.sleep(5)
        vm1_fixture.interface_attach(port_id=port_obj['id'])
        time.sleep(5)
        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error(
                'VM %s is not ACTIVE(It is %s) during attach-detach' %
                (vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False
        if result and not vm2_fixture.ping_with_certainty(port_obj['fixed_ips'][0]['ip_address']):
            self.logger.error('Ping to a attached port %s failed' %
                              (vm1_fixture.vm_ip))
            result = result and False

        assert result, "Test Failed, pls look into the logs"
    # end test_ports_attach_detach

    @preposttest_wrapper
    def test_ports_specific_subnet(self):
        '''Create ports from specific subnets

        Create a port in a VN with 2 subnets.
        Validate that port can be created in any of the subnets
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vn1_subnet1_id = vn1_fixture.vn_subnet_objs[0]['id']
        vn1_subnet2_id = vn1_fixture.vn_subnet_objs[1]['id']
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet1_id}])
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet2_id}])
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        self.assertEqual(
            vm1_fixture.vm_ip,
            port1_obj['fixed_ips'][0]['ip_address'],
            'VM IP and Port IP Mismatch')
        self.assertEqual(
            vm2_fixture.vm_ip,
            port2_obj['fixed_ips'][0]['ip_address'],
            'VM IP and Port IP Mismatch')
        assert IPAddress(vm1_fixture.vm_ip) in IPNetwork(vn1_subnet_1),\
            'Port IP %s not from subnet %s' % (vm1_fixture.vm_ip, vn1_subnet_1)
        assert IPAddress(vm2_fixture.vm_ip) in IPNetwork(vn1_subnet_2),\
            'Port IP %s not from subnet %s' % (vm2_fixture.vm_ip, vn1_subnet_2)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' % (vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_subnet

    @test.attr(type=['sanity', 'vcenter_compute'])
    @preposttest_wrapper
    def test_ports_specific_subnet_ip(self):
        '''Create ports with specific Subnet and IP

        Create two ports in a VN with 2 subnets and specific IPs
        Attach to two VMs
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vn1_subnet1_id = vn1_fixture.vn_subnet_objs[0]['id']
        vn1_subnet2_id = vn1_fixture.vn_subnet_objs[1]['id']
        vn1_subnet1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'], 5)
        vn1_subnet2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[1]['cidr'], 5)
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet1_id,
                                                 'ip_address': vn1_subnet1_ip}])
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet2_id,
                                                 'ip_address': vn1_subnet2_ip}])
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        self.assertEqual(vm1_fixture.vm_ip,
                         vn1_subnet1_ip, 'VM IP and Port IP Mismatch')
        self.assertEqual(vm2_fixture.vm_ip,
                         vn1_subnet2_ip, 'VM IP and Port IP Mismatch')
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' % (vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_subnet_ip

    @skip_because(hypervisor='docker',msg='Bug 1461423:Need privileged access')
#    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ports_multiple_specific_subnet_ips(self):
        '''Create ports with multiple specific Subnets and IPs

        Create two ports in a VN with 2 subnets and specific IPs
        Attach to two VMs
        Ping from a test VM to the fixed IPs should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        test_vm_name = get_random_name('test-vm')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vn1_subnet1_id = vn1_fixture.vn_subnet_objs[0]['id']
        vn1_subnet2_id = vn1_fixture.vn_subnet_objs[1]['id']
        vn1_subnet1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'], 5)
        vn1_subnet2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[1]['cidr'], 5)
        vn1_subnet1_ip2 = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'], 15)
        vn1_subnet2_ip2 = get_an_ip(vn1_fixture.vn_subnet_objs[1]['cidr'], 15)
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet1_id,
                                                 'ip_address': vn1_subnet1_ip}, {'subnet_id': vn1_subnet2_id, 'ip_address': vn1_subnet2_ip}])
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port1_obj['id']])
        test_vm_fixture = self.create_vm(vn1_fixture, test_vm_name,
                                         image_name='cirros')
        vm1_fixture.verify_on_setup()
        assert test_vm_fixture.wait_till_vm_is_up()
        assert vm1_fixture.wait_till_vm_is_up()
        subnet_list = [vn1_subnet1_ip, vn1_subnet2_ip]
        subnet_list2 = [vn1_subnet1_ip2, vn1_subnet2_ip2]
        assert set(vm1_fixture.vm_ips) == set(
            subnet_list), 'Mismatch between VM IPs and the Port IPs'
        # Create alias on the VM to respond to pings
        for subnet in subnet_list:
            output = vm1_fixture.run_cmd_on_vm(['sudo ifconfig eth0:' + unicode(
                subnet_list.index(subnet)) + ' ' + subnet + ' netmask 255.255.255.0'])
        for ip in vm1_fixture.vm_ips:
            assert test_vm_fixture.ping_with_certainty(ip), ''\
                'Ping between VMs %s, %s failed' % (ip,
                                                    test_vm_fixture.vm_ip)
        self.logger.info('Will detach the VM and the port and check ping')
        vm1_fixture.interface_detach(port_id=port1_obj['id'])
        time.sleep(5)
        for ip in vm1_fixture.vm_ips:
            assert test_vm_fixture.ping_with_certainty(ip, expectation=False), ''\
                'Ping between VMs %s, %s passed.Expected to fail' % (ip,
                                                                     test_vm_fixture.vm_ip)
        self.logger.info('Will re-attach the VM and the port and check ping')
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     fixed_ips=[{'subnet_id': vn1_subnet1_id,
                                                 'ip_address': vn1_subnet1_ip2}, {'subnet_id': vn1_subnet2_id, 'ip_address': vn1_subnet2_ip2}])
        self.sleep(5)
        vm1_fixture.clear_vmi_info()
        vm1_fixture.interface_attach(port_id=port1_obj['id'])
        assert vm1_fixture.wait_till_vm_is_up()
       # Create alias on the VM to respond to pings
        for subnet in subnet_list2:
            output = vm1_fixture.run_cmd_on_vm(['sudo ifconfig eth0:' + unicode(
                subnet_list2.index(subnet)) + ' ' + subnet + ' netmask 255.255.255.0'])
        time.sleep(5)
        for ip in subnet_list2:
            assert test_vm_fixture.ping_with_certainty(ip), ''\
                'Ping between VMs %s, %s failed' % (ip,
                                                    test_vm_fixture.vm_ip)

    # end test_ports_multiple_specific_subnet_ip

    @preposttest_wrapper
    def test_ports_specific_mac(self):
        '''Create ports with specific MAC

        Create two ports in a VN with 2 specific MACs
        Attach to two VMs
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vm1_mac = '00:00:00:00:00:01'
        vm2_mac = '00:00:00:00:00:02'

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     mac_address=vm1_mac)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     mac_address=vm2_mac)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        vm1_tap_intf = vm1_fixture.tap_intf[vm1_fixture.vn_fq_names[0]]
        vm2_tap_intf = vm2_fixture.tap_intf[vm2_fixture.vn_fq_names[0]]
        assert vm1_tap_intf['mac_addr'] == vm1_mac, ''\
            'VM MAC %s is not the same as configured %s' % (
                vm1_tap_intf['mac_addr'], vm1_mac)
        assert vm2_tap_intf['mac_addr'] == vm2_mac, ''\
            'VM MAC %s is not the same as configured %s' % (
                vm2_tap_intf['mac_addr'], vm2_mac)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' % (vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_mac

    @preposttest_wrapper
    def test_ports_no_sg(self):
        '''Create port with no SG

        Attach it to a VM
        Validate that another VM in the same VN is not able to reach this VM
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     no_security_group=True)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm1_fixture.vm_ip,
                                                           vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm2_fixture.vm_ip,
                                                           vm1_fixture.vm_ip)
    # end test_ports_no_sg

    @preposttest_wrapper
    def test_ports_custom_sg(self):
        '''Create port with custom SG

        Attach it to a VM
        Validate with another VM that the SG applied is working
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        sg1 = self.create_security_group(get_random_name('sg1'))

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     security_groups=[sg1.uuid])
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm1_fixture.vm_ip,
                                                           vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm2_fixture.vm_ip,
                                                           vm1_fixture.vm_ip)
    # end test_ports_custom_sg

    @preposttest_wrapper
    def test_ports_extra_dhcp_options(self):
        '''Create port with extra dhcp option and attach to a VM

        Validate that VM gets the DHCP option
        Remove the dhcp option
        Validate that VM does not get the DHCP option
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])
        vn1_dns_server = get_an_ip(vn1_subnet_1, 2)

        dns_ip = get_random_ip(get_random_cidr())
        extra_dhcp_opts = [{'opt_name': '6', 'opt_value': dns_ip}]
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     extra_dhcp_opts=extra_dhcp_opts)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'

        # Check DHCP dns option on vm1
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert dns_ip in resolv_output, 'Extra DHCP DNS Server IP %s not seen in '\
            'resolv.conf of the VM' % (dns_ip)
        self.logger.info('Extra DHCP DNS option sent is updated in the VM')

        # Check default behavior on vm2
        output = vm2_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert vn1_dns_server in resolv_output, \
            'Default DNS Server IP %s not seen in resolv.conf of the VM' % (
                dns_ip)

        # Remove the dhcp option and check the result on the VM
        port_dict = {'extra_dhcp_opts': []}
        self.quantum_h.update_port(port1_obj['id'], port_dict)
        vm1_fixture.reboot()
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert vn1_dns_server in resolv_output, \
            'Default DNS Server IP %s not restored in resolv.conf of VM' % (
                dns_ip)

    # end test_ports_extra_dhcp_options

    @preposttest_wrapper
    def test_port_ip_reuse(self):
        '''Validate port IPs gets reused once they are freed

        Create a port and delete it
        Creating another port should get the same IP
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        self.delete_port(port1_obj['id'])
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port1_ip = port1_obj['fixed_ips'][0]['ip_address']
        port2_ip = port2_obj['fixed_ips'][0]['ip_address']
        assert port1_ip == port2_ip,\
            'On delete and recreate of a port, port got a different IP'\
            '%s than %s' % (port2_ip, port1_ip)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
    # end test_port_ip_reuse

    @preposttest_wrapper
    def test_port_rename(self):
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnet = get_random_cidr()
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet])
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port_dict = {'name': "test_port"}
        port_rsp = self.quantum_h.update_port(port1_obj['id'], port_dict)
        assert port_rsp['port'][
            'name'] == "test_port", 'Failed to update port name'
        self.quantum_h.delete_port(port1_obj['id'])

    # end test_port_rename

    @preposttest_wrapper
    def test_port_admin_state_up(self):
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        port_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip)
        port_dict = {'admin_state_up': False}
        port_rsp = self.quantum_h.update_port(port_obj['id'], port_dict)
        assert port_rsp['port'][
            'admin_state_up'] == False, 'Failed to update port admin_state_up to False'
        assert vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False), 'Port forwards packets with admin_state_up set to False not expected'
        port_dict = {'admin_state_up': True}
        port_rsp = self.quantum_h.update_port(port_obj['id'], port_dict)
        assert port_rsp['port'][
            'admin_state_up'], 'Failed to update port admin_state_up to True '
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)

    # end test_port_admin_state_up

    @preposttest_wrapper
    def test_ports_update_sg(self):
        '''For a port, verify updating the SG

        Create a port with default SG
        Update the port with custom SG
        Attach it to a VM
        Validate with another VM that SG applied is working
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        sg1 = self.create_security_group(get_random_name('sg1'))

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'

        # Update the port with custom sg
        port_dict = {'security_groups': [sg1.uuid]}
        self.quantum_h.update_port(port1_obj['id'], port_dict)

        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm1_fixture.vm_ip,
                                                           vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm2_fixture.vm_ip,
                                                           vm1_fixture.vm_ip)
    # end test_ports_update_sg

    @preposttest_wrapper
    def test_ports_device_owner_and_id(self):
        '''For a port, verify device owner and id are correct

        Create a port in a VN
        Device id and owner should be null
        Attach it to a VM
        Device id and owner should be updated to reflect the VM
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        assert port1_obj['device_id'] == '', \
            "Port %s has device id not set to null on creation" % (port1_obj)
        assert port1_obj['device_owner'] ==  '', \
            "Port %s has device-owner not set to null on creation" % (
                port1_obj)

        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros',
                                     port_ids=[port1_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'

        port1_obj = self.quantum_h.get_port(port1_obj['id'])
        assert port1_obj['device_id'] == vm1_fixture.vm_id, \
            "Port %s has device id not set to %s on VM Attach" % (
            port1_obj, vm1_fixture.vm_id)
        assert 'compute:' in port1_obj['device_owner'], \
            "Port %s has device-owner not set to compute:* on VM Attach" % (
                port1_obj)

    # end test_ports_device_owner_and_id

    @preposttest_wrapper
    def test_ports_secondary_ip_attach(self):
        '''
        Validate when 2 different Instance IPs are associated with same VMI,
        and "instance_ip_secondary" is set True for 2nd Instance IP, 1st Instance IP
        should act as native IP of VM. This script verifies following bug:
        https://bugs.launchpad.net/juniperopenstack/+bug/1645414
        
        Create a VN.
        Create a VMI/Port and add set "instance_ip_secondary" = False.
        This will result in 2 instances getting created and attached to same VMI.
        1 IIP Primary and 2nd IIP as Secondary.
        Create a VM using that port and verify that IP from primary IIP gets assigned by DHCP 
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet])
        fixed_ips = [{'subnet_id' : vn1_fixture.vn_subnet_objs[0]['id'],
                      'instance_ip_secondary' : False},
                     {'subnet_id' : vn1_fixture.vn_subnet_objs[0]['id'],
                      'instance_ip_secondary' : True}]
        port_vm1_obj = self.useFixture(PortFixture(vn1_fixture.uuid,
                                api_type = "contrail",
                                fixed_ips = fixed_ips,
                                connections=self.connections))
        assert port_vm1_obj.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port_vm1_obj.uuid])
        assert vm1_fixture.wait_till_vm_is_up()
        if port_vm1_obj.iip_objs[0].instance_ip_address == vm1_fixture.vm_ip:
            self.logger.debug("VM Ip is successfully set to Primary IIP")
        elif port_vm1_obj.iip_objs[1].instance_ip_address == vm1_fixture.vm_ip:
            self.logger.debug("VM Ip is set to secondary IIP")
            assert False, "VM Ip is set to secondary IIP"
        else:
            assert False, "VM Ip is none among any IIP"
    # end test_ports_secondary_ip_attach
 
    @preposttest_wrapper
    def test_shutoff_vm_route_withdrawal(self):
        '''Test shutdown of VM using nova command and correponfing route withdrawal.
        Shutoff the VM using nova stop
        Verify the route is removed from all agent and compute node.
        '''
        result = True

        (self.vn1_name, self.vn1_subnets) = (
            get_random_name("vn1"), ["11.1.1.0/24"])
        (self.vn1_vm1_name, self.vn1_vm2_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        # Get all compute host
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))

        self.vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                vm_name=self.vn1_vm1_name,
                node_name=compute_1))

        self.vn1_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                vm_name=self.vn1_vm2_name,
                node_name=compute_2))

        vn1_fixture = self.vn1_fixture
        vn1_vm1_fixture = self.vn1_vm1_fixture
        vn1_vm2_fixture = self.vn1_vm2_fixture

        vn1_vm1_fixture.wait_till_vm_is_up()
        vn1_vm2_fixture.wait_till_vm_is_up()

        vm1_name = self.vn1_vm1_name
        vn1_name = self.vn1_name
        vn1_subnets = self.vn1_subnets
        vm2_name = self.vn1_vm2_name
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup(force=True)
        assert vn1_vm2_fixture.verify_on_setup(force=True)

        # Test Triger: Shutoff VM
        self.logger.info(
            'Executing nova stop to shutoff the VM %s' % (vm1_name))
        vn1_vm1_fixture.vm_obj.stop()
        assert vn1_vm1_fixture.wait_till_vm_status('SHUTOFF'), ('Unable to '
            ' shutoff a VM')

        # Test specific verification
        self.logger.info(
            'Verifying VM route entry is removed from agent after shutoff')
        assert vn1_vm1_fixture.verify_vm_routes_not_in_agent()
        self.logger.info(
            'Verifying VM route entry is removed from control node after shutoff')
        assert vn1_vm1_fixture.verify_vm_not_in_control_nodes()

        return True

    @preposttest_wrapper
    def test_aap_with_vrrp_admin_state_toggle(self):
        '''Create 2 VMs and enable VRRP between them, specifying a vIP.
        Update the ports of the respective VMs to allow the vIP so configured.
        Cause a VRRP Mastership switchover by bringing down the admin_state of the Master's interface.
        The vIP should still be accessible via the new VRRP master.
        '''

        vn1_name = get_random_name('vn1')
        vn1_subnets = ['10.10.10.0/24']
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vm_test_name = get_random_name('vm_test')
        vIP = '10.10.10.10'
        result = False

        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port2_obj['id']])
        vm_test_fixture = self.create_vm(vn1_fixture, vm_test_name,
                                         image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm_test_fixture.wait_till_vm_is_up(
        ), 'VM does not seem to be up'
        port_list = [port1_obj, port2_obj]
        for port in port_list:
            self.config_aap(port, vIP, mac=port['mac_address'])
        self.config_vrrp(vm1_fixture, vIP, '20')
        self.config_vrrp(vm2_fixture, vIP, '10')
        time.sleep(10)
        assert self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        assert self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP)

        self.logger.info('We will induce a mastership switch')
        port_dict = {'admin_state_up': False}
        self.update_port(port1_obj['id'], port_dict)
        time.sleep(10)
        self.logger.info(
            '%s should become the new VRRP master' % vm2_fixture.vm_name)
        assert self.vrrp_mas_chk(vm2_fixture, vn1_fixture, vIP)
        assert self.verify_vrrp_action(vm_test_fixture, vm2_fixture, vIP)

        self.logger.info('We will bring up the interface')
        port_dict1 = {'admin_state_up': True}
        self.update_port(port1_obj['id'], port_dict1)
        time.sleep(10)
        self.logger.info(
            '%s should become the VRRP master again' % vm1_fixture.vm_name)
        assert self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        assert self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP)

    # end test_aap_with_vrrp_admin_state_toggle

    @skip_because(hypervisor='docker',msg='Uses vsrx image', min_nodes=3)
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_aap_with_fip(self):
        '''
        1. Create 2 VSRXs and enable VRRP between them, specifying a vIP.
        2. Update the ports of the respective VMs to allow the vIP so configured.
        3. Associate the same FIP to both the ports using API.
        4. In the Floating IP object, add the vIP as the fixed_ip_address.
        5. Ping to the vIP and FIP should be answered by the AAP active port.
        6. Cause a VRRP Mastership switchover by changing the VRRP priority.
        7. The vIP and FIP should still be accessible via the new VRRP master.

        '''
        # Since the ping is across projects, enabling allow_all in the SG
        self.project.set_sec_group_for_allow_all(
            self.inputs.project_name, 'default')

        vn1_name = get_random_name('left-vn')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('right-vn')
        vn2_subnets = [get_random_cidr()]
        vn3_name = get_random_name('mgmt-vn')
        vn3_subnets = [get_random_cidr()]

        vsrx1_name = get_random_name('vsrx1')
        vsrx2_name = get_random_name('vsrx2')
        vm_test_name = get_random_name('vm_test')
        vIP = get_an_ip(vn1_subnets[0], offset=10)
        result = False

        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn3_fixture = self.create_vn(vn3_name, vn3_subnets)
        vn_objs = [vn3_fixture.obj, vn1_fixture.obj, vn2_fixture.obj]

        lvn_port_obj1 = self.create_port(net_id=vn1_fixture.vn_id)
        rvn_port_obj1 = self.create_port(net_id=vn2_fixture.vn_id)
        mvn_port_obj1 = self.create_port(net_id=vn3_fixture.vn_id)

        lvn_port_obj2 = self.create_port(net_id=vn1_fixture.vn_id)
        rvn_port_obj2 = self.create_port(net_id=vn2_fixture.vn_id)
        mvn_port_obj2 = self.create_port(net_id=vn3_fixture.vn_id)

        port_ids1 = [
            mvn_port_obj1['id'], lvn_port_obj1['id'], rvn_port_obj1['id']]
        port_ids2 = [
            mvn_port_obj2['id'], lvn_port_obj2['id'], rvn_port_obj2['id']]

        vm1_fixture = self.useFixture(
            VMFixture(
                vn_objs=vn_objs, project_name=self.inputs.project_name, connections=self.connections,
                image_name='vsrx', vm_name=vsrx1_name,
                port_ids=port_ids1, zone='nova'))
        vm2_fixture = self.useFixture(
            VMFixture(
                vn_objs=vn_objs, project_name=self.inputs.project_name, connections=self.connections,
                image_name='vsrx', vm_name=vsrx2_name,
                port_ids=port_ids2, zone='nova'))
        vm_test_fixture = self.create_vm(vn1_fixture, vm_test_name,
                                         image_name='cirros')
        test_vm = self.create_vm(vn3_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        self.logger.info('Create a FVN. Create a FIP-Pool and FIP')
        fvn_name = get_random_name('fvn')
        fvn_subnets = [get_random_cidr()]
        fvn_vm_name = get_random_name('fvn-vm')
        fvn_fixture = self.create_vn(fvn_name, fvn_subnets)
        fvn_vm_fixture = self.create_vm(fvn_fixture, fvn_vm_name,
                                        image_name='cirros')
        assert fvn_vm_fixture.wait_till_vm_is_up(
        ), 'VM does not seem to be up'
        fip_pool_name = 'some-pool1'
        my_fip_name = 'fip'
        fvn_obj = fvn_fixture.obj
        fvn_id = fvn_fixture.vn_id
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fIP = self.create_fip(fip_fixture)
        self.addCleanup(self.del_fip, fIP[1])
        self.logger.info('Use VNC API to associate the same fIP to two ports')
        self.logger.info(
            'Add the vIP- %s as Fixed IP of the fIP- %s' % (vIP, fIP[0]))
        vm1_l_vmi_id = vm1_fixture.get_vmi_ids()[vn1_fixture.vn_fq_name]
        vm2_l_vmi_id = vm2_fixture.get_vmi_ids()[vn1_fixture.vn_fq_name]
        self.assoc_fip(fIP[1], vm1_fixture.vm_id, vmi_id=vm1_l_vmi_id)
        self.assoc_fip(fIP[1], vm2_fixture.vm_id, vmi_id=vm2_l_vmi_id)
        self.assoc_fixed_ip_to_fip(fIP[1], vIP)
        self.addCleanup(self.disassoc_fip, fIP[1])
        port_list = [lvn_port_obj1, lvn_port_obj2]
        for port in port_list:
            self.config_aap(port, vIP, mac='00:00:5e:00:01:01')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.logger.info('We will configure VRRP on the two vSRX')
        op1 = self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=vm1_fixture, vip=vIP, priority='200', interface='ge-0/0/1')
        op2 = self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=vm2_fixture, vip=vIP, priority='100', interface='ge-0/0/1')
        time.sleep(10)
        self.logger.info('Will wait for both the vSRXs to come up')
        vm1_fixture.wait_for_ssh_on_vm()
        vm2_fixture.wait_for_ssh_on_vm()
        vm_test_fixture.wait_till_vm_is_up()
        assert self.vrrp_mas_chk(
            src_vm=test_vm, dst_vm=vm1_fixture, vn=vn1_fixture, ip=vIP, vsrx=True)
        assert self.verify_vrrp_action(
            vm_test_fixture, vm1_fixture, vIP, vsrx=True)
        assert self.verify_vrrp_action(
            fvn_vm_fixture, vm1_fixture, fIP[0], vsrx=True)

        self.logger.info(
            'Will reduce the VRRP priority on %s, causing a VRRP mastership switch' % vm1_fixture.vm_name)
        op = self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=vm1_fixture, vip=vIP, priority='80', interface='ge-0/0/1')
        time.sleep(10)
        self.logger.info('Will wait for both the vSRXs to come up')
        vm1_fixture.wait_for_ssh_on_vm()
        vm2_fixture.wait_for_ssh_on_vm()
        assert self.vrrp_mas_chk(
            src_vm=test_vm, dst_vm=vm2_fixture, vn=vn1_fixture, ip=vIP, vsrx=True)
        assert self.verify_vrrp_action(
            vm_test_fixture, vm2_fixture, vIP, vsrx=True)
        assert self.verify_vrrp_action(
            fvn_vm_fixture, vm2_fixture, fIP[0], vsrx=True)

    # end test_aap_with_fip

    @preposttest_wrapper
    def test_aap_with_vrrp_priority_change(self):
        '''Create 2 VMs and enable VRRP between them, specifying a vIP.
        Update the ports of the respective VMs to allow the vIP so configured.
        Cause a VRRP Mastership switchover by changing the VRRP priority.
        The vIP should still be accessible via the new VRRP master.
        '''

        vn1_name = get_random_name('vn1')
        vn1_subnets = ['10.10.10.0/24']
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vm_test_name = get_random_name('vm_test')
        vIP = '10.10.10.10'
        result = False

        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port2_obj['id']])
        vm_test_fixture = self.create_vm(vn1_fixture, vm_test_name,
                                         image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm_test_fixture.wait_till_vm_is_up(
        ), 'VM does not seem to be up'
        port_list = [port1_obj, port2_obj]
        for port in port_list:
            self.config_aap(port, vIP, mac=port['mac_address'])
        self.config_vrrp(vm1_fixture, vIP, '20')
        self.config_vrrp(vm2_fixture, vIP, '10')
        assert self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        assert self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP)

        self.logger.info(
            'We will Kill vrrpd, induce a networking restart and reconfigure VRRP')
        self.logger.info('%s should become the new master' %
                         vm2_fixture.vm_name)
        kill_vrrp = 'nohup killall -9 vrrpd'
        reset_cmd = '/etc/init.d/networking restart'
        vm1_fixture.run_cmd_on_vm(cmds=[kill_vrrp], as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=[kill_vrrp], as_sudo=True)
        vm1_fixture.run_cmd_on_vm(cmds=[reset_cmd], as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=[reset_cmd], as_sudo=True)
        time.sleep(30)
        self.config_vrrp(vm1_fixture, vIP, '10')
        self.config_vrrp(vm2_fixture, vIP, '20')
        assert self.vrrp_mas_chk(vm2_fixture, vn1_fixture, vIP)
        assert self.verify_vrrp_action(vm_test_fixture, vm2_fixture, vIP)

    # end test_aap_with_vrrp_priority_change
    
    @preposttest_wrapper
    def test_zombie_tap_interface(self):
        '''Test Zombie Tap-interface
            create vn,vm and port
            delete the port
            check whether still tap-interface present or not''' 
        result = True
        vn1_name = get_random_name('vn1')
        vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name)
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port1_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        self.logger.info('get tap_interface of vm %s' %vm1_fixture.vm_name)
        vm_tap_intf=vm1_fixture.get_tap_intf_of_vm()
        assert vm_tap_intf,'Tap interface not present for %s'  %vm1_fixture.vm_name
        self.delete_port(port1_obj['id'])
        sleep(10)
        vm_tap_intf = vm1_fixture.get_tap_intf_of_vm()
        assert not(
            vm_tap_intf), 'Tap interface still present for vm %s' % vm1_fixture.vm_name
        self.logger.info(
            "VM's tap interface got cleaned up on port delete. Test passed")

    # end test_zombie_tap_interface

    @skip_because(hypervisor='docker',msg='Bug 1461423:Need privileged access')
    @preposttest_wrapper
    def test_aap_active_active_mode(self):
        '''
        Verify AAP in active-active mode
            1. Launch 2 vms on same virtual network. 
            2. Configure AAP between the two ports in active-active mode.
            3. Launch a test VM in the same network.
            4. Create a alias on both the VMs for the vIP.
            5. cURL request to the vIP should be answered by either of the two VMs.

        Maintainer: ganeshahv@juniper.net
        '''

        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vm_test_name = get_random_name('vm_test')
        result = False
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vIP = get_an_ip(vn1_subnets[0], offset=10)
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port_list = [port1_obj, port2_obj]
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port2_obj['id']])
        vm_test_fixture = self.create_vm(vn1_fixture, vm_test_name,
                                         image_name='ubuntu')
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm_test_fixture.wait_till_vm_is_up(
        ), 'VM does not seem to be up'
        vm_list = [vm1_fixture, vm2_fixture]
        for port in port_list:
            self.config_aap(
                port, vIP, mac=port['mac_address'], aap_mode='active-active', contrail_api=True)
        self.logger.info(
            'Since no VRRP is run, both the ports should be seen as active')
        for vm in vm_list:
            vm.start_webserver()
            output = vm.run_cmd_on_vm(
                ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])
            self.check_master_in_agent(vm, vn1_fixture, vIP, ecmp=True)
        self.logger.info('Curl requests to %s should be answered by either %s or %s' % (
            vIP, vm1_fixture.vm_name, vm2_fixture.vm_name))
        cmd = "curl --local-port 9001 -i " + vIP + ":8000"
        result = vm_test_fixture.run_cmd_on_vm(cmds=[cmd])
        assert (vm1_fixture.vm_name or vm2_fixture.vm_name) and '200 OK' in result[
            cmd], 'Requests not being answered'
    # end test_aap_active_active_mode

    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_aap_with_zero_mac(self):
        '''
        Verify  VIP reachability over L2 network when AAP MAC is configured with all zeo
            1. Launch 2 vms on same virtual network. 
            2. Configure high availability between them with keepalived.
            3. Launch third VM in same VM. 
            4. Check the reachability of VIP from 3rd VM.
            5. Shutdown keepalive in master VM to induce VIP  switch over.  
            6. Check the reachability of VIP from 3rd VM again.
            7. Bring back master VM which will cause switchover of VIP again.
            8. Check the reachability of VIP from 3rd VM again.
                
        Pass criteria: Step 4,6 and 8 should pass
        Maintainer: chhandak@juniper.net
        '''

        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vm_test_name = get_random_name('vm_test')
        vID = '51'
        result = False

        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vIP = get_an_ip(vn1_subnets[0], offset=10)
        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port_list = [port1_obj, port2_obj]
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name='ubuntu-keepalive',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name='ubuntu-keepalive',
                                     port_ids=[port2_obj['id']])
        vm_test_fixture = self.create_vm(vn1_fixture, vm_test_name,
                                          image_name='ubuntu')
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm_test_fixture.wait_till_vm_is_up(
        ), 'VM does not seem to be up'
        for port in port_list:
            self.config_aap(
                port, vIP, mac='00:00:00:00:00:00', contrail_api=True)
        self.config_keepalive(vm1_fixture, vIP, vID, '10')
        self.config_keepalive(vm2_fixture, vIP, vID, '20')

        self.logger.info('Ping to the Virtual IP from the test VM (Same Network)')
        assert vm_test_fixture.ping_with_certainty(vIP), ''\
            'Ping to the Virtual IP %s from the test VM  %s, failed' % (vIP,
                                                vm_test_fixture.vm_ip)

        self.logger.info('Forcing VIP Switch by stopping keepalive on master')
        self.service_keepalived(vm2_fixture, 'stop')

        self.logger.info('Ping to the Virtual IP after switch over \
                         from the test VM (Same Network)')
        assert vm_test_fixture.ping_with_certainty(vIP), ''\
            'Ping to the Virtual IP %s from the test VM  %s, failed' % (vIP,
                                                vm_test_fixture.vm_ip)

        self.logger.info('Bringing keepalive master back')
        self.service_keepalived(vm2_fixture, 'start')

        self.logger.info('Ping to the Virtual IP after switch over \
                         from the test VM (Same Network)')
        assert vm_test_fixture.ping_with_certainty(vIP), ''\
            'Ping to the Virtual IP %s from the test VM  %s, failed' % (vIP,
                                                vm_test_fixture.vm_ip)
    # end test_aap_with_zero_mac  

    @test.attr(type=['sanity', 'vcenter_compute'])
    @preposttest_wrapper
    def test_ports_bindings(self):
        '''
        Verify that we are able to create a port with custom port bindings
        Steps:
            1) Create Port with Port bindings profile set to {'foo': 'bar'}
            2) Retrieve and verify the same is set
        '''
        bind_dict = {'foo': 'bar'}
        vn = self.create_vn()
        port = self.useFixture(PortFixture(vn.uuid, connections=self.connections,
                               binding_profile=bind_dict))
        assert port.verify_on_setup(), 'VMI %s verification has failed'%port.uuid
    # end test_ports_bindings
