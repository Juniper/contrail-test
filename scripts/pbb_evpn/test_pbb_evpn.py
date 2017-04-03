from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
import test

from common.pbb_evpn.base import *

from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
import socket

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from tcutils.util import get_random_mac
from time import sleep

class TestPbbEvpnMacLearning(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacLearning, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacLearning, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mac_learning_single_isid(self):
        '''
            Test MAC learning on I-Component with single isid
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        # VN parameters
        vn = {'count':1,
              'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
             }

        # Bridge domain parameters
        bd = {'count':1,
              'bd1':{'isid':200200,'vn':'vn1'},
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
        traffic = {
                   'stream1': {'src':'vm1','dst':'vm2','count':10,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd1'}
                  }

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi1','vmi2']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Send Traffic
        for stream in traffic.values():
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'])

        #Verify mac learned
        for stream in traffic.values():
            src_vmi = vm[stream['src']]['vmi'][0]
            assert self.verify_mac_learning(vmi_fixtures[src_vmi],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])
    # end test_mac_learning_single_isid


    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mac_learning_subIntf_single_isid(self):
        '''
            Test MAC learning on I-Component with single isid on sub-interfaces
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Send reverse traffic to verify if mac learned earlier could be used further
        for stream in traffic.values():
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['dst_cmac'], dst_mac=stream['src_cmac'],
                count=stream['count'], interface=interface,
                dst_vm_fixture=vm_fixtures[stream['src']])

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['dst_cmac'])

    # end test_mac_learning_subIntf_single_isid

    @preposttest_wrapper
    def test_mac_learning_multi_isid(self):
        '''
            Test MAC learning on I-Component with multiple isids
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        # VN parameters
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
              'vn2':{'subnet':'20.20.20.0/24', 'asn':64511, 'target':1},
             }

        # Bridge domain parameters
        bd = {'count':2,
              'bd1':{'isid':200200, 'vn':'vn1'},
              'bd2':{'isid':300300, 'vn':'vn2'},
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
        traffic = {
                   'stream1': {'src':'vm1','dst':'vm2','count':10,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd1'},
                   'stream2': {'src':'vm3','dst':'vm4','count':10,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd2'}
                  }

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi1','vmi2'],
                          'bd2':['vmi3','vmi4']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Send Traffic
        for stream in traffic.values():
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'])

        #Verify mac learned
        for stream in traffic.values():
            src_vmi = vm[stream['src']]['vmi'][0]
            assert self.verify_mac_learning(vmi_fixtures[src_vmi],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

    # end test_mac_learning_multi_isid

    @preposttest_wrapper
    def test_mac_learning_subIntf_multi_isid(self):
        '''
            Test MAC learning with sub-interfaces and multiple isid
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        # VN parameters
        vn = {'count':4,
              'vn1':{'subnet':'10.10.10.0/24'},
              'vn2':{'subnet':'1.1.1.0/24', 'asn':64510, 'target':1},
              'vn3':{'subnet':'20.20.20.0/24'},
              'vn4':{'subnet':'2.2.2.0/24', 'asn':64511, 'target':1}
              }

        # Bridge domain parameters
        bd = {'count':2,
              'bd1':{'isid':200200, 'vn':'vn2'},
              'bd2':{'isid':300300, 'vn':'vn4'}
              }

        # VMI parameters
        vmi = {'count':8,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2','parent':'vmi1','vlan':212},
               'vmi4':{'vn': 'vn2','parent':'vmi2','vlan':212},
               'vmi5':{'vn': 'vn3'},
               'vmi6':{'vn': 'vn3'},
               'vmi7':{'vn': 'vn4','parent':'vmi5','vlan':213},
               'vmi8':{'vn': 'vn4','parent':'vmi6','vlan':213}
               }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                'vlan': str(vmi['vmi3']['vlan'])} },
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                'vlan': str(vmi['vmi4']['vlan'])} },
              'vm3':{'vn':['vn3'], 'vmi':['vmi5'], 'userdata':{
                'vlan': str(vmi['vmi7']['vlan'])} },
              'vm4':{'vn':['vn3'], 'vmi':['vmi6'], 'userdata':{
                'vlan': str(vmi['vmi8']['vlan'])} }
              }

        # Traffic
        traffic = {
                   'stream1': {'src':'vm1','dst':'vm2','count':10,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd1', 'src_vmi': 'vmi3',
                                'dst_vmi': 'vmi4'},
                   'stream2': {'src':'vm3','dst':'vm4','count':10,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd2', 'src_vmi': 'vmi7',
                                'dst_vmi': 'vmi8'}
                  }

        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd1':['vmi3','vmi4'],
                          'bd2':['vmi7','vmi8']}

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Traffic
        # Pinging all the VMIs as per defined streams in traffic
        for stream in traffic.values():
            vmi_ip = vmi_fixtures[stream['dst_vmi']].obj['fixed_ips'][0]['ip_address']
            assert vm_fixtures[stream['src']].ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Update aging time of bd1, it should not affect aging time of bd2 
        mac_aging_time = 5
        self.connections.vnc_lib_fixture.vnc_h.update_bd(uuid=bd_fixtures['bd1'].bd_uuid,
            mac_aging_time=mac_aging_time)

        #Wait till mac ages out for bd1
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out for bd1
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream1']['src_vmi']],
            bd_fixtures[traffic['stream1']['bd']], cmac=traffic['stream1']['src_cmac'],
            expectation=False)

        #Verify mac not aged out for bd2
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream2']['src_vmi']],
            bd_fixtures[traffic['stream2']['bd']], cmac=traffic['stream2']['src_cmac'])

    # end test_mac_learning_subIntf_multi_isid

