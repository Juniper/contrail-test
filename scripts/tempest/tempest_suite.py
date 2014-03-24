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

from tempest.tempest_base import *
from tempest.neutron_networks import *
from tempest.neutron_routers import *
from tempest.neutron_floating_ip import *
from tempest.neutron_cli import *
from tempest.neutron_security_group import *
from tempest.neutron_quotas import *
from tempest.neutron_loadbalancer import *
from tempest.neutron_extensions import *
from tempest.neutron_vpnaas import *

from util import get_os_env
from tcutils.contrailtestrunner import ContrailHTMLTestRunner 

if __name__ == "__main__":

    if not get_os_env('SCRIPT_TS') :
        os.environ['SCRIPT_TS']= time.strftime("%Y_%m_%d_%H_%M_%S")
    if 'PARAMS_FILE' in os.environ :
        ini_file= os.environ.get('PARAMS_FILE')
    else:
        ini_file= 'params.ini'
    inputs= ContrailTestInit( ini_file)
    inputs.setUp()
    print "\nTest Log File : %s" %(inputs.log_file)
    suite= unittest.TestSuite()
    test_result= unittest.TestResult()

    suite.addTest(NeutronNetworks('test_create_update_delete_network_subnet'))
    suite.addTest(NeutronNetworks('test_show_network'))
    suite.addTest(NeutronNetworks('test_list_networks'))
    suite.addTest(NeutronNetworks('test_list_subnets'))
    suite.addTest(NeutronNetworks('test_show_subnet'))
    suite.addTest(NeutronNetworks('test_create_update_delete_port'))
    suite.addTest(NeutronNetworks('test_show_port'))
    suite.addTest(NeutronNetworks('test_list_ports'))
    suite.addTest(NeutronNetworks('test_show_non_existent_network'))
    suite.addTest(NeutronNetworks('test_show_non_existent_subnet'))
    suite.addTest(NeutronNetworks('test_show_non_existent_port'))
    suite.addTest(NeutronNetworks('test_tempest_neutron_security_group'))
    suite.addTest(NeutronSecGroup('test_list_security_groups'))
    suite.addTest(NeutronSecGroup('test_create_show_delete_security_group'))
    suite.addTest(NeutronSecGroup('test_create_show_delete_security_group_rule'))
    suite.addTest(NeutronFIP('test_create_list_show_update_delete_floating_ip'))
    suite.addTest(NeutronFIP('test_create_list_show_update_delete_floating_ip_xml'))
    suite.addTest(NeutronRouters('test_create_show_list_update_delete_router'))
    suite.addTest(NeutronRouters('test_add_remove_router_interface_with_subnet_id'))
    suite.addTest(NeutronCLI('test_neutron_fake_action'))
    suite.addTest(NeutronCLI('test_neutron_net_list'))
    suite.addTest(NeutronCLI('test_neutron_ext_list'))
    suite.addTest(NeutronCLI('test_neutron_dhcp_agent_list_hosting_net'))
    suite.addTest(NeutronCLI('test_neutron_agent_list'))
    suite.addTest(NeutronCLI('test_neutron_meter_label_list'))
    suite.addTest(NeutronCLI('test_neutron_meter_label_rule_list'))
    suite.addTest(NeutronCLI('test_neutron_floatingip_list'))
    suite.addTest(NeutronCLI('test_neutron_net_external_list'))
    suite.addTest(NeutronCLI('test_neutron_port_list'))
    suite.addTest(NeutronCLI('test_neutron_quota_list'))
    suite.addTest(NeutronCLI('test_neutron_router_list'))
    suite.addTest(NeutronCLI('test_neutron_security_group_list'))
    suite.addTest(NeutronCLI('test_neutron_security_group_rule_list'))
    suite.addTest(NeutronCLI('test_neutron_subnet_list'))
    suite.addTest(NeutronCLI('test_neutron_help'))
    suite.addTest(NeutronCLI('test_neutron_version'))
    suite.addTest(NeutronCLI('test_neutron_debug_net_list'))
    suite.addTest(NeutronCLI('test_neutron_quiet_net_list'))
    suite.addTest(NeutronVPN('test_create_update_delete_vpn_service'))
    suite.addTest(NeutronVPN('test_list_vpn_services'))
    suite.addTest(NeutronVPN('test_show_vpn_service'))
    suite.addTest(NeutronLB('test_list_vips'))
    suite.addTest(NeutronLB('test_create_update_delete_pool_vip'))
    suite.addTest(NeutronLB('test_show_vip'))
    suite.addTest(NeutronLB('test_show_pool'))
    suite.addTest(NeutronLB('test_list_pools'))
    suite.addTest(NeutronLB('test_list_members'))
    suite.addTest(NeutronLB('test_create_update_delete_member'))
    suite.addTest(NeutronLB('test_list_health_monitors'))
    suite.addTest(NeutronLB('test_create_update_delete_health_monitor'))
    suite.addTest(NeutronLB('test_show_health_monitor'))
    suite.addTest(NeutronLB('test_associate_disassociate_health_monitor_with_pool'))
    suite.addTest(NeutronExtensions('test_list_show_extensions'))
    suite.addTest(NeutronQuotas('test_quotas'))


    descr= inputs.get_html_description()
    if inputs.generate_html_report :
        buf=open( inputs.html_report, 'w')

        runner = ContrailHTMLTestRunner(
                    stream=buf,
                    title='%s Result %s' %(inputs.log_scenario, inputs.build_id),
                    description=descr
                    )
        test_result= runner.run(suite)
        buf.close()
        print "Test HTML Result : %s " %(inputs.html_report)
        inputs.upload_results()
        file_to_send= inputs.html_report
    else:
        test_result=unittest.TextTestRunner(verbosity=2).run(suite)
        file_to_send= inputs.log_file

    inputs.log_any_issues(test_result)
    inputs.send_mail(file_to_send)
    print "\nTest Log File : %s" %(inputs.log_file)
