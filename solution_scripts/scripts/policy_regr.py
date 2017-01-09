# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python sanity_tests.py'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Set the env variable SINGLE_NODE_IP if you are running a single node(No need to populate the json file)
#
import os
import time

import unittest

from tests import *
from NewPolicyTests import *
from policyTrafficTests import *
from mx_test import *
from svc_mon_tests import SvcMonSanityFixture
from test_perms import *
from sdn_policy_traffic_test_topo import *
from tcutils.contrailtestrunner import ContrailHTMLTestRunner
from policy_api_test import TestApiPolicyFixture

if __name__ == "__main__":

    os.environ['SCRIPT_TS'] = time.strftime("%Y%m%d%H%M%S")
    x = TestSanityFixture()
    x.setUp()
    x.inputs.get_pwd()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()

    suite.addTest(TestApiPolicyFixture('test_create_api_policy'))
    suite.addTest(
        TestApiPolicyFixture('test_associate_disassociate_api_policy'))
    suite.addTest(
        TestApiPolicyFixture('test_policy_with_local_keyword_across_multiple_vn'))
    suite.addTest(
        TestApiPolicyFixture('test_policy_rules_scaling_with_ping_api'))
    suite.addTest(TestApiPolicyFixture('test_policy_api_fixtures'))

    suite.addTest(NewPolicyTestFixture('test_remove_policy_with_ref'))
    suite.addTest(NewPolicyTestFixture('test_policy_protocol_summary'))
    suite.addTest(NewPolicyTestFixture('test_policy_with_duplicate_rules'))
    suite.addTest(NewPolicyTestFixture('test_policy_RT_import_export'))
    suite.addTest(NewPolicyTestFixture('test_policy'))
    suite.addTest(NewPolicyTestFixture('test_policy_modify_vn_policy'))
    suite.addTest(NewPolicyTestFixture('test_repeated_policy_modify'))

    suite.addTest(policyTrafficTestFixture(
        'test_controlnode_switchover_policy_between_vns_traffic'))
    suite.addTest(policyTrafficTestFixture(
        'test_multi_vn_repeated_policy_update_with_ping'))
    suite.addTest(policyTrafficTestFixture(
        'test_policy_multi_vn_modify_rules_of_live_flows'))
    suite.addTest(policyTrafficTestFixture(
        'test_policy_multi_vn_with_multi_proto_traffic'))
    suite.addTest(policyTrafficTestFixture(
        'test_policy_single_vn_modify_rules_of_live_flows'))
    suite.addTest(policyTrafficTestFixture(
        'test_policy_single_vn_with_multi_proto_traffic'))
    suite.addTest(policyTrafficTestFixture('test_scale_policy_with_ping'))
    suite.addTest(policyTrafficTestFixture(
        'test_single_vn_repeated_policy_update_with_ping'))
    suite.addTest(policyTrafficTestFixture('test_policy_rules_scaling'))
    suite.addTest(
        policyTrafficTestFixture('test_policy_rules_scaling_with_ping'))
    suite.addTest(
        policyTrafficTestFixture('test_policy_with_scaled_udp_flows'))

    descr = x.inputs.get_html_description()

    if x.inputs.generate_html_report:
        buf = open(x.inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
            stream=buf,
            title='%s Result %s' % (
                x.inputs.log_scenario, x.inputs.build_id),
            description=descr
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
