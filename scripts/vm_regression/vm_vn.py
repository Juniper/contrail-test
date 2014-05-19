# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
# 
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# 
import connections 
import unittest
import fixtures
import testtools
import traffic_tests
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from keystone_tests import *

#from analytics_tests import *
class VMVNTestJSON(testtools.TestCase, fixtures.TestWithFixtures):
    
#    @classmethod
#    def setUpClass(cls):
    def setUp(self):
        super(VMVNTestJSON, self).setUp() 
	pass 
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
        auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
        self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password, 
					tenant= self.inputs.project_name, auth_url= auth_url )
    #end setUpClass
    
    def cleanUp(self):
        super(TestVMVN, self).cleanUp()
    #end cleanUp
    
    def runTest(self):
        pass
    #end runTest

    def get_project_inputs_connections(self,project_name='admin',user = 'admin',password='contrail123'):
        '''Returns objects of project fixture,inputs and conections'''

        dct = {}

        try:
            project_fixture = self.useFixture(ProjectFixture(project_name = project_name,vnc_lib_h= self.vnc_lib,username=user,
                                                password= password,connections= self.connections, option= 'keystone'))
            dct['project'] = project_fixture
    
            try:
            	import keystone_tests 
            	auth_url= 'http://%s:5000/v2.0' %(self.inputs.openstack_ip)
            	self.key_stone_clients= KeystoneCommands(username= self.inputs.stack_user, password= self.inputs.stack_password,
                                                       tenant= self.inputs.project_name, auth_url= auth_url )
            	self.key_stone_clients.add_user_to_tenant(project_name,user , 'admin')
            	self.key_stone_clients.add_user_to_tenant(project_name,'admin' , 'admin')
            except Exception as e:
                self.logger.info("User already added to project")

            project_inputs= self.useFixture(ContrailTestInit(self.ini_file, stack_user=project_fixture.username,
                                        stack_password=project_fixture.password,project_fq_name=['default-domain',project_name]))
            dct['inputs'] = project_inputs

            project_connections= ContrailConnections(project_inputs,project_name= project_name,username=project_fixture.username
					,password= project_fixture.password)
            dct['connections'] = project_connections
        except Exception as e:
            self.logger.warn("Got exception in get_project_inputs_connections as %s"%(e))
        finally:
            time.sleep(2)		
            return dct
    #end get_project_inputs_connections

class TestVNAddDelete(VMVNTestJSON):    
#    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
	print 'aaaa'
        dct=self.get_project_inputs_connections(project_name='vn_add_delete',user = 'test1',password='contrail123')
        vn_obj=self.useFixture( VNFixture(project_name= 'vn_add_delete', connections= dct['connections'],
                     vn_name='vn22', inputs= dct['inputs'], subnets=['22.1.1.0/24'] ))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    #end 
class TestVNAddDeleteXML(TestVNAddDelete):
    pass

class TestVmAddDelete(VMVNTestJSON):
#    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
	print 'aaaa'
        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        dct=self.get_project_inputs_connections(project_name='vm_add_delete',user = 'test1',password='contrail123')
        vn_fixture= self.useFixture(VNFixture(project_name= 'vm_add_delete', connections= dct['connections'],
                     vn_name=vn_name, inputs= dct['inputs'], subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= dct['connections'],
                vn_obj=vn_obj, vm_name= vm1_name, project_name= 'vm_add_delete',ram = '4096',image_name= 'ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        return True
    #end test_vm_add_delete

class TestVmAddDeleteXML(TestVmAddDelete):
    pass
#	
#    @preposttest_wrapper
class TestIpamAddDelete(VMVNTestJSON):
    def test_ipam_add_delete(self):
        '''Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
        '''
	print 'aaaa'
        proj_name='ipam_add_delete'
        ipam_name = 'test_ipam'
        dct=self.get_project_inputs_connections(project_name=proj_name ,user = 'test1',password='contrail123')
        vnc_lib = dct['connections'].vnc_lib 
        project_obj = self.useFixture(ProjectFixture(vnc_lib_h= vnc_lib, connections= dct['connections']))
        ipam_obj=self.useFixture( IPAMFixture(project_obj= dct['project'], name= ipam_name))
        assert ipam_obj.verify_on_setup()
        vn_fixture=self.useFixture( VNFixture(project_name= proj_name , connections= dct['connections'],
                                 vn_name='vn22', inputs= dct['inputs'], subnets=['22.1.1.0/24'], ipam_fq_name = ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(connections= dct['connections'],
               vn_obj = vn_fixture.obj, vm_name= 'vm1',project_name= proj_name))
        vm2_fixture= self.useFixture(VMFixture(connections= dct['connections'],
                vn_obj = vn_fixture.obj,vm_name= 'vm2',project_name= proj_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        return True
    #end test_ipam_add_delete
class TestIpamAddDeleteXML(TestIpamAddDelete):
    pass
 
#    @preposttest_wrapper
class DuplicateVn(VMVNTestJSON):
    def test_duplicate_vn_add(self):
        '''Test to validate adding a Duplicate VN creation and deletion.
        '''
	print 'aaaa'
        dct=self.get_project_inputs_connections(project_name='duplicate_vn_add',user = 'test1',password='contrail123')
        vn_obj1=self.useFixture( VNFixture(project_name= 'duplicate_vn_add', connections= dct['connections'],
                     vn_name='vn22', inputs= dct['inputs'], subnets=['22.1.1.0/24'] ))
        assert vn_obj1.verify_on_setup()
        assert vn_obj1
        
        vn_obj2=self.useFixture( VNFixture(project_name= 'duplicate_vn_add', connections= dct['connections'],
                     vn_name='vn22', inputs= dct['inputs'], subnets=['22.1.1.0/24'] ))
        assert vn_obj2.verify_on_setup()
        assert vn_obj2, 'Duplicate VN cannot be created'
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
        return True
    #end test_duplicate_vn_add
class DuplicateVnXML(DuplicateVn):
    pass
    
