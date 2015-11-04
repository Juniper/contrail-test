import vnc_api_test

class LogicalInterfaceFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Logical Interface object in 
       a phyiscal port 

    Mandatory:
    :param name     : name of the lif
    :param pif_id   : Physical interface UUID 
                      One of pif_id or pif_obj is mandatory 
    :param pif_obj  : PhysicalInterface object which is to be the parent
                      of this object
                      One of pif_id or pif_obj is mandatory

    Optional:
    :params vlan_id : Default is 0
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
        self.name = args[0]
        self.pif_id = kwargs.get('pif_id',None)
        self.pif_obj = kwargs.get('pif_obj',None)
        if not (self.pif_obj or self.pif_id):
            raise TypeError('One of pif_id or pif_obj is mandatory')
        vlan_id = kwargs.get('vlan_id', 0)
        self.vmi_ids = kwargs.get('vmi_ids', [])
        
        self.vlan_id = int(vlan_id)

        self.already_present = False

        self.vn_obj = None
     # end __init__

    def setUp(self):
        super(LogicalInterfaceFixture, self).setUp()
        if self.pif_obj:
            self.pif_id = self.pif_obj.uuid
        else:
            self.pif_obj = self.vnc_api_h.physical_interface_read(id=self.pif_id)
        lif_fq_name = self.pif_obj.fq_name[:]
        lif_fq_name.append(self.name)
        self.fq_name = lif_fq_name

        try:
            self.obj = self.vnc_api_h.logical_interface_read(
                fq_name=lif_fq_name)
            self.already_present = True
            self.logger.debug('Logical port %s already present' % (
                lif_fq_name))
        except vnc_api_test.NoIdError:
            self.create_lif()

        if self.vmi_ids:
            for vmi_id in self.vmi_ids:
                vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
                    id=vmi_id)
                self.obj.add_virtual_machine_interface(vmi_obj)
            self.vnc_api_h.logical_interface_update(self.obj)
    # end setUp

    def create_lif(self):
        self.logger.info('Creating Logical port %s' % (self.fq_name))
        lif_obj = vnc_api_test.LogicalInterface(name=self.name,
                                   parent_obj=self.pif_obj,
                                   display_name=self.name)
        lif_obj.set_logical_interface_vlan_tag(self.vlan_id)
        self.uuid = self.vnc_api_h.logical_interface_create(lif_obj)
        self.obj = self.vnc_api_h.logical_interface_read(id=self.uuid)
    # end create_lif

    def set_vlan_tag(self, vlan_id=0):
        self.vlan_id = vlan_id
        self.obj = self.vnc_api_h.logical_interface_read(id=self.uuid)
        lif_obj.set_logical_interface_vlan_tag(vlan_id)
        self.vnc_api_h.logical_interface_update(lif_obj)
    # end set_vlan_tag

    def cleanUp(self):
        super(LogicalInterfaceFixture, self).cleanUp()
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.debug('Skipping deletion of logical port %s' % (
                self.fq_name))
        self.clear_vmi_mapping()
        if do_cleanup:
            self.delete_lif()
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
        self.clear_vmi_mapping()
        self.logger.info('Deleting Logical port %s' % (self.fq_name))
        self.vnc_api_h.logical_interface_delete(id=self.uuid)
    # end delete_lif
    

    def add_virtual_machine_interface(self, vmi_id):
        self.logger.info('Adding VMI %s to logical interface %s' % (
            vmi_id, self.fq_name))
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_id)
        self.obj.add_virtual_machine_interface(vmi_obj)
        self.vnc_api_h.logical_interface_update(self.obj)

    def delete_virtual_machine_interface(self, vmi_id):
        self.logger.info('Deleting VMI %s from logical interface %s' % (
            vmi_id, self.fq_name))
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_id)
        self.obj.del_virtual_machine_interface(vmi_obj)
        self.vnc_api_h.logical_interface_update(self.obj)

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
