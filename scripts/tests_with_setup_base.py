# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools

from contrail_test_init import *
from vn_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource


class TestSanityBase(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture
        self.cn_inspect = self.connections.cn_inspect

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(TestSanityBase, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(TestSanityBase, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
            1. Create VN with subnet
            2. Verify VN against control-node, collector and API
            3. Delete VN and verify
        Pass criteria: Step 2 and 3 should pass 
        '''
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vnxx', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_fixture.verify_on_setup()
        return True
    # end

    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
            1. Create a VN and launch VM within it
            2. Verify VN and VM against control-node, collector and API
            3. Delete VM & VN and verify
        Pass criteria: Step 2 and 3 should pass 
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, image_name='ubuntu'))
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()
        return True
    # end test_vm_add_delete

    @preposttest_wrapper
    def test_floating_ip(self):
        '''Test to validate floating-ip Assignment to a VM. 
            1. Pick VN from resource pool which has VM'in it 
            2. Create FIP pool for resource FIP VN fvn
            3. Associate FIP from pool to test VM and verify
            4. Ping to FIP from test VM
        Pass criteria: Step 2,3 and 4 should pass
        '''
        result = True
        fip_pool_name = 'some-pool1'
        fvn_name = self.res.fip_vn_name
        fvn_fixture = self.res.get_fvn_fixture()
        vn1_fixture = self.res.get_vn1_fixture()
        vn1_vm1_fixture = self.res.get_vn1_vm1_fixture()
        assert vn1_vm1_fixture.verify_on_setup(force=True)
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        fvn_vm1_fixture = self.res.get_fvn_vm1_fixture()
        assert fvn_vm1_fixture.wait_till_vm_is_up()
        fvn_subnets = self.res.fip_vn_subnets
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn_vm1_fixture.vm_ip):
            result = result and False
        fip_fixture.disassoc_and_delete_fip(fip_id)
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (vn1_vm1_name, fvn_vm1_name))
            self.logger.info('Checking if the required verifications',
                             'on the fixtures pass')
            assert fvn_fixture.verify_on_setup()
            assert vn1_fixture.verify_on_setup()
            assert vn1_vm1_fixture.verify_on_setup()
            assert fvn_vm1_fixture.verify_on_setup()
            assert result
        return True
    # end test_floating_ip

    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN.
            1. Pick VN from resource pool which has 2 VM's within it 
            2. Verify VN & VM against control-node, collector and API
            3. Ping from one VM to another which are launched in same network
        Pass criteria: Step 2 and 3 should pass
        '''
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn1_fixture = self.res.get_vn1_fixture()
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        vm1_fixture.wait_till_vm_is_up()

        vm2_fixture = self.res.get_vn1_vm2_fixture()
        vm2_fixture.wait_till_vm_is_up()
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip) or \
           not vm2_fixture.ping_to_ip(vm1_fixture.vm_ip):
            self.logger.error('Ping between VMs failed,',
                 ' Verifying the fixtures...')
            assert vn1_fixture.verify_on_setup()
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
        return True
    # end test_ping_within_vn
# end TestSanityBase
