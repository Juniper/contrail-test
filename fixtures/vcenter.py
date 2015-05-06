
import time
import random
import uuid
import re
from netaddr import IPNetwork
from fabric.context_managers import settings, hide
from fabric.api import run, env
from fabric.operations import get, put
from pyVim import  connect
from pyVmomi import vim
from orchestrator import Orchestrator
from tcutils.util import *
from tcutils.cfgparser import parse_cfg_file

_vimtype_dict = {
  'dc' : vim.Datacenter,
  'cluster' : vim.ClusterComputeResource,
  'vm' : vim.VirtualMachine,
  'host' : vim.HostSystem,
  'network' : vim.Network,
  'ds' : vim.Datastore,
  'dvs.PortGroup' : vim.dvs.DistributedVirtualPortgroup,
  'dvs.VSwitch' : vim.dvs.VmwareDistributedVirtualSwitch,
  'dvs.PVLan' : vim.dvs.VmwareDistributedVirtualSwitch.PvlanSpec,
  'dvs.PortConfig' : vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy,
  'dvs.ConfigSpec' : vim.dvs.DistributedVirtualPortgroup.ConfigSpec,
  'dvs.PortConn' : vim.dvs.PortConnection,
  'ip.Config' : vim.vApp.IpPool.IpPoolConfigInfo,
  'ip.Association' : vim.vApp.IpPool.Association,
  'ip.Pool' : vim.vApp.IpPool,
  'dev.E1000' : vim.vm.device.VirtualE1000,
  'dev.VD' : vim.vm.device.VirtualDeviceSpec,
  'dev.ConnectInfo' : vim.vm.device.VirtualDevice.ConnectInfo,
  'dev.DVPBackingInfo' : vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo,
  'vm.Config' : vim.vm.ConfigSpec,
  'vm.Reloc' : vim.vm.RelocateSpec,
  'vm.Clone' : vim.vm.CloneSpec,
}

def _vim_obj(typestr, **kwargs):
    return _vimtype_dict[typestr](**kwargs)

def _wait_for_task (task):
    while (task.info.state == vim.TaskInfo.State.running or
           task.info.state == vim.TaskInfo.State.queued):
        time.sleep(2)
    if task.info.state != vim.TaskInfo.State.success:
        raise ValueError("Something went wrong in wait_for_task")
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


