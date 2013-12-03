import urllib2
import xmltodict
import json
import requests
from lxml import etree

class JsonDrv (object):
    def _http_con (self, url):
        return urllib2.urlopen (url)

    def load (self, url):
        return json.load (self._http_con (url))

class XmlDrv (object):
    def load (self, url):
        resp=requests.get(url)
        return etree.fromstring(resp.text)


class EtreeToDict(object):
    def __init__(self, xpath):
        self.xpath = xpath

    def _handle_list(self, elems):
        a_list = []
        for elem in elems.getchildren():
            rval = self._get_one(elem, a_list)
            if 'element' in rval.keys():
                a_list.append(rval['element'])
            elif 'list' in rval.keys():
                a_list.append(rval['list'])
            else:
                a_list.append(rval)

        if not a_list:
            return None
        return a_list

    def _get_one(self, xp, a_list=None):
        val = {}

        child = xp.getchildren()
        if not child:
            val.update({xp.tag: xp.text})
            return val

        for elem in child:
            if elem.tag == 'list':
                val.update({xp.tag: self._handle_list(elem)})
            else:
                rval = self._get_one(elem, a_list)
                if elem.tag in rval.keys():
                    val.update({elem.tag: rval[elem.tag]})
                else:
                    val.update({elem.tag: rval})
        return val

    def get_all_entry(self, path):
        xps = path.xpath(self.xpath)

        if type(xps) is not list:
            return self._get_one(xps)

        val = []
        for xp in xps:
            val.append(self._get_one(xp))
        if len(val) == 1:
            return val[0]
        return val

    def find_entry(self, path, match):
        xp = path.xpath(self.xpath)
        f = filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return f


class VerificationUtilBase (object):
    def __init__ (self, ip, port, drv=JsonDrv):
        self._ip   = ip
        self._port = port
        self._drv  = drv ()

    def _mk_url_str (self, path):
        if path.startswith ('http:'):
            return path
        return "http://%s:%d/%s" % (self._ip, self._port, path)

    def dict_get (self, path=''):
        return self._drv.load (self._mk_url_str (path))

