from netaddr import *

import vnc_api_test
from pif_fixture import PhysicalInterfaceFixture
from common.device_connection import ConnectionFactory
try:
    from webui_test import *
except ImportError:
    pass

class PhysicalDeviceFixture(vnc_api_test.VncLibFixture):

    '''Fixture to manage Physical device objects

    Mandatory:
    :param name   : name of the device
    :param mgmt_ip  : Management IP

    Optional:
    :param vendor : juniper
    :param model  : mx
    :param asn    : default is 64512
    :param ssh_username : Login username to ssh, default is root
    :param ssh_password : Login password, default is Embe1mpls
    :param tunnel_ip    : Tunnel IP (for vtep)
    :param ports        : List of Ports which are available to use

    Inherited optional parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1
    :param logger         : logger object
    '''

    def __init__(self, *args, **kwargs):
        super(PhysicalDeviceFixture, self).__init__(*args, **kwargs)
        self.name = args[0]
        self.mgmt_ip = args[1]
        self.vendor = kwargs.get('vendor', None)
        self.model = kwargs.get('model', None)
        self.asn = kwargs.get('asn', None)
        self.ssh_username = kwargs.get('ssh_username', 'root')
        self.ssh_password = kwargs.get('ssh_password', 'Embe1mpls')
        self.tunnel_ip = kwargs.get('tunnel_ip', None)
        self.ports = kwargs.get('ports', [])
        self.device_details = {}

        self.phy_device = None
        self.nc_handle = None

        self.already_present = False
        self.physical_port_fixtures = {}

        if self.inputs.verify_thru_gui():
            connections = kwargs.get('connections', None)
            self.webui = WebuiTest(connections, self.inputs)
            self.kwargs = kwargs
     # end __init__

    def _get_ip_fabric_ri_obj(self):
        rt_inst_obj = self.vnc_api_h.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        return rt_inst_obj

    # end _get_ip_fabric_ri_obj

    def create_physical_device(self):
        pr = vnc_api_test.PhysicalRouter(self.name)
        pr.physical_router_management_ip = self.mgmt_ip
        pr.physical_router_dataplane_ip = self.tunnel_ip
        pr.physical_router_vendor_name = self.vendor
        pr.physical_router_product_name = self.model
        pr.physical_router_vnc_managed = True
        uc = vnc_api_test.UserCredentials(self.ssh_username, self.ssh_password)
        pr.set_physical_router_user_credentials(uc)
        if self.inputs.is_gui_based_config():
            self.webui.create_physical_router(self)
        else:
            pr_id = self.vnc_api_h.physical_router_create(pr)
        self.logger.info('Created Physical device %s with ID %s' % (
            pr.fq_name, pr.uuid))
        return pr

    def delete_device(self):
        self.vnc_api_h.physical_router_delete(id=self.phy_device.uuid)
        self.logger.info('Deleted physical device : %s, UUID %s' %
            (self.phy_device.fq_name, self.phy_device.uuid))

    def setUp(self):
        super(PhysicalDeviceFixture, self).setUp()
        pr_fq_name = ['default-global-system-config', self.name]
        try:
            self.phy_device = self.vnc_api_h.physical_router_read(
                fq_name=pr_fq_name)
            self.already_present = True
            self.logger.info('Physical device %s already present' % (
                pr_fq_name))
        except vnc_api_test.NoIdError:
            self.phy_device = self.create_physical_device()
        if self.inputs:
            self.device_details = self.get_device_details(
                self.inputs.physical_routers_data)

    def get_device_details(self, physical_routers_data):
        '''
            Returns the device dict of the ToR 
        '''
        for (device_name, device_dict) in physical_routers_data.iteritems():
            if device_name == self.name:
                return device_dict
    # end get_device_details

    def setup_physical_ports(self):
        self.physical_port_fixtures = self.add_physical_ports()
        self.addCleanup(self.delete_physical_ports)

    def cleanUp(self):
        super(PhysicalDeviceFixture, self).cleanUp()
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.info('Skipping deletion of device %s' % (
                self.phy_device.fq_name))
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_physical_router(self)
            else:
                self.delete_device()

    def add_virtual_network(self, vn_id):
        self.logger.debug('Adding VN %s to physical device %s' % (
            vn_id, self.name))
        self.phy_device = self.vnc_api_h.physical_router_read(
            id=self.phy_device.uuid)
        vn_obj = self.vnc_api_h.virtual_network_read(id=vn_id)
        self.phy_device.add_virtual_network(vn_obj)
        self.vnc_api_h.physical_router_update(self.phy_device)

    def delete_virtual_network(self, vn_id):
        self.logger.debug('Removing VN %s from physical device %s' % (
            vn_id, self.name))
        self.phy_device = self.vnc_api_h.physical_router_read(
            id=self.phy_device.uuid)
        vn_ref_list = []
        for x in self.phy_device.get_virtual_network_refs():
            if not x['uuid'] == vn_id:
                vn_ref_list.append(x)
        self.phy_device.set_virtual_network_list(vn_ref_list)
        self.vnc_api_h.physical_router_update(self.phy_device)

    def add_physical_port(self, port_name):
        pif_fixture = PhysicalInterfaceFixture(port_name,
                                               device_id=self.phy_device.uuid,
                                               connections=self.connections,
                                               cfgm_ip=self.cfgm_ip,
                                               auth_server_ip=self.auth_server_ip)
        pif_fixture.setUp()
        return pif_fixture

    def delete_physical_port(self, port_name):
        self.physical_port_fixtures[port_name].cleanUp()

    def delete_physical_ports(self):
        for port in self.ports:
            self.delete_physical_port(port)

    def add_physical_ports(self):
        physical_port_fixtures = {}
        for port in self.ports:
            physical_port_fixtures[port] = self.add_physical_port(port)
        return physical_port_fixtures
    # end add_physical_ports

    def get_connection_obj(self, *args, **kwargs):
        self.conn_obj = ConnectionFactory.get_connection_obj(
            *args, **kwargs)
        self.conn_obj.connect()
        return self.conn_obj
    # end get_connection_obj

    
# end PhysicalDeviceFixture

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
