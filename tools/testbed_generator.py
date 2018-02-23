#!/usr/bin/python

import yaml
import json
import sys
import re
import argparse
from distutils.version import LooseVersion
from collections import defaultdict

discovery_port = '5998'
config_api_port = '8082'
analytics_api_port = '8081'
control_port = '8083'
dns_port = '8092'
agent_port = '8085'

def get_neutron_username(params):
    plugin_cfgs = [v['yaml_additional_config'] for k, v in params.iteritems()
                   if type(v) is dict and v.has_key('yaml_additional_config')]

    for plugin_cfg in plugin_cfgs:
        cfg = yaml.load(plugin_cfg)
        try:
            return cfg['ldap_service_users']['quantum_settings']['keystone']['admin_user']
        except KeyError:
            try:
                return cfg['quantum_settings']['keystone']['admin_user']
            except KeyError:
                pass

def parse_astute_6(params):
    astute_dict = defaultdict(list)
    for node in params['nodes']:
        for host in astute_dict['hosts']:
            if host['host_name'] == node['name']:
               host_dict = host
               break
        else:
            host_dict = {'data_ip': node['private_address'],
                         'host_name': node['name'],
                         'mgmt_ip': node['internal_address']
                        }
            host_dict['role'] = set()
        if 'nova' in node['role'] or 'controller' in node['role']:
            host_dict['role'].add('openstack')
        if 'compute' in node['role']:
            host_dict['role'].add('compute')
        if 'contrail' in node['role']:
            host_dict['role'].add('contrail_config')
            host_dict['role'].add('contrail_control')
            host_dict['role'].add('contrail_db')
        if host_dict['role']:
            astute_dict['hosts'].append(host_dict)
    astute_dict['contrail_vip'] = params['management_vip']
    return astute_dict

def parse_astute_7(params):
    astute_dict = defaultdict(list)
    for name, node_dict in params['network_metadata']['nodes'].iteritems():
        host_dict = {'data_ip': node_dict['network_roles']['neutron/mesh'],
                     'host_name': name,
                     'mgmt_ip': node_dict['network_roles']['management']
                    }
        host_dict['role'] = set()
        for role in node_dict['node_roles']:
            if 'nova' in role or 'controller' in role:
                host_dict['role'].add('openstack')
            if 'compute' in role:
                host_dict['role'].add('compute')
            if 'contrail-config' in role:
                host_dict['role'].add('contrail_config')
            if 'contrail-control' in role:
                host_dict['role'].add('contrail_control')
            if 'contrail-analytics' in role and not 'contrail-analytics-db' in role:
                host_dict['role'].add('contrail_analytics')
            if 'contrail-db' in role:
                host_dict['role'].add('contrail_db')
        if host_dict['role']:
            astute_dict['hosts'].append(host_dict)
    astute_dict['mgmt_vip'] = params['network_metadata']['vips']['management']['ipaddr']
    astute_dict['contrail_vip'] = params['network_metadata']['vips']['contrail_priv']['ipaddr']
    return astute_dict

def parse_astute(filename, version):
    with open(filename, 'r') as fd:
        params = yaml.load(fd)
    if not version:
        version = '7.1' if params.has_key('network_metadata') else '6.1'
    if LooseVersion(version) < LooseVersion('7'):
        astute_dict = parse_astute_6(params)
    else:
        astute_dict = parse_astute_7(params)
    astute_dict['neutron_username'] = get_neutron_username(params)
    return astute_dict

def parse_openrc(filename):
    openrc_dict = dict()
    openrc_values = dict()
    for line in open(filename, 'r').readlines():
        obj = re.match("export\s+(\w+)\s*=\s*(.*)", line)
        if obj:
            val = obj.group(2).strip("'")
            val = val.strip('"')
            openrc_values.update({obj.group(1):val})

    openrc_dict['admin_tenant'] = openrc_values.get('OS_TENANT_NAME', '')
    openrc_dict['admin_user'] = openrc_values.get('OS_USERNAME', '')
    openrc_dict['admin_password'] = openrc_values.get('OS_PASSWORD', '')
    openrc_dict['region_name'] = openrc_values.get('OS_REGION_NAME', '')

    url = openrc_values['OS_AUTH_URL']
    obj = re.match("(?P<protocol>\w+)://(?P<ip>\S+):(?P<port>\d+)", url)
    if obj:
        openrc_dict['auth_ip'] = obj.group('ip')
        openrc_dict['auth_port'] = obj.group('port')
        openrc_dict['auth_protocol'] = obj.group('protocol')
    return openrc_dict

def gen_host_name(hostname):
    special_char = ['-', ':', '.']
    for char in special_char:
        hostname = hostname.replace(char, '_')
    return 'host_'+hostname

def fixup_tb_string(tb_string, hosts):
    for host in hosts:
        tb_string = tb_string.replace('"'+host+'"', host)
    tb_string = tb_string.replace('null', 'None')
    tb_string = tb_string.replace('true', 'True')
    tb_string = tb_string.replace('false', 'False')
    return tb_string

