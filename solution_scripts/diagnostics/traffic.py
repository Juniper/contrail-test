import pdb
import os
import re
from lib import *
import time
from send_zmq import *
from config import *
import itertools
import csv
import threading, Queue

ping_code = {}

def redo_dhclient(tenants):
   comm = ['dhclient eth0']
   dhcl = []
   for tenant in tenants:
      for vn in tenants[tenant]:
         for vm in tenants[tenant][vn]:
            build_traffic_commands(comm, dhcl, src=vm['ip_addr,mgmt'])
   dhclient_res = exec_remote_commands(dhcl, [], 600)

def check_dhclient_int(tors, bms_vlans):
   dhcp_command = []
   total_ints = 0

   for tor in tors:
      for bms in tor['bms']:
         comm = ['for i in $(ip netns list); do ip netns exec $i ifconfig %s.$i | grep Bcast; done | wc -l'%(bms['physical_server_interface'])]
         build_traffic_commands(comm, dhcp_command, src=bms['physical_server_mgmt_ip'])
   dhcp_res = exec_remote_commands(dhcp_command, [], 600)

   for bms in dhcp_res:
      for result in bms['results']:
         total_ints += int(result['output'])
   return total_ints

def setup_bms_netns(tors, bms_vlans):
   netns_command = []
   dhclient_command = []
   netns_resolv = []
   i = 0

   for tor in tors:
      for bms in tor['bms']:
         for vlan in bms_vlans[bms['physical_server_mgmt_ip']]:
            traffic_command = ['/opt/contrail/zmq/nc', bms['physical_server_interface'], str(vlan)]
            build_traffic_commands(traffic_command, netns_command, src=bms['physical_server_mgmt_ip'])

   netns = exec_remote_commands(netns_command, [], 600)

   while check_dhclient_int(tors, bms_vlans) != len(netns_command):
      for tor in tors:
         for bms in tor['bms']:
            for vlan in bms_vlans[bms['physical_server_mgmt_ip']]:
               traffic_command = ['ip netns exec %s dhclient %s.%s'%(str(vlan), bms['physical_server_interface'], str(vlan))]
               build_traffic_commands(traffic_command, dhclient_command, src=bms['physical_server_mgmt_ip'])
      dhclient = exec_remote_commands(dhclient_command, [], 600)
      i += 1
      if i == 3:
         return 0

   for tor in tors:
      for bms in tor['bms']:
         for vlan in bms_vlans[bms['physical_server_mgmt_ip']]:
               traffic_command = ['/opt/contrail/zmq/net_resolv.sh %s %s'%(bms['physical_server_interface'], str(vlan))]
               build_traffic_commands(traffic_command, netns_resolv, src=bms['physical_server_mgmt_ip'])
   resolv = exec_remote_commands(netns_resolv, [], 600)
   
   return 1

def cleanup_bms_netns(tors, bms_vlans):
   netns_command = []
   for tor in tors:
      for bms in tor['bms']:
         traffic_command = ['/opt/contrail/zmq/nd', bms['physical_server_interface']]
         build_traffic_commands(traffic_command, netns_command, src=bms['physical_server_mgmt_ip'])
   netns = exec_remote_commands(netns_command, [], 600)

def get_one_vm_from_vn(temp_vn, exclude_vm = {}):
   vn = temp_vn[:]
   random.shuffle(vn)    
   for vm in vn:
      if not vm['is_bms']:
         if (exclude_vm and not exclude_vm['is_bms']):
            if exclude_vm['name'] != vm['name']:
               return vm
            else:
               continue
         else:
            return vm

def get_one_bms_from_vn(temp_vn, vm = {}):
   vn = temp_vn[:]
   random.shuffle(vn)
   for bms in vn:
      if bms['is_bms']:
         if (vm and vm['is_bms']):
            if bms['name'].split('.')[0] != vm['name'].split('.')[0]:
               return bms 
            else:
               continue
         else:
            return bms
   
def get_one_random_vm(vns, vn_type):
   keys = vns.keys()
   random.shuffle(keys)
   for vn in keys:
      if vn_type in vn:
         if vns[vn]:
            return get_one_vm_from_vn(vns[vn])

def get_one_random_bms(vns, vn_type, vm):
   keys = vns.keys()
   random.shuffle(keys)
   for vn in keys:
      if vn_type in vn:
         if vns[vn]:
            return get_one_bms_from_vn(vns[vn], vm) 

def get_vm_only(vn):
   vm_only = []
   for vm in vn:
      if not vm['is_bms']:
         vm_only.append(vm)
   return vm_only

def vn_pattern(vn):
   if vn:
      return vn.split('.')[-1].strip("0123456789")

def is_attach_fip_vn_type(test, vn_type):
   for vn_group in test.tenant_conf['tenant,vn_group_list']:
      if vn_type in vn_group['vn,name,pattern'].split('.')[2]:
         if vn_group['attach_fip'] == True:
            return True
         else:
            return False

def is_attach_fip(vn):
   for vm in vn:
      if vm['ip_addr,fip']:
         return True
      else:
         return False

def fip_to_name(fip):
   if fip:
      return '-'.join(fip.split('.'))

def transform_to_bms(command, vlan):
   transform_command = command[:] 
   if 'http_load' in command:
      transform_command[-1] += str(vlan)

   netns_command = ['ip', 'netns', 'exec'] + [str(vlan)]
   for i in netns_command[::-1]:
      transform_command.insert(0, i)

   return transform_command

def transform_to_run(command, computed_run):
   run = '/opt/contrail/zmq/run'
   final_command = [run, computed_run] + command
   return final_command

def fqdn(tenant, name, vm = {}):
   temp = '.test1.data.soln.com'
   x = tenant.split(':')
   if vm['is_bms'] or not vm:
      try:
        tenant_num = re.search('Tenant(\d+)', tenant).group(1)
        dom_name1 = "tenant" + tenant_num
        return (name +'.' + dom_name1 + temp)
      except:
        import traceback;traceback.print_exc(sys.stdout)
        import pdb;pdb.set_trace()
   else:
      return name
    
def grouper(n, iterable, fillvalue=None):
   args = [iter(iterable)] * n
   return itertools.izip_longest(*args, fillvalue=fillvalue)

def mgmt_ip_reachable(tenants):
   ping_command = "ping -c 3 -W 3 "
   processes = []
   results = []
   match = None
   mgmt_ips = []
   status = 1
   vms = {}
  
   for tenant in tenants:
      for vn in tenants[tenant]:
         for vm in tenants[tenant][vn]:
            if vm['ip_addr,mgmt']:
               if vm['ip_addr,mgmt'] not in vms:
                  vms[vm['ip_addr,mgmt']] = True

   for k in vms:                  
      command = ping_command + k 
      proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
      processes.append((proc, command))

   for proc, command in processes:
      out, error = proc.communicate()
      results.append(dict(output=out, error=error, command=command)) 
   
   for result in results:
      output = result['output']
      match = re.search(r'100% packet loss', output)
      if match:
         mgmt_ips.append(result['command'])
         status = 0

   if not status:   
      print 'mgmt ping failed for: \n'
      for ip in mgmt_ips:   
         print ip

   return status      


def update_ping_code(src_code, dst_code):
    global ping_code

    if len(src_code) == 1:
       for dst in dst_code:
          ping_code[(src_code[0][0], src_code[0][1])] = ping_code.get((src_code[0][0], src_code[0][1]), []) +\
                                               [[src_code[0][2], src_code[0][3],\
                                                dst[0], dst[1], dst[2]]]
    else:
       for src in src_code:
          ping_code[(src[0], src[1])] = ping_code.get((src[0], src[1]), []) +\
                                                       [[src[2], src[3], \
                                                         dst_code[0][0], dst_code[0][1], dst_code[0][2]]]

def ping_code_str(mgmt_add, vlan):
    if ping_code[(mgmt_add,vlan)]:
       temp = ping_code[(mgmt_add,vlan)].pop(0)
       return '_'.join(temp[:2])+'->'+'_'.join(temp[2:])
    else:
       print 'ping_code error'

