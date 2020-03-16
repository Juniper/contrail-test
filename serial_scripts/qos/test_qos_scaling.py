from common.qos.base import *
from builtins import str
from builtins import range
from tcutils.wrappers import preposttest_wrapper

class TestQosScaling(QosTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosScaling, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosScaling, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_forwarding_class_scaling(self):
        '''
        Verify Scaling limits for Forwarding class
        Steps:
        1. Create 256 forwarding class entries
        2. Map all 256 FC entries to some qos-config
        '''
        fc_already_present = []
        for k in range(0, 256):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
                    .get_vrouter_forwarding_class(k):
                fc_already_present.append(k)
        fc_fixtures = []
        qos_fixtures = []
        for i in range(0, 4):
            for k in range(0, 64):
                fc_dict = {
                    'name': "FC_Test_" + str(i * 64 + k), 'fc_id': i * 64 + k,
                    'dscp': k, 'exp': i, 'dot1p': i}
                if i * 64 + k not in fc_already_present:
                    fc_fixtures.append(self.setup_fcs([fc_dict]))
                    # Configuration takes some time to reflect in agent.
        for elem in fc_fixtures:
            assert elem[0].verify_on_setup()
        for i in range(0, 256):
            dscp_map = {10: i}
            if i not in fc_already_present:
                qos_fixtures.append(self.setup_qos_config(name=
                                                    "qos_config_" + str(i),
                                                    dscp_map=dscp_map))
        for elem in qos_fixtures:
            assert elem.verify_on_setup()
    # end test_forwarding_class_scaling

    @preposttest_wrapper
    def test_qos_config_scaling(self):
        '''
        Verify Scaling limits for Forwarding class
        Steps:
        1. Create few forwarding class entries.
        2. Create all type of mappings to be used in qos_map
        3. Configure 4K qos config tables with 80 entries in each table
        4. Associate each qos-config with a VN
        '''
        fcs = []
        qos_fixtures = []
        qc_already_present = []
        for k in range(0, 4000):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
                    .get_vrouter_qos_config(k):
                qc_already_present.append(k)
        dscp_map, dot1p_map, exp_map = {}, {}, {}
        for k in range(0, 80):
            if k < 64:
                fc_dict = {'name': "FC_Test_" + str(k), 'fc_id': k, 'dscp': k}
                dscp_map[k] = k
            elif k >= 64 and k < 72:
                fc_dict = {'name': "FC_Test_" +
                           str(k), 'fc_id': k, 'dot1p': k - 64}
                dot1p_map[k - 64] = k - 64
            elif k >= 72:
                fc_dict = {'name': "FC_Test_" +
                           str(k), 'fc_id': k, 'exp': k - 72}
                exp_map[k - 72] = k - 72
            fcs.append(fc_dict)
        fc_fixtures = self.setup_fcs(fcs)
        for fc in fc_fixtures:
            assert fc.verify_on_setup()
        for i in range(0, 4000):
            if i not in qc_already_present:
                qos_fixtures.append(self.setup_qos_config(
                    name="qos_config_" + str(i),
                    dscp_map=dscp_map,
                    dot1p_map=dot1p_map,
                    exp_map=exp_map))
        for qos_fixture in qos_fixtures:
            assert qos_fixture.verify_on_setup()
            vn_fixture = self.create_vn()
            self.setup_qos_config_on_vn(qos_fixture, vn_fixture.uuid)
    # end test_qos_config_scaling

