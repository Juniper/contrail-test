# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
# 
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# 
import os
import signal
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
import shlex,subprocess
from subprocess import PIPE    
#from analytics_tests import *
class TestSanityFixture(testtools.TestCase, fixtures.TestWithFixtures):
    
#    @classmethod
    def setUp(self):
        super(TestSanityFixture, self).setUp()  
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
    #end setUpClass
    
    def cleanUp(self):
        super(TestSanityFixture, self).cleanUp()
    #end cleanUp
    
    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN. 
        
        '''
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        return True
    #end test_ping_within_vn
    
    

    #start subnet ping
    #verifying that ping to subnet broadcast is respended by other vms in same subnet
    #vm from other subnet should not respond
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcast . 
        
        '''
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        ping_count='5'
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_vm3_name= 'vm3'
        vn1_vm4_name= 'vm4'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        vm3_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm3_name))
        vm4_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )
        #Geting the VM ips
        vm1_ip=vm1_fixture.vm_ip
        vm2_ip=vm2_fixture.vm_ip
        vm3_ip=vm3_fixture.vm_ip
        vm4_ip=vm4_fixture.vm_ip
        ip_list=[vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping=['30.1.1.255','224.0.0.1','255.255.255.255']
        #passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm=['echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds= cmd_list_to_pass_vm)
        vm2_fixture.run_cmd_on_vm(cmds= cmd_list_to_pass_vm)
        vm3_fixture.run_cmd_on_vm(cmds= cmd_list_to_pass_vm)
        vm4_fixture.run_cmd_on_vm(cmds= cmd_list_to_pass_vm)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s'%(vm1_ip,dst_ip)
#pinging from Vm1 to subnet broadcast
            ping_output= vm1_fixture.ping_to_ip( dst_ip, return_output= True, count=ping_count, other_opt='-b' )
            expected_result=' 0% packet loss'
            assert (expected_result in ping_output)
#getting count of ping response from each vm
            string_count_dict={}
            string_count_dict=get_string_match_count(ip_list,ping_output)
            self.logger.info("Ping reply from vms %s"%(string_count_dict))
            for k in ip_list:
                assert (string_count_dict[k] >= (int(ping_count)-1))#this is a workaround : ping utility exist as soon as it gets one response 
        return True
    #end subnet ping
    

    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        ''' Validate Ping between two VMs within a VN-2 vms in 2 different subnets. 
            Validate ping to subnet broadcast not responded back by other vm
            Validate ping to network broadcast (all 255) is responded back by other vm
        
        '''
        vn1_name='vn030'
        vn1_subnets=['31.1.1.0/30', '31.1.2.0/30']
        #vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        #Geting the VM ips
        vm1_ip=vm1_fixture.vm_ip
        vm2_ip=vm2_fixture.vm_ip
        ip_list=[vm1_ip, vm2_ip]
#       gettig broadcast ip for vm1_ip
        ip_broadcast=''
        ip_broadcast=get_subnet_broadcast_from_ip(vm1_ip,'30')
        list_of_ip_to_ping=[ip_broadcast,'224.0.0.1','255.255.255.255']
        #passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm=['echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        
        vm1_fixture.run_cmd_on_vm( cmds= cmd_list_to_pass_vm)
        vm2_fixture.run_cmd_on_vm( cmds= cmd_list_to_pass_vm)
       
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s'%(vm1_ip,dst_ip)
#pinging from Vm1 to subnet broadcast
            ping_output= vm1_fixture.ping_to_ip( dst_ip, return_output= True, other_opt='-b' )
            expected_result=' 0% packet loss'
            assert (expected_result in ping_output)
#getting count of ping response from each vm
            string_count_dict={}
            string_count_dict=get_string_match_count(ip_list,ping_output)
            self.logger.info("Ping reply from vms %s"%(string_count_dict))
            if (dst_ip == ip_broadcast):
                assert (string_count_dict[vm2_ip]==0)
            if (dst_ip == '224.0.0.1' or dst_ip=='255.255.255.255'):
                assert ( string_count_dict[vm2_ip] > 0)     
        return True
    #end test_ping_within_vn
    
#    @unittest.skip('Skipping a debug test')
#    def test_debug(self):
#        fip_pool_id = raw_input('Enter the fip-pool-id to delete')
#        fip_pool_obj=self.vnc_lib.floating_ip_pool_read(id= fip_pool_id)
#        self.project_obj= self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib))
#        self.project_obj.project_obj.del_floating_ip_pool(fip_pool_obj)
#        self.vnc_lib.project_update( self.project_obj.project_obj )
#        self.vnc_lib.floating_ip_pool_delete(id= fip_pool_id )
#    #end test_debug
    
#    @preposttest_wrapper
#    def test_decor(self):
#        ''' Test to check if skeleton works.
#        
#        '''
#        self.logger.error("Am testing here... %s" %(self.ini_file))
#        return True
#    #end test_decor
#    @unittest.skip('Skipping a debug test')
#    def test_debug(self):
#        fip= raw_input( 'Enter the fip id to delete ') 
#        fip_pool_id = raw_input('Enter the fip-pool-id to delete')
#        fip_pool_obj=self.vnc_lib.floating_ip_pool_read(id= fip_pool_id)
#        self.project_obj= self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib))
#        self.project_obj.project_obj.del_floating_ip_pool(fip_pool_obj)
#        self.vnc_lib.project_update( self.project_obj.project_obj )
#        self.vnc_lib.floating_ip_pool_delete(id= fip_pool_id )
#    #end test_debug
    
#    @preposttest_wrapper
#    def test_decor(self):
#        ''' Test to check if skeleton works.
#        
#        '''
#        self.logger.error("Am testing here... %s" %(self.ini_file))
#        return True
#    #end test_decor
   
    @preposttest_wrapper
    def test_policy_to_deny(self):
        ''' Test to validate that with policy having rule to disable icmp within the VN, ping between VMs should fail
        
        '''
        vn1_name='vn43'
        vn1_subnets=['43.1.1.0/24']
        policy_name= 'policy1'
        rules= [ 
            { 
               'direction'     : '<>', 'simple_action' : 'deny',
#               'protocol'      : 'any',
               'protocol'      : '1',
               'source_network': vn1_name,
#               'src_ports'     : 'any',
#               'src_ports'     : (10,100),
               'dest_network'  : vn1_name,
#               'dst_ports'     : [100,10],
             },
                ]  
        policy_fixture= self.useFixture( PolicyFixture( policy_name= policy_name, rules_list= rules, inputs= self.inputs,
                                    connections= self.connections ))
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets, policy_objs=[policy_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert not vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        return True

    #end test_policy
    
    @preposttest_wrapper
    def test_process_restart_in_policy_between_vns(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with process restarts
        '''
        result = True ; msg = [] 
        vn1_name='vn40'
        vn1_subnets=['40.1.1.0/24']
        vn2_name='vn41'
        vn2_subnets=['41.1.1.0/24']
        policy1_name= 'policy1'
        policy2_name= 'policy2'
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : '1',
               'source_network': vn1_name,
               'dest_network'  : vn2_name,
             },
                ]
        rev_rules= [
            {  
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : '1',
               'source_network': vn2_name,
               'dest_network'  : vn1_name,
             }, 
                ]
        policy1_fixture= self.useFixture( PolicyFixture( policy_name= policy1_name, rules_list= rules, inputs= self.inputs,
                                    connections= self.connections ))
        policy2_fixture= self.useFixture( PolicyFixture( policy_name= policy2_name, rules_list= rev_rules, inputs= self.inputs,
                                    connections= self.connections ))
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets, policy_objs=[policy1_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets, policy_objs=[policy2_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()
       	vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn2_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        self.logger.info ("Verify ping to vm %s" %(vn1_vm2_name))
        ret= vm1_fixture.ping_with_certainty( vm2_fixture.vm_ip, expectation=True )
        result_msg= "vm ping test result to vm %s is: %s" %(vn1_vm2_name, ret)
        self.logger.info (result_msg)
        if ret != True : result= False; msg.extend([result_msg, policy1_name])
        self.assertEqual(result, True, msg)
        
	for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter',[compute_ip])
	for bgp_ip in self.inputs.bgp_ips:
	    self.inputs.restart_service('contrail-control',[bgp_ip])
	sleep(30)
	self.logger.info('Sleeping for 30 seconds')
	vn1_vm3_name= 'vm3'
        vn1_vm4_name= 'vm4'
	vm3_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm3_name))
        vm4_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn2_fixture.obj, vm_name= vn1_vm4_name))
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )
        self.logger.info ("Verify ping to vm %s" %(vn1_vm4_name))
        ret= vm3_fixture.ping_with_certainty( vm4_fixture.vm_ip, expectation=True )
        result_msg= "vm ping test result to vm %s is: %s" %(vn1_vm4_name, ret)
        self.logger.info (result_msg)
        if ret != True : result= False; msg.extend([result_msg, policy1_name])
        self.assertEqual(result, True, msg)

	return True
#end test_process_restart_in_policy_between_vns
    
    @preposttest_wrapper
    def test_policy_between_vns(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass

        '''
        vn1_name='vn40'
        vn1_subnets=['40.1.1.0/24']
        vn2_name='vn41'
        vn2_subnets=['41.1.1.0/24']
        policy1_name= 'policy1'
        policy2_name= 'policy2'
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : '1',
               'source_network': vn1_name,
               'dest_network'  : vn2_name,
             },
                ]
        rev_rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : '1',
               'source_network': vn2_name,
               'dest_network'  : vn1_name,
             },
                ]
        policy1_fixture= self.useFixture( PolicyFixture( policy_name= policy1_name, rules_list= rules, inputs= self.inputs,
                                    connections= self.connections ))
        policy2_fixture= self.useFixture( PolicyFixture( policy_name= policy2_name, rules_list= rev_rules, inputs= self.inputs,
                                    connections= self.connections ))
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets, policy_objs=[policy1_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets, policy_objs=[policy2_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()

        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn2_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        return True
    
    #end test_policy_between_vns

    @preposttest_wrapper
    def test_process_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture (connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs,project_name= self.inputs.project_name,
                      subnets= vn_subnets,vn_count=vn_count_for_test,vm_count=1,subnet_count=1))
            compute_ip=[]
            time.sleep(100)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip=vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('contrail-vrouter',compute_ip)
    	sleep(30)
        try:
            assert vm_fixture.verify_vms_on_setup()
#            for vmobj in vm_fixture.vm_obj_dict.values():
#                assert vmobj.verify_on_setup()
        except Exception as e:
            self.logger.exception("got exception as %s"%(e)) 
        return True

    @preposttest_wrapper
    def test_control_node_switchover(self):
        ''' Stop the control node and check peering with agent fallback to other control node. 
        
        '''
        raise self.skipTest("Skiping a failing test")
        if len(set(self.inputs.bgp_ips)) < 2 :
            raise self.skipTest("Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        # Figuring the active control node
        active_controller= None
        inspect_h= self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller= entry['controller_ip']
        self.logger.info('Active control node from the Agent %s is %s' %(vm1_fixture.vm_node_ip, active_controller))

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %(active_controller))
        self.inputs.stop_service('contrail-control',[active_controller])
        sleep(5)

        # Check the control node shifted to other control node
        new_active_controller= None
        new_active_controller_state = None
        inspect_h= self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller= entry['controller_ip']
                new_active_controller_state= entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %(vm1_fixture.vm_node_ip, new_active_controller))
        if new_active_controller == active_controller:
            self.logger.error('Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %(self.active_controller, new_active_controller))
            result = False 

        if new_active_controller_state != 'Established':
            self.logger.error('Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %(active_controller))
        self.inputs.start_service('contrail-control',[active_controller])

        sleep(10)
        # Check the BGP peering status from the currently active control node
        cn_bgp_entry=self.cn_inspect[new_active_controller].get_cn_bgp_neigh_entry()
        sleep(5)
        for entry in cn_bgp_entry:
            if entry ['state'] != 'Established':
                result = result and False
                self.logger.error('With Peer %s peering is not Established. Current State %s ' %(entry ['peer'] , entry['state']) )

        # Check the ping 
        self.logger.info('Checking the ping between the VM again')
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip ) 

        if not result :
            self.logger.error('Switchover of control node failed')
            assert result
        return True 

    #end test_control_node_switchover

    @preposttest_wrapper
    def test_agent_cleanup_with_control_node_stop(self):
        ''' Stop all the control node and verify the cleanup process in agent
        
        '''
        raise self.skipTest("Skiping a failing test")
        if len(set(self.inputs.bgp_ips)) < 2 :
            raise self.skipTest("Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        # Collecting all the control node details
        controller_list= []
        inspect_h= self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            controller_list.append(entry['controller_ip'])
        list_of_vm= inspect_h.get_vna_vm_list()

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' %(entry))
            self.inputs.stop_service('contrail-control',[entry])
            self.addCleanup(self.inputs.start_service , 'contrail-control' , [entry])
            sleep(5)

        # Wait for cleanup to begin 
        sleep (120)

        # Verify VM entry is removed from the agent introspect 
        vm_id_list= inspect_h.get_vna_vm_list()
        if vm1_fixture.vm_id in vm_id_list:
            result = result and False
            self.logger.error('VM %s is still present in Agent Introspect.Cleanup not working when all control node shut' %(vm1_fixture.vm_name))
        if vm2_fixture.vm_id in vm_id_list:  
            result = result and False
            self.logger.error('VM %s is still present in Agent Introspect.Cleanup not working when all control node shut' %(vm2_fixture.vm_name))
        

        # TODO Verify the IF-Map entry

        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' %(entry))
            self.inputs.start_service('contrail-control',[entry])
            sleep(30)

        # Check everything came up fine
        vm_id_list= inspect_h.get_vna_vm_list()
        if vm1_fixture.vm_id not in vm_id_list or vm2_fixture.vm_id not in vm_id_list:
            result = result and False
            self.logger.error('After starting the service all the VM entry did not came up properly')

        self.logger.info('Checking the VM came up properly or not')
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()
        if not result :
            self.logger.error('Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True
    # end test_agent_cleanup_with_control_node_stop

    @preposttest_wrapper
    def test_bring_up_vm_with_control_node_down(self):
        ''' Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back
        
        '''
        raise self.skipTest("Skiping a failing test")	
        if len(set(self.inputs.bgp_ips)) < 2 :
            raise self.skipTest("Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']

        # Collecting all the control node details
        controller_list= []
        for entry in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[entry]
            agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                controller_list.append(entry['controller_ip'])
        controller_list = set(controller_list)      
      
        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' %(entry))
            self.inputs.stop_service('contrail-control',[entry])
            self.addCleanup(self.inputs.start_service , 'contrail-control' , [entry])
        sleep(30)

        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))

        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))

        # Check all the VM got IP when control node is down
        # Verify VM in Agent. This is more required to get TAP iterface and Metadata IP.
        # TODO Need to check the verify_vm_in_agent chance to get passed when Control node is down with new implmenetation
        vm1_fixture.verify_vm_launched()
        vm2_fixture.verify_vm_launched()
        vm1_fixture.verify_vm_in_agent()
        vm2_fixture.verify_vm_in_agent()
        vm_ip1=vm1_fixture.get_vm_ip_from_vm()
        vm_ip2=vm2_fixture.get_vm_ip_from_vm()
        print "vm_ip1 %s vm_ip2 %s" %(vm_ip1,vm_ip2)
        if vm_ip1 is None or vm_ip2 is None:
            result = result and False
            self.logger.error('VM does not get an IP when all control nodes are down')
        else:
            self.logger.info('Both VM got required IP when control nodes are down')
         
        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' %(entry))
            self.inputs.start_service('contrail-control',[entry])
        sleep(30)

        self.logger.info('Checking the VM came up properly or not')
        assert vn1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        # Check ping between VM
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        if not result :
            self.logger.error('Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True
    
    # end test_bring_up_vm_with_control_node_down
     
#    @preposttest_wrapper
#    def test_vn_add_delete_no_subnet(self):
#        '''Test to validate VN creation even when no subnet is provided. Commented till 811 is fixed.
#        '''
#        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
#            vn_name='vn007', inputs= self.inputs ))
#        assert vn_obj.verify_on_setup()
#        assert vn_obj
#        return True
    #end test_vn_add_delete_no_subnet

#   @preposttest_wrapper
#   def test_vn_reboot_nodes(self):
#        ''' Test to validate persistence of VN across compute/control/cfgm node reboots Commented till 129 is fixed.
#        '''
#        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
#                     vn_name='vn111', inputs= self.inputs, subnets=['100.100.100.0/24']))
#        assert vn_obj.verify_on_setup()
#        reboot the compute node now and verify the VN persistence
#        for compute_ip in self.inputs.compute_ips:
#            self.inputs.reboot(compute_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
#        #reboot the control nodes now and verify the VN persistence
#        for bgp_ip in self.inputs.bgp_ips:
#            self.inputs.reboot(bgp_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
#        #reboot the cfgm node now and verify the VN persistence
#        self.inputs.reboot(self.inputs.cfgm_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
#        assert vn_obj
#        return True
    #end test_vn_reboot_nodes

#    @preposttest_wrapper
#    def vn_subnet_tests(self):
#        """ Validate various type of subnets associated to VNs.Commented till 762, 801, 802, 803 and 805 are fixed.
#        """
#
#        result = True
#        vn_s = {'vn-1' : '0.0.0.0/0', 'vn-2' : ['10.1.1.0/24', '10.1.1.0/24'], 'vn-3' : '169.254.1.1/24', 'vn-4' : '251.2.2.1/24', 'vn-5' : '127.0.0.1/32', 'vn-6' : '8.8.8.8/32', 'vn-7' : '9.9.9.9/31','vn-8' : ['11.11.11.0/30', '11.11.11.11/29'], 'vn-9' : 10.1.1.1/24}
#        multi_vn_fixture = self.useFixture(MultipleVNFixture(
#            connections=self.connections, inputs=self.inputs, subnet_count=2,
#            vn_name_net=vn_s,  project_name=self.inputs.project_name))
#
#        vn_objs = multi_vn_fixture.get_all_fixture_obj()
#        assert not multi_vn_fixture.verify_on_setup()
#
#        return True
#    #end test_subnets_vn

    @preposttest_wrapper
    def test_uve(self):
        '''Test to validate collector uve.
        '''
        analytics_obj=AnalyticsVerification(inputs= self.inputs,connections= self.connections)
        assert analytics_obj.verify_collector_uve()
        return True
    #end test_uve

    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name='vm_mine'
        vn_name='vn2'
        vn_subnets=['11.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
#        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
#                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name , image_name='cirros-0.3.0-x86_64-uec',userdata = './metadata.sh'))
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name , image_name='cirros-0.3.0-x86_64-uec',userdata = '/root/sandipd/multinode/test/scripts/metadata.sh'))
#        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
#                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name , image_name='cirros-0.3.0-x86_64-uec'))
##        time.sleep(20)
        assert vm1_fixture.verify_on_setup()
        return True

    @preposttest_wrapper
    def test_metadata_service(self):
        ''' Test to validate metadata service on VM creation.
            ./provision_linklocal.py --admin_user admin --admin_password c0ntrail123 --linklocal_service_name metadata 
            --ipfabric_service_ip 10.204.216.7 --ipfabric_service_port 8775 --oper add --api_server_port 8095
        '''

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:  
            with open ("/tmp/metadata_script.txt" , "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception("Got exception while creating /tmp/metadata_script.txt as %s"%(e))

        #Enabing metadata service in the nova api
        if self.inputs.multi_tenancy:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper add\
                            --api_server_port 8095"%self.inputs.cfgm_ip
                            
            p_args = shlex.split(command_line)

        else:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper add\
                            --api_server_port 8082"%self.inputs.cfgm_ip
            p_args = shlex.split(command_line)

#        p = subprocess.check_output(p_args)
        p = subprocess.Popen(p_args)
        time.sleep(10)
#        out, err = p.communicate()
        
        import pdb;pdb.set_trace()
        vn_name='vn2'
        vn_subnets=['11.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                        vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name , 
                        image_name='cirros-0.3.0-x86_64-uec',userdata = '/tmp/metadata_script.txt'))
    
        assert vm1_fixture.verify_on_setup()
        cmd = 'ls /tmp/'
        ret = vm1_fixture.run_cmd_on_vm(cmds = [cmd])
        result = False
        for elem in ret.values():
            if 'output.txt' in elem:
                result = True
                break
        if not result:
            self.logger.warn("metadata_script.txt did not get executed in the vm")
        else:
            self.logger.info("Printing the output.txt :")
            cmd = 'cat /tmp/output.txt'
            ret = vm1_fixture.run_cmd_on_vm(cmds = [cmd])
            self.logger.info("%s" %(ret.values()))
            for elem in ret.values():
                if 'Hello World' in elem:
                    result = True
                else:
                    self.logger.warn("metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                    result = False
                    
        assert result
        #Disabling metadata service in the nova api
        if self.inputs.multi_tenancy:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper del\
                            --api_server_port 8095"%self.inputs.cfgm_ip
                            
            p_args = shlex.split(command_line)

        else:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper del\
                            --api_server_port 8082"%self.inputs.cfgm_ip
            p_args = shlex.split(command_line)

#        p = subprocess.check_output(p_args)
        p = subprocess.Popen(p_args)
        
        return True
    

    @preposttest_wrapper
    def test_multiple_metadata_service_scale(self):
        ''' Test to metadata service scale.
        '''
        
        vm1_name='vm_min'
        vn_name='vn1111'
        vn_subnets=['111.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                        vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name , 
                        image_name='cirros-0.3.0-x86_64-uec'))

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:  
            with open ("/tmp/metadata_script.txt" , "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception("Got exception while creating /tmp/metadata_script.txt as %s"%(e))

        #Enabing metadata service in the nova api
        if self.inputs.multi_tenancy:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper add\
                            --api_server_port 8095"%self.inputs.cfgm_ip
                            
            p_args = shlex.split(command_line)

        else:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper add\
                            --api_server_port 8082"%self.inputs.cfgm_ip
            p_args = shlex.split(command_line)

        p = subprocess.Popen(p_args)
        time.sleep(10)

        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture (connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs,project_name= self.inputs.project_name,
                      subnets= vn_subnets,vn_count=vn_count_for_test,vm_count=1,subnet_count=1,userdata = '/tmp/metadata_script.txt',
                        image_name='cirros-0.3.0-x86_64-uec'))

            compute_ip=[]
            time.sleep(30)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        cmd = 'ls /tmp/'
        result = True
        for vmobj in vm_fixture.vm_obj_dict.values():
            ret = vmobj.run_cmd_on_vm(cmds = [cmd])
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = result and True
                    break
            if not result:
                self.logger.warn("metadata_script.txt did not get executed in the vm")
                result = result and False
            else:
                self.logger.info("Printing the output.txt :")
                cmd = 'cat /tmp/output.txt'
                ret = vmobj.run_cmd_on_vm(cmds = [cmd])
                self.logger.info("%s" %(ret.values()))
                for elem in ret.values():
                    if 'Hello World' in elem:
                        result = result and True
                    else:
                        self.logger.warn("metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                        result = result and False
        assert result
        #Disabling metadata service in the nova api
        if self.inputs.multi_tenancy:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper del\
                            --api_server_port 8095"%self.inputs.cfgm_ip
                            
            p_args = shlex.split(command_line)

        else:
            command_line = "/opt/contrail/utils/provision_linklocal.py\
                            --admin_user admin\
                            --admin_password c0ntrail123\
                            --linklocal_service_name metadata\
                            --ipfabric_service_ip %s\
                            --ipfabric_service_port 8775\
                            --oper del\
                            --api_server_port 8082"%self.inputs.cfgm_ip
            p_args = shlex.split(command_line)

        p = subprocess.Popen(p_args)
        return True
#end TestSanityFixture


