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

        self.VM11_fixture.wait_till_vm_is_up()
        self.VM21_fixture.wait_till_vm_is_up()
    
    # end setup_vm

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

        ret = self.VM11_fixture.ping_with_certainty(self.VM21_fixture.vm_ip, \
                                                    expectation=True)

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

        ret = self.VM11_fixture.ping_with_certainty(self.VM21_fixture.vm_ip, \
                                                    expectation=True)

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

        ret = self.VM11_fixture.ping_with_certainty(self.VM21_fixture.vm_ip, \
                                                    expectation=True)

        if ret == True :
            self.logger.info("Test with src as any and dst as policy PASSED")
        else:
            result = False
            self.logger.error("Test with src as any and dst as policy FAILED")

        return result

    # end test_policy_inheritance_src_any_dst_pol

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

        ret = self.VM11_fixture.ping_with_certainty(self.VM21_fixture.vm_ip, \
                                                    expectation=True)

        if ret == True :
            self.logger.info("Test with src as policy and dst as any PASSED")
        else:
            result = False
            self.logger.error("Test with src as policy and dst as any FAILED")

        return result

    # end test_policy_inheritance_src_pol_dst_any 

# end PolicyAclTests
