"""Service chain firewall regression suite."""
import os
import unittest
import fixtures
import testtools
from tcutils.wrappers import preposttest_wrapper
from common.ecmp.ecmp_verify import ECMPVerify
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.servicechain.config import ConfigSvcChain
from base import BaseSvc_FwTest
import test
from common import isolated_creds
import inspect


class TestSvcRegr(BaseSvc_FwTest, VerifySvcFirewall, ConfigSvcChain, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegr, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
        return self.verify_svc_in_network_datapath(svc_img_name='tiny_nat_fw', ci=True)

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_svc_monitor_datapath(self):
        return self.verify_svc_transparent_datapath(svc_img_name='tiny_trans_fw', ci=True)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_transparent_with_3_instance(self):
        return self.verify_svc_transparent_datapath(si_count=3)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_in_network_nat_private_to_public(self):
        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):
            public_vn_fixture = self.public_vn_obj.public_vn_fixture
            public_vn_subnet = self.public_vn_obj.public_vn_fixture.vn_subnets[
                0]['cidr']
            # Since the ping is across projects, enabling allow_all in the SG
            self.project.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')
            self.verify_svc_in_network_datapath(
                svc_mode='in-network-nat', vn2_fixture=public_vn_fixture, vn2_subnets=[public_vn_subnet])
            self.logger.info('Ping to outside world from left VM')
            svms = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            svm_name = svms[0].name
            host = self.get_svm_compute(svm_name)
            tapintf = self.get_svm_tapintf_of_vn(svm_name, self.vn1_fixture)
            self.start_tcpdump_on_intf(host, tapintf)
            assert self.vm1_fixture.ping_with_certainty('8.8.8.8', count='10')
            out = self.stop_tcpdump_on_intf(host, tapintf)
            print out
            if '8.8.8.8' in out:
                self.logger.info(
                    'Ping to 8.8.8.8 is going thru %s ' % svm_name)
            else:
                result = False
                assert result, 'Ping to 8.8.8.8 not going thru the SI'
        else:
            self.logger.info(
                "MX_GW_TEST is not set")
            raise self.skipTest(
                "Env variable MX_GW_TEST not set. Skipping the test")
        return True


class TestSvcRegrFeature(BaseSvc_FwTest, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegrFeature, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_policy_delete_add_transparent_mode(self):
        """Test policy update in transparent mode service chaining."""
        self.verify_svc_transparent_datapath()
        return self.verify_policy_delete_add()

    @preposttest_wrapper
    def test_policy_delete_add_in_network_mode(self):
        """Test policy update in in network mode service chaining."""
        self.verify_svc_in_network_datapath()
        return self.verify_policy_delete_add()

    @preposttest_wrapper
    def test_policy_to_more_vns_transparent_mode(self):
        """Attach the same policy to  one more left and right VN's transparent mode service chaining."""
        self.verify_svc_transparent_datapath()
        return self.verify_add_new_vns()

    @preposttest_wrapper
    def test_policy_to_more_vms_in_network_mode(self):
        """Add more VM's to VN's of in network mode service chaining."""
        self.verify_svc_in_network_datapath()
        return self.verify_add_new_vms()

    @preposttest_wrapper
    def test_policy_port_protocol_change_transparent_mode(self):
        """Change the port and protocol of policy transparent mode service chaining."""
        self.verify_svc_transparent_datapath()
        return self.verify_protocol_port_change()

    @preposttest_wrapper
    def test_policy_port_protocol_change_in_network_mode(self):
        """Change the port and protocol of policy in network mode service chaining."""
        self.verify_svc_in_network_datapath()
        return self.verify_protocol_port_change(mode='in-network')


class TestSvcRegrwithMirror(BaseSvc_FwTest, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegrwithMirror, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_firewall_in_network_with_mirroring_transparent_mode(self):
        """test firewall in in_network with mirroring in transparent mode"""
        return self.verify_firewall_with_mirroring(firewall_svc_mode='in-network-nat', mirror_svc_mode='transparent')

    @preposttest_wrapper
    def test_firewall_transparent_with_mirroring_in_network_mode(self):
        """test firewall in transparent with mirroring in in_network mode"""
        return self.verify_firewall_with_mirroring(firewall_svc_mode='transparent', mirror_svc_mode='in-network')

    @preposttest_wrapper
    def test_firewall_transparent_with_mirroring_in_transparent(self):
        """test firewall in transparent with mirroring in in_network mode"""
        return self.verify_firewall_with_mirroring(firewall_svc_mode='transparent', mirror_svc_mode='transparent')

    @preposttest_wrapper
    def test_firewall_in_network_with_mirroring_in_network(self):
        """test firewall in in-network with mirroring in in_network mode"""
        return self.verify_firewall_with_mirroring(firewall_svc_mode='in-network-nat', mirror_svc_mode='in-network')

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
