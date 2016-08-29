from base import BasePolicyTest
from tcutils.wrappers import preposttest_wrapper
import test
from vn_test import VNFixture
from policy_test import PolicyFixture, copy
from common.policy import policy_test_utils
from vm_test import VMFixture, time
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from tcutils.util import get_random_name, get_random_cidr
from common.system.system_verification import system_vna_verify_policy
from tcutils.test_lib.test_utils import assertEqual
import sdn_basic_topology
import os
import sdn_single_vm_multiple_policy_topology
import sdn_single_vm_policy_topology

af_test = 'dual'

class TestBasicPolicy(BasePolicyTest):

    '''Policy config tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicy, cls).setUpClass()

    def runTest(self):
        pass

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

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'suite1', 'vcenter'])
    @preposttest_wrapper
    def test_policy(self):
        """ Configure policies based on topology and run policy related verifications.
        """
        result = True
        #
        # Get config for test from topology
        topology_class_name = sdn_basic_topology.sdn_basic_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.project_username,
                password=self.project.project_user_password)
        except NameError:
            topo = topology_class_name()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        #
        # Verify [and assert on fail] after setup
        # Calling system policy verification, pick any policy fixture to
        # access fixture verification
        policy_name = topo.policy_list[0]
        system_vna_verify_policy(
            self,
            config_topo['policy'][policy_name],
            topo,
            'setup')
        return True
    # end test_policy

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'vcenter', 'suite1'])
    @preposttest_wrapper
    def test_policy_to_deny(self):
        ''' Test to validate that with policy having rule to disable icmp within the VN, ping between VMs should fail
            1. Pick 2 VN from resource pool which have one VM in each
            2. Create policy with icmp deny rule
            3. Associate policy to both VN
            4. Ping from one VM to another. Ping should fail
        Pass criteria: Step 2,3 and 4 should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = ['192.168.10.0/24']
        policy_name = get_random_name('policy1')
        rules = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        assert vn1_fixture.verify_on_setup()

        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        if not vm1_fixture.ping_with_certainty(expectation=False,dst_vm_fixture=vm2_fixture):
            self.logger.error(
                'Ping from %s to %s passed,expected it to fail' %
                (vm1_fixture.vm_name, vm2_fixture.vm_name))
            self.logger.info('Doing verifications on the fixtures now..')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
        return True
    # end test_policy_to_deny

# end of class TestBasicPolicyConfig

