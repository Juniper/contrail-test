# Fix
# 1.   ssladapter crashes with multiprocessing.
#      https://github.com/sigmavirus24/requests-toolbelt/issues/34 
# 2.   tcutils/util.py ( tcutils is at same level as diagnostics )  needs to be updated as follows:
#      inside 'class customdict'
#      def __setitem__(self, key, value):
#        if self.has_key('validate_set'): #self.validate_set:
#           self.validate_set(key, value)

import sys
import traceback
import uuid
import random
import string
import copy
import inspect
import ipaddr
import requests
import json
import re
import threading
from common import log_orig as logging
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import pdb
import tempfile
import os
from nova_test import NovaHelper
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
from netaddr import IPNetwork
from lbaasv2_fixture import *

import time                                                

def handleRefsExistError():
    sys.stdout.flush()
    while True:
      time.sleep(1)

def timeit(method):
   
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r %2.2f sec' %  (method.__name__, te-ts)
        return result

    return timed

cidr_lock = threading.Lock()
connection_lock = threading.Lock()

from tcutils import Process

#### PROCESS #####

from multiprocessing import TimeoutError
from multiprocessing.dummy import Pool 
from copy_reg import pickle
import time
import threading
import marshal
import thread
import pdb
import types
import sys
from common import log_orig as logging
LOG = logging.getLogger(__name__)

def wrapper(func):
    ''' Decorator to create n tasks 
    Optional:
    :param max_process: No of concurrent processes to create to handle the tcount tasks (default 30)
    :param tcount : No of tasks to create if less than 1 run the task in the current process context (default 1)
    :param timeout : Max wait time in secs for the task to complete execution (default 600s)
    :param args_list : list of args for each task (default: same args is passed to each task)
    :param kwargs_list : list of kwargs for each task (default: same kwargs is passed to each task)
    '''
    def inner(*args, **kwargs):
       self = args[0]
       debug_enabled = kwargs.pop('debug_enabled',False)
       tcount = kwargs.get('tcount',1)
       if debug_enabled or tcount == 1:
          if debug_enabled:
             pdb.set_trace()
          conn_obj_list = kwargs.pop('conn_obj_list')
          kwargs_list   = kwargs.pop('kwargs_list',[])
          args_list   = kwargs.pop('args_list',[])
          if len(kwargs_list) == 0:
              kwargs_list=[{'connection_obj' : conn_obj_list[0]}]
          if len(args_list) == 0:
             args_list = len(kwargs_list) * [self]
          for i,kwargs in enumerate(kwargs_list):
             kwargs['connection_obj']  = conn_obj_list[0]
             ret_value = func(args_list[i],**kwargs)
          return ret_value
       else:
          return multi_process(func,*args,**kwargs)

    return inner

def _pickle_exit(obj):
    return _unpickle_exit, ( )
def _unpickle_exit():
    return exit
pickle(type(exit), _pickle_exit, _unpickle_exit)

def _pickle_ellipsis(obj):
    return _unpickle_ellipsis, (obj.__repr__(), )
def _unpickle_ellipsis(obj):
    return eval(obj)
pickle(types.EllipsisType, _pickle_ellipsis, _unpickle_ellipsis)
pickle(types.NotImplementedType, _pickle_ellipsis, _unpickle_ellipsis)


def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)
def _unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)
pickle(types.MethodType, _pickle_method, _unpickle_method)

lock = dict()
def get_lock(key):
    global lock
    if key not in lock.keys():
        lock[key] = threading.Lock()
    return lock[key]
def _pickle_lock(lock):
    return _unpickle_lock, (lock.__hash__(),)
def _unpickle_lock(key):
    return get_lock(key)
pickle(thread.LockType, _pickle_lock, _unpickle_lock)

def _pickle_file(fobj):
    return _unpickle_file, (fobj.name, fobj.mode)
def _unpickle_file(name, mode):
    if '/' in name:
        return open(name, mode)
    if 'stdout' in name:
        return sys.stdout
    elif 'stderr' in name:
        return sys.stderr
    elif 'stdin' in name:
        return sys.stdin
pickle(types.FileType, _pickle_file, _unpickle_file)

def _pickle_func(func):
    fn_glob = dict()
    modules = dict()
    supported_types = [v for k, v in types.__dict__.iteritems()
                       if k.endswith('Type')]
    for k,v in func.func_globals.iteritems():
         if type(v) in supported_types:
             fn_glob[k] = v
         if type(v) == types.ModuleType:
             modules.update({k: v.__name__})
             del fn_glob[k]
    return _unpickle_func, (marshal.dumps(func.func_code), fn_glob, modules,
                            func.func_name, func.func_defaults,
                            func.func_closure, func.func_dict)

def _unpickle_func(code_string, fn_glob, modules, func_name,
                   func_defaults, func_closure, func_dict):
    code = marshal.loads(code_string)
    for k,v in modules.iteritems():
         fn_glob.update({k: __import__(v)})
    fn = types.FunctionType(code, fn_glob, func_name,
                      func_defaults, func_closure)
    fn.__dict__.update(func_dict)
    return fn
pickle(types.FunctionType, _pickle_func, _unpickle_func)


def multi_process(target,*args, **kwargs):
    count = kwargs.pop('tcount', 0)
    timeout = kwargs.pop('timeout', 600)
    max_process = kwargs.pop('max_process', 30)
    kwargs_list = kwargs.pop('kwargs_list', None)
    args_list = kwargs.pop('args_list', None)

    if kwargs_list:
       n_instances = len(kwargs_list)
    else:
       n_instances = 1

    if not kwargs_list:
        kwargs_list = [kwargs for i in range(n_instances)]
    if not args_list:
        args_list = [args for i in range(n_instances)]

    res = []
    if len(kwargs_list) < count :
       count = len(kwargs_list)
    data = range(len(kwargs_list))
    chunks = [data[x:x+count] for x in xrange(0, len(data), count)]
    print "CHUNKS:",chunks
    for chunk in chunks:
        if len(chunk) == 1:
          kwargs_index = chunk[0]
          kwargs_list[kwargs_index]['connection_obj'] = kwargs.get('conn_obj_list')[0]
          target(args_list[kwargs_index][0], **kwargs_list[kwargs_index])
          continue
        pool = Pool(len(chunk))
        for i,ii in enumerate(chunk):
            kwargs_list[ii]['connection_obj'] = kwargs.get('conn_obj_list')[i]
        results = [pool.apply_async(target, args_list[j], kwargs_list[j]) for j in chunk]
        pool.close() # Close the pool so no more creation of new tasks

        res = list()
        for result in results:
            try:
                res.append(result.get(timeout=timeout))
            except TimeoutError as e:
                LOG.logger.error('Task overrun %d secs and timedout'%timeout)
                print 'Task overrun %d secs and timedout'%timeout
            except Exception as e:
                print 'Exception in a task:', type(e).__name__, str(e)
        pool.terminate() # Terminate the pool to delete the task overrun processes
        pool.join()
        if len(res) != len(chunk):
            raise Exception('Exception observed in some of the processes')
        elif int(count) == 0:
            return res[0]
    return res
#### PROCESS #####

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

def retrieve_mx_name(global_conf):

    mxs = global_conf['pr_mx']
    return mxs[0]['name']   

def retrieve_mx_physical_interface(global_conf):

    mxs = global_conf['pr_mx']
    return mxs[0]['pr_interface']['name']

def retrieve_mx_physical_interface_vlan(global_conf):

    mxs = global_conf['pr_mx']
    return mxs[0]['pr_interface']['vlan']

def parse_vn_out_stats(values):

   """
[{u'bytes': 142434912505, u'other_vn': u'default-domain:default-project:ip-fabric', u'tpkts': 14889382}, {u'bytes': 296549600407, u'other_vn': u'default-domain:symantec.Tenant.20:tenant20.test_id1.Public_FIP_VN0', u'tpkts': 209784131}]
   """

   print "VN_NAME,out_bytes,out_tpkts"
   for value in values:
       for vn in value:
           if vn['other_vn'] == 'default-domain:default-project:ip-fabric' or re.search('__UNKNOWN__|unresolved',vn['other_vn']):
              continue
           print vn['other_vn'],vn['bytes'],vn['tpkts']

def parse_cpu_info(values):

   """{u'sys_mem_info': {u'used': 3092748, u'cached': 252808, u'free': 260765812, u'node_type': None, u'total': 263858560, u'buffers': 205880}, u'meminfo': {u'virt': 863224, u'peakvirt': 928760, u'res': 89460}, u'cpu_share': 0.122083, u'num_cpu': 40, u'cpuload': {u'fifteen_min_avg': 0.004, u'five_min_avg': 0.004, u'one_min_avg': 0.00225}}"""

   print "fifteen_min_avg,five_min_avg,one_min_avg"
   #print values
   for value in values:
       cpuload = value['cpuload']
       print cpuload["fifteen_min_avg"],cpuload['five_min_avg'],cpuload['one_min_avg']

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

def retrieve_vn_conf(vn_group_info,vn_name):
    ret = re.search('tenant(\d+)\.test_id(\d+)\..*(\d+)',vn_name)
    vn_prop = {}
    if ret:
       tenant_id = ret.group(1)
       test_id   = ret.group(2)
       vn_id = ret.group(3)
    else:
       return vn_prop


    vn1   = re.sub(tenant_id,'XXX',vn_name,count=1)
    vn1   = re.sub(test_id,'ZZZ',vn1,count=1)
    vn1   = re.sub(vn_id,'YYY',vn1,count=1)
    for vn_group in vn_group_info:
        if vn_group['vn,name,pattern'] == vn1:
           vn_prop = vn_group
           break
    return vn_prop

class ProjectNotFound(Exception):
      def __init__(self, value):
          self.value = value
      def __str__(self):
          return repr(self.value)

def generate_vdns_conf(global_conf,tenant_conf,vdns):
    vdns_domain_name = vdns.get_domain()
    tenant_domain_name = vdns.get_tenant_domain_name()
    vdns_name = re.sub("\.","-",vdns_domain_name)
    if vdns.get_forwarder():
       vdns_next_vdns = tenant_domain_name + ":" + re.sub("\.","-",vdns.get_forwarder())
    else:
       vdns_next_vdns = None
    conf = {}
    conf['vdns_name']               = vdns_name
    conf['tenant_domain_name']      = tenant_domain_name
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

def generate_ipam_name(global_conf,tenant_conf,tenant_index,ipam_index):
    test_id                  = global_conf['test_id']
    test_id_replace_str      = global_conf['test_id,replace_str']
    ipam_name_pattern        = tenant_conf['ipam,name,pattern']
    tenant_index_replace_str = tenant_conf['tenant,index,replace_str']
    ipam_index_replace_str   = tenant_conf['ipam,index,replace_str']
    ipam_name = re.sub(tenant_index_replace_str,str(tenant_index),ipam_name_pattern)
    ipam_name = re.sub(test_id_replace_str,str(test_id),ipam_name)
    ipam_name = re.sub(ipam_index_replace_str,str(ipam_index),ipam_name)
    return ipam_name

def get_tenant_index(tenant_conf,tenant_fq_name):
    tenant_name_prefix  = tenant_conf['tenant,name_prefix'] 
    print "tenant_fq_name:",tenant_fq_name,tenant_name_prefix
    return int(re.search(tenant_name_prefix+'(\d+)',tenant_fq_name[1]).group(1))

def get_vn_type(vn_name):
    vn_group_list = ['Private_SNAT_VN','Private_VN','Private_LB_VN','Private_LB_VIP_VN','Private_LB_Pool_VN',
                     'SNAT_GW_VN','Public_FIP_VN','Private_SC_MGMT_VN','Private_SC_Left_VN','Private_SC_Right_VN','Private_VSRX_BGP_VN','Private_VSRX_MX_VN','Private_SC_Auto_Left_VN','Private_SC_Auto_Right_VN','Private_MIRROR_VN']
    
    for vn in vn_group_list:
        if re.search(vn,vn_name):
           return vn 

def generate_rt_number(already_allocated_rt):
    while True:
       rt = random.randint(1000000,3000000)
       if rt not in already_allocated_rt:
         break
    return rt

def generate_v4_cidr(tenant_fq_name,vn_type,already_allocated_cidr):
    ip_group = {}
    ip_group['Private_SNAT_VN']    = [i for i in xrange(11,12)]
    ip_group['Private_VN']         = [i for i in xrange(12,13)]
    ip_group['Private_LB_VIP_VN']  = [i for i in xrange(13,14)]
    ip_group['Private_LB_Pool_VN'] = [i for i in xrange(14,15)]
    ip_group['SNAT_GW_VN']         = [i for i in xrange(15,16)]
    ip_group['Public_FIP_VN']      = [i for i in xrange(16,17)]
    ip_group['Private_SC_MGMT_VN'] = [i for i in xrange(17,18)]
    ip_group['Private_SC_Left_VN'] = [i for i in xrange(18,19)]
    ip_group['Private_SC_Right_VN'] = [i for i in xrange(19,20)]
    ip_group['Private_SC_Auto_Left_VN']  = [i for i in xrange(20,21)]
    ip_group['Private_SC_Auto_Right_VN']  = [i for i in xrange(21,22)]
    ip_group['Private_VSRX_BGP_VN'] = [i for i in xrange(22,23)]
    ip_group['Private_VSRX_MX_VN']  = [i for i in xrange(23,24)]
    ip_group['Private_LB_VN']  = [i for i in xrange(24,25)]
    ip_group['Private_MIRROR_VN']  = [i for i in xrange(25,26)]
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
       if mask == 16:
          gw = "%i.%i.0.1" %(first_octet,second_octet)
       elif mask == 24:
          gw = "%i.%i.%i.1" %(first_octet,second_octet,third_octet)
       if cidr not in already_allocated_cidr:
          break
    return cidr,gw

def generate_v6_cidr(tenant_fq_name,vn_type,already_allocated_cidr):

    first_octet   = "fd66"
    random_octet_count   = 2
    prefix_length = "48"
    while True:
      ip = ":".join(["%x%x"%(random.randint(0,255),random.randint(0,255)) for i in xrange(random_octet_count)])
      cidr = first_octet + ":" + ip + "::0/" + prefix_length
      if cidr not in already_allocated_cidr:
          break
    return cidr

def connection(project_name='admin'):
    obj = ProjectConfig(None)
    obj.get_connection_handle(project_name)
    return obj
   
def create_connections(count,project_name='admin'):
    conn_obj_list = []
    for i in xrange(count):
        conn_obj_list.append(connection(project_name))
    return conn_obj_list
    
def debug_func():
    
    obj = ProjectConfig(None)
    obj.get_connection_handle("admin")
    import pdb;pdb.set_trace()
    proj_obj = obj.connections.vnc_lib.project_read(fq_name=['default-domain','admin'])
    #lb_obj=Loadbalancer('test-lb',parent_obj=proj_obj)
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
        logger = Logger.logger

        connection_lock.acquire()
        while True:
             time.sleep(random.random())
             try:
                #import pdb;pdb.set_trace()
                self.inputs = ContrailTestInit(self.ini_file,logger=logger)
                self.connections= ContrailConnections(inputs=self.inputs,logger=logger,project_name=project_name)
                break
             except Exception as ex:
                logger.warn("Exception happened in ContrailConnections..type : %s"%type(ex).__name__)
                if type(ex).__name__ == "RuntimeError" :
                   logger.error("RuntimeError in ContrailConnections")
                   break
        connection_lock.release()
 
