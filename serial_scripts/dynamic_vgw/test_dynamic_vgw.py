# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from dynamic_vgw import base
from dynamic_vgw.verify import VerifyDynamicVgwCases

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
