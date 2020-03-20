from __future__ import division
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
import os
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


class WebuiCommon(object):
    count_in = False

    def __init__(self, obj):
        self.delay = 20
        self.inputs = obj.inputs
        self.jsondrv = JsonDrv(self, args=self.inputs)
        self.connections = obj.connections
        self.browser = obj.browser
        self.browser_openstack = obj.browser_openstack
        self.frequency = 3
        self.logger = self.inputs.logger
        self.dash = "-" * 60
        self.cwd = os.getcwd()
        self.log_path = ('%s' + '/logs/') % self.cwd
        self.log_dir = '/var/log/'
    # end __init__

    def check_login(self, login_type='horizon'):
        con = self.connections.ui_login
        if login_type == 'horizon':
            con.login(
                self.browser_openstack,
                con.os_url,
                con.username,
                con.password)
        else:
            con.login(
                self.browser,
                con.webui_url,
                con.username,
                con.password)
    # end check_login

    def wait_till_ajax_done(self, browser, jquery=True, wait=5):
        jquery = False
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

    def get_vmi_list_ops(self):
        return self._get_list_ops('virtual-machine-interfaces')
    # end get_vmi_list_ops

    def get_database_nodes_list_ops(self):
        return self._get_list_ops('database-nodes')
    # end get_database_nodes_list_ops

    def get_generators_list_ops(self):
        return self._get_list_ops('generators')
    # end get_generators_list_ops

    def get_bgp_peers_list_ops(self):
        return self._get_list_ops('bgp-peers')
    # end get_bgp_peers_list_ops

    def get_policy_list_api(self):
        return self._get_list_api('network-policys')
    # end get_vn_list_api

    def get_dns_servers_list_api(self):
        return self._get_list_api('virtual-DNSs')
    # end get_dns_servers_list_api

    def get_dns_records_list_api(self):
        return self._get_list_api('virtual-DNS-records')
    # end get_dns_records_list_api

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
    # end get_security_group_list_api

    def get_nrt_list_api(self):
        return self._get_list_api('route-tables')
    # end get_nrt_list_api

    def get_ragg_list_api(self):
        return self._get_list_api('route-aggregates')
    # end get_ragg_list_api

    def get_rpol_list_api(self):
        return self._get_list_api('routing-policys')
    # end get_rpol_list_api

    def get_fc_list_api(self):
        return self._get_list_api('forwarding-classs')
    # end get_fc_list_api

    def get_qos_list_api(self):
        return self._get_list_api('qos-configs')
    # end get_qos_list_api

    def get_shc_list_api(self):
        return self._get_list_api('service-health-checks')
    # end get_shc_list_api

    def get_bgpaas_list_api(self):
        return self._get_list_api('bgp-as-a-services')
    # end get_bgpaas_list_api

    def get_pif_list_api(self):
        return self._get_list_api('physical-interfaces')
    # end get_pif_list_api

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

    def get_database_nodes_list_ops(self):
        return self._get_list_ops('database-nodes')
    # end get_database_nodes_list_ops

    def get_modules_list_ops(self):
        return self._get_list_ops('modules')
    # end get_modules_list_ops

    def get_service_instances_list_ops(self):
        return self._get_list_ops('service-instances')
    # end get_service_instances_list_ops

    def get_vn_list_api(self):
        return self._get_list_api('virtual-networks')
    # end get_vn_list_api

    def get_global_config_api(self, option):
        return self._get_list_api(option)
    # end get_global_config_api

    def get_intf_table_list_api(self):
        return self._get_list_api('interface-route-tables')
    # end get_intf_table_list_api

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

    def get_phy_router_list_api(self):
        return self._get_list_api('physical-routers')
    # end get_phy_router_list_api

    def get_alarms_list_api(self):
        return self._get_list_api('alarms')
    # end get_alarms_list_api

    def get_access_list_api(self):
        return self._get_list_api('api-access-lists')
    # end get_access_list_api

    def get_vrouter_list_api(self):
        return self._get_list_api('virtual-routers')
    # end get_vrouter_list_api

    def get_svc_appls_list_api(self):
        return self._get_list_api('service-appliances')
    # end get_svc_appls_list_api

    def get_bgp_router_list_api(self):
        return self._get_list_api('bgp-routers')
    # end get_bgp_router_list_api

    def get_svc_appl_sets_list_api(self):
        return self._get_list_api('service-appliance-sets')
    # end get_svc_appl_sets_api

    def get_vm_list_api(self):
        return self._get_list_api('virtual-machines')
    # end get_vm_list_api

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
            for k, v in kargs.items():
                if not isinstance(v, list):
                    v = str(v)
                if v:
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

    def webui_logout(self):
        try:
            self.click_element('user_info', browser=self.browser)
            self.click_element('fa-power-off', 'class', browser=self.browser)
        except WebDriverException:
            pass
    # end webui_logout

    def click(self, objs):
        for obj in objs:
            try:
                obj.click()
            except:
                pass
    # end click

    def click_on_create(
            self,
            element_type,
            func_suffix=None,
            name=None,
            save=False,
            new_rule=True,
            select_project=True,
            prj_name='admin'):
        browser = self.browser
        index = 0
        if element_type in ('Security Group', 'DNS Server', 'DNS Record'):
            element = 'Create ' + element_type
            element_new = func_suffix[:-1]
        elif element_type == 'Port':
            element = 'Create ' + element_type
            element_new = 'Ports'
        elif element_type == 'Floating IP':
            element = 'Allocate ' + element_type
            element_new = func_suffix
        elif element_type == 'IPAM':
            element = 'Create ' + element_type
            element_new = element_type
        elif element_type == 'PhysicalRouter':
            element = 'btnAdd' + element_type
            element_new = func_suffix
        elif element_type in ['Interface', 'Floating IP Pools']:
            element = 'Add ' + element_type
            element_new = func_suffix
        elif element_type == 'QoS':
            element = 'Create ' + element_type
            element_new = func_suffix +'_cofig'
        elif element_type == 'QOS':
            element = 'btnCreate' + element_type
            element_new = 'qos_cofig'
        elif element_type == 'Routing Policy':
            element = 'Create ' + element_type
            element_new = 'routingPolicy'
        elif element_type == 'Flow Aging ':
            element = 'Edit ' + element_type
            element_new = func_suffix
        else:
            element = 'Create ' + element_type
            element_new = func_suffix
        if save:
            elem = 'configure-%sbtn1' % (element_new)
        else:
            click_func = 'click_configure_' + func_suffix
            click_func = getattr(self, click_func)
            if not click_func():
                self.logger.error(
                    "Error occurred while clicking %s" %
                    (click_func))
                return False
            if select_project:
                if element_type == 'DNS Record':
                    self.select_dns_server(prj_name)
                elif element_type == 'Interface':
                    self.select_project(prj_name, proj_type='prouter')
                elif element_type == 'Service Appliance':
                    self.select_project(prj_name, proj_type='service appliance set')
                elif not element_type in ['DNS Server']:
                    self.select_project(prj_name)
            self.logger.info("Creating %s %s using contrail-webui" %
                             (element_type, name))
            rbac = re.search('rbac_in_(.*)', func_suffix)
            if rbac:
                if rbac.group(1) in ['domain', 'project']:
                    index = 1
                else:
                    index = 0
            toolbar_xpath = "//a[@class='widget-toolbar-icon' and @title='%s']" % element
        if not save:
            if element_type in ['PhysicalRouter', 'QOS']:
                self.click_element(element)
            else:
                try:
                    self.click_element(toolbar_xpath, 'xpath', browser=browser,
                                      elements=True, index=index)
                except WebDriverException:
                    try:
                        self.click_element('close', 'class', screenshot=False)
                    except:
                        pass
                    raise
            self.wait_till_ajax_done(self.browser)
        if save:
            self.click_element(elem)
            if not self.check_error_msg(
                    "Click on %s" %
                    (elem),
                    close_window=True):
                self.logger.error("Click on save button %s failed" % (elem))
                try:
                    self.click_element('close', 'class', screenshot=False)
                except:
                    pass
                return False
            self.logger.info(
	        "Click on save button %s successful" %
	        (element_type))
        else:
            self.logger.info("Click on icon + %s successful" % (element_type))
        return True
    # end click_on_create

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
            if not project in list(count.keys()):
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
            wait=2,
            index=-1, delay=None, screenshot=True):
        if not browser:
            browser = self.browser
        if not delay:
            delay = self.delay
        else:
            jquery = False
        element_to_click = self.find_element(
            element_name_list,
            element_by_list,
            browser,
            if_elements,
            elements,
            delay=delay,
            screenshot=screenshot)
        try:
            if index == -1:
                element_to_click.click()
            else:
                element_to_click[index].click()
            self.wait_till_ajax_done(browser, jquery, wait)
        except:
            self.logger.error(
                'Element found but click failed \'%s\' element name \'%s\'' %
                (element_by_list, element_name_list))
        self.logger.debug(
            'Click element_by : \'%s\' element name \'%s\' successful' %
            (element_by_list, element_name_list))
    # end _click_element

    def send_keys(
            self,
            keys,
            element_name_list,
            element_by_list='id',
            browser=None,
            clear=False,
            if_elements=[],
            elements=False):
        if not browser:
            browser = self.browser
        send_keys_to_element = self.find_element(
            element_name_list, element_by_list, browser, if_elements, elements)
        if clear:
            send_keys_to_element.clear()
        send_keys_to_element.send_keys(keys)
        time.sleep(2)
    # end send_keys

    def click_on_caret_down(self, browser=None, type='down'):
        if not browser:
            browser = self.browser
        element = 'fa-caret-' + type
        self.click_element(element, 'class', browser, wait=2)
    # end click_on_caret_down

    def click_on_accordian(self, element_id, browser=None,
                           accor=True, def_type=True):
        """
        Clicks on the accordian icon on a create/edit page when the element id is passed
        Also scrolls down to get the fields in view of the page
        PARAMETERS :
            element_id : The element which needs to be searched by id using find_element
            browser    : If a specific browser is needed; else, 'None' is taken by default
                            and self.browser will be used
            accor      : If 'accordian' is not part of the id name, set False;
                            else, 'True' is taken by default
            def_type   : Set to 'True' if the element id needs to be appended with '_accordian';
                            'False' if 'Accordian' needs to be appended
        """
        if not browser:
            browser = self.browser
        if accor:
            if def_type:
                element_id = element_id + '_accordian'
            else:
                element_id = element_id + 'Accordian'
        if not accor:
            def_type = False
        try:
            element = self.find_element(element_id)
            self.browser.execute_script("return arguments[0].scrollIntoView();", element)
            element.click()
        except WebDriverException:
            self.logger.error("Click on %s failed" % element_id)
    # end click_on_accordian

    def find_element(
            self,
            element_name_list,
            element_by_list='id',
            browser=None,
            if_elements=[],
            elements=False, delay=None, screenshot=True):
        obj = None
        if not delay:
            delay = self.delay
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
                                browser, element_by, element, screenshot)[indx]
                        else:
                            obj = self._find_elements_by(
                                browser, element_by, element_name, screenshot)
                    else:
                        obj = self._find_element_by(
                            browser,
                            element_by,
                            element_name,
                            delay,
                            screenshot)
                else:
                    if index in if_elements:
                        if isinstance(element_name, tuple):
                            element, indx = element_name
                            obj = self._find_elements_by(
                                obj, element_by, element, screenshot)[indx]
                        else:
                            obj = self._find_elements_by(
                                obj, element_by, element_name, screenshot)
                    else:
                        obj = self._find_element_by(
                            obj, element_by, element_name, delay, screenshot)
        else:
            if elements:
                if isinstance(element_name_list, tuple):
                    element_name, element_index = element_name_list
                    obj = self._find_elements_by(
                        browser,
                        element_by_list,
                        element_name,
                        screenshot)[element_index]
                else:
                    obj = self._find_elements_by(
                        browser,
                        element_by_list,
                        element_name_list,
                        screenshot)
            else:
                obj = self._find_element_by(
                    browser,
                    element_by_list,
                    element_name_list,
                    delay,
                    screenshot)
        return obj
        # end find_element

    def _find_element_by(
            self,
            browser_obj,
            element_by,
            element_name,
            delay=None,
            screenshot=True):
        if not delay:
            delay = self.delay
        try:
            if element_by == 'id':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_id(element_name))
            elif element_by == 'class':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_class_name(element_name))
            elif element_by == 'name':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_name(element_name))
            elif element_by == 'xpath':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_xpath(element_name))
            elif element_by == 'link_text':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_link_text(element_name))
            elif element_by == 'tag':
                if isinstance(element_name, tuple):
                    name1, name2 = element_name
                    obj = None
                    try:
                        obj = WebDriverWait(
                            browser_obj,
                            delay,
                            self.frequency).until(
                            lambda a: a.find_element_by_tag_name(name1))
                    except WebDriverException:
                        obj = WebDriverWait(
                            browser_obj,
                            delay,
                            self.frequency).until(
                            lambda a: a.find_element_by_tag_name(name2))
                else:
                    obj = WebDriverWait(
                        browser_obj,
                        delay,
                        self.frequency).until(
                        lambda a: a.find_element_by_tag_name(element_name))
            elif element_by == 'css':
                obj = WebDriverWait(browser_obj, delay, self.frequency).until(
                    lambda a: a.find_element_by_css_selector(element_name))
            else:
                self.logger.error('Incorrect element_by:%s or value:%s' %
                                  (element_by, element_name))
        except WebDriverException:
            if screenshot:
                self.screenshot(
                    'Error_find_element_by_' +
                    str(element_by) +
                    '_' +
                    str(element_name))
                self.logger.error(
                    'element_by \'%s\' element name \'%s\' not found' %
                    (element_by, element_name))
            raise
        self.logger.debug(
            'element_by \'%s\' element name \'%s\' found' %
            (element_by, element_name))
        return obj
    # end find_element_by

    def _find_elements_by(
            self,
            browser_obj,
            elements_by,
            element_name,
            screenshot=True):
        try:
            if elements_by == 'id':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_id(element_name))
            elif elements_by == 'class':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_class_name(element_name))
            elif elements_by == 'name':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_name(element_name))
            elif elements_by == 'xpath':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_xpath(element_name))
            elif elements_by == 'link_text':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_link_text(element_name))
            elif elements_by == 'tag':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_tag_name(element_name))
            elif elements_by == 'css':
                obj = WebDriverWait(
                    browser_obj,
                    self.delay,
                    self.frequency).until(
                    lambda a: a.find_elements_by_css_selector(element_name))
            else:
                self.logger.error('Incorrect element_by or value :  %s  %s ' %
                                  (elements_by, element_name))
        except WebDriverException:
            if screenshot:
                self.screenshot(
                    'Error_find_elements_by_' +
                    str(elements_by) +
                    '_' +
                    str(element_name))
                self.logger.error(
                    'elements_by \'%s\' element name \'%s\' not found' %
                    (elements_by, element_name))
            raise
        self.logger.debug(
            'elements_by \'%s\' element name \'%s\' found' %
            (elements_by, element_name))
        return obj
    # end find_elements_by

    def click_on_select2_arrow(self, id):
        self.click_element(
            [id, 'select2-arrow'], ['id', 'class'])
        time.sleep(3)
    # end click_on_select2_arrow

    def find_xpath_elements(self, xpath):
        elements = self.find_element(xpath, 'xpath', elements=True)
        return elements
    # end find_xpath_elements

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
    # end select_from_dropdown

    def find_select_from_dropdown(
            self, element_text,
            browser=None, index=0,
            case=None):
        flag = False
        result = True
        if not browser:
            browser = self.browser
        br = self.find_element(
            'ui-autocomplete', 'class', elements=True)
        for index in range(len(br)):
            if br[index].text:
                break
        ele_types = self.find_element(
            'ui-menu-item', 'class', elements=True, browser=br[index])
        if not ele_types:
            self.logger.debug('Drop-down list not found')
            return False
        ele_dropdown = [element.find_element_by_tag_name('a')
                            for element in ele_types]
        for ele in ele_dropdown:
            if case == None:
                comp_ele = ele.text
            elif case == 'lower':
                comp_ele = ele.text.lower()
            elif case == 'upper':
                comp_ele = ele.text.upper()
            if comp_ele == element_text:
                flag = True
                ele.click()
                break
        if not flag:
            self.logger.debug('%s not found in the dropdown' % element_text)
            result = result and False
        return result
    # end find_select_from_dropdown

    def dropdown(self, id, element_name, element_type=None, browser_obj=None, grep=False):
        if browser_obj:
            obj = browser_obj
        else:
            obj = self.browser
        try:
            if not element_type:
                self.click_element(
                    [id, 'select2-arrow'], ['id', 'class'], browser=obj)
            else:
                self.click_element(
                    [id, 'select2-arrow'], [element_type, 'class'], browser=obj)
            self.select_from_dropdown(element_name, grep=grep)
            self.logger.info(
                ' %s successfully got selected from the dropdown' %
                (element_name))
            return True
        except:
            self.logger.error(
                '%s %s not found in the dropdown' %
                (id, element_name))
            raise
    # end dropdown

    def click_select_multiple(self, element_type, element_list):
        try:
            for element in element_list:
                self.click_element([element_type, 'input'], ['id', 'tag'])
                select_list = self.browser.find_elements_by_xpath(
                    "//*[@class = 'select2-match']/..")
                if not self._click_if_element_found(element, select_list):
                    return False
            self.logger.info(
                'All elements from %s successfully got selected' %
                (element_list))
            return True
        except:
            self.logger.error(
                'Some of the elements from %s not found in the dropdown' %
                (element_list))
            raise
    # end click_select_list

    def _click_if_element_found(self, element_name, elements_list):
        for element in elements_list:
            if element.text == element_name:
                element.click()
                return True
        self.find_element('select2-drop-mask').click()
        self.logger.error('No matches found error')
        return False
    # end _click_if_element_found

    def click_if_element_found(self, objs, element_text, grep=False):
        element_found = False
        for index, element_obj in enumerate(objs):
            element_obj_text = element_obj.text
            if (grep and element_obj_text.find(element_text) != -
                    1) or (not grep and element_obj_text == element_text):
                element_found = True
                element_obj.click()
                self.wait_till_ajax_done(self.browser, jquery=False, wait=4)
                break
            else:
                if index == len(objs) - 1:
                    element_obj.click()
        if not element_found:
            self.logger.error(' %s not found' % (element_text))
            self.click_on_cancel_if_failure('cancelBtn')
            return False
        return True
    # end click_if_element_found

    def select_project(self, project_name='admin', proj_type='projects'):
        proj_type = proj_type.replace(' ', '\-')
        proj_crumb = 's2id_' + proj_type + '\-breadcrumb\-dropdown'
        current_project = self.find_element(
            [proj_crumb, 'span'], ['id', 'tag']).text
        if not current_project == project_name:
            self.click_element(
                [proj_crumb, 'a'], ['id', 'tag'], jquery=False, wait=4)
            elements_obj_list = self.find_select2_drop_elements(self.browser)
            self.click_if_element_found(elements_obj_list, project_name)
    # end select_project

    def select_dns_server(self, dns_server_name):
        current_dns_server = self.find_element(
            's2id_undefined').text
        if not current_dns_server == dns_server_name:
            self.click_element('s2id_undefined')
            elements_obj_list = self.find_select2_drop_elements(self.browser)
            self.click_if_element_found(elements_obj_list, dns_server_name)
    # end select_dns_server

    def select_network(self, network_name='all networks'):
        current_network = self.find_element(
            ['s2id_networks\-breadcrumb\-dropdown', 'span'], ['id', 'tag']).text
        if not current_network == network_name:
            self.click_element(
                ['s2id_networks\-breadcrumb\-dropdown', 'span'], ['id', 'tag'], jquery=False, wait=4)
            elements_obj_list = self.find_select2_drop_elements(self.browser)
            self.click_if_element_found(elements_obj_list, network_name)
    # end select_network

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

    def get_memory_string(self, dictn, unit='B', control_flag=0):
        memory_list = []
        if isinstance(dictn, dict):
            if dictn.get('cpu_info'):
                if not control_flag:
                    memory = dictn.get('cpu_info').get('meminfo').get('res')
                else:
                    memory = dictn.get('cpu_info')[0].get('mem_res')
            else:
                memory = dictn.get('mem_res')
        else:
            memory = dictn
            memory = memory / 1024.0
        if unit == 'KB':
            memory = memory * 1024
        offset = 50
        if memory < 1024:
            offset = 80
            memory = round(memory, 2)
            memory_range = list(range(
                int(memory * 100) - offset, int(memory * 100) + offset))
            memory_range = [x / 100.0 for x in memory_range]
            for memory in memory_range:
                if float(memory) == int(memory):
                    memory_list.append(int(memory))
            memory_list = sorted(set(memory_list))
            memory_list = [str(mem) + ' KB' for mem in memory_list]
        elif memory / 1024.0 < 1024:
            memory = memory / 1024.0
            memory = round(memory, 2)
            memory_range = list(range(
                int(memory * 100) - offset, int(memory * 100) + offset))
            memory_range = [x / 100.0 for x in memory_range]
            for memory in memory_range:
                if isinstance(memory, float) and memory == int(memory):
                    index = memory_range.index(memory)
                    memory_range[index] = int(memory)
            memory_list = sorted(set(memory_list))
            memory_list = [str(memory) + ' MB' for memory in memory_range]
        else:
            memory = round(old_div(memory, 1024), 2)
            memory_range = list(range(
                int(memory * 100) - offset, int(memory * 100) + offset))
            memory_range = [x / 100.0 for x in memory_range]
            memory_range = [(memory / 1024.0) for memory in memory_range]
            for memory in memory_range:
                memory_list.append('%.2f' % memory)
                if float(memory) == int(memory):
                    memory_list.append(int(memory))
            memory_list = sorted(set(memory_list))
            memory_list = [str(mem) + ' GB' for mem in memory_list]
        return memory_list
    # end get_memory_string

    def get_cpu_string(self, dictn):
        offset = 15
        if dictn.get('cpu_info'):
            if isinstance(dictn.get('cpu_info'), list):
                cpu = float(dictn.get('cpu_info')[0].get('cpu_share'))
            else:
                cpu = float(dictn.get('cpu_info').get('cpu_share'))
        else:
            cpu = dictn.get('cpu_share')
        cpu_range = list(range(int(cpu * 100) - offset, int(cpu * 100) + offset))
        cpu_range = [x / 100.0 for x in cpu_range]
        cpu_list = [str('%.2f' % cpu) + ' %' for cpu in cpu_range]
        return cpu_list
    # end get_cpu_string

    def get_analytics_msg_count_string(self, dictn, size):
        offset = 25
        tx_socket_size = size
        analytics_msg_count = dictn.get('ModuleClientState').get(
            'session_stats').get('num_send_msg')
        analytics_msg_count_list = list(range(
            int(analytics_msg_count) -
            offset,
            int(analytics_msg_count) +
            offset))
        analytics_messages_string = [
            str(count) +
            ' [' +
            str(size) +
            ']' for count in analytics_msg_count_list for size in tx_socket_size]
        return analytics_messages_string
    # end get_analytics_msg_count_string

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

    def check_error_msg(self, error_msg, close_window=False):
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
                if close_window:
                    self.close_window()
                return False
        except (NoSuchElementException, ElementNotVisibleException):
            if close_window:
                self.close_window()
            return True
    # end check_error_msg

    def close_window(self, cancel_element=None):
        try:
            if cancel_element:
                self.click_element(
                    cancel_element_id,
                    delay=2,
                    screenshot=False)
            else:
                self.click_element(
                    "button[class='close']",
                    'class', delay=2,
                    if_elements=[1], index=0, screenshot=False)
        except WebDriverException:
            pass
    # end close_window

    def _rows(self, browser, canvas):
        try:
            if canvas:
                rows = self.find_element('grid-canvas', 'class', browser)
                rows = self.find_element(
                    'ui-widget-content',
                    'class',
                    rows,
                    elements=True, screenshot=False)
            else:
                rows = self.find_element(
                    'ui-widget-content',
                    'class',
                    browser,
                    elements=True, screenshot=False)
        except WebDriverException:
            rows = None
            pass
        return rows
    # end _rows

    def get_rows(self, browser=None, canvas=False):
        if not browser:
            browser = self.browser
        rows = None
        try:
            rows = self._rows(browser, canvas)
        except WebDriverException:
            self.wait_till_ajax_done(browser)
            try:
                rows = self._rows(browser, canvas)
            except:
                self.logger.debug("rows are not present on the page")
                return []
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

    def extract_and_convert(self, number, extract=True, convert='decimal'):
        """
        Extracts the number when given in the format for example - ef (101110)
        Converts and returns the new number
        PARAMETERS :
            extract    : If the number needs to be extracted. Default is 'True'
            convert    : Convert the number to decimal or binary as specified.
                            values - 'decimal' / 'binary'
                            Default - 'decimal'
            number     : The number which needs to be (extracted?and) converted
        """
        if extract:
            num = re.search('.*\((\d+)\)', number)
            number = num.group(1)
        if convert == 'decimal':
            new_num = int(number, 2)
        elif convert == 'binary':
            new_num = bin(number)[2:]
        else:
            new_num = number
            self.logger.error('Conversion type is not passed correctly')
        return new_num
    # end extract_and_convert

    def click_icon_caret(self, row_index, obj=None, length=None, indx=0, net=0):
        element0 = ('slick-cell', indx)
        if not net:
            element1 = ('div', 'span')
        else:
            element1 = ('div', 'i')
        try:
            if not obj:
                obj = self.find_element('grid-canvas', 'class')
            rows = None
            rows = self.get_rows(obj)
            if length:
                rows = self.check_rows(length, obj)
            br = rows[row_index]
            self.click_element(
                [element0, element1], ['class', 'tag'], br, if_elements=[0], delay=25)
        except StaleElementReferenceException:
            if not obj:
                obj = self.find_element('grid-canvas', 'class')
            rows = None
            rows = self.get_rows(obj)
            if length:
                rows = self.check_rows(length, obj)
            br = rows[row_index]
            self.click_element(
                [element0, element1], ['class', 'tag'], br, if_elements=[0], delay=25)
    # end click_icon_caret

    def click_monitor_instances_basic(self, row_index, length=None):
        self.click_monitor_instances()
        self.wait_till_ajax_done(self.browser)
        self.click_icon_caret(row_index, length=length, net=1)
    # end click_monitor_instances_basic_in_webui

    def select_max_records(self, option='networks', grid_name=None):
        if not grid_name:
            grid_name = 'project-' + option
        grid_br = self.find_element(grid_name)
        self.wait_till_ajax_done(self.browser)
        br = self.find_element('grid-canvas', 'class', browser=grid_br)
        self.click_element('slick-pager-sizes', 'class', browser=grid_br)
        select_result = "//li[contains(@class,'select2-results-dept-0')]"
        self.click_element(select_result, 'xpath', elements=True, index=3)
        self.browser.execute_script("return arguments[0].scrollIntoView();", br)
        return grid_br
    # end select_max_records

    def click_monitor_networking_dashboard_basic(self, row_index, option='networks'):
        self.click_monitor_networking_dashboard(option)
        br = self.select_max_records(option)
        self.click_icon_caret(row_index, net=1, obj=br)
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_networks_dashboard_basic

    def click_monitor_networks_basic(self, row_index, option='networks'):
        self.click_element(option.title(), 'link_text', jquery=False)
        self.wait_till_ajax_done(self.browser, wait=2)
        if option == 'projects':
            grid_name = option
        else:
            grid_name = None
        br = self.select_max_records(option, grid_name)
        self.click_icon_caret(row_index, net=1, obj=br)
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_instances_basic_in_webui

    def click_monitor_vrouters(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_vrouter', 'Virtual Routers'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor vrouters")
    # end click_monitor_vrouters_in_webui

    def click_monitor_dashboard(self):
        self.click_monitor()
        self.click_element('mon_infra_dashboard')
        self.screenshot("dashboard")
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor dashboard")
    # end click_monitor_dashboard_in_webui

    def click_monitor_networking_dashboard(self, tab='networks'):
        self.click_monitor_networks('dashboard')
        self.select_project(self.inputs.project_name)
        self.click_element('project-' + tab + '-tab-link')
        self.wait_till_ajax_done(self.browser, wait=2)
        return self.check_error_msg("monitor networking dashboard")
    # end click_monitor_networking_dashboard

    def click_monitor_config_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_config', 'Config Nodes'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor config nodes")
    # end click_monitor_config_nodes_in_webui

    def click_monitor_control_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_control', 'Control Nodes'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor control nodes")
    # end click_monitor_control_nodes_in_webui

    def click_monitor_analytics_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_analytics', 'Analytics Nodes'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor analytics nodes")
    # end click_monitor_analytics_nodes_in_webui

    def click_monitor_database_nodes(self):
        self.click_monitor()
        self.click_element(
            ['mon_infra_database', 'Database Nodes'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor database nodes")
    # end click_monitor_database_nodes

    def get_service_instance_list_api(self):
        url = 'http://' + self.inputs.cfgm_ip + ':8082/service-instances'
        obj = self.jsondrv.load(url)
        return obj
    # end get_service_instance_list_api

    def click_configure_service_instance_basic(self, row_index):
        self.click_element('Service Instances', 'link_text')
        self.check_error_msg("configure service instance")
        count = 0
        self.select_project(self.inputs.project_name)
        rows = self.get_rows(canvas=True)
        while True:
            if count > 120:
                self.logger.error('Status is Updating.')
            rows = self.get_rows(canvas=True)
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
        rows = self.get_rows(canvas=True)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_service_instance_basic_in_webui

    def click_configure_service_instance(self):
        self.click_element('btn-configure')
        self._click_on_config_dropdown(self.browser, 5)
        self.click_element(
            ['config_sc_svcInstances', 'Service Instances'], ['id', 'link_text'])
        time.sleep(2)
        return self.check_error_msg("configure service instances")
    # end click_configure_service_instance_in_webui

    def find_div_element_by_tag(self, index, browser, return_type='text'):
        element = self.find_element('div', 'tag', elements=True,
                                       browser=browser)[index]
        if return_type == 'text':
            return element.text
        else:
            return element
    # end find_div_element_by_tag

    def delete_element(self, fixture=None, element_type=None):
        result = True
        delete_success = None
        br = None
        if WebuiCommon.count_in == False:
            if element_type in ['phy_interface_delete', 'fc_delete']:
                pass
            else:
                if not element_type == 'svc_template_delete':
                    self.click_configure_networks()
                    if not fixture:
                        self.select_project(self.inputs.project_name)
                    else:
                        self.select_project(fixture.project_name)
                    WebuiCommon.count_in = True
        if element_type == 'svc_instance_delete':
            if not self.click_configure_service_instance():
                result = result and False
            element_name = fixture.si_name
            element_id = 'btnActionDelSvcInst'
            popup_id = 'configure-service_instancebtn1'
        elif element_type == 'svc_health_check_delete':
            if not self.click_configure_service_health_check():
                result = result and False
            element_name = fixture.name
            element_id = 'linkSvcHealthChkDelete'
            popup_id = 'configure-HealthCheckServicesbtn1'
        elif element_type == 'bgp_aas_delete':
            if not self.click_configure_bgp_as_a_service():
                result = result and False
            element_name = 'all'
            element_id = 'btnDeleteBGPAsAService'
            popup_id = 'configure-bgp_as_a_servicebtn1'
        elif element_type == 'vn_delete':
            if not self.click_configure_networks():
                result = result and False
            element_name = fixture.vn_name
            element_id = 'linkVNDelete'
            popup_id = 'configure-networkbtn1'
        elif element_type == 'svc_template_delete':
            if not self.click_configure_service_template():
                result = result and False
            element_name = fixture.st_name
            element_id = 'linkSvcTemplateDelete'
            popup_id = 'configure-service_templatebtn1'
        elif element_type == 'ipam_delete':
            if not self.click_configure_ipam():
                result = result and False
            element_name = fixture.name
            element_id = 'linkIpamDelete'
            popup_id = 'configure-IPAMbtn1'
        elif element_type == 'fip_delete':
            if not self.click_configure_fip():
                result = result and False
            element_name = fixture.pool_name + ':' + fixture.vn_name
            element_id = 'linkFipRelease'
            popup_id = 'configure-fipbtn1'
        elif element_type == 'policy_delete':
            if not self.click_configure_policies():
                result = result and False
            element_name = fixture.policy_name
            element_id = 'fa-trash'
            popup_id = 'configure-policybtn1'
        elif element_type == 'disassociate_fip':
            if not self.click_configure_fip():
                result = result and False
            element_name = fixture.vn_name + ':' + fixture.pool_name
            element_id = 'linkFipRelease'
            popup_id = 'configure-fipbtn1'
        elif element_type == 'port_delete':
            if not self.click_configure_ports():
                result = result and False
            element_name = fixture.vn_name
            element_id  = 'btnDeletePort'
            id_port_delete = 'fa-trash'
            popup_id = 'configure-Portsbtn1'
        elif element_type == 'router_delete':
            if not self.click_configure_routers():
                result = result and False
            element_name = 'all'
            element_id = 'fa-trash'
            popup_id = 'configure-logical_routerbtn1'
        elif element_type == 'dns_server_delete':
            if not self.click_configure_dns_servers():
                result = result and False
            element_name = 'all'
            element_id = 'btnActionDelDNS'
            popup_id = 'configure-dns_serverbtn1'
        elif element_type == 'dns_record_delete':
            if not self.click_configure_dns_records():
                result = result and False
            element_name = 'all'
            element_id = 'btnActionDelDNS'
            popup_id = 'configure-dns_recordbtn1'
        elif element_type == 'security_group_delete':
            if not self.click_configure_security_groups():
                result = result and False
            element_name = fixture.secgrp_name
            element_id = 'btnActionDelSecGrp'
            popup_id = 'configure-security_groupbtn1'
        elif element_type == 'phy_router_delete':
            if not self.click_configure_physical_router():
                result = result and False
            element_name = fixture.name
            element_id = 'btnDeletePhysicalRouter'
            popup_id = 'configure-physical_routerbtn1'
        elif element_type == 'phy_interface_delete':
            if not self.click_configure_interfaces():
                result = result and False
            element_name = fixture.name
            element_id = 'fa-trash'
            popup_id = 'configure-interfacebtn1'
        elif element_type == 'fc_delete':
            if not self.click_configure_forwarding_class():
                result = result and False
            element_name = fixture.name
            element_id = 'btnDeleteForwardingClass'
            popup_id = 'configure-forwarding_classbtn1'
            br = self.find_element('forwarding-class-grid')
        elif element_type == 'qos_config_delete':
            if fixture.global_flag:
                if not self.click_configure_global_qos():
                    result = result and False
                br = self.find_element('qos-grid')
            else:
                if not self.click_configure_qos():
                    result = result and False
            element_name = fixture.name
            element_id = 'btnDeleteQOS'
            popup_id = 'configure-qos_cofigbtn1'
        elif element_type == 'network_route_table_delete':
            if not self.click_configure_route_table():
                result = result and False
            element_name = 'all'
            element_id = 'btnActionDelRtTable'
            popup_id = 'configure-route_tablebtn1'
        elif element_type == 'routing_policy_delete':
            if not self.click_configure_routing_policy():
                result = result and False
            element_name = 'all'
            element_id = 'btnDeleteRoutingPolicy'
            popup_id = 'configure-routingPolicybtn1'
        elif element_type == 'route_aggregate_delete':
            if not self.click_configure_route_aggregate():
                result = result and False
            element_name = 'all'
            element_id = 'btnDeleteRouteAggregate'
            popup_id = 'configure-route_aggregatebtn1'
        elif element_type == 'bgp_router_delete':
            if not self.click_configure_bgp_router():
                result = result and False
            element_name = fixture.name
            element_id = 'btnDeleteBGP'
            popup_id = 'configure-bgp_routerbtn1'
        elif element_type == 'link_local_service_delete':
            if not self.click_configure_link_local_service():
                result = result and False
            element_id = 'btnActionDelLLS'
            popup_id = 'configure-link_local_servicesbtn1'
        elif element_type == 'vrouter_delete':
            if not self.click_configure_vrouter():
                result = result and False
            element_id = 'linkvRouterDelete'
            popup_id = 'configure-config_vrouterbtn1'
            element_name = 'all'
        elif element_type == 'svc_appliance_delete':
            element_id = 'btnActionDelSecGrp'
            popup_id = 'configure-svcAppliancebtn1'
        elif element_type == 'svc_appliance_set_delete':
            if not self.click_configure_svc_appliance_set():
                result = result and False
            element_id = 'btnActionDelSecGrp'
            popup_id = 'configure-svcApplianceSetbtn1'
        elif element_type == 'alarm_delete':
            if fixture.parent_obj_type == 'project':
                if not self.click_configure_alarms_in_project():
                    result = result and False
            else:
                if self.click_configure_alarms_in_global():
                    br = self.find_element('config-alarm-grid')
                else:
                    result = result and False
            element_name = fixture.alarm_name
            element_id = 'btnDeleteAlarm'
            popup_id = 'configure-configalarmbtn1'
        elif element_type == 'rbac_delete':
            click_func = 'self.click_configure_rbac_in_' + fixture.parent_type
            if not eval(click_func)():
                result = result and False
            else:
                br = self.find_element('rbac-' + fixture.parent_type + '-grid')
            if fixture.parent_type == 'global':
                element_id = 'btnDeleteRBAC'
            else:
                element_id = 'btnDelete' + fixture.parent_type.title() + 'RBAC'
            popup_id = 'configure-rbacbtn1'
            element_name = 'all'
        elif element_type == 'log_statistic_delete':
            if self.click_configure_log_stat_in_global():
                br = self.find_element('user-defined-counters-grid')
            else:
                result = result and False
            element_id = 'btnDeleteCounters'
            popup_id = 'configure-user_defined_countersbtn1'
            element_name = 'all'
        elif element_type == 'intf_route_tab_delete':
            if self.click_configure_intf_route_table():
                br = self.find_element('inf_rt-table-grid')
            else:
                result = result and False
            element_id = 'btnActionDelInfRtTable'
            element_name = fixture.name
        if not br:
            br = self.browser
        rows = self.get_rows(br, canvas=True)
        ln = 0
        if rows:
            ln = len(rows)
        if_select = False
        try:
            for num in range(ln):
                element = rows[num]
                if element_type == 'disassociate_fip':
                    element_text = element.find_elements_by_tag_name(
                        'div')[3].text
                    div_obj = element.find_elements_by_tag_name('div')[0]
                elif element_type == 'port_delete':
                    element_text = element.find_elements_by_tag_name(
                        'div')[3].text
                    div_obj = element.find_elements_by_tag_name('div')[1]
                elif element_type in ['router_delete', 'dns_server_delete',
                                      'dns_record_delete', 'bgp_aas_delete',
                                      'network_route_table_delete', 'rbac_delete',
                                      'routing_policy_delete', 'route_aggregate_delete']:
                    element_text = 'all'
                    div_obj = element.find_elements_by_tag_name('div')[1]
                elif element_type == 'bgp_router_delete':
                    element_text = self.find_element('div', 'tag', elements=True,
                                       browser=element)[5].text
                    div_obj = self.find_element('div', 'tag', elements=True,
                                  browser=element)[1]
                elif element_type == 'link_local_service_delete':
                    element_text = self.find_element('div', 'tag', elements=True,
                                       browser=element)[2].text
                    div_obj = self.find_element('div', 'tag', elements=True,
                                  browser=element)[1]
                    if element_text == 'metadata':
                        continue
                    else:
                        element_name = element_text
                elif element_type == 'log_statistic_delete':
                    element_text = 'all'
                    div_obj = self.find_div_element_by_tag(0, element, return_type='obj')
                else:
                    element_text = self.find_div_element_by_tag(2, element)
                    div_obj = self.find_div_element_by_tag(1, element, return_type='obj')
                    if element_type == 'vrouter_delete':
                        element_ip = self.find_div_element_by_tag(4, browser=element)
                        if element_ip == self.inputs.auth_ip:
                            continue
                        else:
                            element_name = element_text
                    if element_type == 'svc_appliance_set_delete':
                        if element_text in ['opencontrail', 'native']:
                            continue
                        else:
                            element_name = element_text
                    if element_type == 'svc_appliance_delete':
                        element_name = element_text
                if (element_text == element_name):
                    div_obj.find_element_by_tag_name('input').click()
                    if_select = True
                    rows = self.get_rows(canvas=True)
            if if_select:
                if element_type in ['policy_delete', 'router_delete']:
                    self.click_element(element_id, 'class')
                elif element_type == 'port_delete':
                    self.click_element("//a[@data-original-title='Delete']", 'xpath')
                elif element_type == 'phy_interface_delete':
                    self.click_element(element_id, 'class')
                    self.click_element("//a[@data-original-title='Delete Interface(s)']", 'xpath')
                else:
                    self.click_element(element_id)
                self.click_element(popup_id, screenshot=False)
                delete_success = True
                if not self.check_error_msg(
                        "Delete element %s %s" %
                        (element_type, popup_id)):
                    result = result and False
            # break
        except WebDriverException:
            self.logger.error("%s deletion failed " % (element_type))
            self.screenshot('delete' + element_type + 'failed')
            result = result and False
        if not delete_success:
            self.logger.warning("%s element does not exist" % (element_type))
        else:
            self.logger.info("%s %s successful using webui" %
                             (element_name, element_type))
        if not self.check_error_msg(element_type):
            self.logger.error("%s deletion failed " % (element_type))
            result = result and False
        return result
    # end delete_element

    def click_configure_networks(self):
        time.sleep(1)
        self.click_element('btn-configure')
        time.sleep(2)
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_networking_networks', 'Networks'], [
                        'id', 'link_text'])
        time.sleep(1)
        return self.check_error_msg("configure networks")
    # end click_configure_networks_in_webui

    def click_configure_Floating_IP_Pool(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_networking_fippool', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure fip pool")
    # end click_configure_Floating_IP_Pool

    def __wait_for_networking_items(self, a):
        if len(
                a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0:
            return True
    # end __wait_for_networking_items

    def click_configure_fip(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_networking_fip', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        return self.check_error_msg("configure fip")
    # end click_configure_fip_in_webui

    def click_configure_ports(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_ports', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure ports")
    # end click_configure_ports

    def click_configure_security_groups(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_sg', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure security groups")
    # end click_configure_security_grps

    def click_configure_security_groups_basic(self, row_index):
        self.click_configure_security_groups()
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_security_groups_basic

    def click_configure_routers(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_routers', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure routers")
    # end click_configure_routers

    def click_configure_routers_basic(self, row_index):
        self.click_configure_routers()
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_routers_basic

    def click_error(self, name):
        self.logger.error("Some error occured whlie clicking on %s" % (name))
        return False
    # end click_error

    def click_monitor(self):
        self.click_element('btn-monitor', jquery=False, wait=3)
        return self.check_error_msg("monitor")
    # end click_monitor

    def click_monitor_debug(self):
        self.click_monitor()
        children = self.find_element(
            ['menu', 'item'], ['id', 'class'], if_elements=[1])
        children[3].find_element_by_tag_name('span').click()
        self.wait_till_ajax_done(self.browser, wait=10)
    # end click_monitor_debug

    def click_monitor_packet_capture(self):
        self.click_monitor_debug()
        self.click_element(
            ['mon_debug_pcapture', 'Packet Capture'], ['id', 'link_text'])
        return self.check_error_msg("Debug Packet Capture")
    # end click_monitor_packet_capture

    def click_monitor_networking(self):
        self.click_monitor()
        children = self.find_element(
            ['menu', 'item'], ['id', 'class'], if_elements=[1])
        children[2].find_element_by_tag_name('span').click()
        self.wait_till_ajax_done(self.browser, wait=10)
    # end click_monitor_in_webui

    def click_monitor_networks(self, option='networks'):
        self.click_monitor_networking()
        self.click_element(
            ['mon_networking_' + option, option.title()], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
        return self.check_error_msg("monitor networks")
    # end click_monitor_networks_in_webui

    def click_monitor_instances(self):
        self.click_monitor_networking()
        self.click_element(
            ['mon_networking_instances', 'Instances'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser, wait=10)
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

    def click_monitor_database_nodes_basic(self, row_index):
        self.click_element('Database Nodes', 'link_text')
        self.check_error_msg("monitor database nodes")
        self.click_monitor_common_basic(row_index)
    # end click_monitor_database_nodes_basic

    def click_monitor_database_nodes_advance(self, row_index):
        self.click_element('Database Nodes', 'link_text')
        self.check_error_msg("monitor database nodes")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_database_nodes_advance

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

    def click_monitor_control_nodes_peers(self, row_index):
        self.click_icon_caret(row_index)
        self.click_element('control_node_peers_id-tab-link')
        self.wait_till_ajax_done(self.browser, wait=3)
    # end click_monitor_control_nodes_peers

    def click_monitor_analytics_nodes_advance(self, row_index):
        self.click_element('Analytics Nodes', 'link_text')
        self.check_error_msg("monitor analytics nodes")
        self.click_monitor_common_advance(row_index)
    # end click_monitor_analytics_nodes_advance_in_webui

    def click_monitor_common_advance(self, row_index):
        self.wait_till_ajax_done(self.browser, wait=10)
        self.click_icon_caret(row_index)
        self.click_element(["div[class*='widget-box transparent']", \
            'fa-cog'], ['css', 'class'])
        self.click_element(["div[class*='widget-box transparent']", \
            'fa-code'], ['css', 'class'])
    # end click_monitor_common_advance_in_webui

    def click_monitor_common_basic(self, row_index):
        self.wait_till_ajax_done(self.browser, wait=10)
        self.click_icon_caret(row_index)
        self.click_element(["div[class*='widget-box transparent']", \
            'fa-cog'], ['css', 'class'])
        self.click_element(["div[class*='widget-box transparent']", \
            'fa-list'], ['css', 'class'])
    # end click_monitor_common_basic_in_webui

    def click_monitor_networks_advance(self, row_index):
        self.click_element('Networks', 'link_text')
        self.check_error_msg("monitor networks")
        self.wait_till_ajax_done(self.browser, wait=10)
        self.click_icon_caret(row_index, net=1)
        rows = self.get_rows(canvas=True)
        self.click_element('fa-code', 'class', browser=rows[row_index + 1])
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_networks_advance_in_webui

    def click_monitor_instances_advance(self, row_index, length=None, option=None):
        if option == 'dashboard':
            self.click_monitor_networking_dashboard('instances')
            br = self.select_max_records('instances')
            rows = self.get_rows(canvas=True, browser=br)
            self.click_element('fa-caret-right', 'class', browser=rows[row_index])
        else:
            self.click_monitor_instances_basic(row_index, length)
            br = self.browser
        rows = self.get_rows(canvas=True, browser=br)
        self.click_element('fa-code', 'class', browser=rows[row_index + 1])
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_instances_advance_in_webui

    def click_monitor_interfaces_advance(self, row_index, length=None, option=None):
        if option == 'dashboard':
            click_func = 'networking_dashboard'
        else:
            click_func = 'networks'
        if not eval('self.click_monitor_' + click_func)('interfaces'):
            result = result and False
        br = self.select_max_records('interfaces')
        rows = self.get_rows(canvas=True, browser=br)
        self.click_element('fa-caret-right', 'class', browser=rows[row_index])
        self.wait_till_ajax_done(self.browser, wait=15)
        self.click_element('fa-code', 'class')
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_interfaces_advance

    def click_monitor_projects_advance(self, row_index, length=None):
        if not eval('self.click_monitor_networks')('projects'):
            result = result and False
        br = self.select_max_records(grid_name='projects')
        rows = self.get_rows(canvas=True, browser=br)
        self.click_element('fa-caret-right', 'class', browser=rows[row_index])
        self.wait_till_ajax_done(self.browser, wait=15)
        self.click_element('fa-code', 'class')
        self.wait_till_ajax_done(self.browser)
    # end click_monitor_projects_advance

    def click_configure_networks_basic(self, row_index):
        self.click_element('Networks', 'link_text')
        self.check_error_msg("configure networks")
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_networks_basic_in_webui

    def click_configure_ports_basic(self, row_index):
        self.click_element('Ports', 'link_text')
        self.check_error_msg("configure ports")
        rows = self.get_rows(canvas=True)
        port = self.find_element('div', 'tag', browser=rows[row_index],
            elements=True)[0]
        self.click_element('i', 'tag', browser=port)
        self.wait_till_ajax_done(self.browser)
    # end click_configure_ports_basic_in_webui

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

    def click_configure_fip_basic(self, row_index):
        self.click_element('Floating IPs', 'link_text')
        self.check_error_msg("configure fip")
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_fip_basic

    def click_configure_intf_route_table_basic(self, row_index):
        self.click_element('Interface Route Tables', 'link_text')
        self.check_error_msg("configure interface route table")
        br = self.find_element('inf_rt-table-grid')
        rows = self.get_rows(browser=br)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_intf_route_table_basic

    def click_configure_project_quotas(self):
        self._click_on_config_dropdown(self.browser, index=0)
        self.click_element(
            ['config_net_quotas', 'Project Settings'], ['id', 'link_text'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure project quotas")
    # end click_configure_project_quota

    def click_configure_global_config(self, parent_tab='global_vrouter',
                                     tab='forwarding_options', msg='Global Config'):
        if not self.click_configure_elements(0, 'config_infra_gblconfig',
                                             msg="Configure Global config"):
            return False
        else:
            self.click_element(parent_tab + '_configs-tab-link')
            self.click_element(tab + '_tab-tab-link')
            self.wait_till_ajax_done(self.browser, wait=3)
            return self.check_error_msg("Configure " + msg + " globally")
    # end click_configure_global_config

    def click_configure_service_template_basic(self, row_index):
        self.click_element(['config_service_templates', 'a'], ['id', 'tag'])
        self.check_error_msg("configure service template")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_service_template_basic_in_webui

    def click_configure_bgp_router(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 0)
        self.click_element(['config_infra_bgp', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser, wait=2)
        return self.check_error_msg("configure bgp routers")
    # end click_configure_bgp_router

    def click_configure_bgp_router_basic(self, row_index):
        self.click_configure_bgp_router()
        br = self.find_element('bgp-grid')
        rows = self.get_rows(browser=br)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_bgp_router_basic

    def click_configure_link_local_service(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 0)
        self.click_element(['config_infra_lls', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser, wait=2)
        return self.check_error_msg("configure link local services")
    # end click_configure_link_local_service

    def click_configure_link_local_service_basic(self, row_index):
        self.click_configure_link_local_service()
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_link_local_service_basic

    def click_configure_nodes(self, tab='virtual_routers',
                             msg="configure virtual routers"):
        if not self.click_configure_elements(0, 'config_infra_nodes',
                                  msg=msg):
            return False
        else:
            element = tab + '_tab-tab-link'
            self.click_element(element)
            self.wait_till_ajax_done(self.browser, wait=3)
            return self.check_error_msg("Configure " + msg)
    # end click_configure_nodes

    def click_configure_vrouter(self):
        return self.click_configure_nodes()
    # end click_configure_vrouter

    def click_configure_vrouter_basic(self, row_index):
        self.click_configure_vrouter()
        rows = self.get_rows()
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_vrouter_basic

    def click_configure_elements(self, index, element, msg=None, wait=2):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, index)
        self.click_element([element, 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser, wait)
        if msg:
            return self.check_error_msg(msg)
        else:
            return True
    # end click_configure_elements

    def click_configure_svc_appliance_set(self):
        return self.click_configure_elements(0, 'config_infra_sapset',
                                             msg="configure Service Appliance Set")
    # end click_configure_svc_appliance_set

    def click_configure_svc_appliance_set_basic(self, row_index):
        self.click_configure_svc_appliance_set()
        rows = self.get_rows(canvas=True)
        for row in range(len(rows)):
            text = self.find_element('div', 'tag', browser=rows[row], elements=True)[2].text
            if text not in ['opencontrail', 'native']:
                rows[row].find_elements_by_tag_name(
                'div')[0].find_element_by_tag_name('i').click()
                self.wait_till_ajax_done(self.browser)
                return row
    # end click_configure_svc_appliance_set_basic

    def click_configure_svc_appliances(self):
        return self.click_configure_elements(0, 'config_infra_sap',
                                             msg="configure Service Appliance Set")
    # end click_configure_svc_appliances

    def click_configure_alarms_in_project(self):
        return self.click_configure_elements(7, 'config_alarm_project',
                                             msg="Configure Alarms for Project")
    # end click_configure_alarms_in_project

    def click_configure_rbac_in_global(self, option='global'):
        if not self.click_configure_elements(0, 'config_infra_rbac',
                                            msg="Configure RBAC Globally"):
            return False
        else:
            self.click_element("rbac_" + option + "_tab-tab-link")
            self.wait_till_ajax_done(self.browser, wait=3)
            return self.check_error_msg("configure RBAC in " + option)

    # end click_configure_rbac_in_global

    def click_configure_rbac_in_domain(self):
        return self.click_configure_rbac_in_global(option='domain')
    # end click_configure_rbac_in_domain

    def click_configure_rbac_in_project(self):
        return self.click_configure_rbac_in_global(option='project')
    # end click_configure_rbac_in_project

    def click_configure_alarms_in_global(self):
        return self.click_configure_global_config(tab='alarm_rule_global',
                                           msg='alarms')
    # end click_configure_alarms_in_global

    def click_configure_alarms_basic(self, row_index, parent_type):
        if parent_type == 'global':
            element = 'Alarm Rules'
        else:
            element = 'Alarms'
        self.click_element(element, 'link_text')
        self.check_error_msg("configure alarm rules")
        br = self.find_element('config-alarm-grid')
        rows = self.get_rows(browser=br)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_alarms_basic

    def click_configure_alarms_global_basic(self, row_index):
        self.click_configure_alarms_basic(row_index, 'global')
    # end click_configure_alarms_global_basic

    def click_configure_alarms_project_basic(self, row_index):
        self.click_configure_alarms_basic(row_index, 'project')
    # end click_configure_alarms_project_basic

    def click_configure_log_stat_in_global(self):
        return self.click_configure_global_config(parent_tab='global_system',
                                                 tab='user_defined_counter',
                                                 msg='Log Statistic')
    # end click_configure_log_stat_in_global

    def click_configure_flow_aging(self):
        return self.click_configure_global_config(tab='flow_aging',
                                                 msg='Flow aging')
    # end click_configure_flow_aging

    def click_configure_rbac_basic(self, row_index, option='global'):
        self.click_element('RBAC', 'link_text')
        self.check_error_msg("configure rbac " + option)
        self.click_element("rbac_" + option + "_tab-tab-link")
        br = self.find_element('rbac-' + option + '-grid')
        rows = self.get_rows(browser=br)
        rows[row_index].find_elements_by_tag_name(
            'div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    # end click_configure_rbac_basic

    def click_configure_rbac_in_global_basic(self, row_index):
        return self.click_configure_rbac_basic(row_index, option='global')
    # end click_configure_rbac_in_global_basic

    def click_configure_rbac_in_domain_basic(self, row_index):
        return self.click_configure_rbac_basic(row_index, option='domain')
    # end click_configure_rbac_in_domain_basic

    def click_configure_rbac_in_project_basic(self, row_index):
        return self.click_configure_rbac_basic(row_index, option='project')
    # end click_configure_rbac_in_project_basic

    def _click_on_config_dropdown(self, br, index=4):
        # index = 5 if svc_instance or svc_template
        # index = 6 if dns
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
        self._click_on_config_dropdown(self.browser, 5)
        self.click_element(['config_service_templates', 'a'], ['id', 'tag'])
        time.sleep(2)
        return self.check_error_msg("configure service template")
    # end click_configure_service_template
    
    def click_configure_service_health_check(self):
        self._click_on_config_dropdown(self.browser, 5)
        self.click_element(['config_service_healthchk', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure service health check")
    # end click_configure_service_health_check

    def click_configure_service_health_check_basic(self, row_index):
        self.click_configure_service_health_check()
        rows = self.get_rows(canvas=True)
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_service_health_check_basic

    def click_configure_bgp_as_a_service(self):
        self._click_on_config_dropdown(self.browser, 5)
        self.click_element(['config_sc_bgpasaservice', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure bgp as a service")
    # end click_configure_bgp_as_a_service

    def click_configure_bgp_as_a_service_basic(self, row_index):
        self.click_configure_bgp_as_a_service()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_bgp_as_a_service_basic

    def click_configure_physical_router(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 3)
        self.click_element(['config_pd_physicalRouters', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure physical router")
    # end click_configure_physical_router

    def click_configure_physical_router_basic(self, row_index):
        self.click_configure_physical_router()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_physical_router_basic

    def click_configure_interfaces(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 3)
        self.click_element(['config_pd_interfaces', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure physical device's interfaces")
    # end click_configure_interfaces

    def click_configure_interfaces_basic(self, row_index):
        self.click_configure_interfaces()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_interfaces_basic

    def click_configure_forwarding_class(self):
        return self.click_configure_global_config(parent_tab='global_qos',
                                                 tab='fc_global', msg='Fowarding')
    # end click_configure_forwarding_class

    def click_configure_forwarding_class_basic(self, row_index):
        self.click_configure_forwarding_class()
        br = self.find_element('forwarding-class-grid')
        rows = self.get_rows(browser=br)
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_forwarding_class_basic

    def click_configure_forwarding_class_advanced(self, row_index):
        self.click_configure_forwarding_class_basic(row_index)
        self.click_element('fa-code', 'class')
        self.wait_till_ajax_done(self.browser)
    #end click_configure_forwarding_class_advanced

    def click_configure_global_qos(self):
        return self.click_configure_global_config(parent_tab='global_qos',
                                                 tab='qos_global', msg='QOS')
    # end click_configure_global_qos

    def click_configure_global_qos_basic(self, row_index):
        self.click_configure_global_qos()
        br = self.find_element('qos-grid')
        rows = self.get_rows(browser=br)
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_global_qos_basic

    def click_configure_dns_servers(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 6)
        self.click_element(['config_dns_servers', 'a'], ['id', 'tag'])
        time.sleep(2)
        return self.check_error_msg("configure dns servers")
    # end click_configure_dns_servers

    def click_configure_dns_servers_basic(self, row_index):
        self.click_configure_dns_servers()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    # end click_configure_dns_servers_basic

    def click_configure_dns_records(self):
        self.wait_till_ajax_done(self.browser)
        self._click_on_config_dropdown(self.browser, 6)
        self.click_element(['config_dns_records', 'a'], ['id', 'tag'])
        time.sleep(2)
        return self.check_error_msg("configure dns records")
    # end click_configure_dns_records

    def click_configure_dns_records_basic(self, row_index, project):
        self.click_configure_dns_records()
        self.select_dns_server(project)
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    # end click_configure_dns_records_basic

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
        ipam = self.find_element('config_networking_ipam')
        self.click_element(
            ['config_networking_ipam', 'IP Address Management'], ['id', 'link_text'])
        return self.check_error_msg("configure ipam")
    # end click_configure_ipam_in_webui

    def click_configure_qos(self):
        self._click_on_config_dropdown(self.browser)
        self.click_element(['config_net_qos', 'a'], ['id', 'tag'])
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("configure qos")
    # end click_configure_qos

    def click_configure_qos_basic(self, row_index):
        self.click_configure_qos()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_qos_basic

    def click_configure_route_table(self, tab=False,
                                   msg="Network Route Table"):
        if not self.click_configure_elements(4, 'config_net_routing',
                                             msg=msg):
            return False
        if tab:
            element = tab + '-tab-link'
            self.click_element(element)
            self.wait_till_ajax_done(self.browser, wait=3)
        return self.check_error_msg("Configure " + msg)
    # end click_configure_route_table

    def click_configure_route_table_basic(self, row_index):
        self.click_configure_route_table()
        rows = self.get_rows()
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_route_table_basic

    def click_configure_routing_policy(self):
        return self.click_configure_route_table(tab='routing_policy_tab',
                                                msg='Routing Policy')
    # end click_configure_routing_policy

    def click_configure_routing_policy_basic(self, row_index):
        self.click_configure_routing_policy()
        br = self.find_element('routing_policy_tab')
        rows = self.get_rows(browser=br)
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_routing_policy_basic

    def click_configure_route_aggregate(self):
        return self.click_configure_route_table(tab='route_aggregates_tab',
                                         msg='Route Aggregate')
    # end click_configure_route_aggregate

    def click_configure_route_aggregate_basic(self, row_index):
        self.click_configure_route_aggregate()
        br = self.find_element('route-aggregate-grid')
        rows = self.get_rows(browser=br)
        div_browser = self.find_element(
            'div', 'tag', if_elements=[1], elements=True,
            browser=rows[row_index])[0]
        self.click_element('i', 'tag', browser = div_browser)
        self.wait_till_ajax_done(self.browser)
    #end click_configure_route_aggregate_basic

    def click_configure_intf_route_table(self):
        return self.click_configure_route_table(tab='interface_route_table',
                                           msg='Interface Route Table')
    # end click_configure_intf_route_table

    def click_fip_vn(self, browser=None):
        if not browser:
            browser = self.browser
        try:
            self.click_element('fa-cog', 'class', browser)
            self.click_element(['tooltip-success', 'i'], ['class', 'tag'])
            fip_element = self.find_element('fip_pool_accordian')
            self.browser.execute_script("return arguments[0].scrollIntoView();", fip_element)
            fip_element.click()
        except WebDriverException:
            self.logger.error("Click on Floating IP Pool(s) under VN failed")
            self.screenshot('Click_on_fip_vn_failed')
    # end click_fip_vn

    def click_instances(self, br=None):
        if not br:
            br = self.browser
        try:
            br.find_element_by_link_text('Instances').click()
        except WebDriverException:
            try:
                self.click_element(
                    ['nav_accordion', 'dt'], ['class', 'tag'], br, [1], index=0)
                self.click_element('Instances', 'link_text', br)
            except WebDriverException:
                self.logger.error("Click on Instances failed")
                self.screenshot('Click_on_instances_failure', br)
    # end click_instances

    def select_project_in_openstack(
            self,
            project_name='admin',
            browser=None,
            os_release='havana'):
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
            elif os_release == 'icehouse':
                ui_proj = self.find_element(
                    ['tenant_switcher', 'h3'], ['id', 'css'], browser).get_attribute('innerHTML')
                if ui_proj != project_name:
                    self.click_element(
                        ['tenant_switcher', 'a'], ['id', 'tag'], browser, jquery=False, wait=3)
                    tenants = self.find_element(
                        ['tenant_list', 'a'], ['id', 'tag'], browser, [1])
                    self.click_if_element_found(tenants, project_name)
            else:
                if os_release in ('liberty', 'mitaka', 'newton', 'ocata'):
                    self.click_element(
                        'fa-caret-down', 'class', browser)
                else:
                    self.click_element(
                        ['button', 'caret'], ['tag', 'class'], browser)
                prj_obj = self.find_element(
                    ['dropdown-menu', 'a'], ['class', 'tag'], browser, [1])
                for element in prj_obj:
                    if element.text == project_name:
                        element.click()
                        break
            if os_release != 'havana':
                try:
                    self.click_element('dt', 'tag', browser, jquery=False, wait=4)
                except:
                    self.click_element(
                        'openstack-dashboard', 'class',
                        browser, jquery=False, wait=4)
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
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className == 'value string' || eleList[i + 1].className == 'value number' ){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
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
        minute_range = list(range(int(time_string.split(
        )[-1][:-1]) - offset, int(time_string.split()[-1][:-1]) + offset + 1))
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
            "var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'value string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length && eleList[j].className == 'value string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
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
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i+3].className == 'value'){if(eleList[i + 8].className == 'key' && eleList[i + 9].className == 'value number'){dataSet.push({key : eleList[i + 8].innerHTML, value : eleList[i + 9].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_num

    def get_advanced_view_bool(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i+3].className == 'value'){if(eleList[i + 16].className == 'key' && eleList[i + 17].className == 'value boolean'){dataSet.push({key : eleList[i + 16].innerHTML, value : eleList[i + 17].innerHTML});}}} return JSON.stringify(dataSet);"))
        if not domArry:
            domArry = json.loads(self.browser.execute_script(
                "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i+3].className == 'value'){if(eleList[i + 8].className == 'key' && eleList[i + 9].className == 'value boolean'){dataSet.push({key : eleList[i + 8].innerHTML, value : eleList[i + 9].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_bool

    def get_advanced_view_obj(self):
        domArry = json.loads(self.browser.execute_script(
            "var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i+3].className == 'value'){if(eleList[i + 10].className == 'key' && eleList[i + 11].className == 'value object'){dataSet.push({key : eleList[i + 10].innerHTML, value : eleList[i + 11].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    # end get_advanced_view_obj

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
            "var eleList = $('div.col-xs-12').find('div.row').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].classList.contains('key') && eleList[i + 1].classList.contains('value')){dataSet.push({key : eleList[i].innerHTML.replace(/(&nbsp;)*/g&&/^\s+|\s+$/g,''),value:eleList[i+1].innerHTML.replace(/\s+/g, ' ')});}} return JSON.stringify(dataSet);"))
        return domArry
    # end get_basic_view_infra

    def get_advanced_view_list(self, name, key_val, index=3, parent=False, parent_click=False):
        key_val_lst1 = self.find_element('pre', 'tag')
        key_val_lst2 = self.find_element(
            'key-value', 'class', elements=True, browser=key_val_lst1)
        key1=val1=flag=None
        for element in key_val_lst2:
            if element.text.startswith(name):
                keys_arry = self.find_element(
                    'key', 'class', elements=True, browser=element)
                # Find and click are separated here to avoid timeout issues and capture screenshot in case find fails
                parent_elements = []
                if parent:
                    parent_elements = self.find_element('fa-plus', 'class', elements=True,
                                           browser=element)
                    for parent_element in parent_elements:
                        if len(parent_elements) > 1:
                            parent_element.click()
                            plus_element = self.find_element('fa-plus', 'class', elements=True, browser=parent_element)[0]
                            self.screenshot('agent')
                            plus_element.click()
                        else:
                            parent_elements[0].click()
                elif not parent_click:
                    plus_element = self.find_element('fa-plus', 'class', elements=True, browser=element)[index]
                keys_arry = self.find_element(
                            'key', 'class', elements=True, browser=element)
                vals_arry = self.find_element(
                            'value', 'class', elements=True, browser=element)
                for ind, ele in enumerate(keys_arry):
                    if key_val == ele.text:
                        key1 = key_val
                        if parent and not parent_click:
                            try:
                                self.click_element('fa-plus', 'class', browser=vals_arry[ind + 1])
                            except:
                                pass
                            val1 = [str(vals_arry[ind + 1].text)]
                        elif parent_click:
                            vals_arry[ind + 2].click()
                            val1 = str(vals_arry[ind + 2].text)

                        else:
                            val1 = [str(vals_arry[ind].text.strip('[ \n]'))][0].split('\n')
                        flag = 1
                        break
                break
        return key1, val1, flag
    # end get_advanced_view_list

    def click_basic_and_get_row_details(
            self,
            func_suffix,
            index=0,
            view='basic',
            canvas=False,
            search_ele=None,
            search_by='id',
            browser=None,
            project=None,
            click_tab='configure'):
        if not browser:
            browser = self.browser
        click_func = 'self.click_' + click_tab + '_' + func_suffix + '_' + view
        row_index = None
        if project:
            eval(click_func)(index, project)
        else:
            row_index = eval(click_func)(index)
        self.logger.info(
            "Click and retrieve %s view details in webui of %s " %
                (view, func_suffix))
        try:
            if 'WebDriver' in str(type(browser)):
                pass
            else:
                self.logger.debug('browser is %s' % (browser.text))
        except StaleElementReferenceException:
            browser = self.find_element(search_ele, search_by)
        rows = self.get_rows(browser, canvas)
        if row_index:
            ind = row_index + 1
        else:
            if not rows[index + 1].text:
                ind = index
            else:
                ind = index + 1
        self.wait_till_ajax_done(browser)
        slick_row_detail = self.find_element(
                'slick-row-detail-container', 'class',
                        browser = rows[ind])
        if view == 'advanced':
            rows_detail = self.find_element(
                              ['pre', 'key-value'], ['tag', 'class'],
                              browser = slick_row_detail, if_elements=[1])
        else:
            item_list = self.find_element('item-list', 'class', browser=slick_row_detail,
                                         elements=True)
            rows_detail = []
            for item in item_list:
                rows_detail.extend(self.find_element('row', 'class', browser=item,
                                  elements=True))
        return rows, rows_detail
    # end click_basic_and_get_row_details

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
        for key, value in list(dict_in.items()):
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

    def append_to_string(self, append_to, append_with, separator=','):
        if not append_to:
            append_to = append_with
        else:
            append_to = append_to + separator + ' ' + append_with
        return append_to

    def list_in_dict(self, dict_ele):
        list_ele = []
        if isinstance(dict_ele, int) or float:
            dict_ele = str(dict_ele)
        if ',' in dict_ele:
            return True

    def match_ui_values(self, complete_ops_data, webui_list):
        error = 0
        match_count = 0
        count = 0
        for ops_items in complete_ops_data:
            match_flag = 0
            for webui_items in webui_list:
                if ops_items['value'] == webui_items['value'] or (
                        ops_items['value'] == 'True' and ops_items['key'] == 'active' and webui_items['value'] == 'Active') or (
                        ops_items['key'] == webui_items['key'] and webui_items['value'] in ops_items['value']):
                    self.logger.info(
                        "Ops key %s ops_value %s matched with %s" %
                        (ops_items['key'], ops_items['value'], webui_items))
                    match_flag = 1
                    match_count += 1
                    break
                elif self.list_in_dict(ops_items['value']) and self.list_in_dict(webui_items['value']) and (ops_items['key'] == webui_items['key']):
                    list_ops = ops_items['value'].split(', ')
                    list_webui = webui_items['value'].split(', ')
                    for list_webui_index in range(len(list_webui)):
                        for list_ops_index in range(len(list_ops)):
                            if (list_webui[
                                    list_webui_index] == list_ops[list_ops_index]):
                                count += 1
                                break
                            elif isinstance(list_webui[list_webui_index], (str, str)) and list_webui[list_webui_index].strip() == list_ops[list_ops_index]:
                                count += 1
                                break
                    if(count == len(list_ops) or count == len(list_webui)):
                        self.logger.info(
                            "Ops key %s.0 : value %s matched" %
                            (ops_items['key'], list_ops))
                        match_flag = 1
                        match_count += 1
                        break
                    else:
                        match_count = len(set(list_ops) & set(list_webui))
                        self.logger.error(
                            "Ops and webui values dint match completely. Expected match: %s but matched: %s" %
                            (len(list_ops), match_count))
                        error = 1
                        break
            if not match_flag:
                self.logger.error(
                    "Ops key %s ops_value %s not found/matched with %s" %
                    (ops_items['key'], ops_items['value'], webui_items))
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

    def match_ui_kv(self, complete_ops_data, merged_arry, data='Ops/API', matched_with='WebUI'):
        self.logger.info("%s data to be matched : %s"% (data, complete_ops_data))
        self.logger.info("%s data to be matched : %s"%  (matched_with, merged_arry))
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
            'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b11',
            'used',
            'free',
            'b200000',
            'fifteen_min_avg',
            'peakvirt',
            'virt',
            'ds_interface_drop',
            'COUNT(cpu_info)',
            'COUNT(vn_stats)',
            'SUM(cpu_info.cpu_share)',
            'SUM(cpu_info.mem_virt)',
            'SUM(cpu_info.mem_res)',
            'MAX(cpu_info.mem_virt)',
            'MAX(cpu_info.mem_res)',
            'SUM(cpu_info.mem_res)',
            'MAX(cpu_info.mem_res)',
            'mem_res',
            'table',
            'ds_discard',
            'discards',
            'ds_flow_action_drop',
            'ds_flood',
            'ds_mcast_df_bit',
            'ds_flow_no_memory',
            'ds_push',
            'ds_invalid_if',
            'ds_pull',
            'ds_no_fmd',
            'ds_invalid_arp',
            'ds_trap_no_if',
            'ds_vlan_fwd_tx',
            'ds_invalid_mcast_source',
            'ds_invalid_source',
            'ds_flow_action_invalid',
            'ds_invalid_packet',
            'ds_flow_invalid_protocol',
            'ds_invalid_vnid',
            'ds_flow_table_full',
            'ds_invalid_label',
            'ds_garp_from_vm',
            'ds_frag_err',
            'ds_vlan_fwd_enq',
            'ds_clone_fail',
            'ds_arp_no_route',
            'ds_misc',
            'ds_interface_rx_discard',
            'ds_flow_unusable',
            'ds_mcast_clone_fail',
            'ds_invalid_protocol',
            'ds_head_space_reserve_fail',
            'ds_interface_tx_discard',
            'ds_nowhere_to_go',
            'ds_arp_no_where_to_go',
            'ds_l2_no_route',
            'ds_cksum_err',
            'ds_flow_queue_limit_exceeded',
            'ds_ttl_exceeded',
            'ds_flow_nat_no_rflow',
            'ds_invalid_nh',
            'ds_head_alloc_fail',
            'ds_pcow_fail',
            'ds_rewrite_fail',
            'primary',
            'no_config_intf_list',
            'total_flows',
            'active_flows',
            'aged_flows',
            'ds_duplicated',
            'udp_sport_bitmap',
            'tcp_sport_bitmap',
            'udp_dport_bitmap',
            'tcp_dport_bitmap',
            'rss',
            'ds_cloned_original',
            'l2_mcast_composites',
            'exception_packets_dropped'
            'b1485172',
            'rows',
            'chunk_where_time',
            'chunk_merge_time',
            'chunk_postproc_time',
            'qid',
            'final_merge_time',
            'time_span',
            'time',
            'chunks',
            'post',
            'where',
            'select',
            'disk_used_bytes',
            'mem_virt',
            'average_blocked_duration',
            'admin_down',
            'sm_back_pressure',
            'log_local',
            'log_category',
            'error_intf_list',
            'max_sm_queue_count',
            'status',
            'control_node_list_cfg',
            'dns_servers',
            'cached',
            'total',
            'reconnects',
            'in_msgs',
            'out_msgs',
            'p1p1',
            'stddev',
            'mean',
            'sigma',
            'mirror_acl',
            'edge_replication_forwards',
            'source_replication_forwards',
            'total_multicast_forwards',
            'local_vm_l3_forwards',
            'rule',
            'count',
            'l2_receives',
            'samples',
            'inst_id',
            'chunk_select_time',
            'last_event_at',
            'last_state_at',
            'proxies',
            'inBytes60',
            'outBytes60',
            'x',
            'y']
        key_list = ['exception_packets_dropped', 'l2_mcast_composites']
        index_list = []
        random_keys = ['{"ts":', '2015 ', '2016 ']
        for element in complete_ops_data[:]:
            [complete_ops_data.remove(
                element) for item in random_keys if element['key'].find(item) != -1]
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
                try:
                    if item_ops_key in key_list:
                        item_webui_int_value = int(item_webui_value)
                        if item_ops_key == item_webui_key and (
                            item_webui_int_value is not None or
                            item_webui_int_value == 0):
                            item_ops_value = self.get_range_string(
                                item_ops_value)
                except:
                    item_webui_int_value = None
                check_type_of_item_webui_value = not isinstance(
                    item_webui_value,
                    list)
                if (item_ops_key == item_webui_key and (item_ops_value == item_webui_value or (
                        item_ops_value == 'None' and item_webui_value == 'null') or (item_ops_value == 'None Total' and item_webui_value == '0 Total'))):
                    self.logger.info(
                        "%s key %s : value %s matched" %
                        (data, item_ops_key, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif (item_ops_key == item_webui_key and item_ops_value == 'True' and item_webui_value == 'true' or item_ops_value == 'False'
                      and item_webui_value == 'false' or item_ops_key == 'build_info'):
                    if item_ops_key == 'build_info':
                        self.logger.info(
                            "Skipping : %s key %s : value %s skipping match" %
                            (data, item_ops_key, item_ops_value))
                        skipped_count = +1
                    else:
                        self.logger.info(
                            "%s key %s : value %s matched" %
                            (data, item_ops_key, item_ops_value))
                        match_count += 1
                    matched_flag = 1
                    break

                elif (check_type_of_item_webui_value and item_ops_key == item_webui_key and item_ops_value == (item_webui_value + '.0')):
                    self.logger.info(
                        "%s key %s.0 : value %s matched" %
                        (data, item_ops_key, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and not isinstance(item_webui_value, list) and isinstance(item_ops_value, list) and (item_webui_value in item_ops_value):
                    self.logger.info(
                        "%s key %s : value : %s matched in %s value range list %s " %
                        (matched_with, item_webui_key, item_webui_value, data, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and not isinstance(item_ops_value, list) and isinstance(item_webui_value, list) and (item_ops_value in item_webui_value):
                    self.logger.info(
                        "%s key %s : value %s matched in %s value range list %s " %
                        (data, item_ops_key, item_ops_value, matched_with, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and isinstance(item_webui_value, list) and isinstance(item_ops_value, list):
                    count = 0
                    for item_webui_index in range(len(item_webui_value)):
                        for item_ops_index in range(len(item_ops_value)):
                            if (item_webui_value[
                                    item_webui_index] == item_ops_value[item_ops_index]):
                                count += 1
                                break
                            elif isinstance(item_webui_value[item_webui_index], (str, str)) and item_webui_value[item_webui_index].strip() == item_ops_value[item_ops_index]:
                                count += 1
                                break
                    if(count == len(item_webui_value)):
                        self.logger.info(
                            "%s key %s.0 : value %s matched" %
                            (data, item_ops_key, item_ops_value))
                        matched_flag = 1
                        match_count += 1
                    break
                elif item_ops_key == item_webui_key:
                    webui_match_try_list.append(
                        {'key': item_webui_key, 'value': item_webui_value})
                    key_found_flag = 1
            if not matched_flag:
                # self.logger.error("ops key %s : value %s not matched with
                # webui data"%(item_ops_key, item_ops_value))
                if key_found_flag:
                    self.logger.error(
                        "%s key %s : value %s not matched key-value pairs list %s" %
                        (data, item_ops_key, item_ops_value, webui_match_try_list))
                    self.screenshot('ERROR_MISMATCH_' + item_ops_key)
                else:
                    self.logger.error(
                        "%s key %s : value %s not found, webui key %s webui value %s " %
                        (data, item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    self.screenshot('ERROR_NOT_FOUND_' + item_ops_key)
                not_matched_count += 1
                for k in range(len(merged_arry)):
                    if item_ops_key == merged_arry[k]['key']:
                        webui_key = merged_arry[k]['key']
                        webui_value = merged_arry[k]['value']
                no_error_flag = False
        self.logger.info("Total %s key-value count is %s" %
                         (data, str(len(complete_ops_data))))
        self.logger.info(
            "Total %s key-value matched count is %s" %
            (data, str(match_count)))
        self.logger.info("Total %s key-value not matched count is %s" %
                         (data, str(not_matched_count)))
        self.logger.info("Total %s key-value match skipped count is %s" %
                         (data, str(skipped_count)))
        if not_matched_count <= 3:
            no_error_flag = True
            if not_matched_count > 0:
                self.logger.debug(
                    "Check the %s mismatched key-value pair(s)" %
                        str(not_matched_count))
        return no_error_flag
    # end match_ui_kv

    def get_range_string(self, value, offset=50):
        try:
            if int(value) or int(value) == 0:
                val_range = list(range(int(value) - offset, int(value) + offset))
                val_range_list = [str(val) for val in val_range]
                return val_range_list
        except:
            return None
    # end get_range_string

    def type_change(self, my_list):
        ''' This method changes the elements of a list from unicode to string '''
        for t in range(len(my_list)):
            if isinstance(my_list[t]['value'], list):
                for m in range(len(my_list[t]['value'])):
                    my_list[t]['value'][m] = str(
                        my_list[t]['value'][m])
            elif isinstance(my_list[t]['value'], str):
                my_list[t]['value'] = str(
                    my_list[t]['value'])
            else:
                my_list[t]['value'] = str(
                    my_list[t]['value'])
    # end type_change

    def get_slick_cell_text(self, br=None, index=1):
        try:
            obj_text = self.find_element(
                ('slick-cell',
                 index),
                'class',
                browser=br,
                elements=True).text
        except WebDriverException:
            time.sleep(15)
            self.screenshot('not able to get slick cell')
            obj_text = self.find_element(
                ('slick-cell',
                 index),
                'class',
                browser=br,
                elements=True).text
        return obj_text
    # end get_slick_cell_text

    def click_on_cancel_if_failure(self, element_id='cancelBtn'):
        try:
            self.click_element(element_id, screenshot=False)
            # Trying a second time since 'cancel' needs to be clicked
            # twice at times to set the cursor on the dialog box
            if self.find_element(element_id):
                self.click_element(element_id, screenshot=False)
        except:
            pass
    # end click_on_cancel_if_failure

    def get_item_list(self, ui_list):
        item_list = self.find_element('item-list', 'class', elements=True)
        for index in range(len(item_list)):
            intf_dict = {}
            label = self.find_element(
                'row',
                'class',
                browser=item_list[index],
                elements=True)
            for lbl in label:
                key = self.find_element('key', 'class', browser=lbl)
                value = self.find_element('value', 'class', browser=lbl)
                if value.text == '':
                    continue
                ui_list.append(value.text)
        return ui_list
    # end get_item_list

    def expand_advance_details(self, count=40):
        flag = 0
        while flag < count:
            plus_objs = []
            try:
                plus_objs = self.find_element(
                    "i[class*='fa-plus expander']",'css', elements=True,screenshot=False)
                flag += 1
                self.browser.execute_script(
                    "return arguments[0].scrollIntoView();", plus_objs)
                self.click(plus_objs)
                time.sleep(3)
            except (WebDriverException, TimeoutException):
                break
    # end expand_advance_details

    def get_value_of_key(self, rows_detail, exp_key, view='basic'):
        """
            Returns the value of a specific key when a list of row details is passed
            PARAMETERS :
                rows_detail : Details of a row on expansion; in list of dicts format
                exp_key : Expected key whose value needs to be returned
        """
        value1 = ''
        flag = True
        for item in rows_detail:
            if view == 'advanced':
                if ':'  in item.text:
                    flag = True
                else:
                    flag = False
            if flag:
                key1 = self.find_element('key', 'class', browser=item).text
                if key1 == exp_key:
                    value1 = self.find_element('value', 'class', browser=item).text
                    break
        return value1
    # end get_value_of_key
    
    def get_api_detail(self, uuid, option):
        self.vn_api_url = option + uuid
        return self._get_list_api(self.vn_api_url)
    # end get_api_detail

    def get_vn_detail_ops(self, domain, project_vn, vn_name):
        self.vn_ops_url = 'virtual-network/' + domain + project_vn + ":" + \
                           vn_name + "?flat"
        return self._get_list_ops(self.vn_ops_url)
    # end get_vn_detail_ops

    def click_icon_cog(self, index, browser, option, type):
        self.click_element('fa-cog', 'class', index)
        self.wait_till_ajax_done(index)
        tool_tip_option = "//a[contains(@class,'tooltip-success')]"
        tool_tip = self.find_element(tool_tip_option, 'xpath', index, elements=True)
        if option == 'edit':
            tool_tip[0].click()
        else:
            if type == 'Networks':
                click_element = type.lower().strip('s')
            else:
                click_element = type
            if type =='Ports':
                if option == 'subinterface':
                    tool_tip[1].click()
                else:
                    tool_tip[2].click()
            else:
                tool_tip[1].click()
            self.wait_till_ajax_done(self.browser, wait=3)
            self.click_element('configure-' + click_element + 'btn1', browser=browser)
        self.wait_till_ajax_done(self.browser, wait=3)
    # end click_icon_cog

    def get_vn_detail_ui(self, search_key, index=0, vn_name=None):
        option  =  'Networks'
        if not self.click_configure_networks():
            self.dis_name = None
        self.select_project(self.inputs.project_name)
        self.wait_till_ajax_done(self.browser)
        if not index:
            rows = self.get_rows(canvas=True)
            if vn_name:
                for row in rows:
                    out = re.search(vn_name, str(row.text))
                    index += 1
                    if out:
                        break
            else:
                index = len(rows)
        toggle_icon = "//i[contains(@class,'toggleDetailIcon')]"
        edit = self.find_element(toggle_icon, 'xpath', elements=True)
        edit[index-1].click()
        self.wait_till_ajax_done(self.browser)
        item = self.find_element('slick-row-detail-container', 'class')
        out_split = re.split("\n",item.text)
        join_res = "-".join(out_split)
        if search_key == 'Display Name':
            regexp = "Display Name\-(.*)\-UUID"
            flag = True
        elif search_key == 'UUID':
            regexp = "UUID\-(.*)\-Admin"
            flag = True
        elif search_key == 'Policy':
            regexp = "Policies\-(.*)\-Forwarding Mode"
            flag = True
        elif search_key == 'Subnet':
            regexp = "Subnet(.*)Name"
            flag = True
        elif search_key == 'Host Route':
            regexp = "Host Route\(s\)(.*)DNS"
            flag = True
        elif search_key == 'Adv Option':
            regexp = "Shared.*Floating"
            flag = False
        elif search_key == 'DNS':
            regexp = "DNS Server\(s\)(.*)Ecmp"
            flag = False
        elif search_key == 'FIP':
            regexp = "Floating IP Pool\(s\)(.*)Route"
            flag = False
        elif search_key == 'RT':
            regexp = "Route Target\(s\)(.*)Export"
            flag = False
        elif search_key == 'ERT':
            regexp = "Export Route Target\(s\)(.*)Import"
            flag = False
        elif search_key == 'IRT':
            regexp = "Import Route Target\(s\)(.*)"
            flag = False
        out = re.search(regexp,join_res)
        if flag:
            result = out.group(1)
        else:
            result = out.group(0)
        return result
    # get_vn_detail_ui

    def edit_remove_option(self, option, category, display_name=None):
        try:
            self.logger.info("Go to Configure->Networking->%s page" %(option))
            click_option = 'self.click_configure_' + option.lower()
            if not eval(click_option)():
                result = result and False
            self.select_project(self.inputs.project_name)
            rows = self.get_rows(canvas=True)
            if rows:
                self.logger.info("%s are available to edit. Editing the %s" % (option,option))
                if display_name:
                    for index, row in enumerate(rows, start=1):
                        if re.search(display_name, str(row.text)):
                            break
                else:
                    index = len(rows)
                if len(rows):
                    self.wait_till_ajax_done(self.browser)
                    self.click_icon_cog(rows[index-1], self.browser, category, option)
            else:
                self.logger.error("No %s are available to edit" % (option))
                self.screenshot(option)
            self.wait_till_ajax_done(self.browser)
            result = index

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_remove_option

    def edit_without_change(self, option, display_name=None):
        result = True
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit', display_name)
            if self.edit_vn_result:
                try:
                    self.logger.info("Click on save button")
                    self.click_on_create(option.strip('s'),
                                        option.strip('s').lower(), save=True)
                except WebDriverException:
                    self.logger.error("Error while trying to save %s" %(option))
                    result = result and False
                    self.screenshot(option)
                    self.click_on_cancel_if_failure('cancelBtn')
                    raise
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_without_change

    def edit_vn_disp_name_change(self, vn_name):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                self.click_element('display_name')
                self.send_keys(vn_name, 'display_name', 'name', clear=True)
                self.click_element('configure-networkbtn1')
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_disp_name_change

    def add_vn_with_policy(self,pol_name):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                self.click_element('s2id_network_policy_refs_dropdown')
                select_highlight = "//li[contains(@class,'select2-highlighted')]"
                select = self.find_element(select_highlight, 'xpath')
                pol_name = select.text
                select.click()
                self.click_element('configure-networkbtn1')
                return pol_name
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # add_vn_with_policy

    def del_vn_with_policy(self,pol_name):
        result = True
        option = "Networks"
        try:
            policy_ui = str(self.get_vn_detail_ui('Policy'))
            policy = pol_name.split(":")
            out = re.search(policy[-1],policy_ui)
            if out:
                index = 1
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                del_row = self.find_element('s2id_network_policy_refs_dropdown')
                count = 0
                if index > 0:
                    close_option = "//a[contains(@class,'select2-search-choice-close')]"
                    for element in self.find_element(close_option, 'xpath', elements=True):
                        count = count + 1
                        if count == index:
                            element.click()
                            self.logger.info("Policy got removed successfully")
                            self.click_element('configure-networkbtn1')
                            self.wait_till_ajax_done(self.browser)
                else:
                    self.logger.warn("There is no policy to edit")
            else:
                self.logger.error("Clicking the edit button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # del_vn_with_policy

    def edit_vn_with_subnet(self, category, subnet, dfrange, dfgate, vn):
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit', display_name=vn)
            if self.edit_vn_result:
                self.wait_till_ajax_done(self.browser)
                self.click_element('subnets')
                self.wait_till_ajax_done(self.browser)
                self.click_element('fa-plus', 'class')
                self.send_keys(subnet, 'user_created_cidr', 'name', clear=True)
                self.send_keys(dfrange, 'allocation_pools', 'name', clear=True)
                self.wait_till_ajax_done(self.browser)
                if category == 'Subnet':
                    self.send_keys(dfgate, 'default_gateway', 'name', clear=True)
                elif category == 'Subnet-gate':
                    self.click_element('user_created_enable_gateway', 'name')
                elif category == 'Subnet-dns':
                    self.click_element('user_created_enable_dns', 'name')
                elif category == 'Subnet-dhcp':
                    self.click_element('enable_dhcp', 'name')
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser)
                result = self.edit_vn_result
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = False
        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_subnet

    def del_vn_with_subnet(self, vn):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit', display_name=vn)
            if self.edit_vn_result:
                self.click_element('subnets')
                self.wait_till_ajax_done(self.browser)
                data_row = "//tr[contains(@class,'data-row')]"
                data = self.find_element(data_row, 'xpath', elements=True)
                ind = 0
                act_cell = self.find_element('action-cell', 'class')
                minus_icon = "//i[contains(@class,'fa-minus')]"
                self.click_element(minus_icon, 'xpath', elements=True, index=ind)
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # del_vn_with_subnet

    def edit_vn_with_host_route(self, button, tc, hprefix, hnexthop):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                self.click_element('host_routes')
                self.wait_till_ajax_done(self.browser)
                if button == 'add':
                    edit_grid = "//a[contains(@class,'editable-grid-add-link')]"
                    add_link = self.find_element(edit_grid, 'xpath', elements=True)
                    add_link[1].click()
                    prefix = "//input[contains(@name,'prefix')]"
                    self.send_keys(hprefix, prefix, 'xpath')
                    next_hop = "//input[contains(@name,'next_hop')]"
                    self.send_keys(hnexthop, next_hop, 'xpath')
                else:
                    minus_icon = "//i[contains(@class,'fa-minus')]"
                    minus = self.find_element(minus_icon, 'xpath', elements=True)
                    index = len(minus)
                    minus[index-3].click()
                    self.wait_till_ajax_done(self.browser)
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser)
                if tc == 'neg':
                    warn_button_host_route = "//span[contains(@data-bind,'hostRoutes')]"
                    warn_button = self.find_element(warn_button_host_route, 'xpath')
                    if warn_button.get_attribute('style') == "":
                        self.click_on_cancel_if_failure('cancelBtn')
                        self.wait_till_ajax_done(self.browser)
                        return result
                    else:
                        result = result and False
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_host_route

    def edit_vn_with_adv_option(self, category, tc, var_list):
        option = "Networks"
        try:
            self.wait_till_ajax_done(self.browser)
            if not self.click_configure_networks():
                result = False
            if category == 1:
                toolbar_xpath = "//a[@class='widget-toolbar-icon' and @title='Create Network']"
                self.click_element(toolbar_xpath, 'xpath')
                self.send_keys(var_list[3], 'display_name', 'name')
                self.click_element('subnets')
                self.wait_till_ajax_done(self.browser, wait=3)
                self.click_element("fa-plus", 'class')
                self.wait_till_ajax_done(self.browser, wait=3)
                self.send_keys(var_list[2], 'user_created_cidr', 'name')
                self.click_element("configure-networkbtn1")
            self.edit_vn_result = self.edit_remove_option(option, 'edit',display_name=var_list[3])
            if self.edit_vn_result:
                self.click_element('advanced_options')
                self.wait_till_ajax_done(self.browser, wait=3)
                is_shared = self.find_element('is_shared', 'name')
                self.browser.execute_script(
                        "return arguments[0].scrollIntoView();", is_shared)
                is_shared.click()
                self.click_element('router_external', 'name')
                self.click_element('allow_transit', 'name')
                self.click_element('flood_unknown_unicast', 'name')
                self.click_element('multi_policy_service_chains_enabled', 'name')
                self.click_element('s2id_ecmp_hashing_include_fields_dropdown')
                self.click_element('select2-highlighted', 'class')
                if tc == 'pos-phy':
                    self.click_element('user_created_sriov_enabled', 'name')
                    self.send_keys(var_list[1], 'physical_network', 'name')
                    self.send_keys(var_list[0], 'segmentation_id', 'name')
                else:
                    self.send_keys(var_list[1], 'physical_network', 'name', clear=True)
                    self.send_keys(var_list[0], 'segmentation_id', 'name', clear=True)
                self.click_element('configure-networkbtn1')
                result = self.edit_vn_result
                if tc == 'neg-phy':
                    warn_advance = "//span[contains(@data-bind,'advanced')]"
                    warn_button = self.find_element(warn_advance, 'xpath')
                    if warn_button.get_attribute('style') == "":
                        self.click_on_cancel_if_failure('cancelBtn')
                        self.wait_till_ajax_done(self.browser)
                        result = self.edit_vn_result
                    else:
                        result = False
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_adv_option

    def edit_vn_with_dns(self, button, tc, dns_ip):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                self.click_element('dns_servers')
                self.wait_till_ajax_done(self.browser, wait=3)
                if button == 'add':
                    add_link = self.find_element('editable-grid-add-link', 'class', elements=True)
                    add_link[2].click()
                    text = self.find_element('ip_address', 'name')
                    text.send_keys(dns_ip)
                else:
                    minus_icon = "//i[contains(@class,'fa-minus')]"
                    minus = self.find_element(minus_icon, 'xpath', elements=True)
                    index = len(minus)
                    minus[index-3].click()
                self.wait_till_ajax_done(self.browser)
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser)
                if tc == 'neg':
                    dns_server = "//span[contains(@data-bind,'dnsServers')]"
                    warn_button = self.find_element(dns_server, 'xpath')
                    if warn_button.get_attribute('style') == "":
                        self.click_on_cancel_if_failure('cancelBtn')
                        self.wait_till_ajax_done(self.browser)
                        return result
                    else:
                        result = result and False
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_dns

    def edit_vn_with_fpool(self, button, fpool):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            if self.edit_vn_result:
                self.click_element('fip_pool_accordian')
                self.wait_till_ajax_done(self.browser)
                if button == 'add':
                    add_link = self.find_element('editable-grid-add-link', 'class', \
                                                 elements=True)
                    self.browser.execute_script(
                        "return arguments[0].scrollIntoView();", add_link[3])
                    add_link[3].click()
                    self.wait_till_ajax_done(self.browser)
                    self.send_keys(fpool, 'name', 'name')
                    self.wait_till_ajax_done(self.browser)
                    self.click_element('s2id_projects_dropdown')
                    select = self.find_element('select2-highlighted', 'class')
                    self.project = select.text
                    select.click()
                else:
                    minus = self.find_element('fa-minus', 'class', elements=True)
                    index = len(minus)
                    minus[index-3].click()
                self.wait_till_ajax_done(self.browser)
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser)
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_fpool

    def edit_vn_with_route_target(self, button, tc, rt_type, asn_no_ip, target_no, count=0):
        result = True
        option = "Networks"
        try:
            self.edit_vn_result = self.edit_remove_option(option, 'edit')
            self.wait_till_ajax_done(self.browser, wait=10)
            if self.edit_vn_result:
                if rt_type == 'RT':
                    self.click_element('route_target_accordian')
                    ind = 4
                elif rt_type == 'ERT':
                    self.click_element('export_route_target_accordian')
                    ind = 5
                elif rt_type == 'IRT':
                    if button == 'add':
                        self.wait_till_ajax_done(self.browser, wait=10)
                        route = self.find_element('import_route_target_accordian')
                        self.browser.execute_script(
                            "return arguments[0].scrollIntoView();", route)
                        route.click()
                        ind = 6
                        self.wait_till_ajax_done(self.browser)
                        if count == 1:
                            route.click()
                        self.wait_till_ajax_done(self.browser)
                if button == 'add':
                    add_link = self.find_element('editable-grid-add-link', 'class', \
                                                 elements=True)
                    self.browser.execute_script(
                        "return arguments[0].scrollIntoView();", add_link[ind])
                    add_link[ind].click()
                    self.wait_till_ajax_done(self.browser)
                    self.send_keys(asn_no_ip, 'asn', 'name')
                    self.send_keys(target_no, 'target', 'name')
                else:
                    if rt_type == 'IRT':
                        self.click_element('import_route_target_accordian')
                        self.wait_till_ajax_done(self.browser)
                        imp_route_target_vcfg = "//div[contains(@id,'import_route_target_vcfg')]"
                        irt = self.find_element(imp_route_target_vcfg, 'xpath', elements=True)
                        imp_route_target = self.find_element('user_created_import_route_targets', \
                                                     elements=True)
                    minus = self.find_element('fa-minus', 'class', elements=True)
                    index = len(minus) - 3 
                    minus[index].click()
                self.wait_till_ajax_done(self.browser)
                self.click_element('configure-networkbtn1')
                self.wait_till_ajax_done(self.browser, wait=10)
                if tc == 'neg':
                    if rt_type == 'RT':
                        warn_button_rt = "//span[contains(@data-bind,'route_target_vcfg')]"
                        warn_button = self.find_element(warn_button_rt, 'xpath')
                    elif rt_type == 'ERT':
                        warn_button_ert = "//span[contains(@data-bind,'export_route_target_vcfg')]"
                        warn_button = self.find_element(warn_button_ert, 'xpath')
                    elif rt_type == 'IRT':
                        warn_button_irt = "//span[contains(@data-bind,'import_route_target_vcfg')]"
                        warn_button = self.find_element(warn_button_irt, 'xpath')
                    if warn_button.get_attribute('style') == "":
                        self.click_on_cancel_if_failure('cancelBtn')
                        self.wait_till_ajax_done(self.browser)
                        return result
                    else:
                        result = result and False
            else:
                self.logger.error("Clicking the Edit Button is not working")
                result = result and False

        except WebDriverException:
            self.logger.error("Error while trying to edit %s" % (option))
            self.screenshot(option)
            result = result and False
            self.click_on_cancel_if_failure('cancelBtn')
            raise
        return result
    # edit_vn_with_route_target

    def get_ui_value(self, option, search_key, name=None):
        dom_arry = []
        eval('self.click_configure_' + option.lower())()
        self.wait_till_ajax_done(self.browser, wait=3)
        rows = self.get_rows(canvas=True)
        if name:
            for index, row in enumerate(rows, start=1):
                if re.search(name, str(row.text)):
                    break
        else:
            index = len(rows)
        rows_detail = self.click_basic_and_get_row_details(
                         'ports', index-1, canvas=True)[1]
        for detail in range(len(rows_detail)):
            key_arry = self.find_element(
                       'key', 'class', browser = rows_detail[detail]).text
            value_arry = self.find_element(
                        'value', 'class', browser = rows_detail[detail]).text
            if key_arry == search_key:
                key_arry = key_arry.replace(' ', '_')
                dom_arry.append({'key': key_arry, 'value': value_arry})
                break
        return dom_arry
    # get_ui_value

    def format_sec_group_name(self, sec_group_list, project_name):
        self.format_sec_group_list = []
        for sg in sec_group_list:
            search_value = re.search("(.*)\(.*:(.*)", sg)
            if search_value:
                sec_group = search_value.group(2).strip('\)') + '-' + \
                            search_value.group(1).strip()
            else:
                sec_group = project_name + '-' + sg.strip()
            self.format_sec_group_list.append(sec_group)
        return self.format_sec_group_list
    # format_sec_group_name

    def negative_test_proc(self, option):
        warn_button = self.find_element('alert-error', 'class')
        if warn_button.get_attribute('style') == "":
            form_error =  option + "_form_error"
            span = "//span[contains(@data-bind, " + form_error + ")]"
            error = self.find_element(span, 'xpath')
            self.logger.info("Getting %s error message while saving" % (error.text))
            self.click_on_cancel_if_failure('cancelBtn')
            self.wait_till_ajax_done(self.browser)
            return False
        else:
            return True
    # negative_test_proc

    def get_global_config_api_href(self, option):
        api_str = 'global-' + option + '-configs'
        global_config_api = self.get_global_config_api(api_str)
        global_config_href = {}
        if len(global_config_api):
            global_config_href = self.get_details(
                global_config_api[api_str][0]['href'])
        return global_config_href
    # get_global_config_api_href

    def get_global_config_row_details_webui(self, webui_global_key_value=[], index=0):
        rows = self.find_element('grid-canvas', 'class', elements=True)[index]
        rows_detail = self.get_rows(rows)
        for row in rows_detail:
            key_value = row.text.split('\n')
            key = str(key_value.pop(0))
            if key == 'Graceful Restart':
                webui_global_key_value.append({'key': 'Graceful_Restart',
                                             'value': key_value[0]})
                if key_value[0] == 'Enabled':
                    timer_values = key_value[-1].split(' ')
                    self.keyvalue_list(webui_global_key_value, BGP_Helper=timer_values[0],
                        Restart_Time=timer_values[1], LLGR_Time=timer_values[2],
                        End_of_RIB=timer_values[3])
                continue
            if len(key_value) == 1:
                key_value = key_value[0]
                if key_value == '-':
                    continue
            key = key.replace(' ', '_')
            webui_global_key_value.append({'key': key, 'value': key_value})
        return webui_global_key_value
    # get_global_config_row_details_webui

    def send_keys_values(self, key_values_dict, br=None):
        result = True
        try:
            if not br:
                br = self.browser
            for key, value in key_values_dict.items():
                for inner_key, inner_value in value.items():
                    self.send_keys(inner_value, inner_key, key, browser=br, clear=True)
        except WebDriverException:
            result = False
        return result
    # end send_keys_values
