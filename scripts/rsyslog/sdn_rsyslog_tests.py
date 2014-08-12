#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import copy
import traceback
import unittest
import fixtures
import testtools
from contrail_test_init import *
from connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from util import fab_put_file_to_vm
from fabric.api import run
from fabric.context_managers import settings
import time
from rsyslog_utils import *


class sdnRsyslog(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(sdnRsyslog, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj
        self.cn_inspect = self.connections.cn_inspect
    # end setUpClass

    def cleanUp(self):
        super(sdnRsyslog, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_rsyslog_messages_in_db_through_contrail_logs(self):
        """Tests related to rsyslog."""
        result = True
        if len(self.inputs.compute_ips) < 1:
            self.logger.warn(
                "Minimum 1 compute nodes are needed for this test to run")
            self.logger.warn(
                "Exiting since this test can't be run.")
            return True

        # get a collector less compute node for the test.
        # so that we can test remote syslog messages.
        try:
            list_of_collector_less_compute = \
                list(set(self.inputs.compute_ips) -
                     set(self.inputs.collector_ips))
            comp_node_ip = list_of_collector_less_compute[0]
        except Exception as e:
            self.logger.error(
                "Colud not get a collector less compute node for the test.")
            self.logger.exception(
                "Got exception as %s" % (e))

        # bring up rsyslog client-server connection with udp protocol.
        restart_collector_to_listen_on_35999(
            self,
            self.inputs.collector_ips[0])
        restart_rsyslog_client_to_send_on_35999(
            self,
            comp_node_ip,
            self.inputs.collector_ips[0])

        # send 10 syslog messages and verify through contrail logs. There might be loss,
        # but few messages should reach. Or else the test fails.

        # copy test files to the compute node.
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            path = self.inputs.test_repo_dir + '/scripts/rsyslog/mylogging.py'
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (self.inputs.username,
                 comp_node_ip),
                password=self.inputs.password,
                src=path,
                dest='~/')
            path = self.inputs.test_repo_dir + '/scripts/rsyslog/message.txt'
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (self.inputs.username,
                 comp_node_ip),
                password=self.inputs.password,
                src=path,
                dest='~/')

        # send 10 messages with delay.
        with settings(host_string='%s@%s' % (self.inputs.username, comp_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "chmod 777 ~/mylogging.py"
            run('%s' % (cmd), pty=True)
            cmd = "~/mylogging.py send_10_log_messages_with_delay"
            run('%s' % (cmd), pty=True)

        # verify through contrail logs.
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | grep 'Test Syslog Messages being sent.' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) == 0:
                self.logger.error(
                    "No syslog messages were through contrail-logs. Seems to be an issue")
                return False
            elif int(output) < 7:
                self.logger.info(
                    "Remote syslog message test connection setup passed.")
                self.logger.warn(
                    "There is 30% message loss. There might be an issue.")
            else:
                self.logger.info(
                    "Remote syslog message test connection setup passed.")
                self.logger.info(
                    "Remote syslog message test over UDP connection passed.")

        # change rsyslog client server connection to tcp.
        update_rsyslog_client_connection_details(
            self,
            node_ip=comp_node_ip,
            server_ip=self.inputs.cfgm_ips[0],
            protocol='tcp',
            restart=True)

        # send 10 log messages without any delay.
        # no message should be lost in a tcp connection.
        with settings(host_string='%s@%s' % (self.inputs.username, comp_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "~/mylogging.py send_10_log_messages"
            run('%s' % (cmd), pty=True)

        # verify through contrail logs.
        time.sleep(2)  # for database sync.
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | grep 'Test Syslog Messages being sent without delay.' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 10:
                self.logger.error(
                    "There was a message loss in a tcp connection which is unexpected.")
                return False
            else:
                self.logger.info(
                    "Remote syslog message test over TCP connection passed.")

        # verify 'category' query of contrail logs.
            cmd = "contrail-logs --last 3m --category cron | grep 'Test Syslog Messages being sent without delay.' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 10:
                self.logger.error(
                    "Unable to retrieve messages from the database using the 'category' query.")
                return False
            else:
                self.logger.info(
                    "Succesfully retrived messages from the database using the 'category' query.")

        # send syslog messages of all facilities and severities and verify.
        with settings(host_string='%s@%s' % (self.inputs.username, comp_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "~/mylogging.py send_messages_of_all_facility_and_severity"
            run('%s' % (cmd), pty=True)

        # verify all facilities and severities through contrail logs.
        time.sleep(2)  # for database sync.
        result_flag = 0
        list_of_facility = ['LOG_KERN', 'LOG_USER', 'LOG_MAIL', 'LOG_DAEMON',
                            'LOG_AUTH', 'LOG_NEWS', 'LOG_UUCP', 'LOG_LOCAL0',
                            'LOG_CRON', 'LOG_SYSLOG', 'LOG_LOCAL1']
        list_of_severity = [
            'LOG_EMERG',
            'LOG_ALERT',
            'LOG_CRIT',
            'LOG_ERR',
            'LOG_WARNING',
            'LOG_NOTICE',
            'LOG_INFO',
            'LOG_DEBUG']

        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | grep 'Test Message from' > ~/result.txt "
            run('%s' % (cmd), pty=True)
            for each_facility in list_of_facility:
                for each_severity in list_of_severity:
                    cmd = "cat ~/result.txt | grep 'Test Message from " + \
                        str(each_facility) + " with severity " + \
                        str(each_severity) + ".' | wc -l"
                    output = run('%s' % (cmd), pty=True)
                    if int(output) != 1:
                        self.logger.error(
                            "Syslog message with facility %s and severity %s was not received" %
                            (each_facility, each_severity))
                        result_flag = 1
                    else:
                        self.logger.info(
                            "Syslog message with facility %s and severity %s was received" %
                            (each_facility, each_severity))

        if result_flag != 0:
            self.logger.error(
                "Error in transmitting or receiving some syslog facilities and severities")
            return False

        # verify 'level' query of contrail logs.
        bug_1353624_fix = False
        if bug_1353624_fix:
            with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                          password=self.inputs.password, warn_only=True, abort_on_prompts=False):
                for each_severity in list_of_severity:
                    cmd = "contrail-logs --last 4m --level " + \
                        str(each_severity) + " | wc -l"
                    output = run('%s' % (cmd), pty=True)
                    if int(output) < 1:
                        self.logger.error(
                            "Syslog message with severity %s was not found." %
                            (each_severity))
                        result_flag = 1
                    else:
                        self.logger.info(
                            "Syslog message with severity %s was found." %
                            (each_severity))

            if result_flag != 0:
                self.logger.error(
                    "Error in transmitting or receiving some syslog severities.")
                return False

        # send 100 messages grater than 1024 bytes with a delay of 1 sec between each message.
        # This delay factor is expected to be brought down through bug fix.
        with settings(host_string='%s@%s' % (self.inputs.username, comp_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "~/mylogging.py send_messages_grater_than_1024_bytes"
            run('%s' % (cmd), pty=True, timeout=120)

        # verify all the 10 messages of 1074 bytes are received.
        time.sleep(2)  # for database sync.
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            cmd = "contrail-logs --last 3m --message-type Syslog | grep 'This is a 1074 byte message' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 100:
                self.logger.error(
                    "Failed to receive all the messages greater than 1024 bytes over a tcp connection.")
                return False
            else:
                self.logger.info(
                    "Successfully received all the messages greater than 1024 bytes over a tcp connection.")

        return True

    # end test_rsyslog_messages_in_db_through_contrail_logs
# end sdnRsyslog
