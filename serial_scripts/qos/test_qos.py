from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture

from common.qos.base import *

from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from scripts.qos.test_qos import QosTestExtendedBase,TestQosPolicy

class TestQosSerial(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosSerial, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
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
        if not cls.setupClass_is_run:
            return
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
        fcs = [ {'fc_id':100, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = { 1: 100 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
#                   count=1,
                    dscp=1,
                    expected_dscp=10,
                    expected_dot1p=1,
                    expected_exp=1,
#                   protocol='tcp',
                    src_port='10000',
                    dest_port='20000',
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    encap = "MPLSoGRE")
    # end test_qos_remark_dscp_on_vmi_gre_encap

    
class TestQosPolicyEncap(TestQosPolicy):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyEncap, cls).setUpClass()
        cls.existing_encap = cls.connections.read_vrouter_config_encap()
        cls.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
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
        fcs = [{'name':"FC_Test",'fc_id':100,'dscp': 62,'dot1p': 7,'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0:100,1:100,2:100,3:100,4:100,5:100,6:100,7:100,8:100,9:100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn2_vm1_fixture,
                    #count=20,
                    dscp=9,
                    expected_dscp=62,
                    expected_exp=3,
                    expected_dot1p=7,
                    src_compute_fixture = self.vn1_vm1_compute_fixture,
                    #protocol='tcp',
                    encap = "MPLSoGRE")
    # end test_qos_remark_exp_dscp_on_policy_gre_encap
 