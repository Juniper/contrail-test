from common.base import GenericTestBase
from tcutils.wrappers import preposttest_wrapper
from common.base import GenericTestBase
import route_agg
from common.servicechain.firewall.verify import VerifySvcFirewall
from route_agg import RouteAggregateFixture
import time

class TestRouteAggregate(GenericTestBase, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestRouteAggregate, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRouteAggregate, cls).tearDownClass()

    @preposttest_wrapper
    def test_route_aggregation(self):
        '''
        1)create svc
        2)Create Route Aggrgate and give prefix of left_vn_cidr
        3)Attach Route Aggregate to svc right intf of si
        4)Verify in control Node of Route aggregates on right routing instnace
        5)Remove Route Aggregate from svc left intf
        6)Verify in control Node,Route aggregates should be removed
        5)ping to from left VM to Right Vm
        '''
        svc_info = self.verify_svc_chain(svc_img_name='cirros_in_net', service_mode='in-network',
                                     create_svms=True)
        si = svc_info['si_fixture']
        left_vn = svc_info['left_vn_fixture']
        right_vn = svc_info['right_vn_fixture']
        left_vm = svc_info['left_vm_fixture']
        agg_prefix = left_vn.get_cidrs()

        agg_fixture = self.useFixture(RouteAggregateFixture(
                                      self.connections, prefix=agg_prefix))
        agg_fixture.attach_route_aggregate_to_si(si=si.si_obj, interface='right')
        self.addCleanup(agg_fixture.remove_route_aggregate_from_si, si.si_obj)
        time.sleep(3)
        assert agg_fixture.verify_route_aggregate_in_control(right_vn, left_vm, agg_prefix[0]),'Route aggreegates Not found in control' 

    @preposttest_wrapper    
    def test_with_multiple_route_aggregation_prefixes(self):
        '''
        1)create svc
        2)Create Route Aggrgates left_agg,Right agg and give prefixes
        3)Attach Route Aggregate to svc left intf
        4)Verify in control Node for Route aggregates
        5)ping to from left VM to Right Vm 
        6)Remove Route Aggregatee from left intf
        7)Attach Route Aggregate to svc right intf
        8)Verify in control Node for Route aggregates
        9)ping to from left VM to Right Vm 
        '''
        svc_info = self.verify_svc_chain(svc_img_name='cirros_in_net', service_mode='in-network',
                                     create_svms=True)
        si = svc_info['si_fixture']
        left_vn = svc_info['left_vn_fixture']
        right_vn = svc_info['right_vn_fixture']
        left_vm = svc_info['left_vm_fixture']
        right_vm = svc_info['right_vm_fixture']
        left_agg_prefix = left_vn.get_cidrs()
        right_agg_prefix = right_vn.get_cidrs()
        left_agg_fixture = self.useFixture(RouteAggregateFixture(
                                      self.connections, prefix=left_agg_prefix))
        left_agg_fixture.attach_route_aggregate_to_si(si=si.si_obj, interface='right')
        self.addCleanup(left_agg_fixture.remove_route_aggregate_from_si, si.si_obj)
        right_agg_fixture = self.useFixture(RouteAggregateFixture(
                                      self.connections, prefix=right_agg_prefix))
        right_agg_fixture.attach_route_aggregate_to_si(si=si.si_obj, interface='left')
        self.addCleanup(right_agg_fixture.remove_route_aggregate_from_si, si.si_obj)
        timee.sleep(3)
        assert left_agg_fixture.verify_route_aggregate_in_control(right_vn, left_vm, left_agg_prefix[0]),'Route aggreegates Not found in control'
        assert right_agg_fixture.verify_route_aggregate_in_control(left_vn, right_vm, right_agg_prefix[0]), 'Route aggreegates Not found in control'
