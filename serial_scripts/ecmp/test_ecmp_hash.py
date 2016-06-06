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
from tcutils.tcpdump_utils import *
from tcutils.commands import *
import re

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

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, 
"ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True

    # end test_static_table

    @preposttest_wrapper
    def test_ecmp_hardcode_path(self):
        """
         Description: Validate ECMP Hash with service chaining in-network mode
         Test steps:
           1.   Creating vm's - vm1 and vm2 in networks vn1 and vn2.
           2.   Creating a service instance in in-network mode with 4 instances and
                left-interface of the service instances sharing the IP.
           3.   Creating a service chain by applying the service instance as a service in a policy between the VNs.
           4.   Checking for ping and tcp traffic between vm1 and vm2. Delete "source-port" hash field in ecmp.
           5.   Delete the Service Instances and Service Template.
           6.   This testcase will be run in only multiple compute node scenario.
         Pass criteria: Ping between the VMs should be successful and TCP traffic should reach vm2 from vm1.
        """
   
        self.verify_svc_transparent_datapath(
            si_count=1, svc_scaling=True, max_inst=2, svc_img_name='tiny_trans_fw',  ci=True)
 
        svm_ids = self.si_fixtures[0].svm_ids
        dst_vm_list = [self.vm2_fixture]
        svms = self.get_svms_in_si(self.si_fixtures[0], self.inputs.project_name)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        i = 0
        session = []
        pcap = []
        filters = '-nn'
        for svm in svms:
            tap_if_of_svm = self.get_bridge_svm_tapintf(svm.name, 'right')
            vm_nodeip = self.inputs.host_data[self.nova_h.get_nova_host_of_vm(self.get_svm_obj(svm.name))]['host_ip']
            compute_user = self.inputs.host_data[vm_nodeip]['username']
            compute_password = self.inputs.host_data[vm_nodeip]['password']
            session_item, pcap_item = start_tcpdump_for_intf(vm_nodeip, compute_user, compute_password, tap_if_of_svm, filters=filters)
            session.append(session_item)
            pcap.append(pcap_item)
            i = i + 1
        cmds = ['nslookup %s %s' % (self.vm1_fixture.vm_ip, self.vm1_fixture.vm_ip)]
        output = self.vm2_fixture.run_cmd_on_vm(cmds=cmds, as_sudo=True)
        i = 0
        sleep(10)
        for svm in svms:
            cmd = 'tcpdump -r %s' % pcap[i]
            cmd_check_nslookup, err = execute_cmd_out(session[i], cmd, self.logger)
            send_ns = re.search("IP (.+ > .+): \d\+ PTR" , cmd_check_nslookup)
            stop_tcpdump_for_vm_intf(self, session[i], pcap[i])
            if not (send_ns and (self.vm2_fixture.vm_ip in send_ns.group(0)) and (self.vm1_fixture.vm_ip in send_ns.group(0))):
                self.logger.error("nslookup packets did not get ecmped across si vms")
            else:
                self.logger.info("nslookup packets got ecmped across si vms")   
            i = i + 1

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True}
        self.config_all_hash(ecmp_hashing_include_fields)
        i = 0
        sess = []
        pcaps = []
        for svm in svms:
            tap_if_of_svm = self.get_bridge_svm_tapintf(svm.name, 'right')
            vm_nodeip = self.inputs.host_data[self.nova_h.get_nova_host_of_vm(self.get_svm_obj(svm.name))]['host_ip']
            compute_user = self.inputs.host_data[vm_nodeip]['username']
            compute_password = self.inputs.host_data[vm_nodeip]['password']
            sess_item, pcaps_item = start_tcpdump_for_intf(vm_nodeip, compute_user, compute_password, tap_if_of_svm, filters = filters)
            sess.append(sess_item)
            pcaps.append(pcaps_item)
            i = i + 1
        cmds = ['nslookup %s %s' % (self.vm1_fixture.vm_ip, self.vm1_fixture.vm_ip)]
        output = self.vm2_fixture.run_cmd_on_vm(cmds=cmds, as_sudo=True)
        i = 0
        sleep(10)
        some_have_nslookup = False
        atleast_one_has_nslookup = False
        for svm in svms:
            cmd = 'tcpdump -r %s' % pcaps[i]
            cmd_check_nslookup, err = execute_cmd_out(sess[i], cmd, self.logger)
            send_ns = re.search("IP (.+ > .+): \d\+ PTR" , cmd_check_nslookup)
            if not (send_ns and (self.vm2_fixture.vm_ip in send_ns.group(0)) and (self.vm1_fixture.vm_ip in send_ns.group(0))): 
                some_have_nslookup = True
            else:
                atleast_one_has_nslookup = True
            stop_tcpdump_for_vm_intf(self, sess[i], pcaps[i])
            i = i + 1
        if not (some_have_nslookup and atleast_one_has_nslookup):
            self.logger.error("nslookup packets should be hardcoded to one of the paths as source-port is removed") 

        self.verify_traffic_flow(
            self.vm1_fixture, [self.vm2_fixture], self.si_fixtures[0], self.vn1_fixture)
        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        self.addCleanup(self.config_all_hash(ecmp_hashing_include_fields))
        return True
    # end test_ecmp_hardcode_path


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

