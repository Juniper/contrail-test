import test_v1
import os
import re
from tcutils.util import get_random_name, retry
from vnc_api.vnc_api import *
from fabric.api import run, hide, settings
from time import sleep
from tcutils.util import get_random_cidr
from random import randint
from common.bgpaas.base import BaseBGPaaS
from contrailapi import ContrailVncApi


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

    def create_interface_static_routes(self):
        ret_dict = self.config_basic()
        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)
        random_cidr = get_random_cidr()
        self.intf_table_to_right_obj = self.static_table_handle.create_route_table(
            prefixes=[random_cidr],
            name=get_random_name('int_table_right'),
            parent_obj=self.project.project_obj,
        )
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + ret_dict['vn_fixture'].vn_name
        self.static_table_handle.bind_vmi_to_interface_route_table(
            str(ret_dict['test_vm'].get_vmi_ids()[id_entry]),
            self.intf_table_to_right_obj)
        return ret_dict,random_cidr
    
    def create_bgpaas_routes(self):
        ret_dict = {}
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        ret_dict['vn_fixture'] = self.create_vn(vn_name, vn_subnets)
        ret_dict['test_vm'] = self.create_vm(ret_dict['vn_fixture'], 'test_vm',
                                 image_name='ubuntu-traffic')
        assert ret_dict['test_vm'].wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(ret_dict['vn_fixture'], 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip)
        bgpaas_vm1.wait_for_ssh_on_vm()
        port1 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw_ip = ret_dict['vn_fixture'].get_subnets()[0]['gateway_ip']
        dns_ip = ret_dict['vn_fixture'].get_subnets()[0]['dns_server_address']
        neighbors = []
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=ret_dict['test_vm'], dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        return ret_dict
        
