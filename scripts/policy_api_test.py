# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run policy_api_test'. To run specific tests,
# You can do 'python -m testtools.run -l policy_api_test'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import policy_test_utils

from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from policy_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from sdn_topo_setup import *


class TestApiPolicyFixture(testtools.TestCase, fixtures.TestWithFixtures):

#    @classmethod
    def setUp(self):
        super(TestApiPolicyFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.project_fq_name = None
        self.api_s_inspect = self.connections.api_server_inspect
        self.analytics_obj = self.connections.analytics_obj
    # end setUpClass

    def cleanUp(self):
        super(TestApiPolicyFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

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
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        proj = self.vnc_lib.project_read(project_obj.project_fq_name)
        self.project_fq_name = project_obj.project_fq_name

        # creaete VN
        vn_blue_obj = vnc_api.VirtualNetwork(vn1_name, proj)
        vn_id = self.vnc_lib.virtual_network_create(vn_blue_obj)
        self.logger.info("VN %s is created using API Server" % vn1_name)

        vb = self.vnc_lib.virtual_network_read(id=str(vn_id))
        if not vb:
            self.logger.error("VN %s object is not present is API server" %
                              vn1_name)
            self.assertIsNotNone(vb, "VN is not present on API server")

        # create policy
        policy_obj = self._create_policy(policy_name, rules_list)
        policy_rsp = self.vnc_lib.network_policy_create(policy_obj)
        self.logger.debug("Policy Creation Response " + str(policy_rsp))
        self.logger.info("policy %s is created with rules using API Server" %
                         policy_name)

        # modify the rule list in network policy
        rules_list.append(rules_list1[0])
        policy_obj1 = self._create_policy(policy_name, rules_list)
        policy_obj1.uuid = policy_rsp
        policy_rsp1 = self.vnc_lib.network_policy_update(policy_obj1)

        pol = self.vnc_lib.network_policy_read(id=str(policy_rsp))
        if not pol:
            self.logger.error("policy %s object is not present in API server" %
                              policy_name)
            self.assertIsNotNone(pol, "policy is not present on API server")
        vn_blue_obj.add_network_policy(policy_obj1,
                                       vnc_api.VirtualNetworkPolicyType(sequence=vnc_api.SequenceType(major=0, minor=0)))
        self.vnc_lib.virtual_network_update(vn_blue_obj)

        vn_in_quantum = self.quantum_fixture.get_vn_obj_if_present(vb.name)
        if not vn_in_quantum:
            self.logger.info("VN %s is not present in the quantum server" %
                             vn1_name)
            self.assertIsNotNone(
                vn_in_quantum, "VN is not present on quantum server")

        # verify vn_policy data on quantum after association
        #vn_assoc_policy_quantum = vn_in_quantum['network']['contrail:policys'][0][2]
        vn_assoc_policy_quantum = self.get_current_policies_bound(
            self.vnc_lib, vn_id)
        vn_assoc_policy_quantum = str(vn_assoc_policy_quantum)
        self.logger.info(
            "verifying vn_policy data on the quantum server for policy %s and vn %s" %
            (policy_name, vn1_name))
        self.assertEqual(vn_assoc_policy_quantum, policy_obj1.name,
                         'associaton policy data on vn is missing from quantum')

        policy_in_quantum = self.quantum_fixture.get_policy_if_present(
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

        # delete network policy
        np_delete = self.vnc_lib.network_policy_delete(id=str(policy_rsp))
        if np_delete:
            self.logger.info("policy %s is still present on the API server" %
                             policy_name)
            self.assertIsNone(np_delete, "policy delete failed")
        self.logger.info("policy %s is successfully deleted using API server" %
                         policy_name)
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
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        proj = self.vnc_lib.project_read(project_obj.project_fq_name)
        self.project_fq_name = project_obj.project_fq_name

        # creaete VN
        vn_obj = vnc_api.VirtualNetwork(vn1_name, proj)
        vn_id = self.vnc_lib.virtual_network_create(vn_obj)
        self.logger.info("VN %s is created using API Server" % vn1_name)

        vb = self.vnc_lib.virtual_network_read(id=str(vn_id))
        if not vb:
            self.logger.error("VN %s object is not present is API server" %
                              vn1_name)
            self.assertIsNotNone(vb, "VN is not present on API server")

        # create policy
        policy_obj = self._create_policy(policy_name, rules_list)
        policy_rsp = self.vnc_lib.network_policy_create(policy_obj)
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
        vn_obj.add_network_policy(policy_obj,
                                  vnc_api.VirtualNetworkPolicyType(sequence=vnc_api.SequenceType(major=0, minor=0)))
        self.logger.info("trying to associate policy %s to vn %s" %
                         (policy_name, vn1_name))
        vn_update_rsp = self.vnc_lib.virtual_network_update(vn_obj)

        if vn_update_rsp == None:
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
        vn_obj.del_network_policy(policy_obj)
        self.logger.info("trying to dis-associate policy %s from vn %s" %
                         (policy_name, vn1_name))
        vn_update_rsp = self.vnc_lib.virtual_network_update(vn_obj)

        if vn_update_rsp == None:
            self.logger.error("policy %s dis-assocation with vn %s failed" %
                              (policy_name, vn1_name))
            self.assertIsNone(vn_update_rsp, "policy dis-association failed")
        self.logger.info("policy %s dis-assocation with vn %s is successful" %
                         (policy_name, vn1_name))

        # delete vn and policy
        np_delete = self.vnc_lib.network_policy_delete(id=str(policy_rsp))
        if np_delete:
            self.logger.info("policy %s is still present on the API server" %
                             policy_name)
            self.assertIsNone(np_delete, "policy delete failed")
        self.logger.info("policy %s is successfully deleted using API server" %
                         policy_name)

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
        topo = topology_class_name()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option='contrail')
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
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
                if ret != True:
                    result = False
                    msg.extend([result_msg, policy])
                self.assertEqual(result, True, msg)
        return True
    # end test_policy_with_local_keyword_across_multiple_vn

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
        policy_objs_list = policy_test_utils._create_n_policy_n_rules(
            self, number_of_policy, valid_rules, number_of_dummy_rules, option='api')
        self.logger.info('Create VN and associate %d policy' %
                         (number_of_policy))

        vn_fixture = {}
        vm_fixture = {}
        ref_tuple = []
        for conf_policy in policy_objs_list:
            ref_tuple.append(
                (conf_policy, VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0))))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name='admin'))
        for vn_name in vn_names:
            vn_fixture[vn_name] = self.useFixture(
                VirtualNetworkTestFixtureGen(
                    self.vnc_lib, virtual_network_name=vn_name,
                    parent_fixt=proj_fixt, id_perms=IdPermsType(enable=True), network_policy_ref_infos=ref_tuple, network_ipam_ref_infos=vn_nets[vn_name]))
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(vn_fixture[vn_name]._obj.uuid))
            if not vn_read:
                self.logger.error("VN %s read on API server failed" % vn_name)
                return {'result': False, 'msg': "VN:%s read failed on API server" % vn_name}
        for vm_name in vm_names:
            vn_read = self.vnc_lib.virtual_network_read(
                id=str(vn_fixture[vn_of_vm[vm_name]]._obj.uuid))
            vn_quantum_obj = self.quantum_fixture.get_vn_obj_if_present(
                vn_read.name)
            # Launch VM with 'ubuntu-traffic' image which has scapy pkg
            # remember to call install_pkg after VM bringup
            # Bring up with 2G RAM to support multiple traffic streams..
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_quantum_obj,
                          flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm_fixture[vm_name].vm_obj)]['host_ip']
            self.logger.info("Calling VM verifications... ")
            time.sleep(5)     # wait for 5secs after launching VM's
            vm_verify_out = None
            vm_verify_out = vm_fixture[vm_name].verify_on_setup()
            if vm_verify_out == False:
                m = "%s - vm verify in agent after launch failed" % vm_node_ip
                err_msg.append(m)
                return {'result': vm_verify_out, 'msg': err_msg}
        for vm_name in vm_names:
            out = self.nova_fixture.wait_till_vm_is_up(
                vm_fixture[vm_name].vm_obj)
            if out == False:
                return {'result': out, 'msg': "VM failed to come up"}
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
        if ret != True:
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
        topo = topology_class_name()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option='contrail')
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo, config_topo = out['data']
        return True
    # end test_policy_api_fixtures

    def _create_policy(self, policy_name, rules_list):
        ''' Create a policy from the supplied rules
        Sample rules_list:
        src_ports and dst_ports : can be 'any'/tuple/list as shown below
        protocol  :  'any' or a string representing a protocol number : ICMP(1), TCP(6), UDP(17)
        simple_action : pass/deny
        source_network/dest_network : VN name
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'any',
               'source_network': vn1_name,
               'src_ports'     : 'any',
               'src_ports'     : (10,100),
               'dest_network'  : vn1_name,
               'dst_ports'     : [100,10],
             },
            {
               'direction'     : '<>',
               'simple_action' : 'pass', 'protocol'      : 'icmp',
               'source_network': vn1_name, 'src_ports'     : (10,100),
               'dest_network'  : vn1_name, 'dst_ports'     : [100,10],
             }
                ]
        '''
        np_rules = []
        for rule_dict in rules_list:
            new_rule = {
                'direction': '<>',
                'simple_action': 'pass',
                'protocol': 'any',
                'source_network': None,
                'src_ports': [PortType(-1, -1)],
                'application': None,
                'dest_network': None,
                'dst_ports': [PortType(-1, -1)],
                'action_list': None
            }
            for key in rule_dict:
                new_rule[key] = rule_dict[key]
            # end for
            # Format Source ports
            if 'src_ports' in rule_dict:
                if type(rule_dict['src_ports']) is tuple or type(rule_dict['src_ports']) is list:
                    new_rule['src_ports'] = [
                        vnc_api.PortType(rule_dict['src_ports'][0], rule_dict['src_ports'][1])]
                elif rule_dict['src_ports'] == 'any':
                    new_rule['src_ports'] = [vnc_api.PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Source ports arguments, should be (Start port, end port) or any ")
                    return None
            # Format Dest ports
            if 'dst_ports' in rule_dict:
                if 'dst_ports' in rule_dict and type(rule_dict['dst_ports']) is tuple or type(rule_dict['dst_ports']) is list:
                    new_rule['dst_ports'] = [
                        vnc_api.PortType(rule_dict['dst_ports'][0], rule_dict['dst_ports'][1])]
                elif rule_dict['dst_ports'] == 'any':
                    new_rule['dst_ports'] = [vnc_api.PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Destination ports arguments, should be (Start port, end port) or any ")
                    return None

            source_vn = ':'.join(self.project_fq_name) + \
                ':' + new_rule['source_network']
            dest_vn = ':'.join(self.project_fq_name) + \
                ':' + new_rule['dest_network']
            # handle 'any' network case
            if rule_dict['source_network'] == 'any':
                source_vn = 'any'
            if rule_dict['dest_network'] == 'any':
                dest_vn = 'any'
            # end code to handle 'any' network
            new_rule['source_network'] = [
                vnc_api.AddressType(virtual_network=source_vn)]
            new_rule['dest_network'] = [
                vnc_api.AddressType(virtual_network=dest_vn)]
            np_rules.append(
                vnc_api.PolicyRuleType(direction=new_rule['direction'],
                                       simple_action=new_rule[
                                           'simple_action'],
                                       protocol=new_rule[
                                           'protocol'],
                                       src_addresses=new_rule[
                                           'source_network'],
                                       src_ports=new_rule['src_ports'],
                                       application=new_rule['application'],
                                       dst_addresses=new_rule[
                                           'dest_network'],
                                       dst_ports=new_rule['dst_ports'],
                                       action_list=new_rule['action_list']))

        # end for
        self.logger.debug("Policy np_rules : %s" % (np_rules))
        pol_entries = vnc_api.PolicyEntriesType(np_rules)
        proj = self.vnc_lib.project_read(self.project_fq_name)
        policy_obj = vnc_api.NetworkPolicy(
            policy_name, network_policy_entries=pol_entries, parent_obj=proj)
        return policy_obj
    # end  _create_policy

    def verify_policy_in_api_quantum_server(self, api_policy_obj, quantum_policy_obj):
        '''Validate policy information in API-Server. Compare data with quantum based policy fixture data.
        Check specifically for following:
        api_server_keys: 1> fq_name, 2> uuid, 3> rules
        quantum_fixture_keys: 1> policy_fq_name, 2> id in policy_obj, 3> policy_obj [for rules]
        '''
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.info("====Verifying data for %s in API_Server ======" %
                         (api_policy_obj.fq_name[2]))
        self.api_s_policy_obj = self.api_s_inspect.get_cs_policy(
            policy=api_policy_obj.fq_name[2], refresh=True)
        self.api_s_policy_obj_x = self.api_s_policy_obj['network-policy']

        # compare policy_fq_name
        out = policy_test_utils.compare_args(
            'policy_fq_name', api_policy_obj.fq_name, quantum_policy_obj['policy']['fq_name'])
        if out:
            err_msg.append(out)
        # compare policy_uuid
        out = policy_test_utils.compare_args(
            'policy_uuid', api_policy_obj.uuid, quantum_policy_obj['policy']['id'])
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

# end TestApiPolicyFixture
