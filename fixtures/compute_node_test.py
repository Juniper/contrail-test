import fixtures
from tcutils.commands import execute_cmd
from tcutils.util import retry
from fabric.api import run, local
from fabric.operations import put, get
from fabric.context_managers import settings, hide
import ConfigParser
from datetime import datetime
import re
import time
import tempfile

from common.agent.flow_table import FlowTable, FlowEntry
from tcutils.contrail_status_check import ContrailStatusChecker

PROTO_MAP = {'icmp' : '1',
             '1'    : '1',
             'udp'  : '17',
             '17'   : '17',
             'tcp'  : '6',
             '6'    : '6',
            }

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
        self.agent_conf_file = '/etc/contrail/contrail-vrouter-agent.conf'
        self.connections = connections
        self.inputs = self.connections.inputs
        self.logger = self.inputs.logger
        self.already_present = False
        self.ip = node_ip
        for name, ip in self.inputs.compute_info.iteritems():
            if ip == self.ip:
                self.name = name
                break
        self.new_agent_conf_file = tempfile.NamedTemporaryFile(
            mode='w+t',
            prefix=self.name)
        self.recd_agent_conf = tempfile.NamedTemporaryFile(
            prefix=self.name+'-recd-')

        # /etc/modprobe.d/vrouter.conf
        self.updated_vrouter_conf_file = tempfile.NamedTemporaryFile(
            mode='w+t',
            prefix=self.name+'-vrouter-')
        self.recd_vrouter_conf_file = tempfile.NamedTemporaryFile(
            prefix=self.name+'-vrouter-recd-')
        self.vrouter_conf_file = '/etc/modprobe.d/vrouter.conf'

        self.recd_agent_conf_file = self.recd_agent_conf.name
        self.username = username
        self.password = password
        # set agent params to defaults
        self.default_values = {}
        self.default_values['DEFAULT'] = {
            'flow_cache_timeout': 180,
            'headless_mode': 'false'}
        self.default_values['FLOWS'] = {'max_vm_flows': 100}
        self.max_system_flows = 512000
        self.agent_inspect_h = self.connections.agent_inspect[self.ip]
        self.flow_table = None
        self.agent_generator_name = None
    # end __init__

    def setUp(self):
        super(ComputeNodeFixture, self).setUp()
    # end setUp

    def cleanUp(self):
        super(ComputeNodeFixture, self).cleanUp()
    # end cleanUp

    def get_file(self, source_file, dest_file):
        return self.file_transfer(
            "get",
            source_file,
            dest_file)

    def put_file(self, local_file, remote_file):
        return self.file_transfer(
            "put",
             local_file,
             remote_file)

    def read_agent_config(self):
        self.get_file(self.agent_conf_file,
            self.recd_agent_conf_file)
        self.config = ConfigParser.SafeConfigParser()
        try:
            self.config.read(self.recd_agent_conf_file)
        except ConfigParser.ParsingError as e:
            self.logger.error('Hit Parsing Error!!')
            self.logger.error('---------------------')
            self.logger.error(e)
            self.logger.error('---------------------')

    def dump_config(self):
        for section_name in self.config.sections():
            self.logger.debug('Section: %s' % section_name)
            self.logger.debug(
                '  Options: %s' %
                self.config.options(section_name))
            for name, value in self.config.items(section_name):
                self.logger.debug('  %s = %s' % (name, value))
            self.logger.debug

    def write_agent_config(self):
        with open(self.new_agent_conf_file.name, 'w') as file_to_update:
            self.config.write(file_to_update)

    def execute_cmd(self, cmd):
        return self.inputs.run_cmd_on_server(
            self.ip,
            cmd,
            username=self.username,
            password=self.password)

    def file_transfer(self, type, node_file, local_file):
        with settings(hide('everything'),host_string='%s@%s' % (
            self.username, self.ip), password=self.password, warn_only=True,
            abort_on_prompts=False):
            if type == "get":
                result = get(node_file, local_file)
                self.logger.debug(result)
                if result.failed:
                    self.logger.warn('Failed to get %s(as %s) from %s' % (
                        node_file, local_file, self.ip))
                return result.succeeded
            if type == "put":
                result = put(node_file, local_file)
                self.logger.debug(result)
                if result.failed:
                    self.logger.error('Failed to upload %s(as %s) to %s' % (
                        node_file, local_file, self.ip))
                return result.succeeded
    # end file_transfer

    def set_flow_aging_time(self, flow_cache_timeout=100):
        self.logger.debug(
            'Set flow aging time in node %s to %s' %
            (self.ip, flow_cache_timeout))
        self.read_agent_config()
        self.config.set(
            'DEFAULT',
            'flow_cache_timeout',
            str(flow_cache_timeout))
        self.write_agent_config()
        self.put_file(self.new_agent_conf_file.name, self.agent_conf_file)
        self.get_config_flow_aging_time()
        if self.flow_cache_timeout != flow_cache_timeout:
            self.logger.error(
                "Problem in setting flow_cache_timeout in node %s, expected %s, got %s" %
                (self.name, flow_cache_timeout, self.flow_cache_timeout))
        else:
            self.logger.info(
                "Flow_cache_timeout set to %s on %s" %
                (flow_cache_timeout, self.ip))

    def get_config_flow_aging_time(self):
        self.flow_cache_timeout = int(self.get_option_value('DEFAULT', 'flow_cache_timeout'))
        return self.flow_cache_timeout

    def get_config_per_vm_flow_limit(self):
        self.max_vm_flows = float(self.get_option_value('FLOWS', 'max_vm_flows'))

    def set_per_vm_flow_limit(self, max_vm_flows=75):
        self.logger.info('Set flow limit per VM at %s percent.' % max_vm_flows)
        self.read_agent_config()
        self.config.set('FLOWS', 'max_vm_flows', str(max_vm_flows))
        self.write_agent_config()
        self.put_file(self.new_agent_conf_file.name, self.agent_conf_file)
        self.get_config_per_vm_flow_limit()
        if self.max_vm_flows != float(max_vm_flows):
            self.logger.error(
                "Problem in setting per_vm_flow_limit in node %s, expected %s, got %s" %
                (self.name, max_vm_flows, self.max_vm_flows))
        else:
            self.logger.info(
                "Per_vm_flow_limit set to %s successfully" %
                (max_vm_flows))

    def get_headless_mode(self):
        self.headless_mode = self.get_option_value('DEFAULT', 'headless_mode')

    def get_option_value(self, section_name, option_name):
        self.logger.debug(
            'Get %s in section %s, node %s' %
            (option_name, section_name, self.ip))
        self.read_agent_config()
        try:
            self.config.get(section_name, option_name)
            exists = True
        except ConfigParser.NoOptionError:
            exists = False
            pass
        if exists:
            option_value = self.config.get(
                section_name,
                option_name)
        else:
            option_value = self.default_values[section_name][option_name]
            self.logger.debug(
                "Section: %s, Option: %s not set explicitly in config file, go with default value: %s" %
                (section_name, option_name, option_value))
        return option_value

    def set_headless_mode(self, headless_mode='false'):
        self.logger.info('Set headless_mode in node %s' % (self.ip))
        self.read_agent_config()
        self.config.set('DEFAULT', 'headless_mode', headless_mode)
        self.write_agent_config()
        self.put_file(self.new_agent_conf_file.name, self.agent_conf_file)
        self.get_headless_mode()
        if self.headless_mode != headless_mode:
            self.logger.error(
                "Problem in setting headless_mode in node %s, expected %s, got %s" %
                (self.name, headless_mode, self.headless_mode))
        else:
            self.logger.info(
                "Headless mode set to %s successfully" %
                (headless_mode))

    @retry(delay=5, tries=15)
    def wait_for_vrouter_agent_state(self, state='active'):
        cmd = "contrail-status | grep 'contrail-vrouter-agent'"
        service_status = self.execute_cmd(cmd)
        if state in service_status:
            self.logger.info(
                'contrail-vrouter-agent is in %s state' % state)
            return True
        else:
            self.logger.info(
                '%s' % service_status)
            self.logger.info(
                'Waiting contrail-vrouter-agent to come up to %s state' % state)
            return False
    #end wait_for_vrouter_agent_state

    def sup_vrouter_process_restart(self):
        self.logger.info(
            'Restart supervisor-vrouter process in node %s' %
            (self.ip))
        cmd = "service supervisor-vrouter restart"
        self.execute_cmd(cmd)
        # This value is set based on experiment.. It takes 5secs after process
        # is restarted to start setting up new flows
        self.logger.debug(
            "Wait for contrail-vrouter-agent to be in active state.")
        self.wait_for_vrouter_agent_state(state='active')

    def restart_service(self, service_name):
        ''' Restart any contrail service on this compute node
        '''
        self.inputs.restart_service(service_name, [self.ip])

    def restart_agent(self):
        self.restart_service('contrail-vrouter-agent')

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
            self.logger.debug(
                'Get count of flows in node %s with action %s' %
                (self.ip, action))
            cmd = 'flow -l | grep Action | grep %s | wc -l ' % (action)
            flow_count[action] = self.execute_cmd(cmd)
        now = datetime.now()
        self.logger.info(
            "Flow count @ time %s in node %s is %s" %
            (now, self.name, flow_count))
        return flow_count

    def get_vrouter_matching_flow(self, flow_data, filters='Action:'):
        '''
        This method is only to be used for test cases specific to flow command testing.
        For other test cases, to verify the action method verify_flow_action
            from vrouter/base.py should be used.
        flow_data: dict of 6 tuples to identify the flow
        dict format: flow_data={'src_ip':<src IP>, 'dst_ip':<dst IP>,
                                   'src_port':<src port>, 'dst_port':<dst port>,
                                   'proto':<protocol-integer>, 'vrf':<vrf-id>}
        '''
        cmd = 'flow -l | grep \"%s\|%s\" -A1 | grep \"%s\|%s\" -A1' % (
                           flow_data['src_ip'], flow_data['dst_ip'],
                           flow_data['src_port'], flow_data['dst_port']) + \
                            '| grep \"%s (%s)\" -A2' % (
                               flow_data['proto'], flow_data['vrf']
                               )
        if filters:
            cmd = cmd + '| grep %s' %  filters

        now = datetime.now()
        flow = self.execute_cmd(cmd)
        flow_count = self.execute_cmd(cmd + '| wc -l')
        self.logger.info(
            "Flow count @ time %s in node %s is %s" %
            (now, self.ip, flow_count))
        self.logger.debug(
            "Flow @ time %s in node %s is %s" %
            (now, self.ip, flow))

        return (int(flow_count), flow)

    def get_vrouter_matching_flow_count(self, flow_data_l=[]):
        '''Return dict of flow data from node matching the parameters supplied
        Currently this filters flows based on tx_vm_ip, rx_vm_ip, proto & vrf_id.
        Provide forward & reverse flows to be matched as inputs..

        Alternatively, use get_flow_entry()
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
            self.logger.debug('Command issued: %s, all flows: %s' %(cmd_1, flow_count['all']))
            flow_count['allowed'] += int(self.execute_cmd(cmd_2))
            self.logger.debug('Command issued: %s, allowed flows: %s' %(cmd_2, flow_count['allowed']))
            flow_count['dropped_by_limit'] += int(self.execute_cmd(cmd_3))
            self.logger.debug('Command issued: %s, Limit dropped flows: %s' %(cmd_3, flow_count['dropped_by_limit']))
        self.logger.info(
            "Flow count in node %s is %s" %
            (self.name, flow_count['allowed']))
        return flow_count

    def get_agent_headless_mode(self):
        result = False
        try:
            self.get_file(self.agent_conf_file,
                self.recd_agent_conf_file)
            self.config=self.read_agent_config()
            opt = self.config.get('DEFAULT','headless_mode')
            if opt == 'true':
                result = True
        except:
            self.logger.info ('Headless mode is not set in the cofig file of agent')

        return result
    # end get_agent_headless_mode

    def set_agent_headless_mode(self):
        """ Reboot the agent to start in headless mode.
        """
        mode = 'true'
        self.logger.info ('Set the agent in headless mode!!!')
        self.get_file(self.agent_conf_file,
            self.recd_agent_conf_file)
        self.read_agent_config()
        self.config.set('DEFAULT', 'headless_mode', mode)
        file= self.write_agent_config()
        self.write_agent_config()
        self.put_file(self.new_agent_conf_file.name, self.agent_conf_file)
        self.sup_vrouter_process_restart()
    # end set_agent_headless_mode

    # Needs implementation
    # def get_OsVersion(self):

    # def get_VrouterReleaseVersion(self):

    # def get_VrouterBuildVersion(self):

    # def get_OS_Release_BuildVersion(self):

    def get_active_controller(self, refresh=False):
        ''' Get the active contol node.
        '''
        if not getattr(self, 'control_node', None) or refresh:
            self.control_node = None
            agent_xmpp_status = self.agent_inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes' \
                        and entry['state'] == 'Established':
                    self.control_node = entry['controller_ip']
                    break
            if not self.control_node:
                self.logger.error('Active controller is not found')
            self.control_node = self.inputs.get_host_ip(self.control_node)
            self.logger.debug('Active controller for agent %s is %s'
                              %(self.ip, self.control_node))
        return self.control_node

    def get_vrf_id(self, vn_fq_name):
        vrf_id = self.agent_inspect_h.get_vna_vrf_id(vn_fq_name)
        if vrf_id:
            return vrf_id[0]
        return None

    def get_flow_table(self, index=None, refresh=True, show_evicted=False):
        ''' Returns FlowTable instance
        '''
        if refresh:
            flow_table_items = self.agent_inspect_h.get_vna_kflowresp(
                index=index, show_evicted=show_evicted)
            self.flow_table = FlowTable(flow_table_items)
        return self.flow_table
    # end get_flow_table

    def get_flow_count(
        self,
        flow_table=None,
        index=None,
        source_ip=None,
        dest_ip=None,
        source_port=None,
        dest_port=None,
        proto=None,
        vrf_id=None,
        refresh=True,
        show_evicted=True):
        '''
        Returns count of matching forward and reverse flows as a tuple
        (forward_flow_count, reverse_flow_count)

        '''
        reqd_entries = {}
        forward_flow_count = 0
        reverse_flow_count = 0
        if refresh or not flow_table:
            flow_table = self.get_flow_table(index=index, refresh=refresh,
                                             show_evicted=show_evicted)

        if index:
            reqd_entries['index'] = index
        if source_ip:
            reqd_entries['sip'] = source_ip
        if dest_ip:
            reqd_entries['dip'] = dest_ip
        if None != source_port:
            reqd_entries['sport'] = str(source_port)
        if None != dest_port:
            reqd_entries['dport'] = str(dest_port)
        if proto:
            reqd_entries['proto'] = PROTO_MAP[proto]
        if vrf_id:
            reqd_entries['vrf_id'] = vrf_id

        for flow_entry_item in flow_table.items:
            if reqd_entries.viewitems() <= flow_entry_item.viewitems():
                forward_flow_count+= 1
                if flow_entry_item['rflow'] != '-1':
                    reverse_flow_count+= 1
        self.logger.debug('Forward and reverse flows for match %s: %s, %s' % (
            reqd_entries, forward_flow_count, reverse_flow_count))
        return (forward_flow_count, reverse_flow_count)
    # end get_flow_count

    def get_flow_entry(
        self,
        flow_table=None,
        index=None,
        source_ip=None,
        dest_ip=None,
        source_port=None,
        dest_port=None,
        proto=None,
        vrf_id=None,
        refresh=True,
        show_evicted=True):
        '''
        Returns tuple of forward and reverse flow instances of FlowEntry class
        Returns (None, None) if not found

        '''
        reqd_entries = {}
        forward_flow = None
        reverse_flow = None
        if refresh or not flow_table:
            flow_table = self.get_flow_table(index=index, refresh=refresh,
                                             show_evicted=show_evicted)

        if index:
            reqd_entries['index'] = index
        if source_ip:
            reqd_entries['sip'] = source_ip
        if dest_ip:
            reqd_entries['dip'] = dest_ip
        if source_port:
            reqd_entries['sport'] = str(source_port)
        if dest_port:
            reqd_entries['dport'] = str(dest_port)
        if proto:
            reqd_entries['proto'] = PROTO_MAP[proto]
        if vrf_id:
            reqd_entries['vrf_id'] = vrf_id

        for flow_entry_item in flow_table.items:
            if reqd_entries.viewitems() <= flow_entry_item.viewitems():
                forward_flow = FlowEntry(flow_entry_item)
                if flow_entry_item['rflow'] != '-1':
                    reverse_flow_item = [x for x 
                        in flow_table.items 
                        if x['index']==forward_flow.r_flow_index][0]
                    reverse_flow = FlowEntry(reverse_flow_item)
                break
        self.logger.debug('Forward flow: %s' % (forward_flow.dump() \
            if forward_flow else None))
        self.logger.debug('Reverse flow: %s' % (reverse_flow.dump() \
            if reverse_flow else None))
        return (forward_flow, reverse_flow)
    # end get_flow_entry

    def delete_all_flows(self):
        return self.agent_inspect_h.delete_all_flows()
    # end delete_all_flows

    def reload_vrouter(self, wait=True):
        '''Reload vrouter module without restarting the compute node
        '''
        self.logger.info('Reloading vrouter module on %s' % (self.ip))
        self.execute_cmd('service supervisor-vrouter stop; '
            'modprobe -r vrouter || rmmod vrouter; '
            'service supervisor-vrouter start')
        if wait:
            status = ContrailStatusChecker(self.inputs)
            status.wait_till_contrail_cluster_stable([self.ip])
    # end reload_vrouter

    def read_vrouter_module_params(self):
        ''' Read /etc/modprobe.d/vrouter.conf and return dict
        '''
        curr_params = {}
        if not self.get_file(self.vrouter_conf_file, 
            self.recd_vrouter_conf_file.name):
            return curr_params

        # Read the file to get any existing params
        try:
            file_h = open(self.recd_vrouter_conf_file.name, 'r')
            content = file_h.readlines()
            file_h.close()
            if content and 'options vrouter' in content[0]:
                line = content[0].split('options vrouter')[1]
                line = line.split()
                curr_params = dict(word.split('=') for word in line)
            else:
                self.logger.debug('Nothing read from %s on %s' %(
                    self.vrouter_conf_file,
                    self.ip))
        except Exception as e:
            self.logger.debug('Unable to read %s due to %s' % (
                self.vrouter_conf_file, e))
        return curr_params
    # end read_vrouter_module_params

    def write_vrouter_module_params(self, params):
        try:
            file_h = open(self.updated_vrouter_conf_file.name, 'w')
            line = 'options vrouter '
            for (name, value) in params.items():
                line+= '%s=%s' % (name, value)
            file_h.write(line)
            file_h.close()
        except Exception as e:
            self.logger.error('Error writing %s' % (
                               self.updated_vrouter_conf_file))
            self.logger.exception(e)
            raise
        return self.put_file(self.updated_vrouter_conf_file.name, self.vrouter_conf_file)
    # end write_vrouter_module_params

    def add_vrouter_module_params(self, params, reload_vrouter=False):
        ''' params is a dict
            Refer https://github.com/Juniper/contrail-controller/wiki/Vrouter-Module-Parameters
        '''
        curr_params = dict(self.read_vrouter_module_params().items() + params.items())
        if not self.write_vrouter_module_params(curr_params):
            self.logger.error('Failed to add %s to %s' % (params,
                self.vrouter_conf_file))
            return False
        if reload_vrouter:
            self.reload_vrouter()
    # end add_vrouter_module_params

    def del_vrouter_module_params(self, params, reload_vrouter=False):
        '''params is a dict
           Refer wiki contrail-controller/wiki/Vrouter-Module-Parameters
        '''
        curr_params = self.read_vrouter_module_params()
        for (key,value) in params.iteritems():
            curr_params.pop(key, None)
        if not self.write_vrouter_module_params(curr_params):
            self.logger.error('Failed to add %s to %s' % (params,
                self.vrouter_conf_file))
            return False

        if reload_vrouter:
            self.reload_vrouter()
    # end del_vrouter_module_params

    def setup_vrouter_module_params(self, params):
        '''Use this to also restore the configs on cleanup
            Useful when you use this class as a Fixture
        '''
        self.add_vrouter_module_params(params, reload_vrouter=True)
        self.addCleanup(self.del_vrouter_module_params, params,
            reload_vrouter=True)
    # end setup_vrouter_module_params

    def get_agent_generator_name(self):
        if not self.agent_generator_name:
            self.agent_generator_name = self.agent_inspect_h.get_generator_name()
        return self.agent_generator_name
    # end get_agent_generator_name

    @property
    def agent_physical_interface(self):
        if not getattr(self, '_agent_phyiscal_interface', None):
            self._agent_phyiscal_interface = self.agent_inspect_h.get_agent_physical_interface()
        return self._agent_phyiscal_interface
