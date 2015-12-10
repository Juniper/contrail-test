import atexit
import requests
from pyVim import connect

def get_vcenter_connection(inputs):
    SI = None
    try:
        SI = connect.SmartConnect(host=inputs.vcenter_server,
                              user=inputs.vcenter_username,
                              pwd=inputs.vcenter_password,
                              port=int(inputs.vcenter_port))
        atexit.register(connect.Disconnect, SI)
        content = SI.RetrieveContent()
        return SI
    except IOError, ex:
        pass

def get_vm_info_by_uuid(inputs,uuid):
    
    try:
        SI=get_vcenter_connection(inputs)
        VM = SI.content.searchIndex.FindByUuid(None, uuid,
                                           True,
                                           True)
        return VM
    except IOError,ex:
        pass

def get_esxi_host_of_vm_by_uuid(inputs,uuid):
    VM = get_vm_info_by_uuid(inputs,uuid)
    return VM.runtime.host.name

def get_contrail_vm_by_vm_uuid(inputs,uuid):
    esxi_host = get_esxi_host_of_vm_by_uuid(inputs,uuid)
    for esxi in inputs.esxi_vm_ips:
        if esxi_host == esxi['ip']:
            contrail_vm = esxi['contrail_vm']
            ip = contrail_vm.split('@')[1]
            return inputs.host_data[ip]['name']
         

class Inputs:
    def __init__(self):
        self.vcenter_server='10.204.217.189'
        self.vcenter_username='administrator@vsphere.local'
        self.vcenter_password='Contrail123!'
        self.vcenter_port='443'

def main():
    inputs=Inputs()
    print get_contrail_vm_by_vm_uuid(inputs,'9175dc3b-5ff5-45ca-a836-05dc986ef19d')

if __name__ == "__main__":
    main()
