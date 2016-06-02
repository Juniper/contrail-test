from tcutils.wrappers import preposttest_wrapper
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import XmppBase
from common.policy.config import ConfigPolicy
from vn_test import VNFixture
from vm_test import VMFixture
import os
import sys
import test
from tcutils.contrail_status_check import *


class TestXmpptests(XmppBase, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(TestXmpptests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestXmpptests, cls).tearDownClass()

    def is_test_applicable(self):
        try:
            assert self.inputs.xmpp_auth_enable
            assert self.inputs.xmpp_dns_auth_enable
            if not (self.inputs.xmpp_auth_enable and self.inputs.xmpp_dns_auth_enable):
                return (False, 'Xmpp auth should be set before running tests')
        except:
            return (False, 'Xmpp auth should be set before running tests')

        return (True, None)

    def setUp(self):
        super(TestXmpptests, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.config_basic()
        else:
            return

    @test.attr(type=['sm_sanity'])
    @preposttest_wrapper
    def test_precedence_xmpp_auth(self):
        """
        Precedence in XMPP auth is that server auth takes precedence over agent auth. To check this,
        undo xmpp auth on server side and check if XMPP is up and it shows no "TLS" string in introspect.
        """
        # Have to add cleanup here before entering for loop to disable auth as
        # there are asserts in the loop
        self.addCleanup(self.enable_auth_on_cluster)
        for node in self.inputs.bgp_control_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-control.conf',
                operation='del',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                node=node,
                service='supervisor-control')
            assert (self.check_xmpp_status(node)
                    ), "XMPP between nodes not up after deleting xmpp auth"
            assert (self.check_if_xmpp_auth_enabled(node, 'NIL')
                    ), "Xmpp auth still set after disabling it on server side"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        for node in self.inputs.bgp_control_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-control.conf',
                operation='set',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                value='true',
                node=node,
                service='supervisor-control')
            assert (self.check_xmpp_status(node)
                    ), "XMPP between nodes not up after adding back xmpp auth"
            assert (self.check_if_xmpp_auth_enabled(node)
                    ), "Xmpp auth not set after enabling it on server side"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        return True

    # end test_precedence_xmpp_auth

    @test.attr(type=['sm_sanity'])
    @preposttest_wrapper
    def test_undo_xmpp_auth(self):
        """
        Check if undoing setting and deleting xmpp auth creates any issues.
        Also confirm if introspect reflects the changes as and when they are done
        """
        for node in self.inputs.bgp_control_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-control.conf',
                operation='del',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                node=node,
                service='supervisor-control')
        # adding cleanup before assert
        self.addCleanup(self.enable_auth_on_cluster)
        assert (self.check_xmpp_status(node)
                ), "XMPP between nodes not up after deleting xmpp auth"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        assert (self.check_if_xmpp_auth_enabled(node, 'NIL')
                ), "Xmpp auth still set after disabling it on server side"
        for node in self.inputs.bgp_control_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-control.conf',
                operation='set',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                value='true',
                node=node,
                service='supervisor-control')
        assert (self.check_xmpp_status(node)
                ), "XMPP between nodes not up after adding back xmpp auth"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        assert (self.check_if_xmpp_auth_enabled(node)
                ), "Xmpp auth not set after enabling it on server side"
        return True
    # end test_undo_xmpp_auth

    @test.attr(type=['sm_sanity'])
    @preposttest_wrapper
    def test_compute_negative_xmpp_auth(self):
        """
        Configure xmpp auth only on agent side. Because of server precedence over agent, XMPP should go down.
        Reconfigure auth back and confirm if things go back to normal.
        """

        for node in self.inputs.compute_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-vrouter-agent.conf',
                operation='del',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                node=node,
                service='supervisor-vrouter')
        # adding cleanup before assert
        self.addCleanup(self.enable_auth_on_cluster)
        for node in self.inputs.bgp_control_ips:
            assert (not (self.check_if_xmpp_connections_present(node))
                    ), "XMPP between nodes should not be up after deleting xmpp auth on agent side"
        assert (not (self.check_if_cluster_has_xmpp())
                ), "XMPP connections should not be found"

        for node in self.inputs.compute_ips:
            self.update_contrail_conf(
                conf_file='/etc/contrail/contrail-vrouter-agent.conf',
                operation='set',
                section='DEFAULT',
                knob='xmpp_auth_enable',
                value='true',
                node=node,
                service='supervisor-vrouter')
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)
                    ), "XMPP between nodes not up after adding back xmpp auth"
            assert (self.check_if_xmpp_auth_enabled(node)
                    ), "Xmpp auth not set after enabling it on agent side"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        return True
    # end test_compute_negative_xmpp_auth

    @preposttest_wrapper
    def test_restart_services_xmpp_auth(self):
        """
        Configure xmpp auth and restart control and vrouter services for 10 iterations.
        Cluster status is checked after each restart iteration. XMPP status is check after
        all iterations are done.
        """

        # adding cleanup here before for loop as the loop has assert
        self.addCleanup(self.enable_auth_on_cluster)
        for i in range(1, 10):
            for node in self.inputs.compute_ips:
                self.inputs.restart_service('supervisor-vrouter', [node])
                cluster_status, error_nodes = ContrailStatusChecker(
                ).wait_till_contrail_cluster_stable(nodes=[node])
                assert cluster_status, 'Hash of error nodes and services : %s' % (
                    error_nodes)
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        for i in range(1, 10):
            for node in self.inputs.bgp_control_ips:
                self.inputs.restart_service('supervisor-control', [node])
                cluster_status, error_nodes = ContrailStatusChecker(
                ).wait_till_contrail_cluster_stable(nodes=[node])
                assert cluster_status, 'Hash of error nodes and services : %s' % (
                    error_nodes)
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set"
        assert (self.check_if_cluster_has_xmpp), "XMPP connections not found"
        return True
    # end test_restart_services_xmpp_auth

# end class Xmpptests
