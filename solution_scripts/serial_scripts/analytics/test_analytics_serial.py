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
from fabric.api import run, local
from analytics import base
import fixtures
import test


class AnalyticsTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

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
                'contrail-control', [self.inputs.bgp_ips[0]])
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

            self.logger.info("Verifying ObjectXmppConnection \
                                Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res2 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectXmppConnection',
                start_time=start_time1,
                end_time='now',
                select_fields=[
                    'ObjectId',
                    'Source',
                    'ObjectLog',
                    'SystemLog',
                    'Messagetype',
                    'ModuleId',
                    'MessageTS'],
                where_clause=query1)
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
            if not self.res2:
                self.logger.info("query output : %s" % (self.res2))
                st = self.analytics_obj.ops_inspect[
                    self.inputs.collector_ips[0]]. send_trace_to_database(
                    node=self.inputs.collector_names[0],
                    module='QueryEngine',
                    trace_buffer_name='QeTraceBuf')
                self.logger.info("status: %s" % (st))
                result = result and False
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

            if self.res2:
                self.logger.info(
                    "Verifying logs from ObjectXmppConnection table")
                result6 = False
                for elem in self.res2:
                    if re.search('EvTcpConnectFail', str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnectFail log sent")
                        result6 = True
                if not result6:
                    self.logger.warn("EvTcpConnectFail log NOT sent")

            start_time = self.analytics_obj.getstarttime(
                self.inputs.bgp_ips[0])
            start_time1 = self.analytics_obj.getstarttime(
                self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service(
                'contrail-control', [self.inputs.bgp_ips[0]])
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

            self.logger.info("Verifying ObjectXmppConnection \
                            Table through opserver %s.." % (self.inputs.collector_ips[0]))
            self.res2 = self.analytics_obj.ops_inspect[
                self.inputs.collector_ips[0]].post_query(
                'ObjectXmppConnection',
                start_time=start_time1,
                end_time='now',
                select_fields=[
                    'ObjectId',
                    'Source',
                    'ObjectLog',
                    'SystemLog',
                    'Messagetype',
                    'ModuleId',
                    'MessageTS'],
                where_clause=query1)
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
            if not self.res2:
                self.logger.info("query output : %s" % (self.res2))
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

            if self.res2:
                self.logger.info(
                    "Verifying logs from ObjectXmppConnection table")
                result7 = False
                result8 = False
                for elem in self.res2:
                    if re.search('EvXmppOpen', str(elem['ObjectLog'])):
                        self.logger.info("EvXmppOpen log sent")
                        result7 = True
                    if re.search('EvTcpConnected', str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnected log sent")
                        result8 = True
                if not result7:
                    self.logger.warn("EvXmppOpen log NOT sent")
                if not result8:
                    self.logger.warn("EvTcpConnected log NOT sent")
        except Exception as e:
            self.logger.exception("%s" % str(e))
            result = result and False
        finally:
            self.inputs.start_service(
                'contrail-control', [self.inputs.bgp_ips[0]])
            time.sleep(4)
            result = result and result1 and result2 and result3 and result4\
                and result5 and result6 and result7 and result8
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
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]])
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
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]])
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
                'contrail-vrouter-agent', [self.inputs.compute_ips[0]])
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
