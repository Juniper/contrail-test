import os
import re

from fabfile.config import *
from fabfile.utils.fabos import *
from fabfile.tasks.helpers import reboot_node
from fabfile.tasks.provision import setup_vrouter_node
from fabfile.tasks.install import create_install_repo_node, install_interface_name_node, install_vrouter_node

@task
def add_vrouter_node(*args):
    """Adds one/more new compute node to the existing cluster."""
    for host_string in args:
        with settings(host_string=host_string):
            execute("create_install_repo_node", env.host_string)
            execute("install_vrouter_node", env.host_string)
            execute("install_interface_name_node", env.host_string)
            #Clear the connections cache
            connections.clear()
            execute("upgrade_pkgs_node", env.host_string)
            execute("setup_vrouter_node", env.host_string)
            execute("reboot_node", env.host_string)


@task
def detach_vrouter_node(*args):
    """Detaches one/more compute node from the existing cluster."""
    for host_string in args:
        with settings(host_string=host_string):
            run("service supervisor-vrouter stop")
    execute("restart_control")
    execute("restart_cfgm")

@task
@roles('build')
def check_and_kill_zookeeper():
    for host_string in env.roledefs['cfgm']:
        with settings(host_string=host_string, warn_only=True):
            pkg_rls = get_release('zookeeper')
            if pkg_rls in ['3.4.3']: 
                print 'Killing existing zookeeper process'
                run('pkill -f zookeeper')
                sleep(3)
            run('ps -ef | grep zookeeper')

@task
@roles('cfgm')
def zoolink():
    """Creates /usr/bin/zookeeper link to /etc/zookeeper"""
    execute("zoolink_node", env.host_string)

@task
def zoolink_node(*args):
    """Creates /usr/bin/zookeeper link to /etc/zookeeper"""
    for host_string in args:
        with settings(host_string=host_string, warn_only=True):
            dirinfo = run('ls -lrt /usr/etc/zookeeper')
        if not '/usr/etc/zookeeper -> /etc/zookeeper' in dirinfo:
            run('ln -s /etc/zookeeper /usr/etc/zookeeper')
            sleep(3)
            run('ls -lrt /usr/etc/zookeeper')


@task
@roles('compute')
def rmmod_vrouter():
    """Removes the vrouter kernal module."""
    execute('rmmod_vrouter_node', env.host_string)

@task
def rmmod_vrouter_node(*args):
    """Removes the vrouter kernal module in one compoute node."""
    for host_string in args:
        if getattr(testbed, 'data', None) and host_string in testbed.data.keys():
            with settings(host_string=host_string):
                run("service supervisor-vrouter stop")
                run("rmmod vrouter")
                run("insmod /lib/modules/3.8.0-29-generic/extra/net/vrouter/vrouter.ko")
                run("service supervisor-vrouter start")
        else:
            print "Managment and data interface are the same."
