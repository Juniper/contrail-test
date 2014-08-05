import fixtures
from tcutils.commands import execute_cmd
from fabric.api import run,local
from fabric.operations import put, get
from fabric.context_managers import settings
import ConfigParser
from datetime import datetime
import re

class ComputeNodeFixture(fixtures.Fixture):
    """ Fixture to configure, verify agent in compute node...
    Also cover vrouter related operations in the node.
    """
    def __init__(self, connections, node_ip, username='root', password='c0ntrail123'):
        self.agent_conf_file='/etc/contrail/contrail-vrouter-agent.conf'
        self.connections= connections
        self.inputs= self.connections.inputs
        self.logger= self.inputs.logger
        self.already_present= False
        self.ip= node_ip
        self.username= username
        self.password= password
        # set agent params to defaults
        self.max_vm_flows=100
        self.flow_cache_timeout=180
    #end __init__

    def setUp (self):
        super(ComputeNodeFixture, self).setUp()
        self.name= self.execute_cmd('hostname')
        self.local_agent_conf_file='/tmp/contrail-vrouter-agent.conf' + "." + self.name
    #end setUp

    def cleanUp(self):
        super(ComputeNodeFixture, self).cleanUp()
        # not needed for now, as agent config is set outside test...
    #end cleanUp

    def get_agent_conf_file(self):
        self.file_transfer("get",self.agent_conf_file,self.local_agent_conf_file)

    def put_agent_conf_file(self, file):
        self.file_transfer("put",file,"/etc/contrail")

    def read_agent_config(self):
        self.get_agent_conf_file()
        config = ConfigParser.ConfigParser()
        config.read(self.local_agent_conf_file)
        return config

    def write_agent_config(self):
        with open(self.local_agent_conf_file, 'wb') as file_to_update:
            self.config.write(file_to_update)
            file_to_update.close()
            local ("cp %s /tmp/contrail-vrouter-agent.conf" %(self.local_agent_conf_file))
            return "/tmp/contrail-vrouter-agent.conf"

    def execute_cmd (self,cmd):
        with settings(host_string= '%s@%s' %(self.username, self.ip), password=self.password, warn_only=True,
            abort_on_prompts=False):
            return run("%s" %(cmd))

    def file_transfer (self,type,node_file,local_file):
        with settings(host_string= '%s@%s' %(self.username, self.ip), password=self.password, warn_only=True,
            abort_on_prompts=False):
            if type == "get":
                return get(node_file,local_file)
            if type == "put":
                return put(node_file,local_file)

    def set_flow_aging_time(self, flow_cache_timeout=100):
        self.logger.info ('Set flow aging time in node %s to %s' %(self.ip,flow_cache_timeout))
        self.config= self.read_agent_config()
        self.config.set('DEFAULT', 'flow_cache_timeout', flow_cache_timeout)
        file= self.write_agent_config()
        self.put_agent_conf_file(file)
        got= self.get_config_flow_aging_time() 
        if int(got) != flow_cache_timeout:
            self.logger.info ("problem in setting flow_cache_timeout in node %s, expected %s, got %s" %(self.name,flow_cache_timeout,got))
        else:
            self.logger.info ("flow_cache_timeout set to %s successfully" %(flow_cache_timeout))

    def get_config_flow_aging_time(self):
        # This is configured value, not runtime, which needs process restart...
        self.logger.info ('get flow aging time in node %s' %(self.ip))
        self.get_agent_conf_file()
        self.config=self.read_agent_config()
        try:
            self.flow_cache_timeout= self.config.get('DEFAULT', 'flow_cache_timeout')
        except Exception as e:
            print e
            self.logger.info ("Variable not set explicitly in config file, go with default")
        self.logger.info ("self.flow_cache_timeout--> %s" %(self.flow_cache_timeout))
        return self.flow_cache_timeout

    def get_config_per_vm_flow_limit(self):
        # This is configured value, not runtime, which needs process restart...
        self.logger.info ('get per vm flow limit in node %s' %(self.ip))
        self.get_agent_conf_file()
        self.config=self.read_agent_config()
        self.max_vm_flows= self.config.get('FLOWS', 'max_vm_flows')
        self.logger.info ("self.max_vm_flows--> %s" %(self.max_vm_flows))
        return self.max_vm_flows

    def set_per_vm_flow_limit(self,max_vm_flows=75):
        self.logger.info ('Set flow limit per VM as %')
        self.config= self.read_agent_config()
        self.config.set('FLOWS', 'max_vm_flows', max_vm_flows)
        file= self.write_agent_config()
        self.put_agent_conf_file(file)
        got= self.get_config_per_vm_flow_limit()
        if int(got) != max_vm_flows:
            self.logger.info ("problem in setting per_vm_flow_limit in node %s, expected %s, got %s" %(self.name,max_vm_flows, got))
        else:
            self.logger.info ("per_vm_flow_limit set to %s successfully" %(max_vm_flows))

    def sup_vrouter_process_restart(self):
        self.logger.info ('restart supervisor-vrouter process in node %s' %(self.ip))
        cmd= "service supervisor-vrouter restart"
        self.execute_cmd(cmd)

    def sup_vrouter_process_start(self):
        self.logger.info ('start supervisor-vrouter process in node %s' %(self.ip))
        cmd= "service supervisor-vrouter start"
        self.execute_cmd(cmd)

    def sup_vrouter_process_stop(self):
        self.logger.info ('stop supervisor-vrouter process in node %s' %(self.ip))
        cmd= "service supervisor-vrouter stop"
        self.execute_cmd(cmd)
 
    def get_vrouter_flow_count(self):
        # return dict of flow count by action - Forward, Deny, NAT
        flow_count={}
        valid_flow_actions=['F','D','N']
        for action in valid_flow_actions:
            self.logger.info ('Get count of flows in node %s with action %s' %(self.ip,action))
            cmd = 'flow -l | grep Action | grep %s | wc -l ' %(action)
            flow_count[action]= self.execute_cmd(cmd)
        now= datetime.now()
        self.logger.info("flow count @ time %s in node %s is %s" %(now,self.name,flow_count))
        return flow_count

    def reboot_agents_in_headless_mode(self, headless_mode=True):
        """ Reboot all the agents in the topology to start in headless mode.
        """
        try:
            if headless_mode is True:
                cmd = "sed -i '/headless_mode/c\headless_mode=true' /etc/contrail/contrail-vrouter-agent.conf"
            else:
                cmd = "sed -i '/headless_mode/c\# headless_mode=' /etc/contrail/contrail-vrouter-agent.conf"

            for each_ip in self.inputs.compute_ips:
                output = self.inputs.run_cmd_on_server(each_ip,
                                                       cmd,
                                                       self.inputs.username,
                                                       self.inputs.password)
            self.inputs.restart_service('supervisor-vrouter', self.inputs.compute_ips)

        except Exception as e:
            self.logger.exception("Got exception at reboot_agents_in_headless_mode as %s" % (e))
    #end reboot_agents_in_headless_mode

    # Needs implementation
    #def get_OsVersion(self):

    #def get_VrouterReleaseVersion(self):

    #def get_VrouterBuildVersion(self):

    #def get_OS_Release_BuildVersion(self):
