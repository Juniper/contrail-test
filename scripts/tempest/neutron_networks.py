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

class NeutronNetworks(TempestBase):
        
    def setUp(self):
        super (NeutronNetworks, self).setUp()
        self.tempest_path = '/opt/stack/tempest/'
        
    def test_create_update_delete_network_subnet(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_create_update_delete_network_subnet ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_show_network(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_network ')
                  assert(output.find( "OK") >= 0), "test Passed"

    def test_list_networks(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_list_networks ')
                  assert(output.find( "OK") >= 0)
 
    def test_list_subnets(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_list_subnets ')
   		  assert(output.find( "OK") >= 0)

    def test_show_subnet(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_list_subnets ')
                  assert(output.find( "OK") >= 0) , "Test Passed" 


    def test_create_update_delete_port(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_create_update_delete_port ')
                  assert(output.find( "OK") >= 0) 

    def test_show_port(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_port ')
                  assert(output.find( "OK") >= 0) 

    def test_list_ports(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_port ')
                  assert(output.find( "OK") >= 0)
    
    def test_show_non_existent_network(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_non_existent_network ')
		  assert(output.find( "OK") >= 0) 

    def test_show_non_existent_subnet(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_non_existent_subnet ')
   		  assert(output.find( "OK") >= 0) 

    def test_show_non_existent_port(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_networks.py:NetworksTestJSON.test_show_non_existent_port ')
                  assert(output.find( "OK") >= 0) 

    def test_tempest_neutron_security_group(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                  output = run(' nosetests -vxs tempest.api.network.test_security_groups.py:SecGroupTest.test_list_security_groups ')
	          assert(output.find( "OK") >= 0)	
   
#end TempestTest


