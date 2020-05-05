from __future__ import absolute_import
from .base import BaseRRTest,verify_peer_in_control_nodes,\
     get_connection_matrix
import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from compute_node_test import ComputeNodeFixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from common import isolated_creds
import inspect
from tcutils.util import skip_because, is_almost_same,ipv4_to_decimal
from tcutils.tcpdump_utils import start_tcpdump_for_intf,\
     stop_tcpdump_for_intf, verify_tcpdump_count
import test
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.traffic_utils.hping_traffic import Hping3
import control_node


class TestBasicRR(BaseRRTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicRR, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicRR, cls).tearDownClass()

    # end test_basic_RR
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_process_restart_with_rr_set(self):
        ''' Test to validate rr works fine 
        with process restarts
            1. Pick 2 VN's from resource pool which has one VM each
            2. Set control node as RR
            3. Ping from one VM to another VM
            4. Restart process 'vrouter' and 'control' on setup
            5. Ping again between VM's after process restart
        Pass criteria: Step 2,3,4 and 5 should pass
        '''
        if len(set(self.inputs.bgp_ips)) < 3:
            self.logger.info(
                "Skipping Test. At least 3 control node required to run the test")
            raise self.skipTest(
                "Skipping Test. At least 3 control node required to run the test")

        vn1_name = get_random_name('vn1')
        vn1_subnets = ['192.168.1.0/24']
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        # Take the first BGP node
        ctrl_node_name = self.inputs.bgp_names[0]
        ctrl_node_ip = self.inputs.host_data[ctrl_node_name]['control-ip']
        ctrl_node_host_ip = self.inputs.host_data[ctrl_node_name]['host_ip']
        #set it as the RR
        ctrl_fixture = self.useFixture(
                control_node.CNFixture(
                          connections=self.connections,
                          inputs=self.inputs,
                          router_name=ctrl_node_name,
                          router_ip=ctrl_node_ip
                          )) 
        cluster_id = ipv4_to_decimal(ctrl_node_ip)
       
        if ctrl_fixture.set_cluster_id(cluster_id):
            self.logger.info("cluster id set")
        else:
            self.logger.error("cluster id not set")
            assert False
        #Calculating connection matrix.The mesh connections should be removed
        connection_dicts = get_connection_matrix(self.inputs,ctrl_node_name)
        #Verifying bgp connections.The non-rr nodes should have only one bgp connection to RR
        #RR should have bgp connections to both the non-rrs
        for entry in connection_dicts:
            if verify_peer_in_control_nodes(self.cn_inspect,entry,connection_dicts[entry],self.logger):
                self.logger.info("BGP connections are proper")
            else: 
                self.logger.error("BGP connections are not proper")

        for compute_ip in self.inputs.compute_ips:
            if compute_ip in self.inputs.dpdk_ips:
                self.inputs.stop_service('contrail-vrouter-agent', [compute_ip],
                                         container='agent')
                self.inputs.restart_service('contrail-vrouter-agent-dpdk', [compute_ip],
                                            container='agent-dpdk')
                self.inputs.start_service('contrail-vrouter-agent', [compute_ip],
                                          container='agent')
            else:
                self.inputs.restart_service('contrail-vrouter-agent', [compute_ip],
                                        container='agent')

        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip],
                                        container='control')
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip],
                                        container='api-server')

        # Wait for cluster to be stable
        cs_obj = ContrailStatusChecker(self.inputs)
        clusterstatus, error_nodes = cs_obj.wait_till_contrail_cluster_stable()
        assert clusterstatus, (
            'Hash of error nodes and services : %s' % (error_nodes))

        assert self.verification_after_process_restart_in_rr()
        for cfgm_name in self.inputs.cfgm_names:
            assert self.analytics_obj.verify_cfgm_uve_module_state\
                        (self.inputs.collector_names[0],
                        cfgm_name,'contrail-api')
        #RR should have bgp connections to both the non-rrs
        for entry in connection_dicts:
            if verify_peer_in_control_nodes(self.cn_inspect,entry,connection_dicts[entry],self.logger):
                self.logger.info("BGP connections are proper after restarts")
            else: 
                self.logger.error("BGP connections are not proper after restarts")
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip)
# end test_process_restart_in_policy_between_vns