class VcenterOrchestrator(Orchestrator):

   def __init__(self, inputs, host, port, user, pwd, dc_name, vnc):
      self._inputs = inputs
      self._host = host
      self._port = port
      self._user = user
      self._passwd = pwd
      self._dc_name = dc_name
      self._vnc = vnc
      self._images_info = parse_cfg_file('configs/images.cfg')
      self._connect_to_vcenter()
      self._create_keypair()

   def _connect_to_vcenter(self):
      self._si = connect.SmartConnect(host=self._host, port=self._port, user=self._user, pwd=self._passwd)
      assert self._si, "Unable to connect to vcenter"
      self._ctnt = self._si.RetrieveContent()
      assert self._ctnt, "Unable to retrieve content"
      self._dc = self._find_obj(self._ctnt.rootFolder, 'dc' , {'name' : self._dc_name})
      assert self._dc, "Datacenter %s not found" % self._dc_name
      dvs = self._get_obj_list(self._dc, 'dvs.VSwitch')
      assert dvs and (len(dvs) == 1), "Number of DVS is either zero or more than one"
      self._vs = dvs[0]
      self._clusters_hosts = self._get_clusters_hosts()
      assert len(self.get_zones()) and len(self.get_hosts()), "Either no clusters or no hosts in datacenter"
      self._computes = self._get_computes()
      self.free_vlans = [(vlan.primaryVlanId, vlan.secondaryVlanId) for vlan in self._vs.config.pvlanConfig if vlan.pvlanType == 'isolated']

   def _find_obj (self, root, vimtype, param):
       if vimtype == 'ip.Pool':
           items = self._ctnt.ipPoolManager.QueryIpPools(self._dc)
       else:
           items = self._ctnt.viewManager.CreateContainerView(root, [_vimtype_dict[vimtype]], True).view
       for obj in items:
           if _match_obj(obj, param):
               return obj
       return None

   def _get_obj_list (self, root, vimtype):
       view = self._ctnt.viewManager.CreateContainerView(root, [_vimtype_dict[vimtype]], True)
       return [obj for obj in view.view]

   def _get_clusters_hosts(self):
       dd = {}
       #clusters = [cluster.name for cluster in self._get_obj_list (self._dc, 'cluster')]
       for cluster in self._get_obj_list(self._dc, 'cluster'):
          hosts = [host.name for host in self._get_obj_list(cluster, 'host')]
          dd[cluster.name] = hosts
       return dd

   def get_hosts(self, zone=None):
       if zone:
          return self._clusters_hosts[zone][:]
       return self._clusters_hosts.values()

   def get_zones(self):
       return self._clusters_hosts.keys()

   def get_image_account(self, image_name):
       return (self._images_info[image_name]['username'],
               self._images_info[image_name]['password'])

   @threadsafe_generator
   def _get_computes(self):
       while True:
           hosts = [(server, cluster) for cluster, servers in self._clusters_hosts.items() for server in servers]
           for host in hosts:
                yield host

   def _upload_to_host(self, host, image):
       vmx = self._images_info[image].get('vctmpl', None)
       loc = self._images_info[image].get('vcpath', None)
       vmdk = self._images_info[image].get('vcname', None)
       webserver = self._images_info[image]['webserver'] or \
            getattr(env, 'IMAGE_WEB_SERVER', '10.204.216.51')
       if not vmdk:
           vmdk = self._images.info[image]['name']
       if not vmx or not loc or not vmdk or ('vmdk' not in vmdk):
           raise Exception("no suitable vmdk or template for %s" % image)

       user = self._inputs.host_data[host.name]['username']
       pwd  = self._inputs.host_data[host.name]['password']
       url = 'http://%s/%s/' % (webserver, loc)
       url_vmx  = url + vmx
       url_vmdk = url + vmdk
       ds   = host.datastore[0]
       dst  = '/vmfs/volumes/' + ds.name + '/' + image + '/'
       dst_vmdk = dst + image + '.vmdk'
       tmp_vmdk = dst + vmdk
       with settings(host_string='%s@%s' % (user, host.name), password=pwd,
                     warn_only = True, shell = '/bin/sh -l -c'):
           run('mkdir -p %s' % dst)
           run('wget %s -P %s' % (url_vmx, dst))
           run('wget %s -P %s' % (url_vmdk, dst))
           run('vmkfstools -i %s -d zeroedthick %s' % (tmp_vmdk, dst_vmdk))
           run('rm %s' % tmp_vmdk)

       return ds.name, image+ '/' + vmx

   def _load_and_register_template(self, image):
       host_name, cluster_name  = next(self._computes)
       host = self._find_obj(self._find_obj(self._dc, 'cluster', {'name' : cluster_name}),
                                   'host', {'name' : host_name})
       ds, vmtx = self._upload_to_host(host, image)
       folder = self._dc.vmFolder
       _wait_for_task(folder.RegisterVM_Task(path='[%s] %s' % (ds, vmtx), name=image,
                          asTemplate=True, host=host, pool=None))

   def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
       if self._find_obj(self._dc, 'vm', {'name' : vm_name}):
           raise Exception("VM exists with the name %s" % vm_name)

       if zone and ((zone not in self._clusters_hosts) or (not len(self._clusters_hosts[zone]))):
           raise Exception("No cluster named %s or no hosts in it" % zone)

       host = None
       if node_name:
           host = self._find_obj(self._dc, 'host', {'name' : node_name})
           if not host:
               raise Exception("host %s not found" % node_name)

       tmpl = self._find_obj(self._dc, "vm", {'name' : image_name})
       if not tmpl:
           self._load_and_register_template(image_name)
           tmpl = self._find_obj(self._dc, "vm", {'name' : image_name})
           if not tmpl:
               raise Exception("template not found")

       nets = [self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vn.name}) for vn in vn_objs]
       objs = []
       for _ in range(count):
          if host:
              tgthost = host
          elif zone:
              while True:
                   host_name, cluster_name  = next(self._computes)
                   if cluster_name == zone:
                       break
              tgthost = self._find_obj(self._find_obj(self._dc, 'cluster', {'name' : cluster_name}),
                                   'host', {'name' : host_name})
          else:
              host_name, cluster_name = next(self._computes)
              tgthost = self._find_obj(self._find_obj(self._dc, 'cluster', {'name' : cluster_name}),
                                   'host', {'name' : host_name})

          vm = VcenterVM.create_in_vcenter(self, vm_name, tmpl, nets, tgthost)
          objs.append(vm)

       return objs

   def delete_vm(self, vm):
       vm_obj = self._find_obj(self._dc, 'vm', {'name' : vm.name})
       if vm_obj:
           if vm_obj.runtime.powerState != 'poweredOff':
               _wait_for_task(vm_obj.PowerOff())
           _wait_for_task(vm_obj.Destroy())

   @retry(tries=30, delay=5)
   def wait_till_vm_is_active(self, vm_obj):
       vm = self._find_obj(self._dc, 'vm', {'name' : vm_obj.name})
       return vm.runtime.powerState == 'poweredOn'

   def get_host_of_vm(self, vm_obj):
       host = self._find_obj(self._dc, 'host', {'name' : vm_obj.host})
       contrail_vm = None
       for vm in host.vm:
           if 'ContrailVM' in vm.name:
               contrail_vm = vm
               break
       return self._inputs.host_data[contrail_vm.summary.guest.ipAddress]['name']
       #return 'ContrailVM-' + self._dc_name + '-' + vm_obj.host

   @retry(tries=10, delay=5)
   def is_vm_deleted(self, vm_obj):
       return self._find_obj(self._dc, 'vm', {'name' : vm_obj.name}) == None

   def get_vm_if_present(self, vm_name, **kwargs):
       vmobj = self._find_obj(self._dc, 'vm', {'name' : vm_name})
       if vmobj:
          return VcenterVM.create_from_vmobj(self, vmobj)
       return None

   def get_vm_by_id(self, vm_id):
       vmobj = self._find_obj(self._dc, 'vm', {'summary.config.instanceUuid':vm_id})
       if vmobj:
          return VcenterVM.create_from_vmobj(self, vmobj)
       return None

   def get_vm_list(self, name_pattern='', **kwargs):
       vm_list = []
       vms = self._get_obj_list(self._dc, 'vm')
       for vmobj in vms:
           if re.match(r'%s' % name_pattern, vmobj.name, re.M | re.I):
               vm_list.append(vmobj)
       vm_list = [VcenterVM.create_from_vmobj(self, vmobj) for vmobj in vm_list]
       return vm_list

   @retry(delay=5, tries=35)
   def get_vm_detail(self, vm_obj):
       return vm_obj.get()

   def get_vm_ip(self, vm_obj, vn_name):
       self.get_vm_detail(vm_obj)
       ret = vm_obj.ips.get(vn_name, None)
       return [ret]

   def _create_keypair(self):
       username = self._inputs.host_data[self._inputs.cfgm_ip]['username']
       password = self._inputs.host_data[self._inputs.cfgm_ip]['password']
       with settings(
                host_string='%s@%s' % (username, self._inputs.cfgm_ip),
                    password=password, warn_only=True, abort_on_prompts=True):
           rsa_pub_arg = '.ssh/id_rsa'
           if exists('.ssh/id_rsa.pub'):  # If file exists on remote m/c
               get('.ssh/id_rsa.pub', '/tmp/')
           else:
               run('mkdir -p .ssh')
               run('rm -f .ssh/id_rsa*')
               run('ssh-keygen -f %s -t rsa -N \'\'' % (rsa_pub_arg))
               get('.ssh/id_rsa.pub', '/tmp/')

   def get_tmp_key_file(self):
       return self.tmp_key_file

   def put_key_file_to_host(self, host_ip):
       username = self._inputs.host_data[self._inputs.cfgm_ip]['username']
       password = self._inputs.host_data[self._inputs.cfgm_ip]['password']
       with hide('everything'):
            with settings(host_string='%s@%s' % (
                    username, self._inputs.cfgm_ip),
                    password=password,
                    warn_only=True, abort_on_prompts=False):
                get('.ssh/id_rsa', '/tmp/')
                get('.ssh/id_rsa.pub', '/tmp/')
       with hide('everything'):
            with settings(
                host_string='%s@%s' % (self._inputs.host_data[host_ip]['username'],
                                       host_ip), password=self._inputs.host_data[
                    host_ip]['password'],
                    warn_only=True, abort_on_prompts=False):
                if self._inputs.cfgm_ips != host_ip:
                    put('/tmp/id_rsa', '/tmp/id_rsa')
                    put('/tmp/id_rsa.pub', '/tmp/id_rsa.pub')
                run('chmod 600 /tmp/id_rsa')
                self.tmp_key_file = '/tmp/id_rsa'

   def create_vn(self, name, subnets, **kwargs):
       if self._find_obj(self._dc, 'dvs.PortGroup', {'name' : name}) or self._find_obj(self._dc,
                             'ip.Pool', {'name' : 'pool-'+name}):
           raise Exception('A VN %s or ip pool %s, exists with the name' % (name, 'pool-'+name))
       if len(subnets) != 1:
           raise Exception('Cannot create VN with %d subnets' % len(subnets))
       vlan = self._allocate_vlan()
       if not vlan:
           raise Exception("Vlans exhausted")
       try:
           return VcenterVN.create_in_vcenter(self, name, vlan, subnets[0]['cidr'])
       except:
           self._free_vlan(vlan)
           raise

   def delete_vn(self, vn_obj):
       self._free_vlan(vn_obj.vlan)
       self._ctnt.ipPoolManager.DestroyIpPool(self._dc, vn_obj.ip_pool_id, True)
       pg = self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vn_obj.name})
       pg.Destroy()
       return True

   def get_vn_obj_if_present(self, vn_name, **kwargs):
       pg = self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vn_name})
       if pg:
          return VcenterVN.create_from_vnobj(self, pg)
       return None

   def get_vn_name(self, vn_obj):
       return vn_obj.name

   def get_vn_id(self, vnobj):
       if not vnobj.uuid:
           vnobj.get()
       return vnobj.uuid

   def _allocate_vlan(self):
       return self.free_vlans.pop(0)

   def _free_vlan(self, vlan):
       self.free_vlans.append(vlan)


