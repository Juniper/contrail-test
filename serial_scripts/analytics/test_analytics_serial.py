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
from alarm_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_name
from fabric.api import run, local
import fixtures
import test

class AnalyticsTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    def verify_analytics_fns(self, skip_list):
        vn_fix = self.useFixture(VNFixture(self.connections))
        vn_fix.verify_on_setup()
        assert self.connections.analytics_obj.verify_vn_link(vn_fix.vn_fq_name, skip_opservers=skip_list), 'virtual-network link not found'

    def verify_alarm_fns(self, skip_list):
        self.vn_fix.bind_policies([self.policy_fix.policy_fq_name])
        sleep(10)
        assert self.analytics_obj.verify_configured_alarm(
            alarm_type=self.alarm_fix.alarm_fq_name,
            alarm_name=self.vn_fix.vn_fq_name,
            skip_nodes=skip_list), 'Alarm not raised'
        self.vn_fix.unbind_policies(self.vn_fix.vn_id, [self.policy_fix.policy_fq_name])
        assert self.analytics_obj.verify_configured_alarm(
            alarm_type=self.alarm_fix.alarm_fq_name,
            alarm_name=self.vn_fix.vn_fq_name,
            verify_alarm_cleared=True,
            skip_nodes=skip_list), 'Alarm not cleared'

    def setup_objects_for_alarm(self):
        alarm_rule = [{'operation': '>=',
            'operand1': "UveVirtualNetworkConfig.total_acl_rules",
            'operand2': {'json_value': '1'}}]
        self.alarm_fix = self.useFixture(AlarmFixture(
            connections=self.connections,
            alarm_name=get_random_name('vn_acl_rule'),
            uve_keys=['virtual-network']))
        self.alarm_fix.create(self.alarm_fix.configure_alarm_rules(alarm_rule))
        self.logger.info('Alarm %s created successfully' %
                         self.alarm_fix.alarm_name)
        policy = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        self.policy_fix = self.useFixture(PolicyFixture(
                    get_random_name('alarm'),
                    policy, self.inputs, self.connections))
        self.logger.info('Policy %s created successfully' %
                         self.policy_fix.policy_name)
        self.vn_fix = self.useFixture(VNFixture(self.connections))
        self.logger.info('VN %s created successfully' %
                         self.vn_fix.vn_name)
        assert self.alarm_fix.verify_on_setup()
        assert self.policy_fix.verify_on_setup()
        assert self.vn_fix.verify_on_setup()
        self.addCleanup(self.vn_fix.unbind_policies, self.vn_fix.vn_id,
            [self.policy_fix.policy_fq_name])

    def verify_service_failover(self, svc):
        saved_func = self.connections.analytics_obj.has_opserver
        self.connections.analytics_obj.has_opserver = lambda : False
        self.setup_objects_for_alarm()
        try:
            nodes = self.inputs.collector_ips[:]
            for node in nodes:
                self.inputs.stop_container([node], svc)
                self.verify_analytics_fns([node])
                self.verify_alarm_fns([node])
                self.inputs.start_container([node], svc, verify_service=False)
                time.sleep(5)
            node_pairs = [nodes[:i] + nodes[i+1:] for i in range(len(nodes))]
            for pairs in node_pairs:
                self.inputs.stop_container(pairs, svc)
                self.verify_analytics_fns(pairs)
                self.verify_alarm_fns(pairs)
                self.inputs.start_container(pairs, svc, verify_service=False)
                time.sleep(5)
        finally:
            self.connections.analytics_obj.has_opserver = saved_func
            self.inputs.start_container(self.inputs.collector_ips, svc, verify_service=False)
        return True

    @skip_because(ssl_enabled=False, analytics_nodes=3)
    @preposttest_wrapper
    def test_stunnel_failover(self):
        return self.verify_service_failover('stunnel')

    @skip_because(analytics_nodes=3)
    @preposttest_wrapper
    def test_redis_failover(self):
        return self.verify_service_failover('redis')

    @skip_because(analytics_nodes=3)
    @preposttest_wrapper
    def test_analytics_api_failover(self):
        return self.verify_service_failover('analytics-api')

    @preposttest_wrapper
    def test_verify_bgp_peer_object_logs(self):
        ''' Test to validate bgp_peer_object logs

        '''
        if (len(self.inputs.bgp_ips) < 2):
            self.logger.info("bgp ips less than 2...skipping the test...")
            return True
        result = True
        try:
            start_time = self.analytics_obj.getstarttime(
                self.inputs.bgp_ips[0])
            start_time1 = self.analytics_obj.getstarttime(
                self.inputs.compute_ips[0])
            object_id = 'default-domain:default-project:ip-fabric:__default__:' +\
                self.inputs.bgp_names[1] +\
                ':default-domain:default-project:ip-fabric:__default__:'\
                + self.inputs.bgp_names[0]
            object_id1 = self.inputs.bgp_control_ips[0]
            query = '(' + 'ObjectId=' + "".join(object_id.split()) + ')'
            query1 = '(' + 'ObjectId=' + object_id1 + \
                ' AND Source=' + self.inputs.compute_names[0] +\
                ' AND ModuleId=contrail-vrouter-agent)'
