# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
# 
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# 
import os
import signal
import re
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
import Queue
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from control_node import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
sys.path.append(os.path.realpath('scale/control-node'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from traffic.core.profile import StandardProfile, ContinuousProfile
sys.path.append(os.path.realpath('/root/contrail-test/scripts'))
sys.path.append(os.path.realpath('/root/contrail-test/scripts/ha'))
sys.path.append(os.path.realpath('/root/contrail-test/scripts/tcutils'))
from tcutils.commands import *

#from analytics_tests import *
class TestHAServiceSanity(testtools.TestCase, fixtures.TestWithFixtures):
    
#    @classmethod
    def setUp(self):
        super(TestHAServiceSanity, self).setUp()  
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
        self.ipmi_list = {}
    #end setUpClass
    
    def cleanUp(self):
        super(TestHAServiceSanity, self).cleanUp()
    #end cleanUp
    
    def runTest(self):
        pass
    #end runTest

    def ha_start(self):
        '''
        ha_start will spawn VM's and starts traffic from 
        VM - VM , VM - floating IP.
        '''
        self.vn1_name='vn100'
        self.vn1_subnets=['20.1.1.0/24']
        self.vn2_name='vn200'
        self.vn2_subnets=['50.1.1.0/24']
        self.fip_pool_name = self.inputs.fip_pool_name
        self.fvn_name = 'public-vn-200'
        self.fip_subnets = [self.inputs.fip_pool]
        self.vmlist = []
        self.vm_fixture = []
        self.vm_num = 2 
        self.jdaf_ip = '6.6.6.1'
        self.public_ip = '8.8.8.8'
        self.mx_rt = self.inputs.mx_rt
        self.secgrp_name = 'default'
        self.sport = 39100
        self.dport = 39200
        self.proto_list = ['tcp','icmp']
        self.fip = "" 
        self.count = ""
        self.sender = {} 
        self.sender_fip = {} 
        self.receiver = {} 
        self.send_node = {} 
        self.send_fip_node = {} 
        self.recv_node = {} 
        self.send_fip_host = {} 
        self.recv_host = {} 
        self.send_host = {} 
        self.host_list=[]

        for i in range(0,self.vm_num):
            self.vmlist.append("vm-test"+str(i))

        for host in self.inputs.compute_ips: 
            self.host_list.append(self.inputs.host_data[host]['name'])

        # ping gateway from VM's

        self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt))

        self.vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn2_name, inputs= self.inputs, subnets= self.vn2_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt,forwarding_mode='l2'))

#        self.fvn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.fvn_name, inputs= self.inputs, subnets= self.fip_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt))

#        self.fip_fixture = self.useFixture(FloatingIPFixture( project_name=self.inputs.project_name, inputs=self.inputs, connections=self.connections, pool_name=self.fip_pool_name, vn_id=self.fvn_fixture.vn_id))

        assert self.vn1_fixture.verify_on_setup()
        assert self.vn2_fixture.verify_on_setup()
#        assert self.fvn_fixture.verify_on_setup()
#        assert self.fip_fixture.verify_on_setup()

        host_cnt = len(set(self.inputs.compute_ips))

        for i in range(0,self.vm_num):
            node_indx = (i % host_cnt)
            self.vm_fixture.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj, self.vn2_fixture.obj], vm_name= self.vmlist[i],flavor='contrail_flavor_large',image_name='ubuntu-traffic',node_name=self.host_list[node_indx])))

        for i in range(0,self.vm_num):
            assert self.vm_fixture[i].verify_on_setup()

        for i in range(0,self.vm_num):
            out1 = self.nova_fixture.wait_till_vm_is_up( self.vm_fixture[i].vm_obj )
            if out1 == False: return {'result':out1, 'msg':"%s failed to come up"%self.vm_fixture[i].vm_name}
            else: sleep (10); self.logger.info('Will install Traffic package on %s'%self.vm_fixture[i].vm_name); self.vm_fixture[i].install_pkg("Traffic")
        '''
        self.fip_id = self.fip_fixture.create_and_assoc_fip(self.fvn_fixture.vn_id, self.vm_fixture[0].vm_id)
        self.addCleanup(self.fip_fixture.disassoc_and_delete_fip, self.fip_id)
        sleep(10)
        assert self.fip_fixture.verify_fip(self.fip_id, self.vm_fixture[0], self.fvn_fixture)
        routing_instance = self.fvn_fixture.ri_name
        '''

