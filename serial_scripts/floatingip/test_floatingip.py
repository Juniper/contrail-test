# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import re
import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import fixtures
import testtools
import unittest
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from tcutils.commands import *
from testresources import ResourcedTestCase
import traffic_tests
from fabric.context_managers import settings
from fabric.api import run
import base
import test


class FloatingipTestSanity_restart(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity_restart, cls).setUpClass()

    @test.attr(type='serial')	
    @preposttest_wrapper
    def test_service_restart_with_fip(self):
        '''Test restart of agent and control service with floating IP
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')
        (self.vn1_name, self.vn1_subnets) = (
            get_random_name("vn1"), ["11.1.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = (
            get_random_name("vn2"), ["22.1.1.0/24"])
        (self.fvn_public_name, self.fvn_public_subnets) = (
            get_random_name("fip_vn_public"), ['10.204.219.16/28'])
        (self.fvn1_name, self.fvn1_subnets) = (
            get_random_name("fip_vn1"), ['100.1.1.0/24'])
        (self.fvn2_name, self.fvn2_subnets) = (
            get_random_name("fip_vn2"), ['200.1.1.0/24'])
        (self.fvn3_name, self.fvn3_subnets) = (
            get_random_name("fip_vn3"), ['170.1.1.0/29'])
        (self.vn1_vm1_name, self.vn1_vm2_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        (self.vn2_vm1_name, self.vn2_vm2_name) = (
            get_random_name('vn2_vm1'), get_random_name('vn2_vm2'))
        (self.fvn_public_vm1_name) = (get_random_name('fvn_public_vm1'))
        (self.fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (self.fvn2_vm1_name) = (get_random_name('fvn2_vm1'))
        (self.fvn3_vm1_name) = (get_random_name('fvn3_vm1'))
        (self.vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (self.fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')
        # Get all compute host
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        fip_pool_name1 = get_random_name('some-pool1')
        fip_pool_name2 = get_random_name('some-pool2')

        self.fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.fvn1_name,
                subnets=self.fvn1_subnets))
        self.fvn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.fvn2_name,
                subnets=self.fvn2_subnets))
        self.fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.fvn1_fixture.obj,
                vm_name=self.fvn1_vm1_name,
                node_name=compute_2))

        self.fvn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.fvn2_fixture.obj,
                vm_name=self.fvn2_vm1_name,
                node_name=compute_1))

        #fvn_name= self.res.fip_vn_name
        fvn1_fixture = self.fvn1_fixture
        fvn2_fixture = self.fvn2_fixture
        fvn1_vm1_fixture = self.fvn1_vm1_fixture
        fvn1_subnets = self.fvn1_subnets
        fvn1_vm1_name = self.fvn1_vm1_name
        fvn2_vm1_fixture = self.fvn2_vm1_fixture
        fvn2_subnets = self.fvn2_subnets
        fvn2_vm1_name = self.fvn2_vm1_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, fvn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, fvn2_vm1_fixture, fvn1_fixture)

        fip_fixture2 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name2,
                vn_id=fvn2_fixture.vn_id))
        assert fip_fixture2.verify_on_setup()
        fip_id2 = fip_fixture2.create_and_assoc_fip(
            fvn2_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture2.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture2.verify_fip(fip_id2, fvn1_vm1_fixture, fvn2_fixture)

        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        self.logger.info('Will restart compute  services now')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        sleep(10)
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        self.logger.info('Will restart control services now')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        sleep(10)
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        if not result:
            self.logger.error(
                'Test Failed for restart of agent and control node with floating IP')
            assert result
        return result
    # end test_service_restart_with_fip

    @preposttest_wrapper
    def test_traffic_with_control_node_switchover(self):
        ''' Stop the control node and check peering with agent fallback to other control node.

        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (self.vn1_name, self.vn1_subnets) = (
            get_random_name("vn1"), ["11.1.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = (
            get_random_name("vn2"), ["22.1.1.0/24"])
        (self.fvn_public_name, self.fvn_public_subnets) = (
            get_random_name("fip_vn_public"), ['10.204.219.16/28'])
        (self.fvn1_name, self.fvn1_subnets) = (
            get_random_name("fip_vn1"), ['100.1.1.0/24'])
        (self.fvn2_name, self.fvn2_subnets) = (
            get_random_name("fip_vn2"), ['200.1.1.0/24'])
        (self.fvn3_name, self.fvn3_subnets) = (
            get_random_name("fip_vn3"), ['170.1.1.0/29'])
        (self.vn1_vm1_name, self.vn1_vm2_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        (self.vn2_vm1_name, self.vn2_vm2_name) = (
            get_random_name('vn2_vm1'), get_random_name('vn2_vm2'))
        (self.fvn_public_vm1_name) = (get_random_name('fvn_public_vm1'))
        (self.fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (self.fvn2_vm1_name) = (get_random_name('fvn2_vm1'))
        (self.fvn3_vm1_name) = (get_random_name('fvn3_vm1'))
        (self.vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (self.fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')
        fip_pool_name1 = get_random_name('some-pool1')
        fip_pool_name2 = get_random_name('some-pool2')

        # Get all compute host
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        self.fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.fvn1_name,
                subnets=self.fvn1_subnets))
        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))

        self.fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.fvn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=self.fvn1_vm1_traffic_name,
                node_name=compute_2))
        self.vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=self.vn1_vm1_traffic_name,
                node_name=compute_1))

        fvn1_fixture = self.fvn1_fixture
        fvn1_vm1_traffic_fixture = self.fvn1_vm1_traffic_fixture
        fvn1_subnets = self.fvn1_subnets
        fvn1_vm1_traffic_name = self.fvn1_vm1_traffic_name
        vn1_fixture = self.vn1_fixture
        vn1_vm1_traffic_fixture = self.vn1_vm1_traffic_fixture
        vn1_subnets = self.vn1_subnets
        vn1_vm1_traffic_name = self.vn1_vm1_traffic_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(
                fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        # Figuring the active control node
        active_controller = None
        inspect_h = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        self.logger.info(
            'Active control node from the Agent %s is %s' %
            (vn1_vm1_traffic_fixture.vm_node_ip, active_controller))

        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams[
            'icmp'] = 1
        dpi = 9100
        proto = 'icmp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture,
                rx_vm_fixture=fvn1_vm1_traffic_fixture,
                stream_proto=proto)
            self.logger.info(
                "Status of start traffic : %s, %s, %s" %
                (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status']), err_msg
        self.logger.info("-" * 80)

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller))
        self.inputs.stop_service('contrail-control', [active_controller])
        sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']

        self.logger.info(
            'Active control node from the Agent %s is %s' %
            (vn1_vm1_traffic_fixture.vm_node_ip, new_active_controller))
        if new_active_controller == active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller, new_active_controller))
            result = False
        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = unicode(8000)
        dpi = unicode(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        vn_fq_name=vn1_vm1_traffic_fixture.vn_fq_name
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=vn1_vm1_traffic_fixture.vm_ip,
            dip=fvn1_vm1_traffic_fixture.vm_ip,
            sport='0',
            dport='0',
            protocol='1')

        if flow_rec1 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' %
                    (flow_rec1))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'direction', 'ingress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be ingress. Flow details %s' %
                    (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required ingress Traffic flow not found')
            result = result and False

        # Verify Egress Traffic
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        self.logger.info('Verifying Egress Flow Records')
        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=fvn1_vm1_traffic_fixture.vm_ip,
            dip=fip_fixture1.fip[fip_id1],
            sport='0',
            dport='0',
            protocol='1')
        
        if flow_rec2 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' %
                    (flow_rec2))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'direction', 'egress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be Egress. Flow details %s' %
                    (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required Egress Traffic flow not found')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            #if stopStatus[proto] != []: msg.append(stopStatus[proto]); result= False
            if stopStatus[proto] != []:
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller))
        self.inputs.start_service('contrail-control', [active_controller])

        sleep(10)
        # Check the BGP peering status from the currently active control node
        self.logger.info(
            'Checking the BGP peering from new active controler  %s' %
            (new_active_controller))
        cn_bgp_entry = self.cn_inspect[
            new_active_controller].get_cn_bgp_neigh_entry()
        sleep(5)
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

        # fip_fixture1.disassoc_and_delete_fip(fip_id1)
        if not result:
            self.logger.error('Switchover of control node failed')
            assert result
        return True
    # end test_traffic_with_control_node_switchover






                                                                                                                                          

