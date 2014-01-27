#!/usr/bin/env python
import os
import os.path

from fabfile.config import *
from fabfile.utils.fabos import detect_ostype
from fabfile.tasks.install import yum_install
from fabfile.tasks.helpers import is_reimage_complete

@task
@roles('build')
def bringup_test_node(build):
    id = build
    cfgm = env.roledefs['cfgm'][0]

    #reimage
    if os.path.isfile(build):
        fname = os.path.basename(build)
        name, type = os.path.splitext(fname)
        if type == '.iso':
            execute('all_reimage', build)
            id = build.split('-')[1]
        else:
            execute('install_pkg_all', build)
            id = build.split('-')[-1].split('.')[0]
    else:
        execute('all_reimage', '@%s' %build)
        if 'ubuntu' in env.ostypes[cfgm]:
            path = os.path.join('/cs-shared/builder/ubuntu/', build)
            debfile = fnmatch.filter(os.listdir(path), 'contrail-install-packages*.deb')
            execute('install_pkg_all', debfile)
    execute('is_reimage_complete', int(id))

    #install contrail
    with settings(host_string=env.roledefs['cfgm'][0]):
        with cd('/opt/contrail/contrail_packages/'):
            run('./setup.sh')
            pass
        put('fabfile/testbeds/testbed.py', '/opt/contrail/utils/fabfile/testbeds/testbed.py')
        with cd('/opt/contrail/utils/'):
            run('pwd')
            run('fab install_contrail:False')
    execute('compute_reboot')
    connections.clear()

    # setup interface
    with cd('/opt/contrail/utils/'):
        run('fab setup_interface')

    # setup all
    with settings(host_string=env.roledefs['cfgm'][0]):
        with cd('/opt/contrail/utils/'):
            run('fab setup_all:False')
            run('pwd')
    execute('compute_reboot')
    connections.clear()
