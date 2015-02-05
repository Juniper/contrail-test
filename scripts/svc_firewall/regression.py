"""Service chain firewall regression suite."""
import os
import unittest
import fixtures
import testtools

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper

from common.servicechain.firewall.verify import VerifySvcFirewall


class SvcMonRegrFixture(testtools.TestCase, VerifySvcFirewall):

    def setUp(self):
        super(SvcMonRegrFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect = self.connections.agent_inspect
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMonRegrFixture, self).cleanUp()

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

    @preposttest_wrapper
    def test_firewall_in_network_with_mirroring_transparent_mode(self):
        """test firewall in in_network with mirroring in transparent mode"""
        return self.verify_firewall_with_mirroring(firewall_svc_mode='in-network', mirror_svc_mode='transparent')

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
        return self.verify_firewall_with_mirroring(firewall_svc_mode='in-network', mirror_svc_mode='in-network')

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

if __name__ == '__main__':
    unittest.main()