class VerificationApiSrv (VerificationUtilBase):
    def __init__ (self, ip):
        super (VerificationApiSrv, self).__init__ (ip, 8082)
        self._cache = {
            'domain': {},
            'project': {},
            'ipam': {},
            'policy': {},
            'vn': {},
            'fip_alloc_pool': {},
            'fip_use_pool': {},
        }

    def update_cache (self, otype, fq_path, d):
        self._cache[otype]['::'.join (fq_path)] = d

    def try_cache (self, otype, fq_path, refresh):
        p = None
        try:
            if not refresh:
                p = self._cache[otype]['::'.join (fq_path)]
        except KeyError:
            pass
        return p

    def get_cs_domain (self, domain='default-domain', refresh=False):
        '''
            method: get_cs_domain find a domain by domin name
            returns None if not found, a dict w/ domain attrib. eg:
            {u'domain': {u'fq_name': [u'ted-domain'],
                 u'id_perms': {u'created': None,
                                u'enable': True,
                                u'last_modified': None,
                                u'permissions': {u'group': u'cloud-admin-group',
                                                 u'group_access': 7,
                                                 u'other_access': 7,
                                                 u'owner': u'cloud-admin',
                                                 u'owner_access': 7},
                                u'uuid': {u'uuid_lslong': 13068984139654137108L,
                                          u'uuid_mslong': 9504116366942620127L}},
                 u'namespaces': [{u'attr': {},
                                   u'href': u'http://10.84.7.3:8082/namespace/c0552b1f-588e-4507-8962-b1837c8f883a',
                                   u'to': [u'ted-domain', u'default-namespace'],
                                   u'uuid': u'c0552b1f-588e-4507-8962-b1837c8f883a'}],
                 u'projects': [{u'attr': {},
                                 u'href': u'http://10.84.7.3:8082/project/0d779509-7d54-4842-9b34-f85557898b67',
                                 u'to': [u'ted-domain', u'ted-eng'],
                                 u'uuid': u'0d779509-7d54-4842-9b34-f85557898b67'},
                                {u'attr': {},
                                 u'href': u'http://10.84.7.3:8082/project/1fcf3244-d4d9-407d-8637-54bb2522020e',
                                 u'to': [u'ted-domain', u'default-project'],
                                 u'uuid': u'1fcf3244-d4d9-407d-8637-54bb2522020e'}],
                 u'_type': u'domain',
                 u'href': u'http://10.84.7.3:8082/domain/83e5677b-1397-49df-b55e-5bd5234c8514',
                 u'name': u'ted-domain',
                 u'uuid': u'83e5677b-1397-49df-b55e-5bd5234c8514'}}

        '''
        d = self.try_cache ('domain', [domain], refresh)
        if d:
            return d
        # cache miss
        doms = self.dict_get ('domains')
        mydom = filter (lambda x: x['fq_name'][-1] == domain, doms['domains'])
        if mydom:
            d = self.dict_get (mydom[-1]['href'])
        # cache set
        if d:
            self.update_cache ('domain', [domain], d)
        return d

    def get_cs_project (self, domain='default-domain', project='admin',
            refresh=False):
        '''
            method: get_cs_project find a project by domin & project name
            returns None if not found, a dict w/ project attrib. eg:
            {u'project': {u'fq_name': [u'ted-domain', u'ted-eng'],
                          u'id_perms': {u'created': None,
                              u'enable': True,
                              u'last_modified': None,
                              u'permissions': {u'group': u'cloud-admin-group',
                                               u'group_access': 7,
                                               u'other_access': 7,
                                               u'owner': u'cloud-admin',
                                               u'owner_access': 7},
                              u'uuid': {u'uuid_lslong': 11183836820092324711L,
                                        u'uuid_mslong': 970408112711551042}},
                          u'network_ipams': [{u'attr': {},
                                               u'href': u'http://10.84.7.3:8082/network-ipam/52310151-ec68-4052-9114-14ae1a47f2fb',
                                               u'to': [u'ted-domain',
                                                       u'ted-eng',
                                                       u'default-network-ipam'],
                                               u'uuid': u'52310151-ec68-4052-9114-14ae1a47f2fb'}],
                          u'network_policys': [{u'attr': {},
                                                 u'href': u'http://10.84.7.3:8082/network-policy/c30461ae-e72a-44a6-845b-7510c7ae3897',
                                                 u'to': [u'ted-domain',
                                                         u'ted-eng',
                                                         u'default-network-policy'],
                                                 u'uuid': u'c30461ae-e72a-44a6-845b-7510c7ae3897'}],
                          u'security_groups': [{u'attr': {},
                                                 u'href': u'http://10.84.7.3:8082/security-group/32dc02af-1b3c-4baa-a6eb-3c97cbdd2941',
                                                 u'to': [u'ted-domain',
                                                         u'ted-eng',
                                                         u'default-security-group'],
                                                 u'uuid': u'32dc02af-1b3c-4baa-a6eb-3c97cbdd2941'}],
                          u'service_templates': [{u'attr': {},
                                                   u'href': u'http://10.84.7.3:8082/service-template/4264dd1e-d312-4e03-a60e-35b40da39e95',
                                                   u'to': [u'ted-domain',
                                                           u'ted-eng',
                                                           u'default-service-template'],
                                                   u'uuid': u'4264dd1e-d312-4e03-a60e-35b40da39e95'}],
                          u'_type': u'project',
                          u'virtual_networks': [{u'attr': {},
                                                  u'href': u'http://10.84.7.3:8082/virtual-network/6a5c5c29-cfe6-4fea-9768-b0dea3b217bc',
                                                  u'to': [u'ted-domain',
                                                          u'ted-eng',
                                                          u'ted-back'],
                                                  u'uuid': u'6a5c5c29-cfe6-4fea-9768-b0dea3b217bc'},
                                                 {u'attr': {},
                                                  u'href': u'http://10.84.7.3:8082/virtual-network/926c8dcc-0b8b-444f-9f59-9ab67a8f9f48',
                                                  u'to': [u'ted-domain',
                                                          u'ted-eng',
                                                          u'ted-front'],
                                                  u'uuid': u'926c8dcc-0b8b-444f-9f59-9ab67a8f9f48'},
                                                 {u'attr': {},
                                                  u'href': u'http://10.84.7.3:8082/virtual-network/b312647f-0921-4ddf-9d59-0667a887989f',
                                                  u'to': [u'ted-domain',
                                                          u'ted-eng',
                                                          u'default-virtual-network'],
                                                  u'uuid': u'b312647f-0921-4ddf-9d59-0667a887989f'}],
                          u'href': u'http://10.84.7.3:8082/project/0d779509-7d54-4842-9b34-f85557898b67',
                          u'name': u'ted-eng',
                          u'parent_name': u'ted-domain',
                          u'uuid': u'0d779509-7d54-4842-9b34-f85557898b67'}}
        '''
        p = self.try_cache ('project', [domain, project], refresh)
        if p:
            return p
        # cache miss
        dom = self.get_cs_domain (domain)
        if dom:
            myproj = filter (lambda x: x['to'] == [domain, project], 
                    dom['domain']['projects'])
            if 1 == len(myproj):
                p = self.dict_get (myproj[0]['href'])
        if p:
            self.update_cache ('project', [domain, project], p)
        return p

    def get_cs_ipam (self, domain='default-domain', project='admin',
            ipam='default-network-ipam', refresh=False):
        '''
            method: get_cs_ipam find an ipam
            returns None if not found, a dict w/ attrib. eg:
    {u'network-ipam': {u'fq_name': [u'ted-domain',
                                     u'ted-eng',
                                     u'default-network-ipam'],
                       u'id_perms': {u'created': None,
                                      u'enable': True,
                                      u'last_modified': None,
                                      u'permissions': {u'group': u'cloud-admin-group',
                                                       u'group_access': 7,
                                                       u'other_access': 7,
                                                       u'owner': u'cloud-admin',
                                                       u'owner_access': 7},
                                      u'uuid': {u'uuid_lslong': 10454003373031551739L,
                                                u'uuid_mslong': 5922516436339146834}},
                       u'network_ipam_mgmt': {u'dhcp_option_list': None,
                                               u'ipam_method': u'dhcp'},
                       u'_type': u'network-ipam',
                       u'virtual_network_back_refs': [{u'attr': {u'ipam_subnets': [{u'default_gateway': None,
                                                                                     u'subnet': {u'ip_prefix': u'192.168.1.0',
                                                                                                 u'ip_prefix_len': 24}}]},
                                                        u'href': u'http://10.84.7.3:8082/virtual-network/6a5c5c29-cfe6-4fea-9768-b0dea3b217bc',
                                                        u'to': [u'ted-domain',
                                                                u'ted-eng',
                                                                u'ted-back'],
                                                        u'uuid': u'6a5c5c29-cfe6-4fea-9768-b0dea3b217bc'}],
                       u'href': u'http://10.84.7.3:8082/network-ipam/52310151-ec68-4052-9114-14ae1a47f2fb',
                       u'name': u'default-network-ipam',
                       u'parent_name': u'ted-eng',
                       u'uuid': u'52310151-ec68-4052-9114-14ae1a47f2fb'}}

        '''
        p = self.try_cache ('ipam', [domain, project, ipam], refresh)
        if p:
            return p
        # cache miss
        proj = self.get_cs_project (domain, project)
        if proj:
            #import pdb; pdb.set_trace ()
            myipam = filter (lambda x: x['to'] == [domain, project, ipam],
                    proj['project']['network_ipams'])
            if 1 == len(myipam):
                p = self.dict_get (myipam[0]['href'])
        if p:
            self.update_cache ('ipam', [domain, project, ipam], p)
        return p

    def get_cs_policy (self, domain='default-domain', project='admin',
            policy='default-network-policy', refresh=False):
        '''
            method: get_cs_ipam find an ipam
            returns None if not found, a dict w/ attrib. eg:
        {u'network-policy': {u'fq_name': [u'ted-domain',
                                           u'ted-eng',
                                           u'default-network-policy'],
                             u'id_perms': {u'created': None,
                                            u'enable': True,
                                            u'last_modified': None,
                                            u'permissions': {u'group': u'cloud-admin-group',
                                                             u'group_access': 7,
                                                             u'other_access': 7,
                                                             u'owner': u'cloud-admin',
                                                             u'owner_access': 7},
                                            u'uuid': {u'uuid_lslong': 9537345350817167511L,
                                                      u'uuid_mslong': 14052464141133300902L}},
                             u'_type': u'network-policy',
                             u'href': u'http://10.84.7.3:8082/network-policy/c30461ae-e72a-44a6-845b-7510c7ae3897',
                             u'name': u'default-network-policy',
                             u'parent_name': u'ted-eng',
                             u'uuid': u'c30461ae-e72a-44a6-845b-7510c7ae3897'}}

        '''
        p = self.try_cache ('policy', [domain, project, policy], refresh)
        if p:
            return p
        # cache miss
        proj = self.get_cs_project (domain, project)
        if proj:
            #import pdb; pdb.set_trace ()
            mypolicy = filter (lambda x: x['to'] == [domain, project, policy], 
                    proj['project']['network_policys'])
            if 1 == len(mypolicy):
                p = self.dict_get (mypolicy[0]['href'])
        if p:
            self.update_cache ('policy', [domain, project, policy], p)
        return p

    def get_cs_vn (self, domain='default-domain', project='admin',
        vn='default-virtual-network', refresh=False):
        '''
        method: get_cs_vn find a vn
        returns None if not found, a dict w/ attrib. eg:
{u'virtual-network': {u'fq_name': [u'ted-domain', u'ted-eng', u'ted-back'],
                  u'id_perms': {u'created': None,
                                 u'enable': True,
                                 u'last_modified': None,
                                 u'permissions': {u'group': u'cloud-admin-group',
                                                  u'group_access': 7,
                                                  u'other_access': 7,
                                                  u'owner': u'cloud-admin',
                                                  u'owner_access': 7},
                                 u'uuid': {u'uuid_lslong': 10910164567580612540L,
                                           u'uuid_mslong': 7664102000529133546}},
                  u'instance_ip_back_refs': [{u'attr': {},
                                               u'href': u'http://10.84.7.3:8082/instance-ip/9d4cbfbc-da80-4732-a98e-77607bd78704',
                                               u'to': [u'9d4cbfbc-da80-4732-a98e-77607bd78704'],
                                               u'uuid': u'9d4cbfbc-da80-4732-a98e-77607bd78704'}],
                  u'network_ipam_refs': [{u'attr': {u'ipam_subnets': [{u'default_gateway': None,
                                                                        u'subnet': {u'ip_prefix': u'192.168.1.0',
                                                                                    u'ip_prefix_len': 24}}]},
                                           u'href': u'http://10.84.7.3:8082/network-ipam/52310151-ec68-4052-9114-14ae1a47f2fb',
                                           u'to': [u'ted-domain',
                                                   u'ted-eng',
                                                   u'default-network-ipam'],
                                           u'uuid': u'52310151-ec68-4052-9114-14ae1a47f2fb'}],
                  u'routing_instances': [{u'attr': {},
                                           u'href': u'http://10.84.7.3:8082/routing-instance/a68948af-46be-4f26-b73e-9ec725f57437',
                                           u'to': [u'ted-domain',
                                                   u'ted-eng',
                                                   u'ted-back',
                                                   u'ted-back'],
                                           u'uuid': u'a68948af-46be-4f26-b73e-9ec725f57437'}],
                  u'_type': u'virtual-network',
                  u'virtual_machine_interface_back_refs': [{u'attr': {},
                                                             u'href': u'http://10.84.7.3:8082/virtual-machine-interface/864ecd37-cf1f-43d5-9f63-4f24831859eb',
                                                             u'to': [u'c707f91f-68e9-427a-a0ba-92563c0d067f',
                                                                     u'864ecd37-cf1f-43d5-9f63-4f24831859eb'],
                                                             u'uuid': u'864ecd37-cf1f-43d5-9f63-4f24831859eb'}],
                  u'href': u'http://10.84.7.3:8082/virtual-network/6a5c5c29-cfe6-4fea-9768-b0dea3b217bc',
                  u'name': u'ted-back',
                  u'parent_name': u'ted-eng',
                  u'uuid': u'6a5c5c29-cfe6-4fea-9768-b0dea3b217bc'}}

        '''
        p = self.try_cache ('vn', [domain, project, vn], refresh)
        if p:
            return p
        # cache miss
        proj = self.get_cs_project (domain, project)
        if proj:
            myvn = filter (lambda x: x['to'] == [domain, project, vn], 
                    proj['project']['virtual_networks'])
            if 1 == len(myvn):
                p = self.dict_get (myvn[0]['href'])
        if p:
            self.update_cache ('vn', [domain, project, vn], p)
        return p

    def get_cs_alloc_fip_pool (self, domain='default-domain', project='admin',
            vn='default-virtual-network', fip_pool='default-floating-ip-pool',
            refresh=False):
        '''
            method: get_cs_alloc_fip_pool finds a fip pool allocated in vn
            returns None if not found, a dict w/ attrib. eg:
{u'floating-ip-pool': {u'fq_name': [u'ted-domain',
                                     u'ted-eng',
                                     u'ted-front',
                                     u'ted_fip_pool'],
                       u'id_perms': {u'created': None,
                                      u'enable': True,
                                      u'last_modified': None,
                                      u'permissions': {u'group': u'cloud-admin-group',
                                                       u'group_access': 7,
                                                       u'other_access': 7,
                                                       u'owner': u'cloud-admin',
                                                       u'owner_access': 7},
                                      u'uuid': {u'uuid_lslong': 13214437371555268939L,
                                                u'uuid_mslong': 18023639221065174839L}},
                       u'project_back_refs': [{u'attr': {},
                                                u'href': u'http://10.84.7.3:8082/project/1fcf3244-d4d9-407d-8637-54bb2522020e',
                                                u'to': [u'ted-domain',
                                                        u'default-project'],
                                                u'uuid': u'1fcf3244-d4d9-407d-8637-54bb2522020e'}],
                       u'_type': u'floating-ip-pool',
                       u'href': u'http://10.84.7.3:8082/floating-ip-pool/fa20d460-d363-4f37-b763-1cc6be32c94b',
                       u'name': u'ted_fip_pool',
                       u'parent_name': u'ted-front',
                       u'uuid': u'fa20d460-d363-4f37-b763-1cc6be32c94b'}}

        '''
        p = self.try_cache ('fip_alloc_pool', [domain, project, vn,
                fip_pool], refresh)
        if p:
            return p
        # cache miss
        _vn = self.get_cs_vn (domain, project, vn)
        if _vn:
            myfip_alloc_pool = filter (lambda x: x['to'] == [domain, project,
                    vn, fip_pool], _vn['virtual-network'][
                    'floating_ip_pools'])
            if 1 == len(myfip_alloc_pool):
                p = self.dict_get (myfip_alloc_pool[0]['href'])
        if p:
            self.update_cache ('fip_alloc_pool', 
                    [domain, project, vn, fip_pool], p)
        return p

    def get_cs_use_fip_pool (self, domain='default-domain', project='admin',
            fip_pool=['default-domain', 'admin', 'default-virtual-network',
            'default-floating-ip-pool'], refresh=False):
        '''
            method: get_cs_use_fip_pool finds a fip pool used by a project
            returns None if not found, a dict w/ attrib. eg:
{u'floating-ip-pool': {u'fq_name': [u'ted-domain',
                                     u'ted-eng',
                                     u'ted-front',
                                     u'ted_fip_pool'],
                       u'id_perms': {u'created': None,
                                      u'enable': True,
                                      u'last_modified': None,
                                      u'permissions': {u'group': u'cloud-admin-group',
                                                       u'group_access': 7,
                                                       u'other_access': 7,
                                                       u'owner': u'cloud-admin',
                                                       u'owner_access': 7},
                                      u'uuid': {u'uuid_lslong': 13214437371555268939L,
                                                u'uuid_mslong': 18023639221065174839L}},
                       u'project_back_refs': [{u'attr': {},
                                                u'href': u'http://10.84.7.3:8082/project/1fcf3244-d4d9-407d-8637-54bb2522020e',
                                                u'to': [u'ted-domain',
                                                        u'default-project'],
                                                u'uuid': u'1fcf3244-d4d9-407d-8637-54bb2522020e'}],
                       u'_type': u'floating-ip-pool',
                       u'href': u'http://10.84.7.3:8082/floating-ip-pool/fa20d460-d363-4f37-b763-1cc6be32c94b',
                       u'name': u'ted_fip_pool',
                       u'parent_name': u'ted-front',
                       u'uuid': u'fa20d460-d363-4f37-b763-1cc6be32c94b'}}

        '''
        p = self.try_cache ('fip_use_pool', [domain, project,
                '::'.join (fip_pool)], refresh)
        if p:
            return p
        # cache miss
        proj = self.get_cs_project (domain, project)
        if proj and proj['project'].has_key ('floating_ip_pool_refs'):
            #import pdb; pdb.set_trace ()
            myfip = filter (lambda x: x['to'] == fip_pool,
                    proj['project']['floating_ip_pool_refs'])
            if 1 == len(myfip):
                p = self.dict_get (myfip[0]['href'])
        if p:
            self.update_cache ('fip_use_pool', [domain, project,
                            '::'.join (fip_pool)], p)
        return p

    def policy_update (self, domain='default-domain', *arg):
        pass

    def dissassociate_ip (self, domain='default-domain', *arg):
        pass


