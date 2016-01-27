import re
from tcutils.verification_util import *
from collections import defaultdict


def _dsResultGet(dct, p1, p2, match=None):
    ret = None
    try:
#        if p2:
#            res = dct.xpath(p1,p2)
#        else:
        res = dct.xpath(p1)
        ret1 = res
        if match:
            ret2 = []
            if isinstance(ret1, list):
                for elem in ret1:
                    if isinstance(elem, dict):
                        for k, v in elem.items():
                            if isinstance(match, tuple):
                                if ((match[0] == k)and (match[1] == v)):
                                    ret2.append(elem)
                                    break
                                elif (isinstance(v, dict)):
                                    if (match[0] in v.keys() and (match[1] in v.values()or (int(match[1]) in v.values()))):
                                        ret2.append(elem)
                                        break
                            else:
                                if(match in v):
                                    ret2.append(elem)
                                    break
                                elif (isinstance(v, dict)):
                                    if(match in v.values()or int(match) in v.values()):
                                        ret2.append(elem)
                                        break
                    else:
                        if (match == elem):
                            ret2.append(elem)
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
        print e
    finally:
        return ret


class DsServicesResult (Result):

    '''
        This class returns a generator flat results
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Service":
            typ = 'services'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _dsResultGet(self, typ, attr, match)

    @property
    def info(self):
        services = {'xmpp-server': 'control-node',
                    'OpServer': 'analytics',
                    'ApiServer': 'config'}
        service_dict = defaultdict(list)
        for service in self.xpath('services'):
            svc_type = services.get(service['service_type'], None)
            if not svc_type:
                continue
            service_dict[svc_type].append(service['info']['ip-address'])
        return service_dict

class DsClientsResult (Result):

    '''
        This class returns a vrouter flat results
    '''

    def get_attr(self, tier, attr=None, match=None):
        if tier == "Clients":
            typ = 'services'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _dsResultGet(self, typ, attr, match)


class DsStatsResult (Result):

    '''
        This class returns a BGP-ROUTER UVE object
    '''

    def get_attr(self, tier, attr, match=None):
        if tier == "Control":
            typ = 'BgpRouterState'
        # elif tier == "Agent":
        #    typ = 'VrouterAgent'
        else:
            raise Exception("Invalid Arguments - bad tier")
        return _dsResultGet(self, typ, attr, match)


class DsConfigResult (Result):

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

        return _dsResultGet(self, typ, attr, match)
