import os
import signal
import re
import struct
import socket
import random
import subprocess
from fabric.state import connections as fab_connections
import test_v1
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.commands import *
from tcutils.util import get_random_name
trafficdir = os.path.join(os.path.dirname(__file__), '../../tcutils/pkgs/Traffic')
sys.path.append(trafficdir)
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from fabric.api import local

class HABaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(HABaseTest, cls).setUpClass()
        cls.nova_h = cls.connections.nova_h
        cls.orch = cls.connections.orch
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        if hasattr(cls.inputs, "hosts_ipmi"): 
            cls.ipmi_list = cls.inputs.hosts_ipmi[0]
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(HABaseTest, cls).tearDownClass()
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        self.remove_api_from_cleanups(fix.cleanUp)
   #end remove_from_cleanups

    def remove_api_from_cleanups(self, api):
        for cleanup in self._cleanups:
            if api in cleanup:
                self._cleanups.remove(cleanup)
                break
   #end remove_api_from_cleanups

    def reboot(self,ip):
        ''' API to reboot a node for a given IP address '''
        self.inputs.run_cmd_on_server(ip, 'reboot')
        sleep(420)
        self.connections.update_inspect_handles()
        fab_connections.clear()
        return True

    def cold_reboot(self,ip,option):
        ''' API to power clycle node for a given IP address '''
        if option != 'on':
            cmd = 'if ! grep -Rq "GRUB_RECORDFAIL_TIMEOUT" /etc/default/grub; then echo "GRUB_RECORDFAIL_TIMEOUT=10" >> /etc/default/grub; update-grub ; fi ;sed -i s/GRUB_CMDLINE_LINUX_DEFAULT.*/GRUB_CMDLINE_LINUX_DEFAULT=\"nomodeset\"/g /etc/default/grub ; update-grub;'
            self.logger.info('command executed  %s' %cmd)
            self.inputs.run_cmd_on_server(ip, cmd)
            # This is required for hardware initialization failure
            cmd = 'echo  "blacklist mei" > /etc/modprobe.d/mei.conf;'
            self.inputs.run_cmd_on_server(ip, cmd)
            cmd = 'echo  "blacklist mei_me" > /etc/modprobe.d/mei_me.conf;'
            self.inputs.run_cmd_on_server(ip, cmd)
            cmd = 'if ! grep -Rq "mei_me" /etc/modprobe.d/blacklist.conf ; then echo "blacklist mei_me" >> /etc/modprobe.d/blacklist.conf; fi ;'
            self.inputs.run_cmd_on_server(ip, cmd)

        ipmi_addr = self.get_ipmi_address(ip)
        cmd = 'ipmitool -H "%s" -U %s -P %s chassis power "%s"'%(ipmi_addr,self.inputs.ipmi_username,self.inputs.ipmi_password,option)
        self.logger.info('command executed  %s' %cmd)
        local(cmd)
        # clear the fab connections
        sleep(20)
        self.connections.update_inspect_handles()
        fab_connections.clear()
        sleep(420)
        return True

    def isolate_node(self,ctrl_ip,state):
        ''' API to isolate node for a given IP address '''
        host_ip = self.inputs.host_data[ctrl_ip]['host_ip']
        ''' Since its not a multi interface returning it'''
        if host_ip == ctrl_ip:
            raise self.skipTest("This test is not supported when data/control ip are same")
        username= self.inputs.host_data[host_ip]['username']
        password= self.inputs.host_data[host_ip]['password']
        cmd = 'intf=$(ip addr show | grep %s | awk \'{print $7}\') ; ifconfig $intf %s' %(ctrl_ip,state)
        self.logger.info('command executed  %s' %cmd)
        self.inputs.run_cmd_on_server(host_ip,cmd,username=username,password=password)
        fab_connections.clear()
        sleep(420)
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

    def update_handles(self, hosts, service=None):
        ''' Updates the handles when a node is isolated or removed from list '''
        vip = self.inputs.contrail_internal_vip
        for host in hosts:
            if host in self.inputs.cfgm_ips:
                self.inputs.cfgm_ips[self.inputs.cfgm_ips.index(host)] = vip
            if host in self.inputs.cfgm_control_ips:
                self.inputs.cfgm_control_ips[self.inputs.cfgm_control_ips.index(host)] = vip
            if service != 'haproxy':
                if host in self.inputs.bgp_ips:
                    self.inputs.bgp_ips[self.inputs.bgp_ips.index(host)] = vip
            if host in self.inputs.collector_ips:
                self.inputs.collector_ips[self.inputs.collector_ips.index(host)] = vip
            if host in self.inputs.ds_server_ip:
                self.inputs.ds_server_ip[self.inputs.ds_server_ip.index(host)] = vip
            self.inputs.ha_tmp_list.append(host)
            if self.inputs.cfgm_ip == host:
                self.inputs.cfgm_ip = vip
                self.connections.update_vnc_lib_fixture()
        self.connections.update_inspect_handles()
        if service:
            self.addCleanup(self.reset_handles, hosts, service=service)
        fab_connections.clear()

    def reset_handles(self, hosts, service=None):
        ''' resetting cfgm_ip , bgp_ips , compute_ips required for ha testing during node failures '''
        vip = self.inputs.contrail_internal_vip
        for host in hosts:
            if vip in self.inputs.cfgm_ips:
                self.inputs.cfgm_ips[self.inputs.cfgm_ips.index(vip)] = host
            if vip in self.inputs.cfgm_control_ips:
                self.inputs.cfgm_control_ips[self.inputs.cfgm_control_ips.index(vip)] = host
            if service != 'haproxy':
                if vip in self.inputs.bgp_ips:
                    self.inputs.bgp_ips[self.inputs.bgp_ips.index(vip)] = host
            if vip in self.inputs.collector_ips:
                self.inputs.collector_ips[self.inputs.collector_ips.index(vip)] = host
            if vip in self.inputs.ds_server_ip:
                self.inputs.ds_server_ip[self.inputs.ds_server_ip.index(vip)] = host
            if self.inputs.cfgm_ip == vip:
                self.inputs.cfgm_ip = host
                self.connections.update_vnc_lib_fixture()
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
   #     self.host_list= self.connections.nova_h.get_hosts()
        self.host_list = self.connections.orch.get_hosts()

        for i in range(0,self.vm_num):
            self.vmlist.append(get_random_name("vm-test"))

        # ping gateway from VM's
        if self.inputs.orchestrator =='vcenter':
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt))
            assert self.vn1_fixture.verify_on_setup()
        else:

            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt))
            self.vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn2_name, inputs= self.inputs, subnets= self.vn2_subnets,router_asn=self.inputs.router_asn, enable_dhcp=False,disable_gateway=True))
