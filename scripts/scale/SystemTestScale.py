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
from contrail_test_init import *
from connections import ContrailConnections
from policy_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
import system_verification
from project_setup import *
from vna_introspect_utils import *

class SystemTestScale( fixtures.TestWithFixtures):

    def setUp(self):
        super(SystemTestScale, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.logger = self.inputs.logger
    # end setUpClass

    def cleanUp(self):
        super(SystemTestScale, self).cleanUp()
    # end cleanUp

    @preposttest_wrapper
    def test_system_scale(self):
        """ Configure policies based on topology and run policy related verifications.
        """
        result = True
        topology_class_name = None
        num_of_projects=2
        num_of_comp_nodes=len(self.inputs.compute_ips)
        max_vm_per_compute=10
        num_vm_per_compute=max_vm_per_compute/num_of_projects

        project_topo={}
        #
        # Get config for test from topology
        import sdn_topo_gen
        for i in range(num_of_projects) :
            if i == (num_of_projects-1):
               project_name='admin'
            else:
               project_name='project' + str(i)
            project_topo[project_name]=sdn_topo_gen.basic_topo(num_vm_per_compute,num_of_comp_nodes,project=project_name)          
            topo = project_topo[project_name]
            #
            # Test setup: Configure policy, VN, & VM
            # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
            # Returned topo is of following format:
            # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
            out = self.useFixture(
              ProjectSetupFixture(self.connections, topo))
            self.assertEqual(out.result, True, out.err_msg)
            if out.result == True:
               topo, config_topo = out.data
            #
            # Verify [and assert on fail] after setup
            # Calling system policy verification, pick any policy fixture to
            # access fixture verification
            policy_name = topo.policy_list[0]
            system_verification.verify(self,config_topo['policy'][policy_name], topo, 'setup')
        return True
    # end test_policy
