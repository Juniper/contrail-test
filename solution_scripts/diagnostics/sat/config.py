import copy
import ipaddr
import multiprocessing as mp
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
from multiprocessing import Process, Queue , Pool,TimeoutError,Manager
from lib import *
import time
from common.log_orig import ContrailLogger

#from vnc_api.vnc_api import *

from multiprocessing import TimeoutError, Pool
from copy_reg import pickle
from types import MethodType

class CIDR:

  def __init__(self,cidr):
   self.cidr  = cidr
   self.index = 0
   self.mask  = self.cidr.split("/")[1]

  def get_next_cidr(self):
    lock.acquire()
    if self.index == 0 :
      self.index += 1
    else: 
      ip = IPNetwork(self.cidr)[0]
      new_ip = ipaddr.IPAddress(ip) + 256
      self.cidr = str(new_ip) + "/" + self.mask
    lock.release()
    return self.cidr

class ProjectNotFound(Exception):
      def __init__(self, value):
          self.value = value
      def __str__(self):
          return repr(self.value)
lock = threading.Lock()

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

def generate_tenant_name_list(tenant_conf,tenant_name):
    tenant_name_prefix       = tenant_conf['tenant,name_prefix']
    tenant_count             = tenant_conf['tenant,count']
    if tenant_name == 'all':
       tenant_name_list      = [tenant_name_prefix + str(i) for i in xrange(tenant_count)]
    else:
       tenant_name_list = [tenant_name]
    return tenant_name_list

def generate_ipam_name(global_conf,tenant_conf,tenant_index):
    test_id  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    ipam_name_pattern        = tenant_conf['ipam,name,pattern']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    ipam_name = re.sub(tenant_index_replace_str,str(tenant_index),ipam_name_pattern)
    ipam_name = re.sub(test_id_replace_str,str(test_id),ipam_name)
    return ipam_name

def get_tenant_index(tenant_conf,tenant_name):
    tenant_name_prefix  = tenant_conf['tenant,name_prefix'] 
    return int(re.search(tenant_name_prefix+'(\d+)',tenant_name).group(1))

def get_vn_type(vn_name):
    vn_group_list = ['Private_SNAT_VN','Private_VN','Private_LB_VIP_VN','Private_LB_Pool_VN',
                     'SNAT_GW_VN','Public_FIP_VN']
    for vn in vn_group_list:
        if re.search(vn,vn_name):
           return vn 

def generate_rt_number():
    lock.acquire()
    while True:
       rt = random.randint(1000000,3000000)
       ret = check_if_rt_already_used(rt_number=rt)
       if not ret:
         break
    lock.release()
    return rt

def generate_cidr(tenant_name,vn_type):
    lock.acquire()
    #ip_group = {}
    #ip_group['public_vn']  = [i for i in xrange(10,171)]
    #ip_group['private_vn'] = [i for i in xrange(173,199)]
    #ip_group['private_snat_vn'] = [i for i in xrange(173,199)]
    #ip_group['private_lb_pool'] = [i for i in xrange(200,210)]
    #ip_group['private_vip']     = [i for i in xrange(211,223)]
    ip_group = {'Private_SNAT_VN':[11],'Private_VN':[12],'Private_LB_VIP_VN':[13],'Private_LB_Pool_VN':[14],'SNAT_GW_VN':[15],'Public_FIP_VN':[16]}
    while True:
       first_octet  = random.choice(ip_group[vn_type])
       second_octet = random.randint(0,254)
       third_octet  = random.randint(0,254)
       fourth_octet = 0
       cidr = "%i.%i.%i.%i/16" %(first_octet,second_octet,third_octet,fourth_octet)
       if not check_if_cidr_already_used(tenant_name=tenant_name,vn_type=vn_type,cidr=cidr):
          break
    lock.release()
    return cidr
    
def single_thread(debug_enabled=False):
    def wrapper1(func):
      def wrapper2(*args,**kwargs):
        if debug_enabled:
           return func(*args,**kwargs)
        else:
           manager = Manager()
           return_dict = manager.dict()
           kwargs['return_dict'] = return_dict
           p = mp.Process(target=func,args=args,kwargs=kwargs)
           p.start()
           p.join()
           if not return_dict.has_key('value'):
             return
           else:
             return return_dict['value']
          
      return wrapper2
    return wrapper1 
 
  
def parallel_threads(debug_enabled=False):
    def wrapper1(func):
      def wrapper2(self,*args,**kwargs):
        thread_count = kwargs.pop('thread_count')
        args_list = kwargs.pop('args_list')
        kwargs_list = kwargs.pop('kwargs_list')
        n_instances = len(args_list)
        if int(thread_count) == 1 or debug_enabled: # serial
           for i in xrange(n_instances):
             if debug_enabled:
                func(self,args_list[i],kwargs_list[i])
             else:
                p = mp.Process(target=func,args=(self,args_list[i],kwargs_list[i]))
                p.start()
                p.join()
        else:
           processes = []
           for i in xrange(n_instances):
               p = mp.Process(target=func,args=(self,args_list[i],kwargs_list[i]))
               processes.append(p)
           for p in processes:
               p.start()
           for p in processes:
               p.join()
      return wrapper2
    return wrapper1

@single_thread(debug_enabled=False)
def check_if_rt_already_used(*args,**kwargs):
    return_dict    = kwargs.get('return_dict',None)
    rt_number = kwargs['rt_number']
    obj = Project(None)
    obj.get_connection_handle()
    vn_list = obj.connections.vnc_lib.virtual_networks_list()['virtual-networks']
    rt_list = []
    for vn in vn_list:
        vn_id = vn['uuid']
        vn_obj = obj.connections.vnc_lib.virtual_network_read(id=vn_id)
        ret = vn_obj.get_route_target_list()
        if ret and ret.get_route_target():
           rt_list.append(int(ret.get_route_target()[0].split(":")[-1]))
    if rt_number in rt_list:
        return_flag = True
    else:
        return_flag = False
    
    if return_dict is not None:
       return_dict['value'] = return_flag

    return return_flag

