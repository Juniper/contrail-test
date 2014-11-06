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

class TestECMPRestart(BaseECMPRestartTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):
    
    @classmethod
    def setUpClass(cls):
        super(TestECMPRestart, cls).setUpClass()

    def runTest(self):
        pass    
    #end runTest
    
    @test.attr(type='serial')
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_service_restarts(self):
        """Validate ECMP after restarting control and vrouter services with service chaining in-network mode datapath having
        service instance"""
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list= [self.vm2_fixture]
#        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list)
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)
        
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()

        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        fab_connections.clear()
#        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list)
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)

        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()

        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        fab_connections.clear()
#        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list)
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_service_restarts

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_reboot_nodes(self):
        """Validate ECMP after restarting control and vrouter services with service chaining in-network mode datapath having
        service instance. Check the ECMP behaviour after rebooting the nodes"""
        cmd = 'reboot'
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3, flavor='contrail_flavor_2cpu')
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        
        dst_vm_list= [self.vm2_fixture]
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.logger.info('Will reboot the Compute and Control nodes')
        nodes= []
        nodes= list(set(self.inputs.compute_ips + self.inputs.bgp_ips))
        for node in nodes:
            if node != self.inputs.cfgm_ips[0]:
                self.logger.info('Will reboot the node %s' %
                                 socket.gethostbyaddr(node)[0])
                self.inputs.run_cmd_on_server(
                    node, cmd, username='root', password='c0ntrail123')
            else:
                self.logger.info(
                    'Node %s is the first cfgm. Will skip rebooting it.' %
                    socket.gethostbyaddr(node)[0])
        self.logger.info('Sleeping for 240 seconds')
        sleep(240)
        self.logger.info(
            'Will check the state of the SIs and power it ON, if it is in SHUTOFF state')
        # We need to check the status of only those VMs associated with this project
        si_svms= []
        si_svms= self.get_svms_in_si(self.si_fixtures[0], self.inputs.project_name)
        vms= [self.vm1_fixture, self.vm2_fixture]
        for svm in si_svms:
            if self.nova_fixture.wait_till_vm_is_active(svm)[1] != 'ACTIVE':
                self.logger.info('Will Power-On %s' % svm.name)
                svm.start()
        for vm in vms:
            if self.nova_fixture.wait_till_vm_is_active(vm.vm_obj)[1] != 'ACTIVE':
                self.logger.info('Will Power-On %s' % vm.vm_obj.name)
                vm.vm_obj.start()
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        fab_connections.clear()
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_reboot_nodes
