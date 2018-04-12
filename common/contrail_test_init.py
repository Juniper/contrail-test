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
from fabric.api import env, run, local, sudo
from fabric.operations import get, put, reboot
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from fabric.contrib.files import exists

from tcutils.util import *
from tcutils.util import custom_dict, read_config_option, get_build_sku, retry
from tcutils.custom_filehandler import *
from tcutils.config.vnc_introspect_utils import VNCApiInspect
from tcutils.collector.opserver_introspect_utils import VerificationOpsSrv
from tcutils.contrail_status_check import ContrailStatusChecker
from keystone_tests import KeystoneCommands
from tempfile import NamedTemporaryFile
import re
from common import log_orig as contrail_logging
from common.contrail_services import CONTRAIL_SERVICES_CONTAINER_MAP

import subprocess
from collections import namedtuple
import random
from cfgm_common import utils
import argparse
import yaml

ORCH_DEFAULT_DOMAIN = {
    'openstack' : 'Default',
    'kubernetes': 'default-domain',
    'vcenter': 'default-domain',
}
DEFAULT_CERT = '/etc/contrail/ssl/certs/server.pem'
DEFAULT_PRIV_KEY = '/etc/contrail/ssl/private/server-privkey.pem'
DEFAULT_CA = '/etc/contrail/ssl/certs/ca-cert.pem'

