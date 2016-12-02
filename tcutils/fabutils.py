from fabric.operations import get, put, sudo, local
from fabric.api import run, env
from fabric.exceptions import CommandTimeout, NetworkError
from fabric.contrib.files import exists
from fabric.state import connections as fab_connections
from fabric.context_managers import settings, hide, cd

import re
from common import log_orig as contrail_logging
import time
import os
import tempfile



def remote_cmd(host_string, cmd, password=None, gateway=None,
               gateway_password=None, with_sudo=False, timeout=120,
               as_daemon=False, raw=False, cwd=None, warn_only=True, tries=1,
               pidfile=None, logger=None, abort_on_prompts=True):
    """ Run command on remote node.
    remote_cmd method to be used to run command on any remote nodes - whether it
    is a remote server or VM or between VMs. This method has capability to
    handle:

    1. run remote command on remote server from test node
    2. Run remote command on node-a through node-b from the test node
      * in this case node-a is the target node, node-b is gateway, and the
    nodes will be connect from testnode
      * This is to avoid situation to login to remote node (node-b in this
        case) and run script (fab script or pexpect or any such code) on
        that remote node (node-b) against running command on target node
        (node-a)
    3. Run remote command on VM thorugh compute node - Same usecase as of #2
    4. Run remote commands between VMs - say copy a file from vm1 to vm2
    through compute node of vm1.
      * This will use ssh-agent forward to avoid copying ssh private keys to
        subsequent servers - Previously we used to copy ssh private keys to
        compute node and then copy the same file to vm1 in order to be able
        to connect from vm1 to vm2.
      * The commands will be running sitting on the test node then run an
      * "ssh/scp" command on vm1 through compute node of vm1 with
        agent_forward on
      * in this case flow is like this: test_node ->
        compute_of_vm1(gateway - passthrough) -> vm1 (run ssh/scp there) ->
        vm2 (final command is run)

    Args:
        tries: Number of retries in case of failure
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
        pidfile : When run in background, use pidfile to store the pid of the 
                  running process
        abort_on_prompts : Run command with abort_on_prompts set to True
                           Note that this SystemExit does get caught and 
                           counted against `tries`
    """
    if not logger:
        logger = contrail_logging.getLogger(__name__)
    logger.debug('Running remote_cmd, Cmd : %s, host_string: %s, password: %s'
        'gateway: %s, gateway password: %s' %(cmd, host_string, password, 
            gateway, gateway_password))
    fab_connections.clear()
    if as_daemon:
        cmd = 'nohup ' + cmd + ' & '
        if pidfile:
            cmd = '%s echo $! > %s' % (cmd, pidfile)

    if cwd:
        cmd = 'cd %s; %s' % (cwd, cmd)

    (username, host_ip) = host_string.split('@')

    if username == 'root':
        with_sudo = False

    shell = '/bin/bash -l -c'

    if username == 'cirros':
        shell = '/bin/sh -l -c'

    _run = sudo if with_sudo else run

    # with hide('everything'), settings(host_string=host_string,
    with hide('everything'), settings(
            host_string=host_string,
            gateway=gateway,
            warn_only=warn_only,
            shell=shell,
            disable_known_hosts=True,
            abort_on_prompts=abort_on_prompts):
        update_env_passwords(host_string, password, gateway, gateway_password)

        logger.debug(cmd)
        output = None
        while tries > 0:
            try:
                output = _run(cmd, timeout=timeout, pty=not as_daemon)
            except (CommandTimeout, NetworkError, SystemExit) as e:
                logger.exception('Unable to run command %s: %s' % (cmd, str(e)))
                tries -= 1
                time.sleep(5)
                continue

            if output and 'Fatal error' in output:
                tries -= 1
                time.sleep(5)
            else:
                break
        # end while

        if raw:
            real_output = output
        else:
            real_output = remove_unwanted_output(output)

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


def remote_copy(src, dest, src_password=None, src_gw=None, src_gw_password=None,
                dest_password=None, dest_gw=None, dest_gw_password=None,
                with_sudo=False, warn_only=True):
    """ Copy files/folders to remote server or VM (in case of VM,
        copy will happen through gateway node - i.e compute node)

    Args:
        src: source can be remote or local
                in case of remote node, it should be in the form of
                    node1:/tmp/source_directory
                in case of local node, it can be just a file/directory path
                    /tmp/source_file
        dest: Can be remote or local
                in case of remote node, it should be in the form of
                    node1:/tmp/destination_directory
                in case of local node, it can be just a file/directory path
                    /tmp/
        src_password: source node password if required
        src_gw: host_string of the node through which source will be connecting
        src_gw_password: src_gw password if required
        dest_password: destination node password if required
        dest_gw: host_string of the node through which destination will be connecting
        dest_gw_password: src_gw password if required
        with_sudo: use Sudo
        warn_only: run fab with warn_only
    """
    fab_connections.clear()

    # dest is local file path
    if re.match(r"^[\t\s]*/", dest):
        dest_node = None
        dest_path = dest
    # dest is remote path
    elif re.match(r"^.*:", dest):
        dest = re.split(':', dest)
        dest_node = dest[0]
        dest_path = dest[1]
    else:
        raise AttributeError("Invalid destination path - %s " % dest)

    # src is local file path
    if re.match(r"^[\t\s]*/", src):
        if os.path.exists(src):
            src_node = None
            src_path = src
        else:
            raise IOError("Source not found - %s No such file or directory" % src)
    # src is remote path
    elif re.match(r"^.*:", src):
        src = re.split(':', src)
        src_node = src[0]
        src_path = src[1]
    else:
        raise AttributeError("Invalid source path - %s" % src)

    if src_node:
        # Source is remote
        with settings(host_string=src_node, gateway=src_gw,
                      warn_only=warn_only, disable_known_hosts=True,
                      abort_on_prompts=False):
            update_env_passwords(src_node, src_password, src_gw, src_gw_password)
            try:
                if exists(src_path, use_sudo=with_sudo):
                    if dest_node:
                        # Both source and destination are remote
                        local_dest = tempfile.mkdtemp()
                        get(src_path, local_dest, use_sudo=True)
                        src_path = os.path.join(local_dest, os.listdir(local_dest)[0])
                    else:
                        # Source is remote and destination is local
                        # Copied to destination
                        get(src_path, dest_path, use_sudo=True)
                        return True
                else:
                    raise IOError("Source not found - %s No such file or directory" % src)
            except NetworkError:
                pass

    if dest_node:
        # Source is either local or remote
        with settings(host_string=dest_node, gateway=dest_gw,
                      warn_only=warn_only, disable_known_hosts=True,
                      abort_on_prompts=False):
            update_env_passwords(dest_node, dest_password, dest_gw, dest_gw_password)
            try:
                put(src_path, dest_path, use_sudo=True)
                return True
            except NetworkError:
                pass
    else:
        # Both are local
        local("cp -r %s %s" % (src_path, dest_path))
        return True


def update_env_passwords(host, password=None, gateway=None, gateway_password=None):
    """ Update env_passwords for the hosts provided
    Args:
        host: host string
        password: password
        gateway: gateway host string
        gateway_password: gateway password
    """
    env.forward_agent = True
    gateway_hoststring = "fake_gateway"
    if gateway:
        gateway_hoststring = (gateway if re.match(r'\w+@[\d\.]+:\d+', gateway)
                              else gateway + ':22')
    node_hoststring = (host
                       if re.match(r'\w+@[\d\.]+:\d+', host)
                       else host + ':22')
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
