''' This module provides utils for setting up sdn topology given the topo inputs'''
import os
import copy
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import fixtures
import topo_steps
from contrail_test_init import *
from vn_test import *
from vn_policy_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from vna_introspect_utils import *
from topo_helper import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from netaddr import *
import policy_test_helper
from svc_template_fixture import SvcTemplateFixture
from svc_instance_fixture import SvcInstanceFixture
from security_group import SecurityGroupFixture

def createProject(self, option='keystone'):
    self.logger.info ("Setup step: Creating Project")
    self.project_fixture= {}
    self.project_fixture[self.topo.project] = self.useFixture(ProjectFixture(project_name= self.topo.project, vnc_lib_h= self.vnc_lib, 
                               username= self.topo.username, password= self.topo.password,
                                   connections= self.connections, option= option))
    self.project_inputs= self.useFixture(ContrailTestInit(self.ini_file, stack_user=self.project_fixture[self.topo.project].username,
                             stack_password=self.project_fixture[self.topo.project].password,project_fq_name=['default-domain',self.topo.project]))
    self.project_connections= ContrailConnections(self.project_inputs)
    self.project_parent_fixt= self.useFixture(ProjectTestFixtureGen(self.vnc_lib, project_name = self.topo.project))
    return self
#end createProject

def createSec_group(self,option='contrail'):
    if option == 'openstack' :
       create_sg_contrail(self)
    elif option == 'contrail' :
       create_sg_contrail(self)
    else:
        self.logger.error("invalid config option %s" %option)
    return self
#end of createSec_group

def create_sg_contrail(self):
    if hasattr(self.topo,'sg_list' ):
       self.sg_uuid={}
       self.secgrp_fixture ={}
       for sg_name in self.topo.sg_list :
           result=True;msg=[]
           self.logger.info ("Setup step: Creating Security Group")
           self.secgrp_fixture[sg_name] = self.useFixture(SecurityGroupFixture(inputs=self.inputs,
                            connections=self.connections, domain_name=self.topo.domain, project_name=self.topo.project,
                            secgrp_name=sg_name, secgrp_id=None, secgrp_entries=self.topo.sg_rules[sg_name]))
           self.sg_uuid[sg_name]=self.secgrp_fixture[sg_name].secgrp_id
           if self.skip_verify == 'no':
              ret,msg=self.secgrp_fixture[sg_name].verify_on_setup()
              assert ret, "Verifications for security group is :%s failed and its error message: %s"%(sg_name,msg)
    else:
       pass
    return self
#end of create_sg_contrail


def createPolicy(self, option= 'openstack'):
    if option == 'openstack':
        createPolicyOpenstack(self)
    elif option == 'contrail':
        createPolicyContrail(self)
    else:
        self.logger.error("invalid config option %s" %option)
    return self
#end createPolicy

def createPolicyOpenstack(self, option= 'openstack'):
    self.logger.info ("Setup step: Creating Policies")
    self.policy_fixt= {}; self.conf_policy_objs= {}; track_created_pol= []
    for vn in self.topo.vnet_list:
        self.conf_policy_objs[vn]= []
        for policy_name in self.topo.vn_policy[vn]:
	    self.policy_fixt[policy_name]= self.useFixture( PolicyFixture( policy_name= policy_name,
	        rules_list= self.topo.rules[policy_name], inputs= self.project_inputs, connections= self.project_connections ))
	 
	    self.conf_policy_objs[vn].append( self.policy_fixt[policy_name].policy_obj )
	    track_created_pol.append(policy_name)
            if self.skip_verify == 'no':
	        ret= self.policy_fixt[policy_name].verify_on_setup()
	        if ret['result'] == False:
                    self.logger.error ("Policy %s verification failed after setup" %policy_name)
                    assert ret['result'], ret['msg']

    print "Creating policies not assigned to VN's"
    d= [p for p in self.topo.policy_list if p not in track_created_pol]
    to_be_created_pol= (p for p in d if d)
    for policy_name in to_be_created_pol:
        self.policy_fixt[policy_name]= self.useFixture( PolicyFixture( policy_name= policy_name,
	    rules_list= self.topo.rules[policy_name], inputs= self.project_inputs, connections= self.project_connections ))
    return self
#end createPolicyOpenstack

