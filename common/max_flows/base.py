from builtins import str
from builtins import range
import test_v1
import fixtures
from common import isolated_creds

import vnc_api_test
from vnc_api.vnc_api import *
import random
import socket
import time
from netaddr import *
from tcutils.util import retry, get_random_mac, get_random_name
from tcutils.tcpdump_utils import *
from fabric.api import run
from floating_ip import *
from contrailapi import ContrailVncApi
from common.base import GenericTestBase
from common.base import GenericTestBase
from common.vrouter.base import BaseVrouterTest
from common.servicechain.config import ConfigSvcChain
from fabric.context_managers import settings, hide
from tcutils.util import safe_run, safe_sudo
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from router_fixture import LogicalRouterFixture
import copy
import re
from common.neutron.base import BaseNeutronTest
from common.fabric_utils import FabricUtils
from lif_fixture import LogicalInterfaceFixture
from bms_fixture import BMSFixture
from vm_test import VMFixture
from compute_node_test import ComputeNodeFixture



class BaseMaxFlowsTest(BaseVrouterTest):

    @classmethod
    def setUpClass(cls, flow_timeout=80):
        super(BaseVrouterTest, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.orch = cls.connections.orch
        cls.compute_fixtures = []
        for name, ip in cls.connections.inputs.compute_info.items():
            cls.compute_fixtures.append(ComputeNodeFixture(cls.connections, ip))

        try:
            cls.set_flow_timeout(cls.compute_fixtures, flow_timeout)
        except:
            cls.cleanup_flow_timeout(cls.compute_fixtures)
            raise

    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_flow_timeout()
        super(BaseVrouterTest, cls).tearDownClass()

    #end tearDownClass 

    @classmethod
    def set_flow_timeout(cls, compute_fixtures, flow_timeout=80):
        for cmp_fix in compute_fixtures:
            cmp_fix.set_flow_aging_time(flow_timeout)
        return True
   
    @classmethod
    def cleanup_flow_timeout(cls, compute_fixtures=None):
        if compute_fixtures is None:
            compute_fixtures = cls.compute_fixtures
        for cmp_fix in compute_fixtures:
            cmp_fix.set_flow_aging_time(cmp_fix.default_values['DEFAULT']['flow_cache_timeout'])
        return True
   

    def update_encap_priority(self, encaps):
        self.addCleanup(self.set_encap_priority, encaps=self.get_encap_priority())
        return self.set_encap_priority(encaps)
    
    def setup_vns(self, vn=None):
        '''Setup VN
           Input vn format:
                vn = {'count':1,
                    'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True,},
                    }

                vn = {'count':1,
                       'vn1':{
                            'address_allocation_mode':'flat-subnet-only',
                            'ip_fabric':True,
                            'ipam_fq_name': 'default-domain:default-project:ipam0'
                          },
                    }
        '''
        vn_count = vn['count'] if vn else 0
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            address_allocation_mode = vn[vn_id].get(
                'address_allocation_mode', 'user-defined-subnet-only')
            if address_allocation_mode == "flat-subnet-only":
                ipam_fq_name = vn[vn_id].get('ipam_fq_name', None)
                vn_fixture = self.create_vn(
                    vn_name=vn_id,
                    address_allocation_mode = address_allocation_mode,
                    forwarding_mode ="l3",
                   ipam_fq_name = ipam_fq_name, option='contrail')

            else:
                vn_subnet = vn[vn_id].get('subnet',None)
                vn_fixture = self.create_vn(vn_name=vn_id,
                                            vn_subnets=[vn_subnet])

            ip_fabric = vn[vn_id].get('ip_fabric',False)
            if ip_fabric:
                ip_fab_vn_obj = self.get_ip_fab_vn()
                assert vn_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)

            vn_fixtures[vn_id] = vn_fixture

        return vn_fixtures

    def setup_vmis(self, vn_fixtures, vmi=None):
        '''Setup VMIs
        Input vmi format:
            vmi = {'count':2,
                   'vmi1':{'vn': 'vn1'},
                   'vmi2':{'vn': 'vn1'},
                  }
        '''
        if vmi is None:
            vmi = {}
        vmi_count = vmi.pop('count', 0)
        vmi_fixtures = {} # Hash to store VMI fixtures
        vmi_keys = [each_key for each_key in vmi if re.match(r'vmi\d+',each_key)]
        for each_vmi in vmi_keys:
            vmi_id = each_vmi
            vmi_vn = vmi[vmi_id]['vn']
            vn_fixture = vn_fixtures[vmi_vn]
            vmi_fixture = self.setup_vmi(vn_fixture.uuid)
            if vmi[vmi_id].get('vip'):
                vIP = vmi[vmi_id]['vip']
                mode = vmi[vmi_id].get('mode', 'active-standby')
                self.config_aap(vmi_fixture, vIP, mac=vmi_fixture.mac_address,
                                aap_mode='active-active', contrail_api=True)

            vmi_fixtures[vmi_id] = vmi_fixture

        return vmi_fixtures

    def setup_vms(self, vn_fixtures, vmi_fixtures, vm=None, **kwargs):
        '''Setup VMs
        Input vm format:
            vm = {'count':2, 'launch_mode':'distribute',
                  'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                    'vlan': str(vmi['vmi3']['vlan'])} },
                  'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                    'vlan': str(vmi['vmi4']['vlan'])} }
                }
            launch_mode can be distribute or non-distribute
        '''
        if vm is None:
            vm = {}
        vm_count = vm.pop('count',0)
        image_name = kwargs.get('image_name','cirros')
        launch_mode = vm.get('launch_mode','default')
        vm_fixtures = {} # Hash to store VM fixtures

        compute_nodes = self.orch.get_hosts()
        compute_nodes_len = len(compute_nodes)
        index = random.randint(0,compute_nodes_len-1)
        vm_index = 0        
        vm_keys = [each_key for each_key in vm if re.match(r'vm\d+',each_key)]
        for each_vm in vm_keys:
            vm_id = each_vm
            vn_list = vm[vm_id]['vn']
            vmi_list = vm[vm_id]['vmi']

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
            if self.inputs.orchestrator == 'vcenter':
                index = vm_index%compute_nodes_len
                node_name = compute_nodes[index]
                vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                        port_ids=vmi_fix_uuid_list,
                                        node_name=node_name, image_name='ubuntu', 
                                        flavor='contrail_flavor_small')
            else:
                vm_node_name = vm[vm_id].get('node', None)
                if vm_node_name is not None:
                    node_name = vm_node_name
                elif launch_mode == 'distribute':
                    index = vm_index%compute_nodes_len
                    node_name = self.inputs.compute_names[index]
                elif launch_mode == 'non-distribute':
                    node_name = self.inputs.compute_names[index]
                elif launch_mode == 'default':
                    node_name=None

                vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                            port_ids=vmi_fix_uuid_list,
                                            node_name=node_name, image_name=image_name)
            vm_fixtures[vm_id] = vm_fixture
            vm_index = vm_index + 1 


        for vm_fixture in list(vm_fixtures.values()):
            assert vm_fixture.wait_till_vm_is_up()

        return vm_fixtures


    def cleanup_test_max_vm_flows_vrouter_config(self, compute_fixtures):
        for cmp_fix in compute_fixtures:
            cmp_fix.set_per_vm_flow_limit(100)
        return True


    def cleanup_flow_timeout_vrouter_config(self, compute_fixtures):
        for cmp_fix in compute_fixtures:
            cmp_fix.set_flow_aging_time(cmp_fix.default_values['DEFAULT']['flow_cache_timeout'])
        return True


