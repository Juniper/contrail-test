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

        # Setting up default encapsulation
#        self.logger.info('Deleting any Encap before continuing')
#        out=self.connections.delete_vrouter_encap()
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
        self.logger.info('updated.UUID is %s' % (config_id))

        (self.vn1_name, self.vn1_subnets) = ("EVPN-VN1", ["33.1.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = ("EVPN-VN2", ["22.1.1.0/24"])
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["11.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])
        (self.vn1_vm1_name) = 'EVPN_VN1_VM1'
        (self.vn1_vm2_name) = 'EVPN_VN1_VM2'
        (self.vn2_vm1_name) = 'EVPN_VN2_VM1'
        (self.vn2_vm2_name) = 'EVPN_VN2_VM2'
        (self.vn_l2_vm1_name) = 'EVPN_VN_L2_VM1'
        (self.vn_l2_vm2_name) = 'EVPN_VN_L2_VM2'
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        self.vn1_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn1_name, subnets=self.vn1_subnets))
        self.vn2_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn2_name, subnets=self.vn2_subnets))
        self.vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                inputs=self.inputs, vn_name=self.vn3_name, subnets=self.vn3_subnets, forwarding_mode='l2_l3'))
        self.vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                inputs=self.inputs, vn_name=self.vn4_name, subnets=self.vn4_subnets, forwarding_mode='l2'))

        #self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= self.vn1_fixture.obj, flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn1_vm1_name,node_name= compute_1))
        #self.vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= self.vn1_fixture.obj, flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn1_vm2_name,node_name= compute_2))
        #self.vn2_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn2_vm1_name,node_name= compute_1))
        #self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_obj= self.vn2_fixture.obj, flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn2_vm2_name,node_name= compute_2))
        #self.vn_l2_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_objs= [self.vn3_fixture.obj , self.vn4_fixture.obj], flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn_l2_vm1_name,node_name= compute_1))
        #self.vn_l2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,connections= self.connections, vn_objs= [self.vn3_fixture.obj , self.vn4_fixture.obj], flavor='contrail_flavor_small', image_name= 'ubuntu-traffic', vm_name= self.vn_l2_vm2_name,node_name= compute_2))
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
