import os
import threading
import argparse
import sys

import pdb
import re
from netaddr import IPNetwork
import ipaddr
from tcutils.cfgparser import parse_cfg_file
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import  yaml
from config import *
from config import Project as ConfigProject

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
from diagnostics.config import Project

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

def delete_mgmt_vn(thread_count,global_conf,tenant_conf):

    pr_mx_name_list = []
    pr_mxs = global_conf['pr_mx']
    for pr_mx in pr_mxs:
        pr_mx_name_list.append(pr_mx['name'])

    mgmt_vn_name   = global_conf['mgmt,vn_name']

    kwargs = {}
    kwargs['tenant_name'] = 'admin'
    kwargs['vn_name']     = ([u'default-domain',u'admin',unicode(mgmt_vn_name)],)
    kwargs['mx_list'] = pr_mx_name_list
    vn_obj = VN(None)
    vn_obj.delete_extend_to_pr(thread_count=thread_count,args_list=[1,],kwargs_list=[kwargs])

    kwargs = {}
    vn_obj = VN(None)
    vn_obj.delete_vn_by_name(args=('admin',mgmt_vn_name),kwargs=kwargs)

def create_mgmt_vn_ipam(thread_count,global_conf,tenant_conf):

    mgmt_vn_name   = global_conf['mgmt,vn_name']
    mgmt_cidr      = global_conf['mgmt,cidr_start']
    mgmt_cidr_obj  = CIDR(mgmt_cidr)
    cidr           = mgmt_cidr_obj.get_next_cidr()

    ipam_name_pattern = global_conf['ipam,name,pattern']
    ipam_name = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),ipam_name_pattern)
    mgmt_domain_name_pattern = global_conf['mgmt,vdns_domain_name_pattern']
    mgmt_domain_name         = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),mgmt_domain_name_pattern)
    mgmt_domain_name         = re.sub('\.','-',mgmt_domain_name)

    ipam_obj = IPAM(None)
    kwargs = {}
    kwargs['tenant_name'] = 'admin'
    kwargs['ipam_name']   = ipam_name
    kwargs['domain_name'] = mgmt_domain_name
    ipam_obj.create_ipam(thread_count=1,args_list=[1],kwargs_list=[kwargs])

    conf = {}
    conf['cidr']         = cidr
    conf['ipam_name']    = ipam_name
    conf['tenant_name']  = 'admin'
    conf['vn_name']      = mgmt_vn_name
    conf['disable_gateway'] = True
    conf['shared_flag']     = True
    conf['external_flag']   = global_conf['mgmt,external_flag']

    print conf
    vn_obj  = VN(None)
    vn_obj.create_vn(thread_count=thread_count,args_list=[1,],kwargs_list=[conf])

    pr_mx_name_list = []
    pr_mxs = global_conf['pr_mx']
    for pr_mx in pr_mxs:
        pr_mx_name_list.append(pr_mx['name'])

    kwargs = {}
    kwargs['tenant_name'] = 'admin'
    kwargs['vn_name']     = mgmt_vn_name
    kwargs['router_list'] = pr_mx_name_list
    vn_obj.add_extend_to_pr(thread_count=thread_count,args_list=[1,],kwargs_list=[kwargs])
 
def get_mysql_token():

    fptr = open("/etc/contrail/mysql.token","r")
    return fptr.readline().strip()
 