def createPolicyContrail(self):
    self.logger.info ("Setup step: Creating Policies")
    self.policy_fixt= {}; self.conf_policy_objs= {}; track_created_pol= []
    for vn in self.topo.vnet_list:
        self.conf_policy_objs[vn]= []
        for policy_name in self.topo.vn_policy[vn]:
            self.policy_fixt[policy_name]= self.useFixture( NetworkPolicyTestFixtureGen(self.vnc_lib, network_policy_name = policy_name, 
                parent_fixt = self.project_parent_fixt, network_policy_entries=PolicyEntriesType(self.topo.rules[policy_name])))
            policy_read= self.vnc_lib.network_policy_read(id=str(self.policy_fixt[policy_name]._obj.uuid))
            if not policy_read:
                self.logger.error( "Policy %s read on API server failed" %policy_name)
                assert False, "Policy %s read failed on API server" %policy_name
            self.conf_policy_objs[vn].append( self.policy_fixt[policy_name]._obj )
            track_created_pol.append(policy_name)
            #if self.skip_verify == 'no':
            #    ret= self.policy_fixt[policy_name].verify_on_setup()
            #    if ret['result'] == False: self.err_msg.append(ret['msg'])

    print "Creating policies not assigned to VN's"
    d= [p for p in self.topo.policy_list if p not in track_created_pol]
    to_be_created_pol= (p for p in d if d)
    for policy_name in to_be_created_pol:
        self.policy_fixt[policy_name]= self.useFixture( NetworkPolicyTestFixtureGen(self.vnc_lib, network_policy_name = policy_name,
            parent_fixt = self.project_parent_fixt, network_policy_entries=PolicyEntriesType(self.topo.rules[policy_name])))
        policy_read= self.vnc_lib.network_policy_read(id=str(self.policy_fixt[policy_name]._obj.uuid))
        if not policy_read:
            self.logger.error( "Policy:%s read on API server failed" %policy_name)
            assert False, "Policy %s read failed on API server" %policy_name
    return self
#end createPolicyContrail

def createIPAM(self, option= 'openstack'):
    self.logger.info ("Setup step: Creating IPAM's")
    track_created_ipam= []; self.ipam_fixture= {}; self.conf_ipam_objs= {}
    default_ipam_name= self.topo.project+"-default-ipam"
    if 'vn_ipams' in dir(self.topo):
        print "topology has IPAM specified, need to create for each VN"
        for vn in self.topo.vnet_list:
            self.conf_ipam_objs[vn]= []
            if vn in self.topo.vn_ipams:
                ipam_name= self.topo.vn_ipams[vn]
            else:
                ipam_name= default_ipam_name
            if ipam_name in track_created_ipam:
                if option == 'contrail':
                    self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].obj
                else:
                    self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].fq_name
                continue
            print "creating IPAM %s" %ipam_name
            self.ipam_fixture[ipam_name]=self.useFixture( IPAMFixture(project_obj= self.project_fixture[self.topo.project], name=ipam_name))
            if self.skip_verify == 'no':
                assert self.ipam_fixture[ipam_name].verify_on_setup(), "verification of IPAM:%s failed"%ipam_name
            track_created_ipam.append(ipam_name)
            if option == 'contrail':
                self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].obj
            else:
                self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].fq_name
    else:
        ipam_name= default_ipam_name
        print "creating project default IPAM %s" %ipam_name
        self.ipam_fixture[ipam_name]=self.useFixture( IPAMFixture(project_obj= self.project_fixture[self.topo.project], name=ipam_name))
        if self.skip_verify == 'no':
            assert self.ipam_fixture[ipam_name].verify_on_setup(), "verification of IPAM:%s failed"%ipam_name     
        for vn in self.topo.vnet_list:
            if option == 'contrail':
                self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].obj
            else:            
       	        self.conf_ipam_objs[vn]= self.ipam_fixture[ipam_name].fq_name 
    return self
#end createIPAM

def createVN_Policy(self, option= 'openstack'):
    if option == 'openstack':
        createVN_Policy_OpenStack(self)
    elif option == 'contrail':
        createVN_Policy_Contrail(self)
    else:
        self.logger.error("invalid config option %s" %option)
    return self
#end createVN_Policy

def createVN(self,option= 'openstack'):
    if option == 'openstack':
        createVNOpenStack(self)
    elif option == 'contrail':
        createVNOpenStack(self)
        #createVNContrail(self)
    else:
        self.logger.error("invalid config option %s" %option)
    return self