#           self.fvn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.fvn_name, inputs= self.inputs, subnets= self.fip_subnets,router_asn=self.inputs.router_asn, rt_number=self.mx_rt))
#           self.fip_fixture = self.useFixture(FloatingIPFixture( project_name=self.inputs.project_name, inputs=self.inputs, connections=self.connections, pool_name=self.fip_pool_name, vn_id=self.fvn_fixture.vn_id))
            assert self.vn1_fixture.verify_on_setup()
            assert self.vn2_fixture.verify_on_setup()


#        assert self.fvn_fixture.verify_on_setup()
#        assert self.fip_fixture.verify_on_setup()
        host_cnt = len(self.host_list)
        for i in range(0,self.vm_num):
            node_indx = (i % host_cnt)
            if self.inputs.orchestrator =='vcenter':
                self.vm_fixture.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj ], vm_name= self.vmlist[i],image_name='ubuntu-traffic',node_name=self.host_list[node_indx])))

            else:
                self.vm_fixture.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj,self.vn2_fixture.obj ], vm_name= self.vmlist[i],image_name='ubuntu-traffic',node_name=self.host_list[node_indx])))
#               self.vm_fixture.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj ], vm_name= self.vmlist[i],flavor='contrail_flavor_large',image_name='ubuntu-traffic',node_name=self.host_list[node_indx])))

        for i in range(0,self.vm_num):
            assert self.vm_fixture[i].verify_on_setup()
        for i in range(0,self.vm_num):
            if self.inputs.orchestrator =='vcenter':
                out1 = self.orch.wait_till_vm_is_active( self.vm_fixture[i].vm_obj )
            else:
                out1 = self.nova_h.wait_till_vm_is_up( self.vm_fixture[i].vm_obj )

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

    def ha_stop(self, skip_packet_loss_check=False):
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
                self.logger.info("Checking for packet drops")
                self.logger.info("Sent: %s:  Proto : %s"%(self.sender[proto][i].sent,proto))
                if proto != 'icmp' :
                    self.logger.info("Received: %s Proto : %s"%(self.receiver[proto][i].recv,proto))
                    err_msg = "Sent and received packet mismatch for {} protocol".format(proto)
                    if not skip_packet_loss_check:
                        assert abs(self.sender[proto][i].sent - self.receiver[proto][i].recv) < 6, err_msg
                    else:
                        self.logger.info("Skipping packet loss check")
                else:
                    self.logger.info("Received: %s Proto : %s"%(self.sender[proto][i].recv,proto))
                    err_msg = "Sent and received packet mismatch for {} protocol".format(proto)
                    if not skip_packet_loss_check:
                        assert abs(self.sender[proto][i].sent - self.sender[proto][i].recv) < 6, err_msg
                    else:
                        self.logger.info("Skipping packet loss check")
                if self.fip == 'True' and proto == 'icmp' :
                    self.logger.info("Sent FIP : %s:  Proto : %s"%(self.sender_fip[proto][i].sent,proto))
                    self.logger.info("Received FIP : %s Proto : %s"%(self.sender_fip[proto][i].recv,proto))
                    err_msg = "Sent and received FIP packet mismatch for {} protocol".format(proto)
                    if not skip_packet_loss_check:
                        assert abs(self.sender_fip[proto][i].sent - self.sender_fip[proto][i].recv) < 6 , err_msg
                    else:
                        self.logger.info("Skipping packet loss check")

        return True


    def ha_basic_test(self, disable_node=False):
        ''' Tests functioning of the setup by spawning 3 VMs. Verifyies
            that the VM are spawned successfully and deletes them.
        '''
        vms = []
