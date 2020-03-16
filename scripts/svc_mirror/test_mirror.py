"""Servcie chain mirroring Regression tests."""
from __future__ import absolute_import
from .base import BaseMirrorTest
import os
import unittest
import fixtures
import testtools
import test

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.mirror.verify import VerifySvcMirror


class TestSVCV2Mirror(BaseMirrorTest, VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(TestSVCV2Mirror, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_svc_v2_mirroring(self):
        """Validate the service chain mirroring"""
        return self.verify_svc_mirroring()

    @preposttest_wrapper
    def test_in_network_svc_v2_mirroring(self):
        """Validate the in network service chain mirroring"""
        return self.verify_svc_mirroring(svc_mode='in-network')

    @preposttest_wrapper
    def test_svc_v2_mirroring_with_2_analyzer(self):
        """Validate the service chain mirroring with three analyzers"""
        #TODO 
        # Need to add rule for udp and validate second mirror instance
        return self.verify_svc_mirroring(si_count=2)

    @preposttest_wrapper
    def test_svc_v2_mirroring_policy_add_delete(self):
        """Validate the service chain mirroring after delete recreate policy"""
        svc_chain_info = self.verify_svc_mirroring()
        return self.verify_policy_delete_add(svc_chain_info)

    @preposttest_wrapper
    def test_svc_v2_mirroring_add_more_vns(self):
        """Validate the service chain mirroring after adding rule to mirror traffic from aditional VNs"""
        svc_chain_info = self.verify_svc_mirroring()
        return self.verify_add_new_vns(svc_chain_info)


class TestSVCV2MirrorFIP(BaseMirrorTest, VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(TestSVCV2MirrorFIP, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_svc_v2_mirroring_with_floating_ip(self):
        """Validate the service chain mirroring with floating IP"""
        return self.verify_svc_mirroring_with_floating_ip()

    @preposttest_wrapper
    def test_svc_v2_mirroring_with_floating_ip_with_2_analyzer(self):
        """Validate the service chain mirroring with floating IP with 2 analyzer"""
        #TODO 
        # Need to add rule for udp and validate second mirror instance
        return self.verify_svc_mirroring_with_floating_ip(max_inst=2)


class TestSVCV2MirrorPolicy(BaseMirrorTest, VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(TestSVCV2MirrorPolicy, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_svc_v2_mirror_with_deny_rule(self):
        """Validate the service chain mirroring after adding rule to mirror traffic from aditional VNs"""
        return self.verify_svc_mirror_with_deny()

    @preposttest_wrapper
    def test_svc_v2_mirroring_with_unidirection_rule(self):
        """Validate the service chain mirroring with allow traffic in unidirection rule"""
        return self.verify_svc_mirroring_unidirection()

    @preposttest_wrapper
    def test_svc_v2_mirroring_with_unidirection_rule_with_2_analyzer(self):
        """Validate the service chain mirroring with allow traffic in unidirection rule"""
        #TODO 
        # Need to add rule for udp and validate second mirror instance
        return self.verify_svc_mirroring_unidirection()

    @preposttest_wrapper
    def test_attach_detach_policy_with_svc_v2_mirroring(self):
        """Test case for bug 1533"""
        return self.verify_attach_detach_policy_with_svc_mirroring()

    @preposttest_wrapper
    def test_detach_attach_diff_policy_with_svc_v2_mirroring(self):
        """Test case for bug 2414"""
        '''steps and checkpoints:
        1.      attach pol1 to 2 n/w VN1 and VN2, routes get exchanged as expected
        2.      Detach pol1 from VN1(only), routes are removed from both VNs.
        3.      In VN2, detach pol1 and attach again. Routes are NOT exchanged.
        4.      In VN2, detach pol1 and attach pol-analyzer. routes are exchanged.
        5.      Now detach pol-analyzer from VN2, routes get deleted from both the n/ws
        6.      again attach pol1 to VN2.  routes should not be exchanged between both the n/ws'''

        return self.verify_detach_attach_diff_policy_with_mirroring()

    @preposttest_wrapper
    def test_detach_attach_policy_change_rules_with_svc_v2(self):
        """Test case for bug 2414"""
        '''steps and checkpoints:
        1.      attach pol-analyzer to both n/w, routes get exchanged.
        2.      Detach pol-analyzer from VN1(only), routes are NOT removed from both VNs.
        3.      Change pol-analyzer rules to remove mirror, routes should be REMOVED from both n/ws
        4.      In VN2, detach pol-analyzer.
        5.      In VN2, attach pol-analyzer again. routes should NOT be exchanged.'''

        return self.verify_detach_attach_policy_change_rules()

    @preposttest_wrapper
    def test_policy_order_change_with_svc_v2(self):
        """Validate mirroring after policy order change."""
        '''steps and checkpoints:
        pol1  : pass protocol any network any port any <> network any port any
        pol-analyzer: pass protocol any network vn1 port any <> network vn2 port any mirror_to default-domain:admin:si-2
        analyzer: transparent, automatic VN
        1. pol-analyzer is attached to both vn1 and vn2, traffic should be mirrored.
        2. attach the policy in both VN in order as (pol1, pol-analyzer), traffic should not be mirrored.
        3. change the order of policy in vn1 as (pol-analyzer, pol1), traffic should be mirrored
        4. change the order of policy in vn2 as (pol-analyzer, pol1), traffic should be mirrored
        5. now detach pol1 from both VN, traffic should be mirrored'''

        return self.verify_policy_order_change()

class TestSVCV2MirrorIPv6(TestSVCV2Mirror):

    @classmethod
    def setUpClass(cls):
        super(TestSVCV2MirrorIPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

    @preposttest_wrapper
    def test_svc_v2_mirroring(self):
        """Validate the service chain mirroring"""
        return self.verify_svc_mirroring()


class TestSVCV2MirrorPolicyIPv6(TestSVCV2MirrorPolicy):

    @classmethod
    def setUpClass(cls):
        super(TestSVCV2MirrorPolicyIPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

if __name__ == '__main__':
    unittest.main()
