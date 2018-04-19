import test_v1
import os
import re
from tcutils.util import get_random_name, retry
from vnc_api.vnc_api import *
from fabric.api import run, hide, settings
from time import sleep


class RPBase(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(RPBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(RPBase, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(RPBase, self).setUp()

    def tearDown(self):
        super(RPBase, self).tearDown()

    def configure_term_routing_policy(self, config_dicts):


        obj_1 = PolicyStatementType()
        obj_2 = PolicyTermType()
        obj_3 = TermMatchConditionType()
        obj_4 = PrefixMatchType()
        if config_dicts['from_term'] == 'protocol':
            obj_3.set_protocol([config_dicts['sub_from']])
        obj_2.set_term_match_condition(obj_3)
        obj_6 = TermActionListType()
        obj_7 = ActionUpdateType()
        obj_8 = ActionCommunityType()
        obj_9 = CommunityListType()
        if config_dicts['to_term'] == 'community':
            obj_9.add_community(config_dicts['sub_to'])
            obj_8.set_add(obj_9)
            obj_7.set_community(obj_8)
        if config_dicts['to_term'] == 'med':
            obj_7.set_med(config_dicts['sub_to'])
        if config_dicts['to_term'] == 'local-preference':
            obj_7.set_local_pref(config_dicts['sub_to'])
        if config_dicts['to_term'] == 'as-path':
            obj_15 = ActionAsPathType()
            obj_16 = AsListType()
            obj_16.asn_list = [config_dicts['sub_to']]
            obj_15.set_expand(obj_16)
            obj_7.set_as_path(obj_15)

        obj_6.set_update(obj_7)
        obj_2.set_term_action_list(obj_6)
        obj_1.add_term(obj_2)
        rp = RoutingPolicy(get_random_name('RP'), config_dicts['vn_fixture'].project_obj)
        rp.set_routing_policy_entries(obj_1)
        if config_dicts['sub_from'] == 'service-chain':
            obj_11 = RoutingPolicyServiceInstanceType()
            obj_11.set_left_sequence('1') 
            rp.add_service_instance(config_dicts['si_fixture'].si_obj, obj_11)

        self.vnc_lib.routing_policy_create(rp)
        if not config_dicts['sub_from'] == 'service-chain':
            fix_vn = self.vnc_lib.virtual_network_read(id = config_dicts['vn_fixture'].uuid)
            fix_vn.set_routing_policy(rp)
            self.vnc_lib.virtual_network_update(fix_vn)
        return rp

    def verify_policy_in_control(self, vn_fixture, test_vm_ip, search_value = ''):

        found_value = re.findall(search_value, str(self.cn_inspect[self.inputs.inputs.bgp_control_ips[0]].get_cn_route_table_entry(test_vm_ip, vn_fixture.vn_fq_name+":"+vn_fixture.vn_name)[0]))
        assert found_value, 'Search term not found in introspect'

    def remove_routing_policy(self, rp, vn_fixture, regular_vn):
        if regular_vn:
            fix_vn = self.vnc_lib.virtual_network_read(id = vn_fixture.uuid)
            fix_vn.del_routing_policy(rp)
            self.vnc_lib.virtual_network_update(fix_vn)
            self.vnc_lib.routing_policy_delete(id = rp.uuid)
        else:
            rp.del_service_instance(vn_fixture.si_obj)
            self.vnc_lib.routing_policy_delete(id = rp.uuid)
