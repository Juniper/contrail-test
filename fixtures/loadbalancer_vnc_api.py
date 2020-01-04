#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#

from vnc_api.vnc_api import *
import uuid
from tcutils import util

#LOG = logging.getLogger(__name__)
DEVICE_OWNER_LOADBALANCER = "TestBaasV2"

class Sentinel(object):
    """A constant object that does not change even when copied."""
    def __deepcopy__(self, memo):
        # Always return the same object because this is essentially a constant.
        return self

    def __copy__(self):
        # called via copy.copy(x)
        return self

ATTR_NOT_SPECIFIED = Sentinel()

class LoadBalancerBase(object):

    def _fields(self, resource, fields):
        if fields:
            return dict(((key, item) for key, item in resource.items()
                         if key in fields))
        return resource

    def _get_resource_name(self, resource, parent, name, uuid):
        """ Generate an unique name. This is display name if there are
        no conflicts or display_name + uuid.
        """
        fq_name = list(parent.fq_name)
        fq_name.append(name)
        try:
            self._api.fq_name_to_id(resource, fq_name)
        except NoIdError:
            return name

        return name + '-' + uuid

    def _get_object_description(self,obj):
        id_perms = obj.id_perms
        if id_perms is None:
            return None
        return id_perms.description
    # end _get_object_description

    def _get_object_status(self,obj):
        id_perms = obj.id_perms
        if id_perms and id_perms.enable:
            return "ACTIVE"
        return "PENDING_DELETE"
    # end get_object_status

