import re
import os
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from contrail_fixtures import *
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from fabric.operations import get, put


class VerifySriovCases():

    def communication_between_two_sriov_vm (self):
        '''
        Configure two SRIOV VM in Same phynets and same VN.
        VMs are configure across compute node.
        Verify the commonication over SRIOV NIC.  
        '''
        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        compute_1 = 'b7s36'
        compute_2 = 'b7s37'

        vm1_sriov_ip = '55.1.1.11'
        vm1_mgmt_ip  = '33.1.1.11'
        vm2_sriov_ip = '55.1.1.12'
        vm2_mgmt_ip  = '33.1.1.12'
        (self.vn3_name, self.vn3_subnets) = ("SRIOV-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets,))

        sriov_vm1_name = 'SRIOV_VM1'
        sriov_vm2_name = 'SRIOV_VM2'

        (self.vn1_name, self.vn1_subnets) = ("SRIOV-Test-VN1", ["55.1.1.0/24"])

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                sriov_enable=True,
                sriov_provider_network='physnet1',
                sriov_vlan='200'))
        assert vn1_fixture.verify_on_setup()
        assert vn3_fixture.verify_on_setup()

        subnet1_objects = vn1_fixture.get_subnets()
        subnet2_objects = vn3_fixture.get_subnets()
        ports1 = {}
        ports2 = {}
        ports1['subnet1'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet1_objects[0]['id'], ip_address=vm1_sriov_ip, sriov=True)
        ports1['subnet2'] = vn3_fixture.create_port(vn3_fixture.vn_id,
                    subnet_id=subnet2_objects[0]['id'],ip_address=vm1_mgmt_ip)
        ports2['subnet1'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet1_objects[0]['id'], ip_address=vm2_sriov_ip, sriov=True)
        ports2['subnet2'] = vn3_fixture.create_port(vn3_fixture.vn_id,
                    subnet_id=subnet2_objects[0]['id'],ip_address=vm2_mgmt_ip)

        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=sriov_vm1_name,
                node_name=compute_1,
                port_ids = [ports1['subnet1']['id'],ports1['subnet2']['id']]))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=sriov_vm2_name,
                node_name=compute_2,
                port_ids = [ports2['subnet1']['id'],ports2['subnet2']['id']]))


        # Wait till vm is up
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        # Bring the intreface up forcefully
        self.bringup_interface_forcefully(vm1_fixture)
        self.bringup_interface_forcefully(vm2_fixture)

        # Configure IPV6 address
        cmd_to_pass1 = ['ifconfig eth1 %s' % (vm1_sriov_ip)]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1 %s' % (vm2_sriov_ip)]
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        assert vm2_fixture.ping_to_ip(vm1_sriov_ip, count='15',
                                              other_opt='-I eth1')
    # End communication_between_two_sriov_vm

