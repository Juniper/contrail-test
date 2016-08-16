import test_v1
from vn_test import MultipleVNFixture
from vnc_api.vnc_api import *
from vm_test import MultipleVMFixture
from fabric.api import run, hide, settings
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from policy_test import PolicyFixture
from common.policy.config import ConfigPolicy
import os
import re
from physical_router_fixture import PhysicalRouterFixture
from time import sleep
from tcutils.verification_util import *
from tcutils.contrail_status_check import *


class XmppBase(test_v1.BaseTestCase_v1, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(XmppBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(XmppBase, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(XmppBase, self).setUp()

    def tearDown(self):
        super(XmppBase, self).tearDown()

    def config_basic(self):
        vn61_name = "test_vnv6sr"
        vn61_net = ['2001::101:0/120']
        vn61_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn61_name, inputs=self.inputs, subnets=vn61_net))
        vn62_name = "test_vnv6dn"
        vn62_net = ['2001::201:0/120']
        vn62_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn62_name, inputs=self.inputs, subnets=vn62_net))
        vm61_name = 'source_vm'
        vm62_name = 'dest_vm'
        vm61_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn61_fixture.obj, vm_name=vm61_name, node_name=None,
            image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))

        vm62_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn62_fixture.obj, vm_name=vm62_name, node_name=None,
            image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))
        vm61_fixture.wait_till_vm_is_up()
        vm62_fixture.wait_till_vm_is_up()

        rule = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn61_name,
                'src_ports': [0, -1],
                'dest_network': vn62_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        policy_name = 'allow_all'
        policy_fixture = self.config_policy(policy_name, rule)

        vn61_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn61_fixture)
        vn62_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn62_fixture)

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
            vn_name_net=vn_s, project_name=self.inputs.project_name))
        vns = self.multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = self.multi_vn_fixture._vn_fixtures[0]
        (self.vn2_name, self.vn2_fix) = self.multi_vn_fixture._vn_fixtures[1]
        self.config_policy_and_attach_to_vn(rules)

        self.multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=1, vn_objs=vns, image_name='cirros-0.3.0-x86_64-uec',
            flavor='m1.tiny'))
        vms = self.multi_vm_fixture.get_all_fixture()
        (self.vm1_name, self.vm1_fix) = vms[0]
        (self.vm2_name, self.vm2_fix) = vms[1]

    def config_policy_and_attach_to_vn(self, rules):
        randomname = get_random_name()
        policy_name = "sec_grp_policy_" + randomname
        policy_fix = self.config_policy(policy_name, rules)
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn2_fix)

    def enable_auth_on_cluster(self):
        for node in self.inputs.bgp_control_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-control.conf',
                operation='set',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                value='true',
                node=node,
                service='supervisor-control')
        for node in self.inputs.compute_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-vrouter-agent.conf',
                operation='set',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                value='true',
                node=node,
                service='supervisor-vrouter')

    def update_contrail_conf(
        self,
        conf_file,
        operation,
        section,
        knob,
        node,
        service,
            value=None):

        if operation == 'del':
            cmd = 'openstack-config --del %s %s %s' % (conf_file,
                                                       section, knob)
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
        if operation == 'set':
            cmd = 'openstack-config --set %s %s %s %s' % (conf_file,
                                                          section, knob, value)
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
        self.inputs.restart_service(service, [node])
        cluster_status, error_nodes = ContrailStatusChecker(
        ).wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (
            error_nodes)

    def check_xmpp_status(self, node):

        result = True
        self.cn_inspect = self.connections.cn_inspect
        for index in range(6):
            try:
                xmpp_match = re.findall(
                    "XMPP",
                    str(self.cn_inspect[node].get_cn_bgp_neigh_entry()))
                if len(xmpp_match) > len(self.inputs.compute_ips):
                    break
                else:
                    sleep(5)
            except:
                sleep(5)

        table_list = self.cn_inspect[node].get_cn_bgp_neigh_entry()
        if isinstance(table_list, dict):
            dict_item = table_list
            table_list = []
            table_list.append(dict_item)
        for item in range(len(table_list)):
            if table_list[item]['encoding'] == 'XMPP':
                if table_list[item]['peer_address'] in self.inputs.compute_ips:
                    if not 'Established' in table_list[item]['state']:
                        self.logger.error(
                            "Node %s has a problem with XMPP status. Status is %s" %
                            (table_list[item]['peer_address'], table_list[item]['state']))
                        result = False
        return result

    def check_if_xmpp_connections_present(self, node):

        self.cn_inspect = self.connections.cn_inspect
        for index in range(6):
            try:
                xmpp_match = re.findall(
                    "XMPP",
                    str(self.cn_inspect[node].get_cn_bgp_neigh_entry()))
                if len(xmpp_match) > len(self.inputs.compute_ips):
                    break
                else:
                    sleep(5)
            except:
                sleep(5)

        table_list = self.cn_inspect[node].get_cn_bgp_neigh_entry()
        if isinstance(table_list, dict):
            dict_item = table_list
            table_list = []
            table_list.append(dict_item)

        for item in range(len(table_list)):
            if "encoding" in table_list[item]:
                if table_list[item]['encoding'] == 'XMPP':
                    if table_list[item]['peer_address'] in self.inputs.compute_ips:
                        return True
        return False

    def check_if_xmpp_auth_enabled(self, node, status='TLS'):
        result = True
        self.cn_inspect = self.connections.cn_inspect
        table_list = self.cn_inspect[node].get_cn_bgp_neigh_entry()
        if isinstance(table_list, dict):
            dict_item = table_list
            table_list = []
            table_list.append(dict_item)

        for item in range(len(table_list)):
            if table_list[item]['encoding'] == 'XMPP':
                if table_list[item]['peer_address'] in self.inputs.compute_ips:
                    if not status in table_list[item]['auth_type']:
                        self.logger.error(
                            "Node %s has a problem with XMPP auth status. Auth status is %s" %
                            (table_list[item]['peer_address'], table_list[item]['auth_type']))
                        result = False

        return result

    def check_if_cluster_has_xmpp(self):

        result = False
        for node in self.inputs.bgp_control_ips:
            if self.check_if_xmpp_connections_present(node):
                result = True
        return result

# end class XmppBase
