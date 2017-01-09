import traceback
import os
import threading
import argparse
import sys
import copy
import time

import pdb
import re
from netaddr import IPNetwork
import ipaddr
from tcutils.cfgparser import parse_cfg_file
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import  yaml
from tcutils import *
from config import *

OS_USERNAME    = os.environ['OS_USERNAME']
OS_PASSWORD    = os.environ['OS_PASSWORD']
OS_TENANT_NAME = os.environ['OS_TENANT_NAME']
OS_AUTH_URL    = os.environ['OS_AUTH_URL']

import string
import random
from common.contrail_test_init import ContrailTestInit
import multiprocessing as mp
from common import log_orig as logging
from common.connections import ContrailConnections
from send_zmq import *
from traffic import *

#debug_func()
#sys.exit()

def parse_yaml_cfg_file(conf_file):
  
   fp = open(conf_file,"r")
   conf = yaml.load(fp)

   return conf
 
class Struct(object):
    def __init__(self, entries):
        self.__dict__.update(entries)

def validate_args(args):
    for key, value in args.__dict__.iteritems():
        if value == 'None':
            args.__dict__[key] = None
        if value == 'False':
            args.__dict__[key] = False
        if value == 'True':
            args.__dict__[key] = True

def update_args(ini_args, cli_args):
    for key in cli_args.keys():
        if cli_args[key]:
            ini_args[key] = cli_args[key]
    return ini_args

def parse_cli(args):

    parser = argparse.ArgumentParser(description=__doc__)
    args, remaining_argv = parser.parse_known_args(sys.argv[1:])
    print "args:",args

def delete_mgmt_vn(conn_obj_list,admin_tenant,thread_count,global_conf,tenant_conf):

    mgmt_vn_name   = global_conf['mgmt,vn_name']
    admin_tenant_fq_name = admin_tenant['fq_name']

    router_obj = RouterConfig(None)
    pr_names   = router_obj.retrieve_existing_pr(conn_obj_list=conn_obj_list)
    kwargs = {}
    kwargs['tenant']      = admin_tenant
    mgmt_vn_fq_name       = admin_tenant_fq_name + [mgmt_vn_name]
    kwargs['vn_name']     = mgmt_vn_fq_name
    kwargs['mx_list']     = pr_names
    pr_obj_list = []
    vn_obj = VN(None)
    for router_name in pr_names:
        pr_obj = vn_obj.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
        if pr_obj:
           pr_obj_list.append(pr_obj)

    vn_ids = vn_obj.get_vn_ids(conn_obj_list=conn_obj_list,tenant_list=[admin_tenant],vn_names_list=[mgmt_vn_name])
     
    mgmt_vn_fq_name_str = ":".join(mgmt_vn_fq_name)
    kwargs_list = []
    if len(pr_obj_list) != 0 and vn_ids.has_key(mgmt_vn_fq_name_str):
       kwargs = {}
       kwargs['pr_obj_list'] = pr_obj_list
       kwargs['vn_id']     = vn_ids[mgmt_vn_fq_name_str]
       kwargs_list.append(kwargs)
       kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
       vn_obj.delete_extend_to_pr(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    if vn_ids.has_key(mgmt_vn_fq_name_str):
       kwarg = {}
       kwarg['tenant']      = admin_tenant
       kwarg['vn_name']     = mgmt_vn_name
       vn_obj = VN(None)
       vn_obj.delete_vn_by_name_process(count=thread_count,conn_obj_list=[conn_obj_list[0]],**kwarg)

def create_dummy_vn(conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):

    mgmt_cidr      = global_conf['mgmt,cidr_start']
    mgmt_cidr_obj  = CIDR(mgmt_cidr)
    cidr           = mgmt_cidr_obj.get_next_cidr()

    mgmt_vn_name   = global_conf['mgmt,vn_name']

    admin_tenant               = {'fq_name':['default-domain','admin']}
    admin_tenant_fq_name       = admin_tenant['fq_name']
    conf                       = {}
    conf['ipv4_cidr_list']     = [cidr]
    conf['tenant']             = admin_tenant
    conf['vn_name']            = mgmt_vn_name
    conf['disable_gateway']    = True
    conf['shared_flag']        = False
    conf['use_fixture']        = False
    conf['external_flag']      = False

    vn_obj  = VN(None)
    vn_obj.create_vn(count=1,conn_obj_list=conn_obj_list,**conf)

def create_mgmt_vn_ipam(conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):

    if update_properties :
       return

    admin_tenant = {'fq_name':['default-domain','admin']}
    admin_tenant_fq_name = admin_tenant['fq_name']

    mgmt_vn_name   = global_conf['mgmt,vn_name']

    ipam_name_pattern = global_conf['ipam,name,pattern']
    ipam_name = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),ipam_name_pattern)
    mgmt_domain_name_pattern = global_conf['mgmt,vdns_domain_name_pattern']
    mgmt_domain_name         = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),mgmt_domain_name_pattern)
    mgmt_domain_name         = re.sub('\.','-',mgmt_domain_name)

    ipam_obj = IPAM(None)
    kwargs = {}
    kwargs['tenant']             = admin_tenant
    kwargs['ipam_name']          = ipam_name
    kwargs['domain_server_name'] = mgmt_domain_name
    ipam_obj.create_ipam(count=1,conn_obj_list=conn_obj_list,**kwargs)
    mgmt_cidr      = global_conf['mgmt,cidr_start']
    mgmt_cidr_obj  = CIDR(mgmt_cidr)
    cidr           = mgmt_cidr_obj.get_next_cidr()
    cidr1          = mgmt_cidr_obj.get_next_cidr()

    conf = {}
    conf['ipam_fq_name_list']  = [admin_tenant_fq_name + [ipam_name]]
    conf['ipv4_cidr_list']     = [cidr1]
    conf['ipam_name']          = ipam_name
    conf['tenant']             = admin_tenant
    conf['vn_name']            = mgmt_vn_name + ".1"
    conf['disable_gateway']    = True
    conf['shared_flag']        = True
    conf['use_fixture']        = False
    conf['external_flag']      = global_conf['mgmt,external_flag']

    vn_obj  = VN(None)
    extend_to_pr,mgmt_vn_fqname,mgmt_vn_uuid = vn_obj.create_vn(count=1,conn_obj_list=conn_obj_list,**conf)
 
    conf = {}
    conf['ipam_fq_name_list']  = [admin_tenant_fq_name + [ipam_name]]
    conf['ipv4_cidr_list']     = [cidr]
    conf['ipam_name']          = ipam_name
    conf['tenant']             = admin_tenant
    conf['vn_name']            = mgmt_vn_name
    conf['disable_gateway']    = True
    conf['shared_flag']        = True
    conf['use_fixture']        = False
    conf['external_flag']      = global_conf['mgmt,external_flag']

    vn_obj  = VN(None)
    extend_to_pr,mgmt_vn_fqname,mgmt_vn_uuid = vn_obj.create_vn(count=1,conn_obj_list=conn_obj_list,**conf)
    return mgmt_vn_fqname,mgmt_vn_uuid

