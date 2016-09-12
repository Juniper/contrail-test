import sys
import os
import subprocess
import signal
import re
import struct
import socket
import random
#from fabric.state import connections as fab_connections
import test_v1
import re
from common.connections import ContrailConnections
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.servicechain.mirror.verify import VerifySvcMirror
from common.servicechain.mirror.config import ConfigSvcMirror
from serial_scripts.perf.base import PerfBase
from tcutils.commands import *
import threading
import thread
import time
import copy

class PerfBaseIxia(PerfBase,VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(PerfBaseIxia, cls).setUpClass()
        cls.nova_h = cls.connections.nova_h
        cls.orch = cls.connections.orch
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.encap_type = ["MPLSoUDP","MPLSoGRE","VXLAN"]
        cls.spirent_linux_user = 'root'
        cls.spirent_linux_passwd = 'n1keenA'
        cls.family = ''
        cls.ixia_linux_host = '10.87.132.179'
        cls.ixia_host = '10.87.132.18'
        cls.spirent_linux_host = '10.87.132.185'
        cls.set_cpu_cores = 4 
        cls.set_si = 1
        cls.dpdk_svc_scaling = False
        cls.nova_flavor= { '2':'contrail_flavor_2cpu','4':'contrail_flavor_4cpu', '8':'contrail_flavor_8cpu','m':'contrail_flavor_multiq'}
        #cls.nova_flavor= { '4':'contrail_flavor_4cpu', '8':'contrail_flavor_8cpu'}
        cls.vrouter_mask_list = ['0xf','0x3f','0xff','0xf000f']
#        cls.logger= cls.inputs.logger
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.results_file.close() 
        super(PerfBaseIxia, cls).tearDownClass()
        #self.set_nova_flavor_key_delete()
    #end tearDownClass 


    def run_perf_tests(self,test_id,mode,proto,family):

        vm_num = 1

        for host in self.host_list:
            self.host_cpu_cores_8[host] = ['8','9','10','11','12','13','14','15']
            self.host_cpu_cores_24[host] = ['24','25','26','27','28','29','30','31']
            self.host_cpu_cores_0[host] = ['0','1','2','3','4','5','6','7']
            self.host_cpu_cores_16[host] = ['16','17','18','19','20','21','22','23']
            if not self.update_vrouter_sysctl(host,self.host_cpu_cores_8[host]):
                self.logger.error("Error in updating sysctl")
                return False

        self.inputs.set_af(family)

        self.print_results("==================================================================\n")

        if mode == 'different':
            self.print_results("DIFFERENT COMPUTE NODES\n")
            if not self.launch_dpdk_vms([self.host_list[0],self.host_list[1]],family,vm_num):
                self.logger.error("Failed to launch VMs")
        elif mode == 'same':
            self.print_results("SAME COMPUTE NODES\n")
            if not self.launch_dpdk_vms([self.host_list[0],self.host_list[0]],family,vm_num):
                self.logger.error("Failed to launch VMs")

        if test_id == 'THROUGHPUT':
            ret = self.dpdk_throughput_test(mode,proto)

        self.print_results("==================================================================\n")

        return ret

    def dpdk_throughput_test(self,mode,proto):
        for id in range(0,len(self.encap_type)):
            self.update_encap_mode(self.inputs.host_data[self.inputs.cfgm_ip]['host_ip'],self.encap_type[id])
            if proto == 'TCP':
                if not self.run_dpdk_throughput_test(self.vm_fixtures[0],self.vm_fixtures[1],self.duration):
                    self.logger.error("ERROR in TCP throughput test")
                    return False
            if proto == 'UDP':
                if not self.run_dpdk_throughput_test(self.vm_fixtures[0],self.vm_fixtures[1],self.duration):
                    self.logger.error("ERROR in UDP throughput test")
                    return False
        return True

    def run_dpdk_throughput_test(self,src_vm_hdl,dest_vm_hdl,duration):
        result = self.start_dpdk_l3fwd(dest_vm_hdl,duration)
        #import pdb ; pdb.set_trace()
        #for payload in  [ 64, 128, 512, 1400 ]:
        for payload in  [64]:
            perf_list = []
            time.sleep(5)
            result = self.start_dpdk_ptkgen(src_vm_hdl,dest_vm_hdl,payload)
            time.sleep(200)
            result = "PAYLOAD : %s TCP %s THROUGHPUT :  : \n"%(payload ,self.inputs.get_af())
            self.logger.info("Result : %s "%result)
            self.print_results(result)
            self.get_dpdk_results(src_vm_hdl)
            #import pdb ; pdb.set_trace()
        time.sleep(10)
        return True

    def start_dpdk_l2fwd(self,vm_fix,delay):
        time.sleep(5)
        vm_fix.vm_username = 'root'
        vm_fix.vm_password = 'c0ntrail123'
        cmd = '(nohup ./start_l2fwd_app.sh >/dev/null 2>&1 &) ; sleep 5'
        vm_fix.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        return True

    def start_dpdk_l3fwd(self,vm_fix,delay):
        time.sleep(5)
        vm_fix.vm_username = 'root'
        vm_fix.vm_password = 'c0ntrail123'
        cmd = 'cd /root/vrouter-pktgen-tests/ ; (nohup ./dpdk_l3fwd.sh >/dev/null 2>&1 &) ; sleep 5'
        vm_fix.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        return True


    def start_dpdk_ptkgen(self,vm_fix_src,vm_fix_dst,payload):
        host = vm_fix_src.node_name
        vm_fix_src.vm_username = 'root'
        vm_fix_src.vm_password = 'c0ntrail123'
        cmd = 'rm /root/pktgen2vrouter*.log'
        vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        cmd = 'sed -i -e s/12.1.1.4/%s/g /root/bin/dpdkgen.lua'%vm_fix_src.vm_ip
        vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        cmd = 'sed -i -e s/12.1.1.3/%s/g /root/bin/dpdkgen.lua'%vm_fix_dst.vm_ip
        vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        cmd = 'sed -i -e s/"size =.*"/"size = %s;"/g /root/bin/dpdkgen.lua'%payload
        vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        #import pdb;pdb.set_trace()
        cmd = 'cd /root/bin/ ; (nohup ./dpdk_run.py >/dev/null  2>&1 &) ; sleep 5'
        vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        return True

    def get_dpdk_results(self,vm_fix_src):
        host = vm_fix_src.node_name
        vm_fix_src.vm_username = 'root'
        vm_fix_src.vm_password = 'c0ntrail123'
        cmd = 'cat /root/pktgen2vrouter*.log'
        result = vm_fix_src.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        result = vm_fix_src.return_output_cmd_dict[cmd]
        self.logger.info("Result : %s "%result)
        #import pdb;pdb.set_trace()
        result = result.replace("\r", "").replace("\t","")
        self.print_results(result)
        return True

    def set_nova_compute_service(self,host,mode):
        username = self.inputs.host_data[self.inputs.openstack_ip]['username']
        password = self.inputs.host_data[self.inputs.openstack_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.inputs.openstack_ip),
                    password=password):
                services_info = run(
                    'source /etc/contrail/openstackrc; nova service-%s %s nova-compute'%(mode,host))
            
        return True

    @classmethod
    def set_nova_flavor_key(self):
        username = self.inputs.host_data[self.inputs.openstack_ip]['username']
        password = self.inputs.host_data[self.inputs.openstack_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.inputs.openstack_ip),
                    password=password):
                    for cpu in self.nova_flavor.keys():
                        run('source /etc/contrail/openstackrc; nova flavor-create --is-public true %s auto 4096 80 %s --rxtx-factor 1.0'%(self.nova_flavor[cpu],int(cpu)))
                        run('source /etc/contrail/openstackrc; nova flavor-key  %s set hw:mem_page_size=large'%self.nova_flavor[cpu])
        return True

    @classmethod
    def set_nova_flavor_key_delete(self):
        username = self.inputs.host_data[self.inputs.openstack_ip]['username']
        password = self.inputs.host_data[self.inputs.openstack_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.inputs.openstack_ip),
                    password=password):
                    for cpu in self.nova_flavor.keys():
                        run('source /etc/contrail/openstackrc; nova flavor-delete %s'%self.nova_flavor[cpu])
        return True



    def launch_svc_vms(self,hosts,family,image_name='dpdk-l2-no-delay',left_rt='2000',right_rt='3000'):
        # Create two virtual networks
        self.vn1_name='vn100-left'
        self.vn1_subnets=['12.0.0.0/8']
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + ":" + self.vn1_name
        self.vn2_name = 'vn100-right'
        self.vn2_subnets = ['13.0.0.0/8'] 
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + ":" + self.vn2_name
        self.left_rt = left_rt 
        self.right_rt = right_rt 
