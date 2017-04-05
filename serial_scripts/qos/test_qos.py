from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture

from common.qos.base import *


class TestQosSerial(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosSerial, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosSerial, cls).tearDownClass()
    # end tearDownClass


class TestQosEncap(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosEncap, cls).setUpClass()
        cls.existing_encap = cls.connections.read_vrouter_config_encap()
        cls.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.connections.update_vrouter_config_encap(
            cls.existing_encap[0], cls.existing_encap[1],
            cls.existing_encap[2])
        super(TestQosEncap, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_gre_encap(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [{'fc_id': 100, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: 100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=dscp_map.keys()[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            expected_exp=fcs[0]['exp'],
            src_port='10000',
            dest_port='20000',
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            encap="MPLSoGRE")
    # end test_qos_remark_dscp_on_vmi_gre_encap


class TestQosPolicyEncap(TestQosPolicyBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyEncap, cls).setUpClass()
        cls.existing_encap = cls.connections.read_vrouter_config_encap()
        cls.connections.update_vrouter_config_encap(
                                        'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.connections.update_vrouter_config_encap(
            cls.existing_encap[0], cls.existing_encap[1],
            cls.existing_encap[2])
        super(TestQosPolicyEncap, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_exp_dscp_on_policy_gre_encap(self):
        '''Test that qos marking happens on fabric interface when qos
           config is applied on policy applied between 2 VNs
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Validate that packets on fabric from A to B have DSCP 
             marked to 62
        '''
        fcs = [{'name': "FC_Test", 'fc_id': 100,
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: 100, 1: 100, 2: 100, 3: 100, 4:
                    100, 5: 100, 6: 100, 7: 100, 8: 100, 9: 100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn2_vm1_fixture,
            dscp=dscp_map.keys()[9],
            expected_dscp=fcs[0]['dscp'],
            expected_exp=fcs[0]['exp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            encap="MPLSoGRE")
    # end test_qos_remark_exp_dscp_on_policy_gre_encap
    
    @preposttest_wrapper
    def test_qos_config_on_policy_for_all_dscp_entries(self):
        '''
        Create a qos config with all valid DSCP values and verify traffic
        for all dscp values
        Steps:
        1. Create 62 FC IDs having unique DSCP values in all
        2. Create a qos config and map all DSCP to unique FC ID
        3. Validate that packets with dscp 1 on fabric from A to B 
           have DSCP marked to 62
        4. Validate that packets with dscp 62 on fabric from A to B 
           have DSCP marked to 1
        5. Similarly, verify for all DSCP values
        '''
        fcs = []
        dscp_map = {}
        for i in range(1, 63):
            fc = {'name': "FC_Test" + str(i), 'fc_id': i, 'dscp': i}
            fcs.append(fc)
            dscp_map[i] = 63 - i
        fc_fixtures = self.setup_fcs(fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': None,
            'expected_dscp': None,
            'src_compute_fixture': self.vn1_vm1_compute_fixture,
            'encap': "MPLSoGRE"}
        for i in range(1, 63):
            validate_method_args['expected_dscp'] = i
            validate_method_args['dscp'] = 63 - i
            assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_on_policy_for_all_dscp_entries
