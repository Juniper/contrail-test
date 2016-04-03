import test_v1
from vn_test import MultipleVNFixture
from vnc_api.vnc_api import *
#from vnc_api.vnc_api import VncApi
from vm_test import MultipleVMFixture
from fabric.api import run, hide, settings
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from scripts.securitygroup.verify import VerifySecGroup
from policy_test import PolicyFixture
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture, get_secgrp_id_from_name
from common import isolated_creds
from tcutils.util import get_random_name, copy_file_to_server, fab_put_file_to_vm
import os
import re
from physical_router_fixture import PhysicalRouterFixture
from time import sleep
from tcutils.verification_util import *

class XmppBase(test_v1.BaseTestCase_v1, VerifySecGroup, ConfigPolicy, VerificationUtilBase):

    @classmethod
    def setUpClass(cls):
        super(Md5Base, cls).setUpClass()
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

    def http_get(self, ip, path):
        handle = VerificationUtilBase(ip = ip, port = 8083, drv=XmlDrv) 
        response = None
        while True:
            response = handle.dict_get(path)
            if response != None:
                break
            print "Retry http get for %s after a second" % (path)
            time.sleep(1)
        return response

    def config_basic(self):

        vn61_name = "test_vnv6sr"
        vn61_net = ['2001::101:0/120']
        #vn1_fixture = self.config_vn(vn1_name, vn1_net)
        vn61_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn61_name, inputs=self.inputs, subnets=vn61_net))
        vn62_name = "test_vnv6dn"
        vn62_net = ['2001::201:0/120']
        #vn2_fixture = self.config_vn(vn2_name, vn2_net)
        vn62_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn62_name, inputs=self.inputs, subnets=vn62_net))
        vm61_name = 'source_vm'
        vm62_name = 'dest_vm'
        #vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        #vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
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
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
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

    def check_xmpp_status(self, node):

        path = 'Snh_BgpNeighborReq?domain=&ip_address=%s' % node
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'
        tbl = self.http_get(node, path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)
        for index in range(len(table_list)):
            if table_list[index]['encoding'] == 'XMPP':
                if table_list[index]['peer_address'] in self.inputs.compute_ips:
                    if not 'Established' in table_list[index]['state']:
                        self.logger.error("Node %s has a problem with XMPP status. Status is %s" % (table_list[index]['peer_address'], table_list[index]['state']))
                        return False
        return True

    def check_if_xmpp_connections_present(self, node):

        path = 'Snh_BgpNeighborReq?domain=&ip_address=%s' % node
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'
        tbl = self.http_get(node, path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)
        for index in range(len(table_list)):
            if table_list[index]['encoding'] == 'XMPP':
                if table_list[index]['peer_address'] in self.inputs.compute_ips:
                        return True
        return False

    def check_if_xmpp_auth_enabled(self, node, status = 'TLS'):

        path = 'Snh_BgpNeighborReq?domain=&ip_address=%s' % node
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'
        tbl = self.http_get(node, path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)
        for index in range(len(table_list)):
            if table_list[index]['encoding'] == 'XMPP':
                if table_list[index]['peer_address'] in self.inputs.compute_ips:
                    if not status in table_list[index]['auth_type']:
                        self.logger.error("Node %s has a problem with XMPP auth status. Auth status is %s" % (table_list[index]['peer_address'], table_list[index]['auth_type']))
                        return False

        return True
# end class XmppBase
