from fabric.operations import get, put, sudo
from fabric.api import run, env
from fabric.exceptions import CommandTimeout, NetworkError
from fabric.contrib.files import exists
from fabric.state import connections as fab_connections
from fabric.context_managers import settings, hide, cd

import re
import logging
import time

log = logging.getLogger('log01')


def remote_cmd(host_string, cmd, password=None, gateway=None,
               gateway_password=None, with_sudo=False, timeout=120,
               as_daemon=False, raw=False, cwd=None, warn_only=True):
    """ Run command on remote node through another node (gateway).
        This is useful to run commands on VMs through compute node
    Args:
        host_string: host_string on which the command to run
        password: Password
        cmd: command
        gateway: host_string of the node through which host_string will connect
        gateway_password: Password of gateway hoststring
        with_sudo: use Sudo
        timeout: timeout
        cwd: change directory to provided parameter
        as_daemon: run in background
        warn_only: run fab with warn_only
        raw: If raw is True, will return the fab _AttributeString object itself without removing any unwanted output
    """
    fab_connections.clear()
    kwargs = {}
    if as_daemon:
        cmd = 'nohup ' + cmd + ' &'
        kwargs.update({'pty': False})

    if cwd:
        cmd = 'cd %s; %s' % (cd, cmd)

    (username, host_ip) = host_string.split('@')

    if username == 'root':
        with_sudo = False

    shell = '/bin/bash -l -c'

    if username == 'cirros':
        shell = '/bin/sh -l -c'

    _run = sudo if with_sudo else run

    # with hide('everything'), settings(host_string=host_string,
    with settings(
            host_string=host_string,
            gateway=gateway,
            warn_only=warn_only,
            shell=shell,
            disable_known_hosts=True,
            abort_on_prompts=False):
        env.forward_agent = True
        gateway_hoststring = (gateway if re.match(r'\w+@[\d\.]+:\d+', gateway)
                              else gateway + ':22')
        node_hoststring = (host_string
                           if re.match(r'\w+@[\d\.]+:\d+', host_string)
                           else host_string + ':22')
        if password:
            env.passwords.update({node_hoststring: password})
            # If gateway_password is not set, guess same password
            # (if key is used, it will be tried before password)
            if not gateway_password:
                env.passwords.update({gateway_hoststring: password})

        if gateway_password:
            env.passwords.update({gateway_hoststring: gateway_password})
            if not password:
                env.passwords.update({node_hoststring: gateway_password})

        log.debug(cmd)
        tries = 1
        output = None
        while tries > 0:
            try:
                output = _run(cmd, timeout=timeout, **kwargs)
            except CommandTimeout:
                pass

            if output and 'Fatal error' in output:
                tries -= 1
                time.sleep(5)
            else:
                break
        # end while

        if not raw:
            real_output = remove_unwanted_output(output)
        else:
            real_output = output
        return real_output


def remove_unwanted_output(text):
    """ Fab output usually has content like [ x.x.x.x ] out : <content>

    Args:
        text: Text to be parsed

    """
    if not text:
        return None

    return_list = text.split('\n')

    return_list1 = []
    for line in return_list:
        line_split = line.split(' out: ')
        if len(line_split) == 2:
            return_list1.append(line_split[1])
        else:
            if ' out:' not in line:
                return_list1.append(line)
    real_output = '\n'.join(return_list1)
    return real_output
