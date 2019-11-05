from __future__ import print_function
from builtins import object
from tcutils.util import retry
from tcutils.config import vmware_introspect_utils
from common import log_orig as contrail_logging

class VMWareVerificationLib(object):
    '''Clas to hold verification helper functions for vcenter plugin introspect'''
    def __init__(self,inputs,vrouter):
        self.inputs = inputs
        self.vcntr_introspect = None
        self.logger = contrail_logging.getLogger(__name__)
        self.intfs_dict = {}
        self.vrouter = vrouter

    def get_introspect(self,vrouter):
        self.vcntr_introspect = vmware_introspect_utils.VMWareInspect(vrouter)

    @retry(delay=10, tries=10)
    def verify_vm_in_vcenter(self, vrouter_ip,vm_name, *args):

       #everytime verify_vm_in_vcenter should be called with introspect refreshed
       self.get_introspect(vrouter_ip)
       vm_details = vmware_introspect_utils.get_vm_details(self.vcntr_introspect, vm_name)
       try:
           if vm_details.virtual_machine:
               for elem in vm_details.virtual_machine['list']:
                   if 'ip_address' in elem and elem['ip_address']:
                       return True
                   else:
                       self.logger.error("VM did not get an ip address yet...")
                       return False
           self.logger.error("VM not yet launched...")
           return False
       except Exception as e:
           self.logger.error(e)
           return False

    @retry(delay=10, tries=10)
    def verify_vm_not_in_vcenter(self, vrouter_ip,vm_name, *args):
       	#everytime verify_vm_in_vcenter should be called with introspect refreshe
       self.get_introspect(vrouter_ip)
       vm_details = vmware_introspect_utils.get_vm_details(self.vcntr_introspect, vm_name)
       try:
           if vm_details.virtual_machine:
               self.logger.error("VM is still there...")
               return False
       except Exception as e:
           self.logger.error(e)
           return True
               
    def get_vmi_from_vcenter_introspect(self, vrouter_ip,vm_name, *args):
       intfs = []
       self.get_introspect(vrouter_ip)
       vm_details = vmware_introspect_utils.get_vm_details(self.vcntr_introspect, vm_name)
       return vm_details.virtual_machine['interfaces']
                
        

if __name__ == '__main__':
    va =  vmware_introspect_utils.VMWareInspect('10.204.216.183')
    class Inputs(object):
        def __init__(self):
            self.cfgm_ips = ['10.204.216.7','10.204.216.14','10.204.216.15']
    import pprint
    inputs = Inputs()
    vcenter = VMWareVerificationLib(inputs,'10.204.216.183')
    print(vcenter.verify_vm_in_vcenter('10.204.216.183','test_vm1'))