#        for i in range(0,self.vm_num):
#            self.vm_fixture[i].remove_security_group(secgrp='default')
#       Traffic setup
        #Set VM credentials
        for proto in self.proto_list:
            self.send_node[proto] = []
            self.sender[proto] = [] 
            if self.fip == 'True' :
                self.sender_fip[proto] = [] 
            self.receiver[proto] = [] 
            self.send_node[proto] = [] 
            self.recv_node[proto] = [] 
            self.send_host[proto] = [] 
            self.recv_host[proto] = [] 

            j = self.vm_num - 1
            for i in range(0,((self.vm_num/2))):
                if self.fip == 'True' and proto == 'icmp' :
                     self.stream_fip = Stream(protocol="ip", sport=self.sport, dport=self.dport, proto=proto, src=self.vm_fixture[i].vm_ip, dst=self.public_ip)

                self.stream = Stream(protocol="ip", sport=self.sport, dport=self.dport, proto=proto, src=self.vm_fixture[i].vm_ip, dst=self.vm_fixture[j].vm_ip)

                profile_kwargs = {'stream': self.stream}
                profile = ContinuousProfile(**profile_kwargs)

                if self.fip == 'True' and proto == 'icmp' :
                    profile_fip_kwargs = {'stream': self.stream_fip}
                    profile_fip = ContinuousProfile(**profile_fip_kwargs)

                self.send_node[proto].append(Host(self.vm_fixture[i].vm_node_ip, self.inputs.username, self.inputs.password))
                self.recv_node[proto].append(Host(self.vm_fixture[j].vm_node_ip, self.inputs.username, self.inputs.password))
                self.send_host[proto].append(Host(self.vm_fixture[i].local_ip, self.vm_fixture[i].vm_username, self.vm_fixture[i].vm_password))
                self.recv_host[proto].append(Host(self.vm_fixture[j].local_ip, self.vm_fixture[j].vm_username, self.vm_fixture[j].vm_password))

        #   Create send, receive helpers
                self.sender[proto].append(Sender("send%s" % proto, profile, self.send_node[proto][i], self.send_host[proto][i], self.inputs.logger))
                
                if self.fip == 'True' and proto == 'icmp' :
                    self.sender_fip[proto].append(Sender("sendfip%s" % proto, profile_fip, self.send_node[proto][i], self.send_host[proto][i], self.inputs.logger))

                self.receiver[proto].append(Receiver("recv%s" % proto, profile, self.recv_node[proto][i], self.recv_host[proto][i], self.inputs.logger))

        #   start traffic
                self.receiver[proto][i].start()
                self.sender[proto][i].start()

                if self.fip == 'True' and proto == 'icmp' :
                    self.sender_fip[proto][i].start()
                sleep(10)
                j = j - 1

        return True

    def ha_stop(self):
        '''
        ha_stop will stop traffic from VM - VM , VM - floating IP,
        and check if there is any drop of traffic during this run.
        '''
