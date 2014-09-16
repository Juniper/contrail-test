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
from fabric.state import connections as fab_connections
sys.path.append(os.path.realpath('/root/contrail-test/scripts'))
sys.path.append(os.path.realpath('/root/contrail-test/scripts/ha'))
sys.path.append(os.path.realpath('/root/contrail-test/scripts/tcutils'))
from tcutils.commands import *
import struct
import socket

#from analytics_tests import *
class TestHARebootSanity(testtools.TestCase, fixtures.TestWithFixtures):
    
#    @classmethod
    def setUp(self):
        super(TestHARebootSanity, self).setUp()  
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
        if self.inputs.ha_setup:
            self.ipmi_list = self.inputs.hosts_ipmi[0]
    #end setUpClass
    
    def cleanUp(self):
        super(TestHARebootSanity, self).cleanUp()
    #end cleanUp
    
    def runTest(self):
        pass
    #end runTest

    def reboot(self,ip):
        username= self.inputs.host_data[ip]['username']
        password= self.inputs.host_data[ip]['password']
        self.inputs.run_cmd_on_server(ip,'reboot', username=username ,password=password)
        return True

    def cold_reboot(self,ip,option):
        self.set_ipmi_address()
        ipmi_addr = self.get_ipmi_address(ip)
        username= self.inputs.host_data[self.inputs.cfgm_ips[0]]['username']
        password= self.inputs.host_data[self.inputs.cfgm_ips[0]]['password']
        # Move this one to install script
        test_ip = self.inputs.cfgm_ips[0]
        cmd = 'wget http://us.archive.ubuntu.com/ubuntu/pool/universe/i/ipmitool/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd , username=username ,password=password)
        cmd = 'dpkg -i /root/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd , username=username ,password=password)
        cmd = 'rm -rf /root/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd , username=username ,password=password)
        # TODO removed later , when support is there to execute test from test node.
        self.inputs.run_cmd_on_server(test_ip,cmd , username = username ,password = password)
        cmd = '/usr/bin/ipmitool -H "%s" -U %s -P %s chassis power "%s"'%(ipmi_addr,self.inputs.ipmi_username,self.inputs.ipmi_password,option)
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd , username=username ,password=password)
        # clear the fab connections
        fab_connections.clear()
        return True

    def isolate_node(self,ip,state):
        username= self.inputs.host_data[ip]['username']
        password= self.inputs.host_data[ip]['password']

        # block all traffic except ssh port for isolating the node 

        cmd = 'iptables -A INPUT -p tcp --dport 22 -j ACCEPT'
        self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
        self.logger.info('command executed  %s' %cmd)

        cmd = 'iptables -A OUTPUT -p tcp --sport 22 -j ACCEPT'
        self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
        self.logger.info('command executed  %s' %cmd)

        cmd = 'iptables -A INPUT -j %s'%(state)
        self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
        self.logger.info('command executed  %s' %cmd)

        cmd = 'iptables -A OUTPUT -j %s'%(state)
        self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
        self.logger.info('command executed  %s' %cmd)

        cmd = 'iptables -A FORWARD -j %s'%(state)
        self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
        self.logger.info('command executed  %s' %cmd)

        cmd = 'cat /proc/net/route'
        res = self.inputs.run_cmd_on_server(ip,cmd,username=username,password=password)
       
        self.get_gw(res) 

        if state == 'ACCEPT':
            cmd = 'iptables -F '
            self.inputs.run_cmd_on_server(ip,cmd, username=username ,password=password)
            self.logger.info('command executed  %s' %cmd)

        fab_connections.clear()

        return True

    def set_ipmi_address(self):
        self.ipmi_list = self.inputs.hosts_ipmi[0]
        return True 

    def get_ipmi_address(self,ip):
        return self.ipmi_list[ip] 

    def get_gw(self,routes):
        for route in routes:
            if route.startswith('Iface'):
                continue
            route_fields = route.split()
            destination = int(route_fields[1], 16)
            if destination == 0:
                gateway = int(route_fields[2], 16)
                gw = socket.inet_ntoa(struct.pack('I', gateway))
                return gw

    def get_mac(ip):
        for route in open('/proc/net/arp', 'r').readlines():
            if route.startswith(ip):
                route_fields = route.split()
                return route_fields[3]

    def ha_start(self):
        '''
        ha_start will spawn VM's and starts traffic from 
        VM - VM , VM - floating IP.
        '''
        self.vn1_name='vn1000'
        self.vn1_subnets=['30.1.1.0/24']
        self.vn2_name='vn2000'
        self.vn2_subnets=['40.1.1.0/24']
        self.fip_pool_name = self.inputs.fip_pool_name
        self.fvn_name = 'public100'
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
            self.vmlist.append("vm"+str(i))

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
        vm_cnt = 1 
