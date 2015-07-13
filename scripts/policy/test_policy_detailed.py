from base import BasePolicyTest
from tcutils.wrappers import preposttest_wrapper
import test
from vn_test import *
from quantum_test import *
from policy_test import *
from vm_test import *
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from common.system.system_verification import system_vna_verify_policy
from common.system.system_verification import all_policy_verify
from common.policy import policy_test_helper
from tcutils.test_lib.test_utils import assertEqual
import sdn_single_vm_multiple_policy_topology
import sdn_policy_traffic_test_topo


class TestDetailedPolicy0(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy0, cls).setUpClass()

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_repeated_policy_modify(self):
        """ Configure policies based on topology; Replace VN's existing policy [same policy name but with different rule set] multiple times and verify.
        """
        ###
        # Get config for test from topology
        # very simple topo will do, one vn, one vm, multiple policies with n
        # rules
        topology_class_name = sdn_single_vm_multiple_policy_topology.sdn_single_vm_multiple_policy_config
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
        ###
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(
                self.connections,
                topo))
        out = setup_obj.topo_setup()
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        ###
        # Verify [and assert on fail] after setup
        # Calling system policy verification, pick any policy fixture to
        # access fixture verification
        policy_name = topo.policy_list[0]
        system_vna_verify_policy(
            self,
            config_topo['policy'][policy_name],
            topo,
            'setup')
        ###
        # Test procedure:
        # Test repeated update of a policy attached to a VM
        test_vm = topo.vmc_list[0]
        test_vn = topo.vn_of_vm[test_vm]
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        for policy in topo.policy_list:
            # set new policy for test_vn to policy
            test_policy_fq_names = []
            name = config_topo['policy'][policy].policy_fq_name
            test_policy_fq_names.append(name)
            state = "policy for %s updated to %s" % (test_vn, policy)
            test_vn_fix.bind_policies(test_policy_fq_names, test_vn_id)
            # wait for tables update before checking after making changes to
            # system
            time.sleep(5)
            self.logger.info(
                "new policy list of vn %s is %s" %
                (test_vn, policy))
            # update expected topology with this new info for verification
            updated_topo = policy_test_utils.update_topo(topo, test_vn, policy)
            system_vna_verify_policy(
                self,
                config_topo['policy'][policy],
                updated_topo,
                state)
        return True
    # end test_repeated_policy_modify

# end of class TestDetailedPolicy0


