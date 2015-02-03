# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from vgw import base
from vgw.verify import VerifyVgwCases
from vgw.verify import VerifyDynamicVgwCases


class TestVgwCases(base.BaseVgwTest, VerifyVgwCases):

    @classmethod
    def setUpClass(cls):
        super(TestVgwCases, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_vgw_with_fip_on_same_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM got FIP from VGW network
        '''

        return self.verify_vgw_with_fip(compute_type='same')

    @preposttest_wrapper
    def test_vgw_with_native_vm_on_same_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM is launched on VGW network
        '''

        return self.verify_vgw_with_native_vm(compute_type='same')

    @preposttest_wrapper
    def test_vgw_with_native_vm_on_different_node(self):
        '''Test VM is launched on the same compute node where VGW is configured and VM is laucnhed on VGW network
        '''

        return self.verify_vgw_with_native_vm(compute_type='different')

    @preposttest_wrapper
    def test_vgw_with_fip_on_different_node(self):
        '''Test VM is launched on the different compute node where VGW is configured and VM got FIP from VGW network
        '''

        return self.verify_vgw_with_fip(compute_type='different')

    @preposttest_wrapper
    def test_vgw_with_multiple_subnet_for_single_vgw(self):
        '''Test VGW having multiple subnet is working properly
        '''

        return self.verify_vgw_with_multiple_subnet()

    @preposttest_wrapper
    def test_vgw_with_restart_of_vgw_node(self):
        '''Test VGW with restarting the VGW node
        '''

        return self.vgw_restart_of_vgw_node()


class TestDynamicVgwCases(base.BaseVgwTest, VerifyDynamicVgwCases):

    @classmethod
    def setUpClass(cls):
        super(TestDynamicVgwCases, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_dynamic_vgw_compute_ping(self):
        '''
        Test to validate dynamic VGW creation and communication from overlay VM to compute IP
         1: Create VGW interface dynamicaly 
         2. Create corresponding vn and launch VM
         3. Ping from VM to the compute where VGW is created 
         4. Delete VGW interface

         Pass criteria:  Step 3 should pass
         Maintainer: chhandak@juniper.net
         '''
        return self.verify_dynamic_vgw_compute_ping()
