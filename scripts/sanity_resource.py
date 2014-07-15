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
        
        self.vn1_fixture = None
        self.vn2_fixture = None
        self.fvn_fixture = None
        self.vn1_vm1_fixture = None
        self.vn1_vm2_fixture = None
        self.vn1_vm3_fixture = None
        self.vn1_vm4_fixture = None
        self.vn1_vm5_fixture = None
        self.vn1_vm6_fixture = None
        self.vn2_vm1_fixture = None
        self.vn2_vm2_fixture = None
        self.vn2_vm3_fixture = None
        self.fvn_vm1_fixture = None
        self.set_common_objects()
        return self
    # end setUp
    
    def get_vn1_fixture(self):
        if self.vn1_fixture:
            return self.vn1_fixture
        else:
            self.vn1_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, 
                          inputs=self.inputs, 
                          vn_name=self.vn1_name,
                          subnets=self.vn1_subnets))
            return self.vn1_fixture 
    # end get_vn1_fixture

    def get_vn2_fixture(self):
        if self.vn2_fixture:
            return self.vn2_fixture
        else:
            self.vn2_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name=self.vn2_name,
                          subnets=self.vn2_subnets))
            return self.vn2_fixture
    # end get_vn2_fixture
            
    def get_fvn_fixture(self):
        if self.fvn_fixture:
            return self.fvn_fixture
        else:
            self.fvn_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name=self.fip_vn_name,
                          subnets=self.fip_vn_subnets))
            return self.fvn_fixture
    # end get_fvn_fixture
    
    def get_vm_fixture(self, vm_fixture, vn_fixture, vm_name, 
                        image_name= os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic',
                        flavor='contrail_flavor_small',node_name=None):
        if vm_fixture:
            if verify:
                assert vm_fixture.verify_on_setup()
            return vm_fixture
        else:
            vm_fixture = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    vm_name=vm_name,
                    image_name=image_name,
                    flavor=flavor,
                    node_name=node_name))
            assert vm_fixture.verify_on_setup(), \
                "VM %s verification failed!" % (vm_fixture.vm_name)
            return vm_fixture
    # end get_vm_fixture 

    def get_vn1_vm1_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm1_fixture, self.vn1_fixture, self.vn1_vm1_name,
                node_name=self.compute_1)
 
    def get_vn1_vm2_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm2_fixture, self.vn1_fixture, self.vn1_vm2_name)

    def get_vn1_vm3_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm3_fixture, self.vn1_fixture, self.vn1_vm3_name)

    def get_vn1_vm4_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm4_fixture, self.vn1_fixture, self.vn1_vm4_name,
                image_name='redmine-fe', flavor='contrail_flavor_medium')

    def get_vn2_vm1_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn2_vm1_fixture, self.vn2_fixture, self.vn2_vm1_name,
                image_name='redmine-be', flavor='contrail_flavor_medium')

    def get_vn1_vm5_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm5_fixture, self.vn1_fixture, self.vn1_vm5_name)

    def get_vn1_vm6_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn1_vm5_fixture, self.vn1_fixture, self.vn1_vm5_name)

    def get_vn2_vm2_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn2_vm2_fixture, self.vn2_fixture, self.vn2_vm2_name,
                node_name=self.compute_2)

    def get_vn2_vm3_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.vn2_vm3_fixture, self.vn2_fixture, self.vn2_vm3_name)

    def get_fvn_vm1_fixture(self, verify=False):
        return self.get_vm_fixture(
                self.fvn_vm1_fixture, self.fvn_fixture, self.fvn_vm1_name)

    def set_common_objects(self):
        (self.vn1_name, self.vn1_subnets) = ("vn1", ["192.168.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = ("vn2", ["192.168.2.0/24"])
        (self.fip_vn_name, self.fip_vn_subnets) = ("fip_vn", ['100.1.1.0/24'])
        (self.vn1_vm1_name, self.vn1_vm2_name) = ('vn1_vm1', 'vn1_vm2')
        (self.vn1_vm3_name, self.vn1_vm4_name) = ('vn1_vm3', 'vn1_vm4')
        (self.vn1_vm5_name, self.vn1_vm6_name) = (
            'netperf_vn1_vm1', 'netperf_vn1_vm2')
        self.vn2_vm1_name = 'vn2_vm1'
        self.vn2_vm2_name = 'vn2_vm2'
        self.vn2_vm3_name = 'netperf_vn2_vm1'
        self.fvn_vm1_name = 'fvn_vm1'

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        self.compute_1 = host_list[0]
        self.compute_2 = host_list[0]
        if len(host_list) > 1:
            self.compute_1 = host_list[0]
            self.compute_2 = host_list[1]
        # Configure 6 VMs in VN1, 1 VM in VN2, and 1 VM in FVN
        sg_name = 'default'
        project_name = self.inputs.project_name
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        self.logger.info('Default SG to be edited for allow all')
        self.project_fixture.set_sec_group_for_allow_all(project_name, sg_name)
    # end setup_common_objects

    def verify(self, fixture):
        if fixture:
            assert fixture.verify_on_setup()

    def verify_common_objects(self):
        self.verify(self.vn1_fixture)
        self.verify(self.vn2_fixture)
        self.verify(self.fvn_fixture)
        self.verify(self.vn1_vm1_fixture)
        self.verify(self.vn1_vm2_fixture)
        self.verify(self.vn1_vm3_fixture)
        self.verify(self.vn1_vm4_fixture)
        self.verify(self.vn1_vm5_fixture)
        self.verify(self.vn1_vm6_fixture)
        self.verify(self.vn2_vm1_fixture)
        self.verify(self.vn2_vm2_fixture)
        self.verify(self.vn2_vm3_fixture)
        self.verify(self.fvn_vm1_fixture)
    # end verify_common_objects

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
