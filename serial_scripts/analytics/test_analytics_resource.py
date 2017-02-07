import os
import time
import fixtures
import testtools
import re
from vn_test import *
from vm_test import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper

sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, StandardProfile, BurstProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver

from common.servicechain.verify import VerifySvcChain
from fabric.api import run, local
from analytics import base
import fixtures

import test
import pprint

class AnalyticsTestSanityWithResource(
        base.AnalyticsBaseTest,
        VerifySvcChain):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanityWithResource, cls).setUpClass()
        cls.res.setUp(cls.inputs, cls.connections)

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(AnalyticsTestSanityWithResource, cls).tearDownClass()
    # end tearDownClass

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_object_log_verification_with_delete_add_in_network_mode(self):
        """Verifying the uve and object log for service instance and service template"""

        #self.vn1_fq_name = "default-domain:admin:" + self.res.vn1_name
        self.vn1_fq_name = self.res.vn1_fixture.vn_fq_name
        self.vn1_name = self.res.vn1_name
        self.vn1_subnets = self.res.vn1_fixture.get_cidrs(af='v4')
        self.vm1_name = self.res.vn1_vm1_name
        #self.vn2_fq_name = "default-domain:admin:" + self.res.vn2_name
        self.vn2_fq_name = self.res.vn2_fixture.vn_fq_name
        self.vn2_name = self.res.vn2_name
        self.vn2_subnets = self.res.vn2_fixture.get_cidrs(af='v4')
        self.vm2_name = self.res.vn2_vm2_name
        self.action_list = []
        self.if_list = [['management', False], ['left', True], ['right', True]]
        self.st_name = 'in_net_svc_template_1'
        si_count = 1
        svc_scaling = False
        max_inst = 1
        svc_mode = 'in-network'

        self.policy_name = 'policy_in_network'
        result = True
        try:
            start_time = self.analytics_obj.getstarttime(self.inputs.cfgm_ip)
            if getattr(self, 'res', None):
                self.vn1_fixture = self.res.vn1_fixture
                self.vn2_fixture = self.res.vn2_fixture
                assert self.vn1_fixture.verify_on_setup()
                assert self.vn2_fixture.verify_on_setup()
            else:
                self.vn1_fixture = self.config_vn(
                    self.vn1_name,
                    self.vn1_subnets)
                self.vn2_fixture = self.config_vn(
                    self.vn2_name,
                    self.vn2_subnets)
            svc_chain_info = self.config_svc_chain(
                left_vn_fixture=self.vn1_fixture,
                right_vn_fixture=self.vn2_fixture,
                max_inst=max_inst,
                st_name=self.st_name,
                service_mode=svc_mode)
            self.st_fixture = svc_chain_info['st_fixture']
            self.si_fixture = svc_chain_info['si_fixture']

            self.si_fixture.verify_on_setup()

            domain, project, name = self.si_fixture.si_fq_name
            si_name = ':'.join(self.si_fixture.si_fq_name)
            # Getting nova uuid of the service instance
            try:
                assert self.analytics_obj.verify_service_chain_uve(self.vn1_fq_name,
                                                            self.vn2_fq_name,
                                                            services = [si_name])
            except Exception as e:
                self.logger.warn(
                    "service chain uve not shown in analytics")
                result = result and False

            service_chain_name = self.analytics_obj.\
                                    get_service_chain_name(self.vn1_fq_name,
                                                          self.vn2_fq_name,
                                                          services = [si_name])
                
            try:
                assert self.analytics_obj.verify_vn_uve_ri(
                    vn_fq_name=self.vn1_fixture.vn_fq_name,
                    ri_name = service_chain_name)
            except Exception as e:
                self.logger.warn(
                    "internal ri not shown in %s uve" %
                    (self.vn1_fixture.vn_fq_name))
                result = result and False

            try:
                assert self.analytics_obj.verify_vn_uve_ri(
                    vn_fq_name=self.vn2_fixture.vn_fq_name,
                    ri_name = service_chain_name)
            except Exception as e:
                self.logger.warn(
                    "internal ri not shown in %s uve" %
                    (self.vn2_fixture.vn_fq_name))
                result = result and False
            try:
                assert self.analytics_obj.verify_connected_networks_in_vn_uve(
                    self.vn1_fixture. vn_fq_name,
                    self.vn2_fixture.vn_fq_name)
            except Exception as e:
                self.logger.warn("Connected networks not shown properly \
                        in %s uve" % (self.vn1_fixture.vn_fq_name))
                result = result and False
            try:
                assert self.analytics_obj.verify_connected_networks_in_vn_uve\
                    (self.vn2_fixture.vn_fq_name, self.vn1_fixture.vn_fq_name)
            except Exception as e:
                self.logger.warn("Connected networks not shown properly in %s\
                    uve" % (self.vn2_fixture.vn_fq_name))
                result = result and False

            si_uuids = []
            for el in self.si_fixture.si_obj.get_virtual_machine_back_refs():
                si_uuids.append(el['uuid'])

            for si_uuid in si_uuids:
                try:
                    assert self.analytics_obj.verify_vm_list_in_vn_uve(
                        vn_fq_name=self.vn1_fixture.vn_fq_name,
                        vm_uuid_lst=[si_uuid])
                except Exception as e:
                    self.logger.warn(
                        "Service instance not shown in %s uve" %
                        (self.vn1_fixture.vn_fq_name))
                    result = result and False
                try:
                    assert self.analytics_obj.verify_vm_list_in_vn_uve(
                        vn_fq_name=self.vn2_fixture.vn_fq_name,
                        vm_uuid_lst=[si_uuid])
                except Exception as e:
                    self.logger.warn("Service instance not shown in %s\
                            uve" % (self.vn2_fixture.vn_fq_name))
                    result = result and False
            self.logger.info("Deleting service instance")
            self.si_fixture.cleanUp()
            self.remove_from_cleanups(self.si_fixture)
            time.sleep(10)
            try:
                self.analytics_obj.verify_si_uve_not_in_analytics(
                    instance=si_name,
                    st_name=self.st_name,
                    left_vn=self.vn1_fq_name,
                    right_vn=self.vn2_fq_name)
                for si_uuid in si_uuids:
                    self.analytics_obj.verify_vn_uve_for_vm_not_in_vn(
                        vn_fq_name=self.vn2_fixture.vn_fq_name,
                        vm=si_uuid)
                    self.analytics_obj.verify_vn_uve_for_vm_not_in_vn(
                        vn_fq_name=self.vn1_fixture.vn_fq_name,
                        vm=si_uuid)
            except Exception as e:
                self.logger.warn(
                    "Service instance uve not removed from analytics")
                result = result and False

            self.logger.info("Deleting service template")
            self.st_fixture.cleanUp()
            self.remove_from_cleanups(self.st_fixture)
