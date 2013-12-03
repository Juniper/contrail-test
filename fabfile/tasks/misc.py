import os
import re

from fabfile.config import *
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
    execute("restart_config")
