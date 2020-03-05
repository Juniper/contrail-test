import test_v1
from builtins import str
from builtins import range
import sys
import os
import signal
import re
import struct
import socket
import random
import inspect
#from fabric.state import connections as fab_connections
import re
from common.connections import ContrailConnections
from common.device_connection import NetconfConnection
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.servicechain.mirror.verify import VerifySvcMirror
from common.servicechain.mirror.config import ConfigSvcMirror
from fabric.api import local
#from serial_scripts.perf.base import PerfBase
from tcutils.commands import *
import time
import copy
import uuid

class PerfBase(test_v1.BaseTestCase_v1,VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(PerfBase, cls).setUpClass()
        cls.nova_h = cls.connections.nova_h
        cls.orch = cls.connections.orch
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.results = 'logs/results_%s'%random.randint(0,100000)
        cls.results_file = open(cls.results,"aw")
        cls.encap_type = ["MPLSoUDP","MPLSoGRE"]
        cls.spirent_linux_user = cls.inputs.spirent_linux_username
        cls.spirent_linux_passwd = cls.inputs.spirent_linux_password
        cls.ixia_linux_user = cls.inputs.ixia_linux_username
        cls.ixia_linux_passwd = cls.inputs.ixia_linux_password
        cls.ixia_linux_host = cls.inputs.ixia_linux_host_ip
        cls.ixia_host = cls.inputs.ixia_host_ip
        cls.spirent_linux_host = cls.inputs.spirent_linux_host_ip
        cls.mx1_ip = cls.inputs.ixia_mx_ip 
        cls.mx2_ip = cls.inputs.spirent_mx_ip
        cls.mx_user = cls.inputs.ixia_mx_username
        cls.mx_password = cls.inputs.ixia_mx_password
        cls.rt = {'ixia': ['2000','3000'],'spirent':['1','2'] }
        cls.family = ''
        cls.dpdk_svc_scaling = False
        cls.nova_flavor= { '2':'contrail_perf_2cpu','3':'contrail_perf_3cpu','4':'contrail_perf_4cpu', '8':'contrail_perf_8cpu'}
        cls.vrouter_mask_list = ['0xff','0x3f','0xff','0xf000f']
        cls.mx1_handle = NetconfConnection(host = cls.mx1_ip,username=cls.mx_user,password=cls.mx_password)
        cls.mx1_handle.connect()
        cls.mx2_handle = NetconfConnection(host = cls.mx2_ip,username=cls.mx_user,password=cls.mx_password)
        cls.mx2_handle.connect()
        cls.host_cpu = {}
        cls.host = None
        cls.cpu_intr_mask = '80'
        cls.perf_si_fixtures = []
        cls.update_hosts()
        cls.create_availability_zone()
        cls.nova_flavor_key_delete()

    @classmethod
    def tearDownClass(cls):
        cls.results_file.close()  
        cls.del_availability_zone()
        cls.nova_flavor_key_delete()
        super(PerfBase, cls).tearDownClass()

    @classmethod
    def print_results(self,result):
        self.results_file.write(result)

    @classmethod
    def update_hosts(self):
        host_list = self.connections.orch.get_hosts()
        self.kvm_hosts = copy.deepcopy(host_list)
        self.dpdk_hosts = [self.inputs.host_data[host]['name'] for host in self.inputs.dpdk_ips] 
        self.netronome_hosts = []
        for host in host_list:
            if host in self.dpdk_hosts:
                self.kvm_hosts.remove(host)
        return

    @classmethod
    def create_availability_zone(self):
        zones = self.connections.orch.get_zones()
        self.agg_id = {} 
        if 'kvm' not in zones: 
            self.agg_id['kvm_id'] = self.connections.orch.create_agg('kvm','kvm')
            self.connections.orch.add_host_to_agg(self.agg_id['kvm_id'],self.kvm_hosts)
        if 'dpdk' not in zones: 
            self.agg_id['dpdk_id']= self.connections.orch.create_agg('dpdk','dpdk')
            self.connections.orch.add_host_to_agg(self.agg_id['dpdk_id'],self.dpdk_hosts)
        return 

    @classmethod
    def del_availability_zone(self):
        if 'kvm_id' in self.agg_id:
            self.connections.orch.del_host_from_agg(self.agg_id['kvm_id'],self.kvm_hosts)
            self.connections.orch.delete_agg(self.agg_id['kvm_id'])
        if 'dpdk_id' in self.agg_id:
            self.connections.orch.del_host_from_agg(self.agg_id['dpdk_id'],self.dpdk_hosts)
            self.connections.orch.delete_agg(self.agg_id['dpdk_id'])
        return 

    def set_test_config(self,**kwargs):
        self.perf_conf = {} 
        self.perf_conf['profile_name'] = kwargs.get('profile_name') 
        self.perf_conf['proto']  = kwargs.get('proto') 
        self.perf_conf['cores']  = kwargs.get('cores') 
        self.perf_conf['family'] = kwargs.get('family') 
        self.perf_conf['si']     = kwargs.get('si') 
        self.perf_conf['image']  = kwargs.get('image') 
        self.perf_conf['encap']  = kwargs.get('encap','MPLSoGRE')
        self.perf_conf['zone'] = kwargs.get('zone','kvm')  
        self.perf_conf['multiq'] = kwargs.get('multiq',False) 
        self.perf_conf['traffic'] = kwargs.get('traffic','ixia') 
        self.perf_conf['flow'] = kwargs.get('flow',None) 
        if self.perf_conf['traffic'] is 'ixia':
            self.perf_conf['left-rt'] = self.rt['ixia'][0]
            self.perf_conf['right-rt'] = self.rt['ixia'][1]
        if self.perf_conf['traffic'] is 'spirent':
            self.perf_conf['left-rt'] = self.rt['spirent'][0]
            self.perf_conf['right-rt'] = self.rt['spirent'][1]

        self.logger.info("profile_name : %s"%self.perf_conf['profile_name'])
        self.logger.info("proto      : %s"%self.perf_conf['proto'])
        self.logger.info("cores      : %s"%self.perf_conf['cores'])
        self.logger.info("family     : %s"%self.perf_conf['family'])
        self.logger.info("number of svms : %s"%self.perf_conf['si'])
        self.logger.info("image      : %s"%self.perf_conf['image'])
        self.logger.info("encap      : %s"%self.perf_conf['encap'])
        self.logger.info("zone       : %s"%self.perf_conf['zone'])
        self.logger.info("multiq     : %s"%self.perf_conf['multiq'])
        self.logger.info("traffic    : %s"%self.perf_conf['traffic'])
        return  

    @classmethod
    def nova_flavor_key_delete(self):
        flavor_list = self.orch.get_flavor_list()
        for flavor in flavor_list:
            if 'contrail_perf' in flavor.name:
                self.orch.delete_flavor(flavor)
        return True

    def nova_flavor_update(self,extra_specs):
        flavor_list = self.orch.get_flavor_list()
        for flavor in flavor_list:
            if 'contrail_perf' in flavor.name:
                flavor.set_keys(extra_specs)
        return True

    def nova_image_update(self,properties):
        image = self.orch.find_image(self.perf_conf['image'])
        if image:
            image.update(properties=properties)
        return True
 
    def update_image_flavor_options(self):
        self.get_zones(refresh=True)
        # setting numa nodes 
        extra_specs = { 'hw:numa_nodes':'1' }  
        self.nova_flavor_update(extra_specs)
        # if multiq is enabled 
        if self.perf_conf['multiq']:
            properties = {'hw_vif_multiqueue_enabled': True}
            self.nova_image_update(properties=properties)
        # if dpdk or netronome is enabled

        if 'dpdk' in self.perf_conf['zone']:
            extra_specs = {  'hw:mem_page_size': 'large' }  
            self.nova_flavor_update(extra_specs)

        # if hw acceleration is enabled
        if 'netronome' in self.perf_conf['zone']:
            properties = {'agilio.hw_acceleration_features':'SR-IOV'}
            self.nova_image_update(properties=properties)
        return True


    def launch_svc_vms(self,host, left_rt='2000',right_rt='3000'):
        # Create two virtual networks
        self.vn1_name='vn100-left'
        self.vn1_subnets=['12.0.0.0/8','2005::/64']
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + ":" + self.vn1_name
        self.vn2_name = 'vn100-right'
        self.vn2_subnets = ['13.0.0.0/8','2006::/64']
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + ":" + self.vn2_name
        self.vmlist = []
        self.vm_fixture = []
        self.version = '2'
        self.userdata = '/tmp/metadata_script.txt'

        self.inputs.set_af(self.perf_conf['family'])
        if self.perf_conf['family'] == 'v6':
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs,router_asn=self.inputs.router_asn, rt_number=self.inputs.mx_rt))
        else:
            self.vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn1_name, inputs= self.inputs, subnets= self.vn1_subnets,router_asn=self.inputs.router_asn, rt_number=left_rt))
            self.vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=self.vn2_name, inputs= self.inputs, subnets= self.vn2_subnets,router_asn=self.inputs.router_asn, rt_number=right_rt))

        # Create service instance 
        self.svc_tmp_name = 'perf_svc_template'
        self.svc_int_prefix = 'perf_vm_'
        self.svc_policy_name = 'perf_svc_policy'
        if self.perf_conf['si']> 1:
            self.dpdk_svc_scaling = True

        if self.version == '2':
            # create service template
            if_details =  { 'left': {}, 'right': {} }
            self.perf_st_fixture = self.useFixture(SvcTemplateFixture(
                               connections=self.connections,
                               st_name=self.svc_tmp_name, svc_img_name=self.perf_conf['image'], service_type='firewall',
                               if_details=if_details, service_mode='in-network', svc_scaling=self.dpdk_svc_scaling,
                               flavor=self.nova_flavor[str(self.perf_conf['cores'])],
                               version=2,availability_zone_enable=True))
            if_details = { 'left' : {'vn_name' : self.vn1_fq_name},
                           'right': {'vn_name' : self.vn2_fq_name}
                         }
            for i in range(0, 1):
                si_name = self.svc_int_prefix + str(i + 1)
                self.perf_si_fixture = self.useFixture(SvcInstanceFixture(
                    connections=self.connections,
                    si_name=si_name,
                    svc_template=self.perf_st_fixture.st_obj, if_details=if_details,
                     max_inst=self.perf_conf['si'], availability_zone=self.perf_conf['zone']))
                self.logger.debug('Launching SVM')
                for i in range(self.perf_conf['si']):
                    svm_name = get_random_name("pt_svm" + str(i))
                    pt_name = get_random_name("port_tuple" + str(i))
                    svm_fixture = self.config_and_verify_vm(
                                 svm_name, image_name=self.perf_conf['image'], vns=[self.vn1_fixture, self.vn2_fixture], 
                                 count=1, flavor=self.nova_flavor[str(self.perf_conf['cores'])],
                                 zone=self.perf_conf['zone'],node_name=host)
                    port_tuples_props = []
                    svm_pt_props = {}
                    svm_pt_props['left'] = svm_fixture.vmi_ids[self.vn1_fq_name]
                    svm_pt_props['right'] = svm_fixture.vmi_ids[self.vn2_fq_name]
                    svm_pt_props['name'] = get_random_name("port_tuple")
                    port_tuples_props.append(svm_pt_props)
                    self.perf_si_fixture.add_port_tuple(svm_pt_props)
                #self.perf_si_fixture.verify_on_setup()
                self.perf_si_fixtures.append(self.perf_si_fixture)

   #     action_list = self.chain_si(self.vm_num,self.svc_int_prefix,self.inputs.project_name)
        action_list = []

        for i in range(1):
            si_name = self.svc_int_prefix + str(i + 1)
            # chain services by appending to action list
            si_fq_name = 'default-domain' + ':' + self.inputs.project_name + ':' + si_name
            action_list.append(si_fq_name)

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
        self.vn1_policy_fix = self.attach_policy_to_vn( self.svc_policy_fixture, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn( self.svc_policy_fixture, self.vn2_fixture)

        time.sleep(180)

        return True

    def update_pre_perf_tunings(self):
        cmd='for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor ; do echo performance > $f; cat $f; done'
        out = self.inputs.run_cmd_on_server(self.host, cmd)
        cmd='service  irqbalance stop'
        out = self.inputs.run_cmd_on_server(self.host, cmd) 
        nics = ','.join(self.host_numa[self.host]['nics'])
        cmd='for intf in {%s}; do for i in $(grep $intf /proc/interrupts | awk {\'print $1\'} | sed s/://g);  do echo "0,%s" > /proc/irq/"$i"/smp_affinity ; done ; done'%(nics,self.cpu_intr_mask)
        out = self.inputs.run_cmd_on_server(self.host, cmd) 
        return True

    def update_post_perf_tunings(self):
        # CPU pinning of VMs based on numa node
        if not self.set_process_cpu(self.host,'qemu'):
                self.logger.error("Not able to pin cpu :%s "%'qemu')

        if 'kvm' in self.perf_conf['zone']:
            if not self.set_process_cpu(self.host,'vhost'):
                self.logger.error("Not able to pin cpu :%s "%'vhost')
           # TODO later 
            if not self.update_txquelen(self.host):
                self.logger.error("Not able to update tap")
        return True

    def update_txquelen(self,host):
        cmd = 'for i in $(ifconfig | grep tap | awk {\'print $1\'}) ; do ifconfig $i txqueuelen 1000000 ; done'
        res = self.inputs.run_cmd_on_server(host, cmd)
        return True

    def set_process_cpu(self,host,process):
        cmd = 'ps ax | pgrep %s'%process
        pids = self.inputs.run_cmd_on_server(host, cmd)
        pids = pids.replace("\r","").split("\n")
        cpus_to_pin = [] 
        numa_id = 'cpu_numa_%s'%self.host_numa[host]['numa'][0]
        self.logger.info("Numa Id : %s"%numa_id)
        for pid in pids:
            cpus_to_pin = [] 
            cores = 1 if process == 'vhost' else int(self.perf_conf['cores'])
            for core in range(cores):
                core_id = self.get_cpu_core(self.host_cpu[host][numa_id])
                if core_id is not None:
                    cpus_to_pin.append(str(core_id))
                else: 
                    self.logger.error("Not able to get CPU core to pin %s"%process)
            cpus_to_pin_str  = ','.join(cpus_to_pin)
            self.logger.info("cpus to pin the process %s :pid : %s:  %s"%(process,pid,cpus_to_pin_str))
            cmd = 'taskset -a -pc %s %s'%(cpus_to_pin_str,pid)
            self.inputs.run_cmd_on_server(host, cmd)
        return True

    def get_cpu_core(self,cpu_id):
        if len(cpu_id):
            return cpu_id.pop(0) 
        else:
            return None 

    def get_hosts(self):
        host = []
        if 'kvm' in self.perf_conf['zone']:
            host = self.kvm_hosts[0]
        if 'dpdk' in self.perf_conf['zone']:
            host = self.dpdk_hosts[0]
        if 'netronome' in self.perf_conf['zone']:
            host = self.netronome_hosts[0]
        return host

    def get_numa_nodes_cpu_cores(self):
        host_numa = {}
        host_cpu = {}
        host_numa[self.host] = {}
        host_numa[self.host]['nics'],host_numa[self.host]['numa'] = self.get_nics_numa_node(self.host)
        #host_numa[self.host]['numa'] = self.get_nics_numa_node(self.host)[1]
        host_cpu = self.get_cpu_cores(self.host)
        self.logger.info("host numa : %s"%host_numa)
        self.logger.info("cpu cores : %s"%host_cpu)
        return host_numa , host_cpu

    def restart_control(self):
        for node in self.inputs.bgp_control_ips:
                self.inputs.restart_service('contrail-control', [node],
                                            container='control')
        return 

    def get_nics_numa_node(self,host_name):
        numa_nodes = [] 
        nics = []
        os_name = self.inputs.get_os_version(host_name) 
        if 'kvm' in self.perf_conf['zone']:
            if 'ubuntu' in os_name: 
                cmd = ''
                cmd = "mac=$(ifconfig | grep vhost0 | awk {\'print $5\'}) ; ifconfig | grep $mac | awk {\'print $1\'}"
                nics = self.inputs.run_cmd_on_server(host_name,cmd)
                nics = nics.replace("\r",'').split("\n")
                nics = [x for x in nics if x not in ['vhost0']]
                nics = [x for x in nics if x not in ['bond0']]
            elif 'redhat' or 'centos' in os_name:
                cmd = 'mac=$(ifconfig | grep vhost0 -A3 | grep ether | awk {\'print $2\'}) ; ifconfig | grep $mac  -B3 | grep UP | awk {\'print $1\'}'
                nics = self.inputs.run_cmd_on_server(host_name,cmd)
                nics = nics.replace("\r",'').replace(":",'').split("\n")
                nics = [x for x in nics if x not in ['vhost0']]
                nics = [x for x in nics if x not in ['bond0']]

        if 'dpdk' in self.perf_conf['zone']:
            cmd = 'cat /var/run/vrouter/bond0_bond'
            nics = self.inputs.run_cmd_on_server(host_name,cmd)
            nics = nics.replace("\r",'').split(" ")[2].split(',')

        if 'netronome' in self.perf_conf['zone']:
            #TODO
            self.logger.info("Netronome mapping of nics ")
       
        if not nics:
            self.logger.error("NICs not present in two NUMA NODES")
            return nics,numa_nodes

        for intf in nics:
            cmd = 'cat /sys/class/net/%s/device/numa_node'%intf
            numa_nodes.append(self.inputs.run_cmd_on_server(host_name,cmd))

        if 'dpdk' in self.perf_conf['zone']:
            #TODO , need to get the nodes properly
            numa_nodes =  ['0']

        numa_nodes = list(set(numa_nodes)) 

        if (len(numa_nodes) > 1 ):
            self.logger.info("NICs present in two NUMA NODES")

        self.logger.info("NICs present NUMA NODES %s"%numa_nodes)

        return nics,numa_nodes

    def get_cpu_cores(self,host):
        cpus_resvd = []
        cpus_intr_resvd = []
        host_cpu = {}
        host_cpu[host] = {}
        if 'dpdk' in self.perf_conf['zone']:
            cpus_resvd = self.hextobit(self.vrouter_mask_list[0])
        cpus_intr_resvd = self.hextobit(self.cpu_intr_mask)
        host_cpu[host]['cpu_numa_0'] = [ x for x in  self.get_cpus_from_host(0,host) if x not in cpus_resvd]
        host_cpu[host]['cpu_numa_1'] = [ x for x in  self.get_cpus_from_host(1,host) if x not in cpus_resvd]
        host_cpu[host]['cpu_numa_0'] = [ x for x in  host_cpu[host]['cpu_numa_0'] if x not in cpus_intr_resvd]
        host_cpu[host]['cpu_numa_1'] = [ x for x in  host_cpu[host]['cpu_numa_1'] if x not in cpus_intr_resvd]
        return host_cpu

    def hextobit(self,mask):
        cpus = []
        count = 0
        val = int(mask,16)
        while (val):
            if (val & 0x1):
                cpus.append(count)
            val = val >> 1
            count += 1
        return cpus

    def get_cpus_from_host(self,numa,host):
        cpus = []
        cmd = "lscpu | grep NUMA | grep node%s |  grep CPU | awk {'print $4'}"%numa
        res = self.inputs.run_cmd_on_server(host,cmd)
        cpu_list = res.replace('\n',',').split(',')
        for cpu in cpu_list:
            for i in range(int(cpu.split('-')[0]),int(cpu.split('-')[1])+1):
                cpus.append(i)
        return cpus

    def configure_mx(self,encap,handle):
        cmd = []
        if encap == 'MPLSoUDP':
            if handle.host  == self.mx1_ip: 
                cmd.append('set groups ixia_flow routing-options dynamic-tunnels contrail udp')
                cmd.append('set groups ixia_flow protocols bgp group contrail export test1-export')
            elif handle.host == self.mx2_ip: 
                cmd.append('set groups __contrail__ routing-options dynamic-tunnels __contrail__ udp')
                cmd.append('set groups __contrail__ protocols bgp group __contrail__ export test1-export') 

        elif encap == 'MPLSoGRE':
            if handle.host  == self.mx1_ip: 
                cmd.append('set groups ixia_flow routing-options dynamic-tunnels contrail gre')
                cmd.append('delete groups ixia_flow protocols bgp group contrail export test1-export')
            elif handle.host == self.mx2_ip: 
                cmd.append('set groups __contrail__ routing-options dynamic-tunnels __contrail__ gre')
                cmd.append('delete groups __contrail__ protocols bgp group __contrail__ export test1-export') 

        self.logger.info("MX configuration cmd executed %s"%cmd)

        cli_output = handle.config(stmts = cmd,ignore_errors=True,timeout = 120) 
        
        self.restart_control()

        return True

    def run_perf_tests(self,**kwargs):
        self.logger.info("Executing Performance Tests")

        self.set_test_config(**kwargs)

        self.host = self.get_hosts()

        self.host_numa,self.host_cpu = self.get_numa_nodes_cpu_cores()

        self.update_pre_perf_tunings()

        self.configure_mx(self.perf_conf['encap'],self.mx1_handle)
        self.configure_mx(self.perf_conf['encap'],self.mx2_handle)

        self.update_image_flavor_options()

        self.test_name = inspect.stack()[1][3]

        if not self.host :
            self.logger.error("Not able to find host to launch VMs")
            return False

        if not self.launch_svc_vms(self.host, self.perf_conf['left-rt'],self.perf_conf['right-rt']):
             self.logger.error("Failed to launch VMs")
             return False

        self.update_post_perf_tunings()

        if self.perf_conf['traffic'] is 'ixia':
            if not self.run_ixia_rfc_tests(self.perf_conf['profile_name']):
                self.logger.error("Failed to run ixia tests successfully")
                return False

        if self.perf_conf['traffic'] is 'spirent':
            if not self.start_spirent_test(self.perf_conf['profile_name']):
                self.logger.error("Failed to run ixia tests successfully")
                return False

        #import pdb;pdb.set_trace()

        return True

    def run_ixia_rfc_tests(self,script_name):
        # TDOD enable these lines later to start ixia test
        cmd='(nohup python /root/scripts/qt.py  /root/scripts/profiles/%s  > /root/results 2>&1 &); sleep 5' %(script_name)
        result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username=self.ixia_linux_user ,password=self.ixia_linux_passwd)
        self.logger.info("RFC Test Running: %s "%result)
        self.logger.info("RFC Test Running: ... ")
        cnt = 0
        while True:
            if self.verify_ixia_test(script_name):
                self.logger.info("RFC Test FINISHED")
                break
            time.sleep(60)
            cnt = cnt + 1
            self.logger.info("RFC Test Running")
            if cnt  > 100 :
                self.logger.error("Ixia Tests failed to return from server")
                return False
        cmd='cat /root/results | grep ResultPath'
        time.sleep(60)
        result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username=self.ixia_linux_user,password=self.ixia_linux_passwd)
        self.logger.info("Result path %s"%result)
        self.update_results(result)
        return True

    def verify_ixia_test(self,script_name):
        try:
            cmd='cat /root/results | grep FINISHED'
            result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username=self.ixia_linux_user,password=self.ixia_linux_passwd)
            if not re.findall('FINISHED',result):
                return False
            cmd='cat /root/results'
            result = self.inputs.run_cmd_on_server(self.ixia_linux_host, cmd,username=self.ixia_linux_user,password=self.ixia_linux_passwd)
            self.logger.info("RFC Test FINISHED%s"%result)
            if re.findall('ERROR',result):
                self.logger.error("RFC Test ERROR%s"%result)
        except Exception as e:
            self.logger.exception("Exception in calling ixia host %s"%(e))
        return True

    def update_results(self,result):
        result = result.replace("\r","")
        result = result.split("\n")
        res = str(result).strip('[]').strip('\'')
        #res=res.replace('\\','/').replace('ResultPath:  /root/C://Users//Administrator//Desktop','%s'%self.ixia_host)+'/AggregateResults.csv'
        res=res.replace('\\','/').replace('ResultPath:  C://Users//Administrator//Desktop','%s'%self.ixia_host)+'/AggregateResults.csv'
        self.logger.info("Result : %s "%res)
        out = '\ntest: %s \nencap : %s   \ncores : %s  \nfamily: %s  \ninstances : %s \n'%(self.test_name,
                                  self.perf_conf['encap'],self.perf_conf['cores'],self.perf_conf['family'],self.perf_conf['si'])
        self.print_results("test_profile: %s"%self.perf_conf['profile_name']) 
        self.print_results(out) 
        self.print_results(res) 
        self.print_results('\n') 
        cmd = 'wget -O /tmp/AggregateResults.csv %s'%res
        res = self.inputs.run_cmd_on_server(self.host,cmd)
        cmd = 'cat /tmp/AggregateResults.csv ; sleep 5 ; rm /tmp/AggregateResults.csv'
        res = self.inputs.run_cmd_on_server(self.host,cmd)
        self.logger.info(res)
        self.logger.info(res)
        self.print_results(res) 
        self.print_results("\n==================================================================\n")
        return True

    def start_spirent_test(self,script_name):
        self.restart_control()
        cmd = "rm -rf /root/spirent/tests/%s/results; source /root/.bash_profile ;(nohup tclsh /root/spirent/tests/%s/test.tcl > results 2>&1 &); sleep 5" %(script_name, script_name)
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd, self.spirent_linux_user , self.spirent_linux_passwd )
        self.logger.info("Spirent Test Running: %s "%result)
        cnt = 0 
        while True:
            if self.verify_spirent_test():
               self.logger.info("Finished running")
               break
            time.sleep(60)
            cnt = cnt + 1
            self.logger.info("Spirent Test Running")
            if cnt  > 60 :
                self.logger.error("Spirent Tests failed to return from server")
                return False
        if not self.get_spirent_result(script_name):
            self.logger.error("Failed to collect test results")
            return False
        return True

    def verify_spirent_test(self):
        cmd='cat results'
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd,self.spirent_linux_user,self.spirent_linux_passwd)
        if not re.findall('Finished running',result):
           return False
        elif re.findall('ERROR',result):
            self.logger.info("Spirent Test ERROR%s"%result)
            return True
        else:
            self.logger.info("Spirent Test FINISHED%s"%result)
            cmd='cat results | grep ResultPath'
            result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd,self.spirent_linux_user,self.spirent_linux_passwd)
            return True

    def get_spirent_result (self, script_name):
        uuid_curr = str(uuid.uuid1())
        remote_dir = '/var/www/html/tests/results/%s/%s/'%(script_name,uuid_curr)
        cmd = "mkdir /var/www/html/tests/results/%s/;mkdir %s ;cp -r /root/spirent/tests/%s/results/ %s ;sleep 1" %(script_name,remote_dir,script_name,remote_dir)
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd, self.spirent_linux_user, self.spirent_linux_passwd)
        logs = "\nLog Path (%s): %s" %(script_name, remote_dir )
        http_logs = "\nLog Path (%s): http://%s//tests/results/%s/%s/" %(script_name,self.spirent_linux_host,script_name, uuid_curr)
        self.logger.info("%s"%logs)
        self.logger.info("%s"%http_logs)
        out = '\ntest: %s \nencap : %s   \ncores : %s  \nfamily: %s  \ninstances : %s \ntest_profile: %s \n'%(self.test_name,
                                  self.perf_conf['encap'],self.perf_conf['cores'],self.perf_conf['family'],self.perf_conf['si'],self.perf_conf['profile_name'])
        self.print_results(out) 
        self.print_results(logs) 
        self.print_results(http_logs) 
        self.print_results("\n") 
        if self.perf_conf['flow'] is 'flow':
            cmd = ' python /root/performance_results/performance_analysis_tool.py -f  %s/results/merged/client/realtime.csv  -o test.html -j time_vs_conn_rate_flow_tests ; sleep 5'%remote_dir

        if self.perf_conf['flow'] is 'flowscale':
            cmd = ' python /root/performance_results/performance_analysis_tool.py -f  %s/results/merged/client/realtime.csv  -o test.html -j time_vs_conn_rate_flow_scale_tests ; sleep 5'%remote_dir

        if self.perf_conf['flow'] is 'throughput':
            cmd = ' python /root/performance_results/performance_analysis_tool.py -f  %s/results/merged/client/realtime.csv  -o test.html -j time_throughput ; sleep 5'%remote_dir
        result = self.inputs.run_cmd_on_server(self.spirent_linux_host, cmd, self.spirent_linux_user, self.spirent_linux_passwd)
        result = result.replace("\r","")
        self.print_results(result)
        self.print_results("\n==================================================================\n")
        return True

