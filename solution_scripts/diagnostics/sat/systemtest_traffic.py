import threading
from common import log_orig as logging
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import pdb
import tempfile
import os
import re
from lib import *
import time
from common.log_orig import ContrailLogger
from send_zmq import *
from config import *
from multiprocessing import TimeoutError, Pool
from copy_reg import pickle
import itertools

def get_one_random_vm(vns, vn_type):
   keys = vns.keys()
   random.shuffle(keys)
   for vn in keys:
      if vn_type in vn:
         return random.choice(vns[vn])

def is_attach_fip(test, vn_type):
   for vn_group in test.tenant_conf['tenant,vn_group_list']:
      if vn_type in vn_group['vn,name,pattern'].split('.')[2]:
         if vn_group['attach_fip'] == True:
            return True
         else:
            return False

def fip_to_name(fip):
   return '-'.join(fip.split('.'))


def grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def ping_check_setup(test, filename=""):
   tenant_name = "all"
   tenants = test.get_vm_info(tenant_name)
   traffic_command = test.traffic_conf['ping']
   client_traffic_commands = []
   pvn_fip = is_attach_fip(test, 'Private_VN')
   vip_fip = is_attach_fip(test, 'Private_LB')
   ex_srv_ip = test.traffic_conf['external_server_ip']
   for tenant in tenants:
      for vn in tenants[tenant]:
         if ((u'Private_VN' in vn) and pvn_fip and ex_srv_ip):
            for vm in tenants[tenant][vn]:
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               fip_vn_vm = get_one_random_vm(tenants[tenant], u'Public_FIP')
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=fip_vn_vm)
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, external_server_ip=ex_srv_ip)
         elif u'Private_VN' in vn and pvn_fip:
            for vm in tenants[tenant][vn]:
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               fip_vn_vm = get_one_random_vm(tenants[tenant], u'Public_FIP')
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=fip_vn_vm)
         elif u'Private_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
         elif u'Private_SNAT_VN' in vn and ex_srv_ip:
            for vm in tenants[tenant][vn]:
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               gw_vn_vm = get_one_random_vm(tenants[tenant], u'SNAT_GW')
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=gw_vn_vm)
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, external_server_ip=ex_srv_ip)
         elif u'Private_SNAT_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               gw_vn_vm = get_one_random_vm(tenants[tenant], u'SNAT_GW')
               build_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=gw_vn_vm)
         #elif u'Private_LB_VIP' in vn:
         else:
            continue
   client_results = exec_remote_commands(client_traffic_commands, [])
   status = process_and_write_ping_results(test, client_results)
   return status

def process_and_write_ping_results(test, results):
    name_re = re.compile(r'^(PING .+) \(([\d.]+)\) .+ data.$')
    unknown_re = re.compile(r'^ping: unknown host (.+)$')
    reverse_name_re = re.compile(r'^.+ from ([\w\d.]+):* .+$')
    info_re = re.compile(r'^.+ (\d+)% .+$')
    stats_re = re.compile(r'^rtt min/avg/max/mdev = ([\d.]+)/'r'([\d.]+)/([\d.]+)/[\d.]+ ms$')
    global_result = 'pass'
    res_str = []
    ex_srv_ip = test.traffic_conf['external_server_ip']
    for client in results:
        for result in client['results']:
            res_str.append(client['address'])
            output = result['output']
            flag = 'pass'
            for line in output.splitlines():
                match = unknown_re.match(line)
                if match:
                   res_str.append('UNKNOWN HOST '+match.group(1))
                   flag = 'fail'
                   global_result = 'fail'                    
                match = name_re.match(line)
                if match:
                    res_str.append(match.group(1))
                    res_str.append(match.group(2))
                match = reverse_name_re.match(line)
                if match:
                    if ('vm' not in match.group(1) and ex_srv_ip != match.group(1)):
                       flag == 'fail'
                       global_result = 'fail'
                       res_str.append('RR Failed')
                match = info_re.match(line)
                if match:
                    if int(match.group(1)) > 25.0:
                        flag = 'fail'
                        global_result = 'fail'
                    res_str.append(match.group(1)+"% Loss")
                match = stats_re.match(line)
                if match:
                    res_str.append(match.group())
                    min_time, avg_time, max_time = map(float, match.groups())
                    if avg_time > 50.0:
                        flag  = 'fail'
                        global_result = 'fail'
            if flag == 'pass' and match:
                res_str.append('SUCCESS\n')
            else:
                res_str.append('FAIL\n')
    fp = open('ping_results.log', 'a')
    fp.write(' '.join(res_str))
    fp.close()

    return global_result


def build_file_commands(file_str, remote_file_commands, src):
   if isinstance(src, dict):
      remote_file_commands.append((src['ip_addr,mgmt'], file_str))
   else:
      remote_file_commands.append((src, file_srt))
   return

def build_traffic_commands(traffic_command, client_traffic_commands, src_vm={}, dst_vm={}, port = "", external_server_ip=""):
   if src_vm and dst_vm:
      final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], dst_vm['name'], port)
      if dst_vm['ip_addr,fip'] and 'ping' in traffic_command:
         fip_name = fip_to_name(dst_vm['ip_addr,fip'])
         final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], fip_name, port)
   elif src_vm and external_server_ip:
      final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], external_server_ip, port)
   elif external_server_ip and dst_vm:
      final_client_traffic_command(traffic_command, client_traffic_commands, external_server_ip, dst_vm['ip_addr,fip'], port)
   elif src_vm:
      final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], dst_vm, port)
   elif external_server_ip:
      final_client_traffic_command(traffic_command, client_traffic_commands, external_server_ip, dst_vm, port)
   else:
      return
   return

