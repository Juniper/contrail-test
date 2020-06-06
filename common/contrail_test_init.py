from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import next
from builtins import range
from builtins import object
import os
import re
import sys
import json
import time
import socket
import getpass
import configparser
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
from tcutils.contrail_status_check import ContrailStatusChecker
from keystone_tests import KeystoneCommands
from tempfile import NamedTemporaryFile
import re
from common import log_orig as contrail_logging
from common.contrail_services import *

import subprocess
from collections import namedtuple
import random
from vnc_api import utils
import argparse
import yaml
from future.utils import with_metaclass

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
OPENSHIFT_CONFIG_FILE = '/root/.kube/config'
K8S_CONFIG_FILE = '/etc/kubernetes/admin.conf'

# License: PSF License 2.0
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
# https://hg.python.org/cpython/file/d37f963394aa/Lib/subprocess.py

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


class TestInputs(with_metaclass(Singleton, object)):
    '''
       Class that would populate testbedinfo from parsing the
       .ini and .json input files if provided (or)
       check the keystone server to populate
       the same with the certain default value assumptions
    '''

    def __init__(self, input_file, logger=None):
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        self.os_type = custom_dict(self.get_os_version, 'os_type')
        self.config = None
        self.input_file = input_file
        self.logger = logger or contrail_logging.getLogger(__name__)

        self.tor_agent_data = {}
        self.sriov_data = {}
        self.dpdk_data = {}
        self.mysql_token = None
        self.pcap_on_vm = False

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
        protocol = 'https' if self.contrail_configs.get('SSL_ENABLE') else 'http'
        self.api_protocol = 'https' if self.contrail_configs.get(
            'CONFIG_API_SSL_ENABLE') else protocol
        self.analytics_api_protocol = 'https' if self.contrail_configs.get(
            'ANALYTICS_API_SSL_ENABLE') else protocol
        self.introspect_protocol = 'https' if self.contrail_configs.get(
            'INTROSPECT_SSL_ENABLE') else protocol
        if self.api_protocol == 'https':
            self.apicertfile = self.contrail_configs.get(
                'CONFIG_API_SERVER_CERTFILE') or DEFAULT_CERT
            self.apikeyfile = self.contrail_configs.get(
                'CONFIG_API_SERVER_KEYFILE') or DEFAULT_PRIV_KEY
            self.apicafile = self.contrail_configs.get(
                'CONFIG_API_SERVER_CA_CERTFILE') or DEFAULT_CA
        if self.introspect_protocol == 'https':
            self.introspect_certfile = self.contrail_configs.get(
                'INTROSPECT_CERTFILE') or DEFAULT_CERT
            self.introspect_keyfile = self.contrail_configs.get(
                'INTROSPECT_KEYFILE') or DEFAULT_PRIV_KEY
            self.introspect_cafile = self.contrail_configs.get(
                'INTROSPECT_CA_CERTFILE') or DEFAULT_CA
        if self.analytics_api_protocol == 'https':
            self.analytics_certfile = self.contrail_configs.get(
                'ANALYTICS_API_SERVER_CERTFILE') or DEFAULT_CERT
            self.analytics_keyfile = self.contrail_configs.get(
                'ANALYTICS_API_SERVER_KEYFILE') or DEFAULT_PRIV_KEY
            self.analytics_cafile = self.contrail_configs.get(
                'ANALYTICS_API_SERVER_CA_CERTFILE') or DEFAULT_CA

        apicertbundle = None
        if not self.api_insecure and self.api_protocol == 'https':
            api_bundle = '/tmp/' + get_random_string() + '.pem'
            apicertbundle = utils.getCertKeyCaBundle(api_bundle,
                            [self.apicertfile, self.apikeyfile,
                             self.apicafile])
        analyticscertbundle = None
        if not self.analytics_api_insecure and self.analytics_api_protocol == 'https':
            analytics_bundle = '/tmp/' + get_random_string() + '.pem'
            analyticscertbundle = utils.getCertKeyCaBundle(analytics_bundle,
                            [self.analytics_certfile, self.analytics_keyfile,
                             self.analytics_cafile])
        introspect_certbundle = None
        if not self.introspect_insecure and self.introspect_protocol == 'https':
            introspect_bundle = '/tmp/' + get_random_string() + '.pem'
            introspect_certbundle = utils.getCertKeyCaBundle(introspect_bundle,
                [self.introspect_certfile, self.introspect_keyfile,
                 self.introspect_cafile])
