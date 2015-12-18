import fixtures
import testtools
import os
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from testresources import OptimisingTestSuite, TestResource


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
        self.inputs = ContrailTestInit(self.ini_file)
        self.connections = ContrailConnections(self.inputs)
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.setup_common_objects()
        return self
    # end setUp

    def setup_common_objects(self):

        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            self.inputs.project_name)
        self.project_fixture.set_sec_group_for_allow_all(
            self.inputs.project_name, 'default')

        # Formin the VGW VN dict for further test use
        self.vgw_vn_list = {}
        for key in self.inputs.vgw_data[0]:
            for vgw in self.inputs.vgw_data[0][key]:
                self.vgw_vn_list[self.inputs.vgw_data[0][key][vgw]['vn']] = {}
                self.vgw_vn_list[self.inputs.vgw_data[0][key][vgw]['vn']][
                    'subnet'] = self.inputs.vgw_data[0][key][vgw]['ipam-subnets']
                self.vgw_vn_list[self.inputs.vgw_data[0]
                                 [key][vgw]['vn']]['host'] = key
                if self.inputs.vgw_data[0][key][vgw].has_key('gateway-routes'):
                    self.vgw_vn_list[self.inputs.vgw_data[0][key][vgw]['vn']][
                        'route'] = self.inputs.vgw_data[0][key][vgw]['gateway-routes']

        # Creating VN
        self.vn_fixture_dict = []
        i = 0
        for key in self.vgw_vn_list:
            self.vn_fixture_dict.append(
                self.useFixture(
                    VNFixture(
                        project_name=self.inputs.project_name, connections=self.connections,
                        inputs=self.inputs, vn_name=key.split(":")[3], subnets=self.vgw_vn_list[key]['subnet'], clean_up=False)))

        self.vn_fixture_private = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections, inputs=self.inputs, vn_name='VN-Private', subnets=['10.10.10.0/24']))

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