class TestDetailedPolicy1(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy1, cls).setUpClass()

    @preposttest_wrapper
    def test_single_vn_repeated_policy_update_with_ping(self):
        """ Call repeated_policy_update_test_with_ping with single VN scenario.
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
        return self.repeated_policy_update_test_with_ping(topo)

    @test.attr(type=['sanity', 'ci_sanity_WIP', 'vcenter'])
    @preposttest_wrapper
    def test_multi_vn_repeated_policy_update_with_ping(self):
        """ Call repeated_policy_update_test_with_ping with multi VN scenario.
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
        return self.repeated_policy_update_test_with_ping(topo)

    def repeated_policy_update_test_with_ping(self, topo):
        """ Pick 2 VM's for testing, test with ping; modify policy of one VN [in which VM is
        present] and verify the rule functionality with ping.
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # 1. Define Traffic Params
        test_vm1 = topo.vmc_list[0]  # 'vmc0'
        test_vm2 = topo.vmc_list[1]  # 'vmc1'
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vn = topo.vn_of_vm[test_vm1]  # 'vnet0'
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        test_proto = 'icmp'
        for policy in topo.policy_test_order:
            # 2. set new policy for test_vn to policy
            test_policy_fq_names = []
            name = config_topo['policy'][policy].policy_fq_name
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
            # 3. set expectation to verify..
            matching_rule_action = {}
            # Topology guide: There is only one policy assigned to test_vn and there is one rule affecting traffic proto.
            # For ping test, set expected result based on action - pass or deny
            # if action = 'pass', expectedResult= True, else Fail;
            num_rules = len(topo.rules[policy])
            for i in range(num_rules):
                proto = topo.rules[policy][i]['protocol']
                matching_rule_action[proto] = topo.rules[
                    policy][i]['simple_action']
            if num_rules == 0:
                matching_rule_action[test_proto] = 'deny'
            self.logger.info("matching_rule_action: %s" %
                             matching_rule_action)
            # 4. Test with ping
            expectedResult = True if matching_rule_action[
                test_proto] == 'pass' else False
            ret = test_vm1_fixture.ping_with_certainty(
                test_vm2_fixture.vm_ip, expectation=expectedResult)
            result_msg = "vm ping test result after %s is: %s" % (state, ret)
            self.logger.info(result_msg)
            if not ret:
                result = False
                msg.extend([result_msg, policy_info])
                all_policy_verify(
                    self, config_topo, updated_topo, state, fixture_only='yes')
        assertEqual(result, True, msg)
        test_vn_fix.unbind_policies(test_vn_id)
        return result
    # end test_repeated_policy_update_with_ping

# end of class TestDetailedPolicy1


class TestDetailedPolicy2(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy2, cls).setUpClass()

    @preposttest_wrapper
    def test_policy_rules_scaling_with_ping(self):
        ''' Test to validate scaling of policy and rules
        '''
        result = True
        msg = []
        vn1_name = 'vn1'
        vn2_name = 'vn2'
        vn1_subnets = ['10.1.1.0/24']
        vn2_subnets = ['20.1.1.0/24']
        number_of_policy = 10
        # adding workaround to pass the test with less number of rules till
        # 1006, 1184 fixed
        number_of_dummy_rules = 148
        valid_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]

        self.logger.info(
            'Creating %d policy and %d rules to test policy scalability' %
            (number_of_policy, number_of_dummy_rules + len(valid_rules)))
        # for now we are creating limited number of policy and rules
        policy_objs_list = policy_test_helper._create_n_policy_n_rules(
            self, number_of_policy, valid_rules, number_of_dummy_rules)
        time.sleep(5)
        self.logger.info('Create VN and associate %d policy' %
                         (number_of_policy))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets,
                policy_objs=policy_objs_list))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets,
                policy_objs=policy_objs_list))
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn1_vm2_name))
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
            msg.extend(
                ["ping failure with scaled policy and rules:", result_msg])
        assertEqual(result, True, msg)
        return True
    # end test_policy_rules_scaling_with_ping

# end of class TestDetailedPolicy2


class TestDetailedPolicy3(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy3, cls).setUpClass()

    @preposttest_wrapper
    def test_scale_policy_with_ping(self):
        """ Test focus is on the scale of VM/VN created..have polict attached to all VN's and ping from one VM to all.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_20vn_20vm_config
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
        return self.policy_scale_test_with_ping(topo)

    def policy_scale_test_with_ping(self, topo):
        """ Setup multiple VM, VN and policies to allow traffic. From one VM, send ping to all VMs to test..
        Test focus is on the scale of VM/VN created..
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        # 1. Define Traffic Params
        test_vm1 = topo.vmc_list[0]  # 'vmc0'
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vn = topo.vn_of_vm[test_vm1]  # 'vnet0'
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        test_proto = 'icmp'
        # Assumption: one policy per VN
        policy = topo.vn_policy[test_vn][0]
        policy_info = "policy in effect is : " + str(topo.rules[policy])
        self.logger.info(policy_info)
        for vmi in range(1, len(topo.vn_of_vm.items())):
            test_vm2 = topo.vmc_list[vmi]
            test_vm2_fixture = config_topo['vm'][test_vm2]
            # 2. set expectation to verify..
            # Topology guide: One policy attached to VN has one rule for protocol under test
            # For ping test, set expected result based on action - pass or deny
            # if action = 'pass', expectedResult= True, else Fail;
            matching_rule_action = {}
            num_rules = len(topo.rules[policy])
            for i in range(num_rules):
                proto = topo.rules[policy][i]['protocol']
                matching_rule_action[proto] = topo.rules[
                    policy][i]['simple_action']
            self.logger.info("matching_rule_action: %s" %
                             matching_rule_action)
            # 3. Test with ping
            self.logger.info("Verify ping to vm %s" % (vmi))
            expectedResult = True if matching_rule_action[
                test_proto] == 'pass' else False
            ret = test_vm1_fixture.ping_with_certainty(
                test_vm2_fixture.vm_ip, expectation=expectedResult)
            result_msg = "vm ping test result to vm %s is: %s" % (vmi, ret)
            self.logger.info(result_msg)
            if not ret:
                result = False
                msg.extend([result_msg, policy_info])
        self.assertEqual(result, True, msg)
        return result
    # end test_policy_with_ping
