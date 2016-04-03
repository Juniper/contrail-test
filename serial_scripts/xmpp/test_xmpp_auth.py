import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vnc_api.vnc_api import VncApi
from scripts.securitygroup.verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import XmppBase
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture,get_secgrp_id_from_name
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
from tcutils.topo.sdn_topo_setup import *
import test
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name
from tcutils.contrail_status_check import *

class TestXmpptests(XmppBase, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(TestXmpptests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestXmpptests, cls).tearDownClass()

    def is_test_applicable(self):
        for node in self.inputs.bgp_control_ips:
            if not self.check_if_xmpp_auth_enabled(node):
                return (False, 'Xmpp auth should be set before running tests')
        return (True, None)

    def setUp(self):
        super(TestXmpptests, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.config_basic()
        else:
            return

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_precedence_xmpp_auth(self):
        """
        Description: Undo xmpp auth with allow specific protocol on all ports and policy with allow all between VN's
        """
        for node in self.inputs.bgp_control_ips:
            cmd = 'openstack-config --del /etc/contrail/contrail-control.conf DEFAULT xmpp_auth_enable'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-control restart'
            self.inputs.run_cmd_on_server(node, cmd)
            sleep(30)
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up after deleting xmpp auth" 
            assert (self.check_if_xmpp_auth_enabled(node, 'NIL')), "Xmpp auth still set after disabling it on server side"
        for node in self.inputs.bgp_control_ips:
            cmd = 'openstack-config --set /etc/contrail/contrail-control.conf DEFAULT xmpp_auth_enable True'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-control restart'
            self.inputs.run_cmd_on_server(node, cmd)
            sleep(30)
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up after adding back xmpp auth"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set after enabling it on server side"

        return True

    #end test_precedence_xmpp_auth 

    @test.attr(type=['sanity'])  
    @preposttest_wrapper
    def test_undo_xmpp_auth(self):
        """
        Description: Undo xmpp auth with allow specific protocol on all ports and policy with allow all between VN's
        """
        for node in self.inputs.bgp_control_ips:
            cmd = 'openstack-config --del /etc/contrail/contrail-control.conf DEFAULT xmpp_auth_enable'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-control restart'
            self.inputs.run_cmd_on_server(node, cmd)
        sleep(30)
        assert (self.check_xmpp_status(node)), "XMPP between nodes not up after deleting xmpp auth"
        assert (self.check_if_xmpp_auth_enabled(node, 'NIL')), "Xmpp auth still set after disabling it on server side"
        for node in self.inputs.bgp_control_ips:
            cmd = 'openstack-config --set /etc/contrail/contrail-control.conf DEFAULT xmpp_auth_enable True'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-control restart'
            self.inputs.run_cmd_on_server(node, cmd)
        sleep(30)
        assert (self.check_xmpp_status(node)), "XMPP between nodes not up after adding back xmpp auth"
        assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set after enabling it on server side"

        return True
    #end test_undo_xmpp_auth

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_compute_negative_xmpp_auth(self):
        """
        Description: Undo xmpp auth with allow specific protocol on all ports and policy with allow all between VN's
        """
        for node in self.inputs.compute_ips:
            cmd = 'openstack-config --del /etc/contrail/contrail-vrouter-agent.conf DEFAULT xmpp_auth_enable'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-vrouter restart'
            self.inputs.run_cmd_on_server(node, cmd)
        sleep(15)
        for node in self.inputs.bgp_control_ips:
            assert (not (self.check_if_xmpp_connections_present(node))), "XMPP between nodes should not be up after deleting xmpp auth on agent side"
        for node in self.inputs.compute_ips:
            cmd = 'openstack-config --set /etc/contrail/contrail-vrouter-agent.conf DEFAULT xmpp_auth_enable True'
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd)
            cmd = 'service supervisor-vrouter restart'
            self.inputs.run_cmd_on_server(node, cmd)
        sleep(15)
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up after adding back xmpp auth"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set after enabling it on agent side"

        return True
    #end test_compute_negative_xmpp_auth

    @preposttest_wrapper
    def test_restart_services_xmpp_auth(self):
        """
        Description: Undo xmpp auth with allow specific protocol on all ports and policy with allow all between VN's
        """
        for i in range(1,10):
            for node in self.inputs.compute_ips:
                cmd = 'service supervisor-vrouter restart'
                self.inputs.run_cmd_on_server(node, cmd)
        sleep(30)
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set"
        for i in range(1,10):
            for node in self.inputs.bgp_control_ips:
                cmd = 'service supervisor-control restart'
                self.inputs.run_cmd_on_server(node, cmd)
        sleep(30)
        for node in self.inputs.bgp_control_ips:
            assert (self.check_xmpp_status(node)), "XMPP between nodes not up"
            assert (self.check_if_xmpp_auth_enabled(node)), "Xmpp auth not set"

        return True
    #end test_restart_services_xmpp_auth

#end class Xmpptests
