from builtins import str
from builtins import object
import fixtures
import testtools
import os
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from floating_ip import *
from testresources import OptimisingTestSuite, TestResource


class ECMPSolnSetup(object):

    def get_random_fip(self, vn):
        return vn.vn_subnets[0]['cidr'].replace(".0/24", ".100/24").split('/')[0]
    #end get_random_fip

    def setup_common_objects(self):

        self.fip_pool_name = 'some-pool1'
        self.my_fip_name = 'fip'
        self.dport1 = '9000'
        self.dport2 = '9001'
        self.dport3 = '9002'
        self.udp_src = str(8000)

        self.fvn = self.create_vn(vn_name=get_random_name('fvn'))
        self.vn1 = self.create_vn(vn_name=get_random_name('vn1'))
        self.vn2 = self.create_vn(vn_name=get_random_name('vn2'))
        self.vn3 = self.create_vn(vn_name=get_random_name('vn3'))
        self.vm1 = self.create_vm(vn_fixture=self.vn1,
            image_name='cirros-traffic', vm_name=get_random_name('vn1_vm1'))
        self.vm2 = self.create_vm(vn_fixture=self.vn2,
            image_name='cirros-traffic', vm_name=get_random_name('vn2_vm1'))
        self.vm3 = self.create_vm(vn_fixture=self.vn3,
            image_name='cirros-traffic', vm_name=get_random_name('vn3_vm1'))
        self.fvn_vm1 = self.create_vm(vn_fixture=self.fvn,
            image_name='cirros-traffic', vm_name=get_random_name('fvn_vm1'))
        self.fvn_vm2 = self.create_vm(vn_fixture=self.fvn,
            image_name='cirros-traffic', vm_name=get_random_name('fvn_vm2'))
        self.fvn_vm3 = self.create_vm(vn_fixture=self.fvn,
            image_name='cirros-traffic', vm_name=get_random_name('fvn_vm3'))
        self.vn1_fq_name = self.vn1.vn_fq_name
        self.vn2_fq_name = self.vn2.vn_fq_name
        self.vn3_fq_name = self.vn3.vn_fq_name
        self.fvn_fq_name = self.fvn.vn_fq_name

        self.fvn_vrf_name = self.fvn.vrf_name
        self.vn1_vrf_name = self.vn1.vrf_name
        self.vn2_vrf_name = self.vn2.vrf_name
        self.vn3_vrf_name = self.vn3.vrf_name

        self.fvn_id = self.fvn.vn_id
        self.vm1_id = self.vm1.vm_id
        self.vm2_id = self.vm2.vm_id
        self.vm3_id = self.vm3.vm_id

        self.fvn_ri_name = self.fvn.ri_name
        self.vn1_ri_name = self.vn1.ri_name
        self.vn2_ri_name = self.vn2.ri_name
        self.vn3_ri_name = self.vn3.ri_name

        self.fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=self.fip_pool_name, vn_id=self.fvn_id))
        assert self.fip_fixture.verify_on_setup()
        self.fip_pool_obj = self.fip_fixture.fip_pool_obj
        self.fip_obj = FloatingIp(self.my_fip_name, self.fip_pool_obj, floating_ip_is_virtual_ip=True)

        self.vmi1_id = self.vm1.get_vmi_id(self.vn1_fq_name)
        self.vmi2_id = self.vm2.get_vmi_id(self.vn2_fq_name)
        self.vmi3_id = self.vm3.get_vmi_id(self.vn3_fq_name)

        self.vm1_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi1_id)
        self.vm2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi2_id)
        self.vm3_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi3_id)

        self.fip_obj.add_virtual_machine_interface(self.vm1_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm2_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm3_intf)

        self.fip_obj.set_project(self.project.project_obj)
        fip = self.vnc_lib.floating_ip_create(self.fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, self.fip_obj.fq_name)
        fip_obj = self.vnc_lib.floating_ip_read(id=fip)
        self.my_fip = fip_obj.get_floating_ip_address()

        self.vm1.wait_till_vm_is_up()
        self.vm2.wait_till_vm_is_up()
        self.vm3.wait_till_vm_is_up()
        self.fvn_vm1.wait_till_vm_is_up()
        self.fvn_vm2.wait_till_vm_is_up()
        self.fvn_vm3.wait_till_vm_is_up()

        errmsg = "Ping to the shared Floating IP ip %s from left VM failed" % self.my_fip
        assert self.fvn_vm1.ping_with_certainty(
                self.my_fip), errmsg
