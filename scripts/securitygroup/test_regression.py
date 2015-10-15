import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import BaseSGTest
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture,get_secgrp_id_from_name
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
sys.path.append(os.path.realpath('scripts/flow_tests'))
from tcutils.topo.sdn_topo_setup import *
import test
import sdn_sg_test_topo
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name
from base_traffic import *
from tcutils.util import skip_because

class SecurityGroupRegressionTests1(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests1, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @test.attr(type=['sanity','ci_sanity'])
    @preposttest_wrapper
    def test_sec_group_add_delete(self):
        """
	Description: Verify security group add delete
	Steps:
            1. Create custom security group with rule in it
            2. Delete custom security group
        Pass criteria: Step 1 and 2 should pass
        """
        rule = [{'direction': '>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_fix = self.config_sec_group(name='test_sec_group', entries=rule)
        self.delete_sec_group(secgrp_fix)
        return True

    @test.attr(type=['sanity','ci_sanity','vcenter'])
    @preposttest_wrapper
    def test_vm_with_sec_group(self):
        """
	Description: Verify attach dettach security group in VM
	Steps:
            1. Create VN with subnet
            2. Create security group with custom rules
            3. Launch VM in custom created security group and verify
            4. Remove secuity group association with VM
            5. Add back custom security group to VM and verify
            6. Try to delete security group with association to VM. It should fail.
        Pass criteria: Step 2,3,4,5 and 6 should pass
        """
        vn_name = "test_sec_vn"
        vn_net = ['11.1.1.0/24']
        vn = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn_name, inputs=self.inputs, subnets=vn_net))
        assert vn.verify_on_setup()

        secgrp_name = 'test_sec_group' + '_' + get_random_name()
        rule = [{'direction': '>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        secgrp = self.config_sec_group(name=secgrp_name, entries=rule)
	secgrp_id = secgrp.secgrp_id
        vm_name = "test_sec_vm"
	img_name = os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        vm = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn.obj, vm_name=vm_name, image_name=img_name, flavor='contrail_flavor_small',
            sg_ids=[secgrp_id]))
        assert vm.verify_on_setup()
        assert vm.wait_till_vm_is_up()
        result, msg = vm.verify_security_group(secgrp_name)
        assert result, msg

        self.logger.info("Remove security group %s from VM %s",
                         secgrp_name, vm_name)
        vm.remove_security_group(secgrp=secgrp_id)
        result, msg = vm.verify_security_group(secgrp_name)
        if result:
            assert False, "Security group %s is not removed from VM %s" % (secgrp_name,
                                                                           vm_name)

        import time
        time.sleep(4)
        vm.add_security_group(secgrp=secgrp_name)
        result, msg = vm.verify_security_group(secgrp_name)
        assert result, msg

        self.logger.info(
            "Try deleting the security group %s with back ref.", secgrp_name)
        try:
            if secgrp.option == 'openstack':
                secgrp.quantum_h.delete_security_group(secgrp.secgrp_id)
            else:
                secgrp.secgrp_fix.cleanUp()
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the security group with back ref as expected")
        else:
            try:
                secgroup = self.vnc_lib.security_group_read(
                    fq_name=secgrp.secgrp_fq_name)
                self.logger.info(
                    "Not able to delete the security group with back ref as expected")
            except NoIdError:
                errmsg = "Security group deleted, when it is attached to a VM."
                self.logger.error(errmsg)
                assert False, errmsg
        return True

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
        self.sg1_fix.replace_rules(rule)

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
        self.sg1_fix.replace_rules(rule)

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
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(port_test=True)
        return True

#end class SecurityGroupRegressionTests2

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
        self.sg1_fix.replace_rules(rule)

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
        self.sg1_fix.replace_rules(rule)

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
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp_port()
        return True

#end class SecurityGroupRegressionTests3

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
                password=self.project.password, compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)
        except (AttributeError,NameError):
            topo = topology_class_name(compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
	out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify_negative_cases(topo_obj, config_topo)
        return True
    #end test_vn_compute_sg_comb 

#end class SecurityGroupRegressionTests4

class SecurityGroupRegressionTests5(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests5, cls).setUpClass()
	cls.option = 'openstack'

    def setUp(self):
        super(SecurityGroupRegressionTests5, self).setUp()
        self.create_sg_test_resources()

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests2.")
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
        self.sg1_fix.replace_rules(rule)
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
        self.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(double_rule=True)
        return True
    #end test_sec_group_with_proto_double_rules_sg1

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

        #try to delete default sg
        secgrp_fq_name = ':'.join(['default-domain',
                                self.inputs.project_name,
                                'default'])
        sg_id = get_secgrp_id_from_name(
                        self.connections,
                        secgrp_fq_name)
        try:
            self.orch.delete_security_group(sg_id)
        except Exception, msg:
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

        #delete egress rule and add new rules and verify with traffic
        self.sg1_fix.delete_all_rules(sg_id)
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
        secgrp_rules = self.sg1_fix.create_sg_rule(sg_id,secgrp_rules=rule)
        assert secgrp_rules

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass')

        #revert back default sg
        self.sg1_fix.delete_all_rules(sg_id)
        rule = [{'direction': '<>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group':secgrp_fq_name}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_rules = self.sg1_fix.create_sg_rule(sg_id,secgrp_rules=rule)
        assert secgrp_rules

        return True
        #end test_default_sg

#end class SecurityGroupRegressionTests5

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
	topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo_sg_stateful(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,config_option=self.option)
        except (AttributeError,NameError):
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

	self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=False)
        return True
    #end test_sg_stateful 

    @preposttest_wrapper
    @skip_because(feature='multi-tenant')
    def test_sg_multiproject(self):
        """
	Description: Test SG across projects
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic
        Pass criteria: step 3 should pass
        """


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
        out = setup_obj.sdn_topo_setup(config_option=self.option)
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo_objs, config_topo, vm_fip_info = out['data']

        self.start_traffic_and_verify_multiproject(topo_objs, config_topo, traffic_reverse=False)

        return True
    #end test_sg_multiproject

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
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,config_option=self.option)
        except (AttributeError,NameError):
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

        self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=True)

        return True
        #end test_sg_no_rule

