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
from floating_ip import *
from testresources import OptimisingTestSuite, TestResource

class ECMPSolnSetup( fixtures.Fixture ):
    def __init__(self, test_resource):
        super (ECMPSolnSetup, self).__init__()
        self.test_resource= test_resource
    
    def setUp(self):
        super (ECMPSolnSetup, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.inputs=self.useFixture(ContrailTestInit( self.ini_file))
        self.connections= ContrailConnections(self.inputs)
        self.quantum_fixture= self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib= self.connections.vnc_lib
        self.logger= self.inputs.logger
        self.agent_inspect= self.connections.agent_inspect
        self.cn_inspect= self.connections.cn_inspect
        self.analytics_obj=self.connections.analytics_obj
        self.agent_vn_obj= {}
        self.api_s_inspect= self.connections.api_server_inspect
        self.setup_common_objects()
        return self
    #end setUp

    def setup_common_objects(self):
        
        self.fip_pool_name= 'some-pool1'
        self.my_fip_name = 'fip'
        self.my_fip= '30.1.1.3'
        self.dport1= '9000'
        self.dport2= '9001'
        self.dport3= '9002'
        self.udp_src= unicode(8000)
     
        self.fvn= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='fvn', inputs= self.inputs, subnets=['30.1.1.0/29']))
        self.vn1= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='vn1', inputs= self.inputs, subnets=['10.1.1.0/29']))
        self.vn2= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='vn2', inputs= self.inputs, subnets=['20.1.1.0/29']))
        self.vn3= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='vn3', inputs= self.inputs, subnets=['40.1.1.0/29']))
                
        self.vm1= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn1.obj, flavor='contrail_flavor_large', image_name= 'ubuntu-traffic', vm_name= 'vn1_vm1'))
        self.vm2= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn2.obj, flavor='contrail_flavor_large', image_name= 'ubuntu-traffic', vm_name= 'vn2_vm1'))
        self.vm3= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn3.obj, flavor='contrail_flavor_large', image_name= 'ubuntu-traffic', vm_name= 'vn3_vm1'))
        self.fvn_vm1= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.fvn.obj, flavor='contrail_flavor_large', image_name= 'ubuntu-traffic', vm_name= 'fvn_vm1'))

        assert self.fvn.verify_on_setup()
        assert self.vn1.verify_on_setup()
        assert self.vn2.verify_on_setup()
        assert self.vn3.verify_on_setup()
        assert self.vm1.verify_on_setup()
        assert self.vm2.verify_on_setup()
        assert self.vm3.verify_on_setup()
        assert self.fvn_vm1.verify_on_setup()

        vm_list= [self.vm1, self.vm2, self.vm3, self.fvn_vm1]
        for vm in vm_list:
            out= self.nova_fixture.wait_till_vm_is_up( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: sleep (5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")

        self.vn1_fq_name= self.vn1.vn_fq_name
        self.vn2_fq_name= self.vn2.vn_fq_name
        self.vn3_fq_name= self.vn3.vn_fq_name
        self.fvn_fq_name= self.fvn.vn_fq_name

        self.fvn_vrf_name= self.fvn.vrf_name
        self.vn1_vrf_name= self.vn1.vrf_name
        self.vn2_vrf_name= self.vn2.vrf_name
        self.vn3_vrf_name= self.vn3.vrf_name

        self.fvn_id= self.fvn.vn_id
        self.vm1_id= self.vm1.vm_id
        self.vm2_id= self.vm2.vm_id
        self.vm3_id= self.vm3.vm_id

        self.fvn_ri_name= self.fvn.ri_name
        self.vn1_ri_name= self.vn1.ri_name
        self.vn2_ri_name= self.vn2.ri_name
        self.vn3_ri_name= self.vn3.ri_name

        self.vmi1_id=  self.vm1.tap_intf[self.vn1_fq_name]['uuid']
        self.vmi2_id=  self.vm2.tap_intf[self.vn2_fq_name]['uuid']
        self.vmi3_id=  self.vm3.tap_intf[self.vn3_fq_name]['uuid']

        self.fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
            connections= self.connections, pool_name = self.fip_pool_name, vn_id= self.fvn_id ))
        assert self.fip_fixture.verify_on_setup()
        self.fvn_obj= self.vnc_lib.virtual_network_read( id = self.fvn_id )
        self.fip_pool_obj = FloatingIpPool( self.fip_pool_name, self.fvn_obj )
        self.fip_obj = FloatingIp( self.my_fip_name, self.fip_pool_obj, self.my_fip, True)
        
        # Get the project_fixture
        self.project_fixture = self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib, project_name= self.inputs.project_name, connections=self.connections))
        # Read the project obj and set to the floating ip object.
        self.fip_obj.set_project(self.project_fixture.project_obj)
        
        self.vm1_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi1_id )
        self.vm2_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi2_id )
        self.vm3_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi3_id )

        self.fip_obj.add_virtual_machine_interface(self.vm1_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm2_intf)
        self.fip_obj.add_virtual_machine_interface(self.vm3_intf)
         
        self.vnc_lib.floating_ip_create(self.fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete,self.fip_obj.fq_name)

        fvn= self.fvn
        vn1= self.vn1
        vn2= self.vn2
        vn3= self.vn3
        vm1= self.vm1
        vm2= self.vm2
        vm3= self.vm3
        fvn_vm1= self.fvn_vm1
        my_fip= self.my_fip
        
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []

        (domain, project, vn2)= self.vn2_fq_name.split(':')
        (domain, project, fvn)= self.fvn_fq_name.split(':')
        (domain, project, vn1)= self.vn1_fq_name.split(':')  
        (domain, project, vn3)= self.vn3_fq_name.split(':')

        vm_node_ips= []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip): vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip): vm_node_ips.append(vm3.vm_node_ip)

        
        #Get the Route Entry in the control node

        for vm_node_ip in vm_node_ips:
            active_controller= None
            inspect_h1= self.agent_inspect[vm_node_ip]
            agent_xmpp_status= inspect_h1.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes':
                    active_controller= entry['controller_ip']
                    self.logger.info('Active control node from the Agent %s is %s' %(vm_node_ip, active_controller))
        sleep(5)
        route_entry= self.cn_inspect[active_controller].get_cn_route_table_entry(ri_name= self.fvn_ri_name, prefix= '30.1.1.3/32')
        self.logger.info('Route_entry in the control node is %s'%route_entry)
        result= True
        if route_entry:
            self.logger.info('Route Entry found in the Active Control-Node %s'%(active_controller))
        else:
            result= False
            assert result, 'Route Entry not found in the Active Control-Node %s'%(active_controller)

        #Get the FIP list and verify the vrf_name and address in the VMI

        fip_addr_vm1= self.vm1.chk_vmi_for_fip(self.vn1_fq_name)
        fip_addr_vm2= self.vm2.chk_vmi_for_fip(self.vn2_fq_name)
        fip_addr_vm3= self.vm3.chk_vmi_for_fip(self.vn3_fq_name)

        fip_vrf_entry_vm1= self.vm1.chk_vmi_for_vrf_entry(self.vn1_fq_name)
        fip_vrf_entry_vm2= self.vm2.chk_vmi_for_vrf_entry(self.vn2_fq_name)
        fip_vrf_entry_vm3= self.vm3.chk_vmi_for_vrf_entry(self.vn3_fq_name)

        self.logger.info('The vrf_entry on the VMI of %s is %s, on %s is %s and on %s is %s'%(self.vm1.vm_name, fip_vrf_entry_vm1, self.vm2.vm_name, fip_vrf_entry_vm2, self.vm3.vm_name, fip_vrf_entry_vm3))
        
        if all(x == self.fvn_vrf_name for x in (fip_vrf_entry_vm1, fip_vrf_entry_vm2, fip_vrf_entry_vm3)):
            self.logger.info('Correct FIP VRF Entries seen ')
        else:
            result= False
            assert result, 'Incorrect FIP VRF Entries seen'
            
        self.logger.info('The FIP address assigned to %s is %s, to %s is %s and to %s is %s'%(vm1.vm_name, fip_addr_vm1, vm2.vm_name, fip_addr_vm2, vm3.vm_name, fip_addr_vm3))
        
        if all(x == my_fip for x in (fip_addr_vm1, fip_addr_vm2, fip_addr_vm3)):
            self.logger.info('FIP Address assigned correctly ')
        else:
            result= False
            assert result, 'FIP Address assignment incorrect'

        #Check for the FIP route entry

        for vm_node_ip in vm_node_ips:
            tap_intf_list = []
            inspect_h9= self.agent_inspect[vm_node_ip]
            agent_vrf_objs= inspect_h9.get_vna_vrf_objs( domain, project, fvn )
            agent_vrf_obj= self.get_matching_vrf( agent_vrf_objs['vrf_list'],self.fvn_vrf_name)
            fvn_vrf_id9=agent_vrf_obj['ucindex']
            paths= inspect_h9.get_vna_active_route(vrf_id= fvn_vrf_id9, ip= self.my_fip, prefix='32')['path_list']
            self.logger.info('There are %s nexthops to %s on Agent %s'%(len(paths),self.my_fip, vm_node_ip))

            next_hops= inspect_h9.get_vna_active_route(vrf_id= fvn_vrf_id9, ip= self.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']
            if not next_hops:
                result= False
                assert result, 'Route not found in the Agent %s'%vm_node_ip
            else:
                self.logger.info('Route found in the Agent %s'%vm_node_ip)

            for nh in next_hops:
                label= nh['label']
                if nh['type'] == 'Tunnel':
                    destn_agent= nh['dip']
                    inspect_hh= self.agent_inspect[destn_agent]
                    agent_vrf_objs= inspect_hh.get_vna_vrf_objs( domain, project, fvn )
                    agent_vrf_obj= self.get_matching_vrf( agent_vrf_objs['vrf_list'],self.fvn_vrf_name)
                    fvn_vrf_id5=agent_vrf_obj['ucindex']
                    next_hops_in_tnl= inspect_hh.get_vna_active_route(vrf_id= fvn_vrf_id5, ip= self.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl= next_hop['itf']
                            tap_intf_list.append(tap_intf_from_tnl)
                elif nh['type'] == 'Interface':
                    tap_intf= nh['itf']
                    tap_intf_list.append(tap_intf)
                    
            agent_tap_intf_list[vm_node_ip] = tap_intf_list
        self.logger.info('The list of Tap interfaces from the agents are %s'%agent_tap_intf_list)

    #end setup_common_objects

    def tearDown(self):
       print "Tearing down resources"
       super(ECMPSolnSetup, self).cleanUp()

    def dirtied(self):
        self.test_resource.dirtied(self)

    def get_matching_vrf(self, vrf_objs, vrf_name ):
        return [ x for x in vrf_objs if x['name'] == vrf_name ][0]

class _ECMPSolnSetupResource(TestResource):
    def make(self, dependencyresource):
        base_setup= ECMPSolnSetup( self)
        base_setup.setUp()
        return base_setup
    #end make

    def clean(self, base_setup):
        print "Am cleaning up here"
        #        super(_ECMPSolnSetupResource,self).clean()
        base_setup.tearDown()
    #end

ECMPSolnSetupResource= _ECMPSolnSetupResource()

