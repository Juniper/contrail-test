import re
from tcutils.verification_util import *
import logging

log = logging.getLogger('log01')


def _OpResult_get_list_name(lst):
    sname = ""
    for sattr in lst.keys():
        if sattr[0] not in ['@']:
            sname = sattr
    return sname


def _OpResultFlatten(inp):
    sname = ""
    if (inp['@type'] == 'struct'):
        sname = _OpResult_get_list_name(inp)
        if (sname == ""):
            return Exception('Struct Parse Error')
        ret = {}
        ret[sname] = {}
        for k, v in inp[sname].items():
            ret[sname][k] = _OpResultFlatten(v)
        return ret
    elif (inp['@type'] == 'list'):
        sname = _OpResult_get_list_name(inp['list'])
        ret = {}
        if (sname == ""):
            return ret
        items = inp['list'][sname]
        if not isinstance(items, list):
            items = [items]
        lst = []
        for elem in items:
            if not isinstance(elem, dict):
                lst.append(elem)
            else:
                lst_elem = {}
                for k, v in elem.items():
                    lst_elem[k] = _OpResultFlatten(v)
                lst.append(lst_elem)
        ret[sname] = lst
        return ret
    else:
        return inp['#text']


def _OpResultListParse(dct, match):
    ret = []
    sname = _OpResult_get_list_name(dct)
    if (sname == ""):
        return ret

    if not isinstance(dct[sname], list):
        lst = [dct[sname]]
    else:
        lst = dct[sname]

    for elem in lst:
        if (match == None):
            isMatch = True
        else:
            isMatch = False

        if sname == 'element':
            if elem == match:
                isMatch = True
            if isMatch:
                ret.append(elem)
        else:
            dret = {}
            isMatcher = True
            for k, v in elem.items():
                if v.has_key('#text'):
                    dret[k] = v["#text"]
                    if v.has_key('@aggtype'):
                        if v['@aggtype'] == 'listkey':
                            if v['#text'] == match:
                                isMatch = True
                    if isinstance(match, list):
                        for matcher in match:
                            if not isinstance(matcher, tuple):
                                raise Exception('Incorrect matcher')
                            mk, mv = matcher
                            if (k == mk):
                                if (v['#text'] != mv):
                                    isMatcher = False
                else:
                    dret[k] = _OpResultFlatten(v)

            if isinstance(match, list):
                if isMatcher:
                    ret.append(dret)
            else:
                if isMatch:
                    ret.append(dret)
    return ret

# def _OpResultGet(dct, p1, p2, match = None):
#    ret = None
#    try:
#        res = dct.xpath(p1,p2)
#
# import pdb; pdb.set_trace()
#        if isinstance(res, list):
#            if len(res) != 1:
#                raise Exception('Inconsistency')
#            res = res[0][0]
#
#        if res['@type'] in ["list"]:
#            ret = _OpResultListParse(res['list'], match)
#        elif res['@type'] in ["struct"]:
#            sname = _OpResult_get_list_name(res)
#            ret = _OpResultFlatten(res)
# ret = res[sname]
#        else:
#            if (match != None):
#                raise Exception('Match is invalid for non-list')
# ret = res['#text']
#    except Exception as e:
#        print e
#    finally:
#        return ret


def _OpResultGet(dct, p1, p2, match=None):
    ret = None
    try:
        if p2:
            res = dct.xpath(p1, p2)
        else:
            res = dct.xpath(p1)
        ret1 = res
        if match:
            ret2 = []
            if isinstance(ret1, list):
                for elem in ret1:
                    if isinstance(elem, dict):
                        try:
                            for k, v in elem.items():
                                if isinstance(match, tuple):
                                    if ((match[0] == k)and (match[1] == v)):
                                        ret2.append(elem)
                                        ret = ret2
                                        return 
                                    elif (isinstance(v, dict)):
                                        if (match[0] in v.keys() and (match[1] in v.values()or (int(match[1]) in v.values()))):
                                            ret2.append(elem)
                                            ret = ret2
                                    	    return 	
                                    elif (isinstance(v,list)):
                                        for vl in v:
                                            if ((match[0] in vl.keys()) and (match[1] in vl.values())):
                                                ret2.append(vl)
                                                ret = ret2
                                                return

                                    elif (isinstance(v, unicode)):
                                        continue
                                else:
                                    if(match in v):
                                        ret2.append(elem)
                                        ret = ret2
                                        return
                                    elif (isinstance(v, dict)):
                                        if(match in v.values()or int(match) in v.values()):
                                            ret2.append(elem)
                                            ret = ret2
                                            return
                        except Exception as e:
                            pass
                    else:
                        if (match == elem):
                            ret2.append(elem)
                            ret = ret2
                            return
            else:
                for k, v in ret1.items():
                    if isinstance(match, tuple):
                        if (match[0] == k and match[1] == v):
                            ret2.append(ret1)
                    else:
                        if(match == v):
                            ret2.append(ret1)
            ret = ret2
        else:
            ret = ret1

    except Exception as e:
        log.debug(e)
    finally:
        return ret


class OpGeneratorResult (Result):

    '''
        This class returns a generator flat results
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Client":
            typ = 'ModuleClientState'
        elif tier == "Server":
            typ = 'ModuleServerState'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _OpResultGet(self, typ, attr, match)


class OpVRouterResult (Result):

    '''
        This class returns a vrouter flat results
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Stats":
            typ = 'VrouterStatsAgent'
        elif tier == "Agent":
            typ = 'VrouterAgent'
        elif tier == "Node":
            typ = 'NodeStatus'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _OpResultGet(self, typ, attr, match)