#            query1='('+'ObjectId='+ object_id1 +')'
            self.logger.info(
                "Stopping the control node in %s" %
                (self.inputs.bgp_ips[0]))
            self.inputs.stop_service(
                'contrail-control', [self.inputs.bgp_ips[0]],
                container='control')
            self.logger.info(
                "Waiting for the logs to be updated in database..")
            time.sleep(20)
            self.logger.info("Verifying ObjectBgpPeer \
                        Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res1 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectBgpPeer',
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
            #object xmpp_connection module got removed
            if self.res1:
                self.logger.info("Verifying logs from ObjectBgpPeer table")
                result1 = False
                result2 = False
                for elem in self.res1:
                    if re.search(
                        'EvConnectTimerExpired', str(
                            elem['ObjectLog'])):
                        self.logger.info("EvConnectTimerExpired log sent")
                        result1 = True
                    if re.search('EvTcpConnectFail', str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnectFail log sent")
                        result2 = True
                if not result1:
                    self.logger.warn("EvConnectTimerExpired log NOT sent")
                if not result2:
                    self.logger.warn("EvTcpConnectFail log NOT sent")

            start_time = self.analytics_obj.getstarttime(
                self.inputs.bgp_ips[0])
            start_time1 = self.analytics_obj.getstarttime(
                self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service(
                'contrail-control', [self.inputs.bgp_ips[0]],
                container='control')
            self.logger.info(
                "Waiting for the logs to be updated in database..")
            time.sleep(30)
            self.logger.info("Verifying ObjectBgpPeer \
                            Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res1 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectBgpPeer',
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

#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s" % (self.res1))
                st = self.analytics_obj.ops_inspect[
                    self.inputs.collector_ips[0]]. send_trace_to_database(
                    node=self.inputs.collector_names[0],
                    module='QueryEngine',
                    trace_buffer_name='QeTraceBuf')
                self.logger.info("status: %s" % (st))
                result = result and False
            if self.res1:
                self.logger.info("Verifying logs from ObjectBgpPeer table")
                result3 = False
                result4 = False
                result5 = False
                for elem in self.res1:
                    if re.search('EvTcpPassiveOpen', str(elem['ObjectLog'])):
                        self.logger.info("EvTcpPassiveOpen log sent")
                        result3 = True
                    if re.search('OpenConfirm', str(elem['ObjectLog'])):
                        self.logger.info("OpenConfirm log sent")
                        result4 = True
                    if re.search('Established', str(elem['ObjectLog'])):
                        self.logger.info("Established log sent")
                        result5 = True
                if not result3:
                    self.logger.warn("EvTcpPassiveOpen log NOT sent")
                if not result4:
                    self.logger.warn("OpenConfirm log NOT sent")
                if not result5:
                    self.logger.warn("Established log NOT sent")

        except Exception as e:
            self.logger.exception("%s" % str(e))
            result = result and False
        finally:
            self.inputs.start_service(
                'contrail-control', [self.inputs.bgp_ips[0]],
                container='control')
            time.sleep(4)
            result = result and result1 and result2 and result3 and result4\
                and result5 
            assert result
            return True

    @preposttest_wrapper
    def test_verify_xmpp_peer_object_logs(self):
        ''' Test to validate xmpp peer object logs
        '''
        result = True
        try:
            start_time = self.analytics_obj.getstarttime(
                self.inputs.compute_ips[0])
            object_id = self.inputs.bgp_names[
                0] + ':' + self.inputs.compute_control_ips[0]
            query = '(' + 'ObjectId=' + object_id + ')'
            self.logger.info(
                "Stopping the xmpp node in %s" %
                (self.inputs.compute_ips[0]))
            self.inputs.stop_service(
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]],
                container='agent')
            self.logger.info(
                "Waiting for the logs to be updated in database..")
            time.sleep(20)
            self.logger.info("Verifying ObjectXmppPeerInfo \
                        Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res1 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectXmppPeerInfo',
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
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s" % (self.res1))
                st = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].\
                    send_trace_to_database\
                    (node=self.inputs.collector_names[0],
                     module='QueryEngine', trace_buffer_name='QeTraceBuf')
                self.logger.info("status: %s" % (st))
                result = result and False

            start_time = self.analytics_obj.getstarttime(
                self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service(
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]],
                container='agent')
            self.logger.info(
                "Waiting for the logs to be updated in database..")
            time.sleep(30)
            self.logger.info("Verifying ObjectXmppPeerInfo \
                        Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res1 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectXmppPeerInfo',
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
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s" % (self.res1))
                st = self.analytics_obj.ops_inspect[
                    self.inputs.collector_ips[0]].send_trace_to_database(
                    node=self.inputs.collector_names[0],
                    module='QueryEngine',
                    trace_buffer_name='QeTraceBuf')
                self.logger.info("status: %s" % (st))
                result = result and False

        except Exception as e:
            self.logger.exception("%s" % str(e))
            result = result and False
        finally:
            #            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            self.inputs.start_service(
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]],
                container='agent')
            time.sleep(20)
            self.logger.info(
                "Verifying ObjectVRouter Table through opserver %s.." %
                (self.inputs.collector_ips[0]))
            object_id = self.inputs.compute_names[0]
            query = '(' + 'ObjectId=' + object_id + ')'
            self.res1 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectVRouter',
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
            if (self.res1):
                self.logger.info("ObjectVRouter table query passed")
                result = result and True
            else:
                self.logger.warn("ObjectVRouter table query failed")
                result = result and False

            assert result
            return True
