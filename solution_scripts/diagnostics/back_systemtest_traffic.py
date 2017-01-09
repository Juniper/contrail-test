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

def final_client_traffic_command(traffic_command, client_traffic_commands, src, dst):
   traffic_command.append(dst)
   temp = traffic_command[:]
   client_traffic_commands.append((src, temp))
   del traffic_command[-1]

def build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm={}, dst_vm={}, external_server_ip=""):
   if src_vm and dst_vm:
      final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], dst_vm['name'])
      if dst_vm['ip_addr,fip']:
         fip_name = fip_to_name(dst_vm['ip_addr,fip'])
         final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], fip_name)
   elif src_vm and external_server_ip:
      final_client_traffic_command(traffic_command, client_traffic_commands, src_vm['ip_addr,mgmt'], external_server_ip)
   elif external_server_ip and dst_vm:
      final_client_traffic_command(traffic_command, client_traffic_commands, external_server_ip, dst_vm['ip_addr,fip'])
   else:
      return
   return

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
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               fip_vn_vm = get_one_random_vm(tenants[tenant], u'Public_FIP')
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=fip_vn_vm)
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, external_server_ip=ex_srv_ip)
         elif u'Private_VN' in vn and pvn_fip:
            for vm in tenants[tenant][vn]:
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               fip_vn_vm = get_one_random_vm(tenants[tenant], u'Public_FIP')
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=fip_vn_vm)
         elif u'Private_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
         elif u'Private_SNAT_VN' in vn and ex_srv_ip:
            for vm in tenants[tenant][vn]:
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               gw_vn_vm = get_one_random_vm(tenants[tenant], u'SNAT_GW')
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=gw_vn_vm)
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, external_server_ip=ex_srv_ip)
         elif u'Private_SNAT_VN' in vn:
            for vm in tenants[tenant][vn]:
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=vm)
               gw_vn_vm = get_one_random_vm(tenants[tenant], u'SNAT_GW')
               build_client_traffic_commands(traffic_command, client_traffic_commands, src_vm=vm, dst_vm=gw_vn_vm)
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
            if flag == 'pass':
                res_str.append('SUCCESS\n')
            else:
                res_str.append('FAIL\n')
    fp = open('ping_results.log', 'a')
    fp.write(' '.join(res_str))
    fp.close()

    return global_result
