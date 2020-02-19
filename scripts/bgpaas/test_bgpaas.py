from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
import random
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds


class TestBGPaaS(BaseBGPaaS):
    @preposttest_wrapper
    def test_bgpaas_ipv6_prefix_limit_idle_timeout(self):

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
        neighbors = []
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
        bgpaas_as = 64500
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
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
            peer_ip=gw_ip,
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
            peer_ip=gw_ip,
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
    def test_bgpaas_bird(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch ubuntu-bird vm which will act as the clients. 
        3. Run VRRP among them. 
        4. The VRRP master will claim the BGP Source Address of the BGPaaS object. 
	Maintainer: vageesant@juniper.net
        '''
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        port1_obj = self.create_port(net_id=vn_fixture.vn_id)
        port2_obj = self.create_port(net_id=vn_fixture.vn_id)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                     image_name='ubuntu-bird',
                                     port_ids=[port1_obj['id']])
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',
                                     image_name='ubuntu-bird',
                                     port_ids=[port2_obj['id']])
        bgp_ip = get_an_ip(vn_subnets[0], offset=10)
        bfd_enabled = True
        lo_ip = get_an_ip(vn_subnets[0], offset=15)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgp_ip)
        self.logger.info('Configure two ports and configure AAP between them')
        port_list = [port1_obj, port2_obj]
        for port in port_list:
            self.config_aap(port['id'], bgp_ip, mac=port['mac_address'])

        assert test_vm.wait_till_vm_is_up()
        assert bgpaas_vm1.wait_till_vm_is_up()
        assert bgpaas_vm2.wait_till_vm_is_up()

        self.logger.info('We will configure VRRP on the two ubuntu-bird vm')
        self.config_vrrp(bgpaas_vm1, bgp_ip, '20')
        self.config_vrrp(bgpaas_vm2, bgp_ip, '10')
        
        assert self.vrrp_mas_chk(dst_vm=bgpaas_vm1, vn=vn_fixture, ip=bgp_ip)

        self.logger.info('Will wait for both the bird-vms to come up')
        bgpaas_vm1.wait_for_ssh_on_vm()
        bgpaas_vm2.wait_for_ssh_on_vm()
        address_families = []
        address_families = ['inet', 'inet6']
        autonomous_system = 64500
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the two bird')
        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm1,
            local_ip=bgp_ip,
            peer_ip=gw_ip,
            peer_as='64512',
            local_as=autonomous_system)
        self.config_bgp_on_bird(
            bgpaas_vm=bgpaas_vm2,
            local_ip=bgp_ip,
            peer_ip=gw_ip,
            peer_as='64512',
            local_as=autonomous_system)
        self.logger.info('Attaching both the VMIs to the BGPaaS object')
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture)
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2, bgpaas_fixture)

        if bfd_enabled:
            shc_fixture = self.create_hc(
                probe_type='BFD', http_url=bgp_ip, timeout=1, delay=1, max_retries=3)
            self.attach_shc_to_bgpaas(shc_fixture, bgpaas_fixture)
            self.addCleanup(self.detach_shc_from_bgpaas,
                            shc_fixture, bgpaas_fixture)
            agent = bgpaas_vm1.vm_node_ip
            shc_fixture.verify_in_agent(agent)
            assert bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
            assert self.verify_bfd_packets(
                bgpaas_vm1, vn_fixture), 'Multihop BFD packets not seen over the BGPaaS interface'
        # end test_bgpaas_vsrx


    @preposttest_wrapper
    def test_bgpaas_vsrx(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch vSRXs which will act as the clients. 
        3. Run VRRP among them. 
        4. The VRRP master will claim the BGP Source Address of the BGPaaS object. 
	Maintainer: ganeshahv@juniper.net
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

        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(3):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"
        for i in range(3):
            bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up"

        bgp_ip = get_an_ip(vn_subnets[0], offset=10)
        bfd_enabled = True
        lo_ip = get_an_ip(vn_subnets[0], offset=15)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgp_ip)
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
        autonomous_system = 64500
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = []
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

        if bfd_enabled:
            shc_fixture = self.create_hc(
                probe_type='BFD', http_url=bgp_ip, timeout=1, delay=1, max_retries=3)
            self.attach_shc_to_bgpaas(shc_fixture, bgpaas_fixture)
            self.addCleanup(self.detach_shc_from_bgpaas,
                            shc_fixture, bgpaas_fixture)
            agent = bgpaas_vm1.vm_node_ip
            shc_fixture.verify_in_agent(agent)
            assert bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1), 'BGPaaS Session not seen in the control-node'
            assert self.verify_bfd_packets(
                bgpaas_vm1, vn_fixture), 'Multihop BFD packets not seen over the BGPaaS interface'
        # end test_bgpaas_vsrx

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
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        bgpaas_vm = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='ubuntu-bird')
        assert bgpaas_vm.wait_till_vm_is_up()
        bgp_vm_port = bgpaas_vm.vmi_ids[bgpaas_vm.vn_fq_name]
        local_as = 65000
        local_ip = bgpaas_vm.vm_ip
        peer_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        peer_as=self.connections.vnc_lib_fixture.get_global_asn()
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=local_as, bgpaas_ip_address=local_ip)
        self.logger.info('We will configure BGP on the VM')
        self.config_bgp_on_bird(bgpaas_vm, local_ip, peer_ip, local_as, peer_as)
        self.logger.info('Attaching the VMI to the BGPaaS object')
        self.attach_vmi_to_bgpaas(bgp_vm_port, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        bgp_vm_port, bgpaas_fixture)
        shc_fixture = self.create_hc(
            probe_type='BFD', http_url=local_ip, timeout=1, delay=1, max_retries=3)
        self.attach_shc_to_bgpaas(shc_fixture, bgpaas_fixture)
        self.addCleanup(self.detach_shc_from_bgpaas,
                        shc_fixture, bgpaas_fixture)
        agent = bgpaas_vm.vm_node_ip
        shc_fixture.verify_in_agent(agent)
        assert bgpaas_fixture.verify_in_control_node(
            bgpaas_vm), 'BGPaaS Session not seen in the control-node'	
        assert self.verify_bfd_packets(
            bgpaas_vm, vn_fixture), 'Multihop BFD packets not seen over the BGPaaS interface'
        op= bgpaas_vm.run_cmd_on_vm(cmds=['birdc show protocols bfd1'], as_sudo=True)
        assert 'up' in op['birdc show protocols bfd1'], 'BFD session not UP'

        # end test_bgpaas_basic
