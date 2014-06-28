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

class NeutronCLI(TempestBase):
   
   def setUp(self):
        super(NeutronCLI,self).setUp()
        self.tempest_path = '/opt/stack/tempest'

   def test_neutron_fake_action(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             
             with cd(self.tempest_path):
                      output = run ('pwd')    
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_fake_action ')
                      assert(output.find( "OK") >= 0), "Test Failed"


   def test_neutron_net_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_net_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_ext_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_ext_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_dhcp_agent_list_hosting_net(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_dhcp_agent_list_hosting_net ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_agent_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_agent_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_meter_label_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_meter_label_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_meter_label_rule_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_meter_label_rule_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_floatingip_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_floatingip_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_net_external_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_net_external_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_port_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_port_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_quota_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_quota_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"
	
   def test_neutron_router_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_router_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_security_group_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_security_group_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_security_group_rule_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_security_group_rule_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def test_neutron_subnet_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_subnet_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def  test_neutron_help(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_help ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def  test_neutron_version(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_version ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def  test_neutron_debug_net_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_debug_net_list ')
                      assert(output.find( "OK") >= 0), "Test Failed"

   def  test_neutron_quiet_net_list(self):
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
                          warn_only=True, abort_on_prompts= False ):
             with cd(self.tempest_path):
                      output = run(' nosetests -vxs tempest.cli.simple_read_only.test_neutron.py:SimpleReadOnlyNeutronClientTest.test_neutron_quiet_net_list')
                      assert(output.find( "OK") >= 0), "Test Failed"
