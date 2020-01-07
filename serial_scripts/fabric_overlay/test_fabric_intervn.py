from __future__ import absolute_import
# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will
# try to pick params.ini in PWD

from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
import test
import random
from tcutils.util import skip_because

class TestFabricEvpnType5(BaseFabricTest):

    @classmethod
    def setUpClass(cls):
        super(TestFabricEvpnType5, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestFabricEvpnType5, cls).tearDownClass()

    def is_test_applicable(self):
        result, msg = super(TestFabricEvpnType5,
                            self).is_test_applicable()
        if result:
            msg = 'No spines in the provided fabric topology'
            for device in self.inputs.physical_routers_data.keys():
                if self.get_role_from_inputs(device) == 'spine':
                    return (True, None)
        return False, msg

    @preposttest_wrapper
    def test_fabric_intervn_basic(self):
        '''
           Create VN vn1
           Create VNs per BMS node
           Create Logical Router and add all the VNs
           Create VM on vn1
           Create untagged BMS instances on respective VNs
           Check ping connectivity across all the instances
        '''
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list(); bms_vns = dict()
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        for bms in self.get_bms_nodes():
            bms_vns[bms] = self.create_vn()
        self.create_logical_router([vn1, vn2]+list(bms_vns.values()))
        vm1 = self.create_vm(vn_fixture=vn1, image_name='ubuntu')
        vm2 = self.create_vm(vn_fixture=vn2, image_name='ubuntu')
        vlan = 3
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                tor_port_vlan_tag=vlan,
                vn_fixture=bms_vns[bms]))
            vlan = vlan + 1
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1, vm2])

    @preposttest_wrapper
    def test_fabric_intervn_tagged(self):
        '''
           Create VN vn1
           Create VNs per BMS node
           Create VM on vn1
           Create Logical Router and add all the VNs
           Create tagged BMS instances on respective VNs
           Check ping connectivity across all the instances
        '''
        vlan = 10
        bms_fixtures = list(); bms_vns = dict()
        vn = self.create_vn()
        for bms in self.get_bms_nodes():
            bms_vns[bms] = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros')
        self.create_logical_router([vn]+list(bms_vns.values()))
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                vn_fixture=bms_vns[bms], vlan_id=vlan))
            vlan = vlan + 10
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])

    @preposttest_wrapper
    def test_evpn_type_5_vxlan_traffic_between_vn(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create logical Routers and attach above created VNs
            Create VMs on Virtual Networks
            Verify traffic between accross Virtual Networks

        '''
        vn1 = self.create_vn(); vn2 = self.create_vn()
        vn3 = self.create_vn(); vn4 = self.create_vn()
        lr1 = self.create_logical_router([vn1, vn2], vni=70001)
        lr2 = self.create_logical_router([vn3, vn4], vni=70002)
        vm11 = self.create_vm(vn_fixture=vn1)
        vm12 = self.create_vm(vn_fixture=vn1)
        vm2 = self.create_vm(vn_fixture=vn2)
        vm3 = self.create_vm(vn_fixture=vn3)
        vm4 = self.create_vm(vn_fixture=vn4)
        bms1 = self.create_bms(
                bms_name=random.choice(self.get_bms_nodes()),
                tor_port_vlan_tag=10,
                vn_fixture=vn2)
        lr1.verify_on_setup()
        lr2.verify_on_setup()
        self.check_vms_booted([vm11, vm12, vm2, vm3, vm4])

        self.logger.info(
            "Verify Traffic between VN-1 and VN-2 on Logical Router: lr1")
        self.verify_traffic(vm11, vm2, 'udp', sport=10000, dport=20000)
        self.logger.info(
            "Verify Traffic between VN-3 and VN-4 on Logical Router: lr2")
        self.verify_traffic(vm3, vm4, 'udp', sport=10000, dport=20000)
        self.do_ping_mesh([vm11, vm2, bms1])
        # end test_evpn_type_5_vxlan_traffic_between_vn

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_remove_vn_from_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now remove VN2 from the LR
            Traffic across the VNs should fail

        '''
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        vn3 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros',
              node_name=self.inputs.compute_names[0])
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros',
              node_name=self.inputs.compute_names[1])
        vm3 = self.create_vm(vn_fixture=vn3, image_name='cirros',
              node_name=self.inputs.compute_names[1])
        bms1 = self.create_bms(
                bms_name=random.choice(self.get_bms_nodes()),
                tor_port_vlan_tag=10,
                vn_fixture=vn1)
        lr = self.create_logical_router([vn1, vn2, vn3], vni=70001)
        lr.verify_on_setup()
        self.check_vms_booted([vm1, vm2, vm3])
        self.do_ping_mesh([vm1, vm2, vm3, bms1])

        self.logger.info(
            'Will disassociate VN2 from the LR. Traffic between the BMS and VM should fail')
        lr.remove_interface([vn2.vn_id])
        self.logger.debug(
            "Sleeping for 30 secs to allow config change to be pushed to the Spine")
        self.sleep(30)
        self.do_ping_test(vm1, vm2.vm_ip, expectation=False)
        self.do_ping_test(bms1, vm2.vm_ip, expectation=False)
        self.do_ping_test(vm3, vm2.vm_ip, expectation=False)
        self.do_ping_test(bms1, vm3.vm_ip)
        self.do_ping_test(vm3, bms1.bms_ip)
        self.do_ping_test(vm3, vm1.vm_ip)
        # end test_evpn_type_5_vm_to_bms_remove_vn_from_lr

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_remove_vni_from_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now remove the VNI from the LR
            Traffic across the VNs should continue to work

        '''
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        lr = self.create_logical_router([vn1, vn2], vni=70001)
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros',
              node_name=self.inputs.compute_names[0])
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros',
              node_name=self.inputs.compute_names[1])
        bms1 = self.create_bms(
                bms_name=random.choice(self.get_bms_nodes()),
                tor_port_vlan_tag=10,
                vn_fixture=vn2)
        lr.verify_on_setup()
        vm1.wait_till_vm_is_up()
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh([bms1, vm1, vm2])
        self.logger.info(
            'Will delete the VNI associated with the LR. Traffic between the BMS and VM should pass with the system-generated VNI')
        lr.delete_vni()
        self.logger.debug(
            "Sleeping for 30 secs to allow config change to be pushed to the Spine")
        self.sleep(30)
        self.do_ping_mesh([bms1, vm1, vm2])
        # end test_evpn_type_5_vm_to_bms_remove_vni_from_lr

    #Dont think changing RT is supported, Believe RT can only be specified during create and cannot be updated
    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_add_rt_to_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now add a new RT to the LR
            Traffic across the VNs should continue to work

        '''
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        lr = self.create_logical_router([vn1, vn2], vni=70001)
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros',
              node_name=self.inputs.compute_names[0])
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros',
              node_name=self.inputs.compute_names[0])
        bms1 = self.create_bms(
                bms_name=random.choice(self.get_bms_nodes()),
                tor_port_vlan_tag=10,
                vn_fixture=vn2)
        lr.verify_on_setup()
        vm1.wait_till_vm_is_up()
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh([vm1, vm2, bms1])

        self.logger.info('Will add a new Route-Target to the LR.'
           'Traffic between the BMS and VM should continue to pass')
        lr.add_rt('target:64512:12345')
        self.logger.debug(
            "Sleeping for 60 secs to allow config change to be pushed to the Spine")
        self.sleep(60)
        self.do_ping_mesh([vm1, vm2, bms1])
        # end test_evpn_type_5_vm_to_bms_add_rt_to_lr
