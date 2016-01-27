"""Helper module to start/stop traffic.
"""
import re
from time import sleep

from fabric.api import run
from fabric.operations import put
from fabric.context_managers import settings, hide
from tcutils.util import run_fab_cmd_on_node

try:
    # Running from the source repo "test".
    from tcutils.pkgs.Traffic.traffic.core.profile import *
    from tcutils.pkgs.Traffic.traffic.utils.logger import LOGGER, get_logger
    from tcutils.pkgs.Traffic.traffic.utils.globalvars import LOG_LEVEL
except ImportError:
    # Distributed and installed as package
    from traffic.core.profile import *
    from traffic.utils.logger import LOGGER, get_logger
    from traffic.utils.globalvars import LOG_LEVEL


LOGGER = "%s.core.helper" % LOGGER
LOG = get_logger(name=LOGGER, level=LOG_LEVEL)


class SSHError(Exception):
    pass


class Host(object):

    """Stores the credentials of a host.
    """

    def __init__(self, ip, user="root", password="C0ntrail123", key=None):
        self.ip = ip
        self.user = user
        self.password = password
        self.key = key


class Helper(object):

    def __init__(self, lhost, rhost, log=LOG):
        self.lhost = lhost
        self.rhost = rhost
        self.log = log

    def get_sshkey(self):
        with settings(host_string='%s@%s' % (self.lhost.user, self.lhost.ip),
                      password=self.lhost.password, warn_only=True,
                      abort_on_prompts=False):
            out = put('~/.ssh/id_rsa', '/tmp/id_rsa')
            out = run('chmod 600 /tmp/id_rsa')
            return '/tmp/id_rsa'

    def runcmd(self, cmd):
        """Run remote command."""
        output = None
#        keyfile = self.get_sshkey()
#        ssh_cmd = 'ssh -o StrictHostKeyChecking=no -i %s %s@%s \"%s\"' % (
#                  keyfile, self.rhost.user, self.rhost.ip, cmd)
        self.log.debug('On host %s exec: %s'%(self.rhost.ip, cmd))
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (self.lhost.user, self.lhost.ip),
                    password=self.lhost.password, warn_only=True, abort_on_prompts=False):
                self.log.debug("Executing: %s", cmd)
                retry = 6
                while True:
                    output = ''
#                    output=run(ssh_cmd)
                    output = run_fab_cmd_on_node(
                        host_string='%s@%s' % (self.rhost.user, self.rhost.ip),
                        password='ubuntu', as_sudo=True, cmd=cmd)
                    if (not output) and retry:
                        self.log.error(
                            "Scapy issue while sending/receiving packets. Will retry after 5 secs.")
                        sleep(5)
                        retry -= 1
                        continue
                    if ("Connection timed out" in output or
                            "Connection refused" in output) and retry:
                        self.log.debug(
                            "SSH timeout, sshd might not be up yet. will retry after 5 secs.")
                        sleep(5)
                        retry -= 1
                        continue
                    elif "Connection timed out" in output:
                        raise SSHError(output)
                    else:
                        break
        self.log.debug(output)
        return output


class Sender(Helper):

    def __init__(self, name, profile, lhost, rhost, log=LOG):
        super(Sender, self).__init__(lhost, rhost, log)
        self.name = name
        self.pktheader = profile.stream.all_fields
        # Pickle the profile object, so that it can be sent across network.
        self.profile = create(profile)
        # Initialize the packet sent/recv count
        self.sent = None
        self.recv = None

    def start(self):
        # Start send; launches the "sendpkts" script in the VM
        self.log.debug("Sender: VM '%s' in Compute '%s'",
                       self.rhost.ip, self.lhost.ip)
        self.log.info("Sending traffic with '%s'", self.pktheader)
        out = self.runcmd("sendpkts --name %s -p %s" %
                          (self.name, self.profile))
        if 'Daemon already running' in out:
            errmsg = "Traffic stream with name '%s' already present in VM '%s' \
                      at compute '%s'" % (self.name, self.rhost.ip, self.lhost.ip)
            assert False, errmsg

    def poll(self):
        """Polls for the number of packets sent/received.
           This api can be used when trraffic is live.
        """
        # Polls for the packets sent; launches the "sendpkts" script in
        # the VM with --poll option
        result = self.runcmd("sendpkts --name %s --poll" % self.name)
        sent = re.search("(Sent)=([0-9]+)", result)
        if sent:
            self.sent = int(sent.group(2))
        recv = re.search("(Received)=([0-9]+)", result)
        if recv:
            self.recv = int(recv.group(2))

    def stop(self):
        # Stop send; launches the "sendpkts" script in the VM with --stop
        # option
        result = self.runcmd("sendpkts --name %s --stop" % self.name)
        sent = re.search("(Sent)=([0-9]+)", result)
        if sent:
            self.sent = int(sent.group(2))
        recv = re.search("(Received)=([0-9]+)", result)
        if recv:
            self.recv = int(recv.group(2))
        self.log.info("Finished sending traffic with '%s'", self.pktheader)


class Receiver(Helper):

    def __init__(self, name, profile, lhost, rhost, log=LOG):
        super(Receiver, self).__init__(lhost, rhost, log)
        self.name = name
        # Pickle the profile object, so that it can be sent across network.
        self.profile = create(profile)
        # Initialize the packet recv count
        self.recv = None
        self.corrupt = None

    def start(self):
        # Start send; launches the "recvpkts" script in the VM
        self.log.debug("Receiver: VM '%s' in Compute '%s'",
                       self.rhost.ip, self.lhost.ip)
        self.runcmd("recvpkts --name %s -p %s" % (self.name, self.profile))

    def poll(self):
        """Polls for the number of packets received.
           This api can be used when traffic is live.
        """
        # Polls for packets recieve; launches the "recvpkts" script in
        # the VM with --poll option
        result = self.runcmd("recvpkts --name %s --poll" % self.name)
        recv = re.search("(Received)=([0-9]+)", result)
        if recv:
            self.recv = int(recv.group(2))
        corrupt = re.search("(Corrupted)=([0-9]+)", result)
        if corrupt:
            self.corrupt = int(corrupt.group(2))

    def stop(self):
        # Stop send; launches the "recvpkts" script in the VM with --stop
        # option
        result = self.runcmd("recvpkts --name %s --stop" % self.name)
        recv = re.search("(Received)=([0-9]+)", result)
        if recv:
            self.recv = int(recv.group(2))
        corrupt = re.search("(Corrupted)=([0-9]+)", result)
        if corrupt:
            self.corrupt = int(corrupt.group(2))
