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
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.base import GenericTestBase
from common.ecmp.base import ECMPTestBase
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
from fabric.state import connections as fab_connections
from common.ecmp.ecmp_test_resource import ECMPSolnSetup
from common import isolated_creds
import inspect

class TestECMPMultipleSC(GenericTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestECMPMultipleSC, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPMultipleSC, cls).tearDownClass()

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_multiple_service_chains(self):
        """
        Description: Validate ECMP with service chaining in-network mode datapath having
                 multiple service chains in parallel between the same two networks.
        Test steps:
                    1.  Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                    2.  Creating multiple service chains in parallel.
                    3.  Creating a service chain by applying the service instance as a service in a policy b
               etween the VNs.
                    4.  Checking for ping and tcp traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 f
                rom vm1.
        Maintainer : ganeshahv@juniper.net
        """
        vn_obj_list = []
        vm_list = []
        for i in range(1, 6):
            vn1_subnets = '10.%s.1.0/24' % i
            vn1_subnet_list= [vn1_subnets]
            vn2_subnets = '20.%s.1.0/24' % i
            vn2_subnet_list= [vn2_subnets]
            ret_dict = self.verify_svc_chain(max_inst=3,
                                             left_vn_subnets=vn1_subnet_list,
                                             right_vn_subnets=vn2_subnet_list,
                                             service_mode='in-network',
                                             create_vms=True)
            vm1_fixture = ret_dict['left_vm_fixture']
            vm2_fixture = ret_dict['right_vm_fixture']
            dst_vm_list= [vm2_fixture]
            self.verify_traffic_flow(vm1_fixture, dst_vm_list,
                ret_dict['si_fixture'], ret_dict['left_vn_fixture'])
    # end test_ecmp_svc_in_network_with_multiple_service_chains

