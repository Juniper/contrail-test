import re

from common.vrouter.base import BaseVrouterTest
from tcutils.util import get_random_name, retry
import random

class FlowTestBase(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(FlowTestBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(FlowTestBase, cls).tearDownClass()
    # end tearDownClass


    def get_flows_exported(self, agent_name, last="1m"):
        ''' agent_name is of format nodek1:Compute:contrail-vrouter-agent:0
        '''
        # TODO
        # Use test-code's api to do query instead of running contrail-stats cmd
        cmd = '''contrail-stats --table SandeshMessageStat.msg_info --select \
"SUM(msg_info.messages)" --last %s --where \
'name=%s' 'msg_info.type=FlowLogDataObject' | tail -1'''  % (last, agent_name)
        output = self.inputs.run_cmd_on_server(self.inputs.collector_ips[0],
                                               cmd, container='analytics-api')
        digits = re.findall('\d+', output)
        if digits:
            return digits[0]
        else:
            self.logger.debug('No flows seen in collector for cmd %s' % (cmd))
            return None
    # end get_flows_exported

    def get_sessions_exported(self, node_ip, start_time, end_time):
        '''
            Gets the total sessions exported within mentioned time range
            by a particular vrouter node
        '''
        table_name = "SessionSeriesTable"
        select_fields = ["forward_action", "sample_count", "vrouter_ip"]

        sessions_exported = 0
        res_s = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
            table_name, start_time=start_time, end_time=end_time,
            select_fields=select_fields, session_type='server')

        res_c = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
            table_name, start_time=start_time, end_time=end_time,
            select_fields=select_fields, session_type='client')

        self.logger.debug("Server sessions: %s\n Client sessions: %s" % (
            res_s, res_c))
        for record in res_s:
            if node_ip == record['vrouter_ip']:
                sessions_exported += record['sample_count']
        for record in res_c:
            if node_ip == record['vrouter_ip']:
                sessions_exported += record['sample_count']
        if not sessions_exported:
            self.logger.debug("No sessions exported from the vrouter %s"\
                " in last %s seconds" % (node_ip, last))

        return sessions_exported

    def setup_flow_export_rate(self, value):
        ''' Set flow export rate and handle the cleanup
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        current_rate = vnc_lib_fixture.get_flow_export_rate()
        vnc_lib_fixture.set_flow_export_rate(value)
        self.addCleanup(vnc_lib_fixture.set_flow_export_rate, current_rate)
    # end setup_flow_export_rate

    def enable_logging_on_compute(self, node_ip, log_type,
            restart_on_cleanup=True):
        ''' Enable local logging on compute node
            log_type: can be agent/syslog
        '''
        container_name = 'agent'
        conf_file = '/etc/contrail/contrail-vrouter-agent.conf'
        service_name = 'contrail-vrouter-agent'
        #Take backup of original conf file to revert back later
        conf_file_backup = '/tmp/'+ get_random_name(conf_file.split('/')[-1])
        cmd = 'cp %s %s' % (conf_file, conf_file_backup)
        status = self.inputs.run_cmd_on_server(node_ip, cmd,
            container=container_name)

        self.addCleanup(
            self.restore_default_config_file, conf_file,
            conf_file_backup, service_name, node_ip, container_name,
            restart_on_cleanup)

        oper = 'set'
        section = 'DEFAULT'
        self.update_contrail_conf(service_name, oper, section,
            'log_flow', 1, node_ip, container_name)
        self.update_contrail_conf(service_name, oper, section,
            'log_local', 1, node_ip, container_name)
        self.update_contrail_conf(service_name, oper, section,
            'log_level', 'SYS_INFO', node_ip, container_name)

        if log_type == 'syslog':
            self.update_contrail_conf(service_name, oper, section,
                'use_syslog', 1, node_ip, container_name)

        self.inputs.restart_service(service_name, [node_ip],
            container=container_name, verify_service=True)
    #end enable_logging_on_compute

    def restore_default_config_file(self, conf_file, conf_file_backup,
            service_name, node_ip, container=None, restart_on_cleanup=True):
        '''Restore config file from conf_file_backup
            conf_file: full path of config file location
            conf_file_backup: full path of backup config file from where it will be restored
            service_name: service name
        '''
        cmd = "mv %s %s" % (conf_file_backup, conf_file)
        output = self.inputs.run_cmd_on_server(
            node_ip,
            cmd,
            container=container)

        if restart_on_cleanup:
            self.inputs.restart_service(service_name, [node_ip],
                container=container, verify_service=True)

    @retry(delay=1, tries=10)
    def search_session_in_log(self, log_file, node_ip, session_log,
            object_name='SessionEndpointObject'):
        '''Search session in log file on node node_ip'''

        container_name = 'agent'
        username = self.inputs.host_data[node_ip]['username']
        password = self.inputs.host_data[node_ip]['password']
        cmd = 'grep -a %s %s | grep -aP "%s"' % (object_name, log_file,
            session_log)
        output = self.inputs.run_cmd_on_server(
            node_ip, cmd, username, password, container=container_name)

        if not output:
            return False, None
        else:
            self.logger.debug("\nSession Expected: %s, \nSession found: %s",
                session_log, output)
            return True, output

    def search_session_in_agent_log(self, node_ip, session_log):
        '''Search session in agent log file'''

        log_file = '/var/log/contrail/contrail-vrouter-agent.log*'
        object_name = 'SessionEndpointObject'
        return self.search_session_in_log(log_file, node_ip, session_log,
            object_name=object_name)

    def search_session_in_syslog(self, node_ip, session_log):
        '''Search session in syslog'''

        log_file = '/var/log/syslog*'
        object_name = 'SessionData'
        return self.search_session_in_log(log_file, node_ip, session_log,
            object_name=object_name)
