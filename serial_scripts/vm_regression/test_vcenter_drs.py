from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from .base import *
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
from fixtures import Fixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common import isolated_creds
from common.connections import *
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from vcenter import *
import test
from tcutils.contrail_status_check import ContrailStatusChecker
import re

data = {} #needed for print_ips functions

class TestVcenterSerial(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenterSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenterSerial, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
            return(False, 'Skipping Test. Require %s setup' % 'vcenter')
        return (True, None)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_drs(self):
        '''
        Description: Trigger drs in vcenter
        Test steps:

               1. Create a VN and launch 10 VMs.
               2. ping between the vms
               3.Put hosts in maintenance mode
               4.Allow drs to occure
               5.Verify no duplictae vlan/ip for any vms
               6.Ping between vms
        Pass criteria: Ping between the VMs should work after drs.
        Maintainer : sandipd@juniper.net
        '''
        self.orch.set_migration(True)
        ##################################
        # Sometimes there are some stranded VM left on Local Datastore from the previous testcases
        # Due to which ESX does not completes entering to Maintance mode,-
        # As those VMs can't be migrated, and testcase fails.
        # Added the workaround to check for any STRANDED VM present in Cluster-
        # Before starting the testcase .. and IF present delete them first.
        ##################################
        vm_list = self.orch.get_vm_list("ctest")
        if len(vm_list) != 0:
           self.logger.info ("There are some stranded VM on cluster, Deleting them first")
           for vm in vm_list:
               self.logger.info("Deleting VM %s" %vm.name)
               self.orch.delete_vm(vm)

        vn1_name = get_random_name('test_vn')
        guest_vms = []
        vn1_fixture = self.create_vn(vn1_name, [get_random_cidr()])
        for _ in range(10):
            vm_name = get_random_name('gutest_vm')
            self.logger.info("Deploying %s VM %s", _+1, vm_name)
            vm = self.create_vm(vn_fixture=vn1_fixture, vm_name=vm_name,image_name='vcenter_tiny_vm')
            guest_vms.append(vm)
        for vm in guest_vms:
            vm.wait_till_vm_is_up()
        src_vm = guest_vms[0]
        for vm in guest_vms:
            assert src_vm.ping_with_certainty(dst_vm_fixture=vm),\
                "Ping from %s to %s failed" % (src_vm.vm_name, vm.vm_name)
        vc_orch = self.connections.orch
        assert if_failed(self.inputs,self.logger)
        self.logger.info("Triggering MAINTANCE MODE for ESXi Hosts")
        assert verify_trigger(self.inputs,'maintenance_mode',self.logger)
        ##################################################################
        # Due to Maintenance Mode on ESXi Contrail VM also put to Shutdown by vCenter.
        # Due to which, Previous SSH TCP session is also closed abruptly on the server side.
        # When in next step Client tries to do ssh and execute some commands
        # Connection reset ERROR occurs on the Socket and Testcase Fails.
        # Applying the Workaround (FIX) for client to wait for SSH to Active and re-initiate TCP session
        #################################################################
        for compute in self.inputs.compute_ips:
            self.logger.info("Waiting for SSH Active on Compute Node %s" %compute)
            wait_for_ssh_on_node(compute, self.inputs.host_data[compute]['password'])
        src_vm.read(True)
        for vm in guest_vms:
            assert src_vm.ping_with_certainty(dst_vm_fixture=vm),\
                "Ping from %s to %s failed" % (src_vm.vm_name, vm.vm_name)

     # end of test test_vcenter_drs

def getNICs(summary, guest):
    nics = {}
    for nic in guest.net:
        if nic.network:  # Only return adapter backed interfaces
            if nic.ipConfig is not None and nic.ipConfig.ipAddress is not None:
                nics[nic.macAddress] = {}  # Use mac as uniq ID for nic
                nics[nic.macAddress]['netlabel'] = nic.network
                ipconf = nic.ipConfig.ipAddress
                for ip in ipconf:
                    if ":" not in ip.ipAddress:  # Only grab ipv4 addresses
                        nics[nic.macAddress]['ip'] = ip.ipAddress
                        nics[nic.macAddress]['prefix'] = ip.prefixLength
                        nics[nic.macAddress]['connected'] = nic.connected
    return nics

def vmsummary(summary, guest):
    vmsum = {}
    config = summary.config
    net = getNICs(summary, guest)
    vmsum['mem'] = str(old_div(config.memorySizeMB, 1024))
    vmsum['diskGB'] = str("%.2f" % (old_div(summary.storage.committed, 1024**3)))
    vmsum['cpu'] = str(config.numCpu)
    vmsum['path'] = config.vmPathName
    vmsum['ostype'] = config.guestFullName
    vmsum['state'] = summary.runtime.powerState
    vmsum['annotation'] = config.annotation if config.annotation else ''
    vmsum['net'] = net

    return vmsum

def vm2dict(dc, cluster, host, vm, summary):
    # If nested folder path is required, split into a separate function
    vmname = vm.summary.config.name
    ports = PrintVmInfo(vm)#It returns the list of all ports of the port-group this vm connected to
    for port in ports:
        if port.connectee.connectedEntity == vm:
            hardware =  port.connectee.connectedEntity.config.hardware.device
            macaddress = None
            for d in hardware:
                if hasattr(d, 'macAddress'):
                    macaddress = d.macAddress
            vlanId = port.config.setting.vlan.vlanId 
            host = vm.runtime.host.name
            key = port.key
    vmnet = summary['net']
    if vmnet:
        for val in list(vmnet.values()):
            try:
                ip = val['ip']
                return NameToIPMap(vmname=vmname,
                             ip=ip,
                             vlanId=vlanId,
                             host=host,port=key,
                             macaddress = macaddress)
            except Exception as e:
                print('%s:%s'%(vmname,val))
                return NameToIPMap(vmname=vmname,
                           ip=None,
                           vlanId=None,
                           host=host,port=key,  
                           macaddress = macaddress)
    else:
        return NameToIPMap(vmname=vmname,
                           ip=None,
                           vlanId=None,
                           host=host,port=key,  
                           macaddress = macaddress)
    
class NameToIPMap(object):
    def __init__(self,vmname=None,ip=None,
                 vlanId=None,host=None,
                 port=None,macaddress=None):
        self.name = vmname
        self.ip = ip
        self.vlanId = vlanId
        self.host = host
        self.port = port
        self.macaddress = macaddress

    def __str__(self):
        return str(('vm name: '+ str(self.name),'ip: '+str(self.ip),\
                   'vlan: '+str(self.vlanId),'esxi_host: '+str(self.host)\
                    ,'port_group_port_key: '+str(self.port),'vm mac: '+ str(self.macaddress)))

def PrintVmInfo(vm):
    vmPowerState = vm.runtime.powerState
    #print("Found VM:", vm.name + "(" + vmPowerState + ")")
    return GetVMNics(vm)

       
def GetVMNics(vm):
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            dev_backing = dev.backing
            portGroup = None
            vlanId = None
            vSwitch = None
            if hasattr(dev_backing, 'port'):
                portGroupKey = dev.backing.port.portgroupKey
                dvsUuid = dev.backing.port.switchUuid
                try:
                    dvs = content.dvSwitchManager.QueryDvsByUuid(dvsUuid)
                except:
                    portGroup = "** Error: DVS not found **"
                    vlanId = "NA"
                    vSwitch = "NA"
                else:
                    pgObj = dvs.LookupDvPortGroup(portGroupKey)
                    ports = search_port(dvs,portGroupKey)
                    return ports
                    portGroup = pgObj.config.name
                    vlanId = str(pgObj.config.defaultPortConfig.vlan.vlanId)
                    vSwitch = str(dvs.name)
            else:
                portGroup = dev.backing.network.name
                vmHost = vm.runtime.host
                # global variable hosts is a list, not a dict
                host_pos = hosts.index(vmHost)
                viewHost = hosts[host_pos]
                # global variable hostPgDict stores portgroups per host
                pgs = hostPgDict[viewHost]
                for p in pgs:
                    if portGroup in p.key:
                        vlanId = str(p.spec.vlanId)
                        vSwitch = str(p.spec.vswitchName)
            if portGroup is None:
                portGroup = 'NA'
            if vlanId is None:
                vlanId = 'NA'
            if vSwitch is None:
                vSwitch = 'NA'
            print('\t' + dev.deviceInfo.label + '->' + dev.macAddress +
                  ' @ ' + vSwitch + '->' + portGroup +
                  ' (VLAN ' + vlanId + ')')

def GetVMHosts(content):
    #print("Getting all ESX hosts ...")
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view if host in hosts]
    host_view.Destroy()
    return obj


