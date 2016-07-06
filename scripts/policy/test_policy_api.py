from base import BasePolicyTest

from vn_test import *
from vm_test import *
from policy_test import PolicyFixture
from common.policy import policy_test_utils
from common.policy import policy_test_helper
from tcutils.wrappers import preposttest_wrapper
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from tcutils.topo.sdn_topo_setup import *
from common import isolated_creds
import inspect


class TestApiPolicyFixture01(BasePolicyTest):

    @classmethod
    def setUpClass(cls):
        super(TestApiPolicyFixture01, cls).setUpClass()
    # end setUpClass

    def cleanUp(self):
        super(TestApiPolicyFixture01, self).cleanUp()
    # end cleanUp

    def get_current_policies_bound(self, vnc_lib_h, vn_id):
        api_vn_obj = vnc_lib_h.virtual_network_read(id=vn_id)
        api_policy_refs = api_vn_obj.get_network_policy_refs()
        api_policy_fq_names = [item['to'] for item in api_policy_refs]
        return api_policy_fq_names
    # end get_current_policies_bound

    @preposttest_wrapper
    def test_create_api_policy(self):
        '''
         Create/Delete/Modify policy using API server APIs
        '''
        vn1_name = 'vn4'
        vn1_subnets = ['10.1.1.0/24']
        policy_name = 'policy1'
        rules_list = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'src_ports': (80, 100),
                'source_network': vn1_name,
                'dest_network': vn1_name,
                'dst_ports': [100, 10],
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]

        rules_list1 = [
            {
                'direction': '>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'src_ports': (80, 120),
                'source_network': vn1_name,
                'dest_network': vn1_name,
                'dst_ports': [100, 10],
            }
        ]

        # get project obj
        proj = self.vnc_lib.project_read(self.project.project_fq_name)

        # creaete VN
        vn_blue_obj = VirtualNetwork(vn1_name, proj)
        vn_id = self.vnc_lib.virtual_network_create(vn_blue_obj)
        self.logger.info("VN %s is created using API Server" % vn1_name)

        vb = self.vnc_lib.virtual_network_read(id=str(vn_id))
        if not vb:
            self.logger.error("VN %s object is not present is API server" %
                              vn1_name)
            self.assertIsNotNone(vb, "VN is not present on API server")

        # create policy
        policy_fixt = self.useFixture(PolicyFixture(
            policy_name, rules_list, self.inputs, self.connections,
            api = 'api'))
        policy_rsp = policy_fixt.policy_obj.uuid
        self.logger.debug("Policy Creation Response " + str(policy_rsp))
        self.logger.info("policy %s is created with rules using API Server" %
                         policy_name)

        # modify the rule list in network policy
        rules_list.append(rules_list1[0])
        policy_fixt1 = self.useFixture(PolicyFixture(
            policy_name, rules_list, self.inputs, self.connections,
            api = 'api'))
        policy_fixt1.policy_obj.uuid = policy_rsp
        policy_rsp1 = self.vnc_lib.network_policy_update(policy_fixt1.policy_obj)

        pol = self.vnc_lib.network_policy_read(id=str(policy_rsp))
        if not pol:
            self.logger.error("policy %s object is not present in API server" %
                              policy_name)
            self.assertIsNotNone(pol, "policy is not present on API server")
        vn_blue_obj.add_network_policy(
            policy_fixt1.policy_obj,
            VirtualNetworkPolicyType(
                sequence=SequenceType(
                    major=0,
                    minor=0)))
        self.vnc_lib.virtual_network_update(vn_blue_obj)

        vn_in_quantum = self.quantum_h.get_vn_obj_if_present(vb.name)
        if not vn_in_quantum:
            self.logger.info("VN %s is not present in the quantum server" %
                             vn1_name)
            self.assertIsNotNone(
                vn_in_quantum, "VN is not present on quantum server")

        # verify vn_policy data on quantum after association
        #vn_assoc_policy_quantum = vn_in_quantum['network']['contrail:policys'][0][2]
        vn_assoc_policy_quantum = self.get_current_policies_bound(
            self.vnc_lib, vn_id)
        vn_assoc_policy_quantum = str(vn_assoc_policy_quantum[0][2])
        self.logger.info(
            "verifying vn_policy data on the quantum server for policy %s and vn %s" %
            (policy_name, vn1_name))
        self.assertEqual(
            vn_assoc_policy_quantum,
            policy_fixt1.policy_obj.name,
            'associaton policy data on vn is missing from quantum')

        policy_in_quantum = self.quantum_h.get_policy_if_present(
            policy_name=pol.name, project_name=self.inputs.project_name)
        if not policy_in_quantum:
            self.logger.info("policy %s is not present in the quantum server" %
                             pol.name)
            self.assertIsNotNone(policy_in_quantum,
                                 "policy is not present on quantum server")
        assert self.verify_policy_in_api_quantum_server(pol, policy_in_quantum)
        self.logger.info("policy %s is verified on API Server" % policy_name)

        # delete vn
        vn_delete = self.vnc_lib.virtual_network_delete(id=str(vn_id))
        if vn_delete:
            self.logger.info("VN %s is still present on the API server" %
                             vn1_name)
            self.assertIsNone(vn_delete, "VN delete failed")
        self.logger.info("VN %s is successfully deleted using API server" %
                         vn1_name)

        return True
    # end create_api_policy_test

    @preposttest_wrapper
    def test_associate_disassociate_api_policy(self):
        '''
         Associate/Disassociate/Delete with reference policy using API server APIs
        '''
        vn1_name = 'vn44'
        vn1_subnets = ['10.1.1.0/24']
        policy_name = 'policy11'
        rules_list = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'src_ports': (80, 100),
                'source_network': vn1_name,
                'dest_network': vn1_name,
                'dst_ports': [100, 10],
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]

        # get project obj
        proj = self.vnc_lib.project_read(self.project.project_fq_name)

        # creaete VN
        vn_obj = VirtualNetwork(vn1_name, proj)
        vn_id = self.vnc_lib.virtual_network_create(vn_obj)
        self.logger.info("VN %s is created using API Server" % vn1_name)

        vb = self.vnc_lib.virtual_network_read(id=str(vn_id))
        if not vb:
            self.logger.error("VN %s object is not present is API server" %
                              vn1_name)
            self.assertIsNotNone(vb, "VN is not present on API server")

        # create policy
        policy_fixt = self.useFixture(PolicyFixture(
            policy_name, rules_list, self.inputs, self.connections,
            api = 'api'))
        policy_rsp = policy_fixt.policy_obj.uuid
        self.logger.debug("Policy Creation Response " + str(policy_rsp))
        self.logger.info("policy %s is created with rules using API Server" %
                         policy_name)

        pol = self.vnc_lib.network_policy_read(id=str(policy_rsp))
        if not pol:
            self.logger.error("policy %s object is not present in API server" %
                              policy_name)
            self.assertIsNotNone(pol, "policy is not present on API server")

        # associate a policy to VN
        vn_update_rsp = None
        vn_obj.add_network_policy(
            policy_fixt.policy_obj,
            VirtualNetworkPolicyType(
                sequence=SequenceType(
                    major=0,
                    minor=0)))
        self.logger.info("trying to associate policy %s to vn %s" %
                         (policy_name, vn1_name))
        vn_update_rsp = self.vnc_lib.virtual_network_update(vn_obj)

        if vn_update_rsp is None:
            self.logger.error("policy %s assocation with vn %s failed" %
                              (policy_name, vn1_name))
            self.assertIsNone(vn_update_rsp, "policy association failed")
        self.logger.info("policy %s assocation with vn %s is successful" %
                         (policy_name, vn1_name))

        # delete policy with reference
        try:
            self.vnc_lib.network_policy_delete(id=str(policy_rsp))
            deleted_policy = []
            self.logger.error(
                "policy %s got deleted even though we had association with VN %s" %
                (policy_name, vn1_name))
            self.assertIsNotNone(
                delete_policy, "delete policy with reference test failed")
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the policy cannot be deleted when the VN is associated to it.')

        # dis-associate a policy from vn
        vn_update_rsp = None
        vn_obj.del_network_policy(policy_fixt.policy_obj)
        self.logger.info("trying to dis-associate policy %s from vn %s" %
                         (policy_name, vn1_name))
        vn_update_rsp = self.vnc_lib.virtual_network_update(vn_obj)

        if vn_update_rsp is None:
            self.logger.error("policy %s dis-assocation with vn %s failed" %
                              (policy_name, vn1_name))
            self.assertIsNone(vn_update_rsp, "policy dis-association failed")
        self.logger.info("policy %s dis-assocation with vn %s is successful" %
                         (policy_name, vn1_name))

        # delete vn
        vn_delete = self.vnc_lib.virtual_network_delete(id=str(vn_id))
        if vn_delete:
            self.logger.info("VN %s is still present on the API server" %
                             vn1_name)
            self.assertIsNone(vn_delete, "VN delete failed")
        self.logger.info("VN %s is successfully deleted using API server" %
                         vn1_name)
        return True
    # end test_associate_disassociate_api_policy

    @preposttest_wrapper
    def test_policy_with_local_keyword_across_multiple_vn(self):
        '''
         Ping test single policy with local as source port and attached to multiple VN using API fixtures
        '''
        result = True
        topology_class_name = None
        #
        # Get config for test from topology
        import sdn_basic_topology_api
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_basic_topology_api.sdn_multiple_vn_single_policy_config_api

        self.logger.info("Scenario for the test used is: %s" %
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
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option='contrail')
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        dst_vm = topo.vmc_list[0]  # 'vmc4'
        dst_vm_fixture = config_topo['vm'][dst_vm]
        dst_vm_ip = dst_vm_fixture.vm_ip
        test_vn = topo.vn_of_vm[dst_vm]  # vnet4
        policy = topo.vn_policy[test_vn][0]  # policy0
        num_rules = len(topo.rules[policy])
        matching_rule_action = {}
        test_proto = 'icmp'
        for i in range(num_rules):
            proto = topo.rules[policy][i].__dict__['protocol']
            matching_rule_action[proto] = topo.rules[
                policy][i].action_list.simple_action
        expectedResult = True if matching_rule_action[
            test_proto] == 'pass' else False
        # test ping from all VM's to testVM
        for vm in topo.vmc_list:
            if vm != dst_vm:
                src_vm_fixture = config_topo['vm'][vm]
                self.logger.info("Verify ping to vm %s from vm %s" %
                                 (dst_vm, vm))
                ret = src_vm_fixture.ping_with_certainty(
                    dst_vm_ip, expectation=expectedResult)
                result_msg = "vm ping test result to vm %s is: %s" % (vm, ret)
                self.logger.info(result_msg)
                if not ret:
                    result = False
                    msg.extend([result_msg, policy])
                self.assertEqual(result, True, msg)
        return True
    # end test_policy_with_local_keyword_across_multiple_vn

    def verify_policy_in_api_quantum_server(
            self,
            api_policy_obj,
            quantum_policy_obj):
        '''Validate policy information in API-Server. Compare data with quantum based policy fixture data.
        Check specifically for following:
        api_server_keys: 1> fq_name, 2> uuid, 3> rules
        quantum_h_keys: 1> policy_fq_name, 2> id in policy_obj, 3> policy_obj [for rules]
        '''
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.info("====Verifying data for %s in API_Server ======" %
                         (api_policy_obj.fq_name[2]))
        self.api_s_policy_obj = self.api_s_inspect.get_cs_policy(
            domain=api_policy_obj.fq_name[0],
            project=api_policy_obj.fq_name[1],
            policy=api_policy_obj.fq_name[2],
            refresh=True)
        self.api_s_policy_obj_x = self.api_s_policy_obj['network-policy']

        # compare policy_fq_name
        out = policy_test_utils.compare_args(
            'policy_fq_name',
            api_policy_obj.fq_name,
            quantum_policy_obj['policy']['fq_name'])
        if out:
            err_msg.append(out)
        # compare policy_uuid
        out = policy_test_utils.compare_args(
            'policy_uuid',
            api_policy_obj.uuid,
            quantum_policy_obj['policy']['id'])
        if out:
            err_msg.append(out)
        # compare policy_rules
        out = policy_test_utils.compare_args(
            'policy_rules', self.api_s_policy_obj_x[
                'network_policy_entries']['policy_rule'],
            quantum_policy_obj['policy']['entries']['policy_rule'])
        if out:
            err_msg.append(out)

        if err_msg != []:
            result = False
            err_msg.insert(
                0, me + ":" + api_policy_obj.fq_name[2])
        self.logger.info("verification: %s, status: %s message: %s" %
                         (me, result, err_msg))
        return {'result': result, 'msg': err_msg}
    # end verify_policy_in_api_quantum_server

