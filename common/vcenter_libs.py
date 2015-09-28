
try:
    from pyVim import  connect as vcenter_connect
    from pyVmomi import vim as vcenter_vim

    vimtype_dict = {
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
    vimtype_dict = {}
    vcenter_connect = None
    vcenter_vim = None
