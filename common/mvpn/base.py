from common.vrouter.base import BaseVrouterTest
from builtins import str
from builtins import range
import re
from vnc_api.vnc_api import *
from common.device_connection import NetconfConnection
from common.gw_less_fwd.base import *
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
import random
from tcutils.tcpdump_utils import *
from tcutils.util import *
from netaddr import IPNetwork
import time

# MVPN specific configuration
MVPN_CONFIG = {
    'mvpn_enable': True,
}

# Multicast source is behind MX. Multicast source details
MX_CONFIG = {
    'name': 'umesh',
    'lo0': '1.1.1.1',                   # MX Loopback interface IP
    'mcast_subnet': '30.30.30.0/24',   # Multicast source address behind MX
    'intf' : 'ge-2/3/9'
}


class MVPNTestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(MVPNTestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def skip_tc_if_no_fabric_gw_config(self):
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


    def provision_gw_less_fwd_mcast_src(self):
        '''
            Provision gateway less forwading for multicast source.
            This is needed to launch a VM in ip-fabric network, to simulate
            multicast source as MX does not support ingress replication for mvpn
        '''

        # Ipam parameters
        ipam = {'count': 1,
                 'ipam1':{'ipam_type': 'dhcp',
                           'subnet_method': 'flat-subnet',
                           'subnet': {
                                'ip_prefix': '10.204.218.0',
                                'len': 24
                            },
                           'allocation_pool': {
                                    'start': '10.204.218.150',
                                    'end': '10.204.218.160',
                            },
                        },
                }

        # launching 1 a VM in "ip-fabric" network (i.e enable IP fabric
        # forwarding on the VN). This VM is used for sending multicast data
        # traffic through MPLS/GRE with label being exchanged in MVPN type-4
        # routes.

        # Setup flat subnet Ipam as per configuration
        self.ipam_obj = self.setup_ipam(ipam)

        # Provision underlay gateway
        self.provision_underlay_gw()


    def provision_mx(self, mx_ip):
        '''
            Provision MX as BGP peer for MVPN functionality.
            Configured a VRF and enabled necessary protocols for mvpn
            interop between MX and contrail. S-PMSI is also confifured on VRF.
            GRE dynamic tunnels are configured for MPLS/GRE.
        '''

        # Initializing list of command need to be configured in MX
        cmd = []

        # MX Loopback IP
        mx_lo0_ip = MX_CONFIG.get('lo0', '1.1.1.1')

        # Mcast src interface on MX
        mcast_subnet = MX_CONFIG.get('mcast_subnet', '30.30.30.0/24')
        mcast_src = get_an_ip(mcast_subnet, 1)

        # Controller IP
        ctrl_ip = self.inputs.bgp_ips[0]
        local_addr = list(self.inputs.dm_mx.values())[0]['control_ip']
        ce_int = MX_CONFIG.get('intf')


        # router asn
        asn = self.inputs.router_asn
        # MX configuration
        cmd.append('set groups mvpn interfaces lo0 unit 0 family inet address '+mx_lo0_ip+'/32')
        cmd.append('set groups mvpn interfaces lo0 unit 0 family mpls')
        cmd.append('set groups mvpn routing-options router-id '+mx_lo0_ip)
        cmd.append('set groups mvpn routing-options route-distinguisher-id '+mx_lo0_ip)
        cmd.append('set groups mvpn routing-options autonomous-system '+asn)
        cmd.append('set groups mvpn routing-options multicast ssm-groups 239.0.0.0/8')
        cmd.append('set groups mvpn routing-options dynamic-tunnels gre1 source-address '+mx_lo0_ip)
        cmd.append('set groups mvpn routing-options dynamic-tunnels gre1 gre')
        cmd.append('set groups mvpn routing-options dynamic-tunnels gre1 destination-networks 10.204.217.0/24')
        cmd.append('set groups mvpn routing-options dynamic-tunnels gre1 destination-networks 10.204.216.0/24')
        cmd.append('set groups mvpn routing-options dynamic-tunnels gre1 destination-networks 10.10.10.0/24')
        cmd.append('set groups mvpn protocols mpls interface all')
        cmd.append('set groups mvpn protocols bgp group mvpn type internal')
        cmd.append('set groups mvpn protocols bgp group mvpn local-address '+local_addr)
        cmd.append('set groups mvpn protocols bgp group mvpn family inet-vpn unicast')
        cmd.append('set groups mvpn protocols bgp group mvpn family inet6-vpn unicast')
        cmd.append('set groups mvpn protocols bgp group mvpn family evpn signaling')
        cmd.append('set groups mvpn protocols bgp group mvpn family inet-mvpn signaling')
        cmd.append('set groups mvpn protocols bgp group mvpn family route-target')
        cmd.append('set groups mvpn protocols bgp group mvpn mvpn-iana-rt-import')
        for ctrl_ip in self.inputs.bgp_control_ips:
            cmd.append('set groups mvpn protocols bgp group mvpn neighbor '+ctrl_ip)
        cmd.append('set groups mvpn routing-instances test instance-type vrf')
        cmd.append('set groups mvpn routing-instances test interface '+ce_int)
        cmd.append('set groups mvpn routing-instances test route-distinguisher '+mx_lo0_ip+':100')
        cmd.append('set groups mvpn routing-instances test provider-tunnel ingress-replication create-new-ucast-tunnel')
        cmd.append('set groups mvpn routing-instances test provider-tunnel ingress-replication label-switched-path label-switched-path-template default-template')
        cmd.append('set groups mvpn routing-instances test provider-tunnel selective group 239.0.0.0/8 source '+mcast_src+'/32 ingress-replication create-new-ucast-tunnel')
        cmd.append('set groups mvpn routing-instances test provider-tunnel selective group 239.0.0.0/8 source '+mcast_src+'/32 ingress-replication label-switched-path label-switched-path-template default-template')
        cmd.append('set groups mvpn routing-instances test vrf-target target:64510:1')
        cmd.append('set groups mvpn routing-instances test vrf-table-label')
        cmd.append('set groups mvpn routing-instances test routing-options multicast ssm-groups 239.0.0.0/8')
        cmd.append('set groups mvpn routing-instances test protocols mpls interface all')
        cmd.append('set groups mvpn routing-instances test protocols pim interface all mode sparse')
        cmd.append('set groups mvpn routing-instances test protocols mvpn mvpn-mode spt-only')
        cmd.append('set apply-groups mvpn')
        cmd.append('set interfaces '+ce_int+' unit 0 family inet address 30.30.30.2/24 arp 30.30.30.1 mac 4c:96:14:98:1f:22')

        mx_handle = NetconfConnection(host = mx_ip)
        mx_handle.connect()
        cli_output = mx_handle.config(stmts = cmd, timeout = 120)
        mx_handle.disconnect()
        assert (not('failed' in cli_output)), "Not able to push config to mx"
        self.addCleanup(self.cleanup_mx, mx_ip)
        time.sleep(30)

    # end configure_mx

    def cleanup_mx(self, mx_ip):
        '''
            Cleanup MX BGP peer for MVPN functionality.
        '''

        # Initializing list of command need to be configured in MX
        cmd = []

        # MX configuration
        cmd.append('delete groups mvpn')
        cmd.append('delete apply-groups mvpn')

        mx_handle = NetconfConnection(host = mx_ip)
        mx_handle.connect()
        cli_output = mx_handle.config(stmts = cmd, timeout = 120)
        mx_handle.disconnect()
        assert (not('failed' in cli_output)), "Not able to push config to mx"

    # end cleanup_mx



    def setup_vns(self, vn=None):
        '''
        Input vn format:
            vn = {'count':1,
                  'vn1':{'subnet':get_random_cidr(), 'asn':64510, 'target':1},
                 }
        '''
        vn_count = vn['count'] if vn else 1
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            if vn_id in vn:
                address_allocation_mode = vn[vn_id].get(
                    'address_allocation_mode', 'user-defined-subnet-only')
                if address_allocation_mode == "flat-subnet-only":
                    ipam_fq_name = vn[vn_id].get('ipam_fq_name', None)
                    vn_fixture = self.create_vn(
                        vn_name=vn_id,
                        address_allocation_mode = address_allocation_mode,
                        forwarding_mode ="l3",
                        ipam_fq_name = ipam_fq_name, option='contrail')
                    # Disable RPF check on Ip Fabric network. This is needed to
                    # simulate source behind MX. Now, one of the VM launched on
                    # IP fabric VN will send multicast source data traffic.
                    self.vnc_lib_fixture.set_rpf_mode(
                        vn_fixture.get_vn_fq_name(), 'disable')

                else:
                    vn_subnet = vn[vn_id].get('subnet',None)
                    asn = vn[vn_id].get('asn',None)
                    target= vn[vn_id].get('target',None)

                    vn_fixture = self.create_vn(vn_name=vn_id,
                                                vn_subnets=[vn_subnet],
                                                router_asn=asn,
                                                rt_number=target)

                ip_fabric = vn[vn_id].get('ip_fabric',False)
                if ip_fabric:
                    ip_fab_vn_obj = self.get_ip_fab_vn()
                    assert vn_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)

                igmp = vn[vn_id].get('igmp',False)
                if igmp:
                    vn_fixture.set_igmp_config(igmp_enable=igmp)
            else:
                vn_fixture = self.create_vn(vn_name=vn_id)
            vn_fixtures[vn_id] = vn_fixture

        return vn_fixtures


    def setup_mvpn(self, vn=None, vmi=None, vm=None, verify=True):
        '''
            Setup MVPN Configuration.

            Sets up MVPN configuration on global level

            Input parameters looks like:
                #VN parameters:
                vn = {'count':1,            # VN count
                     # VN Details
                    'vn1':{'subnet':'10.10.10.0/24', 'asn':64510, 'target':1},
                    }

                #VMI parameters:
                vmi = {'count':2, # VMI Count
                    'vmi1':{'vn': 'vn1'}, # VMI details
                    'vmi2':{'vn': 'vn1'}, # VMI details
                    }

                #VM parameters:
                vm = {'count':2, # VM Count
                    # VM Launch mode i.e distribute non-distribute, default
                    'launch_mode':'distribute',
                    'vm1':{'vn':['vn1'], 'vmi':['vmi1']}, # VM Details
                    'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # VM Details
                    }

        '''

        # MVPN parameters
        mvpn_config = MVPN_CONFIG
        mvpn_enable = mvpn_config.get('mvpn_enable', True)

        # Configuring mvpn at global level
        name = MX_CONFIG.get('name', 'umesh')
        ip = list(self.inputs.dm_mx.values())[0]['control_ip']
        asn = self.inputs.router_asn
        af = ["route-target", "inet-mvpn", "inet-vpn", "e-vpn", "inet6-vpn"]
        self.vnc_h.add_bgp_router('router', name, ip, asn, af)
        self.addCleanup(self.vnc_h.delete_bgp_router, name)

        # MX configuration
        ip = list(self.inputs.dm_mx.values())[0]['mgmt_ip']
        self.provision_mx(ip)

        # VNs creation
        vn_fixtures = self.setup_vns(vn)

        # VMIs creation
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)

        # VMs creation
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm,
                                     image_name='ubuntu-mcast')

        ret_dict = {
            'vmi_fixtures':vmi_fixtures,
            'vn_fixtures':vn_fixtures,
            'vm_fixtures':vm_fixtures,
        }
        return ret_dict

    @classmethod
    def tearDownClass(cls):
        super(MVPNTestBase, cls).tearDownClass()
    # end tearDownClass


class IGMPTestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(IGMPTestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def send_igmp_reports(self, vm_fixtures, traffic, igmp, **kwargs):
        '''
            Sends IGMP Reports from multiple receivers :
                mandatory args:
                    vm_fixtures: VM fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp   : IGMP Report details
        '''

        # Send IGMPv3 membership reports from multicast receivers
        for stream in list(traffic.values()):
            for rcvr in stream['rcvrs']:
                result = self.send_igmp_report(vm_fixtures[rcvr], igmp)

        return True

    def get_pmsi_details(self, route_type, src, maddr,  **kwargs):
        '''
            Get PMSI details on MVPN type-1 or type-4 routes
                mandatory args:
                    route_type  : Type of the MVPN route
                    src         : Multicast source ip
                    maddr       : Multicast group address
                returns pmsi tunnel label and tunnel id
        '''

        (pmsi_tunnel_label, pmsi_tunnel_id) = (0,'0.0.0.0')

        # MVPN Type-1 Route, PMSI is Inclusive PMSI
        if route_type == 1:
            ip = self.inputs.ext_routers[0][1]
            mvpn_route = "1-"+ip
            (pmsi_tunnel_label, pmsi_tunnel_id) = self.get_pmsi_info(mvpn_route)

        # Type-4 MVPN route, S-PMSI details
        elif route_type == 4:
            mx_ip = MX_CONFIG.get('lo0', '1.1.1.1')
            mvpn_route = "4-"+"3-"+mx_ip+".+"+","+src+","+maddr

            # Get pmsi info from bgp master mvpn table
            (pmsi_tunnel_label, pmsi_tunnel_id) = self.get_pmsi_info(mvpn_route)

        return (pmsi_tunnel_label, pmsi_tunnel_id)


    def verify_mvpn_routes(self, route_type, vm_fixtures=None, traffic=None,
                           igmp=None,  **kwargs):
        '''
            Verify MVPN routes at control node:
                mandatory args:
                    route_type  : Type of the MVPN route
                    vm_fixtures : VM Fixture details
                    traffic     : Multicast data traffic details
                    igmp        : IGMPv3 details
        '''

        result = True
        # Verify MVPN Type-1 Route by default
        if route_type == 1:
            ip = MX_CONFIG.get('lo0', '1.1.1.1')
            mvpn_route = "1-"+ip
            result = self.verify_mvpn_route(mvpn_route, expectation=True)

        # Verify other MVPN route types
        else:
            for stream in list(traffic.values()):
                for rcvr in stream['rcvrs']:
                    mx_ip = MX_CONFIG.get('lo0', '1.1.1.1')
                    if igmp['type'] == 0x22:
                        numgrp = igmp.get('numgrp', 1)
                        for record in range(numgrp):
                            record_name = "record"+str(record+1)
                            rtype = igmp[record_name]['rtype']
                            maddr = igmp[record_name]['maddr']
                            srcaddrs = igmp[record_name]['srcaddrs']
                            asn = self.inputs.router_asn

                            # rtype 1 is IGMPv3 include, rtype 2 is for
                            # IGMPv3 exclude.
                            if rtype == 1:
                                expectation = True
                            elif rtype == 6:
                                expectation = False

                            for srcaddr in srcaddrs:
                                if route_type == 7:
                                    mvpn_route = "7-"+mx_ip+".+"+asn+","+srcaddr+","+maddr
                                elif route_type == 3:
                                    mvpn_route = "3-"+mx_ip+".+"+","+srcaddr+","+maddr+","+mx_ip
                                elif route_type == 4:
                                    mvpn_route = "4-"+"3-"+mx_ip+".+"+","+srcaddr+","+maddr+","+mx_ip
                                elif route_type == 5:
                                    src_vm_fixture = vm_fixtures[stream['src']]
                                    compute_ip = src_vm_fixture.get_compute_host()
                                    mvpn_route = "5-"+compute_ip+".+"+","+src+","+maddr

                                # Verify MVPN routes in bgp master mvpn table
                                result = result & self.verify_mvpn_route(mvpn_route,
                                                    expectation=expectation)

                                if result:
                                    self.logger.info('MVPN route type: %s present at '\
                                                    'bgp.mvpn.0 table as EXPECTED' %(route_type))
                                else:
                                    self.logger.warn('MVPN route type: %s NOT present at '\
                                                    'bgp.mvpn.0 table. NOT EXPECTED' %(route_type))

                                # Verify MVPN routes in RI mvpn table
                                vn_fq_name = vm_fixtures[rcvr].vn_fq_name
                                vn_name = vn_fq_name.split(':')[-1]
                                ri_name = vn_fq_name + ':' + vn_name

                                # MVPN Type-7 route in custom VRF is shown as
                                # zero-rd as the source-root-rd and 0 as the
                                # root-as asn
                                if route_type == 7:
                                    mvpn_route = "7-"+".+"+srcaddr+","+maddr

                                  
                                if route_type == 4 and vn_name == 'vn2':
                                    self.logger.info('Since IGMP join is from VN1 , type 4 wont be there in VN2')
                                    expectation = False

                                # Verify MVPN routes in bgp VRF mvpn table
                                result = result & self.verify_mvpn_route(mvpn_route,
                                            ri_name=ri_name, expectation=expectation)
                                if result:
                                    self.logger.info('MVPN route type: %s present at '\
                                                    '%s.mvpn.0 table as EXPECTED' %(route_type, vn_name))
                                else:
                                    self.logger.warn('MVPN route type: %s NOT present at '\
                                                    '%s.mvpn.0 table. NOT EXPECTED' %(route_type, vn_name))


        return result

    def get_pmsi_info(self, mvpn_route, **kwargs):
        '''
            Get tunnel_lable and tunnel_id from PMSI
                mandatory args:
                    mvpn_route : MVPN route
        '''

        (pmsi_tunnel_label, pmsi_tunnel_id) = (0,'0.0.0.0')

        # Verify MVPN routes at control node
        for cn in self.inputs.bgp_ips:
            mvpn_table_entry = self.cn_inspect[cn].get_cn_mvpn_table()

            for mvpn_entry in mvpn_table_entry:
                if re.match(mvpn_route, mvpn_entry['prefix']):
                    pmsi_tunnel_label = self.get_pmsi_tunnel_label_mvpn_route(mvpn_entry)
                    pmsi_tunnel_id = self.get_pmsi_tunnel_id_mvpn_route(mvpn_entry)
                    self.logger.info('Pmsi Tunnel Label:%s, Pmsi Tunnel Id:%s bgpip:%s'
                                     % (pmsi_tunnel_label, pmsi_tunnel_id, cn))
                    return (pmsi_tunnel_label, pmsi_tunnel_id)

        return (pmsi_tunnel_label, pmsi_tunnel_id)


    def verify_mvpn_route(self, mvpn_route, ri_name=None, **kwargs):
        '''
            Verify MVPN routes at control node:
                mandatory args:
                    mvpn_route  : MVPN route
                    ri_name     : Name of the RI
                optional:
                    expectation : True/False, whether route should be present or not
        '''

        expectation = kwargs.get('expectation',True)

        # Verify MVPN routes at control node
        result = False
        temp = ri_name
        for cn in self.inputs.bgp_ips:
            ri_name = temp
            self.logger.info('In cn: %s ri is : %s' % (cn,ri_name))
            mvpn_table_entry = self.cn_inspect[cn].get_cn_mvpn_table(ri_name)
            if not ri_name:
                ri_name = 'bgp.mvpn.0'

            if expectation:
                for mvpn_entry in mvpn_table_entry:
                    if re.match(mvpn_route, mvpn_entry['prefix']):
                        result = True
                        self.logger.info('MVPN route: %s seen in the %s table '\
                                         'of the control node-%s as EXPECTED'
                                         % (mvpn_route, ri_name, cn))
                        origin = self.get_origin_mvpn_route(mvpn_entry)
                        protocol = self.get_protocol_mvpn_route(mvpn_entry)
                        source = self.get_source_mvpn_route(mvpn_entry)
                        pmsi_tunnel_label = self.get_pmsi_tunnel_label_mvpn_route(mvpn_entry)
                        pmsi_tunnel_type = self.get_pmsi_tunnel_type_mvpn_route(mvpn_entry)
                        pmsi_tunnel_id = self.get_pmsi_tunnel_id_mvpn_route(mvpn_entry)
                        self.logger.debug(
                            'Origin:%s, Protocol:%s, Source:%s, Pmsi Tunnel '\
                            'Label:%s, Pmsi Tunnel Type:%s, Pmsi Tunnel Id:%s' %
                            (origin, source, protocol, pmsi_tunnel_label,
                             pmsi_tunnel_type, pmsi_tunnel_id))
                        break
                if result == False:
                    self.logger.warn('MVPN route: %s not seen in the %s table '\
                                     'of the control nodes %s. NOT EXPECTED'
                                     % (mvpn_route, ri_name, cn))
            else:
                result = True
                for mvpn_entry in mvpn_table_entry:
                    if re.match(mvpn_route, mvpn_entry['prefix']):
                        result = False
                        self.logger.warn('MVPN route: %s seen in the %s table'\
                                         'of the control node-%s. NOT EXPECTED'
                                         % (mvpn_route, ri_name, cn))
                        break
                if result == True:
                    self.logger.info('MVPN route: %s not seen in the %s table'\
                                     'of the control nodes as EXPECTED'
                                     % (mvpn_route, ri_name))

        return result

    def get_origin_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get origin of MVPN route:
        '''
        return mvpn_entry['paths'][0]['origin']

    def get_protocol_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get protocol of MVPN route:
        '''
        return mvpn_entry['paths'][0]['protocol']


    def get_source_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get source of MVPN route:
        '''
        return mvpn_entry['paths'][0]['source']

    def get_pmsi_tunnel_label_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get PMSI Tunnel label of MVPN route:
        '''
        return mvpn_entry['paths'][0]['pmsi_tunnel']['ShowPmsiTunnel']['label']

    def get_pmsi_tunnel_type_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get PMSI Tunnel type of MVPN route:
        '''
        return mvpn_entry['paths'][0]['pmsi_tunnel']['ShowPmsiTunnel']['type']

    def get_pmsi_tunnel_id_mvpn_route(self, mvpn_entry, **kwargs):
        '''
            Get PMSI Tunnel ID of MVPN route:
        '''
        return mvpn_entry['paths'][0]['pmsi_tunnel']['ShowPmsiTunnel']['identifier']



    def verify_igmp_reports(self, vm_fixtures, traffic, igmp, **kwargs):
        '''
            Verify IGMP Reports at agent:
                mandatory args:
                    vm_fixtures : VM fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp : IGMP Report details
                optional args:
                     1. count: No. of reports
        '''


        # Verify IGMPv3 membership at agent
        # As IGMP report is sent from these receivers, entries should be present
        # in agent
        result = True
        for stream in list(traffic.values()):
            for rcvr in stream['rcvrs']:
                # Verifying IGMP report details in "ip-fabric" VRF at agent
                vrf_id = 1
                result = result & self.verify_igmp_report(vm_fixtures[rcvr],
                                    vrf_id, igmp, expectation=True)

                if result:
                    self.logger.info('IGMPv3 membership is correct at '\
                                     '"ip-fabric" VRF for mcast receivers')
                else:
                    self.logger.warn('IGMPv3 membership is incorrect at '\
                                     '"ip-fabric" VRF for mcast receivers')

                # Verifying IGMP report details in VM's VRF at agent
                compute_node_ip = vm_fixtures[rcvr].vm_node_ip
                vrf_id = list(vm_fixtures[rcvr].get_vrf_ids()[compute_node_ip].values())[0]
                result = result & self.verify_igmp_report(vm_fixtures[rcvr],
                                    vrf_id, igmp, expectation=True)

                if result:
                    self.logger.info('IGMPv3 membership is correct at '\
                                     'custom VRF for mcast receivers')
                else:
                    self.logger.warn('IGMPv3 membership is incorrect at '\
                                     'custom VRF for mcast receivers')

        # Verify IGMPv3 membership at agent
        # As IGMP report is not sent from these receivers, entries should
        # not be present in agent
        for stream in list(traffic.values()):
            for rcvr in stream['non_rcvrs']:
                # Verifying IGMP report details in "ip-fabric" VRF at agent
                vrf_id = 1
                result = result & self.verify_igmp_report(vm_fixtures[rcvr],
                                vrf_id, igmp, expectation=False)

                if result:
                    self.logger.info('IGMPv3 membership is correct at '\
                                     '"ip-fabric" VRF for mcast non-receivers')
                else:
                    self.logger.warn('IGMPv3 membership is incorrect at '\
                                     '"ip-fabric" VRF for mcast non-receivers')

                # Verifying IGMP report details in VM's VRF at agent
                compute_node_ip = vm_fixtures[rcvr].vm_node_ip
                vrf_id = list(vm_fixtures[rcvr].get_vrf_ids()[compute_node_ip].values())[0]
                result = result & self.verify_igmp_report(vm_fixtures[rcvr],
                                vrf_id, igmp, expectation=False)
                if result:
                    self.logger.info('IGMPv3 membership is correct at '\
                                     'custom VRF for mcast non-receivers')
                else:
                    self.logger.warn('IGMPv3 membership is incorrect at '\
                                     'custom  VRF for mcast non-receivers')


        return result

    def send_igmp_report(self, rcv_vm_fixture, igmp, **kwargs):
        '''
            Sends IGMP Report from VM :
                mandatory args:
                    rcv_vm_fixture: send IGMP Report from this VM
                    igmp : IGMP Report details
                optional args:
                     1. count: No. of reports
        '''

        # Get IGMP parameters
        igmpv3 = {}
        igmpv3gr = {}
        igmpv3['type'] = igmp.get('type', 0x11)
        num_of_grp_records = igmp.get('numgrp', 1)
        for record in range(num_of_grp_records):
            record_name = "record"+str(record+1)
            if record_name in igmp:
                rtype = igmp[record_name]['rtype']
                maddr = igmp[record_name]['maddr']
                srcaddrs = igmp[record_name]['srcaddrs']
                record = {'rtype':rtype,'maddr':maddr,'srcaddrs':srcaddrs}
                igmpv3gr[record_name] = record

        # IGMPv3 Membership report. This can be enhanced once IGMPv2/v1 support
        # comes
        if igmpv3['type'] == 0x22:
            igmpv3mr = {'numgrp':num_of_grp_records}

            scapy_obj = self._generate_igmp_traffic(rcv_vm_fixture,
                                                        igmpv3=igmpv3,
                                                        igmpv3mr=igmpv3mr,
                                                        igmpv3gr=igmpv3gr)

    def _generate_igmp_traffic(self, rcv_vm_fixture, **kwargs):
        '''
            Generate IGMPv3 joins/leaves from multicast receiver VMs
        '''

        params = {}
        ether = {'type': 0x0800}
        ip = {'src': str(rcv_vm_fixture.vm_ip)}
        params['ether'] = ether
        params['ip'] = ip
        params['igmp'] = kwargs.get('igmpv3',{})
        params['igmpv3mr'] = kwargs.get('igmpv3mr',{})
        params['igmpv3gr'] = kwargs.get('igmpv3gr',{})
        params['payload'] = "''"
        params['count'] = 10

        scapy_obj = ScapyTraffic(rcv_vm_fixture, **params)
        scapy_obj.start()
        return scapy_obj

    def verify_igmp_report(self, vm_fixture, vrf_id, igmp, expectation=True):
        '''
            Verify IGMP Report:
                mandatory args:
                    vm_fixture: IGMP Report from this VM
                optional args:
        '''

        result = True
        tap_intf = list(vm_fixture.tap_intf.values())[0]['name']
        compute_node_ip = vm_fixture.vm_node_ip
        num_of_grp_records = igmp.get('numgrp', 1)
        for record in range(num_of_grp_records):
            record_name = "record"+str(record+1)
            if record_name in igmp:
                rtype = igmp[record_name]['rtype']
                maddr = igmp[record_name]['maddr']
                srcaddrs = igmp[record_name]['srcaddrs']

                if expectation:
                    # rtype 1 is IGMPv3 include, rtype 2 is for
                    # IGMPv3 exclude.
                    if rtype == 1:
                        expectation = True
                    elif rtype == 6:
                        expectation = False

                for srcaddr in srcaddrs:
                    # Verifying IGMP report details in VM's VRF at agent
                    result = result & self.verify_igmp_at_agent(compute_node_ip,
                        vrf_id, tap_intf, maddr, srcaddr, expectation=expectation)

        return result

    def start_tcpdump_mcast_rcvrs(self, vm_fixtures, traffic, expectation=True):
        '''
            Verify IGMP Report:
                mandatory args:
                    vm_fixture: IGMP Report from this VM
                    traffic: Multicast data traffic source and receivers details
                optional args:
        '''
        session = {}
        pcap = {}

        # Start tcpdump on receivers and non receivers
        for stream in list(traffic.values()):
            #src_ip = vm_fixtures[stream['src']].vm_ip
            mcast_subnet = MX_CONFIG.get('mcast_subnet', '30.30.30.0/24')
            src_ip = get_an_ip(mcast_subnet, 1)
            dst_ip = stream['maddr']

            # Start the tcpdump on receivers
            for rcvr in stream['rcvrs']:
                filters = '\'(src host %s and dst host %s)\'' % (src_ip, dst_ip)
                session[rcvr], pcap[rcvr] = start_tcpdump_for_vm_intf(
                    self, vm_fixtures[rcvr], vm_fixtures[rcvr].vn_fq_name,
                    filters=filters)

            # Start the tcpdump on non receivers
            for rcvr in stream['non_rcvrs']:
                filters = '\'(src host %s and dst host %s)\'' % (src_ip, dst_ip)
                session[rcvr], pcap[rcvr] = start_tcpdump_for_vm_intf(
                    self, vm_fixtures[rcvr], vm_fixtures[rcvr].vn_fq_name,
                    filters=filters)


        return session, pcap
    def send_mcast_streams(self, vm_fixtures, traffic, **kwargs):
        '''
            Sends Multicast traffic from multiple senders:
                mandatory args:
                    vm_fixtures: VM fixture details
                    traffic: Multicast data traffic source and receivers details
        '''

        # Send Multicast Traffic
        for stream in list(traffic.values()):
            self.send_mcast_stream(vm_fixtures[stream['src']],
                maddr=stream['maddr'], count=stream['count'])
        return True

    def verify_mcast_streams(self, session, pcap, traffic, igmp, **kwargs):
        '''
            Verifies Multicast traffic as per traffic configuration
        '''

        # Verify Multicast Traffic on receivers. Incase, IGMPv3 exclude is sent
        # multicast data traffic should not receive on the receivers. Only
        # IGMPv3 include should receive multicast data traffic.
        for stream in list(traffic.values()):
            maddr_traffic = stream['maddr']
            for rcvr in stream['rcvrs']:
                exp_count = stream['count']
                if igmp['type'] == 0x22:
                    numgrp = igmp.get('numgrp', 1)
                    for record in range(numgrp):
                        record_name = "record"+str(record+1)
                        rtype = igmp[record_name]['rtype']
                        maddr_igmp = igmp[record_name]['maddr']
                        # Match mcast group in tarffic and igmp
                        if maddr_traffic == maddr_igmp:
                            # rtype 2 is for IGMPv3 exclude. Traffic should not
                            # be received.
                            if rtype == 6:
                                exp_count = 0
                            break

                verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
                                     exp_count=exp_count,
                                     grep_string="UDP")

        # Verify Multicast Traffic on non receivers, traffic should not reach
        # these
        for stream in list(traffic.values()):
            for rcvr in stream['non_rcvrs']:

                verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
                                     exp_count=0,
                                     grep_string="UDP")

        return True


    @retry(delay=2, tries=2)
    def verify_igmp_at_agent(self, compute_ip, vrf_id, tap_intf, grp_ip=None,
                             src_ip=None, expectation=True):
        '''
            Verify IGMP Report at agent
        '''
        mcast_route_in_agent = self.agent_inspect[compute_ip].get_vna_mcast_route(
            vrf_id=vrf_id, grp_ip=grp_ip, src_ip=src_ip)

        if expectation:
            if mcast_route_in_agent:
                src_present = mcast_route_in_agent['src']
                grp_present = mcast_route_in_agent['grp']
                for mc_list in mcast_route_in_agent['nh']['mc_list']:
                    try:
                        tap_intf_present = mc_list['itf']
                    except KeyError:
                        tap_intf_present = None

                    if src_ip == src_present and grp_ip == grp_present and tap_intf == tap_intf_present:
                        self.logger.info('IGMPv3 membership (S,G): (%s,%s) found '\
                                        'in agent: %s for tap:%s in vrf_id: %s as EXPECTED'
                                        % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
                        return True

            self.logger.warn('IGMPv3 membership (S,G): (%s,%s) NOT found in '\
                             'agent: %s for tap:%s in vrf_id: %s NOT EXPECTED'
                             % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
            return False
        else:
            if mcast_route_in_agent:
                src_present = mcast_route_in_agent['src']
                grp_present = mcast_route_in_agent['grp']
                for mc_list in mcast_route_in_agent['nh']['mc_list']:
                    try:
                        tap_intf_present = mc_list['itf']
                    except KeyError:
                        tap_intf_present = None

                    if src_ip == src_present and grp_ip == grp_present and tap_intf == tap_intf_present:
                        self.logger.warn('IGMPv3 membership (S,G): (%s,%s) found '\
                                            'in agent: %s for tap:%s in vrf_id: %s as NOT EXPECTED'
                                            % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
                        return False

            self.logger.info('IGMPv3 membership (S,G): (%s,%s) NOT found in '\
                             'agent: %s for tap:%s  in vrf_id: %s as EXPECTED'
                             % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
            return True



    def send_mcast_stream(self, src_vm_fixture, **kwargs):
        '''
            Sends Multicast traffic from VM src_vm_fixture:
                mandatory args:
                    src_vm_fixture: send multicast traffic from this VM
                optional args:
                     1. maddr: Multicast group to which traffic is sent
                     2. count: No. of packets
                     3. payload: upper layer packets
        '''

        maddr = kwargs.get('maddr', None)
        count = kwargs.get('count', 1)

        # Multicast source is behind MX
        mcast_subnet = MX_CONFIG.get('mcast_subnet', '30.30.30.0/24')
        src = get_an_ip(mcast_subnet, 1)

        # src_ip is MX IP
        mx_ip = MX_CONFIG.get('lo0', '1.1.1.1')

        # Get PMSI details i.e forest node ip and label used to send multicast
        # data traffic.
        route_type = 4
        (label, forest_node_ip) = self.get_pmsi_details(route_type, src, maddr)
        payload = kwargs.get('payload', "'*****This is default payload*****'")

        params = {}
        ether = {'type': 0x0800}

        outer_ip = {'src': mx_ip, 'dst':forest_node_ip, 'proto':47}
        inner_ip = {'src': src, 'dst':maddr}
        gre = {'proto': 0x8847}
        mpls = {'label': int(label), 'ttl':64}
        udp = {'sport':1500, 'dport':1501}

        params['ether'] = ether
        params['ip'] = outer_ip
        params['gre'] = gre
        params['mpls'] = mpls
        params['inner_ip'] = inner_ip
        params['inner_udp'] = udp
        params['count'] = count
        params['payload'] = payload

        scapy_obj = ScapyTraffic(src_vm_fixture, **params)
        scapy_obj.start()
        return scapy_obj


    def send_verify_mcast(self, vm_fixtures, traffic, igmp, **kwargs):
        '''
            Send and verify IGMP report and multicast traffic
                mandatory args:
                    vm_fixtures: vm_fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp: IGMP Report details
                optional args:
        '''

        # Send IGMP membership report from multiple receivers
        self.logger.info('Sending IGMPv3 report as per configuration')
        result = self.send_igmp_reports(vm_fixtures, traffic, igmp)

        if result:
            self.logger.info('Successfully sent IGMPv3 reports')
        else:
            assert result, "Error in sending IGMPv3 reports"



        # Verify IGMP membership reports at agent
        self.logger.info('Verifying IGMPv3 report as per configuration')
        result = self.verify_igmp_reports(vm_fixtures, traffic, igmp)

        if result:
            self.logger.info('Successfully validated IGMPv3 reports at agent')
        else:
            assert result, "Error in validating IGMPv3 reports at agent"

        # Verify MVPN routes (type-7) at control node
        self.logger.info('Verifying MVPN type-7 route generation from controller')
        route_type = 7
        result = self.verify_mvpn_routes(route_type, vm_fixtures, traffic, igmp)
        if result:
            self.logger.info('Successfully verified MVPN type-7 routes')
        else:
            assert result, "Error in verifying MVPN type-7 route"

        # Verify MVPN routes (type-3) at control node
        self.logger.info('Verifying MVPN type-3 route on controller')
        route_type = 3
        result = self.verify_mvpn_routes(route_type, vm_fixtures, traffic, igmp)
        if result:
            self.logger.info('Successfully verified MVPN type-3 routes')
        else:
            assert result, "Error in verifying MVPN type-3 route"

        # Verify MVPN routes (type-4) at control node
        self.logger.info('Verifying MVPN type-4 route generation from controller')
        route_type = 4
        result = self.verify_mvpn_routes(route_type, vm_fixtures, traffic, igmp)

        if result:
            self.logger.info('Successfully verified MVPN type-4 routes')
        else:
            assert result, "Error in verifying MVPN type-4 route"

        # Start tcpdump on receivers
        self.logger.info('Starting tcpdump on mcast receivers')
        session, pcap = self.start_tcpdump_mcast_rcvrs(vm_fixtures, traffic)

        # Send multicast traffic
        time.sleep(5)
        self.logger.info('Sending mcast data traffic from mcast source')
        result = self.send_mcast_streams(vm_fixtures, traffic)
        time.sleep(10)
        time.sleep(10)

        if result:
            self.logger.info('Successfully sent multicast data traffic')
        else:
            assert result, "Error in sending multicast data traffic"

        # Verify MVPN routes (type-5) at control node
        #route_type = 5
        #result = self.verify_mvpn_routes(route_type, vm_fixtures, traffic, igmp)

        # Verify multicast traffic
        self.logger.info('Verifying mcast data traffic on mcast receivers')
        result = self.verify_mcast_streams(session, pcap, traffic, igmp)




        if result:
            self.logger.info('Successfully verified multicast data traffic on all receivers')
        else:
            assert result, "Error in verifying multicast data traffic on all receivers"
        return result

    @classmethod
    def tearDownClass(cls):
        super(IGMPTestBase, cls).tearDownClass()
    # end tearDownClass



class MVPNTestSingleVNSingleComputeBase(MVPNTestBase, IGMPTestBase, GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(MVPNTestSingleVNSingleComputeBase, cls).setUpClass()
        cls.inputs.set_af(cls.get_af())

    def bringup_mvpn_setup(self, vn=None, vmi=None, vm=None):
        '''
            Bringup mvpn setup such that both multicast source and
            receivers are part of a single VN. Also, source and receivers are
            part of same compute.But, source and receivers are
            part of different computes
        '''

        # Validate whether test is applible or not
        self.skip_tc_if_no_fabric_gw_config()

        # Configure MVPN at control node. Right now, there is no VNC API. Need
        # to update entrypoint.sh file and restart control docker
        for node_ip in self.inputs.cfgm_ips:
            self.inputs.add_knob_to_container(node_ip, 'control_control_1', 'DEFAULT', 'mvpn_ipv4_enable=1')

        # Gateway less forward provision for multicast source simulation
        self.provision_gw_less_fwd_mcast_src()

        # VN parameters
        vn = {'count':2,
            'vn1':{'subnet':get_random_cidr(), 'asn':64510, 'target':1, 'igmp':True},
            'vn2':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': self.ipam_obj.fq_name,
                    },
            }

        # VMI parameters
        vmi = {'count':3,
            'vmi1':{'vn': 'vn2'},
            'vmi2':{'vn': 'vn1'},
            'vmi3':{'vn': 'vn1'},
            }

        # VM parameters
        vm = {'count':3, 'launch_mode':'non-distribute',
            'vm1':{'vn':['vn2'], 'vmi':['vmi1']}, # Mcast source
            'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # Mcast receiver
            'vm3':{'vn':['vn1'], 'vmi':['vmi3']}, # Mcast receiver
            }

        ret_dict = self.setup_mvpn(vn=vn, vmi=vmi, vm=vm)
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        return ret_dict

    @classmethod
    def tearDownClass(cls):
        super(MVPNTestSingleVNSingleComputeBase, cls).tearDownClass()
    # end tearDownClass


class MVPNTestSingleVNMultiComputeBase(MVPNTestBase, IGMPTestBase, GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(MVPNTestSingleVNMultiComputeBase, cls).setUpClass()
        cls.inputs.set_af(cls.get_af())

    def bringup_mvpn_setup(self):
        '''
            Bringup mvpn setup such that both multicast source and
            receivers are part of a single VN. But, source and receivers are
            part of different computes
        '''

        # Validate whether test is applible or not
        self.skip_tc_if_no_fabric_gw_config()

        # Configure MVPN at control node. Right now, there is no VNC API. Need
        # to update entrypoint.sh file and restart control docker
        for node_ip in self.inputs.cfgm_ips:
            self.inputs.add_knob_to_container(node_ip, 'control_control_1', 'DEFAULT', 'mvpn_ipv4_enable=1')

        # Gateway less forward provision for multicast source simulation
        self.provision_gw_less_fwd_mcast_src()

        # VN parameters
        vn = {'count':2,
            'vn1':{'subnet':get_random_cidr(), 'asn':64510, 'target':1 ,'igmp':True},
            'vn2':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': self.ipam_obj.fq_name,
                    },
            }

        # VMI parameters
        vmi = {'count':4,
            'vmi1':{'vn': 'vn2'},
            'vmi2':{'vn': 'vn1'},
            'vmi3':{'vn': 'vn1'},
            'vmi4':{'vn': 'vn1'},
            }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
            'vm1':{'vn':['vn2'], 'vmi':['vmi1']}, # Mcast source
            'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # Mcast receiver
            'vm3':{'vn':['vn1'], 'vmi':['vmi3']}, # Mcast receiver
            'vm4':{'vn':['vn1'], 'vmi':['vmi4']}, # Mcast receiver
            }

        ret_dict = self.setup_mvpn(vn=vn, vmi=vmi, vm=vm)
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        return ret_dict

    @classmethod
    def tearDownClass(cls):
        super(MVPNTestSingleVNMultiComputeBase, cls).tearDownClass()
    # end tearDownClass

class MVPNTestMultiVNSingleComputeBase(MVPNTestBase, IGMPTestBase, GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(MVPNTestMultiVNSingleComputeBase, cls).setUpClass()
        cls.inputs.set_af(cls.get_af())

    def bringup_mvpn_setup(self):
        '''
            Bringup mvpn setup such that both multicast source and
            receivers are part of a multiple VNs. But, source and receivers are
            part of same compute
        '''

        # Validate whether test is applible or not
        self.skip_tc_if_no_fabric_gw_config()

        # Configure MVPN at control node. Right now, there is no VNC API. Need
        # to update entrypoint.sh file and restart control docker
        for node_ip in self.inputs.cfgm_ips:
            self.inputs.add_knob_to_container(node_ip, 'control_control_1', 'DEFAULT', 'mvpn_ipv4_enable=1')

        # Gateway less forward provision for multicast source simulation
        self.provision_gw_less_fwd_mcast_src()

        # VN parameters
        vn = {'count':3,
            'vn1':{'subnet':get_random_cidr(), 'asn':64510, 'target':1, 'igmp':True},
            'vn2':{'subnet':get_random_cidr(), 'asn':64520, 'target':1, 'igmp':True},
            'vn3':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': self.ipam_obj.fq_name,
                    },
            }

        # VMI parameters
        vmi = {'count':4,
            'vmi1':{'vn': 'vn3'},
            'vmi2':{'vn': 'vn1'},
            'vmi3':{'vn': 'vn2'},
            'vmi4':{'vn': 'vn2'},
            }

        # VM parameters
        vm = {'count':4, 'launch_mode':'non-distribute',
            'vm1':{'vn':['vn3'], 'vmi':['vmi1']}, # Mcast source
            'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # Mcast receiver
            'vm3':{'vn':['vn2'], 'vmi':['vmi3']}, # Mcast receiver
            'vm4':{'vn':['vn2'], 'vmi':['vmi4']}, # Mcast receiver
            }

        ret_dict = self.setup_mvpn(vn=vn, vmi=vmi, vm=vm)
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  }


        # Configure policy between vn1 and vn2
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures


        return ret_dict

    @classmethod
    def tearDownClass(cls):
        super(MVPNTestMultiVNSingleComputeBase, cls).tearDownClass()
    # end tearDownClass

class MVPNTestMultiVNMultiComputeBase(MVPNTestBase, IGMPTestBase, GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(MVPNTestMultiVNMultiComputeBase, cls).setUpClass()
        cls.inputs.set_af(cls.get_af())

    def bringup_mvpn_setup(self):
        '''
            Bringup mvpn setup such that both multicast source and
            receivers are part of a multiple VNs. But, source and receivers are
            part of multiple computes
        '''
        # Validate whether test is applible or not
        self.skip_tc_if_no_fabric_gw_config()

        # Configure MVPN at control node. Right now, there is no VNC API. Need
        # to update entrypoint.sh file and restart control docker
        for node_ip in self.inputs.cfgm_ips:
            self.inputs.add_knob_to_container(node_ip, 'control_control_1', 'DEFAULT', 'mvpn_ipv4_enable=1')

        # Gateway less forward provision for multicast source simulation
        self.provision_gw_less_fwd_mcast_src()

        # VN parameters
        vn = {'count':3,
            'vn1':{'subnet':get_random_cidr(), 'asn':64510, 'target':1, 'igmp':True},
            'vn2':{'subnet':get_random_cidr(), 'asn':64520, 'target':1, 'igmp':True},
            'vn3':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': self.ipam_obj.fq_name,
                    },
            }

        # VMI parameters
        vmi = {'count':4,
            'vmi1':{'vn': 'vn3'},
            'vmi2':{'vn': 'vn1'},
            'vmi3':{'vn': 'vn2'},
            'vmi4':{'vn': 'vn2'},
            }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
            'vm1':{'vn':['vn3'], 'vmi':['vmi1']}, # Mcast source
            'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # Mcast receiver
            'vm3':{'vn':['vn2'], 'vmi':['vmi3']}, # Mcast receiver
            'vm4':{'vn':['vn2'], 'vmi':['vmi4']}, # Mcast receiver
            }

        ret_dict = self.setup_mvpn(vn=vn, vmi=vmi, vm=vm)
        vmi_fixtures = ret_dict['vmi_fixtures']
        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  }


        # Configure policy between vn1 and vn2
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        return ret_dict

    @classmethod
    def tearDownClass(cls):
        super(MVPNTestMultiVNMultiComputeBase, cls).tearDownClass()
    # end tearDownClass


