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
from fabric.api import env, run, local
from fabric.operations import get, put, reboot
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from fabric.contrib.files import exists

from tcutils.util import *
from tcutils.util import custom_dict, read_config_option, get_build_sku
from tcutils.custom_filehandler import *
from tcutils.config.vnc_introspect_utils import VNCApiInspect
from tcutils.config.ds_introspect_utils import VerificationDsSrv
from keystone_tests import KeystoneCommands
from tempfile import NamedTemporaryFile
import re

import subprocess
import ast
from collections import namedtuple

# monkey patch subprocess.check_output cos its not supported in 2.6
if "check_output" not in dir(subprocess):  # duck punch it in!
    def f(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError(
                'stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(
            stdout=subprocess.PIPE,
            *popenargs,
            **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = f

class TestInputs(object):
    '''
       Class that would populate testbedinfo from parsing the
       .ini and .json input files if provided (or)
       check the keystone and discovery servers to populate
       the same with the certain default value assumptions
    '''
    __metaclass__ = Singleton
    def __init__(self, ini_file=None):
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = custom_dict(self.get_os_version, 'os_type')
        self.config = None
        if ini_file:
            self.config = ConfigParser.ConfigParser()
            self.config.read(ini_file)
        self.orchestrator = read_config_option(self.config,
                                               'Basic', 'orchestrator', 'openstack')
        self.prov_file = read_config_option(self.config,
                                            'Basic', 'provFile', None)
        self.key = read_config_option(self.config,
                                      'Basic', 'key', 'key1')

        self.tenant_isolation = read_config_option(self.config,
            'Basic',
            'tenant_isolation',
            True)

        self.user_isolation = read_config_option(self.config,
            'Basic',
            'user_isolation',
            True)
        # Read admin credentials if any

        self.admin_username = read_config_option(self.config,
            'Basic',
            'adminUser',
            os.getenv('OS_USERNAME', None))
        self.admin_password = read_config_option(self.config,
            'Basic',
            'adminPassword',
            os.getenv('OS_PASSWORD', None))
        self.admin_tenant = read_config_option(self.config,
            'Basic',
            'adminTenant',
            os.getenv('OS_TENANT_NAME', None))

        self.stack_user = read_config_option(
            self.config,
            'Basic',
            'stackUser',
            self.admin_username)
        self.stack_password = read_config_option(
            self.config,
            'Basic',
            'stackPassword',
            self.admin_password)
        self.stack_tenant = read_config_option(
            self.config,
            'Basic',
            'stackTenant',
            self.admin_tenant)
        self.stack_domain = read_config_option(
            self.config,
            'Basic',
            'stackDomain',
            os.getenv('OS_DOMAIN_NAME', 'default-domain'))
        self.region_name = read_config_option(
            self.config,
            'Basic',
            'stackRegion',
            os.getenv('OS_REGION_NAME', 'RegionOne'))

        self.endpoint_type = read_config_option(
            self.config,
            'Basic',
            'endpoint_type',
            'publicURL')
        self.auth_ip = read_config_option(self.config,
                                          'Basic', 'auth_ip', None)
        self.auth_port = read_config_option(self.config,
                                            'Basic', 'auth_port', 5000)
        self.auth_protocol = read_config_option(self.config,
                                            'Basic', 'auth_protocol', 'http')
        self.ds_port = read_config_option(self.config, 'services',
                                          'discovery_port', '5998')
        self.api_server_port = read_config_option(self.config, 'services',
                                          'config_api_port', '8082')
        self.analytics_api_port = read_config_option(self.config, 'services',
                                          'analytics_api_port', '8081')
        self.bgp_port = read_config_option(self.config, 'services',
                                          'control_port', '8083')
        self.dns_port = read_config_option(self.config, 'services',
                                          'dns_port', '8092')
        self.agent_port = read_config_option(self.config, 'services',
                                          'agent_port', '8085')
        self.discovery_ip = read_config_option(self.config, 'services',
                                          'discovery_ip', None)
        self.api_server_ip = read_config_option(self.config, 'services',
                                          'config_api_ip', None)
        self.analytics_api_ip = read_config_option(self.config, 'services',
                                          'analytics_api_ip', None)
        self.contrail_internal_vip = read_config_option(self.config, 'HA',
                                          'contrail_internal_vip', None)
        self.contrail_external_vip = read_config_option(self.config, 'HA',
                                          'contrail_external_vip',
                                          self.contrail_internal_vip)
        self.internal_vip = read_config_option(self.config, 'HA',
                                          'internal_vip', None)
        self.external_vip = read_config_option(self.config, 'HA',
                                          'external_vip', self.internal_vip)
        self.multi_tenancy = read_config_option(self.config,
                                                'Basic', 'multiTenancy', False)
        self.enable_ceilometer = read_config_option(self.config,
                                                    'Basic', 'enable_ceilometer', False)
        self.fixture_cleanup = read_config_option(
            self.config,
            'Basic',
            'fixtureCleanup',
            'yes')
        self.key_filename = read_config_option(self.config, 'Basic',
                                               'key_filename', None)
        self.pubkey_filename = read_config_option(self.config, 'Basic',
                                                  'pubkey_filename', None)
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
        if not self.ui_browser and (self.verify_webui or self.verify_horizon):
            raise ValueError(
                "Verification via GUI needs 'browser' details. Please set the same.")
        self.devstack = read_config_option(self.config,
                                           'devstack', 'devstack', None)
        self.use_devicemanager_for_md5 = read_config_option(
            self.config, 'use_devicemanager_for_md5', 'use_devicemanager_for_md5', False)
        # router options
        self.mx_rt = read_config_option(self.config,
                                        'router', 'route_target', '10003')
        self.router_asn = read_config_option(self.config,
                                             'router', 'asn', '64512')
        router_info_tuples_string = read_config_option(
            self.config,
            'router',
            'router_info',
            '[]')
        self.ext_routers = ast.literal_eval(router_info_tuples_string)
        self.fip_pool_name = read_config_option(
            self.config,
            'router',
            'fip_pool_name',
            'public-pool')
        self.fip_pool = read_config_option(self.config,
                                           'router', 'fip_pool', None)
        if self.fip_pool:
            update_reserve_cidr(self.fip_pool)
        self.public_vn = read_config_option(
            self.config,
            'router',
            'public_virtual_network',
            'public-network')
        self.public_tenant = read_config_option(
            self.config,
            'router',
            'public_tenant_name',
            'public-tenant')

        # HA setup IPMI username/password
        self.ha_setup = read_config_option(self.config, 'HA', 'ha_setup', None)

        if self.ha_setup == True:
            self.ipmi_username = read_config_option(
                self.config,
                'HA',
                'ipmi_username',
                'ADMIN')
            self.ipmi_password = read_config_option(
                self.config,
                'HA',
                'ipmi_password',
                'ADMIN')
        # debug option
        self.verify_on_setup = read_config_option(
            self.config,
            'debug',
            'verify_on_setup',
            True)
        self.stop_on_fail = bool(
            read_config_option(
                self.config,
                'debug',
                'stop_on_fail',
                None))

        self.ha_tmp_list = []
        self.tor_agent_data = {}
        self.sriov_data = {}
        self.dpdk_data = {}
        self.mysql_token = None

        self.public_host = read_config_option(self.config, 'Basic',
                                              'public_host', '10.204.216.50')

        self.prov_file = self.prov_file or self._create_prov_file()
        self.prov_data = self.read_prov_file()
        self.auth_url = os.getenv('OS_AUTH_URL') or \
                        '%s://%s:%s/v2.0'%(self.auth_protocol,
                                           self.auth_ip,
                                           self.auth_port)
        #vcenter server
        self.vcenter_dc = read_config_option(
           self.config, 'vcenter', 'vcenter_dc', None)
        self.vcenter_server = read_config_option(
           self.config, 'vcenter', 'vcenter_server', None)
        self.vcenter_port = read_config_option(
           self.config, 'vcenter', 'vcenter_port', None)
        self.vcenter_username = read_config_option(
           self.config, 'vcenter', 'vcenter_username', None)
        self.vcenter_password = read_config_option(
           self.config, 'vcenter', 'vcenter_password', None)
        self.vcenter_compute = read_config_option(
           self.config, 'vcenter', 'vcenter_compute', None)
        if 'vcenter' in self.prov_data.keys():
            try:
                 self.dv_switch = self.prov_data['vcenter'][0]['dv_switch']['dv_switch_name']
            except Exception as e:
                 pass

        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
        # List of service correspond to each module
        self.compute_services = [
            'contrail-vrouter-agent',
            'supervisor-vrouter',
            'contrail-vrouter-nodemgr']
        self.control_services = ['contrail-control', 'supervisor-control',
                                 'contrail-control-nodemgr', 'contrail-dns',
                                 'contrail-named']
        self.cfgm_services = [
            'contrail-api',
            'contrail-schema',
            'contrail-discovery',
            'supervisor-config',
            'contrail-config-nodemgr',
            'contrail-device-manager']
        self.webui_services = ['contrail-webui', 'contrail-webui-middleware',
                               'supervisor-webui']
        self.openstack_services = [
            'openstack-cinder-api', 'openstack-cinder-scheduler',
            'openstack-cinder-scheduler', 'openstack-glance-api',
            'openstack-glance-registry', 'openstack-keystone',
            'openstack-nova-api', 'openstack-nova-scheduler',
            'openstack-nova-cert']
        self.collector_services = [
            'contrail-collector', 'contrail-analytics-api',
            'contrail-query-engine', 'contrail-analytics-nodemgr',
            'supervisor-analytics',
            'contrail-snmp-collector', 'contrail-topology']
        self.correct_states = ['active', 'backup']

    def get_os_env(self, var, default=''):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return default
    # end get_os_env

    def get_os_version(self, host_ip):
        '''
        Figure out the os type on each node in the cluster
        '''
        output = None
        if host_ip in self.os_type:
            return self.os_type[host_ip]
        username = self.host_data[host_ip]['username']
        password = self.host_data[host_ip]['password']
        with hide('output','running','warnings'):
            with settings(host_string='%s@%s' % (username, host_ip),
                          password=password, warn_only=True,
                          abort_on_prompts=False):
                output = run('uname -a')
        if 'el6' in output:
            self.os_type[host_ip] = 'centos_el6'
        elif 'fc17' in output:
            self.os_type[host_ip] = 'fc17'
        elif 'xen' in output:
            self.os_type[host_ip] = 'xenserver'
        elif 'Ubuntu' in output:
            self.os_type[host_ip] = 'ubuntu'
        elif 'el7' in output:
            self.os_type[host_ip] = 'redhat'
        else:
            raise KeyError('Unsupported OS')
        return self.os_type[host_ip]
    # end get_os_version

    def read_prov_file(self):
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
        self.database_control_ips = []
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
        self.tor = {}
        self.tor_hosts_data = {}
        self.physical_routers_data = {}

        self.esxi_vm_ips = {}
        self.vgw_data = {}
        for host in json_data['hosts']:
            host['name'] = host['name']
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
                    self.openstack_ip = host_ip
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
                    self.database_control_ips.append(host_control_ip)
            # end for
        # end for

        if 'vgw' in json_data:
            self.vgw_data = json_data['vgw']

        if 'xmpp_auth_enable' in json_data:
            self.xmpp_auth_enable = json_data['xmpp_auth_enable']
        if 'xmpp_dns_auth_enable' in json_data:
            self.xmpp_dns_auth_enable = json_data['xmpp_dns_auth_enable']

        if 'tor_agent' in json_data:
            self.tor_agent_data = json_data['tor_agent']
        if 'sriov' in json_data:
            self.sriov_data = json_data['sriov']
        if 'dpdk' in json_data:
            self.dpdk_data = json_data['dpdk']
        if 'tor_hosts' in json_data:
            self.tor_hosts_data = json_data['tor_hosts']

        if 'physical_routers' in json_data:
            self.physical_routers_data = json_data['physical_routers']
        self._process_tor_data()

        if 'esxi_vms' in json_data:
            self.esxi_vm_ips = json_data['esxi_vms']
        if 'hosts_ipmi' in json_data:
            self.hosts_ipmi = json_data['hosts_ipmi']

        if not self.auth_ip:
            if self.ha_setup and self.external_vip:
                self.auth_ip = self.external_vip
            else:
                self.auth_ip = self.openstack_ip
        return json_data
    # end read_prov_file

    def _process_tor_data(self):
        for (device_name, device_dict) in self.physical_routers_data.iteritems():
            device_dict['tor_agents'] = []
            device_dict['tor_agent_dicts'] = []
            device_dict['tor_tsn_ips'] = []
            for (host_str, ta_list) in self.tor_agent_data.iteritems():
                for ta in ta_list:
                    if ta['tor_name'] == device_dict['name']:
                        ta['tor_agent_host_string'] = host_str
                        device_dict['tor_ovs_port'] = ta['tor_ovs_port']
                        device_dict['tor_ovs_protocol'] = ta[
                            'tor_ovs_protocol']
                        device_dict['tor_agents'].append('%s:%s' % (host_str,
                                                                    ta['tor_agent_id']))
                        device_dict['tor_agent_dicts'].append(ta)
                        device_dict['tor_tsn_ips'].append(ta['tor_tsn_ip'])
                        if self.ha_setup == True:
                            device_dict['controller_ip'] = self.contrail_external_vip
                        else:
                            device_dict['controller_ip'] = ta['tor_tsn_ip']

    # end _process_tor_data

    def get_host_ip(self, name):
        ip = self.host_data[name]['host_ip']
        if ip in self.ha_tmp_list:
            ip = self.contrail_external_vip
        return ip

    def get_host_data_ip(self, name):
        ip = self.host_data[name]['host_data_ip']
        if ip in self.ha_tmp_list:
            ip = self.contrail_internal_vip
        return ip

    def get_node_name(self, ip):
        return self.host_data[ip]['name']

    def get_computes(self, cfgm_ip):
        kwargs = {'stack_user': self.stack_user,
                  'stack_password': self.stack_password,
                  'project_name': self.stack_tenant,
                  'auth_ip': self.auth_ip,
                  'auth_port': self.auth_port,
                  'api_server_port': self.api_server_port,
                 }
        api_h = VNCApiInspect(cfgm_ip, inputs=type('', (), kwargs))
        return api_h.get_computes()

    def _create_prov_file(self):
        ''' Creates json data for a single node only.
            Optional Env variables:
              openstack creds:
               * OS_USERNAME (default: admin)
               * OS_PASSWORD (default: contrail123)
               * OS_TENANT_NAME (default: admin)
               * OS_DOMAIN_NAME (default: default-domain)
               * OS_AUTH_URL (default: http://127.0.0.1:5000/v2.0)
               * OS_INSECURE (default: True)
              login creds:
               * USERNAME (default: root)
               * PASSWORD (default: c0ntrail123)
              contrail service:
               * DISCOVERY_IP (default: neutron-server ip fetched from keystone endpoint)
        '''
        pattern = 'http[s]?://(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}):(?P<port>\d+)'
        if self.orchestrator.lower() != 'openstack':
            raise Exception('Please specify testbed info in $PARAMS_FILE '
                            'under "Basic" section, keyword "provFile"')
        if self.orchestrator.lower() == 'openstack':
            auth_url = os.getenv('OS_AUTH_URL', None) or \
                       'http://127.0.0.1:5000/v2.0'
            insecure = bool(os.getenv('OS_INSECURE', True))
            keystone = KeystoneCommands(self.stack_user,
                                        self.stack_password,
                                        self.stack_tenant,
                                        auth_url,
                                        region_name=self.region_name,
                                        insecure=insecure)
            match = re.match(pattern, keystone.get_endpoint('identity')[0])
            self.auth_ip = match.group('ip')
            self.auth_port = match.group('port')

        # Assume contrail-config runs in the same node as neutron-server
        discovery = os.getenv('DISCOVERY_IP', None) or \
                    (keystone and re.match(pattern,
                    keystone.get_endpoint('network')[0]).group('ip'))
        ds_client = VerificationDsSrv(discovery)
        services = ds_client.get_ds_services().info
        cfgm = database = services['config']
        collector = services['analytics']
        bgp = services['control-node']
        openstack = [self.auth_ip] if self.auth_ip else []
        computes = self.get_computes(cfgm[0])
        data = {'hosts': list()}
        hosts = cfgm + database + collector + bgp + computes + openstack
        username = os.getenv('USERNAME', 'root')
        password = os.getenv('PASSWORD', 'c0ntrail123')
        for host in set(hosts):
            with settings(host_string='%s@%s' % (username, host),
                          password=password, warn_only=True):
                hname = run('hostname')
            hdict = {'ip': host,
                     'data-ip': host,
                     'control-ip': host,
                     'username': username,
                     'password': password,
                     'name': hname,
                     'roles': [],
                    }
            if host in cfgm:
                hdict['roles'].append({'type': 'cfgm'})
            if host in collector:
                hdict['roles'].append({'type': 'collector'})
            if host in database:
                hdict['roles'].append({'type': 'database'})
            if host in bgp:
                hdict['roles'].append({'type': 'bgp'})
            if host in computes:
                hdict['roles'].append({'type': 'compute'})
            if host in openstack:
                hdict['roles'].append({'type': 'openstack'})
            data['hosts'].append(hdict)
        tempfile = NamedTemporaryFile(delete=False)
        with open(tempfile.name, 'w') as fd:
            json.dump(data, fd)
        return tempfile.name
    # end _create_prov_data

    def get_mysql_token(self):
        if self.mysql_token:
            return self.mysql_token
        if self.orchestrator == 'vcenter':
            return None
        if self.devstack:
            return 'contrail123'
        username = self.host_data[self.openstack_ip]['username']
        password = self.host_data[self.openstack_ip]['password']
        cmd = 'cat /etc/contrail/mysql.token'
        with hide('everything'):
            with settings(
                    host_string='%s@%s' % (username, self.openstack_ip),
                    password=password, warn_only=True, abort_on_prompts=False):
                if not exists('/etc/contrail/mysql.token'):
                    return None
        self.mysql_token = self.run_cmd_on_server(
            self.openstack_ip,
            cmd,
            username,
            password)
        return self.mysql_token
    # end get_mysql_token

    def get_build_sku(self):
        return get_build_sku(self.openstack_ip,
                             self.host_data[self.openstack_ip]['password'],
                             self.host_data[self.openstack_ip]['username'])

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,
                          password=None, pty=True):
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


class ContrailTestInit(object):
    def __getattr__(self, attr):
        return getattr(self.inputs, attr)

    def __init__(
            self,
            ini_file=None,
            stack_user=None,
            stack_password=None,
            stack_tenant=None,
            logger=None):
        self.connections = None
        self.logger = logger or logging.getLogger(__name__)
        self.inputs = TestInputs(ini_file)
        self.stack_user = stack_user or self.stack_user
        self.stack_password = stack_password or self.stack_password
        self.stack_tenant = stack_tenant or self.stack_tenant
        self.project_fq_name = [self.stack_domain, self.stack_tenant]
        self.project_name = self.stack_tenant
        self.domain_name = self.stack_domain
        # Possible af values 'v4', 'v6' or 'dual'
        # address_family = read_config_option(self.config,
        #                      'Basic', 'AddressFamily', 'dual')
        self.address_family = 'v4'
    # end __init__

    def set_af(self, af):
        self.address_family = af

    def get_af(self):
        return self.address_family

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

    def verify_state(self):
        result = True
        for host in self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            if host in self.compute_ips:
                for service in self.compute_services:
                    result = result and self.verify_service_state(
                        host,
                        service,
                        username,
                        password)
            if host in self.bgp_ips:
                for service in self.control_services:
                    result = result and self.verify_service_state(
                        host,
                        service,
                        username,
                        password)
            if host in self.cfgm_ips:
                for service in self.cfgm_services:
                    result = result and self.verify_service_state(
                        host,
                        service,
                        username,
                        password)
            if host in self.collector_ips:
                for service in self.collector_services:
                    result = result and self.verify_service_state(
                        host,
                        service,
                        username,
                        password)
            if host in self.webui_ips:
                for service in self.webui_services:
                    result = result and self.verify_service_state(
                        host,
                        service,
                        username,
                        password)
            # Need to enhance verify_service_state to verify openstack services status as well
            # Commenting out openstack service verifcation untill then
            # if host == self.openstack_ip:
            #    for service in self.openstack_services:
            #        result = result and self.verify_service_state(
            #            host,
            #            service,
            #            username,
            #            password)
        return result
    # end verify_state

    def get_service_status(self, m, service):
        Service = namedtuple('Service', 'name state')
        for keys, values in m.items():
            values = values[0].rstrip().split()
            if service in str(values):
                cls = Service(values[0], values[1])
                self.logger.info("\n%s:%s" % (cls.name, cls.state))
                return cls
        return None

    def verify_service_state(self, host, service, username, password):
        m = None
        cls = None
        try:
            m = self.get_contrail_status(host)
            cls = self.get_service_status(m, service)
            if (cls.state in self.correct_states):
                return True
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))
            self.logger.exception(
                "Service %s not in correct state - its in %s state" %
                (cls.name, cls.state))
            return False
        self.logger.exception(
            "Service %s not in correct state - its in %s state" %
            (cls.name, cls.state))
        return False

    def verify_control_connection(self, connections):
        discovery = connections.ds_verification_obj
        return discovery.verify_bgp_connection()
    # end verify_control_connection

    def build_compute_to_control_xmpp_connection_dict(self, connections):
        agent_to_control_dct = {}
        for ip in self.compute_ips:
            actual_bgp_peer = []
            inspect_h = connections.agent_inspect[ip]
            agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
            for i in xrange(len(agent_xmpp_status)):
                actual_bgp_peer.append(agent_xmpp_status[i]['controller_ip'])
            agent_to_control_dct[ip] = actual_bgp_peer
        return agent_to_control_dct
    # end build_compute_to_control_xmpp_connection_dict

    def reboot(self, server_ip):
        i = socket.gethostbyaddr(server_ip)[0]
        print "rebooting %s" % i
        if server_ip in self.host_data.keys():
            username = self.host_data[server_ip]['username']
            password = self.host_data[server_ip]['password']
        with hide('everything'):
            with settings(
                    host_string='%s@%s' % (username, server_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                reboot(wait=300)
                run('date')
    # end reboot

    @retry(delay=10, tries=10)
    def confirm_service_active(self, service_name, host):
        cmd = 'contrail-status | grep %s | grep " active "' % (service_name)
        output = self.run_cmd_on_server(
            host, cmd, self.host_data[host]['username'],
            self.host_data[host]['password'])
        if output is not None:
            return True
        else:
            return False
    # end confirm_service_active

    def restart_service(
            self,
            service_name,
            host_ips=[],
            contrail_service=True):
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
            assert self.confirm_service_active(service_name, host), \
                "Service Restart failed for %s" % (service_name)
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
            if (state,
                active_str1,
                active_str2) != (state_val,
                                 active_str1_val,
                                 active_str2_val):
                result = False
                self.logger.warn(
                    'On host %s,Service %s states are %s, %s, %s .. NOT Expected !!' %
                    (host, service, state, active_str1, active_str2))
        return result
    # end _compare_service_state

    def get_contrail_status(self, server_ip, username='root',
                            password='contrail123'):
        cache = self.run_cmd_on_server(server_ip, 'contrail-status')
        m = dict([(n, tuple(l.split(';')))
                  for n, l in enumerate(cache.split('\n'))])
        return m

    def run_provision_control(
            self,
            router_asn,
            api_server_ip,
            api_server_port,
            oper):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        bgp_ips = set(self.bgp_ips)
        for host in bgp_ips:
            host_name = self.host_data[host]['name']
            issue_cmd = "python /usr/share/contrail-utils/provision_control.py \
			--host_name '%s' --host_ip '%s' --router_asn '%s' \
			--api_server_ip '%s' --api_server_port '%s' --oper '%s'" % (host_name,
                                                               host,
                                                               router_asn,
                                                               api_server_ip,
                                                               api_server_port,
                                                               oper)

            output = self.run_cmd_on_server(
                self.cfgm_ip, issue_cmd, username, password)
            if output.return_code != 0:
                self.logger.exception('Fail to execute provision_control.py')
                return output

    # end run_provision_control

    def run_provision_mx(
            self,
            api_server_ip,
            api_server_port,
            router_name,
            router_ip,
            router_asn,
            oper):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /usr/share/contrail-utils/provision_mx.py \
			--api_server_ip '%s' --api_server_port '%s' \
			--router_name '%s' --router_ip '%s'  \
			--router_asn '%s' --oper '%s'" % (
            api_server_ip, api_server_port,
            router_name, router_ip, router_asn, oper)
        output = self.run_cmd_on_server(
            self.cfgm_ip, issue_cmd, username, password)
        if output.return_code != 0:
            self.logger.exception('Fail to execute provision_mx.py')
            return output
    # end run_provision_mx

    def config_route_target(
            self,
            routing_instance_name,
            route_target_number,
            router_asn,
            api_server_ip,
            api_server_port):

        username = self.host_data[self.cfgm_ip]['username']
        password = self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /usr/share/contrail-utils/add_route_target.py \
                    --routing_instance_name '%s' --route_target_number '%s' \
                    --router_asn '%s' --api_server_ip '%s' --api_server_port '%s'" % (
                    routing_instance_name, route_target_number,
            router_asn, api_server_ip, api_server_port)

        output = self.run_cmd_on_server(
            self.cfgm_ip, issue_cmd, username, password)
        if output.return_code != 0:
            self.logger.exception('Fail to execute add_route_target.py')
            return output
    # end config_route_target

    def configure_mx(
            self,
            tunnel_name,
            bgp_group,
            cn_ip,
            mx_ip,
            mx_rt,
            mx_as,
            mx_user,
            mx_password,
            ri_name,
            intf,
            vrf_target,
            ri_gateway):

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

    def copy_file_to_server(self, ip, src, dstdir, dst, force=False):
        host = {}
        host['ip'] = ip
        host['username'] = self.host_data[ip]['username']
        host['password'] = self.host_data[ip]['password']
        copy_file_to_server(host, src, dstdir, dst, force)
