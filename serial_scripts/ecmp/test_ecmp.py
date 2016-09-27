import traffic_tests
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
from base import BaseECMPRestartTest
from common import isolated_creds
import inspect
import test 

class TestECMPRestart(BaseECMPRestartTest, VerifySvcFirewall, ECMPSolnSetup, ECMPTraffic, ECMPVerify):
    
    @classmethod
    def setUpClass(cls):
        super(TestECMPRestart, cls).setUpClass()

    def runTest(self):
        pass    
    #end runTest
 
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
        if len(self.inputs.compute_ips) > 1:
            for i in range(4, 17, 4):
                self.logger.info(
                    '%%%%%%%%%% Will launch %s instances in the Service Chain %%%%%%%%%%' % i)
                self.verify_svc_in_network_datapath(
                    si_count=1, svc_scaling=True, max_inst=i, svc_mode='in-network-nat')
                svm_ids = self.si_fixtures[0].svm_ids
                self.get_rt_info_tap_intf_list(
                    self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
                dst_vm_list= [self.vm2_fixture]
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
        else:
            self.logger.info(
                'Scaling test. Will run only on multiple node setup')
        return True
    # end test_ecmp_svc_in_network_nat_scale_max_instances
    
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
            self.verify_svc_in_network_datapath(si_count=1, svc_scaling=True, max_inst=3, vn1_subnets= vn1_subnet_list, vn2_subnets= vn2_subnet_list)
            dst_vm_list= [self.vm2_fixture]
            self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
    # end test_ecmp_svc_in_network_with_multiple_service_chains

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
   
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
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list= [self.vm2_fixture]
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
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        return True
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
        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3, flavor='contrail_flavor_2cpu')
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        
        dst_vm_list= [self.vm2_fixture]
        self.verify_traffic_flow(self.vm1_fixture, dst_vm_list, self.si_fixtures[0], self.vn1_fixture)
        self.logger.info('Will shutdown the SVMs and VMs before rebooting the nodes')
        si_svms= []
        si_svms= self.get_svms_in_si(self.si_fixtures[0], self.inputs.project_name)
        vms= [self.vm1_fixture, self.vm2_fixture]
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
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()
        self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)
        return True
    # end test_ecmp_svc_in_network_with_3_instance_reboot_nodes
  
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_interface_static_table(self):

        self.verify_svc_in_network_datapath(si_count=1, svc_scaling=True, max_inst=3, svc_mode='in-network-nat')
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        key, vm_uuid = self.vm1_fixture.get_vmi_ids().popitem()
        vm_uuid = str(vm_uuid)
        add_static_route_cmd = 'python provision_static_route.py --prefix ' + self.vm2_fixture.vm_ip + '/32' + ' --virtual_machine_interface_id ' + vm_uuid + \
            ' --tenant_name ' + self.inputs.project_name + ' --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table' + \
            ' --user ' + "admin" + ' --password ' + "contrail123"
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

            status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
            self.logger.debug("%s" % status)
            m = re.search(r'Creating Route table', status)
            assert m, 'Failed in Creating Route table'

        (domain, project, vn) = self.vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[self.vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = self.vm1_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=self.vm2_fixture.vm_ip, prefix='32')['path_list'][0]['nh']['mc_list']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info('Route found in the Agent %s' % vm2_fixture.vm_node_ip)

        if (len(next_hops) != 3):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')

        return True

    # end test_static_table

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_network_table(self):

        self.verify_svc_in_network_datapath(si_count=1, svc_scaling=True, max_inst=3, svc_mode='in-network-nat')
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        rt_vnc = RouteTable(name="network_table",parent_obj=self.project.project_obj)
        self.vnc_lib.route_table_create(rt_vnc)
        routes = []
        rt10 = RouteType(prefix = '1.1.1.1/32', next_hop = '2.2.2.2', next_hop_type='ip-address')
        routes.append(rt10)
        rt_vnc.set_routes(routes)
        vn_rt_obj = self.vnc_lib.virtual_network_read(id = self.vn2_fixture.uuid)
        vn_rt_obj.add_route_table(rt_vnc)
        self.vnc_lib.virtual_network_update(vn_rt_obj)
        (domain, project, vn) = self.vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[self.vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = self.vm1_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=self.vm2_fixture.vm_ip, prefix='32')['path_list'][0]['nh']['mc_list']
        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info('Route found in the Agent %s' % vm2_fixture.vm_node_ip)

        if (len(next_hops) != 3):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')

        return True

    # end test_network_table

