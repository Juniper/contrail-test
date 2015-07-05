from vnc_api_test import *

class PhysicalInterfaceFixture(VncLibFixture):

    '''Fixture to handle Physical Interface object in 
       a phyiscal device

    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth-server_ip : default is 127.0.0.1

    :param name : Mandatory, name of the physical interface
    :param device_id : Mandatory, UUID of physical device
    '''

    def __init__(self, *args, **kwargs):
        super(PhysicalInterfaceFixture, self).__init__(self, *args, **kwargs)
        self.name = args[0]
        self.device_id = args[1]

        self.already_present = False

        self.vn_obj = None
     # end __init__

    def setUp(self):
        super(PhysicalInterfaceFixture, self).setUp()
        self.device_obj = self.vnc_api_h.physical_router_read(
            id=self.device_id)
        self.device_name = self.device_obj.fq_name[-1]
        self.fq_name = self.device_obj.fq_name[:]
        self.fq_name.append(self.name)
        try:
            self.obj = self.vnc_api_h.physical_interface_read(
                fq_name=self.fq_name)
            self.already_present = True
            self.uuid = self.obj.uuid
            self.logger.debug('Physical port %s is already present' % (
                self.name))
        except NoIdError:
            self.create_pif()

    # end setUp

    def create_pif(self):
        self.logger.info('Creating physical port %s:' % (
            self.fq_name))
        pif_obj = PhysicalInterface(name=self.name,
                                    parent_obj=self.device_obj,
                                    display_name=self.name)
        self.uuid = self.vnc_api_h.physical_interface_create(pif_obj)
        self.obj = self.vnc_api_h.physical_interface_read(id=self.uuid)
    # end create_pif
    

    def cleanUp(self):
        super(PhysicalInterfaceFixture, self).cleanUp()
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.debug('Skipping deletion of physical port %s :' % (
                 self.fq_name))
        if do_cleanup:
            self.delete_pif()
    # end cleanUp

    def delete_pif(self):
        self.logger.info('Deleting physical port %s:' % (
            self.fq_name))
        self.vnc_api_h.physical_interface_delete(id=self.uuid)    
    # end delete_pif

# end PhysicalInterfaceFixture

if __name__ == "__main__":
    device_id = 'e122f6b2-5d5c-4f2e-b665-d69dba447bdf'
    pif_obj = PhysicalInterfaceFixture(name='ge-0/0/0', device_id=device_id)
    pif_obj.setUp()
    import pdb
    pdb.set_trace()
    pif_obj.cleanUp()
