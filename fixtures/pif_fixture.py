import vnc_api_test
try:
    from webui_test import *
except ImportError:
    pass

class PhysicalInterfaceFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Physical Interface object in
       a physical device

    optional:
    :param name         : name of the physical interface
    :param uuid         : UUID of the physical interface
    :param device_id    : UUID of physical device
    :param device_name  : Name of the physical device
                          One of device_name or device_id is mandatory
    :param interface_type : one of 'lag' or 'regular'
    :param mac_address : mac address of the interface

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
        super(PhysicalInterfaceFixture, self).__init__(self, *args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.device_id = kwargs.get('device_id')
        self.device_name = kwargs.get('device_name')
        self.interface_type = kwargs.get('interface_type')
        self.mac_address = kwargs.get('mac_address')

        self.created = False

        try:
            if self.inputs.verify_thru_gui():
                self.int_type = kwargs.get('int_type', None)
                connections = kwargs.get('connections', None)
                self.webui = WebuiTest(connections, self.inputs)
        except Exception as e:
            pass 
     # end __init__

    def read(self):
        kwargs = dict()
        if not self.uuid:
            if not self.device_name:
                obj = self.vnc_h.read_physical_router(id=self.device_id)
                self.device_name = obj.name
            self.fq_name = ['default-global-system-config',
                            self.device_name, self.name.replace(':', '__')]
            kwargs['fq_name'] = list(self.fq_name)
        else:
            kwargs['id'] = self.uuid
        obj = self.vnc_h.read_physical_interface(**kwargs)
        self.device_name = obj.fq_name[-2]
        self.uuid = obj.uuid
        self.name = obj.display_name
        self.fq_name = obj.fq_name
        self.interface_type = obj.get_physical_interface_type()
        self.mac_address = obj.get_physical_interface_mac_addresses()

    def setUp(self):
        super(PhysicalInterfaceFixture, self).setUp()
        try:
            self.read()
            self.logger.debug('Physical port %s is already present' % (
                self.fq_name))
        except vnc_api_test.NoIdError:
            if self.uuid:
                raise
            self.create_pif()
            self.created = True
    # end setUp

    def create_pif(self):
        self.logger.info('Creating physical port %s:' % (
            self.fq_name))
        if self.inputs:
            if self.inputs.is_gui_based_config():
                self.webui.create_physical_interface(self)
                return
        self.uuid = self.vnc_h.create_physical_interface(
            name=self.name, device_name=self.device_name,
            mac=self.mac_address, interface_type=self.interface_type)
    # end create_pif

    def cleanUp(self, force=False):
        do_cleanup = True
        if not self.created and not force:
            do_cleanup = False
            self.logger.debug('Skipping deletion of physical port %s :' % (
                 self.fq_name))
        if do_cleanup:
            if self.inputs:
                if self.inputs.is_gui_based_config():
                    self.webui.delete_physical_interface(self)
                    return
        self.delete_pif()
        self.verify_on_cleanup()
        super(PhysicalInterfaceFixture, self).cleanUp()
    # end cleanUp

    def delete_pif(self):
        self.logger.info('Deleting physical port %s:' % (
            self.fq_name))
        self.vnc_h.delete_physical_interface(id=self.uuid) 
    # end delete_pif

    def get_logical_ports(self):
        obj = self.read_physical_interface(id=self.uuid)
        return [lif['uuid'] for lif in obj.get_logical_interfaces() or []]

    def verify_on_cleanup(self):
        try:
            self.vnc_h.read_physical_interface(id=self.uuid)
            assert False, 'physical interface %s is not yet deleted'%self.fq_name
        except vnc_api_test.NoIdError:
            self.logger.info('physical interface %s got deleted as expected'%self.fq_name)
            return True
# end PhysicalInterfaceFixture

if __name__ == "__main__":
    device_id = 'e122f6b2-5d5c-4f2e-b665-d69dba447bdf'
    pif_obj = PhysicalInterfaceFixture(name='ge-0/0/0', device_id=device_id)
    pif_obj.setUp()
    pif_obj.cleanUp()
