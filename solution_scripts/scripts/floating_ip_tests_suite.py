import os
import time
import unittest
from tests import *
from floating_ip_tests import *
from mx_test import *
from tcutils.contrailtestrunner import ContrailHTMLTestRunner

if __name__ == "__main__":

    os.environ['SCRIPT_TS'] = time.strftime("%Y%m%d%H%M%S")
    x = TestSanityFixture()
    x.setUp()
    x.inputs.get_pwd()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    suite.addTest(TestFipCases('test_floating_ip'))
    suite.addTest(TestFipCases('test_tcp_transfer_from_fip_vm'))
    suite.addTest(TestFipCases('test_multiple_floating_ip_for_single_vm'))
    suite.addTest(TestFipCases('test_mutual_floating_ip'))
    suite.addTest(TestFipCases('test_exhust_Fip_pool_and_release_fip'))
    suite.addTest(TestFipCases('test_extend_fip_pool_runtime'))
    suite.addTest(TestFipCases('test_service_restart_with_fip'))
    suite.addTest(TestFipCases('test_fip_with_traffic'))
    suite.addTest(TestFipCases('test_removal_of_fip_with_traffic'))
    suite.addTest(TestFipCases('test_traffic_with_control_node_switchover'))
    suite.addTest(TestFipCases('test_fip_in_uve'))
    suite.addTest(TestFipCases('test_vn_info_in_agent_with_fip'))
    suite.addTest(TestFipCases('test_vm_restart_with_fip'))
    suite.addTest(TestFipCases('test_multiple_floating_ip_for_single_vm'))
    suite.addTest(TestFipCases('test_communication_across_borrower_vm'))
    suite.addTest(TestFipCases('test_fip_with_policy'))
    suite.addTest(TestFipCases('test_fip_pool_shared_across_project'))
    suite.addTest(TestFipCases('test_communication_across__diff_proj'))
    suite.addTest(TestFipCases('test_traffic_to_fip'))
    suite.addTest(TestFipCases('test_ping_to_fip_using_diag'))
    suite.addTest(TestMxSanityFixture('test_apply_policy_fip_on_same_vn'))
    suite.addTest(TestMxSanityFixture('test_mx_gateway'))
    suite.addTest(TestMxSanityFixture('test_change_of_rt_in_vn'))
    suite.addTest(TestMxSanityFixture('test_fip_with_vm_in_2_vns'))
    suite.addTest(TestMxSanityFixture('test_ftp_http_with_public_ip'))
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
