# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os

from tcutils.wrappers import preposttest_wrapper

from common.vrouter.base import BaseVrouterTest
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
import test

CIRROS_IMAGE_NAME='cirros-0.3.0-x86_64-uec'

class TestRoutes(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(TestRoutes, cls).setUpClass()
        cls.agent_inspect_h = cls.connections.agent_inspect

    @classmethod
    def tearDownClass(cls):
        super(TestRoutes, cls).tearDownClass()

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 2:
            return (False, 'Skipping test since atleast 2 compute nodes are'
                'required')
        return (True, None)
    # end is_test_applicable

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rt_table_scenario_1(self):
        '''
        In a VN, launch a VM each on two computes
        Add a shorter prefix intf static route to VM2
        Delete the VMs.
        The route table on compute1 should be removed

        '''
        prefixes = ['0.0.0.0/0']
        vn1_name = get_random_name()
        vn1_subnets = [get_random_cidr()]
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        port1_fixture = self.setup_vmi(vn1_fixture.vn_id)

        compute_1 = self.connections.orch.get_hosts()[0]
        compute_2 = self.connections.orch.get_hosts()[1]

        vm1_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     node_name=compute_1)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port1_fixture.uuid],
                                     node_name=compute_2)
        self.setup_interface_route_table(port1_fixture, prefixes=prefixes)
        vm1_fixture.verify_on_setup()
        vm2_fixture.wait_till_vm_is_up()

        # Let the VN fixture know about the vrfs
        vn1_fixture.verify_on_setup()
        # cleanup also checks for route removal
        vm1_fixture.cleanUp()
        self._remove_from_cleanup(vm1_fixture.cleanUp)
        self.logger.info('Validate that Vrouter Route table does get cleared')
    # end test_rt_table_scenario_1

    @preposttest_wrapper
    def test_rt_table_scenario_2(self):
        '''
        In a VN(8.1.0.0/16), launch vms VM1 VM2 VM3
        Add a covering static route 8.1.1.0/23 to VM2
        Add a larger prefix 8.1.1.0/22 to VM3
        Check that 8.1.1.10/32 points to nh of VM2
        Remove route on VM2
        Check that 8.1.1.10/32 points to nh of VM3
        Also check that only one route points to VM2's nh
        '''
        mask = 16
        vn1_name = get_random_name()
        vn1_subnets = ['8.1.0.0/%s' % (mask)]
        prefix_ip = str(vn1_subnets[0].split('/')[0])
        prefix = '%s/%s' %(prefix_ip, mask+2)
        prefixes = [prefix]
        prefixes = ['8.1.1.0/23']
        smaller_prefix = '%s/%s' %(prefix_ip, mask+1)
        smaller_prefix = '8.1.1.0/22'
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn_subnet_id = vn1_fixture.vn_subnet_objs[0]['id']

        vm1_ip = '8.1.1.1/16'
        vm2_ip = '8.1.10.1/16'
        vm3_ip = '8.1.20.1/16'
        unknown_ip = '8.1.1.10/16'

        port1_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm1_ip.split('/')[0]}])
        port2_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm2_ip.split('/')[0]}])
        port3_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm3_ip.split('/')[0]}])

        compute_1 = self.connections.orch.get_hosts()[0]
        compute_2 = self.connections.orch.get_hosts()[1]

        vm1_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port1_fixture.uuid],
                                     node_name=compute_1)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port2_fixture.uuid],
                                     node_name=compute_2)
        vm3_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port3_fixture.uuid],
                                     node_name=compute_2)
        intf_rtb_fixture = self.setup_interface_route_table(prefixes=prefixes)
        intf1_rtb_fixture = self.setup_interface_route_table(
                                prefixes=[smaller_prefix])
        self.add_interface_route_table(port2_fixture, intf_rtb_fixture.obj)
        self.add_interface_route_table(port3_fixture, intf1_rtb_fixture.obj)
        vm1_fixture.verify_on_setup()
        vm2_fixture.verify_on_setup()

        inspect_h = self.agent_inspect_h[vm1_fixture.vm_node_ip]
        lookup_prefix = '%s/32' % (unknown_ip.split('/')[0])
        route = self.get_vrouter_route(lookup_prefix,
                                       vn_fixture=vn1_fixture,
                                       inspect_h=inspect_h)
        assert route, ('No route seen in vrouter for %s' % (lookup_prefix))
        assert self.validate_prefix_is_of_vm_in_vrouter(
            inspect_h, lookup_prefix, vm2_fixture), (''
            'Vrouter NH validation failed, Check logs')

        # Remove the static route and check if nh is not in route table
        self.del_interface_route_table(port2_fixture, intf_rtb_fixture.uuid)

        # lookup_prefix should now point to nh of port3
        assert self.validate_prefix_is_of_vm_in_vrouter(inspect_h,
            lookup_prefix, vm3_fixture), (''
            'Vrouter NH validation failed, Check logs')
        # There should be one nh of VM2 only
        msg = 'nh of covering route is still present in route table'
        assert 1 == self.count_nh_label_in_route_table(vm1_fixture.vm_node_ip,
                                            vn1_fixture,
                                            route['nh_id'],
                                            route['label']), msg
        self.logger.info('NH of covering route is removed in vrouter '
                         'after the route is deleted')
    # end test_rt_table_scenario_2

    @preposttest_wrapper
    def test_rt_table_scenario_3(self):
        '''
        In a VN 10.1.0.0/16, launch vm VM1 on compute1
        Launch VM2 with 10.1.1.10 on Compute2
        Launch VM3 with 10.1.2.10 on Compute1 again
        Add static route 10.1.2.0/24 to point to VM2
        Delete VM3 followed by delete of static route mapping

        10.1.2.0/24 should now point to a discard nh 1 with label 0
        Check that VM2's nh's count is 1 only in vrouter

        '''
        mask = 16
        vn1_name = get_random_name()
        vn1_subnets = ['10.1.0.0/16']
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)

        compute_1 = self.connections.orch.get_hosts()[0]
        compute_2 = self.connections.orch.get_hosts()[1]

        vn_subnet_id = vn1_fixture.vn_subnet_objs[0]['id']
        vm2_ip = '10.1.1.10'
        vm3_ip = '10.1.2.10'
        prefix_ip = '10.1.2.0'
        prefix = '%s/24' %(prefix_ip)
        port2_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm2_ip.split('/')[0]}])
        port3_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm3_ip.split('/')[0]}])
        vm1_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     node_name=compute_1)
        vm1_fixture.verify_on_setup()
        vm2_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port2_fixture.uuid],
                                     node_name=compute_2)
        vm3_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port3_fixture.uuid],
                                     node_name=compute_1)

        intf_rtb_fixture = self.setup_interface_route_table(prefixes=[prefix])
        self.add_interface_route_table(port2_fixture, intf_rtb_fixture.obj)
        vm2_fixture.verify_on_setup()
        vm3_fixture.verify_on_setup()

        query_prefix = '%s/32' % (prefix_ip)
        route = self.get_vrouter_route(query_prefix,
                                       vn_fixture=vn1_fixture,
                                       node_ip=vm1_fixture.vm_node_ip)
        vm3_fixture.cleanUp()
        self._remove_from_cleanup(vm3_fixture.cleanUp)
        self.del_interface_route_table(port2_fixture, intf_rtb_fixture.uuid)

        # Route table compaction should happen in vrouter
        # This route should be pointing to a discard nh and not vm2's nh
        assert self.validate_discard_route(prefix, vn1_fixture,
                                           vm1_fixture.vm_node_ip)
        # There should be one nh of VM2 only
        msg = 'nh of covering route is still present in route table'
        assert 1 == self.count_nh_label_in_route_table(vm1_fixture.vm_node_ip,
                                            vn1_fixture,
                                            route['nh_id'],
                                            route['label']), msg

        self.logger.info('Vrouter route table bug check worked fine')
    # end test_rt_table_scenario_3

    @preposttest_wrapper
    def test_rt_table_scenario_4(self):
        '''
        In a VN(random cidr), launch vm VM1 on compute1
        Note the number of route table entries on compute1
        Add a VM VM2
        Remove VM2
        Check the number of route table entries on compute1 is same as before
        '''
        mask = random.randint(8,24)
        vn1_name = get_random_name()
        vn1_subnets = [get_random_cidr(mask)]
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)

        compute_1 = self.connections.orch.get_hosts()[0]
        compute_2 = self.connections.orch.get_hosts()[1]

        vn_subnet_id = vn1_fixture.vn_subnet_objs[0]['id']
        vm2_ip = get_random_ip(vn1_subnets[0])

        port2_fixture = self.setup_vmi(vn1_fixture.vn_id,
                fixed_ips=[{'subnet_id':vn_subnet_id,
                            'ip_address': vm2_ip.split('/')[0]}])
        vm1_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     node_name=compute_1)
        vm1_fixture.verify_on_setup()
        initial_size = self.get_vrouter_route_table_size(
                           vm1_fixture.vm_node_ip,
                           vn_fixture=vn1_fixture)
        vm2_fixture = self.create_vm(vn1_fixture,
                                     image_name=CIRROS_IMAGE_NAME,
                                     port_ids=[port2_fixture.uuid],
                                     node_name=compute_2)
        vm2_fixture.verify_on_setup()

        vm2_fixture.cleanUp()
        self._remove_from_cleanup(vm2_fixture.cleanUp)
        new_size = self.get_vrouter_route_table_size(
                           vm1_fixture.vm_node_ip,
                           vn_fixture=vn1_fixture)

        assert new_size == initial_size, ('Looks like route table compaction '
            ' has not happened in vrouter!')
        self.logger.info('Vrouter route table compaction worked fine')
    # end test_rt_table_scenario_4
