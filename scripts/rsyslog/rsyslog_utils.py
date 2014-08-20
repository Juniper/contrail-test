from fabric.api import run
from fabric.context_managers import settings
from util import retry


def provision_rsyslog_connections(self, rsyslog_config_param):
    with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]),
                  password=self.inputs.password, warn_only=True, abort_on_prompts=False):
        testbed_file_path = "/opt/contrail/utils/fabfile/testbeds/testbed.py"
        cmd = "grep rsyslog_params " + testbed_file_path
        run_cmd = cmd + " && sed -i \"/syslog_params/c\\" + \
            rsyslog_config_param + "\" " + testbed_file_path
        run_cmd = run_cmd + " || echo \"" + \
            rsyslog_config_param + "\" >> " + testbed_file_path
        output = run(run_cmd)
        run_cmd = "cd /opt/contrail/utils; fab setup_remote_syslog"
        output = run(run_cmd)
# end provision_rsyslog_connections 


@retry(delay=5, tries=10)
def test_connection_function(self, comp_node_ip):
    # send 1 message.
    with settings(host_string='%s@%s' % (self.inputs.username, comp_node_ip),
                  password=self.inputs.password, warn_only=True, abort_on_prompts=False):
        cmd = "chmod 777 ~/mylogging.py"
        run('%s' % (cmd), pty=True)
        cmd = "~/mylogging.py connection_test_message"
        run('%s' % (cmd), pty=True)

    # verify through contrail logs.
    with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.collector_ips[0]),
                  password=self.inputs.password, warn_only=True, abort_on_prompts=False):
        cmd = "contrail-logs --last 3s --message-type Syslog | grep 'This is a connection test message which should reach the collector.' | wc -l"
        output = run('%s' % (cmd), pty=True)
        if int(output) != 1:
            self.logger.error(
                "No syslog messages were received through contrail-logs. Seems to be an issue")
            return False
        elif int(output) == 1:
            self.logger.info(
                "Remote Syslog connection setup passed.")
            return True
# end test_connection_function
