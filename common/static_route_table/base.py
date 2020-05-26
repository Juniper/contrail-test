from common.neutron.base import BaseNeutronTest
from builtins import str
from vm_test import VMFixture
from vnc_api.vnc_api import *
from common import isolated_creds
import os
import re
from contrailapi import ContrailVncApi
from tcutils.util import get_random_name
from netaddr import IPNetwork

class StaticRouteTableBase(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(StaticRouteTableBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        #cls.vnc = ContrailVncApi(cls.vnc_lib, cls.logger)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(StaticRouteTableBase, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(StaticRouteTableBase, self).setUp()
        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)

    def tearDown(self):
        super(StaticRouteTableBase, self).tearDown()

    # create 3 vms, left, right middle. middle should sit in both vns
    def config_basic(self,vm2=False):
        self.vn1_fixture = self.create_vn(disable_dns=True)
        self.vn2_fixture = self.create_vn(disable_dns=True)
        self.vn1_name = self.vn1_fixture.vn_name
        self.vn2_name = self.vn2_fixture.vn_name
        self.left_vm_fixture = self.create_vm(self.vn1_fixture)
        self.right_vm_fixture = self.create_vm(self.vn2_fixture)
        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()

        vm1_name = 'middle_vm1'

        self.vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj,
                     self.vn2_fixture.obj], vm_name=vm1_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        self.vm1_fixture.wait_till_vm_is_up()
        cmd = 'echo 1 > /proc/sys/net/ipv4/ip_forward'
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        vm2_name = 'middle_vm2'
        if vm2:
            self.vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj,
                     self.vn2_fixture.obj], vm_name=vm2_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
            self.vm2_fixture.wait_till_vm_is_up()
            cmd = 'echo 1 > /proc/sys/net/ipv4/ip_forward'
            self.vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    
    # create int route table and bind it to the middle vm's vmi's
    def add_interface_route_table(self, src_vn_fix, dst_vn_fix, port1_fix=None, multiple_tables=1,si=False):
        self.intf_table_to_right_objs = []
        self.intf_table_to_left_objs = []
        self.right_prefixes = []
        self.left_prefixes = []   
        for i in range(0,multiple_tables):
            prefix = self.get_prefix(dst_vn_fix,i)
            self.right_prefixes.append(prefix)
            intf_table_to_right_obj = self.static_table_handle.create_route_table(
                prefixes=[prefix],
                name=get_random_name("int_table_right"),
                parent_obj=self.project.project_obj,
            )
            if not si:
                self.static_table_handle.bind_vmi_to_interface_route_table(
                    str(port1_fix.get_vmi_ids()[src_vn_fix.vn_fq_name]),
                    intf_table_to_right_obj)
            self.intf_table_to_right_objs.append(intf_table_to_right_obj)
            
            prefix = self.get_prefix(src_vn_fix,i)
            self.left_prefixes.append(prefix)
            intf_table_to_left_obj = self.static_table_handle.create_route_table(
                prefixes=[prefix],
                name=get_random_name("int_table_left"),
                parent_obj=self.project.project_obj,
            )
            if not si:
                self.static_table_handle.bind_vmi_to_interface_route_table(
                    str(port1_fix.get_vmi_ids()[dst_vn_fix.vn_fq_name]),
                    intf_table_to_left_obj)
            self.intf_table_to_left_objs.append(intf_table_to_left_obj)

    # delete the created int route table
    def delete_int_route_table(self, src_vn=None, dst_vn=None, port_fix=None, si=False):
        src_vn_fix = src_vn or self.vn1_fixture
        dst_vn_fix = dst_vn or self.vn2_fixture
        port_fix = port_fix or self.vm1_fixture
        if not si:
            self.unbind_interface_table(src_vn_fix, dst_vn_fix, port_fix)
        for intf_table in self.intf_table_to_right_objs + self.intf_table_to_left_objs:
            self.static_table_handle.delete_interface_route_table(
                intf_table.uuid)

    # attach the net route table to vn provided
    def add_network_table_to_vn(self, vn1_fix, vn2_fix, multiple_tables=1):
        self.nw_handle_to_left_objs = []
        self.nw_handle_to_right_objs = []
        self.right_prefixes = []
        self.left_prefixes = []   
        for i in range(0,multiple_tables):
            if str(self.vm1_fixture.vm_ips[0])[:-1] == str(self.right_vm_fixture.vm_ip)[:-1]:
                ip = self.get_prefix(vn1_fix,i)
                prefix = self.get_network_prefix_from_ip_mask(ip)
                nw_handle_to_left = self.static_table_handle.create_route_table(
                    prefixes=[prefix],
                    name=get_random_name("network_table_left_to_right"),
                    next_hop=self.vm1_fixture.vm_ips[0],
                    parent_obj=self.project.project_obj,
                    next_hop_type='ip-address',
                    route_table_type='network',
                )
                self.static_table_handle.bind_network_route_table_to_vn(
                    vn_uuid=vn2_fix.uuid,
                    nw_route_table_obj=nw_handle_to_left)
                self.left_prefixes.append(prefix)
            else:
                ip = self.get_prefix(vn2_fix,i)
                prefix = self.get_network_prefix_from_ip_mask(ip)
                nw_handle_to_right = self.static_table_handle.create_route_table(
                    prefixes=[prefix],
                    name=get_random_name("network_table_left_to_right"),
                    next_hop=self.vm1_fixture.vm_ips[
                        0],
                    parent_obj=self.project.project_obj,
                    next_hop_type='ip-address',
                    route_table_type='network',
                )
                self.static_table_handle.bind_network_route_table_to_vn(
                    vn_uuid=vn1_fix.uuid,
                    nw_route_table_obj=nw_handle_to_right)
                self.right_prefixes.append(prefix)
            if str(self.vm1_fixture.vm_ips[1])[:-1] == str(self.right_vm_fixture.vm_ip)[:-1]:
                ip = self.get_prefix(vn1_fix,i)
                prefix = self.get_network_prefix_from_ip_mask(ip)
                nw_handle_to_left = self.static_table_handle.create_route_table(
                    prefixes=[prefix],
                    name=get_random_name("network_table_right_to_left"),
                    next_hop=self.vm1_fixture.vm_ips[
                        1],
                    parent_obj=self.project.project_obj,
                    next_hop_type='ip-address',
                    route_table_type='network',
                )
                self.static_table_handle.bind_network_route_table_to_vn(
                    vn_uuid=vn2_fix.uuid,
                    nw_route_table_obj=nw_handle_to_left)
                self.left_prefixes.append(prefix)
            else:
                ip = self.get_prefix(vn2_fix,i)
                prefix = self.get_network_prefix_from_ip_mask(ip)
                nw_handle_to_right = self.static_table_handle.create_route_table(
                    prefixes=[prefix],
                    name=get_random_name("network_table_right_to_left"),
                    next_hop=self.vm1_fixture.vm_ips[
                        1],
                    parent_obj=self.project.project_obj,
                    next_hop_type='ip-address',
                    route_table_type='network',
                )
                self.static_table_handle.bind_network_route_table_to_vn(
                    vn_uuid=vn1_fix.uuid,
                    nw_route_table_obj=nw_handle_to_right)
                self.right_prefixes.append(prefix)
            self.nw_handle_to_left_objs.append(nw_handle_to_left)
            self.nw_handle_to_right_objs.append(nw_handle_to_right)
    # delete net route table
    def del_nw_route_table(self):
        self.unbind_network_table(self.vn1_fixture, self.vn2_fixture)
        for nw_handle_to_right in self.nw_handle_to_right_objs:
            self.static_table_handle.delete_network_route_table(
                nw_handle_to_right.uuid)
        for nw_handle_to_left in self.nw_handle_to_left_objs:
            self.static_table_handle.delete_network_route_table(
                nw_handle_to_left.uuid)

    # unbind the int route table from the port provided
    def unbind_interface_table(self, src_vn_fix, dst_vn_fix, port1_fix):
        for intf_table_to_right_obj in self.intf_table_to_right_objs:
            self.static_table_handle.unbind_vmi_from_interface_route_table(
                str(port1_fix.get_vmi_ids()[src_vn_fix.vn_fq_name]),
                intf_table_to_right_obj)

        for intf_table_to_left_obj in self.intf_table_to_left_objs:
            self.static_table_handle.unbind_vmi_from_interface_route_table(
                str(port1_fix.get_vmi_ids()[dst_vn_fix.vn_fq_name]),
                intf_table_to_left_obj)

    # bind a int route table to the port provided
    def bind_interface_table(self, src_vn_fix, dst_vn_fix, port1_fix):
        for intf_table_to_right_obj in self.intf_table_to_right_objs:
            self.static_table_handle.bind_vmi_to_interface_route_table(
                str(port1_fix.get_vmi_ids()[src_vn_fix.vn_fq_name]),
                intf_table_to_right_obj)
        for intf_table_to_left_obj in self.intf_table_to_left_objs:
            self.static_table_handle.bind_vmi_to_interface_route_table(
                str(port1_fix.get_vmi_ids()[dst_vn_fix.vn_fq_name]),
                intf_table_to_left_obj)

    # unbind the net route table from the vn provided
    def unbind_network_table(self, src_vn_fix, dst_vn_fix):
        for nw_handle_to_right in self.nw_handle_to_right_objs:
            self.static_table_handle.unbind_vn_from_network_route_table(
                src_vn_fix.uuid,
                nw_handle_to_right)
        for nw_handle_to_left in self.nw_handle_to_left_objs:
            self.static_table_handle.unbind_vn_from_network_route_table(
                dst_vn_fix.uuid,
                nw_handle_to_left)

    # bind the net route table to the vn provided
    def bind_network_table(self, src_vn_fix, dst_vn_fix):
        for nw_handle_to_right in self.nw_handle_to_right_objs:
            self.static_table_handle.bind_network_route_table_to_vn(
                vn_uuid=src_vn_fix.uuid,
                nw_route_table_obj=nw_handle_to_right)
        for nw_handle_to_left in self.nw_handle_to_left_objs:
            self.static_table_handle.bind_network_route_table_to_vn(
                vn_uuid=dst_vn_fix.uuid,
                nw_route_table_obj=nw_handle_to_left)

    # create a neutron router in addition to the static tables
    def neutron_router_test(self):
        router_dict = self.create_router('neutron_router')
        self.add_vn_to_router(router_dict['id'], self.vn1_fixture)
        self.add_vn_to_router(router_dict['id'], self.vn2_fixture)
        router_ports = self.quantum_h.get_router_interfaces(
            router_dict['id'])
        router_port_ips = [item['fixed_ips'][0]['ip_address']
                           for item in router_ports]
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip)
        self.delete_vn_from_router(router_dict['id'], self.vn1_fixture)
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip)
        self.add_vn_to_router(
            router_dict['id'],
            self.vn1_fixture,
            cleanup=False)
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip)

    # check the number of nexthops for the right route in left table
    def check_route_in_agent(self, expected_next_hops, prefix=None, vn_fix=None, vm_fix=None):
        
        vn_fix = vn_fix or self.vn1_fixture
        vm_fix = vm_fix or self.left_vm_fixture
        (domain, project, vn) = vn_fix.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[vm_fix.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = vm_fix.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn_fix.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        if not prefix:
            prefix = self.right_prefixes[0]
        cidr_prefix = prefix.split('/')
        next_hops = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id, ip=cidr_prefix[0], prefix=cidr_prefix[1])['path_list'][0]['nh']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent'
        else:
            self.logger.info('Route found in the Agent')
        number_of_nh = re.findall('nh_index', str(next_hops))
        if (len(number_of_nh) != expected_next_hops):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')
    
    def get_prefix(self,vn_fixture, i):
        return vn_fixture.get_cidrs()[0].split('/')[0] + '/' + str(int(vn_fixture.get_cidrs()[0].split('/')[-1]) - i)
    
    def get_network_prefix_from_ip_mask(self,ip):
        return str(IPNetwork(ip).cidr)
    
    def attach_interface_route_table_to_si(self, intf_table, si, interface='left'):
        intf_table.set_service_instance(si,ServiceInterfaceTag(interface_type='left'))
        self.vnc_lib.interface_route_table_update(intf_table)
    
    def detach_interface_route_table_from_si(self,intf_table, si):
        intf_table.del_service_instance(si)
        self.vnc_lib.interface_route_table_update(intf_table)