#        vm_cnt = len(self.inputs.cfgm_ips) 
        for i in range(0,vm_cnt):
            vms.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj, self.vn2_fixture.obj ], vm_name= "ha_test_vm"+str(i) ,flavor='contrail_flavor_large',image_name='ubuntu-traffic')))

        for i in range(0,vm_cnt):
            assert vms[i].verify_on_setup()

            status = self.nova_fixture.wait_till_vm_is_up(vms[i].vm_obj )
            if status == False:
               self.logger.error("%s failed to come up" % vms[i].vm_name)
               return False

        for i in range(0,(vm_cnt)):
            vms[0].cleanUp()
            del vms[0]

        return True

    def ha_reboot_test(self, nodes):
        ''' Test reboot of controller nodes
            instance crashes/restarted. 
            Pass crietria: as defined by ha_basic_test
        '''
        self.ha_start()
        
        for node in nodes:

            if not self.reboot(node):
                return False

            sleep(360);

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    def ha_cold_reboot_test(self,nodes):
        ''' Test cold reboot of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''
        self.ha_start()
        
        for node in nodes:

            if not self.cold_reboot(node,'cycle'):
                return False

            sleep(360);

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    def ha_cold_shutdown_test(self,nodes):
        ''' Test cold reboot of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''

        cfgm_ips = copy.deepcopy(self.inputs.cfgm_ips)
        cfgm_control_ips = copy.deepcopy(self.inputs.cfgm_control_ips)
        bgp_ips = copy.deepcopy(self.inputs.bgp_ips)
        compute_ips = copy.deepcopy(self.inputs.compute_ips)

        self.ha_start()
        
        for node in nodes:

            if not self.cold_reboot(node,'off'):
                return False

            sleep(360)
             
            if node in self.inputs.cfgm_ips:
                cfgm_ips.remove(node)

            if node in self.inputs.cfgm_control_ips:
                cfgm_control_ips.remove(node)

            if node in self.inputs.bgp_ips:
                bgp_ips.remove(node)

            if node in self.inputs.compute_ips:
                compute_ips.remove(node)

            self.inputs.update_ip_curr(cfgm_ips=cfgm_ips,cfgm_control_ips=cfgm_control_ips,bgp_ips=bgp_ips,compute_ips=compute_ips)

#            if not self.ha_basic_test():
#                return False

            self.inputs.reset_ip_curr()

            if not self.cold_reboot(node,'on'):
                return False
            
            sleep(360)
            
            if not self.ha_basic_test():
                return False

        return self.ha_stop()

    def ha_isolate_test(self, nodes):
        ''' Test isolation of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''
        self.ha_start()
        
        for node in nodes:

            if not self.isolate_node(node,"DROP"):
                return False

            sleep(240)

#            if not self.ha_basic_test():
#               return False

            if not self.isolate_node(node,"ACCEPT"):
                return False

            sleep(240)

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    @preposttest_wrapper
    def test_ha_reboot(self):
        ret = self.ha_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        sleep(120)
        return ret

    @preposttest_wrapper
    def test_ha_cold_reboot(self):
        ret = self.ha_cold_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        sleep(120)
        return ret

    @preposttest_wrapper
    def test_ha_cold_shutdown(self):
        ret = self.ha_cold_shutdown_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        sleep(120)
        return ret

#    @preposttest_wrapper
#    def test_ha_isolate(self):
#        ret = self.ha_isolate_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
#        sleep(120)
#        return ret

#end HAReboot 


