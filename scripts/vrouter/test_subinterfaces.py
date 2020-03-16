from common.vrouter.base import BaseVrouterTest
import test
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *

# Use common vlan id for all tests for now
VLAN_ID = 100

class TestSubInterfaces(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(TestSubInterfaces, cls).setUpClass()
        cls.agent_inspect_h = cls.connections.agent_inspect

        #vn2 is a dummy parent VN
        cls.vn1_fixture = cls.create_only_vn()
        cls.vn2_fixture = cls.create_only_vn()
        cls.vn3_fixture = cls.create_only_vn()

        cls.vn2_port1 = cls.setup_only_vmi(cls.vn2_fixture.uuid)
        cls.vn1_port1 = cls.setup_only_vmi(cls.vn1_fixture.uuid,
                                       parent_vmi=cls.vn2_port1.vmi_obj,
                                       vlan_id=VLAN_ID,
                                       api_type='contrail',
                                       mac_address=cls.vn2_port1.mac_address)

        cls.vn2_port2 = cls.setup_only_vmi(cls.vn2_fixture.uuid)
        cls.vn1_port2 = cls.setup_only_vmi(cls.vn1_fixture.uuid,
                                       parent_vmi=cls.vn2_port2.vmi_obj,
                                       vlan_id=VLAN_ID,
                                       api_type='contrail',
                                       mac_address=cls.vn2_port2.mac_address)

        cls.vn2_port3 = cls.setup_only_vmi(cls.vn2_fixture.uuid)
        cls.vn3_port1 = cls.setup_only_vmi(cls.vn3_fixture.uuid,
                                       parent_vmi=cls.vn2_port3.vmi_obj,
                                       vlan_id=VLAN_ID,
                                       api_type='contrail',
                                       mac_address=cls.vn2_port3.mac_address)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.vn3_port1.cleanUp()
        cls.vn2_port3.cleanUp()
        cls.vn1_port2.cleanUp()
        cls.vn2_port2.cleanUp()
        cls.vn1_port1.cleanUp()
        cls.vn2_port1.cleanUp()
        cls.vn3_fixture.cleanUp()
        cls.vn2_fixture.cleanUp()
        cls.vn1_fixture.cleanUp()
        super(TestSubInterfaces, cls).tearDownClass()

    '''
    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 2:
            return (False, 'Skipping test since atleast 2 compute nodes are'
                'required')
        return (True, None)
    # end is_test_applicable

    '''
    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_vlan_interface_1(self):
        '''
        Test ping between vlan tagged and untagged interfaces within a VN

        '''
        vm1_fixture = self.create_vm(vn_objs=[self.vn2_fixture.obj],
                                     port_ids=[self.vn2_port1.uuid],
                                     userdata='./scripts/vrouter/user_data1.sh'
                                     )
        vm2_fixture = self.create_vm(self.vn1_fixture)
        vm3_fixture = self.create_vm(vn_objs=[self.vn2_fixture.obj],
                                     port_ids=[self.vn2_port2.uuid],
                                     userdata='./scripts/vrouter/user_data1.sh'
                                     )
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        assert vm3_fixture.wait_till_vm_is_up()
        vm3_ip = self.vn1_port2.get_ip_addresses()[0]
        assert vm1_fixture.ping_with_certainty(vm3_ip)
    # end test_vlan_interface_1

    @test.attr(type=['cb_sanity', 'sanity','dev_reg'])
    @preposttest_wrapper
    def test_vlan_interface_2(self):
        '''
        Test ping/hping between tagged-untagged vmis across VNs
        '''
        vm1_fixture = self.create_vm(vn_objs=[self.vn2_fixture.obj],
                                     port_ids=[self.vn2_port1.uuid],
                                     userdata='./scripts/vrouter/user_data1.sh'
                                     )
        vm2_fixture = self.create_vm(self.vn3_fixture)
        vm3_fixture = self.create_vm(vn_objs=[self.vn2_fixture.obj],
                                     port_ids=[self.vn2_port3.uuid],
                                     userdata='./scripts/vrouter/user_data1.sh'
                                     )
        # vm2 and vm3 are in one VN. vm1 pings to these vms 
        router_dict = self.create_router()
        self.add_vn_to_router(router_dict['id'], self.vn1_fixture)
        self.add_vn_to_router(router_dict['id'], self.vn3_fixture)

        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm3_fixture.wait_till_vm_is_up()

        interface = 'eth0.%s' %(VLAN_ID)
        #Before adding the route, wait till interface is found on VM
        assert vm1_fixture.wait_till_interface_created(interface,
            ip=self.vn1_port1.get_ip_addresses()[0])[0]
        assert vm3_fixture.wait_till_interface_created(interface,
            ip=self.vn3_port1.get_ip_addresses()[0])[0]

        # Add route in VMs so that VM chooses sub-interface to ping
        vm1_fixture.add_route_in_vm(self.vn3_fixture.get_cidrs()[0],
                                    device=interface)
        vm3_fixture.add_route_in_vm(self.vn1_fixture.get_cidrs()[0],
                                    device=interface)

        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        vm3_ip = self.vn3_port1.get_ip_addresses()[0]
        assert vm1_fixture.ping_with_certainty(vm3_ip)
    # end test_vlan_interface_2
