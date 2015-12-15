"""Module to launch any local command."""

import copy
import os
import signal
import tempfile
from subprocess import Popen


class Command(object):

    def __init__(self, cmd, env = None):
        self.cmd = cmd
        self.stdout = None
        self.stderr = None
        self.fstdout = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix='CMD_OUT_')
        self.fstderr = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix='CMD_ERR_')
        self.env = copy.deepcopy(os.environ)
        if not env:
            self.env.update({i.split('=')[0]:i.split('=')[1] for i in e.split()})

    def start(self):
        """Launches a local command as background process."""
        try:
            self.execprocess = Popen(self.cmd.split(),
                                     stdout=self.fstdout,
                                     stderr=self.fstderr,
                                     env=self.env,
                                     shell=False)
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
