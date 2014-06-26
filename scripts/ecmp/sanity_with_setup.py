import os
import fixtures
import testtools
import unittest
from connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from time import sleep
from servicechain.config import ConfigSvcChain
from servicechain.verify import VerifySvcChain
from servicechain.firewall.verify import VerifySvcFirewall
import traffic_tests
import time
from contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from ecmp.ecmp_traffic import ECMPTraffic
from ecmp.ecmp_verify import ECMPVerify
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from fabric.state import connections as fab_connections
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


class ECMPSanityFixture(testtools.TestCase, ResourcedTestCase, VerifySvcFirewall, ECMPTraffic, ECMPVerify):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.quantum_fixture = self.connections.quantum_fixture

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(ECMPSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(ECMPSanityFixture, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_static_route(self):
        """Validate service chaining in-network mode datapath having a static route entry pointing to one of the interfaces of the
        service instance"""
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=1, static_route=['None', '1.2.3.4/32', 'None'])
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.logger.info(
            '***** Will start tcpdump to capture a ICMP packet destined to 1.2.3.4 on the node housing the SI *****')
        svm_name = self.si_fixtures[0].si_name + '_1'
        host = self.get_svm_compute(svm_name)
        tapintf = self.get_svm_tapintf_of_vn(svm_name, self.vn1_fixture)
        session = ssh(host['host_ip'], host['username'], host['password'])
        cmd = 'tcpdump -ni %s dst 1.2.3.4 -vvv -c 1 > /tmp/%s_out.log' % (tapintf,
                                                                          tapintf)
        execute_cmd(session, cmd, self.logger)
        self.logger.info(
            '***** Will start a ping from VM %s to 1.2.3.4 *****' %
            self.vm1_fixture.vm_name)
        cmd_to_ping = ['sh -c "ping -c 100 1.2.3.4 &"; ls']
        self.vm1_fixture.run_cmd_on_vm(cmds=cmd_to_ping, as_sudo=True)
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd = 'cat /tmp/%s_out.log' % tapintf
        out, err = execute_cmd_out(session, output_cmd, self.logger)
        self.logger.info('%s' % out)
        if '1.2.3.4' in out:
            result = True
            self.logger.info('Traffic to 1.2.3.4 seen using the static route')
        else:
            result = False
            assert result, 'Traffic to 1.2.3.4 not seen'
        return True
    # end test_ecmp_svc_in_network_with_static_route

    @preposttest_wrapper
    def test_ecmp_svc_in_network_nat_with_3_instance(self):
        """Validate ECMP with service chaining in-network-nat mode datapath having
        service instance"""
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3, svc_mode='in-network-nat')
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    # end test_ecmp_svc_in_network_nat_with_3_instance

    @preposttest_wrapper
    def test_ecmp_svc_transparent_with_3_instance(self):
        """Validate ECMP with service chaining transparent mode datapath having
        service instance"""
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        self.logger.info('Verify Traffic Flow in both the directions')
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.verify_traffic_flow(self.vm2_fixture, self.vm1_fixture)
        return True
    # end test_ecmp_svc_transparent_with_3_instance

# end ECMPSanityFixture
