"""
This package implements a set of `fabric <http://www.fabfile.org>` tasks to 
provision a Juniper VNS openstack cluster. These tasks can be used after the
cluster is imaged to launch role specific services. To perform this a testbed
specification file has be provided (for eg. `like this <testbeds/testbed_multibox_example.py>`
and `this <testbeds/testbed_singlebox_example.py>`).

This package contains tasks and utils pacakges.
	tasks : Package containing various fab tasks in specific modules.
	utils : Package containing common api's used by the tasks package..
"""

# Config module at fabfile/config.py to import testbed file and hold global
# vars that are shared across various modules in tasks and utisl packages. 
from  config import *

# Fabric tasks
from tasks.tester import *
from tasks.install import *
from tasks.syslogs import *
from tasks.helpers import *
from tasks.provision import *
from tasks.upgrade import *
from tasks.services import *
from tasks.misc import *
from tasks.rabbitmq import *

# For contrail use
try:
    from contraillabs.setup import *
except ImportError:
    pass