class Test(object):

    def __init__(self,yaml_global_conf,ini_global_conf,test_conf):

        self.yaml_global_conf = yaml_global_conf
        self.ini_global_conf = ini_global_conf
        self.test_conf = test_conf
        self.tenant_conf = test_conf['tenants']

        #self.mysql_passwd = get_mysql_token()

    def cleanUpTest(self):

        fip_obj = FloatingIPPool(None)
        fip_obj.delete_fip_pools(self.thread_count,self.global_conf,self.tenant_conf)

        # delete VMs under all the test tenants
        vm_obj = VM(None)
        vm_obj.delete_vms(self.thread_count,self.global_conf,self.tenant_conf)

        lr_obj = LogicalRouter(None)
        lr_obj.delete_logical_routers(self.thread_count,self.global_conf,self.tenant_conf)

        ## delete all VNs under all the test tenants
        vn_obj = VN(None)
        vn_obj.delete_extend_to_physical_routers(self.thread_count,self.global_conf,self.tenant_conf)

        vn_obj = VN(None)
        vn_obj.delete_vns(self.thread_count,self.global_conf,self.tenant_conf)

        # delete ipam attached to all the test tenants
        ipam_obj   = IPAM(None)
        ipam_obj.delete_ipams(self.thread_count,self.global_conf,self.tenant_conf)

        # delete policies under all the test tenants
        #policy_obj = Policy(None)
        #policy_obj.delete_policies(self.thread_count,self.global_conf,self.tenant_conf)

        project_obj = ConfigProject(None)
        project_obj.delete_tenants(self.thread_count,self.global_conf,self.tenant_conf)

        # delte MGMT VN  
        delete_mgmt_vn(self.thread_count,self.global_conf,self.tenant_conf)
        # delete mgmt IPAM
        ipam_name_pattern        = self.global_conf['ipam,name,pattern']
        ipam_name                = re.sub(self.global_conf['test_id,replace_str'],str(self.global_conf['test_id']),ipam_name_pattern)
        mgmt_domain_name_pattern = self.global_conf['mgmt,vdns_domain_name_pattern']
        mgmt_domain_name         = re.sub(self.global_conf['test_id,replace_str'],str(self.global_conf['test_id']),mgmt_domain_name_pattern)
        mgmt_domain_name         = re.sub('\.','-',mgmt_domain_name)

        args_list = [('admin',ipam_name,mgmt_domain_name)]
        kwargs_list = [{}]  
        ipam_obj.delete_ipam(thread_count=self.thread_count,args_list=args_list,kwargs_list=kwargs_list)
        vdns_obj = vDNS(None)
        vdns_obj.delete_vdns()

        lls_obj = LLS(None)
        lls_obj.delete_link_local_services(self.thread_count,self.global_conf,self.tenant_conf)

        return

    def parse_config(self):

        self.image_conf = {}
        self.global_conf = {}
        self.tenant_conf = {}

        self.image_conf['glance,image_name'] = self.ini_global_conf['GLOBALS']['glance_image_name']
        self.thread_count                    = self.ini_global_conf['GLOBALS']['thread_count']

        self.test_name               = self.test_conf['name']
        self.global_conf['test_id']  = self.test_conf['id']
        self.global_conf['test_id,replace_str'] = 'ZZZ'

        self.global_conf['mgmt,vn_name']                  = self.yaml_global_conf['virtual_network']['name']
        self.global_conf['mgmt,subnet_name']              = self.yaml_global_conf['virtual_network']['name'] + "_subnet"
        self.global_conf['mgmt,external_flag']            = self.yaml_global_conf['virtual_network']['adv_options']['external_flag']
        self.global_conf['mgmt,cidr_start']               = self.yaml_global_conf['virtual_network']['subnets'][0]['cidr']
        self.global_conf['mgmt,vdns_domain_name_pattern'] = self.yaml_global_conf['vDNS']['domain_name']

        lls_conf = self.yaml_global_conf.get('LLS',None)
        if lls_conf:
           self.global_conf['lls,name']       = lls_conf['name']
           self.global_conf['lls,count']      = lls_conf['count']
           self.global_conf['lls,start_ip']   = lls_conf['lls_ip']
           self.global_conf['lls,start_port'] = lls_conf['lls_port']
           self.global_conf['lls,fab_ip']     = lls_conf['fab_ip']
           self.global_conf['lls,fab_port']   = lls_conf['fab_port']

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

        pr_mx = self.yaml_global_conf['pr_mx']
        self.global_conf['pr_mx'] = []
        for i,pr in enumerate(pr_mx):
            pr_info = {}
            pr_info['name'] = pr['name']
            self.global_conf['pr_mx'].append(pr_info)

        tenant_conf              = self.test_conf['tenants'][0]
        self.tenant_conf['tenant,name,pattern'] = tenant_conf['name']
        self.tenant_conf['tenant,count']        = tenant_conf['count'] 
        self.tenant_conf['tenant,index,replace_str'] = 'XXX'
        self.tenant_conf['tenant,vn_group_list'] = []

        tenant_network_conf      = tenant_conf['virtual_networks']
        self.tenant_conf['tenant,vn_group_list']     = []
        self.tenant_conf['vn,index,replace_str'] = 'YYY'

        lbaas_conf = tenant_conf.get('Lbaas',None)
        if lbaas_conf:
           tenant_lbaas_conf = tenant_conf['Lbaas'][0]
           self.tenant_conf['lbaas,pool_name']         = tenant_lbaas_conf['pool_name']
           self.tenant_conf['lbaas,count']             = tenant_lbaas_conf['count']
           self.tenant_conf['lbaas,method']            = tenant_lbaas_conf['method']
           self.tenant_conf['lbaas,pool,protocol']     = tenant_lbaas_conf['pool_protocol']
           self.tenant_conf['lbaas,pool,subnet']       = tenant_lbaas_conf['pool_subnet']
           self.tenant_conf['lbaas,pool,members_port'] = tenant_lbaas_conf['pool_members'][0]['port']
           pool_vip_conf = tenant_lbaas_conf['pool_vip']
           self.tenant_conf['lbaas,pool,vip']          = pool_vip_conf['vip']
           self.tenant_conf['lbaas,pool,vip_port']     = pool_vip_conf['port']
           self.tenant_conf['lbaas,pool,vip_protocol'] = pool_vip_conf['protocol']
           self.tenant_conf['lbaas,pool,vip_subnet']   = pool_vip_conf['vip_subnet']
           probe_conf    = tenant_lbaas_conf['probe']
           self.tenant_conf['lbaas,probe,type']    = probe_conf['type']
           self.tenant_conf['lbaas,probe,delay']   = probe_conf['delay']
           self.tenant_conf['lbaas,probe,timeout'] = probe_conf['timeout']
           self.tenant_conf['lbaas,probe,retries'] = probe_conf['retries']
        
        for i in xrange(len(tenant_network_conf)):
            vn_info                    = {}
            vn_info['vn,name,pattern'] = tenant_network_conf[i]['name']
            vn_info['count']           = tenant_network_conf[i]['count']
            vn_info['subnet,count']    = tenant_network_conf[i]['subnets'][0]['count']
            vn_info['subnet,cidr']     = tenant_network_conf[i]['subnets'][0]['cidr']
            vn_info['attach_fip']      = tenant_network_conf[i].get('attach_fip',None)
            if tenant_network_conf[i].has_key('vm'):
              vn_info['vm,name_pattern'] = tenant_network_conf[i]['vm']['name']
              vn_info['vm,count']        = tenant_network_conf[i]['vm']['count']
            if tenant_network_conf[i].has_key('route_targets'):
              vn_info['route_target,count']     = tenant_network_conf[i]['route_targets']['count']
              vn_info['route_target,asn']       = tenant_network_conf[i]['route_targets']['asn']
              vn_info['route_target,rt_number'] = tenant_network_conf[i]['route_targets']['rt_number']
            if tenant_network_conf[i]['adv_options'].has_key('external_flag'):
              vn_info['external_flag'] = tenant_network_conf[i]['adv_options']['external_flag']
            else:
              vn_info['external_flag'] = False
            if tenant_network_conf[i]['adv_options'].has_key('extend_to_pr_flag') and tenant_network_conf[i]['adv_options']['extend_to_pr_flag']:
              vn_info['extend_to_pr_flag'] = True
            else:
              vn_info['extend_to_pr_flag'] = False
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

        tenant_ipam_conf = tenant_conf['IPAM']
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
           self.tenant_conf['fip,name']            = tenant_fip['floating_ip_pool']
           self.tenant_conf['fip,gw_vn_name']      = tenant_fip['fip_gw_vn_name']
           self.tenant_conf['fip,allocation_type'] = tenant_fip['alloc_type']
           self.tenant_conf['fip,count']           = tenant_fip['count']
           self.tenant_conf['fip,attach,vn']       = tenant_fip['attach_fip']

        tenant_routers = tenant_conf.get('routers',None)
        if tenant_routers:
           tenant_router = tenant_conf['routers'][0]
           self.tenant_conf['routers,name']        = tenant_router['name']
           self.tenant_conf['routers,count']       = tenant_router['count']

    def initTest(self):

        self.parse_config()

        self.testbed_file    = self.ini_global_conf['ENV']['testbed_file']

    def runTest(self):

        #lbaas_obj = Lbaas(None)
        #lbaas_obj.create_lb_pools(self.thread_count,self.global_conf,self.tenant_conf)
        #lbaas_obj.create_lb_members(self.thread_count,self.global_conf,self.tenant_conf)

        project_obj = ConfigProject(None)
        project_obj.create_tenants(self.thread_count,self.global_conf,self.tenant_conf)

        project_obj = ConfigProject(None)
        project_obj.update_security_groups(self.thread_count,self.global_conf,self.tenant_conf)

        vdns_obj = vDNS(None)
        vdns_obj.create_vdns_tree(self.thread_count,self.global_conf,self.tenant_conf)

        #policy_obj = Policy(None)
        #policy_obj.create_policies(self.thread_count,self.global_conf,self.tenant_conf)

        ipam_obj = IPAM(None)
        ipam_obj.create_ipams(self.thread_count,self.global_conf,self.tenant_conf)

        vn_obj = VN(None)
        vn_obj.create_vns(self.thread_count,self.global_conf,self.tenant_conf)

        vn_obj = VN(None)
        vn_obj.update_extend_to_physical_routers(self.thread_count,self.global_conf,self.tenant_conf)
        create_mgmt_vn_ipam(self.thread_count,self.global_conf,self.tenant_conf)

        #policy_obj = Policy(None)
        #policy_obj.attach_policies(self.thread_count,self.global_conf,self.tenant_conf)

        vm_obj = VM(None)
        vm_obj.create_vms(self.thread_count,self.global_conf,self.tenant_conf)

        router_obj = LogicalRouter(None)
        router_obj.create_logical_routers(self.thread_count,self.global_conf,self.tenant_conf)
        router_obj.attach_vns_to_logical_routers(self.thread_count,self.global_conf,self.tenant_conf)

        fip_obj = FloatingIPPool(None)
        fip_obj.delete_fip_pools(self.thread_count,self.global_conf,self.tenant_conf)

        fip_obj = FloatingIPPool(None)
        fip_obj.create_fip_pools(self.thread_count,self.global_conf,self.tenant_conf)

        fip_obj = FloatingIPPool(None)
        fip_obj.associate_fips(self.thread_count,self.global_conf,self.tenant_conf)

        lls_obj = LLS(None)
        lls_obj.create_link_local_services(self.thread_count,self.global_conf,self.tenant_conf)

        return 


def main():

   parser = argparse.ArgumentParser(add_help=False)
   parser.add_argument("-i", "--ini_file", default=None,help="Specify global conf file", metavar="FILE")
   parser.add_argument("-c", "--yaml_config_file", default=None,help="Specify Test conf file", metavar="FILE")
   parser.add_argument('--cleanup_only', default=0, type=int, help='Do cleanup only')

   args, remaining_argv = parser.parse_known_args(sys.argv[1:])
   cli_args = parse_cli(remaining_argv)

   ini_conf = parse_cfg_file(args.ini_file)

   yaml_conf = parse_yaml_cfg_file(args.yaml_config_file)

   print "INI_CONF:",ini_conf
   print "YAML_CONF:",yaml_conf

   #Do Global Configurations First
   #Setup MGMT VN: simple network, 1 CIDR for mgmt traffic. Set 'shared' flag for VN so that 
   #all tenants can use the same VN  
      
   yaml_global_conf = yaml_conf['global_config']

   tests = yaml_conf['tests']
   for test_conf in tests:
      test_obj = Test(yaml_global_conf,ini_conf,test_conf)
      test_obj.initTest()
      test_obj.cleanUpTest()
      #test_obj.runTest()
   print "Exiting test"

main()

