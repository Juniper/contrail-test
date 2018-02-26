from netaddr import *
import vnc_api_test
try:
    from webui_test import *
except ImportError:
    pass

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
        try:
            #inputs object not mandatory.Its not passed as part of 
            #tools/setup_tors.py.Code was getting exception here
            if self.inputs.verify_thru_gui():
                self.webui = WebuiTest(self.connections, self.inputs)
                self.ip = args[2]
        except Exception as e:
            pass 

    def setUp(self):
        super(VirtualRouterFixture, self).setUp()
        vr_fq_name = ['default-global-system-config', self.name]
        try:
            self.vr = self.vnc_api_h.virtual_router_read(
                fq_name=vr_fq_name)
            self.logger.info('virtual router %s already present' % (
                vr_fq_name))
        except vnc_api_test.NoIdError:
            if self.inputs and self.inputs.is_gui_based_config():
                self.vr = self.webui.create_virtual_router(self)
            else:
                self.vr = self.create_virtual_router()
       
        try: 
            if not self.inputs.is_gui_based_config():
                self.update_virtual_router_type()
        except Exception as e:
            self.update_virtual_router_type()

    def cleanUp(self):
        super(VirtualRouterFixture, self).cleanUp()
        do_cleanup = True
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_virtual_router(self)
            else:
                pass

# end VirtualRouterFixture

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
