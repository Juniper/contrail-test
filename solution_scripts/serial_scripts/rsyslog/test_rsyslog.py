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
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import copy_file_to_server, retry
from fabric.api import run
from fabric.context_managers import settings
import test
import time
import commands
import re
from tcutils.rsyslog_utils import restart_collector_to_listen_on_port
from tcutils.rsyslog_utils import restart_rsyslog_client_to_send_on_port
from tcutils.rsyslog_utils import update_rsyslog_client_connection_details
from base import BaseRsyslogTest
RSYSLOG_CONF_FILE = '/etc/rsyslog.conf'
COLLECTOR_CONF_FILE = '/etc/contrail/contrail-collector.conf'


class TestRsyslog(BaseRsyslogTest):

    @classmethod
    def setUpClass(cls):
        super(TestRsyslog, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestRsyslog, cls).tearDownClass()
    # end tearDownClass

    @retry(delay=5, tries=3)
    def send_syslog_and_verify_in_db(self, server_ip=None):
        # At this point we are sure that connections were
        # correctly configured for rsyslog.
        # On a retry logic:-
        #     Send syslog message of highest facility and
        #     priority.
        #     Check for the syslog message in the cassandra
        #     db using contrail-logs.
        #     Declare as pass and exit on any successfull try.
        result = False
        cmd = 'logger -p user.crit -t THISISMYTESTLOG '
        log_mesg = 'This is a test log to check rsyslog provisioning.'
        cmd = cmd + '"' + log_mesg + '"'
        for i in range(3):
            reply = commands.getoutput(cmd)
        cmd = "contrail-logs --last 2m --message-type Syslog | "
        cmd = cmd + "grep 'THISISMYTESTLOG'"
        output = self.inputs.run_cmd_on_server(server_ip, cmd,
                             self.inputs.host_data[server_ip]['username'],
                             self.inputs.host_data[server_ip]['password'])
        if log_mesg in output:
            result = True
        return result
    # end send_syslog_and_verify_in_db

    @test.attr(type=['sanity','quick_sanity'])
    @preposttest_wrapper
    def test_rsyslog_sanity_if_provisioned(self):
        """Tests rsyslog connection if provisioned."""
        result = False

        # Check rsyslog.conf file for connections.
        cmd = "grep '@\{1,2\}"
        cmd = cmd+"[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}"
        cmd = cmd+":[0-9]\{1,5\}' "+RSYSLOG_CONF_FILE
        reply = commands.getoutput(cmd)

        # If not present bail out.
        if not reply:
            self.logger.error(
             "No rsyslog connection configurations present on the client side")
            raise self.skipTest(
             "Skipping Test. No client side connection config present")

        # Get the IP address and port number of server/collector.
        ip_match = re.search('[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',
                             reply)
        server_ip = ip_match.group(0)
        port_match = re.search(':[0-9]{1,5}', reply)
        server_port = port_match.group(0)
        server_port = server_port.split(":")[1]

        # Check contrail-collector.conf on the server IP
        # configured in rsyslog.conf.
        cmd = "grep 'syslog_port.=.[0-9]\{1,5\}' "+COLLECTOR_CONF_FILE
        output = self.inputs.run_cmd_on_server(server_ip, cmd,
                                 self.inputs.host_data[server_ip]['username'],
                                 self.inputs.host_data[server_ip]['password'])

        # If syslog_port not configured and not same as
        # rsyslog.conf bail out.
        if not output:
            self.logger.error(
             "Collector is not listening on any port for syslog messages.")
            raise self.skipTest(
             "Skipping Test. Collector side syslog port not configured.")

        listen_port_match = re.search('[0-9]{1,5}', output)
        listen_port = listen_port_match.group(0)
        if server_port != listen_port:
            self.logger.error(
             "Rsyslog cfg and Collector cfg have different syslog ports.")
            raise self.skipTest(
             "Skipping Test. Collector and rsyslog ports don't match.")

        self.logger.info("Collector ip address:- "+server_ip)
        self.logger.info("Collector port no:- "+listen_port)

        # At this point we are sure that connections were
        # correctly configured for rsyslog.
        result = self.send_syslog_and_verify_in_db(server_ip)

        if result is True:
            self.logger.info(
                "Syslog messages are geting into the Cassandra db.")
            self.logger.info("Rsyslog connections are setup properly")
        else:
            self.logger.error(
                "Syslog messages are not present in the Cassandra db.")
            self.logger.error("Rsyslog connections are not setup properly")

        return result

    # end test_rsyslog_connection_on_provision

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
            if not list_of_collector_less_compute:
                self.logger.error(
                "Colud not get a collector less compute node for the test.")
                return False
            comp_node_ip = list_of_collector_less_compute[0]
        except Exception as e:
            self.logger.error(
                "Colud not get a collector less compute node for the test.")
            self.logger.exception(
                "Got exception as %s" % (e))

        # bring up rsyslog client-server connection with udp protocol.
        restart_collector_to_listen_on_port(
            self,
            self.inputs.collector_ips[0])
        restart_rsyslog_client_to_send_on_port(
            self,
            comp_node_ip,
            self.inputs.collector_ips[0])

        # send 10 syslog messages and verify through contrail logs. There might
        # be loss, but few messages should reach. Or else the test fails.

        # copy test files to the compute node.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.cfgm_ips[0]]['username'],
                          self.inputs.cfgm_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.cfgm_ips[0]]['password'],
                      warn_only=True, abort_on_prompts=False):
            host_node = {'username': self.inputs.host_data[
                             comp_node_ip]['username'],
                         'password': self.inputs.host_data[
                             comp_node_ip]['password'],
                         'ip': comp_node_ip}
            path = os.getcwd() + '/serial_scripts/rsyslog/mylogging.py'
            copy_file_to_server(host_node, path, '~/', 'mylogging.py')
            path = os.getcwd() + '/serial_scripts/rsyslog/message.txt'
            copy_file_to_server(host_node, path, '~/', 'message.txt')

        # send 10 messages with delay.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          comp_node_ip]['username'], 
                          comp_node_ip),
                      password=self.inputs.host_data[comp_node_ip]['password'],
                      warn_only=True, abort_on_prompts=False):
            cmd = "chmod 777 ~/mylogging.py"
            run('%s' % (cmd), pty=True)
            cmd = "~/mylogging.py send_10_log_messages_with_delay"
            run('%s' % (cmd), pty=True)

        # verify through contrail logs.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.collector_ips[0]]['username'], 
                          self.inputs.collector_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.collector_ips[0]]['password'],
                      warn_only=True,
                      abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | "
            cmd = cmd + "grep 'Test Syslog Messages being sent.' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) == 0:
                self.logger.error(
                    "No syslog messages in contrail-logs.Seems to be an issue")
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
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          comp_node_ip]['username'], 
                          comp_node_ip),
                      password=self.inputs.host_data[comp_node_ip]['password'],
                      warn_only=True, abort_on_prompts=False):
            cmd = "~/mylogging.py send_10_log_messages"
            run('%s' % (cmd), pty=True)

        # verify through contrail logs.
        time.sleep(2)  # for database sync.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.collector_ips[0]]['username'],
                          self.inputs.collector_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.collector_ips[0]]['password'],
                      warn_only=True,
                      abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | "
            cmd = cmd + "grep 'Test Syslog Messages being sent without delay.' "
            cmd = cmd + "| wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 10:
                self.logger.error(
                    "Seeing message loss in tcp which is unexpected.")
                return False
            else:
                self.logger.info(
                    "Remote syslog message test over TCP passed.")

        # verify 'category' query of contrail logs.
            cmd = "contrail-logs --last 3m --category cron | "
            cmd = cmd + "grep 'Test Syslog Messages being sent without delay.' "
            cmd = cmd + "| wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 10:
                self.logger.error(
                    "'category' based query FAILED.")
                return False
            else:
                self.logger.info(
                    "'category' based query PASSED.")

        # send syslog messages of all facilities and severities and verify.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          comp_node_ip]['username'], 
                          comp_node_ip),
                      password=self.inputs.host_data[comp_node_ip]['password'],
                      warn_only=True, abort_on_prompts=False):
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

        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.collector_ips[0]]['username'],
                          self.inputs.collector_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.collector_ips[0]]['password'],
                      warn_only=True,
                      abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | "
            cmd = cmd + "grep 'Test Message from' > ~/result.txt "
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
            with settings(host_string='%s@%s' % (self.inputs.host_data[
                              self.inputs.collector_ips[0]]['username'],
                              self.inputs.collector_ips[0]),
                          password=self.inputs.host_data[
                              self.inputs.collector_ips[0]]['password'],
                          warn_only=True,
                          abort_on_prompts=False):
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

        # send 100 messages grater than 1024 bytes with a delay of 1 sec 
        # between each message. This delay factor is expected to be brought 
        # down through bug fix.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          comp_node_ip]['username'],
                          comp_node_ip),
                      password=self.inputs.host_data[comp_node_ip]['password'],
                      warn_only=True, abort_on_prompts=False):
            cmd = "~/mylogging.py send_messages_grater_than_1024_bytes"
            run('%s' % (cmd), pty=True, timeout=120)

        # verify all the 10 messages of 1074 bytes are received.
        time.sleep(2)  # for database sync.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.collector_ips[0]]['username'],
                          self.inputs.collector_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.collector_ips[0]]['password'],
                      warn_only=True,
                      abort_on_prompts=False):
            cmd = "contrail-logs --last 3m --message-type Syslog | "
            cmd = cmd + "grep 'This is a 1074 byte message' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) != 100:
                self.logger.error(
                    "Failed to receive all the messages greater than 1024 bytes over a tcp connection.")
                return False
            else:
                self.logger.info(
                    "Successfully received all the messages greater than 1024 bytes over a tcp connection.")

        # setup all nodes to send syslog messages to a single collector and verify,
        # syslog messages are written into the db poperly with the node name
        # tags as expected.
        for each_node_ip in self.inputs.host_ips:
            update_rsyslog_client_connection_details(
                self,
                node_ip=each_node_ip,
                server_ip=self.inputs.collector_ips[0],
                protocol='tcp',
                restart=True)

        # copy test files to all the nodes and send remote syslog test message.
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.cfgm_ips[0]]['username'],
                          self.inputs.cfgm_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.cfgm_ips[0]]['password'],
                      warn_only=True, abort_on_prompts=False):
            for each_node_ip in self.inputs.host_ips:
                host_node = {'username': self.inputs.host_data[
                                 each_node_ip]['username'],
                             'password': self.inputs.host_data[
                                 each_node_ip]['password'],
                             'ip': each_node_ip}
                path = os.getcwd() + '/serial_scripts/rsyslog/mylogging.py'
                copy_file_to_server(host_node, path, '~/', 'mylogging.py')
                path = os.getcwd() + '/serial_scripts/rsyslog/message.txt'
                copy_file_to_server(host_node, path, '~/', 'message.txt')

        for each_node_ip in self.inputs.host_ips:
            with settings(host_string='%s@%s' % (self.inputs.host_data[
                              each_node_ip]['username'],
                              each_node_ip),
                          password=self.inputs.host_data[
                              each_node_ip]['password'],
                          warn_only=True, abort_on_prompts=False):
                cmd = "chmod 777 ~/mylogging.py"
                run('%s' % (cmd), pty=True)
                cmd = "~/mylogging.py send_test_log_message"
                run('%s' % (cmd), pty=True)
                # time.sleep(0.5)

        # verify syslog messages from each node through contrail logs.
        result_flag = 0
        with settings(host_string='%s@%s' % (self.inputs.host_data[
                          self.inputs.collector_ips[0]]['username'],
                          self.inputs.collector_ips[0]),
                      password=self.inputs.host_data[
                          self.inputs.collector_ips[0]]['password'],
                      warn_only=True, abort_on_prompts=False):
            cmd = "contrail-logs --last 2m --message-type Syslog | grep 'Test Syslog Messages from different nodes.'"
            output = run('%s' % (cmd), pty=True)
            for each_host in self.inputs.host_names:
                search_pattern = ' ' + each_host + ' '
                if search_pattern in output:
                    self.logger.info(
                        "Syslog message from host %s received successfully." %
                        (each_host))
                else:
                    self.logger.error(
                        "Syslog message from host %s was not received." %
                        (each_host))
                    result_flag = 1

        if result_flag != 0:
            self.logger.error(
                "Error in transmitting or receiving some syslog messages")
            return False

        return True

    # end test_rsyslog_messages_in_db_through_contrail_logs

# end TestRsyslog
