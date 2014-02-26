import time
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
from policy_test import *
from floating_ip import *
from testresources import OptimisingTestSuite, TestResource 

class SolnSetup( fixtures.Fixture ):
    def __init__(self,test_resource):
        super (SolnSetup, self).__init__()
        self.test_resource= test_resource

    def setUp(self):
        super (SolnSetup, self).setUp()
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
        self.setup_common_objects()
        return self
    #end setUp

    def setup_common_objects(self):
	(self.vn1_name, self.vn1_subnets)= ("vn1", ["192.168.3.0/24"])
        (self.vn2_name, self.vn2_subnets)= ("vn2", ["192.168.4.0/24"])
        (self.vn11_name, self.vn11_subnets)= ("vn11", ["192.168.1.0/24"])
        (self.vn22_name, self.vn22_subnets)= ("vn22", ["192.168.2.0/24"])
        (self.fip_vn_name, self.fip_vn_subnets)= ("fip_vn", ['200.1.1.0/24'])
        (self.vn11_vm1_name, self.vn11_vm2_name,self.vn11_vm3_name)=( 'vn11_vm1', 'vn11_vm2','vn11_vm3')
	(self.vn1_vm1_name,self.vn2_vm2_name) = ( 'vn1_vm1','vn2_vm2')
        self.vn22_vm1_name= 'vn22_vm1'
        self.vn22_vm2_name= 'vn22_vm2'
        self.fvn_vm1_name= 'fvn_vm1'

        # Configure 5 VNs, 2 of them vn1 and vn2 for checking service chaining feature 
        self.vn11_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections, inputs= self.inputs, vn_name= self.vn11_name, subnets= self.vn11_subnets))
        self.vn22_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections, inputs= self.inputs, vn_name= self.vn22_name, subnets= self.vn22_subnets))
        self.fvn_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections, inputs= self.inputs, vn_name= self.fip_vn_name, subnets= self.fip_vn_subnets))
	self.vn1_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections, inputs= self.inputs, vn_name= self.vn1_name, subnets= self.vn1_subnets))
        self.vn2_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections, inputs= self.inputs, vn_name= self.vn2_name, subnets= self.vn2_subnets))
        # Configure 3 VMs in VN1, 2 VM in VN2, and 1 VM in FVN
        self.vn11_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn11_fixture.obj, vm_name= self.vn11_vm1_name,image_name='ubuntu'))
        self.vn11_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn11_fixture.obj, vm_name= self.vn11_vm2_name,image_name='ubuntu'))
	self.vn11_vm3_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn11_fixture.obj, vm_name= self.vn11_vm3_name,image_name='ubuntu'))
        self.vn22_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn22_fixture.obj, vm_name= self.vn22_vm1_name,image_name='ubuntu'))
        self.vn22_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn22_fixture.obj, vm_name= self.vn22_vm2_name,image_name='ubuntu'))
        self.fvn_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.fvn_fixture.obj, vm_name= self.fvn_vm1_name,image_name='ubuntu'))

        self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn1_fixture.obj, vm_name= self.vn1_vm1_name,image_name='ubuntu-traffic'))
	self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_obj= self.vn2_fixture.obj, vm_name= self.vn2_vm2_name, image_name='ubuntu-traffic'))	
	##### Adding Policy between vn11 and vn22  ######
   	assert self.vn11_fixture.verify_on_setup()
        assert self.vn22_fixture.verify_on_setup()	
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'any','src_ports'     : 'any',
               'dst_ports'     : 'any',
               'source_network': 'any',
               'dest_network'  : 'any',
            },
               ]
        policy_name= 'p1'

        self.policy_fixture= self.useFixture( PolicyFixture( policy_name= policy_name, rules_list= rules, inputs= self.inputs,\
            connections= self.connections))
		
	policy_fq_name = [self.policy_fixture.policy_fq_name]
        self.vn11_fixture.bind_policies( policy_fq_name,self.vn11_fixture.vn_id)
	self.addCleanup( self.vn11_fixture.unbind_policies, self.vn11_fixture.vn_id, [self.policy_fixture.policy_fq_name] )
        self.vn22_fixture.bind_policies( policy_fq_name,self.vn22_fixture.vn_id)
	self.addCleanup( self.vn22_fixture.unbind_policies, self.vn22_fixture.vn_id, [self.policy_fixture.policy_fq_name] )

	### Adding Floating ip ###
 	
	assert self.fvn_fixture.verify_on_setup()
	
	fip_pool_name= 'some-pool1'
	self.fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name, vn_id= self.fvn_fixture.vn_id ))
	
	assert self.vn11_vm1_fixture.verify_on_setup()	
	self.fip_id= self.fip_fixture.create_and_assoc_fip(self.fvn_fixture.vn_id, self.vn11_vm1_fixture.vm_id)
	self.addCleanup( self.fip_fixture.disassoc_and_delete_fip, self.fip_id)
        assert self.fip_fixture.verify_fip( self.fip_id, self.vn11_vm1_fixture, self.fvn_fixture )

	assert self.vn22_vm1_fixture.verify_on_setup()
        self.fip_id1 = self.fip_fixture.create_and_assoc_fip( self.fvn_fixture.vn_id, self.vn22_vm1_fixture.vm_id)
        assert self.fip_fixture.verify_fip( self.fip_id1, self.vn22_vm1_fixture, self.fvn_fixture)
	self.addCleanup( self.fip_fixture.disassoc_and_delete_fip, self.fip_id1)


    #end setup_common_objects

    def verify_common_objects_without_collector(self):
	assert self.vn11_fixture.verify_on_setup_without_collector()
        assert self.vn22_fixture.verify_on_setup_without_collector()
        assert self.fvn_fixture.verify_on_setup_without_collector()
        assert self.vn11_vm1_fixture.verify_on_setup()
        assert self.vn11_vm2_fixture.verify_on_setup()
	assert self.vn11_vm3_fixture.verify_on_setup()
        assert self.vn22_vm1_fixture.verify_on_setup()
        assert self.vn22_vm2_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.verify_on_setup()
	assert self.vn1_fixture.verify_on_setup_without_collector()
	assert self.vn2_fixture.verify_on_setup_without_collector()
	assert self.vn1_vm1_fixture.verify_on_setup()
	assert self.vn2_vm2_fixture.verify_on_setup()
	assert self.fip_fixture.verify_on_setup()
        return True
    
    def verify_common_objects(self):
        assert self.vn11_fixture.verify_on_setup()
        assert self.vn22_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        assert self.vn11_vm1_fixture.verify_on_setup()
        assert self.vn11_vm2_fixture.verify_on_setup()
	assert self.vn11_vm3_fixture.verify_on_setup()
        assert self.vn22_vm1_fixture.verify_on_setup()
        assert self.vn22_vm2_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.verify_on_setup()
	assert self.fip_fixture.verify_on_setup()
	return True 
    #end verify_common_objects
        
    def tearDown(self):
        print "Tearing down resources"
        super(SolnSetup, self).cleanUp()
        
    def dirtied(self):
        self.test_resource.dirtied(self)

class _SolnSetupResource(TestResource):
    def make(self, dependencyresource):
        base_setup= SolnSetup( self)
        base_setup.setUp()
        return base_setup
    #end make

    def clean(self, base_setup):
        print "Am cleaning up here"
#        super(_SolnSetupResource,self).clean()
        base_setup.tearDown()
    #end

SolnSetupResource= _SolnSetupResource()


