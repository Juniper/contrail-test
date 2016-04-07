import os
from common.openstack_libs import ks_auth_identity_v2 as v2
from common.openstack_libs import ks_session as session
from common.openstack_libs import heat_client as client
from common.structure import DynamicArgs
from common.openstack_libs import ks_client as ksclient
import functools
from tcutils.util import *
from scripts.heat import base

VERSION = 1
cwd = os.getcwd()
TEMPLATE_DIR = '%s/heat_templates/'%cwd

task_message = {
				'create': 'CREATE_COMPLETE',
				'update': 'UPDATE_COMPLETE' 
				}

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
        auth=v2.Password(auth_url=self.auth_url
                        ,username=self.username, 
                        password=self.password, 
                        tenant_id=self.tenant_id,
                        tenant_name=self.tenant_name)

        self.sess = session.Session(auth=auth,verify=False)         
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
                                        token = self.token)
		return self.client

def command(**kwargs):
	cmd= ""
	if 'template' in kwargs:
		cmd = cmd + " -f " + kwargs['template']
	if 'env_file' in kwargs:
		cmd = cmd + ' -e '+ kwargs['env_file']
	if 'stack_name' in kwargs:
		cmd = cmd + ' ' + kwargs['stack_name']
	if 'parameters' in kwargs:
		cmd = cmd + ' -c '+ kwargs['parameters']
	return cmd

class HeatCli:

	def __init__(self,heat_client,inputs,token , auth_url, **kwargs):
		self.heat_client = heat_client
		self.inputs = inputs
		self.logger = self.inputs.logger
		self.token = token
		self.auth_url = auth_url
		self.openstack_node_user = self.inputs.host_data[self.inputs.openstack_ip]['username']
		self.openstack_node_password = self.inputs.host_data[self.inputs.openstack_ip]['password']

	def execute_command(self,cmd):
		output = self.inputs.run_cmd_on_server(self.inputs.openstack_ip, cmd,
												self.openstack_node_user,
												self.openstack_node_password)

	def create_stack(self,project,**kwargs):
		cmd = command(**kwargs)
		cmd = 'heat -d --os-project-name ' + project + ' --os-auth-token ' + self.token + \
						' --os-auth-url '+ self.auth_url+ ' stack-create ' + cmd
		self.execute_command(cmd)
		self.stack_name = kwargs['stack_name']
		if not self.wait_for_task('create',self.heat_client,self.stack_name):
			self.logger.error("Stack create failed..")
			assert False
		self.id = base.get_stack_id(self.heat_client,self.stack_name)
		self.outputs = base.get_stack_outputs(self.heat_client,self.stack_name)

	def delete_stack(self,project,stack_id,**kwargs):
		cmd = 'heat -d --os-project-name ' + project + ' --os-auth-token ' + self.token + \
						' --os-auth-url '+ self.auth_url+ ' stack-delete ' + stack_id
		self.execute_command(cmd)
		assert self.wait_for_delete(self.heat_client,self.stack_name)

	def update_stack(self):
		pass

	def list_stack(self):
		pass

	@retry(delay=5, tries=10)
	def wait_for_delete(self, heat_client,stack_name):
		result = False
		for stack_obj in self.heat_client.stacks.list():
			if stack_obj.stack_name == stack_name:
				self.logger.debug("Stack not yet deleted...waiting")
				return False
			else:
				continue
		self.logger.info("Stack  deleted.")
		return True
				

	@retry(delay=5, tries=10)
	def wait_for_task(self, func,heat_client,stack_name):
		result = False
		for stack_obj in self.heat_client.stacks.list():
			if stack_obj.stack_name == stack_name:
				if stack_obj.stack_status == task_message[func]:
					self.logger.info(
                	    'Stack %s %s successful.' % (func,stack_obj.stack_name))
					return True	
            	else:
            	    self.logger.info('Stack %s is in %s state. Retrying....' % (
            		    stack_obj.stack_name, stack_obj.stack_status))
		return False
    # end wait_for_task

def main():
	auth_url = os.getenv('OS_AUTH_URL') or \
                'http://10.204.217.12:5000/v2.0'
	username = os.getenv('OS_USERNAME') or \
                'admin'
	password = os.getenv('OS_PASSWORD') or \
                'contrail123'
	tenant_name = os.getenv('OS_TENANT_NAME') or \
                'admin'
	tenant_id = '13e6f8d8c5c84c17914cebce2ffafd84'
	heat_url = os.getenv('OS_ORCHESTRATION_URL') or \
                'http://10.204.217.12:8004/v1/%s'%(tenant_id)
	auth = AuthToken(auth_url
                        ,username,
                        password,
                        '',
                        tenant_name)
#	kc = ksclient.Client(
#            username=username,
#            password=password,
#            tenant_name=tenant_name,
#            auth_url=auth_url,
#            insecure=True)
	token = auth.get_token()
#	import pdb;pdb.set_trace()
	heat_client = HeatClient(heat_url, token = token)
	heat_client = HeatClient(heat_url, token = token)
	heat_client = heat_client.get_client()
	template = "%s/%s"%(TEMPLATE_DIR,'cirros.yaml')
	create_stack(heat_client,stack_name = 'test_stack' , template = template)

if __name__ == "__main__":
    main()           
