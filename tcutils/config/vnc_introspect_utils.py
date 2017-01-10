import logging as LOG

from tcutils.verification_util import *
from vnc_api_results import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class VNCApiInspect (VerificationUtilBase):

    def __init__(self, ip, inputs, protocol='http', logger=LOG):
        super(VNCApiInspect, self).__init__(
            ip, inputs.api_server_port, logger=logger, args=inputs, protocol=protocol)
        self._cache = {
            'domain': {},
            'project': {},
            'ipam': {},
            'policy': {},
            'vn': {},
            'fip_alloc_pool': {},
            'fip_use_pool': {},
            'vm': {},
            'vr': {},
            'vmi': {},
            'iip': {},
            'fip': {},
            'ri': {},
            'rt': {},
            'secgrp': {},
            'si': {},
            'st': {},
            'pt': {},
            'dns': {},
            'dns_rec': {},
            'lb_pool': {},
            'lb_vip': {},
            'lb_member': {},
            'lb_healthmonitor': {},
            'svc_hc': {}, 
            'lr': {},
            'table': {},
            'loadbalancer': {},
            'api-access-list': {},
            'alarm':{},
        }

    def update_cache(self, otype, fq_path, d):
        self._cache[otype]['::'.join(fq_path)] = d

    def try_cache(self, otype, fq_path, refresh):
        p = None
        try:
            if not (refresh or self.get_force_refresh()):
                p = self._cache[otype]['::'.join(fq_path)]
        except KeyError:
            pass
        return p

    def try_cache_by_id(self, otype, uuid, refresh):
        if not (refresh or self.get_force_refresh()):
            for p in self._cache[otype].values():
                if p.uuid() == uuid:
                    return p
        return None

    def get_cs_domain(self, domain='default-domain', refresh=False):
        '''
            method: get_cs_domain find a domain by domin name
            returns CsDomainResult object, None if not found

        '''
        d = self.try_cache('domain', [domain], refresh)
        if not d:
            # cache miss
            doms = self.dict_get('domains')
            mydom = filter(lambda x: x['fq_name'][-1] == domain,
                           doms['domains'])
            if mydom:
                dd = self.dict_get(mydom[-1]['href'])
            # cache set
            if dd:
                d = CsDomainResult(dd)
                self.update_cache('domain', [domain], d)
        return d

    def get_cs_project(self, domain='default-domain', project='admin',
                       refresh=True):
        '''
            method: get_cs_project find a project by domin & project name
            returns None if not found, a dict w/ project attrib. eg:
        '''
        p = self.try_cache('project', [domain, project], refresh)
        pp = None
        if not p:
            # cache miss
            dom = self.get_cs_domain(domain, refresh=True)
            if dom:
                myproj = dom.project(project)
                # myproj = filter (lambda x: x['to'] == [domain, project],
                #        dom['domain']['_projects'])
                if 1 == len(myproj):
                    pp = self.dict_get(myproj[0]['href'])
            if pp:
                p = CsProjectResult(pp)
                self.update_cache('project', [domain, project], p)
        return p

    def get_cs_ipam(self, domain='default-domain', project='admin',
                    ipam='default-network-ipam', refresh=False):
        '''
            method: get_cs_ipam find an ipam
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('ipam', [domain, project, ipam], refresh)
        pp = None
        if not p:
            # cache miss
            proj = self.get_cs_project(domain, project, refresh)
            if proj:
                myipam = filter(lambda x: x['to'] == [domain, project, ipam],
                                proj['project']['network_ipams'])
                if 1 == len(myipam):
                    pp = self.dict_get(myipam[0]['href'])
            if pp:
                p = CsIPAMResult(pp)
                self.update_cache('ipam', [domain, project, ipam], p)
        return p

    def get_cs_policy(self, domain='default-domain', project='admin',
                      policy='default-network-policy', refresh=False):
        '''
            method: get_cs_ipam find an ipam
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('policy', [domain, project, policy], refresh)
        if not p:
            # cache miss
            proj = self.get_cs_project(domain, project, refresh)
            if proj:
                mypolicy = proj.policy(policy)
                if 1 == len(mypolicy):
                    pp = self.dict_get(mypolicy[0]['href'])
            if pp:
                p = CsPolicyResult(pp)
                self.update_cache('policy', [domain, project, policy], p)
        return p

    def get_cs_ri_by_id(self, ri_id=''):
        '''
        method: get_cs_ri find a ri
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = None
        if ri_id:
            pp = None
            try:
                pp = self.dict_get('routing-instance/' + ri_id)
            except:
                self.log.debug("Rounting instance ID: % not found", ri_id)

            if pp:
                p = CsRiResult(pp)
        return p

    def get_cs_vn_by_id(self, vn_id='', refresh=False):
        '''
        method: get_cs_vn find a vn
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('vn', vn_id, refresh)
        if not p and vn_id:
            # cache miss
            pp = None
            try:
                pp = self.dict_get('virtual-network/' + vn_id)
            except:
                self.log.debug("Virtual Network ID: %s not found", vn_id)

            if pp:
                p = CsVNResult(pp)
                self.update_cache('vn', p.fq_name().split(':'), p)
        return p

    def get_cs_vn(self, domain='default-domain', project='admin',
                  vn='default-virtual-network', refresh=False):
        '''
        method: get_cs_vn find a vn
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('vn', [domain, project, vn], refresh)
        if not p:
            # cache miss
            pp = None
            proj = self.get_cs_project(domain, project, refresh)
            if proj:
                myvn = proj.vn(vn)
                if 1 == len(myvn):
                    pp = self.dict_get(myvn[0]['href'])
            if pp:
                p = CsVNResult(pp)
                self.update_cache('vn', [domain, project, vn], p)
        return p

    # TODO
    def get_cs_vn_policys(self, project='admin',  domain='default-domain', vn='default-virtual-network', refresh=False):
        '''
        method: get_cs_vn_policys  find a vn associated policys
        returns None if not found,or  a list of virtual network associated policys

        '''
        vn_final_policy_list = []
        vn_attach_policy_list = {}
        vn_obj = self.get_cs_vn(domain='default-domain',
                                project=project, vn=vn, refresh=True)
        if 'network_policy_refs' in vn_obj['virtual-network']:
            vn_pol = vn_obj['virtual-network']['network_policy_refs']
        else:
            return vn_final_policy_list
        for i in range(len(vn_pol)):
            vn_attach_policy_list[vn_pol[i]['attr']['sequence']
                                  ['major']] = (str(vn_pol[i]['to'][-1]))
        policy_major_no_list = vn_attach_policy_list.keys()
        order_policys = sorted(policy_major_no_list)
        for policy in order_policys:
            vn_final_policy_list.append(vn_attach_policy_list[policy])
        return vn_final_policy_list

    def get_cs_dns(self, vdns_name, domain='default-domain', refresh=False):
        p = self.try_cache('dns', [domain, vdns_name], refresh)
        if not p:
            pp = None
            dom = self.get_cs_domain(domain, refresh)
            if dom:
                #myvdns =dom.vdns_list()
                if dom.vdns_list() is None:
                    self.log.debug('VDNS information not found in API server')
                    return None
                myvdns = dom.vdns(vdns_name)
                if myvdns:
                    pp = self.dict_get(myvdns[0]['href'])
            if pp:
                p = CsVdnsResult(pp)
                self.update_cache('dns', [domain, vdns_name], p)
        return p

    def get_cs_dns_rec(self, rec_name, vdns_name, domain='default-domain', refresh=False):
        p = self.try_cache('dns_rec', [domain, rec_name], refresh)
        if not p:
            pp = None
            rec_ref = None
            dom = self.get_cs_domain(domain, refresh)
            if dom:
                mydns = dom.vdns(vdns_name)
                if mydns:
                    pp = self.dict_get(mydns[0]['href'])
            if pp:
                dns_recs = pp['virtual-DNS']['virtual_DNS_records']
                for rec in dns_recs:
                    if rec['to'][2] == rec_name:
                        rec_ref = rec['href']
                        break
                rec_data = self.dict_get(rec_ref)
                p = CsVdnsResult(rec_data)
                self.update_cache('dns_rec', [domain, rec_name], p)
        return p

    def get_cs_fip_list(self, domain='default-domain', project='admin'):
        '''
        Returns the floating-ips currently used in the project
        '''

    # end get_cs_fip_list

    def get_cs_fip_pool(self, fip_pool_id):
        p = self.dict_get('floating-ip-pool/%s'%fip_pool_id)
        return CsUseFipResult(p) if p else None

    def get_cs_fip(self, fip_id, refresh):
        '''
        Given a Floating IP ID, return the floating-ip dict for it.
        '''
        p = self.try_cache('fip', fip_id, refresh)
        pp = None
        if not p:
            # cache miss
            try:
                pp = self.dict_get('floating-ip/%s' % fip_id)
                if pp:
                    p = CsFipIdResult(pp)
                    self.update_cache('fip', fip_id, p)
            except Exception as e:
                self.log.error(e)
        return p
    # end get_cs_fip

    def get_cs_alloc_fip_pool(self, domain='default-domain', project='admin',
                              vn_name='default-virtual-network', fip_pool_name='default-floating-ip-pool',
                              refresh=False):
        '''
            method: get_cs_alloc_fip_pool finds a fip pool allocated in vn
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('fip_alloc_pool', [domain, project, vn_name,
                                              fip_pool_name], refresh)
        pp = None
        if not p:
            # cache miss
            _vn = self.get_cs_vn(domain, project, vn_name, refresh)
            if _vn:
                myfip_alloc_pool = _vn.fip(fip_pool_name)
                if 1 == len(myfip_alloc_pool):
                    pp = self.dict_get(myfip_alloc_pool[0]['href'])
            if pp:
                p = CsAllocFipPoolResult(pp)
                self.update_cache('fip_alloc_pool',
                                  [domain, project, vn_name, fip_pool_name], p)
        return p

    def get_cs_use_fip_pool(self, domain='default-domain', project='admin',
                            fip_pool_name='default-floating-ip-pool', vn_name='default-virtual-network',
                            refresh=False):
        '''
            method: get_cs_use_fip_pool finds a fip pool used by a project
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('fip_use_pool', [domain, project,
                                            '::'.join(fip_pool_name)], refresh)
        if p:
            return p
        # cache miss
        pp = None
        proj = self.get_cs_project(domain, project, refresh)
        if proj and proj['project'].has_key('floating_ip_pool_refs'):
            myfip = proj.fip_list(fip_pool_name)
            if 1 == len(myfip):
                pp = self.dict_get(myfip[0]['href'])
        if pp:
            p = CsUseFipResult(pp)
            self.update_cache('fip_use_pool', [domain, project,
                                               '::'.join(fip_pool_name)], p)
        return p

    def get_cs_vm(self, vm_id, refresh=False):
        '''

        Returns VM object in API Server as in http://172.27.58.57:8082/virtual-machine/<VM ID>
        '''
        p = self.try_cache('vm', vm_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('virtual-machine/%s' % vm_id)
            if pp:
                p = CsVMResult(pp)
                self.update_cache('vm', vm_id, p)
        return p
    # end get_cs_vm

    def get_cs_vr_of_vm(self, vm_id, refresh=False):
        '''

        Returns the Virtual Router object using the virtual_router_back_refs of a link : http://172.27.58.57:8082/virtual-machine/<VM ID>
        '''
        p = self.try_cache('vr', vm_id, refresh)
        pp = None
        if not p:
            # cache miss
            vm = self.get_cs_vm(vm_id, refresh)
            if vm:
                pp = self.dict_get(vm.vr_link())
            if pp:
                p = CsVrOfVmResult(pp)
                self.update_cache('vr', vm_id, p)
        return p
    # end get_vr_of_vm

    def get_cs_vmi_of_vm(self, vm_id, refresh=False):
        '''

        Returns the Virtual Machine Interface using virtual_machine_interfaces link in http://host/virtual-machine/<VM-ID>
        '''
        p = self.try_cache('vmi', vm_id, refresh) or []
        pp = []
        if not p:
            # cache miss
            vm = self.get_cs_vm(vm_id, refresh)
            if vm:
                links = vm.vmi_links()
                for link in links:
                    pp.append(self.dict_get(link))
            if pp:
                p = []
                for vmi in pp:
                    p.append(CsVmiOfVmResult(vmi))
                self.update_cache('vmi', vm_id, p)
        return p
    # end get_cs_vmi_of_vm

    def get_cs_instance_ips_of_vm(self, vm_id, refresh=False):
        '''

        Returns the Instance-IP objects using virtual_machine_interfaces link of a VM
        '''
        p = self.try_cache('iip', vm_id, refresh) or []
        pp = []
        if not p:
            # cache miss
            vmi_objs = self.get_cs_vmi_of_vm(vm_id, refresh)
            if vmi_objs:
                for vmi_obj in vmi_objs:
                    for link in vmi_obj.ip_link():
                        pp.append(self.dict_get(link))
            if pp:
                p = []
                for ip_obj in pp:
                    p.append(CsIipOfVmResult(ip_obj))
                self.update_cache('iip', vm_id, p)
        return p
    # end get_instance_ips_of_vm

    def get_cs_floating_ips_of_vm(self, vm_id, refresh=False):
        '''

        Returns the Floating-IP objects using virtual_machine_interfaces link of a VM
        '''
        p = self.try_cache('fip', vm_id, refresh)
        pp = []
        if not p:
            # cache miss
            vmi_objs = self.get_cs_vmi_of_vm(vm_id, refresh)
            if vmi_obj:
                try:
                    #import pdb; pdb.set_trace ()
                    for vmi_obj in vmi_objs:
                        pp.append(self.dict_get(vmi_obj.fip_link()))
                    if pp:
                        p = []
                        for fip_obj in pp:
                            p.append(CsFipOfVmResult(fip_obj))
                        self.update_cache('fip', vm_id, p)
                except Exception as e:
                    self.log.error(e)
        return p
    # end get_cs_floating_ips_of_vm

    def get_cs_routing_instances(self, vn_id='', refresh=True):
        ''' Get a list of Routing instances mapped to the VN
        '''
        p = self.try_cache_by_id('ri', vn_id, refresh)
        if not p:
            pp = CsRiResult({'routing_instances': []})
            for rl in self.get_cs_vn_by_id(vn_id, refresh).ri_links():
                pp['routing_instances'].append(self.dict_get(rl))
            if pp['routing_instances']:
                p = pp
                self.update_cache('ri', vn_id, p)
        return p

    # end get_cs_routing_instances

    def get_cs_route_targets(self, vn_id=''):
        ''' Get a list of Route targets mapped to the VN
        '''
        p = self.get_cs_routing_instances(vn_id)
        if p:
            pp = CsRtResult({'route_target_list': []})
            for ri in p['routing_instances']:
                ri_uuid = ri['routing-instance']['uuid']
                rt = self.get_cs_route_targets_of_ri(ri_uuid)
                pp['route_target_list'].append(rt)
            if pp['route_target_list']:
                p = pp
                self.update_cache('rt', vn_id, p)
        return p

    # end get_cs_route_targets

    def get_cs_rt_names(self, rt_obj):
        ''' From the result of get_cs_route_targets(), return the list of Route-target names
            Input will be of the form :
{'route_target_list': [{'route_target_list': [{u'route-target': {u'_type': u'route-target', u'fq_name': [u'target:64512:914'], u'uuid': u'b1c0ef9a-cab8-4554-bfcb-74bf963c6a80', u'routing_instance_back_refs': [{u'to': [u'default-domain', u'admin', u'vn222', u'vn222'], u'href': u'http://10.204.216.38:8082/routing-instance/61983e45-dcdf-46d7-87f4-c434f874597f', u'attr': None, u'uuid': u'61983e45-dcdf-46d7-87f4-c434f874597f'}], u'href': u'http://10.204.216.38:8082/route-target/b1c0ef9a-cab8-4554-bfcb-74bf963c6a80', u'id_perms': {u'enable': True, u'uuid': {u'uuid_mslong': 12808500788346766676L, u'uuid_lslong': 13820268247724616320L}, u'created': None, u'description': None, u'last_modified': None, u'permissions': {u'owner': u'cloud-admin', u'owner_access': 7, u'other_access': 7, u'group': u'cloud-admin-group', u'group_access': 7}}, u'name': u'target:64512:914'}}]}]}
        '''
        rt_list = rt_obj['route_target_list'][0].get('route_target_list', [])
        rt_names = []
        for rt in rt_list:
            rt_names.append(str(rt['route-target']['name']))
        self.log.debug("Route Targets: %s", rt_names)
        return rt_names
    # end get_cs_rt_names

    def get_cs_route_targets_of_ri(self, ri_id='', refresh=False):
        ''' Get a list of Route targets mapped to the VN
        '''
        p = self.get_cs_ri_by_id(ri_id)
        if p:
            pp = CsRtResult({'route_target_list': []})
            for rt in p.rt_links():
                pp['route_target_list'].append(self.dict_get(rt))
            if pp['route_target_list']:
                p = pp
        return p
    # end get_cs_route_targets

    def policy_update(self, domain='default-domain', *arg):
        pass

    def dissassociate_ip(self, domain='default-domain', *arg):
        pass

    def get_cs_secgrp(self, domain='default-domain', project='admin',
                      secgrp='default-security-group', refresh=False):
        '''
            method: get_cs_secgrp find an security group
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('secgrp', [domain, project, secgrp], refresh)
        if not p:
            # cache miss
            proj = self.get_cs_project(domain, project, refresh)
            pp = None
            if proj:
                mysecgrp = proj.secgrp(secgrp)
                if mysecgrp:
                    pp = self.dict_get(mysecgrp[0]['href'])
            if pp:
                p = CsSecurityGroupResult(pp)
                self.update_cache('secgrp', [domain, project, secgrp], p)
        return p

    def get_cs_si(self, domain='default-domain', project='admin',
                  si=None, refresh=False):
        '''
            method: get_cs_si find an service instance
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('si', [domain, project, si], refresh)
        if not p:
            # cache miss
            proj = self.get_cs_project(domain, project, refresh)
            pp = None
            if proj:
                mysi = proj.si(si)
                if mysi:
                    pp = self.dict_get(mysi[0]['href'])
            if pp:
                p = CsServiceInstanceResult(pp)
                self.update_cache('si', [domain, project, si], p)
        return p

    def get_cs_vmi_by_id(self, vmi_id, refresh=True):
        '''
            method: get_cs_vmi_by_id finds the VMI by id
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('vmi', vmi_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('virtual-machine-interface/%s' % vmi_id)
            if pp:
                p = CsVirtualMachineInterfaceResult(pp)
                self.update_cache('vmi', p.fq_name().split(':'), p)
        return p

    def get_cs_pt_by_id(self, pt_id, refresh=False):
        '''
            method: get_cs_pt_by_id finds the port-tuple by id
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('pt', pt_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('port-tuple/%s' % pt_id)
            if pp:
                p = CsPortTupleResult(pp)
                self.update_cache('pt', p.fq_name().split(':'), p)
        return p

    def get_cs_si_by_id(self, si_id, refresh=False):
        '''
            method: get_cs_si_by_id find a service instance by id
            returns None if not found, a dict w/ attrib. eg:
        '''
        p = self.try_cache_by_id('si', si_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('service-instance/%s' %si_id)
            if pp:
                p = CsServiceInstanceResult(pp)
                self.update_cache('si', p.fq_name().split(':'), p)
        return p

    def get_cs_st_by_id(self, st_id='', refresh=False):
        '''
        method: get_cs_st_by_id find a st
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('st', st_id, refresh)
        if not p and st_id:
            # cache miss
            pp = self.dict_get('service-template/' + st_id)
            if pp:
                p = CsServiceTemplateResult(pp)
                self.update_cache('st', p.fq_name().split(':'), p)
        return p

    def get_cs_st(self, domain='default-domain', project='admin',
                  st='nat-template', refresh=False):
        '''
            method: get_cs_st find an service template
            returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('st', [domain, project, st], refresh)
        if not p:
            # cache miss
            dom = self.get_cs_domain(domain)
            pp = None
            if dom:
                myst = dom.st(st)
                if myst:
                    pp = self.dict_get(myst[0]['href'])
            if pp:
                p = CsServiceTemplateResult(pp)
                self.update_cache('secgrp', [domain, project, st], p)
        return p

    def get_global_vrouter_config(self):
        '''Gets global vrouter configs'''
        doms = self.dict_get('global-vrouter-configs')
        gvr_config = self.dict_get(doms['global-vrouter-configs'][0]['href'])
        if gvr_config:
            pp = CsGlobalVrouterConfigResult(gvr_config)
        return pp

    def get_computes(self):
        '''Get list of vrouter-agents'''
        vrouters = CsVrouters(self.dict_get('virtual-routers?detail=True'))
        vr_list = list()
        for vrouter in vrouters:
            vr = CsVrouter(vrouter)
#            if vr.is_tor_agent() or vr.is_tsn():
#                continue
            vr_list.append(vr.ip)
        return vr_list

    def get_secgrp_acls_href(self, domain='default-domain', project='admin',
                      secgrp='default-security-group', refresh=False):
        '''
            method: get_secgrp_acls find acls href for a security group
            returns empty list if not found, a list of href
        '''
        p = []
        secgrp_fq_name = ':'.join([domain,project,secgrp])
        proj = self.get_cs_project(domain, project, refresh)
        pp = None
        if proj:
            pp = self.dict_get('access-control-lists')
            for acl in pp['access-control-lists']:
                if ':'.join([acl['fq_name'][0],acl['fq_name'][1],acl['fq_name'][2]]) == secgrp_fq_name:
                    p.append(acl['href'])

        return p

    def get_lb_pool(self, pool_id, refresh=True):
        '''
        method: get_lb_pool find a lb pool
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('lb_pool', pool_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('loadbalancer-pool/%s' % pool_id)
            if pp:
                p = CsLbPool(pp)
                self.update_cache('lb_pool', p.fq_name().split(':'), p)
        return p

    def get_lb_vip(self, vip_id, refresh=False):
        '''
        method: get_lb_vip find a lb vip
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('lb_vip', vip_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('virtual-ip/%s' % vip_id)
            if pp:
                p = CsLbVip(pp)
                self.update_cache('lb_vip', p.fq_name().split(':'), p)
        return p

    def get_lb_member(self, member_id, refresh=False):
        '''
        method: get_lb_member find a lb member
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('lb_member', member_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('loadbalancer-member/%s' % member_id)
            if pp:
                p = CsLbMember(pp)
                self.update_cache('lb_member', p.fq_name().split(':'), p)
        return p

    def get_lb_healthmonitor(self, healthmonitor_id, refresh=False):
        '''
        method: get_lb_healthmonitor find a lb healthmonitor
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache('lb_healthmonitor', healthmonitor_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('loadbalancer-healthmonitor/%s'%healthmonitor_id)
            if pp:
                p = CsLbHealthMonitor(pp)
                self.update_cache('lb_healthmonitor', p.fq_name().split(':'), p)
        return p

    def get_lr(self, uuid, refresh=False):
        p = self.try_cache_by_id('lr', uuid, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('logical-router/%s' % uuid)
            if pp:
                p = CsLogicalRouterResult(pp)
                self.update_cache('lr', p.fq_name().split(':'), p)
        return p

    def get_route_table(self, uuid, refresh=False):
        p = self.try_cache_by_id('table', uuid, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('route-table/%s' % uuid)
            if pp:
                p = CsTableResult(pp)
                self.update_cache('table', p.fq_name().split(':'), p)
        return p

    def get_service_health_check(self, uuid, refresh=False):
        p = self.try_cache_by_id('svc_hc', uuid, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('service-health-check/%s' % uuid)
            if pp:
                p = CsHealthCheckResult(pp)
                self.update_cache('svc_hc', p.fq_name().split(':'), p)
        return p

    def get_healthcheck_of_vmi(self, vmi_id):
        obj = self.dict_get('virtual-machine-interface/%s'%vmi_id)
        return [x['uuid'] for x in obj['virtual-machine-interface'
                                      ].get('service_health_check_refs', [])]

    def get_loadbalancer(self, lb_id, refresh=True):
        '''
        method: get_loadbalancer find the loadbalancer
        returns None if not found, a dict w/ attrib. eg:

        '''
        p = self.try_cache_by_id('loadbalancer', lb_id, refresh)
        if not p:
            # cache miss
            pp = self.dict_get('loadbalancer/%s' % lb_id)
            if pp:
                p = CsLoadbalancer(pp)
                self.update_cache('loadbalancer', p.fq_name().split(':'), p)
        return p

    def get_cs_vmi(self, vmi_id):
        '''
        method: get_loadbalancer find the loadbalancer
        returns None if not found, a dict w/ attrib. eg:

        '''
        obj = self.dict_get('virtual-machine-interface/%s' %vmi_id)
        if obj:
            return CsVMIResult(obj)
        return None

    def get_api_access_list(self, acl_id):
        '''
            method: get_api_access_list get the api access control list
            returns None if not found, a dict w/ attrib. eg:

        '''
        obj = self.dict_get('api-access-list/%s'%acl_id)
        if obj:
            return CsApiAccessList(obj)
        return None

    def get_aaa_mode(self):
        ''' get aaa-mode '''
        dct = self.dict_get('aaa-mode')
        return dct.get('aaa-mode') if dct else None

    def set_aaa_mode(self, aaa_mode):
        ''' set rbac mode '''
        dct = {'aaa-mode': aaa_mode}
        self.put(path='aaa-mode', payload=dct)

    def get_cs_alarm(self,alarm_id):
        obj = self.dict_get('alarm/%s' %alarm_id)
        if obj:
            return CsAlarmResult(obj)
        return None

if __name__ == '__main__':
    va = VNCApiInspect('10.84.7.2')
    r = va.get_cs_domain()
    pr = va.get_cs_project()
    ir = va.get_cs_ipam()
    polr = va.get_cs_policy()
    vnr = va.get_cs_vn(project='demo', vn='fe')
    vmvr = va.get_cs_instance_ip_of_vm("becd5f61-c446-4963-af5a-886138ce026f")
    print r.project_list(), r.uuid(), r.name(), pr.fq_name(), ir.fq_name()
    print polr.fq_name(), vnr.fq_name()
    import pprint
    pprint.pprint(vmvr)
    if vmvr:
        print polr.fq_name(), vnr.vm_link_list(), vmvr.ip()
    fipr = va.get_cs_floating_ip_of_vm("bae09ef8-fcad-4aae-a36e-0969410daf8e")
    if fipr:
        print fipr.ip()
    print va.get_cs_routing_instances('3236c96e-38cf-40d9-94dd-7ec5495192f1')
    print va.get_cs_route_targets_of_ri('97e53a4e-0d10-4c88-aec9-0ebb3e4471f6')
    va = VNCApiInspect('10.84.11.2')
    print va.get_cs_route_targets('6a454d59-aadb-4140-907f-1bd8b378a7ce')
    # print va.get_cs_domain ('red-domain'),  va.get_cs_domain ('ted-domain')
    # print va.get_cs_project ('ted-domain', 'ted-eng')
    # print va.get_cs_ipam ('ted-domain', 'ted-eng', 'default-network-ipam')
    # print va.get_cs_policy ('ted-domain', 'ted-eng', 'default-network-policy')
    # print va.get_cs_vn ('ted-domain', 'ted-eng', 'ted-back')
    # print va.get_cs_alloc_fip_pool ('ted-domain', 'ted-eng', 'ted-front', 'ted_fip_pool')
    # print va.get_cs_use_fip_pool ('ted-domain', 'default-project', ['ted-domain', 'ted-eng', 'ted-front', 'ted_fip_pool'])
    #va = VNCApiInspect ('10.84.7.4')
    # print va.get_cs_domain ('red-domain'),  va.get_cs_domain ('ted-domain')
    # print va.get_cs_project ('ted-domain', 'ted-eng')
    # print va.get_cs_vr_of_vm('e87b5000-722f-420f-9b7b-7dd74f0b87ef')
    # print va.get_cs_vmi_of_vm('e87b5000-722f-420f-9b7b-7dd74f0b87ef')
    # print va.get_cs_instance_ip_of_vm('e87b5000-722f-420f-9b7b-7dd74f0b87ef')
    # print va.get_cs_ipam ('default-domain', 'demo', 'default-network-ipam'), va.get_cs_ipam ('default-domain', 'demo', 'default-network-ipam2')
    # print va.get_cs_policy ('default-domain', 'default-project', 'default-network-policy'), va.get_cs_policy ('default-domain', 'default-project', 'default-network-policy2')
    # print va.get_cs_vn ('default-domain', 'default-project', 'ip-fabric'), va.get_cs_vn ('my-domain', 'my-proj', 'my-fe')
    # print va.get_cs_fip_pool ('ted-domain', 'ted-eng', 'ted-front',
    # 'ted_fip_pool'), cn.get_cs_fip_pool ('ted-domain', 'ted-eng',
    # 'ted-front', 'ted-fip-pool2')
