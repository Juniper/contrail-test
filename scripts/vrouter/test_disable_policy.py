#Testcases for disabling policy on VMIs:
#PR https://bugs.launchpad.net/juniperopenstack/+bug/1558920 and PR https://bugs.launchpad.net/juniperopenstack/+bug/1566650
from builtins import str
from common.vrouter.base import BaseVrouterTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import get_random_cidr, get_random_name, is_v6, skip_because,\
    get_random_cidrs
import random
from security_group import get_secgrp_id_from_name
from common.servicechain.verify import VerifySvcChain
from netaddr import IPNetwork

AF_TEST = 'v6'

class DisablePolicyEcmp(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(DisablePolicyEcmp, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(DisablePolicyEcmp, cls).tearDownClass()

    @skip_because(hypervisor='docker',msg='Bug 1461423:Need privileged access')
    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_ecmp_with_static_routes(self):
        """
        Description: Verify disabling policy for ECMP routes with static routes on VM
        Steps:
            1. launch 1 VN and launch 3 VMs in it.
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix
            5. add new ECMP destinations and verify load is distributed to new destinations too
            6. remove ECMP destinations and verify load is distributed to remaining destinations
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        prefix_list = get_random_cidrs(self.inputs.get_af())
        assert prefix_list, "Unable to get a random CIDR"

        #Launch sender on first node and ECMP dest VMs on another node
        image = 'ubuntu-traffic'
        vm1_fixture = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        vm_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[1], image_name=image)
        #Launch 1 extra VM, to be used for new ECMP routes later
        vm4_fixture = self.create_vms(vn_fixture= vn1_fixture, count=1,
            node_name=compute_hosts[0], image_name=image)[0]

        self.verify_vms(vm_fixtures)
        self.verify_vms(vm1_fixture)
        vm1_fixture = vm1_fixture[0]
        vm2_fixture = vm_fixtures[0]
        vm3_fixture = vm_fixtures[1]

        #Add static routes, which will create ECMP routes
        static_ip_dict = {}
        for prefix in prefix_list:
            static_ip_dict[prefix] = self.add_static_routes_on_vms(prefix,
                [vm2_fixture, vm3_fixture])
        #Disable the policy on all the VMIs
        self.disable_policy_for_vms([vm1_fixture])
        self.disable_policy_for_vms(vm_fixtures)

        for prefix in prefix_list:
            assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
            assert self.verify_traffic_for_ecmp(vm1_fixture,
                [vm2_fixture,vm3_fixture], static_ip_dict[prefix])

        self.verify_vms([vm4_fixture])
        self.disable_policy_for_vms([vm4_fixture])

        #Add new ECMP destination and verify load is distributed to new destinations
        for prefix in prefix_list:
            self.add_static_routes_on_vms(prefix,
                                [vm4_fixture],
                                ip=static_ip_dict[prefix])
        self.delete_vms([vm2_fixture])
        for prefix in prefix_list:
            assert self.verify_ecmp_routes([vm3_fixture,vm4_fixture], prefix)
            assert self.verify_traffic_for_ecmp(vm1_fixture,
                            [vm3_fixture, vm4_fixture],
                            static_ip_dict[prefix])

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_ecmp_with_static_routes_intra_node(self):
        """
        Description: Verify disabling policy for ECMP routes with static routes on VM
        Steps:
            1. launch 1 VN and launch 3 VMs on the same node
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        prefix = get_random_cidr(af=self.inputs.get_af())
        assert prefix, "Unable to get a random CIDR"

        compute_hosts = self.orch.get_hosts()
        #launch all VMs on same node, to test intra node traffic
        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture=vn1_fixture, count=3,
            node_name=compute_hosts[0], image_name=image)
        self.verify_vms(vm_fixtures)
        vm1_fixture = vm_fixtures[0]
        vm2_fixture = vm_fixtures[1]
        vm3_fixture = vm_fixtures[2]

        static_ip = self.add_static_routes_on_vms(prefix, [vm2_fixture,vm3_fixture])
        self.disable_policy_for_vms(vm_fixtures)
        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture, [vm2_fixture,vm3_fixture], static_ip)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_disable_policy_with_aap(self):
        """
        Description: Verify disabling policy with allowed address pair
        Steps:
            1. launch 1 VN and launch 3 VMs in it.1 client VMs and 2 server VMs.
            2. disable the policy on all the VMIs.
            3. from client VMs,send udp traffic to servers and
                verify mastership and no flow
            4. Induce mastership switch and verify no flow again
        Pass criteria:
            1. flow and mastership verification should pass
        """
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
                                     port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vm2_name,
                                     image_name=image,
                                     port_ids=[port2_obj['id']])

        client_fixture = self.create_vms(vn_fixture= vn1_fixture,count=1,
            image_name=image)[0]
        vm_fix_list = [client_fixture, vm1_fixture, vm2_fixture]
        self.verify_vms(vm_fix_list)

        proto = 'udp'
        dport = 53
        baseport = random.randint(12000, 65000)
        sport = str(baseport)
        compute_node_ips = []
        compute_fixtures = []

        #Get all the VMs compute IPs
        for vm in vm_fix_list:
            if vm.vm_node_ip not in compute_node_ips:
                compute_node_ips.append(vm.vm_node_ip)

        #Get the compute fixture for all the concerned computes
        for ip in compute_node_ips:
            compute_fixtures.append(self.compute_fixtures_dict[ip])

        self.disable_policy_for_vms(vm_fix_list)

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
            assert client_fixture.ping_with_certainty(vIP), 'Ping to vIP failure'


        assert self.vrrp_mas_chk(dst_vm=vrrp_master, vn=vn1_fixture, ip=vIP)

        assert self.send_nc_traffic(client_fixture, vrrp_master,
            sport, dport, proto, ip=vIP)

        for fixture in compute_fixtures:
            vrf_id = fixture.get_vrf_id(vrrp_master.vn_fq_names[0])
            self.verify_flow_on_compute(fixture, client_fixture.vm_ip,
                        vIP, vrf_id, vrf_id, sport, dport, proto,
                        ff_exp=0, rf_exp=0)

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

        assert self.send_nc_traffic(client_fixture, vrrp_master,
            sport, dport, proto, ip=vIP)

        for fixture in compute_fixtures:
            vrf_id = fixture.get_vrf_id(vrrp_master.vn_fq_names[0])
            self.verify_flow_on_compute(fixture, client_fixture.vm_ip,
                        vIP, vrf_id, vrf_id, sport, dport, proto,
                        ff_exp=0, rf_exp=0)

        self.disable_policy_for_vms(vm_fix_list, disable=False)

        assert self.send_nc_traffic(client_fixture, vrrp_master,
            sport, dport, proto, ip=vIP)

        for fixture in [self.compute_fixtures_dict[client_fixture.vm_node_ip],
            self.compute_fixtures_dict[vrrp_master.vm_node_ip]]:
            vrf_id = fixture.get_vrf_id(vrrp_master.vn_fq_names[0])
            self.verify_flow_on_compute(fixture, client_fixture.vm_ip,
                        vIP, vrf_id, vrf_id, sport, dport, proto,
                        ff_exp=1, rf_exp=1)

    @preposttest_wrapper
    def test_disable_enable_policy_inter_node(self):
        """
        Description: Verify disabling enabling policy for ECMP routes with static routes on VM
        Steps:
            1. launch 1 VN and launch 3 VMs in it.
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable-enable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix, verify flow created
            5. Now disable the policy again and verify no flows
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        prefix = get_random_cidr(af=self.inputs.get_af())
        assert prefix, "Unable to get a random CIDR"

        #Launch sender on first node and ECMP dest VMs on another node
        image = 'ubuntu-traffic'
        vm1_fixture = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        vm_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[1], image_name=image)

        self.verify_vms(vm_fixtures)
        self.verify_vms(vm1_fixture)
        vm1_fixture = vm1_fixture[0]
        vm2_fixture = vm_fixtures[0]
        vm3_fixture = vm_fixtures[1]

        #Add static routes, which will create ECMP routes
        static_ip = self.add_static_routes_on_vms(prefix,
                                [vm2_fixture, vm3_fixture])
        #Disable the policy on all the VMIs
        self.disable_policy_for_vms([vm1_fixture])
        self.disable_policy_for_vms(vm_fixtures)
        #Enable the policy
        self.disable_policy_for_vms([vm1_fixture], disable=False)
        self.disable_policy_for_vms(vm_fixtures, disable=False)

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture,
                            [vm2_fixture,vm3_fixture], static_ip, flow_count=1)

        #Disable the policy on all the VMIs
        self.disable_policy_for_vms([vm1_fixture])
        self.disable_policy_for_vms(vm_fixtures)

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture,
                            [vm2_fixture,vm3_fixture], static_ip)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_disable_enable_policy_with_active_flows(self):
        """
        Description: Verify disabling enabling policy with active flows
        Steps:
            1. launch 1 VN and launch 3 VMs in it.
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable-enable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix, verify flow created
            5. Now disable the policy again and verify no flows
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        prefix = get_random_cidr(af=self.inputs.get_af())
        assert prefix, "Unable to get a random CIDR"

        #Launch sender on first node and ECMP dest VMs on another node
        image = 'ubuntu-traffic'
        vm1_fixture = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)
        vm_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[1], image_name=image)

        self.verify_vms(vm_fixtures)
        self.verify_vms(vm1_fixture)
        vm1_fixture = vm1_fixture[0]
        vm2_fixture = vm_fixtures[0]
        vm3_fixture = vm_fixtures[1]

        #Add static routes, which will create ECMP routes
        static_ip = self.add_static_routes_on_vms(prefix,
                                [vm2_fixture, vm3_fixture])

        #Start ping
        ping_h = self.start_ping(vm1_fixture, dst_ip=static_ip)
        #Disable the policy on all the VMIs
        self.disable_policy_for_vms([vm1_fixture])
        self.disable_policy_for_vms(vm_fixtures)
        #Enable the policy
        self.disable_policy_for_vms([vm1_fixture], disable=False)
        self.disable_policy_for_vms(vm_fixtures, disable=False)

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture,
                            [vm2_fixture,vm3_fixture], static_ip, flow_count=1)
        #Get ping stats
        stats = ping_h.get_stats()
        assert stats['loss'] == '0', ('Ping loss seen after disabling enabling policy with active flow')

        #Disable the policy on all the VMIs
        self.disable_policy_for_vms([vm1_fixture])
        self.disable_policy_for_vms(vm_fixtures)

        #Get ping stats again
        stats = ping_h.get_stats()
        assert stats['loss'] == '0', ('Ping loss seen after disabling policy with active flow')

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture,
                            [vm2_fixture,vm3_fixture], static_ip)

        stats = self.stop_ping(ping_h)
        assert stats['loss'] == '0', ('Ping loss seen after disabling policy with active flow')

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_disable_policy_remove_sg(self):
        """
        Description: Verify disabling policy with SG detach from vmi
        Steps:
            1. launch 1 VN and launch 3 VMs on the same node
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable the policy on all VMIs. and start ping
            4. remove the SG from all VMIs
            5. Now from 3rd VM send traffic to an IP from static route prefix
        Pass criteria:
            1. traffic should go through fine and no ping loss
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        prefix = get_random_cidr(af=self.inputs.get_af())
        assert prefix, "Unable to get a random CIDR"

        compute_hosts = self.orch.get_hosts()
        #launch all VMs on same node, to test intra node traffic
        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture=vn1_fixture, count=3,
            node_name=compute_hosts[0], image_name=image)
        self.verify_vms(vm_fixtures)
        vm1_fixture = vm_fixtures[0]
        vm2_fixture = vm_fixtures[1]
        vm3_fixture = vm_fixtures[2]

        static_ip = self.add_static_routes_on_vms(prefix, [vm2_fixture,vm3_fixture])

        #Start ping
        ping_h = self.start_ping(vm1_fixture, dst_ip=static_ip)
        self.disable_policy_for_vms(vm_fixtures)
        #Remove the SG from all VMs
        self.remove_sg_from_vms(vm_fixtures)

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture, [vm2_fixture,vm3_fixture], static_ip)

        #Get ping stats
        stats = ping_h.get_stats()
        assert stats['loss'] == '0', ('Ping loss seen after disabling policy with active flow')

        #Attach the SGs back
        self.add_sg_to_vms(vm_fixtures)
        #Get ping stats
        stats = ping_h.get_stats()
        assert stats['loss'] == '0', ('Ping loss seen after disabling policy with active flow')

        #Remove the SG from all VMs
        self.remove_sg_from_vms(vm_fixtures)
        self.sleep(10)
        #Enable the policy now, some ping loss should be seen now
        self.disable_policy_for_vms(vm_fixtures, disable=False)
        self.sleep(10)
        stats = self.stop_ping(ping_h)
        assert stats['loss'] != '0', ('Ping loss not seen after enabling policy with active flow')

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_remove_sg_disable_policy(self):
        """
        Description: Verify disabling policy with SG detach from vmi
        Steps:
            1. launch 1 VN and launch 3 VMs on the same node
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. remove the SG from all VMIs
            4. Disable the policy on all VMIs. and start ping
            5. Now from 3rd VM send traffic to an IP from static route prefix
        Pass criteria:
            1. traffic should go through fine and no ping loss
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """

        vn_fixtures = self.create_vns(count=1)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        prefix = get_random_cidr(af=self.inputs.get_af())
        assert prefix, "Unable to get a random CIDR"

        compute_hosts = self.orch.get_hosts()
        #launch all VMs on same node, to test intra node traffic
        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture=vn1_fixture, count=3,
            node_name=compute_hosts[0], image_name=image)
        self.verify_vms(vm_fixtures)
        vm1_fixture = vm_fixtures[0]
        vm2_fixture = vm_fixtures[1]
        vm3_fixture = vm_fixtures[2]

        static_ip = self.add_static_routes_on_vms(prefix, [vm2_fixture,vm3_fixture])

        #Remove the SG from all VMs
        self.remove_sg_from_vms(vm_fixtures)

        #Start ping
        ping_h = self.start_ping(vm1_fixture, dst_ip=static_ip)
        #Get ping stats
        self.sleep(1)
        stats = ping_h.get_stats()
        assert stats['received'] == '0', ('Ping succeeded without SG')
        assert stats['loss'] == '100', ('Ping succeeded without SG')

        self.disable_policy_for_vms(vm_fixtures)

        assert self.verify_ecmp_routes([vm2_fixture,vm3_fixture], prefix)
        assert self.verify_traffic_for_ecmp(vm1_fixture, [vm2_fixture,vm3_fixture], static_ip)

        #Get ping stats
        stats = ping_h.get_stats()
        assert int(stats['received']) != 0, ('Ping failed without SG even when policy disabled')

        self.stop_ping(ping_h)

class DisablePolicy(BaseVrouterTest, VerifySvcChain):

    @classmethod
    def setUpClass(cls):
        super(DisablePolicy, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(DisablePolicy, cls).tearDownClass()

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_disable_policy_sg_inter_vn(self):
        """
        Description: Verify disabling policy for inter VN,inter/intra node traffic with SG
        Steps:
            1. launch 2 VNs and launch 3 VMs in it.
            2. disable policy only on destination VMs and add/remove SG and start traffic
        Pass criteria:
            1. traffic should go through and flow should not be created
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=2, rt_number='10000')
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        vn2_fixture = vn_fixtures[1]

        #Launch 1 VM in first VN and 2 VMs in another VN
        image = 'ubuntu-traffic'
        src_vm_fixture = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)[0]
        dst_vm_fixture1 = self.create_vms(vn_fixture= vn2_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)[0]
        dst_vm_fixture2 = self.create_vms(vn_fixture= vn2_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)[0]
        self.verify_vms([src_vm_fixture, dst_vm_fixture1, dst_vm_fixture2])

        self.disable_policy_for_vms([dst_vm_fixture1, dst_vm_fixture2])

        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.connections.domain_name,
                                        self.inputs.project_name,
                                        'default']))
        rule = [{'direction': '<>',
                 'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        sg_fixture = self.create_sg(entries=rule)
        self.verify_sg(sg_fixture)
        proto = 'udp'
        #For Inter node traffic test, use src_vm_fixture and dst_vm_fixture2
        #For Intra node, use src_vm_fixture and dst_vm_fixture1
        for vm in [dst_vm_fixture1, dst_vm_fixture2]:
            if (vm == dst_vm_fixture1):
                #Intra Node
                ff_exp = 1
                rf_exp = 1
            else:
                #Inter Node
                ff_exp = 0
                rf_exp = 0
            #1. receiver VMI SG with allow rule, use default SG
            self.send_traffic_verify_flow_dst_compute(src_vm_fixture,
                vm, proto, ff_exp=ff_exp, rf_exp=rf_exp)

            #2. receiver VMI SG with only egress rule
            self.remove_sg_from_vms([vm], sg_id=default_sg_id)
            self.add_sg_to_vms([vm], sg_id=sg_fixture.secgrp_id)
            self.send_traffic_verify_flow_dst_compute(src_vm_fixture,
                vm, proto, ff_exp=ff_exp, rf_exp=rf_exp)

            #3. receiver VMI SG without any rule
            sg_fixture.delete_all_rules()
            self.send_traffic_verify_flow_dst_compute(src_vm_fixture,
                vm, proto, ff_exp=ff_exp, rf_exp=rf_exp)

            #4. receiver VMI without SG
            self.remove_sg_from_vms([vm], sg_id=sg_fixture.secgrp_id)
            self.send_traffic_verify_flow_dst_compute(src_vm_fixture,
                vm, proto, ff_exp=ff_exp, rf_exp=rf_exp)

    @test.attr(type=['dev_reg'])
    @preposttest_wrapper
    def test_disable_policy_with_vn_policy(self):
        """
        Description: Verify disabling policy for inter VN,inter/intra node traffic with VNs policy
        Steps:
            1. launch 2 VNs and launch 5 VMs in it
            2. disable policy only on destination VMs
            3. policy deny rule: deny udp protocol and allow others
        Pass criteria:
            1. udp traffic should be denied and other proto like ping should succeed.
            2. flow should be created for intra node and not for inter node on dest compute
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn_fixtures = self.create_vns(count=2)
        self.verify_vns(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        vn2_fixture = vn_fixtures[1]

        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture= vn1_fixture,count=2,
            node_name=compute_hosts[0], image_name=image)
        src_vm_fixture = vm_fixtures[0]
        vm_vn1_fixture1 = vm_fixtures[1]
        vm_vn1_fixture2 = self.create_vms(vn_fixture= vn1_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)[0]
        dst_vm_fixture1 = self.create_vms(vn_fixture= vn2_fixture,count=1,
            node_name=compute_hosts[0], image_name=image)[0]
        dst_vm_fixture2 = self.create_vms(vn_fixture= vn2_fixture,count=1,
            node_name=compute_hosts[1], image_name=image)[0]
        self.verify_vms(vm_fixtures)
        self.verify_vms([vm_vn1_fixture2, dst_vm_fixture1, dst_vm_fixture2])

        self.disable_policy_for_vms([vm_vn1_fixture1, vm_vn1_fixture2,
            dst_vm_fixture1, dst_vm_fixture2])

        #Inter VN without policy attached
        proto = 'udp'
        sport = 10000
        dport = 11000

        assert self.send_nc_traffic(src_vm_fixture, dst_vm_fixture1, sport, dport,
            proto, exp=False)

        compute_fix = self.compute_fixtures_dict[dst_vm_fixture1.vm_node_ip]
        src_vrf = compute_fix.get_vrf_id(src_vm_fixture.vn_fq_names[0])
        dst_vrf = compute_fix.get_vrf_id(dst_vm_fixture1.vn_fq_names[0])

        self.verify_flow_on_compute(compute_fix, src_vm_fixture.vm_ip,
            dst_vm_fixture1.vm_ip, src_vrf, dst_vrf, sport=sport, dport=dport, proto=proto,
            ff_exp=0, rf_exp=0)

        rules = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'udp', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_fixture.vn_fq_name,
                'dest_network': vn2_fixture.vn_fq_name,
            },
            {
                'direction': '<>',
                'protocol': 'udp',
                'dest_subnet': str(IPNetwork(vm_vn1_fixture1.vm_ip)),
                'source_subnet': str(IPNetwork(src_vm_fixture.vm_ip)),
                'dst_ports': 'any',
                'simple_action': 'deny',
                'src_ports': 'any'
            },
            {
                'direction': '<>',
                'protocol': 'udp',
                'dest_subnet': str(IPNetwork(vm_vn1_fixture2.vm_ip)),
                'source_subnet': str(IPNetwork(src_vm_fixture.vm_ip)),
                'dst_ports': 'any',
                'simple_action': 'deny',
                'src_ports': 'any'
            },
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_fixture.vn_fq_name,
                'dest_network': vn2_fixture.vn_fq_name,
            }
        ]
        policy_name = get_random_name("policy1")
        policy_fixture = self.config_policy(policy_name, rules)
        vn1_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn1_fixture)
        vn2_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn2_fixture)

        for vm in [vm_vn1_fixture1, vm_vn1_fixture2, dst_vm_fixture1, dst_vm_fixture2]:
            errmsg = "Ping to VM ip %s from VM ip %s failed" % (
                        vm.vm_ip, src_vm_fixture.vm_ip)

            if (vm == vm_vn1_fixture1) or (vm == dst_vm_fixture1):
                #Intra Node
                ff_exp = 1
                rf_exp = 1
            else:
                #Inter Node
                ff_exp = 0
                rf_exp = 0
            self.send_traffic_verify_flow_dst_compute(src_vm_fixture,
                vm, proto, ff_exp=ff_exp, rf_exp=rf_exp, exp=False)
            assert src_vm_fixture.ping_with_certainty(vm.vm_ip), errmsg

class DisablePolicyEcmpIpv6(DisablePolicyEcmp):
    @classmethod
    def setUpClass(cls):
        super(DisablePolicyEcmpIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):

        AF_TEST = 'v6'
        self.logger.info('Address family configured is %s' % self.inputs.get_af())
        self.logger.info('we are setting address family as %s' % AF_TEST)
        self.inputs.set_af(AF_TEST)
        self.logger.info('we are setting address family as %s' % self.inputs.get_af())

        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        if not self.connections.orch.is_feature_supported('ipv6'):
            return(False, 'IPv6 tests not supported in this environment ')
        return (True, None)

    @skip_because(hypervisor='docker',msg='Bug 1461423:Need privileged access')
    @test.attr(type=['cb_sanity', 'sanity','dev_reg'])
    def test_ecmp_with_static_routes(self):
        self.inputs.set_af('dual')
        super(DisablePolicyEcmpIpv6, self).test_ecmp_with_static_routes()
        self.inputs.set_af(AF_TEST)

class DisablePolicyIpv6(DisablePolicy):
    @classmethod
    def setUpClass(cls):
        super(DisablePolicyIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported('ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
