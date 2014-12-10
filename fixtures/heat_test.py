from __future__ import print_function
import argparse
import logging
import six
import sys
from keystoneclient.v2_0 import client as ksclient
import heatclient
from heatclient import client as heat_client
from heatclient.common import utils
from heatclient import exc
from heatclient.openstack.common import strutils
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
        self.project_obj= self.vnc_lib_h.project_read(fq_name= project_fq_name)
        self.project_id = get_plain_uuid(self.project_obj.uuid)
        self.cfgm_ip = cfgm_ip
        insecure = bool(os.getenv('OS_INSECURE',True))
        self.openstack_ip = openstack_ip
        self.inputs = inputs
        self.obj = None
        self.heat_url = 'http://%s:%s/v1/%s' % (self.cfgm_ip, self.heat_port, self.project_id)
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
        self.auth_token= self.kc.auth_token
        kwargs = {
                'token': self.auth_token,
                }

        self.obj= heat_client.Client(self.heat_api_version, self.heat_url, **kwargs)
    # end setUp

    def cleanUp(self):
        super(HeatFixture, self).cleanUp()
    
    def get_handle(self):
        return self.obj
    # end get_handle

    def list_stacks(self):
        stack_list= []
        for i in self.obj.stacks.list():
            stack_list.append(i)
        return stack_list
    # end list_stacks

    def create_stack(self, stack_name, template, env):
        fields = {}
        fields = {'stack_name': stack_name, 'template': template, 'environment': env}
        stack_obj = self.obj.stacks.create(**fields)
        return stack_obj
    #end create_stack

    def delete_stack(self, stack_name):
        self.obj.stacks.delete(stack_name) 
        return True
    #end delete_stack
