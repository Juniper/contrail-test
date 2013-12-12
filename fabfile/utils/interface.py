import os
from netaddr import *

from fabric.api import *

from fabfile.config import testbed
from fabfile.utils.host import hstr_to_ip
from fabric.exceptions import CommandTimeout

@task
def copy_dir(dir_name, tgt_host):
    user_home = os.path.expanduser('~')
    remote_dir = "~/%s" % dir_name.replace(user_home,'')
    for elem in os.listdir(dir_name):
        if elem.startswith('.git'):
            continue
        with settings(host_string=tgt_host):
            run('mkdir -p ~/%s' % dir_name.replace(user_home,''))
            put(os.path.join(dir_name, elem), remote_dir)

def get_data_ip(host_str,section='data'):
    tgt_ip = None
    tgt_gw= None
    if section == 'data':
        data_ip_info = getattr(testbed, 'data', None)
    else:
        data_ip_info = getattr(testbed, 'control', None)
    if data_ip_info:
       if host_str in data_ip_info.keys():
           tgt_ip = str(IPNetwork(data_ip_info[host_str]['ip']).ip)
           tgt_gw = data_ip_info[host_str]['gw']
       else:
           tgt_ip = hstr_to_ip(host_str)
    else:
       tgt_ip = hstr_to_ip(host_str)

    return (tgt_ip, tgt_gw)
#end get_data_ip

def create_intf_file(tgt_host,name,member,mode, intf_ip):

    bond_status= None
    intf_mac_list= None
    (bond_status, intf_mac_list)=is_bond_present(tgt_host,name)
    # Select the bond ip 
    with settings(host_string = tgt_host):
        if intf_ip :
            bond_ip = str(IPNetwork(intf_ip).ip)
            bond_netmask = str(IPNetwork(intf_ip).netmask)
        
        for element in member:
             if bond_status:
                 hwaddr= intf_mac_list[element]
             else:
                 hwaddr= run("ifconfig %s | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'" %(element))
             filename = '/etc/sysconfig/network-scripts/' +  'ifcfg-' + element
             bkp_file_name= '/etc/contrail/' +  'bkp_ifcfg-' + element
           
             with settings(warn_only = True):
                 run("cp %s  %s" %(filename,bkp_file_name)) 
             # Create memeber intf for bonding 
             run("rm -rf %s" %(filename))
             run("echo DEVICE=%s >> %s" %(element,filename))
             run("echo MASTER=%s >> %s" %(name,filename))
             run("echo SLAVE=yes >>  %s" %(filename))
             run("echo TYPE=Ethernet >> %s" %(filename)) 
             run("echo NM_CONTROLLED=no >> %s" %(filename))
             run("echo HWADDR=%s >>  %s" %(hwaddr,filename))

        # Create bonding intf file
        filename = '/etc/sysconfig/network-scripts/' +  'ifcfg-' + name
        bkp_file_name= '/etc/contrail/' +  'bkp_ifcfg-' + name
        with settings(warn_only = True):
            run("cp %s  %s" %(filename,bkp_file_name))
        run("rm -rf %s" %(filename))
        run("echo DEVICE=%s >> %s" %(name,filename))
        run("echo ONBOOT=yes >> %s" %(filename))
        run("echo NM_CONTROLLED=no >>  %s" %(filename))
        run("echo BONDING_MASTER=yes >>  %s" %(filename))
        bond_mode="mode=" + mode
        run("echo BONDING_OPTS=%s >>  %s" %(bond_mode,filename))
        run("echo BOOTPROTO=none >>  %s" %(filename))
        if intf_ip:
            run("echo NETMASK=%s >>  %s" %(bond_netmask,filename))
            run("echo IPADDR=%s >>  %s" %(bond_ip,filename))

            # Need to check if default gateway device is part of memeber intreface.
            default_use_intf= _get_default_route_device(tgt_host)
            if default_use_intf in member: 
                # Need to configure gateway addr
                default_gw_ip=_get_default_route_gateway(tgt_host)
                run("echo GATEWAY=%s >>  %s" %(default_gw_ip,filename))
        
def is_bond_present(tgt_host,name):
    intf_mac_list={}
    bond_status=0
    count=0
    with settings(host_string = tgt_host):
        with settings(warn_only = True):
            count=run("ifconfig -a | grep -c %s" %(name))
            if int(count):
                bond_status=1
                output1= run("cat /proc/net/bonding/bond0 | grep 'Slave Interface' |awk '{print $3}'")
                output2= run("cat /proc/net/bonding/bond0 | grep 'Permanent HW addr' |awk '{print $4}'")
                intf_list= output1.split("\r\n")
                mac_list= output2.split("\r\n")
                for (intf,mac) in zip (intf_list,mac_list):
                    intf_mac_list[intf]=mac.lower()
    return (bond_status, intf_mac_list)
        

def _configure_default_route(tgt_host,name):
    with settings(host_string = tgt_host):
        # Find the default gateway 
        output=run("route -n | grep 'UG[ \t]' | awk '{print $2}'")
        netmask=run("route -n | grep 'UG[ \t]' | awk '{print $3}'")
        run("route add -net 0.0.0.0 netmask %s gw %s %s" %(netmask,output,name))

def _get_default_route_device(tgt_host):
    with settings(host_string = tgt_host):
        output=run("route -n | grep 'UG[ \t]' | awk '{print $8}'")
        return output

def _get_default_route_gateway(tgt_host):
    with settings(host_string = tgt_host):
        output=run("route -n | grep 'UG[ \t]' | awk '{print $2}'")
        return output

def restart_network_service(tgt_host):
    with settings(host_string = tgt_host):
        filename = 'restart_network'
        filepath= '/tmp/' + filename
        run("rm -rf %s" %(filepath))
        run("echo #!/bin/bash >>  %s" %(filepath))
        run("echo service network restart >>  %s" %(filepath))
        run("cd /tmp ; chmod 777 %s" %(filename))
        try:
           run("cd /tmp ; ./%s" %(filename), timeout=30)
        except CommandTimeout:
            pass

def check_intf_is_bond(tgt_host,tgt_device):
    is_bond= False
    with settings(host_string = tgt_host,warn_only = True):
        if run("cat /proc/net/bonding/%s" %(tgt_device)).succeeded:
            is_bond= True
        else:
            is_bond= False
    return is_bond

