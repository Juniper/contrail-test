from vnc_api_test import *


class PortFixture(VncLibFixture):

    '''Fixture to handle Port/VMI objects

    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth-server_ip : default is 127.0.0.1

    :param fixed_ips : list of fixed ip dict
    :param mac_address
    :param security_groups
    :params extra_dhcp_opts
    :param api_type : one of 'neutron'(default) or 'contrail'
    '''

    def __init__(self, *args, **kwargs):
        super(PortFixture, self).__init__(self, *args, **kwargs)
        self.vn_id = args[0]
        self.fixed_ips = kwargs.get('fixed_ips', [])
        self.mac_address = kwargs.get('mac_address', [])
        self.security_groups = kwargs.get('security_groups', [])
        self.extra_dhcp_opts = kwargs.get('extra_dhcp_opts', [])
        self.api_type = kwargs.get('api_type', 'neutron')

        self.vn_obj = None
     # end __init__

    def setUp(self):
        super(PortFixture, self).setUp()
        self.vn_obj = self.vnc_api_h.virtual_network_read(id=self.vn_id)
        
        if self.api_type == 'neutron':
            self._neutron_create_port()
        else:
            self._contrail_create_port()
        self.neutron_handle = self.get_neutron_handle()
        self.obj = self.neutron_handle.get_port(self.uuid)
        self.mac_address = self.obj['mac_address']
        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
            id=self.uuid)
        self.logger.info('Created port %s' % (self.uuid))

    def _neutron_create_port(self):
        neutron_obj = self.neutron_handle.create_port(
            self.vn_id,
            fixed_ips=self.fixed_ips,
            mac_address=self.mac_address,
            security_groups=self.security_groups,
            extra_dhcp_opts=self.extra_dhcp_opts)
        self.neutron_obj = neutron_obj
        self.uuid = neutron_obj['id']

    def _contrail_create_port(self):
        proj_obj = self.vnc_api_h.project_read(id=self.project_id)
        vmi_id = str(uuid.uuid4())
        vmi_obj = VirtualMachineInterface(name=vmi_id, parent_obj=proj_obj)
        if self.mac_address:
            mac_address_obj = MacAddressesType()
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
            default_sg_fq_name = proj_obj.fq_name[:]
            default_sg_fq_name.append('default')
            sg_obj = self.vnc_api_h.security_group_read(
                fq_name=default_sg_fq_name)
            vmi_obj.add_security_group(sg_obj)

        if self.extra_dhcp_opts:
            # TODO
            pass

        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_create(vmi_obj)
        self.uuid = vmi_id

        if self.fixed_ips:
            for fixed_ip in self.fixed_ips:
#                ip_address_obj = IpAddressesType(ip_address=fixed_ip['ip_address'])
                iip_id = str(uuid.uuid4())
                iip_obj = InstanceIp(name=iip_id,
                                     # instance_ip_address=ip_address_obj,
                                     subnet_id=fixed_ip['subnet_id'])
                iip_obj.uuid = iip_id
                iip_obj.add_virtual_machine_interface(vmi_obj)
                iip_obj.add_virtual_network(self.vn_obj)
                iip_obj.set_instance_ip_address(fixed_ip['ip_address'])
                self.vnc_api_h.instance_ip_create(iip_obj)
        else:
            iip_id = str(uuid.uuid4())
            iip_obj = InstanceIp(name=iip_id)
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

# end PortFixture

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
    vn_id = '1c83bed1-7d24-4414-9aa2-9d92975bc86f'
    subnet_id = '49fea486-57ab-4056-beb3-d311a385814e'
    port_fixture = PortFixture(vn_id=vn_id)
#    port_fixture.setUp()
    port_fixture1 = PortFixture(vn_id=vn_id, api_type='contrail')
#    port_fixture1.setUp()
    port_fixture2 = PortFixture(vn_id=vn_id, api_type='contrail', fixed_ips=[
                                {'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture2.setUp()
