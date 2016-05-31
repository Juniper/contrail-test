import os
import sys
import argparse
from common.openstack_libs import ks_auth_identity_v2 as v2
from common.openstack_libs import ks_session as session
from common.openstack_libs import heat_client as client
from common.structure import DynamicArgs
from common.openstack_libs import ks_client as ksclient
import functools
from tcutils.util import *

VERSION = 1
cwd = os.getcwd()
#TEMPLATE_DIR = '%s/heat_templates/' % cwd
TEMPLATE_DIR = '/root/heat_templates/'

task_message = {
    'create': 'CREATE_COMPLETE',
    'update': 'UPDATE_COMPLETE'
}

def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

def get_stack_id(heat_client, stack_name):
    try:
        for stack_obj in heat_client.stacks.list():
            if stack_obj.stack_name == stack_name:
                uuid = stack_obj.id
        return uuid
    except Exception as e:
        return None


def get_stack_outputs(heat_client, stack_name):
    try:
        return heat_client.stacks.get(stack_name).outputs
    except Exception as e:
        return None


def get_vm_uuid(heat_client, stack_name):
    outputs = get_stack_outputs(heat_client, stack_name)
    elements = []
    try:
        for el in outputs:
            vm_dict = {}
            vm_dict[el['output_value']['name']] = el['output_value']['id']
            elements.append(vm_dict)
    except Exception as e:
        pass
    finally:
        return elements

def get_element_from_stack_output(heat_client, stack_name, element):
    outputs = get_stack_outputs(heat_client, stack_name)
    elements = []
    try:
        for el in outputs:
            if el['output_key'] == element:
                elements.append(el['output_value'])
    except Exception as e:
        pass
    finally:
        return elements

class AuthToken(DynamicArgs):

    """Returns auth_token
    :Parameters:
      - `username`: user_id
      - `tenant_id`: tenant_id
      - `password`: password
      - `auth_url`: auth url
    """

    _fields = ['auth_url', 'username', 'password', 'tenant_id', 'tenant_name']

    def get_token(self):
        '''Return auth token'''
        auth = v2.Password(auth_url=self.auth_url, username=self.username,
                           password=self.password,
                           tenant_id=self.tenant_id,
                           tenant_name=self.tenant_name)

        self.sess = session.Session(auth=auth, verify=False)
        self.token = auth.get_token(self.sess)
        return self.token


class HeatClient(DynamicArgs):

    """Returns heat clent  
    :Parameters:
      - `heat_url`: heat_url
      - `auth_token`: auth_token
    """
    _fields = ['heat_url']

    def get_client(self):
        self.client = client.Client(VERSION, self.heat_url,
                                    token=self.token)
        return self.client


def command(**kwargs):
    cmd = ""
    if 'template' in kwargs:
        cmd = cmd + " -f " + kwargs['template']
    if 'env_file' in kwargs:
        cmd = cmd + ' -e ' + kwargs['env_file']
    if 'stack_name' in kwargs:
        cmd = cmd + ' ' + kwargs['stack_name']
    if 'parameters' in kwargs:
        cmd = cmd + ' -c ' + kwargs['parameters']
    return cmd


class HeatCli:

    def __init__(self, heat_client, inputs, token, auth_url, **kwargs):
        self.heat_client = heat_client
        self.inputs = inputs
        self.logger = self.inputs.logger
        self.token = token
        self.auth_url = auth_url
        self.openstack_node_user = self.inputs.host_data[
            self.inputs.openstack_ip]['username']
        self.openstack_node_password = self.inputs.host_data[
            self.inputs.openstack_ip]['password']

    def execute_command(self, cmd):
        output = self.inputs.run_cmd_on_server(self.inputs.openstack_ip, cmd,
                                               self.openstack_node_user,
                                               self.openstack_node_password)

    def create_stack(self, project, **kwargs):
        cmd = command(**kwargs)
        cmd = 'heat --os-project-name ' + project + ' --os-auth-token ' + self.token + \
            ' --os-auth-url ' + self.auth_url + ' stack-create ' + cmd
        self.execute_command(cmd)
        self.stack_name = kwargs['stack_name']
        if not self.wait_for_task('create', self.heat_client, self.stack_name):
            self.logger.error("Stack create failed..")
            print 'Stack create FAILED'
        self.id = get_stack_id(self.heat_client, self.stack_name)
        self.outputs = get_stack_outputs(
            self.heat_client, self.stack_name)
        print 'Stack create SUCCESS'

    def delete_stack(self, project, stack_id, **kwargs):
        cmd = 'heat -d --os-project-name ' + project + ' --os-auth-token ' + self.token + \
            ' --os-auth-url ' + self.auth_url + ' stack-delete ' + stack_id
        self.execute_command(cmd)
        if not self.wait_for_delete(self.heat_client, stack_id):
            print 'Stack delete FAILED'
        else:
            print 'Stack delete SUCCESS'
             

    def update_stack(self):
        pass

    def list_stack(self):
        pass

    @retry(delay=5, tries=30)
    def wait_for_delete(self, heat_client, stack_name):
        result = False
        for stack_obj in self.heat_client.stacks.list():
            if stack_obj.stack_name == stack_name:
                self.logger.debug("Stack not yet deleted...waiting")
                return False
            else:
                continue
        self.logger.info("Stack  deleted.")
        return True

    @retry(delay=5, tries=30)
    def wait_for_task(self, func, heat_client, stack_name):
        result = False
        for stack_obj in self.heat_client.stacks.list():
            if stack_obj.stack_name == stack_name:
                if stack_obj.stack_status == task_message[func]:
                    self.logger.info(
                        'Stack %s %s successful.' % (func, stack_obj.stack_name))
                    return True
                else:
                    self.logger.info('Stack %s is in %s state. Retrying....' % (
                    stack_obj.stack_name, stack_obj.stack_status))
        return False
    # end wait_for_task

