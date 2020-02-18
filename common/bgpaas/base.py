from builtins import str
import test_v1
from bgpaas_fixture import BGPaaSFixture
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from tcutils.tcpdump_utils import *
from tcutils.util import get_random_name, retry
from contrailapi import ContrailVncApi
from common.base import GenericTestBase
from common.neutron.base import BaseNeutronTest
from common.svc_health_check.base import BaseHC


class BaseBGPaaS(BaseNeutronTest, BaseHC):

    @classmethod
    def setUpClass(cls):
        super(BaseBGPaaS, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h = cls.connections.quantum_h
        cls.orch = cls.connections.orch
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    def create_bgpaas(
            self,
            bgpaas_shared='false',
            autonomous_system='64512',
            bgpaas_ip_address=None,
            address_families=[
                'inet',
                'inet6'],
            verify=True,
            local_autonomous_system=''):
        '''
        Calls the BGPaaS Fixture to create the object
        '''
        bgpaas_fixture = self.useFixture(
            BGPaaSFixture(
                connections=self.connections,
                name=get_random_name(
                    self.project_name),
                bgpaas_shared=bgpaas_shared,
                autonomous_system=autonomous_system,
                bgpaas_ip_address=bgpaas_ip_address,
                address_families=address_families,
                local_autonomous_system=local_autonomous_system))
        if verify:
            bgpaas_fixture.verify_on_setup()
        return bgpaas_fixture
    # end create_bgpaas

    def config_bgp_on_vsrx(
            self,
            src_vm=None,
            dst_vm=None,
            bgp_ip=None,
            lo_ip=None,
            address_families=[],
            autonomous_system='64512',
            neighbors=[],
            bfd_enabled=True,
            local_autonomous_system='',
            peer_local=''):
        '''
        Pass VRRP config to the vSRX
        '''
        cmdList = []
        cmdList.extend(
            ('set routing-options router-id ' +
             str(lo_ip),
                'set routing-options autonomous-system ' +
                str(autonomous_system),
                'set protocols bgp group bgpaas local-address ' +
                str(bgp_ip)))
        for family in address_families:
            cmdList.append(
                'set protocols bgp group bgpaas family ' +
                str(family) +
                ' unicast')
        for neighbor in neighbors:
            cmdList.append(
                'set protocols bgp group bgpaas neighbor ' + str(neighbor))
        # cmdList.append('set protocols bgp group bgpaas peer-as ' +
        #               str(self.inputs.router_asn))
        if local_autonomous_system:
            cmdList.append(
                'set protocols bgp group bgpaas peer-as ' +
                str(local_autonomous_system))
        else:
            cmdList.append(
                'set protocols bgp group bgpaas peer-as ' + str(self.inputs.bgp_asn))
        if peer_local:
            cmdList.append(
                'set protocols bgp group bgpaas local-as ' +
                str(peer_local))
        if bfd_enabled:
            cmdList.extend(('set protocols bgp group bgpaas bfd-liveness-detection minimum-interval 1000',
                            'set protocols bgp group bgpaas bfd-liveness-detection multiplier 3',
                            'set protocols bgp group bgpaas bfd-liveness-detection session-mode multihop')),
        cmdList.extend(('set protocols bgp group bgpaas type external', 'set protocols bgp group bgpaas multihop', 'set protocols bgp group bgpaas export export-to-bgp',
                        'set protocols bgp group bgpaas hold-time 30', 'set policy-options policy-statement export-to-bgp term allow_local from protocol direct',
                        'set policy-options policy-statement export-to-bgp term allow_local from protocol local',
                        'set policy-options policy-statement export-to-bgp term allow_local from protocol static', 'set policy-options policy-statement export-to-bgp term allow_local then next-hop ' +
                        str(bgp_ip),
                        'set policy-options policy-statement export-to-bgp term allow_local then accept', 'set policy-options policy-statement export-to-bgp term deny_all then reject'	))
        cmd_string = (';').join(cmdList)
        assert self.set_config_via_netconf(src_vm, dst_vm, cmd_string, timeout=10,
                                           device='junos', hostkey_verify="False"), 'Could not configure BGP thru Netconf'

    def configure_vsrx(self,
                       srv_vm=None,
                       dst_vm=None,
                       cmds = []):
        cmd_string = (';').join(cmds)
        ret = self.set_config_via_netconf(srv_vm, dst_vm, cmd_string, timeout=10,
                                           device='junos', hostkey_verify="False")

    def config_2legs_on_vsrx(
            self,
            src_vm=None,
            dst_vm=None,
            bgp_left_ip=None,
            bgp_right_ip=None,
            address_families=[],
            autonomous_system='64512',
            left_neighbors=[],
            right_neighbors=[],
            left_local_autonomous_system='',
            right_local_autonomous_system='',
            peer_local_left='',
            peer_local_right=''):
        '''
        Configure 2 legs to the vSRX
        '''
        cmdList = []
        cmdList.extend(
            ('set routing-options autonomous-system ' +
             str(autonomous_system),
                'set protocols bgp group bgpaas local-address ' +
                str(bgp_left_ip)))
        for family in address_families:
            cmdList.append(
                'set protocols bgp group bgpaas family ' +
                str(family) +
                ' unicast')
        for neighbor in left_neighbors:
            cmdList.append(
                'set protocols bgp group bgpaas neighbor ' + str(neighbor))
        # cmdList.append('set protocols bgp group bgpaas peer-as ' +
        #               str(self.inputs.router_asn))
        cmdList.append(
            'set protocols bgp group bgpaas local-as ' +
            str(peer_local_left))
        cmdList.append(
            'set protocols bgp group bgpaas1 local-as ' +
            str(peer_local_right))
        if left_local_autonomous_system:
            cmdList.append(
                'set protocols bgp group bgpaas peer-as ' +
                str(left_local_autonomous_system))
        cmdList.append(
            'set protocols bgp group bgpaas1 local-address ' +
            str(bgp_right_ip))
        for family in address_families:
            cmdList.append(
                'set protocols bgp group bgpaas1 family ' +
                str(family) +
                ' unicast')
        for neighbor in right_neighbors:
            cmdList.append(
                'set protocols bgp group bgpaas1 neighbor ' + str(neighbor))

        if right_local_autonomous_system:
            cmdList.append(
                'set protocols bgp group bgpaas1 peer-as ' +
                str(right_local_autonomous_system))
        cmdList.append(
            'deactivate routing-instances left interface ge-0/0/1.0')
        cmdList.append('set protocols bgp group bgpaas type external')
        cmdList.append('set protocols bgp group bgpaas1 type external')
        cmdList.append('set protocols bgp group bgpaas multihop')
        cmdList.append('set protocols bgp group bgpaas1 multihop')
        cmdList.append('set protocols bgp group bgpaas hold-time 90')
        cmdList.append('set protocols bgp group bgpaas1 hold-time 90')
        cmdList.append('deactivate interfaces ge-0/0/1.0 family inet filter')
        cmd_string = (';').join(cmdList)
        assert self.set_config_via_netconf(src_vm, dst_vm, cmd_string, timeout=10,
                                           device='junos', hostkey_verify="False"), 'Could not configure BGP thru Netconf'

    def attach_vmi_to_bgpaas(self, vmi, bgpaas_fixture):
        '''
        Attach VMI to the BGPaaS object
        '''
        result = bgpaas_fixture.attach_vmi(vmi)
        return result

    def detach_vmi_from_bgpaas(self, vmi, bgpaas_fixture):
        '''
        Detach the VMI from the BGPaaS object
        '''
        result = bgpaas_fixture.detach_vmi(vmi)
        return result

    def attach_shc_to_bgpaas(self, shc, bgpaas_fixture):
        '''
        Attach the Health Check to the BGPaaS object
        '''
        result = bgpaas_fixture.attach_shc(shc.uuid)
        return result

    def detach_shc_from_bgpaas(self, shc, bgpaas_fixture):
        '''
        Detach the Health Check from the BGPaaS object
        '''
        result = bgpaas_fixture.detach_shc(shc.uuid)
        return result

    @retry(delay=5, tries=10)
    def verify_bfd_packets(self, vm, vn):
        interface = vm.tap_intf[vn.vn_fq_name]['name']
        username = self.inputs.host_data[vm.vm_node_ip]['username']
        password = self.inputs.host_data[vm.vm_node_ip]['password']
        ip = self.inputs.host_data[vm.vm_node_ip]['host_ip']
        (session, pcap) = start_tcpdump_for_intf(
            ip, username, password, interface)
        time.sleep(5)
        stop_tcpdump_for_intf(session, pcap)
        result = search_in_pcap(session, pcap, '4784')
        return result

    def config_bgp_on_bird(self, bgpaas_vm, local_ip, peer_ip, local_as, peer_as,static_routes=[]):
        # Example: static_routes = [ {"network":"6.6.6.0/24","nexthop":"blackhole"} ]
        static_route_cmd = ""
        if static_routes:
           static_route_cmd += "protocol static {\n"
           for rt in static_routes:
               static_route_cmd += "route %s %s;\n"%(rt["network"],rt["nexthop"])
           static_route_cmd += "}\n"
        self.logger.info('Configuring BGP on %s ' % bgpaas_vm.vm_name)
        cmd = '''cat > /etc/bird/bird.conf << EOS
router id %s;
protocol bgp {
        description "BGPaaS";
        local as %s;
        neighbor %s as %s;
        export where source = RTS_STATIC;
        multihop;
        hold time 90;
        bfd on;
        source address %s;      # What local address we use for the TCP connection
}
protocol bfd {
    neighbor %s local %s multihop on;
}
%s
EOS
'''%(local_ip, local_as, peer_ip, peer_as, local_ip, peer_ip, local_ip,static_route_cmd)
        bgpaas_vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        service_restart= "service bird restart"
        op=bgpaas_vm.run_cmd_on_vm(cmds=[service_restart], as_sudo=True)
    # end config_bgp_on_bird
    def set_admin_down(self,bgpaas_fixture,value):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        session.set_admin_down(value)
        bgpaas_obj.set_bgpaas_session_attributes(session)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)
        
    def get_admin_down(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        return session.get_admin_down()
