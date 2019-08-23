from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.pnf_base import BaseL3PnfTest
import test

class TestL3Pnf(BaseL3PnfTest):
    def _verify_pnf(self, left_vlan_id=None, right_vlan_id=None,
                    left_tor_vlan=None, right_tor_vlan=None, ecmp=None):
        if ecmp and (len(self.pnfs) < 2):
            raise self.skipTest("Need minimum 2 PNF nodes for this test.")

        self.left_vn = self.create_vn()
        self.right_vn = self.create_vn()
        pnf = self.pnfs[0]
        pnf_dict = self.inputs.physical_routers_data[pnf.name]
        for device in self.devices:
            if device.name == pnf_dict['left_qfx']:
                self.left_border_leaf = device
            elif device.name == pnf_dict['right_qfx']:
                self.right_border_leaf = device
        bms_nodes = self.get_bms_nodes(rb_role='erb_ucast_gw')
        left_bms_name = right_bms_name = bms_nodes[0]
        if len(bms_nodes) > 1:
            right_bms_name = bms_nodes[1]
        left_bms = self.create_bms(bms_name=left_bms_name,
            vlan_id=left_vlan_id, tor_port_vlan_tag=left_tor_vlan,
            vn_fixture=self.left_vn)
        right_bms = self.create_bms(bms_name=right_bms_name,
            vlan_id=right_vlan_id, tor_port_vlan_tag=right_tor_vlan,
            vn_fixture=self.right_vn)
        self.left_lr = self.create_logical_router([self.left_vn],
            devices=self.get_associated_prouters(left_bms_name)+\
                    [self.left_border_leaf])
        self.right_lr = self.create_logical_router([self.right_vn],
            devices=self.get_associated_prouters(right_bms_name)+\
                    [self.right_border_leaf])
        self.bms_fixtures = [left_bms, right_bms]
        sid1 = self.create_l3pnf(self.left_lr, self.right_lr, pnf,
            left_svc_vlan='1000', right_svc_vlan='2000',
            left_svc_asn_srx='65000', left_svc_asn_qfx='65100',
            right_svc_asn_qfx='65200')
        self.do_ping_mesh(self.bms_fixtures)

        if ecmp:
            pnf2 = self.pnfs[1]
            sid2 = self.create_l3pnf(self.left_lr, self.right_lr, pnf2,
                left_svc_vlan='1001', right_svc_vlan='2001',
                left_svc_asn_srx='65001', left_svc_asn_qfx='65100',
                right_svc_asn_qfx='65200')
            self.do_ping_mesh(self.bms_fixtures)
            self.perform_cleanup(sid1)
            self.sleep(10)
            self.do_ping_mesh(self.bms_fixtures)



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
        self._verify_pnf(left_tor_vlan=101, right_tor_vlan=102)
        #end test_fabric_pnf_basic

    @preposttest_wrapper
    def test_fabric_pnf_ecmp(self):
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
        self._verify_pnf(left_tor_vlan=101, right_tor_vlan=102,ecmp=True)
        #end test_fabric_pnf_basic

    @preposttest_wrapper
    def test_fabric_pnf_tagged_bms(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
        '''
        self._verify_pnf(left_vlan_id=100, right_vlan_id=200)
        #end test_fabric_pnf_tagged_bms

    @preposttest_wrapper
    def test_fabric_pnf_restart_device_manager(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Perform a restart of the device-manager docker
           10]. Traffic between the two Instances should go through the PNF device again without fail.
        '''
        self._verify_pnf(left_tor_vlan=111, right_tor_vlan=112)
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures)
        #end test_fabric_pnf_restart_device_manager

    @preposttest_wrapper
    def test_fabric_pnf_add_rt_to_lr(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Add a new RT to the LRs.
           10]. Traffic between the two Instances should go through the PNF device again without fail.
        '''
        self._verify_pnf(left_tor_vlan=121, right_tor_vlan=122)
        self.left_lr.add_rt('target:64512:12345')
        self.right_lr.add_rt('target:64512:54321')
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures)
        #end test_fabric_pnf_add_rt_to_lr

    @preposttest_wrapper
    def test_fabric_pnf_add_vni_to_lr(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Add a new VNI to the LRs.
           10]. Traffic between the two Instances should fail.
        '''
        self._verify_pnf(left_tor_vlan=124, right_tor_vlan=125)
        self.left_lr.set_vni('1001')
        self.right_lr.set_vni('2002')
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures, expectation=False)
        #end test_fabric_pnf_add_vni_to_lr

    @preposttest_wrapper
    def test_fabric_pnf_remove_vn_from_lr(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Remove left VN from the LR.
           10]. Traffic between the two Instances should fail.
        '''
        self._verify_pnf(left_tor_vlan=120, right_tor_vlan=121)
        self.left_lr.remove_interface([self.left_vn.vn_id])
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures, expectation=False)
        #end test_fabric_pnf_remove_vn_from_lr

    @preposttest_wrapper
    def test_fabric_pnf_remove_lr_from_router(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Remove the left LR from the border leaf.
           10]. Traffic between the two Instances should fail.
        '''
        self._verify_pnf(left_tor_vlan=11, right_tor_vlan=12)
        self.left_lr.remove_physical_router(self.left_border_leaf.uuid)
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures, expectation=False)
        #end test_fabric_pnf_remove_lr_from_router

    @preposttest_wrapper
    def test_fabric_pnf_vm_to_bms_ping(self):
        '''
           1]. Create 2 VN
           2]. Create Tagged BMS interfaces in each of the VN.
           3]. Create 2 LRs.
           4]. Attach a VN to each of the LR.
           5]. Extend the LR to one Border leaf each and to the ERB-GW.
           6]. Create a PNF Service Template.
           7]. Create a PNF Service Instance between the two LRs.
           8]. Traffic between the two Instances should go through the PNF device.
           9]. Add a new VM in the left VN.
           10]. Traffic between the VM and the two Instances should go through the PNF device without fail.
        '''
        self._verify_pnf(left_tor_vlan=21, right_tor_vlan=22)
        left_vm = self.create_vm(vn_fixture=self.left_vn, image_name='cirros')
        self.sleep(60) #Wait to make sure if any config push happens to complete
        self.do_ping_mesh(self.bms_fixtures + [left_vm])
        #end test_fabric_pnf_vm_to_bms_ping
