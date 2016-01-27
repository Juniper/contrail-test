# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#

import fixtures
import testtools
import unittest

from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from mock_generator import MockGeneratorFixture


class AnalyticsScaleTest(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(AnalyticsScaleTest, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj
        self.ops_inspect = self.connections.ops_inspect
    # end setUp

    def cleanUp(self):
        super(AnalyticsScaleTest, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_generator_scale(self, num_generators=10,
                             num_instances_per_generator=10, num_networks=50,
                             num_flows_per_instance=10):
        '''Test to validate collector scaling viz number of generators
        '''
        mock_gen_fixture = self.useFixture(
            MockGeneratorFixture(connections=self.connections,
                                 inputs=self.inputs, num_generators=num_generators,
                                 num_instances_per_generator=num_instances_per_generator,
                                 num_networks=num_networks,
                                 num_flows_per_instance=num_flows_per_instance))
        return True
    # end test_generator_scale

# end class AnalyticsScaleTest
