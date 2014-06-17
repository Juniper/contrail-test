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

from cs_tests import TestCSSanity
from tcutils.contrailtestrunner import ContrailHTMLTestRunner

if __name__ == "__main__":

    os.environ['SCRIPT_TS']= time.strftime("%Y%m%d%H%M%S")
    x= TestCSSanity()
    x.setUp()
    print "\nTest Log File : %s" %(x.inputs.log_file)
    suite= unittest.TestSuite()
    test_result= unittest.TestResult()

    suite.addTest(TestCSSanity('test_vn_add_delete'))
    suite.addTest(TestCSSanity('test_vm_add_delete'))
    suite.addTest(TestCSSanity('test_ping_within_vn'))
    suite.addTest(TestCSSanity('test_vms_in_project'))
    suite.addTest(TestCSSanity('test_vm_with_fip'))
    suite.addTest(TestCSSanity('test_multiple_networks_per_project'))
    suite.addTest(TestCSSanity('test_mgmt_server_restart'))
    suite.addTest(TestCSSanity('test_disassociate_vn_from_vm'))
    suite.addTest(TestCSSanity('test_vm_stop_start'))
    suite.addTest(TestCSSanity('test_vn_connectivity_thru_policy'))
    suite.addTest(TestCSSanity('test_vsrx_guest_vm_with_ping'))
    suite.addTest(TestCSSanity('test_duplicate_vn_add'))
    suite.addTest(TestCSSanity('test_vm_add_delete_in_2_vns'))
    suite.addTest(TestCSSanity('test_vm_arp'))
    suite.addTest(TestCSSanity('test_vm_vn_block_exhaustion'))
    suite.addTest(TestCSSanity('test_shutdown_vm'))
    suite.addTest(TestCSSanity('test_ping_on_broadcast_multicast'))
    suite.addTest(TestCSSanity('test_vpc_aclrules'))
    suite.addTest(TestCSSanity('test_vpc_acllists'))
    suite.addTest(TestCSSanity('test_multiple_vpc'))
    # Multi-node sanity tests
    if len(x.inputs.compute_ips) > 1:
        suite.addTest(TestCSSanity('test_dedicated_host'))
        suite.addTest(TestCSSanity('test_migrate_vm'))
    suite.addTest(TestCSSanity('test_process_restart_with_multiple_vn_vm'))
    suite.addTest(TestCSSanity('test_xen_host_reboot'))
    suite.addTest(TestCSSanity('test_analytics'))
    suite.addTest(TestCSSanity('test_analytics_query_logs'))
    suite.addTest(TestCSSanity('test_analytics_flows'))

    descr= x.inputs.get_html_description()

    if x.inputs.generate_html_report :
        buf=open( x.inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
                    stream=buf,
                    title='%s Result %s' %(x.inputs.log_scenario, x.inputs.build_id),
                    description=descr
                    )
        test_result= runner.run(suite)
        buf.close()
        print "Test HTML Result : %s " %(x.inputs.html_report)
        x.inputs.upload_results()
        file_to_send= x.inputs.html_report
    else:
        test_result=unittest.TextTestRunner(verbosity=2).run(suite)
        file_to_send= x.inputs.log_file

    x.inputs.log_any_issues(test_result)
    x.inputs.send_mail(file_to_send)
    print "\nTest Log File : %s" %(x.inputs.log_file)

