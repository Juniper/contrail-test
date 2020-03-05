from builtins import str
from common.vrouter.base import BaseVrouterTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import get_random_name, is_v6
import random
from common.neutron.lbaasv2.base import BaseLBaaSTest

AF_TEST = 'v6'

class FatFlow(BaseVrouterTest, BaseLBaaSTest):

    @classmethod
    def setUpClass(cls):
        super(FatFlow, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(FatFlow, cls).tearDownClass()

    #This is required just to override the method in BaseLBaaSTest, else tests
    #run only in openstack liberty and up
    def is_test_applicable(self):
        return (True, None)

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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        afs = ['v4', 'v6'] if 'dual' in self.inputs.get_af() else [self.inputs.get_af()]
        for af in afs:
            self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                                proto, port, af=af)

    @test.attr(type=['dev_reg'])
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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
        fat_flow_config = {'proto':proto,'port':port}
        self.add_fat_flow_to_vmis(server_vmi_id, fat_flow_config)

        self.verify_fat_flow_with_traffic(client_fixtures,server_fixtures[0],
                                            proto, port)

    @test.attr(type=['dev_reg'])
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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
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

    @test.attr(type=['dev_reg'])
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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
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
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
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
            2. on server VMs, config Fat flow for udp with port 0
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
        fat_port = 0
        baseport = random.randint(12000, 65000)
        sport = [str(baseport), str(baseport+1)]
        fat_flow_config = {'proto':proto,'port':fat_port}
        self.add_fat_flow_to_vmis([port1_obj['id'], port2_obj['id']], fat_flow_config)

        port_list = [port1_obj, port2_obj]                                      
        for port in port_list:                                                  
            self.config_aap(port['id'], vIP, mac=port['mac_address'])
        self.config_vrrp(vm1_fixture, vIP, '20')
        self.config_vrrp(vm2_fixture, vIP, '10')
        vrrp_master = vm1_fixture
        if is_v6(vIP):
            #current version of vrrpd does not support IPv6, as a workaround add the vIP
            #    on one of the VM and start ping6 to make the VM as master
            assert vm1_fixture.add_ip_on_vm(vIP)
            assert client_fixtures[0].ping_with_certainty(vIP), 'Ping to vIP failure'

        assert self.vrrp_mas_chk(dst_vm=vrrp_master, vn=vn1_fixture, ip=vIP)

        for vm in client_fixtures:
            for port in sport:
                assert self.send_nc_traffic(vm, vrrp_master,
                    port, dport, proto, ip=vIP)

        dst_compute_fix = self.compute_fixtures_dict[vrrp_master.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(vrrp_master.vn_fq_names[0])
        for vm in client_fixtures:
            self.verify_fat_flow_on_compute(dst_compute_fix, vm.vm_ip,
                        vIP, fat_port, proto, vrf_id_dst,
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
        assert self.vrrp_mas_chk(dst_vm=vrrp_master, vn=vn1_fixture, ip=vIP)

        for vm in client_fixtures:
            for port in sport:
                assert self.send_nc_traffic(vm, vrrp_master,
                    port, dport, proto, ip=vIP)

        dst_compute_fix = self.compute_fixtures_dict[vrrp_master.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(vrrp_master.vn_fq_names[0])
        for vm in client_fixtures:
            self.verify_fat_flow_on_compute(dst_compute_fix, vm.vm_ip,
                        vIP, fat_port, proto, vrf_id_dst,
                        fat_flow_count=1)

    @preposttest_wrapper
    def test_fat_flow_with_aap_ignore_addrs(self):
        """
        Description: Verify Fat flows with ignore addrs with allowed address pair
        Steps:
            1. launch 1 VN and launch 4 VMs in it.2 client VMs and 2 server VMs on different node.
            2. on server VMs, config Fat flow for udp with port 0
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
        dport_list = [53, 54]
        baseport = random.randint(12000, 65000)
        sport_list = [str(baseport), str(baseport+1)]
        port_list = [port1_obj, port2_obj]

        for port in port_list:
            self.config_aap(port['id'], vIP, mac=port['mac_address'])
        self.config_vrrp(vm1_fixture, vIP, '20')
        self.config_vrrp(vm2_fixture, vIP, '10')
        vrrp_master = vm1_fixture
        if is_v6(vIP):
            #current version of vrrpd does not support IPv6, as a workaround add the vIP
            #    on one of the VM and start ping6 to make the VM as master
            assert vm1_fixture.add_ip_on_vm(vIP)
            assert client_fixtures[0].ping_with_certainty(vIP), 'Ping to vIP failure'

        assert self.vrrp_mas_chk(dst_vm=vrrp_master, vn=vn1_fixture, ip=vIP)

        fat_ignore_src = {'proto':proto,'port':dport_list[0],
            'ignore_address':'source'}
        fat_ignore_dst = {'proto':proto,'port':dport_list[1],
            'ignore_address':'destination'}
        fat_ignore_dst_port_0 = {'proto':proto,'port':0,
            'ignore_address':'destination'}
        fat_config_list = [fat_ignore_src, fat_ignore_dst,
            fat_ignore_dst_port_0]

        dst_compute_fix = self.compute_fixtures_dict[vrrp_master.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(vrrp_master.vn_fq_names[0])
        for fat_config in fat_config_list:
            self.add_fat_flow_to_vmis([port1_obj['id'], port2_obj['id']],
                fat_config)
            for vm in client_fixtures:
                for sport in sport_list:
                    for dport in dport_list:
                        assert self.send_nc_traffic(vm, vrrp_master,
                            sport, dport, proto, ip=vIP)
                if fat_config['ignore_address'] == 'source':
                    fat_src_ip = '0.0.0.0' if self.inputs.get_af() == 'v4' else '::'
                    self.verify_fat_flow_on_compute(dst_compute_fix, vm.vm_ip,
                                fat_src_ip, fat_config['port'], proto, vrf_id_dst,
                                fat_flow_count=1)
                if fat_config['ignore_address'] == 'destination':
                    fat_dst_ip = '0.0.0.0' if self.inputs.get_af() == 'v4' else '::'
                    self.verify_fat_flow_on_compute(dst_compute_fix, fat_dst_ip,
                                vIP, fat_config['port'], proto, vrf_id_dst,
                                fat_flow_count=1)
            self.remove_fat_flow_on_vmis([port1_obj['id'], port2_obj['id']],
                fat_config)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_fat_flow_lbaasv2(self):
        '''Creates Lbaas pool with lb-method ROUND ROBIN, 3 members and vip
           Verify: lb-method ROUND ROBIN works as expected, fail otherwise
        '''
        if self.inputs.orchestrator.lower() != 'openstack':
            raise self.skipTest("Skipping Test. Openstack required")
        if self.inputs.get_build_sku().lower()[0] < 'l':
            raise self.skipTest("Skipping Test. LBaasV2 is supported only on liberty and up")

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn_vip_fixture = vn_fixtures[0]
        image = 'ubuntu'
        vm_fixtures = self.create_vms(vn_fixture=vn_vip_fixture,count=3,
            image_name=image)
        self.verify_vms(vm_fixtures)

        lb_pool_servers = vm_fixtures[1:]
        client_vm1_fixture = vm_fixtures[0]
        result = True
        pool_members = {}
        members=[]
        pool_name = get_random_name('mypool')
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        port = 80
        vip_name = get_random_name('myvip')
        listener_name = get_random_name(protocol)

        for VMs in lb_pool_servers:
            members.append(VMs.vm_ip)

        pool_members.update({'address':members})

        #Configure Fat flow on the pool servers
        proto = 'tcp'
        fat_flow_config = {'proto':proto,'port':port}
        for vm in lb_pool_servers:
            vmi_id = list(vm.get_vmi_ids().values())
            self.add_fat_flow_to_vmis(vmi_id, fat_flow_config)

        for vm in lb_pool_servers:
            vm.start_webserver(listen_port=port)

        #Call LB fixutre to create LBaaS VIP, Listener, POOL and Members
        lb = self.create_lbaas(vip_name, vn_vip_fixture.get_uuid(),
              pool_name=pool_name, pool_algorithm=lb_method, pool_protocol=protocol,
              pool_port=port, members=pool_members, listener_name=listener_name,
              vip_port=port, vip_protocol=protocol)

        #Verify all the creations are success
        assert lb.verify_on_setup(), "Verify LB method failed"

        assert self.verify_lb_method(client_vm1_fixture, lb_pool_servers,
            lb.vip_ip), "Verify lb method failed"

        #Verify Fat flow on lb_pool_servers computes
        for vm in lb_pool_servers:
            compute_fix = self.compute_fixtures_dict[vm.vm_node_ip]
            vrf_id = compute_fix.get_vrf_id(vm.vn_fq_names[0])
            self.verify_fat_flow_on_compute(compute_fix, lb.vip_ip,
                        vm.vm_ip, port, proto, vrf_id,
                        fat_flow_count=1)

        #Verify the flow on client compute
        #Skip the below check until bug 1625002 is fixed
        '''compute_fix_client = self.compute_fixtures_dict[
            client_vm1_fixture.vm_node_ip]
        (ff_count, rf_count) = compute_fix_client.get_flow_count(
                                    source_ip=client_vm1_fixture.vm_ip,
                                    dest_ip=lb.vip_ip,
                                    source_port=None,
                                    dest_port=port,
                                    proto=proto,
                                    vrf_id=compute_fix_client.get_vrf_id(
                                              client_vm1_fixture.vn_fq_names[0])
                                    )
        assert ff_count != 0 , ('Flows count '
            'mismatch on client compute, got:%s' % (ff_count))
        assert rf_count != 0, ('Flows count '
            'mismatch on client compute, got:%s' % (rf_count))'''


class FatFlowIpv6(FatFlow):
    @classmethod
    def setUpClass(cls):
        super(FatFlow, cls).setUpClass()
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

    @test.attr(type=['cb_sanity', 'sanity'])
    def test_fat_flow_intra_vn_inter_node(self):
        self.inputs.set_af('dual')
        super(FatFlowIpv6, self).test_fat_flow_intra_vn_inter_node()
