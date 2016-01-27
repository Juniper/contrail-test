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
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
try:
    from heat_test import *
    from base import BaseHeatTest

    class TestHeatBasic(BaseHeatTest, ECMPTraffic, ECMPVerify):

        @classmethod
        def setUpClass(cls):
            super(TestHeatBasic, cls).setUpClass()

        @classmethod
        def tearDownClass(cls):
            super(TestHeatBasic, cls).tearDownClass()

        @test.attr(type=['sanity', 'ci_sanity'])
        @preposttest_wrapper
        def test_heat_stacks_list(self):
            '''
            Validate installation of heat
            This issues a command to list all the heat-stacks
            '''
            stacks_list = []
            self.stacks = self.useFixture(
                HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                            project_fq_name=self.inputs.project_fq_name, inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
            stacks_list = self.stacks.list_stacks()
            self.logger.info(
                'The following are the stacks currently : %s' % stacks_list)
        # end test_heat_stacks_list
except ImportError:
        print 'Missing Heat Client. Will skip tests'
