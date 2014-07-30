import os

import fixtures
from testresources import TestResource

from smgr_common import SmgrFixture
#from connections import ContrailConnections
#from contrail_test_init import ContrailTestInit


class SmgrSetup(fixtures.Fixture):

    """Common resources required for the smgr test suite.
    """

    def __init__(self, common_resource):
        super(SmgrSetup, self).__init__()
        self.common_resource = common_resource

    def setUp(self):
        super(SmgrSetup, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        #self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        #self.connections = ContrailConnections(self.inputs)
        #self.logger = self.inputs.logger

        #self.logger.info("Configuring setup for smgr tests.")
        self.setup()
        #self.logger.info("Verifying setup of smgr tests.")
        #self.verify()
        #self.logger.info(
        #    "Finished configuring setup for smgr tests.")
        return self

    def setup(self):
        """Config common resources."""
        self.smgr_fixture = self.useFixture(SmgrFixture(
            testbed_py="./testbed.py", smgr_config_ini="./smgr_input.ini",
              test_local=False))

        #self.logger.info("Adding Server  to smgr DB")
        self.smgr_fixture.svrmgr_add_all()

    def verify(self):
        """verfiy common resources."""
        #self.logger.debug("Verify the configured roles")
        #assert self.smgr_fixture.verify_roles()
        pass

    def tearDown(self):
        #self.logger.info("Tearing down resources of smgr tests")
        super(SmgrSetup, self).cleanUp()



class _SmgrSetupResource(TestResource):

    def make(self, dependencyresource):
        base_setup = SmgrSetup(self)
        base_setup.setUp()
        return base_setup

    def clean(self, base_setup):
        #base_setup.logger.info(
        #    "Cleaning up smgr test resources here")
        print "Cleaning up smgr test resources here"
        base_setup.tearDown()

SmgrSetupResource = _SmgrSetupResource()