class TestPbbEvpnMacAging(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacAging, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacAging, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mac_aging_default(self):
        '''
        Test with default mac aging timeout 300 seconds, after which learnt C-MAC should be aged out
        '''

        pbb_evpn_config = PBB_EVPN_CONFIG
        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (MAC_AGING_DEFAULT))
        sleep(MAC_AGING_DEFAULT)
        #Verify mac aged out
        for stream in traffic.values():
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'],
                expectation=False)
    # end test_mac_aging_default 

    @preposttest_wrapper
    def test_mac_aging_dynamic_update(self):
        '''
        Test with default mac aging timeout 300 seconds, after which learnt C-MAC should be aged out
        '''

        pbb_evpn_config = PBB_EVPN_CONFIG
        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Update the mac aging time of BD
        mac_aging_time = 5
        self.connections.vnc_lib_fixture.vnc_h.update_bd(uuid=bd_fixtures['bd1'].bd_uuid,
            mac_aging_time=mac_aging_time)

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out
        for stream in traffic.values():
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'],
                expectation=False)

    # end test_mac_aging_dynamic_update

    @preposttest_wrapper
    def test_mac_aging_zero(self):
        '''
        Test with mac aging timeout 0, C-MAC should not age out 
        '''

        pbb_evpn_config = PBB_EVPN_CONFIG
        pbb_evpn_config['mac_aging'] = 0
        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Wait for sometime to verify mac not aged out 
        self.logger.info("Waiting for %s seconds"
            % (MAC_AGING_DEFAULT))
        sleep(MAC_AGING_DEFAULT)

        #Verify mac not aged out
        for stream in traffic.values():
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])


        #Update the mac aging time of BD, after this mac should age out
        mac_aging_time = 2
        self.connections.vnc_lib_fixture.vnc_h.update_bd(uuid=bd_fixtures['bd1'].bd_uuid,
            mac_aging_time=mac_aging_time)

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out
        for stream in traffic.values():
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'],
                expectation=False)
    #end test_mac_aging_zero

class TestPbbEvpnMacMove(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnMacMove, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnMacMove, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mac_move(self):
        '''
        Verify Mac is moved to new vrouter when mac movement detected
        '''
        pbb_evpn_config = PBB_EVPN_CONFIG
        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for vmi_fixture in vmi_fixtures.values():
                vmi_ip = vmi_fixture.obj['fixed_ips'][0]['ip_address']
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.obj['fixed_ips'][1]['ip_address']
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in traffic.values():
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], cmac=stream['src_cmac'])

        #Mac move
        #Send the reverse traffic using earlier learnt C-MAC as src C-MAC from remote VMI,
        #to get the C-MAC moved and verify it further
        for stream in traffic.values():
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            for i in xrange(0,5):
                #Verify mac movement
                result = self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                    bd_fixtures[stream['bd']], cmac=stream['src_cmac'])
                #Wait for few seconds before retrying mac move verification, agent introspect may take sometime to update
                sleep(2)

        assert result, ("Mac move verification failed")
    #end test_mac_move
