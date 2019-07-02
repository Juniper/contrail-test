import test_v1
from bgpaas_fixture import BGPaaSFixture
from vn_test import VNFixture
from vm_test import VMFixture
from control_node_zone import ControlNodeZoneFixture 
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
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.host_list = cls.connections.orch.get_hosts()
    # end setUpClass

    def create_bgpaas(
            self,
            bgpaas_shared=None,
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
                'set protocols bgp group bgpaas peer-as ' + str(self.inputs.router_asn))
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

    def config_bgp_on_bird(self, bgpaas_vm, local_ip, peer_ip, local_as, peer_as):
        self.logger.info('Configuring BGP on %s ' % bgpaas_vm.vm_name)
        cmd = '''cat > /etc/bird/bird.conf << EOS
router id %s;
protocol device {
        scan time 10;           # Scan interfaces every 10 seconds
}
protocol kernel {
#       learn;                  # Learn all alien routes from the kernel
        persist;                # Don't remove routes on bird shutdown
        scan time 20;           # Scan kernel routing table every 20 seconds
        import all;             # Default is import all
        export all;             # Default is export none
#       kernel table 5;         # Kernel table to synchronize with (default: main)
}
protocol direct {
    interface "eth*";
}
protocol bgp {
        description "BGPaaS";
        local as %s;
        neighbor %s as %s;
        multihop;
        export all;
        hold time 90;
        bfd on;
        source address %s;      # What local address we use for the TCP connection
}
protocol bfd {
    neighbor %s local %s multihop on;
}
EOS
'''%(local_ip, local_as, peer_ip, peer_as, local_ip, peer_ip, local_ip)
        bgpaas_vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        service_restart= "service bird restart"
        op=bgpaas_vm.run_cmd_on_vm(cmds=[service_restart], as_sudo=True)
    # end config_bgp_on_bird

    def create_control_node_zones(self,name):
        cnz_fixtures = []
        for zone_id in range(0,len(self.inputs.bgp_names)):
            zone_name = get_random_name(name)
            cnz_fixture = self.useFixture(ControlNodeZoneFixture(
                                       connections=self.connections,
                                       name=get_random_name(
                                                 self.project_name), 
                                       zone_name=zone_name))
            fq_name = [ "default-domain", "default-project", "ip-fabric", "__default__",self.inputs.bgp_names[zone_id]]
            cnz_fixture.add_zone_to_bgp_router(fq_name=fq_name)
            cnz_fixtures.append(cnz_fixture)
        return cnz_fixtures

    def update_control_node_zones(self,cnzs):
        for cnz in cnzs:
            cnz.remove_zone_from_bgp_routers()
        bgp_rtrs = len(self.inputs.bgp_names)
        for zone in range(0,bgp_rtrs):
            fq_name = [ "default-domain", "default-project", "ip-fabric", "__default__", self.inputs.bgp_names[bgp_rtrs-zone-1]]
            cnzs[zone].add_zone_to_bgp_router(fq_name=fq_name)