def build_ping_pvn(tenant, vn, vns, traffic_command, client_traffic_commands, vm):

    dst_code = []

    if vm['is_bms']:
       traffic_command = transform_to_bms(traffic_command, vm['vlan'])
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'BMS', 'PVN')]
    # Ping self's name. Not supported for BMS
    else:
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'VM', 'PVN')]
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=vm['name'])
       dst_code.append(('VM', 'SelfName', 'None'))

    # Intra-VN ping
    pvn_vm = get_one_vm_from_vn(vns[vn], vm)
    if pvn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, pvn_vm['name'], vm))
       dst_code.append(('VM', 'PvnIntra', 'None'))

    pvn_bms = get_one_bms_from_vn(vns[vn], vm)
    if pvn_bms:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=pvn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'PvnIntra', 'None'))

    # Inter-VN ping
    # Assumes all PVNs can talk to each other via policy config

    if len(vns) > 30:
       vn_list = []
       for vnet in vns:
          if (vnet != vn and vn_pattern(vnet) == vn_pattern(vn)):
             vn_list.append(vnet)

       random_vn = random.choice(vn_list)
       pvn_vm = get_one_vm_from_vn(vns[random_vn])
       if pvn_vm:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'],\
                                 dst=fqdn(tenant, pvn_vm['name'], vm))
          dst_code.append(('VM', 'PvnInter', 'None'))

       pvn_bms = get_one_bms_from_vn(vns[random_vn], vm)
       if pvn_bms:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'],\
                                 dst=pvn_bms['ip_addr,data'])
          dst_code.append(('BMS', 'PvnInter', 'None'))
  
       update_ping_code(src_code, dst_code)

       return
 
    for vnet in vns:
       if (vnet != vn and vn_pattern(vnet) == vn_pattern(vn)):
          pvn_vm = get_one_vm_from_vn(vns[vnet])
          if pvn_vm:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=fqdn(tenant, pvn_vm['name'], vm))
             dst_code.append(('VM', 'PvnInter', 'None'))

          pvn_bms = get_one_bms_from_vn(vns[vnet], vm)
          if pvn_bms:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=pvn_bms['ip_addr,data'])
             dst_code.append(('BMS', 'PvnInter', 'None'))

    update_ping_code(src_code, dst_code)


def build_ping_pvn_fip(tenant, vn, vns, traffic_command, client_traffic_commands, vm):

    dst_code = []

    if vm['is_bms']:
       traffic_command = transform_to_bms(traffic_command, vm['vlan'])
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'BMS', 'PVN')]
    else:
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'VM', 'PVN')]

   
    ## vm/BMS behind FIP cant ping BMS on FIP VN.
    ## BMS behind SNAT can.t ping BMS on SNAT GW VN. 

    build_ping_pvn(tenant, vn, vns, traffic_command, client_traffic_commands, vm)

    fip_vn_vm = get_one_random_vm(vns, 'Public_FIP')
    if fip_vn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, fip_vn_vm['name'], vm))
       dst_code.append(('VM', 'PubFIP', 'None'))


    fip_vn_bms = get_one_random_bms(vns, 'Public_FIP', vm)
    if fip_vn_bms:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fip_vn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'PubFIP', 'None'))

    '''
    gw_vn_vm = get_one_random_vm(vns, 'SNAT_GW')
    if gw_vn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, gw_vn_vm['name'], vm))
       dst_code.append(('VM', 'SnatGW', 'None'))

    gw_vn_bms = get_one_random_bms(vns, 'SNAT_GW', vm)
    if gw_vn_bms:
       build_traffic_commands(traffic_command, \
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'], \
                              dst=gw_vn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'SnatGW', 'None'))
    '''

    if len(vns) > 30:
       vn_list = []
       for vnet in vns:
          if (vnet != vn and vn_pattern(vnet) in  ['Private_VN', 'Private_LB_VIP_VN']):
             vn_list.append(vnet)

       random_vn = random.choice(vn_list)

       if is_attach_fip(vns[random_vn]):
       
          pvn_vm = get_one_vm_from_vn(vns[random_vn])
          if pvn_vm:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'], \
                                    dst=fqdn(tenant, \
                                    fip_to_name(pvn_vm['ip_addr,fip']), vm))
             if 'VIP' in vnet:
                dst_code.append(('VIP', 'VipVN', 'FIP'))
             else:
                dst_code.append(('VM', 'PvnInter', 'FIP'))

          pvn_bms = get_one_bms_from_vn(vns[random_vn], vm)
          if pvn_bms:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'], \
                                    dst=pvn_bms['ip_addr,fip'])
             dst_code.append(('BMS', 'PvnInter', 'FIP'))

       update_ping_code(src_code, dst_code)

       return


    for vnet in vns:
       if (vnet != vn and vn_pattern(vnet) in ['Private_VN', 'Private_LB_VIP_VN']):
          if is_attach_fip(vns[vnet]):
             pvn_vm = get_one_vm_from_vn(vns[vnet])
             if pvn_vm:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'], \
                                       dst=fqdn(tenant, \
                                       fip_to_name(pvn_vm['ip_addr,fip']), vm))
                if 'VIP' in vnet:
                   dst_code.append(('VIP', 'VipVN', 'FIP'))
                else:
                   dst_code.append(('VM', 'PvnInter', 'FIP'))


             pvn_bms = get_one_bms_from_vn(vns[vnet])
             if pvn_bms:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'], \
                                       dst=pvn_bms['ip_addr,fip'])
                dst_code.append(('BMS', 'PvnInter', 'FIP'))

    update_ping_code(src_code, dst_code)

       
def build_ping_pvn_fip_ext(tenant, vn, vns, traffic_command, client_traffic_commands,\
                           vm, ex_srv_ip):


    ex_traffic_command = traffic_command 

    if vm['is_bms']:
       traffic_command = transform_to_bms(traffic_command, vm['vlan'])
       host = 'BMS'
       import pdb;pdb.set_trace()
    else:
       host = 'VM'

    
    build_ping_pvn_fip(tenant, vn, vns, traffic_command, client_traffic_commands, vm)

    build_traffic_commands(traffic_command,\
                           client_traffic_commands,\
                           src=vm['ip_addr,mgmt'],\
                           dst=ex_srv_ip)
    src_code = [(vm['ip_addr,mgmt'], vm['vlan'], host, 'PVN')]
    dst_code = [('Ext', 'Ext', 'None')]
    update_ping_code(src_code, dst_code)
 
    build_traffic_commands(ex_traffic_command,\
                           client_traffic_commands,\
                           src=ex_srv_ip,\
                           dst=vm['ip_addr,fip'])
    src_code = [(ex_srv_ip, None, 'Ext', 'Ext')]
    dst_code = [(host, 'PVN', 'FIP')]
    update_ping_code(src_code, dst_code)


