import os
import signal
import re
import struct
import socket
import random
from fabric.state import connections as fab_connections
import test
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.commands import *
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver

class HABaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(HABaseTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        cls.nova_fixture = cls.connections.nova_fixture
#        cls.logger= cls.inputs.logger
        cls.ipmi_list = cls.inputs.hosts_ipmi[0]
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(HABaseTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
   #end remove_from_cleanups

    def reboot(self,ip):
        ''' API to reboot a node for a given IP address '''
        self.inputs.run_cmd_on_server(ip, 'reboot')
        return True

    def cold_reboot(self,ip,option):
        ''' API to power clycle node for a given IP address '''
        ipmi_addr = self.get_ipmi_address(ip)
        # ToDo: Use python based ipmi shutdown wrapper rather than ipmitool
        test_ip = self.inputs.cfgm_ips[0]
        cmd = 'wget http://us.archive.ubuntu.com/ubuntu/pool/universe/i/ipmitool/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd)
        cmd = 'dpkg -i /root/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd)
        cmd = 'rm -rf /root/ipmitool_1.8.13-1ubuntu0.1_amd64.deb'
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd)
        # TODO removed later , when support is there to execute test from test node.
        cmd = '/usr/bin/ipmitool -H "%s" -U %s -P %s chassis power "%s"'%(ipmi_addr,self.inputs.ipmi_username,self.inputs.ipmi_password,option)
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(test_ip,cmd)
        # clear the fab connections
        sleep(10)
        fab_connections.clear()
        return True

    def isolate_node(self,ip,state):
        ''' API to power cycle node for a given IP address '''
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

    def get_ipmi_address(self,ip):
        ''' API to get IPMI address for a given IP address '''
        self.ipmi_list = self.inputs.hosts_ipmi[0]
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

    def update_handles(self, hosts, service):
        ''' Updates the handles when a node is isolated or removed from list '''
        vip = self.inputs.vip['contrail']
        for host in hosts:
            if host in self.inputs.cfgm_ips:
                self.inputs.cfgm_ips[self.inputs.cfgm_ips.index(host)] = vip
            if host in self.inputs.cfgm_control_ips:
                self.inputs.cfgm_control_ips[self.inputs.cfgm_control_ips.index(host)] = vip
            if host in self.inputs.bgp_ips:
                self.inputs.bgp_ips[self.inputs.bgp_ips.index(host)] = vip
            if host in self.inputs.collector_ips:
                self.inputs.collector_ips[self.inputs.collector_ips.index(host)] = vip
            if host in self.inputs.ds_server_ip:
                self.inputs.ds_server_ip[self.inputs.ds_server_ip.index(host)] = vip
            self.inputs.ha_tmp_list.append(host)
        self.connections.update_inspect_handles()
        self.addCleanup(self.reset_handles, hosts, service=service)
        fab_connections.clear()

    def reset_handles(self, hosts, service):
        ''' resetting cfgm_ip , bgp_ips , compute_ips required for ha testing during node failures '''
        vip = self.inputs.vip['contrail']
        for host in hosts:
            if vip in self.inputs.cfgm_ips:
                self.inputs.cfgm_ips[self.inputs.cfgm_ips.index(vip)] = host
            if vip in self.inputs.cfgm_control_ips:
                self.inputs.cfgm_control_ips[self.inputs.cfgm_control_ips.index(vip)] = host
            if vip in self.inputs.bgp_ips:
                self.inputs.bgp_ips[self.inputs.bgp_ips.index(vip)] = host
            if vip in self.inputs.collector_ips:
                self.inputs.collector_ips[self.inputs.collector_ips.index(vip)] = host
            if vip in self.inputs.ds_server_ip:
                self.inputs.ds_server_ip[self.inputs.ds_server_ip.index(vip)] = host
        self.connections.update_inspect_handles()
        for host in hosts:
            if host in self.inputs.ha_tmp_list:
                self.inputs.ha_tmp_list.remove(host)
        fab_connections.clear()

    def ha_start(self):
        '''
        ha_start will spawn VM's and starts traffic from 
        VM - VM , VM - floating IP.
        '''
        self.vn1_name='vn1000'
        self.vn1_subnets=['20.1.1.0/24']
        self.vn2_name='vn2000'
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
            val = random.randint(1,100000)
            self.vmlist.append("vm-test"+str(val))
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

        self.logger.debug("In ha_basic_test.....")
        for i in range(0,vm_cnt):
            vms.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj, self.vn2_fixture.obj ], vm_name= "ha_new_vm"+str(random.randint(1,100000)) ,flavor='contrail_flavor_large',image_name='ubuntu-traffic')))
        for i in range(0,vm_cnt):
            assert vms[i].verify_on_setup()
            status = self.nova_fixture.wait_till_vm_is_up(vms[i].vm_obj )
            if status == False:
               self.logger.error("%s failed to come up" % vms[i].vm_name)
               return False
