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
from webui.tests_with_setup_base_webui import *
from util import get_os_env
from NewPolicyTests import *
from servicechain.firewall.sanity_with_setup import SvcMonSanityFixture
from servicechain.mirror.sanity_with_setup import SvcMirrorSanityFixture
from tcutils.contrailtestrunner import ContrailHTMLTestRunner

if __name__ == "__main__":
    if not get_os_env('SCRIPT_TS'):
        os.environ['SCRIPT_TS'] = time.strftime("%Y_%m_%d_%H_%M_%S")
    if 'PARAMS_FILE' in os.environ:
        ini_file = os.environ.get('PARAMS_FILE')
    else:
        ini_file = 'params.ini'
    inputs = ContrailTestInit(ini_file)
    inputs.setUp()
    print "\nTest Log File : %s" % (inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    suite.addTest(
        WebuiTestSanity('test_networks_in_webui_config_networking_networks'))
    suite.addTest(
        WebuiTestSanity('test_ipam_in_webui_config_networking_ip_address_management'))
    suite.addTest(WebuiTestSanity(
        'test_service_templates_in_webui_config_services_service_templates'))
    suite.addTest(WebuiTestSanity(
        'test_floating_ips_in_webui_config_networking_manage_floating_ips'))
    suite.addTest(
        WebuiTestSanity('test_policy_in_webui_config_networking_policies'))
    suite.addTest(
        WebuiTestSanity('test_dashboard_details_in_webui_monitor_infra_dashborad'))
    suite.addTest(WebuiTestSanity(
        'test_control_node_basic_details_in_webui_monitor_infra_control_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_control_node_advance_details_in_webui_monitor_infra_control_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_config_node_basic_details_in_webui_monitor_infra_config_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_config_node_advance_details_in_webui_monitor_infra_config_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_vrouter_basic_details_in_webui_monitor_infra_virtual_routers'))
    suite.addTest(WebuiTestSanity(
        'test_vrouter_advance_details_in_webui_monitor_infra_virtual_routers'))
    suite.addTest(WebuiTestSanity(
        'test_analytics_node_basic_details_in_webui_monitor_infra_analytics_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_analytics_node_advance_details_in_webui_monitor_infra_analytics_nodes'))
    suite.addTest(WebuiTestSanity(
        'test_network_basic_details_in_webui_monitor_networking_networks'))
    suite.addTest(WebuiTestSanity(
        'test_network_advance_details_in_webui_monitor_networking_networks'))
    suite.addTest(WebuiTestSanity(
        'test_instance_basic_details_in_webui_monitor_networking_networks'))
    suite.addTest(WebuiTestSanity(
        'test_instance_advance_details_in_webui_monitor_networking_networks'))

    descr = inputs.get_html_description()

    if inputs.generate_html_report:
        buf = open(inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
            stream=buf,
            title='%s Result %s' % (
                inputs.log_scenario, inputs.build_id),
            description=descr
        )
        test_result = runner.run(suite)
        buf.close()
        print "Test HTML Result : %s " % (inputs.html_report)
        inputs.upload_results()
        file_to_send = inputs.html_report
    else:
        test_result = unittest.TextTestRunner(verbosity=2).run(suite)
        file_to_send = inputs.log_file

    inputs.log_any_issues(test_result)
    inputs.send_mail(file_to_send)
    print "\nTest Log File : %s" % (inputs.log_file)
