from __future__ import absolute_import
from .base import LocalASBase
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
from vm_test import VMFixture
from time import sleep


class TestBGPaaSlocalAS(LocalASBase, BaseBGPaaS):

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
        ret_dict = self.config_basic(image_name='ubuntu-bird')
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ip,
            local_autonomous_system=cluster_local_autonomous_system)
        self.attach_port_to_bgpaas_obj(bgpaas_vm1, bgpaas_fixture)
        self.configure_bgpaas_obj_and_bird(
            bgpaas_fixture=bgpaas_fixture,
            bgpaas_vm1=bgpaas_vm1,
            vn_fixture=vn_fixture,
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgpaas_vm1.vm_ip,
            lo_ip=bgpaas_vm1.vm_ip,
            cluster_local_autonomous_system=cluster_local_autonomous_system)

        agent = bgpaas_vm1.vm_node_ip
        assert bgpaas_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_negative(self):
        '''
        1. Create a bgpaas vm. Configure different local-as on vm and contrail side.
        2. Make sure BGP with vm does not come up.
        '''
        ret_dict = self.config_basic(image_name="ubuntu-bird")
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ip,
            local_autonomous_system=cluster_local_autonomous_system + 1)
        self.attach_port_to_bgpaas_obj(bgpaas_vm1, bgpaas_fixture)

        self.configure_bgpaas_obj_and_bird(
            bgpaas_fixture=bgpaas_fixture,
            bgpaas_vm1=bgpaas_vm1,
            vn_fixture=vn_fixture,
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgpaas_vm1.vm_ip,
            lo_ip=bgpaas_vm1.vm_ip,
            cluster_local_autonomous_system=cluster_local_autonomous_system)

        agent = bgpaas_vm1.vm_node_ip
        assert not bgpaas_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_bgp_router(self):
        '''
        1. Create a bgpaas vm. Configure same bgp router local-as on vm and contrail side.
        2. Make sure BGP with vm comes up.
        '''
        ret_dict = self.config_basic(image_name="ubuntu-bird")
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ip,
            local_autonomous_system=cluster_local_autonomous_system)
        self.attach_port_to_bgpaas_obj(bgpaas_vm1, bgpaas_fixture)

        peer_local = self.update_bgp_router(bgpaas_vm1, bgpaas_fixture)
        self.configure_bgpaas_obj_and_bird(
            bgpaas_fixture=bgpaas_fixture,
            bgpaas_vm1=bgpaas_vm1,
            vn_fixture=vn_fixture,
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgpaas_vm1.vm_ip,
            lo_ip=bgpaas_vm1.vm_ip,
            cluster_local_autonomous_system=cluster_local_autonomous_system,
            local_as=peer_local)
        agent = bgpaas_vm1.vm_node_ip
        # ToDO skiranh: some setups take a lot of time for bgpaas connection to
        # be up, hence the sleep. Need to figure out if this is expected.
        #sleep(90)
        assert bgpaas_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_bgp_router_negative(self):
        '''
        1. Create a bgpaas vm. Configure different bgp router local-as on vm and contrail side.
        2. Make sure BGP with vm comes up.
        '''
        ret_dict = self.config_basic(image_name="ubuntu-bird")
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ip,
            local_autonomous_system=cluster_local_autonomous_system)
        self.attach_port_to_bgpaas_obj(bgpaas_vm1, bgpaas_fixture)

        peer_local = self.update_bgp_router(bgpaas_vm1, bgpaas_fixture)
        self.configure_bgpaas_obj_and_bird(
            bgpaas_fixture=bgpaas_fixture,
            bgpaas_vm1=bgpaas_vm1,
            vn_fixture=vn_fixture,
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgpaas_vm1.vm_ip,
            lo_ip=bgpaas_vm1.vm_ip,
            cluster_local_autonomous_system=cluster_local_autonomous_system,
            local_as=peer_local + 1)
        agent = bgpaas_vm1.vm_node_ip
        # ToDO skiranh: some setups take a lot of time for bgpaas connection to
        # be up, hence the sleep. Need to figure out if this is expected.
        #sleep(90)
        assert not bgpaas_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'

    @preposttest_wrapper
    def test_basic_bgpaas_local_as_precedence(self):
        '''
        1. Create a bgpaas vm. Configure local-as on bgpaas, bgp router and global AS on vm and contrail side.
        2. bgpaas > bgp router > global AS. COnfirm this precedence is correct.
        '''
        ret_dict = self.config_basic(image_name="ubuntu-bird")
        vn_fixture = ret_dict['vn_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ip,
            local_autonomous_system=cluster_local_autonomous_system)
        self.attach_port_to_bgpaas_obj(bgpaas_vm1, bgpaas_fixture)

        self.configure_bgpaas_obj_and_bird(
            bgpaas_fixture=bgpaas_fixture,
            bgpaas_vm1=bgpaas_vm1,
            vn_fixture=vn_fixture,
            src_vm=test_vm,
            dst_vm=bgpaas_vm1,
            bgp_ip=bgpaas_vm1.vm_ip,
            lo_ip=bgpaas_vm1.vm_ip,
            cluster_local_autonomous_system=cluster_local_autonomous_system)
        agent = bgpaas_vm1.vm_node_ip
        present_as = self.get_present_as()
        # There was a bug recently where having a few seconds before changing global AS caused a crash
        # adding a little sleep to cover this
        sleep(10)
        self.change_global_AS(random.randint(1300, 1400))
        # ToDO skiranh: some setups take a lot of time for bgpaas connection to
        # be up, hence the sleep. Need to figure out if this is expected.
        #sleep(90)
        assert bgpaas_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
        self.change_global_AS(present_as)

    @preposttest_wrapper
    def test_endtoend_bgpaas_local_as(self):
        '''
        1. Create a bgpaas vm. Configure bgpaas vm with 2 legs on 2 VNs.
        2. Confirm route from first VN go to bgpaas vm, and then is advertised back to contrail 2nd VN because local AS values are different.
        '''
        ret_dict = self.create_2_legs()
        vn1_fixture = ret_dict['vn1_fixture']
        vn2_fixture = ret_dict['vn2_fixture']
        test_vm = ret_dict['test_vm']
        bgpaas_vm1 = ret_dict['bgpaas_vm1']

        left_local_autonomous_system = random.randint(200, 800)
        right_local_autonomous_system = random.randint(900, 1300)
        bgpaas1_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ips[0],
            local_autonomous_system=left_local_autonomous_system)
        bgpaas2_fixture = self.create_bgpaas(
            bgpaas_shared=True,
            autonomous_system=64500,
            bgpaas_ip_address=bgpaas_vm1.vm_ips[1],
            local_autonomous_system=right_local_autonomous_system)
        bgpaas_vm1.wait_for_ssh_on_vm()
        self.config_2_ports(
            bgpaas_vm1,
            vn1_fixture,
            vn2_fixture,
            bgpaas1_fixture,
            bgpaas2_fixture,
            test_vm,
            left_local_autonomous_system,
            right_local_autonomous_system)

        agent = bgpaas_vm1.vm_node_ip
        # ToDO skiranh: some setups take a lot of time for bgpaas connection to
        # be up, hence the sleep. Need to figure out if this is expected.
        sleep(90)
        assert bgpaas1_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
        assert bgpaas2_fixture.verify_in_control_node(
            bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
        self.verify_in_agent(vn2_fixture, bgpaas_vm1, test_vm)
