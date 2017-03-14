from netaddr import *

import vnc_api_test
from physical_device_fixture import PhysicalDeviceFixture
try:
    from webui_test import *
except ImportError:
    pass

class VpeRouterFixture(PhysicalDeviceFixture):

    '''Fixture to manage Physical Router objects

    Mandatory:
    :param name   : name of the vcpe router

    '''

    def __init__(self, *args, **kwargs):
        super(VpeRouterFixture, self).__init__( *args, **kwargs)
        if self.inputs.verify_thru_gui():
            self.webui = WebuiTest(self.connections, self.inputs)
            self.kwargs = kwargs
     # end __init__

    def setUp(self):
        super(VpeRouterFixture, self).setUp()

    def vrouter_ref_set(self,vrouter_obj):
        self.phy_device.set_virtual_router(vrouter_obj)
        self.update()

    def vrouters_ref_set(self,vrouter_objs):
        pass

    def update(self):
        self.vnc_api_h.physical_router_update(self.phy_device)

    def setUp(self):
        super(VpeRouterFixture, self).setUp()


    def cleanUp(self):
        super(VpeRouterFixture, self).cleanUp()

# end VcpeRouterFixture

if __name__ == "__main__":
    pass
