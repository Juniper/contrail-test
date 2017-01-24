from webui.webui_common import *
import re

class WebuiEdit:

    def __init__(self, obj):
        self.inputs = obj.inputs
        self.connections = obj.connections
        self.browser = obj.browser
        self.logger = self.inputs.logger
        self.browser_openstack = self.connections.browser_openstack
        self.ui = WebuiCommon(self)
    # end __init__

    def edit_port_with_vn_port(self, option):
        result = True
        try:
            self.edit_port_result = self.ui.edit_remove_option(option, 'edit')
            if self.edit_port_result:
                vn_drop = self.ui.find_element('virtualNetworkName_dropdown')
                mode = vn_drop.get_attribute('data-bind')
                vn_out = re.search('disable: true', mode)
                port_disp_name = self.ui.find_element('display_name', 'name')
                port_mode = port_disp_name.get_attribute('data-bind')
                port_out = re.search('disable: true', port_mode)
                if vn_out and port_out:
                    self.logger.info("Editing is failed for vn and port name as expected")
                else:
                    self.logger.error("Clicking the Edit Button is not working")
                    result = result and False
            else:
                self.logger.error("There are no rows to edit")
                result = result and False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            raise
        self.ui.click_on_cancel_if_failure('cancelBtn')
        return result
    # edit_port_with_vn_port

    def edit_port_with_sec_group(self, option, port_name, **kwargs):
        result = True
        try:
            self.edit_port_result = self.ui.edit_remove_option(option, 'edit',
                                                           display_name=port_name)
            sg_list = kwargs.get('sg_list')
            if self.edit_port_result:
                for sg in sg_list:
                    self.ui.click_element('s2id_securityGroupValue_dropdown')
                    if not self.ui.select_from_dropdown(sg, grep=False):
                        result = result and False
                    self.ui.wait_till_ajax_done(self.browser, wait=3)
                self.ui.click_on_create(option.strip('s'),
                                    option.strip('s').lower(), save=True)
                self.ui.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            self.ui.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_port_with_sec_group

    def edit_port_with_advanced_option(self, option, port_name, **kwargs):
        result = True
        try:
            self.edit_port_result = self.ui.edit_remove_option(option, 'edit',
                                        display_name=port_name)
            port_admin_state = kwargs.get('port_admin_state', 'Up')
            params_list = kwargs.get('params_list', None)
            subnet = kwargs.get('subnet', True)
            allowed_address_pair = kwargs.get('allowed_address_pair', True)
            ecmp = kwargs.get('ecmp', True)
            mirror = kwargs.get('mirror', True)
            mirror_enabled_already = kwargs.get('mirror_enabled_already', False)
            header_mode = kwargs.get('header_mode', 'Enabled')
            traffic_direction = kwargs.get('traffic_direction', 'Both')
            next_hop_mode = kwargs.get('next_hop_mode', 'Dynamic')
            tc = kwargs.get('tc', 'positive')
            if self.edit_port_result:
                self.ui.click_element('advanced_options')
                mac_address = self.ui.find_element('macAddress', 'name')
                mode = mac_address.get_attribute('data-bind')
                mac_out = re.search('disable: true', mode)
                if not mac_out:
                    result = result and False
                self.ui.click_element('s2id_enable_dropdown')
                if not self.ui.select_from_dropdown(port_admin_state, grep=False):
                    result = result and False
                add_value = self.ui.find_element('editable-grid-add-link', 'class',
                                elements=True)
                combobox = self.ui.find_element('custom-combobox-input', 'class',
                               elements=True)
                if subnet:
                    add_value[0].click()
                    subnet_grid = self.ui.find_element('data-row', 'class', elements=True)
                    self.ui.click_element('s2id_subnet_uuid_dropdown', browser=subnet_grid[1])
                    if not self.ui.select_from_dropdown(params_list[0], grep=False):
                        result = result and False
                    self.ui.send_keys(params_list[9], 'fixedIp', 'name', browser=subnet_grid[1],
                        clear=True)
                    combobox[0].send_keys('100')
                if allowed_address_pair:
                    add_value[1].click()
                    self.ui.send_keys(params_list[8], 'ipPrefixVal', 'name', clear=True)
                    self.ui.send_keys(params_list[6], 'mac', 'name', clear=True)
                if ecmp:
                    self.ui.click_element('s2id_ecmpHashingIncFields_dropdown')
                    if not self.ui.select_from_dropdown('destination-ip', grep=False):
                        result = result and False
                combo_state = combobox[1].get_attribute('disabled')
                if not combo_state:
                    result = result and False
                if not mirror_enabled_already:
                    self.ui.click_element('virtual_machine_interface_disable_policy', 'name')
                    self.ui.click_element('is_mirror', 'name')
                if mirror:
                    self.ui.send_keys(params_list[5], 'analyzer_ip_address', 'name', clear=True)
                    self.ui.send_keys(params_list[10], 'udp_port', 'name', clear=True)
                    self.ui.send_keys(params_list[1], 'analyzer_name', 'name', clear=True)
                    self.ui.click_element('s2id_mirrorToRoutingInstance_dropdown')
                    self.ui.click_element('select2-highlighted', 'class')
                    self.ui.send_keys(params_list[2], 'analyzer_mac_address', 'name', clear=True)
                    self.ui.click_element('s2id_juniper_header_dropdown')
                    if not self.ui.select_from_dropdown(header_mode, grep=False):
                        result = result and False
                    self.ui.click_element('s2id_traffic_direction_dropdown')
                    if not self.ui.select_from_dropdown(traffic_direction, grep=False):
                        result = result and False
                    self.ui.click_element('s2id_mirrorToNHMode_dropdown')
                    if self.ui.select_from_dropdown(next_hop_mode, grep=False):
                        if next_hop_mode == 'Static':
                           self.ui.send_keys(params_list[7], 'vtep_dst_ip_address',
                                         'name', clear=True)
                           self.ui.send_keys(params_list[3], 'vtep_dst_mac_address',
                                         'name', clear=True)
                           self.ui.send_keys(params_list[4], 'vni', 'name', clear=True)
                    else:
                        result = result and False
                self.ui.click_on_create(option.strip('s'),
                                    option.strip('s').lower(), save=True)
                if tc != 'positive':
                    result = self.ui.negative_test_proc(option)
                self.ui.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("There are no rows to edit")
                result = result and False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            raise
        self.ui.click_on_cancel_if_failure('cancelBtn')
        return result
    # edit_port_with_advanced_option

    def edit_port_with_dhcp_option(self, option, port_name, **kwargs):
        result = True
        try:
            self.edit_port_result = self.ui.edit_remove_option(option, 'edit',
                                                           display_name=port_name)
            dhcp_option = kwargs.get('dhcp_option')
            if self.edit_port_result:
                self.ui.click_element('dhcpOptionsAccordion')
                self.ui.wait_till_ajax_done(self.browser)
                self.ui.click_element('editable-grid-add-link', 'class',
                                  elements=True, index=3)
                self.ui.send_keys(dhcp_option[0], 'dhcp_option_name', 'name', clear=True)
                self.ui.send_keys(dhcp_option[1], 'dhcp_option_value', 'name', clear=True)
                self.ui.send_keys(int(dhcp_option[1])/8, 'dhcp_option_value_bytes',
                              'name', clear=True)
                self.ui.click_on_create(option.strip('s'),
                                    option.strip('s').lower(), save=True)
                self.ui.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            self.ui.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_port_with_dhcp_option

    def edit_port_with_fat_flow(self, option, port_name, **kwargs):
        result = True
        try:
            self.edit_port_result = self.ui.edit_remove_option(option, 'edit',
                                                           display_name=port_name)
            fat_flow_values = kwargs.get('fat_flow_values')
            tc = kwargs.get('tc', 'positive')
            if self.edit_port_result:
                self.ui.click_element('fatFlowAccordion')
                self.ui.wait_till_ajax_done(self.browser)
                fat_flow_protocol_list = fat_flow_values.keys()
                fat_flow_port_list = fat_flow_values.values()
                for protocol in range(len(fat_flow_protocol_list)):
                    self.ui.click_element('editable-grid-add-link', 'class',
                                      elements=True, index=4)
                    fat_flow = self.ui.find_element('fatFlowCollection')
                    fat_flow_tuple = self.ui.find_element('data-row', 'class',
                                     browser=fat_flow, elements=True)
                    self.ui.click_element('s2id_protocol_dropdown',
                                      browser=fat_flow_tuple[protocol])
                    if not self.ui.select_from_dropdown(fat_flow_protocol_list[protocol],
                                                    grep=False):
                        result = result and False
                    if fat_flow_protocol_list[protocol] == 'ICMP':
                        port = self.ui.find_element('port', 'name')
                        mode = port.get_attribute('data-bind')
                        vn_out = re.search('disable: true', mode)
                    else:
                        self.ui.send_keys(fat_flow_port_list[protocol], 'port', 'name',
                                      browser=fat_flow_tuple[protocol])
                self.ui.click_on_create(option.strip('s'),
                                    option.strip('s').lower(), save=True)
                if tc != 'positive':
                    result = self.ui.negative_test_proc(option)
                self.ui.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            self.ui.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_port_with_fat_flow

    def edit_global_config_forwarding_option(self, paramater_list, **kwargs):
        result = True
        try:
            default = kwargs.get('default', True)
            tc = kwargs.get('tc', 'positive')
            if not self.ui.click_configure_global_config():
                result = result and False
            self.ui.click_element('fa-pencil-square-o', 'class')
            self.ui.click_element('s2id_forwarding_mode_dropdown')
            if not self.ui.select_from_dropdown(paramater_list[0], grep=False):
                result = result and False
            flow_rate = '' if default else paramater_list[1]
            self.ui.send_keys(flow_rate, 'flow_export_rate', 'name', clear=True)
            self.ui.click_element('vxlan_network_identifier_mode')
            config_mode = 'automatic' if default else 'configured'
            config_mode_xpath = "//input[contains(@value, '" + config_mode + "')]"
            self.ui.click_element(config_mode_xpath, 'xpath')
            self.ui.click_element('configure-global_forwarding_optionsbtn1')
            self.ui.wait_till_ajax_done(self.browser)
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            self.ui.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_global_config_forwarding_option

    def edit_global_config_bgp_option(self, parameter_list, **kwargs):
        result = True
        try:
            default = kwargs.get('default', True)
            tc = kwargs.get('tc', 'positive')
            grace_restart = kwargs.get('grace_restart', True)
            subnet = kwargs.get('subnet', True)
            if not self.ui.click_configure_global_config():
                result = result and False
            self.ui.click_element('bgp_options_tab-tab-link')
            self.ui.click_element('fa-pencil-square-o', 'class', elements=True, index=1)
            self.ui.send_keys(parameter_list[0], 'autonomous_system', 'name', clear=True)
            self.ui.click_element('ibgp_auto_mesh', 'name')
            if grace_restart:
                self.ui.click_element('graceful_restart_enable', 'name')
            if not default:
                self.ui.click_element('s2id_bgp_helper_enable_dropdown')
                if not self.ui.select_from_dropdown(parameter_list[1], grep=False):
                   result = result and False
                self.ui.send_keys(parameter_list[2], 'restart_time', 'name', clear=True)
                self.ui.send_keys(parameter_list[3], 'long_lived_restart_time', 'name',
                                 clear=True)
                self.ui.send_keys(parameter_list[4], 'end_of_rib_timeout', 'name',
                                 clear=True)
                if subnet:
                    self.ui.click_element('editable-grid-add-link', 'class')
                    self.ui.send_keys(parameter_list[5], 'ip_fabric_subnets', 'name', clear=True)
            else:
                self.ui.click_element('fa-minus', 'class')
            self.ui.click_element('configure-global_bgp_optionsbtn1')
            if tc != 'positive':
                result = self.ui.negative_test_proc('global_bgp_options')
            self.ui.wait_till_ajax_done(self.browser)
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.ui.screenshot(option)
            result = result and False
            self.ui.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_global_config_bgp_option
