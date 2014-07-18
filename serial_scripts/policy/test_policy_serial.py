from vn_test import VNFixture
from policy_test import PolicyFixture
from vm_test import VMFixture
from base import BaseSerialPolicyTest
from tcutils.wrappers import preposttest_wrapper
from system_verification import assertEqual
from traffic_tests import trafficTestFixture
from time import sleep


class TestSerialPolicy(BaseSerialPolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestSerialPolicy, cls).setUpClass()

    @preposttest_wrapper
    def test_controlnode_switchover_policy_between_vns_traffic(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with control-node switchover without any traffic drops
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            self.logger.info(
                "Skiping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
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
        sleep(5)

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
        sleep(5)
        # bind the new policy to VN2
        vn2_fixture.bind_policies(policy_fq_name2, vn2_fixture.vn_id)
        sleep(5)

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

        sleep(10)
        # Check the BGP peering status from the currently active control node
        cn_bgp_entry = self.cn_inspect[
            new_active_controller].get_cn_bgp_neigh_entry()
        sleep(5)
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
        sleep(5)

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

# end of class TestSerialPolicy
