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
import time
import commands
import re
RSYSLOG_CONF_FILE = '/etc/rsyslog.conf'
COLLECTOR_CONF_FILE = '/etc/contrail/contrail-collector.conf'

class TestRsyslog(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(TestRsyslog, self).setUp()
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
        super(TestRsyslog, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

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

    @preposttest_wrapper
    def test_rsyslog_connection_on_provision(self):
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
             "Skiping Test. No client side connection config present")

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
             "Skiping Test. Collector side syslog port not configured.")

        listen_port_match = re.search('[0-9]{1,5}', output)
        listen_port = listen_port_match.group(0)
        if server_port != listen_port:
            self.logger.error(
             "Rsyslog cfg and Collector cfg have different syslog ports.")
            raise self.skipTest(
             "Skiping Test. Collector and rsyslog ports don't match.")

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
# end TestRsyslog
