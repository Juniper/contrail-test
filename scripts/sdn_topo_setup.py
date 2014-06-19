import os
import copy
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import fixtures
import testtools
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
   
class sdnTopoSetupFixture(fixtures.Fixture):
    def __init__(self, connections, topo):
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.connections= connections
        self.inputs= self.connections.inputs
        self.quantum_fixture= self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib= self.connections.vnc_lib
        self.logger= self.inputs.logger
        self.topo= topo
    #end __init__

    def setUp (self):
        super(sdnTopoSetupFixture, self).setUp()
    #end setUp

    def topo_setup (self, config_option='openstack', skip_verify='no', vm_memory= 4096, vms_on_single_compute= False, VmToNodeMapping=None):
        '''Take topology to be configured as input and return received & configured topology -collection 
        of dictionaries. we return received topology as some data is updated and is required for 
        reference.
        Bring up with 2G RAM to support multiple traffic streams..For scaling tests, min of 8192 is recommended.
        Available config_option for SDN topo setup
        1. 'openstack': Configures all sdn entities like VN,policy etc using Openstack API 
           a. Project: Keystone
           b. Policy:  Quantum
           c. IPAM:    Contrail API
           d. VN:      Quantum
           e. VM:      Nova
        2. 'contrail': Configures all sdn entities like VN,policy etc using Contrail API 
           a. Project: Keystone
           b. Policy:  Contrail API 
           c. IPAM:    Contrail API
           d. VN:      Contrail API 
           e. VM:      Nova
        '''
        self.result= True; self.err_msg= []; self.vm_memory= vm_memory; self.skip_verify= skip_verify
        self.public_vn_present= False; self.fvn_vm_map= False; self.fvn_fixture= None;
        self.fip_fixture= None; self.fip_fixture_dict = {};self.secgrp_fixture=None
        topo_helper_obj= topology_helper(self.topo)
        self.topo.vmc_list= topo_helper_obj.get_vmc_list()
        self.topo.policy_vn= topo_helper_obj.get_policy_vn()
        self.logger.info ("Starting setup")
        topo_steps.createProject(self)
        topo_steps.createSec_group(self,option=config_option)
        topo_steps.createServiceTemplate(self)
        topo_steps.createServiceInstance(self)
        topo_steps.createIPAM(self, option= config_option)
        topo_steps.createVN(self, option= config_option)
        topo_steps.createPolicy(self, option= config_option)
        topo_steps.attachPolicytoVN(self, option= config_option)
        #If vm to node pinning is defined then pass it on to create VM method.
        if VmToNodeMapping is not None:
            topo_steps.createVMNova(self, config_option, vms_on_single_compute, VmToNodeMapping)
        else:
            topo_steps.createVMNova(self, config_option, vms_on_single_compute)
        topo_steps.createPublicVN(self)
        topo_steps.createStaticRouteBehindVM(self)
        #prepare return data
        config_topo= {'project': self.project_fixture, 'policy': self.policy_fixt, 'vn': self.vn_fixture, 'vm': self.vm_fixture, \
                      'fip': [self.public_vn_present, self.fvn_fixture, self.fip_fixture, self.fvn_vm_map, self.fip_fixture_dict], \
                      'si': self.si_fixture, 'st': self.st_fixture,'sec_grp':self.secgrp_fixture,'ipam':self.ipam_fixture}
        if self.err_msg != []:
            self.result= False 
        return {'result':self.result, 'msg': self.err_msg, 'data': [self.topo, config_topo]}
    #end topo_setup

    def incr_fip_only_setup (self, config_option='openstack', skip_verify='no', config_topo={}):
        self.result= True; self.err_msg= []; self.skip_verify= skip_verify
        self.fvn_vm_map= False; self.fip_fixture_dict = {}
        self.config_topo= config_topo
        self.logger.info ("Starting incremental  setup")
        topo_steps.createAllocateAssociateVnFIPPools(self)
        if self.err_msg != []: self.result= False 
        return {'result':self.result, 'msg': self.err_msg, 'data': [self.topo, self.config_topo]}
    #end incr_fip_only_setup

    def sdn_topo_setup (self, config_option='openstack', skip_verify='no', vm_memory= 4096, vms_on_single_compute= False ):
        '''This is wrapper script which internally calls topo_setup to setup sdn topology based on topology.
        This wrapper is basically used to configure multiple projects and it support assigning of FIP to VM from public VN.
        '''
        topo= {}; topo_objs= {}; config_topo= {}; result= True; err_msg= []; total_vm_cnt= 0; fip_possible= False

        #If a vm to compute node mapping is defined pass it on to topo_setup()
        VmToNodeMapping = None
        if 'vm_node_map' in dir(self.topo): VmToNodeMapping = self.topo.vm_node_map
        self.public_vn_present= False; self.fvn_vm_map= False; self.fip_ip_by_vm= {}; self.fvn_fixture= None;
        self.fip_fixture= None; self.fip_fixture_dict= {}
        topo_name= self.topo.__class__
        if 'project_list' in dir(self.topo):
            self.projectList= self.topo.project_list
        else:
            self.projectList= [self.inputs.project_name]
        for project in self.projectList:
            setup_obj={}
            topo_obj= topo_name()
            #expect class topology elements to be defined under method "build_topo_<project_name>"
            topo[project]= eval("topo_obj.build_topo_"+project+"()")
            setup_obj[project]= self.useFixture(sdnTopoSetupFixture(self.connections, topo[project]))
            out= setup_obj[project].topo_setup(config_option, skip_verify, vm_memory, vms_on_single_compute,VmToNodeMapping)
            if out['result'] == True: topo_objs[project], config_topo[project]= out['data']
            total_vm_cnt= total_vm_cnt + len(config_topo[project]['vm'])
            fip_info= config_topo[project]['fip']
            #If public VN present, get the public vn and FIP fixture obj
            if fip_info[0]:
                self.public_vn_present= True
                self.fvn_fixture= fip_info[1]; self.fip_fixture= fip_info[2]
            self.logger.info ("Setup completed for project %s with result %s" %(project, out['result']))
            if out['result'] == False:
                result= False; err_msg.append(out['msg'])
        #Allocate and Associate floating IP to VM,if there is any provision to do so
        fip_possible= topo_steps.verify_fip_associate_possible(self, vm_cnt= total_vm_cnt)
        if fip_possible:
            topo_steps.allocateNassociateFIP(self, config_topo)
        if len(self.projectList) == 1 and 'admin' in self.projectList:
            setup_data= {'result': result, 'msg': err_msg, 'data': [topo_objs[self.inputs.project_name], config_topo[self.inputs.project_name], [fip_possible, self.fip_ip_by_vm]]}
        else:
            setup_data= {'result': result, 'msg': err_msg, 'data': [topo_objs, config_topo, [fip_possible, self.fip_ip_by_vm]]}
        if 'fvn_vm_map' in dir(self.topo):
            #Run incremental FIP setup as it needs access to all project info after launching VN/VMs
            #Run this setup with any project handle as the setup is run in global scope, will configure across projects and has all project fixture data
            any_proj= topo.keys()[0]
            setup_obj= self.useFixture(sdnTopoSetupFixture(self.connections, topo[any_proj]))
            out= setup_obj.incr_fip_only_setup(config_option, skip_verify, config_topo)
            if out['result'] == True: topo_objs, config_topo= out['data']
            setup_data= {'result': result, 'msg': err_msg, 'data': [topo_objs, config_topo, [fip_possible, self.fip_ip_by_vm]]}
        return setup_data

    def cleanUp(self):
        if self.inputs.fixture_cleanup == 'yes':
            super(sdnTopoSetupFixture, self).cleanUp()
        else:
            self.logger.info('Skipping sdn topology config cleanup')
    #end cleanUp

#end sdnSetupFixture
