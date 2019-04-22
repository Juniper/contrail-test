from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.pnf_base import BaseL3PnfTest
import test
import random
from tcutils.util import skip_because


class TestL3Pnf(BaseL3PnfTest):

    @classmethod
    def setUpClass(cls):
        super(TestL3Pnf, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestL3Pnf, cls).tearDownClass()

    def is_test_applicable(self):
        result, msg = super(TestL3Pnf,
                            self).is_test_applicable()
        if result:
            msg = 'No PNF device in the provided fabric topology'
            for device in self.inputs.physical_routers_data.iterkeys():
                if self.get_role_from_inputs(device) == 'pnf':
                    return (True, None)
        return False, msg

    @preposttest_wrapper
    def test_fabric_pnf_basic(self):
        '''
           1]. Create 2 VN
           2]. Add a Instance in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
        '''
        left_vn = self.create_vn()
        right_vn = self.create_vn()
        for device_name, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'pnf':
                right_attachment_point = device_dict['right_attachment_point']
                left_attachment_point = device_dict['left_attachment_point']
                pnf_right_intf = device_dict['pnf_right_intf']
                pnf_left_intf = device_dict['pnf_left_intf']
        for border_leaf in self.border_leafs:
            if border_leaf.name == right_attachment_point.split(':')[0]:
                right_border_leaf = border_leaf
            elif border_leaf.name == left_attachment_point.split(':')[0]:
                left_border_leaf = border_leaf
        left_lr = self.create_and_extend_lr(
            left_vn, [self.erb_leafs[0], left_border_leaf])
        right_lr = self.create_and_extend_lr(
            right_vn, [self.erb_leafs[0], right_border_leaf])
        left_bms_name = self.inputs.bms_data.keys()[0]
        right_bms_name = self.inputs.bms_data.keys()[1]
        left_bms = self.create_bms(
            bms_name=left_bms_name, vn_fixture=left_vn, security_groups=[self.default_sg.uuid])
        right_bms = self.create_bms(
            bms_name=right_bms_name, vn_fixture=right_vn, security_groups=[self.default_sg.uuid])
        bms_fixtures = [left_bms, right_bms]
        self.create_l3pnf(left_lr, right_lr, left_attachment_point, right_attachment_point, pnf_left_intf, pnf_right_intf, left_svc_vlan='1000',
                          right_svc_vlan='2000',
                          left_svc_asn_srx='65000',
                          left_svc_asn_qfx='65100',
                          right_svc_asn_qfx='65200')
        self.do_ping_mesh(bms_fixtures)
