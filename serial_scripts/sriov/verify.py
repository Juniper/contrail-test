import re
import os
import time
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
        sriov_compute_list= self.get_sriov_enabled_compute_list()
        compute_1 = sriov_compute_list[0]
        compute_2 = sriov_compute_list[0]
        if len(sriov_compute_list) > 1:
            compute_1 = sriov_compute_list[0]
            compute_2 = sriov_compute_list[1]
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
                sriov_provider_network=self.get_sriov_physnets(compute_1)[0],
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

        # Configure IP address
        cmd_to_pass1 = ['ifconfig eth1 %s' % (vm1_sriov_ip)]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1 %s' % (vm2_sriov_ip)]
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        assert vm2_fixture.ping_to_ip(vm1_sriov_ip, count='15',
                                              other_opt='-I eth1')
    # End communication_between_two_sriov_vm

    def virtual_function_exhaustion_and_resue (self):
        '''
        Verify Nova can schdule VM to all the VF of a PF.
        Nova should though error when VF is exhausted.
        After clearing one VF that should be rsusable   
        '''
        result = True
        sriov_compute_list= self.get_sriov_enabled_compute_list()
        compute_1 = sriov_compute_list[0]
        compute_2 = sriov_compute_list[0]
        if len(sriov_compute_list) > 1:
            compute_1 = sriov_compute_list[0]
            compute_2 = sriov_compute_list[1]

        vm1_sriov_ip = '55.1.1.3'
        vm1_mgmt_ip  = '33.1.1.3'
        (self.vn3_name, self.vn3_subnets) = ("SRIOV-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets,))

        (self.vn1_name, self.vn1_subnets) = ("SRIOV-Test-VN1", ["55.1.1.0/24"])

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                sriov_enable=True,
                sriov_provider_network=self.get_sriov_physnets(compute_1)[0],
                sriov_vlan='200'))
        assert vn1_fixture.verify_on_setup()
        assert vn3_fixture.verify_on_setup()

        subnet1_objects = vn1_fixture.get_subnets()
        subnet2_objects = vn3_fixture.get_subnets()
        self.logger.info(
                'Exhausting all the VF avaiable for SRIOV NIC in compute %s' % (compute_1))
        total_vf=self.get_sriov_vf_number(compute_1)
        self.logger.info(
                'Creating total %s number of SRIOV VM on compute %s' % (total_vf,compute_1))

        vm_fixture_list=[]
        for x in xrange(0, total_vf):
            ports1=vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet1_objects[0]['id'], ip_address=vm1_sriov_ip, sriov=True)
            ports2=vn3_fixture.create_port(vn3_fixture.vn_id,
                    subnet_id=subnet2_objects[0]['id'],ip_address=vm1_mgmt_ip)

            sriov_vm1_name = 'SRIOV_VM-' + str(x)
            vm_fixture_list.append(self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=sriov_vm1_name,
                node_name=compute_1,
                port_ids = [ports1['id'],ports2['id']])))
            vm1_sriov_ip=self.ip_increment(vm1_sriov_ip,1)
            vm1_mgmt_ip=self.ip_increment(vm1_mgmt_ip,1)
      
            # Wait tillVM is UP 
            assert vm_fixture_list[x].wait_till_vm_is_up()
        self.logger.info(
                'Further VM launch should fail  on compute %s. Max number of VF utilized' % (compute_1))
        ports1=vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet1_objects[0]['id'], ip_address=vm1_sriov_ip, sriov=True)
        ports2=vn3_fixture.create_port(vn3_fixture.vn_id,
                    subnet_id=subnet2_objects[0]['id'],ip_address=vm1_mgmt_ip)
        
        vm_fixture_error=self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn1_fixture.obj],
                image_name='ubuntu',
                vm_name='VM-Error',
                node_name=compute_1,
                port_ids = [ports1['id'],ports2['id']]))
        assert vm_fixture_error.wait_till_vm_status(status='ERROR'), "VM Status should be in Error as all VF already in use"

        # Force delete the VM
        status=self.vm_force_delete(vm_fixture_error)
        self.remove_from_cleanups(vm_fixture_error) 
        self.logger.info(
                'Delete a VM to freeup one VF on Compute %s' % (compute_1))
        vm_fixture_list[3].cleanUp(), 'Cleanup failed VM, Check logs'
        self.remove_from_cleanups(vm_fixture_list[3])
        assert vm_fixture_list[3].verify_vm_not_in_nova()

        self.logger.info(
                'VM launch should be successful now  on compute %s. Max number of VF utilized' % (compute_1))
        vm1_sriov_ip=self.ip_increment(vm1_sriov_ip,1)
        vm1_mgmt_ip=self.ip_increment(vm1_mgmt_ip,1)
        ports1=vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet1_objects[0]['id'], ip_address=vm1_sriov_ip, sriov=True)
        ports2=vn3_fixture.create_port(vn3_fixture.vn_id,
                    subnet_id=subnet2_objects[0]['id'],ip_address=vm1_mgmt_ip)

        vm_fixture_new=self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn1_fixture.obj],
                image_name='ubuntu',
                vm_name='VM-New',
                node_name=compute_1,
                port_ids = [ports1['id'],ports2['id']]))
        assert vm_fixture_new.wait_till_vm_is_up(),"New VM failed to launch"
   
    # End virtual_function_exhaustion_and_resue

    def communication_between_two_sriov_vm_with_large_mtu (self):
        '''
        Configure two SRIOV VM in Same phynets and same VN.
        VMs are configure across compute node.
        Configure higher MTU value. 
        Verify Ping with higher packet size.  
        '''

        result = True
        sriov_compute_list= self.get_sriov_enabled_compute_list()
        compute_1 = sriov_compute_list[0]
        compute_2 = sriov_compute_list[0]
        if len(sriov_compute_list) > 1:
            compute_1 = sriov_compute_list[0]
            compute_2 = sriov_compute_list[1]
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
                sriov_provider_network=self.get_sriov_physnets(compute_1)[0],
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
   
        # Configure IP address
        cmd_to_pass1 = ['ifconfig eth1 %s' % (vm1_sriov_ip)]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1 %s' % (vm2_sriov_ip)]
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        # Configure Higher MTU value
        cmd_to_increase_mtu = ['ifconfig eth1 mtu 5000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True, timeout=60)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True, timeout=60)
        vf_in_vm1=self.get_vf_in_use(vm1_fixture,self.get_sriov_pf(compute_1),self.get_sriov_mac(vm1_fixture,'eth1'))
        vf_in_vm2=self.get_vf_in_use(vm2_fixture,self.get_sriov_pf(compute_2),self.get_sriov_mac(vm2_fixture,'eth1'))
        self.set_mtu_on_vf(vm1_fixture,self.get_sriov_pf(compute_1),vf_in_vm1,'200','5000')
        self.set_mtu_on_vf(vm2_fixture,self.get_sriov_pf(compute_2),vf_in_vm2,'200','5000')

        assert vm2_fixture.ping_to_ip(vm1_sriov_ip, count='15',
                                              other_opt='-I eth1',return_output=True,size='5000')
    # End communication_between_two_sriov_vm_with_large_mtu
