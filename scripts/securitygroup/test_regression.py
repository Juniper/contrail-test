from __future__ import absolute_import
from builtins import range
from common.securitygroup.base import BaseSGTest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from common.securitygroup.verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture, get_secgrp_id_from_name,\
    set_default_sg_rules
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
sys.path.append(os.path.realpath('scripts/flow_tests'))
from tcutils.topo.sdn_topo_setup import *
import test
from common.securitygroup import sdn_sg_test_topo
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name
from base_traffic import *
from tcutils.util import skip_because
from . import test_regression_basic
from common.securitygroup.sdn_sg_test_topo import get_sg_rule

AF_TEST = 'v6'


class SecurityGroupRegressionTests2(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests2, cls).setUpClass()
        cls.option = 'openstack'

    def setUp(self):
        super(SecurityGroupRegressionTests2, self).setUp()
        self.create_sg_test_resources()

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests2.")
        super(SecurityGroupRegressionTests2, self).tearDown()

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_sec_group_with_proto(self):
        """
        Description: Verify security group with allow specific protocol on all ports and policy with allow all between VN's
        Steps:
            1. create the resources VN,VM,policy,SG
            2. update the SG rules with proto tcp(for sg1) and udp(sg2)
            3. verify if traffic allowed is as per the proto allowed in SG rule
        Pass criteria: step 3 should pass
        """
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto()
        return True

    @preposttest_wrapper
    def test_sec_group_with_port(self):
        """
        Description: Verify security group with allow specific protocol/port and policy with allow all between VN's
        Steps:
            1. create the resources VN,VM,policy,SG
            2. update the SG rules with proto tcp(for sg1) and udp(sg2) and open port 8000-9000
            3. verify if traffic allowed is as per the proto/port allowed in SG rule
        Pass criteria: step 3 should pass
        """

        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(
            port_test=True,
            sport=8000,
            dport=9000)
        return True

# end class SecurityGroupRegressionTests2


