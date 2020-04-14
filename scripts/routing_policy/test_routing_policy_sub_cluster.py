from __future__ import absolute_import
from .base import RPBase
from builtins import str
from tcutils.wrappers import preposttest_wrapper
import test
import time
from common.bgpaas.base import BaseBGPaaS
from tcutils.util import *


class TestRPSubCluster(RPBase, BaseBGPaaS):

    @classmethod
    def setUpClass(cls):
        super(TestRPSubCluster, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRPSubCluster, cls).tearDownClass()

    def setUp(self):
        super(TestRPSubCluster, self).setUp()

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_subcluster_ext_community(self):
        '''
        1. Launch VMs in subcluster pop1 and pop2
        2. Validate that a valid subcluster extended community is associated with the routes created in subcluster
           pop1 and pop2.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get primary route subcluster ext-comm in subcluster pop1
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='false')
        if sub_cluster == '':
            assert False, "FAIL: subcluster ext community not present in primary route %s"\
                % (ret_dict['test_vm_pop1'].vm_ip)

        # Validate subcluster ext community [subcluster:<asn>:<id>]
        sc_asn = int(sub_cluster.split(":")[1])
        sc_id = int(sub_cluster.split(":")[2])
        if self.inputs.enable_4byte_as:
            assert sc_asn in range(
                1, 0xffffffff) and sc_id in range(
                1, 0xffff), "FAIL: invalid subcluster"
        else:
            assert sc_asn in range(
                1, 0xffff) and sc_id in range(
                1, 0xffffffff), "FAIL: invalid subcluster"

        self.logger.info(
            "PASS: subcluster %s present in route %s" %
            (sub_cluster, ret_dict['test_vm_pop1'].vm_ip))

        # Get primary route subcluster ext-comm in subcluster pop2
        cn_entries = self.cn_inspect[control_nodes['pop2'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop2'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop2_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='false')
        if sub_cluster == '':
            assert False, "FAIL: subcluster ext community not present in primary route %s"\
                % (ret_dict['test_vm_pop2'].vm_ip)
        self.logger.info(
            "PASS: subcluster %s present in route %s" %
            (sub_cluster, ret_dict['test_vm_pop2'].vm_ip))

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_subcluster_ext_community_primary_route(self):
        '''
        1. Create a routing policy with interface and subcluster ext-community match.
        2. Launch VMs in subcluster pop1 and pop2
        3. Validate that the policy get applied to the primary routes in subcluster pop1 and pop2.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get primary route subcluster ext-comm in subcluster pop1
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='false')
        initial_local_pref = self.get_local_pref(
            cn_entries, is_replicated='false')
        if sub_cluster == '':
            assert False, "FAIL: subcluster ext community not present in primary route in pop1"
        # Apply routing-policy to change local-pref for primary routes in pop1
        # if it matches subcluster-extended community
        config_dicts = {
            'vn_fixture': ret_dict['vn_pop1_fixture'],
            'from_term': 'protocol',
            'sub_from': 'interface',
            'from_term_community': 'ext_community_list',
            'sub_from_community': [sub_cluster],
            'to_term': 'local-preference',
            'sub_to': initial_local_pref + 10}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        # Check if local-pref is changed
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        new_local_pref = self.get_local_pref(cn_entries, is_replicated='false')
        self.logger.info(
            'subcluster = %s, initial_local_pref = %d, new_local_pref = %d' %
            (sub_cluster, initial_local_pref, new_local_pref))
        if new_local_pref != initial_local_pref + 10:
            assert False, "Error: Routing-Policy not applied on primary routes in subcluster pop1"
        self.logger.info(
            "PASS: routing-policy is applied correctly for primary route  %s" %
            (ret_dict['test_vm_pop1'].vm_ip))

        # Get primary route subcluster ext-comm in subcluster pop2
        cn_entries = self.cn_inspect[control_nodes['pop2'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop2'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop2_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='false')
        initial_local_pref = self.get_local_pref(
            cn_entries, is_replicated='false')
        if sub_cluster == '':
            assert False, "FAIL: subcluster ext community not present in primary route in pop2"
        # Apply routing-policy to change local-pref for primary routes in pop2
        # if it matches subcluster-extended community
        config_dicts = {
            'vn_fixture': ret_dict['vn_pop2_fixture'],
            'from_term': 'protocol',
            'sub_from': 'interface',
            'from_term_community': 'ext_community_list',
            'sub_from_community': [sub_cluster],
            'to_term': 'local-preference',
            'sub_to': initial_local_pref + 20}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        # Check if local-pref is changed
        cn_entries = self.cn_inspect[control_nodes['pop2'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop2'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop2_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)
        new_local_pref = self.get_local_pref(cn_entries, is_replicated='false')
        self.logger.info(
            'subcluster = %s, initial_local_pref = %d, new_local_pref = %d' %
            (sub_cluster, initial_local_pref, new_local_pref))
        if new_local_pref != initial_local_pref + 20:
            assert False, "Error: Routing-Policy not applied on primary routes in subcluster pop2"
        self.logger.info(
            "PASS: routing-policy is applied correctly for primary route %s" %
            (ret_dict['test_vm_pop2'].vm_ip))

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_subcluster_secondary_route_no_subcluster_ext_community(self):
        '''
        1. Create a routing policy with bgp match.
        2. Launch VMs in all nodes
        3. Advertise routes from main control-node to subcluster pop1 control-node.
        3. Validate that the policy get applied to the secondary routes not associated to any subcluster.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get local-pref for secondary route coming from main control-node.
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_main'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        initial_local_pref = self.get_local_pref(
            cn_entries, is_replicated='true')
        if initial_local_pref == -1:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)

        # Apply routing-policy to change local-pref for secondary route(bgp)
        # if no subcluster extended community is associated with the route.
        config_dicts = {
            'vn_fixture': ret_dict['vn_pop1_fixture'],
            'from_term': 'protocol',
            'sub_from': 'bgp',
            'to_term': 'local-preference',
            'sub_to': initial_local_pref + 30}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        # Check if local-pref is changed
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_main'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_main'].vm_ip)
        new_local_pref = self.get_local_pref(cn_entries, is_replicated='true')
        self.logger.info(
            'initial_local_pref = %d, new_local_pref = %d' %
            (initial_local_pref, new_local_pref))
        if new_local_pref != initial_local_pref + 30:
            assert False, "Error: Routing-Policy not applied on secondary routes"
        self.logger.info(
            "PASS: routing-policy is applied correctly for secondary routes")

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_inter_subcluster(self):
        '''
        1. Create a routing policy with bgp match.
        2. Launch VMs in all nodes.
        3. Advertise routes coming from subcluster pop2 coming via main control-node.
        3. Validate that the policy get applied to the secondary routes coming from
           different subcluster.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get local-pref for secondary route coming from subcluster pop2.
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop2'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='true')
        initial_local_pref = self.get_local_pref(
            cn_entries, is_replicated='true')
        if initial_local_pref == -1:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)

        # Apply routing-policy to change local-pref for secondary route(bgp)
        # if subcluster associated with the route is diffrent.
        config_dicts = {
            'vn_fixture': ret_dict['vn_pop1_fixture'],
            'from_term': 'protocol',
            'sub_from': 'bgp',
            'from_term_community': 'ext_community_list',
            'sub_from_community': [sub_cluster],
            'to_term': 'local-preference',
            'sub_to': initial_local_pref + 40}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        # Check if local-pref is changed
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop2'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop2'].vm_ip)
        new_local_pref = self.get_local_pref(cn_entries, is_replicated='true')
        self.logger.info(
            'subcluster %s, initial_local_pref %d, new_local_pref = %d' %
            (sub_cluster, initial_local_pref, new_local_pref))
        if new_local_pref != initial_local_pref + 40:
            assert False, "Error: Routing-Policy not applied on secondary route %s"\
                % (ret_dict['test_vm_pop2'].vm_ip)
        self.logger.info(
            "PASS: routing-policy is applied correctly for secondary route %s" %
            (ret_dict['test_vm_pop2'].vm_ip))

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_intra_subcluster(self):
        '''
        1. Create a routing policy with bgp match.
        2. Launch VMs in all nodes
        3. Validate that the policy doesn't get applied to the secondary routes coming
           from a control-node from the same subcluster. pop1 has 2 control-nodes.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get secondary route coming from another control-node from the same
        # subcluster pop1
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='true')
        initial_local_pref = self.get_local_pref(
            cn_entries, is_replicated='true')
        if initial_local_pref == -1:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        if sub_cluster == '':
            assert False, "subcluster ext community not present in route"

        # Apply routing-policy to validate that routing-policy is not applied
        # to secondary routes if subcluster id matches with that assocaited
        # with the route.
        config_dicts = {
            'vn_fixture': ret_dict['vn_pop1_fixture'],
            'from_term_community': 'ext_community_list',
            'sub_from_community': [sub_cluster],
            'from_term': 'protocol',
            'sub_from': 'bgp',
            'to_term': 'local-preference',
            'sub_to': initial_local_pref + 50}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        # Verify that local-pref is not changed
        cn_entries = self.cn_inspect[control_nodes['pop1'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_pop1_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_main'].vm_ip)
        new_local_pref = self.get_local_pref(cn_entries, is_replicated='true')
        self.logger.info(
            'subcluster = %s, initial_local_pref = %d, new_local_pref = %d' %
            (sub_cluster, initial_local_pref, new_local_pref))
        if new_local_pref != initial_local_pref:
            assert False, "Error: Routing-Policy is applied for intra subcluster  secondary routes"
        self.logger.info(
            "PASS: routing-policy is not applied for intra subcluster secondary routes")

    @skip_because(remote_compute_setup=False)
    @preposttest_wrapper
    def test_rp_subcluster_reject_route(self):
        '''
        1. Create a routing policy with bgp match to reject the route.
        2. Launch VMs in all nodes.
        3. Validate that the policy get applied to the secondary routes coming from subcluster pop1 to
           main controller and the route should get rejected.
        '''
        ret_dict = self.create_vm_in_all_nodes()
        control_nodes = self.get_control_nodes()
        compute_nodes = self.get_compute_nodes()

        # Get secondary route coming from subcluster pop1 in main control-node.
        cn_entries = self.cn_inspect[control_nodes['main'][0]].get_cn_route_table_entry(
            prefix=ret_dict['test_vm_pop1'].vm_ip + "/32", table="inet.0",
            ri_name=ret_dict['vn_main_fixture'].ri_name)
        if cn_entries is None:
            assert False, "Route  %s is not present" % (
                ret_dict['test_vm_pop1'].vm_ip)
        sub_cluster = self.get_sub_cluster(cn_entries, is_replicated='true')
        if sub_cluster == '':
            assert False, "subcluster not present in route %s" % (
                ret_dict['test_vm_pop1'].vm_ip)

        # Apply routing-policy to change local-pref for secondary route(bgp)
        # if subcluster associated with the route is diffrent.
        config_dicts = {'vn_fixture': ret_dict['vn_main_fixture'],
                        'from_term': 'protocol', 'sub_from': 'bgp',
                        'from_term_community': 'ext_community_list',
                        'sub_from_community': [sub_cluster],
                        'action': 'reject', 'to_term': None}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        assert self.verify_policy_in_control(ret_dict['vn_main_fixture'], ret_dict['test_vm_main'],
                    search_ip=ret_dict['test_vm_pop1'].vm_ip, search_value='RoutingPolicyReject'),\
                    'Search term not found in introspect'

    def get_sub_cluster(self, cn_entries, is_replicated):
        for entry in cn_entries:
            if entry['replicated'] == is_replicated:
                for comm in entry['communities']:
                    if 'subcluster' in comm:
                        return comm
        return ''

    def get_local_pref(self, cn_entries, is_replicated):
        for entry in cn_entries:
            if entry['replicated'] == is_replicated:
                return int(entry['local_preference'])
        return -1
