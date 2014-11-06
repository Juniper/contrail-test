from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
import time
import random
import fixtures
from ipam_test import *
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from contrail_fixtures import *
from webui.webui_common import WebuiCommon
import re

class WebuiTest:

    os_release = None
    def __init__(self, connections, inputs):
        self.inputs = inputs
        self.connections = connections
        self.logger = self.inputs.logger
        self.browser = self.connections.browser
        self.browser_openstack = self.connections.browser_openstack
        self.delay = 20
        self.frequency = 3
        self.logger = inputs.logger
        self.ui = WebuiCommon(self)
        self.dash = "-" * 60
        self.vnc_lib = connections.vnc_lib_fixture
        self.log_path = None
        if not WebuiTest.os_release:
            WebuiTest.os_release = self.inputs.get_openstack_release()
    # end __init__

    def _click_if_element_found(self, element_name, elements_list):
        for element in elements_list:
            if element.text == element_name:
                element.click()
                break
    # end _click_if_element_found

    def create_vn(self, fixture):
        result = True
        try:
            fixture.obj = fixture.quantum_fixture.get_vn_obj_if_present(
                fixture.vn_name, fixture.project_id)
            if not fixture.obj:
                self.logger.info("Creating vn %s using webui..." %
                                 (fixture.vn_name))
                if not self.ui.click_configure_networks():
                    result = result and False
                self.ui.select_project(fixture.project_name)
                self.ui.click_element('btnCreateVN')
                self.ui.wait_till_ajax_done(self.browser)
                txtVNName = self.ui.find_element('txtDisName')
                txtVNName.send_keys(fixture.vn_name)
                if isinstance(fixture.vn_subnets, list):
                    for subnet in fixture.vn_subnets:
                        self.ui.click_element('btnCommonAddIpam')
                        self.ui.wait_till_ajax_done(self.browser)
                        self.ui.click_element(
                            ['ipamTuples', 'select2-choice'], ['id', 'class'], jquery=False, wait=3)
                        ipam_list = self.ui.find_element(
                            ['select2-drop', 'li'], ['id', 'tag'], if_elements=[1])
                        for ipam in ipam_list:
                            ipam_text = self.ui.find_element(
                                'div',
                                'tag',
                                ipam).text
                            if ipam_text.find(fixture.ipam_fq_name[2]) != -1:
                                ipam.click()
                                break
                        self.ui.send_keys(
                            subnet['cidr'],
                            "//input[@placeholder = 'CIDR']",
                            'xpath')
                else:
                    self.ui.click_element('btnCommonAddIpam')
                    self.ui.click_element('select2-drop-mask')
                    ipam_list = self.ui.find_element(
                        ['select2-drop', 'ul', 'li'], ['id', 'tag', 'tag'], if_elements=[2])
                    for ipam in ipam_list:
                        ipam_text = ipam.get_attribute("innerHTML")
                        if ipam_text == self.ipam_fq_name:
                            ipam.click()
                            break
                    self.ui.send_keys(
                        fixture.vn_subnets,
                        "//input[@placeholder = 'IP Block']",
                        'xpath')
                self.ui.click_element('btnCreateVNOK')
                time.sleep(3)
                if not self.ui.check_error_msg("create VN"):
                    raise Exception("vn creation failed")
            else:
                fixture.already_present = True
                self.logger.info('VN %s already exists, skipping creation ' %
                                 (fixture.vn_name))
                self.logger.debug('VN %s exists, already there' %
                                  (fixture.vn_name))
            fixture.obj = fixture.quantum_fixture.get_vn_obj_if_present(
                fixture.vn_name, fixture.project_id)
            fixture.vn_id = fixture.obj['network']['id']
            fixture.vn_fq_name = ':'.join(self.vnc_lib.id_to_fq_name(
                fixture.obj['network']['id']))
        except WebDriverException:
            self.logger.error("Error while creating %s" % (fixture.vn_name))
            self.ui.screenshot("vn_error")
            raise
    # end create_vn_in_webui

    def create_dns_server(self):
        ass_ipam_list = ['ipam1', 'ipam_1']
        if not self.ui.click_configure_dns_server():
            result = result and False
        self.ui.click_element('btnCreateDNSServer')
        self.ui.send_keys('server1', 'txtDNSServerName')
        self.ui.send_keys('domain1', 'txtDomainName')
        self.browser.find_elements_by_class_name(
            'control-group')[2].find_element_by_tag_name('i').click()
        options = self.ui.find_element(
            ['ui-autocomplete', 'li'], ['class', 'tag'], if_elements=[1])
        for i in range(len(options)):
            if (options[i].find_element_by_tag_name(
                    'a').text == 'default-domain:dnss'):
                options[i].click()
                time.sleep(2)
        self.ui.click_element(['s2id_ddLoadBal', 'a'], ['id', 'tag'])
        rro_list = self.ui.find_element(
            ['select2-drop', 'li'], ['id', 'tag'], if_elements=[1])
        rro_opt_list = [element.find_element_by_tag_name('div')
                        for element in rro_list]
        for rros in rro_opt_list:
            rros_text = rros.text
            if rros_text == 'Round-Robin':
                rros.click()
                break
        self.ui.send_keys('300', 'txtTimeLive')
        for ipam in range(len(ass_ipam_list)):
            self.browser.find_element_by_id(
                's2id_msIPams').find_element_by_tag_name('input').click()
            ipam_list = self.browser.find_element_by_id(
                'select2-drop').find_element_by_class_name('select2-results').find_elements_by_tag_name('li')
            ipam_opt_list = [element.find_element_by_tag_name('div')
                             for element in ipam_list]
            for ipams in ipam_opt_list:
                ipams_text = ipams.text
                if ipams_text == 'admin:' + ass_ipam_list[ipam]:
                    ipams.click()
                    break
        self.ui.click_element('btnCreateDNSServerOK')
        if not self.ui.check_error_msg("create DNS"):
            raise Exception("DNS creation failed")
        # end create_dns_server

    def create_dns_record(self):
        if not self.ui.click_configure_dns_record():
            result = result and False
        self.ui.click_element('btnCreateDNSRecord')
        self.ui.click_element(['s2id_cmbRecordType', 'a'], ['id', 'tag'])
        type_list = self.browser.find_element_by_id(
            'select2-drop').find_elements_by_tag_name('li')
        type_opt_list = [element.find_element_by_tag_name('div')
                         for element in type_list]
        for types in type_opt_list:
            types_text = types.text
            if types_text == 'NS (Delegation Record)':
                types.click()
                if types_text == 'CNAME (Alias Record)':
                    self.browser.find_element_by_id(
                        'txtRecordName').send_keys('abc')
                    self.browser.find_element_by_id(
                        'txtRecordData').send_keys('bcd')
                if types_text == 'A (IP Address Record)':
                    self.browser.find_element_by_id(
                        'txtRecordName').send_keys('abc')
                    self.browser.find_element_by_id(
                        'txtRecordData').send_keys('189.32.3.2/21')
                if types_text == 'PTR (Reverse DNS Record)':
                    self.browser.find_element_by_id(
                        'txtRecordName').send_keys('187.23.2.1/27')
                    self.browser.find_element_by_id(
                        'txtRecordData').send_keys('bcd')
                if types_text == 'NS (Delegation Record)':
                    self.browser.find_element_by_id(
                        'txtRecordName').send_keys('abc')
                    self.browser.find_elements_by_class_name(
                        'control-group')[2].find_element_by_tag_name('i').click()
                    dns_servers = self.browser.find_element_by_class_name(
                        'ui-autocomplete').find_elements_by_tag_name('li')
                    for servers in range(len(dns_servers)):
                        if dns_servers[servers].find_element_by_tag_name(
                                'a').text == 'default-domain:' + 'dns2':
                            dns_servers[servers].find_element_by_tag_name(
                                'a').click()
                            break
                break
        self.browser.find_element_by_id(
            's2id_cmbRecordClass').find_element_by_tag_name('a').click()
        class_list = self.browser.find_element_by_id(
            'select2-drop').find_elements_by_tag_name('li')
        class_opt_list = [element.find_element_by_tag_name('div')
                          for element in class_list]
        for classes in class_opt_list:
            classes_text = classes.text
            if classes_text == 'IN (Internet)':
                classes.click()
                break
        self.browser.find_element_by_id('txtRecordTTL').send_keys('300')
        self.browser.find_element_by_id('btnAddDNSRecordOk').click()
        if not self.ui.check_error_msg("create DNS Record"):
            raise Exception("DNS Record creation failed")
        # end create_dns_record

    def create_svc_template(self, fixture):
        result = True
        if not self.ui.click_configure_service_template():
            result = result and False
        self.logger.info("Creating svc template %s using webui" %
                         (fixture.st_name))
        self.ui.click_element('btnCreatesvcTemplate')
        self.ui.wait_till_ajax_done(self.browser)
        txt_temp_name = self.ui.find_element('txtTempName')
        txt_temp_name.send_keys(fixture.st_name)
        self.browser.find_element_by_id(
            's2id_ddserMode').find_element_by_class_name('select2-choice').click()
        service_mode_list = self.browser.find_element_by_id(
            "select2-drop").find_elements_by_tag_name('li')
        for service_mode in service_mode_list:
            service_mode_text = service_mode.text
            if service_mode_text.lower() == fixture.svc_mode:
                service_mode.click()
                break
        self.browser.find_element_by_id(
            's2id_ddserType').find_element_by_class_name('select2-choice').click()
        service_type_list = self.browser.find_element_by_id(
            "select2-drop").find_elements_by_tag_name('li')
        for service_type in service_type_list:
            service_type_text = service_type.text
            if service_type_text.lower() == fixture.svc_type:
                service_type.click()
                break
        self.browser.find_element_by_id(
            's2id_ddImageName').find_element_by_class_name('select2-choice').click()
        image_name_list = self.browser.find_element_by_id(
            "select2-drop").find_elements_by_tag_name('li')
        for image_name in image_name_list:
            image_name_text = image_name.text
            if image_name_text.lower() == fixture.image_name:
                image_name.click()
                break
        static_route = self.browser.find_element_by_id(
            'widgetStaticRoutes').find_element_by_tag_name('i').click()
        for index, intf_element in enumerate(fixture.if_list):
            intf_text = intf_element[0]
            shared_ip = intf_element[1]
            static_routes = intf_element[2]
            self.browser.find_element_by_id('btnCommonAddInterface').click()
            self.browser.find_element_by_id(
                'allInterface').find_elements_by_tag_name('i')[index * 3].click()
            if shared_ip:
                self.browser.find_element_by_id('allInterface').find_elements_by_tag_name(
                    'input')[index * 3 + 1].click()
            if static_routes:
                self.browser.find_element_by_id(
                    'allInterface').find_elements_by_tag_name('i')[index * 3 + 2].click()
            intf_types = self.browser.find_elements_by_class_name(
                'ui-autocomplete')[index].find_elements_by_class_name('ui-menu-item')
            intf_dropdown = [element.find_element_by_tag_name('a')
                             for element in intf_types]
            for intf in intf_dropdown:
                if intf.text.lower() == intf_text:
                    intf.click()
                    break
        self.browser.find_element_by_id(
            's2id_ddFlavors').find_element_by_class_name('select2-choice').click()
        flavors_list = self.browser.find_elements_by_xpath(
            "//span[@class = 'select2-match']/..")
        for flavor in flavors_list:
            flavor_text = flavor.text
            if flavor_text.find(fixture.flavor) != -1:
                flavor.click()
                break
        if fixture.svc_scaling:
            self.browser.find_element_by_id('chkServiceEnabeling').click()
        self.browser.find_element_by_id('btnCreateSTempOK').click()
        time.sleep(3)
        if not self.ui.check_error_msg("create service template"):
            raise Exception("service template creation failed")
    # end create_svc_template

    def create_svc_instance(self, fixture):
        result = True
        if not self.ui.click_configure_service_instance():
            result = result and False
        self.ui.select_project(fixture.project_name)
        self.logger.info("Creating svc instance %s using webui" %
                         (fixture.si_name))
        self.ui.click_element('btnCreatesvcInstances')
        self.ui.wait_till_ajax_done(self.browser)
        txt_instance_name = self.ui.find_element('txtsvcInstanceName')
        txt_instance_name.send_keys(fixture.si_name)
        self.browser.find_element_by_id(
            's2id_ddsvcTemplate').find_element_by_class_name('select2-choice').click()
        service_template_list = self.browser.find_element_by_id(
            'select2-drop').find_elements_by_tag_name('li')
        service_temp_list = [
            element.find_element_by_tag_name('div') for element in service_template_list]
        for service_temp in service_temp_list:
            service_temp_text = service_temp.text
            if service_temp_text.find(fixture.st_name) != -1:
                service_temp.click()
                break
        intfs = self.browser.find_element_by_id(
            'instanceDiv').find_elements_by_tag_name('a')
        self.browser.find_element_by_id('btnCreatesvcInstencesOK').click()
        time.sleep(3)
        if not self.ui.check_error_msg("create service instance"):
            raise Exception("service instance creation failed")
        time.sleep(40)
    # end create_svc_instance

    def create_ipam(self, fixture):
        result = True
        ip_blocks = False
        if not self.ui.click_configure_ipam():
            result = result and False
        self.ui.select_project(fixture.project_name)
        self.logger.info("Creating ipam %s using webui" % (fixture.name))
        self.ui.click_element('btnCreateEditipam')
        self.ui.send_keys(fixture.name, 'txtIPAMName')
        '''
        self.browser.find_element_by_id('s2id_ddDNS').find_element_by_class_name('select2-choice').click()
        dns_method_list = self.browser.find_element_by_id('select2-drop').find_elements_by_tag_name('li')
        dns_list = [ element.find_element_by_tag_name('div') for element in dns_method_list]
        
        for dns in dns_list :
            dns_text = dns.text
            if dns_text.find('Tenant') != -1 :
                dns.click()
                if dns_text == 'Tenant':
                    self.browser.find_element_by_id('txtdnsTenant').send_keys('189.23.2.3/21')
                    self.browser.find_element_by_id("txtNTPServer").send_keys('32.24.53.45/28')
                    self.browser.find_element_by_id("txtDomainName").send_keys('domain_1')
                elif dns_text == 'Default' or dns.text == 'None':
                    self.browser.find_element_by_id("txtNTPServer").send_keys('32.24.53.45/28')
                    self.browser.find_element_by_id("txtDomainName").send_keys('domain_1')
                elif dns_text == 'Virtual DNS':
                    self.browser.find_element_by_id('dnsvirtualBlock').find_element_by_tag_name('a').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    virtual_dns_list = self.browser.find_element_by_id('select2-drop').find_elements_by_tag_name('li')
                    vdns_list = [ element.find_element_by_tag_name('div') for element in virtual_dns_list]
                    for vdns in vdns_list :
                        vdns_text = vdns.text
                        if vdns_text ==  'default-domain:'+'dns':
                            vdns.click()
                            break
                break
        for net in range(len(net_list)):
            self.browser.find_element_by_id("btnCommonAddVN").click()
            self.browser.find_element_by_id('vnTuples').find_element_by_tag_name('a').click()
            self.ui.wait_till_ajax_done(self.browser)
            vn_list = self.browser.find_element_by_id('select2-drop').find_elements_by_tag_name('li')
            virtual_net_list = [ element.find_element_by_tag_name('div') for element in vn_list]
            for vns in virtual_net_list :
                vn_text = vns.text
                if vn_text ==  net_list[net] :
                    vns.click()
                    break
            
            self.browser.find_element_by_xpath("//*[contains(@placeholder, 'IP Block')]").send_keys('187.23.2.'+str(net+1)+'/21')
            '''
        self.ui.click_element("btnCreateEditipamOK")
        if not self.ui.check_error_msg("Create ipam"):
            raise Exception("ipam creation failed")
        # end create_ipam

    def create_policy(self, fixture):
        result = True
        line = 0
        try:
            fixture.policy_obj = fixture.quantum_fixture.get_policy_if_present(
                fixture.project_name, fixture.policy_name)
            if not fixture.policy_obj:
                self.logger.info("Creating policy %s using webui" %
                                 (fixture.policy_name))
                if not self.ui.click_configure_policies():
                    result = result and False
                self.ui.select_project(fixture.project_name)
                self.ui.click_element('btnCreatePolicy')
                self.ui.send_keys(fixture.policy_name, 'txtPolicyName')
                for index, rule in enumerate(fixture.rules_list):
                    action = rule['simple_action']
                    protocol = rule['protocol']
                    source_net = rule['source_network']
                    direction = rule['direction']
                    dest_net = rule['dest_network']
                    if rule['src_ports']:
                        if isinstance(rule['src_ports'], list):
                            src_port = ','.join(str(num)
                                                for num in rule['src_ports'])
                        else:
                            src_port = str(rule['src_ports'])
                    if rule['dst_ports']:
                        if isinstance(rule['dst_ports'], list):
                            dst_port = ','.join(str(num)
                                                for num in rule['dst_ports'])
                        else:
                            dst_port = str(rule['dst_ports'])
                    self.ui.click_element(
                        'btnCommonAddRule',
                        jquery=False,
                        wait=2)
                    rules = self.ui.find_element(
                        ['ruleTuples', 'rule-item'], ['id', 'class'], if_elements=[1])[line]
                    textbox_rule_items = self.ui.find_element(
                        'span1',
                        'class',
                        rules,
                        elements=True)
                    src_textbox_element = textbox_rule_items[
                        0].find_element_by_tag_name('input')
                    dst_textbox_element = textbox_rule_items[
                        2].find_element_by_tag_name('input')
                    src_textbox_element.clear()
                    src_textbox_element.send_keys(src_port)
                    dst_textbox_element.clear()
                    dst_textbox_element.send_keys(dst_port)
                    dropdown_rule_items = self.ui.find_element(
                        "div[class$='pull-left']",
                        'css',
                        rules,
                        elements=True)
                    self.ui.click_on_dropdown(dropdown_rule_items[3])
                    self.ui.select_from_dropdown(direction)
                    li = self.browser.find_elements_by_css_selector(
                        "ul[class^='ui-autocomplete']")
                    if len(li) == 4 and index == 0:
                        lists = 0
                    elif index == 0:
                        lists = 1
                    for item in range(len(dropdown_rule_items)):
                        if item == 3:
                            continue
                        self.ui.click_on_dropdown(dropdown_rule_items[item])
                        if item == 0:
                            self.ui.select_from_dropdown(action.upper())
                        elif item == 1:
                            self.ui.select_from_dropdown(protocol.upper())
                        elif item == 2:
                            self.ui.select_from_dropdown(source_net)
                        elif item == 4:
                            self.ui.select_from_dropdown(dest_net)
                    lists = lists + 1
                self.ui.click_element('btnCreatePolicyOK')
                if not self.ui.check_error_msg("Create Policy"):
                    raise Exception("Policy creation failed")
                fixture.policy_obj = fixture.quantum_fixture.get_policy_if_present(
                    fixture.project_name,
                    fixture.policy_name)
            else:
                fixture.already_present = True
                self.logger.info(
                    'Policy %s already exists, skipping creation ' %
                    (fixture.policy_name))
                self.logger.debug('Policy %s exists, already there' %
                                  (fixture.policy_name))
        except WebDriverException:
            self.logger.error(
                "Error while creating %s" %
                (fixture.policy_name))
            self.ui.screenshot("policy_create_error")
            raise
    # end create_policy_in_webui

    def verify_analytics_nodes_ops_basic_data(self):
        self.logger.info(
            "Verifying analytics node opserver basic data on Monitor->Infra->Analytics Nodes(Basic view) page.")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_analytics_nodes():
            result = result and False
        rows = self.ui.get_rows()
        analytics_nodes_list_ops = self.ui.get_collectors_list_ops()
        result = True
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in opserver..checking if exists in webui as well" %
                (ops_analytics_node_name))
            if not self.ui.click_monitor_analytics_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info(
                        "Analytics_node name %s found in webui...Verifying basic details" %
                        (ops_analytics_node_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Analytics node name %s not found in webui" %
                    (ops_analytics_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Verify analytics node basic view details for  \
                    analytics_node-name %s " % (ops_analytics_node_name))
                self.ui.click_monitor_analytics_nodes_basic(
                    match_index)
                dom_basic_view = self.ui.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status
                # filter analytics_node basic view details from opserver data
                analytics_nodes_ops_data = self.ui.get_details(
                    analytics_nodes_list_ops[n]['href'])
                ops_basic_data = []
                host_name = analytics_nodes_list_ops[n]['name']
                ip_address = analytics_nodes_ops_data.get(
                    'CollectorState').get('self_ip_list')
                ip_address = ', '.join(ip_address)
                generators_count = str(
                    len(analytics_nodes_ops_data.get('CollectorState').get('generator_infos')))
                version = json.loads(analytics_nodes_ops_data.get('CollectorState').get(
                    'build_info')).get('build-info')[0].get('build-id')
                version = self.ui.get_version_string(version)
                module_cpu_info_len = len(
                    analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                for i in range(module_cpu_info_len):
                    if analytics_nodes_ops_data.get('ModuleCpuState').get(
                            'module_cpu_info')[i]['module_id'] == 'contrail-collector':
                        cpu_mem_info_dict = analytics_nodes_ops_data.get(
                            'ModuleCpuState').get('module_cpu_info')[i]
                        break
                cpu = self.ui.get_cpu_string(cpu_mem_info_dict)
                memory = self.ui.get_memory_string(cpu_mem_info_dict)
                modified_ops_data = []

                process_state_list = analytics_nodes_ops_data.get(
                    'NodeStatus').get('process_info')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                redis_uve_string = None
                redis_query_string = None
                exclude_process_list = [
                    'contrail-config-nodemgr',
                    'contrail-analytics-nodemgr',
                    'contrail-control-nodemgr',
                    'contrail-vrouter-nodemgr',
                    'openstack-nova-compute',
                    'contrail-svc-monitor',
                    'contrail-discovery:0',
                    'contrail-zookeeper',
                    'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'redis-query':
                        redis_query_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-query-engine':
                        contrail_qe_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-analytics-nodemgr':
                        contrail_analytics_nodemgr_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'redis-uve':
                        redis_uve_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-analytics-api':
                        contrail_opserver_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-collector':
                        contrail_collector_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                reduced_process_keys_dict = {}
                for k, v in process_down_stop_time_dict.items():
                    if k not in exclude_process_list:
                        reduced_process_keys_dict[k] = v
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = min(process_up_start_time_dict.values())
                    overall_node_status_time = self.ui.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' +
                        status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.ui.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'

                modified_ops_data.extend(
                    [
                        {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'Generators', 'value': generators_count}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                                'key': 'Version', 'value': version}, {
                                    'key': 'Collector', 'value': contrail_collector_string}, {
                                        'key': 'Query Engine', 'value': contrail_qe_string}, {
                                            'key': 'OpServer', 'value': contrail_opserver_string}, {
                                                'key': 'Overall Node Status', 'value': overall_node_status_string}])
                if redis_uve_string:
                    modified_ops_data.append(
                        {'key': 'Redis UVE', 'value': redis_uve_string})
                if redis_query_string:
                    modified_ops_data.append(
                        {'key': 'Redis Query', 'value': redis_query_string})
                if self.ui.match_ui_kv(
                        modified_ops_data,
                        dom_basic_view):
                    self.logger.info(
                        "Analytics node %s basic view details data matched" %
                        (ops_analytics_node_name))
                else:
                    self.logger.error(
                        "Analytics node %s basic view details data match failed" %
                        (ops_analytics_node_name))
                    result = result and False
                ops_data = []
                ops_data.extend(
                    [
                        {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                            'key': 'Version', 'value': version}, {
                                'key': 'Status', 'value': overall_node_status_string}, {
                                    'key': 'Generators', 'value': generators_count}])

                if self.verify_analytics_nodes_ops_grid_page_data(
                        host_name,
                        ops_data):
                    self.logger.info(
                        "Analytics node %s main page data matched" %
                        (ops_analytics_node_name))
                else:
                    self.logger.error(
                        "Analytics nodes %s main page data match failed" %
                        (ops_analytics_node_name))
                    result = result and False
        return result
        # end verify_analytics_nodes_ops_basic_data_in_webui

    def verify_config_nodes_ops_basic_data(self):
        self.logger.info(
            "Verifying config node api server basic data on Monitor->Infra->Config Nodes->Details(basic view) page ...")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_config_nodes():
            result = result and False
        rows = self.ui.get_rows()
        config_nodes_list_ops = self.ui.get_config_nodes_list_ops()
        result = True
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in opserver..checking if exists in webui as well" %
                (ops_config_node_name))
            if not self.ui.click_monitor_config_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_config_node_name:
                    self.logger.info(
                        "Config node name %s found in webui..Verifying basic details..." %
                        (ops_config_node_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error("Config node name %s not found in webui" % (
                    ops_config_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Verify config node basic view details for  \
                    config_node-name %s " % (ops_config_node_name))
                # filter config_node basic view details from opserver data
                config_nodes_ops_data = self.ui.get_details(
                    config_nodes_list_ops[n]['href'])
                self.ui.click_monitor_config_nodes_basic(match_index)
                dom_basic_view = self.ui.get_basic_view_infra()
                ops_basic_data = []
                host_name = config_nodes_list_ops[n]['name']
                ip_address = config_nodes_ops_data.get(
                    'ModuleCpuState').get('config_node_ip')
                if not ip_address:
                    ip_address = '--'
                else:
                    ip_address = ', '.join(ip_address)
                process_state_list = config_nodes_ops_data.get(
                    'NodeStatus').get('process_info')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr',
                    'contrail-analytics-nodemgr',
                    'contrail-control-nodemgr',
                    'contrail-vrouter-nodemgr',
                    'openstack-nova-compute',
                    'contrail-svc-monitor',
                    'contrail-discovery:0',
                    'contrail-zookeeper',
                    'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-api:0':
                        api_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'ifmap':
                        ifmap_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-discovery:0':
                        discovery_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-schema':
                        schema_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-svc-monitor':
                        monitor_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                reduced_process_keys_dict = {}
                for k, v in process_down_stop_time_dict.items():
                    if k not in exclude_process_list:
                        reduced_process_keys_dict[k] = v
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.ui.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' +
                        status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.ui.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status

                version = config_nodes_ops_data.get(
                    'ModuleCpuState').get('build_info')
                if not version:
                    version = '--'
                else:
                    version = json.loads(config_nodes_ops_data.get('ModuleCpuState').get(
                        'build_info')).get('build-info')[0].get('build-id')
                    version = self.ui.get_version_string(version)
                module_cpu_info_len = len(
                    config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                cpu_mem_info_dict = {}
                for i in range(module_cpu_info_len):
                    if config_nodes_ops_data.get('ModuleCpuState').get(
                            'module_cpu_info')[i]['module_id'] == 'contrail-api':
                        cpu_mem_info_dict = config_nodes_ops_data.get(
                            'ModuleCpuState').get('module_cpu_info')[i]
                        break
                if not cpu_mem_info_dict:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.ui.get_cpu_string(cpu_mem_info_dict)
                    memory = self.ui.get_memory_string(
                        cpu_mem_info_dict)
                modified_ops_data = []
                generator_list = self.ui.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_config_node_name + \
                            ':Config:Contrail-Config-Nodemgr:0':
                        analytics_data = element['href']
                        generators_vrouters_data = self.ui.get_details(
                            element['href'])
                        analytics_data = generators_vrouters_data.get(
                            'ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data[
                                'primary'].split(':')[0] + ' (Up)'

                modified_ops_data.extend(
                    [
                        {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                            'key': 'Version', 'value': version}, {
                                'key': 'API Server', 'value': api_string}, {
                                    'key': 'Discovery', 'value': discovery_string}, {
                                        'key': 'Service Monitor', 'value': monitor_string}, {
                                            'key': 'Ifmap', 'value': ifmap_string}, {
                                                'key': 'Schema Transformer', 'value': schema_string}, {
                                                    'key': 'Overall Node Status', 'value': overall_node_status_string}])
                if self.ui.match_ui_kv(
                        modified_ops_data,
                        dom_basic_view):
                    self.logger.info(
                        "Config nodes %s basic view details data matched" %
                        (ops_config_node_name))
                else:
                    self.logger.error(
                        "Config node %s basic view details data match failed" %
                        (ops_config_node_name))
                    result = result and False
                ops_data = []
                self.logger.info(
                    "Verifying opserver basic data on Monitor->Infra->Config Nodes main page")
                ops_data.extend(
                    [
                        {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address.split(',')[0]}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                            'key': 'Version', 'value': version}, {
                                'key': 'Status', 'value': overall_node_status_string}])
                if self.verify_config_nodes_ops_grid_page_data(
                        host_name,
                        ops_data):
                    self.logger.info(
                        "Config node %s main page data matched" %
                        (ops_config_node_name))
                else:
                    self.logger.error(
                        "Config node %s main page data match failed" %
                        (ops_config_node_name))
                    result = result and False
        return result
        # end verify_config_nodes_ops_basic_data_in_webui

    def verify_vrouter_ops_basic_data(self):
        result = True
        self.logger.info(
            "Verifying opserver basic data on Monitor->Infra->Virtual routers->Details(basic view)...")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_vrouters():
            result = result and False
        rows = self.ui.get_rows()
        vrouters_list_ops = self.ui.get_vrouters_list_ops()
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in opserver..checking if exists in webui as well" %
                (ops_vrouter_name))
            if not self.ui.click_monitor_vrouters():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info(
                        "Vrouter name %s found in webui..Verifying basic details..." %
                        (ops_vrouter_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vrouter name %s not found in webui" % (ops_vrouter_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Verifying vrouter basic view details for vrouter-name %s " %
                    (ops_vrouter_name))
                self.ui.click_monitor_vrouters_basic(match_index)
                dom_basic_view = self.ui.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id(
                    'allItems').find_element_by_tag_name('p').get_attribute('innerHTML')
                if node_status.find("</span>") != -1:
                    node_status = node_status.split("</span>")[1]
                node_status = node_status.replace('\n', '').strip()

                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status
                # special handling for control nodes
                control_nodes = self.browser.find_element_by_class_name(
                    'table-cell').text
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Control Nodes':
                        dom_basic_view[i]['value'] = control_nodes
                # filter vrouter basic view details from opserver data
                vrouters_ops_data = self.ui.get_details(
                    vrouters_list_ops[n]['href'])
                ops_basic_data = []
                host_name = vrouters_list_ops[n]['name']
                ip_address = vrouters_ops_data.get(
                    'VrouterAgent').get('self_ip_list')[0]
                version = json.loads(vrouters_ops_data.get('VrouterAgent').get(
                    'build_info')).get('build-info')[0].get('build-id')
                version = self.ui.get_version_string(version)
                xmpp_messages = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('xmpp_stats_list')
                for i, item in enumerate(xmpp_messages):
                    if item['ip'] == ip_address:
                        xmpp_in_msgs = item['in_msgs']
                        xmpp_out_msgs = item['out_msgs']
                        xmpp_msgs_string = str(xmpp_in_msgs) + \
                            ' In, ' + \
                            str(xmpp_out_msgs) + ' Out'
                        break
                total_flows = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('total_flows')
                active_flows = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('active_flows')
                flow_count_string = str(active_flows) + \
                    ' Active, ' + \
                    str(total_flows) + ' Total'
                if vrouters_ops_data.get('VrouterAgent').get(
                        'connected_networks'):
                    networks = str(
                        len(vrouters_ops_data.get('VrouterAgent').get('connected_networks')))
                else:
                    networks = '--'
                interfaces = str(vrouters_ops_data.get('VrouterAgent')
                                 .get('total_interface_count')) + ' Total'
                if vrouters_ops_data.get('VrouterAgent').get(
                        'virtual_machine_list'):
                    instances = str(
                        len(vrouters_ops_data.get('VrouterAgent').get('virtual_machine_list')))
                else:
                    instances = '--'
                vrouter_stats_agent = vrouters_ops_data.get(
                    'VrouterStatsAgent')
                if not vrouter_stats_agent:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.ui.get_cpu_string(vrouter_stats_agent)
                    memory = self.ui.get_memory_string(vrouter_stats_agent)
                last_log = vrouters_ops_data.get(
                    'VrouterAgent').get('total_interface_count')
                modified_ops_data = []
                process_state_list = vrouters_ops_data.get(
                    'NodeStatus').get('process_info')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr',
                    'contrail-analytics-nodemgr',
                    'contrail-control-nodemgr',
                    'contrail-vrouter-nodemgr',
                    'openstack-nova-compute',
                    'contrail-svc-monitor',
                    'contrail-discovery:0',
                    'contrail-zookeeper',
                    'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-vrouter-agent':
                        contrail_vrouter_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-vrouter-nodemgr':
                        contrail_vrouter_nodemgr_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'openstack-nova-compute':
                        openstack_nova_compute_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                reduced_process_keys_dict = {}
                for k, v in process_down_stop_time_dict.items():
                    if k not in exclude_process_list:
                        reduced_process_keys_dict[k] = v
                '''
                if not reduced_process_keys_dict :
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.ui.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.ui.get_node_status_string(str(max(reduced_process_keys_dict.values())))
                    overall_node_status_string  = ['Down since ' + status for status in overall_node_status_down_time]
                '''
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.ui.get_node_status_string(
                        str(recent_time))
                    down_intf = vrouters_ops_data.get(
                        'VrouterAgent').get('down_interface_count')
                    if down_intf > 0:
                        overall_node_status_string = str(
                            down_intf) + ' Interfaces down'
                    else:
                        overall_node_status_string = [
                            'Up since ' +
                            status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.ui.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    process_down_list = reduced_process_keys_dict.keys()
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'

                generator_list = self.ui.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_vrouter_name + \
                            ':Compute:contrail-vrouter-agent:0':
                        analytics_data = element['href']
                        break
                generators_vrouters_data = self.ui.get_details(
                    element['href'])
                analytics_data = generators_vrouters_data.get(
                    'ModuleClientState').get('client_info')
                if analytics_data['status'] == 'Established':
                    analytics_primary_ip = analytics_data[
                        'primary'].split(':')[0] + ' (Up)'
                    tx_socket_bytes = analytics_data.get(
                        'tx_socket_stats').get('bytes')
                    tx_socket_size = self.ui.get_memory_string(
                        int(tx_socket_bytes))
                    analytics_messages_string = self.ui.get_analytics_msg_count_string(
                        generators_vrouters_data,
                        tx_socket_size)
                control_nodes_list = vrouters_ops_data.get(
                    'VrouterAgent').get('xmpp_peer_list')
                control_nodes_string = ''
                for node in control_nodes_list:
                    if node['status'] and node['primary']:
                        control_ip = node['ip']
                        control_nodes_string = control_ip + '* (Up)'
                        index = control_nodes_list.index(node)
                        del control_nodes_list[index]
                for node in control_nodes_list:
                    node_ip = node['ip']
                    if node['status']:
                        control_nodes_string = control_nodes_string + \
                            ', ' + node_ip + ' (Up)'
                    else:
                        control_nodes_string = control_nodes_string + \
                            ', ' + node_ip + ' (Down)'
                modified_ops_data.extend(
                    [
                        {
                            'key': 'Flow Count', 'value': flow_count_string}, {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'Networks', 'value': networks}, {
                            'key': 'Instances', 'value': instances}, {
                                'key': 'CPU', 'value': cpu}, {
                                    'key': 'Memory', 'value': memory}, {
                                        'key': 'Version', 'value': version}, {
                                            'key': 'vRouter Agent', 'value': contrail_vrouter_string}, {
                                                'key': 'Overall Node Status', 'value': overall_node_status_string}, {
                                                    'key': 'Analytics Node', 'value': analytics_primary_ip}, {
                                                        'key': 'Analytics Messages', 'value': analytics_messages_string}, {
                                                            'key': 'Control Nodes', 'value': control_nodes_string}, {
                                                                'key': 'XMPP Messages', 'value': xmpp_msgs_string}, {
                                                                    'key': 'Interfaces', 'value': interfaces}])
                if self.ui.match_ui_kv(
                        modified_ops_data,
                        dom_basic_view):
                    self.logger.info(
                        "Vrouter %s basic view details data matched" %
                        (ops_vrouter_name))
                else:
                    self.logger.error(
                        "Vrouter %s basic view details data match failed" %
                        (ops_vrouter_name))
                    result = result and False
                ops_data = []
                self.logger.info(
                    "Verifying Vrouter opserver basic data on Monitor->Infra->Virtual Routers main page")
                ops_data.extend(
                    [
                        {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'Networks', 'value': networks}, {
                            'key': 'Instances', 'value': instances}, {
                            'key': 'CPU', 'value': cpu}, {
                                'key': 'Memory', 'value': memory}, {
                                    'key': 'Version', 'value': version}, {
                                        'key': 'Status', 'value': overall_node_status_string}, {
                                            'key': 'Interfaces', 'value': interfaces}])

                if self.verify_vrouter_ops_grid_page_data(host_name, ops_data):
                    self.logger.info(
                        "Vrouter %s main page data matched" %
                        (ops_vrouter_name))
                else:
                    self.logger.error(
                        "Vrouter %s main page data match failed" %
                        (ops_vrouter_name))
                    result = result and False

        return result
        # end verify_vrouter_ops_basic_data_in_webui

    def verify_vrouter_ops_advance_data(self):
        self.logger.info(
            "Verifying vrouter Opserver advance data on Monitor->Infra->Virtual Routers->Details(advance view) page......")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_vrouters():
            result = result and False
        rows = self.ui.get_rows()
        vrouters_list_ops = self.ui.get_vrouters_list_ops()
        result = True
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in opserver..checking if exists in webui as well" %
                (ops_vrouter_name))
            if not self.ui.click_monitor_vrouters():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info(
                        "Vrouter name %s found in webui..Verifying advance details..." %
                        (ops_vrouter_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vrouter name %s not found in webui" % (ops_vrouter_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Verfiying  vrouter advance details for vrouter-name %s " %
                    (ops_vrouter_name))
                self.ui.click_monitor_vrouters_advance(match_index)
                vrouters_ops_data = self.ui.get_details(
                    vrouters_list_ops[n]['href'])
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = self.ui.get_advanced_view_str()
                dom_arry_num = self.ui.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if 'VrouterStatsAgent' in vrouters_ops_data:
                    ops_data = vrouters_ops_data['VrouterStatsAgent']
                    history_del_list = [
                        'total_in_bandwidth_utilization',
                        'cpu_share',
                        'used_sys_mem',
                        'one_min_avg_cpuload',
                        'virt_mem',
                        'total_out_bandwidth_utilization']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']

                    modified_ops_data = []
                    self.ui.extract_keyvalue(
                        ops_data, modified_ops_data)
                if 'VrouterAgent' in vrouters_ops_data:
                    ops_data_agent = vrouters_ops_data['VrouterAgent']
                    modified_ops_data_agent = []
                    self.ui.extract_keyvalue(
                        ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + \
                        modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[k]['value'], list):
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif isinstance(complete_ops_data[k]['value'], unicode):
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.ui.match_ui_kv(
                            complete_ops_data,
                            merged_arry):
                        self.logger.info(
                            "Vrouter %s advance view details matched" %
                            (ops_vrouter_name))
                    else:
                        self.logger.error(
                            "Vrouter %s advance details match failed" %
                            (ops_vrouter_name))
                        result = result and False
        return result
    # end verify_vrouter_ops_advance_data_in_webui

    def verify_bgp_routers_ops_basic_data(self):
        self.logger.info(
            "Verifying Control Nodes opserver basic data on Monitor->Infra->Control Nodes->Details(basic view) page......")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_control_nodes():
            result = result and False
        rows = self.ui.get_rows()
        bgp_routers_list_ops = self.ui.get_bgp_routers_list_ops()
        result = True
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_routers_name = bgp_routers_list_ops[n]['name']
            self.logger.info("Control node host name %s exists in opserver..checking if exists \
                in webui as well" % (ops_bgp_routers_name))
            if not self.ui.click_monitor_control_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_bgp_routers_name:
                    self.logger.info(
                        "Bgp routers name %s found in webui..Verifying basic details..." %
                        (ops_bgp_routers_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error("Bgp routers name %s not found in webui" % (
                    ops_bgp_routers_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Verify control nodes basic view details for \
                    control node name %s " % (ops_bgp_routers_name))
                self.ui.click_monitor_control_nodes_basic(
                    match_index)
                dom_basic_view = self.ui.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status
                # filter bgp_routers basic view details from opserver data
                bgp_routers_ops_data = self.ui.get_details(
                    bgp_routers_list_ops[n]['href'])
                ops_basic_data = []
                host_name = bgp_routers_list_ops[n]['name']
                ip_address = bgp_routers_ops_data.get(
                    'BgpRouterState').get('bgp_router_ip_list')[0]
                if not ip_address:
                    ip_address = '--'
                version = json.loads(bgp_routers_ops_data.get('BgpRouterState').get(
                    'build_info')).get('build-info')[0].get('build-id')
                version = self.ui.get_version_string(version)
                bgp_peers_count = str(
                    bgp_routers_ops_data.get('BgpRouterState').get('num_bgp_peer')) + ' Total'
                bgp_peers_string = 'BGP Peers: ' + bgp_peers_count
                vrouters =  'vRouters: ' + \
                    str(bgp_routers_ops_data.get('BgpRouterState')
                        .get('num_up_xmpp_peer')) + '  Established in Sync'

                cpu = bgp_routers_ops_data.get('BgpRouterState')
                memory = bgp_routers_ops_data.get('BgpRouterState')
                if not cpu:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.ui.get_cpu_string(cpu)
                    memory = self.ui.get_memory_string(memory)
                generator_list = self.ui.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_bgp_routers_name + \
                            ':Control:contrail-control:0':
                        analytics_data = element['href']
                        generators_vrouters_data = self.ui.get_details(
                            element['href'])
                        analytics_data = generators_vrouters_data.get(
                            'ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data[
                                'primary'].split(':')[0] + ' (Up)'
                            tx_socket_bytes = analytics_data.get(
                                'tx_socket_stats').get('bytes')
                            tx_socket_size = self.ui.get_memory_string(
                                int(tx_socket_bytes))
                            analytics_msg_count = generators_vrouters_data.get(
                                'ModuleClientState').get('session_stats').get('num_send_msg')
                            offset = 15
                            analytics_msg_count_list = range(
                                int(analytics_msg_count) -
                                offset,
                                int(analytics_msg_count) +
                                offset)
                            analytics_messages_string = [
                                str(count) +
                                ' [' +
                                str(size) +
                                ']' for count in analytics_msg_count_list for size in tx_socket_size]
                ifmap_ip = bgp_routers_ops_data.get('BgpRouterState').get(
                    'ifmap_info').get('url').split(':')[0]
                ifmap_connection_status = bgp_routers_ops_data.get(
                    'BgpRouterState').get('ifmap_info').get('connection_status')
                ifmap_connection_status_change = bgp_routers_ops_data.get(
                    'BgpRouterState').get('ifmap_info').get('connection_status_change_at')
                ifmap_connection_string = [
                    ifmap_ip +
                    ' (' +
                    ifmap_connection_status +
                    ' since ' +
                    time +
                    ')' for time in self.ui.get_node_status_string(ifmap_connection_status_change)]
                process_state_list = bgp_routers_ops_data.get(
                    'NodeStatus').get('process_info')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr',
                    'contrail-analytics-nodemgr',
                    'contrail-control-nodemgr',
                    'contrail-vrouter-nodemgr',
                    'openstack-nova-compute',
                    'contrail-svc-monitor',
                    'contrail-discovery:0',
                    'contrail-zookeeper',
                    'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-control':
                        control_node_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-control-nodemgr':
                        control_nodemgr_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-dns':
                        contrail_dns_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                    if item['process_name'] == 'contrail-named':
                        contrail_named_string = self.ui.get_process_status_string(
                            item,
                            process_down_stop_time_dict,
                            process_up_start_time_dict)
                reduced_process_keys_dict = {}
                for k, v in process_down_stop_time_dict.items():
                    if k not in exclude_process_list:
                        reduced_process_keys_dict[k] = v

                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.ui.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' +
                        status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.ui.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_list = reduced_process_keys_dict.keys()
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'
                modified_ops_data = []
                modified_ops_data.extend(
                    [
                        {
                            'key': 'Peers', 'value': bgp_peers_string}, {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                                'key': 'Version', 'value': version}, {
                                    'key': 'Analytics Node', 'value': analytics_primary_ip}, {
                                        'key': 'Analytics Messages', 'value': analytics_messages_string}, {
                                            'key': 'Ifmap Connection', 'value': ifmap_connection_string}, {
                                                'key': 'Control Node', 'value': control_node_string}, {
                                                    'key': 'Overall Node Status', 'value': overall_node_status_string}])
                if self.ui.match_ui_kv(
                        modified_ops_data,
                        dom_basic_view):
                    self.logger.info(
                        "Control node %s basic view details matched" %
                        (ops_bgp_routers_name))
                else:
                    self.logger.error(
                        "Control node %s basic view details match failed" %
                        (ops_bgp_routers_name))
                    result = result and False
                ops_data = []
                ops_data.extend(
                    [
                        {
                            'key': 'Peers', 'value': bgp_peers_count}, {
                            'key': 'Hostname', 'value': host_name}, {
                            'key': 'IP Address', 'value': ip_address}, {
                            'key': 'CPU', 'value': cpu}, {
                            'key': 'Memory', 'value': memory}, {
                                'key': 'Version', 'value': version}, {
                                    'key': 'Status', 'value': overall_node_status_string}, {
                                        'key': 'vRouters', 'value': vrouters.split()[1] + ' Total'}])

                if self.verify_bgp_routers_ops_grid_page_data(
                        host_name,
                        ops_data):
                    self.logger.info(
                        "Control node %s  main page data matched" %
                        (ops_bgp_routers_name))
                else:
                    self.logger.error(
                        "Control node %s main page data match failed" %
                        (ops_bgp_routers_name))
                    result = result and False
        return result
        # end verify_bgp_routers_ops_basic_data_in_webui

    def verify_bgp_routers_ops_advance_data(self):
        self.logger.info(
            "Verifying Control Nodes opserver advance data on Monitor->Infra->Control Nodes->Details(advance view) page ......")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_control_nodes():
            result = result and False
        rows = self.ui.get_rows()
        bgp_routers_list_ops = self.ui.get_bgp_routers_list_ops()
        result = True
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_router_name = bgp_routers_list_ops[n]['name']
            self.logger.info(
                "Control node %s exists in opserver..checking if exists in webui " %
                (ops_bgp_router_name))
            self.logger.info(
                "Clicking on Monitor->Control Nodes")
            if not self.ui.click_monitor_control_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_bgp_router_name:
                    self.logger.info(
                        "Control Node name %s found in webui..Verifying advance details..." %
                        (ops_bgp_router_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag:
                self.logger.error("Control Node name %s not found in webui" %
                                  (ops_bgp_router_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "verify control node advance view details for control node %s " %
                    (ops_bgp_router_name))
                self.ui.click_monitor_control_nodes_advance(
                    match_index)
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = self.ui.get_advanced_view_str()
                dom_arry_num = self.ui.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                bgp_routers_ops_data = self.ui.get_details(
                    bgp_routers_list_ops[n]['href'])
                bgp_router_state_ops_data = bgp_routers_ops_data[
                    'BgpRouterState']
                history_del_list = [
                    'total_in_bandwidth_utilization',
                    'cpu_share',
                    'used_sys_mem',
                    'one_min_avg_cpuload',
                    'virt_mem',
                    'total_out_bandwidth_utilization']
                for item in history_del_list:
                    if bgp_router_state_ops_data.get(item):
                        for element in bgp_router_state_ops_data.get(item):
                            if element.get('history-10'):
                                del element['history-10']
                            if element.get('s-3600-topvals'):
                                del element['s-3600-topvals']
                if 'BgpRouterState' in bgp_routers_ops_data:
                    bgp_router_state_ops_data = bgp_routers_ops_data[
                        'BgpRouterState']

                    modified_bgp_router_state_ops_data = []
                    self.ui.extract_keyvalue(
                        bgp_router_state_ops_data,
                        modified_bgp_router_state_ops_data)
                    complete_ops_data = modified_bgp_router_state_ops_data
                    for k in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[k]['value'], list):
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif isinstance(complete_ops_data[k]['value'], unicode):
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.ui.match_ui_kv(
                            complete_ops_data,
                            merged_arry):
                        self.logger.info(
                            "Control node advanced view data matched")
                    else:
                        self.logger.error(
                            "Control node advanced view data match failed")
                        result = result and False
        return result
    # end verify_bgp_routers_ops_advance_data_in_webui

    def verify_analytics_nodes_ops_advance_data(self):
        self.logger.info(
            "Verifying analytics_nodes(collectors) opserver advance data on Monitor->Infra->Analytics Nodes->Details(advanced view) page......")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_analytics_nodes():
            result = result and False
        rows = self.ui.get_rows()
        analytics_nodes_list_ops = self.ui.get_collectors_list_ops()
        result = True
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info(
                "Analytics node %s exists in opserver..checking if exists in webui " %
                (ops_analytics_node_name))
            self.logger.info(
                "Clicking on analytics nodes on Monitor->Infra->Analytics Nodes...")
            if not self.ui.click_monitor_analytics_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info(
                        "Analytics node name %s found in webui..Verifying advance details..." %
                        (ops_analytics_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag:
                self.logger.error("Analytics node name %s not found in webui" %
                                  (ops_analytics_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Verify analytics node advance view details for analytics node-name %s " %
                    (ops_analytics_node_name))
                self.ui.click_monitor_analytics_nodes_advance(
                    match_index)
                analytics_nodes_ops_data = self.ui.get_details(
                    analytics_nodes_list_ops[n]['href'])
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = self.ui.get_advanced_view_str()
                dom_arry_num = self.ui.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                modified_query_perf_info_ops_data = []
                modified_module_cpu_state_ops_data = []
                modified_analytics_cpu_state_ops_data = []
                modified_collector_state_ops_data = []
                history_del_list = [
                    'opserver_mem_virt',
                    'queryengine_cpu_share',
                    'opserver_cpu_share',
                    'collector_cpu_share',
                    'collector_mem_virt',
                    'queryengine_mem_virt',
                    'enq_delay']
                if 'QueryPerfInfo' in analytics_nodes_ops_data:
                    query_perf_info_ops_data = analytics_nodes_ops_data[
                        'QueryPerfInfo']
                    for item in history_del_list:
                        if query_perf_info_ops_data.get(item):
                            for element in query_perf_info_ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                                if element.get('s-3600-summary'):
                                    del element['s-3600-summary']
                    self.ui.extract_keyvalue(
                        query_perf_info_ops_data,
                        modified_query_perf_info_ops_data)
                if 'ModuleCpuState' in analytics_nodes_ops_data:
                    module_cpu_state_ops_data = analytics_nodes_ops_data[
                        'ModuleCpuState']
                    for item in history_del_list:
                        if module_cpu_state_ops_data.get(item):
                            for element in module_cpu_state_ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                                if element.get('s-3600-summary'):
                                    del element['s-3600-summary']

                    self.ui.extract_keyvalue(
                        module_cpu_state_ops_data,
                        modified_module_cpu_state_ops_data)
                if 'AnalyticsCpuState' in analytics_nodes_ops_data:
                    analytics_cpu_state_ops_data = analytics_nodes_ops_data[
                        'AnalyticsCpuState']
                    modified_analytics_cpu_state_ops_data = []
                    self.ui.extract_keyvalue(
                        analytics_cpu_state_ops_data,
                        modified_analytics_cpu_state_ops_data)
                if 'CollectorState' in analytics_nodes_ops_data:
                    collector_state_ops_data = analytics_nodes_ops_data[
                        'CollectorState']
                    self.ui.extract_keyvalue(
                        collector_state_ops_data,
                        modified_collector_state_ops_data)
                complete_ops_data = modified_query_perf_info_ops_data + modified_module_cpu_state_ops_data + \
                    modified_analytics_cpu_state_ops_data + \
                    modified_collector_state_ops_data
                for k in range(len(complete_ops_data)):
                    if isinstance(complete_ops_data[k]['value'], list):
                        for m in range(len(complete_ops_data[k]['value'])):
                            complete_ops_data[k]['value'][m] = str(
                                complete_ops_data[k]['value'][m])
                    elif isinstance(complete_ops_data[k]['value'], unicode):
                        complete_ops_data[k]['value'] = str(
                            complete_ops_data[k]['value'])
                    else:
                        complete_ops_data[k]['value'] = str(
                            complete_ops_data[k]['value'])
                if self.ui.match_ui_kv(
                        complete_ops_data,
                        merged_arry):
                    self.logger.info(
                        "Analytics node advance view data matched")
                else:
                    self.logger.error(
                        "Analytics node match failed")
                    result = result and False
        return result
    # end verify_analytics_nodes_ops_advance_data_in_webui

    def verify_vm_ops_basic_data(self):
        self.logger.info(
            "Verifying instances opserver data on Monitor->Networking->Instances summary (basic view) page ..")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_instances():
            result = result and False
        rows = self.ui.get_rows()
        vm_list_ops = self.ui.get_vm_list_ops()
        result = True
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            if not self.ui.click_monitor_instances():
                result = result and False
            rows = self.ui.get_rows()
            self.logger.info(
                "Vm uuid %s exists in opserver..checking if exists in webui as well" %
                (ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[2].text == ops_uuid:
                    self.logger.info(
                        "Vm uuid %s matched in webui..Verifying basic view details..." %
                        (ops_uuid))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vm_name = rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text
                    break
            if not match_flag:
                self.logger.error(
                    "Uuid exists in opserver but uuid %s not found in webui..." %
                    (ops_uuid))
                self.logger.debug(self.dash)
            else:
                self.ui.click_monitor_instances_basic(
                    match_index,
                    length=len(vm_list_ops))
                self.logger.info(
                    "Verify instances basic view details for uuid %s " %
                    (ops_uuid))
                dom_arry_basic = self.ui.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                basic = "//*[contains(@id, 'basicDetails')]"
                elements = self.ui.find_element(
                    [basic, 'row-fluid'], ['xpath', 'class'], if_elements=[1])
                len_elements = len(elements)
                vm_ops_data = self.ui.get_details(
                    vm_list_ops[k]['href'])
                complete_ops_data = []
                if vm_ops_data and 'UveVirtualMachineAgent' in vm_ops_data:
                    # get vm interface basic details from opserver
                    ops_data_interface_list = vm_ops_data[
                        'UveVirtualMachineAgent']['interface_list']
                    for k in range(len(ops_data_interface_list)):
                        del ops_data_interface_list[k]['l2_active']
                        if ops_data_interface_list[k].get('floating_ips'):
                            fip_list = ops_data_interface_list[
                                k].get('floating_ips')
                            floating_ip = None
                            fip_list_len = len(fip_list)
                            for index, element in enumerate(fip_list):
                                ops_data_interface_list[k][
                                    'floating_ips'] = element.get('ip_address')
                                ops_data_interface_list[k][
                                    'floating_ip_pool'] = element.get('virtual_network')
                            #ops_data_interface_list[k]['floating_ips'] = floating_ip
                        modified_ops_data_interface_list = []
                        self.ui.extract_keyvalue(
                            ops_data_interface_list[k],
                            modified_ops_data_interface_list)
                        complete_ops_data = complete_ops_data + \
                            modified_ops_data_interface_list
                        for t in range(len(complete_ops_data)):
                            if isinstance(complete_ops_data[t]['value'], list):
                                for m in range(len(complete_ops_data[t]['value'])):
                                    complete_ops_data[t]['value'][m] = str(
                                        complete_ops_data[t]['value'][m])
                            elif isinstance(complete_ops_data[t]['value'], unicode):
                                complete_ops_data[t]['value'] = str(
                                    complete_ops_data[t]['value'])
                            else:
                                complete_ops_data[t]['value'] = str(
                                    complete_ops_data[t]['value'])
                # get vm basic interface details excluding basic interface
                # details
                dom_arry_intf = []
                dom_arry_intf.insert(0, {'key': 'vm_name', 'value': vm_name})
                # insert non interface elements in list
                for i in range(len_dom_arry_basic):
                    element_key = elements[
                        i].find_elements_by_tag_name('div')[0].text
                    element_value = elements[
                        i].find_elements_by_tag_name('div')[1].text
                    dom_arry_intf.append(
                        {'key': element_key, 'value': element_value})
                fip_rows_index = False
                for i in range(len_dom_arry_basic + 1, len_elements):
                    if not fip_rows_index:
                        elements_key = elements[
                            len_dom_arry_basic].find_elements_by_tag_name('div')
                    else:
                        elements_key = elements[
                            fip_rows_index].find_elements_by_tag_name('div')
                    elements_value = elements[
                        i].find_elements_by_tag_name('div')
                    if not elements_value[0].text == 'Floating IPs':
                        for j in range(len(elements_key)):
                            if j == 2 and not fip_rows_index:
                                dom_arry_intf.append(
                                    {'key': 'ip_address', 'value': elements_value[j].text.split('/')[0].strip()})
                                dom_arry_intf.append(
                                    {'key': 'mac_address', 'value': elements_value[j].text.split('/')[1].strip()})
                            else:
                                dom_arry_intf.append(
                                    {'key': elements_key[j].text, 'value': elements_value[j].text})
                    else:
                        fip_rows_index = i
                        continue
                for element in complete_ops_data:
                    if element['key'] == 'name':
                        index = complete_ops_data.index(element)
                        del complete_ops_data[index]
                if self.ui.match_ui_values(
                        complete_ops_data,
                        dom_arry_intf):
                    self.logger.info(
                        "VM basic view data matched")
                else:
                    self.logger.error(
                        "VM basic data match failed")
                    result = result and False
        return result
    # end verify_vm_ops_basic_data_in_webui

    def verify_dashboard_details(self):
        self.logger.info(
            "Verifying dashboard details on Monitor->Infra->Dashboard page")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_dashboard():
            result = result and False
        dashboard_node_details = self.browser.find_element_by_id(
            'topStats').find_elements_by_class_name('infobox-data-number')
        dashboard_data_details = self.browser.find_element_by_id(
            'sparkLineStats').find_elements_by_class_name('infobox-data-number')
        dashboard_system_details = self.browser.find_element_by_id(
            'system-info-stat').find_elements_by_tag_name('li')
        servers_ver = self.ui.find_element(
            ['system-info-stat', 'value'], ['id', 'class'], if_elements=[1])
        servers = servers_ver[0].text
        version = servers_ver[2].text
        logical_nodes = servers_ver[1].text
        dom_data = []
        dom_data.append(
            {'key': 'logical_nodes', 'value': logical_nodes})
        dom_data.append(
            {'key': 'vrouters', 'value': dashboard_node_details[0].text})
        dom_data.append(
            {'key': 'control_nodes', 'value': dashboard_node_details[1].text})
        dom_data.append(
            {'key': 'analytics_nodes', 'value': dashboard_node_details[2].text})
        dom_data.append(
            {'key': 'config_nodes', 'value': dashboard_node_details[3].text})
        dom_data.append(
            {'key': 'instances', 'value': dashboard_data_details[0].text})
        dom_data.append(
            {'key': 'interfaces', 'value': dashboard_data_details[1].text})
        dom_data.append(
            {'key': 'virtual_networks', 'value': dashboard_data_details[2].text})
        dom_data.append(
            {
                'key': dashboard_system_details[0].find_element_by_class_name('key').text,
                'value': dashboard_system_details[0].find_element_by_class_name('value').text})
        dom_data.append(
            {
                'key': dashboard_system_details[1].find_element_by_class_name('key').text,
                'value': dashboard_system_details[1].find_element_by_class_name('value').text})
        ops_servers = str(len(self.ui.get_config_nodes_list_ops()))
        ops_version = self.ui.get_version()
        self.ui.append_to_list(
            dom_data, [('servers', servers), ('version', version)])
        ops_dashborad_data = []
        if not self.ui.click_configure_networks():
            result = result and False
        rows = self.ui.get_rows()
        vrouter_total_vm = str(len(self.ui.get_vm_list_ops()))
        total_vrouters = str(len(self.ui.get_vrouters_list_ops()))
        total_control_nodes = str(
            len(self.ui.get_bgp_routers_list_ops()))
        total_analytics_nodes = str(
            len(self.ui.get_collectors_list_ops()))
        total_config_nodes = str(
            len(self.ui.get_config_nodes_list_ops()))
        vrouters_list_ops = self.ui.get_vrouters_list_ops()
        interface_count = 0
        vrouter_total_vn = 0
        for index in range(len(vrouters_list_ops)):
            vrouters_ops_data = self.ui.get_details(
                vrouters_list_ops[index]['href'])
            if vrouters_ops_data.get('VrouterAgent').get(
                    'total_interface_count'):
                interface_count = interface_count + \
                    vrouters_ops_data.get('VrouterAgent').get(
                        'total_interface_count')
            if vrouters_ops_data.get('VrouterAgent').get('connected_networks'):
                vrouter_total_vn = vrouter_total_vn + \
                    (len(vrouters_ops_data.get('VrouterAgent')
                         .get('connected_networks')))
        lnodes = str(
            int(total_control_nodes) +
            int(total_analytics_nodes) +
            int(total_config_nodes) +
            int(total_vrouters))
        ops_dashborad_data.append({'key': 'logical_nodes', 'value': lnodes})
        ops_dashborad_data.append({'key': 'vrouters', 'value': total_vrouters})
        ops_dashborad_data.append(
            {'key': 'control_nodes', 'value': total_control_nodes})
        ops_dashborad_data.append(
            {'key': 'analytics_nodes', 'value': total_analytics_nodes})
        ops_dashborad_data.append(
            {'key': 'config_nodes', 'value': total_config_nodes})
        ops_dashborad_data.append(
            {'key': 'instances', 'value': vrouter_total_vm})
        ops_dashborad_data.append(
            {'key': 'interfaces', 'value': str(interface_count)})
        ops_dashborad_data.append(
            {'key': 'virtual_networks', 'value': str(vrouter_total_vn)})
        self.ui.append_to_list(
            ops_dashborad_data, [
                ('servers', ops_servers), ('version', ops_version)])
        result = True
        if self.ui.match_ui_kv(ops_dashborad_data, dom_data):
            self.logger.info("Monitor dashborad details matched")
        else:
            self.logger.error("Monitor dashborad details not matched")
            result = result and False
        return result
    # end verify_dashboard_details_in_webui

    def verify_vn_ops_basic_data(self):
        self.logger.info(
            "Verifying vn opserver data on Monitor->Networking->Networks page(basic view)")
        self.logger.debug(self.dash)
        error = 0
        if not self.ui.click_monitor_networks():
            result = result and False
        rows = self.ui.get_rows()
        vn_list_ops = self.ui.get_vn_list_ops()
        for k in range(len(vn_list_ops)):
            ops_fq_name = vn_list_ops[k]['name']
            if not self.ui.click_monitor_networks():
                result = result and False
            rows = self.browser.find_element_by_class_name('grid-canvas')
            rows = self.ui.get_rows(rows)
            self.logger.info(
                "Vn fq_name %s exists in opserver..checking if exists in webui as well" %
                (ops_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text == ops_fq_name:
                    self.logger.info(
                        "Vn fq_name %s matched in webui..Verifying basic view details..." %
                        (ops_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fq name exists in opserver but %s not found in webui..." %
                    (ops_fq_name))
                self.logger.debug(self.dash)
            else:
                self.ui.click_monitor_networks_basic(match_index)
                self.logger.info(
                    "Verify VN basic view details for VN fq_name %s " %
                    (ops_fq_name))
                # get vn basic details excluding basic interface details
                dom_arry_basic = self.ui.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                elements = self.browser.find_element_by_xpath(
                    "//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')
                len_elements = len(elements)
                vn_ops_data = self.ui.get_details(
                    vn_list_ops[k]['href'])
                complete_ops_data = []
                ops_data_ingress = {'key':
                                    'ingress_flow_count', 'value': str(0)}
                ops_data_egress = {'key':
                                   'egress_flow_count', 'value': str(0)}
                ops_data_acl_rules = {'key':
                                      'total_acl_rules', 'value': str(0)}
                vn_name = ops_fq_name.split(':')[2]
                ops_data_interfaces_count = {
                    'key': 'interface_list_count', 'value': str(0)}
                if 'UveVirtualNetworkAgent' in vn_ops_data:
                    # creating a list of basic view items retrieved from
                    # opserver
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkAgent')
                    if ops_data_basic.get('ingress_flow_count'):
                        ops_data_ingress = {
                            'key': 'ingress_flow_count',
                            'value': ops_data_basic.get('ingress_flow_count')}
                    if ops_data_basic.get('egress_flow_count'):
                        ops_data_egress = {
                            'key': 'egress_flow_count',
                            'value': ops_data_basic.get('egress_flow_count')}
                    if ops_data_basic.get('total_acl_rules'):
                        ops_data_acl_rules = {
                            'key': 'total_acl_rules',
                            'value': ops_data_basic.get('total_acl_rules')}
                    if ops_data_basic.get('interface_list'):
                        ops_data_interfaces_count = {
                            'key': 'interface_list_count',
                            'value': len(
                                ops_data_basic.get('interface_list'))}
                    if ops_data_basic.get('vrf_stats_list'):
                        vrf_stats_list = ops_data_basic['vrf_stats_list']
                        vrf_stats_list_new = [vrf['name']
                                              for vrf in vrf_stats_list]
                        vrf_list_joined = ','.join(vrf_stats_list_new)
                        ops_data_vrf = {'key': 'vrf_stats_list',
                                        'value': vrf_list_joined}
                        complete_ops_data.append(ops_data_vrf)
                    if ops_data_basic.get('acl'):
                        ops_data_acl = {'key': 'acl', 'value':
                                        ops_data_basic.get('acl')}
                        complete_ops_data.append(ops_data_acl)
                    if ops_data_basic.get('virtualmachine_list'):
                        ops_data_instances = {
                            'key': 'virtualmachine_list',
                            'value': ', '.join(
                                ops_data_basic.get('virtualmachine_list'))}
                        complete_ops_data.append(ops_data_instances)
                complete_ops_data.extend(
                    [ops_data_ingress, ops_data_egress, ops_data_acl_rules, ops_data_interfaces_count])
                if ops_fq_name.find('__link_local__') != -1 or ops_fq_name.find(
                        'default-virtual-network') != -1 or ops_fq_name.find('ip-fabric') != -1:
                    for i, item in enumerate(complete_ops_data):
                        if complete_ops_data[i]['key'] == 'vrf_stats_list':
                            del complete_ops_data[i]
                if 'UveVirtualNetworkConfig' in vn_ops_data:
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkConfig')
                    if ops_data_basic.get('attached_policies'):
                        ops_data_policies = ops_data_basic.get(
                            'attached_policies')
                        if ops_data_policies:
                            pol_name_list = [pol['vnp_name']
                                             for pol in ops_data_policies]
                            pol_list_joined = ', '.join(pol_name_list)
                            ops_data_policies = {
                                'key': 'attached_policies',
                                'value': pol_list_joined}
                            complete_ops_data.extend([ops_data_policies])
                    for t in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[t]['value'], list):
                            for m in range(len(complete_ops_data[t]['value'])):
                                complete_ops_data[t]['value'][m] = str(
                                    complete_ops_data[t]['value'][m])
                        elif isinstance(complete_ops_data[t]['value'], unicode):
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                        else:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])

                if self.ui.match_ui_values(
                        complete_ops_data,
                        dom_arry_basic):
                    self.logger.info(
                        "VN basic view data matched in webui")

                else:
                    self.logger.error(
                        "VN basic view data match failed in webui")
                    error = 1
        return not error
    # end verify_vn_ops_basic_data_in_webui

    def verify_config_nodes_ops_advance_data(self):
        self.logger.info(
            "Verifying config nodes opserver data on Monitor->Infra->Config Nodes->Details(advance view) page")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_config_nodes():
            result = result and False
        rows = self.ui.get_rows()
        config_nodes_list_ops = self.ui.get_config_nodes_list_ops()
        result = True
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info(
                "Config node host name %s exists in opserver..checking if exists in webui as well" %
                (ops_config_node_name))
            if not self.ui.click_monitor_config_nodes():
                result = result and False
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[0].text == ops_config_node_name:
                    self.logger.info(
                        "Config node name %s found in webui..Verifying advance view details..." %
                        (ops_config_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag:
                self.logger.error(
                    "Config node name %s not found in webui" %
                    (ops_config_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Verify config nodes advance view details in webui for config node-name %s " %
                    (ops_config_node_name))
                self.ui.click_monitor_config_nodes_advance(
                    match_index)
                config_nodes_ops_data = self.ui.get_details(
                    config_nodes_list_ops[n]['href'])
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = self.ui.get_advanced_view_str()
                dom_arry_num = self.ui.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if 'ModuleCpuState' in config_nodes_ops_data:
                    ops_data = config_nodes_ops_data['ModuleCpuState']
                    history_del_list = [
                        'api_server_mem_virt',
                        'service_monitor_cpu_share',
                        'schema_xmer_mem_virt',
                        'service_monitor_mem_virt',
                        'api_server_cpu_share',
                        'schema_xmer_cpu_share']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                    modified_ops_data = []
                    self.ui.extract_keyvalue(
                        ops_data, modified_ops_data)
                    complete_ops_data = modified_ops_data
                    for k in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[k]['value'], list):
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif isinstance(complete_ops_data[k]['value'], unicode):
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.ui.match_ui_kv(
                            complete_ops_data,
                            merged_arry):
                        self.logger.info(
                            "Config node advance view data matched in webui")
                    else:
                        self.logger.error(
                            "Config node advance view data match failed in webui")
                        result = result and False
        return result
    # end verify_config_nodes_ops_advance_data_in_webui

    def verify_vn_ops_advance_data(self):
        self.logger.info(
            "Verifying vn opserver advance data on Monitor->Networking->Networks Summary(Advanced view) page .....")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_networks():
            result = result and False
        rows = self.ui.get_rows()
        vn_list_ops = self.ui.get_vn_list_ops()
        result = True
        for n in range(len(vn_list_ops)):
            ops_fqname = vn_list_ops[n]['name']
            self.logger.info(
                "Vn fq name %s exists in opserver..checking if exists in webui as well" %
                (ops_fqname))
            if not self.ui.click_monitor_networks():
                result = result and False
            rows = self.browser.find_element_by_class_name('grid-canvas')
            rows = self.ui.get_rows(rows)
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text == ops_fqname:
                    self.logger.info(
                        "Vn fq name %s found in webui..Verifying advance view details..." %
                        (ops_fqname))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fqname %s not found in webui" % (ops_fqname))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Verify advance view details for fqname %s " %
                    (ops_fqname))
                self.ui.click_monitor_networks_advance(match_index)
                vn_ops_data = self.ui.get_details(
                    vn_list_ops[n]['href'])
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = self.ui.get_advanced_view_str()
                merged_arry = dom_arry + dom_arry_str
                if 'UveVirtualNetworkConfig' in vn_ops_data:
                    ops_data = vn_ops_data['UveVirtualNetworkConfig']
                    modified_ops_data = []
                    self.ui.extract_keyvalue(
                        ops_data, modified_ops_data)

                if 'UveVirtualNetworkAgent' in vn_ops_data:
                    ops_data_agent = vn_ops_data['UveVirtualNetworkAgent']
                    if 'udp_sport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_sport_bitmap']
                    if 'udp_dport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_dport_bitmap']
                    self.logger.info(
                        "Verifying VN %s details: \n %s \n " %
                        (vn_list_ops[i]['href'], ops_data_agent))
                    modified_ops_data_agent = []
                    self.ui.extract_keyvalue(
                        ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + \
                        modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[k]['value'], list):
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif isinstance(complete_ops_data[k]['value'], unicode):
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.ui.match_ui_kv(
                            complete_ops_data,
                            merged_arry):
                        self.logger.info(
                            "VN advance view data matched in webui")
                    else:
                        self.logger.error(
                            "VN advance view data match failed in webui")
                        result = result and False
        return result
    # end verify_vn_ops_advance_data_in_webui

    def verify_vm_ops_advance_data(self):
        self.logger.info(
            "Verifying instance opsserver advance data on Monitor->Networking->Instances->Instances summary(Advance view) page......")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_instances():
            result = result and False
        rows = self.ui.get_rows()
        vm_list_ops = self.ui.get_vm_list_ops()
        result = True
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            if not self.ui.click_monitor_instances():
                result = result and False
            rows = self.ui.get_rows()
            self.logger.info(
                "Vm uuid %s exists in opserver..checking if exists in webui as well" %
                (ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name(
                        'slick-cell')[2].text == ops_uuid:
                    self.logger.info(
                        "Vm uuid %s matched in webui..Verifying advance view details..." %
                        (ops_uuid))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Uuid exists in opserver but uuid %s not found in webui..." %
                    (ops_uuid))
                self.logger.debug(self.dash)
            else:
                self.ui.click_monitor_instances_advance(
                    match_index,
                    length=len(vm_list_ops))
                self.logger.info(
                    "Verify advance view details for uuid %s " % (ops_uuid))
                dom_arry = self.ui.parse_advanced_view()
                dom_arry_str = []
                dom_arry_str = self.ui.get_advanced_view_str()
                merged_arry = dom_arry + dom_arry_str
                vm_ops_data = self.ui.get_details(
                    vm_list_ops[k]['href'])
                if vm_ops_data and 'UveVirtualMachineAgent' in vm_ops_data:
                    ops_data = vm_ops_data['UveVirtualMachineAgent']
                    modified_ops_data = []
                    self.ui.extract_keyvalue(
                        ops_data, modified_ops_data)
                    complete_ops_data = modified_ops_data
                    for t in range(len(complete_ops_data)):
                        if isinstance(complete_ops_data[t]['value'], list):
                            for m in range(len(complete_ops_data[t]['value'])):
                                complete_ops_data[t]['value'][m] = str(
                                    complete_ops_data[t]['value'][m])
                        elif isinstance(complete_ops_data[t]['value'], unicode):
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                        else:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                    if self.ui.match_ui_kv(
                            complete_ops_data,
                            merged_arry):
                        self.logger.info(
                            "VM advance view data matched in webui")
                    else:
                        self.logger.error(
                            "VM advance data match failed in webui")
                        result = result and False
        return result
    # end verify_vm_ops_advance_data_in_webui

    def verify_vn_api_data(self):
        self.logger.info(
            "Verifying vn api server data on Config->Networking->Networks page...")
        self.logger.debug(self.dash)
        result = True
        vn_list_api = self.ui.get_vn_list_api()
        for vns in range(len(vn_list_api['virtual-networks'])):
            pol_list, pol_list1, ip_block_list, ip_block, pool_list, floating_pool, route_target_list, host_route_main = [[] for _ in range(8)]
            api_fq = vn_list_api['virtual-networks'][vns]['fq_name']
            api_fq_name = api_fq[2]
            project_name = api_fq[1]
            if project_name == 'default-project':
                continue
            self.ui.click_configure_networks()
            #if project_name == 'default-project':
            #    continue
            self.ui.select_project(project_name)
            rows = self.ui.get_rows()
            skip_net_list = [
                'ip-fabric',
                'default-virtual-network',
                '__link_local__']
            if api_fq_name in skip_net_list:
                continue
            self.logger.info(
                "Vn fq_name %s exists in api server..checking if exists in webui as well" %
                (api_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                dom_arry_basic = []
                if rows[i].find_elements_by_tag_name(
                        'div')[2].text == api_fq_name:
                    self.logger.info(
                        "Vn fq_name %s matched in webui..Verifying basic view details..." %
                        (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[
                        i].find_elements_by_tag_name('div')[2].text
                    policies = rows[i].find_elements_by_tag_name(
                        'div')[4].text.splitlines()
                    dom_arry_basic.append(
                        {'key': 'Attached Policies', 'value': policies})
                    dom_arry_basic.append(
                        {'key': 'Network', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    dom_arry_basic.append({'key': 'ip_blocks_grid_row', 'value': rows[
                                          i].find_elements_by_tag_name('div')[3].text.split()})
                    dom_arry_basic.append(
                        {'key': 'shared_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[5].text})
                    dom_arry_basic.append({'key': 'admin_state_grid_row', 'value': rows[
                                          i].find_elements_by_tag_name('div')[6].text})
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fq_name exists in apiserver but %s not found in webui..." %
                    (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.ui.click_configure_networks_basic(match_index)
                rows = self.ui.get_rows(canvas=True)
                self.logger.info(
                    "Verify basic view details for VN fq_name %s " %
                    (api_fq_name))
                rows_detail = rows[
                    match_index +
                    1].find_element_by_class_name('slick-row-detail-container').find_elements_by_class_name('row-fluid')
                rows_elements = rows_detail[-11:]
                no_ipams = len(rows_detail) - 11 - 3
                ipam_list = []
                for ipam in range(no_ipams):
                    elements = rows_detail[
                        ipam +
                        3].find_elements_by_tag_name('div')
                    ipam = elements[0].text
                    cidr = elements[2].text
                    gateway = elements[3].text
                    dhcp = elements[5].text
                    alloc_pool = elements[6].text
                    ipam_list.append(
                        ipam +
                        ':' +
                        cidr +
                        ':' +
                        gateway +
                        ':' +
                        dhcp +
                        ':' + 
                        alloc_pool)
                dom_arry_basic.append({'key': 'IP Blocks', 'value': ipam_list})
                for element in rows_elements:
                    span_element = element.find_elements_by_tag_name('span')
                    key = span_element[
                        0].find_element_by_tag_name('label').text
                    if key == 'Floating IP Pools':
                        value = span_element[1].text.split(
                            ': ')[1].split(' ')[0]
                    elif key == 'Attached Network Policies':
                        value = span_element[1].text.split(
                            ': ')[1].splitlines()
                    else:
                        value = span_element[1].text.split(': ')[1]
                    dom_arry_basic.append({'key': key, 'value': value})
                vn_api_data = self.ui.get_details(
                    vn_list_api['virtual-networks'][vns]['href'])
                complete_api_data = []
                if 'virtual-network' in vn_api_data:
                    api_data_basic = vn_api_data.get('virtual-network')
                if api_data_basic.get('name'):
                    complete_api_data.append(
                        {'key': 'Network', 'value': api_data_basic['name']})
                if 'network_policy_refs' in api_data_basic:
                    for ass_pol in range(len(api_data_basic['network_policy_refs'])):
                        pol_list.append(
                            str(api_data_basic['network_policy_refs'][ass_pol]['to'][2]))
                    if len(pol_list) > 2:
                        for item in range(len(policies)):
                            for items in range(len(pol_list)):
                                if policies[item] == pol_list[items]:
                                    pol_list1.append(pol_list[items])
                        pol_string = '(' + str(len(pol_list) - 2) + ' more)'
                        pol_list1.append(pol_string)
                    else:
                        pol_list1 = policies
                    complete_api_data.append(
                        {'key': 'Attached Network Policies', 'value': pol_list})
                    complete_api_data.append(
                        {'key': 'Attached Policies', 'value': pol_list1})
                if 'network_ipam_refs' in api_data_basic:
                    for ip in range(len(api_data_basic['network_ipam_refs'])):
                        dom_arry_basic.append({'key': 'Attached Policies', 'value': rows[
                                              i].find_elements_by_tag_name('div')[3].text.split()})
                        default_net_ipam = api_data_basic[
                            'network_ipam_refs'][ip]['to'][2]
                        len_ipams = len(
                            api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'])
                        net_ipam_refs = api_data_basic['network_ipam_refs'][ip]
                        net_domain = net_ipam_refs['to'][0]
                        net_project = net_ipam_refs['to'][1]
                        net_ipam = net_ipam_refs['to'][2]
                        for ip_sub in range(len_ipams):
                            if default_net_ipam == 'default-network-ipam':
                                prefix = default_net_ipam + \
                                    ' (' + net_domain + ':' + net_project + ')'
                                prefix = prefix.strip().split('\n')[0]
                            else:
                                prefix = default_net_ipam
                            if 'enable_dhcp' in net_ipam_refs[
                                    'attr']['ipam_subnets'][ip_sub]:
                                dhcp_api = net_ipam_refs['attr'][
                                    'ipam_subnets'][ip_sub]['enable_dhcp']
                            else:
                                dhcp_api = False
                            if dhcp_api:
                                dhcp_api = 'Enabled'
                            else:
                                dhcp_api = 'Disabled'
                            cidr_ip_prefix = net_ipam_refs['attr'][
                                'ipam_subnets'][ip_sub]['subnet']['ip_prefix']
                            cidr_ip_prefix_len = str(
                                net_ipam_refs['attr']['ipam_subnets'][ip_sub]['subnet']['ip_prefix_len'])
                            cidr_default_gateway = net_ipam_refs['attr'][
                                'ipam_subnets'][ip_sub]['default_gateway']
                            cidr_prefix_and_len = cidr_ip_prefix + \
                                '/' + cidr_ip_prefix_len
                            cidr_string = cidr_prefix_and_len + \
                                ':' + cidr_default_gateway
                            alloc_pool = net_ipam_refs['attr']['ipam_subnets'][ip_sub]['allocation_pools']
                            if alloc_pool:
                                alloc_pool_string = alloc_pool
                            else:
                                alloc_pool_string  = ''
                            ip_block_list.append(
                                prefix +
                                ':' +
                                cidr_string +
                                ':' +
                                dhcp_api +
                                ':' +
                                alloc_pool_string)
                            if ip_sub in range(2):
                                ip_block.append(cidr_prefix_and_len)
                    if len(ip_block_list) > 2:
                        ip_string = '(' + \
                            str(len(ip_block_list) - 2) + ' more)'
                        ip_block.append(ip_string)
                    complete_api_data.append(
                        {'key': 'IP Blocks', 'value': ip_block_list})
                    complete_api_data.append(
                        {'key': 'ip_blocks_grid_row', 'value': ip_block})
                if 'route_target_list' in api_data_basic and api_data_basic['route_target_list']:
                    if 'route_target' in api_data_basic['route_target_list']:
                        for route in range(len(api_data_basic['route_target_list']['route_target'])):
                            route_target_list.append(
                                str(api_data_basic['route_target_list']['route_target'][route]).strip('target:'))
                        complete_api_data.append(
                            {'key': 'Route Targets', 'value': route_target_list})
                else:
                    complete_api_data.append(
                        {'key': 'Route Targets', 'value': '-'})
                if 'floating_ip_pools' in api_data_basic:
                    for fip in range(len(api_data_basic['floating_ip_pools'])):
                        fip_api = api_data_basic[
                            'floating_ip_pools'][fip]['to']
                        fip_string = fip_api[3]
                        floating_pool.append(fip_string)
                    complete_api_data.append(
                        {'key': 'Floating IP Pools', 'value': floating_pool})
                else:
                    complete_api_data.append(
                        {'key': 'Floating IP Pools', 'value': '-'})
                exists = [ 'true', True ]
                if api_data_basic['id_perms']['enable'] in exists:
                    api_admin_state = 'Up'
                else:
                    api_admin_state = 'Down'
                complete_api_data.append(
                    {'key': 'Admin State', 'value': api_admin_state})
                complete_api_data.append(
                    {'key': 'admin_state_grid_row', 'value': api_admin_state})
                if api_data_basic.get('is_shared'):
                    shared = 'Enabled'
                else:
                    shared = 'Disabled'
                complete_api_data.append(
                    {'key': 'Shared', 'value': shared}) 
                complete_api_data.append(
                    {'key': 'shared_grid_row', 'value': shared})
                if 'router_external' in api_data_basic:
                    if not api_data_basic.get('router_external'):
                        external = 'Disabled'
                    elif api_data_basic.get('router_external'):
                        external = 'Enabled'
                else:
                    external = 'Enabled'
                complete_api_data.append(
                    {'key': 'External', 'value': external})
                display_name = api_data_basic.get('display_name')
                complete_api_data.append(
                    {'key': 'Display Name', 'value': display_name})
                if 'network_ipam_refs' in api_data_basic:
                    for ipams in range(len(api_data_basic['network_ipam_refs'])):
                        if api_data_basic['network_ipam_refs'][
                                ipams]['attr'].get('host_routes'):
                            host_route_value = api_data_basic['network_ipam_refs'][
                                ipams]['attr']['host_routes']['route']
                            ipam_refs_to = api_data_basic[
                                'network_ipam_refs'][ipams]['to']
                            if api_data_basic['network_ipam_refs'][
                                    ipams]['to'][2] == 'default-network-ipam':
                                host_route_sub = []
                                for host_route in range(len(host_route_value)):
                                    host_route_sub.append(
                                        str(host_route_value[host_route]['prefix']))
                                host_route_string = ",".join(host_route_sub)
                                ipam_refs_to = api_data_basic[
                                    'network_ipam_refs'][ipams]['to']
                                ipam_refs_fq = ipam_refs_to[
                                    0] + ':' + ipam_refs_to[1] + ':' + ipam_refs_to[2]
                                host_route_main.append(
                                    ipam_refs_fq +
                                    ' ' +
                                    host_route_string)
                            else:
                                host_route_sub = []
                                for host_route1 in range(len(host_route_value)):
                                    host_route_sub.append(
                                        str(host_route_value[host_route1]['prefix']))
                                host_route_string = ", ".join(host_route_sub)
                                host_route_main.append(
                                    str(ipam_refs_to[2]) + ' ' + host_route_string)
                    if(len(host_route_main) > 0):
                        complete_api_data.append(
                            {'key': 'Host Routes', 'value': host_route_main})
                    else:
                        complete_api_data.append(
                            {'key': 'Host Routes', 'value': '-'})

                if 'forwarding_mode' in api_data_basic[
                        'virtual_network_properties']:
                    forwarding_mode = api_data_basic[
                        'virtual_network_properties']['forwarding_mode']
                    if forwarding_mode == 'l2':
                        forwarding_mode = forwarding_mode.title() + ' Only'
                    elif forwarding_mode == 'l2_l3':
                        forwarding_mode = 'L2 and L3'
                    else:
                        forwarding_mode = '-'
                    complete_api_data.append(
                        {'key': 'Forwarding Mode', 'value': forwarding_mode})
                if 'vxlan_network_identifier' in api_data_basic[
                        'virtual_network_properties']:
                    complete_api_data.append(
                        {
                            'key': 'VxLAN Identifier',
                            'value': str(
                                api_data_basic['virtual_network_properties']['vxlan_network_identifier']).replace(
                                'None',
                                'Automatic')})
                else:
                    complete_api_data.append(
                        {'key': 'VxLAN Identifier', 'value': '-'})
                if self.ui.match_ui_kv(
                        complete_api_data,
                        dom_arry_basic):
                    self.logger.info(
                        "VN config details matched on Config->Networking->Networks page")
                else:
                    self.logger.error(
                        "VN config details not match on Config->Networking->Networks page")
                    result = result and False
        return result
    # end verify_vn_api_basic_data_in_webui

    def verify_service_template_api_basic_data(self):
        self.logger.info(
            "Verifying service template api server data on Config->Services->Service Templates page...")
        self.logger.debug(self.dash)
        result = True
        service_temp_list_api = self.ui.get_service_template_list_api(
        )
        for temp in range(len(service_temp_list_api['service-templates']) - 1):
            interface_list = []
            api_fq_name = service_temp_list_api[
                'service-templates'][temp + 1]['fq_name'][1]
            self.ui.click_configure_service_template()
            rows = self.ui.get_rows()
            self.logger.info(
                "Service template fq_name %s exists in api server..checking if exists in webui as well" %
                (api_fq_name))
            for i in range(len(rows)):
                dom_arry_basic = []
                match_flag = 0
                j = 0
                if rows[i].find_elements_by_tag_name(
                        'div')[2].text == api_fq_name:
                    self.logger.info(
                        "Service template fq_name %s matched in webui..Verifying basic view details..." %
                        (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    rows_div = rows[i].find_elements_by_tag_name('div')
                    dom_arry_basic.append(
                        {'key': 'Name_grid_row', 'value': rows_div[2].text})
                    dom_arry_basic.append(
                        {'key': 'Mode_grid_row', 'value': rows_div[3].text})
                    dom_arry_basic.append(
                        {'key': 'Type_grid_row', 'value': rows_div[4].text})
                    dom_arry_basic.append(
                        {'key': 'Scaling_grid_row', 'value': rows_div[5].text})
                    dom_arry_basic.append(
                        {'key': 'Interface_grid_row', 'value': rows_div[6].text})
                    dom_arry_basic.append(
                        {'key': 'Image_grid_row', 'value': rows_div[7].text})
                    dom_arry_basic.append(
                        {'key': 'Flavor_grid_row', 'value': rows_div[8].text})
                    break
            if not match_flag:
                self.logger.error(
                    "Service template fq_name exists in apiserver but %s not found in webui..." %
                    (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.ui.click_configure_service_template_basic(
                    match_index)
                rows = self.ui.get_rows()
                self.logger.info(
                    "Verify basic view details for service templatefq_name %s " %
                    (api_fq_name))
                rows_detail = rows[match_index + 1].find_element_by_class_name(
                    'slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'Interface Type':
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span10').text})
                    else:
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span10').text})

                service_temp_api_data = self.ui.get_details(
                    service_temp_list_api['service-templates'][temp + 1]['href'])
                complete_api_data = []
                if 'service-template' in service_temp_api_data:
                    api_data_basic = service_temp_api_data.get(
                        'service-template')
                if 'fq_name' in api_data_basic:
                    complete_api_data.append(
                        {'key': 'Template', 'value': str(api_data_basic['fq_name'][1])})
                    complete_api_data.append(
                        {'key': 'Name_grid_row', 'value': str(api_data_basic['fq_name'][1])})
                svc_temp_properties = api_data_basic[
                    'service_template_properties']
                if 'service_mode' in svc_temp_properties:
                    if svc_temp_properties.get('service_mode'):
                        svc_mode_value = str(
                            svc_temp_properties['service_mode']).capitalize()
                    else:
                        svc_mode_value = '-'
                    complete_api_data.append(
                        {'key': 'Mode', 'value': svc_mode_value})
                    complete_api_data.append(
                        {'key': 'Mode_grid_row', 'value': svc_mode_value})
                if 'service_type' in api_data_basic[
                        'service_template_properties']:
                    svc_type_value = str(
                        svc_temp_properties['service_type']).capitalize()
                    complete_api_data.append(
                        {'key': 'Type', 'value': svc_type_value})
                    complete_api_data.append(
                        {'key': 'Type_grid_row', 'value': svc_type_value})
                if 'service_scaling' in svc_temp_properties:
                    if svc_temp_properties['service_scaling']:
                        complete_api_data.append(
                            {
                                'key': 'Scaling',
                                'value': str(
                                    svc_temp_properties['service_scaling']).replace(
                                    'True',
                                    'Enabled')})
                        complete_api_data.append(
                            {
                                'key': 'Scaling_grid_row',
                                'value': str(
                                    svc_temp_properties['service_scaling']).replace(
                                    'True',
                                    'Enabled')})
                    else:
                        complete_api_data.append(
                            {
                                'key': 'Scaling',
                                'value': str(
                                    svc_temp_properties['service_scaling']).replace(
                                    'False',
                                    'Disabled')})
                        complete_api_data.append(
                            {
                                'key': 'Scaling_grid_row',
                                'value': str(
                                    svc_temp_properties['service_scaling']).replace(
                                    'False',
                                    'Disabled')})
                if 'interface_type' in svc_temp_properties:
                    len_svc_temp_properties = len(
                        svc_temp_properties['interface_type'])
                    for interface in range(len_svc_temp_properties):
                        svc_shared_ip = svc_temp_properties[
                            'interface_type'][interface]['shared_ip']
                        svc_static_route_enable = svc_temp_properties[
                            'interface_type'][interface]['static_route_enable']
                        if svc_shared_ip and svc_static_route_enable:
                            interface_type = svc_temp_properties['interface_type'][interface][
                                'service_interface_type'].title() + '(' + 'Shared IP' + ', ' + 'Static Route' + ')'
                        elif not svc_shared_ip and svc_static_route_enable:
                            interface_type = svc_temp_properties['interface_type'][interface][
                                'service_interface_type'].title() + '(' + 'Static Route' + ')'
                        elif svc_shared_ip and not svc_static_route_enable:
                            interface_type = svc_temp_properties['interface_type'][interface][
                                'service_interface_type'].title() + '(' + 'Shared IP' + ')'
                        else:
                            interface_type = svc_temp_properties['interface_type'][
                                interface]['service_interface_type'].title()
                        interface_list.append(interface_type)
                        interface_string = ", ".join(interface_list)
                    complete_api_data.append(
                        {'key': 'Interface Type', 'value': interface_string})
                    complete_api_data.append(
                        {'key': 'Interface_grid_row', 'value': interface_string})
                if 'image_name' in svc_temp_properties:
                    if not svc_temp_properties['image_name']:
                        image_value = ''
                    else:
                        image_value = str(svc_temp_properties['image_name'])
                    complete_api_data.append(
                        {'key': 'Image', 'value': image_value})
                    complete_api_data.append(
                        {'key': 'Image_grid_row', 'value': image_value})
                if 'service_instance_back_refs' in api_data_basic:
                    service_instances = api_data_basic[
                        'service_instance_back_refs']
                    si_text = ''
                    for index, si in enumerate(service_instances):
                        if index == 0:
                            si_text = si['to'][1] + ':' + si['to'][2]
                        else:
                            si_text = si_text + ', ' + \
                                si['to'][1] + ':' + si['to'][2]
                    complete_api_data.append(
                        {'key': 'Instances', 'value': si_text})
                else:
                    complete_api_data.append(
                        {'key': 'Instances', 'value': '-'})
                if 'flavor' in svc_temp_properties:
                    if not svc_temp_properties['flavor']:
                        flavor_value = ''
                    else:
                        flavor_value = str(svc_temp_properties['flavor'])
                    complete_api_data.append(
                        {'key': 'Flavor', 'value': flavor_value})
                    complete_api_data.append(
                        {'key': 'Flavor_grid_row', 'value': flavor_value})
                if self.ui.match_ui_kv(
                        complete_api_data,
                        dom_arry_basic):
                    self.logger.info(
                        "Service template config details matched on Config->Service Templates page")
                else:
                    self.logger.error(
                        "Service template config details match failed on Config->Service Templates page")
                    result = result and False
        return result
    # end verify_service_template_api_basic_data_in_webui

    def verify_floating_ip_api_data(self):
        self.logger.info(
            "Verifying fip api server data on Config->Networking->Manage Floating IPs page...")
        self.logger.info(self.dash)
        result = True
        fip_list_api = self.ui.get_fip_list_api()
        for fips in range(len(fip_list_api['floating-ips'])):
            api_fq_id = fip_list_api['floating-ips'][fips]['uuid']
            self.ui.click_configure_fip()
            project_name = fip_list_api.get(
                'floating-ips')[fips].get('fq_name')[1]
            if project_name == 'default-project':
                continue
            self.ui.select_project(project_name)
            rows = self.ui.get_rows()
            self.logger.info(
                "fip fq_id %s exists in api server..checking if exists in webui as well" %
                (api_fq_id))
            for i in range(len(rows)):
                match_flag = 0
                j = 0
                if rows[i].find_elements_by_tag_name(
                        'div')[4].text == api_fq_id:
                    self.logger.info(
                        "fip fq_id %s matched in webui..Verifying basic view details now" %
                        (api_fq_id))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    dom_arry_basic = []
                    dom_arry_basic.append(
                        {'key': 'IP Address', 'value': rows[i].find_elements_by_tag_name('div')[1].text})
                    dom_arry_basic.append(
                        {'key': 'Instance', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    dom_arry_basic.append({'key': 'Floating IP and Pool', 'value': rows[
                                          i].find_elements_by_tag_name('div')[3].text})
                    dom_arry_basic.append(
                        {'key': 'UUID', 'value': rows[i].find_elements_by_tag_name('div')[4].text})
                    break
            if not match_flag:
                self.logger.error(
                    "fip fq_id exists in apiserver but %s not found in webui..." %
                    (api_fq_id))
                self.logger.info(self.dash)
            else:
                fip_api_data = self.ui.get_details(
                    fip_list_api['floating-ips'][fips]['href'])
                complete_api_data = []
                if 'floating-ip' in fip_api_data:
                    # creating a list of basic view items retrieved from
                    # opserver
                    api_data_basic = fip_api_data.get('floating-ip')
                if api_data_basic.get('floating_ip_address'):
                    complete_api_data.append(
                        {'key': 'IP Address', 'value': api_data_basic['floating_ip_address']})
                if api_data_basic.get('virtual_machine_interface_refs'):
                    vm_api_data = self.ui.get_details(
                        api_data_basic['virtual_machine_interface_refs'][0]['href'])
                    if 'virtual-machine-interface' in vm_api_data:
                        if vm_api_data[
                                'virtual-machine-interface'].get('virtual_machine_refs'):
                            complete_api_data.append({'key': 'Instance', 'value': vm_api_data[
                                                     'virtual-machine-interface']['virtual_machine_refs'][0]['to']})
                else:
                    complete_api_data.append(
                        {'key': 'Instance', 'value': '-'})
                if api_data_basic.get('fq_name'):
                    complete_api_data.append(
                        {
                            'key': 'Floating IP and Pool',
                            'value': api_data_basic['fq_name'][2] +
                            ':' +
                            api_data_basic['fq_name'][3]})
                if api_data_basic.get('fq_name'):
                    complete_api_data.append(
                        {'key': 'UUID', 'value': api_data_basic['fq_name'][4]})
                if self.ui.match_ui_kv(
                        complete_api_data,
                        dom_arry_basic):
                    self.logger.info("FIP config data matched on Config->Networking->Manage Floating IPs page")
                else:
                    self.logger.error("FIP config data match failed on Config->Networking->Manage Floating IPs page")
                    result = False
        return result
    # end verify_floating_ip_api_data_in_webui

    def verify_policy_api_data(self):
        self.logger.info(
            "Verifying policy api server data on Config->Networking->Policies page ...")
        self.logger.debug(self.dash)
        result = True
        policy_list_api = self.ui.get_policy_list_api()
        for policy in range(len(policy_list_api['network-policys']) - 1):
            pol_list = []
            net_list = []
            service_list = []
            api_fq_name = policy_list_api[
                'network-policys'][policy]['fq_name'][2]
            project_name = policy_list_api[
                'network-policys'][policy]['fq_name'][1]
            self.ui.click_configure_policies()
            if project_name == 'default-project':
                continue
            self.ui.select_project(project_name)
            rows = self.ui.get_rows()
            self.logger.info(
                "Policy fq_name %s exists in api server..checking if exists in webui as well" %
                (api_fq_name))
            for i in range(len(rows)):
                dom_arry_basic = []
                match_flag = 0
                detail = 0
                if rows[i].find_elements_by_tag_name(
                        'div')[2].text == api_fq_name:
                    self.logger.info(
                        "Policy fq_name %s matched in webui..Verifying basic view details..." %
                        (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    dom_arry_basic.append(
                        {'key': 'Policy', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    net_grid_row_value = rows[i].find_elements_by_tag_name(
                        'div')[3].text.splitlines()
                    dom_arry_basic.append(
                        {'key': 'Associated_Networks_grid_row', 'value': net_grid_row_value})
                    dom_arry_basic.append({'key': 'Rules_grid_row', 'value': rows[
                                          i].find_elements_by_tag_name('div')[4].text.splitlines()})
                    break
            if not match_flag:
                self.logger.error(
                    "Policy fq name exists in apiserver but %s not found in webui..." %
                    (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.ui.click_configure_policies_basic(match_index)
                rows = self.ui.get_rows()
                self.logger.info(
                    "Verify basic view details for policy fq_name %s " %
                    (api_fq_name))
                rows_detail = rows[match_index + 1].find_element_by_class_name(
                    'slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                while(detail < len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'Associated Networks':
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span11').text.split()})
                    elif text1 == 'Rules':
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span11').text.splitlines()})
                    detail = detail + 2
                policy_api_data = self.ui.get_details(
                    policy_list_api['network-policys'][policy]['href'])
                complete_api_data = []
                if 'network-policy' in policy_api_data:
                    api_data_basic = policy_api_data.get('network-policy')
                if 'fq_name' in api_data_basic:
                    complete_api_data.append(
                        {'key': 'Policy', 'value': api_data_basic['fq_name'][2]})
                if 'virtual_network_back_refs' in api_data_basic:
                    for net in range(len(api_data_basic['virtual_network_back_refs'])):
                        api_project = api_data_basic[
                            'virtual_network_back_refs'][net]['to'][1]
                        if project_name == api_project:
                            fq = api_data_basic[
                                'virtual_network_back_refs'][net]['to'][2]
                        else:
                            fq = ':'.join(
                                api_data_basic['virtual_network_back_refs'][net]['to'])
                        net_list.append(fq)
                    complete_api_data.append(
                        {'key': 'Associated Networks', 'value': net_list})
                    net_list_len = len(net_list)
                    if net_list_len > 2:
                        net_list_grid_row = net_list[:2]
                        more_string = '(' + str(net_list_len - 2) + ' more)'
                        net_list_grid_row.append(more_string)
                        complete_api_data.append(
                            {'key': 'Associated_Networks_grid_row', 'value': net_list_grid_row})
                    else:
                        complete_api_data.append(
                            {'key': 'Associated_Networks_grid_row', 'value': net_list})
                if 'network_policy_entries' in api_data_basic:
                    for rules in range(len(api_data_basic['network_policy_entries']['policy_rule'])):
                        dst_ports = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['dst_ports']
                        src_ports = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['src_ports']
                        source_port = []
                        desti_port = []
                        if dst_ports[0]['start_port'] == -1:
                            desti_port = 'any'
                        else:
                            for item in dst_ports:
                                if item['start_port'] == item['end_port']:
                                    desti_port.append(item['start_port'])
                                else:
                                    port_range = str(item['start_port']) + \
                                        '-' + \
                                        str(item['end_port'])
                                    desti_port.append(port_range)
                        if isinstance(desti_port, list):
                            desti_port = str(desti_port)
                            desti_port = '[ ' + desti_port[1:-1] + ' ]'

                        if src_ports[0]['start_port'] == -1:
                            source_port = 'any'
                        else:
                            for item in src_ports:
                                if item['start_port'] == item['end_port']:
                                    source_port.append(item['start_port'])
                                else:
                                    port_range = str(item['start_port']) + \
                                        '-' + \
                                        str(item['end_port'])
                                    source_port.append(port_range)
                        if isinstance(source_port, list):
                            source_port = str(source_port)
                            source_port = '[ ' + source_port[1:-1] + ' ]'

                        api_src_vnet = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['src_addresses'][0]['virtual_network']
                        api_dst_vnet = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['dst_addresses'][0]['virtual_network']
                        api_vnet_match_list = [
                            'default-domain:default-project:default-virtual-network',
                            'any',
                            'default-domain:default-project:__link_local__',
                            'default-domain:default-project:ip-fabric']
                        if api_src_vnet:
                            if api_src_vnet in api_vnet_match_list:
                                source_network = api_src_vnet
                            else:
                                src_vnet_split = api_src_vnet.split(':')
                                if project_name == src_vnet_split[1]:
                                    source_network = src_vnet_split[2]
                                else:
                                    source_network = src_vnet_split[
                                        2] + ' (' + src_vnet_split[0] + ':' + src_vnet_split[1] + ')'
                        else:
                            api_src_vnet = ''
                        if api_dst_vnet:
                            if api_dst_vnet in api_vnet_match_list:
                                dest_network = api_dst_vnet
                            else:
                                dst_vnet_split = api_dst_vnet.split(':')
                                if project_name == dst_vnet_split[1]:
                                    dest_network = dst_vnet_split[2]
                                else:
                                    dest_network = dst_vnet_split[
                                        2] + ' (' + dst_vnet_split[0] + ':' + dst_vnet_split[1] + ')'
                        else:
                            api_dst_vnet = ''
                        action_list = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['action_list']
                        protocol = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['protocol']
                        direction = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['direction']
                        if action_list.get('apply_service'):
                            for service in range(len(action_list['apply_service'])):
                                service_list.append(
                                    action_list['apply_service'][service])
                            service_string = ",".join(service_list)
                            policy_text = 'protocol' + ' ' + protocol + ' ' + 'network' + ' ' + source_network + ' ' + 'ports' + ' ' + source_port + ' ' + \
                                direction + ' ' + 'network' + ' ' + dest_network + ' ' + 'ports' + \
                                ' ' + desti_port + ' ' + \
                                'apply_service' + ' ' + service_string
                            pol_list.append(policy_text)
                        else:

                            policy_text = action_list['simple_action'] + ' ' + 'protocol' + ' ' + protocol + ' ' + 'network' + ' ' + source_network + \
                                ' ' + 'ports' + ' ' + source_port + ' ' + direction + ' ' + \
                                'network' + ' ' + dest_network + \
                                ' ' + 'ports' + ' ' + desti_port
                            pol_list.append(policy_text)
                    complete_api_data.append(
                        {'key': 'Rules', 'value': pol_list})
                    if len(pol_list) > 2:
                        more_count = len(pol_list) - 2
                        pol_list_grid_row = pol_list[:2]
                        more_text = '(' + str(more_count) + ' more)'
                        pol_list_grid_row.append(more_text)
                    else:
                        pol_list_grid_row = pol_list
                    complete_api_data.append(
                        {'key': 'Rules_grid_row', 'value': pol_list_grid_row})
                if self.ui.match_ui_kv(
                        complete_api_data,
                        dom_arry_basic):
                    self.logger.info("Policy config details matched on Config->Networking->Policies page")
                else:
                    self.logger.error(
                        "Policy config details match failed on Config->Networking->Policies page")
                    result = result and False
        return result
    # end verify_policy_api_basic_data_in_webui

    def verify_ipam_api_data(self):
        self.logger.info(
            "Verifying ipam config data on Config->Networking->IPAMs page")
        self.logger.debug(self.dash)
        result = True
        ipam_list_api = self.ui.get_ipam_list_api()
        for ipam in range(len(ipam_list_api['network-ipams'])):
            net_list = []
            api_fq_name = ipam_list_api['network-ipams'][ipam]['fq_name'][2]
            project_name = ipam_list_api['network-ipams'][ipam]['fq_name'][1]
            if project_name == 'default-project':
                continue
            self.ui.click_configure_ipam()
            self.ui.select_project(project_name)
            rows = self.ui.get_rows()
            self.logger.info(
                "Ipam fq_name %s exists in api server..checking if exists in webui as well" %
                (api_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                j = 0
                dom_arry_basic = []
                if rows[i].find_elements_by_tag_name(
                        'div')[2].text == api_fq_name:
                    self.logger.info(
                        "Ipam fq name %s matched in webui..Verifying basic view details..." %
                        (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    ipam_fq_name = rows[
                        i].find_elements_by_tag_name('div')[2].text
                    dom_arry_basic.append(
                        {'key': 'Name_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    ip_grid_row_value = ' '.join(
                        rows[i].find_elements_by_tag_name('div')[3].text.splitlines())
                    dom_arry_basic.append(
                        {'key': 'IP_grid_row', 'value': ip_grid_row_value})
                    dom_arry_basic.append(
                        {'key': 'DNS_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[4].text})
                    dom_arry_basic.append(
                        {'key': 'NTP_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[5].text})
                    break
            if not match_flag:
                self.logger.error(
                    "Ipam fq_name exists in apiserver but %s not found in webui..." %
                    (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.ui.click_configure_ipam_basic(match_index)
                rows = self.ui.get_rows()
                self.logger.info(
                    "Verify basic view details for ipam fq_name %s " %
                    (api_fq_name))
                rows_detail = rows[match_index + 1].find_element_by_class_name(
                    'slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'IP Blocks':
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span10').text})
                    else:
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span10').text})

                ipam_api_data = self.ui.get_details(
                    ipam_list_api['network-ipams'][ipam]['href'])
                complete_api_data = []
                if 'network-ipam' in ipam_api_data:
                    api_data_basic = ipam_api_data.get('network-ipam')
                if 'fq_name' in api_data_basic:
                    complete_api_data.append(
                        {'key': 'IPAM Name', 'value': str(api_data_basic['fq_name'][2])})
                    complete_api_data.append(
                        {'key': 'Name_grid_row', 'value': str(api_data_basic['fq_name'][2])})
                if api_data_basic.get('network_ipam_mgmt'):
                    if api_data_basic['network_ipam_mgmt'].get(
                            'ipam_dns_method'):
                        if api_data_basic['network_ipam_mgmt'][
                                'ipam_dns_method'] == 'default-dns-server':
                            complete_api_data.append(
                                {'key': 'DNS Server', 'value': '-'})
                            complete_api_data.append(
                                {'key': 'DNS_grid_row', 'value': '-'})
                        elif api_data_basic['network_ipam_mgmt']['ipam_dns_method'] == 'none':
                            complete_api_data.append(
                                {'key': 'DNS Server', 'value': 'DNS Mode : None'})
                            complete_api_data.append(
                                {'key': 'DNS_grid_row', 'value': 'DNS Mode : None'})
                        elif api_data_basic['network_ipam_mgmt']['ipam_dns_method'] == 'virtual-dns-server':
                            complete_api_data.append(
                                {
                                    'key': 'DNS Server',
                                    'value': 'Virtual DNS:' +
                                    ' ' +
                                    api_data_basic['network_ipam_mgmt']['ipam_dns_server']['virtual_dns_server_name']})
                            complete_api_data.append(
                                {
                                    'key': 'DNS_grid_row',
                                    'value': 'Virtual DNS:' +
                                    ' ' +
                                    api_data_basic['network_ipam_mgmt']['ipam_dns_server']['virtual_dns_server_name']})
                        elif api_data_basic['network_ipam_mgmt']['ipam_dns_method'] == 'tenant-dns-server':
                            dns_server_value = str(
                                api_data_basic['network_ipam_mgmt']['ipam_dns_method']).split('-')[0].title() + ' ' + 'Managed' + ' ' + 'DNS' + ':' + ' ' + str(
                                api_data_basic['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'][0])
                            complete_api_data.append(
                                {'key': 'DNS Server', 'value': dns_server_value})
                            complete_api_data.append(
                                {'key': 'DNS_grid_row', 'value': dns_server_value})
                else:
                    complete_api_data.append(
                        {'key': 'DNS Server', 'value': '-'})
                    complete_api_data.append(
                        {'key': 'DNS_grid_row', 'value': '-'})
                if api_data_basic.get('network_ipam_mgmt'):
                    if api_data_basic['network_ipam_mgmt'].get(
                            'dhcp_option_list'):
                        if api_data_basic['network_ipam_mgmt'][
                                'dhcp_option_list'].get('dhcp_option'):
                            if len(
                                    api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option']) > 1:
                                ntp_server_value = str(api_data_basic['network_ipam_mgmt']['dhcp_option_list'][
                                                       'dhcp_option'][0]['dhcp_option_value'])
                                complete_api_data.append({'key': 'Domain Name', 'value': str(api_data_basic[
                                                         'network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][1]['dhcp_option_value'])})
                                complete_api_data.append(
                                    {'key': 'NTP Server', 'value': ntp_server_value})
                                complete_api_data.append(
                                    {'key': 'NTP_grid_row', 'value': ntp_server_value})

                            elif api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][0]['dhcp_option_name'] == '4':
                                ntp_server_value = str(api_data_basic['network_ipam_mgmt']['dhcp_option_list'][
                                                       'dhcp_option'][0]['dhcp_option_value'])
                                complete_api_data.append(
                                    {'key': 'NTP Server', 'value': ntp_server_value})
                                complete_api_data.append(
                                    {'key': 'NTP_grid_row', 'value': ntp_server_value})
                            elif api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][0]['dhcp_option_name'] == '15':
                                complete_api_data.append({'key': 'Domain Name', 'value': str(api_data_basic[
                                                         'network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][0]['dhcp_option_value'])})
                        else:
                            complete_api_data.append(
                                {'key': 'NTP Server', 'value': '-'})
                            complete_api_data.append(
                                {'key': 'NTP_grid_row', 'value': '-'})
                            complete_api_data.append(
                                {'key': 'Domain Name', 'value': '-'})
                else:
                    complete_api_data.append(
                        {'key': 'NTP Server', 'value': '-'})
                    complete_api_data.append(
                        {'key': 'NTP_grid_row', 'value': '-'})
                    complete_api_data.append(
                        {'key': 'Domain Name', 'value': '-'})
                if 'virtual_network_back_refs' in api_data_basic:
                    for net in range(len(api_data_basic['virtual_network_back_refs'])):
                        for ip_sub in range(len(api_data_basic['virtual_network_back_refs'][net]['attr']['ipam_subnets'])):
                            api_project = api_data_basic[
                                'virtual_network_back_refs'][net]['to'][1]
                            if project_name == api_project:
                                fq = str(
                                    api_data_basic['virtual_network_back_refs'][net]['to'][2])
                            else:
                                fq = ':'.join(
                                    api_data_basic['virtual_network_back_refs'][net]['to'])
                            ip_prefix = str(api_data_basic['virtual_network_back_refs'][net][
                                            'attr']['ipam_subnets'][ip_sub]['subnet']['ip_prefix'])
                            ip_prefix_len = str(api_data_basic['virtual_network_back_refs'][net]['attr'][
                                'ipam_subnets'][ip_sub]['subnet']['ip_prefix_len'])
                            default_gateway = str(api_data_basic['virtual_network_back_refs'][net][
                                                  'attr']['ipam_subnets'][ip_sub]['default_gateway'])
                            net_list.append(
                                fq +
                                ' - ' +
                                ip_prefix +
                                '/' +
                                ip_prefix_len +
                                '(' +
                                default_gateway +
                                ')')
                    net_string = ' '.join(net_list)
                    complete_api_data.append(
                        {'key': 'IP Blocks', 'value': net_string})
                    if len(net_list) > 2:
                        net_string_grid_row = ' '.join(
                            net_list[:2]) + ' (' + str(len(net_list) - 2) + ' more)'
                    else:
                        net_string_grid_row = net_string
                    complete_api_data.append(
                        {'key': 'IP_grid_row', 'value': net_string_grid_row})
                if self.ui.match_ui_kv(
                        complete_api_data,
                        dom_arry_basic):
                    self.logger.info(
                        "Ipam config data matched on Config->Networking->IPAM")
                else:
                    self.logger.error(
                        "Ipam config data match failed on Config->Networking->IPAM")
                    result = result and False
        return result
    # end verify_ipam_api_data_in_webui

    def verify_vm_ops_data_in_webui(self, fixture):
        self.logger.info(
            "Verifying vn %s opserver data on Monitor->Networking->Instances page" %
            (fixture.vn_name))
        vm_list = self.ui.get_vm_list_ops()

        if not self.ui.click_monitor_instances():
            result = result and False
        rows = self.ui.get_rows()
        if len(rows) != len(vm_list):
            self.logger.error(" VM count not matched in webui")
        else:
            self.logger.info(" VM count matched in webui")
        for i in range(len(vm_list)):
            vm_name = vm_list[i]['name']
    # end verify_vm_ops_data_in_webui

    def verify_vn_ops_data_in_webui(self, fixture):
        vn_list = self.ui.get_vn_list_ops(fixture)
        self.logger.info(
            "VN details for %s got from ops server and Verifying in webui : " %
            (vn_list))
        if not self.ui.click_configure_networks():
            result = result and False
        rows = self.ui.get_rows()
        ln = len(vn_list)
        for i in range(ln):
            vn_name = vn_list[i]['name']
            details = self.ui.get_vn_details(vn_list[i]['href'])
            UveVirtualNetworkConfig
            if 'UveVirtualNetwokConfig' in details:
                total_acl_rules_ops
            if 'UveVirtualNetworkAgent' in details:
                UveVirtualNetworkAgent_dict = details['UveVirtualNetworkAgent']
                egress_flow_count_api = details[
                    'UveVirtualNetworkAgent']['egress_flow_count']
                ingress_flow_count_api = details[
                    'UveVirtualNetworkAgent']['ingress_flow_count']
                interface_list_count_api = len(
                    details['UveVirtualNetworkAgent']['interface_list_count'])
                total_acl_rules_count = details[
                    'UveVirtualNetworkAgent']['total_acl_rules']
                if self.ui.check_element_exists_by_xpath(
                        row[j + 1], "//label[contains(text(), 'Ingress Flows')]"):
                    for n in range(floating_ip_length_api):
                        fip_api = details[
                            'virtual-network']['floating_ip_pools'][n]['to']
                        if fip_ui[n] == fip_api[3] + \
                                ' (' + fip_api[0] + ':' + fip_api[1] + ')':
                            self.logger.info(" Fip matched ")
            if not self.ui.click_monitor_networks():
                result = result and False
            for j in range(len(rows)):
                rows = self.browser.find_element_by_class_name(
                    'k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                fq_name = rows[j].find_elements_by_tag_name('a')[1].text
                if(fq_name == vn_list[i]['name']):
                    self.logger.info(" %s VN verified in monitor page " %
                                     (fq_name))
                    rows[j].find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('a').click()
                    rows = self.ui.get_rows()
                    expanded_row = rows[
                        j +
                        1].find_element_by_class_name('inline row-fluid position-relative pull-right margin-0-5')
                    expanded_row.find_element_by_class_name(
                        'icon-cog icon-only bigger-110').click()
                    expanded_row.find_elements_by_tag_name('a')[1].click()
                    basicdetails_ui_data = rows[
                        j +
                        1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name("row-fluid")
                    ingress_ui = basicdetails_ui_data[0].text.split('\n')[1]
                    egress_ui = basicdetails_ui_data[1].text.split('\n')[1]
                    acl_ui = basicdetails_ui_data[2].text.split('\n')[1]
                    intf_ui = basicdetails_ui_data[3].text.split('\n')[1]
                    vrf_ui = basicdetails_ui_data[4].text.split('\n')[1]
                    break
                else:
                    self.logger.error(" %s VN not found in monitor page " %
                                      (fq_name))
            details = self.ui.get_vn_details_api(vn_list[i]['href'])
            j = 0
            for j in range(len(rows)):
                if not self.ui.click_monitor_networks():
                    result = result and False
                rows = self.browser.find_element_by_class_name(
                    'k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute(
                        'innerHTML') == details['virtual-network']['fq_name'][2]):
                    if rows[j].find_elements_by_tag_name(
                            'td')[4].text == ip_block:
                        self.logger.info("Ip blocks verified ")
                    rows[j].find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('a').click()
                    rows = self.ui.get_rows()
                    ui_ip_block = rows[
                        j +
                        1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(' ')[
                            1] == ip_block and ui_ip_block.split(' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway']):
                        self.logger.info(
                            "Subnets details matched")
                    else:
                        self.logger.error("Ip block not matched")
                    forwarding_mode = rows[
                        j +
                        1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan = rows[
                        j +
                        1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = {'l2_l3': 'L2 and L3'}
                    if network_dict[details[
                            'virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        self.logger.info(" Forwarding mode matched ")
                    else:
                        self.logger.error("Forwarding mode not matched ")
                    if details[
                            'virtual-network']['virtual_network_properties']['vxlan_network_identifier'] is None:
                        vxlan_api = 'Automatic'
                    else:
                        vxlan_api = details[
                            'virtual-network']['virtual_network_properties']['vxlan_network_identifier']
                    if vxlan_api == vxlan:
                        self.logger.info(" Vxlan matched ")
                    else:
                        self.logger.info(" Vxlan not matched ")
                    rows[j].find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('a').click()
                    break
                elif (j == range(len(rows))):
                    self.logger.info(
                        "Vn name %s : %s is not matched in webui  " %
                        (fixture.vn_name, details['virtual-network']['fq_name'][2]))
    # end verify_vn_ops_data_in_webui

    def verify_vn_in_webui(self, fixture):
        self.ui.screenshot('vm_verify')
        if not self.ui.click_configure_networks():
            result = result and False
        time.sleep(2)
        rows = self.ui.get_rows()
        ln = len(rows)
        vn_flag = 0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('div')[2].get_attribute('innerHTML') == fixture.vn_name and rows[
                    i].find_elements_by_tag_name('div')[4].text == fixture.vn_subnets[0]):
                vn_flag = 1
                rows[i].find_elements_by_tag_name(
                    'div')[0].find_element_by_tag_name('i').click()
                rows = self.ui.get_rows()
                ip_blocks = rows[
                    i +
                    1].find_element_by_class_name('span11').text.split('\n')[1]
                if (ip_blocks.split(' ')[0] == ':'.join(
                        fixture.ipam_fq_name) and ip_blocks.split(' ')[1] == fixture.vn_subnets[0]):
                    self.logger.info(
                        "Vn name %s and ip block %s verified in configure page " %
                        (fixture.vn_name, fixture.vn_subnets))
                else:
                    self.logger.error(
                        "Ip block details failed to verify in configure page %s " %
                        (fixture.vn_subnets))
                    self.ui.screenshot('Verify_vn_configure_page_ip_block')
                    vn_flag = 0
                break
        if not self.ui.click_monitor_networks():
            result = result and False
        time.sleep(3)
        rows = self.ui.get_rows()
        vn_entry_flag = 0
        for i in range(len(rows)):
            fq_name = rows[i].find_elements_by_tag_name(
                'div')[1].find_element_by_tag_name('div').text
            if(fq_name == fixture.ipam_fq_name[0] + ":" + fixture.project_name + ":" + fixture.vn_name):
                self.logger.info(" %s VN verified in monitor page " %
                                 (fq_name))
                vn_entry_flag = 1
                break
        if not vn_entry_flag:
            self.logger.error("VN %s Verification failed in monitor page" %
                              (fixture.vn_name))
            self.ui.screenshot('verify_vn_monitor_page')
        if vn_entry_flag:
            self.logger.info(
                " VN %s and subnet verified on config/monitor pages" %
                (fixture.vn_name))
        # if self.ui.verify_uuid_table(fixture.vn_id):
        #     self.logger.info( "VN %s UUID verified in webui table " %(fixture.vn_name))
        # else:
        #     self.logger.error( "VN %s UUID Verification failed in webui table " %(fixture.vn_name))
        # self.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
        fixture.obj = fixture.quantum_fixture.get_vn_obj_if_present(
            fixture.vn_name, fixture.project_id)
        fq_type = 'virtual_network'
        full_fq_name = fixture.vn_fq_name + ':' + fixture.vn_id
        # if self.ui.verify_fq_name_table(full_fq_name, fq_type):
        #     self.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        # else:
        #     self.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        # self.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        return True
    # end verify_vn_in_webui

    def delete_policy(self, fixture):
        self.ui.delete_element(fixture, 'policy_delete')
    # end delete_policy_in_webui

    def delete_svc_instance(self, fixture):
        self.ui.delete_element(fixture, 'svc_instance_delete')
        time.sleep(25)
    # end svc_instance_delete

    def delete_svc_template(self, fixture):
        self.ui.delete_element(fixture, 'svc_template_delete')
    # end svc_template_delete

    def delete_vn(self, fixture):
        self.ui.delete_element(fixture, 'vn_delete')
    # end vn_delete_in_webui

    def delete_ipam(self, fixture):
        if not self.ui.click_configure_ipam():
            result = result and False
        rows = self.ui.get_rows()
        for ipam in range(len(rows)):
            tdArry = rows[ipam].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteIpam').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id(
                        'btnCnfRemoveMainPopupOK').click()
                    if not self.ui.check_error_msg("Delete ipam"):
                        raise Exception("Ipam deletion failed")
                        break
                    self.ui.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s got deleted using webui" % (name))
                    break
    # end ipam_delete_in_webui

    def service_template_delete_in_webui(self, fixture):
        if not self.ui.click_configure_service_template():
            result = result and False
        rows = self.ui.get_rows()
        for temp in range(len(rows)):
            tdArry = rows[temp].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.st_name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeletesvcTemplate').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id('btnCnfDelPopupOK').click()
                    if not self.ui.check_error_msg("Delete service template"):
                        raise Exception("Service template deletion failed")
                        break
                    self.ui.wait_till_ajax_done(self.browser)
                    self.logger.info("%s got deleted using webui" %
                                     (fixture.st_name))
                    break
    # end service_template_delete_in_webui

    def service_instance_delete_in_webui(self, fixture):
        if not self.ui.click_configure_service_instance():
            result = result and False
        rows = self.ui.get_rows()
        for inst in range(len(rows)):
            tdArry = rows[inst].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.si_name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeletesvcInstances').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id(
                        'btnCnfDelSInstPopupOK').click()
                    if not self.ui.check_error_msg("Delete service instance"):
                        raise Exception("Service instance deletion failed")
                        break
                    self.ui.wait_till_ajax_done(self.browser)
                    self.logger.info("%s got deleted using webui" %
                                     (fixture.si_name))
                    break
    # end service_instance_delete_in_webui

    def dns_server_delete(self, name):
        if not self.ui.click_configure_dns_server():
            result = result and False
        rows = self.ui.get_rows()
        for server in range(len(rows)):
            tdArry = rows[server].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteDNSServer').click()
                    self.browser.find_element_by_id('btnCnfDelPopupOK').click()
                    if not self.ui.check_error_msg("Delete dns server"):
                        raise Exception("Dns server deletion failed")
                        break
                    self.ui.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s got deleted using webui" % (name))
                    break
    # end dns_server_delete_in_webui

    def dns_record_delete(self, name):
        if not self.ui.click_configure_dns_record():
            result = result and False
        rows = self.ui.get_rows()
        for record in range(len(rows)):
            tdArry = rows[record].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteDNSRecord').click()
                    self.browser.find_element_by_id(
                        'btnCnfDelMainPopupOK').click()
                    if not self.ui.check_error_msg("Delete dns record"):
                        raise Exception("Dns record deletion failed")
                        break
                    self.ui.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s got deleted using webui" % (name))
                    break
    # end dns_record_delete_in_webui

    def create_vm(self, fixture):
        if not WebuiTest.os_release:
            WebuiTest.os_release = self.os_release
        try:
            self.browser_openstack = fixture.browser_openstack
            con = self.connections.ui_login
            con.login(
                self.browser_openstack,
                con.os_url,
                con.username,
                con.password)
            self.ui.select_project_in_openstack(
                fixture.project_name,
                self.browser_openstack, self.os_release)
            self.ui.click_instances(self.browser_openstack)
            fixture.image_name = 'ubuntu'
            fixture.nova_fixture.get_image(image_name=fixture.image_name)
            time.sleep(2)
            self.ui.click_element(
                'Launch Instance',
                'link_text',
                self.browser_openstack,
                jquery=False,
                wait=5)
            self.logger.info(
                'Creating instance name %s with image name %s using horizon' %
                (fixture.vm_name, fixture.image_name))
            xpath_image_type = "//select[@name='source_type']/option[contains(text(), 'image') or contains(text(),'Image')]"
            self.ui.click_element(
                xpath_image_type,
                'xpath',
                self.browser_openstack,
                jquery=False,
                wait=2)
            xpath_image_name = "//select[@name='image_id']/option[contains(text(), '" + \
                fixture.image_name + "')]"
            self.ui.click_element(
                xpath_image_name,
                'xpath',
                self.browser_openstack,
                jquery=False,
                wait=2)
            self.ui.find_element(
                'id_name',
                browser=self.browser_openstack).send_keys(
                fixture.vm_name)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='flavor']/option[text()='m1.small']").click()
            self.ui.click_element(
                "//input[@value='Launch']",
                'xpath',
                self.browser_openstack,
                jquery=False,
                wait=4)
            networks = self.ui.find_element(
                ['available_network', 'li'], ['id', 'tag'], self.browser_openstack, [1])
            for net in networks:
                vn_match = net.text.split('(')[0]
                if (vn_match == fixture.vn_name):
                    net.find_element_by_class_name('btn').click()
                    break
            self.ui.click_element(
                "//input[@value='Launch']",
                'xpath',
                self.browser_openstack)
            self.ui.wait_till_ajax_done(self.browser_openstack)
            self.logger.debug('VM %s launched using horizon' %
                              (fixture.vm_name))
            self.logger.info('Waiting for VM %s to come into active state' %
                             (fixture.vm_name))
            time.sleep(10)
            rows_os = self.ui.find_element(
                ['form', 'tbody', 'tr'], ['tag', 'tag', 'tag'], self.browser_openstack, [2])
            for i in range(len(rows_os)):
                rows_os = self.ui.find_element(
                    ['form', 'tbody', 'tr'], ['tag', 'tag', 'tag'], self.browser_openstack, [2])
                if(rows_os[i].find_elements_by_tag_name('td')[1].text == fixture.vm_name):
                    counter = 0
                    vm_active = False
                    while not vm_active:
                        vm_active_status1 = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name(
                            'td')[6].text
                        vm_active_status2 = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name('td')[5].text

                        if(vm_active_status1 == 'Active' or vm_active_status2 == 'Active'):
                            self.logger.info(
                                "%s status changed to Active in openstack" %
                                (fixture.vm_name))
                            vm_active = True
                            time.sleep(5)
                        elif(vm_active_status1 == 'Error' or vm_active_status2 == 'Error'):
                            self.logger.error(
                                "%s state went into Error state in openstack" %
                                (fixture.vm_name))
                            self.ui.screenshot(
                                'verify_vm_state_openstack_' +
                                fixture.vm_name,
                                self.browser_openstack)
                            return "Error"
                        else:
                            self.logger.info(
                                "%s state is not yet Active in openstack, waiting for more time..." %
                                (fixture.vm_name))
                            counter = counter + 1
                            time.sleep(3)
                            self.browser_openstack.find_element_by_link_text(
                                'Instances').click()
                            self.ui.wait_till_ajax_done(
                                self.browser_openstack)
                            time.sleep(3)
                            if(counter >= 100):
                                fixuture.logger.error(
                                    "VM %s failed to come into active state" %
                                    (fixture.vm_name))
                                self.ui.screenshot(
                                    'verify_vm_not_active_openstack_' +
                                    fixture.vm_name,
                                    self.browser_openstack)
                                break
            time.sleep(10)
            fixture.vm_obj = fixture.nova_fixture.get_vm_if_present(
                fixture.vm_name, fixture.project_fixture.uuid)
            fixture.vm_objs = fixture.nova_fixture.get_vm_list(
                name_pattern=fixture.vm_name,
                project_id=fixture.project_fixture.uuid)
        except WebDriverException:
            self.logger.error(
                'Error while creating VM %s with image name %s failed in openstack' %
                (fixture.vm_name, fixture.image_name))
            self.ui.screenshot(
                'verify_vm_error_openstack_' +
                fixture.vm_name,
                self.browser_openstack)
            raise
    # end create_vm_in_openstack

    def delete_vm(self, fixture):
        self.browser_openstack = fixture.browser_openstack
        con = self.connections.ui_login
        con.login(
            self.browser_openstack,
            con.os_url,
            con.username,
            con.password)
        project_name = fixture.project_name
        self.ui.select_project_in_openstack(
            project_name,
            self.browser_openstack, self.os_release)
        self.ui.click_instances(self.browser_openstack)
        rows = self.ui.find_element(
            ['instances', 'tbody'], ['id', 'tag'], self.browser_openstack)
        rows = rows.find_elements_by_tag_name('tr')
        for instance in rows:
            if fixture.vm_name == instance.find_element_by_tag_name('a').text:
                instance.find_elements_by_tag_name(
                    'td')[0].find_element_by_tag_name('input').click()
                break
        ln = len(rows)
        launch_instance = self.ui.click_element(
            'instances__action_terminate',
            browser=self.browser_openstack)
        self.ui.click_element(
            'Terminate Instances',
            'link_text',
            self.browser_openstack)
        time.sleep(8)
        self.ui.click_instances(self.browser_openstack)
        if not self.verify_vm_in_openstack(fixture.vm_name):
            self.logger.info("VM %s got deleted using horizon" %
                             (fixture.vm_name))
        else:
            self.logger.error("VM %s exists" % (fixture.vm_name))
    # end vm_delete_in_openstack

    def verify_vm_in_openstack(self, vm_name):
        rows = self.ui.find_element(
            ['instances', 'tbody', 'tr'], ['id', 'tag', 'tag'], self.browser_openstack, [2])
        len_td = len(rows[0].find_elements_by_tag_name('td'))
        if len_td == 1:
            self.logger.info("No vm found")
            return False
        else:
            for instance in rows:
                if vm_name == instance.find_element_by_tag_name('a').text:
                    self.logger.info("%s vm exists" % (vm_name))
                    return True
        return False
    # end verify_vm_in_openstack

    def verify_vm(self, fixture):
        result = True
        try:
            if not self.ui.click_monitor_instances():
                result = result and False
            rows = self.ui.get_rows()
            ln = len(rows)
            vm_flag = 0
            for i in range(len(rows)):
                rows_count = len(rows)
                vm_name = rows[i].find_elements_by_class_name(
                    'slick-cell')[1].text
                vm_uuid = rows[i].find_elements_by_class_name(
                    'slick-cell')[2].text
                vm_vn = rows[i].find_elements_by_class_name(
                    'slick-cell')[3].text.split(' ')[0]
                if(vm_name == fixture.vm_name and fixture.vm_obj.id == vm_uuid and fixture.vn_name == vm_vn):
                    self.logger.info(
                        "VM %s vm exists..will verify row expansion basic details" %
                        (fixture.vm_name))
                    retry_count = 0
                    while True:
                        self.logger.debug("Count is" + str(retry_count))
                        if retry_count > 20:
                            self.logger.error('Vm details failed to load')
                            break
                        self.browser.find_element_by_xpath(
                            "//*[@id='mon_net_instances']").find_element_by_tag_name('a').click()
                        time.sleep(1)
                        rows = self.ui.get_rows()
                        rows[i].find_elements_by_tag_name(
                            'div')[0].find_element_by_tag_name('i').click()
                        try:
                            retry_count = retry_count + 1
                            rows = self.ui.get_rows()
                            rows[
                                i +
                                1].find_elements_by_class_name('row-fluid')[0].click()
                            self.ui.wait_till_ajax_done(self.browser)
                            break
                        except WebDriverException:
                            pass
                    rows = self.ui.get_rows()
                    row_details = rows[i + 1].find_element_by_xpath(
                        "//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')[5]
                    vm_status = row_details.find_elements_by_tag_name(
                        'div')[8].text
                    vm_ip_and_mac = row_details.find_elements_by_tag_name(
                        'div')[2].text
                    assert vm_status == 'Active'
                    assert vm_ip_and_mac.splitlines()[0] == fixture.vm_ip
                    vm_flag = 1
                    break
            assert vm_flag, "VM name or VM uuid or VM ip or VM status verifications in WebUI for VM %s failed" % (
                fixture.vm_name)
            self.ui.screenshot('vm_create_check')
            self.logger.info(
                "Vm name,vm uuid,vm ip and vm status,vm network verification in WebUI for VM %s passed" %
                (fixture.vm_name))
            mon_net_networks = self.ui.find_element('mon_net_networks')
            self.ui.click_element('Networks', 'link_text', mon_net_networks)
            time.sleep(4)
            self.ui.wait_till_ajax_done(self.browser)
            rows = self.ui.get_rows()
            for i in range(len(rows)):
                if(rows[i].find_elements_by_class_name('slick-cell')[1].text == fixture.vn_fq_name.split(':')[0] + ":" + fixture.project_name + ":" + fixture.vn_name):
                    rows[i].find_elements_by_tag_name(
                        'div')[0].find_element_by_tag_name('i').click()
                    time.sleep(2)
                    self.ui.wait_till_ajax_done(self.browser)
                    rows = self.ui.get_rows()
                    vm_ids = rows[i + 1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_class_name(
                        'row-fluid')[5].find_elements_by_tag_name('div')[1].text
                    if fixture.vm_id in vm_ids:
                        self.logger.info(
                            "Vm id matched on Monitor->Netoworking->Networks basic details page %s" %
                            (fixture.vn_name))
                    else:
                        self.logger.error(
                            "Vm id not matched on Monitor->Netoworking->Networks basic details page %s" %
                            (fixture.vm_name))
                        self.ui.screenshot(
                            'vm_create_check' +
                            fixture.vm_name +
                            fixture.vm_id)
                        result = result and False
                    break
            # if self.ui.verify_uuid_table(fixture.vm_id):
            #    self.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            # else:
            #    self.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            # fq_type='virtual_machine'
            # full_fq_name=fixture.vm_id+":"+fixture.vm_id
            # if self.ui.verify_fq_name_table(full_fq_name,fq_type):
            #   self.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            # else:
            #   self.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            self.logger.info("VM verification in WebUI %s passed" %
                             (fixture.vm_name))
            return result
        except WebDriverException:
            self.logger.error("vm %s test error " % (fixture.vm_name))
            self.ui.screenshot(
                'verify_vm_test_openstack_error' +
                fixture.vm_name)
    # end verify_vm_in_webui

    def create_floatingip_pool(self, fixture, pool_name, vn_name):
        try:
            if not self.ui.click_configure_networks():
                result = result and False
            self.ui.select_project(fixture.project_name)
            rows = self.ui.get_rows()
            self.logger.info("Creating floating ip pool %s using webui" %
                             (pool_name))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')
                        [2].get_attribute('innerHTML') == fixture.vn_name):
                    net.find_element_by_class_name('icon-cog').click()
                    time.sleep(3)
                    self.browser.find_element_by_class_name(
                        'tooltip-success').find_element_by_tag_name('i').click()
                    time.sleep(2)
                    self.ui.click_element(
                        "//span[contains(text(), 'Floating IP Pools')]",
                        'xpath')
                    time.sleep(2)
                    icon = self.ui.find_element(
                        "//div[@title='Add Floating IP Pool below']",
                        'xpath')
                    icon.find_element_by_tag_name('i').click()
                    self.ui.send_keys(
                        fixture.pool_name,
                        "//input[@placeholder='Pool Name']",
                        'xpath')
                    self.browser.find_element_by_id(
                        'fipTuples').find_elements_by_tag_name('input')[1].click()
                    project_elements = self.browser.find_elements_by_xpath(
                        "//*[@class = 'select2-match']/..")
                    self._click_if_element_found(
                        fixture.project_name, project_elements)
                    self.ui.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    self.ui.wait_till_ajax_done(self.browser)
                    time.sleep(2)
                    if not self.ui.check_error_msg("Creating fip pool"):
                        raise Exception("Create fip pool failed")
                    self.logger.info("Fip pool %s created using webui" %
                                     (fixture.pool_name))
                    break
        except WebDriverException:
            self.logger.error("Fip %s Error while creating floating ip pool " %
                              (fixture.pool_name))
            self.ui.screenshot("fip_create_error")
            raise
    # end create_floatingip_pool

    def bind_policies(self, fixture):
        policy_fq_names = [
            fixture.quantum_fixture.get_policy_fq_name(x) for x in fixture.policy_obj[
                fixture.vn]]
        result = True
        try:
            if not self.ui.click_configure_networks():
                result = result and False
            self.ui.select_project(fixture.project_name)
            rows = self.ui.get_rows()
            self.logger.info("Binding policies %s using webui" %
                             (policy_fq_names))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')
                        [2].get_attribute('innerHTML') == fixture.vn):
                    net.find_element_by_class_name('icon-cog').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_class_name(
                        'tooltip-success').find_element_by_tag_name('i').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    for policy in policy_fq_names:
                        self.ui.click_element(
                            ['s2id_msNetworkPolicies', 'input'], ['id', 'tag'])
                        pol = policy[2]
                        self.ui.select_from_dropdown(pol)
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    self.ui.wait_till_ajax_done(self.browser)
                    time.sleep(2)
                    if not self.ui.check_error_msg("Binding policies"):
                        raise Exception("Policy association failed")
                    self.logger.info("Associated Policy  %s  using webui" %
                                     (policy_fq_names))
                    time.sleep(5)
                    break
        except WebDriverException:
            self.logger.error(
                "Error while %s binding polices " %
                (policy_fq_names))
            self.ui.screenshot("policy_bind_error")
            raise
    # end bind_policies

    def detach_policies(self, fixture):
        policy_fq_names = [
            fixture.quantum_fixture.get_policy_fq_name(x) for x in fixture.policy_obj[
                fixture.vn]]
        result = True
        try:
            if not self.ui.click_configure_networks():
                result = result and False
            self.ui.select_project(fixture.project_name)
            rows = self.ui.get_rows()
            self.logger.info("Detaching policies %s using webui" %
                             (policy_fq_names))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')
                        [2].get_attribute('innerHTML') == fixture.vn):
                    self.ui.click_element('icon-cog', 'class', net)
                    self.ui.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_class_name(
                        'tooltip-success').find_element_by_tag_name('i').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    for policy in policy_fq_names:
                        ui_policies_obj = self.ui.find_element(
                            ['s2id_msNetworkPolicies', 'li'], ['id', 'tag'], if_elements=[1])
                        pol = policy[2]
                        for indx in range(len(ui_policies_obj) - 1):
                            if ui_policies_obj[indx].find_element_by_tag_name(
                                    'div').text == pol:
                                ui_policies_obj[
                                    indx].find_element_by_tag_name('a').click()
                                break
                        # self.ui.select_from_dropdown(pol)
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    self.ui.wait_till_ajax_done(self.browser)
                    time.sleep(2)
                    if not self.ui.check_error_msg("Detaching policies"):
                        raise Exception("Policy detach failed")
                    self.logger.info("Detached Policies  %s  using webui" %
                                     (policy_fq_names))
                    break
        except WebDriverException:
            self.logger.error(
                "Error while %s detaching polices " %
                (policy_fq_names))
            self.ui.screenshot("policy_detach_error")
    # end detach_policies

    def create_and_assoc_fip(
            self,
            fixture,
            fip_pool_vn_id,
            vm_id,
            vm_name,
            project=None):
        try:
            fixture.vm_name = vm_name
            fixture.vm_id = vm_id
            if not self.ui.click_configure_networks():
                result = result and False
            self.ui.select_project(fixture.project_name)
            rows = self.ui.get_rows()
            self.logger.info("Creating and associating fip %s using webui" %
                             (fip_pool_vn_id))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')
                        [2].get_attribute('innerHTML') == fixture.vn_name):
                    self.ui.click_element(
                        ['config_net_fip', 'a'], ['id', 'tag'])
                    self.ui.select_project(fixture.project_name)
                    self.ui.click_element('btnCreatefip')
                    self.ui.click_element(
                        ["//div[@id='s2id_ddFipPool']", 'a'], ['xpath', 'tag'])
                    fip_fixture_fq = fixture.project_name + ':' + \
                        fixture.vn_name + ':' + fixture.pool_name
                    if not self.ui.select_from_dropdown(
                            fip_fixture_fq,
                            grep=True):
                        self.logger.error(
                            "Fip %s not found in dropdown " %
                            (fip_fixture_fq))
                        self.ui.click_element('btnCreatefipCancel')
                    else:
                        self.ui.click_element('btnCreatefipOK')
                    if not self.ui.check_error_msg("Creating Fip"):
                        raise Exception("Create fip failed")
                    fip_rows = self.ui.find_element('grid-canvas', 'class')
                    rows1 = self.ui.get_rows(fip_rows)
                    fixture_vn_pool = fixture.vn_name + ':' + fixture.pool_name
                    for element in rows1:
                        fip_ui_fq = element.find_elements_by_class_name(
                            'slick-cell')[3].get_attribute('innerHTML')
                        if fip_ui_fq == fixture_vn_pool:
                            element.find_element_by_class_name(
                                'icon-cog').click()
                            self.ui.wait_till_ajax_done(self.browser)
                            element.find_element_by_xpath(
                                "//a[@class='tooltip-success']").click()
                            self.ui.wait_till_ajax_done(self.browser)
                            pool = self.browser.find_element_by_xpath(
                                "//div[@id='s2id_ddAssociate']").find_element_by_tag_name('a').click()
                            time.sleep(1)
                            self.ui.wait_till_ajax_done(self.browser)
                            if self.ui.select_from_dropdown(vm_id, grep=True):
                                self.ui.click_element('btnAssociatePopupOK')
                            else:
                                self.ui.click_element(
                                    'btnAssociatePopupCancel')
                                self.logger.error(
                                    "not able to associate vm id %s as it is not found in dropdown " %
                                    (vm_id))
                            break
                    if not self.ui.check_error_msg("Fip Associate"):
                        raise Exception("Fip association failed")
                    time.sleep(1)
                    break
        except WebDriverException:
            self.logger.error(
                "Error while creating floating ip and associating it.")
            self.ui.screenshot("fip_assoc_error")
            raise
    # end create_and_assoc_fip

    def disassoc_floatingip(self, fixture, vm_id):
        try:
            if not self.ui.click_configure_fip():
                result = result and False
            self.ui.select_project(fixture.project_name)
            gridfip = self.ui.find_element('gridfip')
            rows = self.ui.get_rows(gridfip)
            self.logger.info("Disassociating fip %s using webui" %
                             (fixture.pool_name))
            for element in rows:
                if element.find_elements_by_class_name(
                        'slick-cell')[2].get_attribute('innerHTML') == vm_id:
                    element.find_element_by_class_name('icon-cog').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    element.find_elements_by_xpath(
                        "//a[@class='tooltip-success']")[1].click()
                    self.ui.wait_till_ajax_done(self.browser)
                    self.ui.click_element('btnDisassociatePopupOK')
                    self.ui.check_error_msg('disassociate_vm')
                    self.ui.delete_element(fixture, 'disassociate_fip')
                    break
        except WebDriverException:
            self.logger.error(
                "Error while disassociating fip.")
            self.ui.screenshot("fip_disassoc_error")
    # end disassoc_floatingip

    def delete_floatingip_pool(self, fixture):
        result = True
        try:
            if not self.ui.click_configure_networks():
                result = result and False
            self.ui.select_project(fixture.project_name)
            rows = self.ui.get_rows()
            self.logger.info("Deleting fip pool %s using webui" %
                             (fixture.pool_name))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')
                        [2].get_attribute('innerHTML') == fixture.vn_name):
                    net.find_element_by_class_name('icon-cog').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_class_name(
                        'tooltip-success').find_element_by_tag_name('i').click()
                    self.ui.wait_till_ajax_done(self.browser)
                    fip_text = net.find_element_by_xpath(
                        "//span[contains(text(), 'Floating IP Pools')]")
                    fip_text.find_element_by_xpath(
                        '..').find_element_by_tag_name('i').click()
                    self.ui.click_element(
                        ['fipTuples', 'icon-minus'], ['id', 'class'])
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    self.ui.wait_till_ajax_done(self.browser)
                    time.sleep(2)
                    if not self.ui.check_error_msg("Deleting_fip"):
                        raise Exception("Delete fip failed")
                    self.logger.info("Deleted fip pool  %s  using webui" %
                                     (fixture.pool_name))
                    time.sleep(20)
                    break
        except WebDriverException:
            self.logger.error(
                "Error while %s deleting fip" %
                (fixture.pool_name))
            self.ui.screenshot("fip_delete_error")
    # end delete_fip

    def verify_fip_in_webui(self, fixture):
        if not self.ui.click_configure_networks():
            result = result and False
        rows = self.ui.find_element(['gridVN', 'tbody', 'tr'], [
                                    'id', 'tag', 'tag'], if_elements=[2])
        for i in range(len(rows)):
            vn_name = rows[i].find_elements_by_tag_name('td')[2].text
            if vn_name == fixture.vn_name:
                rows[i].find_elements_by_tag_name(
                    'td')[0].find_element_by_tag_name('a').click()
                rows = self.ui.get_rows()
                fip_check = rows[
                    i + 1].find_elements_by_xpath("//td/div/div/div")[1].text
                if fip_check.split('\n')[1].split(' ')[0] == fixture.pool_name:
                    self.logger.info(
                        "Fip pool %s verified in WebUI configure network page" %
                        (fixture.pool_name))
                    break
        self.ui.click_element("//*[@id='config_net_fip']/a", 'xpath')
        self.ui.wait_till_ajax_done(self.browser)
        rows = self.browser.find_element_by_xpath(
            "//div[@id='gridfip']/table/tbody").find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            fip = rows[i].find_elements_by_tag_name('td')[3].text.split(':')[1]
            vn = rows[i].find_elements_by_tag_name('td')[3].text.split(':')[0]
            fip_ip = rows[i].find_elements_by_class_name('slick-cell')[1].text
            if rows[i].find_elements_by_tag_name(
                    'td')[2].text == fixture.vm_id:
                if vn == fixture.vn_name and fip == fixture.pool_name:
                    self.logger.info("Fip is found attached with vm %s " %
                                     (fixture.vm_name))
                    self.logger.info("VM %s is found associated with FIP %s " %
                                     (fixture.vm_name, fip))
                else:
                    self.logger.info(
                        "Association of %s VM failed with FIP %s " %
                        (fixture.vm_name, fip))
                    break
        if not self.ui.click_monitor_instances():
            result = result and False
        rows = self.browser.find_element_by_class_name(
            'k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vm_flag = 0
        for i in range(len(rows)):
            vm_name = rows[i].find_elements_by_tag_name(
                'td')[1].find_element_by_tag_name('div').text
            vm_uuid = rows[i].find_elements_by_tag_name('td')[2].text
            vm_vn = rows[i].find_elements_by_tag_name(
                'td')[3].text.split(' ')[0]
            if(vm_name == fixture.vm_name and fixture.vm_id == vm_uuid and vm_vn == fixture.vn_name):
                rows[i].find_elements_by_tag_name(
                    'td')[0].find_element_by_tag_name('a').click()
                self.ui.wait_till_ajax_done(self.browser)
                rows = self.browser.find_element_by_class_name(
                    'k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                fip_check_vm = rows[i + 1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_tag_name(
                    'div')[0].find_elements_by_tag_name('div')[1].text
                if fip_check_vm.split(' ')[0] == fip_ip and fip_check_vm.split(' ')[
                        1] == '\(' + 'default-domain' + ':' + fixture.project_name + ':' + fixture.vn_name + '\)':
                    self.logger.info(
                        "FIP verified in monitor instance page for vm %s " %
                        (fixture.vm_name))
                else:
                    self.logger.info(
                        "FIP failed to verify in monitor instance page for vm %s" %
                        (fixture.vm_name))
                    break
    # end verify_fip_in_webui

    def verify_project_quotas(self):
        self.logger.info(
            "Verifying project quotas api server data on Config->Nwetworking->project quotas page ...")
        result = True
        const_str = ['Not Set', 'Unlimited']
        fip_list_api = self.ui.get_fip_list_api()
        ipam_list_api = self.ui.get_ipam_list_api()
        policy_list_api = self.ui.get_policy_list_api()
        svc_instance_list_api = self.ui.get_service_instance_list_api()
        floating_ip_pool_list_api = self.ui.get_floating_pool_list_api()
        security_grp_list_api = self.ui.get_security_group_list_api()
        vn_list_api = self.ui.get_vn_list_api()
        project_list_api = self.ui.get_project_list_api()
        vm_intf_refs_list_api = self.ui.get_vm_intf_refs_list_api()
        routers_list_api = self.ui.get_routers_list_api()
        routers_count_dict = self.ui.count_quotas(
            routers_list_api.get('logical-routers'))
        subnets_count_dict = self.ui.subnets_count_quotas(
            vn_list_api['virtual-networks'])
        security_grp_rules_count_dict = self.ui.security_grp_rules_count_quotas(
            security_grp_list_api.get('security-groups'))
        vn_count_dict = self.ui.count_quotas(
            vn_list_api.get('virtual-networks'))
        fips_count_dict = self.ui.count_quotas(
            fip_list_api.get('floating-ips'))
        policy_count_dict = self.ui.count_quotas(
            policy_list_api.get('network-policys'))
        ipam_count_dict = self.ui.count_quotas(
            ipam_list_api.get('network-ipams'))
        fip_pool_count_dict = self.ui.count_quotas(
            floating_ip_pool_list_api.get('floating-ip-pools'))
        svc_instance_count_dict = self.ui.count_quotas(
            svc_instance_list_api.get('service-instances'))
        security_grp_count_dict = self.ui.count_quotas(
            security_grp_list_api.get('security-groups'))
        ports_count_dict = self.ui.count_quotas(
            vm_intf_refs_list_api.get('virtual-machine-interfaces'))
        for index, project in enumerate(project_list_api['projects']):
            prj = project.get('fq_name')[1]
            if prj == 'default-project':
                continue
            api_data = []
            prj_quotas_dict = self.ui.get_details(
                project_list_api['projects'][index]['href']).get('project').get('quota')
            not_found = [-1, None]
            if prj_quotas_dict['subnet'] in not_found:
                subnets_limit_api = const_str
            else:
                subnets_limit_api = prj_quotas_dict['subnet']
            if prj_quotas_dict['virtual_machine_interface'] in not_found:
                ports_limit_api = const_str
            else:
                ports_limit_api = prj_quotas_dict['virtual_machine_interface']
            if prj_quotas_dict['security_group_rule'] in not_found:
                security_grp_rules_limit_api = 'Unlimited'
            else:
                security_grp_rules_limit_api = prj_quotas_dict[
                    'security_group_rule']
            if prj_quotas_dict['security_group'] in not_found:
                security_grps_limit_api = 'Unlimited'
            else:
                security_grps_limit_api = prj_quotas_dict['security_group']
            if prj_quotas_dict['virtual_network'] in not_found:
                vnets_limit_api = const_str
            else:
                vnets_limit_api = prj_quotas_dict['virtual_network']
            if not prj_quotas_dict['floating_ip_pool']:
                pools_limit_api = 'Not Set'
            else:
                pools_limit_api = prj_quotas_dict['floating_ip_pool']
            if prj_quotas_dict['floating_ip'] in not_found:
                fips_limit_api = const_str
            else:
                fips_limit_api = prj_quotas_dict['floating_ip']
            if not prj_quotas_dict['network_ipam']:
                ipams_limit_api = 'Not Set'
            else:
                ipams_limit_api = prj_quotas_dict['network_ipam']
            if prj_quotas_dict['logical_router'] in not_found:
                routers_limit_api = const_str
            else:
                routers_limit_api = prj_quotas_dict['logical_router']
            if not prj_quotas_dict['access_control_list']:
                policies_limit_api = 'Not Set'
            else:
                policies_limit_api = prj_quotas_dict['access_control_list']
            if not prj_quotas_dict['service_instance']:
                svc_instances_limit_api = 'Not Set'
            else:
                svc_instances_limit_api = prj_quotas_dict['service_instance']
            if not vn_count_dict.get(prj):
                vn_count_dict[prj] = '0'
            if not fip_pool_count_dict.get(prj):
                fip_pool_count_dict[prj] = '0'
            if not policy_count_dict.get(prj):
                policy_count_dict[prj] = '0'
            if not ipam_count_dict.get(prj):
                ipam_count_dict[prj] = '0'
            if not svc_instance_count_dict.get(prj):
                svc_instance_count_dict[prj] = '0'
            if not security_grp_count_dict.get(prj):
                security_grp_count_dict[prj] = '0'
            if not fips_count_dict.get(prj):
                fips_count_dict[prj] = '0'
            if not ports_count_dict.get(prj):
                ports_count_dict[prj] = '0'
            if not subnets_count_dict.get(prj):
                subnets_count_dict[prj] = '0'
            if not security_grp_rules_count_dict.get(prj):
                security_grp_rules_count_dict[prj] = '0'
            if not routers_count_dict.get(prj):
                routers_count_dict[prj] = '0'
            self.logger.info(
                "Verifying project quotas for project %s ..." %
                (prj))
            self.ui.keyvalue_list(
                api_data,
                vnets=vn_count_dict[prj],
                pools=fip_pool_count_dict[prj],
                policies=policy_count_dict[prj],
                ipams=ipam_count_dict[prj],
                svc_instances=svc_instance_count_dict[prj],
                security_grps=security_grp_count_dict[prj],
                fips=fips_count_dict[prj],
                ports=ports_count_dict[prj],
                subnets=subnets_count_dict[prj],
                security_grp_rules=security_grp_rules_count_dict[prj],
                routers=routers_count_dict[prj],
                vnets_limit=vnets_limit_api,
                subnets_limit=subnets_limit_api,
                ports_limit=ports_limit_api,
                fips_limit=fips_limit_api,
                pools_limit=pools_limit_api,
                policies_limit=policies_limit_api,
                ipams_limit=ipams_limit_api,
                svc_instances_limit=svc_instances_limit_api,
                security_grps_limit=security_grps_limit_api,
                security_grp_rules_limit=security_grp_rules_limit_api,
                routers_limit=routers_limit_api)
            if not self.ui.click_configure_project_quotas():
                result = result and False
            self.ui.select_project(prj)
            rows = self.ui.find_element('grid-canvas', 'class')
            rows = self.ui.get_rows(rows)
            used = []
            limit = []
            for row in rows:
                used.append(
                    self.ui.find_element(
                        ('div', 2), 'tag', row, elements=True).text)
                limit.append(
                    self.ui.find_element(
                        ('div', 1), 'tag', row, elements=True).text)
            vnets, subnets, ports, fips, pools, policies, routers, ipams, svc_instances, security_grps, security_grp_rules = used[
                0], used[1], used[2], used[3], used[4], used[5], used[6], used[7], used[8], used[9], used[10]
            vnets_limit, subnets_limit, ports_limit, fips_limit, pools_limit, policies_limit, routers_limit, ipams_limit, svc_instances_limit, security_grps_limit, security_grp_rules_limit = limit[
                0], limit[1], limit[2], limit[3], limit[4], limit[5], limit[6], limit[7], limit[8], limit[9], limit[10]
            if vnets_limit in const_str:
                vnets_limit = const_str
            if ports_limit in const_str:
                ports_limit = const_str
            if subnets_limit in const_str:
                subnets_limit = const_str
            if fips_limit in const_str:
                fips_limit = const_str

            ui_data = []
            self.ui.keyvalue_list(
                ui_data,
                vnets=vnets,
                pools=pools,
                policies=policies,
                ipams=ipams,
                svc_instances=svc_instances,
                security_grps=security_grps,
                fips=fips,
                security_grp_rules=security_grp_rules,
                subnets=subnets,
                ports=ports,
                routers=routers,
                vnets_limit=vnets_limit,
                subnets_limit=subnets_limit,
                ports_limit=ports_limit,
                fips_limit=fips_limit,
                pools_limit=pools_limit,
                policies_limit=policies_limit,
                ipams_limit=ipams_limit,
                svc_instances_limit=svc_instances_limit,
                security_grps_limit=security_grps_limit,
                security_grp_rules_limit=security_grp_rules_limit,
                routers_limit=routers_limit)
            if self.ui.match_ui_kv(api_data, ui_data):
                self.logger.info("Project quotas matched for %s" % (prj))
            else:
                self.logger.info("Project quotas not matched for %s" % (prj))
                result = result and False
        return result
    # end verify_project_quota

    def verify_service_instance_api_basic_data(self):
        self.logger.info(
            "Verifying service instances api server data on Config->services->service instances...")
        self.logger.info(self.dash)
        result = True
        service_instance_list_api = self.ui.get_service_instance_list_api()
        for instance in range(len(service_instance_list_api['service-instances'])):
            net_list, network_lists1, network_lists3, inst_net_list, power_list, vm_list, status_list, power1_list, status1_list, vm1_list, dom_arry_basic = [
                [] for _ in range(11)]
            template_string, image, flavor, status_main_row = [
                '' for _ in range(4)]
            svc_fq_name = service_instance_list_api[
                'service-instances'][instance]
            api_fq_name = svc_fq_name['fq_name'][2]
            self.ui.click_configure_service_instance()
            project = svc_fq_name['fq_name'][1]
            self.ui.select_project(project)
            time.sleep(30)
            rows = self.ui.get_rows(canvas=True)
            self.logger.info(
                "service instance fq_name %s exists in api server..checking if exists in webui as well" %
                (api_fq_name))
            for i in range(len(rows)):
                not_match_count = 0
                match_flag = 0
                if rows[i].find_elements_by_tag_name(
                        'div')[2].text == api_fq_name:
                    self.logger.info(
                        "service instance fq name %s matched in webui..Verifying basic view details now" %
                        (api_fq_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    div_ele = rows[i].find_elements_by_tag_name('div')
                    self.ui.keyvalue_list(
                        dom_arry_basic,
                        Name_main_row=div_ele[2].text,
                        Template_main_row=div_ele[3].text,
                        Status_main_row=div_ele[4].text.strip(),
                        no_of_instances_main_row=div_ele[6].text,
                        Networks_main_row=div_ele[7].text.split(','))
                    break
            if not match_flag:
                self.logger.error(
                    "service instance fq_name exists in apiserver but %s not found in webui..." %
                    (api_fq_name))
                self.logger.info(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve basic view details in webui for service instance fq_name %s " %
                    (api_fq_name))
                self.ui.click_configure_service_instance_basic(match_index)
                rows = self.ui.get_rows(canvas=True)
                rows_detail = rows[match_index + 1].find_element_by_class_name(
                    'slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'Instance Details':
                        continue
                    elif text1 == 'Networks':
                        network_lists = rows_detail[detail].find_element_by_class_name(
                            'span10').text.split(',')
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': network_lists})
                    elif text1 == 'Virtual Machine':
                        keys_text = rows_detail[detail].find_element_by_class_name(
                            'span10').find_elements_by_tag_name('div')
                        count = 7
                        for keys in range((len(keys_text) / 7) - 1):
                            dom_arry_basic1 = []
                            complete_api_data1 = []
                            network_list = []
                            virtual_net_list = []
                            status = keys_text[count].find_elements_by_class_name(
                                'span2')[1].text
                            vm_name = keys_text[
                                count].find_elements_by_class_name('span2')[0].text
                            power = keys_text[count].find_elements_by_class_name(
                                'span2')[2].text
                            network_list = keys_text[count].find_element_by_class_name(
                                'span10').text.split()
                            count = count + 7
                            self.ui.keyvalue_list(
                                dom_arry_basic1,
                                Virtual_machine=vm_name,
                                Status=status,
                                Power_State=power,
                                Networkss=network_list)
                            self.ui.click_monitor_instances()
                            rows = self.ui.get_rows(canvas=True)
                            vm_list_ops = self.ui.get_vm_list_ops()
                            for insta in range(len(rows)):
                                if rows[insta].find_elements_by_class_name(
                                        'slick-cell')[1].text == vm_name:
                                    uuid = rows[insta].find_elements_by_class_name(
                                        'slick-cell')[2].text
                                    for vm_inst in range(len(vm_list_ops)):
                                        if vm_list_ops[vm_inst][
                                                'name'] == uuid:
                                            vm_inst_ops_data = self.ui.get_details(
                                                vm_list_ops[vm_inst]['href'])
                                            if 'UveVirtualMachineAgent' in vm_inst_ops_data:
                                                ops_data_basic = vm_inst_ops_data.get(
                                                    'UveVirtualMachineAgent')
                                                if ops_data_basic.get(
                                                        'interface_list'):
                                                    if ops_data_basic['interface_list'][
                                                            0].get('vm_name'):
                                                        vm1 = ops_data_basic[
                                                            'interface_list'][0]['vm_name']
                                                    if ops_data_basic['interface_list'][
                                                            0].get('active'):
                                                        status1 = 'ACTIVE'
                                                        power1 = 'RUNNING'
                                                        status_main_row = 'Active'
                                                    else:
                                                        status_main_row = 'Inactive'
                                                    for inter in range(len(ops_data_basic['interface_list'])):
                                                        if ops_data_basic['interface_list'][
                                                                inter].get('virtual_network'):
                                                            if ops_data_basic['interface_list'][inter][
                                                                    'virtual_network'].split(':')[1] == project:
                                                                if ops_data_basic['interface_list'][
                                                                        inter].get('ip_address'):
                                                                    virtual_net_list.append(
                                                                        ops_data_basic['interface_list'][inter]['virtual_network'].split(':')[2] +
                                                                        ':' +
                                                                        str(
                                                                            ops_data_basic['interface_list'][inter]['ip_address']))
                                                    break
                                    break
                            self.ui.keyvalue_list(
                                complete_api_data1,
                                Networkss=virtual_net_list,
                                Virtual_machine=vm1,
                                Status=status1,
                                Power_State=power1)
                            self.logger.info(
                                "Matching the instance details of service instance %s " %
                                (vm1))
                            if self.ui.match_ui_kv(
                                    complete_api_data1,
                                    dom_arry_basic1):
                                self.logger.info(
                                    "Service instance %s config details matched on Config->Services->Service Instances page" %
                                    (vm1))
                            else:
                                self.logger.error(
                                    "Service instance %s config details not matched on Config->Services->Service Instances page" %
                                    (vm1))
                            if keys != ((len(keys_text) / 7) - 1) - 1:
                                self.ui.click_configure_service_instance()
                                self.ui.click_configure_service_instance_basic(
                                    match_index)
                                rows = self.ui.get_rows(canvas=True)
                                rows_detail = rows[match_index + 1].find_element_by_class_name(
                                    'slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                                keys_text = rows_detail[detail].find_element_by_class_name(
                                    'span10').find_elements_by_tag_name('div')
                            else:
                                break
                    else:
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span10').text})
                service_inst_api_data = self.ui.get_details(
                    service_instance_list_api['service-instances'][instance]['href'])
                complete_api_data = []
                service_temp_list_api = self.ui.get_service_template_list_api()
                if 'service-instance' in service_inst_api_data:
                    api_data_basic = service_inst_api_data.get(
                        'service-instance')
                if 'fq_name' in api_data_basic:
                    project = api_data_basic['fq_name'][1]
                    complete_api_data.append(
                        {'key': 'Instance Name', 'value': api_data_basic['fq_name'][2]})
                    complete_api_data.append(
                        {'key': 'Name_main_row', 'value': api_data_basic['fq_name'][2]})
                if 'display_name' in api_data_basic:
                    complete_api_data.append(
                        {'key': 'Display Name', 'value': api_data_basic['display_name']})
                if api_data_basic.get('service_template_refs'):
                    template_string = api_data_basic[
                        'service_template_refs'][0]['to'][1]
                    for temp in range(len(service_temp_list_api['service-templates']) - 1):
                        if template_string == service_temp_list_api[
                                'service-templates'][temp + 1]['fq_name'][1]:
                            service_temp_api_data = self.ui.get_details(
                                service_temp_list_api['service-templates'][temp + 1]['href'])
                            if 'service-template' in service_temp_api_data:
                                api1_data_basic = service_temp_api_data.get(
                                    'service-template')
                                if 'service_mode' in api1_data_basic[
                                        'service_template_properties']:
                                    attached_temp = api1_data_basic[
                                        'service_template_properties']['service_mode'].capitalize()
                                svc_prop = api1_data_basic[
                                    'service_template_properties']
                                if 'image_name' in svc_prop:
                                    image = svc_prop['image_name']
                                if 'flavor' in svc_prop:
                                    flavor = svc_prop['flavor']
                                break
                    self.ui.keyvalue_list(
                        complete_api_data,
                        Template=template_string + ' ' + '(' + attached_temp + ')',
                        Template_main_row=template_string + ' ' + '(' + attached_temp + ')',
                        Status_main_row=status_main_row)
                if api_data_basic.get('service_instance_properties'):
                    serv_inst_list = api_data_basic[
                        'service_instance_properties']
                    for key in serv_inst_list:
                        key_list = [
                            'left_virtual_network',
                            'right_virtual_network',
                            'management_virtual_network']
                        if key == 'scale_out':
                            if serv_inst_list.get('scale_out'):
                                inst_value = str(
                                    serv_inst_list['scale_out']['max_instances']) + ' ' + 'Instances'
                                complete_api_data.append(
                                    {'key': 'Number of instances', 'value': inst_value})
                                complete_api_data.append(
                                    {'key': 'no_of_instances_main_row', 'value': inst_value})
                        elif key == 'interface_list':
                            inst_net_list1 = serv_inst_list['interface_list']
                            if len(inst_net_list1) != len(inst_net_list):
                                for inst_nets1 in range(len(inst_net_list1)):
                                    for inst_nets in range(len(inst_net_list)):
                                        if inst_net_list1[inst_nets1].get(
                                                'virtual_network') != inst_net_list[inst_nets]:
                                            not_match_count = not_match_count + \
                                                1
                                            if not_match_count == len(
                                                    inst_net_list):
                                                other_net = inst_net_list1[
                                                    inst_nets1].get('virtual_network')
                                                if other_net == '':
                                                    pass
                                                    # net_list.append(
                                                    #    'Other Network : Automatic')
                                                elif other_net.split(':')[1] == project:
                                                    net_list.append(
                                                        'Other Network : ' +
                                                        other_net.split(':')[2])
                                                else:
                                                    net_list.append(
                                                        net +
                                                        ' : ' +
                                                        other_net.split(':')[2] +
                                                        '(' +
                                                        other_net.split(':')[0] +
                                                        ':' +
                                                        other_net.split(':')[1] +
                                                        ')')
                                        else:
                                            break
                        elif key in key_list:
                            net = key
                            net_value = serv_inst_list.get(net)
                            net = net.replace('_virtual_', ' ').title()
                            inst_net_list.append(net_value)
                            if net_value == '' or net_value is None:
                                net_list.append(net + ' : Automatic')
                            elif net_value.split(':')[1] == project:
                                net_list.append(
                                    net +
                                    ' : ' +
                                    net_value.split(':')[2])
                            else:
                                net_list.append(
                                    net +
                                    ' : ' +
                                    net_value.split(':')[2] +
                                    '(' +
                                    net_value.split(':')[0] +
                                    ':' +
                                    net_value.split(':')[1] +
                                    ')')
                    self.ui.keyvalue_list(
                        complete_api_data,
                        Networks=net_list,
                        Networks_main_row=net_list,
                        Image=image,
                        Flavor=flavor)
                    if self.ui.match_ui_kv(
                            complete_api_data,
                            dom_arry_basic):
                        self.logger.info(
                            "Service instance config data matched on Config->Services->Service Instances page")
                    else:
                        self.logger.error(
                            "Service instance config data match failed on Config->Services->Service Instances page")
                        result = result and False
        return result
    # end verify_service_instance_data

    def verify_config_nodes_ops_grid_page_data(self, host_name, ops_data):
        webui_data = []
        self.ui.click_monitor_config_nodes()
        rows = self.browser.find_element_by_class_name('grid-canvas')
        rows = self.ui.get_rows(rows)
        for hosts in range(len(rows)):
            if rows[hosts].find_elements_by_class_name(
                    'slick-cell')[0].text == host_name:
                webui_data.append({'key': 'Hostname', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[0].text})
                webui_data.append({'key': 'IP Address', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[1].text})
                webui_data.append({'key': 'Version', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[2].text})
                webui_data.append({'key': 'Status', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[3].text})
                webui_data.append({'key': 'CPU', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[4].text + ' %'})
                webui_data.append({'key': 'Memory', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[5].text})

                if self.ui.match_ui_kv(ops_data, webui_data):
                    return True
                else:
                    return False
    # end verify_config_nodes_ops_grid_page_data

    def verify_analytics_nodes_ops_grid_page_data(self, host_name, ops_data):
        webui_data = []
        self.ui.click_monitor_analytics_nodes()
        rows = self.ui.get_rows()
        for hosts in range(len(rows)):
            if rows[hosts].find_elements_by_class_name(
                    'slick-cell')[0].text == host_name:
                webui_data.append({'key': 'Hostname', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[0].text})
                webui_data.append({'key': 'IP Address', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[1].text})
                webui_data.append({'key': 'Version', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[2].text})
                webui_data.append({'key': 'Status', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[3].text})
                webui_data.append({'key': 'CPU', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[4].text + ' %'})
                webui_data.append({'key': 'Memory', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[5].text})
                webui_data.append({'key': 'Generators', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[6].text})
                if self.ui.match_ui_kv(ops_data, webui_data):
                    return True
                else:
                    return False
    # end verify_analytics_nodes_ops_grid_page_data

    def verify_vrouter_ops_grid_page_data(self, host_name, ops_data):
        webui_data = []
        self.ui.click_monitor_vrouters()
        rows = self.ui.get_rows()
        for hosts in range(len(rows)):
            if rows[hosts].find_elements_by_class_name(
                    'slick-cell')[0].text == host_name:
                webui_data.append({'key': 'Hostname', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[0].text})
                webui_data.append({'key': 'IP Address', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[1].text})
                webui_data.append({'key': 'Version', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[2].text})
                webui_data.append({'key': 'Status', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[3].text})
                webui_data.append({'key': 'CPU', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[4].text + ' %'})
                webui_data.append({'key': 'Memory', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[5].text})
                webui_data.append({'key': 'Networks', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[6].text})
                webui_data.append({'key': 'Instances', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[7].text})
                webui_data.append({'key': 'Interfaces', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[8].text})
                if self.ui.match_ui_kv(ops_data, webui_data):
                    return True
                else:
                    return False
    # end verify_vrouter_ops_grid_page_data

    def verify_bgp_routers_ops_grid_page_data(self, host_name, ops_data):

        webui_data = []
        self.ui.click_monitor_control_nodes()
        rows = self.ui.get_rows()
        for hosts in range(len(rows) - 1):
            if rows[hosts].find_elements_by_class_name(
                    'slick-cell')[0].text == host_name:
                webui_data.append({'key': 'Hostname', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[0].text})
                webui_data.append({'key': 'IP Address', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[1].text})
                webui_data.append({'key': 'Version', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[2].text})
                webui_data.append({'key': 'Status', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[3].text})
                webui_data.append({'key': 'CPU', 'value': str(
                    rows[hosts].find_elements_by_class_name('slick-cell')[4].text) + ' %'})
                webui_data.append({'key': 'Memory', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[5].text})
                webui_data.append({'key': 'Peers', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[6].text})
                webui_data.append({'key': 'vRouters', 'value': rows[
                                  hosts].find_elements_by_class_name('slick-cell')[7].text})
        if self.ui.match_ui_kv(ops_data, webui_data):
            return True
        else:
            return False
    # end verify_bgp_routers_ops_grid_page_data

    def check_alerts(self):
        self.logger.info("Capturing screenshot for alerts...")
        self.logger.debug(self.dash)
        if not self.ui.click_monitor_dashboard():
            result = result and False
        text = self.ui.find_element(
            ['alerts-box', 'text'], ['id', 'class']).text
        if text:
            self.logger.warning("Alerts found %s" % (text))
            self.ui.click_element(
                ['moreAlertsLink', 'More'], ['id', 'link_text'])
            self.ui.screenshot("Alerts")
            self.ui.click_element('alertsClose')
    # end check_alerts

    def verify_vm_ops_basic_grid_data(self, vm_name, vm_ops_data, ops_uuid):
        if not self.ui.click_monitor_instances():
            result = result and False
        dom_arry_basic = []
        vm_name1 = ''
        net = ''
        network_list = []
        network_grid_list = []
        ip_grid_list = []
        ip_list = []
        fip_list = []
        vrouter = ''
        rows = self.ui.get_rows()
        for inst in range(len(rows)):
            if rows[inst].find_elements_by_class_name(
                    'slick-cell')[1].text == vm_name:
                dom_arry_basic.append(
                    {'key': 'Instance_name_grid_row', 'value': vm_name})
                dom_arry_basic.append({'key': 'uuid_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[2].text})
                dom_arry_basic.append({'key': 'vn_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[3].text.splitlines()})
                dom_arry_basic.append({'key': 'interface_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[4].text})
                dom_arry_basic.append({'key': 'vrouter_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[5].text})
                dom_arry_basic.append({'key': 'ip_address_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[6].text.splitlines()})
                dom_arry_basic.append({'key': 'fip_grid_row', 'value': rows[
                                      inst].find_elements_by_class_name('slick-cell')[7].text.splitlines()})
                break
        if vm_ops_data.get('UveVirtualMachineAgent'):
            ops_data = vm_ops_data['UveVirtualMachineAgent']
            if ops_data.get('interface_list'):
                for interface in range(len(ops_data['interface_list'])):
                    if ops_data['interface_list'][interface].get('vm_name'):
                        vm_name1 = ops_data['interface_list'][
                            interface]['vm_name']
                    if ops_data['interface_list'][
                            interface].get('virtual_network'):
                        net = ops_data['interface_list'][
                            interface]['virtual_network']
                        network_list.append(
                            net.split(':')[2] + ' (' + net.split(':')[1] + ')')

                    if ops_data['interface_list'][interface].get('ip_address'):
                        ip_list.append(
                            ops_data['interface_list'][interface]['ip_address'])
                    if ops_data['interface_list'][
                            interface].get('floating_ips'):
                        for fips in range(len(ops_data['interface_list'][interface]['floating_ips'])):
                            fip_list.append(
                                ops_data['interface_list'][interface]['floating_ips'][fips]['ip_address'] +
                                ' (0 B/0 B)')
                if len(network_list) > 2:
                    network_grid_list.extend(
                        [network_list[0], network_list[1]])
                    network_grid_list.append(
                        '(' + str((len(network_list) - 2)) + ' more' + ')')
                else:
                    network_grid_list = network_list
                if len(fip_list) > 2:
                    fip_grid_list.extend([fip_list[0], fip_list[1]])
                    fip_grid_list.append(
                        '(' + str((len(fip_list) - 2)) + ' more' + ')')
                else:
                    fip_grid_list = fip_list
                if len(ip_list) > 2:
                    ip_grid_list.extend([ip_list[0], ip_list[1]])
                    ip_grid_list.append(
                        '(' + str((len(ip_list) - 2)) + ' more' + ')')
                else:
                    ip_grid_list = ip_list

            if ops_data.get('vrouter'):
                vrouter = ops_data['vrouter']
            complete_ops_data = []
            complete_ops_data.append(
                {'key': 'Instance_name_grid_row', 'value': vm_name1})
            complete_ops_data.append(
                {'key': 'uuid_grid_row', 'value': ops_uuid})
            complete_ops_data.append(
                {'key': 'vn_grid_row', 'value': network_grid_list})
            complete_ops_data.append(
                {'key': 'interface_grid_row', 'value': str(len(network_list))})
            complete_ops_data.append(
                {'key': 'vrouter_grid_row', 'value': vrouter})
            complete_ops_data.append(
                {'key': 'ip_address_grid_row', 'value': ip_grid_list})
            complete_ops_data.append(
                {'key': 'fip_grid_row', 'value': fip_grid_list})
            if self.ui.match_ui_kv(complete_ops_data, dom_arry_basic):
                return True
            else:
                return False
