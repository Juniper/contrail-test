from serial_scripts.system_test.flow_tests.base import BaseFlowTest
from tcutils.topo.topo_helper import *
from tcutils.wrappers import preposttest_wrapper
import time
import datetime
import threading
import socket
import flow_test_utils
from compute_node_test import ComputeNodeFixture
import flow_scale_topo
from tcutils.test_lib.test_utils import assertEqual, get_ip_list_from_prefix
import math
from tcutils.topo.sdn_topo_setup import *


class TestFlowScaling(BaseFlowTest):
    _interface = 'json'
    max_system_flows = 512000

    @classmethod
    def setUpClass(cls):
        super(TestFlowScaling, cls).setUpClass()
    # end setUpClass

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
            pkt_cnt='',
            dst_mac_addr='00:00:5e:00:01:00'):
        """ This routine is for generation of UDP flows using pktgen. Only UDP packets are generated using this routine.
        """
        self.logger.info("Sending traffic...")
        try:
            cmd = '~/flow_test_pktgen.sh %s %s %s %s %s %s %s' % (
                src_min_ip, src_max_ip, dest_ip, dest_min_port,
                dest_max_port, pkt_cnt, dst_mac_addr)
            self.logger.info("Traffic cmd: %s" % (cmd))
            vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        except Exception as e:
            self.logger.exception("Got exception at start_traffic as %s" % (e))
    # end start_traffic

    def create_scaled_flows(self):
        """ Routine to generate UDP flows by calling the start_traffic routine in a thread ..
            @inputs :
            traffic_profile - a list of traffic generation parameters as explained in
            test_system_flow_single_project and test_system_flow_multi_project routines.
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

            src_min_ip='',
            src_max_ip='',
            dest_ip='',
            dest_min_port='',
            dest_max_port='',
            pkt_cnt='',

        th = threading.Thread(
            target=self.start_traffic, args=(
            self.traffic_scenarios['1to2'][0],
            '111.1.0.10',
            '111.1.0.110',
            self.traffic_scenarios['1to2'][3],
            '5000',
            '55000',
            self.traffic_scenarios['1to2'][6],
            self.traffic_scenarios['1to2'][8]))

        #import pdb; pdb.set_trace()
        th.start()

        #import pdb; pdb.set_trace()
        #time.sleep(5)
        FlowCountList = []
        src_vm_obj = self.traffic_scenarios['1to2'][0] 
        from datetime import datetime
        self.logger.info(datetime.now().time())
        for index in range(240):
            FlowCountList.append(flow_test_utils.vm_vrouter_flow_count(src_vm_obj))
            time.sleep(0.9)
        self.logger.info(datetime.now().time())

        # single project topo, retrieve topo obj for the project
        # Need to specify the project which has mirror service instance..
        self.logger.info("Joining thread")
        th.join()
        FlowCountList.sort(reverse=True)
        self.logger.info("No. of flows in source compute of vm %s is %s" % (
                                                     src_vm_obj.vm_name,
                                                     FlowCountList[0]))
        #import pdb; pdb.set_trace()
        return True
    # end create_scaled_flows

    def build_traffic_scenarios(self, topo, config_topo):

        # Create traffic based on traffic profile defined in topology.
        traffic_scenarios = {}
        count = 0
        num_ports_per_ip = 50000.00
        # forward flows = (total no. of flows / 2), so fwd_flow_factor = 2
        fwd_flow_factor = 2
        for profile, data in topo.traffic_profile.items():
            src_min_ip = 0
            src_max_ip = 0
            dst_ip = 0
            pkt_cnt = 0
            dst_min_port = 5000
            dst_max_port = 55000
            count += 1
            src_vm = data['src_vm']
            src_vm_obj = None
            dst_vm_obj = None
            pkt_cnt = data['num_pkts']
            for vm_name in config_topo['vm']:
                if data['dst_vm'] == vm_name:
                    dst_ip = config_topo['vm'][vm_name].vm_ip
                    dst_vm_obj = config_topo['vm'][vm_name]
                    dst_mac_addr = config_topo['vm'][
                                       vm_name].mac_addr.values()[0]
                if src_vm == vm_name:
                    src_vm_obj = config_topo['vm'][vm_name]

            forward_flows = int(data['num_flows'] / fwd_flow_factor)
            dst_max_port = dst_min_port + forward_flows
            traffic_scenarios[profile] = [src_vm_obj,
                                         src_vm_obj.vm_ip,  # src_ip_min
                                         src_vm_obj.vm_ip,  # src_ip_max
                                         dst_ip,  # dest_vm_ip
                                         dst_min_port,
                                         dst_max_port,
                                         data['num_pkts'],
                                         dst_vm_obj,
                                         dst_mac_addr]

        return traffic_scenarios
    #end build_traffic_scenarios


    @preposttest_wrapper
    def test_flow_scaling_interNode_interVN(self):
        """Basic systest with single project with many features & traffic..
        """
        result = False
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
        topology_class_name = flow_scale_topo.FlowScaleTopology
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))

        try:
            topo = topology_class_name(
                compute_node_list=self.inputs.compute_ips,
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
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
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map)
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']

        self.traffic_scenarios = self.build_traffic_scenarios(
                                     topo,
                                     config_topo)

        src_vm_obj=self.traffic_scenarios['1to2'][0]
        vn_fq_name=config_topo['vn']['vnet1'].vn_fq_name
        src_vm_intf_id=src_vm_obj.cs_vmi_obj[
            vn_fq_name]['virtual-machine-interface']['uuid']
        src_vm_obj.provision_static_route(
            prefix='111.1.0.0/16',
            virtual_machine_interface_id=src_vm_intf_id)

        result = self.create_scaled_flows()
        self.delete_agent_flows()
        return True

    # end test_flow_scaling_interNode_interVN
# end TestFlowScaling