def GetVMs(content):
    print("Getting all VMs ...")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj


def GetHostsPortgroups(hosts):
    #print("Collecting portgroups on all hosts. This may take a while ...")
    hostPgDict = {}
    for host in hosts:
        pgs = host.config.network.portgroup
        hostPgDict[host] = pgs
        #print("\tHost {} done.".format(host.name))
    #print("\tPortgroup collection complete.")
    return hostPgDict

def search_port(dvs, portgroupkey):
    search_portkey = []
    criteria = vim.dvs.PortCriteria()
    criteria.connected = True
    criteria.inside = True
    criteria.portgroupKey = portgroupkey
    ports = dvs.FetchDVPorts(criteria)
    return ports


def get_conn(args):
    """
    Let this thing fly
    """

    # connect this thing
    from pyVmomi import vim
    from pyVim.connect import SmartConnect, Disconnect
    import atexit
    try:
        si = SmartConnect(host=args.host, port=args.port, user=args.user, pwd=args.password)
    except Exception as exc:
        if isinstance(exc, vim.fault.HostConnectFault) and '[SSL: CERTIFICATE_VERIFY_FAILED]' in exc.msg:
            try:
                import ssl
                default_context = ssl._create_default_https_context
                ssl._create_default_https_context = ssl._create_unverified_context
                si = SmartConnect(
                    host=args.host,
                    port=args.port,
                    user=args.user,
                    pwd=args.password,
                    )
                ssl._create_default_https_context = default_context
            except Exception as exc1:
                raise Exception(exc1)
        else:
            import ssl
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            si = SmartConnect(
                   host=args.host,
                   port=args.port,
                   user=args.user,
                   pwd=args.password,
                   sslContext=context)
    atexit.register(Disconnect, si)
    return si

