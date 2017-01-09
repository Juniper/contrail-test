from flow_tests.base import BaseFlowTest
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.agent.vna_introspect_utils import *
from tcutils.topo.topo_helper import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.topo.sdn_topo_setup import *
from common.policy.get_version import *
from common.system.system_verification import verify_system_parameters
import sdn_flow_test_topo
import traffic_tests
import time
import datetime
import threading
import socket
import flow_test_utils
from compute_node_test import ComputeNodeFixture
import system_test_topo
import flow_test_topo
import sdn_flow_test_topo_multiple_projects
from tcutils.test_lib.test_utils import assertEqual, get_ip_list_from_prefix
import math


class SDNFlowTests(BaseFlowTest, flow_test_utils.VerifySvcMirror):
    _interface = 'json'
    max_system_flows = 512000

    @classmethod
    def setUpClass(cls):
        super(SDNFlowTests, cls).setUpClass()
    # end setUpClass

    def cleanUp(self):
        super(SDNFlowTests, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    def set_flow_tear_time(self):
        # Get flow-cache_timeout from one node and use as reference...
        # Assumption is all nodes set to same value...
        cmp_node = self.inputs.compute_ips[0]
        self.agent_obj = self.useFixture(
            ComputeNodeFixture(
                self.connections,
                cmp_node))
        self.flow_cache_timeout = self.agent_obj.get_config_flow_aging_time()
        self.flow_teardown_time = 60
        self.time_to_retire_flows = int(
            self.flow_cache_timeout) + self.flow_teardown_time

    def delete_agent_flows(self):
        for comp_node in self.inputs.compute_ips:
            comp_node_fixt = self.useFixture(
                ComputeNodeFixture(self.connections, comp_node))
            self.logger.info(
                "flows now in %s: %s" %
                (comp_node, comp_node_fixt.get_vrouter_flow_count()))
            comp_inspect = self.agent_inspect[comp_node]
            comp_inspect.delete_all_flows()
            self.logger.info(
                "flows after deleting in %s: %s" %
                (comp_node, comp_node_fixt.get_vrouter_flow_count()))
        self.logger.info("wait for 10 secs for the flows to tear down")
        time.sleep(10)

    # get source min, max ip's and destination max port.
    def src_min_max_ip_and_dst_max_port(
            self,
            ips,
            no_of_ip,
            dst_min_port,
            flows):
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

    def create_traffic_profiles(self, topo_obj, config_topo):

        # Create traffic based on traffic profile defined in topology.
        traffic_profiles = {}
        count = 0
        num_ports_per_ip = 50000.00
        # forward flows = (total no. of flows / 2), so fwd_flow_factor = 2
        fwd_flow_factor = 2
        for profile, data in topo_obj.traffic_profile.items():
            src_min_ip = 0
            src_max_ip = 0
            dst_ip = 0
            pkt_cnt = 0
            dst_min_port = 5000
            dst_max_port = 55000
            count += 1
            profile = 'profile' + str(count)
            src_vm = data['src_vm']
            src_vm_obj = None
            dst_vm_obj = None
            pkt_cnt = data['num_pkts']
            for proj in config_topo:
                for vm in config_topo[proj]:
                    for vm_name in config_topo[proj][vm]:
                        if data['dst_vm'] == vm_name:
                            dst_ip = config_topo[proj][vm][vm_name].vm_ip
                            dst_vm_obj = config_topo[proj][vm][vm_name]
                        if src_vm == vm_name:
                            src_vm_obj = config_topo[proj][vm][vm_name]

            prefix = topo_obj.vm_static_route_master[src_vm]
            ip_list = get_ip_list_from_prefix(prefix)
            no_of_ip = int(
                math.ceil(
                    (data['num_flows'] /
                     fwd_flow_factor) /
                    num_ports_per_ip))
            forward_flows = data['num_flows'] / fwd_flow_factor
            result_dict = self.src_min_max_ip_and_dst_max_port(
                ip_list, no_of_ip, dst_min_port, forward_flows)
            if int(no_of_ip) == 1:
                # Use the src VM IP to create the flows no need of static IP's
                # that have been provisioned to the VM route table.
                traffic_profiles[profile] = [src_vm_obj,
                                             src_vm_obj.vm_ip,  # src_ip_min
                                             src_vm_obj.vm_ip,  # src_ip_max
                                             dst_ip,  # dest_vm_ip
                                             dst_min_port,  # dest_port_min
                                             # dest_port_max
                                             result_dict['dst_max_port'],
                                             data['num_pkts'], dst_vm_obj]
            else:
                # Use thestatic IP's that have been provisioned to the VM route
                # table as src IP range.
                traffic_profiles[profile] = [src_vm_obj,
                                             # src_ip_min
                                             result_dict['src_min_ip'],
                                             # src_ip_max
                                             result_dict['src_max_ip'],
                                             dst_ip,  # dest_vm_ip
                                             dst_min_port,  # dest_port_min
                                             # dest_port_max
                                             result_dict['dst_max_port'],
                                             data['num_pkts'], dst_vm_obj]
        return traffic_profiles

    # end create_traffic_profiles

    def start_traffic(
            self,
            vm,
            src_min_ip='',
            src_max_ip='',
            dest_ip='',
            dest_min_port='',
            dest_max_port='',
            pkt_cnt=''):
        """ This routine is for generation of UDP flows using pktgen. Only UDP packets are generated using this routine.
        """
        self.logger.info("Sending traffic...")
        try:
            cmd = '~/flow_test_pktgen.sh %s %s %s %s %s %s' % (
                src_min_ip, src_max_ip, dest_ip, dest_min_port, dest_max_port, pkt_cnt)
            self.logger.info("Traffic cmd: %s" % (cmd))
            vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        except Exception as e:
            self.logger.exception("Got exception at start_traffic as %s" % (e))
    # end start_traffic

    def generate_udp_flows_and_do_verification(
            self,
            traffic_profile,
            build_version):
        """ Routine to generate UDP flows by calling the start_traffic routine in a thread and do parallel verification of
            flow setup rate.
            @inputs :
            traffic_profile - a list of traffic generation parameters as explained in test_flow_single_project and test_flow_multi_project routines.
            build_version - os_version, release_version and build_version for logging purposes.
        """
        for cmp_node in self.inputs.compute_ips:
            comp_node_fixt = self.useFixture(ComputeNodeFixture(
                    self.connections, cmp_node))
            flows_now = comp_node_fixt.get_vrouter_flow_count()
            for action, count in flows_now.iteritems():
                # Any flows set by previous traffic tests should have retired
                # by now..
                if int(count) > 1000:
                    self.logger.error(
                        "unexpected flow count of %s with action as %s" %
                        (count, action))
                    return False

        Shost = socket.gethostbyaddr(traffic_profile[0].vm_node_ip)
        Dhost = socket.gethostbyaddr(traffic_profile[7].vm_node_ip)
        self.logger.info(
            "Src_VM = %s, Src_IP_Range = %s to %s, Dest_VM = %s, Dest_IP = %s, Src_VN = %s, Dest_VN = %s,"
            " Port_Range = %s to %s, Src_Node = %s, Dst_Node = %s." %
            (traffic_profile[0].vm_name,
             traffic_profile[1],
             traffic_profile[2],
             traffic_profile[7].vm_name,
             traffic_profile[3],
             traffic_profile[0].vn_name,
             traffic_profile[7].vn_name,
             traffic_profile[4],
             traffic_profile[5],
             Shost[0],
                Dhost[0]))

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
        RelVer = build_version.split('-')[1]
        import ReleaseToFlowSetupRateMapping
        #from ReleaseToFlowSetupRateMapping import *
        try:
            DefinedSetupRate = ReleaseToFlowSetupRateMapping.expected_flow_setup_rate['policy'][RelVer]
        except KeyError:
            # A default value of 7K flows per second is set.
            DefinedSetupRate = default_setup_rate

        #
        # Set Expected NAT Flow Rate
        if PolNatSI == 'NAT Flow':
            DefinedSetupRate = ReleaseToFlowSetupRateMapping.expected_flow_setup_rate['nat'][RelVer]
        #
        # The flow setup rate is calculated based on setup time required for first 100K flows. So TotalFlows is set to 100K and 5
        # samples (NoOfIterations) are taken within the time required to setup 100K flows. The time interval (sleep_interval) is
        # calculated based on DefinedSetupRate for the particular release
        # version.
        TotalFlows = 100000
        NoOfIterations = 5
        sleep_interval = (float(TotalFlows) / float(DefinedSetupRate)) / \
            float(NoOfIterations)

        # For scaled flows & low profile VM, it takes time for VM/tool to start sending packets...
        #self.logger.info("Sleeping for 20 sec, for VM to start sending packets.")
        #time.sleep(20)
        #
        # After each sleep_interval we get the number of active forward or nat flows setup on the vrouter which is repeated for
        # NoOfIterations times. and the average is calculated in each
        # iteration.
        for ind in range(NoOfIterations):
            time.sleep(sleep_interval)
            flows_now = flow_test_utils.vm_vrouter_flow_count(src_vm_obj)
            NoOfFlows.append(flows_now)
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
            self.logger.info("Flow samples so far: %s" % (NoOfFlows))
            self.logger.info(" ")
            if flows_now > 90000:
                self.logger.info("Flows setup so far: %s" % (flows_now))
                self.logger.info("Close to 100k flows setup, no need to wait")
                break

        # @setup rate of 9000 flows per sec, 30*9000=270k flows can be setup
        # with ~10s over with above loop, wait for another 20s
        # self.logger.info("Sleeping for 20 sec, for all the flows to be setup.")
        # time.sleep(20)
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
        # if source and destination VN are same then it's not a NAT/Policy flow
        # else it is a NAT/Policy flow and needs to be logged accordingly.
        if src_vm_obj.vn_name == dst_vm_obj.vn_name:
            mystr = "%s\t%s\t%s\t%s\t%s\n" % (
                build_version, mtime, Shost[0], AverageFlowSetupRate, localflow)
        else:
            mystr = "%s\t%s\t%s\t%s\t%s\t%s\n" % (
                build_version, mtime, Shost[0], AverageFlowSetupRate, localflow, PolNatSI)

        fh.write(mystr)
        fh.close()

        self.logger.info("Joining thread")
        th.join()

        #
        # Fail the test if the actual flow setup rate is < 70% of the defined
        # flow setup rate for the release.
        if (AverageFlowSetupRate < (0.6 * DefinedSetupRate)):
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

    def generate_udp_flows(self, traffic_profile, build_version):
        """ Routine to generate UDP flows by calling the start_traffic routine in a thread ..
            @inputs :
            traffic_profile - a list of traffic generation parameters as explained in test_flow_single_project and test_flow_multi_project routines.
        """
        Shost = socket.gethostbyaddr(traffic_profile[0].vm_node_ip)
        Dhost = socket.gethostbyaddr(traffic_profile[7].vm_node_ip)
        self.logger.info(
            "Src_VM = %s, Src_IP_Range = %s to %s, Dest_VM = %s, Dest_IP = %s, Src_VN = %s, Dest_VN = %s,"
            " Port_Range = %s to %s, Src_Node = %s, Dst_Node = %s." %
            (traffic_profile[0].vm_name,
             traffic_profile[1],
             traffic_profile[2],
             traffic_profile[7].vm_name,
             traffic_profile[3],
             traffic_profile[0].vn_name,
             traffic_profile[7].vn_name,
             traffic_profile[4],
             traffic_profile[5],
             Shost[0],
                Dhost[0]))

        th = threading.Thread(
            target=self.start_traffic, args=(
                traffic_profile[0], traffic_profile[1], traffic_profile[2],
                traffic_profile[3], traffic_profile[
                    4], traffic_profile[
                    5],
                traffic_profile[6]))
        th.start()

        # single project topo, retrieve topo obj for the project
        # Need to specify the project which has mirror service instance..
        proj_topo = self.topo.values()[0]
        for idx, si in enumerate(proj_topo.si_list):
            self.logger.info("Starting tcpdump in mirror instance %s" % (si))
            sessions = self.tcpdump_on_analyzer(si)
            for svm_name, (session, pcap) in sessions.items():
                out, msg = self.verify_mirror(svm_name, session, pcap)
                self.logger.info(
                    "Mirror check status in %s is %s" %
                    (svm_name, out))
        src_vm_obj = traffic_profile[0]
        NoOfFlows = flow_test_utils.vm_vrouter_flow_count(src_vm_obj)
        self.logger.info("No. of flows in source compute is %s" % (NoOfFlows))

        self.logger.info("Joining thread")
        th.join()

        #
        # Fail the test if flows are not generated, use 5-tuple check and not
        # vrouter flow count with flow -l

        return True
    # end generate_udp_flows

    @preposttest_wrapper
    def test_flow_single_project(self):
        """Tests related to flow setup rate and flow table stability accross various triggers for verification
           accross VN's within a single project"""
        result = True
        #self.agent_objs = {}
        #self.set_flow_tear_time()
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
        topology_class_name = flow_test_topo.systest_topo_single_project
        # mini topo for testing script
        # topology_class_name = mini_flow_test_topo.systest_topo_single_project
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))

        topo = topology_class_name(
            compute_node_list=self.inputs.compute_ips)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm':
        # vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data'][0], out['data'][1]
        proj = list(topo.keys())[0]

        # Get the vrouter build version for logging purposes.
        BuildTag = get_OS_Release_BuildVersion(self)

        # Create traffic profile with all details like IP addresses, port
        # numbers and no of flows, from the profile defined in the topology.
        traffic_profiles = self.create_traffic_profiles(
            topo[proj],
            config_topo)

        self.topo, self.config_topo = topo, config_topo
        for each_profile in traffic_profiles:
            result = self.generate_udp_flows_and_do_verification(
                traffic_profiles[each_profile], str(BuildTag))
            # verify_system_parameters(self, out)
            self.delete_agent_flows()
            if not result:
                 False

        return True

    # end test_flow_single_project

    @preposttest_wrapper
    def test_system_single_project(self):
        """Basic systest with single project with many features & traffic..
        """
        result = True
        #self.agent_objs = {}
        #self.set_flow_tear_time()
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
        topology_class_name = system_test_topo.systest_topo_single_project
        # For testing script, use mini topology
        # topology_class_name =
        # mini_system_test_topo.systest_topo_single_project
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))

        topo = topology_class_name(
            compute_node_list=self.inputs.compute_ips)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm':
        # vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data'][0], out['data'][1]
        proj = list(topo.keys())[0]

        # Get the vrouter build version for logging purposes.
        BuildTag = get_OS_Release_BuildVersion(self)

        # Create traffic profile with all details like IP addresses, port
        # numbers and no of flows, from the profile defined in the topology.
        traffic_profiles = self.create_traffic_profiles(
            topo[proj],
            config_topo)

        self.topo, self.config_topo = topo, config_topo
        for each_profile in traffic_profiles:
            result = self.generate_udp_flows(
                traffic_profiles[each_profile], str(BuildTag))
            #verify_system_parameters(self, out)
            self.delete_agent_flows()
            if not result:
                return False

        return True

    # end test_system_single_project

    @preposttest_wrapper
    def test_flow_multi_projects(self):
        """Tests related to flow setup rate and flow table stability accross various triggers for verification
           accross VN's and accross multiple projects"""
        result = True
        self.comp_node_fixt = {}
        for cmp_node in self.inputs.compute_ips:
            self.comp_node_fixt[cmp_node] = self.useFixture(ComputeNodeFixture(
                self.connections, cmp_node))
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
        msg = []
        topology_class_name = sdn_flow_test_topo_multiple_projects.multi_project_topo

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        #
        # Create a list of compute node IP's and pass it to topo if you want to pin
        # a vm to a particular node
        topo = topology_class_name(
            compute_node_list=self.inputs.compute_ips)
        #
        # 1. Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm':
        # vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        assertEqual(out['result'], True, out['msg'])
        self.topo, self.config_topo = out['data'][0], out['data'][1]
        self.proj = list(self.topo.keys())[0]
        # 2. Start Traffic
        for profile, details in self.topo[self.proj].traffic_profile.items():
            self.logger.info("Profile under test: %s, details: %s" %(profile, details))
            self.src_vm = details['src_vm']
            self.dst_vm = details['dst_vm']
            self.src_proj = details['src_proj']
            self.dst_proj = details['dst_proj']
            # Not flow scaling test, limit num_flows to low number..
            num_flows = 15000
            self.generated_flows = 2*num_flows
            self.flow_gen_rate = 1000
            src_vm_fixture = self.config_topo[self.src_proj]['vm'][self.src_vm]
            src_vm_vn = src_vm_fixture.vn_names[0]
            src_vm_vn_fix = self.config_topo[self.src_proj]['vn'][src_vm_vn]
            dst_vm_fixture = self.config_topo[self.dst_proj]['vm'][self.dst_vm]
            self.proto = 'udp'
            self.cmp_node = src_vm_fixture.vm_node_ip
            self.comp_node_fixt[self.cmp_node].get_config_per_vm_flow_limit()
            self.comp_node_fixt[self.cmp_node].get_config_flow_aging_time()
            self.max_vm_flows = self.comp_node_fixt[self.cmp_node].max_vm_flows
            self.flow_cache_timeout = self.comp_node_fixt[self.cmp_node].flow_cache_timeout
            self.traffic_obj = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (tx_vm_fixture= None, rx_vm_fixture= None,
            # stream_proto= 'udp', start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus = self.traffic_obj.startTraffic(
                total_single_instance_streams=num_flows,
                pps=self.flow_gen_rate,
                start_sport=1000,
                cfg_profile='ContinuousSportRange',
                tx_vm_fixture=src_vm_fixture,
                rx_vm_fixture=dst_vm_fixture,
                stream_proto=self.proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                self.proto, src_vm_fixture.vm_ip, startStatus['status'])
            self.logger.info(msg1)
            assert startStatus['status'], msg1
            # 3. Poll live traffic & verify VM flow count
            self.verify_node_flow_setup()
            # 4. Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.traffic_obj.stopTraffic(wait_for_stop=False)
            start_time = time.time()
            # 5. Verify flow ageing
            self.logger.info(
                "With traffic stopped, wait for flow_cache_timeout to trigger flow ageing")
            sleep(self.flow_cache_timeout)
            while True:
                begin_flow_count = self.comp_node_fixt[
                    self.cmp_node].get_vrouter_matching_flow_count(
                    self.flow_data)
                self.logger.debug('begin_flow_count: %s' %(begin_flow_count))
                if begin_flow_count['all'] == 0:
                    break
                flow_teardown_time = math.ceil(flow_test_utils.get_max_flow_removal_time(begin_flow_count['all'], self.flow_cache_timeout))
                # flow_teardown_time is not the actual time to remove flows
                # Based on flow_count at this time, teardown_time is calculated to the value
                # which will vary with agent's poll, which is done at regular intervals..
                self.logger.info('Sleeping for %s secs' %(flow_teardown_time))
                sleep(flow_teardown_time)
                # at the end of wait, actual_flows should be atleast < 50% of total flows before start of teardown
                current_flow_count = self.comp_node_fixt[
                    self.cmp_node].get_vrouter_matching_flow_count(
                    self.flow_data)
                self.logger.debug('current_flow_count: %s' %(current_flow_count))
                if current_flow_count['all'] > (0.5*begin_flow_count['all']):
                    msg = ['Flow removal not happening as expected in node %s' %self.cmp_node]
                    msg.append('Flow count before wait: %s, after wait of %s secs, its: %s' %
                        (begin_flow_count['all'], flow_teardown_time, current_flow_count['all']))
                    assert False, msg
                if current_flow_count['all'] < (0.1*begin_flow_count['all']):
                    break
            # end of while loop
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Flows aged out as expected in configured flow_cache_timeout")
        # end of profile for loop
        return True
    # end test_flow_multi_projects

    def reset_vm_flow_limit_and_stop_traffic(self):
        self.max_vm_flows = 100
        self.comp_node_fixt[
            self.cmp_node].set_per_vm_flow_limit(
            self.max_vm_flows)
        self.comp_node_fixt[self.cmp_node].sup_vrouter_process_restart()
        self.traffic_obj.stopTraffic(wait_for_stop=False)

    def verify_node_flow_setup(self):
        '''Written for agent params test to test flow setup data
        generated_flows: generated by tool
        allowed_flows: set by max_vm_flows value in agent conf
        expected_flows: expected non FlowLimited flows based on above 2 values
        '''
        self.flow_data = flow_test_utils.get_flow_data(
            self.config_topo,
            self.src_vm,
            self.dst_vm,
            self.proto,
            self.src_proj,
            self.dst_proj)
        self.logger.info(
            "Received flow_data for checking: %s" %
            self.flow_data)
        self.comp_node_fixt[
            self.cmp_node].get_vrouter_flow_count()
        # keep generated flow info for processing flow removal
        allowed_flows = int(
            float(self.max_system_flows) * (float(self.max_vm_flows) / 100))
        self.logger.info(
            "In node %s, allowed_flows is set to %s" %
            (self.cmp_node, allowed_flows))
        if self.generated_flows < allowed_flows:
            expected_flows = self.generated_flows
            # assert if flows_beyond_limit found, as we don't expect to see
            flow_limit_assert = False
        else:
            expected_flows = allowed_flows
            # don't assert if flows_beyond_limit found, as we expect to see
            flow_limit_assert = True
        node_flow_data = self.comp_node_fixt[
            self.cmp_node].get_vrouter_matching_flow_count(self.flow_data)
        actual_flows = int(node_flow_data['allowed'])
        retries = 0
        retry_wait_time = 2
        max_retries = math.ceil(self.generated_flows / self.flow_gen_rate)
        while retries < max_retries and actual_flows < expected_flows:
            self.logger.info(
                "Wait for flows to be setup completely, flows so far: %s, expected: %s" %
                (actual_flows, expected_flows))
            sleep(retry_wait_time)
            retries += 1
            node_flow_data = self.comp_node_fixt[
                self.cmp_node].get_vrouter_matching_flow_count(self.flow_data)
            actual_flows = int(node_flow_data['allowed'])
        diff_flows = actual_flows - expected_flows
        # allow 5% diff on upper side..
        allowed_upper_threshold = expected_flows * 0.05
        if diff_flows > allowed_upper_threshold:
            msg = "Seeing more flows in system than expected - node: %s, expected_flows: %s, actual_flows: %s" % (
                self.cmp_node, expected_flows, actual_flows)
            self.reset_vm_flow_limit_and_stop_traffic()
            assert False, msg
        # allow 5% diff on lower side..
        allowed_lower_threshold = expected_flows * 0.05
        if diff_flows < -allowed_lower_threshold:
            msg = "Don't see expected flows in node %s, expected_flows: %s, actual_flows: %s" % (
                self.cmp_node, expected_flows, actual_flows)
            self.reset_vm_flow_limit_and_stop_traffic()
            assert False, msg
        else:
            self.logger.info(
                "Flow count good as configured.., expected %s, actual %s" %
                (expected_flows, actual_flows))
        # If generated_flows < allowed_flows, flows_beyond_limit is not
        # expected..
        flows_beyond_limit = int(node_flow_data['dropped_by_limit'])
        if flows_beyond_limit > 0:
            msg = "Seeing dropped flows due to FlowLimit in system than expected - node: %s, flows_beyond_limit: %s, allowed_flows: %s" % (
                self.cmp_node, flows_beyond_limit, allowed_flows)
            assert flow_limit_assert, msg
        else:
            self.logger.info(
                "Dont see Flow Limited Dropped flows as expected, flow limited drop count is %s.." %
                flows_beyond_limit)

    @preposttest_wrapper
    def test_agent_flow_settings(self):
        """Basic systest with single project with many features & traffic..
        """
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
        # import mini_flow_test_topo
        # topology_class_name = mini_flow_test_topo.systest_topo_single_project
        topology_class_name = flow_test_topo.systest_topo_single_project
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))

        topo = topology_class_name(
            compute_node_list=self.inputs.compute_ips)
        #
        # 1. Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm':
        # vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            config_topo = out['data'][1]
        self.proj = list(config_topo.keys())[0]
        self.topo, self.config_topo = topo, config_topo

        # 2. set agent flow_cache_timeout to 60s
        # set max_vm_flows to 1% of 500k, comes to 5000
        self.comp_node_fixt = {}
        self.flow_cache_timeout = 60
        for cmp_node in self.inputs.compute_ips:
            self.comp_node_fixt[cmp_node] = self.useFixture(ComputeNodeFixture(
                self.connections, cmp_node))
            self.comp_node_fixt[cmp_node].set_flow_aging_time(
                self.flow_cache_timeout)
            self.comp_node_fixt[cmp_node].sup_vrouter_process_restart()

        # 3. Start Traffic
        for profile, details in self.topo.traffic_profile.items():
            self.logger.info("Profile under test: %s, details: %s" %(profile, details))
            self.src_vm = details['src_vm']
            self.dst_vm = details['dst_vm']
            self.src_proj = self.proj
            self.dst_proj = self.proj
            # Set num_flows to fixed, smaller value but > 1% of
            # system max flows
            num_flows = 5555
            self.generated_flows = 2*num_flows
            self.flow_gen_rate = 1000
            src_vm_fixture = self.config_topo[self.proj]['vm'][self.src_vm]
            src_vm_vn = src_vm_fixture.vn_names[0]
            src_vm_vn_fix = self.config_topo[self.proj]['vn'][src_vm_vn]
            dst_vm_fixture = self.config_topo[self.proj]['vm'][self.dst_vm]
            self.proto = 'udp'
            self.cmp_node = src_vm_fixture.vm_node_ip
            # 3a. Set max_vm_flows to 1% in TX VM node
            self.max_vm_flows = 1
            self.comp_node_fixt[
                self.cmp_node].set_per_vm_flow_limit(
                self.max_vm_flows)
            self.comp_node_fixt[self.cmp_node].sup_vrouter_process_restart()
            self.logger.info(
                "Wait for 2s for flow setup to start after service restart")
            sleep(2)
            flow_test_utils.update_vm_mdata_ip(self.cmp_node, self)
            self.traffic_obj = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (tx_vm_fixture= None, rx_vm_fixture= None,
            # stream_proto= 'udp', start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus = self.traffic_obj.startTraffic(
                total_single_instance_streams=num_flows,
                pps=self.flow_gen_rate,
                start_sport=1000,
                cfg_profile='ContinuousSportRange',
                tx_vm_fixture=src_vm_fixture,
                rx_vm_fixture=dst_vm_fixture,
                stream_proto=self.proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                self.proto, src_vm_fixture.vm_ip, startStatus['status'])
            self.logger.info(msg1)
            assert startStatus['status'], msg1
            # 4. Poll live traffic & verify VM flow count
            self.verify_node_flow_setup()
            # 5. Increase max_vm_flows to 50% in TX VM node
            self.max_vm_flows = 50
            self.comp_node_fixt[
                self.cmp_node].set_per_vm_flow_limit(
                self.max_vm_flows)
            self.comp_node_fixt[self.cmp_node].sup_vrouter_process_restart()
            self.logger.info(
                "Wait for 2s for flow setup to start after service restart")
            sleep(2)
            # 6. Poll live traffic
            self.verify_node_flow_setup()
            # 7. Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.traffic_obj.stopTraffic(wait_for_stop=False)
            start_time = time.time()
            # 8. Verify flow ageing
            self.logger.info(
                "With traffic stopped, wait for flow_cache_timeout to trigger flow ageing")
            sleep(self.flow_cache_timeout)
            retries = 0
            retry_wait_time = 10
            flow_teardown_time = math.ceil(flow_test_utils.get_max_flow_removal_time(self.generated_flows, self.flow_cache_timeout))
            self.logger.debug("flow tear down time based on calcualtion: %s" %flow_teardown_time)
            max_retries = math.ceil(self.flow_cache_timeout / retry_wait_time)
            while retries < max_retries:
                actual_flows = self.comp_node_fixt[
                    self.cmp_node].get_vrouter_matching_flow_count(
                    self.flow_data)
                actual_flows = int(actual_flows['all'])
                if actual_flows > 10:
                    self.logger.info("Waiting for flows to age out")
                    sleep(retry_wait_time)
                    retries += 1
                else:
                    break
            elapsed_time = time.time() - start_time
            if actual_flows > 50:
                msg = "Expected flows to age-out as configured, Seeing flows still active after elapsed time %s in node: %s, actual_flows: %s" % (
                    elapsed_time, self.cmp_node, actual_flows)
                assert False, msg
            else:
                self.logger.info(
                    "Flows aged out as expected in configured flow_cache_timeout")
                self.logger.info(
                    "elapsed_time after stopping traffic is %s, flow_count is %s" %
                    (elapsed_time, actual_flows))
        # end of profile for loop
    # end of test_agent_flow_settings
# end SDNFlowTests
