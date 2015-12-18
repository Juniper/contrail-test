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
from vpc_fixture_new import VPCFixture
from vpc_vn_fixture import VPCVNFixture
from vpc_vm_fixture import VPCVMFixture


class VPCTestSetup(fixtures.Fixture):

    def __init__(self, test_resource):
        super(VPCTestSetup, self).__init__()
        self.test_resource = test_resource

    def setUp(self):
        super(VPCTestSetup, self).setUp()
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
        self.vpc1_cidr = '10.2.5.0/24'
        self.vpc1_vn1_cidr = '10.2.5.0/25'
        self.vpc1_vn2_cidr = '10.2.5.128/25'
        self.vpc2_cidr = '10.2.50.0/24'
        self.vpc2_vn1_cidr = '10.2.50.0/25'
        self.vpc1_fixture = self.useFixture(VPCFixture(self.vpc1_cidr,
                                                       connections=self.connections))
#        assert self.vpc1_fixture.verify_on_setup()
        if not self.vpc1_fixture.vpc_id:
            return False 
        self.vpc2_fixture = self.useFixture(VPCFixture(self.vpc2_cidr,
                                                       connections=self.connections))
        if not self.vpc2_fixture.vpc_id:
            return False 
#        assert self.vpc2_fixture.verify_on_setup()
        self.vpc1_vn1_fixture = self.useFixture(VPCVNFixture(
            self.vpc1_fixture,
            subnet_cidr=self.vpc1_vn1_cidr,
            connections=self.connections))
#        assert self.vpc1_vn1_fixture.verify_on_setup()
        if not self.vpc1_vn1_fixture.subnet_id:
            return False 
        self.vpc1_vn2_fixture = self.useFixture(VPCVNFixture(
            self.vpc1_fixture,
            subnet_cidr=self.vpc1_vn2_cidr,
            connections=self.connections))
        if not self.vpc1_vn2_fixture.subnet_id:
            return False 
        self.vpc2_vn1_fixture = self.useFixture(VPCVNFixture(
            self.vpc2_fixture,
            subnet_cidr=self.vpc2_vn1_cidr,
            connections=self.connections))
        if not self.vpc2_vn1_fixture.subnet_id:
            return False 
#        assert self.vpc1_vn2_fixture.verify_on_setup()
        self.vpc1_vn1_vm1_fixture = self.useFixture(
            VPCVMFixture(self.vpc1_vn1_fixture,
                         image_name='ubuntu',
                         connections=self.connections))
        self.vpc1_vn1_vm2_fixture = self.useFixture(VPCVMFixture(
            self.vpc1_vn1_fixture,
            image_name='ubuntu-traffic',
            connections=self.connections))
        self.vpc1_vn2_vm1_fixture = self.useFixture(VPCVMFixture(
            self.vpc1_vn2_fixture,
            image_name='ubuntu-traffic',
            connections=self.connections))
        self.vpc2_vn1_vm1_fixture = self.useFixture(VPCVMFixture(
            self.vpc2_vn1_fixture,
            image_name='ubuntu-traffic',
            connections=self.connections))

    # end setup_common_objects

    def verify_common_objects(self):
        assert self.vpc1_fixture.verify_on_setup()
        assert self.vpc2_fixture.verify_on_setup()
        assert self.vpc1_vn1_fixture.verify_on_setup()
        assert self.vpc1_vn2_fixture.verify_on_setup()
        assert self.vpc2_vn1_fixture.verify_on_setup()
        assert self.vpc1_vn1_vm1_fixture.verify_on_setup()
        assert self.vpc1_vn1_vm2_fixture.verify_on_setup()
        assert self.vpc1_vn2_vm1_fixture.verify_on_setup()
        assert self.vpc2_vn1_vm1_fixture.verify_on_setup()
        self.vpc1_vn1_vm1_fixture.c_vm_fixture.wait_till_vm_is_up()
        self.vpc1_vn1_vm2_fixture.c_vm_fixture.wait_till_vm_is_up()
        self.vpc1_vn2_vm1_fixture.c_vm_fixture.wait_till_vm_is_up()
        self.vpc2_vn1_vm1_fixture.c_vm_fixture.wait_till_vm_is_up()
    # end verify_common_objects

    def tearDown(self):
        print "Tearing down resources"
        super(VPCTestSetup, self).cleanUp()

    def dirtied(self):
        self.test_resource.dirtied(self)


class _VPCTestSetupResource(TestResource):

    def make(self, dependencyresource):
        base_setup = VPCTestSetup(self)
        base_setup.setUp()
        return base_setup
    # end make

    def clean(self, base_setup):
        print "Am cleaning up here"
#        super(_VPCTestSetupResource,self).clean()
        base_setup.tearDown()
    # end

VPCTestSetupResource = _VPCTestSetupResource()
