import os
import re
import sys
import json
import time
import socket
import smtplib
import getpass
import ConfigParser
import datetime

from fabric.api import env, run, cd
from fabric.operations import get, put
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from tcutils.util import *
from tcutils.custom_filehandler import *

CORE_DIR = '/var/crashes'

class ContrailTestInit:
    def __init__(self, ini_file):
        self.build_id = None
        self.config = ConfigParser.ConfigParser()
        self.config.read(ini_file)
        self.prov_file = read_config_option(self.config,
                              'Basic', 'provFile', None)
        self.log_scenario = read_config_option(self.config,
                              'Basic', 'logScenario', 'Sanity')
        if 'EMAIL_SUBJECT' in os.environ:
            self.log_scenario = os.environ.get('EMAIL_SUBJECT')
        else:
            self.log_scenario = self.log_scenario
        self.keystone_ip = read_config_option(self.config,
                              'Basic', 'keystone_ip', None)
        self.webui_browser = read_config_option(self.config,
                              'webui', 'browser', None)

        # Web Server related details
        self.web_server = read_config_option(self.config,
                              'WebServer', 'host', None)
        self.web_server_user = read_config_option(self.config,
                              'WebServer', 'username', None)
        self.web_server_password = read_config_option(self.config,
                              'WebServer', 'password', None)
        self.web_server_report_path = read_config_option(self.config,
                              'WebServer', 'reportPath', None)
        self.web_server_log_path = read_config_option(self.config,
                              'WebServer', 'logPath', None)
        self.web_root = read_config_option(self.config,
                              'WebServer', 'webRoot', None)
        # Mail Setup
        self.smtpServer = read_config_option(self.config,
                              'Mail', 'server', None)
        self.smtpPort = read_config_option(self.config,
                              'Mail', 'port', '25')
        self.mailTo = read_config_option(self.config,
                              'Mail', 'mailTo', None)
        self.mailSender = read_config_option(self.config,
                              'Mail', 'mailSender', 'contrailbuild@juniper.net')
        self.ts = self.get_os_env('SCRIPT_TS') or \
              datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        self.single_node = self.get_os_env('SINGLE_NODE_IP')
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = {}
        self.report_details_file='report_details.ini'
        self.distro = None

    # end __init__

    def setUp(self):
        if self.single_node != '':
            self.prov_data = self._create_prov_data()
        else:
            self.prov_data = self._read_prov_file()
        (self.build_id, self.sku) = self.get_build_id()
        self.setup_detail = '%s %s~%s' % (self.get_distro_sku(), self.build_id,
                                          self.sku)
        self.build_folder = self.build_id + '_' + self.ts
        self.html_log_link = 'http://%s/%s/%s/junit-noframes.html' % (
                             self.web_server, self.web_root, self.build_folder)
        self.log_link = 'http://%s/%s/%s/logs/' % (self.web_server, self.web_root,
                             self.build_folder)
        self.os_type = self.get_os_version()
        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
        self.write_report_details()
    # end setUp

    def get_os_env(self,var, default=''):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return default
    # end get_os_env

    def get_os_version(self):
        '''
        Figure out the os type on each node in the cluster
        '''
        
        if self.os_type:
            return self.os_type
        for host_ip in self.host_ips:
            username = self.host_data[host_ip]['username']
            password = self.host_data[host_ip]['password']
            with settings(
                host_string='%s@%s' % (username, host_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                output = run('uname -a')
                if 'el6' in output:
                    self.os_type[host_ip] = 'centos_el6'
                if 'fc17' in output:
                    self.os_type[host_ip] = 'fc17'
                if 'xen' in output:
                    self.os_type[host_ip] = 'xenserver'
                if 'Ubuntu' in output:
                    self.os_type[host_ip] = 'ubuntu'
        return self.os_type
    # end get_os_version

    def _read_prov_file(self):
        prov_file = open(self.prov_file, 'r')
        prov_data = prov_file.read()
        json_data = json.loads(prov_data)
        self.host_names = []
        self.cfgm_ip = ''
        self.cfgm_ips = []
        self.cfgm_control_ips = []
        self.cfgm_names = []
        self.collector_ips = []
        self.collector_control_ips = []
        self.collector_names = []
        self.database_ips = []
        self.database_names = []
        self.compute_ips = []
        self.compute_names = []
        self.compute_control_ips = []
        self.compute_info = {}
        self.bgp_ips = []
        self.bgp_control_ips = []
        self.bgp_names = []
        self.ds_server_ip = []
        self.ds_server_name = []
        self.host_ips = []
        self.webui_ips = []
        self.host_data = {}
        self.vgw_data = {}
        for host in json_data['hosts']:
            self.host_names.append(host['name'])
            host_ip = str(IPNetwork(host['ip']).ip)
            host_data_ip = str(IPNetwork(host['data-ip']).ip)
            host_control_ip = str(IPNetwork(host['control-ip']).ip)
            self.host_ips.append(host_ip)
            self.host_data[host_ip] = host
            self.host_data[host_data_ip] = host
            self.host_data[host_control_ip] = host
            self.host_data[host['name']] = host
            self.host_data[host['name']]['host_ip'] = host_ip
            self.host_data[host['name']]['host_data_ip'] = host_data_ip
            self.host_data[host['name']]['host_control_ip'] = host_control_ip
            roles = host["roles"]
            for role in roles:
                if role['type'] == 'openstack':
                    if self.keystone_ip:
                        self.openstack_ip = self.keystone_ip
                    else:
                        self.openstack_ip = host_ip
                        self.keystone_ip = host_ip
                if role['type'] == 'cfgm':
                    self.cfgm_ip = host_ip
                    self.cfgm_ips.append(host_ip)
                    self.cfgm_control_ips.append(host_control_ip)
                    self.cfgm_control_ip = host_control_ip
                    self.cfgm_names.append(host['name'])
                    self.ds_server_ip.append(host_ip)
                    self.ds_server_name.append(host['name'])
                    self.masterhost = self.cfgm_ip
                    self.hostname = host['name']
                if role['type'] == 'compute':
                    self.compute_ips.append(host_ip)
                    self.compute_names.append(host['name'])
                    self.compute_info[host['name']] = host_ip
                    self.compute_control_ips.append(host_control_ip)
                if role['type'] == 'bgp':

                    self.bgp_ips.append(host_ip)
                    self.bgp_control_ips.append(host_control_ip)
                    self.bgp_names.append(host['name'])
#                if role['type'] == 'collector' :
#                    self.collector_ip= host_ip
                if role['type'] == 'webui':
                    self.webui_ip = host_ip
                    self.webui_ips.append(host_ip)
                if role['type'] == 'collector':
                    self.collector_ip = host_ip
                    self.collector_ips.append(host_ip)
                    self.collector_control_ips.append(host_control_ip)
                    self.collector_names.append(host['name'])
                if role['type'] == 'database':
                    self.database_ip = host_ip
                    self.database_ips.append(host_ip)
                    self.database_names.append(host['name'])
            # end for
        # end for
        if json_data.has_key('vgw'):
            self.vgw_data = json_data['vgw']
        return json.loads(prov_data)
    # end _read_prov_file

    def _create_prov_data(self):
        ''' Creates json data for a single node only.

        '''
        single_node = self.single_node
        self.cfgm_ip = single_node
        self.cfgm_ips = [single_node]
        self.bgp_ips = [single_node]
        self.compute_ips = [single_node]
        self.host_ips = [single_node]
        self.collector_ip = single_node
        self.collector_ips = [single_node]
        self.database_ip = single_node
        self.database_ips = [single_node]
        self.webui_ip = single_node
        self.openstack_ip = single_node
        json_data = {}
        self.host_data = {}
        hostname = socket.gethostbyaddr(single_node)[0]
        self.hostname = hostname
        self.compute_names = [self.hostname]
        self.compute_info = {hostname: single_node}
        json_data['hosts'] = [{
            'ip': single_node,
            'name': hostname,
            'username': self.username,
            'password': self.password,
            'roles': [
                {"params": {"collector": hostname, "cfgm": hostname},
                 "type": "bgp"},

                {"params": {"bgp": [hostname, hostname], "cfgm":
                            hostname, "collector": hostname}, "type": "compute"},
                {"params": {"collector": hostname}, "type": "cfgm"},
                {"params": {"cfgm": hostname}, "type": "webui"},
                {"type": "collector"}
            ]
        }]
        self.host_data[single_node] = json_data['hosts'][0]
        return json_data
    # end _create_prov_data

    def get_pwd(self):
        if 'EMAIL_PWD' in os.environ:
            self.p = os.environ.get('EMAIL_PWD')
        else:
            self.p = getpass.getpass(
                prompt='Enter password for  ' + self.mailSender + ' : ')
    # end get_pwd

    def get_node_name(self, ip):
        return self.host_data[ip]['name']
    
    def _get_phy_topology_detail(self):
        detail = ''
        compute_nodes = [self.get_node_name(x) for x in self.compute_ips]
        bgp_nodes = [self.get_node_name(x) for x in self.bgp_ips]
        collector_nodes = [self.get_node_name(x) for x in self.collector_ips]
        cfgm_nodes = [self.get_node_name(x) for x in self.cfgm_ips]
        webui_node = self.get_node_name(self.webui_ip)
        openstack_node =  self.get_node_name(self.openstack_ip)
        database_nodes = [self.get_node_name(x) for x in self.database_ips]
        
        newline = '<br/>'
        detail = newline
        detail += 'Config Nodes : %s %s' % (cfgm_nodes, newline)
        detail += 'Control Nodes : %s %s' % (bgp_nodes, newline)
        detail += 'Compute Nodes : %s %s' % (compute_nodes, newline)
        detail += 'Openstack Node : %s %s' % (openstack_node, newline)
        detail += 'WebUI Node : %s %s' % (webui_node, newline)
        detail += 'Analytics Nodes : %s %s' % (collector_nodes, newline)
        return detail
    # end _get_phy_topology_detail 

    def write_report_details(self):

        phy_topology = self._get_phy_topology_detail()

        details_h = open(self.report_details_file, 'w')
        config = ConfigParser.ConfigParser()
        config.add_section('Test')
        config.set('Test', 'Build', self.build_id)
        config.set('Test', 'Distro_Sku', self.setup_detail)
        config.set('Test', 'timestamp', self.ts)
        config.set('Test', 'Report', self.html_log_link)
        config.set('Test', 'LogsLocation', self.log_link)
        config.set('Test', 'Cores', self.get_cores())
        config.set('Test', 'Topology', phy_topology)
        if self.webui_browser:
            config.set('Test', 'Browser', self.webui_browser)

        log_location = ''
        if self.jenkins_trigger:
            log_location = "nodeb10.englab.juniper.net:/cs-shared/test_runs" \
                "/%s/%s" % (self.host_data[self.cfgm_ips[0]]['name'], self.ts) 
            config.set('Test', 'CoreLocation', log_location)
        config.write(details_h)

        details_h.close()
    # end 

    def get_build_id(self):
        if self.build_id:
            return self.build_id
        build_id = None
        cmd = 'contrail-version|grep contrail-install | head -1 | awk \'{print $2}\''
        tries = 50
        while not build_id and tries:
            try:
                build_id = self.run_cmd_on_server(self.cfgm_ips[0], cmd)
            except NetworkError,e:
                time.sleep(1)
                tries -= 1
                pass
        return build_id.rstrip('\n').split('~')

    def get_distro_sku(self):
        if self.distro:
            return self.distro
        cmd = '''
            if [ -f /etc/lsb-release ]; then (cat /etc/lsb-release | grep DISTRIB_DESCRIPTION | cut -d "=" -f2 )
            else
                cat /etc/redhat-release | sed s/\(Final\)//
            fi
            '''
        try:
            self.distro = self.run_cmd_on_server(self.cfgm_ips[0], cmd)
        except NetworkError,e:
            self.distro = ''
        return self.distro
    # end get_distro_sku

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,password=None, pty=True):
        if server_ip in self.host_data.keys():
            if not username:
                username = self.host_data[server_ip]['username']
            if not password:
                password = self.host_data[server_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, server_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                output = run('%s' % (issue_cmd), pty=pty)
                return output
    # end run_cmd_on_server

    def upload_to_webserver(self,elem):
	log = 'logs'
	print "Web server log path %s"%self.web_server_path

	try:
            with hide('everything'):
		with settings(host_string=self.web_server,
	       	              user=self.web_server_user,
		              password=self.web_server_password,
		              warn_only=True, abort_on_prompts=False):
                    if self.jenkins_trigger:
                        # define report path
                        if sanity_type == "Daily":
                            sanity_report = '%s/daily' % (
                                 self.web_server_report_path)
                        else:
                            sanity_report = '%s/regression' % (
                                 self.web_server_report_path)
                           # report name in format
                           # email_subject_line+time_stamp
                            report_file = "%s-%s.html" % (
                                 '-'.join(log_scenario.split(' ')), ts)
                           # create report path if doesnt exist
                            run('mkdir -p %s' % (sanity_report))
                           # create folder by release name passed from jenkins
                            run('cd %s; mkdir -p %s' %
                                 (sanity_report, branch))
                           # create folder by build_number and create soft
                           # link to original report with custom name
                            run('cd %s/%s; mkdir -p %s; cd %s; ln -s %s/junit-noframes.html %s'
                                        % (sanity_report, branch, build_id, build_id,
                                         self.web_server_path, report_file))

		    run('mkdir -p %s' % (self.web_server_path))
		    output = put(elem, self.web_server_path)
		    put('logs', self.web_server_path)

        except Exception,e:
	    print 'Error occured while uploading the logs to the Web Server ',e
	    return False
        return True

    def get_cores(self):
        '''Get the list of cores in all the nodes in the test setup
        '''
        self.cores = {}
        for host in self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            core = self.get_cores_node(host, username, password)
            if core:
                self.cores.update({host: core.split()})
        # end for
        return self.cores

    def get_cores_node(self,node_ip, user, password):
        """Get the list of cores in one of the nodes in the test setup.
        """
        cores = {}
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (user, node_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                with cd(CORE_DIR):
                    core = run("ls core.* 2>/dev/null")
        return core

# end 

# accept sanity_params.ini, report_details.ini, result.xml
def main(arg1):
    obj = ContrailTestInit(arg1)
    obj.setUp()
    #obj.upload_to_webserver(arg2)
    obj.get_cores()
if __name__ == "__main__":
    main(sys.argv[1])