#end createVN

def createVNOpenStack(self):
    self.logger.info ("Setup step: Creating VN's")
    self.vn_fixture= {}; self.vn_of_cn= {};
    for vn in self.topo.vnet_list:
        self.vn_fixture[vn]= self.useFixture(VNFixture(project_name= self.topo.project,
            connections= self.project_connections, vn_name= vn, inputs= self.project_inputs, subnets= self.topo.vn_nets[vn],
                 ipam_fq_name= self.conf_ipam_objs[vn]))
        if self.skip_verify == 'no':
            ret=self.vn_fixture[vn].verify_on_setup()
            assert ret, "One or more verifications for VN:%s failed"%vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]]= []
    return self
#end create_VN_only_OpenStack

def attachPolicytoVN(self,option= 'openstack'):
    self.vn_policy_fixture={}
    for vn in self.topo.vnet_list:
        self.vn_policy_fixture[vn]=self.useFixture(VN_Policy_Fixture(connections= self.project_connections,vn_name=vn,policy_obj=self.conf_policy_objs,vn_obj=self.vn_fixture,topo=self.topo,project_name=self.topo.project))
        if self.skip_verify == 'no':
           ret=self.vn_fixture[vn].verify_on_setup()
           assert ret, "One or more verifications for VN:%s failed"%vn
           for policy_name in self.topo.vn_policy[vn] :
               ret= self.policy_fixt[policy_name].verify_on_setup()
               if ret['result'] == False:
                  self.logger.error ("Policy %s verification failed after setup" %policy_name)
                  assert ret['result'], ret['msg']
    return self
#end attachPolicytoVN

def createVN_Policy_OpenStack(self):
    self.logger.info ("Setup step: Creating VN's")
    self.vn_fixture= {}; self.vn_of_cn= {};
    for vn in self.topo.vnet_list:
        self.vn_fixture[vn]= self.useFixture(VNFixture(project_name= self.topo.project,
	    connections= self.project_connections, vn_name= vn, inputs= self.project_inputs, subnets= self.topo.vn_nets[vn],
                policy_objs= self.conf_policy_objs[vn], ipam_fq_name= self.conf_ipam_objs[vn]))
        if self.skip_verify == 'no':
            ret=self.vn_fixture[vn].verify_on_setup()
            assert ret, "One or more verifications for VN:%s failed"%vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]]= []
    return self
#end createVNOpenStack

def createVN_Policy_Contrail(self):
    self.logger.info ("Setup step: Creating VN's")
    self.vn_fixture= {}; self.vn_of_cn= {};
    for vn in self.topo.vnet_list:
        ref_tuple = []
        for conf_policy in self.conf_policy_objs[vn]:
            ref_tuple.append((conf_policy, VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0))))
            for ipam_info in self.topo.vn_nets[vn]:
                ipam_info= list(ipam_info)
                ipam_info[0]= self.conf_ipam_objs[vn]
                ipam_info= tuple(ipam_info)
            self.vn_fixture[vn]= self.useFixture( VirtualNetworkTestFixtureGen(self.vnc_lib, virtual_network_name = vn,
                parent_fixt=self.project_parent_fixt,id_perms=IdPermsType(enable=True),network_policy_ref_infos=ref_tuple,network_ipam_ref_infos=[ipam_info]))
            vn_read = self.vnc_lib.virtual_network_read(id=str(self.vn_fixture[vn]._obj.uuid))
            if not vn_read:
                self.logger.error( "VN %s read on API server failed" %vn)
                assert False, "VN:%s read failed on API server" %vn
    # Initialize compute's VN list
    for cn in self.inputs.compute_names:
        self.vn_of_cn[self.inputs.compute_info[cn]]= []
    return self
#end createVNContrail

