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


class TestDetailedPolicyBasic0(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicyBasic0, cls).setUpClass()

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