#            introspect_certbundle = self.introspect_cafile

        self.certbundle = None
        if keycertbundle or apicertbundle or introspect_certbundle or analyticscertbundle:
            bundle = '/tmp/' + get_random_string() + '.pem'
            certs = [cert for cert in [keycertbundle, apicertbundle, introspect_certbundle, analyticscertbundle] if cert]
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
            'contrail-collector', 'contrail-analytics-api',
            'contrail-query-engine', 'contrail-analytics-nodemgr']
        self.database_services = [
            'contrail-database', 'contrail-database-nodemgr']
        self.correct_states = ['active', 'backup']

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

    def get_ips_of_host(self, host, nic=None):
        if self.host_data[host].get('ips') and not nic:
            return self.host_data[host]['ips']
        username = self.host_data[host]['username']
        password = self.host_data[host]['password']
        ips = get_ips_of_host(self.get_host_ip(host), nic=nic,
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
            ip = self.get_ips_of_host(host, 'vhost0')[0]
            self.host_data[host]['control_data_ip'] = ip
            return ip
        elif service.lower() == 'control':
            ip_list = self.contrail_configs.get('CONTROL_NODES') or \
                self.contrail_configs.get('CONTROLLER_NODES') or ''
            ips = self.get_ips_of_host(host)
            for ip in ip_list.split(','):
                if ip in ips:
                    self.host_data[host]['control_data_ip'] = ip
                    return ip
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
        return self._get_ip_for_service(host, service)

    def get_service_name(self, host, service_ip):
        host_data = self.host_data[host]
        if service_ip not in host_data.get('service_name'):
            service_name = get_hostname_by_ip(host,
                service_ip,
                username=host_data['username'],
                password=host_data['password'],
                as_sudo=True,
                logger=self.logger)
            host_data['service_name'][service_ip] = service_name or \
                                                    host_data['name']
        return host_data['service_name'][service_ip]

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
        self.collector_ip = ''
        self.collector_ips = []
        self.collector_control_ips = []
        self.collector_names = []
        self.database_ips = []
        self.database_names = []
        self.database_control_ips = []
        self.compute_ips = []
        self.compute_names = []
        self.contrail_service_nodes = []
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
        self.policy_generator_ips = []
        self.policy_generator_control_ips = []
        self.dpdk_ips = []
        self.host_data = {}
        self.tor = {}
        self.tor_hosts_data = {}
        self.physical_routers_data = {}
        self.vcenter_compute_ips= []
        self.qos_queue = []
        self.qos_queue_pg_properties = []
        self.ns_agilio_vrouter_data = {}
        self.virtio = None
        self.esxi_vm_ips = {}
        self.vgw_data = {}
        self.hypervisors = {}
        self.is_dpdk_cluster = False
        provider_configs = (self.config.get('provider_config') or {}).get('bms') or {}
        username = provider_configs.get('ssh_user') or 'root'
        password = provider_configs.get('ssh_pwd') or 'c0ntrail123'
        domainsuffix = provider_configs.get('domainsuffix') or 'englab.juniper.net'
        for host, values  in (self.config.get('instances') or {}).items():
            roles = values.get('roles') or {}
            host_data = dict()
            host_data['host_ip'] = values['ip']
            if 'openstack_control' in roles and not 'openstack' in roles:
                roles.update({'openstack': {}})
            host_data['roles'] = roles
            host_data['username'] = username
            host_data['password'] = password
            host_data['service_name'] = dict()
            self.host_data[host_data['host_ip']] = host_data
            hostname = self.run_cmd_on_server(host_data['host_ip'], 'hostname')
            host_fqname = self.run_cmd_on_server(host_data['host_ip'], 'hostname -f')
            if hostname.endswith('.novalocal'):
                hostname = hostname.rstrip('.novalocal')
            self.host_names.append(hostname)
            self.host_ips.append(host_data['host_ip'])
            host_data['name'] = hostname
            host_data['fqname'] = host_fqname
            self.host_data[host_fqname] = self.host_data[hostname] = host_data
            self._check_containers(host_data)
            host_data_ip = host_control_ip = host_data['host_ip']
            qos_queue_per_host, qos_queue_pg_properties_per_host = \
                                    self._process_qos_data_yml(host_data['host_ip'])
            if qos_queue_per_host:
                self.qos_queue.append(qos_queue_per_host)
            if qos_queue_pg_properties_per_host:
                self.qos_queue_pg_properties.append(qos_queue_pg_properties_per_host)
            if 'openstack' in roles and ( 'nova' in host_data['containers'] or self.deployer == 'juju'):
                self.openstack_ip = host_data['host_ip']
                self.openstack_ips.append(host_data['host_ip'])
                service_ip = self.get_service_ip(host_data['host_ip'], 'openstack')
                self.host_data[service_ip] = host_data
                self.openstack_control_ips.append(service_ip)
                self.openstack_control_ip = service_ip
                service_name = self.get_service_name(host_data['host_ip'], service_ip)
                self.openstack_names.append(service_name)
                self.host_data[service_name] = host_data
            if 'config' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'config')
                self.host_data[service_ip] = host_data
                self.cfgm_ip = service_ip
                self.cfgm_ips.append(service_ip)
                self.cfgm_control_ips.append(service_ip)
                self.cfgm_control_ip = service_ip
                service_name = self.get_service_name(host_data['host_ip'], service_ip)
                self.cfgm_names.append(service_name)
                self.host_data[service_name] = host_data
                self.hostname = hostname
            if 'vrouter' in roles:
                data_ip = self.get_service_ip(host_data['host_ip'], 'vrouter')
                #For single-interface , setting hostname to hostfqname to make vcenter
                #scenario work
                if data_ip != host_data['host_ip']:
                    host_data['name'] = hostname
                else:
                    #not able to get host_fqname from singleinterface vcenter contrailvm
                    if self.deployer == 'rhosp' and len(hostname.split('.')) > 1:
                        host_data['name'] = hostname
                    else:
                        host_data['name'] = '.'.join([hostname,domainsuffix])
                #
                if roles['vrouter'] and roles['vrouter'].get('TSN_EVPN_MODE'):
                    self.contrail_service_nodes.append(hostname)
                else:
                    self.compute_ips.append(host_data['host_ip'])
                    service_name = self.get_service_name(host_data['host_ip'], data_ip)
                    self.compute_names.append(service_name)
                    self.compute_info[service_name] = host_data['host_ip']
                    self.compute_control_ips.append(data_ip)
                    self.host_data[service_name] = host_data
                    if service_name != hostname:
                        self.compute_info[hostname] = host_data['host_ip']
                if roles['vrouter']:
                    if roles['vrouter'].get('AGENT_MODE') == 'dpdk':
                        host_data['is_dpdk'] = True
                        self.is_dpdk_cluster = True
                        self.dpdk_ips.append(host_data['host_ip'])
                host_data_ip = host_control_ip = data_ip
            if 'control' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'control')
                self.bgp_ips.append(host_data['host_ip'])
                self.bgp_control_ips.append(service_ip)
                service_name = self.get_service_name(host_data['host_ip'], service_ip)
                self.bgp_names.append(service_name)
                host_data_ip = host_control_ip = service_ip
                self.host_data[service_name] = host_data
            if 'webui' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'webui')
                self.host_data[service_ip] = host_data
                self.webui_ip = host_data['host_ip']
                self.webui_ips.append(host_data['host_ip'])
                self.webui_control_ips.append(service_ip)
                self.host_data[service_name] = host_data
            if 'policy_generator' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'policy_generator')
                self.policy_generator_ips.append(host_data['host_ip'])
                self.policy_generator_control_ips.append(service_ip)
            if 'analytics' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'analytics')
                self.host_data[service_ip] = host_data
                self.collector_ip = service_ip
                self.collector_ips.append(service_ip)
                self.collector_control_ips.append(service_ip)
                service_name = self.get_service_name(host_data['host_ip'], service_ip)
                self.collector_names.append(service_name)
                self.host_data[service_name] = host_data
            if 'analytics_database' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'analyticsdb')
                self.host_data[service_ip] = host_data
                self.database_ip = host_data['host_ip']
                self.database_ips.append(host_data['host_ip'])
                service_name = self.get_service_name(host_data['host_ip'], service_ip)
                self.database_names.append(service_name)
                self.database_control_ips.append(service_ip)
                self.host_data[service_name] = host_data
            if 'kubemanager' in roles:
                service_ip = self.get_service_ip(host_data['host_ip'], 'kubemanager')
                self.host_data[service_ip] = host_data
                self.kube_manager_ips.append(host_data['host_ip'])
                self.kube_manager_control_ips.append(service_ip)
            if 'k8s_master' in roles:
                with hide('everything'):
                    with settings(
                        host_string='%s@%s' % (username, host_data['host_ip']),
                        password=password, warn_only=True, abort_on_prompts=False):
                        if exists(self.kube_config_file):
                            self.k8s_master_ip = host_data['host_ip'] #K8s Currently only supports 1 master
            if 'k8s_node' in roles:
                self.k8s_slave_ips.append(host_data['host_ip'])
            if 'contrail_command' in roles:
                self.command_server_ip = host_data['host_ip']
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
        for r in ['analytics_snmp', 'analytics_alarm']:
            if r in self.host_data[host]['roles']:
                roles.append(r)
        return roles

    def get_prouter_rb_roles(self, name):
        if not self.physical_routers_data or \
           not self.physical_routers_data.get(name) or \
           not self.physical_routers_data[name].get('rb_roles'):
            return []
        return self.physical_routers_data[name]['rb_roles']

    def _gen_auth_url(self):
        auth_server_ip = self.external_vip or self.openstack_ip
        if self.keystone_version == 'v3':
            auth_url = 'http://%s:5000/v3'%(auth_server_ip)
        else:
            auth_url = 'http://%s:5000/v2.0'%(auth_server_ip)
        return auth_url

    def parse_yml_file(self):
        self.key = 'key1'
        self.use_project_scoped_token = True
        self.insecure = self.api_insecure = self.introspect_insecure = self.analytics_api_insecure = True
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
        self.vro_based = False
        with open(self.input_file, 'r') as fd:
            self.config = yaml.load(fd, Loader=yaml.FullLoader)
        deployment_configs = self.config.get('deployment', {})
        self.deployer = deployment_configs.get('deployer', 'contrail-ansible-deployer')
        self.contrail_configs = contrail_configs = \
            self.config.get('contrail_configuration') or {}
        self.orchestrator_configs = orchestrator_configs = \
            self.config.get('orchestrator_configuration') or {}
        test_configs = self.config.get('test_configuration') or {}
        self.orchestrator = deployment_configs.get('orchestrator') or 'openstack'
        self.slave_orchestrator = deployment_configs.get('slave_orchestrator',None)
        if self.deployer == 'openshift':
            kube_config_file = OPENSHIFT_CONFIG_FILE
        else:
            kube_config_file = K8S_CONFIG_FILE
        self.kube_config_file = test_configs.get('kube_config_file') or kube_config_file

        self.parse_topo()
        if self.deployer != 'contrail_command':
            self.command_server_ip = None

        # contrail related configs
        self.go_server_port = '9091'
        self.api_protocol = 'https' if contrail_configs.get('CONFIG_API_USE_SSL') else 'http'
        self.api_server_port = contrail_configs.get('CONFIG_API_PORT') or '8082'
        self.analytics_api_port = contrail_configs.get('ANALYTICS_API_PORT') or '8081'
        self.bgp_port = contrail_configs.get('CONTROL_INTROSPECT_PORT') or '8083'
        self.dns_port = contrail_configs.get('DNS_INTROSPECT_PORT') or '8092'
        self.k8s_port = contrail_configs.get('K8S_INTROSPECT_PORT') or '8108'
        self.bgp_asn  = contrail_configs.get('BGP_ASN') or 64512
        self.build_sku = contrail_configs.get('OPENSTACK_VERSION', None)
        self.enable_4byte_as = contrail_configs.get('ENABLE_4BYTE_AS') or False
        self.agent_port = '8085'
        self.api_server_ip = contrail_configs.get('CONFIG_API_VIP')
        self.analytics_api_ip = contrail_configs.get('ANALYTICS_API_VIP')
        self.policy_generator_port = contrail_configs.get('POLICY_GENERATOR_PORT') or 9093
        self.config_amqp_ips = contrail_configs.get('RABBITMQ_NODES')
        self.config_amqp_port = contrail_configs.get('RABBITMQ_NODE_PORT', 5673)
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
        self.internal_vip = orchestrator_configs.get('internal_vip')
        self.external_vip = orchestrator_configs.get('external_vip') or self.internal_vip

        #kubernetes specific configs
        if self.orchestrator == 'kubernetes':
            self.k8s_cluster_name = contrail_configs.get('KUBERNETES_CLUSTER_NAME') or "k8s"
            self.admin_tenant = self.k8s_cluster_name + '-default'
        elif self.slave_orchestrator == 'kubernetes':
            self.k8s_clusters = test_configs['k8s_nested']['clusters']

        # test specific configs
        self.auth_url = test_configs.get('auth_url') or os.getenv('OS_AUTH_URL',
                                                     self._gen_auth_url())
        self.stack_user = test_configs.get('stack_user') or self.admin_username
        self.stack_password = test_configs.get('stack_password') or self.admin_password
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
        self.upgrade = test_configs.get('upgrade') or False
        self.stop_on_fail = test_configs.get('stop_on_fail') or False
        self.public_host = test_configs.get('public_host') or '10.204.216.50'
        self.public_host_url = test_configs.get('public_host_url') or 'ntp.juniper.net'
        self.public_vn = test_configs.get('public_virtual_network') or 'public-network'
        self.fip_pool = test_configs.get('public_subnet')
        self.fip_pool_name = test_configs.get('fip_pool_name')
        self.public_tenant = test_configs.get('public_tenant_name')
        self.mx_rt = str(test_configs.get('public_rt') or '')
        self.router_asn = str(test_configs.get('router_asn') or '64512')

        self.public_subnets = test_configs.get('public_subnets')
        #physical_router needs the following configuration
        #    name,type,mgmt_ip,model,vendor,asn,ssh_username,ssh_password,tunnel_ip,ports

        self.data_sw_ip = test_configs.get('data_sw_ip')
        self.data_sw_compute_bond_interface = test_configs.get('data_sw_compute_bond_interface')

        self.physical_routers_data = test_configs.get('physical_routers',{})
        self.bms_data = test_configs.get('bms',{})
        self.bms_lcm_config = test_configs.get('bms_lcm_config',{})

        self.ironic_api_config = test_configs.get('ironic_api_config',{})
        #BMS information connected to TOR's
        self.tor_hosts_data = test_configs.get('tor_hosts',{})

        self.ext_routers = []
        for rtr_name, address in test_configs.get('ext_routers', {}).items():
            self.ext_routers.append((rtr_name, address))
        self.as4_ext_routers = []
        for rtr_name, address in test_configs.get('as4_ext_routers', {}).items():
            self.as4_ext_routers.append((rtr_name, address))
        self.local_asbr_info = []
        for asbr_name, address in test_configs.get('local_asbr', {}).items():
            self.local_asbr_info.append((asbr_name, address))
        self.remote_asbr_info = {}
        remote_asbr_configs = test_configs.get('remote_asbr') or {}
        for remote_asbr in remote_asbr_configs:
          self.remote_asbr_info[remote_asbr] = {}
          for key, value in remote_asbr_configs.get(remote_asbr, {}).items():
            self.remote_asbr_info[remote_asbr][key] = value
        self.fabric_gw_info = []
        for gw_name, address in test_configs.get('fabric_gw', {}).items():
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
            self.ixia_mx_ip = traffic_gen.get('ixia_mx_ip')
            self.spirent_mx_ip = traffic_gen.get('spirent_mx_ip')
            self.ixia_mx_username = traffic_gen.get('ixia_mx_username')
            self.ixia_mx_password = traffic_gen.get('ixia_mx_password')
            self.spirent_mx_username = traffic_gen.get('spirent_mx_username')
            self.spirent_mx_password = traffic_gen.get('spirent_mx_password')
        if 'device_manager' in test_configs:
            self.dm_mx = test_configs['device_manager']
        if 'ns_agilio_vrouter' in test_configs or 'vrouter_mode_dpdk' in test_configs:
            self.pcap_on_vm = True

        self._parse_fabric(test_configs.get('fabric'))
        # If no explicit amqp servers are configured, it will be cfgm ips
        if not self.config_amqp_ips:
            self.config_amqp_ips = self.cfgm_ips
        self.many_computes = (len(self.compute_ips) > 10) or False
        self._set_auth_vars()
        if self.orchestrator == 'kubernetes' or self.slave_orchestrator == 'kubernetes':
            self.tenant_isolation = False
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

        #vcenter parsing
        if self.orchestrator == 'vcenter':
            if os.path.isfile('vcenter_vars.yaml') and os.access('vcenter_vars.yaml', os.R_OK):
                conf_file = 'vcenter_vars.yaml'
            else:
                conf_file = 'vcenter_vars.yml'

            _parse_vcenter = VcenterParmParse(inputs=self,conf_file=conf_file)
            self.vcenter_dc = _parse_vcenter.vcenter_dc
            self.vcenter_server = _parse_vcenter.vcenter_server
            self.vcenter_port = _parse_vcenter.vcenter_port
            self.vcenter_username = _parse_vcenter.vcenter_username
            self.vcenter_password = _parse_vcenter.vcenter_password
            self.dv_switch = _parse_vcenter.dv_switch
            _parse_vcenter.add_esxi_info_to_host_data()
            self.admin_username = self.vcenter_username
            self.admin_password = self.vcenter_password
            self.admin_tenant = self.stack_tenant
            self.admin_domain = self.stack_domain

        #vro parsing
        self.vro_server = test_configs.get('vro_server', None)
        if self.vro_server:
            self.vro_ip = str(self.vro_server['ip'])
            self.vro_username = self.vro_server['username']
            self.vro_password = self.vro_server['password']
            self.vro_port = str(self.vro_server['port'])
                

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
        output = self.run_cmd_on_server(host_ip,'uname -a', username, password)
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

    @property
    def is_ironic_enabled(self):
        if self.host_data[self.openstack_ip]['containers'].get('ironic_conductor'):
            return True
        return False

    @property
    def is_dp_encryption_enabled(self):
        if self.host_data[self.compute_names[0]]['containers'].get('strongswan'):
            return True
        return False

    def refresh_containers(self, host):
        del self.host_data[host]['containers']
        self._check_containers(self.host_data[host])

    def _check_containers(self, host_dict):
        '''
        Find out which components have containers and set
        corresponding attributes in host_dict to True if present
        '''
        host_dict['containers'] = {}
        if  host_dict.get('type', None) == 'esxi':
            return
        cmd = 'docker ps -a 2>/dev/null | grep -v "/pause\|/usr/bin/pod\|nova_api_\|contrail.*init\|init.*contrail\|provisioner" | awk \'{print $NF}\''
        output = self.run_cmd_on_server(host_dict['host_ip'], cmd, as_sudo=True)
        # If not a docker cluster, return
        if not output:
            return
        containers = [x.strip('\r') for x in output.split('\n')]

        containers = [x for x in containers if 'k8s_POD' not in x]
        nodemgr_cntrs = [x for x in containers if 'nodemgr' in x]
        containers = set(containers) - set(nodemgr_cntrs)

        # Observed in Openshift scenario, recent container-name changes causing issue picking wrong container which is down/inactive after fail-over 
        # and solving this with Sorting the Set and as this is simple sorting only and so should not impact any other scneario like Openstack/K8s etc
        nodemgr_cntrs = sorted(nodemgr_cntrs, reverse=True)
        containers = sorted(containers, reverse=True)

        for service, names in get_contrail_services_map(self).items():
            if 'nodemgr' in service:
                continue
            for name in names:
                container = next((container for container in containers
                                  if name in container), None)
                if container:
                    if 'dpdk' in container and 'dpdk' not  in name:
                        continue
                    host_dict['containers'][service] = container
                    containers.remove(container)
                    break

        for service, names in get_contrail_services_map(self).items():
            if 'nodemgr' in service:
                for name in names:
                    container = next((container for container in nodemgr_cntrs
                                      if name in container), None)
                    if container:
                        host_dict['containers'][service] = container
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
            host_dict['containers']['collector'] = host_dict['containers']['analytics']
            host_dict['containers']['query-engine'] = host_dict['containers']['analytics']
        if 'analytics-cassandra' not in host_dict['containers'] and 'analyticsdb' in host_dict['containers']:
            host_dict['containers']['analytics-cassandra'] = host_dict['containers']['analyticsdb']
    # end _check_containers

    def get_vcenter_gateway(self):
        for orch in self.orchs:
            if orch['type'] == 'vcenter':
                return random.choice(orch['gateway_vrouters'])

    def _parse_fabric(self, fabrics):
        self.fabrics = list()
        for fabric in fabrics or list():
            fabric_dict = dict()
            fabric_dict['namespaces'] = fabric.get('namespaces')
            fabric_dict['credentials'] = fabric.get('credentials')
            fabric_dict['provisioning_network'] = fabric.get('provisioning_network')
            fabric_dict['ztp'] = fabric.get('ztp')
            self.fabrics.append(fabric_dict)

    def _process_qos_data_yml(self, host_ip):
        '''
        Reads and populate qos related values
        '''
        qos_queue_per_host = []
        qos_queue_pg_properties_per_host = []
        vrouter_data_dict = self.host_data[host_ip]['roles'].get("vrouter", None)
        if not vrouter_data_dict:
            return (qos_queue_per_host, qos_queue_pg_properties_per_host)
        try:
            if vrouter_data_dict['QOS_QUEUE_ID']:
                hw_queues = vrouter_data_dict['QOS_QUEUE_ID']
                hw_queue_list = hw_queues.split(',')
                hw_queue_list = [x.strip() for x in hw_queue_list]
                logical_queues= vrouter_data_dict['QOS_LOGICAL_QUEUES']
                logical_queue_list = logical_queues.split(';')
                logical_queue_list = [x.strip("[] ") for x in logical_queue_list]
                if "QOS_DEF_HW_QUEUE" in list(vrouter_data_dict.keys()) and \
                        len(logical_queue_list) == len(hw_queue_list):
                    logical_queue_list[-1] = logical_queue_list[-1] + ",default"
                elif "QOS_DEF_HW_QUEUE" in list(vrouter_data_dict.keys()) and \
                        len(logical_queue_list) == (len(hw_queue_list) -1):
                    logical_queue_list.append("default")
                hw_to_logical_map_list = [{hw_queue_list[x]:logical_queue_list[x].split(",")} for \
                                     x in range(0,len(hw_queue_list))]
                qos_queue_per_host = [host_ip , hw_to_logical_map_list]
        except KeyError as e:
            pass
        try:
            if vrouter_data_dict['PRIORITY_ID']:
                priority_ids = vrouter_data_dict['PRIORITY_ID']
                priority_id_list = priority_ids.split(",")
                priority_id_list = [x.strip() for x in priority_id_list]
                priority_bws = vrouter_data_dict['PRIORITY_BANDWIDTH']
                priority_bw_list = priority_bws.split(",")
                priority_bw_list = [x.strip() for x in priority_bw_list]
                priority_schedulings = vrouter_data_dict['PRIORITY_SCHEDULING']
                priority_scheduling_list = priority_schedulings.split(",")
                priority_scheduling_list = [x.strip() for x in priority_scheduling_list]
                pg_properties_list = [{'scheduling': priority_scheduling_list[x],
                                        'bandwidth': priority_bw_list[x],
                                        'priority_id': priority_id_list[x]} for \
                                        x in range(0,len(priority_id_list))]
                qos_queue_pg_properties_per_host = [host_ip ,
                                                     pg_properties_list]
        except KeyError as e:
            pass
        return (qos_queue_per_host, qos_queue_pg_properties_per_host)

    def get_csn(self):
        return self.contrail_service_nodes

    def set_csn(self, value):
        self.contrail_service_nodes = value

    def get_host_ip(self, name):
        try:
            ip = self.host_data[name]['host_ip']
        except KeyError:
            short_name = name.split('.')[0]
            if short_name not in self.host_data:
               return None
            ip = self.host_data[short_name]['host_ip']
        return ip

    def get_host_data_ip(self, name):
        ip = self.host_data[name]['host_data_ip']
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
                          password=None, pty=True, as_sudo=True, as_daemon=False,
                          container=None, detach=None, shell_prefix='/bin/bash -c ',):
        '''
        container : name or id of the container
        '''
        if server_ip in list(self.host_data.keys()):
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
                          as_daemon=as_daemon,
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
        if self.orchestrator == 'kubernetes':
            if not os.path.exists(self.kube_config_file):
                 self.copy_file_from_server(self.k8s_master_ip,
                        self.kube_config_file, self.kube_config_file)
        if self.slave_orchestrator == 'kubernetes':
            for cluster in self.k8s_clusters:
                master_ip = self.get_host_ip(cluster['master'])
                cluster['master_public_ip'] = master_ip
                cluster['kube_config_file'] = '/etc/kubernetes/' + cluster['name'] + '.conf'
                if not os.path.exists(cluster['kube_config_file']):
                    self.copy_file_from_server(master_ip,
                        self.kube_config_file, cluster['kube_config_file'])
    # end __init__

    def is_ci_setup(self):
        if 'ci_image' in os.environ:
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

    def get_contrail_status(self, svc, state):
        '''
        Check & return List of Hosts for the given Service and State
        '''
        return ContrailStatusChecker(self).get_service_status(svc, state)

    def verify_state(self, retries=1, rfsh=False):
        result, failed_services = ContrailStatusChecker(self
            ).wait_till_contrail_cluster_stable(tries=retries, refresh=rfsh)
        if not result and failed_services:
            self.logger.info("Failed services are : %s" % (failed_services))
        return result
    # end verify_state

    def verify_service_state(self, host, service=None, role=None,
            tries=15, delay=5, expected_state=None,
            keyfile=None, certfile=None, cacert=None):
        '''
        Based on name of service, it decides whether its a service name like
        "contrail-vrouter-agent", container name like "agent" or a non contrail service
        like docker.
         expected_state: service status expected, like active, backup etc.
        '''
        contrail_svc = []
        non_contrail_svc = []
        if service:
            services = [service] if not isinstance(service, list) else service
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
            host, role, contrail_svc, tries=tries, delay=delay,
            expected_state=expected_state,
            keyfile=keyfile, certfile=certfile, cacert=cacert)
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
                if i+1 < tries:
                    time.sleep(delay)
            else:
                return (True, status_dict)
        self.logger.error(
            'Not all services up , Gave up!')
        return (False, failed_services)

    def non_contrail_service_status(self, host, service):
        hosts = [host] if not isinstance(host, list) else host
        services = [service] if not isinstance(service, list) else service
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
            for i in range(len(agent_xmpp_status)):
                actual_bgp_peer.append(agent_xmpp_status[i]['controller_ip'])
            agent_to_control_dct[ip] = actual_bgp_peer
        return agent_to_control_dct
    # end build_compute_to_control_xmpp_connection_dict

    def reboot(self, server_ip):
        i = socket.gethostbyaddr(server_ip)[0]
        print("rebooting %s" % i)
        if server_ip in list(self.host_data.keys()):
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
               'contrail-analytics-api': 'analytics-api',
               'contrail-query-engine': 'query-engine',
               'contrail-analytics-nodemgr': 'analytics-nodemgr',
               'contrail-snmp-collector': 'snmp-collector',
               'contrail-topology': 'topology',
               'contrail-database': 'analytics-cassandra',
               'contrail-database-nodemgr': 'analyticsdb-nodemgr',
               'contrail-vrouter-agent': 'agent',
               'contrail-vrouter-agent-dpdk': 'agent-dpdk',
               'contrail-vrouter-nodemgr': 'vrouter-nodemgr',
               'contrail-control': 'control',
               'contrail-control-nodemgr': 'control-nodemgr',
               'contrail-dns': 'dns',
               'contrail-named': 'named',
               'contrail-kube-manager': 'contrail-kube-manager',
               'kube-apiserver': 'kube-apiserver',
               'strongswan': 'strongswan',
               'ironic_pxe': 'ironic_pxe',
               'ironic_conductor': 'ironic_conductor',
               'stunnel': 'stunnel',
               'redis': 'redis',
              }
        if service:
            return dct.get(service)
        elif container:
            try:
                return list(dct.keys())[list(dct.values()).index(container)]
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

    def relaunch_container(self, hosts, pod):
        pods_dir = ANSIBLE_DEPLOYER_PODS_DIR[pod]
        yml_file = ANSIBLE_DEPLOYER_PODS_YML_FILE.get(pod)
        yml_file_str = '-f %s'%yml_file if yml_file else ''
        for host in hosts:
            cmd = 'cd %s ;'%pods_dir
            down_cmd = cmd + 'docker-compose %s down'%yml_file_str
            up_cmd = cmd + 'docker-compose %s up -d'%yml_file_str
            self.logger.info('Running %s on %s' %(down_cmd, host))
            self.run_cmd_on_server(host, down_cmd, pty=True, as_sudo=True)
            self.logger.info('Running %s on %s' %(up_cmd, host))
            self.run_cmd_on_server(host, up_cmd, pty=True, as_sudo=True)

    def _action_on_container(self, hosts, event, container, services=None, verify_service=True, timeout=60):
        containers = set()
        for service in services or []:
            cntr = self.get_container_for_service(service)
            if cntr:
                containers.add(cntr)
        containers.add(container)
        for host in hosts or self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            host_ip = self.host_data[host]['host_ip']
            for container in containers:
                cntr = self.get_container_name(host, container)
                if not cntr:
                    self.logger.info('Unable to find %s container on %s'%(container, host))
                    continue
                timeout = '' if event == 'start' else '-t 60'
                issue_cmd = 'docker %s %s %s' % (event, cntr, timeout)
                self.logger.info('Running %s on %s' %
                                 (issue_cmd, self.host_data[host]['name']))
                self.run_cmd_on_server(host_ip, issue_cmd, username, password, pty=True, as_sudo=True)
                if verify_service:
                    if 'stop' in event:
                        service_status = self.verify_service_down(host_ip, container)[0]
                    else:
                        service_status = self.verify_service_state(host_ip, container)[0]
                    assert service_status
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
                     container=None, verify_service=True):
        self._action_on_service(service_name, 'stop', host_ips, container,
            verify_service=verify_service)
    # end stop_service

    def start_service(self, service_name, host_ips=None,
                      container=None, verify_service=True):
        self._action_on_service(service_name, 'start', host_ips, container,
            verify_service=verify_service)
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

        print("Final commad will be pushed to MX")
        print("%s" % command_to_push)

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

        print("Final commad will be pushed to MX")
        print("%s" % command_to_push)

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
        else:
            container=self.host_data[ip].get('containers', {}).get(container)
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
        if 'ci_image' not in os.environ:
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

    def add_knob_to_container(self, node_ip, container_name, level='DEFAULT',
        knob=None, restart_container=True, file_name='entrypoint.sh'):
        ''' Add/update a configuration knob to container via common.sh or entrypoint.sh
                For entrypoint.sh, it can add at specified level
                For common.sh, it can only edit the existing knob and
                    level must be None in this case
            Args:
                node_ip         : Node on which containers need to be stopped
                container_name  : Name of the container
                file_name       : config script file name
                level           : Hierarchy level where knob needs to be added
                knob            : Knob which needs to be added or list of knobs
            E.g: add_knob_to_container('10.204.217.127', 'control_control_1',
            'DEFAULT', 'mvpn_ipv4_enable=1')
        '''

        issue_cmd = 'docker cp %s:/%s .' % (container_name, file_name)
        username = self.host_data[node_ip]['username']
        password = self.host_data[node_ip]['password']

        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

        knob_list = [knob] if not isinstance(knob, list) else knob
        local_file = file_name.split('/')[-1]

        for knob in knob_list:
            just_knob = knob[:knob.find('=')]
            if level is not None:
                #Delete the existing knob
                issue_cmd = "awk 'BEGIN { section=0; doprint=1 } "
                issue_cmd += "/\["+level+"\]/ { section=1 } "
                issue_cmd += "/"+just_knob+"/ { if (section) {doprint=0; section=0} } "
                issue_cmd += "{ if (doprint) {print} else {doprint=1} }' "
                issue_cmd = "%s %s > %s.modified" % (issue_cmd, local_file, local_file)
                self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
                self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                            as_sudo=True)
                issue_cmd = "mv %s.modified %s; chmod +x %s" % (local_file, local_file, local_file)
                self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
                self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                            as_sudo=True)
                #Insert the new knob at given level
                issue_cmd = 'grep -q -F \''+knob+'\' %s ||' % (local_file) + \
                    'sed -i  \'/\['+level+'\]/a '+knob+'\' %s' % (local_file)
            else:
                #Replace the existing knob with new value
                #Append at next line of first match then delete first match
                issue_cmd = 'sed -i \'/'+just_knob+'=.*/a %s\' %s' % (knob, local_file)
                issue_cmd = issue_cmd + ';sed -i \'0,/%s=.*/{//d}\' %s' % (
                    just_knob, local_file)

            self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
            self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

        issue_cmd = 'docker cp %s %s:/%s' % (local_file, container_name,
            file_name)
        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)
        if restart_container:
            issue_cmd = 'docker restart %s -t 60' % (container_name)
            self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
            self.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                        as_sudo=True)

    # end _add_knob_to_container

    def enable_vro(self, knob=False):
        self.vro_based = knob
    #end enable_vro
    
