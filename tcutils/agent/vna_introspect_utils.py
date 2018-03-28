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

    def __init__(self, ip, port=8085, logger=LOG, inputs=None):
        port = int(port)
        super(AgentInspect, self).__init__(ip, port, XmlDrv, logger=logger,
            args=inputs)

    def get_vna_domain(self, domain='default-domain'):
        pass

    def get_vna_project(self, domain='default-domain', project='admin'):
        pass

    def get_vna_ipam(self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        pass

    def get_vna_policy(self, domain='default-domain', project='admin', policy='default-network-policy'):
        pass

    def get_vna_vrf_list(self, domain='default-domain', project='admin'):
        '''
            method: get_vna_vrf_list returns a list
            returns None if not found, a dict w/ attrib. eg:

        '''
        vrfl = self.dict_get('Snh_VrfListReq?name=')
        avrf = vrfl.xpath('./VrfListResp/vrf_list/list/VrfSandeshData') or \
            vrfl.xpath('./vrf_list/list/VrfSandeshData')
        l = []
        for v in avrf:
            p = {}
            for e in v:
                p[e.tag] = e.text
            l.append(p)
        return VnaVrfListResult({'VRFs': l})

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
        if not vnl:
            return None
        avn = vnl.xpath('./VmListResp/vm_list/list/VmSandeshData/uuid') or \
                vnl.xpath('./vm_list/list/VmSandeshData/uuid')
        l = []
        for v in avn:
            l.append(v.text)
        # return VnaVnListResult ({'VNs': l})
        return l

    def get_vna_vm(self, uuid):
        '''
            returns None if not found, a dict w/ attrib.

        '''
        vml = self.dict_get('Snh_VmListReq?uuid=%s' % (uuid))
        avm = vml.xpath('./VmListResp/vm_list/list/VmSandeshData')
        if not avm:
            return None
        l = elem2dict(avm[0])
        return l
    # end get_vna_vm

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
        if not vnl:
            return None
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

    def get_vna_vrf_by_id(self, vrf_id):
        '''
        Query the vrf using vrf id instead of vrf fqname
        Uses ucindex as a key (ucindex, mcindex, l2index, uc6index are all same
        Returns dict of vrf entry as seen in Snh_VrfListReq query

        If not found, returns empty dict
        '''
        vrf_dict = {}
        vrf_list = self.dict_get('Snh_VrfListReq?name=').xpath('./VrfListResp')[0]
        for entry in vrf_list.xpath('./vrf_list/list/VrfSandeshData'):
            got_vrf_id = entry.xpath('./ucindex')[0].text
            if got_vrf_id == vrf_id:
                vrf_dict = elem2dict(entry)
        return vrf_dict
    # end get_vna_vrf_by_id

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
        vrf_id = [x['ucindex'] for x in agent_vrf_objs['vrf_list'] if x['name'] == vrf]
        if len(vrf_id):
            return vrf_id[0]
        else:
            return None

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

    def get_vna_dns_server(self):
        path = 'Snh_DnsInfo?'
        xpath = 'DnsStats/dns_resolver'
        p = self.dict_get(path)
        dnsList = EtreeToDict('./__DnsStats_list/%s' %(xpath)).get_all_entry(p) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(p)
        dnsIps = dnsList['dns_resolver']
        return dnsIps
    # end get_vna_dns_server

    def get_vna_dns_query_to_named(self):
        path = 'Snh_SandeshTraceRequest?x=DnsBind'
        xpath = 'traces'
        p = self.dict_get(path)
        dnsQuery = EtreeToDict('./SandeshTraceTextResponse/%s' %(xpath)).get_all_entry(p) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(p)
        return dnsQuery
    # end get_vna_dns_query_to_named

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

    def get_vna_mcast_route(self, vrf_id='', grp_ip=None, src_ip=None):
        '''
        Get Multicast route table details
        '''
        routes = {'grp_ip': grp_ip, 'src_ip': src_ip}
        path = 'Snh_Inet4McRouteReq?vrf_id=%s&stale=&src_ip=%s&grp_ip=%s' % (str(vrf_id), str(src_ip), str(grp_ip))
        xpath = 'route_list/list/RouteMcSandeshData'
        ptmp = self.dict_get(path)
        routelist = EtreeToDict('./Inet4McRouteResp/%s' %(xpath)).get_all_entry(ptmp) or \
            EtreeToDict('./%s' % (xpath)).get_all_entry(ptmp)
        return routelist


    # end get_vna_mcast_route


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

    def get_vna_tap_interface_common(self, _type, value, filter_dict=None):
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
        filter_str = ''
        filter_dict = filter_dict or {}
        for k,v in filter_dict.iteritems():
            filter_str = filter_str + '%s:%s' %(k,v)
        p = None
        vnl = self.dict_get('Snh_PageReq?x=begin:-1,end:-1,table:db.interface.0'
            ',%s' %(filter_str))
        intf_list = vnl.xpath('./ItfResp/itf_list/list/ItfSandeshData') or \
                vnl.xpath('./itf_list/list/ItfSandeshData')
        if _type:
            avn = filter(lambda x:  self._itf_fltr(x, _type, value), intf_list)
        else:
            avn = intf_list
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
                if e.tag == 'bridge_domain_list':
                    p[e.tag] = []
                    for bd in e.xpath('./list/VmIntfBridgeDomainUuid'):
                        pp = {}
                        for ee in bd:
                            pp[ee.tag] = ee.text
                        p[e.tag].append(pp)
                else:
                    p[e.tag] = e.text
            ret_list.append(p)
        return ret_list

    def get_vna_tap_interface_by_vm(self, vm_id):
        return self.get_vna_tap_interface_common('vm', vm_id)

    def get_vna_tap_interface_by_ip(self, ip_addr):
        if is_v4(ip_addr):
            key = 'ipv4_address'
        elif is_v6(ip_addr):
            key = 'ipv6_address'
        filter_dict = {key: ip_addr}
        return self.get_vna_tap_interface_common('ip', ip_addr,
                                                 filter_dict=filter_dict)

    def get_vna_interface_by_type(self, _type):
        """
        Returns interface name by type specified
        Type can take 'eth'/'vhost'/'pkt'/'vport'
        """
        intf_name = []
        filter_dict = {'type': _type}
        intf_list = self.get_vna_tap_interface_common('type', _type,
                                                      filter_dict=filter_dict)
        intf_name = [x['name'] for x in intf_list]
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
        return self.get_vna_tap_interface_common('vmi', vmi_id,
                                                 filter_dict={'uuid':vmi_id})
    # end get_vna_tap_interface

    def get_vna_intf_details(self, tap_intf_name):
        '''

        Returns the object got from http://172.27.58.57:8085/Snh_ItfReq?name=<tap-intf_name>
        '''
        return self.get_vna_tap_interface_common('tap', tap_intf_name)
    # end get_vna_intf_details

    def get_vna_tap_interface(self, filter_dict=None):
        return self.get_vna_tap_interface_common(None, None, filter_dict)

    def get_vna_xmpp_connection_status(self):
        '''
            method: get_vna_xmpp_connection_status returns a list
        '''
        vnl = self.dict_get('Snh_AgentXmppConnectionStatusReq?')
        elem = vnl.getchildren()[0]
        var = elem.xpath('./list/AgentXmppData')
        l = []
        for x in var:
            p = elem2dict(x)
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

    def get_agent_physical_interface(self):
        ''' Get it from http://nodek2:8085/Snh_SandeshUVECacheReq?x=VrouterAgent
        '''
        xml_obj = self.dict_get('Snh_SandeshUVECacheReq?x=VrouterAgent')
        return xml_obj.xpath('./UveVrouterAgent/data/VrouterAgent/phy_if/list/'
                             'AgentInterface/name')[0].text
    # end get_agent_physical_interface

    def get_agent_vm_interface_drop_stats(self, fq_name):
        ''' Get it from http://nodek2:8085/Snh_SandeshUVECacheReq?x=UveVMInterfaceAgent
        '''
        xml_obj = self.dict_get('Snh_SandeshUVECacheReq?x=UveVMInterfaceAgent')
        xml_data = xml_obj.xpath('./UveVMInterfaceAgentTrace/data/UveVMInterfaceAgent')
        l = []
        for index, x_data in enumerate(xml_data):
            fq_name_inspect = x_data.xpath('./name')[0].text
            if fq_name == fq_name_inspect:
                x_path = './UveVMInterfaceAgentTrace/data/UveVMInterfaceAgent/raw_drop_stats/AgentDropStats'
                raw_drop_stats_obj = xml_obj.xpath(x_path)
                raw_drop_stats_obj = raw_drop_stats_obj[index]
                dct = elem2dict(raw_drop_stats_obj)
                l.append(dct)
        return l[0]
    # end get_agent_vm_interface_drop_stats

    def get_agent_vrouter_drop_stats(self):
        ''' Get it from http://nodek2:8085/Snh_SandeshUVECacheReq?x=VrouterStatsAgent
        '''
        xml_obj = self.dict_get('Snh_SandeshUVECacheReq?x=VrouterStatsAgent')
        xml_data = xml_obj.xpath('./VrouterStats/data/VrouterStatsAgent')[0]
        raw_drop_stats = xml_data.xpath('./raw_drop_stats')[0]
        agent_raw_drop_stats_obj = raw_drop_stats.xpath('./AgentDropStats')[0]
        return elem2dict(agent_raw_drop_stats_obj)
    # end  get_agent_vrouter_drop_stats

    def get_agent_qos_queue(self, uuid):
        ''' Get it from http://nodei16:8085/Snh_QosQueueSandeshReq?uuid=
                        16dc48cb-0c63-4cc4-bfc5-d9f4b7c3f84c&name=&id=
            Sample : {'uuid': '954bcfda-c38f-41b6-a50b-1c42e400d95e',
                      'id': '1',
                      'name': default-global-system-config:default-global-qos-config:ctest-qos_queue-08282381}
        '''
        xml_obj = self.dict_get('Snh_QosQueueSandeshReq?uuid=%s&name=&id=' % (uuid))
        xpath_str = './QosQueueSandeshResp/qos_queue_list/list/QosQueueSandeshData'
        xml_obj = xml_obj.xpath(xpath_str)

        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch qos queue details in agent for '
                ' uuid %s, Got :%s' % (uuid, xml_obj))
            return None
        return elem2dict(xml_obj[0])
    # end get_agent_qos_queue

    def get_agent_qos_queue_from_id(self, id):
        ''' Get it from http://nodei16:8085/Snh_QosQueueSandeshReq?uuid=&name=&id=1
        '''
        xml_obj = self.dict_get('Snh_QosQueueSandeshReq?uuid=&name=&id=%d' % (id))
        xpath_str = './QosQueueSandeshResp/qos_queue_list/list/QosQueueSandeshData'
        xml_obj = xml_obj.xpath(xpath_str)

        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch qos queue details in agent for '
                ' id %s, Got :%s' % (id, xml_obj))
            return None
        return elem2dict(xml_obj[0])
    # end get_agent_qos_queue_from_id

    def get_agent_forwarding_class(self, uuid):
        '''   Get it from nodek2:8085/Snh_ForwardingClassSandeshReq?uuid=&name=&id=1
            Sample : {'mpls_exp': '1',
                      'vlan_priority': '5',
                      'uuid': '954bcfda-c38f-41b6-a50b-1c42e400d95e',
                      'dscp': '10',
                      'qos_queue': '0',
                      'id': '1',
                      'name': None}
        '''
        xml_obj = self.dict_get('Snh_ForwardingClassSandeshReq?uuid=%s&name=&id=' % (uuid))
        xpath_str = './ForwardingClassSandeshResp/fc_list/list/ForwardingClassSandeshData'
        xml_obj = xml_obj.xpath(xpath_str)

        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch fc details in agent for '
                ' uuid %s, Got :%s' % (uuid, xml_obj))
            return None

        p = {}
        for e in xml_obj[0]:
            p[e.tag] = e.text
        return p
    # end get_agent_forwarding_class

    def get_vrouter_forwarding_class(self, id):
        ''' http://nodek2:8085/Snh_KForwardingClassReq?index=0

            Returns
                {'mpls_exp': '0', 'qos_queue': '0', 'vlan_priority': '0', 'id': '0', 'dscp': '0'}
            or None if id is not found
        '''
        xml_obj = self.dict_get('Snh_KForwardingClassReq?index=%s' % (id))
        xml_obj = xml_obj.xpath('./forwarding_class_list/list/KForwardingClass')
        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch fc details in vrouter for '
                ' id %s, Got :%s' % (id, xml_obj))
            return None
        p = {}
        for e in xml_obj[0]:
            p[e.tag] = e.text
        return p
    # end get_vrouter_forwarding_class

    def get_agent_qos_config(self, uuid):
        ''' Get it from
            http://nodek2:8085/Snh_AgentQosConfigSandeshReq?uuid=4eedad9a-a954-4553-ae8b-9cd95a09b66b&name=&id=
            Sample return dict:
                {'dscp_list': [{'forwarding_class_id': '1', 'qos_value': '0'}],
                 'id': '1',
                 'name': 'default-global-system-config:default-global-qos-config:fab-qc1',
                 'type': 'fabric',
                 'uuid': '4eedad9a-a954-4553-ae8b-9cd95a09b66b',
                 'vlan_priority_list': []}
        '''
        xml_obj = self.dict_get('Snh_AgentQosConfigSandeshReq?uuid=%s&name=&id=' % (uuid))
        xpath_str = './AgentQosConfigSandeshResp/qc_list/list/AgentQosConfigSandeshData'
        xml_obj = xml_obj.xpath(xpath_str)
        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch Qos config details in agent for '
                ' uuid %s, Got :%s' % (uuid, xml_obj))
            return None

        p = {}
        for e in xml_obj[0]:
            if e.tag == 'dscp_list' or e.tag == 'vlan_priority_list' or \
                    e.tag == 'mpls_exp_list' :
                cp_list = e.xpath('./list/QosForwardingClassSandeshPair')
                cps = []
                for cp in cp_list:
                    qv = cp.xpath('./qos_value')[0].text
                    fc = cp.xpath('./forwarding_class_id')[0].text
                    cps.append({'qos_value':  qv, 'forwarding_class_id' : fc})
                p[e.tag] = cps
            else:
                p[e.tag] = e.text
        return p
    # end get_agent_qos_config

    def get_vrouter_qos_config(self, id):
        ''' Get it from
            http://nodek2:8085/Snh_KQosConfigReq?index=0
            Sample return dict:
              {'dscp_map': [{'fc_id': '1', 'qos': '0'},
                            {'fc_id': '0', 'qos': '1'},
                            {'fc_id': '0', 'qos': '2'},
                            {'fc_id': '0', 'qos': '3'},.....64 Code points
                 'id': '0',
                 'mpls_exp_map': [{'fc_id': '0', 'qos': '0'},
                                  {'fc_id': '0', 'qos': '1'},
                                  {'fc_id': '0', 'qos': '2'},
                                  {'fc_id': '0', 'qos': '3'},
                                  {'fc_id': '0', 'qos': '4'},
                                  {'fc_id': '0', 'qos': '5'},
                                  {'fc_id': '0', 'qos': '6'},
                                  {'fc_id': '0', 'qos': '7'}],
                 'vlan_priority_map': [{'fc_id': '0', 'qos': '0'},
                                       {'fc_id': '0', 'qos': '1'},
                                       {'fc_id': '0', 'qos': '2'},
                                       {'fc_id': '0', 'qos': '3'},
                                       {'fc_id': '0', 'qos': '4'},
                                       {'fc_id': '0', 'qos': '5'},
                                       {'fc_id': '0', 'qos': '6'},
                                       {'fc_id': '0', 'qos': '7'}]}

        '''
        xml_obj = self.dict_get('Snh_KQosConfigReq?index=%s' % (id))
        xpath_str = './qos_config_list/list/KQosConfig'
        xml_obj = xml_obj.xpath(xpath_str)
        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch Qos config details in vrouter for '
                ' id %s, Got :%s' % (id, xml_obj))
            return None

        p = {}
        for e in xml_obj[0]:
            if e.tag == 'dscp_map' or e.tag == 'vlan_priority_map' or \
                    e.tag == 'mpls_exp_map' :
                cp_list = e.xpath('./list/kQosIdFowardingClassPair')
                cps = []
                for cp in cp_list:
                    qv = cp.xpath('./qos')[0].text
                    fc = cp.xpath('./fc_id')[0].text
                    cps.append({'qos':  qv, 'fc_id' : fc})
                p[e.tag] = cps
            else:
                p[e.tag] = e.text
        return p
    # end get_vrouter_qos_config

    def get_vrouter_virtual_interface(self, index):
        ''' http://nodek1:8085/Snh_KInterfaceReq?if_id=3
        '''
        xml_obj = self.dict_get('Snh_KInterfaceReq?if_id=%s' % (index))
        xpath_str = './if_list/list/KInterfaceInfo'
        xml_obj = xml_obj.xpath(xpath_str)
        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch intf details in vrouter for '
                ' index %s, Got :%s' % (index, xml_obj))
            return None
        p = {}
        for e in xml_obj[0]:
            p[e.tag] = e.text
        return p
    # end get_vrouter_virtual_interface

    def get_vrouter_nh(self, index):
        ''' http://nodek1:8085/Snh_KNHReq?x=41
        '''
        xml_obj = self.dict_get('Snh_KNHReq?x=%s' % (index))
        xpath_str = './nh_list/list/KNHInfo'
        xml_obj = xml_obj.xpath(xpath_str)
        if not xml_obj or len(xml_obj) != 1:
            self.log.debug('Unable to fetch nh details in vrouter for '
                ' index %s, Got :%s' % (index, xml_obj))
            return None
        return elem2dict(xml_obj[0])
    # end get_vrouter_nh

    def get_vrouter_route_table(self, vrf_id, get_nh_details=False, **kwargs):
        # TODO
        # Once bug 1614824 is fixed , add filter options
        # since this table can be very big
        '''
            Queries http://nodek1:8085/Snh_KRouteReq?vrf_id=4
            get_nh_details: If True, Include nh details also in the route dict
                            It is False by default
            Sample :
            v.get_vrouter_route_table('4', prefix='30.1.1.0', get_nh_details=True))
            returns:
            [{'family': 'AF_INET',
              'label': '18',
              'label_flags': 'MPLS ',
              'nh': {'encap': '0cc47a320a860cc47a320a8c0800',
                     'encap_family': 'INVALID',
                     'encap_len': '14',
                     'encap_oif_id': '0',
                     'family': 'AF_INET',
                     'flags': 'VALID | TUNNEL_MPLS_UDP ',
                     'id': '41',
                     'ref_cnt': '138',
                     'rid': '0',
                     'tun_dip': '10.204.216.222',
                     'tun_sip': '10.204.216.221',
                     'type': 'TUNNEL',
                     'vrf': '0'},
              'nh_id': '41',
              'prefix': '30.1.1.0',
              'prefix_len': '32',
              'rid': '0',
              'vrf_id': '4'},
             {'family': 'AF_INET',
              'label': '18',
              'label_flags': 'MPLS ',
              'nh': {'encap': '0cc47a320a860cc47a320a8c0800',
                     'encap_family': 'INVALID',
                     'encap_len': '14',
                     'encap_oif_id': '0',
                     'family': 'AF_INET',
                     'flags': 'VALID | TUNNEL_MPLS_UDP ',
                     'id': '41',
                     'ref_cnt': '138',
                     'rid': '0',
                     'tun_dip': '10.204.216.222',
                     'tun_sip': '10.204.216.221',
                     'type': 'TUNNEL',
                     'vrf': '0'},
              'nh_id': '41',
              'prefix': '30.1.1.0',
              'prefix_len': '32',
              'rid': '0',
              'vrf_id': '4'}]
        '''
        filter_dict = dict((k,v) for k,v in  kwargs.iteritems() if v is not None)
        filter_set = set(filter_dict.items())
        xml_obj = self.dict_get('Snh_KRouteReq?x=%s' % (vrf_id))
        xpath_str = './KRouteResp'
        xml_obj = xml_obj.xpath(xpath_str)
        if not xml_obj:
            self.log.debug('Unable to fetch route details in vrouter for '
                ' vrf index %s, Got :%s' % (vrf_id, xml_obj))
            return []
        routes = []
        for obj in xml_obj:
            xpath_str = './rt_list/list/KRouteInfo'
            routes_elem = obj.xpath(xpath_str)
            for route in routes_elem:
                p = elem2dict(route)

                # Remove any unhashable values in p
                p = dict((k,v) for k,v in p.iteritems() if v)

                if filter_set.issubset(set(p.items())):
                    if get_nh_details:
                        p['nh'] = self.get_vrouter_nh(p['nh_id'])
                    routes.append(p)
        return routes
    # end get_vrouter_route_table

    def get_nh_for_route_in_vrouter(self, prefix, route_table=[], **kwargs):
        '''
        Return nh details as dict for a route in vrouter

        Sample:
        {'encap': '0cc47a320a860cc47a320a8c0800',
         'encap_family': 'INVALID',
         'encap_len': '14',
         'encap_oif_id': '0',
         'family': 'AF_INET',
         'flags': 'VALID | TUNNEL_MPLS_UDP ',
         'id': '41',
         'ref_cnt': '138',
         'rid': '0',
         'tun_dip': '10.204.216.222',
         'tun_sip': '10.204.216.221',
         'type': 'TUNNEL',
         'vrf': '0'}
        '''

        nh = None
        (prefix_ip, prefix_len) = prefix.split('/')
        if not route_table:
            vrf_id = kwargs.get('vrf_id')
            route_table = self.get_vrouter_route_table(vrf_id, prefix=prefix_ip,
                                               prefix_len=prefix_len,
                                               get_nh_details=True)

        for route in route_table:
            if route['prefix'] == prefix_ip and \
                route['prefix_len'] == prefix_len:
                    nh = route.get('nh') or route.get('nh_id')
        return nh
    # end get_nh_for_route_in_vrouter

    def get_bgpaas(self, uuid):
        # 1734647 needs to be addressed
        bgpaas_obj = self.dict_get(
            'Snh_BgpAsAServiceSandeshReq?uuid=%s' % uuid)
        if bgpaas_obj is None:
            return None
        return VnaBGPaaSResult(bgpaas_obj)

    def get_health_check(self, uuid):
        hc_obj = self.dict_get('Snh_HealthCheckSandeshReq?uuid=%s'%uuid)
        if hc_obj is None:
           return None
        return VnaHealthCheckResult(hc_obj)

    def get_bd(self, bd_uuid):
        '''
            method: get_bd get bd bd_uuid from agent
            returns None if not found, a dict w/ attrib. eg:

            Example:
            query: http://nodec12.englab.juniper.net:8085/Snh_BridgeDomainSandeshReq?uuid=4978b5df-deac-4108-930d-76a000be302b

            sample format of bd_dict:
            {'uuid': '8d6a8fec-91ed-447c-aec3-70caa1af2e1c',
             'vn': 'f456a09d-3c9b-4c0f-8b4c-4056f4d0adfe',
             'isid': '200200',
             'vrf': 'default-domain:ctest-TestPbbEvpnMacLearning-03474827:vn2:vn2:8d6a8fec-91ed-447c-aec3-70caa1af2e1c',
             'pbb_etree_enabled': 'False',
             'learning_enabled': 'True',
             'name': 'default-domain:ctest-TestPbbEvpnMacLearning-03474827:vn2:ctest-bd_ctest-TestPbbEvpnMacLearning-03474827-45482677'}
        '''
        query = 'Snh_BridgeDomainSandeshReq?uuid=' + str(bd_uuid)
        l = []

        bd = self.dict_get(query)
        abd = bd.xpath('./BridgeDomainSandeshResp/bd_list/list/BridgeDomainSandeshData') or \
                bd.xpath('./bd_list/list/BridgeDomainSandeshData')

        for bd in abd:
            bd_dict = elem2dict(bd)
            l.append(bd_dict)
        return l

    def _kitf_fltr(self, x, _type, value):
        if _type == 'name':
            path = './name'
        elif _type == 'ip':
            path = './ip'
        e = x.xpath(path)
        if e:
            return value == e[0].text
        return False

    def get_vrouter_interface_list(self, _type, value):
        '''
            Returns the interface list matching _type and value
        '''
        ret_list = []
        rsp_list = self.dict_get('Snh_KInterfaceReq?if_id=')
        for rsp in rsp_list:
            intf_list = rsp.xpath('./KInterfaceResp/if_list/list/KInterfaceInfo') or \
                    rsp.xpath('./if_list/list/KInterfaceInfo')
            avn = filter(lambda x:  self._kitf_fltr(x, _type, value), intf_list)

            for intf in avn:
                intf_dict = elem2dict(intf)
                ret_list.append(intf_dict)
        return ret_list

    def get_vrouter_interfaces_by_name(self, itf_name):
        return self.get_vrouter_interface_list('name', itf_name)

    def get_nh_list(self, nh_type=None):
        '''
            Returns the NH list of the given type
            If nh_type is None, returns list of all NH
        '''
        ret_list = []
        rsp = self.dict_get('Snh_NhListReq?type=%s' % (nh_type))
        nh_list = rsp.xpath('./NhListResp/nh_list/list/NhSandeshData') or \
                rsp.xpath('./nh_list/list/NhSandeshData')

        for nh in nh_list:
            nh_dict = elem2dict(nh)
            ret_list.append(nh_dict)

        return ret_list

    def get_nh_ids(self, nh_type=None):
        '''
            Returns NH ids of the given type.
            If nh_type is None, returns all NH ids
        '''
        nh_list = self.get_nh_list(nh_type=nh_type)
        nh_ids = []
        for nh in nh_list:
            if (nh_type is not None) and (nh['type'] == nh_type):
                nh_ids.append(nh['nh_index'])
            elif nh_type is None:
                nh_ids.append(nh['nh_index'])

        return nh_ids

if __name__ == '__main__':
    v = AgentInspect('10.204.217.198')
    import pdb; pdb.set_trace()
    v.get_vna_tap_interface_by_vm('3ce99e5b-2690-11e7-91c4-525400010001')
    v.get_vna_vm('710df53c-25f8-11e7-91c4-525400010001')
    x = v.get_vrouter_route_table('4')

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