class ServiceLbManager(LoadBalancerBase):

    '''
        'vip_address': 'vip_address',
        'vip_subnet_id': 'vip_subnet_id',
        'admin_state': 'admin_state_up',
        'provisioning_status': 'provisioning_status',
        'operating_status': 'operating_status',
    '''

    def __init__(self,vnc,logger):
        self._api = vnc
        self.logger = logger

    def _get_listeners(self, lb):
        ll_list = []
        ll_back_refs = lb.get_loadbalancer_listener_back_refs()
        if ll_back_refs:
            for ll_back_ref in ll_back_refs:
                ll_list.append({ 'id': ll_back_ref['uuid'] })
        return ll_list

    def _get_interface_params(self, lb, props):
        vmi_list = lb.get_virtual_machine_interface_refs()
        if vmi_list is None:
            return None

        port_id = vmi_list[0]['uuid']
        if not props.vip_address or props.vip_address == ATTR_NOT_SPECIFIED:
            try:
                vmi = self._api.virtual_machine_interface_read(id=port_id)
            except NoIdError as ex:
                self.logger.error(ex)
                return None

            ip_refs = vmi.get_instance_ip_back_refs()
            if ip_refs:
                try:
                    iip = self._api.instance_ip_read(id=ip_refs[0]['uuid'])
                except NoIdError as ex:
                    self.logger.error(ex)
                    return None
                props.vip_address = iip.get_instance_ip_address()

        return port_id

    def make_dict(self, lb, fields=None):
        props = lb.get_loadbalancer_properties()
        port_id = self._get_interface_params(lb, props)
        res = {'id': lb.uuid,
               'tenant_id': lb.parent_uuid.replace('-', ''),
               'name': lb.display_name,
               'vip_port_id': port_id,
               'vip_subnet_id': props.vip_subnet_id,
               'vip_address': props.vip_address,
               'admin_state_up': props.admin_state,
               'provisioning_status': props.provisioning_status,
               'operating_status': props.operating_status,
               'provider': lb.get_loadbalancer_provider(),
               'listeners': self._get_listeners(lb)}

        return self._fields(res, fields)
        #return res

    def lb_list(self, tenant_id=None):
        if tenant_id:
            parent_id = str(uuid.UUID(tenant_id))
        else:
            parent_id = None
        return self._api.loadbalancers_list(parent_id=parent_id)

    def read(self, id):
        try:
            lb_obj = self._api.loadbalancer_read(id=id)
        except NoIdError:
            return None
        return self.make_dict(lb_obj)

    def delete(self, id):
        lb = self._api.loadbalancer_read(id=id)
        if not lb:
            return

        vmi_ids = lb.get_virtual_machine_interface_refs()
        self._api.loadbalancer_delete(id=id)
        if vmi_ids is None:
            return None
        self._delete_virtual_interface(vmi_ids)

    def _create_virtual_interface(self, project,vn_obj, lb_id, subnet_id,
                                  ip_address):
        if vn_obj:
            network_id = vn_obj.uuid
        if subnet_id:
            network_id = util.get_subnet_network_id(self._api, subnet_id)
        try:
            vnet = self._api.virtual_network_read(id=network_id)
        except NoIdError:
            raise NetworkNotFound(net_id=network_id)

        vmi = VirtualMachineInterface(lb_id, project)
        vmi.set_virtual_network(vnet)
        vmi.set_virtual_machine_interface_device_owner(
            DEVICE_OWNER_LOADBALANCER)

        sg_obj = SecurityGroup("default", project)
        vmi.add_security_group(sg_obj)
        self._api.virtual_machine_interface_create(vmi)

        iip_obj = InstanceIp(name=lb_id)
        iip_obj.set_virtual_network(vnet)
        iip_obj.set_virtual_machine_interface(vmi)
        if ip_address and ip_address != ATTR_NOT_SPECIFIED:
            iip_obj.set_instance_ip_address(ip_address)
        self._api.instance_ip_create(iip_obj)
        iip = self._api.instance_ip_read(id=iip_obj.uuid)
        vip_address = iip.get_instance_ip_address()

        return vmi, vip_address
    
    def _delete_virtual_interface(self, vmi_list):
        if vmi_list is None:
            return

        for vmi_ref in vmi_list:
            interface_id = vmi_ref['uuid']
            try:
                vmi = self._api.virtual_machine_interface_read(id=interface_id)
            except NoIdError as ex:
                LOG.error(ex)
                continue

            ip_refs = vmi.get_instance_ip_back_refs()
            if ip_refs:
                for ref in ip_refs:
                    self._api.instance_ip_delete(id=ref['uuid'])

            fip_refs = vmi.get_floating_ip_back_refs()
            for ref in fip_refs or []:
                try:
                    fip = self._api.floating_ip_read(id=ref['uuid'])
                except NoIdError as ex:
                    LOG.error(ex)
                    continue
                fip.set_virtual_machine_interface_list([])
                self._api.floating_ip_update(fip)
                self._api.floating_ip_delete(id=ref['uuid'])

            self._api.virtual_machine_interface_delete(id=interface_id)

    def _get_resource_name(self, resource, parent, name, uuid):
        """ Generate an unique name. This is display name if there are
        no conflicts or display_name + uuid.
        """
        fq_name = list(parent.fq_name)
        fq_name.append(name)
        try:
            self._api.fq_name_to_id(resource, fq_name)
        except NoIdError:
            return name
        return name + '-' + uuid

    def create(self, service_name,
               proj_obj, vn_obj, vip_address=None, subnet_uuid=None):
        """
        Create a loadbalancer.
        """
        lb_uuid = str(uuid.uuid4())
        lb_name = self._get_resource_name('loadbalancer',proj_obj,
                    service_name,lb_uuid)
        lb_display_name = lb_name
        lb_provider = 'opencontrail'
        lb_obj = Loadbalancer(name=lb_name, parent_obj=proj_obj,
                    loadbalancer_provider=lb_provider,
                    display_name=lb_display_name)

        lb_obj.uuid = lb_uuid

        vmi_obj, vip_address = self._create_virtual_interface(proj_obj,
            vn_obj,lb_uuid,subnet_uuid,vip_address)
        if vmi_obj is None:
            return None
        lb_obj.set_virtual_machine_interface(vmi_obj)

        id_perms = IdPermsType(enable=True)
        props = LoadbalancerType(provisioning_status='ACTIVE', id_perms=id_perms,
                      operating_status='ONLINE', vip_address=vip_address)
        lb_obj.set_loadbalancer_properties(props)

        try:
            self._api.loadbalancer_create(lb_obj)
        except RefsExistError:
            self._api.loadbalancer_update(lb_obj)
        return self.make_dict(lb_obj)

