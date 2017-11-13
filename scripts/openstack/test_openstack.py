# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.util import skip_because
import test_v1
import test
from tcutils.wrappers import preposttest_wrapper

class OpenStackTestSanity(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(OpenStackTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @skip_because(orchestrator = 'vcenter')
    @test.attr(type=['cb_sanity', 'sanity', 'vcenter'])
    @preposttest_wrapper
    def test_openstack_status(self):
        ''' Test to verify that all openstack services are running and active

        '''
        if not self.connections.orch.auth_h.verify_openstack_state():
            self.logger.error("openstack-status failed")
            return False
        else:
            self.logger.info("openstack-status passed")
        return True

