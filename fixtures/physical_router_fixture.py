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

     # end __init__

    def create_bgp_router(self):
        bgp_router = vnc_api_test.BgpRouter(self.name, parent_obj=self._get_ip_fabric_ri_obj())
        params = BgpRouterParams()
        params.address = self.mgmt_ip
        params.address_families = vnc_api_test.AddressFamilies(['route-target',
            'inet-vpn', 'e-vpn', 'inet6-vpn'])
        params.autonomous_system = int(self.asn)
        params.vendor = self.vendor
        params.identifier = self.mgmt_ip
        bgp_router.set_bgp_router_parameters(params)
        self.vnc_api_h.bgp_router_create(bgp_router)
        self.logger.info('Created BGP router %s with ID %s' % (
            self.bgp_router.fq_name, self.bgp_router.uuid))
        return bgp_router
    # end create_bgp_router

    def delete_bgp_router(self):
        self.vnc_api_h.bgp_router_delete(id=self.bgp_router.uuid)
        self.logger.info('Deleted BGP router : %s' % (self.bgp_router.uuid))

    def set_bgp_router(self, bgp_router):
        self.phy_device = self.vnc_api_h.physical_router_read(id=self.phy_device.uuid)
        self.phy_device.set_bgp_router(bgp_router)
        self.vnc_api_h.physical_router_update(self.phy_device)

    def delete_device(self):
        self.set_bgp_router([])
        super(PhysicalRouterFixture, self).delete_device(self)

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
        except NoIdError:
            self.bgp_router = self.create_bgp_router()

        self.set_bgp_router(self.bgp_router)

    def cleanUp(self):
        super(PhysicalRouterFixture, self).cleanUp()
        do_cleanup = True
        if self.bgp_router_already_present:
            do_cleanup = False
        if do_cleanup:
            self.delete_bgp_router()

# end PhysicalRouterFixture

if __name__ == "__main__":
    pass