def build_ping_psvn(tenant, vn, vns, traffic_command, client_traffic_commands, vm):


    dst_code = []
    
    if vm['is_bms']:
       traffic_command = transform_to_bms(traffic_command, vm['vlan'])
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'BMS', 'PSVN')]
    else:
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'VM', 'PSVN')]
       build_traffic_commands(traffic_command, client_traffic_commands,\
                           src=vm['ip_addr,mgmt'], dst=vm['name'])
       dst_code.append(('VM', 'SelfName', 'None'))
 
    # Intra-VN ping    
    psvn_vm = get_one_vm_from_vn(vns[vn])
    if psvn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, psvn_vm['name'], vm))
       dst_code.append(('VM', 'PsvnIntra', 'None'))

    psvn_bms = get_one_bms_from_vn(vns[vn], vm)
    if psvn_bms:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=psvn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'PsvnIntra', 'None'))

    # Ping VM/BMS on FIP VN
    fip_vn_vm = get_one_random_vm(vns, 'Public_FIP')
    if fip_vn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, fip_vn_vm['name'], vm))
       dst_code.append(('VM', 'PubFIP', 'None'))


    fip_vn_bms = get_one_random_bms(vns, 'Public_FIP', vm)
    if fip_vn_bms:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fip_vn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'PubFIP', 'None'))

    # Ping VM/BMS on SNAT GW VN
    '''
    gw_vn_vm = get_one_random_vm(vns, 'SNAT_GW')
    if gw_vn_vm:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=fqdn(tenant, gw_vn_vm['name'], vm))
       dst_code.append(('VM', 'SnatGW', 'None'))

    gw_vn_bms = get_one_random_bms(vns, 'SNAT_GW', vm)
    if gw_vn_bms:
       build_traffic_commands(traffic_command,\
                              client_traffic_commands,\
                              src=vm['ip_addr,mgmt'],\
                              dst=gw_vn_bms['ip_addr,data'])
       dst_code.append(('BMS', 'SnatGW', 'None'))
    '''

    if len(vns) > 30:
       vn_list = []
       pvn_vip_list = []
       for vnet in vns:
          if (vnet != vn and vn_pattern(vnet) == vn_pattern(vn)):
             vn_list.append(vnet)
          elif vn_pattern(vnet) in ['Private_VN', 'Private_LB_VIP_VN']:
             pvn_vip_list.append(vnet)

       random_vn = random.choice(vn_list)
       random_pvn_vip = random.choice(pvn_vip_list)

       random_psvn_vm = get_one_vm_from_vn(vns[random_vn])
       if random_psvn_vm:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'], \
                                 dst=fqdn(tenant, random_psvn_vm['name'], vm))
          dst_code.append(('VM', 'PsvnInter', 'None'))

       random_psvn_bms = get_one_bms_from_vn(vns[vnet], vm)
       if random_psvn_bms:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'],\
                                 dst=random_psvn_bms['ip_addr,data'])
          dst_code.append(('BMS', 'PsvnInter', 'None'))
      
 
       if random_pvn_vip: 
          if is_attach_fip(vns[random_pvn_vip]):
             random_pvn_vip_vm = get_one_vm_from_vn(vns[random_pvn_vip])
             if random_pvn_vip_vm:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'],\
                                       dst=fqdn(tenant, fip_to_name(\
                                              random_pvn_vip_vm['ip_addr,fip']), vm))
                if 'VIP' in random_pvn_vip:
                   dst_code.append(('VIP', 'VipVN', 'FIP'))
                else:
                   dst_code.append(('VM', 'PVN', 'FIP'))

             random_pvn_vip_bms = get_one_bms_from_vn(vns[random_pvn_vip], vm)
             if random_pvn_vip_bms:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'],\
                                       dst=random_pvn_vip_bms['ip_addr,fip'])
                if 'VIP' in random_pvn_vip:
                   dst_code.append(('VIP', 'VipVN', 'FIP'))
                else:
                   dst_code.append(('BMS', 'PVN', 'FIP'))

       update_ping_code(src_code, dst_code)

       return
       
       
    for vnet in vns:
       ## Works only if VNs are connected to same Logical Router.
       ## Add Router info to VN dictionary and update the below
       ## if conditional to ensure VNs are connected to same
       ## logical router.
 
       # Inter-VN ping. Ping hosts on other PVNs connected
       # to the LR
       if (vnet != vn and vn_pattern(vnet) == vn_pattern(vn)):
          psvn_vm = get_one_vm_from_vn(vns[vnet])
          if psvn_vm:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=fqdn(tenant, psvn_vm['name'], vm))
             dst_code.append(('VM', 'PsvnInter', 'None'))

          psvn_bms = get_one_bms_from_vn(vns[vnet], vm)
          if psvn_bms:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=psvn_bms['ip_addr,data'])
             dst_code.append(('BMS', 'PsvnInter', 'None'))

       # Ping VM/BMS FIP and VIP/FIP
       if vn_pattern(vnet) in ['Private_VN', 'Private_LB_VIP_VN']:
          if is_attach_fip(vns[vnet]):
             psvn_vm = get_one_vm_from_vn(vns[vnet])
             if psvn_vm:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'],\
                                       dst=fqdn(tenant, fip_to_name(\
                                              psvn_vm['ip_addr,fip']), vm))
                if 'VIP' in vnet:
                   dst_code.append(('VIP', 'VipVN', 'FIP'))
                else:
                   dst_code.append(('VM', 'PVN', 'FIP'))

             psvn_bms = get_one_bms_from_vn(vns[vnet], vm)
             if psvn_bms:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=vm['ip_addr,mgmt'],\
                                       dst=psvn_bms['ip_addr,fip'])
                if 'VIP' in vnet:
                   dst_code.append(('VIP', 'VipVN', 'FIP'))
                else:
                   dst_code.append(('BMS', 'PVN', 'FIP'))

    update_ping_code(src_code, dst_code)

def build_ping_psvn_ext(tenant, vn, vns, traffic_command, client_traffic_commands,\
                        vm, ex_srv_ip):


    if vm['is_bms']:
       traffic_command = transform_to_bms(traffic_command, vm['vlan'])
       host = 'BMS'
    else:
       host = 'VM'

    build_ping_psvn(tenant, vn, vns, traffic_command, client_traffic_commands, vm)
    build_traffic_commands(traffic_command, client_traffic_commands,\
                           src=vm['ip_addr,mgmt'], dst=ex_srv_ip)
    src_code = [(vm['ip_addr,mgmt'], vm['vlan'], host, 'PSVN')]
    dst_code = [('Ext', 'Ext', 'None')]
    update_ping_code(src_code, dst_code)
    

def build_ping_lb(tenant, vn, vns, traffic_command, client_traffic_commands, vip):

    dst_code = []
    src_code = []

    dst_code.append(('VIP', 'VipVN', 'FIP'))

    for vnet in vns:
       if (vnet != vn and vn_pattern(vnet) in ['Public_FIP_VN', 'Private_SNAT_VN', 'Private_VN']):
             pvn_vm = get_one_vm_from_vn(vns[vnet])
             if pvn_vm and vip['ip_addr,fip']:
                build_traffic_commands(traffic_command,\
                                       client_traffic_commands,\
                                       src=pvn_vm['ip_addr,mgmt'],\
                                       dst=fip_to_name(vip['ip_addr,fip']))
                if 'SNAT' in vnet:
                   src_code.append((pvn_vm['ip_addr,mgmt'],pvn_vm['vlan'], 'VM', 'PSVN'))
                elif 'FIP' in vnet:
                   src_code.append((pvn_vm['ip_addr,mgmt'],pvn_vm['vlan'], 'VM', 'PubFIP'))
                else: 
                   src_code.append((pvn_vm['ip_addr,mgmt'],pvn_vm['vlan'], 'VM', 'PVN'))

             pvn_bms = get_one_bms_from_vn(vns[vnet])
             if pvn_bms and vip['ip_addr,fip']:
                build_traffic_commands(transform_to_bms(traffic_command, pvn_bms['vlan']),\
                                       client_traffic_commands,\
                                       src=pvn_bms['ip_addr,mgmt'],\
                                       dst=fqdn(tenant, fip_to_name(vip['ip_addr,fip']), pvn_bms))
                if 'SNAT' in vnet:
                   src_code.append((pvn_bms['ip_addr,mgmt'],pvn_bms['vlan'], 'BMS', 'PSVN'))
                else:
                   src_code.append((pvn_bms['ip_addr,mgmt'],pvn_bms['vlan'], 'BMS', 'PVN'))

    update_ping_code(src_code, dst_code)

def build_ping_lb_ext(tenant, vn, vns, traffic_command, client_traffic_commands, vip, ex_srv_ip):

    build_ping_lb(tenant, vn, vns, traffic_command, client_traffic_commands, vip)
    build_traffic_commands(traffic_command, client_traffic_commands,\
			   src=ex_srv_ip, dst=vip['ip_addr,fip'])
    src_code = [(ex_srv_ip, None, 'Ext', 'Ext')]
    dst_code = [('VIP', 'VipVN', 'FIP')]
    update_ping_code(src_code, dst_code)

