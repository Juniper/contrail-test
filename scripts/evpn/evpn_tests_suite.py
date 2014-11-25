import os
import time
import unittest
from tests import *
from floating_ip_tests import *
from evpn_tests import *
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
    suite.addTest(TestEvpnCases('test_ipv6_ping_for_non_ip_communication'))
    descr = x.inputs.get_html_description()
    inputs.get_setup_detail()

    if x.inputs.generate_html_report:
        buf = open(x.inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
            stream=buf,
            title='%s %s' % (inputs.setup_detail, inputs.log_scenario),
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
