__all__ = ['install_packages', 'install_cloudstack_packages','install_contrail_packages','setup_cloud', 'install_vm_template',
           'provision_routing', 'provision_all', 'run_sanity', 'enable_proxyvm_console_access', 'cloudstack_api_setup']

from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, \
    execute, local, lcd, hide
from fabric.state import output, connections
from fabric.operations import get, put

import json
import random
import tempfile
from urllib import urlencode, quote
import urllib2
from time import sleep
import sys
import subprocess
import re

from common import *

# Don't add any new testbeds here. Create new files under fabfile/testbeds
# and copy/link the testbed.py file from/to the one you want to use.
#
# Note that fabfile/testbeds/testbed.py MUST NOT be added to the repository.
import testbeds.testbed as testbed

INSTALLER_DIR = '/opt/contrail/contrail_installer'
UTILS_DIR = '/opt/contrail/utils'
BUG_DIR = '/volume/labcores/contrail/bugs'
env.disable_known_hosts=True

def print_hello():
    print "hello world"

def host_string_to_ip(host_string):
    return host_string.split('@')[1]

def render_controller_config(cfg):
    out = cfg['cloud']
    out['nfs_share_path'] = cfg['nfs_share_path']
    out['controller_ip'] = host_string_to_ip(env.roledefs['control'][0])
    return out


def try_login(host, username, password):
    try:
        data = urlencode([('command', 'login'), ('username', username),
                        ('password', password), ('response', 'json')])
        request = urllib2.Request('http://' + host + ':8080/client/api', data,
                                  {'Content-Type': 'application/x-www-form-urlencoded',
                                   'Accept': 'application/json'})
        out = urllib2.urlopen(request)
        if not out.read(1):
            return False
        if out.getcode() is not 200:
            return False

    except Exception as e:
        #print 'Connection to Cloudstack API error: %s' % e
        return False

    return True


def wait_for_cloudstack_management_up(host, username, password):
    timeout = 0
    while timeout <= 90:
        if try_login(host, username, password):
            return True
        sleep(10)
        timeout += 1
        if timeout == 30:
            run('cloudstack-setup-management')
    print 'Timeout while waiting for cloudstack-management to start up'
    sys.exit(1)

def check_cs_version_in_config():
    if 'cs_version' in env:
        print "found cs-version\n"
    else:
        print "cs-versiion doesnt exist\n"
        env.cs_version = '4.2.0'
#end get_cs_version_from_config

@roles('control', 'cfgm')
@task
def add_contrail_repo():
    txt = '[Contrail]\n' + \
        'name=Contrail\n' + \
        'baseurl=http://%s/cloudstack/repo\n' % (env.config['yum_repo_host']) + \
        'enabled=1\n' + \
        'gpgcheck=0\n' + \
        '\n' + \
        '[ContrailCache]\n' + \
        'name=ContrailCache\n' + \
        'baseurl=http://%s/cloudstack/cache\n' % (env.config['yum_repo_host']) + \
        'enabled=1\n' + \
        'gpgcheck=0'
    with tempfile.NamedTemporaryFile() as f:
        f.write(txt)
        f.flush()
        put(f, '/etc/yum.repos.d/Contrail.repo')

def install_packages():
    execute(install_cloudstack_packages)
    execute(install_contrail_packages)


@roles('control')
@task
def install_cloudstack_packages():
    execute(add_contrail_repo)
    run('yum install --disablerepo=base,updates -y contrail-cloudstack-utils')
    check_cs_version_in_config()
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    run('sh /opt/contrail/cloudstack-utils/cloudstack-install.sh %s %s %s %s %s %s' %
(env.config['nfs_share_path'], env.config['yum_repo_host'], env.host, env.cs_version, cfgm_ip, 8082))

@roles('cfgm')
@task
def install_contrail_packages():
    execute(add_contrail_repo)
    run('yum install --disablerepo=base,updates -y contrail-cloudstack-utils')
    run('sh /opt/contrail/cloudstack-utils/contrail-install.sh %s' %
(env.config['yum_repo_host']))

    # Over-write the api-conf file with listen addr as 0.0.0.0
    run("sed -i '/listen_ip_addr/c\listen_ip_addr=0.0.0.0' /etc/contrail/api_server.conf")
    # analytics venv instalation
    with cd("/opt/contrail/analytics-venv/archive"):
        run("source ../bin/activate && pip install *")

    # api venv instalation
    with cd("/opt/contrail/api-venv/archive"):
        run("source ../bin/activate && pip install *")
    #Reboot and wait for sometime for the box to come up
    reboot(180)
 

@roles('cfgm')
@task
def setup_cloud():
    # Create config file on remote host
    with tempfile.NamedTemporaryFile() as f:
        cfg = render_controller_config(env.config)
        json.dump(cfg, f)
        f.flush()
        put(f.name, '~/config.json')
    if env.cs_version == '4.3.0':
        run('python /opt/contrail/cloudstack-utils/system-setup.py ~/config.json ' +
            '~/system-setup.log 4.3')
    else :
        run('python /opt/contrail/cloudstack-utils/system-setup.py ~/config.json ' +
            '~/system-setup.log 4.2')

@roles('control')
@task
def cloudstack_api_setup():
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    run('cat <<EOF > /usr/share/cloudstack-management/webapps/client/WEB-INF/classes/contrail.properties '+ 
'\napi.hostname=%s\napi.port=8082\nEOF' %cfgm_ip) 

@roles('control')
@task
def install_vm_template(url, name, osname):
    options = ' -t "%s" -n "%s" ' % (url, name)
    if osname:
        options += ' -o "%s"' % (osname)
    # TODO: parametrise mysql login/password/database
    options += ' -u cloud -p cloud -d cloud'
    options += ' -s "%s" -i "%s" -v "%s"' % (env.config['nfs_share_path'], env.host, env.cs_version)
    run('sh /opt/contrail/cloudstack-utils/vm-template-install.sh' + options)

