# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Test to upgrade to new contrail version  from existing version  

import re
import time
import os
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
from contrail_fixtures import *
import unittest
import fixtures
import testtools
import traceback
from connections import ContrailConnections
from contrail_test_init import ContrailTestInit
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from floating_ip import *
from policy_test import *
from tcutils.commands import *
from fabric.context_managers import settings, hide
from tcutils.wrappers import preposttest_wrapper
from util import *
from fabric.api import run, local
from testresources import ResourcedTestCase
from upgrade_resource import SolnSetupResource
import traffic_tests
from fabric.state import output, connections
from securitygroup.config import ConfigSecGroup


class Upgrade(ResourcedTestCase, testtools.TestCase, ConfigSecGroup):
	

    resources = [('base_setup', SolnSetupResource)]
    def __init__(self,*args,**kwargs):
	testtools.TestCase.__init__(self, *args, **kwargs)
	self.res= SolnSetupResource.getResource()
	self.inputs= self.res.inputs
	self.connections= self.res.connections
	self.logger= self.res.logger
	self.nova_fixture= self.res.nova_fixture
	self.agent_inspect= self.connections.agent_inspect
	self.cn_inspect= self.connections.cn_inspect
	self.analytics_obj=self.connections.analytics_obj
	self.vnc_lib= self.connections.vnc_lib


    def __del__(self):
	print "Deleting test_with_setup now"
	SolnSetupResource.finishedWith(self.res)
 
    def setUp(self):
        super(Upgrade, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'


    def tearDown(self):
	print "Tearing down test"
	super (Upgrade, self).tearDown()
	SolnSetupResource.finishedWith(self.res)

    def runTest(self):
	pass
	#end runTest

    @preposttest_wrapper
    def test_traffic_after_upgrade(self):
	'''Test to test traffic after upgrade using previouly defined  policy and floating ip and then adding new policy to new resources
	'''	
	result = True
	assert self.res.verify_common_objects_without_collector()
	vn11_fixture = self.res.vn11_fixture
	vn11_vm1_fixture = self.res.vn11_vm1_fixture
	vn11_vm2_fixture = self.res.vn11_vm2_fixture
	vn11_vm3_fixture = self.res.vn11_vm3_fixture
	vn22_fixture = self.res.vn22_fixture
	vn22_vm1_fixture = self.res.vn22_vm1_fixture
	vn22_vm2_fixture = self.res.vn22_vm2_fixture
	fvn_fixture = self.res.fvn_fixture
	fvn_vm1_fixture = self.res.fvn_vm1_fixture
	fip_fixture = self.res.fip_fixture	
        fip_id = self.res.fip_id
	fip_id1 = self.res.fip_id1
	policy_fixture = self.res.policy_fixture

	### Add sec_grp2  allowing icmp traffic hence ping should pass ###

	self.sg2_name = 'sec_grp2'
        rule = [{'direction' : '<>',
                'protocol' : 'icmp',
                'dst_addresses': [{'subnet' : {'ip_prefix' : '192.168.1.0', 'ip_prefix_len' : 24}}],
                'dst_ports': [{'start_port' : 0, 'end_port' : -1}],
                'src_ports': [{'start_port' : 0, 'end_port' : -1}],
                'src_addresses': [{'security_group' : 'local'}],
               }]
	self.secgrp_fixture1 = self.config_sec_group(name=self.sg2_name,entries=rule)
	vn11_vm3_fixture.add_security_group(secgrp=self.sg2_name)
	vn11_vm3_fixture.verify_security_group(self.sg2_name)
		
	self.logger.info('PINGING FROM VN11_VM3 TO VN11_VM1 \n')
        if not vn11_vm3_fixture.ping_with_certainty(vn11_vm1_fixture.vm_ip):
            result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
	vn11_vm3_fixture.remove_security_group(secgrp=self.sg2_name)
	###### checking traffic using floating ip defined before upgrade  ####

        result = self.check_floatingip_traffic()
	assert result
            
	#### checking policy before upgrade ####
	
	result = self.check_policy_traffic()
	assert result

 	#########creating new resources after upgrade #####

	new_res = self.vn_add_delete()
	result = result and new_res 
        assert result

        new_res = self.vm_add_delete()
	result = result and new_res
        assert result

	#### Creating policy  for newly created vn's
	
	newvn_fixture = self.newvn_fixture
        newvn11_fixture = self.newvn11_fixture
      
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'any','src_ports'     : 'any',
               'dst_ports'     : 'any',
               'source_network': 'any',
               'dest_network'  : 'any',
            },
               ]
        policy_name= 'newpolicy'

        policy_fixture1= self.useFixture( PolicyFixture( policy_name= policy_name, rules_list= rules, inputs= self.inputs,\
            connections= self.connections))

        policy_fq_name = [policy_fixture1.policy_fq_name]
        newvn_fixture.bind_policies( policy_fq_name,newvn_fixture.vn_id)
	self.addCleanup( newvn_fixture.unbind_policies, newvn_fixture.vn_id, [policy_fixture1.policy_fq_name] )	
        newvn11_fixture.bind_policies( policy_fq_name,newvn11_fixture.vn_id)
	self.addCleanup( newvn11_fixture.unbind_policies, newvn11_fixture.vn_id, [policy_fixture1.policy_fq_name] )

        assert newvn_fixture.verify_on_setup()
        assert newvn11_fixture.verify_on_setup()

        self.logger.info("Pinging from newvn_vm1_mine to newvn11_vm1_mine by policy rule ")

        if not self.vm4_fixture.ping_with_certainty(self.vm5_fixture.vm_ip, expectation=True):
               result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
	if not self.vm5_fixture.ping_with_certainty(self.vm4_fixture.vm_ip, expectation=True):
               result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

	return result	
    #end test_traffic_after_upgrade	 
   	
    @preposttest_wrapper	
    def test_fiptraffic_before_upgrade(self):
	''' Test to create policy and floating ip rules on common resources and checking if they work fine 
	'''
	result = True
	vn11_vm1_fixture = self.res.vn11_vm1_fixture
	vn11_vm3_fixture = self.res.vn11_vm3_fixture

	
	assert self.res.verify_common_objects()
	### Adding security group to vn11_vm3 ####
	self.sg1_name = 'sec_grp1'
        rules = [{'direction' : '>',
                'protocol' : 'tcp',
                'dst_addresses': [{'subnet' : {'ip_prefix' : '192.168.1.0', 'ip_prefix_len' : 24}},
                                  {'subnet' : {'ip_prefix' : '192.168.2.0', 'ip_prefix_len' : 24}}],
                'dst_ports': [{'start_port' : 0, 'end_port' : -1}],
                'src_ports': [{'start_port' : 0, 'end_port' : -1}],
                'src_addresses': [{'security_group' : 'local'}],
               }]

        self.secgrp_fixture = self.config_sec_group(name=self.sg1_name,entries=rules)
        self.logger.info("Adding the sec groups to the VM's")
        vn11_vm3_fixture.add_security_group(secgrp=self.sg1_name)
	vn11_vm3_fixture.verify_security_group(self.sg1_name)
        self.logger.info("Remove the default sec group form the vn11_vm3's")
        vn11_vm3_fixture.remove_security_group(secgrp='default')
		
	### vn11_vm3 is in sec_grp1 allowing only tcp traffic so ping should fail ###
	self.logger.info("test for SECurity Group ")
	if  vn11_vm3_fixture.ping_to_ip(vn11_vm1_fixture.vm_ip):
	    result = result and False
            self.logger.error('Test to ping between VMs expected to FAIL problem with security group \n')
	    assert result
	self.logger.info("Test to ping from vn11_vm3 was expected to fail since security allows only 'tcp' traffic")
	vn11_vm3_fixture.remove_security_group(secgrp=self.sg1_name)
	### checking traffic between common resource vm's by floating ip rule ###
       
	result = self.check_floatingip_traffic()
	assert result 

	##### Checking  Policy between vn11 and vn22  ######
	
	result = self.check_policy_traffic()
	assert result

	return result
    #end test_fiptraffic_before_upgrade	
	
    def check_policy_traffic(self) :
	
	result = True
	vn11_vm2_fixture = self.res.vn11_vm2_fixture
	vn22_vm2_fixture = self.res.vn22_vm2_fixture
	self.logger.info("Pinging from vn11_vm2 to vn22_vm2 by policy rule ")

        if not vn11_vm2_fixture.ping_with_certainty(vn22_vm2_fixture.vm_ip, expectation=True):
               result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info("Pinging from vn22_vm2 to vn11_vm2 by policy rule ")

        if not vn22_vm2_fixture.ping_with_certainty(vn11_vm2_fixture.vm_ip, expectation=True):
               result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
	return result

	
    def check_floatingip_traffic(self) :
	
	result = True
        vn11_fixture = self.res.vn11_fixture
        vn22_fixture = self.res.vn22_fixture
        fvn_fixture = self.res.fvn_fixture
        vn11_vm1_fixture = self.res.vn11_vm1_fixture
        vn22_vm1_fixture = self.res.vn22_vm1_fixture
        fvn_vm1_fixture = self.res.fvn_vm1_fixture
        fip_fixture = self.res.fip_fixture
        fip_id = self.res.fip_id
        fip_id1 = self.res.fip_id1
	self.logger.info('PINGING FROM VN11_VM1 TO VN22_VM1 \n')
        if not vn11_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN11_VM1 TO FVN_VM1 \n')
        if not vn11_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN22_VM1 TO FVN_VM1 \n')
        if not vn22_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        fip = vn11_vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        self.logger.info('PINGING FROM  FVN_VM1 to VN11_VM1 \n')
        if not fvn_vm1_fixture.ping_to_ip(fip):
            result = result and False
        if not result :
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
	return result
	
   	 		
    @preposttest_wrapper
    def test_upgrade(self):
    	''' Test to upgrade contrail software from existing build to new build and then rebooting resource vm's and verifying them and also Validates the service chaining in network  datapath
	'''
	result =True
	assert self.res.verify_common_objects()
	
	if( set(self.inputs.compute_ips) & set(self.inputs.cfgm_ips) ):
	       raise self.skipTest("Skiping Test. Cfgm and Compute nodes should be different to run  this test case")	
 	
	with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password, warn_only=True,abort_on_prompts=False):
			
		status = run("cd /tmp/temp/;ls")
		m = re.search(r'contrail-install-packages-(.*).noarch.rpm',status)
		assert m , 'Failed in importing rpm'
                rpms = m.group(0)

		status= run("yum -y localinstall /tmp/temp/" + rpms)
		assert not(status.return_code),'Failed in running: yum -y localinstall /tmp/temp/' + rpms
	
		
		status = run("cd /opt/contrail/contrail_packages;./setup.sh")
                assert not(status.return_code), 'Failed in running : cd /opt/contrail/contrail_packages;./setup.sh'

		status = run("cd /opt/contrail/utils" + ";" + "fab upgrade_contrail:/tmp/temp/" + rpms)
		assert not(status.return_code), 'Failed in running : cd /opt/contrail/utils;fab upgrade_contrail:/tmp/temp/' + rpms
		
		m= re.search('contrail-install-packages-([0-9].[0-9][0-9])-(.*).el6.noarch.rpm',rpms)
               	build_id=m.group(2)	
		status = run("contrail-version | awk '{if (NR!=1 && NR!=2) {print $1,$3}}'")
		assert not(status.return_code)
                lists = status.split('\r\n')
                for module in lists:
			success=re.search(build_id,module)
			result = result and success
			if not (result):
				self.logger.error(' Failure while upgrading ' + module + 'should have upgraded to ' + build_id)
			
                	assert result,'Failed to Upgrade ' + module 
		
		time.sleep(90)
		connections.clear()
		self.logger.info('Will REBOOT the SHUTOFF VMs')
	        for vm in self.res.nova_fixture.get_vm_list():
        	    if vm.status != 'ACTIVE':
                	self.logger.info('Will Power-On %s'%vm.name)
                	vm.start()
                	self.res.nova_fixture.wait_till_vm_is_active(vm)
 
		assert self.res.verify_common_objects_without_collector()
		run("rm -rf /tmp/temp")
	
	return result
    #end test_upgrade

    # adding function to create more resources these will be created after upgrade  #	
    def vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        self.newvn_fixture = self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='newvn', inputs= self.inputs, subnets=['22.1.1.0/24']))
        self.newvn_fixture.verify_on_setup()
        
	self.newvn11_fixture = self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='newvn11', inputs= self.inputs, subnets=['11.1.1.0/24']))
        self.newvn11_fixture.verify_on_setup() 
     
        return True
   
    def vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name = 'vn11_vm1_mine'
        vm2_name = 'vn22_vm1_mine'
        vm3_name = 'fip_vn_vm1_mine'
        vm4_name = 'newvn_vm1_mine'
	vm5_name = 'newvn11_vm1_mine'

        vn_obj= self.res.vn11_fixture.obj
        self.res.vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert self.res.vm1_fixture.verify_on_setup()

        vn_obj= self.res.vn22_fixture.obj
        self.res.vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert self.res.vm2_fixture.verify_on_setup()
        
        vn_obj= self.res.fvn_fixture.obj
        self.res.vm3_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm3_name, project_name= self.inputs.project_name))
        assert self.res.vm3_fixture.verify_on_setup()
	
	vn_obj= self.newvn_fixture.obj
        self.vm4_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm4_name, project_name= self.inputs.project_name))
        assert self.vm4_fixture.verify_on_setup()

        vn_obj= self.newvn11_fixture.obj
        self.vm5_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm5_name, project_name= self.inputs.project_name))
        assert self.vm5_fixture.verify_on_setup()

        return True