#end class SecurityGroupRegressionTests6

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
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,config_option=self.option)
        except (AttributeError,NameError):
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

        #Test SG rule, ingress-udp same SG, egress-all
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

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        #start traffic
        sender, receiver = self.start_traffic_scapy(src_vm_fix, dst_vm_fix, 'udp',
                                port, port,recvr=False)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)
        #stop traffic
        sent, recv = self.stop_traffic_scapy(sender, receiver,recvr=False)

        #Test with SG rule, ingress-egress-udp only
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
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        #start traffic
        sender, receiver = self.start_traffic_scapy(src_vm_fix, dst_vm_fix, 'udp',
                                port, port,recvr=False)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)
        #stop traffic
        sent, recv = self.stop_traffic_scapy(sender, receiver,recvr=False)

        #Test with SG rule, ingress-egress-all
        dst_vm_fix = config_topo['vm']['vm2']
        rule = [{'direction': '>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        #start traffic
        sender, receiver = self.start_traffic_scapy(src_vm_fix, dst_vm_fix, 'udp',
                                port, port,recvr=False)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)
        #stop traffic
        sent, recv = self.stop_traffic_scapy(sender, receiver,recvr=False)

        return True
    #end test_icmp_error_handling1

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
                compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)
        except (AttributeError,NameError):
            topo.build_topo2(compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        #Test with SG rule, egress-udp only
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

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        #start traffic
        sender, receiver = self.start_traffic_scapy(src_vm_fix, dst_vm_fix, 'udp',
                                port, port,recvr=False)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap)
        #stop traffic
        sent, recv = self.stop_traffic_scapy(sender, receiver,recvr=False)
        #Test ICMP error from agent
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
        vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn1_name, inputs=self.inputs, subnets=vn1_net))
        assert vn1_fixture.verify_on_setup()
        vn2_name = "test_vnv6dn"
        vn2_net = ['2001::201:0/120']
        #vn2_fixture = self.config_vn(vn2_name, vn2_net)
        vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn2_name, inputs=self.inputs, subnets=vn2_net))
        assert vn2_fixture.verify_on_setup()
        vm1_name = 'source_vm'
        vm2_name = 'dest_vm'
        #vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        #vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn1_fixture.obj, vm_name=vm1_name, node_name=None, 
            image_name='ubuntu-traffic', flavor='contrail_flavor_small'))

        vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn2_fixture.obj, vm_name=vm2_name, node_name=None, 
            image_name='ubuntu-traffic', flavor='contrail_flavor_small'))
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
        self.logger.info("Increasing MTU on src VM and ping with bigger size and reverting MTU")
        cmd_ping = ('ping -M want -s 2500 -c 10 %s | grep \"Frag needed and DF set\"' %
                     (dst_vm_fix.vm_ip))