def create_testbed_file(pargs, astute_dict, openrc_dict):
    tb_filename = pargs.tb_filename
    host_string = set()
    hosts = list()
    env_roledefs = defaultdict(list)
    control_data = {}
    env_keystone = {}
    env_test = {}
    env_cfgm = {}
    env_password = {}
    login_name = pargs.login_username
    is_analytics_isolated = False
    for host_dict in astute_dict['hosts']:
        host_name = gen_host_name(host_dict['host_name'])
        hosts.append(host_name)
        host_string.add("%s = '%s@%s'" %(host_name, login_name, host_dict['mgmt_ip']))
        env_roledefs['all'].append(host_name)
        env_password.update({host_name : 'c0ntrail123'})
        control_data.update({host_name : {'ip': host_dict['data_ip'],
                                          'gw': None}})
        if 'openstack' in host_dict['role']:
            env_roledefs['openstack'].append(host_name)
        if 'contrail_config' in host_dict['role']:
            env_roledefs['cfgm'].append(host_name)
            env_roledefs['webui'].append(host_name)
        if 'contrail_analytics' in host_dict['role']:
            env_roledefs['collector'].append(host_name)
            is_analytics_isolated = True
        if 'contrail_control' in host_dict['role']:
            env_roledefs['control'].append(host_name)
        if 'contrail_db' in host_dict['role']:
            env_roledefs['database'].append(host_name)
        if 'compute' in host_dict['role']:
            env_roledefs['compute'].append(host_name)
    if not is_analytics_isolated:
        for host_dict in astute_dict['hosts']:
            if 'contrail_config' in host_dict['role']:
                host_name = gen_host_name(host_dict['host_name'])
                env_roledefs['collector'].append(host_name)

    for k,v in env_roledefs.iteritems():
        env_roledefs[k] = list(set(v))
    env_keystone.update({'keystone_ip': openrc_dict['auth_ip']})
    env_keystone.update({'auth_protocol': openrc_dict['auth_protocol']})
    env_keystone.update({'auth_port': openrc_dict['auth_port']})
    env_keystone.update({'admin_user': openrc_dict['admin_user']})
    env_keystone.update({'admin_password': openrc_dict['admin_password']})
    env_keystone.update({'admin_tenant': openrc_dict['admin_tenant']})
    env_keystone.update({'region_name': openrc_dict['region_name']})
    env_keystone.update({'insecure': 'True'})

    env_test.update({'discovery_ip': astute_dict['contrail_vip']})
    env_test.update({'config_api_ip': astute_dict['contrail_vip']})
    env_test.update({'analytics_api_ip': astute_dict['contrail_vip']})
    env_test.update({'discovery_port': discovery_port})
    env_test.update({'config_api_port': config_api_port})
    env_test.update({'analytics_api_port': analytics_api_port})
    env_test.update({'control_port': control_port})
    env_test.update({'dns_port': dns_port})
    env_test.update({'agent_port': agent_port})
    env_test.update({'user_isolation': False})
    env_test.update({'neutron_username': astute_dict['neutron_username']})
    env_test.update({'availability_zone': pargs.availability_zone_name})
    if pargs.use_ssl:
        env_cfgm.update({'auth_protocol': 'https'})
        env_cfgm.update({'insecure': 'True'})

    tb_list = list()
    tb_list.append("env.test = %s"%json.dumps(env_test, sort_keys=True, indent=4))
    tb_list.append("env.keystone = %s"%json.dumps(env_keystone, sort_keys=True, indent=4))
    tb_list.append("env.cfgm = %s"%json.dumps(env_cfgm, sort_keys=True, indent=4))
    tb_list.append("control_data = %s"%json.dumps(control_data, sort_keys=True, indent=4))
    tb_list.append("env.roledefs = %s"%json.dumps(env_roledefs, sort_keys=True, indent=4))
    tb_list.append("env.openstack_admin_password = '%s'"%
                    env_keystone['admin_password'])
    tb_list.append("env.passwords = %s"%json.dumps(env_password, sort_keys=True, indent=4))
    replaced_tb_string = fixup_tb_string('\n'.join(tb_list), hosts)

    tb_list = ['from fabric.api import env']
    tb_list.extend(sorted(host_string))
    tb_list.append(replaced_tb_string)
    with open(tb_filename, 'w+') as fd:
        fd.write('\n'.join(tb_list))

def parse_cli(args):
    parser = argparse.ArgumentParser(description='testbed.py file generator for MOS env')
    parser.add_argument('--yaml_file', required=True, help='astute.yaml file path')
    parser.add_argument('--openrc_file', help='openrc file path')
    parser.add_argument('--mos_version', help='mos version in use, optional')
    parser.add_argument('--availability_zone_name', help='Name of the nova availability zone to use for test', default='nova')
    parser.add_argument('--login_username', help='Username to use to login to the hosts (default: root)', default='root')
    parser.add_argument('--tb_filename', default='testbed.py', help='Testbed output file name')
    parser.add_argument('--use_ssl', action='store_true', help='Use https communication with contrail-api service')
    return parser.parse_args(args)

def main(args):
    pargs = parse_cli(args)
    astute_dict = parse_astute(pargs.yaml_file, pargs.mos_version)
    openrc_dict = parse_openrc(pargs.openrc_file)
    create_testbed_file(pargs, astute_dict, openrc_dict)

if __name__ == "__main__":
    main(sys.argv[1:])
