from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
import test

from common.pbb_evpn.base import *

#from svc_instance_fixture import SvcInstanceFixture
#from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
import socket

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer


class TestPbbEvpnMacLearning(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacLearning, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacLearning, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_learning_single_isid(self):
        '''
            Test MAC learning on I-Component with single isid
        '''
        # PBB EVPN parameters
        pbb_evpn_config = {
            'pbb_evpn_enable': True,
            'mac_learning': True,
            'pbb_etree': False,
            'mac_aging':300,
            'mac_limit': {
                'limit'   :1024,
                'action':'log'
            },
            'mac_move_limit': {
                'limit'   :1024,
                'action':'log',
                'window': 30
            }
        }

        # Bridge domain parameters
        bd = {'count':1,
              'bd1':{'isid':200200},
             }

        # VN parameters
        vn = {'count':1,
              'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
             }

        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
             }

        # Traffic
        traffic = {'count':1,
                   'stream1': {'src':'vm1','dst':'vm2','count':10}
                  }

        # BD to VN mapping parameters
        bd_vn_mapping = {'bd1':'vn1'}

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi1','vmi2']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vn_mapping=bd_vn_mapping,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Verification
        #self.verify_pbb_evpn_config()

        # Traffic
        self.validate_l2_traffic(traffic)

        # Cleanup
        self.delete_pbb_evpn(bd_fixtures=bd_fixtures,vmi_fixtures=vmi_fixtures,
                             vm_fixtures=vm_fixtures, vn_fixtures=vn_fixtures)

    # end test_mac_learning_single_isid


    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_learning_subIntf_single_isid(self):
        '''
            Test MAC learning on I-Component with single isid on sub-interfaces
        '''
        # PBB EVPN parameters
        pbb_evpn_config = {
            'pbb_evpn_enable': True,
            'mac_learning': True,
            'pbb_etree': False,
            'mac_aging':300,
            'mac_limit': {
                'limit'   :1024,
                'action':'log'
            },
            'mac_move_limit': {
                'limit'   :1024,
                'action':'log',
                'window': 30
            }
        }

        # Bridge domain parameters
        bd = {'count':1,
              'bd1':{'isid':200200},}

        # VN parameters
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24'},
              'vn2':{'subnet':'1.1.1.0/24', 'asn':64510, 'target':1},}

        # VMI parameters
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2','parent':'vmi1','vlan':212},
               'vmi4':{'vn': 'vn2','parent':'vmi2','vlan':212},}

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':'user_data1.sh'},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':'user_data1.sh'},}

        # Traffic
        traffic = {'count':1,'traffic_gen':'scapy',
                   'stream1': {'src':'vm1','dst':'vm2','count':10}}


        # BD to VN mapping parameters
        bd_vn_mapping = {'bd1':'vn2'}

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi3','vmi4']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vn_mapping=bd_vn_mapping,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Verification
        #self.verify_pbb_evpn_config()

        # Traffic
        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                #assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send explicit traffic
        self.validate_l2_traffic(traffic=traffic, vm_fixtures=vm_fixtures)

        # Cleanup
        self.delete_pbb_evpn(bd_fixtures=bd_fixtures,vmi_fixtures=vmi_fixtures,
                             vm_fixtures=vm_fixtures, vn_fixtures=vn_fixtures)


    # end test_mac_learning_subIntf_single_isid

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_learning_multi_isid(self):
        '''
            Test MAC learning on I-Component with multiple isids
        '''
        # PBB EVPN parameters
        pbb_evpn_config = {
            'pbb_evpn_enable': True,
            'mac_learning': True,
            'pbb_etree': False,
            'mac_aging':300,
            'mac_limit': {
                'limit'   :1024,
                'action':'log'
            },
            'mac_move_limit': {
                'limit'   :1024,
                'action':'log',
                'window': 30
            }
        }

        # Bridge domain parameters
        bd = {'count':2,
              'bd1':{'isid':200200},
              'bd2':{'isid':300300},
             }

        # VN parameters
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
              'vn2':{'subnet':'20.20.20.0/24', 'asn':64511, 'target':1},
             }

        # VMI parameters
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2'},
               'vmi4':{'vn': 'vn2'},
              }

        # VM parameters
        vm = {'count':4,
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn2'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }

        # Traffic
        traffic = {'count':2,
                   'stream1': {'src':'vm1','dst':'vm2','count':10},
                   'stream2': {'src':'vm3','dst':'vm4','count':10}
                  }

        # BD to VN mapping parameters
        bd_vn_mapping = {'bd1':'vn1',
                         'bd2':'vn2'}

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi1','vmi2'],
                          'bd2':['vmi3','vmi4']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vn_mapping=bd_vn_mapping,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Verification
        #self.verify_pbb_evpn_config()

        # Traffic
        self.validate_l2_traffic(traffic)

        # Cleanup
        self.delete_pbb_evpn(bd_fixtures=bd_fixtures,vmi_fixtures=vmi_fixtures,
                             vm_fixtures=vm_fixtures, vn_fixtures=vn_fixtures)

    # end test_mac_learning_multi_isid

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_learning_subIntf_multi_isid(self):
        '''
            Test MAC learning with sub-interfaces and multiple isid
        '''
        # PBB EVPN parameters
        pbb_evpn_config = {
            'pbb_evpn_enable': True,
            'mac_learning': True,
            'pbb_etree': False,
            'mac_aging':300,
            'mac_limit': {
                'limit'   :1024,
                'action':'log'
            },
            'mac_move_limit': {
                'limit'   :1024,
                'action':'log',
                'window': 30
            }
        }

        # Bridge domain parameters
        bd = {'count':2,
              'bd1':{'isid':200200},
              'bd2':{'isid':300300}
              }

        # VN parameters
        vn = {'count':4,
              'vn1':{'subnet':'10.10.10.0/24'},
              'vn2':{'subnet':'1.1.1.0/24', 'asn':64510, 'target':1},
              'vn3':{'subnet':'20.20.20.0/24'},
              'vn4':{'subnet':'2.2.2.0/24', 'asn':64511, 'target':1}
              }

        # VMI parameters
        vmi = {'count':8,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2','parent':'vmi1','vlan':212},
               'vmi4':{'vn': 'vn2','parent':'vmi2','vlan':212},
               'vmi5':{'vn': 'vn3'},
               'vmi6':{'vn': 'vn3'},
               'vmi7':{'vn': 'vn3','parent':'vmi5','vlan':213},
               'vmi8':{'vn': 'vn3','parent':'vmi6','vlan':213}
               }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':'user_data1.sh'},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':'user_data1.sh'},
              'vm3':{'vn':['vn3'], 'vmi':['vmi5'], 'userdata':'user_data1.sh'},
              'vm4':{'vn':['vn3'], 'vmi':['vmi6'], 'userdata':'user_data1.sh'}
              }

        # Traffic
        traffic = {'count':1,'traffic_gen':'scapy',
                   'stream1': {'src':'vm1','dst':'vm2','count':10},
                   'stream1': {'src':'vm5','dst':'vm6','count':10}
                   }


        # BD to VN mapping parameters
        bd_vn_mapping = {'bd1':'vn2',
                         'bd2':'vn4'}

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi3','vmi4'],
                          'bd2':['vmi7','vmi8']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vn_mapping=bd_vn_mapping,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Verification
        #self.verify_pbb_evpn_config()

        # Traffic
        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send explicit traffic
        self.validate_l2_traffic(traffic=traffic, vm_fixtures=vm_fixtures)

        # Cleanup
        self.delete_pbb_evpn(bd_fixtures=bd_fixtures,vmi_fixtures=vmi_fixtures,
                             vm_fixtures=vm_fixtures, vn_fixtures=vn_fixtures)


    # end test_mac_learning_subIntf_multi_isid



class TestPbbEvpnMacLimit(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacLimit, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacLimit, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_limit(self):
        '''
        '''

        # Configuration parameters

        # Verification

        # Traffic

        # Verification

    # end test_mac_limit

class TestPbbEvpnMacAging(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacAging, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacAging, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_aging(self):
        '''
        '''

        # Configuration parameters

        # Verification

        # Traffic

        # Verification

    # end test_mac_aging

class TestPbbEvpnMacMoveLimit(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacAging, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacAging, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_move_limit(self):
        '''
        '''

        # Configuration parameters

        # Verification

        # Traffic

        # Verification

    # end test_mac_move_limit

