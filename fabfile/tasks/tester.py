import os
import re
import json
import string
import tempfile
from random import randrange
from datetime import datetime as dt

from fabfile.config import *
from fabfile.utils.host import *
from fabfile.utils.interface import *
from fabfile.utils.multitenancy import *


@roles('build')
@task
def setup_test_env():
    fab_revision = local('cat .git/refs/heads/master', capture=True)
    if CONTROLLER_TYPE == 'Cloudstack':
        revision = local('cat %s/.git/refs/heads/cs_sanity' % env.test_repo_dir, capture=True)
    else:
        revision = local('cat %s/.git/refs/heads/master' % env.test_repo_dir, capture=True)
    cfgm_host = env.roledefs['cfgm'][0]
    cfgm_ip = hstr_to_ip(cfgm_host)

    execute(copy_dir, env.test_repo_dir, cfgm_host)

    sanity_testbed_dict = {
        'hosts': [],
    }

    sanity_ini_templ = string.Template("""[Basic]
# Provisioning file

# Provisioning json file
testRepoDir=$__test_repo__
provFile=sanity_testbed.json
logScenario=$__log_scenario__

# Nova Keypair 
key=key1

# Pointer for the repo which contains new packages. Needed for setup_systems.py

stackUser=admin
stackPassword=$__stack_password__
stackTenant=$__stack_tenant__
multiTenancy=$__multi_tenancy__

# If you want the HTML report through HTMLTestRunner, select 'yes'. If not, the basic Unittest TextTestRunner will run the tests 
generate_html_report=yes

# If you dont want fixture cleanups to remove the objects which are created as part of setUp of the fixture, set fixtureCleanup to 'no'. Default value should be 'yes'. If objects are already present before start of tests, they are not deleted. To clean them up forcefully, set fixtureCleanup to 'force'
fixtureCleanup=yes

[WebServer]
# The URL to which the test log file and HTML report would be uploaded to.  
# path is the local filesystem path to which the files will get copied to 
# Ex: http://10.204.216.50/Docs/
host=10.204.216.50
username=bhushana
password=bhu@123
path=/home/bhushana/Documents/technical/logs/
webRoot=Docs

[Mail]
server=$__mail_server__
port=$__mail_port__
mailTo=$__mail_to__
mailSender=contrailbuild@juniper.net

[log_screen]
# set if log redirection to console needed
log_to_console= yes

[loggers]
keys=root,log01

[logger_root]
handlers=screen
#qualname=(root)
level=ERROR

[logger_log01]
handlers=file
qualname=log01
level=DEBUG
propagate=0


[formatters]
keys=std

[formatter_std]
format=%(asctime)s [ %(levelname)5s ] %(message)s


[handlers]
keys=file,screen
#keys=file

[handler_file]
class= custom_filehandler.CustomFileHandler
formatter=std
level=DEBUG
args=( 'test_details.log.$__timestamp__','a')
#args is of the form : ( log-file-name , write-mode)

[handler_screen]
class=StreamHandler
formatter=std
#level=ERROR
args=(sys.stdout,)

[Mx]
# Currently, MX configuration will be read only for the BLR sanity setup with a pre-defined MX configuration
#Route Target on the MX
mx_rt=$__public_vn_rtgt__

#Asn
router_asn=$__router_asn__

#Just a notation to identify the router
$__ext_router_names__
$__ext_router_ips__

fip_pool=$__public_vn_subnet__
fip_pool_name=public-pool

[repos]
#Test Revision
test_revision=$__test_revision__
fab_revision=$__fab_revision__

#For debugging
[debug]
stop_on_fail=no
""")

    if CONTROLLER_TYPE == 'Openstack':
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

    for host_string in env.roledefs['all']:
        host_ip = host_string.split('@')[1]
        with settings(host_string = host_string):
            host_name = run("hostname")

        host_dict = {}
        # We may have to change it when we have HA support in Cloudstack
        host_dict['ip'] = "127.0.0.1" if (CONTROLLER_TYPE == 'Cloudstack' and host_string in env.roledefs['control']) else host_ip
        host_dict['data-ip']= get_data_ip(host_string)[0]
        if host_dict['data-ip'] == host_string.split('@')[1]:
            host_dict['data-ip'] = get_data_ip(host_string,section='control')[0]
        host_dict['control-ip']= get_control_host_string(host_string).split('@')[1]
       
        host_dict['name'] = host_name
        host_dict['username'] = host_string.split('@')[0]
        host_dict['password'] = env.passwords[host_string]
        host_dict['roles'] = []

        if CONTROLLER_TYPE == 'Openstack' and host_string in env.roledefs['openstack']:
            role_dict = {'type': 'openstack', 'params': {'cfgm': cfgm_host_name}}
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['cfgm']:
            role_dict = {'type': 'cfgm', 'params': {'collector': host_name, 'cassandra': ' '.join(cassandra_host_names)}}
            if CONTROLLER_TYPE == 'Openstack':
                role_dict['openstack'] = openstack_host_name
            host_dict['roles'].append(role_dict)

        if host_string in env.roledefs['control']:
            role_dict = {'type': 'bgp', 'params': {'collector': cfgm_host_name, 'cfgm': cfgm_host_name}}
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
    # for every host_string

    with settings(host_string = cfgm_host):
        
        repo_dir_name = env.test_repo_dir.split('/')[-1]
        repo_path= get_remote_path(env.test_repo_dir)

        # generate json file and copy to cfgm
        sanity_testbed_json = json.dumps(sanity_testbed_dict)

        mail_to = env.get('mail_to', '')
        log_scenario = env.get('log_scenario', 'Sanity')
        if CONTROLLER_TYPE == 'Cloudstack': 
            stack_password= 'password'
            stack_tenant= 'default-project'
        else:
            stack_password = env.get('openstack_admin_password', 'contrail123')
            stack_tenant= 'admin'

        #get the ext router information from the testbed file and set it the
        # ini inputs.
        ext_bgp_names = ''
        ext_bgp_ips = ''
        router_asn = getattr(testbed, 'router_asn','0')
        public_vn_rtgt = getattr(testbed, 'public_vn_rtgt','0')
        public_vn_subnet = getattr(testbed, 'public_vn_subnet',None)
        ext_routers = getattr(testbed, 'ext_routers', [])
        mail_server = '10.204.216.49'
        mail_port = '25'
        if 'mail_server' in env.keys():
            mail_server = env.mail_server
            mail_port = env.mail_port
        
        for ext_bgp in ext_routers:
            ext_bgp_names = ext_bgp_names + '%s_router_name=%s\n' % (ext_bgp[0], ext_bgp[0])
            ext_bgp_ips = ext_bgp_ips + '%s_router_ip=%s\n' % (ext_bgp[0], ext_bgp[1])

        sanity_params = sanity_ini_templ.safe_substitute(
            {'__timestamp__': dt.now().strftime('%Y-%m-%d-%H:%M:%S'),
             '__multi_tenancy__': get_mt_enable(),
             '__mail_to__': mail_to,
             '__log_scenario__': log_scenario,
             '__test_revision__': revision,
             '__fab_revision__': fab_revision,
             '__stack_password__': stack_password,
             '__stack_tenant__': stack_tenant,
             '__ext_router_names__': ext_bgp_names,
             '__ext_router_ips__': ext_bgp_ips,
             '__router_asn__': router_asn,
             '__public_vn_rtgt__': public_vn_rtgt,
             '__public_vn_subnet__': public_vn_subnet,
             '__mail_server__': mail_server,
             '__mail_port__': mail_port,
             '__test_repo__': get_remote_path(env.test_repo_dir),
            })
        
        fd, fname = tempfile.mkstemp()
        of = os.fdopen(fd, 'w')
        of.write(sanity_testbed_json)
        of.close()
        put(fname, "%s/scripts/sanity_testbed.json" %(repo_path))
        local ("cp %s %s/scripts/sanity_testbed.json" %(fname, env.test_repo_dir))
        os.remove(fname)

        fd, fname = tempfile.mkstemp()
        of = os.fdopen(fd, 'w')
        of.write(sanity_params)
        of.close()
        put(fname, "%s/scripts/sanity_params.ini" %(repo_path))
        local ("cp %s %s/scripts/sanity_params.ini" %(fname, env.test_repo_dir))
        os.remove(fname)
        if CONTROLLER_TYPE == 'Cloudstack':
            with settings(warn_only = True):
                run('yum --disablerepo=base,extras,updates -y install python-extras python-testtools python-fixtures python-pycrypto python-ssh fabric')
        else:
            with settings(warn_only = True):
                run("source /opt/contrail/api-venv/bin/activate && pip install fixtures testtools testresources")

