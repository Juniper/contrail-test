from system_test.flow_tests.base import BaseFlowTest
#from common.contrail_test_init import ContrailTestInit
#from vn_test import *
#from quantum_test import *
#from vnc_api_test import *
#from nova_test import *
#from vm_test import *
from floating_ip import *
#from policy_test import *
#from contrail_fixtures import *
#from tcutils.agent.vna_introspect_utils import *
from tcutils.topo.topo_helper import *
from tcutils.wrappers import preposttest_wrapper
#from tcutils.commands import ssh, execute_cmd, execute_cmd_out
#from tcutils.topo.sdn_topo_setup import *
#from common.policy.get_version import *
#from common.system.system_verification import verify_system_parameters
#import sdn_flow_test_topo
#import traffic_tests
import time
import datetime
import threading
import socket
import flow_test_utils
from compute_node_test import ComputeNodeFixture
import system_test_topo
#import flow_test_topo
#import sdn_flow_test_topo_multiple_projects
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
#        for idx, si in enumerate(proj_topo.si_list):
#            self.logger.info("Starting tcpdump in mirror instance %s" % (si))
#            sessions = self.tcpdump_on_analyzer(si)
#            for svm_name, (session, pcap) in sessions.items():
#                out, msg = self.verify_mirror(svm_name, session, pcap)
#                self.logger.info(
#                    "Mirror check status in %s is %s" %
#                    (svm_name, out))
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
        #import pdb; pdb.set_trace()
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
        #import pdb; pdb.set_trace()
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
        #import pdb; pdb.set_trace()
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
        #import pdb; pdb.set_trace()
        result = False
        result = self.generate_udp_flows(
                     self.traffic_profiles['interVNinterNodeFIP'],
                     str(self.BuildTag))
        self.delete_agent_flows()
        if not result:
            return False

        return True

    # end test_interVNinterNodeFIP_flows
# end SDNFlowTests