class ServiceLbListenerManager(LoadBalancerBase):

    '''
        'protocol': 'protocol',
        'protocol_port': 'protocol_port',
        'admin_state': 'admin_state_up',
        'connection_limit': 'connection_limit',
        'default_tls_container': 'default_tls_container_ref',
        'sni_containers': 'sni_container_refs',
    '''

    def __init__(self,vnc,logger):
        self._api = vnc
        self.logger = logger

    def _get_default_pool(self, ll):
        pool_refs = ll.get_loadbalancer_pool_back_refs()
        if pool_refs is None:
            return None
        return pool_refs[0]['uuid']

    def _get_loadbalancers(self, ll):
        loadbalancers = []
        lb = {}
        lb_refs = ll.get_loadbalancer_refs()
        if lb_refs is None:
            return None
        lb['id'] = lb_refs[0]['uuid']
        loadbalancers.append(lb)
        return loadbalancers

    def make_dict(self, ll, fields=None):
        props = ll.get_loadbalancer_listener_properties()
        res = {'id': ll.uuid,
               'tenant_id': ll.parent_uuid.replace('-', ''),
               'name': ll.display_name,
               'description': self._get_object_description(ll),
               'protocol': props.protocol,
               'protocol_port': props.protocol_port,
               'admin_state_up': props.admin_state,
               'default_pool_id': self._get_default_pool(ll),
               'loadbalancers' : self._get_loadbalancers(ll)}
        if res['loadbalancers']:
            res['loadbalancer_id'] = res['loadbalancers'][0]['id']

        return self._fields(res, fields)
        #return res

    def make_properties(self,**kwargs):
        props = LoadbalancerListenerType()
        for key,value in kwargs.iteritems():
            if value:
                setattr(props, key,value)
        return props

    def read(self, id):
        return self.make_dict(self._api.loadbalancer_listener_read(id=id))

    def delete(self, id):
        return self._api.loadbalancer_listener_delete(id=id)

    def create(self, lb_obj, proj_obj,name=None,**kwargs):

        id_perms = IdPermsType(enable=True)
        ll_obj = LoadbalancerListener(name, proj_obj, id_perms=id_perms,
                                  display_name=name)
        ll_uuid = str(uuid.uuid4())
        ll_obj.uuid = ll_uuid
        name = self._get_resource_name('loadbalancer-listener',
                                  proj_obj, name, ll_uuid)

        if lb_obj:
            ll_obj.set_loadbalancer(lb_obj)

        props = self.make_properties(**kwargs) 
        ll_obj.set_loadbalancer_listener_properties(props)
        if name:
            ll_obj.add_annotations(KeyValuePair(key=name, value=name))

        try:
            self._api.loadbalancer_listener_create(ll_obj)
        except RefsExistError:
            self._api.loadbalancer_listener_update(ll_obj)

        return self.make_dict(ll_obj)

class ServiceLbPoolManager(LoadBalancerBase):
    '''
        'admin_state': 'admin_state_up',
        'protocol': 'protocol',
        'loadbalancer_method': 'lb_algorithm',
        'subnet_id': 'subnet_id'
    '''
    _loadbalancer_pool_type_mapping = {
        'admin_state': 'admin_state_up',
        'protocol': 'protocol',
        'loadbalancer_method': 'lb_algorithm',
        'subnet_id': 'subnet_id'
    }

    def __init__(self,vnc,logger):
        self._api = vnc
        self.logger = logger

    def _get_listeners(self, pool):
        ll_list = []
        ll = {}
        ll_back_refs = pool.get_loadbalancer_listener_refs()
        if ll_back_refs is None:
            return None
        ll['id'] = ll_back_refs[0]['uuid']
        ll_list.append(ll)
        return ll_list

    def make_dict(self, pool, fields=None):
        res = {
            'id': pool.uuid,
            'tenant_id': pool.parent_uuid.replace('-', ''),
            'name': pool.display_name,
            'description': self._get_object_description(pool),
            'status': self._get_object_status(pool),
            'listeners': self._get_listeners(pool),
            'session_persistence': None,
        }
        if res['listeners']:
            res['listener_id'] = res['listeners'][0]['id']

        props = pool.get_loadbalancer_pool_properties()
        for key, mapping in self._loadbalancer_pool_type_mapping.iteritems():
            value = getattr(props, key, None)
            if value is not None:
                res[mapping] = value

        custom_attributes = []
        kvps = pool.get_loadbalancer_pool_custom_attributes()
        if kvps:
            custom_attributes = [{kvp.get_key(): kvp.get_value()} \
                                 for kvp in kvps.get_key_value_pair() or []]
        res['custom_attributes'] = [custom_attributes]

        if props.session_persistence:
            sp = {'type': props.session_persistence}
            if props.session_persistence == 'APP_COOKIE':
                sp['cookie_name'] = props.persistence_cookie_name
            res['session_persistence'] = sp

        # members
        res['members'] = []
        members = pool.get_loadbalancer_members()
        if members is not None:
            res['members'] = [{'id': member['uuid']} for member in members]

        # health_monitor
        hm_refs = pool.get_loadbalancer_healthmonitor_refs()
        if hm_refs is not None:
            res['healthmonitor_id'] = hm_refs[0]['uuid']

        return self._fields(res, fields)
        #return res

    def resource_list(self, tenant_id=None):
        if tenant_id:
            parent_id = str(uuid.UUID(tenant_id))
        else:
            parent_id = None
        return self._api.loadbalancer_pools_list(parent_id=parent_id)

    def read(self, id):
        return self.make_dict(self._api.loadbalancer_pool_read(id=id))

    def delete(self, id):
        return self._api.loadbalancer_pool_delete(id=id)

    def create(self, ll_obj, proj_obj, protocol, 
               name=None,lb_algorithm=None, 
               session_persistence=None,annotations=None):
        """
        Create a loadbalancer_pool object.
        """
        pool_uuid = str(uuid.uuid4())
        props = LoadbalancerPoolType()
        props.set_protocol(protocol)
        if lb_algorithm:
            props.set_loadbalancer_method(lb_algorithm)
        id_perms = IdPermsType(enable=True)
        pool_obj = LoadbalancerPool(ll_obj.name, proj_obj, uuid=pool_uuid,
                                loadbalancer_pool_properties=props,
                                id_perms=id_perms)

        if ll_obj:
            pool_exists = ll_obj.get_loadbalancer_pool_back_refs()
            if pool_exists is not None:
                raise loadbalancerv2.OnePoolPerListener(
                                     listener_id=p['listener_id'],
                                     pool_id=pool_exists[0]['uuid'])
            pool_obj.set_loadbalancer_listener(ll_obj)

        try:
            self._api.loadbalancer_pool_create(pool_obj)
        except RefsExistError:
            self._api.loadbalancer_pool_update(pool_obj)

        return self.make_dict(pool_obj)

