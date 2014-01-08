"""Servcie chain mirroring Regression tests."""
import os
import unittest
import fixtures
import testtools

from connections import ContrailConnections
from contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from servicechain.mirror.verify import VerifySvcMirror


class SvcMirrorRegrFixture(testtools.TestCase, VerifySvcMirror):
    
    def setUp(self):
        super(SvcMirrorRegrFixture, self).setUp()  
        if 'PARAMS_FILE' in os.environ :
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)        
        self.agent_inspect= self.connections.agent_inspect
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj=self.connections.analytics_obj
    
    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMirrorSanityFixture, self).cleanUp()

    @preposttest_wrapper
    def test_svc_mirroring_with_2_analyzer(self):
        """Validate the service chain mirroring with three analyzers"""
        return self.verify_svc_mirroring(si_count=2)

    @preposttest_wrapper
    def test_svc_mirroring_policy_add_delete(self):
        """Validate the service chain mirroring after delete recreate policy"""
        self.verify_svc_mirroring()
        return self.verify_policy_delete_add(self.si_prefix)

    @preposttest_wrapper
    def test_svc_mirroring_add_more_vns(self):
        """Validate the service chain mirroring after adding rule to mirror traffic from aditional VNs"""
        self.verify_svc_mirroring()
        return self.verify_add_new_vns(self.si_prefix)

    @preposttest_wrapper
    def test_svc_mirroring_with_floating_ip(self):
        """Validate the service chain mirroring with floating IP"""
        return self.verify_svc_mirroring_with_floating_ip()

    @preposttest_wrapper
    def test_svc_mirroring_with_floating_ip_with_2_analyzer(self):
        """Validate the service chain mirroring with floating IP with 2 analyzer"""
        return self.verify_svc_mirroring_with_floating_ip(si_count=2)

    @preposttest_wrapper
    def test_svc_mirror_with_deny_rule(self):
        """Validate the service chain mirroring after adding rule to mirror traffic from aditional VNs"""
        return self.verify_svc_mirror_with_deny()

    @preposttest_wrapper
    def test_svc_mirroring_with_unidirection_rule(self):
        """Validate the service chain mirroring with allow traffic in unidirection rule"""
        return self.verify_svc_mirroring_unidirection()

    @preposttest_wrapper
    def test_svc_mirroring_with_unidirection_rule_with_2_analyzer(self):
        """Validate the service chain mirroring with allow traffic in unidirection rule"""
        return self.verify_svc_mirroring_unidirection(si_count=2)

    @preposttest_wrapper
    def test_attach_detach_policy_with_svc_mirroring(self):
        """Test case for bug 1533"""
        return self.verify_attach_detach_policy_with_svc_mirroring()


if __name__ == '__main__':
    unittest.main()
