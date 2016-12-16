import pprint

import vnc_api_test
from cfgm_common.exceptions import NoIdError

from tcutils.util import get_random_name, retry, compare_dict, get_dashed_uuid


class InterfaceRouteTableFixture(vnc_api_test.VncLibFixture):

    def __init__(self, *args, **kwargs):
        super(InterfaceRouteTableFixture, self).__init__(self, *args, **kwargs)
        self.vnc_h = None
        self.verify_is_run = False
        self.prefixes = kwargs.get('prefixes', None)
        self.name = kwargs.get('name', get_random_name('intf-rtb'))
        self.project_id = kwargs.get('project_id', None)
        self.uuid = kwargs.get('uuid', None)
        self.is_already_present = False

    def setUp(self):
        super(InterfaceRouteTableFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(InterfaceRouteTableFixture, self).cleanUp()
        self.delete()

    def create(self):
        if self.uuid:
            return self.read()
        self.parent_obj = self.get_project_obj()
        fq_name = self.parent_obj.fq_name + [self.name]
        try:
            intf_rtb_obj = self.vnc_api_h.interface_route_table_read(
                fq_name=fq_name)
            self.uuid = intf_rtb_obj.uuid
            return self.read()
        except NoIdError, e:
            pass

        intf_rtb_obj = self.vnc_h.create_interface_route_table(
            self.name,
            parent_obj=self.parent_obj,
            prefixes=self.prefixes)
        self._populate_attr(intf_rtb_obj)
    # end create

    def verify_on_setup(self):
        pass
    # end verify_on_setup

    def verify_on_cleanup(self):
        pass
    # end verify_on_cleanup

    def _populate_attr(self, intf_rtb_obj):
        self.obj = intf_rtb_obj
        self.fq_name = intf_rtb_obj.fq_name
        self.uuid = intf_rtb_obj.uuid

    def read(self):
        try:
            intf_rtb_obj = self.vnc_api_h.interface_route_table_read(
                id=self.uuid)
            self.logger.info('Reading existing InterfaceRouteTable with UUID '
                             '%s' % (self.uuid))
        except NoIdError, e:
            self.logger.exception('UUID %s not found, unable to read '
                                  'InterfaceRouteTable' % (self.uuid))
            raise e

        self._populate_attr(intf_rtb_obj)
        self.is_already_present = True
    # end read

    def add_routes(self, prefixes):
        intf_rtb_obj = self.vnc_h.add_interface_route_table_routes(self.uuid,
                                                                   prefixes=prefixes)
        self._populate_attr(intf_rtb_obj)

    def del_routes(self, prefixes):
        self.vnc_h.del_interface_route_table_routes(prefixes)
        self._populate_attr(intf_rtb_obj)
    # end del_routes

    def delete(self):
        if self.is_already_present:
            self.logger.info('Skipping deletion of InterfaceRouteTable %s' % (
                             self.fq_name))
            return
        self.vnc_h.delete_interface_route_table(self.uuid)
        self.verify_on_cleanup()
    # end delete

if __name__ == "__main__":
    rtb_fixture = InterfaceRouteTableFixture(
        name='rtb1', prefixes=['10.1.1.0/24'], project_id=get_dashed_uuid('24c8d6f768c843a2ac83f5a8ff847073'), auth_server_ip='10.204.216.184', cfgm_ip='10.204.216.184')
    rtb_fixture.setUp()
    import pdb
    pdb.set_trace()
    rtb_fixture.cleanUp()
