import os
import re
import sys
import json
import time
import socket
import getpass
import ConfigParser
import ast
from netaddr import *

import fixtures
from fabric.api import env, run , local
from fabric.operations import get, put
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from fabric.contrib.files import exists

from tcutils.util import *
from tcutils.custom_filehandler import *

import subprocess

#monkey patch subprocess.check_output cos its not supported in 2.6
if "check_output" not in dir( subprocess ): # duck punch it in!
    def f(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = f

class ContrailTestInit(fixtures.Fixture):
    def __init__(self, ini_file, stack_user=None, stack_password=None, project_fq_name=None,logger = None  ):
        self.username = 'root'
        self.password = 'c0ntrail123'
        self.api_server_port = '8082'
        self.bgp_port = '8083'
        self.ds_port = '5998'
        self.logger = logger
        self.build_id = None
        self.single_node = self.get_os_env('SINGLE_NODE_IP')
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = {}
        self.report_details_file='report_details.ini'
        self.config = ConfigParser.ConfigParser()
        self.config.read(ini_file)

        self.prov_file = read_config_option(self.config,
                              'Basic', 'provFile', None)
        self.key = read_config_option(self.config,
                              'Basic', 'key', 'key1')
        self.stack_user = stack_user or read_config_option(self.config,
                              'Basic', 'stackUser', 'admin')
        self.stack_password = stack_password or read_config_option(self.config,
                              'Basic', 'stackPassword', 'contrail123')
        self.stack_tenant = read_config_option(self.config,
                              'Basic', 'stackTenant', 'admin')
        self.stack_domain = read_config_option(self.config,
                              'Basic', 'stackDomain', 'default-domain')
        self.project_fq_name = project_fq_name or \
                              [self.stack_domain, self.stack_tenant]
        self.project_name = self.project_fq_name[1]
        self.domain_name = self.project_fq_name[0]
        self.keystone_ip = read_config_option(self.config,
                              'Basic', 'keystone_ip', None)
        self.multi_tenancy = read_config_option(self.config,
                              'Basic', 'multiTenancy', False)
        self.log_scenario = read_config_option(self.config,
                              'Basic', 'logScenario', 'Sanity')
        if 'EMAIL_SUBJECT' in os.environ:
            self.log_scenario = os.environ.get('EMAIL_SUBJECT')
        else:
            self.log_scenario = self.log_scenario
        self.generate_html_report = read_config_option(self.config,
                              'Basic', 'generate_html_report', True)
        self.fixture_cleanup = read_config_option(self.config,
                              'Basic', 'fixtureCleanup', 'yes')
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
        # Mail Setup
        self.smtpServer = read_config_option(self.config,
                              'Mail', 'server', None)
        self.smtpPort = read_config_option(self.config,
                              'Mail', 'port', None)
        self.mailTo = read_config_option(self.config,
                              'Mail', 'mailTo', None)
        self.mailSender = read_config_option(self.config,
                              'Mail', 'mailSender', None)

        self.http_proxy = read_config_option(self.config,
                              'proxy', 'proxy_url', None)
        self.ui_config = read_config_option(self.config,
                              'ui', 'ui_config', None)
        self.ui_browser = read_config_option(self.config,
                              'ui', 'ui_browser', None)
        self.verify_webui = read_config_option(self.config,
                              'ui', 'webui', False)
        self.verify_horizon = read_config_option(self.config,
                              'ui', 'horizon', False)
        if not self.ui_browser and self.verify_webui or self.verify_horizon:
            raise ValueError("Verification via GUI needs 'browser' details. Please set the same.")
        self.devstack = read_config_option(self.config,
                              'devstack', 'devstack', None)
        # router options
        self.mx_rt = read_config_option(self.config,
                              'router', 'route_target', '10003')
        self.router_asn = read_config_option(self.config,
                              'router', 'asn', '64512')
        router_info_tuples_string = read_config_option(self.config,
                              'router', 'router_info', '[]')
        self.ext_routers = ast.literal_eval(router_info_tuples_string)
        self.fip_pool_name = read_config_option(self.config,
                              'router', 'fip_pool_name', 'public-pool')
        self.fip_pool = read_config_option(self.config,
                              'router', 'fip_pool', None)
        self.test_revision = read_config_option(self.config,
                              'repos', 'test_revision', None)
        self.fab_revision = read_config_option(self.config,
                              'repos', 'fab_revision', None)
        # HA setup IPMI username/password 
        self.ha_setup = self.read_config_option('HA', 'ha_setup', None)

        if self.ha_setup == 'True':
            self.ipmi_username = self.read_config_option('HA','ipmi_username','ADMIN')
            self.ipmi_password = self.read_config_option('HA','ipmi_password','ADMIN')
        # debug option
        self.verify_on_setup = read_config_option(self.config,
                              'debug', 'verify_on_setup', False)
        self.stop_on_fail = bool(read_config_option(self.config,
                              'debug', 'stop_on_fail', None))

        self.check_juniper_intranet()

    # end __init__

    def setUp(self):
        super(ContrailTestInit, self).setUp()
        if self.single_node != '':
            self.prov_data = self._create_prov_data()
        else:
            self.prov_data = self._read_prov_file()
        self.build_id = self.get_build_id()

        self.os_type = self.get_os_version()
        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
        # List of service correspond to each module
        self.compute_services = ['contrail-vrouter-agent', 'openstack-nova-compute']
        self.control_services = ['contrail-control']
        self.cfgm_services = ['contrail-api', 'contrail-schema',
                              'contrail-discovery', 'contrail-zookeeper']
        self.webui_services = ['contrail-webui', 'contrail-webui-middleware']
        self.openstack_services = [
            'openstack-cinder-api', 'openstack-cinder-scheduler',
            'openstack-cinder-scheduler', 'openstack-glance-api',
            'openstack-glance-registry', 'openstack-keystone',
            'openstack-nova-api', 'openstack-nova-scheduler',
            'openstack-nova-cert']
        self.collector_services = [
                    'redis', 'contrail-collector', 'contrail-analytics-api', 'contrail-query-engine']
        if self.devstack:
            self.mysql_token = 'contrail123'
        else:
            self.mysql_token = self.get_mysql_token()
        self.copy_fabfile_to_agents()
    # end setUp

    def verify_thru_gui(self):
        '''
        Check if GUI based verification is enabled
        '''
        if self.ui_browser:
            return True
        return False

    def is_gui_based_config(self):
        '''
        Check if objects have to configured via GUI
        '''
        if self.ui_config:
            return self.ui_config
        return False

    def get_os_env(self, var):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return ''
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
                if 'el7' in output:
                    self.os_type[host_ip] = 'redhat'
        return self.os_type
    # end get_os_version

    def read_config_option(self, section, option, default_option):
        ''' Read the config file. If the option/section is not present, return the default_option
        '''
        try:
            val = self.config.get(section, option)
            return val
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default_option
    # end read_config_option

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
        self.cfgm_ips_curr  = []
        self.cfgm_control_ips_curr =[]
        self.cfgm_collector_ips_curr = []
        self.collector_control_ips_curr=[]
        self.compute_ips_curr = []
        self.bgp_ips_curr = []

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
                        if self.ha_setup == 'True':
                            self.openstack_ip = host_ip
                        else:
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

        if json_data.has_key('hosts_ipmi'):
            self.hosts_ipmi = json_data['hosts_ipmi']

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

    def verify_state(self):
        result = True
        for host in self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            if host in self.compute_ips:
                for service in self.compute_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
            if host in self.bgp_ips:
                for service in self.control_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
            if host == self.cfgm_ips:
                for service in self.cfgm_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
            if host in self.collector_ips:
                for service in self.collector_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
            if host == self.webui_ip:
                for service in self.webui_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
            if host == self.openstack_ip:
                for service in self.openstack_services:
                    (state, active_str1, active_str2) = self.get_service_status(host,
                                                                                service, username, password)
                    result = result and self._compare_service_state(
                        host, service, state, 'enabled',
                        active_str1, 'active', active_str2, 'running')
        if not result:
            self.logger.error(
                'One or more process-states are not correct on nodes')
        return result
    # end verify_state

    def verify_control_connection(self, connections):
        self.connections = connections
        self.discovery = self.connections.ds_verification_obj
        return self.discovery.verify_bgp_connection()
    # end verify_control_connection

    def build_compute_to_control_xmpp_connection_dict(self, connections):
        self.connections = connections
        agent_to_control_dct = {}
        for ip in self.compute_ips:
            actual_bgp_peer = []
            inspect_h = self.connections.agent_inspect[ip]
            agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
            for i in xrange(len(agent_xmpp_status)):
                actual_bgp_peer.append(agent_xmpp_status[i]['controller_ip'])
            agent_to_control_dct[ip] = actual_bgp_peer
        return agent_to_control_dct
    # end build_compute_to_control_xmpp_connection_dict

    def reboot(self, host_ip):
        i = socket.gethostbyaddr(host_ip)[0]
        print "rebooting %s" % i
        sudo('reboot')
    # end reboot

    def restart_service(self, service_name, host_ips=[], contrail_service=True):
        result = True
        if len(host_ips) == 0:
            host_ips = self.host_ips
        for host in host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            self.logger.info('Restarting %s.service in %s' %
                             (service_name, self.host_data[host]['name']))
            if contrail_service:
                issue_cmd = 'service %s restart' % (service_name)
            else:
                issue_cmd = 'service %s restart' % (service_name)
            self.run_cmd_on_server(
                host, issue_cmd, username, password, pty=False)
    # end restart_service

    def stop_service(self, service_name, host_ips=[], contrail_service=True):
        result = True
        if len(host_ips) == 0:
            host_ips = self.host_ips
        for host in host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            self.logger.info('Stoping %s.service in %s' %
                             (service_name, self.host_data[host]['name']))
            if contrail_service:
                issue_cmd = 'service %s stop' % (service_name)
            else:
                issue_cmd = 'service %s stop' % (service_name)
            self.run_cmd_on_server(
                host, issue_cmd, username, password, pty=False)
    # end stop_service

    def start_service(self, service_name, host_ips=[], contrail_service=True):
        result = True
        if len(host_ips) == 0:
            host_ips = self.host_ips
        for host in host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            self.logger.info('Starting %s.service in %s' %
                             (service_name, self.host_data[host]['name']))
            if contrail_service:
                issue_cmd = 'service %s start' % (service_name)
            else:
                issue_cmd = 'service %s start' % (service_name)
            self.run_cmd_on_server(
                host, issue_cmd, username, password, pty=False)
    # end start_service

    def _compare_service_state(
        self, host, service, state, state_val, active_str1, active_str1_val,
            active_str2, active_str2_val):
        result = False
        if 'xen' in self.os_type[host] or 'centos' in self.os_type[host]:
            if active_str2 != active_str2_val:
                result = False
                self.logger.warn(
                    'On host %s,Service %s state is (%s) .. NOT Expected !!' %
                    (host, service, active_str2))
        elif 'fc' in self.os_type[host]:
            if (state, active_str1, active_str2) != (state_val, active_str1_val, active_str2_val):
                result = False
                self.logger.warn(
                    'On host %s,Service %s states are %s, %s, %s .. NOT Expected !!' % (host, service,
                                                                                        state, active_str1, active_str2))
        return result
    # end _compare_service_state

    def get_service_status(self, server_ip, service_name, username='root',
                           password='contrail123'):
        state = None
        active_str1 = None
        active_str2 = None
        with hide('everything'):
            with settings(
                host_string=server_ip, username=username, password=password,
                    warn_only=True, abort_on_prompts=False):
                if 'fc' in self.os_type[server_ip]:
                    output = run('systemctl status %s.service | head ' %
                                 (service_name))
                    if service_name not in output:
                        return (None, None, None)
                    match_obj1 = re.search(
                        r'Active: (.*) \((.*)\)', output, re.M | re.I)
                    match_obj2 = re.search(r'Loaded.* (.*)\)',
                                           output, re.M | re.I)
                    if match_obj1:
                        active_str1 = match_obj1.group(1)
                        active_str2 = match_obj1.group(2)
                    if match_obj2:
                        state = match_obj2.group(1)
                elif 'centos' in self.os_type[server_ip] or 'xen' in self.os_type[server_ip]:
                    output = run('/etc/init.d/%s status' % (service_name))
                    if 'running' in output.lower():
                        active_str2 = 'running'
                    else:
                        active_str2 = output
            return (state, active_str1, active_str2)
    # end get_service_status

    def run_provision_control(self, router_asn, api_server_ip, api_server_port, oper):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        bgp_ips = set(self.bgp_ips)
        for host in bgp_ips:
            host_name = self.host_data[host]['name']
            issue_cmd = "python /opt/contrail/utils/provision_control.py --host_name '%s' --host_ip '%s' --router_asn '%s' --api_server_ip '%s' --api_server_port '%s' --oper '%s'" % (
                host_name, host, router_asn, api_server_ip, api_server_port, oper)

            output = self.run_cmd_on_server(
                self.cfgm_ip, issue_cmd, username, password)
            if output.return_code != 0:
                self.logger.exception('Fail to execute provision_control.py')
                return output

    # end run_provision_control

    def get_mysql_token(self):
        username = self.host_data[self.openstack_ip]['username']
        password = self.host_data[self.openstack_ip]['password']
        cmd = 'cat /etc/contrail/mysql.token'
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.openstack_ip),
                password=password, warn_only=True, abort_on_prompts=False):
                if not exists('/etc/contrail/mysql.token'):
                    return None
        return self.run_cmd_on_server(self.openstack_ip, cmd, username, password)
    # end get_mysql_token

    def run_provision_mx(self, api_server_ip, api_server_port, router_name, router_ip, router_asn, oper):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /opt/contrail/utils/provision_mx.py --api_server_ip '%s' --api_server_port '%s' --router_name '%s' --router_ip '%s'  --router_asn '%s' --oper '%s'" % (
            api_server_ip, api_server_port, router_name, router_ip, router_asn, oper)
        output = self.run_cmd_on_server(
            self.cfgm_ip, issue_cmd, username, password)
        if output.return_code != 0:
            self.logger.exception('Fail to execute provision_mx.py')
            return output
    # end run_provision_mx

    def config_route_target(self, routing_instance_name, route_target_number, router_asn, api_server_ip, api_server_port):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /opt/contrail/utils/add_route_target.py --routing_instance_name '%s' --route_target_number '%s' --router_asn '%s' --api_server_ip '%s' --api_server_port '%s'" % (
            routing_instance_name, route_target_number, router_asn, api_server_ip, api_server_port)

        output = self.run_cmd_on_server(
            self.cfgm_ip, issue_cmd, username, password)
        if output.return_code != 0:
            self.logger.exception('Fail to execute add_route_target.py')
            return output
    # end config_route_target

    def configure_mx(self, tunnel_name, bgp_group, cn_ip, mx_ip, mx_rt, mx_as, mx_user, mx_password, ri_name, intf, vrf_target, ri_gateway):

        host_ip_with_subnet = "%s/32" % (cn_ip)

        # Initializing list of command need to be configured in MX
        command_to_push = ['configure']

        # Populating the required command
        ##command_to_push.append("set routing-options dynamic-tunnels tunnel_name source-address %s" %(mx_ip.split('/')[0]))
        #command_to_push.append("set routing-options dynamic-tunnels %s source-address %s" %(tunnel_name,mx_ip))
        #command_to_push.append("set routing-options dynamic-tunnels %s gre" % (tunnel_name ) )
        #command_to_push.append("set routing-options dynamic-tunnels %s destination-networks %s" % (tunnel_name,host_ip_with_subnet))
        #command_to_push.append("set protocols bgp group %s type internal" % (bgp_group))
        ##command_to_push.append("set protocols bgp group %s local-address %s" %(bgp_group,mx_ip.split('/')[0]))
        #command_to_push.append("set protocols bgp group %s local-address %s" %(bgp_group,mx_ip))
        #command_to_push.append("set protocols bgp group %s family inet-vpn unicast" % (bgp_group))
        #command_to_push.append("set protocols bgp group %s neighbor %s" % (bgp_group,cn_ip))
        #command_to_push.append("set routing-instances %s instance-type vrf" % (ri_name))
        #command_to_push.append("set routing-instances %s interface %s" %(ri_name, intf))
        #command_to_push.append("set routing-instances %s vrf-target %s:%s:%s" %(ri_name, vrf_target,mx_as,mx_rt))
        #command_to_push.append("set routing-instances %s vrf-table-label" %(ri_name))
        #command_to_push.append("set routing-instances %s routing-options static route 0.0.0.0/0 next-hop %s" %(ri_name, ri_gateway))
        # command_to_push.append("commit")

        print "Final commad will be pushed to MX"
        print "%s" % command_to_push

        # for command in command_to_push:
        #    output = self.run_cmd_on_server(mx_ip,command,mx_user,mx_password)
        #    if output.return_code != 0:
        #        self.logger.exception('Fail to configure MX')
        #        return output
        command_to_push_string = ";".join(command_to_push)
        output = self.run_cmd_on_server(
            mx_ip, command_to_push_string, mx_user, mx_password)

    # end configure_mx

    def unconfigure_mx(self, tunnel_name, bgp_group):

        # Initializing list of command need to be configured in MX
        command_to_push = ['configure']

        # Populating the required command
        command_to_push.append(
            "delete routing-options dynamic-tunnels %s gre" % (tunnel_name))
        command_to_push.append("delete protocols bgp group %s" % (bgp_group))
        command_to_push.append("commit")

        print "Final commad will be pushed to MX"
        print "%s" % command_to_push

        for command in command_to_push:
            output = self.run_cmd_on_server(
                mx_ip, command, mx_user, mx_password)
            if output.return_code != 0:
                self.logger.exception('Fail to unconfigure MX')
                return output
    # end unconfigure_mx

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,
                          password=None, pty=True):
        self.logger.debug("COMMAND: (%s)" % issue_cmd)
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
                self.logger.debug(output)
                return output
    # end run_cmd_on_server

    def cleanUp(self):
        super(ContrailTestInit, self).cleanUp()

    def log_any_issues(self, test_result):
        ''' Log any issues as seen in test_result (TestResult) object
        '''
        self.logger.info('\n TEST ERRORS AND FAILURES : \n')
        if sys.version_info >= (2, 7):
            self.logger.info(str(test_result.printErrors()))
            print test_result.printErrors()
        for failure_tuple in test_result.failures:
            for item in failure_tuple:
                self.logger.info(item)
                print item
    # end log_any_issues

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
        config.set('Test', 'timestamp', self.ts)
        config.set('Test', 'Report', self.html_log_link)
        config.set('Test', 'LogsLocation', self.log_link)
        config.set('Test', 'Topology', phy_topology)
        #config.write(details_h)

        log_location = ''
        if self.jenkins_trigger:
            log_location = "nodeb10.englab.juniper.net:/cs-shared/test_runs" \
                "/%s/%s" % (self.host_data[self.cfgm_ips[0]]['name'], self.ts) 
            config.set('Test', 'CoreLocation', log_location)

        config.write(details_h)
        details_h.close()
    # end 

    def check_juniper_intranet(self):
        cmd = 'ping -c 5 ntp.juniper.net'
        try:
            # Use http based check if proxy is set.
            if self.http_proxy:
                cmd = "http_proxy=%s wget -O /dev/null --timeout=3 --tries=2 ntp.juniper.net" % self.http_proxy
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            self.is_juniper_intranet = True
            self.logger.debug('Detected to be inside Juniper Network')
        except subprocess.CalledProcessError:
            self.is_juniper_intranet = False
            self.logger.debug('Detected to be outside of Juniper Network')
    # end check_juniper_intranet

    def get_build_id(self):
        if self.build_id:
            return self.build_id
        build_id = None
        cmd = 'contrail-version|grep contrail | head -1 | awk \'{print $2}\''
        tries = 50
        while not build_id and tries:
            try:
                build_id = self.run_cmd_on_server(self.cfgm_ips[0], cmd)
            except NetworkError,e:
                time.sleep(1)
                tries -= 1
                pass
            
        return build_id.rstrip('\n')

    def copy_fabfile_to_agents(self):
        host = {}
        for ip in self.compute_ips:
            host['ip'] = ip
            host['username'] = self.host_data[ip]['username']
            host['password'] = self.host_data[ip]['password']
            copy_file_to_server(host,'tcutils/fabfile.py', '~/','fabfile.py')
    # end copy_fabfile_to_agents

    def get_openstack_release(self):
        with settings(
            host_string='%s@%s' % (
                self.username, self.cfgm_ips[0]),
                password=self.password, warn_only=True, abort_on_prompts=False, debug=True):
            ver = run('contrail-version')
            pkg = re.search(r'contrail-install-packages(.*)~(\w+)(.*)', ver)
            os_release = pkg.group(2)
            self.logger.info("%s" % os_release)
            return os_release
    # end get_openstack_release  

    # Updating cfgm_ip , bgp_ips , compute_ips required for ha testing during node failures .
    def update_ip_curr(self,cfgm_ips = [],cfgm_control_ips=[],bgp_ips=[],compute_ips=[]):
        if cfgm_ips:
            self.cfgm_ips_curr = cfgm_ips
        if cfgm_control_ips:
            self.cfgm_control_ips_curr = cfgm_control_ips
        if bgp_ips:
            self.bgp_ips_curr = bgp_ips
            self.collector_control_ips_curr= bgp_ips
        if compute_ips:
            self.compute_ips_curr = compute_ips

    # resetting cfgm_ip , bgp_ips , compute_ips required for ha testing during node failures .
    def reset_ip_curr(self):
        self.cfgm_ips_curr = []
        self.cfgm_control_ips_curr = []
        self.bgp_ips_curr = []
        self.compute_ips_curr = []
        self.collector_control_ips_curr= []
    # end reset_ip_curr
