from common.mvpn.base import *
from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
import test
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer

class TestMVPNSingleVNSingleCompute(MVPNTestSingleVNSingleComputeBase):

    @classmethod
    def setUpClass(cls):
        super(TestMVPNSingleVNSingleCompute, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestMVPNSingleVNSingleCompute, cls).tearDownClass()
    # end tearDownClass

    #@test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mvpn_single_vn_within_compute(self):
        '''
            Test MVPN functionality when both multicast source and
            receivers are part of a single VN and also part of the same
            compute.
        '''
        # Bringup MVPN setup
        ret_dict = self.bringup_mvpn_setup()

        vm_fixtures = ret_dict['vm_fixtures']

        # Verify MVPN Type-1 routes
        route_type = 1
        result = self.verify_mvpn_routes(route_type)

        # IGMP Join parameter details
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 1,                 # Record type. INCLUDE
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2, not from vm3. So, that when multicast
        # source vm1 starts sending data traffic, vm2 only should receive the
        # traffic, not vm3.
        traffic = {'stream1': {'src':'vm1',         # Multicast source
                               'rcvrs': ['vm2'],    # Multicast receivers
                               'non_rcvrs': ['vm3'],# Non Multicast receivers
                               'maddr':'239.1.1.1', # Multicast group address
                               'count':10           # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast data traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

        # IGMP Leave parameter details
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 6,                 # Record type.BLOCK OLD SOURCES
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

    # end test_mvpn_single_vn_within_compute

class TestMVPNSingleVNMultiCompute(MVPNTestSingleVNMultiComputeBase):

    @classmethod
    def setUpClass(cls):
        super(TestMVPNSingleVNMultiCompute, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestMVPNSingleVNMultiCompute, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mvpn_single_vn_multi_compute(self):
        '''
            Test MVPN functionality when both multicast source and
            receivers are part of a single VN. But, source and receivers are
            part of different computes
        '''

        # Bringup MVPN setup
        ret_dict = self.bringup_mvpn_setup()

        vm_fixtures = ret_dict['vm_fixtures']

        # Verify MVPN Type-1 routes
        route_type = 1
        result = self.verify_mvpn_routes(route_type)

        # IGMP Join parameter details
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 1,                 # Record type. INCLUDE
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Multicast Traffic details
        # IGMPv3 join is sent from vm3, not from vm2 and vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm3 only should
        # receive the traffic, not vm2 and vm4.
        traffic = {'stream1':{'src':'vm1',              # Multicast source
                               'rcvrs': ['vm3'],        # Multicast receivers
                               'non_rcvrs': ['vm2','vm4'], # Non Multicast receivers
                               'maddr': '239.1.1.1',       # Multicast group address
                               'count':10               # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

        # IGMP Leave parameter details
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 6,                 # Record type.BLOCK OLD SOURCES
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

    # end test_mvpn_single_vn_multi_compute

class TestMVPNMultiVNSingleCompute(MVPNTestMultiVNSingleComputeBase):

    @classmethod
    def setUpClass(cls):
        super(TestMVPNMultiVNSingleCompute, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestMVPNMultiVNSingleCompute, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mvpn_multi_vn_single_compute(self):
        '''
            Test MVPN functionality when both multicast source and
            receivers are part of a multiple VNs. But, source and receivers are
            part of different computes
        '''

        # Bringup MVPN setup
        ret_dict = self.bringup_mvpn_setup()

        vm_fixtures = ret_dict['vm_fixtures']

        # Verify MVPN Type-1 routes
        route_type = 1
        result = self.verify_mvpn_routes(route_type)

        # IGMP Join parameters
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 1,                 # Record type. INCLUDE
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':'vm1',             # Multicast source
                               'rcvrs': ['vm2','vm3'],  # Multicast receivers
                               'non_rcvrs': ['vm4'],    # Non Multicast receivers
                               'maddr': '239.1.1.1',    # Multicast group address
                               'count':10               # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

        # IGMP Leave parameters
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 6,                 # Record type.BLOCK OLD SOURCES
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

    # end test_mvpn_multi_vn_single_compute

class TestMVPNMultiVNMultiCompute(MVPNTestMultiVNMultiComputeBase):

    @classmethod
    def setUpClass(cls):
        super(TestMVPNMultiVNMultiCompute, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestMVPNMultiVNMultiCompute, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mvpn_multi_vn_multi_compute(self):
        '''
            Test MVPN functionality when both multicast source and
            receivers are part of a single VN. But, source and receivers are
            part of different computes
        '''

        # Bringup MVPN setup
        ret_dict = self.bringup_mvpn_setup()

        vm_fixtures = ret_dict['vm_fixtures']

        # Verify MVPN Type-1 routes
        route_type = 1
        result = self.verify_mvpn_routes(route_type)

        # IGMP Join parameters
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 1,                 # Record type. INCLUDE
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':'vm1',                 # Multicast source
                               'rcvrs': ['vm2', 'vm3'],     # Multicast receivers
                               'non_rcvrs': ['vm4'],        # Non Multicast receivers
                               'maddr': '239.1.1.1',        # Multicast group address
                               'count':10                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

        # IGMP Leave parameters
        igmp = {'type': 0x22,                   # IGMPv3 Report
                'numgrp': 1,                    # Number of group records
                'record1': {
                    'rtype': 6,                 # Record type.BLOCK OLD SOURCES
                    'maddr': '239.1.1.1',       # Multicast group address
                    'srcaddrs': ['30.30.30.1']  # List of multicast source addresses
                },
               }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcast(vm_fixtures, traffic, igmp)

    # end test_mvpn_multi_vn_multi_compute


