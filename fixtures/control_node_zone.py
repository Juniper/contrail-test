import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class ControlNodeZoneFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Control node zone object
    Optional:
    :param name : name of the control node zone 
    :param uuid : UUID of the control node zone 
    '''
    def __init__(self, *args, **kwargs):
        super(ControlNodeZoneFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('zone_name')
        self.uuid = kwargs.get('uuid')
        self.fq_name = ['default-global-system-config',self.name] 
        self.bgp_router_objs = []
        self.created = False

    def setUp(self):
        super(ControlNodeZoneFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping Control Node Zone clean up %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(ControlNodeZoneFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_control_node_zone(id=self.uuid)

    def read(self):
        obj = self.vnc_h.read_control_node_zone(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        return obj

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_control_node_zone(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_control_node_zone(
                                     name=self.name)
                self.created = True
                self.logger.info('Created control node zone %s(%s)'%(self.name,
                                                                  self.uuid))
        if not self.created:
            self.read()

    def get_bgp_router(self):
        return self.bgp_router_objs

    def add_zone_to_bgp_router(self,**kwargs):
        bgp_router = self._vnc.bgp_router_read(**kwargs)
        if bgp_router not in self.bgp_router_objs: 
            cnz_obj = self.get_object()
            bgp_router.set_control_node_zone(cnz_obj)
            self._vnc.bgp_router_update(bgp_router)  
            self.bgp_router_objs.append(bgp_router)
 
    def remove_zone_from_bgp_routers(self,**kwargs):
        cnz_obj = self.get_object()
        for bgp_router in self.bgp_router_objs:
            bgp_router.del_control_node_zone(cnz_obj)
            self._vnc.bgp_router_update(bgp_router)
            self.bgp_router_objs.remove(bgp_router) 

    def delete(self):
        self.logger.info('Deleting Control node zone %s(%s)'%(self.name, self.uuid))
        try:
            self.remove_zone_from_bgp_routers()
            self.vnc_h.delete_control_node_zone(id=self.uuid)
        except NoIdError:
            pass