class ServiceLbMemberManager(LoadBalancerBase):

    '''
        'admin_state': 'admin_state_up',
        'status': 'status',
        'protocol_port': 'protocol_port',
        'weight': 'weight',
        'address': 'address',
        'subnet_id': 'subnet_id'
    '''
    _loadbalancer_member_type_mapping = {
        'admin_state': 'admin_state_up',
        'status': 'status',
        'protocol_port': 'protocol_port',
        'weight': 'weight',
        'address': 'address',
        'subnet_id': 'subnet_id',
    }

    def __init__(self,vnc,logger):
        self._api = vnc
        self.logger = logger

    def make_properties(self, **kwargs):
        props = LoadbalancerMemberType()
        for key, mapping in self._loadbalancer_member_type_mapping.iteritems():
            if mapping in kwargs:
                setattr(props, key, kwargs[mapping])
        return props

    def _get_member_pool_id(self, member):
        pool_uuid = member.parent_uuid
        return pool_uuid

    def make_dict(self, member, fields=None):
        res = {'id': member.uuid,
               'name': member.name,
               'pool_id': member.parent_uuid,
               'status': self._get_object_status(member)}

        try:
            pool = self._api.loadbalancer_pool_read(id=member.parent_uuid)
            res['tenant_id'] = pool.parent_uuid.replace('-', '')
        except NoIdError:
            pass

        props = member.get_loadbalancer_member_properties()
        for key, mapping in self._loadbalancer_member_type_mapping.iteritems():
            value = getattr(props, key, None)
            if value is not None:
                res[mapping] = value

        return self._fields(res, fields)
        #return res

    def read(self, id):
        return self.make_dict(self._api.loadbalancer_member_read(id=id))

    def delete(self, id):
        return self._api.loadbalancer_member_delete(id=id)

    def create(self, pool_obj,**kwargs):
        """
        Create a loadbalancer_member object.
        """
        lm_uuid = str(uuid.uuid4())
        props = self.make_properties(**kwargs)    
        id_perms = IdPermsType(enable=True)

        member_obj = LoadbalancerMember(
            lm_uuid, pool_obj, loadbalancer_member_properties=props,
            id_perms=id_perms)
        member_obj.uuid = lm_uuid

        self._api.loadbalancer_member_create(member_obj)
        return self.make_dict(member_obj)

    def update(self, member_id,pool_id,**kwargs):
        """
        Update a loadbalancer_member object.
        'admin_state': 'admin_state_up',
        'status': 'status',
        'protocol_port': 'protocol_port',
        'weight': 'weight',
        'address': 'address',
        'subnet_id': 'subnet_id',
        """
        member_obj = self._api.loadbalancer_member_read(id=member_id)
        props = member_obj.get_loadbalancer_member_properties()
        for k,v in props.iteritems():
            if k in kwargs:
                props[k]=kwargs.get(k)
        props=self.make_properties(props)    
        member_obj.set_loadbalancer_member_properties(props)
        return self._api.loadbalancer_member_update(member_obj)