def build_ping_bms_fip_gwvn(tenant, vn, vns, traffic_command, client_traffic_commands,\
                                vm, ex_srv_ip):

    dst_code = []
    if 'FIP' in vn:
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'BMS', 'PubFIP')]
    else:
       src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'BMS', 'SnatGW')]
      
    traffic_command = transform_to_bms(traffic_command, vm['vlan'])

    
    if ex_srv_ip:
       build_traffic_commands(traffic_command, client_traffic_commands,\
                            src=vm['ip_addr,mgmt'], dst=ex_srv_ip)
       dst_code.append(('Ext', 'Ext', 'None'))

    if len(vns) > 30:
       vn_list = []

       for vnet in vns:
          if is_attach_fip(vns[vnet]):
             vn_list.append(vnet)

       random_vn = random.choice(vn_list)

       random_vm = get_one_vm_from_vn(vns[random_vn])
       if random_vm:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'],\
                                 dst=fqdn(tenant, fip_to_name(\
                                 random_vm['ip_addr,fip']), vm))
          if 'VIP' in random_vn:
             dst_code.append(('VIP', 'VipVN', 'FIP'))
          else:
             dst_code.append(('VM', 'PVN', 'FIP'))

       random_bms = get_one_bms_from_vn(vns[random_vn], vm)
       if random_bms:
          build_traffic_commands(traffic_command,\
                                 client_traffic_commands,\
                                 src=vm['ip_addr,mgmt'],\
                                 dst=random_bms['ip_addr,fip'])
          dst_code.append(('BMS', 'PVN', 'FIP'))


       update_ping_code(src_code, dst_code)

       return

    for vnet in vns:
       if is_attach_fip(vns[vnet]):
          '''
          pvn_vm = get_one_vm_from_vn(vns[vnet])
          if pvn_vm:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=fqdn(tenant, fip_to_name(\
                                           pvn_vm['ip_addr,fip']), vm))
             if 'VIP' in vnet: 
                dst_code.append(('VIP', 'VipVN', 'FIP'))
             else:
                dst_code.append(('VM', 'PVN', 'FIP'))
          '''
          pvn_bms = get_one_bms_from_vn(vns[vnet], vm)
          if pvn_bms:
             build_traffic_commands(traffic_command,\
                                    client_traffic_commands,\
                                    src=vm['ip_addr,mgmt'],\
                                    dst=pvn_bms['ip_addr,fip'])
             dst_code.append(('BMS', 'PVN', 'FIP'))
          
    update_ping_code(src_code, dst_code)

def build_ping_service_chain(tenant, vn_pair, left_vms, right_vms,\
                             traffic_command_v4,traffic_command_v6, client_traffic_commands):
 
    src_code = []
    dst_code = []

    code_temp = vn_pair[0].split(':')[-1].split('.')
    code_tenant = code_temp[0]
    code_vn = code_temp[2].split('_')[-1]
    code_final = code_tenant + '_' + code_vn

    for traffic_command in [traffic_command_v4,traffic_command_v6]:
        if traffic_command is None:
           continue
        for left_vm, right_vm in zip(left_vms,right_vms):
           if left_vm['is_bms']:
              traffic_command = transform_to_bms(traffic_command, left_vm['vlan'])
              src_code = [(left_vm['ip_addr,mgmt'], left_vm['vlan'], 'VM', 'PVN')]
              src_code.append((left_vm['ip_addr,mgmt'], left_vm['vlan'], 'SC_BMS', code_final))
           else:
              src_code.append((left_vm['ip_addr,mgmt'], left_vm['vlan'], 'SC_VM', code_final))
           if right_vm['is_bms']:
              dst=right_vm['ip_addr,data']
              dst_code.append(('SC', 'BMS', 'Right'))
           else:
              dst=fqdn(tenant, right_vm['name'], left_vm)
              dst_code.append(('SC', 'VM', 'Right')) 

           build_traffic_commands(traffic_command, client_traffic_commands,\
                                  src=left_vm['ip_addr,mgmt'],\
                                  dst=dst) 

    update_ping_code(src_code, dst_code)
        

def build_file_commands(file_str, remote_file_commands, src):
   if file_str:
      if (src, file_str) not in remote_file_commands:
         remote_file_commands.append((src, file_str))
   else:
      return

def build_traffic_commands(traffic_command,\
                           client_traffic_commands,\
                           src="", dst="", port=""):

   if traffic_command:
     try:
      if "killall" in traffic_command:
         temp = ' '.join(traffic_command)
         client_traffic_commands.append((src,temp))
      elif "ping" in traffic_command or "ping6" in traffic_command:
         traffic_command.append(dst)
         if traffic_command[5] is None:
            return
         print "traffic:",traffic_command
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
      elif "http_load" in traffic_command:
         traffic_command.extend(["&"])
         temp = ' '.join(traffic_command)
         if (src,temp) not in client_traffic_commands:
            client_traffic_commands.append((src,temp))
         del traffic_command[-1:]
      else:
         temp = ' '.join(traffic_command)
         if (src,temp) not in client_traffic_commands:
            client_traffic_commands.append((src,temp))
     except:
        import traceback;traceback.print_exc(sys.stdout)
        import pdb;pdb.set_trace()
   else:
      return

def check_vn_prop(test, tenant, vn):
   
   tenant_num = re.search('Tenant\d+', tenant)
   vn_name = tenant_num.group(0).lower()+'.test_id1.'+vn
   vn_info = retrieve_vn_conf(test.tenant_conf['tenant,vn_group_list'], vn_name)
   print "vn_info:",vn_info,tenant,vn
   if vn_info:
      traffic_command_v4 = None
      traffic_command_v6 = None
      fip_attached = vn_info['attach_fip']
      if vn_info['ipv6_cidr']:
         traffic_command_v6 = test.traffic_conf['ping6']
      if vn_info['ipv4_cidr']:
         traffic_command_v4 = test.traffic_conf['ping']
      if traffic_command_v6 is None and traffic_command_v4 is None:
         traffic_command_v4 = test.traffic_conf['ping']
      return fip_attached, traffic_command_v4,traffic_command_v6
   else:
      return False, [] ,[]

def ping_check_pass_thru_all(test,tenants,sc_info,filename="ping_result_pass_thru.txt"):
   traffic_command = test.traffic_conf['ping']
   print 'starting build: ', time.time()
   client_traffic_commands = []
   vms_list = []
   for tenant in tenants:
      for vn in tenants[tenant]:
          for vm in tenants[tenant][vn]:
              vms_list.append(vm)

   for i,vm in enumerate(vms_list):
       if i == 0:
          from_ip = vm['ip_addr,mgmt']
          continue
       client_traffic_commands.append((from_ip,'ping -c 3 -W 3 ' + vm['ip_addr,data']))
       
   ping_commands = '' 
   for i in client_traffic_commands:
      ping_commands += str(i) + '\n'

   fp = open("ping_commands.txt", 'w')
   fp.write(ping_commands)
   fp.close() 

   print time.time()
   client_results = exec_remote_commands(client_traffic_commands, [], 1800)
   print time.time()
   status = process_and_write_ping_results(test, client_results, filename)
   return status


