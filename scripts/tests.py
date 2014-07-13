# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import signal
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from subprocess import Popen, PIPE
import shlex


class TestSanityFixture(testtools.TestCase, fixtures.TestWithFixtures):

#    @classmethod
    def setUp(self):
        super(TestSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.api_s_inspect = self.connections.api_server_inspect
    # end setUpClass

    def cleanUp(self):
        super(TestSanityFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

# end TestSanityFixture
