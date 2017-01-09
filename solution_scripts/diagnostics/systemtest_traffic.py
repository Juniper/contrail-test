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
import csv

def get_one_random_vm(vns, vn_type):
   keys = vns.keys()
   random.shuffle(keys)
   for vn in keys:
      if vn_type in vn:
         if vns[vn]:
            return random.choice(vns[vn])
   return None

def is_attach_fip(test, vn_type):
   pdb.set_trace()
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

def build_ping_pvn_fip(vns, traffic_command, client_traffic_commands, vm):
    build_traffic_commands(traffic_command, client_traffic_commands,\
           		   src=vm['ip_addr,mgmt'], dst=vm['name'])
    build_traffic_commands(traffic_command, client_traffic_commands,\
                           src=vm['ip_addr,mgmt'], dst=fip_to_name(vm['ip_addr,fip']))

    pvn_vm = get_one_random_vm(vns, u'Private_VN')
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=vm['ip_addr,mgmt'], dst=pvn_vm['name'])
    pvn_vm = get_one_random_vm(vns, u'Private_VN')
    build_traffic_commands(traffic_command, client_traffic_commands,\
                           src=vm['ip_addr,mgmt'], dst=fip_to_name(pvn_vm['ip_addr,fip']))

    fip_vn_vm = get_one_random_vm(vns, u'Public_FIP')
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=fip_vn_vm['ip_addr,mgmt'], dst=fip_to_name(vm['ip_addr,fip']))
    psvn_vm = get_one_random_vm(vns, u'Private_SNAT')
    if psvn_vm:
       build_traffic_commands(traffic_command, client_traffic_commands,\
			      src=psvn_vm['ip_addr,mgmt'], dst=fip_to_name(vm['ip_addr,fip']))

def build_ping_pvn_fip_ext(vns, traffic_command, client_traffic_commands,\
                           vm, ex_srv_ip):
    build_ping_pvn_fip(vns, traffic_command, client_traffic_commands, vm)
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=vm['ip_addr,mgmt'], dst=ex_srv_ip)
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=ex_srv_ip, dst=vm['ip_addr,fip'])

def build_ping_psvn(vns, traffic_command, client_traffic_commands, vm):
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=vm['ip_addr,mgmt'], dst=vm['name'])
    gw_vn_vm = get_one_random_vm(vns, u'SNAT_GW')
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=vm['ip_addr,mgmt'], dst=gw_vn_vm['name'])
    fip_vn_vm = get_one_random_vm(vns, u'Public_FIP')
    if fip_vn_vm:
       build_traffic_commands(traffic_command, client_traffic_commands,\
			      src=vm['ip_addr,mgmt'], dst=fip_vn_vm['name'])
    pvn_vm = get_one_random_vm(vns, u'Private_VN')
    if pvn_vm:
       if pvn_vm['ip_addr,fip']:
          build_traffic_commands(traffic_command, client_traffic_commands,\
			      vm['ip_addr,mgmt'], fip_to_name(pvn_vm['ip_addr,fip']))

def build_ping_psvn_ext(vns, traffic_command, client_traffic_commands,\
                        vm, ex_srv_ip):
    build_ping_psvn(vns, traffic_command, client_traffic_commands, vm)
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=vm['ip_addr,mgmt'], dst=ex_srv_ip)

def build_ping_lb(vns, traffic_command, client_traffic_commands, vip):
    fip_vn_vm = get_one_random_vm(vns, u'Public_FIP')
    if fip_vn_vm:
       build_traffic_commands(traffic_command, client_traffic_commands,\
			      src=fip_vn_vm['ip_addr,mgmt'], dst=vip['ip_addr,fip'])

def build_ping_lb_ext(vns, traffic_command, client_traffic_commands, vip, ex_srv_ip):
    build_ping_lb(vns, traffic_command, client_traffic_commands, vip)
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=ex_srv_ip, dst=vip['ip_addr,fip'])

