import time
import atexit
import requests
try:
    from pyVim import  connect
    from pyVmomi import vim

    _vimtype_dict = {
        'dc' : vim.Datacenter,
        'cluster' : vim.ClusterComputeResource,
        'vm' : vim.VirtualMachine,
        'host' : vim.HostSystem,
        'host.NasSpec' : vim.host.NasVolume.Specification,
        'network' : vim.Network,
        'ds' : vim.Datastore,
        'dvs.PortGroup' : vim.dvs.DistributedVirtualPortgroup,
        'dvs.VSwitch' : vim.dvs.VmwareDistributedVirtualSwitch,
        'dvs.PVLan' : vim.dvs.VmwareDistributedVirtualSwitch.PvlanSpec,
        'dvs.VLan' : vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec,
        'dvs.PortConfig' : vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy,
        'dvs.ConfigSpec' : vim.dvs.DistributedVirtualPortgroup.ConfigSpec,
        'dvs.PortConn' : vim.dvs.PortConnection,
        'dvs.PortGroupSecurity' : vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy,
        'dvs.PortGroupPolicy' : vim.host.NetworkPolicy,
        'dvs.Blob' : vim.dvs.KeyedOpaqueBlob,
        'ip.Config' : vim.vApp.IpPool.IpPoolConfigInfo,
        'ip.Association' : vim.vApp.IpPool.Association,
        'ip.Pool' : vim.vApp.IpPool,
        'dev.E1000' : vim.vm.device.VirtualE1000,
        'dev.VDSpec' : vim.vm.device.VirtualDeviceSpec,
        'dev.VD' : vim.vm.device.VirtualDevice,
        'dev.ConnectInfo' : vim.vm.device.VirtualDevice.ConnectInfo,
        'dev.DVPBackingInfo' : vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo,
        'dev.Ops.add' : vim.vm.device.VirtualDeviceSpec.Operation.add,
        'dev.Ops.remove' : vim.vm.device.VirtualDeviceSpec.Operation.remove,
        'dev.Ops.edit' : vim.vm.device.VirtualDeviceSpec.Operation.edit,
        'vm.Config' : vim.vm.ConfigSpec,
        'vm.Reloc' : vim.vm.RelocateSpec,
        'vm.Clone' : vim.vm.CloneSpec,
        'vm.PassAuth' : vim.vm.guest.NamePasswordAuthentication,
        'vm.Prog' : vim.vm.guest.ProcessManager.ProgramSpec,
     }

except:
    _vimtype_dict = {}
    connect = None
    vim = None
    _vimtype_dict = None

def _vim_obj(typestr, **kwargs):
    return _vimtype_dict[typestr](**kwargs)

def _wait_for_task (task):
    while (task.info.state == vim.TaskInfo.State.running or
           task.info.state == vim.TaskInfo.State.queued):
        time.sleep(2)
    if task.info.state != vim.TaskInfo.State.success:
        if task.info.state == vim.TaskInfo.State.error:
            raise ValueError(task.info.error.localizedMessage)
        raise ValueError("wait_for_task failed:%s" % task.info)
    return

def _match_obj(obj, param):
    attr = param.keys()[0]
    attrs = [attr]
    if '.' in attr:
        attrs = attr.split('.')
        for i in range(len(attrs) - 1):
            if not hasattr(obj, attrs[i]):
                break
            obj = getattr(obj, attrs[i])
    attr = attrs[-1]
    return hasattr(obj, attr) and getattr(obj, attr) == param.values()[0]

def get_vcenter_connection(inputs):
    SI = None
    try:
        SI = connect.SmartConnect(host=inputs.vcenter_server,
                                  port=int(inputs.vcenter_port),
                                  user=inputs.vcenter_username,
                                  pwd=inputs.vcenter_password)
    except Exception as exc:
            if ((isinstance(exc, vim.fault.HostConnectFault)) and
                ('[SSL: CERTIFICATE_VERIFY_FAILED]' in item for item in exc)):
                    try:
                        import ssl
                        default_context = ssl._create_default_https_context
                        ssl._create_default_https_context = ssl._create_unverified_context
                        SI = SmartConnect(
                                host=inputs.vcenter_server,
                                port=int(inputs.vcenter_port),
                                user=inputs.vcenter_username,
                                pwd=inputs.vcenter_password)
                        ssl._create_default_https_context = default_context
                    except Exception as exc1:
                            raise Exception(exc1)
            else:
                    import ssl
                    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                    context.verify_mode = ssl.CERT_NONE
                    SI = connect.SmartConnect(
                                host=inputs.vcenter_server,
                                port=int(inputs.vcenter_port),
                                user=inputs.vcenter_username,
                                pwd=inputs.vcenter_password,
                                sslContext=context)

    if not SI:
            raise Exception("Unable to connect to vcenter: %s:%s %s/%s" %
                           (inputs.vcenter_server,
                            inputs.vcenter_port,
                            inputs.vcenter_username,
                            inputs.vcenter_password))
    return SI

def get_vm_info_by_uuid(inputs,uuid):
    try:
        SI=get_vcenter_connection(inputs)
        content = SI.RetrieveContent()
        if not content:
            raise Exception("Unable to retrieve content from vcenter")

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
