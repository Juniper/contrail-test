import re

from common.vrouter.base import BaseVrouterTest

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
                                               cmd, container='analytics')
        digits = re.findall('\d+', output)
        if digits:
            return digits[0]
        else:
            self.logger.debug('No flows seen in collector for cmd %s' % (cmd))
            return None
    # end get_flows_exported

    def setup_flow_export_rate(self, value):
        ''' Set flow export rate and handle the cleanup
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        current_rate = vnc_lib_fixture.get_flow_export_rate()
        vnc_lib_fixture.set_flow_export_rate(value)
        self.addCleanup(vnc_lib_fixture.set_flow_export_rate, current_rate)
    # end setup_flow_export_rate