def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--conf_file", nargs='?', default="check_string_for_empty",help="pass sanity_params.ini",required=True)
    args = parser.parse_args(remaining_argv)
    return args


class VcenterParmParse(object):
    def __init__(self,inputs=None,conf_file=None):
        with open(conf_file, 'r') as fd:
            self.config = yaml.load(fd)
        self.inputs = inputs

    def _parse(self,server):
        for vc_server in self.config['vcenter_servers']:
             if server in vc_server:
                 return vc_server[server]

    def _parse_esxi_info(self):
        for esxi in self.config['esxihosts']:
            dct =dict()
            dct[esxi['name']] = esxi
            self.inputs.host_data.update(dct)

    def add_esxi_info_to_host_data(self):
        self._parse_esxi_info()

    @property
    def vcenter_dc(self,server='server1'):
        vc_server_dict = self._parse(server)
        return vc_server_dict['datacentername']

    @property
    def vcenter_server(self,server='server1'):
        vc_server_dict = self._parse(server)
        return vc_server_dict['hostname']

    @property
    def vcenter_port(self,server='server1'):
        return '443'

    @property
    def vcenter_username(self,server='server1'):
        vc_server_dict = self._parse(server)
        return vc_server_dict['username']

    @property
    def vcenter_password(self,server='server1'):
        vc_server_dict = self._parse(server)
        return vc_server_dict['password']

    @property
    def dv_switch(self,server='server1'):
        vc_server_dict = self._parse(server)
        return vc_server_dict['dv_switch']['dv_switch_name']


def main(args_str = None):
    if not args_str:
       script_args = ' '.join(sys.argv[1:])
    script_args = _parse_args(script_args)
    inputs = ContrailTestInit(input_file=script_args.conf_file)


if __name__ == '__main__':
    main()
