#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import tcutils.wrappers
from base import BasePolicyTest
import time
from vn_test import VNFixture
from vm_test import VMFixture
from ipam_test import IPAMFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from test import attr
from netaddr import IPNetwork
from common.policy import policy_test_utils

af_test = 'dual'

class TestPolicyAcl(BasePolicyTest):

    @classmethod
    def setUpClass(cls):
        super(TestPolicyAcl, cls).setUpClass()

    def cleanUp(cls):
        super(TestPolicyAcl, cls).cleanUp()
    # end cleanUp

    def setup_ipam_vn(self):
        # create new IPAM
        self.ipam1_obj = self.useFixture(
            IPAMFixture(
                project_obj=self.project,
                name='ipam1'))

        self.ipam2_obj = self.useFixture(
            IPAMFixture(
                project_obj=self.project,
                name='ipam2'))

        self.ipam3_obj = self.useFixture(
            IPAMFixture(
                project_obj=self.project,
                name='ipam3'))

        # create new VN
        self.VN1_fixture = self.useFixture(
            VNFixture(
                project_name=self.project.project_name,
                connections=self.connections,
                vn_name='VN1',
                inputs=self.inputs,
                subnets=['10.1.1.0/24'],
                ipam_fq_name=self.ipam1_obj.fq_name))

        self.VN2_fixture = self.useFixture(
            VNFixture(
                project_name=self.project.project_name,
                connections=self.connections,
                vn_name='VN2',
                inputs=self.inputs,
                subnets=['10.2.1.0/24'],
                ipam_fq_name=self.ipam2_obj.fq_name))

        self.VN3_fixture = self.useFixture(
            VNFixture(
                project_name=self.project.project_name,
                connections=self.connections,
                vn_name='VN3',
                inputs=self.inputs,
                subnets=['10.3.1.0/24'],
                ipam_fq_name=self.ipam3_obj.fq_name))

    # end setup_ipam_vn

    def setup_vm(self):
        # add VMs to VNs
        self.VM11_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN1_fixture.obj,
                vm_name='VM11',
                project_name=self.project.project_name))

        self.VM21_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN2_fixture.obj,
                vm_name='VM21',
                project_name=self.project.project_name))

        self.VM31_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN3_fixture.obj,
                vm_name='VM31',
                project_name=self.project.project_name))

        self.VM11_fixture.wait_till_vm_is_up()
        self.VM21_fixture.wait_till_vm_is_up()
        self.VM31_fixture.wait_till_vm_is_up()
    
    # end setup_vm

    @attr(type=['sanity', 'vcenter'])
    @tcutils.wrappers.preposttest_wrapper
    def test_policy_inheritance_src_vn_dst_pol(self):
        """Test cases to test policy inheritance"""
        """Policy Rule :- source = VN, destination = policy."""
        result = True

        # create Ipam and VN
        self.setup_ipam_vn()

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_policy': 'policy13',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy13'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'}]

        policy13_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy12_fixture.policy_obj, \
                            policy13_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12','policy13'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            self.logger.info("Test with src as VN and dst as policy PASSED")
        else:
            result = False
            self.logger.error("Test with src as VN and dst as policy FAILED")

        return result

    # end test_policy_inheritance_src_vn_dst_pol

    @tcutils.wrappers.preposttest_wrapper
    def test_policy_inheritance_src_pol_dst_vn(self):
        """Test cases to test policy inheritance"""
        """Policy Rule :- source = policy, destination = VN."""
        result = True

        # create Ipam and VN
        self.setup_ipam_vn()

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'VN2',
                  'source_policy': 'policy13',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy13'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'}]

        policy13_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy12_fixture.policy_obj, \
                            policy13_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12','policy13'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : \
                           [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            self.logger.info("Test with src as policy and dst as VN PASSED")
        else:
            result = False
            self.logger.error("Test with src as policy and dst as VN FAILED")

        return result

    # end test_policy_inheritance_src_pol_dst_vn

    @tcutils.wrappers.preposttest_wrapper
    def test_policy_inheritance_src_any_dst_pol(self):
        """Test cases to test policy inheritance"""
        """Policy Rule :- source = Any, destination = policy."""
        result = True

        # create Ipam and VN
        self.setup_ipam_vn()

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_policy': 'policy13',
                  'source_network': 'any',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy13'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'}]

        policy13_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy12_fixture.policy_obj, \
                            policy13_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12','policy13'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : \
                           [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            self.logger.info("Test with src as any and dst as policy PASSED")
        else:
            result = False
            self.logger.error("Test with src as any and dst as policy FAILED")

        return result

    # end test_policy_inheritance_src_any_dst_pol

    @attr(type=['sanity', 'vcenter'])
    @tcutils.wrappers.preposttest_wrapper
    def test_policy_inheritance_src_pol_dst_any(self):
        """Test cases to test policy inheritance"""
        """Policy Rule :- source = policy, destination = Any."""
        result = True

        # create Ipam and VN
        self.setup_ipam_vn()

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'any',
                  'source_policy': 'policy13',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy13'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'}]

        policy13_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy12_fixture.policy_obj, \
                            policy13_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12','policy13'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : \
                           [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            self.logger.info("Test with src as policy and dst as any PASSED")
        else:
            result = False
            self.logger.error("Test with src as policy and dst as any FAILED")

        return result

    # end test_policy_inheritance_src_pol_dst_any 

    @tcutils.wrappers.preposttest_wrapper
    def test_policy_cidr_src_policy_dst_cidr(self):
        """Test cases to test policy CIDR"""
        """Policy Rule :- source = Policy, destination = CIDR."""
        result = True
        af = self.inputs.get_af()

        # create Ipam and VN
        self.setup_ipam_vn()
        VN2_subnet_v4 = self.VN2_fixture.get_cidrs(af='v4')[0]
        if 'v6' == af or 'dual' == af:
            VN2_subnet_v6 = self.VN2_fixture.get_cidrs(af='v6')[0]
        else:
            VN2_subnet_v6 = None

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN2_subnet_v4,
                  'source_policy': 'policy13',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN2_subnet_v4:VN2_subnet_v6})

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_policy': 'policy13',
                  'source_subnet': VN2_subnet_v4,
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN2_subnet_v4:VN2_subnet_v6})

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy13'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'}]

        policy13_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy12_fixture.policy_obj, \
                            policy13_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12','policy13'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM21_fixture)
        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                   self.VM11_fixture.vm_ip, self.VM21_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)\|Action:D(OutPolicy)'"
            cmd = cmd + " | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info("Found %s matching flows" % flow_record)
                self.logger.info("Test with src as policy and dst as cidr PASSED")
            else:
                result = False
                self.logger.error("Test with src as policy and dst as cidr FAILED")
        else:
            result = False
            self.logger.error("Test with src as policy and dst as cidr FAILED")

        return result

    # end test_policy_cidr_src_policy_dst_cidr

    @attr(type=['sanity', 'vcenter'])
    @tcutils.wrappers.preposttest_wrapper
    def test_policy_cidr_src_vn_dst_cidr(self):
        """Test cases to test policy CIDR"""
        """Policy Rule :- source = VN, destination = CIDR."""
        result = True
        af = self.inputs.get_af()

        # create Ipam and VN
        self.setup_ipam_vn()
        VN1_subnet_v4 = self.VN1_fixture.get_cidrs(af='v4')[0]
        VN2_subnet_v4 = self.VN2_fixture.get_cidrs(af='v4')[0]
        if 'v6' == af or 'dual' == af:
            VN1_subnet_v6 = self.VN1_fixture.get_cidrs(af='v6')[0]
            VN2_subnet_v6 = self.VN2_fixture.get_cidrs(af='v6')[0]
        else:
            VN1_subnet_v6 = None
            VN2_subnet_v6 = None

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN2_subnet_v4,
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN2_subnet_v4:VN2_subnet_v6})

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN1_subnet_v4,
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN1_subnet_v4:VN1_subnet_v6})

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : [policy12_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                   self.VM11_fixture.vm_ip, self.VM21_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info("Test with src as VN and dst as cidr PASSED")
            else:
                result = False
                self.logger.error("Test with src as VN and dst as cidr FAILED")
        else:
            result = False
            self.logger.error("Test with src as VN and dst as policy FAILED")

        return result

    # end test_policy_cidr_src_vn_dst_cidr

    @tcutils.wrappers.preposttest_wrapper
    def test_policy_cidr_src_duplicate_vn_dst_cidr(self):
        """Test cases to test policy CIDR"""
        """Policy Rule1 :- source = VN-A, destination = CIDR-A."""
        """Policy Rule2 :- source = VN-A, destination = CIDR-B."""
        result = True
        af = self.inputs.get_af()

        # create Ipam and VN
        self.setup_ipam_vn()
        VN1_subnet_v4 = self.VN1_fixture.get_cidrs(af='v4')[0]
        VN2_subnet_v4 = self.VN2_fixture.get_cidrs(af='v4')[0]
        VN3_subnet_v4 = self.VN3_fixture.get_cidrs(af='v4')[0]
        if 'v6' == af or 'dual' == af:
            VN1_subnet_v6 = self.VN1_fixture.get_cidrs(af='v6')[0]
            VN2_subnet_v6 = self.VN2_fixture.get_cidrs(af='v6')[0]
            VN3_subnet_v6 = self.VN3_fixture.get_cidrs(af='v6')[0]
        else:
            VN1_subnet_v6 = None
            VN2_subnet_v6 = None
            VN3_subnet_v6 = None

        # create policy
        policy_name = 'policy123'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN2_subnet_v4,
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN3_subnet_v4,
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN3',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN2_subnet_v4:VN2_subnet_v6,
                                         VN3_subnet_v4:VN3_subnet_v6})

        policy123_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN1_subnet_v4,
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN1_subnet_v4:VN1_subnet_v6})

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy31'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN1_subnet_v4,
                  'source_network': 'VN3',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN3',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN1_subnet_v4:VN1_subnet_v6})

        policy31_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : [policy123_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy123'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        VN3_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN3_fixture.vn_name,
                policy_obj={self.VN3_fixture.vn_name : [policy31_fixture.policy_obj]},
                vn_obj={self.VN3_fixture.vn_name : self.VN3_fixture},
                vn_policys=['policy31'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM21_fixture)

        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                   self.VM11_fixture.vm_ip, self.VM21_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info("Test with src as VN and dst as cidr PASSED")
            else:
                result = False
                self.logger.error("Test with src as VN and dst as cidr FAILED")
        else:
            result = False
            self.logger.error("Test with src as VN and dst as policy FAILED")

        ret = False
        flow_record = 0
        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM31_fixture)

        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                   self.VM11_fixture.vm_ip, self.VM31_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info("Test with src as VN and dst as cidr PASSED")
            else:
                result = False
                self.logger.error("Test with src as VN and dst as cidr FAILED")

        return result

    # end test_policy_cidr_src_duplicate_vn_dst_cidr

    @attr(type=['sanity', 'vcenter'])
    @tcutils.wrappers.preposttest_wrapper
    def test_policy_cidr_src_cidr_dst_any(self):
        """Test cases to test policy CIDR"""
        """Policy Rule :- source = CIDR, destination = ANY."""
        """Policy Rule :- source = ANY, destination = CIDR."""
        result = True
        af = self.inputs.get_af()

        # create Ipam and VN
        self.setup_ipam_vn()
        VN1_subnet_v4 = self.VN1_fixture.get_cidrs(af='v4')[0]
        VN2_subnet_v4 = self.VN2_fixture.get_cidrs(af='v4')[0]
        if 'v6' == af or 'dual' == af:
            VN1_subnet_v6 = self.VN1_fixture.get_cidrs(af='v6')[0]
            VN2_subnet_v6 = self.VN2_fixture.get_cidrs(af='v6')[0]
        else:
            VN1_subnet_v6 = None
            VN2_subnet_v6 = None

        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'any',
                  'source_subnet': VN1_subnet_v4,
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN1_subnet_v4:VN1_subnet_v6})

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy21'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN1_subnet_v4,
                  'source_network': 'any',
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                        {VN1_subnet_v4:VN1_subnet_v6})

        policy21_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : [policy12_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy21_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy21'],
                project_name=self.project.project_name))

        # create VM
        self.setup_vm()

        ret1 = self.VM11_fixture.ping_with_certainty(expectation=False,
                                     dst_vm_fixture=self.VM21_fixture)

        ret2 = self.VM21_fixture.ping_with_certainty(expectation=False,
                                     dst_vm_fixture=self.VM11_fixture)

        if ((ret1 == True) and (ret2 == True)):
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                   self.VM11_fixture.vm_ip, self.VM21_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info("Found %s matching flows" % flow_record)
                self.logger.info("Test with src as CIDR and dst as ANY PASSED")
            else:
                result = False
                self.logger.error("Test with src as CIDR and dst as ANY FAILED")
        else:
            result = False
            self.logger.error("Test with src as CIDR and dst as ANY FAILED")

        return result

    # end test_policy_cidr_src_cidr_dst_any

    @tcutils.wrappers.preposttest_wrapper
    def test_policy_cidr_src_cidr_dst_cidr(self):
        """Test cases to test policy CIDR"""
        """Policy1 Rule :- source = CIDR-VM11, destination = CIDR-VM12."""
        """Policy2 Rule :- source = CIDR-VM11, destination = CIDR-VM21."""
        result = True
        af = self.inputs.get_af()

        # create Ipam and VN
        self.setup_ipam_vn()

        # create VM
        self.setup_vm()
        self.VM12_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN1_fixture.obj,
                vm_name='VM12',
                project_name=self.project.project_name))
        self.VM12_fixture.wait_till_vm_is_up()

        #Check initial connectivity without policies in place.
        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM12_fixture)
        if ret == True :
            self.logger.info("ICMP traffic is allowed between VMs in same VN")
        else:
            result = False
            self.logger.error(
                "ICMP traffic is not allowed between VMs in same VN, which is wrong")

        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM21_fixture)
        if ret == True :
            self.logger.info("ICMP traffic is not allowed between VMs accross VNs")
        else:
            result = False
            self.logger.error(
                "ICMP traffic is allowed between VMs accross VNs, which is wrong")
        if result == False:
            return result

        #get the VM IP Addresses in cidr format.
        vm11_ip = str(IPNetwork(self.VM11_fixture.get_vm_ips(af='v4')[0]))
        vm12_ip = str(IPNetwork(self.VM12_fixture.get_vm_ips(af='v4')[0]))
        vm21_ip = str(IPNetwork(self.VM21_fixture.get_vm_ips(af='v4')[0]))
        if 'v6' == af or 'dual' == af:
            vm11_ipv6 = str(IPNetwork(self.VM11_fixture.get_vm_ips(af='v6')[0]))
            vm12_ipv6 = str(IPNetwork(self.VM12_fixture.get_vm_ips(af='v6')[0]))
            vm21_ipv6 = str(IPNetwork(self.VM21_fixture.get_vm_ips(af='v6')[0]))
        else:
            vm11_ipv6 = None
            vm12_ipv6 = None
            vm21_ipv6 = None

        # create policy
        policy_name = 'policy1112'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': vm12_ip,
                  'source_subnet': vm11_ip,
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                                    {vm11_ip:vm11_ipv6,
                                                     vm12_ip:vm12_ipv6})

        policy1112_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy1211'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': vm11_ip,
                  'source_subnet': vm12_ip,
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                                    {vm11_ip:vm11_ipv6,
                                                     vm12_ip:vm12_ipv6})

        policy1211_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy1121'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': vm21_ip,
                  'source_subnet': vm11_ip,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                                    {vm11_ip:vm11_ipv6,
                                                     vm21_ip:vm21_ipv6})

        policy1121_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        policy_name = 'policy2111'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': vm11_ip,
                  'source_subnet': vm21_ip,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'any',
                  'dest_network': 'VN1',
                  'source_network': 'VN2',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        rules = policy_test_utils.update_cidr_rules_with_ipv6(af, rules,
                                                    {vm11_ip:vm11_ipv6,
                                                     vm21_ip:vm21_ipv6})

        policy2111_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy1112_fixture.policy_obj, \
                            policy1211_fixture.policy_obj, \
                            policy1121_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy1112','policy1211','policy1121'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : \
                           [policy2111_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy2111'],
                project_name=self.project.project_name))

        #Test traffic with the policies having cidr as src and dst,
        #attached to the respective networks.
        ret = self.VM11_fixture.ping_with_certainty(expectation=False,
                                    dst_vm_fixture=self.VM12_fixture)
        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                  self.VM11_fixture.vm_ip, self.VM12_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:D(Policy)' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info(
                "ICMP traffic is not allowed between VM11 and VM12, by policy1112 and policy1211.")
                self.logger.info("Above test Passed.")
            else:
                result = False
                self.logger.error(
                "ICMP traffic is not allowed between VM11 and VM12, by policy1112 and policy1211.")
                self.logger.error("Above test Failed.")
        else:
            result = False
            self.logger.error(
                "ICMP traffic is not allowed between VM11 and VM12, by policy1112 and policy1211.")
            self.logger.error("Above test Failed.")

        ret = False
        flow_record = 0
        ret = self.VM11_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM21_fixture)
        if ret == True :
            cmd = "flow -l | grep %s -A1 | grep %s -A1 " % (
                  self.VM11_fixture.vm_ip, self.VM21_fixture.vm_ip)
            cmd = cmd + "| grep 'Action:F' | wc -l"
            flow_record = self.inputs.run_cmd_on_server(
                self.VM11_fixture.vm_node_ip, cmd,
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['username'],
                self.inputs.host_data[self.VM11_fixture.vm_node_ip]['password'])
            if flow_record > 0:
                self.logger.info(
                "ICMP traffic is allowed between VM11 and VM21, by policy1121 and policy2111.")
                self.logger.info("Above test Passed.")
            else:
                result = False
                self.logger.error(
                "ICMP traffic is allowed between VM11 and VM21, by policy1121 and policy2111.")
                self.logger.error("Above test Failed.")
        else:
            result = False
            self.logger.error(
                "ICMP traffic is allowed between VM11 and VM21, by policy1121 and policy2111.")
            self.logger.error("Above test Failed.")
        if result == False:
            return result

        return result

    # end test_policy_cidr_src_cidr_dst_cidr
    @tcutils.wrappers.preposttest_wrapper
    def test_route_leaking_pass_protocol_src_cidr_dst_cidr(self):
        """Test case to test route leaking with specific protocol"""
        """Policy Rule :- source = CIDR, destination = CIDR."""
        result = True
        # create Ipam and VN
        self.setup_ipam_vn()
        VN1_subnet = self.VN1_fixture.get_cidrs()[0]
        VN2_subnet = self.VN2_fixture.get_cidrs()[0]
        # create policy
        policy_name = 'policy12'
        rules = []
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_subnet': VN2_subnet,
                  'source_subnet': VN1_subnet,
                  'dst_ports': 'any',
                  'simple_action': 'deny',
                  'src_ports': 'any'
                 },
                 {'direction': '<>',
                  'protocol': 'tcp',
                  'dest_network': 'VN2',
                  'source_network': 'VN1',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]

        policy12_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : [policy12_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=['policy12'],
                project_name=self.project.project_name))

        VN2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN2_fixture.vn_name,
                policy_obj={self.VN2_fixture.vn_name : [policy12_fixture.policy_obj]},
                vn_obj={self.VN2_fixture.vn_name : self.VN2_fixture},
                vn_policys=['policy12'],
                project_name=self.project.project_name))
        # create VM
        self.setup_vm()
        agent_inspect_h = self.agent_inspect[self.VM11_fixture.vm_node_ip]
        vrf_id = agent_inspect_h.get_vna_vrf_id(self.VN1_fixture.vn_fq_name)
        route = agent_inspect_h.get_vna_route(vrf_id= vrf_id[0], ip=self.VM21_fixture.vm_ip)
        self.logger.debug("Route value : %s" % route)
        if route:
            self.logger.info("Route of VN2 found in VN1 database. Route leaking successful")
        else:
            self.logger.error("Route of VN2  not found in VN1 database. Route leaking failed")
            result = False
            assert result, "Route leaking between VN1 and VN2 failed"
        assert self.VM11_fixture.ping_with_certainty(self.VM21_fixture.vm_ip, \
                  expectation=False),"ICMP deny rule working unexpectedly and allowing ICMP"
        assert self.VM11_fixture.check_file_transfer(self.VM21_fixture, mode='scp',\
                 size='100', expectation=True),"TCP Allow rule working unexpectedly and denying TCP as well"
    # end test_route_leaking_pass_protocol_src_cidr_dst_cidr

# end PolicyAclTests

class TestPolicyAclIpv4v6(TestPolicyAcl):

    @classmethod
    def setUpClass(cls):
        super(TestPolicyAcl, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

