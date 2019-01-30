import test
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork

class TestFabricOverlayBasic(BaseFabricTest):
    @preposttest_wrapper
    def test_fabric_sanity_mesh_ping(self):
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, security_groups=[self.default_sg.uuid]))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_with_multiple_subnets(self):
        ''' Create a VN with two /29 subnets
            Create 8 VMIs on the VN so that 1st subnet IPs are exhausted
            Add lifs with 6th and 7th VMIs
            Validate that the BMSs get IP from 2nd subnet and ping passes
        '''
        vn_subnets = [get_random_cidr('29'), get_random_cidr('29')]
        vn_fixture = self.create_vn(vn_subnets=vn_subnets, disable_dns=True)

        lr = self.create_logical_router([vn_fixture])
        bms_data = self.inputs.bms_data.keys()
        bms1_fixture = self.create_bms(bms_name=bms_data[0],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid])
        for i in range(0, 4):
            port_fixture = self.setup_vmi(vn_fixture.uuid)
            if port_fixture.get_ip_addresses()[0] in IPNetwork(vn_subnets[1]):
                self.perform_cleanup(port_fixture)
                break
        bms2_fixture = self.create_bms(bms_name=bms_data[1],
            vn_fixture=vn_fixture, security_groups=[self.default_sg.uuid])
        self.do_ping_test(bms1_fixture, bms2_fixture.bms_ip)
    # end test_with_multiple_subnets

    @preposttest_wrapper
    def test_ping_between_kvm_vm_and_tagged_bms(self, vlanid=10):
        '''Validate ping between a KVM VM and a tagged BMS

        '''
        vn_fixture = self.create_vn()
        bms_data = self.inputs.bms_data.keys()

        bms1_fixture = self.create_bms(bms_name=bms_data[0], vn_fixture=vn_fixture,
            security_groups=[self.default_sg.uuid], vlan_id=vlanid)
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, image_name='cirros')
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(bms1_fixture.bms_ip),\
            self.logger.error('Unable to ping BMS IP %s from VM %s' % (
                bms1_fixture.bms_ip, vm1_fixture.vm_ip))
        self.logger.info('Ping from openstack VM to BMS IP passed')
    #end test_ping_between_kvm_vm_and_tagged_bms

class TestVxlanID(GenericTestBase):
    @preposttest_wrapper
    def test_check_vxlan_id_reuse(self):
        '''
            Create a VN X
            Create another VN Y and check that the VNid is the next number
            Delete the two Vns
            On creating a VN again, verify that Vxlan id of X is used
             (i.e vxlan id gets reused)
        '''
        vn1 = self.create_vn()
        vn2 = self.create_vn()

        vxlan_id1 = vn1.get_vxlan_id()
        vxlan_id2 = vn2.get_vxlan_id()

        assert vxlan_id2 == (vxlan_id1+1), (
            "Vxlan ID allocation is not incremental, "
            "Two VNs were seen to have vxlan ids %s, %s" % (
                vxlan_id1, vxlan_id2))
        # Delete the vns
        self.perform_cleanup(vn1)
        self.perform_cleanup(vn2)

        vn3_fixture = self.create_vn()
        assert vn3_fixture.verify_on_setup(), "VNFixture verify failed!"
        new_vxlan_id = vn3_fixture.get_vxlan_id()
        assert new_vxlan_id == vxlan_id1, (
            "Vxlan ID reuse does not seem to happen",
            "Expected : %s, Got : %s" % (vxlan_id1, new_vxlan_id))
        self.logger.info('Vxlan ids are reused..ok')
    # end test_check_vxlan_id_reuse