class VcenterVN:

   @staticmethod
   def create_in_vcenter(vcenter, name, vlan, prefix):
       vn = VcenterVN()
       vn.vcenter = vcenter
       vn.name = name
       vn.vlan = vlan
       vn.uuid = None
       vn.prefix = IPNetwork(prefix) 
       ip_list = list(vn.prefix.iter_hosts())
       vn.gw_ip = ip_list.pop(-1)
       vn.meta_ip = ip_list.pop(-1)

       spec = _vim_obj('dvs.ConfigSpec', name=name, type='earlyBinding', numPorts = len(ip_list),
                      defaultPortConfig=_vim_obj('dvs.PortConfig',
                                                vlan=_vim_obj('dvs.PVLan', pvlanId=vlan[1])))
       _wait_for_task(vcenter._vs.AddDVPortgroup_Task([spec]))
       pg = vcenter._find_obj(vcenter._dc, 'dvs.PortGroup', {'name' : name})

       ip_pool = _vim_obj('ip.Pool', name='pool-'+name,
                         ipv4Config=_vim_obj('ip.Config',
                                            subnetAddress = str(vn.prefix.network),
                                            netmask = str(vn.prefix.netmask),
                                            range = str(ip_list[0]) + '#' + str(len(ip_list)),
                                            ipPoolEnabled = True),
                         networkAssociation = [_vim_obj('ip.Association',
                                                       network=pg,
                                                       networkName=name)])
       vn.ip_pool_id = vcenter._ctnt.ipPoolManager.CreateIpPool(vcenter._dc, ip_pool)
       return vn

   @staticmethod
   def create_from_vnobj(vcenter, vn_obj):
       vn = VcenterVN()
       vn.vcenter = vcenter
       vn.name = vn_obj.name
       vn.uuid = None
       vlan = vn.config.defaultPortConfig.vlan.pvlanId 
       vn.vlan = (vlan - 1, vlan)
       vn.ip_pool_id = vn_obj.summary.ipPoolId
       pool = vcenter._find_obj(vcenter._dc, 'ip.Pool', {'id':vn.ip_pool_id})
       vn.prefix = IPNetwork(pool.ipv4Config.subnetAddress+'/'+pool.ipv4Config.netmask)
       ip_list = list(prefix.iter_hosts())
       vn.gw_ip = ip_list.pop(-1)
       vn.meta_ip = ip_list.pop(-1)
       return vn

   @retry(tries=30, delay=5)
   def _vnc_vn_id(self, fq_name):
       try:
          obj = self.vcenter._vnc.virtual_network_read(fq_name)
          self.uuid = obj.uuid
          return True
       except:
          return False

   def get(self):
       #pg = self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vnobj.name})
       #return str(uuid.uuid3(uuid.NAMESPACE_OID, pg.key))
       fq_name = [u'default-domain',u'vCenter',unicode(self.name)]
       if not self._vnc_vn_id(fq_name):
           raise Exception("Unable to query VN %s from vnc" % self.name)