#        cmd_tcpdump = 'tcpdump -vvv -c 5 -ni eth0 -v icmp > /tmp/op1.log'
        gw = src_vm_fix.vm_ip
        gw = gw.split('.')
        gw[-1] = '1'
        gw = '.'.join(gw)
        filters = 'icmp'
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        cmds = ['ifconfig eth0 mtu 3000', cmd_ping,
                  'ifconfig eth0 mtu 1500']
        output = src_vm_fix.run_cmd_on_vm(cmds=cmds, as_sudo=True, as_daemon=True)
        cmd = 'tcpdump -r %s' % pcap
        cmd_check_icmp, err = execute_cmd_out(session, cmd, self.logger)
        cmd_df = re.search('need to frag', cmd_check_icmp)
        self.logger.debug("output for ping cmd: %s" % output[cmd_ping])
        cmd_next_icmp = re.search('.+ seq 2, length (\d\d\d\d).*', cmd_check_icmp)
        icmpmatch = ("%s > %s: ICMP %s unreachable - need to frag" %
                     (gw, src_vm_fix.vm_ip, dst_vm_fix.vm_ip))
        if not ((icmpmatch in cmd_check_icmp) and ("need to frag" in cmd_df.group(0))
                  and (cmd_next_icmp.group(1) < '1500')
                  and ("Frag needed and DF set" in output[cmd_ping])):
            self.logger.error("expected ICMP error for type 3 code 4 not found")
            stop_tcpdump_for_vm_intf(self, session, pcap)
            return False
        stop_tcpdump_for_vm_intf(self, session, pcap)
        self.logger.info("increasing MTU on src VM and ping6 with bigger size and reverting MTU")
        cmd_ping = 'ping6 -s 2500 -c 10 %s | grep \"Packet too big\"' % (vm2_fixture.vm_ip)

        if self.option == 'openstack':
            src_vn_fq_name = vn1_fixture.vn_fq_name
#            dst_vn_fq_name = vn2_fixture.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(vn1_fixture._obj.get_fq_name())
#            dst_vn_fq_name = ':'.join(vn2_fixture._obj.get_fq_name())
#        cmd_tcpdump = 'tcpdump -vvv -c 5 -ni eth0 -v icmp6 > /tmp/op.log'
        gw = vm1_fixture.vm_ip
        gw = gw.split(':')
        gw[-1] = '1'
        gw = ':'.join(gw)
        filters = 'icmp6'
        session, pcap = start_tcpdump_for_vm_intf(self, vm1_fixture, src_vn_fq_name, filters = filters)
        cmds = ['ifconfig eth0 mtu 3000', cmd_ping,
                 'ifconfig eth0 mtu 1500']
        output = vm1_fixture.run_cmd_on_vm(cmds=cmds, as_sudo=True, as_daemon=True)
        cmd = 'tcpdump -r %s' % pcap
        cmd_check_icmp, err = execute_cmd_out(session, cmd, self.logger)
        self.logger.debug("output for ping cmd: %s" % output[cmd_ping])
        cmd_next_icmp = re.search('.+ ICMP6, packet too big, mtu (\d\d\d\d).*', cmd_check_icmp)
        icmpmatch = ("ICMP6, packet too big")
        if not ((icmpmatch in cmd_check_icmp) and (cmd_next_icmp.group(1) < '1500')
                 and ("Packet too big" in output[cmd_ping])):
            self.logger.error("expected ICMP6 error for type 2 packet too big message not found")
            stop_tcpdump_for_vm_intf(self, session, pcap)
