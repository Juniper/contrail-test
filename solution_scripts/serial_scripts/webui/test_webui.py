# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import time
import fixtures
import testtools
import re
import test
from tcutils.wrappers import preposttest_wrapper
import base


class WebuiTestSanity(base.WebuiBaseTest):

    @classmethod
    def setUpClass(cls):
        super(WebuiTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    # UI config tests #

    @preposttest_wrapper
    def test1_1_create_svc_templates(self):
        ''' UI Config-> Services-> Service Templates  : Test svc template creation
        '''
        assert self.res.setup_obj.create_svc_template(), 'Svc template creation failed'
        return True
    # end test_create_svc_template

    @preposttest_wrapper
    def test1_2_create_svc_instances(self):
        '''UI Config-> Services-> Service Instances : Test svc instance creation
        '''
        assert self.res.setup_obj.create_svc_instance(), 'Svc instance creation failed'
        return True
    # end test_create_svc_instance

    @preposttest_wrapper
    def test1_3_create_ipams(self):
        '''UI Config : Networking -> IP Address Management :  Test ipam creation
        '''
        assert self.res.setup_obj.create_ipam(), 'Ipam creation failed'
        return True
    # end test_create_svc_instance

    @preposttest_wrapper
    def test1_4_create_virtual_networks(self):
        '''UI Config : Networking -> Networks : Test virtual network creation
        '''
        assert self.res.setup_obj.create_vn(),'Virtual network creation failed'
        return True
    # end test_create_virtual_networks

    @preposttest_wrapper
    def test1_5_create_ports(self):
        '''UI Config : Networking -> ports : Test port creation
        '''
        assert self.res.setup_obj.create_port(), 'Port creation creation failed'
        return True
    # end test_create_ports

    @preposttest_wrapper
    def test1_6_create_routers(self):
        '''UI Config : Networking -> Routers : Test router creation
        '''
        assert self.res.setup_obj.create_router(), 'Router creation failed'
        return True
    # end test_create_routers

    @preposttest_wrapper
    def test1_7_create_policies(self):
        '''UI Config : Networking -> Policies : Test Policy creation
        '''
        assert self.res.setup_obj.create_policy(), 'Policy creation failed'
        return True
    # end test_create_policies

    @preposttest_wrapper
    def test1_8_attach_policy_to_vn(self):
        '''UI Config : Networking -> Networks : Test attach_policy to vn
        '''
        assert self.res.setup_obj.attach_policy_to_vn(), 'Policy attach to a VN failed'
        return True
    # end test_attach_policy_to_vn

    @preposttest_wrapper
    def test1_9_launch_virtual_instances(self):
        ''' Horizon Config : Test launch_virtual_instance
        '''
        assert self.res.setup_obj.create_vm(), 'Virtual instance launch failed'
        return True
    # end test_launch_virtual_instances

    @preposttest_wrapper
    def test2_3_create_security_groups(self):
        assert self.res.setup_obj.create_security_group(), 'Security group creation failed'
        return True
    # end test_create_security_groups

    @preposttest_wrapper
    def test2_1_create_dns_servers(self):
        '''UI Config : DNS -> Servers : Test dns server creation
        '''
        assert self.res.setup_obj.create_dns_server(), 'Dns server creation failed'
        return True
    # end test_create_dns_servers

    @preposttest_wrapper
    def test2_2_create_dns_records(self):
        '''UI Config : DNS -> Records : Test dns record creation
        '''
        assert self.res.setup_obj.create_dns_record(), 'DNS record creation failed'
        return True
    # end test_create_dns_records

    # UI verification tests

    @preposttest_wrapper
    def test_verify_config_networking_floating_ips(self):
        '''Test floating ips on config->Networking->Manage Floating IPs page
        '''
        assert self.webui.verify_floating_ip_api_data(), 'Floating ips config data verification failed' 
        return True
    # end test_verify_config_networking_floating_ips

    @preposttest_wrapper
    def test_verify_config_networking_virtual_networks(self):
        '''Test networks on config->Networking->Networks page
        '''
        assert self.webui.verify_vn_api_data(), 'Virtual netoworks config data verification failed'
        return True
    # end test_verify_config_networking_virtual_networks

    @preposttest_wrapper
    def test_verify_config_networking_ipams(self):
        '''Test ipams on config->Networking->IP Address Management page
        '''
        assert self.webui.verify_ipam_api_data(), 'Ipams config data verification failed'
        return True
    # end test_verify_config_networking_ipams

    @preposttest_wrapper
    def test_verify_config_networking_policies(self):
        '''Test polcies on config->Networking->Policies page
        '''
        assert self.webui.verify_policy_api_data(), 'Policies config data verification failed'
        return True
    # end test_verify_config_networking_policies

    @preposttest_wrapper
    def test_verify_config_services_service_templates(self):
        '''Test svc templates on config->Services->Service Templates page
        '''
        assert self.webui.verify_service_template_api_basic_data(), 'Svc templates config data verification failed'
        return True
    # end test_verify_config_services_service_templates

    @preposttest_wrapper
    def test_verify_config_services_service_instances(self):
        '''Test svc instances on config->Services->Service Instances page
        '''
        assert self.webui.verify_service_instance_api_basic_data(), 'Svc instances config data verification failed'
        return True
    # end test_verify_config_services_service_instances

    @preposttest_wrapper
    def test_verify_config_infra_project_quotas(self):
        '''Test project quotas on config->Networking->Project Quotas page
        '''
        assert self.webui.verify_project_quotas(), 'Project Quotas config data verification failed'
        return True
    # end test_verify_config_infra_project_quotas

    @preposttest_wrapper
    def test_verify_monitor_infra_control_node_basic_details(self):
        '''Test control node basic details on monitor->Infrastruture->Control Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_bgp_routers_ops_basic_data(), 'Control node basic details verification failed'
        return True
    # end test_verify_monitor_infra_control_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_control_node_advance_details(self):
        '''Test control node advance details on monitor->Infrastruture->Control Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_bgp_routers_ops_advance_data(), 'Control node advance details verification failed'
        return True
    # end test_verify_monitor_infra_control_node_advance_details

    @preposttest_wrapper
    def test_verify_monitor_infra_vrouter_basic_details(self):
        '''Test virtual routers basic details on monitor->Infrastruture->Virtual Routers->Node Details-> Basic view page
        '''
        assert self.webui.verify_vrouter_ops_basic_data(),'Vrouter node basic details verification failed'
        return True
    # end test_verify_monitor_infra_vrouter_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_vrouter_advance_details(self):
        '''Test virtual routers advance details on monitor->Infrastruture->Virtual Routers->Node Details-> Advanced view page
        '''
        assert self.webui.verify_vrouter_ops_advance_data(), 'Vrouter advance details verification failed'
        return True
    # end test_verify_monitor_infra_vrouter_advance_details

    @preposttest_wrapper
    def test_verify_monitor_infra_analytics_node_basic_details(self):
        '''Test analytics node basic details on monitor->Infrastruture->Analytics Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_analytics_nodes_ops_basic_data(),'Analytics nodes basic details verification failed'
        return True
    # end test_verify_monitor_infra_analytics_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_analytics_node_advance_details(self):
        '''Test analytics node advance details on monitor->Infrastruture-> Analytics Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_analytics_nodes_ops_advance_data(), 'Analytics nodes advance details verification failed'
        return True
    # end test_verify_monitor_infra_analytics_node_advance_details

    @preposttest_wrapper
    def test_verify_monitor_infra_config_node_basic_details(self):
        '''Test config node basic details on monitor->Infrastruture->Config Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_config_nodes_ops_basic_data(), 'Config node basic details verification failed'
        return True
    # end test_verify_monitor_infra_config_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_config_node_advance_details(self):
        '''Test config node advance details on monitor->Infrastruture->Config Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_config_nodes_ops_advance_data(), 'Config node advance details verification failed'
        return True
    # end test_config_node_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_network_basic_details(self):
        '''Test network basic on monitor->Networking->Networks->Network Summary-> basic page
        '''
        assert self.webui.verify_vn_ops_basic_data(), 'Network basic details verification failed'
        return True
    # end test_network_basic_details

    @preposttest_wrapper
    def test_verify_monitor_networking_network_advance_details(self):
        '''Test network advance details on monitor->Networking->Networks->Network Summary-> Advanced page
        '''
        assert self.webui.verify_vn_ops_advance_data(), 'Network advance details verification failed'
        return True
    # end test_network_advance_details

    @preposttest_wrapper
    def test_verify_monitor_infra_dashboard_details(self):
        '''Test dashboard details on monitor->Infra->Dashboard page
        '''
        assert self.webui.verify_dashboard_details(), 'Dashboard details verification failed'
        return True
    # end test_verify_monitor_infra_dashboard_details

    @preposttest_wrapper
    def test_verify_monitor_networking_instance_basic_details(self):
        '''Test instance basic details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_basic_data(), 'Instance basic details verification failed'
        return True
    # end test_instance_basic_details

    @preposttest_wrapper
    def test_verify_monitor_networking_instance_advance_details(self):
        '''Test instance advance details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_advance_data(), 'Instance advance details verification failed'
        return True
    # end test_instance_advance_details

# end WebuiTestSanity
