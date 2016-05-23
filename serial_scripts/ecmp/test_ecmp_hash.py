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
from tcutils.contrail_status_check import *

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
        self.verify_traffic_flow(self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
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
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
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
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
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
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True}
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn2_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture,self.vm1_fixture, self.vm2_fixture, ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vm1_fixture, self.vm2_fixture,ecmp_hashing_include_fields)
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

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True

    # end test_ecmp_svc_precedence

    @preposttest_wrapper
    def test_static_table(self):

        self.verify_svc_in_network_datapath(
            si_count=1, svc_scaling=True, max_inst=3)
        svm_ids = self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(
            self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, svm_ids)
        dst_vm_list = [self.vm2_fixture]
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        ecmp_hashing_include_fields = 'l3-source-address,l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vm1_fixture, self.vm2_fixture, ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True}
        self.update_hash_on_network(ecmp_hash = ecmp_hashing_include_fields, vn_fixture = self.vn2_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-protocol,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture,self.vm1_fixture, self.vm2_fixture, ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True}
        self.update_hash_on_port(ecmp_hash = ecmp_hashing_include_fields, vm_fixture = self.vm2_fixture)
        ecmp_hashing_include_fields = 'l3-destination-address,l4-destination-port,'
        self.verify_if_hash_changed(self.vn1_fixture, self.vm1_fixture, self.vm2_fixture,ecmp_hashing_include_fields)
        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)
        key, vm_uuid = self.vm1_fixture.get_vmi_ids().popitem()
        vm_uuid = str(vm_uuid)
        add_static_route_cmd = 'python provision_static_route.py --prefix ' + self.vm2_fixture.vm_ip + '/32' + ' --virtual_machine_interface_id ' + vm_uuid + \
            ' --tenant_name ' + self.inputs.project_name + ' --api_server_ip 127.0.0.1 --api_server_port 8082 --oper 
add --route_table_name my_route_table' + \
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

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, 
"ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True

    # end test_static_table


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
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        for node in self.inputs.compute_ips:
             self.inputs.restart_service('supervisor-vrouter', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable(nodes = [node])
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
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
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        for node in self.inputs.cfgm_ips:
             self.inputs.restart_service('contrail-schema', [node])
             cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable(nodes = [node])
             assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)

        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_svc_in_network_restart_schema

