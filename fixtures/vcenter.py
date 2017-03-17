import time
import random
import uuid
import re
import os
from netaddr import IPNetwork
from fabric.context_managers import settings, hide
from fabric.api import run, env
from fabric.operations import get, put
from orchestrator import Orchestrator, OrchestratorAuth
from tcutils.util import *
from tcutils.cfgparser import parse_cfg_file
from vnc_api.vnc_api import VncApi
from common.vcenter_libs import _vimtype_dict
from common.vcenter_libs import connect
from common.vcenter_libs import vim
from tcutils.config import vcenter_verification
from pyVmomi import vim, vmodl

def _vim_obj(typestr, **kwargs):
    return _vimtype_dict[typestr](**kwargs)

def _wait_for_task (task):
    while (task.info.state == vim.TaskInfo.State.running or
           task.info.state == vim.TaskInfo.State.queued):
        time.sleep(2)
    if task.info.state != vim.TaskInfo.State.success:
        if task.info.state == vim.TaskInfo.State.error:
            raise ValueError(task.info.error.localizedMessage)
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


class NFSDatastore:

    __metaclass__ = Singleton

    def __init__(self, inputs, vc):
        self.name = 'nfs-ds'
        self.path = '/nfs'
        self.server = inputs.cfgm_ip
        self.vcpath = '/vmfs/volumes/nfs-ds/'

        if vc._find_obj(vc._dc, 'ds', {'name':self.name}):
            nas_ds=vc._find_obj(vc._dc, 'ds', {'name':self.name})
            if nas_ds.summary.accessible:#In vrouter gateway scenario, we are not provisioning
                return                   #the vcenter server/reimaging the esxi hosts,we are only provisioning 
                                         #the contrail-controllers.Hence, the nfs datastore becomes 
                                         #in-accessiable.We need to create and mount the nfs datastore again. 
            else:
                hosts = [host for cluster in vc._dc.hostFolder.childEntity for host in cluster.host]
                for host in hosts:
                    self._delete_datastore(host,nas_ds)
                
        username = inputs.host_data[self.server]['username']
        password = inputs.host_data[self.server]['password']
        with settings(host_string=username+'@'+self.server, password=password,
                      warn_only = True, shell = '/bin/sh -l -c'):
            sudo('mkdir /nfs')
            sudo('apt-get -y install nfs-kernel-server')
            sudo("sed -i '/nfs /d' /etc/exports")
            sudo('echo "/nfs    *(rw,sync,no_root_squash)" >> /etc/exports')
            sudo('service nfs-kernel-server restart')

        hosts = [host for cluster in vc._dc.hostFolder.childEntity for host in cluster.host]
        spec = _vim_obj('host.NasSpec', remoteHost=self.server, remotePath=self.path,
                        localPath=self.name, accessMode='readWrite')
        for host in hosts:
            host.configManager.datastoreSystem.CreateNasDatastore(spec)

    def _delete_datastore(self,host,datastore):
        host.configManager.datastoreSystem.RemoveDatastore(datastore)  
                    

class VcenterPvtVlanMgr:

    __metaclass__ = Singleton

    def __init__(self, dvs):
        self._vlans = [(vlan.primaryVlanId, vlan.secondaryVlanId) for vlan in dvs.config.pvlanConfig if vlan.pvlanType == 'isolated']

    def allocate_vlan(self):
        return self._vlans.pop(0)

    def free_vlan(self, vlan):
        self._vlans.append(vlan)

class VcenterVlanMgr(VcenterPvtVlanMgr):

    __metaclass__ = Singleton

    def __init__(self, dvs):
        self._vlans = list(range(1,4096)) 


