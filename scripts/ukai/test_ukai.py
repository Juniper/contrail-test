from __future__ import absolute_import
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from .base_ukai import UKAIProc
from test import BaseTestCase
from .base_ukai import *
from common import isolated_creds
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast
from policy_test import*
from project_test import*
from tcutils import*
from . import env
import test
import pdb

class TestuKAI(ukaiBaseTest):
    @classmethod
    def setUpClass(cls):
        pass
        super(TestuKAI, cls).setUpClass()
        

    def runTest(self):
        pass
    #end runTest




    #@preposttest_wrapper
    def test_ukai_add_del_flavor(self):

        '''TEST:
           Add/Del flavor
        '''
        project_name = self.inputs.stack_tenant
        user_name   = 'TestuKAI'
	flavor_name  = 'test1_flavor'
        self.logger.info('Test-1 verify adding  flavor')
        ukai_add_flavor = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name, 
                                   flavor_name= flavor_name, flavor_ram='1000', flavor_vcpus = '1', 
                                   flavor_disk='2', flavor_swap='1', flavor_ephemeral='1')
        ukai_add_flavor.create_flavor()
        ukai_add_flavor.delete_flavor()
      
     # test_ukai_add_del_flavor


    def test_ukai_add_del_image(self):

        '''TEST:
           Add/Del image
        '''

        project_name = self.inputs.stack_tenant
        user_name   = 'TestuKAI'
        image_name = 'cirros'
        self.logger.info('Test-1 verify adding/del  image')
        ukaiImage = UKAIProc(connections=self.admin_connections, image_name= image_name, 
                             container_format='bare', disk_format='qcow2', min_disk='1', min_ram='1')
        ukaiImage.create_image(image_name=image_name)
        ukaiImage.delete_image()

     # test_ukai_add_del_image


    def test_ukai_add_del_pol_admin(self):

        '''TEST:
           Add/Del policy as admin user'''
        project_name = 'admin'
        user_name   = 'admin'
        pol_name     = 'pol1'
        ukaiPol = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name, 
                           pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any')
        ukaiPol.create_pol()
        ukaiPol.delete_pol()

     # test_ukai_add_del_pol_admin


    def test_ukai_add_del_pol_non_admin(self):

        '''TEST:
           Add/Del policy as non admin user'''
        project_name = self.inputs.stack_tenant
        user_name   = self.inputs.stack_tenant
        pol_name     = 'pol1'
        ukaiPol = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name, 
                           pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any')
        ukaiPol.create_pol()
        ukaiPol.delete_pol()

     # test_ukai_add_del_pol_non_admin


    def test_ukai_add_del_vn_admin(self):

        '''TEST:
           Add/Del VN as admin user'''
        project_name = 'admin'
        user_name   = 'admin'
        pol_name     = 'pol1'
        vn_name      = 'VN1'
        #projectObj=ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.admin_connections,project_name=project_name,username=user_name,password=user_name)
        #project_connections = projectObj.get_project_connections()

        ukaiPol = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name, 
                           pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any')

        policy_uuid=ukaiPol.create_pol()
        policy_obj=self.vnc_lib.network_policy_read(id=policy_uuid)
        ukaiVn = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name,
                         vn_name=vn_name, vn_cidr='2.1.1.0/20', vn_prefix_len='24')
        ukaiVn.create_vn()

        self.logger.info ("Update VN with policy")
        ukaiVn = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name,vn_name=vn_name,pol_name=pol_name)
        ukaiVn.update_vn()

        sleep (5)
        vn2_fix = VNFixture(connections=self.admin_connections,project_name=project_name, vn_name=vn_name, policy_objs=[policy_obj])
        vn2_fix.read()
        assert vn2_fix.verify_on_setup()

        ukaiVn.delete_vn()
        ukaiPol.delete_pol()
        
     # test_ukai_add_del_vn__admin



    def test_ukai_add_del_vn_non_admin(self):

        '''TEST:
           Add/Del VN as non admin user'''
        project_name = self.inputs.stack_tenant
        user_name   = self.inputs.stack_tenant
        pol_name     = 'pol1'
        vn_name      = 'VN1'

        ukaiPol = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name, 
                           pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any')
        policy_uuid = ukaiPol.create_pol()
        policy_obj=self.vnc_lib.network_policy_read(id=policy_uuid)

        ukaiVn = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name,
                          vn_name=vn_name, vn_cidr='2.1.1.0/20', vn_prefix_len='24')
        ukaiVn.create_vn()

        self.logger.info ("Update VN with policy")
        ukaiVn = UKAIProc(connections=self.admin_connections,project_name=project_name,user_name=user_name,vn_name=vn_name,pol_name=pol_name)
        ukaiVn.update_vn()
        sleep (5)
        vn2_fix = VNFixture(connections=self.admin_connections,project_name=project_name, vn_name=vn_name, policy_objs=[policy_obj])
        vn2_fix.read()
        assert vn2_fix.verify_on_setup()
        ukaiVn.delete_vn()
        ukaiPol.delete_pol()

     # test_ukai_add_del_vn_non_admin



    def test_ukai_add_del_sg_non_admin(self):

        '''TEST:
           Add/Del SG as non admin user'''
        project_name = self.inputs.stack_tenant
        user_name   = self.inputs.stack_tenant
        sg_name      = 'SG1'

        self.logger.info ("Test create/del sg")
        ukaiSG1=UKAIProc(connections=self.admin_connections, project_name=project_name,user_name=user_name,sg_name=sg_name)
        ukaiSG1.create_sg()
        ukaiSG1.delete_sg()


     # test_ukai_add_del_sg_non_admin



    def test_ukai_add_del_sg_admin(self):

        '''TEST:
           Add/Del SG as admin user'''
        project_name = 'admin'
        user_name   = 'admin'
        sg_name      = 'SG1'

        self.logger.info ("Test create/del sg")
        ukaiSG1=UKAIProc(connections=self.admin_connections, project_name=project_name,sg_name=sg_name)
        ukaiSG1.create_sg()
        ukaiSG1.delete_sg()


     # test_ukai_add_del_sg__admin



    def test_ukai_add_del_svc_temp_admin(self):

        '''TEST:
           Add/Del service template as  admin user'''
        project_name = 'admin'
        user_name   = 'admin'
        sg_name      = 'SG1'

        self.logger.info ("Test create/del sg")
        ukaiSG1=UKAIProc(connections=self.admin_connections, project_name=project_name,sg_name=sg_name)
        ukaiSG1.create_sg()
        ukaiSG1.delete_sg()


     # test_ukai_add_del_svc_temp__admin



    def test_ukai_add_del_vm_admin(self):

        '''TEST:
           Add/Del VM as non admin user'''
        project_name = 'admin'
        user_name   = 'admin'
        image_name   = 'cirros'
        flavor_name  = 'test1_flavor'
        pol_name     = 'pol1'
        vn_name      = 'VN1'
        sg_name      = 'SG1'
        vm_name      = 'VM1'

        ukaiHandle = UKAIProc(connections=self.admin_connections, project_name=project_name,user_name=user_name,flavor_name= flavor_name, 
                      flavor_ram='1000', flavor_vcpus = '1',flavor_disk='2', flavor_swap='1', flavor_ephemeral='1',
                      image_name= image_name, container_format='bare', disk_format='qcow2', min_disk='1', min_ram='1',
                      pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any',
                      vn_name=vn_name, vn_cidr='2.1.1.0/20', vn_prefix_len='24', sg_name=sg_name)

        self.logger.info ("Test create/del VM")
        self.logger.info ("create flavor")
        flavor_id1=ukaiHandle.create_flavor()

        self.logger.info ("add image")
        image_id1=ukaiHandle.create_image(image_name=image_name)

        self.logger.info ("add policy")
        policy_uuid=ukaiHandle.create_pol()
        policy_obj=self.vnc_lib.network_policy_read(id=policy_uuid)        

        self.logger.info ("add vn")
        vn_id1=ukaiHandle.create_vn()
        sleep (10)
        vn_fix = VNFixture(connections=self.admin_connections,project_name=project_name, vn_name=vn_name, policy_objs=[policy_obj])
        vn_fix.read()
        assert vn_fix.verify_on_setup()

        sg_id1 = ukaiHandle.create_sg()
        self.logger.info ("Test create/del VM")

        ukaiVmHandle =UKAIProc(connections=self.admin_connections, project_name=project_name,user_name=user_name,flavor_name= flavor_name,
                      flavor_ram='1000', flavor_vcpus = '1',flavor_disk='2', flavor_swap='1', flavor_ephemeral='1',
                      image_name= image_name, container_format='bare', disk_format='qcow2', min_disk='1', min_ram='1',
                      pol_name= pol_name, pol_action = 'pass', pol_direction ='\u003c\u003e', pol_protocol='any',
                      vn_name=vn_name, vn_cidr='2.1.1.0/20', vn_prefix_len='24', sg_name=sg_name, image_id=image_id1,flavor_id=flavor_id1,sg_id=sg_id1,nw_id=nw_id1)

        ukaiVmHandle.create_vm()
        ukaiVmHandle.delete_vm()

        self.logger.info ("Delete VN")
        ukaiHandle.delete_vn()

        self.logger.info ("Delete pol")
        ukaiHandle.delete_pol()

        self.logger.info ("Test flavor and image ")
        ukaiHandle.delete_image(image_name=image_name)
        ukaiHandle.delete_flavor()
     

     # test_ukai_add_del_vm__admin


if __name__ == '__main__':
    pass
# end of TestuKAI
