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

from vm_vn_tests import *
#from NewPolicyTests import *
#from policyTrafficTests import *
#from ParamTests import ParametrizedTestCase
#from mx_test import *
from test_perms import *
#from sdn_policy_traffic_test_topo import *
#from servicechain.firewall.sanity import SvcMonSanityFixture
from tcutils.contrailtestrunner import ContrailHTMLTestRunner

if __name__ == "__main__":

    os.environ['SCRIPT_TS'] = time.strftime("%Y%m%d%H%M%S")
    x = TestVMVN()
    x.setUp()
    x.inputs.get_pwd()
    print "\nTest Log File : %s" % (x.inputs.log_file)
    suite = unittest.TestSuite()
    test_result = unittest.TestResult()
    suite.addTest(TestVMVN('test_bring_up_vm_with_control_node_down'))
    suite.addTest(TestVMVN('test_broadcast_udp_w_chksum'))
    suite.addTest(TestVMVN('test_diff_proj_same_vn_vm_add_delete'))
    suite.addTest(TestVMVN('test_disassociate_vn_from_vm'))
    suite.addTest(TestVMVN('test_duplicate_vn_add'))
    suite.addTest(TestVMVN('test_ipam_add_delete'))
    suite.addTest(TestVMVN('test_ipam_persistence_across_restart_reboots'))
    suite.addTest(TestVMVN('test_multiple_vn_vm'))
    suite.addTest(
        TestVMVN('test_multistep_vm_add_delete_with_stop_start_service'))
    suite.addTest(TestVMVN('test_multistep_vm_delete_with_stop_start_service'))
    suite.addTest(TestVMVN('test_no_frag_in_vm'))
    suite.addTest(TestVMVN('test_nova_com_sch_restart_with_multiple_vn_vm'))
    suite.addTest(TestVMVN('test_ping_on_broadcast_multicast'))
    suite.addTest(TestVMVN('test_ping_on_broadcast_multicast_with_frag'))
    suite.addTest(TestVMVN('test_ping_within_vn'))
    suite.addTest(
        TestVMVN('test_ping_within_vn_two_vms_two_different_subnets'))
    suite.addTest(TestVMVN('test_policy_between_vns_diff_proj'))
    suite.addTest(TestVMVN('test_process_restart_in_policy_between_vns'))
    suite.addTest(TestVMVN('test_process_restart_with_multiple_vn_vm'))
    suite.addTest(TestVMVN('test_release_ipam'))
    suite.addTest(TestVMVN('test_shutdown_vm'))
    suite.addTest(TestVMVN('test_traffic_bw_vms'))
    suite.addTest(TestVMVN('test_traffic_bw_vms_diff_pkt_size'))
    suite.addTest(TestVMVN('test_traffic_bw_vms_diff_pkt_size_w_chksum'))
    suite.addTest(TestVMVN('test_vm_add_delete'))
    suite.addTest(TestVMVN('test_vm_add_delete_in_2_vns'))
    suite.addTest(TestVMVN('test_vm_add_delete_in_2_vns_chk_ips'))
    suite.addTest(TestVMVN('test_vm_arp'))
    suite.addTest(TestVMVN('test_vm_gw_tests'))
    suite.addTest(TestVMVN('test_vm_in_2_vns_chk_ping'))
    suite.addTest(TestVMVN('test_vm_intf_tests'))
    suite.addTest(TestVMVN('test_vm_multiple_flavors'))
    suite.addTest(TestVMVN('test_vm_static_ip_tests'))
    suite.addTest(TestVMVN('test_vm_vn_block_exhaustion'))
    suite.addTest(TestVMVN('test_vn_add_delete'))
    suite.addTest(TestVMVN('test_vn_in_agent_with_vms_add_delete'))
    suite.addTest(TestVMVN('test_vn_name_with_spl_characters'))
    suite.addTest(TestVMVN('test_vn_subnet_types'))
    suite.addTest(TestVMVN('test_vn_vm_no_ip'))
    suite.addTest(TestVMVN('test_vn_vm_no_ip_assign'))
    # suite.addTest(TestPerms('test_all'))
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
