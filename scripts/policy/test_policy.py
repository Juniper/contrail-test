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

class TestBasicPolicyConfig(BasePolicyTest):

    '''Policy config tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyConfig, cls).setUpClass()

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

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'vcenter'])
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
                username=self.project.username,
                password=self.project.password)
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

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'vcenter'])
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
        if vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            self.logger.error(
                'Ping from %s to %s passed,expected it to fail' %
                (vm1_fixture.vm_name, vm2_fixture.vm_name))
            self.logger.info('Doing verifications on the fixtures now..')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
        return True
    # end test_policy_to_deny

    @preposttest_wrapper
    def test_policy_with_multi_vn_in_vm(self):
        ''' Test to validate policy action in VM with vnic's in  multiple VN's with different policies.
        Test flow: vm1 in vn1 and vn2; vm3 in vn3. policy to allow traffic from vn2 to vn3 and deny from vn1 to vn3.
        Default route for vm1 in vn1, which has no reachability to vn3 - verify traffic - should fail.
        Add specific route to direct vn3 traffic through vn2 - verify traffic - should pass.
        '''
        vm1_name = 'vm_mine1'
        vm2_name = 'vm_mine2'
        vn1_name = 'vn221'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn222'
        vn2_subnets = ['22.1.1.0/24']
        vn3_gateway = '22.1.1.254'
        vn3_name = 'vn223'
        vn3_subnets = ['33.1.1.0/24']
        rules1 = [
            {
                'direction': '>', 'simple_action': 'deny',
                'protocol': 'icmp', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        rules2 = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        policy1_name = 'p1'
        policy2_name = 'p2'
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules1,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rules2,
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
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets,
                disable_gateway=True,
                policy_objs=[
                    policy2_fixture.policy_obj]))
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn3_name,
                inputs=self.inputs,
                subnets=vn3_subnets,
                policy_objs=[
                    policy2_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn3_fixture.verify_on_setup()
        assert vn1_fixture.verify_vn_policy_in_api_server()
        assert vn2_fixture.verify_vn_policy_in_api_server()
        assert vn3_fixture.verify_vn_policy_in_api_server()
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_objs=[
                    vn1_fixture.obj,
                    vn2_fixture.obj],
                vm_name=vm1_name,
                project_name=self.inputs.project_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj],
                vm_name=vm2_name,
                project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_h.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_h.wait_till_vm_is_up(vm2_fixture.vm_obj)
        # For multi-vn vm, configure ip address for 2nd interface
        multivn_vm_ip_list = vm1_fixture.vm_ips
        intf_conf_cmd = "ifconfig eth1 %s netmask 255.255.255.0" % multivn_vm_ip_list[
            1]
        vm_cmds = (intf_conf_cmd, 'ifconfig -a')
        for cmd in vm_cmds:
            cmd_to_output = [cmd]
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
            output = vm1_fixture.return_output_cmd_dict[cmd]
        for ip in multivn_vm_ip_list:
            if ip not in output:
                self.logger.error(
                    "IP %s not assigned to any eth intf of %s" %
                    (ip, vm1_fixture.vm_name))
                assert False
        # Ping test from multi-vn vm to peer vn, result will be based on action
        # defined in policy attached to VN which has the default gw of VM
        self.logger.info(
            "Ping from multi-vn vm to vm2, with no allow rule in the VN where default gw is part of, traffic should fail")
        result = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip,
            expectation=False)
        assertEqual(result, True, "ping passed which is not expected")
        # Configure VM to reroute traffic to interface belonging to different
        # VN
        self.logger.info(
            "Direct traffic to gw which is part of VN with allow policy to destination VN, traffic should pass now")
        i = ' route add -net %s netmask 255.255.255.0 gw %s dev eth1' % (
            vn3_subnets[0].split('/')[0], multivn_vm_ip_list[1])
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        # Ping test from multi-vn vm to peer vn, result will be based on action
        # defined in policy attached to VN which has the default gw for VM
        self.logger.info(
            "Ping from multi-vn vm to vm2, with allow rule in the VN where network gw is part of, traffic should pass")
        result = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip,
            expectation=True)
        assertEqual(result, True, "ping failed which is not expected")
        return True
    # end test_policy_with_multi_vn_in_vm

    @preposttest_wrapper
    def test_policy_protocol_summary(self):
        ''' Test to validate that when policy is created with multiple rules that can be summarized by protocol

        '''
        proj_name = self.inputs.project_name
        vn1_name = 'vn40'
        vn1_subnets = ['10.1.1.0/24']
        policy1_name = 'policy1'
        policy2_name = 'policy2'

        rules2 = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        rules1 = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules1,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rules2,
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

        vn1_vm1_name = 'vm1'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name))
        assert vm1_fixture.verify_on_setup()

        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        vn_fq_name = inspect_h.get_vna_vn(
            domain='default-domain',
            project=proj_name,
            vn_name=vn1_name)['name']

        vna_acl1 = inspect_h.get_vna_acl_by_vn(vn_fq_name)

        policy1_fixture.verify_policy_in_api_server()

        if vn1_fixture.policy_objs:
            policy_fq_names = [
                self.quantum_h.get_policy_fq_name(x) for x in vn1_fixture.policy_objs]

        policy_fq_name2 = self.quantum_h.get_policy_fq_name(
            policy2_fixture.policy_obj)
        policy_fq_names.append(policy_fq_name2)
        vn1_fixture.bind_policies(policy_fq_names, vn1_fixture.vn_id)

        vna_acl2 = inspect_h.get_vna_acl_by_vn(vn_fq_name)
        out = policy_test_utils.compare_args(
            'policy_rules',
            vna_acl1['entries'],
            vna_acl2['entries'])

        if out:
            self.logger.info(
                "policy rules are not matching with expected %s  and actual %s" %
                (vna_acl1['entries'], vna_acl2['entries']))
            self.assertIsNone(out, "policy compare failed")

        return True

    # end test_policy_protocol_summary

# end of class TestBasicPolicyConfig


class TestBasicPolicyNegative(BasePolicyTest):

    '''Negative tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyNegative, cls).setUpClass()

    def runTest(self):
        pass

    @test.attr(type=['sanity','ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_remove_policy_with_ref(self):
        ''' This tests the following scenarios.
           1. Test to validate that policy removal will fail when it referenced with VN.
           2. validate vn_policy data in api-s against quantum-vn data, when created and unbind policy from VN thru quantum APIs.
           3. validate policy data in api-s against quantum-policy data, when created and deleted thru quantum APIs.
        '''
        vn1_name = 'vn4'
        vn1_subnets = ['10.1.1.0/24']
        policy_name = 'policy1'
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


class TestBasicPolicyRouting(BasePolicyTest):

    ''' Check route import/exports based on policy config'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyRouting, cls).setUpClass()

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_policy_RT_import_export(self):
        ''' Test to validate RT imported/exported in control node.
        Verification is implemented in vn_fixture to compare fixture route data with the data in control node..
        Verification expects test code to compile policy allowed VN info, which is used to validate data in CN.
        Test calls get_policy_peer_vns [internally call get_allowed_peer_vns_by_policy for each VN]. This data is
        fed to verify_vn_route_target, which internally calls get_rt_info to build expected list. This is compared
        against actual by calling cn_ref.get_cn_routing_instance and getting rt info.  '''

        vn1_name = 'vn40'
        vn1_subnets = ['40.1.1.0/24']
        vn2_name = 'vn41'
        vn2_subnets = ['41.1.1.0/24']
        vn3_name = 'vn42'
        vn3_subnets = ['42.1.1.0/24']
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        policy3_name = 'policy3'
        policy4_name = 'policy4'
        # cover all combinations of rules for this test
        # 1. both vn's allow each other 2. one vn allows peer, while other denies 3. policy rule doesnt list local vn
        # 4. allow or deny any vn is not handled now..
        rules = [{'direction': '<>',
                  'simple_action': 'pass',
                  'protocol': 'icmp',
                  'source_network': vn1_name,
                  'dest_network': vn2_name},
                 {'direction': '<>',
                  'simple_action': 'deny',
                  'protocol': 'icmp',
                  'source_network': vn1_name,
                  'dest_network': vn3_name},
                 {'direction': '<>',
                  'simple_action': 'pass',
                  'protocol': 'icmp',
                  'source_network': vn2_name,
                  'dest_network': vn3_name},
                 {'direction': '<>',
                  'simple_action': 'pass',
                  'protocol': 'icmp',
                  'source_network': 'any',
                  'dest_network': vn3_name},
                 ]
        rev_rules2 = [{'direction': '<>',
                       'simple_action': 'pass',
                       'protocol': 'icmp',
                       'source_network': vn1_name,
                       'dest_network': vn3_name,
                       },
                      ]

        rev_rules1 = [{'direction': '<>',
                       'simple_action': 'pass',
                       'protocol': 'icmp',
                       'source_network': vn2_name,
                       'dest_network': vn1_name,
                       },
                      ]
        rules2 = [{'direction': '<>',
                   'simple_action': 'pass',
                   'protocol': 'icmp',
                   'source_network': vn3_name,
                   'dest_network': vn1_name,
                   },
                  ]

        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules1,
                inputs=self.inputs,
                connections=self.connections))
        policy3_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy3_name,
                rules_list=rules2,
                inputs=self.inputs,
                connections=self.connections))
        policy4_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy4_name,
                rules_list=rev_rules2,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn3_name,
                inputs=self.inputs,
                subnets=vn3_subnets))
        assert vn3_fixture.verify_on_setup()

        self.logger.info("TEST STEP: End of setup")
        vn_fixture = {
            vn1_name: vn1_fixture,
            vn2_name: vn2_fixture,
            vn3_name: vn3_fixture}
        vnet_list = [vn1_name, vn2_name, vn3_name]

        self.logger.info("TEST STEP: Route verification for VN after setup")
        actual_peer_vns_by_policy = policy_test_utils.get_policy_peer_vns(
            self,
            vnet_list,
            vn_fixture)
        for vn in vnet_list:
            err_msg_on_fail = "route verification failed for vn %s" % (vn)
            assert (
                vn_fixture[vn].verify_vn_route_target(
                    policy_peer_vns=actual_peer_vns_by_policy[vn])), err_msg_on_fail

        self.logger.info(
            "TEST STEP: Bind policys to VN and verify import and export RT values")
        policy_fq_name1 = [policy1_fixture.policy_fq_name]
        policy_fq_name2 = [policy2_fixture.policy_fq_name]
        vn1_fixture.bind_policies(policy_fq_name1, vn1_fixture.vn_id)
        vn1_pol = vn1_fixture.get_policy_attached_to_vn()
        vn2_fixture.bind_policies(policy_fq_name2, vn2_fixture.vn_id)
        vn2_pol = vn2_fixture.get_policy_attached_to_vn()
        vn3_fixture.bind_policies(
            [policy3_fixture.policy_fq_name], vn3_fixture.vn_id)
        vn3_pol = vn3_fixture.get_policy_attached_to_vn()
        self.logger.info("vn: %s policys: %s" % (vn1_name, vn1_pol))
        self.logger.info("vn: %s policys: %s" % (vn2_name, vn2_pol))
        self.logger.info("vn: %s policys: %s" % (vn3_name, vn3_pol))

        actual_peer_vns_by_policy = policy_test_utils.get_policy_peer_vns(
            self,
            vnet_list,
            vn_fixture)
        for vn in vnet_list:
            err_msg_on_fail = "route verification failed for vn %s" % (vn)
            out = vn_fixture[vn].verify_vn_route_target(
                policy_peer_vns=actual_peer_vns_by_policy[vn])
            # control node may not be updated of the config changes right away, as it depends on system load ..
            # one scenario being when multiple tests are run in parallel..
            # wait & retry one more time if result is not as expected..
            if not out:
                self.logger.info("wait and verify VN RT again...")
                time.sleep(5)
                out = vn_fixture[vn].verify_vn_route_target(
                    policy_peer_vns=actual_peer_vns_by_policy[vn])
            assert (out), err_msg_on_fail

        self.logger.info(
            "TEST STEP: Bind one more policy to VN and verify RT import values updated")
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name, policy4_fixture.policy_fq_name], vn1_fixture.vn_id)

        actual_peer_vns_by_policy = policy_test_utils.get_policy_peer_vns(
            self,
            vnet_list,
            vn_fixture)
        for vn in vnet_list:
            err_msg_on_fail = "route verification failed for vn %s" % (vn)
            assert (
                vn_fixture[vn].verify_vn_route_target(
                    policy_peer_vns=actual_peer_vns_by_policy[vn])), err_msg_on_fail

        self.logger.info(
            "TEST STEP: Unbind policy which was added earlier and verify RT import/export values are updated accordingly")
        vn1_fixture.unbind_policies(
            vn1_fixture.vn_id, [
                policy4_fixture.policy_fq_name])
        vn3_fixture.unbind_policies(
            vn3_fixture.vn_id, [
                policy3_fixture.policy_fq_name])

        actual_peer_vns_by_policy = policy_test_utils.get_policy_peer_vns(
            self,
            vnet_list,
            vn_fixture)
        for vn in vnet_list:
            err_msg_on_fail = "route verification failed for vn %s" % (vn)
            assert (
                vn_fixture[vn].verify_vn_route_target(
                    policy_peer_vns=actual_peer_vns_by_policy[vn])), err_msg_on_fail
        return True

    # end of test_policy_RT_import_export

# end of class TestBasicPolicyRouting


class TestBasicPolicyModify(BasePolicyTest):

    '''Policy modification related tests'''

    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicPolicyModify, cls).setUpClass()

    def runTest(self):
        pass

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_policy_modify_vn_policy(self):
        """ Configure policies based on topology;
        """
        ###
        # Get config for test from topology
        # very simple topo will do, one vn, one vm, one policy, 3 rules
        from . import sdn_single_vm_policy_topology
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
            "new policy list of vn %s is %s" %
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
            "new policy list of vn %s is %s" %
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
