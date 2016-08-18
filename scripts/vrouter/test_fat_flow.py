from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
import test

class FatFlow(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(FatFlow, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(FatFlow, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_fat_flow_intra_vn_inter_node(self):
        """
        Description: Verify Fat flow for intra-VN inter-Node traffic
        Steps:
            1. launch 1 VN and launch 3 VMs in it.client VMs on same node and server VM on different node.
            2. on server VM, config Fat flow for udp port 53.
            3. from both client VM, send UDP traffic to server on port 53 twice with diff. src ports
        Pass criteria:
            1. on client VMs compute, 4 set of flows and on server compute, 2 set of flows should be created
            2. on server compute, flow's source port should be 0 for Fat flow
        """
        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
                                    node_name=compute_hosts[0])
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[1])
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)

    @preposttest_wrapper
    def test_fat_flow_intra_vn_intra_node(self):
        """
        Description: Verify Fat flow for intra-VN intra-Node traffic
        Steps:
            1. launch 1 VN and launch 3 VMs in it.All VMs on same node.
            2. on server VM, config Fat flow for udp port 53.
            3. from both client VM, send UDP traffic to server on port 53 twice with diff. src ports
        Pass criteria:
            1. total 4 set of flows should be created
            2. there should not be Fat flow with source port 0
        """
        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        compute_hosts = self.orch.get_hosts()
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
                                    node_name=compute_hosts[0])
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[0])
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)

    @preposttest_wrapper
    def test_fat_flow_icmp_error(self):
        """
        Description: Verify Fat flow when server port is not reachable, bug 1542207
        Steps:
            1. launch 1 VN and launch 2 VMs in it.All VMs on same node
            2. on server VM, config Fat flow for udp port 53, but no process on that port
            3. from client VM, send UDP traffic to server on port 53
            4. server will send icmp error for port 53 traffic
        Pass criteria:
            1. Fat and non-Fat flows should be created
            2. there should not be HOLD flows
        """
        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        compute_hosts = self.orch.get_hosts()
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[0])
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[0])
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        srcport = 10000
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Start the traffic
        (stats, hping_log) = self.send_hping3_traffic(
                                     client_fixtures[0],
                                     server_fixtures[0].vm_ip,
                                     srcport=srcport,
                                     destport=port,
                                     udp=True)

        #Verify the flows
        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, port, fat_flow_count=1,
                               unidirectional_traffic=False)

        compute_fix = self.compute_fixtures_dict[client_fixtures[0].vm_node_ip]
        vrf_id = compute_fix.get_vrf_id(client_fixtures[0].vn_fq_names[0])

        flow_data={'src_ip':client_fixtures[0].vm_ip,
                   'dst_ip':server_fixtures[0].vm_ip,
                   'src_port': srcport, 'dst_port':port,
                   'proto': 17, 'vrf':vrf_id}
        #Verify NO hold flows
        (flow_count, flow) = compute_fix.get_vrouter_matching_flow(flow_data, filters='Action:H')

        assert flow_count == 0, ('Flow with Action HOLD is seen which is NOT '
                                    'expected, test FAILED')
