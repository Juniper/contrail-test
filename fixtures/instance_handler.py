import os

class InstanceHandler(object):
    def __init__(self, username, password, connections, cfgm_ip ):
        self.username= username
        self.password= password
        self.cfgm_ip = cfgm_ip
        self.inputs= connections.inputs
        self.obj=None
        self.logger= self.inputs.logger

    def create_vm(self, image_name, flavor, vn_id, node_name ):
        pass

    def delete_vm(self, vm_obj):
        pass

    def get_vn_obj_if_present(self, vn_name =None, vn_id=None):
        pass

    def get_vn_id_from_obj( self, obj):
        pass

    def delete_vn(self, vn_id):
        pass

    def list_networks(self, args):
        pass

    def get_vn_id(self, vn_name):
        pass

    def get_vn_fq_name ( self, obj):
        pass

    def get_hypervisor_of_vm(self, vm_obj):
        #TODO
        # Right now assume that xen is used only in Cloudstack
        if self.inputs.cstack_env:
            return vm_obj['hypervisor']
        else:
            return 'kvm'
    #end get_hypervisor_of_vm

    def get_domain_id_of_vm( self, host_ip, obj) :
        if self.get_hypervisor_of_vm ( obj ) == 'XenServer':
            username= self.inputs.host_data[host_ip]['username']
            password= self.inputs.host_data[host_ip]['password']
            vm_internal_name= obj['instancename']
            cmd='xe vm-list name-label=%s | grep uuid  | awk \'{ print $5 } \'' %(vm_internal_name)
            vm_xen_id= self.inputs.run_cmd_on_server( host_ip, cmd ).strip('\n')
            print "VM Xen id : %s" %(vm_xen_id)
            cmd= 'xe vm-param-get uuid=%s param-name=dom-id' %(vm_xen_id)
            vm_domain_id= self.inputs.run_cmd_on_server( host_ip, cmd ).strip('\n')
            print "VM Domain id : %s" %(vm_domain_id)
            return vm_domain_id
    #end get_domain_id_of_vm

    def run_cmd_on_xen_vm ( self, host_ip, vm_internal_name, vm_username, vm_password, cmd ):
        console_script_path="./tcutils/console_access.py"
        self.inputs.copy_file_to_server( host_ip, os.path.realpath( console_script_path ), 'console_access.py')
        username= self.inputs.host_data[host_ip]['username']
        password= self.inputs.host_data[host_ip]['password']
        command= 'python console_access.py %s %s %s \"%s\"' %( vm_internal_name, vm_username, vm_password, cmd )
        output= self.inputs.run_cmd_on_server( host_ip, command)
        print output
        return output
    #end run_cmd_on_xen_vm

    def get_compute_host(self):
        while(1):
            for i in self.inputs.compute_ips:
#                yield socket.gethostbyaddr(i)[0]
                yield self.inputs.host_data[i]['name']
    #end get_compute_host


#end InstanceHandler
