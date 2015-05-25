
class Orchestrator:
   """Base class for orchestrator."""

   def get_image_account(self, image_name):
       '''Returns username, password for the image.'''
       raise Exception('Unimplemented interface')

   def get_hosts(self, zone=None):
       '''Returns a list of computes.'''
       raise Exception('Unimplemented interface')

   def get_zones(self):
       '''Returns a list of zones/clusters into which computes are grouped.'''
       raise Exception('Unimplemented interface')

   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       '''Returns a list of VM objects else None.'''
       raise Exception('Unimplemented interface')

   def delete_vm(self, vm_obj):
       '''Deletes the given VM.'''
       raise Exception('Unimplemented interface')
 
   def get_host_of_vm(self, vm_obj):
       '''Returns name of the compute, on which the VM was created.'''
       raise Exception('Unimplemented interface')

   def get_vm_if_present(self, vm_name, **kwargs):
       '''Returns VM object if present else None.'''
       raise Exception('Unimplemented interface')

   def get_vm_by_id(self, vm_id):
       '''Returns VM object if present else None.'''
       raise Exception('Unimplemented interface')

   def get_vm_list(self, name_pattern='', **kwargs):
       '''Returns a list of VM object matching pattern.'''
       raise Exception('Unimplemented interface')

   def get_vm_detail(self, vm_obj):
       '''Refreshes VM object.'''
       raise Exception('Unimplemented interface')

   def get_vm_ip(self, vm_obj, vn_name):
       '''Returns a list of IP of VM in VN.'''
       raise Exception('Unimplemented interface')

   def is_vm_deleted(self, vm_obj):
       '''Returns True if VM has been deleted, else False.'''
       raise Exception('Unimplemented interface')

   def wait_till_vm_is_active(self, vm_obj):
       '''Return True if VM is powered on, else False.'''
       raise Exception('Unimplemented interface')

   def get_key_file(self):
       '''Returns the key file path.'''
       raise Exception('Unimplemented interface')

   def put_key_file_to_host(self, host_ip):
       '''Copy RSA key to host.'''
       raise Exception('Unimplemented interface')

   def get_tmp_key_file(self):
       raise Exception('Unimplemented interface')

   def create_vn(self, name, subnets, **kwargs):
       raise Exception('Unimplemented interface')

   def delete_vn(self, vn_obj):
       '''Delete the VN.'''
       raise Exception('Unimplemented interface')

   def get_vn_obj_if_present(self, vn_name, **kwargs):
       '''Returns VN if already present.'''
       raise Exception('Unimplemented interface')

   def get_vn_name(self, vn_obj):
       '''Returns VN name.'''
       raise Exception('Unimplemented interface')

   def get_vn_id(self, vn_obj):
       '''Returns VN Id.'''
       raise Exception('Unimplemented interface')


class OrchestratorAuth:

   def reauth(self):
       '''Reauthenticates to auth server, returns none.'''
       raise Exception('Unimplemented interface')

   def get_project_id(self, domain, name):
       '''Returns project Id.'''
       raise Exception('Unimplemented interface')

   def create_project(self, name):
       '''Creates a new project and returns Id.'''
       raise Exception('Unimplemented interface')

   def delete_project(self, name):
       '''Delete project.'''
       raise Exception('Unimplemented interface')

   def create_user(self, user, passwd):
       '''Create user.'''
       raise Exception('Unimplemented interface')

   def delete_user(self, user):
       '''Delete user.'''
       raise Exception('Unimplemented interface')

   def add_user_to_project(self, user, project):
       '''Add user to specified project.'''
       raise Exception('Unimplemented interface')

