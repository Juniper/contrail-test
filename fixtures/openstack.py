
import os
from orchestrator import Orchestrator, OrchestratorAuth
from nova_test import NovaHelper
from quantum_test import QuantumHelper
from tcutils.util import get_dashed_uuid
from keystoneclient.v2_0 import client as ksclient
from keystone_tests import KeystoneCommands
from keystoneclient import exceptions as ks_exceptions

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, username, password, project_name, project_id,
                 vnclib):
       self.inputs = inputs
       self.quantum_h = QuantumHelper(username=username, password=password,
                                    inputs=inputs, project_id=project_id,
                                    cfgm_ip=inputs.cfgm_ip,
                                    openstack_ip=inputs.openstack_ip)
       self.nova_h = NovaHelper(inputs=inputs, project_name=project_name,
                              username=username, password=password)

   def get_image_account(self, image_name):
       return self.nova_h.get_image_account(image_name)
        
   def get_hosts(self, zone=None):
       if not zone:
          return self.nova_h.get_hosts()
       else:
          return self.nova_h.get_hosts(zone)

   def get_zones(self):
       return self.nova_h.get_zones()

   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       vn_ids = [vn['network']['id'] for vn in vn_objs]
       return self.nova_h.create_vm(vm_name=vm_name, image_name=image_name, vn_ids=vn_ids,
                                   zone=zone, node_name=node_name, count=count, **kwargs)

   def delete_vm(self, vm_obj):
       return self.nova_h.delete_vm(vm_obj)
 
   def is_vm_deleted(self, vm_obj):
       return self.nova_h.is_vm_deleted_in_nova_db(vm_obj, self.inputs.openstack_ip)

   def get_host_of_vm(self, vm_obj):
       return self.nova_h.get_nova_host_of_vm(vm_obj)

   def wait_till_vm_is_active(self, vm_obj):
       return self.nova_h.wait_till_vm_is_active(vm_obj)

   def get_vm_if_present(self, vm_name, **kwargs):
       return  self.nova_h.get_vm_if_present(vm_name, **kwargs)

   def get_vm_list(self, name_pattern='', **kwargs):
       return self.nova_h.get_vm_list(name_pattern=name_pattern, **kwargs)

   def get_vm_detail(self, vm_obj):
       return self.nova_h.get_vm_detail(vm_obj)

   def get_vm_ip(self, vm_obj, vn_name):
       return self.nova_h.get_vm_ip(vm_obj, vn_name)

   def get_key_file(self):
       return self.nova_h.get_key_file()

   def put_key_file_to_host(self, host_ip):
       self.nova_h.put_key_file_to_host(host_ip)

   def get_tmp_key_file(self):
       return self.nova_h.tmp_key_file

   def create_vn(self, name, subnets, **kwargs):
       return self.quantum_h.create_network(name, subnets, **kwargs)

   def delete_vn(self, vn_obj):
       return self.quantum_h.delete_vn(vn_obj['network']['id'])

   def get_vn_id(self, vn_obj):
       return vn_obj['network']['id']

   def get_vn_name(self, vn_obj):
       return vn_obj['network']['name']

   def get_vn_obj_if_present(self, vn_name, **kwargs):
       return self.quantum_h.get_vn_obj_if_present(vn_name, **kwargs)


class OpenstackAuth(OrchestratorAuth):

   def __init__(self, user, passwd, project_name, inputs, logger):
       self.inputs = inputs
       self.user = user
       self.passwd = passwd
       self.project = project_name
       self.logger = logger
       self.insecure = bool(os.getenv('OS_INSECURE',True))
       self.auth_url = os.getenv('OS_AUTH_URL') or \
               'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
       self.reauth()

   def reauth(self):
       self.keystone = ksclient.Client(
            username=self.user,
            password=self.passwd,
            tenant_name=self.project,
            auth_url=self.auth_url,
            insecure=self.insecure)

   def get_project_id(self, domain, name):
       try:
           obj =  self.keystone.tenants.find(name=name)
           return get_dashed_uuid(obj.id)
       except ks_exceptions.NotFound:
           return None

   def create_project(self, name):
       return get_dashed_uuid(self.keystone.tenants.create(name).id)

   def delete_project(self, name):
       try:
           self.keystone.tenants.delete(self.keystone.tenants.find(name=name))
       except ks_exceptions.ClientException, e:
           # TODO Remove this workaround 
           if 'Unable to add token to revocation list' in str(e):
               self.logger.warn('Exception %s while deleting project' % (
                    str(e)))

   def delete_user(self, user):
       kc = KeystoneCommands(username= self.inputs.stack_user,
                             password= self.inputs.stack_password,
                             tenant= self.inputs.project_name,
                             auth_url= self.auth_url, insecure=self.insecure)
       kc.delete_user(user)

   def create_user(self, user, password):
       kc = KeystoneCommands(username= self.inputs.stack_user,
                             password= self.inputs.stack_password,
                             tenant= self.inputs.project_name,
                             auth_url= self.auth_url, insecure=self.insecure)
       try:
           kc.create_user(user,password,email='',
                          tenant_name=self.inputs.stack_tenant,enabled=True)
       except:
           self.logger.info("%s user already created"%(self.user))

   def add_user_to_project(self, user, project):
       kc = KeystoneCommands(username= self.inputs.stack_user,
                             password= self.inputs.stack_password,
                             tenant= self.inputs.project_name,
                             auth_url= self.auth_url, insecure=self.insecure)
       try:
           kc.add_user_to_tenant(project, user, 'admin')
       except Exception as e:
           self.logger.info("%s user already added to project"%(user))