#            assert vms[i].ping_to_ip(self.jdaf_ip)
        sleep(30)
        for i in range(0,(vm_cnt)):
            vms[i].cleanUp()
            self.remove_from_cleanups(vms[i])
#            self._cleanups.remove(vms[i])
            del vms[i]

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
        if service  == 'mysql' or service == 'haproxy':
            cmd = 'service %s status' % service
            self.logger.info("cmd: %s @ %s" % (cmd, node))
            status = self.inputs.run_cmd_on_server(node, cmd, username=username ,password=password)
            self.logger.info("status: %s" % status)
        if ((operation == 'stop') or (operation == 'restart')):
            if service == 'haproxy':
                if ('not running' not in status):
                    self.logger.error("Failed: %s on %s" % (cmd, node))
                    return False
            else :
                if ('stop' not in status):
                    self.logger.error("Failed: %s on %s" % (cmd, node))
                    return False

        if operation == 'stop':
            self.addCleanup(self.service_command, 'start', service, node)
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

    def ha_service_restart(self, service, nodes):
        ''' Test service instance crash/restart
            Pass crietria: service restarted successfully 
        '''
        sleep(10)
        for node in nodes:
            if not self.service_command('restart', service, node):
               return False
        return True 

    def ha_service_single_failure_test(self, service, nodes):
        ''' Test single service instance failure
            Ensure that that system is operational when a signle service
            instance fails. System should bypass the failure.
            Pass crietria: as defined by ha_basic_test
        '''

        if not self.check_status('openstack-status',self.inputs.cfgm_ips):
            self.logger.info("Failed to start openstack service")
            return False
        if not self.check_status('contrail-status',self.inputs.cfgm_ips):
            self.logger.info("Failed to start contrail service")
            return False
        sleep(10)
        self.ha_start()
        for node in nodes:
            if not self.service_command('stop', service, node):
                return False
            if service == 'haproxy':
                self.update_handles(hosts=[node], service=service)
#           operations after mysql bringing mysql down taking more time.
            if service == 'mysql':
                sleep(240)
            else:
                sleep(120)
            if not self.ha_basic_test():
                self.logger.error("Error in Launching new ha_new_vm after failure")
                self.service_command('start', service, node)
                if service == 'haproxy':
                    self.reset_handles([node], service=service)
                    sleep(120)
                return False
            if not self.service_command('start', service, node):
                self.logger.error("Error in starting service ")
                if service == 'haproxy':
                    self.reset_handles([node], service=service)
                    sleep(120)
                return False
        sleep(30)
        if service == 'haproxy':
            self.reset_handles([node], service=service)
            sleep(240)

        return self.ha_stop() 

    def check_status(self,cmd,nodes):
        for node in nodes:
            self.logger.info("cmd: %s @ %s" % (cmd, node))
            output = self.inputs.run_cmd_on_server(node, cmd)
            for line in output.split("\n"):
                status = None
                service_status = line.split(":")
                service = service_status[0]
                service = service.replace('openstack-','')
                if len(service_status) == 2:
                    status = service_status[1].strip()
                if (status == "dead" or status == "failed"):
                    if not self.service_command('start', service, node):
                        return False
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

            sleep(420);

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

            sleep(420);

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    def ha_cold_shutdown_test(self,nodes):
        ''' Test cold reboot of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''

        self.ha_start()
        
        for node in nodes:

            if not self.cold_reboot(node,'off'):
                return False

            sleep(420)

            self.update_handles(hosts=[node])

            if not self.ha_basic_test():
                self.cold_reboot(node,'on')
                sleep(420)
                return False

            self.reset_handles([node])
#            self.inputs.reset_ip_curr()

            if not self.cold_reboot(node,'on'):
                return False
            
            sleep(420)
            
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


