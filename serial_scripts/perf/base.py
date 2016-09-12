import os
import signal
import re
import struct
import socket
import random

import test_v1
import re
from common.connections import ContrailConnections
#from fabric.state import connections as fab_connections
#import test_v1
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.commands import *
import threading
import thread
import time
import fixtures
from multiprocessing import Process
import multiprocessing as mp

#class PerfBase(test.BaseTestCase):
class PerfBase(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(PerfBase, cls).setUpClass()
#        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
#				cls.inputs, ini_file = cls.ini_file, \
#				logger = cls.logger)
#        cls.isolated_creds.setUp()
#        cls.project = cls.isolated_creds.create_tenant() 
#        cls.isolated_creds.create_and_attach_user_to_tenant()
#        cls.inputs = cls.isolated_creds.get_inputs()
#        cls.connections = cls.isolated_creds.get_conections() 
        cls.nova_h = cls.connections.nova_h
        cls.orch = cls.connections.orch
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.encap_type = ["MPLSoUDP","MPLSoGRE","VXLAN"]
        #cls.encap_type = ["VXLAN"]
        cls.results = 'logs/results_%s'%random.randint(0,100000)
        cls.results_file = open(cls.results,"aw")
        cls.process_list = ['qemu','vhost']
        #cls.process_list = ['qemu']
        cls.duration = 100
        cls.timeout = cls.duration + 60
        cls.nova_cpu = ['8-15','24-31'] 
        cls.nova_cpu0 = ['0-7','16-23']
        cls.family = ''
        cls.host_list = cls.connections.orch.get_hosts()
        cls.host_cpu_cores_8 = {}
        cls.host_cpu_cores_24 = {}
        cls.host_cpu_cores_0 = {}
        cls.host_cpu_cores_16 = {}
        cls.bw ='10g'
        cls.vm_num = 1

        for host in cls.host_list:
            if not cls.set_perf_mode(host):
                self.logger.error("Not able to set perf mode ")
                return False
#            if not cls.set_nova_vcpupin(host,cls.nova_cpu[0]):
#                self.logger.error("Not able to set vcpu in nova.conf")
#                return False

#        cls.logger= cls.inputs.logger
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.results_file.close() 
        super(PerfBase, cls).tearDownClass()
    #end tearDownClass 

    def launch_vm_on_nodes(self,hosts,family,vm_num):
        '''
        Launching VMs on specified hosts based on family 
        '''
        self.vn1_name='vn10001'
        self.vn1_subnets=['20.1.1.0/24']
        self.vm_fixtures = []
        self.vm_num = vm_num 

        if family == 'v6':
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections=cls.connections,vn_name=self.vn1_name, inputs= self.inputs,router_asn=self.inputs.router_asn, rt_number=self.inputs.mx_rt))
        else:
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=self.inputs.mx_rt))

        assert self.vn1_fixture.verify_on_setup()

        for host in hosts:
            for i in range(0,self.vm_num):
                vm_name = "vm-test"+str(random.randint(1,100000))
                self.vm_fixtures.append(self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, vn_objs = [ self.vn1_fixture.obj ], vm_name= vm_name,flavor='contrail_flavor_small',image_name='ubuntu-traffic',node_name=host)))
        #    for proc in self.process_list:
        #        if not self.update_process_cpu(host,proc):
        #            self.logger.error("Not able to pin cpu :%s "%proc)

        for i in range(0,len(self.vm_fixtures)):
            assert self.vm_fixtures[i].verify_on_setup()

        for i in range(0,len(self.vm_fixtures)):
            if self.inputs.orchestrator =='vcenter':
                ret = self.orch.wait_till_vm_is_active( self.vm_fixtures[i].vm_obj )
            else:
                ret = self.nova_h.wait_till_vm_is_up( self.vm_fixtures[i].vm_obj )

            if ret == False: return {'result':ret,'msg':"%s failed to come up"%self.vm_fixtures[i].vm_name}

        for host in list(set(hosts)):
            for proc in self.process_list:
                if not self.update_process_cpu(host,proc):
                    self.logger.error("Not able to pin cpu :%s "%proc)

        for i in range(0,len(self.vm_fixtures)):
            if not self.start_v6_server(self.vm_fixtures[i]):
                self.logger.error("Not able start v6 server")
                return False

        return True

    def run_perf_tests(self,test_id,mode,proto,family,bw):
        #import pdb;pdb.set_trace()
        for host in self.host_list:
            self.host_cpu_cores_8[host] = ['8','9','10','11','12','13','14','15']
            self.host_cpu_cores_24[host] = ['24','25','26','27','28','29','30','31']
            self.host_cpu_cores_0[host] = ['0','1','2','3','4','5','6','7']
            self.host_cpu_cores_16[host] = ['16','17','18','19','20','21','22','23']
            self.bw = bw
            if self.bw == '10g':
                if not self.update_vrouter_sysctl(host,self.host_cpu_cores_8[host]):
                    self.logger.error("Error in updating sysctl")
                    return False
            else: 
                self.vm_num = 4 
                if not self.set_perf_mode_disable(host):
                    self.logger.error("Not able to set perf mode ")
                    return False
                if not self.set_nova_vcpupin(host,self.nova_cpu0[0]):
                    self.logger.error("Not able to set vcpu in nova.conf")
                    return False

        self.inputs.set_af(family)

        self.print_results("==================================================================\n")
        #import pdb;pdb.set_trace()
        if mode == 'different':
            self.print_results("DIFFERENT COMPUTE NODES\n")
            if not self.launch_vm_on_nodes([self.host_list[0],self.host_list[1]],family,self.vm_num):
                self.logger.error("Failed to launch VMs")
        elif mode == 'same':
            self.print_results("SAME COMPUTE NODES\n")
            if not self.launch_vm_on_nodes([self.host_list[0],self.host_list[0]],family,self.vm_num):
                self.logger.error("Failed to launch VMs")

        if self.bw == '10g':
            if test_id == 'THROUGHPUT':
                ret = self.throughput_test(mode,proto)

            elif test_id == 'LATENCY':
                ret = self.latency_test(mode,proto)
        else:
            if test_id == 'THROUGHPUT':
                ret = self.throughput_test_40g(mode,proto)

        self.print_results("==================================================================\n")

        return ret

    def throughput_test_40g(self,mode,proto):
        threads = []
        ip_list = []
        thread_id = 0
        for id in range(0,len(self.encap_type)):
            threads = []
            self.update_encap_mode(self.inputs.host_data[self.inputs.cfgm_ip]['host_ip'],self.encap_type[id])
            if proto == 'TCP':
                try:
                    for th_id in range(0,self.vm_num):
                        src_id = th_id
                        dst_id = th_id + self.vm_num 
                        if not self.update_tap_mtu(self.vm_fixtures[src_id].get_host_of_vm(self.vm_fixtures[src_id].vm_obj),self.vm_fixtures[src_id].tap_intf[self.vn1_fixture.vn_fq_name]['name']):
                            self.logger.error("ERROR in TCP throughput test")
                            return False

                        if not self.update_tap_mtu(self.vm_fixtures[dst_id].get_host_of_vm(self.vm_fixtures[dst_id].vm_obj),self.vm_fixtures[dst_id].tap_intf[self.vn1_fixture.vn_fq_name]['name']):
                            self.logger.error("ERROR in TCP throughput test")
                            return False

                        if not self.run_tcp_throughput_40g(self.vm_fixtures[src_id],self.vm_fixtures[dst_id],self.duration,20):
                            self.logger.error("ERROR in TCP throughput test")
                            return False

                    for th_id in range(0,self.vm_num):
                        src_id = th_id
                        dst_id = th_id + self.vm_num 
                        ip_list.append(self.vm_fixtures[src_id].local_ip)
                    #import pdb;pdb.set_trace() 
                    cmd = '(nohup ./start.sh 2>&1 &) ; sleep 5'
                    if not self.run_parallel_cmds_on_vms(self.vm_fixtures[0].vm_node_data_ip,ip_list,[cmd],True):
                        self.logger.error("ERROR parallel commands")
                        return False

                    time.sleep(self.timeout)

                    for th_id in range(0,self.vm_num):
                        src_id = th_id
                        dst_id = th_id + self.vm_num 
                        if not self.get_results(self.vm_fixtures[src_id]):
                            self.logger.error("ERROR in getting results")
                            return False
                except:
                    self.logger.error("Unable to create thread \n")
                
            if proto == 'UDP':
                if not self.run_udp_throughput(self.vm_fixtures[0],self.vm_fixtures[1],self.duration):
                    self.logger.error("ERROR in UDP throughput test")
                    return False


    def throughput_test(self,mode,proto):
        for id in range(0,len(self.encap_type)):
            self.update_encap_mode(self.inputs.host_data[self.inputs.cfgm_ip]['host_ip'],self.encap_type[id])
            if proto == 'TCP':
                if not self.run_tcp_throughput(self.vm_fixtures[0],self.vm_fixtures[1],self.duration):
                    self.logger.error("ERROR in TCP throughput test")
                    return False
            if proto == 'UDP':
                if not self.run_udp_throughput(self.vm_fixtures[0],self.vm_fixtures[1],self.duration):
                    self.logger.error("ERROR in UDP throughput test")
                    return False

    def latency_test(self,mode,proto):
        for id in range(0,len(self.encap_type)):
            self.update_encap_mode(self.inputs.host_data[self.inputs.cfgm_ip]['host_ip'],self.encap_type[id])
            if proto == 'TCP':
                if not self.run_tcp_latency(self.vm_fixtures[0],self.vm_fixtures[1].vm_ip,self.duration):
                    self.logger.error("ERROR in TCP Request/Response test")
                    return False
            if proto == 'UDP':
                if not self.run_udp_latency(self.vm_fixtures[0],self.vm_fixtures[1].vm_ip,self.duration):
                    self.logger.error("ERROR in UDP Request/Response test")
                    return False
        return True 

    def run_tcp_throughput_40g(self,src_vm_hdl,dest_vm_hdl,duration,flows):
        for payload in  [ 64, 128, 512, 1400, 16348 ]:
        #for payload in  [16348]:
            perf_list = []
            threads = []
            thread_id = 0
            for iterate in range(0,1):
                # Create a thread and get the pps for each iteration.
                
                if self.inputs.get_af() == 'v6':
                    cmd = 'rm -rf start.sh; rm -rf perf.txt ; for i in {1..%s} ; do (echo \"netperf -H %s -6 -p 12000 -l %s -vv -- -m %s >> perf.txt &\" >> start.sh );done; chmod +x start.sh; sleep 5'% (flows,dest_vm_hdl.vm_ip,duration,payload)
                else:
                    cmd = 'rm -rf start.sh; rm -rf perf.txt ; for i in {1..%s} ; do (echo \"netperf -H %s -l %s -vv -- -m %s >> perf.txt &\" >> start.sh );done; chmod +x start.sh; sleep 5'% (flows,dest_vm_hdl.vm_ip,duration,payload)
                time.sleep(5)
                src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
                res= "PAYLOAD : %s \n"%(payload)
                self.logger.info("Result : %s "%res)
        return True

    def start_traffic(self,src_vm_hdl):
        cmd = '(nohup ./start.sh 2>&1 &) ; sleep 5'
        time.sleep(5)
        src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        return True

    def get_results(self,src_vm_hdl):
        perf_list = []
        cmd = 'sed s/^TCP.*//g perf.txt'
        src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        res = src_vm_hdl.return_output_cmd_dict[cmd]
        self.logger.info("Result : %s "%res)
        res = [line.strip() for line in res.split('\n') if line.strip() and 'sudo:' not in line]
        total_perf = 0
        for line in res:
            total_perf = total_perf + float(line)
            self.logger.info("line : %s "%line)
        perf_list.append(total_perf)
        perf_list.sort()
        time.sleep(5)
        res= "TCP %s THROUGHPUT : %s : \n"%(self.inputs.get_af(),perf_list[len(perf_list)-1])
        self.logger.info("Result : %s "%res)
        self.print_results(res)
        return True

    def run_tcp_throughput(self,src_vm_hdl,dest_vm_hdl,duration):
        for payload in  [ 64, 128, 512, 1400, 16348 ]:
        #for payload in  [1400]:
            perf_list = []
            threads = []
            thread_id = 0
            for iterate in range(0,3):
                # Create a thread and get the pps for each iteration.
                
                if self.inputs.get_af() == 'v6':
                    cmd = '(nohup netperf -H %s -6 -p 12000 -l %s -vv -- -m %s > perf.txt 2>&1 &); sleep 5'% (dest_vm_hdl.vm_ip,duration,payload)
                else:
                #    cmd = 'netperf -H %s -l %s -vv -- -m %s '% (dest_vm_hdl.vm_ip,duration,payload)
                    cmd = '(nohup netperf -H %s -l %s -vv -- -m %s > perf.txt 2>&1 &); sleep 5'% (dest_vm_hdl.vm_ip,duration,payload)
                time.sleep(5)
                src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
                time.sleep(self.timeout)
                cmd = 'cat perf.txt'
                src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
                res = src_vm_hdl.return_output_cmd_dict[cmd]
                self.logger.info("Result : %s "%res)
                res= res.replace("\r", "").replace("\t","")
                res= res.split("\n")
                for line in res:
                    self.logger.info("line : %s "%line)
                perf_list.append(float(res[2]))
                perf_list.sort()
            time.sleep(5)
            res= "PAYLOAD : %s TCP %s THROUGHPUT : %s : \n"%(payload ,self.inputs.get_af(),perf_list[len(perf_list)-1])
            self.logger.info("Result : %s "%res)
            self.print_results(res)
        return True

    def run_udp_throughput(self,src_vm_hdl,dest_vm_hdl,duration):
        for payload in  [ 64, 128, 512, 1400, 16348 ]:
        #for payload in  [1400]:
            perf_list = []
            perf_dict = {}
            threads = []
            thread_id = 0
            for iterate in range(0,3):
                if self.inputs.get_af() == 'v6':
                    cmd = '(nohup netperf -H %s -t UDP_STREAM -6 -p 12000 -l %s -- -m %s > perf.txt 2>&1 &); sleep 5'% (dest_vm_hdl.vm_ip,duration,payload)
                else :
                    cmd = '(nohup netperf -H %s -t UDP_STREAM -l %s -- -m %s > perf.txt 2>&1 &); sleep 5'% (dest_vm_hdl.vm_ip,duration,payload)

                time.sleep(5)
                src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
                time.sleep(self.timeout)
                cmd = 'cat perf.txt'
                src_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
                res= src_vm_hdl.return_output_cmd_dict[cmd]
                self.logger.info("Result : %s "%res)
                res= res.replace("\r", "").replace("\t","")
                res= res.split("\n")
                send = re.split('\s+',res[6]);
                recv = re.split('\s+',res[7]);
                perf_dict[float(recv[3])] = float(send[5])
                perf_list.append(float(recv[3]))
                perf_list.sort()
                print perf_dict
            time.sleep(5)
            res = "PAYLOAD : %s UDP %s THROUGHPUT send : %s recv : %s \n"%(payload , self.inputs.get_af(),perf_dict[(perf_list[len(perf_list)-1])],(perf_list[len(perf_list)-1]))
            self.logger.info("Result : %s "%res)
            self.print_results(res)
        return True

    def run_tcp_latency(self,client_hdl,ip,duration):
        perf_list = []
        for iterate in range(0,3):
            if self.inputs.get_af() == 'v6':
                cmd = '(nohup netperf -H %s -6 -p 12000 -t TCP_RR -l %s -vv > perf.txt 2>&1 &); sleep 5'% (ip,duration)
            else:
                cmd = '(nohup netperf -H %s -t TCP_RR -l %s -vv > perf.txt 2>&1 &); sleep 5'% (ip,duration)
            client_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
            time.sleep(self.timeout)
            cmd = 'cat perf.txt'
            client_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
            res= client_hdl.return_output_cmd_dict[cmd]
            self.logger.info("Result : %s "%res)
            res = res.replace("\r", "").replace("\t","")
            res = res.split("\n")
            for line in res:
                self.logger.info("line : %s "%line)
            perf_list.append(float(res[2]))
            perf_list.sort()
        res = "TCP %s Request/Response : %s : \n"%(self.inputs.get_af(),perf_list[len(perf_list)-1])
        self.logger.info("Result : %s "%res)
        self.print_results(res)
        return True

    def run_udp_latency(self,client_hdl,ip,duration):
        perf_list = []
        for iterate in range(0,3):
            if self.inputs.get_af() == 'v6':
                cmd = '(nohup netperf -H %s -6 -p 12000 -t UDP_RR -l %s -vv > perf.txt 2>&1 &); sleep 5'% (ip,duration)
            else:
                cmd = '(nohup netperf -H %s -t UDP_RR -l %s -vv > perf.txt 2>&1 &); sleep 5'% (ip,duration)
            client_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
            time.sleep(self.timeout)
            cmd = 'cat perf.txt'
            client_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
            res= client_hdl.return_output_cmd_dict[cmd]
            self.logger.info("Result : %s "%res)
            res = res.replace("\r", "").replace("\t","")
            res = res.split("\n")
            for line in res:
                self.logger.info("line : %s "%line)
            perf_list.append(float(res[2]))
            perf_list.sort()
        res = "UDP %s Request/Response : %s : \n"%(self.inputs.get_af(),perf_list[len(perf_list)-1])
        self.logger.info("Result : %s "%res)
        self.print_results(res)
        return True

    def print_results(self,result):
        self.results_file.write(result)

    def update_process_cpu(self,host,name):
        cmd = 'ps ax | pgrep %s'%name
        res = self.inputs.run_cmd_on_server(host, cmd)
        res = res.replace("\r","")
        res = res.split("\n")
        for id in res:
            self.logger.info("Host %s Process Id : %s "%(host,id))
            cmd = 'taskset -pc %s'%id
            res = self.inputs.run_cmd_on_server(host, cmd)
            res = res.split(" ")
            self.logger.info("cpu mask :%s "%res[5])

            if re.findall("8-15",res[5]):
               if not self.set_task_pin(host,self.host_cpu_cores_8[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
            elif re.findall("24-31",res[5]):
                if not self.set_task_pin(host,self.host_cpu_cores_24[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
            elif re.findall("0-7",res[5]):
                if not self.set_task_pin(host,self.host_cpu_cores_0[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
            elif re.findall("16-23",res[5]):
                if not self.set_task_pin(host,self.host_cpu_cores_16[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
            elif re.findall("0-31",res[5]):
                if not self.set_task_pin(host,self.host_cpu_cores_0[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
            else:
                if not self.set_task_pin(host,self.host_cpu_cores_8[host],id):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
        return True

    def update_tap_mtu(self,host,tap_intf):
        cmd = 'ifconfig %s mtu 8600 ; ifconfig %s txqueuelen 100000'%(tap_intf,tap_intf)
        res = self.inputs.run_cmd_on_server(host, cmd)
        return True


    def get_cpu_core(self,cpu_id):
        if len(cpu_id):
            return cpu_id.pop(0) 
        else:
            return False

    def set_task_pin(self,host,cpu_id,pid):
        cpu_core = self.get_cpu_core(cpu_id)
        if not cpu_core:
            self.logger.error("Not able to get cpu core")
            return False
        cmd = 'taskset -a -pc %s %s'%(cpu_core,pid)
        rese= self.inputs.run_cmd_on_server(host, cmd)
        cmd = 'taskset -pc %s'%pid
        res = self.inputs.run_cmd_on_server(host, cmd)
        res = res.split(" ")
        self.logger.info("cpu mask :%s "%res[5])
        if res[5] != cpu_core:
            self.logger.error("cpu is not pinned :%s : %s "%(res[5],cpu_core))
            return False
        return True 

    def update_vrouter_sysctl(self,host,cpu_id):
        cpu_core = self.get_cpu_core(cpu_id)
        if not cpu_core:
            self.logger.error("Not able to get cpu core")
            return False
        cmd='sysctl -w \"net.vrouter.q3=%s\"'%cpu_core
        self.inputs.run_cmd_on_server(host, cmd)
        cpu_core = self.get_cpu_core(cpu_id)
        if not cpu_core:
            self.logger.error("Not able to get cpu core")
            return False
        cmd='sysctl -w \"net.vrouter.q2=%s\"'%cpu_core
        self.inputs.run_cmd_on_server(host, cmd)
        return True

    def update_encap_mode(self,host,mode):
        cmd = '/usr/bin/python /opt/contrail/utils/provision_encap.py --api_server_ip 127.0.0.1 --api_server_port 8082 --encap_priority %s --vxlan_vn_id_mode "automatic" --oper add --admin_user "admin" --admin_password "contrail123"'%(mode)
        out = self.inputs.run_cmd_on_server(host, cmd)
        if not re.findall("Updated",out):
            self.logger.error("Encapsulation not updated :%s "%out)
            return False
        res = ('Encapsulation Type :%s\n'%mode)
        self.print_results(res)
        return True

    @classmethod
    def set_perf_mode(self,host):
        cmd='for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor ; do echo performance > $f; cat $f; done'
        out = self.inputs.run_cmd_on_server(host, cmd)
        cmd='service  irqbalance stop'
        out = self.inputs.run_cmd_on_server(host, cmd)
        cmd = 'cat /etc/*-release'
        out = self.inputs.run_cmd_on_server(host, cmd)
        if re.findall('Ubuntu',out):
            cmd='mac=$(maclist=$(ifconfig vhost0 | awk {\'print $5\'}) ; echo $maclist | sed s/MTU.*$//g) ; \
                intfs=$(ifconfig | grep $mac | awk {\'print $1\'} | sed s/vhost0//g | sed s/bond0//g ); \
                for intf in $intfs ; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g); \
                do echo "c0" > /proc/irq/"$i"/smp_affinity ; done ; done '
        else:
             cmd='intfs=$(cat /proc/net/bonding/bond0 | grep Interface | awk {\'print $3\'} ); \
                for intf in $intfs ; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g); \
                do echo "8000" > /proc/irq/"$i"/smp_affinity ; done ; done '
        out = self.inputs.run_cmd_on_server(host, cmd)
        return True

    @classmethod
    def set_perf_mode_disable(self,host):
        cmd='service irqbalance start'
        out = self.inputs.run_cmd_on_server(host, cmd)
        return True

    @classmethod
    def set_nova_vcpupin(self,host,cpu):
        cmd='openstack-config --set /etc/nova/nova.conf DEFAULT vcpu_pin_set %s'%cpu
        out = self.inputs.run_cmd_on_server(host, cmd)
        cmd='service nova-compute restart'
        out = self.inputs.run_cmd_on_server(host, cmd)
        return True

    def start_v6_server(self,client_hdl):
        cmd = 'sudo ifconfig eth0 mtu 8600;ifconfig eth0 txqueuelen 100000; netserver -6 -p 12000 && sleep 5'
        client_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        res = client_hdl.return_output_cmd_dict[cmd]
        self.logger.info("Result : %s "%res)
        res= res.replace("\r", "").replace("\t","")
        #res= res.split("\n")
        if not re.findall('Starting netserver',res):
            self.logger.error("Starting netserver failed : %"%res)
            return False
        return True       

    def get_remote_pps(self,dest_vm_hdl,delay):
        time.sleep(delay)
        cmd = 'ls'
        dest_vm_hdl.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        res = dest_vm_hdl.return_output_cmd_dict[cmd]
        self.logger.info("PPS : %s "%res)
        return True

    def start_pps(self,vm_fix,delay):
        return True
        time.sleep(delay/2)
        tap_intf = vm_fix.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        cmd = 'cat /sys/class/net/%s/statistics/tx_packets ; sleep 1 ;  cat /sys/class/net/%s/statistics/tx_packets'%(tap_intf,tap_intf)
        #cmd = 'cat /sys/class/net/%s/statistics/tx_bytes && cat /sys/class/net/%s/statistics/rx_bytes '%(tap_intf,tap_intf)
        host = vm_fix.node_name
        res= self.inputs.run_cmd_on_server(host, cmd)
        (rx,rx1) = res.split("\n")
        self.logger.info("PPS : %s "%res)
        cmd = 'cat /sys/class/net/%s/statistics/rx_packets ; sleep 1 ;  cat /sys/class/net/%s/statistics/rx_packets'%(tap_intf,tap_intf)
        res= self.inputs.run_cmd_on_server(host, cmd)
        (tx,tx1) = res.split("\n")
        self.logger.info("PPS : %s "%res)
        #res= "%s,%s\n"%(int(tx1)-int(tx),int(rx1)-int(rx))
        #cmd = 'echo %s >> pps.txt'%result
        #res= self.inputs.run_cmd_on_server(host, cmd)
        res= "PPS : RX %s  TX %s DURATION : %s IP : %s\n"%(int(tx1)-int(tx),int(rx1)-int(rx),delay,vm_fix.vm_ip)
        self.logger.info(res)
        self.print_results(res)
        return True

    def get_pps(self,host):
        cmd = 'cat pps.txt'
        res = self.inputs.run_cmd_on_server(host, cmd)
        lines = res.split("\n")
        #res = "PPS : RX %s  TX %s\n"%(int(tx1)-int(tx),int(rx1)-int(rx))
        #self.logger.info(res)
        #self.print_results(res)

    def run_parallel_cmds_on_vms(self,host,ip_list, cmds=[],as_sudo=False, timeout=30, as_daemon=False):
        '''run cmd on VMs in parallel
        '''
        self.return_output_cmd_dict = {}
        self.return_output_values_list = []
        cmdList = cmds
        vm_username='ubuntu'
        vm_password='ubuntu'
        output = ''
        try:
            self.orch.put_key_file_to_host(self.inputs.host_data[host]['host_ip'])
            fab_connections.clear()
            with hide('everything'):
                with settings(
                    host_string='%s@%s' % (self.inputs.host_data[host]['username'], self.inputs.host_data[host]['host_ip']),
                    password=self.inputs.host_data[host]['password'],
                        warn_only=True, abort_on_prompts=False):
                    for cmd in cmdList:
                        self.logger.debug('Running Cmd on %s %s' % (ip_list , cmd))
                        output = run_parallel_on_node( ip_list, username=vm_username, password=vm_password, cmds=cmd)
                        self.logger.debug(output)
                        self.return_output_values_list.append(output)
                    self.return_output_cmd_dict = dict(
                        zip(cmdList, self.return_output_values_list))
            return self.return_output_cmd_dict
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from VM')
            return self.return_output_cmd_dict
