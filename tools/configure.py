import argparse
import ConfigParser
import sys
import string
import json
import os
import re
import platform
from fabric.api import env, run, local, lcd, get
from fabric.context_managers import settings, hide
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
from common import log_orig as contrail_logging
from fabric.contrib.files import exists
from cfgm_common import utils
from tcutils.util import istrue

is_container_env = False

def detect_ostype():
    return platform.dist()[0].lower()

def get_address_family():
    address_family = os.getenv('AF', 'dual')
    # ToDo: CI to execute 'v4' testcases alone for now
    if os.getenv('GUESTVM_IMAGE', None):
        address_family = 'v4'
    return address_family

def get_container_name(containers, host, role):
    if containers and host in containers:
        return containers[host].get(role)
    return None

def get_value_of_key(dct, key, default=None):
    if dct and key:
        return dct.get(key, default)
    return default

def configure_test_env(contrail_fab_path='/opt/contrail/utils', test_dir='/contrail-test'):
    """
    Configure test environment by creating sanity_params.ini and sanity_testbed.json files
    """
    print "Configuring test environment"
    sys.path.insert(0, contrail_fab_path)
    from fabfile.config import testbed
    from fabfile.utils.host import get_openstack_internal_vip, \
        get_control_host_string, get_authserver_ip, get_admin_tenant_name, \
        get_authserver_port, get_env_passwords, get_authserver_credentials, \
        get_vcenter_ip, get_vcenter_port, get_vcenter_username, \
        get_vcenter_password, get_vcenter_datacenter, get_vcenter_compute, \
        get_authserver_protocol, get_region_name, get_contrail_internal_vip, \
        get_openstack_external_vip, get_contrail_external_vip, \
        get_apiserver_protocol, get_apiserver_certfile, get_apiserver_keyfile, \
        get_apiserver_cafile, get_keystone_insecure_flag, \
        get_apiserver_insecure_flag, get_keystone_certfile, get_keystone_keyfile, \
        get_keystone_cafile, get_keystone_version
    from fabfile.utils.multitenancy import get_mt_enable
    from fabfile.utils.interface import get_data_ip
    from fabfile.tasks.install import update_config_option, update_js_config
    from fabfile.utils.fabos import get_as_sudo
    logger = contrail_logging.getLogger(__name__)

    def validate_and_copy_file(filename, source_host):
        with settings(host_string='%s' %(source_host),
                      warn_only=True, abort_on_prompts=False):
            if exists(filename):
                filedir = os.path.dirname(filename)
                if not os.path.exists(filedir):
                    os.makedirs(filedir)
                get_as_sudo(filename, filename)
                return filename
            return ""

    cfgm_host = env.roledefs['cfgm'][0]
    auth_protocol = get_authserver_protocol()
    try:
        auth_server_ip = get_authserver_ip()
    except Exception:
        auth_server_ip = None
    auth_server_port = get_authserver_port()
    api_auth_protocol = get_apiserver_protocol()

    if api_auth_protocol == 'https':
        api_certfile = validate_and_copy_file(get_apiserver_certfile(), cfgm_host)
        api_keyfile = validate_and_copy_file(get_apiserver_keyfile(), cfgm_host)
        api_cafile = validate_and_copy_file(get_apiserver_cafile(), cfgm_host)
        api_insecure_flag = get_apiserver_insecure_flag()
    else:
       api_certfile = ""
       api_keyfile = ""
       api_cafile = ""
       api_insecure_flag = True

    cert_dir = os.path.dirname(api_certfile)
    if auth_protocol == 'https':
        keystone_cafile = validate_and_copy_file(cert_dir + '/' +\
                          os.path.basename(get_keystone_cafile()), cfgm_host)
        keystone_certfile = validate_and_copy_file(cert_dir + '/' +\
                          os.path.basename(get_keystone_certfile()), cfgm_host)
        keystone_keyfile = keystone_certfile
        keystone_insecure_flag = istrue(os.getenv('OS_INSECURE', \
                                 get_keystone_insecure_flag()))
    else:
        keystone_certfile = ""
        keystone_keyfile = ""
        keystone_cafile = ""
        keystone_insecure_flag = True

    with settings(warn_only=True), hide('everything'):
        with lcd(contrail_fab_path):
            if local('git branch').succeeded:
                fab_revision = local('git log --format="%H" -n 1', capture=True)
            else:
                with settings(host_string=cfgm_host), hide('everything'):
                   fab_revision = run('cat /opt/contrail/contrail_packages/VERSION')
        with lcd(test_dir):
            if local('git branch').succeeded:
                revision = local('git log --format="%H" -n 1', capture=True)
            else:
                with settings(host_string=cfgm_host), hide('everything'):
                    revision = run('cat /opt/contrail/contrail_packages/VERSION')

    sanity_testbed_dict = {
        'hosts': [],
        'vgw': [],
        'esxi_vms':[],
        'vcenter_servers':[],
        'hosts_ipmi': [],
        'tor':[],
        'sriov':[],
        'dpdk':[],
        'ns_agilio_vrouter':[],
    }

    sample_ini_file = test_dir + '/' + 'sanity_params.ini.sample'
    with open(sample_ini_file, 'r') as fd_sample_ini:
       contents_sample_ini = fd_sample_ini.read()
    sanity_ini_templ = string.Template(contents_sample_ini)

    if not getattr(env, 'test', None):
        env.test={}

    containers = env.test.get('containers')
    traffic_data = env.test.get('traffic_data')
    ixia_linux_host_ip = get_value_of_key(traffic_data, 'ixia_linux_host_ip')
    ixia_host_ip = get_value_of_key(traffic_data, 'ixia_host_ip')
    spirent_linux_host_ip = get_value_of_key(traffic_data, 'spirent_linux_host_ip')
    ixia_linux_username = get_value_of_key(traffic_data, 'ixia_linux_username')
    ixia_linux_password = get_value_of_key(traffic_data, 'ixia_linux_password')
    spirent_linux_username = get_value_of_key(traffic_data, 'spirent_linux_username')
    spirent_linux_password = get_value_of_key(traffic_data, 'spirent_linux_password')

    if env.get('orchestrator', 'openstack') == 'openstack':
        with settings(host_string = env.roledefs['openstack'][0]), hide('everything'):
            openstack_host_name = run("hostname")

    with settings(host_string = env.roledefs['cfgm'][0]), hide('everything'):
        cfgm_host_name = run("hostname")

    control_host_names = []
    for control_host in env.roledefs['control']:
        with settings(host_string = control_host), hide('everything'):
            host_name = run("hostname")
            control_host_names.append(host_name)

    cassandra_host_names = []
    if 'database' in env.roledefs.keys():
        for cassandra_host in env.roledefs['database']:
            with settings(host_string = cassandra_host), hide('everything'):
                host_name = run("hostname")
                cassandra_host_names.append(host_name)
    keystone_version = get_keystone_version()
    internal_vip = get_openstack_internal_vip()
    external_vip = get_openstack_external_vip()
    contrail_internal_vip = get_contrail_internal_vip()
    contrail_external_vip = get_contrail_external_vip()
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
        with settings(host_string = host_string), hide('everything'):
            try:
                host_name = run("hostname")
                host_fqname = run("hostname -f")
            except:
                logger.warn('Unable to login to %s'%host_ip)
                continue
        host_dict = {}

        host_dict['ip'] = host_ip
        host_dict['data-ip']= get_data_ip(host_string)[0]
        if host_dict['data-ip'] == host_string.split('@')[1]:
            host_dict['data-ip'] = get_data_ip(host_string)[0]
        host_dict['control-ip']= get_control_host_string(host_string).split('@')[1]

        host_dict['name'] = host_name
        host_dict['fqname'] = host_fqname
        host_dict['username'] = host_string.split('@')[0]
        host_dict['password'] =get_env_passwords(host_string)
        host_dict['roles'] = []
        
        if env.get('qos', {}):
            if host_string in env.qos.keys():
                role_dict = env.qos[host_string]
                host_dict['qos'] = role_dict
        if env.get('qos_niantic', {}):
            if host_string in env.qos_niantic.keys():
                role_dict = env.qos_niantic[host_string]
                host_dict['qos_niantic'] = role_dict

        if host_string in env.roledefs['openstack']:
            role_dict = {'type': 'openstack', 'params': {'cfgm': cfgm_host_name}}
            role_dict['container'] = get_container_name(containers, host_string, 'openstack')
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['cfgm']:
            role_dict = {'type': 'cfgm', 'params': {'collector': host_name, 'cassandra': ' '.join(cassandra_host_names)}}
            role_dict['container'] = get_container_name(containers, host_string, 'controller')
            if env.get('orchestrator', 'openstack') == 'openstack':
                role_dict['openstack'] = openstack_host_name
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['control']:
            role_dict = {'type': 'bgp', 'params': {'collector': cfgm_host_name, 'cfgm': cfgm_host_name}}
            role_dict['container'] = get_container_name(containers, host_string, 'controller')
            host_dict['roles'].append(role_dict)

        if 'database' in env.roledefs.keys() and host_string in env.roledefs['database']:
            role_dict = { 'type': 'database', 'params': {'cassandra': ' '.join(cassandra_host_names)} }
            role_dict['container'] = get_container_name(containers, host_string, 'analyticsdb')
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['compute']:
            role_dict = {'type': 'compute', 'params': {'collector': cfgm_host_name, 'cfgm': cfgm_host_name}}
            role_dict['container'] = get_container_name(containers, host_string, 'agent')
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
            role_dict['container'] = get_container_name(containers, host_string, 'analytics')
            host_dict['roles'].append(role_dict)

        if 'webui' in env.roledefs.keys() and host_string in env.roledefs['webui']:
            role_dict = { 'type': 'webui', 'params': {'cfgm': cfgm_host_name} }
            role_dict['container'] = get_container_name(containers, host_string, 'controller')
            host_dict['roles'].append(role_dict)

        sanity_testbed_dict['hosts'].append(host_dict)
    if env.has_key('vgw'): sanity_testbed_dict['vgw'].append(env.vgw)

    #get sriov info
    if env.has_key('sriov'):
        sanity_testbed_dict['sriov'].append(env.sriov)

    #get dpdk info
    if env.has_key('dpdk'):
        sanity_testbed_dict['dpdk'].append(env.dpdk)
   
    #get k8s info
    sanity_testbed_dict['kubernetes'] = env.get('kubernetes', {})
 
   #get ns_agilio_vrouter info
    if env.has_key('ns_agilio_vrouter'):
        sanity_testbed_dict['ns_agilio_vrouter'].append(env.ns_agilio_vrouter)

    # Read ToR config
    sanity_tor_dict = {}
    if env.has_key('tor_agent'):
        sanity_testbed_dict['tor_agent'] = env.tor_agent

    # Read any tor-host config
    if env.has_key('tor_hosts'):
        sanity_testbed_dict['tor_hosts'] = env.tor_hosts

    if env.has_key('xmpp_auth_enable'):
        sanity_testbed_dict['xmpp_auth_enable'] = env.xmpp_auth_enable
    if env.has_key('xmpp_dns_auth_enable'):
        sanity_testbed_dict['xmpp_dns_auth_enable'] = env.xmpp_dns_auth_enable

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
            #Its used for vcenter only mode provosioning for contrail-vm
            #Its not needed for vcenter_gateway mode, hence might not be there in testbed.py
            if 'contrail_vm' in esxi_hosts[esxi]:
                host_dict['contrail_vm'] = esxi_hosts[esxi]['contrail_vm']['host']
            host_dict['roles'] = []
            sanity_testbed_dict['hosts'].append(host_dict)
            sanity_testbed_dict['esxi_vms'].append(host_dict)

    vcenter_servers = env.get('vcenter_servers')
    if vcenter_servers:
        for vcenter in vcenter_servers:
            sanity_testbed_dict['vcenter_servers'].append(vcenter_servers[vcenter])

    orch = getattr(env, 'orchestrator', 'openstack')
    #get other orchestrators (vcenter etc) info if any 
    slave_orch = None  
    if env.has_key('other_orchestrators'):
        sanity_testbed_dict['other_orchestrators'] = env.other_orchestrators
        for k,v in env.other_orchestrators.items():
            if v['type'] == 'vcenter':
                slave_orch = 'vcenter'

    # get host ipmi list
    if env.has_key('hosts_ipmi'):
        sanity_testbed_dict['hosts_ipmi'].append(env.hosts_ipmi)

    # Setting slave orch to k8s when key present   
    if env.has_key('kubernetes'):
        if  sanity_testbed_dict['kubernetes']['mode'] == 'nested':
            slave_orch = 'kubernetes'

    # generate json file and copy to cfgm
    sanity_testbed_json = json.dumps(sanity_testbed_dict)
    stack_user = env.test.get('stack_user', os.getenv('STACK_USER') or env.get('stack_user', ''))
    stack_password = env.test.get('stack_password',
                         os.getenv('STACK_PASSWORD') or env.get('stack_password',''))
    stack_tenant = env.test.get('stack_tenant', os.getenv('STACK_TENANT') or env.get('stack_tenant', ''))
    stack_domain = env.test.get('stack_domain', os.getenv('STACK_DOMAIN') or env.get('stack_domain', ''))
    if not env.has_key('domain_isolation'):
        env.domain_isolation = False
    if not env.has_key('cloud_admin_domain'):
        env.cloud_admin_domain = 'Default'
    if not env.has_key('cloud_admin_user'):
        env.cloud_admin_user = 'admin'
    if not env.has_key('cloud_admin_password'):
        env.cloud_admin_password = env.get('openstack_admin_password')
    domain_isolation = env.test.get('domain_isolation',
                           os.getenv('DOMAIN_ISOLATION') or env.domain_isolation)
    cloud_admin_domain = env.test.get('cloud_admin_domain',
                           os.getenv('CLOUD_ADMIN_DOMAIN') or env.cloud_admin_domain)
    cloud_admin_user = env.test.get('cloud_admin_user',
                           os.getenv('CLOUD_ADMIN_USER') or env.cloud_admin_user)
    cloud_admin_password = env.test.get('cloud_admin_password',
                           os.getenv('CLOUD_ADMIN_PASSWORD') or env.cloud_admin_password)
    tenant_isolation = env.test.get('tenant_isolation',
                           os.getenv('TENANT_ISOLATION') or '')

    stop_on_fail = env.get('stop_on_fail', False)
    mail_to = env.test.get('mail_to', os.getenv('MAIL_TO') or '')
    log_scenario = env.get('log_scenario', 'Sanity')
    stack_region_name = get_region_name()
    admin_user, admin_password = get_authserver_credentials()
    if orch == 'kubernetes':
        admin_tenant = 'default'
    else:
        admin_tenant = get_admin_tenant_name()
    # Few hardcoded variables for sanity environment
    # can be removed once we move to python3 and configparser
    
    webserver_host = env.test.get('webserver_host',
                         os.getenv('WEBSERVER_HOST') or '')
    webserver_user = env.test.get('webserver_user',
                         os.getenv('WEBSERVER_USER') or '')
    webserver_password = env.test.get('webserver_password',
                             os.getenv('WEBSERVER_PASSWORD') or '')
    webserver_log_path = env.test.get('webserver_log_path',
        os.getenv('WEBSERVER_LOG_PATH') or '/var/www/contrail-test-ci/logs/')
    webserver_report_path = env.test.get('webserver_report_path',
        os.getenv('WEBSERVER_REPORT_PATH') or '/var/www/contrail-test-ci/reports/')
    webroot = env.test.get('webroot',
                  os.getenv('WEBROOT') or 'contrail-test-ci')
    mail_server = env.test.get('mail_server', os.getenv('MAIL_SERVER') or '')
    mail_port = env.test.get('mail_port', os.getenv('MAIL_PORT') or '25')
    fip_pool_name = env.test.get('fip_pool_name',
                        os.getenv('FIP_POOL_NAME') or 'floating-ip-pool')
    public_virtual_network=env.test.get('public_virtual_network',
        os.getenv('PUBLIC_VIRTUAL_NETWORK') or 'public')
    public_tenant_name=env.test.get('public_tenant_name',
                           os.getenv('PUBLIC_TENANT_NAME') or 'admin')
    fixture_cleanup = env.test.get('fixture_cleanup',
                          os.getenv('FIXTURE_CLEANUP') or 'yes')
    generate_html_report = env.test.get('generate_html_report',
        os.getenv('GENERATE_HTML_REPORT') or 'True')
    keypair_name = env.test.get('keypair_name',
                       os.getenv('KEYPAIR_NAME') or 'contrail_key')
    mail_sender = env.test.get('mail_sender',
        os.getenv('MAIL_SENDER') or 'contrailbuild@juniper.net')
    discovery_ip = env.test.get('discovery_ip', os.getenv('DISCOVERY_IP') or '')
    config_api_ip = env.test.get('config_api_ip', os.getenv('CONFIG_API_IP') or '')
    analytics_api_ip = env.test.get('analytics_api_ip',
                           os.getenv('ANALYTICS_API_IP') or '')
    discovery_port = env.test.get('discovery_port',
                                  os.getenv('DISCOVERY_PORT') or '')
    config_api_port = env.test.get('config_api_port',
                                   os.getenv('CONFIG_API_PORT') or '')
    analytics_api_port = env.test.get('analytics_api_port',
                                      os.getenv('ANALYTICS_API_PORT') or '')
    control_port = env.test.get('control_port', os.getenv('CONTROL_PORT') or '')
    dns_port = env.test.get('dns_port', os.getenv('DNS_PORT') or '')
    agent_port = env.test.get('agent_port', os.getenv('AGENT_PORT') or '')
    user_isolation = env.test.get('user_isolation', (os.getenv('USER_ISOLATION')) or False if stack_user else True)
    neutron_username = env.test.get('neutron_username',
                                    os.getenv('NEUTRON_USERNAME') or None)
    availability_zone = env.test.get('availability_zone',
                                     os.getenv('AVAILABILITY_ZONE') or None)
    ci_flavor = env.test.get('ci_flavor',
                             os.getenv('CI_FLAVOR') or None)
    kube_config_file = env.test.get('kube_config_file',
                                     '/etc/kubernetes/admin.conf')
    use_devicemanager_for_md5 = getattr(testbed, 'use_devicemanager_for_md5', False)
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

    if not env.has_key('openstack'):
        env.openstack = {}
    if not env.has_key('cfgm'):
        env.cfgm = {}

    config_amqp_ip = env.openstack.get('amqp_host', '')
    if config_amqp_ip:
        config_amqp_ips = [config_amqp_ip]
    else:
        config_amqp_ips = []

    # If amqp details are in env.cfgm as well, use that 
    config_amqp_port = env.cfgm.get('amqp_port', '5672')
    config_amqp_ips = env.cfgm.get('amqp_hosts', config_amqp_ips)

    key_filename = env.get('key_filename', '')
    pubkey_filename = env.get('pubkey_filename', '')

    vcenter_dc = ''
    if orch == 'vcenter' or slave_orch== 'vcenter':
        public_tenant_name='vCenter'

    if env.has_key('vcenter_servers'):
            if env.vcenter_servers:
                for vc in env.vcenter_servers:
                    for dc in env.vcenter_servers[vc]['datacenters']:    
                        vcenter_dc = dc

    #global controller
    gc_host_mgmt = getattr(testbed, 'gc_host_mgmt', '')
    gc_host_control_data =  getattr(testbed, 'gc_host_control_data', '')
    gc_user_name = getattr(testbed, 'gc_user_name', '')
    gc_user_pwd = getattr(testbed, 'gc_user_pwd', '')
    keystone_password = getattr(testbed, 'keystone_password', '')

    sanity_params = sanity_ini_templ.safe_substitute(
        {'__testbed_json_file__'   : 'sanity_testbed.json',
         '__keystone_version__'    : keystone_version,
         '__nova_keypair_name__'   : keypair_name,
         '__orch__'                : orch,
         '__admin_user__'          : admin_user,
         '__admin_password__'      : admin_password,
         '__admin_tenant__'        : admin_tenant,
         '__domain_isolation__'    : domain_isolation,
         '__cloud_admin_domain__'  : cloud_admin_domain,
         '__cloud_admin_user__'    : cloud_admin_user,
         '__cloud_admin_password__': cloud_admin_password,
         '__tenant_isolation__'    : tenant_isolation,
         '__stack_user__'          : stack_user,
         '__stack_password__'      : stack_password,
         '__auth_ip__'             : auth_server_ip,
         '__auth_port__'           : auth_server_port,
         '__auth_protocol__'       : auth_protocol,
         '__stack_region_name__'   : stack_region_name,
         '__stack_tenant__'        : stack_tenant,
         '__stack_domain__'        : stack_domain,
         '__multi_tenancy__'       : get_mt_enable(),
         '__address_family__'      : get_address_family(),
         '__log_scenario__'        : log_scenario,
         '__generate_html_report__': generate_html_report,
         '__fixture_cleanup__'     : fixture_cleanup,
         '__key_filename__'        : key_filename,
         '__pubkey_filename__'     : pubkey_filename,
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
         '__contrail_internal_vip__' : contrail_internal_vip,
         '__contrail_external_vip__' : contrail_external_vip,
         '__internal_vip__'        : internal_vip,
         '__external_vip__'        : external_vip,
         '__vcenter_dc__'          : vcenter_dc,
         '__vcenter_server__'      : get_vcenter_ip(),
         '__vcenter_port__'        : get_vcenter_port(),
         '__vcenter_username__'    : get_vcenter_username(),
         '__vcenter_password__'    : get_vcenter_password(),
         '__vcenter_datacenter__'  : get_vcenter_datacenter(),
         '__vcenter_compute__'     : get_vcenter_compute(),
         '__use_devicemanager_for_md5__'       : use_devicemanager_for_md5,
         '__discovery_port__'      : discovery_port,
         '__config_api_port__'     : config_api_port,
         '__analytics_api_port__'  : analytics_api_port,
         '__control_port__'        : control_port,
         '__dns_port__'            : dns_port,
         '__vrouter_agent_port__'  : agent_port,
         '__discovery_ip__'        : discovery_ip,
         '__config_api_ip__'       : config_api_ip,
         '__analytics_api_ip__'    : analytics_api_ip,
         '__user_isolation__'      : user_isolation,
         '__neutron_username__'    : neutron_username,
         '__availability_zone__'   : availability_zone,
         '__ci_flavor__'           : ci_flavor,
         '__config_amqp_ips__'     : ','.join(config_amqp_ips),
         '__config_amqp_port__'    : config_amqp_port,
         '__api_auth_protocol__'   : api_auth_protocol,
         '__api_certfile__'        : api_certfile,
         '__api_keyfile__'         : api_keyfile,
         '__api_cafile__'          : api_cafile,
         '__api_insecure_flag__'   : api_insecure_flag,
         '__keystone_certfile__'   : keystone_certfile,
         '__keystone_keyfile__'    : keystone_keyfile,
         '__keystone_cafile__'     : keystone_cafile,
         '__keystone_insecure_flag__': keystone_insecure_flag,
         '__gc_host_mgmt__'        : gc_host_mgmt,
         '__gc_host_control_data__': gc_host_control_data,
         '__gc_user_name__'        : gc_user_name,
         '__gc_user_pwd__'         : gc_user_pwd,
         '__keystone_password__'   : keystone_password,
         '__slave_orch__'          : slave_orch,
	 '__ixia_linux_host_ip__'  : ixia_linux_host_ip,
	 '__ixia_host_ip__'        : ixia_host_ip,
	 '__spirent_linux_host_ip__': spirent_linux_host_ip,
	 '__ixia_linux_username__' : ixia_linux_username,
	 '__ixia_linux_password__' : ixia_linux_password,
	 '__spirent_linux_username__': spirent_linux_username,
	 '__spirent_linux_password__': spirent_linux_password,

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

    keycertbundle = None
    if keystone_cafile and keystone_keyfile and keystone_certfile:
        bundle = '/tmp/keystonecertbundle.pem'
        certs = [keystone_certfile, keystone_keyfile, keystone_cafile]
        keycertbundle = utils.getCertKeyCaBundle(bundle, certs)

    with open('/etc/contrail/openstackrc','w') as rc:
        rc.write("export OS_USERNAME=%s\n" % admin_user)
        rc.write("export OS_PASSWORD=%s\n" % admin_password)
        rc.write("export OS_TENANT_NAME=%s\n" % admin_tenant)
        rc.write("export OS_REGION_NAME=%s\n" % stack_region_name)
        rc.write("export OS_AUTH_URL=%s://%s:%s/v2.0\n" % (auth_protocol,
                                                           auth_server_ip,
                                                           auth_server_port))
        rc.write("export OS_CACERT=%s\n" % keycertbundle)
        rc.write("export OS_CERT=%s\n" % keystone_certfile)
        rc.write("export OS_KEY=%s\n" % keystone_keyfile)
        rc.write("export OS_INSECURE=%s\n" % keystone_insecure_flag)
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
    config.set('auth','AUTHN_PROTOCOL', auth_protocol)
    config.set('auth','AUTHN_SERVER', auth_server_ip)
    config.set('auth','AUTHN_PORT', auth_server_port)
    if keystone_version == 'v3':
        config.set('auth','AUTHN_URL', '/v3/auth/tokens')
    else:
        config.set('auth','AUTHN_URL', '/v2.0/tokens')

    if api_auth_protocol == 'https':
        if 'global' not in config.sections():
            config.add_section('global')
        config.set('global','certfile', api_certfile)
        config.set('global','cafile', api_cafile)
        config.set('global','keyfile', api_keyfile)
        config.set('global','insecure',api_insecure_flag)

    if auth_protocol == 'https':
        if 'auth' not in config.sections():
            config.add_section('auth')
        config.set('auth','certfile', keystone_certfile)
        config.set('auth','cafile', keystone_cafile)
        config.set('auth','keyfile', keystone_keyfile)
        config.set('auth','insecure', keystone_insecure_flag)

    with open(vnc_api_ini,'w') as f:
        config.write(f)

    # For now, assume first config node is same as kubernetes master node
    # Get kube config file to the testrunner node
    if orch == 'kubernetes' or slave_orch == 'kubernetes':
        if not os.path.exists(kube_config_file):
            dir_name = os.path.dirname(kube_config_file)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with settings(host_string = env.kubernetes['master']):
                get(kube_config_file, kube_config_file)


    # If webui = True, in testbed, setup webui for sanity
    if webui:
        update_config_option('openstack', '/etc/keystone/keystone.conf',
                             'token', 'expiration',
                             '86400','keystone')
        update_js_config('openstack', '/etc/contrail/config.global.js',
                         'contrail-webui', container=is_container_env)

open_delimiters = ['(', '[', '{']
close_delimiters = [')', ']', '}']

def getindices(string):
    delimiters = open_delimiters + close_delimiters
    pattern = '{}'.format('|'.join(map(re.escape, delimiters)))
    indices = [(it.start(), string[it.start()])
               for it in re.finditer(pattern, string, re.M|re.S)]
    return indices

def get_section(string, pattern):
    block = list()
    match = re.search(pattern, string, re.M|re.S)
    if not match:
        return None, None
    match_end = match.end()
    indices = getindices(string)
    for index in range(len(indices)):
        delimiter_tuple = indices[index]
        if delimiter_tuple[0] < match_end:
            continue
        if delimiter_tuple[1] in open_delimiters:
            block.append(delimiter_tuple[0])
        else:
            if len(block) == 1:
                return (match.start(), delimiter_tuple[0]+1)
            block.pop()
    return (None, None)

def testbed_format_conversion(path='/opt/contrail/utils'):
    tb_file = path + '/fabfile/testbeds/testbed.py'
    tb_file_tmp = path + '/fabfile/testbeds/testbed_new.py'

    #check if file already has both parameter version.
    with open(tb_file) as fd:
        tb = fd.read()
    # Trim the comments
    tb = re.sub('#.*\n', '\n', tb)
    tb = re.sub('^\s*\n', '', tb, flags=re.M)
    with open(tb_file+'.cmp', 'w') as fd:
        fd.write(tb)
    # Find roledefs section
    start, end = get_section(tb, 'env.roledefs')
    if not start:
        return True
    global is_container_env
    is_container_env = True
    block = tb[start:end]
    # Find contrail-controller section
    match = re.search('contrail-controller.*?].*?,', block, re.M|re.S)
    if not match:
        return True
    ctrl_start = match.start()
    ctrl_end = match.end()
    ctrl_block = block[ctrl_start-1:ctrl_end]
    # Replace role names
    ctrl_block = ctrl_block.replace('contrail-controller', 'cfgm') + \
                 ctrl_block.replace('contrail-controller', 'control') + \
                 ctrl_block.replace('contrail-controller', 'webui')
    roledef_block = block[:ctrl_start-1] + ctrl_block + block[ctrl_end:]
    roledef_block = roledef_block.replace('contrail-analyticsdb', 'database')
    roledef_block = roledef_block.replace('contrail-analytics', 'collector')
    roledef_block = roledef_block.replace('contrail-compute', 'compute')
    new_tb = tb[:start] + roledef_block + tb[end:]
    with open(tb_file_tmp, 'w') as fd:
        fd.write(new_tb)
    env.mytestbed = 'testbed_new'

# end testbed_format_conversion

def main(argv=sys.argv):
    ap = argparse.ArgumentParser(
        description='Configure test environment')
    ap.add_argument('contrail_test_directory', type=str,
                    help='contrail test directory')
    ap.add_argument('-p','--contrail-fab-path', type=str, default='/opt/contrail/utils',
                    help='Contrail fab path on local machine')
    args = ap.parse_args()

    testbed_format_conversion(args.contrail_fab_path)
    configure_test_env(args.contrail_fab_path, args.contrail_test_directory)

if __name__ == "__main__":
    sys.exit(not main(sys.argv))
