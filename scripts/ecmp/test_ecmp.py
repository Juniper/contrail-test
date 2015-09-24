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


class TestECMPSanity(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPSanity, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity_WIP', 'sanity'])
    @preposttest_wrapper
    def test_ecmp_svc_transparent_with_3_instance(self):
        """
           Description: Validate ECMP with service chaining transparent mode datapath having service instance
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Checking for ping and bidirectional tcp traffic between vm1 and vm2.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=2, svc_img_name='tiny_trans_fw',  ci=True)
        return True
    # end test_ecmp_svc_transparent_with_3_instance

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
                     service instance.
        Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in in-network mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy
                     between the VNs.
                4.Checking for ping and traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2
                  from vm1 and vice-versa.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
    # end test_ecmp_svc_in_network_with_3_instance

    @test.attr(type=['sanity'])
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
        vn1_subnet_list = ['100.1.1.0/24']
        vn2_subnet_list = ['200.1.1.0/24']
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling=True, max_inst=1, static_route=[
                                            'None', vn2_subnet_list[0], vn1_subnet_list[0]], vn1_subnets=vn1_subnet_list, vn2_subnets=vn2_subnet_list)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.logger.info(
            '***** Will Detach the policy from the networks and delete it *****')
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)
        sleep(30)
        self.logger.info(
            '***** Ping and traffic between the networks should go thru fine because of the static route configuration *****')
        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)

        # Cleaning up
        self.delete_vm(self.vm1_fixture)
        self.delete_vm(self.vm2_fixture)
        self.delete_si_st(self.si_fixtures, self.st_fixture)
        self.delete_vn(self.vn1_fixture)
        self.delete_vn(self.vn2_fixture)

        return True
        # end test_ecmp_svc_in_network_with_static_route_no_policy


class TestECMPFeature(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPFeature, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_ecmp_in_pol_based_svc(self):
        """
           Description: Validate ECMP with Policy Based service chaining
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy, which allows only TCP traffic between the VNs.
                4.Ping and UDP traffic should fail, while tcp traffic should be allowed between vm1 and vm2.
           Pass criteria: Ping and UDP Traffic between the VMs should fail, while TCP traffic should reach vm2 from vm1.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3, proto='tcp')
        self.vm1_fixture.put_pub_key_to_vm()
        self.vm2_fixture.put_pub_key_to_vm()
        # TFTP from Left VM to Right VM is expected to fail
        errmsg1 = "TFTP to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='tftp', size='333', expectation=False), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to pass
        errmsg2 = "SCP to right VM ip %s from left VM failed; expected to pass" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='scp', size='444'), errmsg2
        return True
    # end test_ecmp_in_pol_based_svc

    @preposttest_wrapper
    def test_ecmp_in_pol_based_svc_pol_update(self):
        """
           Description: Validate ECMP with Policy Based service chaining
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy, which allows only TCP traffic between the VNs.
                4.Ping and UDP traffic should fail, while tcp traffic should be allowed between vm1 and vm2.
                5.Dynamically update the policy to allow only UDP Traffic.
           Pass criteria: Ping and UDP Traffic between the VMs should fail, while TCP traffic should reach vm2 from vm1.
                          After updating the policy, TCP traffic should be blocked, while UDP should flow thru.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3, proto='tcp')
        self.vm1_fixture.put_pub_key_to_vm()
        self.vm2_fixture.put_pub_key_to_vm()
        # TFTP from Left VM to Right VM is expected to fail
        errmsg1 = "TFTP to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='tftp', size='111', expectation=False), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to pass
        errmsg2 = "SCP to right VM ip %s from left VM failed; expected to pass" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='scp', size='222'), errmsg2
        self.logger.info('Will update the policy to allow only udp')
        old_data = {
            'policy': {'entries': self.policy_fixture.policy_obj['policy']['entries']}}
        old_entry = self.policy_fixture.policy_obj['policy']['entries']
        new_entry = old_entry
        new_entry['policy_rule'][0]['protocol'] = u'udp'
        pol_id = self.policy_fixture.policy_obj['policy']['id']
        new_data = {'policy': {'entries': new_entry}}
        self.policy_fixture.update_policy(pol_id, new_data)
        time.sleep(5)
        # TFTP from Left VM to Right VM is expected to pass
        errmsg1 = "TFTP to right VM ip %s from left VM failed; expected to pass" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='tftp', size='101'), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to fail
        errmsg2 = "SCP to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.check_file_transfer(
            dest_vm_fixture=self.vm2_fixture, mode='scp', size='202', expectation=False), errmsg2
        return True
    # end test_ecmp_in_pol_based_svc_pol_update

    @preposttest_wrapper
    def test_multi_SC_with_ecmp(self):
        """
        Description: Validate Multiple Service Instances with ECMP. 
        Test steps:
                    1. Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.  Creating 3 service instances in transparent mode with 3 instances each.
                    3.  Creating a service chain by applying the service instance as a service in a policy b
            etween the VNs.
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
                  rom vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=3, svc_scaling=True, max_inst=3)
        return True
    # end test_multi_SC_with_ecmp

    @test.attr(type=['ci_sanity_WIP'])
    @preposttest_wrapper
    def test_ecmp_svc_in_network_nat_with_3_instance(self):
        """
         Description: Validate ECMP with service chaining in-network-nat mode datapath having service instance
         Test steps:
           1.	Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.	Creating a service instance in in-network-nat mode with 3 instances and
                left-interface of the service instances sharing the IP and enabled for static route.

           3.	Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.	Checking for ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
         Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=2, svc_mode='in-network-nat', svc_img_name='tiny_nat_fw', ci=True)
        return True
    # end test_ecmp_svc_in_network_nat_with_3_instance

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_add_flows(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
                     service instance. Add flows on top and verify that the current flows are unaffected
        Test steps:
                    1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.  Creating a service instance in in-network-nat mode with 3 instances and
                        left-interface of the service instances sharing the IP and enabled for static route.
                    3.   Start traffic and and more flows. 
                    4.  Creating a service chain by applying the service instance as a service in a policy b
                        etween the VNs.
                    5.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
                       rom vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        vm_list = [self.vm1_fixture, self.vm2_fixture]
        for vm in vm_list:
            vm.install_pkg("Traffic")
        old_stream1 = Stream(
            protocol="ip", proto="icmp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        old_stream2 = Stream(
            protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        old_stream3 = Stream(
            protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        self.old_stream_list = [old_stream1, old_stream2, old_stream3]

        dst_vm_list = [self.vm2_fixture]
        self.old_sender, self.old_receiver = self.start_traffic(
            self.vm1_fixture, dst_vm_list, self.old_stream_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.logger.info(
            'Sending traffic for 10 seconds and will start more flows')
        time.sleep(10)
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.verify_flow_records(
            self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.stop_traffic(
            self.old_sender, self.old_receiver, dst_vm_list, self.old_stream_list)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_add_flows

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_diff_proto(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
                service instance. Send 3 different protocol traffic to the same destination.
        Test steps:
                    1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.  Creating a service instance in in-network-nat mode with 3 instances and
                         left-interface of the service instances sharing the IP and enabled for static route.
                    3.   Start traffic and send 3 different protocol traffic to the same destination. 
                    4.  Creating a service chain by applying the service instance as a service in a policy b
                            etween the VNs.
                    5.  Checking for ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
            rom vm1.
         Maintainer : ganeshahv@juniper.net
         """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        vm_list = [self.vm1_fixture, self.vm2_fixture]
        for vm in vm_list:
            vm.install_pkg("Traffic")

        stream1 = Stream(
            protocol="ip", proto="icmp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream2 = Stream(
            protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream3 = Stream(
            protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        self.stream_list = [stream1, stream2, stream3]

        dst_vm_list = [self.vm2_fixture]
        self.sender, self.receiver = self.start_traffic(
            self.vm1_fixture, dst_vm_list, self.stream_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)

        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)

        self.verify_flow_records(
            self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)

        self.stop_traffic(
            self.sender, self.receiver, dst_vm_list, self.stream_list)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_diff_proto

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_incr_dip(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
                 service instance. Send traffic to 3 different DIPs.
        Test steps:
                    1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.  Creating a service instance in in-network-nat mode with 3 instances and
                         left-interface of the service instances sharing the IP and enabled for static route.
                    3.   Start traffic and send 3 different streams, one each to a DIP.
                    4.  Creating a service chain by applying the service instance as a service in a policy b
         etween the VNs.
                    5.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
            rom vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dest_vm2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='dest_vm2'))
        assert dest_vm2.verify_on_setup()
        dest_vm3 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='dest_vm3'))
        assert dest_vm3.verify_on_setup()
        vm_list = [self.vm1_fixture, self.vm2_fixture, dest_vm2, dest_vm3]
        for vm in vm_list:
            vm.install_pkg("Traffic")

        stream1 = Stream(
            protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,
            dst=self.vm2_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream2 = Stream(
            protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,
            dst=dest_vm2.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream3 = Stream(
            protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,
            dst=dest_vm3.vm_ip, sport=unicode(8000), dport=unicode(9000))

        self.stream_list = [stream1, stream2, stream3]

        dst_vm_list = [self.vm2_fixture]
        self.sender, self.receiver = self.start_traffic(self.vm1_fixture, dst_vm_list, self.stream_list,
                                                        self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.verify_flow_records(
            self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.stop_traffic(
            self.sender, self.receiver, dst_vm_list, self.stream_list)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_incr_dip

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_policy_bind_unbind(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
              multiple service chain. Unbind and bind back the policy and check traffic.
        Test steps:
                        1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                        2.  Creating a service instance in in-network-nat mode with 3 instances and
                             left-interface of the service instances sharing the IP and enabled for static route.
                        3.   Start traffic.
                        4.   Unbind and bind back the policy and check tha traffic.
                        5.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
                rom vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.logger.info(
            'Will Detach the policy from the networks and delete it')
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)
        sleep(30)
        self.logger.info('Traffic between the VMs should fail now')
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.vm2_fixture.vm_ip
        assert self.vm1_fixture.ping_with_certainty(
            self.vm2_fixture.vm_ip, expectation=False), errmsg

        self.logger.info(
            'Will Re-Configure the policy and attach it to the networks')
        self.policy_fixture = self.config_policy(self.policy_name, self.rules)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.vn2_fixture)
        sleep(30)
        self.logger.info('Traffic between the VMs should pass now')
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
    # end test_ecmp_svc_in_network_with_policy_bind_unbind


class TestECMPwithFIP(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPwithFIP, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_ecmp_with_svc_with_fip_dest(self):
        """
        Description: Validate ECMP with service chaining and FIP at the destination
        Test steps:
                    1.  Creating 4 VMs in a VN and associating a single FIP with the three of them.
                    2.  Sending traffic from one VM to the FIP.
                    3.  Check the route table for the FIP address which should indicate ECMP.
        Pass criteria: Traffic should reach the other VMs from vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        self.logger.info('.' * 80)
        self.logger.info(
            'We will create 3 VMs at the destination and make them share the same FIP address')
        self.logger.info('.' * 80)
        self.my_fip_name = 'fip'
        self.my_fip = self.get_random_fip(self.vn1_fixture)

        self.vm2_1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2_1'))
        self.vm2_2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2_2'))

        assert self.vm2_1.verify_on_setup()
        assert self.vm2_2.verify_on_setup()

        self.fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name='some-pool1', vn_id=self.vn1_fixture.vn_id))
        assert self.fip_fixture.verify_on_setup()

        self.fvn_obj = self.vnc_lib.virtual_network_read(
            id=self.vn1_fixture.vn_id)
        self.fip_pool_obj = FloatingIpPool('some-pool1', self.fvn_obj)
        self.fip_obj = FloatingIp('fip', self.fip_pool_obj, self.my_fip, True)

        # Get the project_fixture
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        # Read the project obj and set to the floating ip object.
        self.fip_obj.set_project(self.project_fixture.project_obj)

        self.vn2_fq_name = self.vn2_fixture.vn_fq_name
        self.vn2_vrf_name = self.vn2_fixture.vrf_name
        self.vn2_ri_name = self.vn2_fixture.ri_name
        self.vmi1_id = self.vm2_fixture.tap_intf[
            self.vn2_fixture.vn_fq_name]['uuid']
        self.vmi2_id = self.vm2_1.tap_intf[
            self.vn2_fixture.vn_fq_name]['uuid']
        self.vmi3_id = self.vm2_2.tap_intf[
            self.vn2_fixture.vn_fq_name]['uuid']
        self.vm2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi1_id)
        self.vm2_1_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi2_id)
        self.vm2_2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi3_id)
        for intf in [self.vm2_intf, self.vm2_1_intf, self.vm2_2_intf]:
            self.fip_obj.add_virtual_machine_interface(intf)
        self.vnc_lib.floating_ip_create(self.fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, self.fip_obj.fq_name)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        self.vm1_fixture.ping_with_certainty(self.my_fip)
        return True
    # end test_ecmp_with_svc_with_fip_dest

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_add_del_same_fip(self):
        """
        Description: Validate ECMP with service chaining and FIP at the destination
        Test steps:
                   1.  Test communication between three VMs who have borrowed the FIP from common FIP pool.
                   2.   Delete two of the VMs and check that traffic flow is unaffected.
                   3.  Sending traffic from one VM to the FIP.
                   4.  Check the route table for the FIP address which should indicate ECMP.
        Pass criteria: Traffic should reach the other VMs from vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.setup_common_objects()
        vm_list = []
        vm_list = [self.vm1, self.vm2, self.vm3]

        self.logger.info('Will send traffic from the fvn_vm1 to 30.1.1.3')
        self.stream_list = self.setup_streams(
            self.fvn_vm1, vm_list, self.fvn_vm1.vm_ip, self.my_fip)
        self.sender, self.receiver = self.start_traffic(
            self.fvn_vm1, vm_list, self.stream_list, self.fvn_vm1.vm_ip, self.my_fip)

        self.logger.info(
            'Will disassociate the fip address from two VMs and check that there should be no traffic loss.')
        self.fip_obj.del_virtual_machine_interface(self.vm1_intf)
        self.fip_obj.del_virtual_machine_interface(self.vm3_intf)
        self.vnc_lib.floating_ip_update(self.fip_obj)
        sleep(5)
        self.logger.info(
            'Will re-associate the fip address to the VMs ')
        self.fip_obj.add_virtual_machine_interface(self.vm3_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm1_intf)
        self.vnc_lib.floating_ip_update(self.fip_obj)

        self.verify_flow_records(self.fvn_vm1, self.fvn_vm1.vm_ip, self.my_fip)
        self.stop_traffic(
            self.sender, self.receiver, vm_list, self.stream_list)

        return True
    # end test_ecmp_bw_three_vms_add_del_same_fip

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip_incr_sport(self):
        """
        Description: Test communication between three VMs who have borrowed the FIP from common FIP
         pool. Increment sport and have 3 flows setup.
        Test steps:
                       1.  Test communication between three VMs who have borrowed the FIP from common FIP pool.
                       2.  Sending 3 different streams with incrementing sports.
                       3.  Check the route table for the FIP address which should indicate ECMP.
         Pass criteria: Traffic should reach the other VMs from vm1.
         Maintainer : ganeshahv@juniper.net
         """
        self.setup_common_objects()
        vm_list = [self.vm1, self.vm2, self.vm3]
        stream1 = Stream(protocol="ip", proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(8000), dport=self.dport1)
        stream2 = Stream(protocol="ip", proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(11000), dport=self.dport1)
        stream3 = Stream(protocol="ip", proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(12000), dport=self.dport1)
        stream_list = [stream1, stream2, stream3]

        self.sender, self.receiver = self.start_traffic(
            self.fvn_vm1, vm_list, stream_list, self.fvn_vm1.vm_ip, self.my_fip)
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.verify_flow_records(self.fvn_vm1, self.fvn_vm1.vm_ip, self.my_fip)
        return True

    # end test_ecmp_bw_three_vms_same_fip_incr_sport

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip_incr_sip(self):
        """
        Description: Test communication between three VMs who have borrowed the FIP from common FIP
             pool. Increment SIP and have 3 flows setup.
        Test steps:
                   1.  Test communication between three VMs who have borrowed the FIP from common FIP pool.
                   2.  Sending 3 different streams with incrementing sip.
                   3.  Check the route table for the FIP address which should indicate ECMP.
        Pass criteria: Traffic should reach the other VMs from vm1.
        Maintainer : ganeshahv@juniper.net
        """
        self.setup_common_objects()
        vm_list = [self.vm1, self.vm2, self.vm3]
        stream1 = Stream(protocol="ip", proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream2 = Stream(protocol="ip", proto="udp", src=self.fvn_vm2.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream3 = Stream(protocol="ip", proto="udp", src=self.fvn_vm3.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream_list = [stream1, stream2, stream3]

        self.sender, self.receiver = self.start_traffic(
            self.fvn_vm1, vm_list, stream_list, self.fvn_vm1.vm_ip, self.my_fip)
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.verify_flow_records(self.fvn_vm1, self.fvn_vm1.vm_ip, self.my_fip)
        return True


class TestECMPwithSVMChange(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPwithSVMChange, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ecmp_with_svm_deletion(self):
        """
           Description: Validate ECMP with service chaining transparent mode datapath by removing SVMs
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Delete the SVMs in the SI one by one.
                5.There should be no traffic loss.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svms = self.get_svms_in_si(
            self.si_fixtures[0], self.inputs.project_name)
        self.logger.info('The Service VMs in the Service Instance %s are %s' % (
            self.si_fixtures[0].si_name, svms))
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm, svm.status))
        self.logger.info('Will send traffic between the VMs')
        dst_vm_list = [self.vm2_fixture]
        self.stream_list = self.setup_streams(
            self.vm1_fixture, dst_vm_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.sender, self.receiver = self.start_traffic(
            self.vm1_fixture, dst_vm_list, self.stream_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.verify_flow_thru_si(self.si_fixtures[0])
        while(len(svms) > 1):
            self.logger.info('Will reduce the SVM count to %s' %(len(svms)-1))
            si_id = self.vnc_lib.service_instances_list()['service-instances'][0]['uuid']
            si_obj = self.vnc_lib.service_instance_read(id=si_id)
            si_prop = si_obj.get_service_instance_properties()
            scale_out = my_vnc_api.ServiceScaleOutType(max_instances=(len(svms)-1))
            si_prop.set_scale_out(scale_out)
            si_obj.set_service_instance_properties(si_prop)
            self.vnc_lib.service_instance_update(si_obj)
#            svms[-1].delete()  Instead of deleting the SVMs, we will reduce the max_inst
            sleep(10)
            svms = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            svms = sorted(set(svms))
            if None in svms:
                svms.remove(None)
            self.logger.info('The Service VMs in the Service Instance %s are %s' % (
                self.si_fixtures[0].si_name, svms))
            self.verify_flow_records(
                self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
            self.verify_flow_thru_si(self.si_fixtures[0])
        return True
    # end test_ecmp_with_svm_deletion

    @preposttest_wrapper
    def test_ecmp_with_svm_suspend_start(self):
        """
           Description: Validate ECMP with service chaining transparent mode datapath by suspending and later staring SVMs
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Suspend the SVMs in the SI one by one.
                5.There should be no traffic loss.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svms = self.get_svms_in_si(
            self.si_fixtures[0], self.inputs.project_name)
        self.logger.info('The Service VMs in the Service Instance %s are %s' % (
            self.si_fixtures[0].si_name, svms))
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm, svm.status))
        self.logger.info('Will send traffic between the VMs')
        dst_vm_list = [self.vm2_fixture]
        self.stream_list = self.setup_streams(
            self.vm1_fixture, dst_vm_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.sender, self.receiver = self.start_traffic(
            self.vm1_fixture, dst_vm_list, self.stream_list, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
        self.verify_flow_thru_si(self.si_fixtures[0])

        self.logger.info(
            '****** Will suspend the SVMs and check traffic flow ******')
        for i in range(len(svms) - 1):
            self.logger.info('Will Suspend SVM %s' % svms[i].name)
            svms[i].suspend()
            sleep(30)
            self.verify_flow_records(
                self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
            self.verify_flow_thru_si(self.si_fixtures[0])

        self.logger.info(
            '****** Will resume the suspended SVMs and check traffic flow ******')
        for i in range(len(svms)):
            svms = self.get_svms_in_si(
                self.si_fixtures[0], self.inputs.project_name)
            if svms[i].status == 'SUSPENDED':
                self.logger.info(
                    'Will resume the suspended SVM %s' % svms[i].name)
                svms[i].resume()
                sleep(30)
            else:
                self.logger.info('SVM %s is not SUSPENDED' % svms[i].name)
            self.verify_flow_records(
                self.vm1_fixture, self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip)
            self.verify_flow_thru_si(self.si_fixtures[0])

        return True
    # end test_ecmp_with_svm_suspend_start


class TestMultiInlineSVC(BaseECMPTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestMultiInlineSVC, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_three_stage_SC(self):
        """
        Description: Validate multi-Inline SVC.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 3 service instances.
                         3.Creating a service chain by applying the 3 service instances in a policy between t
                    he VNs.
                         4.There should be no traffic loss.
        Pass criteria: Ping between the VMs should be successful.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_multi_inline_svc(
            si_list=[('bridge', 1), ('in-net', 1), ('nat', 1)])
        return True
    # end test_three_stage_SC

    @preposttest_wrapper
    def test_three_stage_SC_with_ECMP(self):
        """
        Description: Validate multi-Inline SVC with ECMP.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 3 service instances, with 3 SVMs in each of them.
                         3.Creating a service chain by applying the 3 service instances in a policy between t
                         he VNs.
                         4.There should be no traffic loss.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2
                   from vm1 and vice-versa.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_multi_inline_svc(
            si_list=[('bridge', 2), ('in-net', 2), ('nat', 2)])
        return True
    # end test_three_stage_SC_with_ECMP

    @preposttest_wrapper
    def test_three_stage_SC_with_traffic(self):
        """
        Description: Validate multi-Inline SVC with traffic.
        Test steps:
                    1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.Creating 3 service instances.
                    3.Creating a service chain by applying the 3 service instances in a policy between t
                he VNs.
                    4.There should be no traffic loss.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2
                 from vm1 and vice-versa.
        Maintainer : ganeshahv@juniper.net
        """
        self.verify_multi_inline_svc(
            si_list=[('in-net', 2), ('bridge', 2), ('nat', 2)])
        tap_list = []
        si_list = self.si_list
        svm_ids = self.si_fixtures[0].svm_ids
        tap_list = self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)

        return True
    # end test_three_stage_SC_with_traffic