#        self.left_rt = '1'
#        self.right_rt = '2'
        self.vmlist = []
        self.vm_fixture = []
        self.vm_num = 1 
        self.cpu_id_0=['0','1','2','3','4','5','6','7']
        self.cpu_id_00=['16','17','18','19','20','21','22','23']
        self.cpu_id_10=['8','9','10','11','12','13','14','15']
        self.cpu_id_11=['24','25','26','27','28','29','30','31']
        #self.images = ['ubuntu-in-net']
        #self.images = ['ubuntu-traffic']

        for i in range(0,self.vm_num):
            val = random.randint(1,100000)
            self.vmlist.append("vm-test"+str(val))

      #  for i in range(0,len(hosts)):
      #      if not self.set_perf_mode(hosts[i]):
      #          self.logger.error("Not able to set perf mode ")
      #      if not self.set_nova_vcpupin(hosts[i]):
      #          self.logger.error("Not able to set vcpu in nova.conf")
        
        self.inputs.set_af(family)

        if family == 'v6':
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs,router_asn=self.inputs.router_asn, rt_number=self.inputs.mx_rt))
        else:
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=self.left_rt))
            self.vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn2_name, inputs= self.inputs, subnets= self.vn2_subnets,router_asn=self.inputs.router_asn, rt_number=self.right_rt))
