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
from webui_topology import *
topo = sdn_webui_config()
global count
count = 1

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
        '''Test to edit the existing network without changing anything
           1. Go to Configure->Networking->Networks. Then select any of the vn and
              click the edit button
           2. Click the save button without changing anything
           3. Check the UUID in UI page and API and OPS

           Pass Criteria: UUID shouldn't be changed after editing
        '''
        result = True
        opt_list = []
        self.webui.logger.debug("Step 1 : Get the uuid before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        vn_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.webui.logger.debug("UUID before editing " + uuid)
        self.webui.logger.debug("Step 2 : Verify WebUI before editing")
        if not self.webui.verify_vn_after_edit_ui('UUID', uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in WebUI failed")
            result = result and False
        self.webui.logger.debug("Step 3 : Verify API server before editing")
        if not self.webui.verify_vn_after_edit_api('UUID', uuid, uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in API failed")
            result = result and False
        self.webui.logger.debug("Step 4 : Verify OPS server before editing")
        if not self.webui.verify_vn_after_edit_ops('UUID', vn_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Edit the VN without changing anything")
        if not self.webui_common.edit_vn_without_change():
            self.webui.logger.debug('Editing Network failed')
            result = result and False
        self.webui.logger.debug("Step 6 : Verify WebUI server after editing")
        if not self.webui.verify_vn_after_edit_ui('UUID', uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in UI failed")
            result = result and False
        self.webui.logger.debug("Step 7 : Verify API server after editing")
        if not self.webui.verify_vn_after_edit_api('UUID', uuid, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 8 : Verify OPS server after editing")
        if not self.webui.verify_vn_after_edit_ops('UUID', vn_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        return result
    #end test3_1_edit_vn_witout_change

    @preposttest_wrapper
    def test3_2_edit_net_disp_name_change(self):
        ''' Test to edit the existing network by changing VN display name
            1. Go to Configure->Networking->Networks. Then select any of the vn and
               click the edit button
            2. Change the Display name and click the save button
            3. Check that new display name got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Get the display name of the VN before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        opt_list = [topo.vn_disp_name]
        result = True
        if self.vn_disp_name:
            self.webui.logger.debug("Getting VN display name is successful and \
                                     the VN name is %s" %(self.vn_disp_name))
            self.webui.logger.debug("Step 2 : Editing the VN by the name")
            if not self.webui_common.edit_vn_disp_name_change(topo.vn_disp_name):
                self.webui.logger.debug("Editing network failed")
                result = result and False
            self.webui.logger.debug("Step 3 : Verify WebUI server after editing")
            if not self.webui.verify_vn_after_edit_ui('Display Name', \
                                                      topo.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 4 : Verify API server after editing")
            if not self.webui.verify_vn_after_edit_api('Display Name', topo.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 5 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
            self.webui.logger.debug("Step 6 : Editing the VN with the previous vn name")
            if not self.webui_common.edit_vn_disp_name_change(self.vn_disp_name):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            opt_list = [self.vn_disp_name]
            self.webui.logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            if not self.webui.verify_vn_after_edit_ui('Display Name', self.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 8 : Verifying the VN after editing \
                                    previous vn name in API")
            if not self.webui.verify_vn_after_edit_api('Display Name', self.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 9 : Verify OPS server after editing with previous name")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
        else:
            self.webui.logger.error("Not able to get the display name. \
                                    So Editing Vn is not possible")
            result = result and False
        return result
    #end test3_2_edit_vn_witout_change

    @preposttest_wrapper
    def test3_3_edit_net_disp_name_change_with_spl_char(self):
        ''' Test to edit the existing network by changing VN display name with special character
            1. Go to Configure->Networking->Networks. Then select any of the vn and
               click the edit button
            2. Change the Display name with special character and click the save button
            3. Check that new display name got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        opt_list = [topo.vn_disp_name_spl_char_ops]
        result = True
        self.webui.logger.debug("Step 1 : Get the display name of the VN before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        if self.vn_disp_name:
            self.webui.logger.debug("Getting VN display name is successful \
                                     and the VN name is %s" %(self.vn_disp_name))
            self.webui.logger.debug("Step 2 : Editing the VN by the name with special characters")
            if not self.webui_common.edit_vn_disp_name_change(topo.vn_disp_name_spl_char):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            self.webui.logger.debug("Step 3 : Verify WebUI server after editing")
            if not self.webui.verify_vn_after_edit_ui('Display Name', topo.vn_disp_name_spl_char, \
                                                      opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 4 : Verify API server after editing")
            if not self.webui.verify_vn_after_edit_api('Display Name', \
                                                        topo.vn_disp_name_spl_char, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 5 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', self.vn_disp_name, \
                                                        uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
            self.webui.logger.debug("Step 6 : Editing the VN with the previous vn name")
            if not self.webui_common.edit_vn_disp_name_change(self.vn_disp_name):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            self.webui.logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            opt_list = [self.vn_disp_name]
            if not self.webui.verify_vn_after_edit_ui('Display Name', self.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 8 : Verifying the VN after editing previous \
                                    vn name in API")
            if not self.webui.verify_vn_after_edit_api('Display Name', self.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
            self.webui.logger.debug("Step 9 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
        else:
            self.webui.logger.error("Not able to get the display name. \
                                    So Editing Vn is not possible")
            result = result and False
        return result
    #end test3_3_edit_vn_witout_change

    @preposttest_wrapper
    def test3_4_edit_net_by_add_policy(self):
        ''' Test to edit the existing network by policy
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Attach one policy for the vn and save.
            3. Check that attached policy is there in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Attach policy to the VN")
        pol_name = ""
        pol_name = self.webui_common.add_vn_with_policy(pol_name)
        result = True
        opt_list = [pol_name]
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.vn_policy = str(self.webui_common.get_vn_detail_ui('Policy'))
        self.webui.logger.debug("Step 2 : Verify the VN for the attached policy \
                                through WebUI server")
        if not self.webui.verify_vn_after_edit_ui('Policy', self.vn_policy, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify the VN for the attached policy through API server")
        if not self.webui.verify_vn_after_edit_api("Policy", "Policy", uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for the attached policy through OPS server")
        if not self.webui.verify_vn_after_edit_ops('Policy', self.vn_disp_name, \
                                                   self.vn_disp_name, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the policy which is attached")
        if not self.webui_common.del_vn_with_policy(pol_name):
            self.webui.logger.debug('Editing network with policy failed')
            result = result and False
        return result
    #end test3_4_edit_net_policy

    @preposttest_wrapper
    def test3_5_edit_net_by_add_subnet(self):
        ''' Test to edit the existing network by subnet
            1. Go to configure->Networking->Networks. Create a new VN
            2. Edit the created VN and add subnet with all options and save
            3. Check that subnet with all options got reflected in WebUI,API and OPS.
            4. Remove the subnet and and add it back with subnet-gate option.
            5. Check the same got updated in WebUI, API and OPs.
               Similarly doing for subnet-dns and subnet-dhcp

            Pass Criteria : Step 3,4,5 should pass
        '''
        opt_list = [topo.subnet_edit, topo.mask, topo.subnet_sip, topo.subnet_eip,
                    topo.subnet_dns_ip, topo.subnet_gate_ip, topo.subnet_default_gate_ip]
        result = True
        if self.webui_common.click_configure_networks():
            add = self.webui_common.find_element("//i[contains(@class,'icon-plus')]", 'xpath')
            add.click()
            self.webui_common.wait_till_ajax_done(self.browser, wait=3)
            self.webui_common.find_element("//input[contains(@name,'display_name')]", \
                                            'xpath').send_keys(topo.vn_disp_name)
            self.webui_common.wait_till_ajax_done(self.browser, wait=3)
            self.webui_common.click_element('configure-networkbtn1')

            self.webui_common.wait_till_ajax_done(self.browser, wait=5)
            verify_list = ['Subnet', 'Subnet-gate', 'Subnet-dns', 'Subnet-dhcp']
            for subnet_type in verify_list:
                if subnet_type == 'Subnet':
                    str1 = 'all'
                else:
                    str1 = subnet_type + 'disabled'
                self.webui.logger.debug("Step 1 - " + subnet_type + \
                                        ": Add subnet with " + str1 + "options")
                ind = self.webui_common.edit_vn_with_subnet(subnet_type, topo.subnet_edit + \
                                                             "/" + topo.mask, \
                                                             topo.subnet_sip + "-" + \
                                                             topo.subnet_eip, \
                                                             topo.subnet_gate_ip, topo.vn_disp_name)
                if not ind:
                    self.webui.logger.debug('Editing network with subnet failed')
                    result = result and False
                uuid = self.webui_common.get_vn_detail_ui('UUID', index=ind)
                self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', index=ind)
                subnet = self.webui_common.get_vn_detail_ui('Subnet', index=ind)
                self.webui.logger.debug("Step 2 - " + subnet_type + \
                                        ": Verify the VN for subnet in WebUI")
                if not self.webui.verify_vn_after_edit_ui(subnet_type, subnet, opt_list, index=ind):
                    self.webui.logger.debug('Virtual networks config data \
                                             verification in UI failed')
                    result = result and False
                self.webui.logger.debug("Step 3 - " + subnet_type + \
                                        ": Verify the VN for subnet in API server")
                if not self.webui.verify_vn_after_edit_api(subnet_type, subnet, uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in API failed')
                    result = result and False
                self.webui.logger.debug("Step 4 - " + subnet_type + \
                                        ": Verify the VN for subnet in OPS server")
                if not self.webui.verify_vn_after_edit_ops(subnet_type, self.vn_disp_name, \
                                                           uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in OPS failed')
                    result = result and False
                self.webui.logger.debug("Step 5 : Remove the subnet which is added")
                if not self.webui_common.del_vn_with_subnet(topo.vn_disp_name):
                    self.webui.logger.debug('Editing network with subnet failed')
                    result = result and False
        self.webui.logger.debug("Step 6 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   vn_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    #end test3_5_edit_net_subnet

    @preposttest_wrapper
    def test3_6_edit_net_host_opt(self):
        ''' Test to edit the existing network by Host routes
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Add Host route with route prefix and next hop and save.
            3. Check that host route is added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.host_prefix, topo.host_nexthop]
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.webui.logger.debug("Step 1 : Add Host Route under VN")
        if not self.webui_common.edit_vn_with_host_route('add', 'pos', topo.host_prefix, \
                                                         topo.host_nexthop):
            self.webui.logger.debug('Editing network with host routes failed')
            result = result and False
        host_route = self.webui_common.get_vn_detail_ui('Host Route')
        self.webui.logger.debug("Step 2 : Verify the host route in WebUI")
        if not self.webui.verify_vn_after_edit_ui('Host Route', host_route, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify the host route in API server")
        if not self.webui.verify_vn_after_edit_api('Host Route', host_route, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for host route in OPS server")
        if not self.webui.verify_vn_after_edit_ops('Host Route', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Host Route which is added")
        if not self.webui_common.edit_vn_with_host_route('remove', 'pos', \
                                                         topo.host_prefix, topo.host_nexthop):
            self.webui.logger.debug('Editing network with host routes failed')
            result = result and False
        return result
    # end test3_6_edit_net_host_opt

    @preposttest_wrapper
    def test5_1_edit_net_host_opt_neg(self):
        ''' Test to edit the existing network by Invalid Host routes
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Add Host route with invalid route prefix and invalid next hop and save it.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.webui.logger.debug("Step 1 : Add Host Route under VN")
        assert self.webui_common.edit_vn_with_host_route('add', 'neg', topo.dns_ip, \
                                                         topo.host_nexthop), \
                                                         'Editing network with host routes failed \
                                                         as expected for negative scenario'
    # end test5_1_edit_net_host_opt_neg

    @preposttest_wrapper
    def test3_7_edit_net_adv_opt(self):
        ''' Test to edit the existing network by Advanced Options
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Select all the options under advanced option and save.
            3. Check that all the options under advanced option got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.vlan_id, topo.phy_net, topo.subnet_adv_option, topo.vn_disp_name]
        self.webui.logger.debug("Step 1 : Add advanced options under VN")
        index = self.webui_common.edit_vn_with_adv_option(1, 'pos-phy', opt_list)
        if not index:
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        uuid = self.webui_common.get_vn_detail_ui('UUID', index=index)
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', index=index)
        adv_option = self.webui_common.get_vn_detail_ui('Adv Option', index=index)
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('Adv Option', adv_option, opt_list, index=index):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('Adv Option', adv_option, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('Adv Option', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   vn_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    # end test3_7_edit_net_adv_opt

    @preposttest_wrapper
    def test5_2_edit_net_adv_opt_neg(self):
        ''' Test to edit the existing network by Invalid physical network
            and invalid vlan id under Advanced option
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Select all the options under advanced option and give
               invalid physical network and invalid vlan and save it.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add advanced options under VN")
        opt_list = [topo.vlan_id, topo.phy_net, topo.subnet_adv_option, topo.vn_disp_name]
        index = self.webui_common.edit_vn_with_adv_option(1, 'pos-phy', opt_list)
        if not index:
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        self.webui.logger.debug("Step 2 : Edit the vn using advanced options")
        opt_list_invalid = [topo.invalid_vlan_id, topo.phy_net, topo.subnet_edit, topo.vn_disp_name]
        if not self.webui_common.edit_vn_with_adv_option(0, 'neg-phy', opt_list_invalid):
            self.webui.logger.debug('Editing network with advanced option is failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   vn_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    # end test5_2_edit_net_adv_opt_neg

    @preposttest_wrapper
    def test3_8_edit_net_dns(self):
        ''' Test to edit the existing network by DNS
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add dns IP under DNS Server.
            3. Check that dns Ip got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.dns_ip]
        self.webui.logger.debug("Step 1 : Add dns server IP under VN")
        if not self.webui_common.edit_vn_with_dns('add', 'pos', topo.dns_ip):
            self.webui.logger.debug('Editing network with dns is failed')
            result = result and False
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        dns = self.webui_common.get_vn_detail_ui('DNS')
        self.webui.logger.debug("Step 2 : Verify the DNS server IP in WebUI")
        if not self.webui.verify_vn_after_edit_ui('DNS', dns, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify DNS server IP in API server")
        if not self.webui.verify_vn_after_edit_api('DNS', dns, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for DNS server IP in OPS server")
        if not self.webui.verify_vn_after_edit_ops('DNS', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the VN which is added")
        if not self.webui_common.edit_vn_with_dns('remove', 'pos', topo.dns_ip):
            self.webui.logger.debug('Editing network with dns is failed')
            result = result and False
        return result
    # end test3_8_edit_net_dns

    @preposttest_wrapper
    def test3_9_edit_net_dns_neg(self):
        ''' Test to edit the existing network by DNS
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add Invalid dns IP under DNS Server.
            3. WebUI should thrown an error message while saving

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Add dns server IP under VN")
        assert self.webui_common.edit_vn_with_dns('add', 'neg', topo.invalid_dns_ip), \
                                                  'Editing network with dns is failed'
    # end test3_9_edit_dns_neg

    @preposttest_wrapper
    def test4_1_edit_net_fip(self):
        ''' Test to edit the existing network by Floating IP
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add Pool name and project name under Floating IP.
            3. Check that pool and project name got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.fpool]
        self.webui.logger.debug("Step 1 : Add Floating server IP under VN")
        if not self.webui_common.edit_vn_with_fpool('add', topo.fpool):
            self.webui.logger.debug('Editing network with FIP is failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        fip = self.webui_common.get_vn_detail_ui('FIP')
        self.webui.logger.debug("Step 2 : Verify the Floating IP in WebUI")
        if not self.webui.verify_vn_after_edit_ui('FIP', fip, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify Floating IP in API server")
        if not self.webui.verify_vn_after_edit_api('FIP', fip, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for Floating IP in OPS server")
        if not self.webui.verify_vn_after_edit_ops('FIP', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the FIP which is added")
        if not self.webui_common.edit_vn_with_fpool('remove', topo.fpool):
            self.webui.logger.debug('Editing network with FIP is failed')
            result = result and False
        return result
    # end test4_1_edit_net_fip

    @preposttest_wrapper
    def test4_2_edit_net_route_target_asn_num(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add ASN number and Target number under Route Target.
            3. Check the asn and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'RT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        rt = self.webui_common.get_vn_detail_ui('RT')
        self.webui.logger.debug("Step 2 : Verify the Route Target in WebUI")
        if not self.webui.verify_vn_after_edit_ui('RT', rt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('RT', rt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for n in OPS server")
        if not self.webui.verify_vn_after_edit_ops('RT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'RT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Route Target is failed')
            result = result and False
        return result
    # end test4_2_edit_net_route_target_asn_num

    @preposttest_wrapper
    def test4_3_edit_net_route_target_asn_ip(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'RT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        rt = self.webui_common.get_vn_detail_ui('RT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('RT', rt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('RT', rt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('RT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'RT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Route Target is failed')
            result = result and False
        return result
    # end test4_3_edit_net_route_target_asn_ip

    @preposttest_wrapper
    def test5_3_edit_net_route_target_neg_asn_ip(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'RT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with Route \
                                                           target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_3_edit_net_route_target_neg_asn_ip

    @preposttest_wrapper
    def test5_4_edit_net_route_target_neg_asn_num(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'RT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_4_edit_net_route_target_neg_asn_num

    @preposttest_wrapper
    def test5_5_edit_net_exp_route_target_asn_num(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add asn number and Target number under Export Route Target.
            3. Check the asn number and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'ERT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        ert = self.webui_common.get_vn_detail_ui('ERT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('ERT', ert, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('ERT', ert, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('ERT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'ERT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route Target is failed')
            result = result and False
        return result
    # end test5_5_edit_net_exp_route_target_asn_num

    @preposttest_wrapper
    def test4_4_edit_net_exp_route_target_asn_ip(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Export Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'ERT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        ert = self.webui_common.get_vn_detail_ui('ERT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('ERT', ert, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('ERT', ert, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('ERT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Export Route which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'ERT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route Target is failed')
            result = result and False
        return result
    # end test4_4_edit_net_exp_route_target_asn_ip

    @preposttest_wrapper
    def test5_6_edit_net_exp_route_target_neg_asn_ip(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Target number under Export Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'ERT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Export Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_6_edit_net_exp_route_target_neg_asn_ip

    @preposttest_wrapper
    def test5_8_edit_net_exp_route_target_neg_asn_num(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Export Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'ERT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Export Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_8_edit_net_exp_route_target_neg_asn_num

    @preposttest_wrapper
    def test4_5_edit_net_imp_route_target_asn_num(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add asn and Target number under Import Route Target.
            3. Check the asn and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count  = count + 1
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'IRT', \
                                                           topo.asn_num, topo.target_num, \
                                                           count=count):
            self.webui.logger.debug('Editing network with import Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        irt = self.webui_common.get_vn_detail_ui('IRT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('IRT', irt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('IRT', irt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('IRT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Import Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', \
                                                           'IRT', topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Import Route Target is failed')
            result = result and False
        return result
    # end test4_5_edit_net_imp_route_target_asn_num

    @preposttest_wrapper
    def test4_6_edit_net_imp_route_target_asn_ip(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Import Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count = count + 1
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        self.webui_common.wait_till_ajax_done(self.browser)
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'IRT', \
                                                           topo.asn_ip, topo.target_num, \
                                                           count=count):
            self.webui.logger.debug('Editing network with Import Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        irt = self.webui_common.get_vn_detail_ui('IRT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('IRT', irt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('IRT', irt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('IRT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Import Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'IRT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Import Route Target is failed')
            result = result and False
        return result
    # end test4_6_edit_net_route_target_asn_ip

    @preposttest_wrapper
    def test5_7_negative_case_edit_net_with_invalid_route_target_ip(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Import Target number under Import Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count += 1
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'IRT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num, \
                                                           count=count), \
                                                           'Editing network with \
                                                           Import Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_7_negative_case_edit_net_with_invalid_route_target_ip

    @preposttest_wrapper
    def test5_9_negative_case_edit_net_with_invalid_route_target_num(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Target number under Import Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count += 1
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'IRT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num, \
                                                           count=count), \
                                                           'Editing network with \
                                                           Import Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_9_negative_case_edit_net_with_invalid_route_target_num

    @preposttest_wrapper
    def test4_7_create_vn_with_spl_char(self):
        ''' Test to create vn with combination of spl char and verify in all API, OPS and WebUI
            1. Go to Configure->Networking->Networks. Then create VN with all
               combination of spl characters
            2. Verify the VN in WebUI, OPS and API server.

            Pass Criteria : Step 2 should pass
        '''
        vn_list = [topo.vn_name_beg_spl_char, topo.vn_name_end_spl_char, topo.vn_name_mid_spl_char]
        opt_list = []
        result = True
        for vn in vn_list:
            self.webui.logger.debug("Step 1 : Create vn %s " %(vn))
            if self.webui_common.click_configure_networks():
                add = self.webui_common.find_element("//i[contains(@class,'icon-plus')]", 'xpath')
                add.click()
                self.webui_common.wait_till_ajax_done(self.browser, wait=3)
                self.webui_common.find_element("//input[contains(@name,'display_name')]", \
                                               'xpath').send_keys(vn)
                self.webui_common.wait_till_ajax_done(self.browser, wait=3)
                self.webui_common.click_element('configure-networkbtn1')
                self.webui_common.wait_till_ajax_done(self.browser)
                uuid = self.webui_common.get_vn_detail_ui('UUID', vn_name='vn1')
                self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', \
                                                                      vn_name='vn1')
                self.webui.logger.debug("Step 2 : Verify WebUI server after editing")
                if not self.webui.verify_vn_after_edit_ui('Display Name', vn, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in UI failed')
                    result = result and False
                self.webui.logger.debug("Step 3 : Verify API server after editing")
                if not self.webui.verify_vn_after_edit_api('Display Name', vn, uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in API failed')
                    result = result and False
                self.webui.logger.debug("Step 4 : Verify OPS server after editing")
                if not self.webui.verify_vn_after_edit_ops('Display Name', vn, vn, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in OPS failed')
                    result = result and False
                self.webui.logger.debug("Step 5 : Remove the VN which is added")
                if not self.webui_common.edit_remove_option("Networks", 'remove', vn_name='vn1'):
                    self.webui.logger.debug('Editing network with advanced options is failed')
                    result = result and False
        return result
    # test4_7_create_vn_with_spl_char

# end WebuiTestSanity
