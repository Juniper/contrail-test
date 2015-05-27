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

from tests_with_setup import *
from util import get_os_env
from NewPolicyTests import *
from policyTrafficTests import *
from encap_tests import *
from tcutils.contrailtestrunner import ContrailHTMLTestRunner
from vm_vn_tests import TestVMVN
from securitygroup.sanity import SecurityGroupSanityTests
from tests import TestSanityFixture
from discovery_tests_with_setup import TestDiscoveryFixture
from vdns.vdns_tests import TestVdnsFixture
from analytics_tests_with_setup import AnalyticsTestSanity
from vpc.sanity import VPCSanityTests

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

    suite.addTest(TestDiscoveryFixture(
        'test_all_publishers_registered_to_discovery_service'))
    suite.addTest(
        TestDiscoveryFixture('test_agent_gets_control_nodes_from_discovery'))
    suite.addTest(
        TestDiscoveryFixture('test_control_nodes_subscribed_to_ifmap_service'))
    #disable test below, not passing in ci environment
    #suite.addTest(
    #    TestDiscoveryFixture('test_agents_connected_to_collector_service'))
    suite.addTest(TestSanity('test_vn_add_delete'))
    suite.addTest(TestSanity('test_vm_add_delete'))
    suite.addTest(SecurityGroupSanityTests('test_sec_group_add_delete'))
    suite.addTest(TestSanity('test_floating_ip'))
    suite.addTest(TestSanity('test_ping_within_vn'))
    suite.addTest(TestSanity('test_policy_to_deny'))
    suite.addTest(TestSanity('test_remove_policy_with_ref'))
    suite.addTest(TestSanity('test_ipam_add_delete'))
    suite.addTest(TestSanityFixture('test_project_add_delete'))
    suite.addTest(NewPolicyTestFixture('test_policy'))
    suite.addTest(NewPolicyTestFixture('test_policy_modify_vn_policy'))
    suite.addTest(NewPolicyTestFixture('test_repeated_policy_modify'))
    suite.addTest(policyTrafficTestFixture(
        'test_multi_vn_repeated_policy_update_with_ping'))
    #disable this case for vrouter core
    #suite.addTest(TestSanity('test_process_restart_in_policy_between_vns'))
    # Tune certain parameters for scp test.
    TestVMVN.scp_test_file_sizes = ['1303']
    suite.addTest(TestVMVN('test_vm_file_trf_scp_tests'))
    suite.addTest(TestSanity('test_ping_on_broadcast_multicast'))
    suite.addTest(
        TestSanity('test_ping_within_vn_two_vms_two_different_subnets'))
    #suite.addTest(TestMxSanityFixture('test_mx_gateway'))
    #suite.addTest(TestMxSanityFixture('test_change_of_rt_in_vn'))
    #suite.addTest(TestSanity('test_control_node_switchover'))
    #suite.addTest(SvcMonSanityFixture('test_svc_monitor_datapath'))
    #suite.addTest(SvcMonSanityFixture('test_svc_in_network_datapath'))
    #suite.addTest(SvcMonSanityFixture('test_svc_transparent_with_3_instance'))
    suite.addTest(
        TestSanityFixture('test_process_restart_with_multiple_vn_vm'))
    suite.addTest(TestSanityFixture('test_metadata_service'))
    #disable test below, not passing in ci environment
    #suite.addTest(TestSanityFixture('test_generic_link_local_service'))
    #suite.addTest(TestVMVN('test_dns_resolution_for_link_local_service'))
    #suite.addTest(SvcMirrorSanityFixture('test_svc_mirroring'))
    suite.addTest(TestSanity('test_verify_generator_collector_connections'))
    #suite.addTest(TestEncapsulation('test_apply_policy_fip_on_same_vn_gw_mx'))
    #suite.addTest(TestVdnsFixture('test_vdns_ping_same_vn'))
    suite.addTest(AnalyticsTestSanity('test_verify_object_logs'))
    #suite.addTest(AnalyticsTestSanity('test_verify_flow_tables'))
    #suite.addTest(VPCSanityTests('test_create_delete_vpc'))
    #suite.addTest(VPCSanityTests('test_subnet_create_delete'))
    #suite.addTest(VPCSanityTests('test_ping_between_instances'))
    #suite.addTest(VPCSanityTests('test_acl_with_association'))
    #suite.addTest(VPCSanityTests('test_security_group'))
    #suite.addTest(VPCSanityTests('test_allocate_floating_ip'))
    #suite.addTest(
    #    ECMPSanityFixture('test_ecmp_svc_in_network_with_static_route_no_policy'))
    #suite.addTest(
    #    ECMPSanityFixture('test_ecmp_svc_in_network_nat_with_3_instance'))
    #suite.addTest(
    #    ECMPSanityFixture('test_ecmp_svc_transparent_with_3_instance'))
    if inputs.multi_tenancy == 'True':
        suite.addTest(TestPerms('test_all'))
    #suite.addTest(PerformanceSanity('test_netperf_within_vn'))
    #suite.addTest(TestEvpnCases('test_with_vxlan_l2_mode'))
    #suite.addTest(TestEvpnCases('test_with_vxlan_encap_agent_restart'))
    #suite.addTest(
    #    TestEvpnCases('test_with_vxlan_encap_to_verify_l2_vm_file_trf_by_scp'))
    #suite.addTest(
    #    TestEvpnCases('test_with_vxlan_encap_to_verify_l2_vm_file_trf_by_tftp'))

    descr = inputs.get_html_description()
    inputs.get_setup_detail()

    if inputs.generate_html_report:
        buf = open(inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
            stream=buf,
            title='%s %s' % (inputs.setup_detail, inputs.log_scenario),
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