class VcenterOrchestrator(Orchestrator):

    def __init__(self, inputs, host, port, user, pwd, dc_name, vnc, logger):
        super(VcenterOrchestrator, self).__init__(inputs, vnc, logger)
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
        if self._inputs.orchestrator == 'vcenter':
            self._vlanmgmt = VcenterPvtVlanMgr(self._vs)
        else: 
            self._vlanmgmt = VcenterVlanMgr(self._vs)
        self._create_keypair()
        self._nfs_ds = NFSDatastore(self._inputs, self)
        self.enable_vmotion(self.get_hosts())

    def is_feature_supported(self, feature):
        unsupported_features = ['multi-subnet', 'multi-tenant', 'multi-ipam', 'service-instance', 'ipv6']
        return feature not in unsupported_features

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
            for dv in dvs:
                if dv.name in self._inputs.dv_switch:
                     self._vs = dvs[0]
                     break
        else:
            self._vs = dvs[0]

        self._clusters_hosts = self._get_clusters_hosts()
        if len(self.get_zones()) == 0:
            raise Exception("Datacenter %s has no clusters" % self._dc_name)
        if len(self.get_hosts()) == 0:
            raise Exception("Datacenter %s has no hosts" % self._dc_name)
        self._computes = self._get_computes()

    def _find_obj (self, root, vimtype, param):
        self._content = self._si.RetrieveContent()
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

    def get_image_name_for_zone(self, image_name='ubuntu', zone=None):
        return image_name

    def get_image(self, *args, **kwargs):
        pass

    def get_flavor(self, *args, **kwargs):
        pass

    def get_default_image_flavor(self, *args, **kwargs):
        pass

    def enable_vmotion(self, hosts):
        for host in hosts:
            username = self._inputs.host_data[host]['username']
            password = self._inputs.host_data[host]['password']
            with settings(host_string=username+'@'+host, password=password,
                      warn_only = True, shell = '/bin/sh -l -c'):
                 run('vim-cmd hostsvc/vmotion/vnic_set vmk0')

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
             os.getenv('IMAGE_WEB_SERVER', '10.204.216.50')
        if not vmdk:
            vmdk = self._images_info[image]['name']
        if not vmx or not loc or not vmdk or ('vmdk' not in vmdk):
            raise Exception("no suitable vmdk or template for %s" % image)

        user = self._inputs.host_data[host.name]['username']
        pwd  = self._inputs.host_data[host.name]['password']
        url = 'http://%s/%s/' % (webserver, loc)
        url_vmx  = url + vmx
        url_vmdk = url + vmdk
        dst  =  self._nfs_ds.vcpath + image + '/'
        dst_vmdk = dst + image + '.vmdk'
        tmp_vmdk = dst + vmdk
        with settings(host_string='%s@%s' % (user, host.name), password=pwd,
                      warn_only = True, shell = '/bin/sh -l -c'):
            run('mkdir -p %s' % dst)
            run('wget %s -P %s' % (url_vmx, dst))
            run('wget %s -P %s' % (url_vmdk, dst))
            run('vmkfstools -i %s -d zeroedthick %s' % (tmp_vmdk, dst_vmdk))
            run('rm %s' % tmp_vmdk)

        return self._nfs_ds.name, image + '/' + vmx

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
            sg_ids = kwargs.get('sg_ids', [])
            for sg_id in sg_ids:
                 self.add_security_group(vm_id=vm.id, sg_id=sg_id)
        return objs

    def delete_vm(self, vm, **kwargs):
        vm_obj = self._find_obj(self._dc, 'vm', {'name' : vm.name})
        if vm_obj:
            if vm_obj.runtime.powerState != 'poweredOff':
                _wait_for_task(vm_obj.PowerOff())
            _wait_for_task(vm_obj.Destroy())

    @retry(tries=30, delay=5)
    def wait_till_vm_is_active(self, vm_obj, **kwargs):
        vm = self._find_obj(self._dc, 'vm', {'name' : vm_obj.name})
        return vm.runtime.powerState == 'poweredOn'

    def wait_till_vm_status(self, vm_obj, status):
        raise Exception('Unimplemented interface')

    def enter_maintenance_mode(self, name):
        host = self._find_obj(self._dc, 'host', {'name' : name})
        assert host, "Unable to find host %s" % name
        if host.runtime.inMaintenanceMode:
            self._log.debug("Host %s already in maintenance mode" % name)
        for vm in host.vm:
            if vm.summary.config.template:
                continue
            self._log.debug("Powering off %s" % vm.name)
            _wait_for_task(vm.PowerOff())
        self._log.debug("EnterMaintenence mode on host %s" % name)
        _wait_for_task(host.EnterMaintenanceMode(timeout=10))

    def exit_maintenance_mode(self, name):
        host = self._find_obj(self._dc, 'host', {'name' : name})
        assert host, "Unable to find host %s" % name
        if not host.runtime.inMaintenanceMode:
            self._log.debug("Host %s not in maintenance mode" % name)
        self._log.debug("ExitMaintenence mode on host %s" % name)
        _wait_for_task(host.ExitMaintenanceMode(timeout=10))
        for vm in host.vm:
            if vm.summary.config.template:
                continue
            self._log.debug("Powering on %s" % vm.name)
            _wait_for_task(vm.PowerOn())

    def add_networks_to_vm(self, vm_obj, vns):
        nets = [self._find_obj(self._dc, 'dvs.PortGroup', {'name':vn_obj.name}) for vn_obj in vns]
        vm_obj.add_networks(nets)

    def delete_networks_from_vm(self, vm_obj, vns):
        nets = [self._find_obj(self._dc, 'dvs.PortGroup', {'name':vn_obj.name}) for vn_obj in vns]
        vm_obj.delete_networks(nets)

    def change_network_to_vm(self,vm_obj,vn):
        net = self._find_obj(self._dc, 'dvs.PortGroup', {'name':vn})
        vm_obj.change_networks(net)

    def get_host_of_vm(self, vm_obj):
        host = self._find_obj(self._dc, 'host', {'name' : vm_obj.host})
        contrail_vm = None
        for vm in host.vm:
            if 'ContrailVM' in vm.name:
                contrail_vm = vm
                return self._inputs.host_data[contrail_vm.summary.guest.ipAddress]['name']
        #for vcenter and vcenter as compute mode, contrail_vm would be in the esxi server
        #but for vcenter gateway, its a physical server configured to work as the gateway
        #the vcenter gateway info would be captured in contrail_test_init.py
        return self._inputs.get_vcenter_gateway()

    def get_networks_of_vm(self, vm_obj, **kwargs):
         return vm_obj.nets[:]

    @retry(tries=10, delay=5)
    def is_vm_deleted(self, vm_obj, **kwargs):
        return self._find_obj(self._dc, 'vm', {'name' : vm_obj.name}) == None

    def get_vm_if_present(self, vm_name, **kwargs):
        vmobj = self._find_obj(self._dc, 'vm', {'name' : vm_name})
        if vmobj:
           return VcenterVM.create_from_vmobj(self, vmobj)
        return None

    def get_vm_by_id(self, vm_id, **kwargs):
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
    def get_vm_detail(self, vm_obj, **kwargs):
        return vm_obj.get()

    def get_console_output(self, vm_obj, **kwargs):
        return None

    def get_vm_ip(self, vm_obj, vn_name=None, **kwargs):
        self.get_vm_detail(vm_obj)
        if vn_name:
            ret = vm_obj.ips.get(vn_name, None)
        else:
            ret = vm_obj.ips.values()
        return [ret]

    def migrate_vm(self, vm_obj, host):
        if host == vm_obj.host:
            self._log.debug("Target Host %s is same as current host %s" % (host, vm_obj.host))
            return
        tgt = self._find_obj(self._dc, 'host', {'name':host})
        assert tgt, 'Migration failed, no such host:%s' % host
        vm = self._find_obj(self._dc, 'vm', {'name' : vm_obj.name})
        _wait_for_task(vm.RelocateVM_Task(_vim_obj('vm.Reloc',host=tgt,datastore=tgt.datastore[0])))

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
                              'ip.Pool', {'name' : 'pool-'+name}):
            raise Exception('A VN %s or ip pool %s, exists with the name' % (name, 'pool-'+name))
        if len(subnets) != 1:
            raise Exception('Cannot create VN with %d subnets' % len(subnets))
        vlan = self._vlanmgmt.allocate_vlan()
        if not vlan:
            raise Exception("Vlans exhausted")
        try:
            dhcp = kwargs.get('enable_dhcp', True)
            return VcenterVN.create_in_vcenter(self, name, vlan, subnets, dhcp)
        except:
            self._vlanmgmt.free_vlan(vlan)
            raise

    def delete_vn(self, vn_obj, **kwargs):
        self._vlanmgmt.free_vlan(vn_obj.vlan)
        try: #Sometimes the ip pool delete fails in vcenter - not root caused yet.
             #Till its completely debugged, handled the exception.
            pg = self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vn_obj.name})
            pg.Destroy()
            self._content.ipPoolManager.DestroyIpPool(self._dc, vn_obj.ip_pool_id, True)
        except Exception as e:
            return True
        return True

    def get_vn_obj_if_present(self, vn_name, **kwargs):
        pg = self._find_obj(self._dc, 'dvs.PortGroup', {'name' : vn_name})
        if pg:
           return VcenterVN.create_from_vnobj(self, pg)
        return None

    def get_vn_obj_from_id(self, vn_id):
        obj = self._vnc.virtual_network_read(id=vn_id)
        return self.get_vn_obj_if_present(obj.name)

    def get_vn_name(self, vn_obj, **kwargs):
        return vn_obj.name

    def get_vn_id(self, vnobj, **kwargs):
        if not vnobj.uuid:
            vnobj.get()
        return vnobj.uuid

    def get_image_name_for_zone(self, image_name='ubuntu', zone=None):
        return image_name

    def run_a_command(self, vm_id , vm_user, vm_password, path_to_cmd, cmd_args = None):
        vm = self._find_obj(self._dc, 'vm', {'summary.config.instanceUuid':vm_id})
        creds = _vim_obj('vm.PassAuth', username = vm_user, password = vm_password)
        ps = _vim_obj('vm.Prog', programPath=path_to_cmd, arguments=cmd_args)
        pm = self._content.guestOperationsManager.processManager
        res = pm.StartProgramInGuest(vm, creds, ps)
        return res

    def get_vm_tap_interface(self,obj):
        return obj['parent_interface']

    def get_security_group(self, sg, **kwargs):
        ret = super(VcenterOrchestrator, self).get_security_group(sg)
        if ret:
            return ret
        return super(VcenterOrchestrator, self).get_security_group(['default-domain', 'vCenter', sg])

    def get_vcenter_introspect(self):
        return vcenter_verification.VMWareVerificationLib(self._inputs)

    def verify_vm_in_vcenter(self, vm_obj):
        vm_name = vm_obj.name
        vrouter = self._inputs.host_data[self.get_host_of_vm(vm_obj)]['host_ip']
        inspect = self.get_vcenter_introspect()
        return inspect.verify_vm_in_vcenter(vrouter,vm_name)

    def verify_vm_not_in_vcenter(self,vm_obj):
        vm_name = vm_obj.name
        vrouter = self._inputs.host_data[self.get_host_of_vm(vm_obj)]['host_ip']
        inspect = self.get_vcenter_introspect()
        return inspect.verify_vm_not_in_vcenter(vrouter,vm_name)

