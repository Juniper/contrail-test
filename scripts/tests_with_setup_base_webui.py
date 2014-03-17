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
from selenium.webdriver.support.ui import WebDriverWait

class TestSanityBase(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures ):
    
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
	if self.inputs.webui_flag=='True':
		self.browser =self.connections.browser
		self.browser_openstack =self.connections.browser_openstack
		self.delay = 10
    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)
    
    def setUp(self):
        super (TestSanityBase, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super (TestSanityBase, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    #end runTest
    

    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='vnxx', inputs= self.inputs, option='gui',subnets=['22.1.1.0/24']))
        #assert vn_fixture.verify_vn_in_gui()
	assert vn_fixture.verify_on_setup()
	return True
    #end 
 
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name='vm_test'
        vn_name='vn222'
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
#end TestSanityBase
