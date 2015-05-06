
from orchestrator import Orchestrator
from nova_test import NovaHelper
from quantum_test import QuantumHelper

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, username, password, project_name, project_id,
                 vnclib):
       self.inputs = inputs
       self.quantum = QuantumHelper(username=username, password=password,
                                     inputs=inputs, project_id=project_id,
                                     cfgm_ip=inputs.cfgm_ip,
                                     openstack_ip=inputs.openstack_ip)
       self.nova = NovaHelper(inputs=inputs, project_name=project_name,
                               username=username, password=password)

   def get_image_account(self, image_name):
       return self.nova.get_image_account(image_name)
        
   def get_hosts(self, zone=None):
       if not zone:
          return self.nova.get_hosts()
       else:
          return self.nova.get_hosts(zone)

   def get_zones(self):
       return self.nova.get_zones()

   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       vn_ids = [vn['network']['id'] for vn in vn_objs]
       return self.nova.create_vm(vm_name=vm_name, image_name=image_name, vn_ids=vn_ids,
                                   zone=zone, node_name=node_name, count=count, **kwargs)

   def delete_vm(self, vm_obj):
       return self.nova.delete_vm(vm_obj)
 
   def is_vm_deleted(self, vm_obj):
       return self.nova.is_vm_deleted_in_nova_db(vm_obj, self.inputs.openstack_ip)

   def get_host_of_vm(self, vm_obj):
       return self.nova.get_nova_host_of_vm(vm_obj)

   def wait_till_vm_is_active(self, vm_obj):
       return self.nova.wait_till_vm_is_active(vm_obj)

   def get_vm_if_present(self, vm_name, **kwargs):
       return  self.nova.get_vm_if_present(vm_name, **kwargs)

   def get_vm_list(self, name_pattern='', **kwargs):
       return self.nova.get_vm_list(name_pattern=name_pattern, **kwargs)

   def get_vm_detail(self, vm_obj):
       return self.nova.get_vm_detail(vm_obj)

   def get_vm_ip(self, vm_obj, vn_name):
       return self.nova.get_vm_ip(vm_obj, vn_name)

   def put_key_file_to_host(self, host_ip):
       self.nova.put_key_file_to_host(host_ip)

   def get_tmp_key_file(self):
       return self.nova.tmp_key_file

   def create_vn(self, name, subnets, **kwargs):
       return self.quantum.create_network(name, subnets, **kwargs)

   def delete_vn(self, vn_obj):
       return self.quantum.delete_vn(vn_obj['network']['id'])

   def get_vn_id(self, vn_obj):
       return vn_obj['network']['id']

   def get_vn_name(self, vn_obj):
       return vn_obj['network']['name']

   def get_vn_obj_if_present(self, vn_name, **kwargs):
       return self.quantum.get_vn_obj_if_present(vn_name, **kwargs)

