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
from NewPolicyTests import NewPolicyTestFixture
from policyTrafficTests import policyTrafficTestFixture
from mx_test import *
from test_perms import *
from sdn_policy_traffic_test_topo import *
from tcutils.contrailtestrunner import ContrailHTMLTestRunner
from policy_api_test import TestApiPolicyFixture
from vm_vn_tests import TestVMVN
from analytics_tests_with_setup import AnalyticsTestSanity
from floating_ip_tests import TestFipCases
from servicechain.firewall.sanity import SvcMonSanityFixture
from servicechain.mirror.sanity import SvcMirrorSanityFixture
from servicechain.mirror.regression import SvcMirrorRegrFixture
from servicechain.firewall.regression import SvcMonRegrFixture
from vdns.vdns_tests import TestVdnsFixture
from discovery_tests_with_setup import TestDiscoveryFixture
from ecmp.sanity import TestECMP
from ecmp.sanity_w_svc import ECMPSvcMonSanityFixture
from vpc.sanity import VPCSanityTests
from evpn.evpn_tests import TestEvpnCases
from encap_tests import TestEncapsulation
from securitygroup.sanity import SecurityGroupSanityTests
from securitygroup.regression import SecurityGroupRegressionTests
from vgw.vgw_tests import TestVgwCases
from util import get_os_env

if __name__ == "__main__":

    if not get_os_env('SCRIPT_TS'):
        os.environ['SCRIPT_TS'] = time.strftime("%Y_%m_%d_%H_%M_%S")
    x = TestSanityFixture()
    x.setUp()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    test_classes = []
    if len(sys.argv) == 1:
        # Run all suites
        test_classes = ['TestApiPolicyFixture', 'NewPolicyTestFixture',
                        'policyTrafficTestFixture', 'TestVMVN',
                        'AnalyticsTestSanity', 'TestFipCases',
                        'SvcMonSanityFixture', 'SvcMirrorSanityFixture',
                        'SvcMirrorRegrFixture', 'SvcMonRegrFixture',
                        'TestSanityFixture', 'TestPerms', 'TestVdnsFixture',
                        'TestDiscoveryFixture', 'TestECMP',
                        'ECMPSvcMonSanityFixture', 'VPCSanityTests',
                        'TestEvpnCases', 'TestEncapsulation',
                        'SecurityGroupSanityTests',
                        'SecurityGroupRegressionTests',
                        'TestVgwCases'
                        ]
    else:
        for test_class in sys.argv[1:]:
            test_classes.append(test_class)
    # end if

    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    loader = unittest.TestLoader()
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(eval(test_class)))
        if test_class == 'TestPerms':
            if x.inputs.multi_tenancy == 'True':
                suite.addTest(TestPerms('test_all'))
    # end for
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
