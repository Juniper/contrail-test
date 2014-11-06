from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import time
import datetime
import logging
from tcutils.util import *
from vnc_api.vnc_api import *
from tcutils.verification_util import *
from selenium.common.exceptions import ElementNotVisibleException


def wait_for_ajax(driver):
    while True:
        if (driver.execute_script("return jQuery.active") == 0):
            return True
# end wait_for_ajax


def ajax_complete(driver):
    try:
        return 0 == driver.execute_script("return jQuery.active")
    except WebDriverException:
        pass
# end ajax_complete


class WebuiCommon:

    def __init__(self, obj):
        self.delay = 15
        self.inputs = obj.inputs
        self.jsondrv = JsonDrv(self, args=self.inputs)
        self.connections = obj.connections
        self.browser = obj.browser
        self.browser_openstack = obj.browser_openstack
        self.frequency = 3
        self.logger = self.inputs.logger
        self.dash = "-" * 60
        self.log_path = None
        self.log_dir = '/var/log/'
    # end __init__

    def wait_till_ajax_done(self, browser, jquery=True, wait=5):
        jquery = False
        wait = 5
        if jquery:
            WebDriverWait(
                browser,
                self.delay,
                self.frequency).until(ajax_complete)
        else:
            time.sleep(wait)
    # end wait_till_ajax_done

    def _get_list_api(self, item):
        url = 'http://' + self.inputs.cfgm_ip + ':8082/' + item
        obj = self.jsondrv.load(url)
        return obj
    # end _get_list_api

    def _get_list_ops(self, item):
        url = 'http://' + self.inputs.collector_ip + \
            ':8081/analytics/uves/' + item
        obj = self.jsondrv.load(url)
        return obj
    # end _get_list_api

    def get_routers_list_api(self):
        return self._get_list_api('logical-routers')
    # end get_routers_list_api

    def get_service_instance_list_api(self):
        return self._get_list_api('service-instances')
    # end get_service_instance_list_api

    def get_service_chains_list_ops(self):
        return self._get_list_ops('service-chains')
    # end get_service_instance_list_api

    def get_generators_list_ops(self):
        return self._get_list_ops('generators')
    # end get_generators_list_ops

    def get_bgp_peers_list_ops(self):
        return self._get_list_ops('bgp-peers')
    # end get_bgp_peers_list_ops

    def get_policy_list_api(self):
        return self._get_list_api('network-policys')
    # end get_vn_list_api

    def get_ipam_list_api(self):
        return self._get_list_api('network-ipams')
    # end get_ipam_list_api

    def get_service_template_list_api(self):
        return self._get_list_api('service-templates')
    # end get_service_template_list_api

    def get_floating_pool_list_api(self):
        return self._get_list_api('floating-ip-pools')
    # end get_floating_pool_list_api

    def get_security_group_list_api(self):
        return self._get_list_api('security-groups')
    # end get_security_group_list_api(

    def get_vm_intf_refs_list_api(self):
        return self._get_list_api('virtual-machine-interfaces')
    # end get_vm_intf_refs_list_api

    def get_project_list_api(self):
        return self._get_list_api('projects')
    # end get_project_list_api

    def get_vrouters_list_ops(self):
        return self._get_list_ops('vrouters')
    # end get_vrouters_list_ops

    def get_fip_list_api(self):
        return self._get_list_api('floating-ips')
    # end get_fip_list_ops

    def get_dns_nodes_list_ops(self):
        return self._get_list_ops('dns-nodes')
    # end get_dns_nodes_list_ops

    def get_collectors_list_ops(self):
        return self._get_list_ops('analytics-nodes')
    # end get_collectors_list_ops

    def get_bgp_routers_list_ops(self):
        return self._get_list_ops('control-nodes')
    # end get_bgp_routers_list_ops

    def get_control_nodes_list_ops(self):
        return self._get_list_ops('control-nodes')
    # end get_config_nodes_list_ops

    def get_config_nodes_list_ops(self):
        return self._get_list_ops('config-nodes')
    # end get_config_nodes_list_ops

    def get_modules_list_ops(self):
        return self._get_list_ops('modules')
    # end get_modules_list_ops

    def get_service_instances_list_ops(self):
        return self._get_list_ops('service-instances')
    # end get_service_instances_list_ops

    def get_vn_list_api(self):
        return self._get_list_api('virtual-networks')
    # end get_vn_list_api

    def get_details(self, url):
        obj = self.jsondrv.load(url)
        return obj
    # end get_details

    def get_vn_list_ops(self):
        return self._get_list_ops('virtual-networks')
    # end get_vn_list_ops

    def get_xmpp_list_ops(self):
        return self._get_list_ops('xmpp-peers')
    # end get_xmpp_list_ops

    def get_vm_list_ops(self):
        return self._get_list_ops('virtual-machines')
    # end get_vm_list_ops

    def log_msg(self, t, msg):
        if t == 'info':
            self.logger.info(msg)
        elif t == 'error':
            self.logger.error(msg)
        elif t == 'debug':
            self.logger.debug(msg)
        else:
            self.logger.info(msg)
    # end log_msg

    def keyvalue_list(self, list_obj, *args, **kargs):
        if args:
            for arg in args:
                list_obj.append({'key': str(arg), 'value': arg})
        if kargs:
            for k, v in kargs.iteritems():
                if not isinstance(v, list):
                    v = str(v)
                list_obj.append({'key': str(k), 'value': v})
    # end keyvalue_list

    def screenshot(self, string, browser=None, log=True):
        if not browser:
            browser = self.browser
        file_name = string + self.date_time_string() + '.png'
        if browser:
            browser.get_screenshot_as_file(self.log_path + file_name)
            if log:
                browser.get_screenshot_as_file(self.log_dir + file_name)
            self.logger.info("Screenshot captured  %s" % (file_name))
    # end screenshot

    def subnets_count_quotas(self, href):
        subnet_count_dict = {}
        for index in range(len(href)):
            project = href[index]['fq_name'][1]
            if project == 'default-project':
                continue
            vn_api_details = self.get_details(href[index][
                'href'])['virtual-network']['network_ipam_refs']
            if project not in subnet_count_dict:
                subnet_count_dict[project] = 0
            for index1 in vn_api_details:
                subnet_len = len(index1['attr']['ipam_subnets'])
                subnet_count_dict[project] += subnet_len
        return subnet_count_dict
    # end subnet_count_quotas

    def security_grp_rules_count_quotas(self, href):
        security_grp_rules_count_dict = {}
        for index in range(len(href)):
            project = href[index]['fq_name'][1]
            if project == 'default-project':
                continue
            security_grp_rules_api_details = self.get_details(href[index][
                'href'])['security-group']['security_group_entries'][
                    'policy_rule']
            if project not in security_grp_rules_count_dict:
                security_grp_rules_count_dict[project] = 0
            rules_len = len(security_grp_rules_api_details)
            security_grp_rules_count_dict[project] += rules_len
        return security_grp_rules_count_dict
    # end security_grp_rules_count_quotas

    def count_quotas(self, href):
        count = {}
        for index in range(len(href)):
            project = href[index]['fq_name'][1]
            if not project in count.keys():
                count[project] = 1
            else:
                count[project] += 1
        return count
    # end count_quotas

    def click_if_element_match(self, element_name, elements_list):
        for element in elements_list:
            if element.text == element_name:
                element.click()
                break
    # end click_if_element_match

    def click_element(
            self,
            element_name_list,
            element_by_list='id',
            browser=None,
            if_elements=[],
            elements=False,
            jquery=True,
            wait=2):
        if not browser:
            browser = self.browser
        else:
            jquery = False
        element_to_click = self.find_element(
            element_name_list, element_by_list, browser, if_elements, elements)
        element_to_click.click()
        self.wait_till_ajax_done(browser, jquery, wait)
    # end _click_element

    def send_keys(
            self,
            keys,
            element_name_list,
            element_by_list='id',
            browser=None,
            if_elements=[],
            elements=False):
        if not browser:
            browser = self.browser
        send_keys_to_element = self.find_element(
            element_name_list, element_by_list, browser, if_elements, elements)
        send_keys_to_element.send_keys(keys)
        time.sleep(2)
    # end send_keys

    def find_element(
            self,
            element_name_list,
            element_by_list='id',
            browser=None,
            if_elements=[],
            elements=False):
        obj = None
        if not browser:
            browser = self.browser
        if isinstance(element_name_list, list):
            for index, element_by in enumerate(element_by_list):
                element_name = element_name_list[index]
                if index == 0:
                    if index in if_elements:
                        if isinstance(element_name, tuple):
                            element, indx = element_name
                            obj = self._find_elements_by(
                                browser, element_by, element)[indx]
                        else:
                            obj = self._find_elements_by(
                                browser, element_by, element_name)
                    else:
                        obj = self._find_element_by(
                            browser, element_by, element_name)
                else:
                    if index in if_elements:
                        if isinstance(element_name, tuple):
                            element, indx = element_name
                            obj = self._find_elements_by(
                                obj, element_by, element)[indx]
                        else:
                            obj = self._find_elements_by(
                                obj, element_by, element_name)
                    else:
                        obj = self._find_element_by(
                            obj, element_by, element_name)
        else:
            if elements:
                if isinstance(element_name_list, tuple):
                    element_name, element_index = element_name_list
                    obj = self._find_elements_by(
                        browser, element_by_list, element_name)[element_index]
                else:
                    obj = self._find_elements_by(
                        browser, element_by_list, element_name_list)
            else:
                obj = self._find_element_by(
                    browser, element_by_list, element_name_list)
        return obj
        # end find_element

    def _find_element_by(self, browser_obj, element_by, element_name):
        try:
            if element_by == 'id':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_id(element_name))
            elif element_by == 'class':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_class_name(element_name))
            elif element_by == 'name':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_name(element_name))
            elif element_by == 'xpath':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_xpath(element_name))
            elif element_by == 'link_text':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_link_text(element_name))
            elif element_by == 'tag':
                if isinstance(element_name, tuple):
                    name1, name2 = element_name
                    obj = None
                    try:
                        obj = WebDriverWait(
                            browser_obj,
                            self.delay,
                            self.frequency).until(
                            lambda a: a.find_element_by_tag_name(name1))
                    except WebDriverException:
                        obj = WebDriverWait(
                            browser_obj,
                            self.delay,
                            self.frequency).until(
                            lambda a: a.find_element_by_tag_name(name2))
                else:
                    obj = WebDriverWait(
                        browser_obj,
                        self.delay,
                        self.frequency).until(
                        lambda a: a.find_element_by_tag_name(element_name))
            elif element_by == 'css':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_element_by_css_selector(element_name))
            else:
                self.logger.error('Incorrect element_by:%s or value:%s' %
                                  (element_by, element_name))
        except WebDriverException:
            self.screenshot('Error_find_element_by_' + str(element_by) + '_' + str(element_name))
            raise
        return obj
    # end find_element_by

    def _find_elements_by(self, browser_obj, elements_by, element_name):
        try:
            if elements_by == 'id':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_id(element_name))
            elif elements_by == 'class':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_class_name(element_name))
            elif elements_by == 'name':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_name(element_name))
            elif elements_by == 'xpath':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_xpath(element_name))
            elif elements_by == 'link_text':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_link_text(element_name))
            elif elements_by == 'tag':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                lambda a: a.find_elements_by_tag_name(element_name))
            elif elements_by == 'css':
                obj = WebDriverWait(browser_obj, self.delay, self.frequency).until(
                    lambda a: a.find_elements_by_css_selector(element_name))
            else:
                self.logger.error('Incorrect element_by or value :  %s  %s ' %
                                  (elements_by, element_name))
        except WebDriverException:
            self.screenshot('Error_find_elements_by_' + str(elements_by) + '_' + str(element_name))
            raise        
        return obj
    # end find_elements_by

    def click_on_dropdown(self, browser=None):
        if not browser:
            browser = self.browser
        self.click_element(
            ['select2-container', 'a'], ['class', 'tag'], browser, jquery=False, wait=2)
    # end click_on_dropdown

    def find_select2_drop_elements(self, browser):
        element_list = self.find_element(
            ['select2-drop', 'li'], ['id', 'tag'], browser, [1])
        if not element_list:
            self.logger.error('no dropdown elements found')
            return None
        return element_list
    # end find_select2_drop_elements

    def select_from_dropdown(self, element_text, browser=None, grep=False):
        if not browser:
            browser = self.browser
            element_list = self.find_select2_drop_elements(browser)
            if not element_list:
                return False
            div_obj_list = [
                element.find_element_by_tag_name('div') for element in element_list]
            if not self.click_if_element_found(
                    div_obj_list,
                    element_text,
                    grep):
                return False
        return True
    # end select_from_dropdown_list

    def click_if_element_found(self, objs, element_text, grep=False):
        element_found = False
        for element_obj in objs:
            element_obj_text = element_obj.text
            if (grep and element_obj_text.find(element_text) != -
                    1) or (not grep and element_obj_text == element_text):
                element_found = True
                element_obj.click()
                self.wait_till_ajax_done(self.browser, jquery=False, wait=4)
                break
        if not element_found:
            self.logger.error(' %s not found' % (element_text))
            return False
        return True
    # end click_if_element_found

    def select_project(self, project_name):
        current_project = self.find_element(
            ['s2id_ddProjectSwitcher', 'span'], ['id', 'tag']).text
        if not current_project == project_name:
            self.click_element(
                ['s2id_ddProjectSwitcher', 'a'], ['id', 'tag'], jquery=False, wait=4)
            elements_obj_list = self.find_select2_drop_elements(self.browser)
            self.click_if_element_found(elements_obj_list, project_name)
    # end select_project

    def get_element(self, name, key_list):
        get_element = ''
        for key in key_list:
            get_element = get_element + ".get('" + key + "')"
        return name.get_element
        # end get_element

    def append_to_list(self, elements_list, key_value):
        if isinstance(key_value, list):
            for k, v in key_value:
                elements_list.append({'key': k, 'value': v})
        else:
            k, v = key_value
            elements_list.append({'key': k, 'value': v})
    # end append_to_dict

    def get_memory_string(self, dictn):
        if isinstance(dictn, dict):
            memory = dictn.get('cpu_info').get('meminfo').get('virt')
        else:
            memory = dictn
            memory = memory / 1024.0
        offset = 20
        if memory < 1024:
            offset = 50
            memory = round(memory, 2)
            memory_range = range(
                int(memory * 100) - offset, int(memory * 100) + offset)
            memory_range = map(lambda x: x / 100.0, memory_range)
            memory_list = [str(memory) + ' KB' for memory in memory_range]
        elif memory / 1024.0 < 1024:
            memory = memory / 1024.0
            memory = round(memory, 2)
            memory_range = range(
                int(memory * 100) - offset, int(memory * 100) + offset)
            memory_range = map(lambda x: x / 100.0, memory_range)
            for memory in memory_range:
                if isinstance(memory, float) and memory == int(memory):
                    index = memory_range.index(memory)
                    memory_range[index] = int(memory)
            memory_list = [str(memory) + ' MB' for memory in memory_range]
        else:
            memory = round(memory / 1024, 2)
            memory_range = range(
                int(memory * 100) - offset, int(memory * 100) + offset)
            memory_range = map(lambda x: x / 100.0, memory_range)
            memory_list = [str(memory) + ' GB' for memory in memory_range]
        return memory_list
    # end get_memory_string

    def get_cpu_string(self, dictn):
        offset = 15
        cpu = float(dictn.get('cpu_info').get('cpu_share'))
        cpu = round(cpu, 2)
        cpu_range = range(int(cpu * 100) - offset, int(cpu * 100) + offset)
        cpu_range = map(lambda x: x / 100.0, cpu_range)
        cpu_list = [str('%.2f' % cpu) + ' %' for cpu in cpu_range]
        return cpu_list
    # end get_cpu_string

    def get_analytics_msg_count_string(self, dictn, size):
        offset = 25
        tx_socket_size = size
        analytics_msg_count = dictn.get('ModuleClientState').get(
            'session_stats').get('num_send_msg')
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
        return analytics_messages_string
    # end get_cpu_string

    def get_version_string(self, version):
        version = version.split('-')
        ver = version[1].split('.')[0]
        version = version[0] + ' (Build ' + ver + ')'
        return version
    # end get_version_string

    def get_version(self):
        config_nodes_list_ops = self.get_config_nodes_list_ops()
        if len(config_nodes_list_ops):
            config_nodes_ops_data = self.get_details(
                config_nodes_list_ops[0]['href'])
            build_info = config_nodes_ops_data.get(
                'ModuleCpuState').get('build_info')
            if build_info:
                version = json.loads(config_nodes_ops_data.get('ModuleCpuState').get(
                    'build_info')).get('build-info')[0].get('build-id')
                version = self.get_version_string(version)
            else:
                version = "build_info missing in config node"
        else:
            version = '--'
        return version
    # end get_version

    def check_error_msg(self, error_msg):
        try:
            if self.browser.find_element_by_id('infoWindow'):
                error_header = self.find_element(
                    'modal-header-title',
                    'class').text
                error_text = self.browser.find_element_by_id('short-msg').text
                self.logger.error('error occured while clicking on %s : %s ' %
                                  (error_msg, error_header))
                self.logger.error('error text : msg is %s ' % (error_text))
                self.logger.info(
                    self.log_path +
                    'Capturing screenshot of error msg .')
                self.screenshot(error_msg + '_click_failure')
                self.logger.info(
                    'Captured screenshot' +
                    error_msg +
                    'click_failure' +
                    self.date_time_string() +
                    '.png')
                self.click_element('infoWindowbtn0')
                return False
        except (NoSuchElementException, ElementNotVisibleException):
            return True
    # end check_error_msg

    def _rows(self, browser, canvas):
        if canvas:
            rows = self.find_element('grid-canvas', 'class', browser)
            rows = self.find_element(
                'ui-widget-content',
                'class',
                rows,
                elements=True)
        else:
            rows = self.find_element(
                'ui-widget-content',
                'class',
                browser,
                elements=True)
        return rows
    # end _rows

    def get_rows(self, browser=None, canvas=False):
        if not browser:
            browser = self.browser
        rows = None
        try:
            rows = self._rows(browser, canvas)
        except WebDriverException:
            self.wait_till_ajax_done(browser, jquery, wait)
            rows = self._rows(browser, canvas)
        return rows
    # end get_rows

    def check_rows(self, length, obj):
        count = 0
        while True:
            if count > 50:
                self.logger.error("Loading failed")
                return False
            rows = self.get_rows(obj)
            count = count + 1
            if len(rows) == length:
                break
            else:
                self.logger.info("Still loading")
        return rows
    # end check_rows

    def click_icon_caret(self, row_index, obj=None, length=None):
        if not obj:
            obj = self.find_element('grid-canvas', 'class')
        rows = None
        rows = self.get_rows(obj)
        if length:
            rows = self.check_rows(length, obj)
        br = rows[row_index]
        element0 = ('slick-cell', 0)
        element1 = ('div', 'i')
        self.click_element(
            [element0, element1], ['class', 'tag'], br, if_elements=[0])
    # end click_icon_caret

    def click_monitor_instances_basic(self, row_index, length=None):
        self.click_monitor_instances()
        self.wait_till_ajax_done(self.browser)
        self.click_icon_caret(row_index, length=length)
    # end click_monitor_instances_basic_in_webui

    def click_monitor_networks_basic(self, row_index):
        self.click_element('Networks', 'link_text', jquery=False)
        time.sleep(2)
        self.click_icon_caret(row_index)
        rows = self.get_rows()
        rows[row_index + 1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser)
        rows[row_index + 1].find_element_by_class_name(
            'pull-right').find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_instances_basic_in_webui

    def click_monitor_vrouters(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_vrouter', 'Virtual Routers'], ['id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("monitor vrouters")
    # end click_monitor_vrouters_in_webui

    def click_monitor_dashboard(self):
        self.click_monitor()
        self.click_element('mon_infra_dashboard')
        self.screenshot("dashboard")
        time.sleep(1)
        return self.check_error_msg("monitor dashboard")
    # end click_monitor_dashboard_in_webui

    def click_monitor_config_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_config', 'Config Nodes'], ['id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("monitor config nodes")
    # end click_monitor_config_nodes_in_webui

    def click_monitor_control_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_control', 'Control Nodes'], ['id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("monitor control nodes")
    # end click_monitor_control_nodes_in_webui

    def click_monitor_analytics_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_analytics', 'Analytics Nodes'], ['id', 'link_text'])
        return self.check_error_msg("monitor analytics nodes")
    # end click_monitor_analytics_nodes_in_webui

    def get_service_instance_list_api(self):
        url = 'http://' + self.inputs.cfgm_ip + ':8082/service-instances'
        obj = self.jsondrv.load(url)
        return obj
    # end get_service_instance_list_api

    def click_configure_service_instance_basic(self, row_index):
        self.click_element('Service Instances', 'link_text')
        self.check_error_msg("configure service instance")
        count = 0
        rows = self.get_rows()
        while True:
            if count > 120:
                self.logger.error('Status is Updating.')
            rows = self.get_rows()
            if len(rows) < 1:
                break
            text = rows[0].find_elements_by_tag_name('div')[4].text
            if text == 'Updating.':
                count = count + 1
                self.logger.info('Waiting for status update')
                time.sleep(1)
            else:
                self.logger.info('Status is %s' % (text))
                break
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_service_instance_basic_in_webui

    def click_configure_service_instance(self):
        self.click_element('btn-configure')
        self._click_on_config_dropdown(self.browser, 2)
        self.click_element(
            ['config_sc_svcInstances', 'Service Instances'], ['id', 'link_text'])
        time.sleep(2)
        return self.check_error_msg("configure service instances")
    # end click_configure_service_instance_in_webui

    def delete_element(self, fixture, element_type):
        result = True
        delete_success = None
        if not element_type == 'svc_template_delete':
            self.select_project(fixture.project_name)
        if element_type == 'svc_instance_delete':
            if not self.click_configure_service_instance():
                result = result and False
            element_name = fixture.si_name
            element_id = 'btnDeletesvcInstances'
            popup_id = 'btnCnfDelSInstPopupOK'
        elif element_type == 'vn_delete':
            if not self.click_configure_networks():
                result = result and False
            element_name = fixture.vn_name
            element_id = 'btnDeleteVN'
            popup_id = 'btnCnfRemoveMainPopupOK'
        elif element_type == 'svc_template_delete':
            if not self.click_configure_service_template():
                result = result and False
            element_name = fixture.st_name
            element_id = 'btnDeletesvcTemplate'
            popup_id = 'btnCnfDelPopupOK'
        elif element_type == 'ipam_delete':
            if not self.click_configure_ipam():
                result = result and False
            element_name = fixture.name
            element_id = 'btnDeleteIpam'
            popup_id = 'btnCnfRemoveMainPopupOK'
        elif element_type == 'fip_delete':
            if not self.click_configure_fip():
                result = result and False
            element_name = fixture.pool_name + ':' + fixture.vn_name
            element_id = 'btnDeletefip'
            popup_id = 'btnCnfReleasePopupOK'
        elif element_type == 'policy_delete':
            if not self.click_configure_policies():
                result = result and False
            element_name = fixture.policy_name
            element_id = 'btnDeletePolicy'
            popup_id = 'btnCnfRemoveMainPopupOK'
        elif element_type == 'disassociate_fip':
            if not self.click_configure_fip():
                result = result and False
            element_name = fixture.vn_name + ':' + fixture.pool_name
            element_id = 'btnDeletefip'
            popup_id = 'btnCnfReleasePopupOK'
        rows = self.get_rows()
        ln = len(rows)
        try:
            for element in rows:
                if element_type == 'disassociate_fip':
                    element_text = element.find_elements_by_tag_name(
                        'div')[3].text
                    div_obj = element.find_elements_by_tag_name('div')[0]
                else:
                    element_text = element.find_elements_by_tag_name(
                        'div')[2].text
                    div_obj = element.find_elements_by_tag_name('div')[1]

                if (element_text == element_name):
                    div_obj.find_element_by_tag_name('input').click()
                    self.click_element(element_id)
                    self.click_element(popup_id)
                    delete_success = True
                    break
        except WebDriverException:
            self.logger.error("%s deletion failed " % (element_type))
            self.screenshot('delete' + element_type + 'failed')
        if not delete_success:
            self.logger.error("%s element does not exist" % (element_type))
            result = result and False
        if not self.check_error_msg(element_type):
            self.logger.error("%s deletion failed " % (element_type))
            result = result and False
        else:
            self.logger.info("%s got deleted using webui" %
                             (element_name))
    # end delete_element

    def click_configure_networks(self):
        time.sleep(1)
        self.click_element('btn-configure')
        time.sleep(2)
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_vn', 'Networks'], ['id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("configure networks")
    # end click_configure_networks_in_webui

    def __wait_for_networking_items(self, a):
        if len(
                a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0:
            return True
    # end __wait_for_networking_items

    def click_configure_fip(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_fip', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        return self.check_error_msg("configure fip")
    # end click_configure_fip_in_webui

    def click_error(self, name):
        self.logger.error("Some error occured whlie clicking on %s" % (name))
        return False
    # end click_error

    def click_monitor(self):
        self.click_element('btn-monitor', jquery=False, wait=3)
        return self.check_error_msg("monitor")
    # end click_monitor

    def click_monitor_networking(self):
        self.click_monitor()
        children = self.find_element(
            ['menu', 'item'], ['id', 'class'], if_elements=[1])
        children[1].find_element_by_tag_name('span').click()
        time.sleep(2)
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_in_webui

    def click_monitor_networks(self):
        self.click_monitor_networking()
        self.click_element(
            ['mon_net_networks', 'Networks'], ['id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("monitor networks")
    # end click_monitor_networks_in_webui

    def click_monitor_instances(self):
        self.click_monitor_networking()
        self.click_element(
            ['mon_net_instances', 'Instances'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        return self.check_error_msg("monitor_instances")
    # end click_monitor_instances_in_webui

    def click_monitor_vrouters_basic(self, row_index):
        self.click_element('Virtual Routers', 'link_text')
        self.check_error_msg("monitor vrouters")
        self.click_monitor_common_basic(row_index)
    # end click_monitor_vrouters_basic_in_webui

    def click_monitor_analytics_nodes_basic(self, row_index):
        self.click_element('Analytics Nodes', 'link_text')
        self.check_error_msg("monitor analytics nodes")
        self.click_monitor_common_basic(row_index)
    # end click_monitor_analytics_nodes_basic_in_webui

    def click_monitor_control_nodes_basic(self, row_index):
        self.click_element('Control Nodes', 'link_text')
        self.check_error_msg("monitor control nodes")
        self.click_monitor_common_basic(row_index)
    # end click_monitor_vrouters_basic_in_webui

    def click_monitor_config_nodes_basic(self, row_index):
        self.click_element('Config Nodes', 'link_text')
        self.check_error_msg("monitor config nodes")
        self.click_monitor_common_basic(row_index)
    # end click_monitor_config_nodes_basic_in_webui

    def click_monitor_vrouters_advance(self, row_index):
        self.click_element('Virtual Routers', 'link_text')
        self.check_error_msg("monitor vrouters")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_vrouters_advance_in_webui

    def click_monitor_config_nodes_advance(self, row_index):
        self.click_element('Config Nodes', 'link_text')
        self.check_error_msg("monitor config nodes")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_config_nodes_advance_in_webui

    def click_monitor_control_nodes_advance(self, row_index):
        self.click_element('Control Nodes', 'link_text')
        self.check_error_msg("monitor control nodes")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_control_nodes_advance_in_webui

    def click_monitor_analytics_nodes_advance(self, row_index):
        self.click_element('Analytics Nodes', 'link_text')
        self.check_error_msg("monitor analytics nodes")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_analytics_nodes_advance_in_webui

    def click_monitor_common_advance(self, row_index):
        self.click_icon_caret(row_index)
        self.click_element(['dashboard-box', 'icon-cog'], ['id', 'class'])
        self.click_element(['dashboard-box', 'icon-code'], ['id', 'class'])
    # end click_monitor_common_advance_in_webui

    def click_monitor_common_basic(self, row_index):
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        self.click_icon_caret(row_index)
        self.click_element(['dashboard-box', 'icon-cog'], ['id', 'class'])
        self.click_element(['dashboard-box', 'icon-list'], ['id', 'class'])
    # end click_monitor_common_basic_in_webui

    def click_monitor_networks_advance(self, row_index):
        self.click_element('Networks', 'link_text')
        self.check_error_msg("monitor networks")
        self.click_icon_caret(row_index)
        rows = self.get_rows()
        rows[row_index + 1].find_element_by_class_name('icon-cog').click()
        time.sleep(1)
        self.wait_till_ajax_done(self.browser)
        rows[row_index + 1].find_element_by_class_name(
            'pull-right').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
    # end click_monitor_networks_advance_in_webui

    def click_monitor_instances_advance(self, row_index, length=None):
        self.click_monitor_instances_basic(row_index, length)
        rows = self.get_rows()
        rows[row_index + 1].find_element_by_class_name('icon-cog').click()
        time.sleep(2)
        rows[row_index + 1].find_element_by_class_name(
            'pull-right').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        time.sleep(2)
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_instances_advance_in_webui

    def click_configure_networks_basic(self, row_index):
        self.click_element('Networks', 'link_text')
        self.check_error_msg("configure networks")
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_networks_basic_in_webui

    def click_configure_policies_basic(self, row_index):
        self.click_element('Policies', 'link_text')
        self.check_error_msg("configure policies")
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_policies_basic_in_webui

    def click_configure_ipam_basic(self, row_index):
        self.find_element('IP Address Management', 'link_text')
        self.check_error_msg("configure ipam")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_ipam_basic_in_webui

    def click_configure_project_quotas(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(
            ['config_net_quotas', 'Project Quotas'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure project quotas")
    # end click_configure_project_quota

    def click_configure_service_template_basic(self, row_index):
        self.click_element(['config_sc_svctemplate', 'a'], ['id', 'tag'])
        self.check_error_msg("configure service template")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_service_template_basic_in_webui

    def _click_on_config_dropdown(self, br, index=1):
        # index = 2 if svc_instance or svc_template
        self.click_element('btn-configure', browser=br)
        children = self.find_element(
            ['menu', 'item'], ['id', 'class'], br, [1])
        children[index].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(br)
        time.sleep(2)
    # end _click_on_config_dropdown

    def click_configure_service_template(self):
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        self._click_on_config_dropdown(self.browser, 2)
        self.click_element(['config_sc_svctemplate', 'a'], ['id', 'tag'])
        time.sleep(2)
        return self.check_error_msg("configure service template")
    # end click_configure_service_template_in_webui

    def click_configure_policies(self):
        self.click_element('btn-configure')
        children = self.find_element(
            ['menu', 'item'], ['id', 'class'], if_elements=[1])
        self._click_on_config_dropdown(self.browser)
        config_net_policy = self.find_element('config_net_policies')
        time.sleep(2)
        config_net_policy.find_element_by_link_text('Policies').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        return self.check_error_msg("configure policies")
    # end click_configure_policies_in_webui

    def click_configure_ipam(self):
        self._click_on_config_dropdown(self.browser)
        ipam = self.find_element('config_net_ipam')
        self.click_element(
            ['config_net_ipam', 'IP Address Management'], ['id', 'link_text'])
        return self.check_error_msg("configure ipam")
    # end click_configure_ipam_in_webui

    def click_instances(self, br=None):
        if not br:
            br = self.browser
        try:
            self.click_element('Instances', 'link_text', br)
        except WebDriverException:
            self.logger.error("Click on Instances failed")
            self.screenshot('Click_on_instances_failure', br)
    # end click_instances

    def select_project_in_openstack(self, project_name='admin', browser=None, os_release='havana'):
        try:
            if not browser:
                browser = self.browser_openstack
            if os_release == 'havana':
                self.click_element(
                    'Project',
                    'link_text',
                    browser,
                    jquery=False,
                    wait=4)
            ui_proj = self.find_element(
                ['tenant_switcher', 'h3'], ['id', 'css'], browser).get_attribute('innerHTML')
            if ui_proj != project_name:
                self.click_element(
                    ['tenant_switcher', 'a'], ['id', 'tag'], browser, jquery=False, wait=3)
                tenants = self.find_element(
                    ['tenant_list', 'a'], ['id', 'tag'], browser, [1])
                self.click_if_element_found(tenants, project_name)
            if os_release != 'havana':
                self.click_element('dt', 'tag', browser, jquery=False, wait=4)
        except WebDriverException:
            self.logger.error("Click on select project failed")
            self.screenshot('Click_select_project_failure', browser)
    # end select_project_in_openstack

    def os_login(self, fixture):
        try:
            br = fixture.browser_openstack
            user_name = fixture.inputs.stack_user
            password = fixture.inputs.stack_password
            user_obj = self.find_element('username', 'name', br)
            passwd_obj = self.find_element('password', 'name', br)
            user_obj.send_keys(user_name)
            passwd_obj.send_keys(password)
            self.click_element('btn', 'class', br)
            self.wait_till_ajax_done(br)
        except WebDriverException:
            pass
    # end os_login

    def verify_uuid_table(self, uuid):
        browser = self.browser
        delay = self.delay
        browser.find_element_by_id('btn-setting').click()
        time.sleep(2)
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn = browser.find_element_by_id(
            "setting_configdb_uuid").find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        flag = 1
        element = WebDriverWait(
            self.browser,
            self.delay,
            self.frequency).until(
            lambda a: a.find_element_by_id('cdb-results'))
        page_length = element.find_element_by_xpath(
            "//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln = len(page_length)
        total_pages = page_length[ln - 1].get_attribute('data-page')
        length = int(total_pages)
        for l in range(0, length):
            if flag == 0:
                browser.find_element_by_id(
                    "cdb-results").find_element_by_xpath("//a[@title='Go to the next page']").click()
                self.wait_till_ajax_done(self.browser)
            row5 = browser.find_element_by_id(
                'main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
            row6 = row5.find_elements_by_tag_name('a')
            for k in range(len(row6)):
                str2 = row6[k].get_attribute("innerHTML")
                num1 = str2.find(uuid)
                if num1 != -1:
                    flag = 1
                    return True
                    break
                else:
                    flag = 0
    # end verify_uuid_table

    def verify_fq_name_table(self, full_fq_name, fq_type):
        browser = self.browser
        delay = self.delay
        uuid = full_fq_name
        fq_name = fq_type
        btn_setting = WebDriverWait(browser, delay).until(
            lambda a: a.find_element_by_id('btn-setting')).click()
        WebDriverWait(browser, delay).until(ajax_complete)
        row1 = browser.find_element_by_id(
            'main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
        obj_fq_name_table = 'obj_fq_name_table~' + fq_name
        row1.find_element_by_xpath(
            "//*[@id='" + obj_fq_name_table + "']").click()
        WebDriverWait(browser, delay).until(
            ajax_complete, "Timeout waiting for page to appear")
        page_length = browser.find_element_by_id("cdb-results").find_element_by_xpath(
            "//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln = len(page_length)
        page_length1 = int(page_length[ln - 1].get_attribute('data-page'))
        flag = 1
        for l in range(page_length1):
            if flag == 0:
                page = browser.find_element_by_id("cdb-results").find_element_by_xpath(
                    "//div[@class='k-pager-wrap k-grid-pager k-widget']").find_element_by_tag_name("ul")
                page1 = page.find_elements_by_tag_name('li')
                page2 = page1[l].find_element_by_tag_name('a').click()
                WebDriverWait(browser, delay).until(
                    ajax_complete, "Timeout waiting for page to appear")
            row3 = browser.find_element_by_id(
                'main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
            row4 = row3.find_elements_by_tag_name('td')
            for k in range(len(row4)):
                fq = row4[k].get_attribute('innerHTML')
                if(fq == uuid):
                    flag = 1
                    return True
                    break
                else:
                    flag = 0
            if flag == 1:
                break
    # end verify_fq_name_table

    def check_element_exists_by_xpath(self, webdriver, xpath):
        try:
            webdriver.find_element_by_xpath(xpath)
        except NoSuchElementException:
            return False
        return True
    # end check_element_exists_by_xpath

    def get_expanded_api_data(self, row_index):
        i = 1
        self.click_configure_networks()
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].click()
        self.wait_till_ajax_done(self.browser)
        rows = self.get_rows()
        div_elements = rows[
            row_index +
            1].find_element_by_tag_name('td').find_elements_by_tag_name('label')
    # end get_expanded_api_data_in_webui

    def parse_advanced_view(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className != 'preBlock'){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end parse_advanced_view

    def get_node_status_string(self, time):
        time = str(time)
        offset = 1
        time_string = json.loads(
            self.browser.execute_script(
                " var startTime = new XDate(" +
                time +
                "/1000); var status = diffDates(startTime,XDate()); return JSON.stringify(status);"))
        if len(time_string.split()[:-1]) != 0:
            if len(time_string.split()[:-1]) == 2:
                days = time_string.split()[-3] + ' '
            else:
                days = ''
            hrs = int(time_string.split()[-2][:-1])
            days_hrs = ' '.join(time_string.split()[:-1]) + ' '
        else:
            days_hrs = None
        minute_range = range(int(time_string.split(
        )[-1][:-1]) - offset, int(time_string.split()[-1][:-1]) + offset + 1)
        if days_hrs is not None:
            if hrs - 1 != 0:
                hrs = str(hrs - 1) + 'h' + ' '
            else:
                hrs = ''
            status_time_list = [days +
                                hrs +
                                str(60 +
                                    minute) +
                                'm' if minute < 0 else days_hrs +
                                str(minute) +
                                'm' for minute in minute_range]
        else:
            status_time_list = [str(minute) + 'm' for minute in minute_range]
        return status_time_list
    # end get_node_status_string

    def get_process_status_string(
            self,
            item,
            process_down_stop_time_dict,
            process_up_start_time_dict):
        offset = 1
        last_start_time = int(
            0 if item['last_start_time'] is None else item['last_start_time'])
        last_stop_time = int(
            0 if item['last_stop_time'] is None else item['last_stop_time'])
        last_exit_time = int(
            0 if item['last_exit_time'] is None else item['last_exit_time'])
        if item['process_state'] == 'PROCESS_STATE_RUNNING':
            status_time_list = self.get_node_status_string(last_start_time)
            status_string_list = ['Up since ' +
                                  status for status in status_time_list]
            process_up_start_time_dict[item['process_name']] = last_start_time
        else:
            down_time = max(last_stop_time, last_exit_time)
            status_down_time_list = self.get_node_status_string(down_time)
            process_down_stop_time_dict[item['process_name']] = down_time
            status_string_list = ['Down since ' +
                                  status for status in status_down_time_list]
        return status_string_list
    # end get_process_status_string

    def get_advanced_view_str(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length && eleList[j].className == 'string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_str

    def get_advanced_view_str_special(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-2; i++){if(eleList[i].className == 'preBlock' && eleList[i + 2].className == 'expanded'){ var j = i + 2 , itemArry = [];  while(j < eleList.length && eleList[j].className != 'key' ){ if(eleList[j].className == 'string'){itemArry.push(eleList[j].innerHTML);}  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_str

    def get_advanced_view_num(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className == 'preBlock' && eleList[i + 4].className == 'number'){dataSet.push({key : eleList[i+3].innerHTML, value : eleList[i + 4].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_num

    def get_basic_view_details(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('div.widget-main.row-fluid').find('label').find('div'),dataSet = []; for(var i = 0; i < eleList.length; i++){if(eleList[i].className == 'key span5' && eleList[i + 1].className == 'value span7'){dataSet.push({key : eleList[i].innerHTML,value:eleList[i+1].innerHTML.replace(/^\s+|\s+$/g, '')});}} return JSON.stringify(dataSet);"))
        return domArry
    # end get_basic_view_details

    def get_vm_basic_view(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('div.slick-row-detail-container').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className == 'span2' && eleList[i + 1].className == 'span10'){dataSet.push({key : eleList[i].getElementsByTagName('label')[0].innerHTML,value:eleList[i+1].innerHTML});}} return JSON.stringify(dataSet);"))
        return domArry
    # end get_vm_basic_view

    def get_basic_view_infra(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('ul#detail-columns').find('li').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className== 'key span5' && eleList[i + 1].className == 'value span7'){dataSet.push({key : eleList[i].innerHTML.replace(/(&nbsp;)*/g,''),value:eleList[i+1].innerHTML.replace(/^\s+|\s+$/g, '')});}} return JSON.stringify(dataSet);"))
        return domArry
    # end get_basic_view_infra

    def trim_spl_char(self, d):
        data = []
        for item in d:
            if item['key'].endswith(':'):
                k = item['key'][:-1]
            else:
                k = item['key']

            if isinstance(item['value'], list):
                l = []
                for g in range(len(item['value'])):
                    l.append(item['value'][g].replace('"', ''))
            else:
                l = item['value'].replace('"', '')
            data.append({'key': k, 'value': l})
        return data
    # end trim_spl_char

    def get_items(self, d, key):
        data = []
        for item in d:
            if item['key'] == key:
                data.append(item)
        return data
    # end trim_spl_char

    def extract_keyvalue(self, dict_in, list_out):
        for key, value in dict_in.items():
            if isinstance(value, dict):  # If value itself is dictionary
                self.extract_keyvalue(value, list_out)
            elif isinstance(value, list):  # If value itself is list
                for val in value:
                    if isinstance(val, dict):
                        self.extract_keyvalue(val, list_out)
                    else:
                        dictn = {}
                        dictn['key'] = key
                        dictn['value'] = value
                        list_out.append(dictn)
                        break
            elif value is None:
                dictn = {}
                dictn['key'] = key
                dictn['value'] = None
                list_out.append(dictn)
            else:
                dictn = {}
                dictn['key'] = key
                dictn['value'] = value
                list_out.append(dictn)
    # end  extract_keyvalue

    def match_ui_values(self, complete_ops_data, webui_list):
        error = 0
        match_count = 0
        for ops_items in complete_ops_data:
            match_flag = 0
            for webui_items in webui_list:
                if ops_items['value'] == webui_items['value'] or ops_items['value'].split(':')[0] == webui_items['value'] or (
                        ops_items['value'] == 'True' and ops_items['key'] == 'active' and webui_items['value'] == 'Active'):
                    self.logger.info(
                        "Ops key %s ops_value %s matched with %s" %
                        (ops_items['key'], ops_items['value'], webui_items['value']))
                    match_flag = 1
                    match_count += 1
                    break
            if not match_flag:
                self.logger.error(
                    "Ops key %s ops_value %s not found/matched" %
                    (ops_items['key'], ops_items['value']))
                error = 1

        self.logger.info("Total ops/api key-value count is %s" %
                         (str(len(complete_ops_data))))
        self.logger.info(
            "Total ops/api key-value matched count is %s" %
            (str(match_count)))
        return not error

    # end match_ui_values

    def date_time_string(self):
        current_date_time = str(datetime.datetime.now())
        return '_' + \
            current_date_time.split()[0] + '_' + current_date_time.split()[1]
    # end date_time_string

    def match_ui_kv(self, complete_ops_data, merged_arry):
        #self.logger.info("opserver data to be matched : %s"% complete_ops_data)
        #self.logger.info("webui data to be matched : %s"%  merged_arry)
        self.logger.debug(self.dash)
        no_error_flag = True
        match_count = 0
        not_matched_count = 0
        skipped_count = 0
        delete_key_list = [
            'in_bandwidth_usage',
            'cpu_one_min_avg',
            'vcpu_one_min_avg',
            'out_bandwidth_usage',
            'free',
            'buffers',
            'five_min_avg',
            'one_min_avg',
            'bmax',
            'used',
            'in_tpkts',
            'out_tpkts',
            'bytes',
            'ds_arp_not_me',
            'in_bytes',
            'out_bytes',
            'in_pkts',
            'out_pkts',
            'sum',
            'cpu_share',
            'exception_packets_allowed',
            'exception_packets',
            'average_bytes',
            'calls',
            'b400000',
            'b0.2',
            'b1000',
            'b520000',
            'b300000',
            'b0.1',
            'res',
            'b1',
            'used',
            'free',
            'b200000',
            'fifteen_min_avg',
            'b2',
            'peakvirt',
            'virt',
            'ds_interface_drop',
            'COUNT(cpu_info)',
            'COUNT(vn_stats)',
            'SUM(cpu_info.cpu_share)',
            'SUM(cpu_info.mem_virt)',
            'table',
            'ds_discard',
            'ds_flow_action_drop',
            'total_flows',
            'active_flows',
            'aged_flows',
            'ds_duplicated',
            'udp_sport_bitmap',
            'tcp_sport_bitmap',
            'udp_dport_bitmap',
            'tcp_dport_bitmap']
        index_list = []
        for num in range(len(complete_ops_data)):
            for element in complete_ops_data:
                if element['key'] in delete_key_list:
                    index = complete_ops_data.index(element)
                    del complete_ops_data[index]
                    skipped_count += 1
        for i in range(len(complete_ops_data)):
            item_ops_key = complete_ops_data[i]['key']
            item_ops_value = complete_ops_data[i]['value']
            check_type_of_item_ops_value = not isinstance(item_ops_value, list)
            matched_flag = 0
            webui_match_try_list = []
            key_found_flag = 0
            for j in range(len(merged_arry)):
                matched_flag = 0
                item_webui_key = merged_arry[j]['key']
                item_webui_value = merged_arry[j]['value']
                check_type_of_item_webui_value = not isinstance(
                    item_webui_value,
                    list)
                if (item_ops_key == item_webui_key and (item_ops_value == item_webui_value or (
                        item_ops_value == 'None' and item_webui_value == 'null'))):
                    self.logger.info(
                        "Ops/api key %s : value %s matched" %
                        (item_ops_key, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif (item_ops_key == item_webui_key and item_ops_value == 'True' and item_webui_value == 'true' or item_ops_value == 'False'
                      and item_webui_value == 'false' or item_ops_key == 'build_info'):
                    if item_ops_key == 'build_info':
                        self.logger.info(
                            "Skipping : ops key %s : value %s skipping match" %
                            (item_ops_key, item_ops_value))
                        skipped_count = +1
                    else:
                        self.logger.info(
                            "Ops/api key %s : value %s matched" %
                            (item_ops_key, item_ops_value))
                        match_count += 1
                    matched_flag = 1
                    break

                elif (check_type_of_item_webui_value and item_ops_key == item_webui_key and item_ops_value == (item_webui_value + '.0')):
                    self.logger.info(
                        "Ops/api key %s.0 : value %s matched" %
                        (item_ops_key, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and not isinstance(item_webui_value, list) and isinstance(item_ops_value, list) and (item_webui_value in item_ops_value):
                    self.logger.info(
                        "Webui key %s : value : %s matched in ops/api value range list %s " %
                        (item_webui_key, item_webui_value, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and isinstance(item_webui_value, list) and isinstance(item_ops_value, list):
                    count = 0
                    if len(item_webui_value) == len(item_ops_value):
                        for item_webui_index in range(len(item_webui_value)):
                            for item_ops_index in range(len(item_ops_value)):
                                if (item_webui_value[
                                        item_webui_index] == item_ops_value[item_ops_index]):
                                    count += 1
                                    break
                                elif isinstance(item_webui_value[item_webui_index], (str, unicode)) and item_webui_value[item_webui_index].strip() == item_ops_value[item_ops_index]:
                                    count += 1
                                    break
                        if(count == len(item_webui_value)):
                            self.logger.info(
                                "Ops key %s.0 : value %s matched" %
                                (item_ops_key, item_ops_value))
                            matched_flag = 1
                            match_count += 1
                    break
                elif item_ops_key == item_webui_key:
                    webui_match_try_list.append(
                        {'key': item_webui_key, 'value': item_webui_value})
                    key_found_flag = 1
            if not matched_flag:
                #self.logger.error("ops key %s : value %s not matched with webui data"%(item_ops_key, item_ops_value))
                if key_found_flag:
                    self.logger.error(
                        "Ops/api key %s : value %s not matched key-value pairs list %s" %
                        (item_ops_key, item_ops_value, webui_match_try_list))
                    self.screenshot('ERROR_MISMATCH_' + item_ops_key)
                else:
                    self.logger.error(
                        "Ops/api key %s : value %s not found, webui key %s webui value %s " %
                        (item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    self.screenshot('ERROR_NOT_FOUND_' + item_ops_key)
                not_matched_count += 1
                for k in range(len(merged_arry)):
                    if item_ops_key == merged_arry[k]['key']:
                        webui_key = merged_arry[k]['key']
                        webui_value = merged_arry[k]['value']
                no_error_flag = False
        self.logger.info("Total ops/api key-value count is %s" %
                         (str(len(complete_ops_data))))
        self.logger.info(
            "Total ops/api key-value matched count is %s" %
            (str(match_count)))
        self.logger.info("Total ops/api key-value not matched count is %s" %
                         str(not_matched_count))
        self.logger.info("Total ops/api key-value match skipped count is %s" %
                         str(skipped_count))
        return no_error_flag
    # end match_ui_kv