def createVMNova(self, option= 'openstack', vms_on_single_compute= False, VmToNodeMapping=None):
    self.logger.info ("Setup step: Creating VM's")
    sec_gp=[]
    self.vm_fixture= {}; host_list=[]
    vm_image_name= 'ubuntu-traffic'
    for host in self.inputs.compute_ips: host_list.append(self.inputs.host_data[host]['name'])

    for vm in self.topo.vmc_list:
        if option == 'contrail':
            vn_read= self.vnc_lib.virtual_network_read(id=str(self.vn_fixture[self.topo.vn_of_vm[vm]]._obj.uuid))
            vn_obj= self.quantum_fixture.get_vn_obj_if_present(vn_read.name, project_name= self.topo.project)
        else:
            vn_obj= self.vn_fixture[self.topo.vn_of_vm[vm]].obj
        if hasattr(self.topo,'sg_of_vm') :
           sg=self.topo.sg_of_vm[vm]
           sec_gp=[self.sg_uuid[sg]]
        else:
           pass
        if vms_on_single_compute:
            self.vm_fixture[vm]= self.useFixture(VMFixture(project_name= self.topo.project,
                connections= self.project_connections, vn_obj= vn_obj, ram= self.vm_memory,
                    image_name= vm_image_name, vm_name= vm,sg_ids=sec_gp, node_name= host_list[0]))
        else:
            #If vm is pinned to a node get the node name from node IP and pass it on to VM creation method.
            if VmToNodeMapping is not None:
                IpToNodeName = self.inputs.host_data[VmToNodeMapping[vm]]['name']
                self.vm_fixture[vm]= self.useFixture(VMFixture(project_name= self.topo.project,
                connections= self.project_connections, vn_obj= vn_obj, ram= self.vm_memory,
                image_name= vm_image_name, vm_name= vm, sg_ids=sec_gp, node_name=IpToNodeName))
            else:
                self.vm_fixture[vm]= self.useFixture(VMFixture(project_name= self.topo.project,
                connections= self.project_connections, vn_obj= vn_obj, ram= self.vm_memory,
                image_name= vm_image_name,sg_ids=sec_gp, vm_name= vm))

    # added here 30 seconds sleep
    #import time; time.sleep(30)
    self.logger.info("Setup step: Verify VM status and install Traffic package... ")
    for vm in self.topo.vmc_list:
        if self.skip_verify == 'no':
            vm_verify_out= self.vm_fixture[vm].verify_on_setup()
            if vm_verify_out == False:
                m= "on compute %s - vm %s verify failed after setup" %(self.vm_fixture[vm].vm_node_ip,
                   self.vm_fixture[vm].vm_name); self.err_msg.append(m)
                assert vm_verify_out, self.err_msg 
        else:
            # Even if vm verify is set to skip, run minimum needed verifications..
            vm_verify_out= self.vm_fixture[vm].mini_verify_on_setup()
            if vm_verify_out == False:
                m= "%s - mini_vm_verify in agent after setup failed" %self.vm_fixture[vm].vm_node_ip; self.err_msg.append(m)
                assert vm_verify_out, self.err_msg

        vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm_fixture[vm].vm_obj)]['host_ip']
        self.vn_of_cn[vm_node_ip].append(self.topo.vn_of_vm[vm])

        # In some less powerful computes, VM takes more time to come up.. including retry...
        # each call to wait_till_vm_is_up inturn includes 20 retries with 5s sleep.
        retry= 0
        while True:
            out= self.nova_fixture.wait_till_vm_is_up( self.vm_fixture[vm].vm_obj )
            retry += 1
            if out == True or retry > 2: break
        if out == False:
            assert out, "VM %s failed to come up in node %s" %(vm, vm_node_ip)
        if vm_image_name == 'ubuntu-traffic': self.vm_fixture[vm].install_pkg("Traffic")

    # Add compute's VN list to topology object based on VM creation
    self.topo.__dict__['vn_of_cn']= self.vn_of_cn
    return self
#end createVMNova

def createPublicVN(self):
    if 'public_vn' in dir(self.topo):
        fip_pool_name= self.inputs.fip_pool_name
        fvn_name= self.topo.public_vn
        fip_subnets= [self.inputs.fip_pool]
        mx_rt= self.inputs.mx_rt
        self.fvn_fixture= self.useFixture(VNFixture(project_name= self.topo.project, connections= self.project_connections, vn_name=fvn_name, inputs= self.project_inputs,
            subnets= fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
        assert self.fvn_fixture.verify_on_setup()
        self.logger.info('created public VN:%s' %fvn_name)        
        self.fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.topo.project, inputs = self.project_inputs, connections= self.project_connections,
            pool_name = fip_pool_name, vn_id= self.fvn_fixture.vn_id ))
        assert self.fip_fixture.verify_on_setup()
        self.logger.info('created FIP Pool:%s under Project:%s' %(fip_pool_name, self.topo.project))  
        self.public_vn_present= True
    return self