#            output = vm1_fixture.run_cmd_on_vm(cmds='rm /tmp/op.log', as_sudo=True)
            return False
        stop_tcpdump_for_vm_intf(self, session, pcap)

        return True
        #end test_icmp_error_handling2

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


        if ('MX_GW_TEST' not in os.environ) or (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') != '1')):
            self.logger.info(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            return True

        public_vn_info = {'subnet':[self.inputs.fip_pool], 'router_asn':self.inputs.router_asn, 'rt_number':self.inputs.mx_rt}
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
                public_vn_info=public_vn_info,config_option=self.option)
        except (AttributeError,NameError):
            topo.build_topo(public_vn_info=public_vn_info,config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(skip_verify='no',config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        pol_fix = config_topo['policy'][topo_obj.policy_list[0]]
        if self.option == 'openstack':
            policy_id = pol_fix.policy_obj['policy']['id']
            new_policy_entries = config_topo['policy'][topo_obj.policy_list[1]].policy_obj['policy']['entries']
            data = {'policy': {'entries': new_policy_entries}}
            pol_fix.update_policy(policy_id, data)
        else:
            policy_name = topo_obj.policy_list[0]
            proj_obj = pol_fix._conn_drv.project_read(['default-domain',self.project.project_name])
            new_policy_entries = pol_fix._conn_drv.network_policy_read(['default-domain',
                                                                       self.project.project_name,
                                                                       topo_obj.policy_list[1]]).network_policy_entries
            net_policy_obj = NetworkPolicy(
                                policy_name, network_policy_entries=new_policy_entries,
                                parent_obj=proj_obj)
            pol_fix._conn_drv.network_policy_update(net_policy_obj)

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
        host_compute = {'username': self.inputs.username, 'password': self.inputs.password, 'ip': src_vm_fix.vm_node_ip}
        copy_file_to_server(host_compute,path, '/tmp',pkg)

        self.logger.info("copying traceroute from compute node to VM")
        with settings(host_string='%s@%s' % (self.inputs.username, src_vm_fix.vm_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            path = '/tmp/' + pkg
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (src_vm_fix.vm_username,
                 src_vm_fix.local_ip),
                password=src_vm_fix.vm_password,
                src=path,
                dest='/tmp')

        self.logger.info("installing traceroute")
        cmd = 'dpkg -i /tmp/' + pkg
        output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert "Setting up traceroute" in output_cmd_dict[cmd], "traceroute pkg installation error, output:%s" % output_cmd_dict[cmd]

        self.logger.info("starting tcpdump on src VM")
        filters = '\'(icmp[0]=11 and icmp[1]=0)\''
        session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)

        self.logger.info("starting traceroute to out of cluster, 8.8.8.8")
        cmd = 'traceroute 8.8.8.8'
        for i in range(0,4):
            output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
            self.logger.info(output_cmd_dict[cmd])

            if verify_tcpdump_count(self, session, pcap):
                return True

        return False
        #end test_icmp_error_handling_from_mx_with_si

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
                compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)
        except (AttributeError,NameError):
            topo.build_topo2(compute_node_list=self.connections.orch.get_hosts(),config_option=self.option)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        #Test with SG rule, egress-udp only and also send diff ICMP error with diff payload
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

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3)\'' 
        session1, pcap1 = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
        #start traffic
        sender1, receiver1 = self.start_traffic_scapy(src_vm_fix, dst_vm_fix, 'udp',
                                port, port,recvr=False)

        icmp_code = 0
        for icmp_type in xrange(0,3):
                #start tcpdump on src VM
                filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (icmp_type, icmp_code)
                session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=icmp_code,count=pkt_cnt)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count is ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
	        #verify packet count and stop tcpdump
                assert verify_tcpdump_count(self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        #type 3 , code (0,3)
        icmp_type = 3
        for icmp_code in xrange(0,3):
                #start tcpdump on src VM
                filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (icmp_type, icmp_code)
                session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=icmp_code,count=pkt_cnt)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count is ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                #verify packet count and stop tcpdump
                assert verify_tcpdump_count(self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        #type 3 , code (4,15)
        icmp_type = 3
        for icmp_code in xrange(4,16):
                #start tcpdump on src VM
                filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (icmp_type, icmp_code)
                session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=icmp_code,count=pkt_cnt)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count is ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                #verify packet count and stop tcpdump
                assert verify_tcpdump_count(self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        #type (4,11), code 0
        icmp_code = 0
        for icmp_type in xrange(4,12):
                #start tcpdump on src VM
                filters = '\'(icmp[0] = %s and icmp[1] = %s)\'' % (icmp_type, icmp_code)
                session, pcap = start_tcpdump_for_vm_intf(self, src_vm_fix, src_vn_fq_name, filters = filters)
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=icmp_code,count=pkt_cnt)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count is ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                #verify packet count and stop tcpdump
                assert verify_tcpdump_count(self, session, pcap, exp_count=0), "pkt count in tcpdump is not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session1, pcap1)
        #stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1,recvr=False)
        return True
        #end test_icmp_error_payload_matching

