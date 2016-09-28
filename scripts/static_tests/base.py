import test_v1
from vn_test import MultipleVNFixture
from fabric.api import run, hide, settings
from vm_test import MultipleVMFixture
#from vn_test import VNFixture
#from vm_test import VMFixture
from vnc_api.vnc_api import *
from policy_test import PolicyFixture
from tcutils.util import get_random_name
from scripts.securitygroup.verify import VerifySecGroup
from common.policy.config import ConfigPolicy
from common import isolated_creds
import os
import re
from time import sleep

class StaticTableBase(test_v1.BaseTestCase_v1, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(StaticTableBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(StaticTableBase, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(StaticTableBase, self).setUp()

    def tearDown(self):
        super(StaticTableBase, self).tearDown()

    def config_basic(self):

        vn1 = "vn1"
        vn2 = "vn2"
        vn_s = {'vn1': '10.1.1.0/24', 'vn2': ['20.1.1.0/24']}
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1,
                'src_ports': [0, -1],
                'dest_network': vn2,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]

        self.logger.info("Configure the policy with allow any")
        self.multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        vns = self.multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = self.multi_vn_fixture._vn_fixtures[0]
        (self.vn2_name, self.vn2_fix) = self.multi_vn_fixture._vn_fixtures[1]
        #self.config_policy_and_attach_to_vn(rules)

        self.pol1_fixture = self.config_policy("policy_static", rules)
        self.vn1_policy_fix = self.attach_policy_to_vn(self.pol1_fixture, self.vn1_fix)
        self.multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=1, vn_objs=vns, image_name='cirros-0.3.0-x86_64-uec',
            flavor='m1.tiny'))
        vms = self.multi_vm_fixture.get_all_fixture()
        (self.vm1_name, self.vm1_fix) = vms[0]
        (self.vm2_name, self.vm2_fix) = vms[1]

        vm3_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vns, vm_name="middle", node_name=None,
            image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))

    def add_interface_route_table(self):

        key, vm_uuid = self.vm1_fixture.get_vmi_ids().popitem()
        vm_uuid = str(vm_uuid)
        add_static_route_cmd = 'python provision_static_route.py --prefix ' + self.vm2_fixture.vm_ip + '/32' + ' --virtual_machine_interface_id ' + vm_uuid + \
            ' --tenant_name ' + self.inputs.project_name + ' --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table' + \
            ' --user ' + "admin" + ' --password ' + "contrail123"
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

            status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
            self.logger.debug("%s" % status)
            m = re.search(r'Creating Route table', status)
            assert m, 'Failed in Creating Route table'

    def add_network_table_to_vn(self):
        rt_vnc = RouteTable(name="network_table",parent_obj=self.project.project_obj)
        self.vnc_lib.route_table_create(rt_vnc)
        routes = []
        rt10 = RouteType(prefix = self.vm2_fixture.vm_ip + '/32', next_hop = self.vm3_fixture.vm_ip, next_hop_type='ip-address')
        routes.append(rt10)
        rt_vnc.set_routes(routes)

        vn_rt_obj = self.vnc_lib.virtual_network_read(id = self.vn1_fixture.uuid)
        vn_rt_obj.add_route_table(rt_vnc)
        self.vnc_lib.virtual_network_update(vn_rt_obj)

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

