from vn_test import *
from vm_test import *
from vnc_api_test import *
from tcutils.wrappers import preposttest_wrapper
from base import BaseForwardingMode
from common import isolated_creds
import time
import test

class TestForwardingMode(BaseForwardingMode):
   
    @classmethod
    def setUpClass(cls):
        super(TestForwardingMode, cls).setUpClass()
        

    @classmethod
    def tearDownClass(cls):
        super(TestForwardingMode, cls).tearDownClass()

    @preposttest_wrapper
    def test_forwarding_mode_l2(self):
        '''Test to check traffic between VM's when forwarding_mode set to L2'''
        return self.setup_commmon_objects(vn_name='vn_l2',vm_name1='vm1_l2',vm_name2='vm2_l2',forwarding_mode='l2')
        
    @preposttest_wrapper
    def test_forwarding_mode_l3(self):
        '''Test to check traffic between VM's when forwarding_mode set to L3'''
        return self.setup_commmon_objects(vn_name='vn_l3',vm_name1='vm1_l3',vm_name2='vm2_l3',forwarding_mode='l3')
        
    @preposttest_wrapper
    def test_forwarding_mode_l2_l3(self):
        '''Test to check traffic between VM's when forwarding_mode set to L2_L3'''
        return self.setup_commmon_objects(vn_name='vn_l2_l3',vm_name1='vm1_l2_l3',vm_name2='vm2_l2_l3',forwarding_mode='l2_l3')
        
    @preposttest_wrapper      
    def test_forwarding_mode_global_l2(self):
        '''Test to check traffic between VM's when global forwarding_mode set to L2'''
        self.gl_forwarding_mode='l2'
        self.vnc_lib_fixture.set_global_forwarding_mode(self.gl_forwarding_mode)
        return self.setup_commmon_objects(vn_name='vn_global_l2',vm_name1='vm1_global_l2',vm_name2='vm2_global_l2',forwarding_mode=None)
    
    @preposttest_wrapper    
    def test_forwarding_mode_global_l3(self):
        '''Test to check traffic between VM's when global forwarding_mode set to L3'''
        self.gl_forwarding_mode='l3'
        self.vnc_lib_fixture.set_global_forwarding_mode(self.gl_forwarding_mode)
        return self.setup_commmon_objects(vn_name='vn_global_l3',vm_name1='vm1_global_l3',vm_name2='vm2_global_l3',forwarding_mode=None)
    
    @preposttest_wrapper      
    def test_forwarding_mode_global_l2_l3(self):
        '''Test to check traffic between VM's when global forwarding_mode set to L2_L3'''
        self.gl_forwarding_mode='l2_l3'
        self.vnc_lib_fixture.set_global_forwarding_mode(self.gl_forwarding_mode)
        return self.setup_commmon_objects(vn_name='vn_global_l2_l3',vm_name1='vm1_global_l2_l3',vm_name2='vm2_global_l2_l3',forwarding_mode=None)
    
    def setup_commmon_objects(self,vn_name,vm_name1,vm_name2,forwarding_mode):
        vn_fixture = self.create_vn(vn_name=vn_name,forwarding_mode=forwarding_mode)
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = self.connections.orch.get_hosts()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=get_random_name(vm_name1),
                                     flavor='contrail_flavor_small',
                                     image_name='ubuntu',
                                     node_name=host_list[0])
        if len(host_list) > 1:
            self.logger.info("Multi-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=get_random_name(vm_name2),
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu',
                                         node_name=host_list[1])
        else:
            self.logger.info("Single-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=get_random_name(vm_name2),
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu')
        
        if  self.vnc_lib_fixture.get_active_forwarding_mode(vn_fixture.vn_fq_name) =='l2':
            self.logger.info("sleeping until vm's comes up")
            sleep(300)
        vm1_fixture.wait_till_vm_is_up() 
        vm2_fixture.wait_till_vm_is_up()
        vm1_fixture.verify_on_setup() 
        vm2_fixture.verify_on_setup()
        
        if  self.vnc_lib_fixture.get_active_forwarding_mode(vn_fixture.vn_fq_name) =='l2':
            self.logger.info("Skipping Ping Test between VM's as forwarding_mode is L2")
        else:
            assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
                "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
            assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
                "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        return True
    #end setup_common_objects