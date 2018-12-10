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

class IGMPV2TestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(IGMPV2TestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    @classmethod
    def tearDownClass(cls):
        super(IGMPV2TestBase, cls).tearDownClass()

    def send_igmp_reportsv2(self, vm_fixtures, traffic, igmp, **kwargs):
        '''
            Sends IGMP Reports from multiple receivers :
                mandatory args:
                    vm_fixtures: VM fixture details
                    traffic: Multicast data traffic source and receivers details
                    igmp   : IGMP Report details
        '''

        # Send IGMPv3 membership reports from multicast receivers
        for stream in traffic.values():
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


        return result

    def verify_evpn_route(self,vxlan_id,vm_fixtures,evpn_route, **kwargs):

        result = False
        expectation = kwargs.get('expectation',True)

        vn_fq_name = vm_fixtures['vrf'].vn_fq_name
        vn_name = vn_fq_name.split(':')[-1]
        ri_name = vn_fq_name + ':' + vn_name

        for cn in self.inputs.bgp_ips:
            evpn_table_entry = self.cn_inspect[cn].get_cn_mvpn_table(ri_name,'evpn.0')

            for evpn_entry in evpn_table_entry:
                self.logger.info('comparing %s with %s ' %(evpn_route, evpn_entry['prefix']))
                if re.match(evpn_route, evpn_entry['prefix']):
                    self.logger.info('MATCH FOUND %s with %s ' %(evpn_route, evpn_entry['prefix']))
                    result = True
                    break


        if expectation == result:
            if expectation == False:
                self.logger.info('EVPN route : %s is not expected.' %(evpn_route))
                self.logger.info('EVPN route : %s not found in table evpn.0 .' %(evpn_route))
            else:
                self.logger.info('EVPN route : %s is expected.' %(evpn_route))
                self.logger.info('EVPN route : %s found in table evpn.0 .' %(evpn_route))
            return True
        else:
            if expectation == False:
                self.logger.info('EVPN route : %s is not expected.' %(evpn_route))
                self.logger.info('EVPN route : %s found in table evpn.0 .' %(evpn_route))
            else:
                self.logger.info('EVPN route : %s is expected.' %(evpn_route))
                self.logger.info('EVPN route : %s not found in table evpn.0 .' %(evpn_route))
            #self.logger.warn('Route  %s not found ' %(evpn_route))
            return False


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
        for stream in traffic.values():
            for rcvr in stream['rcvrs']:

                ## Verifying IGMP report details in VM's VRF at agent
                compute_node_ip = vm_fixtures[rcvr].vm_node_ip
                vrf_id = vm_fixtures[rcvr].get_vrf_ids()[compute_node_ip].values()[0]
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
        for stream in traffic.values():
            for rcvr in stream['non_rcvrs']:


                # Verifying IGMP report details in VM's VRF at agent
                compute_node_ip = vm_fixtures[rcvr].vm_node_ip
                vrf_id = vm_fixtures[rcvr].get_vrf_ids()[compute_node_ip].values()[0]
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

        params = {}
        params['igmpv2'] = kwargs.get('igmpv2',{})
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
            #dip = str(group)
            ip = {'dst': '224.0.0.2'}

        params['ip'] = ip
        params['payload'] = "''"
        params['count'] = numgrp


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
        #print "py code is %s" % python_code

        rcv_vm_fixture.run_python_code(python_code) 


    def verify_igmp_report(self, vm_fixture, vrf_id, igmp, expectation=True):
        '''
            Verify IGMP Report:
                mandatory args:
                    vm_fixture: IGMP Report from this VM
                optional args:
        '''

        result = True
        tap_intf = vm_fixture.tap_intf.values()[0]['name']
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
        for stream in traffic.values():
            src_ip = stream['source']
            dst_ip = stream['maddr']
            net = stream['mnet']
            if net == None:
                net = dst_ip
            # Start the tcpdump on receivers
            for rcvr in stream['rcvrs']:
                filters = '\'src host %s and net %s\'' % (src_ip, net)
                #filters = '\'(src host %s and dst host %s)\'' % (src_ip, dst_ip)
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

    def send_mcast_streams(self, vm_fixtures, traffic, **kwargs):
        '''
            Sends Multicast traffic from multiple senders:
                mandatory args:
                    vm_fixtures: VM fixture details
                    traffic: Multicast data traffic source and receivers details
        '''

        # Send Multicast Traffic

        for stream in traffic.values():
            #self.send_mcast_stream(vm_fixtures[stream['src']], maddr=stream['maddr'], count=stream['count'])
            #import pdb;pdb.set_trace()
            src = stream['src'][0]
            self._generate_multicast_trafficv2(vm_fixtures[src], maddr=stream['maddr'], count=stream['count'])
        return True

    def _generate_multicast_trafficv2(self, bms_fixture,maddr,count):
        '''
            Generate IGMPv3 joins/leaves from multicast receiver VMs
        '''

        params = {}

        src_ip = bms_fixture.static_ip
        ip = {'dst': maddr ,'src': src_ip}
        params['ip'] = ip
        int = bms_fixture.get_mvi_interface()
        params['interface'] = int
        params['payload'] = "''"
        params['count'] = count
        udp = {'sport':1500, 'dport':1501}
        params['inner_udp'] = udp



        python_code = Template('''
from scapy.all import *
from scapy.contrib.igmp import *
import ipaddress
dip = unicode('$dst_ip', "utf-8")
dip = ipaddress.ip_address(dip)
payload = 'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'
for i in range(0,$numgrp):
    a=IP(dst=str(dip),src='$sip')/UDP(dport=1501,sport=1500)/payload
    send(a, iface='$int',inter=1.000000,count=10)
    dip = dip + 1
           ''')

        python_code = python_code.substitute(dst_ip=maddr,numgrp=count,int=int,sip=src_ip)

        bms_fixture.run_python_code(python_code)



    def verify_mcast_streams(self, session, pcap, traffic, igmp, **kwargs):
        '''
            Verifies Multicast traffic as per traffic configuration
        '''

        result = True

        # Verify Multicast Traffic on receivers. Incase, IGMPv3 exclude is sent
        # multicast data traffic should not receive on the receivers. Only
        # IGMPv3 include should receive multicast data traffic.
        for stream in traffic.values():
            maddr_traffic = stream['maddr']
            for rcvr in stream['rcvrs']:
                exp_count = stream['pcount'] * stream['count']

                result = verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
                                     exp_count=exp_count, grep_string="UDP")
        # Verify Multicast Traffic on non receivers, traffic should not reach
        # these
        for stream in traffic.values():
            for rcvr in stream['non_rcvrs']:

                result = verify_tcpdump_count(self, session[rcvr], pcap[rcvr],
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

        ctrl_node =  self.inputs.bgp_control_ips[0]

        for stream in traffic.values():
            if stream['rcvrs'] == []:
                result = self.verify_evpn_routes(6,vxlan_id,ctrl_node,vm_fixtures, igmp, expectation=False)
            else:
                result = self.verify_evpn_routes(6,vxlan_id,ctrl_node,vm_fixtures, igmp, expectation=True)
        if result:
            self.logger.info('Successfully verified evpn t6 routes')
        else:
            assert result, "Error in verifying evpn t6 route"

        #result = self.verify_evpn_routes(3,vxlan_id,'150.1.1.1',vm_fixtures, igmp, expectation=True)
        #if result:
        #    self.logger.info('Successfully verified evpn t3 routes')
        #else:
        #    assert result, "Error in verifying evpn t3 route"


        # Start tcpdump on receivers
        self.logger.info('Starting tcpdump on mcast receivers')
        session, pcap = self.start_tcpdump_mcast_rcvrs(vm_fixtures, traffic)

        # Send multicast traffic
        time.sleep(15)
        self.logger.info('Sending mcast data traffic from mcast source')
        bms_fixtures = vm_fixtures['bms']
        int = bms_fixtures.get_mvi_interface()
        result = self.send_mcast_streams(vm_fixtures, traffic)

        time.sleep(10)
        time.sleep(10)
        time.sleep(15)

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

    @classmethod
    def tearDownClass(cls):
        super(IGMPV2TestBase, cls).tearDownClass()
    # end tearDownClass

class setupFabricDcGw(BaseFabricTest):

    def is_test_applicable(self):
        result, msg = super(setupFabricDcGw, self).is_test_applicable()
        if result:
            msg = 'No spines in the provided fabric topology'
            for device in self.inputs.physical_routers_data.iterkeys():
                if self.get_role_from_inputs(device) == 'spine':
                    break
            else:
                return False, msg
            msg = 'No public subnets specified in test inputs yaml'
            if self.inputs.public_subnets:
                return (True, None)
        return False, msg

    def setUp(self):
        for device_name, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'spine':
                self.rb_roles[device_name] = ['DC-Gateway']
        super(setupFabricDcGw, self).setUp()

class Evpnt6base(BaseFabricTest):

    def setUp(self):

        for device_name, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'spine':
                self.rb_roles[device_name] = ['DC-Gateway']
        super(Evpnt6base, self).setUp()


        tors_info_list = self.get_available_devices('tor')
        tor_params = tors_info_list[0]
        peer_ip=tor_params['peer_ip']
        loop_ip=tor_params['loop_ip']

        cmd='ip route add '+str(loop_ip)+ '/32 dev vhost0 via '+str(peer_ip)
        for item in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(
                item, cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'])

        cmd='ip route add '+str(loop_ip)+'/32 dev eno2 via '+str(peer_ip)
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

    def configure_qfx(self,vxlan_id,rt_value):

        encap = 'vxlan'
        tors_info_list = self.get_available_devices('tor')
        tor_params = tors_info_list[0]
        mgmt_ip=tor_params['mgmt_ip']
        port=tor_params['ports']

        cmd = []
        vxlan = "vx" + str(vxlan_id)
        vn    = "vncom" + str(vxlan_id)
        cmd.append('set interfaces '+ port +' unit 0 family ethernet-switching interface-mode trunk')
        cmd.append('set interfaces ' + port +' unit 0 family ethernet-switching vlan members '+str(vxlan_id))
        cmd.append('set protocols igmp-snooping vlan bd-'+str(vxlan_id)+' proxy')
        mx_handle = NetconfConnection(host = mgmt_ip)
        mx_handle.connect()
        time.sleep(30)
        cli_output = mx_handle.config(stmts = cmd, timeout = 120)
        time.sleep(30)
        mx_handle.disconnect()

    def get_available_devices(self, device_type):
        ''' device_type is one of router/tor
        '''
        available = []
        for (device, device_dict) in self.inputs.physical_routers_data.iteritems():
            if device_dict['type'] == device_type :
                available.append(device_dict)
        return available
    # end get_available_devices

    def create_bms(self, bms_name, **kwargs):
        self.logger.info('Creating bms %s'%bms_name)
        bms = self.useFixture(BMSFixture(
                              connections=self.connections,
                              name=bms_name,
                              **kwargs))
        return bms

class Evpnt6MultinodeBase(IGMPV2TestBase,Evpnt6base):

    @classmethod
    def setUpClass(cls):
        super(Evpnt6MultinodeBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(Evpnt6MultinodeBase, cls).tearDownClass()

    def delete_vn(self):
        self.logger.info('!!!!!!!!!! Detaching VN from fabric!!!!!!!!!!!!!!!!')
        for spine in self.spines:
            spine.delete_virtual_network(self.vn1_fixture.uuid)

    def configure_evpn_mn_topology(self):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''
        encap = 'vxlan'
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap('VXLAN', 'MPLSoUDP', 'MPLSoGRE')
        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]

        if len(host_list) > 2:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]
            
        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'
        vn_l2_vm3_name = 'EVPN_VN_L2_VM3'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["5.1.1.0/24"])
        self.vxlan_id = 400
        self.vxlan_id_nr = 401
        vxlan_id = 400
        rt_value = 7000007

        self.configure_qfx(vxlan_id,rt_value)
        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')
        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                vxlan_id=self.vxlan_id,
                forwarding_mode='l2_l3'))
        assert self.vn1_fixture.verify_on_setup()

        assert self.vn1_fixture.verify_on_setup()

        self.vn1_fixture.set_igmp_config()
        time.sleep(10)


        bms =self.inputs.bms_data.keys()
        bms_fixtures = []
        bms_fixtures = self.create_bms(bms_name=bms[0], vn_fixture=self.vn1_fixture, vlan_id=400, static_ip='5.1.1.10', bms_ip='5.1.1.10')

        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm3_name,
                node_name=compute_3))



        # Wait till vm is up
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()

        vm_fixtures = {'vm1':vm1_fixture,'vm2':vm2_fixture,'vm3':vm3_fixture}

        for spine in self.spines:
            spine.add_virtual_network(self.vn1_fixture.uuid)
            self.addCleanup(self.delete_vn)

        time.sleep(50)

        vn1_fixture = self.vn1_fixture 
        vm_fixtures = {'vm1':vm1_fixture,'vm2':vm2_fixture,'vm3':vm3_fixture,'bms':bms_fixtures, 'vn1':vn1_fixture}

        return vm_fixtures

