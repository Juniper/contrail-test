from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
import test
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from tcutils.util import get_random_name
import random

AF_TEST = 'v6'

class FatFlowSerial(BaseVrouterTest, ConfigSvcChain, VerifySvcChain):

    @classmethod
    def setUpClass(cls):
        super(FatFlowSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(FatFlowSerial, cls).tearDownClass()

    @preposttest_wrapper
    def test_fat_flow_inter_vn_inter_node(self):
        """
        Description: Verify Fat flow for inter-VN inter-Node traffic and with protocol based flow aging set
        Steps:
            1. launch 2 VN and launch 2 client VMs on same node and server VM from other VN on different node.
            2. on server VM, config Fat flow for udp port 53.
            3. add flow aging for udp port 53 as 80 sec.
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

        #Set udp aging timeout to 80 sec
        flow_timeout = 80
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

        self.logger.info("Fat flow got deleted after aging timeout as expected")

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


    @preposttest_wrapper
    def test_fat_flow_with_service_chain(self):
        """
        Description: Verify Fat flow with service chain
        Steps:
            1. launch 2 VN and launch 2 client VMs on same node and server VM from other VN on different node.
            2. on server VM, config Fat flow for tcp port dport 10000.
            3. add flow aging for tcp port dport as 100 sec.
            4. create service instance, create policy and attach to both the VNs
            5. from both client VM, send TCP traffic to server on port dport twice with diff. src ports
        Pass criteria:
            1. on server compute, Fat flows should be created
            2. Fat flow should be deleted after 60 sec
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=3)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        vn2_fixture = vn_fixtures[1]
        vn_mgmt = vn_fixtures[2]

        image = 'ubuntu'
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[0], image_name=image)
        server_fixtures = self.create_vms(vn_fixture= vn2_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)

        st_name = get_random_name("in_net_svc_template_1")
        si_prefix = get_random_name("in_net_svc_instance") + "_"
        policy_name = get_random_name("policy_in_network")
        si_count = 1
        svc_mode = 'in-network'

        st_fixture, si_fixtures = self.config_st_si(
            st_name, si_prefix, si_count,
            mgmt_vn_fixture=vn_mgmt,
            left_vn_fixture=vn1_fixture,
            right_vn_fixture=vn2_fixture, svc_mode=svc_mode,
            svc_img_name='tiny_in_net',
            project=self.inputs.project_name, st_version=1)
        action_list = self.chain_si(
            si_count, si_prefix, self.inputs.project_name)
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1_fixture.vn_fq_name,
                'src_ports': [0, -1],
                'dest_network': vn2_fixture.vn_fq_name,
                'dst_ports': [0, -1],
                'simple_action': None,
                'action_list': {'apply_service': action_list}
            },
        ]
        policy_fixture = self.config_policy(policy_name, rules)
        vn1_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn1_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn2_fixture)

        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        proto = 'tcp'
        dport = 10000
        baseport = random.randint(12000, 65000)
        sport = [str(baseport), str(baseport+1)]

        #Configure Fat flow on server VM
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':dport}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Set udp aging timeout to 100 sec
        flow_timeout = 100
        self.add_proto_based_flow_aging_time(proto, dport, flow_timeout)

        #Start the tcp traffic
        for vm in client_fixtures:
            for port in sport:
                assert self.send_nc_traffic(vm, server_fixtures[0],
                    port, dport, proto)

        #FAT flow verification
        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, dport, fat_flow_count=1)

        self.logger.info("Verifying if Fat flow gets "
            "deleted after aging timeout, sleeping for %s seconds" % (
            flow_timeout))
        self.sleep(flow_timeout)

        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, dport, fat_flow_count=0)

        self.logger.info("Fat flow got deleted after aging timeout as expected")

class FatFlowSerialIpv6(FatFlowSerial):
    @classmethod
    def setUpClass(cls):
        super(FatFlowSerialIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