class ServiceLbHealthMonitorManager(LoadBalancerBase):

    '''
        'admin_state': 'admin_state_up',
        'monitor_type': 'type',
        'delay': 'delay',
        'timeout': 'timeout',
        'max_retries': 'max_retries',
        'http_method': 'http_method',
        'url_path': 'url_path',
        'expected_codes': 'expected_codes'
    '''

    _loadbalancer_health_type_mapping = {
        'admin_state': 'admin_state_up',
        'monitor_type': 'type',
        'delay': 'delay',
        'timeout': 'timeout',
        'max_retries': 'max_retries',
        'http_method': 'http_method',
        'url_path': 'url_path',
        'expected_codes': 'expected_codes'
    }

    def __init__(self,vnc,logger):
        self._api = vnc
        self.logger = logger

    def make_properties(self, **kwargs):
        props = LoadbalancerHealthmonitorType()
        for key, mapping in self._loadbalancer_health_type_mapping.iteritems():
            if mapping in kwargs:
                setattr(props, key, kwargs[mapping])
        return props

    def make_dict(self, healthmonitor, fields=None):
        res = {'id': healthmonitor.uuid,
               'name': healthmonitor.name,
               'tenant_id': healthmonitor.parent_uuid.replace('-', ''),
               'status': self._get_object_status(healthmonitor)}

        props = healthmonitor.get_loadbalancer_healthmonitor_properties()
        monitor_type = getattr(props, 'monitor_type')
        for key, mapping in self._loadbalancer_health_type_mapping.iteritems():
            value = getattr(props, key, None)
            if value is not None:
                if monitor_type not in ('HTTP', 'HTTPS'):
                    if mapping in ('http_method', 'url_path', 'expected_codes'):
                        continue
                res[mapping] = value

        pool_ids = []
        pool_back_refs = healthmonitor.get_loadbalancer_pool_back_refs()
        for pool_back_ref in pool_back_refs or []:
            pool_id = {}
            pool_id['pool_id'] = pool_back_ref['uuid']
            pool_ids.append(pool_id)
        res['pools'] = pool_ids

        return self._fields(res, fields)
        #return res

    def read(self,id):
        return self.make_dict(self._api.loadbalancer_healthmonitor_read(id=id))

    def delete(self,id):
        hm_obj = self._api.loadbalancer_healthmonitor_read(id=id)
        for pool_back_refs in hm_obj.get_loadbalancer_pool_back_refs() or []:
            self._api.ref_update('loadbalancer-pool', pool_back_refs['uuid'],
                'loadbalancer-healthmonitor', id, None, 'DELETE')
        return self._api.loadbalancer_healthmonitor_delete(id=id)

    def create(self,pool_id, delay, max_retries,
               probe_type, timeout, http_method=None,
               http_codes=None, http_url=None,proj_obj=None):
        props = self.make_properties(
                                    monitor_type=probe_type,
                                    delay=delay,
                                    timeout=timeout,
                                    max_retries=max_retries,
                                    http_method=http_method,
                                    url_path=http_url,
                                    expected_codes=http_codes)
        hm_uuid = str(uuid.uuid4())
        id_perms = IdPermsType(enable=True)
        monitor = LoadbalancerHealthmonitor(
            hm_uuid, proj_obj, loadbalancer_healthmonitor_properties=props,
            id_perms=id_perms)
        monitor.uuid = hm_uuid
        try:
            pool = self._api.loadbalancer_pool_read(id=pool_id)
        except NoIdError:
            return None
        hm_obj = self._api.loadbalancer_healthmonitor_create(monitor)
        self._api.ref_update('loadbalancer-pool', pool_id,
            'loadbalancer-healthmonitor', hm_uuid, None, 'ADD')
        return self.make_dict(monitor)

    def update(self,hm_id=None,
               proj_obj=None,**kwargs):
        hm_obj = self.read(id=hm_id)
        props = hm_obj.get_loadbalancer_healthmonitor_properties()
        for k,v in props.iteritems():
            if k in kwargs:
                props[k]=kwargs.get(k)
        props = self.make_properties(props)
        hm_obj.set_loadbalancer_healthmonitor_properties(props)
        return self._api.loadbalancer_healthmonitor_update(hm_obj)
                