class Evpnt6SinglenodeBase(IGMPV2TestBase,Evpnt6base):

    @classmethod
    def setUpClass(cls):
        super(Evpnt6SinglenodeBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(Evpnt6SinglenodeBase, cls).tearDownClass()

    def configure_evpn_sn_topology(self):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''
        encap = 'vxlan'
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap('VXLAN', 'MPLSoUDP', 'MPLSoGRE')
        encap = 'vxlan'
        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]


        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'
        vn_l2_vm3_name = 'EVPN_VN_L2_VM3'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["5.1.1.0/24"])
        self.vxlan_id = 400
        self.vxlan_id_nr = 401
        vxlan_id = 400
        rt_value = 7000007


        self.configure_qfx(vxlan_id,rt_value)
        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                vxlan_id=self.vxlan_id,
                forwarding_mode='l2_l3'))
        assert self.vn1_fixture.verify_on_setup()



        self.vn1_fixture.set_igmp_config()
        time.sleep(10)

        bms_fixtures = []
        bms =self.inputs.bms_data.keys()
        bms_fixtures = self.create_bms(bms_name=bms[0], vn_fixture=self.vn1_fixture, vlan_id=400, static_ip='5.1.1.10',bms_ip='5.1.1.10')
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_1))
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm3_name,
                node_name=compute_1))



        # Wait till vm is up
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()

        for spine in self.spines:
            spine.add_virtual_network(self.vn1_fixture.uuid)
            self.addCleanup(self.delete_vn)
        time.sleep(50)
        vm_fixtures = {'vm1':vm1_fixture,'vm2':vm2_fixture,'vm3':vm3_fixture,'bms':bms_fixtures}

        return vm_fixtures

    def delete_vn(self):
        self.logger.info('!!!!!!!!!! Detaching VN from fabric!!!!!!!!!!!!!!!!')
        for spine in self.spines:
            spine.delete_virtual_network(self.vn1_fixture.uuid)