class VerificationControl (VerificationUtilBase):
    def __init__ (self, ip):
        super (VerificationControl, self).__init__ (ip, 8083, XmlDrv)

    def _join(self, *args):
        return ':'.join(args)

    def _get_if_map_table_entry (self, match):
	p=self.dict_get('Snh_IFMapTableShowReq')
        xp=p.xpath('./IFMapTableShowResp/ifmap_db/list/IFMapNodeShowInfo/node_name')
        f=filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return f

    def get_cn_routing_instance(self, riname, domain='default-domain',
                                project='admin'):
        '''Returns a routing instance dictionary.
        '''
        m = self._join(domain, project, riname, riname)
        path = 'Snh_ShowRoutingInstanceReq?name=%s' % m
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_routing_instance_list(self, domain='default-domain',
                                     project='admin'):
        '''Returns a list of routing instance dictionaries.
        '''
        path = 'Snh_ShowRoutingInstanceReq'
        xpath = '/ShowRoutingInstanceResp/instances/list/ShowRoutingInstance'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_route_table(self, domain='default-domain', project='admin',
                           fabric='ip-fabric', riname='__default__'):
        '''Returns a routing table dictionary of a specifc routing instance,
        includes both the unicast and multicast table.
        ''' 
        m = self._join(domain, project, fabric, riname)
        path = 'Snh_ShowRouteReq?name=%s' % m
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        return EtreeToDict(xpath).get_all_entry(p)

    def get_cn_route_table_entry(self, prefix, domain='default-domain', project='admin',
                                 fabric='ip-fabric', riname='__default__'):
        '''Returns the route dictionary for requested prefix and routing instance.
        '''
        m = self._join(domain, project, fabric, riname)
        path = 'Snh_ShowRouteReq?name=%s' % m
        xpath = '/ShowRouteResp/tables/list/ShowRouteTable'
        p = self.dict_get(path)
        rt = EtreeToDict(xpath).get_all_entry(p)
        for entry in rt:
            for route in entry['routes']:
                if route['prefix'] == prefix:
                    return route['paths']

    def get_cn_domain (self, domain='default-domain'):
        pass

    def get_cn_project (self, domain='default-domain', project='admin'):
        pass

    def get_vn_ipam (self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        m='network-ipam:'+domain+':'+project+':'+ipam
        return self._get_if_map_table_entry (m)
    

    def get_cn_policy (self, domain='default-domain', project='admin', policy='default-network-policy'):
        m='network-policy:'+domain+':'+project+':'+policy
        return self._get_if_map_table_entry (m)

    def get_cn_vn (self, domain='default-domain', project='admin', vn='default-virtual-network'):
        m='virtual-network:'+domain+':'+project+':'+vn
        return self._get_if_map_table_entry (m)

    def get_cn_fip_pool (self, domain='default-domain', project='admin', vn='default-virtual-network', fip_pool='default-floating-ip-pool'):
        m='floating-ip-pool:'+domain+':'+project+':'+vn+':'+fip_pool
        return self._get_if_map_table_entry (m)

    def policy_update (self, domain='default-domain', *arg):
        pass

    def dissassociate_ip (self, domain='default-domain', *arg):
        pass


class VerificationVnAgent (VerificationUtilBase):
    def __init__ (self, ip):
        super (VerificationVnAgent, self).__init__ (ip, 8085, XmlDrv)

    def get_vna_domain (self, domain='default-domain'):
        pass

    def get_vna_project (self, domain='default-domain', project='admin'):
        pass

    def get_vna_ipam (self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        pass

    def get_vna_policy (self, domain='default-domain', project='admin', policy='default-network-policy'):
        pass

    def get_vna_vn (self, domain='default-domain', project='admin',
            vn='default-virtual-network'):
        '''
            method: get_vna_vn finds a vn
            returns None if not found, a dict w/ attrib. eg:

            {'acl_uuid': '00000000-0000-0000-0000-000000000000',
             'ipam_data': None,
             'mirror_acl_uuid': '00000000-0000-0000-0000-000000000000',
             'name': 'default-domain:admin:front-end',
             'uuid': '75b38b78-554e-40fe-96ca-e7137b8d9974',
             'vrf_name': 'default-domain:admin:front-end:front-end'}


        '''
        p = None
        vnl = self.dict_get ('Snh_VnListReq?name=')
        avn = filter (lambda x: x.xpath ('./name')[0].text == ':'.join (
                    (domain, project, vn)), vnl.xpath (
                        './vn_list/list/VnSandeshData'))
        if 1 == len (avn):
            p = {}
            for e in avn[0]:
                p[e.tag] = e.text
        #import pdb; pdb.set_trace ()
        return p

    def get_cs_alloc_fip_pool (self, domain='default-domain', project='admin', fip_pool='default-floating-ip-pool'):
        pass

    def policy_update (self, domain='default-domain', *arg):
        pass

    def dissassociate_ip (self, domain='default-domain', *arg):
        pass


class VerificationOpsSrv (VerificationUtilBase):
    def __init__ (self, ip):
        super (VerificationOpsSrv, self).__init__ (ip, 8081)

    def get_ops_domain (self, domain='default-domain'):
        pass

    def get_ops_project (self, domain='default-domain', project='admin'):
        pass

    def get_ops_ipam (self, domain='default-domain', project='admin', ipam='default-network-ipam'):
        pass

    def get_ops_policy (self, domain='default-domain', project='admin', policy='default-network-policy'):
        pass

    def get_ops_vn (self, domain='default-domain', project='admin', vn='default-virtual-network'):
        pass

    def get_cs_alloc_fip_pool (self, domain='default-domain', project='admin', fip_pool='default-floating-ip-pool'):
        pass

    def policy_update (self, domain='default-domain', *arg):
        pass

    def dissassociate_ip (self, domain='default-domain', *arg):
        pass

if __name__ == '__main__':
    va = VerificationApiSrv ('10.84.7.3')
    print va.get_cs_domain ('red-domain'),  va.get_cs_domain ('ted-domain') 
    print va.get_cs_project ('ted-domain', 'ted-eng') 
    print va.get_cs_ipam ('ted-domain', 'ted-eng', 'default-network-ipam') 
    print va.get_cs_policy ('ted-domain', 'ted-eng', 'default-network-policy') 
    print va.get_cs_vn ('ted-domain', 'ted-eng', 'ted-back') 
    print va.get_cs_alloc_fip_pool ('ted-domain', 'ted-eng', 'ted-front', 'ted_fip_pool') 
    print va.get_cs_use_fip_pool ('ted-domain', 'default-project', ['ted-domain', 'ted-eng', 'ted-front', 'ted_fip_pool']) 
    va = VerificationApiSrv ('10.84.7.3')
    print va.get_cs_domain ('red-domain'),  va.get_cs_domain ('ted-domain') 
    print va.get_cs_project ('ted-domain', 'ted-eng') 
    va = VerificationControl ('10.84.14.3')
    print va.get_cn_routing_instance_list()
    print va.get_cn_routing_instance(riname='pub')
    print va.get_cn_route_table(fabric='pub', riname='pub')
    print va.get_cn_route_table_entry('172.168.10.253/32', fabric='pub', riname='pub')
    print va.get_vn_ipam ('default-domain', 'demo', 'default-network-ipam'), va.get_vn_ipam ('default-domain', 'demo', 'default-network-ipam2')
    print va.get_cn_policy ('default-domain', 'default-project', 'default-network-policy'), va.get_cn_policy ('default-domain', 'default-project', 'default-network-policy2')
    print va.get_cn_vn ('default-domain', 'default-project', 'ip-fabric'), va.get_cn_vn ('my-domain', 'my-proj', 'my-fe')
    print va.get_cn_fip_pool ('ted-domain', 'ted-eng', 'ted-front', 'ted_fip_pool'), va.get_cn_fip_pool ('ted-domain', 'ted-eng', 'ted-front', 'ted-fip-pool2')

    #import pdb; pdb.set_trace ()
    vvnagnt = VerificationVnAgent ('10.84.7.3')
    print vvnagnt.get_vna_vn ('default-domain', 'admin', 'front-end')
