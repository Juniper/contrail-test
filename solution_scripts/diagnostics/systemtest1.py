import pdb

import re
from netaddr import IPNetwork
import ipaddr
import sys
import string
import argparse
from tcutils.cfgparser import parse_cfg_file
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import  yaml
from config import *
import os

from vdns_fixture import *

from novaclient import exceptions as nova_exceptions
from keystoneclient.v2_0 import client as kclient
from novaclient import client as nova_client
from neutronclient.neutron import client as neutron_client

OS_USERNAME    = os.environ['OS_USERNAME']
OS_PASSWORD    = os.environ['OS_PASSWORD']
OS_TENANT_NAME = os.environ['OS_TENANT_NAME']
OS_AUTH_URL    = os.environ['OS_AUTH_URL']

def parse_yaml_cfg_file(conf_file):
  
   fp = open(conf_file,"r")
   conf = yaml.load(fp)

   return conf

class CIDR:

  def __init__(self,cidr):
   self.cidr = cidr

  def get_next_cidr(self):
    ip = IPNetwork(self.cidr)[0]
    new_ip = ipaddr.IPAddress(ip) + 256
    self.cidr = str(new_ip) + "/24"
    return self.cidr
  
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


class Tenant :
   
    def __init__(self):
       self.tenant_id = None

    def set_tenant_id(self,tenant_id):
       self.tenant_id = tenant_id

class virtual_network:

   def __init__(self,conf):
       self.vn_id = None
       self.vn_name = None

   def set_network_id(self,vn_id):
       self.vn_id = vn_id


class subnet:

   def __init__(self,conf):
      self.subnet_id = None
      self.cidr = None

   def set_subnet_id(self,subnet_id):
       self.subnet_id = subnet_id

class virtual_machines:

   def __init__(self,vm_name,tenant_id,network_id,subnet_id):
       self.set_tenant_id(tenant_id)
       self.set_network_id(network_id)
       self.set_subnet_id(subnet_id)
       self.vm_role = "client"
       self.vm_name = vm_name

   def print_params(self):
       print "TenantID:%s,NetworkID:%s,VM_Role:%s,VM_Name:%s"%(self.tenant_id,self.vn_id,self.vm_role,self.vm_name)
    
def setup_test_infra(testbed_file):
    global mylogger,inputs
    import logging
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('SystemTest')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit(testbed_file, logger=mylogger)
    inputs.setUp()
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections


def parse_cli(args):

    parser = argparse.ArgumentParser(description=__doc__)
    return dict(parser.parse_known_args(args)[0]._get_kwargs())

class Openstack(object):

  def __init__(self,auth_url,username,password,tenant,auth_token=None):

     self.keystone_client = kclient.Client(username=username,
                                   password=password,
                                   tenant_name=tenant,
                                   auth_url=auth_url)

     if not auth_token:
       auth_token = self.keystone_client.auth_token

     self.nova_client = nova_client.Client('2',  auth_url=auth_url,
                                       username=username,
                                       api_key=password,
                                       project_id=tenant,
                                       auth_token=auth_token,
                                       insecure=True)
     ''' Get neutron client handle '''
     self.neutron_client = neutron_client.Client('2.0',
                                             auth_url=auth_url,
                                             username=username,
                                             password=password,
                                             tenant_name=tenant,
                                             insecure=True)

def get_mysql_token():

    fptr = open("/etc/contrail/mysql.token","r")
    return fptr.readline().strip()


