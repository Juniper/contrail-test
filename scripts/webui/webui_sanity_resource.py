import fixtures
import testtools
import os
import uuid
from connections import ContrailConnections
from contrail_test_init import *
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from testresources import OptimisingTestSuite, TestResource
import time
from sdn_topo_setup import *
from webui_topology import *


class SolnSetup(fixtures.Fixture):

    def __init__(self, test_resource):
        super(SolnSetup, self).__init__()
        self.test_resource = test_resource

    def setUp(self):
        super(SolnSetup, self).setUp()
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
        self.setup_common_objects()
        return self
    # end setUp

    def setup_common_objects(self):
        time.sleep(5)
        topo_obj = sdn_webui_config()
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo_obj))
        out = setup_obj.topo_setup(skip_verify='yes')
    # end setup_webui_objects

    def tearDown(self):
        print "Tearing down resources"
        super(SolnSetup, self).cleanUp()

    def dirtied(self):
        self.test_resource.dirtied(self)


class _SolnSetupResource(TestResource):

    def make(self, dependencyresource):
        base_setup = SolnSetup(self)
        base_setup.setUp()
        return base_setup
    # end make

    def clean(self, base_setup):
        print "Am cleaning up here"
#        super(_SolnSetupResource,self).clean()
        base_setup.tearDown()
    # end

SolnSetupResource = _SolnSetupResource()
