# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
# 
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# 
import os
import fixtures
import testtools

from contrail_test_init import *
from vn_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
import time
import random
from webui_test import * 
from selenium.webdriver.support.ui import WebDriverWait

class WebuiTestSanity(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures ):
    
    resources = [('base_setup', SolnSetupResource)]
    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res= SolnSetupResource.getResource()
        self.inputs= self.res.inputs
        self.connections= self.res.connections
        self.logger= self.res.logger
        self.nova_fixture= self.res.nova_fixture
        self.analytics_obj=self.connections.analytics_obj
        self.vnc_lib= self.connections.vnc_lib
        self.quantum_fixture= self.connections.quantum_fixture
        self.cn_inspect= self.connections.cn_inspect
	if self.inputs.webui_flag :
		self.browser =self.connections.browser
		self.browser_openstack =self.connections.browser_openstack
		self.delay = 10
                self.webui = webui_test(self.connections, self.inputs)
                self.webui_common = webui_common(self.webui)

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)
    
    def setUp(self):
        super (WebuiTestSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super (WebuiTestSanity, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    #end runTest
    

    @preposttest_wrapper
    def test_verify_bgp_routers_in_webui(self):
        '''Test to validate bgp routers advance details in webui
        '''
        assert self.webui.verify_bgp_routers_ops_basic_data_in_webui()
        assert self.webui.verify_bgp_routers_ops_advance_data_in_webui()
        return True
    #end test_verify_bgp_routers_in_webui

    @preposttest_wrapper
    def test_verify_config_nodes_in_webui(self):
        ''''Test to validate config nodes advance details in webui'''
        assert self.webui.verify_config_nodes_ops_basic_data_in_webui()
        assert self.webui.verify_config_nodes_ops_advance_data_in_webui()
        return True
    #end test_verify_config_nodes_in_webui

    @preposttest_wrapper    
    def test_verify_analytics_nodes_in_webui(self):
        '''Test to validate analytics nodes details in webui
        '''
        assert self.webui.verify_analytics_nodes_ops_basic_data_in_webui()
        assert self.webui.verify_analytics_nodes_ops_advance_data_in_webui()
        return True
    #end test_verify_analytics_nodes_in_webui

    def test_verify_vrouters_in_webui(self):
        '''Test to validate vrouter details in webui '''
        assert self.webui.verify_vrouter_ops_basic_data_in_webui()
        assert self.webui.verify_vrouter_ops_advance_data_in_webui()
        return True
    #end test_verify_vrouters_in_webui
    
    @preposttest_wrapper
    def test_verify_vm_in_webui(self):
        '''Test to validate vm details in webui
        '''
        assert self.webui.verify_vm_ops_basic_data_in_webui()
        assert self.webui.verify_vm_ops_advance_data_in_webui()
        return True
    #end test_verify_vm_in_webui
    
    @preposttest_wrapper
    def test_verify_vn_in_webui(self):
        '''Test to validate vn details in webui '''
        assert self.webui.verify_vn_ops_basic_data_in_webui()
        assert self.webui.verify_vn_ops_advance_data_in_webui()
        return True
    #end test_verify_vn_in_webui
    
    @preposttest_wrapper
    def test_vn_add_verify_delete_in_webui(self):
        '''Test to validate VN creation and deletion.
        '''
 
        vn_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='webui_vn_test_vn', inputs= self.inputs, option='gui',subnets=['22.1.1.0/24']))
	assert vn_fixture.verify_on_setup()
	return True
    #end 
    
    @preposttest_wrapper
    def test_vm_add_verify_delete_in_webui(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name='webui_vm_test_vm'
        vn_name='webui_vn_test_vm'
        vn_subnets=['11.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
	assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name, image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        return True
    #end test_vm_add_delete    
   
    @preposttest_wrapper
    def test_floating_ip_add_verify_delete_in_webui(self):
        '''Test to validate floating-ip Assignment to a VM. 
        It creates a VM, assigns a FIP to it and pings to a IP in the FIP VN.
        '''
        result= True
        fip_pool_name= 'webui_pool'
        fvn_name= self.res.fip_vn_name
        fvn_fixture= self.res.fvn_fixture
        vn1_fixture= self.res.vn1_fixture
        vn1_vm1_fixture= self.res.vn1_vm1_fixture
        fvn_vm1_fixture= self.res.fvn_vm1_fixture
        fvn_subnets= self.res.fip_vn_subnets
        vm1_name= self.res.vn1_vm1_name
        vn1_name= self.res.vn1_name
        vn1_subnets= self.res.vn1_subnets
        assert fvn_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert fvn_vm1_fixture.verify_on_setup()
        fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name, vn_id= fvn_fixture.vn_id, vn_name = fvn_name ))
        fip_id=fip_fixture.create_and_assoc_fip_webui( fvn_fixture.vn_id, vn1_vm1_fixture.vm_id,vn1_vm1_fixture.vm_name)
        fip_fixture.webui.verify_fip_in_webui(fip_fixture) 
        if not vn1_vm1_fixture.ping_with_certainty( fvn_vm1_fixture.vm_ip ):
            result = result and False
        fip_fixture.webui.delete_fip_in_webui(fip_fixture)
        if not result :
            self.logger.error('Test to ping between VMs %s and %s' %(vn1_vm1_name, fvn_vm1_name))
            assert result
        return True
    #end test_floating_ip

    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN.

        '''
        vn1_name=self.res.vn1_name
        vn1_subnets= self.res.vn1_subnets
        vn1_vm1_name= self.res.vn1_vm1_name
        vn1_vm2_name= self.res.vn1_vm2_name
        vn1_fixture= self.res.vn1_fixture
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.res.vn1_vm1_fixture
        assert vm1_fixture.verify_on_setup()
        
        vm2_fixture= self.res.vn1_vm2_fixture
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        return True
    #end test_ping_within_vn   
#end WebuiTestSanity
