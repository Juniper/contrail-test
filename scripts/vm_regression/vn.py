import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds

class TestVN(BaseVnVmTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestVMVN, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes
 
    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj=self.useFixture( VNFixture(project_name= self.project.project_name,
                                connections= self.connections,
                               vn_name='vn22', inputs= self.inputs
                               , subnets=['22.1.1.0/24'] ))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    #end test_vn_add_delete

    @preposttest_wrapper
    def test_vn_name_with_spl_characters(self):
        '''Test to validate VN name with special characters is allowed.
        '''
        vn1_obj=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
            vn_name='vn.1', inputs= self.inputs, subnets=['22.1.1.0/29'] ))
        assert vn1_obj.verify_on_setup()
        assert vn1_obj

        vn2_obj=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
            vn_name='vn,2', inputs= self.inputs, subnets=['33.1.1.0/30'] ))
        assert vn2_obj.verify_on_setup()
        assert vn2_obj

        vn3_obj=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
            vn_name='vn&3', inputs= self.inputs, subnets=['44.1.1.0/29'] ))
        self.logger.info("VN names with '&' are allowed via API, but not through Openstack ==> Bug 1023")
        assert not vn3_obj.verify_on_setup()
        if vn3_obj:
            self.logger.error('Bug 1023 needs to be fixed')

        vn4_obj=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
            vn_name='vn_4', inputs= self.inputs, subnets=['55.1.1.0/31'] ))
        assert vn4_obj.verify_on_setup()
        assert vn4_obj

        return True
    #end test_vn_name_with_spl_characters

    @preposttest_wrapper
    def test_duplicate_vn_add(self):
        '''Test to validate adding a Duplicate VN creation and deletion.
        '''
        vn_obj1 = self.useFixture( VNFixture(project_name= self.project.project_name,
                connections= self.connections,vn_name='vn22', inputs = self.inputs
                ,subnets=['22.1.1.0/24'] ))
        assert vn_obj1.verify_on_setup()
        assert vn_obj1

        vn_obj2 = self.useFixture( VNFixture(project_name= self.project.project_name,
                  connections= self.connections,vn_name='vn22', inputs= self.inputs,
                  subnets=['22.1.1.0/24'] ))
        assert vn_obj2.verify_on_setup()
        assert vn_obj2, 'Duplicate VN cannot be created'
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
        return True
    #end test_duplicate_vn_add


#end TestVMVN
class TestVNXML(TestVN):
    _interface = 'xml'
    pass
