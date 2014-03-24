from time import sleep
import fixtures
import testtools
import os
from connections import ContrailConnections
from contrail_test_init import *
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from testresources import OptimisingTestSuite, TestResource

class VerifyEvpnCases():

    def verify_ipv6_ping_for_non_ip_communication(self,encap):

        # Setting up default encapsulation 
        self.logger.info('Deleting any Encap before continuing')
        out=self.connections.delete_vrouter_encap()
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoGRE','MPLSoUDP','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoGRE is the highest priority encap'%(config_id))
        elif (encap == 'udp'): 
            config_id=self.connections.set_vrouter_config_encap('MPLSoUDP','MPLSoGRE','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoUDP is the highest priority encap'%(config_id))
        elif (encap == 'vxlan'):
            config_id=self.connections.set_vrouter_config_encap('VXLAN','MPLSoUDP','MPLSoGRE')
            self.logger.info('Created.UUID is %s. VXLAN is the highest priority encap'%(config_id))
       
        host_list=[] 
        for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
  
        vn1_fixture= self.res.vn1_fixture
        vn2_fixture= self.res.vn2_fixture
        #vn1_vm1_fixture= self.res.vn1_vm1_fixture
        #vn1_vm2_fixture= self.res.vn1_vm2_fixture
        vm1_name= self.res.vn1_vm1_name
        vm2_name= self.res.vn1_vm2_name
        vn1_name= self.res.vn1_name
        vn1_subnets= self.res.vn1_subnets
        vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, image_name= 'ubuntu', vm_name= vm1_name,node_name= compute_1))
        vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, image_name= 'ubuntu', vm_name= vm2_name,node_name= compute_2))

        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        for i in range(0,20):
            sleep (5)
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            if vm2_ipv6 is not None:
                break
        if vm2_ipv6 is None:
            self.logger.error('Not able to get VM link local address')
            return False
        assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        return True
    # End verify_ipv6_ping_for_non_ip_communication

    def verify_ping_to_configured_ipv6_address (self,encap):
        '''Configure IPV6 address to VM. Test IPv6 ping to that address.
        '''
        result= True
        # Setting up default encapsulation 
        self.logger.info('Deleting any Encap before continuing')
        out=self.connections.delete_vrouter_encap()
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoGRE','MPLSoUDP','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoGRE is the highest priority encap'%(config_id))
        elif (encap == 'udp'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoUDP','MPLSoGRE','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoUDP is the highest priority encap'%(config_id))
        elif (encap == 'vxlan'):
            config_id=self.connections.set_vrouter_config_encap('VXLAN','MPLSoUDP','MPLSoGRE')
            self.logger.info('Created.UUID is %s. VXLAN is the highest priority encap'%(config_id))
 
        host_list=[]
        for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        vn1_vm1= '1001::1/64'
        vn1_vm2= '1001::2/64'
        vn1_fixture= self.res.vn1_fixture
        vn2_fixture= self.res.vn2_fixture
        #vn1_vm1_fixture= self.res.vn1_vm1_fixture
        #vn1_vm2_fixture= self.res.vn1_vm2_fixture
        vm1_name= self.res.vn1_vm1_name
        vm2_name= self.res.vn1_vm2_name
        vn1_name= self.res.vn1_name
        vn1_subnets= self.res.vn1_subnets
        vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, ram= '4096', image_name= 'ubuntu-traffic', vm_name= vm1_name,node_name= compute_1))
        vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, ram= '4096', image_name= 'ubuntu-traffic', vm_name= vm2_name,node_name= compute_2))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()  
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        # Waiting for VM to boots up
        sleep (60)
        cmd_to_pass1=['sudo ifconfig eth0 inet6 add %s' %(vn1_vm1)]
        vn1_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1)
        cmd_to_pass2=['sudo ifconfig eth0 inet6 add %s' %(vn1_vm2)]
        vn1_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2)
        vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm(addr_type='global')
        vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm(addr_type='global')
        assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        return True
    # End verify_ping_to_configured_ipv6_address

    def verify_epvn_with_agent_restart (self,encap):
        '''Restart the vrouter service and verify the impact on L2 route
        '''

        # Setting up default encapsulation 
        self.logger.info('Deleting any Encap before continuing')
        out=self.connections.delete_vrouter_encap()
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoGRE','MPLSoUDP','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoGRE is the highest priority encap'%(config_id))
        elif (encap == 'udp'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoUDP','MPLSoGRE','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoUDP is the highest priority encap'%(config_id))
        elif (encap == 'vxlan'):
            config_id=self.connections.set_vrouter_config_encap('VXLAN','MPLSoUDP','MPLSoGRE')
            self.logger.info('Created.UUID is %s. VXLAN is the highest priority encap'%(config_id))

        result= True
        host_list=[]
        for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        vn1_fixture= self.res.vn1_fixture
        vn2_fixture= self.res.vn2_fixture
        #vn1_vm1_fixture= self.res.vn1_vm1_fixture
        #vn1_vm2_fixture= self.res.vn1_vm2_fixture
        vm1_name= self.res.vn1_vm1_name
        vm2_name= self.res.vn1_vm2_name
        vn1_name= self.res.vn1_name
        vn1_subnets= self.res.vn1_subnets
        vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, ram= '4096', image_name= 'ubuntu-traffic', vm_name= vm1_name,node_name= compute_1))
        vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= vn1_fixture.obj, ram= '4096', image_name= 'ubuntu-traffic', vm_name= vm2_name,node_name= compute_2))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        for i in range(0,20):
            sleep (5)
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            if vm2_ipv6 is not None:
                break
        if vm2_ipv6 is None:
            self.logger.error('Not able to get VM link local address')
            return False
        #vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm()
        #vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
        self.logger.info('Checking the communication between 2 VM using ping6 to VM link local address from other VM')
        assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        self.logger.info('Will restart compute  services now')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter',[compute_ip])
        sleep(10)
        self.logger.info('Verifying L2 route and other VM verification after restart')
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        #vm1_ipv6=vn1_vm1_fixture.get_vm_ipv6_addr_from_vm()
        #vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
        for i in range(0,20):
            sleep (5)
            vm2_ipv6=vn1_vm2_fixture.get_vm_ipv6_addr_from_vm()
            if vm2_ipv6 is not None:
                break
        if vm2_ipv6 is None:
            self.logger.error('Not able to get VM link local address')
            return False
        self.logger.info('Checking the communication between 2 VM after vrouter restart')
        assert vn1_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        return True
    # End test_epvn_with_agent_restart

    def verify_epvn_l2_mode (self,encap):
        '''Restart the vrouter service and verify the impact on L2 route
        '''

        # Setting up default encapsulation 
        self.logger.info('Deleting any Encap before continuing')
        out=self.connections.delete_vrouter_encap()
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoGRE','MPLSoUDP','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoGRE is the highest priority encap'%(config_id))
        elif (encap == 'udp'):
            config_id=self.connections.set_vrouter_config_encap('MPLSoUDP','MPLSoGRE','VXLAN')
            self.logger.info('Created.UUID is %s. MPLSoUDP is the highest priority encap'%(config_id))
        elif (encap == 'vxlan'):
            config_id=self.connections.set_vrouter_config_encap('VXLAN','MPLSoUDP','MPLSoGRE')
            self.logger.info('Created.UUID is %s. VXLAN is the highest priority encap'%(config_id))

        result= True
        host_list=[]
        for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:   
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        vn1_vm1= '1001::1/64'
        vn1_vm2= '1001::2/64'
        nova_fixture= self.res.nova_fixture
        vn3_fixture= self.res.vn3_fixture
        vn4_fixture= self.res.vn4_fixture
        vn_l2_vm1_name= self.res.vn_l2_vm1_name
        vn_l2_vm2_name= self.res.vn_l2_vm2_name
        vn3_name= self.res.vn3_name
        vn4_name= self.res.vn4_name
        vn3_subnets= self.res.vn3_subnets
        vn4_subnets= self.res.vn4_subnets

        vn_l2_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_objs= [vn3_fixture.obj , vn4_fixture.obj], image_name= 'ubuntu', vm_name= vn_l2_vm1_name,node_name= compute_1))
        vn_l2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_objs= [vn3_fixture.obj , vn4_fixture.obj], image_name= 'ubuntu', vm_name= vn_l2_vm2_name,node_name= compute_2))
        
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup() 
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        self.nova_fixture.wait_till_vm_is_up( vn_l2_vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vn_l2_vm2_fixture.vm_obj )

        # Configured IPV6 address
        cmd_to_pass1=['ifconfig eth1 inet6 add %s' %(vn1_vm1)]
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True)
        cmd_to_pass2=['ifconfig eth1 inet6 add %s' %(vn1_vm2)]
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True)

        # Bring the intreface up forcefully
        cmd_to_pass3=['ifconfig eth1 1']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True)
        cmd_to_pass4=['ifconfig eth1 1']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True)
        sleep (30)
      
        vm1_ipv6=vn_l2_vm1_fixture.get_vm_ipv6_addr_from_vm(intf= 'eth1', addr_type='global')
        vm2_ipv6=vn_l2_vm2_fixture.get_vm_ipv6_addr_from_vm(intf= 'eth1', addr_type='global')
        assert vn_l2_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)

        #self.logger.info('Will restart compute  services now')
        #for compute_ip in self.inputs.compute_ips:
        #    self.inputs.restart_service('contrail-vrouter',[compute_ip])
        #sleep(10)

        # TODO
        #assert vn1_vm1_fixture.verify_on_setup()
        #assert vn1_vm2_fixture.verify_on_setup()

        #self.logger.info('Checking the communication between 2 VM after vrouter restart')
        #assert vn_l2_vm1_fixture.ping_to_ipv6(vm2_ipv6.split("/")[0],return_output=True)
        return True
    # End verify_epvn_l2_mode

