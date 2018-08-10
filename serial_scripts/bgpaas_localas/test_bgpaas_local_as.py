from tcutils.wrappers import preposttest_wrapper
import test
import time
from common import isolated_creds
from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from tcutils.util import *
from contrailapi import ContrailVncApi
from tcutils.util import get_random_cidr
from random import randint
from time import sleep

class TestBGPaaSlocalAS(BaseBGPaaS):

    @classmethod
    def setUpClass(cls):
        super(TestBGPaaSlocalAS, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBGPaaSlocalAS, cls).tearDownClass()

    def is_test_applicable(self):
        return (True, None)

    def setUp(self):
        super(TestBGPaaSlocalAS, self).setUp()
        result = self.is_test_applicable()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_basic_bgpaas_local_as(self):
        '''
        1. Create a bgpaas vm. Configure same local-as on vm and contrail side.
        2. Make sure BGP with vm comes up.
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip, local_autonomous_system=local_autonomous_system)
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
        self.logger.info('We will configure BGP on the vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False, local_autonomous_system=local_autonomous_system)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        agent = bgpaas_vm1.vm_node_ip
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_negative(self):
        '''
        1. Create a bgpaas vm. Configure different local-as on vm and contrail side.
        2. Make sure BGP with vm comes up.
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip, local_autonomous_system=local_autonomous_system+1)
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
        self.logger.info('We will configure BGP on the vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False, local_autonomous_system=local_autonomous_system)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        agent = bgpaas_vm1.vm_node_ip
        assert not bgpaas_fixture.verify_in_control_node(bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_bgp_router(self):
        '''
        1. Create a bgpaas vm. Configure local-as on vm and bgp router on contrail side.
        2. Make sure BGP with vm comes up.
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip, local_autonomous_system=local_autonomous_system)
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
        self.logger.info('We will configure BGP on the vSRX')
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        bgp_router_uuid = self.vnc_lib.bgp_as_a_service_read(id = bgpaas_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router = self.vnc_lib.bgp_router_read(id = bgp_router_uuid)
        rparam = bgp_router.bgp_router_parameters
        peer_local = random.randint(900, 1200)
        rparam.set_local_autonomous_system(peer_local)
        bgp_router.set_bgp_router_parameters(rparam)
        self.vnc_lib.bgp_router_update(bgp_router)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False, local_autonomous_system=local_autonomous_system, peer_local = peer_local)
        agent = bgpaas_vm1.vm_node_ip
        sleep(90)
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
    
    @preposttest_wrapper
    def test_basic_bgpaas_local_as_bgp_router_negative(self):
        '''
        1. Create a bgpaas vm. Configure different local-as on vm and contrail bgp router side.
        2. Make sure BGP with vm comes up.
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip, local_autonomous_system=local_autonomous_system)
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
        self.logger.info('We will configure BGP on the vSRX')
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        bgp_router_uuid = self.vnc_lib.bgp_as_a_service_read(id = bgpaas_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router = self.vnc_lib.bgp_router_read(id = bgp_router_uuid)
        rparam = bgp_router.bgp_router_parameters
        peer_local = random.randint(900, 1200)
        rparam.set_local_autonomous_system(peer_local+1)
        bgp_router.set_bgp_router_parameters(rparam)
        self.vnc_lib.bgp_router_update(bgp_router)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False, local_autonomous_system=local_autonomous_system, peer_local = peer_local)
        agent = bgpaas_vm1.vm_node_ip
        sleep(90)
        assert not bgpaas_fixture.verify_in_control_node(bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_precedence(self):
        '''
        1. Create a bgpaas vm. Configure same local-as on vm and contrail side.
        2. Make sure BGP with vm comes up. Check precedence of global AS and local-as
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert bgpaas_vm1.wait_till_vm_is_up()
        local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgpaas_vm1.vm_ip, local_autonomous_system=local_autonomous_system)
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
        self.logger.info('We will configure BGP on the vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=False, local_autonomous_system=local_autonomous_system)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,port1['id'], bgpaas_fixture)
        agent = bgpaas_vm1.vm_node_ip
        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(id=global_system_id)
        old_as = global_system_config.get_autonomous_system()
        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(id=global_system_id)
        global_system_config.set_autonomous_system(random.randint(1300, 1400))
        self.vnc_lib.global_system_config_update(global_system_config)
        sleep(90)
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(id=global_system_id)
        global_system_config.set_autonomous_system(old_as)
        self.vnc_lib.global_system_config_update(global_system_config)
