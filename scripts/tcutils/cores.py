""" Module to check and collect information about cores during the test."""

import sys
import traceback
import unittest
from functools import wraps

from fabric.api import run, cd
from fabric.context_managers import settings, hide

CORE_DIR = '/var/crashes'


class TestFailed(Exception):
    pass


def get_node_ips(inputs):
    """Get the list of nodes ip address in the test setup.
    """
    node_ips = []
    nodes = ['cfgm_ips', 'bgp_ips', 'collector_ips', 'webui_ip', 'compute_ips', 'openstack_ip']
    for node in nodes:
        ip = inputs.__getattribute__(node)
        if type(ip) is str:
            ip = [ip]
        node_ips = list(set(node_ips).union(set(ip)))
    return node_ips
    
def get_cores(nodes, user, password):
    """Get the list of cores in all of the nodes in the test setup.
    """
    cores = {}
    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' % (user, node), password=password,
                          warn_only=True, abort_on_prompts= False ):
                with cd(CORE_DIR):
                    core = run("ls core.* 2>/dev/null")
                    if core:
                        cores.update({node : core.split()})
    return cores

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
            new.update({node : diff})
        else:
            new.update({node : final})

    return new
            
def get_service_crashes(nodes, user, password):
    """Get the list of services crashed in all of the nodes in the test setup.
    """
    crashes = {}
    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' % (user, node), password=password,
                          warn_only=True, abort_on_prompts= False ):
                crash = run("contrail-status")
        services = []
        if "Failed service list" in crash:
            for line in crash.split("\n"):
                if "Failed service list" in line:
                    #dont iterate beyond this to look for service: status
                    break
                status = None
                service_status = line.split(":")
                service = service_status[0]
                if len(service_status) == 2:
                    status = service_status[1].strip()
                if (status == "inactive" or 
                    status == "failed"):
                    services.append(service)
            crashes.update({node : services})
                 
    return crashes