class VcenterVM:

    @staticmethod
    def create_from_vmobj(vcenter, vmobj):
        vm = VcenterVM()
        vm.vcenter = vcenter
        vm.name = vmobj.name
        vm.host = vmobj.runtime.host.name
        vm.nets = [net.name for net in vmobj.network]
        vm.get(vmobj)
        return vm

    @staticmethod
    def create_in_vcenter(vcenter, name, template, networks, host):
        vm = VcenterVM()
        vm.vcenter = vcenter
        vm.name = name
        vm.host = host.name
        vm.nets = [net.name for net in networks]

        intfs = []
        switch_id = vcenter._vs.uuid
        for net in networks:
            spec = _vim_obj('dev.VD', operation=vim.vm.device.VirtualDeviceSpec.Operation.add,
                           device=_vim_obj('dev.E1000',
                                          addressType='Generated',
                                          connectable=_vim_obj('dev.ConnectInfo',
                                                              startConnected=True,
                                                              allowGuestControl=True),
                                          backing=_vim_obj('dev.DVPBackingInfo',
                                                          port = _vim_obj('dvs.PortConn',
                                                          switchUuid=switch_id,
                                                          portgroupKey=net.key))))
            intfs.append(spec)

        spec = _vim_obj('vm.Clone',
                       location=_vim_obj('vm.Reloc',
                                        datastore=host.datastore[0],
                                        pool=host.parent.resourcePool),
                       config=_vim_obj('vm.Config', deviceChange=intfs),
                       powerOn=True)
        _wait_for_task(template.Clone(folder=vcenter._dc.vmFolder, name=vm.name,
                                      spec=spec))
        vmobj = vcenter._find_obj(vcenter._dc, 'vm', {'name' : vm.name})
        vm.get(vmobj)
        return vm

    def get(self, vm=None):
        if not vm:
           vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        self.id = vm.summary.config.instanceUuid
        self.macs = {intf.network : intf.macAddress for intf in vm.guest.net}
        self.ips = {intf.network : intf.ipAddress[0] for intf in vm.guest.net}
        return len(self.ips) == len(self.nets)

    def reboot(r):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        if r == 'SOFT':
           vm.RebootGuest()
        else:
           _wait_for_task(vm.ResetVM())