#    def update_control_node_zones(self,cnzs,reset=True,fq_names=None):
#         if reset is True:
#             for cnz in cnzs:
#                 cnz.remove_zone_from_bgp_routers()
#             bgp_rtrs = len(self.inputs.bgp_names)
#             for zone in range(0,bgp_rtrs):
#                 fq_name = [ "default-domain", "default-project", "ip-fabric", "__default__", self.inputs.bgp_names[bgp_rtrs-zone-1]]
#                 cnzs[zone].add_zone_to_bgp_router(fq_name=fq_name)
#        else :
#            for cnz in cnzs:
#                cnz.add_zone_to_bgp_router(fq_name=fq_name)



    def attach_zones_to_bgpaas(self,cnz_fixtures,bgpaas_fixture,**kwargs):
        self.zones =  [] 
        #kwargs['fq_name']= [ "default-domain", "admin", "bgpaas-scale-1.st0"] 
        fq_name = bgpaas_fixture.fq_name
        self.vnc_h.attach_zone_to_bgpaas(zone_id=cnz_fixtures[0].uuid,zone_attr='primary',fq_name=fq_name,**kwargs)
        self.vnc_h.attach_zone_to_bgpaas(zone_id=cnz_fixtures[1].uuid,zone_attr='secondary',fq_name=fq_name,**kwargs)
        bgpaas_fixture.update_zones_to_bgpaas(primary=cnz_fixtures[0],secondary=cnz_fixtures[1])
        self.addCleanup(self.vnc_h.detach_zone_from_bgpaas,zone_id=cnz_fixtures[0].uuid,fq_name=fq_name,**kwargs)
        self.addCleanup(self.vnc_h.detach_zone_from_bgpaas,zone_id=cnz_fixtures[1].uuid,fq_name=fq_name,**kwargs)

    def detach_zones_from_bgpaas(self,cnz_fixture,bgpaas_fixture):
        bgpaas_fixture.update_zones_to_bgpaas(primary=None,secondary=None)
        return self.vnc_h.detach_zone_from_bgpaas(zone_id=cnz_fixture.uuid,fq_name=bgpaas_fixture.fq_name)

    def create_and_attach_bgpaas(self,cnz_fixtures,vn,vms,local_as,vip):
        bgpaas_fixtures = []
        peer_ips = []
        cnt = 0
        bgpaas_fixtures.append(self.create_bgpaas(autonomous_system=local_as))
        self.attach_zones_to_bgpaas(cnz_fixtures,bgpaas_fixtures[0])
        self.logger.info('We will configure BGP on the VM')
        peer_ips.append(vn.get_subnets()[0]['gateway_ip'])
        peer_ips.append(vn.get_subnets()[0]['dns_server_address'])
        peer_as = self.connections.vnc_lib_fixture.get_global_asn()
        for vm in vms:
            self.config_bgp_on_bird(vm, vm.vm_ip, peer_ips[cnt], local_as, peer_as) 
            self.attach_vmi_to_bgpaas(vm.vmi_ids[vm.vn_fq_name], bgpaas_fixtures[0]) 
            self.logger.info('Attaching the VMI %s to the BGPaaS %s object'%
                                                   (vm.uuid , bgpaas_fixtures[0].uuid)) 
            self.addCleanup(self.detach_vmi_from_bgpaas,vm.vmi_ids[vm.vn_fq_name],
                                                                      bgpaas_fixtures[0])
        #    self.config_aap(vms[i].vmi_ids[vms[i].vn_fq_name], vip, 
        #                                       mac=vms[i].mac_addr[vms[i].vn_fq_name])
            vm.run_cmd_on_vm(cmds=['sudo ip addr add %s dev eth0'%vip], as_sudo=True)
            cnt = cnt+1
        return bgpaas_fixtures 

    def verify_bgpaas_in_control_nodes_and_agent(self,bgpaas_fixtures,vms,count):
        result = False
        for vm in vms:
            for bgpaas in bgpaas_fixtures: 
                if bgpaas.pri_zone is not None:
                    bgp_routers = [rtr.bgp_router_parameters.address for rtr in bgpaas.pri_zone.bgp_router_objs]
                    if bgpaas.verify_in_control_nodes(control_nodes=bgp_routers,peer_address=vm.vm_ip,count=count):
                        result = True
                    break
                if bgpaas.sec_zone is not None:
                    bgp_routers = [rtr.bgp_router_parameters.address for rtr in bgpaas.sec_zone.bgp_router_objs]
                    if bgpaas.verify_in_control_nodes(control_nodes=bgp_routers,peer_address=vm.vm_ip,count=count):
                        result = True
                    break 
            for bgpaas in bgpaas_fixtures: 
                if not self.verify_control_node_zones_in_agent(vm,bgpaas):
                    return False
        return True 

    def flap_bgpaas_peering(self,vms):
        for vm in vms:
            vm.run_cmd_on_vm(cmds=['service bird restart'],as_sudo=True) 
        return         
  
    def verify_control_node_zones_in_agent(self,vm,bgpaas):
        ''' http://<ip>:8085/Snh_ControlNodeZoneSandeshReq
            verify control node zones to bgp router
            [{'name': 'default-domain:default-project:ip-fabric:__default__:5b4s2', 
               'control_node_zone': 'default-global-system-config:test-zone-0', 
               ')ipv4_address_port': '5.5.5.129:179'}]'''
        cnz_host_dict = {}
        cnz_bgp_rtr = {}
        host = vm.vm_node_ip
        agent_hdl = self.connections.get_vrouter_agent_inspect_handle(host)
            #cnz_host_list.append(agent_hdl.get_control_node_zones_in_agent())
        cnz_host_dict[host] = agent_hdl.get_control_node_zones_in_agent()
        for cnz_key in cnz_host_dict.keys():
            for bgp_list in cnz_host_dict[cnz_key]:
                    for bgp_rtr in bgp_list['bgp_router_list']:
                        cnz_bgp_rtr[bgp_rtr['control_node_zone'].split(":")[1]] = \
                                                   bgp_rtr['name'].split(":")[4]
        if bgpaas.pri_zone.name not in cnz_bgp_rtr.keys():
            self.logger.error('primary zone %s is not present in agent %s '% \
                                         (bgpaas.pri_zone.name,cnz_bgp_rtr.keys()))
            return False

        if bgpaas.sec_zone.name not in cnz_bgp_rtr.keys():
            self.logger.error('secondary zone %s is not present in agent %s '% \
                                         (bgpaas.sec_zone.name,cnz_bgp_rtr.keys()))
            return False

        return True

