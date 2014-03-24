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

class NeutronLB(TempestBase):
        
    def setUp(self):
        super (NeutronLB , self).setUp()
    
    def test_list_vips(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_list_vips ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_create_update_delete_pool_vip(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_create_update_delete_pool_vip ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_show_vip(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_show_vip ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_show_pool(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_show_pool ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_list_pools(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_list_pools ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_list_members(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_list_members ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_create_update_delete_member(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_create_update_delete_member ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_list_health_monitors(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_list_health_monitors ')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_create_update_delete_health_monitor(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_create_update_delete_health_monitor')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_show_health_monitor(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_show_health_monitor')
                      assert(output.find( "OK") >= 0), "Test Failed"

    def test_associate_disassociate_health_monitor_with_pool(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.api.network.test_load_balancer.py:LoadBalancerJSON.test_associate_disassociate_health_monitor_with_pool')
                      assert(output.find( "OK") >= 0), "Test Failed"

#end TempestTest