def build_file_commands(file_str, remote_file_commands, src):
   if isinstance(src, dict):
      remote_file_commands.append((src['ip_addr,mgmt'], file_str))
   else:
      remote_file_commands.append((src, file_str))
   return


def build_traffic_commands(traffic_command,\
                           client_traffic_commands,\
                           src="", dst="", port=""):
   if "killall" in traffic_command:
      temp = ' '.join(traffic_command)
      client_traffic_commands.append((src,temp))
   elif "ping" in traffic_command:
      traffic_command.append(dst)
      temp = ' '.join(traffic_command)
      client_traffic_commands.append((src, temp))
      del traffic_command[-1]
   elif ("iperf3" in traffic_command and "-s" in traffic_command):
      traffic_command.extend(["-p", str(port), "&"])
      temp = ' '.join(traffic_command)
      if (src,temp) not in client_traffic_commands:
         client_traffic_commands.append((src,temp))
      del traffic_command[-3:]
   elif "iperf3" in traffic_command:
      traffic_command.extend(["-c", dst, "-p", str(port), "&"])
      temp = ' '.join(traffic_command)
      if (src,temp) not in client_traffic_commands:
         client_traffic_commands.append((src,temp))
      del traffic_command[-5:]
   elif "httpload" in traffic_command:
      traffic_command.extend(["&"])
      temp = ' '.join(traffic_command)
      if (src,temp) not in client_traffic_commands:
         client_traffic_commands.append((src,temp))
      del traffic_command[-1:]
   else:
      print 'wrong command'
   return


def ping_check_setup(test, tenants, filename = "ping_result.log"):
   traffic_command = test.traffic_conf['ping']
   client_traffic_commands = []
   pvn_fip = is_attach_fip(test, 'Private_VN')
   vip_fip = is_attach_fip(test, 'Private_LB')
   ex_srv_ip = test.traffic_conf['external_server_ip']
   for tenant in tenants:
      for vn in tenants[tenant]:
         if ((u'Private_VN' in vn) and pvn_fip and ex_srv_ip):
            for vm in tenants[tenant][vn]:
               build_ping_pvn_fip_ext(tenants[tenant], traffic_command,\
                                      client_traffic_commands, vm, ex_srv_ip)
         elif u'Private_VN' in vn and pvn_fip:
            for vm in tenants[tenant][vn]:
               build_ping_pvn_fip(tenants[tenant], traffic_command,\
                                  client_traffic_commands, vm)
         elif u'Private_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_traffic_commands(tenants[tenant], traffic_command,\
                                      client_traffic_commands, src_vm=vm, dst_vm=vm)
         elif u'Private_SNAT_VN' in vn and ex_srv_ip:
            for vm in tenants[tenant][vn]:
               build_ping_psvn_ext(tenants[tenant], traffic_command,\
                                   client_traffic_commands, vm, ex_srv_ip)
         elif u'Private_SNAT_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_ping_psvn(tenants[tenant], traffic_command,\
                               client_traffic_commands, vm)
         elif u'Private_LB_VIP' in vn and ex_srv_ip:
            for vip in tenants[tenant][vn]:
               build_ping_lb_ext(tenants[tenant], traffic_command,\
                                         client_traffic_commands, vip, ex_srv_ip)
         elif u'Private_LB_POOL' in vn:
            for vip in tenants[tenant][vn]:
               build_ping_lb(tenants[tenant], traffic_command,\
                             client_traffic_commands, vip)
         else:
            continue
   print time.time()
   client_results = exec_remote_commands(client_traffic_commands, [], 1800)
   print time.time()
   status = process_and_write_ping_results(test, client_results, filename)
   return status

def process_and_write_ping_results(test, results, filename):
    unknown_re = re.compile(r'^ping: unknown host (.*)$')
    name_re = re.compile(r'^(PING .+) \(([\d.]+)\) .+ data.$')
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
                    if ('vm' not in match.group(1) and (ex_srv_ip != match.group(1) and client['address'] != ex_srv_ip)):
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
    fp = open(filename, 'w')
    fp.write(' '.join(res_str))
    fp.close()
    return global_result


