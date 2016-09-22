from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
import test
from tcutils.util import get_random_name, is_v6
import random

af_test = 'v6'

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
            1. create 1 VN and launch 3 VMs in it.client VMs on same node and server VM on different node.
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
            1. create 1 VN and launch 3 VMs in it.All VMs on same node.
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
        image = 'ubuntu-traffic'
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        srcport = 10000
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Start the traffic without any receiver, dest VM will send icmp error
        nc_options = '-4' if (self.inputs.get_af() == 'v4') else '-6'
        nc_options = nc_options + ' -q 2 -u'
        client_fixtures[0].nc_send_file_to_ip('icmp_error', server_fixtures[0].vm_ip,
            local_port=srcport, remote_port=port,
            nc_options=nc_options)

        #Verify the flows
        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, port, fat_flow_count=1,
                               unidirectional_traffic=False)

        compute_fix = self.compute_fixtures_dict[client_fixtures[0].vm_node_ip]
        vrf_id = compute_fix.get_vrf_id(client_fixtures[0].vn_fq_names[0])

        #Verify NO hold flows
        action = 'HOLD'
        self.verify_flow_action(compute_fix, action,
            src_ip=client_fixtures[0].vm_ip, dst_ip=server_fixtures[0].vm_ip,
            sport=srcport, dport=port, src_vrf=vrf_id, proto=proto, exp=False)

    @preposttest_wrapper
    def test_fat_flow_icmp_error_inter_node(self):
        """
        Description: Verify Fat flow when server port is not reachable, bug 1542207
        Steps:
            1. launch 1 VN and launch 2 VMs in it.All VMs on different node
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
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")

        image = 'ubuntu-traffic'
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'udp'
        port = 53
        srcport = 10000
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        #Start the traffic without any receiver, dest VM will send icmp error
        nc_options = '-4' if (self.inputs.get_af() == 'v4') else '-6'
        nc_options = nc_options + ' -q 2 -u'
        client_fixtures[0].nc_send_file_to_ip('icmp_error', server_fixtures[0].vm_ip,
            local_port=srcport, remote_port=port,
            nc_options=nc_options)

        #Verify the flows
        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, port, fat_flow_count=1,
                               unidirectional_traffic=False)

        compute_fix = self.compute_fixtures_dict[client_fixtures[0].vm_node_ip]
        vrf_id = compute_fix.get_vrf_id(client_fixtures[0].vn_fq_names[0])

        #Verify NO hold flows
        action = 'HOLD'
        self.verify_flow_action(compute_fix, action,
            src_ip=client_fixtures[0].vm_ip, dst_ip=server_fixtures[0].vm_ip,
            sport=srcport, dport=port, src_vrf=vrf_id, proto=proto, exp=False)

    @preposttest_wrapper
    def test_fat_flow_no_tcp_eviction(self):
        """
        Description: Verify Fat flows are not evicted on connection closure
        Steps:
            1. launch 1 VN and launch 2 VMs in it.client VM and server VM on different node.
            2. on server VM, config Fat flow for tcp.
            3. from client VM,send tcp traffic to server
        Pass criteria:
            1. Fat flow should not be evicted after connection closure
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        image = 'ubuntu'
        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        server_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)
        self.verify_vms(client_fixtures)
        self.verify_vms(server_fixtures)

        #Configure Fat flow on server VM
        proto = 'tcp'
        port = 10000
        sport = 9000
        server_vmi_id = server_fixtures[0].get_vmi_ids().values()
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        assert self.send_nc_traffic(client_fixtures[0], server_fixtures[0],
            sport, port, proto)

        #FAT flow verification
        assert self.verify_fat_flow(client_fixtures, server_fixtures[0],
                               proto, port, fat_flow_count=1)

    @preposttest_wrapper
    def test_fat_flow_with_aap(self):
        """
        Description: Verify Fat flows with allowed address pair
        Steps:
            1. launch 1 VN and launch 4 VMs in it.2 client VMs and 2 server VMs on different node.
            2. on server VMs, config Fat flow for udp.
            3. from client VMs,send udp traffic to servers and
                verify mastership and Fat flow
            4. Induce mastership switch and verify the Fat flow again
        Pass criteria:
            1. Fat flow and mastership verification should pass
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,"
                                    "this test needs atleast 2 compute nodes")

        vn1_fixture = self.create_vns(count=1)[0]
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        result = False
        vIP = self.get_random_ip_from_vn(vn1_fixture)[0]
        image = 'ubuntu-traffic'

        port1_obj = self.create_port(net_id=vn1_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                     image_name=image,
                                     port_ids=[port1_obj['id']],
                                     node_name=compute_hosts[0])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name=image,
                                     port_ids=[port2_obj['id']],
                                     node_name=compute_hosts[0])

        client_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[1], image_name=image)
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        self.verify_vms(client_fixtures)

        proto = 'udp'
        dport = 53
        baseport = random.randint(12000, 65000)
        sport = [str(baseport), str(baseport+1)]
        fat_flow_config = {'proto':proto,'port':dport}
        self.add_fat_flow_to_vmis([port1_obj['id'], port2_obj['id']], fat_flow_config)

        self.config_aap(port1_obj, port2_obj, vIP)
        self.config_vrrp(vm1_fixture, vIP, '20')
        self.config_vrrp(vm2_fixture, vIP, '10')
        vrrp_master = vm1_fixture
        if is_v6(vIP):
            #current version of vrrpd does not support IPv6, as a workaround add the vIP
            #    on one of the VM and start ping6 to make the VM as master
            assert vm1_fixture.add_ip_on_vm(vIP)
            assert client_fixtures[0].ping_with_certainty(vIP), 'Ping to vIP failure'

        assert self.vrrp_mas_chk(vrrp_master, vn1_fixture, vIP)

        for vm in client_fixtures:
            for port in sport:
                assert self.send_nc_traffic(vm, vrrp_master,
                    port, dport, proto, ip=vIP)

        dst_compute_fix = self.compute_fixtures_dict[vrrp_master.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(vrrp_master.vn_fq_names[0])
        for vm in client_fixtures:
            self.verify_fat_flow_on_compute(dst_compute_fix, vm.vm_ip,
                        vIP, dport, proto, vrf_id_dst,
                        fat_flow_count=1)

        if is_v6(vIP):
            #Skip further verification as current version of vrrpd does not support IPv6
            return True
        self.logger.info('We will induce a mastership switch')
        port_dict = {'admin_state_up': False}
        self.update_port(port1_obj['id'], port_dict)
        self.logger.info(
            '%s should become the new VRRP master' % vm2_fixture.vm_name)
        vrrp_master = vm2_fixture
        assert self.vrrp_mas_chk(vrrp_master, vn1_fixture, vIP)

        for vm in client_fixtures:
            for port in sport:
                assert self.send_nc_traffic(vm, vrrp_master,
                    port, dport, proto, ip=vIP)

        dst_compute_fix = self.compute_fixtures_dict[vrrp_master.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(vrrp_master.vn_fq_names[0])
        for vm in client_fixtures:
            self.verify_fat_flow_on_compute(dst_compute_fix, vm.vm_ip,
                        vIP, dport, proto, vrf_id_dst,
                        fat_flow_count=1)

class FatFlowIpv6(FatFlow):
    @classmethod
    def setUpClass(cls):
        super(FatFlow, cls).setUpClass()
        cls.inputs.set_af(af_test)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
