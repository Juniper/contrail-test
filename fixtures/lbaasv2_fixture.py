import vnc_api_test
from compute_node_test import ComputeNodeFixture
from tcutils.util import get_random_name, retry
from tcutils.parsers.haproxy import parse_haproxy

class LBBaseFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Loadbalancer object
    Optional:
    :param lb_name : name of the Loadbalancer
    :param lb_uuid : UUID of the Loadbalancer
    :param network_id : uuid of the network on which Loadbalancer belongs to
    :param vip_ip : VIP address of the Loadbalancer
    :param fip_id : UUID of FloatingIP object
    :param fip_net_id : UUID of the FloatingIP network object

    '''

    def __init__(self, *args, **kwargs):
        super(LBBaseFixture, self).__init__(self, **kwargs)
        self.lb_name = kwargs.get('lb_name', get_random_name('LB'))
        self.lb_uuid = kwargs.get('lb_uuid', None)
        self.network_id = kwargs.get('network_id', None)
        self.vip_ip = kwargs.get('vip_ip', None)
        self.fip_id = kwargs.get('fip_id', None)
        self.fip_net_id = kwargs.get('fip_net_id', None)
        self.api_type = kwargs.get('api_type', 'neutron')
        self.fip_ip = None
        self.lb_present = False
        self.is_fip_active = False
        self.parent_fq_name = [self.domain, self.project_name]
        self.fq_name = self.parent_fq_name + [self.lb_name]

    def setUp(self):
        super(LBBaseFixture, self).setUp()
        self.lb_create()

    def cleanUp(self):
        super(LBBaseFixture, self).cleanUp()
        if (self.lb_present or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Load Balancer %s :'
                              %(self.fq_name))
        else:
            self.lb_delete()

    def get_network_handle(self):
        if self.api_type == 'contrail':
            return self.get_handle()
        else:
            return self.get_neutron_handle()

    @property
    def network_h(self):
        if not getattr(self, '_network_h', None):
            self._network_h = self.get_network_handle()
        return self._network_h

    def lb_read(self):
        self.logger.debug('Fetching info about Load Balancer %s'%self.lb_uuid)
        self.obj = self.network_h.get_loadbalancer(self.lb_uuid)
        if not self.obj:
            raise Exception('load balancer with id %s not found'%self.lb_uuid)
        self.lb_uuid = self.obj['id']
        self.lb_name = self.obj['name']
        self.vip_ip = self.obj['vip_address']
        self.vip_port_id = self.obj['vip_port_id']
        self.network_id = self.network_h.get_vn_of_subnet(
                          self.obj['vip_subnet_id'])
        fip = self.network_h.list_floatingips(port_id=self.vip_port_id)
        if fip:
            self.fip_id = fip[0]['id']
            self.fip_net_id = fip[0]['floating_network_id']
            self.fip_ip = fip[0]['floating_ip_address']
            self.is_fip_active = True
        self._populate_vars()

    def lb_create(self):
        if not self.lb_uuid:
            obj = self.network_h.list_loadbalancers(name=self.lb_name)
            self.lb_uuid = obj[0]['id'] if obj else None
        if self.lb_uuid:
            self.lb_present = True
        else:
            obj = self.network_h.create_loadbalancer(
                                       name=self.lb_name,
                                       network_id=self.network_id,
                                       address=self.vip_ip)
            self.lb_uuid = obj['id']
        self.lb_read()
        if (self.fip_id or self.fip_net_id) and not self.fip_ip:
            self.create_fip_on_vip()

    def lb_delete(self):
        self.logger.info('Deleting LoadBalancer %s(%s)'%(self.lb_name, self.lb_uuid))
        if self.is_fip_active:
            self.delete_fip_on_vip()
        self.network_h.delete_loadbalancer(self.lb_uuid)
        if getattr(self, 'verify_lb_is_run', None):
            assert self.lb_verify_on_cleanup(), "Verify on cleanup failed after LB delete"
        self.lb_uuid = None

    def create_fip_on_vip(self, fip_net_id=None, fip_id=None):
        fip_net_id = fip_net_id or self.fip_net_id
        fip_id = fip_id or self.fip_id
        if fip_id:
            fip = self.network_h.assoc_floatingip(fip_id,
                                 self.vip_port_id)['floatingip']
        elif fip_net_id:
            fip = self.network_h.create_floatingip(fip_net_id,
                                 port_id=self.vip_port_id)['floatingip']
        self.fip_ip = fip['floating_ip_address']
        self.fip_id = fip['id']
        self.fip_net_id = fip['floating_network_id']
        self.is_fip_active = True
        self.logger.info('Assoc VIP %s with FIP %s'%(self.vip_ip, self.fip_ip))

    def delete_fip_on_vip(self):
        self.network_h.delete_floatingip(self.fip_id)
        self.is_fip_active = False
        self.logger.info('Disassoc VIP %s with FIP %s'%(self.vip_ip,
                                                        self.fip_ip))

    def apply_sg_to_vip_vmi(self, sg_list):
        self.network_h.apply_sg_to_port(self.vip_port_id, sg_list)

    def _populate_vars(self):
        self.si_uuid = None
        self.label = None
        self.active_vm = None
        self.standby_vm = None
        self.control_node = None

    def get_si_name(self):
        return self.lb_uuid

    def get_standby_vrouter(self, refresh=False):
        if not getattr(self, 'standby_vr', None) or refresh:
            self.standby_vr = self._get_vrouter('standby')[1]
        return self.standby_vr

    def get_active_vrouter(self, refresh=False):
        if not getattr(self, 'active_vr', None) or refresh:
            self.active_vr = self._get_vrouter('active')[1]
        return self.active_vr

    @retry(tries=12, delay=5)
    def _get_vrouter(self, ha='active'):
        try:
            svc_mon_h = self.connections.get_svc_mon_h()
            si_obj = svc_mon_h.get_service_instance(name=self.get_si_name(),
                                                    refresh=True)
            if ha == 'active':
                vrouter = si_obj.active_vrouter()
            else:
                vrouter = si_obj.standby_vrouter()
        except:
            vrouter = None
        #vrouter = None if vrouter == 'None' else self.inputs.get_host_ip(vrouter)
        vrouter = None if not vrouter else self.inputs.get_host_ip(vrouter)
        return (True if vrouter else False, vrouter)

    # The test is expected to add start_active_vrouter in addCleanup
    def stop_active_vrouter(self):
        active_vr = self.get_active_vrouter()
        self.inputs.stop_service('supervisor-vrouter', [active_vr])
        self._populate_vars()

    def start_active_vrouter(self):
        active_vr = self.get_active_vrouter()
        self.inputs.start_service('supervisor-vrouter', [active_vr])

    # The test is expected to add start_standby_vrouter in addCleanup
    def stop_standby_vrouter(self):
        standby_vr = self.get_standby_vrouter()
        self.inputs.stop_service('supervisor-vrouter', [standby_vr])
        self._populate_vars()

    def start_standby_vrouter(self):
        standby_vr = self.get_standby_vrouter()
        self.inputs.start_service('supervisor-vrouter', [standby_vr])

    @retry(tries=12, delay=5)
    def _get_active_svc(self):
        active_svc = None
        try:
            svc_mon_h = self.connections.get_svc_mon_h(refresh=True)
            if svc_mon_h:
                active_svc = svc_mon_h._ip
        except:
            self.logger.warn("Fail to get svc_mon_h, verify the contrail status")
        return (True if active_svc else False, active_svc)

    def get_active_svc(self, refresh=False):
        if not getattr(self, 'active_svc', None) or refresh:
            self.active_svc = self._get_active_svc()[1]
        return self.active_svc

    def restart_active_svc_mon(self):
        active_svc = self.get_active_svc()
        self.inputs.restart_service('contrail-svc-monitor', [active_svc])
        self.get_active_svc(refresh=True)

    def get_si(self):
        if not getattr(self, 'si_uuid', None):
            self.si_uuid = None
            self.api_h = self.connections.api_server_inspect
            lb = self.api_h.get_loadbalancer(self.lb_uuid, refresh=True)
            if lb:
                self.si_uuid = lb.si()
            self.logger.debug('LB %s: SI uuid is %s'%(self.lb_uuid, self.si_uuid))
        return self.si_uuid

    def get_vms(self):
        self.api_h = self.connections.api_server_inspect
        si = self.api_h.get_cs_si_by_id(self.get_si(), refresh=True)
        if si:
            return si.get_vms()
        return []

    def get_active_standby_instance(self):
        self.active_vm = None; self.standby_vm = None
        self.api_h = self.connections.api_server_inspect
        for vm_id in self.get_vms():
            vmis = self.api_h.get_cs_vmi_of_vm(vm_id, refresh=True)
            pref = vmis[0].properties('local_preference')
            if pref == 200:
               self.active_vm = vm_id
            else:
               self.standby_vm = vm_id
        return (self.active_vm, self.standby_vm)

    def get_standby_instance(self):
        if not getattr(self, 'standby_vm', None):
            self.get_active_standby_instance()
            if not self.standby_vm:
                self.logger.debug('Unable to get standby vm for LB %s'%self.lb_uuid)
        return self.standby_vm

    def get_active_instance(self):
        if not getattr(self, 'active_vm', None):
            self.get_active_standby_instance()
            if not self.active_vm:
                self.logger.debug('Unable to get active vm for LB %s'%self.lb_uuid)
        return self.active_vm

    def get_vip_label(self, refresh=False):
        if not getattr(self, 'label', None) or refresh:
            self.label = None
            vm_id = self.get_active_instance()
            active_vr = self.get_active_vrouter()
            if not (active_vr and vm_id):
                self.logger.debug('LB: Unable to fetch either of '
                                  'active vm/vrouter info')
                return None
            inspect_h = self.connections.agent_inspect[active_vr]
            vmis = inspect_h.get_vna_tap_interface_by_vm(vm_id)
            if vmis:
                self.label = [vmi['label'] for vmi in vmis
                              if vmi['ip_addr'] == self.vip_ip][0]
            if self.label == -1:
                self.label = None
            if not self.label:
                self.logger.debug('LB: Unable to fetch label of vip intf')
        return self.label

    def get_ctrl_nodes(self, ri_name):
        peer_list = set()
        ri = self.vnc_api_h.routing_instance_read(fq_name=ri_name)
        rt_list = [rt['to'][0] for rt in ri.get_route_target_refs()]
        ctrl_node = ComputeNodeFixture(self.connections,
                                       self.get_active_vrouter()
                                      ).get_active_controller()
        cn_inspect = self.connections.cn_inspect[ctrl_node]
        peer_list.add(ctrl_node)
        for rt in rt_list:
            rt_group_entry = cn_inspect.get_cn_rtarget_group(rt)
            for peer in rt_group_entry['peers_interested'] or []:
                peer_list.add(self.inputs.get_host_ip(peer))
        self.logger.debug('Interested control nodes for rt(%s) %s'%(
                          rt_list, peer_list))
        return list(peer_list)

    def verify_on_setup(self):
        if self.verify_lb_in_api_server() == False:
            self.logger.error('verify_lb_in_api_server failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_lb_in_agent() == False:
            self.logger.error('verify_lb_in_agent failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_lb_in_control_node() == False:
            self.logger.error('verify_lb_in_control_node failed for LB %s'%self.lb_uuid)
            return False
        self.logger.info('LoadBalancer(%s): verify_on_setup passed'%self.lb_uuid)
        self.verify_lb_is_run = True
        return True

    def lb_verify_on_cleanup(self):
        if self.verify_lb_not_in_api_server() == False:
            self.logger.error('verify_lb_not_in_api_server failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_netns_instance_deleted() == False:
            self.logger.error('Netns delete verification failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_vip_not_in_agent() == False:
            self.logger.error('verify_vip_not_in_agent failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_vip_not_in_control_node() == False:
            self.logger.error('verify_vip_not_in_control_node failed for LB %s'%self.lb_uuid)
            return False
        if self.verify_si_deleted() == False:
            self.logger.error('verify_si_delete failed for LB %s'%self.lb_uuid)
            return False
        if self.fip_id:
            if self.verify_fip_not_in_agent() == False:
                self.logger.error('verify_fip_not_in_agent failed for LB %s'%self.lb_uuid)
                return False
            if self.verify_fip_not_in_control_node() == False:
                self.logger.error('verify_fip_not_in_control_node failed for LB %s'%self.lb_uuid)
                return False
        self.logger.info('LoadBalancer(%s): verify_on_cleanup passed'%self.lb_uuid)
        self.lb_uuid = None
        return True

    def verify_lb_in_api_server(self):
        if self.verify_loadbalancer_in_api_server() == False:
            return False
        if self.verify_si_launched() == False:
            return False
        if self.is_fip_active and self.verify_fip_in_api_server() == False:
            return False
        self.logger.info('LoadBalancer(%s): verify_lb_in_api_server passed'%self.lb_uuid)
        return True

    def verify_lb_not_in_api_server(self):
        if self.verify_loadbalancer_not_in_api_server() == False:
            return False
        if self.fip_id:
            if self.verify_fip_not_in_api_server() == False:
                return False
        self.logger.info('LoadBalancer(%s): verify_lb_not_in_api_server passed'%self.lb_uuid)
        return True

    @retry(delay=6, tries=10)
    def verify_hmon_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        hmon = self.api_h.get_lb_healthmonitor(self.hmon_id, refresh=True)
        if not hmon:
            self.logger.warn("HMON %s not found in api server" %self.hmon_id)
            return False
        self.logger.info("HMON %s found in api server" %self.hmon_id)
        return True

    @retry(delay=6, tries=10)
    def verify_hmon_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        hmon = self.api_h.get_lb_healthmonitor(self.hmon_id, refresh=True)
        if hmon:
            self.logger.warn("HMON %s is still found in api server" %self.hmon_id)
            return False
        self.logger.info("HMON %s deleted from api server as expected" %self.hmon_id)
        return True

    @retry(delay=6, tries=10)
    def verify_loadbalancer_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        pool = self.api_h.get_loadbalancer(self.lb_uuid, refresh=True)
        if not pool:
            self.logger.warn("LB %s not found in api server" %self.lb_uuid)
            return False
        self.logger.info("LB %s found in api server" %self.lb_uuid)
        return True

    @retry(delay=6, tries=10)
    def verify_loadbalancer_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        pool = self.api_h.get_loadbalancer(self.lb_uuid, refresh=True)
        if pool:
            self.logger.warn("LB %s still found in api server" %self.lb_uuid)
            return False
        self.logger.info("LB %s deleted from api server" %self.lb_uuid)
        return True

    @retry(delay=6, tries=10)
    def verify_si_launched(self, refresh=False):
        svc_mon_h = self.connections.get_svc_mon_h(refresh)
        si = svc_mon_h.get_service_instance(name=self.get_si_name(),
                                            refresh=True)
        if si and si.is_launched():
            self.logger.info('Load Balancer: SI got launched')
            return True
        self.logger.warn('LB(%s): SI status is not active in svc-mon'%self.lb_uuid)
        return False

    @retry(delay=6, tries=10)
    def verify_si_deleted(self, refresh=True):
        svc_mon_h = self.connections.get_svc_mon_h(refresh)
        si = svc_mon_h.get_service_instance(name=self.get_si_name(),
                                            refresh=True)
        if si:
            self.logger.warn("Service instance , %s , not deleted" % si['name'])
            return False
        self.logger.info("Service instance got deleted")
        return True

    @retry(delay=6, tries=10)
    def verify_fip_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        fip_obj = self.api_h.get_cs_fip(self.fip_id, refresh=True)
        if not fip_obj:
            self.logger.warn("Fip %s not found in api server" %(self.fip_ip))
            return False
        vmi = fip_obj.vmi()
        if self.vip_port_id not in vmi:
            self.logger.warn("FIP doesnt have VIP port id refs, expect %s "
                             "got %s"%(self.vip_port_id, vmi))
            return False
        if len(vmi) != 3:
            self.logger.warn("FIP doesnt have the netns instance vmis refs")
            return False
        self.logger.info('LB(%s): verify_fip_in_api_server passed'%self.lb_uuid)
        return True

    @retry(delay=6, tries=10)
    def verify_fip_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_fip(self.fip_id, refresh=True):
            self.logger.warn('FIP is not deleted from API server')
            return False
        self.logger.info('FIP removal verification passed in API server')
        return True

    def verify_lb_in_agent(self):
        self.verify_netns_instance_launched()
        self.verify_vip_in_agent()
        if self.is_fip_active:
            self.verify_fip_in_agent(), "LB %s: verify_lb_in_agent failed" %self.lb_uuid
        self.logger.info('LB %s: verify_lb_in_agent passed'%self.lb_uuid)
        return True

    @retry(6, 10)
    def verify_netns_instance_launched(self):
        active_vr = self.get_active_vrouter()
        active_vm = self.get_active_instance()
        if not self.is_instance_launched(active_vm, active_vr):
            self.logger.warn('Netns launch verification failed on %s'%active_vr)
            return False
        if len(self.inputs.compute_ips) > 1:
            standby_vr = self.get_standby_vrouter()
            standby_vm = self.get_standby_instance()
            if not self.is_instance_launched(standby_vm, standby_vr):
                self.logger.warn('Netns launch verification failed '
                                 ' on %s'%standby_vr)
                return False
        self.logger.info('Netns instances launched for the LB(%s)' %self.lb_uuid)
        return True

    @retry(6, 10)
    def verify_netns_instance_deleted(self):
        active_vr = self.get_active_vrouter()
        active_vm = self.get_active_instance()
        if self.is_instance_launched(active_vm, active_vr) == True:
            self.logger.warn('LB(%s): Netns not yet removed from %s'
                             %(self.lb_uuid, active_vr))
            return False
        if len(self.inputs.compute_ips) > 1:
            standby_vr = self.get_standby_vrouter()
            standby_vm = self.get_standby_instance()
            if self.is_instance_launched(standby_vm, standby_vr) == True:
                self.logger.warn('LB(%s): Netns not yet removed from %s'
                                 %(self.lb_uuid, standby_vr))
                return False
        self.logger.info('Netns instance got deleted')
        return True

    def is_instance_launched(self, vm_id, vrouter):
        if not vm_id or not vrouter:
            self.logger.debug('is_instance_launched: si vm_id or vrouter'
                             ' info not available')
            return False
        cmd_str = 'ip netns list | grep %s:%s | grep -v grep'%(vm_id, self.lb_uuid)
        output = self.inputs.run_cmd_on_server(vrouter, cmd_str)
        if not output:
            self.logger.debug('netns instance %s:%s not found'
                             %(vm_id, self.lb_uuid))
            return False
        if len(output.strip().split('\n')) > 1:
            self.logger.debug('Multiple %s:%s netns instances found'
                             %(vm_id, self.lb_uuid))
            return False
        cmd_str = 'ps ax | grep haproxy | grep %s | grep -v grep' %self.lb_uuid
        if not self.inputs.run_cmd_on_server(vrouter, cmd_str):
            self.logger.debug('haproxy not found for LB %s'%self.lb_uuid)
            return False
        self.logger.info("netns got launched, so do haproxy")
        return True

    @retry(6, 10)
    def verify_vip_in_agent(self):
        exp_label = self.get_vip_label()
        active_vr = self.get_active_vrouter()
        if not active_vr or not exp_label:
            self.logger.warn('LB(%s): unable to find active vr'%self.lb_uuid)
            return False
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.network_id))
        route = inspect_h.get_vna_active_route(ip=self.vip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if not route or exp_label != route['path_list'][0]['active_label']:
            self.logger.warn('LB: agent: label doesnt match for vip ip %s, '
                             'expected %s: actual %s'%(self.vip_ip,
                             exp_label, route['path_list'][0]['active_label']
                             if route else None))
            return False
        self.logger.info("Verify VIP in agent passed")
        return True

    @retry(6, 10)
    def verify_vip_not_in_agent(self):
        active_vr = self.get_active_vrouter()
        if not active_vr:
            self.logger.warn('LB(%s): unable to find active vr'%self.lb_uuid)
            return True
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.network_id))
        route = inspect_h.get_vna_active_route(ip=self.vip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if route:
            self.logger.warn('LB: vip route %s still found in %s'
                             %(self.vip_ip, vn_fq_name))
            return False
        self.logger.info('LB: vip route %s not found in %s, as expected'
                             %(self.vip_ip, vn_fq_name))
        return True

    @retry(6, 10)
    def verify_fip_in_agent(self):
        exp_label = self.get_vip_label()
        active_vr = self.get_active_vrouter()
        if not active_vr or not exp_label or exp_label < 1:
            self.logger.warn('LB(%s): unable to find active vr'%self.lb_uuid)
            return False
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.fip_net_id))
        route = inspect_h.get_vna_active_route(ip=self.fip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if not route or exp_label != route['path_list'][0]['active_label']:
            self.logger.warn('LB: agent: label doesnt match for fip ip %s, '
                             'expected %s: actual %s'%(self.fip_ip,
                             exp_label, route['path_list'][0]['active_label']
                             if route else None))
            return False
        self.logger.info("LB(%s): Verify FIP in agent passed" %self.lb_uuid)
        return True

    @retry(6, 10)
    def verify_fip_not_in_agent(self):
        active_vr = self.get_active_vrouter()
        if not active_vr:
            self.logger.warn('LB(%s): unable to find active vr'%self.lb_uuid)
            return True
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.fip_net_id))
        route = inspect_h.get_vna_active_route(ip=self.fip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if route:
            self.logger.warn('FIP %s still present in Agent %s'
                             %(self.fip_ip, active_vr))
            return False
        self.logger.info('FIP %s is removed from agent %s'
                         %(self.fip_ip, active_vr))
        return True

    def verify_lb_in_control_node(self):
        if self.verify_vip_in_control_node() == False:
            self.logger.error('LB %s: verify_lb_in_control_node failed'%self.lb_uuid)
            return False
        if self.is_fip_active and self.verify_fip_in_control_node() == False:
            self.logger.error('LB %s: verify_lb_in_control_node failed'%self.lb_uuid)
            return False
        self.logger.info('LB %s: verify_lb_in_control_node passed'%self.lb_uuid)
        return True

    @retry(6, 10)
    def verify_vip_in_control_node(self):
        exp_label = self.get_vip_label()
        if not exp_label:
            self.logger.warn('LB: Unable to fetch vip label')
            return False
        vn_fqname = self.id_to_fq_name(self.network_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.get_ctrl_nodes(ri_fqname):
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.vip_ip,
                                                ri_name=':'.join(ri_fqname))
            if not routes:
                self.logger.warn('LB: ctrl node %s: vip %s not found in RI %s'
                                 %(ctrl_node, self.vip_ip, ri_fqname))
                return False
            match = False
            for route in routes:
                if route['label'] == exp_label:
                    match = True
            if match == False:
                self.logger.warn('LB: label(%s) doesnt match expected(%s)'
                                 %(route['label'], exp_label))
                return False
        self.logger.info('Verify VIP in control node is passed')
        return True

    @retry(6, 10)
    def verify_vip_not_in_control_node(self):
        vn_fqname = self.id_to_fq_name(self.network_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.vip_ip,
                                                ri_name=':'.join(ri_fqname))
            if routes:
                self.logger.warn('ctrl node %s: vip %s not deleted in RI %s'
                                 %(ctrl_node, self.vip_ip, ri_fqname))
                return False
        self.logger.info('ctrl node %s: vip %s deleted in RI %s'
                                 %(ctrl_node, self.vip_ip, ri_fqname))
        return True

    @retry(6, 10)
    def verify_fip_in_control_node(self):
        exp_label = self.get_vip_label()
        if not exp_label:
            self.logger.warn('LB: Unable to fetch vip label')
            return False
        vn_fqname = self.id_to_fq_name(self.fip_net_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.get_ctrl_nodes(ri_fqname):
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.fip_ip,
                                                ri_name=':'.join(ri_fqname))
            if not routes:
                self.logger.warn('LB: ctrl node %s: fip %s not found in RI %s'
                                 %(ctrl_node, self.fip_ip, ri_fqname))
                return False
            match = False
            for route in routes:
                if route['label'] == exp_label:
                    match = True
            if match == False:
                self.logger.warn('LB: label(%s) doesnt match expected(%s)'
                                 %(route['label'], exp_label))
                return False
        self.logger.info('Verify FIP in control node is passed')
        return True

    @retry(6, 10)
    def verify_fip_not_in_control_node(self):
        vn_fqname = self.id_to_fq_name(self.fip_net_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.fip_ip,
                                                ri_name=':'.join(ri_fqname))
            if routes:
                self.logger.warn('ctrl node %s: fip %s not deleted in RI %s'
                                 %(ctrl_node, self.fip_ip, ri_fqname))
                return False
        self.logger.info('ctrl node %s: fip %s deleted in RI %s'
                                 %(ctrl_node, self.fip_ip, ri_fqname))
        return True

mappings = {'ROUND_ROBIN': 'roundrobin',
            'SOURCE_IP': 'source',
            'LEAST_CONNECTIONS': 'leastconn',
           }
class LBaasV2Fixture(LBBaseFixture):

    '''Fixture to handle Listener and its children objects
       Optionally can create Loadbalancer object

    Optional:
     lb_name or lb_uuid must be specified
     To create loadbalancer object please specify network_id too
    :param lb_name : name of the Loadbalancer
    :param lb_uuid : UUID of the Loadbalancer
    :param network_id : uuid of the network on which Loadbalancer belongs to
    :param vip_ip : VIP address of the Loadbalancer
    :param fip_id : UUID of FloatingIP object
    :param fip_net_id : UUID of the FloatingIP network object

    :param listener_name : name of the Listener (random name)
    :param listener_uuid : UUID of the Listener
    :param vip_port : L4 port number
    :param vip_protocol : Protocol one of HTTP, TCP or HTTPS
    :param pool_name : Name of the Pool (default: random name)
    :param pool_port : L4 port number of members
    :param pool_protocol : Protocol one of HTTP, TCP or HTTPS
    :param pool_algorithm : LB method (ROUND_ROBIN,LEAST_CONNECTIONS,SOURCE_IP)
    :param members: dict of list of members vm_ids or vmi_ids or address
                    {'vmis': ['...', '...'], 'vms': ['...'], 'address': ['...']}
    :param hm_probe_type : Health monitor probe type (PING,TCP,HTTP,HTTPS)
    :param hm_delay : Health monitor - delay in secs between probes
    :param hm_max_retries : Health monitor - max no of retries
    :param hm_timeout : Health monitor - timeout for each probe, must be < delay

    Inherited optional parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1

    '''

    def __init__(self, **kwargs):
        super(LBaasV2Fixture, self).__init__(self, **kwargs)
        self.lb_name = kwargs.get('lb_name', None)
        self.lb_uuid = kwargs.get('lb_uuid', None)
        self.network_id = kwargs.get('network_id', None)
        self.vip_ip = kwargs.get('vip_ip', None)
        self.fip_id = kwargs.get('fip_id', None)
        self.fip_net_id = kwargs.get('fip_net_id', None)
        if not self.lb_uuid and not (self.lb_name and self.network_id):
            raise Exception('LB UUID or LB name and network_id is reqd')
        self.listener_name = kwargs.get('listener_name',
                                        get_random_name('Listener'))
        self.listener_uuid = kwargs.get('listener_uuid', None)
        self.vip_port = kwargs.get('vip_port', 80)
        self.vip_protocol = kwargs.get('vip_protocol', 'HTTP')
        self.pool_name = kwargs.get('pool_name', get_random_name('Pool'))
        self.pool_port = kwargs.get('pool_port', 80)
        self.pool_protocol = kwargs.get('pool_protocol', 'HTTP')
        self.pool_algorithm = kwargs.get('pool_algorithm', 'ROUND_ROBIN')
        self.members = kwargs.get('members', dict())
        self.hm_probe_type = kwargs.get('hm_probe_type', None)
        self.hm_max_retries = kwargs.get('hm_max_retries', '5')
        self.hm_delay = kwargs.get('hm_delay', '5')
        self.hm_timeout = kwargs.get('hm_timeout', '5')
        self.pool_uuid = None
        self.member_ips = list()
        self.member_ids = list()
        self.member_weight = list()
        self.deleted_member_ids = list()
        self.hmon_id = None
        self.already_present = False

    def setUp(self):
        super(LBaasV2Fixture, self).setUp()
        self.create()

    def cleanUp(self):
        if (self.already_present or self.inputs.fixture_cleanup == 'no')\
           and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Load Balancer %s :'
                              %(self.fq_name))
        else:
            self.delete()
            super(LBaasV2Fixture, self).cleanUp()

    def get_network_handle(self):
        return self.get_neutron_handle()

    @property
    def network_h(self):
        if not getattr(self, '_network_h', None):
            self._network_h = self.get_network_handle()
        return self._network_h

    def read(self):
        self.logger.debug('Fetching info about listener %s'%self.listener_uuid)
        obj = self.network_h.get_listener(self.listener_uuid)
        if not obj:
            raise Exception('listener with id %s not found'%self.listener_uuid)
        self.listener_name = obj.get('name', None)
        self.vip_protocol = obj.get('protocol', None)
        self.vip_port = obj.get('protocol_port', None)
        pools = self.network_h.list_lbaas_pools(listeners=self.listener_uuid)
        pool_obj = pools[0] if pools else None
        if pool_obj:
            self.pool_uuid = pool_obj['id']
            self.pool_name = pool_obj['name']
            self.lb_method = pool_obj['lb_algorithm']
            self.pool_protocol = pool_obj['protocol']
            self.member_ids = [x['id'] for x in pool_obj.get('members', [])]
            self.member_ips = [self.network_h.get_lbaas_member(x,
                               self.pool_uuid)['address']
                               for x in self.member_ids]
            self.hmon_id = pool_obj.get('healthmonitor_id', None)
            if self.hmon_id:
                hmon_obj = self.network_h.get_health_monitor(self.hmon_id)
                self.hm_delay = hmon_obj['delay']
                self.hm_probe_type = hmon_obj['type']
                self.hm_max_retries = hmon_obj['max_retries']
                self.hm_timeout = hmon_obj['timeout']

    def create(self):
        if not self.listener_uuid:
            obj = self.network_h.list_listeners(name=self.listener_name)
            self.listener_uuid = obj[0]['id'] if obj else None
        if self.listener_uuid:
            self.already_present = True
        else:
            obj = self.network_h.create_listener(self.lb_uuid,
                                                 self.vip_protocol,
                                                 self.vip_port,
                                                 self.listener_name)
            self.listener_uuid = obj['id']
            if self.listener_uuid:
                self.listener_active = True
        self.read()

        if not self.pool_uuid:
            self.create_pool()

        if self.members:
            for vmi in self.members.get('vmis', []):
                self.create_member(vmi=vmi)
            for vm in self.members.get('vms', []):
                self.create_member(vm=vm)
            for address in self.members.get('address', []):
                self.create_member(address=address)

        if not self.hmon_id and self.hm_probe_type:
            self.create_hmon(self.hm_probe_type, self.hm_delay, self.hm_max_retries, self.hm_timeout)

    def create_pool(self):
        self.pool_active = False
        pool_obj = self.network_h.create_lbaas_pool(
                                  self.listener_uuid,
                                  self.pool_protocol,
                                  self.pool_algorithm,
                                  self.pool_name)
        self.pool_uuid = pool_obj['id']
        if self.pool_uuid:
            self.pool_active = True
        return self.pool_uuid

    def delete_pool(self):
        if self.pool_uuid:
            self.network_h.delete_lbaas_pool(self.pool_uuid)
            self.pool_active = False
            self.pool_uuid = None

    def create_member(self, address=None, vmi=None,
                      vm=None, port=None, network_id=None, weight=1):
        port = port or self.pool_port
        network_id = network_id or self.network_id
        if vm:
            vm_obj = self.connections.orch.get_vm_by_id(vm)
            address = self.connections.orch.get_vm_ip(vm_obj)[0]
        if vmi:
            address = self.network_h.get_port_ips(vmi)[0]
        if not port:
            raise Exception('Protocol port is not defined')
        if address not in self.member_ips:
            self.logger.info('Creating LB Member %s'%address)
            obj = self.network_h.create_lbaas_member(address, port,
                                                     self.pool_uuid,
                                                     network_id=network_id,
                                                     weight=weight)
            self.member_ids.append(obj.get('id'))
            self.member_ips.append(address)
            self.member_weight.append(weight)
            self.logger.info('Created LB Member with UUID,%s'%obj.get('id'))
            return obj.get('id')
        else:
            self.logger.info('Member , %s,  already exists for the pool %s'%(address, self.pool_uuid))

    def delete_member(self, member_id=None, address=None, vmi=None, vm=None):
        if not member_id:
            if vmi:
                address = self.network_h.get_port_ips(vmi)[0]
            if vm:
                vm_obj = self.connections.orch.get_vm_by_id(vm)
                address = self.connections.orch.get_vm_ip(vm_obj)[0]
            member_ids = [x['id'] for x in self.network_h.list_lbaas_members(
                                  self.pool_uuid, address=address, fields='id')]
            member_id = list(set(member_ids) & set(self.member_ids))[0]
        else:
            address = self.network_h.get_lbaas_member(member_id,
                      self.pool_uuid, fields='address')['address']
        self.logger.info('Deleting LB Member %s'%address)
        self.network_h.delete_lbaas_member(member_id, self.pool_uuid)
        self.deleted_member_ids.append(member_id)
        self.member_ids.remove(member_id)
        self.member_ips.remove(address)

    def update_member(self, member_id, **kwargs):
        weight = kwargs.get('weight', None)
        port = kwargs.get('port', None)
        admin_state = kwargs.get('admin_state', None)
        mem_obj = self.network_h.update_lbaas_member(
            member_id, self.pool_uuid, port=port, weight=weight, admin_state=admin_state)
        if weight:
            mem_idx = self.member_ids.index(member_id)
            self.member_weight[mem_idx] = weight

    def create_hmon(self, probe_type, delay, max_retries, timeout):
        hmon_obj = self.network_h.create_lbaas_healthmonitor(
                                  self.pool_uuid, delay, max_retries,
                                  probe_type, timeout)
        self.hmon_id = hmon_obj['id']
        return self.hmon_id

    def delete_hmon(self):
        if self.hmon_id:
            self.network_h.delete_lbaas_healthmonitor(self.hmon_id)
            self.hmon_id = None

    def update_hmon(self, **kwargs):
        delay = kwargs.get('delay', None)
        max_retries = kwargs.get('max_retries', None)
        timeout = kwargs.get('timeout', None)
        hmon_update_obj = self.network_h.update_lbaas_healthmonitor(
            self.hmon_id, delay=delay, max_retries=max_retries, timeout=timeout)
        if delay:
            self.hm_delay = delay
        if max_retries:
            self.hm_max_retries = max_retries
        if timeout:
            self.hm_timeout=timeout

    def delete(self):
        for member_id in list(self.member_ids):
            self.delete_member(member_id)
        self.delete_hmon()
        self.delete_pool()
        if self.listener_uuid:
            self.network_h.delete_listener(self.listener_uuid)
            self.listener_uuid = None
        self.listener_active = False
        if getattr(self, 'verify_lb_is_run', None):
            assert self.verify_on_cleanup(), "Verify on cleanup failed"

    def verify_on_setup(self):
        if not super(LBaasV2Fixture, self).verify_on_setup():
            return False
        if not self.verify_haproxy_configs_on_setup():
            return False
        return True

    @retry(3, 5)
    def verify_haproxy_configs_on_setup(self):
        if not self._verify_haproxy_configs()[0]:
            self.logger.warn("Verify haproxy config file on setup failed")
            return False
        self.logger.info("Verify haproxy config file on setup passed")
        return True

    @retry(3, 5)
    def verify_haproxy_configs_on_cleanup(self):
        retval = self._verify_haproxy_configs()
        if not self.lb_present:
            if not retval[0] and retval[1] == "HAPROXY_NOT_EXIST":
                self.logger.info("haproxy config file updated")
                return True
        if not self.listener_active:
            if not retval[0] and retval[1] == "FRONTEND_NOT_EXIST":
                self.logger.info("frontend for LISTENER %s, removed from haproxy conf after listener delete" %self.listener_uuid)
                return True
        if not self.pool_active:
            if not retval[0] and retval[1] == "BACKEND_NOT_EXIST":
                self.logger.info("backend for pool %s, removed from haproxy conf after pool delete" %self.pool_uuid)
                return True
        self.logger.warn("Verify haproxy config file on cleanup failed")
        return False

    def _verify_haproxy_configs(self):
        retval = False
        conf_filename = '/var/lib/contrail/loadbalancer/haproxy/%s/haproxy.conf'%self.lb_uuid
        for host in [self.get_active_vrouter()] + list(self.get_standby_vrouter() or []):
            username = self.inputs.host_data[host]['username']
            password = self.inputs.host_data[host]['password']
            haproxy_dict = parse_haproxy(conf_filename, host, username, password)
            if haproxy_dict == None:
                return (False, "HAPROXY_NOT_EXIST")
            for frontend in haproxy_dict['frontends'] or []:
                if self.listener_uuid == frontend['uuid'] and \
                   self.vip_ip == frontend['address'] and \
                   self.vip_protocol.lower() == frontend['protocol'] and \
                   self.vip_port == frontend['port']:
                   if self.pool_uuid:
                       if self.pool_uuid != frontend['backend']:
                           break
                   retval = True
                   break
            if retval == False:
                self.logger.debug("frontend not found in haproxy config file")
                return (False, "FRONTEND_NOT_EXIST")
            retval = False
            for backend in haproxy_dict['backends'] or []:
                if self.pool_uuid == backend['uuid'] and \
                    self.pool_protocol.lower() == backend['protocol']:
                    if mappings[self.pool_algorithm] != backend['lb_method']:
                        break
                    act_mem_list = [(member['uuid'], member['address'], member['weight'])
                                    for member in backend['members']]
                    exp_mem_list = zip(self.member_ids, self.member_ips, self.member_weight)
                    if sorted(act_mem_list) != sorted(exp_mem_list):
                        break
                    if self.hmon_id and (str(self.hm_timeout) != backend['timeout'] or
                        [(member['delay'], member['retries']) for member in backend['members'] if member['delay'] != self.hm_delay or member['retries'] != self.hm_max_retries]):
                        self.logger.info("healthmonitor values didn't match, %s" %backend)
                        break
                    retval = True
                    break
            if retval == False:
                self.logger.debug("backend not found in haproxy config file")
                return (False, "BACKEND_NOT_EXIST")
        return (True, "SUCCESS")

    def verify_on_cleanup(self):
        if self.verify_haproxy_configs_on_cleanup() == False:
            self.logger.error('verify_haproxy_configs_on_cleanup failed')
            return False
        return True
        #return super(LBaasV2Fixture, self).verify_on_cleanup()

def setup_test_infra():
    import logging
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('event')
    logger.setUp()
    mylogger = logger.logger
    from common.connections import ContrailConnections
    connections = ContrailConnections(logger=mylogger)
    return connections

def main():
    import sys
    from vn_test import VNFixture
    from vm_test import VMFixture
#    sys.settrace(tracefunc)
#    obj = LBaasFixture(api_type='neutron', name='LB', connections=setup_test_infra(), network_id='4b39a2bd-4528-40e8-b848-28084e59c944', members={'vms': ['a72ad607-f1ca-44f2-b31e-e825a3f2d408'], 'address': ['192.168.1.10']}, vip_net_id='4b39a2bd-4528-40e8-b848-28084e59c944', protocol='TCP', port='22', healthmonitors=[{'delay':5, 'timeout':5, 'max_retries':5, 'probe_type':'PING'}])
    conn = setup_test_infra()
    vnfix = VNFixture(connections=conn, vn_name='admin-33688095')
    vnfix.setUp()
    fip_fix = VNFixture(connections=conn, router_external=True, vn_name='fip-vn')
    fip_fix.setUp()
    subnet = vnfix.get_cidrs()[0]
    vm_fix = VMFixture(connections=conn, vn_obj=vnfix.obj, vm_name='member-vm')
    vm_fix.setUp()
    obj = LBaasV2Fixture(lb_name='LB-Test', connections=conn, network_id=vnfix.uuid,
                         fip_net_id=fip_fix.uuid, listener_name='Listener-Test', vip_port='80',
                         vip_protocol='HTTP', pool_name='Pool-Test', pool_port='80', pool_protocol='HTTP',
                         pool_algorithm='ROUND_ROBIN', members={'vms': [vm_fix.vm_id]},
                         hm_delay=5, hm_timeout=5, hm_max_retries=5, hm_probe_type='PING',
                        )
    obj.setUp()
    import pdb; pdb.set_trace()
    obj.verify_on_setup()
    obj.cleanUp()
    exit()
    import pdb; pdb.set_trace()
#    obj = LBaasFixture(api_type='neutron', uuid='58e5fb2c-ec47-4eb8-b4bf-9c66b0473f78', connections=setup_test_infra())
    obj.verify_on_setup()
    obj.delete_custom_attr('max_sess_rate')
    obj.add_custom_attr('client_timeout', 20000)
    obj.delete_custom_attr('server_timeout')
    obj.add_custom_attr('max_sess_rate', 20000)
    obj.delete_custom_attr('rate_limit_sessions')
    obj.add_custom_attr('rate_limit_sessions', 20)
    obj.delete_custom_attr('max_conn')
    obj.add_custom_attr('max_conn', 20)
    obj.delete_custom_attr('http_server_close')
    obj.add_custom_attr('http_server_close', "False")
    obj.verify_on_setup()
    obj.create_fip_on_vip()
    obj.verify_on_setup()
    obj.delete_fip_on_vip()
    obj.verify_on_setup()
    obj.delete_vip()
    obj.verify_on_setup()
    obj.check_and_create_vip()
    obj.verify_on_setup()
    obj.delete_member(address=obj.member_ips[1])
    obj.verify_on_setup()
    obj.create_member(address=get_random_ip(subnet))
    obj.verify_on_setup()
    obj.delete_hmon(obj.hmons.keys()[0])
    obj.verify_on_setup()
    obj.create_hmon({'delay': 5, 'max_retries': 5, 'probe_type': 'PING', 'timeout': 10})
    obj.verify_on_setup()
    obj.cleanUp()
    vm_fix.cleanUp()
    vnfix.cleanUp()
    vip_fix.cleanUp()
    fip_fix.cleanUp()

if __name__ == "__main__":
    main()
