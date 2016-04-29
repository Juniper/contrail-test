from time import sleep
import os
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.util import get_random_name

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
        cmd2="python /usr/share/contrail-utils/provision_vgw_interface.py  %s" %(vgw_args)
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
        cmd3="python /usr/share/contrail-utils/provision_vgw_interface.py  %s" %(vgw_args)
        cmd= cmd1 + ";" + cmd3
        output = self.inputs.run_cmd_on_server(vgw_compute['ip'], cmd,
                             vgw_compute['username'],
                             vgw_compute['password'])
        
        if not result:
            self.logger.error(
                'Test  ping to underlay compute ip from VM %s failed' % (vm1_name))

            assert result    
                             
        return True 