class Args(object):
    def __init__(self,host,port,user,password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

def print_ips(inputs): 
    inputs = inputs
    server = inputs.inputs.vcenter_server
    port = inputs.inputs.vcenter_port
    user = inputs.inputs.vcenter_username
    password = inputs.inputs.vcenter_password
    args = Args(server,port,user,password)
    si = get_conn(args)
    vm_list = []
    #si = vc.get_si()

    global content, hosts, hostPgDict,dc_name
    content = si.RetrieveContent()
    dc_name = inputs.inputs.vcenter_dc

    children = content.rootFolder.childEntity
    for child in children:  # Iterate though DataCenters
        dc = child
        if dc.name != dc_name:
            continue
        data[dc.name] = {}  # Add data Centers to data dict
        clusters = dc.hostFolder.childEntity
        for cluster in clusters:  # Iterate through the clusters in the DC
            # Add Clusters to data dict
            data[dc.name][cluster.name] = {}
            hosts = cluster.host  # Variable to make pep8 compliance
            for host in hosts:  # Iterate through Hosts in the Cluster
                hostname = host.summary.config.name
                # Add VMs to data dict by config name
                data[dc.name][cluster.name][hostname] = {}
                vms = host.vm
                for vm in vms:  # Iterate through each VM on the host
                    if vm.config.template:
                        continue 
                    vmname = vm.summary.config.name
                    if 'ContrailVM' in vmname:
                        continue
                    data[dc.name][cluster.name][hostname][vmname] = {}
                    summary = vmsummary(vm.summary, vm.guest)
                    vm_list.append(vm2dict(dc.name, cluster.name, hostname, vm, summary))
#    for vm in vm_list:
#        print "Vm: %s"%vm
    return vm_list    
      
@retry(tries=10, delay=3)
def if_failed(inputs,logger):
    inputs = inputs 
    vm_list = print_ips(inputs)
    if ip_not_set(vm_list,logger):
        logger.info('Ip not set')
        return False
    if not duplicate_ip(vm_list,logger):
        logger.info('Duplicate ip')
        return False
    if not duplicate_vlan(vm_list,logger):
        logger.info('Duplicate vlan') 
        return False
    if not if_any_change(vm_list,None,logger):
        logger.info('Duplicate vlan') 
        return False
    return True
     
def ip_not_set(vm_list,logger):
    for vm in vm_list:
        if hasattr(vm, 'ip'):
            if vm.ip:
                continue
            else:
                logger.info('IP not set for %s: '%vm)
                return True
        else: 
            logger.info('IP not set for %s: '%vm)
    return False

def duplicate_ip(vm_list,logger):
    ips = []
    for vm in vm_list:
        if hasattr(vm, 'ip'):
            if vm.ip and vm.ip not in ips:
                ips.append(vm.ip)
            else:
                logger.info('IP is duplicate for %s: '%vm)
                return False
        else:
            logger.info('IP not set for %s: '%vm)
    return True

def duplicate_vlan(vm_list,logger): 
    d = defaultdict(list)
    for vm in vm_list:
        d[vm.host].append(vm.vlanId)
    for k,v in d.items():
        lst = []
        for vlan in v:
            if vlan == 0:
                 logger.info("Vlan 0 was set")
            if vlan and vlan not in lst:
                lst.append(vlan)
            else:
                logger.info('Duplicate vlan %s in %s: '%(vlan,k))
                return False
    return True     

def if_any_change(vm_list1,vm_list2,logger):
    if not vm_list2:
        return True   
    vms = [vm for vm in vm_list1 for vm1 in vm_list2 if vm.name == vm1.name and vm.ip != vm1.ip]
    if vms:
        for vm in vms:
           logger.error("IP changed for vm %s"%(vm))  
           return False
    else:
        logger.info("IP did not change for any vm")   
    return True        
   
def verify_trigger(inputs,trigger,logger):
    inputs = inputs
    for host in hosts:
       vm_list1 = print_ips(inputs)
       enter_maintenance_mode(host) 
       time.sleep(120)
       vm_list2 = print_ips(inputs)
       if not if_failed(inputs,logger):
           return False
       if not if_any_change(vm_list1,vm_list2,logger):
           return False
       exit_maintenance_mode(host) 
       time.sleep(120)
       if not if_failed(inputs,logger):
           return False
       if not if_any_change(vm_list1,vm_list2,logger):
           return False
    return True
    #eval(trigger)

def enter_maintenance_mode(host):
    _wait_for_task(host.EnterMaintenanceMode(timeout=90))

def exit_maintenance_mode(host):
    _wait_for_task(host.ExitMaintenanceMode(timeout=90))

def _wait_for_task (task):
    time.sleep(2)
    state = task.info.state
    while (state == vim.TaskInfo.State.queued or
           state == vim.TaskInfo.State.running):
        time.sleep(2)
        state = task.info.state

    state = task.info.state
    if state != vim.TaskInfo.State.success:
        if state == vim.TaskInfo.State.error:
            raise ValueError(task.info.error.localizedMessage)
        raise ValueError("Something went wrong in wait_for_task")
    return
          
