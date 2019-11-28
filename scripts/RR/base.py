import test_v1
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture
import os
import copy
from tcutils.util import retry

class BaseRRTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseRRTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.orch = cls.connections.orch 
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseRRTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
   #end remove_from_cleanups

    def create_vn(self, vn_name, vn_subnets, option = 'orch'):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name=vn_name,
                          subnets=vn_subnets,
                          option = option))
    
    def create_vm(self, vn_fixture, vm_name, node_name=None,
                    flavor='contrail_flavor_small',
                    image_name='ubuntu',
                    *args, **kwargs):
        image_name = self.inputs.get_ci_image() or image_name
        return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    vm_name=vm_name,
                    image_name=image_name,
                    flavor=flavor,
                    node_name=node_name,
                    *args, **kwargs))

@retry(delay=5, tries=12)
def verify_peer_in_control_nodes(cn_inspect,ip,peers,skip_peers,logger):
        """
        Check the configured control node has any peer and if so the state is Established.
        """
        result = True
        expected_peers = peers
        cn_bgp_entry = cn_inspect[
            ip].get_cn_bgp_neigh_entry(encoding='BGP')
        if not cn_bgp_entry:
            result = False
            logger.error(
                'Control Node %s does not have any BGP Peer' %
                (self.router_ip))
        else:
            configured_peers = []
            for entry in cn_bgp_entry:
                if entry['peer'] in skip_peers:
                   continue
                if entry['state'] != 'Established' and entry['router_type'] != 'bgpaas-client':
                    result = result and False
                    logger.error('ctrl node %s With Peer %s peering is not Established. Current State %s ' % (ip,
                        entry['peer'], entry['state']))
                    return False
                else:
                    configured_peers.append(entry['peer'])
                    logger.debug(
                        'With Peer %s peering is Current State is %s ' %
                        (entry['peer'], entry['state']))
        if expected_peers.sort() == configured_peers.sort():
             logger.debug("BGP connections are proper")
        else:
             logger.debug("BGP connections are not proper")
             result = False
        return result

def get_connection_matrix(inputs,rr):

    #Calculating connection matrix
    ctrl_node_name = rr
    ctrl_node_host_ip = inputs.host_data[ctrl_node_name]['host_ip']
    ctrl_node_ip = inputs.host_data[ctrl_node_name]['control-ip']
    connection_dicts = {}
    bgp_nodes = inputs.bgp_names
    non_RR_nodes = copy.deepcopy(bgp_nodes)
    non_RR_nodes.remove(ctrl_node_name)
    non_RR_nodes_ctrl_ip = [inputs.host_data[node_name]['control-ip'] for node_name in non_RR_nodes]
    connection_dicts[ctrl_node_host_ip] = non_RR_nodes_ctrl_ip
    for entry in non_RR_nodes:
        connection_dicts[inputs.host_data[entry]['host_ip']] = [ctrl_node_ip]
    return connection_dicts
