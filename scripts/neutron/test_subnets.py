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
from tcutils.util import get_an_ip


class TestSubnets(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestSubnets, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestSubnets, cls).tearDownClass()

    @preposttest_wrapper
    def test_subnet_host_routes(self):
        '''Validate host_routes parameter in subnet
        Create a VN with subnet having a host-route
        Create a VM using that subnet
        Check the route table in the VM

        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
        dest_ip = '8.8.8.8'
        destination = dest_ip + '/32'
        # nh IP does not matter, it will always be the default gw
        nh = '30.1.1.10'
        vn1_subnets = [{'cidr': vn1_subnets[0],
                        'host_routes': [{'destination': destination,
                                         'nexthop': nh},
                                        {'destination': '0.0.0.0/0',
                                         'nexthop': vn1_gateway}],
                        }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert dest_ip in route_output, 'Route pushed from DHCP is not '\
            'present in Route table of the VM'
        self.logger.info('Route pushed from DHCP is present in route-table '
                         ' of the VM..OK')

        self.logger.info('Updating the subnet to remove the host routes')
        vn1_subnet_dict = {'host_routes': []}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
                                  vn1_subnet_dict)
        time.sleep(5)
        vm1_fixture.reboot()
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert dest_ip not in route_output, 'Route pushed from DHCP is still '\
            'present in Route table of the VM'
        self.logger.info('Route table in VM does not have the host routes..OK')
        assert vn1_gateway in route_output, 'Default Gateway is missing the \
                        route table of the VM'
    # end test_subnet_host_routes

    @preposttest_wrapper
    def test_dns_nameservers(self):
        '''Validate dns-nameservers parameter in subnet
        Create a VN with subnet having a dns-nameserver
        Create a VM using that subnet
        Check the resolv.conf in the VM

        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
        vn1_default_dns = get_an_ip(vn1_subnets[0], 2)
        dns1_ip = '8.8.8.8'
        dns2_ip = '4.4.4.4'
        vn1_subnets = [{'cidr': vn1_subnets[0],
                        'dns_nameservers': [dns1_ip, dns2_ip]
                        }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        resolv_output = output.values()[0]
        assert dns1_ip in resolv_output, 'DNS Server IP %s not seen in '\
            'resolv.conf of the VM' % (dns1_ip)
        assert dns2_ip in resolv_output, 'DNS Server IP %s not seen in '\
            'resolv.conf of the VM' % (dns2_ip)
        self.logger.info('DNS Server IPs are seen in resolv.conf of the VM')

        self.logger.info('Updating the subnet to remove the dns servers')
        vn1_subnet_dict = {'dns_nameservers': []}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
                                  vn1_subnet_dict)
        vm1_fixture.reboot()
        time.sleep(5)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        dns_output = output.values()[0]
        assert dns1_ip not in dns_output, 'DNS Server IP %s still seen '\
            ' in resolv.conf of the VM' % (dns1_ip)
        assert dns2_ip not in dns_output, 'DNS Server IP %s still seen '\
            ' in resolv.conf of the VM' % (dns2_ip)
        assert vn1_default_dns in dns_output, 'Default DNS Server %s is missing in the '\
            'resolv.conf of the VM' % (vn1_default_dns)
        self.logger.info('resolv.conf in VM has the default DNS Server..OK')
    # end test_dns_nameservers

    @preposttest_wrapper
    def test_gateway(self):
        '''Validate that GW of first address of the subnet cidr is chosen by
        default.
        Check that gw cannot be from within the allocation pool
        Check that custom addresses can be given
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr()
        vn1_gateway = get_an_ip(vn1_subnet_cidr, 1)
        vn1_subnets = [{'cidr': vn1_subnet_cidr, 'allocation_pools': [
            {'start': get_an_ip(vn1_subnet_cidr, 3), 'end': get_an_ip(vn1_subnet_cidr, 10)}], }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert vn1_gateway in route_output, 'First address of CIDR %s : %s'\
            'is NOT set as gateway on the VM' % (
                vn1_subnet_cidr, vn1_gateway)
        self.logger.info(
            'First address of CIDR %s : %s'
            'is set as gateway on the VM' %
            (vn1_subnet_cidr, vn1_gateway))

        # Updating the gateway is not supported. Comment it for now
#        self.logger.info('Try updating gateway ip to be within the alloc pool')
#        vn1_subnet_dict = {'gateway_ip' : get_an_ip(vn1_subnet_cidr,5)}
#        self.assertRaises(CommonNetworkClientException,
#                                vn1_fixture.update_subnet,
#                                vn1_fixture.vn_subnet_objs[0]['id'],
#                                vn1_subnet_dict)

        # Updating Gateway is not supported. for now, disable the below code
#        self.logger.info('Updating to valid GW IP and checking if VM gets it')
#        gw_plus1_ip = get_an_ip(vn1_subnet_cidr, 2)
#        vn1_subnet_dict = {'gateway_ip' : gw_plus1_ip}
#        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
#                                  vn1_subnet_dict)
#        vm1_fixture.reboot()
#        time.sleep(5)
#        assert vm1_fixture.wait_till_vm_is_up()
#        output = vm1_fixture.run_cmd_on_vm(['route -n| grep ^0.0.0.0'])
#        route_output = output.values()[0]
#        assert gw_plus1_ip in route_output, 'VM has not got the modified GWIP'\
#                            ' %s' % (gw_plus1_ip)
#        self.logger.info('VM has got the modified GW IP %s' % (gw_plus1_ip))

# Disable gateway
#        subnet_id = vn1_fixture.vn_subnet_objs[0]['id']
#        self.logger.info('Disabling gateway on subnet %s' % (subnet_id))
#        vn1_subnet_dict = {'gateway_ip' : None}
#        vn1_fixture.update_subnet(subnet_id, vn1_subnet_dict)
#        vm1_fixture.reboot()
#        time.sleep(5)
#        assert vm1_fixture.wait_till_vm_is_up()
#        output = vm1_fixture.run_cmd_on_vm(['route -n| grep ^0.0.0.0'])
#        route_output = output.values()[0]
#        assert vn1_gateway not in route_output, \
#            'VM got the GWIP %s even when GW is disabled' % (vn1_gateway)
#        self.logger.info('VM did not get GW IP %s..OK' % (vn1_gateway))
    # end test_gateway

    @preposttest_wrapper
    def test_allocation_pools(self):
        '''Validate allocation pool config

        Create a VN with subnet having allocation pool
        Verify VMs are only created when alloc pool is available
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr('29')
        vn1_gateway = get_an_ip(vn1_subnet_cidr, 1)
        # Leave out the second IP...start from 3
        vn1_subnets = [{'cidr': vn1_subnet_cidr,
                        'allocation_pools': [
                            {'start': get_an_ip(vn1_subnet_cidr, 3),
                             'end': get_an_ip(vn1_subnet_cidr, 4)
                             },
                            {'start': get_an_ip(vn1_subnet_cidr, 6),
                                'end': get_an_ip(vn1_subnet_cidr, 6)
                             }
                        ],
                        }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_is_up(), 'VM is not up on reboot!'
        assert vm1_fixture.vm_ip == get_an_ip(vn1_subnet_cidr, 3),\
            'IP of VM %s should have been %s. It is %s' % (
                vm1_fixture.vm_name, get_an_ip(vn1_subnet_cidr, 3),
                vm1_fixture.vm_ip)

        vm2_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm2_fixture.wait_till_vm_is_up(), 'VM is not up on reboot!'
        assert vm2_fixture.vm_ip == get_an_ip(vn1_subnet_cidr, 4),\
            'IP of VM %s should have been %s. It is %s' % (
                vm2_fixture.vm_name, get_an_ip(vn1_subnet_cidr, 4),
                vm2_fixture.vm_ip)

        vm3_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm3_fixture.wait_till_vm_is_up(), 'VM is not up on reboot!'
        assert vm3_fixture.vm_ip == get_an_ip(vn1_subnet_cidr, 6),\
            'IP of VM %s should have been %s. It is %s' % (
                vm3_fixture.vm_name, get_an_ip(vn1_subnet_cidr, 6),
                vm3_fixture.vm_ip)

        vm4_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm4_fixture.wait_till_vm_status('ERROR'), 'VM %s should '\
            'have failed since allocation pool is full' % (vm4_fixture.vm_name)
    # end test_allocation_pools

    @preposttest_wrapper
    def test_enable_dhcp(self):
        '''Validate dhcp-enable parameter in subnet
        Check that dhcp-enable is set to true by default
        Create a VN with subnet where dhcp is disabled
        Create a VM using that subnet
        Validate that the VM does not get an IP

        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
        vn1_subnets = [{'cidr': vn1_subnets[0], }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.vn_subnet_objs[0]['enable_dhcp'],\
            'DHCP is not enabled by default in the Subnet!'

        # Update subnet to disable dhcp
        vn1_subnet_dict = {'enable_dhcp': False}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
                                  vn1_subnet_dict)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_up(),\
            'Unable to detect if VM booted up using console log'

        console_log = vm1_fixture.get_console_output()
        assert 'No lease, failing' in console_log,\
            'Failure while determining if VM got a DHCP IP. Log : %s' % (
                console_log)
        self.logger.info('VM did not get an IP when DHCP is disabled..OK')

        # Update Subnet to enable DHCP
        vn1_subnet_dict = {'enable_dhcp': True}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
                                  vn1_subnet_dict)
        vm1_fixture.reboot()
        time.sleep(5)
        assert vm1_fixture.wait_till_vm_is_up(), 'VM is not up on reboot!'

        result_output = vm1_fixture.run_cmd_on_vm(['ifconfig -a'])
        output = result_output.values()[0]
        assert vm1_fixture.vm_ip in output,\
            'VM did not get an IP %s after enabling DHCP' % (vm1_fixture.vm_ip)
        self.logger.info('VM got DHCP IP after subnet-dhcp is enabled..OK')

    # end test_enable_dhcp

    @preposttest_wrapper
    def test_ip_allocation_order(self):
        '''Validate the order of IPs allocated in case of multiple subnets

        Create a VN with 2 subnets
        First VM created in the VN (using net-id) should pick subnet1
        Create second VM in VN (using second subnet). It should pick subnet2
        Create a third VM in VN (using net-id). It should pick from subnet1
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_list = [get_random_cidr(), get_random_cidr()]
        vn1_subnets = [{'cidr': vn1_subnet_list[0], },
                       {'cidr': vn1_subnet_list[1], }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_vm3_name = get_random_name('vn1-vm3')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)

        self.logger.info('Create first VM in the VN')
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_status('ACTIVE'),\
            'VM %s is not active' % (vm1_fixture.vm_name)

        # Create a second VM in second subnet
        port_obj = self.create_port(net_id=vn1_fixture.vn_id,
                    subnet_id=vn1_fixture.vn_subnet_objs[1]['id'])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                     image_name='cirros-0.3.0-x86_64-uec',
                                     port_ids=[port_obj['id']])
        assert vm2_fixture.wait_till_vm_status('ACTIVE'),\
            'VM %s is not active' % (vm2_fixture.vm_name)

        # Create third VM and check if it gets IP from first subnet
        self.logger.info('Create a third VM in the VN')
        vm3_fixture = self.create_vm(vn1_fixture, vn1_vm3_name,
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm3_fixture.wait_till_vm_is_up(),\
            'VM %s is not fully up' % (vm3_fixture.vm_name)
        assert IPAddress(vm3_fixture.vm_ip) in IPNetwork(vn1_subnet_list[0]),\
            'IP for third VM %s should be have been picked from subnet %s. '\
            'It is %s' % (vm3_fixture.vm_name, vn1_subnet_list[0],
                          vm3_fixture.vm_ip)
    # end test_ip_allocation_order

    @preposttest_wrapper
    def test_subnet_rename(self):
        '''Launch a vn and rename the associated subnet
           check if subnet name gets updated or not
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr()
        vn1_subnets = [{'cidr': vn1_subnet_cidr}]
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        subnet_dict = {'name': "test_subnet"}
        subnet_rsp = self.quantum_h.update_subnet(
            vn1_fixture.vn_subnet_objs[0]['id'],
            subnet_dict)
        assert subnet_rsp['subnet'][
            'name'] == "test_subnet", 'Failed to update subnet name'

    # end test_subnet_rename
