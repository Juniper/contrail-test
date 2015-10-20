import vnc_api_test
from tcutils.util import get_random_name, retry

class LBaasFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle LBaas object
    
    Optional:
    :param name : name of the LBaas Pool (random name)
    :param uuid : UUID of the LBaas Pool
    :param network_id : uuid of the network on which pool belongs to
    :param members: dict of list of members vmi_ids or ip address
                    {'vmi': ['...', '...'], 'address': ['...'], 'vm': [...]}
    :param api_type     : one of 'neutron'(default) or 'contrail'
    :param lb_method : LB method (ROUND_ROBIN,LEAST_CONNECTIONS,SOURCE_IP)
    :param protocol : Protocol one of HTTP, TCP or HTTPS
    :param port : L4 Port number
    :param vip_name : VIP name (vip-$(LB_Name))
    :param vip_net_id : vip network id, mandatory to create vip
    :param vip_protocol : Protocol one of HTTP, TCP or HTTPS
    :param vip_port : L4 Port number
    :param probe_type : Health monitor probe type (PING,TCP,HTTP,HTTPS)
    :param delay : Health monitor - delay in secs between probes
    :param retries : Health monitor - max no of retries
    :param timeout : Health monitor - timeout for each probe, must be < delay

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
        super(LBaasFixture, self).__init__(self, **kwargs)
        self.name = kwargs.get('name', get_random_name('LB'))
        self.uuid = kwargs.get('uuid', None)
        self.network_id = kwargs.get('network_id', None)
        self.lb_method = kwargs.get('lb_method', 'ROUND_ROBIN')
        self.members = kwargs.get('members', None)
        self.protocol = kwargs.get('protocol', 'HTTP')
        self.port = kwargs.get('port', None)
        self.vip_net_id = kwargs.get('vip_net_id', None)
        self.vip_name = kwargs.get('vip_name', 'vip-'+self.name)
        self.vip_protocol = kwargs.get('vip_protocol', self.protocol)
        self.vip_port = kwargs.get('vip_port', self.port)
        self.probe_type = kwargs.get('probe_type', None)
        self.delay = kwargs.get('delay', None)
        self.retries = kwargs.get('retries', None)
        self.timeout = kwargs.get('timeout', None)
        self.api_type = kwargs.get('api_type', 'neutron')
        self.already_present = False
        self.member_ips = list()
        self.member_ids = list()
        self.vip_id = None
        self.vip_ip = None

        # temporary place till vnc_api_test is re-done
        super(LBaasFixture, self).setUp()
        self.network_h = self.get_network_handle()
        self.vnc_api_h = self.get_handle()

        if self.uuid:
            self.read(self.uuid)
        self.parent_fq_name = [self.domain, self.project_name]
        self.fq_name = self.parent_fq_name + [self.name]
        self.parent_type = 'project'

    def setUp(self):
        super(LBaasFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(LBaasFixture, self).cleanUp()
        if (self.already_present or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.debug('Skipping deletion of Load Balancer %s :'
                              %(self.fq_name))
        else:
            self.delete()

    def get_network_handle(self):
        if self.api_type == 'contrail':
            return self.get_handle()
        else:
            return self.get_neutron_handle()

    def read(self, uuid):
        self.logger.debug('Fetching info about Load Balancer Pool %s'%uuid)
        self.obj= self.network_h.get_lb_pool(uuid)
        if not self.obj:
            raise Exception('load balancer pool with id %s not found'%uuid)
        self.uuid = self.obj.get('id', None) or getattr(self.obj, 'uuid', None)
        self.name = self.obj.get('name', None) or getattr(self.obj, 'name',None)
        self.protocol = self.obj.get('protocol', None)
        self.lb_method = self.obj.get('lb_method', None)
        self.network_id = self.network_h.get_vn_of_subnet(\
                          self.obj.get('subnet_id', None))
        self.vip_id = self.obj.get('vip_id', None)
        self.vip_ip = None
        if self.vip_id:
            vip_obj = self.network_h.show_vip(self.vip_id)
            self.vip_ip = vip_obj.get('address', None)
            self.vip_net_id = self.network_h.get_vn_of_subnet(\
                              vip_obj.get('subnet_id', None))
            self.vip_port = vip_obj.get('protocol_port', None)
            self.vip_protocol = vip_obj.get('protocol', None)
            self.vip_port_id = vip_obj.get('port_id', None)

        self.member_ids = self.obj.get('members', [])
        self.member_ips = [self.network_h.show_lb_member(x)['address']
                                                for x in self.member_ids]
        if self.member_ids:
            self.port = self.network_h.show_lb_member(
                             self.member_ids[0])['protocol_port']
        self.health_monitors = self.obj.get('health_monitors', [])
        if self.health_monitors:
            hm_obj = self.network_h.show_lb_member(self.health_monitors[0])
            self.probe_type = hm_obj.get('type', None)
            self.retries = hm_obj.get('max_retries', None)
            self.delay = hm_obj.get('delay', None)
            self.timeout = hm_obj.get('timeout', None)
        self.logger.debug('LB: %s, members: %s, vip: %s, protocol %s, port %s'
                         %(self.name, self.member_ips, self.vip_ip,
                           self.protocol, self.port))

    def create(self):
        try:
            self.obj = self.network_h.get_lb_pool(name=self.name)
            self.uuid = self.obj.get('id')
            self.read(self.uuid)
            self.already_present = True
            self.logger.debug('Load Balancer is already present')
        except:
            self.logger.info('Creating Load Balancer %s'%self.name)
            self.obj = self.network_h.create_lb_pool(self.name,
                                      lb_method=self.lb_method,
                                      protocol=self.protocol,
                                      network_id=self.network_id)
        self.uuid = self.obj.get('id', None) or getattr(self, 'id', None)
        if self.vip_net_id and not self.vip_id:
            self.check_and_create_vip()
        if self.members:
            for vmi in self.members.get('vmis', []):
                self.create_member(vmi=vmi)
            for vm in self.members.get('vms', []):
                self.create_member(vm=vm)
            for address in self.members.get('address', []):
                self.create_member(address=address)
        self.logger.debug('LoadBalancer: %s, members: %s, vip: %s'%(self.name,
                                   self.member_ips, self.vip_ip))

    def create_member(self, address=None, vmi=None, vm=None, port=None):
        port = port or self.port
        if vm:
            vm_obj = self.connections.orch.get_vm_by_id(vm)
            address = self.connections.orch.get_vm_ip(vm_obj)[0]
        if vmi:
            address = self.network_h.get_port_ips(vmi)[0]
        if not port:
            raise Exception('Protocol port is not defined')
        if address not in self.member_ips:
            self.logger.info('Creating LB Member %s'%address)
            obj = self.network_h.create_lb_member(address, port, self.uuid)
            self.member_ids.append(obj.get('id'))
            self.member_ips.append(address)
            return obj.get('id')

    def delete_member(self, member_id=None, address=None, vmi=None, vm=None):
        if not member_id:
            if vmi:
                address = self.network_h.get_port_ips(vmi)[0]
            if vm:
                vm_obj = self.connections.orch.get_vm_by_id(vm)
                address = self.connections.orch.get_vm_ip(vm_obj)[0]
            member_ids = self.network_h.list_lb_members(address=address,
                                                        fields='id')['id']
            member_id = list(set(member_ids) & set(self.member_ids))[0]
        else:
            address = self.network_h.show_lb_member(member_id,
                                     fields='address')['address']
        self.logger.info('Deleting LB Member %s'%address)
        self.network_h.delete_lb_member(member_id)
        self.member_ids.remove(member_id)
        self.member_ips.remove(address)

    def check_and_create_vip(self):
        try:
            obj = self.network_h.show_vip(name=self.vip_name)
            self.vip_id = obj.get('id')
            self.vip_ip = obj.get('address')
            self.vip_port_id = obj.get('port_id', None)
            self.already_present = True
            self.logger.debug('VIP is already present')
        except:
            self.logger.info('Creating VIP %s'%self.name)
            self.vip_id = self.create_vip(self.vip_name,
                                      protocol=self.vip_protocol,
                                      port=self.vip_port,
                                      network_id=self.vip_net_id)
        return self.vip_id

    def create_vip(self, name=None, protocol=None, port=None, network_id=None):
        name = name or self.vip_name
        protocol = protocol or self.vip_protocol
        port = port or self.vip_port
        net_id = network_id or self.vip_net_id
        obj = self.network_h.create_vip(name, protocol, port, self.uuid,
                                        network_id=network_id)
        self.vip_id = obj.get('id')
        self.vip_ip = obj.get('address')
        self.vip_port_id = obj.get('port_id', None)
        self.logger.debug('Created vip(%s) %s' %(self.vip_id, self.vip_ip))
        return self.vip_id

    def delete_vip(self, verify=False):
        self.logger.info('Deleting vip(%s) %s' %(self.vip_id, self.vip_ip))
        self.network_h.delete_vip(self.vip_id)
        if getattr(self, 'verify_is_run', None) or verify:
            assert self.verify_vip_not_in_agent()
            assert self.verify_vip_not_in_control_node()
        self.vip_ip = None
        self.vip_id = None
        self.vip_port_id = None
        self.active_vr = None
        self.standby_vr = None
        self.active_instance = None
        self.standby_instance = None

    def delete(self):
        self.logger.info('Deleting LoadBalancer %s(%s)'%(self.name, self.uuid))
        self.member_ids_backup = self.member_ids
        for member_id in list(self.member_ids):
            self.delete_member(member_id)
        if self.vip_id:
            self.delete_vip()
        self.network_h.delete_lb_pool(self.uuid)
        if getattr(self, 'verify_is_run', None):
            assert self.verify_on_cleanup()
        self.uuid = None

    def verify_on_setup(self):
        assert self.verify_on_api_server()
        if self.vip_id:
            assert self.verify_on_agent()
            assert self.verify_on_control_node()
        self.logger.info('LoadBalancer(%s): verify_on_setup passed'%self.uuid)
        self.verify_is_run = True
        return True

    def verify_on_cleanup(self):
        assert self.verify_not_in_api_server()
        self.logger.info('LoadBalancer(%s): verify_on_cleanup passed'%self.uuid)
        return True

    def verify_not_in_api_server(self):
        assert self.verify_pool_not_in_api_server()
        assert self.verify_member_not_in_api_server()
        assert self.verify_vip_not_in_api_server()
        return True

    @retry(delay=3, tries=10)
    def verify_pool_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        pool = self.api_h.get_lb_pool(self.uuid)
        if pool:
            self.logger.warn("Loadbalancer pool %s still present in API"
                             " server even after pool delete" %(self.uuid))
            return False
        self.logger.debug(
            "Load Balancer pool %s got deleted in API server" %(self.uuid))
        return True

    @retry(delay=3, tries=10)
    def verify_member_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for member_id in self.member_ids_backup:
            member = self.api_h.get_lb_member(member_id)
            if member:
                self.logger.warn("LB member %s still present in API server"
                                 " even after member delete" % (member_id))
                return False
            self.logger.debug(
                "LB member %s got deleted in API server" % (member_id))
        return True

    @retry(delay=3, tries=10)
    def verify_vip_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        vip = self.api_h.get_lb_vip(self.vip_id)
        if vip:
            self.logger.warn("LB VIP %s still present in API server"
                             " even after vip delete" % (self.vip_id))
            return False
        self.logger.debug(
            "LB vip %s got deleted in API server" % (self.vip_id))
        return True

    def verify_on_api_server(self):
        assert self.verify_lb_pool_in_api_server()
        if self.member_ids:
            assert self.verify_member_in_api_server()
        if self.vip_id:
            assert self.verify_vip_in_api_server()
            assert self.verify_si_launched()
        return True

    @retry(delay=3, tries=10)
    def verify_lb_pool_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        pool = self.api_h.get_lb_pool(self.uuid, refresh=True)
        if not pool:
            self.logger.warn("LB %s not found in api server" % (self.uuid))
            return False
        if self.member_ids:
            if sorted(self.member_ids) != sorted(pool.members()):
                self.logger.warn("LB %s members doesnt match, expected %s"
                                 " got %s"%(self.uuid, self.member_ids,
                                            sorted(pool.members())))
                return False
        if self.vip_id:
            if self.vip_id != pool.vip():
                self.logger.warn("LB %s VIP id doesnt match, expected %s" 
                                 " got %s"%(self.uuid, self.vip_id, pool.vip()))
                return False
        prop = pool.properties()
        if self.protocol != prop['protocol']:
            self.logger.warn("LB %s protocol doesnt match, expected %s got %s"
                            %(self.uuid, self.protocol, prop['protocol']))
            return False
        if self.lb_method != prop['loadbalancer_method']:
            self.logger.warn("LB %s lb_method doesnt match, expected %s got %s"
                            %(self.uuid, self.lb_method,
                              prop['loadbalancer_method']))
            return False
        if self.network_id != self.network_h.get_vn_of_subnet(
                                           prop['subnet_id']):
            self.logger.warn("LB %s pool subnet ids doesnt match")
            return False
        self.logger.debug("LB(%s) got created in api server"% (self.uuid))
        return True

    @retry(delay=3, tries=10)
    def verify_vip_in_api_server(self):
        vip = self.api_h.get_lb_vip(self.vip_id)
        if not vip:
            self.logger.warn("LB Vip %s not found in api server" %(self.vip_id))
            return False
        if vip.vmi() != self.vip_port_id:
            self.logger.warn("vip(%s) port ids dont match, expected %s got %s"
                             %(self.vip_id, self.vip_port_id, vip.vmi()))
            return False
        if vip.ip() != self.vip_ip:
            self.logger.warn("vip(%s) address dont match, expected %s got %s"
                             %(self.vip_id, self.vip_ip, vip.ip()))
            return False
        self.logger.info("LB VIP %s got created in api server" %(self.vip_id))
        return True

    @retry(delay=3, tries=10)
    def verify_member_in_api_server(self):
        for member_id in self.member_ids:
            member = self.api_h.get_lb_member(member_id)
            if not member:
                self.logger.warn("LB member %s not found" %(member_id))
                return False
            if member.ip() not in self.member_ips:
                self.logger.warn("member %s ip dont match, expected one of %s"
                             "got %s"%(member_id, self.member_ips, member.ip()))
                return False
            self.logger.info("LB member %s created successfully" % (member_id))
        return True

    @retry(6, 10)
    def verify_si_launched(self, refresh=False):
        svc_mon_h = self.connections.get_svc_mon_h(refresh)
        if svc_mon_h.get_service_instance(name=self.get_si_name(),
                                          refresh=True).is_launched():
            self.logger.debug('Load Balancer: SI got launched')
            return True
        self.logger.warn('LB(%s): SI status is not active in svc-mon'%self.uuid)
        return False

    def get_si_name(self):
        return self.uuid

    def get_si(self, refresh=False):
        if not getattr(self, 'si_uuid', None) or refresh:
            self.si_uuid = None
            self.api_h = self.connections.api_server_inspect
            pool = self.api_h.get_lb_pool(self.uuid, refresh=refresh)
            if pool:
                self.si_uuid = pool.si()
            self.logger.debug('LB %s: SI uuid is %s'%(self.uuid, self.si_uuid))
        return self.si_uuid

    def get_vms(self):
        self.api_h = self.connections.api_server_inspect
        return self.api_h.get_cs_si_by_id(self.get_si(), True).get_vms()

    def get_active_instance(self, refresh=False):
        if not getattr(self, 'active_vm', None) or refresh:
            self.active_vm = None; self.standby_vm = None
            self.api_h = self.connections.api_server_inspect
            for vm_id in self.get_vms():
                vmis = self.api_h.get_cs_vmi_of_vm(vm_id, refresh=True)
                pref = vmis[0].properties('local_preference')
                if pref == 200:
                   self.active_vm = vm_id
                else:
                   self.standby_vm = vm_id
            if not self.active_vm:
                self.logger.warn('Unable to get active vm for LR %s'%self.uuid)
        return self.active_vm

    def get_standby_instance(self):
        if not getattr(self, 'standby_vm', None):
            self.get_active_instance(refresh=True)
        return self.standby_vm

    def get_active_vrouter(self, refresh=False):
        if not getattr(self, 'active_vr', None) or refresh:
            svc_mon_h = self.connections.get_svc_mon_h(refresh)
            try:
                self.active_vr = self.inputs.get_host_ip(
                                 svc_mon_h.get_service_instance(
                                           name=self.get_si_name(),
                                           refresh=refresh).active_vrouter())
                if self.active_vr == 'None':
                    self.active_vr = None
            except:
                self.logger.warn('Fail to get active vrouter for active lbaas')
                self.active_vr = None
        return self.active_vr

    def get_standby_vrouter(self, refresh=False):
        if not getattr(self, 'standby_vr', None) or refresh:
            svc_mon_h = self.connections.get_svc_mon_h(refresh)
            try:
                self.standby_vr = self.inputs.get_host_ip(
                                  svc_mon_h.get_service_instance(
                                            name=self.get_si_name(),
                                            refresh=refresh).standby_vrouter())
                if self.standby_vr == 'None':
                    self.standby_vr = None
            except:
                self.logger.warn('Fail to get standby vrouter for active lbaas')
                self.standby_vr = None
        return self.standby_vr

    def get_vip_label(self, refresh=False):
        if not getattr(self, 'label', None) or refresh:
            self.label = None
            vm_id = self.get_active_instance()
            active_vr = self.get_active_vrouter()
            if not (active_vr and vm_id):
                self.logger.warn('LB: Unable to fetch either of '
                                 'active vm/vrouter info')
                return None
            inspect_h = self.connections.agent_inspect[active_vr]
            vmis = inspect_h.get_vna_tap_interface_by_vm(vm_id)
            if vmis:
                self.label = [vmi['label'] for vmi in vmis
                              if vmi['ip_addr'] == self.vip_ip][0]
            if not self.label:
                self.logger.warn('LR: Unable to fetch label of vip intf')
        return self.label

    def get_active_controller(self):
        ''' Get the active contol node.
        '''
        if not getattr(self, 'control_node', None):
            self.control_node = None
            active_vr = self.get_active_vrouter()
            inspect_h = self.connections.agent_inspect[active_vr]
            agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes' \
                        and entry['state'] == 'Established':
                    self.control_node = entry['controller_ip']
                    break
            if not self.control_node:
                self.logger.error('Active controlloer is not found')
            self.control_node = self.inputs.get_host_ip(self.control_node)
        return self.control_node

    def get_ctrl_nodes(self, ri_name):
        rt_list = []
        peer_list = []
        ri = self.vnc_api_h.routing_instance_read(fq_name=ri_name)
        rt_list = [rt['to'][0] for rt in ri.get_route_target_refs()]
        ctrl_node = self.get_active_controller()
        cn_inspect = self.connections.cn_inspect[ctrl_node]
        peer_list.append(ctrl_node)
        for rt in rt_list:
            rt_group_entry = cn_inspect.get_cn_rtarget_group(rt)
            if rt_group_entry['peers_interested'] is not None:
                for peer in rt_group_entry['peers_interested']:
                    if peer in self.inputs.host_names:
                        peer = self.inputs.get_host_ip(peer)
                        peer_list.append(peer)
                    else:
                        self.logger.info('%s is not defined as a control node'
                                         ' in the topology' % peer)
        self.logger.debug('Interested control nodes %s'%peer_list)
        return list(set(peer_list))

    def verify_on_control_node(self):
        assert self.verfiy_vip_in_control_node()
        self.logger.debug('LB %s: vip %s: verify_on_control_node passed'
                          %(self.uuid, self.vip_id))
        return True

    @retry(6, 10)
    def verfiy_vip_in_control_node(self):
        exp_label = self.get_vip_label()
        if not exp_label:
            self.logger.warn('LB: Unable to fetch vip label')
            return False
        vn_fqname = self.id_to_fq_name(self.vip_net_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.get_ctrl_nodes(ri_fqname):
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.vip_ip,
                                                ri_name=':'.join(ri_fqname))
            if not routes:
                self.logger.warn('LB: ctrl node %s: vip %s not found in RI %s'
                                 %(ctrl_node, self.vip_ip, ri_fqname))
                return False
            for route in routes:
                if route['label'] != exp_label:
                    self.logger.warn('LB: label(%s) doesnt match expected(%s)'
                                     %(route['label'], exp_label))
                    return False
        return True

    @retry(6, 10)
    def verify_vip_not_in_control_node(self):
        vn_fqname = self.id_to_fq_name(self.vip_net_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix=self.vip_ip,
                                                ri_name=':'.join(ri_fqname))
            if routes:
                self.logger.warn('ctrl node %s: vip %s not deleted in RI %s'
                                 %(ctrl_node, self.vip_ip, ri_fqname))
                return False
        return True

    def verify_on_agent(self):
        assert self.verify_netns_instance_launched()
        assert self.verify_vip_in_agent()
        self.logger.debug('LB %s: vip %s: verify_on_agent passed'
                          %(self.uuid, self.vip_id))
        return True

    def is_instance_launched(self, vm_id, vrouter):
        if not vm_id or not vrouter:
            return False
        cmd_str = 'ip netns list | grep %s:%s'%(vm_id, self.uuid)
        output = self.inputs.run_cmd_on_server(vrouter, cmd_str)
        if not output:
            self.logger.debug('netns instance %s:%s not found'
                             %(vm_id, self.uuid))
            return False
        if len(output.strip().split('\n')) > 1:
            self.logger.debug('Multiple %s:%s netns instances found'
                             %(vm_id, self.uuid))
            return False
        cmd_str = 'ps ax | grep haproxy | grep %s' % self.uuid
        if not self.inputs.run_cmd_on_server(vrouter, cmd_str):
            self.logger.debug('haproxy not found for LB %s'%self.uuid)
            return False
        return True

    @retry(6, 10)
    def verify_netns_instance_launched(self):
        active_vr = self.get_active_vrouter()
        active_vm = self.get_active_instance()
        if not self.is_instance_launched(active_vm, active_vr):
            return False
        if len(self.inputs.compute_ips) > 1:
            standby_vr = self.get_standby_vrouter()
            standby_vm = self.get_standby_instance()
            if not self.is_instance_launched(standby_vm, standby_vr):
                return False
        return True

    @retry(6, 10)
    def verify_vip_in_agent(self):
        exp_label = self.get_vip_label()
        active_vr = self.get_active_vrouter()
        if not active_vr or not exp_label:
            self.logger.warn('LB(%s): unable to find active vr'%self.uuid)
            return False
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.vip_net_id))
        route = inspect_h.get_vna_active_route(ip=self.vip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if not route or exp_label != route['path_list'][0]['active_label']:
            self.logger.warn('LB: agent: label doesnt match for vip ip %s, '
                             'expected %s: actual %s'%(self.vip_ip,
                             exp_label, route['path_list'][0]['active_label']
                             if route else None))
            return False
        return True

    @retry(6, 10)
    def verify_vip_not_in_agent(self):
        active_vr = self.get_active_vrouter()
        if not active_vr:
            self.logger.warn('LB(%s): unable to find active vr'%self.uuid)
            return True
        inspect_h = self.connections.agent_inspect[active_vr]
        vn_fq_name = ':'.join(self.id_to_fq_name(self.vip_net_id))
        route = inspect_h.get_vna_active_route(ip=self.vip_ip,
                                               prefix='32',
                                               vn_fq_name=vn_fq_name)
        if route:
            self.logger.warn('LB: vip route %s still found in %s'
                             %(self.vip_ip, vn_fq_name))
            return False
        return True

    @retry(6, 10)
    def verify_netns_instance_deleted(self):
        active_vr = self.get_active_vrouter()
        active_vm = self.get_active_instance()
        assert not self.is_instance_launched(active_vm, active_vr)
        if len(self.inputs.compute_ips) > 1:
            standby_vr = self.get_standby_vrouter()
            standby_vm = self.get_standby_instance()
            assert not self.is_instance_launched(standby_vm, standby_vr)
        return True

def setup_test_infra():
    import logging
    from common.contrail_test_init import ContrailTestInit
    from common.connections import ContrailConnections
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('event')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit('./sanity_params.ini', logger=mylogger)
    inputs.setUp()
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

if __name__ == "__main__":
    obj = LBaasFixture(api_type='neutron', name='LB', connections=setup_test_infra(), network_id='4b39a2bd-4528-40e8-b848-28084e59c944', members={'vms': ['a72ad607-f1ca-44f2-b31e-e825a3f2d408'], 'address': ['192.168.1.10']}, vip_net_id='4b39a2bd-4528-40e8-b848-28084e59c944', protocol='TCP', port='22')
    obj.setUp()
#    obj = LBaasFixture(api_type='neutron', uuid='41a3d680-2b45-4dd3-8577-70e2bbe4193b', connections=setup_test_infra())
    obj.verify_on_setup()
    obj.cleanUp()