class SecurityGroupRegressionTests3(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests3, cls).setUpClass()
        cls.option = 'openstack'

    def setUp(self):
        super(SecurityGroupRegressionTests3, self).setUp()
        self.create_sg_test_resources()

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests3.")
        super(SecurityGroupRegressionTests3, self).tearDown()

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp(self):
        """
        Description: Verify security group with allow specific protocol on all ports and policy with allow only TCP between VN's
        Steps:
            1. create the resources VN,VM,policy,SG
            2. update the SG rules with proto tcp(for sg1) and udp(sg2)
            3. verify if traffic allowed is as per the proto allowed in SG rule and policy
        Pass criteria: step 3 should pass
        """

        self.logger.info("Configure the policy with allow TCP only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp()
        return True

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp_ports(self):
        """
        Description: Verify security group with allow specific protocol on all ports and policy with allow only TCP on specifif ports between VN's
        Steps:
            1. create the resources VN,VM,policy,SG
            2. update the SG rules with proto tcp(for sg1) and udp(sg2)
            3. verify if traffic allowed is as per the proto allowed in SG rule and port in policy
        Pass criteria: step 3 should pass
        """

        self.logger.info(
            "Configure the policy with allow TCP port 8000/9000 only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.vn1_name,
                'src_ports': [8000, 8000],
                'dest_network': self.vn2_name,
                'dst_ports': [9000, 9000],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp_port(
            sport=8000,
            dport=9000)
        return True

# end class SecurityGroupRegressionTests3


class SecurityGroupRegressionTests4(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests4, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    @skip_because(feature='multi-subnet')
    def test_vn_compute_sg_comb(self):
        """
        Description: Verify traffic between intra/inter VN,intra/inter compute and same/diff default/user-define SG
        Steps:
            1. define the topology for intra/inter VN,intra/inter compute and same/diff default/user-define SG
            2. create the resources as defined in the topo
            3. verify the traffic
        Pass criteria: step 3 should pass
        """
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
                password=self.project.password,
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option,
                af_test=self.inputs.get_af())
        except (AttributeError, NameError):
            topo = topology_class_name(
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option,
                af_test=self.inputs.get_af())

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(
            VmToNodeMapping=topo.vm_node_map,
            config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify_negative_cases(topo_obj, config_topo)
        return True
    # end test_vn_compute_sg_comb

# end class SecurityGroupRegressionTests4


class SecurityGroupRegressionTests5(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests5, cls).setUpClass()
        cls.option = 'openstack'

    def setUp(self):
        super(SecurityGroupRegressionTests5, self).setUp()
        self.create_sg_test_resources()

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests5.")
        super(SecurityGroupRegressionTests5, self).tearDown()

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_sec_group_with_proto_double_rules_sg1(self):
        """
        Description: Verify security group with allow tcp/udp protocol on all ports and policy with allow all between VN's
        Steps:
            1. create the resources VN,VM,policy,SG
            2. update the SG rules with proto tcp/udp
            3. verify if traffic allowed is as per the proto allowed in SG rule
        Pass criteria: step 3 should pass
        """

        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                 'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg1_fix.replace_rules(rule)
        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(double_rule=True)
        return True
    # end test_sec_group_with_proto_double_rules_sg1

    @preposttest_wrapper
    def test_default_sg(self):
        """
        Description: test default security group
        Steps:
            1. try to delete default sg, should fail
            2. add/delete rules and verify the rules with traffic
        Pass criteria: step 1 and 2 should pass
        """

        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        # try to delete default sg
        secgrp_fq_name = ':'.join(['default-domain',
                                   self.inputs.project_name,
                                   'default'])
        sg_id = get_secgrp_id_from_name(
            self.connections,
            secgrp_fq_name)
        try:
            self.orch.delete_security_group(sg_id)
        except Exception as msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the default security group as expected")
        else:
            try:
                secgroup = self.vnc_lib.security_group_read(
                    fq_name=secgrp_fq_name)
                self.logger.info(
                    "Not able to delete the default security group as expected")
            except NoIdError:
                errmsg = "default Security group deleted"
                self.logger.error(errmsg)
                assert False, errmsg

        # delete egress rule and add new rules and verify with traffic
        self.sg1_fix.delete_all_rules(sg_id)
        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_rules = self.sg1_fix.create_sg_rule(sg_id, secgrp_rules=rule)
        assert secgrp_rules

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass')

        # revert back default sg
        assert set_default_sg_rules(self.connections, sg_id)
        self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail')
        return True
        # end test_default_sg

# end class SecurityGroupRegressionTests5


class SecurityGroupRegressionTests6(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests6, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    @skip_because(feature='multi-subnet')
    def test_sg_stateful(self):
        """
        Description: Test if SG is stateful
            1. test if inbound traffic without allowed ingress rule is allowed
            2. Test if outbound traffic without allowed egress rule is allowed
            3. test traffic betwen SG with only ingress/egress rule
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic
        Pass criteria: step 3 should pass
        """

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo_sg_stateful(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo_sg_stateful(config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(
            topo_obj,
            config_topo,
            traffic_reverse=False)
        return True
    # end test_sg_stateful

    @preposttest_wrapper
    @skip_because(feature='multi-subnet')
    def test_sg_no_rule(self):
        """
        Description: Test SG without any rule, it should deny all traffic
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic denied
        Pass criteria: step 3 should pass
        """

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_1vn_2vm_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo(config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(
            topo_obj,
            config_topo,
            traffic_reverse=True)

        return True
        # end test_sg_no_rule

# end class SecurityGroupRegressionTests6


class SecurityGroupRegressionTests7(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests7, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_icmp_error_handling1(self):
        """
        Description: Test ICMP error handling
            1. ingress-udp from same SG, egress-all
            2. Test with SG rule, ingress-egress-udp only
            3. Test with SG rule, ingress-egress-all
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic for each of the cases mentioned in description
        Pass criteria: step 3 should pass
        """

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo(config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        # Test SG rule, ingress-udp same SG, egress-all
        port = 10000
        pkt_cnt = 10
        src_vm_name = 'vm1'
        dst_vm_name = 'vm3'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())

        if self.inputs.get_af() == 'v4':
            #icmp type 3 code 3, port unreachable
            filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (
                dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        elif self.inputs.get_af() == 'v6':
            #icmp6 type 1 code 4, port unreachable
            filters = '\'(icmp6 and ip6[40]=1 and ip6[41]=4 and src host %s and dst host %s)\'' % (
                dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        # start tcpdump on src VM
        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)

        if sys.version_info > (3,0):
            self.logger.info("Sleeping for 5 seconds ------------------")
            sleep(5)

        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', receiver=False)

        # verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)

        # Test with SG rule, ingress-egress-udp only
        rule = [get_sg_rule('egress',af=self.inputs.get_af(),
            proto='udp'),
                get_sg_rule('ingress',af=self.inputs.get_af(),
            proto='udp')
                 ]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        # start tcpdump on src VM
        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)

        if sys.version_info > (3,0):
            self.logger.info("Sleeping for 5 seconds ------------------")
            sleep(5)

        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', receiver=False)

        # verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)

        # Test with SG rule, ingress-egress-all
        dst_vm_fix = config_topo['vm']['vm2']
        rule = [get_sg_rule('egress',af=self.inputs.get_af(),
            proto='any'),
                get_sg_rule('ingress',af=self.inputs.get_af(),
            proto='any')
                 ]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        # start tcpdump on src VM
        if self.inputs.get_af() == 'v4':
            #icmp type 3 code 3, port unreachable
            filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (
                dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        elif self.inputs.get_af() == 'v6':
            #icmp6 type 1 code 4, port unreachable
            filters = '\'(icmp6 and ip6[40]=1 and ip6[41]=4 and src host %s and dst host %s)\'' % (
                dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)

        if sys.version_info > (3,0):
            self.logger.info("Sleeping for 5 seconds ------------------")
            sleep(5)

        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', receiver=False)

        # verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)

        return True
    # end test_icmp_error_handling1

    @preposttest_wrapper
    def test_icmp_error_handling2(self):
        """
        Description:
            1. Test ICMP error handling with SG rules egress-udp only
            2. Test ICMP error from agent
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic for each of the cases mentioned in description
        Pass criteria: step 3 should pass
        """

        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo2(
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(
            VmToNodeMapping=topo.vm_node_map,
            config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        # Test with SG rule, egress-udp only
        port = 10000
        pkt_cnt = 10
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())

        # start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)

        if sys.version_info > (3,0):
            self.logger.info("Sleeping for 5 seconds ------------------")
            sleep(5)

        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', receiver=False)

        # verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)
        # Test ICMP error from agent
        if len(self.connections.orch.get_hosts()) < 2:
            self.logger.info("Skipping second case(Test ICMP error from agent), \
                                    this test needs atleast 2 compute nodes")
            raise self.skipTest("Skipping second case(Test ICMP error from agent), \
                                    this test needs atleast 2 compute nodes")
            return True
        rule = [{'direction': '>',
                 'protocol': 'icmp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'icmp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        vn1_name = "test_vnv6sr"
        vn1_net = ['2001::101:0/120']
        #vn1_fixture = self.config_vn(vn1_name, vn1_net)
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_net))
        assert vn1_fixture.verify_on_setup()
        vn2_name = "test_vnv6dn"
        vn2_net = ['2001::201:0/120']
        #vn2_fixture = self.config_vn(vn2_name, vn2_net)
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_net))
        assert vn2_fixture.verify_on_setup()
        vm1_name = 'source_vm'
        vm2_name = 'dest_vm'
        #vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        #vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        af_old = self.inputs.get_af()
        self.inputs.set_af('dual')
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vm1_name,
                node_name=None,
                image_name='ubuntu-traffic',
                flavor='contrail_flavor_small'))

        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vm2_name,
                node_name=None,
                image_name='ubuntu-traffic',
                flavor='contrail_flavor_small'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        rule = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1_name,
                'src_ports': [0, -1],
                'dest_network': vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        policy_name = 'allow_all'
        policy_fixture = self.config_policy(policy_name, rule)

        vn1_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn1_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn2_fixture)

        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
        self.logger.info(
            "Increasing MTU on src VM and ping with bigger size and reverting MTU")
        cmd_ping = (
            'ping -M want -s 2500 -c 10 %s | grep \"Frag needed and DF set\"' %
            (dst_vm_fix.vm_ip))

        output = src_vm_fix.run_cmd_on_vm(
            cmds=['''netstat -anr  |grep ^0.0.0.0 | awk '{ print $2 }' '''],
            as_sudo=True)
        gw = list(output.values())[0].split('\r\n')[-1]

        filters = '\'(icmp and ((src host %s and dst host %s) or (src host %s and dst host %s)))\'' % (
            gw, src_vm_fix.vm_ip, src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)
        cmds = ['ifconfig eth0 mtu 3000', cmd_ping,
                'ifconfig eth0 mtu 1500']
        output = src_vm_fix.run_cmd_on_vm(
            cmds=cmds,
            as_sudo=True,
            as_daemon=True)
        self.logger.debug("output for ping cmd: %s" % output[cmd_ping])
        if not verify_tcpdump_count(self, session, pcap):
            result = False

        cmd = 'sudo tcpdump -nn -r %s' % pcap
        cmd_check_icmp, err = execute_cmd_out(session, cmd, self.logger)
        cmd_df = re.search('need to frag', cmd_check_icmp)
        cmd_next_icmp = re.search(
            '.+ seq 2, length (\d\d\d\d).*',
            cmd_check_icmp)
        icmpmatch = ("%s > %s: ICMP %s unreachable - need to frag" %
                     (gw, src_vm_fix.vm_ip, dst_vm_fix.vm_ip))
        if not (
            (icmpmatch in cmd_check_icmp) and (
                "need to frag" in cmd_df.group(0)) and (
                cmd_next_icmp.group(1) < '1500') and (
                "Frag needed and DF set" in output[cmd_ping])):
            self.logger.error(
                "expected ICMP error for type 3 code 4 not found")
            result = False
        stop_tcpdump_for_vm_intf(self, session, pcap)
        self.logger.info(
            "increasing MTU on src VM and ping6 with bigger size and reverting MTU")
        cmd_ping = 'ping6 -s 2500 -c 10 %s | grep \"Packet too big\"' % (
            vm2_fixture.vm_ip)

        src_vn_fq_name = vn1_fixture.vn_fq_name
        gw = vm1_fixture.vm_ip
        gw = gw.split(':')
        gw[-1] = '1'
        gw = ':'.join(gw)
        filters = '\'(icmp6 and ((src host %s and dst host %s) or (src host %s and dst host %s)))\'' % (
            gw, vm1_fixture.vm_ip, vm1_fixture.vm_ip, vm2_fixture.vm_ip)

        session, pcap = start_tcpdump_for_vm_intf(
            self, vm1_fixture, src_vn_fq_name, filters=filters)
        cmds = ['ifconfig eth0 mtu 3000', cmd_ping,
                'ifconfig eth0 mtu 1500']
        output = vm1_fixture.run_cmd_on_vm(
            cmds=cmds,
            as_sudo=True,
            as_daemon=True)
        self.logger.debug("output for ping cmd: %s" % output[cmd_ping])
        if not verify_tcpdump_count(self, session, pcap):
            result = False

        cmd = 'sudo tcpdump -nn -r %s' % pcap
        cmd_check_icmp, err = execute_cmd_out(session, cmd, self.logger)
        cmd_next_icmp = re.search(
            '.+ ICMP6, packet too big, mtu (\d\d\d\d).*',
            cmd_check_icmp)
        icmpmatch = ("ICMP6, packet too big")
        if not (
                (icmpmatch in cmd_check_icmp) and (
                    cmd_next_icmp.group(1) < '1500') and (
                "Packet too big" in output[cmd_ping])):
            self.logger.error(
                "expected ICMP6 error for type 2 packet too big message not found")
            result = False
        stop_tcpdump_for_vm_intf(self, session, pcap)
        self.inputs.set_af(af_old)

        assert result
        return result
        # end test_icmp_error_handling2

    @preposttest_wrapper
    @skip_because(feature='service-instance')
    def test_icmp_error_handling_from_mx_with_si(self):
        """
        Description: Test ICMP error handling from MX with SI in the middle
            1. uses traceroute util on the VM
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. copy the traceroute pkg to VM and install
            4. run the traceroute to 8.8.8.8
            5. verify through tcpdump if icmp error recvd on VM
        Pass criteria: step 5 should pass
        """

        if ('MX_GW_TEST' not in os.environ) or (
                ('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') != '1')):
            self.logger.info(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            return True

        public_vn_info = {
            'subnet': [
                self.inputs.fip_pool],
            'router_asn': self.inputs.router_asn,
            'rt_number': self.inputs.mx_rt}
        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_mx_with_si

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                public_vn_info=public_vn_info, config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo(
                public_vn_info=public_vn_info,
                config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(skip_verify='no', config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        svc_chain_info = self.config_svc_chain(
            service_mode='transparent',
            service_type='firewall',
            svc_img_name='tiny_trans_fw',
            left_vm_fixture=config_topo['vm'][topo_obj.vmc_list[0]],
            right_vm_fixture=config_topo['vm'][topo_obj.vmc_list[1]])
        st_fixture = svc_chain_info['st_fixture']
        si_fixture = svc_chain_info['si_fixture']

        src_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())

        pkg = 'traceroute_2.0.18-1_amd64.deb'

        self.logger.info("copying traceroute pkg to the compute node.")
        path = os.getcwd() + '/tcutils/pkgs/' + pkg
        src_vm_fix.copy_file_to_vm(path, '/tmp')

        self.logger.info("installing traceroute")
        cmd = 'dpkg -i /tmp/' + pkg
        output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert "Setting up traceroute" in output_cmd_dict[
            cmd], "traceroute pkg installation error, output:%s" % output_cmd_dict[cmd]

        self.logger.info("starting tcpdump on src VM")
        filters = '\'(icmp[0]=11 and icmp[1]=0)\''
        session, pcap = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)

        self.logger.info("starting traceroute to out of cluster, 8.8.8.8")
        cmd = 'traceroute 8.8.8.8'
        for i in range(0, 4):
            output_cmd_dict = src_vm_fix.run_cmd_on_vm(
                cmds=[cmd],
                as_sudo=True)
            self.logger.info(output_cmd_dict[cmd])

            if verify_tcpdump_count(self, session, pcap):
                return True

        return False
        # end test_icmp_error_handling_from_mx_with_si

    @preposttest_wrapper
    def test_icmp_error_payload_matching(self):
        """
        Description: Test ICMP error handling with payload diff. from original packet
            1. icmp pakcet with payload matching should be accepted and others should be denied
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. send the traffic from sender to unreachable port on recvr side(port 10000 used here), recvr will send icmp error to sender for "destination port unreachable"
            4. from recvr side send many other icmp error types in loop
            5. sender should recv only icmp error mentioned in step 3 and should NOT recv errors mentioned in step4
        Pass criteria: step 5 should pass
        """

        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo2(
                compute_node_list=self.connections.orch.get_hosts(),
                config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(
            VmToNodeMapping=topo.vm_node_map,
            config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        # Test with SG rule, egress-udp only and also send diff ICMP error with
        # diff payload
        port = 10000
        pkt_cnt = 2
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())

        # start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3)\''
        session1, pcap1 = start_tcpdump_for_vm_intf(
            self, src_vm_fix, src_vn_fq_name, filters=filters)
        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', receiver=False)

        icmp_code = 0
        for icmp_type in range(0, 3):
                # start tcpdump on src VM
            filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (
                icmp_type, icmp_code)
            session, pcap = start_tcpdump_for_vm_intf(
                self, src_vm_fix, src_vn_fq_name, filters=filters)
            sender, receiver = self.start_traffic_scapy(
                dst_vm_fix, src_vm_fix, 'icmp', port, port, payload="payload", icmp_type=icmp_type, icmp_code=icmp_code, count=pkt_cnt)
            sent, recv = self.stop_traffic_scapy(sender, receiver)
            # verify packet count and stop tcpdump
            assert verify_tcpdump_count(
                self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        # type 3 , code (0,3)
        icmp_type = 3
        for icmp_code in range(0, 3):
            # start tcpdump on src VM
            filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (
                icmp_type, icmp_code)
            session, pcap = start_tcpdump_for_vm_intf(
                self, src_vm_fix, src_vn_fq_name, filters=filters)
            sender, receiver = self.start_traffic_scapy(
                dst_vm_fix, src_vm_fix, 'icmp', port, port, payload="payload", icmp_type=icmp_type, icmp_code=icmp_code, count=pkt_cnt)
            sent, recv = self.stop_traffic_scapy(sender, receiver)
            # verify packet count and stop tcpdump
            assert verify_tcpdump_count(
                self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        # type 3 , code (4,15)
        icmp_type = 3
        for icmp_code in range(4, 16):
            # start tcpdump on src VM
            filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (
                icmp_type, icmp_code)
            session, pcap = start_tcpdump_for_vm_intf(
                self, src_vm_fix, src_vn_fq_name, filters=filters)
            sender, receiver = self.start_traffic_scapy(
                dst_vm_fix, src_vm_fix, 'icmp', port, port, payload="payload", icmp_type=icmp_type, icmp_code=icmp_code, count=pkt_cnt)
            sent, recv = self.stop_traffic_scapy(sender, receiver)
            # verify packet count and stop tcpdump
            assert verify_tcpdump_count(
                self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        # type (4,11), code 0
        icmp_code = 0
        for icmp_type in range(4, 12):
            # start tcpdump on src VM
            filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (
                icmp_type, icmp_code)
            session, pcap = start_tcpdump_for_vm_intf(
                self, src_vm_fix, src_vn_fq_name, filters=filters)
            sender, receiver = self.start_traffic_scapy(
                dst_vm_fix, src_vm_fix, 'icmp', port, port, payload="payload", icmp_type=icmp_type, icmp_code=icmp_code, count=pkt_cnt)
            sent, recv = self.stop_traffic_scapy(sender, receiver)
            # verify packet count and stop tcpdump
            assert verify_tcpdump_count(
                self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        # verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session1, pcap1)
        return True
        # end test_icmp_error_payload_matching

# end class SecurityGroupRegressionTests7


class SecurityGroupRegressionTests8(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests8, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_flow_to_sg_rule_mapping(self):
        """
        Description: test flow to security group rule uuid mapping for
            1. default SG
            2. user-defined SG
        Steps:
            1. create resources as defined in topology
            2. start traffic for specific protocol which matches with specific security group rule
            3. get flow records from agent and verify if sg rule uuid matches with corresponding ingress/egress rule id
        Pass criteria:
            step 3 should PASS
        """

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.inputs.compute_ips,
                config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo(compute_node_list=self.inputs.compute_ips,
                            config_option=self.option)

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,
                                   config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        proto = 'udp'
        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        default_secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      'default']))

        # test with default SG
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, proto)


        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            default_secgrp_id,
            proto,
            port)

        # test with user-defined SG
        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        src_vm_fix.remove_security_group(secgrp=default_secgrp_id)
        dst_vm_fix.remove_security_group(secgrp=default_secgrp_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, proto)

        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            secgrp_id,
            proto,
            port)

        return True
    # end test_flow_to_sg_rule_mapping

    @preposttest_wrapper
    def test_flow_to_sg_rule_mapping_multiple_rules(self):
        """
        Description: test flow to security group rule uuid mapping for
        1. SG with multiple rules and diff active flows matching diff. rules
        2. Multiple SG attached to VMs and diff active flows matching diff. SG
        Steps:
            1. create resources as defined in topology
            2. start traffic for specific protocol which matches with specific security group rule
            3. get flow records from agent and verify if sg rule uuid matches with corresponding ingress/egress rule id
        Pass criteria:
            step 3 should PASS
        """

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.inputs.compute_ips,
                config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo2(compute_node_list=self.inputs.compute_ips,
                             config_option=self.option)

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,
                                   config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]

        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        if self.inputs.get_af() == 'v4':
            traffic_obj_tcp = BaseTraffic.factory(proto='tcp')
            assert traffic_obj_tcp
            assert traffic_obj_tcp.start(src_vm_fix, dst_vm_fix,
                'tcp', port, port)
            if sys.version_info > (3,0):
                assert src_vm_fix.ping_with_certainty(dst_vm_fix.vm_ip, expectation=True)
            else:
                sender_icmp, receiver_icmp = self.start_traffic_scapy(
                    src_vm_fix, dst_vm_fix, 'icmp', port, port, payload="payload")

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            secgrp_id,
            'udp',
            port)

        sg_name = topo_obj.sg_list[1]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        if self.inputs.get_af() == 'v4':
            assert self.verify_flow_to_sg_rule_mapping(
                src_vm_fix,
                dst_vm_fix,
                src_vn_fix,
                dst_vn_fix,
                secgrp_id,
                'tcp',
                port)

            port = 0
            sg_name = topo_obj.sg_list[0]
            secgrp_id = get_secgrp_id_from_name(
                self.connections,
                ':'.join([self.connections.domain_name,
                          self.inputs.project_name,
                          sg_name]))

            if sys.version_info < (3,0):
                assert self.verify_flow_to_sg_rule_mapping(
                    src_vm_fix,
                    dst_vm_fix,
                    src_vn_fix,
                    dst_vn_fix,
                    secgrp_id,
                    'icmp',
                    port)

            sent, recv = traffic_obj_tcp.stop()
            if sys.version_info < (3,0):
                sent, recv = self.stop_traffic_scapy(sender_icmp, receiver_icmp)

        return True
    # end test_flow_to_sg_rule_mapping_multiple_rules

    @preposttest_wrapper
    def test_flow_to_sg_rule_mapping_intra_vn(self):
        """
        Description: test flow to security group rule uuid mapping for
            1. intra VN traffic with diff SG in src and dst VM
        Steps:
            1. create resources as defined in topology
            2. start traffic for specific protocol which matches with specific security group rule
            3. get flow records from agent and verify if sg rule uuid matches with corresponding ingress/egress rule id
        Pass criteria:
            step 3 should PASS
        """

        topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling
        topo = topology_class_name(af_test=self.inputs.get_af())
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo2(config_option=self.option)

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        rule = [get_sg_rule('egress',af=self.inputs.get_af(),
            proto='udp'),
                get_sg_rule('ingress',af=self.inputs.get_af(),
            proto='udp')]

        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        proto = 'udp'
        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_sg_name = topo_obj.sg_list[0]
        dst_sg_name = topo_obj.sg_list[1]

        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      src_sg_name]))
        # start traffic
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, proto)

        # get the egress rule uuid
        rule_uuid = None
        rules = list_sg_rules(self.connections, secgrp_id)
        af = self.inputs.get_af()
        for rule in rules:
            if rule['direction'] == 'egress' and \
               ((af == 'v4' and (rule['ethertype'] == 'IPv4' or \
                   rule['remote_ip_prefix'] == '0.0.0.0/0')) or \
                (af == 'v6' and (rule['ethertype'] == 'IPv6' or \
                   rule['remote_ip_prefix'] == '::/0'))) and \
               (rule['protocol'] == 'any' or rule['protocol'] == proto):
                rule_uuid = rule['id']
                break
        assert rule_uuid, "Egress rule id could not be found"

        test_result = True
        nh_dst = dst_vm_fix.tap_intf[dst_vn_fq_name]['flow_key_idx']
        nh = src_vm_fix.tap_intf[src_vn_fq_name]['flow_key_idx']
        # verify forward flow on src compute node
        if not self.fetch_flow_verify_sg_uuid(
                nh, src_vm_fix, dst_vm_fix, port, port, '17',
                rule_uuid, src_vm_fix.vm_node_ip):
            test_result = False

        # verify reverse flow on src compute node
        if src_vm_fix.vm_node_ip == dst_vm_fix.vm_node_ip:
            nh = nh_dst
        if not self.fetch_flow_verify_sg_uuid(
                nh, dst_vm_fix, src_vm_fix, port, port, '17',
                rule_uuid, src_vm_fix.vm_node_ip):
            test_result = False

        if src_vm_fix.vm_node_ip != dst_vm_fix.vm_node_ip:
            secgrp_id = get_secgrp_id_from_name(
                self.connections,
                ':'.join([self.connections.domain_name,
                          self.inputs.project_name,
                          dst_sg_name]))

            # get the ingress rule uuid
            rule_uuid = None
            rules = list_sg_rules(self.connections, secgrp_id)
            for rule in rules:
                if rule['direction'] == 'ingress' and \
                   ((af == 'v4' and (rule['ethertype'] == 'IPv4' or \
                        rule['remote_ip_prefix'] == '0.0.0.0/0' or \
                        rule['remote_group_id'] == secgrp_id)) or \
                    (af == 'v6' and (rule['ethertype'] == 'IPv6' or \
                        rule['remote_group_id'] == secgrp_id or \
                        rule['remote_ip_prefix'] == '::/0'))) and \
                   (rule['protocol'] == 'any' or rule['protocol'] == proto):
                    rule_uuid = rule['id']
                    break
            assert rule_uuid, "Ingress rule id could not be found"

            # verify forward flow on dst compute node
            if not self.fetch_flow_verify_sg_uuid(
                    nh_dst, src_vm_fix, dst_vm_fix, port, port, '17',
                    rule_uuid, dst_vm_fix.vm_node_ip):
                test_result = False

            # verify reverse flow on dst compute node
            if not self.fetch_flow_verify_sg_uuid(
                    nh_dst, dst_vm_fix, src_vm_fix, port, port, '17',
                    rule_uuid, dst_vm_fix.vm_node_ip):
                test_result = False

        assert test_result

        return True

    # end test_flow_to_sg_rule_mapping_intra_vn

    @preposttest_wrapper
    def test_verify_sg_rule_uuid_in_control_api(self):
        """
        1. Verify uuid for each sg rule in api/control introspect and neutron cli"""

        topology_class_name = None
        af = self.inputs.get_af()
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name(af_test=af)
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                config_option=self.option)
        except (AttributeError, NameError):
            topo.build_topo2(config_option=self.option)

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        rule = [get_sg_rule('egress',af=af,
            proto='udp'),
                get_sg_rule('ingress',af=af,
            proto='udp')]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        sg_list = ['default', topo_obj.sg_list[0]]
        proto = 'udp'

        try:
            prj_name = self.project.project_name
        except (AttributeError, NameError):
            prj_name = 'admin'

        for sg_name in sg_list:
            secgrp_id = get_secgrp_id_from_name(
                self.connections,
                ':'.join([self.connections.domain_name,
                          self.inputs.project_name,
                          sg_name]))

            # get the egress and ingress rule uuid
            egress_ipv4_id = None
            egress_ipv6_id = None
            ingress_ipv4_id = None
            ingress_ipv6_id = None
            rules = list_sg_rules(self.connections, secgrp_id)
            for rule in rules:
                if rule['direction'] == 'egress' and rule[
                        'ethertype'] == 'IPv4':
                    egress_ipv4_id = rule['id']
                elif rule['direction'] == 'ingress' and rule['ethertype'] == 'IPv4':
                    ingress_ipv4_id = rule['id']
                elif rule['direction'] == 'ingress' and rule['ethertype'] == 'IPv6':
                    ingress_ipv6_id = rule['id']
                elif rule['direction'] == 'egress' and rule['ethertype'] == 'IPv6':
                    egress_ipv6_id = rule['id']

            if af == 'v4':
                assert egress_ipv4_id, "Egress rule id could not be found"
                assert ingress_ipv4_id, "Ingress rule id could not be found"

            elif af == 'v6':
                assert egress_ipv6_id, "Egress rule id could not be found"
                assert ingress_ipv6_id, "Ingress rule id could not be found"

            # get SG rule uuid from api and match with neutron uuid
            api_secgrp_obj = self.api_s_inspect.get_cs_secgrp(
                project=prj_name,
                secgrp=sg_name,
                refresh=True)

            uuid_egress_ipv4 = None
            uuid_ingress_ipv4 = None
            uuid_egress_ipv6 = None
            uuid_ingress_ipv6 = None

            for rule in api_secgrp_obj['security-group']['security_group_entries']['policy_rule']:
                if rule['src_addresses'][0][
                        'security_group'] == "local" and rule['ethertype'] == 'IPv4':
                    uuid_egress_ipv4 = rule['rule_uuid']
                elif rule['dst_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv4':
                    uuid_ingress_ipv4 = rule['rule_uuid']
                elif rule['src_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv6':
                    uuid_egress_ipv6 = rule['rule_uuid']
                elif rule['dst_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv6':
                    uuid_ingress_ipv6 = rule['rule_uuid']

            if egress_ipv4_id:
                assert uuid_egress_ipv4 == egress_ipv4_id, ("egress IPv4 rule "
                    "uuid is not same in API and neutron for SG:%s" % (sg_name))
            if ingress_ipv4_id:
                assert uuid_ingress_ipv4 == ingress_ipv4_id, ("ingress IPv4 "
                    "rule uuid is not same in API "
                    "and neutron for SG:%s" % (sg_name))

            if ingress_ipv6_id:
                assert ingress_ipv6_id == uuid_ingress_ipv6, ("ingress IPv6 "
                    "rule uuid is not same in API "
                    "and neutron for SG:%s" % (sg_name))
            if egress_ipv6_id:
                assert egress_ipv6_id == uuid_egress_ipv6, ("egress IPv6 rule "
                    "uuid is not same in API and neutron for SG:%s" % (sg_name))

            self.logger.info(
                "%s security group rule uuid matches in API with neutron" %
                (sg_name))
            # get SG rule uuid from control node and match with neutron uuid
            for cn in self.inputs.bgp_ips:
                uuid_egress_ipv4 = None
                uuid_ingress_ipv4 = None
                cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp(
                    project=prj_name,
                    secgrp=sg_name)
                for rule in cn_secgrp_obj['obj_info'][0]['data']['security-group-entries']:
                    if rule[
                            'src-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv4':
                        uuid_egress_ipv4 = rule['rule-uuid']
                    elif rule['dst-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv4':
                        uuid_ingress_ipv4 = rule['rule-uuid']
                    elif rule['src-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv6':
                        uuid_egress_ipv6 = rule['rule-uuid']
                    elif rule['dst-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv6':
                        uuid_ingress_ipv6 = rule['rule-uuid']

                if egress_ipv4_id:
                    assert uuid_egress_ipv4 == egress_ipv4_id, ("egress rule "
                        "uuid are not same in control and neutron for SG:%s" % (
                        sg_name))
                if ingress_ipv4_id:
                    assert uuid_ingress_ipv4 == ingress_ipv4_id, ("ingress rule"
                        " uuid are not same in control and neutron for SG:%s" % (
                        sg_name))
                if ingress_ipv6_id:
                    assert ingress_ipv6_id == uuid_ingress_ipv6, ("ingress IPv6"
                        " rule uuid is not same in control "
                        "and neutron for SG:%s" % (sg_name))
                if egress_ipv6_id:
                    assert egress_ipv6_id == uuid_egress_ipv6, ("egress IPv6 "
                        "rule uuid is not same in control "
                        "and neutron for SG:%s" % (sg_name))

            self.logger.info(
                "%s security group rule uuid matches in control with neutron" %
                (sg_name))

        return True
        # end test_verify_sg_rule_uuid_in_control_api

# end class SecurityGroupRegressionTests8


class SecurityGroupRegressionTests9(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests9, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_add_remove_default_sg_active_flow(self):
        """ add/remove default SG from VM when flow is active and traffic from both ends"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(
            topology_class_name, "build_topo")

        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_vn_fq_name = ''
        dst_vn_fq_name = ''
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        sg_name = 'default'
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(tcp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting traffic udp and tcp on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'tcp')

        self.logger.info("Verify traffic udp and tcp on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove security group from source vm.")
        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        sleep(5)

        self.logger.info("Starting tcpdump on src and dest vm after removing SG.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting traffic udp and tcp on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', exp=False)
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'tcp', exp=False)

        self.logger.info("Verify traffic udp and tcp on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1, exp_count=0)
        assert verify_tcpdump_count(self, session2, pcap2, exp_count=0)

        self.logger.info("Add security group back to source vm.")
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        sleep(5)

        self.logger.info("Starting tcpdump on src and dest vm after adding SG.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting traffic on src and dest vm after adding SG.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        for loop in range(30):
            resp = self.send_nc_traffic(
                dst_vm_fix, src_vm_fix, port, port, 'tcp')
            if resp == True:
                break;
            sleep(5)

        self.logger.info("Verify traffic udp and tcp on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        return True
        # end test_add_remove_default_sg_active_flow

    @preposttest_wrapper
    def test_add_remove_sg_active_flow1(self):
        """ add/remove SG from VM when flow is active
        1.Traffic from both ends
        2.Test for SG with rule with remote as sg for both ingress-egress"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(
            topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()
        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_vn_fq_name = ''
        dst_vn_fq_name = ''
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        default_sg_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)
        # ingress-egress from same sg
        rule = [{'direction': '>',
                 'protocol': 'udp',
                 'dst_addresses': [{'security_group': topo_obj.domain + ':' + topo_obj.project + ':' + sg_name}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'security_group': topo_obj.domain + ':' + topo_obj.project + ':' + sg_name}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][sg_name].replace_rules(rule)

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(udp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove %s SG from source vm." % (sg_name))
        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        self.logger.info("Add %s SG to source vm." % ('sg_allow_all'))
        src_vm_fix.add_security_group(secgrp=sg_allow_all)
        sleep(5)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', exp=False)
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'udp', exp=False)

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1, exp_count=0)
        assert verify_tcpdump_count(self, session2, pcap2, exp_count=0)

        self.logger.info("Remove %s SG from source vm." % ('sg_allow_all'))
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow1

    @preposttest_wrapper
    def test_add_remove_sg_active_flow2(self):
        """ add/remove SG from VM when flow is active
        1.Traffic from both ends
        2.Test for SG with egress cidr rule,ingress sg"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(
            topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()

        port = 10000
        port2 = 11000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_vn_fq_name = ''
        dst_vn_fq_name = ''
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        default_sg_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # ingress from same sg and egress to all
        rule = [{'direction': '>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'security_group': topo_obj.domain + ':' + topo_obj.project + ':' + sg_name}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][sg_name].replace_rules(rule)

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(udp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port2, port2, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove %s SG from source vm." % (sg_name))
        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        self.logger.info("Add %s SG to source vm." % ('sg_allow_all'))
        src_vm_fix.add_security_group(secgrp=sg_allow_all)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp', exp=False)
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port2, port2, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1, exp_count=0)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove %s SG from source vm." % ('sg_allow_all'))
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow2

    @preposttest_wrapper
    def test_add_remove_sg_active_flow3(self):
        """ add/remove SG from VM when flow is active
        1. Traffic from both ends
        2. Test for SG with ingress cidr and egress sg"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(
            topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()

        port = 10000
        port2 = 11000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_vn_fq_name = ''
        dst_vn_fq_name = ''
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        default_sg_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # egress to same sg and ingress from all
        rule = [{'direction': '>',
                 'protocol': 'udp',
                 'dst_addresses': [{'security_group': topo_obj.domain + ':' + topo_obj.project + ':' + sg_name}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][sg_name].replace_rules(rule)

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(udp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port2, port2, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove %s SG from source vm." % (sg_name))
        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        self.logger.info("Add %s SG to source vm." % ('sg_allow_all'))
        src_vm_fix.add_security_group(secgrp=sg_allow_all)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port2, port2, 'udp', exp=False)

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2, exp_count=0)

        self.logger.info("Remove %s SG from source vm." % ('sg_allow_all'))
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow3

    @preposttest_wrapper
    def test_add_remove_sg_active_flow4(self):
        """ add/remove SG from VM when flow is active
        1. Traffic from both ends
        2. Test for SG with cidr both ingress-egress"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(
            topology_class_name, "build_topo")

        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        src_vn_fq_name = ''
        dst_vn_fq_name = ''
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      sg_name]))

        default_sg_id = get_secgrp_id_from_name(
            self.connections,
            ':'.join([self.connections.domain_name,
                      self.inputs.project_name,
                      'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # ingress-egress from all
        rule = [{'direction': '>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][sg_name].replace_rules(rule)

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(udp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        self.logger.info("Remove %s SG from source vm." % (sg_name))
        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        self.logger.info("Add %s SG to source vm." % (sg_name))
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        sleep(5)

        self.logger.info("Starting tcpdump on src and dest vm.")
        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = filters1)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = filters2)

        self.logger.info("Starting udp traffic on src and dest vm.")
        assert self.send_nc_traffic(
            src_vm_fix, dst_vm_fix, port, port, 'udp')
        assert self.send_nc_traffic(
            dst_vm_fix, src_vm_fix, port, port, 'udp')

        self.logger.info("Verify udp traffic on src and dest vm.")
        assert verify_tcpdump_count(self, session1, pcap1)
        assert verify_tcpdump_count(self, session2, pcap2)

        return True
        # end test_add_remove_sg_active_flow4

# end class SecurityGroupRegressionTests9


class SecurityGroupSynAckTest(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupSynAckTest, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_syn_ack_create_flow(self):
        """
        Description:
            verify if SYN ack is allowed and flow is created again after flow is expired
        Steps:
            1. configure secgroupA with egress rule
            2. configure secgroupB with ingress/egress rule
            3. Make sure traffic from VM(secgrpB) to VM(secgrpA) fails as the VM(secgrpA) doesn't allow ingress traffic
            4. Send traffic from VM(secgrpA) to VM(secgrpB), expected to pass through
            5. Send SYN from VM(secgrpA) to VM(secgrpB).
            6. recv SYN at VM(secgrpB) and Wait for flow to expire(180 sec)
            7. Send SYN+ACK from VM(secgrpB) to VM(secgrpA), though the flow is expired and VM(secgrpA) denies ingress traffic, SYN_ACK packet of intial SYN should go through.

        Pass criteria:
            step 7 should PASS
        """
        af = self.inputs.get_af()
        topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling
        topo = topology_class_name(af_test=af)
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.inputs.compute_ips)
        except (AttributeError, NameError):
            topo.build_topo2(compute_node_list=self.inputs.compute_ips)

        topo.sg_rules[topo.sg_list[0]] = [
            get_sg_rule('egress',af=af,
                proto='any')]
        topo.sg_rules[topo.sg_list[1]] = [
            get_sg_rule('egress',af=af,
                proto='any'),
            get_sg_rule('ingress',af=af,
                proto='any')]

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(vms_on_single_compute=True)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        src_vm_name = 'vm1'
        src_vm_fix = config_topo['vm'][src_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vm_name = 'vm2'
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        pkg = 'syn_client.py'

        self.logger.info("copying syn client to the src VM.")
        path = os.getcwd() + '/tcutils/pkgs/syn_ack_test/' + pkg
        src_vm_fix.copy_file_to_vm(path, '/tmp')

        self.logger.info("copying syn server to the dst VM.")
        pkg = 'syn_server.py'
        path = os.getcwd() + '/tcutils/pkgs/syn_ack_test/' + pkg
        dst_vm_fix.copy_file_to_vm(path, '/tmp')

        cmd1 = 'chmod +x /tmp/syn_server.py;/tmp/syn_server.py %s %s %s \
                    2>/tmp/server.log 1>/tmp/server.log' \
                    % (src_vm_fix.vm_ip, dst_vm_fix.vm_ip, af)
        cmd2 = 'chmod +x /tmp/syn_client.py;/tmp/syn_client.py %s %s %s \
                    2>/tmp/client.log 1>/tmp/client.log' \
                    % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip, af)
        output_cmd_dict = dst_vm_fix.run_cmd_on_vm(
            cmds=[cmd1],
            as_sudo=True,
            as_daemon=True)
        output_cmd_dict = src_vm_fix.run_cmd_on_vm(
            cmds=[cmd2],
            as_sudo=True,
            as_daemon=True)

        inspect_h1 = self.agent_inspect[src_vm_fix.vm_node_ip]
        flow_rec1 = None
        sport = '8100'
        dport = '8000'
        vn_fq_name = src_vm_fix.vn_fq_name
        flow_timeout = 180

        # verify flow created
        sleep(10)
        for i in range(0,3):
            flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
                nh=src_vm_fix.tap_intf[vn_fq_name]['flow_key_idx'],
                sip=src_vm_fix.vm_ip,
                dip=dst_vm_fix.vm_ip,
                sport=sport,
                dport=dport,
                protocol='6')
            if flow_rec1:
                break
            sleep(1)
        assert flow_rec1
        # wait for flow to expire
        sleep(flow_timeout + 2)

        # verify flow created again
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=src_vm_fix.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=src_vm_fix.vm_ip,
            dip=dst_vm_fix.vm_ip,
            sport=sport,
            dport=dport,
            protocol='6')
        assert flow_rec1

        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=dst_vm_fix.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=dst_vm_fix.vm_ip,
            dip=src_vm_fix.vm_ip,
            sport=dport,
            dport=sport,
            protocol='6')
        assert flow_rec1

        return True
    # end test_syn_ack_create_flow

# end class SecurityGroupSynAckTest


# creating new classes to run all tests with contrail apis
class SecurityGroupBasicRegressionTests1_contrail(
        test_regression_basic.SecurityGroupBasicRegressionTests1):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1_contrail, cls).setUpClass()
        cls.option = 'contrail'

    @test.attr(type=['sanity', 'vcenter', 'suite1'])
    def test_sec_group_basic(self):
        super(SecurityGroupBasicRegressionTests1_contrail, self).test_sec_group_basic()

class SecurityGroupBasicRegressionTests1_contrail_vro(
        test_regression_basic.SecurityGroupBasicRegressionTests1):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1_contrail_vro, cls).setUpClass()
        cls.option = 'contrail'
    
    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.inputs.vro_based:
            return(False, 'Skipping Test Vro server not preset on vcenter setup')
        return (True, None)

    @test.attr(type=['vcenter','vro'])
    @set_attr('vro_based')
    def test_sec_group_basic(self):
        super(SecurityGroupBasicRegressionTests1_contrail_vro, self).test_sec_group_basic()



class SecurityGroupRegressionTests2_contrail(SecurityGroupRegressionTests2):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests2, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests3_contrail(SecurityGroupRegressionTests3):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests3, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests4_contrail(SecurityGroupRegressionTests4):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests4, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests5_contrail(SecurityGroupRegressionTests5):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests5, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests6_contrail(SecurityGroupRegressionTests6):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests6, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests7_contrail(SecurityGroupRegressionTests7):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests7, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests8_contrail(SecurityGroupRegressionTests8):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests8, cls).setUpClass()
        cls.option = 'contrail'


class SecurityGroupRegressionTests9_contrail(SecurityGroupRegressionTests9):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests9, cls).setUpClass()
        cls.option = 'contrail'

class SecurityGroupBasicRegressionTests1Ipv6(
        test_regression_basic.SecurityGroupBasicRegressionTests1):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

    @test.attr(type=['sanity','suite1'])
    def test_sec_group_basic(self):
        super(SecurityGroupBasicRegressionTests1Ipv6, self).test_sec_group_basic()

class SecurityGroupRegressionTests2Ipv6(SecurityGroupRegressionTests2):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests2Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)


class SecurityGroupRegressionTests3Ipv6(SecurityGroupRegressionTests3):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests3Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityGroupRegressionTests4Ipv6(SecurityGroupRegressionTests4):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests4Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityGroupRegressionTests5Ipv6(SecurityGroupRegressionTests5):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests5Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityGroupRegressionTests6Ipv6(SecurityGroupRegressionTests6):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests6Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityGroupRegressionTests7Ipv6(SecurityGroupRegressionTests7):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests7Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)


class SecurityGroupRegressionTests8Ipv6(SecurityGroupRegressionTests8):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests8Ipv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityGroupSynAckTestIpv6(SecurityGroupSynAckTest):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupSynAckTestIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