# TO DO:Sandipd - SI cleanup in analytics still an issue
#                 Skipping it for now
#            try:
#                assert self.analytics_obj.verify_st_uve_not_in_analytics(
#                    instance=si_name,
#                    st_name=self.st_name,
#                    left_vn=self.vn1_fq_name,
#                    right_vn=self.vn2_fq_name)
#            except Exception as e:
#                self.logger.warn(
#                    "Service Template uve not removed from analytics")
#                result = result and False
#            try:
#                assert self.analytics_obj.verify_ri_not_in_vn_uve(
#                        vn_fq_name=self.vn1_fixture.vn_fq_name,
#                    ri_name = service_chain_name)
#            except Exception as e:
#                self.logger.warn(
#                    "RI not removed from %s uve " %
#                    (self.vn1_fixture.vn_fq_name))
#                result = result and False
#            try:
#                assert self.analytics_obj.verify_ri_not_in_vn_uve(
#                        vn_fq_name = self.vn2_fixture.vn_fq_name,
#                        ri_name = service_chain_name)
#            except Exception as e:
#                self.logger.warn(
#                    "RI not removed from %s uve " %
#                    (self.vn2_fixture.vn_fq_name))
#                result = result and False

            self.logger.info("Verifying the object logs...")
            obj_id_lst = self.analytics_obj.get_uve_key(
                uve='service-instances')
            obj_id1_lst = self.analytics_obj.get_uve_key(uve='service-chains')
            for elem in obj_id_lst:
                query = '(' + 'ObjectId=' + elem + ')'
                self.logger.info(
                    "Verifying ObjectSITable Table through opserver %s.." %
                    (self.inputs.collector_ips[0]))
                res1 = self.analytics_obj.ops_inspect[
                    self.inputs.collector_ips[0]].post_query(
                    'ObjectSITable',
                    start_time=start_time,
                    end_time='now',
                    select_fields=[
                        'ObjectId',
                        'Source',
                        'ObjectLog',
                        'SystemLog',
                        'Messagetype',
                        'ModuleId',
                        'MessageTS'],
                    where_clause=query)
                if res1:
                    self.logger.info("SI object logs received %s" % (res1))
                    result = result and True
                else:
                    self.logger.warn("SI object logs NOT received ")
                    result = result and False

            for elem in obj_id1_lst:
                query = '(' + 'ObjectId=' + elem + ')'
                self.logger.info(
                    "Verifying ServiceChain Table through opserver %s.." %
                    (self.inputs.collector_ips[0]))
                res2 = self.analytics_obj.ops_inspect[
                    self.inputs.collector_ips[0]].post_query(
                    'ServiceChain',
                    start_time=start_time,
                    end_time='now',
                    select_fields=[
                        'ObjectId',
                        'Source',
                        'ObjectLog',
                        'SystemLog',
                        'Messagetype',
                        'ModuleId',
                        'MessageTS'],
                    where_clause=query)
                if res2:
                    self.logger.info("ST object logs received %s" % (res2))
                    result = result and True
                else:
                    self.logger.warn("ST object logs NOT received ")
                    result = result and False
        except Exception as e:
            self.logger.warn("Got exception as %s" % (e))
            result = result and False
        assert result
        return True

    @preposttest_wrapper
    def test_object_tables(self):
        '''Test object tables.
        '''
        start_time = self.analytics_obj.get_time_since_uptime(
            self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_object_tables(
            start_time=start_time,
            skip_tables=[
                u'ObjectVMTable',
                u'ConfigObjectTable',
                u'ObjectBgpPeer',
                u'ObjectBgpRouter',
                u'ObjectXmppConnection',
                u'ObjectVNTable',
                u'ObjectGeneratorInfo',
                u'ObjectRoutingInstance',
                u'ObjectVRouter',
                u'ObjectConfigNode',
                u'ObjectXmppPeerInfo',
                u'ObjectCollectorInfo'])

        return True

    @preposttest_wrapper
    def test_virtual_machine_uve_vm_tiers(self):
        '''Test to validate virtual machine uve tiers - should be UveVirtualMachineConfig and UveVirtualMachineAgent.
        '''
        vm_uuid_list = [
            self.res.vn1_vm1_fixture.vm_id,
            self.res.vn2_vm2_fixture.vm_id]
        for uuid in vm_uuid_list:
            assert self.analytics_obj.verify_vm_uve_tiers(uuid=uuid)
        return True

    @preposttest_wrapper
    def test_vn_uve_routing_instance(self):
        '''Test to validate routing instance in vn uve.
        '''
        vn_list = [
            self.res.vn1_fixture.vn_fq_name,
            self.res.vn2_fixture.vn_fq_name,
            self.res.fvn_fixture.vn_fq_name]
        for vn in vn_list:
            assert self.analytics_obj.verify_vn_uve_ri(vn_fq_name=vn)
        return True

    @preposttest_wrapper
    def test_vn_uve_tiers(self):
        '''Test to validate vn uve receives uve message from api-server and Agent.
        '''
        vn_list = [
            self.res.vn1_fixture.vn_fq_name,
            self.res.vn2_fixture.vn_fq_name,
            self.res.fvn_fixture.vn_fq_name]
        for vn in vn_list:
            assert self.analytics_obj.verify_vn_uve_tiers(vn_fq_name=vn)
        return True

    @preposttest_wrapper
    def test_vrouter_uve_vm_on_vm_create(self):
        '''Test to validate vm list,connected networks and tap interfaces in vrouter uve.
        '''
        vn_list = [
            self.res.vn1_fixture.vn_fq_name,
            self.res.vn2_fixture.vn_fq_name,
            self.res.fvn_fixture.vn_fq_name]
        vm_fixture_list = [self.res.vn1_vm1_fixture, self.res.vn2_vm2_fixture]

        for vm_fixture in vm_fixture_list:
            assert vm_fixture.verify_on_setup()
            vm_uuid = vm_fixture.vm_id
            vm_node_ip = vm_fixture.inputs.host_data[
                vm_fixture.orch.get_host_of_vm(
                    vm_fixture.vm_obj)]['host_ip']
            vn_of_vm = vm_fixture.vn_fq_name
            vm_host = vm_fixture.inputs.host_data[vm_node_ip]['name']
            interface_name = vm_fixture.agent_inspect[
                vm_node_ip].get_vna_tap_interface_by_vm(vm_id=vm_uuid)[0]['config_name']
            self.logger.info(
                "expected tap interface of vm uuid %s is %s" %
                (vm_uuid, interface_name))
            self.logger.info(
                "expected virtual netowrk  of vm uuid %s is %s" %
                (vm_uuid, vn_of_vm))
            assert self.analytics_obj.verify_vm_list_in_vrouter_uve(
                vm_uuid=vm_uuid,
                vn_fq_name=vn_of_vm,
                vrouter=vm_host,
                tap=interface_name)

        return True

    @preposttest_wrapper
    def test_verify_connected_networks_based_on_policy(self):
        ''' Test to validate attached policy in the virtual-networks

        '''
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_fixture.get_cidrs(af='v4')
        vn2_name = self.res.vn2_name
        vn2_subnets = self.res.vn2_fixture.get_cidrs(af='v4')
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.vn1_fixture
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(
            vn1_fixture.unbind_policies, vn1_fixture.vn_id, [
                policy1_fixture.policy_fq_name])

        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.res.vn2_fixture
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        assert vn2_fixture.verify_on_setup()
        self.addCleanup(
            vn2_fixture.unbind_policies, vn2_fixture.vn_id, [
                policy2_fixture.policy_fq_name])
#        self.res.verify_common_objects()
        self.logger.info(
            "Verifying the connected_networks based on policy in the vn uve..")
        vn1_fq_name = self.res.vn1_fixture.vn_fq_name
        vn2_fq_name = self.res.vn2_fixture.vn_fq_name
        assert self.analytics_obj.verify_connected_networks_in_vn_uve(
            vn1_fq_name,
            vn2_fq_name)
        assert self.analytics_obj.verify_connected_networks_in_vn_uve(
            vn2_fq_name,
            vn1_fq_name)
        return True

    @preposttest_wrapper
    def test_verify_flow_series_table_query_range(self):
        ''' Test to validate flow series table for query range

        '''
        # installing traffic package in vm
        self.res.vn1_vm1_fixture.install_pkg("Traffic")
        self.res.vn1_vm2_fixture.install_pkg("Traffic")

        self.tx_vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        self.rx_vm_node_ip = self.res.vn1_vm2_fixture.vm_node_ip
        self.tx_local_host = Host(
            self.tx_vm_node_ip, self.inputs.host_data[
                self.tx_vm_node_ip]['username'], self.inputs.host_data[
                self.tx_vm_node_ip]['password'])
        self.rx_local_host = Host(
            self.rx_vm_node_ip, self.inputs.host_data[
                self.rx_vm_node_ip]['username'], self.inputs.host_data[
                self.rx_vm_node_ip]['password'])

        self.send_host = Host(self.res.vn1_vm1_fixture.local_ip,
                              self.res.vn1_vm1_fixture.vm_username,
                              self.res.vn1_vm1_fixture.vm_password)
        self.recv_host = Host(self.res.vn1_vm2_fixture.local_ip,
                              self.res.vn1_vm2_fixture.vm_username,
                              self.res.vn1_vm2_fixture.vm_password)

        # Create traffic stream
        start_time = self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        self.logger.info("Creating streams...")
        dport = 11000
        stream = Stream(
            protocol="ip",
            proto="udp",
            src=self.res.vn1_vm1_fixture.vm_ip,
            dst=self.res.vn1_vm2_fixture.vm_ip,
            dport=dport)

        startport = 10000
        profile = ContinuousSportRange(
            stream=stream,
            listener=self.res.vn1_vm2_fixture.vm_ip,
            startport=10000,
            endport=dport,
            pps=100)
        sender = Sender(
            'sname',
            profile,
            self.tx_local_host,
            self.send_host,
            self.inputs.logger)
        receiver = Receiver(
            'rname',
            profile,
            self.rx_local_host,
            self.recv_host,
            self.inputs.logger)
        receiver.start()
        sender.start()
        time.sleep(30)
        sender.stop()
        receiver.stop()
        print sender.sent, receiver.recv
        time.sleep(1)

        vm_node_ip = self.res.vn1_vm1_fixture.inputs.host_data[
            self.res. vn1_vm1_fixture.orch.get_host_of_vm(
                self.res.vn1_vm1_fixture.vm_obj)]['host_ip']
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        time.sleep(30)
        # Verifying flow series table
        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn1_name
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn1_name
        # creating query: '(sourcevn=default-domain:admin:vn1) AND
        # (destvn=default-domain:admin:vn2)'
        query = '(sourcevn=%s) AND (destvn=%s) AND protocol= 17 AND (sport = 10500 < 11000)' % (
            src_vn, dst_vn)
        for ip in self.inputs.collector_ips:
            self.logger.info('setup_time= %s' % (start_time))
            # Quering flow sreies table

            self.logger.info(
                "Verifying flowSeriesTable through opserver %s" %
                (ip))
            self.res1 = self.analytics_obj.ops_inspect[ip].post_query(
                'FlowSeriesTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'sport',
                    'dport',
                    'T=1'],
                where_clause=query)
            assert self.res1
            for elem in self.res1:
                if ((elem['sport'] < 10500) or (elem['sport'] > 11000)):
                    self.logger.warn(
                        "Out of range element (range:sport > 15500 and sport < 16000):%s" %
                        (elem))
                    self.logger.warn("Test Failed")
                    result = False
                    assert result
        return True

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_verify_flow_tables(self):
        '''
          Description:  Test to validate flow tables

            1.Creat 2 vn and 1 vm in each vn
            2.Create policy between vns
            3.send 100 udp packets from vn1 to vn2
            4.Verify in vrouter uve that active flow matches with the agent introspect - fails otherwise
            5.Query flowrecord table for the flow and verify packet count mtches 100 - fails otherwise
            6.Query flow series table or the flow and verify packet count mtches 100 - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        vn1_name = self.res.vn1_name
        vn1_fq_name = '%s:%s:%s' % (
            self.inputs.project_fq_name[0], self.inputs.project_fq_name[1], self.res.vn1_name)
        vn1_subnets = self.res.vn1_fixture.get_cidrs(af='v4')
        vn2_name = self.res.vn2_name
        vn2_fq_name = '%s:%s:%s' % (
            self.inputs.project_fq_name[0], self.inputs.project_fq_name[1], self.res.vn2_name)
        vn2_subnets = self.res.vn2_fixture.get_cidrs(af='v4')
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        result = True
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.vn1_fixture
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(
            vn1_fixture.unbind_policies, vn1_fixture.vn_id, [
                policy1_fixture.policy_fq_name])

        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.res.vn2_fixture
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        assert vn2_fixture.verify_on_setup()
        self.addCleanup(
            vn2_fixture.unbind_policies, vn2_fixture.vn_id, [
                policy2_fixture.policy_fq_name])
#        self.res.verify_common_objects()
        # start_time=self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        # installing traffic package in vm
        self.res.vn1_vm1_fixture.verify_on_setup()
        self.res.vn2_vm2_fixture.verify_on_setup()
        self.res.fvn_vm1_fixture.verify_on_setup()
        self.res.vn1_vm1_fixture.install_pkg("Traffic")
        self.res.vn2_vm2_fixture.install_pkg("Traffic")
        self.res.fvn_vm1_fixture.install_pkg("Traffic")

        self.tx_vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        self.rx_vm_node_ip = self.res.vn2_vm2_fixture.vm_node_ip
        self.tx_local_host = Host(
            self.tx_vm_node_ip, self.inputs.host_data[
                self.tx_vm_node_ip]['username'], self.inputs.host_data[
                self.tx_vm_node_ip]['password'])
        self.rx_local_host = Host(
            self.rx_vm_node_ip, self.inputs.host_data[
                self.rx_vm_node_ip]['username'], self.inputs.host_data[
                self.rx_vm_node_ip]['password'])
        self.send_host = Host(self.res.vn1_vm1_fixture.local_ip,
                              self.res.vn1_vm1_fixture.vm_username,
                              self.res.vn1_vm1_fixture.vm_password)
        self.recv_host = Host(self.res.vn2_vm2_fixture.local_ip,
                              self.res.vn2_vm2_fixture.vm_username,
                              self.res.vn2_vm2_fixture.vm_password)
        pkts_before_traffic = self.analytics_obj.get_inter_vn_stats(
            self.inputs.collector_ips[0],
            src_vn=vn1_fq_name,
            other_vn=vn2_fq_name,
            direction='in')
        if not pkts_before_traffic:
            pkts_before_traffic = 0

        self.res.vn1_vm1_fixture.wait_till_vm_is_up()
        self.res.vn1_vm2_fixture.wait_till_vm_is_up()
        # Create traffic stream
        self.logger.info("Creating streams...")
        stream = Stream(
            protocol="ip",
            proto="udp",
            src=self.res.vn1_vm1_fixture.vm_ip,
            dst=self.res.vn2_vm2_fixture.vm_ip,
            dport=9000)

        profile = StandardProfile(
            stream=stream,
            size=100,
            count=10,
            listener=self.res.vn2_vm2_fixture.vm_ip)
        sender = Sender(
            "sendudp",
            profile,
            self.tx_local_host,
            self.send_host,
            self.inputs.logger)
        receiver = Receiver(
            "recvudp",
            profile,
            self.rx_local_host,
            self.recv_host,
            self.inputs.logger)
        start_time = self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        receiver.start()
        sender.start()
        time.sleep(10)
        # Poll to make usre traffic flows, optional
        # sender.poll()
        # receiver.poll()
        sender.stop()
        receiver.stop()
        print sender.sent, receiver.recv
        for vn in [self.res.vn1_fixture.vn_fq_name,\
                    self.res.vn2_fixture.vn_fq_name]:
                 
            #ACL count        
            if not (int(self.analytics_obj.get_acl\
                    (self.inputs.collector_ips[0],vn)) > 0):
                    self.logger.error("Acl counts not received from Agent uve \
                                in %s vn uve"%(vn))
                    result = result and False

            if not (int(self.analytics_obj.get_acl\
                    (self.inputs.collector_ips[0], vn, tier = 'Config')) > 0):
                    self.logger.error("Acl counts not received from Config uve \
                                in %s vn uve"%(vn))
                    result = result and False

            #Bandwidth usage        
            if not (int(self.analytics_obj.get_bandwidth_usage\
                    (self.inputs.collector_ips[0], vn, direction = 'out')) > 0):
                    self.logger.error("Bandwidth not shown  \
                                in %s vn uve"%(vn))
                    result = result and False

            if not (int(self.analytics_obj.get_bandwidth_usage\
                    (self.inputs.collector_ips[0], vn, direction = 'in')) > 0):
                    self.logger.error("Bandwidth not shown  \
                                in %s vn uve"%(vn))
                    result = result and False

            #Flow count
            if not (int(self.analytics_obj.get_flow\
                    (self.inputs.collector_ips[0], vn, direction = 'egress')) > 0):
                    self.logger.error("egress flow  not shown  \
                                in %s vn uve"%(vn))
                    result = result and False

            if not (int(self.analytics_obj.get_flow\
                    (self.inputs.collector_ips[0], vn, direction = 'ingress')) > 0):
                    self.logger.error("ingress flow  not shown  \
                                in %s vn uve"%(vn))
                    result = result and False
                   
            #VN stats
            vns = [self.res.vn1_fixture.vn_fq_name,\
                    self.res.vn2_fixture.vn_fq_name]
            vns.remove(vn)
            other_vn = vns[0]        
            if not (self.analytics_obj.get_vn_stats\
                    (self.inputs.collector_ips[0], vn, other_vn)):
                    self.logger.error("vn_stats   not shown  \
                                in %s vn uve"%(vn))
                    result = result and False

        assert "sender.sent == receiver.recv", "UDP traffic to ip:%s failed" % self.res.vn2_vm2_fixture.vm_ip
        # Verifying the vrouter uve for the active flow
        vm_node_ip = self.res.vn1_vm1_fixture.inputs.host_data[
            self.res.vn1_vm1_fixture.orch.get_host_of_vm(
                self.res.vn1_vm1_fixture.vm_obj)]['host_ip']
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        self.logger.info(
            "Waiting for the %s vrouter uve to be updated with active flows" %
            (vm_host))
        time.sleep(60)
        self.flow_record = self.analytics_obj.get_flows_vrouter_uve(
            vrouter=vm_host)
        self.logger.info(
            "Active flow in vrouter uve = %s" %
            (self.flow_record))
        if (self.flow_record > 0):
            self.logger.info("Flow records  updated")
            result = result and True
        else:
            self.logger.warn("Flow records NOT updated")
            result = result and False

#        assert ( self.flow_record > 0)
#        self.logger.info("Waiting for inter-vn stats to be updated...")
#        time.sleep(60)
        pkts_after_traffic = self.analytics_obj.get_inter_vn_stats(
            self.inputs.collector_ips[0],
            src_vn=vn1_fq_name,
            other_vn=vn2_fq_name,
            direction='in')
        if not pkts_after_traffic:
            pkts_after_traffic = 0
        self.logger.info("Verifying that the inter-vn stats updated")
        self.logger.info(
            "Inter vn stats before traffic %s" %
            (pkts_before_traffic))
        self.logger.info(
            "Inter vn stats after traffic %s" %
            (pkts_after_traffic))
        if ((pkts_after_traffic - pkts_before_traffic) >= 10):
            self.logger.info("Inter vn stats updated")
            result = result and True
        else:
            self.logger.warn("Inter vn stats NOT updated")
            result = result and False

        self.logger.info("Waiting for flow records to be expired...")
        time.sleep(224)
        self.flow_record = self.analytics_obj.get_flows_vrouter_uve(
            vrouter=vm_host)
#        if ( self.flow_record > 0):
#            self.logger.info("Flow records  updated")
#            result = result and True
#        else:
#            self.logger.warn("Flow records NOT updated")
#            result = result and False
        self.logger.debug(
            "Active flow in vrouter uve = %s" %
            (self.flow_record))
#        assert ( self.flow_record == 0)
        # Verifying flow series table
        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn1_name
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn2_name
        # creating query: '(sourcevn=default-domain:admin:vn1) AND
        # (destvn=default-domain:admin:vn2)'
        query = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ')'
        for ip in self.inputs.collector_ips:
            self.logger.info(
                "Verifying flowRecordTable through opserver %s.." %
                (ip))
            self.res2 = self.analytics_obj.ops_inspect[ip].post_query(
                'FlowRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'setup_time',
                    'teardown_time',
                    'agg-packets'],
                where_clause=query)

            self.logger.info("Query output: %s" % (self.res2))
            assert self.res2
            if self.res2:
                r = self.res2[0]
                s_time = r['setup_time']
                e_time = r['teardown_time']
                agg_pkts = r['agg-packets']
                assert (agg_pkts == sender.sent)
            self.logger.info(
                'setup_time= %s,teardown_time= %s' %
                (s_time, e_time))
            self.logger.info("Records=\n%s" % (self.res2))
            # Quering flow sreies table
            self.logger.info(
                "Verifying flowSeriesTable through opserver %s" %
                (ip))
            self.res1 = self.analytics_obj.ops_inspect[ip].post_query(
                'FlowSeriesTable',
                start_time=str(s_time),
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)'],
                where_clause=query)
            self.logger.info("Query output: %s" % (self.res1))
            assert self.res1
            if self.res1:
                r1 = self.res1[0]
                sum_pkts = r1['sum(packets)']
                assert (sum_pkts == sender.sent)
            self.logger.info("Flow series Records=\n%s" % (self.res1))
            assert (sum_pkts == agg_pkts)

        assert result
        return True

    @preposttest_wrapper
    def test_verify_flow_series_table(self):
        ''' Test to validate flow series table

        '''
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_fixture.get_cidrs(af='v4')
        vn2_name = self.res.vn2_name
        vn2_subnets = self.res.vn2_fixture.get_cidrs(af='v4')
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.vn1_fixture
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(
            vn1_fixture.unbind_policies, vn1_fixture.vn_id, [
                policy1_fixture.policy_fq_name])

        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.res.vn2_fixture
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        assert vn2_fixture.verify_on_setup()
        self.addCleanup(
            vn2_fixture.unbind_policies, vn2_fixture.vn_id, [
                policy2_fixture.policy_fq_name])
#        self.res.verify_common_objects()
        # installing traffic package in vm
        self.res.vn1_vm1_fixture.install_pkg("Traffic")
        self.res.vn2_vm2_fixture.install_pkg("Traffic")
#        self.res.fvn_vm1_fixture.install_pkg("Traffic")

        self.tx_vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        self.rx_vm_node_ip = self.res.vn2_vm2_fixture.vm_node_ip
        self.tx_local_host = Host(
            self.tx_vm_node_ip, self.inputs.host_data[
                self.tx_vm_node_ip]['username'], self.inputs.host_data[
                self.tx_vm_node_ip]['password'])
        self.rx_local_host = Host(
            self.rx_vm_node_ip, self.inputs.host_data[
                self.rx_vm_node_ip]['username'], self.inputs.host_data[
                self.rx_vm_node_ip]['password'])
        self.send_host = Host(self.res.vn1_vm1_fixture.local_ip,
                              self.res.vn1_vm1_fixture.vm_username,
                              self.res.vn1_vm1_fixture.vm_password)
        self.recv_host = Host(self.res.vn2_vm2_fixture.local_ip,
                              self.res.vn2_vm2_fixture.vm_username,
                              self.res.vn2_vm2_fixture.vm_password)
        # Create traffic stream
        start_time = self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        for i in range(10):
            count = 100
            dport = 9000
            count = count * (i + 1)
            dport = dport + i
            print 'count=%s' % (count)
            print 'dport=%s' % (dport)

            self.logger.info("Creating streams...")
            stream = Stream(
                protocol="ip",
                proto="udp",
                src=self.res.vn1_vm1_fixture.vm_ip,
                dst=self.res.vn2_vm2_fixture.vm_ip,
                dport=dport)

            profile = StandardProfile(
                stream=stream,
                size=100,
                count=count,
                listener=self.res.vn2_vm2_fixture.vm_ip)
            sender = Sender(
                "sendudp",
                profile,
                self.tx_local_host,
                self.send_host,
                self.inputs.logger)
            receiver = Receiver(
                "recvudp",
                profile,
                self.rx_local_host,
                self.recv_host,
                self.inputs.logger)
            receiver.start()
            sender.start()
            sender.stop()
            receiver.stop()
            print sender.sent, receiver.recv
            time.sleep(1)
        vm_node_ip = self.res.vn1_vm1_fixture.inputs.host_data[
            self.res.vn1_vm1_fixture.orch.get_host_of_vm(
                self.res.vn1_vm1_fixture.vm_obj)]['host_ip']
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        time.sleep(300)
        # Verifying flow series table
        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn1_name
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + self.res.vn2_name
        # creating query: '(sourcevn=default-domain:admin:vn1) AND
        # (destvn=default-domain:admin:vn2)'
        query = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ')'
        for ip in self.inputs.collector_ips:
            self.logger.info('setup_time= %s' % (start_time))
            # Quering flow sreies table
            self.logger.info(
                "Verifying flowSeriesTable through opserver %s" %
                (ip))
            self.res1 = self.analytics_obj.ops_inspect[ip].post_query(
                'FlowSeriesTable',
                start_time=start_time,
                end_time='now',
                select_fields=[
                    'sourcevn',
                    'sourceip',
                    'destvn',
                    'destip',
                    'sum(packets)',
                    'sport',
                    'dport',
                    'T=1'],
                where_clause=query,
                sort=2,
                limit=5,
                sort_fields=['sum(packets)'])
            assert self.res1
    
    @preposttest_wrapper
    def test_verify_process_status_agent(self):
        ''' Test to validate process_status

        '''
        assert self.analytics_obj.verify_process_and_connection_infos_agent()

    @preposttest_wrapper
    def test_uves(self):
        '''Test uves.
        '''
        assert self.analytics_obj.verify_all_uves()
        return True
    
    @preposttest_wrapper
    def test_vn_uve_for_all_tiers(self):
        '''Test uves.
        '''
        vn_uves = ['udp_sport_bitmap','in_bytes',
                'total_acl_rules','out_bandwidth_usage',
                'udp_dport_bitmap','out_tpkts',
                'virtualmachine_list',
                'associated_fip_count',
                'mirror_acl',
                'tcp_sport_bitmap',
                'vn_stats','vrf_stats_list',
                'in_bandwidth_usage','egress_flow_count',
                'ingress_flow_count',
                'interface_list']
        for vn in [self.res.vn1_fixture.vn_fq_name,\
                    self.res.vn2_fixture.vn_fq_name]:
            uve = self.analytics_obj.get_vn_uve(vn)
            for elem in vn_uves:
                if elem not in str(uve):
                    self.logger.error("%s not shown in vn uve %s"%(elem,vn))
        return True


    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_run_contrail_flows_cli_cmds(self):
        '''1. Test to verify  contrail-flows cli cmd with various optional arguments is not broken..

              Run the following commands:

              cmd1: contrail-flows --source-vn default-domain:ctest-AnalyticsTestSanityWithResource-70247115:ctest-vn1-92886157
                    --source-ip 107.191.91.3 --source-port 1453 --protocol 1 --direction ingress --tunnel-info
                    --start-time now-30m --end-time now'

              cmd2: contrail-flows --destination-vn default-domain:ctest-AnalyticsTestSanityWithResource-70247115:ctest-vn1-92886157
                    --destination-ip 107.191.91.4 --destination-port 0 --action pass --protocol 1 --verbose --last 1h

              cmd3: contrail-flows --vrouter-ip 'vrouter-ip' --other-vrouter-ip 'peer-vrouter-ip' --start-time now-10m --end-time now

              cmd4: contrail-flows --vrouter 'vrouter-name' --last 10m'

              cmd5: contrail-flows --vmi-uuid 'vmi-uuid'

           2.Verify the command runs properly

           3.Verify the cmd is returning non null output
        '''
        result = True
        src_vn = self.res.vn1_vm1_fixture.vn_fq_names[0]
        dst_vn = self.res.vn1_vm2_fixture.vn_fq_names[0]

        other_vrouter_ip = self.res.vn1_vm2_fixture._vm_node_ip
        vrouter_ip = self.res.vn1_vm1_fixture._vm_node_ip

        src_vm_host = self.res.vn1_vm1_fixture.get_host_of_vm()
        dst_vm_host = self.res.vn1_vm2_fixture.get_host_of_vm()

        src_vm_introspect = self.agent_inspect[src_vm_host]
        dst_vm_introspect = self.agent_inspect[dst_vm_host]

        src_vm_ip =  self.res.vn1_vm1_fixture.get_vm_ips()[0]
        dst_vm_ip = self.res.vn1_vm2_fixture.get_vm_ips()[0]
        vm_ips = [src_vm_ip, dst_vm_ip]

        timer = 0
        while True:
            flows = []
            my_flows = []
            assert self.res.vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=self.res.vn1_vm2_fixture)
            all_flows = src_vm_introspect.get_vna_fetchallflowrecords()
            for flow in all_flows:
                proto = flow['protocol']
                src_ip = flow.get('sip')
                dst_ip = flow.get('dip')
                action = flow['action_str'][0]['action']
                if proto == '1':
                    my_flows.append((proto, src_ip, dst_ip))
                if proto == '1' and action == 'pass' and src_ip in vm_ips and dst_ip in vm_ips:
                    flows.append(flow)

            self.logger.info(pprint.pprint(my_flows)); print vm_ips
            try:
                src_flow = flows[0]
                dst_flow = flows[1]
                break
            except (IndexError, KeyError):
                time.sleep(2)
                timer = timer + 1
                print timer
                if timer > 30:
                    self.logger.error("Flow not found")
                    return False

        protocol = src_flow['protocol']
        dip = src_flow['dip']
        dst_port = src_flow['dst_port']
        dst_vn = self.res.vn1_vm2_fixture.vn_fq_names[0]
        direction = src_flow['direction']
        action = 'pass'

        src_vn = self.res.vn1_vm1_fixture.vn_fq_names[0]
        src_port = src_flow['src_port']
        sip = src_flow['sip']
        vmi_uuid = self.res.vn1_vm1_fixture.get_vmi_ids().values()[0]

        cmd_args_list = [ { 'source-vn':src_vn, 'source-ip':sip, 'source-port':src_port,
            'protocol':protocol, 'direction':direction, 'no_key':['start-time now-30m', 'end-time now']},
            {'destination-vn':dst_vn, 'destination-ip':dip, 'destination-port':dst_port,
            'action':action, 'protocol':protocol, 'no_key':['verbose, last 1h']},
            {'vrouter-ip':vrouter_ip, 'other-vrouter-ip':other_vrouter_ip, 'no_key':['start-time now-10m', 'end-time now']},
            {'vrouter':src_vm_host, 'no_key': ['last 10m']}, {'vmi-uuid':vmi_uuid, 'no_key': ['last 20m']}]

        failed_cmds = []
        passed_cmds = []

        for cmd_args in cmd_args_list:
            cmd = self._form_cmd('contrail-flows', cmd_args)
            self.logger.info("Running the following cmd:%s \n" %cmd)
            if not self.execute_cli_cmd(cmd, check_output=True):
                self.logger.error('%s contrail-flows command failed..' % cmd)
                failed_cmds.append(cmd)
                result = result and False
            passed_cmds.append(cmd)

        self.logger.info('%s commands passed..\n' % passed_cmds)
        self.logger.info('%s commands failed..\n ' % failed_cmds)
        return result

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_verify_contrail_logs_cli_command_not_broken(self):
        '''1.Run command 'contrail-logs --object-type virtual-network'
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        cmd = 'contrail-logs --object-type virtual-network'
        if not self.execute_cli_cmd(cmd):
            self.logger.error('%s contrail-logs command failed..' % cmd)
            return False
        return True
    
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_verify_contrail_stats_cli_command_not_broken(self):
        '''1.Run command 'contrail-stats --table SandeshMessageStat.msg_info --select "SUM(msg_info.messages)" msg_info.type --sort "SUM(msg_info.messages)"'
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        cmd = 'contrail-stats --table SandeshMessageStat.msg_info --select "SUM(msg_info.messages)" msg_info.type --sort "SUM(msg_info.messages)"'
        if not self.execute_cli_cmd(cmd):
            self.logger.error('%s contrail-stats command failed..' % cmd)
            return False
        return True
#End AnalyticsTestSanityWithResource        