#end createPublicVN

def verifySystemPolicy(self):
    result,err_msg=policy_test_helper.comp_rules_from_policy_to_system(self)
    self.result=result
    if err_msg :
       self.err_msg=err_msg
    else:
       self.err_msg=[] 
    return self.result,self.err_msg

def verify_fip_associate_possible(self, vm_cnt):
    self.cn_inspect= self.connections.cn_inspect
    if not self.public_vn_present:
        return False

    if len(self.inputs.ext_routers) >= 1:
        router_name= self.inputs.ext_routers[0][0]
        router_ip= self.inputs.ext_routers[0][1]
        for host in self.inputs.bgp_ips:
            # Verify the connection between all control nodes and MX(if present)
            cn_bgp_entry=self.cn_inspect[host].get_cn_bgp_neigh_entry()
            if type(cn_bgp_entry) == type(dict()):
                if cn_bgp_entry['peer_address'] == router_ip:
                    if cn_bgp_entry['state'] != 'Established':
                        return False
            else:
                for entry in cn_bgp_entry:
                    if entry ['peer_address'] == router_ip:
                        if entry ['state'] != 'Established':
                            return False
    else:
        self.logger.info('No MX connectivity exists for this setup, we can use normal way to pump traffic')
        return False
    fip_pool= IPNetwork(self.inputs.fip_pool)
    if fip_pool.size <= 3:
        self.logger.info('FIP pool is not sufficient to allocate FIPs to all VM')
        return False
    if vm_cnt <= (fip_pool.size - 3):
        self.logger.info('FIP pool is sufficient to allocate FIPs to all VM')
        return True
    else:
        self.logger.info('FIP pool is not sufficient to allocate FIPs to all VM')
        return False
#end verify_fip_associate_possible

def allocateNassociateFIP(self, config_topo):
    self.fip_ip_by_vm= {}
    for project in self.projectList:
        self.logger.info( "Share public-pool with project:%s" %project )
        pool_share = self.fip_fixture.assoc_project( self.fip_fixture, project )
        self.addCleanup( self.fip_fixture.deassoc_project, self.fip_fixture, project )
        for vmfixt in config_topo[project]['vm']:
            fip_id= self.fip_fixture.create_and_assoc_fip( self.fvn_fixture.vn_id, config_topo[project]['vm'][vmfixt].vm_id )
            assert self.fip_fixture.verify_fip( fip_id, config_topo[project]['vm'][vmfixt], self.fvn_fixture )
            self.fip_ip_by_vm[vmfixt]= config_topo[project]['vm'][vmfixt].chk_vmi_for_fip( vn_fq_name= self.fvn_fixture.vn_fq_name )
            self.addCleanup( self.fip_fixture.disassoc_and_delete_fip, fip_id )    
    return self
#end allocateNassociateFIP

def createStaticRouteBehindVM(self):
    try:
        self.topo.vm_static_route
    except AttributeError:
        return self
    import analytics_performance_tests
    obj = analytics_performance_tests.AnalyticsTestPerformance()
    obj.setUp()
    for vm_name in self.topo.vm_static_route:
        prefix=self.topo.vm_static_route[vm_name]
        vm_uuid=self.vm_fixture[vm_name].vm_id
        vm_ip=self.vm_fixture[vm_name].vm_ip
        # vmi_id = tap_interface in vm fixture
        vmi_id=self.vm_fixture[vm_name].tap_interface
        # get uuid from fqn tap_interface
        vmi_id= vmi_id.split(':')[2]
        vm_route_table_name="%s_rt" % vm_name
        self.logger.info("Provisioning static route %s behind vm - %s in project %s." %(prefix, vm_name, self.topo.project))
        obj.provision_static_route(prefix = prefix, tenant_name= self.topo.project,
                                virtual_machine_interface_id=vmi_id, route_table_name=vm_route_table_name,
                                user= self.topo.username, password=self.topo.password)
    return self
#end createStaticRouteBehindVM

