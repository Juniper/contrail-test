import cgitb
cgitb.enable(format='text')

import logging as LOG

from tcutils.verification_util import *
from vna_results import *
import re
from netaddr import *
from tcutils.util import is_v6

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class AgentInspect (VerificationUtilBase):

    def __init__(self, ip, port=8085, logger=LOG):
        port = int(port)
        super(AgentInspect, self).__init__(ip, port, XmlDrv, logger=logger)

    def get_vna_domain(self, domain='default-domain'):
        pass

    def get_vna_project(self, domain='default-domain', project='admin'):
        pass

    def get_vna_ipam(self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        pass

    def get_vna_policy(self, domain='default-domain', project='admin', policy='default-network-policy'):
        pass

    def get_vna_vn_list(self, domain='default-domain', project='admin'):
        '''
            method: get_vna_vn_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''
        vnl = self.dict_get('Snh_VnListReq?name=')
        avn = vnl.xpath('./VnListResp/vn_list/list/VnSandeshData') or \
                vnl.xpath('./vn_list/list/VnSandeshData')
        l = []
        for v in avn:
            p = {}
            for e in v:
                p[e.tag] = e.text
            l.append(p)
        return VnaVnListResult({'VNs': l})

    def get_vna_vm_list(self, domain='default-domain', project='admin'):
        '''
            method: get_vna_vm_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''
        vnl = self.dict_get('Snh_VmListReq?uuid=')
        avn = vnl.xpath('./VmListResp/vm_list/list/VmSandeshData/uuid') or \
                vnl.xpath('./vm_list/list/VmSandeshData/uuid')
        l = []
        for v in avn:
            l.append(v.text)
        # return VnaVnListResult ({'VNs': l})
        return l

    def get_vna_vn(self, domain='default-domain', project='admin',
                   vn_name='default-virtual-network'):
        '''
            method: get_vna_vn finds a vn
            returns None if not found, a dict w/ attrib. eg:
            Sample : {'name': 'default-domain:admin:vn222', 'mirror_acl_uuid': None, 'acl_uuid': None, 'vrf_name': 'default-domain:admin:vn222:vn222', 'mirror_cfg_acl_uuid': None, 'ipam_data': None, 'uuid': '43c92a36-89fa-4e3e-b89f-702cdddd33ea'}

        '''
        p = None
        vn_fq_name = ':'.join((domain, project, vn_name))
        vnl = self.dict_get('Snh_VnListReq?name=%s' %vn_fq_name)
        vns = vnl.xpath('./VnListResp/vn_list/list/VnSandeshData') or \
                vnl.xpath('./vn_list/list/VnSandeshData')
        for vn in vns:
            if vn.find('name').text in vn_fq_name:
                p = VnaVnResult()
                for e in vn:
                    p[e.tag] = e.text
        return p

    def get_vna_acl_by_vn(self,
                          fq_vn_name='default-domain:admin:default-virtual-network'):
        '''
            method: get_vna_acl_by_vn finds acl of the vn
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = None
        vn = self.get_vna_vn(*fq_vn_name.split(':'))
        if vn and vn.acl():
            dict_resp = self.dict_get('Snh_AclReq?x=' + vn.acl())
            vnl = dict_resp.xpath('./AclResp/acl_list/list/AclSandeshData') or \
                    dict_resp.xpath('./acl_list/list/AclSandeshData')
            if 1 == len(vnl):
                p = VnaACLResult()
                for e in vnl[0]:
                    if e.tag == 'entries':
                        p[e.tag] = []
                        for ae in e.xpath('./list/AclEntrySandeshData'):
                            ace = {}
                            p[e.tag].append(ace)
                            for c in ae:
                                if c.tag in ('src_port_l', 'dst_port_l', 'proto_l'):
                                    ace[c.tag] = {}
                                    # Validate data before looking for list
                                    # elements as port_list is Not Available if
                                    # protocol is ICMP
                                    cdata = c.xpath('./list/SandeshRange')
                                    if cdata == []:
                                        ace[c.tag] = 'NA'
                                    else:
                                        for pl in cdata[0]:
                                            ace[c.tag][pl.tag] = pl.text
                                elif c.tag in ('action_l', ):
                                    ace[c.tag] = map(lambda x: x.text,
                                                     c.xpath('./list/ActionStr/action'))
                                else:
                                    ace[c.tag] = c.text
                    else:
                        p[e.tag] = e.text
        return p

    def get_vna_flow_by_vn(self,
                           fq_vn_name='default-domain:admin:default-virtual-network'):
        '''
            method: get_vna_flow_by_vn finds acl of the vn
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = None
        vn = self.get_vna_vn(*fq_vn_name.split(':'))
        if vn.acl() == None:
            err_msg = "ERROR: VN under test has no policy associated in Agent - %s" % vn
            return err_msg
        if vn and vn.acl():
            vnl = self.dict_get('Snh_AclFlowReq?uuid=' + vn.acl())
            vnl = vnl.xpath('./AclFlowResp') or vnl
            if vnl:
                p = VnaFlowResult()
                for e in vnl:
                    if e.tag == 'flow_entries':
                        p[e.tag] = []
                        for ae in e.xpath('./list/FlowSandeshData'):
                            # Dump following info for debugging in case of
                            # failure
                            chk_keys = ['ace_l', 'src', 'dst', 'source_vn',
                                        'dest_vn', 'protocol', 'action_l', 'flow_uuid']
                            for i in ae.getchildren():
                                if i.tag == 'dest_vn' and i.text == '__UNKNOWN__':
                                    err_msg = "ERROR: Route import issue seen in agent, check log for failed flow"
                                    # print flow data for debugging..
                                    for k in chk_keys:
                                        if k == i.tag:
                                            self.log.info(
                                                "flow: %s, -->, %s" %
                                                (i.tag, i.text))
                                            break
                                    return err_msg
                            ace = {}
                            p[e.tag].append(ace)
                            for c in ae:
                                if c.tag in ('ace_l', ):
                                    ace[c.tag] = {}
                                    ace_id_data = c.xpath('./list/AceId')
                                    if ace_id_data == []:
                                        ace[c.tag] = []
                                    else:
                                        for pl in ace_id_data[0]:
                                            ace[c.tag][pl.tag] = pl.text
                                elif c.tag in ('action_l', ):
                                    ace[c.tag] = map(lambda x: x.text,
                                                     c.xpath('./list/ActionStr/action'))
                                else:
                                    ace[c.tag] = c.text
                    elif e.tag == 'aceid_cnt_list':
                        p[e.tag] = []
                        for ae in e.xpath('./list/AceIdFlowCnt'):
                            ace = {}
                            p[e.tag].append(ace)
                            for c in ae:
                                ace[c.tag] = c.text
                    else:
                        p[e.tag] = e.text

        return p

    def get_vna_pkt_agentstatsreq(self):
        '''returns output of http://10.204.216.15:8085/Snh_AgentStatsReq?
        {'XmppStatsResp': {'xmpp_out_msgs': '62', 'xmpp_reconnect': '4', 'xmpp_in_msgs': '20', 'more': 'true'}, 'PktTrapStatsResp': {'invalid_agent_hdr': '0', 'invalid_interface': '8', 'exceptions': '3937', 'pkt_dropped': '8', 'no_handler': '8', 'more': 'true'}, 'IpcStatsResp': {'ipc_in_msgs': '0', 'ipc_out_msgs': '0', 'more': 'true'}, 'FlowStatsResp': {'flow_aged': '44', 'flow_denied': '0', 'flow_duplicate': '0', 'flow_allowed': '48', 'flow_active': '4', 'more': 'true'}, 'SandeshStatsResp': {'sandesh_out_msgs': '0', 'sandesh_reconnects': '0', 'sandesh_http_sessions': '0', 'sandesh_in_msgs': '0', 'more': 'false'}}'''

        stat_dct = {}
        stats = self.dict_get('Snh_AgentStatsReq?')
        for elem in stats.getchildren():
            dct = {}
            k = elem.tag
            for e in elem:
                k1 = e.tag
                v1 = e.text
                d = {k1: v1}
                dct.update(d)
            d1 = {k: dct}
            stat_dct.update(d1)
        return stat_dct

    def get_vna_fetchallflowrecords(self):
        '''returns out from http://10.204.216.15:8085/Snh_FetchAllFlowRecords?
        return a list of all the flow records as below:
        [{'protocol': '1', 'stats_bytes': '222180', 'stats_packets': '2645', 'setup_time_utc': '1371254131073195', 'sip': '1.1.1.253', 'src_port': '0', 'uuid': '3a95eaa5-87e5-4b37-a49a-15a406db8356', 'nat': 'disabled', 'mirror_port': '0', 'direction': 'ingress', 'implicit_deny': 'no', 'refcount': '4', 'setup_time': '2013-Jun-14 23:55:31.073195', 'vrf': '1', 'dest_vrf': '0', 'interface_idx': '3', 'flow_handle': '54518', 'dst_port': '0', 'action': '32', 'short_flow': 'no', 'dip': '2.1.1.253', 'mirror_ip': '0.0.0.0'}, {'protocol': '1', 'stats_bytes': '222180', 'stats_packets': '2645', 'setup_time_utc': '1371254131065594', 'sip': '2.1.1.253', 'src_port': '0', 'uuid': '2ea64aa3-d716-407e-acf6-54c81027c042', 'nat': 'disabled', 'mirror_port': '0', 'direction': 'ingress', 'implicit_deny': 'no', 'refcount': '4', 'setup_time': '2013-Jun-14 23:55:31.065594', 'vrf': '2', 'dest_vrf': '0', 'interface_idx': '4', 'flow_handle': '25755', 'dst_port': '0', 'action': '32', 'short_flow': 'no', 'dip': '1.1.1.253', 'mirror_ip': '0.0.0.0'}]

l[0]={'protocol': '1', 'stats_bytes': '222180', 'stats_packets': '2645', 'setup_time_utc': '1371254131073195', 'sip': '1.1.1.253', 'src_port': '0', 'uuid': '3a95eaa5-87e5-4b37-a49a-15a406db8356', 'nat': 'disabled', 'mirror_port': '0', 'direction': 'ingress', 'implicit_deny': 'no', 'refcount': '4', 'setup_time': '2013-Jun-14 23:55:31.073195', 'vrf': '1', 'dest_vrf': '0', 'interface_idx': '3', 'flow_handle': '54518', 'dst_port': '0', 'action': '32', 'short_flow': 'no', 'dip': '2.1.1.253', 'mirror_ip': '0.0.0.0'}'''

        r = self.dict_get('Snh_FetchAllFlowRecords?')
        l = []
        xpath = './flow_list'
        records = EtreeToDict(xpath).get_all_entry(r)
        return records['flow_list']

    def get_vna_fetchflowrecord(self, nh=None, sip=None, dip=None, sport=None, dport=None, protocol=None):
        '''http://10.204.216.15:8085/Snh_FetchFlowRecord?vrf=1&sip=1.1.1.253&dip=2.1.1.253&src_port=0&dst_port=0&protocol=1
        usage:self.records=inspect_h.get_vna_fetchflowrecord(nh='1',sip='1.1.1.253',dip='2.1.1.253',sport='0',dport='0',protocol='1')

        return value:[{'nh': '1'}, {'sip': '1.1.1.253'}, {'dip': '2.1.1.253'}, {'src_port': '0'}, {'dst_port': '0'}, {'protocol': '1'}, {'dest_vrf': '0'}, {'action': '32'}, {'mirror_ip': '0.0.0.0'}, {'mirror_port': '0'}, {'direction': 'ingress'}, {'stats_bytes': '0'}, {'stats_packets': '0'}, {'uuid': 'aa010de9-5eec-48d8-884a-ccbc5de665bb'}, {'nat': 'disabled'}, {'flow_handle': '54518'}, {'interface_idx': '3'}, {'setup_time': '2013-Jun-17 11:28:08.708658'}, {'refcount': '4'}, {'implicit_deny': 'no'}, {'short_flow': 'no'}, {'setup_time_utc': '1371468488708658'}]'''
        path = 'Snh_FetchFlowRecord?nh=' + nh + '&sip=' + sip + '&dip=' + dip + \
            '&src_port=' + sport + '&dst_port=' + \
            dport + '&protocol=' + protocol
        rec = self.dict_get(path)
        if (rec.getchildren()[0].text == 'No Flow Record for specified key '):
            return None
        rec = rec.getchildren()[0].xpath('./FlowRecordsResp/SandeshFlowData') or \
                rec.getchildren()[0].xpath('./SandeshFlowData')
        if rec is None:
            return None
        record = rec[0].getchildren()
        l = []
        for v in record:
            p = {}
            p[v.tag] = v.text
            l.append(p)
        return l

    def delete_all_flows(self):
        '''Delete flows with following introspect url - http://10.204.216.15:8085/Snh_DeleteAllFlowRecords?. 
        ''' 
        resp = self.dict_get('Snh_DeleteAllFlowRecords?')
           
    def match_item_in_flowrecord(self, flow_rec, item, expected):
        '''This proc typically work in pair with get_vna_fetchflowrecord. It parse the output of get_vna_fetchflowrecord and verify for the given item output is matching with the user expected one.'''
        result = False
        for itr in flow_rec:
            if itr.keys() == [item]:
                if expected in itr.values()[0]:
                    result = True
        return result

    def _get_vna_kflowresp(self, record, show_evicted=False):
        '''return list of kernel flow records for a given record..
        a record is an element with tag KFlowInfo and has flow_list
        By default, return non-evicted flows'''
        l = []
        record = record.getchildren()[0].xpath('./list/KFlowInfo')
        for v in record:
            p = {}
            include_flow = False
            flag = v.xpath('flags')[0].text
            if ('EVICTED' in flag or 'DEAD' in flag):
                if show_evicted:
                    include_flow = True
            else:
                include_flow = True
            if include_flow:
                for e in v:
                    p[e.tag] = e.text
                l.append(p)
        # end for
        return l

    def get_vna_kflowresp(self, index=None, show_evicted=False):
        '''http://10.204.216.15:8085/Snh_KFlowReq?flow_idx=
        introspect has 3 different return values - record_list, record and []
        
        By default, will return non-evicted flows
        '''
        if not index:
            index = ''
        record_list = self.dict_get('Snh_KFlowReq?flow_idx=%s' % (index))
        l = []
        if ('KFlowResp' in record_list.getchildren()[0].tag):
            for record in record_list:
                l = l + self._get_vna_kflowresp(record, show_evicted)
            return l
        elif ('flow_list' in record_list.getchildren()[0].tag):
            if 'flow_handle' in record_list.getchildren()[1].tag:
                l += self._get_vna_kflowresp(record_list, show_evicted)
                next_index = record_list.getchildren()[1].text
                while next_index != '0':
                    (records_set, next_index) = self.get_vna_next_kflowresp(
                                                    next_index, show_evicted)
                    l.extend(records_set)
                return l
        else:
            self.log.debug("Introspect output match failure, got as follows: ")
            self.log.debug(etree.tostring(record_list, pretty_print=True))
            return None

    def get_vna_next_kflowresp(self, x='', show_evicted=False):
        ''' nodek1:8085/Snh_NextKFlowReq?x=<optional number>
        Kflow data is returned in batches
        By default, will return non-evicted flows
        '''
        l = []
        response = self.dict_get('Snh_NextKFlowReq?x=%s' % (x))
        records = response.getchildren()[0].xpath('./list/KFlowInfo')
        next_index = response.getchildren()[1].text
        for v in records:
            p = {}
            include_flow = False
            flag = v.xpath('flags')[0].text
            if ('EVICTED' in flag or 'DEAD' in flag):
                if show_evicted:
                    include_flow = True
            else:
                include_flow = True

            if include_flow:
                for e in v:
                    p[e.tag] = e.text
                l.append(p)
        return (l, next_index)
    # end get_vna_next_kflowresp        

    def get_vna_kflow_entry(self, index=None):
        ''' Requests http://nodek1:8085/Snh_KFlowReq?flow_idx=165172
        '''
        p = {}
        if not index:
            return None
        response = self.dict_get('Snh_KFlowReq?flow_idx=%s' % (index))
        try:
            record = response.getchildren()[0].xpath('./list/KFlowInfo')[0]
        except IndexError:
            # No such index exists
            return {}
        for e in record:
            p[e.tag] = e.text
        return p
    # end get_vna_kflow_entry


    def get_cs_alloc_fip_pool(self, domain='default-domain', project='admin', fip_pool='default-floating-ip-pool'):
        pass

    def policy_update(self, domain='default-domain', *arg):
        pass

    def dissassociate_ip(self, domain='default-domain', *arg):
        pass

    def get_vna_vrf_objs(self, domain='default-domain', project='admin', vn_name='default-virtual-network'):
        '''

        Returns VRF objects list from VRF name in agent using : http://172.27.58.57:8085/Snh_VrfListReq?x=default-domain:admin:net10:net10
        Sample : List of {'mcindex': '1', 'name': 'default-domain:admin:vn222:vn222', 'ucindex': '1'}
        '''
        p = None
        vrflist = self.dict_get('Snh_VrfListReq?name=%s:%s:%s:%s' % (domain,
                                                                 project, vn_name, vn_name))
        if len(vrflist.xpath('./VrfListResp')):
            vrf = vrflist.xpath('./VrfListResp')[0]
        else:
            vrf = vrflist
        avn = filter(lambda x:  ':'.join((domain, project,
                                          vn_name)) in x.xpath('./name')[0].text, vrf.xpath(
            './vrf_list/list/VrfSandeshData'))
        p = VnaVrfListResult({'vrf_list': []})
        for v in avn:
            pp = VnaVrfRouteResult()
            for e in v:
                pp[e.tag] = e.text
            p['vrf_list'].append(pp)
        return p
    # end get_vna_vrf_objs

    def get_vna_vrf_id(self, vn_fq_name):
        domain = str(vn_fq_name.split(':')[0])
        project = str(vn_fq_name.split(':')[1])
        vn = str(vn_fq_name.split(':')[2])
        vrf = '%s:%s:%s:%s' % (domain,
                                project, vn, vn)
        agent_vrf_objs = self.get_vna_vrf_objs(domain,project,vn)
        return [x['ucindex'] for x in agent_vrf_objs['vrf_list'] if x['name'] == vrf]

    def get_vna_route(self, vrf_id='', ip=None, prefix=None):
        if not ip or not is_v6(ip):
            table = 'Snh_Inet4UcRouteReq'
            plen = 32
        else:
            table = 'Snh_Inet6UcRouteReq'
            plen = 128
        table_resp = table.replace('Req', 'Resp')
        table_resp = table_resp.replace('Snh_', '')
        prefix =  plen if prefix is None else prefix
        routes = {'ip': ip, 'prefix': prefix}
        path = '%s?x=%s' % (table, str(vrf_id))
        xpath = 'route_list/list/RouteUcSandeshData'

        p = self.dict_get(path)

        routelist = EtreeToDict('./%s/%s' %(table_resp, xpath)).get_all_entry(p) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(p)
        if not ip:
            routes.update({'routes': routelist})
            return routes
        if type(routelist) is dict:
            routelist1 = [routelist]
        else:
            routelist1 = routelist
        for route in routelist1:
            if (route['src_ip'] == ip and route['src_plen'] == str(prefix)):
                routes.update({'routes': [route]})
                return routes
    # end get_vna_route
    
    def get_vna_discovered_dns_server(self):
        path = 'Snh_AgentDiscoveryDnsXmppConnectionsRequest'
        xpath = 'xmpp_inuse_connections/list/AgentXmppInUseConnections'
        p = self.dict_get(path)
        dnsList = EtreeToDict('./AgentDiscoveryDnsXmppConnectionsResponse/%s' %(xpath)).get_all_entry(p) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(p)
        if type(dnsList) is dict:
            dnsList = [dnsList]
        dnsIps = []
        for dns in dnsList:
            dnsIps.append(dns['controller_ip'])
        return dnsIps
    # end get_vna_discovered_dns_server 

    def get_vna_layer2_route(self, vrf_id='', mac=None):
        routes = {'mac': mac}
        path = 'Snh_Layer2RouteReq?x=%s' % str(vrf_id)
        xpath = 'route_list/list/RouteL2SandeshData'
        p = self.dict_get(path)
        routelist = EtreeToDict('./Layer2RouteResp/%s' %(xpath)).get_all_entry(p) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(p)
        if not mac:
            routes.update({'routes': routelist})
            return routes
        if type(routelist) is dict:
            routelist1 = [routelist]
        else:
            routelist1 = routelist
        for route in routelist1:
            if (EUI(route['mac']) == EUI(mac)):
                routes.update({'routes': [route]})
                return routes
    # end get_vna_layer2_route

    def get_vna_route_in_mclist_by_key(self, vrf_id, key, ip, prefix):
        route_list = self.get_vna_active_route(
            vrf_id, ip, prefix)['path_list'][0]['nh']['mc_list']
        for entry in route_list:
            if entry[key]:
                return entry[key]
            else:
                return None
  # end get_vna_route_in_mclist_by_key

    def get_vna_active_route(self, ip, prefix=None, vrf_id=None, vn_fq_name=None):
        '''
        Returns the first path got from get_vna_route. We would later need to have API to search a path given a set of match-conditions like  nh/label/peer etc.
        '''
        if vrf_id is None:
            assert vn_fq_name, "Either vrf_id or vn_fq_name has to be specified"
            vrf_id = self.get_vna_vrf_id(vn_fq_name)
            if not vrf_id:
                return None
            vrf_id = vrf_id[0]
        route_list = self.get_vna_route(vrf_id, ip, prefix)
        if route_list:
            return route_list['routes'][0]
        else:
            return None
    # end get_vna_active_route

    def _itf_fltr(self, x, _type, value):
        if _type == 'vmi':
            path = './uuid'
        elif _type == 'tap':
            path = './name'
        elif _type == 'vm':
            path = './vm_uuid'
        elif _type == 'ip':
            path = './ip_addr'
        elif _type == 'type':
            path = './type'
        e = x.xpath(path)
        if e:
            return value == e[0].text
        return False

    def get_vna_tap_interface_common(self, _type, value):
        '''

        Returns the tap-interface name for a VM as seen by agent
           Note:: define elsewhere
              def get_vna_tap_interface(vm_id):
                cs = VNCApiInspect (ip)
                vna = AgentInspect(ip)
                return vna.get_vna_tap_interface (cs.get_cs_vmi_of_vm(
                            vm_id)['virtual-machine-interface']['uuid'])
        '''
        ret_list = []
        p = None
        vnl = self.dict_get('Snh_PageReq?x=begin:-1,end:-1,table:db.interface.0,')
        intf_list = vnl.xpath('./ItfResp/itf_list/list/ItfSandeshData') or \
                vnl.xpath('./itf_list/list/ItfSandeshData')
        avn = filter(lambda x:  self._itf_fltr(x, _type, value), intf_list)
#        if 1 == len (avn):
        for intf in avn:
            p = VnaItfResult()
            for e in intf:  # intf replaces avn[0]
                if e.tag == 'fip_list':
                    p[e.tag] = []
                    for fip in e.xpath('./list/FloatingIpSandeshList'):
                        pp = {}
                        for ee in fip:
                            pp[ee.tag] = ee.text
                        p[e.tag].append(pp)
                else:
                    p[e.tag] = e.text
            ret_list.append(p)
        return ret_list

    def get_vna_tap_interface_by_vm(self, vm_id):
        return self.get_vna_tap_interface_common('vm', vm_id)

    def get_vna_tap_interface_by_ip(self, ip_addr):
        return self.get_vna_tap_interface_common('ip', ip_addr)

    def get_vna_interface_by_type(self, type):
        """
        Returns interface name by type specified
        Type can take 'eth'/'vhost'/'pkt'/'vport'
        """
        intf_name = []
        intf_list = self.get_vna_tap_interface_common('type', type)
        for intf in intf_list:
            if intf['type'] == type:
                intf_name.append(intf['name'])
        return intf_name

    def get_vna_tap_interface_by_vmi(self, vmi_id):
        '''

        Returns the tap-interface name for a VM as seen by agent
           Note:: define elsewhere
              def get_vna_tap_interface(vm_id):
                cs = VNCApiInspect (ip)
                vna = AgentInspect(ip)
                return vna.get_vna_tap_interface (cs.get_cs_vmi_of_vm(
                            vm_id)['virtual-machine-interface']['uuid'])
        '''
        return self.get_vna_tap_interface_common('vmi', vmi_id)
    # end get_vna_tap_interface

    def get_vna_intf_details(self, tap_intf_name):
        '''

        Returns the object got from http://172.27.58.57:8085/Snh_ItfReq?name=<tap-intf_name>
        '''
        return self.get_vna_tap_interface_common('tap', tap_intf_name)
    # end get_vna_intf_details

    def get_vna_xmpp_connection_status(self):
        '''
            method: get_vna_xmpp_connection_status returns a list
        '''
        vnl = self.dict_get('Snh_AgentXmppConnectionStatusReq?')
        elem = vnl.getchildren()[0]
        var = elem.xpath('./list/AgentXmppData')
        l = []
        for x in range(0, len(var)):
            p = {}
            p[elem.xpath('./list/AgentXmppData')[x].xpath('./controller_ip')[0]
              .tag] = elem.xpath('./list/AgentXmppData')[x].xpath('./controller_ip')[0].text
            p[elem.xpath('./list/AgentXmppData')[x].xpath('./cfg_controller')[0]
              .tag] = elem.xpath('./list/AgentXmppData')[x].xpath('./cfg_controller')[0].text
            p[elem.xpath('./list/AgentXmppData')[x].xpath('./state')[0]
              .tag] = elem.xpath('./list/AgentXmppData')[x].xpath('./state')[0].text
            l.append(p)
        return l
    # end get_vna_xmpp_connection_status

    def get_vna_diag_ping_res(self, src_ip='', src_port='', dst_ip='', dst_port='', proto='', vrf='', size='', count='', intv=''):
        '''
        method: Get the ping response from diag introspect
        '''
        ping_url = "Snh_PingReq?source_ip=%s&source_port=%s&dest_ip=%s&dest_port=%s&protocol=%s&vrf_name=%s&packet_size=%s&count=%s&interval=%s" % (
            src_ip, src_port, dst_ip, dst_port, proto, vrf, size, count, intv)
        print ping_url
        self.ping_out = self.dict_get(ping_url)
        l = {}
        i = 1
        # Get individual ping response
        ping_resp = self.ping_out.xpath('/__PingResp_list/PingResp')
        if ping_resp != []:
            for x in ping_resp:
                q = {}
                for y in x.getchildren():
                    q[y.tag] = y.text
                l[i] = q
                i = i + 1
            # Get ping response summary
            ping_sum_resp = self.ping_out.xpath(
                '/__PingResp_list/PingSummaryResp')
            m = []
            for x in ping_sum_resp[0].getchildren():
                r = {}
                r[x.tag] = x.text
                m.append(r)
            l['PingSummaryResp'] = m
        return l

    def get_vna_verify_diag_ping(self, src_ip='', src_port='', dst_ip='', dst_port='', proto='', vrf='', size='', count='', intv=''):
        '''
        method: This method verify the ping response from diag introspect
        '''
        result = True,
        req_sent = 0
        req_rcv = 0
        loss = 0
        ping_count = self.get_vna_diag_ping_res(
            src_ip=src_ip, src_port=src_port, dst_ip=dst_ip, dst_port=dst_port, proto=proto, vrf=vrf, size=size, count=10, intv=intv)
        if ping_count == {}:
            result = False
        else:
            for i in range(0, len(ping_count['PingSummaryResp']) - 1):
                if ping_count['PingSummaryResp'][i].keys()[0] == 'request_sent':
                    req_sent = int(
                        ping_count['PingSummaryResp'][i].values()[0])
                elif ping_count['PingSummaryResp'][i].keys()[0] == 'response_received':
                    req_rcv = int(ping_count['PingSummaryResp'][i].values()[0])
                elif ping_count['PingSummaryResp'][i].keys()[0] == 'pkt_loss':
                    loss = int(ping_count['PingSummaryResp'][i].values()[0])
            print "%s %s %s" % (req_sent, req_rcv, loss)
            print "%s" % (count)

            if req_sent == req_rcv:
                result = True
            else:
                result = False
        return result

    def get_sg_list(self):
        '''
            method: get_sg_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''
        l = []
        sg = self.dict_get('Snh_SgListReq?name=')
        asg = sg.xpath('./SgListResp/sg_list/list/SgSandeshData') or \
                sg.xpath('./sg_list/list/SgSandeshData')

        for s in asg:
            p = {}
            for e in s:
                p[e.tag] = e.text
            l.append(p)
        return l

    def get_sg(self, sg_uuid):
        '''
            method: get_sg get sg sg_uuid from agent 
            returns None if not found, a dict w/ attrib. eg:

        '''
	query = 'Snh_SgListReq?sg_uuid=' + str(sg_uuid)
	l = []
        sg = self.dict_get(query)
        asg = sg.xpath('./SgListResp/sg_list/list/SgSandeshData') or \
                sg.xpath('./sg_list/list/SgSandeshData')

        for s in asg:
            p = {}
            for e in s:
                p[e.tag] = e.text
            l.append(p)
        return l

    def get_sg_acls_list(self, sg_uuid):
        '''
            method: get_sg_acls_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''

	sg_info = self.get_sg(sg_uuid)
	acl_id_list = [sg_info[0]['ingress_acl_uuid'], sg_info[0]['egress_acl_uuid']]

        l = []
	for acl_id in acl_id_list:
	    query = 'Snh_AclReq?uuid=' + str(acl_id)
            acl = self.dict_get(query)
            aacl = acl.xpath('./AclResp/acl_list/list/AclSandeshData') or \
                    acl.xpath('./acl_list/list/AclSandeshData')
            for a in aacl:
                p = {}
                for e in a:
                    if e.tag == 'entries':
                        entry = e.xpath('./list/AclEntrySandeshData')
                        enl = []
                        for rule in entry:
                            en = {}
                            for x in rule:
                                en[x.tag] = x.text
                            enl.append(en)
                        p[e.tag] = enl
                    else:
                        p[e.tag] = e.text
                l.append(p)
        return l

    def get_acls_list(self):
        '''
            method: get_acls_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''
        l = []
        acl = self.dict_get('Snh_AclReq?name=')
        aacl = acl.xpath('./AclResp/acl_list/list/AclSandeshData') or \
                acl.xpath('./acl_list/list/AclSandeshData')
        for a in aacl:
            p = {}
            for e in a:
                if e.tag == 'entries':
                    entry = e.xpath('./list/AclEntrySandeshData')
                    enl = []
                    for rule in entry:
                        en = {}
                        for x in rule:
                            en[x.tag] = x.text
                        enl.append(en)
                    p[e.tag] = enl
                else:
                    p[e.tag] = e.text
            l.append(p)
        return l

    def get_generator_name(self):
        ''' Returns string of format nodek1:Compute:contrail-vrouter-agent:0
        '''
        xml_data = self.dict_get('Snh_SandeshUVECacheReq?x=ModuleClientState')
        name = xml_data.getchildren()[0].xpath('./data/ModuleClientState/name')[0].text
        return name
    # end get_generator_name

if __name__ == '__main__':

    vvnagnt = AgentInspect('10.204.217.12')
    print vvnagnt.get_vna_vn('default-domain', 'admin', 'vn-1')
    print vvnagnt.get_vna_vn_list('default-domain', 'demo')
    print vvnagnt.get_vna_vrf_id('default-domain', 'demo', 'fe:fe')
    print vvnagnt.get_vna_route(3, '172.168.10.254', 32)
    print vvnagnt.get_vna_tap_interface_by_vmi('73caeeed-7cac-4ef4-8268-f16c1ba514a4')
    print vvnagnt.get_vna_tap_interface_by_vm('ae57b6d0-f057-4ccc-95eb-e3932a265752')
    print vvnagnt.get_vna_intf_details('tap8e3d0097-7b')
    print vvnagnt.get_vna_acl_by_vn('default-domain:demfeo:fe')
    print vvnagnt.get_vna_flow_by_vn('default-domain:demo:pub')
    print vvnagnt.get_vna_tap_interface_by_vm('aec7cc6e-977a-4e2d-8650-e583c5f63241')
