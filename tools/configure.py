import argparse
import ConfigParser
import sys
import string
import json
import os
from fabric.api import env, run, local, lcd
from fabric.context_managers import settings, hide


def get_address_family():
    address_family = os.getenv('AF', 'dual')
    # ToDo: CI to execute 'v4' testcases alone for now
    if os.getenv('GUESTVM_IMAGE', None):
        address_family = 'v4'
    return address_family


def configure_test_env(contrail_fab_path='/opt/contrail/utils', test_dir='/contrail-test'):
    """
    Configure test environment by creating sanity_params.ini and sanity_testbed.json files
    """
    sys.path.insert(0, contrail_fab_path)
    from fabfile.testbeds import testbed
    from fabfile.utils.host import get_openstack_internal_vip,\
        get_control_host_string, get_authserver_ip, get_admin_tenant_name, \
        get_authserver_port, get_env_passwords, get_authserver_credentials, \
        get_vcenter_ip, get_vcenter_port, get_vcenter_username, \
        get_vcenter_password, get_vcenter_datacenter, get_vcenter_compute, \
        get_authserver_protocol
    from fabfile.utils.multitenancy import get_mt_enable
    from fabfile.utils.interface import get_data_ip

    cfgm_host = env.roledefs['cfgm'][0]

    with settings(warn_only=True):
        with lcd(contrail_fab_path):
            if local('git branch').succeeded:
                fab_revision = local('git log --format="%H" -n 1', capture=True)
            else:
                with settings(host_string=cfgm_host):
                   fab_revision = run('cat /opt/contrail/contrail_packages/VERSION')
        with lcd(test_dir):
            if local('git branch').succeeded:
                revision = local('git log --format="%H" -n 1', capture=True)
            else:
                with settings(host_string=cfgm_host):
                    revision = run('cat /opt/contrail/contrail_packages/VERSION')

    sanity_testbed_dict = {
        'hosts': [],
        'vgw': [],
        'esxi_vms':[],
        'hosts_ipmi': [],
        'tor':[],
    }

    sample_ini_file = test_dir + '/' + 'sanity_params.ini.sample'
    with open(sample_ini_file, 'r') as fd_sample_ini:
       contents_sample_ini = fd_sample_ini.read()
    sanity_ini_templ = string.Template(contents_sample_ini)

    with settings(host_string = env.roledefs['openstack'][0]):
        openstack_host_name = run("hostname")

    with settings(host_string = env.roledefs['cfgm'][0]):
        cfgm_host_name = run("hostname")

    control_host_names = []
    for control_host in env.roledefs['control']:
        with settings(host_string = control_host):
            host_name = run("hostname")
            control_host_names.append(host_name)

    cassandra_host_names = []
    if 'database' in env.roledefs.keys():
        for cassandra_host in env.roledefs['database']:
            with settings(host_string = cassandra_host):
                host_name = run("hostname")
                cassandra_host_names.append(host_name)

    internal_vip = get_openstack_internal_vip()
    multi_role_test = False
    for host_string in env.roledefs['all']:
        if host_string in env.roledefs.get('test',[]):
            for role in env.roledefs.iterkeys():
                if role in ['test','all']:
                    continue
                if host_string in env.roledefs.get(role,[]):
                    multi_role_test=True
                    break
            if not multi_role_test:
                continue
        host_ip = host_string.split('@')[1]
        with settings(host_string = host_string):
            host_name = run("hostname")

        host_dict = {}

        host_dict['ip'] = host_ip
        host_dict['data-ip']= get_data_ip(host_string)[0]
        if host_dict['data-ip'] == host_string.split('@')[1]:
            host_dict['data-ip'] = get_data_ip(host_string)[0]
        host_dict['control-ip']= get_control_host_string(host_string).split('@')[1]

        host_dict['name'] = host_name
        host_dict['username'] = host_string.split('@')[0]
        host_dict['password'] =get_env_passwords(host_string)
        host_dict['roles'] = []

        if not internal_vip:
            if host_string in env.roledefs['openstack']:
                role_dict = {'type': 'openstack', 'params': {'cfgm': cfgm_host_name}}
                host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['cfgm']:
            role_dict = {'type': 'cfgm', 'params': {'collector': host_name, 'cassandra': ' '.join(cassandra_host_names)}}

            if internal_vip:
                role_dict['openstack'] = 'contrail-vip'
            else:
                role_dict['openstack'] = openstack_host_name

            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['control']:
            role_dict = {'type': 'bgp', 'params': {'collector': cfgm_host_name, 'cfgm': cfgm_host_name}}
            host_dict['roles'].append(role_dict)

        if 'database' in env.roledefs.keys() and host_string in env.roledefs['database']:
            role_dict = { 'type': 'database', 'params': {'cassandra': ' '.join(cassandra_host_names)} }
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['compute']:
            role_dict = {'type': 'compute', 'params': {'collector': cfgm_host_name, 'cfgm': cfgm_host_name}}
            role_dict['params']['bgp'] = []
            if len(env.roledefs['control']) == 1:
                role_dict['params']['bgp'] = control_host_names
            else:
                for control_node in control_host_names:
                    role_dict['params']['bgp'].append(control_node)
               # role_dict['params']['bgp'].extend(control_host_names[randrange(len(env.roledefs['control']))])
            host_dict['roles'].append(role_dict)

        if 'collector' in env.roledefs.keys() and host_string in env.roledefs['collector']:
            role_dict = { 'type': 'collector', 'params': {'cassandra': ' '.join(cassandra_host_names)} }
            host_dict['roles'].append(role_dict)

        if 'webui' in env.roledefs.keys() and host_string in env.roledefs['webui']:
            role_dict = { 'type': 'webui', 'params': {'cfgm': cfgm_host_name} }
            host_dict['roles'].append(role_dict)

        sanity_testbed_dict['hosts'].append(host_dict)
    if env.has_key('vgw'): sanity_testbed_dict['vgw'].append(env.vgw)

    # Read ToR config
    sanity_tor_dict = {}
    if env.has_key('tor_agent'):
        sanity_testbed_dict['tor_agent'] = env.tor_agent

    # Read any tor-host config
    if env.has_key('tor_hosts'):
        sanity_testbed_dict['tor_hosts'] = env.tor_hosts

    # Read any MX config (as physical_router )
    if env.has_key('physical_routers'):
        sanity_testbed_dict['physical_routers'] = env.physical_routers

    esxi_hosts = getattr(testbed, 'esxi_hosts', None)
    if esxi_hosts:
        for esxi in esxi_hosts:
            host_dict = {}
            host_dict['ip'] = esxi_hosts[esxi]['ip']
            host_dict['data-ip'] = host_dict['ip']
            host_dict['control-ip'] = host_dict['ip']
            host_dict['name'] = esxi
            host_dict['username'] = esxi_hosts[esxi]['username']
            host_dict['password'] = esxi_hosts[esxi]['password']
            host_dict['contrail_vm'] = esxi_hosts[esxi]['contrail_vm']['host']
            host_dict['roles'] = []
            sanity_testbed_dict['hosts'].append(host_dict)
            sanity_testbed_dict['esxi_vms'].append(host_dict)
    # Adding vip VIP dict for HA test setup

    with settings(host_string = env.roledefs['openstack'][0]):
        if internal_vip:
            host_dict = {}
            host_dict['data-ip']= get_authserver_ip()
            host_dict['control-ip']= get_authserver_ip()
            host_dict['ip']= get_authserver_ip()
            host_dict['name'] = 'contrail-vip'
            with settings(host_string = env.roledefs['cfgm'][0]):
                host_dict['username'] = host_string.split('@')[0]
                host_dict['password'] = get_env_passwords(host_string)
            host_dict['roles'] = []
            role_dict = {'type': 'openstack', 'params': {'cfgm': cfgm_host_name}}
            host_dict['roles'].append(role_dict)
            sanity_testbed_dict['hosts'].append(host_dict)

    # get host ipmi list
    if env.has_key('hosts_ipmi'):
        sanity_testbed_dict['hosts_ipmi'].append(env.hosts_ipmi)


    if not getattr(env, 'test', None):
        env.test={}

    # generate json file and copy to cfgm
    sanity_testbed_json = json.dumps(sanity_testbed_dict)

    stop_on_fail = env.get('stop_on_fail', False)
    mail_to = env.test.get('mail_to', '')
    log_scenario = env.get('log_scenario', 'Sanity')
    stack_user, stack_password = get_authserver_credentials()
    stack_tenant = get_admin_tenant_name()
    # Few hardcoded variables for sanity environment
    # can be removed once we move to python3 and configparser
    stack_domain = env.get('stack_domain', 'default-domain')
    webserver_host = env.test.get('webserver_host', '')
    webserver_user = env.test.get('webserver_user', '')
    webserver_password = env.test.get('webserver_password', '')
    webserver_log_path = env.test.get('webserver_log_path', '/var/www/contrail-test-ci/logs/')
    webserver_report_path = env.test.get('webserver_report_path', '/var/www/contrail-test-ci/reports/')
    webroot = env.test.get('webroot', 'contrail-test-ci')
    mail_server = env.test.get('mail_server', '')
    mail_port = env.test.get('mail_port','25')
    fip_pool_name = env.test.get('fip_pool_name','floating-ip-pool')
    public_virtual_network=env.test.get('public_virtual_network','public')
    public_tenant_name=env.test.get('public_tenant_name','admin')
    fixture_cleanup = env.test.get('fixture_cleanup', 'yes')
    generate_html_report = env.test.get('generate_html_report','True')
    keypair_name = env.test.get('keypair_name', 'contrail_key')
    mail_sender = env.test.get('mail_sender', 'contrailbuild@juniper.net')

    use_devicemanager_for_md5 = getattr(testbed, 'use_devicemanager_for_md5', False)
    orch = getattr(env, 'orchestrator', 'openstack')
    router_asn = getattr(testbed, 'router_asn', '')
    public_vn_rtgt = getattr(testbed, 'public_vn_rtgt', '')
    public_vn_subnet = getattr(testbed, 'public_vn_subnet', '')
    ext_routers = getattr(testbed, 'ext_routers', '')
    router_info = str(ext_routers)
    test_verify_on_setup = getattr(env, 'test_verify_on_setup', True)
    webui = getattr(testbed, 'webui', False)
    horizon = getattr(testbed, 'horizon', False)
    ui_config = getattr(testbed, 'ui_config', False)
    ui_browser = getattr(testbed, 'ui_browser', False)

    vcenter_dc = ''
    if orch == 'vcenter':
        public_tenant_name='vCenter'

    if env.has_key('vcenter'):
        if env.vcenter:
            vcenter_dc = env.vcenter['datacenter']

    sanity_params = sanity_ini_templ.safe_substitute(
        {'__testbed_json_file__'   : 'sanity_testbed.json',
         '__nova_keypair_name__'   : keypair_name,
         '__orch__'                : orch,
         '__stack_user__'          : stack_user,
         '__stack_password__'      : stack_password,
         '__auth_ip__'             : get_authserver_ip(),
         '__auth_port__'           : get_authserver_port(),
         '__stack_tenant__'        : stack_tenant,
         '__stack_domain__'        : stack_domain,
         '__multi_tenancy__'       : get_mt_enable(),
         '__address_family__'      : get_address_family(),
         '__log_scenario__'        : log_scenario,
         '__generate_html_report__': generate_html_report,
         '__fixture_cleanup__'     : fixture_cleanup,
         '__webserver__'           : webserver_host,
         '__webserver_user__'      : webserver_user,
         '__webserver_password__'  : webserver_password,
         '__webserver_log_dir__'   : webserver_log_path,
         '__webserver_report_dir__': webserver_report_path,
         '__webroot__'             : webroot,
         '__mail_server__'         : mail_server,
         '__mail_port__'           : mail_port,
         '__sender_mail_id__'      : mail_sender,
         '__receiver_mail_id__'    : mail_to,
         '__http_proxy__'          : env.get('http_proxy', ''),
         '__ui_browser__'          : ui_browser,
         '__ui_config__'           : ui_config,
         '__horizon__'             : horizon,
         '__webui__'               : webui,
         '__devstack__'            : False,
         '__public_vn_rtgt__'      : public_vn_rtgt,
         '__router_asn__'          : router_asn,
         '__router_name_ip_tuples__': router_info,
         '__public_vn_name__'      : fip_pool_name,
         '__public_virtual_network__':public_virtual_network,
         '__public_tenant_name__'  :public_tenant_name,
         '__public_vn_subnet__'    : public_vn_subnet,
         '__test_revision__'       : revision,
         '__fab_revision__'        : fab_revision,
         '__test_verify_on_setup__': test_verify_on_setup,
         '__stop_on_fail__'        : stop_on_fail,
         '__ha_setup__'            : getattr(testbed, 'ha_setup', ''),
         '__ipmi_username__'       : getattr(testbed, 'ipmi_username', ''),
         '__ipmi_password__'       : getattr(testbed, 'ipmi_password', ''),
         '__vcenter_dc__'          : vcenter_dc,
         '__vcenter_server__'      : get_vcenter_ip(),
         '__vcenter_port__'        : get_vcenter_port(),
         '__vcenter_username__'    : get_vcenter_username(),
         '__vcenter_password__'    : get_vcenter_password(),
         '__vcenter_datacenter__'  : get_vcenter_datacenter(),
         '__vcenter_compute__'     : get_vcenter_compute(),
         '__use_devicemanager_for_md5__'       : use_devicemanager_for_md5,
        })

    ini_file = test_dir + '/' + 'sanity_params.ini'
    testbed_json_file = test_dir + '/' + 'sanity_testbed.json'
    with open(ini_file, 'w') as ini:
        ini.write(sanity_params)

    with open(testbed_json_file,'w') as tb:
        tb.write(sanity_testbed_json)

    # Create /etc/contrail/openstackrc
    if not os.path.exists('/etc/contrail'):
        os.makedirs('/etc/contrail')

    with open('/etc/contrail/openstackrc','w') as rc:
        rc.write("export OS_USERNAME=%s\n" % stack_user)
        rc.write("export OS_PASSWORD=%s\n" % stack_password)
        rc.write("export OS_TENANT_NAME=%s\n" % stack_tenant)
        rc.write("export OS_AUTH_URL=%s://%s:5000/v2.0\n" % (get_authserver_protocol(), get_authserver_ip()))
        rc.write("export OS_NO_CACHE=1\n")

    # Write vnc_api_lib.ini - this is required for vnc_api to connect to keystone
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    vnc_api_ini = '/etc/contrail/vnc_api_lib.ini'
    if os.path.exists(vnc_api_ini):
        config.read(vnc_api_ini)

    if 'auth' not in config.sections():
        config.add_section('auth')

    config.set('auth','AUTHN_TYPE', 'keystone')
    config.set('auth','AUTHN_PROTOCOL', get_authserver_protocol())
    config.set('auth','AUTHN_SERVER', get_authserver_ip())
    config.set('auth','AUTHN_PORT', get_authserver_port())
    config.set('auth','AUTHN_URL', '/v2.0/tokens')

    with open(vnc_api_ini,'w') as f:
        config.write(f)

def main(argv=sys.argv):
    ap = argparse.ArgumentParser(
        description='Configure test environment')
    ap.add_argument('contrail_test_directory', type=str,
                    help='contrail test directory')
    ap.add_argument('-p','--contrail-fab-path', type=str, default='/opt/contrail/utils',
                    help='Contrail fab path on local machine')
    args = ap.parse_args()

    configure_test_env(args.contrail_fab_path, args.contrail_test_directory)

if __name__ == "__main__":
    sys.exit(not main(sys.argv))