class Subnets(object):

    def __init__(self,subnet):
        self.subnet = subnet
        self.pefix = IPNetwork(self.subnet)

    @property
    def prefix(self):
        return self.pefix

    @property
    def hosts(self):
        return self.pefix.iter_hosts()

    @property
    def netmask(self):
        return self.pefix.netmask

    @property
    def sub_network(self):
        return self.pefix.network

    @property
    def range(self):
        ip_list = list(self.hosts)
        range = str(ip_list[0]) + '#' + str(len(ip_list))
        return range

    @property
    def range2(self):
        ip_list = list(self.hosts)
        # vmware adds to the first given ip for count of IP's
        count = len(ip_list) - 2
        range = str(ip_list[2]) + '#' + str(count)
        return range

class IPv4Subnet(Subnets):

    def __init__(self,subnet):
        super(IPv4Subnet,self).__init__(subnet)

class IPv6Subnet(Subnets):

    def __init__(self,subnet):
        super(IPv6Subnet,self).__init__(subnet)

    @property
    def range(self):
        ip_list = self.pefix.iter_hosts()
        ip = next(ip_list)
        ip = next(ip_list)
        range = str(ip) + '#' + '255'
        return range

class VcenterVN:

    @staticmethod
    def create_in_vcenter(vcenter, name, vlan, prefix, dhcp=True):
        vn = VcenterVN()
        vn.vcenter = vcenter
        vn.name = name
        vn.vlan = vlan
        vn.uuid = None

        v6_network = None
        for p in prefix:
            if (IPNetwork(p['cidr']).version == 4):
                v4_network = IPv4Subnet(p['cidr'])
            if (IPNetwork(p['cidr']).version == 6):
                v6_network = IPv6Subnet(p['cidr'])
        ip_list = list(v4_network.hosts)

        ipam_setting = [_vim_obj('dvs.Blob', key='external_ipam', opaqueData='true')] if not dhcp else None
        if len(str(vlan)) > 1:
            spec = _vim_obj('dvs.ConfigSpec', name=name, type='earlyBinding', numPorts = len(ip_list),
                       defaultPortConfig=_vim_obj('dvs.PortConfig',
                       vlan=_vim_obj('dvs.PVLan', pvlanId=vlan[1])),
                       vendorSpecificConfig=ipam_setting)
        else:
            spec = _vim_obj('dvs.ConfigSpec', name=name, type='earlyBinding', numPorts = len(ip_list),
                       defaultPortConfig=_vim_obj('dvs.PortConfig',
                        vlan=_vim_obj('dvs.VLan', vlanId=vlan),
                       securityPolicy=_vim_obj('dvs.PortGroupSecurity',
                                      allowPromiscuous=vim.BoolPolicy(value=True), 
                                      macChanges=vim.BoolPolicy(value=True),
                                      forgedTransmits=vim.BoolPolicy(value=True))),
                       vendorSpecificConfig=ipam_setting)

        _wait_for_task(vcenter._vs.AddDVPortgroup_Task([spec]))
        pg = vcenter._find_obj(vcenter._dc, 'dvs.PortGroup', {'name' : name})

        if v6_network:
            ip_pool = _vim_obj('ip.Pool', name='ip-pool-for-'+name,
                              ipv4Config=_vim_obj('ip.Config',
                                                 subnetAddress = str(v4_network.sub_network),
                                                 netmask = str(v4_network.netmask),
                                                 range = v4_network.range,
                                                 ipPoolEnabled = dhcp),
                              ipv6Config=_vim_obj('ip.Config',
                                                 subnetAddress = str(v6_network.sub_network),
                                                 netmask = str(v6_network.netmask),
                                                 range = v6_network.range,
                                                 ipPoolEnabled = dhcp),
                              networkAssociation = [_vim_obj('ip.Association',
                                                            network=pg,
                                                            networkName=name)])
        else:
            ip_pool = _vim_obj('ip.Pool', name='ip-pool-for-'+name,
                              ipv4Config=_vim_obj('ip.Config',
                                                 subnetAddress = str(v4_network.sub_network),
                                                 netmask = str(v4_network.netmask),
                                                 range = v4_network.range2,
                                                 ipPoolEnabled = dhcp),
                              networkAssociation = [_vim_obj('ip.Association',
                                                            network=pg,
                                                            networkName=name)])
        vn.ip_pool_id = vcenter._content.ipPoolManager.CreateIpPool(vcenter._dc, ip_pool)
        time.sleep(2)
        return vn

    @staticmethod
    def create_from_vnobj(vcenter, vn_obj):
        vn = VcenterVN()
        vn.vcenter = vcenter
        vn.name = vn_obj.name
        vn.uuid = None
        try:#when vcenter only mode, we need to get the pvlan id
            vlan = vn_obj.config.defaultPortConfig.vlan.pvlanId
            vn.vlan = (vlan - 1, vlan)
        except Exception as e:#vcenter gateway mode,where we create normal vlan
            vlan = vn_obj.config.defaultPortConfig.vlan.vlanId
            vn.vlan =  vlan
            
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
        vm.networks = networks
        vm.nets = [net.name for net in networks]
        #below 2 attributes needed for vcenter gateway
        #as we create vmis/logical interface, we can update the below lists lif and port objects, it will ease the delete vm 
        #, we just need to  call vm.ports[<index>].cleanUP and same for lif objects 
        vm.ports = []
        vm.lifs = []

        intfs = []
        switch_id = vcenter._vs.uuid
        for net in networks:
            spec = _vim_obj('dev.VDSpec', operation=_vimtype_dict['dev.Ops.add'],
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
        self.host = vm.runtime.host.name
        self.id = vm.summary.config.instanceUuid
        self.macs = {}
        self.ips = {}
        tools_status = vm.guest.toolsStatus
        if (tools_status == 'toolsNotInstalled' or
                tools_status == 'toolsNotRunning'):
            self.install_vmware_tools(self.vcenter,vm)
        for intf in vm.guest.net:
            self.macs[intf.network] = intf.macAddress
            self.ips[intf.network] = intf.ipAddress[0]
        return len(self.ips) == len(self.nets)

    def reboot(self, r):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        assert r != 'SOFT', 'Soft reboot is not supported, use VMFixture.run_cmd_on_vm'
        _wait_for_task(vm.ResetVM_Task())

    def add_networks(self, nets):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        intfs = []
        for net in nets:
            spec = _vim_obj('dev.VDSpec', operation=_vimtype_dict['dev.Ops.add'],
                           device=_vim_obj('dev.E1000',
                                          addressType='Generated',
                                          connectable=_vim_obj('dev.ConnectInfo',
                                                              startConnected=True,
                                                              allowGuestControl=True),
                                          backing=_vim_obj('dev.DVPBackingInfo',
                                                          port = _vim_obj('dvs.PortConn',
                                                          switchUuid=self.vcenter._vs.uuid,
                                                          portgroupKey=net.key))))
            intfs.append(spec)

        cfg = _vim_obj('vm.Config', deviceChange=intfs)
        _wait_for_task(vm.ReconfigVM_Task(cfg))

    def delete_networks(self, nets):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        intfs = []
        for net in nets:
            for dev in vm.config.hardware.device:
                if isinstance(dev, _vimtype_dict['dev.E1000']) and dev.backing.port.portgroupKey == net.key:
                    spec = _vim_obj('dev.VDSpec', operation=_vimtype_dict['dev.Ops.remove'],
                                    device=dev)
                    intfs.append(spec)

        cfg = _vim_obj('vm.Config', deviceChange=intfs)
        _wait_for_task(vm.ReconfigVM_Task(cfg))

    def change_networks(self,net):
        vm = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : self.name})
        device_change = []
        try:
            for dev in vm.config.hardware.device:
                if isinstance(dev, _vimtype_dict['dev.E1000']):
                    nicspec = _vimtype_dict['dev.VDSpec']()
                    nicspec.operation = _vimtype_dict['dev.Ops.edit']
                    nicspec.device = dev
                    nicspec.device.wakeOnLanEnabled = True
                    dvs_port_connection = _vimtype_dict['dvs.PortConn']() 
                    dvs_port_connection.portgroupKey = net.key
                    dvs_port_connection.switchUuid= self.vcenter._vs.uuid
                    nicspec.device.backing = _vimtype_dict['dev.DVPBackingInfo']()
                    nicspec.device.backing.port = dvs_port_connection
             
                    nicspec.device.connectable = _vimtype_dict['dev.ConnectInfo']()
                    nicspec.device.connectable.startConnected = True
                    nicspec.device.connectable.allowGuestControl = True
                    device_change.append(nicspec)

                    break
            cfg = _vim_obj('vm.Config', deviceChange=device_change)
            _wait_for_task(vm.ReconfigVM_Task(cfg))
            vmobj = self.vcenter._find_obj(self.vcenter._dc, 'vm', {'name' : vm.name})
            self.get(vmobj)
            #return vm
        except vmodl.MethodFault as error:
            self._log.debug("Caught vmodl fault : %s" %error.msg)

    @retry(tries=30, delay=5)
    def assign_ip(self, intf, ip, gw, mask='255.255.255.0'):
        cmd_path = '/usr/bin/sudo'
        user = 'ubuntu'
        password = 'ubuntu'
        try:
            args = 'killall -9 dhclient3'
            self.vcenter.run_a_command(self.id,user,password,cmd_path,args)
            args = 'ifconfig %s %s netmask %s' % (intf, ip, mask)
            self.vcenter.run_a_command(self.id,user,password,cmd_path,args)
            args = 'route add default gw %s' % (gw)
            self.vcenter.run_a_command(self.id,user,password,cmd_path,args)
            args = 'ifconfig %s up' % (intf)
            self.vcenter.run_a_command(self.id,user,password,cmd_path,args)
        except Exception:
            return False
        time.sleep(60)
        return True

    @retry(tries=120, delay=5)
    def install_vmware_tools(self, vcenter ,vm):
        if not vm.guest.guestOperationsReady:
            self.vcenter._log.error("Vm not yet operational.retrying....")
            return False
        cmd_path = '/usr/bin/sudo'
        user = 'ubuntu'
        password = 'ubuntu'
        vm_id = self.id
        cmd = './vmware-tools-distrib/vmware-install.pl -d'#Assuming that package is there in the disk image,
        try:                                               #but not installed 
            vcenter.run_a_command(vm_id,user,password,cmd_path,cmd)
            return True
        except Exception as e:
            return False

    def bring_up_interfaces(self, vcenter ,vm , intfs=[]):
        time.sleep(20)
        cmd_path = '/usr/bin/sudo'
        user = 'ubuntu'
        password = 'ubuntu'
        vm_id = vm.id
        for intf in intfs: 
            args = 'ifconfig %s up'%(intf)
            try:
                vcenter.run_a_command(vm_id,user,password,cmd_path,args)
            except Exception as e:
                print e
            args = 'dhclient %s'%(intf)
            try:
                vcenter.run_a_command(vm_id,user,password,cmd_path,args)
            except Exception as e:
                print e
        time.sleep(20)

