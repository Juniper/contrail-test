import re
from vnc_api.vnc_api import *

from common.vrouter.base import BaseVrouterTest
from bridge_domain_fixture import BDFixture
from common.neutron.base import BaseNeutronTest
from compute_node_test import ComputeNodeFixture
from common.base import GenericTestBase
from common.vrouter.base import BaseVrouterTest

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic

import random
from netaddr import *
from tcutils.util import retry, get_random_mac
from tcutils.tcpdump_utils import *


USER_DATA = """#!/bin/bash

echo \"auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
auto eth0.%s
iface eth0.%s inet dhcp
vlan-raw-device eth0\" > /etc/network/interfaces

/etc/init.d/networking restart"""

MAC_AGING_DEFAULT = 300 #in Seconds

PBB_EVPN_CONFIG = {
    'pbb_evpn_enable': True,
    'mac_learning': True,
    'pbb_etree': False,
    'mac_aging':MAC_AGING_DEFAULT,
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
VLAN_ID1 = 212
VLAN_ID2 = 213
PBB_RESOURCES_SINGLE_ISID = {

        # VN parameters
        'vn': {'count':2,
              'vn1':{'subnet':'10.10.10.0/24'},
              'vn2':{'subnet':'1.1.1.0/24', 'asn':64510, 'target':1},},

        # Bridge domain parameters
        'bd': {'count':1,
              'bd1':{'isid':200200,'vn':'vn2'}},

        # VMI parameters
        'vmi': {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2','parent':'vmi1','vlan':VLAN_ID1},
               'vmi4':{'vn': 'vn2','parent':'vmi2','vlan':VLAN_ID1},},

        # VM parameters
        'vm': {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                'vlan':str(VLAN_ID1)} },
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                'vlan':str(VLAN_ID1)} }
            },

        # Traffic
        'traffic': {
                   'stream1': {'src':'vm1','dst':'vm2','count':5,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd1', 'src_vmi': 'vmi3',
                                'dst_vmi': 'vmi4'}
                  },

        # BD to VMI mapping parameters
        'bd_vmi_mapping': {'bd1':['vmi3','vmi4']}
}

PBB_RESOURCES_TWO_ISID = {
        # VN parameters
        'vn': {'count':4,
              'vn1':{'subnet':'10.10.10.0/24'},
              'vn2':{'subnet':'1.1.1.0/24', 'asn':64510, 'target':1},
              'vn3':{'subnet':'20.20.20.0/24'},
              'vn4':{'subnet':'2.2.2.0/24', 'asn':64511, 'target':1}
              },

        # Bridge domain parameters
        'bd': {'count':2,
              'bd1':{'isid':200200, 'vn':'vn2'},
              'bd2':{'isid':300300, 'vn':'vn4'}
              },

        # VMI parameters
        'vmi': {'count':8,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2','parent':'vmi1','vlan':VLAN_ID1},
               'vmi4':{'vn': 'vn2','parent':'vmi2','vlan':VLAN_ID1},
               'vmi5':{'vn': 'vn3'},
               'vmi6':{'vn': 'vn3'},
               'vmi7':{'vn': 'vn4','parent':'vmi5','vlan':VLAN_ID2},
               'vmi8':{'vn': 'vn4','parent':'vmi6','vlan':VLAN_ID2}
               },

        # VM parameters
        'vm': {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                'vlan': str(VLAN_ID1)} },
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                'vlan': str(VLAN_ID1)} },
              'vm3':{'vn':['vn3'], 'vmi':['vmi5'], 'userdata':{
                'vlan': str(VLAN_ID2)} },
              'vm4':{'vn':['vn3'], 'vmi':['vmi6'], 'userdata':{
                'vlan': str(VLAN_ID2)} }
              },

        # Traffic
        'traffic': {
                   'stream1': {'src':'vm1','dst':'vm2','count':5,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd1', 'src_vmi': 'vmi3',
                                'dst_vmi': 'vmi4'},
                   'stream2': {'src':'vm3','dst':'vm4','count':5,
                                'src_cmac': get_random_mac(),
                                'dst_cmac': get_random_mac(),
                                'bd': 'bd2', 'src_vmi': 'vmi7',
                                'dst_vmi': 'vmi8'}
                  },

        # BD to VMI mapping parameters
        'bd_vmi_mapping': {'bd1':['vmi3','vmi4'],
                          'bd2':['vmi7','vmi8']},
}

