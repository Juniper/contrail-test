import os
import fixtures
import testtools
import unittest
from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from time import sleep
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.servicechain.firewall.verify import VerifySvcFirewall
import traffic_tests
import time
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
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
        self.nova_h = self.res.nova_h
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.quantum_h = self.connections.quantum_h

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
    def test_ecmp_svc_in_network_with_static_route_no_policy(self):
        """
        Description:    Validate service chaining in-network mode datapath having a static route entries of the either virtual networks pointing to the corresponding interfaces of the
        service instance. We will not configure any policy.
        Test steps:
            1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
            2.  Creating a service instance in in-network mode with 1 instance and left-interface of the service instance sharing the IP and both the left and the right interfaces enabled for static route.
            3.  Delete the policy.
            4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.

        Maintainer : ganeshahv@juniper.net
        """
        if getattr(self, 'res', None):
            self.vn1_fq_name = "default-domain:admin:" + self.res.vn1_name
            self.vn1_name = self.res.vn1_name
            self.vn1_subnets = self.res.vn1_subnets
            self.vm1_name = self.res.vn1_vm1_name
            self.vn2_fq_name = "default-domain:admin:" + self.res.vn2_name
            self.vn2_name = self.res.vn2_name
            self.vn2_subnets = self.res.vn2_subnets
            self.vm2_name = self.res.vn2_vm2_name
        else:
            self.vn1_fq_name = "default-domain:admin:in_network_vn1"
            self.vn1_name = "in_network_vn1"
            self.vn1_subnets = ['10.1.1.0/24']
            self.vm1_name = 'in_network_vm1'
            self.vn2_fq_name = "default-domain:admin:in_network_vn2"
            self.vn2_name = "in_network_vn2"
            self.vn2_subnets = ['20.2.2.0/24']
            self.vm2_name = 'in_network_vm2'

        self.verify_svc_in_network_datapath(si_count=1, svc_scaling=True, max_inst=1, static_route=[
                                            'None', self.vn2_subnets[0], self.vn1_subnets[0]])
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)

        self.logger.info(
            '***** Will Detach the policy from the networks and delete it *****')
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)
        sleep(30)

        self.logger.info(
            '***** Ping and traffic between the networks should go thru fine because of the static route configuration *****')
        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)

        return True

    # end test_ecmp_svc_in_network_with_static_route_no_policy

    @preposttest_wrapper
    def test_ecmp_svc_in_network_nat_with_3_instance(self):
        """Validate ECMP with service chaining in-network-nat mode datapath having
           service instance
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Checking for ping and bidirectional tcp traffic between vm1 and vm2.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
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
           service instance
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Checking for ping and bidirectional tcp traffic between vm1 and vm2.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        self.logger.info('Verify Traffic Flow in both the directions')
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.verify_traffic_flow(self.vm2_fixture, self.vm1_fixture)
        return True
    # end test_ecmp_svc_transparent_with_3_instance

# end ECMPSanityFixture
