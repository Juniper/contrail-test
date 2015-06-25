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
from user_test import UserFixture
from control_node import CNFixture
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.neutron.base import BaseNeutronTest
import test
from tcutils.util import *
from testtools import skipIf
from floating_ip import FloatingIPFixture


class TestRouters(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestRouters, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRouters, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_basic_router_behavior(self):
        '''Validate a router is able to route packets between two VNs
        Create a router
        Create 2 VNs, and a VM in each
        Add router port from each VN
        Ping between VMs
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn2_gateway = get_an_ip(vn2_subnets[0], 1)
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        router_dict = self.create_router(router_name)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        router_ports = self.quantum_h.get_router_interfaces(
            router_dict['id'])
        router_port_ips = [item['fixed_ips'][0]['ip_address']
                           for item in router_ports]
        assert vn1_gateway in router_port_ips and \
            vn2_gateway in router_port_ips,\
            'One or more router port IPs are not gateway IPs'\
            'Router ports : %s' % (router_ports)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
        self.delete_vn_from_router(router_dict['id'], vn1_fixture)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)
        self.add_vn_to_router(router_dict['id'], vn1_fixture, cleanup=False)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
    # end test_basic_router_behavior

    @preposttest_wrapper
    def test_router_rename(self):
        ''' Test router rename
        '''
        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_update_dict = {'name': "test_router"}
        router_rsp = self.quantum_h.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'name'] == "test_router", 'Failed to update router name'

    @preposttest_wrapper
    def test_router_admin_state_up(self):
        ''' Routing should not work with router's admin_state_up set to False
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        router_dict = self.create_router(router_name)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
        router_update_dict = {'admin_state_up': False}
        router_rsp = self.quantum_h.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'admin_state_up'] == False, 'Failed to update router admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(
            vn2_vm1_fixture.vm_ip, expectation=False), 'Routing works with admin_state_up set to False not expected'
        router_update_dict = {'admin_state_up': True}
        router_rsp = self.quantum_h.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'admin_state_up'], 'Failed to update router admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)

    @preposttest_wrapper
    def test_router_with_existing_ports(self):
        '''Validate routing works by using two existing ports
        Create a router
        Create 2 VNs, and a VM in each
        Create two ports in each of these VNs
        Attach these two ports to the router
        Ping between VMs
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn2_fixture.vn_id)
        router_dict = self.create_router(router_name)
        self.add_router_interface(router_dict['id'], port_id=port1_obj['id'])
        self.add_router_interface(router_dict['id'], port_id=port2_obj['id'])
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip),\
            'Ping between VMs across router failed!'
    # end test_router_with_existing_ports


    @preposttest_wrapper
    def test_router_with_alloc_pool_and_gateway(self):
        ''' Validate that with non-default alloc pool,
            router ports are created fine
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr()
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
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        router_dict = self.create_router(router_name)
        add_intf_result = self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert 'port_id' in add_intf_result.keys(), \
            'Router port not created when allocation-pool is set in Subnet'
        router_port_ip = self.quantum_h.get_port_ips(
            add_intf_result['port_id'])[0]
        vn1_gateway_ip = vn1_fixture.vn_subnet_objs[0]['gateway_ip']
        assert router_port_ip == vn1_gateway_ip,\
            'Gateway IP(%s) is not the same as Router intf IP(%s)' % (
                vn1_gateway_ip, router_port_ip)

        # Now test with custom gateway and alloc pool
        vn2_name = get_random_name('vn2')
        vn2_subnet_cidr = get_random_cidr()
        vn2_subnets = [{'cidr': vn1_subnet_cidr,
                        'allocation_pools': [
                            {'start': get_an_ip(vn1_subnet_cidr, 3),
                             'end': get_an_ip(vn1_subnet_cidr, 4)
                             },
                            {'start': get_an_ip(vn1_subnet_cidr, 6),
                                'end': get_an_ip(vn1_subnet_cidr, 6)
                             }
                        ],
                        'gateway_ip': get_an_ip(vn1_subnet_cidr, 10)
                        }]
        router_name = get_random_name('router2')
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        router_dict = self.create_router(router_name)
        add_intf_result = self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert 'port_id' in add_intf_result.keys(), \
            'Router port not created when allocation-pool is set in Subnet'
        router_port_ip = self.quantum_h.get_port_ips(
            add_intf_result['port_id'])[0]
        vn2_gateway_ip = vn2_fixture.vn_subnet_objs[0]['gateway_ip']
        assert router_port_ip == vn2_gateway_ip,\
            'Gateway IP(%s) is not the same as Router intf IP(%s)' % (
                vn2_gateway_ip, router_port_ip)