class VcenterAuth(OrchestratorAuth):

    def __init__(self, user, passwd, project_name, inputs, domain='default-domain'):
        self.inputs = inputs
        self.user = user
        self.passwd = passwd
        self.domain = domain
        self.project_name = project_name
        use_ssl = self.inputs.api_protocol == 'https'
        self.vnc = VncApi(username=user, password=passwd,
                          tenant_name=project_name,
                          api_server_host=self.inputs.cfgm_ip,
                          api_server_port=self.inputs.api_server_port,
                          api_server_use_ssl=use_ssl)

    def get_project_id(self, project_name=None, domain_id=None):
       if not project_name:
           project_name = self.project_name
       fq_name = [unicode(self.domain), unicode(project_name)]
       obj = self.vnc.project_read(fq_name=fq_name)
       if obj:
           return obj.get_uuid()
       return None

    def reauth(self):
        raise Exception('Unimplemented interface')

    def create_project(self, name):
        raise Exception('Unimplemented interface')

    def delete_project(self, name):
        raise Exception('Unimplemented interface')

    def create_user(self, user, passwd):
        raise Exception('Unimplemented interface')

    def delete_user(self, user):
        raise Exception('Unimplemented interface')

    def add_user_to_project(self, user, project):
        raise Exception('Unimplemented interface')
