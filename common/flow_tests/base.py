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
                " for start time %s, end time %s" % (node_ip, start_time, end_time))

        return sessions_exported

    def setup_flow_export_rate(self, value):
        ''' Set flow export rate and handle the cleanup
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        current_rate = vnc_lib_fixture.get_flow_export_rate()
        vnc_lib_fixture.set_flow_export_rate(value)
        self.addCleanup(vnc_lib_fixture.set_flow_export_rate, current_rate)
    # end setup_flow_export_rate

