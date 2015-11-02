import logging as LOG

from tcutils.verification_util import *
from vnc_api_results import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

def get_vcenter_plugin_introspect_elements(vcenterclient):

    vcenterplugin = {}
    inspect = vcenterclient.get_vcenter_plugin_struct()
    children = inspect[0].getchildren()
    for child in children:
        if (child.tag == 'master'):
            master = Master(child)
            vcenterplugin['master'] = master.master
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
            print 'Invalid element'
            continue
    return vcenterplugin

class Master():
    '''Represent vcenter plugin master'''
    def __init__(self,element):
        self.return_list = []
        d ={}
        d[element.tag] = element.text
        self.return_list.append(VMWarePluginResult(d))

    @property
    def master(self):
        return [ele.master() for ele in self.return_list]

class PluginSessions():
    '''Represent vcenter plugin pluginsessions'''
    def __init__(self,element):
        self.return_list = []
        d ={}
        d[element.tag] = element.text
        self.return_list.append(VMWarePluginResult(d))

    @property
    def pluginsessions(self):
        return [ele.pluginsessions() for ele in self.return_list]

class VRouterStats():
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

class ApiServerInfo():
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

class VCenterServerInfo():
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
            ip, 8777,XmlDrv, logger=logger, args=args)

    def get_vcenter_plugin_struct(self):
        doms = self.dict_get('Snh_VCenterPluginInfo')
        plugin_structs = doms.xpath('./VCenterPlugin/VCenterPluginStruct')
        return plugin_structs

class VMWarePluginResult(Result):
    '''
        Returns value from the below link
        http://<ip>:8777/Snh_VCenterPluginInfo
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
    va = VMWareInspect('10.204.216.14')
    r = get_vcenter_plugin_introspect_elements(va)
    import pprint
    pprint.pprint(r)
