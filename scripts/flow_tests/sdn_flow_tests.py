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
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from vna_introspect_utils import *
from random import choice
from topo_helper import *
import policy_test_utils
import project_test_utils
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from sdn_topo_setup import *
from get_version import *
from system_verification import *
import sdn_flow_test_topo
import traffic_tests
import time
import datetime
import threading
import socket
import flow_test_utils


class sdnFlowTest(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(sdnFlowTest, self).setUp()
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
        super(sdnFlowTest, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    # get source min, max ip's and destination max port.
    def src_min_max_ip_and_dst_max_port(self, ips, no_of_ip, dst_min_port, flows):
        """ Called by test_flow_single_project or test_flow_multi_project to get the min source ip, max source ip and 
            Max port number of the destination. This helps to create certain no of flows as expected by test_flow_single_project
            or test_flow_multi_project routines, from where it is called.
        """
        ip_list = list()
        for index in range(no_of_ip):
            ip_list.append(ips[index])
        src_min_ip = ip_list[0]
        src_max_ip = ip_list[-1]
        dst_max_port = dst_min_port + (flows / no_of_ip)
        result_dict = {'src_min_ip': src_min_ip, 'src_max_ip':
                       src_max_ip, 'dst_max_port': dst_max_port}
        return result_dict
    # end src_min_max_ip_and_dst_max_port

    def start_traffic(self, vm, src_min_ip='', src_max_ip='', dest_ip='', dest_min_port='', dest_max_port='', pkt_cnt=''):
        """ This routine is for generation of UDP flows using pktgen. Only UDP packets are generated using this routine. 
        """
        self.logger.info("Sending traffic...")
        try:
            cmd = '~/flow_test_pktgen.sh %s %s %s %s %s %s' % (src_min_ip,
                                                               src_max_ip, dest_ip, dest_min_port, dest_max_port, pkt_cnt)
            vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        except Exception as e:
            self.logger.exception("Got exception at start_traffic as %s" % (e))
    # end start_traffic

    def generate_udp_flows_and_do_verification(self, traffic_profile, verification_obj, build_version):
        """ Routine to generate UDP flows by calling the start_traffic routine in a thread and do parallel verification of 
            flow setup rate and system level verifications like vm-state, vn-state, policies etc.
            @inputs :
            traffic_profile - a list of traffic generation parameters as explained in test_flow_single_project and test_flow_multi_project
                              routines.
            verification_obj - topology objects to call verification methods on them.
            build_version - os_version, release_version and build_version for logging purposes.
        """
        Shost = socket.gethostbyaddr(traffic_profile[0].vm_node_ip)
        Dhost = socket.gethostbyaddr(traffic_profile[7].vm_node_ip)
        self.logger.info("Src_VM = %s, Src_IP_Range = %s to %s, Dest_VM = %s, Dest_IP = %s, Src_VN = %s, Dest_VN = %s,"
                         " Port_Range = %s to %s, Src_Node = %s, Dst_Node = %s." % (traffic_profile[0].vm_name,
                                                                                    traffic_profile[1], traffic_profile[
                                                                                        2], traffic_profile[
                                                                                        7].vm_name, traffic_profile[
                                                                                        3],
                                                                                    traffic_profile[0].vn_name, traffic_profile[
                                                                                        7].vn_name, traffic_profile[
                                                                                        4], traffic_profile[
                                                                                        5],
                                                                                    Shost[0], Dhost[0]))

        th = threading.Thread(
            target=self.start_traffic, args=(
                traffic_profile[0], traffic_profile[1], traffic_profile[2],
                traffic_profile[3], traffic_profile[
                    4], traffic_profile[
                    5],
                traffic_profile[6]))
        th.start()

        #
        # Flow setup rate calculation.
        NoOfFlows = []
        FlowRatePerInterval = []
        AverageFlowSetupRate = 0
        default_setup_rate = 7000  # A default value of 7K flows per second.
        src_vm_obj = traffic_profile[0]
        dst_vm_obj = traffic_profile[7]

        #
        # Decide the test is for NAT Flow or Policy Flow.
        PolNatSI = 'NONE'
        srcFIP = src_vm_obj.chk_vmi_for_fip(src_vm_obj.vn_fq_name)
        dstFIP = dst_vm_obj.chk_vmi_for_fip(dst_vm_obj.vn_fq_name)
        if srcFIP is None:
            if dstFIP is None:
                PolNatSI = 'Policy Flow'
        else:
            PolNatSI = 'NAT Flow'

        #
        # Get or calculate the sleep_interval/wait time before getting the no of flows in vrouter for each release based
        # on a file defining a release to average flow setup rate mapping. The threshold defined in the file is for Policy Flows,
        # so NAT flow is calculated at 70% of the average flow setup rate
        # defined.
        RelVer = str(get_VrouterReleaseVersion(self))
        from ReleaseToFlowSetupRateMapping import *
        try:
            DefinedSetupRate = my_rel_flow_setup_rate_mapping[RelVer]
        except KeyError:
            # A default value of 7K flows per second is set.
            DefinedSetupRate = default_setup_rate

        #
        # if we are creating NAT Flows then our expected flow setup rate should be 70% of the defined flow setup
        # rate defined for that release in ReleaseToFlowSetupRateMapping file.
        if PolNatSI == 'NAT Flow':
            DefinedSetupRate = 0.7 * DefinedSetupRate
        #
        # The flow setup rate is calculated based on setup time required for first 100K flows. So TotalFlows is set to 100K and 5
        # samples (NoOfIterations) are taken within the time required to setup 100K flows. The time interval (sleep_interval) is
        # calculated based on DefinedSetupRate for the particular release
        # version.
        TotalFlows = 100000
        NoOfIterations = 5
        sleep_interval = (float(TotalFlows) / float(DefinedSetupRate)) / \
            float(NoOfIterations)

        #
        # After each sleep_interval we get the number of active forward or nat flows setup on the vrouter which is repeated for
        # NoOfIterations times. and the average is calculated in each
        # iteration.
        for ind in range(NoOfIterations):
            time.sleep(sleep_interval)
            NoOfFlows.append(flow_test_utils.vm_vrouter_flow_count(src_vm_obj))
            if ind == 0:
                FlowRatePerInterval.append(NoOfFlows[ind])
                AverageFlowSetupRate = FlowRatePerInterval[ind]
            elif ind > 0:
                FlowRatePerInterval.append(NoOfFlows[ind] - NoOfFlows[ind - 1])
                AverageFlowSetupRate = (
                    AverageFlowSetupRate + FlowRatePerInterval[ind]) / 2
            self.logger.info("Flows setup in last %s sec = %s" %
                             (sleep_interval, FlowRatePerInterval[ind]))
            self.logger.info(
                "Average flow setup rate per %s sec till this iteration = %s" %
                (sleep_interval, AverageFlowSetupRate))
            self.logger.info(" ")

        self.logger.info("Sleeping for 60 sec, for all the flows to be setup.")
        time.sleep(60)
        # Calculate the flow setup rate per second = average flow setup in
        # sleep interval over the above iterations / sleep interval.
        AverageFlowSetupRate = int(AverageFlowSetupRate / sleep_interval)
        self.logger.info("Flow setup rate seen in this test is = %s" %
                         (AverageFlowSetupRate))
        if (AverageFlowSetupRate < (0.9 * DefinedSetupRate)):
            self.logger.warn(
                "Flow setup rate seen in this test fell below 90 percent of the defined flow setup rate for this release - %s." %
                (DefinedSetupRate))
        else:
            self.logger.info(
                "Flow setup rate seen in this test is close to or above the defined flow setup rate for this release - %s." %
                (DefinedSetupRate))

        # write to a file to do record keeping of the flow rate on a particular
        # node.
        ts = time.time()
        mtime = datetime.datetime.fromtimestamp(
            ts).strftime('%Y-%m-%d %H:%M:%S')

        fh = open("Flow_Test_Data.xls", "a")
        localflow = 'Remote Flow'
        # Check if it's a remote or local flow to log the data accordingly.
        if Shost[0] == Dhost[0]:
            localflow = 'Local Flow'
        # if source and destination VN are same then it's not a NAT/Policy flow else it is a NAT/Policy flow and needs to be logged
        # accordingly.
        if src_vm_obj.vn_name == dst_vm_obj.vn_name:
            mystr = "%s\t%s\t%s\t%s\t%s\n" % (
                build_version, mtime, Shost[0], AverageFlowSetupRate, localflow)
        else:
            mystr = "%s\t%s\t%s\t%s\t%s\t%s\n" % (
                build_version, mtime, Shost[0], AverageFlowSetupRate, localflow, PolNatSI)

        fh.write(mystr)
        fh.close()

        #
        # Do system verification.
        verify_system_parameters(self, verification_obj)

        self.logger.info("Joining thread")
        th.join()

        #
        # Fail the test if the actual flow setup rate is < 70% of the defined
        # flow setup rate for the release.
        if (AverageFlowSetupRate < (0.7 * DefinedSetupRate)):
            self.logger.error(
                "The Flow setup rate seen in this test is below 70% of the defined (expected) flow setup rate for this release.")
            self.logger.error(
                "The Actual Flow setup rate = %s and the Defined Flow setup rate = %s." %
                (AverageFlowSetupRate, DefinedSetupRate))
            self.logger.error(
                "This clearly indicates there is something wrong here and thus the test will execute no further test cases.")
            self.logger.error("Exiting Now!!!")
            return False

        return True
    # end generate_udp_flows_and_do_verification

    @preposttest_wrapper
    def test_flow_single_project(self):
        """Tests related to flow setup rate and flow table stability accross various triggers for verification
           accross VN's within a single project"""
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
        import sdn_flow_test_topo
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_flow_test_topo.sdn_flow_test_topo_single_project

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

        # Create traffic based on traffic profile defined in topology.
        import analytics_performance_tests
        ana_obj = analytics_performance_tests.AnalyticsTestPerformance()
        ana_obj.setUp()
        traffic_profiles = {}
        count = 0
        num_ports_per_ip = 50000.00
        # forward flows = (total no. of flows / 2), so fwd_flow_factor = 2
        fwd_flow_factor = 2
        for TrafficProfile in topo_obj.traffic_profile:
            src_min_ip = 0
            src_max_ip = 0
            dst_ip = 0
            pkt_cnt = 0
            dst_min_port = 5000
            dst_max_port = 55000
            count += 1
            profile = 'profile' + str(count)
            src_vm = topo_obj.traffic_profile[TrafficProfile]['src_vm']
            src_vm_obj = None
            pkt_cnt = topo_obj.traffic_profile[TrafficProfile]['num_pkts']
            for proj in config_topo:
                for vm in config_topo[proj]:
                    for vm_name in config_topo[proj][vm]:
                        if topo_obj.traffic_profile[TrafficProfile]['dst_vm'] == vm_name:
                            dst_ip = config_topo[proj][vm][vm_name].vm_ip
                            dst_vm_obj = config_topo[proj][vm][vm_name]
                        if src_vm == vm_name:
                            src_vm_obj = config_topo[proj][vm][vm_name]

            prefix = topo_obj.vm_static_route_master[src_vm]
            ip_list = ana_obj.get_ip_list_from_prefix(prefix)
            no_of_ip = int(math.ceil(
                (topo_obj.traffic_profile[TrafficProfile]['num_flows'] / fwd_flow_factor) / num_ports_per_ip))
            forward_flows = topo_obj.traffic_profile[
                TrafficProfile]['num_flows'] / fwd_flow_factor
            result_dict = sdnFlowTest.src_min_max_ip_and_dst_max_port(
                self, ip_list, no_of_ip, dst_min_port, forward_flows)
            if int(no_of_ip) == 1:
                # Use the src VM IP to create the flows no need of static IP's
                # that have been provisioned to the VM route table.
                traffic_profiles[profile] = [src_vm_obj,  # src_vm obj
                                             src_vm_obj.vm_ip,  # src_ip_min
                                             src_vm_obj.vm_ip,  # src_ip_max
                                             dst_ip,  # dest_vm_ip
                                             dst_min_port,  # dest_port_min
                                             # dest_port_max
                                             result_dict['dst_max_port'],
                                             # packet_count
                                             topo_obj.traffic_profile[
                                                 TrafficProfile]['num_pkts'],
                                             dst_vm_obj]  # dest_vm obj
            else:
                # Use thestatic IP's that have been provisioned to the VM route
                # table as src IP range.
                traffic_profiles[profile] = [src_vm_obj,  # src_vm obj
                                             # src_ip_min
                                             result_dict['src_min_ip'],
                                             # src_ip_max
                                             result_dict['src_max_ip'],
                                             dst_ip,  # dest_vm_ip
                                             dst_min_port,  # dest_port_min
                                             # dest_port_max
                                             result_dict['dst_max_port'],
                                             # packet_count
                                             topo_obj.traffic_profile[
                                                 TrafficProfile]['num_pkts'],
                                             dst_vm_obj]  # dest_vm obj

        # Get the vrouter build version for logging purposes.
        BuildTag = get_OS_Release_BuildVersion(self)

        for each_profile in traffic_profiles:
            result = sdnFlowTest.generate_udp_flows_and_do_verification(
                self, traffic_profiles[each_profile], out, str(BuildTag))
            if result == False:
                return False
            self.logger.info(
                "Sleeping for 210 sec, for the flows to age out and get purged.")
            time.sleep(210)

        return True

    # end test_flow_single_project

    @preposttest_wrapper
    def test_flow_multi_projects(self):
        """Tests related to flow setup rate and flow table stability accross various triggers for verification
           accross VN's and accross multiple projects"""
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
        import sdn_flow_test_topo
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_flow_test_topo.sdn_flow_test_topo_multi_project

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

        # Create traffic based on traffic profile defined in topology.
        import analytics_performance_tests
        ana_obj = analytics_performance_tests.AnalyticsTestPerformance()
        ana_obj.setUp()
        traffic_profiles = {}
        count = 0
        num_ports_per_ip = 50000.00
        # forward flows = (total no. of flows / 2), so fwd_flow_factor = 2
        fwd_flow_factor = 2
        for TrafficProfile in topo_obj.traffic_profile:
            src_min_ip = 0
            src_max_ip = 0
            dst_ip = 0
            pkt_cnt = 0
            dst_min_port = 5000
            dst_max_port = 55000
            count += 1
            profile = 'profile' + str(count)
            src_vm = topo_obj.traffic_profile[TrafficProfile]['src_vm']
            src_vm_obj = None
            pkt_cnt = topo_obj.traffic_profile[TrafficProfile]['num_pkts']
            for proj in config_topo:
                for vm in config_topo[proj]:
                    for vm_name in config_topo[proj][vm]:
                        if topo_obj.traffic_profile[TrafficProfile]['dst_vm'] == vm_name:
                            dst_ip = config_topo[proj][vm][vm_name].vm_ip
                            dst_vm_obj = config_topo[proj][vm][vm_name]
                        if src_vm == vm_name:
                            src_vm_obj = config_topo[proj][vm][vm_name]

            prefix = topo_obj.vm_static_route_master[src_vm]
            ip_list = ana_obj.get_ip_list_from_prefix(prefix)
            no_of_ip = int(math.ceil(
                (topo_obj.traffic_profile[TrafficProfile]['num_flows'] / fwd_flow_factor) / num_ports_per_ip))
            forward_flows = topo_obj.traffic_profile[
                TrafficProfile]['num_flows'] / fwd_flow_factor
            result_dict = sdnFlowTest.src_min_max_ip_and_dst_max_port(
                self, ip_list, no_of_ip, dst_min_port, forward_flows)
            traffic_profiles[profile] = [src_vm_obj,  # src_vm obj
                                         # src_ip_min
                                         result_dict['src_min_ip'],
                                         # src_ip_max
                                         result_dict['src_max_ip'],
                                         dst_ip,  # dest_vm_ip
                                         dst_min_port,  # dest_port_min
                                         # dest_port_max
                                         result_dict['dst_max_port'],
                                         # packet_count
                                         topo_obj.traffic_profile[
                                             TrafficProfile]['num_pkts'],
                                         dst_vm_obj]  # dest_vm obj

        # Get the vrouter build version for logging purposes.
        BuildVersion = sdnFlowTest.get_vrouter_build_version(self)

        for each_profile in traffic_profiles:
            sdnFlowTest.generate_udp_flows_and_do_verification(
                self, traffic_profiles[each_profile], out, str(BuildVersion))
            self.logger.info(
                "Sleeping for 210 sec, for the flows to age out and get purged.")
            time.sleep(210)

        return True
    # end test_flow_multi_projects

# end sdnFlowTest
