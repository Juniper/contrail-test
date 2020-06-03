from builtins import str
import vnc_api_test
from tcutils.util import retry, get_random_name
import json
import uuid
from netaddr import EUI
from vnc_api.vnc_api import NoIdError
import netaddr
import ast

class PortFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Port/VMI objects

    Optional:
    :param vn_id    : UUID of the VN
    :param fixed_ips : list of fixed ip dict
    :param mac_address
    :param security_groups
    :params extra_dhcp_opts
    :param api_type     : one of 'neutron'(default) or 'contrail'
    :param project_obj   : Project object which is to be the parent
                          object of this port
    :param vlan_id     : vlan id of sub-interface if any
    :param parent_vmi  : If this is sub-interface, instance of parent
                               VirtualMachineInterface

    Inherited parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1
    '''

    def __init__(self, *args, **kwargs):
        super(PortFixture, self).__init__(self, *args, **kwargs)
        self.vn_id = args[0] if args else kwargs.get('vn_id', None)
        self.name = kwargs.get('name') or get_random_name('vmi')
        self.fixed_ips = kwargs.get('fixed_ips', [])
        self.mac_address = kwargs.get('mac_address', [])
        self.security_groups = kwargs.get('security_groups') or []
        self.extra_dhcp_opts = kwargs.get('extra_dhcp_opts', [])
        self.api_type = kwargs.get('api_type', 'neutron')
        if self.inputs.orchestrator == 'vcenter':
            self.api_type = 'contrail'
        self.project_obj = kwargs.get('project_obj', None)
        self.binding_profile = kwargs.get('binding_profile', None)
        self.port_group_name = kwargs.get('port_group_name', None)
        self.vlan_id = kwargs.get('vlan_id', None)
        self.parent_vmi = kwargs.get('parent_vmi', None)
        self.tor_port_vlan_tag = kwargs.get('tor_port_vlan_tag', None)
        self.create_iip = kwargs.get('create_iip', True)
        self.uuid = kwargs.get('uuid', None)
        self.device_owner = kwargs.get('device_owner', None)
        self.max_flows = kwargs.get('max_flows', None)
        self.port_profiles = kwargs.get('port_profiles') or list()
        project_name = self.project_obj.name if self.project_obj else self.project_name
        self.fq_name = [self.domain, project_name, self.name]
        self.vn_obj = None
        self.created = False
        self.af = self.inputs.get_af()
        self.binding_vnic_type = kwargs.get('binding_vnic_type', None)
        if self.inputs.ns_agilio_vrouter_data or self.inputs.virtio:
            self.binding_vnic_type = kwargs.get('binding_vnic_type', 'virtio-forwarder')
            self.api_type = 'contrail'
            self.af = 'dual' if self.af == 'v6' else self.af
     # end __init__

    def read(self):
        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
            id=self.uuid)
        if self.vmi_obj.get_virtual_network_refs():
            self.vn_id = self.vmi_obj.get_virtual_network_refs()[0]['uuid']
        mac = self.vmi_obj.get_virtual_machine_interface_mac_addresses()
        self.mac_address = mac.mac_address[0]
        self.iip_objs = []
        for iip in self.vmi_obj.get_instance_ip_back_refs() or []:
            self.iip_objs.append(self.vnc_api_h.instance_ip_read(id=iip['uuid']))

    def setUp(self):
        super(PortFixture, self).setUp()
        if not self.uuid:
            try:
                obj = self.vnc_h.read_virtual_machine_interface(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.vn_obj = self.vnc_api_h.virtual_network_read(id=self.vn_id)
                if self.api_type == 'neutron':
                    self._neutron_create_port()
                else:
                    self._contrail_create_port()
                self.created = True
                self.logger.debug('Created port %s' % (self.uuid))
        self.read()
        self.add_port_profiles(self.port_profiles)

    def _neutron_create_port(self):
        if not self.neutron_handle:
            self.neutron_handle = self.get_neutron_handle()
        neutron_obj = self.neutron_handle.create_port(
            self.vn_id,
            name=self.name,
            fixed_ips=self.fixed_ips,
            mac_address=self.mac_address,
            security_groups=self.security_groups,
            extra_dhcp_opts=self.extra_dhcp_opts,
            binding_profile=self.binding_profile)
        self.neutron_obj = neutron_obj
        self.uuid = neutron_obj['id']

    def _contrail_create_port(self):
        vmi_props = vnc_api_test.VirtualMachineInterfacePropertiesType()
        if not self.project_obj:
            self.project_obj = self.vnc_api_h.project_read(id=self.project_id)
        vmi_id = str(uuid.uuid4())
        vmi_obj = vnc_api_test.VirtualMachineInterface(name=self.name,
            parent_obj=self.project_obj)
        if self.mac_address:
            mac_address_obj = vnc_api_test.MacAddressesType()
            mac_address_obj.set_mac_address([str(EUI(self.mac_address))])
            vmi_obj.set_virtual_machine_interface_mac_addresses(
                mac_address_obj)
        vmi_obj.uuid = vmi_id
        vmi_obj.add_virtual_network(self.vn_obj)

        if self.security_groups:
            for sg_id in self.security_groups:
                sg_obj = self.vnc_api_h.security_group_read(id=sg_id)
                vmi_obj.add_security_group(sg_obj)
        else:
            # Associate default SG
            default_sg_fq_name = self.project_obj.fq_name[:]
            default_sg_fq_name.append('default')
            sg_obj = self.vnc_api_h.security_group_read(
                fq_name=default_sg_fq_name)
            vmi_obj.add_security_group(sg_obj)

        if self.extra_dhcp_opts:
            # TODO
            pass

        if self.vlan_id is not None:
            vmi_props.set_sub_interface_vlan_tag(int(self.vlan_id))

        if self.parent_vmi:
            vmi_obj.add_virtual_machine_interface(self.parent_vmi)

        if self.device_owner:
            vmi_obj.set_virtual_machine_interface_device_owner(self.device_owner)

        if self.binding_profile:
            bind_kv = vnc_api_test.KeyValuePair(key='profile',
                      value=json.dumps(self.binding_profile))
            kv_pairs = vmi_obj.get_virtual_machine_interface_bindings() or\
                       vnc_api_test.KeyValuePairs()
            kv_pairs.add_key_value_pair(bind_kv)
            if self.tor_port_vlan_tag:
                vlan_kv = vnc_api_test.KeyValuePair(key='tor_port_vlan_id',
                    value=str(self.tor_port_vlan_tag))
                kv_pairs.add_key_value_pair(vlan_kv)
            if 'local_link_information' in self.binding_profile:
                vnic_kv = vnc_api_test.KeyValuePair(key='vnic_type',
                          value='baremetal')
                kv_pairs.add_key_value_pair(vnic_kv)
                vmi_obj.set_virtual_machine_interface_device_owner("baremetal:None")
                if self.port_group_name:
                    pg_kv = vnc_api_test.KeyValuePair(key='vpg',
                        value=self.port_group_name)
                    kv_pairs.add_key_value_pair(pg_kv)
            vmi_obj.set_virtual_machine_interface_bindings(kv_pairs)

        if self.binding_vnic_type:
            bind_kv = vnc_api_test.KeyValuePair(key='vnic_type', value=self.binding_vnic_type)
            kv_pairs = vmi_obj.get_virtual_machine_interface_bindings() or\
                       vnc_api_test.KeyValuePairs()
            kv_pairs.add_key_value_pair(bind_kv)
            vmi_obj.set_virtual_machine_interface_bindings(kv_pairs)
        vmi_obj.set_virtual_machine_interface_properties(vmi_props)

        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_create(vmi_obj)
        self.uuid = vmi_id

        self.iip_objs = []
        if self.create_iip == False:
            return
        if self.fixed_ips:
            for fixed_ip in self.fixed_ips:
                iip_id = str(uuid.uuid4())
                iip_obj = vnc_api_test.InstanceIp(name=iip_id,
                                     subnet_id=fixed_ip['subnet_id'])
                iip_obj.uuid = iip_id
                iip_obj.add_virtual_machine_interface(vmi_obj)
                iip_obj.add_virtual_network(self.vn_obj)
                if fixed_ip.get("ip_address", None):
                    iip_obj.set_instance_ip_address(fixed_ip['ip_address'])
                if fixed_ip.get("instance_ip_secondary", False):
                    iip_obj.instance_ip_secondary = True
                id = self.vnc_api_h.instance_ip_create(iip_obj)
                iip_obj = self.vnc_api_h.instance_ip_read(id=id)
                self.iip_objs.append(iip_obj)
        else:
            iip_id = str(uuid.uuid4())
            if self.inputs.ns_agilio_vrouter_data or self.af in ['v6', 'dual']:
                iip_obj = vnc_api_test.InstanceIp(name=iip_id, instance_ip_family='v4')
            else:
                iip_obj = vnc_api_test.InstanceIp(name=iip_id)
            iip_obj.uuid = iip_id
            iip_obj.add_virtual_machine_interface(vmi_obj)
            iip_obj.add_virtual_network(self.vn_obj)
            self.vnc_api_h.instance_ip_create(iip_obj)
            if self.af in ['v6', 'dual']:
                iip_id2 = str(uuid.uuid4())
                iip_obj2 = vnc_api_test.InstanceIp(name=iip_id2, instance_ip_family='v6')
                iip_obj2.uuid = iip_id2
                iip_obj2.add_virtual_machine_interface(vmi_obj)
                iip_obj2.add_virtual_network(self.vn_obj)
                self.vnc_api_h.instance_ip_create(iip_obj2)
    # end _contrail_create_port

    def cleanUp(self, force=False):
        if self.created or force:
            try: 
                if self.api_type == 'neutron':
                    self._neutron_delete_port()
                else:
                    self._contrail_delete_port()
                self.logger.info('Deleted port %s' % (self.uuid))
            except NoIdError:
                pass
        super(PortFixture, self).cleanUp()

    def _neutron_delete_port(self):
        self.neutron_handle.delete_port(self.uuid)

    def _contrail_delete_port(self):
        vmi_iips = self.vmi_obj.get_instance_ip_back_refs()
        for vmi_iip in vmi_iips or []:
            vmi_iip_uuid = vmi_iip['uuid']
            self.vnc_api_h.instance_ip_delete(id=vmi_iip_uuid)
        self.vnc_api_h.virtual_machine_interface_delete(id=self.uuid)

    def verify_on_setup(self):
        if not self.verify_port_in_api_server():
            self.logger.error('VMI %s verification in API Server failed'%self.uuid)
            return False
        else:
            self.logger.info('VMI %s verification in API Server passed'%self.uuid)
        return True

    @retry(delay=2, tries=5)
    def verify_port_in_api_server(self):
        api_h = self.connections.api_server_inspect
        vmi = api_h.get_cs_vmi(self.uuid)
        if not vmi:
            self.logger.warn('Unable to fetch VMI %s from API server'%self.uuid)
            return False
        if self.binding_profile:
            bindings = vmi.get_bindings()
            if bindings['profile'] != json.dumps(self.binding_profile
                    ) and json.dumps(ast.literal_eval(bindings['profile'])) != json.dumps(self.binding_profile):
                self.logger.warn('VMI binding profile doesnt match.'
                                 'Expected %s actual %s for VMI %s'%(
                                 self.binding_profile, bindings['profile'], self.uuid))
                return False
        return True

    def disable_policy(self):
        return self.set_policy(True)

    def enable_policy(self):
        return self.set_policy(False)

    def set_policy(self, value):
        vmi_obj = self.vnc_h.virtual_machine_interface_read(id=self.uuid)
        vmi_obj.set_virtual_machine_interface_disable_policy(bool(value))
        self.vnc_h.virtual_machine_interface_update(vmi_obj)

    def set_igmp_config(self, value):
        vmi_obj = self.vnc_h.virtual_machine_interface_read(self.uuid)
        vmi_obj.set_igmp_enable(bool(value))
        self.vnc_h.virtual_machine_interface_update(vmi_obj)

    def get_igmp_enable(self, value):
        vmi_obj = self.vnc_h.virtual_machine_interface_read(self.uuid)
        igmp_enable = vmi_obj.get_igmp_enable()
        return igmp_enable

    def get_vpg_fqname(self):
        vmi_obj = self.vnc_h.read_virtual_machine_interface(id=self.uuid,
            fields='virtual_port_group_back_refs')
        vpg = vmi_obj.get_virtual_port_group_back_refs()
        if not vpg:
            return None
        return vpg[0]['to']

    def update_bms(self, binding_profile, port_group_name=None):
        vmi_obj = self.vnc_h.read_virtual_machine_interface(id=self.uuid)
        bind_kv = vnc_api_test.KeyValuePair(key='profile',
                  value=json.dumps(binding_profile))
        kv_pairs = vmi_obj.get_virtual_machine_interface_bindings() or\
                   vnc_api_test.KeyValuePairs()
        kv_pairs.add_key_value_pair(bind_kv)
        if 'local_link_information' in self.binding_profile:
            vnic_kv = vnc_api_test.KeyValuePair(key='vnic_type',
                      value='baremetal')
            kv_pairs.add_key_value_pair(vnic_kv)
            if port_group_name:
                pg_kv = vnc_api_test.KeyValuePair(key='vpg',
                    value=port_group_name)
                kv_pairs.add_key_value_pair(pg_kv)
            vmi_obj.set_virtual_machine_interface_device_owner("baremetal:None")
        vmi_obj.set_virtual_machine_interface_bindings(kv_pairs)
        self.vnc_h.virtual_machine_interface_update(vmi_obj)

    def update_vlan_id(self, vlan_id):
        vmi_obj = self.vnc_h.read_virtual_machine_interface(id=self.uuid)
        vmi_props = vmi_obj.get_virtual_machine_interface_properties() \
            or vnc_api_test.VirtualMachineInterfacePropertiesType()
        vmi_props.set_sub_interface_vlan_tag(vlan_id)
        vmi_obj.set_virtual_machine_interface_properties(vmi_props)
        self.vnc_h.virtual_machine_interface_update(vmi_obj)
        self.vlan_id = vlan_id

    def verify_port_in_control_node_ifmap(self):
        pass

    def verify_port_in_control_node(self):
        pass

    def verify_port_in_agent(self):
        pass

    def verify_port_in_agent_ifmap(self):
        pass

    def add_fat_flow(self, fat_flow_config):
        '''
        fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        self.vnc_h.add_fat_flow_to_vmi(self.uuid, fat_flow_config)

        return True

    def remove_fat_flow(self, fat_flow_config):
        '''
        fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        self.vnc_h.remove_fat_flow_on_vmi(self.uuid, fat_flow_config)

        return True

    def add_interface_route_table(self, intf_route_table_obj):
        '''
        Adds interface static routes to a port

        Args:
        intf_route_table_obj:  InterfaceRouteTable instance
        '''
        self.vnc_h.bind_vmi_to_interface_route_table(self.uuid,
                                                     intf_route_table_obj)
    # end add_interface_route_table

    def del_interface_route_table(self, intf_route_table_uuid):
        '''Unbind intf_route_table_obj from port
        intf_route_table_obj is InterfaceRouteTable instance
        '''
        self.vnc_h.unbind_vmi_from_interface_route_table(
            self.uuid, intf_route_table_uuid)
    # end del_interface_route_table

    def get_ip_addresses(self):
        return [iip.instance_ip_address for iip in self.iip_objs]

    def set_max_flows(self, max_flows=None):
        if max_flows is None:
            max_flows = self.max_flows

        self.logger.info('Setting Max Flows of VMI(%s)-uuid %s to %s' % (
            self.name, self.uuid, max_flows))
        vnc_lib = self.vnc_api_h
        vmi_obj = vnc_lib.virtual_machine_interface_read(id=self.uuid)
        vmi_properties_obj = vmi_obj.get_virtual_machine_interface_properties() \
            or vnc_api_test.VirtualMachineInterfacePropertiesType()
        vmi_properties_obj.set_max_flows(int(max_flows))
        vmi_obj.set_virtual_machine_interface_properties(vmi_properties_obj)
        return vnc_lib.virtual_machine_interface_update(vmi_obj)

    def delete_max_flows(self):

        self.logger.info('Deleting Max Flows of VMI(%s)-uuid %s' % (self.name, self.uuid))
        vnc_lib = self.vnc_api_h
        vmi_obj = vnc_lib.virtual_machine_interface_read(id=self.uuid)
        vmi_properties_obj = vmi_obj.get_virtual_machine_interface_properties() \
            or vnc_api_test.VirtualMachineInterfacePropertiesType()
        vmi_properties_obj.set_max_flows(int(0))
        vmi_obj.set_virtual_machine_interface_properties(vmi_properties_obj)
        return vnc_lib.virtual_machine_interface_update(vmi_obj)

    def get_max_flows(self):
        vmi_obj = vnc_lib.virtual_machine_interface_read(id=self.uuid)
        vmi_properties_obj = vmi_obj.get_virtual_machine_interface_properties()
        if vmi_properties_obj:
            return vmi_properties_obj['max_flows']
        else:
            return None

    def add_port_profiles(self, port_profiles):
        for pp_uuid in port_profiles:
            self.vnc_h.assoc_port_profile_to_vmi(pp_uuid, self.uuid)
        self.port_profiles = list(set(self.port_profiles).union(
                                  set(port_profiles)))

    def delete_port_profiles(self, port_profiles):
        for pp_uuid in port_profiles:
            self.vnc_h.disassoc_port_profile_from_vmi(pp_uuid, self.uuid)

    def add_security_groups(self, security_groups):
        for sg_uuid in security_groups:
            self.vnc_h.add_security_group(sg_id=sg_uuid, vmi_id=self.uuid)

    def delete_security_groups(self, security_groups):
        for sg_uuid in security_groups:
            self.vnc_h.remove_security_group(sg_id=sg_uuid, vmi_id=self.uuid)

# end PortFixture

if __name__ == "__main__":
    vn_id = '1c83bed1-7d24-4414-9aa2-9d92975bc86f'
    subnet_id = '49fea486-57ab-4056-beb3-d311a385814e'
#    port_fixture = PortFixture(vn_id=vn_id)
    port_fixture = PortFixture(vn_id, auth_server_ip='10.204.216.184',
                               cfgm_ip='10.204.216.184',
                               api_type='contrail',
                               project_id=get_dashed_uuid('24c8d6f768c843a2ac83f5a8ff847073'))
#    port_fixture.setUp()
    port_fixture2 = PortFixture(vn_id=vn_id, api_type='contrail', fixed_ips=[
                                {'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture2.setUp()
