from builtins import str
from builtins import range
from time import sleep
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from string import Template
import re
from common.device_connection import NetconfConnection
from common.vrouter.base import BaseVrouterTest
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic

from tcutils.tcpdump_utils import *
from tcutils.wrappers import preposttest_wrapper

from bms_fixture import BMSFixture
from physical_router_fixture import PhysicalRouterFixture
from common.contrail_fabric.base import BaseFabricTest
import ipaddress

class Evpnt6base(BaseFabricTest):

    def setUp(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'crb_mcast_gw' in (device_dict.get('rb_roles') or []) \
               and device_dict['role'] == 'spine':
                self.rb_roles[device] = ['CRB-MCAST-Gateway',
                    'CRB-Gateway', 'Route-Reflector']
            elif 'erb_ucast_gw' in (device_dict.get('rb_roles') or []) \
               and device_dict['role'] == 'leaf':
                self.rb_roles[device] = ['ERB-UCAST-Gateway']
        super(Evpnt6base, self).setUp()
        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')

    def is_test_applicable(self):
        result, msg = super(Evpnt6base, self).is_test_applicable()
        if result:
            msg = 'Need devices with crb_mcast_gw and erb_ucast_gw rb_roles'
            mcast_gw = ucast_gw = False
            for device_dict in list(self.inputs.physical_routers_data.values()):
                if 'crb_mcast_gw' in (device_dict.get('rb_roles') or []) \
                   and device_dict['role'] == 'spine':
                    mcast_gw = True
                elif 'erb_ucast_gw' in (device_dict.get('rb_roles') or []) \
                   and device_dict['role'] == 'leaf':
                    ucast_gw = True
                if mcast_gw and ucast_gw:
                    if self.get_bms_nodes(rb_role='erb_ucast_gw'):
                        return (True, None)
                    else:
                        msg = "Unable to find bms nodes attached to leafs " \
                              "with erb_ucast_gw rb_role"
                        return False, msg
            else:
                return False, msg
        return False, msg

    def send_igmp_reportsv2(self, vm_fixtures, traffic, igmp, **kwargs):
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
                result = self.send_igmp_reportv2(vm_fixtures[rcvr], igmp)
        return True

    def verify_evpn_routes(self, route_type, vxlan_id,ip,vm_fixtures=None, igmp=None, expectation=True):
        '''
            Verify MVPN routes at control node:
                mandatory args:
                    route_type  : Type of the MVPN route
                    vm_fixtures : VM Fixture details
                    traffic     : Multicast data traffic details
                    igmp        : IGMPv3 details
        '''

        result = True

        rtype = igmp['type']
        maddr = igmp['gaddr']

        if route_type == 6:
            evpn_route = "6-" + ".+" + "-" + str(vxlan_id) + "-" + maddr + "-" + ip
        elif route_type == 3:
            evpn_route = "3-" + ".+" + "-" + str(vxlan_id) + "-" + ip

        # Verify EVPN routes in bgp master mvpn table
        result = result & self.verify_evpn_route(vxlan_id,vm_fixtures,evpn_route, expectation=expectation)

        if result:
            self.logger.info('Successfully verified evpn route')
        else:
            assert result, "Error in verify_evpn_route"
        return result

    @retry(2, 10)
    def verify_evpn_route(self,vxlan_id,vm_fixtures,evpn_route, expectation=True):

        result = False

        vn_fq_name = vm_fixtures['vrf'].vn_fq_name
        vn_name = vn_fq_name.split(':')[-1]
        ri_name = vn_fq_name + ':' + vn_name

        for cn in vm_fixtures['vm1'].get_control_nodes():
            evpn_table_entry = self.cn_inspect[cn].get_cn_mvpn_table(ri_name,'evpn.0')

            for evpn_entry in evpn_table_entry:
                self.logger.debug('comparing %s with %s ' %(evpn_route, evpn_entry['prefix']))
                if re.match(evpn_route, evpn_entry['prefix']):
                    self.logger.debug('MATCH FOUND %s with %s ' %(evpn_route, evpn_entry['prefix']))
                    result = True
                    break


        if expectation == result:
            if expectation == False:
                self.logger.info('EVPN route : %s is not expected.' %(evpn_route))
                self.logger.debug('EVPN route : %s not found in table evpn.0 .' %(evpn_route))
            else:
                self.logger.info('EVPN route : %s is expected.' %(evpn_route))
                self.logger.debug('EVPN route : %s found in table evpn.0 .' %(evpn_route))
            return True
        else:
            if expectation == False:
                self.logger.warn('EVPN route : %s is not expected.' %(evpn_route))
                self.logger.debug('EVPN route : %s found in table evpn.0 .' %(evpn_route))
            else:
                self.logger.warn('EVPN route : %s is expected.' %(evpn_route))
                self.logger.debug('EVPN route : %s not found in table evpn.0 .' %(evpn_route))
            return False

    def verify_igmp_reports(self, vm_fixtures, traffic, igmp):
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

                ## Verifying IGMP report details in VM's VRF at agent
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

    def send_igmp_reportv2(self, rcv_vm_fixture, igmp, **kwargs):
        '''
            Sends IGMP Report from VM :
                mandatory args:
                    rcv_vm_fixture: send IGMP Report from this VM
                    igmp : IGMP Report details
                optional args:
                     1. count: No. of reports
        '''


        igmpv2 = {}
        igmpv2['type'] = igmp.get('type')
        igmpv2['gaddr'] = igmp.get('gaddr')
        igmpv2['numgrp'] = igmp.get('numgrp')
        scapy_obj = self._generate_igmp_trafficv2(rcv_vm_fixture,
                                                    igmpv2=igmpv2)
        return

    def _generate_igmp_trafficv2(self, rcv_vm_fixture, **kwargs):
        '''
            Generate IGMPv3 joins/leaves from multicast receiver VMs
        '''

        v2 = kwargs.get('igmpv2',{})
        group = v2['gaddr']
        numgrp = v2['numgrp']

        type = v2['type']
        ip = {'dst': str(group)}
        if type == 22:
            dip = str(group)
            ip = {'dst': str(group)}
        elif type == 23:
            dip='224.0.0.2'
            ip = {'dst': '224.0.0.2'}

        python_code = Template('''
from scapy.all import *
from scapy.contrib.igmp import *
import ipaddress
#group = unicode(group, "utf-8")
dip = unicode('$dst_ip', "utf-8")
dip = ipaddress.ip_address(dip)

group = unicode('$group', "utf-8")
group = ipaddress.ip_address(group)

payload = 'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'
for i in range(0,$numgrp):
    a=IP(dst=str(dip))/IGMP(gaddr=str(group),type=$type)/payload
    send(a, iface='eth0',inter=1.000000,count=1)
    group = group + 1
    if type == 22:
        dip = dip + 1

           ''')

        python_code = python_code.substitute(dst_ip=dip,group=group,numgrp=numgrp,type=type)

        rcv_vm_fixture.run_python_code(python_code) 


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
                    if rtype == 22:
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
            src_ip = stream['source']
            dst_ip = stream['maddr']
            net = stream['mnet']
            if net == None:
                net = dst_ip
            # Start the tcpdump on receivers
            for rcvr in stream['rcvrs']:
                filters = '\'src host %s and net %s\'' % (src_ip, net)
                session[rcvr], pcap[rcvr] = start_tcpdump_for_vm_intf(
                    self, vm_fixtures[rcvr], vm_fixtures[rcvr].vn_fq_name,
                    filters=filters)

            # Start the tcpdump on non receivers
            for rcvr in stream['non_rcvrs']:
                filters = '\'src host %s and net %s\'' % (src_ip, net)
                session[rcvr], pcap[rcvr] = start_tcpdump_for_vm_intf(
                    self, vm_fixtures[rcvr], vm_fixtures[rcvr].vn_fq_name,
                    filters=filters)

        return session, pcap

    def send_mcast_streams(self, vm_fixtures, traffic, interface):
        '''
            Sends Multicast traffic from multiple senders:
                mandatory args:
                    vm_fixtures: VM fixture details
                    traffic: Multicast data traffic source and receivers details
        '''

        # Send Multicast Traffic

        for stream in list(traffic.values()):
            src = stream['src'][0]
            self._generate_multicast_trafficv2(vm_fixtures[src], maddr=stream['maddr'], count=stream['count'], interface=interface)
        return True

    def _generate_multicast_trafficv2(self, fixture, maddr, count, interface):
        '''
            Generate IGMPv3 joins/leaves from multicast receiver VMs
        '''

        src_ip = self._my_ip(fixture)[0]
        ip = {'dst': maddr ,'src': src_ip}
        udp = {'sport':1500, 'dport':1501}

        python_code = Template('''
from scapy.all import *
from scapy.contrib.igmp import *
import ipaddress
dip = unicode('$dst_ip', "utf-8")
dip = ipaddress.ip_address(dip)
payload = 'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'
for i in range(0,$numgrp):
    a=IP(dst=str(dip),src='$sip')/UDP(dport=1501,sport=1500)/payload
    send(a, iface='$interface',inter=1.000000,count=10)
    dip = dip + 1
           ''')

        python_code = python_code.substitute(dst_ip=maddr,numgrp=count,interface=interface,sip=src_ip)

        fixture.run_python_code(python_code)


    def verify_mcast_streams(self, session, pcap, traffic, igmp):
        '''
            Verifies Multicast traffic as per traffic configuration
        '''

        result = True

        # Verify Multicast Traffic on receivers. Incase, IGMPv3 exclude is sent
        # multicast data traffic should not receive on the receivers. Only
        # IGMPv3 include should receive multicast data traffic.
        for stream in list(traffic.values()):
            maddr_traffic = stream['maddr']
            for rcvr in stream['rcvrs']:
                exp_count = stream['pcount'] * stream['count']

                result = result & verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
                                     exp_count=exp_count, grep_string="UDP")
        # Verify Multicast Traffic on non receivers, traffic should not reach
        # these
        for stream in list(traffic.values()):
            for rcvr in stream['non_rcvrs']:

                result = result & verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
                                     exp_count=0, grep_string="UDP")

        return result


    @retry(delay=2, tries=2)
    def verify_igmp_at_agent(self, compute_ip, vrf_id, tap_intf, grp_ip=None,
                             src_ip=None, expectation=True):
        '''
            Verify IGMP Report at agent
        '''
        mcast_route_in_agent = self.agent_inspect[compute_ip].get_vna_mcast_route(
            vrf_id=vrf_id, grp_ip=grp_ip, src_ip=src_ip)

        if mcast_route_in_agent:
            src_present = mcast_route_in_agent['src']
            grp_present = mcast_route_in_agent['grp']
            for mc_list in mcast_route_in_agent['nh']['mc_list']:
                try:
                    tap_intf_present = mc_list['itf']
                except KeyError:
                    tap_intf_present = None

                if src_ip == src_present and grp_ip == grp_present and tap_intf == tap_intf_present:
                   if expectation:
                        self.logger.info('IGMPv3 membership (S,G): (%s,%s) found '\
                                        'in agent: %s for tap:%s in vrf_id: %s as EXPECTED'
                                        % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
                        return True
                   else:
                        self.logger.warn('IGMPv3 membership (S,G): (%s,%s) found '\
                                            'in agent: %s for tap:%s in vrf_id: %s as NOT EXPECTED'
                                            % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
                        return False

        if expectation:
            self.logger.warn('IGMPv3 membership (S,G): (%s,%s) NOT found in '\
                         'agent: %s for tap:%s in vrf_id: %s NOT EXPECTED'
                         % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
            return False
        else:
            self.logger.info('IGMPv3 membership (S,G): (%s,%s) NOT found in '\
                         'agent: %s for tap:%s  in vrf_id: %s as EXPECTED'
                         % (src_ip, grp_ip, compute_ip, tap_intf, vrf_id))
            return True


    def send_verify_mcastv2(self, vm_fixtures, traffic, igmp, vxlan_id,assertFlag=True):
        '''
            Send and verify IGMP report and multicast traffic
                mandatory args:
                    vm_fixtures: vm_fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp: IGMP Report details
                optional args:
        '''
     
        self.logger.info('Sending IGMPv3 report as per configuration')
        result = self.send_igmp_reportsv2(vm_fixtures, traffic, igmp)

        if result:
            self.logger.info('Successfully sent IGMPv3 reports')
        else:
            assert result, "Error in sending IGMPv3 reports"

        # Verify IGMP membership reports at agent
        self.logger.info('Verifying IGMPv3 report as per configuration')
        result = self.verify_igmp_reports(vm_fixtures, traffic, igmp)

        ctrl_node = vm_fixtures['vm1'].get_control_nodes()[0]

        for stream in list(traffic.values()):
            if stream['rcvrs'] == []:
                result = self.verify_evpn_routes(6,vxlan_id,ctrl_node,vm_fixtures, igmp, expectation=False)
            else:
                result = self.verify_evpn_routes(6,vxlan_id,ctrl_node,vm_fixtures, igmp, expectation=True)
        if result:
            self.logger.info('Successfully verified evpn t6 routes')
        else:
            assert result, "Error in verifying evpn t6 route"



        # Start tcpdump on receivers
        self.logger.info('Starting tcpdump on mcast receivers')
        session, pcap = self.start_tcpdump_mcast_rcvrs(vm_fixtures, traffic)

        # Send multicast traffic
        time.sleep(40)
        self.logger.info('Sending mcast data traffic from mcast source')
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        result = self.send_mcast_streams(vm_fixtures, traffic,interface)

        time.sleep(25)

        if result:
            self.logger.info('Successfully sent multicast data traffic')
        else:
            assert result, "Error in sending multicast data traffic"


        # Verify multicast traffic
        self.logger.info('Verifying mcast data traffic on mcast receivers')
        result = self.verify_mcast_streams(session, pcap, traffic, igmp)

        if result:
            self.logger.info('Successfully verified multicast data traffic on all receivers')
        else:
            if assertFlag:
                assert result, "Error in verifying multicast data traffic on all receivers"
        return result

    def send_verify_mcast_traffic(self, vm_fixtures, traffic, igmp, vxlan_id,assertFlag=True):
        '''
            Send and verify IGMP report and multicast traffic
                mandatory args:
                    vm_fixtures: vm_fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp: IGMP Report details
                optional args:
        '''
     
        self.logger.info('Sending IGMPv3 report as per configuration')
        result = self.send_igmp_reportsv2(vm_fixtures, traffic, igmp)

        if result:
            self.logger.info('Successfully sent IGMPv3 reports')
        else:
            assert result, "Error in sending IGMPv3 reports"

        # Verify IGMP membership reports at agent
        self.logger.info('Verifying IGMPv3 report as per configuration')
        result = self.verify_igmp_reports(vm_fixtures, traffic, igmp)

        ctrl_node =  self.inputs.bgp_control_ips[0]


        # Start tcpdump on receivers
        self.logger.info('Starting tcpdump on mcast receivers')
        session, pcap = self.start_tcpdump_mcast_rcvrs(vm_fixtures, traffic)

        # Send multicast traffic
        time.sleep(15)
        self.logger.info('Sending mcast data traffic from mcast source')
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        result = self.send_mcast_streams(vm_fixtures, traffic,interface)

        time.sleep(25)

        if result:
            self.logger.info('Successfully sent multicast data traffic')
        else:
            assert result, "Error in sending multicast data traffic"


        # Verify multicast traffic
        self.logger.info('Verifying mcast data traffic on mcast receivers')
        result = self.verify_mcast_streams(session, pcap, traffic, igmp)

        if result:
            self.logger.info('Successfully verified multicast data traffic on all receivers')
        else:
            if assertFlag:
                assert result, "Error in verifying multicast data traffic on all receivers"
        return result

    def send_verify_mcast_traffic_within_cluster(self, vm_fixtures, traffic, igmp, vxlan_id,assertFlag=True):
        '''
            Send and verify IGMP report and multicast traffic
                mandatory args:
                    vm_fixtures: vm_fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp: IGMP Report details
                optional args:
        '''
     

        ctrl_node =  self.inputs.bgp_control_ips[0]

        # Start tcpdump on receivers
        self.logger.info('Starting tcpdump on mcast receivers')
        session, pcap = self.start_tcpdump_mcast_rcvrs(vm_fixtures, traffic)

        # Send multicast traffic
        time.sleep(15)
        self.logger.info('Sending mcast data traffic from mcast source')
        interface = 'eth0'
        result = self.send_mcast_streams(vm_fixtures, traffic,interface)

        time.sleep(25)

        if result:
            self.logger.info('Successfully sent multicast data traffic')
        else:
            assert result, "Error in sending multicast data traffic"


        # Verify multicast traffic
        self.logger.info('Verifying mcast data traffic on mcast receivers')
        result = self.verify_mcast_streams(session, pcap, traffic, igmp)

        if result:
            self.logger.info('Successfully verified multicast data traffic on all receivers')
        else:
            if assertFlag:
                assert result, "Error in verifying multicast data traffic on all receivers"
        return result

    def disable_snooping(self, prouters):
        cmd = []
        cmd.append('deactivate protocols igmp-snooping')
        cmd.append('deactivate groups __contrail_overlay_evpn_ucast_gateway__ protocols igmp-snooping')
        for prouter in prouters:
            prouter.netconf.config(stmts=cmd, timeout=120)

    def enable_snooping(self, prouters):
        cmd = []
        cmd.append('activate protocols igmp-snooping')
        cmd.append('activate groups __contrail_overlay_evpn_ucast_gateway__ protocols igmp-snooping')
        for prouter in prouters:
            prouter.netconf.config(stmts=cmd, timeout=120)
    
    def configure_igmp_on_vmi(self,vmi,flag):
        '''
            Configure IGMP on VMI:
        '''
        vmi_obj = self.vnc_lib.virtual_machine_interface_read(id=vmi)
        vmi_obj.set_igmp_enable(flag)
        self.vnc_h.virtual_machine_interface_update(vmi_obj)
        return True

class Evpnt6TopologyBase(Evpnt6base):

    def configure_evpn_topology(self, vxlan, **kwargs):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''

        result = True

        multinode = kwargs.get('multinode', 1)
        mode = kwargs.get('mode', 'l2_l3')
        self.vxlan_id = vxlan

        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]

        if len(host_list) > 2 and multinode:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]
            
        vm1_name = get_random_name('evpnvm1')
        vm2_name = get_random_name('evpnvm2')
        vm3_name = get_random_name('evpnvm3')

        self.vn1_fixture = self.create_vn(vxlan_id=self.vxlan_id,
                                          forwarding_mode=mode)
        self.vn1_fixture.set_igmp_config()

        bms_node = kwargs.pop('bms_node', None)
        bms = [bms_node] if bms_node else self.get_bms_nodes(rb_role='erb_ucast_gw')

        vm1_fixture = self.create_vm(vn_fixture=self.vn1_fixture,
            image_name='ubuntu', vm_name=vm1_name, node_name=compute_1)
        vm2_fixture = self.create_vm(vn_fixture=self.vn1_fixture,
            image_name='ubuntu', vm_name=vm2_name, node_name=compute_2)
        vm3_fixture = self.create_vm(vn_fixture=self.vn1_fixture,
            image_name='ubuntu', vm_name=vm3_name, node_name=compute_3)

        # Wait till vm is up
        if mode == 'l2_l3':
            assert vm1_fixture.wait_till_vm_is_up()
            assert vm2_fixture.wait_till_vm_is_up()
            assert vm3_fixture.wait_till_vm_is_up()

        vm_fixtures = {'vm1':vm1_fixture,'vm2':vm2_fixture,'vm3':vm3_fixture}

        bms_fixture = self.create_bms(bms_name=bms[0],
            vn_fixture=self.vn1_fixture,
            vlan_id=self.vxlan_id)

        time.sleep(60)

        vn1_fixture = self.vn1_fixture 
        vm_fixtures = {'vm1':vm1_fixture,'vm2':vm2_fixture,'vm3':vm3_fixture,'bms':bms_fixture, 'vn1':vn1_fixture}

        return vm_fixtures

class Evpnt6MultiVnBase(Evpnt6base):

    def is_test_applicable(self):
        result, msg = super(Evpnt6base, self).is_test_applicable()
        if result:
            msg = 'Need atleast 3 compute nodes'
            if len(self.connections.orch.get_hosts()) > 2:
                return True, None
        return False, msg

    def configure_evpn_mvn_topology(self,vxlan,vn_count):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[1]
        compute_3 = host_list[2]

        self.vxlan_id = vxlan
        bms =self.get_bms_nodes(rb_role='erb_ucast_gw')
        
        vn_ip = str('5.1.1.0', "utf-8")
        vn_ip = ipaddress.ip_address(vn_ip)
        vm_fixtures = {}
        for i in range(1,vn_count):
    
            bms_name = 'bms'+str(i)
            vm_name = 'vm'+str(i)
            vn_name = 'vn'+str(i)
            vn_subnet = str(vn_ip) +'/24'
            vn_subnets = [vn_subnet] 

            self.vn_fixture = self.create_vn(vn_name=vn_name, vn_subnets=vn_subnets ,vxlan_id=self.vxlan_id)
            self.vn_fixture.set_igmp_config()
            vm_fixture = self.create_vm(vn_fixture=self.vn_fixture ,image_name='ubuntu',vm_name=vm_name)

            # Wait till vm is up
            assert vm_fixture.wait_till_vm_is_up()
            vm_fixtures[vm_name] = vm_fixture

            if i == 1:
                bms_fixture = self.create_bms(bms_name=bms[0],
                    vn_fixture=self.vn_fixture,
                    vlan_id=self.vxlan_id)
            else:
                bms_fixture = self.create_bms(bms_name=bms[0],
                    vn_fixture=self.vn_fixture,
                    vlan_id=self.vxlan_id,
                    port_group_name=bms_fixture.port_group_name,
                    bond_name=bms_fixture.bond_name)

            vm_fixtures[bms_name] = bms_fixture

            vn_ip =  vn_ip + 16777216
            self.vxlan_id = self.vxlan_id + 1

        time.sleep(60)
        return vm_fixtures
