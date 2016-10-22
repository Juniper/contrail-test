import test_v1
from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
from common import isolated_creds
import os
import re
from contrailapi import ContrailVncApi

class StaticRouteTableBase(test_v1.BaseTestCase_v1):

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

    def config_basic(self):

        self.vn1_name = "left-vn"
        vn1_net = ['1.1.1.0/24']
        self.vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn1_name, inputs=self.inputs, subnets=vn1_net))
        self.vn2_name = "right-vn"
        vn2_net = ['2.2.2.0/24']
        self.vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn2_name, inputs=self.inputs, subnets=vn2_net))
        left_vm_name = "left-vm"
        right_vm_name = "right-vm"
        self.left_vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn1_fixture.obj, vm_name=left_vm_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))

        self.right_vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn2_fixture.obj, vm_name=right_vm_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))

        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()

        vm1_name = 'middle_vm1'

        self.vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj, self.vn2_fixture.obj], vm_name=vm1_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        self.vm1_fixture.wait_till_vm_is_up()
        cmd = 'echo 1 > /proc/sys/net/ipv4/ip_forward'
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

    def add_interface_route_table(self, src_vn_fix, dst_vn_fix, port1_fix):
        self.intf_table_to_right_obj = self.static_table_handle.create_route_table(prefixes = [str(dst_vn_fix.get_cidrs()[0])],\
                                        name="int_table_right", \
                                        parent_obj = self.project.project_obj, \
                                        )
        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn1_name
        self.static_table_handle.bind_vmi_to_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_right_obj)

        self.intf_table_to_left_obj = self.static_table_handle.create_route_table(prefixes = [str(src_vn_fix.get_cidrs()[0])],\
                                        name="int_table_left", \
                                        parent_obj = self.project.project_obj, \
                                        )
        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn2_name
        self.static_table_handle.bind_vmi_to_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_left_obj)

    def add_network_table_to_vn(self, vn1_fix, vn2_fix): 

        if str(self.vm1_fixture.vm_ips[0])[:-1] == str(self.right_vm_fixture.vm_ip)[:-1]:
            self.nw_handle_to_left =self.static_table_handle.create_route_table(prefixes = [self.left_vm_fixture.vm_ip + '/32'],\
                                            name="network_table_left_to_right", \
                                            next_hop = self.vm1_fixture.vm_ips[0], \
                                            parent_obj = self.project.project_obj, \
                                            next_hop_type='ip-address', \
                                            route_table_type = 'network', \
                                            )
            self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = vn2_fix.uuid, nw_route_table_obj=nw_handle)
        else:
            self.nw_handle_to_right =self.static_table_handle.create_route_table(prefixes = [self.right_vm_fixture.vm_ip + '/32'],\
                                            name="network_table_left_to_right", \
                                            next_hop = self.vm1_fixture.vm_ips[0], \
                                            parent_obj = self.project.project_obj, \
                                            next_hop_type='ip-address', \
                                            route_table_type = 'network', \
                                            )
            self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = vn1_fix.uuid, nw_route_table_obj=nw_handle)
        if str(self.vm1_fixture.vm_ips[1])[:-1] == str(self.right_vm_fixture.vm_ip)[:-1]:
            self.nw_handle_to_left =self.static_table_handle.create_route_table(prefixes = [self.left_vm_fixture.vm_ip + '/32'],\
                                            name="network_table_right_to_left", \
                                            next_hop = self.vm1_fixture.vm_ips[1], \
                                            parent_obj = self.project.project_obj, \
                                            next_hop_type='ip-address', \
                                            route_table_type = 'network', \
                                            )
            self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = vn2_fix.uuid, nw_route_table_obj=nw_handle)
        else:
            self.nw_handle_to_right =self.static_table_handle.create_route_table(prefixes = [self.right_vm_fixture.vm_ip + '/32'],\
                                            name="network_table_right_to_left", \
                                            next_hop = self.vm1_fixture.vm_ips[1], \
                                            parent_obj = self.project.project_obj, \
                                            next_hop_type='ip-address', \
                                            route_table_type = 'network', \
                                            )
            self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = vn1_fix.uuid, nw_route_table_obj=nw_handle)

    def unbind_interface_table(self, src_vn_fix, dst_vn_fix, port1_fix):

        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn1_name
        self.static_table_handle.unbind_vmi_from_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_right_obj)

        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn2_name
        self.static_table_handle.unbind_vmi_from_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_left_obj)

    def bind_interface_table(self, src_vn_fix, dst_vn_fix, port1_fix):
        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn1_name
        self.static_table_handle.bind_vmi_to_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_right_obj)

        id_entry = self.inputs.project_fq_name[0] + ':' + self.inputs.project_fq_name[1] + ':' + self.vn2_name
        self.static_table_handle.bind_vmi_to_interface_route_table(str(port1_fix.get_vmi_ids()[id_entry]), self.intf_table_to_right_obj)

    def unbind_network_table(self, src_vn_fix, dst_vn_fix):
        self.static_table_handle.unbind_vn_from_network_route_table(src_vn_fix.uuid, self.nw_handle_to_right)
        self.static_table_handle.unbind_vn_from_network_route_table(dst_vn_fix.uuid, self.nw_handle_to_left) 

    def bind_network_table(self, src_vn_fix, dst_vn_fix):
        self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = src_fix.uuid, nw_route_table_obj=self.nw_handle_to_right)
        self.static_table_handle.bind_network_route_table_to_vn(vn_uuid = dst_fix.uuid, nw_route_table_obj=self.nw_handle_to_left)

    def test_interop_with_neutron_router(self):
        router_dict = self.create_router('neutron_router')
        self.add_vn_to_router(router_dict['id'], self.vn1_fixture)
        self.add_vn_to_router(router_dict['id'], self.vn2_fixture)
        router_ports = self.quantum_h.get_router_interfaces(
            router_dict['id'])
        router_port_ips = [item['fixed_ips'][0]['ip_address']
                           for item in router_ports]
        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)
        self.delete_vn_from_router(router_dict['id'], self.vn1_fixture)
        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip,
                                                   expectation=False)
        self.add_vn_to_router(router_dict['id'], self.vn1_fixture, cleanup=False)
        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)

    def check_route_in_agent(self, expected_next_hops):

        (domain, project, vn) = self.vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[self.left_vm_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = self.left_vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=self.vn2_fixture.get_cidrs()[0][:-1][:-1][:-1], prefix='24')['path_list'][0]['nh']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent'
        else:
            self.logger.info('Route found in the Agent')
        number_of_nh = re.findall('itf',str(next_hops))
        if (len(number_of_nh) != expected_next_hops):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')

