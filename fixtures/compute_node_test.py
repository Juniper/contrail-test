import fixtures
from tcutils.commands import execute_cmd
from fabric.api import run, local
from fabric.operations import put, get
from fabric.context_managers import settings
import ConfigParser
from datetime import datetime
import re
import time
import tempfile


class ComputeNodeFixture(fixtures.Fixture):

    """ Fixture to configure, verify agent in compute node...
    Also cover vrouter related operations in the node.
    """

    def __init__(
            self,
            connections,
            node_ip,
            username='root',
            password='c0ntrail123'):
        self.agent_conf_dir = '/etc/contrail/'
        self.agent_conf_file = self.agent_conf_dir + \
            'contrail-vrouter-agent.conf'
        self.connections = connections
        self.inputs = self.connections.inputs
        self.logger = self.inputs.logger
        self.already_present = False
        self.ip = node_ip
        for name, ip in self.inputs.compute_info.iteritems():
            if ip == self.ip:
                self.name = name
                break
        self.local_agent_conf_file = tempfile.NamedTemporaryFile(
            mode='w',
            prefix=self.name)
        self.username = username
        self.password = password
        # set agent params to defaults
        self.max_vm_flows = 100
        self.flow_cache_timeout = 180
    # end __init__

    def setUp(self):
        super(ComputeNodeFixture, self).setUp()
    # end setUp

    def cleanUp(self):
        super(ComputeNodeFixture, self).cleanUp()
    # end cleanUp

    def get_agent_conf_file(self):
        self.file_transfer(
            "get",
            self.agent_conf_file,
            self.local_agent_conf_file)

    def put_agent_conf_file(self, file):
        self.file_transfer("put", file, self.agent_conf_file)

    def read_agent_config(self):
        self.get_agent_conf_file()
        config = ConfigParser.ConfigParser()
        config.read(self.local_agent_conf_file.name)
        return config

    def write_agent_config(self):
        with open(self.local_agent_conf_file.name, 'w') as file_to_update:
            self.config.write(file_to_update)
            return self.local_agent_conf_file.name

    def execute_cmd(self, cmd):
        return self.inputs.run_cmd_on_server(
            self.ip,
            cmd,
            username=self.username,
            password=self.password)

    def file_transfer(self, type, node_file, local_file):
        with settings(host_string='%s@%s' % (self.username, self.ip), password=self.password, warn_only=True,
                      abort_on_prompts=False):
            if type == "get":
                return get(node_file, local_file)
            if type == "put":
                return put(node_file, local_file)

    def set_flow_aging_time(self, flow_cache_timeout=100):
        self.logger.info(
            'Set flow aging time in node %s to %s' %
            (self.ip, flow_cache_timeout))
        self.config = self.read_agent_config()
        self.config.set('DEFAULT', 'flow_cache_timeout', flow_cache_timeout)
        file = self.write_agent_config()
        self.put_agent_conf_file(file)
        got = self.get_config_flow_aging_time()
        if int(got) != flow_cache_timeout:
            self.logger.error(
                "Problem in setting flow_cache_timeout in node %s, expected %s, got %s" %
                (self.name, flow_cache_timeout, got))
        else:
            self.logger.info(
                "Flow_cache_timeout set to %s successfully" %
                (flow_cache_timeout))

    def get_config_flow_aging_time(self):
        # This is configured value, not runtime, which needs process restart...
        self.logger.info('Get flow aging time in node %s' % (self.ip))
        self.get_agent_conf_file()
        self.config = self.read_agent_config()
        try:
            self.flow_cache_timeout = self.config.get(
                'DEFAULT',
                'flow_cache_timeout')
        except Exception as e:
            self.logger.info("Caught following exception:%s" % e)
            self.logger.info(
                "Variable not set explicitly in config file, go with default")
        return self.flow_cache_timeout

    def get_config_per_vm_flow_limit(self):
        # This is configured value, not runtime, which needs process restart...
        self.logger.info('Get per vm flow limit in node %s' % (self.ip))
        self.get_agent_conf_file()
        self.config = self.read_agent_config()
        self.max_vm_flows = self.config.get('FLOWS', 'max_vm_flows')
        return self.max_vm_flows

    def set_per_vm_flow_limit(self, max_vm_flows=75):
        self.logger.info('Set flow limit per VM as %')
        self.config = self.read_agent_config()
        self.config.set('FLOWS', 'max_vm_flows', max_vm_flows)
        file = self.write_agent_config()
        self.put_agent_conf_file(file)
        got = self.get_config_per_vm_flow_limit()
        if int(got) != max_vm_flows:
            self.logger.error(
                "Problem in setting per_vm_flow_limit in node %s, expected %s, got %s" %
                (self.name, max_vm_flows, got))
        else:
            self.logger.info(
                "Per_vm_flow_limit set to %s successfully" %
                (max_vm_flows))

    def sup_vrouter_process_restart(self):
        self.logger.info(
            'Restart supervisor-vrouter process in node %s' %
            (self.ip))
        cmd = "service supervisor-vrouter restart"
        self.execute_cmd(cmd)
        # This value is set based on experiment.. It takes 5secs after process
        # is restarted to start setting up new flows
        self.logger.info(
            "Wait for 5 secs for process to complete start/init phase after restart")
        time.sleep(5)

    def sup_vrouter_process_start(self):
        self.logger.info(
            'start supervisor-vrouter process in node %s' %
            (self.ip))
        cmd = "service supervisor-vrouter start"
        self.execute_cmd(cmd)

    def sup_vrouter_process_stop(self):
        self.logger.info(
            'Stop supervisor-vrouter process in node %s' %
            (self.ip))
        cmd = "service supervisor-vrouter stop"
        self.execute_cmd(cmd)

    def get_vrouter_flow_count(self):
        ''' Return dict of flow count by action - Forward, Deny, NAT ...
        Calling code should migrate to get_vrouter_matching_flow_count, which is more specific..
        '''
        flow_count = {}
        valid_flow_actions = ['F', 'D', 'N']
        for action in valid_flow_actions:
            self.logger.info(
                'Get count of flows in node %s with action %s' %
                (self.ip, action))
            cmd = 'flow -l | grep Action | grep %s | wc -l ' % (action)
            flow_count[action] = self.execute_cmd(cmd)
        now = datetime.now()
        self.logger.info(
            "Flow count @ time %s in node %s is %s" %
            (now, self.name, flow_count))
        return flow_count

    def get_vrouter_matching_flow_count(self, flow_data_l=[]):
        '''Return dict of flow data from node matching the parameters supplied
        Currently this filters flows based on tx_vm_ip, rx_vm_ip, proto & vrf_id.
        '''
        flow_count = {'all': 0, 'allowed': 0, 'dropped_by_limit': 0}
        for flow_data in flow_data_l:
            src_ip = flow_data['src_ip']
            dst_ip = flow_data['dst_ip']
            proto = flow_data['proto']
            vrf = flow_data['vrf']
            self.logger.info('Get count of flows in node %s' % (self.ip))
            cmd_1 = 'flow -l | grep %s -A1 | grep %s -A1 | grep \"%s (%s\" -A1 | grep Action | wc -l' % (
                src_ip, dst_ip, proto, vrf)
            cmd_2 = 'flow -l |grep %s -A1| grep %s -A1 |grep \"%s (%s\" -A1 |grep Action |grep -v FlowLim| wc -l' % (
                src_ip, dst_ip, proto, vrf)
            cmd_3 = 'flow -l |grep %s -A1| grep %s -A1 |grep \"%s (%s\" -A1 |grep Action |grep FlowLim| wc -l' % (
                src_ip, dst_ip, proto, vrf)
            flow_count['all'] += int(self.execute_cmd(cmd_1))
            flow_count['allowed'] += int(self.execute_cmd(cmd_2))
            flow_count['dropped_by_limit'] += int(self.execute_cmd(cmd_3))
        self.logger.info(
            "Flow count in node %s is %s" %
            (self.name, flow_count['allowed']))
        return flow_count
    # Needs implementation
    # def get_OsVersion(self):

    # def get_VrouterReleaseVersion(self):

    # def get_VrouterBuildVersion(self):

    # def get_OS_Release_BuildVersion(self):
