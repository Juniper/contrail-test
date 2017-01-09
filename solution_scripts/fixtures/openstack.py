import os
from orchestrator import Orchestrator, OrchestratorAuth
from nova_test import NovaHelper
from quantum_test import QuantumHelper
from keystone_tests import KeystoneCommands
from common.openstack_libs import ks_exceptions

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, username, password, project_name, logger):
       self.inputs = inputs
       self.logger = logger
       self.quantum_h = QuantumHelper(username=username, password=password,
                                    inputs=inputs, project_name=project_name,
                                    openstack_ip=inputs.openstack_ip)
       self.nova_h = NovaHelper(inputs=inputs, project_name=project_name,
                              username=username, password=password,update_ssh_key=False)

   def get_compute_h(self):
       return self.nova_h

   def get_network_h(self):
       return self.quantum_h

   def get_image_account(self, image_name):
       return self.nova_h.get_image_account(image_name)
        
   def get_hosts(self, zone=None):
       if not zone:
          return self.nova_h.get_hosts()
       else:
          return self.nova_h.get_hosts(zone)

   def get_zones(self):
       return self.nova_h.get_zones()

   def host_aggregates(self):
       #import pdb;pdb.set_trace()
       self.nova_h.obj.aggregates.AggregateManager.create('AG1','AZ')

   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       vn_ids = kwargs.pop('vn_ids',[])
       if not vn_ids:
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

   def get_vm_if_present(self, vm_name=None, **kwargs):
       return  self.nova_h.get_vm_if_present(vm_name=vm_name, **kwargs)

   def get_vm_list(self, name_pattern='', **kwargs):
       return self.nova_h.get_vm_list(name_pattern=name_pattern, **kwargs)

   def get_vm_detail(self, vm_obj):
       return self.nova_h.get_vm_detail(vm_obj)

   def get_vm_by_id(self, vm_id):
       return self.nova_h.get_vm_by_id(vm_id)

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

   def assoc_floating_ip(self, fip_id, vm_id,vn_id=None):
       update_dict = {}
       update_dict['port_id'] = self.quantum_h.get_port_id(vm_id,vn_id)
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

   def __init__(self, user, passwd, project_name, inputs, logger):
       self.inputs = inputs
       self.user = user
       self.passwd = passwd
       self.project = project_name
       self.logger = logger
       self.insecure = bool(os.getenv('OS_INSECURE',True))
       self.auth_url = os.getenv('OS_AUTH_URL') or \
               'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
       self.domain = 'default-domain'
       self.reauth()

   def reauth(self):
       self.keystone = KeystoneCommands(username= self.user,
                                        password= self.passwd,
                                        tenant= self.project,
                                        auth_url= self.auth_url,
                                        insecure=self.insecure)

   def get_project_id(self, domain_name=None, project_name=None):
       if not project_name or project_name == self.project:
           return self.keystone.get_id()
       else:
           return self.keystone.get_project_id(project_name)

   def create_project(self, name):
       return self.keystone.create_project(name)

   def delete_project(self, name):
       try:
           self.keystone.delete_project(name)
       except ks_exceptions.ClientException, e:
           # TODO Remove this workaround 
           if 'Unable to add token to revocation list' in str(e):
               self.logger.warn('Exception %s while deleting project' % (
                    str(e)))

   def delete_user(self, user):
       self.keystone.delete_user(user)

   def create_user(self, user, password):
       try:
           self.keystone.create_user(user, password,
                         tenant_name=self.inputs.stack_tenant)
       except:
           self.logger.info("%s user already created"%(self.user))

   def add_user_to_project(self, user, project):
       try:
           self.keystone.add_user_to_tenant(project, user, 'admin')
       except Exception as e:
           self.logger.info("%s user already added to project"%(user))

   def get_keystone_h(self):
       return self.keystone
