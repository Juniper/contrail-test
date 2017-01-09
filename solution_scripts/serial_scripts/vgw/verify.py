from time import sleep
import os
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.util import get_random_name


class VerifyVgwCases():

    def verify_vgw_with_fip(self, compute_type):

        # Setup resources

        fip_pool_name = get_random_name('some-pool1')
        result = True

        vn_fixture_private = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=get_random_name('VN-Private'),
                subnets=['10.10.10.0/24']))
        # Verification of VN
        assert vn_fixture_private.verify_on_setup()
        assert self.vn_fixture_dict[0].verify_on_setup()

        # Selection of compute to launch VM and VGW to configure
        host_list = self.connections.nova_h.get_hosts()
        vgw_compute = None
        vm_compute = None
        if len(host_list) > 1:
            for key in self.vgw_vn_list:
                if key.split(":")[3] == self.vn_fixture_dict[0].vn_name:
                    vgw_compute = self.vgw_vn_list[
                        key]['host'].split("@")[1]

            if compute_type == 'same':
                vm_compute = self.inputs.host_data[vgw_compute]['name']
            else:
                host_list.remove(vgw_compute)
                vm_compute = self.inputs.host_data[host_list[0]]['name']
        else:
            vm_compute = self.inputs.host_data[host_list[0]]['name']
            vgw_compute = host_list[0]

        vm1_name = get_random_name('VGW_VM1-FIP-' + vm_compute)
        # Creation of VM and validation
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture_private.obj,
                vm_name=vm1_name,
                node_name=vm_compute))
        assert vm1_fixture.verify_on_setup()

        # FIP Pool creation and validation
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=self.vn_fixture_dict[0].vn_id))
        assert fip_fixture.verify_on_setup()

        # FIP pool association and validation
        fip_id = fip_fixture.create_and_assoc_fip(
            self.vn_fixture_dict[0].vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(
            fip_id, vm1_fixture, self.vn_fixture_dict[0])
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
            assert result

        return True
    # End verify_vgw_with_fip

    def verify_vgw_with_native_vm(self, compute_type):

        result = True

        # Verification of VN
        assert self.vn_fixture_dict[0].verify_on_setup()

        # Selection of compute to launch VM and VGW to configure
        host_list = self.connections.nova_h.get_hosts()
        vgw_compute = None
        vm_compute = None
        if len(host_list) > 1:
            for key in self.vgw_vn_list:
                if key.split(":")[3] == self.vn_fixture_dict[0].vn_name:
                    vgw_compute = self.vgw_vn_list[
                        key]['host'].split("@")[1]

            if compute_type == 'same':
                vm_compute = self.inputs.host_data[vgw_compute]['name']
            else:
                host_list.remove(vgw_compute)
                vm_compute = self.inputs.host_data[host_list[0]]['name']
        else:
            vm_compute = self.inputs.host_data[host_list[0]]['name']
            vgw_compute = host_list[0]

        vm1_name = get_random_name('VGW_VM1-Native-' + vm_compute)
        # Creation of VM and validation
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn_fixture_dict[0].obj,
                vm_name=vm1_name,
                node_name=vm_compute))
        assert vm1_fixture.verify_on_setup()

        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
            assert result

        return True
    # End verify_vgw_with_native_vm

    def verify_vgw_with_multiple_subnet(self):

        fip_pool_name = get_random_name('some-pool1')
        result = True

        vn_fixture_private = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=get_random_name('VN-Private'),
                subnets=['30.10.10.0/24']))

        # Selection of compute to launch VM and VGW to configure
        # host_list=[]
        vgw_compute = None
        vm_compute = None
        #for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['ip'])

        # Scaning the testbed config to check VGW with multple subnet
        for key in self.vgw_vn_list:
            if len(self.vgw_vn_list[key]['subnet']) > 1:
                for key1 in self.vn_fixture_dict:
                    if key.split(":")[3] == self.vn_fixture_dict[0].vn_name:
                        vn_fixture = key1
                    break
                break

        vm1_name = get_random_name('VGW_VM2')

        # Verification of VN
        assert vn_fixture_private.verify_on_setup()
        assert vn_fixture.verify_on_setup()

        # Creation of VM and validation
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture_private.obj,
                vm_name=vm1_name))
        assert vm1_fixture.verify_on_setup()

        # FIP Pool creation and validation
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=vn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        # FIP pool association and validation
        fip_id = fip_fixture.create_and_assoc_fip(
            vn_fixture.vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn_fixture)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
            assert result

        return True
    # End verify_vgw_with_multiple_subnet

    def vgw_restart_of_vgw_node(self):

        fip_pool_name = get_random_name('some-pool1')
        result = True

        vn_fixture_private = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=get_random_name('VN-Private'),
                subnets=['40.10.10.0/24']))

        # Verification of VN
        assert vn_fixture_private.verify_on_setup()
        assert self.vn_fixture_dict[0].verify_on_setup()

        # Selection of compute to launch VM and VGW to configure
        host_list = self.connections.nova_h.get_hosts()
        vgw_compute = None
        vm_compute = None
        if len(host_list) > 1:
            for key in self.vgw_vn_list:
                if key.split(":")[3] == self.vn_fixture_dict[0].vn_name:
                    vgw_compute = self.vgw_vn_list[
                        key]['host'].split("@")[1]
            host_list.remove(vgw_compute)
            vm_compute = self.inputs.host_data[host_list[0]]['name']
        else:
            vm_compute = self.inputs.host_data[host_list[0]]['name']
            vgw_compute = host_list[0]

        vm1_name = get_random_name('VGW_VM1-FIP-' + vm_compute)
        # Creation of VM and validation
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture_private.obj,
                vm_name=vm1_name,
                node_name=vm_compute))
        assert vm1_fixture.verify_on_setup()

        # FIP Pool creation and validation
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=self.vn_fixture_dict[0].vn_id))
        assert fip_fixture.verify_on_setup()

        # FIP pool association and validation
        fip_id = fip_fixture.create_and_assoc_fip(
            self.vn_fixture_dict[0].vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(
            fip_id, vm1_fixture, self.vn_fixture_dict[0])
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
            assert result

        # Restart vrouter service
        self.logger.info('Will restart compute  services now')
        self.inputs.restart_service('contrail-vrouter-agent', [vgw_compute])
        sleep(30)

        # Try ping after vrouter restart

        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s after vrouter restart failed' %
                (vm1_name))
            assert result

        return True
   
