import os
import fixtures
import testtools
import unittest

from testresources import ResourcedTestCase

from connections import ContrailConnections
from securitygroup.config import ConfigSecGroup
from tcutils.wrappers import preposttest_wrapper
from securitygroup.setup import SecurityGroupSetupResource
from verify import VerifySecGroup
from policy.config import ConfigPolicy
from sdn_topo_setup import *
from topo_helper import *
import sdn_sg_test_topo


class SecurityGroupRegressionTests(testtools.TestCase, ResourcedTestCase,
                                   fixtures.TestWithFixtures,
                                   ConfigSecGroup, VerifySecGroup):

    resources = [('base_setup', SecurityGroupSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SecurityGroupSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.inputs.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture

    def __del__(self):
        self.logger.debug("Unconfig the common resurces.")
        SecurityGroupSetupResource.finishedWith(self.res)

    def setUp(self):
        super(SecurityGroupRegressionTests, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests.")
        super(SecurityGroupRegressionTests, self).tearDown()
        SecurityGroupSetupResource.finishedWith(self.res)

    def runTest(self):
        pass

    def config_policy_and_attach_to_vn(self, rules):
        policy_name = "sec_grp_policy"
        policy_fix = self.config_policy(policy_name, rules)
        assert policy_fix.verify_on_setup()
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.res.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.res.vn2_fix)

    @preposttest_wrapper
    def test_sec_group_with_proto(self):
        """Verify security group with allow specific protocol on all ports and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto()
        return True

    @preposttest_wrapper
    def test_sec_group_with_port(self):
        """Verify security group with allow specific protocol/port and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(port_test=True)
        return True

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp(self):
        """Verify security group with allow specific protocol on all ports and policy with allow only TCP between VN's"""
        self.logger.info("Configure the policy with allow TCP only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp()
        return True

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp_ports(self):
        """Verify security group with allow specific protocol on all ports and policy with allow only TCP on specifif ports between VN's"""
        self.logger.info(
            "Configure the policy with allow TCP port 8000/9000 only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.res.vn1_name,
                'src_ports': [8000, 8000],
                'dest_network': self.res.vn2_name,
                'dst_ports': [9000, 9000],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp_port()
        return True

    @preposttest_wrapper
    def test_vn_compute_sg_comb(self):
        """ Verify traffic between intra/inter VN,intra/inter compute and same/diff default/user-define SG"""
        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_4vn_xvm_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, compute_node_list=self.inputs.compute_ips)
        except (AttributeError,NameError):
            topo = topology_class_name()

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify_negative_cases(topo_obj, config_topo)
        return True
    #end test_vn_compute_sg_comb

    @preposttest_wrapper
    def test_sec_group_with_proto_double_rules_sg1(self):
        """Verify security group with allow tcp/udp protocol on all ports and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)
        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)
        self.verify_sec_group_port_proto(double_rule=True)
        return True
#end test_sec_group_with_proto_double_rules_sg1

    @preposttest_wrapper
    def test_sg_stateful(self):
        """ Test if SG is stateful:
        1. test if inbound traffic without allowed ingress rule is allowed
        2. Test if outbound traffic without allowed egress rule is allowed
        3. test traffic betwen SG with only ingress/egress rule"""

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo_sg_stateful(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except (AttributeError,NameError):
            topo.build_topo_sg_stateful()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=False)
        return True
    #end test_sg_stateful

    @preposttest_wrapper
    def test_sg_multiproject(self):
        """ Test SG across projects"""

        topology_class_name = None

        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config_multiproject

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))

        topo = topology_class_name()
        self.topo = topo

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        topo_objs = {}
        config_topo = {}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo_objs, config_topo, vm_fip_info = out['data']

        self.start_traffic_and_verify_multiproject(topo_objs, config_topo, traffic_reverse=False)

        return True

    @preposttest_wrapper
    def test_sg_no_rule(self):
        '''Test SG without any rule:
           it should deny all traffic'''

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_1vn_2vm_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except (AttributeError,NameError):
            topo.build_topo()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=True)

        return True
        #end test_sg_no_rule

