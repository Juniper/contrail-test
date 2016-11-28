""" Module to check and collect information about cores during the test."""

import sys
import traceback
import unittest
import random
from time import sleep
from functools import wraps

from fabric.api import run, cd
from fabric.contrib.files import exists
from fabric.context_managers import settings, hide
from paramiko.ssh_exception import ChannelException

from tcutils.util import retry

CORE_DIR = '/var/crashes'


class TestFailed(Exception):
    pass

def get_cores(inputs):
    '''Get the list of cores in all the nodes in the test setup
    '''
    cores = {}
    for host in inputs.host_ips:
        username = inputs.host_data[host]['username']
        password = inputs.host_data[host]['password']
        core = get_cores_node(host, username, password)
        if core:
            cores.update({host: core.split()}) 
    # end for
    return cores
        

def get_cores_node(node_ip, user, password):
    """Get the list of cores in one of the nodes in the test setup.
    """
    core = None
    with hide('everything'):
        try:
            with settings(
                host_string='%s@%s' % (user, node_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                if exists(CORE_DIR):
                    with cd(CORE_DIR):
                        (ret_val, core) = run("ls core.* 2>/dev/null")
        except Exception:
            pass
    return core


def find_new(initials, finals):
    """Finds if new cores/crashes in any of the nodes in test setup.
    """
    new = {}
    for node, final in finals.items():
        if node in initials.keys():
            initial = initials[node]
            diff = list(set(final).difference(set(initial)))
            if not diff:
                continue
            new.update({node: diff})
        else:
            new.update({node: final})

    return new

def get_service_crashes(inputs):
    """Get the list of services crashed in all of the nodes in the test setup.
    """
    crashes = {}
    for node_ip in inputs.host_ips:
        username = inputs.host_data[node_ip]['username']
        password = inputs.host_data[node_ip]['password']
        service_crash = get_service_crashes_node(node_ip, username, password)
        if service_crash:
            crashes.update({node_ip: service_crash})
    return crashes
                 

@retry(tries=10, delay=3)
def _run(cmd):
    try:
        output = run(cmd)
    except ChannelException, e:
        # Handle too many concurrent sessions
        if 'Administratively prohibited' in str(e):
            sleep(random.randint(1,5))
            return (False, None)
    return (True, output)
# end _run

def get_service_crashes_node(node_ip, user, password):
    """Get the list of services crashed in one of the nodes in the test setup.
    """
    crash = None
    services = []
    with hide('everything'):
        with settings(
            host_string='%s@%s' % (user, node_ip), password=password,
                warn_only=True, abort_on_prompts=False):
            (ret_val, crash) = _run("contrail-status")
    if crash and "Failed service list" in crash:
        for line in crash.split("\n"):
            if "Failed service list" in line:
                # dont iterate beyond this to look for service: status
                break
            status = None
            service_status = line.split(":")
            service = service_status[0]
            if len(service_status) == 2:
                status = service_status[1].strip()
            if (status == "inactive" or
                    status == "failed"):
                services.append(service)

    return services
# end get_service_crashes_node