class PortTuples(Base):

    @wrapper
    def list_port_tuples(self,*arg,**kwarg):
        tenant_list          = kwarg['tenant_list']
        connections     = kwarg['connection_obj'].connections
        port_tuples_filtered = []
        tenant_list  = map(lambda x:x['fq_name'],tenant_list)
        ports_list = connections.vnc_lib.port_tuples_list()['port-tuples']
        for port in ports_list:
            dom,t_name,si_name,tup_name=port['fq_name']
            if [dom,t_name] not in tenant_list:
               continue
            port_tuples_filtered.append(port['uuid'])
        return port_tuples_filtered

    @wrapper
    def delete_port_tuple(self,*arg,**kwarg):
        connections  = kwarg['connection_obj'].connections
        port_tuple_id     = kwarg['port_tuple_id']
        connections.vnc_lib.port_tuple_delete(id=port_tuple_id)

    def delete_port_tuples(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
	kwargs = {}
        kwargs['tenant_list'] = tenant_list	
        ports_list = self.list_port_tuples(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if not ports_list:
           return
        kwargs_list = []
        for port_id in ports_list:
            kwargs = {}
            kwargs['port_tuple_id'] = port_id
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_port_tuple(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
     
class Policy(Base):
    def create(self,inputs,policy_name,rules,connections,api=None):
        fixture = PolicyFixture(
                       policy_name=policy_name,
                       rules_list=rules,
                       inputs=inputs,
                       connections=connections,api=api)
        fixture.setUp()
        return fixture

    def delete(self, policy_fixture):
        policy_fixture.cleanUp()

    def get_fixture(self,connections,uuid=None):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            fixture = PolicyFixture(connections=connections, uuid=uuid)
        return fixture

    def construct_policy_rules(self,allow_rules_network,allow_rules_port,action_list):
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
           if action_list:
              rule['action_list'] = action_list

           rules.append(rule)
        return rules

    @wrapper
    def create_policy(self,*arg,**kwarg):
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        domain_name,tenant_name  = tenant_fq_name
        policy_name      = kwarg['policy_name']
        rules            = kwarg['rules']
        connection_obj   = kwarg['connection_obj']
        connections = connection_obj.connections
        policy_fq_name   = tenant_fq_name + [policy_name]
        try:   
           connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
           print "Policy: %s already available...skipping create.."%str(policy_fq_name)
           return
        except NoIdError :
           self.quantum_h = connections.quantum_h
           self.create(connections.inputs,policy_name,rules,connections)
           return
        return
        ## NEW_CODE
        #./vnc_api/gen/heat/resources/network_policy_heat.py
        #network_policy = NetworkPolicy(parent_obj=project_obj)
        #network_policy.set_display_name(policy_name)
        #obj1 = PolicyEntriesType()
        #obj2 = PolicyRuleType()
        #obj3 = SequenceType()
        #obj3.set_major
        #obj3.set_minor
        #obj2.set_rule_sequence(obj3)
        #obj2.set_rule_uuid(
        #obj2.set_direction
        #obj2.set_protocol

    @timeit
    def create_policies(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        policy_count  = tenant_conf.get('policy,count',None)
        if policy_count is None:
          return
        action_list = None
        policy_rules = self.construct_policy_rules(tenant_conf['policy,allow_rules_network'],tenant_conf['policy,allow_rules_port'],action_list)
        kwargs_list = []
        for tenant in tenant_list:
          if tenant['fq_name'] == ['default-domain','admin']:
             continue
          tenant_indx = get_tenant_index(tenant_conf,tenant['fq_name'])
          policy_name = generate_policy_name(global_conf,tenant_conf,tenant_indx)
          kwargs = {}
          kwargs['tenant']      = tenant
          kwargs['policy_name'] = policy_name
          kwargs['rules']       = policy_rules
          kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.create_policy(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
   
    @wrapper
    def delete_policy(self,*arg,**kwarg):
        tenant           = kwarg['tenant']
        tenant_uuid      = tenant['uuid']
        connections = kwarg['connection_obj'].connections
        policys  = connections.vnc_lib.network_policys_list(parent_id=tenant_uuid)['network-policys']
        for policy in policys:
            try:
               connections.vnc_lib.network_policy_delete(id=policy['uuid'])
            except NoIdError:
               pass

    def delete_policies(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_policy(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def detach(self,connections,tenant_fq_name,vn_fq_name):
        vn_obj     = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.set_network_policy_list([],True)
        connections.vnc_lib.virtual_network_update(vn_obj)
        return

    @wrapper
    def attach_policy(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        tenant           = kwarg['tenant'] 
        tenant_fq_name   = tenant['fq_name']
        policy_name      = kwarg['policy_name']
        vn_fq_name       = kwarg['vn_fq_name']
        domain_name,tenant_name = tenant_fq_name
        domain,tenant,vn_name   = vn_fq_name
        policy_fq_name = [domain_name,tenant_name,policy_name]
        try:
           policy_obj = connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
        except NoIdError:
           print "ERROR: network policy missing..skipping attach_policy to VN"
           print "ERROR: vn_name:%s,policy_name:%s"%(str(vn_fq_name),str(policy_name))
           return
        vn_obj     = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        vn_obj.add_network_policy(policy_obj,VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0)))
        connections.vnc_lib.virtual_network_update(vn_obj)

    @wrapper
    def detach_policy(self,*arg,**kwarg):
        tenant_fq_name   = kwarg['tenant_fq_name']
        vn_fq_name       = kwarg['vn_fq_name']
        connections = kwarg['connection_obj'].connections
        self.detach(connections,tenant_fq_name,vn_fq_name)

    def detach_policies(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        kwargs_list = []
        vn_obj = VN(None)
        vn_list = vn_obj.list_vn(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if not vn_list:
           return
        for vn in vn_list:
           tenant_fq_name,vn_id,vn_fq_name = vn
           kwargs = {}
           kwargs['tenant_fq_name'] = tenant_fq_name
           kwargs['vn_fq_name']     = vn_fq_name
           kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.detach_policy(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

class AnalyticsConfig(Base):

    def read_url(self,url,headers):

        response = requests.get(url,headers=headers)
        if response.status_code == 200:
           return json.loads(response.text)
        else:
           return {}
    
    @wrapper
    def analytics(self,*arg,**kwarg):

        global_conf = kwarg['global_conf']
        connections = kwarg['connection_obj'].connections

        analytics_conf = global_conf['analytics']
        analytics_check_negative_value = analytics_conf['global']['check_negative_value']
        params = analytics_conf['params']
        params_list = map(lambda x:x['name'],params) 
		
        headers = {'X-Auth-Token': '356f09e8f0004b10a97a2bd4f0fd85f1'}        

        vnetworks_list = self.read_url("http://172.16.70.3:8081/analytics/uves/virtual-networks",headers)
        vn_out_stats = []
        for vnetwork_link in vnetworks_list:
           vn_name = vnetwork_link.get('name') 
           vn_link = vnetwork_link.get('href')
           if not re.search('default-domain:admin:MGMT|symantec.Tenant',vn_name):
              continue
           vnetwork_response = self.read_url(vn_link,headers)
           UveVirtualNetworkAgent = vnetwork_response.get('UveVirtualNetworkAgent',None)
           if UveVirtualNetworkAgent == None:
              continue
           for k,v in UveVirtualNetworkAgent.iteritems():
               if 'Vnetwork.UveVirtualNetworkAgent.%s'%k in params_list or 'Vnetwork.UveVirtualNetworkAgent.ALL' in params_list:
                  #print vn_name,k,UveVirtualNetworkAgent[k]
                  pass
               else:
                  continue
               if k == 'out_stats':
                  vn_out_stats.append(v)
        if len(vn_out_stats):
             parse_vn_out_stats(vn_out_stats)
	if True:
           return

        vrouters_list = self.read_url("http://172.16.70.3:8081/analytics/uves/vrouters",headers)

        cpu_info_values = []
        for vrouter_link in vrouters_list:
           compute_name = vrouter_link.get('name') 
           compute_link = vrouter_link.get('href')
           vrouter_response = self.read_url(compute_link,headers)
           VrouterStatsAgent = vrouter_response['VrouterStatsAgent']
           for k,v in VrouterStatsAgent.iteritems():
               if 'Vrouter.VrouterStatsAgent.%s'%k in params_list or 'Vrouter.VrouterStatsAgent.ALL' in params_list:
                  print compute_name,k,VrouterStatsAgent[k]
               else:
                  continue
               if k == 'cpu_info':
                  cpu_info_values.append(v)
        if len(cpu_info_values):
           parse_cpu_info(cpu_info_values)
         
    def analyticss(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties,dpdk):
        kwargs_list         = []   
        kwargs = {}
        kwargs_list.append(kwargs)
        if len(kwargs_list):
           self.analytics(global_conf=global_conf,tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

class ProjectConfig(Base):


    def create(self,connections,domain_name,tenant_name):

        fixture = ProjectFixture(domain_name=domain_name,project_name=tenant_name, connections=connections)
        fixture.setUp()
        project_id = fixture.get_uuid()
        connections.auth.add_user_to_project('admin',tenant_name)
        return project_id
    
    @wrapper
    def list_projects(self, *arg, **kwarg):
        connection_obj   = kwarg['connection_obj']
        connections = connection_obj.connections
        projects_list = connections.vnc_lib.projects_list()['projects']
        print projects_list
        return projects_list

    def retrieve_admin_tenant_info(self,conn_obj_list):
        projects_list = self.list_projects(tcount=1,conn_obj_list=conn_obj_list)
        for proj in projects_list:
            if proj['fq_name'] == ['default-domain','admin']: 
               return {'fq_name':['default-domain','admin'],'uuid':proj['uuid']}

    def retrieve_configured_tenant_list(self,conn_obj_list):
        exclude_tenants = [u'invisible_to_admin',u'default-project', u'demo','service']
        tenant_list = [] 
        projects_list = self.list_projects(tcount=1,conn_obj_list=conn_obj_list)
       
        for proj in projects_list:
            domain,t_name = proj['fq_name']
            if t_name in exclude_tenants:
               continue
            tenant_list.append({'fq_name':proj['fq_name'],'uuid':proj['uuid']})
        #tenant_list = sorted_nicely(tenant_list)
        return tenant_list

    @wrapper
    def retrieve_vn_list(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        vn_list = connections.vnc_lib.virtual_networks_list()['virtual-networks']
        return vn_list

    @wrapper
    def configured_rt_numbers(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        existing_rt_list = []
        rt_list = connections.vnc_lib.route_targets_list()['route-targets']
        for rt in rt_list:
            existing_rt_list.append(rt['fq_name'][2])
        return existing_rt_list

    @wrapper
    def configured_cidr(self,*arg,**kwarg):
        existing_cidr = []
        connections = kwarg['connection_obj'].connections
        ipams_list       = connections.vnc_lib.network_ipams_list()['network-ipams']
        existing_vns     = []
        for ipam in ipams_list:
           ipam_id  = ipam['uuid']
           try:
             ipam_obj = connections.vnc_lib.network_ipam_read(id=ipam_id)
           except NoIdError,TypeError:
             continue
           virtual_nw_back_refs = ipam_obj.get_virtual_network_back_refs() or []
           for nw in virtual_nw_back_refs:
               domain,t_name,vn_name = nw['to']
               existing_vns.append(nw['to'])
               subnets = nw['attr']['ipam_subnets']
               for subnet in subnets:
                   cidr_l = str(subnet['subnet']['ip_prefix']) + "/" + str(subnet['subnet']['ip_prefix_len'])
                   existing_cidr.append(cidr_l)

        return (existing_cidr,existing_vns)

    @wrapper
    def create_tenant(self,*arg,**kwarg):
        connection_obj   = kwarg['connection_obj']
        connections = connection_obj.connections
        #auth        = connection_obj.auth
        domain_name,tenant_name = kwarg['tenant_fq_name']
            
        project_id  = self.create(connections,domain_name,tenant_name)

    def create_tenants(self,admin_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        existing_projects_list = self.list_projects(tcount=1,conn_obj_list=admin_conn_obj_list)
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name          = tenant['fq_name']
            domain_name,tenant_name = tenant_fq_name
            project_count = 0
            for proj in existing_projects_list:
                dom,tname = proj['fq_name']
                if ( proj['fq_name'] == tenant_fq_name ) or (re.search('^%s-'%tenant_name,tname) and dom == domain_name ):
                   project_count += 1
            if project_count == 1 :
               print "INFO: tenant:%s already exists..skipping create"%tenant_name
               continue
            elif project_count > 1:
               print "ERROR: More than one uuid for the tenant:%s seen"%tenant_name
               sys.exit()
            else:
               kwargs = dict()
               kwargs['tenant_fq_name'] = tenant_fq_name
               kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        ret = self.create_tenant(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def update_security_group(self,*arg,**kwarg):
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        connection_obj   = kwarg['connection_obj']
        connections = connection_obj.connections
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        uuid_3 = uuid.uuid1().urn.split(':')[2]
        uuid_4 = uuid.uuid1().urn.split(':')[2]
        rules = [{'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1,'ethertype': 'IPv4'
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_2,'ethertype': 'IPv4'
                  },
                  {'direction': '>',
                 'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_3,'ethertype': 'IPv6'
                  },
                  {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_4,'ethertype': 'IPv6'
                  }
                 ]

        sg_fq_name = tenant_fq_name + ['default']
        try:
           sg_obj = connections.vnc_lib.security_group_read(fq_name=sg_fq_name)
           rule_list = PolicyEntriesType(policy_rule=rules)
           sg_obj.set_security_group_entries(rule_list)
           connections.vnc_lib.security_group_update(sg_obj)
        except:
           print "ERROR: in creating update_security_groups"
           traceback.print_exc(file=sys.stdout)
           pass # TO_FIX

    @timeit
    def update_security_groups(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties=False):
        if update_properties:
           return
        if tenant_list == [{'fq_name': ['default-domain', 'admin']}]: # GLobalConfig Update
           kwargs = dict()
           kwargs['tenant'] = {'fq_name': ['default-domain', 'admin']}
           self.update_security_group(tcount=thread_count,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
           return
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            kwargs = dict()
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        
        if len(kwargs_list) == 0:
           return
        self.update_security_group(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
    
    def add_user_to_tenant(self, uuid):
        kc = connections.get_auth_h().get_keystone_h()
        user_id = kc.get_user_dct(connections.inputs.stack_user)
        role_id = kc.get_role_dct('admin')
        kc._add_user_to_tenant(uuid.replace('-', ''), user_id, role_id)


    #def update_default_sg(self,tenant_name=tenant_name,uuid=None):
    #    project_fixture = self.get_fixture(tenant_name=tenant_name,uuid=uuid)
    #    project_fixture.set_sec_group_for_allow_all()

    def delete(self,connections,tenant_name, uuid):
        project_fixture= self.get_fixture(connections=connections,tenant_name=tenant_name,uuid=uuid)
        project_fixture.delete(verify=True)

    @retry(tries=3,delay=5)
    @wrapper
    def delete_tenant(self,*arg,**kwarg):
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        dom,tenant_name  = tenant_fq_name
        tenant_uuid      = tenant['uuid']
        connections = kwarg['connection_obj'].connections
        try:
          proj_obj = connections.vnc_lib.project_read(id=tenant_uuid)
        except NoIdError:
          print "project %s not found..skipping delete"%str(tenant_fq_name)
          return True
        try:
          self.delete(connections,tenant_name,tenant_uuid)
          return True
        except NoIdError:
          return True
        except ConnectionError:
          return False
        except RefsExistError:
          print "ERROR: delete failed..RefExists for project:",proj_obj.uuid
          traceback.print_exc(file=sys.stdout)
          handleRefsExistError()
        except:
          print "ERROR seen during delete_tenant:%s...retrying.."%str(tenant_fq_name)
          traceback.print_exc(file=sys.stdout)
          return False
    
    def delete_tenants(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin'] or tenant['fq_name'] == ['default-domain','services']:
             continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_tenant(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=kwargs_list)

    def verify(self, uuid):
        self.fixture= self.get_fixture(uuid=uuid)
        assert self.fixture.verify_on_setup()

    def get_fixture(self,connections,tenant_name, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            fixture = ProjectFixture(connections=connections,project_name=tenant_name,uuid=uuid)
        return fixture

class vDNSInfo:

      def __init__(self,tenant_domain_name,domain_name):
        self.tenant_domain_name = tenant_domain_name
        self.domain_name = domain_name
        d = domain_name.split(".")

        if len(d) == 2 :
          self.forwarder = None
        else:
          self.forwarder = ".".join(d[1:])
 
      def get_tenant_domain_name(self):
         return self.tenant_domain_name

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
        self.fixture = VdnsFixture(connections=connections, name=name)
        self.fixture.setUp()
        return self.fixture.get_uuid()

    def delete(self, tenant_name,uuid):
        vdns_fixture = self.get_fixture(tenant_name=tenant_name,uuid=uuid)
        vdns_fixture.delete(verify=True)

    def verify(self, uuid):
        vdns_fixture = self.get_fixture(uuid=uuid)
        assert vdns_fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = VdnsFixture(connections=connections, uuid=uuid)
        return self.fixture

    def generate_vdns_list(self,vdns,tenant_domain_name,domain_name):
        d = domain_name.split(".")
        if len(d) <= 2 :
          return vdns

        if not vdns.has_key(domain_name):
           vdns[domain_name] = vDNSInfo(tenant_domain_name,domain_name)
           self.generate_vdns_list(vdns,tenant_domain_name,".".join(d[1:]))

        return vdns

    @wrapper
    def delete_record(self,*arg,**kwarg):
        tenant_domain_name = kwarg.get('tenant_domain_name',None)
        tenant_fq_name = kwarg.get('tenant_fq_name',None)
        domain_name    = kwarg.get('domain_name',None)
        forwarder_name = kwarg.get('forwarder_name',None)
        connections = kwarg['connection_obj'].connections
        dns_records = connections.vnc_lib.virtual_DNS_records_list()['virtual-DNS-records']
        if domain_name is None and tenant_domain_name is None:
           records_to_delete = dns_records
        elif tenant_domain_name :
           records_to_delete = filter(lambda x:x['fq_name'][0] == tenant_domain_name,dns_records)
        else:
           t_domain,tenant_name = tenant_fq_name
           records_to_delete = []
           for record in dns_records:
               if record['fq_name'] == [t_domain,forwarder_name,domain_name] :
                  records_to_delete.append(record)
        for dns_record in records_to_delete :
           connections.vnc_lib.virtual_DNS_record_delete(fq_name=dns_record['fq_name'])

    @wrapper
    def create_record(self,*arg,**kwarg):
      try:
        tenant_domain_name = kwarg['tenant_domain_name']
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
        connections = connection_obj.connections

        try:
          connections.vnc_lib.virtual_DNS_record_read(fq_name=[tenant_domain_name,forwarder.split(':')[-1],rec_name])
          print "Record: %s:%s found..skipping create"%(tenant_domain_name,rec_name)
          return
        except NoIdError:
          pass  # continue with record creation  

        vdns_obj = connections.vnc_lib.virtual_DNS_read(fq_name_str = forwarder)
        vdns_rec_data = VirtualDnsRecordType(rec_name, rec_type, rec_class, rec_data, int(rec_ttl))
        vdns_rec_obj = VirtualDnsRecord(rec_name, vdns_obj, vdns_rec_data)
        connections.vnc_lib.virtual_DNS_record_create(vdns_rec_obj)
      except:
        print "ERROR in vDNS create"
        traceback.print_exc(file=sys.stdout)

    @wrapper
    def create_vdns(self,*arg,**kwarg):

        name        = kwarg['vdns_name']
        tenant_domain_name = kwarg['tenant_domain_name']
        dns_domain  = kwarg['vdns_domain_name']
        dyn_updates = kwarg['vdns_dyn_updates']
        rec_order   = kwarg['vdns_rec_order']
        ttl         = kwarg['vdns_ttl']
        next_vdns   = kwarg['vdns_next_vdns']
        fip_record  = kwarg['vdns_fip_record']
        reverse_resolution = kwarg['vdns_reverse_resolution']
        
        connection_obj = kwarg['connection_obj']
        connections = connection_obj.connections

        domain_name_list = []
        domain_name_list_list = list(domain_name_list)
        ## TO_FIX domain_obj is not used.
        try:
            domain_obj = connections.vnc_lib.domain_read(fq_name=[tenant_domain_name])
        except NoIdError:
            domain_obj = None

        if next_vdns and len(next_vdns):
          try:
           next_vdns_obj = connections.vnc_lib.virtual_DNS_read(fq_name_str = next_vdns)
          except NoIdError:
           pass

        try:
          connections.vnc_lib.virtual_DNS_read(fq_name=[u'%s'%tenant_domain_name,u'%s'%name])
          print "Virtual DNS " + name + " found..skipping create.."
          return
        except NoIdError: 
          pass

        vdns_str = ':'.join([tenant_domain_name, name])
        vdns_data = VirtualDnsType(domain_name=dns_domain, dynamic_records_from_client=dyn_updates, record_order=rec_order, default_ttl_seconds=int(ttl),next_virtual_DNS=next_vdns,reverse_resolution=reverse_resolution,floating_ip_record=fip_record)

        dns_obj    = VirtualDns(name, domain_obj,virtual_DNS_data = vdns_data)
        connections.vnc_lib.virtual_DNS_create(dns_obj)

    def create_mgmt_vdns_tree(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
        if update_properties:
           return
        mgmt_vdns_domain_name_pattern = global_conf.get('vdns,domain_name,pattern',None)
        if mgmt_vdns_domain_name_pattern is None:
           return
        mgmt_vdns_domain_name         = re.sub(global_conf['test_id,replace_str'],str(global_conf['test_id']),mgmt_vdns_domain_name_pattern)

        domain_list = []
        domain_list.append(["default-domain",mgmt_vdns_domain_name])
        self.create_vdns_tree(conn_obj_list,global_conf,tenant_conf,domain_list)

    @timeit
    def create_data_vdns_tree(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        data_vdns_domain_name_pattern = tenant_conf.get('vdns,domain_name,pattern',None)
        if data_vdns_domain_name_pattern is None:
           return
        domain_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name = tenant['fq_name']
            tenant_domain_name,tenant_name = tenant_fq_name
            tenant_index = get_tenant_index(tenant_conf,tenant_fq_name)
            tenant_vdns_domain_name = generate_domain_name(global_conf,tenant_conf,tenant_index)
            domain_list.append([tenant_domain_name,tenant_vdns_domain_name])
        self.create_vdns_tree(admin_conn_obj_list,global_conf,tenant_conf,domain_list)

    def create_vdns_tree(self,conn_obj_list,global_conf,tenant_conf,domain_list):
        global_vdns = {}
        for tenant_domain_name,vdns_domain in domain_list:
          global_vdns = self.generate_vdns_list(global_vdns,tenant_domain_name,vdns_domain)
          base_domain = ".".join(vdns_domain.split(".")[-2:])		
          global_vdns[base_domain] = vDNSInfo(tenant_domain_name,base_domain)

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
              self.create_vdns(conn_obj_list=conn_obj_list,kwargs_list=[vdns_conf])
              conf = {}
              conf['tenant_domain_name'] = vdns_conf['tenant_domain_name']
              conf['forwarder']  = vdns_conf['vdns_next_vdns']
              conf['rec_name']   = re.sub("\.","-",vdns_conf['vdns_domain_name'])
              conf['rec_data']   = conf['tenant_domain_name'] + ":%s"%conf['rec_name']
              conf['rec_ttl']    = 86400
              conf['rec_type']   = "NS"
              conf['rec_class']  = "IN"
              self.create_record(conn_obj_list=conn_obj_list,kwargs_list=[conf])

    def delete_record_per_tenant(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name     = tenant['fq_name']
            domain_name,tenant_name = tenant_fq_name
            tenant_index       = get_tenant_index(tenant_conf,tenant_fq_name)
            domain_server_name = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            forwarder_name     = "-".join(domain_server_name.split("-")[1:])
            kwargs = {}
            kwargs['tenant_fq_name'] = tenant_fq_name
            kwargs['domain_name']    = domain_server_name
            kwargs['forwarder_name'] = forwarder_name
            kwargs_list.append(kwargs) 
        if len(kwargs_list) == 0:
           return
        self.delete_record(tcount=thread_count,conn_obj_list=admin_conn_obj_list[0:],kwargs_list=kwargs_list)

    @wrapper
    def delete_vdns_tree(self,*args,**kwargs):

       root_domain  = kwargs['root_domain'] 

       connections = kwargs['connection_obj'].connections

       vdns_list = connections.vnc_lib.virtual_DNSs_list()['virtual-DNSs']
       vdns_info = {}
       vdns_ids = []
       for vdns in vdns_list :
          if vdns["fq_name"][0] != root_domain[0]:
             continue
          vdns_obj = connections.vnc_lib.virtual_DNS_read(vdns["fq_name"])
          fq_name_str = ":".join(vdns["fq_name"])
          vdns_info[vdns_obj.uuid] = fq_name_str
          vdns_info[fq_name_str]   = vdns_obj.uuid
          vdns_ids.append(vdns_obj.uuid)
          vdns_data = vdns_obj.get_virtual_DNS_data()
          up_vdns   = vdns_data.get_next_virtual_DNS()
          if up_vdns is None:
             up_vdns = "root_domain"
          if vdns_info.has_key("%s,down"%up_vdns):
             vdns_info["%s,down"%up_vdns].append(vdns_obj.uuid)
          else:
             vdns_info["%s,down"%up_vdns] = [vdns_obj.uuid]
          vdns_info['%s,up'%vdns_obj.uuid] = up_vdns
       for i in xrange(10):
         if len(vdns_ids) == 0:
            break
         vdns_ids1 = vdns_ids[:]
         for vdns_id in vdns_ids :
           vdns_name = vdns_info[vdns_id]
           if not vdns_info.has_key('%s,down'%vdns_name) or len(vdns_info['%s,down'%vdns_name]) == 0:
              up_vdns = vdns_info['%s,up'%vdns_id]
              vdns_info['%s,down'%up_vdns].remove(vdns_id)
              vdns_ids.remove(vdns_id)
              connections.vnc_lib.virtual_DNS_delete(id=vdns_id)
     
    @wrapper
    def list_domains(self,*arg,**kwarg):
        connections  = kwarg['connection_obj'].connections
        domains = connections.vnc_lib.domains_list() ['domains']
        return domains

    def delete_vdns(self,conn_obj_list):

       kw = {'conn_obj_list':[conn_obj_list[0]]}
       domains = self.list_domains(count=1,**kw)
       for domain in domains:
           kw = {'conn_obj_list':[conn_obj_list[0]],'tenant_domain_name':domain['fq_name'][0]}
           self.delete_record(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=[kw])
           kwargs = {'root_domain':domain['fq_name'] ,'conn_obj_list':[conn_obj_list[0]]}
           self.delete_vdns_tree(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=[kwargs])
       return

class IPAM(Base):
    def create(self, connections,name, vdns_id=None):
        vdns_obj=None
        if vdns_id:
            vdns_obj = connections.vnc_lib.virtual_DNS_read(id=vdns_id)
        fixture = IPAMFixture(connections=connections,
                                   name=name, vdns_obj=vdns_obj)
        fixture.setUp()
        return fixture.get_uuid()

    @wrapper
    def create_ipam(self,*arg,**kwarg):
        tenant             = kwarg['tenant']
        tenant_fq_name     = tenant['fq_name']
        ipam_name          = kwarg['ipam_name']
        domain_server_name = kwarg['domain_server_name']
        connections   = kwarg['connection_obj'].connections
        domain_name,tenant_name = tenant_fq_name
        ipam_fq_name = tenant_fq_name + [ipam_name]
        try:
           connections.vnc_lib.network_ipam_read(fq_name=ipam_fq_name)
           print "IPAM: %s already available...skipping create.."%str(ipam_fq_name)
           return
        except NoIdError :
           pass
        domain_obj = connections.vnc_lib.virtual_DNS_read(fq_name=[domain_name,u"%s"%domain_server_name])
        
        ipam_obj = NetworkIpam(name=ipam_name, parent_type='project',
                           fq_name=ipam_fq_name, network_ipam_mgmt=IpamType("dhcp"))

        vdns_server   = IpamDnsAddressType(virtual_dns_server_name=domain_obj.get_fq_name_str())
        ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=vdns_server)
        ipam_obj.set_network_ipam_mgmt(ipam_mgmt_obj)
        ipam_obj.add_virtual_DNS(domain_obj)
        try:
          connections.vnc_lib.network_ipam_create(ipam_obj)
        except RefsExistError:
          pass

    @timeit
    def create_ipams(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        ipam_count          = tenant_conf.get('ipam,count',None)
        if ipam_count is None:
           return
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name      = tenant['fq_name']
            tenant_index        = get_tenant_index(tenant_conf,tenant_fq_name)
            domain_server_name  = generate_domain_server_name(global_conf,tenant_conf,tenant_index)
            for ipam_indx in xrange(ipam_count):
                ipam_name           = generate_ipam_name(global_conf,tenant_conf,tenant_index,ipam_indx)
                kwargs = {}
                kwargs['tenant']             = tenant
                kwargs['ipam_name']          = ipam_name 
                kwargs['domain_server_name'] = domain_server_name
                kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        self.create_ipam(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def delete(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        ipam_fixture.delete(verify=True)

    @wrapper
    def delete_ipam(self,*arg,**kwarg):

        connections = kwarg['connection_obj'].connections
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        tenant_uuid      = tenant['uuid']
        ipam_name        = kwarg.get('ipam_name',None)
        domain_name,tenant_name              = tenant_fq_name
        ipams = connections.vnc_lib.network_ipams_list(parent_id=tenant_uuid)['network-ipams']
        for ipam in ipams:
            ipam_name_t = tenant_fq_name + [ipam_name]
            if ipam_name is not None and ipam['fq_name'] != ipam_name_t:
               continue
            try:
               #self.delete(ipam['uuid'])
               connections.vnc_lib.network_ipam_delete(id=ipam['uuid'])
            except NoIdError,TypeError:
               pass
            except RefsExistError:
               print "ERROR: delete failed..RefExists for IPAM:",ipam['uuid']
               traceback.print_exc(file=sys.stdout)
               handleRefsExistError()

    def delete_ipams(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0 :
           return
        self.delete_ipam(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def verify(self, uuid):
        ipam_fixture = self.get_fixture(uuid=uuid)
        assert ipam_fixture.verify_on_setup()

    def get_fixture(self, uuid):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            self.fixture = IPAMFixture(connections=connections, uuid=uuid)
        return self.fixture

def additional_vn_count(global_conf,tenant_conf):

    vn_group_l = tenant_conf['tenant,vn_group_list']
    vn_count_dict       = {}
    for vn_group_index in xrange(len(vn_group_l)):
        vn_info               = tenant_conf['tenant,vn_group_list'][vn_group_index]
        vn_group_cnt          = vn_info.get('count',1)
        additional_vns        = []
        if vn_info.has_key('vm,name_pattern'):
           vm_additional_vns     = vn_info.get('vm,additional_vn_list')
           additional_vns.extend(vm_additional_vns)
        if vn_info.has_key('bgp_vm,name_pattern'):
           bgp_vm_additional_vns = vn_info.get('bgp_vm,additional_vn_list')  
           additional_vns.extend(bgp_vm_additional_vns)
        for addntl_vn in additional_vns:
            name = addntl_vn['name']
            cnt  = addntl_vn.get('count',1)
            if vn_count_dict.has_key(name):
               vn_count_dict[name] += cnt * vn_group_cnt
            else:
               vn_count_dict[name]  = cnt * vn_group_cnt
    return vn_count_dict

def service_instance_vn_count(global_conf,tenant_conf):
    service_instances = tenant_conf.get('service_instances',None)
    service_templates = global_conf.get('service_templates',None)
    serial_service_chain  = tenant_conf.get('serial_service_chain',[])
    parallel_service_chain  = tenant_conf.get('parallel_service_chain',[])
    if service_instances is None or service_templates is None:
       return 0,0
    service_instances = service_instances[:]
    if len(serial_service_chain):
       serial_service_chain_count = serial_service_chain[0]['count']
       serial_service_chain_si_groups = []
       for si_group in serial_service_chain[0]['instances']:
           serial_service_chain_si_groups.append(si_group['name'])
    else:
       serial_service_chain_count = 0
       serial_service_chain_si_groups = []
    if len(parallel_service_chain):
       parallel_service_chain_count = parallel_service_chain[0]['count']
       parallel_service_chain_si_groups = []
       for si_group in parallel_service_chain[0]['instances']:
           parallel_service_chain_si_groups.append(si_group['name'])
    else:
       parallel_service_chain_count = 0
       parallel_service_chain_si_groups = []
    service_instances_serial = []
    service_instances_single = [] 
    service_instances_parallel = [] 
    standalone_si_count = 0
    trans_standalone_si_count = 0
    trans_serial_si_count      = 0
    trans_parallel_si_count      = 0
    for i in xrange(len(service_instances)):
        si_group = service_instances.pop()
        if si_group['name'] in serial_service_chain_si_groups:
           service_instances_serial.append(si_group)
           if re.search('transparent',si_group['service_template_name']):
              trans_serial_si_count += si_group.get('count',1)
        elif si_group['name'] in parallel_service_chain_si_groups:
           service_instances_parallel.append(si_group)
           if re.search('transparent',si_group['service_template_name']):
              trans_parallel_si_count += si_group.get('count',1)
        else:
           try:
              left_vn_count = si_group['interfaces']['left']['count']
           except:
              left_vn_count = 1
           configure = si_group.get('configure',True)
           if configure == False:
              continue
           cnt = si_group.get('count',1) * left_vn_count
           standalone_si_count += cnt
           service_instances_single.append(si_group)
           if re.search('transparent',si_group['service_template_name']):
              trans_standalone_si_count += cnt
    service_instances = service_instances_serial + service_instances_parallel + service_instances_single
    vn_count = serial_service_chain_count + parallel_service_chain_count + standalone_si_count
    trans_si_count = trans_serial_si_count * serial_service_chain_count + trans_parallel_si_count * parallel_service_chain_count + trans_standalone_si_count
    return vn_count,trans_si_count
 
class VN(Base):
    @wrapper
    def list_vn(self,*arg,**kwarg):
       tenant_list      = kwarg.get('tenant_list',None)
       vn_name_prefix   = kwarg.get('vn_name_prefix',None)
       connections = kwarg['connection_obj'].connections
       vnet_list = []
       for tenant in tenant_list:
         if tenant['fq_name'] == ['default-domain','admin']:
             continue
         tenant_fq_name = tenant['fq_name']
         tenant_id = tenant['uuid']
         net_list  = connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
         for vn in net_list:
            domain,tenant_name,vn_name = vn['fq_name']
            if [domain,tenant_name] == ['default-domain','admin']:
               continue
            if vn_name_prefix is None or re.search('^%s'%vn_name_prefix,vn['fq_name'][-1]):
               vnet_list.append((tenant_fq_name,vn['uuid'],vn['fq_name']))
       return vnet_list

    def create(self,connections, name, subnets=[], ipam_name_list=[], external=False,shared=False,disable_gateway=False,rt_number=None,project_obj=None,forwarding_mode=None,project_name=None):
        kwargs = dict()
        kwargs['shared'] = shared
        kwargs['ipam_fq_name_list'] = ipam_name_list
        kwargs['router_external'] = external
        kwargs['rt_number']       = rt_number
        kwargs['disable_gateway'] = disable_gateway
        kwargs['forwarding_mode'] = forwarding_mode
        kwargs['project_obj']     = project_obj
        kwargs['project_name']    = project_name
        fixture = VNFixture(connections=connections, vn_name=name,
                                 subnets=subnets, **kwargs)
        fixture.setUp()
        
        uuid = fixture.get_uuid()
        return uuid

    @wrapper
    def add_extend_to_pr(self,*arg,**kwarg):

        connections = kwarg['connection_obj'].connections
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

        connections.vnc_lib.physical_router_update(pr_obj)

    @wrapper
    def get_vn_ids(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        tenant_list      = kwarg['tenant_list']
        vn_names_list    = kwarg.get('vn_names_list',[])
        vn_info_dict = {}
        for tenant in tenant_list:
            tenant_fq_name = tenant['fq_name']
            tenant_uuid    = tenant['uuid']
            try:
              project_obj = connections.vnc_lib.project_read(id=tenant_uuid)
            except NoIdError:
              print "tenant :%s missing..skipping..."%str(tenant_fq_name)
              continue
            vns = project_obj.get_virtual_networks()
            if not vns:
               continue
            for vn in vns:
                   vn_info_dict[":".join(vn[u'to'])] = vn[u'uuid']
        return vn_info_dict

    @wrapper
    def delete_extend_to_pr(self,*args,**kwarg):

        connections = kwarg['connection_obj'].connections
        pr_obj_list      = kwarg['pr_obj_list']
        vn_id            = kwarg['vn_id']

        try:
          vn_obj = connections.vnc_lib.virtual_network_read(id=vn_id)
        except NoIdError:
          print "VN :%s missing..skipping delete extend to physical router"%vn_id
          return
 
        for pr_obj in pr_obj_list:
            pr_obj.del_virtual_network(vn_obj)
            connections.vnc_lib.physical_router_update(pr_obj)

    @wrapper
    def update_pr_objs(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        pr_objs          = kwarg['pr_objs']
        for router_name,pr_obj in pr_objs.iteritems():
            connections.vnc_lib.physical_router_update(pr_obj)

    @wrapper
    def delete_pr_extn(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        pr_obj_info      = kwarg['pr_obj_info']
        vn_ids           = kwarg['vn_ids']
        for vn_id in vn_ids:
            vn_obj = connections.vnc_lib.virtual_network_read(id=vn_id)
            pr_refs = vn_obj.get_physical_router_back_refs()
            if pr_refs is None:
               continue
            for pr_ref in pr_refs:
               pr_fq_name = pr_ref['to']
               pr_name    = pr_fq_name[1]
               pr_obj     = pr_obj_info[pr_name]
               pr_obj.del_virtual_network(vn_obj)
        for pr_name,pr_obj in pr_obj_info.iteritems():
            connections.vnc_lib.physical_router_update(pr_obj)

    def delete_extend_to_physical_routers(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        tenant_count = tenant_conf['tenant,count']
        router_obj   = RouterConfig(None)
        pr_names     = router_obj.retrieve_existing_pr(tcount=1,conn_obj_list=admin_conn_obj_list)
        pr_obj_info  = {}

        for router_name in pr_names:
            kw = {}
            kw['router_name'] = router_name
            pr_obj = self.retrieve_pr_obj(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kw])
            if pr_obj:
               pr_obj_info[router_name] = pr_obj

        kwargs_list = []
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        vn_obj = VN(None)
        vn_list = vn_obj.list_vn(conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if not vn_list:
           return

        for vn in vn_list:
           kwargs = {}
           kwargs['pr_obj_list'] = pr_obj_info.values()
           tenant_name_fq,uid,fq_name = vn
           kwargs['vn_id']            = uid
           kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return

        self.delete_extend_to_pr(tcount=1,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def retrieve_pr_obj(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        router_name = kwarg['router_name']
        pr_fq_name  = [u'default-global-system-config', u'%s'%router_name]
        try:
          pr_obj = connections.vnc_lib.physical_router_read(fq_name=pr_fq_name)
        except NoIdError:
          pr_obj = None
        return pr_obj

    @timeit
    def update_extend_to_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])
        pr_obj_list = []
        for router_name in pr_mx_name_list:
            pr_obj = self.retrieve_pr_obj(tcount=1,conn_obj_list=conn_obj_list,router_name=router_name)
            if pr_obj:
               pr_obj_list.append(pr_obj)
        if len(pr_obj_list) == 0:
           return
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name = tenant['fq_name']
            tenant_index = get_tenant_index(tenant_conf,tenant_fq_name)
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
                   kwargs['tenant']      = tenant
                   kwargs['vn_name']     = vn_name
                   kwargs['router_list'] = pr_mx_name_list
                   kwargs['pr_obj_list'] = pr_obj_list
                   kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        self.add_extend_to_pr(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)
 
    @wrapper
    def create_vn(self,*arg,**kwarg):
        # disable GW works only with use_fixture.
        #use_fixture     = kwarg.get('use_fixture',True)
        use_fixture     = False
        vn_name         = kwarg['vn_name']
        #ipam_name       = kwarg['ipam_name']
        tenant          = kwarg['tenant']
        tenant_fq_name  = tenant['fq_name']
        disable_gateway = kwarg.get('disable_gateway',False)
        external        = kwarg.get('external_flag',False)
        shared          = kwarg.get('shared_flag',False)
        rt_number       = kwarg.get('rt_number',None)
        asn_number      = kwarg.get('asn_number',None)
        fwd_mode        = kwarg.get('fwd_mode',None)
        ipv4_cidr_list  = kwarg.get('ipv4_cidr_list',[])
        ipv6_cidr_list  = kwarg.get('ipv6_cidr_list',[])
        subnet_count    = kwarg.get('subnet_count',1)
        attach_qos      = kwarg.get('attach_qos',False)
        qos_name        = kwarg.get('qos_name','')
        connections = kwarg['connection_obj'].connections
        vn_fq_name       = tenant_fq_name + [vn_name]
        ipam_fq_name_list = kwarg.get('ipam_fq_name_list',[])
        policy_name     = kwarg.get('policy_name',None)
        attach_policy   = kwarg.get('attach_policy',False)
        extend_to_pr    = kwarg.get('extend_to_pr',False)
        pr_obj_list     = kwarg.get('pr_obj_list',[])
        multi_chain_service_flag = kwarg.get('multi_chain_service_flag',False)
        flood_unknown_unicast    = kwarg.get('flood_unknown_unicast',False)
        reverse_path_forwarding  = kwarg.get('reverse_path_forwarding',False)
        allow_transit            = kwarg.get('allow_transit',False)
        update_properties        = kwarg.get('update_properties',False)
        domain_name,tenant_name  = tenant_fq_name
        project_obj = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
        project_obj.project_fq_name=tenant_name
        
        try:
           vn_obj = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
           print "INFO: VN:%s already existing..skipping create"%str(vn_fq_name)
        except NoIdError:
           vn_obj = None
        except:
           traceback.print_exc(file=sys.stdout)
           print "ERROR: exception seen..skipping create",str(vn_fq_name)
           return

        if vn_obj and not update_properties:
           return (extend_to_pr,vn_fq_name,vn_obj.uuid)

        if not vn_obj:

           if use_fixture:
              subnets = []
              for i,ipv4_cidr_gw in enumerate(ipv4_cidr_list):
                  ipv4_cidr,ipv4_gw = ipv4_cidr_gw
                  subnets.append({'cidr':ipv4_cidr,'name':vn_name+"_ipv4_subnet%d"%i})
              for i,ipv6_cidr in enumerate(ipv6_cidr_list):
                  subnets.append({'cidr':ipv6_cidr,'name':vn_name+"_ipv6_subnet%d"%i})
              if len(ipam_fq_name_list) == 1:
                 ipam_fq_name_list = len(subnets) * ipam_fq_name_list  
              self.create(connections,vn_name,subnets,ipam_fq_name_list,external,shared,disable_gateway,rt_number,project_obj,fwd_mode,connections.inputs.project_name)
              vn_obj = self.fixture.api_vn_obj
           else:
              vn_obj = VirtualNetwork(vn_name, parent_obj=project_obj,router_external=external,is_shared=shared,forwarding_mode=fwd_mode)
              ipam_sn_lst = []
              for i,ipv4_cidr_gw in enumerate(ipv4_cidr_list):
                  ipv4_cidr,ipv4_gw = ipv4_cidr_gw
                  ipv4_network,ipv4_prefix = ipv4_cidr.split("/")
                  ipam_sn = IpamSubnetType(subnet=SubnetType(ipv4_network, int(ipv4_prefix)),addr_from_start=True)
                  ipam_sn.set_subnet_name(vn_name+"_ipv4_subnet%d"%i)
                  if disable_gateway:
                    ipam_sn.set_default_gateway("0.0.0.0")
                  ipam_sn_lst.append(ipam_sn)
              for i,ipv6_cidr in enumerate(ipv6_cidr_list):
                  ipv6_network,ipv6_prefix = ipv6_cidr.split("/")
                  ipam_sn = IpamSubnetType(subnet=SubnetType(ipv6_network, int(ipv6_prefix)),addr_from_start=True)
                  ipam_sn.set_subnet_name(vn_name+"_ipv6_subnet%d"%i)
                  ipam_sn_lst.append(ipam_sn)
              if len(ipam_fq_name_list) == 1:
                 ipam_obj = connections.vnc_lib.network_ipam_read(fq_name=ipam_fq_name_list[0])
                 vn_obj.add_network_ipam(ipam_obj,VnSubnetsType(ipam_sn_lst))
              else:
                 ipam_fq_name_list = len(ipam_sn_lst) * ipam_fq_name_list  
                 for i,ipam_fq_name in enumerate(ipam_fq_name_list):
                     ipam_obj = connections.vnc_lib.network_ipam_read(fq_name=ipam_fq_name)
                     vn_obj.add_network_ipam(ipam_obj,VnSubnetsType(ipam_sn_lst[i]))
           if asn_number and rt_number:
              route_targets = RouteTargetList([":".join(["target",str(asn_number),str(rt_number)])])
              vn_obj.set_route_target_list(route_targets)

        vn_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
        vn_obj_properties.set_forwarding_mode(fwd_mode)
        if attach_policy:
           try:
              policy_fq_name = tenant_fq_name + [policy_name]
              policy_obj = connections.vnc_lib.network_policy_read(fq_name=policy_fq_name)
              vn_obj.add_network_policy(policy_obj,VirtualNetworkPolicyType(sequence=SequenceType(major=0, minor=0)))
           except NoIdError:
              print "ERROR: NoIdError seen for policy:%s VN:%s"%(str(policy_fq_name),str(vn_fq_name))
              pass

        vn_obj.multi_policy_service_chains_enabled = multi_chain_service_flag
        if flood_unknown_unicast:
           vn_obj.set_flood_unknown_unicast(True)
        else:
           vn_obj.set_flood_unknown_unicast(False)
        if reverse_path_forwarding:
           vn_obj_properties.set_rpf('enable')
        else:
           vn_obj_properties.set_rpf('disable')
        if allow_transit:
           vn_obj_properties.set_allow_transit(True)
        else:
           vn_obj_properties.set_allow_transit(False)
        vn_obj.set_virtual_network_properties(vn_obj_properties)

        if attach_qos:
          qos_fq_name = ['default-global-system-config','default-global-qos-config',qos_name]
          try:
            qos_config_obj = connections.vnc_lib.qos_config_read(fq_name=qos_fq_name)
            vn_obj.add_qos_config(qos_config_obj)
          except: 
            pass

        if use_fixture or update_properties: 
	   # VN is supposed to have been created already.just do update
           connections.vnc_lib.virtual_network_update(vn_obj)
        else:
           try:
               connections.vnc_lib.virtual_network_create(vn_obj)
           except RefsExistError:
               print "ERROR:", "RefsExistError:",vn_fq_name
               traceback.print_exc(file=sys.stdout)
           vn_obj = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        for pr_obj in pr_obj_list :
            if extend_to_pr:
               pr_obj.add_virtual_network(vn_obj)
               connections.vnc_lib.physical_router_update(pr_obj)
            elif update_properties and not extend_to_pr:
               pr_obj.del_virtual_network(vn_obj)
               connections.vnc_lib.physical_router_update(pr_obj)
        return (extend_to_pr,vn_fq_name,vn_obj.uuid)
         
    @wrapper
    def update_import_rt(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        global_conf      = kwarg['global_conf']
        tenant_conf      = kwarg['tenant_conf']
        tenant_fq_name     = kwarg['tenant_fq_name']
        rt_vn_name_pattern = kwarg['analyzer_public_vn']
        data_vn_name       = kwarg['data_vn_name']
        vn_indx = 0 
        tenant_indx = get_tenant_index(tenant_conf,tenant_fq_name)
        rt_vn_name   = generate_vn_name(global_conf,tenant_conf,tenant_indx,rt_vn_name_pattern,vn_indx)
        rt_vn_fq_name   = tenant_fq_name + [rt_vn_name]
        data_vn_fq_name = tenant_fq_name + [data_vn_name]
        data_vn_obj  = connections.vnc_lib.virtual_network_read(fq_name=data_vn_fq_name)
        rt_vn_obj    = connections.vnc_lib.virtual_network_read(fq_name=rt_vn_fq_name)
        public_vn_rt = rt_vn_obj.get_route_target_list().get_route_target() 
        rt_obj       = data_vn_obj.get_import_route_target_list() 
        if rt_obj:
           rt_info = rt_obj.get_route_target()
        else:
           rt_info = []
           rt_obj = RouteTargetList()
        rt_info.extend(public_vn_rt)
        rt_obj.set_route_target(rt_info)
        data_vn_obj.set_import_route_target_list(rt_obj)
        connections.vnc_lib.virtual_network_update(data_vn_obj)
  
    @timeit
    def create_vns(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties,dpdk,is_heat):
        kwargs_list = []
        project_obj = admin_conn_obj_list[0]
        already_allocated_cidr,existing_vns = project_obj.configured_cidr(tcount=1,conn_obj_list=admin_conn_obj_list)
        already_allocated_rt   = project_obj.configured_rt_numbers(tcount=1,conn_obj_list=admin_conn_obj_list)

        service_instances = tenant_conf.get('service_instances',None)
        service_templates = global_conf.get('service_templates',None)
        serial_service_chain  = tenant_conf.get('serial_service_chain',[])
        if len(serial_service_chain):
           serial_service_chain_count = serial_service_chain[0]['count']
           serial_service_chain_si_groups = []
           for si_group in serial_service_chain[0]['instances']:
               serial_service_chain_si_groups.append(si_group['name'])
        else:
           serial_service_chain_count = 0
           serial_service_chain_si_groups = []

        parallel_service_chain  = tenant_conf.get('parallel_service_chain',[])
        if len(parallel_service_chain):
           parallel_service_chain_count = parallel_service_chain[0]['count']
           parallel_service_chain_si_groups = []
           for si_group in parallel_service_chain[0]['instances']:
               parallel_service_chain_si_groups.append(si_group['name'])
        else:
           parallel_service_chain_count = 0
           parallel_service_chain_si_groups = []

        pr_mx_name_list = []
        pr_mxs = global_conf['pr_mx']
        for pr_mx in pr_mxs:
            pr_mx_name_list.append(pr_mx['name'])

        pr_obj_list = []
        for router_name in pr_mx_name_list:
            kw = {}
            kw['router_name'] = router_name
            pr_obj = self.retrieve_pr_obj(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kw])
            if pr_obj:
               pr_obj_list.append(pr_obj)

        port_mirror_rt_update_vn_list = [] 
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
             continue
            tenant_fq_name = tenant['fq_name']
            tenant_index   = get_tenant_index(tenant_conf,tenant_fq_name)
            ipam_count     = tenant_conf.get('ipam,count',None)
            ipam_fq_name_list = []
            for ipam_indx in xrange(ipam_count):
                ipam_name    = generate_ipam_name(global_conf,tenant_conf,tenant_index,ipam_indx)
                ipam_fq_name = tenant_fq_name + [ipam_name]
                ipam_fq_name_list.append(ipam_fq_name)
            policy_name  = generate_policy_name(global_conf,tenant_conf,tenant_index)
            additional_vn_count_d = additional_vn_count(global_conf,tenant_conf)
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
                vn_index        = 0
                vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
                fwd_mode        = vn_info.get('fwd_mode')
                vn_name_pattern = vn_info['vn,name,pattern']
 
                if re.search('Private_SC_Right_VN|Private_SC_Left_VN',vn_name_pattern):
                   vn_count,trans_si_count  = service_instance_vn_count(global_conf,tenant_conf)
                elif re.search('Private_SC_Auto_Left_VN|Private_SC_Auto_Right_VN',vn_name_pattern):
                   vn_count,trans_si_count  = service_instance_vn_count(global_conf,tenant_conf)
                   vn_count = trans_si_count
                elif re.search('Addnl_VN',vn_name_pattern):
                   vn_count = additional_vn_count_d[vn_name_pattern]
                else:
                   vn_count       = vn_info['count']
                   trans_si_count = 0

                vn_type              = get_vn_type(vn_name_pattern) 
                external_flag        = vn_info['external_flag']
                extend_to_pr_flag    = vn_info['extend_to_pr_flag']
                shared_flag          = vn_info['shared_flag']
                attach_policy_flag   = vn_info.get('attach_policy',False)
                subnet_count         = vn_info.get('subnet,count',1)
                ipv4_cidr            = vn_info.get('ipv4_cidr',False)
                ipv4_gw              = vn_info.get('ipv4_gw',False)
                ipv6_cidr            = vn_info.get('ipv6_cidr',False)
                flood_unknown_unicast   = vn_info.get('flood_unknown_unicast')
                reverse_path_forwarding = vn_info.get('reverse_path_forwarding')
                allow_transit           = vn_info.get('allow_transit')
                if ipv4_cidr is False and ipv6_cidr is False:
                   ipv4_cidr = True
                disable_gateway      = vn_info.get('disable_gateway')
                for vn_indx in xrange(vn_count):
                    vn_name = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_index)
                    if re.search('Private_SC_Right_VN|Private_SC_Left_VN',vn_name_pattern) \
                       and vn_index >= serial_service_chain_count and \
                       vn_index < (serial_service_chain_count + parallel_service_chain_count):
                           multi_chain_service_flag = True
                    else:
                       multi_chain_service_flag = False

                    vn_index += 1

                    vn_fq_name = tenant_fq_name + [vn_name]
                    if not update_properties and vn_fq_name in existing_vns and not is_heat:
                       continue

                    ipv4_cidr_list = []
                    if ipv4_cidr is True:
                       for i in xrange(subnet_count):
                         v4_cidr,v4_gw   = generate_v4_cidr(tenant_fq_name,vn_type,already_allocated_cidr)
                         already_allocated_cidr.append(v4_cidr)
                         ipv4_cidr_list.append([v4_cidr,v4_gw])
                    elif ipv4_cidr :
                       v4_cidr = ipv4_cidr
                       v4_gw   = ipv4_gw
                       already_allocated_cidr.append(v4_cidr)
                       ipv4_cidr_list.append([v4_cidr,v4_gw])
                    else:
                       v4_cidr = False

                    ipv6_cidr_list = []
                    if ipv6_cidr is True:
                       for i in xrange(subnet_count):
                         v6_cidr    = generate_v6_cidr(tenant_fq_name,vn_type,already_allocated_cidr)
                         already_allocated_cidr.append(v6_cidr)
                         ipv6_cidr_list.append(v6_cidr)
                    elif ipv6_cidr :
                       v6_cidr = ipv6_cidr
                       already_allocated_cidr.append(v6_cidr)
                       ipv6_cidr_list.append(v6_cidr)
                    else:
                       v6_cidr = False

                    rt_number    = vn_info.get('route_target,rt_number') 
                    asn_number   = vn_info.get('route_target,asn') 
                    if rt_number:
                       rt_number = generate_rt_number(already_allocated_rt)
                       already_allocated_rt.append(rt_number)
                    else:
                       rt_number = None
                    if vn_info.get('vm,attach_port_mirror'):
                       vn_fq_name = tenant_fq_name + [vn_name]
                       port_mirror_rt_update_vn_list.append(vn_fq_name)
                    if vn_info.get('qos',False) and vn_info['qos'].get('attach_qos'):
                       attach_qos = True
                       qos_name   = vn_info['qos']['qos_name']
                    else:
                       attach_qos = False
                       qos_name   = ""
                    kwarg = {}
                    kwarg['ipv4_cidr_list']    = ipv4_cidr_list
                    kwarg['ipv6_cidr_list']    = ipv6_cidr_list 
                    kwarg['ipam_fq_name_list'] = ipam_fq_name_list
                    kwarg['tenant']          = tenant
                    kwarg['vn_name']         = vn_name
                    kwarg['subnet_count']    = vn_info['subnet,count']
                    kwarg['asn_number']      = asn_number
                    kwarg['rt_number']       = rt_number
                    kwarg['external_flag']   = external_flag
                    kwarg['shared_flag']     = shared_flag
                    kwarg['disable_gateway'] = disable_gateway
                    kwarg['fwd_mode']        = fwd_mode
                    kwarg['policy_name']     = policy_name
                    kwarg['attach_policy']   = attach_policy_flag
                    kwarg['attach_qos']      = attach_qos
                    kwarg['qos_name']        = qos_name
                    kwarg['multi_chain_service_flag'] = multi_chain_service_flag
                    kwarg['extend_to_pr']    = extend_to_pr_flag
                    kwarg['pr_obj_list']     = pr_obj_list
                    kwarg['flood_unknown_unicast']   = flood_unknown_unicast
                    kwarg['reverse_path_forwarding'] = reverse_path_forwarding
                    kwarg['allow_transit']     = allow_transit
                    kwarg['update_properties'] = update_properties
                    kwargs_list.append(kwarg)

        if len(kwargs_list) == 0:
           return

        if is_heat:
           return kwargs_list

        extend_flag_vn_ids = self.create_vn(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)


        if update_properties:
           return

        kwargs_list = []
        for vn_name_l in port_mirror_rt_update_vn_list:
            dom,t_name,vn_name = vn_name_l
            kwargs = {}
            kwargs['tenant_fq_name']     = [dom,t_name]
            kwargs['data_vn_name']       = vn_name
            kwargs['tenant_conf']        = tenant_conf
            kwargs['global_conf']        = global_conf
            port_mirror_conf             = tenant_conf['port_mirror_conf']
            kwargs['analyzer_public_vn'] = port_mirror_conf['analyzer_public_vn']
            kwargs_list.append(kwargs)
        if len(kwargs_list) != 0:
           self.update_import_rt(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

        if type(extend_flag_vn_ids) == tuple:
           extend_flag_vn_ids = [extend_flag_vn_ids]       

        vn_ids    = []
        fq_name_l = []
        for extend_flag_vn_id in extend_flag_vn_ids: 
            extend_flag,fq_name,vn_id = extend_flag_vn_id
            if extend_flag:
               vn_ids.append(vn_id)
               fq_name_l.append(fq_name)

    def add_policy(self,fixture,policy_obj):
        fixture.bind_policies([policy_obj.policy_fq_name], self.vn_id)

    def delete_policy(self,fixture,policy_obj):
        fixture.unbind_policies(self.vn_id,[policy_obj.policy_fq_name])

    def delete(self,connections,vn_name, uuid, subnets=[]):
        if not subnets:
            subnets = self.get_subnets(connections,uuid)
        vn_fixture = self.get_fixture(connections,vn_name=vn_name,uuid=uuid, subnets=subnets)
        vn_fixture.obj = vn_fixture._orch_call('get_vn_obj_from_id',uuid)
        vn_fixture.delete(verify=True)

    @wrapper
    def delete_vn_by_name_process(self,*arg,**kwarg):
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        tenant_uuid      = tenant['uuid']
        vn_name          = kwarg['vn_name']
        connections = kwarg['connection_obj'].connections
        net_list = connections.vnc_lib.virtual_networks_list(parent_id=tenant_uuid)['virtual-networks']
        vn_id = None
        vn_fq_name = tenant_fq_name + [vn_name]
        for net in net_list:
           if net['fq_name'] == vn_fq_name:
              vn_id = net['uuid']
              break
        if vn_id is None:  
           return
        try:
          self.delete(connections,vn_name,vn_id)
        except RefsExistError:
          print "ERROR: delete failed..RefExists for VN:",vn_id
          traceback.print_exc(file=sys.stdout)
          handleRefsExistError()

    @timeit
    @wrapper
    def delete_vn(self,*arg,**kwarg):
        vn_id       = kwarg['vn_id']
        vn_fq_name  = kwarg['vn_fq_name']
        connections = kwarg['connection_obj'].connections
        print "INFO: deleting VN:%s , %s"%(str(vn_fq_name),vn_id)
        try:
           vn_obj = connections.vnc_lib.virtual_network_read(id=vn_id)
        except NoIdError,TypeError:
           return
        inst_ip_ref = vn_obj.get_instance_ip_back_refs() or []
        for inst_ip in inst_ip_ref:
            connections.vnc_lib.instance_ip_delete(id=inst_ip['uuid']) 
        try:
           connections.vnc_lib.virtual_network_delete(id=vn_id)
        except NoIdError,TypeError:
           pass
        except RefsExistError:
           print "ERROR: delete failed..RefExists for VN:",vn_id
           traceback.print_exc(file=sys.stdout)
           handleRefsExistError()

    def delete_vns(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

        router_obj   = RouterConfig(None)
        pr_names     = router_obj.retrieve_existing_pr(tcount=1,conn_obj_list=admin_conn_obj_list)
        pr_obj_info  = {}
        for router_name in pr_names:
            kw = {}
            kw['router_name'] = router_name
            pr_obj = self.retrieve_pr_obj(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kw])
            if pr_obj:
               pr_obj_info[router_name] = pr_obj

        tenant_list_t = []
        for tenant in tenant_list:
          if tenant['fq_name'] == ['default-domain','admin']:
             continue
          else:
            tenant_list_t.append(tenant)

        if len(tenant_list_t) == 0:
           return
        kwargs_tenant = {}
        kwargs_tenant['tenant_list'] = tenant_list_t
        for i in xrange(5):
          if i != 0 :
             time.sleep(60)
          vn_list = self.list_vn(conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs_tenant])
          if not vn_list:
             return True

          kwargs_list = []
          for vn in vn_list:
              tenant_fq_name,vn_id,vn_fq_name = vn
              if tenant_fq_name == ['default-domain','admin']:
                 continue
              kwargs = {}
              kwargs['vn_id']       = vn_id
              kwargs['vn_fq_name']  = vn_fq_name
              kwargs['pr_obj_info'] = pr_obj_info
              kwargs_list.append(kwargs) 
          if len(kwargs_list) == 0:
             return

          self.delete_vn(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def get_subnets(self,connections, uuid):
        quantum_h = connections.quantum_h
        return quantum_h.get_subnets_of_vn(uuid)

    def verify(self, uuid, subnets=[]):
        if not subnets:
            subnets = self.get_subnets(uuid)
        vn_fixture = self.get_fixture(uuid=uuid, subnets=subnets)
        assert vn_fixture.verify_on_setup()

    def get_fixture(self,connections, vn_name,uuid, subnets=[]):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            fixture = VNFixture(connections=connections,
                                     uuid=uuid,vn_name=vn_name,subnets=subnets)
        return fixture

def filter_vms_in_vn(vms,vn_names):

    vm_list = []
    for vm in vms:
        vm_iface_names = vm.networks.keys()
        if set(vm_iface_names).intersection(set(vn_names)):
           vm_list.append((vm,list(set(vm_iface_names).intersection(set(vn_names)))[0]))
    return vm_list

class VM(Base):

    @wrapper
    def retrieve_vm_info(self,*arg,**kwarg):
      try:  
        tenant_list      = kwarg['tenant_list']
        tenant_conf      = kwarg['tenant_conf']
        global_conf      = kwarg['global_conf']
        connections = kwarg['connection_obj'].connections
        tenant_info  = {}
        fips         = connections.vnc_lib.floating_ips_list()['floating-ips']
        fip_info     = {}
        fip_obj_info = {}
        # TO_FIX: tenant filter is missing
        for fip in fips:
            domain,t_name,vn_name,poll_name,fip_id=fip['fq_name']
            try:
               fip_obj = connections.vnc_lib.floating_ip_read(id=fip_id)
            except NoIdError:
               continue
            fip_obj_info[fip_id] = fip_obj

        vmi_obj_info = {}
        for fip_id,fip_obj in fip_obj_info.iteritems():
            try:
               iface_id  = fip_obj.virtual_machine_interface_refs[0]['uuid']
            except:
               print "SEEN EXCEPTION",traceback.print_exc(sys.stdout)
               continue ## TO_FIX
            iface_obj = connections.vnc_lib.virtual_machine_interface_read(id=iface_id)
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
    
        virtual_ips = connections.vnc_lib.virtual_ips_list()['virtual-ips']
        si_instances = connections.vnc_lib.service_instances_list()['service-instances']
        for tenant in tenant_list:
           if tenant['fq_name'] == ['default-domain','admin']:
             continue
           tenant_id = tenant['uuid']
           tenant_fq_name = tenant['fq_name']
           vms_all   = connections.orch.get_vm_list(project_id=tenant_id) or []
           net_list  = connections.vnc_lib.virtual_networks_list(parent_id=tenant_id)['virtual-networks']
           vmis_t    = connections.vnc_lib.virtual_machine_interfaces_list(parent_id=tenant_id)['virtual-machine-interfaces']
           vmis_filtered = []
           for vmi in vmis_t:
              if vmi_obj_info.has_key(vmi['uuid']):
                 vmi_obj = vmi_obj_info[vmi['uuid']]
              else:
                 vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
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
               if [dom,t_name] != tenant_fq_name:
                  continue
               vip_id  = virtual_ip['uuid']
               vip_obj = connections.vnc_lib.virtual_ip_read(id=vip_id)
               vm_interfaces = vip_obj.get_virtual_machine_interface_refs()
               vip_prop      = vip_obj.virtual_ip_properties
               vip_addr      = vip_prop.get_address()
               protocol_port = vip_prop.protocol_port
               for vmi in vm_interfaces:
                   vmi_id    = vmi['uuid']
                   if vmi_obj_info.has_key(vmi['uuid']):
                      vmi_obj = vmi_obj_info[vmi['uuid']]
                   else:
                      vmi_obj   = connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
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
                      fip_obj  = connections.vnc_lib.floating_ip_read(id=fip_id)
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
                      vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                      vmi_obj_info[vmi['uuid']] = vmi_obj
                   dom,t_name,vmi_vn_name = vmi_obj.get_virtual_network_refs()[0]['to']
                   if vmi_vn_name == vn_name:
                      inst_ip_id    = vmi_obj.get_instance_ip_back_refs()[0]['uuid']
                      inst_ip       = connections.vnc_lib.instance_ip_read(id=inst_ip_id)
                      mac_obj       = vmi_obj.get_virtual_machine_interface_mac_addresses()
                      data_mac_addr = mac_obj.get_mac_address()[0]
                      mac_indx      = physical_server_mac_list.index(data_mac_addr)
                      phy_ip_addr   = physical_server_ip_list[mac_indx]
                      li_ref   = vmi_obj.get_logical_interface_back_refs()[0]
                      li_obj   = connections.vnc_lib.logical_interface_read(id=li_ref['uuid'])
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
                       if addr.has_key(mgmt_vn_name):
                          vm_info['ip_addr,mgmt'] = addr[mgmt_vn_name] [0]['addr']
                       else:
                          vm_info['ip_addr,mgmt'] = addr['svc-vn-mgmt'][0]['addr']
                       vm_info['ip_addr,data'] = addr[vn_name][0]['addr']
                       data_mac_addr           = addr[vn_name][0]['OS-EXT-IPS-MAC:mac_addr']
                       vm_info['ip_addr,fip']  = fip_info.get(data_mac_addr,None)
                       vm_info['vlan']   = None
                       vm_info['compute_host_name'] = vm._info['OS-EXT-SRV-ATTR:hypervisor_hostname']
                       vm_info['is_bms'] = False
                       vm_info_list.append(vm_info) 
               vn_name = vn_name.split(".")[-1]
               vn_group_info[vn_name] = vm_info_list
           tenant_info[":".join(tenant_fq_name)] = vn_group_info
        return tenant_info
      except:
        traceback.print_exc(file=sys.stdout)

    @wrapper
    def list_vmis(self,*arg,**kwarg):
        tenant_list    = kwarg['tenant_list']
        tenant_list_t  = map(lambda x:x['fq_name'],tenant_list)
        #lr_back_ref_check = kwarg.get('lr_back_ref_check',False)
        #non_vm_ref_check  = kwarg.get('non_vm_ref_check',False)
        connections  = kwarg['connection_obj'].connections
        vmis_filtered = []
        vmis_list     = connections.vnc_lib.virtual_machine_interfaces_list()['virtual-machine-interfaces'] or []
        for vmi in vmis_list:
            dom,t_name,name = vmi['fq_name']
            if [dom,t_name] not in tenant_list_t:
               continue
            try:
              vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
            except NoIdError:
              pass
            vm_ref = vmi_obj.get_virtual_machine_refs()
            vmis_filtered.append((vmi,vm_ref))
            #if non_vm_ref_check:
            #   vm_ref = vmi_obj.get_virtual_machine_refs() 
            #   if vm_ref is None:
            #      vmis_filtered.append((vmi,None))
            #elif lr_back_ref_check:
            #   li_ref  = vmi_obj.get_logical_interface_back_refs()
            #   if li_ref is not None:
            #      vmis_filtered.append((vmi,li_ref))
            #else:
            #   vmis_filtered.append((vmi,None))
        return vmis_filtered

    @wrapper
    def list_vms(self,*arg,**kwarg):
        tenant_list = kwarg['tenant_list']
        vn_list          = kwarg.get('vn_list',[])
        connections = kwarg['connection_obj'].connections
        if len(tenant_list) == 0:
           return
        vms_list = []
        for tenant in tenant_list:
          if tenant['fq_name'] == ['default-domain','admin']:
             continue
          tenant_id = tenant['uuid']
          vms_all = connections.orch.get_vm_list(project_id=tenant_id) or []
          if len(vn_list):
             vms_filtered = filter_vms_in_vn(vms_all,vn_list)
          else:
             vms_filtered = [(vm,"") for vm in vms_all]
          for vm_obj,vn_name in vms_filtered:
            vm = {}
            vm['tenant']      = tenant
            vm['vn_name']     = vn_name
            vm['vm_name']     = vm_obj.name
            vm['id']          = vm_obj.id
            vm['ip']          = vm_obj.addresses
            vm['networks']    = vm_obj.networks
            vms_list.append(vm)
        return vms_list

    def create(self,connections,name, data_vn_obj,mgmt_vn_obj,additional_vn_obj_list,vn_id_dict,subnet_id_dict,mgmt_network_first,image='ubuntu',userdata=None,flavor="m1.small",zone=None):
        fixture = VMFixture(connections=connections, vm_name=name, image_name=image,userdata=userdata,zone=zone,project_name=connections.project_name)
        fixture.flavor = flavor
        if subnet_id_dict['mgmt'] :
           mgmt_vn_id     = vn_id_dict['mgmt']
           mgmt_subnet_id = subnet_id_dict['mgmt']
           data_vn_id     = vn_id_dict['data']
           data_subnet_id = subnet_id_dict['data']
           # subnet_id can be a list of subnets
           fixture.quantum_h = connections.quantum_h
           mgmt_port = fixture.quantum_h.create_port(mgmt_vn_id,mgmt_subnet_id,fixed_ips=[])
           data_port = fixture.quantum_h.create_port(data_vn_id,data_subnet_id,fixed_ips=[])
           if mgmt_network_first:
              fixture.port_ids = [mgmt_port['id'],data_port['id']]
           else:
              fixture.port_ids = [data_port['id'],mgmt_port['id']]
        else:
           additional_vn_ids_list = vn_id_dict['additional_vn_id_list']
           vn_obj_list = []
           if mgmt_network_first:
              vn_ids = [vn_id_dict['mgmt'],vn_id_dict['data']]
              vn_obj_list.append(mgmt_vn_obj)
              vn_obj_list.append(data_vn_obj)
           else:
              vn_ids = [vn_id_dict['data'],vn_id_dict['mgmt']]
              vn_obj_list.append(data_vn_obj)
              vn_obj_list.append(mgmt_vn_obj)
           vn_ids.extend(additional_vn_ids_list)
           vn_obj_list.extend(additional_vn_obj_list)
           fixture.vn_ids  = vn_ids
           fixture.vn_objs = vn_obj_list
        fixture.setUp()
        time.sleep(60)
        #fixture.wait_till_vm_is_up()
        return fixture.get_uuid()

    def check_if_vm_already_exists(self,existing_vms,conf):
        vm_name        = conf['vm,name']
        tenant         = conf['tenant']
        tenant_fq_name = tenant['fq_name']
        data_vn_name = conf['data_vn_name']
        mgmt_vn_name = conf['mgmt_vn_name']
        for vm in existing_vms:
            if vm['tenant']['fq_name'] != tenant_fq_name or vm['vm_name'] != vm_name:
               continue
            if vm['networks'].has_key(data_vn_name) and vm['networks'].has_key(mgmt_vn_name):
               return vm
        return False

    @wrapper
    def create_vm(self,*arg,**kwarg):
      try:
        global_conf  = kwarg.get('global_conf')
        tenant_conf  = kwarg.get('tenant_conf')
        tenant_indx  = kwarg.get('tenant_indx')
        vm_name      = kwarg['vm,name']
        data_vn_name = kwarg['data_vn_name']
        mgmt_vn_name = kwarg['mgmt_vn_name']
        data_subnet_id = kwarg.get('data,subnet_id',None)
        mgmt_subnet_id = kwarg.get('mgmt,subnet_id',None)
        zone               = kwarg.get('zone_name',None)
        mgmt_network_first = kwarg.get('mgmt_network_first',False)
        additional_vn_name_list = kwarg.get('additional_vn_name_list',[])
        attach_port_mirror = kwarg.get('attach_port_mirror')
        port_mirror_conf   = kwarg.get('port_mirror_conf',{})
        update_properties  = kwarg.get('update_properties')
        vm_id              = kwarg.get('vm_id',None)
        fat_flow       = kwarg.get('fat_flow')
        disable_policy = kwarg.get('disable_policy')
        flavor         = kwarg['flavor']
        tenant         = kwarg['tenant']
        tenant_fq_name = tenant['fq_name']
        tenant_uuid       = tenant['uuid']
        admin_tenant_uuid = kwarg['admin_tenant_uuid']
        image_name   = kwarg['image_name']
        userdata     = kwarg.get('userdata',None)
        connections = kwarg['connection_obj'].connections
        domain_name,tenant_name = tenant_fq_name

        if update_properties and vm_id:
           vm_obj = connections.vnc_lib.virtual_machine_read(id=vm_id)
        else:
           vm_obj = None
        if not vm_obj:
           quantum_h    = connections.quantum_h
           data_vn_obj  = quantum_h.get_vn_obj_if_present(data_vn_name,tenant_uuid)
           mgmt_vn_obj  = quantum_h.get_vn_obj_if_present(mgmt_vn_name,admin_tenant_uuid) 
           additional_vn_id_list  = []
           additional_vn_obj_list = []

           print "additional_vn_name_list",additional_vn_name_list
           for additional_vn_name in additional_vn_name_list:
              additional_vn_obj    = quantum_h.get_vn_obj_if_present(additional_vn_name,tenant_uuid)
              additional_vn_obj_list.append(additional_vn_obj)
              additional_vn_id_list.append(additional_vn_obj['network']['id'])
 
           vn_id_dict = {}
           vn_id_dict['mgmt'] = mgmt_vn_obj['network']['id']
           vn_id_dict['data'] = data_vn_obj['network']['id']
           vn_id_dict['additional_vn_id_list'] = additional_vn_id_list
           
           subnet_id_dict = {}
           subnet_id_dict['mgmt'] = mgmt_subnet_id
           subnet_id_dict['data'] = data_subnet_id

           try:
             vm_id = self.create(connections,vm_name,data_vn_obj,mgmt_vn_obj,additional_vn_obj_list,vn_id_dict,subnet_id_dict,mgmt_network_first,image_name,userdata,flavor,zone)
           except TypeError,ClientException:
             return 

        if update_properties and disable_policy is None:
           disable_policy = False

        if update_properties and attach_port_mirror is None:
           attach_port_mirror = False
        if update_properties and fat_flow is None:
           fat_flow = []

        vmi_obj_filtered = []

        if attach_port_mirror in [True,False] or fat_flow is not None or disable_policy is not None:
           time.sleep(60)
           #self.fixture.wait_till_vm_is_up()
           if vm_obj is None:
              vm_obj = connections.vnc_lib.virtual_machine_read(id=vm_id)
        else:
           return True

        if attach_port_mirror in [True,False] or fat_flow is not None or disable_policy is not None:
           vmi_refs = vm_obj.get_virtual_machine_interface_back_refs() or [] ## TO_FIX
           for vmi_ref in vmi_refs:       
               vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi_ref['uuid'])
               dom,t_name,v_name = vmi_obj.virtual_network_refs[0]['to']
               if t_name != 'admin':
                  vmi_obj_filtered.append(vmi_obj)
        
        if attach_port_mirror is not None:
           mirror_direction = port_mirror_conf['direction']
           analyzer_name    = port_mirror_conf['analyzer_name']
           analyzer_ip      = port_mirror_conf['analyzer_ip']
           analyzer_port    = port_mirror_conf['analyzer_port']
           ri_name = tenant_fq_name + [data_vn_name,data_vn_name]
           ri_name = ":".join(ri_name)
           for vmi_obj in vmi_obj_filtered:
               iface_prop = vmi_obj.get_virtual_machine_interface_properties() or \
                                     VirtualMachineInterfacePropertiesType()
               iface_mirror_type =InterfaceMirrorType()
               if attach_port_mirror:
                  iface_mirror_type.set_traffic_direction(mirror_direction)
                  mirror_action_type=MirrorActionType()
                  mirror_action_type.set_analyzer_name(analyzer_name)
                  mirror_action_type.set_analyzer_ip_address(analyzer_ip)
                  mirror_action_type.set_routing_instance(ri_name)
                  mirror_action_type.set_udp_port(int(analyzer_port))
                  iface_mirror_type.set_mirror_to(mirror_action_type)
                  iface_prop.set_interface_mirror(iface_mirror_type)
               else:
                  iface_prop.set_interface_mirror(iface_mirror_type)
               vmi_obj.set_virtual_machine_interface_properties(iface_prop)
               connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

        if fat_flow is not None:
           proto_list = []
           for fw in fat_flow:
              proto = fw['protocol']
              port  = fw['port']
              proto_list.append(ProtocolType(proto,port))
           ff = FatFlowProtocols(proto_list)
           for vmi_obj in vmi_obj_filtered:
               vmi_obj.set_virtual_machine_interface_fat_flow_protocols(ff)
               connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

        if disable_policy is not None:
           for vmi_obj in vmi_obj_filtered:
               vmi_obj.set_virtual_machine_interface_disable_policy(disable_policy)
               connections.vnc_lib.virtual_machine_interface_update(vmi_obj)
        return True
      except:
         traceback.print_exc(file=sys.stdout)
         pdb.set_trace()

    @wrapper
    def list_subnets(self,*arg,**kwarg):
        tenant_list      = kwarg['tenant_list']
        vn_list          = kwarg.get('vn_list',[])
        connections = kwarg['connection_obj'].connections
        if len(tenant_list) == 0:
           return
        subnet_dict = {}
        
        for tenant in tenant_list:
            tenant_id  = tenant['uuid']
            ipams_list = connections.vnc_lib.network_ipams_list(parent_id=tenant_id)['network-ipams'] or []
            for ipam in ipams_list:
                ipam_obj = connections.vnc_lib.network_ipam_read(id=ipam['uuid'])
                net_ref  = ipam_obj.get_virtual_network_back_refs() or []
                for net in net_ref:
                    net_fq_name     = net['to']
                    net_fq_name_str = ":".join(net_fq_name)
                    subnets         = net['attr']['ipam_subnets']                 
                    subnets_list = []
                    for subnet in subnets:
                        subnet_name = subnet['subnet_name']
                        subnet_uuid = subnet['subnet_uuid']
                        subnets_list.append((subnet_name,subnet_uuid))
                    subnet_dict[net_fq_name_str] = subnets_list
        return subnet_dict

    @timeit
    def create_vms(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties,dpdk,is_heat):
        kwargs = {}
        tenant_list_t = tenant_list[:]
        proj = ProjectConfig(None)
        admin_tenant = proj.retrieve_admin_tenant_info(admin_conn_obj_list)
        tenant_list_t.append(admin_tenant)
        print "tenant_list:",tenant_list_t
        kwargs['tenant_list'] = tenant_list_t
        subnet_dict = self.list_subnets(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        print "subnet_dict:",subnet_dict
        kwargs_list         = []   
        bgp_vm_kwargs_list  = []   
        mgmt_vn_name     = global_conf['mgmt,vn_name']
        port_mirror_conf = tenant_conf['port_mirror_conf']
        vm_obj = VM(None)
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        existing_vms = vm_obj.list_vms(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        
        for tenant in tenant_list:
            tenant_fq_name = tenant['fq_name']
            if tenant_fq_name == [u'default-domain', u'admin']:
               admin_tenant_uuid = tenant['uuid']
               break 

        for tenant in tenant_list :
            tenant_fq_name = tenant['fq_name']
            tenant_uuid    = tenant['uuid']
            if tenant_fq_name == [u'default-domain', u'admin']:
               continue
            tenant_index = get_tenant_index(tenant_conf,tenant_fq_name)
            vm_index   = 0  
            for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
              vn_index = 0 
              vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
              vn_name_pattern      = vn_info['vn,name,pattern']
              if re.search('Private_SC_Auto_Left_VN|Private_SC_Auto_Right_VN',vn_name_pattern):
                 continue
              elif re.search('Private_SC_Right_VN|Private_SC_Left_VN',vn_name_pattern):
                 vn_count,trans_si_count = service_instance_vn_count(global_conf,tenant_conf)
              else:
                 vn_count     = vn_info['count']
              for vn_indx  in xrange(vn_count):
                 vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,vn_name_pattern,vn_indx)
                 #if not vn_info.has_key('vm,count') :
                 #   continue
                 vm_count        = vn_info.get('vm,count',None)
                 if vm_count is not None:
                    vm_name_pattern = vn_info['vm,name_pattern']
                    image           = vn_info['vm,glance_image']
                    additional_vn_list  = vn_info['vm,additional_vn_list']
                    additional_vn_name_list = []
                    for additional_vn in additional_vn_list:
                        additional_vn_name  = additional_vn['name']
                        additional_vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,additional_vn_name,vn_indx)
                        additional_vn_name_list.append(additional_vn_name)
                    if dpdk:
                       flavor       = global_conf['dpdk_config'][0]['flavor']
                       zone_name    = global_conf['dpdk_config'][0]['zone_name']
                    else:
                       flavor       = vn_info.get('vm,flavor',None)
                       zone_name    = vn_info.get('zone_name',None)
                       if zone_name is None:
                          zone_name = global_conf['non_dpdk_config'][0]['zone_name']
                       if flavor is None:
                          flavor    = global_conf['non_dpdk_config'][0]['flavor']
                    vn_fq_name   = tenant_fq_name + [vn_name]
                    data_subnets = subnet_dict[":".join(vn_fq_name)]
                    mgmt_subnets = subnet_dict[":".join(['default-domain','admin',mgmt_vn_name])]
                    data_subnets_dict = dict(data_subnets)
                    v4_subnets=filter(lambda x:re.search('ipv4',x),dict(data_subnets))
                    v6_subnets=filter(lambda x:re.search('ipv6',x),dict(data_subnets))
                    if len(v4_subnets) != 0 :
                       subnet_list = v4_subnets
                    else:
                       subnet_list = v6_subnets
                    if len(v6_subnets):
                       ipv6_present = True
                    else:
                       ipv6_present = False
                    for subnet in subnet_list:
                      subnet_id_list = []
                      subnet_id_list.append(data_subnets_dict[subnet])
                      if re.search('ipv4',subnet) and ipv6_present:
                         subnet_m = re.sub('ipv4','ipv6',subnet)
                         subnet_id_list.append(data_subnets_dict[subnet_m])
                      for vm_indx in xrange(vm_count):
                        vm_name              = re.sub('QQQ',str(vm_index),vm_name_pattern)
                        conf                 = {}
                        conf['tenant_conf']  = tenant_conf
                        conf['global_conf']  = global_conf
                        conf['tenant_indx']  = tenant_index
                        conf['tenant']             = tenant
                        conf['admin_tenant_uuid']  = admin_tenant['uuid']
                        conf['vm,name']        = vm_name
                        conf['additional_vn_name_list'] = additional_vn_name_list
                        conf['data,subnet_id'] = subnet_id_list
                        conf['mgmt,subnet_id'] = mgmt_subnets[0][1]
                        conf['data_vn_name']   = vn_name
                        conf['mgmt_vn_name']   = mgmt_vn_name
                        conf['mgmt_network_first'] = vn_info.get('vm,mgmt_network_first',False)
                        conf['image_name']   = image
                        conf['flavor']       = flavor
                        conf['zone_name']    = zone_name
                        conf['attach_port_mirror'] = vn_info['vm,attach_port_mirror']
                        conf['port_mirror_conf']   = port_mirror_conf
                        conf['fat_flow']           = vn_info['vm,fat_flow']
                        conf['disable_policy']     = vn_info['vm,disable_policy']
                        conf['update_properties'] = update_properties
                        vm_index += 1
                        ret = self.check_if_vm_already_exists(existing_vms,conf)
                        if ret and not update_properties:
                           print "VM: %s already existing..skipping create CONF.."%vm_name
                        else:
                           if ret:
                              conf['vm_id'] = ret['id']
                           kwargs_list.append(conf)
                 bgp_vm_count        = vn_info.get('bgp_vm,count',None)
                 if bgp_vm_count is not None:
                    bgp_vm_name_pattern = vn_info['bgp_vm,name_pattern']
                    image               = vn_info['bgp_vm,glance_image']
                    bgp_user_data       = vn_info['bgp_vm,userdata']
                    additional_vn_list  = vn_info['bgp_vm,additional_vn_list']
                    if dpdk:
                       flavor       = global_conf['dpdk_config'][0]['flavor']
                       zone_name    = global_conf['dpdk_config'][0]['zone_name']
                    else:
                       flavor       = vn_info.get('bgp_vm,flavor',None)
                       zone_name    = vn_info.get('bgp_vm,zone_name',None)
                       if zone_name is None:
                          zone_name = global_conf['non_dpdk_config'][0]['zone_name']
                       if flavor is None:
                          flavor    = global_conf['non_dpdk_config'][0]['flavor']
                    additional_vn_name_list = []
                    for additional_vn in additional_vn_list:
                        additional_vn_name  = additional_vn['name']
                        additional_vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_index,additional_vn_name,vn_indx)
                        additional_vn_name_list.append(additional_vn_name)
                    for vm_indx in xrange(bgp_vm_count):
                        vm_name              = re.sub('QQQ',str(vm_index),bgp_vm_name_pattern)
                        conf                 = {}
                        conf['admin_tenant_uuid']  = admin_tenant_uuid
                        conf['tenant_conf']  = tenant_conf
                        conf['global_conf']  = global_conf
                        conf['tenant_indx']  = tenant_index
                        conf['tenant']       = tenant
                        conf['vm,name']      = vm_name
                        conf['data_vn_name'] = vn_name
                        conf['mgmt_vn_name'] = mgmt_vn_name
                        conf['additional_vn_name_list'] = additional_vn_name_list
                        conf['mgmt_network_first'] = vn_info.get('bgp_vm,mgmt_network_first',False)
                        conf['flavor']       = flavor
                        conf['image_name']   = image
                        conf['userdata']     = bgp_user_data
                        conf['zone_name']    = zone_name
                        vm_index += 1
                        bgp_vm_kwargs_list.append(conf)
                 vn_index += 1

        if is_heat:
           return bgp_vm_kwargs_list,kwargs_list
        if len(bgp_vm_kwargs_list) :
           self.create_vm(count=1,conn_obj_list=proj_conn_obj_list,kwargs_list=bgp_vm_kwargs_list)
        if len(kwargs_list):
           self.create_vm(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def get_vm_creds(self):
        return (self.fixture.get_vm_username(),
                self.fixture.get_vm_password())

    def delete(self,connections, uuid,vm_obj, vn_ids=[],verify=False):
        connections.inputs.fixture_cleanup = 'force'
        vm_fixture = self.get_fixture(connections,uuid=uuid, vn_ids=vn_ids)
        vm_fixture.vm_objs = [vm_obj]
        vm_fixture.delete(verify=verify)

    @wrapper
    def delete_vmi(self,*arg,**kwarg):
        vmi_id = kwarg['vmi_id']
        connections = kwarg['connection_obj'].connections
        try:
           vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
        except NoIdError,TypeError:
           ## TypeError: ('__init__() takes exactly 2 arguments (1 given)', <class 'cfgm_common.exceptions.NoIdError'>, ()) TO_FIX
           print "VMI: %s missing..skipping delete"%vmi_id
           return
        inst_ips = vmi_obj.get_instance_ip_back_refs() or []
        for inst_ip in inst_ips:
            inst_ip_id = inst_ip['uuid']
            try:
              inst_ip_obj = connections.vnc_lib.instance_ip_read(id=inst_ip_id)
              inst_ip_obj.del_virtual_machine_interface(vmi_obj)
              connections.vnc_lib.instance_ip_update(inst_ip_obj)
              connections.vnc_lib.instance_ip_delete(id=inst_ip_id)
            except NoIdError,TypeError:
              print "INFO: deleting instance ip failed NoIdError:",inst_ip_id,vmi_id
              continue
            except RefsExistError:
               print "ERROR: delete failed..RefExists for instance_ip:",inst_ip_id,vmi_id
               traceback.print_exc(file=sys.stdout)
               handleRefsExistError()
        li_refs = vmi_obj.get_logical_interface_back_refs() or []
        for li in li_refs:
            try:
              li_obj = connections.vnc_lib.logical_interface_read(id=li['uuid'])
            except NoIdError,TypeError:
              print "INFO: NoIdError for LI update",li['uuid']
              li_obj = None
            if li_obj:
              li_obj.del_virtual_machine_interface(vmi_obj)
              connections.vnc_lib.logical_interface_update(li_obj)
        lr_refs = vmi_obj.get_logical_router_back_refs() or []
        for lr in lr_refs:
            try:
              lr_obj = connections.vnc_lib.logical_router_read(id=lr['uuid'])
            except NoIdError,TypeError:
              lr_obj = None
              print "INFO: LR update failed.. NoIdError",lr['uuid']
            if lr_obj:
              lr_obj.del_virtual_machine_interface(vmi_obj)
              connections.vnc_lib.logical_router_update(lr_obj)
        try:
           vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
        except NoIdError,TypeError:
           ## TypeError: ('__init__() takes exactly 2 arguments (1 given)', <class 'cfgm_common.exceptions.NoIdError'>, ()) TO_FIX
           print "VMI: %s missing..skipping delete"%vmi_id
           return
        li_refs  = vmi_obj.get_logical_interface_back_refs() or []
        inst_ips = vmi_obj.get_instance_ip_back_refs() or []
        lr_refs  = vmi_obj.get_logical_router_back_refs() or []
        if inst_ips or li_refs or lr_refs:
           print "ERROR: in deleting VMI, there is some hanging reference"
           print "inst_ips:",inst_ips
           print "li_refs:",li_refs
           print "lr_refs:",lr_refs
           #handleRefsExistError()
        try:
          connections.vnc_lib.virtual_machine_interface_delete(id=vmi_id)
        except NoIdError,TypeError:
          pass
        except RefsExistError:
          print "ERROR: delete failed..RefExists for VMI:",vmi_id
          traceback.print_exc(file=sys.stdout)
          handleRefsExistError()

    @wrapper
    def delete_vm(self,*arg,**kwarg):
        tenant   = kwarg['tenant']
        tenant_fq_name = tenant['fq_name']
        vm_id       = kwarg['vm_id']
        
        connections = kwarg['connection_obj'].connections
        domain_name,tenant_name = tenant_fq_name
        print "DEBUG: deleting VM : %s"%vm_id
        try:
           vm_obj = connections.vnc_lib.virtual_machine_read(id=vm_id)
        except NoIdError:
           print "DEBUG: VM:%s not found...skipping delete"%vm_id
           return
        si_refs = vm_obj.get_service_instance_refs() or []
        if si_refs:
           si_vm = True
        else:
           si_vm = False
        for si_ref in si_refs:
            try:
              si_obj = connections.vnc_lib.service_instance_read(id=si_ref['uuid'])
              vm_obj.del_service_instance(si_obj)
              connections.vnc_lib.virtual_machine_update(vm_obj)
            except NoIdError:
              pass
        if si_vm:
           return
        try:
          vm_obj=connections.orch.get_vm_by_id(vm_obj.uuid)
          self.delete(connections,vm_id,vm_obj)
        except RefsExistError:
          print "ERROR: delete failed..RefExists for VM:",vm_id
          traceback.print_exc(file=sys.stdout)
          handleRefsExistError()
        except Exception:
          print "Exception seen in deleting VM..."
          print traceback.print_exc(sys.stdout)
          pass # retry loop in delete_vms will take care of this.

    def delete_vmis(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

        tenant_list_t = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            else:
               tenant_list_t.append(tenant)

        kwargs_tenant = {}
        kwargs_tenant['tenant_list'] = tenant_list_t
        for i in xrange(10):
            vmis_list = self.list_vmis(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs_tenant])
            if not vmis_list:
               return
               
            kwargs_list = []
            for vmi,ref in vmis_list:
                kwargs = {}
                kwargs['vmi_id'] = vmi['uuid']
                kwargs_list.append(kwargs)
            if len(kwargs_list) == 0:
               return
            self.delete_vmi(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def delete_vms(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        for i in xrange(10):
           if i != 0 :
              time.sleep(60) 
           print "iteration",i
           kwargs = {}
           kwargs['tenant_list'] = tenant_list
           
           ret = self.list_vms(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
           vms_list = []
           if ret:
              vms_list.extend(ret)
           if len(vms_list) == 0:
              return True 
           kwargs_list = []
           for vm in vms_list:
             kwargs = {}
             kwargs['tenant']  = vm['tenant']
             kwargs['vm_id']           = vm['id']
             kwargs_list.append(kwargs)

           if len(kwargs_list) == 0:
              return
           self.delete_vm(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def verify(self, uuid, vn_ids=[], username='ubuntu', password='ubuntu'):
        vm_fixture = self.get_fixture(uuid=uuid, vn_ids=vn_ids)
        vm_fixture.set_vm_creds(username, password)
        assert vm_fixture.verify_on_setup()

    def vm_ip(self, uuid, vn_name=None):
        orch_h = connections.get_orch_h()
        vm_obj = orch_h.get_vm_by_id(vm_id=uuid)
        return orch_h.get_vm_ip(vm_obj, vn_name)

    def vm_name(self, uuid):
        orch_h = connections.get_orch_h()
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

    def get_fixture(self,connections, uuid, vn_ids=[]):
        if not getattr(self, 'fixture', None):
            assert uuid, 'ID cannot be None'
            fixture = VMFixture(connections=connections,
                                     uuid=uuid, vn_ids=vn_ids)
        return fixture

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
    def create(self,connections, vn_id, name=None):
        fixture = FloatingIPFixture(connections=connections,
                                         pool_name=name, vn_id=vn_id)
        fixture.setUp()
        return fixture.get_uuid()

    @wrapper
    def create_fip_pool(self,*arg,**kwarg):
        vn_id         = kwarg['vn_id']
        fip_pool_name = kwarg['fip,pool,name']
        tenant_fq_name   = kwarg['tenant,fq_name']
        connections = kwarg['connection_obj'].connections
        self.create(connections,vn_id,fip_pool_name)
      
    @timeit
    def create_fip_pools(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        public_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_vn_group_index = vn_group_indx
            break
        if public_vn_group_index is None:
           return
        vn_info_dict = {}
        kwargs_list = []
        vn_obj = VN(None)
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if ret:
           vn_info_dict.update(ret)
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name = tenant['fq_name']
            tenant_indx            = get_tenant_index(tenant_conf,tenant_fq_name)
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
                kwargs['tenant,fq_name'] = tenant_fq_name
                kwargs['fip,pool,name']  = fip_pool_name_list[indx]
                vn_fq_name               = tenant_fq_name + [fip_gw_vn_names[indx]]
                kwargs['vn_id']          = vn_info_dict[":".join(vn_fq_name)]
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.create_fip_pool(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
 
    def delete(self,connections, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        fip_fixture.delete(verify=True)

    def delete_fips(self,connections,fips):
     
        for fip in fips:
            try:
              fip_obj = connections.vnc_lib.floating_ip_read(id=fip['uuid'])
            except NoIdError:
              continue
            vmis = fip_obj.get_virtual_machine_interface_refs() or []
            for vmi in vmis:
              try:
                vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
              except NoIdError:
                continue
              fip_obj.del_virtual_machine_interface(vmi_obj)
              connections.vnc_lib.floating_ip_update(fip_obj)
            try:
              connections.vnc_lib.floating_ip_delete(id=fip_obj.uuid)
            except RefsExistError:
               print "ERROR: delete failed..RefExists for FIP:",fip_obj.uuid
               traceback.print_exc(file=sys.stdout)
               handleRefsExistError()

    @wrapper
    def delete_fip_pool(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        tenant_fq_name   = kwarg['tenant,fq_name']
        try:
           admin_proj    = connections.vnc_lib.project_read(fq_name=['default-domain','admin'])
           project_obj   = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
        except NoIdError:
           return
        fips = project_obj.get_floating_ip_back_refs() or []
        self.delete_fips(connections,fips)
        fip_pools     = connections.vnc_lib.floating_ip_pools_list()['floating-ip-pools']
        for fip_pool in fip_pools: 
            fip_domain,fip_tenant_name,fip_vn_name,fip_pool_name = fip_pool[u'fq_name']  
            if [fip_domain,fip_tenant_name] != tenant_fq_name:
               continue
            try:
              pool_obj = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool[u'fq_name'])
            except NoIdError:
              continue
            fips = pool_obj.get_floating_ips() or []
            self.delete_fips(connections,fips)
            project_obj.del_floating_ip_pool(pool_obj)
            connections.vnc_lib.project_update(project_obj)
            admin_proj.del_floating_ip_pool(pool_obj)
            connections.vnc_lib.project_update(admin_proj)
            connections.vnc_lib.floating_ip_pool_delete(id=pool_obj.uuid)

    @timeit
    def delete_fip_pools(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties=False):
        if update_properties:
           return
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            kwargs      = {}
            kwargs['tenant,fq_name']   = tenant['fq_name']
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_fip_pool(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def associate_fip(self,*arg,**kwarg):
        fip_pool_tenant_fq_name = kwarg ['fip_pool_tenant_fq_name']
        tenant         = kwarg['tenant']
        tenant_fq_name = tenant['fq_name']
        fip_pool_name  = kwarg['fip_pool_name']
        vm_id          = kwarg['vm_id']
        vn_id          = kwarg['private_vn_id']
        fip_gw_vn_name = kwarg['fip_gw_vn_name']
        fip_gw_vn_id   = kwarg['fip_gw_vn_id']
        username       = "ubuntu"
        password       = "ubuntu"

        connections = kwarg['connection_obj'].connections

        domain_name,tenant_name = tenant_fq_name 
        connections.project_name = connections.inputs.project_name = tenant_name

        # delete default-fip-pool
        project_obj = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
        try:
           fip_pool_fq_name = tenant_fq_name + [fip_gw_vn_name,'floating-ip-pool']
           pool_obj = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool_fq_name)
           project_obj.del_floating_ip_pool(pool_obj)
           connections.vnc_lib.project_update(project_obj)
           self.delete(connections,pool_obj.uuid)
        except NoIdError:
           print "FIP pool:%s not found..skipping delete"%fip_pool_name
        # delete default-fip-pool

        fip_pool_fq_name = fip_pool_tenant_fq_name + [fip_gw_vn_name,fip_pool_name]
        fip_pool_obj = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_pool_fq_name)
        fip_pool_id  = fip_pool_obj.uuid
        fixture = self.get_fixture(connections=connections,uuid=fip_pool_id)
        fixture.fip_pool_obj = fip_pool_obj
        project_name = tenant_name
        return fixture.create_and_assoc_fip(fip_pool_vn_id=fip_gw_vn_id,vm_id=vm_id,project=project_obj,vn_id=vn_id)

    @timeit
    def associate_fips(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        vn_index_replace_str      = tenant_conf['vn,index,replace_str']
        public_fip_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):
          if re.search('Public_FIP',vn_group['vn,name,pattern']):
            public_fip_vn_group_index = vn_group_indx

        fip_shared = tenant_conf.get('fip,shared',False)

        if public_fip_vn_group_index is None and fip_shared is False:
           return
        if fip_shared:
           fip_shared_tenant_name  = tenant_conf['fip,shared,tenant_name'] 
           fip_gw_vn_name          = tenant_conf['fip,shared,fip_gw_vn_name']
           fip_pool_name           = tenant_conf['fip,shared,floating_ip_pool']
           fip_gw_vn_fq_name       = fip_shared_tenant_name.split(":") + [fip_gw_vn_name]
           fip_pool_tenant_fq_name = fip_shared_tenant_name.split(":")
         
        vn_info_dict = {}
        if fip_shared:
           tenant_list_l = tenant_list + [fip_pool_tenant_fq_name]
        else:
           tenant_list_l = tenant_list[:]
        kwargs = {}
        kwargs['tenant_list'] = tenant_list_l
        vn_obj = VN(None)
        ret    = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if ret:
           vn_info_dict.update(ret)
        if not fip_shared :
          fip_gw_vn_count          = tenant_conf['fip,gw_vn_count']
          fip_gw_vn_name_pattern   = tenant_conf['fip,gw_vn_name']
          fip_pool_name_pattern    = tenant_conf['fip,name']
        kwargs_list = []
        vm_obj = VM(None)
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name = tenant['fq_name']
            tenant_indx         = get_tenant_index(tenant_conf,tenant_fq_name)
            if not fip_shared :
               fip_gw_vn_name_list = [generate_vn_name(global_conf,tenant_conf,tenant_indx,fip_gw_vn_name_pattern,vn_indx) for vn_indx in xrange(fip_gw_vn_count)]
               fip_pool_name_list  = [generate_fip_pool_name(global_conf,tenant_conf,tenant_indx,pool_indx) for pool_indx in xrange(fip_gw_vn_count)]
               fip_gw_vn_name          = fip_gw_vn_name_list[0]
               fip_pool_name           = fip_pool_name_list[0]
               fip_gw_vn_fq_name       = tenant_fq_name + [fip_gw_vn_name]
               fip_pool_tenant_fq_name = tenant_fq_name[:]
            fip_gw_vn_id   = vn_info_dict[":".join(fip_gw_vn_fq_name)]

            for vn_info in tenant_conf['tenant,vn_group_list']:
                fip_associate_required = vn_info.get('attach_fip',None)
                if not fip_associate_required:
                   continue
                private_vn_count = vn_info['count']
                vn_name_pattern  = vn_info['vn,name,pattern']
                vn_names_list    = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(private_vn_count)]
                
                kwargs_t = {}
                kwargs_t['tenant_list'] = [tenant]
                kwargs_t['vn_list']     = vn_names_list
                vm_list = vm_obj.list_vms(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs_t])
                if not vm_list:
                   continue
                for vm in vm_list:
                    tenant         = vm['tenant']
                    vn_name        = vm['vn_name']
                    if vn_name == "":
                       private_vn_id = None
                    else:
                       vn_fq_name = tenant_fq_name + [vn_name]
                       private_vn_id = vn_info_dict[":".join(vn_fq_name)]
                    kwargs = {}
                    kwargs['tenant']           = tenant
                    kwargs['private_vn_id']    = private_vn_id
                    kwargs['vm_id']            = vm['id']
                    kwargs['fip_pool_tenant_fq_name'] = fip_pool_tenant_fq_name
                    kwargs['fip_pool_name']    = fip_pool_name
                    kwargs['fip_gw_vn_id']     = fip_gw_vn_id
                    kwargs['fip_gw_vn_name']   = fip_gw_vn_name
                    kwargs_list.append(kwargs)
        
        if len(kwargs_list) == 0:
           return
        self.associate_fip(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def disassociate_fip(self, uuid, fip_id):
        self.fixture = self.get_fixture(uuid=uuid)
        self.fixture.disassoc_and_delete_fip(fip_id)

    def get_fip_from_id(self, fip_id):
        quantum_h = connections.quantum_h
        return quantum_h.get_floatingip(fip_id)['floatingip']['floating_ip_address']

    def verify_fip(self, uuid, fip_id, vm_id, vn_ids, vm_connections):
        fip_fixture = self.get_fixture(uuid=uuid)
        fvn_fixture = VNFixture(connections=connections,
                                uuid=fip_fixture.get_vn_id())
        vm_fixture = VMFixture(connections=vm_connections, uuid=vm_id, vn_ids=vn_ids)
        assert fip_fixture.verify_fip(fip_id, vm_fixture, fvn_fixture)

    def verify_no_fip(self, uuid, fip_id, vm_id, fip=None):
        fip_fixture = self.get_fixture(uuid=uuid)
        fvn_fixture = VNFixture(connections=connections,
                                uuid=fip_fixture.get_vn_id())
        assert fip_fixture.verify_no_fip(fip_id, fvn_fixture, fip)

    def verify(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        assert fip_fixture.verify_on_setup()

    def get_associated_fips(self, uuid):
        fip_fixture = self.get_fixture(uuid=uuid)
        return fip_fixture.get_associated_fips()

    def get_fip_pool_id(self, fip_id):
        vnc = connections.get_vnc_lib_h().get_handle()
        return vnc.floating_ip_read(id=fip_id).parent_uuid

    def get_fixture(self,connections ,uuid):
         if not getattr(self, 'fixture', None):
             assert uuid, 'ID cannot be None'
             fixture = FloatingIPFixture(connections=connections, uuid=uuid)
         return fixture

class LogicalRouterConfig(Base):
    @wrapper
    def get_router_id(self,*arg,**kwarg):
        
        connection_obj   = kwarg.pop('connection_obj')
        connections = connection_obj.connections
        return_value = {}
        for tenant_fq_name,route_name_list in kwarg.iteritems():
            for router_name in route_name_list:
                router_fq_name = tenant_fq_name.split(":") + [router_name]
                try:
                  router_obj = connections.vnc_lib.logical_router_read(fq_name=router_fq_name)
                  return_value[router_name] = router_obj.uuid
                except NoIdError:
                  pass
        return return_value

    def create(self,connections, name, tenant_id,vn_ids=[], gw=None):
        quantum_h   = connections.quantum_h
        try:
          response     = quantum_h.get_router(name=name)
        except:
          response = None
        if response:
           print "router is already available..skipping create"
           return
        response    = quantum_h.create_router(name,tenant_id)
        print "Response:",response
        uuid   = response['id']
        if response.has_key('contrail:fq_name'):
           fqname = response['contrail:fq_name']
        else:
           fqname = response['fq_name']
        if gw:
            self.set_gw(connections,uuid, gw)
        for vn_id in vn_ids:
            self.attach_vn(connections,uuid, vn_id)
        return uuid
        lr = LogicalRouter(parent_obj=project_obj)
        lr.set_display_name(name)
        connections.vnc_lib.logical_router_create(lr)

    @wrapper
    def create_logical_router(self,*arg,**kwarg):
        tenant         = kwarg['tenant']
        tenant_uuid    = tenant['uuid']
        tenant_fq_name = tenant['fq_name']
        router_name    = kwarg['router_name']
        gw             = kwarg['gw_nw']
        connections = kwarg['connection_obj'].connections
        try:
          self.create(connections,router_name,tenant_uuid,gw=gw)
        except:
          traceback.print_exc(file=sys.stdout)

    @timeit
    def create_logical_routers(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        gw_vn_group_index = None
        fip_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
            break
          elif re.search('Public_FIP_VN',vn_group['vn,name,pattern']):
            fip_vn_group_index = vn_group_indx
        if gw_vn_group_index is None and fip_vn_group_index is not None:
           gw_vn_group_index = fip_vn_group_index

        if not gw_vn_group_index:
           return 

        router_count         = tenant_conf.get('routers,count',None)
        if router_count is None:
           return
        vn_index_replace_str = tenant_conf['vn,index,replace_str']

        kwargs_list  = []
        vn_info_dict = {}
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if ret:
           vn_info_dict.update(ret)
        for tenant in tenant_list:
           if tenant['fq_name'] == ['default-domain','admin']:
             continue
           tenant_fq_name   = tenant['fq_name']
           tenant_indx      = get_tenant_index(tenant_conf,tenant_fq_name)
           router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
           vn_info          = tenant_conf['tenant,vn_group_list'][gw_vn_group_index]
           vn_name_pattern  = vn_info['vn,name,pattern']
           gw_vn_name_list  = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(router_count)]

           for indx,router_name in enumerate(router_name_list):
               gw_vn_name            = gw_vn_name_list[indx]
               kwargs                = {}
               kwargs['tenant']      = tenant
               kwargs['router_name'] = router_name
               gw_vn_fq_name = tenant_fq_name + [gw_vn_name]
               kwargs['gw_nw']       = vn_info_dict[":".join(gw_vn_fq_name)]
               kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.create_logical_router(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    #@wrapper
    #def delete_logical_router(self,*arg,**kwarg):
    #    connections = kwarg['connection_obj'].connections
    #    #logger      = kwarg['connection_obj'].logger
    #    tenant   = kwarg['tenant']
    #    lrs = connections.vnc_lib.logical_routers_list()['logical-routers']
    #    for lr in lrs:
    #        lr_domain,lr_tenant_name,lr_name = lr[u'fq_name']
    #        if lr_tenant_name != unicode(tenant_name):
    #    
    #    if not gw_vn_group_index:
    #       return 
    #    router_count         = tenant_conf['routers,count']
    #    vn_index_replace_str = tenant_conf['vn,index,replace_str']

    #    kwargs_list  = []
    #    vn_info_dict = {}
    #    vn_obj = VN(None)
    #    ret = vn_obj.get_vn_ids(tenant_list=tenant_list,conn_obj_list=conn_obj_list)
    #    if ret:
    #       vn_info_dict.update(ret)
    #    for tenant_fq_name in tenant_list:
    #       tenant_indx = get_tenant_index(tenant_conf,tenant_fq_name)
    #       router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
    #       vn_info          = tenant_conf['tenant,vn_group_list'][gw_vn_group_index]
    #       vn_name_pattern  = vn_info['vn,name,pattern']
    #       gw_vn_name_list  = [generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name_pattern,vn_indx) for vn_indx in xrange(router_count)]

    #       for indx,router_name in enumerate(router_name_list):
    #           gw_vn_name            = gw_vn_name_list[indx]
    #           kwargs                = {}
    #           kwargs['tenant_fq_name'] = tenant_fq_name
    #           kwargs['router_name'] = router_name
    #           kwargs['gw_nw']       = vn_info_dict[u'default-domain:%s:%s'%(tenant_name,gw_vn_name)]
    #           kwargs_list.append(kwargs)
    #    if len(kwargs_list) == 0:
    #       return
    #    kwargs = {'kwargs_list': kwargs_list } if len(kwargs_list) > 1 else kwargs_list[0]
    #    self.create_logical_router(count=True,conn_obj_list=conn_obj_list,**kwargs)

    @wrapper
    def delete_logical_router(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger
        tenant           = kwarg['tenant']
        tenant_fq_name   = tenant['fq_name']
        lrs = connections.vnc_lib.logical_routers_list()['logical-routers']
        for lr in lrs:
            lr_domain,lr_tenant_name,lr_name = lr[u'fq_name']
            if [lr_domain,lr_tenant_name] != tenant_fq_name:
               continue
            router_obj = connections.vnc_lib.logical_router_read(fq_name=lr[u'fq_name'])
            uuid    = router_obj.uuid
            vn_ref  = router_obj.get_virtual_network_refs() or None
            vmi_ref = router_obj.get_virtual_machine_interface_refs() or None
            if vn_ref:
               for vn in vn_ref:
                   try:
                     vn_obj = connections.vnc_lib.virtual_machine_read(id=vn['uuid'])
                     router_obj.del_virtual_network(vn_obj)
                   except NoIdError:
                     pass
            if vmi_ref:
               for vmi in vmi_ref:
                   try:
                     vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                     router_obj.del_virtual_machine_interface(vmi_obj)
                   except NoIdError:
                     pass
            if vn_ref or vmi_ref:
               connections.vnc_lib.logical_router_update(router_obj)
            try:
              self.delete(connections,uuid)
            except:
              print "Exception seen in LR delete"

    def delete_logical_routers(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_logical_router(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def attach_vns_to_logical_router(self,*arg,**kwarg):
        tenant         = kwarg['tenant']
        tenant_fq_name = tenant['fq_name']
        router_id     = kwarg['router_id']
        net_ids       = kwarg['private_vns']
        connections = kwarg['connection_obj'].connections
        domain_name,tenant_name = tenant_fq_name
        connections.project_name = tenant_name
        connections.inputs.project_name = tenant_name
        quantum_h = connections.quantum_h
        for net_id in net_ids:
            subnet_id = quantum_h.get_vn_obj_from_id(net_id)['network']['subnets'][0]
            try:
              quantum_h.add_router_interface(router_id=router_id, subnet_id=subnet_id)
            except:
              pass # interface may be already added TO_FIX

    @timeit
    def attach_vns_to_logical_routers(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        gw_vn_group_index           = None
        fip_vn_group_index          = None
        snat_private_vn_group_index = None
        for vn_group_indx,vn_group in enumerate(tenant_conf['tenant,vn_group_list']):  
          if re.search('SNAT_GW',vn_group['vn,name,pattern']):
            gw_vn_group_index = vn_group_indx
          elif re.search('Private_SNAT',vn_group['vn,name,pattern']):
            snat_private_vn_group_index = vn_group_indx
          elif re.search('Public_FIP_VN',vn_group['vn,name,pattern']):
            fip_vn_group_index = vn_group_indx

        if gw_vn_group_index is None and fip_vn_group_index is not None:
           gw_vn_group_index = fip_vn_group_index 

        if not gw_vn_group_index:
           return 

        router_count         = tenant_conf.get('routers,count',None)
        if router_count is None:
           return

        vn_info_dict      = {}
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        if ret:
           vn_info_dict.update(ret)
        kwargs            = {}
        router_info_dict  = {}
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name   = tenant['fq_name']
            tenant_indx      = get_tenant_index(tenant_conf,tenant_fq_name)
            router_count     = tenant_conf['routers,count']
            router_name_list = [generate_router_name(global_conf,tenant_conf,tenant_indx,i) for i in xrange(router_count)]
            kwargs[":".join(tenant_fq_name)] = router_name_list
        
        router_info_dict = self.get_router_id(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])

        kwargs_list       = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name   = tenant['fq_name']
            tenant_indx      = get_tenant_index(tenant_conf,tenant_fq_name)
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
                kwargs['tenant']      = tenant
                kwargs['router_id']   = router_info_dict[router_name]
                private_vn_names      = vn_names_list[vn_index_offset:vn_index_offset+private_vn_per_routers]
                vn_index_offset      += private_vn_per_routers
                private_vn_ids = []
                for vn_name in private_vn_names:
                    vn_fq_name = tenant_fq_name + [vn_name]
                    private_vn_ids.append(vn_info_dict[":".join(vn_fq_name)])
                kwargs['private_vns'] = private_vn_ids
                kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        self.attach_vns_to_logical_router(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

    def set_gw(self,connections, uuid, gw):
        quantum_h = connections.quantum_h
        quantum_h.router_gateway_set(uuid, gw)

    def clear_gw(self, uuid):
        quantum_h = connections.quantum_h
        quantum_h.router_gateway_clear(uuid)

    def attach_vn(self,connections, uuid, vn_id):
        quantum_h = connections.quantum_h
        subnet_id = quantum_h.get_vn_obj_from_id(vn_id)['network']['subnets'][0]
        quantum_h.add_router_interface(router_id=uuid, subnet_id=subnet_id)

    def detach_vn(self, uuid, vn_id):
        quantum_h = connections.quantum_h
        subnet_id = quantum_h.get_vn_obj_from_id(vn_id)['network']['subnets'][0]
        quantum_h.delete_router_interface(router_id=uuid, subnet_id=subnet_id)

    def delete(self,connections, uuid):
        quantum_h = connections.quantum_h
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
            quantum_h = connections.quantum_h
            router_obj = quantum_h.show_router(router_id=uuid)
            self.fqname = router_obj['contrail:fq_name']
        return self.fqname


class LLS(Base):
    @wrapper
    def retrieve_existing_services(self,*args,**kwargs):
        connections = kwargs['connection_obj'].connections
        current_config=connections.vnc_lib.global_vrouter_config_read(
                                fq_name=['default-global-system-config',
                                         'default-global-vrouter-config'])
        current_linklocal=current_config.get_linklocal_services()
        current_entries = current_linklocal.linklocal_service_entry
        service_names = []
        for entry in current_entries:
            value = entry.linklocal_service_name,entry.linklocal_service_ip,entry.linklocal_service_port
            service_names.append(value)
        return service_names

    def create(self,connections,service_name,service_ip,service_port,fabric_dns_name,fabric_ip,fabric_port):

        linklocal_obj=LinklocalServiceEntryType(
                 linklocal_service_name=service_name,
                 linklocal_service_ip=service_ip,
                 linklocal_service_port=service_port,
                 ip_fabric_DNS_service_name=fabric_dns_name,
                 ip_fabric_service_ip=[fabric_ip],
                 ip_fabric_service_port=fabric_port)

        current_config=connections.vnc_lib.global_vrouter_config_read(
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
           #logger.warn("LLS entry:%s already found..skipping create"%service_name)
           return
        current_entries.append(linklocal_obj)
        linklocal_services_obj=LinklocalServicesTypes(current_entries)
        conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
        result=connections.vnc_lib.global_vrouter_config_update(conf_obj)

    @wrapper
    def create_link_local_service(self,*arg,**kwarg):
        services         = kwarg['services'] 
        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger

        #self.create(service_name,lls_ip,lls_port,lls_fab_dns,lls_fab_ip,lls_fab_port)
        for service in services:
            service_name = service['lls_name']
            lls_ip       = service['lls_ip']
            lls_port     = service['lls_port']
            lls_fab_ip   = service['lls_fab_ip']
            lls_fab_port = service['lls_fab_port']
            lls_fab_dns  = service['lls_fab_dns']
            self.create(connections,service_name,lls_ip,lls_port,None,lls_fab_ip,lls_fab_port)

    def create_link_local_services(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
        if update_properties:
           return
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
        self.create_link_local_service(tcount=1,conn_obj_list=[conn_obj_list[0]],kwargs_list=[kwarg])

    @wrapper
    def delete_link_local_service(self,*arg,**kwarg):
        connection_obj   = kwarg['connection_obj']
        connections = connection_obj.connections
        #logger      = connection_obj.logger
        lls_names        = kwarg['lls_name_list']
        for service_name in lls_names:
            current_config=connections.vnc_lib.global_vrouter_config_read(
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
               #logger.warn("LLS entry:%s not found...skipping delete"%service_name)
               return
            linklocal_services_obj=LinklocalServicesTypes(current_entries)
            conf_obj=GlobalVrouterConfig(linklocal_services=linklocal_services_obj)
            result=connections.vnc_lib.global_vrouter_config_update(conf_obj)
        return True

    def delete_link_local_services(self,conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf):

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
        self.delete_link_local_service(tcount=thread_count,conn_obj_list=[conn_obj_list[0]],kwargs_list=[kwargs])


class LbaasV2(Base):

    def create_lbaas(self,connections,vn_id,fip_vn_id,vm_ids):
        obj = LBaasV2Fixture(lb_name='LB-Test', connections=connections, network_id=vn_id,
                         fip_net_id=fip_vn_id, listener_name='Listener-Test', vip_port='80',
                         vip_protocol='HTTP', pool_name='Pool-Test', pool_port='80', pool_protocol='HTTP',
                         pool_algorithm='ROUND_ROBIN', members={'vms': vm_ids},
                         hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type='PING',
                        )
        obj.setUp()

class Lbaas(Base):
     #@wrapper
     #def remove_lb_service_instances(self,*arg,**kwarg):
     #   connections = kwarg['connection_obj'].connections
     #   #logger      = kwarg['connection_obj'].logger
     #   tenant_list = kwarg['tenant_list']
     #   service_instances = connections.vnc_lib.service_instances_list()['service-instances']
     #   for si in service_instances:
     #       dom,t_name,si_name = si['fq_name']
     #       if t_name not in tenant_list:
     #          continue
     #       #if re.search('^si_',si_name):
     #       #   continue
     #       connections.vnc_lib.service_instance_delete(fq_name=si['fq_name'])
      
     @wrapper
     def retrieve_lb_pools_info(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger
        pools = connections.vnc_lib.loadbalancer_pools_list() 
        return pools

     @wrapper
     def create_lb_pool(self,*arg,**kwarg):
         connections   = kwarg['connection_obj'].connections
         #logger        = kwarg['connection_obj'].logger
         tenant            = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         tenant_uuid    = tenant['uuid']
         domain,tenant_name = tenant_fq_name
         pool_name      = kwarg['pool_name']
         lb_method      = kwarg['lb_method']
         protocol       = kwarg['protocol']
         servers_net_id = kwarg['servers_net_id']
         lb_pools = connections.vnc_lib.loadbalancer_pools_list(parent_id=tenant_uuid)['loadbalancer-pools']
         lb_pool_already_exists = False
         for lb_pool in lb_pools:
             dom,t_name,pool_n = lb_pool['fq_name']
             if [dom,t_name] == tenant_fq_name and pool_n == pool_name:
                lb_pool_already_exists = True

         if lb_pool_already_exists:
            #logger.warn("lb_pool:%s already exists..skipping create"%pool_name)
            return
         connections.project_name = tenant_name
         connections.inputs.project_name = tenant_name
         quantum_h = connections.quantum_h
         subnet_id = quantum_h.get_vn_obj_from_id(servers_net_id)['network']['subnets'][0]
         quantum_h.create_lb_pool(pool_name,lb_method,protocol,subnet_id)

     @wrapper
     def delete_lb_pool(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         tenant_uuid      = tenant['uuid']
         lb_pools = connections.vnc_lib.loadbalancer_pools_list(parent_id=tenant_uuid) ['loadbalancer-pools']
         for lb_pool in lb_pools:
             uuid = lb_pool['uuid']
             try:
                connections.vnc_lib.loadbalancer_pool_delete(id=uuid)
             except NoIdError:
                pass

     def delete_lb_pools(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_lb_pool(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

     def create_lb_pools(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        pool_names_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name = tenant['fq_name']
            tenant_indx = get_tenant_index(tenant_conf,tenant_fq_name)
            pool_names_list.append(generate_lb_pool_name(global_conf,tenant_conf,tenant_indx))
        lb_pool_vn_list = []
        vn_info_dict = {}
        kwargs = {}
        kwargs['tenant_list'] = tenant_list
        vn_obj = VN(None)
        ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=[kwargs])
        if ret:
           vn_info_dict.update(ret)
        pool_vn_ids = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name = tenant['fq_name']
            tenant_indx  = get_tenant_index(tenant_conf,tenant_fq_name)
            pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
            if not pool_vn_name:
               return
            lb_pool_vn_list.append(pool_vn_name)
            pool_vn_fq_name = tenant_fq_name + [pool_vn_name]
            pool_vn_id   = vn_info_dict[":".join(pool_vn_fq_name)]
            pool_vn_ids.append(pool_vn_id)
        kwargs_list = []
        for i,tenant in enumerate(tenant_list):
             if tenant['fq_name'] == ['default-domain','admin']:
               continue
             kwargs = {}
             kwargs['tenant']      = tenant
             kwargs['pool_name']   = pool_names_list[i]
             kwargs['lb_method']   = tenant_conf['lbaas,method']
             kwargs['protocol']    = tenant_conf['lbaas,pool,protocol']
             kwargs['servers_net_id'] = pool_vn_ids[i]
             kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.create_lb_pool(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def create_lb_member(self,*arg,**kwarg):
         tenant         = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         pool_id        = kwarg['pool_id']
         server_ip      = kwarg['server_ip']
         protocol_port  = kwarg['protocol_port']
         vm_id          = kwarg['vm_id']
         domain_name,tenant_name = tenant_fq_name

         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         connections.project_name = tenant_name
         connections.inputs.project_name = tenant_name
         try:
           pool_obj     = connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except NoIdError:
           return
         lb_members   = pool_obj.get_loadbalancer_members()
         quantum_h    = connections.quantum_h
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

         #vm_obj = connections.vnc_lib.virtual_machine_read(id=vm_id)
         #vmis   = vm_obj.get_virtual_machine_interface_back_refs()
         #for vmi in vmis:
         #    vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
         #    vmi_obj.set_virtual_machine_interface_device_owner("compute:nova")
         #    connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

         if member_found:
            #logger.warn("lb_member : %s %s found..skipping create"%(server_ip,str(protocol_port)))
            return

         quantum_h.create_lb_member(server_ip,protocol_port,pool_id)

     @wrapper
     def delete_lb_member(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         lb_members = connections.vnc_lib.loadbalancer_members_list()['loadbalancer-members']
         for lb_member in lb_members:
             dom,t_name,pool_name,member_id = lb_member['fq_name']
             if [dom,t_name] == tenant_fq_name :
                connections.vnc_lib.loadbalancer_member_delete(id=member_id)

     def delete_lb_members(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
        kwargs_list = []
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            kwargs = {}
            kwargs['tenant'] = tenant
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete_lb_member(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

     def create_lb_members(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        tenant_list_t  = map(lambda x:x['fq_name'],tenant_list)
        ret      = self.retrieve_lb_pools_info(conn_obj_list=conn_obj_list)
        lb_pools = ret['loadbalancer-pools'] 
        lb_pool_info = {}
        for lb_pool in lb_pools:
            dom,t_name,pool_name = lb_pool['fq_name']
            if [dom,t_name] == ['default-domain','admin'] or [dom,t_name] not in tenant_list_t :
               continue
            lb_pool_id           = lb_pool['uuid'] 
            lb_pool_info['%s,%s,%s'%(dom,t_name,pool_name)] = lb_pool_id

        if not lb_pool_info :
           return

        vms_list    = []
        kwargs_list = []
        vm_obj      = VM(None)

        for indx,tenant in enumerate(tenant_list):
          if tenant['fq_name'] == ['default-domain','admin']:
             continue
          tenant_fq_name = tenant['fq_name']
          tenant_indx  = get_tenant_index(tenant_conf,tenant_fq_name)
          pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
          pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
          if not pool_vn_name:
             return
          vms_list     = vm_obj.list_vms(tcount=1,conn_obj_list=conn_obj_list,tenant_list=[tenant],vn_list=[pool_vn_name])
          if not vms_list:
            print "no servers in this VN pool..skipping.."
            continue
          for vm in vms_list:
             vn_name = vm['vn_name']
             vm_ip   = vm['ip'][vn_name][0]['addr']
             kwargs = {}
             kwargs['tenant']        = tenant
             domain,tenant_name      = tenant_fq_name
             kwargs['pool_id']       = lb_pool_info['%s,%s,%s'%(domain,tenant_name,pool_name)]
             kwargs['server_ip']     = vm_ip
             kwargs['vm_id']         = vm['id']
             kwargs['protocol_port'] = tenant_conf['lbaas,pool,members_port']
             kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.create_lb_member(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def create_lb_vip_associate_fip(self,*arg,**kwarg):
         tenant            = kwarg['tenant']
         tenant_fq_name    = tenant['fq_name']
         vip_name          = kwarg['vip_name']
         vip_protocol      = kwarg['vip_protocol']
         vip_protocol_port = kwarg['vip_port']
         pool_id           = kwarg['pool_id']
         subnet_name       = kwarg['subnet_name']
         fip_pool_vn_id    = kwarg['fip_pool_vn_id']
         fip_vn_name       = kwarg['fip_vn_name']
         fip_pool_name     = kwarg['fip_pool_name']
         connections  = kwarg['connection_obj'].connections
         #logger       = kwarg['connection_obj'].logger
         domain_name,tenant_name = tenant_fq_name
         try:
           pool_obj = connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except NoIdError:
           print "ERROR: LB pool is missing",pool_id,tenant_name
           return
         vip_ref  = pool_obj.get_virtual_ip_back_refs() 
         if vip_ref:
            #logger.warn("pool:%s already has VIP..skipping vip create"%pool_id)
            vip_create = False
         else:
            vip_create = True

         fip_fq_name = tenant_fq_name + [fip_vn_name,fip_pool_name]
         try:
            fip_pool_obj  = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_fq_name)
         except NoIdError:
            return
         
         connections.project_name = tenant_name
         connections.inputs.project_name = tenant_name
         vn_fq_name = tenant_fq_name + [subnet_name]
         vn_obj     = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
         net_id     = vn_obj.uuid
         quantum_h = connections.quantum_h
         if vip_create:
            subnet_id      = quantum_h.get_vn_obj_from_id(net_id)['network']['subnets'][0]
            vip_resp       = quantum_h.create_vip(vip_name, vip_protocol,\
                              vip_protocol_port, subnet_id, pool_id)
         vip_fq_name = tenant_fq_name + [vip_name]
         vip_obj = connections.vnc_lib.virtual_ip_read(fq_name=vip_fq_name)
         vmi_refs = vip_obj.get_virtual_machine_interface_refs() or []
         for vmi_ref in vmi_refs:
             vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi_ref['uuid'])
             vmi_obj.set_virtual_machine_interface_device_owner("neutron:LOADBALANCER")
             connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

         vm_intf_id = vmi_refs[0]['uuid']
         dom,t_name,vmi_port_id = vmi_refs[0]['to']
         vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vm_intf_id)
         fips    = vmi_obj.get_floating_ip_back_refs()
         if fips:
            #logger.warn("fip is already attached to VIP..skipping fip attach")
            return

         proj_obj      = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
         connections.orch = connections.get_orch_h()
         fip_ip,fip_id = connections.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id, project_obj=proj_obj, pool_obj=fip_pool_obj)
         update_dict = {}
         update_dict['port_id'] = vm_intf_id
         quantum_h.update_floatingip(fip_id,{'floatingip': update_dict})
         
     @wrapper
     def delete_lb_vip(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         tenant_uuid      = tenant['uuid']
         virt_ips_list = connections.vnc_lib.virtual_ips_list(parent_id=tenant_uuid)['virtual-ips']
         if len(virt_ips_list) == 0:
            return
         quantum_h = connections.quantum_h
         for virt_ip  in virt_ips_list:
             dom,t_name,vip_name = virt_ip['fq_name']
             if [dom,t_name] != tenant_fq_name:
                continue
             virt_ip_id = virt_ip['uuid']
             try:
               quantum_h.delete_vip(virt_ip_id)
             except NotFound:
               pass

     def delete_lb_vips(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

         kwargs_list = []
         for tenant in tenant_list:
             if tenant['fq_name'] == ['default-domain','admin']:
                continue
             kwargs = {}
             kwargs['tenant'] = tenant
             kwargs_list.append(kwargs)

         if len(kwargs_list) == 0:
            return
         self.delete_lb_vip(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
    
     #NOT_USED
     @wrapper
     def associate_fip_to_vip(self,*arg,**kwarg):
         tenant         = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         vip_name       = kwarg['vip_name']
         fip_vn_name    = kwarg['fip_vn_name']
         fip_pool_name  = kwarg['fip_pool_name']
         fip_pool_vn_id = kwarg['fip_pool_vn_id']
         connections = kwarg['connection_obj'].connections
         connections.orch = connections.get_orch_h()
         proj_obj      = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
         fip_fq_name = tenant_fq_name + [fip_vn_name,fip_pool_name]
         try:
            fip_pool_obj  = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_fq_name)
         except NoIdError:
            return
         fip_ip,fip_id = connections.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id, project_obj=proj_obj, pool_obj=fip_pool_obj)
         virt_ips      = connections.vnc_lib.virtual_ips_list()['virtual-ips']
         for vip in virt_ips:
            dom,t_name,v_name = vip['fq_name']
            if not ( [dom,t_name] == tenant_fq_name and v_name == vip_name):
               continue
            vip_id      = vip['uuid']
            vip_obj     = connections.vnc_lib.virtual_ip_read(id=vip_id)
            vm_intf_ref = vip_obj.get_virtual_machine_interface_refs()
            if not vm_intf_ref:
               continue
            vm_intf_id = vm_intf_ref[0]['uuid']
            dom,t_name,vmi_port_id = vm_intf_ref[0]['to']
            vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vm_intf_id)
            fips    = vmi_obj.get_floating_ip_back_refs()
            if fips:
               #logger.warn("fip is already attached to VIP..skipping fip attach")
               return
            vn_id = None
            connections.orch.assoc_floating_ip(fip_id,vmi_port_id,vn_id)
            fips    = vmi_obj.get_floating_ip_back_refs()
            fip_obj = connections.vnc_lib.floating_ip_read(id=fips[0]['uuid'])
            vmi_ref = fip_obj.get_virtual_machine_interface_refs()
            for vmi in vmi_ref:
                vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                vmi_obj.set_virtual_machine_interface_device_owner("compute:nova")
                connections.vnc_lib.virtual_machine_interface_update(vmi_obj)

     def not_used_associate_fip_to_vips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
         if update_properties:
           return
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
         kwargs = {}
         kwargs['tenant_list'] = tenant_list
         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=[kwargs])
         if ret:
            vn_info_dict.update(ret)
         for tenant in tenant_list:
             if tenant['fq_name'] == ['default-domain','admin']:
                continue
             tenant_indx = get_tenant_index(tenant_conf,tenant_fq_name)
             kwargs = {}
             kwargs['tenant']      = tenant
             kwargs['vip_name']    = generate_vip_name(global_conf,tenant_conf,tenant_indx)
             pool_vn_name          = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                        fip_vn_name_pattern,vn_index)
             kwargs['fip_vn_name'] = pool_vn_name
             kwargs['fip_pool_name'] = generate_fip_pool_name(global_conf,tenant_conf,\
                                          tenant_indx,pool_indx)
             pool_vn_fq_name         = tenant_fq_name + [pool_vn_name]
             kwargs['fip_pool_vn_id'] = vn_info_dict[":".join(pool_vn_fq_name)]
             kwargs_list.append(kwargs)
         if len(kwargs_list) == 0:
            return
         self.associate_fip_to_vip(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     def create_lb_vips_associate_fips(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
         if update_properties:
           return
         fip_pool_indx = 0
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
            lb_pool_info['%s,%s,%s'%(dom,t_name,pool_name)] = lb_pool_id

         kwargs = {}
         kwargs['tenant_list'] = tenant_list
         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=[kwargs])
         if ret:
            vn_info_dict.update(ret)

         fip_vn_name_pattern = None
         vip_vn_name_pattern = None
         attach_fip = False
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
             vn_info              = tenant_conf['tenant,vn_group_list'][vn_group_index]
             vn_name_pattern      = vn_info['vn,name,pattern']
             if re.search('Public_FIP_VN',vn_name_pattern):
                fip_vn_name_pattern = vn_name_pattern
             if re.search('Private_LB_VIP_VN',vn_name_pattern):
                vip_vn_name_pattern = vn_name_pattern
                attach_fip = vn_info['attach_fip']

         kwargs_list  = []
         for tenant in tenant_list:
             if tenant['fq_name'] == ['default-domain','admin']:
                continue
             tenant_fq_name = tenant['fq_name']
             tenant_indx  = get_tenant_index(tenant_conf,tenant_fq_name)
             pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
             pool_vn_name = generate_lb_pool_vn_name(global_conf,tenant_conf,tenant_indx)
             if not pool_vn_name:
                return
             pool_vn_fq_name = tenant_fq_name + [pool_vn_name]
             pool_vn_id   = vn_info_dict[":".join(pool_vn_fq_name)]
             vip_index    = tenant_indx
             vn_index     = 0
             vip_name     = generate_vip_name(global_conf,tenant_conf,vip_index)
             vip_vn_name  = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                vip_vn_name_pattern,vn_index)
             kwargs = {}
             kwargs['tenant']       = tenant
             domain,tenant_name     = tenant_fq_name
             kwargs['vip_name']     = vip_name
             kwargs['vip_port']     = vip_port
             kwargs['vip_protocol'] = vip_protocol
             kwargs['subnet_name']  = vip_vn_name
             kwargs['pool_id']      = lb_pool_info['%s,%s,%s'%(domain,tenant_name,pool_name)]
             if attach_fip:
                fip_pool_vn_name = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                        fip_vn_name_pattern,vn_index)
                kwargs['fip_vn_name'] = fip_pool_vn_name
                kwargs['fip_pool_name'] = generate_fip_pool_name(global_conf,tenant_conf,\
                                          tenant_indx,fip_pool_indx)
                fip_pool_vn_fq_name = tenant_fq_name + [fip_pool_vn_name]
                fip_pool_vn_fq_name_str = ":".join(fip_pool_vn_fq_name)
                kwargs['fip_pool_vn_id'] = vn_info_dict[fip_pool_vn_fq_name_str]
             kwargs_list.append(kwargs)
    
         if len(kwargs_list) == 0:
            return
         self.create_lb_vip_associate_fip(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def create_health_monitor(self,*arg,**kwarg):
         tenant   = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         tenant_uuid    = tenant['uuid']
         domain_name,tenant_name = tenant_fq_name
         probe_type  = kwarg['probe_type']
         delay       = kwarg['probe_delay']
         timeout     = kwarg['probe_timeout']
         max_retries = kwarg['probe_retries']
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         hms = connections.vnc_lib.loadbalancer_healthmonitors_list(parent_id=tenant_uuid)['loadbalancer-healthmonitors']
         if hms:
            #logger.warn("Health-monitor already present..skipping create for tenant:%s"%tenant_name)
            return
         connections.project_name        = tenant_name
         connections.inputs.project_name = tenant_name
         quantum_h = connections.quantum_h
         quantum_h.create_health_monitor( delay, max_retries, probe_type, timeout)

     def create_health_monitors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
           return
        lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
        if lbaas_pool_name_pattern is None:
           return
        kwargs_list  = []
        probe_type = tenant_conf.get('lbaas,probe,type',None)
        if probe_type is None:
           return
        for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            kwargs = {}
            kwargs['tenant']        = tenant
            kwargs['probe_type']    = tenant_conf['lbaas,probe,type']
            kwargs['probe_delay']   = tenant_conf['lbaas,probe,delay']
            kwargs['probe_timeout'] = tenant_conf['lbaas,probe,timeout']
            kwargs['probe_retries'] = tenant_conf['lbaas,probe,retries']
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return
        self.create_health_monitor(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def associate_health_monitor(self,*arg,**kwarg):
         tenant         = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         domain_name,tenant_name = tenant_fq_name
         pool_name        = kwarg['pool_name']
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         pools   = connections.vnc_lib.loadbalancer_pools_list()['loadbalancer-pools']
         if len(pools) == 0:
            return
         pool_fq_name = tenant_fq_name + [pool_name]
         pool_id = None
         for pool in pools:
            if pool['fq_name'] == pool_fq_name:
               pool_id = pool['uuid']
         connections.project_name = tenant_name
         connections.inputs.project_name = tenant_name
         quantum_h = connections.quantum_h
         hms = connections.vnc_lib.loadbalancer_healthmonitors_list()['loadbalancer-healthmonitors']
         hm_id = None
         for hm in hms:
             dom,t_name,hmid = hm['fq_name']
             if [dom,t_name] == tenant_fq_name:
               hm_id = hmid
               break
         try:
           pool_obj = connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
         except NoIdError:
           return 
         hm_ref   = pool_obj.get_loadbalancer_healthmonitor_refs()
         
         if hm_ref:
            #logger.warn("health monitor is already associated with the pool..skipping hm associate.")
            return
         quantum_h.associate_health_monitor(pool_id,hm_id)

     def associate_health_monitors(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
           if update_properties:
              return
           lbaas_pool_name_pattern  = tenant_conf.get('lbaas,pool_name',None)
           if lbaas_pool_name_pattern is None:
              return
           probe_type = tenant_conf.get('lbaas,probe,type',None)
           if probe_type is None:
              return
           kwargs_list  = []
           for tenant in tenant_list:
               if tenant['fq_name'] == ['default-domain','admin']:
                  continue
               tenant_fq_name = tenant['fq_name']
               tenant_indx  = get_tenant_index(tenant_conf,tenant_fq_name)
               pool_name    = generate_lb_pool_name(global_conf,tenant_conf,tenant_indx)
               kwargs = {}
               kwargs['tenant']    = tenant
               kwargs['pool_name'] = pool_name
               kwargs_list.append(kwargs)

           if len(kwargs_list) == 0:
              return
           self.associate_health_monitor(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def delete_health_monitor(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         tenant_uuid      = tenant['uuid']
         hms = connections.vnc_lib.loadbalancer_healthmonitors_list(parent_id=tenant_uuid)['loadbalancer-healthmonitors']
         for hm in hms:
             hm_obj = connections.vnc_lib.loadbalancer_healthmonitor_read(id=hm['uuid'])
             pools = hm_obj.get_loadbalancer_pool_back_refs() or []
             for pool in pools:
                 pool_id = pool['uuid']
                 pool_obj = connections.vnc_lib.loadbalancer_pool_read(id=pool_id)
                 pool_obj.del_loadbalancer_healthmonitor(hm_obj)
                 connections.vnc_lib.loadbalancer_pool_update(pool_obj)
             connections.vnc_lib.loadbalancer_healthmonitor_delete(hm_obj.fq_name)

     def delete_health_monitors(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

           kwargs_list  = []
           for tenant in tenant_list:
               if tenant['fq_name'] == ['default-domain','admin']:
                  continue
               kwargs = {}
               kwargs['tenant'] = tenant
               kwargs_list.append(kwargs)

           if len(kwargs_list) == 0:
              return
           self.delete_health_monitor(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

def generate_si_name(si_name,index):
    return re.sub('CCC',str(index),si_name)

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
      @wrapper
      def retrieve_pr_vlan_info(self,*arg,**kwarg):
          global_conf     = kwarg.get('global_conf',None)
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
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
                 pi_obj = connections.vnc_lib.physical_interface_read(fq_name=['default-global-system-config',unicode(pr_name),unicode(pi_interface_m)])
              except NoIdError:
                 continue
              li_ref = pi_obj.get_logical_interfaces() or []
              pi_vlan_info[physical_server_ip_addr] = []
              for li in li_ref:
                  try:
                    li_obj = connections.vnc_lib.logical_interface_read(id=li['uuid'])
                  except NoIdError:
                    continue
                  vlan_id = li_obj.logical_interface_vlan_tag
                  pi_vlan_info[physical_server_ip_addr].append(vlan_id)
          return pi_vlan_info
 
      @wrapper
      def create_physical_router(self,*arg,**kwarg):
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
          loopback_ip       = kwarg.get('pr,loopback_ip',None)
          ta                = kwarg.get('pr,ta',None)
          pr_interface_name = kwarg.get('pr,interface_name',None)
          pr_interface_vlan = kwarg.get('pr,interface_vlan',None)
          pr_interface_vn   = kwarg.get('pr,interface_vn',None)
          pr_interface_mac  = kwarg.get('pr,interface_mac',None)
          pr_interface_ip   = kwarg.get('pr,interface_ip',None)
          net_conf_enabled  = kwarg.get('pr,net_conf_enabled')
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          rt_inst_obj = connections.vnc_lib.routing_instance_read(
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
              #params.identifier = pr_mgmt_ip
              params.identifier = loopback_ip
              bgp_router.set_bgp_router_parameters(params)
              try:
                  connections.vnc_lib.bgp_router_read(fq_name=['default-domain', 'default-project', 'ip-fabric', '__default__', pr_name])
                  connections.vnc_lib.bgp_router_update(bgp_router)
              except NoIdError:
                  connections.vnc_lib.bgp_router_create(bgp_router)

          pr = PhysicalRouter(pr_name)
          pr.physical_router_management_ip = pr_mgmt_ip
          pr.physical_router_vendor_name   = 'juniper'
          pr.physical_router_product_name  = 'mx'
          if pr_login is not None:
             uc = UserCredentials(pr_login,pr_password)
             pr.set_physical_router_user_credentials(uc)
          if is_tor == False:
             pr.set_bgp_router(bgp_router)
             #pr.set_physical_router_loopback_ip(loopback_ip)
          try:
              connections.vnc_lib.physical_router_read(
                        fq_name=[u'default-global-system-config',pr_name]) 
              connections.vnc_lib.physical_router_update(pr)
          except NoIdError:
              connections.vnc_lib.physical_router_create(pr)
          pr.physical_router_vnc_managed     = net_conf_enabled
          if is_tor :
             pr.physical_router_product_name = 'qfx'
          else:
             pr.physical_router_product_name = 'mx'
             junos_service_ports = JunosServicePorts()
             junos_service_ports.service_port.append(pr_junos_si)
             pr.set_physical_router_junos_service_ports(junos_service_ports)
          pr.physical_router_vendor_name     = 'juniper'
          pr.physical_router_dataplane_ip    = pr_dataplane_ip
          connections.vnc_lib.physical_router_update(pr)

          pr_obj = connections.vnc_lib.physical_router_read(
                        fq_name=[u'default-global-system-config',pr_name])
         
          if pr_interface_name:
             try:
               pr_interface_name_m = re.sub(":","__",pr_interface_name)
               pi = connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, pr_interface_name_m])
             except NoIdError:
               pi = PhysicalInterface(pr_interface_name_m, parent_obj = pr,display_name=pr_interface_name)
               connections.vnc_lib.physical_interface_create(pi)

             iface_name   = pr_interface_name + "." + str(pr_interface_vlan)
             iface_name_m = re.sub(":","__",iface_name)
             vmi_fq_name  = ['default-domain','admin',unicode(iface_name_m)]
             vn_fq_name   = ['default-domain','admin',pr_interface_vn]
             vn_obj       = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
             try:
               vmi_obj = connections.vnc_lib.virtual_machine_interface_read(fq_name=vmi_fq_name)
             except NoIdError:
               vmi_obj = VirtualMachineInterface(fq_name=vmi_fq_name, parent_type='project')
               vmi_obj.set_virtual_machine_interface_device_owner("PhysicalRouter")
               mac_address_obj = MacAddressesType()
               mac_address_obj.set_mac_address([pr_interface_mac])
               vmi_obj.set_virtual_machine_interface_mac_addresses(mac_address_obj)
               vmi_obj.add_virtual_network(vn_obj)
               connections.vnc_lib.virtual_machine_interface_create(vmi_obj)
               vmi_obj = connections.vnc_lib.virtual_machine_interface_read(fq_name=vmi_fq_name)
             try:
               li = connections.vnc_lib.logical_interface_read(
                             fq_name=[u'default-global-system-config', pr_name,pr_interface_name_m,iface_name_m])
               li.set_virtual_machine_interface(vmi_obj)
               connections.vnc_lib.logical_interface_update(li)
             except NoIdError:
               li = LogicalInterface(iface_name_m, parent_obj = pi,logical_interface_vlan_tag=pr_interface_vlan,display_name=iface_name)
               li.set_virtual_machine_interface(vmi_obj)
               connections.vnc_lib.logical_interface_create(li)
               instance_ip_name = iface_name_m + "." + str(pr_interface_vlan)
               try:
                 ip_obj = connections.vnc_lib.instance_ip_read(fq_name=[unicode(instance_ip_name)])
                 ip_obj.set_virtual_machine_interface(vmi_obj)
                 ip_obj.set_virtual_network(vn_obj)
                 ip_obj.set_instance_ip_address(pr_interface_ip)
                 connections.vnc_lib.instance_ip_update(ip_obj)
               except NoIdError:
                 ip_obj = InstanceIp(name=instance_ip_name)
                 ip_obj.set_virtual_machine_interface(vmi_obj)
                 ip_obj.set_instance_ip_address(pr_interface_ip)
                 ip_obj.set_virtual_network(vn_obj)
                 connections.vnc_lib.instance_ip_create(ip_obj)

          if ta:
             vr = VirtualRouter(ta)
             vr.virtual_router_ip_address = tsn_ip
             vr.virtual_router_type='tor-agent'
             try:
               connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',ta])
               connections.vnc_lib.virtual_router_update(vr)
             except NoIdError:
               connections.vnc_lib.virtual_router_create(vr)
             tor_agent_obj = connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',ta])
          if tsn:
             vr = VirtualRouter(tsn)
             vr.virtual_router_ip_address = tsn_ip
             vr.virtual_router_type='tor-service-node'
             try:
               connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',tsn])
               connections.vnc_lib.virtual_router_update(vr)
             except NoIdError:
               connections.vnc_lib.virtual_router_create(vr)
             tsn_obj = connections.vnc_lib.virtual_router_read(
                           fq_name=[u'default-global-system-config',tsn])

          if ta and tsn:
             pr_obj.add_virtual_router(tor_agent_obj)
             pr_obj.add_virtual_router(tsn_obj)
             connections.vnc_lib.physical_router_update(pr_obj)

      @wrapper
      def retrieve_existing_li(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          existing_li      = connections.vnc_lib.logical_interfaces_list()['logical-interfaces']
          return existing_li

      @wrapper
      def retrieve_pi_vlan_info(self,*arg,**kwarg):
          pr_qfxs = kwarg['pr_qfxs']
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
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
                    pi_obj = connections.vnc_lib.physical_interface_read(fq_name=['default-global-system-config',unicode(pr_name),unicode(pi_m)])
                  except NoIdError,TypeError:
                    continue
                  li_ref = pi_obj.get_logical_interfaces() or []
                  for li in li_ref:
                      li_obj = connections.vnc_lib.logical_interface_read(id=li['uuid'])
                      vlan_id = li_obj.logical_interface_vlan_tag 
                      pi_vlan_info[pr_name].append(vlan_id)
                      try:
                        vmi_refs = li_obj.virtual_machine_interface_refs[0]
                        vmi_obj  = connections.vnc_lib.virtual_machine_interface_read(id=vmi_refs['uuid'])
                      except:
                        continue #TO_FIX
                      mac_obj  = vmi_obj.get_virtual_machine_interface_mac_addresses()
                      mac_addr = mac_obj.mac_address[0]
                      if pi_vlan_info.has_key(mac_addr):
                         pi_vlan_info[mac_addr].append(vlan_id)
                      else:
                         pi_vlan_info[mac_addr] = []
          return pi_vlan_info

      @wrapper
      def create_logical_interface(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          physical_iface_name   = kwarg['physical_iface']
          physical_iface_name_m = re.sub(":","__",physical_iface_name)
          tenant       = kwarg['tenant']
          tenant_fq_name = tenant['fq_name']
          pr_name      = kwarg['pr_name']
          mac_addr     = kwarg['mac_addr']
          iface_name   = kwarg['iface_name']
          existing_li  = kwarg['existing_li']
          iface_name_m = re.sub(":","__",iface_name)
          pi_obj       = kwarg['pi_obj']
          vn_name      = kwarg['vn_name']
          li_regex     = "default-global-system-config:" + pr_name + ":.*" + "%s.bms%s\."%(vn_name,kwarg['bms_index'])

          li = LogicalInterface(iface_name_m, parent_obj = pi_obj,logical_interface_vlan_tag=kwarg['vlan_id'],display_name=iface_name)
          li.parent_uuid = pi_obj.uuid

          try:
            connections.vnc_lib.logical_interface_create(li)
          except (RefsExistError,PermissionDenied): # PermissionDenied seen for Vlan tag already used
            pass

          vmi_fq_name = tenant_fq_name + [iface_name_m]
          vmi_obj = VirtualMachineInterface(fq_name=vmi_fq_name, parent_type='project')
          mac_address_obj = MacAddressesType()
          mac_address_obj.set_mac_address([mac_addr])
          vmi_obj.set_virtual_machine_interface_device_owner("PhysicalRouter")
          vmi_obj.set_virtual_machine_interface_mac_addresses(mac_address_obj)
          vn_fq_name  = tenant_fq_name + [vn_name]
          vn_obj      = connections.vnc_lib.virtual_network_read(fq_name=vn_fq_name)
          vmi_obj.add_virtual_network(vn_obj)
          try:
            connections.vnc_lib.virtual_machine_interface_create(vmi_obj)
          except RefsExistError:
            pass

          instance_ip_name = iface_name_m + "." + str(kwarg['vlan_id'])
          try:
            ip_obj = connections.vnc_lib.instance_ip_read(fq_name=[unicode(instance_ip_name)])
            ip_obj.set_virtual_machine_interface(vmi_obj)
            ip_obj.set_virtual_network(vn_obj)
            connections.vnc_lib.instance_ip_update(ip_obj)
          except NoIdError:
            ip_obj = InstanceIp(name=instance_ip_name)
            ip_obj.set_virtual_machine_interface(vmi_obj)
            ip_obj.set_virtual_network(vn_obj)
            try:
               connections.vnc_lib.instance_ip_create(ip_obj)
            except RefsExistError:
               pass

          #conf_obj = GlobalVrouterConfig(vxlan_network_identifier_mode='auto-configured')
          #connections.vnc_lib.global_vrouter_config_update(conf_obj)

          vni_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
          vni_obj_properties.set_vxlan_network_identifier(kwarg['vlan_id'])
          vn_obj.set_virtual_network_properties(vni_obj_properties)
          connections.vnc_lib.virtual_network_update(vn_obj)
          li.add_virtual_machine_interface(vmi_obj)
          connections.vnc_lib.logical_interface_update(li)

      @wrapper
      def retrieve_existing_pr(self,*arg,**kwarg):
          connection_obj = kwarg['connection_obj']
          connections = connection_obj.connections
          #logger      = connection_obj.logger
          prs = connections.vnc_lib.physical_routers_list()['physical-routers']
          pr_names = []
          for pr in prs:
              fq_name = pr['fq_name'][1]
              pr_names.append(fq_name)
          return pr_names

      @wrapper
      def retrieve_pi_obj(self,*arg,**kwarg):
          connection_obj   = kwarg['connection_obj']
          connections = connection_obj.connections
          #logger      = connection_obj.logger
          pr_name          = kwarg['pr_name']
          physical_iface_name = kwarg['physical_iface_name']
          iface_name_m = re.sub(":","__",physical_iface_name)
          pi_obj = connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, iface_name_m])
          return pi_obj

      def create_logical_interfaces(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
          if update_properties:
             return
          tenant_list = tenant_list
          global_conf      = global_conf
          tenant_conf      = tenant_conf
          conf_l  = []
          pr_qfxs = global_conf['pr_qfx']
          if not pr_qfxs:
            return True
          kwargs_t = {}
          kwargs_t['pr_qfxs'] = pr_qfxs
          pi_vlan_info = self.retrieve_pi_vlan_info(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs_t])
          existing_li  = self.retrieve_existing_li(tcount=1,conn_obj_list=admin_conn_obj_list)
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
                  kwargs_t = {}
                  kwargs_t['pr_name'] = pr_name
                  kwargs_t['physical_iface_name'] = physical_iface_name
                  pi_obj = self.retrieve_pi_obj(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs_t])
                  pi_obj_dict[pr_name,physical_iface_name] = pi_obj

          for tenant in tenant_list:
              if tenant['fq_name'] == ['default-domain','admin']:
                 continue
              tenant_fq_name = tenant['fq_name']
              tenant_index   = get_tenant_index(tenant_conf,tenant_fq_name)
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
                          li_conf['tenant']      = tenant
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
                            tenant_fq_name = li_conf['tenant']['fq_name']
                            tenant_index = get_tenant_index(tenant_conf,tenant_fq_name)
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
                            kwargs['tenant']         = li_conf['tenant']
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
          self.create_logical_interface(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
                 
      @wrapper
      def delete_physical_interface(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          pr_name = kwarg['pr_name']
          pis = connections.vnc_lib.physical_interfaces_list()['physical-interfaces']
          for pi in pis:
              pi_fq_name  = pi['fq_name']
              router_name = pi_fq_name[1]
              if router_name != pr_name:
                 continue
              try:
                 pi_obj=connections.vnc_lib.physical_interface_read(id=pi['uuid'])
                 connections.vnc_lib.physical_interface_delete(pi_obj.fq_name)
              except NoIdError:
                 pass
              except RefsExistError:
                 print "ERROR: delete failed..RefExists for physical interface:",pi['uuid']
                 traceback.print_exc(file=sys.stdout)
                 handleRefsExistError()
   
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
          self.delete_physical_interface(tcount=1,conn_obj_list=conn_obj_list, kwargs_list=kwargs_list)

      @wrapper
      def delete_logical_interface(self,*arg,**kwarg):
          pr_name          = kwarg['pr_name']
          tenant_list      = kwarg['tenant_list']
          tenant_list_t    = map(lambda x:x['fq_name'],tenant_list)
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          lis              = kwarg['existing_li']
          for li in lis:
              li_fq_name  = li['fq_name']
              router_name = li_fq_name[1]
              if router_name != pr_name:
                 continue
              try: #CHECK
                li_obj = connections.vnc_lib.logical_interface_read(id=li['uuid'])
              except NoIdError:
                continue
              vmis   = li_obj.get_virtual_machine_interface_refs() or []
              delete_li = False
              for vmi in vmis:
                try:
                  dom,t_name,vmi_name = vmi['to']
                  if [dom,t_name] not in tenant_list_t:
                     delete_li = False
                     break
                  vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                  inst_ips = vmi_obj.get_instance_ip_back_refs() or []
                  for inst_ip in inst_ips:
                      inst_ip_id = inst_ip['uuid']
                      connections.vnc_lib.instance_ip_delete(id=inst_ip_id)
                  li_obj.del_virtual_machine_interface(vmi_obj)
                  connections.vnc_lib.logical_interface_update(li_obj)
                  connections.vnc_lib.virtual_machine_interface_delete(vmi_obj.fq_name)
                except:
                  pass # TO_FIX
              if delete_li or len(vmis) == 0:
                 try:
                   connections.vnc_lib.logical_interface_delete(id=li['uuid'])
                 except NoIdError:
                   pass
                 except RefsExistError:
                    print "ERROR: delete failed..RefExists for Logical interface:",li['uuid']
                    traceback.print_exc(file=sys.stdout)
                    handleRefsExistError()
              else:
                 print "INFO: skipping delete LI",li_fq_name

      def delete_logical_interfaces(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list=[]):

          existing_li = self.retrieve_existing_li(tcount=1,conn_obj_list=admin_conn_obj_list)
          pr_names    = self.retrieve_existing_pr(tcount=1,conn_obj_list=admin_conn_obj_list)
          kwargs_list = []
          existing_li_filtered = []
          mx_name = retrieve_mx_name(global_conf)
          mx_physical_interface = retrieve_mx_physical_interface(global_conf)
          mx_physical_interface_vlan = retrieve_mx_physical_interface_vlan(global_conf)

          if ( len(tenant_list) == 1 and tenant_list[0]['fq_name'] == ['default-domain', 'admin']):
             global_conf_delete = True
          else:
             global_conf_delete = False		
          if global_conf_delete == True:
             existing_li_filtered = existing_li
	  else:	
             for li in existing_li:
               if ( li['fq_name'] == [u'default-global-system-config',mx_name,mx_physical_interface,mx_physical_interface + "." + str(mx_physical_interface_vlan)]) :
                 continue
               else:
                 existing_li_filtered.append(li)
          for pr in pr_names:
              kwargs = {}
              kwargs['tenant_list'] = tenant_list
              kwargs['pr_name']     = pr
              kwargs['existing_li'] = existing_li_filtered
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          if ( len(tenant_list) == 1  and tenant_list[0]['fq_name'] == ['default-domain', 'admin']):
             self.delete_logical_interface(tcount=1,timeout=1800,conn_obj_list=admin_conn_obj_list,kwargs_list=kwargs_list)
          else: 
             self.delete_logical_interface(tcount=thread_count,timeout=1800,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

      @wrapper
      def delete_physical_router(self,*arg,**kwarg):
          pr_name = kwarg['pr_name']
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          try:
            pr_obj = connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', unicode(pr_name)])
          except NoIdError:
            return
          connections.vnc_lib.physical_router_delete(pr_obj.fq_name)

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
          self.delete_physical_router(tcount=1,conn_obj_list=conn_obj_list, kwargs_list=kwargs_list)
          return

      @wrapper
      def create_physical_interface(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          pr_name                 = kwarg['pr_name']
          physical_interface_list = kwarg['physical_interface_list']
          pr_obj = connections.vnc_lib.physical_router_read(fq_name=[u'default-global-system-config', unicode(pr_name)])
          for physical_interface in physical_interface_list:
             try:
                 physical_interface_m = re.sub(":","__",physical_interface)
                 pi = connections.vnc_lib.physical_interface_read(fq_name=[u'default-global-system-config', pr_name, physical_interface_m])
             except NoIdError:
                 pi = PhysicalInterface(physical_interface_m, parent_obj = pr_obj,display_name=physical_interface)
                 connections.vnc_lib.physical_interface_create(pi)

      def create_physical_interfaces(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
          if update_properties:
             return
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
          self.create_physical_interface(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

      def create_physical_routers(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
          if update_properties:
             return
          physical_routers_config = global_conf['pr_mx']
          kwargs_list = []
          for physical_router in physical_routers_config:  
              kwargs = {}
              kwargs['pr,name']     = physical_router['name']
              kwargs['pr,mgmt_ip']  = physical_router['mgmt_ip']
              kwargs['pr,login']    = physical_router['netconf']['uname']
              kwargs['pr,password'] = physical_router['netconf']['password']
              kwargs['pr,junos_si'] = physical_router['netconf']['junos_si']
              kwargs['pr,net_conf_enabled'] = physical_router['netconf']['enabled']
              kwargs['pr,dataplane_ip'] = physical_router['vtep_ip']
              kwargs['pr,loopback_ip'] = physical_router['loopback_ip']
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
          self.create_physical_router(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

      @wrapper
      def associate_fip_to_vmi(self,*arg,**kwarg):
         pool_tenant_fq_name = kwarg['pool_tenant_fq_name']
         tenant   = kwarg['tenant']
         tenant_fq_name = tenant['fq_name']
         tenant_uuid    = tenant['uuid']
         tenant_conf    = kwarg['tenant_conf']
         global_conf    = kwarg['global_conf']
         fip_vn_name    = kwarg['fip_vn_name']
         fip_pool_name  = kwarg['fip_pool_name']
         fip_pool_vn_id = kwarg['fip_pool_vn_id']
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         fip_fq_name   = pool_tenant_fq_name + [fip_vn_name,fip_pool_name]
         try:
            fip_pool_obj  = connections.vnc_lib.floating_ip_pool_read(fq_name=fip_fq_name)
         except NoIdError:
            print "ERROR: FIP pool %s missing"%str(fip_fq_name)
            return
         vmis = connections.vnc_lib.virtual_machine_interfaces_list(parent_id=tenant_uuid)['virtual-machine-interfaces']
         attach_fip_vns = []
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
            tenant_index = get_tenant_index(tenant_conf,tenant_fq_name)
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
                    vn_fq_name = tenant_fq_name + [vn_name]
                    attach_fip_vns.append(vn_fq_name)
            
         proj_obj = connections.vnc_lib.project_read(id=tenant_uuid)
         for vmi in vmis:
             vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
             net_ref = vmi_obj.get_virtual_network_refs()[0]['to']
             if net_ref not in attach_fip_vns:
                print "Skipping FIP attach for vmi:%s,%s"%(vmi_obj.fq_name,net_ref)
                continue
             li_ref  = vmi_obj.get_logical_interface_back_refs()
             if li_ref is None:
                 print "INFO: li_ref is none for VMI:%s..skipping FIP attach"%(str(vmi_obj.fq_name))
                 continue
             fips    = vmi_obj.get_floating_ip_back_refs()
             if fips:
               print "fip is already attached to VMI..skipping fip attach"
               continue
             else:
               print "attaching fip:%s"%str(vmi_obj.fq_name)
             fip_ip,fip_id = connections.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id, project_obj=proj_obj, pool_obj=fip_pool_obj)
             fip_obj = connections.vnc_lib.floating_ip_read(id=fip_id)
             fip_obj.set_virtual_machine_interface(vmi_obj)
             fip_obj.set_project(proj_obj)   
             connections.vnc_lib.floating_ip_update(fip_obj)
             print "INFO: fip attached to VMI:",vmi_obj.fq_name

      def associate_fip_to_vmis(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
         if update_properties:
            return
         kwargs_list = []
         vn_index    = 0
         pool_indx   = 0
         fip_vn_name_pattern = None
         for vn_group_index in xrange(len(tenant_conf['tenant,vn_group_list'])):
             vn_info         = tenant_conf['tenant,vn_group_list'][vn_group_index]
             vn_name_pattern = vn_info['vn,name,pattern']
             if re.search('Public_FIP_VN',vn_name_pattern):
                fip_vn_name_pattern = vn_name_pattern
         fip_shared = tenant_conf.get('fip,shared',False)
         if fip_vn_name_pattern is None and fip_shared is False:
            return
         vn_info_dict = {}
         if fip_shared:
            tenant_list_l = tenant_list + fip_pool_tenant_fq_name
         else:
            tenant_list_l = tenant_list[:]
         kwargs = {}
         kwargs['tenant_list'] = tenant_list_l
         vn_obj = VN(None)
         ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
         if ret:
            vn_info_dict.update(ret)
         for tenant in tenant_list:
             if tenant['fq_name'] == ['default-domain','admin']:
                continue
             tenant_fq_name        = tenant['fq_name']
             tenant_indx           = get_tenant_index(tenant_conf,tenant_fq_name)
             if fip_shared:
               pool_vn_name        = tenant_conf['fip,shared,fip_gw_vn_name'] 
               pool_tenant_fq_name = tenant_conf['fip,shared,tenant_name']
             else:
               pool_vn_name        = generate_vn_name(global_conf,tenant_conf,tenant_indx,\
                                        fip_vn_name_pattern,vn_index)
               fip_pool_name       = generate_fip_pool_name(global_conf,tenant_conf,\
                                          tenant_indx,pool_indx)
               pool_tenant_fq_name = tenant_fq_name 
             kwargs = {}
             kwargs['tenant'] = tenant
             kwargs['pool_tenant_fq_name'] = pool_tenant_fq_name
             kwargs['tenant_conf'] = tenant_conf
             kwargs['global_conf'] = global_conf
             kwargs['fip_vn_name'] = pool_vn_name
             kwargs['fip_pool_name'] = fip_pool_name
             pool_vn_fq_name = pool_tenant_fq_name + [pool_vn_name]
             pool_vn_fq_name_str = ":".join(pool_vn_fq_name)
             kwargs['fip_pool_vn_id'] = vn_info_dict[pool_vn_fq_name_str]
             kwargs_list.append(kwargs)
         if len(kwargs_list) == 0:
            return
         self.associate_fip_to_vmi(tcount=thread_count,conn_obj_list=admin_conn_obj_list,kwargs_list=kwargs_list)

      def create_tors(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False,tenant_list=[]):
          if update_properties:
            return
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
              kwargs['pr,net_conf_enabled'] = False
              kwargs['is_tor']      = True
              kwargs['global_conf'] = global_conf
              kwargs['tenant_conf'] = tenant_conf
              kwargs['tenant_list'] = tenant_list
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          print "Creating ToR:"
          self.create_physical_router(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

class VrouterGlobalConfig(Base):
    @wrapper
    def create_qos(self,*arg,**kwarg):
        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger
        qos_name         = kwarg['qos_name']
        dscp_values_list = kwarg['dscp_entries']
        mpls_values_list = kwarg['mpls_entries']
        vlan_values_list = kwarg['vlan_entries']

        if dscp_values_list:
           dscp_values_list_n = [0,1,2,3,4,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,44,46,48,56]
        else:
           dscp_values_list_n = []
        if mpls_values_list:
           mpls_values_list_n = range(0,8)
        else:
           mpls_values_list_n = []
        if vlan_values_list:
           vlan_values_list_n = range(0,8)
        else:
           vlan_values_list_n = []

        global_qos_fq_name = [u'default-global-system-config', u'default-global-qos-config']
        global_qos_obj = connections.vnc_lib.global_qos_config_read(fq_name=global_qos_fq_name)

        qos_obj = QosConfig(name=qos_name,parent_obj=global_qos_obj)     
        qos_obj.set_qos_config_type('vhost')

        dscp_entries = QosIdForwardingClassPairs()
        for dscp_value in dscp_values_list_n:
            dscp_entry = QosIdForwardingClassPair()
            dscp_entry.set_key(dscp_value)
            dscp_entry.set_forwarding_class_id(1)
            dscp_entries.add_qos_id_forwarding_class_pair(dscp_entry)
        qos_obj.set_dscp_entries(dscp_entries)

        mpls_entries = QosIdForwardingClassPairs()
        for mpls_value in mpls_values_list_n:
            mpls_entry = QosIdForwardingClassPair()
            mpls_entry.set_key(mpls_value)
            mpls_entry.set_forwarding_class_id(1)
            mpls_entries.add_qos_id_forwarding_class_pair(mpls_entry)
        qos_obj.set_mpls_exp_entries(mpls_entries)

        vlan_entries = QosIdForwardingClassPairs()
        for vlan_value in vlan_values_list_n:
            vlan_entry = QosIdForwardingClassPair()
            vlan_entry.set_key(vlan_value)
            vlan_entry.set_forwarding_class_id(1)
            vlan_entries.add_qos_id_forwarding_class_pair(vlan_entry)
        qos_obj.set_vlan_priority_entries(vlan_entries)
        gs_conf_obj = connections.vnc_lib.global_system_config_read(fq_name=[u'default-global-system-config'])
        qos_obj.add_global_system_config(gs_conf_obj)
        connections.vnc_lib.qos_config_create(qos_obj)

    def create_qoss(self,count,conn_obj_list,global_conf):

        qos_config_l = global_conf['qos'] 
        kwargs_list = []
        for qos_config in qos_config_l:
            qos_name = qos_config['name']
            #forwarding_class_id = qos_config['forwarding_class_id']
            dscp_entries = qos_config.get('dscp_entries',[])
            mpls_entries = qos_config.get('mpls_entries',[])
            vlan_entries = qos_config.get('vlan_entries',[])
            kwargs = {}
            kwargs['qos_name'] = qos_name
            #kwargs['default_forwarding_class_id'] = default_forwarding_class_id
            kwargs['dscp_entries'] = dscp_entries
            kwargs['mpls_entries'] = mpls_entries
            kwargs['vlan_entries'] = vlan_entries
            kwargs_list.append(kwargs)
           
        if len(kwargs_list):
           self.create_qos(count=count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def list_qos(self,*arg,**kwarg):

        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger
        try:
          return connections.vnc_lib.qos_configs_list().get('qos-configs',[])
        except:
          return []

    @wrapper
    def delete_qos(self,*arg,**kwarg):
        qos_uuid = kwarg['uuid']
        connections = kwarg['connection_obj'].connections
        #logger      = kwarg['connection_obj'].logger
        connections.vnc_lib.qos_config_delete(id=qos_uuid)

    def delete_qoss(self,count,conn_obj_list,global_conf):

        qos_list = self.list_qos(tcount=1,conn_obj_list=conn_obj_list)
        kwargs_list = []
        for qos in qos_list:
            kwargs = {}
            kwargs['uuid'] = qos['uuid']
            kwargs_list.append(kwargs)
        if len(kwargs_list):
           self.delete_qos(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

    @wrapper
    def update_conf(self,*arg,**kwarg):
          connection_obj = kwarg['connection_obj']
          global_conf    = kwarg['global_conf']
          update_properties = kwarg.get('update_properties',False)
          if update_properties:
             return
          connections = connection_obj.connections
          #logger      = connection_obj.logger
          global_vr_conf_obj  = connections.vnc_lib.global_vrouter_config_read(fq_name=[u'default-global-system-config', u'default-global-vrouter-config'])

          forwarding_mode = global_conf['forwarding_mode']
          global_vr_conf_obj.set_forwarding_mode(forwarding_mode)

          encap_priority = global_conf['encap_priority']
          if encap_priority:
             encap_prior = EncapsulationPrioritiesType()
             encap_prior.set_encapsulation(encap_priority)
             global_vr_conf_obj.set_encapsulation_priorities(encap_prior)

          ecmp_hashing_list  = global_conf['ecmp_hashing']
          ecmp_hash = EcmpHashingIncludeFields()
          if "destination-ip" in ecmp_hashing_list:
              ecmp_hash.set_destination_ip(True)
          else:
              ecmp_hash.set_destination_ip(False)
          if "ip-protocol" in ecmp_hashing_list:
              ecmp_hash.set_ip_protocol(True)
          else:
              ecmp_hash.set_ip_protocol(False)
          if "source-ip" in ecmp_hashing_list:    
              ecmp_hash.set_source_ip(True)
          else:
              ecmp_hash.set_source_ip(False)
          if "source-port" in ecmp_hashing_list:    
              ecmp_hash.set_source_port(True)
          else:
              ecmp_hash.set_source_port(False)
          if "destination-port" in ecmp_hashing_list:    
              ecmp_hash.set_destination_port(True)
          else:
              ecmp_hash.set_destination_port(False)
          if ecmp_hashing_list:
             global_vr_conf_obj.set_ecmp_hashing_include_fields(ecmp_hash)

          flowing_aging_list = global_conf['flow_aging']
          fl_obj_list = [] 
          for flow_aging in flowing_aging_list:
              fl_obj = FlowAgingTimeout(flow_aging['protocol'],flow_aging['port'],flow_aging['timeout'])
              fl_obj_list.append(fl_obj)
          fl_timeout_obj_list=FlowAgingTimeoutList(fl_obj_list)
          global_vr_conf_obj.set_flow_aging_timeout_list(fl_timeout_obj_list)

          vxlan_identifier_mode = global_conf['vxlan_identifier_mode']
          global_vr_conf_obj.set_vxlan_network_identifier_mode(vxlan_identifier_mode)
          connections.vnc_lib.global_vrouter_config_update(global_vr_conf_obj)
         
          gs_conf_obj = connections.vnc_lib.global_system_config_read(fq_name=[u'default-global-system-config'])
          ip_fab_subnets = global_conf['ip_fab_subnets']
          if ip_fab_subnets:
             ip_fabric_subnet = ip_fab_subnets.split("/")
             obj1 = SubnetListType() 
             obj2 = SubnetType()
             obj2.set_ip_prefix(ip_fabric_subnet[0])
             obj2.set_ip_prefix_len(int(ip_fabric_subnet[1]))
             obj1.add_subnet(obj2)
             gs_conf_obj.set_ip_fabric_subnets(obj1)
          connections.vnc_lib.global_system_config_update(gs_conf_obj)

class Bgpaas(Base):

     @wrapper
     def create(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         vm_id            = kwarg['vm_id']
         service_name     = kwarg['bgpaas,name']
         asn              = kwarg['bgpaas,asn']
         project_obj  = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
         service_fq_name = tenant_fq_name + [service_name]
         bgpaas_obj = None
         try:
            bgpaas_obj = connections.vnc_lib.bgp_as_a_service_read(fq_name=service_fq_name)
         except NoIdError:
            pass
         if bgpaas_obj is None:
            bgpaas_obj = BgpAsAService(name=service_name,parent_obj=project_obj)
            vm_obj = connections.vnc_lib.virtual_machine_read(id=vm_id)
            vmis   = vm_obj.get_virtual_machine_interface_back_refs()
            for vmi in vmis:
                vmi_obj  = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                networks = vmi_obj.get_virtual_network_refs()[0]['to']
                def_dom,t_name,netname = networks
                if re.search('BGP',netname):
                   vmi = vmi_obj
                   break
            inst_ips = vmi.get_instance_ip_back_refs()
            ip_obj = connections.vnc_lib.instance_ip_read(id=inst_ips[0]['uuid'])
            bgpaas_obj.add_virtual_machine_interface(vmi) # vSRX VMI
            bgpaas_obj.set_autonomous_system(asn)
            bgpaas_obj.set_display_name(service_name)
            bgpaas_obj.set_bgpaas_ip_address(ip_obj.get_instance_ip_address()) # get instance IP attached to vmi.
            bgp_addr_fams = AddressFamilies(['inet','inet6'])
            bgp_sess_attrs = BgpSessionAttributes(address_families=bgp_addr_fams,hold_time=300)
            bgpaas_obj.set_bgpaas_session_attributes(bgp_sess_attrs)
            connections.vnc_lib.bgp_as_a_service_create(bgpaas_obj)

     def create_bgpaas(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
        if update_properties:
            return

        bgpaas_name = tenant_conf.get('bgpaas,name',None)
        if bgpaas_name is None:
           return

        kwargs_list = []

        kwargs = {}
        kwargs['tenant_list'] = tenant_list

        vm_obj = VM(None)
        vms = vm_obj.list_vms(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
        
        for tenant in tenant_list:
            found = False
            vm_id = None
            tenant_fq_name = tenant['fq_name']
            for vm in vms:
                if vm['tenant']['fq_name'] != tenant_fq_name or not re.search('bgp.vm',vm['vm_name']):
                   continue
                vm_id = vm['id']
                break
            if vm_id is None:
               continue
            kwargs = {}
            kwargs['tenant']       = tenant
            kwargs['vm_id']        = vm_id
            kwargs['bgpaas,name']  = bgpaas_name
            kwargs['bgpaas,asn']   = tenant_conf['bgpaas,asn']
            kwargs_list.append(kwargs)

        if len(kwargs_list) == 0:
           return

        self.create(tcount=thread_count,conn_obj_list=admin_conn_obj_list,kwargs_list=kwargs_list)

     @wrapper
     def delete(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         tenant           = kwarg['tenant']
         tenant_fq_name   = tenant['fq_name']
         services_list    = connections.vnc_lib.bgp_as_a_services_list()
         if services_list.has_key('bgp-as-a-services'):
            services_list = services_list['bgp-as-a-services']
         else:
            return
         for service in services_list:
             dom,t_name,service_name = service['fq_name']
             if [dom,t_name] != tenant_fq_name:
                continue
             try:
               bgpaas_obj = connections.vnc_lib.bgp_as_a_service_read(id=service['uuid'])
             except NoIdError:
               continue
             vmi_refs = bgpaas_obj.virtual_machine_interface_refs or []
             for vmi in vmi_refs:
                 vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                 bgpaas_obj.del_virtual_machine_interface(vmi_obj)
             connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)
             connections.vnc_lib.bgp_as_a_service_delete(id=bgpaas_obj.get_uuid())

     def delete_bgpaas(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):

        kwargs_list = []

        #vm_obj = VM(None)
        #vms = vm_obj.list_vms(conn_obj_list=conn_obj_list,tenant_list=tenant_list)

        for i,tenant in enumerate(tenant_list):
            #found = False
            #vm_id = None
            #for vm in vms:
            #    if vm['tenant_name'] != tenant_name or not re.search('bgp.vm',vm['vm_name']):
            #       continue
            #    vm_id = vm['id']
            #    break
            #if vm_id is None:
            #   continue
            kwargs = {}
            kwargs['tenant'] = tenant
            #kwargs['vm_id']        = vm_id
            #kwargs['bgpaas,name'] = tenant_conf['bgpaas,name']
            #kwargs['bgpaas,asn']  = tenant_conf['bgpaas,asn']
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return
        self.delete(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

class HostAggregate(Base):

      @wrapper
      def create_host_aggregate(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         quantum_h   = connections.quantum_h
         nova_h = connections.nova_h

         aggr_name = kwarg['aggr_name']
         zone_name = kwarg['zone_name']
         hosts     = kwarg['hosts']

         aggr_obj = nova_h.obj.aggregates.create(aggr_name,zone_name)
         for host in hosts:
              if host == "INVALID_HOST":
                 continue
              nova_h.obj.aggregates.add_host(aggr_obj.id,host)

      def create_host_aggregates(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
        if update_properties:
            return
        host_aggregates = global_conf['host_aggregates']
        kwargs_list = []
        for aggr in host_aggregates:
            kwargs = {}
            kwargs['aggr_name'] = aggr['aggr_name']
            kwargs['zone_name'] = aggr['zone_name']
            kwargs['hosts']     = aggr['hosts']
            kwargs_list.append(kwargs)
        if len(kwargs_list) == 0:
           return

        self.create_host_aggregate(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)

      @wrapper
      def delete_host_aggregate(self,*arg,**kwarg):
         connections = kwarg['connection_obj'].connections
         #logger      = kwarg['connection_obj'].logger
         quantum_h   = connections.quantum_h
         self.nova_h = connections.nova_h
         aggr_list   = self.nova_h.obj.aggregates.list()
         for aggr in aggr_list:
             hosts   = aggr.hosts
             for host in hosts:
                aggr.remove_host(host)
             aggr.delete()

      def delete_host_aggregates(self,conn_obj_list,thread_count,global_conf,tenant_conf):

         self.delete_host_aggregate(tcount=thread_count,conn_obj_list=conn_obj_list)
         
class ServicesConfig(Base):
      @wrapper
      def retrieve_sc_info(self,*arg,**kwarg):
          tenant_list = kwarg['tenant_list']
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          service_chain_info = {}
          for tenant in tenant_list:
             if tenant['fq_name'] == ['default-domain','admin']:
                continue
             tenant_fq_name          = tenant['fq_name']
             domain_name,tenant_name = tenant_fq_name
             service_chain_info[":".join(tenant_fq_name)] = {}
             try:
                proj_obj  = connections.vnc_lib.project_read(fq_name=tenant_fq_name)
             except NoIdError:
                continue
             policys = proj_obj.get_network_policys() or []
             vn_pairs_list = []
             for policy in policys:
                 pol_obj = connections.vnc_lib.network_policy_read(id=policy['uuid']) 
                 pol_rules = pol_obj.get_network_policy_entries().policy_rule
                 vn_dict = {}
                 vn_dict['left'] = []
                 vn_dict['right'] = []
                 for rule in pol_rules:
                     s_net = rule.src_addresses[0].get_virtual_network()
                     d_net = rule.dst_addresses[0].get_virtual_network()
                     if not re.search('Private_SC_Left',s_net):
                        continue
                     vn_dict['left'].append(s_net)
                     vn_dict['right'].append(d_net)
                 if len(vn_dict['left']):
                    vn_pairs_list.append(vn_dict)
             service_chain_info[":".join(tenant_fq_name)]['service-instances'] = vn_pairs_list
          return service_chain_info 
 
      @wrapper
      def create_service_template(self,*arg,**kwarg):
          st_name        = kwarg['st_name']
          domain_name    = kwarg['domain_name']
          st_fq_name     = [domain_name,st_name]
          domain_fq_name = [domain_name]
          image_name     = kwarg['image_name']
          availability_zone = kwarg['availability_zone']
          svc_type       = kwarg['svc_type']
          svc_mode       = kwarg['svc_mode']
          version        = kwarg['version']
          flavor         = kwarg['flavor']
          svc_scaling    = kwarg['svc_scaling']
          ordered_interfaces = kwarg['ordered_interfaces']
          if_list            = kwarg['if_list']
          static_routes      = kwarg['static_routes']
          shared_ip          = kwarg['shared_ip']
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          try:
            svc_template = connections.vnc_lib.service_template_read(fq_name=st_fq_name)
            #logger.warn("Service template: %s already exists"%str(st_fq_name))
            return
          except NoIdError:
            domain = connections.vnc_lib.domain_read(fq_name=domain_fq_name)
            svc_template = ServiceTemplate(name=st_name,parent_obj=domain)
            svc_properties = ServiceTemplateType()
            svc_properties.set_image_name(image_name)
            svc_properties.set_service_type(svc_type)
            svc_properties.set_service_mode(svc_mode)
            svc_properties.set_service_scaling(svc_scaling)
            svc_properties.set_version(version)
            svc_properties.set_availability_zone_enable(bool(availability_zone))
            # Add flavor if not already added
            # self.nova_h.get_flavor(flavor)
            svc_properties.set_flavor(flavor)
            svc_properties.set_service_virtualization_type('virtual-machine')
            svc_properties.set_ordered_interfaces(ordered_interfaces)
            for i,itf in enumerate(if_list):
                if_type = ServiceTemplateInterfaceType(
                    service_interface_type=itf, shared_ip=shared_ip[i],static_route_enable=static_routes[i])
                if_type.set_service_interface_type(itf)
                svc_properties.add_interface_type(if_type)
            svc_template.set_service_template_properties(svc_properties)
            connections.vnc_lib.service_template_create(svc_template)  

      @wrapper
      def create_service_health_check(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger

          tenant          = kwarg['tenant']
          tenant_uuid     = tenant['uuid']
          name            = kwarg['name']
          protocol        = kwarg['protocol']
          monitor_target  = kwarg['monitor_target']
          delay_seconds   = kwarg['delay_seconds']
          timeout_seconds = kwarg['timeout_seconds']
          retries         = kwarg['retries']
          proj_obj = connections.vnc_lib.project_read(id=tenant_uuid)
          hc_obj = ServiceHealthCheck(name = name,parent_obj=proj_obj)
          hc_type_obj = ServiceHealthCheckType()
          hc_type_obj.set_monitor_type(protocol)
          hc_type_obj.set_delay(delay_seconds)
          hc_type_obj.set_timeout(timeout_seconds)
          hc_type_obj.set_max_retries(retries)
          #obj_1.set_http_method
          hc_type_obj.set_url_path(monitor_target)
          hc_obj.set_service_health_check_properties(hc_type_obj)

          connections.vnc_lib.service_health_check_create(hc_obj)

      def create_service_health_checks(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties=False):
          service_health_check = tenant_conf.get('service_health_check',None)
          if not service_health_check:
             return
          kwargs_list = [] 
          for tenant in tenant_list:
              if tenant['fq_name'] == ['default-domain','admin']:
                 continue
              for service_hc in service_health_check:
                  kwargs = copy.deepcopy(service_hc)
                  kwargs['tenant'] = tenant
                  kwargs_list.append(kwargs)

          if len(kwargs_list) == 0:
             return
          self.create_service_health_check(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
            
      @wrapper
      def list_service_health_checks(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          tenant_list      = kwarg['tenant_list']
          tenant_list_t    = map(lambda x:x['fq_name'],tenant_list)
          hc_list = connections.vnc_lib.service_health_checks_list()['service-health-checks'] or []
          hc_info = {}
          for hc in hc_list:
              domain,tenant_name,hc_name = hc['fq_name']
              if [domain,tenant_name] not in tenant_list_t:
                 continue
              hc_info[":".join(hc['fq_name'])] = hc['uuid']
              
          return hc_info

      @wrapper
      def delete_service_health_check(self,*arg,**kwarg):
          connections = kwarg['connection_obj'].connections
          #logger      = kwarg['connection_obj'].logger
          hc_uuid          = kwarg['uuid']
          hc_obj = connections.vnc_lib.service_health_check_read(id=hc_uuid)
          si_ref = hc_obj.get_service_instance_refs() or []
          for si in si_ref:
              si_obj = connections.vnc_lib.service_instance_read(id=si['uuid'])
              hc_obj.del_service_instance(si_obj)
          connections.vnc_lib.service_health_check_update(hc_obj)
          connections.vnc_lib.service_health_check_delete(id=hc_uuid)

      def delete_service_health_checks(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties=False):
          kwargs = {}
          kwargs['tenant_list'] = tenant_list
          hc_info_dict = self.list_service_health_checks(conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
          tenant_list_t  = map(lambda x:x['fq_name'],tenant_list)
          kwargs_list = []
          for hc_name,hc_uuid in hc_info_dict.iteritems():
              domain_name,tenant_name,hc_name = hc_name.split(":")
              if [domain_name,tenant_name] == ['default-domain','admin']:
                 continue
              kwargs = {}
              kwargs['uuid']    = hc_uuid
              kwargs_list.append(kwargs)

          if len(kwargs_list) == 0:
             return
          self.delete_service_health_check(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)

      def create_service_templates(self,conn_obj_list,thread_count,global_conf,tenant_conf,update_properties=False):
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
              kwargs['version']            = st['version']
              kwargs['image_name']         = st['image_name']
              kwargs['flavor']             = st['instance_flavor']
              kwargs['if_list']            = st['interface_list']
              kwargs['static_routes']      = st.get('static_routes',[False,False,False])
              kwargs['shared_ip']          = st.get('shared_ip',[False,False,False])
              kwargs['availability_zone']  = st['availability_zone']
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          self.create_service_template(tcount=1,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)
         
      @wrapper
      def create_service_instance(self,*arg,**kwarg):
       try:
          update_properties = kwarg['update_properties']
          svc_mode      = kwarg['service_mode']
          svc_scaling   = kwarg['service_scaling']
          st_name       = kwarg['service_template_name']
          si_name       = kwarg['si_name']
          ha_mode       = kwarg['ha_mode']
          az_name       = kwarg['az_name']
          host_name     = kwarg['host_name']
          tenant        = kwarg['tenant']
          tenant_fq_name = tenant['fq_name']
          tenant_uuid    = tenant['uuid']
          domain_name,tenant_name = tenant_fq_name
          si_fq_name    = tenant_fq_name + [si_name]
          st_fq_name    = ['default-domain',st_name]
          max_inst      = kwarg['num_of_instances']
          interface_order = kwarg['interface_order']
          if_vn_dict      = kwarg['if_vn_dict']
          if isinstance(if_vn_dict,list):
             if_vn_dict = if_vn_dict[0]
          if_vn_dict1      = kwarg['if_vn_dict1']
          if isinstance(if_vn_dict1,list):
             if_vn_dict1 = if_vn_dict1[0]
          vn_id_dict      = kwarg['vn_id_dict']
          left_vn_name    = if_vn_dict.get('left',None)
          right_vn_name   = if_vn_dict.get('right',None)
          left1_vn_name   = if_vn_dict1.get('left',left_vn_name)
          right1_vn_name  = if_vn_dict1.get('right',right_vn_name)
          mgmt_vn_name    = if_vn_dict.get('management',None)
          left_vn_id      = vn_id_dict.get(left_vn_name,None)
          right_vn_id     = vn_id_dict.get(right_vn_name,None)
          mgmt_vn_id      = vn_id_dict.get(mgmt_vn_name,None)
          si_version      = kwarg['service_instance_version']
          si_image        = kwarg['service_instance_image']
          si_flavor       = kwarg['service_instance_flavor']
          
          connections = kwarg['connection_obj'].connections
          connections.inputs.availability_zone = az_name
          quantum_h = connections.quantum_h
          st_route_dict    = kwarg['if_static_route_dict']
          rt_comm_dict     = kwarg['if_route_comm_dict']
          if_st_route_list = []
          if_route_comm_list = []
          for iface in interface_order:
              if_st_route_list.append(st_route_dict[iface])
          if not if_st_route_list:
              if_st_route_list = [None,None,None]
          for iface in interface_order:
              if_route_comm_list.append(rt_comm_dict[iface])
          if not if_route_comm_list:
              if_route_comm_list = [None,None,None]
          if svc_scaling == True:
            if svc_mode == 'in-network-nat':
                if_d = {}
                if_d['left']       = ['left', True, False]
                if_d['right']      = ['right', False, False]
                if_d['management'] = ['management', False, False]
            else:
                if_d = {}
                if_d['left']       = ['left', True, False]
                if_d['right']      = ['right', True, False]
                if_d['management'] = ['management', False, False]
          else:
                if_d = {}
                if_d['left']       = ['left', False, False]
                if_d['right']      = ['right', False, False]
                if_d['management'] = ['management', False, False]
          if_list = []
          for iface in interface_order:
              if_list.append(if_d[iface])
          try:
            si_obj = connections.vnc_lib.service_instance_read(fq_name=si_fq_name)
          except NoIdError:
            si_obj = None
          
          if update_properties and si_obj:
             si_prop          = si_obj.get_service_instance_properties()
             current_max_inst = si_prop.get_scale_out()
             change_config = False
             if max_inst != current_max_inst:
                change_config = True
                si_prop.set_scale_out(ServiceScaleOutType(max_inst))
                si_obj.set_service_instance_properties(si_prop)
             if change_config:
                si_obj.set_service_instance_properties(si_prop)
                connections.vnc_lib.service_instance_update(si_obj)

          if si_obj:
             return

          st_obj = connections.vnc_lib.service_template_read(fq_name=st_fq_name)
          if_details = {}
          if_details['left'] = {}
          if_details['left']['vn_name']=left_vn_name
          if_details['right'] = {}
          if_details['right']['vn_name']=right_vn_name
          if_details['management'] = {}
          if_details['management']['vn_name']=mgmt_vn_name
          az_name='AZ1'
          fixture = SvcInstanceFixture(
                connections=connections, 
                si_name=si_name,
                svc_template=st_obj,
                if_details = if_details,
                max_inst=max_inst,
                static_route = st_route_dict,
                availability_zone = az_name
                )
		#route_community=if_route_comm_list,host_name=host_name,ha_mode=ha_mode)
          try:
            fixture.max_instances = max_inst
            fixture.setUp()
          except RefsExistError:
            pass
          si_obj = fixture.si_obj
          si_vms = None
          if int(si_version) == 2:
             #connections.project_name        = tenant_name
             #connections.inputs.project_name = tenant_name
             vm_ids = []
             for vm_indx in range(max_inst):
                 vm_fixture = VM(None)
                 vm_fixture = VMFixture(connections=connections, vm_name="si-vm-%s-%d"%(si_name,vm_indx), image_name=si_image,zone=az_name)
                 vm_fixture.flavor = si_flavor
                 vm_fixture.vn_ids = [left_vn_id,right_vn_id,mgmt_vn_id]
                 left_vn_obj = quantum_h.get_vn_obj_if_present(left_vn_name.split(":")[-1])
                 right_vn_obj = quantum_h.get_vn_obj_if_present(right_vn_name.split(":")[-1])
                 mgmt_vn_obj = quantum_h.get_vn_obj_if_present(mgmt_vn_name.split(":")[-1])
                 vm_fixture.vn_objs = [left_vn_obj,right_vn_obj,mgmt_vn_obj]
                 vm_fixture.setUp()
                 vm_fixture.get_uuid()
                 vm_ids.append(vm_fixture.vm_obj.id)
             time.sleep(60)
             st_uuid  = si_obj.get_service_template_refs()[0]['uuid']
             st_obj   = connections.vnc_lib.service_template_read(id=st_uuid)
             st_props = st_obj.get_service_template_properties()
             if_list  = st_props.get_interface_type()
             for vm_indx in range(max_inst):
                 pt_obj  = PortTuple(name=u'pt_%s_%d'%(si_name,vm_indx), parent_obj=si_obj)
                 pt_uuid = connections.vnc_lib.port_tuple_create(pt_obj)
                 vm_id   = vm_ids[vm_indx]
                 vm_obj  = connections.vnc_lib.virtual_machine_read(id=vm_id)
                 vmis    = vm_obj.get_virtual_machine_interface_back_refs()
                 for vmi in vmis:
                     vmi_id = vmi['uuid']
                     vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi_id)
                     nw_name = vmi_obj.virtual_network_refs[0]['to']
                     dom,tname,network_name = nw_name
                     if tname == 'admin':
                        service_interface_type = "management"
                     elif re.search('left',network_name,re.I):
                        service_interface_type = "left"
                     else:
                        service_interface_type = "right"

                     vmi_props = VirtualMachineInterfacePropertiesType()
                     vmi_props.set_service_interface_type(service_interface_type)
                     vmi_obj.set_virtual_machine_interface_properties(vmi_props)
                     vmi_obj.add_port_tuple(pt_obj)
                     connections.vnc_lib.virtual_machine_interface_update(vmi_obj)
          else:
             #for i in xrange(60):
             #    si_vms = si_obj.get_virtual_machine_back_refs()
             #    if si_vms is None:
             #       print "waiting for SI vm to come up.."
             #       time.sleep(1)
             #       continue
             #if si_vms is None:
             #   print "ERROR: SI vms did not come up.."
             #   return
             #print "SI_VMs:",si_vms
             time.sleep(60)
             si_vms = si_obj.get_virtual_machine_back_refs() or []
             for si_vm in si_vms:
                 si_vm_obj = connections.vnc_lib.virtual_machine_read(id=si_vm['uuid'])
                 vmi_ref   = si_vm_obj.get_virtual_machine_interface_back_refs() or []
                 mgmt_vmi  = None
                 for vmi in vmi_ref:
                     dom,tname,vmi_name = vmi['to']
                     if re.search('left|right',vmi_name):
                        vmi_obj = connections.vnc_lib.virtual_machine_interface_read(id=vmi['uuid'])
                        inst_ips  = vmi_obj.get_instance_ip_back_refs()
                        ip_obj    = connections.vnc_lib.instance_ip_read(id=inst_ips[0]['uuid'])
                        vmi_addr = ""
                        while vmi_addr == "":
                           print "vmi ip is None...trying.."
                           vmi_addr = ip_obj.get_instance_ip_address()
                           time.sleep(1)
                           print "vmi ip:",vmi_addr
                        print "vmi ip is %s ...done.."%vmi_addr

          health_check = kwarg['health_check']
         
          if health_check:
             health_check_name = health_check['name']
             health_check_interface_type = health_check['interface_type'] 
             health_check_fq_name_str    =":".join([domain_name,tenant_name,health_check_name])
             health_check_uuid           = kwarg['health_check_ids'][health_check_fq_name_str]
             hc_obj = connections.vnc_lib.service_health_check_read(id=health_check_uuid)
             iface_tag = ServiceInterfaceTag()
             iface_tag.set_interface_type(health_check_interface_type)
             hc_obj.add_service_instance(si_obj, iface_tag)
             connections.vnc_lib.service_health_check_update(hc_obj)
          return
       except:
          traceback.print_exc(sys.stdout)
          import pdb;pdb.set_trace()

      def retrieve_service_template_config(self,service_templates,st_name):
          for st in service_templates:
              if st['name'] == st_name:
                 return st
          return None

      @timeit
      def create_service_instances(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties,dpdk):
          service_instances = tenant_conf.get('service_instances',None)
          service_templates = global_conf.get('service_templates',None)
          serial_service_chain  = tenant_conf.get('serial_service_chain',[])
          if len(serial_service_chain):
             serial_service_chain_count = serial_service_chain[0]['count']
             serial_service_chain_si_groups = []
             for si_group in serial_service_chain[0]['instances']:
                 serial_service_chain_si_groups.append(si_group['name'])
          else:
             serial_service_chain_count = 0
             serial_service_chain_si_groups = []

          parallel_service_chain  = tenant_conf.get('parallel_service_chain',[])
          if len(parallel_service_chain):
             parallel_service_chain_count = parallel_service_chain[0]['count']
             parallel_service_chain_si_groups = []
             for si_group in parallel_service_chain[0]['instances']:
                 parallel_service_chain_si_groups.append(si_group['name'])
          else:
             parallel_service_chain_count = 0
             parallel_service_chain_si_groups = []

          if service_templates is None or service_instances is None:
             return
          kwargs_list = []
          policy_info_list = []

          service_instances_serial   = []
          service_instances_parallel = []
          service_instances_single   = [] 
          standalone_si_count = 0
          for i in xrange(len(service_instances)):
              si_group = service_instances.pop()
              configure = si_group.get('configure',True)
              if configure == False:
                 continue
              if si_group['name'] in serial_service_chain_si_groups:
                 service_instances_serial.append(si_group)
              elif si_group['name'] in parallel_service_chain_si_groups:
                 service_instances_parallel.append(si_group)
              else:
                 try:
                    left_vn_count = si_group['interfaces']['left']['count']
                 except:
                    left_vn_count = 1
                 standalone_si_count += si_group.get('count',1) * left_vn_count
                 service_instances_single.append(si_group)
          service_instances = service_instances_serial + service_instances_parallel + service_instances_single
          vn_count = serial_service_chain_count + parallel_service_chain_count + standalone_si_count

          vn_id_dict = {}
          kwargs = {}
          kwargs['tenant_list'] = tenant_list
          vn_obj = VN(None)
          ret = vn_obj.get_vn_ids(tcount=1,conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])
          if ret:
             vn_id_dict.update(ret)

          health_check_ids = self.list_service_health_checks(conn_obj_list=admin_conn_obj_list,kwargs_list=[kwargs])

          host_aggregates = global_conf['host_aggregates']
          zone_hosts_dict = {}
          for host_aggr in host_aggregates:
              zone_name = host_aggr['zone_name'] 
              hosts     = host_aggr['hosts']
              zone_hosts_dict[zone_name] = hosts
          non_dpdk_zone_name = global_conf['non_dpdk_config'][0]['zone_name']
          non_dpdk_hosts = zone_hosts_dict[non_dpdk_zone_name]
          dpdk_zone_name = global_conf['dpdk_config'][0]['zone_name']
          dpdk_hosts = zone_hosts_dict[dpdk_zone_name]
          for tenant in tenant_list:
            if tenant['fq_name'] == ['default-domain','admin']:
               continue
            tenant_fq_name = tenant['fq_name']
            trans_auto_vn_index_l = 0
            trans_auto_vn_index_r = 0
            tenant_indx       = get_tenant_index(tenant_conf,tenant_fq_name)
            vn_index = 0
            service_instance_info_d = {}
            for si in service_instances:
                si_group_list = []
                si_group_name = si['name']
                if si_group_name in serial_service_chain_si_groups:
                   si_count = serial_service_chain_count
                   vn_index = 0
                elif si_group_name in parallel_service_chain_si_groups:
                   si_count = parallel_service_chain_count
                   vn_index = serial_service_chain_count
                else:
                   si_count = si.get('count',1)
                   if vn_index < serial_service_chain_count + parallel_service_chain_count:
                      vn_index = serial_service_chain_count + parallel_service_chain_count
                try:
                  vn_count = si['interfaces']['left']['count']
                except:
                  vn_count = 1
                for si_indx in xrange(si_count):
                    kwargs = {}
                    si_name                      = generate_si_name(si['name'],si_indx)
                    kwargs['si_name']            = si_name
                    kwargs['tenant']             = tenant
                    if dpdk:
                       st_name = si['service_template_name'] + "-dpdk"
                    else:
                       st_name = si['service_template_name']
                    kwargs['service_template_name'] = st_name
                    kwargs['num_of_instances']      = si['num_of_instances']
                    st = self.retrieve_service_template_config(service_templates,st_name)
                    
                    kwargs['service_instance_version'] = st['version']
                    kwargs['service_instance_image']   = st['image_name']
                    kwargs['service_instance_flavor']  = st['instance_flavor']
                    kwargs['service_mode']          = st['service_mode']
                    kwargs['service_scaling']       = st['scaling']
                    kwargs['ha_mode']               = si['HA-mode']
                    #kwargs['az_name']               = si.get('AZ','ANY')
                    #kwargs['host_name']             = si.get('host','ANY')
                    if dpdk:
                       az_name = global_conf['dpdk_config'][0]['zone_name']
                       host_name = random.choice(dpdk_hosts)
                    else:
                       az_name = si.get('AZ',None)
                       if az_name is None:
                          az_name = global_conf['non_dpdk_config'][0]['zone_name']
                       host_name = si.get('host_name',None)
                       if host_name is None:
                          host_name = random.choice(non_dpdk_hosts)
                    kwargs['az_name'] = az_name
                    kwargs['host_name'] = host_name
                    kwargs['interface_order']       = st['interface_list']
                    kwargs['vn_id_dict']            = vn_id_dict
                    kwargs['health_check']          = si.get('service_health_check',False)
                    kwargs['health_check_ids']      = health_check_ids
                    interfaces                      = si['interfaces']
                    vn_pair_list = []
                    vn_pair_list1 = []
                    for indx in xrange(vn_count):
                      if_vn_dict = {}
                      if_vn_dict1 = {}
                      if_static_route_dict = {}
                      if_route_comm_dict   = {} 
                      for interface_type in ['management','left','right']:
                        iface = interfaces.get(interface_type,None)
                        if iface is None:
                           continue
                        vn_name = iface['vn_name']
                        auto_configured = iface.get('auto_configured',False)
                        if interface_type in ['left','right'] :
                           vn_name = generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name,vn_index)
                           vn_fq_name = tenant_fq_name + [vn_name]
                           vn_fq_name_str = ":".join(vn_fq_name)
                           if_vn_dict1[interface_type] = vn_fq_name_str
                           if auto_configured and int(st['version']) == 1:
                              vn_name = ""
                              if_vn_dict[interface_type] = vn_name
                           elif auto_configured and int(st['version']) == 2:
                              vn_name = iface['auto_vn_name']
                              if interface_type == 'left':
                                 trans_auto_vn_index = trans_auto_vn_index_l
                              else:
                                 trans_auto_vn_index = trans_auto_vn_index_r
                              vn_name = generate_vn_name(global_conf,tenant_conf,tenant_indx,vn_name,trans_auto_vn_index)
                              vn_fq_name = tenant_fq_name + [vn_name]
                              vn_fq_name_str = ":".join(vn_fq_name)
                              if interface_type == 'left':
                                 trans_auto_vn_index_l += 1
                              else:
                                 trans_auto_vn_index_r += 1
                              if_vn_dict[interface_type] = vn_fq_name_str
                           else:
                              if_vn_dict[interface_type] = vn_fq_name_str
                        else:
                           vn_name = "default-domain:admin:%s"%vn_name
                           if_vn_dict[interface_type] = vn_name
                           if_vn_dict1[interface_type] = vn_name
                        static_routes   = iface.get('static_routes',[])
                        static_routes_l = []
                        route_comm_l    = []
                        for route in static_routes:
                            pref  = route['prefix']
                            count = route['subnet_count'] or 0
                            if count == 0:
                               continue
                            static_routes_l.append(pref)
                            next_r = pref
                            for cnt in xrange(count):
                                route_comm_l.append(route['community'])
                            for cnt in xrange(count-1):
                               next_r = IPNetwork(next_r).next()
                               static_routes_l.append(str(next_r))
                        if_static_route_dict[interface_type] = static_routes_l
                        if_route_comm_dict[interface_type]   = route_comm_l
                      vn_pair_list.append(if_vn_dict)
                      vn_pair_list1.append(if_vn_dict1)
                      vn_index += 1
                    kwargs['if_vn_dict']  = vn_pair_list
                    kwargs['if_vn_dict1'] = vn_pair_list1
                    kwargs['if_static_route_dict'] = if_static_route_dict
                    kwargs['if_route_comm_dict']   = if_route_comm_dict
                    kwargs['update_properties']    = update_properties
                    kwargs_list.append(kwargs)
                    si_group_list.append(kwargs)
                service_instance_info_d[si_group_name] = si_group_list
          if len(kwargs_list) == 0:
             return
          self.create_service_instance(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
          if update_properties:
             return
          serial_chain_info_list = []
          for sc in serial_service_chain:
             count = sc['count']
             insts = sc['instances'] 
             for ci in xrange(count):
                 chain_info = []
                 for inst in insts:
                     inst_group = service_instance_info_d[inst['name']] 
                     chain_info.append(inst_group[ci])
                 serial_chain_info_list.append(chain_info)

          parallel_chain_info_list = []
          for sc in parallel_service_chain:
             count = sc['count']
             insts = sc['instances'] 
             for ci in xrange(count):
                 chain_info = []
                 for inst in insts:
                     inst_group = service_instance_info_d[inst['name']] 
                     chain_info.append(inst_group[ci])
                 parallel_chain_info_list.append(chain_info)

          parallel_protocol_info   = []
          for sc in parallel_service_chain:
             insts = sc['instances'] 
             for inst in insts:
                 parallel_protocol_info.append(inst['protocol'])

          serial_chain_si_list = sum(serial_chain_info_list,[])      
          parallel_chain_si_list = sum(parallel_chain_info_list,[])      
          si_all = sum(service_instance_info_d.values(),[])
          diff = lambda l1,l2: filter(lambda x: x not in l2, l1)
          si_single1 = diff(si_all,serial_chain_si_list)
          si_single = diff(si_single1,parallel_chain_si_list)
          create_policy_kwargs_list = []
          
          for si in si_single:
              tenant = si['tenant']
              tenant_fq_name = tenant['fq_name']
              service_name   = si['si_name']
              service_fq_name = tenant_fq_name + [service_name]
              service_fq_name_str = ":".join(service_fq_name)
              policy_name  = service_name + ".pol"
              src_port = "any"
              dst_port = "any"
              policy_rules = []
              for if_vn_dict in si['if_vn_dict1']:
                  src_nw = if_vn_dict['left']
                  dst_nw = if_vn_dict['right']
                  rule = {
                           'direction': '<>', 'simple_action': 'pass',
                           'protocol': 'any',
                           'src_ports': '%s'%src_port, 'dst_ports': '%s'%dst_port,
                           'source_network': '%s'%src_nw, 'dest_network': '%s'%dst_nw,
                           'action_list':{'apply_service':[service_fq_name_str]}
                       }
                  policy_rules.append(rule)
              kwargs = {}
              kwargs['tenant']      = tenant
              kwargs['policy_name'] = policy_name
              kwargs['rules']       = policy_rules
              create_policy_kwargs_list.append(kwargs)

          for indx,si_l in enumerate(serial_chain_info_list):
              si           = si_l[0]
              tenant = si['tenant']
              tenant_fq_name = tenant['fq_name']
              si_name_l = []
              for si in si_l:
                  service_name     = si['si_name']
                  service_fq_name  = tenant_fq_name + [service_name]
                  service_name_str = ":".join(service_fq_name)
                  si_name_l.append(service_name_str)
              service_name = si['si_name']
              policy_name  = "serial_sc.%d.pol"%indx
              if_vn_dict   = si['if_vn_dict1']
              if isinstance(if_vn_dict,list):
                 if_vn_dict = if_vn_dict[0]
              src_nw = if_vn_dict['left']
              dst_nw = if_vn_dict['right']
              src_port = "any"
              dst_port = "any"
              policy_rules = []
              rule = {
                       'direction': '<>', 'simple_action': 'pass',
                       'protocol': 'any',
                       'src_ports': '%s'%src_port, 'dst_ports': '%s'%dst_port,
                       'source_network': '%s'%src_nw, 'dest_network': '%s'%dst_nw,
                       'action_list':{'apply_service':si_name_l}
                   }
              policy_rules.append(rule)
              kwargs = {}
              kwargs['policy_name'] = policy_name
              kwargs['tenant']      = tenant
              kwargs['rules']       = policy_rules
              create_policy_kwargs_list.append(kwargs)

          for indx,si_l in enumerate(parallel_chain_info_list):
              si           = si_l[0]
              tenant       = si['tenant']
              tenant_fq_name = tenant['fq_name']
              si_name_l = []
              policy_name  = "parallel_sc.%d.pol"%indx
              if_vn_dict   = si['if_vn_dict1']
              if isinstance(if_vn_dict,list):
                 if_vn_dict = if_vn_dict[0]
              src_nw = if_vn_dict['left']
              dst_nw = if_vn_dict['right']
              src_port = "any"
              dst_port = "any"
              policy_rules = []
              for indxl,si in enumerate(si_l):
                  service_name        = si['si_name']
                  service_fq_name     = tenant_fq_name + [service_name]
                  service_fq_name_str = ":".join(service_fq_name)
                  proto = parallel_protocol_info[indxl]
                  rule = {
                       'direction': '<>', 'simple_action': 'pass',
                       'protocol': '%s'%proto,
                       'src_ports': '%s'%src_port, 'dst_ports': '%s'%dst_port,
                       'source_network': '%s'%src_nw, 'dest_network': '%s'%dst_nw,
                       'action_list':{'apply_service':[service_fq_name_str]}
                  }
                  policy_rules.append(rule)
              kwargs = {}
              kwargs['tenant']      = tenant
              kwargs['policy_name'] = policy_name
              kwargs['rules']       = policy_rules
              create_policy_kwargs_list.append(kwargs)
          if len(create_policy_kwargs_list) != 0:
             kwargs = {'kwargs_list': create_policy_kwargs_list } if len(create_policy_kwargs_list) > 1 else create_policy_kwargs_list[0]
             policy_obj = Policy(None)
             policy_obj.create_policy(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=create_policy_kwargs_list)

          attach_policy_kwargs_list = []
          for si in si_single:
            if_vn_dict = si['if_vn_dict1']
            if not isinstance(if_vn_dict,list):
              if_vn_dict = [if_vn_dict]
            for vn_dict in if_vn_dict:
              kwargs = {}
              kwargs['tenant']      = si['tenant']
              kwargs['policy_name'] = si['si_name'] + ".pol"
              kwargs['vn_fq_name']  = vn_dict['left'].split(":")
              attach_policy_kwargs_list.append(kwargs)
              kwargs = {}
              kwargs['tenant']      = si['tenant']
              kwargs['policy_name'] = si['si_name'] + ".pol"
              kwargs['vn_fq_name']  = vn_dict['right'].split(":")
              attach_policy_kwargs_list.append(kwargs)

          for indx,si_l in enumerate(serial_chain_info_list):
           for si in si_l:
              kwargs = {}
              kwargs['tenant']      = si['tenant']
              kwargs['policy_name'] = "serial_sc.%d.pol"%indx
              if_vn_dict = si['if_vn_dict1']
              if isinstance(if_vn_dict,list):
                 if_vn_dict = if_vn_dict[0]
              kwargs['vn_fq_name']  = if_vn_dict['left'].split(":")
              attach_policy_kwargs_list.append(kwargs)
              kwargs = {}
              kwargs['tenant'] = si['tenant']
              kwargs['policy_name'] = "serial_sc.%d.pol"%indx
              kwargs['vn_fq_name']  = if_vn_dict['right'].split(":")
              attach_policy_kwargs_list.append(kwargs)

          for indx,si_l in enumerate(parallel_chain_info_list):
           for si in si_l:
              kwargs = {}
              kwargs['tenant']      = si['tenant']
              kwargs['policy_name'] = "parallel_sc.%d.pol"%indx
              if_vn_dict = si['if_vn_dict1']
              if isinstance(if_vn_dict,list):
                 if_vn_dict = if_vn_dict[0]
              kwargs['vn_fq_name']  = if_vn_dict['left'].split(":")
              attach_policy_kwargs_list.append(kwargs)
              kwargs = {}
              kwargs['tenant'] = si['tenant']
              kwargs['policy_name'] = "parallel_sc.%d.pol"%indx
              kwargs['vn_fq_name']  = if_vn_dict['right'].split(":")
              attach_policy_kwargs_list.append(kwargs)

          if len(attach_policy_kwargs_list) != 0:
             kwargs = {'kwargs_list': attach_policy_kwargs_list } if len(attach_policy_kwargs_list) > 1 else attach_policy_kwargs_list[0]
             policy_obj = Policy(None)
             policy_obj.attach_policy(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=attach_policy_kwargs_list)

      @wrapper
      def delete_service_instance(self,*arg,**kwarg):
          tenant   = kwarg['tenant']          
          tenant_fq_name = tenant['fq_name']
          connections = kwarg['connection_obj'].connections
          domain_name,tenant_name = tenant_fq_name
          si = connections.vnc_lib.service_instances_list() 
          if si.has_key('service-instances'):
             service_instances = si['service-instances']
          else:
             return
          for service_instance in service_instances:
             dom,t_name,si_name = service_instance['fq_name']
             if [dom,t_name] == tenant_fq_name:
                uuid = service_instance['uuid']
                print "INFO: deleting SI : %s,%s"%(str(si_name),uuid)
                try:
                  connections.vnc_lib.service_instance_delete(id=uuid)
                except:
                  print "INFO: error-deleting SI:%s,ID:%s does not exist"%(str(si_name),uuid)

      def delete_service_instances(self,admin_conn_obj_list,proj_conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list):
          kwargs_list = []
          for tenant in tenant_list:
              if tenant['fq_name'] == ['default-domain','admin']:
                 continue
              kwargs = {}
              kwargs['tenant'] = tenant
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          self.delete_service_instance(tcount=thread_count,conn_obj_list=proj_conn_obj_list,kwargs_list=kwargs_list)
 
      @wrapper
      def create_static_route(self,*arg,**kwarg):
          tenant   = kwarg['tenant']          
          connections = kwarg['connection_obj'].connections

      def create_static_routes(self,conn_obj_list,thread_count,global_conf,tenant_conf,tenant_list,update_properties):
          if update_properties:
             return
          kwargs_list = []
          for tenant in tenant_list:
              if tenant['fq_name'] == ['default-domain','admin']:
                 continue
              kwargs = {}
              kwargs['tenant'] = tenant
              kwargs_list.append(kwargs)
          if len(kwargs_list) == 0:
             return
          self.create_static_route(tcount=thread_count,conn_obj_list=conn_obj_list,kwargs_list=kwargs_list)