def get_mysql_token():

    fptr = open("/etc/contrail/mysql.token","r")
    return fptr.readline().strip()

def get_pairs(si):

    left_vns = si['left']
    right_vns = si['right']
    vn_pairs = []

    for lvn in left_vns:
        for rvn in right_vns:
            if lvn.split("_")[-1] == rvn.split("_")[-1]:
                vn_pairs.append((lvn,rvn))
                continue

    return vn_pairs
                
 
class Test(object):

    def __init__(self,yaml_global_conf,ini_global_conf,test_conf):

        self.yaml_global_conf = yaml_global_conf
        self.ini_global_conf = ini_global_conf
        self.test_conf = test_conf
        self.tenant_conf = test_conf['tenants']

    def cleanup_tenant(self):
        tenant_list   = self.global_conf['tenant_list']
        conn_obj_list = self.conn_obj_list
        func_arg = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list
        proj_obj = ProjectConfig(None)

        print "tenant_list:",tenant_list
        func_arg = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list

        lbaas_obj = Lbaas(None)
        lbaas_obj.delete_lb_vips(*func_arg)
       
        bgpaas_obj = Bgpaas(None)
        bgpaas_obj.delete_bgpaas(*func_arg)

        fip_obj = FloatingIPPool(None)
        fip_obj.delete_fip_pools(*func_arg)

        router_obj = RouterConfig(None)
        router_obj.delete_logical_interfaces(*func_arg)

        lbaas_obj = Lbaas(None)
        lbaas_obj.delete_health_monitors(*func_arg)
        lbaas_obj.delete_lb_members(*func_arg)

        vm_obj = VM(None)
        vm_obj.delete_vms(*func_arg)

        lr_obj    = LogicalRouterConfig(None)
        lr_obj.delete_logical_routers(*func_arg)

        svc_obj = ServicesConfig(None)
        svc_obj.delete_service_health_checks(*func_arg)

        svc_obj = ServicesConfig(None)
        svc_obj.delete_service_instances(*func_arg)

        vm_obj = VM(None)
        vm_obj.delete_vmis(*func_arg)

        port_tuple = PortTuples(None) 
        port_tuple.delete_port_tuples(*func_arg)
        
        vn_obj = VN(None)
        vn_obj.delete_extend_to_physical_routers(*func_arg)

        lbaas_obj = Lbaas(None)
        lbaas_obj.delete_lb_vips(*func_arg)
        lbaas_obj.delete_lb_pools(*func_arg)

        vn_obj = VN(None)
        vn_obj.delete_vns(*func_arg)

        ipam_obj   = IPAM(None)
        ipam_obj.delete_ipams(*func_arg)

        policy_obj = Policy(None)
        #policy_obj.detach_policies(*func_arg)
        policy_obj.delete_policies(*func_arg)

        project_obj = ProjectConfig(None)
        project_obj.delete_tenants(*func_arg)

        vdns_obj = vDNS(None)
        vdns_obj.delete_record_per_tenant(*func_arg)
        time.sleep(2)
 
    def get_vm_info(self):
        
        conn_obj_list = self.conn_obj_list
        tenant_list = self.global_conf['tenant_list']
        vm_obj = VM(None)
        vm_info = vm_obj.retrieve_vm_info(conn_obj_list=conn_obj_list,tenant_list=tenant_list,global_conf=self.global_conf,tenant_conf=self.tenant_conf)
        svc_obj = ServicesConfig(None)
        sc_info = svc_obj.retrieve_sc_info(conn_obj_list=conn_obj_list,tenant_list=tenant_list)
        for tenant in sc_info.keys():
           for si in sc_info[tenant]['service-instances']:
               left_right_vn_pairs = get_pairs(si)
               for vn_pair in left_right_vn_pairs:
                   vms_left = vm_info[tenant][vn_pair[0].split(".")[-1]]
                   vms_left = filter(lambda x: re.search('vm',x['name']),vms_left)
                   vms_right = vm_info[tenant][vn_pair[1].split(".")[-1]]
                   vms_right = filter(lambda x: re.search('vm',x['name']),vms_right)
                   sc_info[tenant][vn_pair] = (vms_left, vms_right)
        #print sc_info
        return vm_info, sc_info
        #return vm_info

    def get_vlan_info(self):
        conn_obj_list = self.conn_obj_list
        router_obj = RouterConfig(None)
        vlan_info  = router_obj.retrieve_pr_vlan_info(conn_obj_list=conn_obj_list,global_conf=self.global_conf)
        return vlan_info

    def cleanup_global_config(self):

        admin_tenant = {'fq_name':['default-domain','admin']}
        admin_tenant_fq_name = admin_tenant['fq_name']
        conn_obj_list = self.conn_obj_list
        proj = ProjectConfig(None)
        admin_tenant = proj.retrieve_admin_tenant_info(conn_obj_list)
        func_arg = [self.thread_count,self.global_conf,self.tenant_conf]
        lls_obj = LLS(None)
        lls_obj.delete_link_local_services(conn_obj_list,*func_arg)

        routerconf_obj = RouterConfig(None)
        func_arg1 = func_arg[:]
        func_arg1.append([admin_tenant])
        routerconf_obj.delete_logical_interfaces(conn_obj_list,*func_arg1)
        routerconf_obj.delete_physical_interfaces(conn_obj_list,*func_arg)
        routerconf_obj.delete_physical_routers(conn_obj_list,*func_arg)

        delete_mgmt_vn(conn_obj_list,admin_tenant,*func_arg)

        global_conf_obj = VrouterGlobalConfig(None)
        global_conf_obj.delete_qoss(count=self.thread_count,conn_obj_list=conn_obj_list,global_conf=self.global_conf)

        # delete mgmt IPAM
        ipam_name_pattern        = self.global_conf['ipam,name,pattern']
        ipam_name                = re.sub(self.global_conf['test_id,replace_str'],str(self.global_conf['test_id']),ipam_name_pattern)
        mgmt_domain_name_pattern = self.global_conf['mgmt,vdns_domain_name_pattern']
        mgmt_domain_name         = re.sub(self.global_conf['test_id,replace_str'],str(self.global_conf['test_id']),mgmt_domain_name_pattern)
        mgmt_domain_name         = re.sub('\.','-',mgmt_domain_name)

        args_list = [1]
        kwargs    = {'tenant':admin_tenant,'ipam_name':ipam_name}
        ipam_obj  = IPAM(None)
        ipam_obj.delete_ipam(count=self.thread_count,conn_obj_list=[conn_obj_list[0]],**kwargs)
        vdns_obj = vDNS(None)
        vdns_obj.delete_vdns(conn_obj_list)

        host_aggr_obj = HostAggregate(None)
        host_aggr_obj.delete_host_aggregates(conn_obj_list,*func_arg)
        return

    def parse_cli_args(self,args):
        """
          --tenant_count use cli count else count from yaml
          --tenant_index 200:10000 or default: 0-650
          --tenant_index_random # if mentioned,index should be random,else start from initial index

          --tenant_name_prefix  # default:None ( use yaml ).If configured use to generate tenant names

          --tenant_name         # default:None.If configured,act on particular tenant name
        """   
        self.global_conf['cli,tenant_count']         = int(args.tenant_count)
        self.global_conf['cli,tenant_index_range']   = args.tenant_index_range
        self.global_conf['cli,tenant_index_random']  = args.tenant_index_random
        self.global_conf['cli,tenant_name_prefix']   = args.tenant_name_prefix
        self.global_conf['cli,tenant_name']          = args.tenant_name
        self.global_conf['cli,action,create']        = args.create
        self.global_conf['cli,action,delete']        = args.delete
        self.global_conf['cli,action,create_global'] = args.create_global
        self.global_conf['cli,action,delete_global'] = args.delete_global
        self.global_conf['tenant_index_range']  = self.global_conf['cli,tenant_index_range']
        self.global_conf['tenant_index_random'] = self.global_conf['cli,tenant_index_random']

        if self.global_conf['cli,action,create'] or self.global_conf['cli,action,create_global'] :
           create = True
        elif self.global_conf['cli,action,delete'] or self.global_conf['cli,action,delete_global']:
           create = False
        else:
           create = None

        host_aggregates_yaml = self.yaml_global_conf.get('host_aggregates',[])
        host_aggregates = []
        for host_aggr in host_aggregates_yaml:
           aggr = {}
           aggr['aggr_name'] = host_aggr['name']
           aggr['zone_name'] = host_aggr['zone_name']
           aggr['hosts'] = []
           for host in host_aggr['hosts']:
               aggr['hosts'].append(host['name'])
           host_aggregates.append(aggr)
 
        self.global_conf['host_aggregates'] = host_aggregates

        self.global_conf['dpdk_config']     = self.yaml_global_conf.get('dpdk_config',None)
        self.global_conf['non_dpdk_config'] = self.yaml_global_conf.get('non_dpdk_config',None)

        if self.global_conf['cli,tenant_count'] != 0 :
           self.global_conf['tenant_count'] = self.global_conf['cli,tenant_count']
        else:
           self.global_conf['tenant_count'] = self.tenant_conf['tenant,count']

        tenant_name  = self.global_conf['cli,tenant_name']
        if args.tenant_name_prefix:
           tenant_name_prefix = args.tenant_name_prefix
        else:
           tenant_name_prefix = self.tenant_conf['tenant,name_prefix']
        if args.domain_name_prefix:
           domain_name_prefix = args.domain_name_prefix
        else:
           domain_name_prefix = self.tenant_conf['tenant,domain_prefix']
        tenant_count = self.global_conf['tenant_count']
        tenant_index = self.global_conf['tenant_index_range'].split(":") 
        tenant_index_start = int(tenant_index[0])
        if len(tenant_index) == 1:
           tenant_index_end = 65000
        else:
           tenant_index_end = int(tenant_index[1])

        self.conn_obj_list = create_connections(self.thread_count)

        proj_obj = ProjectConfig(None)
        if tenant_name and string.upper(tenant_name) == "ALL":
           # for delete/traffic only
           existing_tenants = proj_obj.retrieve_configured_tenant_list(conn_obj_list=self.conn_obj_list) 
           tenant_list = []
           for tenant in existing_tenants:
               if tenant['fq_name'] == ['default-domain','admin']:
                  continue
               tenant_list.append(tenant)  
        elif tenant_name and string.upper(tenant_name) == "ALL_TEST" :
           # for delete/traffic only
           existing_tenants = proj_obj.retrieve_configured_tenant_list(conn_obj_list=self.conn_obj_list) 
           tenant_list = []
           for tenant in existing_tenants:
               domain_name,tenant_name = tenant['fq_name']
               if tenant['fq_name'] == ['default-domain','admin']:
                  continue
               if re.search(tenant_name_prefix,tenant_name):
                   tenant_list.append(tenant)
        elif tenant_name :
           # do action for particular tenant_name
           tenant_fq_name_list = []
           if re.search(tenant_name_prefix,tenant_name):
              tenant_fq_name_list.append(tenant_name)
        elif tenant_name is None:
           tenant_list = []
           if create:
              while len(tenant_list) != tenant_count:
                    if self.global_conf['tenant_index_random']:
                       index = random.randint(tenant_index_start,tenant_index_end)
                    else:
                       if len(tenant_list) == 0:
                          index = tenant_index_start
                    tenant_name = tenant_name_prefix + "." + str(index)
                    domain_name = re.sub('XXX',str(index),domain_name_prefix)
                    index += 1
                    if [domain_name,tenant_name] in tenant_list:
                       continue
                    tenant_list.append([domain_name,tenant_name])
              tenant_list.append(['default-domain','admin'])
              tenant_list = map(lambda x: {'fq_name':x},tenant_list)
           else: # --delete/traffic only
              existing_tenants = proj_obj.retrieve_configured_tenant_list(conn_obj_list=self.conn_obj_list)
              filtered_tenants = []
              filtered_tenant_dict = {}
              for tenant in existing_tenants:
                  domain_name,tenant_name = tenant['fq_name']
                  ret = re.search('(\d+)',tenant_name)
                  if ret:
                     tenant_index = ret.group(1)
                     if int(tenant_index) >= tenant_index_start and \
                              int(tenant_index) <= tenant_index_end:
                        filtered_tenants.append(tenant)
                        filtered_tenant_dict[int(tenant_index)] = tenant
              tenant_indx_key = filtered_tenant_dict.keys()[:]
              tenant_indx_key.sort()
              filtered_tenants_n = []
              for tenant_indx in tenant_indx_key:
                  filtered_tenants_n.append(filtered_tenant_dict[tenant_indx])
                 
              if self.global_conf['tenant_index_random']:
                 for i in xrange(tenant_count):
                    random.shuffle(filtered_tenants_n)
                    tenant_list.append(filtered_tenants_n[0])
                    filtered_tenants.pop(0)
              else:
                 tenant_list = filtered_tenants_n[0:tenant_count] 

        return tenant_list

    def parse_config(self):

        self.global_conf = {}
        self.tenant_conf = {}
        self.traffic_conf = {}

        self.global_conf['glance,image_name'] = self.ini_global_conf['GLOBALS']['glance_image_name']
        self.thread_count                     = int(self.ini_global_conf['GLOBALS']['thread_count'])

        self.test_name               = self.test_conf['name']
        self.global_conf['test_id']  = self.test_conf['id']
        self.global_conf['test_id,replace_str'] = 'ZZZ'

        self.global_conf['mgmt,vn_name']                  = self.yaml_global_conf['virtual_network']['name']
        self.global_conf['mgmt,subnet_name']              = self.yaml_global_conf['virtual_network']['name'] + "_subnet"
        self.global_conf['mgmt,external_flag']            = self.yaml_global_conf['virtual_network']['adv_options']['external_flag']
        self.global_conf['mgmt,cidr_start']               = self.yaml_global_conf['virtual_network']['subnets'][0]['cidr']
        self.global_conf['mgmt,vdns_domain_name_pattern'] = self.yaml_global_conf['vDNS']['domain_name']
        self.global_conf['pr_mx']  = self.yaml_global_conf.get('pr_mx',[])
        self.global_conf['pr_qfx']         = self.yaml_global_conf.get('pr_qfx',[])
        self.global_conf['flow_aging']     = self.yaml_global_conf.get('flow_aging',[])
        self.global_conf['forwarding_mode'] = self.yaml_global_conf.get('forwarding_mode',"l2_l3")
        self.global_conf['vxlan_identifier_mode'] = self.yaml_global_conf.get('vxlan_identifier_mode',"automatic")
        self.global_conf['qos']            = self.yaml_global_conf.get('qos',[])
        self.global_conf['encap_priority'] = self.yaml_global_conf.get('encap_priority',[])
        self.global_conf['ecmp_hashing']   = self.yaml_global_conf.get('ecmp_hashing',[])
        self.global_conf['ip_fab_subnets'] = self.yaml_global_conf.get('ip_fab_subnets',"")

        lls_conf = self.yaml_global_conf.get('LLS',None)
        if lls_conf:
           self.global_conf['lls,name']       = lls_conf['name']
           self.global_conf['lls,count']      = lls_conf['count']
           self.global_conf['lls,start_ip']   = lls_conf['lls_ip']
           self.global_conf['lls,start_port'] = lls_conf['lls_port']
           self.global_conf['lls,fab_ip']     = lls_conf['fab_ip']
           self.global_conf['lls,fab_port']   = lls_conf['fab_port']
           self.global_conf['lls,fab_dns']    = lls_conf['fab_dns']

        global_vdns_conf = self.yaml_global_conf.get('vDNS',None)
        if global_vdns_conf:
           self.global_conf['vdns,name_pattern']         = global_vdns_conf['name']
           self.global_conf['vdns,domain_name,pattern']  = global_vdns_conf['domain_name']
           self.global_conf['vdns,dyn_updates']          = global_vdns_conf['dyn_updates']
           self.global_conf['vdns,rec_resolution_order'] = global_vdns_conf['rec_resolution_order']
           self.global_conf['vdns,floating_ip_record']   = global_vdns_conf['floating_ip_record']
           self.global_conf['vdns,ttl']                  = global_vdns_conf['ttl']
           self.global_conf['vdns,forwarder']            = global_vdns_conf['forwarder']
           self.global_conf['vdns,external_visible']     = global_vdns_conf['external_visible']
           self.global_conf['vdns,reverse_resolution']   = global_vdns_conf['reverse_resolution']

        global_ipam_conf = self.yaml_global_conf.get('IPAM',None)
        if global_ipam_conf:
           self.global_conf['ipam,name,pattern']  = global_ipam_conf['name']
           self.global_conf['ipam,count']         = global_ipam_conf['count']

        st_conf = self.yaml_global_conf.get('service_template',None)
        self.global_conf['service_templates'] = st_conf

        tenant_conf              = self.test_conf['tenants'][0]
        self.tenant_conf['tenant,name_prefix']       = tenant_conf['name_prefix']
        self.tenant_conf['tenant,domain_prefix']     = tenant_conf.get('domain_prefix','default-domain')
        self.tenant_conf['tenant,count']             = tenant_conf['count'] 
        self.tenant_conf['tenant,index,replace_str'] = 'XXX'
        self.tenant_conf['tenant,vn_group_list']     = []

        tenant_network_conf      = tenant_conf['virtual_networks']
        self.tenant_conf['tenant,vn_group_list'] = []
        self.tenant_conf['vn,index,replace_str'] = 'YYY'
        bgpaas_conf = tenant_conf.get('bgpaas',None)
        if bgpaas_conf:
           self.tenant_conf['bgpaas,name'] = bgpaas_conf['name']
           self.tenant_conf['bgpaas,asn']  = bgpaas_conf['asn']

        lbaas_conf = tenant_conf.get('Lbaas',None)
        
        if False: #lbaas_conf:
           tenant_lbaas_conf = tenant_conf['Lbaas'][0]
           self.tenant_conf['lbaas,pool_name']         = tenant_lbaas_conf['pool_name']
           self.tenant_conf['lbaas,count']             = tenant_lbaas_conf['count']
           self.tenant_conf['lbaas,method']            = tenant_lbaas_conf['method']
           self.tenant_conf['lbaas,pool,protocol']     = tenant_lbaas_conf['pool_protocol']
           self.tenant_conf['lbaas,pool,members_port'] = tenant_lbaas_conf['pool_members'][0]['port']
           pool_vip_conf = tenant_lbaas_conf['pool_vip']
           self.tenant_conf['lbaas,pool,vip_name']     = pool_vip_conf['vip_name']
           self.tenant_conf['lbaas,pool,vip_port']     = pool_vip_conf['port']
           self.tenant_conf['lbaas,pool,vip_protocol'] = pool_vip_conf['protocol']
           probe_conf    = tenant_lbaas_conf['probe']
           self.tenant_conf['lbaas,probe,type']    = probe_conf['type']
           self.tenant_conf['lbaas,probe,delay']   = probe_conf['delay']
           self.tenant_conf['lbaas,probe,timeout'] = probe_conf['timeout']
           self.tenant_conf['lbaas,probe,retries'] = probe_conf['retries']
        
        self.tenant_conf['port_mirror_conf'] = tenant_conf.get('port_mirror',{})

        for i in xrange(len(tenant_network_conf)):
            vn_info                    = {}
            vn_info['vn,name,pattern'] = tenant_network_conf[i]['name']
            vn_info['count']           = tenant_network_conf[i].get('count',1)
            vn_info['zone_name']       = tenant_network_conf[i].get('zone_name',None)
            vn_info['subnet,count']    = tenant_network_conf[i]['subnets'][0]['count']
            #vn_info['subnet,cidr']     = tenant_network_conf[i]['subnets'][0]['cidr']
            vn_info['attach_fip']      = tenant_network_conf[i].get('attach_fip',None)
            vn_info['attach_policy']   = tenant_network_conf[i].get('attach_policy',False)
            vn_info['fwd_mode']        = tenant_network_conf[i].get('fwd_mode','l2_l3')
            vn_info['qos']             = tenant_network_conf[i].get('qos',False)
            vn_info['ipv4_cidr']       = tenant_network_conf[i].get('ipv4_cidr',False)
            vn_info['ipv6_cidr']       = tenant_network_conf[i].get('ipv6_cidr',False)
            if tenant_network_conf[i].has_key('vm'):
              vn_info['vm,name_pattern'] = tenant_network_conf[i]['vm']['name']
              vn_info['vm,count']        = tenant_network_conf[i]['vm']['count']
              vn_info['vm,attach_port_mirror'] = tenant_network_conf[i]['vm'].get('attach_port_mirror',None)
              vn_info['vm,flavor']         = tenant_network_conf[i]['vm'].get('flavor',"m1.small")
              vn_info['vm,fat_flow']       = tenant_network_conf[i]['vm'].get('fat_flow',None)
              vn_info['vm,disable_policy'] = tenant_network_conf[i]['vm'].get('disable_policy',None)
              vn_info['vm,additional_vn_list'] = tenant_network_conf[i]['vm'].get('additional_vn',[])
              glance_image = tenant_network_conf[i]['vm'].get('image',None)
              if glance_image:
                 vn_info['vm,glance_image'] = glance_image
              else:
                 vn_info['vm,glance_image'] = self.global_conf['glance,image_name']
              vn_info['vm,mgmt_network_first'] = tenant_network_conf[i]['vm'].get('mgmt_network_first',False)
            if tenant_network_conf[i].has_key('bgp_vm'):
              vn_info['bgp_vm,name_pattern'] = tenant_network_conf[i]['bgp_vm']['name']
              vn_info['bgp_vm,count']        = tenant_network_conf[i]['bgp_vm']['count']
              vn_info['bgp_vm,flavor']       = tenant_network_conf[i]['bgp_vm']['flavor']
              glance_image = tenant_network_conf[i]['bgp_vm'].get('image',None)
              if glance_image:
                 vn_info['bgp_vm,glance_image'] = glance_image
              else:
                 vn_info['bgp_vm,glance_image'] = self.global_conf['glance,image_name']
              vn_info['bgp_vm,userdata'] = tenant_network_conf[i]['bgp_vm'].get('userdata',None)
              vn_info['bgp_vm,mgmt_network_first'] = tenant_network_conf[i]['bgp_vm'].get('mgmt_network_first',False)
              vn_info['bgp_vm,additional_vn_list'] = tenant_network_conf[i]['bgp_vm'].get('additional_vn',[])

            if tenant_network_conf[i].has_key('bms'):
              vn_info['bms,name']  = tenant_network_conf[i]['bms']['name']
              vn_info['bms,count'] = tenant_network_conf[i]['bms'].get('count',1)
              vn_info['bms,tor_list']   = tenant_network_conf[i]['bms']['tor_list']
            if tenant_network_conf[i].has_key('route_targets'):
              vn_info['route_target,count']     = tenant_network_conf[i]['route_targets']['count']
              vn_info['route_target,asn']       = tenant_network_conf[i]['route_targets']['asn']
              vn_info['route_target,rt_number'] = tenant_network_conf[i]['route_targets']['rt_number']

            if tenant_network_conf[i]['adv_options'].has_key('external_flag'):
              vn_info['external_flag'] = tenant_network_conf[i]['adv_options']['external_flag']
            else:
              vn_info['external_flag'] = False

            if tenant_network_conf[i]['adv_options'].has_key('shared_flag'):
              vn_info['shared_flag'] = tenant_network_conf[i]['adv_options']['shared_flag']
            else:
              vn_info['shared_flag'] = False

            if tenant_network_conf[i]['adv_options'].has_key('extend_to_pr_flag') :
              vn_info['extend_to_pr_flag'] = tenant_network_conf[i]['adv_options']['extend_to_pr_flag']
            else:
              vn_info['extend_to_pr_flag'] = False

            if tenant_network_conf[i]['adv_options'].has_key('disable_gateway'):
              vn_info['disable_gateway'] = tenant_network_conf[i]['adv_options']['disable_gateway']
            else:
              vn_info['disable_gateway'] = False

            if tenant_network_conf[i]['adv_options'].has_key('flood_unknown_unicast'):
              vn_info['flood_unknown_unicast'] = tenant_network_conf[i]['adv_options']['flood_unknown_unicast']
            else:
              vn_info['flood_unknown_unicast'] = False

            if tenant_network_conf[i]['adv_options'].has_key('reverse_path_forwarding'):
              vn_info['reverse_path_forwarding'] = tenant_network_conf[i]['adv_options']['reverse_path_forwarding']
            else:
              vn_info['reverse_path_forwarding'] = True

            if tenant_network_conf[i]['adv_options'].has_key('allow_transit'):
              vn_info['allow_transit'] = tenant_network_conf[i]['adv_options']['allow_transit']
            else:
              vn_info['allow_transit'] = False

            self.tenant_conf['tenant,vn_group_list'].append(vn_info)

        tenant_vdns_conf = tenant_conf.get('vDNS',None)
        if tenant_vdns_conf:
           self.tenant_conf['vdns,name_pattern']         = tenant_vdns_conf['name']
           self.tenant_conf['vdns,domain_name,pattern']  = tenant_vdns_conf['domain_name']
           self.tenant_conf['vdns,dyn_updates']          = tenant_vdns_conf['dyn_updates']
           self.tenant_conf['vdns,rec_resolution_order'] = tenant_vdns_conf['rec_resolution_order']
           self.tenant_conf['vdns,floating_ip_record']   = tenant_vdns_conf['floating_ip_record']
           self.tenant_conf['vdns,ttl']                  = tenant_vdns_conf['ttl']
           self.tenant_conf['vdns,forwarder']            = tenant_vdns_conf['forwarder']
           self.tenant_conf['vdns,external_visible']     = tenant_vdns_conf['external_visible']
           self.tenant_conf['vdns,reverse_resolution']   = tenant_vdns_conf['reverse_resolution']

        tenant_ipam_conf = tenant_conf.get('IPAM',None)
        if tenant_ipam_conf:
           self.tenant_conf['ipam,index,replace_str']  = 'AAA'
           self.tenant_conf['ipam,name,pattern']  = tenant_ipam_conf['name']
           self.tenant_conf['ipam,count']         = tenant_ipam_conf['count']

        tenant_policy = tenant_conf.get('policies',None)
        if tenant_policy:
           self.tenant_conf['policy,name,pattern']        = tenant_policy['name']
           self.tenant_conf['policy,count']               = tenant_policy['count']
           self.tenant_conf['policy,allow_rules_network'] = tenant_policy['rules']['allow_rules_network']
           self.tenant_conf['policy,allow_rules_port']    = tenant_policy['rules']['allow_rules_port']
           
        tenant_fip = tenant_conf.get('FIP',None)
        
        if tenant_fip:
           shared_fip = tenant_fip.get('shared_fip',None)
           if shared_fip:
              self.tenant_conf['fip,shared'] = True
              self.tenant_conf['fip,shared,tenant_name'] = shared_fip['fip_tenant_name']
              self.tenant_conf['fip,shared,fip_gw_vn_name'] = shared_fip['fip_gw_vn_name']
              self.tenant_conf['fip,shared,floating_ip_pool'] = shared_fip['floating_ip_pool']
           else:
              self.tenant_conf['fip,name']            = tenant_fip['floating_ip_pool']
              self.tenant_conf['fip,gw_vn_count']     = tenant_fip['count']
              self.tenant_conf['fip,gw_vn_name']      = tenant_fip['fip_gw_vn_name']
              self.tenant_conf['fip,allocation_type'] = tenant_fip['alloc_type']
              self.tenant_conf['fip,count']           = tenant_fip['count']

        tenant_routers = tenant_conf.get('routers',None)
        if tenant_routers:
           tenant_router = tenant_conf['routers'][0]
           self.tenant_conf['routers,name']        = tenant_router['name']
           self.tenant_conf['routers,count']       = tenant_router['count']
        service_instance = tenant_conf.get('service_instance',None)
        if service_instance:
           self.tenant_conf['service_instances'] = service_instance
        service_health_check = tenant_conf.get('service_health_check',None)
        if service_health_check:
           self.tenant_conf['service_health_check'] = service_health_check
        serial_service_chain = tenant_conf.get('serial_service_chain',None)
        if serial_service_chain:
           self.tenant_conf['serial_service_chain'] = serial_service_chain
        parallel_service_chain = tenant_conf.get('parallel_service_chain',None)
        if parallel_service_chain:
           self.tenant_conf['parallel_service_chain'] = parallel_service_chain
         
        tenant_traffic_block = self.test_conf.get('traffic_block',None)
        if tenant_traffic_block:
           url_short_file = '/opt/contrail/tools/http/httpload/url_short'
           url_lls_file = '/opt/contrail/tools/http/httpload/url_lls'
           url_lb_file = 'opt/contrail/tools/http/httpload/url_lb'
           run = '/opt/contrail/zmq/run'
           duration = int(tenant_traffic_block['duration'])
           sampling_interval = int(tenant_traffic_block['sampling_interval'])
           httpload_loop_count = duration // sampling_interval
           lls_rate = int(tenant_traffic_block['client_comm']['c_httpload_lls'][-1])
           short_rate = int(tenant_traffic_block['client_comm']['c_httpload_short'][-1])

           self.traffic_conf['duration'] = str(duration)
           self.traffic_conf['sampling_interval'] = str(sampling_interval)
           self.traffic_conf['external_server_ip'] = tenant_traffic_block['external_server']['ip']
           self.traffic_conf['pvn_ext_port_start'] = int(tenant_traffic_block['external_server']['pvn_ext_port_start'])
           self.traffic_conf['psvn_ext_port_start'] = int(tenant_traffic_block['external_server']['snat_ext_port_start'])
           self.traffic_conf['ping'] = tenant_traffic_block['client_comm']['c_ping']
           self.traffic_conf['ping6'] = tenant_traffic_block['client_comm']['c_ping6']
           self.traffic_conf['c_iperf3'] = tenant_traffic_block['client_comm']['c_iperf3'] + ["-i", str(sampling_interval), "-t", str(duration)]
           self.traffic_conf['s_iperf3'] = tenant_traffic_block['server_comm']['s_iperf3']

           self.traffic_conf['c_udp_ucast'] = tenant_traffic_block['client_comm']['c_udp_ucast'] + ["-i", str(sampling_interval), "-t", str(sampling_interval)]
           self.traffic_conf['s_udp_ucast'] = tenant_traffic_block['server_comm']['s_udp_ucast']

           self.traffic_conf['httpload_lb'] = tenant_traffic_block['client_comm']['c_lbaas']

           self.traffic_conf['httpload_lls'] = [run, str(httpload_loop_count)] + tenant_traffic_block['client_comm']['c_httpload_lls'] + \
                                               ['-fetches', str(lls_rate * sampling_interval), url_lls_file]
           self.traffic_conf['httpload_short'] = [run, str(httpload_loop_count)] + tenant_traffic_block['client_comm']['c_httpload_short'] + \
                                               ['-fetches', str(short_rate * sampling_interval), url_short_file]

        


    def initTest(self,args):

        self.parse_config()
        tenant_list = self.parse_cli_args(args)
        self.global_conf['tenant_list'] = tenant_list

        self.testbed_file    = self.ini_global_conf['ENV']['testbed_file']

    def configure_dummy_vn(self):
        
        conn_obj_list = self.conn_obj_list
        create_dummy_vn(conn_obj_list,1,self.global_conf,self.tenant_conf)

    def configure_global_config(self):

        tenant_list = self.global_conf['tenant_list']
        conn_obj_list = self.conn_obj_list
        update_properties = self.update_properties

        func_arg = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,update_properties

        admin_tenant_fq_name = {'fq_name':['default-domain','admin']}
        func_arg1 = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,[admin_tenant_fq_name],update_properties
        #svc_obj = ServicesConfig(None)
        #svc_obj.create_service_templates(*func_arg)
        #sys.exit()

        project_obj = ProjectConfig(None)
        project_obj.update_security_groups(*func_arg1)

        global_conf_obj = VrouterGlobalConfig(None)
        #global_conf_obj.create_qoss(count=self.thread_count,conn_obj_list=conn_obj_list,global_conf=self.global_conf)

        global_conf_obj.update_conf(count=self.thread_count,conn_obj_list=conn_obj_list,global_conf=self.global_conf)

        vdns_obj = vDNS(None)
        vdns_obj.create_mgmt_vdns_tree(*func_arg)

        mgmt_vn_fq_name_uuid = create_mgmt_vn_ipam(*func_arg)

        router_obj = RouterConfig(None)
        router_obj.create_physical_routers(*func_arg)

        if not update_properties:
           mgmt_vn_fqname,mgmt_vn_uuid = mgmt_vn_fq_name_uuid
           pr_mx_name_list = []
           pr_mxs = self.global_conf['pr_mx']
           for pr_mx in pr_mxs:
               pr_mx_name_list.append(pr_mx['name'])

           kwargs = {}
           kwargs['tenant_fq_name'] = admin_tenant_fq_name
           kwargs['vn_name']     = self.global_conf['mgmt,vn_name']
           kwargs['router_list'] = pr_mx_name_list
           kwargs['vn_ids']      = [mgmt_vn_uuid]
           kwargs['fq_name']     = [mgmt_vn_fqname]
           pr_obj_list = []
           vn_obj = VN(None)
           for router_name in pr_mx_name_list:
               pr_obj = vn_obj.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
               if pr_obj:
                  pr_obj_list.append(pr_obj)
           mgmt_vn_obj = VN(None)
           for pr_obj in pr_obj_list:
               mgmt_vn_obj.add_extend_to_pr(count=self.thread_count,conn_obj_list=conn_obj_list,pr_obj=pr_obj,**kwargs)

        lls_obj = LLS(None)
        lls_obj.create_link_local_services(*func_arg)
 
        router_obj = RouterConfig(None)
        router_obj.create_tors(*func_arg)
        router_obj.create_physical_interfaces(*func_arg)

        host_aggr_obj = HostAggregate(None)
        host_aggr_obj.create_host_aggregates(*func_arg)

        svc_obj = ServicesConfig(None)
        svc_obj.create_service_templates(*func_arg)
        return

    def analytics_check(self):
        tenant_list_conf  = self.global_conf['tenant_list']
        conn_obj_list     = self.conn_obj_list
        update_properties = self.update_properties
        dpdk              = self.dpdk
        func_arg     = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list_conf,update_properties , dpdk
        analytic_obj = AnalyticsConfig(None)
        analytic_obj.analyticss(*func_arg)

    def configure_tenant(self):
        tenant_list_conf  = self.global_conf['tenant_list']
        conn_obj_list     = self.conn_obj_list
        update_properties = self.update_properties
        dpdk              = self.dpdk

        func_arg = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list_conf,update_properties

        project_obj = ProjectConfig(None)
        project_obj.create_tenants(*func_arg)

        tenant_list = []
        existing_tenants = project_obj.retrieve_configured_tenant_list(conn_obj_list=conn_obj_list)
        existing_tenants_t = map(lambda x:x['fq_name'],existing_tenants)
        for tenant in tenant_list_conf:
            indx = existing_tenants_t.index(tenant['fq_name'])
            tenant_list.append(existing_tenants[indx])

        func_arg = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list,update_properties
        func_arg1 = conn_obj_list,self.thread_count,self.global_conf,self.tenant_conf,tenant_list,update_properties,dpdk 

        #svc_obj = ServicesConfig(None)
        #svc_obj.create_service_instances(*func_arg1)

        policy_obj = Policy(None)
        policy_obj.create_policies(*func_arg)
        vdns_obj = vDNS(None)
        vdns_obj.create_data_vdns_tree(*func_arg)
        ipam_obj = IPAM(None)
        ipam_obj.create_ipams(*func_arg)

        vn_obj = VN(None)
        vn_obj.create_vns(*func_arg)

        lrouter_obj = LogicalRouterConfig(None)
        lrouter_obj.create_logical_routers(*func_arg)
        lrouter_obj.attach_vns_to_logical_routers(*func_arg)

        project_obj = ProjectConfig(None)
        project_obj.update_security_groups(*func_arg)

        vm_obj = VM(None)
        vm_obj.create_vms(*func_arg1)
        
        fip_obj = FloatingIPPool(None)
        fip_obj.delete_fip_pools(*func_arg)
        fip_obj = FloatingIPPool(None)
        fip_obj.create_fip_pools(*func_arg)

        fip_obj = FloatingIPPool(None)
        fip_obj.associate_fips(*func_arg)

        router_obj = RouterConfig(None)
        router_obj.create_logical_interfaces(*func_arg)
        router_obj.associate_fip_to_vmis(*func_arg)

        #lbaas_obj = Lbaas(None)
        #lbaas_obj.create_lb_pools(*func_arg)
        #lbaas_obj.create_lb_members(*func_arg)
        #lbaas_obj.create_health_monitors(*func_arg)
        #lbaas_obj.associate_health_monitors(*func_arg)
        #lbaas_obj.create_lb_vips_associate_fips(*func_arg)

        svc_obj = ServicesConfig(None)
        svc_obj.create_service_health_checks(*func_arg)

        svc_obj = ServicesConfig(None)
        svc_obj.create_service_instances(*func_arg1)

        bgpaas_obj = Bgpaas(None)
        bgpaas_obj.create_bgpaas(*func_arg)

        time.sleep(5)