class Evpnt6MultiVnBase(IGMPV2TestBase,Evpnt6base):

    @classmethod
    def setUpClass(cls):
        super(Evpnt6MultiVnBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(Evpnt6MultiVnBase, cls).tearDownClass()

    def delete_vn(self,vn):
        self.logger.info('!!!!!!!!!! Detaching VN from fabric!!!!!!!!!!!!!!!!')
        for spine in self.spines:
            spine.delete_virtual_network(vn.uuid)
            time.sleep(3)

    def configure_evpn_mvn_topology(self,vn_count):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''
        encap = 'vxlan'
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap('VXLAN', 'MPLSoUDP', 'MPLSoGRE')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]

        self.vxlan_id = 400
        self.vxlan_id_nr = 401
        vxlan_id = 400
        rt_value = 7000007
        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')
        bms =self.inputs.bms_data.keys()
        
        vn_ip = unicode('5.1.1.0', "utf-8")
        vn_ip = ipaddress.ip_address(vn_ip)
        vm_fixtures = {}
        for i in range(1,vn_count):
    
            bms_name= Template('bms$i')
            bms_name =bms_name.substitute(i=i)
            vm_name= Template('vm$i')
            vm_name =vm_name.substitute(i=i)
            vn_name= Template('vn$i')
            vn_name =vn_name.substitute(i=i)
            vn_subnet = str(vn_ip) +'/24'
            bms_ip = vn_ip + 10
            vn_subnets = [vn_subnet] 

            self.vn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    inputs=self.inputs,
                    vn_name=vn_name,
                    subnets=vn_subnets,
                    vxlan_id=vxlan_id,
                    forwarding_mode='l2_l3'))
            assert self.vn_fixture.verify_on_setup()

            self.vn_fixture.set_igmp_config()
            time.sleep(10)

            vm_fixture = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_objs=[
                        self.vn_fixture.obj],
                    image_name='ubuntu',
                    vm_name=vm_name,
                    node_name=compute_1))

            # Wait till vm is up
            assert vm_fixture.verify_on_setup()
            vm_fixtures[vm_name] = vm_fixture

            self.configure_qfx(vxlan_id,rt_value)
            for spine in self.spines:
                spine.add_virtual_network(self.vn_fixture.uuid)
                self.addCleanup(self.delete_vn,self.vn_fixture)

            bms_fixtures = self.create_bms(bms_name=bms[0], vn_fixture=self.vn_fixture, vlan_id=vxlan_id, bms_ip=str(bms_ip),static_ip=str(bms_ip), unit=vxlan_id)
            vm_fixtures[bms_name] = bms_fixtures

            vn_ip =  vn_ip + 16777216
            vxlan_id = vxlan_id + 1
            rt_value = rt_value + 1

        time.sleep(50)
        return vm_fixtures
