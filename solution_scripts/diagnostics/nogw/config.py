# Fix
# 1.   ssladapter crashes with multiprocessing.
#      https://github.com/sigmavirus24/requests-toolbelt/issues/34 
# 2.   tcutils/util.py ( tcutils is at same level as diagnostics )  needs to be updated as follows:
#      inside 'class customdict'
#      def __setitem__(self, key, value):
#        if self.has_key('validate_set'): #self.validate_set:
#           self.validate_set(key, value)

import traceback
import uuid
import random
import string
import copy
import inspect
import ipaddr
import re
import threading
from common import log_orig as logging
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import pdb
import tempfile
import os
from vm_test import *
from vn_test import *
from ipam_test import *
from floating_ip import *
from project_test import *
from vdns_fixture import *
from policy_test import *
from lib import *
import time
from common.log_orig import ContrailLogger
from svc_instance_fixture import SvcInstanceFixture

import time                                                

def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te-ts)
        return result

    return timed

#from vnc_api.vnc_api import *

cidr_lock = threading.Lock()
connection_lock = threading.Lock()

from tcutils import Process

def retry(tries=4, delay=3):
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                ret = f(*args, **kwargs)
                if ret:
                   break
                mtries -= 1
                print "retrying..."
                time.sleep(delay)
        return f_retry
    return deco_retry

def dumpArgs(func):
    '''Decorator to print function call details - parameters names and effective values'''
    def wrapper(*func_args, **func_kwargs):
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        args = func_args[:len(arg_names)]
        defaults = func.__defaults__ or ()
        args = args + defaults[len(defaults) - (func.__code__.co_argcount - len(args)):]
        params = list(zip(arg_names, args))
        args = func_args[len(arg_names):]
        if args: params.append(('args', args))
        if func_kwargs: params.append(('kwargs', func_kwargs))
        print(func.__name__ + ' (' + ', '.join('%s = %r' % p for p in params) + ' )')
        return func(*func_args, **func_kwargs)
    return wrapper  

class CIDR:

  def __init__(self,cidr):
   self.cidr  = cidr
   self.index = 0
   self.mask  = self.cidr.split("/")[1]

  def get_next_cidr(self):
    cidr_lock.acquire()
    if self.index == 0 :
      self.index += 1
    else: 
      ip = IPNetwork(self.cidr)[0]
      new_ip = ipaddr.IPAddress(ip) + 256
      self.cidr = str(new_ip) + "/" + self.mask
    cidr_lock.release()
    return self.cidr

class ProjectNotFound(Exception):
      def __init__(self, value):
          self.value = value
      def __str__(self):
          return repr(self.value)

def generate_vdns_conf(global_conf,tenant_conf,vdns):
    vdns_domain_name = vdns.get_domain()
    vdns_name = re.sub("\.","-",vdns_domain_name)
    if vdns.get_forwarder():
       vdns_next_vdns = "default-domain:" + re.sub("\.","-",vdns.get_forwarder())
    else:
       vdns_next_vdns = None
    conf = {}
    conf['vdns_name']               = vdns_name
    conf['domain']                  = "default-domain"
    conf['vdns_domain_name']        = vdns_domain_name
    conf['vdns_next_vdns']          = vdns_next_vdns
    conf['vdns_dyn_updates']        = global_conf['vdns,dyn_updates']
    conf['vdns_rec_order']          = global_conf['vdns,rec_resolution_order']
    conf['vdns_ttl']                = global_conf['vdns,ttl']
    conf['vdns_fip_record']         = global_conf['vdns,floating_ip_record']
    conf['vdns_external_visible']   = global_conf['vdns,external_visible']
    conf['vdns_reverse_resolution'] = global_conf['vdns,reverse_resolution']

    return conf


def generate_lb_pool_name(global_conf,tenant_conf,tenant_indx):
    test_id                  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    lbaas_pool_name_pattern  = tenant_conf['lbaas,pool_name']

    pool_name = re.sub(tenant_index_replace_str,str(tenant_indx),lbaas_pool_name_pattern)
    pool_name = re.sub(test_id_replace_str,str(test_id),pool_name)
    return pool_name

def generate_vip_name(global_conf,tenant_conf,vip_index):

    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    vip_name_pattern = tenant_conf['lbaas,pool,vip_name']
    vip_name = re.sub(tenant_index_replace_str,str(vip_index),vip_name_pattern)
    return vip_name

def generate_domain_name(global_conf,tenant_conf,tenant_indx):
    test_id                  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    domain_name_pattern = tenant_conf['vdns,domain_name,pattern']
    domain_name = re.sub(tenant_index_replace_str,str(tenant_indx),domain_name_pattern)
    domain_name = re.sub(test_id_replace_str,str(test_id),domain_name)
    return domain_name

def generate_domain_server_name(global_conf,tenant_conf,tenant_indx):
    test_id                  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    domain_name_pattern = tenant_conf['vdns,domain_name,pattern']
    domain_server_name = re.sub(tenant_index_replace_str,str(tenant_indx),domain_name_pattern)
    domain_server_name = re.sub(test_id_replace_str,str(test_id),domain_server_name)
    domain_server_name = re.sub("\.","-",domain_server_name)
    return domain_server_name

def generate_fip_pool_name(global_conf,tenant_conf,tenant_indx,pool_indx):
    test_id                  = global_conf['test_id']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    test_id_replace_str      = global_conf['test_id,replace_str']
    vn_index_replace_str     = tenant_conf['vn,index,replace_str']
    pool_name_pattern        = tenant_conf['fip,name']
    pool_name =  re.sub(tenant_index_replace_str,str(tenant_indx),pool_name_pattern)
    pool_name =  re.sub(test_id_replace_str,str(test_id),pool_name)
    pool_name =  re.sub(vn_index_replace_str,str(pool_indx),pool_name)
    return pool_name

def generate_policy_name(global_conf,tenant_conf,tenant_indx):
    test_id                  = global_conf['test_id']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    test_id_replace_str      = global_conf['test_id,replace_str']
    policy_name_pattern = tenant_conf['policy,name,pattern']
    policy_name =  re.sub(tenant_index_replace_str,str(tenant_indx),policy_name_pattern) 
    policy_name =  re.sub(test_id_replace_str,str(test_id),policy_name) 
    return policy_name

def generate_mgmt_vn_name(global_conf,tenant_conf):

    return global_conf['mgmt,vn_name']

def generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx):

    test_id                  = global_conf['test_id']
    tenant_name_prefix       = tenant_conf['tenant,name_prefix']
    vn_index_replace_str     = tenant_conf['vn,index,replace_str']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    test_id_replace_str      = global_conf['test_id,replace_str']
     
    vn_name = re.sub(vn_index_replace_str,str(vn_indx),vn_name_pattern)
    vn_name = re.sub(tenant_index_replace_str,str(tenant_indx),vn_name)
    vn_name = re.sub(test_id_replace_str,str(test_id),vn_name)
    return vn_name

def generate_router_name(global_conf,tenant_conf,tenant_indx,router_indx):
    test_id                  = global_conf['test_id']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    test_id_replace_str      = global_conf['test_id,replace_str']
    vn_index_replace_str     = tenant_conf['vn,index,replace_str']
    router_name_pattern      = tenant_conf['routers,name']
    router_name = re.sub(tenant_index_replace_str,str(tenant_indx),router_name_pattern)
    router_name = re.sub(test_id_replace_str,str(test_id),router_name)
    router_name = re.sub(vn_index_replace_str,str(router_indx),router_name)
    return router_name

def generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_index):
    test_id               = global_conf['test_id']
    test_id_replace_str   = global_conf['test_id,replace_str']
    pool_vn_name_pattern  = None
    for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
        vn_info        = tenant_conf['tenant,vn_group_list'][vn_group_index]
        vn_name_pattern = vn_info['vn,name,pattern']
        if re.search('Private_LB_Pool_VN',vn_name_pattern):
           pool_vn_name_pattern = vn_name_pattern
           break
    if pool_vn_name_pattern is None:
       return False
    vn_index = 0
    vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,pool_vn_name_pattern,vn_index)
    return vn_name

def generate_ipam_name(global_conf,tenant_conf,tenant_index):
    test_id                  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    ipam_name_pattern        = tenant_conf['ipam,name,pattern']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    ipam_name = re.sub(tenant_index_replace_str,str(tenant_index),ipam_name_pattern)
    ipam_name = re.sub(test_id_replace_str,str(test_id),ipam_name)
    return ipam_name

def get_tenant_index(tenant_conf,tenant_name):
    tenant_name_prefix  = tenant_conf['tenant,name_prefix'] 
    return int(re.search(tenant_name_prefix+'.(\d+)',tenant_name).group(1))

def get_vn_type(vn_name):
    vn_group_list = ['Private_SNAT_VN','Private_VN','Private_LB_VIP_VN','Private_LB_Pool_VN',
                     'SNAT_GW_VN','Public_FIP_VN','Private_SC_Left_VN','Private_SC_Right_VN','Private_BGP_VN']
    for vn in vn_group_list:
        if re.search(vn,vn_name):
           return vn 

def generate_rt_number(already_allocated_rt):
    while True:
       rt = random.randint(1000000,3000000)
       if rt not in already_allocated_rt:
         break
    return rt

def generate_cidr(tenant_name,vn_type,already_allocated_cidr):
    ip_group = {}
    ip_group['Private_SNAT_VN']    = [i for i in xrange(11,12)]
    ip_group['Private_VN']         = [i for i in xrange(12,13)]
    ip_group['Private_LB_VIP_VN']  = [i for i in xrange(13,14)]
    ip_group['Private_LB_Pool_VN'] = [i for i in xrange(14,15)]
    ip_group['SNAT_GW_VN']         = [i for i in xrange(15,16)]
    ip_group['Public_FIP_VN']      = [i for i in xrange(16,17)]
    ip_group['Private_SC_Left_VN'] = [i for i in xrange(17,18)]
    ip_group['Private_SC_Right_VN'] = [i for i in xrange(18,19)]
    ip_group['Private_BGP_VN']      = [i for i in xrange(19,20)]
    #ip_group = {'Private_SNAT_VN':[11],'Private_VN':[12],'Private_LB_VIP_VN':[13],'Private_LB_Pool_VN':[14],'SNAT_GW_VN':[15],'Public_FIP_VN':[16]}
    mask = 16 if vn_type == 'Public_FIP_VN' else 24
    while True:
       first_octet  = random.choice(ip_group[vn_type])
       second_octet = random.randint(0,254)
       if mask == 16:
          third_octet = 0
       else:
          third_octet = random.randint(0,254)
       fourth_octet = 0
       cidr = "%i.%i.%i.%i/%d" %(first_octet,second_octet,third_octet,fourth_octet,mask)
       if cidr not in already_allocated_cidr:
          break
    return cidr


def connection():
    obj = ProjectConfig(None)
    obj.get_connection_handle()
    return obj
   
def create_connections(count):
    conn_obj_list = []
    for i in xrange(count):
        conn_obj_list.append(connection())
    return conn_obj_list
    
def debug_func():
     
    obj = ProjectConfig(None)
    obj.get_connection_handle()
    pdb.set_trace()
    
def sorted_nicely( l ):
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key = alphanum_key)


class Base(object):
    def __init__(self, connections):
        self.connections = connections

    def fq_name(self, uuid=None):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = self.get_fixture(uuid=uuid)
        return self.fixture.get_fq_name()

    def uuid(self):
        return self.fixture.get_uuid()

    def get_connection_handle(self,project_name="admin"):

        self.ini_file= 'sanity_params.ini'
        self.log_name='tor-scale.log'

        import logging as log1
        from common.log_orig import ContrailLogger
        log1.getLogger('urllib3.connectionpool').setLevel(log1.WARN)
        log1.getLogger('paramiko.transport').setLevel(log1.WARN)
        log1.getLogger('keystoneclient.session').setLevel(log1.WARN)
        log1.getLogger('keystoneclient.httpclient').setLevel(log1.WARN)
        log1.getLogger('neutronclient.client').setLevel(log1.WARN)

        Logger = logging.ContrailLogger(self.log_name)
        Logger.setUp()
        self.logger = Logger.logger

        connection_lock.acquire()
        while True:
             time.sleep(random.random())
             try:
                self.inputs = ContrailTestInit(self.ini_file,logger=self.logger)
                self.inputs.setUp()
                self.connections= ContrailConnections(inputs=self.inputs,logger=self.logger,project_name=project_name)
                self.connections.get_vnc_lib_h() # will set self.connections.vnc_lib in the object
                self.connections.inputs.project_name=project_name
                self.auth = self.connections.get_auth_h()
                break
             except Exception as ex:
                self.logger.warn("Exception happened in ContrailConnections..type : %s"%type(ex).__name__)
                if type(ex).__name__ == "RuntimeError" :
                   self.logger.error("RuntimeError in ContrailConnections")
                   break
        connection_lock.release()
 
