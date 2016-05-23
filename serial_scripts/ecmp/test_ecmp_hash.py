import sys
import os
import fixtures
import testtools
import unittest
import time
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from vnc_api import vnc_api as my_vnc_api
from nova_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from fabric.state import connections as fab_connections
from common.ecmp.ecmp_test_resource import ECMPSolnSetup
from base import BaseECMPTest
from common import isolated_creds
import inspect
import test
from tcutils.contrail_status_check import *

class TestECMPHash(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

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
            ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
            self.config_all_hash(ecmp_hashing_include_fields)
        else:
            return

    @preposttest_wrapper
    def test_ecmp_hash_svc_transparent(self):

        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=2, svc_img_name='tiny_trans_fw',  ci=True)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.addCleanup(self.config_all_hash)
        return True

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network(self):
        """
         Description: Validate ECMP Hash with service chaining in-network mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """
        
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash)
        return True
    # end test_ecmp_svc_in_network

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_nat(self):
        """
         Description: Validate ECMP Hash with service chaining in-network-nat mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network-nat mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """

        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=2, svc_mode='in-network-nat', svc_img_name='tiny_nat_fw', ci=True)

        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash)
        return True
    # end test_ecmp_svc_in_network_nat

    @preposttest_wrapper
    def test_ecmp_hash_svc_precedence(self):
        """
         Description: Validate ECMP Hash with service chaining in-network mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """

        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.verify_if_hash_changed(ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True}
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.verify_if_hash_changed(ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_if_hash_changed(ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash)
        return True

    # end test_ecmp_svc_precedence

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_vrouter(self):
        """
         Description: Validate ECMP Hash with service chaining in-network mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """

        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        for node in self.inputs.compute_ips:
             self.inputs.restart_service('supervisor-vrouter', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable(nodes = [node])
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash)
        return True
    # end test_ecmp_svc_in_network_restart_vrouter

    @preposttest_wrapper
    def test_ecmp_hash_svc_in_network_restart_schema(self):
        """
         Description: Validate ECMP Hash with service chaining in-network mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """

        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn1_fixture)
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm1_fixture)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        for node in self.inputs.cfgm_ips:
             self.inputs.restart_service('contrail-schema', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable(nodes = [node])
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash)
        return True
    # end test_ecmp_svc_in_network_restart_schema

