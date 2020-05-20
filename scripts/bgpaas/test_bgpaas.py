from common.bgpaas.base import BaseBGPaaS
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds


class TestBGPaaS(BaseBGPaaS):

    @preposttest_wrapper
    def disable_test_bgpaas_tunnel_encap(self):
        """
        disabling this as of now this is not supported
        Description: Configure tunnel-encap on bgpaas session parameter and verify tunnel-encap is correctly seen in VRF
        Test Steps:
           1. Create a bgpaas service,ubuntu-bird vm and advertise 0.0.0.0 from the VM
           2. Configure tunnel-encap as mpls,gre and verify 0.0.0.0 route has this tunnel-encap
           3. Update tunnel-encap as udp,vxlan and verify 0.0.0.0 route has this tunnel-encap
        Maintainer: vageesant@juniper.net
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(45000,45100)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes)

        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen")
        else:
           assert False,"BGP session with Controller is not seen"

        input_encap_list = ["mpls","gre"]
        # mpls,gre,udp,vxlan
        self.set_addr_family_attr(bgpaas_fixture,"inet",tunnel_encap_list=input_encap_list)
 
        for cn in self.inputs.bgp_control_ips:
            entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for entry in entries:
                if entry["protocol"] == 'BGP (bgpaas)':
                   for encap in input_encap_list: 
                       if encap not in entry["tunnel_encap"]:
                          assert False,"Configured tunnel_encap is missing in the route entry"

        self.logger.info("Configured tunnel_encap is seen in the route entries")
        self.logger.info("re-configure tunnel-encap")
        input_encap_list = ["udp","vxlan"]

        self.set_addr_family_attr(bgpaas_fixture,"inet",tunnel_encap_list=["udp","vxlan"])
 
        for cn in self.inputs.bgp_control_ips:
            entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for entry in entries:
                if entry["protocol"] == 'BGP (bgpaas)':
                   for encap in input_encap_list: 
                       if encap not in entry["tunnel_encap"]:
                          assert False,"Configured tunnel_encap is missing in the route entry"
        self.logger.info("Updated tunnel_encap is seen in the route entries")

    @preposttest_wrapper
    def test_bgpaas_community(self):
        """
        Description: Verify community attribute advertised by BGP VM is seen correctly on all controllers
        Test Steps:
            1. Configure BGP VM to advertise community for 0.0.0.0/0 route
            2. Verify this community attribute is seen for 0.0.0.0/0 on all controllers VRF.
        Maintainer: vageesant@juniper.net
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(1000,2000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        community_asn = 65000
        community_num = 666 
        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]
        export_filter = [ "export filter bgp_out_uplink_a;",
                          """filter bgp_out_uplink_a
                             {
                             bgp_community.add((%d,%d));
                             accept;
                             }
                          """ %(community_asn,community_num)
                         ]

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes,export_filter_cmds=export_filter)

        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen")
        else:
           assert False,"BGP session with Controller is not seen"

        community_str = "%d:%d"%(community_asn,community_num)
        community_not_seen = False
        for cn in self.inputs.bgp_control_ips:
            entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for entry in entries:
                if community_str not in entry["communities"]:
                   community_not_seen = True
                   break

        if not community_not_seen:
           self.logger.info("Communities sent by BGPaaS VM is seen in control node")
        else:
           assert False,"Communities sent by BGPaaS VM is NOT seen in control node" 
 
    @preposttest_wrapper
    def test_bgpaas_ibgp(self):
        """
        Description: Verify iBGP session is not supported in BGPaaS
        Test Steps:
           1. Configure iBGP session on bgp vm.
           2. Verify BGP session is not established.
        Maintainer: vageesant@juniper.net:
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        bgpaas_as = random.randint(21000,22000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=bgpaas_as)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=bgpaas_as,
            local_as=bgpaas_as,static_routes=static_routes)

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           assert False,"BGP session with Controller is seen with iBGP configuration"
        else:
           self.logger.info("BGP session with Controller is NOT seen as expected in iBGP configuration")
 
    @preposttest_wrapper
    def disabled_test_bgpaas_private_as_action(self):
        """
        disabling this as of now this is not supported
        Description: Verify private-as action remove,remove-all,replace-all
        Test Steps: 
            1. Configure BGP VM to advertise routes with private-as
            2. Set private-as action in bgp session attribute as remove
               Verify left-most private-as number is removed.
            3. Set private-as action in bgp session attribute as remove-all
               Verify all the private-as numbers are removed
            4. set private-as action in bgp session attribute as replace-all
               Verify all the private-as numbers are replaced with local-as of controller
        Maintainer: vageesant@juniper.net
        """
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(23000,24000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)
        self.set_private_as_action(bgpaas_fixture,"")
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]
        export_filter = [ "export filter bgp_out_uplink_a;",
                          """filter bgp_out_uplink_a
                             {
                             bgp_path.prepend(%d);
                             bgp_path.prepend(%d);
                             bgp_path.prepend(%d);
                             bgp_path.prepend(%d);
                             bgp_path.prepend(%d);
                             accept;
                             }
                          """ %(64512,40000,64513,30000,bgpaas_as)
                         ]

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes,export_filter_cmds=export_filter)

        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")
 
        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)
        as_path_configured = "%s 30000 64513 40000 64512 %s"%(bgpaas_as,bgpaas_as)
        expected_as_path = {}
        expected_as_path["remove"] = "%s 30000 40000 64512"%bgpaas_as
        expected_as_path["remove-all"] = "%s 30000 40000"%bgpaas_as
        expected_as_path["replace-all"] = "%s 30000 %s 40000 %s"%(bgpaas_as,cluster_local_autonomous_system,cluster_local_autonomous_system)
        action_list = expected_as_path.keys()
        for action in action_list:
            self.set_private_as_action(bgpaas_fixture,action)
            ret = self.get_private_as_action()
            if ret == action:
               self.logger.info("Private-as-action is update to %s correctly"%action)
            else:
               assert False,"private-as-action update to %s failed"%action
            expect_as_path_seen = False
            for cn in self.inputs.bgp_control_ips:
                entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
                for entry in entries:
                    if entry["protocol"] == 'BGP (bgpaas)':
                       if entry["as_path"] == expected_as_path[action]:
                          expect_as_path_seen = True
                          break
            if expect_as_path_seen:
               self.logger.info("Private-as-action for %s is working correctly"%action)
            else:
               assert False,"Private-as-action for %s is incorrect"%action
 
    @preposttest_wrapper
    def test_bgpaas_ipv6_prefix_limit_idle_timeout(self):
        """
        Description: Configure max-prefix limit for ipv6 and idle timeout when max-prefix limit is hit
        Test Steps:
           1. Configure vsrx VM to advertise 50 ipv6 prefixes and verify BGP session is up.
           2. Limit ipv6 max-prefix to 20 and idle timeout of 300.Verify BGP session is down.
           3. Reduce the number of ipv6 prefix to 10 and Verify BGP session dont come up before idle timeout.
           4. Check the BGP session comes up after idle timeout
        Maintainer: vageesant@juniper.net
        """

        addr_family = "v6"

        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='vsrx')
        assert test_vm.wait_till_vm_is_up()

        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"

        autonomous_system1 = 63500

        bgpaas_fixture1 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=autonomous_system1, bgpaas_ip_address=bgpaas_vm1.vm_ip)
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]

        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system1, neighbors=neighbors, bfd_enabled=False)
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture1)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture1)

        cmds = []
        for i in range(50):
            cidr = get_random_cidr(af=addr_family)
            cmds.append("set routing-options rib inet6.0 static route %s discard"%cidr)

        self.logger.info("Configuring %d inet6 routes in vsrx vm"%len(cmds))
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm1,cmds=cmds)

        ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("bgpaas_vm1: BGPaaS Session is seen")

        assert bgpaas_fixture1.verify_in_control_node(
            bgpaas_vm1), 'bgpaas_vm1: BGPaaS Session not seen in the control-node'

        self.logger.info("Setting max_prefix_limit for inet6 to 20")
        self.set_addr_family_attr(bgpaas_fixture1,"inet6",limit=20,idle_timeout=300)

        time.sleep(10)

        ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if not ret: # retry
           ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if ret:
           assert False,"BGP session with Controller is seen when vsrx is advertising 50 inet6 prefix and max_prefix_limit is 20"
        else:
           self.logger.info("BGP session with Controller is NOT seen , as expected , after setting max_prefix_limit to 20")

        cmds.insert(0,"delete routing-options rib inet6.0")
        self.logger.info("Configuring %d inet6 routes in vsrx vm"%len(cmds[:10]))
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm1,cmds=cmds[:10])

        time.sleep(60)

        ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if ret:
           assert False,"BGP session with Controller is seen even before idle_timeout"
        else:
           self.logger.info("BGP session with Controller is NOT seen before idle_timeout")

        time.sleep(300)

        ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen after idle_timeout")
        else:
           assert False,"BGP session with Controller is NOT seen after idle_timeout"

    @preposttest_wrapper
    def test_bgpaas_ipv4_prefix_limit_idle_timeout(self):
        """
        Description: Configure max-prefix limit for ipv4 and idle timeout when max-prefix limit is hit
        Test Steps:
           1. Configure vsrx VM to advertise 50 ipv4 prefixes and verify BGP session is up.
           2. Limit ipv4 max-prefix to 20 and idle timeout of 300.Verify BGP session is down.
           3. Reduce the number of ipv4 prefix to 10 and Verify BGP session dont come up before idle timeout.
           4. Check the BGP session comes up after idle timeout
        Maintainer: vageesant@juniper.net
        """

        addr_family = "v4"

        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(25000,26000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        static_routes_list = []
        for i in range(50):
            cidr = get_random_cidr(af=addr_family)
            static_routes_list.append({"network":cidr,"nexthop":"blackhole"})
        
        self.logger.info("Configuring %d inet6 routes in vsrx vm"%len(static_routes_list))

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes_list)

        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

        self.logger.info("Configuring set_addr_family_attr for inet to 20")
        self.set_addr_family_attr(bgpaas_fixture,"inet",limit=20,idle_timeout=300)
        time.sleep(10)
        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
          assert False,"BGP session with Controller is seen when bird advertises 50 inet prefixes and set_addr_family_attr=20"
        else:
          self.logger.info("BGP session with Controller is NOT seen when bird advertises 50 inet prefixes and set_addr_family_attr=20")

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes_list[:10])

        time.sleep(10)
        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if not ret: # retry
           ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
          assert False,"BGP session with Controller is seen when bird advertises 50 inet prefixes and set_addr_family_attr=20 , before idle-timeout"
        else:
          self.logger.info("BGP session with Controller is seen when bird advertises 50 inet prefixes and set_addr_family_attr=20,before idle timeout")

        time.sleep(300)

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen after idle_timeout")
        else: 
           assert False,"BGP session with Controller is NOT seen after idle_timeout"


    @preposttest_wrapper
    def test_bgpaas_hold_time(self):

        """
        Description: Verify BGP session is created with configured hold-time
        Test Steps:
             1. Configure BGP session with max hold time 65535 in BGP VM , so that it accepts any hold time by peer
             2. Verify by default BGP session from vrouter/controller is created with default hold time=0
             3. Update hold time with 20s and random time and Verify BGP session up.
        Maintainer: vageesant@juniper.net
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(27000,28000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,hold_time=65535)

        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")
        hold_time = self.get_hold_time(bgpaas_fixture)
        assert hold_time == 0 , "hold_time is not set 0 by default.current value is %d"%hold_time
        random_hold_time = random.randint(0,65535)

        test_hold_times = [ 20 , random_hold_time ]

        for hold_time in test_hold_times:
            self.set_hold_time(bgpaas_fixture,random_hold_time)

            current_set_hold_time = self.get_hold_time(bgpaas_fixture)

            if current_set_hold_time == random_hold_time:
               self.logger.info("Hold timer is updated on the bgpaas object correctly")
            else:
               assert False, "hold time is not updated"
            time.sleep(5)
            ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
            if ret:
               self.logger.info("BGP session is not up after updating hold_time")
            else:
               assert False,"BGP session is not up after updating hold_time"
 
            output=bgpaas_vm1.run_cmd_on_vm(cmds=["birdc show protocols all"],as_sudo=True)
            ret = re.search("Hold timer:\s+(\d+)/(?P<hold>\d+)",output['birdc show protocols all'])
            hold_timer_seen = ret.group('hold') if ret else -1
            if int(ret.group('hold')) == random_hold_time:
               hold_timer_seen = int(ret.group('hold'))
               self.logger.info("Hold timer is seen correctly in the peer:%d"%int(random_hold_time))
            assert hold_timer_seen == random_hold_time,"Hold timer seen in the peer is incorrect.Expected: %d , Actual: %d"%(random_hold_time,hold_timer_seen)
 
    @preposttest_wrapper
    def test_bgpaas_asn_update(self):
        """
        Description: Update the AS of the BGPaaS VM to different values
        Test Steps:
           1. Create BGPaaS service with the AS mentioned in bgpaas_as[0]
           2. Update the AS in the BGPaaS service and also in BGP VM to different values from bgpaas_as list.
           3. Verify BGP session is established after updating AS of the BGPaaS and also AS_PATH is correctly set with new AS.
        Maintainer: vageesant@juniper.net
        """
        bgpaas_as = [ 64000,84000,54000]
        cluster_local_as = [64100,84100,54100]
        as4_flag  = [ False,True,True]
         
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]

        cn_inspect_handle = {}

        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        assert test_vm.wait_till_vm_is_up()
        assert bgpaas_vm1.wait_till_vm_is_up()

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')
        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]

        bgpaas_fixture = None

        existing_as4_flag = self.get_4byte_enable()
        self.addCleanup(self.set_4byte_enable,existing_as4_flag)

        for i,val in enumerate(bgpaas_as):
            autonomous_system = bgpaas_as[i]
            cluster_local_autonomous_system = cluster_local_as[i]
            current_as_flag = as4_flag[i]
            if existing_as4_flag != current_as_flag :
              self.set_4byte_enable(current_as_flag)
              existing_as4_flag = current_as_flag
            if i == 0 : 
               bgpaas_fixture = self.create_bgpaas(
                                      bgpaas_shared=True, autonomous_system=autonomous_system,
                                      bgpaas_ip_address=bgpaas_vm1.vm_ip,
                                      local_autonomous_system=cluster_local_autonomous_system)
               self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
            else:
               self.update_bgpaas_as(bgpaas_fixture=bgpaas_fixture,
                                     autonomous_system=autonomous_system,
                                     local_autonomous_system=cluster_local_autonomous_system)

            self.config_bgp_on_bird(
                     bgpaas_vm=bgpaas_vm1,
                     local_ip=bgpaas_vm1.vm_ip,
                     neighbors=neighbors,
                     peer_as=cluster_local_autonomous_system,
                     local_as=autonomous_system,
                     static_routes=static_routes)

            ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
            if ret:
               self.logger.info("BGP Session is established with Control node")
            else:
               assert False,"BGP Session is not established with Control node"

            for cn in self.inputs.bgp_control_ips:
                entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
                for entry in entries:
                   if entry["protocol"] == 'BGP (bgpaas)':
                     if int(entry['as_path']) == autonomous_system:
                        self.logger.info("as_path is not set correctly: as_path: %s vm as: %s "%(entry['as_path'],autonomous_system))
                     else:
                        assert False , "as_path is not set correctly: as_path: %s vm as: %s "%(entry['as_path'],autonomous_system)
                        break

    @preposttest_wrapper
    def test_bgpaas_vsrx_ipv4_mapped_ipv6_nexthop(self):
        """
        Description: Validate ipv4_mapped_ipv6_nexthop flag
        Test Steps:
           1. Advertise Ipv6 route from vsrx1.Verify vsrx2 dont receive ipv6 routes by default.
           2. Enable ipv4_mapped_ipv6_nexthop and verify vsrx2 receive ipv6 routes
              verify ipv4 mapped ipv6 nexthop on the received route.
           3. Disable ipv4_mapped_ipv6_nexthop and verify vsrx2 dont receive ipv6 routes
        Maintainer: vageesant@juniper.net    
        """
        
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='vsrx')
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',
                                    image_name='vsrx')
        assert test_vm.wait_till_vm_is_up()

        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"
        for i in range(5):
            bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
            if bgpaas_vm2_state:
               break
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up"

        autonomous_system1 = 63500
        autonomous_system2 = 64500

        bgpaas_fixture1 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=autonomous_system1, bgpaas_ip_address=bgpaas_vm1.vm_ip)
        bgpaas_fixture2 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=autonomous_system2, bgpaas_ip_address=bgpaas_vm2.vm_ip)
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]

        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system1, neighbors=neighbors, bfd_enabled=False)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm2, bgp_ip=bgpaas_vm2.vm_ip, lo_ip=bgpaas_vm2.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system2, neighbors=neighbors, bfd_enabled=False)
        self.logger.info('Will wait for both the vSRXs to come up')

        self.logger.info('Attaching both the VMIs to the BGPaaS object')
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture1)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture1)
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture2)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2, bgpaas_fixture2)

        ipv6_route = "2001:db8::1/128"
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm1,cmds=["set interfaces lo0 unit 0 family inet6 address %s"%ipv6_route])

        ret = bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        if ret:
            self.logger.info("bgpaas_vm1: BGPaaS Session not seen in the control-node")
        else:
            assert False, "bgpaas_vm1: BGPaaS Session not seen in the control-node"

        ret = bgpaas_fixture2.verify_in_control_node(bgpaas_vm2)
        if ret:
           self.logger.info("bgpaas_vm2: BGPaaS Session not seen in the control-node")
        else:
           assert False, "bgpaas_vm2: BGPaaS Session not seen in the control-node"

        advertised_routes = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route advertising-protocol bgp %s"%gw_ip)
        if re.search(ipv6_route,advertised_routes):
           self.logger.info("IPv6 route: %s is advertised from bgpaas_vm1"%ipv6_route)
        else:
           assert False,"IPv6 route : %s is not advertised from bgpaas_vm1"%ipv6_route

        received_routes = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s all"%gw_ip)
        if re.search(ipv6_route,received_routes):
           assert False,"IPv6 route is received by default without enabling IPv4 mapped IPv6 next-hop"
        else:
           self.logger.info("IPv6 route is not received by default , without enabling IPv4 mapped IPv6 next-hop,as expected")

        self.set_ipv4_mapped_ipv6_nexthop(bgpaas_fixture2,True)
        ret = self.get_ipv4_mapped_ipv6_nexthop(bgpaas_fixture2)
        if ret:
           self.logger.info("Use IPv4-mapped IPv6 Nexthop flag is set correctly in bgpaas_fixture2")
        else:
           assert False,"Use IPv4-mapped IPv6 Nexthop flag is NOT set correctly in bgpaas_fixture2"

        time.sleep(5)
        
        ret = bgpaas_fixture2.verify_in_control_node(bgpaas_vm2)
        if ret:
           self.logger.info("bgpaas_vm2: BGPaaS Session not seen in the control-node")
        else:
           assert False, 'bgpaas_vm2: BGPaaS Session not seen in the control-node'

        received_routes = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s all"%gw_ip)

        if re.search("%s\s+::ffff:%s"%(ipv6_route,gw_ip),received_routes):
           self.logger.info("IPv4-mapped IPv6 Nexthop is seen correctly")
        else:
           assert False,"IPv4-mapped IPv6 Nexthop is NOT seen.Expected route: %s\s+::ffff:%s"%(ipv6_route,gw_ip)

        self.set_ipv4_mapped_ipv6_nexthop(bgpaas_fixture2,False)
        ret = self.get_ipv4_mapped_ipv6_nexthop(bgpaas_fixture2)
        if not ret:
           self.logger.info("Use IPv4-mapped IPv6 Nexthop flag is re-set correctly in bgpaas_fixture2")
        else:
           assert False,"Use IPv4-mapped IPv6 Nexthop flag is NOT re-set correctly in bgpaas_fixture2"

        time.sleep(5)
        assert bgpaas_fixture2.verify_in_control_node(
            bgpaas_vm2), 'bgpaas_vm2: BGPaaS Session not seen in the control-node'

        received_routes = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s all"%gw_ip)

        if re.search("%s\s+::ffff:%s"%(ipv6_route,gw_ip),received_routes):
           assert False,"route: %s\s+::ffff:%s is seen when ipv4_mapped_ipv6_nexthop flag is reset"%(ipv6_route,gw_ip)
        else:
           self.logger.info("IPv4-mapped IPv6 Nexthop route is NOT seen as expected")


    @preposttest_wrapper
    def test_bgpaas_md5(self):
        """
        Description: Verify md5 for bgpaas bgp session
        Test Steps:
           1. Configure authentication method to md5 and configure key in bgpaas service
           2. Verify BGP session dont come up , when authentication key is not configured in vsrx.
           3. Configure authentication key on vsrx and verify BGP session comes up.
        Maintainer: vageesant@juniper.net
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')

        cluster_local_autonomous_system = random.randint(7000, 8000)
        bgpaas_as1 = random.randint(29000,30000)
        bgpaas_fixture1 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as1, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture1)

        assert test_vm.wait_till_vm_is_up(),"test_vm is not up"

        bgpaas_vm1_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state :
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up" 

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')

        self.set_md5_auth_data(bgpaas_fixture1,"juniper")

        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, 
                                bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=bgpaas_as1,
                                neighbors=neighbors,local_autonomous_system=cluster_local_autonomous_system)

        time.sleep(95)

        assert not bgpaas_fixture1.verify_in_control_node(bgpaas_vm1) , "BGP session should not be up as authentication key is not configured on vsrx"

        self.configure_vsrx(src_vm=test_vm,dst_vm=bgpaas_vm1,cmds = ["set protocols bgp authentication-key juniper"])

        time.sleep(95)

        assert bgpaas_fixture1.verify_in_control_node(bgpaas_vm1) , "BGP session is NOT up after configuring authentication key in vsrx"
 
    def bgpaas_as_loop_count(self,four_byte=False):

        if four_byte:
           initial_4byte_enable = self.get_4byte_enable()
           if initial_4byte_enable == False:
              self.set_4byte_enable(True)
              self.addCleanup(self.set_4byte_enable,initial_4byte_enable)
           cluster_local_autonomous_system = random.randint(70000, 80000)
           bgpaas_as1 = 645000
           bgpaas_as2 = 645010
        else:
           cluster_local_autonomous_system = random.randint(7000, 8000)
           bgpaas_as1 = 64500
           bgpaas_as2 = 64501

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',image_name='vsrx')

        bgpaas_fixture1 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as1, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)
        bgpaas_fixture2 = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as2, bgpaas_ip_address=bgpaas_vm2.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture1)
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture2)

        cn_inspect_handle = {}

        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        assert test_vm.wait_till_vm_is_up()
        assert bgpaas_vm1.wait_till_vm_is_up()
        bgpaas_vm2_state = False
        for i in range(5):
           bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
           if bgpaas_vm2_state:
              break
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up"

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')
        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]

        export_filter = [ "export filter bgp_out_uplink_a;",
                          """filter bgp_out_uplink_a
                             {
                             bgp_path.prepend(%s);
                             bgp_path.prepend(%s);
                             bgp_path.prepend(%s);
                             bgp_path.prepend(%s);
                             accept;
                             }
                          """ %(cluster_local_autonomous_system,cluster_local_autonomous_system,cluster_local_autonomous_system,bgpaas_as1)
                         ]

        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as1,static_routes=static_routes,export_filter_cmds=export_filter)

        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm2, 
                                bgp_ip=bgpaas_vm2.vm_ip, lo_ip=bgpaas_vm2.vm_ip,
                                address_families=address_families, autonomous_system=bgpaas_as2,
                                neighbors=neighbors,local_autonomous_system=cluster_local_autonomous_system)

        bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        bgpaas_fixture2.verify_in_control_node(bgpaas_vm2)
        output = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        if re.search("0.0.0.0/0",output):
           assert False,"ERROR: route 0.0.0.0/0 is seen in bgpaas_vm2 when there is as-path-loop"
        else:
           self.logger.info(" route 0.0.0.0/0 is NOT seen in bgpaas_vm2 when there is as-path-loop,as expected")

        as_path_looped = False
        for cn in self.inputs.bgp_control_ips:
           entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
           for entry in entries:
              if entry["protocol"] == 'BGP (bgpaas)' and "AsPathLooped" in entry["flags"]:
                as_path_looped = True

        if as_path_looped:
           self.logger.info("AsPathLooped detected for 0.0.0.0/0 , as expected")
        else:
           assert False,"AsPathLooped not seen for route 0.0.0.0/0"
 
        new_as_loop_count = 3
        self.set_as_loop_count(bgpaas_fixture1,new_as_loop_count)
        as_loop_count = self.get_as_loop_count(bgpaas_fixture1)
        assert as_loop_count == new_as_loop_count , "AS Loop Count is not updated correctly to 3"
        time.sleep(2)
        bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        output = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        if re.search("0.0.0.0/0",output):
           self.logger.info("route 0.0.0.0/0 is seen in bgpaas_vm2 after updating as loop count")
        else:
           assert False,"ERROR: route 0.0.0.0/0 is not seen in bgpaas_vm2 after updating as loop count"

        as_path_looped = False
        for cn in self.inputs.bgp_control_ips:
           entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
           for entry in entries:
               if entry["protocol"] == 'BGP (bgpaas)' and "AsPathLooped" in entry["flags"]:
                  as_path_looped = True
        assert not as_path_looped,"AsPathLooped seen for route 0.0.0.0/0 even after setting as_loop_count"

        new_as_loop_count = 1
        self.set_as_loop_count(bgpaas_fixture1,new_as_loop_count)
        as_loop_count = self.get_as_loop_count(bgpaas_fixture1)
        assert as_loop_count == new_as_loop_count , "AS Loop Count is not updated correctly to 1"
        time.sleep(2)
        bgpaas_fixture1.verify_in_control_node(bgpaas_vm1)
        output = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        as_path_looped = False
        for cn in self.inputs.bgp_control_ips:
           entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
           for entry in entries:
               if entry["protocol"] == 'BGP (bgpaas)' and "AsPathLooped" in entry["flags"]:
                  as_path_looped = True
        assert as_path_looped,"AsPathLooped NOT seen for route 0.0.0.0/0 even after re-setting as_loop_count"

        output = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        if re.search("0.0.0.0/0",output):
           assert False,"ERROR: route 0.0.0.0/0 is seen in bgpaas_vm2 after re-setting as loop count"

    @preposttest_wrapper
    def test_bgpaas_as_loop_count_2byte(self):
        """
        Description: Create AS_LOOP for 2 byte ASN and verify AsPathLooped is seen in VRF.
        Test Steps:
          1. From vsrx1 , advertise routes with clusters local asn number 2 times in AS_PATH.
             By default as-loop-count is 0 and hence route should be marked with AsPathLooped
             Verify AsPathLooped routes are not seen in vsrx2.
          2. Update as-loop-count to 3 and verify AsPathLooped is not seen in VRF
             Verify the route is seen in vsrx2.
          3. Update as-loop-count to 1 and Verify AsPathLooped is seen in VRF.
             verify the route is NOT seen in vsrx2
        Maintainer: vageesant@juniper.net
        """
        self.bgpaas_as_loop_count(four_byte=False)

    @preposttest_wrapper
    def test_bgpaas_as_loop_count_4byte(self):
        """
        Description: Create AS_LOOP for 4 byte ASN and verify AsPathLooped is seen in VRF.
        Test Steps:
          1. Enable 4Byte ASN in global configuration and set 4Byte ASN
          2. From vsrx1 , advertise routes with clusters local asn number 2 times in AS_PATH.
             By default as-loop-count is 0 and hence route should be marked with AsPathLooped
             Verify AsPathLooped routes are not seen in vsrx2.
          3. Update as-loop-count to 3 and verify AsPathLooped is not seen in VRF
             Verify the route is seen in vsrx2.
          4. Update as-loop-count to 1 and Verify AsPathLooped is seen in VRF.
             verify the route is NOT seen in vsrx2
        Maintainer: vageesant@juniper.net
        """
        self.bgpaas_as_loop_count(four_byte=True)

    @preposttest_wrapper
    def test_bgpaas_vsrx_as_override(self):
        """
        Description: Validate enable/disable as-override flag.
        Test Steps:
            1. Create 2 BGPaaS with same asn number.
            2. By default due to as-loop, routes from vsrx1 should not be seen in vsrx2.Verify this.
            3. Enable as-override flag in vsrx1 bgpaas service.
               This will make routes from vsrx1 to be advertised to vsrx2 with controller local-asn 
               replacing vsrx1's asn.
            4. Disable as-override flag and verify route from vsrx1 is not seen in vsrx2.
        """
 
        initial_4byte_enable = self.get_4byte_enable()
        if initial_4byte_enable == False:
           self.set_4byte_enable(True)
           self.addCleanup(self.set_4byte_enable,initial_4byte_enable)
       
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='vsrx')
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',
                                    image_name='vsrx')
        assert test_vm.wait_till_vm_is_up()

        autonomous_system = 645000
        cluster_local_autonomous_system = 655000
        bgpaas_fixture1 = self.create_bgpaas(bgpaas_shared=True,
             autonomous_system=autonomous_system, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)
        bgpaas_fixture2 = self.create_bgpaas(bgpaas_shared=True,
             autonomous_system=autonomous_system, bgpaas_ip_address=bgpaas_vm2.vm_ip,local_autonomous_system=cluster_local_autonomous_system) 
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up" 
        for i in range(5):
            bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
            if bgpaas_vm2_state:
              break
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up" 
        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors,local_autonomous_system=cluster_local_autonomous_system)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm2, bgp_ip=bgpaas_vm2.vm_ip, lo_ip=bgpaas_vm2.vm_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors,local_autonomous_system=cluster_local_autonomous_system)
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture1)
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture2)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture1)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2, bgpaas_fixture2)

        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm2,cmds=["set routing-options static route 0.0.0.0/0 discard"])

        assert bgpaas_fixture1.verify_in_control_node(
                bgpaas_vm1), 'BGPaaS Session for bgpaas_vm1 not seen in the control-node'

        assert bgpaas_fixture2.verify_in_control_node(
                bgpaas_vm2), 'BGPaaS Session for bgpaas_vm2 not seen in the control-node'

        output = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)

        ret = re.search("0.0.0.0/0",(output))
        if ret:
           self.logger.error("ERROR: STEP-1: route advertised by other BGPaasVM with same ASN is seen when as-override flag is not set")
           assert False
        else:
           self.logger.info("INFO: STEP-1: route advertised by other BGPaasVM with same ASN is NOT seen when as-override flag is not set,as expected")

        self.set_as_override(bgpaas_fixture1,True)
        assert self.get_as_override(bgpaas_fixture1),"bgpaas_fixture1: AS_Override flag is not updated to True"
      
        time.sleep(2)
        assert bgpaas_fixture1.verify_in_control_node(
                bgpaas_vm1), 'BGPaaS Session for bgpaas_vm1 not seen in the control-node'

        output = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)

        ret = re.search("0.0.0.0/0\s+%s\s+%s %s I"%(gw_ip,cluster_local_autonomous_system,cluster_local_autonomous_system),output)
        if ret:
           self.logger.info("STEP-2: INFO: route advertised by other BGPaasVM with same ASN is seen when as-override flag is set,as expected.")
        else:
           self.logger.error("STEP-2: ERROR: route advertised by other BGPaasVM with same ASN is NOT seen when as-override flag is set")
           assert False

        self.set_as_override(bgpaas_fixture1,False)
        assert not self.get_as_override(bgpaas_fixture1),"bgpaas_fixture1: AS_Override flag is not updated to False"

        time.sleep(2)
        assert bgpaas_fixture1.verify_in_control_node(
                bgpaas_vm1), 'BGPaaS Session for bgpaas_vm1 not seen in the control-node'

        output = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)
        ret = re.search("0.0.0.0/0",output)
        if ret:
           self.logger.error("ERROR: STEP-3: route advertised by other BGPaasVM with same ASN is seen when as-override flag is not set")
           assert False
        else:
           self.logger.info("INFO: STEP-3: route advertised by other BGPaasVM with same ASN is NOT seen when as-override flag is not set,as expected")

    @preposttest_wrapper
    def test_bgpaas_route_origin_override(self):
        """
        Description: Modify origin attribute for the routes from bgpaas VM to be IGP,EGP,INCOMPLETE
        Test steps:
             1. Configure bgpaas vm to advertise route 0.0.0.0/0.
                Verify route origin is advertised with default origin attribute as igp
             2. Enable origin-override and set origin to IGP. 
                Verify routes are seen with origin as igp in the vrf
             3. Enable origin-override and set origin to EGP
                verify routes seen with origin as egp in the vrf.
             4. Enable origin-override and set origin to INCOMPLETE
                verify routes seen with origin as incomplete in the vrf.
        Maintainer: vageesant@juniper.net
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='ubuntu-bird')
        assert bgpaas_vm1.wait_till_vm_is_up()

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(37000,38000)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the bird-vm')
        static_routes = [ {"network":"0.0.0.0/0","nexthop":"blackhole"}]
        
        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgpaas_vm1.vm_ip,
            neighbors=neighbors,
            peer_as=cluster_local_autonomous_system,
            local_as=bgpaas_as,static_routes=static_routes)
        bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        origin_from_bgpaas_vm = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  origin_from_bgpaas_vm = rt_entry["origin"]
        assert origin_from_bgpaas_vm == "igp","route 0.0.0.0/0 is not seen in ri: %s"%vn_fixture.ri_name
        self.logger.info("Unmodified Origin info for route 0.0.0.0/0 is : %s"%origin_from_bgpaas_vm)

        origin_override = self.get_route_origin_override(bgpaas_fixture)

        assert not origin_override,"ERROR: Origin Override is enabled by default"

        self.set_route_origin_override(bgpaas_fixture,True,"IGP")

        time.sleep(2)
        bgpaas_fixture.verify_in_control_node(bgpaas_vm1)

        origin_from_bgpaas_vm = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  origin_from_bgpaas_vm = rt_entry["origin"]

        assert origin_from_bgpaas_vm=="igp","route 0.0.0.0/0 is not seen in ri: %s"%vn_fixture.ri_name
        self.logger.info("Origin info for route 0.0.0.0/0 is : %s"%origin_from_bgpaas_vm)
       
        self.set_route_origin_override(bgpaas_fixture,True,"EGP")
        time.sleep(2)
        bgpaas_fixture.verify_in_control_node(bgpaas_vm1)

        origin_override = self.get_route_origin_override(bgpaas_fixture)
        origin = origin_override.get_origin() if origin_override else None
        if origin_override and origin == "EGP":
           origin_override_set = True
        else:
           origin_override_set = False
        assert origin_override_set,"Origin Override is not set correctly,Expected: True,EGP"

        origin_from_bgpaas_vm = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  origin_from_bgpaas_vm = rt_entry["origin"]
        assert origin_from_bgpaas_vm == "egp","route 0.0.0.0/0 is not seen in ri: %s"%vn_fixture.ri_name
        self.logger.info("Origin info for route 0.0.0.0/0 is : %s"%origin_from_bgpaas_vm)

        self.set_route_origin_override(bgpaas_fixture,True,"INCOMPLETE")
        time.sleep(5)
        bgpaas_fixture.verify_in_control_node(bgpaas_vm1)

        origin_override = self.get_route_origin_override(bgpaas_fixture)
        origin = origin_override.get_origin() if origin_override else None
        if origin_override and origin == "INCOMPLETE":
           origin_override_set = True
        else:
           origin_override_set = False

        assert origin_override_set,"Origin Override is not set correctly,Expected: True,INCOMPLETE"

        origin_from_bgpaas_vm = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  origin_from_bgpaas_vm = rt_entry["origin"]
        assert origin_from_bgpaas_vm=="incomplete","route 0.0.0.0/0 is not seen in ri: %s"%vn_fixture.ri_name
        self.logger.info("Origin info for route 0.0.0.0/0 is : %s"%origin_from_bgpaas_vm)

        self.set_route_origin_override(bgpaas_fixture,False,None)
        time.sleep(5)
        bgpaas_fixture.verify_in_control_node(bgpaas_vm1)

        origin_from_bgpaas_vm = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="0.0.0.0/0",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  origin_from_bgpaas_vm = rt_entry["origin"]
       
        assert origin_from_bgpaas_vm=="igp","route 0.0.0.0/0 is not seen in ri: %s"%vn_fixture.ri_name
        self.logger.info("Origin info for route 0.0.0.0/0 is : %s"%origin_from_bgpaas_vm)

    @preposttest_wrapper
    def test_bgpaas_vsrx_bfd_suppress_route_advt(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch vSRXs which will act as the clients. 
        3. Run VRRP among them. 
        4. The VRRP master will claim the BGP Source Address of the BGPaaS object. 
        5. Configure bfd and verify.

        Suppress route-advt:
           1. Enable suppress-route-advt and verify test_vm is not advertised to vsrx.
           2. Disable suppress-route-advt and verify test_vm is advertised to vsrx.
	Maintainer: vageesant@juniper.net
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='vsrx')
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',
                                    image_name='vsrx')
        assert test_vm.wait_till_vm_is_up()

        autonomous_system = random.randint(30000,31000)
        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(3):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"
        for i in range(3):
            bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
            if bgpaas_vm2_state:
               break
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up"

        bgp_ip = get_an_ip(vn_subnets[0], offset=10)
        bfd_enabled = True
        lo_ip = get_an_ip(vn_subnets[0], offset=15)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=autonomous_system, bgpaas_ip_address=bgp_ip)
        self.logger.info('Configure two ports and configure AAP between them')
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        port_list = [port1, port2]
        for port in port_list:
            self.config_aap(port, bgp_ip, mac='00:00:5e:00:01:01')
        self.logger.info('We will configure VRRP on the two vSRX')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm1, vip=bgp_ip, priority='200', interface='ge-0/0/0')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm2, vip=bgp_ip, priority='100', interface='ge-0/0/0')
        self.logger.info('Will wait for both the vSRXs to come up')

        assert self.vrrp_mas_chk(
            src_vm=test_vm, dst_vm=bgpaas_vm1, vn=vn_fixture, ip=bgp_ip, vsrx=True)
        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgp_ip, lo_ip=lo_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=True)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm2, bgp_ip=bgp_ip, lo_ip=lo_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=True)
        self.logger.info('Will wait for both the vSRXs to come up')

        self.logger.info('Attaching both the VMIs to the BGPaaS object')
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture)
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2, bgpaas_fixture)

        session1 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1)
        session2 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm2)

        if session1 or session2 :
           self.logger.info("BGPaaS Session is seen in control-node")
        else:
           assert False,"BGPaaS Session is NOT seen in control-node"

        received_routes1 = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)
        received_routes2 = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        routes_received = False
        if re.search("inet.0",received_routes1) and re.search(test_vm.vm_ip,received_routes1):
            routes_received = True
        if re.search("inet.0",received_routes2) and re.search(test_vm.vm_ip,received_routes2):
            routes_received = True
       
        assert routes_received,"ERROR: Routes are NOT received by BGPaaS VM correctly"

        self.set_suppress_route_advt(bgpaas_fixture,True)
        assert self.get_suppress_route_advt(bgpaas_fixture),"suppress route enable is not updated"
        time.sleep(2)
        session1 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1)
        session2 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm2)

        if session1 or session2 :
           self.logger.info("BGPaaS Session is seen in control-node")
        else:
           assert False,"BGPaaS Session is NOT seen in control-node"

        received_routes1 = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)
        received_routes2 = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)

        routes_received = False
        if re.search("inet.0",received_routes1) and re.search(test_vm.vm_ip,received_routes1):
            routes_received = True
        if re.search("inet.0",received_routes2) and re.search(test_vm.vm_ip,received_routes2):
            routes_received = True

        assert not routes_received,"ERROR: Routes are received by BGPaaS VM when suppress-advt is enabled"

        self.set_suppress_route_advt(bgpaas_fixture,False)
        time.sleep(2)

        session1 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1)
        session2 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm2)

        if session1 or session2 :
           self.logger.info("BGPaaS Session is seen in control-node")
        else:
           assert False,"BGPaaS Session is NOT seen in control-node"

        assert not self.get_suppress_route_advt(bgpaas_fixture),"suppress route disable is not updated"

        received_routes1 = self.get_config_via_netconf(test_vm,bgpaas_vm1,"show route receive-protocol bgp %s"%gw_ip)
        received_routes2 = self.get_config_via_netconf(test_vm,bgpaas_vm2,"show route receive-protocol bgp %s"%gw_ip)
        routes_received = False
        if re.search("inet.0",received_routes1) and re.search(test_vm.vm_ip,received_routes1):
            routes_received = True
        if re.search("inet.0",received_routes2) and re.search(test_vm.vm_ip,received_routes2):
            routes_received = True

        assert routes_received,"ERROR: Routes are NOT received by BGPaaS VM when suppress-advt is disabled"

        if bfd_enabled:
            shc_fixture = self.create_hc(
                probe_type='BFD', http_url=bgp_ip, timeout=1, delay=1, max_retries=3)
            self.attach_shc_to_bgpaas(shc_fixture, bgpaas_fixture)
            self.addCleanup(self.detach_shc_from_bgpaas,
                            shc_fixture, bgpaas_fixture)
            agent = bgpaas_vm1.vm_node_ip
            shc_fixture.verify_in_agent(agent)
            assert self.verify_bfd_packets(
                bgpaas_vm1, vn_fixture), 'Multihop BFD packets not seen over the BGPaaS interface'
        # end test_bgpaas_vsrx

    @preposttest_wrapper
    def test_bgpaas_with_bfd_shc_attached_to_vmi(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch a VM which will act as the BGPaaS client.
        3. Configure BFDoVMI on it.
        4. Verify BGP and BFD sessions over it come up fine.
        Maintainer: ankitja@juniper.net
        '''
        self.bgpaas_basic_common(attach_to='vmi')
    # end test_bgpaas_with_bfd_shc_attached_to_vmi

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_bgpaas_basic(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch a VM which will act as the BGPaaS client. 
        3. Configure BFDoBGPaaS on it. 
        4. Verify BGP and BFD sessions over it come up fine.
        Maintainer: ganeshahv@juniper.net
        '''
        self.bgpaas_basic_common(attach_to='bgpaas')
    # end test_bgpaas_basic

    def bgpaas_basic_common(self, attach_to='bgpaas'):
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        bgpaas_vm = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='ubuntu-bird')
        assert bgpaas_vm.wait_till_vm_is_up()
        bgp_vm_port = bgpaas_vm.vmi_ids[bgpaas_vm.vn_fq_name]
        local_as = random.randint(29000,30000)
        local_as = 64500
        local_ip = bgpaas_vm.vm_ip
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        peer_as=self.connections.vnc_lib_fixture.get_global_asn()
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=local_as, bgpaas_ip_address=local_ip)
        self.logger.info('We will configure BGP on the VM')
        self.config_bgp_on_bird(bgpaas_vm, local_ip,local_as,neighbors, peer_as)
        self.logger.info('Attaching the VMI to the BGPaaS object')
        self.attach_vmi_to_bgpaas(bgp_vm_port, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        bgp_vm_port, bgpaas_fixture)
        shc_fixture = self.create_hc(
            probe_type='BFD', http_url=local_ip, timeout=1, delay=1, max_retries=3)
        if attach_to == 'bgpaas':
            self.attach_shc_to_bgpaas(shc_fixture, bgpaas_fixture)
            self.addCleanup(self.detach_shc_from_bgpaas,
                            shc_fixture, bgpaas_fixture)
        elif attach_to == 'vmi':
            self.attach_shc_to_vmi(shc_fixture, bgpaas_vm)
            self.addCleanup(self.detach_shc_from_vmi,
                            shc_fixture, bgpaas_vm)

        agent = bgpaas_vm.vm_node_ip
        shc_fixture.verify_in_agent(agent)
        assert bgpaas_fixture.verify_in_control_node(
            bgpaas_vm), 'BGPaaS Session not seen in the control-node'
        assert self.verify_bfd_packets(
            bgpaas_vm, vn_fixture), 'Multihop BFD packets not seen over the BGPaaS interface'
        op= bgpaas_vm.run_cmd_on_vm(cmds=['birdc show protocols bfd1'], as_sudo=True)
        assert 'up' in op['birdc show protocols bfd1'], 'BFD session not UP'

        # end bgpaas_basic_common
