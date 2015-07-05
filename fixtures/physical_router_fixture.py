from netaddr import *

import vnc_api_test
from pif_fixture import PhysicalInterfaceFixture

class PhysicalRouterFixture(vnc_api_test.VncLibFixture):

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
    :tunnel_ip      : Tunnel IP (for vtep)
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
        self.ssh_username = kwargs.get('ssh_username','root')
        self.ssh_password = kwargs.get('ssh_password','Embe1mpls')
        self.tunnel_ip = kwargs.get('tunnel_ip', self.mgmt_ip)
        self.ports = kwargs.get('ports', [])

        self.bgp_router = None
        self.phy_router = None

        self.already_present = False
        self.physical_port_fixtures = {}

     # end __init__

    def _get_ip_fabric_ri_obj(self):
        rt_inst_obj = self.vnc_api_h.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        return rt_inst_obj

    # end _get_ip_fabric_ri_obj

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

    def create_physical_router(self):
        pr = PhysicalRouter(self.name)
        pr.physical_router_management_ip = self.mgmt_ip
        pr.physical_router_vendor_name = self.vendor
        pr.physical_router_product_name = self.model
        pr.physical_router_vnc_managed = True
        uc = UserCredentials(self.ssh_username, self.ssh_password)
        pr.set_physical_router_user_credentials(uc)
        pr_id = self.vnc_api_h.physical_router_create(pr)
        self.logger.info('Created Physical router %s with ID %s' % (
            pr.fq_name, pr.uuid))
        return pr

    def set_bgp_router(self, bgp_router):
        self.phy_router.set_bgp_router(bgp_router)
        self.vnc_api_h.physical_router_update(self.phy_router)


    def delete_router(self):
        self.phy_router = self.vnc_api_h.physical_router_read(id=self.phy_router.uuid)
        self.phy_router.set_bgp_router([])
        self.vnc_api_h.physical_router_update(self.phy_router)
        self.vnc_api_h.physical_router_delete(id=self.phy_router.uuid)
        self.logger.info('Deleted physical router : %s' % (self.phy_router.uuid))

        self.vnc_api_h.bgp_router_delete(id=self.bgp_router.uuid)
        self.logger.info('Deleted BGP router : %s' % (self.bgp_router.uuid))

    def setUp(self):
        super(PhysicalRouterFixture, self).setUp()
        pr_fq_name = ['default-global-system-config', self.name]
        try:
            self.phy_router = self.vnc_api_h.physical_router_read(
                fq_name=pr_fq_name)
            self.already_present = True
            self.logger.info('Physical router %s already present' % (
                pr_fq_name))
        except NoIdError:        
            self.phy_router = self.create_physical_router()

        bgp_fq_name = ['default-domain', 'default-project',
                       'ip-fabric', '__default__', self.name]
        try:
            self.bgp_router = self.vnc_api_h.bgp_router_read(
                fq_name=bgp_fq_name)
            self.already_present = True
            self.logger.info('BGP router %s already present' % (
                bgp_fq_name))
        except NoIdError:
            self.bgp_router = self.create_bgp_router()

        self.set_bgp_router(self.bgp_router)

        ## Add physical interfaces if any
        #if self.ports:
        #    self.physical_port_fixtures = self.add_physical_ports()
        #    self.addCleanup(self.delete_physical_ports)

    def setup_physical_ports(self):
        self.physical_port_fixtures = self.add_physical_ports()
        self.addCleanup(self.delete_physical_ports)

    def cleanUp(self):
        super(PhysicalRouterFixture, self).cleanUp()
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.info('Skipping deletion of routers %s, %s' % (
                self.bgp_router.fq_name, self.phy_router.fq_name))
        if do_cleanup:
            self.delete_router()
            self.logger.info('Deleted routers : %s, %s' % (
                self.bgp_router.fq_name, self.phy_router.fq_name))

    def add_virtual_network(self, vn_id):
        self.logger.debug('Adding VN %s to physical router %s' % (
            vn_id, self.name))
        self.phy_router = self.vnc_api_h.physical_router_read(id= self.phy_router.uuid)
        vn_obj = self.vnc_api_h.virtual_network_read(id = vn_id)
        self.phy_router.add_virtual_network(vn_obj)
        self.vnc_api_h.physical_router_update(self.phy_router)

    def delete_virtual_network(self, vn_id):
        self.logger.debug('Removing VN %s from physical router %s' % (
            vn_id, self.name))
        self.phy_router = self.vnc_api_h.physical_router_read(id= self.phy_router.uuid)
        vn_ref_list=[]
        for x in self.phy_router.get_virtual_network_refs():
            if not x['uuid'] == vn_id :
                vn_ref_list.append(x)
        self.phy_router.set_virtual_network_list(vn_ref_list)
        self.vnc_api_h.physical_router_update(self.phy_router)

    def add_physical_port(self, port_name):
        pif_fixture = PhysicalInterfaceFixture(port_name,
                device_id=self.phy_router.uuid,
                connections=self.connections)
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
            physical_port_fixtures[port]= self.add_physical_port(port)
        return physical_port_fixtures
    # end add_physical_ports

# end PhysicalRouterFixture

if __name__ == "__main__":
    pass
