from vn_test import *
from vm_test import *
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
        vn_fixtures = self.create_vn(count=1)
        self.verify_vn(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

	compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")    
        client_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=2,
                                    node_name=compute_hosts[0])
        server_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[1])
        self.verify_vm(client_fixtures)
        self.verify_vm(server_fixtures)

	#Configure Fat flow on server VM
	proto = 'udp'
	port = 53
	server_vmi_id = server_fixtures[0].get_vmi_ids().values()
	fat_flow_config = {'proto':proto,'port':port}
	self.config_fat_flow_on_vmi(server_vmi_id, fat_flow_config)

	self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)
        return True

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
        vn_fixtures = self.create_vn(count=1)
        self.verify_vn(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        compute_hosts = self.orch.get_hosts()
        client_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=2,
                                    node_name=compute_hosts[0])
        server_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=1,
                                    node_name=compute_hosts[0])
        self.verify_vm(client_fixtures)
        self.verify_vm(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.config_fat_flow_on_vmi(server_vmi_id, fat_flow_config)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)
        return True

    @preposttest_wrapper
    def test_fat_flow_inter_vn_inter_node(self):
        """
        Description: Verify Fat flow for inter-VN inter-Node traffic and with protocol based flow aging set
        Steps:
            1. launch 2 VN and launch 2 client VMs on same node and server VM from other VN on different node. 
            2. on server VM, config Fat flow for udp port 53.
	    3. add flow aging for udp port 53 as 60 sec.
            4. from both client VM, send UDP traffic to server on port 53 twice with diff. src ports
        Pass criteria:
            1. on client VMs compute, 4 set of flows and on server compute, 2 set of flows should be created
            2. on server compute, flow's source port should be 0 for Fat flow
	    3. flow should be deleted after 60 sec 
        """
        vn_fixtures = self.create_vn(count=2, rt_number='10000')
        self.verify_vn(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        vn2_fixture = vn_fixtures[1]

        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")
        client_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=2,
						node_name=compute_hosts[0])
        server_fixtures = self.create_vm(vn_fixture= vn2_fixture,count=1,
						node_name=compute_hosts[1])
        self.verify_vm(client_fixtures)
        self.verify_vm(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.config_fat_flow_on_vmi(server_vmi_id, fat_flow_config)

        #Set udp aging timeout to 60 sec
        flow_timeout = 60
	self.set_proto_based_flow_aging_time(proto, port, flow_timeout)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
						proto, port)

        self.logger.info("Verifying if Fat flow gets "
                    "deleted after aging timeout")
        sleep(flow_timeout)
        self.verify_fat_flow_with_traffic(client_fixtures,
                                           server_fixtures[0],
                                           proto, port,
                                           traffic=False, expectation=False)

        return True
