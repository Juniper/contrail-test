import sys
import os
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from vnc_api import vnc_api as my_vnc_api
from nova_test import *
from vm_test import *
from tcutils.util import skip_because
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.ecmp.base import ECMPTestBase
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from common.ecmp.ecmp_test_resource import ECMPSolnSetup
from common.base import GenericTestBase
import test



class TestECMPSanity(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPSanity, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestECMPSanity, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_ecmp_svc_v2_transparent_with_3_instance(self):
        """
           Description: Validate ECMP with version 2 service chaining transparent mode datapath having service instance
           Test steps:
                1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                2.Creating a service instance in transparent mode with 3 instances.
                3.Creating a service chain by applying the service instance as a service in a policy between the VNs.
                4.Checking for ping and bidirectional tcp traffic between vm1 and vm2.
           Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1 and vice-versa.
           Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_chain(max_inst=2,
                              service_mode='transparent',
                              create_svms=True,
                              **self.common_args)
    # end test_ecmp_svc_v2_transparent_with_3_instance

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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)
        dst_vm_list = [self.right_vm_fixture]
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, si_fixture,
            self.left_vn_fixture)
    # end test_ecmp_svc_in_network_with_3_instance

    @test.attr(type=['sanity','vcenter'])
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
        static_route = None
        if self.inputs.get_af() == 'v6':
            static_route = {'management': None,
                            'left': self.right_vn_subnets[0],
                            'right': self.left_vn_subnets[0] }

        if not static_route:
            static_route = {'management': None,
                            'left': self.right_vn_subnets[0],
                            'right': self.left_vn_subnets[0]}
        ret_dict = self.verify_svc_chain(max_inst=1,
                              service_mode='in-network',
                              create_svms=True,
                              static_route=static_route,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)
        dst_vm_list = [self.right_vm_fixture]
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, si_fixture,
            self.left_vn_fixture)
        self.logger.info(
            '%%%%% Will Detach the policy from the networks and delete it %%%%%')
        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])
        self.unconfig_policy(ret_dict['policy_fixture'])
        self.sleep(30)
        self.logger.info(
            '%%%%% Ping and traffic between the networks should go thru fine because of the static route configuration %%%%%')
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip)
    # end test_ecmp_svc_in_network_with_static_route_no_policy


class TestECMPFeature(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPFeature, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPFeature, cls).tearDownClass()
    # end tearDownClass

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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='transparent',
                              create_svms=True,
                              proto='tcp',
                              **self.common_args)
        self.left_vm_fixture.put_pub_key_to_vm()
        self.right_vm_fixture.put_pub_key_to_vm()
        # TFTP from Left VM to Right VM is expected to fail
        errmsg1 = "TFTP to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='tftp', size='333', expectation=False), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to pass
        errmsg2 = "SCP to right VM ip %s from left VM failed; expected to pass" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='scp', size='444'), errmsg2
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='transparent',
                              create_svms=True,
                              proto='tcp',
                              **self.common_args)
        self.left_vm_fixture.put_pub_key_to_vm()
        self.right_vm_fixture.put_pub_key_to_vm()
        # TFTP from Left VM to Right VM is expected to fail
        errmsg1 = "TFTP to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='tftp', size='111', expectation=False), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to pass
        errmsg2 = "SCP to right VM ip %s from left VM failed; expected to pass" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='scp', size='222'), errmsg2
        self.logger.info('Will update the policy to allow only udp')
        policy_fixture = ret_dict['policy_fixture']
        old_data = {
            'policy': {'entries': policy_fixture.policy_obj['policy']['entries']}}
        old_entry = policy_fixture.policy_obj['policy']['entries']
        new_entry = old_entry
        new_entry['policy_rule'][0]['protocol'] = u'udp'
        pol_id = policy_fixture.policy_obj['policy']['id']
        new_data = {'policy': {'entries': new_entry}}
        policy_fixture.update_policy(pol_id, new_data)
        self.sleep(5)
        # TFTP from Left VM to Right VM is expected to pass
        errmsg1 = "TFTP to right VM ip %s from left VM failed; expected to pass" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='tftp', size='101'), errmsg1
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip, expectation=False), errmsg
        # SCP from Left VM to Right VM is expected to fail
        errmsg2 = "SCP to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.check_file_transfer(
            dest_vm_fixture=self.right_vm_fixture, mode='scp', size='202', expectation=False), errmsg2
    # end test_ecmp_in_pol_based_svc_pol_update

    @test.attr(type=['cb_sanity', 'sanity','vcenter'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_ecmp_svc_v2_in_network_nat_with_3_instance(self):
        """
         Description: Validate ECMP with v2 service chaining in-network-nat mode datapath having service instance
         Test steps:
           1.	Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.	Creating a service instance in in-network-nat mode with 3 instances and
                left-interface of the service instances sharing the IP and enabled for static route.

           3.	Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.	Checking for ping and tcp traffic between vm1 and vm2.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
         Maintainer : ganeshahv@juniper.net
        """
        self.verify_svc_chain(max_inst=2,
                              service_mode='in-network-nat',
                              create_svms=True,
                              **self.common_args)
    # end test_ecmp_svc_v2_in_network_nat_with_3_instance


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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture, svm_ids,
            si_fixture)
        vm_list = [self.left_vm_fixture, self.right_vm_fixture]
        for vm in vm_list:
            vm.install_pkg("Traffic")
        old_stream1 = Stream(
            proto="icmp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        old_stream2 = Stream(
            proto="udp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        old_stream3 = Stream(
            proto="tcp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(10000), dport=unicode(11000))
        old_stream_list = [old_stream1, old_stream2, old_stream3]

        dst_vm_list = [self.right_vm_fixture]
        old_sender, old_receiver = self.start_traffic(
            self.left_vm_fixture, dst_vm_list, old_stream_list,
            self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        self.logger.info(
            'Sending traffic for 10 seconds and will start more flows')
        self.sleep(10)
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, si_fixture, self.left_vn_fixture)
        self.verify_flow_records(
            self.left_vm_fixture, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        self.stop_traffic(
            old_sender, old_receiver, dst_vm_list, old_stream_list)
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture, svm_ids,
            si_fixture)
        vm_list = [self.left_vm_fixture, self.right_vm_fixture]
        for vm in vm_list:
            vm.install_pkg("Traffic")

        stream1 = Stream(
            proto="icmp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream2 = Stream(
            proto="udp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream3 = Stream(
            proto="tcp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream_list = [stream1, stream2, stream3]

        dst_vm_list = [self.right_vm_fixture]
        sender, receiver = self.start_traffic(
            self.left_vm_fixture, dst_vm_list, stream_list,
            self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)

        self.logger.info('Sending traffic for 10 seconds')
        self.sleep(10)

        #Verify flow records for each stream
        #Need to do ICMP flow verification
        for protocol in ['6', '17']:
          self.verify_flow_records(
            self.left_vm_fixture, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip, flow_count=1, protocol=protocol)

        self.stop_traffic(
            sender, receiver, dst_vm_list, stream_list)
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)
        dest_vm2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.right_vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='dest_vm2'))
        assert dest_vm2.verify_on_setup()
        dest_vm3 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.right_vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='dest_vm3'))
        assert dest_vm3.verify_on_setup()
        vm_list = [self.left_vm_fixture, self.right_vm_fixture, dest_vm2, dest_vm3]
        for vm in vm_list:
            vm.install_pkg("Traffic")

        stream1 = Stream(
            proto="udp", src=self.left_vm_fixture.vm_ip,
            dst=self.right_vm_fixture.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream2 = Stream(
            proto="udp", src=self.left_vm_fixture.vm_ip,
            dst=dest_vm2.vm_ip, sport=unicode(8000), dport=unicode(9000))
        stream3 = Stream(
            proto="udp", src=self.left_vm_fixture.vm_ip,
            dst=dest_vm3.vm_ip, sport=unicode(8000), dport=unicode(9000))

        stream_list = [stream1, stream2, stream3]

        dst_vm_list = [self.right_vm_fixture]
        sender, receiver = self.start_traffic(self.left_vm_fixture, dst_vm_list, stream_list,
                               self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        self.sleep(1)
        for dst_ip in [self.right_vm_fixture.vm_ip, dest_vm2.vm_ip, dest_vm3.vm_ip]:
          self.verify_flow_records(
            self.left_vm_fixture, self.left_vm_fixture.vm_ip, dst_ip, flow_count=1)
        self.stop_traffic(
            sender, receiver, dst_vm_list, stream_list)
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture, svm_ids, si_fixture)
        dst_vm_list = [self.right_vm_fixture]
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, si_fixture, self.left_vn_fixture)
        self.logger.info(
            'Will Detach the policy from the networks and delete it')
        self.detach_policy(ret_dict['left_vn_policy_fix'])
        self.detach_policy(ret_dict['right_vn_policy_fix'])
        self.sleep(30)
        self.logger.info('Traffic between the VMs should fail now')
        # Ping from left VM to right VM; expected to fail
        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip, expectation=False), errmsg

        self.logger.info(
            'Will Re-Configure the policy and attach it to the networks')
        self.attach_policy_to_vn(ret_dict['policy_fixture'], self.left_vn_fixture)
        self.attach_policy_to_vn(ret_dict['policy_fixture'], self.right_vn_fixture)
        self.sleep(30)
        self.logger.info('Traffic between the VMs should pass now')
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, si_fixture, self.left_vn_fixture)
    # end test_ecmp_svc_in_network_with_policy_bind_unbind


class TestECMPwithFIP_1(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPwithFIP_1, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPwithFIP_1, cls).tearDownClass()
    # end tearDownClass

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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        self.logger.info('.' * 80)
        self.logger.info(
            'We will create 3 VMs at the destination and make them share the same FIP address')
        self.logger.info('.' * 80)
        my_fip_name = 'fip'
        my_fip = self.get_random_fip(self.left_vn_fixture)

        vm2_1 = self.create_vm(vn_fixture=self.right_vn_fixture,
                               vm_name='vm2_1')
        vm2_2 = self.create_vm(vn_fixture=self.right_vn_fixture,
                               vm_name='vm2_2')
        assert vm2_1.verify_on_setup()
        assert vm2_2.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name='some-pool1', vn_id=self.left_vn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        fvn_obj = self.vnc_lib.virtual_network_read(
            id=self.left_vn_fixture.vn_id)
        fip_pool_obj = FloatingIpPool('some-pool1', fvn_obj)
        fip_obj = FloatingIp('fip', fip_pool_obj, my_fip, True)

        # Get the project_fixture
        project_fixture = self.useFixture(ProjectFixture(
            project_name=self.inputs.project_name, connections=self.connections))
        # Read the project obj and set to the floating ip object.
        fip_obj.set_project(project_fixture.project_obj)

        vn2_fq_name = self.right_vn_fixture.vn_fq_name
        vn2_vrf_name = self.right_vn_fixture.vrf_name
        vn2_ri_name = self.right_vn_fixture.ri_name
        vmi1_id = self.right_vm_fixture.tap_intf[
            self.right_vn_fixture.vn_fq_name]['uuid']
        vmi2_id = vm2_1.tap_intf[
            self.right_vn_fixture.vn_fq_name]['uuid']
        vmi3_id = vm2_2.tap_intf[
            self.right_vn_fixture.vn_fq_name]['uuid']
        vm2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=vmi1_id)
        vm2_1_intf = self.vnc_lib.virtual_machine_interface_read(
            id=vmi2_id)
        vm2_2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=vmi3_id)
        for intf in [vm2_intf, vm2_1_intf, vm2_2_intf]:
            fip_obj.add_virtual_machine_interface(intf)
        self.vnc_lib.floating_ip_create(fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, fip_obj.fq_name)
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)
        self.left_vm_fixture.ping_with_certainty(my_fip)
    # end test_ecmp_with_svc_with_fip_dest

class TestECMPwithFIP_2(GenericTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPwithFIP_2, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPwithFIP_2, cls).tearDownClass()
    # end tearDownClass

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
        stream1 = Stream(proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(8000), dport=self.dport1)
        stream2 = Stream(proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(11000), dport=self.dport1)
        stream3 = Stream(proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=unicode(12000), dport=self.dport1)
        stream_list = [stream1, stream2, stream3]

        self.sender, self.receiver = self.start_traffic(
            self.fvn_vm1, vm_list, stream_list, self.fvn_vm1.vm_ip, self.my_fip)
        self.logger.info('Sending traffic for 10 seconds')
        self.sleep(10)
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
        stream1 = Stream(proto="udp", src=self.fvn_vm1.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream2 = Stream(proto="udp", src=self.fvn_vm2.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream3 = Stream(proto="udp", src=self.fvn_vm3.vm_ip,
                         dst=self.my_fip, sport=self.udp_src, dport=self.dport1)
        stream_list = [stream1, stream2, stream3]

        self.sender, self.receiver = self.start_traffic(
            self.fvn_vm1, vm_list, stream_list, self.fvn_vm1.vm_ip, self.my_fip)
        self.logger.info('Sending traffic for 10 seconds')
        self.sleep(10)
        self.verify_flow_records(self.fvn_vm1, self.fvn_vm1.vm_ip, self.my_fip)
        return True


class TestECMPwithSVMChange(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPwithSVMChange, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPwithSVMChange, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='in-network',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svms = self.get_svms_in_si(si_fixture)
        self.logger.info('The Service VMs in the Service Instance %s are %s' % (
            si_fixture.si_name, svms))
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm, svm.status))
        self.logger.info('Will send traffic between the VMs')
        dst_vm_list = [self.right_vm_fixture]
        stream_list = self.setup_streams(
            self.left_vm_fixture, dst_vm_list, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        sender, receiver = self.start_traffic(
            self.left_vm_fixture, dst_vm_list, stream_list,
            self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        self.verify_flow_thru_si(si_fixture, self.left_vn_fixture)
        while(len(svms) > 1):
            old_count = len(svms)
            self.logger.info(
                'Will reduce the SVM count from %s to %s' % (old_count, len(svms) - 1))
            to_be_deleted_svm = ret_dict['svm_fixtures'][len(svms) - 1]
            to_be_deleted_svm.cleanUp()
            self.remove_from_cleanups(to_be_deleted_svm.cleanUp)
            to_be_deleted_svm.verify_cleared_from_setup(verify=True)
            for svm in svms:
                if svm.id == to_be_deleted_svm.vm_id:
                    svms.remove(svm)
            svms = self.get_svms_in_si(si_fixture)
            svms = sorted(set(svms))
            new_count = len(svms)
            errmsg = 'The SVMs count has not decreased'
            assert new_count < old_count, errmsg
            self.logger.info('The Service VMs in the Service Instance %s are %s' % (
                si_fixture.si_name, svms))
            svm_ids = []
            for svm in svms:
                svm_ids.append(svm.id)
            self.get_rt_info_tap_intf_list(
                self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
                svm_ids, si_fixture)
            self.verify_flow_records(
                self.left_vm_fixture, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
            self.verify_flow_thru_si(si_fixture, self.left_vn_fixture)
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
        ret_dict = self.verify_svc_chain(max_inst=3,
                              service_mode='transparent',
                              create_svms=True,
                              **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svms = self.get_svms_in_si(si_fixture)
        self.logger.info('The Service VMs in the Service Instance %s are %s' % (
            si_fixture.si_name, svms))
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm, svm.status))
        self.logger.info('Will send traffic between the VMs')
        dst_vm_list = [self.right_vm_fixture]
        stream_list = self.setup_streams(
            self.left_vm_fixture, dst_vm_list, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        sender, receiver = self.start_traffic(
            self.left_vm_fixture, dst_vm_list, stream_list, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
        self.verify_flow_thru_si(si_fixture)

        self.logger.info(
            '%%%%%% Will suspend the SVMs and check traffic flow %%%%%%')
        for i in range(len(svms) - 1):
            self.logger.info('Will Suspend SVM %s' % svms[i].name)
            svms[i].suspend()
            sleep(30)
            self.verify_flow_records(
                self.left_vm_fixture, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
            self.verify_flow_thru_si(si_fixture)

        self.logger.info(
            '%%%%%% Will resume the suspended SVMs and check traffic flow %%%%%%')
        for i in range(len(svms)):
            svms = self.get_svms_in_si(si_fixture)
            if svms[i].status == 'SUSPENDED':
                self.logger.info(
                    'Will resume the suspended SVM %s' % svms[i].name)
                svms[i].resume()
                self.sleep(30)
            else:
                self.logger.info('SVM %s is not SUSPENDED' % svms[i].name)
            self.verify_flow_records(
                self.left_vm_fixture, self.left_vm_fixture.vm_ip, self.right_vm_fixture.vm_ip)
            self.verify_flow_thru_si(si_fixture)

    # end test_ecmp_with_svm_suspend_start


class TestMultiInlineSVC(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestMultiInlineSVC, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMultiInlineSVC, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic(self):
        """
        Description: Basic test to validate fate sharing in a multi inline service chain with 2 SIs, 1 SVM each.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 inline service instances SI1 and SI2.
                         3.Creating a service chain by applying the 2 service instances in a policy between t
                    he VNs.
                         4.Associate an HC instance with right intf of one of the SVMs
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs
                         7.Verify the step 6 in both control node and agent
                         8.Bring up the intf in the step 5
                         8.Verify that the routes should be re-originated again, and the traffic also starts flowing

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'in-network'},
                        { 'service_mode' : 'in-network'}]
        else:
            si_list = [ { 'service_mode' : 'in-network'},
                        { 'service_mode' : 'in-network'} ]
        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, create_svms=True, hc={'si_index':0, 'si_intf_type':'right'},
                                     **self.common_args)
    # end test_svc_fate_sharing_basic

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic_with_transparent(self):
        """
        Description: Validate fate sharing in a multi inline service chain with 2 SIs, 1 SVM each and segment based hc.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 inline service instances.
                         3.Creating a service chain by applying the 2 service instances transparent and in-net in a policy between t
                    he VNs.
                         4.Associate an Segment based HC instance with right intf of one of the SVMs
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs
                         7.Verify the step 6 in both control node and agent
                         8.Bring up the intf in the step 5
                         8.Verify that the routes should be re-originated again, and the traffic also starts flowing

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'transparent'},
                        { 'service_mode' : 'in-network'}]
        else:
            si_list = [ { 'service_mode' : 'transparent'},
                        { 'service_mode' : 'in-network'} ]

        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, create_svms=True, hc={'si_index':0, 'si_intf_type':'right', 'hc_type':'segment'},
                                     **self.common_args)
    # end test_svc_fate_sharing_basic_with_transparent

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic_with_transparent_in_net_nat(self):
        """
        Description: Validate fate sharing in a multi inline service chain with 2 SIs, 1 SVM each  with in-network-nat.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 inline service instances.
                         3.Creating a service chain by applying the 2 service instances transparent and in-network-nat in a policy between t
                    he VNs.
                         4.Associate an Segment based HC instance with right intf of one of the SVMs
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs
                         7.Verify the step 6 in both control node and agent
                         8.Bring up the intf in the step 5
                         8.Verify that the routes should be re-originated again, and the traffic also starts flowing

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'transparent'},
                        { 'service_mode' : 'in-network-nat'}]
        else:
            si_list = [ { 'service_mode' : 'transparent'},
                        { 'service_mode' : 'in-network-nat'} ]

        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, create_svms=True, hc={'si_index':1, 'si_intf_type':'left'},
                                     **self.common_args)
    # end test_svc_fate_sharing_basic_with_in_network_net

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_in_net_in_net(self):
        """
        Description: Validate fate sharing in 2 multi inline service chains with 2 SIs, 1 SVM each.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 multi inline service chains Svc0, Svc1 with 2 SIs, 1 SVM each
                         3 Apply the service instances of svc chain 0 in a policy p1 allowing icmp traffic
                         4. Apply the service instances of svc chain 1 in a policy p2 allowing tcp traffic
                         4.Associate an HC instance with right intf of one of the SVMs of the first svc chain 0
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs of
                           the first svc chain.
                         7.Verify the step 6 in both control node and agent
                         8. Check that tcp traffic still flows from vm1 to vm2 ; Verify that the traffic continues to flow through svc chain 1
                         9. Check that icmp does not work from vm1 to vm2 ; Verify that the traffic stops flowing through svc chain 0
                         9.Bring up the intf in the step 5
                         10.Verify that the routes get re-originated again, and the traffic is still flowing through one of the svc chains

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        else:
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network','max_inst':1} ]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        self.common_args['proto'] = 'icmp' #icmp for svc chain0, tcp for svc chain 1
        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, si_list1=si_list1, create_svms=True, hc={'si_index':0, 'si_intf_type':'right'},
                                     **self.common_args)
    # test_svc_fate_sharing_in_2_multi_inline_svc_chains_in_net_in_net

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_transparent(self):
        """
        Description: Validate fate sharing in 2 multi inline service chains with 2 SIs, 1 SVM each and segment based HC.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 multi inline service chains Svc0, Svc1 with 2 SIs, 1 SVM each
                         3 Apply the service instances of svc chain 0 in a policy p1 allowing icmp traffic
                         4. Apply the service instances of svc chain 1 in a policy p2 allowing tcp traffic
                         4.Associate an HC instance with right intf of one of the SVMs of the first svc chain 0
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs of
                           the first svc chain.
                         7.Verify the step 6 in both control node and agent
                         8. Check that tcp traffic still flows from vm1 to vm2 ; Verify that the traffic continues to flow through svc chain 1
                         9. Check that icmp does not work from vm1 to vm2 ; Verify that the traffic stops flowing through svc chain 0
                         9.Bring up the intf in the step 5
                         10.Verify that the routes get re-originated again, and the traffic is still flowing through one of the svc chains

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'transparent', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'transparent' ,'max_inst':1}]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        else:
            si_list = [ { 'service_mode' : 'transparent', 'max_inst':1},
                        { 'service_mode' : 'in-network','max_inst':1},
                        { 'service_mode' : 'transparent' ,'max_inst':1} ]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        self.common_args['proto'] = 'icmp' #icmp for svc chain0, tcp for svc chain 1
        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, si_list1=si_list1, create_svms=True, hc={'si_index':2, 'si_intf_type':'left', 'hc_type':'segment'},
                                     **self.common_args)
    # end test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_transparent

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_in_net_nat(self):
        """
        Description: Validate fate sharing in 2 multi inline service chains with 2 SIs, 1 SVM each.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 multi inline service chains Svc0, Svc1 with 2 SIs, 1 SVM each with transparent, in-network and in-network-nat
                         3 Apply the service instances of svc chain 0 in a policy p1 allowing icmp traffic
                         4. Apply the service instances of svc chain 1 in a policy p2 allowing tcp traffic
                         4.Associate an HC instance with right intf of one of the SVMs of the first svc chain 0
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are deleted from all the RIs of all the SIs of
                           the first svc chain.
                         7.Verify the step 6 in both control node and agent
                         8. Check that tcp traffic still flows from vm1 to vm2 ; Verify that the traffic continues to flow through svc chain 1
                         9. Check that icmp does not work from vm1 to vm2 ; Verify that the traffic stops flowing through svc chain 0
                         9.Bring up the intf in the step 5
                         10.Verify that the routes get re-originated again, and the traffic is still flowing through one of the svc chains

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'transparent', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network-nat', 'max_inst':1}]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        else:
            si_list = [ { 'service_mode' : 'transparent', 'max_inst':1},
                        { 'service_mode' : 'in-network','max_inst':1},
                        { 'service_mode' : 'in-network-nat' ,'max_inst':1} ]
            si_list1 = [ { 'service_mode' : 'in-network', 'max_inst':1},
                        { 'service_mode' : 'in-network', 'max_inst':1}]
        self.common_args['proto'] = 'icmp' #icmp for svc chain0, tcp for svc chain 1
        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, si_list1=si_list1, create_svms=True, hc={'si_index':0, 'si_intf_type':'right', 'hc_type':'segment'},
                                     **self.common_args)
    # end test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_in_net_nat

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic_with_multiple_svm_instances(self):
        """
        Description: Validate fate sharing in a multi inline service chain with 2 SIs, 2 SVMs each.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 inline service instances with 2 SVMs each.
                         3.Creating a service chain by applying the 2 service instances in a policy between t
                    he VNs.
                         4.Associate an HC instance with right intf of one of the SVMs
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are not deleted from any the RIs of all the SIs
                         7.Verify the step 6 in both control node and agent
                         8.Verify that the traffic is still flowing through the svc as just one svm is down
                         9.Bring up the intf in the step 5; Expect the HC to come up
                         10.Verify that there should not be any impact, and the traffic continues to flow

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """

        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':2},
                        { 'service_mode' : 'in-network', 'max_inst':2}]
        else:
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':2},
                        { 'service_mode' : 'in-network', 'max_inst':2} ]

        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, create_svms=True, hc={'si_index':0, 'si_intf_type':'right'},
                                     **self.common_args)
    # end test_svc_fate_sharing_basic_with_multiple_svm_instances

    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_svc_fate_sharing_basic_with_3_svm_instances(self):

        """
        Description: Validate fate sharing in a multi inline service chain with 2 SIs, 3 SVMs each.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 2 inline service instances with 3 SVMs each.
                         3.Creating a service chain by applying the 2 service instances in a policy between t
                    he VNs.
                         4.Associate an HC instance with right intf of one of the SVMs
                         5.Bring down the intf in the step 4
                         6.Verify that all the re-origined routes(ServiceChain) are not deleted from any the RIs of all the SIs
                         7.Verify the step 6 in both control node and agent
                         8.Verify that the traffic is still flowing through the svc as just one svm is down
                         9.Bring up the intf in the step 5; Expect the HC to come up
                         10.Verify that there should not be any impact, and the traffic continues to flow

        Pass criteria: Ping/Route deletion/Route addition should be successful.
        Maintainer : ankitja@juniper.net
        """

        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':3},
                        { 'service_mode' : 'in-network', 'max_inst':3}]
        else:
            si_list = [ { 'service_mode' : 'in-network', 'max_inst':3},
                        { 'service_mode' : 'in-network', 'max_inst':3} ]

        self.verify_multi_inline_svc_with_fate_share(si_list=si_list, create_svms=True, hc={'si_index':0, 'si_intf_type':'right'},
                                     **self.common_args)

    # end test_svc_fate_sharing_basic_with_3_svm_instances

    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_three_stage_v2_SC(self):
        """
        Description: Validate multi-Inline SVC version 2.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                         2.Creating 3 service instances.
                         3.Creating a service chain by applying the 3 service instances in a policy between t
                    he VNs.
                         4.There should be no traffic loss.
        Pass criteria: Ping between the VMs should be successful.
        Maintainer : ganeshahv@juniper.net
        """
        if self.inputs.orchestrator == 'vcenter':
            si_list = [ { 'service_mode' : 'in-network'},
                        { 'service_mode' : 'in-network-nat'}]
        else:
            si_list = [ { 'service_mode' : 'transparent'},
                        { 'service_mode' : 'in-network-nat'} ]
        self.verify_multi_inline_svc(si_list=si_list, create_svms=True,
                                     **self.common_args)
    # end test_three_stage_v2_SC

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
        si_list = [ { 'service_mode' : 'transparent', 'max_inst' : 2 },
                    { 'service_mode' : 'in-network',  'max_inst' : 2 },
                    { 'service_mode' : 'in-network-nat',  'max_inst' : 2 } ]
        if self.inputs.get_af() == 'v6':
            si_list = [ { 'service_mode' : 'transparent', 'max_inst' : 2 },
                        { 'service_mode' : 'in-network',  'max_inst' : 2 }]
        self.verify_multi_inline_svc(si_list=si_list, create_svms=True,
                                     **self.common_args)
    # end test_three_stage_SC_with_ECMP

    @preposttest_wrapper
    def test_multi_inline_SVC_VN_with_external_RT(self):
        """
        Description: Validate multi-Inline SVC with ECMP.
        Bug: 1436642
        The Right VN and the left VN have external RTs configured.
        The traffic between left and right VMs should go through the Service Chain.
        Test steps:
                         1.Creating vm's - vm1 and vm2 in networks vn1 and vn2. Configure RT on the 2 VNs.
                         2.Creating a multi-stage service chain with in-network SIs, between the VNs.
                         3.There should be no traffic loss.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2
                   from vm1 and vice-versa.
        Maintainer : ganeshahv@juniper.net
        """
        si_list = [{'service_mode': 'in-network', 'max_inst': 1},
                   {'service_mode': 'in-network',  'max_inst': 1}]
        ret_dict = self.verify_multi_inline_svc(si_list=si_list, create_svms=True,
                                                **self.common_args)
        si_fixtures = ret_dict['si_fixtures']
        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fq_name = left_vn_fixture.vn_fq_name
        right_vn_fq_name = right_vn_fixture.vn_fq_name
        self.logger.info('Adding User-defined RT to the end VNs')
        right_vn_fixture.add_route_target(router_asn=random.randint(
            1000, 2000), route_target_number=random.randint(9000000, 9500000))
        left_vn_fixture.add_route_target(router_asn=random.randint(
            2000, 3000), route_target_number=random.randint(8500000, 9000000))
        result, msg = self.validate_svc_action(
            left_vn_fq_name, si_fixtures[0], right_vm_fixture, src='left')
        result, msg = self.validate_svc_action(
            right_vn_fq_name, si_fixtures[-1], left_vm_fixture, src='right')
        assert left_vm_fixture.ping_with_certainty(right_vm_fixture.vm_ip)
        assert right_vm_fixture.ping_with_certainty(left_vm_fixture.vm_ip)

    # end test_multi_inline_SVC_VN_with_external_RT

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
        si_list = [ { 'service_mode' : 'transparent', 'max_inst' : 2 },
                    { 'service_mode' : 'in-network',  'max_inst' : 2 },
                    { 'service_mode' : 'in-network-nat',  'max_inst' : 2 } ]
        if self.inputs.get_af() == 'v6':
            si_list = [ { 'service_mode' : 'transparent', 'max_inst' : 2 },
                        { 'service_mode' : 'in-network',  'max_inst' : 2 }]
        ret_dict = self.verify_multi_inline_svc(si_list=si_list, create_svms=True,
                                     **self.common_args)
        last_si_fixture = ret_dict['si_fixtures'][-1]
        svm_ids = last_si_fixture.svm_ids
        dst_vm_list = [self.right_vm_fixture]
        self.verify_traffic_flow(
            self.left_vm_fixture, dst_vm_list, last_si_fixture,
            self.left_vn_fixture)

    # end test_three_stage_SC_with_traffic

class TestECMPSanityIPv6(TestECMPSanity):

    @classmethod
    def setUpClass(cls):
        cls.set_af('v6')
        super(TestECMPSanityIPv6, cls).setUpClass()

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @preposttest_wrapper
    def test_ecmp_svc_v2_transparent_with_3_instance(self):
        super(TestECMPSanityIPv6,self).test_ecmp_svc_v2_transparent_with_3_instance()

    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_ecmp_svc_in_network_with_3_instance(self):
        super(TestECMPSanityIPv6,self).test_ecmp_svc_in_network_with_3_instance()

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_static_route_no_policy(self):
        super(TestECMPSanityIPv6,self).test_ecmp_svc_in_network_with_static_route_no_policy()

class TestECMPFeatureIPv6(TestECMPFeature):

    @classmethod
    def setUpClass(cls):
        cls.set_af('v6')
        super(TestECMPFeatureIPv6, cls).setUpClass()

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @preposttest_wrapper
    def test_ecmp_svc_v2_in_network_nat_with_3_instance(self):
        super(TestECMPFeatureIPv6,self).test_ecmp_svc_v2_in_network_nat_with_3_instance()

class TestECMPwithSVMChangeIPv6(TestECMPwithSVMChange):

    @classmethod
    def setUpClass(cls):
        cls.set_af('v6')
        super(TestECMPwithSVMChangeIPv6, cls).setUpClass()

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @preposttest_wrapper
    def test_ecmp_with_svm_deletion(self):
        super(TestECMPwithSVMChangeIPv6,self).test_ecmp_with_svm_deletion()

class TestMultiInlineSVCIPv6(TestMultiInlineSVC):

    @classmethod
    def setUpClass(cls):
        cls.set_af('v6')
        super(TestMultiInlineSVCIPv6, cls).setUpClass()

    def is_test_applicable(self):
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)


    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    def test_svc_fate_sharing_basic(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_basic()


    @preposttest_wrapper
    def test_svc_fate_sharing_basic_with_transparent(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_basic_with_transparent()


    @preposttest_wrapper
    def test_svc_fate_sharing_basic_with_transparent_in_net_nat(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_basic_with_transparent_in_net_nat()

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_in_net_in_net(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_in_2_multi_inline_svc_chains_in_net_in_net()

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic_with_multiple_svm_instances(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_basic_with_multiple_svm_instances()

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_basic_with_3_svm_instances(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_basic_with_3_svm_instances()


    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_in_net_nat(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_in_net_nat()

    @preposttest_wrapper
    @skip_because(min_nodes=2)
    def test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_transparent(self):
        super(TestMultiInlineSVCIPv6,self).test_svc_fate_sharing_in_2_multi_inline_svc_chains_transparent_in_net_transparent()


    @preposttest_wrapper
    def test_three_stage_v2_SC(self):
        super(TestMultiInlineSVCIPv6,self).test_three_stage_v2_SC()

class TestECMPConfigHashFeature(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPConfigHashFeature, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPConfigHashFeature, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity','vcenter'])
    @preposttest_wrapper
    @skip_because(min_nodes=3)
    def test_ecmp_hash_src_ip(self):
        """
            Validates ecmp hash when only source ip is configured
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"

        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hash with only "source_ip"
        ecmp_hash = {"source_ip": True}
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        si_fixture = ret_dict['si_fixture']
        dst_vm_list = [right_vm_fixture]
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
        return True
    # end test_ecmp_hash_src_ip

    def test_ecmp_hash_dest_ip(self):
        """
            Validates ecmp hash when only destination ip is configured
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"

        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hash with only "destination_ip"
        ecmp_hash = {"destination_ip": True}
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        si_fixture = ret_dict['si_fixture']
        dst_vm_list = [right_vm_fixture]
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
        return True
    # end test_ecmp_hash_dest_ip

    def test_ecmp_hash_src_port(self):
        """
            Validates ecmp hash when only source port is configured
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"

        # Distribute End VMs and service VMs across compute nodes
        vm_launch_mode = "distribute"
        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hash with only "source_port"
        ecmp_hash = {"source_port": True}
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        dst_vm_list = [right_vm_fixture]
        si_fixture = ret_dict['si_fixture']
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
        return True
    # end test_ecmp_hash_src_port

    def test_ecmp_hash_dest_port(self):
        """
            Validates ecmp hash when only destination port is configured
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"

        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hash with only "destionation_port"
        ecmp_hash = {"destination_port": True}
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)
        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        dst_vm_list = [right_vm_fixture]
        si_fixture = ret_dict['si_fixture']
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
    # end test_ecmp_hash_dest_port

    def test_ecmp_hash_protocol(self):
        """
            Validates ecmp hash when only ip protocol is configured
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"
        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hash with only "ip_protocol"
        ecmp_hash = {"ip_protocol": True}
        config_level = "vn"

        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)
        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        si_fixture = ret_dict['si_fixture']
        dst_vm_list = [right_vm_fixture]
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
        return True
    # end test_ecmp_hash_protocol

    def test_ecmp_hash_precedence(self):
        """
            Validates ecmp hash config precedence levels
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"
        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # Default ECMP Hash config at Global level
        ecmp_hash = "default"
        config_level = "global"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Default ECMP Hash config at VN level
        ecmp_hash = "default"
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # "destination_ip" only ECMP Hash config at VMI level. VMI should take
        # priority over VN and Global
        ecmp_hash = {"destination_ip": True}
        config_level = "vmi"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        si_fixture = ret_dict['si_fixture']
        dst_vm_list = [right_vm_fixture]
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)

        # Delete the ECMP Hash config at Global, VN and VMI level
        ecmp_hash = "None"
        config_level = "all"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)


        return True
    # end test_ecmp_hash_precedence

    def test_ecmp_hash_deletion(self):
        """
            Validates deletion of ecmp hash configuration. When explicit ecmp hash
            is deleted, hashing should happen based upon default hash (5 tuple)
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 2
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"
        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # Explicitly delete the ECMP Hashing config
        ecmp_hash = 'None'
        config_level = "all"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # When explicit ecmp hash config is deleted, default hash should takes
        # place. Verifying whether flows are distributed as per default hash or
        # not
        ecmp_hash = {"source_ip": True, "destination_ip": True,
                     "source_port": True, "destination_port": True,
                     "ip_protocol": True}

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        si_fixture = ret_dict['si_fixture']
        dst_vm_list = [right_vm_fixture]
        self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                 si_fixture, left_vn_fixture,
                                 ecmp_hash=ecmp_hash, flow_count=flow_count)
        return True
    # end test_ecmp_hash_deletion

    def test_ecmp_hash_vm_suspend_restart(self):
        """
            Validates deletion and addition of VMs with ecmp hash configuration.
            Maintainer : cmallam@juniper.net
        """
        # Bringing up the basic service chain setup.
        max_inst = 3
        service_mode = 'in-network-nat'
        ecmp_hash = 'default'
        config_level = "vn"
        ret_dict = self.setup_ecmp_config_hash_svc(max_inst=max_inst,
                                                   service_mode=service_mode,
                                                   ecmp_hash=ecmp_hash,
                                                   config_level=config_level)

        left_vn_fixture = ret_dict['left_vn_fixture']
        right_vn_fixture = ret_dict['right_vn_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']

        # ECMP Hashing config with 'destination_ip' and at VN level
        ecmp_hash = {"destination_ip": True}
        config_level = "vn"
        self.modify_ecmp_config_hash(ecmp_hash=ecmp_hash,
                                     config_level=config_level,
                                     right_vm_fixture=right_vm_fixture,
                                     right_vn_fixture=right_vn_fixture)

        # Verify ECMP Hash at Agent and control node
        self.verify_ecmp_hash(ecmp_hash=ecmp_hash, vn_fixture=left_vn_fixture,
                              left_vm_fixture=left_vm_fixture,
                              right_vm_fixture=right_vm_fixture)

        si_fixture = ret_dict['si_fixture']
        svms = self.get_svms_in_si(si_fixture)
        self.logger.info('The Service VMs in the Service Instance %s are %s'% (si_fixture.si_name, svms))
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm, svm.status))
        self.logger.info('%% Will suspend the SVMs and check traffic flow %%')

        # Verify traffic from vn1 (left) to vn2 (right), with user specified
        # flow count
        flow_count = 5
        dst_vm_list = [right_vm_fixture]
        for i in range(len(svms) - 1):
            self.logger.info('Will Suspend SVM %s' % svms[i].name)
            svms[i].suspend()
            sleep(30)
            self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                     si_fixture, left_vn_fixture,
                                     ecmp_hash=ecmp_hash, flow_count=flow_count)
        self.logger.info('%% Will resume the suspended SVMs and check traffic flow %%%%%%')
        for i in range(len(svms)):
            svms = self.get_svms_in_si(si_fixture)
            if svms[i].status == 'SUSPENDED':
                self.logger.info('Will resume the suspended SVM %s' % svms[i].name)
                svms[i].resume()
                sleep(30)
            else:
                self.logger.info('SVM %s is not SUSPENDED' % svms[i].name)

            self.verify_traffic_flow(left_vm_fixture, dst_vm_list,
                                     si_fixture, left_vn_fixture,
                                     ecmp_hash=ecmp_hash, flow_count=flow_count)


        return True
    # end test_ecmp_hash_vm_suspend_restart


