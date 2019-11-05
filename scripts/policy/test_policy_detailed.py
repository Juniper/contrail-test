from __future__ import absolute_import
from .base import BasePolicyTest
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
from . import sdn_single_vm_multiple_policy_topology
from . import sdn_policy_traffic_test_topo
from . import test_policy_basic

af_test = 'dual'

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

    @test.attr(type=['sanity'])
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
        test_vn = None
        for vn in topo.vn_policy:
            if 'policy0' in topo.vn_policy[vn]:
                test_vn = vn
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
                test_vm2_fixture.vm_ip, expectation=expectedResult,
                dst_vm_fixture=test_vm2_fixture)
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
        ''' Test to validate scaling of policy and rules.
            Test to validate multiple policy scaling with
            10 rules each. These policies will be attached
            to two VN's and 2 VM's will be spawned in each
            of the VN's to verify exact number of acls are
            created in the agent introspect.
            Expected ace id's = 150 policy * 10 distinct rules
            + 1 valid rule + 2 default rules = 1503 ace id's.
        '''
        result = True
        msg = []
        vn1_name = 'vn1'
        vn2_name = 'vn2'
        vn1_subnets = [get_random_cidr(af='v4')]
        vn2_subnets = ['20.1.1.0/24']
        number_of_policy = 150
        number_of_dummy_rules = 10
        number_of_valid_rules = 1
        number_of_default_rules = 2
        total_number_of_rules = (number_of_dummy_rules * number_of_policy) + number_of_valid_rules + number_of_default_rules
        no_of_rules_exp = total_number_of_rules
        valid_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]

        self.logger.info(
            'Creating %d policy and %d rules to test policy scalability' %
            (number_of_policy, number_of_dummy_rules + len(valid_rules)))
        policy_objs_list = policy_test_helper._create_n_policy_n_rules(
            self, number_of_policy, valid_rules, number_of_dummy_rules, verify=False)
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
            vm2_fixture.vm_ip, expectation=True,
            dst_vm_fixture=vm2_fixture)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend(
                ["ping failure with scaled policy and rules:", result_msg])
        assertEqual(result, True, msg)
        if self.inputs.get_af() == af_test:
            #In v6 test, new rule is added for proto 58 corresponding to v4 icmp rule,
            #so expected no. of rules should be increamented by 1
            no_of_rules_exp = total_number_of_rules + 1

        vn1_acl_count=len(self.agent_inspect[
            vm1_fixture._vm_node_ip].get_vna_acl_by_vn(vn1_fixture.vn_fq_name)['entries'])
        vn2_acl_count=len(self.agent_inspect[
            vm2_fixture._vm_node_ip].get_vna_acl_by_vn(vn2_fixture.vn_fq_name)['entries'])
        self.assertEqual(vn1_acl_count, no_of_rules_exp,
            "Mismatch in number of ace ID's and total number of rules in agent introspect \
                for vn %s" %vn1_fixture.vn_fq_name)
        self.assertEqual(vn2_acl_count, no_of_rules_exp,
            "Mismatch in number of ace ID's and total number of rules in agent introspect \
                for vn %s" %vn2_fixture.vn_fq_name)
        self.logger.info(
            'Verified ace Id\'s were created for %d rules, to test policy scalability' %
            no_of_rules_exp)
        return True
    # end test_policy_rules_scaling_with_ping

    @preposttest_wrapper
    def test_one_policy_rules_scaling_with_ping(self):
        ''' Test to validate scaling of policy and rules.
            Test to validate rules scaling on a single
            policy. The policy will be attached to two
            VN's and 2 VM's will be spawned in each of
            the VN's to verify exact number of acls are
            created in the agent introspect.
            Expected ace id's = 1 policy * 1498 distinct rules
            + 2 valid rule + 2 default rules = 1504 ace id's.
        '''
        result = True
        msg = []
        vn1_name = 'vn1'
        vn2_name = 'vn2'
        vn1_subnets = ['10.1.1.0/24']
        vn2_subnets = ['20.1.1.0/24']
        number_of_policy = 1
        number_of_dummy_rules = 1498
        number_of_valid_rules = 2
        number_of_default_rules = 2
        total_number_of_rules=number_of_dummy_rules + number_of_valid_rules + number_of_default_rules
        no_of_rules_exp = total_number_of_rules
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
            vm2_fixture.vm_ip, expectation=True,
            dst_vm_fixture=vm2_fixture)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend(
                ["ping failure with scaled policy and rules:", result_msg])
        assertEqual(result, True, msg)
        if self.inputs.get_af() == af_test:
            #In v6 test, new rule is added for proto 58 corresponding to v4 icmp rule,
            #so expected no. of rules should be increamented by 1
            no_of_rules_exp = total_number_of_rules + 1

        vn1_acl_count=len(self.agent_inspect[
            vm1_fixture._vm_node_ip].get_vna_acl_by_vn(vn1_fixture.vn_fq_name)['entries'])
        vn2_acl_count=len(self.agent_inspect[
            vm2_fixture._vm_node_ip].get_vna_acl_by_vn(vn2_fixture.vn_fq_name)['entries'])
        self.assertEqual(vn1_acl_count, no_of_rules_exp,
            "Mismatch in number of ace ID's and total number of rules in agent introspect \
                for vn %s" %vn1_fixture.vn_fq_name)
        self.assertEqual(vn2_acl_count, no_of_rules_exp,
            "Mismatch in number of ace ID's and total number of rules in agent introspect \
                for vn %s" %vn2_fixture.vn_fq_name)
        self.logger.info(
            'Verified ace Id\'s were created for %d rules, to test policy scalability' %
            no_of_rules_exp)
        return True
    # end test_one_policy_rules_scaling_with_ping

# end of class TestDetailedPolicy2


class TestDetailedPolicy3(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy3, cls).setUpClass()

    @preposttest_wrapper
    def test_scale_policy_with_ping(self):
        """ Test focus is on the scale of VM/VN created.have policy attached to all VN's and ping from one VM to all.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_10vn_10vm_config
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
                test_vm2_fixture.vm_ip, expectation=expectedResult,
                dst_vm_fixture=test_vm2_fixture)
            result_msg = "vm ping test result to vm %s is: %s" % (vmi, ret)
            self.logger.info(result_msg)
            if not ret:
                result = False
                msg.extend([result_msg, policy_info])
        self.assertEqual(result, True, msg)
        return result
    # end test_policy_with_ping

class TestDetailedPolicy0Ipv4v6(test_policy_basic.TestDetailedPolicy0):
    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy0Ipv4v6, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_repeated_policy_modify(self):
        super(TestDetailedPolicy0Ipv4v6, self).test_repeated_policy_modify()

class TestDetailedPolicy1Ipv4v6(TestDetailedPolicy1):
    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy1Ipv4v6, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class TestDetailedPolicy2Ipv4v6(TestDetailedPolicy2):
    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy2Ipv4v6, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class TestDetailedPolicy3Ipv4v6(TestDetailedPolicy3):
    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy3Ipv4v6, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