def createServiceTemplate(self):
    try:
        self.logger.info ("Setup step: Creating Service Templates")
        self.st_fixture = {}
        for st_name in self.topo.st_list:
            self.st_fixture[st_name] = self.useFixture(SvcTemplateFixture(
                connections=self.project_connections, inputs=self.project_inputs, domain_name=self.topo.domain,
                st_name=st_name, svc_img_name=self.topo.st_params[st_name]['svc_img_name'], svc_type=self.topo.st_params[st_name]['svc_type'],
                if_list=self.topo.st_params[st_name]['if_list'], svc_mode=self.topo.st_params[st_name]['svc_mode'], svc_scaling= self.topo.st_params[st_name]['svc_scaling'], flavor= self.topo.st_params[st_name]['flavor'], ordered_interfaces= self.topo.st_params[st_name]['ordered_interfaces']))
            assert self.st_fixture[st_name].verify_on_setup()
    except (NameError, AttributeError):
        self.logger.info ("Not Creating Service Templates, as its not defined in topology")
    return self
#end createServiceTemplate

def createServiceInstance(self):
    try:
        self.logger.info ("Setup step: Creating Service Instances")
        self.si_fixture = {}
        for si_name in self.topo.si_list:
            self.si_fixture[si_name] = self.useFixture(SvcInstanceFixture(
                connections=self.project_connections, inputs=self.project_inputs,
                domain_name=self.topo.domain, project_name=self.topo.project, si_name=si_name,
                svc_template=self.st_fixture[self.topo.si_params[si_name]['svc_template']].st_obj, if_list=self.topo.si_params[si_name]['if_list'],
                left_vn_name=self.topo.si_params[si_name]['left_vn'] ))
            self.si_fixture[si_name].verify_on_setup()
    except (NameError, AttributeError):
        self.logger.info ("Not Creating Service Instances, as its not defined in topology")
    return self
#end createServiceInstance

def allocNassocFIP(self):
    for vn_name in self.topo.fvn_vm_map:
        for index in range(len(self.topo.fvn_vm_map[vn_name])):
            assigned_fip = self.vm_fixture[self.topo.fvn_vm_map[vn_name][index]].chk_vmi_for_fip(vn_fq_name = self.vn_fixture[vn_name].vn_fq_name)
            if assigned_fip == None:
                self.logger.info('Allocating and associating FIP from %s VN pool to %s VM' %(vn_name, self.topo.fvn_vm_map[vn_name][index]))
                fip_id= self.fip_fixture_dict[vn_name].create_and_assoc_fip(self.vn_fixture[vn_name].vn_id,
                                                                            self.vm_fixture[self.topo.fvn_vm_map[vn_name][index]].vm_id)
                assert self.fip_fixture_dict[vn_name].verify_fip(fip_id, self.vm_fixture[self.topo.fvn_vm_map[vn_name][index]],
                                                                 self.vn_fixture[vn_name])
                self.logger.info('alloc&assoc FIP %s' %(fip_id))
                #self.fip_ip_by_vm[self.vm_fixture[self.topo.fvn_vm_map[vn_name][index]]]= self.vm_fixture[self.topo.fvn_vm_map[vn_name][index]].chk_vmi_for_fip(vn_fq_name= self.vn_fixture[vn_name].vn_fq_name)
                self.addCleanup(self.fip_fixture_dict[vn_name].deassoc_project, self.fip_fixture_dict[vn_name], self.topo.project)
                self.addCleanup(self.fip_fixture_dict[vn_name].disassoc_and_delete_fip, fip_id)
    return self
#end allocNassocFIP

def createAllocateAssociateVnFIPPools(self):
    if 'fvn_vm_map' in dir(self.topo):
        index=0
        for vn_name in self.topo.fvn_vm_map:
            index = index+1
            fip_pool_name = 'FIP_pool' + str(index)
            self.fip_fixture_dict[vn_name]= self.useFixture(FloatingIPFixture( project_name= self.topo.project, inputs = self.project_inputs,
                                                                 connections= self.project_connections, pool_name = fip_pool_name,
                                                                 vn_id= self.vn_fixture[vn_name].vn_id ))
            assert self.fip_fixture_dict[vn_name].verify_on_setup()
            self.logger.info('created FIP Pool:%s in Virtual Network:%s under Project:%s' %(fip_pool_name, self.fip_fixture_dict[vn_name].pub_vn_name,
                                                                                            self.topo.project))
        self.fvn_vm_map= True
        allocNassocFIP(self)
    return self
#end createAllocateAssociateVnFIPPools

if __name__ == '__main__':
    ''' Unit test to invoke sdn topo setup utils.. '''

# end __main__