def ping_check_setup(test, tenants, sc_info, filename = "ping_result.txt"):
   traffic_command = test.traffic_conf['ping']
   client_traffic_commands = []
   ex_srv_ip = test.traffic_conf['external_server_ip']
   print 'starting build: ', time.time()
   for tenant in tenants:
      for vn in tenants[tenant]:
         fip_attached, traffic_command_v4,traffic_command_v6 = check_vn_prop(test, tenant, vn)
         
         #if 'VSRX_BGP' in vn:
         if 'BGP_Addnl' in vn:
            for vm in tenants[tenant][vn]:
               if vm['ip_addr,data'] == '1.3.0.4':
                  build_bgpaas_ping(vm,\
                                    traffic_command_v4,traffic_command_v6,\
                                    client_traffic_commands)
                  #build_traffic_commands(traffic_command,\
                  #                       client_traffic_commands,\
                  #                       src=vm['ip_addr,mgmt'],\
                  #                       dst=ipv4)
                  #build_traffic_commands(traffic_command_v6, client_traffic_commands, src=vm['ip_addr,mgmt'], dst=ipv6_1)
                  #build_traffic_commands(traffic_command_v6, client_traffic_commands, src=vm['ip_addr,mgmt'], dst=ipv6_2)
         for traffic_command in [traffic_command_v4,traffic_command_v6]:
             if traffic_command is None:
                continue
             if (('Private_VN' in vn) and fip_attached and ex_srv_ip):
                for vm in tenants[tenant][vn]:
                   build_ping_pvn_fip_ext(tenant, vn, tenants[tenant],\
                                          traffic_command,\
                                          client_traffic_commands, vm, ex_srv_ip)
             elif 'Private_VN' in vn and fip_attached:
                for vm in tenants[tenant][vn]:
                   build_ping_pvn_fip(tenant, vn, tenants[tenant],\
                                      traffic_command,\
                                      client_traffic_commands, vm)
             elif 'Private_VN' in vn:
                for vm in tenants[tenant][vn]:
                   build_ping_pvn(tenant, vn, tenants[tenant], traffic_command,\
                                      client_traffic_commands, vm)
             elif 'Private_SNAT_VN' in vn and ex_srv_ip:
                for vm in tenants[tenant][vn]:
                   build_ping_psvn_ext(tenant, vn, tenants[tenant], traffic_command,\
                                       client_traffic_commands, vm, ex_srv_ip)
             elif 'Private_SNAT_VN' in vn:
                for vm in tenants[tenant][vn]:
                   build_ping_psvn(tenant, vn, tenants[tenant], traffic_command,\
                                       client_traffic_commands, vm)
             elif 'Private_LB_VIP' in vn and ex_srv_ip:
                for vip in tenants[tenant][vn]:
                   build_ping_lb_ext(tenant, vn, tenants[tenant], traffic_command,\
                                             client_traffic_commands, vip, ex_srv_ip)
             elif 'Private_LB_VIP' in vn:
                for vip in tenants[tenant][vn]:
                   build_ping_lb(tenant, vn, tenants[tenant], traffic_command,\
                                 client_traffic_commands, vip)
             elif ('Public_FIP' in vn):
                for vm in tenants[tenant][vn]:
                   if vm['is_bms']:
                      build_ping_bms_fip_gwvn(tenant, vn, tenants[tenant],\
                                 transform_to_bms(traffic_command, vm['vlan']),\
                                 client_traffic_commands, vm, ex_srv_ip)
             else:
                continue

   for tenant in sc_info:
      for vn_pair in sc_info[tenant]:
         if vn_pair == 'service-instances':
            continue
         left_vms, right_vms = sc_info[tenant][vn_pair]
         vn = str(vn_pair[0].split(':')[2].split('.')[2])
         fip_attached, traffic_command_v4,traffic_command_v6 = check_vn_prop(test, tenant, vn)
         build_ping_service_chain(tenant, vn_pair, left_vms, right_vms, traffic_command_v4,traffic_command_v6, client_traffic_commands)

   print 'done building: ', time.time()

   ping_commands = '' 
   for i in client_traffic_commands:
      ping_commands += str(i) + '\n'

   fp = open('ping_commands.txt', 'w')
   fp.write(ping_commands)
   fp.close() 

   print time.time()
   client_results = exec_remote_commands(client_traffic_commands, [], 1800)
   print time.time()
   status = process_and_write_ping_results(test, client_results, filename)
   return status

def build_bgpaas_ping(vm, traffic_command_v4,traffic_command_v6, client_traffic_commands):

   #loop_ip = '9.0.'
   #last_oct = '.1'
   #ipv4 = random.choice([loop_ip+str(i)+last_oct for i in range(1,10)])
   ipv4 = '3.1.1.5'
   ipv6_1 = '2001:0db8:0:f101::1'
   ipv6_2 = '2001:0db8:0:f102::1'

   #traffic_command_v6 = ["ping6", "-c", "3", "-W", "3"] 

   src_code = []
   dst_code = []

   if traffic_command_v4:
      build_traffic_commands(traffic_command_v4, client_traffic_commands, src=vm['ip_addr,mgmt'], dst=ipv4)

   src_code = [(vm['ip_addr,mgmt'], vm['vlan'], 'VM', 'BGPaaS')]
   dst_code = [('Loopback', 'BGPaaS', 'None')]

   update_ping_code(src_code, dst_code)
 
   build_traffic_commands(traffic_command_v6, client_traffic_commands, src=vm['ip_addr,mgmt'], dst=ipv6_1)
   update_ping_code(src_code, dst_code)
   build_traffic_commands(traffic_command_v6, client_traffic_commands, src=vm['ip_addr,mgmt'], dst=ipv6_2)
   update_ping_code(src_code, dst_code)


def process_and_write_ping_results(test, results, filename):
    unknown_re = re.compile(r'^ping: unknown host (.*)$')
    name_re = re.compile(r'^(PING .+) \(([\d.]+)\) .+ data.$')
    reverse_name_re = re.compile(r'^.+ from ([\w\d.]+):* .+$')
    info_re = re.compile(r'^.+ (\d+)% .+$')
    stats_re = re.compile(r'^rtt min/avg/max/mdev = ([\d.]+)/'r'([\d.]+)/([\d.]+)/[\d.]+ ms$')
    global_result = 1 
    res_str = []
    bms_mgmt_ips = []
    ex_srv_ip = test.traffic_conf['external_server_ip']

    for tor in test.global_conf['pr_qfx']:
       for bms in tor['bms']:
          bms_mgmt_ips.append(bms['physical_server_mgmt_ip'])

    for client in results:
        for result in client['results']:
            netns = re.search(r'exec (\d+)', result['command'][0])
            ping6 = re.search(r'ping6', result['command'][0])
            try:
              if netns:
                  res_str.append(ping_code_str(client['address'], int(netns.group(1))))
              else:
                  res_str.append(ping_code_str(client['address'], None))
            except:
              pass
            res_str.append(client['address'])
            if netns:
                res_str.append(netns.group(1))
            output = result['output']
            error = result['error']
            flag = 'pass'
            match = None
            match1 = unknown_re.match(error)
            if match1:
                res_str.append('vDNS Failed. Unknown host: ' + match1.group(1))
                flag = 'fail'
                global_result = 0
            for line in output.splitlines():
                match = name_re.match(line)
                if match:
                    res_str.append(match.group(1))
                    res_str.append(match.group(2))
                match = reverse_name_re.match(line)
                if match:
                    if (re.search(r'data.soln.com', result['command'][0]) and 'vm' not in match.group(1)):
                    #if ('vm' not in match.group(1) and (ex_srv_ip != match.group(1)\
                    #                               and client['address'] != ex_srv_ip\
                    #                               and client['address'] not in bms_mgmt_ips)):
                       flag = 'fail'
                       global_result = 0 
                       res_str.append('RR Failed')
                match = info_re.match(line)
                if match:
                    if int(match.group(1)) == 100:
                        flag = 'fail'
                        global_result = 0 
                    res_str.append(match.group(1)+"% Loss")
                match = stats_re.match(line)
                if match:
                    res_str.append(match.group())
                    min_time, avg_time, max_time = map(float, match.groups())
                    #if avg_time > 50.0:
                    #    flag  = 'fail'
                    #    global_result = 0 
            if flag == 'pass' and output:
                res_str.append('PASS\n')
            else:
                res_str.append('FAIL\n')
    fp = open(filename, 'a')
    fp.write(' '.join(res_str))
    fp.close()
    #fp = open('raw_res.txt', 'a')
    #fp.write(str(results))
    #fp.close()
    return global_result


