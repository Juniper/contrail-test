from tcutils.util import retry
from tcutils.config import vmware_introspect_utils

class VMWareVerificationLib:
    '''Clas to hold verification helper functions for vcenter plugin introspect'''
    def __init__(self,inputs):
        self.inputs = inputs
        self.vcntr_introspect = None
        self.logger = self.inputs.logger

    def get_introspect(self):
        try:
            for ip in self.inputs.cfgm_ips:
                vc_inspect = vmware_introspect_utils.\
							get_vcenter_plugin_introspect_elements(\
							vmware_introspect_utils.VMWareInspect(ip))
                if (vc_inspect['master'][0] == 'true'):
                    self.vcntr_introspect = vmware_introspect_utils.VMWareInspect(ip)
                    break
        except Exception as e:
            self.logger.exception(e)

    @retry(delay=10, tries=10)
    def verify_vm_in_vcenter(self, vrouter_ip,vm_name, *args):

       #everytime verify_vm_in_vcenter should be called with introspect refreshed
       self.get_introspect()
       vrouter_details = vmware_introspect_utils.get_vrouter_details(self.vcntr_introspect, vrouter_ip)
       for virtual_machine in vrouter_details.virtual_machines:
           if virtual_machine.name == vm_name:
               self.logger.info("Vcenter plugin verification:%s launched in vorouter %s in virtual network %s"\
                               %(vm_name,vrouter_ip,virtual_machine.virtual_network))
               return True
       self.logger.error("Vcenter plugin verification:%s NOT launched in vorouter %s "\
                               %(vm_name,vrouter_ip))
       return False

    @retry(delay=10, tries=10)
    def verify_vm_not_in_vcenter(self, vrouter_ip,vm_name, *args):
       	#everytime verify_vm_in_vcenter should be called with introspect refreshe
		self.get_introspect()
		vrouter_details = vmware_introspect_utils.get_vrouter_details(self.vcntr_introspect, vrouter_ip)
		try:
			for virtual_machine in vrouter_details.virtual_machines:
				if virtual_machine.name == vm_name:
					self.logger.error("Vcenter plugin verification:%s STILL in vorouter %s in virtual network %s"\
								%(vm_name,vrouter_ip,virtual_machine.virtual_network))
					return False
		except Exception as e:
			self.logger.info("Vcenter plugin verification:%s deleted in vorouter %s "\
                               %(vm_name,vrouter_ip))
			return True

		self.logger.info("Vcenter plugin verification:%s deleted in vorouter %s "\
                               %(vm_name,vrouter_ip))
		return True

if __name__ == '__main__':
    va =  vmware_introspect_utils.VMWareInspect('10.204.216.14')
    class Inputs:
        def __init__(self):
            self.cfgm_ips = ['10.204.216.7','10.204.216.14','10.204.216.15']
    r =  vmware_introspect_utils.vrouter_details(va,'10.204.217.27')
    import pprint
    pprint.pprint(r)
    inputs = Inputs()
    vcenter = VMWareVerificationLib(inputs)
    vcenter.verify_vm_in_vcenter('10.204.217.27','test_vm2')

