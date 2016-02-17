# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD

from tcutils.wrappers import preposttest_wrapper
from verify import VerifySriovCases
import base
import test

class TestSriov(base.BaseSriovTest, VerifySriovCases):
     
    @classmethod
    def setUpClass(cls):
        super(TestSriov, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def test_communication_between_two_sriov_vm(self):
        '''
        '''
        return self.communication_between_two_sriov_vm()


