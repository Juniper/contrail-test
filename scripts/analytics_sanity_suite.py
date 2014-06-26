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
from ParamTests import ParametrizedTestCase
from mx_test import *
from test_perms import *
from sdn_policy_traffic_test_topo import *
from analytics_tests_with_setup import *
from servicechain.firewall.sanity import SvcMonSanityFixture
from tcutils.contrailtestrunner import ContrailHTMLTestRunner

if __name__ == "__main__":

    os.environ['SCRIPT_TS'] = time.strftime("%Y%m%d%H%M%S")
    x = AnalyticsTestSanity()
    x.setUp()
    x.inputs.get_pwd()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
#    suite.addTest(AnalyticsTestSanity('test_collector_uve'))
#    suite.addTest(AnalyticsTestSanity('test_vrouter_uve'))
    suite.addTest(AnalyticsTestSanity('test_vn_uve_tiers'))
    suite.addTest(AnalyticsTestSanity('test_vn_uve_routing_instance'))
#    suite.addTest(AnalyticsTestSanity('test_vn_uve_vm_list'))
    suite.addTest(AnalyticsTestSanity('test_vrouter_uve_vm_on_vm_create'))
    suite.addTest(AnalyticsTestSanity('test_virtual_machine_uve_vm_tiers'))
#    suite.addTest(AnalyticsTestSanity('test_virtual_machine_uve_and_other_uve_cross_verification'))
# suite.addTest(AnalyticsTestSanity('test_delete_vm_and_verify_vm_uve_and_uve_cross_verification'))
    suite.addTest(AnalyticsTestSanity('test_verify_flow_tables'))
    suite.addTest(
        AnalyticsTestSanity('test_verify__bgp_router_uve_up_xmpp_and_bgp_count'))
    suite.addTest(
        AnalyticsTestSanity('test_verify_connected_networks_based_on_policy'))
    # test_policy_between_vns replaced by enhanced tests in policyTrafficTestFixture
    # suite.addTest(TestSanityFixture('test_policy_between_vns'))
    # suite.addTest(TestPerms('test_all'))
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
