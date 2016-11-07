#Testcases for disabling policy on VMIs:
#PR https://bugs.launchpad.net/juniperopenstack/+bug/1558920 and PR https://bugs.launchpad.net/juniperopenstack/+bug/1566650
from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
import test
from tcutils.util import get_random_cidr, get_random_name
import random
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain

AF_TEST = 'v6'

class DisablePolicyEcmpSerial(BaseVrouterTest, ConfigSvcChain, VerifySvcChain):

    @classmethod
    def setUpClass(cls):
        super(DisablePolicyEcmpSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(DisablePolicyEcmpSerial, cls).tearDownClass()

    @preposttest_wrapper
    def test_disable_policy_ecmp_siv2(self):
        """
        Description: Verify disable policy with service chain with scaling
        Steps:
            1. create 2 VNs and connect it with policy via service chain v2
            2. launch VMs in both VNs and SIs and disable the policy on all the VMIs
                including SIs
            3. start the traffic from left to right VN
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among all the SIs
        """
        vn_fixtures = self.create_vns(count=3)
        self.verify_vns(vn_fixtures)
        vn_left = vn_fixtures[0]
        vn_right = vn_fixtures[1]
        vn_mgmt = vn_fixtures[2]

        vm_left = self.create_vms(vn_fixture=vn_left, count=1)[0]
        vm_right = self.create_vms(vn_fixture=vn_right, count=1)[0]

        st_name = get_random_name("in_net_svc_template_1")
        si_prefix = get_random_name("in_net_svc_instance") + "_"
        policy_name = get_random_name("policy_in_network")
        si_count = 1
        max_inst = 2
        image = 'tiny_trans_fw'
        svc_mode = 'transparent'

        st_fixture, si_fixtures = self.config_st_si(
            st_name, si_prefix, si_count,
            mgmt_vn=vn_mgmt.vn_fq_name,
            left_vn=vn_left.vn_fq_name,
            right_vn=vn_right.vn_fq_name, svc_mode=svc_mode, svc_img_name=image,
            project=self.inputs.project_name, st_version=2, max_inst=max_inst)
        action_list = self.chain_si(
            si_count, si_prefix, self.inputs.project_name)
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn_left.vn_fq_name,
                'src_ports': [0, -1],
                'dest_network': vn_right.vn_fq_name,
                'dst_ports': [0, -1],
                'simple_action': None,
                'action_list': {'apply_service': action_list}
            },
        ]

        policy_fixture = self.config_policy(policy_name, rules)
        vnl_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn_left)
        vnr_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn_right)

        self.verify_vms([vm_left, vm_right])
        self.verify_vms(si_fixtures[0].svm_list)
        self.disable_policy_for_vms([vm_left, vm_right])
        self.disable_policy_for_vms(si_fixtures[0].svm_list)

        assert self.verify_traffic_load_balance_si(vm_left,
            si_fixtures[0].svm_list, vm_right)

        self.disable_policy_for_vms([vm_left, vm_right], disable=False)

        assert self.verify_traffic_load_balance_si(vm_left,
            si_fixtures[0].svm_list, vm_right, flow_count=True)

class DisablePolicyEcmpSerialIpv6(DisablePolicyEcmpSerial):
    @classmethod
    def setUpClass(cls):
        super(DisablePolicyEcmpSerialIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
