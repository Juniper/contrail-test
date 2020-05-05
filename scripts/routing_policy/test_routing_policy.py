from __future__ import absolute_import
from .base import RPBase
from builtins import str
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.svc_health_check.base import BaseHC
import test
import time
from common import isolated_creds
from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
from tcutils.util import *
from tcutils.tcpdump_utils import *
from contrailapi import ContrailVncApi
from tcutils.util import get_random_cidr
from random import randint

class TestRP(RPBase, BaseBGPaaS, BaseHC, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestRP, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRP, cls).tearDownClass()

    def is_test_applicable(self):
        return (True, None)

    def setUp(self):
        super(TestRP, self).setUp()
        result = self.is_test_applicable()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_interface(self):
        '''
        1. Create a routing policy with interface match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'community', 'sub_to':'64512:55555'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '55555'), 'Search term not found in introspect'
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)
         
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_interface_static(self):
        '''
        1. Create a routing policy with interface-static match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict,random_cidr = self.create_interface_static_routes()
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_value = '55555', search_ip = random_cidr), 'Search term not found in introspect'
        assert ret_dict['test_vm'].ping_with_certainty(ret_dict['test2_vm'].vm_ip) 

    @preposttest_wrapper
    def test_rp_service_interface(self):
        '''
        1. Create a routing policy with service-interface match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        
        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = '55555')
        assert left_vm_fixture.ping_with_certainty(right_vm_fixture.vm_ip)

    @preposttest_wrapper
    def test_rp_service_chain(self):
        '''
        1. Create a routing policy with service-chain match.
        2. Launch VMs.
        3. Attach policy to VN and confirm if policy takes hold.
        '''

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = '55555')
        assert left_vm_fixture.ping_with_certainty(right_vm_fixture.vm_ip)

    @test.attr(type=['sanity'])
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_rp_secondary_routes(self):
        '''
        Maintainer: vageesant@juniper.net
        Description: CEM-6735 - Enhanced import policy extended to MP-BGP route type
        To verify: routing-policy to change routing-parameters for secondary routes ( routes from External Devices )
        1. Create VN and add MXs route-target to VN , to import route from MX into VN.
        2. Retrieve the local-preference advertised by MX.
        3. Create routing-policy to change local-preference and attach to VN
        4. Verify updated routing-policy is applied to secondary routes from MX and local-preference value is set to new value mentioned through routing-policy.
        '''

        vm1_name = get_random_name('vm_private')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        mx_rt = self.inputs.mx_rt
        
        if self.inputs.config['test_configuration'].get('router_asn',False):
           router_asn = self.inputs.config['test_configuration'].get('router_asn')
        else:
           router_asn = self.inputs.bgp_asn

        vn1_fixture.add_route_target(routing_instance_name=vn1_fixture.ri_name,
                                    router_asn=router_asn, route_target_number=mx_rt)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        initial_local_pref = -1
        new_local_pref     = -1
        for cn in self.inputs.bgp_control_ips:
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn1_fixture.ri_name)
            if cn_entries:
               initial_local_pref = int(cn_entries[0]['local_preference'])
        if initial_local_pref == -1:
           assert False,"Default route 0.0.0.0/0 is not advertised by MX.Check the MX routing-instance configurations."
        config_dicts = {'vn_fixture':vn1_fixture, 'from_term':'protocol','sub_from':'bgp','to_term':'local-preference','sub_to':initial_local_pref + 10}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        for cn in self.inputs.bgp_control_ips:
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn1_fixture.ri_name)
            if cn_entries:
               new_local_pref = int(cn_entries[0]['local_preference'])
        self.logger.info("Old local-preference: %d , New local-preference: %d"%(initial_local_pref,new_local_pref))
        if new_local_pref != initial_local_pref + 10:
           assert False,"Error: Routing-Policy not applied on Secondary routes from MX and Local Preference is not updated"
        self.logger.info("PASS: routing-policy is applied correctly for secondary-routes from MX")

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_rp_secondary_routes_si(self):
        '''
        Maintainer: vageesant@juniper.net
        Description: CEM-6735 - Enhanced import policy extended to MP-BGP route type. Policy should not be applied on MP-BGP external routes in SC scenario.
        To verify:
            Apply rp to update local_preference and attach to SI.Verify only primary routes are updated with local_preference value in RP and secondary SC routes
            are not affected.
        1. Create in-network SC and attach MX's RT to left-vn , to import route from MX to VN.
        2. Create Routing Policy to modify local_preference and attach to SI.
        3. Verify SC secondary routes ( routes from MX ) are not updated with local_preference from RP.
        4. Verify SC Primary routes ( right-vm route on left-service instance vrf ) is updated with local_preference from RP.
        '''

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        mx_rt = self.inputs.mx_rt
        
        if self.inputs.config['test_configuration'].get('router_asn',False):
           router_asn = self.inputs.config['test_configuration'].get('router_asn')
        else:
           router_asn = self.inputs.bgp_asn

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        left_svn_fixture = ret_dict['si_left_vn_fixture']
        left_vn_fixture.add_route_target(routing_instance_name=left_vn_fixture.ri_name,
                                    router_asn=router_asn, route_target_number=mx_rt)
        right_vm_ip = ret_dict['right_vm_fixture'].vm_ip
        left_vm_fixture.ping_with_certainty(
                right_vm_fixture.vm_ip, count='3')

        initial_local_pref_bgp_route = -1
        new_local_pref_bgp_route     = -1
        initial_local_pref_sc_route  = -1
        new_local_pref_sc_route      = -1
        for cn in self.inputs.bgp_control_ips:
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=left_svn_fixture.ri_name)
            if cn_entries:
               initial_local_pref_bgp_route = int(cn_entries[0]['local_preference'])
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix=right_vm_ip+"/32",table="inet.0",ri_name=left_svn_fixture.ri_name)
            if cn_entries:
               initial_local_pref_sc_route = int(cn_entries[0]['local_preference'])
        if initial_local_pref_bgp_route == -1:
           assert False,"Default route 0.0.0.0/0 is not advertised by MX.Check the MX routing-instance configurations."

        local_pref_config     = initial_local_pref_bgp_route + 10
        config_dicts = {'vn_fixture':left_vn_fixture,'si_rp_interface_type': ['left_vn','right_vn'],'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'local-preference','sub_to': local_pref_config}
        rp = self.configure_term_routing_policy(config_dicts)
        time.sleep(10)
        for cn in self.inputs.bgp_control_ips:
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=left_svn_fixture.ri_name)
            if cn_entries:
               new_local_pref_bgp_route = int(cn_entries[0]['local_preference'])
            cn_entries = self.cn_inspect[cn].get_cn_route_table_entry(prefix=right_vm_ip+"/32",table="inet.0",ri_name=left_svn_fixture.ri_name)
            if cn_entries:
               new_local_pref_sc_route = int(cn_entries[0]['local_preference'])

        self.logger.info("BGP Route: Old local-preference: %d , New local-preference: %d"%(initial_local_pref_bgp_route,new_local_pref_bgp_route))
        self.logger.info("Primary Route: Old local-preference: %d , New local-preference: %d"%(initial_local_pref_sc_route,new_local_pref_sc_route))
        if new_local_pref_bgp_route != initial_local_pref_bgp_route :
           assert False,"Error: Routing-Policy applied on SI-Secondary routes from MX and Local Preference is updated.Expected not to apply rp on Secondary routes in SC."

        if new_local_pref_sc_route != local_pref_config:
           assert False,"Error: Routing-Policy NOT applied on SC-Primary routes."

        self.logger.info("PASS: routing-policy is NOT applied ,as expected , for SC secondary-routes from MX.")
        self.logger.info("PASS: routing-policy is applied ,as expected , for SC Primary-routes.")


    @preposttest_wrapper
    def test_rp_bgpaas(self):
        '''
        1. Create a routing policy with bgpaas match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        
        ret_dict = self.create_bgpaas_routes()
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        #will have to wait for bgp hold timer
        sleep(90)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_ip = str(ret_dict['vn_fixture'].get_subnets()[0]['cidr']), search_value = '55555')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_interface_ext_community(self):
        '''
        1. Create a routing policy with interface match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'target:64512:44444'), 'Search term not found in introspect'
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'set_ext_community', 'sub_to':'target:64512:33333'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'target:64512:33333'), 'Search term not found in introspect'

    @preposttest_wrapper
    def test_rp_interface_static_ext_community(self):
        '''
        1. Create a routing policy with interface-static match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict,random_cidr = self.create_interface_static_routes()
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_value = 'target:64512:44444',search_ip = random_cidr), 'Search term not found in introspect'
        assert ret_dict['test_vm'].ping_with_certainty(ret_dict['test2_vm'].vm_ip) 
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'set_ext_community', 'sub_to':'target:64512:33333'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_value = 'target:64512:33333',search_ip = random_cidr), 'Search term not found in introspect'
    
    @preposttest_wrapper
    def test_rp_service_interface_ext_community(self):
        '''
        1. Create a routing policy with service-interface match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        
        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = 'target:64512:44444')
        assert left_vm_fixture.ping_with_certainty(right_vm_fixture.vm_ip)
        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'set_ext_community', 'sub_to':'target:64512:33333'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = 'target:64512:33333')
    
    @preposttest_wrapper
    def test_rp_service_chain_ext_community(self):
        '''
        1. Create a routing policy with service-chain match.
        2. Launch VMs.
        3. Attach policy to VN and confirm if policy takes hold.
        '''

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = 'target:64512:44444')
        assert left_vm_fixture.ping_with_certainty(right_vm_fixture.vm_ip)
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'set_ext_community', 'sub_to':'target:64512:33333'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = 'target:64512:33333'), 'Search term not found in introspect'

    @preposttest_wrapper
    def test_rp_bgpaas_ext_community(self):
        '''
        1. Create a routing policy with bgpaas match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        
        ret_dict = self.create_bgpaas_routes()
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'}
        rp = self.configure_term_routing_policy(config_dicts)
        sleep(90)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_ip = str(ret_dict['vn_fixture'].get_subnets()[0]['cidr']), search_value = 'target:64512:44444')
        config_dicts = {'vn_fixture':ret_dict['vn_fixture'], 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'set_ext_community', 'sub_to':'target:64512:44444'} 
        rp = self.configure_term_routing_policy(config_dicts)
        sleep(90)
        assert self.verify_policy_in_control(ret_dict['vn_fixture'], ret_dict['test_vm'], search_ip = str(ret_dict['vn_fixture'].get_subnets()[0]['cidr']), search_value = 'target:64512:44444'), 'Search term not found in introspect'

    @preposttest_wrapper
    def test_rp_interface_matrix(self):
        '''
        1. Create a routing policy with interface match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']

        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '666')
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)

    @preposttest_wrapper
    def test_rp_interface_static_matrix(self):
        '''
        1. Create a routing policy with interface-static match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']

        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)
        random_cidr = get_random_cidr()
        self.intf_table_to_right_obj = self.static_table_handle.create_route_table(
            prefixes=[random_cidr],
            name=get_random_name('int_table_right'),
            parent_obj=self.project.project_obj,
        )
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + vn_fixture.vn_name
        self.static_table_handle.bind_vmi_to_interface_route_table(
            str(test_vm.get_vmi_ids()[id_entry]),
            self.intf_table_to_right_obj)
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '666')
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)

    @preposttest_wrapper
    def test_rp_service_interface_matrix(self):
        '''
        1. Create a routing policy with service-interface match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']

        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = '444')
        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = '555')
        config_dicts = {'vn_fixture':left_vn_fixture, 'from_term':'protocol', 'sub_from':'service-interface', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(self.vnc_lib.routing_instance_read(id = str(self.vnc_lib.virtual_network_read(id = left_vn_fixture.uuid).get_routing_instances()[1]['uuid'])).get_service_chain_information().service_chain_address), search_value = '666')

    @preposttest_wrapper
    def test_rp_bgpaas_matrix(self):
        '''
        1. Create a routing policy with bgpaas match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict = self.create_bgpaas_routes()
        vn_fixture = ret_dict["vn_fixture"]
        test_vm    = ret_dict["test_vm"]
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        sleep(90)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = str(vn_fixture.get_subnets()[0]['cidr']), search_value = '444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        sleep(90)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = str(vn_fixture.get_subnets()[0]['cidr']), search_value = '555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        sleep(90)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = str(vn_fixture.get_subnets()[0]['cidr']), search_value = '666')

    @preposttest_wrapper
    def test_rp_service_chain_matrix(self):
        '''
        1. Create a routing policy with service-chain match.
        2. Launch VMs.
        3. Attach policy to VN and confirm if policy takes hold.
        '''

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = '444')
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = '555')
        config_dicts = {'vn_fixture':left_vn_fixture, 'si_fixture':si_fixture, 'si_fixture':si_fixture, 'from_term':'protocol', 'sub_from':'service-chain', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(left_vn_fixture, left_vm_fixture, search_ip = str(right_vm_fixture.vm_ip), search_value = '666')

    @preposttest_wrapper
    def test_rp_xmpp_matrix(self):
        '''
        1. Create a routing policy with interface match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']

        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '55555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'add_ext_community', 'sub_to':'target:64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'target:64512:55555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'set_ext_community', 'sub_to':'target:64512:44444'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'target:64512:44444'), 'Search term not found in introspect'
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'xmpp', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '666')
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)

    @preposttest_wrapper
    def test_rp_network_static_matrix(self):
        '''
        1. Create a routing policy with interface match and different "to" conditions:med, as-path, local-pref, community.
        2. Launch VMs.
        3. Attach policy to VN and confirm if policy takes hold.
        '''

        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']

        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)
        random_cidr = get_random_cidr()
        self.nw_handle_to_right = self.static_table_handle.create_route_table(
                prefixes=[random_cidr],
                name="network_table_left_to_right",
                next_hop=test_vm.vm_ip,
                parent_obj=self.project.project_obj,
                next_hop_type='ip-address',
                route_table_type='network',
            )
        self.static_table_handle.bind_network_route_table_to_vn(
                vn_uuid=vn_fixture.uuid,
                nw_route_table_obj=self.nw_handle_to_right)

        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '55555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'add_ext_community', 'sub_to':'target:64512:44444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = 'target:64512:44444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'set_ext_community', 'sub_to':'target:64512:33333'} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = 'target:64512:33333'), 'Search term not found in introspect'
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'med', 'sub_to':'444'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '444')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'local-preference', 'sub_to':'555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '555')
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'static', 'to_term':'as-path', 'sub_to':'666'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = random_cidr, search_value = '666')
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)

    @preposttest_wrapper
    def test_rp_ext_community_list_match_all_reject(self):
        '''
        1. Create a routing policy with ext_community_list ,interface match and then reject.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''
        ret_dict = self.config_basic()
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        test2_vm = ret_dict['test2_vm']
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'from_term_community':'ext_community_list', 'sub_from_community':['encapsulation:gre','encapsulation:udp'], 'action': 'reject', 'to_term': None} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'RoutingPolicyReject'), 'Search term not found in introspect'
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'from_term_community':'ext_community_list', 'sub_from_community':['encapsulation:gre','encapsulation:udp'], 'action': 'reject', 'to_term': None, 'match_all': True} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'RoutingPolicyReject'), 'Search term not found in introspect'
        #give wrong communinty value and check match_all
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface', 'from_term_community':'ext_community_list', 'sub_from_community':['encapsulation:gre','encapsulation:uuup'], 'action': 'reject', 'to_term': None, 'match_all': True} 
        rp = self.configure_term_routing_policy(config_dicts)
        assert not self.verify_policy_in_control(vn_fixture, test_vm, search_value = 'RoutingPolicyReject'), 'Search term found in introspect'

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
        bgpaas_vm1 = self.create_vm(ret_dict['vn_fixture'], 'bgpaas_vm1',image_name='ubuntu-bird')
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
        self.logger.info('Configuring BGP on the bird vm')
        static_routes = []
        static_routes.append({"network":ret_dict['vn_fixture'].get_subnets()[0]['cidr'],"nexthop":"blackhole"})
        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=self.inputs.bgp_asn,
            local_as=autonomous_system,static_routes=static_routes)
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        return ret_dict
 
