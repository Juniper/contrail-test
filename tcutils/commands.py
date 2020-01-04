"""Module to launch any local/remote command."""

import os
import signal
import tempfile
import logging as LOG
from subprocess import Popen

import paramiko

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class Command(object):

    """Launch local command."""

    def __init__(self, cmd):
        self.cmd = cmd
        self.stdout = None
        self.stderr = None
        self.fstdout = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix='CMD_OUT_')
        self.fstderr = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix='CMD_ERR_')

    def start(self):
        """Launches a local command as background process."""
        try:
            self.execprocess = Popen([self.cmd],
                                     stdout=self.fstdout,
                                     stderr=self.fstderr,
                                     shell=True)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stops the background process and exits. 

        Return tuple of (RC, stdout, stderr)."""
        rc = self.execprocess.poll()
        if rc is None:
            # process still runs, kill it.
            os.kill(self.execprocess.pid, signal.SIGTERM)
            process_id, rc = os.waitpid(self.execprocess.pid, 0)

        with file(self.fstdout.name, 'r') as fh:
            self.stdout = fh.read()
        with file(self.fstderr.name, 'r') as fh:
            self.stderr = fh.read()

        return (rc, self.stdout, self.stderr)


def ssh(host, user, passwd, log=LOG):
    """SSH to any host.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=passwd)
    return ssh


def execute_cmd(session, cmd, log=LOG):
    """Executing long running commands in background through fabric has issues
    So implemeted this to execute the command.
    """
    log.debug("Executing command: %s" % cmd)
    stdin, stdout, stderr = session.exec_command(cmd)


def execute_cmd_out(session, cmd, log=LOG):
    """Executing long running commands in background through fabric has issues
    So implemeted this to execute the command.
    """
    log.debug("Executing command: %s" % cmd)
    stdin, stdout, stderr = session.exec_command(cmd)
    out = None
    err = None
    out = stdout.read()
    err = stderr.read()
    if out:
        log.debug("STDOUT: %s", out)
    if err:
        log.debug("STDERR: %s", err)
    return (out, err)