def compute_c_s_p_tuple(test, tenant_index, pvn_vm_list = [], psvn_vm_list = [], fip_vm_list = [], gw_vm_list = []):
   ex_srv_ip = test.traffic_conf['external_server_ip']
   vm_list = []
   c_s_p_list = []
   
   if pvn_vm_list:
      port_start = 'pvn_ext_port_start'
      vm_list = pvn_vm_list
      dst_vm_list = fip_vm_list
   elif psvn_vm_list:
      port_start = 'psvn_ext_port_start'
      vm_list = psvn_vm_list
      dst_vm_list = gw_vm_list
      
   if ex_srv_ip:
      first_server_port = test.traffic_conf[port_start] + tenant_index*100
      last_server_port = first_server_port + len(vm_list)
      c_s_p_list = zip(vm_list, [ex_srv_ip]*len(vm_list), xrange(first_server_port,last_server_port))
   else:
      num_of_dst_vms = len(dst_vm_list)
      num_ports_per_vm = len(vm_list) // num_of_dst_vms 
      first_server_port = test.traffic_conf[port_start]
      last_server_port = first_server_port + num_of_dst_vms*num_ports_per_vm
      for i,j in zip(vm_list, itertools.product(dst_vm_list, xrange(first_server_port,last_server_port))):
         n = (i,)+j
         c_s_p_list.append(n)
   return c_s_p_list


def handle_psvn_traffic(test, psvn_vm_list, gw_vm_list, tenant_index):
   
   psvn_c_s_list = []
   
   return compute_c_s_p_tuple(test, tenant_index, psvn_vm_list = psvn_vm_list, gw_vm_list = gw_vm_list)

    
def handle_pvn_traffic(test, pvn_vm_list, fip_vm_list, tenant_index):
   
   pvn_fip = is_attach_fip(test, 'Private_VN')
   pvn_c_s_list = []
   
   if not pvn_fip:
      grp_list = grouper(2, pvn_vm_list)
      p = int(test.traffic_conf['pvn_ext_port_start']) - 1 
      for i in grp_list:
         j = i + (p,)
         pvn_c_s_list.append(j)
      return pvn_c_s_list
   else:
      return compute_c_s_p_tuple(test, tenant_index, pvn_vm_list = pvn_vm_list, fip_vm_list = fip_vm_list)
   