class Policy(Base):
    def create(self,inputs,policy_name,rules,connections,api=None):
        self.fixture = PolicyFixture(
                       policy_name=policy_name,
                       rules_list=rules,
                       inputs=inputs,
                       connections=connections,api=api)
        self.fixture.setUp()
        return self.fixture

    def delete(self, policy_fixture):
        policy_fixture.cleanUp()

    def get_fixture(self,uuid=None):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = PolicyFixture(connections=self.connections, uuid=uuid)
        return self.fixture

    def construct_policy_rules(self,allow_rules_network,allow_rules_port):
        rules = []
        for rule_index in xrange(len(allow_rules_network)):
           r = allow_rules_network[rule_index].split()
           src_nw = r[0]
           dst_nw = r[1]
           r = allow_rules_port[rule_index].split()
           src_port = r[0]
           dst_port = r[1]
           rule = {
                       'direction': '<>', 'simple_action': 'pass',
                       'protocol': 'any',
                       'src_ports': '%s'%src_port, 'dst_ports': '%s'%dst_port,
                       'source_network': '%s'%src_nw, 'dest_network': '%s'%dst_nw,
                   } 
           rules.append(rule)
        return rules

    @Process.wrapper
    def create_policy(self,*arg,**kwarg):
        tenant_name = kwarg['tenant_name']
        policy_name = kwarg['policy_name']
        rules       = kwarg['rules']
        connection_obj = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        policy_fq_name = [u'default-domain',u'%s'%tenant_name,unicode(policy_name)]
        project_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name
        try:   
           self.connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
           self.logger.info("Policy: %s already available...skipping create.."%str(policy_fq_name))
           return
        except NoIdError :
           self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
           self.quantum_h = self.connections.get_network_h()
           self.create(self.connections.inputs,policy_name,rules,self.connections)
           return

    def create_policies(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        policy_count        = tenant_conf.get('policy,count',None)
        if policy_count is None:
          return
        policy_rules        = self.construct_policy_rules(tenant_conf['policy,allow_rules_network'],tenant_conf['policy,allow_rules_port'])
        kwargs_list = []
        for tenant_name in tenant_name_list:
          tenant_indx = get_tenant_index(tenant_conf,tenant_name)
          policy_name = generate_policy_name(global_conf,tenant_conf,tenant_indx)
          kwargs = {}
          kwargs['tenant_name'] = tenant_name
          kwargs['policy_name'] = policy_name
          kwargs['rules']       = policy_rules
          kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_policy(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
   
    @Process.wrapper
    def delete_policy(self,*arg,**kwarg):
        tenant_name = kwarg['tenant_name']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
        policys  = self.connections.vnc_lib.network_policys_list(parent_id=proj_obj.uuid)['network-policys']
        for policy in policys:
            self.connections.vnc_lib.network_policy_delete(id=policy['uuid'])

    def delete_policies(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_policy(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def detach(self,tenant_name,vn_fq_name):
        vn_obj     = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.set_network_policy_list([],True)
        self.connections.vnc_lib.virtual_network_update(vn_obj)
        return

    @Process.wrapper
    def attach_policy(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name           = kwarg['tenant_name'] 
        vn_id                 = kwarg['vn_id']
        policy_name           = kwarg['policy_name']
        vn_fq_name            = kwarg['vn_fq_name']
        domain,tenant,vn_name = vn_fq_name
        policy_fq_name = [u'default-domain',u'%s'%tenant_name,unicode(policy_name)]
        try:
           policy_obj = self.connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
        except NoIdError:
           return
        vn_obj     = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.add_network_policy(policy_obj,VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0)))
        self.connections.vnc_lib.virtual_network_update(vn_obj)

    @timeit
    def attach_policies(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        policy_count = tenant_conf.get('policy,count',None)
        if policy_count is None:
          return
        kwargs_list = []
        vns_list    = []
        vn_obj      = VN(None)
        for tenant_name in tenant_name_list:
           tenant_indx = get_tenant_index(tenant_conf,tenant_name)
           for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
               vn_info                = tenant_conf['tenant,vn_group_list'][vn_group_indx]
               attach_policy_required = vn_info.get('attach_policy',None)
               if attach_policy_required is None or not attach_policy_required:
                  continue
               vn_name_pattern = vn_info['vn,name,pattern']
               vn_index = ""
               vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_index)
               kwargs = {}
               kwargs['tenant_name_list'] = [tenant_name]
               kwargs['vn_name_prefix']   = vn_name
               ret      = vn_obj.list_vn(conn_obj_list=conn_obj_list,**kwargs)
               if ret:
                  vns_list.extend(ret)
        if not len(vns_list):
           return
        policy_count        = tenant_conf['policy,count']
        for vn in vns_list:
           tenant_name,vn_id,vn_fq_name = vn
           tenant_indx = get_tenant_index(tenant_conf,tenant_name)
           kwargs = {}
           kwargs['tenant_name'] = tenant_name
           kwargs['policy_name'] = generate_policy_name(global_conf,tenant_conf,tenant_indx)
           kwargs['vn_id']       = vn_id  
           kwargs['vn_fq_name']  = vn_fq_name
           kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.attach_policy(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    @Process.wrapper
    def detach_policy(self,*arg,**kwarg):
        tenant_name           = kwarg['tenant_name']
        vn_fq_name            = kwarg['vn_fq_name']
        domain,tenant,vn_name = vn_fq_name
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        try:
           self.detach(tenant_name,vn_fq_name)
        except:
           pass

    def detach_policies(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        vn_obj = VN(None)
        vn_list = vn_obj.list_vn(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
        if not vn_list:
           return
        for vn in vn_list:
           tenant_name,vn_id,vn_fq_name = vn
           kwargs = {}
           kwargs['tenant_name'] = tenant_name
           kwargs['vn_fq_name']  = vn_fq_name
           kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.detach_policy(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

class ProjectConfig(Base):

    def create(self, name):
        self.fixture = ProjectFixture(project_name=name, connections=self.connections)
        self.fixture.setUp()
        project_id = self.fixture.get_uuid()
        self.add_user_to_tenant(project_id)
        return project_id
    
    @Process.wrapper
    def list_projects(self, *arg, **kwarg):
        connection_obj   = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        projects_list = self.connections.vnc_lib.projects_list()['projects']
        return projects_list

    def retrieve_configured_tenant_list(self,conn_obj_list):
        exclude_tenants = [u'invisible_to_admin', u'admin', u'default-project', u'demo','service']
        tenant_name_list = [] 
        projects_list = self.list_projects(conn_obj_list=conn_obj_list)
        for proj in projects_list:
            domain,t_name = proj['fq_name']
            uuid = proj['uuid']
            if t_name in exclude_tenants:
               continue
            tenant_name_list.append(t_name)
        tenant_name_list = sorted_nicely(tenant_name_list)
        return tenant_name_list

    @Process.wrapper
    def retrieve_vn_list(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        vn_list = self.connections.vnc_lib.virtual_networks_list()['virtual-networks']
        return vn_list

    @Process.wrapper
    def configured_rt_numbers(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        existing_rt_list = []
        rt_list = self.connections.vnc_lib.route_targets_list()['route-targets']
        for rt in rt_list:
            existing_rt_list.append(rt['fq_name'][2])
        return existing_rt_list

    @Process.wrapper
    def configured_cidr(self,*arg,**kwarg):
        existing_cidr = []
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        ipams_list       = self.connections.vnc_lib.network_ipams_list()['network-ipams']
        existing_vns     = []
        for ipam in ipams_list:
           ipam_id  = ipam['uuid']
           ipam_obj = self.connections.vnc_lib.network_ipam_read(id=ipam_id)
           virtual_nw_back_refs = ipam_obj.get_virtual_network_back_refs() or []
           for nw in virtual_nw_back_refs:
               domain,t_name,vn_name = nw['to']
               existing_vns.append(nw['to'])
               subnets = nw['attr']['ipam_subnets']
               for subnet in subnets:
                   cidr_l = str(subnet['subnet']['ip_prefix']) + "/" + str(subnet['subnet']['ip_prefix_len'])
                   existing_cidr.append(cidr_l)

        return (existing_cidr,existing_vns)

    @Process.wrapper
    def create_tenant(self,*arg,**kwarg):
        connection_obj   = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        self.auth        = connection_obj.auth
        tenant_name = kwarg['tenant_name']
        projects = self.connections.vnc_lib.projects_list()['projects']
        project_count = 0
        for proj in projects:
            dom,tname = proj['fq_name']
            if tname == tenant_name or re.search('^%s-'%tenant_name,tname):
               project_count += 1
        if project_count > 1:
           print "ERROR: More than one uuid for the tenant seen",tenant_name
           return False
            
        uuid = self.auth.get_project_id("default-domain",tenant_name)
        if uuid :
           self.logger.warn("Tenant %s already exists with UUID:%s..skipping create"%(tenant_name,uuid))
           return True
        try:
          project_id  = self.create(tenant_name)
          return True
        except:
          return False

    def create_tenants(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = dict()
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        ret = self.create_tenant(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
        if ret is True:
           return
        if ret is False:
           print "ERROR: tenant create failed",tenant_name_list
           sys.exit()
        elif False in ret:
           failed_tenants = []
           for i,t in enumerate(tenant_name_list):
               if ret[i] == False: 
                  failed_tenants.append(t) 
           print "ERROR: tenant create failed for tenants:",failed_tenants
           sys.exit()

    @Process.wrapper
    def update_security_group(self,*arg,**kwarg):
      try:
        tenant_name      = kwarg.pop('tenant_name')
        connection_obj   = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rules = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_2
                  },
                 ]

        sg_fq_name = ['default-domain',tenant_name,'default']
        sg_obj = self.connections.vnc_lib.security_group_read(fq_name=sg_fq_name)
        rule_list = PolicyEntriesType(policy_rule=rules)
        sg_obj.set_security_group_entries(rule_list)
        self.connections.vnc_lib.security_group_update(sg_obj)
      except:
        traceback.print_exc(file=sys.stdout)
        sys.exit()

    @timeit
    def update_security_groups(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = dict()
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.update_security_group(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
    
    def add_user_to_tenant(self, uuid):
        kc = self.connections.get_auth_h().get_keystone_h()
        user_id = kc.get_user_dct(self.connections.inputs.stack_user)
        role_id = kc.get_role_dct('admin')
        kc._add_user_to_tenant(uuid.replace('-', ''), user_id, role_id)

    def update_default_sg(self, uuid=None):
        project_fixture = self.get_fixture(uuid=uuid)
        project_fixture.set_sec_group_for_allow_all()

    def get_connections(self, uuid=None):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = self.get_fixture(uuid=uuid)
        return self.fixture.get_project_connections()

    def delete(self, uuid):
        project_fixture= self.get_fixture(uuid=uuid)
        project_fixture.delete(verify=True)

    @retry(tries=3,delay=5)
    @Process.wrapper
    def delete_tenant(self,*arg,**kwarg):
        #self.get_connection_handle()
        tenant_name = kwarg.pop('tenant_name')
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        try:
          proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
        except:
          self.logger.warn("project %s not found..skipping delete"%tenant_name)
          return True
        try:
          self.delete(proj_obj.uuid)
          return True
        except:
          self.logger.warn("ERROR seen during delete_tenant:%s...retrying.."%tenant_name)
          traceback.print_exc(file=sys.stdout)
          return False
    
    def delete_tenants(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_tenant(thread_count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def verify(self, uuid):
        self.fixture= self.get_fixture(uuid=uuid)
        assert self.fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = ProjectFixture(connections=self.connections, uuid=uuid)
        return self.fixture

class vDNSInfo:

      def __init__(self,domain_name):
        self.domain_name = domain_name
        d = domain_name.split(".")

        if len(d) == 2 :
          self.forwarder = None
        else:
          self.forwarder = ".".join(d[1:])
 
      def get_domain(self):
         return self.domain_name

      def set_uuid(self,uuid):
         self.uuid = uuid

      def get_uuid(self):
         return self.uuid

      def get_forwarder(self):
         return self.forwarder


class vDNS(Base):
    def create(self, name):
        self.fixture = VdnsFixture(connections=self.connections, name=name)
        self.fixture.setUp()
        return self.fixture.get_uuid()

    def delete(self, uuid):
        vdns_fixture = self.get_fixture(uuid=uuid)
        vdns_fixture.delete(verify=True)

    def verify(self, uuid):
        vdns_fixture = self.get_fixture(uuid=uuid)
        assert vdns_fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = VdnsFixture(connections=self.connections, uuid=uuid)
        return self.fixture

    def generate_vdns_list(self,vdns,domain_name):
        d = domain_name.split(".")
        if len(d) <= 2 :
          return vdns

        if not vdns.has_key(domain_name):
           vdns[domain_name] = vDNSInfo(domain_name)
           self.generate_vdns_list(vdns,".".join(d[1:]))

        return vdns

    @Process.wrapper
    def delete_record(self,*arg,**kwarg):
        domain_name    = kwarg.get('domain_name',None)
        forwarder_name = kwarg.get('forwarder_name',None)
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        dns_records = self.connections.vnc_lib.virtual_DNS_records_list()['virtual-DNS-records']
        if domain_name is None:
           records_to_delete = dns_records
        else:
           records_to_delete = []
           for record in dns_records:
               if record['fq_name'] == [u'default-domain',u'%s'%forwarder_name,u'%s'%domain_name] :
                  records_to_delete.append(record)
        for dns_record in records_to_delete :
           self.connections.vnc_lib.virtual_DNS_record_delete(fq_name=dns_record['fq_name'])

    @Process.wrapper
    def create_record(self,*arg,**kwarg):
      try:
        forwarder     = kwarg['forwarder'] 
        rec_name      = kwarg['rec_name']  
        vdns_rec_data = kwarg['rec_data']  
        rec_class     = kwarg['rec_class'] 
        rec_ttl       = kwarg['rec_ttl']   
        rec_type      = kwarg['rec_type']   
        rec_data      = kwarg['rec_data']   

        if forwarder is None:
          return 
        connection_obj = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger

        try:
          self.connections.vnc_lib.virtual_DNS_record_read(fq_name=['default-domain',forwarder.split(':')[-1],rec_name])
          self.logger.warn("Record: default-domain:%s found..skipping create"%rec_name)
          return
        except NoIdError:
          pass  # continue with record creation  

        vdns_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name_str = forwarder)
        vdns_rec_data = VirtualDnsRecordType(rec_name, rec_type, rec_class, rec_data, int(rec_ttl))
        vdns_rec_obj = VirtualDnsRecord(rec_name, vdns_obj, vdns_rec_data)
        self.connections.vnc_lib.virtual_DNS_record_create(vdns_rec_obj)
      except:
            traceback.print_exc(file=sys.stdout)

    @Process.wrapper
    def create_vdns(self,*arg,**kwarg):

        name        = kwarg['vdns_name']
        domain_name = kwarg['domain']
        dns_domain  = kwarg['vdns_domain_name']
        dyn_updates = kwarg['vdns_dyn_updates']
        rec_order   = kwarg['vdns_rec_order']
        ttl         = kwarg['vdns_ttl']
        next_vdns   = kwarg['vdns_next_vdns']
        fip_record  = kwarg['vdns_fip_record']
        reverse_resolution = kwarg['vdns_reverse_resolution']
        
        connection_obj = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger

        domain_name_list = []
        domain_name_list.append(domain_name)
        domain_name_list_list = list(domain_name_list)
        try:
            domain_obj = self.connections.vnc_lib.domain_read(fq_name=domain_name_list_list)
        except NoIdError:
            pass

        if next_vdns and len(next_vdns):
          try:
           next_vdns_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name_str = next_vdns)
          except NoIdError:
           pass

        try:
          self.connections.vnc_lib.virtual_DNS_read(fq_name=[u'%s'%domain_name,u'%s'%name])
          self.logger.warn("Virtual DNS " + name + " found..skipping create..")
          return
        except NoIdError: 
          pass

        vdns_str = ':'.join([domain_name, name])
        vdns_data = VirtualDnsType(domain_name=dns_domain, dynamic_records_from_client=dyn_updates, record_order=rec_order, default_ttl_seconds=int(ttl),next_virtual_DNS=next_vdns,reverse_resolution=reverse_resolution,floating_ip_record=fip_record)

        domain_obj =  Domain(name=domain_name)
        dns_obj    = VirtualDns(name, domain_obj,
                             virtual_DNS_data = vdns_data)
        self.connections.vnc_lib.virtual_DNS_create(dns_obj)

    def create_mgmt_vdns_tree(self,conn_obj_list,thread_count,global_conf,tenant_conf):
        mgmt_vdns_domain_name_pattern = global_conf.get('vdns,domain_name,pattern',None)
        if mgmt_vdns_domain_name_pattern is None:
           return
        mgmt_vdns_domain_name         = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),mgmt_vdns_domain_name_pattern)

        domain_list = []
        domain_list.append(mgmt_vdns_domain_name)
        self.create_vdns_tree(conn_obj_list,global_conf,tenant_conf,domain_list)

    def create_data_vdns_tree(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        data_vdns_domain_name_pattern = tenant_conf.get('vdns,domain_name,pattern',None)
        if data_vdns_domain_name_pattern is None:
           return
        domain_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            tenant_vdns_domain_name = generate_domain_name(global_conf,tenant_conf,tenant_index)
            domain_list.append(tenant_vdns_domain_name)
        self.create_vdns_tree(conn_obj_list,global_conf,tenant_conf,domain_list)

    def create_vdns_tree(self,conn_obj_list,global_conf,tenant_conf,domain_list):
        global_vdns = {}
        for domain in domain_list:
          global_vdns = self.generate_vdns_list(global_vdns,domain)
          base_domain = ".".join(domain.split(".")[-2:])		
          global_vdns[base_domain] = vDNSInfo(base_domain)

        self.vdns_info = {}
        for k,v in global_vdns.iteritems():
           l = len(v.get_domain().split("."))
           if self.vdns_info.has_key(l):
              self.vdns_info[l].append(v)
           else:
              self.vdns_info[l] = [v]

        for l in sorted(self.vdns_info.keys()):
           vdns_l = self.vdns_info[l]
           for vdns in vdns_l:
              vdns_conf = generate_vdns_conf(global_conf,tenant_conf,vdns)
              self.create_vdns(count=1,conn_obj_list=conn_obj_list,**vdns_conf)
              conf = {}
              conf['forwarder']  = vdns_conf['vdns_next_vdns']
              conf['rec_name']   = re.sub("\.","-",vdns_conf['vdns_domain_name'])
              conf['rec_data']   = "default-domain:%s"%conf['rec_name']
              conf['rec_ttl']    = 86400
              conf['rec_type']   = "NS"
              conf['rec_class']  = "IN"
              self.create_record(count=1,conn_obj_list=conn_obj_list,**conf)

    def delete_record_per_tenant(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index       = get_tenant_index(tenant_conf,tenant_name)
            domain_server_name = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            forwarder_name     = "-".join(domain_server_name.split("-")[1:])
            kwargs = {}
            kwargs['domain_name']    = domain_server_name
            kwargs['forwarder_name'] = forwarder_name
            kwargs_list.append(kwargs) 
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_record(count=thread_count,conn_obj_list=[conn_obj_list[0]],**kwargs)

    def delete_vdns_tree(self,args,kwargs):

       root_domain  = kwargs['root_domain'] 
       fq_name      = kwargs['fq_name']

       self.connections = kwargs['connection_obj'].connections
       self.logger      = kwargs['connection_obj'].logger

       vdns_list = self.connections.vnc_lib.virtual_DNSs_list()['virtual-DNSs']
       child_list = []
       current_vdns_uuid = ""
       for vdns in vdns_list :
          vdns_obj = self.connections.vnc_lib.virtual_DNS_read(vdns["fq_name"])
          vdns_data = vdns_obj.get_virtual_DNS_data()
          if ":".join(vdns["fq_name"]) == fq_name :
             current_vdns_uuid = vdns['uuid']
          if vdns_data.get_next_virtual_DNS() == fq_name :
             child_list.append(vdns)

       for vdns in child_list:
          kw = { 'root_domain' : root_domain , 'fq_name':":".join(vdns['fq_name']),'connection_obj':kwargs['connection_obj'] }
          self.delete_vdns_tree(1,kw)
          vdns_list = self.connections.vnc_lib.virtual_DNSs_list()['virtual-DNSs']
       
       if fq_name == root_domain :
           self.logger.debug("reached root domain :%s..clean up done"%root_domain)
           return
       try:
         self.connections.vnc_lib.virtual_DNS_delete(id=current_vdns_uuid)
       except:
         pass
     
    def delete_vdns(self,conn_obj_list):

       kw = {'conn_obj_list':[conn_obj_list[0]]}
       self.delete_record(count=1,**kw)
       root_domain = 'default-domain:soln-com'
       kwargs = {'root_domain':root_domain ,'fq_name':root_domain,'connection_obj':conn_obj_list[0]}
       p = mp.Process(target=self.delete_vdns_tree,args=(1,kwargs))
       p.start()
       p.join()
       return

class IPAM(Base):
    def create(self, name, vdns_id=None):
        vdns_obj=None
        if vdns_id:
            vdns_obj = self.connections.vnc_lib.virtual_DNS_read(id=vdns_id)
        self.fixture = IPAMFixture(connections=self.connections,
                                   name=name, vdns_obj=vdns_obj)
        self.fixture.setUp()
        return self.fixture.get_uuid()

    @Process.wrapper
    def create_ipam(self,*arg,**kwarg):
      try:
        tenant_name        = kwarg['tenant_name']
        ipam_name          = kwarg['ipam_name']
        domain_server_name = kwarg['domain_server_name']
        self.connections   = kwarg['connection_obj'].connections
        self.logger        = kwarg['connection_obj'].logger
        self.connections.get_vnc_lib_h()
        ipam_fq_name = [u'default-domain',u'%s'%tenant_name,unicode(ipam_name)]
        try:
           self.connections.vnc_lib.network_ipam_read(fq_name=ipam_fq_name)
           self.logger.warn("IPAM: %s already available...skipping create.."%str(ipam_fq_name))
           return
        except NoIdError :
           pass
        domain_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name=[u"default-domain",u"%s"%domain_server_name])
        
        ipam_obj = NetworkIpam(name=ipam_name, parent_type='project',
                           fq_name=ipam_fq_name, network_ipam_mgmt=IpamType("dhcp"))

        vdns_server   = IpamDnsAddressType(virtual_dns_server_name=domain_obj.get_fq_name_str())
        ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=vdns_server)
        ipam_obj.set_network_ipam_mgmt(ipam_mgmt_obj)
        ipam_obj.add_virtual_DNS(domain_obj)
        self.connections.vnc_lib.network_ipam_create(ipam_obj)
      except:
           traceback.print_exc(file=sys.stdout)
           pass

    def create_ipams(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        ipam_count          = tenant_conf.get('ipam,count',None)
        if ipam_count is None:
           return
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index        = get_tenant_index(tenant_conf,tenant_name)
            domain_server_name  = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            ipam_name           = generate_ipam_name(global_conf,tenant_conf,tenant_index)
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['ipam_name']   = ipam_name 
            kwargs['domain_server_name'] = domain_server_name
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_ipam(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def delete(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        ipam_fixture.delete(verify=True)

    @Process.wrapper
    def delete_ipam(self,*arg,**kwarg):

        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name = kwarg['tenant_name']
        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name
        proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
        ipams = self.connections.vnc_lib.network_ipams_list(parent_id=proj_obj.uuid)['network-ipams']
        for ipam in ipams:
            try:
              self.delete(ipam['uuid'])
            except:
              pass

    def delete_ipams(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0 :
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_ipam(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def verify(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        assert ipam_fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = IPAMFixture(connections=self.connections, uuid=uuid)
        return self.fixture

class VN(Base):
    @Process.wrapper
    def list_vn(self,*arg,**kwarg):
       tenant_name_list = kwarg.get('tenant_name_list',None)
       vn_name_prefix   = kwarg.get('vn_name_prefix',None)
       self.connections = kwarg['connection_obj'].connections
       self.logger      = kwarg['connection_obj'].logger
       vnet_list = []
       for tenant_name in tenant_name_list:
         try:
           proj_fq_name = [u'default-domain', u'%s'%tenant_name]
           proj_obj  = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
         except:
           continue
         tenant_id = proj_obj.uuid
         net_list  = self.connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
         for vn in net_list:
            if vn_name_prefix is None or re.search('^%s'%vn_name_prefix,vn['fq_name'][-1]):
               vnet_list.append((tenant_name,vn['uuid'],vn['fq_name']))
       return vnet_list

    def create(self, name, subnets=[], ipam_id=None, external=False,shared=False,disable_gateway=False,rt_number=None,project_obj=None,forwarding_mode=None):
        kwargs = dict()
        kwargs['shared'] = shared
        if ipam_id:
            kwargs['ipam_fq_name'] = IPAM(self.connections).fq_name(ipam_id)
        kwargs['router_external'] = external
        kwargs['rt_number']       = rt_number
        kwargs['disable_gateway'] = disable_gateway
        kwargs['forwarding_mode'] = forwarding_mode
        kwargs['project_obj']     = project_obj
        self.fixture = VNFixture(connections=self.connections, vn_name=name,
                                 subnets=subnets, **kwargs)
        self.fixture.setUp()
        
        uuid = self.fixture.get_uuid()
        return uuid

    @Process.wrapper
    def add_extend_to_pr(self,*arg,**kwarg):

        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        vn_ids           = kwarg['vn_ids']
        fq_name          = kwarg['fq_name']
        pr_obj           = kwarg['pr_obj']

        vn_ref = pr_obj.get_virtual_network_refs() or []
        existing_vn_ids = []

        for vn in vn_ref :
            existing_vn_ids.append(vn['uuid'])

        for i,vn_id in enumerate(vn_ids):
            if vn_id in existing_vn_ids:
               continue
            ref_info = {'to':fq_name[i]}
            ref_info['uuid'] = vn_id
            vn_ref.append(ref_info)

        pr_obj.set_virtual_network_list(vn_ref)

        try:
           self.connections.vnc_lib.physical_router_update(pr_obj)
        except:
           pass

    @Process.wrapper
    def get_vn_ids(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name_list = kwarg['tenant_name_list']
        vn_names_list    = kwarg.get('vn_names_list',[])
        vn_info_dict = {}
        for tenant_name in tenant_name_list:
            try:
              proj_fq_name = [u'default-domain',u'%s'%tenant_name]
              project_obj = self.connections.vnc_lib.project_read(fq_name=proj_fq_name)
            except:
              self.logger.warn("tenant :%s missing..skipping..."%tenant_name)
              continue
            vns = project_obj.get_virtual_networks()
            if not vns:
               continue
            for vn in vns:
                   vn_info_dict[":".join(vn[u'to'])] = vn[u'uuid']
        return vn_info_dict

    @Process.wrapper
    def delete_extend_to_pr(self,*args,**kwarg):

        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        pr_obj           = kwarg['pr_obj']
        vn_list          = kwarg['vn_list']
        vn_ids           = [x[1] for x in vn_list]

        vn_ref = pr_obj.get_virtual_network_refs() or []
        if len(vn_ref) == 0:
           return

        vn_ref_new = []

        for vn in vn_ref :
            if vn['uuid'] not in vn_ids:
               vn_ref_new.append(vn)
        
        pr_obj.set_virtual_network_list(vn_ref_new)

        try:
           self.connections.vnc_lib.physical_router_update(pr_obj)
        except:
           pass

    @Process.wrapper
    def update_pr_objs(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        pr_objs          = kwarg['pr_objs']
        for router_name,pr_obj in pr_objs.iteritems():
            self.connections.vnc_lib.physical_router_update(pr_obj)

    @Process.wrapper
    def delete_pr_extn(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        pr_obj_info      = kwarg['pr_obj_info']
        vn_ids           = kwarg['vn_ids']
        for vn_id in vn_ids:
            vn_obj = self.connections.vnc_lib.virtual_network_read(id=vn_id)
            pr_refs = vn_obj.get_physical_router_back_refs()
            if pr_refs is None:
               continue
            for pr_ref in pr_refs:
               pr_fq_name = pr_ref['to']
               pr_name    = pr_fq_name[1]
               pr_obj     = pr_obj_info[pr_name]
               pr_obj.del_virtual_network(vn_obj)
        for pr_name,pr_obj in pr_obj_info.iteritems():
            try:
               self.connections.vnc_lib.physical_router_update(pr_obj)
            except:
               pass

    def delete_extend_to_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        tenant_count = tenant_conf['tenant,count']
        router_obj   = RouterConfig(None)
        pr_names     = router_obj.retrieve_existing_pr(conn_obj_list=conn_obj_list)
        pr_obj_info  = {}

        for router_name in pr_names:
            pr_obj = self.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
            if pr_obj:
               pr_obj_info[router_name] = pr_obj

        kwargs_list = []
        vn_obj = VN(None)
        vn_list = vn_obj.list_vn(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
        if not vn_list:
           return

        for router_name,pr_obj in pr_obj_info.iteritems():
           kwargs = {}
           kwargs['pr_obj']      = pr_obj
           kwargs['vn_list']     = vn_list
           kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_extend_to_pr(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    @Process.wrapper
    def retrieve_pr_obj(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        router_name = kwarg['router_name']
        pr_fq_name = [u'default-global-system-config', u'%s'%router_name]
        try:
          pr_obj = self.connections.vnc_lib.physical_router_read(fq_name=pr_fq_name)
        except:
          pr_obj = None
        return pr_obj

    @timeit
    def update_extend_to_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])
        pr_obj_list = []
        for router_name in pr_mx_name_list:
            pr_obj = self.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
            if pr_obj:
               pr_obj_list.append(pr_obj)
        if len(pr_obj_list) == 0:
           return
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                vn_index = 0
                vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
                vn_count             = vn_info['count']
                vn_name_pattern      = vn_info['vn,name,pattern']
                extend_to_pr_flag    = vn_info['extend_to_pr_flag']
                for vn_indx in xrange(vn_count):
                   vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_index)
                   vn_index += 1
                   if not extend_to_pr_flag:
                      continue
                   kwargs = {}
                   kwargs['tenant_name'] = tenant_name
                   kwargs['vn_name']     = vn_name
                   kwargs['router_list'] = pr_mx_name_list
                   kwargs['pr_obj_list'] = pr_obj_list
                   kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.add_extend_to_pr(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
 
    @Process.wrapper
    def create_vn(self,*arg,**kwarg):
      try:
        use_fixture     = kwarg.get('use_fixture',False)
        vn_name         = kwarg['vn_name']
        cidr            = kwarg['cidr']
        ipam_name       = kwarg['ipam_name']
        tenant_name     = kwarg['tenant_name']
        disable_gateway = kwarg.get('disable_gateway',False)
        external        = kwarg.get('external_flag',False)
        shared          = kwarg.get('shared_flag',False)
        rt_number       = kwarg.get('rt_number',None)
        asn_number      = kwarg.get('asn_number',None)
        fwd_mode        = kwarg.get('fwd_mode',None)
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        project_fq_name = [u'default-domain',unicode(tenant_name)]
        vn_fq_name      = [u'default-domain',unicode(tenant_name),unicode(vn_name)]
        ipam_fq_name    = [u'default-domain',unicode(tenant_name),unicode(ipam_name)]
        policy_name     = kwarg.get('policy_name',None)
        attach_policy   = kwarg.get('attach_policy',False)
        extend_to_pr    = kwarg.get('extend_to_pr',False)
        pr_obj_list     = kwarg.get('pr_obj_list',[])

        try:
           ipam_obj = self.connections.vnc_lib.network_ipam_read(fq_name=ipam_fq_name)
        except:
           ipam_obj = None  
        
        project_obj = self.connections.vnc_lib.project_read(fq_name=project_fq_name)
        project_obj.project_fq_name=project_fq_name
        
        try:
           vn_obj = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
           print "INFO: VN:%s already existing..skipping create"%str(vn_fq_name)
           return (extend_to_pr,vn_fq_name,vn_obj.uuid)
        except:
           pass
        if use_fixture:
           ipam_id = ipam_obj.uuid
           subnets = [{'cidr':cidr,'name':vn_name+"_subnet"}]
           self.create(vn_name,subnets,ipam_id,external,shared,disable_gateway,rt_number,project_obj,fwd_mode)
           vn_obj = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
           return (extend_to_pr,vn_fq_name,vn_obj.uuid)
        else:
           vn_obj = VirtualNetwork(vn_name, parent_obj=project_obj,router_external=external,is_shared=shared,forwarding_mode=fwd_mode,disable_gateway=disable_gateway)
           network,prefix = cidr.split("/")
           ipam_sn_lst = []
           ipam_sn = IpamSubnetType(subnet=SubnetType(network, int(prefix)),addr_from_start=True)
           ipam_sn_lst.append(ipam_sn)
           vn_obj.add_network_ipam(ipam_obj,VnSubnetsType(ipam_sn_lst))
           if asn_number and rt_number:
              route_targets = RouteTargetList([":".join(["target",str(asn_number),str(rt_number)])])
              vn_obj.set_route_target_list(route_targets)
           vn_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
           vn_obj_properties.set_forwarding_mode(fwd_mode)
           vn_obj.set_virtual_network_properties(vn_obj_properties)
           if attach_policy:
              try:
                 policy_fq_name = [u'default-domain',u'%s'%tenant_name,unicode(policy_name)]
                 policy_obj = self.connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
                 vn_obj.add_network_policy(policy_obj,VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0)))
              except NoIdError:
                 pass
           try:
              self.connections.vnc_lib.virtual_network_create(vn_obj)
           except RefsExistError:
              pass

           vn_obj = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
           return (extend_to_pr,vn_fq_name,vn_obj.uuid)
         
      except:
           traceback.print_exc(file=sys.stdout)
           pass

    @timeit
    def create_vns(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        project_obj = conn_obj_list[0]
        already_allocated_cidr,existing_vns = project_obj.configured_cidr(conn_obj_list=conn_obj_list)
        existing_vn_list       = project_obj.retrieve_vn_list(conn_obj_list=conn_obj_list)
        already_allocated_rt   = project_obj.configured_rt_numbers(conn_obj_list=conn_obj_list)

        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])

        pr_obj_list = []
        for router_name in pr_mx_name_list:
            pr_obj = self.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
            if pr_obj:
               pr_obj_list.append(pr_obj)

        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            ipam_name    = generate_ipam_name(global_conf,tenant_conf,tenant_index)
            policy_name  = generate_policy_name(global_conf,tenant_conf,tenant_index)
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                vn_index        = 0
                vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
                fwd_mode        = vn_info.get('fwd_mode')
                vn_count        = vn_info['count']
                vn_name_pattern = vn_info['vn,name,pattern']
                vn_type         = get_vn_type(vn_name_pattern) 
                external_flag   = vn_info['external_flag']
                extend_to_pr_flag    = vn_info['extend_to_pr_flag']
                attach_policy_flag   = vn_info.get('attach_policy',False)
                for vn_indx in xrange(vn_count):
                    vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_index)
                    vn_index += 1
                    if ['default-domain',tenant_name,vn_name] in existing_vns:
                       continue
                    cidr    = generate_cidr(tenant_name,vn_type,already_allocated_cidr)
                    already_allocated_cidr.append(cidr)
                    rt_number    = vn_info.get('route_target,rt_number') 
                    asn_number   = vn_info.get('route_target,asn') 
                    if rt_number:
                       rt_number = generate_rt_number(already_allocated_rt)
                       already_allocated_rt.append(rt_number)
                    else:
                       rt_number = None
                    kwarg = {}
                    kwarg['cidr']            = cidr 
                    kwarg['ipam_name']       = ipam_name
                    kwarg['tenant_name']     = tenant_name
                    kwarg['vn_name']         = vn_name
                    kwarg['asn_number']      = asn_number
                    kwarg['rt_number']       = rt_number
                    kwarg['external_flag']   = external_flag
                    kwarg['disable_gateway'] = False
                    kwarg['fwd_mode']        = fwd_mode
                    kwarg['policy_name']     = policy_name
                    kwarg['attach_policy']   = attach_policy_flag
                    kwarg['extend_to_pr']    = extend_to_pr_flag
                    kwarg['pr_obj_list']     = pr_obj_list
                    kwargs_list.append(kwarg)

        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        extend_flag_vn_ids = self.create_vn(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
        print "extend_flag_vn_ids:",extend_flag_vn_ids
       
        vn_ids    = []
        fq_name_l = []
        for extend_flag_vn_id in extend_flag_vn_ids: 
            if extend_flag_vn_id is None or extend_flag_vn_id is bool:
               continue
            extend_flag,fq_name,vn_id = extend_flag_vn_id
            if extend_flag:
               vn_ids.append(vn_id)
               fq_name_l.append(fq_name)

        kwargs_list = []
        for pr_obj in pr_obj_list:
            kwargs = {}
            kwargs['pr_obj'] = pr_obj
            kwargs['vn_ids'] = vn_ids
            kwargs['fq_name'] = fq_name_l
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.add_extend_to_pr(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def add_policy(self,policy_obj):
        self.fixture.bind_policies([policy_obj.policy_fq_name], self.vn_id)

    def delete_policy(self,policy_obj):
        self.fixture.unbind_policies(self.vn_id,[policy_obj.policy_fq_name])

    def delete(self, uuid, subnets=[]):
        if not subnets:
            subnets = self.get_subnets(uuid)
        vn_fixture = self.get_fixture(uuid=uuid, subnets=subnets)
        vn_fixture.delete(verify=True)

    @Process.wrapper
    def delete_vn_by_name_process(self,*arg,**kwarg):
        tenant_name      = kwarg['tenant_name']
        vn_name          = kwarg['vn_name']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        try:
           obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
           tenant_id = obj.uuid
        except:
           return
        net_list = self.connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
        vn_id = None
        for net in net_list:
           if net['fq_name'] == [u'default-domain', u'%s'%tenant_name, u'%s'%vn_name] :
              vn_id = net['uuid']
              break
        if vn_id:  
           try:
             self.delete(vn_id)
           except:
             pass

    def delete_vn_by_name(self,args,kwargs):
        tenant_name,vn_name = args
        p = mp.Process(target=self.delete_vn_by_name_process,args=(tenant_name,vn_name))
        p.start()
        p.join()

    @timeit
    @Process.wrapper
    def delete_vn(self,*arg,**kwarg):
        tenant_name = kwarg['tenant_name']
        vn_id       = kwarg['vn_id']
        vn_fq_name  = kwarg['vn_fq_name']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        pr_obj_info      = kwarg.get('pr_obj_info',None)
        try:
           vn_obj = self.connections.vnc_lib.virtual_network_read(id=vn_id)
        except NoIdError:
           return

        try:
           self.connections.vnc_lib.virtual_network_delete(id=vn_id)
        except:
           traceback.print_exc(file=sys.stdout)
           pass

    def delete_vns(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        vn_list = self.list_vn(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
        if not vn_list:
           return True

        router_obj   = RouterConfig(None)
        pr_names     = router_obj.retrieve_existing_pr(conn_obj_list=conn_obj_list)
        pr_obj_info  = {}
        for router_name in pr_names:
            pr_obj = self.retrieve_pr_obj(conn_obj_list=conn_obj_list,router_name=router_name)
            if pr_obj:
               pr_obj_info[router_name] = pr_obj

        kwargs_list = []
        for vn in vn_list:
            tenant_name,vn_id,vn_fq_name = vn
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['vn_id']       = vn_id
            kwargs['vn_fq_name']  = vn_fq_name
            kwargs['pr_obj_info'] = pr_obj_info
            kwargs_list.append(kwargs) 
        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_vn(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def get_subnets(self, uuid):
        quantum_h = self.connections.get_network_h()
        return quantum_h.get_subnets_of_vn(uuid)

    def verify(self, uuid, subnets=[]):
        if not subnets:
            subnets = self.get_subnets(uuid)
        vn_fixture = self.get_fixture(uuid=uuid, subnets=subnets)
        assert vn_fixture.verify_on_setup()

    def get_fixture(self, uuid, subnets=[]):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = VNFixture(connections=self.connections,
                                     uuid=uuid, subnets=subnets)
        return self.fixture

def filter_vms_in_vn(vms,vn_names):

    vm_list = []
    for vm in vms:
        vm_iface_names = vm.networks.keys()
        if set(vm_iface_names).intersection(set(vn_names)):
           vm_list.append((vm,list(set(vm_iface_names).intersection(set(vn_names)))[0]))
    return vm_list

class VM(Base):

    @Process.wrapper
    def retrieve_vm_info(self,*arg,**kwarg):
      try:  
        tenant_name_list = kwarg['tenant_name_list']
        tenant_conf      = kwarg['tenant_conf']
        global_conf      = kwarg['global_conf']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.connections.orch = self.connections.get_orch_h()
        tenant_info  = {}
        fips         = self.connections.vnc_lib.floating_ips_list()['floating-ips']
        fip_info     = {}
        fip_obj_info = {}
        for fip in fips:
            domain,t_name,vn_name,poll_name,fip_id=fip['fq_name']
            fip_obj = self.connections.vnc_lib.floating_ip_read(id=fip_id)
            fip_obj_info[fip_id] = fip_obj

        vmi_obj_info = {}
        for fip_id,fip_obj in fip_obj_info.iteritems():
            try:
               iface_id  = fip_obj.virtual_machine_interface_refs[0]['uuid']
            except:
               continue
            iface_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=iface_id)
            vmi_obj_info[iface_id] = iface_obj
            mac_addr  = iface_obj.get_virtual_machine_interface_mac_addresses().get_mac_address()[0]
            li_ref    = iface_obj.get_logical_interface_back_refs() or []
            if li_ref:
               li_name = ":".join(li_ref[0]['to'])
               fip_info[li_name] = fip_obj.get_floating_ip_address()
            else:
               fip_info[mac_addr] = fip_obj.get_floating_ip_address()
    
        qfx_config = global_conf['pr_qfx']
        physical_server_mac_list = []
        physical_server_ip_list = []
        for qfx in qfx_config:
            bms_servers = qfx['bms']
            for bms in bms_servers:
                physical_server_mac_list.append(bms['physical_server_mac'])
                physical_server_ip_list.append(bms['physical_server_mgmt_ip'])
    
        virtual_ips = self.connections.vnc_lib.virtual_ips_list()['virtual-ips']
        for tenant_name in tenant_name_list:
           try:
              proj_fq_name = [u'default-domain', u'%s'%tenant_name]
              proj_obj  = self.connections.vnc_lib.project_read(fq_name=proj_fq_name)
           except:
              continue
           tenant_id = proj_obj.uuid
           vms_all   = self.connections.orch.get_vm_list(project_id=tenant_id)
           net_list  = self.connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
           vmis_t    = self.connections.vnc_lib.virtual_machine_interfaces_list(parent_id=tenant_id)['virtual-machine-interfaces']
           vmis_filtered = []
           for vmi in vmis_t:
              if vmi_obj_info.has_key(vmi['uuid']):
                 vmi_obj = vmi_obj_info[vmi['uuid']]
              else:
                 vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                 vmi_obj_info[vmi['uuid']] = vmi_obj
              li_ref  = vmi_obj.get_logical_interface_back_refs()
              if li_ref is not None:
                 vmis_filtered.append(vmi)
           # BUG: parent_fq_name does not filter correctly.
           #virtual_ips = obj.connections.vnc_lib.virtual_ips_list(parent_fq_name=['default-domain',tenant_name])['virtual-ips']
           vip_info_list = []
           vn_group_info = {}
           for virtual_ip in virtual_ips:
               dom,t_name,vip_name = virtual_ip['fq_name']
               if t_name != tenant_name:
                  continue
               vip_id  = virtual_ip['uuid']
               vip_obj = self.connections.vnc_lib.virtual_ip_read(id=vip_id)
               vm_interfaces = vip_obj.get_virtual_machine_interface_refs()
               vip_prop      = vip_obj.virtual_ip_properties
               vip_addr      = vip_prop.get_address()
               protocol_port = vip_prop.protocol_port
               for vmi in vm_interfaces:
                   vmi_id    = vmi['uuid']
                   if vmi_obj_info.has_key(vmi['uuid']):
                      vmi_obj = vmi_obj_info[vmi['uuid']]
                   else:
                      vmi_obj   = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
                      vmi_obj_info[vmi_id] = vmi_obj
                   fips_ref  = vmi_obj.get_floating_ip_back_refs()
                   vn_ref    = vmi_obj.get_virtual_network_refs()[0]
                   dom,t_name,vn_name   = vn_ref['to']
                   vn_name = vn_name.split(".")[-1] # tenant5.test_id1.Private_LB_VIP_VN0
                   instance_ip_ref = vmi_obj.get_instance_ip_back_refs()
                   
                   if fips_ref is None:
                      fip_addr = None
                   else:
                      #for fip in fips_ref:
                      fip      = fips_ref[0]
                      fip_id   = fip['uuid']
                      fip_obj  = self.connections.vnc_lib.floating_ip_read(id=fip_id)
                      fip_addr = fip_obj.get_floating_ip_address()
                      #vip_addr = fip_obj.floating_ip_fixed_ip_address
    
                   vip_info = {}
                   vip_info['ip_addr,data'] = vip_addr
                   vip_info['vip,protocol_port'] = protocol_port
                   vip_info['ip_addr,mgmt'] = None
                   vip_info['name']         = None
                   vip_info['is_bms']       = False
                   vip_info['ip_addr,fip']  = fip_addr 
                   if not vn_group_info.has_key(vn_name):
                      vn_group_info[vn_name] = [vip_info]
                   else:
                      vn_group_info[vn_name].append(vip_info)
           mgmt_vn_name = generate_mgmt_vn_name(global_conf,tenant_conf)
           for vn in net_list:
               vn_name = vn['fq_name'][-1]
               if re.search('Private_LB_VIP_VN',vn_name):
                  continue
               vms_filtered  = filter_vms_in_vn(vms_all,[vn_name])
               vmis_l = []
               vm_info_list = []
               for vmi in vmis_filtered:
                   if vmi_obj_info.has_key(vmi['uuid']):
                      vmi_obj = vmi_obj_info[vmi['uuid']]
                   else:
                      vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                      vmi_obj_info[vmi['uuid']] = vmi_obj
                   dom,t_name,vmi_vn_name = vmi_obj.get_virtual_network_refs()[0]['to']
                   if vmi_vn_name == vn_name:
                      inst_ip_id    = vmi_obj.get_instance_ip_back_refs()[0]['uuid']
                      inst_ip       = self.connections.vnc_lib.instance_ip_read(id=inst_ip_id)
                      mac_obj       = vmi_obj.get_virtual_machine_interface_mac_addresses()
                      data_mac_addr = mac_obj.get_mac_address()[0]
                      mac_indx      = physical_server_mac_list.index(data_mac_addr)
                      phy_ip_addr   = physical_server_ip_list[mac_indx]
                      li_ref   = vmi_obj.get_logical_interface_back_refs()[0]
                      li_obj   = self.connections.vnc_lib.logical_interface_read(id=li_ref['uuid'])
                      li_name  = ":".join(li_ref['to'])
                      vlan_id  = li_obj.logical_interface_vlan_tag
                      vmi_info = {}
                      vmi_info['name']         = vmi_obj.display_name
                      vmi_info['ip_addr,mgmt'] = phy_ip_addr
                      vmi_info['ip_addr,data'] = inst_ip.instance_ip_address
                      vmi_info['ip_addr,fip']  = fip_info.get(li_name,None)
                      vmi_info['vlan']   = vlan_id
                      vmi_info['is_bms'] = True
                      vm_info_list.append(vmi_info)
               for vm,vn_name in vms_filtered:
                       addr    = vm.addresses
                       vm_info = {}
                       vm_info['name']         = vm.name
                       vm_info['ip_addr,mgmt'] = addr[mgmt_vn_name] [0]['addr']
                       vm_info['ip_addr,data'] = addr[vn_name][0]['addr']
                       data_mac_addr           = addr[vn_name][0]['OS-EXT-IPS-MAC:mac_addr']
                       vm_info['ip_addr,fip']  = fip_info.get(data_mac_addr,None)
                       vm_info['vlan']   = None
                       vm_info['is_bms'] = False
                       vm_info_list.append(vm_info) 
               vn_name = vn_name.split(".")[-1]
               vn_group_info[vn_name] = vm_info_list
           tenant_info[tenant_name] = vn_group_info
        return tenant_info
      except:
        traceback.print_exc(file=sys.stdout)

    @Process.wrapper
    def list_vmis(self,*arg,**kwarg):
        tenant_name_list  = kwarg['tenant_name_list']
        lr_back_ref_check = kwarg.get('lr_back_ref_check',False)
        self.connections  = kwarg['connection_obj'].connections
        self.logger       = kwarg['connection_obj'].logger
        vmis_filtered = []
        vmis_list     = self.connections.vnc_lib.virtual_machine_interfaces_list()['virtual-machine-interfaces'] or []
        for vmi in vmis_list:
            try:
              vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
            except:
              pass
            dom,t_name,name = vmi_obj.fq_name
            if t_name not in tenant_name_list:
               continue
            if lr_back_ref_check:
               li_ref  = vmi_obj.get_logical_interface_back_refs()
               if li_ref is not None:
                  vmis_filtered.append((vmi,li_ref))
            else:
               vmis_filtered.append((vmi,None))
        return vmis_filtered

    @Process.wrapper
    def list_vms(self,*arg,**kwarg):
      try:
        tenant_name_list = kwarg['tenant_name_list']
        vn_list          = kwarg.get('vn_list',[])
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        if len(tenant_name_list) == 0:
           return
        self.connections.orch = self.connections.get_orch_h()
        vms_list = []
        for tenant_name in tenant_name_list:
          try:
            proj_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
          except:
            continue
          tenant_id = proj_obj.uuid
          vms_all = self.connections.orch.get_vm_list(project_id=tenant_id) or []
          if len(vn_list):
             vms_filtered = filter_vms_in_vn(vms_all,vn_list)
          else:
             vms_filtered = [(vm,"") for vm in vms_all]
          for vm_obj,vn_name in vms_filtered:
            vm = {}
            vm['tenant_name'] = tenant_name
            vm['vn_name']     = vn_name
            vm['vm_name']     = vm_obj.name
            vm['id']          = vm_obj.id
            vm['ip']          = vm_obj.addresses
            vm['networks']    = vm_obj.networks
            vms_list.append(vm)
        return vms_list
      except:
        traceback.print_exc(file=sys.stdout)

    def create(self, name, vn_ids, image='ubuntu',userdata=None):
        self.fixture = VMFixture(connections=self.connections, vn_ids=vn_ids, vm_name=name, image_name=image,userdata=userdata)
        self.fixture.flavor = "m1.small"
        self.fixture.setUp()
        #self.fixture.wait_till_vm_is_up()
        return self.fixture.get_uuid()

    @Process.wrapper
    def create_vm(self,*arg,**kwarg):
        vm_name      = kwarg['vm,name']
        data_vn_name = kwarg['data_vn_name']
        mgmt_vn_name = kwarg['mgmt_vn_name']
        tenant_name  = kwarg['tenant_name']
        image_name   = kwarg['image_name']
        userdata    = kwarg.get('userdata',None)
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name
        quantum_h = self.connections.get_network_h()
        self.nova_h = self.connections.nova_h
        servers = self.nova_h.get_vm_list()
        server_already_exist = False

        projects_list = self.connections.vnc_lib.projects_list()['projects']
        uuid = None
        admin_uuid = None
        for proj in projects_list :
           fq_name = proj['fq_name']
           if fq_name == [u'default-domain', u'%s'%tenant_name]:
              uuid = proj['uuid']
           elif fq_name == [u'default-domain', u'admin']:
              admin_uuid = proj['uuid']
        data_vn_obj  = quantum_h.get_vn_obj_if_present(data_vn_name,uuid)
        mgmt_vn_obj  = quantum_h.get_vn_obj_if_present(mgmt_vn_name,admin_uuid) 
 
        for server in servers:
            if server.name == unicode(vm_name) and server.tenant_id == re.sub("-","",uuid):
               server_already_exist = True
               break
        if server_already_exist :
            print "VM: %s already existing..skipping create.."%vm_name
            return

        uid = self.create(vm_name,[data_vn_obj['network']['id'],mgmt_vn_obj['network']['id']],image_name,userdata)
        return 

    @timeit
    def create_vms(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list  = []   
        mgmt_vn_name = global_conf['mgmt,vn_name']
        for tenant_name in tenant_name_list :
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            vm_index   = 0  
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
              vn_index = 0 
              vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
              vn_name_pattern      = vn_info['vn,name,pattern']
              for vn_indx  in xrange(vn_info['count']):
                 vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_indx)
                 vn_index += 1
                 if not vn_info.has_key('vm,count') :
                    continue
                 vm_count        = vn_info['vm,count']
                 vm_name_pattern = vn_info['vm,name_pattern']
                 image           = vn_info['vm,glance_image']
                 for vm_indx in xrange(vm_count):
                     vm_name              = re.sub('QQQ',str(vm_index),vm_name_pattern)
                     conf                 = {}
                     conf['tenant_name']  = tenant_name
                     conf['vm,name']      = vm_name
                     conf['data_vn_name'] = vn_name
                     conf['mgmt_vn_name'] = mgmt_vn_name
                     conf['image_name']   = image
                     vm_index += 1
                     kwargs_list.append(conf)
                 '''
                 bgp_vm_count        = vn_info['bgp_vm,count']
                 bgp_vm_name_pattern = vn_info['bgp_vm,name_pattern']
                 image               = vn_info['bgp_vm,glance_image']
                 bgp_user_data       = vn_info['bgp_vm,userdata']
                 for vm_indx in xrange(bgp_vm_count):
                     vm_name              = re.sub('QQQ',str(vm_index),bgp_vm_name_pattern)
                     conf                 = {}
                     conf['tenant_name']  = tenant_name
                     conf['vm,name']      = vm_name
                     conf['data_vn_name'] = vn_name
                     conf['mgmt_vn_name'] = mgmt_vn_name
                     conf['image_name']   = image
                     conf['userdata']     = bgp_user_data
                     vm_index += 1
                     kwargs_list.append(conf)
                 '''
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_vm(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def get_vm_creds(self):
        return (self.fixture.get_vm_username(),
                self.fixture.get_vm_password())

    def delete(self, uuid, vn_ids=[],verify=False):
        vm_fixture = self.get_fixture(uuid=uuid, vn_ids=vn_ids)
        vm_fixture.delete(verify=verify)

    @Process.wrapper
    def delete_vmi(self,*arg,**kwarg):
        vmi_id = kwarg['vmi_id']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.logger.info("deleting VMI : %s"%vmi_id)
        try:
           vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
        except NoIdError:
           return
        inst_ips = vmi_obj.get_instance_ip_back_refs() or []
        for inst_ip in inst_ips:
            inst_ip_id = inst_ip['uuid']
            try:
              self.connections.vnc_lib.instance_ip_delete(id=inst_ip_id)
            except:
              continue
        li_refs = vmi_obj.get_logical_interface_back_refs() or []
        for li in li_refs:
            try:
              li_obj = self.connections.vnc_lib.logical_interface_read(id=li['uuid'])
              li_obj.del_virtual_machine_interface(vmi_obj)
              self.connections.vnc_lib.logical_interface_update(li_obj)
            except:
              pass
        try:
          self.connections.vnc_lib.virtual_machine_interface_delete(vmi_obj.fq_name)
        except:
          pass

    @retry(tries=10,delay=5)
    @Process.wrapper
    def delete_vm(self,*arg,**kwarg):
        tenant_name = kwarg['tenant_name']
        vm_id       = kwarg['vm_id']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.logger.info("DEBUG: deleting VM : %s"%vm_id)
        try:
           vm_obj = self.connections.vnc_lib.virtual_machine_read(id=vm_id)
        except NoIdError:
           print "DEBUG: VM:%s not found...skipping delete"%vm_id
           return
        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name
        try:
          self.delete(vm_id)
          return True
        except:
          return False

    def delete_vmis(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        vmis_list = self.list_vmis(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        if not vmis_list:
           return
           
        kwargs_list = []
        for vmi,li_ref in vmis_list:
            kwargs = {}
            kwargs['vmi_id'] = vmi['uuid']
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_vmi(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def delete_vms(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        vms_list = []
        ret = self.list_vms(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        if ret:
           vms_list.extend(ret)
        if len(vms_list) == 0:
           return True 
        kwargs_list = []
        for vm in vms_list:
          kwargs = {}
          kwargs['tenant_name']     = vm['tenant_name']
          kwargs['vm_id']           = vm['id']
          kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_vm(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def verify(self, uuid, vn_ids=[], username='ubuntu', password='ubuntu'):
        vm_fixture = self.get_fixture(uuid=uuid, vn_ids=vn_ids)
        vm_fixture.set_vm_creds(username, password)
        assert vm_fixture.verify_on_setup()

    def vm_ip(self, uuid, vn_name=None):
        orch_h = self.connections.get_orch_h()
        vm_obj = orch_h.get_vm_by_id(vm_id=uuid)
        return orch_h.get_vm_ip(vm_obj, vn_name)

    def vm_name(self, uuid):
        orch_h = self.connections.get_orch_h()
        vm_obj = orch_h.get_vm_by_id(vm_id=uuid)
        return vm_obj.name

    def ping(self, uuid, dst, username='ubuntu', password='ubuntu'):
        vm_fixture = self.get_fixture(uuid=uuid)
        vm_fixture.set_vm_creds(username, password)
        return vm_fixture.ping_to_ip(dst)

    def copy_file_to_vm(self, uuid, localfile, dst='/tmp/',
                        username='ubuntu', password='ubuntu'):
        vm_fixture = self.get_fixture(uuid=uuid)
        vm_fixture.set_vm_creds(username, password)
        vm_fixture.copy_file_to_vm(localfile, dst)

    def get_fixture(self, uuid, vn_ids=[]):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = VMFixture(connections=self.connections,
                                     uuid=uuid, vn_ids=vn_ids)
        return self.fixture

    def tcpecho(self, uuid, dst, dport=50000,
                username='ubuntu', password='ubuntu'):
        vm_fixture = self.get_fixture(uuid=uuid)
        tcpclient = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 '../', 'tcutils', 'tcpechoclient.py')
        self.copy_file_to_vm(uuid, tcpclient, '/tmp/',
                             username, password)
        cmd = 'python /tmp/tcpechoclient.py '+\
              ' --servers %s --dports %s --count 5'%(dst, dport)
        output = vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        if not output or not output[cmd]:
             print 'retry to workaround fab issues'
             output = vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert output[cmd], 'Connection timedout'
        exp = 'sent and received 5'
        if exp not in output[cmd]:
            print output[cmd]
            assert False, 'TCP Echo failure'
        return True

    def run_cmd(self, uuid, cmd, sudo=False, daemon=False):
        vm_fixture = self.get_fixture(uuid)
        vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=sudo, as_daemon=daemon)

class FloatingIPPool(Base):
    def create(self, vn_id, name=None):
        self.fixture = FloatingIPFixture(connections=self.connections,
                                         pool_name=name, vn_id=vn_id)
        self.fixture.setUp()
        return self.fixture.get_uuid()

    @Process.wrapper
    def create_fip_pool(self,*arg,**kwarg):
        vn_id         = kwarg['vn_id']
        fip_pool_name = kwarg['fip,pool,name']
        tenant_name   = kwarg['tenant,name']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.create(vn_id,fip_pool_name)
      
    @timeit
    def create_fip_pools(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        public_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_vn_group_index = vn_group_indx
            break
        if not public_vn_group_index:
           return
        vn_info_dict = {}
        kwargs_list = []
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
        if ret:
           vn_info_dict.update(ret)
        for tenant_name in tenant_name_list:
            tenant_indx            = get_tenant_index(tenant_conf,tenant_name)
            vn_info                = tenant_conf['tenant,vn_group_list'][public_vn_group_index]
            fip_gw_vn_name_pattern = vn_info['vn,name,pattern']
            fip_gw_vn_count        = vn_info['count']
            fip_gw_vn_names        = [generate_vn_name(global_conf,tenant_conf,tenant_indx,fip_gw_vn_name_pattern,vn_indx) for vn_indx in xrange(fip_gw_vn_count)]
            fip_pool_name_pattern  = tenant_conf.get('fip,name',None)
            if fip_pool_name_pattern is None:
               return 
            fip_pool_name_list     = [generate_fip_pool_name(global_conf,tenant_conf,tenant_indx,pool_indx) for pool_indx in xrange(fip_gw_vn_count)]
            for indx,pool_name in enumerate(fip_pool_name_list):
                kwargs = {}
                kwargs['tenant,name']   = tenant_name
                kwargs['fip,pool,name'] = fip_pool_name_list[indx]
                kwargs['vn_id']         = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,fip_gw_vn_names[indx])]
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_fip_pool(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
 
    def delete(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        fip_fixture.delete(verify=True)

    @Process.wrapper
    def delete_fip_pool(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name   = kwarg['tenant,name']
        proj_fq_name  = [u'default-domain',u'%s'%tenant_name]
        admin_proj    = self.connections.vnc_lib.project_read(fq_name=['default-domain','admin'])
        project_obj   = self.connections.vnc_lib.project_read(fq_name=proj_fq_name)
        fip_pools     = self.connections.vnc_lib.floating_ip_pools_list()['floating-ip-pools']
        try:
          for fip_pool in fip_pools: 
            fip_domain,fip_tenant_name,fip_vn_name,fip_pool_name = fip_pool[u'fq_name']  
            if fip_tenant_name != unicode(tenant_name):
               continue
            try:
              pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool[u'fq_name'])
            except:
              continue
            fips = pool_obj.get_floating_ips() or []
            for fip in fips:
                try:
                  fip_obj = self.connections.vnc_lib.floating_ip_read(id=fip['uuid'])
                except:
                  continue
                vmis = fip_obj.get_virtual_machine_interface_refs() or []
                for vmi in vmis:
                  try:
                    vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                  except:
                    continue
                  fip_obj.del_virtual_machine_interface(vmi_obj)
                try:
                  self.connections.vnc_lib.floating_ip_delete(id=fip_obj.uuid)
                except:
                  pass
            project_obj.del_floating_ip_pool(pool_obj)
            self.connections.vnc_lib.project_update(project_obj)
            admin_proj.del_floating_ip_pool(pool_obj)
            self.connections.vnc_lib.project_update(admin_proj)
            self.connections.vnc_lib.floating_ip_pool_delete(id=pool_obj.uuid)
        except:
            traceback.print_exc(file=sys.stdout)

    @timeit
    def delete_fip_pools(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs      = {}
            kwargs['tenant,name']   = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_fip_pool(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    @Process.wrapper
    def associate_fip(self,*arg,**kwarg):
        tenant_name    = kwarg['tenant_name']
        fip_pool_name  = kwarg['fip_pool_name']
        vm_id          = kwarg['vm_id']
        vn_id          = kwarg['private_vn_id']
        fip_gw_vn_name = kwarg['fip_gw_vn_name']
        fip_gw_vn_id   = kwarg['fip_gw_vn_id']
        username       = "ubuntu"
        password       = "ubuntu"

        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger

        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name

        # delete default-fip-pool
        try:
           pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=[u'default-domain', u'%s'%tenant_name, u'%s'%fip_gw_vn_name, u'floating-ip-pool'])
           project_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
           project_obj.del_floating_ip_pool(pool_obj)
           self.connections.vnc_lib.project_update(project_obj)
           self.delete(pool_obj.uuid)
        except NoIdError:
           self.logger.warn("FIP pool:%s not found..skipping delete"%fip_pool_name)
        # delete default-fip-pool

        fip_pool_fq_name = [u'default-domain', u'%s'%tenant_name,\
                                u'%s'%fip_gw_vn_name, u'%s'%fip_pool_name]
        fip_pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool_fq_name)
        fip_pool_id  = fip_pool_obj.uuid
        self.fixture = self.get_fixture(uuid=fip_pool_id)
        self.project_name = tenant_name
        return self.fixture.create_and_assoc_fip(fip_pool_vn_id=fip_gw_vn_id,vm_id=vm_id,vn_id=vn_id)

    @timeit
    def associate_fips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        vn_index_replace_str      = tenant_conf['vn,index,replace_str']
        public_fip_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_fip_vn_group_index = vn_group_indx
        if public_fip_vn_group_index == None :
           return
        vn_info_dict = {}
        vn_obj = VN(None)
        ret    = vn_obj.get_vn_ids(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        if ret:
           vn_info_dict.update(ret)
        fip_gw_vn_count          = tenant_conf['fip,gw_vn_count']
        fip_gw_vn_name_pattern   = tenant_conf['fip,gw_vn_name']
        fip_pool_name_pattern    = tenant_conf['fip,name']
        kwargs_list = []
        vm_obj = VM(None)
        for tenant_name in tenant_name_list:
            tenant_indx         = get_tenant_index(tenant_conf,tenant_name)
            fip_gw_vn_name_list = [generate_vn_name(global_conf,tenant_conf,tenant_indx,fip_gw_vn_name_pattern,vn_indx) for vn_indx in xrange(fip_gw_vn_count)]
            fip_pool_name_list  = [generate_fip_pool_name(global_conf,tenant_conf,tenant_indx,pool_indx) for pool_indx in xrange(fip_gw_vn_count)]
            fip_gw_vn_name = fip_gw_vn_name_list[0]
            fip_pool_name  = fip_pool_name_list[0]
            fip_gw_vn_id   = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,fip_gw_vn_name)]

            for vn_info in tenant_conf['tenant,vn_group_list']:
                fip_associate_required = vn_info.get('attach_fip',None)
                if not fip_associate_required:
                   continue
                private_vn_count = vn_info['count']
                vn_name_pattern  = vn_info['vn,name,pattern']
                vn_names_list    = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(private_vn_count)]
                
                vm_list = vm_obj.list_vms(conn_obj_list=conn_obj_list,tenant_name_list=[tenant_name],vn_list=vn_names_list)
                if not vm_list:
                   continue
                for vm in vm_list:
                    tenant_name = vm['tenant_name']
                    vn_name     = vm['vn_name']
                    if vn_name == "":
                       private_vn_id = None
                    else:
                       private_vn_id = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,vn_name)]
                    kwargs = {}
                    kwargs['tenant_name']      = tenant_name
                    kwargs['private_vn_id']    = private_vn_id
                    kwargs['vm_id']            = vm['id']
                    kwargs['fip_pool_name']    = fip_pool_name
                    kwargs['fip_gw_vn_id']     = fip_gw_vn_id
                    kwargs['fip_gw_vn_name']   = fip_gw_vn_name
                    kwargs_list.append(kwargs)
        
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.associate_fip(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def disassociate_fip(self, uuid, fip_id):
        self.fixture = self.get_fixture(uuid=uuid)
        self.fixture.disassoc_and_delete_fip(fip_id)

    def get_fip_from_id(self, fip_id):
        quantum_h = self.connections.get_network_h()
        return quantum_h.get_floatingip(fip_id)['floatingip']['floating_ip_address']

    def verify_fip(self, uuid, fip_id, vm_id, vn_ids, vm_connections):
        fip_fixture = self.get_fixture(uuid=uuid)
        fvn_fixture = VNFixture(connections=self.connections,
                                uuid=fip_fixture.get_vn_id())
        vm_fixture = VMFixture(connections=vm_connections, uuid=vm_id, vn_ids=vn_ids)
        assert fip_fixture.verify_fip(fip_id, vm_fixture, fvn_fixture)

    def verify_no_fip(self, uuid, fip_id, vm_id, fip=None):
        fip_fixture = self.get_fixture(uuid=uuid)
        fvn_fixture = VNFixture(connections=self.connections,
                                uuid=fip_fixture.get_vn_id())
        assert fip_fixture.verify_no_fip(fip_id, fvn_fixture, fip)

    def verify(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        assert fip_fixture.verify_on_setup()

    def get_associated_fips(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        return fip_fixture.get_associated_fips()

    def get_fip_pool_id(self, fip_id):
        vnc = self.connections.get_vnc_lib_h().get_handle()
        return vnc.floating_ip_read(id=fip_id).parent_uuid

    def get_fixture(self, uuid):
         if not getattr(self, 'fixture', None):
             assert uuid, 'ID cannot be None'
             self.fixture = FloatingIPFixture(connections=self.connections, uuid=uuid)
         return self.fixture

class LogicalRouterConfig(Base):
    @Process.wrapper
    def get_router_id(self,*arg,**kwarg):
        
        connection_obj   = kwarg.pop('connection_obj')
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        return_value = {}
        for tenant_name,route_name_list in kwarg.iteritems():
            for router_name in route_name_list:
                router_fq_name = [u'default-domain',u'%s'%tenant_name,unicode(router_name)]
                try:
                  router_obj = self.connections.vnc_lib.logical_router_read(fq_name=router_fq_name)
                  return_value[router_name] = router_obj.uuid
                except:
                  pass
        return return_value

    def create(self, name, tenant_id,vn_ids=[], gw=None):
        quantum_h   = self.connections.get_network_h()
        response    = quantum_h.check_and_create_router(name,tenant_id)
        self.uuid   = response['id']
        self.fqname = response['contrail:fq_name']
        if gw:
            self.set_gw(self.uuid, gw)
        for vn_id in vn_ids:
            self.attach_vn(self.uuid, vn_id)
        return self.uuid

    @Process.wrapper
    def create_logical_router(self,*arg,**kwarg):
        tenant_name   = kwarg['tenant_name']
        router_name   = kwarg['router_name']
        gw            = kwarg['gw_nw']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        proj_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',unicode(tenant_name)])
        tenant_id = proj_obj.uuid
        try:
          self.create(router_name,tenant_id,gw=gw)
        except:
          pass

    @timeit
    def create_logical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        
        gw_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
            break
        if not gw_vn_group_index:
           return 
        router_count         = tenant_conf['routers,count']
        vn_index_replace_str = tenant_conf['vn,index,replace_str']

        kwargs_list  = []
        vn_info_dict = {}
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
        if ret:
           vn_info_dict.update(ret)
        for tenant_name in tenant_name_list:
           tenant_indx = get_tenant_index(tenant_conf,tenant_name)
           router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
           vn_info          = tenant_conf['tenant,vn_group_list'][gw_vn_group_index]
           vn_name_pattern  = vn_info['vn,name,pattern']
           gw_vn_name_list  = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(router_count)]

           for indx,router_name in enumerate(router_name_list):
               gw_vn_name            = gw_vn_name_list[indx]
               kwargs                = {}
               kwargs['tenant_name'] = tenant_name
               kwargs['router_name'] = router_name
               kwargs['gw_nw']       = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,gw_vn_name)]
               kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_logical_router(count=True,conn_obj_list=conn_obj_list,**kwargs)

    @Process.wrapper
    def delete_logical_router(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name      = kwarg['tenant_name']
        lrs = self.connections.vnc_lib.logical_routers_list()['logical-routers']
        for lr in lrs:
            lr_domain,lr_tenant_name,lr_name = lr[u'fq_name']
            if lr_tenant_name != unicode(tenant_name):
               continue
            router_obj = self.connections.vnc_lib.logical_router_read(fq_name=lr[u'fq_name'])
            uuid = router_obj.uuid
            try:
              self.delete(uuid)
            except:
              pass

    def delete_logical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_logical_router(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    @Process.wrapper
    def attach_vns_to_logical_router(self,*arg,**kwarg):
        tenant_name   = kwarg['tenant_name']
        router_id     = kwarg['router_id']
        net_ids       = kwarg['private_vns']
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        self.connections.project_name = tenant_name
        self.connections.inputs.project_name = tenant_name
        quantum_h = self.connections.get_network_h()
        for net_id in net_ids:
            subnet_id = quantum_h.get_vn_obj_from_id(net_id)['network']['subnets'][0]
            try:
              quantum_h.add_router_interface(router_id=router_id, subnet_id=subnet_id)
            except:
              pass # interface may be already added

    @timeit
    def attach_vns_to_logical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        gw_vn_group_index           = None
        snat_private_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
          if re.search('Private_SNAT',vn_group['vn,name,pattern']):
            snat_private_vn_group_index = vn_group_indx
        if not gw_vn_group_index:
           return 
        vn_info_dict      = {}
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        if ret:
           vn_info_dict.update(ret)
        kwargs            = {}
        router_info_dict  = {}
        for tenant_name in tenant_name_list:
            tenant_indx      = get_tenant_index(tenant_conf,tenant_name)
            router_count     = tenant_conf['routers,count']
            router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
            kwargs[tenant_name] = router_name_list
        
        router_info_dict = self.get_router_id(conn_obj_list=conn_obj_list,**kwargs)

        kwargs_list       = []
        for tenant_name in tenant_name_list:
            tenant_indx      = get_tenant_index(tenant_conf,tenant_name)
            router_count     = tenant_conf['routers,count']
            router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
            vn_info          = tenant_conf['tenant,vn_group_list'][snat_private_vn_group_index]
            vn_count         = vn_info['count']
            vn_name_pattern  = vn_info['vn,name,pattern']
            vn_names_list    = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(vn_count)]
            if len(router_name_list) > 1:
               private_vn_per_routers = len(vn_names_list) / len(router_name_list)
            else:
               private_vn_per_routers = len(vn_names_list) 

            vn_index_offset = 0
            for router_name in router_name_list :
                kwargs = {}
                kwargs['tenant_name'] = tenant_name
                kwargs['router_id']   = router_info_dict[router_name]
                private_vn_names      = vn_names_list[vn_index_offset:vn_index_offset+private_vn_per_routers]
                vn_index_offset      += private_vn_per_routers
                private_vn_ids = []
                for vn_name in private_vn_names:
                    private_vn_ids.append(vn_info_dict[u'default-domain:%s:%s'%(tenant_name,vn_name)])
                kwargs['private_vns'] = private_vn_ids
                kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.attach_vns_to_logical_router(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

    def set_gw(self, uuid, gw):
        quantum_h = self.connections.get_network_h()
        quantum_h.router_gateway_set(uuid, gw)

    def clear_gw(self, uuid):
        quantum_h = self.connections.get_network_h()
        quantum_h.router_gateway_clear(uuid)

    def attach_vn(self, uuid, vn_id):
        quantum_h = self.connections.get_network_h()
        subnet_id = quantum_h.get_vn_obj_from_id(vn_id)['network']['subnets'][0]
        quantum_h.add_router_interface(router_id=uuid, subnet_id=subnet_id)

    def detach_vn(self, uuid, vn_id):
        quantum_h = self.connections.get_network_h()
        subnet_id = quantum_h.get_vn_obj_from_id(vn_id)['network']['subnets'][0]
        quantum_h.delete_router_interface(router_id=uuid, subnet_id=subnet_id)

    def delete(self, uuid):
        quantum_h = self.connections.get_network_h()
        ports = quantum_h.get_router_interfaces(uuid)
        for port in ports:
            quantum_h.delete_router_interface(router_id=uuid, port_id=port['id'])
        quantum_h.delete_router(uuid)

    def uuid(self):
        return self.uuid

    def fq_name(self, uuid=None):
        if not getattr(self, 'fqname', None):
            if not uuid:
                assert False, 'uuid has to be specified'
            quantum_h = self.connections.get_network_h()
            router_obj = quantum_h.show_router(router_id=uuid)
            self.fqname = router_obj['contrail:fq_name']
        return self.fqname


class LLS(Base):
    @Process.wrapper
    def retrieve_existing_services(self,*args,**kwargs):
        self.connections = kwargs['connection_obj'].connections
        self.logger      = kwargs['connection_obj'].logger
        current_config=self.connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])
        current_linklocal=current_config.get_linklocal_services()
        current_entries = current_linklocal.linklocal_service_entry
        service_names = []
        for entry in current_entries:
            value = entry.linklocal_service_name,entry.linklocal_service_ip,entry.linklocal_service_port
            service_names.append(value)
        return service_names

    def create(self,service_name,service_ip,service_port,fabric_dns_name,fabric_ip,fabric_port):

        linklocal_obj=LinklocalServiceEntryType(
                 linklocal_service_name=service_name,
                 linklocal_service_ip=service_ip,
                 linklocal_service_port=service_port,
                 ip_fabric_DNS_service_name=fabric_dns_name,
                 ip_fabric_service_ip=[fabric_ip],
                 ip_fabric_service_port=fabric_port)

        current_config=self.connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])

        current_linklocal=current_config.get_linklocal_services()
        current_entries = current_linklocal.linklocal_service_entry
        entry_found = False
        for i,entry in enumerate(current_entries):
            if entry.linklocal_service_name == unicode(service_name) :
               entry_found = True
               break
        if entry_found == True:
           self.logger.warn("LLS entry:%s already found..skipping create"%service_name)
           return
        current_entries.append(linklocal_obj)
        linklocal_services_obj=LinklocalServicesTypes(current_entries)
        conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
        result=self.connections.vnc_lib.global_vrouter_config_update(conf_obj)

    @Process.wrapper
    def create_link_local_service(self,*arg,**kwarg):
        services  = kwarg['services'] 
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger

        #self.create(service_name,lls_ip,lls_port,lls_fab_dns,lls_fab_ip,lls_fab_port)
        for service in services:
            service_name = service['lls_name']
            lls_ip       = service['lls_ip']
            lls_port     = service['lls_port']
            lls_fab_ip   = service['lls_fab_ip']
            lls_fab_port = service['lls_fab_port']
            lls_fab_dns  = service['lls_fab_dns']
            self.create(service_name,lls_ip,lls_port,None,lls_fab_ip,lls_fab_port)

    def create_link_local_services(self,conn_obj_list,thread_count,global_conf,tenant_conf):

        count      = global_conf.get('lls,count',None)
        if count is None:
           return
        start_ip   = global_conf['lls,start_ip']
        start_port = global_conf['lls,start_port']
        fab_ip     = global_conf['lls,fab_ip']
        fab_port   = global_conf['lls,fab_port']
        fab_dns    = global_conf['lls,fab_dns']
        service_ip   = ipaddr.IPAddress(start_ip)
        service_port = start_port 
        service_name_pattern = global_conf['lls,name']
        service_conf_l = [] 
        for i in xrange(count):
            kwargs = {}
            service_name = re.sub('###',str(i),service_name_pattern)
            fab_dns_name = re.sub('###',str(i),fab_dns)
            kwargs['lls_name']     = service_name
            kwargs['lls_ip']       = str(service_ip)
            kwargs['lls_port']     = service_port
            kwargs['lls_fab_ip']   = fab_ip
            kwargs['lls_fab_port'] = fab_port
            kwargs['lls_fab_dns']  = fab_dns_name
            service_ip   += 1
            service_port += 1
            fab_port     += 1 
            service_conf_l.append(kwargs)
        kwarg = {}
        kwarg['services'] = service_conf_l 
        self.create_link_local_service(count=thread_count,conn_obj_list=[conn_obj_list[0]],**kwarg)

    @Process.wrapper
    def delete_link_local_service(self,*arg,**kwarg):
        connection_obj   = kwarg['connection_obj']
        self.connections = connection_obj.connections
        self.logger      = connection_obj.logger
        lls_names        = kwarg['lls_name_list']
        return
        for service_name in lls_names:
            current_config=self.connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])
            current_linklocal=current_config.get_linklocal_services()
            current_entries = current_linklocal.linklocal_service_entry
            entry_found = False
            for i,entry in enumerate(current_entries):
                if entry.linklocal_service_name == service_name :
                   entry_found = True
                   current_entries.pop(i)
                   break
            if entry_found == False:
               self.logger.warn("LLS entry:%s not found...skipping delete"%service_name)
               return
            linklocal_services_obj=LinklocalServicesTypes(current_entries)
            conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
            result=self.connections.vnc_lib.global_vrouter_config_update(conf_obj)
        return True

    def delete_link_local_services(self,conn_obj_list,thread_count,global_conf,tenant_conf):

        count      = global_conf.get('lls,count',None)
        if count is None:
           return
        service_name_pattern = global_conf['lls,name']
        lls_name_list = []
        for i in xrange(count):
            service_name = re.sub('###',str(i),service_name_pattern)
            lls_name_list.append(service_name)
        kwargs = {}
        kwargs['lls_name_list'] = lls_name_list
        if len(lls_name_list) == 0:
           return
        self.delete_link_local_service(count=thread_count,conn_obj_list=[conn_obj_list[0]],**kwargs)

class Lbaas(Base):
     @Process.wrapper
     def remove_lb_service_instances(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        tenant_name_list = kwarg['tenant_name_list']
        service_instances = self.connections.vnc_lib.service_instances_list()['service-instances']
        for si in service_instances:
            dom,t_name,si_name = si['fq_name']
            if t_name not in tenant_name_list:
               continue
            #if re.search('^si_',si_name):
            #   continue
            self.connections.vnc_lib.service_instance_delete(fq_name=si['fq_name'])
      
     @Process.wrapper
     def retrieve_lb_pools_info(self,*arg,**kwarg):
        self.connections = kwarg['connection_obj'].connections
        self.logger      = kwarg['connection_obj'].logger
        pools = self.connections.vnc_lib.loadbalancer_pools_list() 
        return pools

     @Process.wrapper
     def create_lb_pool(self,*arg,**kwarg):
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name    = kwarg['tenant_name']
         pool_name      = kwarg['pool_name']
         lb_method      = kwarg['lb_method']
         protocol       = kwarg['protocol']
         servers_net_id = kwarg['servers_net_id']
         project_fq_name = [u'default-domain',u'%s'%tenant_name]
         project_obj = self.connections.vnc_lib.project_read(fq_name=project_fq_name)
         tenant_id = project_obj.uuid
         lb_pools = self.connections.vnc_lib.loadbalancer_pools_list(parent_id=tenant_id)['loadbalancer-pools']
         lb_pool_already_exists = False
         for lb_pool in lb_pools:
             dom,t_name,pool_n = lb_pool['fq_name']
             if t_name == tenant_name and pool_n == pool_name:
                lb_pool_already_exists = True

         if lb_pool_already_exists:
            self.logger.warn("lb_pool:%s already exists..skipping create"%pool_name)
            return
         self.connections.project_name = tenant_name
         self.connections.inputs.project_name = tenant_name
         quantum_h = self.connections.get_network_h()
         subnet_id = quantum_h.get_vn_obj_from_id(servers_net_id)['network']['subnets'][0]
         quantum_h.create_lb_pool(pool_name,lb_method,protocol,subnet_id)

     @Process.wrapper
     def delete_lb_pool(self,*arg,**kwarg):
         #self.get_connection_handle()
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name = kwarg['tenant_name']
         proj_obj=self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
         lb_pools = self.connections.vnc_lib.loadbalancer_pools_list(parent_id=proj_obj.uuid) ['loadbalancer-pools']
         for lb_pool in lb_pools:
             uuid = lb_pool['uuid']
             self.connections.vnc_lib.loadbalancer_pool_delete(id=uuid)

     def delete_lb_pools(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_lb_pool(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     def create_lb_pools(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        pool_names_list = []
        for tenant_name in tenant_name_list:
            tenant_indx = get_tenant_index(tenant_conf,tenant_name)
            pool_names_list.append(generate_lb_pool_name(global_conf,tenant_conf,tenant_indx))
        lb_pool_vn_list = []
        vn_info_dict = {}
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        if ret:
           vn_info_dict.update(ret)
        pool_vn_ids = []
        for tenant_name in tenant_name_list:
            tenant_indx  = get_tenant_index(tenant_conf,tenant_name)
            pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
            if not pool_vn_name:
               return
            lb_pool_vn_list.append(pool_vn_name)
            pool_vn_id   = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,pool_vn_name)]
            pool_vn_ids.append(pool_vn_id)
        kwargs_list = []
        for i,tenant_name in enumerate(tenant_name_list):
             kwargs = {}
             kwargs['tenant_name'] = tenant_name
             kwargs['pool_name']   = pool_names_list[i]
             kwargs['lb_method']   = tenant_conf['lbaas,method']
             kwargs['protocol']    = tenant_conf['lbaas,pool,protocol']
             kwargs['servers_net_id'] = pool_vn_ids[i]
             kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_lb_pool(count=thread_count,conn_obj_list=conn_obj_list, **kwargs)

     @Process.wrapper
     def create_lb_member(self,*arg,**kwarg):
         tenant_name    = kwarg['tenant_name']
         pool_id        = kwarg['pool_id']
         server_ip      = kwarg['server_ip']
         protocol_port  = kwarg['protocol_port']
         vm_id          = kwarg['vm_id']

         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         self.connections.project_name = tenant_name
         self.connections.inputs.project_name = tenant_name
         try:
           pool_obj     = self.connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except:
           return
         lb_members   = pool_obj.get_loadbalancer_members()
         quantum_h    = self.connections.get_network_h()
         member_found = False
         member_uuid = None
         if lb_members is not None:
            for lb_member in lb_members:
              uid = lb_member['uuid'] 
              ret = quantum_h.show_lb_member(uid)
              if unicode(server_ip) == ret['address'] and \
                      int(protocol_port) == int(ret['protocol_port']):
                member_found = True
                member_uuid = uid
                break

         #vm_obj = self.connections.vnc_lib.virtual_machine_read(id=vm_id)
         #vmis   = vm_obj.get_virtual_machine_interface_back_refs()
         #for vmi in vmis:
         #    vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
         #    vmi_obj.set_virtual_machine_interface_device_owner("compute:nova")
         #    self.connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

         if member_found:
            self.logger.warn("lb_member : %s %s found..skipping create"%(server_ip,str(protocol_port)))
            return

         quantum_h.create_lb_member(server_ip,protocol_port,pool_id)
      

     @Process.wrapper
     def delete_lb_member(self,*arg,**kwarg):
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name    = kwarg['tenant_name']
         lb_members = self.connections.vnc_lib.loadbalancer_members_list()['loadbalancer-members']
         for lb_member in lb_members:
             dom,t_name,pool_name,member_id = lb_member['fq_name']
             if t_name == tenant_name :
                self.connections.vnc_lib.loadbalancer_member_delete(id=member_id)

     def delete_lb_members(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete_lb_member(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     def create_lb_members(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        ret      = self.retrieve_lb_pools_info(conn_obj_list=conn_obj_list)
        lb_pools = ret['loadbalancer-pools'] 
        lb_pool_info = {}
        for lb_pool in lb_pools:
            dom,t_name,pool_name = lb_pool['fq_name']
            if t_name not in tenant_name_list:
               continue
            lb_pool_id           = lb_pool['uuid'] 
            lb_pool_info['%s,%s'%(t_name,pool_name)] = lb_pool_id

        if not lb_pool_info :
           return

        vms_list    = []
        kwargs_list = []
        vm_obj      = VM(None)

        for indx,tenant_name in enumerate(tenant_name_list):
          tenant_indx  = get_tenant_index(tenant_conf,tenant_name)
          pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
          pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
          if not pool_vn_name:
             return
          vms_list     = vm_obj.list_vms(conn_obj_list=conn_obj_list,tenant_name_list=[tenant_name],vn_list=[pool_vn_name])
          if not vms_list:
            print "no servers in this VN pool..skipping.."
            continue
          for vm in vms_list:
             vn_name = vm['vn_name']
             vm_ip = vm['ip'][vn_name][0]['addr']
             kwargs = {}
             kwargs['tenant_name']   = tenant_name
             kwargs['pool_id']       = lb_pool_info['%s,%s'%(tenant_name,pool_name)]
             kwargs['server_ip']     = vm_ip
             kwargs['vm_id']        = vm['id']
             kwargs['protocol_port'] = tenant_conf['lbaas,pool,members_port']
             kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_lb_member(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     @Process.wrapper
     def create_lb_vip(self,*arg,**kwarg):
         tenant_name       = kwarg['tenant_name']
         vip_name          = kwarg['vip_name']
         vip_protocol      = kwarg['vip_protocol']
         vip_protocol_port = kwarg['vip_port']
         pool_id           = kwarg['pool_id']
         subnet_name       = kwarg['subnet_name']
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         try:
           pool_obj = self.connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except:
           return
         vip_ref  = pool_obj.get_virtual_ip_back_refs()
         if vip_ref:
            self.logger.warn("pool:%s already has VIP..skipping vip create"%pool_id)
            return
         
         self.connections.project_name = tenant_name
         self.connections.inputs.project_name = tenant_name
         self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
         vn_fq_name = [u'default-domain',u'%s'%tenant_name,u'%s'%subnet_name]
         vn_obj     = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
         net_id     = vn_obj.uuid
         self.quantum_h = self.connections.get_network_h()
         subnet_id      = self.quantum_h.get_vn_obj_from_id(net_id)['network']['subnets'][0]
         vip_resp       = self.quantum_h.create_vip(vip_name, vip_protocol,\
                              vip_protocol_port, subnet_id, pool_id)
         vip_obj = self.connections.vnc_lib.virtual_ip_read(fq_name=[u'default-domain',unicode(tenant_name),unicode(vip_name)])
         vm_refs = vip_obj.get_virtual_machine_interface_refs() or []
         for vm_ref in vm_refs:
             vm_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vm_ref['uuid'])
             vm_obj.set_virtual_machine_interface_device_owner("compute:nova")
             self.connections.vnc_lib.virtual_machine_interface_update(vm_obj)

     @Process.wrapper
     def delete_lb_vip(self,*arg,**kwarg):
         #self.get_connection_handle()
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name       = kwarg['tenant_name']
         proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
         virt_ips_list = self.connections.vnc_lib.virtual_ips_list(parent_id=proj_obj.uuid)['virtual-ips']
         if len(virt_ips_list) == 0:
            return
         self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
         self.quantum_h = self.connections.get_network_h()
         for virt_ip  in virt_ips_list:
             dom,t_name,vip_name = virt_ip['fq_name']
             if t_name != tenant_name:
                continue
             virt_ip_id = virt_ip['uuid']
             self.quantum_h.delete_vip(virt_ip_id)

     def delete_lb_vips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

         kwargs_list = []
         for tenant_name in tenant_name_list:
             kwargs = {}
             kwargs['tenant_name'] = tenant_name
             kwargs_list.append(kwargs)

         if len(kwargs_list) == 0:
            return
         kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
         self.delete_lb_vip(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
    
     @Process.wrapper
     def associate_fip_to_vip(self,*arg,**kwarg):
         tenant_name    = kwarg['tenant_name']
         vip_name       = kwarg['vip_name']
         fip_vn_name    = kwarg['fip_vn_name']
         fip_pool_name  = kwarg['fip_pool_name']
         fip_pool_vn_id = kwarg['fip_pool_vn_id']
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         self.connections.orch = self.connections.get_orch_h()
         proj_obj      = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
         fip_fq_name   = ['default-domain',tenant_name,fip_vn_name,fip_pool_name] 
         try:
            fip_pool_obj  = self.connections.vnc_lib.floating_ip_pool_read(fq_name=fip_fq_name)
         except NoIdError:
            return
         fip_ip,fip_id = self.connections.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id, project_obj=proj_obj, pool_obj=fip_pool_obj)
         virt_ips      = self.connections.vnc_lib.virtual_ips_list()['virtual-ips']
         for vip in virt_ips:
            dom,t_name,v_name = vip['fq_name']
            if not ( t_name == tenant_name and v_name == vip_name):
               continue
            vip_id      = vip['uuid']
            vip_obj     = self.connections.vnc_lib.virtual_ip_read(id=vip_id)
            vm_intf_ref = vip_obj.get_virtual_machine_interface_refs()
            if not vm_intf_ref:
               continue
            vm_intf_id = vm_intf_ref[0]['uuid']
            dom,t_name,vmi_port_id = vm_intf_ref[0]['to']
            vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vm_intf_id)
            fips    = vmi_obj.get_floating_ip_back_refs()
            if fips:
               self.logger.warn("fip is already attached to VIP..skipping fip attach")
               return
            vn_id = None
            self.connections.orch.assoc_floating_ip(fip_id,vmi_port_id,vn_id)
            fips    = vmi_obj.get_floating_ip_back_refs()
            fip_obj = self.connections.vnc_lib.floating_ip_read(id=fips[0]['uuid'])
            vmi_ref = fip_obj.get_virtual_machine_interface_refs()
            for vmi in vmi_ref:
                vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                vmi_obj.set_virtual_machine_interface_device_owner("compute:nova")
                self.connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

     def associate_fip_to_vips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
         lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
         if lbaas_pool_name_pattern is None:
            return
         kwargs_list = []
         vn_index    = 0
         pool_indx   = 0
         fip_vn_name_pattern = None
         attach_fip = False
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
             vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
             vn_name_pattern = vn_info['vn,name,pattern']
             if re.search('Public_FIP_VN',vn_name_pattern):
                fip_vn_name_pattern = vn_name_pattern
             if re.search('Private_LB_VIP_VN',vn_name_pattern):
                attach_fip = vn_info['attach_fip']
         vip_name = tenant_conf.get('lbaas,pool,vip_name',None)
         if fip_vn_name_pattern is None or vip_name is None or not attach_fip:
            return
         vn_info_dict = {}
         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
         if ret:
            vn_info_dict.update(ret)
         for tenant_name in tenant_name_list:
             tenant_indx = get_tenant_index(tenant_conf,tenant_name)
             kwargs = {}
             kwargs['tenant_name'] = tenant_name
             kwargs['vip_name']    = generate_vip_name(global_conf,tenant_conf,tenant_indx)
             pool_vn_name          = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                        fip_vn_name_pattern,vn_index)
             kwargs['fip_vn_name'] = pool_vn_name
             kwargs['fip_pool_name'] = generate_fip_pool_name(global_conf,tenant_conf,\
                                          tenant_indx,pool_indx)
             kwargs['fip_pool_vn_id'] = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,pool_vn_name)]
             kwargs_list.append(kwargs)
         if len(kwargs_list) == 0:
            return
         kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
         self.associate_fip_to_vip(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     def create_lb_vips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
         vip_port     = tenant_conf.get('lbaas,pool,vip_port',None)
         if vip_port is None:
            return
         vip_protocol = tenant_conf['lbaas,pool,vip_protocol'] 
         vn_info_dict = {}
         lb_pool_info = {}

         ret      = self.retrieve_lb_pools_info(conn_obj_list=conn_obj_list)
         lb_pools = ret['loadbalancer-pools'] 
         lb_pool_info = {}

         for lb_pool in lb_pools:
            dom,t_name,pool_name = lb_pool['fq_name']
            lb_pool_id           = lb_pool['uuid'] 
            lb_pool_info['%s,%s'%(t_name,pool_name)] = lb_pool_id

         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
         if ret:
            vn_info_dict.update(ret)

         vip_vn_name_pattern = None
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
             vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
             vn_name_pattern      = vn_info['vn,name,pattern']
             if re.search('Private_LB_VIP_VN',vn_name_pattern):
                vip_vn_name_pattern = vn_name_pattern
                break

         kwargs_list  = []
         for tenant_name in tenant_name_list:
             tenant_indx  = get_tenant_index(tenant_conf,tenant_name)
             pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
             pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
             if not pool_vn_name:
                return
             pool_vn_id   = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,pool_vn_name)]
             vip_index    = tenant_indx
             vn_index     = 0
             vip_name     = generate_vip_name(global_conf,tenant_conf,vip_index)
             vip_vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                vip_vn_name_pattern,vn_index)
             kwargs = {}
             kwargs['tenant_name']  = tenant_name
             kwargs['vip_name']     = vip_name
             kwargs['vip_port']     = vip_port
             kwargs['vip_protocol'] = vip_protocol
             kwargs['subnet_name']  = vip_vn_name
             kwargs['pool_id']      = lb_pool_info['%s,%s'%(tenant_name,pool_name)]
             kwargs_list.append(kwargs)
    
         if len(kwargs_list) == 0:
            return
         kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
         self.create_lb_vip(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     @Process.wrapper
     def create_health_monitor(self,*arg,**kwarg):
         tenant_name = kwarg['tenant_name']
         probe_type  = kwarg['probe_type']
         delay       = kwarg['probe_delay']
         timeout     = kwarg['probe_timeout']
         max_retries = kwarg['probe_retries']
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
         hms = self.connections.vnc_lib.loadbalancer_healthmonitors_list(parent_id=proj_obj.uuid)['loadbalancer-healthmonitors']
         if hms:
            self.logger.warn("Health-monitor already present..skipping create for tenant:%s"%tenant_name)
            return
         self.connections.project_name = tenant_name
         self.connections.inputs.project_name = tenant_name
         self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
         self.quantum_h = self.connections.get_network_h()
         self.quantum_h.create_health_monitor( delay, max_retries, probe_type, timeout)

     def create_health_monitors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        kwargs_list  = []
        probe_type = tenant_conf.get('lbaas,probe,type',None)
        if probe_type is None:
           return
        for tenant_name in tenant_name_list:
               kwargs = {}
               kwargs['tenant_name']   = tenant_name
               kwargs['probe_type']    = tenant_conf['lbaas,probe,type']
               kwargs['probe_delay']   = tenant_conf['lbaas,probe,delay']
               kwargs['probe_timeout'] = tenant_conf['lbaas,probe,timeout']
               kwargs['probe_retries'] = tenant_conf['lbaas,probe,retries']
               kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create_health_monitor(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     @Process.wrapper
     def associate_health_monitor(self,*arg,**kwarg):
         tenant_name = kwarg['tenant_name']
         pool_name   = kwarg['pool_name']
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
         pools   = self.connections.vnc_lib.loadbalancer_pools_list()['loadbalancer-pools']
         if len(pools) == 0:
            return
         pool_id = None
         for pool in pools:
            if pool['fq_name'] == [u'default-domain', u'%s'%tenant_name, u'%s'%pool_name]:
               pool_id = pool['uuid']
         self.connections.project_name = tenant_name
         self.connections.inputs.project_name = tenant_name
         self.quantum_h = self.connections.get_network_h()
         hms = self.connections.vnc_lib.loadbalancer_healthmonitors_list()['loadbalancer-healthmonitors']
         hm_id = None
         for hm in hms:
             dom,t_name,hmid = hm['fq_name']
             if t_name == tenant_name:
               hm_id = hmid
               break
         try:
           pool_obj = self.connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except:
           return 
         hm_ref   = pool_obj.get_loadbalancer_healthmonitor_refs()
         
         if hm_ref:
            self.logger.warn("health monitor is already associated with the pool..skipping hm associate.")
            return
         self.quantum_h.associate_health_monitor(pool_id,hm_id)

     def associate_health_monitors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
           lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
           if lbaas_pool_name_pattern is None:
              return

           probe_type = tenant_conf.get('lbaas,probe,type',None)
           if probe_type is None:
              return
           kwargs_list  = []
           for tenant_name in tenant_name_list:
               tenant_indx  = get_tenant_index(tenant_conf,tenant_name)
               pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
               kwargs = {}
               kwargs['tenant_name']   = tenant_name
               kwargs['pool_name']     = pool_name
               kwargs_list.append(kwargs)

           if len(kwargs_list) == 0:
              return
           kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
           self.associate_health_monitor(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     @Process.wrapper
     def delete_health_monitor(self,*arg,**kwarg):
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name = kwarg['tenant_name']
         proj_obj = self.connections.vnc_lib.project_read(fq_name=['default-domain',tenant_name])
         hms = self.connections.vnc_lib.loadbalancer_healthmonitors_list(parent_id=proj_obj.uuid)['loadbalancer-healthmonitors']
         for hm in hms:
             hm_obj = self.connections.vnc_lib.loadbalancer_healthmonitor_read(id=hm['uuid'])
             pools = hm_obj.get_loadbalancer_pool_back_refs() or []
             for pool in pools:
                 pool_id = pool['uuid']
                 pool_obj = self.connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
                 pool_obj.del_loadbalancer_healthmonitor(hm_obj)
                 self.connections.vnc_lib.loadbalancer_pool_update(pool_obj)
             self.connections.vnc_lib.loadbalancer_healthmonitor_delete(hm_obj.fq_name)

     def delete_health_monitors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

           kwargs_list  = []
           for tenant_name in tenant_name_list:
               kwargs = {}
               kwargs['tenant_name']   = tenant_name
               kwargs_list.append(kwargs)

           if len(kwargs_list) == 0:
              return
           kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
           self.delete_health_monitor(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

def generate_random_vlan_id(pi_vlan_info,pr_name):
    pi_vlan_info[pr_name].sort()
    total_range = xrange(10,4094)
    available_vlan_id = list(set(total_range) - set(pi_vlan_info[pr_name]))
    if len(available_vlan_id) == 0:
       return False
    else:
       random.shuffle(available_vlan_id)
       return available_vlan_id[0]

class RouterConfig(Base):
      @Process.wrapper
      def retrieve_pr_vlan_info(self,*arg,**kwarg):
          global_conf     = kwarg.get('global_conf',None)
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          pr_qfx = global_conf['pr_qfx']
          physical_interface_list = []
          for qfx in pr_qfx:
              bms_servers = qfx['bms']
              for bms in bms_servers:
                  info = {}
                  info['pr_name']                 = qfx['name']
                  info['tor_interface']           = bms['tor_interface']
                  info['physical_server_ip_addr'] = bms['physical_server_mgmt_ip']
                  physical_interface_list.append(info)
          pi_vlan_info = {}
          for pi in physical_interface_list:
              pr_name        = pi['pr_name']
              pi_interface   = pi['tor_interface']
              physical_server_ip_addr = pi['physical_server_ip_addr']
              pi_interface_m = re.sub(":","__",pi_interface)
              try:
                 pi_obj = self.connections.vnc_lib.physical_interface_read(fq_name=['default-global-system-config',unicode(pr_name),unicode(pi_interface_m)])
              except:
                 continue
              li_ref = pi_obj.get_logical_interfaces() or []
              pi_vlan_info[physical_server_ip_addr] = []
              for li in li_ref:
                  li_obj = self.connections.vnc_lib.logical_interface_read(id=li['uuid'])
                  vlan_id = li_obj.logical_interface_vlan_tag
                  pi_vlan_info[physical_server_ip_addr].append(vlan_id)
          return pi_vlan_info
 
      @Process.wrapper
      def create_physical_router(self,*arg,**kwarg):
        try:
          pr_name           = kwarg['pr,name']
          pr_mgmt_ip        = kwarg['pr,mgmt_ip']
          pr_login          = kwarg.get('pr,login',None)
          pr_password       = kwarg.get('pr,password',None)
          pr_dataplane_ip   = kwarg['pr,dataplane_ip']
          pr_junos_si       = kwarg.get('pr,junos_si',None)
          is_tor            = kwarg.get('is_tor',False)
          mac_addr          = kwarg.get('pr,mac',None)
          global_conf       = kwarg.get('global_conf',None)
          tsn               = kwarg.get('pr,tsn',None)
          tsn_ip            = kwarg.get('pr,tsn_ip',None)
          ta                = kwarg.get('pr,ta',None)
          pr_interface_name = kwarg.get('pr,interface_name',None)
          pr_interface_vlan = kwarg.get('pr,interface_vlan',None)
          pr_interface_vn   = kwarg.get('pr,interface_vn',None)
          pr_interface_mac  = kwarg.get('pr,interface_mac',None)
          pr_interface_ip   = kwarg.get('pr,interface_ip',None)
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          rt_inst_obj = self.connections.vnc_lib.routing_instance_read(
                              fq_name=['default-domain', 'default-project',
                                        'ip-fabric', '__default__'])
          bgp_router = None
          if is_tor == False:
              bgp_router     = BgpRouter(pr_name, parent_obj=rt_inst_obj)
              params         = BgpRouterParams()
              params.address = pr_dataplane_ip
              params.address_families = AddressFamilies(['route-target', 'inet-vpn', 'e-vpn',
                                               'inet6-vpn'])
              params.autonomous_system = 64512
              params.vendor     = 'mx'
              params.identifier = pr_mgmt_ip
              bgp_router.set_bgp_router_parameters(params)
              try:
                  self.connections.vnc_lib.bgp_router_read(fq_name=['default-domain', 'default-project', 'ip-fabric', '__default__', pr_name])
                  self.connections.vnc_lib.bgp_router_update(bgp_router)
              except NoIdError:
                  self.connections.vnc_lib.bgp_router_create(bgp_router)

          pr = PhysicalRouter(pr_name)
          pr.physical_router_management_ip = pr_mgmt_ip
          pr.physical_router_vendor_name   = 'juniper'
          pr.physical_router_product_name  = 'mx'
          pr.physical_router_vnc_managed   = True 
          if pr_login is not None:
             uc = UserCredentials(pr_login,pr_password)
             pr.set_physical_router_user_credentials(uc)
          if is_tor == False:
             pr.set_bgp_router(bgp_router)
          try:
              self.connections.vnc_lib.physical_router_read(
                        fq_name=[u'default-global-system-config',pr_name]) 
              self.connections.vnc_lib.physical_router_update(pr)
          except NoIdError:
              self.connections.vnc_lib.physical_router_create(pr)
          if is_tor :
             pr.physical_router_vnc_managed  = False
             pr.physical_router_product_name = 'qfx'
          else:
             pr.physical_router_vnc_managed  = True
             pr.physical_router_product_name = 'mx'
             junos_service_ports = JunosServicePorts()
             junos_service_ports.service_port.append(pr_junos_si)
             pr.set_physical_router_junos_service_ports(junos_service_ports)
          pr.physical_router_vendor_name     = 'juniper'
          pr.physical_router_dataplane_ip    = pr_dataplane_ip
          self.connections.vnc_lib.physical_router_update(pr)

          pr_obj = self.connections.vnc_lib.physical_router_read(
                        fq_name=[u'default-global-system-config',pr_name])
         
          if pr_interface_name:
             try:
               pr_interface_name_m = re.sub(":","__",pr_interface_name)
               pi = self.connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, pr_interface_name_m])
             except NoIdError:
               pi = PhysicalInterface(pr_interface_name_m, parent_obj = pr,display_name=pr_interface_name)
               self.connections.vnc_lib.physical_interface_create(pi)

             iface_name   = pr_interface_name + "." + str(pr_interface_vlan)
             iface_name_m = re.sub(":","__",iface_name)
             vmi_fq_name  = ['default-domain','admin',unicode(iface_name_m)]
             vn_fq_name   = ['default-domain','admin',pr_interface_vn]
             vn_obj       = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
             try:
               vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(fq_name=vmi_fq_name)
             except NoIdError:
               vmi_obj = VirtualMachineInterface(fq_name=vmi_fq_name, parent_type='project')
               mac_address_obj = MacAddressesType()
               mac_address_obj.set_mac_address([pr_interface_mac])
               vmi_obj.set_virtual_machine_interface_mac_addresses(mac_address_obj)
               vmi_obj.add_virtual_network(vn_obj)
               self.connections.vnc_lib.virtual_machine_interface_create(vmi_obj)
               vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(fq_name=vmi_fq_name)
             try:
               li = self.connections.vnc_lib.logical_interface_read(
                             fq_name=[u'default-global-system-config', pr_name,pr_interface_name_m,iface_name_m])
               li.set_virtual_machine_interface(vmi_obj)
               self.connections.vnc_lib.logical_interface_update(li)
             except NoIdError:
               li = LogicalInterface(iface_name_m, parent_obj = pi,logical_interface_vlan_tag=pr_interface_vlan,display_name=iface_name)
               li.set_virtual_machine_interface(vmi_obj)
               self.connections.vnc_lib.logical_interface_create(li)
               instance_ip_name = iface_name_m + "." + str(pr_interface_vlan)
               try:
                 ip_obj = self.connections.vnc_lib.instance_ip_read(fq_name=[unicode(instance_ip_name)])
                 ip_obj.set_virtual_machine_interface(vmi_obj)
                 ip_obj.set_virtual_network(vn_obj)
                 ip_obj.set_instance_ip_address(pr_interface_ip)
                 self.connections.vnc_lib.instance_ip_update(ip_obj)
               except NoIdError:
                 ip_obj = InstanceIp(name=instance_ip_name)
                 ip_obj.set_virtual_machine_interface(vmi_obj)
                 ip_obj.set_instance_ip_address(pr_interface_ip)
                 ip_obj.set_virtual_network(vn_obj)
                 self.connections.vnc_lib.instance_ip_create(ip_obj)

          if ta:
             vr = VirtualRouter(ta)
             vr.virtual_router_ip_address = tsn_ip
             vr.virtual_router_type=[u'tor-agent']
             try:
               self.connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',ta])
               self.connections.vnc_lib.virtual_router_update(vr)
             except NoIdError:
               self.connections.vnc_lib.virtual_router_create(vr)
             tor_agent_obj = self.connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',ta])
          if tsn:
             vr = VirtualRouter(tsn)
             vr.virtual_router_ip_address = tsn_ip
             vr.virtual_router_type=[u'tor-service-node']
             try:
               self.connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',tsn])
               self.connections.vnc_lib.virtual_router_update(vr)
             except NoIdError:
               self.connections.vnc_lib.virtual_router_create(vr)
             tsn_obj = self.connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',tsn])

          if ta and tsn:
             pr_obj.add_virtual_router(tor_agent_obj)
             pr_obj.add_virtual_router(tsn_obj)
             self.connections.vnc_lib.physical_router_update(pr_obj)
        except:
            traceback.print_exc(file=sys.stdout)

      @Process.wrapper
      def retrieve_existing_li(self,*arg,**kwarg):
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          existing_li      = self.connections.vnc_lib.logical_interfaces_list()['logical-interfaces']
          return existing_li

      @Process.wrapper
      def retrieve_pi_vlan_info(self,*arg,**kwarg):
        try:
          pr_qfxs = kwarg['pr_qfxs']
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          pi_vlan_info = {}
          for pr_qfx in pr_qfxs:
              pr_name = pr_qfx['name']
              pi_vlan_info[pr_name] = []
              bms_servers = pr_qfx['bms']
              physical_interface_list  = []
              physical_server_mac_list = []
              physical_server_mgmt_ip  = []
              for bms_server in bms_servers:
                  physical_interface_list.append(bms_server['tor_interface'])
                  physical_server_mac_list.append(bms_server['physical_server_mac'])
                  physical_server_mgmt_ip.append(bms_server['physical_server_mgmt_ip'])
              for pi in physical_interface_list:
                  pi_m = re.sub(":","__",pi)
                  try:
                    pi_obj = self.connections.vnc_lib.physical_interface_read(fq_name=['default-global-system-config',unicode(pr_name),unicode(pi_m)])
                  except:
                    continue
                  li_ref = pi_obj.get_logical_interfaces() or []
                  for li in li_ref:
                      li_obj = self.connections.vnc_lib.logical_interface_read(id=li['uuid'])
                      vlan_id = li_obj.logical_interface_vlan_tag 
                      pi_vlan_info[pr_name].append(vlan_id)
                      try:
                        vmi_refs = li_obj.virtual_machine_interface_refs[0]
                      except:
                        continue
                      vmi_obj  = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi_refs['uuid'])
                      mac_obj  = vmi_obj.get_virtual_machine_interface_mac_addresses()
                      mac_addr = mac_obj.mac_address[0]
                      if pi_vlan_info.has_key(mac_addr):
                         pi_vlan_info[mac_addr].append(vlan_id)
                      else:
                         pi_vlan_info[mac_addr] = []
        except:
            traceback.print_exc(file=sys.stdout)
        return pi_vlan_info

      @Process.wrapper
      def create_logical_interface(self,*arg,**kwarg):
        try:
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          physical_iface_name   = kwarg['physical_iface']
          physical_iface_name_m = re.sub(":","__",physical_iface_name)
          tenant_name  = kwarg['tenant_name']
          pr_name      = kwarg['pr_name']
          mac_addr     = kwarg['mac_addr']
          iface_name   = kwarg['iface_name']
          existing_li  = kwarg['existing_li']
          iface_name_m = re.sub(":","__",iface_name)
          pi_obj       = kwarg['pi_obj']
          li_regex     = "default-global-system-config:" + pr_name + ":.*" + "%s.bms%s\."%(kwarg['vn_name'],kwarg['bms_index'])

          li = LogicalInterface(iface_name_m, parent_obj = pi_obj,logical_interface_vlan_tag=kwarg['vlan_id'],display_name=iface_name)
          li.parent_uuid = pi_obj.uuid

          try:
            self.connections.vnc_lib.logical_interface_create(li)
          except (RefsExistError,PermissionDenied): # PermissionDenied seen for Vlan tag already used
            pass

          vmi_fq_name = [unicode('default-domain'),unicode(tenant_name),unicode(iface_name_m)]
          vmi_obj = VirtualMachineInterface(fq_name=vmi_fq_name, parent_type='project')
          mac_address_obj = MacAddressesType()
          mac_address_obj.set_mac_address([mac_addr])
          vmi_obj.set_virtual_machine_interface_mac_addresses(mac_address_obj)
          vn_fq_name  = [unicode('default-domain'),unicode(tenant_name),unicode(kwarg['vn_name'])]
          vn_obj      = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
          vmi_obj.add_virtual_network(vn_obj)
          try:
            self.connections.vnc_lib.virtual_machine_interface_create(vmi_obj)
          except RefsExistError:
            pass

          instance_ip_name = iface_name_m + "." + str(kwarg['vlan_id'])
          try:
            ip_obj = self.connections.vnc_lib.instance_ip_read(fq_name=[unicode(instance_ip_name)])
            ip_obj.set_virtual_machine_interface(vmi_obj)
            ip_obj.set_virtual_network(vn_obj)
            self.connections.vnc_lib.instance_ip_update(ip_obj)
          except NoIdError:
            ip_obj = InstanceIp(name=instance_ip_name)
            ip_obj.set_virtual_machine_interface(vmi_obj)
            ip_obj.set_virtual_network(vn_obj)
            try:
               self.connections.vnc_lib.instance_ip_create(ip_obj)
            except RefsExistError:
               pass

          #conf_obj = GlobalVrouterConfig(vxlan_network_identifier_mode='auto-configured')
          #self.connections.vnc_lib.global_vrouter_config_update(conf_obj)

          vni_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
          vni_obj_properties.set_vxlan_network_identifier(kwarg['vlan_id'])
          vn_obj.set_virtual_network_properties(vni_obj_properties)
          try:
             self.connections.vnc_lib.virtual_network_update(vn_obj)
          except:
             pass

          li.add_virtual_machine_interface(vmi_obj)
          try:
            self.connections.vnc_lib.logical_interface_update(li)
          except:
            traceback.print_exc(file=sys.stdout)
        except:
            traceback.print_exc(file=sys.stdout)
            sys.exit()

      @Process.wrapper
      def retrieve_existing_pr(self,*arg,**kwarg):
          connection_obj = kwarg['connection_obj']
          self.connections = connection_obj.connections
          self.logger      = connection_obj.logger
          prs = self.connections.vnc_lib.physical_routers_list()['physical-routers']
          pr_names = []
          for pr in prs:
              fq_name = pr['fq_name'][1]
              pr_names.append(fq_name)
          return pr_names

      @Process.wrapper
      def retrieve_pi_obj(self,*arg,**kwarg):
          connection_obj = kwarg['connection_obj']
          self.connections = connection_obj.connections
          self.logger      = connection_obj.logger
          pr_name = kwarg['pr_name']
          physical_iface_name = kwarg['physical_iface_name']
          iface_name_m = re.sub(":","__",physical_iface_name)
          pi_obj = self.connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, iface_name_m])
          return pi_obj

      def create_logical_interfaces(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
          tenant_name_list = tenant_name_list
          global_conf      = global_conf
          tenant_conf      = tenant_conf
          conf_l  = []
          pr_qfxs = global_conf['pr_qfx']
          if not pr_qfxs:
            return True
          pi_vlan_info = self.retrieve_pi_vlan_info(conn_obj_list=conn_obj_list,pr_qfxs=pr_qfxs)
          existing_li  = self.retrieve_existing_li(conn_obj_list=conn_obj_list)
          conf_lis = []
          for li in existing_li:
              conf_lis.append(":".join(li['fq_name']))
          kwargs_list = []
          pi_list     = []

          pi_obj_dict = {}
          for pr_qfx in pr_qfxs:
              pr_name = pr_qfx['name']
              bms_servers = pr_qfx['bms']
              for bms_server in bms_servers:
                  physical_iface_name = bms_server['tor_interface']
                  pi_obj = self.retrieve_pi_obj(conn_obj_list=conn_obj_list,pr_name=pr_name,physical_iface_name=physical_iface_name)
                  pi_obj_dict[pr_name,physical_iface_name] = pi_obj

          for tenant_name in tenant_name_list:
              tenant_index = get_tenant_index(tenant_conf,tenant_name)
              for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                  vn_index        = 0
                  vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
                  vn_name_pattern = vn_info['vn,name,pattern']
                  vn_count        = vn_info['count']
                  bms_config      = vn_info.get('bms,name',False)
                  if not bms_config:
                     continue
                  li_conf_list = []
                  bms_count  = vn_info['bms,count']
                  tor_list   = vn_info['bms,tor_list']
                  for vn_indx in xrange(vn_count):
                      vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_index)
                      vn_index += 1
                      for bms_i in xrange(bms_count):
                          li_conf = {}
                          li_conf['tenant_name'] = tenant_name
                          li_conf['bms_index']   = bms_i
                          li_conf['vn_name']     = vn_name
                          bms_configured = False
                          li_regex = "%s.bms%s"%(vn_name,str(bms_i))
                          for li in conf_lis:
                            if re.search(li_regex,li):
                              bms_configured = True
                              break
                          if bms_configured:
                             print "BMS: already configured",vn_name,bms_i
                          else:
                              li_conf_list.append(li_conf)
                  vlan_id_list = []
                  for li_conf in li_conf_list:
                      pr_name = pr_qfxs[0]['name']
                      vlan_id = generate_random_vlan_id(pi_vlan_info,pr_name)
                      if not vlan_id:
                         print "ERROR: vlan_id exhausted.."
                         continue
                      pi_vlan_info[pr_name].append(vlan_id)
                      vlan_id_list.append(vlan_id)

                  for pr_qfx in pr_qfxs:
                    pr_name = pr_qfx['name']
                    bms_servers = pr_qfx['bms']
                    physical_interface_list  = []
                    physical_server_mac_list = []
                    physical_server_mgmt_ip  = []
                    for bms_server in bms_servers:
                        physical_interface_list.append(bms_server['tor_interface'])
                        physical_server_mac_list.append(bms_server['physical_server_mac'])
                        physical_server_mgmt_ip.append(bms_server['physical_server_mgmt_ip'])
                    physical_server_mac_list_filter = filter(lambda x:x is not None,physical_server_mac_list)
                    if len(li_conf_list) < len(physical_server_mac_list_filter):
                       server_count_per_pi = 1
                    else:
                       server_count_per_pi = len(li_conf_list)/len(physical_server_mac_list_filter)
                    li_conf_list_g = [li_conf_list[n:n+server_count_per_pi] for n in range(0, len(li_conf_list),server_count_per_pi)]
                    vlan_indx = 0
                    for indx,li_conf_l in enumerate(li_conf_list_g):
                        mac_addr = physical_server_mac_list_filter[indx]
                        mac_indx = physical_server_mac_list.index(mac_addr)
                        physical_iface_name = physical_interface_list[mac_indx]
                        physical_iface_name_m = re.sub(":","__",physical_iface_name)
                        for li_conf in li_conf_l:
                            tenant_index = get_tenant_index(tenant_conf,li_conf['tenant_name'])
                            try:
                               vlan_id      = vlan_id_list[vlan_indx]
                            except IndexError:
                               continue
                            vlan_indx += 1
                            iface_name   = physical_iface_name + ".%s.bms%s.%d"%(li_conf['vn_name'],li_conf['bms_index'],vlan_id)
                            kwargs = {}
                            kwargs['pr_name']        = pr_name
                            kwargs['physical_iface'] = physical_iface_name
                            kwargs['pi_obj']         = pi_obj_dict[pr_name,physical_iface_name]
                            kwargs['tenant_name'] = li_conf['tenant_name']
                            kwargs['vlan_id']     = vlan_id    
                            kwargs['iface_name']  = iface_name
                            kwargs['bms_index']   = li_conf['bms_index']
                            kwargs['mac_addr']    = mac_addr
                            kwargs['vn_name']     = li_conf['vn_name']
                            kwargs['existing_li'] = existing_li
                            kwargs_list.append(kwargs)
                            pi_list.append((pr_name,physical_iface_name))
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_logical_interface(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
                 
      @Process.wrapper
      def delete_physical_interface(self,*arg,**kwarg):
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          pr_name = kwarg['pr_name']
          pis = self.connections.vnc_lib.physical_interfaces_list()['physical-interfaces']
          for pi in pis:
              pi_fq_name  = pi['fq_name']
              router_name = pi_fq_name[1]
              if router_name == pr_name:
                 continue
              try:
                 pi_obj=self.connections.vnc_lib.physical_interface_read(id=pi['uuid'])
                 self.connections.vnc_lib.physical_interface_delete(pi_obj.fq_name)
              except:
                 continue
   
      def delete_physical_interfaces(self,conn_obj_list,thread_count,global_conf,tenant_conf):

          pr_mxs  = global_conf['pr_mx']
          pr_qfxs = global_conf['pr_qfx']
          pr_names = []
          for pr_mx in pr_mxs:
              pr_names.append(pr_mx['name'])
          for pr_qfx in pr_qfxs:
              pr_names.append(pr_qfx['name'])
          kwargs_list = []
          for pr in pr_names:
              kwargs = {}
              kwargs['pr_name'] = pr
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.delete_physical_interface(count=thread_count,conn_obj_list=conn_obj_list, **kwargs)

      @Process.wrapper
      def delete_logical_interface(self,*arg,**kwarg):
          pr_name          = kwarg['pr_name']
          tenant_name_list = kwarg['tenant_name_list']
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          lis              = kwarg['existing_li']
          for li in lis:
              li_fq_name  = li['fq_name']
              router_name = li_fq_name[1]
              if router_name != pr_name:
                 continue
              try: #CHECK
                li_obj = self.connections.vnc_lib.logical_interface_read(id=li['uuid'])
              except:
                continue
              vmis   = li_obj.get_virtual_machine_interface_refs() or []
              delete_li = False
              for vmi in vmis:
                try:
                  dom,t_name,vmi_name = vmi['to']
                  if t_name not in tenant_name_list:
                     delete_li = False
                     break
                  vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                  inst_ips = vmi_obj.get_instance_ip_back_refs() or []
                  for inst_ip in inst_ips:
                      inst_ip_id = inst_ip['uuid']
                      self.connections.vnc_lib.instance_ip_delete(id=inst_ip_id)
                  li_obj.del_virtual_machine_interface(vmi_obj)
                  self.connections.vnc_lib.logical_interface_update(li_obj)
                  self.connections.vnc_lib.virtual_machine_interface_delete(vmi_obj.fq_name)
                except:
                  pass
              if delete_li or len(vmis) == 0:
                 try:
                   self.connections.vnc_lib.logical_interface_delete(li_fq_name)
                 except:
                   traceback.print_exc(file=sys.stdout)
                   pass
              else:
                 print "skipping delete LI",li_fq_name

      def delete_logical_interfaces(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list=[]):

          existing_li = self.retrieve_existing_li(conn_obj_list=conn_obj_list)
          pr_names    = self.retrieve_existing_pr(conn_obj_list=conn_obj_list)
          kwargs_list = []
          for pr in pr_names:
              kwargs = {}
              kwargs['tenant_name_list'] = tenant_name_list
              kwargs['pr_name'] = pr
              kwargs['existing_li'] = existing_li
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.delete_logical_interface(count=thread_count,timeout=1800,conn_obj_list=conn_obj_list,**kwargs)

      @Process.wrapper
      def delete_physical_router(self,*arg,**kwarg):
          pr_name = kwarg['pr_name']
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          try:
            pr_obj = self.connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', unicode(pr_name)])
          except:
            return
          self.connections.vnc_lib.physical_router_delete(pr_obj.fq_name)

      def delete_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf):

          pr_mxs = global_conf['pr_mx']
          pr_qfxs = global_conf['pr_qfx']
          pr_names = []
          for pr_mx in pr_mxs:
              pr_names.append(pr_mx['name'])
          for pr_qfx in pr_qfxs:
              pr_names.append(pr_qfx['name'])
          kwargs_list = []
          for pr in pr_names:
              kwargs = {}
              kwargs['pr_name'] = pr
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.delete_physical_router(count=thread_count,conn_obj_list=conn_obj_list, **kwargs)
          return

      @Process.wrapper
      def create_physical_interface(self,*arg,**kwarg):
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          pr_name                 = kwarg['pr_name']
          physical_interface_list = kwarg['physical_interface_list']
          pr_obj = self.connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', unicode(pr_name)])
          for physical_interface in physical_interface_list:
             try:
                 physical_interface_m = re.sub(":","__",physical_interface)
                 pi = self.connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, physical_interface_m])
             except NoIdError:
                 pi = PhysicalInterface(physical_interface_m, parent_obj = pr_obj,display_name=physical_interface)
                 self.connections.vnc_lib.physical_interface_create(pi)

      def create_physical_interfaces(self,conn_obj_list,thread_count,global_conf,tenant_conf):

          pr_qfxs = global_conf['pr_qfx']
          kwargs_list = []
          for pr in pr_qfxs:
              kwargs = {}
              kwargs['pr_name'] = pr['name']
              bms_servers       = pr['bms']
              kwargs['physical_interface_list'] = []
              for bms in bms_servers :
                  kwargs['physical_interface_list'].append(bms['tor_interface'])
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_physical_interface(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

      def create_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf):
          physical_routers_config = global_conf['pr_mx']
          kwargs_list = []
          for physical_router in physical_routers_config:  
              kwargs = {}
              kwargs['pr,name']     = physical_router['name']
              kwargs['pr,mgmt_ip']  = physical_router['mgmt_ip']
              kwargs['pr,login']    = physical_router['netconf']['uname']
              kwargs['pr,password'] = physical_router['netconf']['password']
              kwargs['pr,junos_si'] = physical_router['netconf']['junos_si']
              kwargs['pr,dataplane_ip'] = physical_router['vtep_ip']
              kwargs['is_tor']          = False
              pr_interface = physical_router.get('pr_interface',None)
              if pr_interface :
                 kwargs['pr,interface_name'] = pr_interface['name']
                 kwargs['pr,interface_vlan'] = pr_interface['vlan']
                 kwargs['pr,interface_vn']   = pr_interface['vn']
                 kwargs['pr,interface_mac']  = pr_interface['mac']
                 kwargs['pr,interface_ip']   = pr_interface['ip']
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_physical_router(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

      @Process.wrapper
      def associate_fip_to_vmi(self,*arg,**kwarg):
         tenant_name    = kwarg['tenant_name']
         tenant_conf    = kwarg['tenant_conf']
         global_conf    = kwarg['global_conf']
         fip_vn_name    = kwarg['fip_vn_name']
         fip_pool_name  = kwarg['fip_pool_name']
         fip_pool_vn_id = kwarg['fip_pool_vn_id']
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         self.connections.orch = self.connections.get_orch_h()
         proj_obj      = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
         fip_fq_name   = ['default-domain',tenant_name,fip_vn_name,fip_pool_name] 
         try:
            fip_pool_obj  = self.connections.vnc_lib.floating_ip_pool_read(fq_name=fip_fq_name)
         except NoIdError:
            print "ERROR: FIP pool %s missing"%str(fip_fq_name)
            return
         vmis = self.connections.vnc_lib.virtual_machine_interfaces_list(parent_id=proj_obj.uuid)['virtual-machine-interfaces']
         attach_fip_vns = []
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                vn_index       = 0
                vn_info        = tenant_conf['tenant,vn_group_list'][vn_group_index]
                attach_fip     = vn_info.get('attach_fip',False)
                if not attach_fip:
                   continue
                vn_count       = vn_info['count']
                vn_name_pattern = vn_info['vn,name,pattern']
                for vn_indx in xrange(vn_count):
                    vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_indx)
                    attach_fip_vns.append(['default-domain',tenant_name,vn_name])
            
         for vmi in vmis:
             vmi_obj = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
             net_ref = vmi_obj.get_virtual_network_refs()[0]['to']
             if net_ref not in attach_fip_vns:
                self.logger.warn("Skipping FIP attach for vmi:%s,%s"%(vmi_obj.fq_name,net_ref))
                continue
             li_ref  = vmi_obj.get_logical_interface_back_refs()
             if li_ref is None:
                 self.logger.warn("INFO: li_ref is none for VMI:%s..skipping FIP attach"%(str(vmi_obj.fq_name)))
                 continue
             fips    = vmi_obj.get_floating_ip_back_refs()
             if fips:
               #self.logger.warn("fip is already attached to VMI..skipping fip attach")
               continue
             else:
               self.logger.warn("attaching fip:%s"%str(vmi_obj.fq_name))
             fip_ip,fip_id = self.connections.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id, project_obj=proj_obj, pool_obj=fip_pool_obj)
             fip_obj = self.connections.vnc_lib.floating_ip_read(id=fip_id)
             fip_obj.set_virtual_machine_interface(vmi_obj)
             fip_obj.set_project(proj_obj)   
             self.connections.vnc_lib.floating_ip_update(fip_obj)
             print "INFO: fip attached to VMI:",vmi_obj.fq_name

      def associate_fip_to_vmis(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
         kwargs_list = []
         vn_index    = 0
         pool_indx   = 0
         fip_vn_name_pattern = None
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
             vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
             vn_name_pattern = vn_info['vn,name,pattern']
             if re.search('Public_FIP_VN',vn_name_pattern):
                fip_vn_name_pattern = vn_name_pattern
         if fip_vn_name_pattern is None:
            return
         vn_info_dict = {}
         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tenant_name_list=tenant_name_list,conn_obj_list=conn_obj_list)
         if ret:
            vn_info_dict.update(ret)
         for tenant_name in tenant_name_list:
             tenant_indx           = get_tenant_index(tenant_conf,tenant_name)
             pool_vn_name          = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                        fip_vn_name_pattern,vn_index)
             kwargs = {}
             kwargs['tenant_name'] = tenant_name
             kwargs['tenant_conf'] = tenant_conf
             kwargs['global_conf'] = global_conf
             kwargs['fip_vn_name'] = pool_vn_name
             kwargs['fip_pool_name'] = generate_fip_pool_name(global_conf,tenant_conf,\
                                          tenant_indx,pool_indx)
             kwargs['fip_pool_vn_id'] = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,pool_vn_name)]
             kwargs_list.append(kwargs)
         if len(kwargs_list) == 0:
            return
         kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
         self.associate_fip_to_vmi(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

      def create_tors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list=[]):
          qfx_config = global_conf['pr_qfx']
          kwargs_list = []
          for qfx in qfx_config:
              kwargs = {}
              kwargs['pr,name']         = qfx['name']
              kwargs['pr,mgmt_ip']      = qfx['mgmt_ip']
              kwargs['pr,dataplane_ip'] = qfx['vtep_ip']
              kwargs['pr,tsn']      = qfx['tsn']
              kwargs['pr,tsn_ip']   = qfx['tsn_ip']
              kwargs['pr,ta']       = qfx['ta']
              kwargs['is_tor']      = True
              kwargs['global_conf'] = global_conf
              kwargs['tenant_conf'] = tenant_conf
              kwargs['tenant_name_list'] = tenant_name_list
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_physical_router(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)


class VrouterGlobalConfig(Base):

      @Process.wrapper
      def update_conf(self,*arg,**kwarg):
          connection_obj = kwarg['connection_obj']
          self.connections = connection_obj.connections
          self.logger      = connection_obj.logger
          encap_obj=EncapsulationPrioritiesType(encapsulation=['VXLAN','MPLSoGRE','MPLSoUDP'])
          conf_obj=GlobalVrouterConfig(encapsulation_priorities=encap_obj, evpn_status='true')
          self.connections.vnc_lib.global_vrouter_config_update(conf_obj)
          #conf_obj = GlobalVrouterConfig(vxlan_network_identifier_mode='auto-configured')
          #self.connections.vnc_lib.global_vrouter_config_update(conf_obj)
          
class Bgpaas(Base):

     @Process.wrapper
     def create(self,*arg,**kwarg):
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name      = kwarg['tenant_name']
         vm_id            = kwarg['vm_id']
         service_name     = kwarg['bgp_service_name']
         project_obj  = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',tenant_name])
         bgpaas_prefix = "bgp"
         i = 0
         j = 0
         fq_name=[u'default-domain',tenant_name,service_name]
         bgpaas_obj = None
         try:
            bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(fq_name=fq_name)
         except NoIdError:
            pass
         if bgpaas_obj is None:
            bgpaas_obj = BgpAsAService(name=service_name,parent_obj=project_obj)
            vm_obj = self.connections.vnc_lib.virtual_machine_read(id=vm_id)
            vmis   = vm_obj.get_virtual_machine_interface_back_refs()
            for vmi in vmis:
                vmi_obj  = self.connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                networks = vmi_obj.get_virtual_network_refs()[0]['to']
                def_dom,t_name,netname = networks
                if re.search('BGP',netname):
                   vmi = vmi_obj
                   break
            inst_ips = vmi.get_instance_ip_back_refs()
            ip_obj = self.connections.vnc_lib.instance_ip_read(id=inst_ips[0]['uuid'])
            bgpaas_obj.add_virtual_machine_interface(vmi) # vSRX VMI
            bgpaas_obj.set_autonomous_system('65000')
            bgpaas_obj.set_display_name(service_name)
            bgpaas_obj.set_bgpaas_ip_address(ip_obj.get_instance_ip_address()) # get instance IP attached to vmi.
            bgp_addr_fams = AddressFamilies(['inet','inet6'])
            bgp_sess_attrs = BgpSessionAttributes(address_families=bgp_addr_fams,hold_time=300)
            bgpaas_obj.set_bgpaas_session_attributes(bgp_sess_attrs)
            self.connections.vnc_lib.bgp_as_a_service_create(bgpaas_obj)

     def create_bgpaas(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        kwargs_list = []

        vm_obj = VM(None)
        vms = vm_obj.list_vms(conn_obj_list=conn_obj_list,tenant_name_list=tenant_name_list)
        
        for i,tenant_name in enumerate(tenant_name_list):
            found = False
            vm_id = None
            for vm in vms:
                if vm['tenant_name'] != tenant_name or not re.search('bgp_vm',vm['vm_name']):
                   continue
                vm_id = vm['id']
                break
            kwargs = {}
            kwargs['tenant_name']  = tenant_name
            kwargs['vm_id']        = vm_id
            kwargs['bgp_service_name'] = 'bgpaas-router'
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.create(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

     @Process.wrapper
     def delete(self,*arg,**kwarg):
         self.connections = kwarg['connection_obj'].connections
         self.logger      = kwarg['connection_obj'].logger
         tenant_name      = kwarg['tenant_name']
         vm_id            = kwarg['vm_id']
         bgp_service_name = kwarg['bgp_service_name']

         vm_obj = self.connections.vnc_lib.virtual_machine_read(id=vm_id)
         vmis   = vm_obj.get_virtual_machine_interface_back_refs()
         vmi    = self.connections.vnc_lib.virtual_machine_interface_read(id=vmis[0]['uuid'])
    
         fq_name = ['default-domain',tenant_name,bgp_service_name]
         try:
            bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(fq_name=fq_name)
         except:
            return
         bgpaas_obj.del_virtual_machine_interface(vmi)
         self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)
         self.connections.vnc_lib.bgp_as_a_service_delete(id=bgpaas_obj.get_uuid())

     def delete_bgpaas(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):

        kwargs_list = []

        for i,tenant_name in enumerate(tenant_name_list):
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['vm_id']       = 'f08e0289-ca32-4b23-b9de-8038dae6f344'
            kwargs['bgp_service_name'] = 'bgpaas-router'
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return

        kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
        self.delete(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)

class ServiceTemplateConfig(Base):

      @Process.wrapper
      def create_service_template(self,*arg,**kwarg):
          st_name        = kwarg['st_name']
          domain_name    = kwarg['domain_name']
          st_fq_name     = [domain_name,st_name]
          domain_fq_name = [domain_name]
          image_name     = kwarg['image_name']
          svc_type       = kwarg['svc_type']
          svc_mode       = kwarg['svc_mode']
          flavor         = kwarg['flavor']
          svc_scaling    = kwarg['svc_scaling']
          ordered_interfaces = kwarg['ordered_interfaces']
          if_list            = kwarg['if_list']
          static_routes      = kwarg['static_routes']
          shared_ip          = kwarg['shared_ip']
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          try:
            svc_template = self.connections.vnc_lib.service_template_read(fq_name=st_fq_name)
            self.logger.warn("Service template: %s already exists"%st_fq_name)
            return
          except NoIdError:
            domain = self.connections.vnc_lib.domain_read(fq_name=domain_fq_name)
            svc_template = ServiceTemplate(name=st_name,parent_obj=domain)
            svc_properties = ServiceTemplateType()
            svc_properties.set_image_name(image_name)
            svc_properties.set_service_type(svc_type)
            svc_properties.set_service_mode(svc_mode)
            svc_properties.set_service_scaling(svc_scaling)
            # Add flavor if not already added
            # self.nova_h.get_flavor(flavor)
            svc_properties.set_flavor(flavor)
            svc_properties.set_ordered_interfaces(ordered_interfaces)
            for i,itf in enumerate(if_list):
                if_type = ServiceTemplateInterfaceType(
                    service_interface_type=itf, shared_ip=shared_ip[i],static_route_enable=static_routes[i])
                if_type.set_service_interface_type(itf)
                svc_properties.add_interface_type(if_type)
            svc_template.set_service_template_properties(svc_properties)
            self.connections.vnc_lib.service_template_create(svc_template)  

      def create_service_templates(self,conn_obj_list,thread_count,global_conf,tenant_conf):
          service_templates = global_conf.get('service_templates',None)
          if service_templates is None:
             return
          kwargs_list = []
          for st in service_templates:
              kwargs = {}
              kwargs['st_name']            = st['name']
              kwargs['domain_name']        = "default-domain"
              kwargs['ordered_interfaces'] = True 
              kwargs['svc_type']           = st['service_type']
              kwargs['svc_mode']           = st['service_mode']
              kwargs['svc_scaling']        = st['scaling']
              kwargs['image_name']         = st['image_name']
              kwargs['flavor']             = st['instance_flavor']
              kwargs['if_list']            = st['interface_list']
              kwargs['static_routes']      = st['static_routes']
              kwargs['shared_ip']          = st['shared_ip']
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_service_template(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
         
      @Process.wrapper
      def create_service_instance(self,*arg,**kwarg):
          svc_mode      = kwarg['service_mode']
          svc_scaling   = kwarg['service_scaling']
          st_name       = kwarg['service_template_name']
          si_name       = kwarg['si_name']
          tenant_name   = kwarg['tenant_name']
          si_fq_name    = ['default-domain',tenant_name,si_name] 
          st_fq_name    = ['default-domain',st_name]
          left_vn_name  = kwarg.get('left,vn_name',None)
          right_vn_name = kwarg.get('right,vn_name',None)
          mgmt_vn_name  = kwarg.get('mgmt,vn_name',None)
          max_inst      = kwarg['si_count']
          if_vn_dict    = kwarg['if_vn_dict']
          left_vn_name  = if_vn_dict.get('left',None)
          right_vn_name  = if_vn_dict.get('right',None)
          mgmt_vn_name   = if_vn_dict.get('management',None)
          self.connections = kwarg['connection_obj'].connections
          self.logger      = kwarg['connection_obj'].logger
          static_route     = [None,None,None]
          if svc_scaling == True:
            if svc_mode == 'in-network-nat':
                if_list = [['management', False, False],
                           ['left', True, False], ['right', False, False]]
            else:
                if_list = [['management', False, False],
                           ['left', True, False], ['right', True, False]]
          else:
            if_list = [['management', False, False],
                       ['left', False, False], ['right', False, False]]
          self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
          st_obj = self.connections.vnc_lib.service_template_read(fq_name=st_fq_name)
          fixture = SvcInstanceFixture(
                connections=self.connections, inputs=self.connections.inputs,
                domain_name='default-domain', project_name=tenant_name, si_name=si_name,
                svc_template=st_obj, if_list=if_list,management_virtual_network=mgmt_vn_name,
                left_vn_name=left_vn_name, right_vn_name=right_vn_name, do_verify=False, max_inst=max_inst, static_route=static_route)
          fixture.setUp()


      def create_service_instances(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_name_list):
          service_instances = tenant_conf.get('service_instances',None)
          if service_instances is None:
             return
          service_template = global_conf.get('service_templates',None)
          kwargs_list = []
          for tenant_name in tenant_name_list:
            tenant_indx       = get_tenant_index(tenant_conf,tenant_name)
            for si in service_instances:
              kwargs = {}
              kwargs['si_name']            = si['name']
              kwargs['tenant_name']        = tenant_name
              kwargs['si_count']              = si['count']
              kwargs['service_template_name'] = si['service_template_name']
              kwargs['num_of_instances']      = si['num_of_instances']
              kwargs['service_mode']          = service_template[0]['service_mode']
              kwargs['service_scaling']       = service_template[0]['scaling']
              static_interfaces = si['interface_static']
              if_vn_dict = {}
              for iface in static_interfaces:
                  iface_type = iface['interface_type']
                  vn_name    = iface['vn_name']
                  if iface_type == 'left' or iface_type == 'right':
                     vn_indx    = 0
                     vn_name    = generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name,vn_indx)
                  if_vn_dict[iface_type] = vn_name
              kwargs['if_vn_dict'] = if_vn_dict
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
          self.create_service_instance(count=thread_count,conn_obj_list=conn_obj_list,**kwargs)
 