#end class SecurityGroupRegressionTests7

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
        topo = topology_class_name()
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
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        'default']))

        # test with default SG
        traffic_obj = BaseTraffic.factory(proto=proto)
        assert traffic_obj
        assert traffic_obj.start(src_vm_fix, dst_vm_fix,
                              proto, port, port)

        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            default_secgrp_id,
            proto,
            port)
        sent, recv = traffic_obj.stop()

        # test with user-defined SG
        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        src_vm_fix.remove_security_group(secgrp=default_secgrp_id)
        dst_vm_fix.remove_security_group(secgrp=default_secgrp_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        traffic_obj = BaseTraffic.factory(proto=proto)
        assert traffic_obj
        assert traffic_obj.start(src_vm_fix, dst_vm_fix,
                              proto, port, port)
     

        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            secgrp_id,
            proto,
            port)
        sent, recv = traffic_obj.stop()

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
        topo = topology_class_name()
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
        traffic_obj_udp = BaseTraffic.factory(proto='udp')
        assert traffic_obj_udp
        assert traffic_obj_udp.start(src_vm_fix, dst_vm_fix,
                              'udp', port, port)
        traffic_obj_tcp = BaseTraffic.factory(proto='tcp')
        assert traffic_obj_tcp
        assert traffic_obj_tcp.start(src_vm_fix, dst_vm_fix,
                              'tcp', port, port)
        sender_icmp, receiver_icmp = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'icmp', port, port, payload="payload")

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
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
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

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
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        assert self.verify_flow_to_sg_rule_mapping(
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix,
            secgrp_id,
            'icmp',
            port)

        # stop traffic
        sent, recv = traffic_obj_udp.stop()
        sent, recv = traffic_obj_tcp.stop()
        sent, recv = self.stop_traffic_scapy(sender_icmp, receiver_icmp)

        return True
    #end test_flow_to_sg_rule_mapping_multiple_rules

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
        topo = topology_class_name()
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
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        src_sg_name]))
        # start traffic
        traffic_obj = BaseTraffic.factory(proto=proto)
        assert traffic_obj
        assert traffic_obj.start(src_vm_fix, dst_vm_fix,
                              proto, port, port)

        # get the egress rule uuid
        rule_uuid = None
        rules = list_sg_rules(self.connections, secgrp_id)
        for rule in rules:
            if rule['direction'] == 'egress' and (rule['ethertype'] == 'IPv4' or \
                        rule['remote_ip_prefix'] == '0.0.0.0/0') and \
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
                                    ':'.join([self.inputs.domain_name,
                                            self.inputs.project_name,
                                            dst_sg_name]))

            # get the ingress rule uuid
            rule_uuid = None
            rules = list_sg_rules(self.connections, secgrp_id)
            for rule in rules:
                if rule['direction'] == 'ingress' and \
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

        # stop traffic
        sent, recv = traffic_obj.stop()
        assert test_result

        return True

    #end test_flow_to_sg_rule_mapping_intra_vn

    @preposttest_wrapper
    def test_verify_sg_rule_uuid_in_control_api(self):
        """
        1. Verify uuid for each sg rule in api/control introspect and neutron cli"""

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

        rule = [{'direction': '>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 'ethertype': 'IPv4'
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 'ethertype': 'IPv4'
                 }]
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
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

            # get the egress and ingress rule uuid
            egress_ipv4_id = None
            egress_ipv6_id = None
            ingress_ipv4_id = None
            ingress_ipv6_id = None
            rules = list_sg_rules(self.connections, secgrp_id)
            for rule in rules:
                if rule['direction'] == 'egress' and rule['ethertype'] == 'IPv4':
                    egress_ipv4_id = rule['id']
                elif rule['direction'] == 'ingress' and rule['ethertype'] == 'IPv4':
                    ingress_ipv4_id = rule['id']
                elif rule['direction'] == 'ingress' and rule['ethertype'] == 'IPv6':
                    ingress_ipv6_id = rule['id']
                elif rule['direction'] == 'egress' and rule['ethertype'] == 'IPv6':
                    egress_ipv6_id = rule['id']


            assert egress_ipv4_id, "Egress rule id could not be found"
            assert ingress_ipv4_id, "Ingress rule id could not be found"

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
                if rule['src_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv4':
                    uuid_egress_ipv4 = rule['rule_uuid']
                elif rule['dst_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv4':
                    uuid_ingress_ipv4 = rule['rule_uuid']
                elif rule['src_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv6':
                    uuid_egress_ipv6 = rule['rule_uuid']
                elif rule['dst_addresses'][0]['security_group'] == "local" and rule['ethertype'] == 'IPv6':
                    uuid_ingress_ipv6 = rule['rule_uuid']

            assert uuid_egress_ipv4 == egress_ipv4_id, "egress IPv4 rule uuid is not same in API and \
                                                        neutron for SG:%s" % (sg_name)
            assert uuid_ingress_ipv4 == ingress_ipv4_id, "ingress IPv4 rule uuid is not same in API \
                                                        and neutron for SG:%s" % (sg_name)

            if ingress_ipv6_id:
                assert ingress_ipv6_id == uuid_ingress_ipv6, "ingress IPv6 rule uuid is not same in API \
                                                        and neutron for SG:%s" % (sg_name)
            if egress_ipv6_id:
                assert egress_ipv6_id == uuid_egress_ipv6, "egress IPv6 rule uuid is not same in API \
                                                        and neutron for SG:%s" % (sg_name)


            self.logger.info("%s security group rule uuid matches in API with neutron" % (sg_name))
            # get SG rule uuid from control node and match with neutron uuid
            for cn in self.inputs.bgp_ips:
                uuid_egress_ipv4 = None
                uuid_ingress_ipv4 = None
                cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp(
                    project=prj_name,
                    secgrp=sg_name)
                for rule in cn_secgrp_obj['obj_info'][0]['data']['security-group-entries']:
                    if rule['src-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv4':
                        uuid_egress_ipv4 = rule['rule-uuid']
                    elif rule['dst-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv4':
                        uuid_ingress_ipv4 = rule['rule-uuid']
                    elif rule['src-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv6':
                        uuid_egress_ipv6 = rule['rule-uuid']
                    elif rule['dst-addresses']['security-group'] == 'local' and rule['ethertype'] == 'IPv6':
                        uuid_ingress_ipv6 = rule['rule-uuid']

                assert uuid_egress_ipv4 == egress_ipv4_id, "egress rule uuid are not same in control \
                                                        and neutron for SG:%s" % (sg_name)
                assert uuid_ingress_ipv4 == ingress_ipv4_id, "ingress rule uuid are not same in control \
                                                        and neutron for SG:%s" % (sg_name)
                if ingress_ipv6_id:
                    assert ingress_ipv6_id == uuid_ingress_ipv6, "ingress IPv6 rule uuid is not same in control \
                                                        and neutron for SG:%s" % (sg_name)
                if egress_ipv6_id:
                    assert egress_ipv6_id == uuid_egress_ipv6, "egress IPv6 rule uuid is not same in control \
                                                        and neutron for SG:%s" % (sg_name)

            self.logger.info("%s security group rule uuid matches in control with neutron" % (sg_name))

        return True
        # end test_verify_sg_rule_uuid_in_control_api

#end class SecurityGroupRegressionTests8

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
        topo_obj, config_topo = self.create_topo_setup(topology_class_name, "build_topo")

        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]

        sg_name = 'default'
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        filters1 = '\'(udp and src host %s and dst host %s)\'' % (
            src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        filters2 = '\'(tcp and src host %s and dst host %s)\'' % (
            dst_vm_fix.vm_ip, src_vm_fix.vm_ip)

        sender1, receiver1 = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'udp', port, port, payload="payload")
        sender2, receiver2 = self.start_traffic_scapy(
            dst_vm_fix, src_vm_fix, 'tcp', port, port, payload="payload")

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        src_vm_fix.remove_security_group(secgrp=secgrp_id)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1,
                             src_exp_count=0, dst_exp_count=0)

        src_vm_fix.add_security_group(secgrp=secgrp_id)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        # stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1)
        sent, recv = self.stop_traffic_scapy(sender2, receiver2)

        return True
        # end test_add_remove_default_sg_active_flow

    @preposttest_wrapper
    def test_add_remove_sg_active_flow1(self):
        """ add/remove SG from VM when flow is active
        1.Traffic from both ends
        2.Test for SG with rule with remote as sg for both ingress-egress"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()
        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
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

        sender1, receiver1 = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'udp', port, port, payload="payload")

        sender2, receiver2 = self.start_traffic_scapy(
            dst_vm_fix, src_vm_fix, 'udp', port, port, payload="payload")

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        src_vm_fix.add_security_group(secgrp=sg_allow_all)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1,
                             src_exp_count=0, dst_exp_count=0)

        # stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1)
        sent, recv = self.stop_traffic_scapy(sender2, receiver2)
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow1

    @preposttest_wrapper
    def test_add_remove_sg_active_flow2(self):
        """ add/remove SG from VM when flow is active
        1.Traffic from both ends
        2.Test for SG with egress cidr rule,ingress sg"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()

        port = 10000
        port2 = 11000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # start the traffic from src VM
        sender1, receiver1 = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'udp', port, port, payload="payload")
        # start the traffic from dst VM
        sender2, receiver2 = self.start_traffic_scapy(
            dst_vm_fix, src_vm_fix, 'udp', port2, port2, payload="payload")

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

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        src_vm_fix.add_security_group(secgrp=sg_allow_all)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1,
                             dst_exp_count=0)

        # stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1)
        sent, recv = self.stop_traffic_scapy(sender2, receiver2)
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow2

    @preposttest_wrapper
    def test_add_remove_sg_active_flow3(self):
        """ add/remove SG from VM when flow is active
        1. Traffic from both ends
        2. Test for SG with ingress cidr and egress sg"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(topology_class_name, "build_topo")

        sg_allow_all = self.create_sec_group_allow_all()
        port = 10000
        port2 = 11000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]

        sg_name = topo_obj.sg_list[0]
        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # start the traffic from src VM
        sender1, receiver1 = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'udp', port, port, payload="payload")
        # start the traffic from dst VM
        sender2, receiver2 = self.start_traffic_scapy(
            dst_vm_fix, src_vm_fix, 'udp', port2, port2, payload="payload")

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

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        src_vm_fix.add_security_group(secgrp=sg_allow_all)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1,
                             src_exp_count=0)

        # stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1)
        sent, recv = self.stop_traffic_scapy(sender2, receiver2)
        src_vm_fix.remove_security_group(secgrp=sg_allow_all)

        return True
        # end test_add_remove_sg_active_flow3

    @preposttest_wrapper
    def test_add_remove_sg_active_flow4(self):
        """ add/remove SG from VM when flow is active
        1. Traffic from both ends
        2. Test for SG with cidr both ingress-egress"""

        topology_class_name = sdn_sg_test_topo.sdn_topo_flow_to_sg_rule_mapping
        topo_obj, config_topo = self.create_topo_setup(topology_class_name, "build_topo")

        port = 10000
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
        dst_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[dst_vm_name]]
        sg_name = topo_obj.sg_list[0]

        secgrp_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        sg_name]))

        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        'default']))

        src_vm_fix.remove_security_group(secgrp=default_sg_id)
        dst_vm_fix.remove_security_group(secgrp=default_sg_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)
        dst_vm_fix.add_security_group(secgrp=secgrp_id)

        # start the traffic from src VM
        sender1, receiver1 = self.start_traffic_scapy(
            src_vm_fix, dst_vm_fix, 'udp', port, port, payload="payload")
        # start the traffic from dst VM
        sender2, receiver2 = self.start_traffic_scapy(
            dst_vm_fix, src_vm_fix, 'udp', port, port, payload="payload")

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

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        src_vm_fix.remove_security_group(secgrp=secgrp_id)
        src_vm_fix.add_security_group(secgrp=secgrp_id)

        assert self.verify_traffic_on_vms(src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             filters2, filters1)

        # stop traffic
        sent, recv = self.stop_traffic_scapy(sender1, receiver1)
        sent, recv = self.stop_traffic_scapy(sender2, receiver2)

        return True
        # end test_add_remove_sg_active_flow4

#end class SecurityGroupRegressionTests9

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

        topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.inputs.compute_ips)
        except (AttributeError,NameError):
            topo.build_topo2(compute_node_list=self.inputs.compute_ips)

        topo.sg_rules[topo.sg_list[0]] = [
                {'direction': '>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0',
                                    'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        topo.sg_rules[topo.sg_list[1]] = [
                {'direction': '>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0',
                                    'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                'protocol': 'any',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0',
                                    'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

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

        self.logger.info("copying syn client to the compute node.")
        path = os.getcwd() + '/tcutils/pkgs/syn_ack_test/' + pkg
        host_compute = {
          'username': self.inputs.host_data[src_vm_fix.vm_node_ip]['username'],
          'password': self.inputs.host_data[src_vm_fix.vm_node_ip]['password'],
          'ip': src_vm_fix.vm_node_ip}
        copy_file_to_server(host_compute, path, '/tmp', pkg)

        self.logger.info("copying syn client from compute node to VM")
        with settings(host_string='%s@%s' % (self.inputs.username,
                                            src_vm_fix.vm_node_ip),
                      password=self.inputs.password, warn_only=True,
                      abort_on_prompts=False):
            path = '/tmp/' + pkg
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (src_vm_fix.vm_username,
                 src_vm_fix.local_ip),
                password=src_vm_fix.vm_password,
                src=path,
                dest='/tmp')

        pkg = 'syn_server.py'
        self.logger.info("copying syn server to the compute node.")
        path = os.getcwd() + '/tcutils/pkgs/syn_ack_test/' + pkg
        host_compute = {
            'username': self.inputs.username,
            'password': self.inputs.password,
            'ip': dst_vm_fix.vm_node_ip}
        copy_file_to_server(host_compute, path, '/tmp', pkg)

        self.logger.info("copying syn server from compute node to VM")
        with settings(host_string='%s@%s' % (self.inputs.username,
                                            dst_vm_fix.vm_node_ip),
                      password=self.inputs.password, warn_only=True,
                      abort_on_prompts=False):
            path = '/tmp/' + pkg
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (dst_vm_fix.vm_username,
                 dst_vm_fix.local_ip),
                password=dst_vm_fix.vm_password,
                src=path,
                dest='/tmp')

        cmd1 = 'chmod +x /tmp/syn_server.py;/tmp/syn_server.py %s %s \
                    2>/tmp/server.log 1>/tmp/server.log' \
                    % (src_vm_fix.vm_ip, dst_vm_fix.vm_ip)
        cmd2 = 'chmod +x /tmp/syn_client.py;/tmp/syn_client.py %s %s \
                    2>/tmp/client.log 1>/tmp/client.log' \
                    % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        output_cmd_dict = dst_vm_fix.run_cmd_on_vm(cmds=[cmd1],
                                        as_sudo=True, as_daemon=True)
        output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd2],
                                        as_sudo=True, as_daemon=True)

        sleep(1)
        #verify flow created
        inspect_h1 = self.agent_inspect[src_vm_fix.vm_node_ip]
        flow_rec1 = None
        sport = '8100'
        dport = '8000'
        vn_fq_name=src_vm_fix.vn_fq_name
        flow_timeout = 180

        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=src_vm_fix.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=src_vm_fix.vm_ip,
            dip=dst_vm_fix.vm_ip,
            sport=sport,
            dport=dport,
            protocol='6')
        assert flow_rec1
        #wait for flow to expire
        sleep(flow_timeout+2)

        #verify flow created again
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
    #end test_syn_ack_create_flow

# end class SecurityGroupSynAckTest 


#creating new classes to run all tests with contrail apis
class SecurityGroupRegressionTests1_contrail(SecurityGroupRegressionTests1):
    @classmethod
    def setUpClass(cls):
        super(SecurityGroupRegressionTests1, cls).setUpClass()
        cls.option = 'contrail'
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

