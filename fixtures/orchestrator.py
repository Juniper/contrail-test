from abc import ABCMeta, abstractmethod

class Orchestrator:
   """Base class for orchestrator."""

   __metaclass__ = ABCMeta  
   
   @abstractmethod 
   def get_image_account(self, image_name):
       '''Returns username, password for the image.'''
       pass

   @abstractmethod 
   def get_hosts(self, zone=None):
       '''Returns a list of computes.'''
       pass 

   @abstractmethod 
   def get_zones(self):
       '''Returns a list of zones/clusters into which computes are grouped.'''
       pass 

   @abstractmethod 
   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       '''Returns a list of VM objects else None.'''
       pass 

   @abstractmethod 
   def delete_vm(self, vm_obj):
       '''Deletes the given VM.'''
       pass 
 
   @abstractmethod 
   def get_host_of_vm(self, vm_obj):
       '''Returns name of the compute, on which the VM was created.'''
       pass 

   @abstractmethod 
   def get_networks_of_vm(self, vm_obj):
       '''Returns names of the networks, associated with the VM.'''
       pass 

   @abstractmethod 
   def get_vm_if_present(self, vm_name, **kwargs):
       '''Returns VM object if present else None.'''
       pass 

   @abstractmethod 
   def get_vm_by_id(self, vm_id):
       '''Returns VM object if present else None.'''
       pass 

   @abstractmethod 
   def get_vm_list(self, name_pattern='', **kwargs):
       '''Returns a list of VM object matching pattern.'''
       pass 

   @abstractmethod 
   def get_vm_detail(self, vm_obj):
       '''Refreshes VM object.'''
       pass 

   @abstractmethod 
   def get_vm_ip(self, vm_obj, vn_name):
       '''Returns a list of IP of VM in VN.'''
       pass 

   @abstractmethod 
   def is_vm_deleted(self, vm_obj):
       '''Returns True if VM has been deleted, else False.'''
       pass 

   @abstractmethod 
   def wait_till_vm_is_active(self, vm_obj):
       '''Return True if VM is powered on, else False.'''
       pass 

   @abstractmethod 
   def get_key_file(self):
       '''Returns the key file path.'''
       pass 

   @abstractmethod 
   def put_key_file_to_host(self, host_ip):
       '''Copy RSA key to host.'''
       pass 

   @abstractmethod 
   def get_tmp_key_file(self):
       pass 

   @abstractmethod 
   def create_vn(self, name, subnets, **kwargs):
       pass 

   @abstractmethod 
   def delete_vn(self, vn_obj):
       '''Delete the VN.'''
       pass 

   @abstractmethod 
   def get_vn_obj_if_present(self, vn_name, **kwargs):
       '''Returns VN if already present.'''
       pass 

   @abstractmethod 
   def get_vn_name(self, vn_obj):
       '''Returns VN name.'''
       pass 

   @abstractmethod 
   def get_vn_id(self, vn_obj):
       '''Returns VN Id.'''
       pass 

   @abstractmethod 
   def add_security_group(self, vm_obj, secgrp):
       pass 

   @abstractmethod 
   def remove_security_group(self, vm_obj, secgrp):
       pass 

   @abstractmethod 
   def get_console_output(self, vm_obj):
       pass 

   @abstractmethod 
   def wait_till_vm_status(self, vm_obj, status):
       pass 

   @abstractmethod 
   def get_policy(self, fq_name):
       pass 

   @abstractmethod 
   def get_floating_ip(self, fip_id):
       pass 

   @abstractmethod 
   def create_floating_ip(self, pool_vn_id, pool_obj, project_obj):
       pass 

   @abstractmethod 
   def delete_floatingip(self, fip_id):
       pass 

   @abstractmethod 
   def assoc_floating_ip(self, fip_id, vm_id):
       pass 

   @abstractmethod 
   def disassoc_floatingip(self, fip_id):
       pass 

   @abstractmethod 
   def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
       '''get image name compatible with zone '''
       pass 

class OrchestratorAuth:
   __metaclass__ = ABCMeta  

   @abstractmethod 
   def reauth(self):
       '''Reauthenticates to auth server, returns none.'''
       pass 

   @abstractmethod 
   def get_project_id(self, domain, name):
       '''Returns project Id.'''
       pass 

   @abstractmethod 
   def create_project(self, name):
       '''Creates a new project and returns Id.'''
       pass 

   @abstractmethod 
   def delete_project(self, name):
       '''Delete project.'''
       pass 

   @abstractmethod 
   def create_user(self, user, passwd):
       '''Create user.'''
       pass 

   @abstractmethod 
   def delete_user(self, user):
       '''Delete user.'''
       pass 

   @abstractmethod 
   def add_user_to_project(self, user, project):
       '''Add user to specified project.'''
       pass 