def compute_c_s_p_tuple(test, tenant_index, pvn_vm_list = [], psvn_vm_list = [], fip_vm_list = []):
   ex_srv_ip = test.traffic_conf['external_server_ip']
   src_vm_list = []
   dst_vm_list = get_vm_only(fip_vm_list)
   src_vm_list.extend(pvn_vm_list)
   src_vm_list.extend(psvn_vm_list)
   c_s_p_list = []
   port_start = 'pvn_ext_port_start'
      
   if ex_srv_ip:
      first_server_port = test.traffic_conf[port_start] + tenant_index*300
      last_server_port = first_server_port + len(src_vm_list)
      c_s_p_list = zip(src_vm_list, [ex_srv_ip]*len(src_vm_list), xrange(first_server_port,last_server_port))
   else:
      num_of_dst_vms = len(dst_vm_list)
      if num_of_dst_vms:
         num_ports_per_vm,r = divmod(len(src_vm_list),num_of_dst_vms)
         if r:
            num_ports_per_vm += 1
         first_server_port = test.traffic_conf[port_start]
         last_server_port = first_server_port + num_ports_per_vm
         for i,j in zip(src_vm_list, itertools.product(dst_vm_list, xrange(first_server_port,last_server_port))):
            n = (i,)+j
            c_s_p_list.append(n)
   return c_s_p_list


def handle_pvn_psvn_traffic(test, pvn_vm_list, psvn_vm_list, fip_vm_list, tenant_index):
   pvn_fip = is_attach_fip_vn_type(test, 'Private_VN')
   pvn_c_s_list = []
   c_s_list = []
   if not pvn_fip:
      grp_list = grouper(2, pvn_vm_list)
      p = int(test.traffic_conf['pvn_ext_port_start']) - 1 
      for i in grp_list:
         j = i + (p,)
         pvn_c_s_list.append(j)
   if pvn_fip and psvn_vm_list: 
      c_s_list = compute_c_s_p_tuple(test, tenant_index, pvn_vm_list = pvn_vm_list, psvn_vm_list = psvn_vm_list, fip_vm_list = fip_vm_list)
   else:
      c_s_list = compute_c_s_p_tuple(test, tenant_index, psvn_vm_list = psvn_vm_list, fip_vm_list = fip_vm_list)

   pvn_c_s_list.extend(c_s_list)
   return pvn_c_s_list
   

