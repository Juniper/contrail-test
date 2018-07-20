import vnc_api_test

class LogicalInterfaceFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Logical Interface object in 
       a phyiscal port 

    Optional:
    :param name     : name of the lif
    :param uuid     : UUID of the logical interface
    :param pif_id   : Physical interface UUID 
    :param pif_fqname   : Physical interface fqname 
    :param vlan_id : Default is 0
    :param interface_type : l2 or l3
    :param vmi_ids  : List of vmi ids part of this lif, default is []

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
        super(LogicalInterfaceFixture, self).__init__(self, *args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.pif_id = kwargs.get('pif_id')
        self.pif_fqname = kwargs.get('pif_fqname')
        self.interface_type = kwargs.get('interface_type')
        self.vmi_ids = kwargs.get('vmi_ids', [])
        self.vlan_id = int(kwargs.get('vlan_id') or 0)

        self.created = False
        self.vn_obj = None
     # end __init__

    def read(self):
        kwargs = dict()
        if not self.uuid:
            if not self.pif_fqname:
                obj = self.vnc_h.read_physical_interface(id=self.pif_id)
                self.pif_fqname = list(obj.get_fq_name())
            self.fq_name = self.pif_fqname + [self.name.replace(':', '__')]
            kwargs['fq_name'] = list(self.fq_name)
        else:
            kwargs['id'] = self.uuid
        obj = self.vnc_h.read_logical_interface(**kwargs)
        self.pif_fqname = obj.fq_name[:-1]
        self.uuid = obj.uuid
        self.fq_name = obj.fq_name
        self.name = obj.display_name
        self.interface_type = obj.get_logical_interface_type()
        self.vlan_id = int(obj.logical_interface_vlan_tag or 0)

    def setUp(self):
        super(LogicalInterfaceFixture, self).setUp()
        try:
            self.read()
            self.logger.debug('Logical port %s is already present' % (
                self.fq_name))
        except vnc_api_test.NoIdError:
            if self.uuid:
                raise
            self.create_lif()
            self.created = True
        if self.vmi_ids:
            for vmi_id in self.vmi_ids:
                self.add_virtual_machine_interface(vmi_id)
    # end setUp

    def create_lif(self):
        self.logger.info('Creating Logical port %s' % (self.fq_name))
        self.uuid = self.vnc_h.create_logical_interface(name=self.name,
            pif_fqname=self.pif_fqname, vlan=self.vlan_id,
            interface_type=self.interface_type)
    # end create_lif

    def set_vlan_tag(self, vlan_id=0):
        self.vlan_id = vlan_id
        self.vnc_h.update_logical_interface(id=self.uuid, vlan=vlan_id)
    # end set_vlan_tag

    def cleanUp(self, force=False):
        do_cleanup = True
        if not self.created and not force:
            do_cleanup = False
            self.logger.debug('Skipping deletion of logical port %s' % (
                self.fq_name))
        self.clear_vmi_mapping()
        if do_cleanup:
            self.delete_lif()
        self.verify_on_cleanup()
        super(LogicalInterfaceFixture, self).cleanUp()
    # end cleanUp

    def clear_vmi_mapping(self):
        ''' Disassociate all vmis from this lif
        '''
        self.logger.debug('Disassociating all vmis from %s' % (self.fq_name))
        self.obj = self.vnc_api_h.logical_interface_read(id=self.uuid)
        self.obj.set_virtual_machine_interface_list([])
        self.vnc_api_h.logical_interface_update(self.obj)
    # end clear_vmi_mapping
        
    def delete_lif(self):
        self.logger.info('Deleting Logical port %s' % (self.fq_name))
        self.vnc_h.delete_logical_interface(id=self.uuid)
    # end delete_lif

    def add_virtual_machine_interface(self, vmi_id):
        self.logger.info('Adding VMI %s to logical interface %s' % (
            vmi_id, self.fq_name))
        self.vnc_h.add_vmi_to_lif(vmi_id=vmi_id, lif_id=self.uuid)

    def delete_virtual_machine_interface(self, vmi_id):
        self.logger.info('Deleting VMI %s from logical interface %s' % (
            vmi_id, self.fq_name))
        self.vnc_h.delete_vmi_from_lif(vmi_id=vmi_id, lif_id=self.uuid)

    def verify_on_cleanup(self):
        try:
            self.vnc_h.read_logical_interface(id=self.uuid)
            assert False, 'logical interface %s is not yet deleted'%self.fq_name
        except vnc_api_test.NoIdError:
            self.logger.info('logical interface %s got deleted as expected'%self.fq_name)
            return True
# end LogicalInterfaceFixture

if __name__ == "__main__":
    device_id = 'e122f6b2-5d5c-4f2e-b665-d69dba447bdf'
    from pif_fixture import PhysicalInterfaceFixture
    from port_fixture import PortFixture
    pif_obj = PhysicalInterfaceFixture(name='ge-0/0/0', device_id=device_id)
    pif_obj.setUp()

    vn_id = '1c83bed1-7d24-4414-9aa2-9d92975bc86f'
    subnet_id = '49fea486-57ab-4056-beb3-d311a385814e'
    port_fixture = PortFixture(
        vn_id=vn_id, api_type='contrail', mac_address="00:00:00:00:00:01",
        fixed_ips=[{'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture.setUp()
    lif_obj = LogicalInterfaceFixture(
        name='ge-0/0/0.0', pif_id=pif_obj.uuid, vmi_ids=[port_fixture.uuid])
    lif_obj.setUp()