# end TestApiPolicyFixture01


class TestApiPolicyFixture02(BasePolicyTest):

    @classmethod
    def setUpClass(cls):
        super(TestApiPolicyFixture02, cls).setUpClass()
    # end setUpClass

    def cleanUp(self):
        super(TestApiPolicyFixture02, self).cleanUp()
    # end cleanUp

    def get_current_policies_bound(self, vnc_lib_h, vn_id):
        api_vn_obj = vnc_lib_h.virtual_network_read(id=vn_id)
        api_policy_refs = api_vn_obj.get_network_policy_refs()
        api_policy_fq_names = [item['to'] for item in api_policy_refs]
        return api_policy_fq_names
    # end get_current_policies_bound

    @preposttest_wrapper
    def test_policy_rules_scaling_with_ping_api(self):
        ''' Test to validate scaling of policy and rules
        '''
        result = True
        msg = []
        err_msg = []
        vn_names = ['vn1', 'vn2']
        vm_names = ['vm1', 'vm2']
        vn_of_vm = {'vm1': 'vn1', 'vm2': 'vn2'}
        vn_nets = {
            'vn1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('10.1.1.0', 24))]))],
            'vn2': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('20.1.1.0', 24))]))]
        }
        number_of_policy = 1
        # adding workaround to pass the test with less number of rules till
        # 1006, 1184 fixed
        number_of_dummy_rules = 149
        valid_rules = [
            PolicyRuleType(
                direction='<>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')],
                src_addresses=[AddressType(virtual_network='any')], dst_ports=[PortType(-1, -1)],
                action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
        ]
        self.logger.info(
            'Creating %d policy and %d rules to test policy scalability' %
            (number_of_policy, number_of_dummy_rules + len(valid_rules)))
        # for now we are creating limited number of policy and rules
        policy_objs_list = policy_test_helper._create_n_policy_n_rules(
            self,
            number_of_policy,
            valid_rules,
            number_of_dummy_rules,
            option='api')
        self.logger.info('Create VN and associate %d policy' %
                         (number_of_policy))

        vn_fixture = {}
        vm_fixture = {}
        ref_tuple = []
        for conf_policy in policy_objs_list:
            ref_tuple.append(
                (conf_policy,
                 VirtualNetworkPolicyType(
                     sequence=SequenceType(
                         major=0,
                         minor=0))))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(
                self.vnc_lib,
                project_name=self.project.project_name))
        for vn_name in vn_names:
            vn_fixture[vn_name] = self.useFixture(
                VirtualNetworkTestFixtureGen(
                    self.vnc_lib,
                    virtual_network_name=vn_name,
                    parent_fixt=proj_fixt,
                    id_perms=IdPermsType(
                        enable=True),
                    network_policy_ref_infos=ref_tuple,
                    network_ipam_ref_infos=vn_nets[vn_name]))
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(vn_fixture[vn_name]._obj.uuid))
            if not vn_read:
                self.logger.error("VN %s read on API server failed" % vn_name)
                return {
                    'result': False,
                    'msg': "VN:%s read failed on API server" %
                    vn_name}
        for vm_name in vm_names:
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(vn_fixture[vn_of_vm[vm_name]]._obj.uuid))
            vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(
                vn_read.name)
            # Launch VM with 'ubuntu-traffic' image which has scapy pkg
            # remember to call install_pkg after VM bringup
            # Bring up with 2G RAM to support multiple traffic streams..
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_quantum_obj,
                    flavor='contrail_flavor_small',
                    image_name='ubuntu-traffic',
                    vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_node_ip = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(
                    vm_fixture[vm_name].vm_obj)]['host_ip']
            self.logger.info("Calling VM verifications... ")
            time.sleep(5)     # wait for 5secs after launching VM's
            vm_verify_out = None
            vm_verify_out = vm_fixture[vm_name].verify_on_setup()
            if not vm_verify_out:
                m = "%s - vm verify in agent after launch failed" % vm_node_ip
                self.logger.error(m) 
                return vm_verify_out
        for vm_name in vm_names:
            out = self.nova_h.wait_till_vm_is_up(
                vm_fixture[vm_name].vm_obj)
            if not out:
                self.logger.error("VM failed to come up")
                return out
            else:
                vm_fixture[vm_name].install_pkg("Traffic")
        # Test ping with scaled policy and rules
        dst_vm = vm_names[len(vm_names) - 1]  # 'vm2'
        dst_vm_fixture = vm_fixture[dst_vm]
        dst_vm_ip = dst_vm_fixture.vm_ip
        self.logger.info("Verify ping to vm %s" % (dst_vm))
        ret = vm_fixture[vm_names[0]].ping_with_certainty(
            dst_vm_ip, expectation=True)
        result_msg = "vm ping test result to vm %s is: %s" % (dst_vm, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend(
                ["ping test failure with scaled policy and rules:", result_msg])
        self.assertEqual(result, True, msg)
        return True
    # end test_policy_rules_scaling_with_ping_api

    @preposttest_wrapper
    def test_policy_api_fixtures(self):
        '''
         Policy related tests using auto generated API fixtures
        '''
        #
        # Get config for test from topology
        result = True
        topology_class_name = None
        #
        # Get config for test from topology
        import sdn_basic_topology_api
        result = True
        msg = []
        #topology_class_name= eval("self.topology")
        if not topology_class_name:
            topology_class_name = sdn_basic_topology_api.sdn_basic_config_api

        self.logger.info("Scenario for the test used is: %s" %
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
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option='contrail')
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo, config_topo = out['data']
        return True
    # end test_policy_api_fixtures

    def verify_policy_in_api_quantum_server(
            self,
            api_policy_obj,
            quantum_policy_obj):
        '''Validate policy information in API-Server. Compare data with quantum based policy fixture data.
        Check specifically for following:
        api_server_keys: 1> fq_name, 2> uuid, 3> rules
        quantum_h_keys: 1> policy_fq_name, 2> id in policy_obj, 3> policy_obj [for rules]
        '''
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.info("====Verifying data for %s in API_Server ======" %
                         (api_policy_obj.fq_name[2]))
        self.api_s_policy_obj = self.api_s_inspect.get_cs_policy(
            domain=api_policy_obj.fq_name[0],
            project=api_policy_obj.fq_name[1],
            policy=api_policy_obj.fq_name[2],
            refresh=True)
        self.api_s_policy_obj_x = self.api_s_policy_obj['network-policy']

        # compare policy_fq_name
        out = policy_test_utils.compare_args(
            'policy_fq_name',
            api_policy_obj.fq_name,
            quantum_policy_obj['policy']['fq_name'])
        if out:
            err_msg.append(out)
        # compare policy_uuid
        out = policy_test_utils.compare_args(
            'policy_uuid',
            api_policy_obj.uuid,
            quantum_policy_obj['policy']['id'])
        if out:
            err_msg.append(out)
        # compare policy_rules
        out = policy_test_utils.compare_args(
            'policy_rules', self.api_s_policy_obj_x[
                'network_policy_entries']['policy_rule'],
            quantum_policy_obj['policy']['entries']['policy_rule'])
        if out:
            err_msg.append(out)

        if err_msg != []:
            result = False
            err_msg.insert(
                0, me + ":" + api_policy_obj.fq_name[2])
        self.logger.info("verification: %s, status: %s message: %s" %
                         (me, result, err_msg))
        return {'result': result, 'msg': err_msg}
    # end verify_policy_in_api_quantum_server

# end TestApiPolicyFixture02
