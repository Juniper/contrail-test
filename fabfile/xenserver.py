__all__ = ['reimage', 'setup', 'reimage_and_setup']

from fabric.api import *
from common import *
import socket
import tempfile
import sys

def get_host_name(ip):
    hostname, alias, ip = socket.gethostbyaddr(ip)
    return hostname.split('.')[0]


def host_string_to_ip(host_string):
    return host_string.split('@')[1]


@roles('compute')
@task
def add_contrail_repo():
    txt = '[Contrail]\n' + \
        'name=Contrail\n' + \
        'baseurl=http://%s/xen_repo\n' % (env.config['yum_repo_host']) + \
        'enabled=1\n' + \
        'gpgcheck=0\n'
    with tempfile.NamedTemporaryFile() as f:
        f.write(txt)
        f.flush()
        put(f, '/etc/yum.repos.d/Contrail.repo')

def check_xen_version():
    if not 'xen_ver' in env:
        print "ERROR: Please set xen_ver=<6.1 or 6.2> in testbed.py"
        sys.exit(1)
    elif env.xen_ver != '6.1' and env.xen_ver != '6.2':
        print "ERROR: xen_ver should be 6.1 or 6.2 in testbed.py"
        sys.exit(1)
    return
#end check_xen_version

@roles('compute')
@task
def install_packages():
    PKG = "contrail-libs-%s contrail-xen-utils-%s contrail-vrouter-%s" %(env.xen_ver, env.xen_ver, env.xen_ver) 
    execute(add_contrail_repo)
    run('yum clean all')
    #run('yum install --disablerepo=citrix -y contrail-*')
    run('yum install --disablerepo=citrix -y %s' %PKG)

@roles('compute')
@task
def reimage():
    host = get_host_name(env.host)
    check_xen_version()
    if env.xen_ver == '6.1':
        local('/cs-shared/cf/bin/xen.reimage %s' % host)
    if env.xen_ver == '6.2':
        local('/cs-shared/cf/bin/xen62.reimage %s' % host)
    print 'Waiting for reimage to finish...'
    wait_until_host_down()
    reconnect(1500)


@roles('compute')
@task
def setup():
    #check_xen_version()
    execute(install_packages)
    cfgm_ip = host_string_to_ip(env.roledefs['cfgm'][0])
    run('cd /opt/contrail/xenserver-scripts/ && sh ./contrail-setup.sh %s %s' %
        (env.config['yum_repo_host'], cfgm_ip))

    reboot(180)


@hosts('localhost')
@task
def reimage_and_setup():
    execute(reimage)
    execute(setup)