class Inputs(object):
    def __init__(self,openstack_ip,username,password):
        import logging
        from fabric.api import env, run, local
        from fabric.operations import get, put, reboot
        from fabric.context_managers import settings, hide
        from fabric.exceptions import NetworkError
        from fabric.contrib.files import exists
        self.logger = logging.getLogger(__name__)
        self.openstack_ip = openstack_ip
        self.host_data = dict()
        nested_set(self.host_data,[self.openstack_ip,'username'],username) 
        nested_set(self.host_data,[self.openstack_ip,'password'],password) 

    def run_cmd_on_server(self, server_ip, issue_cmd, username=None,
                          password=None, pty=True):
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, server_ip), password=password,
                    warn_only=True, abort_on_prompts=False):
                output = run('%s' % (issue_cmd), pty=pty)
                return output
    # end run_cmd_on_server


def _parse_args( args_str):
    parser = argparse.ArgumentParser()
    args, remaining_argv = parser.parse_known_args(args_str.split())
    parser.add_argument(
                "--auth_url", nargs='?', default="check_string_for_empty",help="Auth Url",required=True)
    parser.add_argument(
                "--heat_url", nargs='?', default="check_string_for_empty",help="heat Url",required=True)
    parser.add_argument(
                "--username", nargs='?', default="admin",help="User name",required=True)
    parser.add_argument(
                "--password", nargs='?', default="contrail123",help="password",required=True)
    parser.add_argument(
                "--tenant_name", nargs='?', default="admin",help="Project name",required=True)
    parser.add_argument(
                "--tenant_id", help="Tenant id",required=True)
    parser.add_argument(
                "--openstack_ip",  help="openstack ip",required=True)
    parser.add_argument(
                "--openstack_server_user", default='root', help="openstack server username")
    parser.add_argument(
                "--openstack_server_password", default='c0ntrail123', help="openstack server password")
    parser.add_argument(
                "--stack_name", default='test', help="stack name to used while creating/deleting stack")
    parser.add_argument(
                "--operation", default='create', help="Operation is create/delete stack")
    parser.add_argument(
                "--template",  help="template to create stack",required=True)
    args = parser.parse_args(remaining_argv)
    return args

def main(args_str = None):
    if not args_str:
       script_args = ' '.join(sys.argv[1:])
    script_args = _parse_args(script_args)

    auth_url = os.getenv('OS_AUTH_URL') or \
        script_args.auth_url
    username = os.getenv('OS_USERNAME') or \
        script_args.username
    password = os.getenv('OS_PASSWORD') or \
        script_args.password
    tenant_name = os.getenv('OS_TENANT_NAME') or \
        script_args.tenant_name
    tenant_id = script_args.tenant_id
    heat_url = os.getenv('OS_ORCHESTRATION_URL') or \
        script_args.heat_url+'/'+ tenant_id
    openstack_ip = script_args.openstack_ip
    auth = AuthToken(auth_url, username,
                     password,
                     tenant_id,
                     tenant_name)
    token = auth.get_token()
    heat_client = HeatClient(heat_url, token=token)
    heat_client = heat_client.get_client()
    inputs = Inputs(openstack_ip,script_args.openstack_server_user,script_args.openstack_server_password)
    heat_cli = HeatCli( heat_client, inputs, token, auth_url)
    template = "%s/%s" % (TEMPLATE_DIR, script_args.template)

    if (script_args.operation == 'create'):
        heat_cli.create_stack(tenant_name, stack_name=script_args.stack_name, template=template)
   
    if (script_args.operation == 'delete'):
        heat_cli.delete_stack(tenant_name, script_args.stack_name)


#Ussage:
#python fixtures/heatlibs/heat_client.py --auth_url http://10.204.217.12:5000/v2.0 --heat_url http://10.204.217.12:8004/v1 --username root --password contrail123 --tenant_name admin --tenant_id 3135dbf3ac344a3aa57fbf02ba5dfdfa --openstack_ip 10.204.217.12 --openstack_server_user root --openstack_server_password c0ntrail123 --stack_name non_test --operation create --template cirrus.yaml
if __name__ == "__main__":
    main()
