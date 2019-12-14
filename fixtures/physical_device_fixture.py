from netaddr import *
import re
import vnc_api_test
from pif_fixture import PhysicalInterfaceFixture
from common.device_connection import ConnectionFactory
from tcutils.util import retry
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
    :param model  : mx
    :param ssh_username : Login username to ssh, default is root
    :param ssh_password : Login password, default is Embe1mpls
    :param tunnel_ip    : Tunnel IP (for vtep)
    :param peer_ip      : BGP Peer IP (mostly tunnel ip)
    :param lldp         : List of Ports which are available to use
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
        if args:
            self.name = args[0]
            self.mgmt_ip = args[1]
        else:
            self.name = kwargs['name']
            self.mgmt_ip = kwargs.get('mgmt_ip')
        self.tunnel_ip = kwargs.get('tunnel_ip')
        self.peer_ip = kwargs.get('peer_ip') or self.tunnel_ip
        self.dm_managed = kwargs.get('dm_managed', True)
        self.ssh_username = kwargs.get('ssh_username', 'root')
        self.ssh_password = kwargs.get('ssh_password', 'Embe1mpls')
        self.lldp = kwargs.get('lldp', True)
        self.role = kwargs.get('role')
        self.model = kwargs.get('model', None)
        self.ports = kwargs.get('ports', [])
        self.device_details = {}

        self.created = False
        self.physical_port_fixtures = {}
        csn = kwargs.get('tsn') or []
        self.csn = csn if isinstance(csn, list) else [csn]
        try:
            if self.inputs.verify_thru_gui():
                connections = kwargs.get('connections', None)
                self.webui = WebuiTest(connections, self.inputs)
                self.kwargs = kwargs
        except Exception as e:
            pass
     # end __init__

    def _get_ip_fabric_ri_obj(self):
        rt_inst_obj = self.vnc_api_h.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        return rt_inst_obj

    # end _get_ip_fabric_ri_obj

    def read(self):
        if not getattr(self, '_cleanups', None):
            self._clear_cleanups()
        obj = self.vnc_h.read_physical_router(self.name)
        self.uuid = obj.uuid
        self.mgmt_ip = obj.physical_router_management_ip
        self.tunnel_ip = obj.physical_router_loopback_ip
        self.peer_ip = obj.physical_router_dataplane_ip
        self.role = obj.physical_router_role
        self.model = obj.physical_router_product_name
        self.dm_managed = obj.physical_router_vnc_managed
        self.hw_inventorys = [entry['uuid'] for entry in
            obj.get_hardware_inventorys() or []]
