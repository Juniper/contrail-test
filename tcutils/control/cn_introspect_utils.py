import logging as LOG
from lxml import etree
import re
from tcutils.verification_util import *
from tcutils.util import is_v6, get_random_name
from netaddr import IPNetwork, AddrFormatError
from tcutils.test_lib.contrail_utils import get_ri_name

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class ControlNodeInspect (VerificationUtilBase):

    def __init__(self, ip, port=8083, logger=LOG):
        super(ControlNodeInspect, self).__init__(ip, port, XmlDrv,
                                                 logger=logger)

    def _join(self, *args):
        """Joins the args with ':'"""
        return ':'.join(args)

    def _get_if_map_table_entry(self, match):
        d = None
        #Changes to paging will require fetching particular element rather than entire data
        table_name = re.match('(\S+?):', match)
        new_table_req = 'Snh_IFMapTableShowReq?table_name=' + table_name.group(1) + '&search_string=' + match
        p = self.dict_get(new_table_req)
        xp = p.xpath('./IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo')
        if not xp:
            # sometime ./xpath dosen't work; work around
            # should debug to find the root cause.
            xp = p.xpath('/IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo')
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
                                # Remove CDATA; if present
                                text = eod.text.replace(
                                    "<![CDATA[<", "<").strip("]]>")
                                nxml = etree.fromstring(text)
                                for iqc in nxml:
                                    if iqc.tag == 'virtual-DNS-data':
                                        d[e.tag][eod.tag][iqc.tag] = {}
                                        for dns in iqc:
                                            d[e.tag][eod.tag][iqc.tag][
                                                dns.tag] = dns.text
                                    if iqc.tag == 'virtual-DNS-record-data':
                                        d[e.tag][eod.tag][iqc.tag] = {}
                                        for dns in iqc:
                                            d[e.tag][eod.tag][iqc.tag][
                                                dns.tag] = dns.text
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

    def get_if_map_peer_server_info(self, match=None):
        d = None
        try:
            p = self.dict_get('Snh_IFMapPeerServerInfoReq?')
            xpath = './IFMapPeerServerInfoResp/%s' % (match)
            d = EtreeToDict(xpath).get_all_entry(p)
        except Exception as e:
            print e
        finally:
            return d

    def get_cn_domain(self, domain='default-domain'):
        pass

    def get_cn_project(self, domain='default-domain', project='admin'):
        pass

    def get_cn_vdns(self, vdns, domain='default-domain'):
        m = 'virtual-DNS:' + domain + ':' + vdns
        return self._get_if_map_table_entry(m)

    def get_cn_vdns_rec(self, vdns, rec_name, domain='default-domain'):
        m = 'virtual-DNS-record:' + domain + ':' + vdns + ':' + rec_name
        return self._get_if_map_table_entry(m)

    def get_cn_config_ipam(self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        m = 'network-ipam:' + domain + ':' + project + ':' + ipam
        return self._get_if_map_table_entry(m)

    def get_cn_config_policy(self, domain='default-domain', project='admin', policy='default-network-policy'):
        policy_name = 'network-policy:' + domain + ':' + project + ':' + policy
        path = 'Snh_IFMapTableShowReq?table_name=network-policy&search_string=%s' % (policy_name)
        xpath = './IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo'
        p = self.dict_get(path)
        ifmaps = EtreeToDict(xpath).get_all_entry(p)

        if type(ifmaps) is dict and ifmaps.has_key('node_name') and ifmaps['node_name'] == policy_name:
            return ifmaps

        if type(ifmaps) is list:
            for ifmap in ifmaps:
                if ifmap['node_name'] == policy_name:
                    return ifmap

    def get_cn_config_vn(self, domain='default-domain', project='admin', vn_name='default-virtual-network'):
        m = 'virtual-network:' + domain + ':' + project + ':' + vn_name
        return self._get_if_map_table_entry(m)

    def get_cn_config_fip_pool(self, domain='default-domain', project='admin', vn_name='default-virtual-network', fip_pool_name='default-floating-ip-pool'):
        m = 'floating-ip-pool:' + domain + ':' + \
            project + ':' + vn_name + ':' + fip_pool_name
        return self._get_if_map_table_entry(m)

    def get_cn_routing_instance(self, ri_name):
        '''Returns a routing instance dictionary.
        '''
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_name
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_routing_instance_list(self):
        '''Returns a list of routing instance dictionaries.
        '''
        path = 'Snh_ShowRoutingInstanceReq'
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_route_table(self, ri_name):
        '''Returns a routing table dictionary of a specifc routing instance,
        includes both the unicast and multicast table.
        '''
        path = 'Snh_ShowRouteReq?name=%s' % ri_name
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_rtarget_group(self, route_target):
        '''Returns the dictionary of the rtarget_group.
        '''
        path = 'Snh_ShowRtGroupReq?x=%s'%route_target
        xpath = '/ShowRtGroupResp/rtgroup_list/list/ShowRtGroupInfo'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_rtarget_table(self):
        '''Returns the dictionary of the bgp.rtarget.0 table.
        '''
        path = 'Snh_ShowRouteReq?x=bgp.rtarget.0'
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        return rt['routes']

    def get_cn_vpn_table(self, prefix):
        result= True
        path = 'Snh_ShowRouteReq?x=bgp.l3vpn-inet6.0' if is_v6(prefix) \
               else 'Snh_ShowRouteReq?x=bgp.l3vpn.0'
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        for route in rt['routes']:
            if prefix in route['prefix']:
                result= True
                break
            else:
                result= False
        return result

    def get_cn_route_table_entry(self, prefix, ri_name, table=None):
        '''Returns the route dictionary for requested prefix and routing instance.
        '''
        try:
            prefix = str(IPNetwork(prefix).network) + '/' + \
                     str(IPNetwork(prefix).prefixlen)
        except AddrFormatError:
            pass
        if not table:
            table = 'inet6.0' if is_v6(prefix) else 'inet.0'
        path = 'Snh_ShowRouteReq?x=%s.%s' % (ri_name, table)
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        if type(rt) == type(dict()):
            for route in rt['routes']:
                if route['prefix'] == prefix:
                    return route['paths']
        else:
            for entry in rt:
                for route in entry['routes']:
                    if route['prefix'] == prefix:
                        return route['paths']

    def get_cn_bgp_neigh_entry(self, encoding='All'):
        '''Returns the route dictionary for requested prefix and routing instance.
        '''
        path = 'Snh_BgpNeighborReq?domain=&ip_address='
        xpath = '/BgpNeighborListResp/neighbors/list/BgpNeighborResp'
        p = self.dict_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        if encoding is 'All':
            return rt
        else:
            parshed_rt = []
            for entry in rt:
                if entry['encoding'] == encoding:
                    parshed_rt.append(entry)
            return parshed_rt

    def policy_update(self, domain='default-domain', *arg):
        pass

    def dissassociate_ip(self, domain='default-domain', *arg):
        pass

    def get_cn_sec_grp(self, domain='default-domain', project='admin', secgrp='default'):
        sec_name = 'security-group:' + domain + ':' + project + ':' + secgrp
        path = 'Snh_IFMapTableShowReq?table_name=security_group&search_string=%s' % (sec_name)
        xpath = './IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo'
        p = self.dict_get(path)
        ifmaps = EtreeToDict(xpath).get_all_entry(p)

        if type(ifmaps) is dict and ifmaps.has_key('node_name') and ifmaps['node_name'] == sec_name:
            return ifmaps

        if type(ifmaps) is list:
            for ifmap in ifmaps:
                if ifmap['node_name'] == sec_name:
                    return ifmap

    def get_cn_sec_grp_acls(self, domain='default-domain', project='admin', secgrp='default'):
        sec_name = 'access-control-list:' + domain + ':' + project + ':' + secgrp
        egress = sec_name + ':' + 'egress-access-control-list'
        ingress = sec_name + ':' + 'ingress-access-control-list'
        path = 'Snh_IFMapTableShowReq?table_name=access-control-list&search_string=%s' % (sec_name)
        xpath = './IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo'
        acls_dict = {}
        p = self.dict_get(path)
        ifmaps = EtreeToDict(xpath).get_all_entry(p)
        if type(ifmaps) is dict or (type(ifmaps) is list and len(ifmaps) != 2):
            return False

        for ifmap in ifmaps:
            if ifmap['node_name'] == egress:
                acls_dict['egress-access-control-list'] = ifmap
            if ifmap['node_name'] == ingress:
                acls_dict['ingress-access-control-list'] = ifmap

        return acls_dict

    def get_cn_ri_membership(self, ri_name=None, vn_fq_name=None ):
        '''
        Return the peers (includes both bgp and xmpp peers) who are
        interested in this RI (across all families inet/evpn etc.)
        Data is got from Snh_ShowRoutingInstanceReq itself

        Returns a list of hostnames
        '''
        ri_fq_name = None
        if vn_fq_name:
            ri_fq_name = get_ri_name(vn_fq_name)
        if ri_name:
            ri_fq_name = ri_name
        if not ri_fq_name:
            self.logger.debug('get_cn_ri_membership needs RI or vn name')
            return None

        path = 'Snh_ShowRoutingInstanceReq?name=%s' % ri_fq_name
        ri_resp = self.dict_get(path)
        if ri_resp is not None:
            self.logger.debug('No RI detail found for %s' % (ri_fq_name))
            return
        xpath = ('./instances/list/ShowRoutingInstance/tables/list/'
        'ShowRoutingInstanceTable/membership/ShowTableMembershipInfo/peers')
        peers_info = EtreeToDict(xpath).get_all_entry(ri_resp)
        all_peers = set()
        for info in peers_info:
            for x in info.get('peers') or []:
                all_peers.add(x['peer'])
        return list(all_peers)
    # end get_cn_ri_membership

if __name__ == '__main__':
    cn = ControlNodeInspect('10.204.216.58')
    import pdb; pdb.set_trace()
    v = cn.get_cn_ri_membership('default-domain:admin:net1:net1')
    import pdb; pdb.set_trace()
    cn = ControlNodeInspect('10.84.14.9')
    print "ipam", cn.get_cn_config_ipam()
    print "policy", cn.get_cn_config_policy()
    print "vn", cn.get_cn_config_vn()
    print "vn", cn.get_cn_config_vn(vn_name=get_random_name("fvnn100"))
    print "fip_pool", cn.get_cn_config_fip_pool()
