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
from test_perms import *
from sdn_policy_traffic_test_topo import *
from vpc.sanity import VPCSanityFixture
from servicechain.firewall.sanity import SvcMonSanityFixture
from servicechain.mirror.sanity import SvcMirrorSanityFixture
from tcutils.contrailtestrunner import ContrailHTMLTestRunner
from util import get_os_env

if __name__ == "__main__":

#    os.environ['SCRIPT_TS']= time.strftime("%Y%m%d%H%M%S")
    if not get_os_env('SCRIPT_TS'):
        os.environ['SCRIPT_TS'] = time.strftime("%Y_%m_%d_%H_%M_%S")
    x = TestSanityFixture()
    x.setUp()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    suite.addTest(TestSanityFixture('test_vn_add_delete'))
    suite.addTest(TestSanityFixture('test_vm_add_delete'))
    suite.addTest(TestSanityFixture('test_ipam_add_delete'))
    suite.addTest(TestSanityFixture('test_floating_ip'))
    suite.addTest(TestSanityFixture('test_ping_within_vn'))
    suite.addTest(TestSanityFixture('test_policy_to_deny'))
    suite.addTest(NewPolicyTestFixture('test_remove_policy_with_ref'))
    suite.addTest(NewPolicyTestFixture('test_policy'))
    suite.addTest(NewPolicyTestFixture('test_policy_modify_vn_policy'))
    suite.addTest(NewPolicyTestFixture('test_repeated_policy_modify'))
    # test_policy_between_vns replaced by enhanced tests in policyTrafficTestFixture
    # suite.addTest(TestSanityFixture('test_policy_between_vns'))
    suite.addTest(policyTrafficTestFixture(
        'test_multi_vn_repeated_policy_update_with_ping'))
    suite.addTest(
        TestSanityFixture('test_process_restart_in_policy_between_vns'))
    suite.addTest(TestSanityFixture('test_tcp_transfer_from_fip_vm'))
    suite.addTest(TestSanityFixture('test_ping_on_broadcast_multicast'))
    suite.addTest(
        TestSanityFixture('test_ping_within_vn_two_vms_two_different_subnets'))
    suite.addTest(TestMxSanityFixture('test_mx_gateway'))
    suite.addTest(TestMxSanityFixture('test_change_of_rt_in_vn'))
    suite.addTest(TestSanityFixture('test_control_node_switchover'))
    suite.addTest(SvcMonSanityFixture('test_svc_monitor_datapath'))
    suite.addTest(SvcMonSanityFixture('test_svc_in_network_datapath'))
    suite.addTest(SvcMonSanityFixture('test_svc_transparent_with_3_instance'))
    suite.addTest(
        TestSanityFixture('test_process_restart_with_multiple_vn_vm'))
    # suite.addTest(SvcMirrorSanityFixture('test_svc_mirroring'))
    suite.addTest(VPCSanityFixture('test_create_delete_vpc'))
    suite.addTest(VPCSanityFixture('test_create_delete_vpc_false_cidr'))
    suite.addTest(VPCSanityFixture('test_subnet_create_delete'))
    suite.addTest(VPCSanityFixture('test_subnet_create_delete_false_cidr'))
    suite.addTest(VPCSanityFixture('test_run_instance'))
    suite.addTest(VPCSanityFixture('test_allocate_floating_ip'))
    suite.addTest(VPCSanityFixture('test_run_instance_with_floating_ip'))

    if x.inputs.multi_tenancy == 'True':
        suite.addTest(TestPerms('test_all'))
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