class OpBGPRouterResult (Result):

    '''
        This class returns a BGP-ROUTER UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Control":
            typ = 'BgpRouterState'
        elif tier == "Node":
            typ = 'NodeStatus'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _OpResultGet(self, typ, attr, match)


class OpVNResult (Result):

    '''
        This class returns a VN UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        #import pdb; pdb.set_trace ()
        if tier == "Config":
            typ = 'UveVirtualNetworkConfig'
        elif tier == "Agent":
            typ = 'UveVirtualNetworkAgent'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpVMResult (Result):

    '''
        This class returns a VM UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        #import pdb; pdb.set_trace ()
        if tier == "Config":
            typ = 'UveVirtualMachineConfig'
        elif tier == "Agent":
            typ = 'UveVirtualMachineAgent'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpHrefResult(Result):

    '''Get all hrefs for a uve type
    '''

    def get_attr(self, tier, attr=None, match=None):

        if tier == "Href":
            typ = 'href'
        elif tier == "Name":
            typ = 'name'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)

class OpHrefTableResult(Result):

    '''Get all hrefs for a uve type
    '''

    def get_attr(self, tier, attr=None, match=None):

        if tier == "Href":
            typ = 'href'
        elif tier == "Name":
            typ = 'name'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)

class OpBGPPeerResult (Result):

    '''
        This class returns a bgp-peer UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Control":
            typ = 'BgpPeerInfoData'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpBGPXmppPeerResult (Result):

    '''
        This class returns a bgp_xmpp_peer UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Control":
            typ = 'XmppPeerInfoData'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpSIResult (Result):

    '''
        This class returns a service instance UVE object
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Config":
            typ = 'UveSvcInstanceConfig'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpSTResult (Result):

    '''
        This class returns a service template UVE object
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Config":
            typ = 'UveServiceChainData'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpCollectorResult (Result):

    '''
        This class returns a collector UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        #import pdb; pdb.set_trace ()
        if tier == "Node":
            typ = 'NodeStatus'
        elif tier == "Collector":
            typ = 'CollectorState'
        elif tier == "Module":
            typ = 'ModuleCpuState'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


class OpConfigResult (Result):

    '''
        This class returns a config node UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        #import pdb; pdb.set_trace ()
        if tier == "Node":
            typ = 'NodeStatus'
#        elif tier == "Collector":
#            typ = 'CollectorState'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)

class OpServiceChainResult (Result):

    '''
        This class returns a service chain node UVE object
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Config":
            typ = 'value'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)

class OpDbResult(Result):

    '''
        This class returns a database node UVE object
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Node":
            typ = 'NodeStatus'
        elif tier == 'DatabasePurge':    
            typ = 'DatabasePurgeInfo'
        elif tier == 'DatabaseUsage':    
            typ = 'DatabaseUsageInfo'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)

class OpVmIntfResult(Result):

    '''
        This class returns a database node UVE object
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Agent":
            typ = 'UveVMInterfaceAgent'
        else:
            raise Exception("Invalid Arguments - bad tier")

        return _OpResultGet(self, typ, attr, match)


if __name__ == '__main__':
    ret = [{u'process_name': u'contrail-topology', u'start_count': 2, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': u'1459335478187353', u'core_file_list': [], u'last_start_time': u'1459335485479907', u'stop_count': 1, u'last_exit_time': None, u'exit_count': 0}, {u'process_name': u'contrail-snmp-collector', u'start_count': 5, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': u'1459335460085416', u'core_file_list': [], u'last_start_time': u'1459354997793674', u'stop_count': 1, u'last_exit_time': u'1459354992338304', u'exit_count': 3}, {u'process_name': u'contrail-query-engine', u'start_count': 2, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': None, u'core_file_list': [u'/var/crashes/core.contrail-query-.28570.nodea18.1459354650'], u'last_start_time': u'1459354657348157', u'stop_count': 0, u'last_exit_time': u'1459354651334948', u'exit_count': 1}, {u'process_name': u'contrail-analytics-nodemgr', u'start_count': 1, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': u'1459335448983065', u'core_file_list': [], u'last_start_time': u'1459335448985432', u'stop_count': 1, u'last_exit_time': None, u'exit_count': 0}, {u'process_name': u'contrail-analytics-api', u'start_count': 2, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': None, u'core_file_list': [u'/var/crashes/core.contrail-analyt.28571.nodea18.1459354619'], u'last_start_time': u'1459354626974772', u'stop_count': 0, u'last_exit_time': u'1459354620439921', u'exit_count': 1}, {u'process_name': u'contrail-collector', u'start_count': 3, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': u'1459336769593271', u'core_file_list': [u'/var/crashes/core.contrail-collec.20835.nodea18.1459354660'], u'last_start_time': u'1459354669133185', u'stop_count': 1, u'last_exit_time': u'1459354663017154', u'exit_count': 1}, {u'process_name': u'contrail-alarm-gen', u'start_count': 1, u'process_state': u'PROCESS_STATE_RUNNING', u'last_stop_time': None, u'core_file_list': [], u'last_start_time': u'1459335436000000', u'stop_count': 0, u'last_exit_time': None, u'exit_count': 0}]

    abc = _OpResultGet(ret,'NodeStatus','process_info',match = ('process_name', 'contrail-analytics-api'))
