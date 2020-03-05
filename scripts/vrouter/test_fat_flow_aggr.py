from common.vrouter.base import BaseVrouterTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import get_random_name, is_v6
import random
from common.neutron.lbaasv2.base import BaseLBaaSTest
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain

AF_TEST = 'v6'

class FatFlowAggr(BaseVrouterTest, BaseLBaaSTest):

    @classmethod
    def setUpClass(cls):
        super(FatFlowAggr, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(FatFlowAggr, cls).tearDownClass()

    #This is required just to override the method in BaseLBaaSTest, else tests
    #run only in openstack liberty and up
    def is_test_applicable(self):
        return (True, None)
    @test.attr(type=['sanity','dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_icmp_intra_vn_inter_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv4) for intra-vn inter-node
        Steps:
            1. Create 1 VN and launch 3 VMs.2 client VMs on same node and server VM on different node.
               Client 1 in subnet 1, Client 2 in the next subnet. 
            2. On server VM, config fat flow aggr prefix dest len 25 for ICMP port 0.
            3. From both the client VMs, send ICMP traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2) 
               of fat flows with prefix aggregated for the src IPs
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of flows and on server compute, 
               expect 2 pairs of flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net 

        """
        prefix_length = 27
        ipv6 = False
        only_v6 = False
        prefix_length6 = 123
        if self.inputs.get_af() == 'dual':
            ipv6 = True
            only_v6 = True

        inter_node = True
        inter_vn = False
        proto = 'icmp'
        if proto == 'icmp':
            port = 0
        policy_deny = False
        vn_policy = False
        self.fat_flow_with_prefix_aggr(prefix_length=prefix_length,
            inter_node=inter_node,inter_vn=inter_vn,
            proto=proto, port=port, policy_deny=policy_deny, vn_policy=vn_policy, 
            dual=ipv6, prefix_length6=prefix_length6, only_v6=only_v6)

        return True

    # end test_fat_flow_aggr_dest_len_icmp_intra_vn_inter_node

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_udp_inter_vn_inter_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv4) for intra-vn inter-node
        Steps:
            1. Create 2 VNs and launch 3 VMs.2 client VMs in VN1 on same node 
               and server VM in VN2 on different node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow udp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest len 29 for UDP port 55.
            3. From both the client VMs, send ICMP traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of fat flows with prefix aggregated for the src IPs
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of flows and on server compute,
               expect 2 pairs of flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net

        """
        prefix_length = 29
        ipv6 = False
        only_v6 = False
        if self.inputs.get_af() == 'dual':
            ipv6 = True
            only_v6 = True
        prefix_length6 = 125
        inter_node = True
        inter_vn = True
        proto = 'udp'
        port = 55
        policy_deny = False
        vn_policy = True
        self.fat_flow_with_prefix_aggr(prefix_length=prefix_length,
            inter_node=inter_node,inter_vn=inter_vn, proto=proto,
            port=port, vn_policy=vn_policy, policy_deny=policy_deny, 
            dual=ipv6, prefix_length6=prefix_length6, only_v6=only_v6)
        return True

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_ignore_src_udp_inter_vn_inter_node(self):
        """:
        Description: Verify fat flow prefix aggr dest for intra-vn inter-node
        Steps:
            1. Create 2 VNs and launch 3 VMs.2 client VMs in VN1 on same node
               and server VM in VN2 on different node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow udp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest len 29 
               with ignore src for UDP port 55.
            3. From both the client VMs, send udp traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of fat flows with prefix aggregated for the src IPs and with dest ip 0.0.0.0/0
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of flows and on server compute,
               expect 2 pairs of flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net
        """
        prefix_length = 28
        inter_node = True
        inter_vn = True
        ignore_address = 'src'
        proto = 'udp'
        port = 55
        policy_deny = False
        vn_policy = True
        ipv6 = False
        only_v6 = False
        if self.inputs.get_af() == 'dual':
            ipv6 = True
            only_v6 = True
        prefix_length6 = 124
        self.fat_flow_with_prefix_aggr(prefix_length=prefix_length,
            inter_node=inter_node,inter_vn=inter_vn, proto=proto,
            port=port, vn_policy=vn_policy, policy_deny=policy_deny, 
            ignore_address=ignore_address, dual=ipv6, 
            prefix_length6=prefix_length6, only_v6=only_v6)
        return True

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_ignore_src_icmp_inter_vn_intra_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv4) for intra-vn inter-node
        Steps:
            1. Create 2 VNs and launch 3 VMs.2 client VMs in VN1 on same node
               and server VM in VN2 on the same node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow icmp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest len 29
               with ignore src for icmp port 0.
            3. From both the client VMs, send icmp traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of fat flows with prefix aggregated for the src IPs and with dest ip 0.0.0.0/0
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On the CN, also expect 4 pairs of flows.
            3. On the compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net
        """
        prefix_length = 27
        inter_node = False
        inter_vn = True
        ignore_address = 'src'
        proto = 'icmp'
        port = 0
        policy_deny = False
        vn_policy = True
        ipv6 = False
        only_v6 = False
        if self.inputs.get_af() == 'dual':
            ipv6 = True
            only_v6 = True
        prefix_length6 = 125
        self.fat_flow_with_prefix_aggr(prefix_length=prefix_length,
            inter_node=inter_node,inter_vn=inter_vn, proto=proto,
            port=port, vn_policy=vn_policy, policy_deny=policy_deny, ignore_address=ignore_address, 
            dual=ipv6, prefix_length6=prefix_length6, only_v6=only_v6)
        return True

    @preposttest_wrapper
    def itest_fat_flow_aggr_scaling(self):
        """:
        Description: Verify fat flow prefix aggr dest for intra-vn inter-node
        Steps:
            1. Create 2 VNs and launch n clients VMs.1 server VM in VN2 on remote node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow icmp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest len 25
               with ignore src for icmp port 0.
            3. From all the client VMs, send icmp traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the server CN, expect  2 pairs( 1 for client 1, 1 for client 2)
               of fat flows with prefix aggregated for the src IPs and with dest ip 0.0.0.0/0
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On the CN, also expect n pairs of flows.
            3. On the compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net
        """
        prefix_length = 25
        inter_node = True
        inter_vn = True
        ignore_address = 'src'
        proto = 'icmp'
        port = 0
        policy_deny = False
        vn_policy = True
        self.fat_flow_with_prefix_aggr(prefix_length=prefix_length,
            inter_node=inter_node,inter_vn=inter_vn, proto=proto,
            port=port, vn_policy=vn_policy, policy_deny=policy_deny, 
            ignore_address=ignore_address, scale=4)
        return True


class FatFlowAggrIpv6(FatFlowAggr):
    @classmethod
    def setUpClass(cls):
        super(FatFlowAggr, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @preposttest_wrapper
    def test_fat_flow_lbaasv2(self):
        raise self.skipTest("Skipping Test. LBaas is NOT supported for IPv6")

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_icmp_intra_vn_inter_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv6) for intra-vn inter-node
        Steps:
            1. Create 1 VN with IPv6 subnet and launch 3 VMs.
               2 client VMs on same node and server VM on different node.
               Client 1 in subnet 1, Client 2 in the next subnet.
            2. On server VM, config fat flow aggr prefix dest IPv6 len 123 for ICMP port 0.
            3. From both the client VMs, send ICMP6 traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of IPv6 fat flows with prefix aggregated for the src IPs
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of IPv6 flows and on server compute,
               expect 2 pairs of IPv6 flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net

        """
        self.inputs.set_af('dual')
        super(FatFlowAggrIpv6, self).test_fat_flow_aggr_dest_icmp_intra_vn_inter_node()

    @test.attr(type=['sanity','dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_udp_inter_vn_inter_node(self):
        """ 
        Description: Verify fat flow prefix aggr dest (IPv6) for intra-vn inter-node
        Steps:
            1. Create 2 VNs with IPv6 subnets and launch 3 VMs.2 client VMs in VN1 on same node
               and server VM in VN2 on different node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow udp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest IPv6 len 125 for UDP port 55.
            3. From both the client VMs, send ICMP6 traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of IPv6 fat flows with prefix aggregated for the src IPs
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of IPv6 flows and on server compute,
               expect 2 pairs of IPv6 flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net

        """
        self.inputs.set_af('dual')
        super(FatFlowAggrIpv6, self).test_fat_flow_aggr_dest_udp_inter_vn_inter_node()

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_ignore_src_udp_inter_vn_inter_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv6) for intra-vn inter-node
        Steps:
            1. Create 2 VNs with IPv6 subnets and launch 3 VMs.2 client VMs in VN1 on same node
               and server VM in VN2 on different node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow udp traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest IPv6 len 100
               with ignore src for UDP port 55.
            3. From both the client VMs, send udp traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the remote CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of fat IPv6 flows with prefix aggregated for the src IPs and with dest IPv6 :::0
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On client VM compute nodes, expect 4 pairs of flows and on server compute,
               expect 2 pairs of flows
            3. On server compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net
        """
        self.inputs.set_af('dual')
        super(FatFlowAggrIpv6, self).test_fat_flow_aggr_dest_ignore_src_udp_inter_vn_inter_node()

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_aggr_dest_ignore_src_icmp_inter_vn_intra_node(self):
        """:
        Description: Verify fat flow prefix aggr dest (IPv6) for intra-vn inter-node
        Steps:
            1. Create 2 VNs with IPv6 subnets and launch 3 VMs.2 client VMs in VN1 on same node
               and server VM in VN2 on the same node.
               Client 1 in subnet 1, Client 2 in the next subnet.
               Policy p1 configured to allow icmp6 traffic between VN1 and VN2.
            2. On server VM, config fat flow aggr prefix dest IPv6 len 100
               with ignore src for icmp6 port 0.
            3. From both the client VMs, send icmp6 traffic to the server VM twice with diff. src ports
        Pass criteria:
            1. On the CN, expect 2 pairs ( 1 for client 1, 1 for client 2)
               of fat IPv6 flows with prefix aggregated for the src IPs and with dest ip :::0
               (VM to fabric, Prefix Aggr Dest: Aggregation happens for SRC IPs)
            2. On the CN, also expect 4 pairs of IPv6 flows.
            3. On the compute node, flow's source port should be 0 for fat flows

        Maintainer: Ankitja@juniper.net
        """
        self.inputs.set_af('dual')
        super(FatFlowAggrIpv6, self).test_fat_flow_aggr_dest_ignore_src_icmp_inter_vn_intra_node()


