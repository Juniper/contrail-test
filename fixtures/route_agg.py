from tcutils.util import retry
from vnc_api.vnc_api import *
#from time import sleep
import vnc_api_test
import fixtures

class RouteAggregateFixture(fixtures.Fixture):
    
    def __init__(self, connections, agg_name, prefix=None):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.connections.logger
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.api_s_inspect = self.connections.api_server_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.project = self.connections.project_name
        self.agg_name = agg_name
        self.agg_id = None
        self.agg_fq_name = ['default-domain', self.agg_name]
        self.prefix = prefix if type(prefix) is list else [prefix]
        self.project_name = self.connections.project_name
        self.obj = None
    
    def read(self):
        if self.agg_id:
            self.agg_obj = self.vnc_lib_h.route_aggregate_read(id=self.agg_id)
            self.agg_name = self.agg_obj.name
    # end read

    def setUp(self):
        super(RouteAggregateFixture, self).setUp()
        self.create()
    # end setup

    def create(self):
        if not self.agg_id:
            project=self.vnc_lib_h.project_read(fq_name=['default-domain', self.project_name])
            route_aggregate=RouteAggregate(name=self.agg_name, parent_obj=project)
            route_list=RouteListType(self.prefix)
            route_aggregate.set_aggregate_route_entries(route_list)
            self.agg_id = self.vnc_lib_h.route_aggregate_create(route_aggregate)
            self.logger.info('created RouteAggreegate %s'%self.agg_name)
            self.read()

    def attach_route_aggregate_to_si(self, si, interface='left'):
        self.agg_obj.set_service_instance(si,ServiceInterfaceTag(interface_type=interface))
        self.vnc_lib_h.route_aggregate_update(self.agg_obj)
    
    def remove_route_aggregate_from_si(self, si):
        self.agg_obj.del_service_instance(si)
        self.vnc_lib_h.route_aggregate_update(self.agg_obj)
    
    def update_route_aggregate(self,prefix,interface=None):
        route_list=RouteListType(self.prefix)
        self.agg_obj.set_aggregate_route_entries(route_list)
        if interface:
            self.agg_obj.set_service_instance(si,ServiceInterfaceTag(interface_type=interface))
        self.vnc_lib_h.route_aggregate_update(self.agg_obj)
        
    @retry(delay=1, tries=10)
    def verify_route_aggregate_in_control(self, vn_fixture, vm_fixture, prefix = '', search_value = 'Aggregate'):
        search_in_cn = prefix
        found_value = True
        for cn in vm_fixture.get_control_nodes():
            found_value = found_value and re.findall(search_value, str(
                self.cn_inspect[cn
                ].get_cn_route_table_entry(search_in_cn,
                vn_fixture.vn_fq_name+":"+vn_fixture.vn_name)[0]))
            self.logger.info('Route Aggregates were found in control node %s'%cn)
        return True if found_value else False
    
    def delete(self):
        self.logger.info('Deleting RouteAggregate %s'%self.agg_name)
        self.vnc_lib_h.route_aggregate_delete(id=self.agg_id)
    
    def cleanUp(self):
        self.delete()
        self.logger.info('Deleted RouteAggregate %s' % self.agg_name)
        super(RouteAggregateFixture, self).cleanUp()
    # end cleanup