#            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn))
#            self.vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn2_name, inputs= self.inputs, subnets= self.vn2_subnets,router_asn=self.inputs.router_asn))


        assert self.vn1_fixture.verify_on_setup()
        assert self.vn2_fixture.verify_on_setup()
        # Create service instance 
        self.svc_tmp_name = 'perf_svc_template'
        self.svc_int_prefix = 'perf_vm_'
        self.svc_policy_name = 'perf_svc_policy'

        if self.set_si > 1:
            self.dpdk_svc_scaling = True
    
        self.perf_st_fixture , self.perf_si_fixtures = self.config_st_si(self.svc_tmp_name,
                          self.svc_int_prefix,self.vm_num,left_vn=self.vn1_fq_name ,svc_scaling=self.dpdk_svc_scaling,max_inst=self.set_si, 
                          right_vn=self.vn2_fq_name,svc_mode='in-network',svc_img_name=image_name,flavor=self.nova_flavor[str(self.set_cpu_cores)],
                          project=self.inputs.project_name)
        action_list = self.chain_si(self.vm_num,self.svc_int_prefix,self.inputs.project_name)

        self.project.set_sec_group_for_allow_all()
        # Create a policy 
        self.rules = [{'direction': '<>',
                 'protocol': 'any',
                 'source_network': self.vn1_name,
                 'src_ports': [0, -1],
                 'dest_network': self.vn2_name,
                 'dst_ports': [0, -1],
                 'simple_action': None,
                 'action_list': {'apply_service': action_list}
                 }]

        self.svc_policy_fixture = self.config_policy(self.svc_policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.svc_policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.svc_policy_fixture, self.vn2_fixture)

        time.sleep(180)

        for host in hosts:
            if not self.update_process_cpu_virt(host,'qemu'):
                self.logger.error("Not able to pin cpu :%s "%'qemu')

        for host in hosts:
            if not self.update_process_cpu_virt(host,'vhost'):
                self.logger.error("Not able to pin cpu :%s "%'vhost')

        for host in hosts:
             if not self.update_mtu(host):
                 self.logger.error("Not able to update tap")

        #import pdb ; pdb.set_trace()       
        # update VM tap interface and txqueuelen 
        #for vm_fix in self.perf_si_fixtures:
        #    if not self.update_vm_tap(vm_fix):
        #        self.logger.error("Not able to update VM tap")

        # Create service instance 
        # Create a policy 
        # Attach policy to VNs
        # attach policy to service instance
        return True 


    def run_ixia_perf_tests_pps(self,test_id,proto,family,cores,si):
        self.host_list = self.connections.orch.get_hosts()
        self.disable_hosts = copy.deepcopy(self.host_list) 
        self.set_cpu_cores = cores
        self.set_si = si
        self.encap_type = ["MPLSoGRE"]
        #host_vm = self.disable_hosts.pop(-1)
        host_vm = '5b4s10'
        #self.set_nova_flavor_key_delete()
        self.disable_hosts = ['5b4s12']

        for host in self.disable_hosts:
            if not self.set_nova_compute_service(host,'disable'):
                self.logger.error("Error in disabling nova compute")
                return False
            # for multiqueue
            if not self.launch_svc_vms([host_vm],family,'ubuntu-14.04'):
            #if not self.launch_svc_vms([host_vm],family,'ubuntu-in-net'):
                for host in self.host_list:
                    self.set_nova_compute_service(host,'enable')
                self.logger.error("Failed to launch VMs")
                return False

            if not self.run_ixia_throughput_tests(proto):
                for host in self.host_list:
                    self.set_nova_compute_service(host,'enable')
                self.logger.error("Failed to run ixia tests")
                return False

            if not self.cleanup_vms():
                for host in self.host_list:
                    self.set_nova_compute_service(host,'enable')
                self.logger.error("ERROR: In deleting service instance VM and template")
                return False

            cmd = 'cat /root/AggregateResults.csv; sleep 5 ; rm /root/AggregateResults.csv'
            res = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip,cmd)
            self.logger.info(res)
            self.print_results(res) 
            self.print_results("==================================================================\n")

        for host in self.host_list:
                self.set_nova_compute_service(host,'enable')
        
        return True

    def run_spirent_perf_test(self,test_id,proto,family,cores,si):
        self.host_list = self.connections.orch.get_hosts()
        self.disable_hosts = copy.deepcopy(self.host_list)
        self.set_cpu_cores = cores
        self.set_si = si
        self.encap_type = ["MPLSoGRE"]
        host_vm = self.disable_hosts.pop(-1)
        freemem=0
        freemem1=0
        # for multiqueue
        #if not self.launch_svc_vms([host_vm],family,'perf-ubuntu-14.04','1','2'):
        if not self.launch_svc_vms([host_vm],family,'perf-ubuntu','1','2'):
            for host in self.host_list:
                self.set_nova_compute_service(host,'enable')
            self.logger.error("Failed to launch VMs")
            return False
        for host in self.host_list:
	   # if test_id == 'Contrail_Perf2-Throughput_KVM_Jumbo':
            self.set_perf_mode_jumbo(host)
            cmd="cat /proc/meminfo | grep MemFree | awk \{'print $2'\}" 
            freemem = self.inputs.run_cmd_on_server(host, cmd, 'root', 'c0ntrail123')
            print freemem            

        if not self.start_spirent_traffic(self.spirent_linux_passwd, self.spirent_linux_user, self.spirent_linux_host, test_id):
            self.logger.error("Failed to run Spirent tests")
            return False

        if not self.get_spirent_result(self.spirent_linux_passwd, self.spirent_linux_user, self.spirent_linux_host, test_id):
            self.logger.error("Failed to collect test results")
            return False
        if not self.cleanup_vms():
            self.logger.error("ERROR: In deleting service instance VM and template")
            return False

        for host in self.host_list:
            cmd="cat /proc/meminfo | grep MemFree | awk \{'print $2'\}" 
            freemem1 = self.inputs.run_cmd_on_server(host, cmd, 'root', 'c0ntrail123')
            print freemem1          
        self.logger.info("Initial Memory: %s"%freemem) 
        self.logger.info("Final Memory: %s"%freemem1) 

        for host in self.host_list:
                self.set_nova_compute_service(host,'enable')

        return True

    def start_spirent_traffic (self, web_server_password, web_server_username, web_server, script_name):
        cmd = "service contrail-control restart; sleep 5" 
        print cmd
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            print line,
        retval = p.wait()
        cmd = "rm -rf /root/spirent/tests/%s/results; source /root/.bash_profile ;(nohup tclsh /root/spirent/tests/%s/test.tcl > results 2>&1 &); sleep 5" %(script_name, script_name)
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd, web_server_username, web_server_password)
        self.logger.info("Spirent Test Running: %s "%result)
        while True:
            if self.verify_spirent_test(web_server_username, web_server_password):
               self.logger.info("Finished running")
               break
            time.sleep(60)
            self.logger.info("Spirent Test Running")
        #import pdb;pdb.set_trace()
        return True



    def get_spirent_result (self, web_server_password, web_server_username, web_server, script_name):
        cmd = "mkdir /var/www/html/tests/results/%s/; id=$(uuidgen); mkdir /var/www/html/tests/results/%s/$id ; cp -r /root/spirent/tests/%s/results/ /var/www/html/tests/results/%s/$id/; sleep 1" %(script_name, script_name, script_name, script_name)
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd, web_server_username, web_server_password)
        cmd = "mkdir %s ; rm -rf %s/*; sshpass -p %s scp -o StrictHostKeyChecking=no -r %s@%s:/root/spirent/tests/%s/results %s" %(script_name, script_name, web_server_password, web_server_username, web_server, script_name, script_name)
        print cmd
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            print line,
        retval = p.wait()
        return True

    def run_ixia_throughput_tests(self,proto):
        return True
        for id in range(0,len(self.encap_type)):
            #self.update_encap_mode(self.inputs.host_data[self.inputs.cfgm_ip]['host_ip'],self.encap_type[id])
            if proto == 'TCP':
                if not self.start_ixia_rfc_tests():
                    self.logger.error("ERROR in TCP throughput test")
                    return False
            if proto == 'UDP':
                if not self.start_ixia_rfc_tests():
                    self.logger.error("ERROR in TCP throughput test")
                    return False
        return True 
 
    def start_ixia_rfc_tests(self):
        cmd='(nohup python /root/scripts/qt.py > results 2>&1 &); sleep 5'
        result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username='root',password='contrail123')
        self.logger.info("RFC Test Running: %s "%result)
        while True:
            if self.verify_ixia_test():
               self.logger.info("RFC Test FINISHED")
               break 
            time.sleep(60)
            self.logger.info("RFC Test Running")
        #import pdb;pdb.set_trace()
        return True

    def verify_ixia_test(self):
        cmd='cat results'
        result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username='root',password='contrail123')
        if not re.findall('FINISHED',result):
           return False
        elif re.findall('ERROR',result): 
            self.logger.info("RFC Test ERROR%s"%result)
            return True 
        else:
            self.logger.info("RFC Test FINISHED%s"%result)
            cmd='cat results | grep ResultPath'
            result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username='root',password='contrail123')
            self.update_results(result)
            return True 

    def verify_spirent_test(self, username, password):
        cmd='cat results'
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd,username ,password )
        if not re.findall('Finished running',result):
           return False
        elif re.findall('ERROR',result):
            self.logger.info("Spirent Test ERROR%s"%result)
            return True
        else:
            self.logger.info("Spirent Test FINISHED%s"%result)
            cmd='cat results | grep ResultPath'
            result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd,username ,password)
            #self.update_results(result)
            return True

    def update_results(self,result):
        result = result.replace("\r","")
        result = result.split("\n")
        res = str(result).strip('[]').strip('\'')
        res=res.replace('\\','/').replace('ResultPath:  /root/C://Users//Administrator//Desktop','%s'%self.ixia_host)+'/AggregateResults.csv'
        self.logger.info("Result : %s "%res)
        cmd = 'wget %s'%res
        res = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip,cmd)
        #cmd = 'cat AggregateResults.csv >> results_summary.csv ; sleep 1 ; rm AggregateResults.csv'
        #res = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip,cmd)
        return True
 
    def cleanup_vms(self):
        self.delete_si_st(self.perf_si_fixtures, self.perf_st_fixture)
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.svc_policy_fixture)
#        self.delete_vn(self.vn1_fixture)
#        self.delete_vn(self.vn2_fixture)
        return True

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break


    def get_cpu_core_virt(self,cpu_id):
        if len(cpu_id):
            return cpu_id.pop(0) 
        else:
            return False

    def set_task_pin_virt(self,host,cpu_id,pid,cpu_cores):
        cpu_core = self.get_cpu_core_virt(cpu_id) 
        cpu_core1 = cpu_core
        if not cpu_core:
            self.logger.error("Not able to get cpu core")
            return False
        if cpu_cores > 1 :
            for i in range(1,(cpu_cores)) :
                cpu_core1 = self.get_cpu_core_virt(cpu_id)
        #cpu_core1 = (int(cpu_core) + self.set_cpu_cores - 1)
        cmd = 'taskset -a -pc %s-%s %s'%(cpu_core,str(cpu_core1),pid)
        task_out = self.inputs.run_cmd_on_server(host, cmd)
        cmd = 'taskset -pc %s'%pid
        task_out = self.inputs.run_cmd_on_server(host, cmd)
        task_out=task_out.split(" ")
        self.logger.info("cpu mask :%s "%task_out[5])
        #if task_out[5] != cpu_core:
        #    self.logger.error("cpu is not pinned :%s : %s "%(task_out[5],cpu_core))
        #    return False
        return True 

    def update_mtu(self,host):
        cmd = 'for i in $(ifconfig | grep tap | awk {\'print $1\'}) ; do ifconfig $i txqueuelen 1000000 ; done'
        res = self.inputs.run_cmd_on_server(host, cmd)
        return True

    def update_vm_tap(self,vm_obj):
        for vm_obj in self.nova_h.get_vm_list():        
            vm_fix = self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,uuid=vm_obj.id))
            cmd = 'for i in $(ifconfig | grep eth | awk {\'print $1\'}) ; do ifconfig $i txqueuelen 1000000 ; done'
            vm_fix.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
            cmd = 'route add -net 15.0.0.0/8 gw 13.1.1.1 ; route add -net 11.0.0.0/8 gw 12.1.1.1'
            vm_fix.run_cmd_on_vm(cmds=[cmd],as_sudo=True, timeout=self.timeout)
        return True

    #This is hardcoded. Need to fix it
    def set_perf_mode_jumbo(self,host):
        #cmd='mac=$(maclist=$(ifconfig vhost0 | awk {\'print $5\'}) ; echo $maclist | sed s/MTU.*$//g) ; \
        #        intfs=$(ifconfig | grep $mac | awk {\'print $1\'} | sed s/vhost0//g | sed s/bond0//g ); \
        #        for intf in $intfs ; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g); \
        #        do echo "c0" > /proc/irq/"$i"/smp_affinity ; done ; done '
        cmd='for intf in em3 p2p1 ; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g);  do echo "800080" > /proc/irq/"$i"/smp_affinity ; done ; done'
        out = self.inputs.run_cmd_on_server(host, cmd)
        cmd='for intf in em1 em2 ; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g);  do echo "400040" > /proc/irq/"$i"/smp_affinity ; done ; done'
        out = self.inputs.run_cmd_on_server(host, cmd)
        return True

    def update_process_cpu_virt(self,host,name):
        cmd = 'ps ax | pgrep %s'%name
        res = self.inputs.run_cmd_on_server(host, cmd)
        res = res.replace("\r","")
        res = res.split("\n")
        for id in res:
            self.logger.info("Process Id : %s "%id)
            cmd = 'taskset -pc %s'%id
            task_out = self.inputs.run_cmd_on_server(host, cmd)
            task_out=task_out.split(" ")
            self.logger.info("cpu mask :%s "%task_out[5])

            if re.findall("8-15",task_out[5]):
               if not self.set_task_pin_virt(host,self.cpu_id_10,id,self.set_cpu_cores):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
        #        del self.cpu_id_10[0]
            elif re.findall("24-31",task_out[5]):
                if not self.set_task_pin_virt(host,self.cpu_id_11,id,self.set_cpu_cores):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
                    return False 
        #        del self.cpu_id_11[0]
            elif re.findall("0-7",task_out[5]):
                if not self.set_task_pin_virt(host,self.cpu_id_00,id,self.set_cpu_cores):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
                    return False 
            elif re.findall("16-23",task_out[5]):
                if not self.set_task_pin_virt(host,self.cpu_id_0,id,self.set_cpu_cores):
                    self.logger.error("Error in pinnng cpu :%s "%cmd)
                    return False 
            elif re.findall("0-31",task_out[5]):
                if name == 'qemu':
                    if not self.set_task_pin_virt(host,self.cpu_id_10,id,self.set_cpu_cores):
                        self.logger.error("Error in pinnng cpu :%s "%cmd)
                        return False 
                if name == 'vhost':
                    if not self.set_task_pin_virt(host,self.cpu_id_0,id,1):
                        self.logger.error("Error in pinnng cpu :%s "%cmd)
                        return False 
        #        del self.cpu_id_0[0]
        return True


