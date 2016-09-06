from netaddr import *
from contrailapi import ContrailVncApi
import vnc_api_test


class VirtualRouterBase(vnc_api_test.VncLibFixture):

    '''Fixture to manage virtual router objects

    Mandatory:
    :param name   : name of the device
    :param virtual_router_type  : virtual router type('embedded','hypervisor' etc)
    '''

    def __init__(self, *args, **kwargs):
        super(VirtualRouterBase, self).__init__(*args, **kwargs)
        self.name = args[0]
        self.virtual_router_type = args[1]
        self.vr = None
        self.vnc_h = ContrailVncApi(self.vnc_api_h, self.logger)

     # end __init__
    def setUp(self):
        super(VirtualRouterBase, self).setUp()
    
    def cleanUp(self):
        super(VirtualRouterBase, self).cleanUp()


    def create(self):
        pass

    def delete(self):
        pass

    def update(self):
        self.vnc_api_h.virtual_router_update(self.vr)

    def read(self,id):
        self.vr = self.vnc_api_h.virtual_router_read(id=id)
    
    def update_virtual_router_type(self,vrouter_type=None):
        if not vrouter_type:
            self.vnc_h.update_virtual_router_type(self.name,self.virtual_router_type)
        else:
            self.vnc_h.update_virtual_router_type(self.name,vrouter_type)


class VirtualRouterFixture(VirtualRouterBase):
    def __init__(self, *args, **kwargs):
        super(VirtualRouterFixture,self).__init__(*args, **kwargs)

    def setUp(self):
        super(VirtualRouterFixture, self).setUp()
        vr_fq_name = ['default-global-system-config', self.name]
        try:
            self.vr = self.vnc_api_h.virtual_router_read(
                fq_name=vr_fq_name)
            self.logger.info('virtual router %s already present' % (
                vr_fq_name))
        except vnc_api_test.NoIdError:
            self.vr = self.create_virtual_router()
        self.update_virtual_router_type()

    def cleanUp(self):
        super(VirtualRouterFixture, self).cleanUp()
        pass

# end VirtualRouterFixture

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
