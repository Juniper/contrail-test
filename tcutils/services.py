""" Module to perfome command line operation in the services."""

from fabric.api import run, cd
from fabric.context_managers import settings, hide


def execute_cmd_in_node(node, user, passwd, cmd):
    with hide('everything'):
        with settings(host_string='%s@%s' % (user, node), password=password,
                      warn_only=True, abort_on_prompts=False):
            output = run(cmd)
    return output


def get_status(node, user, passwd, service):
    cmd = "service %s status" % serivce
    return execute_cmd_in_node(node, user, passwd, cmd)
