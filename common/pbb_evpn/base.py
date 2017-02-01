import re
from vnc_api.vnc_api import *

from common.neutron.base import BaseNeutronTest
from compute_node_test import ComputeNodeFixture
from common.base import GenericTestBase
from common.vrouter.base import BaseVrouterTest

from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.hping_traffic import Hping3

from time import sleep
import random
from netaddr import *

class PbbEvpnTestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(PbbEvpnTestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def setup_pbb_evpn(self,pbb_evpn_config=None, bd=None, vn=None, vmi=None,
                       vm=None, bd_vn_mapping=None, bd_vmi_mapping=None):
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


                #BD to VN mapping parameters:
                bd_vn_mapping = {'bd1':'vn1'}

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

        # Global system configuration
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        vnc_lib_fixture.set_global_mac_limit_control(mac_limit_control=mac_limit_obj)
        vnc_lib_fixture.set_global_mac_move_control(mac_move_control=mac_move_limit_obj)
        vnc_lib_fixture.set_global_mac_aging_time(mac_aging_time=mac_aging_time)

        # Bridge domains creation
        bd_count = bd['count']
        bd_fixtures = {} # Hash to store BD fixtures
        for i in range(0,bd_count):
            bd_id = 'bd'+str(i+1)
            if bd_id in bd:
                bd_isid = bd[bd_id].get('isid',0)
            else:
                bd_isid=randint(1,2**24-1)
            parent_obj = self.connections.vnc_lib_fixture.get_project_obj()
            bd_fixture = self.vnc_h.create_bd(parent_obj=parent_obj,
                                              mac_learning_enabled=mac_learning_enabled,
                                              mac_limit_control=mac_limit_obj,
                                              mac_move_control=mac_move_limit_obj,
                                              mac_aging_time=mac_aging_time,
                                              isid=bd_isid)
            bd_fixtures[bd_id] = bd_fixture


        # VNs creation
        vn_count = vn['count']
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            if vn_id in vn:
                vn_subnet = vn[vn_id].get('subnet',None)
                asn = vn[vn_id].get('asn',None)
                target= vn[vn_id].get('target',None)
                vn_fixture = self.create_only_vn(vn_name=vn_id, vn_subnets=[vn_subnet],
                                                 router_asn=asn, rt_number=target)
            else:
                vn_fixture = self.create_only_vn()
            vn_fixtures[vn_id] = vn_fixture

        # VMIs creation
        vmi_count = vmi['count']
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
                    vmi_fixture = self.setup_only_vmi(vn_fixture.uuid,
                                                      parent_vmi=parent_vmi_fixture.vmi_obj,
                                                      vlan_id=vlan,
                                                      api_type='contrail',
                                                      mac_address=parent_vmi_fixture.mac_address)
                else:
                    vmi_fixture = self.setup_only_vmi(vn_fixture.uuid)
            vmi_fixtures[vmi_id] = vmi_fixture

        # VMs creation
        vm_count = vm['count']
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
            if userdata:
                userdata = './common/pbb_evpn/'+userdata

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
                node_name = self.inputs.compute_names[index]
                index = random.randint(0,compute_nodes_len-1)
            elif launch_mode == 'non-distribute':
                node_name = self.inputs.compute_names[index]
            elif launch_mode == 'default':
                node_name=None

            vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                        port_ids=vmi_fix_uuid_list,
                                        userdata=userdata,
                                        node_name=node_name)
            vm_fixtures[vm_id] = vm_fixture

        # PBB EVPN VN configuration
        for vn_fixture in vn_fixtures.values():
            vn_fixture.set_pbb_evpn_enable(pbb_evpn_enable=pbb_evpn_enable)
            vn_fixture.set_pbb_etree_enable(pbb_etree_enable=pbb_etree_enable)
            vn_fixture.set_unknown_unicast_forwarding(True)

        # BD to VN mapping
        for bd, vn in bd_vn_mapping.iteritems():
            bd_fixture = bd_fixtures[bd]
            vn_fixture = vn_fixtures[vn]
            vn_fixture.add_bridge_domain(bd_obj=bd_fixture)

        for vm_fixture in vm_fixtures.values():
            vm_fixture.wait_till_vm_is_up()

        # BD to VMI mapping
        vlan_tag = 0
        for bd, vmi_list in bd_vmi_mapping.iteritems():
            bd_fixture = bd_fixtures[bd]
            for vmi in vmi_list:
                vmi_fixture = vmi_fixtures[vmi]
                self.vnc_h.add_bd_to_vmi(bd_fixture.uuid, vmi_fixture.uuid, vlan_tag)

        # Disable Policy on all VMIs
        for vmi_fixture in vmi_fixtures.values():
            self.vnc_h.disable_policy_on_vmi(vmi_fixture.uuid, True)


        ret_dict = {
            'bd_fixtures':bd_fixtures,
            'vmi_fixtures':vmi_fixtures,
            'vn_fixtures':vn_fixtures,
            'vm_fixtures':vm_fixtures,
        }
        return ret_dict

    def delete_pbb_evpn(self, bd_fixtures=None, vn_fixtures=None,
                         vm_fixtures=None, vmi_fixtures=None, ):

        # Clean up BD
        for bd_fixture in bd_fixtures.values():
            self.vnc_h.delete_bd(uuid=bd_fixture.uuid)

        # Clean up VMI
        for vmi_fixture in vmi_fixtures.values():
            self.addCleanup(vmi_fixture.cleanUp)

        # Clean up VM
        for vm_fixture in vm_fixtures.values():
            self.addCleanup(vm_fixture.cleanUp)

        # Clean up VN
        for vn_fixture in vn_fixtures.values():
            self.addCleanup(vn_fixture.cleanUp)

    @classmethod
    def tearDownClass(cls):
        super(PbbEvpnTestBase, cls).tearDownClass()
    # end tearDownClass


