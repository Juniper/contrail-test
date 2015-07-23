
import os
from orchestrator import Orchestrator, OrchestratorAuth
from nova_test import NovaHelper
from quantum_test import QuantumHelper
from tcutils.util import get_dashed_uuid
from keystone_tests import KeystoneCommands
from common.openstack_libs import ks_client as ksclient
from common.openstack_libs import ks_exceptions

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, username, password, project_name, project_id,
                 vnclib=None, logger=None, auth_server_ip=None):
       self.inputs = inputs
       self.logger = logger or logging.getLogger(__name__)
       self.quantum_h = None
       self.nova_h = None
       self.username = username
       self.password = password
       self.project_name = project_name
       self.project_id = project_id 
       self.vnc_lib = vnclib
       self.auth_server_ip = auth_server_ip
       if not auth_server_ip:
           self.auth_server_ip = self.inputs.auth_ip

   def get_network_handler(self):
       if not self.quantum_h: 
           self.quantum_h = QuantumHelper(username=self.username,
                                          password=self.password,
                                          project_id=self.project_id,
                                          auth_server_ip=self.auth_server_ip,
                                          logger=self.logger)
           self.quantum_h.setUp()
       return self.quantum_h

   def get_nova_handler(self):
       if not self.nova_h:
          self.nova_h = NovaHelper(inputs=self.inputs,
                                   project_name=self.project_name,
                                   username=self.username,
                                   password=self.password)
       return self.nova_h

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

   def get_networks_of_vm(self, vm_obj):
       return vm_obj.networks.keys()

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

   def add_security_group(self, vm_obj, secgrp):
       return self.nova_h.add_security_group(vm_obj.id, secgrp)

   def remove_security_group(self, vm_obj, secgrp):
       return self.nova_h.remove_security_group(vm_obj.id, secgrp)

   def get_console_output(self, vm_obj):
       return self.nova_h.get_vm_console_output(vm_obj)

   def wait_till_vm_status(self, vm_obj, status):
       return self.nova_h.wait_till_vm_status(vm_obj, status)

   def get_policy(self, fq_name):
       return self.quantum_h.get_policy_if_present(fq_name[1], fq_name[2])

   def get_floating_ip(self, fip_id):
       fip = self.quantum_h.get_floatingip(fip_id)
       return fip['floatingip']['floating_ip_address']

   def create_floating_ip(self, pool_vn_id, project_obj, **kwargs):
       fip_resp = self.quantum_h.create_floatingip(
                        pool_vn_id, project_obj.uuid)
       return (fip_resp['floatingip']['floating_ip_address'],
                        fip_resp['floatingip']['id'])

   def delete_floating_ip(self, fip_id):
       self.quantum_h.delete_floatingip(fip_id)

   def assoc_floating_ip(self, fip_id, vm_id):
       update_dict = {}
       update_dict['port_id'] = self.quantum_h.get_port_id(vm_id)
       self.logger.debug('Associating FIP ID %s with Port ID %s' %(fip_id,
                          update_dict['port_id']))
       if update_dict['port_id']:
           fip_resp = self.quantum_h.update_floatingip(fip_id,
                            {'floatingip': update_dict})
           return fip_resp
       else:
           return None

   def disassoc_floating_ip(self, fip_id):
       update_dict = {}
       update_dict['port_id'] = None
       self.logger.debug('Disassociating port from FIP ID : %s' %(fip_id))
       fip_resp = self.quantum_h.update_floatingip(fip_id,
                       {'floatingip': update_dict})
       return fip_resp


class OpenstackAuth(OrchestratorAuth):

   def __init__(self, user, passwd, project_name, inputs=None, logger=None,
                auth_url=None):
       self.inputs = inputs
       self.user = user
       self.passwd = passwd
       self.project = project_name
       self.logger = logger or logging.getLogger(__name__)
       self.insecure = bool(os.getenv('OS_INSECURE',True))
       if inputs:
           self.auth_url = 'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
       else:
           self.auth_url = auth_url or os.getenv('OS_AUTH_URL')
       self.reauth()

   def reauth(self):
       self.keystone = ksclient.Client(
            username=self.user,
            password=self.passwd,
            tenant_name=self.project,
            auth_url=self.auth_url,
            insecure=self.insecure)

   def get_project_id(self, name=None):
       if not name:
           return get_dashed_uuid(self.keystone.tenant_id)
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