def handle_lbaas_traffic(test, tenant, vip_list, client_traffic_commands, remote_file_commands, pvn_vm_list = [], psvn_vm_list = [], fip_vm_list = []):
   pvn_fip = is_attach_fip_vn_type(test, 'Private_VN')
   ex_srv_ip = test.traffic_conf['external_server_ip']
   httpload_url_lbaas = "url_lb\n"
   url_lb_file = '/opt/contrail/tools/http/httpload/url_lb'
   run = '/opt/contrail/zmq/run'
   vm_list = []

   for vip in vip_list:
      if ex_srv_ip:
         httpload_url_lbaas += 'http://'+vip['ip_addr,fip']+':'+str(vip['vip,protocol_port'])+'/512kb\n'
      else:
         print "vip['ip_addr,fip']:",vip['ip_addr,fip']
         print "vip['vip,protocol_port']:",vip['vip,protocol_port']
         httpload_url_lbaas += 'http://'+fip_to_name(vip['ip_addr,fip'])+':'+str(vip['vip,protocol_port'])+'/512kb\n'
      
   computed_run = str(int(test.traffic_conf['duration']) // int(test.traffic_conf['sampling_interval']))

   if ex_srv_ip:
      computed_lbaas_rate = int(test.traffic_conf['httpload_lb'][2])*len(vip_list)
      computed_lbaas_command = [run, computed_run, 'http_load', '-rate', str(computed_lbaas_rate), '-fetches',\
                                str(computed_lbaas_rate * int(test.traffic_conf['sampling_interval'])), url_lb_file]
      build_traffic_commands(computed_lbaas_command, client_traffic_commands, src=ex_srv_ip)
      build_file_commands(httpload_url_lbaas, remote_file_commands, src=ex_srv_ip)
   else:
      for vm in pvn_vm_list:
         if vm['ip_addr,fip']: 
            vm_list.append(vm)
      vm_list.extend(psvn_vm_list)
      vm_list.extend(fip_vm_list)
      computed_lbaas_rate = int(test.traffic_conf['httpload_lb'][2])*len(vip_list) // len(vm_list)
      for vm in vm_list:
         if not vm['is_bms']:
            computed_vm_lbaas_command = [run, computed_run, 'http_load', '-rate', str(computed_lbaas_rate), '-fetches',\
                                str(computed_lbaas_rate * int(test.traffic_conf['sampling_interval'])), url_lb_file]
            build_traffic_commands(computed_vm_lbaas_command, client_traffic_commands, src=vm['ip_addr,mgmt'])
            build_file_commands(httpload_url_lbaas, remote_file_commands, src=vm['ip_addr,mgmt'])
         else:
            httpload_url_lbaas_bms = ''
            for vip in vip_list:
               httpload_url_lbaas_bms += 'url_lb'+str(vm['vlan'])+'\n'+'http://'+fqdn(tenant,\
                                      fip_to_name(vip['ip_addr,fip']), vm)+':'+str(vip['vip,protocol_port'])+'/512kb\n'
            computed_bms_lbaas_command = [run, computed_run, 'http_load', '-rate', str(computed_lbaas_rate), '-fetches',\
                                str(computed_lbaas_rate * int(test.traffic_conf['sampling_interval'])), url_lb_file]
            build_traffic_commands(transform_to_bms(computed_bms_lbaas_command, vm['vlan']), client_traffic_commands, src=vm['ip_addr,mgmt'])
            build_file_commands(httpload_url_lbaas_bms, remote_file_commands, src=vm['ip_addr,mgmt'])


def build_kill_traffic_commands(test, tenants):
   vm_list = []
   kill_traffic_commands = []
   kill_iperf = ['killall', 'iperf3']
   kill_bash = ['killall', '/bin/bash']
   kill_httpload = ['killall', 'http_load']
   ex_srv_ip = test.traffic_conf.get('external_server_ip', None)
   kill_vn_list = ['Private_VN', 'Private_SNAT', 'Public_FIP', 'Private_SC']
   vms = {}
 
   for tenant in tenants:
      for vn in tenants[tenant]:
         if any(x in vn for x in kill_vn_list): 
            for vm in tenants[tenant][vn]:
               if vm['ip_addr,mgmt'] not in vms:
                  vms[vm['ip_addr,mgmt']] = True

   for mgmt_ip in vms:
      build_traffic_commands(kill_iperf, kill_traffic_commands, src=mgmt_ip)
      build_traffic_commands(kill_bash, kill_traffic_commands, src=mgmt_ip)
      build_traffic_commands(kill_httpload, kill_traffic_commands, src=mgmt_ip)

   if ex_srv_ip:
      build_traffic_commands(kill_iperf, kill_traffic_commands, src=ex_srv_ip)
      build_traffic_commands(kill_bash, kill_traffic_commands, src=ex_srv_ip)
      build_traffic_commands(kill_httpload, kill_traffic_commands, src=ex_srv_ip)

   kill_result = exec_remote_kill(kill_traffic_commands, [], 120)

 
def run_traffic(test, tenants, sc_info, filename = ""):

   client_traffic_commands = []
   remote_file_commands = []
   server_traffic_commands = []

   computed_run = str(int(test.traffic_conf['duration']) // int(test.traffic_conf['sampling_interval']))

   ex_srv_ip = test.traffic_conf.get('external_server_ip', None)
  
   if test.global_conf.get('lls,name', None):
      lls_urls = ""
      lls_obj = LLS(None)
      lls_list = lls_obj.retrieve_existing_services(conn_obj_list=test.admin_conn_obj_list)
      for lls in lls_list:
         if lls[0] != 'metadata':
            lls_urls += "http://"+lls[0]+':'+str(lls[2])+"/256kb\n"

   for tenant in tenants:
      tenant_index = re.search('(\d+)$',tenant).group(1)
      pvn_vm_list = []
      psvn_vm_list= []
      fip_vm_list = []
      ip_list    = []
      c_s_p_list = []
      vip_list = []

      for vn in tenants[tenant]:
         if 'Private_VN' in vn:
            pvn_vm_list.extend(tenants[tenant][vn])
         if 'Private_SNAT_VN' in vn:
            psvn_vm_list.extend(tenants[tenant][vn])
         if 'Public_FIP' in vn:
            fip_vm_list.extend(tenants[tenant][vn])
         if 'VIP' in vn:
            vip_list.extend(tenants[tenant][vn])

      c_s_p_list = handle_pvn_psvn_traffic(test, pvn_vm_list, psvn_vm_list, fip_vm_list, tenant_index)
      if vip_list:
         handle_lbaas_traffic(test, tenant, vip_list, client_traffic_commands, remote_file_commands,\
                              pvn_vm_list, psvn_vm_list, fip_vm_list)

      for vn_pair in sc_info[tenant]:
         if vn_pair == 'service-instances':
            continue
         left_vms, right_vms = sc_info[tenant][vn_pair]
         port = [100]*len(left_vms)
         sc_c_s_p_list = zip(left_vms, right_vms, port)
         c_s_p_list.extend(sc_c_s_p_list)

      for c,s,p in c_s_p_list:
         #pvn without fip, grouper will return none server when vm count is odd.
         #ignore the last vm in such a case.
         if c and s: 
               if c['is_bms']:
                  ctc_iperf3 = transform_to_bms(test.traffic_conf['c_iperf3'], c['vlan'])
                  ctc_udp_ucast = transform_to_bms(transform_to_run(test.traffic_conf['c_udp_ucast'], computed_run), c['vlan'])
                  ctc_httpload_short = transform_to_bms(test.traffic_conf['httpload_short'], c['vlan'])
                  ctc_httpload_lls = []
                  cfc_lls_url = ""
                  httpload_short_file = 'url_short'+ str(c['vlan']) + '\n'
                  src_mgmt = c['ip_addr,mgmt']
               else:
                  ctc_iperf3 = test.traffic_conf['c_iperf3']
                  ctc_udp_ucast = transform_to_run(test.traffic_conf['c_udp_ucast'], computed_run)
                  ctc_httpload_short = test.traffic_conf['httpload_short']
                  ctc_httpload_lls = test.traffic_conf['httpload_lls']
                  cfc_lls_url = lls_urls 
                  httpload_short_file = "url_short\n" 
                  src_mgmt = c['ip_addr,mgmt']
               if s == ex_srv_ip:
                  stc_iperf3 = test.traffic_conf['s_iperf3']
                  stc_udp_ucast = test.traffic_conf['s_udp_ucast']
                  stc_httpload_lls = []
                  sfc_lls_url = "" 
                  dst_data = s
                  dst_mgmt = s
               elif s['is_bms']:
                  stc_iperf3 = transform_to_bms(test.traffic_conf['s_iperf3'], s['vlan'])
                  stc_udp_ucast = transform_to_bms(test.traffic_conf['s_udp_ucast'], s['vlan'])
                  stc_httpload_lls = []
                  sfc_lls_url = "" 
                  dst_data = s['ip_addr,data']
                  dst_mgmt = s['ip_addr,mgmt']
               else:
                  stc_iperf3 = test.traffic_conf['s_iperf3']
                  stc_udp_ucast = test.traffic_conf['s_udp_ucast']
                  stc_httpload_lls = test.traffic_conf['httpload_lls']
                  sfc_lls_url = lls_urls 
                  if not c['is_bms']:
                     dst_data = s['name']
                  else:
 		     dst_data = fqdn(tenant, s['name'], c)
                  dst_mgmt = s['ip_addr,mgmt']

               build_traffic_commands(ctc_iperf3, client_traffic_commands, src=src_mgmt, dst=dst_data, port=p)
               build_traffic_commands(stc_iperf3, server_traffic_commands, src=dst_mgmt, port=p)
               build_traffic_commands(ctc_udp_ucast, client_traffic_commands, src=src_mgmt, dst=dst_data, port=p+2000)
               build_traffic_commands(stc_udp_ucast, server_traffic_commands, src=dst_mgmt, port=p+2000)

               build_traffic_commands(ctc_httpload_short, client_traffic_commands, src=src_mgmt, port=p)
               build_traffic_commands(ctc_httpload_lls, client_traffic_commands, src=src_mgmt, port=p)
               build_traffic_commands(stc_httpload_lls, client_traffic_commands, src=dst_mgmt, port=p)

	       build_file_commands(cfc_lls_url, remote_file_commands, src_mgmt)
               build_file_commands(sfc_lls_url, remote_file_commands, dst_mgmt)
               
               httpload_url_short = httpload_short_file + 'http://'+dst_data+'/1mb\n'
               build_file_commands(httpload_url_short, remote_file_commands, src_mgmt)
   file_result = exec_send_file(remote_file_commands, [], 180)
   server_result = exec_remote_commands(server_traffic_commands, [], 60)
   print time.time()

   full_traff_commands = ''
   for i in client_traffic_commands:
      full_traff_commands += str(i) + '\n'

   for i in server_traffic_commands:
      full_traff_commands += str(i) + '\n'

   print "full_traff_commands:",full_traff_commands
   fp = open('full_traff_commands.txt', 'w')
   fp.write(full_traff_commands)
   fp.close()


   q = Queue.Queue()
   print exec_remote_commands,client_traffic_commands,test.traffic_conf
   threading.Thread(target=exec_remote_commands, args=(client_traffic_commands, [], int(test.traffic_conf['duration'])+1200, q)).start()
   print "INFO: started traffic threads..sleeping for %ds"%(int(test.traffic_conf['duration'])+60)
   sys.stdout.flush()
   time.sleep(int(test.traffic_conf['duration'])+60)
   kill_result = build_kill_traffic_commands(test, tenants)

   print 'traffic run: ', time.time()
   #process_client_results(q.get())
   print 'final stats in: res.csv'

def get_httpload_type(command):
   url = re.search(r'url_([a-z]+)', command) 
   if url:
      return url.group(1)

def process_client_results(client_results):

   iperf3 = {}
   iperf3_udp = {}
   httpload_short = {}
   httpload_lb = {}
   httpload_lls = {}
   for client in client_results:
      for result in client['results']:
         if 'iperf3' in result['command'][0] and "-u" not in result['command'][0]:
            iperf3_stats_handler(iperf3, result['output'], client['address'], result['command'][0])
         elif 'iperf3' in result['command'][0]:
            iperf3_udp_stats_handler(iperf3_udp, result['output'], client['address'], result['command'][0])
         elif 'http_load' in result['command'][0]:
            if 1:
               #if not result['error']:
               http_type = get_httpload_type(result['command'][0])
               if http_type == 'lls':
                  httpload_stats_handler(httpload_lls, result['output'], client['address'], result['command'], result['error'])
               elif http_type == 'lb':
                  httpload_stats_handler(httpload_lb, result['output'], client['address'], result['command'], result['error'])
               elif http_type == 'short':
                  httpload_stats_handler(httpload_short, result['output'], client['address'], result['command'], result['error'])
               else:
                  print 'error'
            else:
               httpload_error_handler(result['error'])


   fp = open('res.csv.txt', 'ab')
   writer = csv.writer(fp, dialect = 'excel')
   '''
   title = ['TCP_Throughput_Success', 'TCP_Retrans', 'TCP_Throughput_Fail',\
            'UDP_Throughput_Success', 'UDP_Throughput_Failure',\
            'S_Fetches', 'S_Success', 'S_Failures', 'S_Rate', 'S_min', 'S_max', 'S_mean',\
            'LL_Fetches', 'LL_Success', 'LL_Failures', 'LL_Rate', 'LL_min', 'LL_max', 'LL_mean',\
            'LB_Fetches', 'LB_Success', 'LB_Failures', 'LB_Rate', 'LB_min', 'LB_max', 'LB_mean']
   writer.writerow(title)
   '''

   if not iperf3.get('total',None) and \
      not iperf3_udp.get('total',None) and \
      not httpload_short.get('total',None) and \
      not httpload_lls.get('total',None) and \
      not httpload_lb.get('total',None):
      print 'no results to show'
      return

   if not iperf3.get('total',None):
      for item in [httpload_short, httpload_lls, httpload_lb]:
         if item.get('total',None):
            iperf3['total'] = [(0,)*3]*len(item['total'])
            break

   if not iperf3_udp.get('total',None):
      for item in [httpload_short, httpload_lls, httpload_lb]:
         if item.get('total',None):
            iperf3_udp['total'] = [(0,)*3]*len(item['total'])
            break

   for item in [httpload_short, httpload_lls, httpload_lb]:
      if not item.get('total',None):
         item['total'] = [(0,)*7]*len(iperf3['total'])


   for row in zip(iperf3['total'], iperf3_udp['total'], httpload_short['total'], httpload_lls['total'], httpload_lb['total']):
      row_tup = row[0]+row[1]+row[2]+row[3]+row[4]
      writer.writerow(row_tup)
   fp.close()


   if iperf3:
      write_full_results(iperf3, 'iperf')
   if iperf3_udp:
      write_full_results(iperf3_udp, 'iperf_udp')
   if httpload_short:
      write_full_results(httpload_short, 'http_short')
   if httpload_lls:
      write_full_results(httpload_lls, 'http_lls')
   if httpload_lb:
      write_full_results(httpload_lb, 'http_lb')

def write_full_results(res, fn):

   output_res = ''
   for k in res:
      output_res += str(k) + ':' + '\n'
      output_res += '\t' + str(res[k]) + '\n'
   fp = open('full_'+fn+'.txt', 'a')
   fp.write(output_res)
   fp.close()

def write_results_csv(output):
   fp = open('res.csv', 'ab')
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

def iperf3_udp_stats_handler(iperf3_udp, output, address, command):

   run_count_re = re.search(r'run ([\d]+)', command)
   options_re = re.search(r'-P ([\d]+) -b ([\d]+)[\w]+ -i ([\d]+) -t ([\d]+) -c ([\w\d.]+)', command)
   vm_stats = []
   total_vm_stats = []

   #run_count = int(run_count_re.group(1))
   #n = len(output)/run_count
   #json_list = [output[i:i+n] for i in range(0, len(output), n)]

   json_list = output.split('}\n{')
   for i,j in enumerate(json_list):
      if i == 0:
         json_list[i] += '}'
      elif i == len(json_list) - 1:
         json_list[i] = '{' + json_list[i]
      else:
         json_list[i] = '{'+json_list[i]+'}'

   start = 1

   for json_stat in json_list:

      try:
         output = json.loads(json_stat)
      except ValueError:
         continue

      if output.get('error', None):
         if start:
            local_host = address
            remote_host = options_re.group(5)
         mbps_fail = int(options_re.group(2))*int(options_re.group(1)) 
         vm_stats.append((0, mbps_fail))
      else:
         if start:
            local_host = output['start']['connected'][0]['local_host']
            remote_host = output['start']['connected'][0]['remote_host']
            start = 0
         for index,sample in enumerate(output['intervals']):
            mbps_success = float('{0:.2f}'.format(sample['sum']['bits_per_second'] / 1000000.0))
            mbps_fail = float('{0:.2f}'.format(int(options_re.group(2))*int(options_re.group(1)) - mbps_success))
            vm_stats.append((mbps_success, mbps_fail))
     
   iperf3_udp[local_host,remote_host] = vm_stats
   if not iperf3_udp.get('total',0):
      iperf3_udp['total'] = vm_stats
   else:
      for x,y in zip(iperf3_udp['total'], vm_stats):
         mbps_success_tot = float('{0:.2f}'.format(x[0] + y[0]))
         mbps_fail_tot = float('{0:.2f}'.format(x[1] + y[1]))
         total_vm_stats.append((mbps_success_tot, mbps_fail_tot))
      iperf3_udp['total'] = total_vm_stats


def iperf3_stats_handler(iperf3, output, address, command):

   options_re = re.search(r'-b ([\d]+)[\w]+ -i ([\d]+) -t ([\d]+) -c ([\w\d.]+)', command)
   vm_stats = []
   total_vm_stats = []
   
   output = json.loads(output)
  
   if output.get('error', None):
      local_host = address
      if options_re:
         mbps_fail = int(options_re.group(1))
         samples = int(options_re.group(3)) / int(options_re.group(2))
         remote_host = options_re.group(4)
      for i in xrange(samples):
         vm_stats.append((0, 0, mbps_fail))
   else:
      local_host = output['start']['connected'][0]['local_host']
      remote_host = output['start']['connected'][0]['remote_host']
      for index,sample in enumerate(output['intervals']):
         mbps_success = float('{0:.2f}'.format(float(sample['sum']['bits_per_second'] / 1000000.0)))
         retrans =  int(sample['sum']['retransmits'])
         mbps_fail = 0
         vm_stats.append((mbps_success, retrans, mbps_fail))

   iperf3[local_host,remote_host] = vm_stats
   if not iperf3.get('total',0):
      iperf3['total'] = vm_stats 
   else:
      for x,y in zip(iperf3['total'], vm_stats):
         mbps_success_tot = float('{0:.2f}'.format(x[0] + y[0]))
         retrans_tot = float('{0:.2f}'.format(x[1] + y[1]))
         mbps_fail_tot = float('{0:.2f}'.format(x[2] + y[2]))
         total_vm_stats.append((mbps_success_tot,retrans_tot, mbps_fail_tot))
      iperf3['total'] = total_vm_stats

def httpload_stats_handler(httpload_result, output, address, command, output_error):

   line1_re = re.compile(r'^([\d.]+) fetches.*in ([\d.]+) seconds$') 
   line2_re = re.compile(r'^msecs/connect: ([\d.]+) mean, ([\d.]+) max, ([\d.]+) min$')
   line3_re = re.compile(r'^msecs/first-response: ([\d.]+) mean, ([\d.]+) max, ([\d.]+) min$')
   line5_re = re.compile(r'^.*code 200 -- ([\d]+)$')
   line4_re = re.compile(r'^HTTP response codes:$')
   http_bms = re.search(r'exec (\d+)', command[0])
   rate_match = re.search(r'-rate (\d+)', command[0])
   fetches_match = re.search(r'-fetches (\d+)', command[0])
   loop_count_match = re.search(r'run (\d+)', command[0])
   rate = int(rate_match.group(1))
   tot_fetches = int(fetches_match.group(1))
   loop_count = int(loop_count_match.group(1))
   total_result = []
   http_temp = []

   
   if http_bms:
      netns = http_bms.group(1)
   else:
      netns = None


   if output_error:
      code_200 = 0
      failures = tot_fetches
      conn_min, conn_max, conn_mean = 0,0,0
      temp = [(tot_fetches, code_200, failures, rate, conn_min, conn_max, conn_mean)]*loop_count
      httpload_result[(address,netns)] = temp
   else: 
      output_split = output.splitlines()
      for idx, line in enumerate(output_split):
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
            if idx < len(output_split) - 1:
               code_match = line5_re.match(output_split[idx+1])
               if code_match:
                  code_200 = int(code_match.group(1))
                  failures = tot_fetches - code_200
               else:
                  code_200 = 0
                  failures = tot_fetches
                  conn_min = conn_max = conn_mean = 0
            else:
               code_200 = 0
               failures = tot_fetches
               conn_min = conn_max = conn_mean = 0
            temp = (tot_fetches, code_200, failures, rate, conn_min, conn_max, conn_mean)
            if not httpload_result.get((address, netns), None):
               httpload_result[(address,netns)] = [temp]
            else:
               httpload_result[(address,netns)].append(temp)
   if not httpload_result.get('total', None):
         httpload_result['total'] = httpload_result[(address, netns)]
   else:
      for x in zip(httpload_result['total'], httpload_result[(address, netns)]):
         for i in xrange(0,7):
            if i == 4:
               try:
                  z = min(x[0][i],x[1][i])
               except IndexError:
                  continue 
            elif i == 5:
               try:
                  z = max(x[0][i],x[1][i])
               except IndexError:
                  continue 
            elif i == 6:
               try: 
                  z = float('{0:.2f}'.format(((x[0][i] * (len(httpload_result)-2)) + x[1][i])/(len(httpload_result)-1)))
               except IndexError:
                  continue 
            else:
               z = float('{0:.2f}'.format(x[0][i] + x[1][i]))
            total_result.append(z)
         http_temp.append(tuple(total_result))
         total_result = []
      httpload_result['total'] = http_temp[:]
      http_temp = []
     
def httpload_error_handler(error):
   return
