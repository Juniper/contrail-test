"""Config module that is use to share data acreoss other modules in the
fabric-utils package.
"""
import sys
import datetime
from netaddr import *
from time import sleep, strftime

from fabric.api import *
from fabric.state import output, connections
from fabric.operations import get, put
from fabric.exceptions import CommandTimeout

# Don't add any new testbeds here. Create new files under fabfile/testbeds
# and copy/link the testbed.py file from/to the one you want to use.
#
# Note that fabfile/testbeds/testbed.py MUST NOT be added to the repository.
import testbeds.testbed as testbed

class Logger(object):
    def __init__(self, filename="fabric.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def isatty(self):
        return self.terminal.isatty() 

    def flush(self):
        self.terminal.flush()
        self.log.flush()

class StdErrLogger(Logger):
    def __init__(self, filename="fabric.log"):
        super(StdErrLogger, self).__init__(filename)
        self.terminal = sys.stderr


fabtasks = [fabtask.split(':')[0] for fabtask in env.tasks]
ts = datetime.datetime.now().strftime("%Y_%m_%H_%M_%S_%f")
sys.stdout = Logger('_'.join(fabtasks) + '_' + ts + '.log')
sys.stderr = StdErrLogger('_'.join(fabtasks) + '_' + ts + '.log')


INSTALLER_DIR = '/opt/contrail/contrail_installer'
UTILS_DIR = '/opt/contrail/utils'
BUG_DIR = '/volume/labcores/contrail/bugs'
RPMS_DIR = '/root/rpms'
env.disable_known_hosts=True

CONTROLLER_TYPE = 'Openstack'
# Import cloudstack functions for appropriate testbeds
if hasattr(testbed, 'controller_type'):
    if testbed.controller_type == 'Cloudstack':
        import cloudstack
        CONTROLLER_TYPE = testbed.controller_type

# Import xenserver functions for appropriate testbeds
if hasattr(testbed, 'controller_type'):
    if testbed.hypervisor_type == 'XenServer':
        import xenserver

# Choose the right decorator(parallel/serial) for execution
EXECUTE_TASK = serial
if hasattr(testbed, 'do_parallel'):
    if testbed.do_parallel:
        EXECUTE_TASK = parallel(pool_size=20)
