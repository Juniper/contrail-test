from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds

class TestBGPaasZone(BaseBGPaaS):

#    @classmethod
#    def setUpClass(cls):
#        #cls.host_list = 
#        '''
#         create vms 
#        ''' 
#        pass
 
    @preposttest_wrapper
    def test_bgp_control_node_zone(self):
        self.logger.info('executing bgp_control_zone test')
        vms = []
        bgpaas_fixtures = []
        vn_subnets = [get_random_cidr()] 
        local_as = 65000
        vn_name = get_random_name("cnz_vn")
        vn = self.create_vn(vn_name,vn_subnets)
        for i in range(0,2):
            vms.append(self.create_vm(vn_fixture=vn, image_name='ubuntu-bird'))
        client_vm = self.create_vm(vn_fixture=vn, image_name='ubuntu-bird')
        self.check_vms_booted(vms + [client_vm])
        cnzs = self.create_control_node_zones("test-zone")
        vip = get_an_ip(vn_subnets[0],offset=20)
        bgpaas_fixtures = self.create_and_attach_bgpaas(cnzs,vn,vms,local_as,vip)
        time.sleep(20)
        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
        msg = 'ping from %s to %s failed'%(client_vm.name, vip)
        assert client_vm.ping_with_certainty(vip)
        # update control node zone with different bgp routers
        self.update_control_node_zones(cnzs)
        self.flap_bgpaas_peering(vms)
        time.sleep(20)
        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
        assert client_vm.ping_with_certainty(vip)
        # remove zone from bgpaas and add new zone 
        self.detach_zones_from_bgpaas(cnzs[0],bgpaas_fixtures[0])
        cnzs[0].remove_zone_from_bgp_routers()
        self.attach_zones_to_bgpaas([cnzs[1],cnzs[2]],bgpaas_fixtures[0])
        self.flap_bgpaas_peering(vms)
        time.sleep(20)
        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
        assert client_vm.ping_with_certainty(vip)
        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,[vms[0]],1) is not False
        # add different control node zone test-zone
        return

#    @preposttest_wrapper
#    def test_bgp_multiple_control_nodes_in_zone(self):
#        self.logger.info('executing bgp_control_zone test')
#        vms = []
#        bgpaas_fixtures = []
#        vn_subnets = [get_random_cidr()] 
#        local_as = 65000
#        vn_name = get_random_name("cnz_vn")
#        vn = self.create_vn(vn_name,vn_subnets)
#        for i in range(0,2):
#            vms.append(self.create_vm(vn_fixture=vn, image_name='ubuntu-bird'))
#        client_vm = self.create_vm(vn_fixture=vn, image_name='ubuntu-bird')
#        self.check_vms_booted(vms + [client_vm])
#        cnzs = self.create_control_node_zones("test-zone")
#        vip = get_an_ip(vn_subnets[0],offset=20)
#        bgpaas_fixtures = self.create_and_attach_bgpaas(cnzs,vn,vms,local_as,vip)
#        time.sleep(20)
#        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
#        msg = 'ping from %s to %s failed'%(client_vm.name, vip)
#        assert client_vm.ping_with_certainty(vip)
#        # update control node zone with different bgp routers
#        self.update_control_node_zones(cnzs)
#        self.flap_bgpaas_peering(vms)
#        time.sleep(20)
#        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
#        assert client_vm.ping_with_certainty(vip)
#        # remove zone from bgpaas and add new zone 
#        self.detach_zones_from_bgpaas(cnzs[0],bgpaas_fixtures[0])
#        cnzs[0].remove_zone_from_bgp_routers()
#        self.attach_zones_to_bgpaas([cnzs[1],cnzs[2]],bgpaas_fixtures[0])
#        self.flap_bgpaas_peering(vms)
#        time.sleep(20)
#        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,vms,1)
#        assert client_vm.ping_with_certainty(vip)
#        assert self.verify_bgpaas_in_control_nodes_and_agent(bgpaas_fixtures,[vms[0]],1) is not False
#        # add different control node zone test-zone
#        return




#    def is_test_applicable(self):
#        # check for atleast 2 compute nodes
#        if len(self.host_list) < 2 :
#            return (False ,"compute nodes are not sufficient")
#        # check for atleast 3 control nodes
#        if len(self.inputs.bgp_ips) <= 3 :
#            return (False, "control nodes are not sufficient")
#        # check for 1 mx 
#        return (True,None)



