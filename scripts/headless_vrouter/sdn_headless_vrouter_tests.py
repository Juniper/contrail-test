#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import copy
import traceback
import unittest
import fixtures
import testtools
from contrail_test_init import *
from vn_test import *
from vnc_api_test import *
from vm_test import *
from connections import ContrailConnections
from contrail_fixtures import *
from vna_introspect_utils import *
from topo_helper import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from sdn_topo_setup import *
import time
import traffic_tests
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver


class sdnHeadlessVrouter(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(sdnHeadlessVrouter, self).setUp()
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

    def reboot_agents_in_headless_mode(self):
        """ Reboot all the agents in the topology to start in headless mode.
        """
        try:
            cmd = "sed -i '/headless_mode/c\headless_mode=true' /etc/contrail/contrail-vrouter-agent.conf"
            for each_ip in self.inputs.compute_ips:
                output = self.inputs.run_cmd_on_server(each_ip,
                                                       cmd,
                                                       self.inputs.username,
                                                       self.inputs.password)
            self.inputs.restart_service('supervisor-vrouter', self.inputs.compute_ips)

        except Exception as e:
            self.logger.exception("Got exception at reboot_agents_in_headless_mode as %s" % (e))
    #end reboot_agents_in_headless_mode

    def start_ping(self, src_vm, dest_vm):
        """ Starting a ping from src_vm to dest_vm.
        """
        self.logger.info("Starting ping from %s to %s" %(src_vm.vm_name, dest_vm.vm_name))
        try:
            cmd = 'ping %s &' % (dest_vm.vm_ip)
            response = src_vm.run_cmd_on_vm(cmds=[cmd])
        except Exception as e:
            self.logger.exception("Got exception at start_ping as %s" % (e))
    # end start_ping

    def stop_ping(self, src_vm):
        """ Stopping ping running on src_vm.
        """
        self.logger.info("Stopping ping from %s" %(src_vm.vm_name))
        try:
            cmd = 'ps aux | pgrep ping'
            response = src_vm.run_cmd_on_vm(cmds=[cmd])
            cmd2 = 'kill -9 %s' %(response[cmd])
            response2 = src_vm.run_cmd_on_vm(cmds=[cmd])
        except Exception as e:
            self.logger.exception("Got exception at start_ping as %s" % (e))
    # end start_ping

    def start_all_control_services(self):
        """ Start all the control services running in the topology.
        """
        self.inputs.start_service('supervisor-control', self.inputs.bgp_ips)
        time.sleep(5)
    #end stop_all_control_services

    def stop_all_control_services(self):
        """ Stop all the control services running in the topology.
        """
        self.inputs.stop_service('supervisor-control', self.inputs.bgp_ips)
        time.sleep(5)
    #end stop_all_control_services

    def check_through_tcpdump(self, dest_vm, src_vm):
        """ Check that the traffic is alive through tcpdump.
        """
        try:
            cmd = "tcpdump -i eth0 -c 3 -n src host %s | grep '%s'" %(src_vm.vm_ip, dest_vm.vm_ip)
            response = dest_vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
            if '3 packets received by filter' in response[cmd]:
                self.logger.info("Ping traffic is stable and continued.")
        except Exception as e:
            self.logger.exception("Got exception at check_through_tcpdump as %s" % (e))
    #end check_through_tcpdump

    def get_flow_index_list(self, src_vm, dest_vm):
        """ Get all the flow index numbers of the flows created.
        """
        try:
            cmd = "flow -l | grep '%s' | grep '%s' | grep '^ [0-9]\|^[0-9]' | awk '{print $1}'" %(src_vm.vm_ip, dest_vm.vm_ip)
            output = self.inputs.run_cmd_on_server(src_vm.vm_node_ip, cmd,
                                           self.inputs.host_data[
                                               src_vm.vm_node_ip]['username'],
                                           self.inputs.host_data[src_vm.vm_node_ip]['password'])

        except Exception as e:
            self.logger.exception("Got exception at get_flow_index_list as %s" % (e))
        output = output.split('\r\n')
        return output
    #end get_flow_index_list


    @preposttest_wrapper
    def test_traffic_connections_while_control_nodes_go_down(self):
        """Tests related to connections and traffic while switching from normal mode to headless and back
           i.e. control nodes go down and come online."""
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
        import sdn_headless_vrouter_topo
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_headless_vrouter_topo.sdn_headless_vrouter_topo

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

        #Start Test
        self.reboot_agents_in_headless_mode() 

        proj = config_topo.keys()
        vms = config_topo[proj[0]]['vm'].keys()
        src_vm = config_topo[proj[0]]['vm'][vms[0]]
        dest_vm = config_topo[proj[0]]['vm'][vms[1]]
        flow_cache_timeout = 180

        #Setup Traffic.
        stream = Stream(protocol="ip", proto="icmp",
                        src=src_vm.vm_ip, dst=dest_vm.vm_ip)
        profile = ContinuousProfile(stream=stream, count=0, capfilter="icmp")

        tx_vm_node_ip = src_vm.vm_node_ip
        rx_vm_node_ip = dest_vm.vm_node_ip

        tx_local_host = Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        rx_local_host = Host(rx_vm_node_ip, self.inputs.username, self.inputs.password)

        send_host = Host(src_vm.local_ip, src_vm.vm_username, src_vm.vm_password)
        recv_host = Host(dest_vm.local_ip, dest_vm.vm_username, dest_vm.vm_password)

        sender = Sender("icmp", profile, tx_local_host,
                        send_host, self.inputs.logger)
        receiver = Receiver("icmp", profile, rx_local_host,
                            recv_host, self.inputs.logger)

        receiver.start()
        sender.start()

        #self.start_ping(src_vm, dest_vm)

        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)

        self.stop_all_control_services()

        self.check_through_tcpdump(dest_vm, src_vm)

        flow_index_list2 = self.get_flow_index_list(src_vm, dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error("Flow indexes have changed. Test Failed, Exiting")
            return False
   
        #wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout)

        #verify_flow_is_not_recreated
        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error("Flow indexes have changed. Test Failed, Exiting")
            return False

        receiver.stop()
        sender.stop()

        #wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout)

        #verify_flow_is_cleared
        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)
        if not flow_index_list[0]:
            self.logger.info("No flows are present")
        else:
            self.logger.error("Flows are still present.")
            return False

        #start_ping
        receiver.start()
        sender.start()
        
        #verify_flow_is_recreated
        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)
        if (flow_index_list[0] and flow_index_list[1]):
            self.logger.info("Flows are recreated.")
        else:
            self.logger.error("Flows are still absent.")
            return False

        self.start_all_control_services()

        self.check_through_tcpdump(dest_vm, src_vm)

        #wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout)

        flow_index_list2 = self.get_flow_index_list(src_vm, dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error("Flow indexes have changed. Test Failed, Exiting")
            return False

        receiver.stop()
        sender.stop()

        #wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout)

        #verify_flow_is_cleared
        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)
        if not flow_index_list[0]:
            self.logger.info("No flows are present")
        else:
            self.logger.error("Flows are still present.")
            return False

        #start_ping
        receiver.start()
        sender.start()

        #verify_flow_is_recreated
        flow_index_list = self.get_flow_index_list(src_vm, dest_vm)
        if (flow_index_list[0] and flow_index_list[1]):
            self.logger.info("Flows are recreated.")
        else:
            self.logger.error("Flows are still absent.")
            return False

        receiver.stop()
        sender.stop()


        return True

    # end test_traffic_connections_while_control_nodes_go_down
# end sdnHeadlessVrouter
