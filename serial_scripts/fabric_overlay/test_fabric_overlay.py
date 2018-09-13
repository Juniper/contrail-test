import os
import fixtures
import testtools
import time

import test
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest

from vn_test import VNFixture

class TestFabricOverlayBasic(BaseFabricTest):
    @classmethod
    def setUpClass(cls):
        super(TestFabricOverlayBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
#        if getattr(cls, 'fabric', None):
#            cls.cleanup_fabric(cls.fabric)
        super(TestFabricOverlayBasic, cls).tearDownClass()

    def setUp(self):
        super(TestFabricOverlayBasic, self).setUp()
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric, devices, interfaces = self.onboard_existing_fabric(fabric_dict)
        assert interfaces, 'Failed to onboard existing fabric %s'%fabric_dict
        self.assign_roles(fabric, devices)
        self.spines = []
        self.leafs = []
        for device in devices:
            device.read()
            if device.role == 'spine':
                self.spines.append(device)
            elif device.role == 'leaf':
                self.leafs.append(device)

    @preposttest_wrapper
    def test_fabric_sanity_mesh_ping(self):
        bms_fixtures = list()

        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        assert self.do_ping_mesh(bms_fixtures+[vm1])

    @preposttest_wrapper
    def test_ping_between_kvm_vm_and_untagged_bms(self, vlanid=0):
        '''Validate ping between a KVM VM and a untagged BMS

        '''
        vn = self.create_vn()
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn, security_groups=[self.default_sg.uuid], vlan_id=vlanid)
        vm1_fixture = self.create_vm(vn_fixture=vn, image_name='cirros')
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(bms1_fixture.bms_ip),\
            self.logger.error('Unable to ping BMS IP %s from VM %s' % (
                bms1_fixture.bms_ip, vm1_fixture.vm_ip))
        self.logger.info('Ping from openstack VM to BMS IP passed')
    #end test_ping_between_kvm_vm_and_untagged_bms

    @preposttest_wrapper
    def test_ping_between_kvm_vm_and_tagged_bms(self, vlanid=10):
        '''Validate ping between a KVM VM and a tagged BMS

        '''
        vn_fixture = self.create_vn()
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=vlanid)
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, image_name='cirros')
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(bms1_fixture.bms_ip),\
            self.logger.error('Unable to ping BMS IP %s from VM %s' % (
                bms1_fixture.bms_ip, vm1_fixture.vm_ip))
        self.logger.info('Ping from openstack VM to BMS IP passed')
    #end test_ping_between_kvm_vm_and_tagged_bms

    @preposttest_wrapper
    def test_ping_between_two_instances_intra_vn(self):
        '''
        Create two tagged BMSs on two TORs in the same VN
        Test ping between them
        Validate that the MACs are resolved correctly for each others' IP
        '''
        vlanid = 0
        vn_fixture = self.create_vn(disable_dns=True)
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=vlanid)
        bms2_fixture = self.create_bms(bms_name=bms_data[1], vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=vlanid)

        self.do_ping_test(bms1_fixture, bms1_fixture.bms_ip, bms2_fixture.bms_ip)
    # end test_ping_between_two_tors_intra_vn

    @preposttest_wrapper
    def test_add_remove_vmi_from_lif(self):
        '''Validate addition and removal of VMI from the ToR Lif
        Add a VMI(for BMS) to a ToR lif
        Check if BMS connectivity is fine
        Remove the VMI from the lif
        Check if BMS connectivity is broken
        Add the VMI back again
        Check if BMS connectivity is restored
        '''
        vlanid = 0
        vn_fixture = self.create_vn(disable_dns=True)
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=vlanid)
        bms2_fixture = self.create_bms(bms_name=bms_data[1], vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid], vlan_id=vlanid)

        # Remove first bms' vmi from lif
        bms1_fixture.disassociate_lif()
        self.do_ping_test(bms1_fixture, bms1_fixture.bms_ip, bms2_fixture.bms_ip, expectation=False)

        # Add the bms' vmi back to lif
        bms1_fixture.associate_lif()
        self.do_ping_test(bms1_fixture, bms1_fixture.bms_ip, bms2_fixture.bms_ip)
    # end test_add_remove_vmi_from_tor_lif

    