class TestRouterSNAT(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestRouterSNAT, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRouterSNAT, cls).tearDownClass()


    def is_test_applicable(self):
        if os.environ.get('MX_GW_TEST') != '1':
            return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        return (True, None)

    @test.attr(type=['ci_sanity'])
    @preposttest_wrapper
    def test_basic_snat_behavior_without_external_connectivity(self):
        '''Create an external network, a router
        set router-gateway to external network
        launch a private network and attach it to router
        validate left vm pinging right vm through Snat
       '''

        vm1_name = get_random_name('vm_left')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()

        ext_vn_name = get_random_name('ext_vn')
        ext_subnets = [get_random_cidr()]

        ext_vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=ext_vn_name,
                inputs=self.inputs,
                subnets=ext_subnets,
                router_external=True))

        ext_vn_fixture.verify_on_setup()

        vm2_name = get_random_name('vm_right')
        vm2_fixture = self.create_vm(ext_vn_fixture, vm2_name,
                                         image_name='ubuntu')
        vm2_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                ext_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert vm1_fixture.ping_with_certainty(
         vm2_fixture.vm_ip), 'Ping from vm_left to vm_right through snat failed'

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_basic_snat_behavior(self):
        '''Create an external network, a router
        set router-gateway to external network
        launch a private network and attach it to router
        validate ftp and ping to 8.8.8.8 from vm here
        '''
        vm1_name = get_random_name('vm_private')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert self.verify_snat(vm1_fixture)

    @preposttest_wrapper
    def test_basic_snat_behavior_with_fip(self):
        vm1_name = get_random_name('vm_private')
        vm2_name = get_random_name('vm_public')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name) 
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.create_vm(self.public_vn_obj.public_vn_fixture, vm2_name,
                                         image_name='ubuntu')
        vm2_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert self.verify_snat(vm1_fixture)
        assert self.verify_snat_with_fip(self.public_vn_obj, \
                vm2_fixture, vm1_fixture, connections= self.connections, 
                inputs = self.inputs)

    @preposttest_wrapper
    def test_basic_snat_behavior_with_diff_projects(self):
        project_name = get_random_name('project1')
        user_fixture = self.useFixture(UserFixture(
            connections=self.connections, username='test_usr',
            password='testusr123'))
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        user_fixture.add_user_to_tenant(project_name, 'test_usr', 'admin')
        assert project_fixture_obj.verify_on_setup()

        project_name1 = get_random_name('project2')
        user_fixture1 = self.useFixture(UserFixture(
            connections=self.connections, username='test_usr1',
            password='testusr1231'))
        project_fixture_obj1 = self.useFixture(ProjectFixture(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            project_name=project_name1,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        user_fixture1.add_user_to_tenant(project_name1, 'test_usr1', 'admin')
        assert project_fixture_obj1.verify_on_setup()

        proj_connection = project_fixture_obj.get_project_connections\
                            (username='test_usr', password='testusr123') 
        proj_connection1 = project_fixture_obj1.get_project_connections\
                            (username='test_usr1', password= 'testusr1231')
        vm1_name = get_random_name('vm1_vn1_private')
        vn1_name = get_random_name('vn1_private')
        vn1_subnets = [get_random_cidr()]
        vm2_name = get_random_name('vm2_vn2_private')
        vn2_name = get_random_name('vn2_private')
        vn2_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.admin_inputs.project_name)
        self.allow_default_sg_to_allow_all_on_project(project_name1)
        self.allow_default_sg_to_allow_all_on_project(project_name)
        vn1_fixture = self.useFixture(
                VNFixture(
                    project_name=project_name1,
                    connections=proj_connection1,
                    vn_name=vn1_name,
                    inputs=proj_connection1.inputs,
                    subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name1,
                    connections=proj_connection1,
                    vn_obj=vn1_fixture.obj,
                    vm_name=vm1_name))
        vm1_fixture.wait_till_vm_is_up()

        vn2_fixture = self.useFixture(
                VNFixture(
                    project_name=project_name,
                    connections=proj_connection,
                    vn_name=vn2_name,
                    inputs=proj_connection.inputs,
                    subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name,
                    connections=proj_connection,
                    vn_obj=vn2_fixture.obj,
                    vm_name=vm2_name))
        vm2_fixture.wait_till_vm_is_up()
        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name, tenant_id=project_fixture_obj1.uuid)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)

        assert self.verify_snat(vm1_fixture)
        router_name = get_random_name('router2')
        router_dict = self.create_router(router_name, tenant_id=project_fixture_obj.uuid)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
     
        assert self.verify_snat(vm2_fixture)

    @preposttest_wrapper
    def test_basic_snat_behavior_with_fip_and_diff_projects(self):
        project_name = get_random_name('project1')
        user_fixture = self.useFixture(UserFixture(
            connections=self.connections, username='test_usr',
            password='testusr123'))
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        user_fixture.add_user_to_tenant(project_name, 'test_usr', 'admin')
        assert project_fixture_obj.verify_on_setup()

        project_name1 = get_random_name('project2')
        user_fixture1 = self.useFixture(UserFixture(
            connections=self.connections, username='test_usr1',
            password='testusr1231'))
        project_fixture_obj1 = self.useFixture(ProjectFixture(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            project_name=project_name1,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        user_fixture1.add_user_to_tenant(project_name1, 'test_usr1', 'admin')
        assert project_fixture_obj1.verify_on_setup()

        proj_connection = project_fixture_obj.get_project_connections(
            'test_usr',
            'testusr123')
        proj_connection1 = project_fixture_obj1.get_project_connections(
            'test_usr1',
            'testusr1231')
        vm1_name = get_random_name('vm1_vn1_private')
        vn1_name = get_random_name('vn1_private')
        vn1_subnets = [get_random_cidr()]
        vm2_name = get_random_name('vm2_vn2_private')
        vn2_name = get_random_name('vn2_private')
        vn2_subnets = [get_random_cidr()]
        vm3_name = get_random_name('public_vm')
        self.allow_default_sg_to_allow_all_on_project(self.admin_inputs.project_name)
        self.allow_default_sg_to_allow_all_on_project(project_name1)
        self.allow_default_sg_to_allow_all_on_project(project_name)

        vn1_fixture = self.useFixture(
                VNFixture(
                    project_name=project_name1,
                    connections=proj_connection1,
                    vn_name=vn1_name,
                    inputs=proj_connection1.inputs,
                    subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name1,
                    connections=proj_connection1,
                    vn_obj=vn1_fixture.obj,
                    vm_name=vm1_name))
        vm1_fixture.wait_till_vm_is_up()

        vn2_fixture = self.useFixture(
                VNFixture(
                    project_name=project_name,
                    connections=proj_connection,
                    vn_name=vn2_name,
                    inputs=proj_connection.inputs,
                    subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name,
                    connections=proj_connection,
                    vn_obj=vn2_fixture.obj,
                    vm_name=vm2_name))
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture = self.useFixture(
                VMFixture(
                    project_name=self.admin_inputs.project_name,
                    connections=self.admin_connections,
                    vn_obj=self.public_vn_obj.public_vn_fixture.obj,
                    vm_name=vm3_name))
        vm3_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name, tenant_id=project_fixture_obj1.uuid)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert self.verify_snat(vm1_fixture)
        router_name = get_random_name('router2')
        router_dict = self.create_router(router_name, tenant_id=project_fixture_obj.uuid)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert self.verify_snat(vm2_fixture)
        assert self.verify_snat_with_fip(self.public_vn_obj, vm3_fixture, 
                    vm1_fixture, connections= self.admin_connections, inputs = self.admin_inputs)

        assert self.verify_snat_with_fip(self.public_vn_obj, vm3_fixture, 
                    vm1_fixture, connections= self.admin_connections, inputs = self.admin_inputs)

    @preposttest_wrapper
    def test_basic_snat_behavior_with_subnet_attach_detach(self):
        vm1_name = get_random_name('vm_private')
        vm2_name = get_random_name('vm_public')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm2_fixture = self.create_vm(self.public_vn_obj.public_vn_fixture, vm2_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
            router_dict['id'],
            self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert self.verify_snat(vm1_fixture)
        assert self.verify_snat_with_fip(self.public_vn_obj, 
                vm2_fixture, vm1_fixture, connections= self.connections, 
                inputs = self.inputs)

        self.delete_vn_from_router(router_dict['id'], vn1_fixture)

        assert not self.verify_snat(vm1_fixture, expectation=False)
        assert self.verify_snat_with_fip(self.public_vn_obj, vm2_fixture, 
                                             vm1_fixture, 
                                             connections=self.connections,
                                             inputs = self.inputs)

        self.add_vn_to_router(router_dict['id'], vn1_fixture, cleanup=False)
        assert self.verify_snat(vm1_fixture)
        assert self.verify_snat_with_fip(self.public_vn_obj, 
                    vm2_fixture, vm1_fixture, connections= self.connections, 
                    inputs = self.inputs)

    @preposttest_wrapper
    def test_basic_snat_behavior_with_different_vns(self):
        '''Create 2 private vns attached to external router
           detaching one vn from router should not effect snat for other vn
        '''
        vm1_name = get_random_name('vm1_private')
        vm2_name = get_random_name('vm2_private')
        vn1_name = get_random_name('vn1_private')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2_private')
        vn2_subnets = [get_random_cidr()]

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn2_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm2_fixture = self.create_vm(vn2_fixture, vm2_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
            router_dict['id'],
            self.public_vn_obj.public_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert self.verify_snat(vm1_fixture), "snat verification failed"
        assert self.verify_snat(vm2_fixture), "snat verification failed"

        self.delete_vn_from_router(router_dict['id'], vn1_fixture)

        assert not self.verify_snat(vm1_fixture, expectation=False), "snat verification\
                 expexted to fail since vn %s is deleted from router %s " \
                    % (vn1_name, router_name)
        assert self.verify_snat(vm2_fixture), "snat verification failed"
        self.add_vn_to_router(router_dict['id'], vn1_fixture, cleanup=False)
        assert self.verify_snat(vm1_fixture), "snat verification failed"
        assert self.verify_snat(vm2_fixture), "snat verification failed"

    def verify_snat_with_fip(self, public_vn_obj, public_vm_fix, \
                            vm_fixture, connections, inputs):
        fip_fixture = public_vn_obj.fip_fixture 
        ext_vn_fixture = public_vn_obj.public_vn_fixture
        result = True
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
                ext_vn_fixture.vn_id, vm_fixture.vm_id)
        fip = vm_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()


        if not public_vm_fix.ping_with_certainty(fip):
            result = result and False
            self.logger.error('Ping from %s to %s failed' %(
                              public_vm_fix.vm_name, vm_fixture.vm_name))
        public_vm_fix.put_pub_key_to_vm()
        vm_fixture.put_pub_key_to_vm()
        self.logger.info("scp files from public_vm %s to private vm %s " \
                    %(public_vm_fix.vm_name, vm_fixture.vm_name))
        result = result and public_vm_fix.check_file_transfer\
                    (dest_vm_fixture=vm_fixture, mode='scp', size='1000', fip = fip)
        fip_fixture.disassoc_and_delete_fip(fip_id)
        return result
