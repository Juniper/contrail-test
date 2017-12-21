from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds


class TestBGPaaS(BaseBGPaaS):

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_bgpaas_basic(self):
        '''
        1. Create a BGPaaS object with shared attribute, IP address and ASN.
        2. Launch vSRXs which will act as the clients. 
        3. Run VRRP among them. 
        4. The VRRP master will claim the BGP Source Address of the BGPaaS object. 
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
        assert bgpaas_vm1.wait_till_vm_is_up()
        assert bgpaas_vm2.wait_till_vm_is_up()
        bgp_ip = get_an_ip(vn_subnets[0], offset=100)
        bfd_enabled = True
        lo_ip = get_an_ip(vn_subnets[0], offset=150)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=64500, bgpaas_ip_address=bgp_ip)
        self.logger.info('Configure two ports and configure AAP between them')
        port1 = {}
        port2 = {}
        port1['id'] = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2['id'] = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        port_list = [port1, port2]
        for port in port_list:
            self.config_aap(port, bgp_ip, mac='00:00:5e:00:01:01')
        self.logger.info('We will configure VRRP on the two vSRX')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm1, vip=bgp_ip, priority='200', interface='ge-0/0/0')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm2, vip=bgp_ip, priority='100', interface='ge-0/0/0')
        self.logger.info('Will wait for both the vSRXs to come up')
        bgpaas_vm1.wait_for_ssh_on_vm()
        bgpaas_vm2.wait_for_ssh_on_vm()
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
        bgpaas_vm1.wait_for_ssh_on_vm()
        bgpaas_vm2.wait_for_ssh_on_vm()
        self.logger.info('Attaching both the VMIs to the BGPaaS object')
        self.attach_vmi_to_bgpaas(port1['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1['id'], bgpaas_fixture)
        self.attach_vmi_to_bgpaas(port2['id'], bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2['id'], bgpaas_fixture)

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
            interface = bgpaas_vm1.tap_intf[vn_fixture.vn_fq_name]['name']
            username = self.inputs.host_data[bgpaas_vm1.vm_node_ip]['username']
            password = self.inputs.host_data[bgpaas_vm1.vm_node_ip]['password']
            ip = self.inputs.host_data[bgpaas_vm1.vm_node_ip]['host_ip']
            (session, pcap) = start_tcpdump_for_intf(ip, username, password, interface,
                                                     filters='-P out')  # to capture packets sent to the BGPaaS client
            time.sleep(5)
            stop_tcpdump_for_intf(session, pcap)
            result = search_in_pcap(session, pcap, '4784')
            assert result, 'Multihop BFD packets not seen over the BGPaaS interface'
        # end test_bgpaas_basic