#        creds = obj.get_physical_router_user_credentials()
#        self.ssh_username = creds.username
#        self.ssh_password = creds.password
        if self.inputs.physical_routers_data.get(self.name):
            details = self.inputs.physical_routers_data[self.name]
            self.ssh_username = details.get('ssh_username')
            self.ssh_password = details.get('ssh_password')
        csns = list()
        for csn in obj.get_virtual_router_refs() or []:
            csns.append(csn['to'][-1])
        self.csn = csns

    def get_uuid(self):
        return self.uuid

    def create_physical_device(self):
        if self.inputs.is_gui_based_config():
            self.webui.create_physical_router(self)
        else:
            self.uuid = self.vnc_h.create_physical_router(self.name,
                self.mgmt_ip, self.tunnel_ip, peer_ip=self.peer_ip,
                role=self.role, model=self.model,
                username=self.ssh_username, password=self.ssh_password)
            if self.csn:
                self.add_csn(csn=self.csn)
        self.logger.info('Created Physical device %s with ID %s' % (
            self.name, self.uuid))

    def add_csn(self, csns=None):
        csns = csns or self.inputs.get_csn()
        for csn in csns:
            self.vnc_h.add_csn_to_physical_router(device=self.name,
                                                  csn=csn)

    def delete_csn(self, csns=None):
        csns = csns or self.inputs.get_csn()
        for csn in csns:
            self.vnc_h.delete_csn_from_physical_router(device=self.name,
                                                   csn=csn)

    def delete_device(self):
        self.vnc_h.delete_physical_router(self.name)
        self.logger.info('Deleted physical device: %s' %(self.name))

    def setUp(self):
        super(PhysicalDeviceFixture, self).setUp()
        if not self.dm_managed:
            return
        try:
            self.read()
            self.logger.info('Physical device %s already present' % (
                self.name))
        except vnc_api_test.NoIdError:
            self.create_physical_device()
            self.created = True
        self.phy_device = self.vnc_h.read_physical_router(self.name)
        if self.inputs:
            self.device_details = self.get_device_details(
                self.inputs.physical_routers_data)

    def get_device_details(self, physical_routers_data):
        '''
            Returns the device dict of the ToR 
        '''
        for (device_name, device_dict) in physical_routers_data.items():
            if device_name == self.name:
                return device_dict
    # end get_device_details

    def cleanUp(self, force=False):
        do_cleanup = True
        if not self.created and not force:
            do_cleanup = False
            self.logger.info('Skipping deletion of device %s' % (
                self.name))
        if self.dm_managed and do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_physical_router(self)
            else:
                if self.csn:
                    self.delete_csn(self.csn)
                self.delete_device()
            assert self.verify_on_cleanup()
        super(PhysicalDeviceFixture, self).cleanUp()

    def add_virtual_network(self, vn_id):
        self.logger.debug('Adding VN %s to physical device %s' % (
            vn_id, self.name))
        self.vnc_h.add_vn_to_physical_router(self.name, vn_id)

    def delete_virtual_network(self, vn_id):
        self.logger.debug('Removing VN %s from physical device %s' % (
            vn_id, self.name))
        self.vnc_h.delete_vn_from_physical_router(self.name, vn_id)

    @retry(2, 5)
    def verify_on_cleanup(self):
        try:
            self.vnc_h.read_physical_router(self.name)
            self.logger.warn('physical router %s not yet deleted'%self.name)
            return False
        except vnc_api_test.NoIdError:
            self.logger.info('physical router %s got deleted as expected'%self.name)
            return True
        if self.hw_inventorys:
            try:
                self.vnc_h.read_hardware_inventory(id=self.hw_inventorys[0])
                self.logger.warn('hw inventory for %s is not deleted'%self.name)
                return False
            except vnc_api_test.NoIdError:
                self.logger.info('hw inventory for %s got deleted'%self.name)
                return True

    def get_physical_ports(self):
        obj = self.vnc_h.read_physical_router(self.name)
        return [pif['uuid'] for pif in obj.get_physical_interfaces() or []]

    def assign_role(self, role):
        self.vnc_h.update_physical_router(role=role, name=self.name)

    def setup_physical_ports(self):
        self.physical_port_fixtures = self.add_physical_ports()
        self.addCleanup(self.delete_physical_ports)

    def add_physical_port(self, port_name):
        pif_fixture = PhysicalInterfaceFixture(name=port_name,
                                               device_name=self.name,
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

    @property
    def netconf(self):
        if not getattr(self, '_netconf', None):
            self._netconf = self.get_connection_obj('juniper',
                 host=self.mgmt_ip,
                 username=self.ssh_username,
                 password=self.ssh_password)
            self.addCleanup(self._netconf.disconnect)
        return self._netconf

    def get_config(self):
        return self.netconf.get_config()

    @retry(tries=12, delay=5)
    def validate_interfaces_status(self, interfaces, status):
        found = False
        interfaces = [interface.replace('_', ':') for interface in interfaces]
        intf_list = self.netconf.get_interfaces(terse=True)
        for intf in intf_list:
            if intf['name'].strip() in interfaces:
                if intf['oper-status'].strip().lower() != status.lower():
                    self.logger.debug('%s is not %s on %s'%(
                        intf['name'].strip(), status, self.name))
                    return False
                found = True
        return found

    def get_associated_ae_interface(self, interface, prouter_config):
        ae = re.findall('interfaces %s .* (ae.*)'%interface, prouter_config)
        assert len(set(ae)) <= 1, 'More than one ae %s associated with %s on %s'%(
                              ae, interface, self.name)
        return ae[:1]

    def get_storm_control_config(self, interface, prouter_config):
        dct = dict()
        match = re.search('%s .*storm-control (.*)'%interface,
                                      prouter_config)
        if not match:
            return dct
        sc_name = match.group(1).strip()
        match = re.search('%s .*action-shutdown'%sc_name, prouter_config)
        if match:
            dct['action'] = 'interface-shutdown'
        match = re.search('%s .* recovery-timeout ([0-9]+)'%interface,
                          prouter_config)
        if match:
            dct['recovery_timeout'] = int(match.group(1))
        match = re.search('%s .*bandwidth-percentage ([0-9]+)'%sc_name,
                          prouter_config)
        if match:
            dct['bandwidth'] = int(match.group(1))
        match = re.search('%s .*no-broadcast'%sc_name, prouter_config)
        if match:
            dct['no_broadcast'] = True
        match = re.search('%s .*no-multicast'%sc_name, prouter_config)
        if match:
            dct['no_multicast'] = True
        match = re.search('%s .*no-registered-multicast'%sc_name, prouter_config)
        if match:
            dct['no_registered_multicast'] = True
        match = re.search('%s .*no-unregistered-multicast'%sc_name, prouter_config)
        if match:
            dct['no_unregistered_multicast'] = True
        match = re.search('%s .*no-unknown-unicast'%sc_name, prouter_config)
        if match:
            dct['no_unknown_unicast'] = True
        return dct

    def get_connection_obj(self, *args, **kwargs):
        self.conn_obj = ConnectionFactory.get_connection_obj(
            *args, **kwargs)
        self.conn_obj.connect()
        return self.conn_obj
    # end get_connection_obj

    def add_service_interface(self, service_port):
        self.vnc_h.add_si_to_prouter(self.uuid, service_port)

    def get_hardware_inventorys(self, refresh=False):
        if refresh or not self.hw_inventorys:
            obj = self.vnc_h.read_physical_router(self.name)
            self.hw_inventorys = [entry['uuid'] for entry in
                obj.get_hardware_inventorys() or []]
        return self.hw_inventorys
# end PhysicalDeviceFixture
