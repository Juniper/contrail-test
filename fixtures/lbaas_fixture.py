import vnc_api_test
from compute_node_test import ComputeNodeFixture
from tcutils.util import get_random_name, retry

custom_attributes_dict = {
        'max_conn': 'maxconn',
        'max_conn_rate': 'maxconnrate',
        'max_sess_rate': 'maxsessrate',
        'max_ssl_conn': 'maxsslconn',
        'max_ssl_rate': 'maxsslrate',
        'ssl_ciphers': 'ssl-default-bind-ciphers',
        'tune_http_max_header': 'tune.http.maxhdr',
        'tune_ssl_max_record': 'tune.ssl.maxrecord',
        'server_timeout': 'timeout server',
        'client_timeout': 'timeout client',
        'connect_timeout': 'timeout connect',
        'http_server_close': 'option http-server-close',
        'rate_limit_sessions': 'rate-limit sessions',
}

class LBaasFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle LBaas object
    
    Optional:
    :param name : name of the LBaas Pool (random name)
    :param uuid : UUID of the LBaas Pool
    :param network_id : uuid of the network on which pool belongs to
    :param members: dict of list of members vmi_ids or ip address
                    {'vmis': ['...', '...'], 'address': ['...'], 'vms': ['...']}
    :param custom_attr  : dict of key value pairs (Check custom_attributes_dict
                          @ https://github.com/Juniper/contrail-controller/blob/master/src/vnsw/opencontrail-vrouter-netns/opencontrail_vrouter_netns/haproxy_validator.py
                          for supported KV pairs)
    :param api_type  : one of 'neutron'(default) or 'contrail'
    :param lb_method : LB method (ROUND_ROBIN,LEAST_CONNECTIONS,SOURCE_IP)
    :param protocol : Protocol one of HTTP, TCP or HTTPS
    :param port : L4 Port number
    :param vip_name : VIP name (vip-$(LB_Name))
    :param vip_net_id : vip network id, mandatory to create vip
    :param vip_protocol : Protocol one of HTTP, TCP or HTTPS
    :param vip_port : L4 Port number
    :param healthmonitors : List of dicts
        id : healthmonitor id in case its precreated
        or, the below set of keys
        probe_type : Health monitor probe type (PING,TCP,HTTP,HTTPS)
        delay : Health monitor - delay in secs between probes
        max_retries : Health monitor - max no of retries
        timeout : Health monitor - timeout for each probe, must be < delay
    :param fip_id : UUID of FloatingIP object
    :param fip_net_id : UUID of the FloatingIP network object

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
        self.healthmonitors = kwargs.get('healthmonitors', list())
        self.fip_id = kwargs.get('fip_id', None)
        self.fip_net_id = kwargs.get('fip_net_id', None)
        self.api_type = kwargs.get('api_type', 'neutron')
        self.custom_attr = kwargs.get('custom_attr', dict())
        self.already_present = False
        self.member_ips = list()
        self.member_ids = list()
        self.deleted_member_ids = list()
        self.is_vip_active = False
        self.is_fip_active = False
        self.vip_ip = None
        self.vip_id = None
        self.fip_id = None
        self.fip_ip = None
        self.hmons = dict()

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
        self.inputs.fixture_cleanup = 'force'
        if (self.already_present or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Load Balancer %s :'
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
        vip_id = self.obj.get('vip_id', None)
        if vip_id:
            self.vip_id = vip_id
            self.vip = self.network_h.show_vip(self.vip_id)
            self.vip_port = self.vip.get('protocol_port', None)
            self.vip_protocol = self.vip.get('protocol', None)
            self._populate_vars_from_vip_obj()
            fip = self.network_h.list_floatingips(port_id=self.vip_port_id)
            if fip:
                self.fip_id = fip[0]['id']
                fip = self.network_h.get_floatingip(self.fip_id)
                self.fip_net_id = fip['floating_network_id']
                self.fip_ip = fip['floating_ip_address']
        self.member_ids = self.obj.get('members', [])
        self.member_ips = [self.network_h.show_lb_member(x)['address']
                                                for x in self.member_ids]
        if self.member_ids:
            self.port = self.network_h.show_lb_member(
                             self.member_ids[0])['protocol_port']
        health_monitors = self.obj.get('health_monitors', [])
        for hmon in health_monitors:
            self.hmons[hmon] = self.network_h.get_health_monitor(hmon)
        custom_attr_list = self.obj.get('custom_attributes', [])
        for attr_dict in custom_attr_list and custom_attr_list[0]:
            self.custom_attr.update({k:v for k,v in attr_dict.iteritems()})
        self.logger.info('LB %s, members %s, vip %s, fip %s, protocol %s, port '
                         '%s healthmonitors %s'%(self.name, self.member_ips,
                         self.vip_ip, self.fip_ip, self.protocol,
                         self.port, self.hmons.keys()))

    def create(self):
        try:
            self.obj = self.network_h.get_lb_pool(name=self.name)
            self.uuid = self.obj.get('id')
            self.read(self.uuid)
            self.already_present = True
            self.logger.info('Load Balancer %s is already present'%self.name)
        except:
            self.logger.info('Creating Load Balancer %s'%self.name)
            self.obj = self.network_h.create_lb_pool(self.name,
                                      lb_method=self.lb_method,
                                      protocol=self.protocol,
                                      network_id=self.network_id,
                                      custom_attr=self.custom_attr)
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
        for hmon in self.healthmonitors:
            self.create_hmon(hmon)
        if self.vip_id and (self.fip_net_id or self.fip_id):
            self.create_fip_on_vip()
        self.logger.info('LoadBalancer: %s, members: %s, vip: %s, fip:%s '
                         'hmons: %s'%(self.name, self.member_ips, self.vip_ip,
                         self.fip_ip, self.hmons.keys()))

    def create_fip_on_vip(self, fip_net_id=None, fip_id=None):
        if not self.is_vip_active:
            raise Exception('LB %s doesnt have vip set'%self.uuid)
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

    def create_hmon(self, hmon_dict):
        if hmon_dict.get('id', None):
            if hmon_dict['id'] not in self.hmons.keys():
                hmon_obj = self.network_h.get_health_monitor(hmon_dict['id'])
            else:
                hmon_obj = self.hmons[hmon_dict['id']]
        else:
            hmon_obj = self.network_h.create_health_monitor(
                                      hmon_dict['delay'],
                                      hmon_dict['max_retries'],
                                      hmon_dict['probe_type'],
                                      hmon_dict['timeout'])
            assert hmon_obj, 'Create Healthmonitor failed'
            self.logger.info('Created Health Monitor %s'%hmon_obj['id'])
        self.hmons[hmon_obj['id']] = hmon_obj
        self.associate_hmon(hmon_obj['id'])

    def associate_hmon(self, hmon_id):
        self.network_h.associate_health_monitor(self.uuid, hmon_id)

    def delete_hmon(self, hmon_id):
        self.disassociate_hmon(hmon_id)
        self.logger.info('Deleting Health Monitor %s'%hmon_id)
        self.network_h.delete_health_monitor(hmon_id)
        self.hmons.pop(hmon_id)

    def disassociate_hmon(self, hmon_id):
        self.network_h.disassociate_health_monitor(self.uuid, hmon_id)

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
            member_ids = [x['id'] for x in self.network_h.list_lb_members(
                                           address=address, fields='id')]
            member_id = list(set(member_ids) & set(self.member_ids))[0]
        else:
            address = self.network_h.show_lb_member(member_id,
                                     fields='address')['address']
        self.logger.info('Deleting LB Member %s'%address)
        self.network_h.delete_lb_member(member_id)
        self.deleted_member_ids.append(member_id)
        self.member_ids.remove(member_id)
        self.member_ips.remove(address)

    def _populate_vars_from_vip_obj(self):
        self.vip_id = self.vip.get('id')
        self.vip_ip = self.vip.get('address')
        self.vip_port_id = self.vip.get('port_id', None)
        self.vip_net_id = self.network_h.get_vn_of_subnet(\
                              self.vip.get('subnet_id', None))
        self.is_vip_active = True
        self.si_uuid = None
        self.label = None
        self.active_vr = None
        self.standby_vr = None
        self.active_vm = None
        self.standby_vm = None
        self.control_node = None

    def check_and_create_vip(self):
        try:
            self.vip = self.network_h.show_vip(name=self.vip_name)
            self._populate_vars_from_vip_obj()
            self.logger.info('VIP is already present')
        except:
            self.logger.debug('Creating VIP %s'%self.name)
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
        self.vip = self.network_h.create_vip(name, protocol, port, self.uuid,
                                        network_id=network_id)
        self._populate_vars_from_vip_obj()
        self.logger.info('Created vip(%s) %s' %(self.vip_id, self.vip_ip))
        return self.vip_id

    def delete_vip(self):
        self.logger.info('Deleting vip(%s) %s' %(self.vip_id, self.vip_ip))
        self.network_h.delete_vip(self.vip_id)
        self.is_vip_active = False
        self.is_fip_active = False

    def reset_vip(self, verify=False):
        self.delete_vip()
        self.create_vip()

    def delete_custom_attr(self, key):
        self.custom_attr.pop(key, None)
        self.update_custom_attr()

    def add_custom_attr(self, key, value):
        self.custom_attr.update({key:value})
        self.update_custom_attr()

    def update_custom_attr(self, custom_attr_dict=dict()):
        self.custom_attr = custom_attr_dict or self.custom_attr
        self.network_h.update_lb_pool(self.uuid, {'custom_attributes':
                                                  [self.custom_attr]})

    # The test is expected to add start_active_vrouter in addCleanup
    def stop_active_vrouter(self):
        active_vr = self.get_active_vrouter()
        self.inputs.stop_service('supervisor-vrouter', [active_vr])
        self._populate_vars_from_vip_obj()

    def start_active_vrouter(self):
        active_vr = self.get_active_vrouter()
        self.inputs.start_service('supervisor-vrouter', [active_vr])

    # The test is expected to add start_standby_vrouter in addCleanup
    def stop_standby_vrouter(self):
        standby_vr = self.get_standby_vrouter()
        self.inputs.stop_service('supervisor-vrouter', [standby_vr])
        self._populate_vars_from_vip_obj()

    def start_standby_vrouter(self):
        standby_vr = self.get_standby_vrouter()
        self.inputs.start_service('supervisor-vrouter', [standby_vr])

    def delete(self):
        self.logger.info('Deleting LoadBalancer %s(%s)'%(self.name, self.uuid))
        for member_id in list(self.member_ids):
            self.delete_member(member_id)
        for hmon_id in self.hmons.keys():
            self.delete_hmon(hmon_id)
        if self.is_fip_active:
            self.delete_fip_on_vip()
        if self.is_vip_active:
            self.delete_vip()
        self.network_h.delete_lb_pool(self.uuid)
        if getattr(self, 'verify_is_run', None):
            assert self.verify_on_cleanup()
        self.uuid = None

    def verify_on_setup(self):
        assert self.verify_in_api_server()
        if self.is_vip_active:
            assert self.verify_in_agent()
            assert self.verify_in_control_node()
        self.logger.info('LoadBalancer(%s): verify_on_setup passed'%self.uuid)
        self.verify_is_run = True
        return True

    def verify_on_cleanup(self):
        assert self.verify_not_in_api_server()
        if self.vip_id:
            assert self.verify_vip_not_in_agent()
            assert self.verify_vip_not_in_control_node()
        if self.fip_id:
            assert self.verify_fip_not_in_agent()
            assert self.verify_fip_not_in_control_node()
        self.logger.info('LoadBalancer(%s): verify_on_cleanup passed'%self.uuid)
        return True

    def verify_not_in_api_server(self):
        assert self.verify_member_not_in_api_server()
        assert self.verify_hm_not_in_api_server()
        if self.fip_id:
            assert self.verify_fip_not_in_api_server()
        if self.vip_id:
            assert self.verify_vip_not_in_api_server()
        assert self.verify_pool_not_in_api_server()
        return True

    @retry(delay=6, tries=10)
    def verify_fip_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_fip(self.fip_id, refresh=True):
            return False
        self.logger.debug('FIP removal verification passed in API server')
        return True

    @retry(delay=6, tries=10)
    def verify_pool_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        pool = self.api_h.get_lb_pool(self.uuid, refresh=True)
        if pool:
            self.logger.warn("Loadbalancer pool %s still present in API"
                             " server even after pool delete" %(self.uuid))
            return False
        self.logger.debug(
            "Load Balancer pool %s got deleted in API server" %(self.uuid))
        return True

    @retry(delay=6, tries=10)
    def verify_member_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for member_id in self.deleted_member_ids:
            member = self.api_h.get_lb_member(member_id, refresh=True)
            if member:
                self.logger.warn("LB member %s still present in API server"
                                 " even after member delete" % (member_id))
                return False
            self.logger.debug(
                "LB member %s got deleted in API server" % (member_id))
        return True

    @retry(delay=6, tries=10)
    def verify_vip_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        vip = self.api_h.get_lb_vip(self.vip_id, refresh=True)
        if vip:
            self.logger.warn("LB VIP %s still present in API server"
                             " even after vip delete" % (self.vip_id))
            return False
        self.logger.debug(
            "LB vip %s got deleted in API server" % (self.vip_id))
        return True

    @retry(delay=6, tries=10)
    def verify_hm_not_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for hmon_id in self.hmons.keys():
            hmon = self.api_h.get_lb_healthmonitor(hmon_id, refresh=True)
            if hmon:
                self.logger.warn("LB health monitor %s still present"%(hmon_id))
                return False
            self.logger.debug("LB health monitor %s got deleted" %(hmon_id))
        return True

    def verify_in_api_server(self):
        assert self.verify_lb_pool_in_api_server()
        if self.member_ids:
            assert self.verify_member_in_api_server()
        if self.is_vip_active:
            assert self.verify_vip_in_api_server()
            assert self.verify_si_launched()
        if self.is_fip_active:
            assert self.verify_fip_in_api_server()
        if self.hmons:
            assert self.verify_hm_in_api_server()
        return True

    @retry(delay=6, tries=10)
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
        if self.is_vip_active:
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
        if self.hmons:
            if sorted(self.hmons.keys()) != sorted(pool.hmons()):
                self.logger.warn("LB %s health monitors dont match, expected %s"
                                 " got %s"%(self.uuid, self.hmons.keys(),
                                            pool.members()))
                return False
        if self.custom_attr:
            custom_attrs = pool.custom_attrs()
            if self.custom_attr != custom_attrs:
                self.logger.warn("LB %s custom_attributes doesnt match,"
                                 "expected %s, got %s"%(self.uuid,
                                 self.custom_attr, custom_attrs))
                return False
        self.logger.debug("LB(%s) got created in api server"% (self.uuid))
        return True

    @retry(delay=6, tries=10)
    def verify_vip_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
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
        self.logger.debug("LB VIP %s got created in api server" %(self.vip_id))
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
        return True

    @retry(delay=6, tries=10)
    def verify_member_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for member_id in self.member_ids:
            member = self.api_h.get_lb_member(member_id)
            if not member:
                self.logger.warn("LB member %s not found" %(member_id))
                return False
            if member.ip() not in self.member_ips:
                self.logger.warn("member %s ip dont match, expected one of %s"
                             "got %s"%(member_id, self.member_ips, member.ip()))
                return False
            self.logger.debug("LB member %s created successfully" % (member_id))
        return True

    @retry(delay=6, tries=10)
    def verify_hm_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for hm_id, hm_obj in self.hmons.iteritems():
            hm = self.api_h.get_lb_healthmonitor(hm_id)
            if not hm:
                self.logger.warn("Health Monitor %s not found"%hm_id)
                return False
            self.logger.debug("LB Health Monitor %s created successfully"%hm_id)
        return True

    @retry(6, 10)
    def verify_si_launched(self, refresh=False):
        svc_mon_h = self.connections.get_svc_mon_h(refresh)
        si = svc_mon_h.get_service_instance(name=self.get_si_name(),
                                            refresh=True)
        if si and si.is_launched():
            self.logger.debug('Load Balancer: SI got launched')
            return True
        self.logger.warn('LB(%s): SI status is not active in svc-mon'%self.uuid)
        return False

    def get_si_name(self):
        return self.uuid

    def get_si(self):
        if not getattr(self, 'si_uuid', None):
            self.si_uuid = None
            self.api_h = self.connections.api_server_inspect
            pool = self.api_h.get_lb_pool(self.uuid, refresh=True)
            if pool:
                self.si_uuid = pool.si()
            self.logger.debug('LB %s: SI uuid is %s'%(self.uuid, self.si_uuid))
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
                self.logger.warn('Unable to get standby vm for LB %s'%self.uuid)
        return self.standby_vm

    def get_active_instance(self):
        if not getattr(self, 'active_vm', None):
            self.get_active_standby_instance()
            if not self.active_vm:
                self.logger.warn('Unable to get active vm for LB %s'%self.uuid)
        return self.active_vm

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
                self.logger.warn('Fail to get vrouter for active lbaas')
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
                self.logger.warn('Fail to get vrouter for standby lbaas')
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
                self.logger.warn('LB: Unable to fetch label of vip intf')
        return self.label

    def get_ctrl_nodes(self, ri_name):
        rt_list = []
        peer_list = []
        ri = self.vnc_api_h.routing_instance_read(fq_name=ri_name)
        rt_list = [rt['to'][0] for rt in ri.get_route_target_refs()]
        ctrl_node = ComputeNodeFixture(self.connections,
                                       self.get_active_vrouter()
                                      ).get_active_controller()
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

    def verify_in_control_node(self):
        assert self.verify_vip_in_control_node()
        if self.is_fip_active:
            assert self.verify_fip_in_control_node()
        self.logger.debug('LB %s: vip %s: verify_in_control_node passed'
                          %(self.uuid, self.vip_id))
        return True

    @retry(6, 10)
    def verify_vip_in_control_node(self):
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
            match = False
            for route in routes:
                if route['label'] == exp_label:
                    match = True
            if match == False:
                self.logger.warn('LB: label(%s) doesnt match expected(%s)'
                                 %(route['label'], exp_label))
                return False
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
        return True

    def verify_in_agent(self):
        assert self.verify_netns_instance_launched()
        assert self.verify_vip_in_agent()
        if self.is_fip_active:
            assert self.verify_fip_in_agent()
        self.logger.debug('LB %s: vip %s: verify_in_agent passed'
                          %(self.uuid, self.vip_id))
        return True

    def is_instance_launched(self, vm_id, vrouter):
        if not vm_id or not vrouter:
            self.logger.warn('is_instance_launched: si vm_id or vrouter'
                             ' info not available')
            return False
        cmd_str = 'ip netns list | grep %s:%s | grep -v grep'%(vm_id,self.uuid)
        output = self.inputs.run_cmd_on_server(vrouter, cmd_str)
        if not output:
            self.logger.debug('netns instance %s:%s not found'
                             %(vm_id, self.uuid))
            return False
        if len(output.strip().split('\n')) > 1:
            self.logger.debug('Multiple %s:%s netns instances found'
                             %(vm_id, self.uuid))
            return False
        cmd_str = 'ps ax | grep haproxy | grep %s | grep -v grep' % self.uuid
        if not self.inputs.run_cmd_on_server(vrouter, cmd_str):
            self.logger.debug('haproxy not found for LB %s'%self.uuid)
            return False
        if not self.is_custom_attr_in_haproxy_conf(vrouter):
            return False
        return True

    def is_custom_attr_in_haproxy_conf(self, vrouter):
        haproxy_cfg = '/var/lib/contrail/loadbalancer/%s/haproxy.conf'%self.uuid
        for key,value in self.custom_attr.iteritems():
            cmd = custom_attributes_dict[key]
            if cmd.startswith('option '):
                value = '' if value == 'True' else 'no'
            cmd_str = 'grep "%s" %s | grep -v grep'%(cmd, haproxy_cfg)
            ret = self.inputs.run_cmd_on_server(vrouter, cmd_str)
            if not ret or 'No such file or directory' in ret or\
               cmd not in ret or str(value) not in ret:
                self.logger.debug('custom attr (%s, %s) not found '
                                  'for LB %s @ %s'%(key, value, self.uuid,
                                                    vrouter))
                return False
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
        self.logger.debug('Netns instances got launched')
        return True

    @retry(6, 10)
    def verify_fip_in_agent(self):
        exp_label = self.get_vip_label()
        active_vr = self.get_active_vrouter()
        if not active_vr or not exp_label or exp_label < 1:
            self.logger.warn('LB(%s): unable to find active vr'%self.uuid)
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
        return True
    # end verify_fip_not_in_agent

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
    def verify_fip_not_in_agent(self):
        vn_fq_name = ':'.join(self.id_to_fq_name(self.fip_net_id))
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.connections.agent_inspect[compute_ip]
            route = inspect_h.get_vna_active_route(ip=self.fip_ip,
                                                   prefix='32',
                                                   vn_fq_name=vn_fq_name)
            if route:
                self.logger.warn('FIP %s still present in Agent %s'
                                 %(self.fip_ip, compute_ip))
                return False
            self.logger.debug('FIP %s is removed from agent %s'
                             %(self.fip_ip, compute_ip))
        return True
    # end verify_fip_not_in_agent

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
        self.logger.debug('Netns instance got deleted')
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
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

def tracefunc(frame, event, arg, indent=[0]):
      if event == "call":
          indent[0] += 2
          if frame.f_code.co_name.startswith('verify_'):
              print "-" * indent[0] + "> call function", frame.f_code.co_name
      elif event == "return":
#          if frame.f_code.co_name.startswith('verify_'):
#              print "<" + "-" * indent[0], "exit function", frame.f_code.co_name, frame.f_code.co_names
          indent[0] -= 2
      return tracefunc

if __name__ == "__main__":
    import sys
    from vn_test import VNFixture
    from vm_test import VMFixture
#    sys.settrace(tracefunc)
#    obj = LBaasFixture(api_type='neutron', name='LB', connections=setup_test_infra(), network_id='4b39a2bd-4528-40e8-b848-28084e59c944', members={'vms': ['a72ad607-f1ca-44f2-b31e-e825a3f2d408'], 'address': ['192.168.1.10']}, vip_net_id='4b39a2bd-4528-40e8-b848-28084e59c944', protocol='TCP', port='22', healthmonitors=[{'delay':5, 'timeout':5, 'max_retries':5, 'probe_type':'PING'}])
    conn = setup_test_infra()
    vnfix = VNFixture(connections=conn)
    vnfix.setUp()
    vip_fix = VNFixture(connections=conn)
    vip_fix.setUp()
    fip_fix = VNFixture(connections=conn, router_external=True)
    fip_fix.setUp()
    subnet = vnfix.get_cidrs()[0]
    vm_fix = VMFixture(connections=conn, vn_obj=vnfix.obj)
    vm_fix.setUp()
    obj = LBaasFixture(api_type='neutron', name='LB', connections=conn, network_id=vnfix.uuid,
                       members={'address': [get_random_ip(subnet)], 'vms': [vm_fix.vm_id]},
                       vip_net_id=vip_fix.uuid, fip_net_id=fip_fix.uuid, protocol='TCP', port='22',
                       healthmonitors=[{'delay':5, 'timeout':5, 'max_retries':5, 'probe_type':'PING'}],
                       custom_attr={'max_conn': 100, 'max_sess_rate': 20, 'server_timeout': 50000, 'rate_limit_sessions': 10, 'http_server_close': "True"})
    obj.setUp()
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
