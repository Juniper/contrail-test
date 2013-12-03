__all__ = ['reimage', 'setup', 'reimage_and_setup']

from fabric.api import *
from common import *
import socket
import tempfile


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


@roles('compute')
@task
def install_packages():
    execute(add_contrail_repo)
    run('yum clean all')
    run('yum install --disablerepo=citrix -y contrail-*')


@roles('compute')
@task
def reimage():
    host = get_host_name(env.host)
    local('/cs-shared/cf/bin/xen.reimage %s' % host)
    print 'Waiting for reimage to finish...'
    wait_until_host_down()
    reconnect(1500)


@roles('compute')
@task
def setup():
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

