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

class NeutronSecGroup(TempestBase):
        
    def setUp(self):
        super (NeutronSecGroup , self).setUp()
        self.tempest_path = '/opt/stack/tempest'
        
    def test_list_security_groups(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_security_groups.py:SecGroupTest.test_list_security_groups ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_create_show_delete_security_group(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_security_groups.py:SecGroupTest.test_create_show_delete_security_group ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_create_show_delete_security_group_rule(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_security_groups.py:SecGroupTest.test_create_show_delete_security_group_rule ')
                      assert(output.find( "OK") >= 0), "Test Failed"


#end TempestTest


