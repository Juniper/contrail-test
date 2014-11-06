# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import copy
import fixtures
import testtools
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from vna_introspect_utils import *
import ParamTests
from topo_helper import topology_helper
import policy_test_utils
from tcutils.wrappers import preposttest_wrapper
from sdn_topo_setup import *
import test


class NewPolicyTestsBase(ParamTests.ParametrizedTestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(NewPolicyTestsBase, self).setUp()
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
        self.analytics_obj = self.connections.analytics_obj
        self.agent_inspect = self.connections.agent_inspect
    # end setUpClass

    def cleanUp(self):
        super(NewPolicyTestsBase, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    def assertEqual(self, a, b, error_msg):
        assert (a == b), error_msg

    def verify(self, policy_fixt, topo, state):
        ''' Verify & assert on fail'''
        self.logger.info("Starting Verifications after %s" % (state))
        ret = policy_fixt.verify_policy_in_vna(topo)
        # expect return to be empty for Pass, or dict for Fail
        result_msg = "Verification result after " + state + ":" + str(ret)
        self.logger.info(result_msg)
        self.assertEqual(ret['result'], True, ret['msg'])
        self.logger.info("-" * 40)
    # end verify

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_policy(self):
        """ Configure policies based on topology and run policy related verifications.
        1. Create 4 virtual-networks
        2. Create multiple policy with different options and attach to networks
        3. Launch virtual-machines in virtual-network created
        4. Verify below items:
           For each vn present in compute [vn has vm in compute]
            -whats the expected policy list for the vn
            -derive expected system rules for vn in vna
            -get actual system rules for vn in vna
            -compare  
        """
        result = True
        topology_class_name = None
        #
        # Get config for test from topology
        import sdn_basic_topology
        topology_class_name = eval("self.topology")
        if not topology_class_name:
            topology_class_name = sdn_basic_topology.sdn_basic_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name(project=self.inputs.stack_tenant,
                                   username=self.inputs.stack_user,
                                   password=self.inputs.stack_password)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo, config_topo = out['data']
        #
        # Verify [and assert on fail] after setup
        # Calling system policy verification, pick any policy fixture to
        # access fixture verification
        policy_name = topo.policy_list[0]
        self.verify(config_topo['policy'][policy_name], topo, 'setup')
        return True
    # end test_policy
