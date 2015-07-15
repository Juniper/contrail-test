from vn_test import VNFixture
from policy_test import PolicyFixture
from vm_test import VMFixture
from base import BaseSerialPolicyTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from common.system.system_verification import assertEqual
import common.system.system_verification
from common.policy import policy_test_utils
from tcutils.topo.topo_helper import topology_helper
from traffic_tests import trafficTestFixture
import time
import json
import re
import copy
import random
import sdn_policy_traffic_test_topo
from common.topo import sdn_policy_topo_with_multi_project
from tcutils.util import get_random_name, get_random_cidr, gen_str_with_spl_char
import os

class TestSerialPolicy(BaseSerialPolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestSerialPolicy, cls).setUpClass()

    def check_policy_route_available(self, vnet_list, vn_fixture):
        '''For a given VN pair, vnet_listi, check if policy routes are available..
        VN's are expected in FQDN format.. Return True of route exists.. else False'''

        vn_policys_peer_vns = {}
        vns = []
        fqns = {}
        pvns = {}
        for v in vnet_list:
            m = re.search(r"(\S+):(\S+):(\S+)", v)
            vns.append(m.group(3))
            fqns[m.group(3)] = v

        actual_peer_vns_by_policy = policy_test_utils.get_policy_peer_vns(
            self, vns, vn_fixture)
        print "actual_peer_vns_by_policy: ", actual_peer_vns_by_policy
        # actual_peer_vns_by_policy format:
        # {'vnet0':[u'default-domain:admin:vnet1',
        # u'default-domain:admin:vnet2'], ..}]

        pvns[0] = actual_peer_vns_by_policy[vns[0]]
        # find if vn1 in the given pair is in vn0's peer list
        if fqns[vns[1]] not in pvns[0]:
            self.logger.info(
                "vn %s not in peer list of %s, actual_peer_vns_by_policy %s" %
                (vns[1], vns[0], pvns[0]))
            result = False
        else:
            # Find if vn0 is in vn1's peer list
            pvns[1] = actual_peer_vns_by_policy[vns[1]]
            if fqns[vns[0]] not in pvns[1]:
                self.logger.info(
                    "vn %s not in peer list of %s, actual_peer_vns_by_policy %s" %
                    (vns[0], vns[1], pvns[1]))
                result = False
            else:
                result = True

        return result

    def check_exception_flows_in_kernel(self, compNode):
        '''Look for HOLD and Null flows.. return False if found, else True.
        '''
        self.logger.info(
            "Inspecting kernel for exception flows - Null flows with src/dest address 0.0.0.0 & HOLD flows with action as HOLD")
        status = True
        msg = []
        inspect_h = self.agent_inspect[compNode]
        try:
            kflows = inspect_h.get_vna_kflowresp()
        except Exception as e:
            err = "Compute: %s, hit error in kernel introspect, check topology for expected result" % (
                compNode)
            self.logger.warn(err)
            et, ei, tb = sys.exc_info()
            formatted_traceback = ''.join(traceback.format_tb(tb))
            fail_trace = '\n{0}\n{1}:\n{2}'.format(
                formatted_traceback, et.__name__, ei.message)
            self.logger.warn(
                "Exception happened while collecting kernel flow, failure trace as follows:")
            self.logger.warn(fail_trace)
        if kflows is None:
            msg.append(
                "Not getting kernel flow info from agent %s..Check detailed error printed by introspect" %
                compNode)
            self.logger.error(msg)
            return {'status': False, 'msg': msg}
        self.logger.info("Info on total kernel flows in compute %s: %s" %
                         (compNode, len(kflows)))
        #self.logger.info ("all kernel flows in compute %s: %s" %(compNode, kflows))
        hold_flow_l = []
        null_flow_l = []
        for flow in kflows:
            if flow['action'] == 'HOLD':
                hold_flow_l.append(flow)
            # null flow has following signature - flow['sip'] == '0.0.0.0' and flow['dip'] == '0.0.0.0' and
            # flow['sport'] == '0' and flow['dport'] == '0' and flow['proto'] == '0' and flow['vrf_id'] == '0']
            # we will just do partial check and see if other variants show
            # up...
            elif flow['sip'] == '0.0.0.0':
                null_flow_l.append(flow)
        self.logger.info(
            "Info on kernel flows in HOLD state in compute %s: %s" %
            (compNode, hold_flow_l))
        self.logger.info("Info on kernel Null flows in compute %s: %s" %
                         (compNode, null_flow_l))
        # end checking all test flows
        if hold_flow_l:
            status = False
            msg.extend(
                ["Hold flows found in compute: ", hold_flow_l])
        if null_flow_l:
            status = False
            msg.extend(
                ["Null flows found in compute: ", null_flow_l])
        return {'status': status, 'msg': msg}

    def validate_flow_in_vna(self, test_flow_list, test_vn, vn_fixture):
        ''' Given 5-tuple, validate flow info in agent. 5-tuple as follows: src-addr, dst-addr, src-port, dst-port,
        protocol and action for the flow. For bi-dir flows, each direction needs to be checked.
        '''
        msg = []
        self.logger.info("Validate agent flows against test flows")
        self.logger.info("flow list recd. for checking: %s" % test_flow_list)
        compNode = test_flow_list[0]['agent_inspect_ip']
        inspect_h = self.agent_inspect[compNode]
        flows_found = []
        flows_not_found = []
        for f in test_flow_list:
            flow = f['flow_entries']
            self.logger.info(
                "--->VNA-Flow check: Looking for following test flow: %s" %
                (json.dumps(flow, sort_keys=True)))
            vnet_list = [flow['source_vn'], flow['dst_vn']]
            policy_route_state = self.check_policy_route_available(
                vnet_list, vn_fixture)
            try:
                mflow = inspect_h.get_vna_fetchflowrecord(
                    nh=flow['nh_id'],
                    sip=flow['src'],
                    dip=flow['dst'],
                    sport=flow['src_port'],
                    dport=flow['dst_port'],
                    protocol=flow['protocol'])
            except:
                msg.append(
                    "Agent: %s, VN: %s, hit error in vna flow inspect, check topology for expected result" %
                    (compNode, test_vn))
                self.logger.warn(msg)
                return {'status': False, 'msg': msg}

            # maintain 2 variables of match - few_flows_found [to track none or
            # few found] & all_flows_found
            few_flows_found = False
            all_flows_found = True
            if mflow is None:
                if policy_route_state:
                    msg.append("test_flow not seen in agent %s, flow: %s" %
                               (compNode, json.dumps(flow, sort_keys=True)))
                    all_flows_found = all_flows_found and False
                    flows_not_found.append(json.dumps(flow, sort_keys=True))
                    continue   # Move on to next flow
                else:
                    self.logger.info(
                        "Flow not found, which is expected when routes not available")
                    continue

            # proceed with flow inspection..
            agent_flow = {}
            for i in mflow:
                agent_flow.update(i)
            self.logger.info("Matching flow from agent: %s" %
                             (json.dumps(agent_flow, sort_keys=True)))

            # For a matching flow, check following key values
            keys_to_verify = ['dst_vn', 'action']

            # For matching flow, check dest_vn and action to see if they are
            # intact
            for k in keys_to_verify:
                err_msg = None
                match = True
                if k == 'action':
                    if flow[k][0] == 'pass':
                        if agent_flow[k] == 'pass' or agent_flow[k] == '32':
                            match = match and True
                        else:
                            err_msg = (
                                "For the matching flow, data for key %s not matching, test has %s, agent flow has %s" %
                                (k, flow[k], agent_flow[k]))
                            match = match and False
                            break
                    if flow[k][0] == 'deny':
                        if agent_flow[k][0] == 'drop' or agent_flow[k] == '4':
                            match = match and True
                        else:
                            err_msg = (
                                "For the matching flow, data for key %s not matching, test has %s, agent flow has %s" %
                                (k, expected, agent_flow[k]))
                            match = match and False
                            break
                elif k == 'dst_vn':
                    expected_vn = "__UNKNOWN__" if policy_route_state == False else flow[
                        k]
                    if expected_vn == agent_flow[k]:
                        match = match and True
                    else:
                        err_msg = (
                            "For the matching flow, data for key %s not matching, test has %s, agent flow has %s" %
                            (k, flow[k], agent_flow[k]))
                        match = match and False
                        break
            # end for, done matching test flow with all agent flows

            if match:
                self.logger.info(
                    "--->VNA-Flow check: Matching flow has all fields intact: %s" %
                    agent_flow['uuid'])
                few_flows_found = few_flows_found or True
                flows_found.append(json.dumps(flow, sort_keys=True))
            if not match:
                flows_not_found.append(json.dumps(flow, sort_keys=True))
                all_flows_found = all_flows_found and False
                msg1 = "VNA-Flow check: Agent %s: Failing test flow: %s" % (
                    compNode, flow)
                try:
                    err_msg
                except:
                    msg.append(msg1)
                else:
                    msg.extend([msg1, err_msg])
        # end checking all test flows

        status = True if all_flows_found else False
        rdata = {
            'status': status, 'msg': msg, 'few_flows_found': few_flows_found,
            'flows_found': flows_found, 'flows_not_found': flows_not_found}
        self.logger.info("return data from agent flow introspect: %s" % rdata)

        return rdata

    def build_test_flow(
            self,
            policy,
            test_vm1,
            test_vm2,
            topo,
            config_topo,
            traffic_proto_l,
            total_streams,
            dpi=9100):
        ''' Getting the setup details and traffic params to generate the test flow for validation in agent and
            update the test flow list to validate flow in agent and also
            update the matching flow list to verifying  the traffic.
        '''
        test_flow_list = []
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vn_vm1 = topo.vn_of_vm[
            test_vm1]
        test_vn_vm1_fix = config_topo['vn'][test_vn_vm1]
        test_vn_vm2 = topo.vn_of_vm[
            test_vm2]
        test_vn_vm2_fix = config_topo['vn'][test_vn_vm2]
        for proto in traffic_proto_l:
            for i in range(total_streams[proto]):
                test_flow = {}
                test_flow['agent_inspect_ip'] = test_vm1_fixture.vm_node_ip
                test_flow['flow_entries'] = {}
                f = test_flow['flow_entries']
                f['src'] = test_vm1_fixture.vm_ip
                f['dst'] = test_vm2_fixture.vm_ip
                f['source_vn'] = test_vn_vm1_fix.vn_fq_name
                f['dst_vn'] = test_vn_vm2_fix.vn_fq_name
                vm1_vn_fq_name = test_vm1_fixture.vn_fq_name
                nh = test_vm1_fixture.tap_intf[vm1_vn_fq_name]['flow_key_idx']
                f['nh_id'] = nh
                if proto == 'icmp':
                    f['protocol'] = '1'
                    f['src_port'] = '0'
                    f['dst_port'] = '0'
                if proto == 'udp' or proto == 'tcp':
                    if proto == 'udp':
                        f['protocol'] = '17'
                    if proto == 'tcp':
                        f['protocol'] = '6'
                    f['dst_port'] = str(dpi + i)
                    f['src_port'] = '8000'
            test_flow_list.append(test_flow)
        # set expectations..
        matching_rule_action = {}
        num_rules = len(topo.rules[policy])
        for i in range(num_rules):
            proto = topo.rules[policy][i]['protocol']
            matching_rule_action[proto] = topo.rules[
                policy][i]['simple_action']
        if num_rules == 0:
            for proto in traffic_proto_l:
                matching_rule_action[proto] = 'deny'
        for test_flow in test_flow_list:
            f = test_flow['flow_entries']
            if f['protocol'] == '17':
                f['action'] = str(matching_rule_action['udp'])
                f['action_l'] = [f['action']]
            if f['protocol'] == '6':
                f['action'] = str(matching_rule_action['tcp'])
                f['action_l'] = [f['action']]
            if f['protocol'] == '1':
                f['action'] = str(matching_rule_action['icmp'])
                f['action_l'] = [f['action']]
            # action granularity is at proto only for this test
        self.logger.info(
            "return data from build test-flow,test_flow_list :%s and matching_rule_action:%s" %
            (test_flow_list, matching_rule_action))
        return (test_flow_list, matching_rule_action)
    # End  building test_flow_list

    @preposttest_wrapper
    def test_controlnode_switchover_policy_between_vns_traffic(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with control-node switchover without any traffic drops
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            self.logger.info(
                "Skipping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
        result = True
        msg = []
        vn1_name = 'vn40'
        vn1_subnets = ['40.1.1.0/24']
        vn2_name = 'vn41'
        vn2_subnets = ['41.1.1.0/24']
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        policy3_name = 'policy3'
        policy4_name = 'policy4'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules,
                inputs=self.inputs,
                connections=self.connections))
        policy3_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy3_name,
                rules_list=rules1,
                inputs=self.inputs,
                connections=self.connections))
        policy4_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy4_name,
                rules_list=rev_rules1,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets,
                policy_objs=[
                    policy1_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets,
                policy_objs=[
                    policy2_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic'))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn1_vm2_name,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=True)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy1_name])
        assertEqual(result, True, msg)

        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        dpi = 9100
        proto = 'udp'
        expectedResult = {}
        for proto in traffic_proto_l:
            expectedResult[proto] = True if rules[0][
                'simple_action'] == 'pass' else False
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=vm1_fixture,
                rx_vm_fixture=vm2_fixture,
                stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, vm1_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = ["Traffic disruption is seen: details: "] + \
                traffic_stats['msg']
        assertEqual(traffic_stats['status'],
                    expectedResult[proto], err_msg)
        self.logger.info("-" * 80)

        # Figuring the active control node
        active_controller = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, active_controller))

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller))
        self.inputs.stop_service('contrail-control', [active_controller])
        self.addCleanup(self.inputs.start_service,
                        'contrail-control', [active_controller])
        time.sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, new_active_controller))
        if new_active_controller == active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller, new_active_controller))
            result = False

        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

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
        assertEqual(result, True, msg)

        # bind the new policy to VN1
        self.logger.info("Bind the new policy to VN's..")
        policy_fq_name1 = [policy3_fixture.policy_fq_name]
        policy_fq_name2 = [policy4_fixture.policy_fq_name]
        vn1_fixture.bind_policies(policy_fq_name1, vn1_fixture.vn_id)
        time.sleep(5)
        # bind the new policy to VN2
        vn2_fixture.bind_policies(policy_fq_name2, vn2_fixture.vn_id)
        time.sleep(5)

        # policy deny applied traffic should fail
        self.logger.info(
            'Checking the ping between the VM with new policy(deny)')
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy3_name])
        assertEqual(result, True, msg)

        self.logger.info("Verify ping to vm %s" % (vn1_vm1_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm1_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy4_name])
        assertEqual(result, True, msg)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller))
        self.inputs.start_service('contrail-control', [active_controller])

        time.sleep(10)
        # Check the BGP peering status from the currently active control node
        cn_bgp_entry = self.cn_inspect[
            new_active_controller].get_cn_bgp_neigh_entry()
        time.sleep(5)
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

        # Stop on current Active node to simulate fallback
        self.logger.info("Will fallback to original primary control-node..")
        self.logger.info('Stoping the Control service in  %s' %
                         (new_active_controller))
        self.inputs.stop_service('contrail-control', [new_active_controller])
        self.addCleanup(self.inputs.start_service,
                        'contrail-control', [new_active_controller])
        time.sleep(5)

        # Check the control node shifted back to previous cont
        orig_active_controller = None
        orig_active_controller_state = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                orig_active_controller = entry['controller_ip']
                orig_active_controller_state = entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, orig_active_controller))
        if orig_active_controller == new_active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (self.new_active_controller, orig_active_controller))
            result = False

        if orig_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Check the ping
        self.logger.info(
            'Checking the ping between the VM again with new policy deny..')
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy3_name])
        assertEqual(result, True, msg)

        self.logger.info("Verify ping to vm %s" % (vn1_vm1_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm1_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy4_name])
        assertEqual(result, True, msg)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (new_active_controller))
        self.inputs.start_service('contrail-control', [new_active_controller])
        if not result:
            self.logger.error('Switchover of control node failed')
            assert result
        return True
    # end test_controlnode_switchover_policy_between_vns_traffic

    @preposttest_wrapper
    def test_policy_single_vn_with_multi_proto_traffic(self):
        """ Call policy_test_with_multi_proto_traffic with single VN scenario.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_1vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_with_multi_proto_traffic(topo)

    @preposttest_wrapper
    def test_policy_multi_vn_with_multi_proto_traffic(self):
        """ Call policy_test_with_multi_proto_traffic with multi VN scenario.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_2vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_with_multi_proto_traffic(topo)

    def policy_test_with_multi_proto_traffic(self, topo):
        """ Pick 2 VM's for testing, have rules affecting icmp & udp protocols..
        Generate traffic streams matching policy rules - udp & icmp for now..
        assert if traffic failure is seen as no disruptive trigger is applied here..
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # Setup/Verify Traffic ---
        # 1. Define Traffic Params
        test_vm1 = topo.vmc_list[0]  # 'vmc0'
        test_vm2 = topo.vmc_list[1]  # 'vmc1'
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vn = topo.vn_of_vm[test_vm1]  # 'vnet0'
        test_vn1 = topo.vn_of_vm[test_vm2]
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp', 'udp', 'tcp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 1
        total_streams['tcp'] = 1
        dpi = 9100
        # 2. set expectation to verify..
        matching_rule_action = {}
        # Assumption made here: one policy assigned to test_vn
        policy = topo.vn_policy[test_vn][0]
        policy_info = "policy in effect is : " + str(topo.rules[policy])
        num_rules = len(topo.rules[policy])
        for i in range(num_rules):
            proto = topo.rules[policy][i]['protocol']
            matching_rule_action[proto] = topo.rules[
                policy][i]['simple_action']
        if num_rules == 0:
            for proto in traffic_proto_l:
                matching_rule_action[proto] = 'deny'
        self.logger.info("matching_rule_action: %s" % matching_rule_action)
        # 3. Start Traffic
        expectedResult = {}
        start_time = self.analytics_obj.getstarttime(
            self.inputs.compute_ips[0])
        for proto in traffic_proto_l:
            expectedResult[proto] = True if matching_rule_action[
                proto] == 'pass' else False
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=test_vm1_fixture,
                rx_vm_fixture=test_vm2_fixture,
                stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, test_vm1_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            self.assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # 4. Poll live traffic
        # poll traffic and get status - traffic_stats['msg'],
        # traffic_stats['status']
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = [policy_info] + traffic_stats['msg']
            self.logger.info(
                " --> , flow proto: %s, expected: %s, got: %s" %
                (proto, expectedResult[proto], traffic_stats['status']))
            self.assertEqual(traffic_stats['status'],
                             expectedResult[proto], err_msg)
        self.logger.info("-" * 80)
        # 4.a Opserver verification
        self.logger.info("Verfiy Policy info in Opserver")
        self.logger.info("-" * 80)
        exp_flow_count = total_streams['icmp'] + \
            total_streams['tcp'] + total_streams['udp']
        self.logger.info("-" * 80)

        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + test_vn
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + test_vn1
        query = {}
        query['udp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =17) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        query['tcp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =6) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        query['icmp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =1) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        flow_record_data = {}
        flow_series_data = {}
        expected_flow_count = {}
        for proto in traffic_proto_l:
            flow_record_data[proto] = self.ops_inspect.post_query(
                'FlowRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'setup_time',
                    'teardown_time',
                    'agg-packets',
                    'agg-bytes',
                    'protocol'],
                where_clause=query[proto])
            flow_series_data[proto] = self.ops_inspect.post_query(
                'FlowSeriesTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'flow_count',
                    'sum(bytes)',
                    'sum(bytes)'],
                where_clause=query[proto])
            msg1 = proto + \
                " Flow count info is not matching with opserver flow series record"
            # initialize expected_flow_count to num streams generated for the
            # proto
            expected_flow_count[proto] = total_streams[proto]
            self.logger.info(flow_series_data[proto])
            self.assertEqual(
                flow_series_data[proto][0]['flow_count'],
                expected_flow_count[proto],
                msg1)
        # 5. Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        traffic_stats = {}
        for proto in traffic_proto_l:
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            status = True if stopStatus[proto] == [] else False
            if status != expectedResult[proto]:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
            # Get the traffic Stats for each protocol sent
            traffic_stats[proto] = traffic_obj[proto].returnStats()
            time.sleep(5)
            # Get the Opserver Flow series data
            flow_series_data[proto] = self.ops_inspect.post_query(
                'FlowSeriesTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'flow_count',
                    'sum(bytes)',
                    'sum(bytes)'],
                where_clause=query[proto])
        self.assertEqual(result, True, msg)
        # 6. Match traffic stats against Analytics flow series data
        self.logger.info("-" * 80)
        self.logger.info(
            "***Match traffic stats against Analytics flow series data***")
        self.logger.info("-" * 80)
        msg = {}
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against Analytics flow series data" %
                (proto))
            msg[proto] = proto + \
                " Traffic Stats is not matching with opServer flow series data"
            self.logger.info(
                "***Actual Traffic sent by agent %s \n\n stats shown by Analytics flow series%s" %
                (traffic_stats[proto], flow_series_data[proto]))
            self.assertGreaterEqual(
                flow_series_data[proto][0]['sum(packets)'],
                traffic_stats[proto]['total_pkt_sent'],
                msg[proto])

        # 6.a Let flows age out and verify analytics still shows the data
        self.logger.info("-" * 80)
        self.logger.info(
            "***Let flows age out and verify analytics still shows the data in the history***")
        self.logger.info("-" * 80)
        time.sleep(180)
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against Analytics flow series data after flow age out" %
                (proto))
            flow_series_data[proto] = self.ops_inspect.post_query(
                'FlowSeriesTable',
                start_time='now',
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'flow_count',
                    'sum(bytes)',
                    'sum(bytes)'],
                where_clause=query[proto])
            msg = proto + \
                " Flow count info is not matching with opserver flow series record after flow age out in kernel"
            # live flows shoud be '0' since all flows are age out in kernel
            # self.assertEqual(flow_series_data[proto][0]['flow_count'],0,msg)
            self.assertEqual(len(flow_series_data[proto]), 0, msg)
            flow_series_data[proto] = self.ops_inspect.post_query(
                'FlowSeriesTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'flow_count',
                    'sum(bytes)',
                    'sum(bytes)'],
                where_clause=query[proto])
            msg = proto + \
                " Traffic Stats is not matching with opServer flow series data after flow age out in kernel"
            # Historical data should be present in the Analytics, even if flows
            # age out in kernel
            self.assertGreaterEqual(
                flow_series_data[proto][0]['sum(packets)'],
                traffic_stats[proto]['total_pkt_sent'],
                msg)
        return result
    # end test_policy_with_multi_proto_traffic

    @preposttest_wrapper
    def test_policy_single_vn_modify_rules_of_live_flows(self):
        """ Call policy_test_modify_rules_of_live_flows with single VN scenario..
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_1vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_modify_rules_of_live_flows(topo)

    @preposttest_wrapper
    def test_policy_multi_vn_modify_rules_of_live_flows(self):
        """ Call policy_test_modify_rules_of_live_flows with multi VN scenario..
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_2vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_modify_rules_of_live_flows(topo)

    @preposttest_wrapper
    def test_policy_replace_single_vn_modify_rules_of_live_flows(self):
        """ Call policy_test_modify_rules_of_live_flows with single VN scenario..
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_1vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_modify_rules_of_live_flows(
            topo,
            update_mode='replace')

    def policy_test_modify_rules_of_live_flows(
            self,
            topo,
            update_mode='modify'):
        """ 1. Pick 2 VM's for testing, have rules affecting icmp & udp protocols..
        2. Generate traffic streams matching policy rules - udp & icmp ..
        3. verify expected traffic behavior.
        4. modify rules and check for expected behavior for live flows..
        5. Modifying rules does following.. one set of update affects single live flow and checks expected behavior.
        another set adds dummy rule and verifies expected behavior.
        """
        result = True
        msg = []
        err_msg = []
        #
        # Test setup: Configure policy, VN, & VM
        self.logger.info("TEST STEP -1: configure topology")
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        # ---> Verify & return here on failure
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # Verify Traffic ---
        # Start Traffic
        self.logger.info("TEST STEP -2: start traffic")
        # Get data for 2 VM's to run traffic..
        test_vm1 = topo.vmc_list[
            0]
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2 = topo.vmc_list[
            1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vn = topo.vn_of_vm[
            test_vm1]
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        test_vn_vm1 = topo.vn_of_vm[
            test_vm1]
        test_vn_vm1_fix = config_topo['vn'][test_vn_vm1]
        test_vn_vm2 = topo.vn_of_vm[
            test_vm2]
        test_vn_vm2_fix = config_topo['vn'][test_vn_vm2]
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp', 'udp', 'tcp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams[
            'udp'] = 1
        total_streams['tcp'] = 1
        dpi = 9100   # starting dest_port incase of udp
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000, total_single_instance_streams= 20):
            # vm1 as src and vm2 as dst
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=test_vm1_fixture,
                rx_vm_fixture=test_vm2_fixture,
                stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, test_vm1_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            # ---> Verify & return here on failure
            self.assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # Poll live traffic
        self.logger.info("TEST STEP -3: verify traffic after setup")
        self.logger.info("Poll live traffic and get status..")
        # Assumption made here: one policy assigned to test_vn
        policy = topo.vn_policy[test_vn][0]
        num_rules = len(topo.rules[policy])
        policy_info = "policy in effect is : %s" % (topo.rules[policy])
        # set expectations & build test_flow_list to verify
        self.logger.info(
            "TEST STEP -3a: build test_flow_list and validate in VN Agent")
        test_flow_list, matching_rule_action = self.build_test_flow(
            policy, test_vm1, test_vm2, topo, config_topo, traffic_proto_l, total_streams, dpi)
        self.logger.info(
            "TEST STEP -3b: Validate Agent/Kernel for flows and Poll traffic ..")
        # with live traffic, validate flows programmed in agents.
        # time.sleep (30) # wait for short flows to settle down
        #out= self.validate_flow_in_kernel(test_flow_list, test_vn)
        # if out['status'] != True:
        #    err_msg.extend (["Kernel flow validation failed after startTraffic, details - ", out['msg']])
        #    self.logger.error (err_msg)
        #self.assertEqual(out['status'], True, err_msg)
        # waiting for short flows to settle down after setup/starting traffic..
        time.sleep(30)
        out = self.validate_flow_in_vna(
            test_flow_list, test_vn, config_topo['vn'])
        if out['status'] != True:
            err_msg.extend(
                ["Flows not programmed as expected in computes after startTraffic - ", out['msg']])
            self.logger.error(err_msg)
        self.assertEqual(out['status'], True, err_msg)
        expectedResult = {}
        for proto in traffic_proto_l:
            expectedResult[proto] = True if matching_rule_action[
                proto] == 'pass' else False
        # poll traffic and get status - traffic_stats['msg'],
        # traffic_stats['status']
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = [policy_info] + traffic_stats['msg']
            self.logger.info(" --> expected: %s, got: %s" %
                             (expectedResult[proto], traffic_stats['status']))
            # ---> Verify & return here on failure
        self.assertEqual(traffic_stats['status'],
                         expectedResult[proto], err_msg)
        self.logger.info("-" * 80)
        self.logger.info("TEST STEP -4: modify policy")
        starting_policy_name = policy
        starting_policy_fixture = config_topo['policy'][policy]
        starting_policy_id = starting_policy_fixture.policy_obj['policy']['id']
        #import pdb; pdb.set_trace()
        for policy in topo.policy_test_order:
            if update_mode == 'replace':
                # set new policy for test_vn to policy
                test_policy_fq_names = []
                name = config_topo['policy'][
                    policy].policy_obj['policy']['fq_name']
                test_policy_fq_names.append(name)
                test_vn_fix.bind_policies(test_policy_fq_names, test_vn_id)
            elif update_mode == 'modify':
                new_policy_entries = config_topo['policy'][
                    policy].policy_obj['policy']['entries']
                data = {'policy': {'entries': new_policy_entries}}
                starting_policy_fixture.update_policy(starting_policy_id, data)
                new_rules = topo.rules[policy]
                # policy= current_policy_name     #policy name is still old one
                # update new rules in reference topology
                topo.rules[starting_policy_name] = copy.copy(new_rules)
            # wait for tables update before checking after making changes to
            # system
            time.sleep(5)
            state = "policy for " + test_vn + " updated to rules of policy" + \
                policy + "by mode" + update_mode
            self.logger.info("new policy list of vn %s is %s" %
                             (test_vn, policy))
            # update expected topology with this new info for verification
            updated_topo = policy_test_utils.update_topo(topo, test_vn, policy)
            self.logger.info("Starting Verifications after %s" % (state))
            policy_info = "policy in effect is : %s" % (topo.rules[policy])
            self.logger.info(policy_info)
            # Topology guide: each policy has explicit single rule matching udp & icmp protocols
            # For each protocol, set expected result based on action - pass or deny
            # if action = 'pass', expectedResult= True, else Fail;
            test_flow_list, matching_rule_action = self.build_test_flow(
                policy, test_vm1, test_vm2, topo, config_topo, traffic_proto_l, total_streams, dpi)
            self.logger.info(
                "test_flow_list after setting action as follows: %s" %
                test_flow_list)
            # time.sleep(30)  # Wait for new flows to establish and temp flows to settle down..
            #out= self.validate_flow_in_kernel(test_flow_list, test_vn)
            # if out['status'] != True:
            #    err_msg.extend (["Kernel flow validation failed after policy update, details - ", out['msg']])
            #    self.logger.error (err_msg)
            #self.assertEqual(out['status'], True, err_msg)
            out = self.validate_flow_in_vna(
                test_flow_list, test_vn, config_topo['vn'])
            expected_status = True
            if out['status'] != expected_status:
                err_msg.extend(
                    ["Flows not programmed as expected in computes after policy update - ", out['msg']])
                self.logger.error(err_msg)
            self.assertEqual(out['status'], expected_status, err_msg)
            self.logger.info("-" * 80)
            expectedResult = {}
            for proto in traffic_proto_l:
                expectedResult[proto] = True if matching_rule_action[
                    proto] == 'pass' else False
            # poll traffic and get status - traffic_stats['msg'],
            # traffic_stats['status']
            self.logger.info("TEST STEP -4b: Poll traffic and validate")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                m = (
                    " --> flow for proto %s, traffic result expected: %s, got: %s" %
                    (proto, expectedResult[proto], traffic_stats['status']))
                self.logger.info(m)
                err_msg = [m] + [policy_info] + traffic_stats['msg']
                self.assertEqual(
                    traffic_stats['status'], expectedResult[proto], err_msg)
        # end for loop
        self.logger.info("-" * 80)
        # Stop Traffic
        self.logger.info("TEST STEP -5: stop traffic")
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
        # 6. Verify flow aging(expect flows to exist for 180s after stopping
        # traffic)
        self.logger.info(
            "TEST STEP -6: Check for flow existence after stopping traffic")
        wait_time = 150
        time.sleep(wait_time)
        self.logger.info(
            "Checking for flows after %s secs after stopping traffic" %
            wait_time)
        expected_status = False
        #out= self.validate_flow_in_kernel(test_flow_list, test_vn)
        # if out['status'] != expected_status:
        #    err_msg.extend (["In flow aging check: Kernel flow validation failed - ", "expected_status: ", expected_status, "actual status: ", out['status'], "error info: ", out['msg']])
        #    self.logger.error (err_msg)
        recheck = 3
        while recheck > 0:
            err_msg = []
            out = self.validate_flow_in_vna(
                test_flow_list, test_vn, config_topo['vn'])
            if out['few_flows_found'] != expected_status:
                err_msg.extend(
                    [
                        "In flow aging check, time_elapsed_since_stop_traffic: ",
                        wait_time,
                        "Flows have not aged out as expected in computes, retry if allowed.. error info: ",
                        out['flows_found']])
                self.logger.warn(err_msg)
                time.sleep(30)
                recheck = recheck - 1
                wait_time += 30
            else:
                self.logger.info("no flows found as expected..")
                recheck = 0
        self.assertEqual(out['status'], expected_status, err_msg)
        self.logger.info("-" * 80)
        return result
    # end test_policy_modify_rules_of_live_flows

    @preposttest_wrapper
    def test_policy_with_scaled_udp_flows(self):
        """ Test focus on scaling flows.. With 2VN's and nVM's based on num computes, launch UDP streams from all VM's.
        """
        computes = len(self.inputs.compute_ips)
        vms_per_compute = 2
        num_streams = 800
        topology_class_name = sdn_policy_traffic_test_topo.sdn_2vn_xvm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo_params = "project=self.project.project_name, username=self.project.username, password=self.project.password"
        except NameError:
            topo_params = ""
        topo_params = topo_params + \
            "num_compute=computes, num_vm_per_compute=vms_per_compute"
        topo = topology_class_name(topo_params)
        planned_per_compute_num_streams = vms_per_compute * num_streams
        total_streams_generated = planned_per_compute_num_streams * computes
        self.logger.info("Total streams to be generated per compute: %s" %
                         planned_per_compute_num_streams)
        self.logger.info("Total streams to be generated : %s" %
                         total_streams_generated)
        return self.policy_test_with_scaled_udp_flows(
            topo,
            num_udp_streams=num_streams,
            pps=100,
            wait_time_after_start_traffic=10)

    def policy_test_with_scaled_udp_flows(
            self,
            topo,
            num_udp_streams=100,
            pps=100,
            wait_time_after_start_traffic=300,
            vms_on_single_compute=False,
            setup_only=False):
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
        if out['result']:
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
        startStatus = {}
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
                trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture, rx_vm_fixture, \
            # stream_proto, packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20)
            startStatus[i] = traffic_obj[i].startTraffic(
                tx_vm_fixture=test_vm1_fixture,
                rx_vm_fixture=test_vm2_fixture,
                total_single_instance_streams=total_single_instance_streams,
                cfg_profile='ContinuousSportRange',
                pps=pps)
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

    @preposttest_wrapper
    def test_policy_verify_flows_unaffected_by_policy_update(self):
        """
        Configure 2 traffic streams, of same proto but to different vm's in 2 different vn's
        vn0 policy: one allow udp to vn1, other deny udp to vn2
        vn1, vn2 policy- allow any
        validate live traffic for both streams
        modify policy of vn0 to allow udp to vn2
        validate live traffic for both streams
        stop traffic and validate total recd for unaffected, should be same as sent
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_3vn_3vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_verify_flows_unaffected_by_policy_update(topo)

    def policy_test_verify_flows_unaffected_by_policy_update(self, topo):
        """Pick 2 VM's for testing, have rules affecting udp protocol..
        Generate traffic streams matching policy rules - udp for now..
        assert if traffic failure is seen as no disruptive trigger is applied here..
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(flavor='contrail_flavor_small')
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # Setup/Verify Traffic ---
        # 1. Define Traffic Params
        # Traffic streams: vnet0<-->vnet1, vnet0<-->vnet2
        # vnet0 to vnet1 to be unaffected and stats to be checked after stopping traffic
        # vnet0 to vnet2 to be affected and stats to be ignored after stopping
        # traffic
        topo.vnet_list = sorted(topo.vnet_list)
        test_vn = topo.vnet_list[0]
        vm_vn_to_check = 'vnet1'
        topo_helper_obj = topology_helper(topo)
        vms_in_vn = topo_helper_obj.get_vm_of_vn()
        test_vm1 = vms_in_vn['vnet0'][0]
        test_vm2 = vms_in_vn['vnet1'][0]
        test_vm3 = vms_in_vn['vnet2'][0]
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vm3_fixture = config_topo['vm'][test_vm3]
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        dest_vn_vm_dict = {topo.vn_of_vm[test_vm2]: test_vm2_fixture,
                           topo.vn_of_vm[test_vm3]: test_vm3_fixture}
        # 2. set expectation to verify..
        matching_rule_action = {}
        # Assumption made here: test_vn, which is traffic source, has one
        # policy, with one rule for each dest vn..
        policy = topo.vn_policy[test_vn][0]
        policy_info = "policy in effect is : " + str(topo.rules[policy])
        num_rules = len(topo.rules[policy])
        for dest_vn, dest_vm_fixture in dest_vn_vm_dict.items():
            matching_rule_action[dest_vn] = 'deny'  # init to deny
            for i in range(num_rules):
                vn = topo.rules[policy][i]['dest_network']
                if vn == dest_vn:
                    matching_rule_action[dest_vn] = topo.rules[
                        policy][i]['simple_action']
                    break
        self.logger.info("matching_rule_action: %s" % matching_rule_action)
        # 3. Start Traffic
        traffic_obj = {}
        startStatus = {
        }
        stopStatus = {}
        expectedResult = {}
        for dest_vn, dest_vm_fixture in dest_vn_vm_dict.items():
            expectedResult[dest_vn] = True if matching_rule_action[
                dest_vn] == 'pass' else False
            traffic_obj[dest_vn] = self.useFixture(
                trafficTestFixture(self.connections))
            startStatus[dest_vn] = traffic_obj[dest_vn].startTraffic(
                name=dest_vn,
                tx_vm_fixture=test_vm1_fixture,
                rx_vm_fixture=dest_vm_fixture,
                cfg_profile='ContinuousSportRange')
            msg1 = "Status of start traffic : %s, %s, %s" % (
                dest_vn, test_vm1_fixture.vm_ip, startStatus[dest_vn]['status'])
            if startStatus[dest_vn]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[dest_vn]['msg']])
            else:
                self.logger.info(msg1)
            self.assertEqual(startStatus[dest_vn]['status'], True, msg)
        self.logger.info("-" * 80)
        self.logger.info("TEST STEP -4: modify policy")
        starting_policy_name = policy
        starting_policy_fixture = config_topo['policy'][policy]
        starting_policy_id = starting_policy_fixture.policy_obj['policy']['id']
        for policy in topo.policy_test_order:
            # set new policy for test_vn to rules of policy
            new_policy_entries = config_topo['policy'][
                policy].policy_obj['policy']['entries']
            data = {'policy': {'entries': new_policy_entries}}
            update_status = starting_policy_fixture.update_policy(
                starting_policy_id, data)
            new_rules = topo.rules[policy]
            # policy= current_policy_name     #policy name is still old one
            # update new rules in reference topology
            topo.rules[starting_policy_name] = copy.copy(new_rules)
            state = "policy for " + test_vn + " updated to rules of " + policy
            # wait for tables update before checking after making changes to
            # system
            time.sleep(5)
            policy_info = "policy in effect is : %s" % (topo.rules[policy])
            self.logger.info(policy_info)
        # Done with policy updates..
        # 5. Stop Traffic & validate received packets..
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for dest_vn, dest_vm_fixture in dest_vn_vm_dict.items():
            stopStatus[dest_vn] = traffic_obj[dest_vn].stopTraffic()
            # Check the status only if the stream is unaffected by policy
            # change
            if dest_vn == vm_vn_to_check:
                self.logger.info(
                    "Status of stop traffic for dest_vn %s is %s" %
                    (dest_vn, stopStatus[dest_vn]))
                status = True if stopStatus[dest_vn] == [] else False
                if not status:
                    msg.append(stopStatus[dest_vn])
                    result = False
        self.assertEqual(result, True, msg)
        self.logger.info("-" * 80)
        return result
    # end policy_test_verify_flows_unaffected_by_policy_update

    @preposttest_wrapper
    def test_policy_across_projects(self):
        '''
         Traffic test with policy applied across multiple projects
        '''
        #
        # Get config for test from topology
        result = True
        msg = []
        topology_class_name = sdn_policy_topo_with_multi_project.sdn_basic_policy_topo_with_3_project

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo_obj = topology_class_name()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        topo = {}
        topo_objs = {}
        config_topo = {}
        for project in topo_obj.project_list:
            setup_obj = {}
            topo[project] = eval("topo_obj.build_topo_" + project + "()")
            setup_obj[project] = self.useFixture(
                sdnTopoSetupFixture(self.connections, topo[project]))
            out = setup_obj[project].topo_setup()
            self.assertEqual(out['result'], True, out['msg'])
            if out['result']:
                topo_objs[project], config_topo[project] = out['data']
            try:
                for pp in topo_obj.project_list:
                    self.logger.info('topo of %s is %s' %(pp, topo_objs[pp].project))
            except:
                pass
            self.logger.info("Setup completed for project %s with result %s" %
                             (project, out['result']))
        exit
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
                tx_vm_fixt = config_topo[p_lst[0]]['vm'][p1vm1]
                rx_vm_fixt = config_topo[p_lst[1]]['vm'][p2vm2]
            else:
                tx_vm_fixt = config_topo[p_lst[0]]['vm'][p1vm1]
                rx_vm_fixt = config_topo[p_lst[2]]['vm'][p3vm3]

            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=tx_vm_fixt,
                rx_vm_fixture=rx_vm_fixt,
                stream_proto=proto)
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
            "With proto tcp allowed between %s and %s, trying to send icmp traffic" %
            (p1vm1, p3vm3))
        expectedResult = False
        self.logger.info(
            "Verify ping to vm %s from vm %s, expecting it to fail" %
            (dst_vm, src_vm))
        ret = src_vm_fixture.ping_with_certainty(
            dst_vm_ip, expectation=expectedResult)
        result_msg = "vm ping test result to vm %s is: %s" % (dst_vm, ret)
        self.logger.info(result_msg)
        if not ret:
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
        if not ret:
            result = False
            msg.extend(
                ["ICMP traffic failed between default and non-default project with policy:", result_msg])
        self.assertEqual(result, True, msg)
        return True
    # end test_policy_across_projects

    def traffic_generator_for_proto_list(self, proto_list, source_fixture, dest_fixture, dpi, policy_info, topo):
        # 1. Start Traffic
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 1
        total_streams['tcp'] = 1
        traffic_proto_l = proto_list.keys()
        expectedResult = {}
        start_time = self.analytics_obj.getstarttime(
            self.inputs.compute_ips[0])
        for proto in traffic_proto_l:
            expectedResult[proto] = True if proto_list[
                proto] == 'pass' else False
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=source_fixture, rx_vm_fixture=dest_fixture, stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, source_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
                self.assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # 2. Poll live traffic
        # poll traffic and get status - traffic_stats['msg'],
        # traffic_stats['status']
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = [policy_info] + traffic_stats['msg']
            self.logger.info(" --> , flow proto: %s, expected: %s, got: %s" %
                             (proto, expectedResult[proto], traffic_stats['status']))
            self.assertEqual(traffic_stats['status'],
                             expectedResult[proto], err_msg)
        self.logger.info("-" * 80)
        # 3. Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        traffic_stats = {}
        for proto in traffic_proto_l:
            try:
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
            except Exception as e:
                self.logger.exception("Got exception in stopTraffic() as:- %s"%(e))
            status = True if stopStatus[proto] == [] else False
            if status != expectedResult[proto]:
                msg.append(stopStatus[proto])
                result = False
                self.logger.info("Status of stop traffic for proto %s is %s" %
                                 (proto, stopStatus[proto]))
                # Get the traffic Stats for each protocol sent
                traffic_stats[proto] = traffic_obj[proto].returnStats()
                time.sleep(5)
        return (self.assertEqual(result, True, msg))
        # End of traffic_generator_for_proto_list

    def parse_and_build_implicit_rule(self, policy, topo):
        # 1 Get the implicit rule for both same and different network from the
        # policy
        chk_policy = topo.rules[policy]
        num_rules = len(chk_policy)
        intra_vn_explicit_proto = {}
        inter_vn_explicit_proto = {}
        intra_vn_ntw = {'dst_port': 9100, 'src_port': 9100}
        inter_vn_ntw = {'dst_port': 9100, 'src_port': 9100}
        new_port = 9100
        min = 1
        max = 65535
        # Getting the explicit protocol list and port number for selected
        # explicit rule.
        for i in range(num_rules):
            if (chk_policy[i]['dest_network'] ==
                    chk_policy[i]['source_network']):
                if ((chk_policy[i]['src_ports'] != chk_policy[i]['dst_ports']) and (
                        chk_policy[i]['protocol'] == 'tcp' or 'udp'or 'any')):
                    if (chk_policy[i]['src_ports'] != 'any'):
                        port_range = chk_policy[i]['src_ports']
                        start_port = port_range[0]
                        end_port = port_range[1]
                        num = range(min, start_port) + range(end_port, max)
                        new_port = random.choice(num)
                        intra_vn_ntw['src_port'] = new_port
                        intra_vn_ntw['src_ntw'] = chk_policy[
                            i]['source_network']
                        intra_vn_ntw[
                            'dst_ntw'] = chk_policy[i]['dest_network']
                    else:
                        port_range = chk_policy[i]['dst_ports']
                        start_port = port_range[0]
                        end_port = port_range[1]
                        num = range(min, start_port) + range(end_port, max)
                        new_port = random.choice(num)
                        intra_vn_ntw['dst_port'] = new_port
                        intra_vn_ntw['src_ntw'] = chk_policy[
                            i]['source_network']
                        intra_vn_ntw[
                            'dst_ntw'] = chk_policy[i]['dest_network']
                elif ((chk_policy[i]['src_ports'] == chk_policy[i]['dst_ports']) and (chk_policy[i]['protocol'] == 'any')):
                    intra_vn_explicit_proto[
                        chk_policy[i]['protocol']] = chk_policy[i]['simple_action']
                    intra_vn_ntw['dst_ntw'] = chk_policy[i]['dest_network']
                    intra_vn_ntw[
                        'src_ntw'] = chk_policy[i]['source_network']
                    intra_vn_ntw['src_port'] = new_port
                    intra_vn_ntw[
                        'dst_port'] = new_port
                    self.logger.info(
                        "Defined Explicit rule#:%d  for same network :src_net= %s, dst_net=%s, src_port= %s, dst_port=%s, protocol:%s,action= %s " %
                        (i,
                         chk_policy[i]['source_network'],
                            chk_policy[i]['dest_network'],
                            chk_policy[i]['src_ports'],
                            chk_policy[i]['dst_ports'],
                            chk_policy[i]['protocol'],
                            chk_policy[i]['simple_action']))
                    break
                elif ((chk_policy[i]['src_ports'] == chk_policy[i]['dst_ports']) and (chk_policy[i]['protocol'] == 'tcp' or 'udp' or 'icmp')):
                    intra_vn_explicit_proto[
                        chk_policy[i]['protocol']] = chk_policy[i]['simple_action']
                    intra_vn_ntw['dst_ntw'] = chk_policy[i]['dest_network']
                    intra_vn_ntw[
                        'src_ntw'] = chk_policy[i]['source_network']
                    intra_vn_ntw['src_port'] = new_port
                    intra_vn_ntw[
                        'dst_port'] = new_port
                self.logger.info(
                    "Defined Explicit rule#:%d  for same network :src_net= %s, dst_net=%s, src_port= %s, dst_port=%s, protocol:%s,action= %s " %
                    (i,
                     chk_policy[i]['source_network'],
                        chk_policy[i]['dest_network'],
                        chk_policy[i]['src_ports'],
                        chk_policy[i]['dst_ports'],
                        chk_policy[i]['protocol'],
                        chk_policy[i]['simple_action']))
            elif (chk_policy[i]['dest_network'] != chk_policy[i]['source_network']):
                if ((chk_policy[i]['src_ports'] != chk_policy[i]['dst_ports']) and (
                        chk_policy[i]['protocol'] == 'tcp' or 'udp' or 'any')):
                    if (chk_policy[i]['src_ports'] != 'any'):
                        port_range = chk_policy[i]['src_ports']
                        start_port = port_range[0]
                        end_port = port_range[1]
                        num = range(min, start_port) + range(end_port, max)
                        new_port = random.choice(num)
                        inter_vn_ntw['src_port'] = new_port
                        inter_vn_ntw['src_ntw'] = chk_policy[
                            i]['source_network']
                        inter_vn_ntw[
                            'dst_ntw'] = chk_policy[i]['dest_network']
                    else:
                        port_range = chk_policy[i]['dst_ports']
                        start_port = port_range[0]
                        end_port = port_range[1]
                        num = range(min, start_port) + range(end_port, max)
                        new_port = random.choice(num)
                        inter_vn_ntw['dst_port'] = new_port
                        inter_vn_ntw['src_ntw'] = chk_policy[
                            i]['source_network']
                        inter_vn_ntw[
                            'dst_ntw'] = chk_policy[i]['dest_network']
                elif ((chk_policy[i]['src_ports'] == chk_policy[i]['dst_ports']) and (chk_policy[i]['protocol'] == 'any')):
                    inter_vn_explicit_proto[
                        chk_policy[i]['protocol']] = chk_policy[i]['simple_action']
                    inter_vn_ntw['dst_ntw'] = chk_policy[i]['dest_network']
                    inter_vn_ntw[
                        'src_ntw'] = chk_policy[i]['source_network']
                    inter_vn_ntw['src_port'] = new_port
                    inter_vn_ntw[
                        'dst_port'] = new_port
                    self.logger.info(
                        "Defined Explicit rule#:%d for two different network  :src_net= %s, dst_net=%s, src_port= %s, dst_port=%s, protocol:%s,action= %s " %
                        (i,
                         chk_policy[i]['source_network'],
                            chk_policy[i]['dest_network'],
                            chk_policy[i]['src_ports'],
                            chk_policy[i]['dst_ports'],
                            chk_policy[i]['protocol'],
                            chk_policy[i]['simple_action']))
                    break
                elif ((chk_policy[i]['src_ports'] == chk_policy[i]['dst_ports']) and (chk_policy[i]['protocol'] == 'tcp' or 'udp' or 'icmp')):
                    inter_vn_explicit_proto[
                        chk_policy[i]['protocol']] = chk_policy[i]['simple_action']
                    inter_vn_ntw['dst_ntw'] = chk_policy[i]['dest_network']
                    inter_vn_ntw[
                        'src_ntw'] = chk_policy[i]['source_network']
                    inter_vn_ntw['src_port'] = new_port
                    inter_vn_ntw[
                        'dst_port'] = new_port
                self.logger.info(
                    "Defined Explicit rule#:%d for two different network  :src_net= %s, dst_net=%s, src_port= %s, dst_port=%s, protocol:%s,action= %s " %
                    (i,
                     chk_policy[i]['source_network'],
                        chk_policy[i]['dest_network'],
                        chk_policy[i]['src_ports'],
                        chk_policy[i]['dst_ports'],
                        chk_policy[i]['protocol'],
                        chk_policy[i]['simple_action']))
        # 2 Building the implicit rule based selected explicit protocols and
        # Insert the remaing implicit protocols
        final_intra_vn_implicit_rule = {}
        final_inter_vn_implicit_rule = {}
        proto_intra_vn_len = len(intra_vn_explicit_proto)
        proto_inter_vn_len = len(inter_vn_explicit_proto)
        if proto_intra_vn_len == 1:
            if 'tcp' in intra_vn_explicit_proto:
                final_intra_vn_implicit_rule = {'udp': 'pass', 'icmp': 'pass'}
            elif 'udp' in intra_vn_explicit_proto:
                final_intra_vn_implicit_rule = {'tcp': 'pass', 'icmp': 'pass'}
            elif 'icmp' in intra_vn_explicit_proto:
                final_intra_vn_implicit_rule = {'udp': 'pass', 'tcp': 'pass'}
            elif 'any' in intra_vn_explicit_proto:
                final_intra_vn_implicit_rule = {
                    'tcp': intra_vn_explicit_proto['any'],
                    'udp': intra_vn_explicit_proto['any'],
                    'icmp': intra_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for same network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif (proto_intra_vn_len == 0 and (intra_vn_ntw['dst_port'] != 9100 or intra_vn_ntw['src_port'] != 9100)):
            final_intra_vn_implicit_rule = {
                'udp': 'pass', 'icmp': 'pass', 'tcp': 'pass'}
        elif proto_intra_vn_len == 2:
            if ('tcp' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {'icmp': 'pass'}
            elif ('tcp' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {'udp': 'pass'}
            elif ('udp' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {'tcp': 'pass'}
            elif ('any' in intra_vn_explicit_proto and 'tcp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'udp': intra_vn_explicit_proto['any'],
                    'icmp': intra_vn_explicit_proto['any']}
            elif ('any' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'tcp': intra_vn_explicit_proto['any'],
                    'icmp': intra_vn_explicit_proto['any']}
            elif ('any' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'tcp': intra_vn_explicit_proto['any'],
                    'udp': intra_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for same network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif proto_intra_vn_len == 3:
            if (
                    'tcp' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto):
                self.logger.error(
                    ("No need to run the implicit rule for defined explicit rules "))
            elif ('tcp' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto and 'any' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'icmp': intra_vn_explicit_proto['any']}
            elif ('tcp' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto and 'any' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'udp': intra_vn_explicit_proto['any']}
            elif ('icmp' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto and 'any' in intra_vn_explicit_proto):
                final_intra_vn_implicit_rule = {
                    'tcp': intra_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for same network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif proto_intra_vn_len == 4:
            if ('tcp' in intra_vn_explicit_proto and 'udp' in intra_vn_explicit_proto and 'icmp' in intra_vn_explicit_proto and
                    'any' in intra_vn_explicit_proto):
                self.logger.error(
                    ("No need to run the implicit rule for defined explicit rules "))
            else:
                self.logger.error(
                    "All three protocols are not defined properly in policy for same network combination.")
                sys.exit(0)
        elif proto_intra_vn_len > 4:
            self.logger.error(
                "Only TCP,UDP and ICMP protocols are applicable for same network, Please define the proper protocol rules in policy")
            sys.exit(0)
        else:
            pass

        if proto_inter_vn_len == 1:
            if 'tcp' in inter_vn_explicit_proto:
                final_inter_vn_implicit_rule = {'udp': 'deny', 'icmp': 'deny'}
            elif 'udp' in inter_vn_explicit_proto:
                final_inter_vn_implicit_rule = {'tcp': 'deny', 'icmp': 'deny'}
            elif 'icmp' in inter_vn_explicit_proto:
                final_inter_vn_implicit_rule = {'udp': 'deny', 'tcp': 'deny'}
            elif 'any' in inter_vn_explicit_proto:
                final_inter_vn_implicit_rule = {
                    'tcp': inter_vn_explicit_proto['any'],
                    'udp': inter_vn_explicit_proto['any'],
                    'icmp': inter_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for different network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif (proto_inter_vn_len == 0 and (inter_vn_ntw['dst_port'] != 9100 or inter_vn_ntw['src_port'] != 9100)):
            final_inter_vn_implicit_rule = {
                'udp': 'deny', 'icmp': 'deny', 'tcp': 'deny'}
        elif proto_inter_vn_len == 2:
            if ('tcp' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto):
                final_inter_vn_explicit_rule = {'icmp': 'deny'}
            elif ('tcp' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {'udp': 'deny'}
            elif ('udp' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {'tcp': 'deny'}
            elif ('any' in inter_vn_explicit_proto and 'tcp' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'udp': inter_vn_explicit_proto['any'],
                    'icmp': inter_vn_explicit_proto['any']}
            elif ('any' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'tcp': inter_vn_explicit_proto['any'],
                    'icmp': inter_vn_explicit_proto['any']}
            elif ('any' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'tcp': inter_vn_explicit_proto['any'],
                    'udp': inter_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for different network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif proto_inter_vn_len == 3:
            if (
                    'tcp' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto):
                self.logger.info(
                    "No need to run the implicit rule for defined explicit rules ")
            elif ('tcp' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto and 'any' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'icmp': inter_vn_explicit_proto['any']}
            elif ('tcp' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto and 'any' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'udp': inter_vn_explicit_proto['any']}
            elif ('icmp' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto and 'any' in inter_vn_explicit_proto):
                final_inter_vn_implicit_rule = {
                    'tcp': inter_vn_explicit_proto['any']}
            else:
                self.logger.error(
                    "Only TCP,UDP and ICMP protocols are applicable for different network, Please define the proper protocol rules in policy")
                sys.exit(0)
        elif proto_inter_vn_len == 4:
            if ('tcp' in inter_vn_explicit_proto and 'udp' in inter_vn_explicit_proto and 'icmp' in inter_vn_explicit_proto and
                    'any' in inter_vn_explicit_proto):
                self.logger.info(
                    "No need to run the implicit rule for defined explicit rules ")
            else:
                self.logger.error(
                    "All three protocols are not defined properly in policy for different network combination.")
        elif proto_inter_vn_len > 4:
            self.logger.error(
                "Only TCP,UDP and ICMP protocols are applicable for different network, Please define the proper protocol rules in policy")
            sys.exit(0)
        else:
            pass
        final_intra_vn_implicit_rule = dict(
            final_intra_vn_implicit_rule, **intra_vn_ntw)
        final_inter_vn_implicit_rule = dict(
            final_inter_vn_implicit_rule, **inter_vn_ntw)
        # sending the 5 tuple list of same and different network implicit rules
        # like implicit proto_list,src/dst ntws and ports
        return (final_intra_vn_implicit_rule, final_inter_vn_implicit_rule)
    # End parse_and_build_implicit_rule

    def translate_of_implicit_rule_into_flow_params(
            self,
            all_implicit_rule,
            config_topo,
            topo):
        # Defining the source network ,destination network ,src/dst ports and
        # protocol list to run the traffic
        if all_implicit_rule:
            dpi = 9100
            parse_im_rule = all_implicit_rule
            src_ntw = parse_im_rule['src_ntw']
            dst_ntw = parse_im_rule['dst_ntw']
            topo_helper_obj = topology_helper(topo)
            vms_from_vn = topo_helper_obj.get_vm_of_vn()
            if src_ntw == dst_ntw:
                source_vms = vms_from_vn[src_ntw]
                test_vm = source_vms[0]
                dst_vm = source_vms[1]
                source_fixture = config_topo['vm'][test_vm]
                dest_fixture = config_topo['vm'][dst_vm]
                source_ntw = src_ntw
                dest_ntw = dst_ntw
            else:
                source_vms = vms_from_vn[src_ntw]
                dest_vms = vms_from_vn[dst_ntw]
                test_vm = source_vms[0]
                dst_vm = dest_vms[0]
                source_fixture = config_topo['vm'][test_vm]
                dest_fixture = config_topo['vm'][dst_vm]
                source_ntw = src_ntw
                dest_ntw = dst_ntw
            if parse_im_rule['src_port'] != 9100:
                dpi = parse_im_rule['src_port']
            elif parse_im_rule['dst_port'] != 9100:
                dpi = parse_im_rule['src_port']
            if (
                    'tcp' in parse_im_rule and 'udp' in parse_im_rule and 'icmp' in parse_im_rule):
                proto_list = {
                    'tcp': parse_im_rule['tcp'],
                    'udp': parse_im_rule['udp'],
                    'icmp': parse_im_rule['icmp']}
            elif ('tcp' in parse_im_rule and 'udp' in parse_im_rule):
                proto_list = {
                    'tcp': parse_im_rule['tcp'],
                    'udp': parse_im_rule['udp']}
            elif ('tcp' in parse_im_rule and 'icmp' in parse_im_rule):
                proto_list = {
                    'tcp': parse_im_rule['tcp'],
                    'icmp': parse_im_rule['icmp']}
            elif ('udp' in parse_im_rule and 'icmp' in parse_im_rule):
                proto_list = {
                    'udp': parse_im_rule['udp'],
                    'icmp': parse_im_rule['icmp']}
            elif ('tcp' in parse_im_rule):
                proto_list = {'tcp': parse_im_rule['tcp']}
            elif ('icmp' in parse_im_rule):
                proto_list = {'icmp': parse_im_rule['icmp']}
            elif ('udp' in parse_im_rule):
                proto_list = {'udp': parse_im_rule['udp']}
        else:
            self.logger.error(
                "Implicit rules are not exist for defined policy")
        return (proto_list, source_fixture, dest_fixture, dpi)
        # End traslation_of_implicit_flow_params

    @preposttest_wrapper
    def test_policy_with_implict_rule_proto_traffic(self):
        """ Call policy_test_for_implicit_rule_proto_traffic with multi VN scenario.
        """
        topo = sdn_policy_traffic_test_topo.sdn_3vn_4vm_config()
        return self.policy_test_with_implicit_rule_proto_traffic(topo)

    def policy_test_with_implicit_rule_proto_traffic(self, topo):
        """ Pick 4 VM's for testing implicit rule for each policy and ...
        test VM will be same for both same  and different network.
        Generate traffic streams matching policy for  implicit rules - tcp,udp & icmp for now..
        assert if traffic failure is seen as no disruptive trigger is applied here..
        steps followed to generate and run the traffic for implicit rule
        1.Parsing the policy and Building the implicit rule for selected policy
        2.Translation of implicit rules into flow parameters for generating the traffic
        3.Generating the traffic for defined implicit rules either for same or different network.
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(skip_verify='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # Setup/Verify Traffic ---
        # 1. Define the Test VM params
        topo.vmc_list = sorted(topo.vmc_list)
        test_vm = topo.vmc_list[0]  # 'vmc0'
        test_vn = topo.vn_of_vm[test_vm]  # 'vnet0'
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        for policy in topo.policy_test_order:
            # 2. set new policy for test_vn to policy
            test_policy_fq_names = []
            name = config_topo['policy'][
                policy].policy_obj['policy']['fq_name']
            test_policy_fq_names.append(name)
            state = "policy for " + test_vn + " updated to " + policy
            test_vn_fix.bind_policies(test_policy_fq_names, test_vn_id)
            # wait for tables update before checking after making changes to
            # system
            time.sleep(5)
            self.logger.info("new policy list of vn %s is %s" %
                             (test_vn, policy))
            # update expected topology with this new info for verification
            updated_topo = policy_test_utils.update_topo(topo, test_vn, policy)
            self.logger.info("Starting Verifications after %s" % (state))
            policy_info = "policy in effect is : %s" % (topo.rules[policy])
            self.logger.info(policy_info)
            same_ntw_im_rule = {}
            diff_ntw_im_rule = {}
            # 3. Parsing  and Building the implicit rule for selected policy.
            same_ntw_im_rule, diff_ntw_im_rule = self.parse_and_build_implicit_rule(
                policy, topo)
            # 4. Traslation of flow parameters (5-tuples) and run the traffic
            # for same network implicit rule
            if (
                    'tcp' in same_ntw_im_rule or 'udp' in same_ntw_im_rule or 'icmp' in same_ntw_im_rule):
                proto_list, source_fixture, dest_fixture, dpi = self.translate_of_implicit_rule_into_flow_params(
                    same_ntw_im_rule, config_topo, topo)
                self.logger.info(
                    "For applied policy :%s ,Generated implicit rule for same network :%s" %
                    (policy, same_ntw_im_rule))
                self.logger.info(
                    "Generating the traffic flow for same network with combination of protocol list: %s ,source ip :%s , dest-ip:%s,port-id:%d" %
                    (proto_list, source_fixture.vm_ip, dest_fixture.vm_ip, dpi))
                im_flow_result = self.traffic_generator_for_proto_list(
                    proto_list,
                    source_fixture,
                    dest_fixture,
                    dpi,
                    policy_info,
                    topo)
                self.logger.info(
                    "Traffic flow generation is done for same network implicit rule :%s",
                    same_ntw_im_rule)
            # 5.Translation of implicit rule into flow parameters(5-tuples) and
            # run the traffic for different network implicit rule
            if (
                    'tcp' in diff_ntw_im_rule or 'udp' in diff_ntw_im_rule or 'icmp' in diff_ntw_im_rule):
                proto_list, source_fixture, dest_fixture, dpi = self.translate_of_implicit_rule_into_flow_params(
                    diff_ntw_im_rule, config_topo, topo)
                self.logger.info(
                    "For applied policy :%s ,Generated implicit rule for differnt network :%s" %
                    (policy, diff_ntw_im_rule))
                self.logger.info(
                    "Genarating the traffic flow for different network with combination of protocol list: %s ,source ip :%s , dest-ip:%s,port-id:%d" %
                    (proto_list, source_fixture.vm_ip, dest_fixture.vm_ip, dpi))
                im_flow_result = self.traffic_generator_for_proto_list(
                    proto_list,
                    source_fixture,
                    dest_fixture,
                    dpi,
                    policy_info,
                    topo)
                self.logger.info(
                    "Traffic flow generation is done for different network implicit rule :%s",
                    diff_ntw_im_rule)
        return result
    # end test_policy_with_implicit_proto_traffic

    def create_vn(self, vn_name, subnets):
        return self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections,
                      inputs=self.inputs,
                      vn_name=vn_name,
                      subnets=subnets))

    def create_vm(
            self,
            vn_fixture,
            vm_name,
            node_name=None,
            flavor='contrail_flavor_small',
            image_name='ubuntu-traffic'):
        image_name=os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        return self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture.obj,
                vm_name=vm_name,
                image_name=image_name,
                flavor=flavor,
                node_name=node_name))

    @preposttest_wrapper
    def test_policy_with_spl_char_in_name(self):
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]

        policy_name = 'policy1' + gen_str_with_spl_char(10)

        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]

        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn2_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn2_fixture.vn_id)

        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        assert vn1_fixture.verify_on_setup()

        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        assert vn2_fixture.verify_on_setup()

        vn1_vm1_name = get_random_name('vn1_vm1')
        vn2_vm1_name = get_random_name('vn2_vm1')
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn2_vm1_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            self.logger.error(
                'Ping from %s to %s failed, expected it to pass' %
                (vm1_fixture.vm_name, vm2_fixture.vm_name))
            result = False
        if not vm2_fixture.ping_to_ip(vm1_fixture.vm_ip):
            self.logger.error(
                'Ping from %s to %s failed, expected it to pass' %
                (vm2_fixture.vm_name, vm1_fixture.vm_name))
            result = False

        self.inputs.restart_service('ifmap', host_ips=self.inputs.cfgm_ips)

        sleep(120)
        #Revisit this once contrail-status cli work is complete

        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            self.logger.error(
                'Ping from %s to %s failed, expected it to pass' %
                (vm1_fixture.vm_name, vm2_fixture.vm_name))
            result = False
        if not vm2_fixture.ping_to_ip(vm1_fixture.vm_ip):
            self.logger.error(
                'Ping from %s to %s failed, expected it to pass' %
                (vm2_fixture.vm_name, vm1_fixture.vm_name))
            result = False

        return result

    # end of class TestSerialPolicy
