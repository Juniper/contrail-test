import test_v1
import os
import re
from tcutils.util import get_random_name, retry
import random
from vnc_api.vnc_api import *
from fabric.api import run, hide, settings
from time import sleep
from tcutils.util import get_random_cidr
from random import randint
from vm_test import VMFixture


class LocalASBase(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(LocalASBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(LocalASBase, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(LocalASBase, self).setUp()

    def tearDown(self):
        super(LocalASBase, self).tearDown()

    # create test vm and bgpaas vm.
    def config_basic(self,image_name='vsrx'):
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros-traffic')
        bgpaas_vm1 = self.create_vm(
            vn_fixture, 'bgpaas_vm1', image_name=image_name)
                
        assert test_vm.wait_till_vm_is_up()
        assert bgpaas_vm1.wait_till_vm_is_up()
        ret_dict = {
            'vn_fixture': vn_fixture,
            'test_vm': test_vm,
            'bgpaas_vm1': bgpaas_vm1,
        }
        return ret_dict

    # take the port object and attach to the bgpaas object
    def attach_port_to_bgpaas_obj(self, bgpaas_vm1, bgpaas_fixture):

        bgpaas_vm1.wait_for_ssh_on_vm()
        port1 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(
            self.detach_vmi_from_bgpaas,
            port1['id'],
            bgpaas_fixture)

    def configure_bgpaas_obj_and_bird(
            self,
            bgpaas_fixture,
            bgpaas_vm1,
            vn_fixture,
            src_vm,
            dst_vm,
            bgp_ip,
            lo_ip,
            cluster_local_autonomous_system,
            local_as=64500):

        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird')
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgp_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=local_as)

    # configure vsrx with correct families and local as/peer as if necessary
    def configure_bgpaas_obj_and_vsrx(
            self,
            bgpaas_fixture,
            bgpaas_vm1,
            vn_fixture,
            src_vm,
            dst_vm,
            bgp_ip,
            lo_ip,
            local_autonomous_system,
            peer_local=''):

        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the vSRX')
        self.config_bgp_on_vsrx(
            src_vm=src_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgp_ip,
            lo_ip=bgp_ip,
            address_families=address_families,
            autonomous_system=autonomous_system,
            neighbors=neighbors,
            bfd_enabled=False,
            local_autonomous_system=local_autonomous_system,
            peer_local=peer_local)
        bgpaas_vm1.wait_for_ssh_on_vm()

    # get current AS value in the system
    def get_present_as(self):

        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(
            id=global_system_id)
        self.present_as = global_system_config.get_autonomous_system()
        return self.present_as

    # change As value to value passed on
    def change_global_AS(self, value):

        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(
            id=global_system_id)
        global_system_config.set_autonomous_system(value)
        self.vnc_lib.global_system_config_update(global_system_config)

    # update the bgp router with local-as value passed on
    def update_bgp_router(self, bgpaas_vm1, bgpaas_fixture):
        #toDO skiranh: getting bgp router ref is taken a few extra seconds.
        #adding sleep temporarily
        sleep(10)
        bgp_router_uuid = self.vnc_lib.bgp_as_a_service_read(
            id=bgpaas_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router = self.vnc_lib.bgp_router_read(id=bgp_router_uuid)
        rparam = bgp_router.bgp_router_parameters
        peer_local = random.randint(900, 1200)
        rparam.set_local_autonomous_system(peer_local)
        bgp_router.set_bgp_router_parameters(rparam)
        self.vnc_lib.bgp_router_update(bgp_router)
        return peer_local

    # create bgpaas vm with 2 legs on 2 different VNs.
    def create_2_legs(self):

        vn1_name = get_random_name('bgpaas_vn')
        vn1_subnets = [get_random_cidr()]
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        test_vm = self.create_vm(vn1_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        assert test_vm.wait_till_vm_is_up()
        vn2_name = get_random_name('bgpaas_vn')
        vn2_subnets = [get_random_cidr()]
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        bgpaas_vm1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn1_fixture.obj,
                    vn2_fixture.obj],
                vm_name='bgpaas_vm1',
                node_name=None,
                image_name='vsrx'))

        bgpaas_vm1_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"
        ret_dict = {
            'vn1_fixture': vn1_fixture,
            'vn2_fixture': vn2_fixture,
            'test_vm': test_vm,
            'bgpaas_vm1': bgpaas_vm1,
        }
        return ret_dict

    # for bgpaas vm with 2 legs, configure 2 bgpaas objects.
    def config_2_ports(
            self,
            bgpaas_vm1,
            vn1_fixture,
            vn2_fixture,
            bgpaas1_fixture,
            bgpaas2_fixture,
            test_vm,
            left_local_autonomous_system,
            right_local_autonomous_system):

        bgpaas_vm1.wait_for_ssh_on_vm()
        port1 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_names[0]]
        port2 = {}
        port2['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_names[1]]
        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw1_ip = vn1_fixture.get_subnets()[0]['gateway_ip']
        dns1_ip = vn1_fixture.get_subnets()[0]['dns_server_address']
        left_neighbors = []
        left_neighbors = [gw1_ip, dns1_ip]
        gw2_ip = vn2_fixture.get_subnets()[0]['gateway_ip']
        dns2_ip = vn2_fixture.get_subnets()[0]['dns_server_address']
        right_neighbors = []
        right_neighbors = [gw2_ip, dns2_ip]
        self.logger.info('We will configure BGP on the vSRX')

        bgpaas_vm1.wait_for_ssh_on_vm()
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas1_fixture)
        self.attach_vmi_to_bgpaas(port2['id'], bgpaas2_fixture)
        self.addCleanup(
            self.detach_vmi_from_bgpaas,
            port1['id'],
            bgpaas1_fixture)
        self.addCleanup(
            self.detach_vmi_from_bgpaas,
            port2['id'],
            bgpaas2_fixture)
        #toDO skiranh: getting bgp router ref is taken a few extra seconds.
        #adding sleep temporarily
        sleep(10)
        bgp_router1_uuid = self.vnc_lib.bgp_as_a_service_read(
            id=bgpaas1_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router1 = self.vnc_lib.bgp_router_read(id=bgp_router1_uuid)
        rparam1 = bgp_router1.bgp_router_parameters
        peer_local1 = random.randint(900, 1200)
        rparam1.set_local_autonomous_system(peer_local1)
        bgp_router1.set_bgp_router_parameters(rparam1)
        self.vnc_lib.bgp_router_update(bgp_router1)

        #toDO skiranh: getting bgp router ref is taken a few extra seconds.
        #adding sleep temporarily
        sleep(10)
        bgp_router2_uuid = self.vnc_lib.bgp_as_a_service_read(
            id=bgpaas2_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router2 = self.vnc_lib.bgp_router_read(id=bgp_router2_uuid)
        rparam2 = bgp_router2.bgp_router_parameters
        peer_local2 = random.randint(900, 1200)
        rparam2.set_local_autonomous_system(peer_local2)
        bgp_router2.set_bgp_router_parameters(rparam2)
        self.vnc_lib.bgp_router_update(bgp_router2)

        self.config_2legs_on_vsrx(
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_left_ip=bgpaas_vm1.vm_ips[0],
            bgp_right_ip=bgpaas_vm1.vm_ips[1],
            address_families=address_families,
            autonomous_system=autonomous_system,
            left_neighbors=left_neighbors,
            right_neighbors=right_neighbors,
            left_local_autonomous_system=left_local_autonomous_system,
            right_local_autonomous_system=right_local_autonomous_system,
            peer_local_left=peer_local1,
            peer_local_right=peer_local2)

    # verify a particular route exists in agent
    def verify_in_agent(self, vn2_fixture, bgpaas_vm1, test_vm):

        (domain, project, vn) = vn2_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[bgpaas_vm1.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = bgpaas_vm1.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn2_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        cidr_prefix = test_vm.vm_ip
        next_hops = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id, ip=cidr_prefix, prefix='32')['path_list'][0]['nh']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent'
        else:
            self.logger.info('Route found in the Agent')
