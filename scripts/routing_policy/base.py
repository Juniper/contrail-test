from builtins import str
import test_v1
import os
import re
from tcutils.util import get_random_name, retry
from vnc_api.vnc_api import *
from fabric.api import run, hide, settings
from time import sleep
from tcutils.util import get_random_cidr
from random import randint

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

    def config_basic(self):
        vn_name = get_random_name('bgpaas_vn')
        vn2_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn2_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        rt_value = randint(50000, 60000)
        vn_fixture.add_route_target(vn_fixture.ri_name, self.inputs.router_asn, rt_value)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn2_fixture.add_route_target(vn2_fixture.ri_name, self.inputs.router_asn, rt_value)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros')
        test2_vm = self.create_vm(vn2_fixture, 'test2_vm', image_name='cirros')
        assert test_vm.wait_till_vm_is_up()
        assert test2_vm.wait_till_vm_is_up()

        ret_dict = {
                'vn_fixture' : vn_fixture,
                'test_vm' : test_vm,
                'test2_vm' : test2_vm,
                }
        return ret_dict

    def configure_term_routing_policy(self, config_dicts):
        obj_1 = PolicyStatementType()
        obj_2 = PolicyTermType()
        obj_3 = TermMatchConditionType()
        obj_4 = PrefixMatchType()
        if config_dicts['from_term'] == 'protocol':
            obj_3.set_protocol([config_dicts['sub_from']])
        if config_dicts.get('from_term_community') and config_dicts['from_term_community'] == 'ext_community_list':
            obj_3.set_extcommunity_list(config_dicts['sub_from_community'])
            if config_dicts.get('match_all'):
                obj_3.set_extcommunity_match_all(config_dicts['match_all'])
        obj_2.set_term_match_condition(obj_3)
        obj_6 = TermActionListType()
        obj_7 = ActionUpdateType()
        obj_8 = ActionCommunityType()
        obj_9 = CommunityListType()
        if config_dicts['to_term'] == 'community':
            obj_9.add_community(config_dicts['sub_to'])
            obj_8.set_add(obj_9)
            obj_7.set_community(obj_8)
        if config_dicts['to_term'] == 'set_communinty':
            obj_9.set_community(config_dicts['sub_to'])
            obj_8.set_set(obj_9)
            obj_7.set_community(obj_8)
        if config_dicts['to_term'] == 'add_ext_community':
            obj_9.add_community(config_dicts['sub_to'])
            obj_8.set_add(obj_9)
            obj_7.set_extcommunity(obj_8)
        if config_dicts['to_term'] == 'set_ext_community':
            obj_9.set_community([config_dicts['sub_to']])
            obj_8.set_set(obj_9)
            obj_7.set_extcommunity(obj_8)
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
        if config_dicts.get('action'):
            obj_6.set_action(config_dicts['action'])
        else:
            obj_6.set_update(obj_7)
        obj_2.set_term_action_list(obj_6)
        obj_1.add_term(obj_2)
        rp = RoutingPolicy(get_random_name('RP'), config_dicts['vn_fixture'].project_obj)
        rp.set_routing_policy_entries(obj_1)
        if config_dicts['sub_from'] == 'service-chain':
            obj_11 = RoutingPolicyServiceInstanceType()
            if config_dicts.get('si_rp_interface_type') :
               if 'left_vn' in config_dicts['si_rp_interface_type']:
                  obj_11.set_left_sequence('1')
               if 'right_vn' in config_dicts['si_rp_interface_type']:
                  obj_11.set_right_sequence('1')
            else:
               obj_11.set_left_sequence('1')
            rp.add_service_instance(config_dicts['si_fixture'].si_obj, obj_11)

        self.vnc_lib.routing_policy_create(rp)
        self.addCleanup(self.vnc_lib.routing_policy_delete, id=rp.uuid)
        if not config_dicts['sub_from'] == 'service-chain':
            fix_vn = self.vnc_lib.virtual_network_read(id = config_dicts['vn_fixture'].uuid)
            fix_vn.set_routing_policy(rp)
            self.vnc_lib.virtual_network_update(fix_vn)
            self.addCleanup(self.delete_rp_refs_from_vn, rp, fix_vn)
        return rp

    #Routine to see if the Routing policy options are being correctly set.
    #This involves using only get_control_nodes to see if cn_introspect has the values
    @retry(delay=1, tries=10)
    def verify_policy_in_control(self, vn_fixture, vm_fixture, search_ip = '', search_value = ''):
        if not search_ip:
            search_in_cn = vm_fixture.vm_ip
        else:
            search_in_cn = search_ip
        found_value = True
        for cn in vm_fixture.get_control_nodes():
            found_value = found_value and re.findall(search_value, str(
                self.cn_inspect[cn
                ].get_cn_route_table_entry(search_in_cn,
                vn_fixture.vn_fq_name+":"+vn_fixture.vn_name)[0]))
        return True if found_value else False

    def delete_rp_refs_from_vn(self, rp_obj, vn_obj):
        vn_obj.del_routing_policy(rp_obj)
        self.vnc_lib.virtual_network_update(vn_obj)

    def remove_routing_policy(self, rp, vn_fixture, regular_vn):
        if regular_vn:
            fix_vn = self.vnc_lib.virtual_network_read(id = vn_fixture.uuid)
            fix_vn.del_routing_policy(rp)
            self.vnc_lib.virtual_network_update(fix_vn)
            self.vnc_lib.routing_policy_delete(id = rp.uuid)
        else:
            rp.del_service_instance(vn_fixture.si_obj)
            self.vnc_lib.routing_policy_delete(id = rp.uuid)

    def create_vm_in_all_nodes(self):
        vn_pop1_name = get_random_name('pop1_vn')
        vn_pop2_name = get_random_name('pop2_vn')
        vn_main_name = get_random_name('main_vn')

        vn_pop1_subnet = [get_random_cidr()]
        vn_pop2_subnet = [get_random_cidr()]
        vn_main_subnet = [get_random_cidr()]

        rt_value = randint(50000, 60000)

        vn_pop1_fixture = self.create_vn(vn_pop1_name, vn_pop1_subnet)
        vn_pop1_fixture.add_route_target(vn_pop1_fixture.ri_name,
                self.inputs.router_asn, rt_value)

        vn_pop2_fixture = self.create_vn(vn_pop2_name, vn_pop2_subnet)
        vn_pop2_fixture.add_route_target(vn_pop2_fixture.ri_name,
                self.inputs.router_asn, rt_value)

        vn_main_fixture = self.create_vn(vn_main_name, vn_main_subnet)
        vn_main_fixture.add_route_target(vn_main_fixture.ri_name,
                self.inputs.router_asn, rt_value)

        compute_nodes = self.get_compute_nodes()
        test_vm_pop1 = self.create_vm(vn_pop1_fixture, 'test_vm_pop1', image_name='cirros',
                node_name=compute_nodes['pop1'][0])
        test_vm_pop2 = self.create_vm(vn_pop2_fixture, 'test_vm_pop2', image_name='cirros',
                node_name=compute_nodes['pop2'][0])
        test_vm_main = self.create_vm(vn_main_fixture, 'test_vm_main', image_name='cirros',
                node_name=compute_nodes['main'][0])

        assert test_vm_pop1.wait_till_vm_is_up()
        assert test_vm_pop2.wait_till_vm_is_up()
        assert test_vm_main.wait_till_vm_is_up()

        ret_dict = {
                'vn_pop1_fixture' : vn_pop1_fixture,
                'vn_pop2_fixture' : vn_pop2_fixture,
                'vn_main_fixture' : vn_main_fixture,
                'test_vm_pop1' : test_vm_pop1,
                'test_vm_pop2' : test_vm_pop2,
                'test_vm_main' : test_vm_main,
                }
        return ret_dict

    def get_control_nodes(self):
        # Get control nodes of subcluster pop1, pop2 and main controller.
        control_nodes = {'pop1':[], 'pop2':[], 'main':[]}
        for host in self.inputs.bgp_control_ips:
            if self.inputs.host_data[host]['roles'].get('control'):
                if self.inputs.host_data[host]['roles'].get('control').get('location') == 'pop1':
                    control_nodes['pop1'].append(self.inputs.host_data[host]['host_ip'])
                if self.inputs.host_data[host]['roles'].get('control').get('location') == 'pop2':
                    control_nodes['pop2'].append(self.inputs.host_data[host]['host_ip'])
            else:
                control_nodes['main'].append(self.inputs.host_data[host]['host_ip'])
        return control_nodes

    def get_compute_nodes(self):
        # Get compute nodes of subcluster pop1, pop2 and main compute.
        compute_nodes = {'pop1':[], 'pop2':[], 'main':[]}
        for host in self.inputs.compute_ips:
            if self.inputs.host_data[host]['roles'].get('vrouter'):
                if self.inputs.host_data[host]['roles'].get('vrouter').get('location') == 'pop1':
                    compute_nodes['pop1'].append(self.inputs.host_data[host]['name'])
                elif self.inputs.host_data[host]['roles'].get('vrouter').get('location') == 'pop2':
                    compute_nodes['pop2'].append(self.inputs.host_data[host]['name'])
                else:
                    compute_nodes['main'].append(self.inputs.host_data[host]['name'])
        return compute_nodes