#       stop traffic
        j = self.vm_num - 1
        for proto in self.proto_list:
            for i in range(0,((self.vm_num/2))):

                self.sender[proto][i].stop()

                if self.fip == 'True' and proto == 'icmp' :
                    self.sender_fip[proto][i].stop()

                sleep(10)

                if proto != 'icmp' :
                    self.receiver[proto][i].stop()
                self.logger.debug("Sent: %s:  Proto : %s", self.sender[proto][i].sent,proto)

                if proto != 'icmp' :
                    self.logger.debug("Received: %s Proto : %s",self.receiver[proto][i].recv,proto)
                    recvpkts = self.receiver[proto][i].recv
                else:
                    self.logger.debug("Received: %s Proto : %s",self.sender[proto][i].recv,proto)
                    self.receiver[proto][i].stop()
                    recvpkts = self.sender[proto][i].recv

                if self.fip == 'True' and proto == 'icmp' :
                    recvpkts_fip = self.sender_fip[proto][i].recv

                print("Sent: %s:  Proto : %s"%(self.sender[proto][i].sent,proto))

                if proto != 'icmp' :
                    print("Received: %s Proto : %s"%(self.receiver[proto][i].recv,proto))
                else: 
                    print("Received: %s Proto : %s"%(self.sender[proto][i].recv,proto))

                if self.fip == 'True' and proto == 'icmp' :
                    print("Sent FIP : %s:  Proto : %s"%(self.sender_fip[proto][i].sent,proto))
                    print("Received FIP : %s Proto : %s"%(self.sender_fip[proto][i].recv,proto))

        return True


    def ha_basic_test(self):
        ''' Tests functioning of the setup by spawning 3 VMs. Verifyies
            that the VM are spawned successfully and deletes them.
        '''
        vms = []
 
#        vm_cnt = len(self.inputs.cfgm_ips) 
        vm_cnt = 1 

        for i in range(0,vm_cnt):
            vms.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj, self.vn2_fixture.obj ], vm_name= "ha_new_vm"+str(i) ,flavor='contrail_flavor_large',image_name='ubuntu-traffic')))

        for i in range(0,vm_cnt):
            assert vms[i].verify_on_setup()
            status = self.nova_fixture.wait_till_vm_is_up(vms[i].vm_obj )
            if status == False:
               self.logger.error("%s failed to come up" % vms[i].vm_name)
               return False
#            assert vms[i].ping_to_ip(self.jdaf_ip)
        sleep(30)
        for i in range(0,(vm_cnt)):
            vms[0].cleanUp()
            del vms[0]

        return True

    def service_command(self, operation, service, node):
        ''' Routine return True if "operation" was successful for "service"
            on the "node".

            operation - start/stop/restart
            node - ip address
            service - service name
        '''

        cmd = 'service %s %s' % (service, operation)
        st = 'service %s status' % service
        username= self.inputs.host_data[node]['username']
        password= self.inputs.host_data[node]['password']

        # start - if service is already running  do nothing
        if operation == 'start':
           self.logger.info("cmd: %s @ %s" % (st, node))
           status = self.inputs.run_cmd_on_server(node, st, username=username ,password=password)
           self.logger.info("status: %s " % status)
           if re.search('RUNNING', status,flags=re.I):
               ret = True 

        self.logger.info("cmd: %s @ %s" % (cmd, node))
        status = self.inputs.run_cmd_on_server(node, cmd, username=username ,password=password)
        self.logger.info("status: %s" % status)

        if service  == 'mysql':
            cmd = 'service %s status' % service
            self.logger.info("cmd: %s @ %s" % (cmd, node))
            status = self.inputs.run_cmd_on_server(node, cmd, username=username ,password=password)
            self.logger.info("status: %s" % status)

        if ((operation == 'stop') or (operation == 'restart')) and ('stop' not in status):
           self.logger.error("Failed: %s on %s" % (cmd, node))
           return False

        if operation == 'stop':
           return True

        # for start or restart ensure service has started
        ret = False
        for i in range(6):
            sleep(10)
            self.logger.info("cmd: %s @ %s" % (st, node))
            status = self.inputs.run_cmd_on_server(node, st, username=username ,password=password)
            self.logger.info("status: %s" % status)

            if re.search('RUNNING', status,flags=re.I):
               ret = True 
               break

        if not ret:
           self.logger.error("Failed: %s on %s" % (cmd, node))
           return ret

        return True

    def ha_service_restart_test(self, service, nodes):
        ''' Test service instance crash/restart
            Ensure that that system is operational when a signle service
            instance crashes/restarted. 
            Pass crietria: as defined by ha_basic_test
        '''

        sleep(10)

        self.ha_start()

        for node in nodes:
            if not self.service_command('restart', service, node):
               return False

            sleep(60);

            if not self.ha_basic_test():
               return False

        sleep(10)

        return self.ha_stop()


    def ha_service_single_failure_test(self, service, nodes):
        ''' Test single service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: as defined by ha_basic_test
        '''

        sleep(10)