class TestBasicPolicyNegative(BasePolicyTest):

    '''Negative tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyNegative, cls).setUpClass()

    def runTest(self):
        pass

    @test.attr(type=['sanity','ci_sanity', 'suite1', 'vcenter'])
    @preposttest_wrapper
    def test_remove_policy_with_ref(self):
        ''' This tests the following scenarios.
           1. Test to validate that policy removal will fail when it referenced with VN.
           2. validate vn_policy data in api-s against quantum-vn data, when created and unbind policy from VN thru quantum APIs.
           3. validate policy data in api-s against quantum-policy data, when created and deleted thru quantum APIs.
        '''
        vn1_name = get_random_name('vn4')
        vn1_subnets = ['10.1.1.0/24']
        policy_name = get_random_name('policy1')
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
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
                    policy_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        ret = policy_fixture.verify_on_setup()
        if ret['result'] == False:
            self.logger.error(
                "Policy %s verification failed after setup" % policy_name)
            assert ret['result'], ret['msg']

        self.logger.info(
            "Done with setup and verification, moving onto test ..")
        # try to remove policy which  was referenced with VN.
        policy_removal = True
        pol_id = None
        if self.quantum_h:
            policy_removal = self.quantum_h.delete_policy(policy_fixture.get_id())
        else:
            try:
                self.vnc_lib.network_policy_delete(id=policy_fixture.get_id())
            except Exception as e:
                policy_removal = False
        self.assertFalse(
            policy_removal,
            'Policy removal succeed as not expected since policy is referenced with VN')
        #assert vn1_fixture.verify_on_setup()
        # policy_fixture.verify_policy_in_api_server()
        return True
    # end test_remove_policy_with_ref

# end of class TestBasicPolicyNegative

class TestBasicPolicyModify(BasePolicyTest):

    '''Policy modification related tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyModify, cls).setUpClass()

    def runTest(self):
        pass

    @test.attr(type=['sanity', 'ci_sanity', 'suite1', 'vcenter'])
    @preposttest_wrapper
    def test_policy_modify_vn_policy(self):
        """ Configure policies based on topology;
        """
        ###
        # Get config for test from topology
        # very simple topo will do, one vn, one vm, one policy, 3 rules
        topology_class_name = sdn_single_vm_policy_topology.sdn_single_vm_policy_config

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
        # Test adding new policy to VN's exiting policy list
        state = "add policy: "
        test_vm = topo.vmc_list[0]
        test_vn = topo.vn_of_vm[test_vm]
        # Init test data, take backup of current topology
        initial_vn_policy_list = copy.copy(topo.vn_policy[test_vn])
        new_policy_to_add = policy_test_utils.get_policy_not_in_vn(
            initial_vn_policy_list,
            topo.policy_list)
        if not new_policy_to_add:
            result = 'False'
            msg = "test %s cannot be run as required config not available in topology; aborting test"
            self.logger.info(msg)
            assertEqual(result, True, msg)
        initial_policy_vn_list = copy.copy(topo.policy_vn[new_policy_to_add])
        new_vn_policy_list = copy.copy(initial_vn_policy_list)
        new_policy_vn_list = copy.copy(initial_policy_vn_list)
        new_vn_policy_list.append(new_policy_to_add)
        new_policy_vn_list.append(test_vn)
        test_vn_fix = config_topo['vn'][test_vn]
        test_vn_id = test_vn_fix.vn_id
        # configure new policy
        config_topo['policy'][new_policy_to_add] = self.useFixture(
            PolicyFixture(
                policy_name=new_policy_to_add,
                rules_list=topo.rules[new_policy_to_add],
                inputs=self.inputs,
                connections=self.connections))
        # get new policy_set to be pushed for the vn
        test_policy_fq_names = []
        for policy in new_vn_policy_list:
            name = config_topo['policy'][policy].policy_fq_name
            test_policy_fq_names.append(name)
        self.logger.info(
            "adding policy %s to vn %s" %
            (new_policy_to_add, test_vn))
        test_vn_fix.bind_policies(test_policy_fq_names, test_vn_id)
        # wait for tables update before checking after making changes to system
        time.sleep(5)
        self.logger.info(
            "New policy list of VN %s is %s" %
            (test_vn, new_vn_policy_list))
        # update expected topology with this new info for verification
        topo.vn_policy[test_vn] = new_vn_policy_list
        topo.policy_vn[new_policy_to_add] = new_policy_vn_list
        system_vna_verify_policy(
            self,
            config_topo['policy'][new_policy_to_add],
            topo,
            state)
        # Test unbinding all policies from VN
        state = "unbinding all policies"
        test_vn_fix.unbind_policies(test_vn_id)
        # wait for tables update before checking after making changes to system
        time.sleep(5)
        current_vn_policy_list = new_vn_policy_list
        new_vn_policy_list = []
        self.logger.info(
            "New policy list of VN %s is %s" %
            (test_vn, new_vn_policy_list))
        # update expected topology with this new info for verification
        topo.vn_policy[test_vn] = new_vn_policy_list
        for policy in current_vn_policy_list:
            topo.policy_vn[policy].remove(test_vn)
        system_vna_verify_policy(
            self,
            config_topo['policy'][new_policy_to_add],
            topo,
            state)
        return True
    # end test_policy_modify

# end of class TestBasicPolicyModify

class TestDetailedPolicy0(BasePolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDetailedPolicy0, cls).setUpClass()

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1'])
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