@roles('cfgm')
@task
def provision_routing():
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    run('python /opt/contrail/cloudstack-utils/provision_routing.py ' +
        '%s 127.0.0.1 %s %s' % (cfgm_ip, env.config['route_target'],env.config['mx_ip']))

@roles('control')
@task
def provision_all():
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    execute(install_cloudstack_packages)
    #Induce some sleep here to wait till CS finishes DB upgrade 
    sleep(120)
    wait_for_cloudstack_management_up(env.host, env.config['cloud']['username'],
                                      env.config['cloud']['password'])
    #Issue a reboot to cleanup and restart CS 
    reboot(180)
    execute(install_contrail_packages)
    # Need to ensure connectivity between CS and API, so restart
    run('/etc/init.d/cloudstack-management restart')
    wait_for_cloudstack_management_up(env.host, env.config['cloud']['username'],
                                      env.config['cloud']['password'])
    execute(setup_cloud)
    wait_for_cloudstack_management_up(env.host, env.config['cloud']['username'],
                                      env.config['cloud']['password'])
    execute(install_vm_template, env.config['vm_template_url'],
            env.config['vm_template_name'], 'CentOS 5.6 (32-bit)')
    execute(install_vm_template, env.config['vsrx_template_url'],
            env.config['vsrx_template_name'], 'Other (32-bit)')
    execute(provision_routing)
    execute(check_systemvms)
    execute(enable_proxyvm_console_access)

@roles('compute')
@task
def enable_proxyvm_console_access():
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    run('cd /opt/contrail/xenserver-scripts/ && sh ./xen-console-proxy-vm-setup.sh %s' %controller_ip)

@roles('cfgm')
@task
def check_systemvms():
    interval = 30
    file = "/tmp/tmp%d.cookie" %random.randint(100, 1000)
    run('touch %s' %file)
    response = cloudLogin(file)
    if not response:
        assert False, "Authentication failed"
    keypair = getKeys(response, file)
    if not keypair:
        assert False, "Unable to fetch apikey and secret key"
    (apikey, secretkey) = keypair
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    run('cloudmonkey set color false')
    run('sed -i "/host/c\host=%s" ~/.cloudmonkey/config' %controller_ip)
    run('sed -i "s/secretkey\s*\=.*$/secretkey \= %s/" ~/.cloudmonkey/config' %secretkey)
    run('sed -i "s/apikey\s*\=.*$/apikey \= %s/" ~/.cloudmonkey/config' %apikey)

    for retry in range (30):
        output = run('cloudmonkey listSystemVms')
        state = re.findall(r'state = Running', output, re.M|re.I)
        if state and len(state) == 2:
            print "Both the System Vms are up and running"
            break
        else:
            if (retry < 29):
                print "System VMs are not up. Sleeping for %d secs before retry" %interval
                sleep(interval)

    run('cloudmonkey set color true')
    if retry == 29:
        assert False, "SystemVms are not up even after %d secs" %((retry+1)*interval)

def cloudLogin(file):
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    login = ("'command=login&username=" + env.config['cloud']['username'] + "&password=" + env.config['cloud']['password'] +
             "&response=json'")
    cmd = "curl -H 'Content-Type: application/x-www-form-urlencoded' -H 'Accept: application/json' -X POST -d %s -c '%s' http://%s:8080/client/api" %(login, file, controller_ip)
    output = run(cmd)
    response = json.loads(output)
    if not response or response.get('errorresponse'):
        if response:
            print response['errorresponse']['errortext']
        return None
    return response['loginresponse']

def getKeys(loginresp, file):
    urlParam = '&response=json&id=' + loginresp['userid'] + '&sessionkey=' + encodeURIComponent(loginresp['sessionkey'])
    controller_ip = host_string_to_ip(env.roledefs['control'][0])
    cmd = "curl -H 'Content-Type: application/json' -b %s -X POST 'http://%s:8080/client/api/?command=listUsers%s'" %(file, controller_ip, urlParam)
    output = run(cmd)
    response = json.loads(output)
    user = response['listusersresponse']['user'][0]
    if not 'apikey' in user:
        return None
    return user['apikey'], user['secretkey']

def encodeURIComponent(str):
    return quote(str, safe='~()*!.\'')

@roles('control')
@task
def setup_vmtemplate():
    execute(install_vm_template, env.config['vm_template_url'],
    env.config['vm_template_name'], 'CentOS 5.6 (32-bit)')
    execute(install_vm_template, env.config['vsrx_template_url'],
    env.config['vsrx_template_name'], 'Other (32-bit)')

@roles('build')
@task
def run_sanity(feature='sanity', test=None):
    repo = env.test_repo_dir
    env_vars = "PARAMS_FILE=sanity_params.ini PYTHONPATH='../fixtures'"
    suites = {
              'basic_vn_vm'  : ['%s/scripts/vm_vn_tests.py' % repo],
              'vpc'          : ['%s/scripts/vpc/sanity.py' % repo],
              }

    env_vars = "PARAMS_FILE=sanity_params.ini PYTHONPATH='../fixtures:.:./cloudstack:/opt/contrail/cloudstack-utils'"
    cmds = {'sanity'   : '%s python cloudstack/cs_sanity_suite.py' % (env_vars)
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

    from tasks.tester import *
    execute(setup_test_env)
    #cfgm_host = env.roledefs['cfgm'][0]
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    with settings(host_string = cfgm_ip):
        with cd('%s/scripts' %(get_remote_path(env.test_repo_dir))):
            if feature in cmds.keys():
                run(cmds[feature])
                return
            run(cmd + test)

#end run_sanity

