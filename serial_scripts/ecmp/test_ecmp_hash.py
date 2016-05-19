import os
import fixtures
import testtools
import unittest
import time
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
from fabric.state import connections as fab_connections
from common.ecmp.ecmp_test_resource import ECMPSolnSetup
from base import BaseECMPRestartTest
import test
from common import isolated_creds                                                                                     
import inspect

class TestECMPHash(BaseECMPRestartTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPHash, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 1:
            return (False, 'Scaling test. Will run only on multiple node setup')
        return (True, None)

    def setUp(self):
        super(TestECMPHash, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.config_all_hash()
        else:
            return

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_nat_scale_max_instances(self):
        """
         Description: Validate ECMP Hash with service chaining in-network-nat mode datapath by incrementing the max instances
                    from 4 in steps of 4 till 16
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network-nat mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   Increment the service instance max count by 4 and repeat steps 1-5.
           7.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """
        
        for i in range(4, 17, 4):
            self.logger.info(
                '***** Will launch %s instances in the Service Chain *****' % i)
            self.verify_svc_in_network_datapath(
                si_count=1, svc_scaling=True, max_inst=i, svc_mode='in-network-nat')
            svm_ids = self.si_fixtures[0].svm_ids
            self.get_rt_info_tap_intf_list(
                self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
            dst_vm_list= [self.vm2_fixture]
            ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
            self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
            self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
            self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
            for si in self.si_fixtures:
                self.logger.info('Deleting the SI %s' % si.st_name)
                si.cleanUp()
                si.verify_on_cleanup()
                self.remove_from_cleanups(si)
            self.logger.info('Deleting the ST %s' %
                             self.st_fixture.st_name)
            self.st_fixture.cleanUp()
            self.remove_from_cleanups(self.st_fixture)
        self.addCleanup(self.config_all_hash)
        return True
    # end test_ecmp_svc_in_network_nat_scale_max_instances

