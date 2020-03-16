from common.qos.base import *
from tcutils.wrappers import preposttest_wrapper
from vnc_api.exceptions import BadRequest
from common.neutron.base import BaseNeutronTest

class TestQosNegative(QosTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosNegative, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosNegative, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_invalid_range_for_fc(self):
        '''
        Validate that incorrect values while configuring Forwarding class
        are not accepted:
        Verify following:
        1. To verify that FC ID more than 255 is not accepted
        2. To verify that FC ID as negative value is not accepted
        3. To verify that FC ID as string is not accepted
        4. To verify that DSCP more than 63 is not accepted
        5. To verify that Dot1p more than 7 is not accepted
        6. To verify that exp more than 8 is not accepted
        7. To verify that negative values for dscp,dot1p and exp
            are not accepted
        8. To verify that string values for dscp,dot1p and exp
            are not accepted
        '''
        fc_list = []
        fc_list.append([{'fc_id': 256, 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': -1, 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': "string", 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': 1, 'dscp': 64, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': 2, 'dscp': 62, 'dot1p': 8, 'exp': 1}])
        fc_list.append([{'fc_id': 3, 'dscp': 62, 'dot1p': 4, 'exp': 8}])
        fc_list.append([{'fc_id': 4, 'dscp': -1, 'dot1p': -1, 'exp': -1}])
        fc_list.append([{'fc_id': 5, 'dscp': "x", 'dot1p': "y", 'exp': "z"}])
        for elem in fc_list:
            try:
                self.setup_fcs(elem)
                self.logger.error("Creation of invalid FC '%s' passed" % elem)
                assert False, "FC with invalid values got created"
            except BadRequest as e:
                self.logger.debug(e)
                self.logger.debug("Creation of invalid FC '%s' failed as expected"
                                  % elem)
    # end test_invalid_range_for_qc_and_fc

    @preposttest_wrapper
    def test_invalid_range_for_qc(self):
        '''
        Validate that incorrect values while configuring Qos config are 
        not accepted:
        Verify following:
        1. To verify that DSCP > 63 in dscp map is not accepted
        2. To verify that Dot1P > 8 in dot1p map is not accepted
        3. To verify that EXP > 8 in exp map is not accepted
        4. To verify that negative value for any map is not accepted
        5. To verify that string value for any map is not accepted
        6. To verify that negative FC value in map is not accepted
        7. To verify that string FC value in map is not accepted
        8. To verify that FC ID in map should not be more than 255
        '''
        maps = [{'dscp_map': {64: 4}},
                {'dot1p_map': {8: 4}},
                {'exp_map': {8: 4}},
                {'dscp_map': {-1: 4}, 'dot1p_map':
                    {-1: 4}, 'exp_map': {-1: 4}},
                {'dscp_map': {"x": 4}, 'dot1p_map':
                 {"y": 4}, 'exp_map': {"z": 4}},
                {'dscp_map': {63: -1}, 'dot1p_map':
                 {7: -1}, 'exp_map': {7: -1}},
                {'dscp_map': {63: "x"}, 'dot1p_map':
                 {7: "y"}, 'exp_map': {7: "z"}},
                {'dscp_map': {64: 4}}]
        for elem in maps:
            try:
                qos_fixture = self.setup_qos_config(**elem)
                self.logger.error("Creation of invalid QC with map '%s'"
                                  "passed" % elem)
                assert False, "QC with invalid values got created"
            except BadRequest as e:
                self.logger.debug(e)
                self.logger.debug("Creation of invalid QC with map '%s'"
                                  " failed as expected" % elem)
    # end test_invalid_range_for_qc