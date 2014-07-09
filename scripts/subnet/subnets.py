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
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from floating_ip_test_resource import SolnSetupResource
import time

class TestPorts(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures ):
    
    def setUp(self):
        super (TestPorts, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.inputs=self.useFixture(ContrailTestInit( self.ini_file))
        self.connections= ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.logger = self.inputs.logger
    
    def cleanUp(self):
        super (TestPorts, self).tearDown()
    
    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def test_ports_attach_detach (self):
        '''Validate port attach/detach operations
        Create a port in a VN
        Create a VM using that port
        Detach the port
        
        '''
        result= True
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        port_obj = self.quantum_fixture.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name, port_ids=[port_obj['id']]))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        vm1_fixture.wait_till_vm_is_up() 
        vm2_fixture.wait_till_vm_is_up() 
        if not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
            self.logger.error('Ping to a attached port %s failed' %(vm1_fixture.vm_ip))
            result = result and False
        time.sleep(2)
        vm1_fixture.interface_detach(port_id=port_obj['id'])
        # No need to delete the port. It gets deleted on detach 

        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error('VM %s is not ACTIVE(It is %s) after port-detach' %(
                vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False

        if not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, expectation=False):
            self.logger.error('Ping to a detached port %s passed!' %(vm1_fixture.vm_ip))
            result = result and False
        else:
            self.logger.info('Unable to ping to a detached port.. OK')

        #Now attach the interface again 
        port_obj = self.quantum_fixture.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture.interface_attach(port_id=port_obj['id']) 
        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error('VM %s is not ACTIVE(It is %s) during attach-detach' %(
                vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False
        if result and not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
            self.logger.error('Ping to a attached port %s failed' %(vm1_fixture.vm_ip))
            result = result and False

        return result
    #end test_ports_attach_detach
