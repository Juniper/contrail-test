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
from webui import base

class WebuiTestSanity(base.WebuiBaseTest):

    @classmethod
    def setUpClass(cls):
        super(WebuiTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_control_node_basic_details_in_webui_monitor_infra_control_nodes(self):
        '''Test to validate control node basic view details in webui monitor tab
        '''
        assert self.webui.verify_bgp_routers_ops_basic_data()
        return True
    # end
    # test_verify_control_node_basic_details_in_webui_monitor_infra_control_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_control_node_advance_details_in_webui_monitor_infra_control_nodes(self):
        '''Test to validate  control node basic view  details in webui monitor tab
        '''
        assert self.webui.verify_bgp_routers_ops_advance_data()
        return True
    # end
    # test_verify_control_node_advance_details_in_webui_monitor_infra_control_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_vrouter_basic_details_in_webui_monitor_infra_virtual_routers(self):
        '''Test to validate vrouter basic view details in webui monitor tab
        '''
        assert self.webui.verify_vrouter_ops_basic_data()
        return True
    # end
    # test_verify_vrouter_basic_details_in_webui_monitor_infra_virtual_routers

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_vrouter_advance_details_in_webui_monitor_infra_virtual_routers(self):
        '''Test to validate  vrouter advance view details in webui monitor tab
        '''
        assert self.webui.verify_vrouter_ops_advance_data()
        return True
    # end
    # test_verify_vrouter_node_advance_details_in_webui_monitor_infra_virtual_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_analytics_node_basic_details_in_webui_monitor_infra_analytics_nodes(self):
        '''Test to validate analytics node basic view details in webui monitor tab
        '''
        assert self.webui.verify_analytics_nodes_ops_basic_data()
        return True
    # end
    # test_verify_analytics_basic_details_in_webui_monitor_infra_analytics_nodes
    
    @test.attr(type='serial')
    @preposttest_wrapper
    def test_analytics_node_advance_details_in_webui_monitor_infra_analytics_nodes(self):
        '''Test to validate analytics node advance view details in webui monitor tab
        '''
        assert self.webui.verify_analytics_nodes_ops_advance_data()
        return True
    # end
    # test_verify_analytics_node_advance_details_in_webui_monitor_infra_analytics_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_config_node_basic_details_in_webui_monitor_infra_config_nodes(self):
        '''Test to validate config node advance view details in webui monitor
        '''
        assert self.webui.verify_config_nodes_ops_basic_data()
        return True
    # end
    # test_verify_config_node_basic_details_in_webui_monitor_infra_config_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_config_node_advance_details_in_webui_monitor_infra_config_nodes(self):
        '''Test to validate config node advance view details in webui monitor tab
        '''
        assert self.webui.verify_config_nodes_ops_advance_data()
        return True
    # end
    # test_verify_config_node_advance_details_in_webui_monitor_infra_config_nodes

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_network_basic_details_in_webui_monitor_networking_networks(self):
        '''Test to validate network basic view details in webui monitor
        '''
        assert self.webui.verify_vn_ops_basic_data()
        return True
    # end
    # test_verify_networks_basic_details_in_webui_monitor_networking_networks

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_network_advance_details_in_webui_monitor_networking_networks(self):
        '''Test to validate network advance view details in webui monitor tab
        '''
        assert self.webui.verify_vn_ops_advance_data()
        return True
    # end
    # test_verify_networks_advance_details_in_webui_monitor_networking_networks

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_dashboard_details_in_webui_monitor_infra_dashborad(self):
        '''Test to validate dashboard details details in webui monitor tab
        '''
        assert self.webui.verify_dashboard_details()
        return True
    # end test_dashboard_details_in_webui_monitor_infra_dashborad

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_instance_basic_details_in_webui_monitor_networking_networks(self):
        '''Test to validate instace basic view details in webui monitor tab
        '''
        assert self.webui.verify_vm_ops_basic_data()
        return True
    # end
    # test_verify_instance_basic_details_in_webui_monitor_networking_networks

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_instance_advance_details_in_webui_monitor_networking_networks(self):
        '''Test to validate instance advance view details in webui monitor tab
        '''
        assert self.webui.verify_vm_ops_advance_data()
        return True
    # end
    # test_verify_instance_advance_details_in_webui_monitor_networking_networks

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_floating_ips_in_webui_config_networking_manage_floating_ips(self):
        '''Test to validate networks in webui config tab
        '''
        assert self.webui.verify_floating_ip_api_data()
        return True
    # end test_floating_ips_in_webui_config_networking_manage_floating_ips

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_networks_in_webui_config_networking_networks(self):
        '''Test to validate networks in webui config tab
        '''
        assert self.webui.verify_vn_api_data()
        return True
    # end test_verify_networks_in_webui_config_networking_networks

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_ipam_in_webui_config_networking_ip_address_management(self):
        '''Test to validate ipam in webui config networking ip address management
        '''
        assert self.webui.verify_ipam_api_data()
        return True
    # end verify_ipam_api_basic_data_in_webui

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_policy_in_webui_config_networking_policies(self):
        '''Test to validate policies in webui config networking policies
        '''
        assert self.webui.verify_policy_api_data()
        return True
    # end verify_policies_api_basic_data_in_webui

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_service_templates_in_webui_config_services_service_templates(self):
        '''Test to validate service templates in webui config services service templates
        '''
        assert self.webui.verify_service_template_api_basic_data()
        return True
    # end test_service_templates_in_webui_config_services_service_templates


# end WebuiTestSanity