BASIC_PBB_RESOURCES = PBB_RESOURCES_SINGLE_ISID
PBB_EVPN_API_ERROR_MSGS = {
    'vn_can_have_one_bd': "Virtual network(%s) can have only one bridge domain. Bridge domain(%s) is already created under this virtual network",
    'vmi_bd_in_same_vn': "Virtual machine interface(%s) can only refer to bridge domain belonging to virtual network(%s)",
}

class PbbEvpnTestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(PbbEvpnTestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def config_encap_priority(self, encap='udp'):
        '''pbb evpn is supported only for MPLSoUDP and MPLSoGRE encap.
           vxlan is not supported
           Configuring encap priority and restoring the prev encap priority
           at cleanup
        '''

        # Other than MPLSoGRE, MPLSoUDP encapuslations are not supported
        if encap != 'udp' and encap != 'gre':
            result = False
            assert result,'Invalid Encapsulation'

        self.logger.debug("Read the existing encap priority")
        existing_encap = self.connections.read_vrouter_config_encap()

        if encap == 'gre':
            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
            self.logger.info(
                'Created.UUID is %s. MPLSoGRE is the highest priority encap' %
                (config_id))
            configured_encap_list = [
                unicode('MPLSoGRE'), unicode('MPLSoUDP'), unicode('VXLAN')]
        elif encap == 'udp':
            pbb_encap = self.connections.update_vrouter_config_encap(
                    'MPLSoUDP', 'MPLSoGRE', 'VXLAN')
            self.logger.info(
                'Created.UUID is %s. MPLSoUDP is the highest priority encap' %
                (pbb_encap))
            configured_encap_list = [
                unicode('MPLSoUDP'), unicode('MPLSoGRE'), unicode('VXLAN')]
        if existing_encap != configured_encap_list :
            self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])


    def update_vms_for_pbb(self, vm_fixtures):
        '''update /etc/hosts with local hostname to avoid DNS resolution
            for cmds with sudo
        '''
        for vm in vm_fixtures:
            cmd = "echo \"%s %s\" >> /etc/hosts" % (vm.vm_ip, vm.vm_name)
            vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

    def create_user_data(self, vlan):
        '''
            Creates the user-data using given vlan id and returns file obj
        '''
        import tempfile
        file_obj = tempfile.NamedTemporaryFile()
        user_data = USER_DATA % (vlan, vlan)

        file_obj.write(user_data)
        file_obj.seek(0)
        return file_obj

    def create_bd(self, parent_obj, bd_name=None, **kwargs):
        cleanup = kwargs.get('cleanup', True)
        bd_fixture = BDFixture(parent_obj, bd_name=bd_name,
                                connections=self.connections,
                                **kwargs)
        bd_fixture.setUp()
        if cleanup:
            self.addCleanup(bd_fixture.cleanUp)
        return bd_fixture

    def verify_bds(self, bd_fixtures):
        for bd in bd_fixtures:
            assert bd.verify_on_setup()

    def setup_vns(self, vn=None):
        '''
        Input vn format:
            vn = {'count':1,
                  'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
                 }
        '''
        vn_count = vn['count'] if vn else 1
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            if vn_id in vn:
                vn_subnet = vn[vn_id].get('subnet',None)
                asn = vn[vn_id].get('asn',None)
                target= vn[vn_id].get('target',None)

                # Layer2 control word
                l2cw = vn[vn_id].get('l2cw',True)
                vn_fixture = self.create_vn(vn_name=vn_id, vn_subnets=[vn_subnet],
                                                 router_asn=asn, rt_number=target)
                assert vn_fixture.set_layer2_control_word(l2cw)
            else:
                vn_fixture = self.create_vn(vn_name=vn_id)
            vn_fixtures[vn_id] = vn_fixture

        return vn_fixtures

    def setup_bds(self, vn_fixtures,
            mac_learning_enabled,
            mac_limit_obj,
            mac_move_limit_obj,
            mac_aging_time, bd=None):
        '''
        Input bd format:
            bd = {'count':1,
                  'bd1':{'isid':200200,'vn':'vn1'},
                 }
        '''
        bd_count = bd['count'] if bd else 1
        bd_fixtures = {} # Hash to store BD fixtures
        for i in range(0,bd_count):
            bd_id = 'bd'+str(i+1)
            vn = bd[bd_id]['vn']
            if bd_id in bd:
                bd_isid = bd[bd_id].get('isid',0)
            else:
                bd_isid=randint(1,2**24-1)
            vn_obj = self.vnc_h.virtual_network_read(id=vn_fixtures[vn].uuid)
            bd_fixture = self.create_bd(parent_obj=vn_obj,
                                  mac_learning_enabled=mac_learning_enabled,
                                  mac_limit_control=mac_limit_obj,
                                  mac_move_control=mac_move_limit_obj,
                                  mac_aging_time=mac_aging_time,
                                  isid=bd_isid)
            bd_fixtures[bd_id] = bd_fixture

        self.verify_bds(bd_fixtures.values())

        return bd_fixtures

    def setup_vmis(self, vn_fixtures, vmi=None):
        '''
        Input vmi format:
            vmi = {'count':2,
                   'vmi1':{'vn': 'vn1'},
                   'vmi2':{'vn': 'vn1'},
                  }
        '''
        vmi_count = vmi['count'] if vmi else 1
        vmi_fixtures = {} # Hash to store VMI fixtures
        for i in range(0,vmi_count):
            vmi_id = 'vmi'+str(i+1)
            if vmi_id in vmi:
                vmi_vn = vmi[vmi_id]['vn']
                vn_fixture = vn_fixtures[vmi_vn]
                parent_vmi = vmi[vmi_id].get('parent',None)
                # VMI is Sub-interface
                if parent_vmi:
                    parent_vmi_fixture = vmi_fixtures[parent_vmi]
                    vlan = vmi[vmi_id].get('vlan',0)
                    vmi_fixture = self.setup_vmi(vn_fixture.uuid,
                                                      parent_vmi=parent_vmi_fixture.vmi_obj,
                                                      vlan_id=vlan,
                                                      api_type='contrail',
                                                      mac_address=parent_vmi_fixture.mac_address)
                    # Disable Policy on sub-interfaces
                    self.vnc_h.disable_policy_on_vmi(vmi_fixture.uuid,
                        vmi[vmi_id].get('disable_policy',True))
                else:
                    vmi_fixture = self.setup_vmi(vn_fixture.uuid)
            else:
                vmi_vn = 'vn'+str(i+1)
                vn_fixture = vn_fixtures[vmi_vn]
                vmi_fixture = self.setup_vmi(vn_fixture.uuid)
            vmi_fixtures[vmi_id] = vmi_fixture

        return vmi_fixtures

    def setup_vms(self, vn_fixtures, vmi_fixtures, vm=None):
        '''
        Input vm format:
            vm = {'count':2, 'launch_mode':'distribute',
                  'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                    'vlan': str(vmi['vmi3']['vlan'])} },
                  'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                    'vlan': str(vmi['vmi4']['vlan'])} }
                }
            launch_mode can be distribute or non-distribute
        '''
        vm_count = vm['count'] if vm else 1
        launch_mode = vm.get('launch_mode','default')
        vm_fixtures = {} # Hash to store VM fixtures

        compute_nodes = self.orch.get_hosts()
        compute_nodes_len = len(compute_nodes)
        index = random.randint(0,compute_nodes_len-1)
        for i in range(0,vm_count):
            vm_id = 'vm'+str(i+1)
            vn_list = vm[vm_id]['vn']
            vmi_list = vm[vm_id]['vmi']
            # Get the userdata related to sub interfaces
            userdata = vm[vm_id].get('userdata',None)
            userdata_file = None
            if userdata:
                file_obj = self.create_user_data(userdata['vlan'])
                userdata_file = file_obj.name

            vn_fix_obj_list =[]
            vmi_fix_uuid_list =[]

            # Build the VN fixtures objects
            for vn in vn_list:
                vn_fix_obj_list.append(vn_fixtures[vn].obj)

           # Build the VMI UUIDs
            for vmi in vmi_list:
                vmi_fix_uuid_list.append(vmi_fixtures[vmi].uuid)

            # VM launch mode handling
            # Distribute mode, generate the new random index
            # Non Distribute mode, use previously generated index
            # Default mode, Nova takes care of launching
            if launch_mode == 'distribute':
                index = i%compute_nodes_len
                node_name = self.inputs.compute_names[index]
            elif launch_mode == 'non-distribute':
                node_name = self.inputs.compute_names[index]
            elif launch_mode == 'default':
                node_name=None

            vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                        port_ids=vmi_fix_uuid_list,
                                        userdata=userdata_file,
                                        node_name=node_name)
            vm_fixtures[vm_id] = vm_fixture
            if userdata:
                file_obj.close()

        for vm_fixture in vm_fixtures.values():
            assert vm_fixture.wait_till_vm_is_up()
        self.update_vms_for_pbb(vm_fixtures.values())

        return vm_fixtures

    def setup_pbb_evpn(self,pbb_evpn_config=None, bd=None, vn=None, vmi=None,
                       vm=None, bd_vmi_mapping=None, verify=True):
        '''
            Setup PBB EVPN Configuration.

            Sets up PBB EVPN configuration on global level, BD level, VN level,
            VMI level

            Input parameters looks like:
                #PBB EVPN parameters:
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
                #Bridge domain parameters:
                bd = {'count':1,            # Bridge domain count
                    'bd1':{'isid':200200},  # Bridge domain details
                    }

                #VN parameters:
                vn = {'count':1,            # VN count
                     # VN Details
                    'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
                    }

                #VMI parameters:
                vmi = {'count':2, # VMI Count
                    'vmi1':{'vn': 'vn1'}, # VMI details
                    'vmi2':{'vn': 'vn1'}, # VMI details
                    }

                #VM parameters:
                vm = {'count':2, # VM Count
                    # VM Launch mode i.e distribute non-distribute, default
                    'launch_mode':'distribute',
                    'vm1':{'vn':['vn1'], 'vmi':['vmi1']}, # VM Details
                    'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # VM Details
                    }

                #BD to VMI mapping parameters:
                bd_vmi_mapping = {'bd1':['vmi1','vmi2']}

            Configures BD to VN mapping

            Configures BD to VMI mapping
        '''

        # Base PBB EVPN config
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

        # PBB E-Tree parameters
        pbb_etree_enable =  pbb_evpn_config.get('pbb_etree',False)


        # MAC Limit and MAC Move limit objects
        mac_limit_obj = MACLimitControlType(mac_limit=mac_limit,
                                            mac_limit_action=mac_limit_action)
        mac_move_limit_obj = MACMoveLimitControlType(mac_move_limit=mac_move_limit,
                                                     mac_move_limit_action=mac_move_limit_action,
                                                     mac_move_time_window=mac_move_time_window)

        # Configuring the encapsulation priority. Supported enacps are:
        # MPLSoUDP and MPLSoGRE. VXLAN is not supported.
        self.config_encap_priority('udp')

        # VNs creation
        vn_fixtures = self.setup_vns(vn)

        # Bridge domains creation
        bd_fixtures = self.setup_bds(vn_fixtures,
                            mac_learning_enabled,
                            mac_limit_obj,
                            mac_move_limit_obj,
                            mac_aging_time, bd)

        # VMIs creation
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)

        # VMs creation
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm)

        # Compute nodes, where vms have launched, pbb verification
        # needs to be checked on these compute nodes
        pbb_compute_node_ips = []
        for vm_fixture in vm_fixtures:
            pbb_compute_node_ips.append(vm_fixtures[vm_fixture]._vm_node_ip)

        # PBB EVPN VN configuration
        for vn_fixture in vn_fixtures.values():
            assert vn_fixture.set_pbb_evpn_enable(pbb_evpn_enable=pbb_evpn_enable)
            assert vn_fixture.set_pbb_etree_enable(pbb_etree_enable=pbb_etree_enable)
            assert vn_fixture.set_unknown_unicast_forwarding(True)
            assert vn_fixture.set_mac_learning_enabled(mac_learning_enabled)
            assert vn_fixture.set_mac_limit_control(mac_limit_obj)
            assert vn_fixture.set_mac_move_control(mac_move_limit_obj)
            assert vn_fixture.set_mac_aging_time(mac_aging_time)

        # BD to VMI mapping
        vlan_tag = 0
        for bd, vmi_list in bd_vmi_mapping.iteritems():
            bd_fixture = bd_fixtures[bd]
            for vmi in vmi_list:
                vmi_fixture = vmi_fixtures[vmi]
                assert bd_fixture.add_bd_to_vmi(vmi_fixture.uuid, vlan_tag,
                    verify=verify)

        ret_dict = {
            'bd_fixtures':bd_fixtures,
            'vmi_fixtures':vmi_fixtures,
            'vn_fixtures':vn_fixtures,
            'vm_fixtures':vm_fixtures,
            'pbb_compute_node_ips':pbb_compute_node_ips,
        }
        return ret_dict

    def send_l2_traffic(self,
                        src_vm_fixture,
                        **kwargs):
        '''
            Sends L2 traffic from VM src_vm_fixture:
                mandatory args:
                    src_vm_fixture: send l2 traffic from this VM
                optional args:
                     1. interface: use this interface to send traffic
                     2. src_mac: use src_mac as source mac
                     3. dst_mac: use dst_mac as dest mac
                     4. vlan: send vlan tagged packets
                     5. count: No. of packets
                     6. ether_type: ether type
                     7. payload: upper layer packets
                     8. dst_vm_fixture: verify sent packet on dst_vm with tcpdump
        '''

        interface = kwargs.get('interface', None)
        src_mac = kwargs.get('src_mac', "00:11:22:33:44:55")
        dst_mac = kwargs.get('dst_mac', "ff:ff:ff:ff:ff:ff")
        vlan = kwargs.get('vlan', None)
        count = kwargs.get('count', 1)
        ether_type = kwargs.get('ether_type', 0x0000)
        payload = kwargs.get('payload', "'*****This is default payload*****'")
        dst_vm_fixture = kwargs.get('dst_vm_fixture', None)

        ether = {'src':src_mac, 'dst':dst_mac, 'type':ether_type}
        dot1p = 0
        dot1q = {}
        if vlan:
            dot1q = {'prio':dot1p, 'vlan':vlan}

        if dst_vm_fixture:
            #Start the tcpdump on dst VM
            filters = '\'(ether src %s and ether dst %s)\'' % (src_mac, dst_mac)
            session, pcap = start_tcpdump_for_vm_intf(
                self, dst_vm_fixture, dst_vm_fixture.vn_fq_name, filters=filters)

        scapy_obj = self._generate_scapy_traffic(src_vm_fixture,
                                                interface=interface,
                                                count=count,
                                                ether=ether,
                                                dot1q=dot1q,
                                                payload=payload)

        if dst_vm_fixture:
            # verify packet count and stop tcpdump
            assert verify_tcpdump_count(self, session, pcap, exp_count=count)

    def _generate_scapy_traffic(self, src_vm_fixture,
                                interface=None,
                                count=1,
                                **kwargs):
        params = {}
        params['ether'] = kwargs.get('ether',{})
        params['dot1q'] = kwargs.get('dot1q',{})
        params['payload'] = kwargs.get('payload','')

        scapy_obj = ScapyTraffic(src_vm_fixture,
                               count = count,
                               interface=interface,
                               **params)
        scapy_obj.start()
        return scapy_obj

    def verify_mac_learning(self, vmi_fixture, bd_fixture,
                            pbb_compute_node_ips, cmac=None,
                            expectation=True):
        '''
        Verify if c-mac learned in agents:
            1. in local agent, nh type should be interface
            2. in remote agents, nh type should be PBB tunnel
        '''
        cmac = cmac or vmi_fixture.mac_address
        bd_uuid = bd_fixture.bd_uuid
        isid = bd_fixture.isid
        vmi_host_ip = self.inputs.get_host_ip(self.vnc_h.get_vmi_host_name(vmi_fixture.uuid))
        #Get I-component vrf
        vrf = self.get_i_component_vrf(vmi_fixture, bd_uuid)
        mpls_label = self.get_vrf_mpls_label(vrf)
        result = True

        for ip in pbb_compute_node_ips:
            if ip == vmi_host_ip:
                nh_type = 'interface' #Local cmac
            else:
                nh_type = 'PBB Tunnel'# Remote cmac

            #Get I-component vrf id
            vrf = self.get_i_component_vrf(vmi_fixture, bd_uuid, compute_ip=ip)
            vrf_id = self.get_vrf_id(vrf)

            l2_route_in_agent = self.get_vna_layer2_route(ip, vrf_id, mac=cmac,
                expectation=expectation)
            if not expectation:
                result = True if l2_route_in_agent else False
                if result:
                    continue
                else:
                    return result
            if not l2_route_in_agent:
                self.logger.error("C-MAC %s is NOT learned in agent %s" % (
                    cmac, ip))
                result = False
            else:
                l2_route_in_agent = l2_route_in_agent[1]
                result = self.validate_pbb_l2_route(l2_route_in_agent, cmac,
                    vmi_fixture.mac_address, nh_type, mpls_label, isid)

            if not result:
                self.logger.error("Mac learning verification for C-MAC %s in "
                    "agent %s FAILED" % (cmac, ip))
                return result
            self.logger.info("Mac learning verification for C-MAC %s in "
                "agent %s PASSED" % (cmac, ip))

        return result

    def get_i_component_vrf(self, vmi_fixture, bd_uuid, compute_ip=None):
        '''
            Get the I-component vrf on a specific compute for the VMI
        '''
        vn_fq_name = vmi_fixture.vn_obj.get_fq_name_str()
        (domain, project, vn) = vn_fq_name.split(':')
        i_comp_vrf_name = vn_fq_name + ":" + vn + \
            ":" + str(bd_uuid)

        compute_ip = compute_ip or \
            self.inputs.get_host_ip(self.vnc_h.get_vmi_host_name(vmi_fixture.uuid))
        agent_vrf_objs_vn = self.agent_inspect[compute_ip
            ].get_vna_vrf_objs(domain, project, vn)

        for vrf in agent_vrf_objs_vn['vrf_list']:
            if vrf['name'] == i_comp_vrf_name:
                return vrf

    def get_vrf_id(self, agent_vrf_obj_vn):
        return agent_vrf_obj_vn['l2index']

    def get_vrf_mpls_label(self, agent_vrf_obj_vn):
        return agent_vrf_obj_vn['table_label']

    @retry(delay=2, tries=7)
    def get_vna_layer2_route(self, compute_ip, vrf_id, mac=None,
            expectation=True):
        '''
        Get L2 routes from the agent with retry
        '''
        l2_route_in_agent = self.agent_inspect[compute_ip].get_vna_layer2_route(
            vrf_id=vrf_id, mac=mac)
        if expectation:
            if not l2_route_in_agent:
                self.logger.warn("L2 routes in agent %s not found for vrf id %s" % (
                    compute_ip, vrf_id))
                return False
            else:
                self.logger.debug("L2 routes found in agent is: %s" % (
                    l2_route_in_agent))
                return (True, l2_route_in_agent['routes'])
        else:
            if l2_route_in_agent:
                self.logger.warn("L2 routes found in agent is: %s" % (
                    l2_route_in_agent))
                return False
            else:
                self.logger.debug("L2 routes in agent %s not found for vrf id %s" % (
                    compute_ip, vrf_id))
                return (True, None)

    def validate_pbb_l2_route(self, l2_route_in_agent, cmac, bmac, nh_type,
            mpls_label=None, isid=0):

        result = True
        #No. of routes for cmac should be only one
        if len(l2_route_in_agent) != 1:
            self.logger.warn("No. of L2 route for C-MAC %s is not one, routes "
                "from agent is: %s" % (cmac, l2_route_in_agent))
            result = False
        else:
            route = l2_route_in_agent[0]

        if (EUI(route['mac']) != EUI(cmac)):
            self.logger.warn("C-MAC in agent is not as expected: %s "
                "got: %s" % (cmac, route['mac']))
            result = False

        if (len(route['path_list']) != 1):
            result = False

        if route['path_list'][0] ['nh']['type'] != nh_type:
            result = False
            self.logger.warn("nh type in agent is not as expected: %s "
                "got: %s" % (nh_type, route['path_list'][0] ['nh']['type']))

            #No need to proceed further verifications if nh type itself does not match
            return result
        if (nh_type == 'PBB Tunnel') and (EUI(route['path_list'][0]['nh'][
                'pbb_bmac']) != EUI(bmac)):
            result = False
            self.logger.warn("B-MAC in agent is not as expected: %s "
                "got: %s" % (bmac, route['path_list'][0] ['nh']['pbb_bmac']))
        elif (nh_type == 'interface') and (EUI(route['path_list'][0]['nh'][
                'mac']) != EUI(bmac)):
            result = False
            self.logger.warn("B-MAC in agent is not as expected: %s "
                "got: %s" % (bmac, route['path_list'][0] ['nh']['mac']))

        if (nh_type == 'PBB Tunnel') and (route['path_list'][0] ['nh'][
            'mc_list'][0]['label'] != mpls_label):
            result = False
            self.logger.warn("MPLS label in agent is not as expected: %s "
                "got: %s" % (mpls_label,
                route['path_list'][0] ['nh']['mc_list'][0]['label']))

        if (nh_type == 'PBB Tunnel') and (int(route['path_list'][0]['nh'][
            'isid']) != isid):
            result = False
            self.logger.warn("ISID value in agent is not as expected: %s "
                "got: %s" % (isid,
                route['path_list'][0] ['nh']['isid']))
        elif (nh_type == 'interface') and (int(route['path_list'][0]['nh'][
            'isid']) != 0):
            result = False
            self.logger.warn("ISID value in agent is not as expected: 0 "
                "got: %s" % (route['path_list'][0] ['nh']['isid']))

        self.logger.debug("Validation in agent for PBB L2 routes passed")
        return result

    @classmethod
    def tearDownClass(cls):
        super(PbbEvpnTestBase, cls).tearDownClass()
    # end tearDownClass
