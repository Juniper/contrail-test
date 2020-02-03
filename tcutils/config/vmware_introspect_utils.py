from __future__ import absolute_import
from builtins import object
import logging as LOG

from tcutils.verification_util import *
from .vnc_api_results import *
from tcutils.util import retry,istrue

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

def elem2dict(node, alist=False):
        d = list() if alist else dict()
        for e in node.iterchildren():
            #key = e.tag.split('}')[1] if '}' in e.tag else e.tag
            if e.tag == 'list':
                value = elem2dict(e, alist=True)
            else:
                value = e.text if e.text else elem2dict(e)
            if type(d) == type(list()):
                d.append(value)
            else:
                d[e.tag] = value
        return d

def get_vcenter_plugin_introspect_elements(vcenterclient):

    vcenterplugin = {}
    inspect = vcenterclient.get_vcenter_plugin_struct()
    children = inspect[0].getchildren()
    for child in children:
        if (child.tag == 'master'):
            master = Master(child)
            vcenterplugin['master'] = master.master
            if not istrue(master.master[0]):
                return False 
            else:
                return True
        elif (child.tag == 'pluginSessions'):
            session = PluginSessions(child)
            vcenterplugin['pluginSessions'] = session.pluginsessions
        elif (child.tag == 'vRouterStats'):
            vrouter = VRouterStats(child)
            vcenterplugin['vRouterStats'] = vrouter.vrouterstats
        elif (child.tag == 'ApiServerInfo'):
            api_info = ApiServerInfo(child)
            vcenterplugin['ApiServerInfo'] = api_info.apiserverinfo
        elif (child.tag == 'VCenterServerInfo'):
            vcntr_info = VCenterServerInfo(child)
            vcenterplugin['VCenterServerInfo'] = vcntr_info.vcenterserverinfo
        else:
            LOG.info( 'Invalid element')
    return vcenterplugin

def get_esxi_to_vrouter_mapping(vcenterclient,query_value):
    vrouter = []
    inspect = vcenterclient.get_vcenter_plugin_vrouter_up(query_value)
    try:
        for elem in inspect[0].getchildren():
            vrouter.append(elem2dict(elem))
    except Exception as e:
        LOG.exception(e)
    finally:
        return vrouter

def get_vrouter_details(vcenterclient,query_value):
    try:
        inspect = vcenterclient.get_vcenter_plugin_vrouter_details(query_value)
        return VRouterDetails(inspect[0])
    except Exception as e:
        LOG.exception(e)
        return None

def get_vm_details(vcenterclient,query_value):
    try:
        inspect = vcenterclient.get_vcm_vm_details(query_value)
        return VirtualMachinesInVcenter(inspect)
    except Exception as e:
        LOG.exception(e)
        return None

class VRouterDetails(Result):
    '''Vrouter details objects'''
    def __init__(self,d={}):
        super(VRouterDetails, self).__init__(d)
        self.virtual_machines = []
        self.state = self['state']
        self.esxiHost = self['EsxiHost']
        self.ip = self['ipAddr']
        self.virtual_networks = [VirtualNetworks(vn['name']) for vn in self['VirtualNetworks']['list']]
        for element in self['VirtualNetworks']['list']:
            net = element['name']
            for vm in element['VirtualMachineInterfaces']['list']:
                self.virtual_machines.append(VirtualMachinesInVcenter(net,vm)) 

class VirtualNetworks(object):
    '''Represents one virtual network in the vcenter'''
    def __init__(self,vn):
        self.name = vn

class VirtualMachinesInVcenter(object):
    '''Represents one vm in the vcenter introspect page'''
    def __init__(self,elems=[]):
        self.virtual_machine = {}
        for elem in elems:
            #mapping to each class to avoid if-else
            #tag uuid would map
            dct = eval(elem.tag + '(elem)')
            dct = dct.make_dict()
            self.virtual_machine.update(dct)

