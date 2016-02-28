import os
from tcutils.util import *
import logging
from common.openstack_libs import network_client as client
from common.openstack_libs import network_http_client as HTTPClient
from common.openstack_libs import network_client_exception as CommonNetworkClientException


class NetworkClientException(CommonNetworkClientException):

    def __init__(self, **kwargs):
        message = kwargs.get('message')
        self.status_code = kwargs.get('status_code', 0)
        if message:
            self.message = message
        super(NetworkClientException, self).__init__(**kwargs)

    def __str__(self):
        return repr(self.message)


class QuantumHelper():

    def __init__(
            self,
            username,
            password,
            project_id,
            auth_server_ip,
            cfgm_ip=None,
            logger=None):
        httpclient = None
        self.quantum_port = '9696'
        self.username = username
        self.password = password
        self.project_id = get_plain_uuid(project_id)
        self.cfgm_ip = cfgm_ip
        self.auth_server_ip = auth_server_ip
        self.obj = None
        self.logger = logger or logging.getLogger(__name__)

        self.auth_url = os.getenv('OS_AUTH_URL') or \
            'http://' + auth_server_ip + ':5000/v2.0'
    # end __init__

    def setUp(self):
        insecure = bool(os.getenv('OS_INSECURE', True))
        # Quantum Client class does not have tenant_id as argument
        # So, do quantum auth differently
        if 'quantum' in client.__name__:
            self._do_quantum_authentication()
        else:
            self.obj = client.Client('2.0', username=self.username,
                                     password=self.password,
                                     tenant_id=self.project_id,
                                     auth_url=self.auth_url)
    # end __init__

    def _do_quantum_authentication(self):
        try:
            httpclient = HTTPClient(username=self.username,
                                    tenant_id= self.project_id,
                                    password=self.password,
                                    auth_url=self.auth_url)
            httpclient.authenticate()
        except CommonNetworkClientException, e:
            self.logger.exception('Exception while connection to Quantum')
            raise e
        OS_URL = 'http://%s:%s/' % (self.cfgm_ip, self.quantum_port)
        OS_TOKEN = httpclient.auth_token        
        self.obj = client.Client('2.0', endpoint_url=OS_URL, token=OS_TOKEN)
    # end _do_quantum_authentication

    def get_handle(self):
        return self.obj
    # end get_handle

    def create_network(
            self,
            vn_name,
            vn_subnets=None,
            ipam_fq_name=None,
            shared=False,
            router_external=False,
            enable_dhcp = True,
            disable_gateway=False):
        """Create network given a name and a list of subnets.
        """
        try:
            net_req = {}
            net_req['name'] = vn_name
            if shared:
                net_req['shared'] = shared
            if router_external:
                net_req['router:external'] = router_external
            net_rsp = self.obj.create_network({'network': net_req})
            self.logger.debug('Response for create_network : ' + repr(net_rsp))

            vn_id = net_rsp['network']['id']
            net_id = net_rsp['network']['id']
            if vn_subnets:
                for subnet in vn_subnets:
                    net_rsp = self.create_subnet(
                        subnet, net_id, ipam_fq_name, enable_dhcp, disable_gateway)
            # end for
            return self.obj.show_network(network=net_id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating network %s' % (vn_name))
            return None

    def create_subnet(self, subnet, net_id, ipam_fq_name=None, enable_dhcp=True, disable_gateway=False):
        subnet_req = subnet
        subnet_req['network_id'] = net_id
        subnet_req['enable_dhcp'] = enable_dhcp
        subnet_req['ip_version'] = '6' if is_v6(subnet['cidr']) else '4'
        subnet_req['cidr'] = unicode(subnet_req['cidr'])
        subnet_req['contrail:ipam_fq_name'] = ipam_fq_name
        if disable_gateway:
           subnet_req['gateway_ip'] = None
        try:
            subnet_rsp = self.obj.create_subnet({'subnet': subnet_req})
            self.logger.debug(
                'Response for create_subnet : ' +
                repr(subnet_rsp))
            return subnet_rsp
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating subnet for vn with id %s' %
                (net_id))
            return None
    # end _create_subnet

    def create_port(self, net_id, fixed_ips=[],
                    mac_address=None, no_security_group=False,
                    security_groups=[], extra_dhcp_opts=None):
        port_req_dict = {
            'network_id': net_id,
        }
        if mac_address:
            port_req_dict['mac_address'] = mac_address
        if no_security_group:
            port_req_dict['security_groups'] = None
        if security_groups:
            port_req_dict['security_groups'] = security_groups
        if extra_dhcp_opts:
            port_req_dict['extra_dhcp_opts'] = extra_dhcp_opts

        if fixed_ips:
            port_req_dict['fixed_ips'] = fixed_ips
        try:
            port_rsp = self.obj.create_port({'port': port_req_dict})
            self.logger.debug('Response for create_port : ' + repr(port_rsp))
            return port_rsp['port']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating port in vn with id %s' %
                (net_id))
            return None

    # end create_port

    def get_port(self, port_id, field=''):
        try:
            port_obj = self.obj.show_port(port_id, fields=field)['port']
            return port_obj[field] if field else port_obj
        except CommonNetworkClientException as e:
            self.logger.debug('Get port on %s failed' % (port_id))
    # end get_port

    def get_port_ips(self, port_id):
        port_obj = self.get_port(port_id, field='fixed_ips')
        return [x['ip_address'] for x in port_obj]

    def create_security_group(self, name):
        sg_dict = {'name': name, 'description': 'SG-' + name}
        try:
            sg_resp = self.obj.create_security_group(
                {'security_group': sg_dict})
            return sg_resp['security_group']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating security group %s' % (name))
            return None

    # end create_security_group

    def delete_security_group(self, sg_id):
        self.obj.delete_security_group(sg_id)
    # end delete_security_group

    def create_security_group_rule(self, sg_id, direction='ingress',
                                   port_range_min=None, port_range_max=None,
                                   protocol=None, remote_group_id=None,
                                   remote_ip_prefix=None):
        sg_rule = None
        sg_rule_dict = {'security_group_id': sg_id}
        if direction:
            sg_rule_dict['direction'] = direction
        if port_range_min != None:
            sg_rule_dict['port_range_min'] = port_range_min
        if port_range_max != None:
            sg_rule_dict['port_range_max'] = port_range_max
        if protocol:
            sg_rule_dict['protocol'] = protocol
        if remote_group_id:
            sg_rule_dict['remote_group_id'] = remote_group_id
        if remote_ip_prefix:
            sg_rule_dict['remote_ip_prefix'] = remote_ip_prefix
        try:
            sg_rule = self.obj.create_security_group_rule(
                {'security_group_rule': sg_rule_dict})
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating SG Rule %s' % (sg_rule_dict))
        return sg_rule
    # end create_security_group_rule

    def delete_default_egress_rule(self, sg_id):
        #currently this method can be only used before adding any custom rule to sg
        rules = self.list_security_group_rules(tenant_id=self.project_id)
        for rule in rules['security_group_rules']:
            if rule['security_group_id'] == sg_id and rule['remote_ip_prefix'] == '0.0.0.0/0':
                self.delete_security_group_rule(rule['id'])
                break

    def delete_security_group_rule(self, rule_id):
        self.obj.delete_security_group_rule(rule_id)
    # end delete_security_group_rule

    def delete_port(self, port_id,):
        port_rsp = self.obj.delete_port(port_id)
        self.logger.debug('Response for delete_port : ' + repr(port_rsp))
        return port_rsp
    # end delete_port

    def get_vn_obj_if_present(self, vn_name, project_id=None):
        project_id = project_id if project_id else self.project_id
        try:
            net_rsp = self.obj.list_networks(tenant_id=project_id, name=vn_name)['networks']
            if net_rsp:
                return self.obj.show_network(network=net_rsp[0]['id'])
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing Neutron net-list")
            raise NetworkClientException(message=str(e))
        return None
    # end get_vn_obj_if_present

    def get_vn_obj_from_id(self, uuid):
        try:
            return self.obj.show_network(network=uuid)
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing neutron net-list")
            return None
        return None

    def delete_vn(self, vn_id):
        result = True
        try:
            net_rsp = self.obj.delete_network(vn_id)
            self.logger.debug('Response for deleting network %s' %
                              (str(net_rsp)))
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron exception while deleting a VN %s' % (vn_id))
            result = False

        return result
    # end _delete_vn

    def delete_quota(self, project_id):
        result = True
        try:
            net_rsp = self.obj.delete_quota(project_id)
            self.logger.debug('Response for deleting quota %s' %
                              (str(net_rsp)))
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron exception while quota delete for project %s' % (project_id))
            result = False

        return result
    # end delete_quota

    def list_networks(self, args):
        try:
            net_rsp = self.obj.list_networks(args)
            return net_rsp
        except CommonNetworkClientException as e:
            self.logger.debug("Exception while viewing Network list")
            return []
    # end list_networks

    def create_floatingip(self, fip_pool_vn_id, project_id=None, port_id=None):
        if not project_id:
            project_id = self.project_id
        fip_req = {'floatingip': {'floating_network_id': fip_pool_vn_id,
                                  'tenant_id': project_id}}
        if port_id:
            fip_req['floatingip']['port_id'] = port_id
        try:
            fip_resp = self.obj.create_floatingip(fip_req)
            return fip_resp
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating floatingip for tenant %s with fip_pool_vn_id %s' %
                (project_id, fip_pool_vn_id))
            return None

    # end create_floatingip

    def delete_floatingip(self, fip_id):
        fip_resp = self.obj.delete_floatingip(fip_id)
        return fip_resp
    # end delete_floatingip

    def list_floatingips(self, tenant_id=None, port_id=None):
        if not tenant_id:
            tenant_id = self.project_id
        if port_id:
            tenant_id = None # workaround for api-server bug with multiple filters
        return self.obj.list_floatingips(tenant_id=tenant_id, port_id=port_id)['floatingips']
    # end

    def get_floatingip(self, fip_id, fields=''):
        fip_resp = self.obj.show_floatingip(fip_id, fields='')['floatingip']
        return fip_resp[fields] if fields else fip_resp
    # end get_floatingip

    def get_port_id(self, vm_id):
        ''' Returns the Neutron port-id of a VM.

        '''
        try:
            port_rsp = self.obj.list_ports(device_id=[vm_id])
            port_id = port_rsp['ports'][0]['id']
            return port_id
        except Exception as e:
            self.logger.error('Error occured while getting port-id of a VM ')
            return None
    # end

    def assoc_floatingip(self, fip_id, port_id):
        fip_dict = {'floatingip': {'port_id': port_id}}
        return self.update_floatingip(fip_id, fip_dict)

    def update_floatingip(self, fip_id, update_dict):
        return self.obj.update_floatingip(fip_id, update_dict)
    # end update_floatingip

    def get_vn_id(self, vn_name):
        net_id = None
        net_rsp = self.obj.list_networks()
        for (
            x,
            y,
            z) in [
            (network['name'],
             network['id'],
             network['tenant_id']) for network in net_rsp['networks']]:
            if vn_name == x and self.project_id in z:
                net_id = y
                break
        return net_id
    # end get_vn_id

    def create_policy(self, policy_dict):
        policy_rsp = None
        try:
            policy_rsp = self.obj.create_policy(policy_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Neutron Exception while creating policy" + str(e))
        return policy_rsp
    # end create_policy

    def update_policy(self, policy_id, policy_entries):
        '''policy_data format {'policy': {'entries': new_policy_entries}}'''
        policy_rsp = None
        try:
            policy_rsp = self.obj.update_policy(policy_id, policy_entries)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Neutron Exception while creating policy" + str(e))
        self.logger.debug("policy_rsp for policy_id %s after update is %s" %
                         (policy_id, policy_rsp))
        return policy_rsp
    # end update_policy

    def get_policy_if_present(self, project_name=None, policy_name=None):
        policy_rsp = None
        try:
            policy_rsp = self.list_policys()
            for (
                x,
                y,
                z) in [
                (policy['name'],
                 policy['id'],
                    policy['fq_name']) for policy in policy_rsp['policys']]:
                if policy_name == x:
                    if project_name:
                        if project_name in z:
                            policy_id = y
                            return self.obj.show_policy(policy=policy_id)
                    else:
                        policy_id = y
                        return self.obj.show_policy(policy=policy_id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing Neutron policy-listing")
        return None

    # end get_policy_if_present

    def list_policys(self):
        policy_list = None
        try:
            policy_list = self.obj.list_policys(tenant_id=self.project_id)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Neutron Exception while listing policies" + str(e))
        return policy_list
    # end list_policys

    def delete_policy(self, policy_id):
        result = True
        try:
            self.obj.delete_policy(policy_id)
        except CommonNetworkClientException as e:
            result = False
            self.logger.error(
                "Neutron Exception while deleting policy" + str(e))
        return result
    # end delete_policy

    def get_policy_fq_name(self, policy_obj):
        return policy_obj['policy']['fq_name']
    # end get_policy_fq_name

    def update_network(self, vn_id, network_dict):
        net_rsp = None
        try:
            net_rsp = self.obj.update_network(vn_id, network_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Neutron Exception while updating network" + str(e))
        return net_rsp
    # end update_network

    def list_security_groups(self, *args, **kwargs):
        return self.obj.list_security_groups(*args, **kwargs)
    # end list_security_groups

    def show_security_group(self, sg_id):
        return self.obj.show_security_group(sg_id)
    # end show_security_group

    def list_security_group_rules(self, *args, **kwargs):
        return self.obj.list_security_group_rules(*args, **kwargs)
    # end list_security_group_rules

    def create_router(self, router_name, tenant_id=None):
        router_body = {}
        router_body['router'] = {}
        router_body['router']['name'] = router_name
        if tenant_id:
            router_body['router']['tenant_id'] = tenant_id
        try:
            return self.obj.create_router(router_body)['router']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Neutron Exception while creating Router %s' % (router_name))
            return None

    def get_router(self, uuid=None, name=None):
        if uuid:
            return self.obj.show_router(uuid)['router']
        if name:
            return self.obj.list_routers(name=name, tenant_id=self.project_id)['routers'][0]

    def delete_router(self, router_id=None):
        return self.obj.delete_router(router_id)

    def get_subnet_ids(self, vn_id):
        return self.obj.show_network(vn_id, fields='subnets')['network']['subnets']

    def get_subnets_of_vn(self, vn_id):
        subnets = []
        try:
            for subnet_id in self.get_subnet_ids(vn_id):
                subnets.append(self.obj.show_subnet(subnet_id)['subnet'])
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Exception while reading network details%s' % (vn_id))
            return None
        return subnets
    # end get_subnets_of_vn

    def get_subnet(self, subnet_id, field=''):
        resp = self.obj.show_subnet(subnet_id, fields=field)['subnet']
        return resp[field] if field else resp

    def get_vn_of_subnet(self, subnet_id):
        return self.get_subnet(subnet_id, field='network_id')

    def get_vn_of_port(self, port_id):
        return self.get_port(port_id, field='network_id')

    def add_router_interface(self, router_id, subnet_id=None, port_id=None, vn_id=None):
        ''' Add an interface to router.
            Result will be of form
            {u'subnet_id': u'd5ae735b-4df2-473f-9d6c-ca9ddb263fdc', u'tenant_id': u'509a5c7a23474f15a456905adcd9fc8d', u'port_id': u'f2d4cb13-2401-4830-b8cc-c23d544bb1d6', u'id': u'da7e4878-04fa-4d1a-8def-4b11c2eaf569'}
        '''
        body = {}
        if vn_id:
            subnet_id = self.get_subnet_ids(vn_id)[0]
        if subnet_id:
            body['subnet_id'] = subnet_id
        if port_id:
            body['port_id'] = port_id
        self.logger.info('Adding interface with subnet_id %s, port_id %s'
                         ' to router %s' % (subnet_id, port_id, router_id))
        result = self.obj.add_interface_router(router_id, body)
        return result
    # end add_router_interface

    def delete_router_interface(self, router_id, subnet_id=None, port_id=None, vn_id=None):
        ''' Remove an interface from router
        '''
        body = {}
        if vn_id:
            subnet_id = self.get_subnet_ids(vn_id)[0]
        if subnet_id:
            body['subnet_id'] = subnet_id
        if port_id:
            body['port_id'] = port_id
        self.logger.info('Deleting interface with subnet_id %s, port_id %s'
                         ' from router %s' % (subnet_id, port_id, router_id))
        try:
            result = self.obj.remove_interface_router(router_id, body)
            return result
        except NetworkClientException as e:
            self.logger.exception(e)
            raise NetworkClientException(message=str(e))
    # end delete_router_interface

    def router_gateway_set(self, router_id, ex_net_id):
        '''Set gateway for router
        '''
        body = {}
        body['network_id'] = ex_net_id
        self.logger.info('Setting gateway for router %s to network %s '
                         % (router_id, ex_net_id))
        try:
            result = self.obj.add_gateway_router(router_id, body)
            return result
        except NetworkClientException as e:
            self.logger.exception(e)
            raise NetworkClientException(message=str(e))
    # end router_gateway_set

    def router_gateway_clear(self, router_id):
        self.logger.info('Clearing gateway of router %s' %router_id)
        try:
            result = self.obj.remove_gateway_router(router_id)
            return result
        except NetworkClientException as e:
            self.logger.exception(e)
            raise NetworkClientException(message=str(e))

    def update_router(self, router_id, router_dict):
        router_rsp = None
        body = {}
        body['router'] = router_dict
        try:
            router_rsp = self.obj.update_router(router_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Exception while updating router " + str(e))
            raise e
        return router_rsp
    # end update_router

    def update_security_group(self, sg_id, sg_dict):
        sg_rsp = None
        body = {}
        body['security_group'] = sg_dict
        try:
            sg_rsp = self.obj.update_security_group(sg_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Exception while updating security group " + str(e))
            raise e
        return sg_rsp
    # end update_security_group

    def get_router_interfaces(self, router_id):
        ports_obj = self.obj.list_ports(device_id=router_id)['ports']
        return ports_obj

    def update_subnet(self, subnet_id, subnet_dict):
        subnet_rsp = None
        body = {}
        body['subnet'] = subnet_dict
        try:
            subnet_rsp = self.obj.update_subnet(subnet_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Neutron Exception while updating subnet" + str(e))
            raise e
        return subnet_rsp
    # end update_subnet

    def update_port(self, port_id, port_dict):
        port_rsp = None
        body = {}
        body['port'] = port_dict
        self.logger.debug('Updating port %s with body : %s' % (
            port_id, body))
        try:
            port_rsp = self.obj.update_port(port_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Exception while updating port" + str(e))
            raise e
        return port_rsp
    # end update_port

    def show_quota(self, tenant_id):
        quota_rsp = None
        try:
            quota_rsp = self.obj.show_quota(tenant_id)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Exception while running show quota" + str(e))
            raise e
        return quota_rsp
    # end show_quota

    def update_quota(self, tenant_id, quota_dict):
        quota_rsp = None
        body = {}
        body['quota'] = quota_dict
        try:
            quota_rsp = self.obj.update_quota(tenant_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Exception while running  quota update " + str(e))
        return quota_rsp
    # end update_quota

    def create_lb_pool(self, name, lb_method, protocol,
                       subnet_id=None, network_id=None, custom_attr={}):
        '''Create lb pool. Returns the lb object created'''
        if network_id and not subnet_id:
            subnet_id = self.get_subnet_ids(network_id)[0]
        pool_dict = {'name': name, 'lb_method': lb_method,
                     'protocol': protocol, 'subnet_id': subnet_id,
                     'custom_attributes': [custom_attr]}
        try:
            pool_resp = self.obj.create_pool({'pool': pool_dict})
            return pool_resp['pool']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Network Exception while creating LB Pool %s' % (name))
            return None
    # end create_lb_pool

    def delete_lb_pool(self, pool_id):
        '''Delete the lb'''
        pool_rsp = self.obj.delete_pool(pool_id)
        self.logger.debug('Response for delete_pool : ' + repr(pool_rsp))
    # end delete_lb_pool

    def update_lb_pool(self, pool_id, pool_dict={}):
        pool_rsp = None
        try:
            pool_rsp = self.obj.update_pool(pool_id, {'pool': pool_dict})
        except CommonNetworkClientException as e:
            self.logger.error(
                "NetworkClient Exception while updating pool" + str(e))
        return pool_rsp
    # end update_lb_pool

    def get_lb_pool(self, pool_id=None, name=None):
        ''' Returns the pool dict
            If pool_id is not found , returns None'''
        try:
            if pool_id:
                return self.obj.show_pool(pool_id)['pool']
            elif name:
                return self.obj.list_pools(name=name, tenant_id=self.project_id)['pools'][0]
        except:
            self.logger.debug('Get pool on %s failed' % (pool_id))
            return None
    # end get_pool

    def list_lb_pools(self):
        ''' Returns the LB pools in this tenant'''
        try:
            pools_list = self.obj.list_pools()
        except CommonNetworkClientException as e:
            self.logger.exception('List pools failed')
            return None
        return pools_list['pools']

    def create_health_monitor(self, delay, max_retries, probe_type, timeout):
        '''Returns the neutron health monitor dict created '''
        hm_dict = {'delay': delay, 'max_retries': max_retries,
                   'type': probe_type, 'timeout': timeout}
        try:
            hm_resp = self.obj.create_health_monitor(
                {'health_monitor': hm_dict})
            return hm_resp['health_monitor']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Network Exception while creating Health monitor')
            return None
    # end create_health_monitor

    def delete_health_monitor(self, hm_id):
        ''' Delete the Health monitor '''
        hm_rsp = self.obj.delete_health_monitor(hm_id)
        self.logger.debug(
            'Response for delete_health_monitor : ' + repr(hm_rsp))

    def update_health_monitor(self, hm_id, hm_dict):
        '''Update Health monitor object'''
        hm_rsp = None
        try:
            hm_rsp = self.obj.update_health_monitor(hm_id, hm_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "NetworkClient Exception while updating Health monitr" + str(e))
        return hm_rsp
    # end update_health_monitor

    def get_health_monitor(self, hm_id):
        ''' Returns Health monitor object as dict. 
            If not found, returns None
        '''
        try:
            hm_obj = self.obj.show_health_monitor(hm_id)
            return hm_obj['health_monitor']
        except CommonNetworkClientException as e:
            self.logger.debug('Get health-monitor on %s failed' % (hm_id))

    def list_health_monitors(self):
        ''' Returns a list of health monitor objects(dicts) in a tenant '''
        try:
            hm_list = self.obj.list_health_monitors()
        except CommonNetworkClientException as e:
            self.logger.error('List health-monitors failed')
            return None
        return hm_list['health_monitors']

    def associate_health_monitor(self, pool_id, hm_id):
        ''' Associate Health monitor to the pool. Returns True on success.
            Returns False if it fails
        '''
        body = {'health_monitor': {'id' : hm_id}}
        try:
            hm_list = self.obj.associate_health_monitor(pool_id, body)
        except CommonNetworkClientException as e:
            self.logger.error('Associating HM %s to Pool %s failed' % (
                              hm_id, pool_id))
            return None
        return hm_list['health_monitor']

    def disassociate_health_monitor(self, pool_id, hm_id):
        '''Disassociate health monitor from the pool
        '''
        self.obj.disassociate_health_monitor(pool_id, hm_id)

    def create_vip(self, name, protocol, protocol_port, pool_id,
                   subnet_id=None, network_id=None):
        ''' Create vip in the pool. Returns the vip object as dict
        '''
        if network_id and not subnet_id:
            subnet_id = self.get_subnet_ids(network_id)[0]
        vip_dict = {'name': name,
                    'protocol': protocol,
                    'protocol_port': protocol_port,
                    'subnet_id': subnet_id,
                    'pool_id': pool_id}
        try:
            vip_resp = self.obj.create_vip(
                {'vip': vip_dict})
            return vip_resp['vip']
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Network Exception while creating vip %s' % (name))
            return None
    # end create_vip

    def delete_vip(self, vip_id):
        '''Delete the vip'''
        self.obj.delete_vip(vip_id)

    def update_vip(self, vip_id, vip_dict):
        '''Update vip usign vip_dict. Returns the updated object as dict'''
        vip_resp = None
        try:
            vip_resp = self.obj.update_vip(hm_id, vip_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "NetworkClient Exception while updating vip" + str(e))
        return vip_resp
    # end update_vip_resp

    def show_vip(self, vip_id=None, name=None):
        '''Returns the vip object using id. If not found, returns None'''
        try:
            if vip_id:
                return self.obj.show_vip(vip_id)['vip']
            elif name:
                return self.obj.list_vips(name=name, tenant_id=self.project_id)['vips'][0]
        except:
            self.logger.debug('Get vip on %s/%s failed' % (vip_id, name))
            return None
    # end show_vip

    def list_vips(self):
        '''List the vips in this tenant'''
        try:
            vip_list = self.obj.list_vips()
        except CommonNetworkClientException as e:
            self.logger.error('List vips failed')
            return None
        return vip_list['vips']

    def create_lb_member(self, ip_address, protocol_port, pool_id):
        '''Create lb member. Returns the created lb member as dict'''
        member_dict = {'address':ip_address,
                       'protocol_port':protocol_port,
                       'pool_id':pool_id}
        try:
             member_resp = self.obj.create_member({'member': member_dict})
             return member_resp['member']
        except CommonNetworkClientException as e:
            self.logger.exception('Network Exception while creating LB member with address %s' % (ip_address))
            return None

    def delete_lb_member(self, lb_member_id):
        '''Delete the lb member'''
        member_resp = self.obj.delete_member(lb_member_id)
        self.logger.debug('Response for delete_member : ' + repr(member_resp))
    # end delete_lb_member

    def update_lb_member(self, lb_member_id, lb_member_dict):
        '''Update lb member using lb_member_dict. 
           Returns the updated object '''
        pass

    def list_lb_members(self, **kwargs):
        '''Returns a list of lb member objects in the tenant'''
        try:
            member_list = self.obj.list_members(**kwargs)
        except CommonNetworkClientException as e:
            self.logger.error('List member failed')
            return None
        return member_list['members']

    def show_lb_member(self, lb_member_id, **kwargs):
        '''Returns the lb member dict '''
        try:
            member_obj = self.obj.show_member(lb_member_id, **kwargs)
            return member_obj['member']
        except CommonNetworkClientException as e:
            self.logger.debug('show member on %s failed' % (lb_member_id))
            return None
    # end show_lb_member

# end QuantumHelper
