"""Service chain firewall regression suite."""
from common.svc_firewall.base import BaseSvc_FwTest
from builtins import str
import os
import unittest
import fixtures
import testtools
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_name
from common.ecmp.ecmp_verify import ECMPVerify
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.servicechain.mirror.verify import VerifySvcMirror
from netaddr import IPNetwork
import test
from common import isolated_creds
import inspect


class TestSvcRegr(BaseSvc_FwTest, VerifySvcFirewall, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegr, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
        return self.verify_svc_chain(svc_img_name='cirros_in_net', service_mode='in-network',
                                     create_svms=True)


    @test.attr(type=['sanity'])
    @preposttest_wrapper
    @skip_because(feature='trans_svc')
    def test_svc_v2_transparent_datapath(self):
        return self.verify_svc_chain(service_mode='transparent',
                                                    create_svms=True)

    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    def test_svc_in_net_nat_with_static_routes(self):
        third_vn = self.create_vn(vn_name=get_random_name('third-vn'))
        third_vm = self.create_vm(vn_fixture=third_vn,
                                  vm_name=get_random_name('vm-in-third-vn'))
        assert third_vm.wait_till_vm_is_active()
        routes = list()
        vm_ips = third_vm.get_vm_ips()
        for vm_ip in vm_ips:
            routes.append(str(IPNetwork(vm_ip)))
        sc_info = self.verify_svc_chain(service_mode='in-network-nat',
                                        create_svms=True,
                                        static_route={'left': routes})
        si_fixture = sc_info['si_fixture']
        right_vn_fixture = sc_info['right_vn_fixture']
        left_vm_fixture = sc_info['left_vm_fixture']
        self.add_static_route_in_svm(si_fixture, third_vn, 'eth2')
        self.setup_policy_between_vns(right_vn_fixture, third_vn)
        for vm_ip in vm_ips:
            errmsg = "Ping to third VM %s from Left VM failed" % vm_ip
            assert left_vm_fixture.ping_with_certainty(vm_ip, count='3'), errmsg

    @preposttest_wrapper
    @skip_because(address_family='v6')
    def test_svc_in_network_nat_private_to_public(self):
        if  os.environ.get('MX_GW_TEST', 0) != '1':
            self.logger.info(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")

        public_vn_fixture = self.public_vn_obj.public_vn_fixture
        public_vn_subnet = self.public_vn_obj.public_vn_fixture.vn_subnets[
            0]['cidr']
        # Since the ping is across projects, enabling allow_all in the SG
        self.project.set_sec_group_for_allow_all(
            self.inputs.project_name, 'default')
        ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
                                         right_vn_fixture=public_vn_fixture,
                                         right_vn_subnets=[public_vn_subnet],
                                         create_svms=True)
        self.logger.info('Ping to outside world from left VM')
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        assert left_vm_fixture.ping_with_certainty('8.8.8.8', count='10')
        return True


class TestSvcRegrFeature(BaseSvc_FwTest, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegrFeature, cls).setUpClass()

    @preposttest_wrapper
    def test_policy_delete_add_transparent_mode(self):
        """Test policy update in transparent mode service chaining."""
        ret_dict = self.verify_svc_chain(svc_img_name='tiny_trans_fw',
                                         create_svms=True)
        self.verify_policy_delete_add(ret_dict)

    @preposttest_wrapper
    def test_policy_delete_add_in_network_mode(self):
        """Test policy update in in network mode service chaining."""
        ret_dict = self.verify_svc_chain(service_mode='in-network', create_svms=True)
        return self.verify_policy_delete_add(ret_dict)

    @preposttest_wrapper
    def test_policy_to_more_vns_transparent_mode(self):
        """Attach the same policy to  one more left and right VN's transparent mode service chaining."""
        ret_dict = self.verify_svc_chain(svc_img_name='tiny_trans_fw',
                                         create_svms=True)
        return self.verify_add_new_vns(ret_dict)

    @preposttest_wrapper
    def test_policy_to_more_vns_in_network_mode(self):
        """Add more VM's to VN's of in network mode service chaining."""
        mode = 'in-network'
        ret_dict = self.verify_svc_chain(service_mode=mode, create_svms=True)
        return self.verify_add_new_vms(ret_dict)

    @preposttest_wrapper
    def test_policy_port_protocol_change_transparent_mode(self):
        """Change the port and protocol of policy transparent mode service chaining."""
        ret_dict = self.verify_svc_chain(svc_img_name='tiny_trans_fw',
                                         create_svms=True)
        return self.verify_protocol_port_change(ret_dict)

    @preposttest_wrapper
    def test_policy_port_protocol_change_in_network_mode(self):
        """Change the port and protocol of policy in network mode service chaining."""
        mode = 'in-network'
        ret_dict = self.verify_svc_chain(service_mode=mode, create_svms=True)
        return self.verify_protocol_port_change(ret_dict, mode='in-network')

class TestSvcRegrIPv6(TestSvcRegr):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegrIPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
        return self.verify_svc_chain(svc_img_name='tiny_in_net', service_mode='in-network',
                                     create_svms=True)

    @preposttest_wrapper
    @skip_because(feature='trans_svc')
    def test_svc_v2_transparent_datapath(self):
        super(TestSvcRegrIPv6,self).test_svc_v2_transparent_datapath()

    @preposttest_wrapper
    def test_svc_in_net_nat_with_static_routes(self):
        super(TestSvcRegrIPv6,self).test_svc_in_net_nat_with_static_routes()

    @preposttest_wrapper
    @skip_because(address_family='v6')
    def test_svc_in_network_nat_private_to_public(self):
        super(TestSvcRegrIPv6,self).test_svc_in_network_nat_private_to_public()

class TestSvcRegrFeatureIPv6(TestSvcRegrFeature):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegrFeatureIPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

# Mirror tests are disabled since
# 1) feature not used in real-world
# 2) logic for number of mirror'd pkt is not solid
# class TestSvcRegrwithMirror(BaseSvc_FwTest, VerifySvcFirewall, VerifySvcMirror):
#
#     @classmethod
#     def setUpClass(cls):
#         super(TestSvcRegrwithMirror, cls).setUpClass()
#
#     def runTest(self):
#         pass
#     # end runTest
#
#     @preposttest_wrapper
#     def test_firewall_in_network_with_mirroring_transparent_mode(self):
#         """test firewall in in_network with mirroring in transparent mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='in-network-nat', mirror_svc_mode='transparent')
#
#     @preposttest_wrapper
#     def test_firewall_transparent_with_mirroring_in_network_mode(self):
#         """test firewall in transparent with mirroring in in_network mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='transparent', mirror_svc_mode='in-network')
#
#     @preposttest_wrapper
#     def test_firewall_transparent_with_mirroring_in_transparent(self):
#         """test firewall in transparent with mirroring in in_network mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='transparent', mirror_svc_mode='transparent')
#
#     @preposttest_wrapper
#     def test_firewall_in_network_with_mirroring_in_network(self):
#         """test firewall in in-network with mirroring in in_network mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='in-network-nat', mirror_svc_mode='in-network')
#
# TODO: Following tests will be valid after the bug#1130 fix
#      http://10.84.5.133/bugs/show_bug.cgi?id=1130
#    @preposttest_wrapper
#    def test_svc_span_transparent_mode(self):
#        """Verify svc span in transparent mode."""
#        return self.verify_svc_span()
#
#    @preposttest_wrapper
#    def test_svc_span_in_network_mode(self):
#        """Verify svc span in in-network mode."""
#        return self.verify_svc_span(in_net=True)

# class TestSvcRegrwithMirrorIPv6(TestSvcRegrwithMirror):
#
#     @classmethod
#     def setUpClass(cls):
#         super(TestSvcRegrwithMirrorIPv6, cls).setUpClass()
#         cls.inputs.set_af('v6')
#
#     def is_test_applicable(self):
#         if not self.connections.orch.is_feature_supported('ipv6'):
#             return(False, 'IPv6 tests not supported in this environment ')
#         return (True, None)
#
#     @preposttest_wrapper
#     def test_firewall_in_network_with_mirroring_transparent_mode(self):
#         """test firewall in in_network with mirroring in transparent mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='in-network',
#             mirror_svc_mode='transparent')
#
#     @preposttest_wrapper
#     def test_firewall_in_network_with_mirroring_in_network(self):
#         """test firewall in in-network with mirroring in in_network mode"""
#         return self.verify_firewall_with_mirroring(
#             firewall_svc_mode='in-network',
#             mirror_svc_mode='in-network')
