from builtins import str
from builtins import range
from common.pbb_evpn.base import *
from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
import test
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

    @test.attr(type=['cb_sanity', 'sanity'])
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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Send Traffic
        for stream in list(traffic.values()):
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'])

        #Verify mac learned
        for stream in list(traffic.values()):
            sleep(5)
            src_vmi = vm[stream['src']]['vmi'][0]
            assert self.verify_mac_learning(vmi_fixtures[src_vmi],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])
    # end test_mac_learning_single_isid


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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Before pinging, wait till interface is found on VM
        interface = 'eth0.%s' %(VLAN_ID1)
        for src_vm_fixture in list(vm_fixtures.values()):
            assert src_vm_fixture.wait_till_interface_created(interface)

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip, count=2)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Send reverse traffic to verify if mac learned earlier could be used further
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['dst_cmac'], dst_mac=stream['src_cmac'],
                count=stream['count'], interface=interface,
                dst_vm_fixture=vm_fixtures[stream['src']])

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['dst_cmac'])

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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Send Traffic
        for stream in list(traffic.values()):
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'])


        #Verify mac learned

        for stream in list(traffic.values()):

            src_vm = stream['src']
            dst_vm = stream['dst']
            pbb_compute_node_ips = []
            pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
            pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)

            src_vmi = vm[stream['src']]['vmi'][0]
            assert self.verify_mac_learning(vmi_fixtures[src_vmi],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Traffic
        # Pinging all the VMIs as per defined streams in traffic
        for stream in list(traffic.values()):
            vmi_ip = vmi_fixtures[stream['dst_vmi']].get_ip_addresses()[0]
            assert vm_fixtures[stream['src']].ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

        #Verify mac learned
        for stream in list(traffic.values()):
            src_vm = stream['src']
            dst_vm = stream['dst']
            pbb_compute_node_ips = []
            pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
            pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']],  pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Verify mac not learned across BDs
        src_vm = traffic['stream1']['src']
        dst_vm = traffic['stream1']['dst']
        pbb_compute_node_ips = []
        pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
        pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream1']['src_vmi']],
            bd_fixtures[traffic['stream1']['bd']], pbb_compute_node_ips,
            cmac=traffic['stream2']['src_cmac'], expectation=False)

        src_vm = traffic['stream2']['src']
        dst_vm = traffic['stream2']['dst']
        pbb_compute_node_ips = []
        pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
        pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream2']['src_vmi']],
            bd_fixtures[traffic['stream2']['bd']], pbb_compute_node_ips,
            cmac=traffic['stream1']['src_cmac'], expectation=False)

        #Update aging time of bd1, it should not affect aging time of bd2
        mac_aging_time = 5
        bd_fixtures['bd1'].update_bd(mac_aging_time=mac_aging_time)

        #Wait till mac ages out for bd1
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out for bd1
        src_vm = traffic['stream1']['src']
        dst_vm = traffic['stream1']['dst']
        pbb_compute_node_ips = []
        pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
        pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream1']['src_vmi']],
            bd_fixtures[traffic['stream1']['bd']], pbb_compute_node_ips,
            cmac=traffic['stream1']['src_cmac'], expectation=False)

        #Verify mac not aged out for bd2
        src_vm = traffic['stream2']['src']
        dst_vm = traffic['stream2']['dst']
        pbb_compute_node_ips = []
        pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
        pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
        assert self.verify_mac_learning(vmi_fixtures[traffic['stream2']['src_vmi']],
            bd_fixtures[traffic['stream2']['bd']], pbb_compute_node_ips,
            cmac=traffic['stream2']['src_cmac'])

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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (MAC_AGING_DEFAULT))
        sleep(MAC_AGING_DEFAULT)
        #Verify mac aged out
        for stream in list(traffic.values()):
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']],  pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)
    # end test_mac_aging_default

    @preposttest_wrapper
    def test_mac_aging_dynamic_update(self):
        '''
        Test updating mac aging dynamically and then verify C-MAC ageout
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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Update the mac aging time of BD
        mac_aging_time = 5
        bd_fixtures['bd1'].update_bd(mac_aging_time=mac_aging_time)

        #Send reverse traffic and verify mac learning after aging time update
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['dst_cmac'], dst_mac=stream['src_cmac'],
                count=stream['count'], interface=interface,
                dst_vm_fixture=vm_fixtures[stream['src']])

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['dst_cmac'])

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out
        for stream in list(traffic.values()):
            #For forward traffic
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)
            #For reverse traffic
            assert self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['dst_cmac'], expectation=False)

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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Wait for sometime to verify mac not aged out
        self.logger.info("Waiting for %s seconds"
            % (MAC_AGING_DEFAULT))
        sleep(MAC_AGING_DEFAULT)

        #Verify mac not aged out
        for stream in list(traffic.values()):
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])


        #Update the mac aging time of BD, after this mac should age out
        mac_aging_time = 2
        bd_fixtures['bd1'].update_bd(mac_aging_time=mac_aging_time)

        #Wait till learnt mac aged out
        self.logger.info("Waiting for %s seconds, till learnt C-MAC ages out.."
            % (mac_aging_time))
        sleep(mac_aging_time)

        #Verify mac aged out
        for stream in list(traffic.values()):
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)
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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Mac move
        #Send the reverse traffic using earlier learnt C-MAC as src C-MAC from remote VMI,
        #to get the C-MAC moved and verify it further
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            for i in range(0,5):
                #Verify mac movement
                result = self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                    bd_fixtures[stream['bd']], pbb_compute_node_ips,
                    cmac=stream['src_cmac'])
                #Wait for few seconds before retrying mac move verification, agent introspect may take sometime to update
                sleep(2)

        assert result, ("Mac move verification failed")
    #end test_mac_move

class TestPbbEvpnPbbBridgeDomainConfig(PbbEvpnTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestPbbEvpnPbbBridgeDomainConfig, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestPbbEvpnPbbBridgeDomainConfig, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_mac_learning_disable_at_bd(self):
        '''
            Test disabling MAC learning at BD level
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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        #Disable Mac learning in BD
        bd_fixtures['bd1'].update_bd(mac_learning_enabled=False)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac not learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)

        #Enable Mac learning in BD
        bd_fixtures['bd1'].update_bd(mac_learning_enabled=True)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

    # end test_mac_learning_disable_at_bd

    @preposttest_wrapper
    def test_change_isid_at_bd(self):
        '''
            Test changing ISID dynamically:
                Verify learning, forwarding happens properly after ISID change
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
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'])

        #Change ISID in BD
        old_isid = bd_fixtures['bd1'].isid
        new_isid = bd_fixtures['bd1'].isid + 1
        bd_fixtures['bd1'].update_bd(isid=new_isid)

        for stream in list(traffic.values()):
            #Verify already learnt C-MAC is deleted
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)

        #Send reverse traffic after ISID change
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['dst']].get_vm_interface_name() + '.' + \
                str(vmi[stream['dst_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['dst']],
                src_mac=stream['dst_cmac'], dst_mac=stream['src_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['dst_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['dst_cmac'])

    # end test_change_isid_at_bd

    @preposttest_wrapper
    def test_negative_cases_for_bd(self):
        '''
            Test negative cases for bridge domains:
                1. Verify VN can have only 1 BD
                2. Verify bridge domain, along with vlan-tag can be added to VMI
                3. Verify multiple bridge domains can not be added to single VMI
                    and VMI and BD should be in same VN
        '''
        result = True
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        vn = BASIC_PBB_RESOURCES['vn']
        vmi_dict = BASIC_PBB_RESOURCES['vmi']

        # Bridge domain parameters
        bd = {'count':2,
              'bd1':{'isid':100100, 'vn':'vn1'},
              'bd2':{'isid':200200, 'vn':'vn2'},
              'bd3':{'isid':300300, 'vn':'vn1'},
             }
        # BD to VMI mapping parameters
        bd_vmi_mapping = {'bd2':['vmi3'],
                         }

        pbb_evpn_enable = pbb_evpn_config.get('pbb_evpn_enable', True)
        mac_learning_enabled = pbb_evpn_config.get('mac_learning_enabled', True)
        mac_limit = pbb_evpn_config.get('mac_limit').get('limit',1024)
        mac_limit_action = pbb_evpn_config.get('mac_limit').get('action','log')

        # MAC Move Limit parameters
        mac_move_limit = pbb_evpn_config.get('mac_move_limit').get('limit',1024)
        mac_move_limit_action = pbb_evpn_config.get('mac_move_limit').get('action','log')
        mac_move_time_window = pbb_evpn_config.get('mac_move_limit').get('window',60)

        # MAC Aging parameters
        mac_aging_time = pbb_evpn_config.get('mac_aging',300)

        # MAC Limit and MAC Move limit objects
        mac_limit_obj = MACLimitControlType(mac_limit=mac_limit,
                                            mac_limit_action=mac_limit_action)
        mac_move_limit_obj = MACMoveLimitControlType(mac_move_limit=mac_move_limit,
                                                     mac_move_limit_action=mac_move_limit_action,
                                                     mac_move_time_window=mac_move_time_window)

        # VNs creation
        vn_fixtures = self.setup_vns(vn)

        # Bridge domains creation
        bd_fixtures = self.setup_bds(vn_fixtures,
                            mac_learning_enabled,
                            mac_limit_obj,
                            mac_move_limit_obj,
                            mac_aging_time, bd)

        test_bd = 'bd3'
        vn_uuid = vn_fixtures[bd[test_bd]['vn']].uuid
        bd_uuid = bd_fixtures['bd1'].bd_uuid
        bd_error = PBB_EVPN_API_ERROR_MSGS['vn_can_have_one_bd'] % (
            vn_uuid, bd_uuid)
        #Verify VN can have only 1 BD
        try:
            vn_obj = self.vnc_h.virtual_network_read(id=vn_uuid)
            bd_fixture = self.create_bd(parent_obj=vn_obj,
                                  mac_learning_enabled=mac_learning_enabled,
                                  mac_limit_control=mac_limit_obj,
                                  mac_move_control=mac_move_limit_obj,
                                  mac_aging_time=mac_aging_time,
                                  isid=bd[test_bd]['isid'])
        except Exception as msg:
            assert msg.status_code == 400
            assert msg.content == bd_error
        else:
            self.logger.error("Able to add more than 1 BD in a VN, test failed")
            result = False

        # VMIs creation
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi_dict)

        #Verify bridge domain, along with vlan-tag can be added to VMI
        vlan_tag = 100
        for bd, vmi_list in bd_vmi_mapping.items():
            bd_fixture = bd_fixtures[bd]
            for vmi in vmi_list:
                vmi_fixture = vmi_fixtures[vmi]
                assert bd_fixture.add_bd_to_vmi(vmi_fixture.uuid, vlan_tag,
                    verify=False)

        test_vmi = 'vmi3'
        test_bd = 'bd1'
        vmi_uuid = vmi_fixtures[test_vmi].uuid
        vn_uuid = vn_fixtures[vmi_dict[test_vmi]['vn']].uuid
        vmi_bd_error = PBB_EVPN_API_ERROR_MSGS['vmi_bd_in_same_vn'] % (
            vmi_uuid, vn_uuid)
        bd_fixture = bd_fixtures[test_bd]
        vmi_fixture = vmi_fixtures[test_vmi]

        #Verify multiple bridge domains can not be added to single VMI and VMI and BD should be in same VN
        try:
            bd_fixture.add_bd_to_vmi(vmi_fixture.uuid, vlan_tag, verify=False)
        except Exception as msg:
            assert msg.status_code == 400
            assert msg.content == vmi_bd_error
        else:
            self.logger.error("Able to add BD in VMI from different VN, test failed")
            result = False
    #end test_negative_cases_for_bd

    @preposttest_wrapper
    def test_swap_isids_on_bds(self):
        '''
            Test swapping the ISIDs on 2 bridge domains and verify the functionality
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG

        vn = PBB_RESOURCES_TWO_ISID['vn']
        bd = PBB_RESOURCES_TWO_ISID['bd']
        vmi = PBB_RESOURCES_TWO_ISID['vmi']
        vm = PBB_RESOURCES_TWO_ISID['vm']
        traffic = PBB_RESOURCES_TWO_ISID['traffic']
        bd_vmi_mapping = PBB_RESOURCES_TWO_ISID['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
                                       bd=bd, vn=vn, vmi=vmi, vm=vm,
                                       bd_vmi_mapping=bd_vmi_mapping)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Traffic
        # Pinging all the VMIs as per defined streams in traffic
        for stream in list(traffic.values()):
            vmi_ip = vmi_fixtures[stream['dst_vmi']].get_ip_addresses()[0]
            assert vm_fixtures[stream['src']].ping_with_certainty(vmi_ip)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

        # Swap the ISIDs. 
        sleep(10)
        bd_fixtures['bd1'].update_bd(isid=bd['bd2']['isid'])
        sleep(10)
        bd_fixtures['bd2'].update_bd(isid=bd['bd1']['isid'])
        sleep(70)

        #Verify C-MACs get deleted
        for stream in list(traffic.values()):

            src_vm = stream['src']
            dst_vm = stream['dst']
            pbb_compute_node_ips = []
            pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
            pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)

            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)

        # Send Traffic again
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

        #Verify C-MACs learnt again
        for stream in list(traffic.values()):
            src_vm = stream['src']
            dst_vm = stream['dst']
            pbb_compute_node_ips = []
            pbb_compute_node_ips.append(vm_fixtures[src_vm]._vm_node_ip)
            pbb_compute_node_ips.append(vm_fixtures[dst_vm]._vm_node_ip)
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips, cmac=stream['src_cmac'])

    #end test_swap_isids_on_bds

    @preposttest_wrapper
    def  test_zero_isid_config(self):
        '''
            Test BD creation with ISID=0
                then changing the value to non-zero ISID, verify mac learning and forwarding
                then change ISID to zero again and verify if C-MACs gets flushed out
        '''
        # PBB EVPN parameters
        pbb_evpn_config = PBB_EVPN_CONFIG
        test_bd = 'bd1'
        vn = BASIC_PBB_RESOURCES['vn']
        bd = BASIC_PBB_RESOURCES['bd']
        bd[test_bd]['isid'] = 0
        vmi = BASIC_PBB_RESOURCES['vmi']
        vm = BASIC_PBB_RESOURCES['vm']
        traffic = BASIC_PBB_RESOURCES['traffic']
        bd_vmi_mapping = BASIC_PBB_RESOURCES['bd_vmi_mapping']

        ret_dict = self.setup_pbb_evpn(pbb_evpn_config=pbb_evpn_config,
            bd=bd, vn=vn, vmi=vmi, vm=vm,
            bd_vmi_mapping=bd_vmi_mapping,
            verify=False)
        bd_fixtures = ret_dict['bd_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        pbb_compute_node_ips = ret_dict['pbb_compute_node_ips']

        # Pinging all the VMIs
        for src_vm_fixture in list(vm_fixtures.values()):
            for vmi_fixture in list(vmi_fixtures.values()):
                vmi_ip = vmi_fixture.get_ip_addresses()[0]
                try:
                    socket.inet_aton(vmi_ip)
                except Exception as e:
                    vmi_ip = vmi_fixture.get_ip_addresses()[1]
                assert src_vm_fixture.ping_with_certainty(vmi_ip)

        #Verification for adding BD with ISID 0 to VMI should fail
        vlan_tag = 0
        for bd_name, vmi_list in bd_vmi_mapping.items():
            bd_fixture = bd_fixtures[bd_name]
            for vmi_name in vmi_list:
                vmi_fixture = vmi_fixtures[vmi_name]
                assert not bd_fixture.add_bd_to_vmi(vmi_fixture.uuid, vlan_tag,
                    verify=True)

        #Change ISID to non-zero
        bd_fixtures[test_bd].update_bd(isid=1)

        # Send Traffic
        for stream in list(traffic.values()):
            interface = vm_fixtures[stream['src']].get_vm_interface_name() + '.' + \
                str(vmi[stream['src_vmi']]['vlan'])
            self.send_l2_traffic(vm_fixtures[stream['src']],
                src_mac=stream['src_cmac'], dst_mac=stream['dst_cmac'],
                count=stream['count'], interface=interface)

            #Verify mac learned
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips, cmac=stream['src_cmac'])

        # Filed CEM-3673 . On changing back isid to any non zero value mac is getting flushed out. 0 is not a valid isid value

        #Revert back isid to 0
        bd_fixtures[test_bd].update_bd(isid=5)

        #Verify mac flushed out
        for stream in list(traffic.values()):
            assert self.verify_mac_learning(vmi_fixtures[stream['src_vmi']],
                bd_fixtures[stream['bd']], pbb_compute_node_ips,
                cmac=stream['src_cmac'], expectation=False)

    #end test_bd_with_isid_zero
