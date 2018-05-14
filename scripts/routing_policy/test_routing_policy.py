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
from base import RPBase
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
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'interface-static', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_value = '55555', search_ip = random_cidr), 'Search term not found in introspect'
        assert test_vm.ping_with_certainty(test2_vm.vm_ip)  

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

    @preposttest_wrapper
    def test_rp_bgpaas(self):
        '''
        1. Create a routing policy with bgpaas match.
        2. Launch VMs. 
        3. Attach policy to VN and confirm if policy takes hold. 
        '''

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip)
        bgpaas_vm1.wait_for_ssh_on_vm()
        port1 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        config_dicts = {'vn_fixture':vn_fixture, 'from_term':'protocol', 'sub_from':'bgpaas', 'to_term':'community', 'sub_to':'64512:55555'}
        rp = self.configure_term_routing_policy(config_dicts)
        #will have to wait for bgp hold timer
        sleep(90)
        assert self.verify_policy_in_control(vn_fixture, test_vm, search_ip = str(vn_fixture.get_subnets()[0]['cidr']), search_value = '55555')

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

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip)
        bgpaas_vm1.wait_for_ssh_on_vm()
        port1 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
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

