from tcutils.util import *
from common import log_orig as contrail_logging
from common.openstack_libs import heat_client
from tcutils.util import get_plain_uuid, get_dashed_uuid
import fixtures
import openstack

class HeatFixture(fixtures.Fixture):
    '''
       Wrapper around heat client library
       Optional params:
       :param connections: ContrailConnections object
       :param auth_h: OpenstackAuth object
       :param inputs: ContrailTestInit object which has test env details
       :param logger: logger object
       :param auth_url: Identity service endpoint for authorization.
       :param username: Username for authentication.
       :param password: Password for authentication.
       :param project_name: Tenant name for tenant scoping.
       :param region_name: Region name of the endpoints.
       :param certfile: Public certificate file
       :param keyfile: Private Key file
       :param cacert: CA certificate file
       :param verify: Enable or Disable ssl cert verification
    '''
    def __init__(self, connections=None, auth_h=None, **kwargs):
        self.heat_api_version = '1'
        self.logger = kwargs.get('logger') or connections.logger if connections \
                      else contrail_logging.getLogger(__name__)
        auth_h = auth_h or connections.auth if connections else None
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth = auth_h
        self.obj = None
        self.certfile = kwargs.get('certfile') or auth_h.keystone_certfile
        self.cacert = kwargs.get('cacert') or auth_h.certbundle
        self.keyfile = kwargs.get('keyfile') or auth_h.keystone_keyfile
        self.insecure = kwargs.get('insecure') or auth_h.insecure
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def setUp(self):
        super(HeatFixture, self).setUp()
        self.heat_url = self.auth.get_endpoint('orchestration')
        self.auth_token = self.auth.get_token()
        kwargs = {
            'token': self.auth_token,
            'ca_file': self.cacert,
            'cert_file': self.certfile,
            'key_file': self.keyfile,
            'insecure': self.insecure,
        }
        self.obj = heat_client.Client(
            self.heat_api_version, self.heat_url, **kwargs)
    # end setUp

    def cleanUp(self):
        super(HeatFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    # end get_handle

    def list_stacks(self):
        stack_list = []
        for i in self.obj.stacks.list():
            stack_list.append(i)
        return stack_list
    # end list_stacks


class HeatStackFixture(fixtures.Fixture):

    def __init__(
            self,
            connections,
            stack_name,
            template=None,
            env=None):
        self.connections = connections
        self.stack_name = stack_name
        self.template = template
        self.logger = self.connections.logger
        self.env = env
        self.already_present = False
#   end __init__

    def setUp(self):
        super(HeatStackFixture, self).setUp()
        fields = {}
        fields = {'stack_name': self.stack_name,
                  'template': self.template, 'environment': self.env}
        self.heat_obj = self.useFixture(HeatFixture(connections=self.connections))
        self.heat_client_obj = self.heat_obj.obj
        for i in self.heat_client_obj.stacks.list():
            if i.stack_name == self.stack_name:
                self.logger.info('Stack %s exists. Not creating'%i.stack_name)
                self.already_present = True
                return i
        if self.already_present != True:
            stack_obj = self.heat_client_obj.stacks.create(**fields)
            self.logger.info('Creating Stack %s' % self.stack_name)
            self.wait_till_stack_created()
            return stack_obj
    # end create_stack

    def cleanUp(self):
        super(HeatStackFixture, self).cleanUp()
        do_cleanup = True
        self.logger.info('Deleting Stack %s' % self.stack_name)
        if self.already_present:
            do_cleanup = False    
        if do_cleanup:
            self.heat_obj = self.useFixture(HeatFixture(connections=self.connections))
            self.heat_client_obj = self.heat_obj.obj
            self.heat_client_obj.stacks.delete(self.stack_name)
            self.wait_till_stack_is_deleted()
        else:
            self.logger.info('Skipping the deletion of Stack %s' %self.stack_name)
    # end delete_stack

    def update(self, new_parameters):
        fields = {}
        fields = {'stack_name': self.stack_name,
                  'template': self.template, 'environment': {},
                  'parameters': new_parameters}
        self.heat_client_obj = self.heat_obj.obj
        for i in self.heat_client_obj.stacks.list():
            if i.stack_name == self.stack_name:
                result= True
                stack_obj = self.heat_client_obj.stacks.update(i.id, **fields)
                self.logger.info('Updating Stack %s' % self.stack_name)
                self.wait_till_stack_updated()
                return stack_obj
            else:
                result= False
        assert result, 'Stack %s not seen'%self.stack_name
    #end update

    def update_template_env(self, template, env):
        self.template = template
        self.env = env
        fields = {}
        fields = {'stack_name': self.stack_name,
                  'template': self.template, 'environment': self.env}
        self.heat_client_obj = self.heat_obj.obj
        for i in self.heat_client_obj.stacks.list():
            if i.stack_name == self.stack_name:
                result= True
                stack_obj = self.heat_client_obj.stacks.update(i.id, **fields)
                self.logger.info('Updating Stack %s' % self.stack_name)
                self.wait_till_stack_updated()
                return stack_obj
            else:
                result= False
        assert result, 'Stack %s not seen'%self.stack_name
    #end update

    @retry(delay=5, tries=15)
    def wait_till_stack_updated(self):
        result = False
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == self.stack_name:
                if stack_obj.stack_status == 'UPDATE_COMPLETE':
                    self.logger.info(
                        'Stack %s updated successfully.' % stack_obj.stack_name)
                    result = True
                    break
                elif stack_obj.stack_status == 'UPDATE_FAILED':
                    self.logger.info('Stack (%s) update failed.' % stack_obj.stack_name)
                    result = False
                    return result
                else:
                    self.logger.info('Stack %s is in %s state. Retrying....' % (
                        stack_obj.stack_name, stack_obj.stack_status))
        return result
    # end wait_till_stack_updated

    @retry(delay=5, tries=15)
    def wait_till_stack_created(self):
        result = False
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == self.stack_name:
                if stack_obj.stack_status == 'CREATE_COMPLETE':
                    self.logger.info(
                        'Stack %s created successfully.' % stack_obj.stack_name)
                    result = True
                    break
                elif stack_obj.stack_status == 'CREATE_FAILED':
                    self.logger.info('Stack %s creation failed.' % stack_obj.stack_name)
                    result = False
                    return result
                else:
                    self.logger.info('Stack %s is in %s state. Retrying....' % (
                        stack_obj.stack_name, stack_obj.stack_status))
        return result
    # end wait_till_stack_created

    @retry(delay=5, tries=15)
    def wait_till_stack_is_deleted(self):
        result = True
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == self.stack_name:
                result = False
                self.logger.info('Stack %s is in %s state. Retrying....' % (
                    stack_obj.stack_name, stack_obj.stack_status))
                break
            else:
                continue
        if result == True:
            self.logger.info('Stack %s is deleted.' % self.stack_name)
        return result
    # end wait_till_stack_is_deleted