#        vm_cnt = len(self.inputs.cfgm_ips)
        vm_cnt = 1

        self.logger.debug("In ha_basic_test.....")
        for i in range(0,vm_cnt):
            if disable_node:
                vms.append(self.useFixture(VMFixture(
                    project_name= self.inputs.project_name,
                    connections= self.connections,
                    vn_objs = [ self.vn1_fixture.obj ], 
                    vm_name= get_random_name("ha_new_vm"),
                    image_name='ubuntu-traffic',
                    node_name='disable')))
            else:
                vms.append(self.useFixture(VMFixture(
                    project_name= self.inputs.project_name,
                    connections= self.connections,
                    vn_objs = [ self.vn1_fixture.obj ], 
                    vm_name= get_random_name("ha_new_vm"),
                    image_name='ubuntu-traffic')))
        for i in range(0,vm_cnt):
            assert vms[i].verify_on_setup()
            if self.inputs.orchestrator =='vcenter':
                status = self.orch.wait_till_vm_is_active(vms[i].vm_obj )
            else:
                status = self.nova_h.wait_till_vm_is_up(vms[i].vm_obj )
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

    def service_command(self, operation, service, node, container=None):
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
                if not re.findall('not running|stop', status):
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

    def ha_service_restart_test(self, service, nodes, container=None):
        ''' Test service instance crash/restart
            Ensure that that system is operational when a signle service
            instance crashes/restarted.
            Pass crietria: as defined by ha_basic_test
        '''

        sleep(10)
        assert self.ha_start(), "Basic HA setup failed"
        for node in nodes:
            if not self.service_command('restart', service, node,
                                        container=container):
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
            if not self.service_command('restart', service, node,
                                        container=container):
               return False
        return True

    def ha_service_single_failure_test(self, service, nodes, container=None):
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
        assert self.ha_start(), "Basic HA setup failed"
        for node in nodes:
            if not self.service_command('stop', service, node,
                                        container=container):
                return False
            if service == 'haproxy':
                self.update_handles(hosts=[node], service=service)
