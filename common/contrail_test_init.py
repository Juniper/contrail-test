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
from keystone_tests import KeystoneCommands
from tempfile import NamedTemporaryFile
import re
from common import log_orig as contrail_logging
from common.services_map import SERVICES_MAP

import subprocess
from collections import namedtuple
import random
from cfgm_common import utils
import argparse


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
    def __init__(self, ini_file=None, logger=None):
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = custom_dict(self.get_os_version, 'os_type')
        self.config = None
        self.ini_file = ini_file
        if ini_file:
            self.config = ConfigParser.ConfigParser()
            self.config.read(ini_file)
        self.logger = logger or contrail_logging.getLogger(__name__)
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
        self.neutron_username = read_config_option(
            self.config,
            'Basic',
            'neutron_username',
            None)
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
                                            'services', 'config_amqp_port', '5672')
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
        self.pcap_on_vm = False

        self.public_host = read_config_option(self.config, 'Basic',
                                              'public_host', '10.204.216.50')

        if self.keystone_version == 'v3':
            #Set to run testecases in V2 mode
            self.v2_in_v3 = os.getenv('KSV2_IN_KSV3',None)
            if self.v2_in_v3:
                self.domain_isolation = False
                self.auth_url = '%s://%s:%s/v2.0'%(self.auth_protocol,
                                           self.auth_ip,
                                           self.auth_port)
                self.authn_url = '/v2.0/tokens'
            else:
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

        self.prov_file = self.prov_file or self._create_prov_file()
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

        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
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


    def get_os_env(self, var, default=''):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return default
    # end get_os_env

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

    def is_container_up(self, host, service):
        container = self.host_data[host]['containers'][service]
        cmd = "docker ps -f NAME=%s -f status=running 2>/dev/null"%container
        for i in range(3):
            output = self.run_cmd_on_server(host, cmd)
            if not output or 'Up' not in output:
                self.logger.warn('Container %s is not up on host %s'%(container, host))
                return False
            time.sleep(3)
        self.logger.debug('Container %s is up on host %s'%(container, host))
        return True

    def _check_containers(self, host_dict):
        '''
        Find out which components have containers and set
        corresponding attributes in host_dict to True if present
        '''
        host_dict['containers'] = {}
        if  host_dict.get('type', None) == 'esxi':
            return
        cmd = 'docker ps 2>/dev/null | awk \'{print $NF}\''
        output = self.run_cmd_on_server(host_dict['ip'], cmd)
        # If not a docker cluster, return
        if not output:
            return
        containers = [x.strip('\r') for x in output.split('\n')]

        for service, names in SERVICES_MAP.iteritems():
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
        if 'controller' in host_dict['containers']:
            host_dict['containers']['api-server'] = host_dict['containers']['controller']
            host_dict['containers']['svc-monitor'] = host_dict['containers']['controller']
            host_dict['containers']['schema'] = host_dict['containers']['controller']
            host_dict['containers']['control'] = host_dict['containers']['controller']
            host_dict['containers']['dns'] = host_dict['containers']['controller']
            host_dict['containers']['named'] = host_dict['containers']['controller']
        if 'analytics' in host_dict['containers']:
            host_dict['containers']['analytics-api'] = host_dict['containers']['analytics']
            host_dict['containers']['alarm-gen'] = host_dict['containers']['analytics']
            host_dict['containers']['collector'] = host_dict['containers']['analytics']
            host_dict['containers']['query-engine'] = host_dict['containers']['analytics']
        if 'analyticsdb' in host_dict['containers']:
            host_dict['containers']['analytics-cassandra'] = host_dict['containers']['analyticsdb']
    # end _check_containers

    @property
    def is_microservices_env(self):
        if 'schema' in self.host_data[self.cfgm_ip]['containers'] and \
            'schema' in self.host_data[self.cfgm_ip]['containers']['schema']:
            return True
        return False

    def restart_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'restart', container, verify_service=verify_service)
    # end restart_service

    def stop_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'stop', container, verify_service=verify_service)
    # end stop_service

    def start_container(self, host_ips=None, container=None, verify_service=True):
        self._action_on_container(host_ips, 'start', container, verify_service=verify_service)
    # end start_service

    def _action_on_container(self, hosts, event, container, verify_service=True):
        for host in hosts or self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            cntr = self.get_container_name(host, container)
            if not cntr:
                self.logger.info('Unable to find %s container on %s'%(container, host))
                continue
            issue_cmd = 'docker %s %s -t %s' % (event, cntr, timeout)
            self.logger.info('Running %s on %s' %
                             (issue_cmd, self.host_data[host]['name']))
            self.run_cmd_on_server(host, issue_cmd, username, password, pty=True)
            if verify_service:
                status = self.is_container_up(host, container)
                assert status if 'start' in event else not status

    def get_container_name(self, host, service):
        '''
           Provided the contrail service and hostname/hostip return container name
           host - hostname or hostip
           service - contrail service (eg: agent)
        '''
        return self.host_data[host].get('containers', {}).get(service)

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
        self.host_data = {}
        self.tor = {}
        self.tor_hosts_data = {}
        self.physical_routers_data = {}
        self.qos_queue = []
        self.lb_ip = ''
        self.lb_ips = []
        self.lb_control_ips = []
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
                if role['type'] == 'lb':
                    self.lb_ip = host_ip
                    self.lb_ips.append(host_ip)
                    self.lb_control_ips .append(host_control_ip)
                    if role['container']:
                        host['containers']['lb'] = role['container']

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

    def get_computes(self, cfgm_ip):
        kwargs = {'stack_user': self.stack_user,
                  'stack_password': self.stack_password,
                  'project_name': self.stack_tenant,
                  'auth_ip': self.auth_ip,
                  'auth_port': self.auth_port,
                  'auth_protocol': self.auth_protocol,
                  'api_server_port': self.api_server_port,
                  'api_protocol': self.api_protocol,
                  'insecure': self.insecure,
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
               * OS_DOMAIN_NAME (default: Default)
               * OS_AUTH_URL (default: http://127.0.0.1:5000/v2.0)
               * OS_INSECURE (default: False)
              login creds:
               * USERNAME (default: root)
               * PASSWORD (default: c0ntrail123)
              contrail service:
               * COLLECTOR_IP (default: neutron-server ip fetched from keystone endpoint)
        '''
        pattern = 'http[s]?://(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}):(?P<port>\d+)'
        if self.orchestrator.lower() != 'openstack':
            raise Exception('Please specify testbed info in $PARAMS_FILE '
                            'under "Basic" section, keyword "provFile"')
        if self.orchestrator.lower() == 'openstack':
            keystone = KeystoneCommands(username=self.stack_user,
                                        password=self.stack_password,
                                        tenant=self.stack_tenant,
                                        domain_name=self.stack_domain,
                                        auth_url=self.auth_url,
                                        region_name=self.region_name,
                                        insecure=self.insecure,
                                        cert=self.keystonecertfile,
                                        key=self.keystonekeyfile,
                                        cacert=self.certbundle,
                                        logger=self.logger)
            match = re.match(pattern, keystone.get_endpoint('identity'))
            self.auth_ip = match.group('ip')
            self.auth_port = match.group('port')

        # Assume contrail-collector runs in the same node as neutron-server
        collector_ip = os.getenv('ANALYTICS_IP', None) or \
                    (keystone and re.match(pattern,
                    keystone.get_endpoint('network')).group('ip'))
        cfgm = self.get_nodes_from_href(collector_ip, "config-nodes")
        database = self.get_nodes_from_href(collector_ip, "database-nodes")
        collector = self.get_nodes_from_href(collector_ip, "analytics-nodes")
        bgp = self.get_nodes_from_href(collector_ip, "control-nodes")
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
                hfqname = run('hostname -f')
            hdict = {'ip': host,
                     'data-ip': host,
                     'control-ip': host,
                     'username': username,
                     'password': password,
                     'name': hname,
                     'fqname': hfqname,
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

    def get_nodes_from_href(self, collector_ip, uve_type):
        op_server_client = VerificationOpsSrv(collector_ip)
        service_href_list = op_server_client.get_hrefs_to_all_UVEs_of_a_given_UVE_type(
                                                uveType = uve_type)
        node_name_list = []
        for elem in service_href_list:
            node_href = elem['href']
            uve = uve_type.rstrip('s')
            re_string = '(.*?)/%s/(.*?)\?flat' % uve
            match = re.search(re_string , node_href)
            node = match.group(2)
            node_name_list.append(node)
        node_ip_list = []
        for node in node_name_list:
            if uve_type == "control-nodes":
                node_dict = op_server_client.get_ops_bgprouter(node)
                node_ip = node_dict['BgpRouterState']['router_id']
                node_ip_list.append(node_ip)
            elif uve_type == "analytics-nodes":
                node_dict = op_server_client.get_ops_collector(node)
                node_ip = node_dict['ContrailConfig']['elements']\
                                    ['analytics_node_ip_address'].strip('"')
                node_ip_list.append(node_ip)
            elif uve_type == "config-nodes":
                node_dict = op_server_client.get_ops_config(node)
                node_ip = node_dict['ContrailConfig']['elements']\
                                    ['config_node_ip_address'].strip('"')
                node_ip_list.append(node_ip)
            elif uve_type == "database-nodes":
                node_dict = op_server_client.get_ops_db(node)
                node_ip = node_dict['ContrailConfig']['elements']\
                                    ['database_node_ip_address'].strip('"')
                node_ip_list.append(node_ip)
        return node_ip_list

    def get_mysql_token(self):
        #ToDo: msenthil need to remove the usage of logging into mysqldb from fixtures
        if self.mysql_token:
            return self.mysql_token
        if self.orchestrator == 'vcenter' or self.vcenter_present_in_this_setup:
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
                          detach=detach)
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
            stack_domain=None,
            logger=None):
        self.connections = None
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.inputs = TestInputs(ini_file, self.logger)
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
        #ToDo: msenthil - Revisit once contrail-status is implemented for microservices
        result = True
        failed_services = []

        for host in self.host_ips:
            self.logger.info("Executing 'contrail-status' on host %s\n" %(host))
            if host in self.compute_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='agent',
                        role='compute')
                if failed:
                    failed_services.extend(failed)
                    result = result and False

            if host in self.bgp_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='controller',
                        role='control')
                if failed:
                    failed_services.extend(failed)
                    result = result and False

            if host in self.cfgm_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='controller',
                        role='config')
                if failed:
                    failed_services.extend(failed)
                    result = result and False

            if host in self.collector_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='analytics',
                        role='analytics')
                if failed:
                    failed_services.extend(failed)
                    result = result and False

            if host in self.webui_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='controller',
                        role='webui')
                if failed:
                    failed_services.extend(failed)
                    result = result and False

            if host in self.database_ips:
                res, failed = self.verify_service_state(
                        host,
                        container='analyticsdb',
                        role='database')
                if failed:
                    failed_services.extend(failed)
                    result = result and False
            # Need to enhance verify_service_state to verify openstack services status as well
            # Commenting out openstack service verifcation untill then
            # if host == self.openstack_ip:
            #    for service in self.openstack_services:
            #        result = result and self.verify_service_state(
            #            host,
            #            service,
            #            username,
            #            password)
        if failed_services:
            self.logger.info("Failed services are : \n %s\n" % ('\n '.join(map(str, failed_services))))
        return result
    # end verify_state

    def get_service_status(self, m, service, print_output=False):
        Service = namedtuple('Service', 'name state')
        for keys, values in m.items():
            values = values[0].rstrip().split()
            if service in str(values):
                cls = Service(values[0], values[1])
                if print_output:
                    self.logger.info("%s:%s" % (cls.name, cls.state))
                return cls
        return None

    @retry(tries=6, delay=5)
    def verify_service_state(self, host, service=None, role=None, container=None, openstack=False):
        result = True
        failed_services = []
        services = self.get_contrail_services(service_name=service, role=role)
        os_services = self.openstack_services
        try:
            if openstack:
                m = self.get_openstack_status(host, container=container)
                services = os_services
            else:
                m = self.get_contrail_status(host, container=container)
            for service in services:
                cls = self.get_service_status(m, service)
                if (cls.state not in self.correct_states):
                    self.logger.error("Service %s not in correct state on %s - "
                                "its in %s state" %(cls.name, host, cls.state))
                    failed = "Host: %s  Container: %s  Role: %s  Service: %s  State: %s" %(host, container, role, cls.name, cls.state)
                    failed_services.append(failed)
                    result = result and False
                else:
                    self.logger.debug('Service %s is in %s state on %s'
                                      %(cls.name, cls.state, host))
        except Exception as e:
            self.logger.error("Unable to get service status of %s on %s"
                              %(service, host))
            self.logger.exception("Got exception as %s" % (e))
            return False, failed_services
        return result, failed_services

    # Commenting below 4 lines due to discovery changes in R4.0 - Bug 1658035
    ###def verify_control_connection(self, connections):
    ###    discovery = connections.ds_verification_obj
    ###    return discovery._verify_bgp_connection()
    ### end verify_control_connection

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
        #ToDo - msenthil - need to revisit once contrail-status command is available
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

        output = self.run_cmd_on_server(
            host, cmd, self.host_data[host]['username'],
            self.host_data[host]['password'],
            container=container)
        if output and (service_name in output) and (status in output):
            return True
        else:
            return False
    # end confirm_service_active

    def get_analytics_aaa_mode(self, host=None):
        host = host or self.collector_ip
        cmd = 'crudini --get /etc/contrail/contrail-analytics-api.conf DEFAULTS aaa_mode'
        aaa_mode = self.run_cmd_on_server(host, cmd, container='analytics-api')
        return aaa_mode or 'cloud-admin'

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
        if self.is_microservices_env:
            return self._action_on_container(host_ips, event, container,
                                             verify_service=verify_service)
        _container = container
        for service in services:
            for host in host_ips or self.host_ips:
                username = self.host_data[host]['username']
                password = self.host_data[host]['password']
                issue_cmd = 'service %s %s' % (service, event)
                self.logger.info('%s %s.service on %s - %s %s' %
                                 (event, service, self.host_data[host]['name'],
                                  issue_cmd, 'on '+container if container else ''))
                self.run_cmd_on_server(
                    host, issue_cmd, username, password, pty=True, container=container)
                if verify_service and (event == 'restart'):
                    assert self.confirm_service_active(service_name,
                               host, container=container), \
                               "Service Restart failed for %s" % (service_name)

    def restart_service(self, service_name, host_ips=None, contrail_service=True,
                        container=None, verify_service=True):
        self._action_on_service(service_name, 'restart', host_ips, container,
            verify_service=verify_service)
    # end restart_service

    def stop_service(self, service_name, host_ips=None, contrail_service=True,
                     container=None):
        self._action_on_service(service_name, 'stop', host_ips, container)
    # end stop_service

    def start_service(self, service_name, host_ips=None, contrail_service=True,
                      container=None):
        self._action_on_service(service_name, 'start', host_ips, container)
    # end start_service

    def run_status_cmd(self, server_ip, cmd='contrail-status', container=None):
        cache = self.run_cmd_on_server(server_ip, cmd,
                                       container=container)
        m = dict([(n, tuple(l.split(';')))
                  for n, l in enumerate(cache.split('\n'))])
        return m

    def get_contrail_status(self, server_ip, container=None):
        return self.run_status_cmd(server_ip, cmd='contrail-status', container=container)

    def get_openstack_status(self, server_ip, container=None):
        return self.run_status_cmd(server_ip, cmd='openstack-status', container=container)

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
    inputs = ContrailTestInit(ini_file=script_args.conf_file)

if __name__ == '__main__':
    main()