DEFAULT_CI_IMAGE = os.getenv('DEFAULT_CI_IMAGE', 'cirros')
DEFAULT_CI_SVC_IMAGE = os.getenv('DEFAULT_CI_SVC_IMAGE', 'cirros_in_net')
CI_IMAGES = [DEFAULT_CI_IMAGE, DEFAULT_CI_SVC_IMAGE]

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
       check the keystone server to populate
       the same with the certain default value assumptions
    '''
    __metaclass__ = Singleton
    def __init__(self, input_file, logger=None):
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = custom_dict(self.get_os_version, 'os_type')
        self.config = None
        self.input_file = input_file
        self.logger = logger or contrail_logging.getLogger(__name__)

        self.ha_tmp_list = []
        self.tor_agent_data = {}
        self.sriov_data = {}
        self.dpdk_data = {}
        self.mysql_token = None
        self.pcap_on_vm = False

        if input_file.endswith('.ini'):
            self.parse_ini_file()
        elif input_file.endswith(('.yml', '.yaml')):
            self.parse_yml_file()
        if self.fip_pool:
            update_reserve_cidr(self.fip_pool)
        if not self.ui_browser and (self.verify_webui or self.verify_horizon):
            raise ValueError(
                "Verification via GUI needs 'browser' details. Please set the same.")
        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']

        insecure = istrue(os.getenv('OS_INSECURE', False))
        if insecure:
            self.api_insecure = self.insecure = insecure
        keycertbundle = None
        if not self.insecure and self.auth_protocol == 'https' and \
           self.keystonecertfile and self.keystonekeyfile and \
           self.keystonecafile:
            keystone_bundle = '/tmp/' + get_random_string() + '.pem'
            keycertbundle = utils.getCertKeyCaBundle(keystone_bundle,
                            [self.keystonecertfile, self.keystonekeyfile,
                             self.keystonecafile])
        apicertbundle = None
        if not self.api_insecure and self.api_protocol == 'https' and \
           self.apicertfile and self.apikeyfile and self.apicafile:
            api_bundle = '/tmp/' + get_random_string() + '.pem'
            apicertbundle = utils.getCertKeyCaBundle(api_bundle,
                            [self.apicertfile, self.apikeyfile,
                             self.apicafile])
        introspect_certbundle = None
        if not self.introspect_insecure and self.introspect_protocol == 'https' and \
           self.introspect_cafile:
            introspect_certbundle = self.introspect_cafile

        self.certbundle = None
        if keycertbundle or apicertbundle or introspect_certbundle:
            bundle = '/tmp/' + get_random_string() + '.pem'
            certs = [cert for cert in [keycertbundle, apicertbundle, introspect_certbundle] if cert]
            self.certbundle = utils.getCertKeyCaBundle(bundle, certs)

        # List of service correspond to each module
        self.compute_services = [
            'contrail-vrouter-agent',
            'contrail-vrouter-nodemgr']
        self.control_services = ['contrail-control',
                                 'contrail-control-nodemgr', 'contrail-dns',
                                 'contrail-named']
        self.cfgm_services = [
            'contrail-api',
            'contrail-schema',
            'contrail-svc-monitor',
            'contrail-config-nodemgr',
            'contrail-device-manager']
        self.webui_services = ['contrail-webui', 'contrail-webui-middleware']
        self.openstack_services = [
            'openstack-cinder-api', 'openstack-cinder-scheduler',
            'openstack-cinder-scheduler', 'openstack-glance-api',
            'openstack-glance-registry', 'openstack-keystone',
            'openstack-nova-api', 'openstack-nova-scheduler', 'openstack-nova-conductor',
            'heat-api', 'heat-api-cfn', 'heat-engine', 'rabbitmq-server']
        self.collector_services = [
            'contrail-collector', 'contrail-analytics-api', 'contrail-alarm-gen',
            'contrail-query-engine', 'contrail-analytics-nodemgr',
            'contrail-snmp-collector', 'contrail-topology']
        self.database_services = [
            'contrail-database', 'contrail-database-nodemgr', 'kafka']
        self.correct_states = ['active', 'backup']

    def parse_ini_file(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.input_file)
        self.orchestrator = read_config_option(self.config,
                                               'Basic', 'orchestrator', 'openstack')
        self.slave_orchestrator = read_config_option(self.config,
                                                     'Basic', 'slave_orchestrator', None)
        self.deployer = read_config_option(self.config,
                                               'Basic', 'deployer', 'openstack')
        self.prov_file = read_config_option(self.config,
                                            'Basic', 'provFile', None)
        self.key = read_config_option(self.config,
                                      'Basic', 'key', 'key1')
        self.keystone_version = read_config_option(self.config,
                                                   'Basic',
                                                   'keystone_version',
                                                   'v2')
        self.use_project_scoped_token = read_config_option(self.config,
                                                   'Basic',
                                                   'use_project_scoped_token',
                                                   False)
        self.domain_isolation = read_config_option(self.config,
            'Basic',
            'domain_isolation',
            False) if self.keystone_version == 'v3' else False
        self.cloud_admin_domain = read_config_option(self.config,
            'Basic',
            'cloud_admin_domain',
            'Default')
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
            os.getenv('OS_USERNAME', 'admin'))
        self.admin_password = read_config_option(self.config,
            'Basic',
            'adminPassword',
            os.getenv('OS_PASSWORD', 'contrail123'))
        self.admin_tenant = read_config_option(self.config,
            'Basic',
            'adminTenant',
            os.getenv('OS_TENANT_NAME', 'admin'))

        self.admin_domain = read_config_option(self.config,
            'Basic',
            'adminDomain',
            os.getenv('OS_DOMAIN_NAME',
                ORCH_DEFAULT_DOMAIN.get(self.orchestrator)))

        if self.orchestrator == 'kubernetes':
            self.admin_tenant = 'default'
            self.tenant_isolation = False
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
            os.getenv('OS_DOMAIN_NAME', self.admin_domain))
        self.region_name = read_config_option(
            self.config,
            'Basic',
            'stackRegion',
            os.getenv('OS_REGION_NAME', 'RegionOne'))
        self.availability_zone = read_config_option(
            self.config,
            'Basic',
            'availability_zone',
            None)
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
        self.api_protocol = read_config_option(self.config,
                                          'cfgm', 'api_protocol', 'http')
        self.api_insecure = read_config_option(self.config,
                                          'cfgm', 'api_insecure_flag', True)
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
        self.ci_flavor = read_config_option(self.config,
                                            'Basic', 'ci_flavor', None)
        self.config_amqp_ips = read_config_option(self.config,
                                            'services', 'config_amqp_ips', None)
        if self.config_amqp_ips:
            self.config_amqp_ips = self.config_amqp_ips.split(',')
        self.config_amqp_port = read_config_option(self.config,
                                            'services', 'config_amqp_port', '5673')
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
        self.kube_config_file = read_config_option(self.config,
                                                   'kubernetes', 'config_file',
                                                   '/etc/kubernetes/admin.conf')
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

        fabric_gw_info_tuples_string = read_config_option(
            self.config,
            'router',
            'fabric_gw_info',
            '[]')
        self.fabric_gw_info = ast.literal_eval(fabric_gw_info_tuples_string)

        self.fip_pool_name = read_config_option(
            self.config,
            'router',
            'fip_pool_name',
            'public-pool')
        self.fip_pool = read_config_option(self.config,
                                           'router', 'fip_pool', None)
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
        self.public_host = read_config_option(self.config, 'Basic',
                                              'public_host', '10.204.216.50')

        if self.keystone_version == 'v3':
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                        '%s://%s:%s/v3'%(self.auth_protocol,
                                           self.auth_ip,
                                           self.auth_port)
            self.authn_url = '/v3/auth/tokens'
        else:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                        '%s://%s:%s/v2.0'%(self.auth_protocol,
                                           self.auth_ip,
                                           self.auth_port)
            self.authn_url = '/v2.0/tokens'
        self._set_auth_vars()
        self.apicertfile = read_config_option(self.config,
                                             'cfgm', 'api_certfile', DEFAULT_CERT)
        self.apikeyfile = read_config_option(self.config,
                                            'cfgm', 'api_keyfile', DEFAULT_PRIV_KEY)
        self.apicafile = read_config_option(self.config,
                                           'cfgm', 'api_cafile', DEFAULT_CA)
        self.api_insecure = bool(read_config_option(self.config,
                                 'cfgm', 'api_insecure_flag', False))

        self.introspect_certfile = read_config_option(self.config,
                                             'introspect', 'introspect_certfile', DEFAULT_CERT)
        self.introspect_keyfile = read_config_option(self.config,
                                            'introspect', 'introspect_keyfile', DEFAULT_PRIV_KEY)
        self.introspect_cafile = read_config_option(self.config,
                                           'introspect', 'introspect_cafile', DEFAULT_CA)
        self.introspect_insecure = bool(read_config_option(self.config,
                                 'introspect', 'introspect_insecure_flag', True))
        self.introspect_protocol = read_config_option(self.config,
                                          'introspect', 'introspect_protocol', 'http')

        self.keystonecertfile = read_config_option(self.config,
                                'Basic', 'keystone_certfile',
                                os.getenv('OS_CERT', None))
        self.keystonekeyfile = read_config_option(self.config,
                               'Basic', 'keystone_keyfile',
                               os.getenv('OS_KEY', None))
        self.keystonecafile = read_config_option(self.config,
                              'Basic', 'keystone_cafile',
                              os.getenv('OS_CACERT', None))
        self.insecure = bool(read_config_option(self.config,
                             'Basic', 'keystone_insecure_flag', False))
        self.prov_data = self.read_prov_file()
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
        #for multiple vcenter
        try:
            if 'vcenter_servers' in self.prov_data.keys():
                for server in self.prov_data['vcenter_servers']:
                    for dc in server['datacenters']:
                        for dv in server['datacenters'][dc]['dv_switches']:
                            self.dv_switch = dv
            elif 'vcenter' in self.prov_data.keys():
                self.dv_switch = self.prov_data['vcenter'][0]['dv_switch']['dv_switch_name']
        except Exception as e:
            pass
        self.gc_host_mgmt = read_config_option(self.config,
                                             'global-controller', 'gc_host_mgmt', 'None')
        self.gc_host_control_data = read_config_option(self.config,
                                             'global-controller', 'gc_host_control_data', 'None')
        self.gc_user_name = read_config_option(self.config,
                                             'global-controller', 'gc_user_name', 'None')
        self.gc_user_pwd = read_config_option(self.config,
                                             'global-controller', 'gc_user_pwd', 'None')
        self.keystone_password = read_config_option(self.config,
                                             'global-controller', 'keystone_password', 'None')
	self.ixia_linux_host_ip = read_config_option(self.config,
                                             'traffic_data', 'ixia_linux_host_ip', None)
	self.ixia_host_ip = read_config_option(self.config,
                                             'traffic_data', 'ixia_host_ip', None)
	self.spirent_linux_host_ip = read_config_option(self.config,
                                             'traffic_data', 'spirent_linux_host_ip', None)
	self.ixia_linux_username = read_config_option(self.config,
	                                     'traffic_data', 'ixia_linux_username', None)
	self.ixia_linux_password = read_config_option(self.config,
                                             'traffic_data', 'ixia_linux_password', None)
	self.spirent_linux_username = read_config_option(self.config,
                                             'traffic_data', 'spirent_linux_username', None)
	self.spirent_linux_password = read_config_option(self.config,
                                             'traffic_data', 'spirent_linux_password', None)
        #Report Parsing
        self.log_scenario = read_config_option(self.config,
                                               'Basic', 'logScenario', 'Sanity')
        self.image_web_server = read_config_option(self.config,
            'Basic',
            'image_web_server',
            os.getenv('IMAGE_WEB_SERVER') or '10.204.216.50')
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

    def _set_auth_vars(self):
        '''
        Set auth_protocol, auth_ip, auth_port from self.auth_url
        '''
        match = re.match(r'(.*?)://(.*?):([\d]+).*$', self.auth_url, re.M|re.I)
        if match:
            self.auth_protocol = match.group(1)
            self.auth_ip = match.group(2)
            self.auth_port = match.group(3)
    # end _set_auth_vars

    def get_ctrl_data_ip(self, host):
        net_list = self.contrail_configs.get('CONTROL_DATA_NET_LIST')
        if not net_list:
            return
        if self.host_data[host].get('control_data_ip'):
            return self.host_data[host]['control_data_ip']
        ips = self.get_ips_of_host(host)
        for net in net_list.split(","):
            for ip in ips:
                if IPAddress(ip) in IPNetwork(net):
                    self.host_data[host]['control_data_ip'] = ip
                    return ip
    #end get_ctrl_data_listen_ip

    def get_ips_of_host(self, host, nic=None):
        if self.host_data[host].get('ips') and not nic:
            return self.host_data[host]['ips']
        username = self.host_data[host]['username']
        password = self.host_data[host]['password']
        ips = get_ips_of_host(host, nic=nic,
                          username=username,
                          password=password,
                          as_sudo=True,
                          logger=self.logger)
        if not nic:
            self.host_data[host]['ips'] = ips
        return ips

    def _get_ip_for_service(self, host, service):
        host_dict = self.host_data[host]
        if service.lower() == 'vrouter':
            return self.get_ips_of_host(host, 'vhost0')[0]
        elif service.lower() == 'openstack':
            nic = host_dict['roles']['openstack'].get('network_interface') \
                  if host_dict['roles']['openstack'] else \
                  self.orchestrator_configs.get('network_interface')
            if not nic:
                return host
            ips = self.get_ips_of_host(host, nic)
            if not ips and 'vrouter' in host_dict['roles']:
                ips = self.get_ips_of_host(host, 'vhost0')
            if ips:
                return ips[0]
            return host
        else:
            service_nodes = service.upper()+'_NODES' if service else ''
            if not self.contrail_configs.get(service_nodes):
                service_nodes = 'CONTROLLER_NODES'
            if self.contrail_configs.get(service_nodes):
                cfg_ips = set(self.contrail_configs[service_nodes].split(','))
		ips = set(self.get_ips_of_host(host))
                if ips.intersection(cfg_ips):
                    return list(ips.intersection(cfg_ips))[0]
        return host

    def get_service_ip(self, host, service='CONTROLLER'):
        ip = self.get_ctrl_data_ip(host)
        if not ip:
           ip = self._get_ip_for_service(host, service)
        return ip

    def parse_topo(self):
        self.host_names = []
        self.cfgm_ip = ''
        self.cfgm_ips = []
        self.cfgm_control_ips = []
        self.cfgm_names = []
        self.openstack_ip = ''
        self.openstack_ips = []
        self.openstack_control_ips = []
        self.openstack_names = []
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
        self.host_ips = []
        self.webui_ips = []
        self.webui_control_ips = []
        self.kube_manager_ips = []
        self.kube_manager_control_ips = []
        self.k8s_master_ip = ""
        self.k8s_slave_ips = []
        self.host_data = {}
        self.tor = {}
        self.tor_hosts_data = {}
        self.physical_routers_data = {}
        self.vcenter_compute_ips= []
        self.qos_queue = []
        self.qos_queue_pg_properties = []
        self.ns_agilio_vrouter_data = {}
        self.esxi_vm_ips = {}
        self.vgw_data = {}
        self.hypervisors = {}
        provider_configs = (self.config.get('provider_config') or {}).get('bms') or {}
        username = provider_configs.get('ssh_user') or 'root'
        password = provider_configs.get('ssh_pwd') or 'c0ntrail123'
        for host, values  in (self.config.get('instances') or {}).iteritems():
            roles = values.get('roles') or {}
            host_data = dict()
            host_data['host_ip'] = values['ip']
            host_data['roles'] = roles
            host_data['username'] = username
            host_data['password'] = password
            self.host_data[host_data['host_ip']] = host_data
            hostname = self.run_cmd_on_server(host_data['host_ip'], 'hostname')
            host_fqname = self.run_cmd_on_server(host_data['host_ip'], 'hostname -f')
            self.host_names.append(hostname)
            self.host_ips.append(host_data['host_ip'])
            host_data['name'] = hostname
            host_data['fqname'] = host_fqname
            self.host_data[host_fqname] = self.host_data[hostname] = host_data
            self._check_containers(host_data)
            host_data_ip = host_control_ip = host_data['host_ip']
            control_data_ip = self.get_ctrl_data_ip(host_data['host_ip'])
            if control_data_ip:
                host_data_ip = host_control_ip = control_data_ip
            qos_queue_per_host, qos_queue_pg_properties_per_host = \
                                    self._process_qos_data(host_data['host_ip'])
            if qos_queue_per_host:
                self.qos_queue.append(qos_queue_per_host)
            if qos_queue_pg_properties_per_host:
                self.qos_queue_pg_properties.append(qos_queue_pg_properties_per_host)
            if 'openstack' in roles:
                self.openstack_ip = host_data['host_ip']
                self.openstack_ips.append(host_data['host_ip'])
                service_ip = self.get_service_ip(host_data['host_ip'], 'openstack')
                self.openstack_control_ips.append(service_ip)
                self.openstack_control_ip = service_ip
                self.openstack_names.append(hostname)
            if 'config' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'config')
                self.cfgm_ip = service_ip
                self.cfgm_ips.append(service_ip)
                self.cfgm_control_ips.append(service_ip)
                self.cfgm_control_ip = service_ip
                self.cfgm_names.append(hostname)
                self.hostname = hostname
            if 'vrouter' in roles:
                data_ip = self.get_service_ip(host_data['host_ip'], 'vrouter')
                self.compute_ips.append(host_data['host_ip'])
                self.compute_names.append(hostname)
                self.compute_info[hostname] = host_data['host_ip']
                self.compute_control_ips.append(data_ip)
                host_data_ip = host_control_ip = data_ip
            if 'control' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'control')
                self.bgp_ips.append(host_data['host_ip'])
                self.bgp_control_ips.append(service_ip)
                self.bgp_names.append(hostname)
            if 'webui' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'webui')
                self.webui_ip = host_data['host_ip']
                self.webui_ips.append(host_data['host_ip'])
                self.webui_control_ips.append(service_ip)
            if 'analytics' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'analytics')
                self.collector_ip = host_data['host_ip']
                self.collector_ips.append(host_data['host_ip'])
                self.collector_control_ips.append(service_ip)
                self.collector_names.append(hostname)
            if 'analytics_database' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'analytics_database')
                self.database_ip = host_data['host_ip']
                self.database_ips.append(host_data['host_ip'])
                self.database_names.append(hostname)
                self.database_control_ips.append(service_ip)
            if 'kubemanager' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'kubemanager')
                self.kube_manager_ips.append(host_data['host_ip'])
                self.kube_manager_control_ips.append(service_ip)
            if 'k8s_master' in roles:
                self.k8s_master_ip = host_data['host_ip'] #K8s Currently only supports 1 master
            if 'k8s_node' in roles:
                self.k8s_slave_ips.append(host_data['host_ip'])
            host_data['data-ip'] = host_data['host_data_ip'] = host_data_ip
            host_data['control-ip'] = host_data['host_control_ip'] = host_control_ip
            self.host_data[host_data_ip] = self.host_data[host_control_ip] = host_data
        # end for

    def get_roles(self, host):
        roles = list()
        host_ip = self.get_host_ip(host)
        host_data_ip = self.get_host_data_ip(host)
        if host_ip in self.cfgm_ips or host_data_ip in self.cfgm_ips:
            roles.append('config')
            roles.append('config-database')
        if host_ip in self.compute_ips or host_data_ip in self.compute_control_ips:
            roles.append('vrouter')
        if host_ip in self.bgp_ips or host_data_ip in self.bgp_control_ips:
            roles.append('control')
        if host_ip in self.collector_ips or host_data_ip in self.collector_control_ips:
            roles.append('analytics')
        if host_ip in self.database_ips or host_data_ip in self.database_control_ips:
            roles.append('analytics-database')
        if host_ip in self.webui_ips or host_data_ip in self.webui_control_ips:
            roles.append('webui')
        if host_ip in self.kube_manager_ips or host_data_ip in self.kube_manager_control_ips:
            roles.append('kubernetes')
        return roles

    def _gen_auth_url(self):
        if self.keystone_version == 'v3':
            auth_url = 'http://%s:5000/v3'%(self.external_vip or self.openstack_ip)
        else:
            auth_url = 'http://%s:5000/v2.0'%(self.external_vip or self.openstack_ip)
        return auth_url

    def parse_yml_file(self):
        self.key = 'key1'
        self.use_project_scoped_token = True
        self.insecure = self.api_insecure = self.introspect_insecure = True
        self.keystonecertfile = self.keystonekeyfile = self.keystonecafile = None
        self.apicertfile = self.apikeyfile = self.apicafile = None
        self.introspect_certfile = self.introspect_keyfile = self.introspect_cafile = None
        self.multi_tenancy = True
        self.enable_ceilometer = True
        self.vcenter_gateway = []
        self.orchs = []
        self.vcenter_gw_setup = False
        self.vcenter_present_in_this_setup = False
        self.vcenter_dc = self.vcenter_server = self.vcenter_port = None
        self.vcenter_username = self.vcenter_password = None
        self.vcenter_compute = None

        with open(self.input_file, 'r') as fd:
            self.config = yaml.load(fd)
        deployment_configs = self.config.get('deployment', {})
        self.deployer = deployment_configs.get('deployer', 'contrail-ansible-deployer')
        self.contrail_configs = contrail_configs = \
            self.config.get('contrail_configuration') or {}
        self.orchestrator_configs = orchestrator_configs = \
            self.config.get('orchestrator_configuration') or {}
        test_configs = self.config.get('test_configuration') or {}
        self.orchestrator = deployment_configs.get('orchestrator') or 'openstack'
        self.slave_orchestrator = deployment_configs.get('slave_orchestrator')
        self.parse_topo()

        # contrail related configs
        self.api_protocol = 'https' if contrail_configs.get('CONFIG_API_USE_SSL') else 'http'
        self.api_server_port = contrail_configs.get('CONFIG_API_PORT') or '8082'
        self.analytics_api_port = contrail_configs.get('ANALYTICS_API_PORT') or '8081'
        self.bgp_port = contrail_configs.get('CONTROL_INTROSPECT_PORT') or '8083'
        self.dns_port = contrail_configs.get('DNS_INTROSPECT_PORT') or '8092'
        self.agent_port = '8085'
        self.api_server_ip = contrail_configs.get('CONFIG_API_VIP')
        self.analytics_api_ip = contrail_configs.get('ANALYTICS_API_VIP')
        self.config_amqp_ips = contrail_configs.get('RABBITMQ_NODES')
        self.config_amqp_port = contrail_configs.get('RABBITMQ_NODE_PORT', 5673)
        self.contrail_internal_vip = self.contrail_external_vip = self.api_server_ip
        self.xmpp_auth_enable = contrail_configs.get('XMPP_SSL_ENABLE')
        self.xmpp_dns_auth_enable = contrail_configs.get('XMPP_SSL_ENABLE')

        # openstack related configs
        keystone_configs = orchestrator_configs.get('keystone') or {}
        self.keystone_version = keystone_configs.get('version') or 'v3'
        self.admin_username = keystone_configs.get('username') or \
                                  os.getenv('OS_USERNAME', 'admin')
        self.admin_password = keystone_configs.get('password') or \
                                  os.getenv('OS_PASSWORD', 'c0ntrail123')
        self.admin_tenant = keystone_configs.get('tenant') or \
                                os.getenv('OS_TENANT_NAME', 'admin')
        self.admin_domain = keystone_configs.get('domain') or \
                                os.getenv('OS_DOMAIN_NAME',
                                ORCH_DEFAULT_DOMAIN.get(self.orchestrator))
        self.region_name = keystone_configs.get('region') or \
                               os.getenv('OS_REGION_NAME', 'RegionOne')
        if self.keystone_version == 'v3':
            self.authn_url = '/v3/auth/tokens'
        else:
            self.authn_url = '/v2.0/tokens'
        if self.orchestrator == 'kubernetes':
            self.admin_tenant = 'default'
        self.internal_vip = orchestrator_configs.get('internal_vip')
        self.external_vip = orchestrator_configs.get('external_vip') or self.internal_vip
        # test specific configs
        self.auth_url = test_configs.get('auth_url') or os.getenv('OS_AUTH_URL',
                                                     self._gen_auth_url())
        self.stack_user = test_configs.get('stack_user') or self.admin_username
        self.stack_password = test_configs.get('stack_user') or self.admin_password
        self.stack_tenant = test_configs.get('stack_tenant') or self.admin_tenant
        self.stack_domain = test_configs.get('stack_domain') or self.admin_domain
        self.availability_zone = test_configs.get('availability_zone')
        self.use_project_scoped_token = test_configs.get('use_project_scoped_token') or False
        self.domain_isolation = test_configs.get('domain_isolation') or False
        self.tenant_isolation = False if test_configs.get('tenant_isolation') is False else True
        self.user_isolation = False if test_configs.get('user_isolation') is False else True
        self.ci_flavor = test_configs.get('ci_image_flavor')
        self.key_filename = test_configs.get('nova_keypair_private_key_filename')
        self.pubkey_filename = test_configs.get('nova_keypair_public_key_filename')

        self.fixture_cleanup = test_configs.get('fixture_cleanup', 'yes')
        self.http_proxy = test_configs.get('http_proxy')
        self.ui_config = test_configs.get('ui_config')
        self.ui_browser = test_configs.get('ui_browser')
        self.verify_webui = test_configs.get('verify_webui', False)
        self.verify_horizon = test_configs.get('verify_horizon', False)
        self.use_devicemanager_for_md5 = test_configs.get('use_devicemanager_for_md5', False)
        self.verify_on_setup = False if test_configs.get('verify_on_setup') is False else True
        self.stop_on_fail = test_configs.get('stop_on_fail') or False
        self.public_host = test_configs.get('public_host') or '10.204.216.50'
        self.public_vn = test_configs.get('public_virtual_network') or 'public-network'
        self.fip_pool = test_configs.get('public_subnet')
        self.fip_pool_name = test_configs.get('fip_pool_name')
        self.public_tenant = test_configs.get('public_tenant_name')
        self.mx_rt = str(test_configs.get('public_rt') or '')
        self.router_asn = str(test_configs.get('router_asn') or '64512')
        self.kube_config_file = test_configs.get('kube_config_file') or '/etc/kubernetes/admin.conf'
        self.ext_routers = []
        for rtr_name, address in test_configs.get('ext_routers', {}).iteritems():
            self.ext_routers.append((rtr_name, address))
        self.fabric_gw_info = []
        for gw_name, address in test_configs.get('fabric_gw', {}).iteritems():
            self.fabric_gw_info.append((gw_name, address))
        if 'traffic_generator' in test_configs:
            traffic_gen = test_configs['traffic_generator']
	    self.ixia_linux_host_ip = traffic_gen.get('ixia_linux_host_ip')
	    self.ixia_host_ip = traffic_gen.get('ixia_host_ip')
	    self.spirent_linux_host_ip = traffic_gen.get('spirent_linux_host_ip')
	    self.ixia_linux_username = traffic_gen.get('ixia_linux_username')
	    self.ixia_linux_password = traffic_gen.get('ixia_linux_password')
	    self.spirent_linux_username = traffic_gen.get('spirent_linux_username')
	    self.spirent_linux_password = traffic_gen.get('spirent_linux_password')
        if 'device_manager' in test_configs:
            self.dm_mx = test_configs['device_manager']
        if 'ns_agilio_vrouter' in test_configs:
            self.pcap_on_vm = True
        if not self.config_amqp_ips:
            self.config_amqp_ips = self.openstack_control_ips if \
                                   self.openstack_control_ips else\
                                   self.cfgm_control_ips  #vcenter only mode
        self.many_computes = (len(self.compute_ips) > 10) or False
        self._set_auth_vars()
        if self.orchestrator == 'kubernetes':
            self.tenant_isolation = False
#        self.endpoint_type = test_configs.get('endpoint_type')
#        self.cloud_admin_domain = test_configs.get('cloud_admin_domain', 'Default')
        self.image_web_server = test_configs.get('image_web_server') or \
                                os.getenv('IMAGE_WEB_SERVER') or '10.204.216.50'
        # Report Gen related parsers
        report_configs = test_configs.get('report') or {}
        self.log_scenario = report_configs.get('log_scenario') or 'Sanity'
        # Web Server related details
        webserver_configs = test_configs.get('web_server') or {}
        self.web_server = webserver_configs.get('server')
        self.web_server_user = webserver_configs.get('username')
        self.web_server_password = webserver_configs.get('password')
        self.web_server_report_path = webserver_configs.get('report_path')
        self.web_server_log_path = webserver_configs.get('log_path')
        self.web_root = webserver_configs.get('web_root')
        # Mail Setup
        mailserver_configs = test_configs.get('mail_server') or {}
        self.smtpServer = mailserver_configs.get('server')
        self.smtpPort = mailserver_configs.get('port') or '25'
        self.mailTo = mailserver_configs.get('to')
        self.mailSender = mailserver_configs.get('sender') or 'contrailbuild@juniper.net'

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
        a_container = None
        if host_ip in self.os_type:
            return self.os_type[host_ip]
        username = self.host_data[host_ip]['username']
        password = self.host_data[host_ip]['password']
        containers = self.host_data[host_ip]['containers'].keys()
        if containers :
            a_container = containers[0]
        with hide('output','running','warnings'):
            output = self.run_cmd_on_server(host_ip,
                        'uname -a', username, password, container=a_container)
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

    def get_active_containers(self, host):
        cmd = "docker ps -f status=running --format {{.Names}} 2>/dev/null"
        output = self.run_cmd_on_server(host, cmd, as_sudo=True)
        containers = [x.strip('\r') for x in output.split('\n')]
        return containers

    def _check_containers(self, host_dict):
        '''
        Find out which components have containers and set
        corresponding attributes in host_dict to True if present
        '''
        host_dict['containers'] = {}
        if  host_dict.get('type', None) == 'esxi':
            return
        cmd = 'docker ps 2>/dev/null | grep -v "/pause" | awk \'{print $NF}\''
        output = self.run_cmd_on_server(host_dict['host_ip'], cmd, as_sudo=True)
        # If not a docker cluster, return
        if not output:
            return
        containers = [x.strip('\r') for x in output.split('\n')]

        for service, names in CONTRAIL_SERVICES_CONTAINER_MAP.iteritems():
            for name in names:
                container = next((container for container in containers if name in container), None)
                if container:
                    host_dict['containers'][service] = container
                    containers.remove(container)
                    break

        # Added for backward compatibility can be removed when we dont have fat containers
        for container in containers:
            if '_network_' not in container:
                host_dict['containers'][container] = container
        if 'nova' in host_dict['containers']:
            host_dict['containers']['openstack'] = host_dict['containers']['nova']
        if 'schema' not in host_dict['containers'] and 'controller' in host_dict['containers']:
            host_dict['containers']['api-server'] = host_dict['containers']['controller']
            host_dict['containers']['svc-monitor'] = host_dict['containers']['controller']
            host_dict['containers']['schema'] = host_dict['containers']['controller']
            host_dict['containers']['control'] = host_dict['containers']['controller']
            host_dict['containers']['dns'] = host_dict['containers']['controller']
            host_dict['containers']['named'] = host_dict['containers']['controller']
        if 'alarm-gen' not in host_dict['containers'] and 'analytics' in host_dict['containers']:
            host_dict['containers']['analytics-api'] = host_dict['containers']['analytics']
            host_dict['containers']['alarm-gen'] = host_dict['containers']['analytics']
            host_dict['containers']['collector'] = host_dict['containers']['analytics']
            host_dict['containers']['query-engine'] = host_dict['containers']['analytics']
        if 'analytics-cassandra' not in host_dict['containers'] and 'analyticsdb' in host_dict['containers']:
            host_dict['containers']['analytics-cassandra'] = host_dict['containers']['analyticsdb']
    # end _check_containers

    def read_prov_file(self):
        prov_file = open(self.prov_file, 'r')
        prov_data = prov_file.read()
        json_data = json.loads(prov_data)
        self.host_names = []
        self.cfgm_ip = ''
        self.cfgm_ips = []
        self.cfgm_control_ips = []
        self.cfgm_names = []
        self.openstack_ip = ''
        self.openstack_ips = []
        self.openstack_control_ips = []
        self.openstack_names = []
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
        self.host_ips = []
        self.webui_ips = []
        self.webui_control_ips = []
        self.kube_manager_ips = []
        self.kube_manager_control_ips = []
        self.k8s_master_ip = ""
        self.k8s_slave_ips = []
        self.host_data = {}
        self.tor = {}
        self.tor_hosts_data = {}
        self.physical_routers_data = {}
        self.qos_queue = []
        self.vcenter_compute_ips= []
        ''' self.qos_queue used for populating HW to Logical map
            format self.qos_queue = [['comput_ip' , [{'hw_q_id':[logical_ids]}, {'hw_q_id':[logical_ids]}]]]
            eg, self.qos_queue= [['10.204.217.128', [{u'3': [u'1', u'6-10', u'12-15']}, {u'11': [u'40-46']}]],
                            , ['10.204.217.130', [{u'4': [u'1', u'6-10', u'12-15']}, {u'12': [u'40-46']}]]]'''
        self.qos_queue_pg_properties = []
        ''' self.qos_queue_pg_properties used for populating per Priority Group Properties
            format self.qos_queue_pg_properties = [['comput_ip' , [{1st PG properties}, {2nd PG properties}]]]
            eg, self.qos_queue_pg_properties = [['10.204.217.128', [{u'scheduling': u'strict', u'bandwidth': u'0', u'priority_id': u'0'},
                                                                {u'scheduling': u'rr', u'bandwidth': u'10', u'priority_id': u'2'}]],
                            ,                ['10.204.217.130', [{u'scheduling': u'strict', u'bandwidth': u'0', u'priority_id': u'1'},
                                                                {u'scheduling': u'rr', u'bandwidth': u'25', u'priority_id': u'3'}]]]'''
        self.ns_agilio_vrouter_data = {}

        self.esxi_vm_ips = {}
        self.vgw_data = {}
        self.hypervisors = {}
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
            if host.get('fqname', None):
                self.host_data[host['fqname']] = self.host_data[host['name']]
            self._check_containers(host)
            qos_queue_per_host, qos_queue_pg_properties_per_host = \
                                    self._process_qos_data(host_ip)
            if qos_queue_per_host:
                self.qos_queue.append(qos_queue_per_host)
            if qos_queue_pg_properties_per_host:
                self.qos_queue_pg_properties.append(qos_queue_pg_properties_per_host)
            roles = host["roles"]
            for role in roles:
                if role['type'] == 'openstack':
                    self.openstack_ip = host_ip
                    self.openstack_ips.append(host_ip)
                    self.openstack_control_ips.append(host_control_ip)
                    self.openstack_control_ip = host_control_ip
                    self.openstack_names.append(host['name'])
                    if role['container']:
                        host['containers']['openstack'] = role['container']
                if role['type'] == 'cfgm':
                    self.cfgm_ip = host_ip
                    self.cfgm_ips.append(host_ip)
                    self.cfgm_control_ips.append(host_control_ip)
                    self.cfgm_control_ip = host_control_ip
                    self.cfgm_names.append(host['name'])
                    self.masterhost = self.cfgm_ip
                    self.hostname = host['name']
                    if role['container']:
                        host['containers']['controller'] = role['container']
                if role['type'] == 'compute':
                    self.compute_ips.append(host_ip)
                    self.compute_names.append(host['name'])
                    self.compute_info[host['name']] = host_ip
                    self.compute_control_ips.append(host_control_ip)
                    if role['container']:
                        host['containers']['agent'] = role['container']
                if role['type'] == 'bgp':
                    self.bgp_ips.append(host_ip)
                    self.bgp_control_ips.append(host_control_ip)
                    self.bgp_names.append(host['name'])
                if role['type'] == 'webui':
                    self.webui_ip = host_ip
                    self.webui_ips.append(host_ip)
                    self.webui_control_ips.append(host_control_ip)
                if role['type'] == 'collector':
                    self.collector_ip = host_ip
                    self.collector_ips.append(host_ip)
                    self.collector_control_ips.append(host_control_ip)
                    self.collector_names.append(host['name'])
                    if role['container']:
                        host['containers']['analytics'] = role['container']
                if role['type'] == 'database':
                    self.database_ip = host_ip
                    self.database_ips.append(host_ip)
                    self.database_names.append(host['name'])
                    self.database_control_ips.append(host_control_ip)
                    if role['container']:
                        host['containers']['analyticsdb'] = role['container']
                if role['type'] == 'contrail-kubernetes':
                    self.kube_manager_ips.append(host_ip)
                    self.kube_manager_control_ips.append(host_control_ip)
                if role['type'] == 'vcenter_compute':
                    vcenter_compute_ip = host_ip
                    self.vcenter_compute_ips.append(host_ip)
            # end for
        # end for

        if 'vgw' in json_data:
            self.vgw_data = json_data['vgw']

        if 'xmpp_auth_enable' in json_data:
            self.xmpp_auth_enable = json_data['xmpp_auth_enable']
        if 'xmpp_dns_auth_enable' in json_data:
            self.xmpp_dns_auth_enable = json_data['xmpp_dns_auth_enable']
        if 'metadata_ssl_enable' in json_data:
            self.metadata_ssl_enable = json_data['metadata_ssl_enable']

        if 'dm_mx' in json_data:
            self.dm_mx = json_data['dm_mx']

        if 'tor_agent' in json_data:
            self.tor_agent_data = json_data['tor_agent']
        if 'sriov' in json_data:
            self.sriov_data = json_data['sriov']
        if 'dpdk' in json_data:
            self.dpdk_data = json_data['dpdk']
        if 'tor_hosts' in json_data:
            self.tor_hosts_data = json_data['tor_hosts']
        if 'kubernetes' in json_data and json_data['kubernetes'] != {}:
            self.k8s_master_ip = json_data['kubernetes']['master'].split("@")[-1]
            self.k8s_slave_ips = [value.split("@")[-1] for value in json_data['kubernetes']['slaves']]

        if 'physical_routers' in json_data:
            self.physical_routers_data = json_data['physical_routers']
        if 'ns_agilio_vrouter' in json_data:
            self.ns_agilio_vrouter_data = json_data['ns_agilio_vrouter']
            if self.ns_agilio_vrouter_data:
                self.pcap_on_vm = True

        self._process_tor_data()
        self._process_for_vcenter_gateway()
        self._process_other_orchestrators(json_data)

        if 'esxi_vms' in json_data:
            self.esxi_vm_ips = json_data['esxi_vms']
        if 'hosts_ipmi' in json_data:
            self.hosts_ipmi = json_data['hosts_ipmi']

        if not self.auth_ip:
            if self.ha_setup and self.external_vip:
                self.auth_ip = self.external_vip
            else:
                self.auth_ip = self.openstack_ip

        # If no explicit amqp servers are configured, it will be cfgm ips
        if not self.config_amqp_ips:
            self.config_amqp_ips = self.openstack_control_ips if \
                                   self.openstack_control_ips else\
                                   self.cfgm_control_ips  #vcenter only mode

        self.many_computes = (len(self.compute_ips) > 10) or False

        if 'hypervisor' in json_data:
            self.hypervisors = json_data['hypervisor']

        return json_data
    # end read_prov_file

    def _process_for_vcenter_gateway(self):
        self.vcenter_gateway = []
        for (device_name, device_dict) in self.physical_routers_data.iteritems():
            if ((device_dict.has_key('type')) and (device_dict['type'] in 'vcenter_gateway')):
               self.vcenter_gateway.append(device_dict)
    #end _process_for_vcenter_gateway

    def _process_other_orchestrators(self,json_data):
        self.orchs = []
        #Depending on these 2 below flags, the tenant would be set to vCenter
        self.vcenter_gw_setup = False
        self.vcenter_present_in_this_setup = False
        if 'other_orchestrators' in json_data:
            for (orch_name, orch_dict) in json_data['other_orchestrators'].iteritems():
                orch = {}
                orch['name'] = orch_name
                orch['type'] = orch_dict['type']
                if orch['type'] == 'vcenter':
                    orch['vcenter_server'] = orch_dict['vcenter_server']
                    self.vcenter_present_in_this_setup = True
                if 'gateway_vrouters' in orch_dict:
                    orch['gateway_vrouters'] = orch_dict['gateway_vrouters']
                    self.vcenter_gw_setup = True
                if 'controller_refs' in orch_dict:
                    orch['controller_refs'] = orch_dict['controller_refs']
                self.orchs.append(orch)
    # end _process_other_orchestrators

    def get_vcenter_gateway(self):
        for orch in self.orchs:
            if orch['type'] == 'vcenter':
                return random.choice(orch['gateway_vrouters'])

    def _process_qos_data(self, host_ip):
        '''
        Reads and populate qos related values
        '''
        qos_queue_per_host = []
        qos_queue_pg_properties_per_host = []
        try:
            if self.host_data[host_ip]['qos']:
                hw_to_logical_map_list = []
                for entry in self.host_data[host_ip]['qos']:
                    if "default" in entry.keys() and \
                    "logical_queue" in entry.keys():
                        entry["logical_queue"].append("default")
                        hw_to_logical_map = {entry["hardware_q_id"] :
                                             entry["logical_queue"]}
                    elif "default" in entry.keys() and \
                    "logical_queue" not in entry.keys():
                        hw_to_logical_map = {entry["hardware_q_id"] :
                                             ["default"]}
                    else:
                        hw_to_logical_map = {entry["hardware_q_id"] :
                                             entry["logical_queue"]}
                    hw_to_logical_map_list.append(hw_to_logical_map)
                qos_queue_per_host = [host_ip , hw_to_logical_map_list]
        except KeyError, e:
            pass
        try:
            if self.host_data[host_ip]['qos_niantic']:
                pg_properties_list = []
                for entry in self.host_data[host_ip]['qos_niantic']:
                    if 'bandwidth' not in entry.keys():
                        entry.update({'bandwidth' : "0"})
                        pg_property = entry
                    else:
                        pg_property = entry
                    pg_properties_list.append(pg_property)
                qos_queue_pg_properties_per_host = [host_ip ,
                                                     pg_properties_list]
        except KeyError, e:
            pass
        return (qos_queue_per_host, qos_queue_pg_properties_per_host)

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
                                                                    ta['tor_id']))
                        device_dict['tor_agent_dicts'].append(ta)
                        device_dict['tor_tsn_ips'].append(ta['tor_tsn_ip'])
                        if self.ha_setup == True:
                            device_dict['controller_ip'] = self.contrail_external_vip
                        else:
                            device_dict['controller_ip'] = ta['tor_tsn_ip']

    # end _process_tor_data

    def get_host_ip(self, name):
        try:
            ip = self.host_data[name]['host_ip']
        except KeyError:
            short_name = name.split('.')[0]
            ip = self.host_data[short_name]['host_ip']
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

    def get_mysql_token(self):
        #ToDo: msenthil need to remove the usage of logging into mysqldb from fixtures
        if self.mysql_token:
            return self.mysql_token
        if self.orchestrator == 'vcenter' or self.vcenter_present_in_this_setup:
            return None
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
            password,
            container='openstack')
        return self.mysql_token
    # end get_mysql_token

    def get_build_sku(self):
        if not getattr(self, 'build_sku', None):
            try:
                self.build_sku = get_build_sku(self.openstack_ip,
                     self.host_data[self.openstack_ip]['password'],
                     self.host_data[self.openstack_ip]['username'],
                     container=self.host_data[self.openstack_ip]['containers'].get('nova'))
            except Exception as e:
                self.build_sku='vcenter'		
        return self.build_sku

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,
                          password=None, pty=True, as_sudo=True,
                          container=None, detach=None, shell_prefix='/bin/bash -c '):
        '''
        container : name or id of the container
        '''
        if server_ip in self.host_data.keys():
            if not username:
                username = self.host_data[server_ip]['username']
            if not password:
                password = self.host_data[server_ip]['password']
        if container:
            cntr = self.host_data[server_ip].get('containers', {}).get(container)
            # If the container does not exist on this host, log it and
            # run the cmd on the host itself
            # This helps backward compatibility
            if not cntr:
                self.logger.debug('Container %s not in host %s, running on '
                    ' host itself' % (container, server_ip))
            container = cntr
        output = run_cmd_on_server(issue_cmd,
                          server_ip,
                          username,
                          password,
                          pty=pty,
                          as_sudo=as_sudo,
                          logger=self.logger,
                          container=container,
                          detach=detach,
                          shell_prefix=shell_prefix)
        return output
    # end run_cmd_on_server


class ContrailTestInit(object):
    def __getattr__(self, attr):
        return getattr(self.inputs, attr)

    def __init__(
            self,
            input_file=None,
            stack_user=None,
            stack_password=None,
            stack_tenant=None,
            stack_domain=None,
            logger=None):
        self.connections = None
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.inputs = TestInputs(input_file, self.logger)
        self.stack_user = stack_user or self.stack_user
        self.stack_password = stack_password or self.stack_password
        self.stack_domain = stack_domain or self.stack_domain
        self.stack_tenant = stack_tenant or self.stack_tenant
        if self.stack_domain == 'Default':
            self.project_fq_name = ['default-domain', self.stack_tenant]
        else:
            self.project_fq_name = [self.stack_domain, self.stack_tenant]
        self.project_name = self.stack_tenant
        self.domain_name = self.stack_domain
        # Possible af values 'v4', 'v6' or 'dual'
        # address_family = read_config_option(self.config,
        #                      'Basic', 'AddressFamily', 'dual')
        self.address_family = 'v4'
        if self.orchestrator == 'kubernetes' or self.slave_orchestrator == 'kubernetes':
            if not os.path.exists(self.kube_config_file):
                self.copy_file_from_server(self.kube_manager_ips[0],
                    self.kube_config_file, self.kube_config_file)
    # end __init__

    def is_ci_setup(self):
        if os.environ.has_key('ci_image'):
            return True
        else:
            return False
    # end is_ci_setup

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
        result, failed_services = ContrailStatusChecker(self
            ).wait_till_contrail_cluster_stable(tries=1)
        if not result and failed_services:
            self.logger.info("Failed services are : %s" % (failed_services))
        return result
    # end verify_state

    def verify_service_state(self, host, service=None, role=None):
        '''
        Based on name of service, it decides whether its a service name like
        "contrail-vrouter-agent", container name like "agent" or a non contrail service
        like docker.
        '''
        if service:
            services = [service] if isinstance(service, str) else service
            contrail_svc = []
            non_contrail_svc = []
            for s in services:
                svc_container = self.get_container_for_service(s)
                if svc_container:
                    contrail_svc.append(svc_container)
                elif self.get_container_for_service(container=s):
                    contrail_svc.append(s)
                else:
                    non_contrail_svc.append(s)
        if non_contrail_svc != []:
                return self.verify_non_contrail_service_state(host,
                                                              non_contrail_svc)
        return ContrailStatusChecker(self).wait_till_contrail_cluster_stable(
            host, role, contrail_svc, tries=6, delay=5)
    #end verify_service_state
    
    def verify_service_down(self, host, service=None, role=None):
        return ContrailStatusChecker(self).wait_till_service_down(
            host, role, service, tries=6, delay=5)
        
    def verify_non_contrail_service_state(self, host, service,
                                           delay =5, tries =10):
        for i in range(0, tries):
            status_dict = self.non_contrail_service_status(host, service)
            failed_services = defaultdict(dict)
            for node in status_dict:
                for svc in status_dict[node]:
                    if status_dict[node][svc] != "active":
                        failed_services[node][svc]=status_dict[node][svc]
            if failed_services:
                self.logger.debug('Not all services up. '
                   'Sleeping for %s seconds. iteration: %s' %(delay, i))
                time.sleep(delay)
                continue
            else:
                return (True, status_dict)
        self.logger.error(
            'Not all services up , Gave up!')
        return (False, failed_services)
                    
    def non_contrail_service_status(self, host, service):
        hosts = [host] if (isinstance(host, str) or isinstance(host, unicode)) else host
        services = [service] if isinstance(service, str) else service
        status_dict = dict()
        for node in hosts:
            status_dict[node] = dict() 
            for svc in services:
                cmd = "systemctl status  %s | grep Active| awk '{print $2}'" \
                    % svc
                self.logger.debug('Running command "%s" on host "%s" for service "%s"' %
                     (cmd, node, svc))
                output = self.run_cmd_on_server(
                    node, cmd, self.host_data[node]['username'],
                    self.host_data[node]['password'])
                status_dict[node][svc] = output
        return status_dict
    #end non_contrail_service_status
     
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
    def confirm_service_active(self, service_name, host, container=None,
            certs_dict=None):
        '''
        In some cases service certificates can be different than client(test
        cases in this case). so we need service certs to be used in contrail-status,
        which can be passed as certs_dict.
        certs_dict = {'key':value, 'cert':value, 'ca':value}
        '''
        raise Exception('contrail-status not supported')
        #ToDo - msenthil - need to revisit once contrail-status command is available
        if container:
            if not self.introspect_insecure:
                if certs_dict:
                    key = certs_dict['key']
                    cert = certs_dict['cert']
                    ca = certs_dict['ca']
                else:
                    key = self.introspect_keyfile
                    cert = self.introspect_certfile
                    ca = self.introspect_cafile
                ssl_args = ' -k %s -c %s -a %s' % (key, cert, ca)
            else:
                ssl_args = None
        
            status = " active"
            cmd = 'contrail-status'
            if ssl_args:
                cmd = cmd + ssl_args
            cmd = '%s | grep %s' % (cmd, service_name)
        else:
            cmd = "systemctl status  %s | grep Active| awk '{print $2}'" \
                    % service_name
        self.logger.debug('Running command "%s" on host "%s" and container "%s" '
                         'for service "%s"' %
                         (cmd, self.host_data[host]['name'], container, service_name))
        output = self.run_cmd_on_server(
            host, cmd, self.host_data[host]['username'],
            self.host_data[host]['password'],
            container=container)
        if container and output and (service_name in output) and (status in output):
            return True
        elif not container and output=="active":
            return True
        else:
            return False
    # end confirm_service_active

    def get_analytics_aaa_mode(self, host=None):
        host = host or self.collector_ip
        cmd = 'crudini --get /etc/contrail/contrail-analytics-api.conf DEFAULTS aaa_mode'
        aaa_mode = self.run_cmd_on_server(host, cmd, container='analytics-api')
        return aaa_mode or 'cloud-admin'

    # A very ugly hack until we modify all the tests to use microservice env
    def get_container_for_service(self, service = None, container = None):
        """
        To get container from service, use argument "service"
        To get service from container, use argument "container
        """
        dct = {'contrail-api': 'api-server',
               'contrail-schema': 'schema',
               'contrail-svc-monitor': 'svc-monitor',
               'contrail-config-nodemgr': 'config-nodemgr',
               'contrail-device-manager': 'device-manager',
               'contrail-webui': 'webui',
               'contrail-webui-middleware': 'webui-middleware',
               'contrail-collector': 'collector',
               'contrail-alarm-gen': 'alarm-gen',
               'contrail-analytics-api': 'analytics-api',
               'contrail-query-engine': 'query-engine',
               'contrail-analytics-nodemgr': 'analytics-nodemgr',
               'contrail-snmp-collector': 'snmp-collector',
               'contrail-topology': 'topology',
               'contrail-database': 'analytics-cassandra',
               'contrail-database-nodemgr': 'analyticsdb-nodemgr',
               'kafka': 'analytics-kafka',
               'contrail-vrouter-agent': 'agent',
               'contrail-vrouter-nodemgr': 'vrouter-nodemgr',
               'contrail-control': 'control',
               'contrail-control-nodemgr': 'control-nodemgr',
               'contrail-dns': 'dns',
               'contrail-named': 'named',
               'contrail-kube-manager': 'contrail-kube-manager',
              }
        if service:
            return dct.get(service)
        elif container:
            try:
                return dct.keys()[dct.values().index(container)]
            except ValueError:
                return

    def get_container_name(self, host, service):
        '''
           Provided the contrail service and hostname/hostip return container name
           host - hostname or hostip
           service - contrail service (eg: agent)
        '''
        return self.host_data[host].get('containers', {}).get(service)

    def is_container_up(self, host, service):
        container = self.host_data[host]['containers'][service]
        cmd = "docker ps -f NAME=%s -f status=running 2>/dev/null"%container
        for i in range(3):
            output = self.run_cmd_on_server(host, cmd, as_sudo=True)
            if not output or 'Up' not in output:
                self.logger.warn('Container %s is not up on host %s'%(container, host))
                return False
            time.sleep(3)
        self.logger.debug('Container %s is up on host %s'%(container, host))
        return True

    @property
    def is_microservices_env(self):
        if 'schema' in self.host_data[self.cfgm_ip]['containers'] and \
            'schema' in self.host_data[self.cfgm_ip]['containers']['schema']:
            return True
        return False

    def _action_on_container(self, hosts, event, container, services=None, verify_service=True, timeout=60):
        containers = set()
        for service in services or []:
            cntr = self.get_container_for_service(service)
            if cntr:
                containers.add(cntr)
        if containers and container not in ['analytics', 'analyticsdb', 'controller']:
            containers.add(container)
        for host in hosts or self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            for container in containers:
                cntr = self.get_container_name(host, container)
                if not cntr:
                    self.logger.info('Unable to find %s container on %s'%(container, host))
                    continue
                timeout = '' if event == 'start' else '-t 60'
                issue_cmd = 'docker %s %s %s' % (event, cntr, timeout)
                self.logger.info('Running %s on %s' %
                                 (issue_cmd, self.host_data[host]['name']))
                self.run_cmd_on_server(host, issue_cmd, username, password, pty=True, as_sudo=True)
                if verify_service:
                    container_status = self.is_container_up(host, container)
                    assert container_status if 'start' in event else not container_status
                    service_status = self.verify_service_state(host, container)[0]
                    assert service_status if 'start' in event else not service_status
    #end _action_on_container

    def restart_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'restart', container, verify_service=verify_service)
    # end restart_service

    def stop_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'stop', container, verify_service=verify_service)
    # end stop_service

    def start_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'start', container, verify_service=verify_service)
    # end start_service

    def get_contrail_services(self, role=None, service_name=None):
        ''' get contrail services of a role or
            if supervisor services return all services of the role
            Note: role takes precedence over service_name
        '''
        service_name = None if role else service_name
        if role == 'config' or 'supervisor-config' == service_name:
            return self.cfgm_services
        if role == 'control' or 'supervisor-control' == service_name:
            return self.control_services
        if role == 'compute' or 'supervisor-vrouter' == service_name:
            return self.compute_services
        if role == 'webui' or 'supervisor-webui' == service_name:
            return self.webui_services
        if role == 'database' or 'supervisor-database' == service_name:
            return self.database_services
        if role == 'analytics' or 'supervisor-analytics' == service_name:
            return self.collector_services
        return [service_name] if service_name else []

    def _action_on_service(self, service_name, event, host_ips=None, container=None,
            verify_service=True):
        services = self.get_contrail_services(service_name=service_name)
        if self.is_microservices_env and container:
            return self._action_on_container(host_ips, event, container, services=services,
                                             verify_service=verify_service)
        _container = container
        for service in services:
            for host in host_ips or self.host_ips:
                username = self.host_data[host]['username']
                password = self.host_data[host]['password']
                issue_cmd = 'service %s %s' % (service, event)
                self.logger.info('%s %s.service on %s - %s %s' %
                                 (event, service, self.host_data[host]['name'],
                                  issue_cmd, 'on '+container if container else 'host'))
                self.run_cmd_on_server(
                    host, issue_cmd, username, password, pty=True, container=container)
                if verify_service and (event == 'restart'):
                    assert self.verify_service_state(host, service=service_name)[0] ,\
                               "Service Restart failed for %s" % (service_name)
    #end _action_on_service

    def restart_service(self, service_name, host_ips=None,
                        container=None, verify_service=True):
        self._action_on_service(service_name, 'restart', host_ips, container,
            verify_service=verify_service)
    # end restart_service

    def stop_service(self, service_name, host_ips=None,
                     container=None):
        self._action_on_service(service_name, 'stop', host_ips, container)
    # end stop_service

    def start_service(self, service_name, host_ips=None,
                      container=None):
        self._action_on_service(service_name, 'start', host_ips, container)
    # end start_service

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
                self.cfgm_ip, issue_cmd, username, password,
                container='controller')
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
            self.cfgm_ip, issue_cmd, username, password,
            container='controller')
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
            self.cfgm_ip, issue_cmd, username, password,
            container='controller')
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

    def copy_file_to_server(self, ip, src, dstdir, dst, force=False,
                            container=None):
        host = {}
        host['ip'] = ip
        host['username'] = self.host_data[ip]['username']
        host['password'] = self.host_data[ip]['password']
        if not self.host_data[ip].get('containers', {}).get(container):
            container = None
            self.logger.debug('Container %s not in host %s, copying to '
                ' host itself' % (container, ip))
        copy_file_to_server(host, src, dstdir, dst, force, container=container)

    def copy_file_from_server(self, ip, src_file_path, dest_folder,
            container=None):
        host = {}
        host['ip'] = ip
        host['username'] = self.host_data[ip]['username']
        host['password'] = self.host_data[ip]['password']
        if not self.host_data[ip].get('containers', {}).get(container):
            container = None
            self.logger.debug('Container %s not in host %s, copying from '
                ' host itself' % (container, ip))
        copy_file_from_server(host, src_file_path, dest_folder,
            container=container)
    # end copy_file_from_server

    def get_ci_image(self, image_name='cirros'):
        '''
        if ci_image env variable is not defined, returns None
        If ci_image is defined:
            if image_name is in CI_IMAGES list
                Returns image_name
            else
                Returns 'cirros' image name
        '''
        if not os.environ.has_key('ci_image'):
            return None
        if image_name in CI_IMAGES:
            return image_name
        else:
            return DEFAULT_CI_IMAGE
    # end get_ci_image

    def get_linux_distro(self, host_ip, container=None):
        '''
        Figure out the os type and release on nodes or container in the cluster
        '''
        output = None
        cmd = 'python -c "from platform import linux_distribution; print linux_distribution()" '
        output = self.run_cmd_on_server(host_ip,
                        cmd, container=container)
        return eval(output)
    #get_linux_distro

def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--conf_file", nargs='?', default="check_string_for_empty",help="pass sanity_params.ini",required=True)
    args = parser.parse_args(remaining_argv)
    return args


def main(args_str = None):
    if not args_str:
       script_args = ' '.join(sys.argv[1:])
    script_args = _parse_args(script_args)
    inputs = ContrailTestInit(input_file=script_args.conf_file)

if __name__ == '__main__':
    main()


