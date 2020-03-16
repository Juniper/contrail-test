from __future__ import print_function
from analytics import base
from builtins import str
from builtins import range
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
import fixtures

import test
import pprint

class AnalyticsTestSanityWithMin(
        base.AnalyticsBaseTest,
        VerifySvcChain):
    '''
    Sanity tests with minimum resource objects created during setUpClass
    '''

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanityWithMin, cls).setUpClass()
        cls.res.setUp(cls.inputs, cls.connections)

    @classmethod
    def tearDownClass(cls):
        super(AnalyticsTestSanityWithMin, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['sanity', 'vcenter'])
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
              cmd5: contrail-flows --vmi 'vmi fq_name'
           2.Verify the command runs properly
           3.Verify the cmd is returning non null output
        '''
        result = True
        self.setup_flow_export_rate(10)
        src_vn = self.res.vn1_vm1_fixture.vn_fq_names[0]
        dst_vn = self.res.vn1_vm2_fixture.vn_fq_names[0]
        other_vrouter_ip = self.res.vn1_vm2_fixture.vm_node_data_ip
        vrouter_ip = self.res.vn1_vm1_fixture.vm_node_data_ip

        src_vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        dst_vm_node_ip = self.res.vn1_vm2_fixture.vm_node_data_ip
        src_svc_name = self.inputs.host_data[src_vm_node_ip]['service_name']
        dst_svc_name = self.inputs.host_data[dst_vm_node_ip]['service_name']
        if not src_svc_name:
            src_vm_host = self.inputs.host_data[src_vm_node_ip]['host_ip']
        else:
            src_vm_host = self.inputs.host_data[src_vm_node_ip]['service_name'][src_vm_node_ip]

        if not dst_svc_name:
            dst_vm_host = self.inputs.host_data[dst_vm_node_ip]['host_ip']
        else:
            dst_vm_host = self.inputs.host_data[dst_vm_node_ip]['service_name'][dst_vm_node_ip]
        src_vm_host_ip = self.res.vn1_vm1_fixture.vm_node_ip
        dst_vm_host_ip = self.res.vn1_vm2_fixture.vm_node_ip
        src_vm_introspect = self.agent_inspect[src_vm_host_ip]
        dst_vm_introspect = self.agent_inspect[dst_vm_host_ip]

        src_vm_ip =  self.res.vn1_vm1_fixture.get_vm_ips()[0]
        dst_vm_ip = self.res.vn1_vm2_fixture.get_vm_ips()[0]
        vm_ips = [src_vm_ip, dst_vm_ip]
        vmi_uuid = list(self.res.vn1_vm1_fixture.get_vmi_ids().values())[0]
        vmi_objs = self.res.vn1_vm1_fixture.get_vmi_objs()
        vmi_fq_name_list = vmi_objs[self.inputs.cfgm_ip][0]['virtual-machine-interface']['fq_name']
        vmi_fq_name = ":".join(vmi_fq_name_list)

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

            self.logger.info(pprint.pprint(my_flows)); print(vm_ips)
            try:
                src_flow = flows[0]
                dst_flow = flows[1]
                break
            except (IndexError, KeyError):
                time.sleep(2)
                timer = timer + 1
                print(timer)
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
        
        cmd_args_list = [ { 'source-vn':src_vn, 'source-ip':sip, 'source-port':src_port,
            'protocol':protocol, 'direction':direction, 'no_key':['start-time now-30m', 'end-time now']},
            {'destination-vn':dst_vn, 'destination-ip':dip, 'destination-port':dst_port,
            'action':action, 'protocol':protocol, 'no_key':['verbose', 'last 1h']},
            {'vrouter-ip':vrouter_ip, 'other-vrouter-ip':other_vrouter_ip, 'no_key':['start-time now-10m', 'end-time now']},
            {'vrouter':src_vm_host, 'no_key': ['last 10m']}, {'vmi':vmi_fq_name, 'no_key': ['last 20m']},
            {'no_key': ['help']}]


        return self.check_cmd_output('contrail-flows', cmd_args_list, check_output=True, as_sudo=True, print_output=False)

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_multiple_different_optional_args(self):
        '''1.Test to verify contrail-logs cli cmd with multiple different optional type args is not broken
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        vmi_uuid = list(self.res.vn1_vm1_fixture.get_vmi_ids().values())[0]
        vm_id = self.res.vn1_vm1_fixture.get_uuid()
        cfgm = self.res.inputs.cfgm_names[0]
        collector = self.res.inputs.collector_names[0]
        cmd_args_list = [
            {'object-type':'vrouter', 'no_key': ['start-time now-5m', 'end-time now']},
            {'object-type':'database-node', 'message-type':'NodeStatusUVE',
                'no_key':['start-time now-10m', 'end-time now', 'raw']},
            {'node-type': 'Database', 'message-type': 'CassandraStatusUVE',
                'no_key': ['start-time now-2h']},
            {'node-type':'Compute', 'message-type':'UveVMInterfaceAgentTrace',
                'no_key': ['start-time now-10m', 'json']},
            {'module':'contrail-vrouter-agent', 'message-type':'SandeshModuleClientTrace',
                'no_key': ['start-time now-20m', 'end-time now']},
            {'node-type':'Config', 'module':'contrail-api', 'no_key': ['raw']},
            {'module':'contrail-vrouter-agent', 'message-type': 'UveVirtualNetworkAgentTrace',
                'node-type': 'Compute', 'no_key': ['last 5m', 'verbose', 'reverse']},
            {'module':'contrail-analytics-api', 'message-type': 'AnalyticsApiStats',
                'node-type': 'Analytics ', 'no_key': ['json']},
            {'object-type': 'virtual-machine', 'object-id':vm_id, 'no_key': ['verbose', 'raw', 'json']},
            {'node-type': 'Analytics', 'module': 'contrail-analytics-api',  'message-type': 'AnalyticsApiStats'},
            {'object-type' :'virtual-network', 'module':'contrail-control','no_key': ['last 10m']},
            {'module': 'contrail-analytics-api', 'source':collector, 'node-type': 'Analytics'},
            {'no_key': ['help']}
            ]

        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output=True, print_output=False)

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_run_contrail_stats_cli_cmds(self):
        '''1.Run contrail-stats commands with various options
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        src_vn = self.res.vn1_vm1_fixture.vn_fq_names[0]

        dst_vn = self.res.vn1_vm2_fixture.vn_fq_names[0]
        src_vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        src_svc_name = self.inputs.host_data[src_vm_node_ip]['service_name']
        if not src_svc_name:
            src_vm_host = self.inputs.host_data[src_vm_node_ip]['host_ip']
        else:
            src_vm_host = self.inputs.host_data[src_vm_node_ip]['service_name'][src_vm_node_ip]

        cmd_args_list = [

            'contrail-stats --table VMIStats.raw_if_stats --select "SUM(raw_if_stats.in_bytes)" \
            name --where name="*" --start-time now-11h --end-time now-10h',

            'contrail-stats --table NodeStatus.process_mem_cpu_usage --select "T=120" "AVG(process_mem_cpu_usage.cpu_share)" \
            "AVG(process_mem_cpu_usage.mem_res)" --where process_mem_cpu_usage.__key=cassandra --last 30m',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --select "T=60" "SUM(vn_stats.in_bytes)" --where name="*"',

            'contrail-stats --table SandeshMessageStat.msg_info --select "SUM(msg_info.messages)" \
            msg_info.type --sort "SUM(msg_info.messages)"',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --select "T=60" "SUM(vn_stats.in_bytes)" \
            --where name=' + src_vn + ' --last 1h',

            'contrail-stats --table VrouterStatsAgent.phy_band_in_bps --select phy_band_in_bps.__value phy_band_in_bps.__key',

            'contrail-stats --table SandeshMessageStat.msg_info --select "SUM(msg_info.messages)" msg_info.type --sort "SUM(msg_info.messages)"',

            'contrail-stats --table AnalyticsApiStats.api_stats  --select "PERCENTILES(api_stats.response_size_bytes)" \
            "SUM(api_stats.response_size_objects)" name --where name="*"',

            'contrail-stats --table NodeStatus.process_mem_cpu_usage --select "UUID" "process_mem_cpu_usage.cpu_share" \
            "AVG(process_mem_cpu_usage.cpu_share)" "name" --where name="*"',

            'contrail-stats --table AnalyticsApiStats.api_stats --select "name" "api_stats.useragent" "AVG(api_stats.response_size_bytes)" --where name="*"',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --select "T=60" "SUM(vn_stats.in_bytes)" --where name=' + src_vn + ' --last 1h',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --where "name=' + src_vn + '" \
            --select vn_stats.other_vn "SUM(vn_stats.out_bytes)" "SUM(vn_stats.in_bytes)" "COUNT(vn_stats)" --last 1h',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats  --where "name=' + src_vn + ' AND vn_stats.vrouter=' + src_vm_host + '" \
                --select "T" "vn_stats.other_vn" "UUID" "vn_stats.out_bytes" "vn_stats.in_bytes" --last 10m'

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --where "name=' + src_vn + ' AND vn_stats.vrouter=' + src_vm_host + '" \
            --select T vn_stats.other_vn UUID vn_stats.out_bytes vn_stats.in_bytes --last 40m',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --where "name=' + src_vn + '" --select vn_stats.other_vn \
            "SUM(vn_stats.out_bytes)" "SUM(vn_stats.in_bytes)" "COUNT(vn_stats)" --last 1h',

            'contrail-stats --table UveVirtualNetworkAgent.vn_stats --where "name=' + src_vn + ' AND vn_stats.other_vn=' + dst_vn + '" \
            --select T=300 "SUM(vn_stats.out_bytes)" "SUM(vn_stats.in_bytes)" --last 1h',

            'contrail-stats --help']

        return self.check_cmd_output('contrail-stats', cmd_args_list, check_output=True, form_cmd=False, print_output=False)
# end class AnalyticsTestSanityWithMin

class AnalyticsTestSanityWithResource(
        base.AnalyticsBaseTest,
        VerifySvcChain):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanityWithResource, cls).setUpClass()
        cls.res.setUp(cls.inputs, cls.connections)

    @classmethod
    def tearDownClass(cls):
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
            vm_node_ip = vm_fixture.vm_node_data_ip
            vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]
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
        self.setup_flow_export_rate(10)
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
        print(sender.sent, receiver.recv)
        time.sleep(1)

        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]
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
                    'SUM(packets)',
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
        self.setup_flow_export_rate(10)
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
        #moving vna stats verification to base to counter timing issue
        #while verifying bandwidth usage
        #Disabling due to bug 1717709
        #result = result and self.verify_vna_stats('bandwidth_usage')
        #result = result and self.verify_vna_stats()
        sender.stop()
        receiver.stop()
        print(sender.sent, receiver.recv)

        assert "sender.sent == receiver.recv", "UDP traffic to ip:%s failed" % self.res.vn2_vm2_fixture.vm_ip
        # Verifying the vrouter uve for the active flow
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]
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
                    'SUM(packets)'],
                where_clause=query)
            self.logger.info("Query output: %s" % (self.res1))
            assert self.res1
            if self.res1:
                r1 = self.res1[0]
                sum_pkts = r1['SUM(packets)']
                assert (sum_pkts == sender.sent)
            self.logger.info("Flow series Records=\n%s" % (self.res1))
            assert (sum_pkts == agg_pkts)

        assert result
        return True

    @preposttest_wrapper
    def test_verify_flow_series_table(self):
        ''' Test to validate flow series table

        '''
        self.setup_flow_export_rate(10)
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
            print('count=%s' % (count))
            print('dport=%s' % (dport))

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
            print(sender.sent, receiver.recv)
            time.sleep(1)
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]
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
                    'SUM(packets)',
                    'sport',
                    'dport',
                    'T=1'],
                where_clause=query,
                sort=2,
                limit=5,
                sort_fields=['SUM(packets)'])
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


    
    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_optional_arg_module(self):

        '''Test to verify contrail-logs cli cmd with various optinal module type args is not broken
           1.Run command 'contrail-logs --module contrail-control'
           2.Verify the command runs properly
           3.Verify the cmd is returning non null output
        '''

        module = ['contrail-control', 'contrail-vrouter-agent', 'contrail-api', 'contrail-schema' ,'contrail-analytics-api',
            'contrail-collector' , 'contrail-query-engine', 'contrail-svc-monitor', 'contrail-device-manager', 'contrail-dns',
            'contrail-discovery', 'IfmapServer', 'XmppServer', 'contrail-analytics-nodemgr', 'contrail-control-nodemgr',
            'contrail-config-nodemgr', 'contrail-database-nodemgr', 'Contrail-WebUI-Nodemgr', 'contrail-vrouter-nodemgr',
            'Storage-Stats-mgr', 'Ipmi-Stats-mgr', 'InventoryAgent',
            'contrail-tor-agent', 'contrail-broadview', 'contrail-kube-manager', 'contrail-mesos-manager']

        module_ = ['IfmapServer', 'XmppServer', 'Contrail-WebUI-Nodemgr', 'Storage-Stats-mgr', 'Storage-Stats-mgr', 'Ipmi-Stats-mgr',
           'InventoryAgent', 'contrail-tor-agent', 'contrail-broadview', 'contrail-kube-manager', 'contrail-mesos-manager']

        module = list(set(module) - set(module_))

        analytics = self.res.inputs.collector_ips[0]
        cfgm = self.res.inputs.cfgm_ips[0]

        self.inputs.restart_service('contrail-device-manager', [cfgm],
                                    container='controller')

        cmd_args_list = []
        for arg_type in module:
            cmd = {'module':arg_type, 'no_key': ['last 60m']}
            cmd_args_list.append(cmd)
        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output=True, print_output=False)

    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_optional_arg_object_type(self):
        '''1.Test to verify contrail-logs cli cmd with various optinal object type args is not broken
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        object_type = ['service-chain', 'database-node', 'routing-instance', 'analytics-query',
            'virtual-machine-interface', 'config-user', 'analytics-query-id', 'storage-osd', 'logical-interface',
            'xmpp-peer', 'generator', 'virtual-network', 'analytics-node', 'prouter', 'bgp-peer', 'loadbalancer',
            'user-defined-log-statistic', 'config', 'dns-node', 'storage-cluster', 'control-node', 'physical-interface',
            'server', 'virtual-machine', 'vrouter', 'storage-disk', 'storage-pool', 'service-instance', 'config-node']

        object_type_ = [ 'service-chain', 'storage-osd', 'logical-interface', 'prouter', 'loadbalancer', 'user-defined-log-statistic',
            'storage-cluster', 'physical-interface', 'server', 'storage-disk', 'storage-pool', 'service-instance', 'analytics-query-id', 'analytics-query']

        object_type = list(set(object_type) - set(object_type_))

        control = self.inputs.bgp_control_ips[0]
        self.inputs.restart_service('contrail-dns', [control],
                                    container='dns')

        failed_cmds = []
        passed_cmds = []

        syslog_exclude_list = ['xmpp-connection', 'xmpp-peer', 'generator', 'config-node']
        cmd_args_list = []
        for arg_type in object_type:
            cmds = [
                { 'object-type':arg_type, 'no_key':['last 10m']},
                { 'object-type':arg_type, 'no_key':['object-values']},
                { 'object-type':arg_type, 'no_key':['object-select-field ObjectLog']}
                ]
            for cmd in cmds:
                cmd_args_list.append(cmd)

        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output=True, print_output=False)

    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_optional_arg_message_type(self):
        '''1.Test to verify contrail-logs cli cmd with various optinal message type args is not broken
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        message_type = ['PeerStatsUve', 'RoutingInstanceStats', 'NodeStatusUVE', 'VrouterControlStatsTrace',
            'ContrailConfigTrace', 'VncApiConfigLog', 'CollectorInfo', 'SandeshModuleServerTrace',
            'BgpConfigInstanceUpdateLog', 'VncApiStatsLog', 'SandeshModuleClientTrace', 'SandeshMessageStat',
            'VirtualMachineStatsTrace', 'VrfObjectLog', 'UveVMInterfaceAgentTrace', 'IFMapNodeOperation',
            'CassandraStatusUVE', 'BGPRouterInfo', 'RoutingInstanceUpdateLog', 'VncApiDebug', 'TcpSessionMessageLog',
            'VnObjectLog', 'BgpPeerStateMachineLog', 'XmppPeerMembershipLog', 'VmObjectLog', 'PeerFlap',
            'SvcMonitorLog', 'IFMapClientSendInfo', 'CollectorDbStatsTrace', 'XmppPeerTableLog', 'UveVirtualNetworkConfigTrace']
        cmd_args_list = []
        for arg_type in message_type:
            cmds = [
                { 'message-type':arg_type, 'no_key':['last 60m']}
                ]
            for cmd in cmds:
                cmd_args_list.append(cmd)

        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output=True, print_output=False)

    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_optional_arg_level_type(self):
        '''1.Test to verify contrail-logs cli cmd with various optinal level type args is not broken
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        levels = ['SYS_DEBUG', 'SYS_INFO', 'INVALID', 'SYS_EMERG', 'SYS_CRIT', 'SYS_ALERT', 'SYS_ERR', 'SYS_WARN', 'SYS_NOTICE']
        levels_no_output = ['SYS_EMERG', 'SYS_CRIT', 'SYS_ALERT', 'SYS_ERR', 'SYS_WARN', 'SYS_NOTICE']
        cmd_args_list = []
        for arg_type in levels:
            check_output = False if arg_type in levels_no_output else True
            cmd = { 'level':arg_type, 'no_key':['last 5m', 'verbose'] }
            cmd_args_list.append(cmd)

        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output, print_output=False)

    @preposttest_wrapper
    def test_run_contrail_logs_cli_cmd_with_optional_arg_node_type(self):
        '''1.Test to verify contrail-logs cli cmd with various optinal node type args is not broken
           2.Verify the command runs properly and its returning some output
           3.Do not verify the correctness of the output
        '''
        node_type = ['Invalid','Config', 'Control' ,' Analytics' ,'Compute', 'WebUI', 'Database', 'OpenStack', 'ServerMgr']
        cmd_args_list = []
        for arg_type in node_type:
            cmd = {'node-type':arg_type, 'no_key':['last 5m', 'verbose']}
            cmd_args_list.append(cmd)
        return self.check_cmd_output('contrail-logs', cmd_args_list, check_output=True, print_output=False)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_verify_session_sampling_teardown(self):
        '''
        1.query client session samples
        2.query server session samples
        3.query client session to get number of sessions exported
        4.query session record table for teardown bytes/pkts
        5.query sample count after teardown on server side
        '''
        self.setup_flow_export_rate(100)
        result = True
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.creat_bind_policy(policy_name, rules,self.res.vn1_fixture,self.res.vn2_fixture)
        assert self.res.vn1_fixture.verify_on_setup()
        assert self.res.vn2_fixture.verify_on_setup()
        self.res.verify_common_objects()
        
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        
        assert self.res.vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=self.res.vn2_vm2_fixture)
        time.sleep(10)
        
        src_vn = self.res.vn1_fixture.vn_fq_name
        dst_vn = self.res.vn2_fixture.vn_fq_name
        result = self.verify_session_sampling_teardown(start_time, src_vn, dst_vn)
        
        assert result,'Failed to get expected number of samples'
    #test_verify_session_sampling_teardown
    
    @preposttest_wrapper
    def test_verify_session_table_intra_vn(self):
        '''Verify session tables ,generated stats within vn
        '''
        self.setup_flow_export_rate(100)
        self.res.verify_common_objects()
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        assert self.res.vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=self.res.vn1_vm2_fixture)
        time.sleep(100)
        src_vn = self.res.vn1_fixture.vn_fq_name
        result = self.verify_session_sampling_teardown(start_time, src_vn, src_vn)
        
        assert result,'Failed to get expected number of samples'
    #end test_verify_session_series_table_intra_vn

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_verify_session_series_table_inter_vn(self):
        '''Verify session series table ,generated stats between different vns
        1.query client session samples
        2.query for server ports
        3.sort results by server_port column
        4.verify granularity with T=10
        5.verify sampled bytes
        6.verify logged bytes
        7.query and verify filter by action
        '''
        self.setup_flow_export_rate(100)
        result = True
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.creat_bind_policy(policy_name, rules,self.res.vn1_fixture,self.res.vn2_fixture)
        assert self.res.vn1_fixture.verify_on_setup()
        assert self.res.vn2_fixture.verify_on_setup()
        self.res.verify_common_objects()
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        self.setup_and_create_streams(self.res.vn1_vm1_fixture, self.res.vn2_vm2_fixture)
        src_vn = self.res.vn1_fixture.vn_fq_name
        dst_vn = self.res.vn2_fixture.vn_fq_name
        
        self.verify_session_series_table(start_time, src_vn, dst_vn)
    #test_verify_session_series_table_inter_vn

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_verify_session_record_table_inter_vn(self):
        '''Verify session record table ,generated stats between different vns
        1.query and verify number of client session records
        2.query and verify number of server session records
        3.query with local_ip server_port protocol
        4.query with server_port local_ip filter by server_port
        5.query with client_port remote_ip filter by client_port 
          Total we get three record limit by 2
        6.query with sort_fields
        '''
        self.setup_flow_export_rate(100)
        result = True
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.creat_bind_policy(policy_name, rules,self.res.vn1_fixture,self.res.vn2_fixture)
        assert self.res.vn1_fixture.verify_on_setup()
        assert self.res.vn2_fixture.verify_on_setup()
        self.res.verify_common_objects()
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        self.setup_and_create_streams(self.res.vn1_vm1_fixture, self.res.vn2_vm2_fixture)
        time.sleep(100)
        src_vn = self.res.vn1_fixture.vn_fq_name
        dst_vn = self.res.vn2_fixture.vn_fq_name
        self.verify_session_record_table(start_time, src_vn, dst_vn)
    #test_verify_session_record_table_inter_vn   
    
    @preposttest_wrapper
    def test_verify_session_tables_with_invalid_fields_values(self):
        '''Veify Session tables with invalid_fields_values
        1.query with invalid where parameters
        2.query with session_type server with src_vn and dst_vn refering to client_session
        3.invalid fields
        4.dont give uuid still has to display
        '''
        self.setup_flow_export_rate(100)
        result = True
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.creat_bind_policy(policy_name, rules,self.res.vn1_fixture,self.res.vn2_fixture)
        assert self.res.vn1_fixture.verify_on_setup()
        assert self.res.vn2_fixture.verify_on_setup()
        self.res.verify_common_objects()
        
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        self.setup_and_create_streams(self.res.vn1_vm1_fixture, self.res.vn2_vm2_fixture)
        src_vn = self.res.vn1_fixture.vn_fq_name
        dst_vn = self.res.vn2_fixture.vn_fq_name
        
        ip = self.inputs.collector_ips[0]
        self.logger.info('Verifying session tables with invalid parameters')
        #query with invalid where parameters
        query ='vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=177'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','local_ip','remote_vn','remote_ip',
                'SUM(forward_sampled_pkts)','sample_count'],
            where_clause=query,
            session_type='client')
        if res:
            self.logger.error('Got result with invalid where parameters')
            result = result and False
        self.logger.debug(res)
        
        #query with session_type server with src_vn and dst_vn refering to client_session
        #it should return empty result
        query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','local_ip','remote_vn','remote_ip',
                'SUM(forward_sampled_pkts)','sample_count'],
            where_clause=query,
            session_type='server')
        if res:
            self.logger.error('Got result with invalid session parameters')
            result = result and False
        self.logger.debug(res)
        
        #invalid fields
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionRecordTable',
            start_time=start_time,
            end_time='now',
            select_fields=['forward_flow_uuid',
                       'reverse_flow_uuid', 'vn', 'remote_vn', 'vrouter', 'vrouter_ip'],
            where_clause=query,
            filter='vrouter=vrouter1',
            session_type='client')
        if res:
            self.logger.error('Got result with invalid vrouter filter name ')
            result = result and False
        self.logger.debug(res)
        
        #dont give uuid still has to display
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionRecordTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn', 'remote_vn', 'vrouter', 'vrouter_ip'],
            where_clause=query,
            session_type='client')
        uuid =  ['forward_flow_uuid', 'reverse_flow_uuid']
        if res and not set(uuid) < set(res[0].keys()) :
            self.logger.error('uuid fields were missing in the result')
            result = result and False
        self.logger.debug(res)
        assert result,'Failed to get expected  number of records'

    #end test_verify_session_tables_with_invalid_fields_values
    
    @preposttest_wrapper
    def test_verify_session_table_with_security_tagging(self):
        ''' Test to validate session tables with security tagging
        '''
        self.setup_flow_export_rate(100)
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'udp',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.creat_bind_policy(policy_name, rules,self.res.vn1_fixture,self.res.vn2_fixture)
        assert self.res.vn1_fixture.verify_on_setup()
        assert self.res.vn2_fixture.verify_on_setup()
        self.res.verify_common_objects()
        
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_ip
        vm_host = self.res.vn1_vm1_fixture.inputs.host_data[vm_node_ip]['name']
        
        start_time = self.analytics_obj.getstarttime(vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        self.setup_and_create_streams(self.res.vn1_vm1_fixture, self.res.vn2_vm2_fixture)
        time.sleep(100)
        
        # Verifying session series table

        src_vn = self.res.vn1_fixture.vn_fq_name
        dst_vn = self.res.vn2_fixture.vn_fq_name
        ip = self.inputs.collector_ips[0]
        #Will update once api_calls and fixture support added for tagging
    #end test_verify_session_table_with_security_tagging         
            
