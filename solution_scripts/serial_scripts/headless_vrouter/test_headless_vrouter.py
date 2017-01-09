#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import fixtures
from base import BaseHeadlessVrouterTest
from tcutils.topo import topo_helper
from tcutils.wrappers import preposttest_wrapper
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from vn_test import VNFixture
from vm_test import VMFixture
from ipam_test import IPAMFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
import time
import traffic_tests
import os
import sys
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
import headless_vr_utils
import test_headless_vrouter_topo
from compute_node_test import *

class TestHeadlessVrouter(BaseHeadlessVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(TestHeadlessVrouter, cls).setUpClass()
    # end setUpClass

    def cleanUp(cls):
        super(TestHeadlessVrouter, cls).cleanUp()
    # end cleanUp

    @preposttest_wrapper
    def test_traffic_connections_while_control_nodes_go_down(self):
        """Tests related to connections and traffic while switching from normal mode to headless and back
           i.e. control nodes go down and come online."""

        if len(self.inputs.compute_ips) < 2:
            raise unittest.SkipTest("This test needs atleast 2 compute nodes.")
        else:
            self.logger.info("Required resources are in place to run the test.")

        result = True
        topology_class_name = None

        self.compute_fixture_dict = {}
        for each_compute in self.inputs.compute_ips:
            self.compute_fixture_dict[each_compute] = self.useFixture(
                ComputeNodeFixture(
                    connections=self.connections,
                    node_ip=each_compute,
                    username=self.inputs.username,
                    password=self.inputs.password))
            mode = self.compute_fixture_dict[
                each_compute].get_agent_headless_mode()
            if mode is False:
                self.compute_fixture_dict[
                    each_compute].set_agent_headless_mode()
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = test_headless_vrouter_topo.sdn_headless_vrouter_topo

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
        if out['result']:
            topo_objs, config_topo, vm_fip_info = out['data']

        # Start Test
        proj = config_topo.keys()
        vms = config_topo[proj[0]]['vm'].keys()
        src_vm = config_topo[proj[0]]['vm'][vms[0]]
        dest_vm = config_topo[proj[0]]['vm'][vms[1]]
        flow_cache_timeout = 180

        # Setup Traffic.
        stream = Stream(protocol="ip", proto="icmp",
                        src=src_vm.vm_ip, dst=dest_vm.vm_ip)
        profile = ContinuousProfile(stream=stream, count=0, capfilter="icmp")

        tx_vm_node_ip = src_vm.vm_node_ip
        rx_vm_node_ip = dest_vm.vm_node_ip

        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.username,
            self.inputs.password)
        rx_local_host = Host(
            rx_vm_node_ip,
            self.inputs.username,
            self.inputs.password)

        send_host = Host(
            src_vm.local_ip,
            src_vm.vm_username,
            src_vm.vm_password)
        recv_host = Host(
            dest_vm.local_ip,
            dest_vm.vm_username,
            dest_vm.vm_password)

        sender = Sender("icmp", profile, tx_local_host,
                        send_host, self.inputs.logger)
        receiver = Receiver("icmp", profile, rx_local_host,
                            recv_host, self.inputs.logger)

        receiver.start()
        sender.start()
        self.logger.info("Waiting for 5 sec for traffic to be setup ...")
        time.sleep(5)

        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        headless_vr_utils.stop_all_control_services(self)
        self.addCleanup(self.inputs.start_service, 'supervisor-control', self.inputs.bgp_ips)

        headless_vr_utils.check_through_tcpdump(self, dest_vm, src_vm)

        flow_index_list2 = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error(
                "Flow indexes have changed. Test Failed, Exiting")
            return False

        # wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout)

        # verify_flow_is_not_recreated
        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error(
                "Flow indexes have changed. Test Failed, Exiting")
            return False

        receiver.stop()
        sender.stop()

        # wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout + 5)

        # verify_flow_is_cleared
        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)
        if not flow_index_list[0]:
            self.logger.info("No flows are present")
        else:
            self.logger.error("Flows are still present.")
            return False

        # start_ping
        receiver.start()
        sender.start()
        self.logger.info("Waiting for 5 sec for traffic to be setup ...")
        time.sleep(5)

        # verify_flow_is_recreated
        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)
        if (flow_index_list[0] and flow_index_list[1]):
            self.logger.info("Flows are recreated.")
        else:
            self.logger.error("Flows are still absent.")
            return False

        headless_vr_utils.start_all_control_services(self)

        headless_vr_utils.check_through_tcpdump(self, dest_vm, src_vm)

        # wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout + 5)

        flow_index_list2 = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error(
                "Flow indexes have changed. Test Failed, Exiting")
            return False

        receiver.stop()
        sender.stop()

        # wait_for_flow_cache_timeout
        time.sleep(flow_cache_timeout + 5)

        # verify_flow_is_cleared
        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)
        if not flow_index_list[0]:
            self.logger.info("No flows are present")
        else:
            self.logger.error("Flows are still present.")
            return False

        # start_ping
        receiver.start()
        sender.start()
        self.logger.info("Waiting for 5 sec for traffic to be setup ...")
        time.sleep(5)

        # verify_flow_is_recreated
        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)
        if (flow_index_list[0] and flow_index_list[1]):
            self.logger.info("Flows are recreated.")
        else:
            self.logger.error("Flows are still absent.")
            return False

        receiver.stop()
        sender.stop()

        return True

    # end test_traffic_connections_while_control_nodes_go_down

    @preposttest_wrapper
    def test_config_add_change_while_control_nodes_go_down(self):
        """Tests related to configuration add, change, and delete while switching from normal mode
           to headless and back i.e. control nodes go down and come online."""

        if len(self.inputs.compute_ips) < 2:
            raise unittest.SkipTest("This test needs atleast 2 compute nodes.")
        else:
            self.logger.info("Required resources are in place to run the test.")

        result = True
        topology_class_name = None

        self.compute_fixture_dict = {}
        for each_compute in self.inputs.compute_ips:
            self.compute_fixture_dict[each_compute] = self.useFixture(
                ComputeNodeFixture(
                    connections=self.connections,
                    node_ip=each_compute,
                    username=self.inputs.username,
                    password=self.inputs.password))
            mode = self.compute_fixture_dict[
                each_compute].get_agent_headless_mode()
            if mode is False:
                self.compute_fixture_dict[
                    each_compute].set_agent_headless_mode()
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = test_headless_vrouter_topo.sdn_headless_vrouter_topo

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
        if out['result']:
            topo_objs, config_topo, vm_fip_info = out['data']

        # Start Test
        proj = config_topo.keys()
        vms = config_topo[proj[0]]['vm'].keys()
        src_vm = config_topo[proj[0]]['vm'][vms[0]]
        dest_vm = config_topo[proj[0]]['vm'][vms[1]]
        flow_cache_timeout = 180

        # Setup Traffic.
        stream = Stream(protocol="ip", proto="icmp",
                        src=src_vm.vm_ip, dst=dest_vm.vm_ip)
        profile = ContinuousProfile(stream=stream, count=0, capfilter="icmp")

        tx_vm_node_ip = src_vm.vm_node_ip
        rx_vm_node_ip = dest_vm.vm_node_ip

        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.username,
            self.inputs.password)
        rx_local_host = Host(
            rx_vm_node_ip,
            self.inputs.username,
            self.inputs.password)

        send_host = Host(
            src_vm.local_ip,
            src_vm.vm_username,
            src_vm.vm_password)
        recv_host = Host(
            dest_vm.local_ip,
            dest_vm.vm_username,
            dest_vm.vm_password)

        sender = Sender("icmp", profile, tx_local_host,
                        send_host, self.inputs.logger)
        receiver = Receiver("icmp", profile, rx_local_host,
                            recv_host, self.inputs.logger)

        receiver.start()
        sender.start()
        self.logger.info("Waiting for 5 sec for traffic to be setup ...")
        time.sleep(5)

        #self.start_ping(src_vm, dest_vm)

        flow_index_list = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        headless_vr_utils.stop_all_control_services(self)
        self.addCleanup(self.inputs.start_service, 'supervisor-control', self.inputs.bgp_ips)
        time.sleep(10)
        headless_vr_utils.check_through_tcpdump(self, dest_vm, src_vm)

        flow_index_list2 = headless_vr_utils.get_flow_index_list(
            self,
            src_vm,
            dest_vm)

        if set(flow_index_list) == set(flow_index_list2):
            self.logger.info("Flow indexes have not changed.")
        else:
            self.logger.error(
                "Flow indexes have changed. Test Failed, Exiting")
            return False

        receiver.stop()
        sender.stop()
        project1_instance = config_topo['project1']['project']['project1']
        project1_instance.get_project_connections()
        vnet2_instance = config_topo['project1']['vn']['vnet2']

        # add VM to existing VN
        VM22_fixture = self.useFixture(
            VMFixture(
                connections=project1_instance.project_connections,
                vn_obj=vnet2_instance.obj,
                vm_name='VM22',
                project_name=project1_instance.project_name))

        # create new IPAM
        ipam3_obj = self.useFixture(
            IPAMFixture(
                project_obj=project1_instance,
                name='ipam3'))
        ipam4_obj = self.useFixture(
            IPAMFixture(
                project_obj=project1_instance,
                name='ipam4'))

        # create new VN
        VN3_fixture = self.useFixture(
            VNFixture(
                project_name=project1_instance.project_name,
                connections=project1_instance.project_connections,
                vn_name='VN3',
                inputs=project1_instance.inputs,
                subnets=['10.3.1.0/24'],
                ipam_fq_name=ipam3_obj.fq_name))

        VN4_fixture = self.useFixture(
            VNFixture(
                project_name=project1_instance.project_name,
                connections=project1_instance.project_connections,
                vn_name='VN4',
                inputs=project1_instance.inputs,
                subnets=['10.4.1.0/24'],
                ipam_fq_name=ipam4_obj.fq_name))

        # create policy
        policy_name = 'policy34'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': VN4_fixture.vn_fq_name,
                  'source_network': VN3_fixture.vn_fq_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'},
                 {'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': VN3_fixture.vn_fq_name,
                  'source_network': VN4_fixture.vn_fq_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy34_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=project1_instance.inputs,
                connections=project1_instance.project_connections,
                project_fixture=project1_instance))

        # create VN to policy mapping in a dict of policy list.
        vn_policys = {
            VN3_fixture.vn_name: [policy_name],
            VN4_fixture.vn_name: [policy_name]}

        # create a policy object list of policies to be attached to a vm
        policy_obj_dict = {}
        policy_obj_dict[VN3_fixture.vn_name] = [policy34_fixture.policy_obj]
        policy_obj_dict[VN4_fixture.vn_name] = [policy34_fixture.policy_obj]

        # vn fixture dictionary.
        vn_obj_dict = {}
        vn_obj_dict[VN3_fixture.vn_name] = VN3_fixture
        vn_obj_dict[VN4_fixture.vn_name] = VN4_fixture

        # attach policy to VN
        VN3_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=project1_instance.project_connections,
                vn_name=VN3_fixture.vn_name,
                policy_obj=policy_obj_dict,
                vn_obj=vn_obj_dict,
                vn_policys=vn_policys[
                    VN3_fixture.vn_name],
                project_name=project1_instance.project_name))

        VN4_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=project1_instance.project_connections,
                vn_name=VN4_fixture.vn_name,
                policy_obj=policy_obj_dict,
                vn_obj=vn_obj_dict,
                vn_policys=vn_policys[
                    VN4_fixture.vn_name],
                project_name=project1_instance.project_name))

        # add VM to new VN
        VM31_fixture = self.useFixture(
            VMFixture(
                connections=project1_instance.project_connections,
                vn_obj=VN3_fixture.obj,
                vm_name='VM31',
                project_name=project1_instance.project_name))

        VM41_fixture = self.useFixture(
            VMFixture(
                connections=project1_instance.project_connections,
                vn_obj=VN4_fixture.obj,
                vm_name='VM41',
                project_name=project1_instance.project_name))

        # verification routines.
        test_flag = 0
        if ((VN3_fixture.verify_vn_in_api_server()) and
                (VN3_fixture.verify_vn_not_in_agent()) and
                (VN3_fixture.verify_vn_policy_in_api_server()['result'])):
            self.logger.info(
                "Verification of VN3 PASSED while control nodes down.")
        else:
            self.logger.error(
                "Verification of VN3 FAILED while control nodes down.")
            test_flag = 1

        if ((VN4_fixture.verify_vn_in_api_server()) and
                (VN4_fixture.verify_vn_not_in_agent()) and
                (VN4_fixture.verify_vn_policy_in_api_server()['result'])):
            self.logger.info(
                "Verification of VN4 PASSED while control nodes down.")
        else:
            self.logger.error(
                "Verification of VN4 FAILED while control nodes down.")
            test_flag = 1

        if ((VM22_fixture.verify_vm_launched()) and
                (VM22_fixture.verify_vm_in_api_server())):
            self.logger.info(
                "Verification of VM22 PASSED while control nodes down.")
        else:
            self.logger.error(
                "Verification of VM22 FAILED while control nodes down.")
            test_flag = 1

        if ((VM31_fixture.verify_vm_launched()) and
                (VM31_fixture.verify_vm_in_api_server())):
            self.logger.info(
                "Verification of VM31 PASSED while control nodes down.")
        else:
            self.logger.error(
                "Verification of VM31 FAILED while control nodes down.")
            test_flag = 1

        if ((VM41_fixture.verify_vm_launched()) and
                (VM41_fixture.verify_vm_in_api_server())):
            self.logger.info(
                "Verification of VM41 PASSED while control nodes down.")
        else:
            self.logger.error(
                "Verification of VM41 FAILED while control nodes down.")
            test_flag = 1

        # start all control services.
        headless_vr_utils.start_all_control_services(self)

        # if something went wrong in the controller down state bail out here.
        if test_flag == 1:
            self.logger.error("Verifications and Test failed while the controllers were down in \
                               headless state of agent. Check earlier error logs")
            return False

        # wait for 3 to 5 sec for configuration sync from control nodes to the
        # agents.
        time.sleep(5)

        # wait till VM's are up.
        VM22_fixture.wait_till_vm_is_up()
        VM31_fixture.wait_till_vm_is_up()
        VM41_fixture.wait_till_vm_is_up()

        # verify vm config gets downloaded to the agents.
        if ((VM22_fixture.verify_vm_in_agent()) and
                (VM31_fixture.verify_vm_in_agent()) and
                (VM41_fixture.verify_vm_in_agent())):
            self.logger.info("VM verification on the agent PASSED")
        else:
            self.logger.error("VM verification on the agent FAILED")
            return False

        # check ping success between the two VM's
        assert config_topo['project1']['vm']['VM11'].ping_with_certainty(
            VM22_fixture.vm_ip, expectation=True)
        assert VM31_fixture.ping_with_certainty(
            VM41_fixture.vm_ip,
            expectation=True)
        assert VM41_fixture.ping_with_certainty(
            VM31_fixture.vm_ip,
            expectation=True)

        # verification routines.
        if ((VN3_fixture.verify_on_setup()) and
                (VN4_fixture.verify_on_setup()) and
                (VM22_fixture.verify_on_setup()) and
                (VM31_fixture.verify_on_setup()) and
                (VM41_fixture.verify_on_setup())):
            self.logger.info(
                "All verifications passed after controllers came up in headless agent mode")
        else:
            self.logger.error(
                "Verifications FAILED after controllers came up in headless agent mode")
            return False

        return True

    # end test_config_add_change_while_control_nodes_go_down
# end TestHeadlessVrouter