#end setup_test_env

def get_remote_path(path):
    user_home = os.path.expanduser('~')
    remote_dir = "~/%s" % path.replace(user_home,'')
    return remote_dir

def get_module(suite):
    module = os.path.splitext(os.path.basename(suite))[0]
    pkg = os.path.dirname(suite.split('/scripts/')[-1:][0]).replace('/', '.')
    if pkg:
        module = '%s.%s' % (pkg, module)
    else:
        module = module
    return module

def get_testcases(suites):
    """Retuns the list of testcases in the specified unittest module."""
    tests = []
    classfinder = re.compile(r"^class\s+(.*)\(\s*.*", re.MULTILINE)
    testfinder = re.compile(r"^\s+def\s+(test_.*)\(\s*", re.MULTILINE)
    for suite in suites:
        module = get_module(suite)
        with open(suite, 'r') as suite:
            data = suite.readlines()
        for line in data:
            classmatch = classfinder.search(line)
            if classmatch:
                testclass = classmatch.group(1)
                continue
            testmatch = testfinder.search(line)
            if testmatch:
                test = testmatch.group(1)
                tests.append('%s.%s.%s' % (module.strip(), testclass.strip(), test.strip()))
    return tests

@roles('build')
@task
def run_sanity(feature='sanity', test=None):
    repo = env.test_repo_dir
    env_vars = "PARAMS_FILE=sanity_params.ini PYTHONPATH='../fixtures'"
    suites = {'svc_firewall' : ['%s/scripts/servicechain/firewall/sanity.py' % repo,
                                '%s/scripts/servicechain/firewall/regression.py' % repo],
              'floating_ip'  : ['%s/scripts/floating_ip_tests.py' % repo],
              'mx'           : ['%s/scripts/mx_test.py' % repo],
              'policy'       : ['%s/scripts/NewPolicyTests.py' % repo,
                                '%s/scripts/policyTrafficTests.py' % repo,
                                '%s/scripts/policy_api_test.py' % repo,
                                '%s/scripts/sdn_tests.py' % repo,
                                '%s/scripts/NewPolicyTestsBase.py' % repo],
              'analytics'    : ['%s/scripts/analytics_tests_with_setup.py' % repo],
              'basic_vn_vm'  : ['%s/scripts/vm_vn_tests.py' % repo],
              'svc_mirror'   : ['%s/scripts/servicechain/mirror/sanity.py' % repo,
                                '%s/scripts/servicechain/mirror/regression.py' % repo],
              'vpc'          : ['%s/scripts/vpc/sanity.py' % repo],
              'sec_group'    : ['%s/scripts/securitygroup/sanity.py' % repo],
              'multi_tenancy': ['%s/scripts/test_perms.py' % repo],
              'vdns'         : ['%s/scripts/vdns/vdns_tests.py' % repo],
              'discovery'    : ['%s/scripts/discovery_tests_with_setup.py' % repo],
              'analytics_scale' : ['%s/scripts/analytics_scale_tests_with_setup.py' % repo],
              'performance'  : ['%s/scripts/performance/sanity.py' % repo],
              'multitenancy'  : ['%s/scripts/test_perms.py' % repo],
              'ecmp'            : ['%s/scripts/ecmp/sanity_with_setup.py' %repo],
              'evpn'            : ['%s/scripts/evpn/evpn_tests.py' %repo],
              }

    pre_cmd = 'source /opt/contrail/api-venv/bin/activate && '
    cmd = pre_cmd + '%s python -m testtools.run ' % (env_vars)
    cmds = {'sanity'       : pre_cmd + '%s python sanity_tests_with_setup.py' % (env_vars),
            'quick_sanity' : pre_cmd + '%s python quick_sanity_suite.py' % (env_vars),
            'regression'   : pre_cmd + '%s python regression_tests.py' % (env_vars),
             }
    if CONTROLLER_TYPE == 'Cloudstack':
        env_vars = "PARAMS_FILE=sanity_params.ini PYTHONPATH='../fixtures:.:./cloudstack:/opt/contrail/cloudstack'"
        cmds = {'sanity'   : pre_cmd + '%s python cloudstack/cs_sanity_suite.py' % (env_vars)
               }

    if (feature != 'help' and
        feature not in suites.keys() + cmds.keys()):
        print "ERROR: Unsuported feature '%s'" % feature
        feature = 'help'

    if feature == 'help':
        print "Usage: fab run_sanity[<:feature>[,list]|[,<testcase>]]"
        print "       fab run_sanity[:%s]" % ' | :'.join(suites.keys() + cmds.keys())
        print "\n<:feature> is Optional; Default's to <:sanity>"
        print "<:feature><,list> Lists the testcase in the specified <feature> as below,"
        print "\tmod1.class1.test1"
        print "\tmod1.class2.test1"
        print "\tmod2.class1.test1"
        print "\n<:feature><,testcase> Runs the specified <testcase>"
        print "\tExample:"
        print "\tfab run_sanity:feature1,mod1.class2.test1"
        return

    if feature not in cmds.keys():
        if test == 'list':
            print "\nList of tests:\n\t" + '\n\t'.join(get_testcases(suites[feature]))
            return
        elif test:
            tests = get_testcases(suites[feature])
            if test not in tests:
                print "Test '%s' not present in %s." % (test, suites[feature])
                return
        else:
            tests = [get_module(suite) for suite in suites[feature]]
            test = ' '.join(tests)

    execute(setup_test_env)
    cfgm_host = env.roledefs['cfgm'][0]
    with settings(host_string = cfgm_host):
        with cd('%s/scripts' %(get_remote_path(env.test_repo_dir))):
            if feature in cmds.keys():
                run(cmds[feature])
                return
            run(cmd + test)

#end run_sanity
