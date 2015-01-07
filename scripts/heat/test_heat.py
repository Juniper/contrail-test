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
try:
    from heat_test import *
    from base import BaseHeatTest

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
            stacks_list = []
            self.stacks = self.useFixture(
                HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                            project_fq_name=self.inputs.project_fq_name, inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
            stacks_list = self.stacks.list_stacks()
            self.logger.info(
                'The following are the stacks currently : %s' % stacks_list)
        # end test_heat_stacks_list

        @test.attr(type=['sanity'])
        @preposttest_wrapper
        def test_svc_creation_with_heat(self):
            '''
            Validate creation of a in-network-nat service chain using heat
            '''
            vn_list = []
            right_net_fix = self.config_vn(stack_name='right_net')
            left_net_fix = self.config_vn(stack_name='left_net')
            vn_list = [left_net_fix, right_net_fix]
            end_vms = []
            end_vms = self.config_end_vms(vn_list)
            svc_template = self.config_svc_template(stack_name='svc_template')
            st_fq_name = ':'.join(svc_template.st_fq_name)
            st_obj = svc_template.st_obj
            svc_instance = self.config_svc_instance(
                'svc_instance', st_fq_name, st_obj, vn_list)
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_chain = self.config_svc_chain(si_fq_name, vn_list)
            end_vms[0].ping_with_certainty(end_vms[1].vm_ip, expectation=True)
        # end test_svc_creation_with_heat

    # end TestHeat

except ImportError:
    print 'Missing Heat Client. Will skip tests'
