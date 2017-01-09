
import time
import random
import uuid
import re
import os
from netaddr import IPNetwork
from fabric.context_managers import settings, hide
from fabric.api import run, env
from fabric.operations import get, put
from pyVim import  connect
from pyVmomi import vim
from orchestrator import Orchestrator, OrchestratorAuth
from tcutils.util import *
from tcutils.cfgparser import parse_cfg_file
from vnc_api.vnc_api import *

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


class VcenterVlanMgr:

   __metaclass__ = Singleton

   def __init__(self, dvs):
      self._vlans = [(vlan.primaryVlanId, vlan.secondaryVlanId) for vlan in dvs.config.pvlanConfig if vlan.pvlanType == 'isolated']

   def allocate_vlan(self):
       return self._vlans.pop(0)

   def free_vlan(self, vlan):
       self._vlans.append(vlan)


class VcenterOrchestrator(Orchestrator):

   def __init__(self, inputs, host, port, user, pwd, dc_name, vnc, logger):
      self._inputs = inputs
      self._host = host
      self._port = port
      self._user = user
      self._passwd = pwd
      self._dc_name = dc_name
      self._vnc = vnc
      self._log = logger
      self._images_info = parse_cfg_file('configs/images.cfg')
      self._connect_to_vcenter()
      self._vlanmgmt = VcenterVlanMgr(self._vs)
      self._create_keypair()

   def _connect_to_vcenter(self):
      self._si = connect.SmartConnect(host=self._host, port=self._port, user=self._user, pwd=self._passwd)
      if not self._si:
          raise Exception("Unable to connect to vcenter: %s:%d %s/%s" % (self._host,
                          self._port, self._user, self._passwd))
      self._content = self._si.RetrieveContent()
      if not self._content:
          raise Exception("Unable to retrieve content from vcenter")
      self._dc = self._find_obj(self._content.rootFolder, 'dc' , {'name' : self._dc_name})
      if not self._dc:
          raise Exception("Datacenter %s not found" % self._dc_name)
      dvs = self._get_obj_list(self._dc, 'dvs.VSwitch')
      if not dvs:
          raise Exception("Datacenter %s does not have a distributed virtual switch" % self._dc_name)
      if len(dvs) > 1:
          raise Exception("Datacenter %s has %d distributed virtual switches, excepting only one" % (self._dc_name,
                          len(dvs)))
      self._vs = dvs[0]
      self._clusters_hosts = self._get_clusters_hosts()
      if len(self.get_zones()) == 0:
          raise Exception("Datacenter %s has no clusters" % self._dc_name)
      if len(self.get_hosts()) == 0:
          raise Exception("Datacenter %s has no hosts" % self._dc_name)
      self._computes = self._get_computes()

   def _find_obj (self, root, vimtype, param):
       if vimtype == 'ip.Pool':
           items = self._content.ipPoolManager.QueryIpPools(self._dc)
       else:
           items = self._content.viewManager.CreateContainerView(root, [_vimtype_dict[vimtype]], True).view
       for obj in items:
           if _match_obj(obj, param):
               return obj
       return None

   def _get_obj_list (self, root, vimtype):
       view = self._content.viewManager.CreateContainerView(root, [_vimtype_dict[vimtype]], True)
       return [obj for obj in view.view]

   def _get_clusters_hosts(self):
       dd = {}
       for cluster in self._get_obj_list(self._dc, 'cluster'):
          hosts = [host.name for host in self._get_obj_list(cluster, 'host')]
          dd[cluster.name] = hosts
       self._log.debug('Vcenter clusters & hosts\n%s' % str(dd))
       return dd

   def get_hosts(self, zone=None):
       if zone:
          return self._clusters_hosts[zone][:]
       return [host for hosts in self._clusters_hosts.values() for host in hosts]

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
           vmdk = self._images_info[image]['name']
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

   def get_networks_of_vm(self, vm_obj):
        return vm_obj.nets[:]

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
           if 'ContrailVM' in vmobj.name:
               continue
           if re.match(r'%s' % name_pattern, vmobj.name, re.M | re.I):
               vm_list.append(vmobj)
       vm_list = [VcenterVM.create_from_vmobj(self, vmobj) for vmobj in vm_list]
       return vm_list

   @retry(delay=5, tries=35)
   def get_vm_detail(self, vm_obj):
       return vm_obj.get()

   def get_console_output(self, vm_obj):
       return None

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

   def get_key_file(self):
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
                if self._inputs.cfgm_ips[0] != host_ip:
                    put('/tmp/id_rsa', '/tmp/id_rsa')
                    put('/tmp/id_rsa.pub', '/tmp/id_rsa.pub')
                run('chmod 600 /tmp/id_rsa')
                self.tmp_key_file = '/tmp/id_rsa'

   def create_vn(self, name, subnets, **kwargs):
       if self._find_obj(self._dc, 'dvs.PortGroup', {'name' : name}) or self._find_obj(self._dc,
                             'ip.Pool', {'name' : 'ip-pool-for-'+name}):
           raise Exception('A VN %s or ip pool %s, exists with the name' % (name, 'ip-pool-for-'+name))
       if len(subnets) != 1:
           raise Exception('Cannot create VN with %d subnets' % len(subnets))
       vlan = self._vlanmgmt.allocate_vlan()
       if not vlan:
           raise Exception("Vlans exhausted")
       try:
           return VcenterVN.create_in_vcenter(self, name, vlan, subnets[0]['cidr'])
       except:
           self._vlanmgmt.free_vlan(vlan)
           raise

   def delete_vn(self, vn_obj):
       self._vlanmgmt.free_vlan(vn_obj.vlan)
       self._content.ipPoolManager.DestroyIpPool(self._dc, vn_obj.ip_pool_id, True)
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

   def get_policy(self, fq_name):
       self._vnc.network_policy_read(fq_name=fq_name)

   def get_floating_ip(self, fip_id):
       fip_obj = self._vnc.floating_ip_read(id=fip_id)
       return fip_obj.get_floating_ip_address()

   def create_floating_ip(self, pool_obj, project_obj, **kwargs):
       fip_obj = FloatingIp(get_random_name('fip'), pool_obj)
       fip_obj.set_project(project_obj)
       self._vnc.floating_ip_create(fip_obj)
       fip_obj = self._vnc.floating_ip_read(fq_name=fip_obj.fq_name)
       return (fip_obj.get_floating_ip_address(), fip_obj.uuid)

   def delete_floating_ip(self, fip_id):
       self._vnc.floating_ip_delete(id=fip_id)

   def assoc_floating_ip(self, fip_id, vm_id):
       fip_obj = self._vnc.floating_ip_read(id=fip_id)
       vm_obj = self._vnc.virtual_machine_read(id=vm_id)
       vmi = vm_obj.get_virtual_machine_interface_back_refs()[0]['uuid']
       vmintf = self._vnc.virtual_machine_interface_read(id=vmi)
       fip_obj.set_virtual_machine_interface(vmintf)
       self._log.debug('Associating FIP:%s with VMI:%s' % (fip_id, vm_id))
       self._vnc.floating_ip_update(fip_obj)
       return fip_obj

   def disassoc_floating_ip(self, fip_id):
       self._log.debug('Disassociating FIP %s' % fip)
       fip_obj = self._vnc.floating_ip_read(id=fip_id)
       fip_obj.virtual_machine_interface_refs=None
       self._vnc.floating_ip_update(fip_obj)
       return fip_obj


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

       spec = _vim_obj('dvs.ConfigSpec', name=name, type='earlyBinding', numPorts = len(ip_list),
                      defaultPortConfig=_vim_obj('dvs.PortConfig',
                                                vlan=_vim_obj('dvs.PVLan', pvlanId=vlan[1])))
       _wait_for_task(vcenter._vs.AddDVPortgroup_Task([spec]))
       pg = vcenter._find_obj(vcenter._dc, 'dvs.PortGroup', {'name' : name})

       ip_pool = _vim_obj('ip.Pool', name='ip-pool-for-'+name,
                         ipv4Config=_vim_obj('ip.Config',
                                            subnetAddress = str(vn.prefix.network),
                                            netmask = str(vn.prefix.netmask),
                                            range = str(ip_list[0]) + '#' + str(len(ip_list)),
                                            ipPoolEnabled = True),
                         networkAssociation = [_vim_obj('ip.Association',
                                                       network=pg,
                                                       networkName=name)])
       vn.ip_pool_id = vcenter._content.ipPoolManager.CreateIpPool(vcenter._dc, ip_pool)
       return vn

   @staticmethod
   def create_from_vnobj(vcenter, vn_obj):
       vn = VcenterVN()
       vn.vcenter = vcenter
       vn.name = vn_obj.name
       vn.uuid = None
       vlan = vn_obj.config.defaultPortConfig.vlan.pvlanId
       vn.vlan = (vlan - 1, vlan)
       vn.ip_pool_id = vn_obj.summary.ipPoolId
       pool = vcenter._find_obj(vcenter._dc, 'ip.Pool', {'id':vn.ip_pool_id})
       vn.prefix = IPNetwork(pool.ipv4Config.subnetAddress+'/'+pool.ipv4Config.netmask)
       ip_list = list(vn.prefix.iter_hosts())
       return vn

   @retry(tries=30, delay=5)
   def _get_vnc_vn_id(self, fq_name):
       try:
          obj = self.vcenter._vnc.virtual_network_read(fq_name)
          self.uuid = obj.uuid
          return True
       except:
          return False

   def get(self):
       fq_name = [u'default-domain',u'vCenter',unicode(self.name)]
       if not self._get_vnc_vn_id(fq_name):
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
        self.macs = {}
        self.ips = {}
        for intf in vm.guest.net:
             self.macs[intf.network] = intf.macAddress
             self.ips[intf.network] = intf.ipAddress[0]
        return len(self.ips) == len(self.nets)

    def reboot(r):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        if r == 'SOFT':
           vm.RebootGuest()
        else:
           _wait_for_task(vm.ResetVM())


class VcenterAuth(OrchestratorAuth):

   def __init__(self, user, passwd, project_name, inputs):
       self.inputs = inputs
       self.user = user
       self.passwd = passwd
       self.vnc = VncApi(username=user, password=passwd,
                         tenant_name=project_name,
                         api_server_host=self.inputs.cfgm_ip,
                         api_server_port=self.inputs.api_server_port)

   def get_project_id(self, domain, name):
       fq_name = [unicode(domain), unicode(name)]
       obj = self.vnc.project_read(fq_name=fq_name)
       if obj:
           return obj.get_uuid()
       return None

   def get_handle(self):
       return self
