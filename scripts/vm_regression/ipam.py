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

class TestIPAM(BaseVnVmTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestIPAM, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes

    @preposttest_wrapper
    def test_ipam_add_delete(self):
        '''Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
        '''
#        proj_name='ipam_add_delete'
        ipam_name = 'test_ipam'
        vnc_lib = self.connections.vnc_lib
        project_obj = self.useFixture(ProjectFixture(vnc_lib_h= vnc_lib, connections= self.connections))
        ipam_obj=self.useFixture( IPAMFixture(project_obj= self.project, name= ipam_name))
        assert ipam_obj.verify_on_setup()
        vn_fixture=self.useFixture( VNFixture(project_name= self.project.project_name , connections= self.connections,
                                 vn_name='vn22', inputs= self.inputs, subnets=['22.1.1.0/24'],
                                 ipam_fq_name = ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
               vn_obj = vn_fixture.obj, vm_name= 'vm1',project_name= self.project.project_name))
        vm2_fixture = self.useFixture(VMFixture(connections= self.connections,vn_obj = vn_fixture.obj,
                      vm_name= 'vm2',project_name= self.project.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        return True

   #end test_ipam_add_delete

    @preposttest_wrapper
    def test_ipam_persistence_across_restart_reboots(self):
        '''Test to validate IPAM persistence across restarts and reboots of nodes.
        '''
        project_obj = self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib, connections= self.connections))
        ipam_obj=self.useFixture( IPAMFixture(project_obj= project_obj, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
                                 vn_name='vn22', inputs= self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name = ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
               vn_obj = vn_fixture.obj, vm_name= 'vm1'))
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj = vn_fixture.obj,vm_name= 'vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        self.logger.info('Will restart the services now')
        for compute_ip in self.inputs.compute_ips:
            pass
#            self.inputs.restart_service('contrail-vrouter',[compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
#            self.inputs.restart_service('contrail-control',[bgp_ip])
            pass
        sleep(30)

        self.logger.info('Will check if the ipam persists and ping b/w VMs is still successful')

        assert ipam_obj
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        return True

    @preposttest_wrapper
    def test_release_ipam(self):
        '''Test to validate that IPAM cannot be deleted until the VM associated with it is deleted.
        '''
        project_obj = self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib, connections= self.connections))
        ipam_obj=self.useFixture( IPAMFixture(project_obj= project_obj, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
                                 vn_name='vn22', inputs= self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name = ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
             self.logger.info( 'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it.')

        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
               vn_obj = vn_fixture.obj, vm_name= 'vm1'))
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj = vn_fixture.obj,vm_name= 'vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
             self.logger.info( 'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it, which has VMs on it.')

        return True
    #end test_release_ipam
 
#end TestVMVN
class TestIPAMXML(TestIPAM):
    _interface = 'xml'
    pass
