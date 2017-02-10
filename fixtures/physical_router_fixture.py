from netaddr import *

import vnc_api_test
from pif_fixture import PhysicalInterfaceFixture
from physical_device_fixture import PhysicalDeviceFixture

class PhysicalRouterFixture(PhysicalDeviceFixture):

    '''Fixture to manage Physical Router objects

    Mandatory:
    :param name   : name of the device
    :param mgmt_ip  : Management IP

    Optional:
    :param vendor : juniper
    :param model  : mx
    :param asn    : default is 64512
    :param ssh_username : Login username to ssh, default is root
    :param ssh_password : Login password, default is Embe1mpls
    :param :tunnel_ip      : Tunnel IP (for vtep)
    :ports          : List of Ports which are available to use

    Inherited optional parameters:
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
        super(PhysicalRouterFixture, self).__init__(self, *args, **kwargs)
        self.name = args[0]
        self.mgmt_ip = args[1]
        self.vendor = kwargs.get('vendor', 'juniper')
        self.model = kwargs.get('model','mx')
        self.asn = kwargs.get('asn','64512')
        self.tunnel_ip = kwargs.get('tunnel_ip', self.mgmt_ip)
        self.ports = kwargs.get('ports', [])

        self.bgp_router = None
        self.bgp_router_already_present = False
        if self.inputs.verify_thru_gui():
            from webui_test import WebuiTest
            self.webui = WebuiTest(self.connections, self.inputs)
            self.kwargs = kwargs
     # end __init__

    def create_bgp_router(self):
        bgp_router = vnc_api_test.BgpRouter(self.name, parent_obj=self._get_ip_fabric_ri_obj())
        params = vnc_api_test.BgpRouterParams()
        params.address = self.tunnel_ip
        params.address_families = vnc_api_test.AddressFamilies(['route-target',
            'inet-vpn', 'e-vpn', 'inet6-vpn'])
        params.autonomous_system = int(self.asn)
        params.vendor = self.vendor
        params.identifier = self.mgmt_ip
        bgp_router.set_bgp_router_parameters(params)
        bgp_router_id = self.vnc_api_h.bgp_router_create(bgp_router)
        bgp_router_obj = self.vnc_api_h.bgp_router_read(id=bgp_router_id)
        self.logger.info('Created BGP router %s with ID %s' % (
            bgp_router_obj.fq_name, bgp_router_obj.uuid))
        return bgp_router_obj
    # end create_bgp_router

    def delete_bgp_router(self):
        self.vnc_api_h.bgp_router_delete(id=self.bgp_router.uuid)
        self.logger.info('Deleted BGP router : %s' % (self.bgp_router.uuid))

    def add_bgp_router(self, bgp_router):
        self.phy_device = self.vnc_api_h.physical_router_read(id=self.phy_device.uuid)
        self.phy_device.add_bgp_router(bgp_router)
        self.vnc_api_h.physical_router_update(self.phy_device)

    def unbind_bgp_router(self, bgp_router):
        self.phy_device = self.vnc_api_h.physical_router_read(id=self.phy_device.uuid)
        self.phy_device.del_bgp_router(bgp_router)
        self.vnc_api_h.physical_router_update(self.phy_device)

    def delete_device(self):
        self.phy_device = self.vnc_api_h.physical_router_read(id=self.phy_device.uuid)
        self.phy_device.del_bgp_router(self.bgp_router)
        self.vnc_api_h.physical_router_update(self.phy_device)

        super(PhysicalRouterFixture, self).delete_device()

    def setUp(self):
        super(PhysicalRouterFixture, self).setUp()

        bgp_fq_name = ['default-domain', 'default-project',
                       'ip-fabric', '__default__', self.name]
        try:
            self.bgp_router = self.vnc_api_h.bgp_router_read(
                fq_name=bgp_fq_name)
            self.already_present = True
            self.logger.info('BGP router %s already present' % (
                bgp_fq_name))
            self.bgp_router_already_present = True
        except vnc_api_test.NoIdError:
            if self.inputs.is_gui_based_config():
                self.bgp_router = self.webui.create_bgp_router(self)
            else:
                self.bgp_router = self.create_bgp_router()
        if not self.inputs.is_gui_based_config():
            self.add_bgp_router(self.bgp_router)
        self.router_session = self.get_connection_obj(self.vendor,
            host=self.mgmt_ip,
            username=self.ssh_username,
            password=self.ssh_password,
            logger=self.logger)

    def cleanUp(self):
        super(PhysicalRouterFixture, self).cleanUp()
        do_cleanup = True
        if self.bgp_router_already_present:
            do_cleanup = False
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_bgp_router(self)
            else:
                self.delete_bgp_router()

    def get_irb_mac(self):
        return self.router_session.get_mac_address('irb')

    def get_virtual_gateway_mac(self, ip_address):
        return self.router_session.get_mac_in_arp_table(ip_address)

# end PhysicalRouterFixture

if __name__ == "__main__":
    pass
