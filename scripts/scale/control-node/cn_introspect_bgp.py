# generic
import json
import requests
import re
import os
import sys
import subprocess
import time
import datetime

# contrail

import urllib2
from lxml import etree
import xmltodict
from commands import Command
from tcutils.verification_util import *


class ControlNodeInspect (VerificationUtilBase):

    def __init__(self, ip):
        super(ControlNodeInspect, self).__init__(ip, 8083, XmlDrv)

    def _join(self, *args):
        """Joins the args with ':'"""
        return ':'.join(args)

    def http_get(self, path):
        response = None
        while True:
            response = self.dict_get(path)
            if response != None:
                break
            print "Retry http get for %s after a second" % (path)
            time.sleep(1)
        return response

    def _get_if_map_table_entry(self, match):
        d = None
        #Changes to paging will require fetching particular element rather than entire data
        table_name = re.match('(\S+?):', match)
        new_table_req = 'Snh_IFMapTableShowReq?table_name=' + table_name.group(1) + '&search_string=' + match
        p = self.dict_get(new_table_req)
        xp = p.xpath('./IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo')
        f = filter(lambda x: x.xpath('./node_name')[0].text == match, xp)
        if 1 == len(f):
            d = {}
            for e in f[0]:
                if e.tag != 'obj_info':
                    d[e.tag] = e.text
                else:
                    od = e.xpath('./list/IFMapObjectShowInfo')
                    if od:
                        d[e.tag] = {}
                        for eod in od[0]:
                            if eod.tag != 'data':
                                d[e.tag][eod.tag] = eod.text
                            else:
                                d[e.tag][eod.tag] = {}
                                text = eod.text.replace(
                                    "<![CDATA[<", "<").strip("]]>")
                                nxml = etree.fromstring(text)
                                for iqc in nxml:
                                    if iqc.tag == 'id-perms':
                                        d[e.tag][eod.tag][iqc.tag] = {}
                                        for idpc in iqc:
                                            if idpc.tag == 'permissions':
                                                d[e.tag][eod.tag][iqc.tag][
                                                    idpc.tag] = {}
                                                for prm in idpc:
                                                    d[e.tag][eod.tag][iqc.tag][
                                                        idpc.tag][prm.tag] = prm.text
                                            elif idpc.tag == 'uuid':
                                                d[e.tag][eod.tag][iqc.tag][
                                                    idpc.tag] = {}
                                                for prm in idpc:
                                                    d[e.tag][eod.tag][iqc.tag][
                                                        idpc.tag][prm.tag] = prm.text
                                            else:
                                                d[e.tag][eod.tag][iqc.tag][
                                                    idpc.tag] = idpc.text

        return d

    def get_cn_domain(self, domain='default-domain'):
        pass

    def get_cn_project(self, domain='default-domain', project='admin'):
        pass

    def get_cn_config_ipam(self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        m = 'network-ipam:' + domain + ':' + project + ':' + ipam
        return self._get_if_map_table_entry(m)

    def get_cn_config_policy(self, domain='default-domain', project='admin', policy='default-network-policy'):
        m = 'network-policy:' + domain + ':' + project + ':' + policy
        return self._get_if_map_table_entry(m)

    def get_cn_config_vn(self, domain='default-domain', project='admin', vn_name='default-virtual-network'):
        m = 'virtual-network:' + domain + ':' + project + ':' + vn_name
        return self._get_if_map_table_entry(m)

    def get_cn_config_fip_pool(self, domain='default-domain', project='admin', vn_name='default-virtual-network', fip_pool_name='default-floating-ip-pool'):
        m = 'floating-ip-pool:' + domain + ':' + \
            project + ':' + vn_name + ':' + fip_pool_name
        return self._get_if_map_table_entry(m)

    def get_cn_routing_instance_bgp_active_paths(self, ri_name='', family=':'):
        '''Returns total number of bgp active paths for a particular family (inet.0 or inetmcast.0 at this time)
           Requires instance name. If no family is provided, the fist vlaue, inet.0, is returned.
           Call: num_paths = get_cn_routing_instance_bgp_active_paths(ri_name, family)
        '''

        # Return error if no routing-instance name supplied
        if not ri_name:
            return "ERROR:missing instance-name in call:get_cn_routing_instance_bgp_active_paths"

        # The "path" string is used to retrieve http data. It is appended to the http string
        # which is already setup as something like: "http://<control-node
        # ip>:8083"
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_name

        # Get all table names associated with this instance
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance/tables/list/ShowRoutingInstanceTable/name'
        tbl = self.http_get(path)

        # This could happen if the cn goes away (crashes or restarts)
        # print "type of tbl: %s" %(type(tbl))
        if tbl is None:
            return 0

        table_list = EtreeToDict(xpath).get_all_entry(tbl)

        # Check the instance route tables (one per family, e.g., inet.0, inetmcast.0, etc)
        # to see if there is a match with the "family" passed in as a parameter to this call
        # Note that the default matches most any table name
        found = False
        for index in range(len(table_list)):
            if re.search(family, table_list[index]['name'], re.IGNORECASE):
                found = True
                break

        # Return active path count for "family", otherwise "None" if the family
        # passed in was not present
        if found:
            xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance/tables/list/ShowRoutingInstanceTable/active_paths'
            p = self.http_get(path)
            return int(EtreeToDict(xpath).get_all_entry(p)[index]['active_paths'])
        else:
            return None

    # end get_routing_instance_bgp_active_paths

    def get_cn_routing_instance_peer_count(self, ri_name):
        '''Returns a routing instance dictionary.
        '''
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_name
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.http_get(path)

        # This could happen if the cn goes away (crashes or restarts)
        if p is None:
            return 0

        table_list = EtreeToDict(xpath).get_all_entry(p)

        # Get the table sub-element length as long as the  table_list is not
        # empty (and element is not None)
        if table_list and (table_list['tables'][0]['peers'] != None):
            num_peers = len(table_list['tables'][0]['peers'])
        else:
            num_peers = 0

        return num_peers

    def get_cn_routing_instance(self, ri_name):
        '''Returns a routing instance dictionary.
        '''
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_name
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.http_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_routing_instance_list(self):
        '''Returns a list of routing instance dictionaries.
        '''
        path = 'Snh_ShowRoutingInstanceReq'
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.http_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    # end get_cn_routing_instance_list

    def get_cn_route_table(self, ri_name):
        '''Returns a routing table dictionary of a specifc routing instance,
        includes both the unicast and multicast table.
        '''
        path = 'Snh_ShowRouteReq?name=%s' % ri_name
        xpath = '/ShowRouteResp/tables/listShowRouteTable'
        p = self.http_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    # end get_cn_route_table

    def get_cn_route_table_entry(self, prefix, ri_name):
        '''Returns the route dictionary for requested prefix and routing instance.
        '''
        path = 'Snh_ShowRouteReq?name=%s' % ri_name
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.http_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        for entry in rt:
            for route in entry['routes']:
                if route['prefix'] == prefix:
                    return route['paths']
    # end get_cn_route_table_entry

    def get_cn_bgp_nighbor_state(self, ip_address, encoding=''):
        '''Returns a list of BPG peers for the control node
           format example: http://10.84.7.28:8083/Snh_BgpNeighborReq?domain=&ip_address=10.84.7.250
        '''
        path = 'Snh_BgpNeighborReq?domain=&ip_address=%s' % ip_address
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'

        # print EtreeToDict(xpath).get_all_entry(self.http_get(path))

        # Get peer info
        tbl = self.http_get(path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)

        # Check if the peer with the propper encoding is found, if so return
        # the state
        return_val = 'PeerNotFound'
        for index in range(len(table_list)):
            if re.search(ip_address, table_list[index]['peer_address'], re.IGNORECASE):
                return_val = table_list[index]['state']
                if encoding:
                    if re.search(encoding, table_list[index]['encoding'], re.IGNORECASE):
                        break
                    else:
                        return_val = "PeerFound_ButWrongEncoding_found_%s" % table_list[
                            index]['encoding']

        return return_val

    # end get_cn_bgp_nighbor_state

    def get_element_from_dict(self, val, val_name, list_or_dict, secondary_val_name=''):
        '''Search for key in either a list of dictionaries or one dictionary.
           Return associated element value from the dictionary tree.
        '''
        return_val = 'KeyNotFound'
        element2 = 'ElementNotFound'

        # Treat as one dictionary
        if type(list_or_dict) is dict:
            if list_or_dict[val_name] == val:
                if secondary_val_name:
                    element2 = list_or_dict[secondary_val_name]
                return_val = True

        # Treat as list of dictionaries
        elif type(list_or_dict) is list:
            for element in list_or_dict:
                if element[val_name] == val:
                    if secondary_val_name:
                        element2 = element[secondary_val_name]
                    return_val = True
                    break

        return (return_val, element2)

    # end get_element_from_dict

    def get_cn_bgp_neighbor_element(self, ip_address, element):
        '''Get an element for a particular bgp peer
           format example: http://10.84.7.28:8083/Snh_BgpNeighborReq?domain=&ip_address=10.84.7.250
        '''
        path = 'Snh_BgpNeighborReq?domain=&ip_address=%s' % ip_address
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'

        # print EtreeToDict(xpath).get_all_entry(self.http_get(path))

        tbl = self.http_get(path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)

        # Search/get element
        # Note: table_list may be a list of dictionaries, or one dictionary
        status, element_val = self.get_element_from_dict(
            ip_address, 'peer_address', table_list, element)

        # if not status and re.search('KeyNotFound', status, re.IGNORECASE):
        if status == 'KeyNotFound':
            status = 'PeerNotFound'

        return (status, element_val)

    # end get_cn_bgp_neighbor_element

    def get_cn_bgp_neighbor_stats_element(self, element, encoding='', state='', domain=''):
        '''Get the count of bgp neighbor state status
           format example, all default values: http://10.84.7.28:8083/Snh_ShowNeighborStatisticsReq?bgp_or_xmpp=&up_or_down=&domain=
           format example: http://10.84.7.28:8083/Snh_ShowNeighborStatisticsReq?bgp_or_xmpp=xmpp&up_or_down=up&domain=default-domain%3Ademo%3Ainstance1%3Ainstance1
        '''
        path = 'Snh_ShowNeighborStatisticsReq?bgp_or_xmpp=%s&up_or_down=%s&omain=%s' % (
            encoding, state, domain)
        xpath = '/ShowNeighborStatisticsResp'

        # print EtreeToDict(xpath).get_all_entry(self.http_get(path))
        http_get = None
        while True:
            http_get = self.http_get(path)
            if http_get != None:
                break
            print "Retry http get for %s after a second" % (path)
            time.sleep(1)

        # Get element
        element_val = None
        element_val = EtreeToDict(xpath).get_all_entry(http_get)[element]

        return element_val

    def get_cn_routing_instance_table_element(self, ri_name, family, element):
        '''Returns a routing instance dictionary.
        '''
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_name
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance/tables/list/ShowRoutingInstanceTable'
        #xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance/tables/list/ShowRoutingInstanceTable/active_paths'

        tbl = self.http_get(path)
        table_list = EtreeToDict(xpath).get_all_entry(tbl)
        # print EtreeToDict(xpath).get_all_entry(self.http_get(path))

        # Search/get element
        # Note: table_list may be a list of dictionaries, or one dictionary
        status, element_val = self.get_element_from_dict(
            "%s.%s" % (ri_name, family), 'name', table_list, element)

        if element_val.isdigit():
            element_val = int(element_val)

        return (status, element_val)

    # end get_cn_routing_instance_table_element

    def policy_update(self, domain='default-domain', *arg):
        pass

    def dissassociate_ip(self, domain='default-domain', *arg):
        pass