class uuid(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        d = {}
        d[self.d.tag] = self.d.text
        return d

class name(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        d = {}
        d[self.d.tag] = self.d.text
        return d

class host_uuid(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        d = {}
        d[self.d.tag] = self.d.text
        return d

class vrouter_uuid(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        d = {}
        d[self.d.tag] = self.d.text
        return d

class interfaces(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        intfs = []
        intf_dct = {}
        interfaces = self.d.xpath('./list/VirtualMachineInterfaceData')
        for intf in interfaces:
            intf_dct = {}
            for child in intf.getchildren():
                dct = {}
                dct[child.tag] = child.text
                intf_dct.update(dct)
            intfs.append(intf_dct)
        interfaces = {}
        interfaces['interfaces'] = intfs 
        return interfaces 
    
class VirtualMachinesInterface(object):
    def __init__(self,d):
        self.d = d
    def make_dict(self):
        pass

class Master(object):
    '''Represent vcenter plugin master'''
    def __init__(self,element):
        self.return_list = []
        d ={}
        d[element.tag] = element.text
        self.return_list.append(VMWarePluginResult(d))

    @property
    def master(self):
        return [ele.master() for ele in self.return_list]

class PluginSessions(object):
    '''Represent vcenter plugin pluginsessions'''
    def __init__(self,element):
        self.return_list = []
        d ={}
        d[element.tag] = element.text
        self.return_list.append(VMWarePluginResult(d))

    @property
    def pluginsessions(self):
        return [ele.pluginsessions() for ele in self.return_list]

class VRouterStats(object):
    '''Represent vcenter plugin vRouterStats'''
    def __init__(self,element):
        self.return_list = []
        vstats ={}
        stats =  element.getchildren()
        for stat in stats:
            ele = stat.getchildren()  
            for ele1 in ele:
                d = {}
                d[ele1.tag] = ele1.text  
                vstats.update(d)  
        vrouterStats={}
        vrouterStats['vRouterStats'] = vstats 
        self.return_list.append(VMWarePluginResult(vrouterStats))

    @property
    def vrouterstats(self):
        return [ele.vrouterstats() for ele in self.return_list]

class ApiServerInfo(object):
    '''Represent vcenter plugin ApiServerInfo'''
    def __init__(self,element):
        self.return_list = []
        cfgm_info ={}
        stats =  element.getchildren()
        for stat in stats:
            ele = stat.getchildren()  
            for ele1 in ele:
                d = {}
                d[ele1.tag] = ele1.text  
                cfgm_info.update(d)  
        api_info={}
        api_info['ApiServerInfo'] = cfgm_info 
        self.return_list.append(VMWarePluginResult(api_info))
    
    @property
    def apiserverinfo(self):
        return [ele.apiserverinfo() for ele in self.return_list]

class VCenterServerInfo(object):
    '''Represent vcenter plugin VCenterServerInfo'''
    def __init__(self,element):
        self.return_list = []
        cfgm_info ={}
        stats =  element.getchildren()
        for stat in stats:
            ele = stat.getchildren()  
            for ele1 in ele:
                d = {}
                d[ele1.tag] = ele1.text  
                cfgm_info.update(d)  
        api_info={}
        api_info['VCenterServerInfo'] = cfgm_info 
        self.return_list.append(VMWarePluginResult(api_info))
    
    @property
    def vcenterserverinfo(self):
        return [ele.vcenterserverinfo() for ele in self.return_list]

class VMWareInspect (VerificationUtilBase):

    def __init__(self, ip, logger=LOG, args=None):
        super(VMWareInspect, self).__init__(
            ip, 9090,XmlDrv, logger=logger, args=args)
        self.ip = ip

    def get_vcenter_plugin_struct(self):
        doms = self.dict_get('Snh_VCenterPluginInfo')
        plugin_structs = doms.xpath('./VCenterPlugin/VCenterPluginStruct')
        return plugin_structs

    def get_vcenter_plugin_vrouter_up(self,query_val,*args):
        path = 'Snh_vRoutersTotal?x=%s' %query_val
        val = self.dict_get(path)
        return val.xpath('./VirtualRouters/list')
    
    def get_vcenter_plugin_vrouter_details(self,query_val,*args):
        path = 'Snh_vRouterDetail?x=%s' %query_val
        val = self.dict_get(path)
        return val.xpath('./VRouterInfo/VRouterInfoStruct')
    
    def get_vcm_vm_details(self,query_val,*args):
        path = 'Snh_VirtualMachineRequest?uuid=&name=%s' %query_val
        val = self.dict_get(path)
        return val.xpath('./machines/list/VirtualMachineData')[0].getchildren()

class VMWarePluginResult(Result):
    '''
        Returns value from the below link
        http://<ip>:9090/Snh_VCenterPluginInfo
    '''
    
    def master(self):
        return self['master']

    def pluginsessions(self):
        return self['pluginSessions']

    def vrouterstats(self):
        return self['vRouterStats']

    def apiserverinfo(self):
        return self['ApiServerInfo']

    def vcenterserverinfo(self):
        return self['VCenterServerInfo']

if __name__ == '__main__':
    va = VMWareInspect('10.204.216.183')
    class Inputs(object):
        def __init__(self):
            self.cfgm_ips = ['10.204.216.61','10.204.216.62','10.204.216.63'] 
    r = get_vm_details(va,'test_vm1')
    import pdb;pdb.set_trace()
    import pprint
    pprint.pprint(r)