def final_client_traffic_command(traffic_command, client_traffic_commands, src, dst, port):
   #pdb.set_trace()
   if "ping" in traffic_command:
      traffic_command.append(dst)
      temp = traffic_command[:]
      client_traffic_commands.append((src, temp))
      del traffic_command[-1]
   elif ("iperf3" in traffic_command and "-s" in traffic_command):
      traffic_command.extend([str(port)])
      temp = traffic_command[:]
      client_traffic_commands.append((src,temp))
      del traffic_command[-1]
      print client_traffic_commands
   elif ("iperf3" in traffic_command):
      traffic_command.extend(["-c", dst, "-p", str(port)])
      temp = traffic_command[:]
      client_traffic_commands.append((src,temp))
      del traffic_command[-4]
      print client_traffic_commands
   elif "httpload" in traffic_command:
      temp = traffic_command[:]
      client_traffic_commands.append((src,temp))
      print client_traffic_commands
   else:
      print 'wrong command'
   return


def run_traffic(test):
   tenant_name = "all"
   tenants = test.get_vm_info(tenant_name)


   client_traffic_commands = []
   client_file_commands = []
   server_traffic_commands = []

   pvn_fip = is_attach_fip(test, 'Private_VN')
   vip_fip = is_attach_fip(test, 'Private_LB')
   ex_srv_ip = test.traffic_conf['external_server_ip']

   if test.global_conf.get('lls,name',None):
      lls_urls = ""
      lls_obj = LLS(None)
      lls_names = lls_obj.retrieve_existing_services()
      for lls in lls_names:
         if lls != 'metadata':
            lls_urls += "http://"+lls+"\n"

   pvn_vm_list = []
   psvn_vm_list= []
   fip_vm_list = []
   gw_vm_list  = []

   for tenant in tenants:
      tenant_index = int(tenant.split('.')[-1])
      pvn_vm_list = []
      psvn_vm_list= []
      fip_vm_list = []
      gw_vm_list  = []
      client_traffic_commands = []
      server_traffic_commands = []
      remote_file_commands    = [] 
      for vn in tenants[tenant]:
         if 'Private_VN' in vn:
            pvn_vm_list.extend(tenants[tenant][vn])
         if 'Private_SNAT_VN' in vn:
            psvn_vm_list.extend(tenants[tenant][vn])
         if 'Public_FIP' in vn:
            fip_vm_list.extend(tenants[tenant][vn])
         if 'SNAT_GW' in vn:
            gw_vm_list.extend(tenants[tenant][vn])
      if pvn_vm_list:
         pvn_c_s_list = []
         if not pvn_fip:
            grp_list = grouper(2, pvn_vm_list)
            p = int(test.traffic_conf['pvn_ext_port_start']) - 1 
            for i in grp_list:
               j = i + (p,)
               pvn_c_s_list.append(j)
         else:
            if ex_srv_ip:
               first_server_port = test.traffic_conf['pvn_ext_port_start'] + tenant_index*100
               last_server_port = first_server_port + len(pvn_vm_list)
               pvn_c_s_list = zip(pvn_vm_list, [ex_srv_ip]*len(pvn_vm_list), xrange(first_server_port,last_server_port))
            else:
               num_of_fip_vms = len(fip_vm_list)
               num_ports_per_vm = len(pvn_vm_list) // num_of_fip_vms 
               first_server_port = test.traffic_conf['pvn_ext_port_start'] + tenant_index*100
               last_server_port = first_server_port + num_of_fip_vms*num_ports_per_vm
               for i,j in zip(pvn_vm_list, itertools.product(fip_vm_list, xrange(first_server_port,last_server_port))):
                  n = (i,)+j
               pvn_c_s_list.append(n)
         print pvn_c_s_list
         for c,s,p in pvn_c_s_list:
            if c and s:
               if s != ex_srv_ip:
                  build_traffic_commands(test.traffic_conf['c_iperf3'], client_traffic_commands, src_vm=c, dst_vm=s, port=p)
                  build_traffic_commands(test.traffic_conf['s_iperf3'], server_traffic_commands, src_vm=s, port=p)
                  build_traffic_commands(test.traffic_conf['httpload_lls'], client_traffic_commands, src_vm=s)
	          build_file_commands(lls_urls, remote_file_commands, s)
                  httpload_url_short = 'http://'+s['name']+"/1mb\n"
               else:
                  build_traffic_commands(test.traffic_conf['c_iperf3'], client_traffic_commands, src_vm=c, external_server_ip=s, port=p)
                  build_traffic_commands(test.traffic_conf['s_iperf3'], server_traffic_commands, external_server_ip=s, port=p)
                  httpload_url_short = 'http://'+ ex_srv_ip+'/1mb\n'
            build_traffic_commands(test.traffic_conf['httpload_short'], client_traffic_commands, src_vm=c)
            #build_traffic_commands(test.traffic_conf['httpload_lls'], client_traffic_commands, src_vm=c)
            build_file_commands(httpload_url_short, remote_file_commands, c)
            print remote_file_commands
            #build_file_commands(lls_urls, remote_file_commands, c)
            print remote_file_commands
   file_result = exec_send_file(remote_file_commands, [])
   pdb.set_trace()
   print file_result
   server_result = exec_remote_commands(server_traffic_commands, [])
   client_results = exec_remote_commands(client_traffic_commands, [])
   #status = process_and_write_ping_results(test, client_results)
   print client_results
   #return status

