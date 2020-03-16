from common.vrouter.base import BaseVrouterTest
from builtins import str
from tcutils.wrappers import preposttest_wrapper
import test
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from tcutils.util import get_random_name
import random

AF_TEST = 'v6'

class FatFlowSerial(BaseVrouterTest, VerifySvcChain):

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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
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

    @test.attr(type=['dev_reg'])
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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)

        self.remove_fat_flow_on_vmis(server_vmi_id, fat_flow_config)
        self.delete_all_flows_on_vms_compute(server_fixtures + client_fixtures)
        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port, fat_flow_count=0)


    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_with_service_chain(self):
        """
        Description: Verify Fat flow with service chain
        Steps:
            1. launch 2 VN and launch 2 client VMs on same node and server VM from other VN on different node.
            2. on server VM, config Fat flow for tcp port dport 10000.
            3. add flow aging for tcp port dport, flow_timeout 100 sec.
            4. create service instance, create policy and attach to both the VNs
            5. from both client VM, send TCP traffic to server on port dport twice with diff. src ports
        Pass criteria:
            1. on server compute, Fat flows should be created
            2. Fat flow should be deleted after flow_timeout
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
        svc_mode = 'in-network'

        svc_chain_info = self.config_svc_chain(
            left_vn_fixture=vn1_fixture,
            right_vn_fixture=vn2_fixture,
            mgmt_vn_fixture=vn_mgmt,
            service_mode=svc_mode,
            left_vm_fixture=client_fixtures[0],
            right_vm_fixture=server_fixtures[0],
            create_svms=True,
            hosts=[compute_hosts[0]])
        st_fixture = svc_chain_info['st_fixture']
        si_fixture = svc_chain_info['si_fixture']

        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        proto = 'tcp'
        dport = 10000
        baseport = random.randint(12000, 65000)
        sport = [str(baseport), str(baseport+1)]

        #Configure Fat flow on server VM
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
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

    @preposttest_wrapper
    def test_fat_flow_port_zero_intra_node(self):
        """
        Description: Verify Fat flow with port 0 for inter node traffic
            sub-cases:
                a. Fat config on server VMI
                b. Fat config on client VMI
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch 2 client VMs and 1 server VM and config Fat flow
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='intra-node', no_of_client=2,
            no_of_server=1)

        #Configure Fat flow on server VM
        proto = 'udp'
        dport_list = [53, 54]
        server_vmi_id = list(self.server_fixtures[0].get_vmi_ids().values())
        fat_flow_config = {'proto':proto,'port':0}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Set udp aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)

        afs = ['v4', 'v6'] if 'dual' in self.inputs.get_af() else [self.inputs.get_af()]
        for af in afs:
            self.verify_fat_flow_with_traffic(self.client_fixtures,self.server_fixtures[0],
                proto, af=af, fat_flow_config=fat_flow_config,
                dport_list=dport_list)

        #Remove Fat flow from server VM
        self.remove_fat_flow_on_vmis(server_vmi_id, fat_flow_config)
        #Add Fat flow on client VMs
        client1_vmi_id = list(self.client_fixtures[0].get_vmi_ids().values())
        client2_vmi_id = list(self.client_fixtures[1].get_vmi_ids().values())
        self.add_fat_flow_to_vmis(client1_vmi_id+client2_vmi_id,
            fat_flow_config)

        #Clear all the flows before starting traffic
        self.delete_all_flows_on_vms_compute(
            self.server_fixtures + self.client_fixtures)
        #When Fat flow with port 0 is configured on client VMs
        sport_list = [10000, 10001]
        compute_fix = self.compute_fixtures_dict[self.client_fixtures[0].vm_node_ip]
        for af in afs:
            for client_vm in self.client_fixtures:
                for sport in sport_list:
                    for dport in dport_list:
                        assert self.send_nc_traffic(client_vm,
                            self.server_fixtures[0], sport,
                            dport, proto,
                            ip=self.server_fixtures[0].get_vm_ips(af=af)[0])

            for client_vm in self.client_fixtures:
                vrf_id_src = compute_fix.get_vrf_id(client_vm.vn_fq_names[0])
                self.verify_fat_flow_on_compute(compute_fix,
                    client_vm.get_vm_ips(af=af)[0],
                    self.server_fixtures[0].get_vm_ips(af=af)[0], 0, proto,
                    vrf_id_src, fat_flow_count=1)

    @preposttest_wrapper
    def test_fat_flow_ignore_addrs(self):
        """
        Description: Verify Fat flow with ignore address for inter node traffic
            sub-cases:
                a. ignore source and specific port
                b. ignore destination and specific port
                c. ignore source and port 0
                d. ignore destination and port 0
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on client/server VMs
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', no_of_client=2,
            no_of_server=2)
        proto = 'udp'
        dport_list = [53]
        sport_list = [10000]

        #Set udp aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)

        fat_config_on = ['server']
        for config in fat_config_on:
            vmi_ids = []
            if config == 'server':
                port = dport_list[0]
                for vm in self.server_fixtures:
                    vmi_ids.extend(list(vm.get_vmi_ids().values()))
            elif config == 'client':
                port = sport_list[0]
                for vm in self.client_fixtures:
                    vmi_ids.extend(list(vm.get_vmi_ids().values()))
            fat_config_list = [
                {'proto':proto,'port':port, 'ignore_address':'source'},
                {'proto':proto,'port':port, 'ignore_address':'destination'},
                {'proto':proto,'port':0, 'ignore_address':'source'},
                {'proto':proto,'port':0, 'ignore_address':'destination'},
                {'proto':proto,'port':0}
                ]

            for fat_config in fat_config_list:
                self.add_fat_flow_to_vmis(vmi_ids, fat_config)
                self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
                    self.server_fixtures, fat_config,
                    fat_config_on=config)
                self.remove_fat_flow_on_vmis(vmi_ids, fat_config)

    @preposttest_wrapper
    def test_fat_flow_ignore_addrs_icmp_error(self):
        """
        Description: Verify Fat flow with ignore address for icmp error for inter node traffic
            sub-cases:
                a. ignore source and specific port on server VMI
                b. ignore destination and specific port on server VMI
                c. ignore source and port 0 on server VMI
                d. ignore destination and port 0 on server VMI
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on server VMs
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', no_of_client=2,
            no_of_server=2)
        proto = 'udp'
        dport_list = [53]
        sport_list = [10000]

        #Set udp aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)

        fat_config_on = ['client', 'server']
        for config in fat_config_on:
            vmi_ids = []
            if config == 'server':
                port = dport_list[0]
                for vm in self.server_fixtures:
                    vmi_ids.extend(list(vm.get_vmi_ids().values()))
            elif config == 'client':
                port = sport_list[0]
                for vm in self.client_fixtures:
                    vmi_ids.extend(list(vm.get_vmi_ids().values()))
            fat_config_list = [
                {'proto':proto,'port':port, 'ignore_address':'source'},
                {'proto':proto,'port':port, 'ignore_address':'destination'},
                {'proto':proto,'port':0, 'ignore_address':'source'},
                {'proto':proto,'port':0, 'ignore_address':'destination'},
                {'proto':proto,'port':0}
                ]

            for fat_config in fat_config_list:
                self.add_fat_flow_to_vmis(vmi_ids, fat_config)
                self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
                    self.server_fixtures, fat_config, icmp_error=True,
                    fat_config_on=config)
                self.remove_fat_flow_on_vmis(vmi_ids, fat_config)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_ignore_addrs_icmp_error_intra_node(self):
        """
        Description: Verify Fat flow with ignore address for icmp error for intra node traffic
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on server VMs
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='intra-node', no_of_client=2,
            no_of_server=2)
        proto = 'udp'
        dport_list = [53]
        sport_list = [10000]

        #Set udp aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)

        fat_config_on = 'server'
        vmi_ids = []
        port = dport_list[0]
        for vm in self.server_fixtures:
            vmi_ids.extend(list(vm.get_vmi_ids().values()))
        fat_config_list = [
            {'proto':proto,'port':port, 'ignore_address':'destination'},
            {'proto':proto,'port':0, 'ignore_address':'destination'},
            {'proto':proto,'port':0}
            ]

        for fat_config in fat_config_list:
            self.add_fat_flow_to_vmis(vmi_ids, fat_config)
            self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
                self.server_fixtures, fat_config, icmp_error=True,
                fat_config_on=fat_config_on)
            self.remove_fat_flow_on_vmis(vmi_ids, fat_config)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_at_vn(self):
        """
        Description: Verify Fat flow at VN level
            sub-cases:
                a. ignore source and specific port
                b. ignore destination and specific port
                c. ignore source and port 0
                d. ignore destination and port 0
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on client/server VMs
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', no_of_client=2,
            no_of_server=2)
        proto = 'udp'
        dport_list = [10000]
        sport_list = [10000]

        #Set aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)

        fat_config_on = ['server']
        for config in fat_config_on:
            vns = []
            if config == 'server':
                port = dport_list[0]
                vns.append(self.vn2_fixture)
            elif config == 'client':
                port = sport_list[0]
                vns.append(self.vn1_fixture)
            fat_config_list = [
                {'proto':proto,'port':port, 'ignore_address':'source'},
                {'proto':proto,'port':port, 'ignore_address':'destination'},
                {'proto':proto,'port':0, 'ignore_address':'source'},
                {'proto':proto,'port':0, 'ignore_address':'destination'},
                {'proto':proto,'port':0}
                ]

            for fat_config in fat_config_list:
                self.add_fat_flow_to_vns(vns, fat_config)
                self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
                    self.server_fixtures, fat_config,
                    fat_config_on=config, sport=sport_list[0],
                    dport=dport_list[0])
                self.delete_fat_flow_from_vns(vns)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_at_vn_intra_vn(self):
        """
        Description: Verify Fat flow at VN level and intra-vn/node traffic
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on client/server VMs
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', no_of_client=4,
            no_of_server=1)
        proto = 'udp'
        dport_list = [53]
        sport_list = [10000]

        #Set udp aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)
        client_fixs = [self.client_fixtures[0], self.client_fixtures[1]]
        server_fixs = [self.client_fixtures[2], self.client_fixtures[3]]
        port = dport_list[0]
        vns = [self.vn1_fixture]
        fat_config_list = [
            {'proto':proto,'port':port, 'ignore_address':'destination'},
            {'proto':proto,'port':0, 'ignore_address':'destination'},
            {'proto':proto,'port':0}
            ]

        for fat_config in fat_config_list:
            self.add_fat_flow_to_vns(vns, fat_config)
            self.verify_fat_flow_with_ignore_addrs(client_fixs,
                server_fixs, fat_config,
                fat_config_on='all')
            self.delete_fat_flow_from_vns(vns)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_vn_vmi(self):
        """
        Description: configure Fat flow on both VN and VMI
        Steps:
            1. Create 2 VNs and connect using policy
            2. launch VMs and config Fat flow on VMI and VN both
            3. start traffic and verify Fat flow on required compute nodes
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', no_of_client=4,
            no_of_server=1)
        proto = 'udp'
        dport_list = [11000]
        sport_list = [10000]

        #Set aging timeout to 300 sec
        flow_timeout = 300
        self.add_proto_based_flow_aging_time(proto, 0, flow_timeout)
        port = dport_list[0]
        vns = [self.vn2_fixture]
        vmi_ids = []
        for vm in self.server_fixtures:
            vmi_ids.extend(list(vm.get_vmi_ids().values()))
        fat_config_vn = {
            'proto':proto,'port':0, 'ignore_address':'destination'
            }
        fat_config_vmi = {
            'proto':proto,'port':dport_list[0], 'ignore_address':'destination'
            }
        self.add_fat_flow_to_vns(vns, fat_config_vn)
        self.add_fat_flow_to_vmis(vmi_ids, fat_config_vmi)
        self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
            self.server_fixtures, fat_config_vmi,
            fat_config_on='server', sport=sport_list[0],
            dport=dport_list[0])

        self.verify_fat_flow_with_ignore_addrs(self.client_fixtures,
            self.server_fixtures, fat_config_vn,
            fat_config_on='server', sport=sport_list[0],
            dport=dport_list[0])

class FatFlowSerialIpv6(FatFlowSerial):
    @classmethod
    def setUpClass(cls):
        super(FatFlowSerialIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

