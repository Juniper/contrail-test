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
from heat_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
import time
from base import BaseHeatTest
import test
from tcutils.util import *
from netaddr import IPNetwork, IPAddress


class TestHeat(BaseHeatTest):

    @classmethod
    def setUpClass(cls):
        super(TestHeat, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestHeat, cls).tearDownClass()

    @test.attr(type=['sanity', 'ci_sanity'])
    @preposttest_wrapper
    def test_heat_stacks_list(self):
        '''
        Validate installation of heat
        This issues a command to list all the heat-stacks
        '''
        stacks_list= []
        self.stacks = self.get_stack_obj()
        stacks_list= self.stacks.list_stacks()
        self.logger.info('The following are the stacks currently : %s'%stacks_list)
    # end test_heat_stacks_list

    @preposttest_wrapper
    def test_vn_creation_with_heat(self):
        '''
        Validate creation of VN using heat
        '''
        stack_name= 'right_net'
        stacks_list= []
        self.stacks = self.get_stack_obj()
        template = self.get_template(template_name= 'right_net_template')
        env = self.get_env(env_name= 'right_net_env') 
        right_net = self.stacks.create_stack(stack_name, template, env) 
        time.sleep(5)
        stacks_list= self.stacks.list_stacks()
#        right_net_id= 'right_net_id'
#        self.verify_vn(stacks_list, right_net_id)
        for i in stacks_list:
            self.logger.info('Stack %s created and is in %s state'%(i.stack_name, i.stack_status))
        self.stacks.delete_stack(stack_name)
    # end test_heat_stacks_list

# end TestHeat   
