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
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.neutron.base import BaseNeutronTest
import test
from tcutils.util import *
from netaddr import IPNetwork, IPAddress


class TestPorts(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestPorts, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPorts, cls).tearDownClass()

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
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='ubuntu-traffic',
                                     port_ids=[port_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
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
        vm1_fixture.interface_attach(port_id=port_obj['id'])
        time.sleep(5)
        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error(
                'VM %s is not ACTIVE(It is %s) during attach-detach' %
                (vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False
        if result and not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
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
                                     subnet_id=vn1_subnet1_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     subnet_id=vn1_subnet2_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
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

    @test.attr(type=['sanity'])
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
                                     subnet_id=vn1_subnet1_id,
                                     ip_address=vn1_subnet1_ip)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id,
                                     subnet_id=vn1_subnet2_id,
                                     ip_address=vn1_subnet2_ip)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.assertEqual(vm1_fixture.vm_ip,
                         vn1_subnet1_ip, 'VM IP and Port IP Mismatch')
        self.assertEqual(vm2_fixture.vm_ip,
                         vn1_subnet2_ip, 'VM IP and Port IP Mismatch')
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' % (vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_subnet_ip

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
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
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
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' % (vm1_fixture.vm_ip,
                                                           vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping from VM %s to %s, should have passed' % (vm2_fixture.vm_ip,
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
                                     security_groups=[sg1['id']])
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
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
        vn1_gateway = get_an_ip(vn1_subnet_1, 1)

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
        self.logger.info('Extra DHCP DNS option sent in updated in the VM')

        # Check default behavior on vm2
        output = vm2_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert vn1_gateway in resolv_output, \
            'Default DNS Server IP %s not seen in resolv.conf of the VM' % (
                dns_ip)

        # Remove the dhcp option and check the result on the VM
        port_dict = {'extra_dhcp_opts': []}
        self.quantum_fixture.update_port(port1_obj['id'], port_dict)
        vm1_fixture.reboot()
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert vn1_gateway in resolv_output, \
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
        port_rsp = self.quantum_fixture.update_port(port1_obj['id'], port_dict)
        assert port_rsp['port'][
            'name'] == "test_port", 'Failed to update port name'
        self.quantum_fixture.delete_port(port1_obj['id'])

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
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip)
        port_dict = {'admin_state_up': False}
        port_rsp = self.quantum_fixture.update_port(port_obj['id'], port_dict)
        assert port_rsp['port'][
            'admin_state_up'] == False, 'Failed to update port admin_state_up to False'
        assert vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False), 'Port forwards packets with admin_state_up set to False not expected'
        port_dict = {'admin_state_up': True}
        port_rsp = self.quantum_fixture.update_port(port_obj['id'], port_dict)
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
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'

        # Update the port with custom sg
        port_dict = {'security_groups':[sg1['id']]}
        self.quantum_fixture.update_port(port1_obj['id'], port_dict)

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
          "Port %s has device-owner not set to null on creation" % (port1_obj)

        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port1_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'

        port1_obj = self.quantum_fixture.get_port(port1_obj['id'])
        assert port1_obj['device_id'] == vm1_fixture.vm_id, \
            "Port %s has device id not set to %s on VM Attach" % (
            port1_obj, vm1_fixture.vm_id)
        assert 'compute:' in port1_obj['device_owner'] , \
            "Port %s has device-owner not set to compute:* on VM Attach" % (
                port1_obj)

    # end test_ports_device_owner_and_id

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
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
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
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
 
        # Test Triger: Shutoff VM       
        self.logger.info(
            'Executing nova stop to shutoff the VM %s' %(vm1_name))   
        vn1_vm1_fixture.vm_obj.stop()

        # Test specific verification 
        self.logger.info(
            'Verifying VM route entry is removed from agent after shutoff')
        assert vn1_vm1_fixture.verify_vm_routes_not_in_agent()
        self.logger.info(
            'Verifying VM route entry is removed from control node after shutoff')
        assert vn1_vm1_fixture.verify_vm_not_in_control_nodes()

        return True

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
        vIP= '10.10.10.10'
        result= False

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
        assert vm_test_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        
        self.config_aap(port1_obj, port2_obj, vIP)
        self.config_vrrp(vm1_fixture, vm2_fixture, vIP)
        time.sleep(10)
        self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP)
        
        self.logger.info('We will induce a mastership switch')
        port_dict = {'admin_state_up': False}                                                                                                                                                                                                                                 
        self.update_port(port1_obj['id'], port_dict)
        time.sleep(10)
        self.logger.info('%s should become the new VRRP master'%vm2_fixture.vm_name)
        self.vrrp_mas_chk(vm2_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm2_fixture, vIP) 
        
        self.logger.info('We will bring up the interface')
        port_dict1 = {'admin_state_up': True}                                                                                                                                                                                                                                 
        self.update_port(port1_obj['id'], port_dict1)
        time.sleep(10)
        self.logger.info('%s should become the VRRP master again'%vm1_fixture.vm_name)
        self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP) 

    # end test_aap_with_vrrp_admin_state_toggle

    @test.attr(type=['sanity']) 
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
        vIP= '10.10.10.10'
        result= False

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
        assert vm_test_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        
        self.config_aap(port1_obj, port2_obj, vIP)
        self.config_vrrp(vm1_fixture, vm2_fixture, vIP)
        time.sleep(10)
        self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP)
        
        self.logger.info('We will induce a mastership switch')
        kill_vrrp= 'nohup killall -9 vrrpd'
        reconfig_vrrp= 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p 8 10.10.10.10'
        reset_cmd= '/etc/init.d/networking restart'
        vm1_fixture.run_cmd_on_vm(cmds=[kill_vrrp], as_sudo=True)
        time.sleep(5)
        vm1_fixture.run_cmd_on_vm(cmds=[reset_cmd], as_sudo=True)
        vm1_fixture.run_cmd_on_vm(cmds=[reconfig_vrrp], as_sudo=True)
        time.sleep(10)
        self.logger.info('%s should become the new VRRP master'%vm2_fixture.vm_name)
        self.vrrp_mas_chk(vm2_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm2_fixture, vIP) 

        self.logger.info('We will reduce the VRRP priority on %s now'%vm2_fixture.vm_name)
        reconfig_vrrp2= 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p 6 10.10.10.10'
        vm2_fixture.run_cmd_on_vm(cmds=[kill_vrrp], as_sudo=True)
        time.sleep(5)
        vm2_fixture.run_cmd_on_vm(cmds=[reset_cmd], as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=[reconfig_vrrp2], as_sudo=True)
        time.sleep(10)
        self.logger.info('%s should become the VRRP master again'%vm1_fixture.vm_name)
        self.vrrp_mas_chk(vm1_fixture, vn1_fixture, vIP)
        self.verify_vrrp_action(vm_test_fixture, vm1_fixture, vIP) 

    # end test_aap_with_vrrp_priority_change
