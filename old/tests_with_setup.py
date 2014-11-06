# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tests_with_setup_base import *


class TestSanity(TestSanityBase):

    def setUp(self):
        super(TestSanity, self).setUp()
    # end setUp

    def cleanUp(self):
        super(TestSanity, self).cleanUp()
    # end cleanUp

# end TestSanityFixture
