import os

import fixtures
from testresources import TestResource

from smgr_common import SmgrFixture
#from connections import ContrailConnections
from contrail_test_init import ContrailTestInit


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
            self.ini_file = 'sanity_params.ini'

        if 'TESTBED_FILE' in os.environ:
            self.testbed_py = os.environ.get('TESTBED_FILE')
        else:
            self.testbed_py = 'testbed.py'
       
        if 'SMGR_FILE' in os.environ:
            self.smgr_file = os.environ.get('SMGR_FILE')
        else:
            self.smgr_file = 'smgr_input.ini'
        
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        #self.connections = ContrailConnections(self.inputs)
        self.logger = self.inputs.logger

        self.logger.info("Configuring setup for smgr tests.")
        self.setup()
        self.logger.info("Verifying setup of smgr tests.")
        self.verify()
        self.logger.info(
            "Finished configuring setup for smgr tests.")
        return self

    def setup(self):
        """Config common resources."""
        self.smgr_fixture = self.useFixture(SmgrFixture(
            self.inputs, testbed_py=self.testbed_py, smgr_config_ini=self.smgr_file,
              test_local=True))

        self.logger.info("Adding Server  to smgr DB")
        self.smgr_fixture.svrmgr_add_all()

    def verify(self):
        """verfiy common resources."""
        self.logger.debug("Verify the common resources")
        #assert self.smgr_fixture.verify_roles()
        pass

    def tearDown(self):
        self.logger.info("Tearing down resources of smgr tests")
        super(SmgrSetup, self).cleanUp()



class _SmgrSetupResource(TestResource):

    def make(self, dependencyresource):
        base_setup = SmgrSetup(self)
        base_setup.setUp()
        return base_setup

    def clean(self, base_setup):
        base_setup.logger.info(
            "Cleaning up smgr test resources here")
        base_setup.tearDown()

SmgrSetupResource = _SmgrSetupResource()
