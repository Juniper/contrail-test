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
from vnc_api.gen.resource_xsd import RouteOriginOverride,BgpFamilyAttributes,BgpPrefixLimit,BGPaaServiceParametersType
from tcutils.control.cn_introspect_utils import ControlNodeInspect

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
            bgpaas_shared=False,
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

    def get_bgp_router_flap_count(self, bgpaas_fixture):

        bgp_router_uuid = self.vnc_lib.bgp_as_a_service_read(
            id=bgpaas_fixture.uuid).get_bgp_router_refs()[0]['uuid']
        bgp_router = self.vnc_lib.bgp_router_read(id=bgp_router_uuid)
        bgp_router_name = bgp_router.name

        flap_info = {}

        for entry1 in self.inputs.bgp_ips:
            self.cn_ispec = ControlNodeInspect(entry1)
            cn_bgp_entry = self.cn_ispec.get_cn_bgp_neigh_entry(encoding='BGP') or []

            if not cn_bgp_entry:
                result = False
                self.logger.error(
                    'Control Node %s does not have any BGP Peer' %
                    (entry1))
            else:
                for entry in cn_bgp_entry:
                    if entry['peer'] == bgp_router_name:
                        flap_info[entry1] = entry['flap_count']
                        self.logger.info(
                            'Node %s peering info:With Peer %s : %s peering is Current State is %s ' %
                            (entry['local_address'], bgp_router_name, entry['peer'], entry['state']))
        return flap_info 

    def create_bird_bgpaas(self):
        vn_name = get_random_name('bgpaas_vn')
        vm_name = get_random_name('bgpaas_vm1')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)

        bgpaas_vm1 = self.create_vm(vn_fixture, vm_name,image_name='ubuntu-bird')
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

        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")
        return bgpaas_fixture,bgpaas_vm1


    def config_bgp_on_bird(self, bgpaas_vm, local_ip,local_as, neighbors, peer_as, static_routes=[],export_filter_cmds="",hold_time=90):
        # Example: static_routes = [ {"network":"6.6.6.0/24","nexthop":"blackhole"} ]
        static_route_cmd = ""
        if static_routes:
           static_route_cmd += "protocol static {\n"
           for rt in static_routes:
               static_route_cmd += "route %s %s;\n"%(rt["network"],rt["nexthop"])
           static_route_cmd += "}\n"
        if not export_filter_cmds:
           export_filter = "export where source = RTS_STATIC;\n" 
           export_filter_fn = ""
        else:
           export_filter = export_filter_cmds[0]
           export_filter_fn = export_filter_cmds[1]
        neighbor_info_str = "neighbor %s as %s"%(neighbors[0],peer_as)
        neighbor_bfd_info_str = "neighbor %s local %s multihop on"%(neighbors[0],local_ip)

        self.logger.info('Configuring BGP on %s ' % bgpaas_vm.vm_name)
        bgp_info = {}
        bgp_info["local_ip"] = local_ip
        bgp_info["local_as"]         = local_as
        bgp_info["export_filter_fn"] = export_filter_fn
        bgp_info["export_filter"]    = export_filter
        bgp_info["neighbor_info_str"] = neighbor_info_str
        bgp_info["neighbor_bfd_info_str"] = neighbor_bfd_info_str
        bgp_info["hold_time"]             = hold_time
        bgp_info["static_route_fn"]       = static_route_cmd
        

        cmd = """cat > /etc/bird/bird.conf << EOS
router id {local_ip};
{export_filter_fn}
protocol bgp {{
        local as {local_as};
        {neighbor_info_str};
        {export_filter}
        multihop;
        hold time {hold_time};
        bfd on;
        source address {local_ip};
}}
protocol bfd {{
        {neighbor_bfd_info_str};
}}
{static_route_fn}
EOS
""".format(**bgp_info)

        bgpaas_vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        service_restart= "service bird restart"
        op=bgpaas_vm.run_cmd_on_vm(cmds=[service_restart], as_sudo=True)
    # end config_bgp_on_bird

    def set_route_origin_override(self,bgpaas_fixture,origin_override,origin):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        routeorigin=session_attr.get_route_origin_override()
        if not routeorigin :
           routeorigin = RouteOriginOverride()

        routeorigin.set_origin_override(True)
        routeorigin.set_origin(origin)
        session_attr.set_route_origin_override(routeorigin)
        bgpaas_obj.set_bgpaas_session_attributes(session_attr)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_route_origin_override(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        routeorigin=session_attr.get_route_origin_override()
        return routeorigin

    def set_suppress_route_advt(self,bgpaas_fixture,suppress):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        bgpaas_obj.set_bgpaas_suppress_route_advertisement(suppress)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_suppress_route_advt(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        return bgpaas_obj.get_bgpaas_suppress_route_advertisement()

    def set_as_override(self,bgpaas_fixture,as_override):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        session_attr.set_as_override(as_override)
        bgpaas_obj.set_bgpaas_session_attributes(session_attr)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_as_override(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        return session_attr.get_as_override()


    def get_as_loop_count(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        return session_attr.get_loop_count()


    def set_as_loop_count(self,bgpaas_fixture,loop_count):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        session_attr.set_loop_count(loop_count)
        bgpaas_obj.set_bgpaas_session_attributes(session_attr)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def set_md5_auth_data(self,bgpaas_fixture,auth_password):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        auth_data={'key_items': [ { 'key':auth_password,"key_id":0 } ], "key_type":"md5"}
        session_attr.set_auth_data(auth_data)
        bgpaas_obj.set_bgpaas_session_attributes(session_attr)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)


    def set_ipv4_mapped_ipv6_nexthop(self,bgpaas_fixture,value):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        bgpaas_obj.set_bgpaas_ipv4_mapped_ipv6_nexthop(value)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_ipv4_mapped_ipv6_nexthop(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        return bgpaas_obj.get_bgpaas_ipv4_mapped_ipv6_nexthop()

    def update_bgpaas_as(self,bgpaas_fixture,autonomous_system=None,local_autonomous_system=None):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        if autonomous_system:
           bgpaas_obj.set_autonomous_system(autonomous_system)
        if local_autonomous_system:
           session = bgpaas_obj.get_bgpaas_session_attributes()
           session.set_local_autonomous_system(local_autonomous_system)
           bgpaas_obj.set_bgpaas_session_attributes(session)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_4byte_enable(self):
        gsc_obj = self.connections.vnc_lib.global_system_config_read(
            fq_name=['default-global-system-config'])
        return gsc_obj.get_enable_4byte_as()

    def set_4byte_enable(self, state):
        if state in ['true','True',True]:
           state = True
        else:
           state = False
        self.logger.info("SET_4BYTE_ENABLE " + str(state ) )
        gsc_obj = self.connections.vnc_lib.global_system_config_read(
            fq_name=['default-global-system-config'])
        gsc_obj.set_enable_4byte_as(state)
        self.connections.vnc_lib.global_system_config_update(gsc_obj)

    def set_hold_time(self,bgpaas_fixture,value):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        session.set_hold_time(value)
        bgpaas_obj.set_bgpaas_session_attributes(session)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_hold_time(self,bgpaas_fixture):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        return int(session.get_hold_time())

    def set_addr_family_attr(self,bgpaas_fixture,addr_family,limit=0,idle_timeout=0,tunnel_encap_list=None):

        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        attr_list = session.get_family_attributes()
        if len(attr_list) == 0:
           attr = BgpFamilyAttributes()
           if tunnel_encap_list:
             attr.set_default_tunnel_encap(tunnel_encap_list)
           attr.set_address_family(addr_family)
           prefix_limit = BgpPrefixLimit()
           prefix_limit.set_idle_timeout(idle_timeout)
           prefix_limit.set_maximum(limit)
           attr.set_prefix_limit(prefix_limit)
           attr_list.append(attr)
        else:
          for attr in attr_list:
            if attr.get_address_family() == addr_family: # inet,inet6
               if tunnel_encap_list:
                  attr.set_default_tunnel_encap(tunnel_encap_list)
               prefix_limit = attr.get_prefix_limit()
               prefix_limit.set_maximum(limit)
               prefix_limit.set_idle_timeout(idle_timeout)
               break
        session.set_family_attributes(attr_list)
        bgpaas_obj.set_bgpaas_session_attributes(session)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def get_private_as_action(self,bgpaas_fixture,action):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        return session.get_private_as_action()

    def set_private_as_action(self,bgpaas_fixture,action):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixture.uuid)
        session = bgpaas_obj.get_bgpaas_session_attributes()
        session.set_private_as_action(action)
        bgpaas_obj.set_bgpaas_session_attributes(session)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)


    def get_global_service_port_range(self):
        gsc_obj = self.connections.vnc_lib.global_system_config_read(fq_name=['default-global-system-config'])
        bgpaas_parameters = gsc_obj.get_bgpaas_parameters()
        if not bgpaas_parameters:
           return 50000,50512
        else:
           return bgpaas_parameters.get_port_start(),bgpaas_parameters.get_port_end()  

    def set_global_service_port_range(self,port_start,port_end):
        gsc_obj = self.connections.vnc_lib.global_system_config_read(fq_name=['default-global-system-config'])
        bgpaas_params = gsc_obj.get_bgpaas_parameters()
        if not bgpaas_params:
           bgpaas_params = BGPaaServiceParametersType()
        if port_start:
           bgpaas_params.set_port_start(port_start)
        if port_end:
           bgpaas_params.set_port_end(port_end)
        
        gsc_obj.set_bgpaas_parameters(bgpaas_params)
        try:
          self.connections.vnc_lib.global_system_config_update(gsc_obj)
          return True
        except:
          return False