def handle_lbaas_traffic(test, vip_list, client_traffic_commands, remote_file_commands, pvn_vm_list = [], psvn_vm_list = []):
   pvn_fip = is_attach_fip(test, 'Private_VN')
   ex_srv_ip = test.traffic_conf['external_server_ip']
   httpload_url_lbaas = ""
   url_lb_file = '/opt/contrail/tools/http/httpload/url_lb'
   run = '/opt/contrail/zmq/run'

   for vip in vip_list:
      if ex_srv_ip:
         httpload_url_lbaas += 'http://'+vip['ip_addr,fip']+':'+str(vip['vip,protocol_port'])+'/512kb\n'
      else:
         httpload_url_lbaas += 'http://'+fip_to_name(vip['ip_addr,fip'])+':'+str(vip['vip,protocol_port'])+'/512kb\n'

   computed_run= str(int(test.traffic_conf['duration']) // int(test.traffic_conf['sampling_interval']))

   if ex_srv_ip:
      computed_lbaas_rate = int(test.traffic_conf['httpload_lb'][2])*len(vip_list)
      computed_lbaas_command = [run, computed_run, 'httpload', '-rate', str(computed_lbaas_rate), '-seconds',\
                                test.traffic_conf['sampling_interval'], url_lb_file]
      build_traffic_commands(computed_lbaas_command, client_traffic_commands, src=ex_srv_ip)
      build_file_commands(httpload_url_lbaas, remote_file_commands, src=ex_srv_ip)
   else:
      if pvn_fip:
         vm_list = pvn_vm_list + psvn_vm_list
      else:
         vm_list = psvn_vm_list
      computed_lbaas_rate = int(test.traffic_conf['httpload_lb'][2])*len(vip_list) // len(vm_list)
      computed_lbaas_command = [run, computed_run, 'httpload', '-rate', str(computed_lbaas_rate), '-seconds',\
                                test.traffic_conf['sampling_interval'], url_lb_file]
      for vm in vm_list:
         build_traffic_commands(computed_lbaas_command, client_traffic_commands, src=vm['ip_addr,mgmt'])
         build_file_commands(httpload_url_lbaas, remote_file_commands, src=vm)


def build_kill_traffic_commands(test, tenants):
   vm_list = []
   kill_traffic_commands = []
   kill_iperf = ['killall', 'iperf3']
   kill_bash = ['killall', '/bin/bash']
   kill_httpload = ['killall', 'httpload']
   ex_srv_ip = test.traffic_conf.get('external_server_ip', None)
   kill_vn_list = ['Private_VN', 'Private_SNAT', 'Public_FIP', 'SNAT_GW']

 
   for tenant in tenants:
      for vn in tenants[tenant]:
         if any(x in vn for x in kill_vn_list): 
            for vm in tenants[tenant][vn]:
               build_traffic_commands(kill_iperf, kill_traffic_commands, src=vm['ip_addr,mgmt'])
               build_traffic_commands(kill_bash, kill_traffic_commands, src=vm['ip_addr,mgmt'])
               build_traffic_commands(kill_httpload, kill_traffic_commands, src=vm['ip_addr,mgmt'])

   if ex_srv_ip:
      build_traffic_commands(kill_iperf, kill_traffic_commands, src=ex_srv_ip)
      build_traffic_commands(kill_bash, kill_traffic_commands, src=ex_srv_ip)
      build_traffic_commands(kill_httpload, kill_traffic_commands, src=ex_srv_ip)
   
   kill_result = exec_remote_kill(kill_traffic_commands, [], 120)

   
def run_traffic(test, tenants, filename = ""):

   client_traffic_commands = []
   remote_file_commands = []
   server_traffic_commands = []

   pvn_fip = is_attach_fip(test, 'Private_VN')
   vip_fip = is_attach_fip(test, 'Private_LB')
   ex_srv_ip = test.traffic_conf.get('external_server_ip', None)
  
   if test.global_conf.get('lls,name', None):
      lls_urls = ""
      lls_obj = LLS(None)
      lls_list = lls_obj.retrieve_existing_services()
      for lls in lls_list:
         if lls[0] != 'metadata':
            lls_urls += "http://"+lls[0]+':'+str(lls[2])+"/256kb\n"

   for tenant in tenants:
      tenant_index = int(tenant.split('.')[-1])
      pvn_vm_list = []
      psvn_vm_list= []
      fip_vm_list = []
      gw_vm_list  = []
      ip_list    = []
      pvn_c_s_list = []
      psvn_c_s_list = []
      vip_list = []

      for vn in tenants[tenant]:
         if 'Private_VN' in vn:
            pvn_vm_list.extend(tenants[tenant][vn])
         if 'Private_SNAT_VN' in vn:
            psvn_vm_list.extend(tenants[tenant][vn])
         if 'Public_FIP' in vn:
            fip_vm_list.extend(tenants[tenant][vn])
         if 'SNAT_GW' in vn:
            gw_vm_list.extend(tenants[tenant][vn])
         if 'VIP' in vn:
            vip_list.extend(tenants[tenant][vn])
        
      if pvn_vm_list:
         pvn_c_s_list = handle_pvn_traffic(test, pvn_vm_list, fip_vm_list, tenant_index)
      if psvn_vm_list:
         psvn_c_s_list = handle_psvn_traffic(test, psvn_vm_list, gw_vm_list, tenant_index)
      if vip_list:
         handle_lbaas_traffic(test, vip_list, client_traffic_commands, remote_file_commands,\
                              pvn_vm_list, psvn_vm_list)

      for c,s,p in itertools.chain(pvn_c_s_list, psvn_c_s_list):
         #pvn without fip, grouper will return none server when vm count is odd.
         #ignore the last vm in such a case.
         if c and s: 
            if s != ex_srv_ip:
               build_traffic_commands(test.traffic_conf['c_iperf3'], client_traffic_commands, src=c['ip_addr,mgmt'], dst=s['name'], port=p)
               build_traffic_commands(test.traffic_conf['s_iperf3'], server_traffic_commands, src=s['ip_addr,mgmt'], port=p)
               build_traffic_commands(test.traffic_conf['httpload_lls'], client_traffic_commands, src=s['ip_addr,mgmt'])
	       build_file_commands(lls_urls, remote_file_commands, s)
               httpload_url_short = 'http://'+s['name']+"/1mb\n"
            else:
               build_traffic_commands(test.traffic_conf['c_iperf3'], client_traffic_commands, src=c['ip_addr,mgmt'], dst=s, port=p)
               build_traffic_commands(test.traffic_conf['s_iperf3'], server_traffic_commands, src=s, port=p)
               httpload_url_short = 'http://'+ ex_srv_ip+'/1mb\n'
            build_traffic_commands(test.traffic_conf['httpload_short'], client_traffic_commands, src=c['ip_addr,mgmt'])
            build_traffic_commands(test.traffic_conf['httpload_lls'], client_traffic_commands, src=c['ip_addr,mgmt'])
            build_file_commands(httpload_url_short, remote_file_commands, c)
            build_file_commands(lls_urls, remote_file_commands, c)
   file_result = exec_send_file(remote_file_commands, [], 180)
   server_result = exec_remote_commands(server_traffic_commands, [], 180)
   print time.time()
   client_results = exec_remote_commands(client_traffic_commands, [], float(test.traffic_conf['duration'])+180)
   print time.time()
   process_client_results(client_results)

def get_httpload_type(command):
   url = re.compile(r'^.*/opt/contrail/tools/http/httpload/url_([\w]+) &$')
   match = url.match(command)
   if match:
      return match.group(1)

def process_client_results(client_results):

   iperf3 = {}
   #fetches, code_200, failures, fetches/sec, conn_min, conn_max, conn_mean
   httpload_short = {}
   httpload_lb = {}
   httpload_lls = {}
   for client in client_results:
      for result in client['results']:
         if 'iperf3' in result['command'][0]:
            if not result['error']:
               iperf3_stats_handler(iperf3, result['output'])
            else:
               iperf3_error_handler(result['error'])   
         elif 'httpload' in result['command'][0]:
            if not result['error']:
               http_type = get_httpload_type(result['command'][0])
               if http_type == 'lls':
                  httpload_stats_handler(httpload_lls, result['output'], client['address'], result['command'])
               elif http_type == 'lb':
                  httpload_stats_handler(httpload_lb, result['output'], client['address'], result['command'])
               elif http_type == 'short':
                  httpload_stats_handler(httpload_short, result['output'], client['address'], result['command'])
               else:
                  print 'error'
            else:
               httpload_error_handler(result['error'])
   print 'iperf'
   print_dic(iperf3)
   print 'short'
   print_dic(httpload_short)
   print 'lb'
   print_dic(httpload_lb)
   print 'lls'
   print_dic(httpload_lls)

   fp = open('res.csv', 'wb')
   writer = csv.writer(fp, dialect = 'excel')
   title = ['Throughput', 'Retrans', 'S_Fetches', 'S_Success', 'S_Failures', 'S_Rate', 'S_min', 'S_max', 'S_mean',\
                                     'LL_Fetches', 'LL_Success', 'LL_Failures', 'LL_Rate', 'LL_min', 'LL_max', 'LL_mean',\
                                     'LB_Fetches', 'LB_Success', 'LB_Failures', 'LB_Rate', 'LB_min', 'LB_max', 'LB_mean']
   writer.writerow(title)

   for row in zip(iperf3['total'], httpload_short['total'], httpload_lls['total'], httpload_lb['total']):
      row_tup = row[0]+row[1]+row[2]+row[3]
      writer.writerow(row_tup)
   fp.close()

def write_results_csv(output):
   fp = open('res.csv', 'wb')
   writer = csv.writer(fp, delimiter = ',')
   for row in output['total']:
      writer.writerow(row)
   fp.close()
      
def iperf3_error_handler(error):
   return

def print_dic(temp):
   for i in temp:
      if i == 'total':
         print i, temp[i]

def iperf3_stats_handler(iperf3, output):

   vm_stats = []
   total_vm_stats = []

   output = json.loads(output)
   local_host = output['start']['connected'][0]['local_host']
   remote_host = output['start']['connected'][0]['remote_host']

   for index,sample in enumerate(output['intervals']):
      mbps = float(sample['sum']['bits_per_second'] / 1000000.0)
      retrans =  int(sample['sum']['retransmits'])
      vm_stats.append((mbps, retrans))

   iperf3[local_host,remote_host] = vm_stats
   if not iperf3.get('total',0):
      iperf3['total'] = vm_stats 
   else:
      for x,y in zip(iperf3['total'], vm_stats):
         mbps_tot = float('{0:.2f}'.format(x[0] + y[0]))
         retrans_tot = float('{0:.2f}'.format(x[1] + y[1]))
         total_vm_stats.append((mbps_tot,retrans_tot))
      iperf3['total'] = total_vm_stats

def httpload_stats_handler(httpload_result, output, address, command):
  
   line1_re = re.compile(r'^([\d.]+) fetches.*in ([\d.]+) seconds$') 
   line2_re = re.compile(r'^msecs/connect: ([\d.]+) mean, ([\d.]+) max, ([\d.]+) min$')
   line3_re = re.compile(r'^msecs/first-response: ([\d.]+) mean, ([\d.]+) max, ([\d.]+) min$')
   line4_re = re.compile(r'^.*code 200 -- ([\d]+)$')
   rate_match = re.search(r'-rate (\d+)', command[0])
   rate = int(rate_match.group(1))
 
   total_result = []
   http_temp = []
   
   for line in output.splitlines():
      match = line1_re.match(line)
      if match:
         fetches = int(match.group(1))
         continue
      match = line2_re.match(line)
      if match:
         conn_mean = float('{0:.2f}'.format(float(match.group(1))))
         conn_max  = float('{0:.2f}'.format(float(match.group(2))))
         conn_min  = float('{0:.2f}'.format(float(match.group(3))))
         continue
      match = line3_re.match(line)
      if match:
         ttfb_mean = float('{0:.2f}'.format(float(match.group(1))))
         ttfb_max  = float('{0:.2f}'.format(float(match.group(2))))
         ttfb_min  = float('{0:.2f}'.format(float(match.group(3))))
         continue
      match = line4_re.match(line)
      if match:
         code_200 = int(match.group(1))
         failures = fetches - code_200
         temp = (fetches, code_200, failures, rate, conn_min, conn_max, conn_mean)
         if not httpload_result.get(address, None):
            httpload_result[address] = [temp]
         else:
            httpload_result[address].append(temp)
   
   if not httpload_result.get('total', None):
      httpload_result['total'] = httpload_result[address]
   else:
      for x in zip(httpload_result['total'], httpload_result[address]):
         for i in xrange(0,7):
            if i == 4:
               z = min(x[0][i],x[1][i])
            elif i == 5:
               z = max(x[0][i],x[1][i])
            elif i == 6:
               z = float('{0:.2f}'.format((x[0][i] * (len(httpload_result)-2)) + (x[1][i]/(len(httpload_result)-1))))
            else:
               z = float('{0:.2f}'.format(x[0][i] + x[1][i]))
            total_result.append(z)
         http_temp.append(tuple(total_result))
         total_result = []
      httpload_result['total'] = http_temp[:]
      http_temp = []
     
def httpload_error_handler(error):
   return
