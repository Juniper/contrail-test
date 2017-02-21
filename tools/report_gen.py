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
import logging

from fabric.api import env, run, cd
from fabric.operations import get, put
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from tcutils.util import *
from tcutils.custom_filehandler import *

CORE_DIR = '/var/crashes'
logging.getLogger("paramiko").setLevel(logging.WARNING)


class ContrailReportInit:

    def __init__(self, ini_file, report_details):
        self.build_id = None
        self.bgp_stress = False
        self.config = ConfigParser.ConfigParser()
        self.config.read(ini_file)
        self.orch = read_config_option(self.config, 'Basic', 'orchestrator',
                                       'openstack')
        self.prov_file = read_config_option(self.config,
                                            'Basic', 'provFile', None)
        self.log_scenario = read_config_option(self.config,
                                               'Basic', 'logScenario', 'Sanity')
        if 'EMAIL_SUBJECT' in os.environ and os.environ['EMAIL_SUBJECT'] != '':
            self.log_scenario = os.environ.get('EMAIL_SUBJECT')
        if 'EMAIL_SUBJECT_PREFIX' in os.environ:
            self.log_scenario = '%s %s' % (os.environ.get('EMAIL_SUBJECT_PREFIX'),
                                           self.log_scenario)
        self.ext_rtr = read_config_option(
            self.config, 'router', 'router_info', 'None')
        self.ui_browser = read_config_option(self.config,
                                             'ui', 'browser', None)
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        for file in os.listdir(log_path):
            if file.startswith("results_summary") and file.endswith(".txt"):
                self.bgp_stress = True

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
        self.core_location = self.ts
        self.single_node = self.get_os_env('SINGLE_NODE_IP')
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        if self.jenkins_trigger:
            self.ts = self.ts + '_' + str(time.time())
        self.report_details_file = report_details
        self.distro = None

    # end __init__

    def setUp(self):
        if self.single_node != '':
            self.prov_data = self._create_prov_data()
        else:
            self.prov_data = self._read_prov_file()
        (self.build_id, self.sku) = self.get_build_id()
        self.setup_detail = '%s %s~%s' % (self.get_distro(), self.build_id,
                                          self.sku)
        self.build_folder = self.build_id + '_' + self.ts
        self.html_log_link = 'http://%s/%s/%s/junit-noframes.html' % (
                             self.web_server, self.web_root, self.build_folder)
        self.log_link = 'http://%s/%s/%s/logs/' % (self.web_server, self.web_root,
                                                   self.build_folder)
        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
        self.sm_pkg = self.get_os_env('SERVER_MANAGER_INSTALLER')
        self.contrail_pkg = self.get_os_env('CONTRAIL_PACKAGE')
        self.puppet_pkg = self.get_os_env('PUPPET_PKG')
        self.write_report_details()
        if self.ui_browser:
            self.upload_png_files()
    # end setUp

    def upload_png_files(self):
        self.build_folder = self.build_id + '_' + self.ts
        self.web_server_path = self.web_server_log_path + \
            '/' + self.build_folder + '/'
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        elem = log_path + '*.png'
        try:
            with hide('everything'):
                with settings(host_string=self.web_server,
                              user=self.web_server_user,
                              password=self.web_server_password,
                              warn_only=True, abort_on_prompts=False):
                    run('mkdir -p %s' % (self.web_server_path))
                    output = put(elem, self.web_server_path)
                    put('logs', self.web_server_path)
        except Exception, e:
            print 'Error occured while uploading the png files to the Web Server ', e
            pass
    # end upload_png_files

    def get_os_env(self, var, default=''):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return default
    # end get_os_env

    #TODO
    # Duplicating code from contrail_test_init.py :(
    # due to legacy..need to cleanup
    def _check_containers(self, host_dict):
        '''
        Find out which components have containers and set
        corresponding attributes in host_dict to True if present
        '''
        cmd = 'docker ps |grep contrail | awk \'{print $NF}\''
        output = self.run_cmd_on_server(host_dict['ip'], cmd)
        attr_list = output.split('\n')
        attr_list = [x.rstrip('\r') for x in attr_list]

        host_dict['containers'] = {}
        for attr in attr_list:
            host_dict['containers'][attr] =  True
        return
    # end _check_containers

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
        self.openstack_ips = [] 
        self.host_data = {}
        self.physical_routers_data = {}
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
            self._check_containers()
            roles = host["roles"]
            for role in roles:
                if role['type'] == 'openstack':
                    self.openstack_ips.append(host_ip)
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
        if json_data.has_key('physical_routers'):
            self.physical_routers_data = json_data['physical_routers']
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
        self.openstack_ips = [single_node]
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

    def _get_stress_test_summary(self):
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        for file in os.listdir(log_path):
            if file.startswith("results_summary") and file.endswith(".txt"):
                file_fq_name = log_path + '/' + file
                f = open(file_fq_name, 'r')
                file_contents = f.read()
                f.close()
        return file_contents
   # end _get_stress_test_summary

    def _get_phy_topology_detail(self):
        detail = ''
        compute_nodes = [self.get_node_name(x) for x in self.compute_ips]
        bgp_nodes = [self.get_node_name(x) for x in self.bgp_ips]
        collector_nodes = [self.get_node_name(x) for x in self.collector_ips]
        cfgm_nodes = [self.get_node_name(x) for x in self.cfgm_ips]
        webui_node = self.get_node_name(self.webui_ip)
        ext_rtr = unicode(self.ext_rtr.strip('[()]').split(',')[0])
        phy_dev = []
        phy_dev = self.physical_routers_data.keys()
        phy_dev.append(ext_rtr)
        if self.orch == 'openstack':
            openstack_nodes = [self.get_node_name(x) for x in self.openstack_ips]
        database_nodes = [self.get_node_name(x) for x in self.database_ips]

        newline = '<br/>'
        detail = newline
        detail += 'DISTRO : %s %s' % (self.get_distro(), newline)
        detail += 'SKU : %s %s' % (self.sku, newline)
        detail += 'Config Nodes : %s %s' % (cfgm_nodes, newline)
        detail += 'Control Nodes : %s %s' % (bgp_nodes, newline)
        detail += 'Compute Nodes : %s %s' % (compute_nodes, newline)
        if self.orch == 'openstack':
            detail += 'Openstack Node : %s %s' % (openstack_nodes, newline)
        detail += 'WebUI Node : %s %s' % (webui_node, newline)
        detail += 'Analytics Nodes : %s %s' % (collector_nodes, newline)
        detail += 'Database Nodes : %s %s' % (database_nodes, newline)
        detail += 'Physical Devices : %s %s' % (phy_dev, newline)
        if self.ui_browser:
            detail += 'Browser : %s %s' % (self.ui_browser, newline)
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

        if (self.sm_pkg or self.contrail_pkg or self.puppet_pkg):
            config.set('Test', 'sm_pkg', self.sm_pkg)
            config.set('Test', 'contrail_pkg', self.contrail_pkg)
            config.set('Test', 'puppet_pkg', self.puppet_pkg)

        if self.bgp_stress:
            bgp_stress_test_summary = self._get_stress_test_summary()
            config.set('Test', 'BGP Stress Test Summary', bgp_stress_test_summary)
        config.set('Test', 'Topology', phy_topology)
        config.set('Test', 'logScenario', self.log_scenario)
        if self.ui_browser:
            config.set('Test', 'Browser', self.ui_browser)

        debug_logs_location = ''
        if self.jenkins_trigger:
            debug_logs_location = "/cs-shared/test_runs" \
                "/%s/%s" % (self.host_data[self.cfgm_ips[0]]['name'], self.core_location)
            config.set('Test', 'CoreLocation', debug_logs_location)
        config.write(details_h)
        details_h.close()
    # end

    def get_build_id(self):
        if self.build_id:
            return self.build_id
        build_id = None
        cmd = 'contrail-version | grep contrail-config | head -1 | awk \'{print $2}\''
        alt_cmd = 'contrail-version | grep contrail-nodemgr | head -1 | awk \'{print $2}\''
        tries = 50
        while not build_id and tries:
            try:
                build_id = self.run_cmd_on_server(self.cfgm_ips[0], cmd)
                if not build_id:
                    build_id = self.run_cmd_on_server(
                        self.cfgm_ips[0], alt_cmd)
            except NetworkError, e:
                time.sleep(1)
                pass
            tries -= 1
        build_sku = self.get_os_env("SKU")
        if build_sku is None:
            container = self.host_data[self.openstack_ips[0]].get(
                            'containers', {}).get('openstack')
            build_sku=get_build_sku(self.openstack_ips[0],self.host_data[self.openstack_ip]['password'],
                                    container=container)
        if (build_id.count('.') > 3):
            build_id=re.match(r'([0-9\.-]*)\.',build_id).group(1)
        return [build_id.rstrip('\n'), build_sku]

    def get_distro(self):
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
            self.distro = self.distro.replace(')', '')
            self.distro = self.distro.replace('(', '')
        except NetworkError, e:
            self.distro = ''
        return self.distro
    # end get_distro

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,
                          password=None, pty=True, as_sudo=True,
                          container=None, detach=None):
        '''
        container : name or id of the container
        '''
        if server_ip in self.host_data.keys():
            if not username:
                username = self.host_data[server_ip]['username']
            if not password:
                password = self.host_data[server_ip]['password']
        if container:
            # If the container does not exist on this host, log it and 
            # run the cmd on the host itself 
            # This helps backward compatibility
            self.logger.debug('Container %s not in host %s, running on '
                ' host itself' % (container, server_ip))
            if not self.host_data[server_ip].get('containers', {}).get(container):
                container = None
        output = run_cmd_on_server(issue_cmd,
                          server_ip,
                          username,
                          password,
                          pty=pty,
                          as_sudo=as_sudo,
                          logger=self.logger,
                          container=container,
                          detach=detach)
        return output
    # end run_cmd_on_server

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

    def get_cores_node(self, node_ip, user, password):
        """Get the list of cores in one of the nodes in the test setup.
        """
        core = ''
        cmd = 'ls core.* 2>/dev/null'
        containers = self.host_data[node_ip].get('containers', {}).keys()
        if not containers:
            core = run_cmd_on_server(cmd, node_ip, user, password)
            return core

        for container in containers:
            with cd(CORE_DIR):
                 output = run_cmd_on_server(cmd, node_ip, user, password,
                            container=container)
                 core = '%s %s' (core, output)
        return core

# end

def main(arg1, arg2):
    obj = ContrailReportInit(arg1, arg2)
    obj.setUp()
    obj.get_cores()

# accept sanity_params.ini and report_details.ini
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
