# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python sanity_tests.py'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Set the env variable SINGLE_NODE_IP if you are running a single node(No need to populate the json file)
#
import os
import HTMLTestRunner
import unittest
import time
from tests import *
from NewPolicyTests import *
from ParamTests import ParametrizedTestCase
from policy_test_input import *

if __name__ == "__main__":

    os.environ['SCRIPT_TS'] = time.strftime("%Y%m%d%H%M%S")
    x = TestSanityFixture()
    x.setUp()
    x.inputs.get_pwd()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    # Following line will generate a suite of all test cases from the feature test
    # class with the given parameter [topology]
    suite.addTest(ParametrizedTestCase.parametrize(NewPolicyTestFixture,
                                                   topology=PolicyTestBasicConfig_1))
    # Regular test cases can be added as usual
    suite.addTest(TestSanityFixture('test_vn_add_delete'))
    #suite.addTest( TestSanityFixture('test_vm_add_delete'))
    #suite.addTest( TestSanityFixture('test_floating_ip'))
    #suite.addTest( TestSanityFixture('test_ping_within_vn'))
    #suite.addTest( TestSanityFixture('test_policy_to_deny'))
    #suite.addTest( NewPolicyTestFixture('test_policy_in_vna'))
    #suite.addTest( TestSanityFixture('test_policy_between_vns'))
    #suite.addTest( TestSanityFixture('test_tcp_transfer_from_fip_vm'))

    if x.inputs.generate_html_report:
        buf = open(x.inputs.html_report, 'w')

        runner = HTMLTestRunner.HTMLTestRunner(
            stream=buf,
            title='Sanity Result %s' % (x.inputs.build_id),
            description='Sanity Result of Build %s<br>Log File : %s<br>Report    : %s' % (
                        x.inputs.build_id, x.inputs.log_link, x.inputs.html_log_link)
        )
        test_result = runner.run(suite)
        buf.close()
        print "Test HTML Result : %s " % (x.inputs.html_report)
        x.inputs.upload_results()
        file_to_send = x.inputs.html_report
    else:
        test_result = unittest.TextTestRunner(verbosity=2).run(suite)
        file_to_send = x.inputs.log_file

    x.inputs.log_any_issues(test_result)
    x.inputs.send_mail(file_to_send)
    print "\nTest Log File : %s" % (x.inputs.log_file)
