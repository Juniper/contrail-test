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


class BaseInterAS(BaseNeutronTest, ConfigPolicy):

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
            self.remote_asbr.append(bgp_router_obj)

    def control_node_fix(self, bgp_router):
        router_name = bgp_router.name
        router_ip = bgp_router.bgp_router_parameters.address
        cntrl_fix = self.useFixture(CNFixture(
                               connections=self.connections,
                               router_name=router_name,
                               router_ip=router_ip,
                               router_type='mx',
                               inputs=self.inputs))
        return cntrl_fix

    def verify_asbr_connection(self, local=True):
        result = True
        asbrs_obj = self.local_asbr if local else self.remote_asbr
        for asbr in asbrs_obj:
            cn_fix = self.control_node_fix(asbr)
            if not cn_fix.verify_peer_in_control_nodes():
                self.logger.debug("Neighbor verification failed for %s", asbr.name)
                result = result and False
        return result

    def verify_inet3_routing_instance(self):
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table(rt_name='inet.3')
            for compute in self.inputs.compute_ips:
                compute = self.inputs.host_data[compute]['host_data_ip']
                rt_found = False
                for route in routes['routes']:
                    if compute in route['prefix']:
                        self.logger.info ("vhost ip , %s, is seen in inet.3 table" % compute)
                        rt_found = True
                        break
                if not rt_found:
                    return rt_found
        return True
