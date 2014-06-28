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

from contrail_test_init import *
from connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper

import shlex,subprocess
from subprocess import PIPE    
from fabric.api import run, cd
from time import sleep
import shutil

class TempestBase(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(TempestBase,self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
 
        self.inputs=self.useFixture(ContrailTestInit( self.ini_file))
        self.connections= ContrailConnections(self.inputs)
        self.logger= self.inputs.logger

        self.tempest_sample_path = '/opt/stack/tempest/etc/tempest.conf.sample'
        self.tempest_cnf_path = '/opt/stack/tempest/etc/tempest.conf'

        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.compute_ips[0]), password=self.inputs.password,
            warn_only=True, abort_on_prompts= False ):

            shutil.copy2(self.tempest_sample_path, self.tempest_cnf_path)
            s= open (self.tempest_cnf_path).read()
            s= s.replace('neutron = false' , 'neutron = True')
            s= s.replace('cli_dir = /usr/local/bin' , 'cli_dir = /usr/bin')
            s= s.replace('admin_password = secret' , 'admin_password = contrail123')
            f= open (self.tempest_cnf_path, 'w')        
            f.write (s)
            f.close() 
            output = run('source /etc/contrail/openstackrc; keystone user-password-update  --pass secret demo')

    def cleanUp(self):
        super(TempestBase, self).cleanUp()
