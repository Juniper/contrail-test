import logging
from abc import ABCMeta, abstractmethod

from contrailapi import ContrailVncApi

class Orchestrator:
   """Base class for orchestrator."""

   __metaclass__ = ABCMeta

   def __init__(self, inputs, vnc_api_h, logger=None):
       self.inputs = inputs
       self.logger = logger or logging.getLogger(__name__)
       self.vnc_h = ContrailVncApi(vnc_api_h, logger)

   def is_feature_supported(self, feature):
       return True

   @abstractmethod
   def get_image_account(self, image_name):
       '''Returns username, password for the image.'''
       pass

   @abstractmethod
   def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
       '''Get image name compatible with zone '''
       pass

   @abstractmethod
   def get_flavor(self, flavor):
       '''Installs and Returns Flavor ID.'''
       pass

   @abstractmethod
   def get_default_image_flavor(self, image_name):
       '''Returns Flavor ID for an image.'''
       pass

   @abstractmethod
   def get_image(self, image):
       '''Installs and Returns Image ID.'''
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
   def delete_vm(self, vm_obj, **kwargs):
       pass

   @abstractmethod
   def get_host_of_vm(self, vm_obj, **kwargs):
       '''Returns name of the compute, on which the VM was created.'''
       pass

   @abstractmethod
   def get_networks_of_vm(self, vm_obj, **kwargs):
       '''Returns names of the networks, associated with the VM.'''
       pass

   @abstractmethod
   def get_vm_if_present(self, vm_name, **kwargs):
       pass

   @abstractmethod
   def get_vm_by_id(self, vm_id, **kwargs):
       pass

   @abstractmethod
   def get_vm_list(self, name_pattern='', **kwargs):
       '''Returns a list of VM object matching pattern.'''
       pass 
   
   @abstractmethod
   def get_vm_detail(self, vm_obj, **kwargs):
       '''Refreshes VM object.'''
       pass

   @abstractmethod
   def get_vm_ip(self, vm_obj, vn_name, **kwargs):
       '''Returns a list of IP of VM in VN.'''
       pass

   @abstractmethod
   def is_vm_deleted(self, vm_obj, **kwargs):
       pass

   @abstractmethod
   def wait_till_vm_is_active(self, vm_obj, **kwargs):
       pass

   @abstractmethod
   def wait_till_vm_status(self, vm_obj, status, **kwargs):
       pass

   @abstractmethod
   def get_console_output(self, vm_obj, **kwargs):
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
   def create_vn(self, vn_name, subnets, **kwargs):
       pass

   @abstractmethod
   def delete_vn(self, vn_obj, **kwargs):
       pass

   @abstractmethod
   def get_vn_obj_if_present(self, vn_name, **kwargs):
       pass

   @abstractmethod
   def get_vn_name(self, vn_obj, **kwargs):
       pass

   @abstractmethod
   def get_vn_id(self, vn_obj, **kwargs):
       pass

   def get_vn_list(self, **kwargs):
       return self.vnc_h.get_vn_list(**kwargs)

   def get_policy(self, fq_name, **kwargs):
       return self.vnc_h.get_policy(fq_name, **kwargs)

   def get_floating_ip(self, fip_id, **kwargs):
       return self.vnc_h.get_floating_ip(fip_id, **kwargs)

   def create_floating_ip(self, pool_vn_id, pool_obj, project_obj, **kwargs):
       return self.vnc_h.create_floating_ip( pool_obj, project_obj,
                                            **kwargs)

   def delete_floating_ip(self, fip_id, **kwargs):
       return self.vnc_h.delete_floating_ip(fip_id, **kwargs)

   def assoc_floating_ip(self, fip_id, vm_id, **kwargs):
       return self.vnc_h.assoc_floating_ip(fip_id, vm_id, **kwargs)

   def disassoc_floating_ip(self, fip_id, **kwargs):
       return self.vnc_h.disassoc_floating_ip(fip_id, **kwargs)

   def add_security_group(self, vm_id, sg_id, **kwargs):
       return self.vnc_h.add_security_group(vm_id, sg_id, **kwargs)

   def remove_security_group(self, vm_id, sg_id, **kwargs):
       return self.vnc_h.remove_security_group(vm_id, sg_id, **kwargs)

   def create_security_group(self, sg_name, parent_fqname, sg_entries, **kwargs):
       return self.vnc_h.create_security_group(sg_name, parent_fqname,
                                               sg_entries, **kwargs)

   def delete_security_group(self, sg_id, **kwargs):
       return self.vnc_h.delete_security_group(sg_id, **kwargs)

   def get_security_group(self, sg_id, **kwargs):
       return self.vnc_h.get_security_group(sg_id, **kwargs)

   def get_security_group_rules(self, sg_id, **kwargs):
       return self.vnc_h.get_security_group_rules(sg_id, **kwargs)

   def delete_security_group_rules(self, sg_id, **kwargs):
       return self.vnc_h.delete_security_group_rules(sg_id, **kwargs)

   def set_security_group_rules(self, sg_id, **kwargs):
       return self.vnc_h.set_security_group_rules(sg_id, **kwargs)

class OrchestratorAuth:
   __metaclass__ = ABCMeta

   @abstractmethod
   def reauth(self):
       pass

   @abstractmethod
   def get_project_id(self, name=None):
       pass

   @abstractmethod
   def create_project(self, name):
       pass

   @abstractmethod
   def delete_project(self, name):
       pass

   @abstractmethod
   def create_user(self, user, passwd):
       pass

   @abstractmethod
   def delete_user(self, user):
       pass

   @abstractmethod
   def add_user_to_project(self, user, project):
       pass
