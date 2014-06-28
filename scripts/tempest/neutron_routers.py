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

from tempest_base import *
from contrail_test_init import *
from connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper

import shlex,subprocess
from subprocess import PIPE    
from fabric.api import run, cd
from time import sleep

class NeutronRouters(TempestBase):
        
    def setUp(self):
        super (NeutronRouters , self).setUp(*args, **kwargs)
        self.tempest_path = '/opt/stack/tempest/' 
    def test_create_show_list_update_delete_router(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.test_routers.py:RoutersTest.test_create_show_list_update_delete_router')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_add_remove_router_interface_with_subnet_id(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.test_routers.py:RoutersTest.test_add_remove_router_interface_with_subnet_id')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_add_remove_router_interface_with_port_id(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.test_routers.py:RoutersTest.test_add_remove_router_interface_with_port_id')
                      assert(output.find( "OK") >= 0), "Test Failed"
