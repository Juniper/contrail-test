#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import copy
import traceback
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.agent.vna_introspect_utils import *
from random import choice
from topo_helper import *
from common.policy import policy_test_utils
import project_test_utils
from tcutils.wrappers import preposttest_wrapper
from tcutils.topo.sdn_topo_setup import *
import sdn_policy_traffic_test_topo
import traffic_tests
from flow_tests.flow_test_utils import *


class sdnTrafficTest(VerifySvcMirror, testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(sdnTrafficTest, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect = self.connections.agent_inspect
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.ops_inspect = self.connections.ops_inspect
    # end setUpClass

    def cleanUp(self):
        super(sdnTrafficTest, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_traffic_across_projects(self):
        """Traffic test with policy applied across multiple projects"""
        result = True
        topology_class_name = None

        #
        # Check if there are enough nodes i.e. atleast 2 compute nodes to run this test.
        # else report that minimum 2 compute nodes are needed for this test and
        # exit.
        if len(self.inputs.compute_ips) < 2:
            self.logger.warn(
                "Minimum 2 compute nodes are needed for this test to run")
            self.logger.warn(
                "Exiting since this test can't be run on single compute node")
            return True

        #
        # Get config for test from topology
        import common.topo.sdn_policy_topo_with_multi_project
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_policy_topo_with_multi_project.sdn_basic_policy_topo_with_fip

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        #
        # Create a list of compute node IP's and pass it to topo if you want to pin
        # a vm to a particular node
        topo_obj = topology_class_name(
                        compute_node_list=self.inputs.compute_ips)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        topo = {}
        topo_objs = {}
        config_topo = {}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo_obj))
        out = setup_obj.sdn_topo_setup()
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo_objs, config_topo, vm_fip_info = out['data']

        p_lst = topo_obj.project_list  # projects
        p1vm1 = topo_objs[p_lst[0]].vmc_list[0]  # 'vmc1'
        p2vm2 = topo_objs[p_lst[1]].vmc_list[0]  # 'vmc2'
        p3vm3 = topo_objs[p_lst[2]].vmc_list[0]  # 'vmc3'
        adminvm = topo_objs[p_lst[3]].vmc_list[0]  # 'vmc-admin'

        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 1
        total_streams['tcp'] = 1
        dpi = 9100
        expectedResult = {}
        for proto in traffic_proto_l:
            expectedResult[proto] = True
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            if proto == 'icmp':
                tx_vm_fixt = config_topo[p_lst[0]]['vm'][
                    p1vm1]
                rx_vm_fixt = config_topo[p_lst[1]]['vm'][p2vm2]
            else:
                tx_vm_fixt = config_topo[p_lst[0]]['vm'][
                    p1vm1]
                rx_vm_fixt = config_topo[p_lst[2]]['vm'][p3vm3]

            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            if vm_fip_info[0]:
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=tx_vm_fixt, rx_vm_fixture=rx_vm_fixt, stream_proto=proto, vm_fip_info=vm_fip_info[1])
            else:
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=tx_vm_fixt, rx_vm_fixture=rx_vm_fixt, stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, tx_vm_fixt.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            self.assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # Poll live traffic
        traffic_stats = {}
        err_msg = []
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            self.logger.info("Poll live traffic %s and get status.." %
                             (proto))
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            if not traffic_stats['status']:
                err_msg.extend(
                    ["Traffic disruption is seen:", traffic_stats['msg']])
        self.assertEqual(traffic_stats['status'],
                         expectedResult[proto], err_msg)
        self.logger.info("-" * 80)

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            status = True if stopStatus[proto] == [] else False
            if status != expectedResult[proto]:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        self.assertEqual(result, True, msg)

        result = True
        msg = []
        dst_vm = p3vm3  # 'vmc3'
        dst_vm_fixture = config_topo[p_lst[2]]['vm'][p3vm3]
        dst_vm_ip = dst_vm_fixture.vm_ip
        src_vm = p1vm1  # 'vmc1'
        src_vm_fixture = config_topo[p_lst[0]]['vm'][p1vm1]
        self.logger.info(
            "With proto tcp allowed between %s and %s, trying to send icmp traffic" % (p1vm1, p3vm3))
        expectedResult = False
        self.logger.info(
            "Verify ping to vm %s from vm %s, expecting it to fail" %
            (dst_vm, src_vm))
        ret = src_vm_fixture.ping_with_certainty(
            dst_vm_ip, expectation=expectedResult)
        result_msg = "vm ping test result to vm %s is: %s" % (dst_vm, ret)
        self.logger.info(result_msg)
        if ret != True:
            result = False
            msg.extend(
                ["icmp traffic passed with deny rule:", result_msg])
        self.assertEqual(result, True, msg)

        result = True
        msg = []
        expectedResult = True
        dst_vm = p2vm2  # 'vmc2'
        dst_vm_fixture = config_topo[p_lst[1]]['vm'][p2vm2]
        dst_vm_ip = dst_vm_fixture.vm_ip
        src_vm_fixture = config_topo[p_lst[3]]['vm'][adminvm]  # 'vmc-admin'
        self.logger.info(
            "Now will test ICMP traffic between admin VM %s and non-default project VM %s" %
            (adminvm, p2vm2))
        ret = src_vm_fixture.ping_with_certainty(
            dst_vm_ip, expectation=expectedResult)
        result_msg = "vm ping test result to vm %s is: %s" % (dst_vm, ret)
        self.logger.info(result_msg)
        if ret != True:
            result = False
            msg.extend(
                ["ICMP traffic failed between default and non-default project with policy:", result_msg])
        self.assertEqual(result, True, msg)
        return True
    # end test_traffic_across_projects

    @preposttest_wrapper
    def test_policy_with_scaled_udp_18k_flows_900persec_setup_only(self):
        """ Test focus on scaling flows.. With 2VN's and nVM's based on num computes, launch UDP streams from all VM's.
        """
        # Setup only test, not for automated regression
        skip_test = False
        # XXXX set skip_test to False for manual run only...
        #skip_test= False
        if skip_test:
            self.logger.warn("Skipping test meant for manual run")
            return True
        self.inputs.fixture_cleanup = 'no'
        computes = len(self.inputs.compute_ips)
        # 6000 flows[pkts]/min=100 pps==> 18000 peak flows in 180s
        vms_per_compute = 2
        num_streams = 180
        flow_rate = 900
        topo_obj = sdn_policy_traffic_test_topo.sdn_2vn_xvm_config(
                       project=self.inputs.project_name)
        topo = topo_obj.build_topo(
            num_compute=computes, num_vm_per_compute=vms_per_compute)
        planned_per_compute_num_streams = vms_per_compute * num_streams
        total_streams_generated = planned_per_compute_num_streams * computes
        self.logger.info("Total streams to be generated per compute: %s" %
                         planned_per_compute_num_streams)
        self.logger.info("Total streams to be generated : %s" %
                         total_streams_generated)
        return self.policy_test_with_scaled_udp_flows(
            topo, num_udp_streams=num_streams, pps=flow_rate,
            wait_time_after_start_traffic=10, setup_only=True)

    @preposttest_wrapper
    def test_policy_with_scaled_udp_18k_flows_900persec_vms_on_single_compute_setup_only(self):
        """ Test focus on scaling flows.. With 2VN's and nVM's based on num computes, launch UDP streams from all VM's.
            All VMs will be launched in single compute node.
        """
        # Setup only test, not for automated regression
        skip_test = False
        # XXXX set skip_test to False for manual run only...
        #skip_test= False
        if skip_test:
            self.logger.warn("Skipping test meant for manual run")
            return True
        self.inputs.fixture_cleanup = 'no'
        computes = len(self.inputs.compute_ips)
        # 6000 flows[pkts]/min=100 pps==> 18000 peak flows in 180s
        vms_per_compute = 2
        num_streams = 180
        flow_rate = 900
        topo_obj = sdn_policy_traffic_test_topo.sdn_2vn_xvm_config(
                       project=self.inputs.project_name)
        topo = topo_obj.build_topo(
            num_compute=computes, num_vm_per_compute=vms_per_compute)
        planned_per_compute_num_streams = vms_per_compute * num_streams
        total_streams_generated = planned_per_compute_num_streams * computes
        self.logger.info("Total streams to be generated per compute: %s" %
                         planned_per_compute_num_streams)
        self.logger.info("Total streams to be generated : %s" %
                         total_streams_generated)
        return self.policy_test_with_scaled_udp_flows(
            topo, num_udp_streams=num_streams, pps=flow_rate,
            wait_time_after_start_traffic=10, vms_on_single_compute=True, setup_only=True)

    def policy_test_with_scaled_udp_flows(self, topo, num_udp_streams=100, pps=100, wait_time_after_start_traffic=300, vms_on_single_compute=False, setup_only=False):
        """Pick 2n VM's for testing, have rules affecting udp protocol..
        pick 2 VN's, source and destination. each VM in src will send to a unique VM in dest.
        Generate traffic streams matching policy rules - udp for now..
        Check for system stability with flow scaling and traffic behavior as expected.
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        if vms_on_single_compute:
            out = setup_obj.topo_setup(vms_on_single_compute=True)
        else:
            out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo, config_topo = out['data']
        # Setup/Verify Traffic ---
        # 1. Define Traffic Params
        # This will be source_vn for traffic test
        test_vn = topo.vnet_list[0]
        dest_vn = topo.vnet_list[1]
        topo_helper_obj = topology_helper(topo)
        vms_in_vn = topo_helper_obj.get_vm_of_vn()
        src_vms = vms_in_vn[test_vn]
        dest_vms = vms_in_vn[dest_vn]
        self.logger.info("----" * 20)
        self.logger.info("num_udp_streams: %s, pps: %s, src_vms: %s" %
                         (num_udp_streams, pps, len(src_vms)))
        self.logger.info("----" * 20)
        # using default protocol udp, traffic_proto_l= ['udp']
        total_single_instance_streams = num_udp_streams
        # 2. set expectation to verify..
        matching_rule_action = {}
        # Assumption made here: one policy assigned to test_vn
        policy = topo.vn_policy[test_vn][0]
        policy_info = "policy in effect is : " + str(topo.rules[policy])
        num_rules = len(topo.rules[policy])
        # Assumption made here: one rule for each dest_vn
        for i in range(num_rules):
            dvn = topo.rules[policy][i]['dest_network']
            matching_rule_action[dvn] = topo.rules[policy][i]['simple_action']
        if num_rules == 0:
            matching_rule_action[dvn] = 'deny'
        self.logger.info("matching_rule_action: %s" % matching_rule_action)
        # 3. Start Traffic
        traffic_obj = {}
        startStatus = {
        }
        stopStatus = {}
        expectedResult = {}
        for i in range(len(src_vms)):
            test_vm1 = src_vms[i]
            test_vm2 = dest_vms[i]
            test_vm1_fixture = config_topo['vm'][test_vm1]
            test_vm2_fixture = config_topo['vm'][test_vm2]
            expectedResult[i] = True if matching_rule_action[
                dest_vn] == 'pass' else False
            startStatus[i] = {}
            traffic_obj[i] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture, rx_vm_fixture, \
            # stream_proto, packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20)
            startStatus[i] = traffic_obj[i].startTraffic(
                tx_vm_fixture=test_vm1_fixture,
                rx_vm_fixture=test_vm2_fixture, total_single_instance_streams=total_single_instance_streams,
                cfg_profile='ContinuousSportRange', pps=pps)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                i, test_vm1_fixture.vm_ip, startStatus[i]['status'])
            if startStatus[i]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[i]['msg']])
            else:
                self.logger.info(msg1)
            self.assertEqual(startStatus[i]['status'], True, msg)
        self.logger.info("-" * 80)
        sessions = self.tcpdump_on_analyzer(topo.si_list[0])
        for svm_name, (session, pcap) in sessions.items():
            self.verify_mirror(svm_name, session, pcap)

        if setup_only:
            self.logger.info("Test called with setup only..")
            return True
        else:
            # Should be more than 3 mins, aging time, for flows to peak and
            # stabilise
            time.sleep(wait_time_after_start_traffic)
        # 4. Stop Traffic & validate received packets..
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for i in range(len(src_vms)):
            stopStatus[i] = traffic_obj[i].stopTraffic(loose='yes')
            status = True if stopStatus[i] == [] else False
            if status != expectedResult[i]:
                msg.append(stopStatus[i])
            self.logger.info("Status of stop traffic for instance %s is %s" %
                             (i, stopStatus[i]))
        if msg != []:
            result = False
        self.assertEqual(result, True, msg)
        self.logger.info("-" * 80)
        # 5. verify kernel flows after stopping traffic.. we dont expect any
        # stuck HOLD flows.
        for compNode in self.inputs.compute_ips:
            retry = 0
            while retry < 5:
                kflows = self.agent_inspect[compNode].get_vna_kflowresp()
                wait_time = 60 if len(kflows) > 1000 else 30
                if len(kflows) == 0:
                    break
                else:
                    self.logger.info(
                        "Waiting for Kernel flows to drain in Compute %s, attempt %s, num_flows %s" %
                        (compNode, retry, len(kflows)))
                    time.sleep(wait_time)
                    retry += 1
        for compNode in self.inputs.compute_ips:
            out = self.check_exception_flows_in_kernel(compNode)
            self.logger.info("out is: %s" % out)
            self.assertEqual(out['status'], True, out['msg'])
        # end checking flows
        return result
    # end policy_test_with_scaled_udp_flows

# end sdnTrafficTest