class TestVxlanID(BaseFabricTest):

    @classmethod
    def setUpClass(cls):
        super(TestVxlanID, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVxlanID, cls).tearDownClass()

    def setUp(self):
        super(TestVxlanID, self).setUp()
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric, devices, interfaces = self.onboard_existing_fabric(fabric_dict)
        assert interfaces, 'Failed to onboard existing fabric %s'%fabric_dict
        self.assign_roles(fabric, devices)
#Have to move this to fabric base.py
        self.spines = []
        self.leafs = []
        for device in devices:
            device.read()
            if device.role == 'spine':
                self.spines.append(device)
            elif device.role == 'leaf':
                self.leafs.append(device)

    @preposttest_wrapper
    def test_check_vxlan_id_reuse(self):
        '''
            Create a VN X
            Create another VN Y and check that the VNid is the next number
            Delete the two Vns
            On creating a VN again, verify that Vxlan id of X is used
             (i.e vxlan id gets reused)
        '''
        vn1_name = get_random_name('vn')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn')
        vn2_subnets = [get_random_cidr()]

        # First VN
        vn1_obj = VNFixture(project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=vn1_name,
            subnets=vn1_subnets)
        vn1_obj.setUp()
        vxlan_id1 = vn1_obj.get_vxlan_id()

        # Second VN
        vn2_obj = VNFixture(project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=vn2_name,
            subnets=vn2_subnets)
        vn2_obj.setUp()
        vxlan_id2 = vn2_obj.get_vxlan_id()

        assert vxlan_id2 == (vxlan_id1+1), (
            "Vxlan ID allocation is not incremental, "
            "Two VNs were seen to have vxlan ids %s, %s" % (
                vxlan_id1, vxlan_id2))
        # Delete the vns
        vn1_obj.cleanUp()
        vn2_obj.cleanUp()

        vn3_fixture = self.create_vn()
        assert vn3_fixture.verify_on_setup(), "VNFixture verify failed!"
        new_vxlan_id = vn3_fixture.get_vxlan_id()
        assert new_vxlan_id == vxlan_id1, (
            "Vxlan ID reuse does not seem to happen",
            "Expected : %s, Got : %s" % (vxlan_id1, new_vxlan_id))
        self.logger.info('Vxlan ids are reused..ok')
    # end test_check_vxlan_id_reuse


class TestBasicInterVN(BaseFabricTest):
    @classmethod
    def setUpClass(cls):
        super(TestBasicInterVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicInterVN, cls).tearDownClass()

    def setUp(self):
        super(TestBasicInterVN, self).setUp()
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric, devices, interfaces = self.onboard_existing_fabric(fabric_dict)
        assert interfaces, 'Failed to onboard existing fabric %s'%fabric_dict
        self.assign_roles(fabric, devices)
        self.spines = []
        self.leafs = []
        for device in devices:
            device.read()
            if device.role == 'spine':
                self.spines.append(device)
            elif device.role == 'leaf':
                self.leafs.append(device)

# need to revisit once the logical router fixture is stable
    @preposttest_wrapper
    def test_ping_between_two_tors_inter_vn(self):
        ''' Create two vns
            VxLan ID allocation is automatic
            Have two bmss in each of those vns
            Apply policy between vns to allow all traffic
            Validate ping between the bmss
            Validate arp of gateway IP on the bmss
        '''
        vlan_id = 0
        vn1_vxlan_id = None
        vn2_vxlan_id = None

        vn1_fixture = self.create_vn()
        vn2_fixture = self.create_vn()
        
        # Extend VNs and Spines to logical router
        vn_fixtures = [vn1_fixture, vn2_fixture]
        self.create_logical_routers(self.spines, vn_fixtures)

        bms_data = self.inputs.bms_data.keys()


        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn1_fixture, security_groups=[self.default_sg.uuid])
        bms2_fixture = self.create_bms(bms_name=bms_data[1], vn_fixture=vn2_fixture, security_groups=[self.default_sg.uuid])

        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)

        # Clear arps and check again
        self.clear_arps([bms1_fixture, bms2_fixture])
        self.do_ping_test(bms1_fixture, bms1_ip, bms2_ip)
