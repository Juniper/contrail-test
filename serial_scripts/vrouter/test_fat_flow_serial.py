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
        vn_fixtures = self.create_vns(count=2, rt_number='10000')
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        vn2_fixture = vn_fixtures[1]

        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
                                                node_name=compute_hosts[0])
        server_fixtures = self.create_vms(vn_fixture= vn2_fixture,count=1,
                                                node_name=compute_hosts[1])
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Set udp aging timeout to 60 sec
        flow_timeout = 60
        self.add_proto_based_flow_aging_time(proto, port, flow_timeout)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                                proto, port)

        self.logger.info("Verifying if Fat flow gets "
            "deleted after aging timeout, sleeping for %s seconds" % (
            flow_timeout))
        self.sleep(flow_timeout)
        self.verify_fat_flow_with_traffic(client_fixtures,
                                           server_fixtures[0],
                                           proto, port,
                                           traffic=False, expected_flow_count=0,
                                           fat_flow_count=0)

    @preposttest_wrapper
    def test_add_delete_fat_flow_config(self):
        """
        Description: Verify adding and deleting Fat flow config, and verify flow after config deletion
        Steps:
            1. launch 1 VN and launch 3 VMs in it.client VMs on same node and server VM on different node.
            2. on server VM, config Fat flow for udp port 53.
            3. from both client VM, send UDP traffic to server on port 53 twice with diff. src ports
            4. delete the Fat flow config and verify the flow again
        Pass criteria:
            1. when Fat config is added, Fat flow should be created
            2. when Fat config is deleted, Fat flow should be not be created
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

        self.remove_fat_flow_on_vmis(server_vmi_id, fat_flow_config)
        self.delete_all_flows_on_vms_compute(server_fixtures + client_fixtures)
        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port, fat_flow_count=0)

