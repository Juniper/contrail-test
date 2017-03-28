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


class ECMPSolnSetup():

    def get_random_fip(self, vn):
        return vn.vn_subnets[0]['cidr'].replace(".0/24", ".100/24").split('/')[0]
    #end get_random_fip

    def setup_common_objects(self):

        self.fip_pool_name = 'some-pool1'
        self.my_fip_name = 'fip'
        self.my_fip = '30.1.1.30'
        self.dport1 = '9000'
        self.dport2 = '9001'
        self.dport3 = '9002'
        self.udp_src = unicode(8000)

        self.fvn = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_name='fvn', inputs=self.inputs, subnets=['30.1.1.0/24']))
        self.vn1 = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_name='vn1', inputs=self.inputs, subnets=['10.1.1.0/29']))
        self.vn2 = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_name='vn2', inputs=self.inputs, subnets=['20.1.1.0/29']))
        self.vn3 = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_name='vn3', inputs=self.inputs, subnets=['40.1.1.0/29']))

        self.vm1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn1.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vn1_vm1'))
        self.vm2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vn2_vm1'))
        self.vm3 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn3.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vn3_vm1'))
        self.fvn_vm1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_vm1'))
        self.fvn_vm2 = self.useFixture(
                VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_vm2'))
        self.fvn_vm3 = self.useFixture(
                VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_vm3'))
                
        assert self.fvn.verify_on_setup()
        assert self.vn1.verify_on_setup()
        assert self.vn2.verify_on_setup()
        assert self.vn3.verify_on_setup()
        self.vm1.wait_till_vm_is_up()
        self.vm2.wait_till_vm_is_up()
        self.vm3.wait_till_vm_is_up()
        self.fvn_vm1.wait_till_vm_is_up()
        self.fvn_vm2.wait_till_vm_is_up()
        self.fvn_vm3.wait_till_vm_is_up()

        all_vm_list = [self.vm1, self.vm2, self.vm3, self.fvn_vm1, self.fvn_vm2, self.fvn_vm3]
        for vm in all_vm_list:
                vm.install_pkg("Traffic")
        sleep(5)

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

        self.vmi1_id = self.vm1.tap_intf[self.vn1_fq_name]['uuid']
        self.vmi2_id = self.vm2.tap_intf[self.vn2_fq_name]['uuid']
        self.vmi3_id = self.vm3.tap_intf[self.vn3_fq_name]['uuid']

        self.fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=self.fip_pool_name, vn_id=self.fvn_id))
        assert self.fip_fixture.verify_on_setup()
        self.fvn_obj = self.vnc_lib.virtual_network_read(id=self.fvn_id)
        self.fip_pool_obj = FloatingIpPool(self.fip_pool_name, self.fvn_obj)
        self.fip_obj = FloatingIp(
            self.my_fip_name, self.fip_pool_obj, self.my_fip, True)

        # Get the project_fixture
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        # Read the project obj and set to the floating ip object.
        self.fip_obj.set_project(self.project_fixture.project_obj)

        self.vm1_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi1_id)
        self.vm2_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi2_id)
        self.vm3_intf = self.vnc_lib.virtual_machine_interface_read(
            id=self.vmi3_id)

        self.fip_obj.add_virtual_machine_interface(self.vm1_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm2_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm3_intf)

        self.vnc_lib.floating_ip_create(self.fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, self.fip_obj.fq_name)
        errmsg = "Ping to the shared Floating IP ip %s from left VM failed" % self.my_fip
        assert self.fvn_vm1.ping_with_certainty(
                self.my_fip), errmsg


