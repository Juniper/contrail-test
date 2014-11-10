from system_test.flow_tests.base import BaseFlowTest
from floating_ip import *
from tcutils.topo.topo_helper import *
from tcutils.wrappers import preposttest_wrapper
import traffic_tests
import time
import datetime
import threading
import socket
import flow_test_utils
from compute_node_test import ComputeNodeFixture
import system_test_topo
import sdn_flow_test_topo_multiple_projects
from tcutils.test_lib.test_utils import assertEqual, get_ip_list_from_prefix
import math
from system_flows_config import config_topo_single_proj


class TestFlowSingleProj(BaseFlowTest, flow_test_utils.VerifySvcMirror):
    _interface = 'json'
    max_system_flows = 512000

    @classmethod
    def setUpClass(self):
        super(TestFlowSingleProj, self).setUpClass()
        config_topo_single_proj(TestFlowSingleProj,
                                system_test_topo.systest_topo_single_project)
    # end setUpClass

    @classmethod
    def tearDownClass(self):
        if self.inputs.fixture_cleanup == 'yes':
            self.config_setup_obj.cleanUp()
        else:
            self.logger.info('Skipping topology config cleanup')
        super(TestFlowSingleProj, self).cleanUp()
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

    def generate_udp_flows(self, traffic_profile, build_version):
        """ Routine to generate UDP flows by calling the start_traffic routine in a thread ..
            @inputs :
            traffic_profile - a list of traffic generation parameters as explained in
            test_system_flow_single_project and test_system_flow_multi_project routines.
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
    def test_intraVNintraNode_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['intraVNintraNode'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False
        return True

    # end test_intraVNintraNode_flows

    @preposttest_wrapper
    def test_intraVNinterNode_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['intraVNinterNode'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_intraVNinterNode_flows

    @preposttest_wrapper
    def test_interVNintraNodePol_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['interVNintraNodePol'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_interVNintraNodePol_flows

    @preposttest_wrapper
    def test_interVNinterNodePol_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['interVNinterNodePol'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_interVNinterNodePol_flows

    @preposttest_wrapper
    def test_interVNintraNodeFIP_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['interVNintraNodeFIP'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_interVNintraNodeFIP_flows

    @preposttest_wrapper
    def test_interVNinterNodeFIP_flows(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
        result = self.generate_udp_flows(
            self.traffic_profiles['interVNinterNodeFIP'],
            str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_interVNinterNodeFIP_flows
# end TestFlowSingleProj


class TestFlowMultiProj(BaseFlowTest, flow_test_utils.VerifySvcMirror):
    _interface = 'json'
    max_system_flows = 512000

    @classmethod
    def setUpClass(self):
        super(TestFlowMultiProj, self).setUpClass()
        config_topo_single_proj(
            TestFlowMultiProj,
            sdn_flow_test_topo_multiple_projects.multi_project_topo,
            create_traffic_profile=False)
    # end setUpClass

    @classmethod
    def tearDownClass(self):
        if self.inputs.fixture_cleanup == 'yes':
            self.config_setup_obj.cleanUp()
        else:
            self.logger.info('Skipping topology config cleanup')
        super(TestFlowMultiProj, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    def traffic_setup(self, profile, details, num_flows, flow_gen_rate, proto):
        self.logger.info(
            "Profile under test: %s, details: %s" %
            (profile, details))
        self.src_vm = details['src_vm']
        self.dst_vm = details['dst_vm']
        self.src_proj = details['src_proj']
        self.dst_proj = details['dst_proj']
        # Not flow scaling test, limit num_flows to low number..
        self.generated_flows = 2 * num_flows
        self.flow_gen_rate = flow_gen_rate
        self.src_vm_fixture = self.config_topo[
            self.src_proj]['vm'][
            self.src_vm]
        src_vm_vn = self.src_vm_fixture.vn_names[0]
        src_vm_vn_fix = self.config_topo[self.src_proj]['vn'][src_vm_vn]
        self.dst_vm_fixture = self.config_topo[
            self.dst_proj]['vm'][
            self.dst_vm]
        self.proto = proto
        self.cmp_node = self.src_vm_fixture.vm_node_ip
        self.comp_node_fixt[self.cmp_node].get_config_per_vm_flow_limit()
        self.comp_node_fixt[self.cmp_node].get_config_flow_aging_time()
        self.max_vm_flows = self.comp_node_fixt[self.cmp_node].max_vm_flows
        self.flow_cache_timeout = self.comp_node_fixt[
            self.cmp_node].flow_cache_timeout

    # end traffic_setup

    @preposttest_wrapper
    def test_flow_multi_projects(self):
        """Tests related to flow setup rate and flow table stability accross
           various triggers for verification accross VN's and accross multiple
           projects.
        """
        result = True
        self.comp_node_fixt = {}
        for cmp_node in self.inputs.compute_ips:
            self.comp_node_fixt[cmp_node] = self.useFixture(ComputeNodeFixture(
                self.connections, cmp_node))

        # 1. Start Traffic
        num_flows = 15000
        flow_gen_rate = 1000
        proto = 'udp'
        profile = 'TrafficProfile1'
        details = self.topo[self.topo.keys()[0]].traffic_profile[profile]
        self.traffic_setup(profile, details, num_flows, flow_gen_rate, proto)
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
            tx_vm_fixture=self.src_vm_fixture,
            rx_vm_fixture=self.dst_vm_fixture,
            stream_proto=self.proto)

        msg1 = "Status of start traffic : %s, %s, %s" % (
            self.proto, self.src_vm_fixture.vm_ip, startStatus['status'])
        self.logger.info(msg1)
        assert startStatus['status'], msg1
        # 2. Poll live traffic & verify VM flow count
        flow_test_utils.verify_node_flow_setup(self)
        # 3. Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.traffic_obj.stopTraffic(wait_for_stop=False)
        start_time = time.time()
        # 4. Verify flow ageing
        self.logger.info(
            "With traffic stopped, wait for flow_cache_timeout to trigger flow ageing")
        sleep(self.flow_cache_timeout)
        while True:
            begin_flow_count = self.comp_node_fixt[
                self.cmp_node].get_vrouter_matching_flow_count(
                self.flow_data)
            self.logger.debug('begin_flow_count: %s' % (begin_flow_count))
            if begin_flow_count['all'] == 0:
                break
            flow_teardown_time = math.ceil(
                flow_test_utils.get_max_flow_removal_time(
                    begin_flow_count['all'],
                    self.flow_cache_timeout))
            # flow_teardown_time is not the actual time to remove flows
            # Based on flow_count at this time, teardown_time is calculated to the value
            # which will vary with agent's poll, which is done at regular
            # intervals..
            self.logger.info('Sleeping for %s secs' % (flow_teardown_time))
            sleep(flow_teardown_time)
            # at the end of wait, actual_flows should be atleast < 50% of total
            # flows before start of teardown
            current_flow_count = self.comp_node_fixt[
                self.cmp_node].get_vrouter_matching_flow_count(
                self.flow_data)
            self.logger.debug('current_flow_count: %s' % (current_flow_count))
            if current_flow_count['all'] > (0.5 * begin_flow_count['all']):
                msg = [
                    'Flow removal not happening as expected in node %s' %
                    self.cmp_node]
                msg.append(
                    'Flow count before wait: %s, after wait of %s secs, its: %s' %
                    (begin_flow_count['all'],
                     flow_teardown_time,
                     current_flow_count['all']))
                assert False, msg
            if current_flow_count['all'] < (0.1 * begin_flow_count['all']):
                break
        # end of while loop
        elapsed_time = time.time() - start_time
        self.logger.info(
            "Flows aged out as expected in configured flow_cache_timeout")
        return True
    # end test_flow_multi_projects

# end TestFlowMultiProj