class Test(object):

    def __init__(self,global_conf,test_conf):

        self.global_conf = global_conf
        self.test_conf = test_conf
        self.connections = setup_test_infra(global_conf['ENV']['testbed_file'])
        self.uuid = dict()
        self.tenant_ids = list()
        self.vm_connections_map = dict()
        self.ostack_admin_obj = Openstack(OS_AUTH_URL,OS_USERNAME,OS_PASSWORD,OS_TENANT_NAME)

        self.mysql_passwd = get_mysql_token()

    @retry(delay=60, tries=30)
    def wait_until_vms_deleted(self,tenant_id):

        vm_list = self.ostack_admin_obj.nova_client.servers.list(search_opts={'all_tenants': 1})
        print "VM_list:",vm_list
        vm_to_be_deleted = []

        for vm in vm_list:
            vm_id = vm.id
            if vm.tenant_id == re.sub("-","",tenant_id) :
               vm_to_be_deleted.append(vm)

        if len(vm_to_be_deleted) == 0 :
           return True
        else:
           return False

    def delete_vms(self,tenant_id):

        vm_list = self.ostack_admin_obj.nova_client.servers.list(search_opts={'all_tenants': 1})
        print "VM_list:",vm_list
        vm_to_be_deleted = []

        for vm in vm_list:
            vm_id = vm.id
            #print vm.tenant_id,tenant_id
            if vm.tenant_id == re.sub("-","",tenant_id) :
               vm_to_be_deleted.append(vm)

        for vm in vm_to_be_deleted:
            vm_id = vm.id
            print "deletingvm:%s"%str(vm_id)
            self.ostack_admin_obj.nova_client.servers.delete(vm_id) 

        self.wait_until_vms_deleted(tenant_id)

    def cleanup(self,tenant_obj,tenant_id):

        net_list = self.ostack_admin_obj.neutron_client.list_networks()['networks']
        subnet_list = self.ostack_admin_obj.neutron_client.list_subnets()['subnets']
        port_list = self.ostack_admin_obj.neutron_client.list_ports()['ports']

        self.delete_vms(tenant_id)
    
        for subnet in subnet_list :
           if subnet["tenant_id"] == re.sub("-","",tenant_id) :
              print "Name:",subnet['name']
              subnet_id = subnet['id']
              self.ostack_admin_obj.neutron_client.delete_subnet(subnet_id)

        for net in net_list :
           if net["tenant_id"] == re.sub("-","",tenant_id) :
              print "Name:",net['name']
              net_id = net['id']
              self.ostack_admin_obj.neutron_client.delete_network(net_id)

        tenant_obj.delete(tenant_id)

    def create_vm(self,tenant_name,vm_name,shared_vn_id,vn_id,image):
         
        self.connections.inputs.project_name = tenant_name
        self.connections.project_name = tenant_name

        self.connections.inputs.stack_tenant = tenant_name

        vm_obj = VM(self.connections)
        vm_obj.flavor=5
        vm_obj.zone="nova"
        #vm_obj.sg_ids=["4dd30150-f3ff-43d9-afcc-102df8dc658a"]
        
        print "VM:",vm_name,vn_id,image,shared_vn_id,vn_id
        vm_id  = vm_obj.create(vm_name,[shared_vn_id,vn_id],image)
        return vm_id

    def setUp(self):

        tenants = self.test_conf['tenants'][0]
        tenant_count = tenants['count'] 
        vns_count    = tenants['virtual_networks'][0]['count'] 
        subnet_count = tenants['virtual_networks'][0]['subnets'][0]['count']
        vm_count     = tenants['virtual_networks'][0]['virtual_machines'][0]['count'] + tenants['virtual_networks'][0]['virtual_machines'][1]['count']

        glance_image = self.global_conf['GLOBALS']['glance_image_name']
        cidr_start   = tenants['virtual_networks'][0]['subnets'][0]['cidr']
        cidr_obj     = CIDR(cidr_start)
        vm_obj_list = []

        self.connections.project_name = "admin"
        self.connections = ContrailConnections(inputs=inputs, logger=mylogger)
        self.connections.vnc_lib = self.connections.get_vnc_lib_h()

        vdns_obj = vDNS(self.connections)
        vdns_id = vdns_obj.create('vDNS-test')
        vdns_fqname = vdns_obj.fq_name(vdns_id)
        print "vDNS:",vdns_fqname
        
        ipam_obj = IPAM(self.connections)
        ipam_id = ipam_obj.create('ipam-test', vdns_id)    
        ipam_fqname = ipam_obj.fq_name(ipam_id)
        print "IPAM:",ipam_fqname 

          
        vn_obj = VN(self.connections)
       
        cidr = "192.167.0.0/16"
        vn_name = "shared_net"
        subnets = [{'cidr':cidr,'name':"shared_subnet"}]
        vn_obj.shared=True
        shared_vn_id = vn_obj.create(vn_name,subnets=subnets,ipam_id=ipam_id)
  
        tenant_obj = Project(self.connections)
        admin_tenant_id = self.connections.get_auth_h().get_project_id('default_domain','admin')

        for tenant_index in xrange(tenant_count):

          self.connections.project_id   = admin_tenant_id
          self.connections.inputs.project_name = "admin"
          self.connections.project_name = "admin"
          self.connections.project_fq_name = "admin"
          self.connections.domain_name = "admin"


          self.connections = ContrailConnections(inputs=inputs, logger=mylogger,project_name="admin")
          self.connections.vnc_lib = self.connections.get_vnc_lib_h()

          self.tenant_name = "TC002_tenant_%d"%tenant_index

          tenant_id = self.connections.get_auth_h().get_project_id('default_domain',self.tenant_name)
          if not tenant_id:
             tenant_id = tenant_obj.create(self.tenant_name)

          self.connections = ContrailConnections(inputs=inputs, logger=mylogger,project_name=self.tenant_name)
          self.connections.vnc_lib = self.connections.get_vnc_lib_h()

          self.connections.inputs.project_name = self.tenant_name
          self.connections.project_name = self.tenant_name
          self.connections.project_fq_name = self.tenant_name
          self.connections.domain_name = self.tenant_name
          self.connections.project_id   = tenant_id


def main():

   parser = argparse.ArgumentParser(add_help=False)
   parser.add_argument("-i", "--ini_file", default=None,help="Specify global conf file", metavar="FILE")
   parser.add_argument("-c", "--yaml_config_file", default=None,help="Specify Test conf file", metavar="FILE")

   args, remaining_argv = parser.parse_known_args(sys.argv[1:])
   cli_args = parse_cli(remaining_argv)

   ini_conf = parse_cfg_file(args.ini_file)

   yaml_conf = parse_yaml_cfg_file(args.yaml_config_file)

   print "INI_CONF:",ini_conf
   print "YAML_CONF:",yaml_conf

   #Do Global Configurations First
   #Setup MGMT VN: simple network, 1 CIDR for mgmt traffic. Set 'shared' flag for VN so that 
   #all tenants can use the same VN  
      
   tests = yaml_conf['tests']
   for test_conf in tests:
      test_obj = Test(ini_conf,test_conf)
      test_obj.setUp()

   #test_obj.cleanup()


main()