def main():

   parser = argparse.ArgumentParser(add_help=False)
   parser.add_argument("-i", "--ini_file", default=None,help="Specify global conf file", metavar="FILE")
   parser.add_argument("-g", "--global_yaml_config_file", default=None,help="Specify global yaml conf file", metavar="FILE")
   parser.add_argument("-c", "--yaml_config_file", default=None,help="Specify Test conf file", metavar="FILE")
   parser.add_argument('--delete',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--create',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--update',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--update_global',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--delete_global',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--create_global',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--create_dummy_vn',action="store_true",default=False,help='action for specific tenant only')
   parser.add_argument('--tenant_count',action="store", default='0', help='action for specific tenant only')
   parser.add_argument('--tenant_index_range',action="store", default="0:65000", help='action for specific tenant only')
   parser.add_argument('--tenant_index_random',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--tenant_name',action="store", default=None, help='action for specific tenant only[None or all or specific tenant_name]')
   parser.add_argument('--tenant_name_prefix',action="store", default=None, help='action for specific tenant only')
   parser.add_argument('--domain_name_prefix',action="store", default=None, help='action for specific tenant only')
   parser.add_argument('--dry',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--stop_traffic',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--analytics',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--traffic',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--traffic_only',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--feature_ping',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--feature_ping_only',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--dpdk',action="store_true", default=False, help='action for specific tenant only')
   parser.add_argument('--loop_count',action="store", default='1', help='loop count')
   parser.add_argument('--debug',action="store_true", default=False, help='')

   args, remaining_argv = parser.parse_known_args(sys.argv[1:])
   cli_args = parse_cli(remaining_argv)
   ini_conf = parse_cfg_file(args.ini_file)

   print args
   
   if args.debug:
      debug_func()
      sys.exit()
      
   yaml_conf = parse_yaml_cfg_file(args.global_yaml_config_file)
   yaml_global_conf = yaml_conf['global_config']

   yaml_conf = parse_yaml_cfg_file(args.yaml_config_file)
   tests = yaml_conf['tests']
   for test_conf in tests:
      test_obj = Test(yaml_global_conf,ini_conf,test_conf)
      test_obj.initTest(args)
      tenant_list = test_obj.global_conf['tenant_list']
      if args.dry:
         print "##### TEST_ACTION ####"
         print "tenant_list:",tenant_list
         print "create:",args.create
         print "delete:",args.delete
         print "dpdk:",args.dpdk
         print "######################"
         continue

      if args.update or args.update_global:
         test_obj.update_properties = True
      else:
         test_obj.update_properties = False

      if args.dpdk:
         test_obj.dpdk = True
      else:
         test_obj.dpdk = False

      if args.traffic_only or args.stop_traffic or args.feature_ping_only:
           args.delete = False
           args.delete_global = False
           args.create_global = False
           args.create = False
           args.traffic = True
      if args.delete:
         test_obj.cleanup_tenant()
      if args.delete_global:
         test_obj.cleanup_global_config()
      if args.create_global or args.update_global:
         test_obj.configure_global_config()
      if args.create_dummy_vn:
         test_obj.configure_dummy_vn()
         sys.exit()
      if args.create or args.update:
         test_obj.configure_tenant()
      if args.analytics:
         test_obj.analytics_check()
      if args.traffic or args.stop_traffic:
         for tenant in tenant_list:
             tenant_fq_name = tenant['fq_name']
             domain_name,tenant_name = tenant_fq_name
             if re.search('-',tenant_name):
                print "ERROR: duplicate tenant ids present",tenant_name
                sys.exit()
         fp = open("result.txt","w")
         print time.time()
         tenants, sc_info = test_obj.get_vm_info()
         print time.time()
         print "checking MGMT IP reachability..."
         if not mgmt_ip_reachable(tenants):
            print "MGMT IP not pingable"
            fp.write("1")
            #sys.exit()
         else:
            print "MGMT IP is pingable..continuing test.."
         kill_result = build_kill_traffic_commands(test_obj, tenants)
         if args.stop_traffic:
            print "Kill traffic done..exiting.."
            sys.exit()
       
         bms_vlans = test_obj.get_vlan_info()
         print time.time()
         print "BMS vlans:",bms_vlans
         bms_vlans = False
         if bms_vlans:
            cleanup_bms_netns(test_obj.global_conf['pr_qfx'], bms_vlans)
            if not setup_bms_netns(test_obj.global_conf['pr_qfx'], bms_vlans):
               print "BMS NETNS setup failed"
               #sys.exit()
         #redo_dhclient(tenants)
         if test_obj.traffic_conf:
            print "Running Feature PINGs. Results in ping_result.log"
            fp_ex = open('res.csv.txt', 'ab')
            writer = csv.writer(fp_ex, dialect = 'excel')
            title = ['TCP_Throughput_Success', 'TCP_Retrans', 'TCP_Throughput_Fail',\
                     'UDP_Throughput_Success', 'UDP_Throughput_Failure',\
                     'S_Fetches', 'S_Success', 'S_Failures', 'S_Rate', 'S_min', 'S_max', 'S_mean',\
                     'LL_Fetches', 'LL_Success', 'LL_Failures', 'LL_Rate', 'LL_min', 'LL_max', 'LL_mean',\
                     'LB_Fetches', 'LB_Success', 'LB_Failures', 'LB_Rate', 'LB_min', 'LB_max', 'LB_mean']
            writer.writerow(title)
            fp_ex.close()

            if args.feature_ping or args.feature_ping_only :
              for i in range(int(args.loop_count)):
               if ping_check_setup(test_obj, tenants, sc_info,"ping_result_%s.txt"%tenant_name):
                  print "Feature Ping Passed. Exiting"
               else: 
                  print "Feature Ping Failed..exiting.."
              
            if args.feature_ping_only:
               sys.exit()

            print "Feature Ping Passed. Running FULL Traffic"

            for i in range(int(args.loop_count)):
               client_res = run_traffic(test_obj, tenants,sc_info)
               kill_result = build_kill_traffic_commands(test_obj, tenants)
               fp.write("0")
            else:
               print "Feature Ping Failed. Exiting"
               fp.write("1")
   print "Exiting test"
try:
  main()
except AttributeError,SystemExit:
  pass
except:
  traceback.print_exc(file=sys.stdout)
  sys.stdout.flush()
  #while True:
  #    time.sleep(1)
