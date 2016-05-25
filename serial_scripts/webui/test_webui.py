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

    @preposttest_wrapper
    def test3_1_edit_net_without_change(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page without changing anything")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Get the uuid before editing")
        uuid = self.ui.get_vn_display_name('UUID')
        vn_name = self.ui.get_vn_display_name('Display Name')
        logger.debug("UUID before editing " + uuid)
        logger.debug("Step 2 : Verify WebUI before editing")
        assert self.webui.verify_vn_after_edit_ui('UUID',uuid), 'Virtual networks config data verification in UI failed'
        logger.debug("Step 3 : Verify API server before editing")
        assert self.webui.verify_vn_after_edit_api('UUID',uuid,uuid), 'Virtual networks config data verification in API failed'
        logger.debug("Step 4 : Verify OPS server before editing")
        assert self.webui.verify_vn_after_edit_ops('UUID',vn_name,uuid), 'Virtual networks config data verification in OPS failed'
        logger.debug("Step 5 : Edit the VN without changing anything")
        assert self.webui.edit_vn_without_change(), 'Editing Network failed'
        logger.debug("Step 6 : Verify WebUI server after editing")
        assert self.webui.verify_vn_after_edit_ui('UUID',uuid), 'Virtual networks config data verification in UI failed'
        logger.debug("Step 7 : Verify API server after editing")
        assert self.webui.verify_vn_after_edit_api('UUID',uuid,uuid), 'Virtual networks config data verification in API failed'
        logger.debug("Step 8 : Verify OPS server after editing")
        assert self.webui.verify_vn_after_edit_ops('UUID',vn_name,uuid), 'Virtual networks config data verification in OPS failed'
        return True

    #end test_edit_vn_witout_change

    @preposttest_wrapper
    def test3_2_edit_net_disp_name_change(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page changing VN display name")

        logger.debug("Step 1 : Get the display name of the VN before editing")
        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        if self.vn_disp_name:
            logger.debug("Getting VN display name is successful and the VN name is %s" %(self.vn_disp_name))
            logger.debug("Step 2 : Editing the VN by the name")
            assert self.webui.edit_vn_disp_name_change('vn1'), 'Editing Network failed'
            logger.debug("Step 3 : Verify WebUI server after editing")
            assert self.webui.verify_vn_after_edit_ui('Display Name','vn1'), 'Virtual networks config data verification in UI failed'
            logger.debug("Step 4 : Verify API server after editing")
            assert self.webui.verify_vn_after_edit_api('Display Name','vn1',uuid), 'Virtual networks config data verification in API failed'
            logger.debug("Step 5 : Verify OPS server after editing")
            assert self.webui.verify_vn_after_edit_ops('Display Name','vn1','vn1'), 'Virtual networks config data verification in OPS failed'
            logger.debug("Step 6 : Editing the VN with the previous vn name")
            assert self.webui.edit_vn_disp_name_change(self.vn_disp_name), 'Editing Network failed'
            logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            assert self.webui.verify_vn_after_edit_ui('Display Name',self.vn_disp_name), 'Virtual networks config data verification in UI failed'
            logger.debug("Step 8 : Verifying the VN after editing previous vn name in API")
            assert self.webui.verify_vn_after_edit_api('Display Name',self.vn_disp_name,uuid),'Virtual networks config data verification in API failed'
            logger.debug("Step 9 : Verify OPS server after editing with previous name")
            assert self.webui.verify_vn_after_edit_ops('Display Name',self.vn_disp_name,self.vn_disp_name), 'Virtual networks config data verification in OPS failed'


        else:
            logger.error("Not able to get the display name. So Editing Vn is not possible")
        return True
    #end test_edit_vn_witout_change

    @preposttest_wrapper
    def test3_3_edit_net_disp_name_change_with_spl_char(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page changing VN display name with spl char")
        logger.debug("Step 1 : Get the display name of the VN before editing")
        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        if self.vn_disp_name:
            logger.debug("Getting VN display name is successful and the VN name is %s" %(self.vn_disp_name))
            logger.debug("Step 2 : Editing the VN by the name with special characters")
            assert self.webui.edit_vn_disp_name_change('vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-'), 'Editing Network failed'
            logger.debug("Step 3 : Verify WebUI server after editing")
            assert self.webui.verify_vn_after_edit_ui('Display Name','vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-'), 'Virtual networks config data verification in UI failed'

            logger.debug("Step 4 : Verify API server after editing")
            assert self.webui.verify_vn_after_edit_api('Display Name','vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-',uuid), 'Virtual networks config data verification in API failed'
            logger.debug("Step 5 : Verify OPS server after editing")
            assert self.webui.verify_vn_after_edit_ops('Display Name','vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-','vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-'), 'Virtual networks config data verification in OPS failed'

            logger.debug("Step 6 : Editing the VN with the previous vn name")
            assert self.webui.edit_vn_disp_name_change(self.vn_disp_name), 'Editing Network failed'
            logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            assert self.webui.verify_vn_after_edit_ui('Display Name',self.vn_disp_name), 'Virtual networks config data verification in UI failed'

            logger.debug("Step 8 : Verifying the VN after editing previous vn name in API")
            assert self.webui.verify_vn_after_edit_api('Display Name',self.vn_disp_name,uuid),'Virtual networks config data verification in API failed'
            logger.debug("Step 9 : Verify OPS server after editing")
            assert self.webui.verify_vn_after_edit_ops('Display Name',self.vn_disp_name,self.vn_disp_name), 'Virtual networks config data verification in OPS failed'
        else:
            logger.error("Not able to get the display name. So Editing Vn is not possible")
        return True

    #end test_edit_vn_witout_change

    @preposttest_wrapper
    def test3_4_edit_net_policy(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with policy")
        logger.debug("Step 1 : Attach policy to the VN")
        assert self.webui.add_vn_with_policy(), 'Editing network with policy failed'

        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        self.vn_policy = str(self.ui.get_vn_display_name('Policy'))

        logger.debug("Step 2 : Verify the VN for the attached policy through WebUI server")
        assert self.webui.verify_vn_after_edit_ui('Policy',self.vn_policy), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify the VN for the attached policy through API server")
        assert self.webui.verify_vn_after_edit_api("Policy","Policy",uuid), 'Virtual networks config data verification in API failed'
        logger.debug("Step 4 : Verify the VN for the attached policy through OPS server")
        assert self.webui.verify_vn_after_edit_ops('Policy',self.vn_disp_name,self.vn_disp_name), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the policy which is attached")

        assert self.webui.del_vn_with_policy(), 'Editing network with policy failed'

    #end test3_4_edit_net_policy

    @preposttest_wrapper
    def test3_5_edit_net_subnet(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with subnet")
        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        verify_list = ['Subnet','Subnet-gate','Subnet-dns','Subnet-dhcp']
        for i in verify_list:
            if i == 'Subnet':
                str1 = 'all'
            else:
                str1 = i + 'disabled'
            logger.debug("Step 1 - " + i + ": Add subnet with " + str1 + "options")
            assert self.webui.edit_vn_with_subnet(i), 'Editing network with subnet failed'
            subnet = self.ui.get_vn_display_name('Subnet')

            logger.debug("Step 2 - " + i + ": Verify the VN for subnet in WebUI")
            assert self.webui.verify_vn_after_edit_ui(i,subnet), 'Virtual networks config data verification in UI failed'
            logger.debug("Step 3 - " + i + ": Verify the VN for subnet in API server")
            assert self.webui.verify_vn_after_edit_api(i,subnet,uuid), 'Virtual networks config data verification in API failed'
            logger.debug("Step 4 - " + i + ": Verify the VN for subnet in OPS server")
            assert self.webui.verify_vn_after_edit_ops(i,self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'
            logger.debug("Step 5 : Remove the subnet which is added")
            assert self.webui.del_vn_with_subnet(), 'Editing network with subnet failed'

    #end test3_5_edit_net_subnet

    @preposttest_wrapper
    def test3_6_edit_net_host_opt(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with host routes")
        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        logger.debug("Step 1 : Add Host Route under VN")
        assert self.webui.edit_vn_with_host_route('add','pos'), 'Editing network with host routes failed'
        time.sleep(5)
        host_route = self.ui.get_vn_display_name('Host Route')
        logger.debug("Step 2 : Verify the host route in WebUI")
        assert self.webui.verify_vn_after_edit_ui('Host Route',host_route), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify the host route in API server")
        assert self.webui.verify_vn_after_edit_api('Host Route',host_route,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for host route in OPS server")
        assert self.webui.verify_vn_after_edit_ops('Host Route',host_route,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Host Route which is added")
        assert self.webui.edit_vn_with_host_route('remove','pos'), 'Editing network with host routes failed'
    # end test3_6_edit_net_host_opt

    @preposttest_wrapper
    def test3_7_edit_net_host_opt_neg(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with host routes")
        self.ui = WebuiCommon(self)
        uuid = self.ui.get_vn_display_name('UUID')
        logger.debug("Step 1 : Add Host Route under VN")
        assert self.webui.edit_vn_with_host_route('add','neg'), 'Editing network with host routes failed as expected for negative scenario'
    # end test3_7_edit_net_host_opt_neg

    @preposttest_wrapper
    def test3_8_edit_net_adv_opt(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Advanced Options")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add advanced options under VN")
        time.sleep(5)
        assert self.webui.edit_vn_with_adv_option(1,'pos-phy'), 'Editing network with advanced options is failed'
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        adv_option = self.ui.get_vn_display_name('Adv Option')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('Adv Option',adv_option), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('Adv Option',adv_option,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('Adv Option',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the VN which is added")
        assert self.webui.edit_option("Networks",'remove'), 'Editing network with advanced options is failed'

    # end test3_8_edit_net_adv_opt

    @preposttest_wrapper
    def test3_9_edit_net_adv_opt_neg(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Advanced Options")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add advanced options under VN")

        assert self.webui.edit_vn_with_adv_option(1,'pos-phy'), 'Editing network with advanced options is failed'
        logger.debug("Step 2 : Edit the vn using advanced options")

        assert self.webui.edit_vn_with_adv_option(0,'neg-phy'), 'Editing network with advanced option is failed'

        logger.debug("Step 3 : Remove the VN which is added")
        assert self.webui.edit_option("Networks",'remove'), 'Editing network with advanced options is failed'

    # end test3_9_edit_net_adv_opt_neg

    @preposttest_wrapper
    def test3_10_edit_net_dns(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with DNS server")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add dns server IP under VN")
        assert self.webui.edit_vn_with_dns('add','pos'), 'Editing network with dns is failed'

        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        dns = self.ui.get_vn_display_name('DNS')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('DNS',dns), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('DNS',dns,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('DNS',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the VN which is added")
        assert self.webui.edit_vn_with_dns('remove','pos'), 'Editing network with dns is failed'


    # end test3_10_edit_net_dns

    @preposttest_wrapper
    def test3_11_edit_net_dns_neg(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Advanced Options")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add dns server IP under VN")
        assert self.webui.edit_vn_with_dns('add','neg'), 'Editing network with dns is failed'


    # end test3_11_edit_dns_neg

    @preposttest_wrapper
    def test3_12_edit_net_fip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with DNS server")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Floating server IP under VN")
        assert self.webui.edit_vn_with_fpool('add'), 'Editing network with FIP is failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        fip = self.ui.get_vn_display_name('FIP')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('FIP',fip), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('FIP',fip,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('FIP',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the FIP which is added")
        assert self.webui.edit_vn_with_fpool('remove'), 'Editing network with FIP is failed'

    # end test3_12_edit_net_fip

    @preposttest_wrapper
    def test3_13_edit_net_route_target_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','number','pos','RT'), 'Editing network with Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        rt = self.ui.get_vn_display_name('RT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('RT',rt), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('RT',rt,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('RT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Route Target which is added")
        assert self.webui.edit_vn_with_route_target('remove','number','pos','RT'), 'Editing network with Route Target is failed'

    # end test3_13_edit_net_route_target_as_no

    @preposttest_wrapper
    def test3_14_edit_net_route_target_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','pos','RT'), 'Editing network with Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        rt = self.ui.get_vn_display_name('RT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('RT',rt), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('RT',rt,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('RT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Route Target which is added")
        assert self.webui.edit_vn_with_route_target('remove','ip','pos','RT'), 'Editing network with Route Target is failed'

    # end test3_14_edit_net_route_target_as_ip

    @preposttest_wrapper
    def test3_15_edit_net_route_target_neg_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','RT'), 'Editing network with Route target failed'
        time.sleep(3)

    # end test3_15_edit_net_route_target_neg_as_ip

    @preposttest_wrapper
    def test3_16_edit_net_route_target_neg_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','RT'), 'Editing network with Route target failed'
        time.sleep(3)

    # end test3_16_edit_net_route_target_neg_as_no

    @preposttest_wrapper
    def test3_17_edit_net_exp_route_target_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Export Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','number','pos','ERT'), 'Editing network with Export Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        ert = self.ui.get_vn_display_name('ERT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('ERT',ert), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('ERT',ert,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('ERT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Route Target which is added")
        assert self.webui.edit_vn_with_route_target('remove','number','pos','ERT'), 'Editing network with Export Route Target is failed'

    # end test3_17_edit_net_exp_route_target_as_no

    @preposttest_wrapper
    def test3_18_edit_net_exp_route_target_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Export Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','pos','ERT'), 'Editing network with Export Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        ert = self.ui.get_vn_display_name('ERT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('ERT',ert), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('ERT',ert,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('ERT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Export Route which is added")
        assert self.webui.edit_vn_with_route_target('remove','ip','pos','ERT'), 'Editing network with Export Route Target is failed'

    # end test3_18_edit_net_exp_route_target_as_ip

    @preposttest_wrapper
    def test3_19_edit_net_exp_route_target_neg_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Export Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','ERT'), 'Editing network with Export Route target failed'
        time.sleep(3)

    # end test3_19_edit_net_route_target_neg_as_ip

    @preposttest_wrapper
    def test3_20_edit_net_exp_route_target_neg_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Export Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','ERT'), 'Editing network with Export Route target failed'
        time.sleep(3)

    # end test3_20_edit_net_exp_route_target_neg_as_no

    @preposttest_wrapper
    def test3_21_edit_net_imp_route_target_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Import Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','number','pos','IRT'), 'Editing network with import Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        irt = self.ui.get_vn_display_name('IRT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('IRT',irt), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('IRT',irt,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('IRT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Import Route Target which is added")
        assert self.webui.edit_vn_with_route_target('remove','number','pos','IRT'), 'Editing network with Import Route Target is failed'

    # end test3_21_edit_net_imp_route_target_as_no

    @preposttest_wrapper
    def test3_22_edit_net_imp_route_target_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Import Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Import Route Target under VN")
        time.sleep(3)
        assert self.webui.edit_vn_with_route_target('add','ip','pos','IRT'), 'Editing network with Import Route target failed'
        time.sleep(3)
        uuid = self.ui.get_vn_display_name('UUID')
        self.vn_disp_name = self.ui.get_vn_display_name('Display Name')
        irt = self.ui.get_vn_display_name('IRT')

        logger.debug("Step 2 : Verify the advanced option in WebUI")
        assert self.webui.verify_vn_after_edit_ui('IRT',irt), 'Virtual networks config data verification in UI failed'

        logger.debug("Step 3 : Verify advanced option in API server")
        assert self.webui.verify_vn_after_edit_api('IRT',irt,uuid), 'Virtual networks config data verification in API failed'

        logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        assert self.webui.verify_vn_after_edit_ops('IRT',self.vn_disp_name,uuid), 'Virtual networks config data verification in OPS failed'

        logger.debug("Step 5 : Remove the Import Route Target which is added")
        assert self.webui.edit_vn_with_route_target('remove','ip','pos','IRT'), 'Editing network with Import Route Target is failed'

    # end test3_22_edit_net_route_target_as_ip

    @preposttest_wrapper
    def test3_23_edit_net_imp_route_target_neg_as_ip(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Import Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','IRT'), 'Editing network with Import Route target failed'
        time.sleep(3)

    # end test3_23_edit_net_imp_route_target_neg_as_ip

    @preposttest_wrapper
    def test3_24_edit_net_imp_route_target_neg_as_no(self):
        logger.info("Testcase Description")
        logger.info("Edit the existing network Configure->Networking->Networks Page with Import Route Target")
        self.ui = WebuiCommon(self)
        logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui.edit_vn_with_route_target('add','ip','neg','IRT'), 'Editing network with Import Route target failed'
        time.sleep(3)

    # end test3_24_edit_net_imp_route_target_neg_as_no




# end WebuiTestSanity