#       To be enabled if we want to check traffic during serivce failures.
#       Will be covered in Full regression script for service failures.
        self.ha_start()

        for node in nodes:
            if not self.service_command('stop', service, node):
               return False

#           operations after mysql bringing mysql down taking more time.
            if service == 'mysql':
                sleep(240)
            else:
                sleep(60)

            if not self.ha_basic_test():
               self.service_command('start', service, node)
               return False

            if not self.service_command('start', service, node):
               return False

        sleep(10)
#       To be enabled if we want to check traffic during serivce failures.
#       Will be covered in Full regression script for service failures.
        return self.ha_stop() 

        return True 

    @preposttest_wrapper
    def test_ha_keystone_single_failure(self):
        ''' Test keystone service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('keystone', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_glance_single_failure(self):
        ''' Test glance service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('glance-api', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_mysql_single_failure(self):
        ''' Test mysql service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('mysql', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_api_single_failure(self):
        ''' Test nova-api service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-api', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_conductor_single_failure(self):
        ''' Test nova conductor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-conductor', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_nova_scheduler_single_failure(self):
        ''' Test nova scheduler service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('nova-scheduler', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_api_server_single_failure(self):
        ''' Test api-server service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-api', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_ifmap_single_failure(self):
        ''' Test ifmap service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('ifmap', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_schema_transformer_single_failure(self):
        ''' Test schema service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-schema', [self.inputs.cfgm_ips[0]])
        sleep(30)
        return ret

    @preposttest_wrapper
    def test_ha_discovery_single_failure(self):
        ''' Test discovery service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-discovery', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_svc_monitor_single_failure(self):
        ''' Test svc monitor service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret = self.ha_service_single_failure_test('contrail-svc-monitor', [self.inputs.cfgm_ips[0]])
        sleep(30)
        return ret

    @preposttest_wrapper
    def test_ha_control_single_failure(self):
        ''' Test contrail-control service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        ret =  self.ha_service_single_failure_test('contrail-control', [self.inputs.bgp_ips[0]])
        sleep(60)
        return ret

    @preposttest_wrapper
    def test_ha_dns_single_failure(self):
        ''' Test dns service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-dns', [self.inputs.bgp_ips[0]])

    @preposttest_wrapper
    def test_ha_named_single_failure(self):
        ''' Test named service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-named', [self.inputs.bgp_ips[0]])

    @preposttest_wrapper
    def test_ha_rabbitmq_single_failure(self):
        ''' Test rabbitmq service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('rabbitmq-server', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_zookeeper_single_failure(self):
        ''' Test zookeeper service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('zookeeper', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_cassandra_single_failure(self):
        ''' Test cassandra service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('contrail-database', [self.inputs.ds_server_ip[0]])

#    @preposttest_wrapper
#    def test_ha_haproxy_single_failure(self):
#         ''' Test mysql service instance failure
#            Ensure that that system is operational when a signle service
#            instance fails. System should bypass the failure.
#            Pass crietria: Should be able to spawn a VM 
#        '''
#        return self.ha_service_single_failure_test('haproxy', [self.inputs.cfgm_ips[0]])
 
#    @preposttest_wrapper
#    def test_ha_keepalived_single_failure(self):
#          ''' Test mysql service instance failure
#            Ensure that that system is operational when a signle service
#            instance fails. System should bypass the failure.
#            Pass crietria: Should be able to spawn a VM 
#        '''
#       return self.ha_service_single_failure_test('keepalived', [self.inputs.cfgm_ips[0]])

    @preposttest_wrapper
    def test_ha_neutron_single_failure(self):
        ''' Test neutron-server service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: Should be able to spawn a VM 
        '''
        return self.ha_service_single_failure_test('neutron-server', [self.inputs.cfgm_ips[0]])

#end TestHAServiceSanity


