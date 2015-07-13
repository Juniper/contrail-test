# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will
# try to pick params.ini in PWD
import sys
import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from testresources import ResourcedTestCase
from ecmp_test_resource import ECMPSolnSetupResource


class TestECMP(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures):

    resources = [('base_setup', ECMPSolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = ECMPSolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.res.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.api_s_inspect = self.connections.api_server_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.agent_vn_obj = {}

    def __del__(self):
        print "Deleting test_with_setup now"
        ECMPSolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(TestECMP, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(TestECMP, self).tearDown()
        ECMPSolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_ecmp_to_non_ecmp_bw_three_vms_same_fip(self):
        '''Test communication between three VMs who have borrowed the FIP from common FIP pool.Delete two of the VMs and check that traffic flow is unaffected.
        '''
        result = True
        self.fip_pool_name = self.res.fip_pool_name
        fvn = self.res.fvn
        vn1 = self.res.vn1
        vn2 = self.res.vn2
        vn3 = self.res.vn3
        my_fip = self.res.my_fip
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = self.res.dport1
        dport2 = self.res.dport2
        dport3 = self.res.dport3
        udp_src = self.res.udp_src
        vm1 = self.res.vm1
        vm2 = self.res.vm2
        vm3 = self.res.vm3
        fvn_vm1 = self.res.fvn_vm1

        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip):
            vm_node_ips.append(vm3.vm_node_ip)

        self.logger.info("-" * 80)
        self.logger.info('Starting TCP Traffic from fvn_vm1 to 30.1.1.3')
        self.logger.info("-" * 80)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport2)
        stream3 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport3)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                send_filename = 'sendtcp_%s' % count
                recv_filename = 'recvtcp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                sender[stream][vm] = Sender(
                    send_filename, profile[stream][vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
                sender[stream][vm].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.logger.info(
            'Will disassociate the fip address from two VMs and check that there should be no traffic loss.')
        self.res.fip_obj.del_virtual_machine_interface(self.res.vm1_intf)
        self.res.vnc_lib.floating_ip_update(self.res.fip_obj)
        self.res.fip_obj.del_virtual_machine_interface(self.res.vm3_intf)
        self.res.vnc_lib.floating_ip_update(self.res.fip_obj)
        self.logger.info('Get the Route Entry in the control node')

        for vm_node_ip in vm_node_ips:
            active_controller = None
            inspect_h1 = self.agent_inspect[vm_node_ip]
            agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes':
                    active_controller = entry['controller_ip']
                    self.logger.info(
                        'Active control node from the Agent %s is %s' %
                        (vm_node_ip, active_controller))
        sleep(5)
        route_entry = self.cn_inspect[active_controller].get_cn_route_table_entry(
            ri_name=self.res.fvn_ri_name, prefix='30.1.1.3/32')
        self.logger.info('Route_entry in the control node is %s' % route_entry)
        result = True
        if route_entry:
            self.logger.info(
                'Route Entry found in the Active Control-Node %s' %
                (active_controller))
        else:
            result = False
            assert result, 'Route Entry not found in the Active Control-Node %s' % (
                active_controller)

        self.logger.info(
            'Get the FIP list and verify the vrf_name and address in the VMI')

        fip_addr_vm1 = self.res.vm1.chk_vmi_for_fip(self.res.vn1_fq_name)
        fip_addr_vm2 = self.res.vm2.chk_vmi_for_fip(self.res.vn2_fq_name)
        fip_addr_vm3 = self.res.vm3.chk_vmi_for_fip(self.res.vn3_fq_name)

        fip_vrf_entry_vm1 = self.res.vm1.chk_vmi_for_vrf_entry(
            self.res.vn1_fq_name)
        fip_vrf_entry_vm2 = self.res.vm2.chk_vmi_for_vrf_entry(
            self.res.vn2_fq_name)
        fip_vrf_entry_vm3 = self.res.vm3.chk_vmi_for_vrf_entry(
            self.res.vn3_fq_name)
        self.logger.info(
            'The vrf_entry on the VMI of %s is %s, on %s is %s and on %s is %s' %
            (self.res.vm1.vm_name, fip_vrf_entry_vm1, self.res.vm2.vm_name, fip_vrf_entry_vm2, self.res.vm3.vm_name, fip_vrf_entry_vm3))
        if ((fip_vrf_entry_vm2 == self.res.fvn_vrf_name) and all(x == None for x in (fip_vrf_entry_vm1, fip_vrf_entry_vm3))):
            self.logger.info('Correct FIP VRF Entries seen ')
        else:
            result = False
            assert result, 'Incorrect FIP VRF Entries seen'

        self.logger.info(
            'The FIP address assigned to %s is %s, to %s is %s and to %s is %s' %
            (vm1.vm_name, fip_addr_vm1, vm2.vm_name, fip_addr_vm2, vm3.vm_name, fip_addr_vm3))
        if ((fip_addr_vm2 == my_fip) and all(x == None for x in (fip_addr_vm1, fip_addr_vm3))):
            self.logger.info('FIP Address assigned correctly ')
        else:
            result = False
            assert result, 'FIP Address assignment incorrect'

        for stream in stream_list:
            for vm in vm_list:
                sender[stream][vm].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for vm in vm_list:
                stream_sent_count[stream] = stream_sent_count[stream] + \
                    sender[stream][vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5:
                self.logger.info(
                    '%s packets sent and %s packets received in Stream after disassociating ' %
                    (stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result = False
                assert result, '%s packets sent and %s packets received in Stream' % (
                    stream_sent_count[stream], stream_recv_count[stream])
        return True
    # end test_ecmp_to_non_ecmp_bw_three_vms_same_fip

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip_delete_add_fip(self):
        '''Test communication between three VMs who have borrowed the FIP from common FIP pool.Delete one of the VM and check that ECMP hold good. Add a VM later and check that ECMP continues between the three VMs
        '''
        result = True
        self.fip_pool_name = self.res.fip_pool_name
        fvn = self.res.fvn
        vn1 = self.res.vn1
        vn2 = self.res.vn2
        vn3 = self.res.vn3
        my_fip = self.res.my_fip
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = self.res.dport1
        dport2 = self.res.dport2
        dport3 = self.res.dport3
        udp_src = self.res.udp_src
        vm1 = self.res.vm1
        vm2 = self.res.vm2
        vm3 = self.res.vm3
        fvn_vm1 = self.res.fvn_vm1

        (domain, project, vn2) = self.res.vn2_fq_name.split(':')
        (domain, project, fvn) = self.res.fvn_fq_name.split(':')
        (domain, project, vn1) = self.res.vn1_fq_name.split(':')
        (domain, project, vn3) = self.res.vn3_fq_name.split(':')

        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip):
            vm_node_ips.append(vm3.vm_node_ip)

        self.logger.info("-" * 80)
        self.logger.info('Starting TCP Traffic from fvn_vm1 to 30.1.1.3')
        self.logger.info("-" * 80)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport2)
        stream3 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport3)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                send_filename = 'sendtcp_%s' % count
                recv_filename = 'recvtcp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                sender[stream][vm] = Sender(
                    send_filename, profile[stream][vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
                sender[stream][vm].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.logger.info(
            'Will disassociate the fip address from one of the VMs and check if ECMP still exists between the other two')
        self.logger.info('There should be no packet loss')
        self.res.fip_obj.del_virtual_machine_interface(self.res.vm1_intf)
        self.res.vnc_lib.floating_ip_update(self.res.fip_obj)

        self.logger.info('Get the Route Entry in the control node')

        for vm_node_ip in vm_node_ips:
            active_controller = None
            inspect_h1 = self.agent_inspect[vm_node_ip]
            agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes':
                    active_controller = entry['controller_ip']
                    self.logger.info(
                        'Active control node from the Agent %s is %s' %
                        (vm_node_ip, active_controller))
        sleep(5)
        route_entry = self.cn_inspect[active_controller].get_cn_route_table_entry(
            ri_name=self.res.fvn_ri_name, prefix='30.1.1.3/32')
        self.logger.info('Route_entry in the control node is %s' % route_entry)
        result = True
        if route_entry:
            self.logger.info(
                'Route Entry found in the Active Control-Node %s' %
                (active_controller))
        else:
            result = False
            assert result, 'Route Entry not found in the Active Control-Node %s' % (
                active_controller)

        self.logger.info(
            'Get the FIP list and verify the vrf_name and address in the VMI')

        fip_addr_vm1 = self.res.vm1.chk_vmi_for_fip(self.res.vn1_fq_name)
        fip_addr_vm2 = self.res.vm2.chk_vmi_for_fip(self.res.vn2_fq_name)
        fip_addr_vm3 = self.res.vm3.chk_vmi_for_fip(self.res.vn3_fq_name)

        fip_vrf_entry_vm1 = self.res.vm1.chk_vmi_for_vrf_entry(
            self.res.vn1_fq_name)
        fip_vrf_entry_vm2 = self.res.vm2.chk_vmi_for_vrf_entry(
            self.res.vn2_fq_name)
        fip_vrf_entry_vm3 = self.res.vm3.chk_vmi_for_vrf_entry(
            self.res.vn3_fq_name)
        self.logger.info(
            'The vrf_entry on the VMI of %s is %s, on %s is %s and on %s is %s' %
            (self.res.vm1.vm_name, fip_vrf_entry_vm1, self.res.vm2.vm_name, fip_vrf_entry_vm2, self.res.vm3.vm_name, fip_vrf_entry_vm3))
        if ((fip_vrf_entry_vm1 == None) and all(x == self.res.fvn_vrf_name for x in (fip_vrf_entry_vm2, fip_vrf_entry_vm3))):
            self.logger.info('Correct FIP VRF Entries seen ')
        else:
            result = False
            assert result, 'Incorrect FIP VRF Entries seen'

        self.logger.info(
            'The FIP address assigned to %s is %s, to %s is %s and to %s is %s' %
            (vm1.vm_name, fip_addr_vm1, vm2.vm_name, fip_addr_vm2, vm3.vm_name, fip_addr_vm3))
        if ((fip_addr_vm1 == None) and all(x == my_fip for x in (fip_addr_vm2, fip_addr_vm3))):
            self.logger.info('FIP Address assigned correctly ')
        else:
            result = False
            assert result, 'FIP Address assignment incorrect'

        self.logger.info('Check for the FIP route entry')

        for vm_node_ip in vm_node_ips:
            tap_intf_list = []
            inspect_h9 = self.agent_inspect[vm_node_ip]
            agent_vrf_objs = inspect_h9.get_vna_vrf_objs(domain, project, fvn)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.res.fvn_vrf_name)
            fvn_vrf_id9 = agent_vrf_obj['ucindex']
            paths = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=self.res.my_fip, prefix='32')['path_list']
            self.logger.info('There are %s nexthops to %s on Agent %s' %
                             (len(paths), self.res.my_fip, vm_node_ip))
            next_hops = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=self.res.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']

            if not next_hops:
                result = False
                assert result, 'Route not found in the Agent %s' % vm_node_ip
            else:
                self.logger.info('Route found in the Agent %s' % vm_node_ip)

            for nh in next_hops:
                label = nh['label']
                if nh['type'] == 'Tunnel':
                    destn_agent = nh['dip']
                    inspect_hh = self.agent_inspect[destn_agent]
                    agent_vrf_objs = inspect_hh.get_vna_vrf_objs(
                        domain, project, fvn)
                    agent_vrf_obj = self.get_matching_vrf(
                        agent_vrf_objs['vrf_list'], self.res.fvn_vrf_name)
                    fvn_vrf_id5 = agent_vrf_obj['ucindex']
                    next_hops_in_tnl = inspect_hh.get_vna_active_route(
                        vrf_id=fvn_vrf_id5, ip=self.res.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl = next_hop['itf']
                            tap_intf_list.append(tap_intf_from_tnl)
                elif nh['type'] == 'Interface':
                    tap_intf = nh['itf']
                    tap_intf_list.append(tap_intf)

            agent_tap_intf_list[vm_node_ip] = tap_intf_list
        self.logger.info('The list of Tap interfaces from the agents are %s' %
                         agent_tap_intf_list)
#        a_list= agent_tap_intf_list.values()
#        result= all(x == a_list[0] for x in a_list)
#
#        if result == True:
#            self.logger.info('The Tap interface list is the same across agents')
#        else:
#            assert result, 'The Tap interface list across agents is incorrect'
        for stream in stream_list:
            for vm in vm_list:
                sender[stream][vm].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()
        sleep(10)
        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for vm in vm_list:
                stream_sent_count[stream] = stream_sent_count[stream] + \
                    sender[stream][vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5:
                self.logger.info(
                    '%s packets sent and %s packets received in Stream after disassociating ' %
                    (stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result = False
                assert result, '%s packets sent and %s packets received in Stream after disassociating' % (
                    stream_sent_count[stream], stream_recv_count[stream])

        self.logger.info("-" * 80)
        self.logger.info('Starting TCP Traffic again from fvn_vm1 to 30.1.1.3')
        self.logger.info("-" * 80)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport2)
        stream3 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport3)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                send_filename = 'sendtcp_%s' % count
                recv_filename = 'recvtcp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                sender[stream][vm] = Sender(
                    send_filename, profile[stream][vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
                sender[stream][vm].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.logger.info(
            'Will re-associate the fip address from one of the VMs and check if ECMP holds ')
        self.logger.info(
            'There should be no packet loss in the traffic stream')
        self.res.fip_obj.add_virtual_machine_interface(self.res.vm1_intf)
        self.res.vnc_lib.floating_ip_update(self.res.fip_obj)
        sleep(10)
        self.logger.info(
            'Get the FIP list again and verify the vrf_name and address in the VMI')

        fip_addr_vm1 = self.res.vm1.chk_vmi_for_fip(self.res.vn1_fq_name)
        fip_addr_vm2 = self.res.vm2.chk_vmi_for_fip(self.res.vn2_fq_name)
        fip_addr_vm3 = self.res.vm3.chk_vmi_for_fip(self.res.vn3_fq_name)

        fip_vrf_entry_vm1 = self.res.vm1.chk_vmi_for_vrf_entry(
            self.res.vn1_fq_name)
        fip_vrf_entry_vm2 = self.res.vm2.chk_vmi_for_vrf_entry(
            self.res.vn2_fq_name)
        fip_vrf_entry_vm3 = self.res.vm3.chk_vmi_for_vrf_entry(
            self.res.vn3_fq_name)
        self.logger.info(
            'The vrf_entry on the VMI of %s is %s, on %s is %s and on %s is %s' %
            (self.res.vm1.vm_name, fip_vrf_entry_vm1, self.res.vm2.vm_name, fip_vrf_entry_vm2, self.res.vm3.vm_name, fip_vrf_entry_vm3))
        if all(x == self.res.fvn_vrf_name for x in (fip_vrf_entry_vm1, fip_vrf_entry_vm2, fip_vrf_entry_vm3)):
            self.logger.info('Correct FIP VRF Entries seen ')
        else:
            result = False
            assert result, 'Incorrect FIP VRF Entries seen'

        self.logger.info(
            'The FIP address assigned to %s is %s, to %s is %s and to %s is %s' %
            (vm1.vm_name, fip_addr_vm1, vm2.vm_name, fip_addr_vm2, vm3.vm_name, fip_addr_vm3))
        if all(x == my_fip for x in (fip_addr_vm1, fip_addr_vm2, fip_addr_vm3)):
            self.logger.info('FIP Address assigned correctly ')
        else:
            result = False
            assert result, 'FIP Address assignment incorrect'

        self.logger.info('Check for the FIP route entry')

        for vm_node_ip in vm_node_ips:
            tap_intf_list = []
            inspect_h9 = self.agent_inspect[vm_node_ip]
            agent_vrf_objs = inspect_h9.get_vna_vrf_objs(domain, project, fvn)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.res.fvn_vrf_name)
            fvn_vrf_id9 = agent_vrf_obj['ucindex']
            paths = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=self.res.my_fip, prefix='32')['path_list']
            self.logger.info('There are %s nexthops to %s on Agent %s' %
                             (len(paths), self.res.my_fip, vm_node_ip))
            next_hops = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=self.res.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']

            if not next_hops:
                result = False
                assert result, 'Route not found in the Agent %s' % vm_node_ip
            else:
                self.logger.info('Route found in the Agent %s' % vm_node_ip)

            for nh in next_hops:
                label = nh['label']
                if nh['type'] == 'Tunnel':
                    destn_agent = nh['dip']
                    inspect_hh = self.agent_inspect[destn_agent]
                    agent_vrf_objs = inspect_hh.get_vna_vrf_objs(
                        domain, project, fvn)
                    agent_vrf_obj = self.get_matching_vrf(
                        agent_vrf_objs['vrf_list'], self.res.fvn_vrf_name)
                    fvn_vrf_id5 = agent_vrf_obj['ucindex']
                    next_hops_in_tnl = inspect_hh.get_vna_active_route(
                        vrf_id=fvn_vrf_id5, ip=self.res.my_fip, prefix='32')['path_list'][0]['nh']['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl = next_hop['itf']
                            tap_intf_list.append(tap_intf_from_tnl)
                elif nh['type'] == 'Interface':
                    tap_intf = nh['itf']
                    tap_intf_list.append(tap_intf)

            agent_tap_intf_list[vm_node_ip] = tap_intf_list
        self.logger.info('The list of Tap interfaces from the agents are %s' %
                         agent_tap_intf_list)
#        a_list= agent_tap_intf_list.values()
#        result= all(x == a_list[0] for x in a_list)
#
#        if result == True:
#            self.logger.info('The Tap interface list is the same across agents')
#        else:
#            assert result, 'The Tap interface list across agents is incorrect'

        for stream in stream_list:
            for vm in vm_list:
                sender[stream][vm].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()
        sleep(10)
        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for vm in vm_list:
                stream_sent_count[stream] = stream_sent_count[stream] + \
                    sender[stream][vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5:
                self.logger.info(
                    '%s packets sent and %s packets received in Stream after associating the FIP address back' %
                    (stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result = False
                assert result, '%s packets sent and %s packets received in Stream after associating the FIP address back' % (
                    stream_sent_count[stream], stream_recv_count[stream])

        self.logger.info('Checking Flow Records')

        flow_result = False
        flow_result2 = False
        flow_result3 = False

        rev_flow_result = False
        rev_flow_result1 = False
        rev_flow_result2 = False

        vn1_vrf_id = vm1.get_vrf_id(
            self.res.vn1_fq_name, self.res.vn1_vrf_name)
        vn2_vrf_id = vm2.get_vrf_id(
            self.res.vn2_fq_name, self.res.vn2_vrf_name)
        vn3_vrf_id = vm3.get_vrf_id(
            self.res.vn3_fq_name, self.res.vn3_vrf_name)
        fvn_vrf_id = fvn_vm1.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)

        for vm_node_ip in vm_node_ips:
            inspect_h100 = self.agent_inspect[vm_node_ip]
            flow_rec1 = None
            flow_rec2 = None
            flow_rec3 = None
            dpi1 = unicode(self.res.dport1)
            dpi2 = unicode(self.res.dport2)
            dpi3 = unicode(self.res.dport3)
            flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi1, protocol='6')
            flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi2, protocol='6')
            flow_rec3 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi3, protocol='6')
            if flow_rec1 is not None:
                flow_result = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result = flow_result or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))

            if flow_rec2 is not None:
                flow_result2 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2, vm_node_ip))
            else:
                flow_result2 = flow_result2 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2, vm_node_ip))

            if flow_rec3 is not None:
                flow_result3 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3, vm_node_ip))
            else:
                flow_result3 = flow_result3 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3, vm_node_ip))

            dpi_list = [dpi1, dpi2, dpi3]
            rev_flow_rec1 = {}
            rev_flow_rec2 = {}
            rev_flow_rec3 = {}
            rev_flow_result1 = True
            rev_flow_result2 = True
            rev_flow_result3 = True

            for dpi in dpi_list:
                rev_flow_rec1[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                rev_flow_rec2[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn2_vrf_id, sip=vm2.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                rev_flow_rec3[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn3_vrf_id, sip=vm3.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                if rev_flow_rec1[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result1 = rev_flow_result1 or False
                if rev_flow_rec2[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm2.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result2 = rev_flow_result2 or False
                if rev_flow_rec3[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm3.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result3 = rev_flow_result3 or False

        assert flow_result, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert flow_result2, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2)
        assert flow_result3, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3)
        assert (
            rev_flow_result3 or rev_flow_result1 or rev_flow_result2), 'Records for the reverse flow not seen on any of the agents'

        return True
    # end test_ecmp_bw_three_vms_same_fip_delete_add_fip

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip_incr_sport(self):
        '''Test communication between three VMs who have borrowed the FIP from common FIP pool. Increment sport and have 3 flows setup.
        '''
        result = True
        self.fip_pool_name = self.res.fip_pool_name
        fvn = self.res.fvn
        vn1 = self.res.vn1
        vn2 = self.res.vn2
        vn3 = self.res.vn3
        my_fip = self.res.my_fip
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = self.res.dport1
        dport2 = self.res.dport2
        dport3 = self.res.dport3
        udp_src = self.res.udp_src
        vm1 = self.res.vm1
        vm2 = self.res.vm2
        vm3 = self.res.vm3
        fvn_vm1 = self.res.fvn_vm1

        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip):
            vm_node_ips.append(vm3.vm_node_ip)

        self.logger.info("-" * 100)
        self.logger.info(
            'Starting the following UDP flows : %s:10000-->30.1.1.3, %s:11000-->30.1.1.3, %s:12000-->30.1.1.3' %
            (fvn_vm1.vm_ip, fvn_vm1.vm_ip, fvn_vm1.vm_ip))
        self.logger.info("-" * 100)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        fvm_list = [fvn_vm1]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="udp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=unicode(10000), dport=dport1)
        stream2 = Stream(protocol="ip", proto="udp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=unicode(11000), dport=dport1)
        stream3 = Stream(protocol="ip", proto="udp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=unicode(12000), dport=dport1)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0

        for stream in stream_list:
            profile[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                recv_filename = 'recvudp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
        for i in range(len(stream_list)):
            profile[i] = {}
            sender[i] = {}
            count = count + 1
            send_filename = 'sendudp_%s' % count
            profile[i] = ContinuousProfile(stream=stream_list[i], chksum=True)
            sender[i] = Sender(send_filename, profile[i],
                               tx_local_host, send_host, self.inputs.logger)
            sender[i].start()

        self.logger.info('Sending traffic for 10 seconds')
        sleep(10)
        for i in range(len(stream_list)):
            sender[i].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = 0
        stream_recv_total_count = 0
        stream_recv_count = {}
        result = True
        for i in range(len(stream_list)):
            self.logger.info('%s packets sent in Stream_%s' %
                             (sender[i].sent, i))
            if sender[i].sent == None:
                sender[i].sent = 0
            stream_sent_count = stream_sent_count + sender[i].sent
        self.logger.info('Total %s packets sent out.' % stream_sent_count)
        for stream in stream_list:
            stream_recv_count[stream] = 0
            for vm in vm_list:
                if receiver[stream][vm].recv == None:
                    receiver[stream][vm].recv = 0
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            self.logger.info('%s packets received in Stream_%s' %
                             (stream_recv_count[stream], stream))
            stream_recv_total_count = stream_recv_total_count + \
                stream_recv_count[stream]
        self.logger.info('Total %s packets received.' %
                         stream_recv_total_count)
        if abs(stream_recv_total_count - stream_sent_count) < 5:
            self.logger.info('No Packet Loss Seen')
        else:
            self.logger.info('Packet Loss Seen')

        # Checking Flow Records

        flow_result = False
        flow_result2 = False
        flow_result3 = False

        rev_flow_result = False
        rev_flow_result1 = False
        rev_flow_result2 = False

        vn1_vrf_id = vm1.get_vrf_id(
            self.res.vn1_fq_name, self.res.vn1_vrf_name)
        vn2_vrf_id = vm2.get_vrf_id(
            self.res.vn2_fq_name, self.res.vn2_vrf_name)
        vn3_vrf_id = vm3.get_vrf_id(
            self.res.vn3_fq_name, self.res.vn3_vrf_name)
        fvn_vrf_id = fvn_vm1.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)

        for vm_node_ip in vm_node_ips:
            inspect_h100 = self.agent_inspect[vm_node_ip]
            flow_rec1 = None
            flow_rec2 = None
            flow_rec3 = None
            dpi1 = unicode(self.res.dport1)
            dpi2 = unicode(self.res.dport2)
            dpi3 = unicode(self.res.dport3)
            flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=unicode(10000), dport=dpi1, protocol='17')
            flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=unicode(11000), dport=dpi1, protocol='17')
            flow_rec3 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=unicode(12000), dport=dpi1, protocol='17')
            if flow_rec1 is not None:
                flow_result = True
                self.logger.info(
                    'Flow from %s:10000 to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result = flow_result or False
                self.logger.info('No Flow from %s:10000 to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.my_fip, dpi1, vm_node_ip))

            if flow_rec2 is not None:
                flow_result2 = True
                self.logger.info(
                    'Flow from %s:11000 to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.my_fip, dpi2, vm_node_ip))
            else:
                flow_result2 = flow_result2 or False
                self.logger.info('No Flow from %s:11000 to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.my_fip, dpi2, vm_node_ip))

            if flow_rec3 is not None:
                flow_result3 = True
                self.logger.info(
                    'Flow from %s:12000 to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.my_fip, dpi3, vm_node_ip))
            else:
                flow_result3 = flow_result3 or False
                self.logger.info('No Flow from %s:12000 to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.my_fip, dpi3, vm_node_ip))

            dpi_list = [dpi1]
            rev_flow_rec1 = {}
            rev_flow_rec2 = {}
            rev_flow_rec3 = {}
            rev_flow_result1 = True
            rev_flow_result2 = True
            rev_flow_result3 = True
            for dpi in dpi_list:
                rev_flow_rec1[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=unicode(10000), protocol='17')
                rev_flow_rec2[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn2_vrf_id, sip=vm2.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=unicode(11000), protocol='17')
                rev_flow_rec3[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn3_vrf_id, sip=vm3.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=unicode(12000), protocol='17')
                if rev_flow_rec1[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result1 = rev_flow_result1 or False
                if rev_flow_rec2[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm2.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result2 = rev_flow_result2 or False
                if rev_flow_rec3[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm3.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result3 = rev_flow_result3 or False

        assert flow_result, 'Records for the flow between %s:%s and %s:10000 not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert flow_result2, 'Records for the flow between %s:%s and %s:11000 not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2)
        assert flow_result3, 'Records for the flow between %s:%s and %s:12000 not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3)
        assert (
            rev_flow_result3 or rev_flow_result1 or rev_flow_result2), 'Records for the reverse flow not seen on any of the agents'

        return True

    # end test_ecmp_bw_three_vms_same_fip_incr_sport

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip_incr_sip(self):
        '''Test communication between three VMs who have borrowed the FIP from common FIP pool. Increment SIP and have 3 flows setup.
        '''
        result = True
        self.fip_pool_name = self.res.fip_pool_name
        fvn = self.res.fvn
        vn1 = self.res.vn1
        vn2 = self.res.vn2
        vn3 = self.res.vn3
        my_fip = self.res.my_fip
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = self.res.dport1
        dport2 = self.res.dport2
        dport3 = self.res.dport3
        udp_src = self.res.udp_src
        vm1 = self.res.vm1
        vm2 = self.res.vm2
        vm3 = self.res.vm3
        fvn_vm1 = self.res.fvn_vm1
        fvn_vm2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.res.fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_vm2'))
        assert fvn_vm2.verify_on_setup()
        fvn_vm3 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.res.fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_vm3'))
        assert fvn_vm3.verify_on_setup()

        fvm_list = [fvn_vm2, fvn_vm3]
        for vm in fvm_list:
            out = vm.wait_till_vm_is_up()
            if out == False:
                return {'result': out, 'msg': "%s failed to come up" % vm.vm_name}
            else:
                sleep(5)
                self.logger.info('Installing Traffic package on %s ...' %
                                 vm.vm_name)
                vm.install_pkg("Traffic")

        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip):
            vm_node_ips.append(vm3.vm_node_ip)
        self.logger.info("-" * 100)
        self.logger.info(
            'Starting the following UDP flows : %s-->30.1.1.3, %s-->30.1.1.3, %s-->30.1.1.3' %
            (fvn_vm1.vm_ip, fvn_vm2.vm_ip, fvn_vm3.vm_ip))
        self.logger.info("-" * 100)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        fvm_list = [fvn_vm1, fvn_vm2, fvn_vm3]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="udp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="udp", src=fvn_vm2.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream3 = Stream(protocol="ip", proto="udp", src=fvn_vm3.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = {}
        tx_local_host = {}
        send_host = {}

        for fvm in fvm_list:
            tx_vm_node_ip[fvm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(fvm.vm_obj)]['host_ip']
            tx_local_host[fvm] = Host(
                tx_vm_node_ip[fvm],
                self.inputs.host_data[fvm.vm_node_ip]['username'],
                self.inputs.host_data[fvm.vm_node_ip]['password'])
            send_host[fvm] = Host(
                fvm.local_ip, fvm.vm_username, fvm.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0

        for stream in stream_list:
            profile[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                recv_filename = 'recvudp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
        for i in range(len(stream_list)):
            profile[i] = {}
            sender[i] = {}
            count = count + 1
            send_filename = 'sendudp_%s' % count
            profile[i] = ContinuousProfile(stream=stream_list[i], chksum=True)
            sender[i] = Sender(send_filename, profile[i], tx_local_host[
                               fvm_list[i]], send_host[fvm_list[i]], self.inputs.logger)
            sender[i].start()

        self.logger.info('Sending traffic for 10 seconds')
        sleep(10)
        for i in range(len(stream_list)):
            sender[i].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = 0
        stream_recv_total_count = 0
        stream_recv_count = {}
        result = True
        for i in range(len(stream_list)):
            self.logger.info('%s packets sent in Stream_%s' %
                             (sender[i].sent, i))
            if sender[i].sent == None:
                sender[i].sent = 0
            stream_sent_count = stream_sent_count + sender[i].sent
        self.logger.info('Total %s packets sent out.' % stream_sent_count)
        for stream in stream_list:
            stream_recv_count[stream] = 0
            for vm in vm_list:
                if receiver[stream][vm].recv == None:
                    receiver[stream][vm].recv = 0
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            self.logger.info('%s packets received in Stream_%s' %
                             (stream_recv_count[stream], stream))
            stream_recv_total_count = stream_recv_total_count + \
                stream_recv_count[stream]
        self.logger.info('Total %s packets received.' %
                         stream_recv_total_count)
        if abs(stream_recv_total_count - stream_sent_count) < 5:
            self.logger.info('No Packet Loss Seen')
        else:
            self.logger.info('Packet Loss Seen')

        # Checking Flow Records

        flow_result = False
        flow_result2 = False
        flow_result3 = False

        rev_flow_result = False
        rev_flow_result1 = False
        rev_flow_result2 = False

        vn1_vrf_id = vm1.get_vrf_id(
            self.res.vn1_fq_name, self.res.vn1_vrf_name)
        vn2_vrf_id = vm2.get_vrf_id(
            self.res.vn2_fq_name, self.res.vn2_vrf_name)
        vn3_vrf_id = vm3.get_vrf_id(
            self.res.vn3_fq_name, self.res.vn3_vrf_name)
        fvn_vrf_id_1 = fvn_vm1.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)
        fvn_vrf_id_2 = fvn_vm2.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)
        fvn_vrf_id_3 = fvn_vm3.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)

        for vm_node_ip in vm_node_ips:
            inspect_h100 = self.agent_inspect[vm_node_ip]
            flow_rec1 = None
            flow_rec2 = None
            flow_rec3 = None
            dpi1 = unicode(self.res.dport1)
            dpi2 = unicode(self.res.dport2)
            dpi3 = unicode(self.res.dport3)
            flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id_1, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi1, protocol='17')
            flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id_2, sip=fvn_vm2.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi1, protocol='17')
            flow_rec3 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id_3, sip=fvn_vm3.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi1, protocol='17')
            if flow_rec1 is not None:
                flow_result = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result = flow_result or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))

            if flow_rec2 is not None:
                flow_result2 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm2.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result2 = flow_result2 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm2.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))

            if flow_rec3 is not None:
                flow_result3 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm3.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result3 = flow_result3 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm3.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))

            dpi_list = [dpi1]
            rev_flow_rec1 = {}
            rev_flow_rec2 = {}
            rev_flow_rec3 = {}
            rev_flow_result1 = True
            rev_flow_result2 = True
            rev_flow_result3 = True
            for dpi in dpi_list:
                rev_flow_rec1[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='17')
                rev_flow_rec2[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn2_vrf_id, sip=vm2.vm_ip, dip=fvn_vm2.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='17')
                rev_flow_rec3[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn3_vrf_id, sip=vm3.vm_ip, dip=fvn_vm3.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='17')
                if rev_flow_rec1[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result1 = rev_flow_result1 or False
                if rev_flow_rec2[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm2.vm_ip, fvn_vm2.vm_ip, vm_node_ip))
                    rev_flow_result2 = rev_flow_result2 or False
                if rev_flow_rec3[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm3.vm_ip, fvn_vm3.vm_ip, vm_node_ip))
                    rev_flow_result3 = rev_flow_result3 or False

        assert flow_result, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert flow_result2, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm2.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert flow_result3, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm3.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert (
            rev_flow_result3 or rev_flow_result1 or rev_flow_result2), 'Records for the reverse flow not seen on any of the agents'

        return True

    # end test_ecmp_bw_three_vms_same_fip_incr_sip

    @preposttest_wrapper
    def test_ecmp_bw_three_vms_same_fip(self):
        '''Test communication between three VMs who have borrowed the FIP from common FIP pool.
        '''
        result = True
        self.fip_pool_name = self.res.fip_pool_name
        fvn = self.res.fvn
        vn1 = self.res.vn1
        vn2 = self.res.vn2
        vn3 = self.res.vn3
        my_fip = self.res.my_fip
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = self.res.dport1
        dport2 = self.res.dport2
        dport3 = self.res.dport3
        udp_src = self.res.udp_src
        vm1 = self.res.vm1
        vm2 = self.res.vm2
        vm3 = self.res.vm3
        fvn_vm1 = self.res.fvn_vm1

        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)
        if (vm1.vm_node_ip != vm3.vm_node_ip):
            vm_node_ips.append(vm3.vm_node_ip)

        # Starting two flows of TCP Traffic from fvn_vm1 to 30.1.1.3

        self.logger.info("-" * 80)
        self.logger.info('Starting TCP Traffic from fvn_vm1 to 30.1.1.3')
        self.logger.info("-" * 80)
        vm_list = []
        vm_list = [vm1, vm2, vm3]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport2)
        stream3 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport3)
        stream_list = [stream1, stream2, stream3]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm], 
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                send_filename = 'sendtcp_%s' % count
                recv_filename = 'recvtcp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                sender[stream][vm] = Sender(
                    send_filename, profile[stream][vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
                sender[stream][vm].start()
        self.logger.info('Sending traffic for 10 seconds')
        sleep(10)

        for stream in stream_list:
            for vm in vm_list:
                sender[stream][vm].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for vm in vm_list:
                stream_sent_count[stream] = stream_sent_count[stream] + \
                    sender[stream][vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5:
                self.logger.info(
                    '%s packets sent and %s packets received in Stream' %
                    (stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result = False
                assert result, '%s packets sent and %s packets received in Stream' % (
                    stream_sent_count[stream], stream_recv_count[stream])
        # Checking Flow Records

        flow_result = False
        flow_result2 = False
        flow_result3 = False

        rev_flow_result = False
        rev_flow_result1 = False
        rev_flow_result2 = False

        vn1_vrf_id = vm1.get_vrf_id(
            self.res.vn1_fq_name, self.res.vn1_vrf_name)
        vn2_vrf_id = vm2.get_vrf_id(
            self.res.vn2_fq_name, self.res.vn2_vrf_name)
        vn3_vrf_id = vm3.get_vrf_id(
            self.res.vn3_fq_name, self.res.vn3_vrf_name)
        fvn_vrf_id = fvn_vm1.get_vrf_id(
            self.res.fvn_fq_name, self.res.fvn_vrf_name)

        for vm_node_ip in vm_node_ips:
            inspect_h100 = self.agent_inspect[vm_node_ip]
            flow_rec1 = None
            flow_rec2 = None
            flow_rec3 = None
            dpi1 = unicode(self.res.dport1)
            dpi2 = unicode(self.res.dport2)
            dpi3 = unicode(self.res.dport3)
            flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi1, protocol='6')
            flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi2, protocol='6')
            flow_rec3 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=self.res.my_fip, sport=self.res.udp_src, dport=dpi3, protocol='6')
            if flow_rec1 is not None:
                flow_result = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))
            else:
                flow_result = flow_result or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1, vm_node_ip))

            if flow_rec2 is not None:
                flow_result2 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2, vm_node_ip))
            else:
                flow_result2 = flow_result2 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2, vm_node_ip))

            if flow_rec3 is not None:
                flow_result3 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3, vm_node_ip))
            else:
                flow_result3 = flow_result3 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3, vm_node_ip))

            dpi_list = [dpi1, dpi2, dpi3]
            rev_flow_rec1 = {}
            rev_flow_rec2 = {}
            rev_flow_rec3 = {}
            rev_flow_result1 = True
            rev_flow_result2 = True
            rev_flow_result3 = True

            for dpi in dpi_list:
                rev_flow_rec1[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                rev_flow_rec2[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn2_vrf_id, sip=vm2.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                rev_flow_rec3[dpi] = inspect_h100.get_vna_fetchflowrecord(
                    vrf=vn3_vrf_id, sip=vm3.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi, dport=self.res.udp_src, protocol='6')
                if rev_flow_rec1[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result1 = rev_flow_result1 or False
                if rev_flow_rec2[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm2.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result2 = rev_flow_result2 or False
                if rev_flow_rec3[dpi]:
                    self.logger.info(
                        'Reverse Flow from %s to %s exists on Agent %s' %
                        (vm3.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
                    rev_flow_result3 = rev_flow_result3 or False

        assert flow_result, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi1)
        assert flow_result2, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi2)
        assert flow_result3, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, self.res.udp_src, self.res.my_fip, dpi3)
        assert (
            rev_flow_result3 or rev_flow_result1 or rev_flow_result2), 'Records for the reverse flow not seen on any of the agents'

        return True

    # end test_ecmp_bw_three_vms_same_fip

    @preposttest_wrapper
    def test_ecmp_bw_two_vms_same_fip(self):
        '''Test communication between the VMs who has borrowed the FIP from common FIP pool.
        '''
        result = True
        fip_pool_name = 'some-pool'
        #fvn_name= self.res.fip_vn_name
        fvn = self.useFixture(VNFixture(project_name=self.inputs.project_name,
                              connections=self.connections, vn_name='fvn_1', inputs=self.inputs, subnets=['33.1.1.0/29']))
        vn1 = self.useFixture(VNFixture(project_name=self.inputs.project_name,
                              connections=self.connections, vn_name='vn_1', inputs=self.inputs, subnets=['11.1.1.0/29']))
        #vn2= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='vn2', inputs= self.inputs, subnets=['20.1.1.0/29']))
        my_fip = '33.1.1.3'
        agent_tap_intf_list = {}
        tap_intf_list = []
        a_list = []
        dport1 = '9000'
        dport2 = '9001'
        udp_src = unicode(8000)
        vm1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vn_1_vm_1'))
        vm2 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vn_1_vm_2'))
        fvn_vm1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=fvn.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='fvn_1_vm1'))

        assert fvn.verify_on_setup()
        assert vn1.verify_on_setup()
        assert vm1.verify_on_setup()
        assert vm2.verify_on_setup()
        assert fvn_vm1.verify_on_setup()

        out1 = vm1.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1.vm_name}
        else:
            self.logger.info('Installing Traffic package on %s ...' %
                             vm1.vm_name)
            vm1.install_pkg("Traffic")

        out2 = vm2.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             vm2.vm_name)
            vm2.install_pkg("Traffic")

        out3 = fvn_vm1.wait_till_vm_is_up()
        if out3 == False:
            return {'result': out3, 'msg': "%s failed to come up" % fvn_vm1.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             fvn_vm1.vm_name)
            fvn_vm1.install_pkg("Traffic")

        vn1_fq_name = vn1.vn_fq_name
        fvn_fq_name = fvn.vn_fq_name
        fvn_vrf_name = fvn.vrf_name
        vn1_vrf_name = vn1.vrf_name
        fvn_id = fvn.vn_id
        vm1_id = vm1.vm_id
        vm2_id = vm2.vm_id
        fvn_ri_name = fvn.ri_name
        vn1_ri_name = vn1.ri_name
        (domain, project, fvn) = fvn_fq_name.split(':')
        (domain, project, vn1) = vn1_fq_name.split(':')
        vmi1_id = vm1.tap_intf[vn1_fq_name]['uuid']
        vmi2_id = vm2.tap_intf[vn1_fq_name]['uuid']
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_id))
        assert fip_fixture.verify_on_setup()
        my_fip_name = 'fip'
        fvn_obj = self.vnc_lib.virtual_network_read(id=fvn_id)
        fip_pool_obj = FloatingIpPool(fip_pool_name, fvn_obj)
        fip_obj = FloatingIp(my_fip_name, fip_pool_obj, my_fip, True)

        # Get the project_fixture
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        # Read the project obj and set to the floating ip object.
        fip_obj.set_project(self.project_fixture.project_obj)

        vm1_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi1_id)
        vm2_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi2_id)
        fip_obj.add_virtual_machine_interface(vm1_intf)
        fip_obj.add_virtual_machine_interface(vm2_intf)
        self.vnc_lib.floating_ip_create(fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, fip_obj.fq_name)
        vm_node_ips = []
        vm_node_ips.append(vm1.vm_node_ip)
        if (vm1.vm_node_ip != vm2.vm_node_ip):
            vm_node_ips.append(vm2.vm_node_ip)

        # Get the Route Entry in the control node

        for vm_node_ip in vm_node_ips:
            active_controller = None
            inspect_h1 = self.agent_inspect[vm_node_ip]
            agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes':
                    active_controller = entry['controller_ip']
                    self.logger.info(
                        'Active control node from the Agent %s is %s' %
                        (vm_node_ip, active_controller))
        sleep(5)
        route_entry = self.cn_inspect[active_controller].get_cn_route_table_entry(
            ri_name=fvn_ri_name, prefix='33.1.1.3/32')
        result = True
        self.logger.info('Route_entry in the control node is %s' % route_entry)
        if route_entry:
            self.logger.info(
                'Route Entry found in the Active Control-Node %s' %
                (active_controller))
        else:
            result = False
            assert result, 'Route Entry not found in the Active Control-Node %s' % (
                active_controller)

        # Get the FIP list and verify the vrf_name and address in the VMI

        fip_addr_vm1 = vm1.chk_vmi_for_fip(vn1_fq_name)
        fip_addr_vm2 = vm2.chk_vmi_for_fip(vn1_fq_name)
        fip_vrf_entry_vm1 = vm1.chk_vmi_for_vrf_entry(vn1_fq_name)
        fip_vrf_entry_vm2 = vm2.chk_vmi_for_vrf_entry(vn1_fq_name)

        self.logger.info(
            'The vrf_entry on the VMI of %s is %s and on %s is %s' %
            (vm1.vm_name, fip_vrf_entry_vm1, vm2.vm_name, fip_vrf_entry_vm2))
        if ((fip_vrf_entry_vm1 == fvn_vrf_name) and (fip_vrf_entry_vm2 == fvn_vrf_name)):
            self.logger.info('Correct FIP VRF Entries seen ')
        else:
            result = False
            assert result, 'Incorrect FIP VRF Entries seen'

        self.logger.info(
            'The FIP address assigned to %s is %s and to %s is %s' %
            (vm1.vm_name, fip_addr_vm1, vm2.vm_name, fip_addr_vm2))
        if ((fip_addr_vm1 == my_fip) and (fip_addr_vm2 == my_fip)):
            self.logger.info('FIP Address assigned correctly ')
        else:
            result = False
            assert result, 'FIP Address assignment incorrect'

        # Check for the FIP route entry

        for vm_node_ip in vm_node_ips:
            inspect_h2 = self.agent_inspect[vm_node_ip]
            fvn_vrf_id1 = inspect_h2.get_vna_vrf_objs(
                domain, project, fvn)['vrf_list'][0]['ucindex']
            nh1 = inspect_h2.get_vna_active_route(
                vrf_id=fvn_vrf_id1, ip=my_fip, prefix='32')
            if not nh1:
                result = False
                assert result, 'Route not found in the Agent %s' % vm_node_ip
            else:
                self.logger.info('Route found in the Agent %s' % vm_node_ip)

        # Check for the FIP route entry

        for vm_node_ip in vm_node_ips:
            tap_intf_list = []
            inspect_h9 = self.agent_inspect[vm_node_ip]
            agent_vrf_objs = inspect_h9.get_vna_vrf_objs(domain, project, fvn)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], fvn_vrf_name)
            fvn_vrf_id9 = agent_vrf_obj['ucindex']
            paths = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=my_fip, prefix='32')['path_list']
            self.logger.info('There are %s nexthops to %s on Agent %s' %
                             (len(paths), my_fip, vm_node_ip))
            next_hops = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=my_fip, prefix='32')['path_list'][0]['nh']['mc_list']

            if not next_hops:
                result = False
                assert result, 'Route not found in the Agent %s' % vm_node_ip

            else:
                self.logger.info('Route found in the Agent %s' % vm_node_ip)

            for nh in next_hops:
                label = nh['label']
                if nh['type'] == 'Tunnel':
                    destn_agent = nh['dip']
                    inspect_hh = self.agent_inspect[destn_agent]
                    agent_vrf_objs = inspect_hh.get_vna_vrf_objs(
                        domain, project, fvn)
                    agent_vrf_obj = self.get_matching_vrf(
                        agent_vrf_objs['vrf_list'], fvn_vrf_name)
                    fvn_vrf_id5 = agent_vrf_obj['ucindex']
                    next_hops_in_tnl = inspect_hh.get_vna_active_route(
                        vrf_id=fvn_vrf_id5, ip=my_fip, prefix='32')['path_list'][0]['nh']['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl = next_hop['itf']
                            tap_intf_list.append(tap_intf_from_tnl)
                elif nh['type'] == 'Interface':
                    tap_intf = nh['itf']
                    tap_intf_list.append(tap_intf)

            agent_tap_intf_list[vm_node_ip] = tap_intf_list
        self.logger.info('The list of Tap interfaces from the agents are %s' %
                         agent_tap_intf_list)

#        a_list= agent_tap_intf_list.values()
#        result= all(x == a_list[0] for x in a_list)
#        if result == True:
#            self.logger.info('The Tap interface list is the same across agents')
#        else:
#            assert result, 'The Tap interface list across agents is incorrect'

        # Starting two flows of TCP Traffic from fvn_vm1 to 30.1.1.3

        self.logger.info("-" * 80)
        self.logger.info('Starting TCP Traffic from fvn_vm1 to 30.1.1.3')
        self.logger.info("-" * 80)
        vm_list = []
        vm_list = [vm1, vm2]
        profile = {}
        sender = {}
        receiver = {}

        stream1 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport1)
        stream2 = Stream(protocol="ip", proto="tcp", src=fvn_vm1.vm_ip,
                         dst=my_fip, sport=udp_src, dport=dport2)
        stream_list = [stream1, stream2]

        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(fvn_vm1.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(fvn_vm1.local_ip, fvn_vm1.vm_username,
                         fvn_vm1.vm_password)

        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for vm in vm_list:
            rx_vm_node_ip[vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm] = Host(
                rx_vm_node_ip[vm],
                self.inputs.host_data[vm.vm_node_ip]['username'],
                self.inputs.host_data[vm.vm_node_ip]['password'])
            recv_host[vm] = Host(vm.local_ip, vm.vm_username, vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for vm in vm_list:
                count = count + 1
                send_filename = 'sendtcp_%s' % count
                recv_filename = 'recvtcp_%s' % count
                profile[stream][vm] = ContinuousProfile(
                    stream=stream, listener=vm.vm_ip, chksum=True)
                sender[stream][vm] = Sender(
                    send_filename, profile[stream][vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][vm] = Receiver(
                    recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
                sender[stream][vm].start()
        self.logger.info('Sending traffic for 10 seconds')
        sleep(10)

        for stream in stream_list:
            for vm in vm_list:
                sender[stream][vm].stop()

        for stream in stream_list:
            for vm in vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for vm in vm_list:
                stream_sent_count[stream] = stream_sent_count[stream] + \
                    sender[stream][vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + \
                    receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5:
                self.logger.info(
                    '%s packets sent and %s packets received in Stream' %
                    (stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result = False
                assert result, '%s packets sent and %s packets received in Stream' % (
                    stream_sent_count[stream], stream_recv_count[stream])

        # Checking Flow Records

        flow_result = False
        flow_result2 = False

        rev_flow_result = False
        rev_flow_result1 = False

        vn1_vrf_id = vm1.get_vrf_id(vn1_fq_name, vn1_vrf_name)
        vn2_vrf_id = vm2.get_vrf_id(vn1_fq_name, vn1_vrf_name)
        fvn_vrf_id = fvn_vm1.get_vrf_id(fvn_fq_name, fvn_vrf_name)
        for vm_node_ip in vm_node_ips:
            inspect_h100 = self.agent_inspect[vm_node_ip]
            flow_rec1 = None
            flow_rec2 = None
            dpi1 = unicode(dport1)
            dpi2 = unicode(dport2)
            flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=my_fip, sport=udp_src, dport=dpi1, protocol='6')
            flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=fvn_vrf_id, sip=fvn_vm1.vm_ip, dip=my_fip, sport=udp_src, dport=dpi2, protocol='6')
            if flow_rec1 is not None:
                assert not flow_result, 'Duplicate Flow detected'
                flow_result = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, udp_src, my_fip, dpi1, vm_node_ip))
            else:
                flow_result = flow_result or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, udp_src, my_fip, dpi1, vm_node_ip))

            if flow_rec2 is not None:
                assert not flow_result2, 'Duplicate Flow detected'
                flow_result2 = True
                self.logger.info(
                    'Flow from %s:%s to %s:%s exists on Agent %s' %
                    (fvn_vm1.vm_ip, udp_src, my_fip, dpi2, vm_node_ip))
            else:
                flow_result2 = flow_result2 or False
                self.logger.info('No Flow from %s:%s to %s:%s on Agent %s' %
                                 (fvn_vm1.vm_ip, udp_src, my_fip, dpi2, vm_node_ip))

            rev_flow_rec1 = inspect_h100.get_vna_fetchflowrecord(
                vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi1, dport=udp_src, protocol='6')
            rev_flow_rec2 = inspect_h100.get_vna_fetchflowrecord(
                vrf=vn1_vrf_id, sip=vm1.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi2, dport=udp_src, protocol='6')

            if (rev_flow_rec1 or rev_flow_rec2):
                assert not rev_flow_result, 'Duplicate Reverse Flow detected'
                rev_flow_result = True
                self.logger.info(
                    'Reverse flow records between %s and %s seen properly on Agent %s' %
                    (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
            else:
                rev_flow_result = rev_flow_result or False
                self.logger.info(
                    'Reverse flow records between %s and %s not seen on Agent %s' %
                    (vm1.vm_ip, fvn_vm1.vm_ip, vm_node_ip))

            rev_flow_rec3 = inspect_h100.get_vna_fetchflowrecord(
                vrf=vn1_vrf_id, sip=vm2.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi1, dport=udp_src, protocol='6')
            rev_flow_rec4 = inspect_h100.get_vna_fetchflowrecord(
                vrf=vn1_vrf_id, sip=vm2.vm_ip, dip=fvn_vm1.vm_ip, sport=dpi2, dport=udp_src, protocol='6')

            if (rev_flow_rec3 or rev_flow_rec4):
                assert not rev_flow_result1, 'Duplicate Reverse Flow detected'
                rev_flow_result1 = True
                self.logger.info(
                    'Reverse flow records between %s and %s seen properly on Agent %s' %
                    (vm2.vm_ip, fvn_vm1.vm_ip, vm_node_ip))
            else:
                rev_flow_result1 = rev_flow_result1 or False
                self.logger.info(
                    'Reverse flow records between %s and %s not seen on Agent %s' %
                    (vm2.vm_ip, fvn_vm1.vm_ip, vm_node_ip))

        assert flow_result, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, udp_src, my_fip, dpi1)
        assert flow_result2, 'Records for the flow between %s:%s and %s:%s not seen on any of the agents' % (
            fvn_vm1.vm_ip, udp_src, my_fip, dpi2)

        assert (
            rev_flow_result or rev_flow_result1), 'Records for the reverse flow not seen on any of the agents'

        return True
    # end test_ecmp_bw_two_vms_same_fip

    def get_matching_vrf(self, vrf_objs, vrf_name):
        return [x for x in vrf_objs if x['name'] == vrf_name][0]

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            # break
    # end remove_from_cleanups

# end TestECMP
