# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run vdns_tests'. To run specific tests,
# You can do 'python -m testtools.run -l vdns_tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import unittest
import fixtures
import testtools
import traceback

from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BasevDNSRestartTest 
from common import isolated_creds
import inspect
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from vdns_fixture import *
from floating_ip import *
from policy_test import *
from control_node import *
from user_test import UserFixture
import test

class TestvDNSRestart(BasevDNSRestartTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNSRestart, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest
 
    @preposttest_wrapper
    def test_vdns_controlnode_switchover(self):
        ''' This test test control node switchover functionality'''
        restart_process = 'ControlNodeRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_dns_restart(self):
        ''' This test test dns process restart functionality'''
        restart_process = 'DnsRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_agent_restart(self):
        '''This test tests agent process restart functionality'''
        restart_process = 'AgentRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_named_restart(self):
        '''This test tests named process restart functionality'''
        restart_process = 'NamedRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