class VerifyDynamicVgwCases():
 
    def verify_dynamic_vgw_compute_ping(self):

        result = True
        host_list = []
        vgw_compute = None
        vm_compute = None
        vgw_intf = 'vgw1'
        vgw_subnets = ['11.1.1.0/24']
        route = '0.0.0.0/0'
        vgw_fq_name= 'default-domain:admin:vgwvn:vgwvn'
        vm1_name= "vgw_vm"
        host_list = self.connections.nova_h.get_hosts()
        if len(host_list) > 1:
            vm_compute = self.inputs.host_data[host_list[0]]
            vgw_compute = self.inputs.host_data[host_list[1]]
        else:
            vm_compute = self.inputs.host_data[host_list[0]]
            vgw_compute = self.inputs.host_data[host_list[0]]


        # Configure VGW
        self.logger.info("Creating VGW interface %s dynamically on %s" %(vgw_intf, vgw_compute['name']))
        self.logger.info("Configuring VGW on the Compute %s", (vgw_compute['ip']))
        cmd1 =  "export PYTHONPATH=/usr/share/pyshared/contrail_vrouter_api/gen_py/instance_service"

        vgw_args = "--oper create --interface %s --subnets %s --vrf %s --routes %s" \
                   %(vgw_intf,vgw_subnets[0],vgw_fq_name, route)
        cmd2="python /opt/contrail/utils/provision_vgw_interface.py  %s" %(vgw_args)
        cmd= cmd1 + ";" + cmd2
        output = self.inputs.run_cmd_on_server(vgw_compute['ip'], cmd,
                             vgw_compute['username'],
                             vgw_compute['password'])
        # Creating Virtual network with VGW FQ name
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=vgw_fq_name.split(":")[1],
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vgw_fq_name.split(":")[2],
                subnets=vgw_subnets))
        # Verification of VN
        assert vn_fixture.verify_on_setup()

        # Creation of VM and validation
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=vgw_fq_name.split(":")[1],
                connections=self.connections,
                vn_obj=vn_fixture.obj,
                vm_name=vm1_name,
                node_name=vm_compute['name']))

        # Verification on VM
        assert vm1_fixture.verify_on_setup()

        self.logger.info("Now trying to ping underlay compute ip %s from VM %s" %(vgw_compute['ip'],vm1_name))
        if not vm1_fixture.ping_with_certainty(vgw_compute['ip']):
            result = result and False

        # Delete VGW
        self.logger.info("Deleting VGW interface %s on %s" %(vgw_intf, vgw_compute['name']))
        vgw_args = "--oper delete --interface %s --subnets %s --vrf %s --routes %s" \
                   %(vgw_intf,vgw_subnets[0],vgw_fq_name, route)
        cmd3="python /opt/contrail/utils/provision_vgw_interface.py  %s" %(vgw_args)
        cmd= cmd1 + ";" + cmd3
        output = self.inputs.run_cmd_on_server(vgw_compute['ip'], cmd,
                             vgw_compute['username'],
                             vgw_compute['password'])
        
        if not result:
            self.logger.error(
                'Test  ping to underlay compute ip from VM %s failed' % (vm1_name))

            assert result    
                             
        return True 
