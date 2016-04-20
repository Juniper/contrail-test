# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time
import sys
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
import time
import test
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
import base
from base import BaseHeatTest
from heatlibs import heat_client
from openstack import OpenstackAuth

VERSION = 1
cwd = os.getcwd()
TEMPLATE_DIR = '%s/heat_templates/' % cwd


class TestHeatCli(BaseHeatTest):

    @classmethod
    def setUpClass(cls):
        super(TestHeatCli, cls).setUpClass()
        cls.auth = OpenstackAuth(cls.inputs.stack_user,
                                 cls.inputs.stack_password,
                                 cls.inputs.project_name, cls.inputs, cls.logger)
        cls.auth_token = cls.auth.keystone.keystone.auth_token
        cls.tenant_id = cls.auth.get_project_id()
        cls.tenant_name = cls.auth.project
        cls.auth_url = cls.auth.auth_url
        cls.heat_url = cls.auth.keystone.get_endpoint('orchestration')[0]
        cls.heat_client = heat_client.HeatClient(
            cls.heat_url, token=cls.auth_token)
        cls.heat_client = cls.heat_client.get_client()
        cls.heat_cli = heat_client.HeatCli(
            cls.heat_client, cls.inputs, cls.auth_token, cls.auth_url)

    @classmethod
    def tearDownClass(cls):
        super(TestHeatCli, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_heat_stacks_create(self):
        '''
        Validate heat stack create
        '''
        template_file = 'cirros.yaml'
        template = TEMPLATE_DIR + template_file
        self.heat_cli.create_stack(self.tenant_name,
                                   template=template,
                                   stack_name=get_random_name("test_stack-"))
        self.verify_all_vms_in_stack(
            self.heat_client, self.heat_cli.stack_name)
        self.heat_cli.delete_stack(self.tenant_name, self.heat_cli.id)
    # end test_heat_stacks_create

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_heat_stacks_created_vms_ping(self):
        '''
        Validate ping between vms
        '''
        template_file = 'cirros.yaml'
        template = TEMPLATE_DIR + template_file
        self.heat_cli.create_stack(self.tenant_name,
                                   template=template,
                                   stack_name=get_random_name("test_stack-"))
        vms = base.get_vm_uuid(self.heat_client, self.heat_cli.stack_name)
        vm_obj_list = []
        for elem in vms:
            for uuid in elem.values():
                vm_obj_list.append(self.get_vm_by_id(uuid, image='cirros'))
        assert self.ping_between_vms(vm_obj_list)
        self.heat_cli.delete_stack(self.tenant_name, self.heat_cli.id)
    # end test_heat_stacks_create