class TestECMPRestart(ECMPTestBase, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):
    
    @classmethod
    def setUpClass(cls):
        super(TestECMPRestart, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestECMPRestart, cls).tearDownClass()

    @preposttest_wrapper
    def test_ecmp_svc_in_network_nat_scale_max_instances(self):
        """
         Description: Validate ECMP with service chaining in-network-nat mode datapath by incrementing the max instances
                    from 4 in steps of 4 till 16
         Test steps:
           1.	Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.	Creating a service instance in in-network-nat mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.	Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.	Checking for ping and tcp traffic between vm1 and vm2.
           5.   Delete the Service Instances and Service Template.
           6.   Increment the service instance max count by 4 and repeat steps 1-5.
           7.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
         Maintainer : ganeshahv@juniper.net
        """
        if len(self.inputs.compute_ips) <= 1:
            raise self.skipTest(''
                'Scaling test. Will run only on multiple node setup')
        for i in range(4, 17, 4):
            self.logger.info(
                '%%%%%%%%%% Will launch %s instances in the Service Chain %%%%%%%%%%' % i)
            ret_dict = self.verify_svc_chain(max_inst=i,
                                             service_mode='in-network-nat',
                                             create_svms=True,
                                             **self.common_args)
            si_fixture = ret_dict['si_fixture']
            st_fixture = ret_dict['st_fixture']
            svm_ids = si_fixture.svm_ids
            self.get_rt_info_tap_intf_list(
                ret_dict['left_vn_fixture'],
                ret_dict['left_vm_fixture'],
                ret_dict['right_vm_fixture'],
                svm_ids,
                si_fixture)
            dst_vm_list= [self.right_vm_fixture]
            self.verify_traffic_flow(self.left_vm_fixture, dst_vm_list,
                si_fixture, self.left_vn_fixture)
            self.logger.info('Deleting the SI %s' % si_fixture.st_name)
            si_fixture.cleanUp()
            self.remove_from_cleanups(si_fixture.cleanUp)
            assert si_fixture.verify_on_cleanup()
            self.logger.info('Deleting the ST %s' %
                             st_fixture.st_name)
            st_fixture.cleanUp()
            self.remove_from_cleanups(st_fixture.cleanUp)
        # end for
    # end test_ecmp_svc_in_network_nat_scale_max_instances

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_service_restarts(self):
        """
        Description: Validate ECMP after restarting control and vrouter services with service chainin
        g in-network mode datapath having service instance
        Test steps:
                   1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                   2.Creating a service instance in in-network mode with 3 instances.
                   3.Creating a service chain by applying the service instance as a service in a po
        licy between the VNs.
                   4.Checking for ping and traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 fr
        om vm1 and vice-versa even after the restarts.
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
        self.verify_traffic_flow(self.left_vm_fixture, dst_vm_list,
            si_fixture, self.left_vn_fixture)
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip],
                                        container='agent')

        # Wait for service stability
        cs_checker = ContrailStatusChecker()
        cluster_status, error_nodes = cs_checker.wait_till_contrail_cluster_stable(
                                          self.inputs.compute_ips)
        assert cluster_status, 'Hash of error nodes and services : %s' % (
                                    error_nodes)

        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()

        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)
        fab_connections.clear()
        self.verify_traffic_flow(self.left_vm_fixture, dst_vm_list,
            si_fixture, self.left_vn_fixture)
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip],
                                        container='control')

        cluster_status, error_nodes = cs_checker.wait_till_contrail_cluster_stable(
                                          self.inputs.bgp_ips)
        assert cluster_status, 'Hash of error nodes and services : %s' % (
                                    error_nodes)

        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()

        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)

        fab_connections.clear()
        self.verify_traffic_flow(self.left_vm_fixture, dst_vm_list,
            si_fixture, self.left_vn_fixture)
    # end test_ecmp_svc_in_network_with_3_instance_service_restarts

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_reboot_nodes(self):
        """
        Description: Validate ECMP after restarting control and vrouter services with service chainin
        g in-network mode datapath having service instance. Check the ECMP behaviour after rebooting the nodes.
        Test steps:
                              1.Creating vm's - vm1 and vm2 in networks vn1 and vn2.
                              2.Creating a service instance in in-network mode with 3 instances.
                              3.Creating a service chain by applying the service instance as a service in a po
           licy between the VNs.
                              4.Checking for ping and traffic between vm1 and vm2.
        Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 fr
           om vm1 and vice-versa even after the restarts.
        Maintainer : ganeshahv@juniper.net
        """
        cmd = 'reboot'
        ret_dict = self.verify_svc_chain(max_inst=3,
                                         service_mode='in-network',
                                         create_svms=True,
                                         **self.common_args)
        si_fixture = ret_dict['si_fixture']
        svm_ids = si_fixture.svm_ids
        self.get_rt_info_tap_intf_list(
            self.left_vn_fixture, self.left_vm_fixture, self.right_vm_fixture,
            svm_ids, si_fixture)

        dst_vm_list= [self.right_vm_fixture]
        self.verify_traffic_flow(self.left_vm_fixture, dst_vm_list,
                                 si_fixture, self.left_vn_fixture)
        self.logger.info('Will shutdown the SVMs and VMs before rebooting the nodes')
        si_svms= []
        si_svms= self.get_svms_in_si(si_fixture)
        vms= [self.left_vm_fixture, self.right_vm_fixture]
        for svm in si_svms:
            svm.stop()
        for vm in vms:
            vm.vm_obj.stop()
        self.logger.info('Will reboot the Compute and Control nodes')
        nodes= []
        nodes = list(set(self.inputs.compute_ips + self.inputs.bgp_ips) - set(self.inputs.cfgm_ips))
        for node in nodes:
            if socket.gethostbyaddr(node)[0] != socket.gethostname():
               self.inputs.reboot(node)
            else:
                self.logger.info(
                    'Node %s is the active cfgm. Will skip rebooting it.' %
                    socket.gethostbyaddr(node)[0])
        self.logger.info(
            'Will check the state of the SIs and power it ON, if it is in SHUTOFF state')
        for svm in si_svms:
            try:
                self.logger.info('Will Power-On %s' % svm.name)
                svm.start()
            except Conflict:
                pass
        for vm in vms:
            try:
                self.logger.info('Will Power-On %s' % vm.vm_obj.name)
                vm.vm_obj.start()
            except Conflict:
                pass
        self.logger.info('Sleeping for 120 seconds')
        sleep(120)
        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip)
    # end test_ecmp_svc_in_network_with_3_instance_reboot_nodes
