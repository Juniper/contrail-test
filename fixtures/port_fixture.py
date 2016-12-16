import vnc_api_test
from tcutils.util import retry
import json
import uuid
from netaddr import EUI
import netaddr

class PortFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Port/VMI objects

    Mandatory:
    :param vn_id    : UUID of the VN

    Optional:
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
        self.vn_id = args[0]
        self.fixed_ips = kwargs.get('fixed_ips', [])
        self.mac_address = kwargs.get('mac_address', [])
        self.security_groups = kwargs.get('security_groups', [])
        self.extra_dhcp_opts = kwargs.get('extra_dhcp_opts', [])
        self.api_type = kwargs.get('api_type', 'neutron')
        self.project_obj = kwargs.get('project_obj', None)
        self.binding_profile = kwargs.get('binding_profile', None)
        self.vlan_id = kwargs.get('vlan_id', None)
        self.parent_vmi = kwargs.get('parent_vmi', None)
        self.vn_obj = None
     # end __init__

    def setUp(self):
        super(PortFixture, self).setUp()
        self.vn_obj = self.vnc_api_h.virtual_network_read(id=self.vn_id)

        if self.api_type == 'neutron':
            self._neutron_create_port()
        else:
            self._contrail_create_port()
        #Sandipd:This code was crashing while creating port as part of 
        #vcenter gateway testing.Hence handled the exception as the mac 
        #not needed to be obtained always,its passed as an argument to the fixture 
        try:
            self.neutron_handle = self.get_neutron_handle()
            self.obj = self.neutron_handle.get_port(self.uuid)
            self.mac_address = self.obj['mac_address']
        except Exception as e:
            pass
        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
            id=self.uuid)
        self.logger.debug('Created port %s' % (self.uuid))

    def _neutron_create_port(self):
        if not self.neutron_handle:
            self.neutron_handle = self.get_neutron_handle()
        neutron_obj = self.neutron_handle.create_port(
            self.vn_id,
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
        vmi_obj = vnc_api_test.VirtualMachineInterface(name=vmi_id,
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

        if self.vlan_id:
            vmi_props.set_sub_interface_vlan_tag(int(self.vlan_id))

        if self.parent_vmi:
            vmi_obj.add_virtual_machine_interface(self.parent_vmi)

        if self.binding_profile:
            bind_kv = vnc_api_test.KeyValuePair(key='profile', value=str(self.binding_profile))
            kv_pairs = vmi_obj.get_virtual_machine_interface_bindings() or\
                       vnc_api_test.KeyValuePairs()
            kv_pairs.add_key_value_pair(bind_kv)
            vmi_obj.set_virtual_machine_interface_bindings(kv_pairs)

        vmi_obj.set_virtual_machine_interface_properties(vmi_props)
        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_create(vmi_obj)
        self.uuid = vmi_id

        if self.fixed_ips:
            for fixed_ip in self.fixed_ips:
                iip_id = str(uuid.uuid4())
                iip_obj = vnc_api_test.InstanceIp(name=iip_id,
                                     subnet_id=fixed_ip['subnet_id'])
                iip_obj.uuid = iip_id
                iip_obj.add_virtual_machine_interface(vmi_obj)
                iip_obj.add_virtual_network(self.vn_obj)
                iip_obj.set_instance_ip_address(fixed_ip['ip_address'])
                self.vnc_api_h.instance_ip_create(iip_obj)
        else:
            iip_id = str(uuid.uuid4())
            iip_obj = vnc_api_test.InstanceIp(name=iip_id)
            iip_obj.uuid = iip_id
            iip_obj.add_virtual_machine_interface(vmi_obj)
            iip_obj.add_virtual_network(self.vn_obj)
            self.vnc_api_h.instance_ip_create(iip_obj)
    # end _contrail_create_port

    def cleanUp(self):
        super(PortFixture, self).cleanUp()
        if self.api_type == 'neutron':
            self._neutron_delete_port()
        else:
            self._contrail_delete_port()
        self.logger.info('Deleted port %s' % (self.uuid))

    def _neutron_delete_port(self):
        self.neutron_handle.delete_port(self.uuid)

    def _contrail_delete_port(self):
        vmi_iips = self.vmi_obj.get_instance_ip_back_refs()
        for vmi_iip in vmi_iips:
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
            if bindings['profile'] != json.dumps(self.binding_profile):
                self.logger.warn('VMI binding profile doesnt match.'
                                 'Expected %s actual %s for VMI %s'%(
                                 self.binding_profile, bindings['profile'], self.uuid))
                return False
        return True

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

    def get_ip(self, subnet_id):
        fixed_ips = self.obj['fixed_ips']
        ip = [x['ip_address'] for x in fixed_ips if x['subnet_id'] == subnet_id]
        if ip:
            return ip[0]
        else :
            return None
    # end get_ip
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
    port_fixture.get_ip(subnet_id)
    port_fixture2 = PortFixture(vn_id=vn_id, api_type='contrail', fixed_ips=[
                                {'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture2.setUp()
