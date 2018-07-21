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
    def test_prouter_connectivity_alarm(self):
        ''' Test to check prouter process connectivity alarm
            Steps:
                1) Check prouter connectivity alarm is not already raised when system is stable
                1) stop tor-agent-* processes
                2) step 1 makes connected_agent_list empty
                3) Verify prouter connectivity alarm gets raised
                4) undo step1
                5) Expect prouter connectivity alarm gets cleared
        '''
        info_str = 'Skipping Test. No BMS details seen in the Test cluster'
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            raise self.skipTest(info_str)
        assert self.analytics_obj.verify_prouter_connectivity_alarm()
        return True
    # end test_prouter_connectivity_alarm

    @preposttest_wrapper
    def test_vrouter_intf_alarm(self):
        ''' Test to check vrouter-interface alarm
            Steps:
                1) Create a vn and a vm
                2) Bring the tap intf of vm down
                3) Verify vrouter intf alarm gets generated for the same
                4) Bring the tap intf of vm up
                5) Verify vrouter intf alarm gets cleared for the same
        '''
        vn_fix = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name='vrouter_intf_alarm_test_vn',
                          subnets=['10.1.1.0/24'],
                          option = 'orch'))
        compute0 = self.inputs.compute_ips[0]
        hostname = self.inputs.host_data[compute0]['name']
        vm_fix = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fix.obj,
                    vm_name='vrouter_intf_alarm_test_vm',
                    image_name='ubuntu',
                    flavor='m1.tiny',
                    node_name=hostname))
        assert vm_fix.verify_on_setup()
        vmi_id = vm_fix.get_vmi_ids().values()[0]
        tap = vm_fix.get_tap_intf_of_vmi(vmi_id)['name']
        host_ip = vm_fix.vm_node_ip
        cmd_down = 'ifconfig ' + tap + ' down'
        cmd_up = 'ifconfig ' + tap + ' up'
        self.inputs.run_cmd_on_server(host_ip, cmd_down)
        assert self.analytics_obj.verify_vrouter_intf_alarm()
        self.inputs.run_cmd_on_server(host_ip, cmd_up)
        assert self.analytics_obj.verify_vrouter_intf_alarm(verify_alarm_cleared=True)
        return True
    # end test_vrouter_intf_alarm

    @preposttest_wrapper
    def test_disk_usage_alarms(self):
        ''' Test to check disk-usage alarms
            Steps:
                1) Create a large file to fill the disk space upto 91%
                2) Expect disk usage alarm to get raised
                3) Verify disk usage alarms for analytics-node, control-node, vrouter, db node and config-node
        '''
        assert self.analytics_obj.verify_disk_usage_alarm()
        return True

    @preposttest_wrapper
    def test_conf_incorrect_alarms(self):
        ''' Test to check conf-incorrect alarms
            Steps:
                1) Change disc_server_ip in contrail-api conf file and restart
                2) Expect process connectivity alarm to get raised
                3) Verify ConfIncorrect alarms for analytics-node, control-node, vrouter, db node and config-node
        '''
        assert self.analytics_obj.verify_conf_incorrect_alarm()
        return True

    @preposttest_wrapper
    def test_contrail_control_process_connectivity_alarm(self):
        ''' Test to check contrail-control process connectivity alarm
            Steps:
                1) Change ifmap user in contrail-control conf file and restart
                2) Expect contrail control  process connectivity alarm to get raised
                3) Verify contrail control process connectivity alarm

        '''
        assert self.analytics_obj.verify_process_connectivity_contrail_control_alarm()
        return True

    @preposttest_wrapper
    def test_partial_sysinfo_config_alarm(self):
        ''' Test to check PartialSysinfoConfig alarm
            Steps:
                1) Change disc_server_ip in contrail-api conf file and restart
                2) Expect partial-sysinfo-config alarm to get raised
                3) Verify PartialSysinfoConfig alarm

        '''
        assert self.analytics_obj.verify_partial_sysinfo_config_alarm()
        return True

    @preposttest_wrapper
    def test_vrouter_agent_process_connectivity_alarm(self):
        ''' Test to check vrouter agent process connectivity alarm
            Steps:
                1) Change ifmap user in contrail-control conf file and restart
                2) Expect process connectivity alarm to get raised
                3) Verify vrouter agent process connectivity alarm
        '''
        assert self.analytics_obj.verify_process_connectivity_vrouter_agent_alarm()
        return True

    @preposttest_wrapper
    def test_address_mismatch_control_alarm(self):
        ''' Test to check contrail AddressMismatchControl alarm
            Steps:
               1) Change hostip in contrail-control conf file and restart
               2) Expect address mismatch alarm to get raised
               3) Verify AddressMismatchControl alarm
        '''
        assert self.analytics_obj.verify_address_mismatch_control_alarm()
        return True

    @preposttest_wrapper
    def test_control_node_bgp_connectivity_alarm(self):
        ''' Test whether contrail bgp connectivity alarm is generated 
            when there is bgp peer mismatch
        '''
        assert self.analytics_obj.verify_bgp_connectivity_alarm()
        return True

    @test.attr(type=['sanity', 'vcenter', 'vcenter_compute'])
    @skip_because(deployer = 'helm')
    @preposttest_wrapper
    def test_cfgm_node_process_status_alarms(self):
        ''' Test whether process status alarm gets generated/cleared
            after stopping the process
            Steps:
            1) Stop process 'contrail-schema'
            2) Verify alarm of process-status type gets generated for contrail-schema
            3) Start process 'contrail-schema'
            4) Verify alarm of process-status type gets cleared for contrail-schema
            5) Repeat step 1 to 4 for all config node processes
        '''

        assert self.analytics_obj.verify_cfgm_alarms()
        return True

    @test.attr(type=['sanity','vcenter', 'vcenter_compute'])
    @skip_because(deployer = 'helm')
    @preposttest_wrapper
    def test_db_node_process_status_alarms(self):
        ''' Test whether process status alarm gets generated/cleared
            after stopping the process
            Steps:
            1) Stop process 'contrail-database'
            2) Verify alarm of process-status type gets generated for contrail-database
            3) Start process 'contrail-database'
            4) Verify alarm of process-status type gets cleared for contrail-database
            5) Repeat step 1 to 4 for all database node processes
        '''

        assert self.analytics_obj.verify_db_alarms()
        return True

    @test.attr(type=['sanity','vcenter', 'vcenter_compute'])
    @skip_because(deployer = 'helm')
    @preposttest_wrapper
    def test_analytics_node_process_status_alarms(self):
        ''' Test whether process status alarm gets generated/cleared
            after stopping the process
            Steps:
            1) Stop process 'contrail-snmp-connector'
            2) Verify alarm of process-status type gets generated for contrail-snmp-collector
            3) Start process 'contrail-snmp-collector'
            4) Verify alarm of process-status type gets cleared for contrail-snmp-collector
            5) Repeat step 1 to 4 for all analytics node processes
        '''
        assert self.analytics_obj.verify_analytics_alarms()
        return True

    @test.attr(type=['sanity','vcenter', 'vcenter_compute'])
    @skip_because(deployer = 'helm')
    @preposttest_wrapper
    def test_control_node_process_status_alarms(self):
        ''' Test whether process status alarm gets generated/cleared
            after stopping the process
            Steps:
            1) Stop process 'contrail-control'
            2) Verify alarm of process-status type gets generated for contrail-control
            3) Start process 'contrail-control'
            4) Verify alarm of process-status type gets cleared for contrail-control
            5) Repeat step 1 to 4 for all control node processes
        '''

        assert self.analytics_obj.verify_control_alarms()
        return True

    @test.attr(type=['cb_sanity', 'sanity','vcenter', 'vcenter_compute'])
    @skip_because(deployer = 'helm')
    @preposttest_wrapper
    def test_vrouter_process_status_alarms(self):
        ''' Test whether process status alarm gets generated/cleared
            after stopping the process
            Steps:
            1) Stop process 'contrail-vrouter-agent'
            2) Verify alarm of process-status type gets generated for contrail-vrouter-agent
            3) Start process 'contrail-database'
            4) Verify alarm of process-status type gets cleared for contrail-vrouter-agent
            5) Repeat step 1 to 4 for all compute node processes
        '''

        assert self.analytics_obj.verify_vrouter_alarms()
        return True

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
                'contrail-control', [self.inputs.bgp_ips[0]],
                container='control')
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
