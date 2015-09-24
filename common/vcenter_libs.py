import time
try:
    from pyVim import  connect
    from pyVmomi import vim

    _vimtype_dict = {
        'dc' : vim.Datacenter,
        'cluster' : vim.ClusterComputeResource,
        'vm' : vim.VirtualMachine,
        'host' : vim.HostSystem,
        'network' : vim.Network,
        'ds' : vim.Datastore,
        'host.NasSpec' : vim.host.NasVolume.Specification,
        'dvs.PortGroup' : vim.dvs.DistributedVirtualPortgroup,
        'dvs.VSwitch' : vim.dvs.VmwareDistributedVirtualSwitch,
        'dvs.PVLan' : vim.dvs.VmwareDistributedVirtualSwitch.PvlanSpec,
        'dvs.PortConfig' : vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy,
        'dvs.ConfigSpec' : vim.dvs.DistributedVirtualPortgroup.ConfigSpec,
        'dvs.PortConn' : vim.dvs.PortConnection,
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
        'vm.Config' : vim.vm.ConfigSpec,
        'vm.Reloc' : vim.vm.RelocateSpec,
        'vm.Clone' : vim.vm.CloneSpec,
        'vm.PassAuth' : vim.vm.guest.NamePasswordAuthentication,
        'vm.Prog' : vim.vm.guest.ProcessManager.ProgramSpec,
    }
except:
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
