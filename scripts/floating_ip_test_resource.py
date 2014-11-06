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
        (self.vn1_name, self.vn1_subnets) = ("vn1", ["11.1.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = ("vn2", ["22.1.1.0/24"])
        (self.fvn_public_name, self.fvn_public_subnets) = (
            "fip_vn_public", ['10.204.219.16/28'])
        (self.fvn1_name, self.fvn1_subnets) = ("fip_vn1", ['100.1.1.0/24'])
        (self.fvn2_name, self.fvn2_subnets) = ("fip_vn2", ['200.1.1.0/24'])
        (self.fvn3_name, self.fvn3_subnets) = ("fip_vn3", ['170.1.1.0/29'])
        (self.vn1_vm1_name, self.vn1_vm2_name) = ('vn1_vm1', 'vn1_vm2')
        (self.vn2_vm1_name, self.vn2_vm2_name) = ('vn2_vm1', 'vn2_vm2')
        (self.fvn_public_vm1_name) = ('fvn_public_vm1')
        (self.fvn1_vm1_name) = ('fvn1_vm1')
        (self.fvn2_vm1_name) = ('fvn2_vm1')
        (self.fvn3_vm1_name) = ('fvn3_vm1')
        (self.vn1_vm1_traffic_name) = 'VN1_VM1_traffic'
        (self.fvn1_vm1_traffic_name) = 'FVN1_VM1_traffic'
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        # Configure 6 VNs, 4 of them being Floating-VN
        self.vn1_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn1_name, subnets=self.vn1_subnets))
        self.vn2_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn2_name, subnets=self.vn2_subnets))
        self.fvn_public_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections, inputs=self.inputs, vn_name=self.fvn_public_name, subnets=self.fvn_public_subnets))
        self.fvn1_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.fvn1_name, subnets=self.fvn1_subnets))
        self.fvn2_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.fvn2_name, subnets=self.fvn2_subnets))
        self.fvn3_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.fvn3_name, subnets=self.fvn3_subnets))

        # Configure 2 VMs in VN1, 2 VMs in VN2, 1 VM in FVN_PUBLIC, 1 VM in
        # FVN1,FVN2 and FVN3 each
        self.vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn1_fixture.obj, vm_name=self.vn1_vm1_name, node_name=compute_1))
        self.vn1_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn1_fixture.obj, vm_name=self.vn1_vm2_name, node_name=compute_2))
        self.vn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, vm_name=self.vn2_vm1_name, node_name=compute_2))
        self.vn2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.vn2_fixture.obj, vm_name=self.vn2_vm2_name, node_name=compute_1))
        self.fvn_public_vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.fvn_public_fixture.obj, vm_name=self.fvn_public_vm1_name))
        self.fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn1_fixture.obj, vm_name=self.fvn1_vm1_name, node_name=compute_2))
        self.fvn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn2_fixture.obj, vm_name=self.fvn2_vm1_name, node_name=compute_1))
        self.fvn3_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=self.fvn3_fixture.obj, vm_name=self.fvn3_vm1_name, node_name=compute_2))
        self.fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.fvn1_fixture.obj,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=self.fvn1_vm1_traffic_name, node_name=compute_2))
        self.vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn1_fixture.obj,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=self.vn1_vm1_traffic_name, node_name=compute_1))
    # end setup_common_objects

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
