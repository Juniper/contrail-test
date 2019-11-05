from builtins import str
import test_v1, time
from vn_test import VNFixture
from vm_test import VMFixture
from control_node import CNFixture
from contrailapi import ContrailVncApi
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from common.base import GenericTestBase
from common.policy.config import ConfigPolicy, AttachPolicyFixture
from common.neutron.base import BaseNeutronTest
from vnc_api.vnc_api import *
from tcutils.traffic_utils.iperf3_traffic import Iperf3
from collections import OrderedDict
from compute_node_test import ComputeNodeFixture
from common.pbb_evpn.base import PbbEvpnTestBase
from common.device_connection import NetconfConnection

class BaseInterAS(PbbEvpnTestBase, BaseNeutronTest):
    ENCAP = 'gre'

    @classmethod
    def setUpClass(cls):
        super(BaseInterAS, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h= cls.connections.quantum_h
        cls.orch = cls.connections.orch
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.vnc_h = ContrailVncApi(cls.vnc_lib, cls.logger)
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseInterAS, cls).tearDownClass()
    # end tearDownClass

    def configure_labeled_unicast(self):
        '''
           Routine to configure inet-labeled unicast on all the control node
        '''
        for ctrl_node in self.inputs.bgp_ips:
            self.vnc_h.update_bgp_router_af(self.inputs.host_data[ctrl_node]['fqname'], 'inet-labeled')
        
    def configure_local_asbr(self):
        self.local_asbr = []
        for (router, ip) in self.inputs.inputs.local_asbr_info:
            bgp_router_obj = self.vnc_h.provision_bgp_router \
                             (router, ip, self.inputs.router_asn, ['inet-labeled'])
            params = bgp_router_obj.get_bgp_router_parameters()
            address_families = params.get_address_families()
            if 'inet-labeled' not in address_families.family:
                self.vnc_h.update_bgp_router_af(router, 'inet-labeled')
            self.local_asbr.append(bgp_router_obj)

    def configure_remote_asbr(self):
        self.remote_asbr = []
        for router in self.inputs.remote_asbr_info:
            bgp_router_obj = self.vnc_h.provision_bgp_router \
                             (router, self.inputs.remote_asbr_info[router]['ip'], \
                             self.inputs.remote_asbr_info[router]['asn'], ['inet-vpn'])
            params = bgp_router_obj.get_bgp_router_parameters()
            address_families = params.get_address_families()
            if 'inet-vpn' not in address_families.family:
               self.vnc_h.update_bgp_router_af(router, 'inet-vpn')
            self.associate_peers_for_remote_asbr(bgp_router_obj)
            self.remote_asbr.append(bgp_router_obj)

    def associate_peers_for_remote_asbr(self, remote_asbr_obj):
        #bgp_addr_fams = AddressFamilies(['inet-vpn'])
        #bgp_sess_attrs = [
            #BgpSessionAttributes(address_families=bgp_addr_fams)]
        #bgp_sessions = [BgpSession(attributes=bgp_sess_attrs)]
        bgp_family_attr = BgpFamilyAttributes()
        bgp_family_attr.set_address_family(u'inet-vpn')
        bgp_family_attr.set_default_tunnel_encap([u'mpls'])
        
        bgp_session_param = BgpSessionAttributes()
        bgp_session_param.set_family_attributes([bgp_family_attr])

        bgp_session = BgpSession()
        bgp_session.set_attributes([bgp_session_param])
        bgp_peering_attrs = BgpPeeringAttributes(session=[bgp_session])
        for ctrl_node in self.inputs.bgp_ips:
            fq_name=['default-domain', 'default-project',
                'ip-fabric', '__default__',
                self.inputs.host_data[ctrl_node]['fqname']]
            ctrl_node_obj = self.vnc_lib.bgp_router_read(fq_name=fq_name)
            remote_asbr_obj.add_bgp_router(ctrl_node_obj, bgp_peering_attrs)
            self.vnc_lib.bgp_router_update(remote_asbr_obj)
  

    def control_node_fix(self, bgp_router):
        router_name = bgp_router.name
        router_ip = bgp_router.bgp_router_parameters.address
        cntrl_fix = self.useFixture(CNFixture(
                               connections=self.connections,
                               router_name=router_name,
                               router_ip=router_ip,
                               router_type='router',
                               inputs=self.inputs))
        return cntrl_fix

    def verify_asbr_connection(self, local=True):
        result = True
        asbrs_obj = self.local_asbr if local else self.remote_asbr
        for asbr in asbrs_obj:
            cn_fix = self.control_node_fix(asbr)
            if not cn_fix.verify_peer_in_control_nodes():
                self.logger.debug("Neighbor verification failed for %s",\
                    asbr.name)
                result = result and False
        return result

    @retry(delay=5, tries=5)
    def verify_inet3_routing_instance(self):
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table(rt_name='inet.3')
            for compute in self.inputs.compute_ips:
                compute = self.inputs.host_data[compute]['host_data_ip']
                rt_found = False
                for route in routes['routes']:
                    if compute in route['prefix']:
                        self.logger.info ("vhost ip , %s, is seen in\
                           inet.3 table" % compute)
                        rt_found = True
                        break
                if not rt_found:
                    return rt_found
        return True

    @retry(delay=5, tries=5)
    def verify_l3vpn_routing_instance(self):
        for router in self.inputs.remote_asbr_info:
            params = self.inputs.remote_asbr_info[router]
            rt_found = False
            for ctrl_node in self.inputs.bgp_ips:
                cn_inspect = self.connections.cn_inspect[ctrl_node]
                routes = \
                    cn_inspect.get_cn_route_table(rt_name='bgp.l3vpn.0')
                for route in routes['routes']:
                    if route['prefix'].split('/')[0] == \
                      params['ip']+':'+str(params['target'])+':'+params['CE'][0]:
                          self.logger.info("route, %s , found" \
                            %routes['routes'][0]['prefix'])
                          rt_found = True
                          break
            if not rt_found:
                return False
        return True

    def run_cmds_on_mx(self, mx_ip, cmds):
        mx_handle = NetconfConnection(host = mx_ip)
        mx_handle.connect()
        cli_output = mx_handle.config(stmts = cmds, timeout = 120)
        mx_handle.disconnect()
        assert (not('failed' in cli_output)), "Not able to push config to mx"

    def tunnel_config_on_local_asbr(self, mode='gre'):
        cmd = 'set groups testbed_l7_l3_h5 routing-options dynamic-tunnels testbed_l3 %s' %mode
        for (router, ip) in self.inputs.inputs.local_asbr_info:
            mx_ip = self.inputs.physical_routers_data[router]['mgmt_ip']
            self.run_cmds_on_mx(mx_ip, [cmd])

    def basic_end_to_end_ping(self, aap=False, verify_ssh=False, enable_fat_flow=False, forwarding_mode=None):
        self.config_encap_priority(self.ENCAP)
        self.tunnel_config_on_local_asbr(self.ENCAP)
        for router in self.inputs.remote_asbr_info:
            vn = {}
            vn['count']=1
            vn['vn1']={}
            vn['vn1']['subnet']=\
                self.inputs.remote_asbr_info[router]['subnet']
            vn['vn1']['asn']=\
                self.inputs.remote_asbr_info[router]['asn']
            vn['vn1']['target']=\
                self.inputs.remote_asbr_info[router]['target']

            vn_fixtures = self.setup_vns(vn)
    
            if forwarding_mode:
                self.set_vn_forwarding_mode(vn_fixtures['vn1'], forwarding_mode)

            vmi = {'count': 2,
               'vmi1': {'vn': 'vn1'},
               'vmi2': {'vn': 'vn1'}
              }

            vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)
            vm = {'count':2,
              'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{}},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{}}
            }
            vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm)

            import pdb;pdb.set_trace()
            if enable_fat_flow:
                fat_flow_config = {'proto': 'icmp', 'port':0}
                vmi_ids = [vmi.uuid for vmi in list(vmi_fixtures.values())]
                self.add_fat_flow_to_vmis(vmi_ids, fat_flow_config)

            if aap:
                vIP = get_an_ip(vn['vn1']['subnet'], offset=100)
                for vmi in list(vmi_fixtures.values()):
                    self.config_aap(vmi.uuid, vIP, \
                      mac=vmi.mac_address, aap_mode='active-active', contrail_api=True)
                for vm in list(vm_fixtures.values()):
                    output = vm.run_cmd_on_vm(
                        ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])
                result = False
                for vm in list(vm_fixtures.values()):
                    result = result or vm.ping_with_certainty\
                      (ip=self.inputs.remote_asbr_info[router]['CE'][0], other_opt="-I "+vIP)
                    if result:
                        self.logger.info("Ping from VM to remote ce with vIP, %s, as source passed" %vIP)
                        return True
                assert result, "Ping from both VM to remote ce with vIP, %s, as source failed" %vIP
            else:
              for vm_fix in vm_fixtures:
                assert  vm_fixtures[vm_fix].ping_with_certainty\
                  (ip=self.inputs.remote_asbr_info[router]['CE'][0])
                if verify_ssh:
                    assert self.verify_ssh(vm_fixtures[vm_fix], self.inputs.remote_asbr_info[router]['CE'][0])


    def set_vn_forwarding_mode(self, vn_fix, forwarding_mode="default"):
        self.logger.info("Set VN Forwarding mode to %s" %forwarding_mode)
        vn_fix = self.vnc_h.virtual_network_read(id=vn_fix.uuid)
        vni_obj_properties = vn_fix.get_virtual_network_properties(
            ) or VirtualNetworkType()
        vni_obj_properties.set_forwarding_mode(forwarding_mode)
        vn_fix.set_virtual_network_properties(vni_obj_properties)
        self.vnc_h.virtual_network_update(vn_fix)

    def verify_ssh(self, src_vm, dest_ip, user='root', password='c0ntrail123'):
        cmd = "sshpass -p " + password + " ssh -o StrictHostKeyChecking=no " + user + "@" + dest_ip + " ls"
        command_output = src_vm.run_cmd_on_vm(cmds=[cmd], timeout=10, as_sudo=True)
        return True if list(command_output.values()) else False

    def add_fat_flow_to_vmis(self, vmi_ids, fat_flow_config):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>,
            'ignore_address': <string, source/destination>}
        '''
        for vmi_id in vmi_ids:
            self.vnc_h.add_fat_flow_to_vmi(vmi_id, fat_flow_config)

        return True

    def remove_fat_flow_on_vmis(self, vmi_ids, fat_flow_config):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        for vmi_id in vmi_ids:
            vmi_obj = self.vnc_h.remove_fat_flow_on_vmi(vmi_id, fat_flow_config)

        return True
