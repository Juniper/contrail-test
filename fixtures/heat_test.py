from __future__ import print_function
from tcutils.util import *
import argparse
import logging
import six
import sys
from common.openstack_libs import ks_client as ksclient
import heatclient
from heatclient import client as heat_client
from heatclient.common import utils
from heatclient import exc
from oslo.utils import strutils
logger = logging.getLogger(__name__)
from tcutils.util import get_plain_uuid, get_dashed_uuid
import os
import fixtures
from contrail_fixtures import contrail_fix_ext


class HeatFixture(fixtures.Fixture):

    def __init__(
            self,
            connections,
            username,
            password,
            project_fq_name,
            inputs,
            cfgm_ip,
            openstack_ip):
        self.connections = connections
        httpclient = None
        self.heat_port = '8004'
        self.heat_api_version = '1'
        self.username = username
        self.password = password
        self.vnc_lib_h = self.connections.vnc_lib
        self.project_obj = self.vnc_lib_h.project_read(fq_name=project_fq_name)
        self.project_id = get_plain_uuid(self.project_obj.uuid)
        self.cfgm_ip = cfgm_ip
        insecure = bool(os.getenv('OS_INSECURE', True))
        self.openstack_ip = openstack_ip
        self.inputs = inputs
        self.openstack_ip = self.inputs.host_data[self.openstack_ip]['host_ip']
        self.obj = None
        self.heat_url = 'http://%s:%s/v1/%s' % (
            self.openstack_ip, self.heat_port, self.project_id)
        if not self.inputs.ha_setup:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://' + openstack_ip + ':5000/v2.0'
        else:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://' + openstack_ip + ':5000/v2.0'
        self.kc = ksclient.Client(
            username=self.inputs.stack_user,
            password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name,
            auth_url=self.auth_url,
            insecure=insecure)
        self.logger = self.inputs.logger
    # end __init__

    def setUp(self):
        super(HeatFixture, self).setUp()
        self.auth_token = self.kc.auth_token
        kwargs = {
            'token': self.auth_token,
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
            inputs,
            stack_name,
            project_fq_name,
            template=None,
            env=None):
        self.connections = connections
        self.vnc_lib_h = self.connections.vnc_lib
        self.project_obj = self.vnc_lib_h.project_read(fq_name=project_fq_name)
        self.project_id = get_plain_uuid(self.project_obj.uuid)
        self.inputs = inputs
        self.stack_name = stack_name
        self.template = template
        self.logger = self.inputs.logger
        self.env = env
        self.already_present = False
#   end __init__

    def setUp(self):
        super(HeatStackFixture, self).setUp()
        fields = {}
        fields = {'stack_name': self.stack_name,
                  'template': self.template, 'environment': self.env}
        self.heat_obj = self.useFixture(
            HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                        project_fq_name=self.inputs.project_fq_name, inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
        self.heat_client_obj = self.heat_obj.obj
        for i in self.heat_client_obj.stacks.list():
            if i.stack_name == self.stack_name:
                self.logger.info('Stack %s exists. Not creating'%i.stack_name)
                self.already_present = True
                return i
        if self.already_present != True:
            stack_obj = self.heat_client_obj.stacks.create(**fields)
            self.logger.info('Creating Stack %s' % self.stack_name)
            self.wait_till_stack_created(self.stack_name)
            return stack_obj
    # end create_stack

    def cleanUp(self):
        super(HeatStackFixture, self).cleanUp()
        do_cleanup = True
        self.logger.info('Deleting Stack %s' % self.stack_name)
        if self.already_present:                                                                                                                                                                                                                                             
            do_cleanup = False    
        if do_cleanup:
            self.heat_obj = self.useFixture(
            HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                        project_fq_name=self.inputs.project_fq_name, inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
            self.heat_client_obj = self.heat_obj.obj
            self.heat_client_obj.stacks.delete(self.stack_name)
            self.wait_till_stack_is_deleted(self.stack_name)
        else:
            self.logger.info('Skipping the deletion of Stack %s' %self.stack_name)
    # end delete_stack

    def update(self, stack_name, new_parameters):
        fields = {}
        fields = {'stack_name': self.stack_name,                                                                                                                                                                                                     
                  'template': self.template, 'environment': {},
                  'parameters': new_parameters}
        self.heat_client_obj = self.heat_obj.obj
        for i in self.heat_client_obj.stacks.list():
            if i.stack_name == stack_name:
                result= True
                stack_obj = self.heat_client_obj.stacks.update(i.id, **fields)
                self.logger.info('Updating Stack %s' % self.stack_name)
                self.wait_till_stack_updated(self.stack_name)
                return stack_obj
            else:
                result= False
        assert result, 'Stack %s not seen'%self.stack_name
    #end update

    @retry(delay=5, tries=10)
    def wait_till_stack_updated(self, stack_name=None):
        result = False
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == stack_name:
                if stack_obj.stack_status == 'UPDATE_COMPLETE':
                    self.logger.info(
                        'Stack %s updated successfully.' % stack_obj.stack_name)
                    result = True
                    break
                else:
                    self.logger.info('Stack %s is in %s state. Retrying....' % (
                        stack_obj.stack_name, stack_obj.stack_status))
        return result
    # end wait_till_stack_updated

    @retry(delay=5, tries=10)
    def wait_till_stack_created(self, stack_name=None):
        result = False
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == stack_name:
                if stack_obj.stack_status == 'CREATE_COMPLETE':
                    self.logger.info(
                        'Stack %s created successfully.' % stack_obj.stack_name)
                    result = True
                    break
                else:
                    self.logger.info('Stack %s is in %s state. Retrying....' % (
                        stack_obj.stack_name, stack_obj.stack_status))
        return result
    # end wait_till_stack_created

    @retry(delay=5, tries=10)
    def wait_till_stack_is_deleted(self, stack_name=None):
        result = True
        for stack_obj in self.heat_obj.list_stacks():
            if stack_obj.stack_name == stack_name:
                result = False
                self.logger.info('Stack %s is in %s state. Retrying....' % (
                    stack_obj.stack_name, stack_obj.stack_status))
                break
            else:
                continue
        if result == True:
            self.logger.info('Stack %s is deleted.' % stack_name)
        return result
    # end wait_till_stack_is_deleted