@single_thread(debug_enabled=False)
def check_if_cidr_already_used(*args,**kwargs):
    return_dict    = kwargs.get('return_dict',None)
    tenant_name = kwargs['tenant_name']
    vn_type     = kwargs['vn_type']
    cidr        = kwargs['cidr']
    existing_cidr = {}
    obj = Project(None)
    obj.get_connection_handle()
    ipams_list = obj.connections.vnc_lib.network_ipams_list()['network-ipams']
    for ipam in ipams_list:
       ipam_id = ipam['uuid']
       ipam_obj = obj.connections.vnc_lib.network_ipam_read(id=ipam_id)
       virtual_nw_back_refs = ipam_obj.get_virtual_network_back_refs()
       if virtual_nw_back_refs is None:
          continue
       for nw in virtual_nw_back_refs:
           domain,t_name,vn_name = nw['to']
           subnets = nw['attr']['ipam_subnets']
           for subnet in subnets:
             cidr_l = str(subnet['subnet']['ip_prefix']) + "/" + str(subnet['subnet']['ip_prefix_len'])
             existing_cidr['%s'%(cidr_l)]=True
    if existing_cidr.has_key('%s'%(cidr)):
        return_flag = True
    else:
        return_flag = False

    if return_dict is not None:
       return_dict['value'] = return_flag

    return return_flag


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

        for i in xrange(10):
          try:
             self.inputs = ContrailTestInit(self.ini_file,logger=self.logger)
             self.inputs.setUp()
             self.connections= ContrailConnections(inputs=self.inputs,logger=self.logger,project_name=project_name)
             self.connections.get_vnc_lib_h() # will set self.connections.vnc_lib in the object
             self.connections.inputs.project_name=project_name
             self.auth = self.connections.get_auth_h()
             break
          except Exception as ex:
            if type(ex).__name__ == "NetworkError" :
              self.logger.info("Exception happened in ContrailConnections..type : %s..retrying after one second"%type(ex).__name__)   
              time.sleep(1)
            else:
              self.logger.warn("Exception happened in ContrailConnections..type : %s"%type(ex).__name__)
              raise ProjectNotFound("Info: Tenant %s missing.."%project_name)
              
 
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
           print "rule:",rule
           rules.append(rule)
        return rules

    @parallel_threads(debug_enabled=False)
    def create_policy(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        policy_name = kwargs['policy_name']
        rules       = kwargs['rules']
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping create policy"%tenant_name
           return
        try:   
           self.connections.vnc_lib.network_policy_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(policy_name)])
           print "Policy: %s already available...skipping create.."%str([u'default-domain',u'%s'%tenant_name,unicode(policy_name)])
           return
        except NoIdError :
           print "Policy: %s not available..creating.."%str([u'default-domain',u'%s'%tenant_name,unicode(policy_name)])
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        self.create(self.connections.inputs,policy_name,rules,self.connections)

    def create_policies(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
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
        args_list = [i for i in kwargs_list]
        self.create_policy(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)
   
    @parallel_threads(debug_enabled=False)
    def delete_policy(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        policy_name = kwargs['policy_name']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping delete policy"%tenant_name
           return
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        try:
          policy_obj = self.connections.vnc_lib.network_policy_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(policy_name)])
        except:
          return
        policy_id = policy_obj.uuid
        self.connections.vnc_lib.network_policy_delete(id=policy_id)

    def delete_policies(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list    = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_indx = get_tenant_index(tenant_conf,tenant_name)
            policy_name = generate_policy_name(global_conf,tenant_conf,tenant_indx)
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['policy_name'] = policy_name
            kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.delete_policy(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    def attach(self,tenant_name,vn_fq_name,vn_uuid,policy_name):
        policy_obj = Policy(self.connections)
        policy_obj = self.connections.vnc_lib.network_policy_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(policy_name)])
        vn_obj     = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.add_network_policy(policy_obj,VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0)))
        self.connections.vnc_lib.virtual_network_update(vn_obj)
        return

    def detach(self,tenant_name,vn_fq_name):
        vn_obj     = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.set_network_policy_list([],True)
        self.connections.vnc_lib.virtual_network_update(vn_obj)
        return

    @parallel_threads(debug_enabled=False)
    def attach_policy(self,args,kwargs):
        tenant_name           = kwargs['tenant_name'] 
        vn_id                 = kwargs['vn_id']
        policy_name           = kwargs['policy_name']
        vn_fq_name            = kwargs['vn_fq_name']
        domain,tenant,vn_name = vn_fq_name
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping attach policy"%tenant_name
           return
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        self.attach(tenant_name,vn_fq_name,vn_id,policy_name)

    def attach_policies(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        vns_list    = []
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
               ret      = list_vn(tenant_name=tenant_name,vn_name_prefix=vn_name)
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
        count = len(kwargs_list)
        args_list = [i for i in xrange(count)]
        self.attach_policy(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def detach_policy(self,args,kwargs):
        tenant_name           = kwargs['tenant_name']
        vn_fq_name            = kwargs['vn_fq_name']
        domain,tenant,vn_name = vn_fq_name
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping detach policy"%tenant_name
           return
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        self.detach(tenant_name,vn_fq_name)

    def detach_policies(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        vn_list     = []
        for tenant_name in tenant_name_list:
            ret = list_vn(tenant_name=tenant_name)
            if ret:
               vn_list.extend(ret)
        if not len(vn_list):
           return
        for vn in vn_list:
           tenant_name,vn_id,vn_fq_name = vn
           kwargs = {}
           kwargs['tenant_name'] = tenant_name
           kwargs['vn_fq_name']  = vn_fq_name
           kwargs_list.append(kwargs)
        count = len(kwargs_list)
        args_list = [i for i in xrange(count)]
        self.detach_policy(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

class Project(Base):

    def create(self, name):
        self.fixture = ProjectFixture(project_name=name, connections=self.connections)
        self.fixture.setUp()
        project_id = self.fixture.get_uuid()
        self.add_user_to_tenant(project_id)
        return project_id

    @parallel_threads(debug_enabled=False)
    def create_tenant(self,args,kwargs):
        tenant_name = args
        self.get_connection_handle()

        uuid = self.auth.get_project_id("default-domain",tenant_name)
        if uuid :
           print "Tenant %s already exists with UUID:%s..skipping create"%(tenant_name,uuid)
           return
        project_id  = self.create(tenant_name)

    def create_tenants(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = [{} for i in xrange(len(tenant_name_list))]
        self.create_tenant(thread_count=thread_count,args_list=tenant_name_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def update_security_group(self,args,kwargs):
        tenant_name = args
        self.get_connection_handle()
        obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
        self.update_default_sg(uuid=obj.uuid)

    def update_security_groups(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = [{} for i in xrange(len(tenant_name_list))]
        self.update_security_group(thread_count=thread_count,args_list=tenant_name_list,kwargs_list=kwargs_list)
    
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

    @parallel_threads(debug_enabled=False)
    def delete_tenant(self,args,kwargs):
    
        tenant_name = args
        self.get_connection_handle()
        projects_list = self.connections.vnc_lib.projects_list()['projects']
        uuid = None
        for proj in projects_list :
           fq_name = proj['fq_name']
           if fq_name == [u'default-domain', u'%s'%tenant_name]:
              uuid = proj['uuid']
              break
    
        if uuid:
           self.delete(uuid)
        else :
           print "INFO: project %s not found..skipping delete"%tenant_name
    
    def delete_tenants(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = [{} for i in xrange(len(tenant_name_list))]
        self.delete_tenant(thread_count=thread_count,args_list=tenant_name_list,kwargs_list=kwargs_list)

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

    @parallel_threads(debug_enabled=False)
    def delete_record(self,args,kwargs):
        domain_name    = kwargs.get('domain_name',None)
        forwarder_name = kwargs.get('forwarder_name',None)
        self.get_connection_handle()
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

    @parallel_threads(debug_enabled=False)
    def create_record(self,args,kwargs):

        forwarder     = kwargs['forwarder'] 
        rec_name      = kwargs['rec_name']  
        vdns_rec_data = kwargs['rec_data']  
        rec_class     = kwargs['rec_class'] 
        rec_ttl       = kwargs['rec_ttl']   
        rec_type      = kwargs['rec_type']   
        rec_data      = kwargs['rec_data']   

        if forwarder is None:
          return 
        self.get_connection_handle()

        try:
          self.connections.vnc_lib.virtual_DNS_record_read(fq_name=['default-domain',forwarder.split(':')[-1],rec_name])
          print "Record: default-domain:%s found..skipping create"%rec_name
          return
        except NoIdError:
          print "default-domain:%s NOT found.."%rec_name
          pass  # continue with record creation  

        vdns_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name_str = forwarder)
        vdns_rec_data = VirtualDnsRecordType(rec_name, rec_type, rec_class, rec_data, int(rec_ttl))
        vdns_rec_obj = VirtualDnsRecord(rec_name, vdns_obj, vdns_rec_data)
        self.connections.vnc_lib.virtual_DNS_record_create(vdns_rec_obj)

    @parallel_threads(debug_enabled=False)
    def create_vdns(self,args,kwargs):

        name        = kwargs['vdns_name']
        domain_name = kwargs['domain']
        dns_domain  = kwargs['vdns_domain_name']
        dyn_updates = kwargs['vdns_dyn_updates']
        rec_order   = kwargs['vdns_rec_order']
        ttl         = kwargs['vdns_ttl']
        next_vdns   = kwargs['vdns_next_vdns']
        fip_record  = kwargs['vdns_fip_record']
        reverse_resolution = kwargs['vdns_reverse_resolution']
        
        self.get_connection_handle()

        domain_name_list = []
        domain_name_list.append(domain_name)
        domain_name_list_list = list(domain_name_list)
        try:
            domain_obj = self.connections.vnc_lib.domain_read(fq_name=domain_name_list_list)
            print 'Domain ' + domain_name + ' found!'
        except NoIdError:
            print 'Domain ' + domain_name + ' not found!'

        if next_vdns and len(next_vdns):
          try:
           next_vdns_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name_str = next_vdns)
           print 'Virtual DNS ' + next_vdns + ' found!'
          except NoIdError:
           print 'Virtual DNS ' + next_vdns + ' not found!'

        try:
          self.connections.vnc_lib.virtual_DNS_read(fq_name=[u'%s'%domain_name,u'%s'%name])
          print "Virtual DNS " + name + " found..skipping create.."
          return
        except NoIdError: 
          print "Virtual DNS " + name + " not found..creating it.."

        vdns_str = ':'.join([domain_name, name])
        vdns_data = VirtualDnsType(domain_name=dns_domain, dynamic_records_from_client=dyn_updates, record_order=rec_order, default_ttl_seconds=int(ttl),next_virtual_DNS=next_vdns,reverse_resolution=reverse_resolution,floating_ip_record=fip_record)

        domain_obj =  Domain(name=domain_name)
        dns_obj = VirtualDns(name, domain_obj,
                             virtual_DNS_data = vdns_data)
        self.connections.vnc_lib.virtual_DNS_create(dns_obj)
        #obj = vnc_lib.virtual_DNS_read(id = dns_obj.uuid)


    def create_mgmt_vdns_tree(self,thread_count,global_conf,tenant_conf):
        mgmt_vdns_domain_name_pattern = global_conf.get('vdns,domain_name,pattern',None)
        if mgmt_vdns_domain_name_pattern is None:
           return
        mgmt_vdns_domain_name         = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),mgmt_vdns_domain_name_pattern)

        domain_list = []
        domain_list.append(mgmt_vdns_domain_name)
        self.create_vdns_tree(global_conf,tenant_conf,domain_list)

    def create_data_vdns_tree(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        domain_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            tenant_vdns_domain_name = generate_domain_name(global_conf,tenant_conf,tenant_index)
            domain_list.append(tenant_vdns_domain_name)
        self.create_vdns_tree(global_conf,tenant_conf,domain_list)

    def create_vdns_tree(self,global_conf,tenant_conf,domain_list):
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
              self.create_vdns(thread_count=1,args_list=[1,],kwargs_list=[vdns_conf])

              conf = {}
              conf['forwarder']  = vdns_conf['vdns_next_vdns']
              conf['rec_name']   = re.sub("\.","-",vdns_conf['vdns_domain_name'])
              conf['rec_data']   = "default-domain:%s"%conf['rec_name']
              conf['rec_ttl']    = 86400
              conf['rec_type']   = "NS"
              conf['rec_class']  = "IN"
              self.create_record(thread_count=1,args_list=[1,],kwargs_list=[conf])

    def delete_record_per_tenant(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            domain_server_name  = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            forwarder_name  = "-".join(domain_server_name.split("-")[1:])
            kwargs = {}
            kwargs['domain_name']    = domain_server_name
            kwargs['forwarder_name'] = forwarder_name
            kwargs_list.append(kwargs) 
        args_list = [i for i in xrange(len(kwargs_list))]
        self.delete_record(thread_count=len(args_list),args_list=args_list,kwargs_list=kwargs_list)

    def delete_vdns_tree(self,args,kwargs):

       root_domain  = kwargs['root_domain'] 
       fq_name      = kwargs['fq_name']

       self.get_connection_handle()

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
          kw = { 'root_domain' : root_domain , 'fq_name':":".join(vdns['fq_name']) }
          self.delete_vdns_tree(1,kw)
          vdns_list = self.connections.vnc_lib.virtual_DNSs_list()['virtual-DNSs']
       
       if fq_name == root_domain :
           print "INFO: reached root domain :%s..clean up done"%root_domain
       print "deleting vdns:",fq_name
       try:
         self.connections.vnc_lib.virtual_DNS_delete(id=current_vdns_uuid)
       except:
         pass
     
    def delete_vdns(self):

       self.delete_record(thread_count=1,args_list=[1,],kwargs_list=[{}]) 
       root_domain = 'default-domain:soln-com'
       kwargs = {'root_domain':root_domain ,'fq_name':root_domain}
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

    @parallel_threads(debug_enabled=False)
    def create_ipam(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        ipam_name   = kwargs['ipam_name']
        domain_server_name = kwargs['domain_server_name']
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping create IPAM"%tenant_name
           return
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        try:
           self.connections.vnc_lib.network_ipam_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(ipam_name)])
           print "IPAM: %s already available...skipping create.."%str([u'default-domain',u'%s'%tenant_name,unicode(ipam_name)])
           return
        except NoIdError :
           print "IPAM: %s not available..creating.."%str([u'default-domain',u'%s'%tenant_name,unicode(ipam_name)])

        domain_obj = self.connections.vnc_lib.virtual_DNS_read(fq_name=[u"default-domain",u"%s"%domain_server_name])
        vdns_id = domain_obj.uuid
        self.create(ipam_name,vdns_id)

    def create_ipams(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        ipam_count          = tenant_conf['ipam,count']
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            domain_server_name  = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            ipam_name    = generate_ipam_name(global_conf,tenant_conf,tenant_index)
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['ipam_name']   = ipam_name 
            kwargs['domain_server_name'] = domain_server_name
            kwargs_list.append(kwargs)

        args_list = [1 for i in xrange(len(kwargs_list))]       
        self.create_ipam(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    def delete(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        ipam_fixture.delete(verify=True)

    @parallel_threads(debug_enabled=False)
    def delete_ipam(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        ipam_name   = kwargs['ipam_name']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound :
           return
        except Exception as e:
           self.logger.warn("Got exception as %s"%e + "..skipping delete ipam")
           print "DEBUG: Tenant %s missing..skipping delete IPAM"%tenant_name
           return
        self.connections.api_server_inspect = self.connections.get_api_server_inspect_handles()
        self.quantum_h = self.connections.get_network_h()
        ipam_obj = None
        try:
           ipam_obj = self.connections.vnc_lib.network_ipam_read(fq_name=[u'default-domain',u'%s'%tenant_name,u'%s'%ipam_name])
        except:
          print "ipam: %s missing..skipping delete"%str([u'default-domain',u'%s'%tenant_name,u'%s'%ipam_name])
          return
        ipam_id = ipam_obj.uuid
        self.delete(ipam_id)

    def delete_ipams(self,thread_count,global_conf,tenant_conf,tenant_name):

        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        ipam_count          = tenant_conf['ipam,count']
      
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            domain_name  = generate_domain_name(global_conf,tenant_conf,tenant_index)
            ipam_name    = generate_ipam_name(global_conf,tenant_conf,tenant_index)
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['ipam_name']   = ipam_name 
            kwargs['domain_name'] = domain_name
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0 :
           return
        args_list = [1 for i in xrange(len(kwargs_list))]
        self.delete_ipam(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    def verify(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        assert ipam_fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = IPAMFixture(connections=self.connections, uuid=uuid)
        return self.fixture

@single_thread(debug_enabled=False)
def retrieve_vm_info(*args,**kwargs):
    tenant_name   = kwargs['tenant_name']
    tenant_conf   = kwargs['tenant_conf']
    global_conf   = kwargs['global_conf']
    return_dict    = kwargs.get('return_dict',None)
    try:
      obj = Project(None)
      obj.get_connection_handle()
    except ProjectNotFound:
       print "DEBUG: Tenant %s missing..skipping VN list.."%tenant_name
       return
    obj.connections.orch = obj.connections.get_orch_h()
    tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
    tenant_info = {}
    fips = obj.connections.vnc_lib.floating_ips_list()['floating-ips']
    fip_info = {}
    for fip in fips:
        domain,t_name,vn_name,poll_name,fip_id=fip['fq_name']
        fip_obj = obj.connections.vnc_lib.floating_ip_read(id=fip_id)
        try:
           iface_id  = fip_obj.virtual_machine_interface_refs[0]['uuid']
        except:
           continue
        iface_obj = obj.connections.vnc_lib.virtual_machine_interface_read(id=iface_id)
        mac_addr  = iface_obj.get_virtual_machine_interface_mac_addresses().get_mac_address()[0]
        fixed_ip = fip_obj.get_floating_ip_fixed_ip_address()
        fip_info[mac_addr] = fip_obj.get_floating_ip_address()

    for tenant_name in tenant_name_list:
       try:
          proj_obj  = obj.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
       except:
          continue
       tenant_id = proj_obj.uuid
       net_list  = obj.connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
       #vn_list   = []
       #for vn in net_list:
       #    if re.search('%s'%vn_group_name,vn['fq_name'][-1]):
       #       vn_list.append(vn['fq_name'][-1])
       vms_all   = obj.connections.orch.get_vm_list(project_id=tenant_id)
       mgmt_vn_name = generate_mgmt_vn_name(global_conf,tenant_conf)
       vn_group_info = {}
       for vn in net_list:
           vn_name = vn['fq_name'][-1]
           vms_filtered = filter_vms_in_vn(vms_all,[vn_name])
           vm_info_list = []
           for vm,vn_name in vms_filtered:
               addr    = vm.addresses
               vm_info = {}
               vm_info['name']         = vm.name
               vm_info['ip_addr,mgmt'] = addr[mgmt_vn_name] [0]['addr']
               vm_info['ip_addr,data'] = addr[vn_name][0]['addr']
               data_mac_addr = addr[vn_name][0]['OS-EXT-IPS-MAC:mac_addr']
               vm_info['ip_addr,fip'] = fip_info.get(data_mac_addr,None)
               vm_info_list.append(vm_info)
           vn_name = vn_name.split(".")[-1]
           vn_group_info[vn_name] = vm_info_list
       tenant_info[tenant_name] = vn_group_info
    if return_dict is not None:
       return_dict['value'] = tenant_info
    return tenant_info


@single_thread(debug_enabled=False)
def list_vn(*args,**kwargs):
    tenant_name    = kwargs['tenant_name']
    vn_name_prefix = kwargs.get('vn_name_prefix',None)
    return_dict    = kwargs.get('return_dict',None)
    try:
      obj = Project(tenant_name)
      obj.get_connection_handle()
    except ProjectNotFound:
       print "DEBUG: Tenant %s missing..skipping VN list.."%tenant_name
       return
    obj.connections.orch = obj.connections.get_orch_h() 
    try:
      proj_obj  = obj.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
    except:
      return
    tenant_id = proj_obj.uuid
    net_list  = obj.connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
    vnet_list = []
    for vn in net_list:
       if vn_name_prefix is None or re.search('^%s'%vn_name_prefix,vn['fq_name'][-1]):
          vnet_list.append((tenant_name,vn['uuid'],vn['fq_name']))
    if return_dict is not None:
       return_dict['value'] = vnet_list
    return vnet_list

@single_thread(debug_enabled=False)
def get_router_id(*args,**kwargs):
    tenant_name = kwargs['tenant_name']
    router_name  = kwargs['router_name']
    return_dict = kwargs.get('return_dict',None)
    
    try:
       obj = Project(None)
       obj.get_connection_handle(tenant_name)
    except ProjectNotFound:
       print "DEBUG: Tenant %s missing..error in identifying FIP VN id"%tenant_name
       return
    try:
      router_obj = obj.connections.vnc_lib.logical_router_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(router_name)])
      if return_dict != None:
         return_dict['value'] = router_obj.uuid
    except:
      pass
    return router_obj.uuid

@single_thread(debug_enabled=False)
def get_vn_ids(*args,**kwargs):
    return_dict = kwargs.get('return_dict',None)
    tenant_name = kwargs['tenant_name']
    vn_names_list = kwargs.get('vn_names_list',[])
    try:
      obj = Project(tenant_name)
      obj.get_connection_handle()
    except ProjectNotFound:
      print "INFO: tenant :%s missing..skipping..."%tenant_name
      return   
    vn_info_dict = {}
    try:
      project_obj = obj.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
    except:
      print "INFO: tenant :%s missing..skipping..."%tenant_name
      return
    vns = project_obj.get_virtual_networks()
    if not vns:
      return 
    for vn in vns:
           vn_info_dict[":".join(vn[u'to'])] = vn[u'uuid']
    if return_dict != None:
       return_dict['value'] = vn_info_dict  
    return vn_info_dict

def filter_vms_in_vn(vms,vn_names):

    vm_list = []
    
    for vm in vms:
        vm_iface_names = vm.networks.keys()
        if set(vm_iface_names).intersection(set(vn_names)):
           vm_list.append((vm,list(set(vm_iface_names).intersection(set(vn_names)))[0]))
    return vm_list

@single_thread(debug_enabled=False)
def list_vms(*args,**kwargs):
    tenant_name = kwargs['tenant_name']
    vn_list     = kwargs.get('vn_list',[])
    return_dict = kwargs.get('return_dict',None)
    try:
      obj = Project(tenant_name)
      obj.get_connection_handle()
    except :
      print "Project %s not found..skipping vm list"%tenant_name
      return
    obj.connections.orch = obj.connections.get_orch_h()
    vms = []
    try:
      proj_obj = obj.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])
    except:
      return
    tenant_id = proj_obj.uuid
    vms_all = obj.connections.orch.get_vm_list(project_id=tenant_id)
    if len(vn_list):
       vms_filtered = filter_vms_in_vn(vms_all,vn_list)
    else:
       vms_filtered = [(vm,"") for vm in vms_all]
    vms_list = []
    for vm_obj,vn_name in vms_filtered:
        vm = {}
        vm['tenant_name'] = tenant_name
        vm['vn_name']     = vn_name
        vm['id']          = vm_obj.id
        vm['ip']          = vm_obj.addresses
        vms_list.append(vm)
    if return_dict != None:
       return_dict['value'] = vms_list
    return vms_list

class VN(Base):
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

    @parallel_threads(debug_enabled=False)
    def add_extend_to_pr(self,args,kwargs):

        tenant_name = kwargs['tenant_name']
        vn_name     = kwargs['vn_name']
        router_list = kwargs['router_list']
        try:
           self.get_connection_handle()
        except :
           print "ERROR: creating connection.."
           return
        try:
           vn_obj = self.connections.vnc_lib.virtual_network_read(fq_name=[u'default-domain', u'%s'%tenant_name, u'%s'%vn_name])
        except:
           return
        for router_name in router_list:
           try:
              pr_obj = self.connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', u'%s'%router_name])
           except:
              print "ERROR: router %s missing..."%router_name
              continue
           pr_obj.add_virtual_network(vn_obj)
           self.connections.vnc_lib.physical_router_update(pr_obj)

    @parallel_threads(debug_enabled=False)
    def delete_extend_to_pr(self,args,kwargs):

        tenant_name      = kwargs['tenant_name']
        physical_routers = kwargs['mx_list']
        vn_name          = kwargs['vn_name']
        try:
           self.get_connection_handle()
        except :
           print "ERROR: creating connection.."
           return
        vn_fq_name = vn_name[-1]
        
        try:
           vn_obj = self.connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        except:
           return
        for router_name in physical_routers:
           try:
              pr_obj = self.connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', u'%s'%router_name])
           except:
              print "ERROR: router %s missing..."%router_name
              continue
           pr_obj.del_virtual_network(vn_obj)
           self.connections.vnc_lib.physical_router_update(pr_obj)

    def delete_extend_to_physical_routers(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_count             = tenant_conf['tenant,count']
        tenant_name_list         = generate_tenant_name_list(tenant_conf,tenant_name)
        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])
        kwargs_list = []
        for tenant_name in tenant_name_list:
             vn_list = list_vn(tenant_name=tenant_name)
             if not vn_list:
                continue
             for vn in vn_list:
                kwargs = {}
                kwargs['tenant_name'] = tenant_name
                kwargs['mx_list']     = pr_mx_name_list
                kwargs['vn_name']     = vn
                kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.delete_extend_to_pr(thread_count=1,args_list=args_list,kwargs_list=kwargs_list)

    def update_extend_to_physical_routers(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list         = generate_tenant_name_list(tenant_conf,tenant_name)
        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])
 
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
                   kwargs_list.append(kwargs)

        args_list = [i for i in xrange(len(kwargs_list))]
        self.add_extend_to_pr(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)
 
    @parallel_threads(debug_enabled=False)
    def create_vn(self,args,kwargs):
        vn_name     = kwargs['vn_name']
        cidr        = kwargs['cidr']
        ipam_name   = kwargs['ipam_name']
        tenant_name = kwargs['tenant_name']
        subnets = [{'cidr':cidr,'name':vn_name+"_subnet"}]
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping create VN"%tenant_name
           return
        try:
           self.connections.vnc_lib.virtual_network_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(vn_name)])
           print "VN:%s already available..skipping create.."%vn_name
           return
        except NoIdError:
            pass
        try:
           ipam_id = self.connections.vnc_lib.network_ipam_read(fq_name=[u'default-domain',u'%s'%tenant_name,unicode(ipam_name)]).uuid
        except:
           ipam_id = None  
        if kwargs.has_key('disable_gateway') :
           disable_gateway = kwargs['disable_gateway']
        else:
           disable_gateway = False
        if kwargs.has_key('external_flag') and kwargs['external_flag'] :
           external = True
        else:
           external = False
        if kwargs.has_key('shared_flag') and kwargs['shared_flag']:
           shared = True
        else:
           shared = False
        
        if kwargs.has_key('rt_number') and kwargs['rt_number']:
           rt_number = kwargs['rt_number']
        else:
           rt_number = None
        project_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain', u'%s'%tenant_name])      
        project_obj.project_fq_name=[u'default-domain', u'%s'%tenant_name]
        self.create(vn_name,subnets,ipam_id,disable_gateway=disable_gateway,external=external,shared=shared,rt_number=rt_number,project_obj=project_obj,forwarding_mode='l2_l3')

    def create_vns(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            ipam_name    = generate_ipam_name(global_conf,tenant_conf,tenant_index)
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                vn_index       = 0
                vn_info        = tenant_conf['tenant,vn_group_list'][vn_group_index]
                vn_count       = vn_info['count']
                vn_name_pattern = vn_info['vn,name,pattern']
                vn_type        = get_vn_type(vn_name_pattern) 
                cidr_list      = [generate_cidr(tenant_name,vn_type) for x in xrange(vn_count)]
                external_flag  = vn_info['external_flag']
                for vn_indx in xrange(vn_count):
                    vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_index)
                    cidr    = cidr_list[vn_indx]
                    vn_index += 1
                    rt_number            = vn_info.get('route_target,rt_number') 
                    if rt_number:
                       rt_number = generate_rt_number()
                    else:
                       rt_number = None
                    kwarg = {}
                    kwarg['cidr']            = cidr 
                    kwarg['ipam_name']       = ipam_name
                    kwarg['tenant_name']     = tenant_name
                    kwarg['vn_name']         = vn_name
                    kwarg['rt_number']       = rt_number
                    kwarg['external_flag']   = external_flag
                    kwarg['disable_gateway'] = False
                    kwargs_list.append(kwarg)

        args_list = [i for i in xrange(len(kwargs_list))]
        self.create_vn(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    def add_policy(self,policy_obj):
        self.fixture.bind_policies([policy_obj.policy_fq_name], self.vn_id)

    def delete_policy(self,policy_obj):
        self.fixture.unbind_policies(self.vn_id,[policy_obj.policy_fq_name])

    def delete(self, uuid, subnets=[]):
        if not subnets:
            subnets = self.get_subnets(uuid)
        vn_fixture = self.get_fixture(uuid=uuid, subnets=subnets)
        vn_fixture.delete(verify=True)

    def delete_vn_by_name_process(self,tenant_name,vn_name) :
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping delete VN"%tenant_name
           return
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
           self.delete(vn_id)


    def delete_vn_by_name(self,args,kwargs):
        tenant_name,vn_name = args
        p = mp.Process(target=self.delete_vn_by_name_process,args=(tenant_name,vn_name))
        p.start()
        p.join()

    @parallel_threads(debug_enabled=False)
    def delete_vn(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        vn_id       = kwargs['vn_id']
        vn_fq_name  = kwargs['vn_fq_name']
        try:
           self.get_connection_handle(tenant_name)
        except:
           print "DEBUG: Tenant %s missing..skipping delete VN"%tenant_name
           return
        self.delete(vn_id)

    def delete_vns(self,thread_count,global_conf,tenant_conf,tenant_name='all'):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)

        vn_list = []
        for tenant_name in tenant_name_list:
           ret = list_vn(tenant_name=tenant_name)
           if ret:
             vn_list.extend(ret)
        kwargs_list = []
        for vn in vn_list:
            tenant_name,vn_id,vn_fq_name = vn
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs['vn_id']       = vn_id
            kwargs['vn_fq_name']  = vn_fq_name
            kwargs_list.append(kwargs) 
        args_list = [i for i in xrange(len(kwargs_list)) ]
        if len(args_list) == 0 :
           return
        self.delete_vn(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

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

class VM(Base):
    def create(self, name, vn_ids, image='ubuntu'):
        self.fixture = VMFixture(connections=self.connections, vn_ids=vn_ids, vm_name=name, image_name=image)
        self.fixture.flavor = "m1.small"
        
        self.fixture.setUp()
        #self.fixture.wait_till_vm_is_up()
        return self.fixture.get_uuid()

    @parallel_threads(debug_enabled=False)
    def create_vm(self,args,kwargs):
        vm_name      = kwargs['vm,name']
        data_vn_name = kwargs['data_vn_name']
        mgmt_vn_name = kwargs['mgmt_vn_name']
        tenant_name  = kwargs['tenant_name']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping create VM"%tenant_name
           return
        quantum_h = self.connections.get_network_h()
        self.nova_h=self.connections.nova_h
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

        uid = self.create(vm_name,[data_vn_obj['network']['id'],mgmt_vn_obj['network']['id']])
        return 

    def create_vms(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list    = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []   
        mgmt_vn_name = global_conf['mgmt,vn_name']
        for tenant_name in tenant_name_list :
            tenant_index = get_tenant_index(tenant_conf,tenant_name)
            vm_index = 0  
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
              vn_index = 0 
              vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
              vn_name_pattern      = vn_info['vn,name,pattern']
              for vn_indx  in xrange(vn_info['count']):
                 vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_indx)
                 vn_index += 1
                 if vn_info.has_key('vm,count') :
                   vm_count        = vn_info['vm,count']
                   vm_name_pattern = vn_info['vm,name_pattern']
                   for vm_indx in xrange(vm_count):
                       vm_name              = re.sub('QQQ',str(vm_index),vm_name_pattern)
                       conf                 = {}
                       conf['tenant_name']  = tenant_name
                       conf['vm,name']      = vm_name
                       conf['data_vn_name'] = vn_name
                       conf['mgmt_vn_name'] = mgmt_vn_name
                       conf['image'] = "ubuntu"
                       vm_index += 1
                       kwargs_list.append(conf)
        count = len(kwargs_list)
        args_list = [ i for i in xrange(count)]
        self.create_vm(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    def get_vm_creds(self):
        return (self.fixture.get_vm_username(),
                self.fixture.get_vm_password())

    def delete(self, uuid, vn_ids=[],verify=False):
        vm_fixture = self.get_fixture(uuid=uuid, vn_ids=vn_ids)
        vm_fixture.delete(verify=verify)

    @parallel_threads(debug_enabled=False)
    def delete_vm(self,args,kwargs):
        tenant_name = kwargs['tenant_name']
        vm_id       = kwargs['vm_id']
        try:
          self.get_connection_handle(tenant_name)
        except Exception as e:
          self.logger.warn("Got exception as %s"%e + "..skipping delete VM:%s"%vm_id)
          return
        self.logger.info("DEBUG: deleting VM : %s"%vm_id)
        
        self.delete(vm_id,[],True)

    def delete_vms(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        vms_list = []
        for tenant_name in tenant_name_list:
          ret = list_vms(tenant_name=tenant_name)
          if ret:
           vms_list.extend(ret)
         
        kwargs_list = []
        for vm in vms_list:
          kwargs = {}
          kwargs['tenant_name']     = vm['tenant_name']
          kwargs['vm_id']           = vm['id']
          kwargs_list.append(kwargs)

        args_list = [ i for i in xrange(len(kwargs_list)) ]
        if len(args_list) == 0 :
           return
        self.delete_vm(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

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

    @parallel_threads(debug_enabled=False)
    def create_fip_pool(self,args,kwargs):
        vn_id   = kwargs['vn_id']
        fip_pool_name = kwargs['fip,pool,name']
        tenant_name   = kwargs['tenant,name']
        try:
          self.get_connection_handle(tenant_name)
        except ProjectNotFound:
          print "Project: %s missing..skipping FIP creation"%tenant_name
          return
        self.create(vn_id,fip_pool_name)
      
    def create_fip_pools(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        public_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_vn_group_index = vn_group_indx
            break
        if not public_vn_group_index:
           return
        vn_info_dict = {}
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_indx = get_tenant_index(tenant_conf,tenant_name)
            vn_info               = tenant_conf['tenant,vn_group_list'][public_vn_group_index]
            fip_gw_vn_name_pattern   = vn_info['vn,name,pattern']
            fip_gw_vn_count       = vn_info['count']
            fip_gw_vn_names       = [generate_vn_name(global_conf,tenant_conf,tenant_indx,fip_gw_vn_name_pattern,vn_indx) for vn_indx in xrange(fip_gw_vn_count)]
            fip_pool_name_pattern = tenant_conf['fip,name']
            fip_pool_name_list    = [generate_fip_pool_name(global_conf,tenant_conf,tenant_indx,pool_indx) for pool_indx in xrange(fip_gw_vn_count)]
            ret = get_vn_ids(tenant_name=tenant_name)
            if ret:
               vn_info_dict.update(ret)
            for indx,pool_name in enumerate(fip_pool_name_list):
                kwarg = {}
                kwarg['tenant,name']   = tenant_name
                kwarg['fip,pool,name'] = fip_pool_name_list[indx]
                kwarg['vn_id']         = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,fip_gw_vn_names[indx])]
            kwargs_list.append(kwarg)
        args_list = [1 for i in xrange(len(kwargs_list))] 
        self.create_fip_pool(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)
 
    def delete(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        fip_fixture.delete(verify=True)

    @parallel_threads(debug_enabled=False)
    def delete_fip_pool(self,args,kwargs):
        tenant_name   = kwargs['tenant,name']
        try:
          self.get_connection_handle()
        except ProjectNotFound:
          print "Project:%s missing..skipping FIP pool deletion"%tenant_name
          return
        fip_pools = self.connections.vnc_lib.floating_ip_pools_list()['floating-ip-pools']
        try:
           project_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
        except:
           return
        for fip_pool in fip_pools: 
            fip_domain,fip_tenant_name,fip_vn_name,fip_pool_name = fip_pool[u'fq_name']  
            if fip_tenant_name != unicode(tenant_name):
               continue
            try:
              pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool[u'fq_name'])
            except:
              continue
            fips = pool_obj.get_floating_ips()
            if fips: 
               for fip in fips:
                   self.disassociate_fip(pool_obj.uuid,fip['uuid'])
            project_obj.del_floating_ip_pool(pool_obj)
            self.connections.vnc_lib.project_update(project_obj)
            try:
              self.delete(pool_obj.uuid)
            except:
              pass

    def delete_fip_pools(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        for tenant_name in tenant_name_list:
            tenant_indx = get_tenant_index(tenant_conf,tenant_name)
            kwarg       = {}
            kwarg['tenant,name']   = tenant_name
            kwargs_list.append(kwarg)
        args_list = [1 for i in xrange(len(kwargs_list))]
        self.delete_fip_pool(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def associate_fip(self,args,kwargs):
        tenant_name    = kwargs['tenant_name']
        fip_pool_name  = kwargs['fip_pool_name']
        vm_id          = kwargs['vm_id']
        vn_id          = kwargs['private_vn_id']
        fip_gw_vn_name = kwargs['fip_gw_vn_name']
        fip_gw_vn_id   = kwargs['fip_gw_vn_id']
        username       = "ubuntu"
        password       = "ubuntu"
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping associate FIPs"%tenant_name
           return

        # delete default-fip-pool
        try:
           pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=[u'default-domain', u'%s'%tenant_name, u'%s'%fip_gw_vn_name, u'floating-ip-pool'])
           print "FIP pool:%s found..deleting.."%fip_pool_name
           project_obj = self.connections.vnc_lib.project_read(fq_name=[u'default-domain',u'%s'%tenant_name])
           project_obj.del_floating_ip_pool(pool_obj)
           self.connections.vnc_lib.project_update(project_obj)
           self.delete(pool_obj.uuid)
        except NoIdError:
           print "FIP pool:%s not found..skipping delete"%fip_pool_name
        # delete default-fip-pool

        fip_pool_obj = self.connections.vnc_lib.floating_ip_pool_read(fq_name=[u'default-domain', u'%s'%tenant_name, u'%s'%fip_gw_vn_name, u'%s'%fip_pool_name])
        fip_pool_id  = fip_pool_obj.uuid
        self.fixture = self.get_fixture(uuid=fip_pool_id)
        self.project_name = tenant_name
        return self.fixture.create_and_assoc_fip(fip_pool_vn_id=fip_gw_vn_id,vm_id=vm_id,vn_id=vn_id)

    def associate_fips(self,thread_count,global_conf,tenant_conf,tenant_name):
       
        tenant_name_list          = generate_tenant_name_list(tenant_conf,tenant_name)
        vn_index_replace_str      = tenant_conf['vn,index,replace_str']
        public_fip_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_fip_vn_group_index = vn_group_indx
        if public_fip_vn_group_index == None :
           return
        vn_info_dict = {}
        for tenant_name in tenant_name_list:
           ret = get_vn_ids(tenant_name=tenant_name)
           if ret:
             vn_info_dict.update(ret)
        fip_gw_vn_count          = tenant_conf['fip,gw_vn_count']
        fip_gw_vn_name_pattern   = tenant_conf['fip,gw_vn_name']
        fip_pool_name_pattern    = tenant_conf['fip,name']
        kwargs_list = []
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
                vm_list = list_vms(tenant_name=tenant_name,vn_list=vn_names_list)
                if not vm_list:
                   continue
                for vm in vm_list:
                    tenant_name = vm['tenant_name']
                    vn_name     = vm['vn_name']
                    if vn_name == "":
                       private_vn_id = None
                    else:
                       private_vn_id = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,vn_name)]
                    kwarg = {}
                    kwarg['tenant_name']      = tenant_name
                    kwarg['private_vn_id']    = private_vn_id
                    kwarg['vm_id']            = vm['id']
                    kwarg['fip_pool_name']    = fip_pool_name
                    kwarg['fip_gw_vn_id']     = fip_gw_vn_id
                    kwarg['fip_gw_vn_name']   = fip_gw_vn_name
                    kwargs_list.append(kwarg)
        args_list = [ i for i in xrange(len(kwargs_list))]
        if len(args_list) == 0 :
           return
        self.associate_fip(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

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

class LogicalRouter(Base):

    def create(self, name, vn_ids=[], gw=None):
        quantum_h = self.connections.get_network_h()
        response = quantum_h.check_and_create_router(name)
        self.uuid = response['id']
        self.fqname = response['contrail:fq_name']
        if gw:
            self.set_gw(self.uuid, gw)
        for vn_id in vn_ids:
            self.attach_vn(self.uuid, vn_id)
        return self.uuid
   
    @parallel_threads(debug_enabled=False)
    def create_logical_router(self,args,kwargs):
        tenant_name   = kwargs['tenant_name']
        router_name   = kwargs['router_name']
        gw            = kwargs['gw_nw']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping creating LR"%tenant_name
        self.create(router_name,gw=gw)

    def create_logical_routers(self,thread_count,global_conf,tenant_conf,tenant_name):
        gw_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
            break
        if not gw_vn_group_index:
           return 
        tenant_name_list     = generate_tenant_name_list(tenant_conf,tenant_name)
        router_count         = tenant_conf['routers,count']
        vn_index_replace_str = tenant_conf['vn,index,replace_str']

        kwargs_list = []
        vn_info_dict = {}
        for tenant_name in tenant_name_list:
           tenant_indx = get_tenant_index(tenant_conf,tenant_name)
           ret = get_vn_ids(tenant_name=tenant_name)
           if ret:
             vn_info_dict.update(ret)
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
        args_list = [i for i in xrange(len(kwargs_list))]
        self.create_logical_router(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def delete_logical_router(self,args,kwargs):
        tenant_name   = kwargs['tenant_name']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping LR delete"
           return
        lrs = self.connections.vnc_lib.logical_routers_list()['logical-routers']
        for lr in lrs:
            lr_domain,lr_tenant_name,lr_name = lr[u'fq_name']
            if lr_tenant_name != unicode(tenant_name):
               continue
            router_obj = self.connections.vnc_lib.logical_router_read(fq_name=lr[u'fq_name'])
            uuid = router_obj.uuid
            self.delete(uuid)

    def delete_logical_routers(self,thread_count,global_conf,tenant_conf,tenant_name):
        tenant_name_list  = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list = []
        for tenant_name in tenant_name_list:
            kwargs = {}
            kwargs['tenant_name'] = tenant_name
            kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.delete_logical_router(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def attach_vns_to_logical_router(self,args,kwargs):
        tenant_name   = kwargs['tenant_name']
        router_id     = kwargs['router_id']
        net_ids       = kwargs['private_vns']
        try:
           self.get_connection_handle(tenant_name)
        except ProjectNotFound:
           print "DEBUG: Tenant %s missing..skipping associate FIPs"%tenant_name
        quantum_h = self.connections.get_network_h()
        for net_id in net_ids:
            subnet_id = quantum_h.get_vn_obj_from_id(net_id)['network']['subnets'][0]
            try:
              quantum_h.add_router_interface(router_id=router_id, subnet_id=subnet_id)
            except:
              pass # interface may be already added

    def attach_vns_to_logical_routers(self,thread_count,global_conf,tenant_conf,tenant_name):
        gw_vn_group_index           = None
        snat_private_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
          if re.search('Private_SNAT',vn_group['vn,name,pattern']):
            snat_private_vn_group_index = vn_group_indx
        if not gw_vn_group_index:
           return 
        tenant_name_list  = generate_tenant_name_list(tenant_conf,tenant_name)
        kwargs_list       = []
        vn_info_dict      = {}
        router_info_dict  = {}
        for tenant_name in tenant_name_list:
            tenant_indx = get_tenant_index(tenant_conf,tenant_name)
            ret = get_vn_ids(tenant_name=tenant_name)
            if ret:
              vn_info_dict.update(ret)
            router_count     = tenant_conf['routers,count']
            router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
            for router_name in router_name_list:
                ret = get_router_id(tenant_name=tenant_name,router_name=router_name)
                if ret:
                   router_info_dict.update({router_name:ret})
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

        args_list = [i for i in xrange(len(kwargs_list))]
        self.attach_vns_to_logical_router(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

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
    @single_thread(debug_enabled=True)
    def retrieve_existing_services(self,*args,**kwargs):
        return_dict    = kwargs.get('return_dict',None)
        try:
           self.get_connection_handle()
        except ProjectNotFound:
           print "DEBUG: Tenant admin missing..skipping LLS delete"
        current_config=self.connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])
        current_linklocal=current_config.get_linklocal_services()
        current_entries = current_linklocal.linklocal_service_entry
        service_names = []
        for entry in current_entries:
            service_names.append(entry.linklocal_service_name)
        if return_dict is not None:
           return_dict['value'] = service_names
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
        current_entries = retrieve_existing_services() 
        current_entries.append(linklocal_obj)
        linklocal_services_obj=LinklocalServicesTypes(current_entries)
        conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
        result=self.connections.vnc_lib.global_vrouter_config_update(conf_obj)
        print 'Created LLS.UUID is %s'%(result)

    def delete(self,service_name):

        current_config=self.connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])
        current_linklocal=current_config.get_linklocal_services()
        current_entries = current_linklocal.linklocal_service_entry
        for i,entry in enumerate(current_entries):
            if entry.linklocal_service_name == service_name :
               current_entries.pop(i)
               break
        linklocal_services_obj=LinklocalServicesTypes(current_entries)
        conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
        result=self.connections.vnc_lib.global_vrouter_config_update(conf_obj)
        print 'Deleted LLS.UUID is %s'%(result)

    @parallel_threads(debug_enabled=False)
    def create_link_local_service(self,args,kwargs):
        service_name = kwargs['lls_name']
        lls_ip       = kwargs['lls_ip']
        lls_port     = kwargs['lls_port']
        lls_fab_ip   = kwargs['lls_fab_ip']
        lls_fab_port = kwargs['lls_fab_port']
        try:
           self.get_connection_handle()
        except ProjectNotFound:
           print "DEBUG: Tenant admin missing..skipping LLS create"
        self.create(service_name,lls_ip,lls_port,None,lls_fab_ip,lls_fab_port)

    def create_link_local_services(self,thread_count,global_conf,tenant_conf):

        count      = global_conf.get('lls,count',None)
        if count is None:
           return
        start_ip   = global_conf['lls,start_ip']
        start_port = global_conf['lls,start_port']
        fab_ip     = global_conf['lls,fab_ip']
        fab_port   = global_conf['lls,fab_port']
        kwargs_list  = []
        service_ip   = ipaddr.IPAddress(start_ip)
        service_port = start_port 
        service_name_pattern = global_conf['lls,name']
        for i in xrange(count):
            kwargs = {}
            service_name = re.sub('###',str(i),service_name_pattern)
            kwargs['lls_name']     = service_name
            kwargs['lls_ip']       = str(service_ip)
            kwargs['lls_port']     = service_port
            kwargs['lls_fab_ip']   = fab_ip
            kwargs['lls_fab_port'] = fab_port
            service_ip   += 1
            service_port += 1
            fab_port     += 1 
            kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.create_link_local_service(thread_count=thread_count,args_list=args_list,kwargs_list=kwargs_list)

    @parallel_threads(debug_enabled=False)
    def delete_link_local_service(self,args,kwargs):
        service_name = kwargs['lls_name']
        try:
           self.get_connection_handle()
        except ProjectNotFound:
           print "DEBUG: Tenant admin missing..skipping LLS delete"
        self.delete(service_name)

    def delete_link_local_services(self,thread_count,global_conf,tenant_conf):

        count      = global_conf.get('lls,count',None)
        if count is None:
           return
        kwargs_list  = []
        service_name_pattern = global_conf['lls,name']
        for i in xrange(count):
            kwargs = {}
            service_name = re.sub('###',str(i),service_name_pattern)
            kwargs['lls_name']     = service_name
            kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.delete_link_local_service(thread_count=1,args_list=args_list,kwargs_list=kwargs_list)

class Lbaas(Base):

     @parallel_threads(debug_enabled=False)
     def create_lb_pool(self,args,kwargs):
         tenant_name = kwargs['tenant_name']
         pool_name = kwargs['pool_name']
         lb_method = kwargs['lb_method']
         protocol  = kwargs['protocol']
         servers_subnet_id = kwargs['servers_subnet_id']
         try:
           self.get_connection_handle(tenant_name)
         except:
           print "DEBUG: Tenant %s missing..skipping Lbaas pool create"%tenant_name
           return

         quantum_h = self.connections.get_network_h()
         quantum_h.create_lb_pool(pool_name,lb_method,protocol,servers_subnet_id)

     def create_lb_pools(self,thread_count,global_conf,tenant_conf):
        tenant_count             = tenant_conf['tenant,count']
        tenant_name_pattern      = tenant_conf['tenant,name,pattern']
        tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
        tenant_name_list         = [re.sub(tenant_index_replace_str,str(i),tenant_name_pattern) for i in xrange(tenant_count)]
        lbaas_pool_name_pattern  = tenant_conf['lbaas,pool_name']
        pool_names               = [re.sub(tenant_index_replace_str,str(i),lbaas_pool_name_pattern) for i in xrange(tenant_count)]
        pool_names_list          = [re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),pool_name) for pool_name in pool_names]

        print "Pool_name:",pool_names_list

        servers_subnet_id = ['6619e973-8a9b-4a25-99b5-5d8d636e33f2','b0fa73f4-de3b-4403-9198-86d837f1371a']
        kwargs_list = []
        for i,tenant_name in enumerate(tenant_name_list):
             kwargs = {}
             kwargs['tenant_name'] = tenant_name
             kwargs['pool_name']   = pool_names_list[i]
             kwargs['lb_method']   = tenant_conf['lbaas,method']
             kwargs['protocol']    = tenant_conf['lbaas,pool,protocol']
             #kwargs['servers_subnet_id'] = tenant_conf['lbaas,pool,subnet']
             kwargs['servers_subnet_id'] = servers_subnet_id[i]
             kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.create_lb_pool(thread_count=1,args_list=args_list,kwargs_list=kwargs_list)

     @parallel_threads(debug_enabled=False)
     def create_lb_member(self,args,kwargs):
         tenant_name    = kwargs['tenant_name']
         pool_id        = kwargs['pool_id']
         server_ip      = kwargs['server_ip']
         protocol_port  = kwargs['protocol_port']
         try:
           self.get_connection_handle(tenant_name)
         except:
           print "DEBUG: Tenant %s missing..skipping Lbaas pool create"%tenant_name
           return

         quantum_h = self.connections.get_network_h()
         quantum_h.create_lb_member(server_ip,protocol_port,pool_id)

     def create_lb_members(self,thread_count,global_conf,tenant_conf):
        tenant_count             = tenant_conf['tenant,count']
        tenant_name_pattern      = tenant_conf['tenant,name,pattern']
        tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
        tenant_name_list         = [re.sub(tenant_index_replace_str,str(i),tenant_name_pattern) for i in xrange(tenant_count)]
        lbaas_pool_name_pattern  = tenant_conf['lbaas,pool_name']
        pool_names               = [re.sub(tenant_index_replace_str,str(i),lbaas_pool_name_pattern) for i in xrange(tenant_count)] 
        pool_names_list          = [re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),pool_name) for pool_name in pool_names]

        #VN group-2
        servers_subnet_id = ['6619e973-8a9b-4a25-99b5-5d8d636e33f2','b0fa73f4-de3b-4403-9198-86d837f1371a']

        server_pool_vn_names = ['tenant0.test_id1.GW','tenant1.test_id1.GW']
        server_pool_id       = ['906ce897-3285-4fe7-98fd-8b7f932b968d','6b147b56-f374-41f1-81f7-c4e6051e7640']
        vms_list = []
        kwargs_list = []
        for indx,tenant_name in enumerate(tenant_name_list):
          vms_list = list_vms(tenant_name=tenant_name,vn_list=[server_pool_vn_names[indx]])
          if not vms_list:
            print "INFO: no servers in this VN pool..skipping.."
            continue
          for vm in vms_list:
             vn_name = vm['vn_name']
             vm_ip = vm['ip'][vn_name][0]['addr']
             kwargs = {}
             kwargs['tenant_name']   = tenant_name
             kwargs['pool_id']       = server_pool_id[indx]
             kwargs['server_ip']     = vm_ip
             kwargs['protocol_port'] = tenant_conf['lbaas,pool,members_port']
             kwargs_list.append(kwargs)
        args_list = [i for i in xrange(len(kwargs_list))]
        self.create_lb_member(thread_count=1,args_list=args_list,kwargs_list=kwargs_list)

     #def create_lb_vips(self,thread_count,global_conf,tenant_conf):