#           operations after mysql bringing mysql down taking more time.
            if service == 'mysql' or service == 'haproxy':
                sleep(240)
            else:
                sleep(120)
            if not self.ha_basic_test():
                self.logger.error("Error in Launching new ha_new_vm after failure")
                self.service_command('start', service, node,
                                     container=container)
                if service == 'haproxy':
                    self.reset_handles([node], service=service)
                    sleep(240)
                return False
            if not self.service_command('start', service, node,
                                        container=container):
                self.logger.error("Error in starting service ")
                if service == 'haproxy':
                    self.reset_handles([node], service=service)
                    sleep(240)
                return False
        sleep(30)
        if service == 'haproxy':
            self.reset_handles([node], service=service)
            sleep(240)
            if not self.ha_basic_test():
                return False

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
                    if not self.service_command('start', service, node,
                                                container='openstack'):
                        return False
        return True

    def ha_reboot_test(self, nodes):
        ''' Test reboot of controller nodes
            instance crashes/restarted.
            Pass crietria: as defined by ha_basic_test
        '''
        assert self.ha_start(), "Basic HA setup failed"

        for node in nodes:

            if not self.reboot(node):
                return False

#            sleep(420);

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    def ha_cold_reboot_test(self,nodes):
        ''' Test cold reboot of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''
        assert self.ha_start(), "Basic HA setup failed"

        for node in nodes:

            if not self.cold_reboot(node,'cycle'):
                return False

            if not self.ha_basic_test():
               return False

        return self.ha_stop()

    def ha_reboot_all_test(self,nodes,mode):
        ''' Test cold reboot of compute nodes
            Pass crietria: as defined by ha_basic_test
        '''
        assert self.ha_start(), "Basic HA setup failed"

        for node in nodes:
            if mode == 'ipmi':
                if not self.cold_reboot(node,'cycle'):
                    return False
            else:
                if not self.reboot(node):
                    return False

        if not self.ha_basic_test():
            return False

        return self.ha_stop()

    def ha_cold_shutdown_test(self,nodes):
        ''' Test cold reboot of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''
        assert self.ha_start(), "Basic HA setup failed"

        for node in nodes:

            if not self.cold_reboot(node,'off'):
                return False
            self.addCleanup(self.cold_reboot, node,'on')
            self.update_handles(hosts=[node])
            if not self.ha_basic_test():
                self.cold_reboot(node,'on')
                return False
            if not self.cold_reboot(node,'on'):
                return False
            self.reset_handles([node])
            self.remove_api_from_cleanups(self.cold_reboot)
            self.remove_api_from_cleanups(self.reset_handles)
            if not self.ha_basic_test():
                return False

        return self.ha_stop()

    def ha_isolate_test(self, nodes):
        ''' Test isolation of controller nodes
            Pass crietria: as defined by ha_basic_test
        '''
        assert self.ha_start(), "Basic HA setup failed"
        for node in nodes:
            self.addCleanup(self.isolate_node, node,'up')
            if not self.isolate_node(node,"down"):
                return False
            host_ip = self.inputs.host_data[node]['host_ip']
            self.update_handles(hosts=[host_ip])
            if not self.ha_basic_test():
                self.isolate_node(node,"up")
                return False
            self.reset_handles([host_ip])
            if not self.isolate_node(node,"up"):
                return False
            self.remove_api_from_cleanups(self.isolate_node)
            self.remove_api_from_cleanups(self.reset_handles)
            if not self.ha_basic_test():
                return False

        return self.ha_stop()

    @retry(delay=5, tries=3)
    def _is_container_up(self, host_ip, container_name):

        verify_command = "docker ps -f NAME=%s -f status=running 2>/dev/null | grep -v POD" \
            % (container_name)
        output = self.inputs.run_cmd_on_server(
            server_ip=host_ip,
            issue_cmd=verify_command,
            username=self.inputs.inputs.username,
            password=self.inputs.inputs.password,
            as_sudo=True)
        if not output or 'Up' not in output:
            self.logger.warn('Container is not up on host %s'%(host_ip))
            return False
        self.logger.info("Container {} is UP after restart on host {}".format(
            container_name,
            host_ip))
        return True

    def node_failure_check(self, host_ips, service_list, skip_packet_loss_check=False):
        '''
        Finds out nodes on which different service containers are running
        Reboots every node one after the other
        Verifies data and VM creation during these node failures
        '''
        self.logger.info("Find node IPs on which the below mentioned services are running")
        self.logger.info("{}".format(service_list))
        hosts_list_combined = []
        reboot_shell_cmd = "echo \"sleep 10 ; reboot -f \" > \/tmp\/reboot.sh"
        chmod_cmd = "chmod +x \/tmp\/reboot.sh"
        reboot_cmd = " \/tmp\/reboot.sh "
        for service_name in service_list:
            self.logger.info("Running hard reboot test for nodes running {} service".format(service_name))
            hosts_list, container_name = self.get_node_ip_list(service_name, host_ips)
            if not hosts_list[:-1]:
                self.logger.error("Not enough HA nodes to do node failure test")
                assert False, "Not enough HA nodes to do node failure test"
            hosts_list_combined.extend(hosts_list)
        hosts_list_combined = list(set(hosts_list_combined))
        self.logger.info("Hosts list covering services {} : {}".format(
            service_list, hosts_list_combined))
        if not self.ha_start():
            self.logger.error("Error in ha_start")
            return False
        for host_ip in hosts_list_combined:
            compute_ips_modified = False
            collector_ips_modified = False
            self.logger.info("Hard rebooting the node {}".format(host_ip))
            self.inputs.run_cmd_on_server(
                server_ip=host_ip,
                issue_cmd=reboot_shell_cmd,
                username=self.inputs.inputs.username,
                password=self.inputs.inputs.password,
                pty=True,
                as_sudo=True)
            self.inputs.run_cmd_on_server(
                server_ip=host_ip,
                issue_cmd=chmod_cmd,
                username=self.inputs.inputs.username,
                password=self.inputs.inputs.password,
                pty=True,
                as_sudo=True)
            self.inputs.run_cmd_on_server(
                server_ip=host_ip,
                issue_cmd=reboot_cmd,
                username=self.inputs.inputs.username,
                password=self.inputs.inputs.password,
                pty=True,
                as_sudo=True,
                as_daemon=True)
            if host_ip in self.inputs.collector_ips:
                self.logger.info("Removing {} from self.collector_ips list".format(
                    host_ip))
                self.logger.debug("self.collector_ips: {}".format(self.inputs.collector_ips))
                self.inputs.collector_ips.remove(host_ip)
                self.logger.debug("self.collector_ips after removal: {}".format(
                    self.inputs.collector_ips))
                collector_ips_modified = True
            if host_ip in self.inputs.compute_ips:
                self.logger.info("Removing {} from self.inputs.compute_ips".format(host_ip))
                self.inputs.compute_ips.remove(host_ip)
                compute_ips_modified = True
            self.logger.info("Calling update_inspect_handles")
            self.connections.update_inspect_handles()
            node_down = True
            while node_down:
                attempt = 0
                ping_successful = subprocess.check_output(["ping", "-c", "1", host_ip])
                if ping_successful:
                    self.logger.info("Node {} is up after hard reboot".format(host_ip))
                    node_down = False
                else:
                    attempt += 1
                    self.logger.info("Node {} not yet up after reboot. Retrying... Attempt {} of 100".format(
                        host_ip,
                        attempt))
                    time.sleep(3)
                    if attempt > 100:
                        assert False, "Node {} is not up after hard reboot".format(host_ip)
            self.logger.info("Sleeping 10 seconds for services to come up")
            time.sleep(10)
            self.logger.info("Test VM creation after hard rebooting node{}".format(host_ip))
            assert self.ha_basic_test(),"VM creation failed after hard rebooting node{}".format(host_ip)
            self.logger.info("VM creation test PASSED after hard rebooting node{}".format(host_ip))
            self.logger.info("Sleeping for 5 seconds")
            time.sleep(5)
            if collector_ips_modified:
                self.logger.info("Appending {} to self.collector_ips list".format(
                    host_ip))
                self.logger.debug("self.collector_ips: {}".format(self.inputs.collector_ips))
                self.inputs.collector_ips.append(host_ip)
            if compute_ips_modified:
                self.logger.info("Appending {} to self.compute_ips list".format(
                    host_ip))
                self.logger.debug("self.compute_ips: {}".format(self.inputs.compute_ips))
                self.inputs.compute_ips.append(host_ip)
            self.logger.info("Moving on to next Node...")
        self.logger.info("No more nodes left")
        self.logger.info("Checking for packet loss")
        if not self.ha_stop(skip_packet_loss_check=skip_packet_loss_check):
            self.logger.error("Error in ha_stop")
            return False

    def get_node_ip_list(self, service_name, host_ips):
        hosts_list = [] # List of hosts running the desired service as a container
        container_found = False
        container_name = ''
        for host_ip in host_ips:
            self.logger.info("Getting list of running containers")
            cmd = 'docker ps 2>/dev/null | grep -v "/pause\|/usr/bin/pod" | awk \'{print $NF}\''
            output = self.inputs.run_cmd_on_server(host_ip, cmd, as_sudo=True)
            if not output:
                self.logger.info("No running containers found in host {}".format(host_ip))
                continue
            containers = [x.strip('\r') for x in output.split('\n')]
   
            try: 
                for name in CONTRAIL_SERVICES_CONTAINER_MAP[service_name]:
                    container_name_tmp = next((container for container in containers if name in container), None)
                    if container_name_tmp:
                        container_found = True
                        container_name = container_name_tmp
                        self.logger.info("Found container. Container name: {}".format(container_name))
                        break
            except KeyError,e:
                self.logger.error("""Entry missing in CONTRAIL_SERVICES_CONTAINER_MAP for
                    service \"{}\"""".format(service_name))
                assert False,"""Entry missing in CONTRAIL_SERVICES_CONTAINER_MAP for
                    service \"{}\"""".format(service_name)
            if not container_name_tmp:
                self.logger.debug("{} container not running/found in host {}".format(
                    service_name,
                    host_ip))
            else:
                hosts_list.append(host_ip)
                self.logger.info("Found the desired container {} in {}".format(
                    container_name,
                    host_ip))
                self.logger.info("Adding {} to hosts list".format(host_ip))
                self.logger.info("hosts list: {}".format(hosts_list))
        self.logger.info("Checked all hosts.")
        assert container_found, "Desired service container {} not found in any of the hosts".format(
            service_name)
        self.logger.info("Found container {} in hosts {}".format(
            container_name,
            hosts_list))

        return hosts_list, container_name

    def reboot_service(self, service_name, host_ips, stop_service=False, node_failure=False):

        hosts_list, container_name = self.get_node_ip_list(service_name, host_ips)
        collector_ips_modified = False
        compute_ips_modified = False
        openstack_ips_modified = False

        if stop_service:
            if 'agent' in service_name:
                self.logger.info("Stopping nova compute on this node so that \
                    this node is not selected for VM creation")
                issue_cmd_stop = 'docker stop %s -t 10; docker stop nova_compute'% (container_name)
            else:
                issue_cmd_stop = 'docker stop %s -t 10' % (container_name)
            
            self.logger.debug("Issue command: {}".format(issue_cmd_stop))
            if not hosts_list[:-1]:
                self.logger.error("Not enough HA nodes to do container STOP test")
                assert False, "Not enough HA nodes to do container STOP test"
            if not self.ha_start():
                self.logger.error("Error in ha_start")
                return False
            
            for host_ip in hosts_list:
                self.logger.info('Running %s on %s' %(issue_cmd_stop, host_ip))
                self.inputs.run_cmd_on_server(
                    server_ip=host_ip,
                    issue_cmd=issue_cmd_stop,
                    username=self.inputs.inputs.username,
                    password=self.inputs.inputs.password,
                    pty=True,
                    as_sudo=True)
                self.addCleanup(self.start_containers ,container_name, [host_ip])
                if 'agent' in service_name:
                    self.addCleanup(self.start_containers ,'nova_compute', [host_ip])
                
                if service_name == 'agent':
                    self.logger.info("Sleeping for 90 seconds after stopping nova\
                        compute so that hypervisor state goes down")
                    time.sleep(90)
                if host_ip in self.inputs.openstack_ips:
                    self.logger.info("Removing {} from self.inputs.openstack_ips list".format(
                        host_ip))
                    self.logger.debug("self.inputs.openstack_ips: {}".format(self.inputs.openstack_ips))
                    self.inputs.openstack_ips.remove(host_ip)
                    self.logger.debug("self.inputs.openstack_ips after removal: {}".format(
                        self.inputs.openstack_ips))
                    openstack_ips_modified = True
                if host_ip in self.inputs.collector_ips:
                    self.logger.info("Removing {} from self.inputs.collector_ips list".format(
                        host_ip))
                    self.logger.debug("self.collector_ips: {}".format(self.inputs.collector_ips))
                    self.inputs.collector_ips.remove(host_ip)
                    self.logger.debug("self.collector_ips after removal: {}".format(
                        self.inputs.collector_ips))
                    collector_ips_modified = True
                if host_ip in self.inputs.compute_ips:
                    self.logger.info("Removing {} from self.inputs.compute_ips".format(host_ip))
                    self.inputs.compute_ips.remove(host_ip)
                    compute_ips_modified = True
                self.logger.info("Calling update_inspect_handles")
                self.connections.update_inspect_handles()
                self.logger.info("Test VM creation after rebooting {} service".format(
                    service_name))
                if 'agent' in service_name:
                    assert self.ha_basic_test(
                        disable_node=True),"VM creation failed after {} service was restarted".format(
                        service_name)
                else:
                    assert self.ha_basic_test(),"VM creation failed after {} service was restarted".format(
                        service_name)
                self.logger.info("VM creation test PASSED after stopping {} service on node {}".format(
                    service_name, host_ip))
                self.logger.info("Sleeping for 5 seconds before starting the stopped container")
                time.sleep(5)
 
                self.logger.info("Starting the container {} after VM and data verification".format(
                    container_name))
                if 'agent' in service_name:
                    issue_cmd_start = 'docker start %s ; docker start nova_compute' % (container_name)
                else:
                    issue_cmd_start = 'docker start %s ' % (container_name)

                self.logger.info('Running %s on %s' %(issue_cmd_start, host_ip))
                self.inputs.run_cmd_on_server(
                    server_ip=host_ip,
                    issue_cmd=issue_cmd_start,
                    username=self.inputs.inputs.username,
                    password=self.inputs.inputs.password,
                    pty=True,
                    as_sudo=True)
                if collector_ips_modified:
                    self.logger.info("Appending {} to self.inputs.collector_ips list".format(
                        host_ip))
                    self.logger.debug("self.inputs.collector_ips: {}".format(self.inputs.collector_ips))
                    self.inputs.collector_ips.append(host_ip)
                    collector_ips_modified = False
                if compute_ips_modified: 
                    self.logger.info("Appending {} to self.inputs.compute_ips list".format(
                        host_ip))
                    self.logger.debug("self.inputs.compute_ips: {}".format(self.inputs.compute_ips))
                    self.inputs.compute_ips.append(host_ip)
                    compute_ips_modified = False
                if openstack_ips_modified: 
                    self.logger.info("Appending {} to self.inputs.openstack_ips list".format(
                        host_ip))
                    self.logger.debug("self.inputs.openstack_ips: {}".format(self.inputs.openstack_ips))
                    self.inputs.openstack_ips.append(host_ip)
                    openstack_ips_modified = False
                self.logger.info("Sleeping for 60 seconds before restarting the next container")
                self.logger.info("Waiting for hypervisor state to change to Up")
                time.sleep(60)
                assert self._is_container_up(host_ip, container_name), "Service {} is not up \
                    after stopping and starting".format(service_name)
                self.logger.info(
                    "Service {} is up after stopping and starting".format(service_name))
            if 'agent' in service_name:
                if not self.ha_stop(skip_packet_loss_check=True):
                    self.logger.error("Error in ha_stop")
                    return False
            else:
                if not self.ha_stop():
                    self.logger.error("Error in ha_stop")
                    return False
        else:
            issue_cmd = 'docker restart %s -t 5' % (container_name)
            if not self.ha_start():
                self.logger.error("Error in ha_start")
                return False
            for host_ip in hosts_list:
                self.logger.info('Running %s on %s' %(issue_cmd, host_ip))
                self.inputs.run_cmd_on_server(
                    server_ip=host_ip,
                    issue_cmd=issue_cmd,
                    username=self.inputs.inputs.username,
                    password=self.inputs.inputs.password,
                    pty=True,
                    as_sudo=True)

                assert self._is_container_up(host_ip, container_name), "Service {} is not up \
                    after restart".format(service_name)
                self.logger.info("Service {} is up after restart".format(service_name))
                self.logger.info("Test VM creation after rebooting {} service".format(
                    service_name))
                if 'agent' in service_name:
                    assert self.ha_basic_test(
                        disable_node=True),"VM creation failed after {} service was restarted".format(
                        service_name)
                else:
                    assert self.ha_basic_test(),"VM creation failed after {} service was restarted".format(
                        service_name)
                
                self.logger.info("VM creation test PASSED after rebooting {} service".format(
                    service_name))
                self.logger.info("Sleeping for 10 seconds before restarting the next container")
                time.sleep(10)
            self.logger.info("Running HA stop after restarting {} service".format(
                service_name))
            if 'agent' in service_name:
                if not self.ha_stop(skip_packet_loss_check=True):
                    self.logger.error("Error in ha_stop")
                    return False
            else:
                if not self.ha_stop():
                    self.logger.error("Error in ha_stop")
                    return False

        self.logger.info("Sleeping for 5 seconds...")
        time.sleep(5)
        if not stop_service:
            self.logger.info("VM creation and data validations passed after service reboot")
        else:
            self.logger.info("VM creation and data validations passed after service stop")
        return True

    def start_containers(self, container_name, hosts_list):
        self.logger.info("Starting the container {} after VM and data verification".format(
                    container_name))
        issue_cmd_start = 'docker start %s ' % (container_name)

        for host_ip in hosts_list:
            self.logger.info('Running %s on %s' %(issue_cmd_start, host_ip))
            self.inputs.run_cmd_on_server(
                server_ip=host_ip,
                issue_cmd=issue_cmd_start,
                username=self.inputs.inputs.username,
                password=self.inputs.inputs.password,
                pty=True,
                as_sudo=True)
