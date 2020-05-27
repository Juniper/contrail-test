from __future__ import absolute_import
from builtins import str
from builtins import range
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
