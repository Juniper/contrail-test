from netaddr import IPNetwork
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
import time
import random
import fixtures
from ipam_test import *
from project_test import *
from util import *
from vnc_api.vnc_api import *
from netaddr import *
from time import sleep
from contrail_fixtures import *
from pyvirtualdisplay import Display
import inspect
import policy_test_utils
import threading
import sys
from webui_common import *


class WebuiTest:

    def __init__(self, connections, inputs):
        self.proj_check_flag = 0
        self.inputs = inputs
        self.connections = connections
        self.logger = self.inputs.logger
        self.browser = self.connections.browser
        self.browser_openstack = self.connections.browser_openstack
        self.delay = 10
        self.frequency = 1
        self.logger = inputs.logger
        self.webui_common = WebuiCommon(self)
        self.dash = "-" * 60
        self.vnc_lib = connections.vnc_lib_fixture

    def _click_if_element_found(self, element_name, elements_list):
        for element in elements_list:
            if element.text == element_name:
                element.click()
                break
    # end _click_if_element_found

    def create_vn_in_webui(self, fixture):
        result = True
        try:
            fixture.obj = fixture.quantum_fixture.get_vn_obj_if_present(
                fixture.vn_name, fixture.project_id)
            if not fixture.obj:
                self.logger.info("Creating VN %s using webui..." %
                                 (fixture.vn_name))
                if not self.webui_common.click_configure_networks():
                    result = result and False
                self.webui_common.select_project(fixture.project_name)
                self.browser.get_screenshot_as_file(
                    'createVN' + self.webui_common.date_time_string() + '.png')
                self.webui_common.click_element(
                    self.browser, 'btnCreateVN', 'id')
                self.webui_common.wait_till_ajax_done(self.browser)
                txtVNName = self.webui_common.find_element(
                    self.browser, 'txtVNName', 'id')
                txtVNName.send_keys(fixture.vn_name)
                if type(fixture.vn_subnets) is list:
                    for subnet in fixture.vn_subnets:
                        self.webui_common.click_element(
                            self.browser, 'btnCommonAddIpam', 'id')
                        self.webui_common.wait_till_ajax_done(self.browser)
                        self.webui_common.click_element(
                            self.browser, ['ipamTuples', 'select2-choice'], ['id', 'class'])
                        ipam_list = self.webui_common.find_element(
                            self.browser, ['select2-drop', 'li'], ['id', 'tag'], [1])
                        self.webui_common.wait_till_ajax_done(self.browser)
                        for ipam in ipam_list:
                            ipam_text = ipam.find_element_by_tag_name(
                                'div').text
                            time.sleep(2)
                            if ipam_text.find(fixture.ipam_fq_name[2]) != -1:
                                ipam.click()
                                break
                        self.browser.find_element_by_xpath(
                            "//input[@placeholder = 'IP Block'] ").send_keys(subnet['cidr'])
                else:
                    self.browser.find_element_by_id('btnCommonAddIpam').click()
                    self.browser.find_element_by_id(
                        "select2-drop-mask").click()
                    ipam_list = self.browser.find_element_by_id(
                        "select2-drop").find_element_by_tag_name('ul').find_elements_by_tag_name('li')
                    for ipam in ipam_list:
                        ipam_text = ipam.get_attribute("innerHTML")
                        if ipam_text == self.ipam_fq_name:
                            ipam.click()
                            break
                    self.browser.find_element_by_xpath(
                        "//input[@placeholder = 'IP Block'] ").send_keys(fixture.vn_subnets['cidr'])
                self.browser.find_element_by_id('btnCreateVNOK').click()
                time.sleep(3)
                if not self.webui_common.check_error_msg("create VN"):
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
        except Exception as e:
            with fixture.lock:
                self.logger.exception(
                    "Got exception as %s while creating %s" % (e, fixture.vn_name))
                sys.exit(-1)
    # end create_vn_in_webui

    def create_dns_server_in_webui(self):
        ass_ipam_list = ['ipam1', 'ipam_1']
        if not self.webui_common.click_configure_dns_server():
            result = result and False
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('btnCreateDNSServer')).click()
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtDNSServerName')).send_keys('server1')
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtDomainName')).send_keys('domain1')
        self.browser.find_elements_by_class_name(
            'control-group')[2].find_element_by_tag_name('i').click()
        options = self.browser.find_element_by_class_name(
            'ui-autocomplete').find_elements_by_tag_name('li')
        for i in range(len(options)):
            if (options[i].find_element_by_tag_name('a').text == 'default-domain:dnss'):
                options[i].click()
                time.sleep(2)
        self.browser.find_element_by_id(
            's2id_ddLoadBal').find_element_by_tag_name('a').click()
        rro_list = self.browser.find_element_by_id(
            'select2-drop').find_elements_by_tag_name('li')
        rro_opt_list = [element.find_element_by_tag_name('div')
                        for element in rro_list]
        for rros in rro_opt_list:
            rros_text = rros.text
            if rros_text == 'Round-Robin':
                rros.click()
                break
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtTimeLive')).send_keys('300')
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
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('btnCreateDNSServerOK')).click()
        if not self.webui_common.check_error_msg("create DNS"):
            raise Exception("DNS creation failed")
        # end create_dns_server_in_webui

    def create_dns_record_in_webui(self):
        if not self.webui_common.click_configure_dns_record():
            result = result and False
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('btnCreateDNSRecord')).click()
        self.browser.find_element_by_id(
            's2id_cmbRecordType').find_element_by_tag_name('a').click()
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
                        if dns_servers[servers].find_element_by_tag_name('a').text == 'default-domain:' + 'dns2':
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
        if not self.webui_common.check_error_msg("create DNS Record"):
            raise Exception("DNS Record creation failed")
        # end create_dns_record_in_webui

    def create_svc_template_in_webui(self, fixture):
        result = True
        if not self.webui_common.click_configure_service_template():
            result = result and False
        self.logger.info("Creating svc template %s using webui" %
                         (fixture.st_name))
        self.webui_common.click_element(
            self.browser, 'btnCreatesvcTemplate', 'id')
        self.webui_common.wait_till_ajax_done(self.browser)
        txt_temp_name = WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtTempName'))
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
        if not self.webui_common.check_error_msg("create service template"):
            raise Exception("service template creation failed")
    # end create_svc_template_in_webui

    def create_svc_instance_in_webui(self, fixture):
        result = True
        if not self.webui_common.click_configure_service_instance():
            result = result and False
        self.webui_common.select_project(fixture.project_name)
        self.logger.info("Creating svc instance %s using webui" %
                         (fixture.si_name))
        self.webui_common.click_element(
            self.browser, 'btnCreatesvcInstances', 'id')
        self.webui_common.wait_till_ajax_done(self.browser)
        txt_instance_name = WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtsvcInstanceName'))
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
        if not self.webui_common.check_error_msg("create service instance"):
            raise Exception("service instance creation failed")
        time.sleep(40)
    # end create_svc_instance_in_webui

    def create_ipam_in_webui(self, fixture):
        result = True
        ip_blocks = False
        if not self.webui_common.click_configure_ipam():
            result = result and False
        self.webui_common.select_project(fixture.project_name)
        self.logger.info("Creating ipam %s using webui" % (fixture.name))
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('btnCreateEditipam')).click()
        self.webui_common.wait_till_ajax_done(self.browser)
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_id('txtIPAMName')).send_keys(fixture.name)
        self.webui_common.wait_till_ajax_done(self.browser)
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
                    self.webui_common.wait_till_ajax_done(self.browser)
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
            self.webui_common.wait_till_ajax_done(self.browser)
            vn_list = self.browser.find_element_by_id('select2-drop').find_elements_by_tag_name('li')
            virtual_net_list = [ element.find_element_by_tag_name('div') for element in vn_list]
            for vns in virtual_net_list :
                vn_text = vns.text
                if vn_text ==  net_list[net] :
                    vns.click()
                    break
            
            self.browser.find_element_by_xpath("//*[contains(@placeholder, 'IP Block')]").send_keys('187.23.2.'+str(net+1)+'/21')
            '''
        self.browser.find_element_by_id("btnCreateEditipamOK").click()
        if not self.webui_common.check_error_msg("Create ipam"):
            raise Exception("ipam creation failed")
        # end create_ipam_in_webui

    def create_policy_in_webui(self, fixture):
        result = True
        line = 0
        try:
            fixture.policy_obj = fixture.quantum_fixture.get_policy_if_present(
                fixture.project_name, fixture.policy_name)
            if not fixture.policy_obj:
                self.logger.info("Creating policy %s using webui" %
                                 (fixture.policy_name))
                if not self.webui_common.click_configure_policies():
                    result = result and False
                self.webui_common.select_project(fixture.project_name)
                WebDriverWait(self.browser, self.delay).until(
                    lambda a: a.find_element_by_id('btnCreatePolicy')).click()
                time.sleep(2)
                WebDriverWait(self.browser, self.delay).until(
                    lambda a: a.find_element_by_id('txtPolicyName')).send_keys(fixture.policy_name)
                time.sleep(2)
                for index, rule in enumerate(fixture.rules_list):
                    action = rule['simple_action']
                    protocol = rule['protocol']
                    source_net = rule['source_network']
                    direction = rule['direction']
                    dest_net = rule['dest_network']
                    if rule['src_ports']:
                        if type(rule['src_ports']) is list:
                            src_port = ','.join(str(num)
                                                for num in rule['src_ports'])
                        else:
                            src_port = str(rule['src_ports'])
                    if rule['dst_ports']:
                        if type(rule['dst_ports']) is list:
                            dst_port = ','.join(str(num)
                                                for num in rule['dst_ports'])
                        else:
                            dst_port = str(rule['dst_ports'])
                    self.browser.find_element_by_id('btnCommonAddRule').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    controls = WebDriverWait(self.browser, self.delay).until(
                        lambda a: a.find_element_by_class_name('controls'))
                    rules = self.webui_common.find_element(
                        controls, ['ruleTuples', 'rule-item'], ['id', 'class'], [1])[line]
                    src_dst_port_obj = self.webui_common.find_element(
                        controls, ['ruleTuples', 'rule-item'], ['id', 'class'], [1])[line]
                    src_dst_port_obj.find_elements_by_class_name(
                        'span1')[2].find_element_by_tag_name('input').send_keys(src_port)    
                    src_dst_port_obj.find_elements_by_class_name(
                        'span1')[4].find_element_by_tag_name('input').send_keys(dst_port)       
                    rules = rules.find_elements_by_css_selector(
                        "div[class$='pull-left']")
                    rules[3].find_element_by_class_name(
                        'select2-container').find_element_by_tag_name('a').click()
                    direction_list = self.browser.find_element_by_id(
                        'select2-drop').find_elements_by_tag_name('li')
                    dir_list = [element.find_element_by_tag_name('div')
                        for element in direction_list]
                    for directions in dir_list:
                        direction_text = directions.text
                        if direction_text == direction:
                            directions.click()
                            break
                    li = self.browser.find_elements_by_css_selector(
                        "ul[class^='ui-autocomplete']")
                    if len(li) == 4 and index == 0 :
                        lists = 0
                    elif index == 0 :
                        lists = 1
                    for rule in range(len(rules)):
                        if rule == 3 :
                            continue
                        rules[rule].find_element_by_class_name(
                            'add-on').find_element_by_class_name('icon-caret-down').click()
                        time.sleep(2)
                        opt = li[lists].find_elements_by_tag_name('li')
                        if rule == 0:
                            self.sel(opt, action.upper())
                        elif rule == 1:
                            self.sel(opt, protocol.upper())
                        elif rule == 2:
                            self.sel(opt, source_net)
                        elif rule == 4:
                            self.sel(opt, dest_net)
                        lists = lists + 1
                self.browser.find_element_by_id('btnCreatePolicyOK').click()
                self.webui_common.wait_till_ajax_done(self.browser)
                if not self.webui_common.check_error_msg("Create Policy"):
                    raise Exception("Policy creation failed")
                fixture.policy_obj = fixture.quantum_fixture.get_policy_if_present(
                    fixture.project_name, fixture.policy_name)
            else:
                fixture.already_present = True
                self.logger.info(
                    'Policy %s already exists, skipping creation ' %
                    (fixture.policy_name))
                self.logger.debug('Policy %s exists, already there' %
                                  (fixture.policy_name))
        except Exception as e:
            self.logger.exception("Got exception as %s while creating %s" %
                                  (e, fixture.policy_name))
            sys.exit(-1)

    def sel(self, opt, choice):
        for i in range(len(opt)):
            option = opt[i].find_element_by_class_name('ui-corner-all')
            text = option.get_attribute("innerHTML")
            if text == choice:
                time.sleep(1)
                option.click()
                time.sleep(1)
                return
            continue

    def policy_delete_in_webui(self, fixture):
        if not self.webui_common.click_configure_policies():
            result = result and False
        rows = self.webui_common.get_rows()
        for pol in range(len(rows)):
            tdArry = rows[pol].find_elements_by_class_name('slick-cell')
            if(len(tdArry) > 2):
                if (tdArry[2].text == fixture.policy_name):
                    tdArry[0].find_element_by_tag_name('i').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    rows = self.webui_common.get_rows()
                    ass_net = rows[
                        pol + 1].find_elements_by_class_name('row-fluid')[1].find_element_by_xpath("//div[@class='span11']").text.split()
                    if(ass_net[0] != '-'):
                        for net in range(len(ass_net)):
                            network.append(ass_net[net])
                    else:
                        print("No networks associated")
                    tdArry[5].find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id(
                        'gridPolicy-action-menu-' + str(i)).find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
                    self.browser.find_element_by_id("btnRemovePopupOK").click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    if not self.webui_common.check_error_msg("Delete policy"):
                        raise Exception("Policy deletion failed")
                    self.logger.info("%s is deleted successfully using webui" %
                                     (fixture.policy_name))
                    break
    # end policy_delete_in_webui

    def verify_analytics_nodes_ops_basic_data(self):
        self.logger.info("Verifying analytics_node basic ops-data in Webui...")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_analytics_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        analytics_nodes_list_ops = self.webui_common.get_collectors_list_ops()
        result = True
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info("Vn host name %s exists in op server..checking if exists in webui as well" % (
                ops_analytics_node_name))
            if not self.webui_common.click_monitor_analytics_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info("Analytics_node name %s found in webui..going to match basic details.." % (
                        ops_analytics_node_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error("Analytics_node name %s did not match in webui...not found in webui" % (
                    ops_analytics_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Click and retrieve analytics_node basic view details in webui for  \
                    analytics_node-name %s " % (ops_analytics_node_name))
                self.webui_common.click_monitor_analytics_nodes_basic(
                    match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status
                # filter analytics_node basic view details from opserver data
                analytics_nodes_ops_data = self.webui_common.get_details(
                    analytics_nodes_list_ops[n]['href'])
                ops_basic_data = []
                host_name = analytics_nodes_list_ops[n]['name']
                ip_address = analytics_nodes_ops_data.get(
                    'CollectorState').get('self_ip_list')
                ip_address = ', '.join(ip_address)
                generators_count = str(
                    len(analytics_nodes_ops_data.get('CollectorState').get('generator_infos')))
                version = json.loads(analytics_nodes_ops_data.get('CollectorState').get('build_info')).get(
                    'build-info')[0].get('build-id')
                version = self.webui_common.get_version_string(version)
                module_cpu_info_len = len(
                    analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                for i in range(module_cpu_info_len):
                    if analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i][
                            'module_id'] == 'Collector':
                        cpu_mem_info_dict = analytics_nodes_ops_data.get(
                            'ModuleCpuState').get('module_cpu_info')[i]
                        break
                cpu = self.webui_common.get_cpu_string(cpu_mem_info_dict)
                memory = self.webui_common.get_memory_string(cpu_mem_info_dict)
                modified_ops_data = []
                
                process_state_list = analytics_nodes_ops_data.get(
                    'ModuleCpuState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                redis_uve_string = None
                redis_query_string = None
                exclude_process_list = [
                    'contrail-config-nodemgr', 'contrail-analytics-nodemgr', 'contrail-control-nodemgr', 'contrail-vrouter-nodemgr',
                    'openstack-nova-compute', 'contrail-svc-monitor', 'contrail-discovery:0', 'contrail-zookeeper', 'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'redis-query':
                        redis_query_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-qe':
                        contrail_qe_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-analytics-nodemgr':
                        contrail_analytics_nodemgr_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'redis-uve':
                        redis_uve_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-opserver':
                        contrail_opserver_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-collector':
                        contrail_collector_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = {}
		for k, v in process_down_stop_time_dict.items():
			if k not in exclude_process_list:
				reduced_process_keys_dict[k]=v
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = min(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'

                modified_ops_data.extend(
                    [{'key': 'Hostname', 'value': host_name}, {'key': 'Generators', 'value': generators_count}, {'key': 'IP Address', 'value': ip_address}, {'key': 'CPU', 'value': cpu}, {'key': 'Memory', 'value': memory}, {'key': 'Version', 'value': version}, {'key': 'Collector', 'value': contrail_collector_string},
                     {'key': 'Query Engine', 'value': contrail_qe_string}, {'key': 'OpServer', 'value': contrail_opserver_string}, {'key': 'Overall Node Status', 'value': overall_node_status_string}])
                if redis_uve_string:
                    modified_ops_data.append({'key': 'Redis UVE', 'value': redis_uve_string})
                if redis_query_string:
                    modified_ops_data.append({'key': 'Redis Query', 'value': redis_query_string})
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info(
                        "Ops %s uves analytics_nodes basic view details data matched in webui" %
                        (ops_analytics_node_name))
                else:
                    self.logger.error(
                        "Ops %s uves analytics_nodes basic view details data match failed in webui" %
                        (ops_analytics_node_name))
                    result = result and False
        return result
        # end verify_analytics_nodes_ops_basic_data_in_webui

    def verify_config_nodes_ops_basic_data(self):
        self.logger.info(
            "Verifying config_node basic ops-data in Webui monitor->infra->Config Nodes->details(basic view)...")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_config_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        config_nodes_list_ops = self.webui_common.get_config_nodes_list_ops()
        result = True
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info("Vn host name %s exists in op server..checking if exists in webui as well" % (
                ops_config_node_name))
            if not self.webui_common.click_monitor_config_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_config_node_name:
                    self.logger.info("Config_node name %s found in webui..going to match basic details..." % (
                        ops_config_node_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error("Config_node name %s did not match in webui...not found in webui" % (
                    ops_config_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Click and retrieve config_node basic view details in webui for  \
                    config_node-name %s " % (ops_config_node_name))
                # filter config_node basic view details from opserver data
                config_nodes_ops_data = self.webui_common.get_details(
                    config_nodes_list_ops[n]['href'])
                self.webui_common.click_monitor_config_nodes_basic(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                ops_basic_data = []
                host_name = config_nodes_list_ops[n]['name']
                ip_address = config_nodes_ops_data.get(
                    'ModuleCpuState').get('config_node_ip')
                if not ip_address:
                    ip_address = '--'
                else:
                    ip_address = ', '.join(ip_address)
                process_state_list = config_nodes_ops_data.get(
                    'ModuleCpuState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr', 'contrail-analytics-nodemgr', 'contrail-control-nodemgr', 'contrail-vrouter-nodemgr',
                    'openstack-nova-compute', 'contrail-svc-monitor', 'contrail-discovery:0', 'contrail-zookeeper', 'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-api:0':
                        api_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'ifmap':
                        ifmap_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-discovery:0':
                        discovery_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-schema':
                        schema_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-svc-monitor':
                        monitor_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = {}
		for k, v in process_down_stop_time_dict.items():
			if k not in exclude_process_list:
				reduced_process_keys_dict[k]=v
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(
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
                    version = json.loads(config_nodes_ops_data.get('ModuleCpuState').get('build_info')).get(
                        'build-info')[0].get('build-id')
                    version = self.webui_common.get_version_string(version)
                module_cpu_info_len = len(
                    config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                cpu_mem_info_dict = {}
                for i in range(module_cpu_info_len):
                    if config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i][
                            'module_id'] == 'ApiServer':
                        cpu_mem_info_dict = config_nodes_ops_data.get(
                            'ModuleCpuState').get('module_cpu_info')[i]
                        break
                if not cpu_mem_info_dict:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.webui_common.get_cpu_string(cpu_mem_info_dict)
                    memory = self.webui_common.get_memory_string(
                        cpu_mem_info_dict)
                modified_ops_data = []
                generator_list = self.webui_common.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_config_node_name + ':Config:Contrail-Config-Nodemgr:0':
                        analytics_data = element['href']
                        generators_vrouters_data = self.webui_common.get_details(
                            element['href'])
                        analytics_data = generators_vrouters_data.get(
                            'ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data[
                                'primary'].split(':')[0] + ' (Up)'

                modified_ops_data.extend(
                    [{'key': 'Hostname', 'value': host_name}, {'key': 'IP Address', 'value': ip_address}, {'key': 'CPU', 'value': cpu}, {'key': 'Memory', 'value': memory}, {'key': 'Version', 'value': version}, {'key': 'API Server', 'value': api_string},
                     {'key': 'Discovery', 'value': discovery_string}, {'key': 'Service Monitor', 'value': monitor_string}, {'key': 'Ifmap', 'value': ifmap_string}, {'key': 'Schema Transformer', 'value': schema_string}, {'key': 'Overall Node Status', 'value': overall_node_status_string}])
                self.webui_common.match_ops_with_webui(
                    modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info(
                        "Ops %s uves config_nodes basic view details data matched in webui" %
                        (ops_config_node_name))
                else:
                    self.logger.error(
                        "Ops %s uves config_nodes basic view details data match failed in webui" % (ops_config_node_name))
                    result = result and False
        return result
        # end verify_config_nodes_ops_basic_data_in_webui

    def verify_vrouter_ops_basic_data(self):
        result = True
        self.logger.info(
            "Verifying vrouter basic ops-data in Webui monitor->infra->Virtual routers->details(basic view)...")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_vrouters():
            result = result and False
        rows = self.webui_common.get_rows()
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in op server..checking if exists in webui as well" %
                (ops_vrouter_name))
            if not self.webui_common.click_monitor_vrouters():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info(
                        "Vrouter name %s found in webui..going to match basic details..." % (ops_vrouter_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vrouter name %s did not match in webui...not found in webui" % (ops_vrouter_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve vrouter basic view details in webui for vrouter-name %s " % (ops_vrouter_name))
                self.webui_common.click_monitor_vrouters_basic(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
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
                vrouters_ops_data = self.webui_common.get_details(
                    vrouters_list_ops[n]['href'])
                ops_basic_data = []
                host_name = vrouters_list_ops[n]['name']
                ip_address = vrouters_ops_data.get(
                    'VrouterAgent').get('self_ip_list')[0]
                version = json.loads(vrouters_ops_data.get('VrouterAgent').get('build_info')).get(
                    'build-info')[0].get('build-id')
                version = version.split('-')
                version = version[0] + ' (Build ' + version[1] + ')'
                xmpp_messages = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('xmpp_stats_list')
                for i, item in enumerate(xmpp_messages):
                    if item['ip'] == ip_address:
                        xmpp_in_msgs = item['in_msgs']
                        xmpp_out_msgs = item['out_msgs']
                        xmpp_msgs_string = str(xmpp_in_msgs) + \
                            ' In ' + \
                            str(xmpp_out_msgs) + ' Out'
                        break
                total_flows = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('total_flows')
                active_flows = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('active_flows')
                flow_count_string = str(active_flows) + \
                    ' Active, ' + \
                    str(total_flows) + ' Total'
                if vrouters_ops_data.get('VrouterAgent').get('connected_networks'):
                    networks = str(
                        len(vrouters_ops_data.get('VrouterAgent').get('connected_networks')))
                else:
                    networks = '--'
                interfaces = str(vrouters_ops_data.get('VrouterAgent')
                                 .get('total_interface_count'))
                if vrouters_ops_data.get('VrouterAgent').get('virtual_machine_list'):
                    instances = str(
                        len(vrouters_ops_data.get('VrouterAgent').get('virtual_machine_list')))
                else:
                    instances = '--'
                cpu = vrouters_ops_data.get('VrouterStatsAgent').get(
                    'cpu_info').get('cpu_share')
                cpu = str(round(cpu, 2)) + ' %'
                memory = vrouters_ops_data.get('VrouterStatsAgent').get(
                    'cpu_info').get('meminfo').get('virt')
                memory = memory / 1024.0
                if memory < 1024:
                    memory = str(round(memory, 2)) + ' MB'
                else:
                    memory = str(round(memory / 1024), 2) + ' GB'
                last_log = vrouters_ops_data.get(
                    'VrouterAgent').get('total_interface_count')
                modified_ops_data = []
                process_state_list = vrouters_ops_data.get(
                    'VrouterStatsAgent').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr', 'contrail-analytics-nodemgr', 'contrail-control-nodemgr', 'contrail-vrouter-nodemgr',
                    'openstack-nova-compute', 'contrail-svc-monitor', 'contrail-discovery:0', 'contrail-zookeeper', 'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-vrouter':
                        contrail_vrouter_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-vrouter-nodemgr':
                        contrail_vrouter_nodemgr_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'openstack-nova-compute':
                        openstack_nova_compute_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = {}
		for k, v in process_down_stop_time_dict.items():
			if k not in exclude_process_list:
				reduced_process_keys_dict[k] = v
                '''
                if not reduced_process_keys_dict :
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values()))) 
                    overall_node_status_string  = ['Down since ' + status for status in overall_node_status_down_time]
                '''
                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    process_down_list = reduced_process_keys_dict.keys()
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'

                generator_list = self.webui_common.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_vrouter_name + ':Compute:VRouterAgent:0':
                        analytics_data = element['href']
                        break
                generators_vrouters_data = self.webui_common.get_details(
                    element['href'])
                analytics_data = generators_vrouters_data.get(
                    'ModuleClientState').get('client_info')
                if analytics_data['status'] == 'Established':
                    analytics_primary_ip = analytics_data[
                        'primary'].split(':')[0] + ' (Up)'
                    tx_socket_bytes = analytics_data.get(
                        'tx_socket_stats').get('bytes')
                    tx_socket_size = self.webui_common.get_memory_string(
                        int(tx_socket_bytes))
                    analytics_msg_count = generators_vrouters_data.get(
                        'ModuleClientState').get('session_stats').get('num_send_msg')
                    offset = 10
                    analytics_msg_count_list = range(
                        int(analytics_msg_count) - offset, int(analytics_msg_count) + offset)
                    analytics_messages_string = [
                        str(count) + ' [' + str(size) + ']' for count in analytics_msg_count_list for size in tx_socket_size]
                control_nodes_list = vrouters_ops_data.get(
                    'VrouterAgent').get('xmpp_peer_list')
                control_nodes_string = ''
                for node in control_nodes_list:
                    if node['status'] == True and node['primary'] == True:
                        control_ip = node['ip']
                        control_nodes_string = control_ip + '* (Up)'
                        index = control_nodes_list.index(node)
                        del control_nodes_list[index]
                for node in control_nodes_list:
                    node_ip = node['ip']
                    if node['status'] == True:
                        control_nodes_string = control_nodes_string + \
                            ', ' + node_ip + ' (Up)'
                    else:
                        control_nodes_string = control_nodes_string + \
                            ', ' + node_ip + ' (Down)'

                modified_ops_data.extend(
                    [{'key': 'Flow Count', 'value': flow_count_string}, {'key': 'Hostname', 'value': host_name}, {'key': 'IP Address', 'value': ip_address}, {'key': 'Networks', 'value': networks}, {'key': 'Instances', 'value': instances}, {'key': 'CPU', 'value': cpu}, {'key': 'Memory', 'value': memory}, {'key': 'Version', 'value': version},
                     {'key': 'vRouter Agent', 'value': contrail_vrouter_string}, {'key': 'Overall Node Status', 'value': overall_node_status_string},  {'key': 'Analytics Node', 'value': analytics_primary_ip}, {'key': 'Analytics Messages', 'value': analytics_messages_string}, {'key': 'Control Nodes', 'value': control_nodes_string}])
                self.webui_common.match_ops_with_webui(
                    modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info(
                        "Ops %s uves vrouters basic view details data matched in webui" % (ops_vrouter_name))
                else:
                    self.logger.error(
                        "Ops %s uves vrouters basic view details data match failed in webui" % (ops_vrouter_name))
                    result = result and False

        return result
        # end verify_vrouter_ops_basic_data_in_webui

    def verify_vrouter_ops_advance_data(self):
        self.logger.info(
            "Verifying vrouter Ops-data in Webui monitor->infra->Virtual Routers->details(advance view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_vrouters():
            result = result and False
        rows = self.webui_common.get_rows()
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        result = True
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info(
                "Vn host name %s exists in op server..checking if exists in webui as well" %
                (ops_vrouter_name))
            if not self.webui_common.click_monitor_vrouters():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info(
                        "Vrouter name %s found in webui..going to match advance details..." % (ops_vrouter_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vrouter name %s did not match in webui...not found in webui" % (ops_vrouter_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve vrouter advance details in webui for vrouter-name %s " % (ops_vrouter_name))
                self.webui_common.click_monitor_vrouters_advance(match_index)
                vrouters_ops_data = self.webui_common.get_details(
                    vrouters_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if vrouters_ops_data.has_key('VrouterStatsAgent'):
                    ops_data = vrouters_ops_data['VrouterStatsAgent']
                    history_del_list = [
                        'total_in_bandwidth_utilization', 'cpu_share', 'used_sys_mem',
                        'one_min_avg_cpuload', 'virt_mem', 'total_out_bandwidth_utilization']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']

                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(
                        ops_data, modified_ops_data)
                if vrouters_ops_data.has_key('VrouterAgent'):
                    ops_data_agent = vrouters_ops_data['VrouterAgent']
                    modified_ops_data_agent = []
                    self.webui_common.extract_keyvalue(
                        ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + \
                        modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list:
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(
                            "Ops %s uves virual networks advance view data matched in webui" % (ops_vrouter_name))
                    else:
                        self.logger.error(
                            "Ops %s uves virual networks advance data match failed in webui" % (ops_vrouter_name))
                        result = result and False
        return result
    # end verify_vrouter_ops_advance_data_in_webui

    def verify_bgp_routers_ops_basic_data(self):
        self.logger.info(
            "Verifying Control Nodes basic ops-data in Webui monitor->infra->Control Nodes->details(basic view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_control_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        bgp_routers_list_ops = self.webui_common.get_bgp_routers_list_ops()
        result = True
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_routers_name = bgp_routers_list_ops[n]['name']
            self.logger.info("Control node host name %s exists in op server..checking if exists \
                in webui as well" % (ops_bgp_routers_name))
            if not self.webui_common.click_monitor_control_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_bgp_routers_name:
                    self.logger.info("Bgp routers name %s found in webui..going to match basic details..." % (
                        ops_bgp_routers_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error("Bgp routers name %s did not match in webui...not found in webui" % (
                    ops_bgp_routers_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info("Click and retrieve control nodes basic view details in webui for \
                    control node name %s " % (ops_bgp_routers_name))
                self.webui_common.click_monitor_control_nodes_basic(
                    match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute('innerHTML').replace('\n', '').strip()
                for i, item in enumerate(dom_basic_view):
                    if item.get('key') == 'Overall Node Status':
                        dom_basic_view[i]['value'] = node_status
                # filter bgp_routers basic view details from opserver data
                bgp_routers_ops_data = self.webui_common.get_details(
                    bgp_routers_list_ops[n]['href'])
                ops_basic_data = []
                host_name = bgp_routers_list_ops[n]['name']
                ip_address = bgp_routers_ops_data.get(
                    'BgpRouterState').get('bgp_router_ip_list')[0]
                if not ip_address:
                    ip_address = '--'
                version = json.loads(bgp_routers_ops_data.get('BgpRouterState').get('build_info')).get(
                    'build-info')[0].get('build-id')
                version = self.webui_common.get_version_string(version)
                bgp_peers_string = 'BGP Peers: ' + \
                    str(bgp_routers_ops_data.get('BgpRouterState')
                        .get('num_bgp_peer')) + ' Total'
                vrouters =  'vRouters: ' + \
                    str(bgp_routers_ops_data.get('BgpRouterState')
                        .get('num_up_xmpp_peer')) + '  Established in Sync'

                cpu = bgp_routers_ops_data.get('BgpRouterState')
                memory = bgp_routers_ops_data.get('BgpRouterState')
                if not cpu:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.webui_common.get_cpu_string(cpu)
                    memory = self.webui_common.get_memory_string(memory)
                generator_list = self.webui_common.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_bgp_routers_name + ':Control:ControlNode:0':
                        analytics_data = element['href']
                        generators_vrouters_data = self.webui_common.get_details(
                            element['href'])
                        analytics_data = generators_vrouters_data.get(
                            'ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data[
                                'primary'].split(':')[0] + ' (Up)'
                            tx_socket_bytes = analytics_data.get(
                                'tx_socket_stats').get('bytes')
                            tx_socket_size = self.webui_common.get_memory_string(
                                int(tx_socket_bytes))
                            analytics_msg_count = generators_vrouters_data.get(
                                'ModuleClientState').get('session_stats').get('num_send_msg')
                            offset = 10
                            analytics_msg_count_list = range(
                                int(analytics_msg_count) - offset, int(analytics_msg_count) + offset)
                            analytics_messages_string = [
                                str(count) + ' [' + str(size) + ']' for count in analytics_msg_count_list for size in tx_socket_size]
                ifmap_ip = bgp_routers_ops_data.get('BgpRouterState').get(
                    'ifmap_info').get('url').split(':')[0]
                ifmap_connection_status = bgp_routers_ops_data.get(
                    'BgpRouterState').get('ifmap_info').get('connection_status')
                ifmap_connection_status_change = bgp_routers_ops_data.get(
                    'BgpRouterState').get('ifmap_info').get('connection_status_change_at')
                ifmap_connection_string = [ifmap_ip + ' (' + ifmap_connection_status + ' since ' + time +
                                           ')' for time in self.webui_common.get_node_status_string(ifmap_connection_status_change)]
                process_state_list = bgp_routers_ops_data.get(
                    'BgpRouterState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = [
                    'contrail-config-nodemgr', 'contrail-analytics-nodemgr', 'contrail-control-nodemgr', 'contrail-vrouter-nodemgr',
                    'openstack-nova-compute', 'contrail-svc-monitor', 'contrail-discovery:0', 'contrail-zookeeper', 'contrail-schema']
                for i, item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-control':
                        control_node_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-control-nodemgr':
                        control_nodemgr_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-dns':
                        contrail_dns_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-named':
                        contrail_named_string = self.webui_common.get_process_status_string(
                            item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = {}
		for k, v in process_down_stop_time_dict.items():
                        if k not in exclude_process_list:
                                reduced_process_keys_dict[k] = v

                if not reduced_process_keys_dict:
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(
                        str(recent_time))
                    overall_node_status_string = [
                        'Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(
                        str(max(reduced_process_keys_dict.values())))
                    process_down_list = reduced_process_keys_dict.keys()
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(
                        process_down_count) + ' Process down'
                modified_ops_data = []
                modified_ops_data.extend(
                    [{'key': 'Peers', 'value': bgp_peers_string}, {'key': 'Hostname', 'value': host_name}, {'key': 'IP Address', 'value': ip_address}, {'key': 'CPU', 'value': cpu}, {'key': 'Memory', 'value': memory}, {'key': 'Version', 'value': version}, {'key': 'Analytics Node',
                                                                                                                                                                                                                                                                'value': analytics_primary_ip}, {'key': 'Analytics Messages', 'value': analytics_messages_string}, {'key': 'Ifmap Connection', 'value': ifmap_connection_string}, {'key': 'Control Node', 'value': control_node_string}, {'key': 'Overall Node Status', 'value': overall_node_status_string}])
                self.webui_common.match_ops_with_webui(
                    modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info(
                        "Ops %s uves bgp_routers basic view details data matched in webui" %
                        (ops_bgp_routers_name))
                else:
                    self.logger.error(
                        "Ops %s uves bgp_routers basic view details data match failed in webui" % (ops_bgp_routers_name))
                    result = result and False
        return result
        # end verify_bgp_routers_ops_basic_data_in_webui

    def verify_bgp_routers_ops_advance_data(self):
        self.logger.info(
            "Verifying Control Nodes ops-data in Webui monitor->infra->Control Nodes->details(advance view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_control_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        bgp_routers_list_ops = self.webui_common.get_bgp_routers_list_ops()
        result = True
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_router_name = bgp_routers_list_ops[n]['name']
            self.logger.info(
                "Bgp router %s exists in op server..checking if exists in webui " %
                (ops_bgp_router_name))
            self.logger.info(
                "Clicking on bgp_routers in monitor page  in Webui...")
            if not self.webui_common.click_monitor_control_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_bgp_router_name:
                    self.logger.info(
                        "Bgp router name %s found in webui..going to match advance details..." % (ops_bgp_router_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag:
                self.logger.error("Bgp router name %s not found in webui" %
                                  (ops_bgp_router_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve bgp advance view details in webui for bgp router-name %s " %
                    (ops_bgp_router_name))
                self.webui_common.click_monitor_control_nodes_advance(
                    match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                bgp_routers_ops_data = self.webui_common.get_details(
                    bgp_routers_list_ops[n]['href'])
                bgp_router_state_ops_data = bgp_routers_ops_data[
                    'BgpRouterState']
                history_del_list = [
                    'total_in_bandwidth_utilization', 'cpu_share', 'used_sys_mem',
                    'one_min_avg_cpuload', 'virt_mem', 'total_out_bandwidth_utilization']
                for item in history_del_list:
                    if bgp_router_state_ops_data.get(item):
                        for element in bgp_router_state_ops_data.get(item):
                            if element.get('history-10'):
                                del element['history-10']
                            if element.get('s-3600-topvals'):
                                del element['s-3600-topvals']
                if bgp_routers_ops_data.has_key('BgpRouterState'):
                    bgp_router_state_ops_data = bgp_routers_ops_data[
                        'BgpRouterState']

                    modified_bgp_router_state_ops_data = []
                    self.webui_common.extract_keyvalue(
                        bgp_router_state_ops_data, modified_bgp_router_state_ops_data)
                    complete_ops_data = modified_bgp_router_state_ops_data
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list:
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(
                            "Ops uves bgp router advanced view data matched in webui")
                    else:
                        self.logger.error(
                            "Ops uves bgp router advanced view bgp router match failed in webui")
                        result = result and False
        return result
    # end verify_bgp_routers_ops_advance_data_in_webui

    def verify_analytics_nodes_ops_advance_data(self):
        self.logger.info(
            "Verifying analytics_nodes(collectors) ops-data in Webui monitor->infra->Analytics Nodes->details(advance view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_analytics_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        analytics_nodes_list_ops = self.webui_common.get_collectors_list_ops()
        result = True
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info(
                "Analytics node %s exists in op server..checking if exists in webui " %
                (ops_analytics_node_name))
            self.logger.info(
                "Clicking on analytics_nodes in monitor page  in Webui...")
            if not self.webui_common.click_monitor_analytics_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info(
                        "Analytics node name %s found in webui..going to match advance details..." %
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
                    "Click and retrieve analytics advance view details in webui for analytics node-name %s " %
                    (ops_analytics_node_name))
                self.webui_common.click_monitor_analytics_nodes_advance(
                    match_index)
                analytics_nodes_ops_data = self.webui_common.get_details(
                    analytics_nodes_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
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
                    'opserver_mem_virt', 'queryengine_cpu_share', 'opserver_cpu_share',
                    'collector_cpu_share', 'collector_mem_virt', 'queryengine_mem_virt', 'enq_delay']
                if analytics_nodes_ops_data.has_key('QueryPerfInfo'):
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
                    self.webui_common.extract_keyvalue(
                        query_perf_info_ops_data, modified_query_perf_info_ops_data)
                if analytics_nodes_ops_data.has_key('ModuleCpuState'):
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

                    self.webui_common.extract_keyvalue(
                        module_cpu_state_ops_data, modified_module_cpu_state_ops_data)
                if analytics_nodes_ops_data.has_key('AnalyticsCpuState'):
                    analytics_cpu_state_ops_data = analytics_nodes_ops_data[
                        'AnalyticsCpuState']
                    modified_analytics_cpu_state_ops_data = []
                    self.webui_common.extract_keyvalue(
                        analytics_cpu_state_ops_data, modified_analytics_cpu_state_ops_data)
                if analytics_nodes_ops_data.has_key('CollectorState'):
                    collector_state_ops_data = analytics_nodes_ops_data[
                        'CollectorState']
                    self.webui_common.extract_keyvalue(
                        collector_state_ops_data, modified_collector_state_ops_data)
                complete_ops_data = modified_query_perf_info_ops_data + modified_module_cpu_state_ops_data + \
                    modified_analytics_cpu_state_ops_data + \
                    modified_collector_state_ops_data
                for k in range(len(complete_ops_data)):
                    if type(complete_ops_data[k]['value']) is list:
                        for m in range(len(complete_ops_data[k]['value'])):
                            complete_ops_data[k]['value'][m] = str(
                                complete_ops_data[k]['value'][m])
                    elif type(complete_ops_data[k]['value']) is unicode:
                        complete_ops_data[k]['value'] = str(
                            complete_ops_data[k]['value'])
                    else:
                        complete_ops_data[k]['value'] = str(
                            complete_ops_data[k]['value'])
                if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                    self.logger.info(
                        "Ops uves analytics node advance view data matched in webui")
                else:
                    self.logger.error(
                        "Ops uves analytics node match failed in webui")
                    result = result and False
        return result
    # end verify_analytics_nodes_ops_advance_data_in_webui

    def verify_vm_ops_basic_data(self):
        self.logger.info(
            "Verifying VM basic ops-data in Webui monitor->Networking->instances summary(basic view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_instances():
            result = result and False
        rows = self.webui_common.get_rows()
        vm_list_ops = self.webui_common.get_vm_list_ops()
        result = True
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            if not self.webui_common.click_monitor_instances():
                result = result and False
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Vm uuid %s exists in op server..checking if exists in webui as well" % (ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[2].text == ops_uuid:
                    self.logger.info(
                        "Vm uuid %s matched in webui..going to match basic view details..." % (ops_uuid))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vm_name = rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text
                    break
            if not match_flag:
                self.logger.error(
                    "Uuid exists in opserver but uuid %s not found in webui..." % (ops_uuid))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_monitor_instances_basic(match_index)
                self.logger.info(
                    "Click and retrieve basic view details in webui for uuid %s " % (ops_uuid))
                dom_arry_basic = self.webui_common.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                elements = self.browser.find_element_by_xpath(
                    "//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')
                len_elements = len(elements)
                vm_ops_data = self.webui_common.get_details(
                    vm_list_ops[k]['href'])
                complete_ops_data = []
                if vm_ops_data and vm_ops_data.has_key('UveVirtualMachineAgent'):
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
                                # if index ==  0:
                                #    floating_ip = element.get('ip_address') + ' (' +  element.get('virtual_network') + ')'
                                # else:
                                #    floating_ip = floating_ip + ' , ' + element.get('ip_address') + ' (' +  element.get('virtual_network') + ')'
                            #ops_data_interface_list[k]['floating_ips'] = floating_ip
                        modified_ops_data_interface_list = []
                        self.webui_common.extract_keyvalue(
                            ops_data_interface_list[k], modified_ops_data_interface_list)
                        complete_ops_data = complete_ops_data + \
                            modified_ops_data_interface_list
                        for t in range(len(complete_ops_data)):
                            if type(complete_ops_data[t]['value']) is list:
                                for m in range(len(complete_ops_data[t]['value'])):
                                    complete_ops_data[t]['value'][m] = str(
                                        complete_ops_data[t]['value'][m])
                            elif type(complete_ops_data[t]['value']) is unicode:
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
                if self.webui_common.match_ops_values_with_webui(complete_ops_data, dom_arry_intf):
                    self.logger.info(
                        "Ops vm uves basic view data matched in webui")
                else:
                    self.logger.error(
                        "Ops vm uves basic data match failed in webui")
                    result = result and False
        return result
    # end verify_vm_ops_basic_data_in_webui

    def verify_dashboard_details(self):
        self.logger.info("Verifying dashboard details...")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_dashboard():
            result = result and False
        dashboard_node_details = self.browser.find_element_by_id(
            'topStats').find_elements_by_class_name('infobox-data-number')
        dashboard_data_details = self.browser.find_element_by_id(
            'sparkLineStats').find_elements_by_class_name('infobox-data-number')
        dashboard_system_details = self.browser.find_element_by_id(
            'system-info-stat').find_elements_by_tag_name('li')
        servers_ver = self.webui_common.find_element(
            self.browser, ['system-info-stat', 'value'], ['id', 'class'], [1])
        servers = servers_ver[0].text
        version = servers_ver[1].text
        dom_data = []
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
        dom_data.append({'key': dashboard_system_details[0].find_element_by_class_name(
            'key').text, 'value': dashboard_system_details[0].find_element_by_class_name('value').text})
        dom_data.append({'key': dashboard_system_details[1].find_element_by_class_name(
            'key').text, 'value': dashboard_system_details[1].find_element_by_class_name('value').text})
        ops_servers = str(len(self.webui_common.get_config_nodes_list_ops()))
        ops_version = self.webui_common.get_version()
        self.webui_common.append_to_list(
            dom_data, [('servers', servers), ('version', version)])
        ops_dashborad_data = []
        if not self.webui_common.click_configure_networks():
            result = result and False
        rows = self.webui_common.get_rows()
        vrouter_total_vm = str(len(self.webui_common.get_vm_list_ops()))
        total_vrouters = str(len(self.webui_common.get_vrouters_list_ops()))
        total_control_nodes = str(
            len(self.webui_common.get_bgp_routers_list_ops()))
        total_analytics_nodes = str(
            len(self.webui_common.get_collectors_list_ops()))
        total_config_nodes = str(
            len(self.webui_common.get_config_nodes_list_ops()))
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        interface_count = 0
        vrouter_total_vn = 0
        for index in range(len(vrouters_list_ops)):
            vrouters_ops_data = self.webui_common.get_details(
                vrouters_list_ops[index]['href'])
            if vrouters_ops_data.get('VrouterAgent').get('total_interface_count'):
                interface_count = interface_count + \
                    vrouters_ops_data.get('VrouterAgent').get(
                        'total_interface_count')
            if vrouters_ops_data.get('VrouterAgent').get('connected_networks'):
                vrouter_total_vn = vrouter_total_vn + \
                    (len(vrouters_ops_data.get('VrouterAgent')
                     .get('connected_networks')))

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
        self.webui_common.append_to_list(
            ops_dashborad_data, [('servers', ops_servers), ('version', ops_version)])
        result = True
        if self.webui_common.match_ops_with_webui(ops_dashborad_data, dom_data):
            self.logger.info("Monitor dashborad details matched")
        else:
            self.logger.error("Monitor dashborad details not matched")
            result = result and False
        return result
    # end verify_dashboard_details_in_webui

    def verify_vn_ops_basic_data(self):
        self.logger.info("Verifying VN basic ops-data in Webui...")
        self.logger.debug(self.dash)
        error = 0
        if not self.webui_common.click_monitor_networks():
            result = result and False
        rows = self.webui_common.get_rows()
        vn_list_ops = self.webui_common.get_vn_list_ops()
        for k in range(len(vn_list_ops)):
            ops_fq_name = vn_list_ops[k]['name']
            if not self.webui_common.click_monitor_networks():
                result = result and False
            rows = self.browser.find_element_by_class_name('grid-canvas')
            rows = self.webui_common.get_rows(rows)
            self.logger.info(
                "Vn fq_name %s exists in op server..checking if exists in webui as well" % (ops_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[1].text == ops_fq_name:
                    self.logger.info(
                        "Vn fq_name %s matched in webui..going to match basic view details..." % (ops_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[i].find_elements_by_class_name(
                        'slick-cell')[1].text
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fq_name exists in opserver but %s not found in webui..." % (ops_fq_name))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_monitor_networks_basic(match_index)
                self.logger.info(
                    "Click and retrieve basic view details in webui for VN fq_name %s " % (ops_fq_name))
                # get vn basic details excluding basic interface details
                dom_arry_basic = self.webui_common.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                elements = self.browser.find_element_by_xpath(
                    "//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')
                len_elements = len(elements)
                vn_ops_data = self.webui_common.get_details(
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
                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    # creating a list of basic view items retrieved from
                    # opserver
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkAgent')
                    if ops_data_basic.get('ingress_flow_count'):
                        ops_data_ingress = {'key': 'ingress_flow_count',
                                            'value': ops_data_basic.get('ingress_flow_count')}
                    if ops_data_basic.get('egress_flow_count'):
                        ops_data_egress = {'key': 'egress_flow_count',
                                           'value': ops_data_basic.get('egress_flow_count')}
                    if ops_data_basic.get('total_acl_rules'):
                        ops_data_acl_rules = {
                            'key': 'total_acl_rules', 'value': ops_data_basic.get('total_acl_rules')}
                    if ops_data_basic.get('interface_list'):
                        ops_data_interfaces_count = {
                            'key': 'interface_list_count', 'value': len(ops_data_basic.get('interface_list'))}
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
                        ops_data_instances = {'key': 'virtualmachine_list', 'value': ', '.join(
                            ops_data_basic.get('virtualmachine_list'))}
                        complete_ops_data.append(ops_data_instances)
                complete_ops_data.extend(
                    [ops_data_ingress, ops_data_egress, ops_data_acl_rules, ops_data_interfaces_count])
                if ops_fq_name.find('__link_local__') != -1 or ops_fq_name.find('default-virtual-network') != -1 or ops_fq_name.find('ip-fabric') != -1:
                    for i, item in enumerate(complete_ops_data):
                        if complete_ops_data[i]['key'] == 'vrf_stats_list':
                            del complete_ops_data[i]
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkConfig')
                    if ops_data_basic.get('attached_policies'):
                        ops_data_policies = ops_data_basic.get(
                            'attached_policies')
                        if ops_data_policies:
                            pol_name_list = [pol['vnp_name']
                                             for pol in ops_data_policies]
                            pol_list_joined = ', '.join(pol_name_list)
                            ops_data_policies = {
                                'key': 'attached_policies', 'value': pol_list_joined}
                            complete_ops_data.extend([ops_data_policies])
                    for t in range(len(complete_ops_data)):
                        if type(complete_ops_data[t]['value']) is list:
                            for m in range(len(complete_ops_data[t]['value'])):
                                complete_ops_data[t]['value'][m] = str(
                                    complete_ops_data[t]['value'][m])
                        elif type(complete_ops_data[t]['value']) is unicode:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                        else:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])

                if self.webui_common.match_ops_values_with_webui(complete_ops_data, dom_arry_basic):
                    self.logger.info(
                        "Ops uves virutal networks basic view data matched in webui")

                else:
                    self.logger.error(
                        "Ops uves virutal networks  basic view data match failed in webui")
                    error = 1
        return not error
    # end verify_vn_ops_basic_data_in_webui

    def verify_config_nodes_ops_advance_data(self):
        self.logger.info(
            "Verifying config_nodes ops-data in Webui monitor->infra->Config Nodes->details(advance view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_config_nodes():
            result = result and False
        rows = self.webui_common.get_rows()
        config_nodes_list_ops = self.webui_common.get_config_nodes_list_ops()
        result = True
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info(
                "Config node host name %s exists in op server..checking if exists in webui as well" %
                (ops_config_node_name))
            if not self.webui_common.click_monitor_config_nodes():
                result = result and False
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_config_node_name:
                    self.logger.info(
                        "Config node name %s found in webui..going to match advance view details..." % (ops_config_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag:
                self.logger.error(
                    "Config node name %s did not match in webui...not found in webui" %
                    (ops_config_node_name))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve config nodes advance view details in webui for config node-name %s " %
                    (ops_config_node_name))
                self.webui_common.click_monitor_config_nodes_advance(
                    match_index)
                config_nodes_ops_data = self.webui_common.get_details(
                    config_nodes_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num:
                    dom_arry_num_new.append(
                        {'key': item['key'].replace('\\', '"').replace(' ', ''), 'value': item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if config_nodes_ops_data.has_key('ModuleCpuState'):
                    ops_data = config_nodes_ops_data['ModuleCpuState']
                    history_del_list = [
                        'api_server_mem_virt', 'service_monitor_cpu_share', 'schema_xmer_mem_virt',
                        'service_monitor_mem_virt', 'api_server_cpu_share', 'schema_xmer_cpu_share']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(
                        ops_data, modified_ops_data)
                    complete_ops_data = modified_ops_data
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list:
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(
                            "Ops uves config nodes advance view data matched in webui")
                    else:
                        self.logger.error(
                            "Ops uves config nodes advance view data match failed in webui")
                        result = result and False
        return result
    # end verify_config_nodes_ops_advance_data_in_webui

    def verify_vn_ops_advance_data(self):
        self.logger.info(
            "Verifying VN advance ops-data in Webui monitor->Networking->Networks Summary(basic view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_networks():
            result = result and False
        rows = self.webui_common.get_rows()
        vn_list_ops = self.webui_common.get_vn_list_ops()
        result = True
        for n in range(len(vn_list_ops)):
            ops_fqname = vn_list_ops[n]['name']
            self.logger.info(
                "Vn fq name %s exists in op server..checking if exists in webui as well" % (ops_fqname))
            if not self.webui_common.click_monitor_networks():
                result = result and False
            rows = self.browser.find_element_by_class_name('grid-canvas') 
            rows = self.webui_common.get_rows(rows)
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[1].text == ops_fqname:
                    self.logger.info(
                        "Vn fq name %s found in webui..going to match advance view details..." % (ops_fqname))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fqname %s did not match in webui...not found in webui" % (ops_fqname))
                self.logger.debug(self.dash)
            else:
                self.logger.info(
                    "Click and retrieve advance view details in webui for fqname %s " % (ops_fqname))
                self.webui_common.click_monitor_networks_advance(match_index)
                vn_ops_data = self.webui_common.get_details(
                    vn_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                merged_arry = dom_arry + dom_arry_str
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data = vn_ops_data['UveVirtualNetworkConfig']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(
                        ops_data, modified_ops_data)

                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    ops_data_agent = vn_ops_data['UveVirtualNetworkAgent']
                    if 'udp_sport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_sport_bitmap']
                    if 'udp_dport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_dport_bitmap']
                    self.logger.info(
                        "VN details for %s  got from  ops server and going to match in webui : \n %s \n " %
                        (vn_list_ops[i]['href'], ops_data_agent))
                    modified_ops_data_agent = []
                    self.webui_common.extract_keyvalue(
                        ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + \
                        modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list:
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(
                                    complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] = str(
                                complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(
                            "Ops uves virtual networks advance view data matched in webui")
                    else:
                        self.logger.error(
                            "Ops uves virtual networks advance view data match failed in webui")
                        result = result and False
        return result
    # end verify_vn_ops_advance_data_in_webui

    def verify_vm_ops_advance_data(self):
        self.logger.info(
            "Verifying VM ops-data in Webui monitor->Networking->instances->Instances summary(Advance view)......")
        self.logger.debug(self.dash)
        if not self.webui_common.click_monitor_instances():
            result = result and False
        rows = self.webui_common.get_rows()
        vm_list_ops = self.webui_common.get_vm_list_ops()
        result = True
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            if not self.webui_common.click_monitor_instances():
                result = result and False
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Vm uuid %s exists in op server..checking if exists in webui as well" % (ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[2].text == ops_uuid:
                    self.logger.info(
                        "Vm uuid %s matched in webui..going to match advance view details..." % (ops_uuid))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag:
                self.logger.error(
                    "Uuid exists in opserver but uuid %s not found in webui..." % (ops_uuid))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_monitor_instances_advance(match_index)
                self.logger.info(
                    "Click and retrieve advance view details in webui for uuid %s " % (ops_uuid))
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = []
                dom_arry_str = self.webui_common.get_advanced_view_str()
                merged_arry = dom_arry + dom_arry_str
                vm_ops_data = self.webui_common.get_details(
                    vm_list_ops[k]['href'])
                if vm_ops_data and vm_ops_data.has_key('UveVirtualMachineAgent'):
                    ops_data = vm_ops_data['UveVirtualMachineAgent']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(
                        ops_data, modified_ops_data)
                    complete_ops_data = modified_ops_data
                    for t in range(len(complete_ops_data)):
                        if type(complete_ops_data[t]['value']) is list:
                            for m in range(len(complete_ops_data[t]['value'])):
                                complete_ops_data[t]['value'][m] = str(
                                    complete_ops_data[t]['value'][m])
                        elif type(complete_ops_data[t]['value']) is unicode:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                        else:
                            complete_ops_data[t]['value'] = str(
                                complete_ops_data[t]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(
                            "Ops vm uves advance view data matched in webui")
                    else:
                        self.logger.error(
                            "Ops vm uves advance data match failed in webui")
                        result = result and False
        return result
    # end verify_vm_ops_advance_data_in_webui

    def verify_vn_api_data(self):
        self.logger.info(
            "Verifying VN api details in Webui config networks...")
        self.logger.debug(self.dash)
        result = True
        vn_list_api = self.webui_common.get_vn_list_api()
        for vns in range(len(vn_list_api['virtual-networks']) - 3):
            pol_list = []
            pol_list1 = []
            ip_block_list = []
            ip_block = []
            pool_list = []
            floating_pool = []
            route_target_list = []
            host_route_main = []
            api_fq_name = vn_list_api['virtual-networks'][vns]['fq_name'][2]
            self.webui_common.click_configure_networks()
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Vn fq_name %s exists in api server..checking if exists in webui as well" % (api_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                dom_arry_basic = []
                if rows[i].find_elements_by_tag_name('div')[2].text == api_fq_name:
                    self.logger.info(
                        "Vn fq_name %s matched in webui..going to match basic view details..." % (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[
                        i].find_elements_by_tag_name('div')[2].text
                    policies = rows[i].find_elements_by_tag_name(
                        'div')[3].text.splitlines()
                    dom_arry_basic.append(
                        {'key': 'Attached Policies', 'value': policies})
                    dom_arry_basic.append(
                        {'key': 'Network', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    dom_arry_basic.append(
                        {'key': 'ip_blocks_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[4].text.split()})
                    break
            if not match_flag:
                self.logger.error(
                    "Vn fq_name exists in apiserver but %s not found in webui..." % (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_configure_networks_basic(match_index)
                rows = self.webui_common.get_rows()
                self.logger.info(
                    "Click and retrieve basic view details in webui for VN fq_name %s " % (api_fq_name))
                rows_detail = rows[
                    match_index + 1].find_element_by_class_name('slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_tag_name('label')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[detail].text
                    if text1 == 'Attached Network Policies':
                        poli = str(rows_detail[detail].find_element_by_xpath('..').text).replace(
                            text1, '').strip().split()
                        dom_arry_basic.append(
                            {'key': str(rows_detail[detail].text), 'value': poli})
                    elif text1 == 'IP Blocks' or text1 == 'Host Routes':
                        dom_arry_basic.append({'key': str(text1), 'value': str(
                            rows_detail[detail].find_element_by_xpath('..').text).replace(text1, '').strip().splitlines()})
                    elif text1 == 'Floating IP Pools':
                        pools = rows_detail[detail].find_element_by_xpath(
                            '..').text.replace(text1, '').strip().splitlines()
                        for pool in range(len(pools)):
                            pool_list.append(pools[pool].split()[0])
                        dom_arry_basic.append(
                            {'key': text1, 'value': pool_list})
                    elif text1 == 'Route Targets':
                        dom_arry_basic.append({'key': str(text1), 'value': str(
                            rows_detail[detail].find_element_by_xpath('..').text).replace(text1, '').strip().split(', ')})
                    else:
                        dom_arry_basic.append({'key': str(text1), 'value': str(
                            rows_detail[detail].find_element_by_xpath('..').text).replace(text1, '').strip()})
                vn_api_data = self.webui_common.get_details(
                    vn_list_api['virtual-networks'][vns]['href'])
                complete_api_data = []
                if vn_api_data.has_key('virtual-network'):
                    api_data_basic = vn_api_data.get('virtual-network')
                if api_data_basic.get('name'):
                    complete_api_data.append(
                        {'key': 'Network', 'value': api_data_basic['name']})
                if api_data_basic.has_key('network_policy_refs'):
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
                if api_data_basic.has_key('network_ipam_refs'):
                    for ip in range(len(api_data_basic['network_ipam_refs'])):
                        dom_arry_basic.append(
                            {'key': 'Attached Policies', 'value': rows[i].find_elements_by_tag_name('div')[3].text.split()})
                        if(api_data_basic['network_ipam_refs'][ip]['to'][2]) == 'default-network-ipam':
                            for ip_sub in range(len(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'])):
                                ip_block_list.append(str(api_data_basic['network_ipam_refs'][ip]['to'][0] + ':' + api_data_basic['network_ipam_refs'][ip]['to'][1] + ':' + api_data_basic['network_ipam_refs'][ip]['to'][2]) + ' ' + str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets']
                                                     [ip_sub]['subnet']['ip_prefix']) + '/' + str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'][ip_sub]['subnet']['ip_prefix_len']) + ' ' + str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'][ip_sub]['default_gateway']))

                        else:
                            for ip_sub1 in range(len(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'])):
                                ip_block_list.append(str(api_data_basic['network_ipam_refs'][ip]['to'][2]) + ' ' + str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'][ip_sub1]['subnet']['ip_prefix']) + '/' +
                                                     str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'][ip_sub1]['subnet']['ip_prefix_len']) + ' ' + str(api_data_basic['network_ipam_refs'][ip]['attr']['ipam_subnets'][ip_sub1]['default_gateway']))
                    if len(ip_block_list) > 2:
                        for ips in range(2):
                            ip_block.append(ip_block_list[ips].split()[1])
                        ip_string = '(' + \
                            str(len(ip_block_list) - 2) + ' more)'
                        ip_block.append(ip_string)
                    else:
                        for ips in range(len(ip_block_list)):
                            ip_block.append(ip_block_list[ips].split()[1])
                    complete_api_data.append(
                        {'key': 'IP Blocks', 'value': ip_block_list})
                    complete_api_data.append(
                        {'key': 'ip_blocks_grid_row', 'value': ip_block})
                if api_data_basic.has_key('route_target_list'):
                    if api_data_basic['route_target_list'].has_key('route_target'):
                        for route in range(len(api_data_basic['route_target_list']['route_target'])):
                            route_target_list.append(
                                str(api_data_basic['route_target_list']['route_target'][route]).strip('target:'))
                        complete_api_data.append(
                            {'key': 'Route Targets', 'value': route_target_list})
                if api_data_basic.has_key('floating_ip_pools'):
                    for fip in range(len(api_data_basic['floating_ip_pools'])):
                        floating_pool.append(
                            str(api_data_basic['floating_ip_pools'][fip]['to'][3]))
                    complete_api_data.append(
                        {'key': 'Floating IP Pools', 'value': floating_pool})
                if api_data_basic.has_key('network_ipam_refs'):
                    for ipams in range(len(api_data_basic['network_ipam_refs'])):
                        if api_data_basic['network_ipam_refs'][ipams]['attr'].get('host_routes'):

                            if api_data_basic['network_ipam_refs'][ipams]['to'][2] == 'default-network-ipam':
                                host_route_sub = []
                                for host_route in range(len(api_data_basic['network_ipam_refs'][ipams]['attr']['host_routes']['route'])):
                                    host_route_sub.append(
                                        str(api_data_basic['network_ipam_refs'][ipams]['attr']['host_routes']['route'][host_route]['prefix']))
                                host_route_string = ",".join(host_route_sub)

                                host_route_main.append(str(api_data_basic['network_ipam_refs'][ipams]['to'][
                                                       0] + ':' + api_data_basic['network_ipam_refs'][ipams]['to'][1] + ':' + api_data_basic['network_ipam_refs'][ipams]['to'][2]) + ' ' + host_route_string)
                            else:
                                host_route_sub = []
                                for host_route1 in range(len(api_data_basic['network_ipam_refs'][ipams]['attr']['host_routes']['route'])):
                                    host_route_sub.append(
                                        str(api_data_basic['network_ipam_refs'][ipams]['attr']['host_routes']['route'][host_route1]['prefix']))
                                host_route_string = ", ".join(host_route_sub)
                                host_route_main.append(
                                    str(api_data_basic['network_ipam_refs'][ipams]['to'][2]) + ' ' + host_route_string)
                    if(len(host_route_main) > 0):
                        complete_api_data.append(
                            {'key': 'Host Routes', 'value': host_route_main})
                if api_data_basic['virtual_network_properties'].has_key('forwarding_mode'):
                    forwarding_mode = api_data_basic[
                        'virtual_network_properties']['forwarding_mode']
                    if forwarding_mode == 'l2':
                        forwarding_mode = forwarding_mode.title() + ' Only'
                    else:
                        forwarding_mode = 'L2 and L3'
                    complete_api_data.append(
                        {'key': 'Forwarding Mode', 'value': forwarding_mode})
                if api_data_basic['virtual_network_properties'].has_key('vxlan_network_identifier'):
                    complete_api_data.append({'key': 'VxLAN Identifier', 'value': str(
                        api_data_basic['virtual_network_properties']['vxlan_network_identifier']).replace('None', 'Automatic')})
                if self.webui_common.match_ops_with_webui(complete_api_data, dom_arry_basic):
                    self.logger.info(
                        "Api virutal networks details matched in webui config networks")
                else:
                    self.logger.error(
                        "Api virutal networks details not match in webui config networks")
                    result = result and False
        return result
    # end verify_vn_api_basic_data_in_webui

    def verify_service_template_api_basic_data(self):
        self.logger.info("Verifying service template api-data in Webui...")
        self.logger.debug(self.dash)
        result = True
        service_temp_list_api = self.webui_common.get_service_template_list_api(
        )
        for temp in range(len(service_temp_list_api['service-templates']) - 1):
            interface_list = []
            api_fq_name = service_temp_list_api[
                'service-templates'][temp + 1]['fq_name'][1]
            self.webui_common.click_configure_service_template()
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Service template fq_name %s exists in api server..checking if exists in webui as well" % (api_fq_name))
            for i in range(len(rows)):
                dom_arry_basic = []
                match_flag = 0
                j = 0
                if rows[i].find_elements_by_tag_name('div')[2].text == api_fq_name:
                    self.logger.info(
                        "Service template fq_name %s matched in webui..going to match basic view details..." % (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    dom_arry_basic.append(
                        {'key': 'Name_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    dom_arry_basic.append(
                        {'key': 'Mode_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[3].text})
                    dom_arry_basic.append(
                        {'key': 'Type_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[4].text})
                    dom_arry_basic.append(
                        {'key': 'Scaling_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[5].text})
                    dom_arry_basic.append(
                        {'key': 'Interface_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[6].text})
                    dom_arry_basic.append(
                        {'key': 'Image_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[7].text})
                    dom_arry_basic.append(
                        {'key': 'Flavor_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[8].text})
                    break
            if not match_flag:
                self.logger.error(
                    "Service template fq_name exists in apiserver but %s not found in webui..." % (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_configure_service_template_basic(
                    match_index)
                rows = self.webui_common.get_rows()
                self.logger.info(
                    "Click and retrieve basic view details in webui for service templatefq_name %s " % (api_fq_name))
                rows_detail = rows[
                    match_index + 1].find_element_by_class_name('slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'Interface Type':
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': rows_detail[detail].find_element_by_class_name('span10').text})
                    else:
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': rows_detail[detail].find_element_by_class_name('span10').text})

                service_temp_api_data = self.webui_common.get_details(
                    service_temp_list_api['service-templates'][temp + 1]['href'])
                complete_api_data = []
                if service_temp_api_data.has_key('service-template'):
                    api_data_basic = service_temp_api_data.get(
                        'service-template')
                if api_data_basic.has_key('fq_name'):
                    complete_api_data.append(
                        {'key': 'Template', 'value': str(api_data_basic['fq_name'][1])})
                    complete_api_data.append(
                        {'key': 'Name_grid_row', 'value': str(api_data_basic['fq_name'][1])})
                if api_data_basic['service_template_properties'].has_key('service_mode'):
                    complete_api_data.append({'key': 'Mode', 'value': str(
                        api_data_basic['service_template_properties']['service_mode']).capitalize()})
                    complete_api_data.append({'key': 'Mode_grid_row', 'value': str(
                        api_data_basic['service_template_properties']['service_mode']).capitalize()})
                if api_data_basic['service_template_properties'].has_key('service_type'):
                    complete_api_data.append({'key': 'Type', 'value': str(
                        api_data_basic['service_template_properties']['service_type']).title()})
                    complete_api_data.append({'key': 'Type_grid_row', 'value': str(
                        api_data_basic['service_template_properties']['service_type']).title()})
                if api_data_basic['service_template_properties'].has_key('service_scaling'):
                    if api_data_basic['service_template_properties']['service_scaling'] == True:
                        complete_api_data.append({'key': 'Scaling', 'value': str(
                            api_data_basic['service_template_properties']['service_scaling']).replace('True', 'Enabled')})
                        complete_api_data.append({'key': 'Scaling_grid_row', 'value': str(
                            api_data_basic['service_template_properties']['service_scaling']).replace('True', 'Enabled')})
                    else:
                        complete_api_data.append({'key': 'Scaling', 'value': str(
                            api_data_basic['service_template_properties']['service_scaling']).replace('False', 'Disabled')})
                        complete_api_data.append({'key': 'Scaling_grid_row', 'value': str(
                            api_data_basic['service_template_properties']['service_scaling']).replace('False', 'Disabled')})
                if api_data_basic['service_template_properties'].has_key('interface_type'):
                    for interface in range(len(api_data_basic['service_template_properties']['interface_type'])):
                        if api_data_basic['service_template_properties']['interface_type'][interface]['shared_ip'] == True and api_data_basic['service_template_properties']['interface_type'][interface]['static_route_enable'] == True:
                            interface_type = api_data_basic['service_template_properties']['interface_type'][
                                interface]['service_interface_type'].title() + '(' + 'Shared IP' + ', ' + 'Static Route' + ')'
                        elif api_data_basic['service_template_properties']['interface_type'][interface]['shared_ip'] == False and api_data_basic['service_template_properties']['interface_type'][interface]['static_route_enable'] == True:
                            interface_type = api_data_basic['service_template_properties']['interface_type'][
                                interface]['service_interface_type'].title() + '(' + 'Static Route' + ')'
                        elif api_data_basic['service_template_properties']['interface_type'][interface]['shared_ip'] == True and api_data_basic['service_template_properties']['interface_type'][interface]['static_route_enable'] == False:
                            interface_type = api_data_basic['service_template_properties']['interface_type'][
                                interface]['service_interface_type'].title() + '(' + 'Shared IP' + ')'
                        else:
                            interface_type = api_data_basic['service_template_properties'][
                                'interface_type'][interface]['service_interface_type'].title()

                        interface_list.append(interface_type)
                        interface_string = ", ".join(interface_list)
                    complete_api_data.append(
                        {'key': 'Interface Type', 'value': interface_string})
                    complete_api_data.append(
                        {'key': 'Interface_grid_row', 'value': interface_string})
                if api_data_basic['service_template_properties'].has_key('image_name'):
                    complete_api_data.append(
                        {'key': 'Image', 'value': str(api_data_basic['service_template_properties']['image_name'])})
                    complete_api_data.append({'key': 'Image_grid_row', 'value': str(
                        api_data_basic['service_template_properties']['image_name'])})
                if api_data_basic.has_key('service_instance_back_refs'):
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
                if api_data_basic['service_template_properties'].has_key('flavor'):
                    complete_api_data.append(
                        {'key': 'Flavor', 'value': str(api_data_basic['service_template_properties']['flavor'])})
                    complete_api_data.append({'key': 'Flavor_grid_row', 'value': str(
                        api_data_basic['service_template_properties']['flavor'])})
                if self.webui_common.match_ops_with_webui(complete_api_data, dom_arry_basic):
                    self.logger.info(
                        "Api service templates details matched in webui")
                else:
                    self.logger.error(
                        "Api uves service templates details match failed in webui")
                    result = result and False
        return result
    # end verify_service_template_api_basic_data_in_webui

    def verify_floating_ip_api_data(self):
        self.logger.info("Verifying FIP api-data in Webui...")
        self.logger.info(self.dash)
        result = True
        fip_list_api = self.webui_common.get_fip_list_api()
        for fips in range(len(fip_list_api['floating-ips'])):
            api_fq_id = fip_list_api['floating-ips'][fips]['uuid']
            self.webui_common.click_configure_fip()
            project_name = fip_list_api.get('floating-ips')[fips].get('fq_name')[1]
            self.webui_common.select_project(project_name)
            rows = self.webui_common.get_rows()
            self.logger.info(
                "fip fq_id %s exists in api server..checking if exists in webui as well" % (api_fq_id))
            for i in range(len(rows)):
                match_flag = 0
                j = 0
                if rows[i].find_elements_by_tag_name('div')[4].text == api_fq_id:
                    self.logger.info(
                        "fip fq_id %s matched in webui..going to match basic view details now" % (api_fq_id))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    dom_arry_basic = []
                    dom_arry_basic.append(
                        {'key': 'IP Address', 'value': rows[i].find_elements_by_tag_name('div')[1].text})
                    dom_arry_basic.append(
                        {'key': 'Instance', 'value': rows[i].find_elements_by_tag_name('div')[2].text})
                    dom_arry_basic.append(
                        {'key': 'Floating IP and Pool', 'value': rows[i].find_elements_by_tag_name('div')[3].text})
                    dom_arry_basic.append(
                        {'key': 'UUID', 'value': rows[i].find_elements_by_tag_name('div')[4].text})
                    break
            if not match_flag:
                self.logger.error(
                    "fip fq_id exists in apiserver but %s not found in webui..." % (api_fq_id))
                self.logger.info(self.dash)
            else:
                fip_api_data = self.webui_common.get_details(
                    fip_list_api['floating-ips'][fips]['href'])
                complete_api_data = []
                if fip_api_data.has_key('floating-ip'):
                    # creating a list of basic view items retrieved from
                    # opserver
                    api_data_basic = fip_api_data.get('floating-ip')
                if api_data_basic.get('floating_ip_address'):
                    complete_api_data.append(
                        {'key': 'IP Address', 'value': api_data_basic['floating_ip_address']})
                if api_data_basic.get('virtual_machine_interface_refs'):
                    vm_api_data = self.webui_common.get_details(
                        api_data_basic['virtual_machine_interface_refs'][0]['href'])
                    if vm_api_data.has_key('virtual-machine-interface'):
                        if vm_api_data['virtual-machine-interface'].get('virtual_machine_refs'):
                            complete_api_data.append(
                                {'key': 'Instance', 'value': vm_api_data['virtual-machine-interface']['virtual_machine_refs'][0]['to']})
                else:
                    complete_api_data.append(
                        {'key': 'Instance', 'value': '-'})
                if api_data_basic.get('fq_name'):
                    complete_api_data.append(
                        {'key': 'Floating IP and Pool', 'value': api_data_basic['fq_name'][2] + ':' + api_data_basic['fq_name'][3]})
                if api_data_basic.get('fq_name'):
                    complete_api_data.append(
                        {'key': 'UUID', 'value': api_data_basic['fq_name'][4]})
                if self.webui_common.match_ops_with_webui(complete_api_data, dom_arry_basic):
                    self.logger.info("api fip data matched in webui")
                else:
                    self.logger.error("api fip data match failed in webui")
                    result = False
        return result
    # end verify_floating_ip_api_data_in_webui

    def verify_policy_api_data(self):
        self.logger.info("Verifying policy details in Webui...")
        self.logger.debug(self.dash)
        result = True
        policy_list_api = self.webui_common.get_policy_list_api()
        for policy in range(len(policy_list_api['network-policys']) - 1):
            pol_list = []
            net_list = []
            service_list = []
            api_fq_name = policy_list_api[
                'network-policys'][policy]['fq_name'][2]
            project_name = policy_list_api[
                'network-policys'][policy]['fq_name'][1]
            self.webui_common.click_configure_policies()
            self.webui_common.select_project(project_name)
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Policy fq_name %s exists in api server..checking if exists in webui as well" % (api_fq_name))
            for i in range(len(rows)):
                dom_arry_basic = []
                match_flag = 0
                detail = 0
                if rows[i].find_elements_by_tag_name('div')[2].text == api_fq_name:
                    self.logger.info(
                        "Policy fq_name %s matched in webui..going to match basic view details..." % (api_fq_name))
                    self.logger.debug(self.dash)
                    match_index = i
                    match_flag = 1
                    dom_arry_basic.append(
                        {'key': 'Policy', 'value':  rows[i].find_elements_by_tag_name('div')[2].text})
                    net_grid_row_value = rows[i].find_elements_by_tag_name('div')[3].text.splitlines()
                    dom_arry_basic.append({'key':'Associated_Networks_grid_row','value': net_grid_row_value})                    
                    dom_arry_basic.append(
                        {'key': 'Rules_grid_row', 'value': rows[i].find_elements_by_tag_name('div')[4].text.splitlines()})
                    break
            if not match_flag:
                self.logger.error(
                    "Policy fq_name exists in apiserver but %s not found in webui..." % (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_configure_policies_basic(match_index)
                rows = self.webui_common.get_rows()
                self.logger.info(
                    "Click and retrieve basic view details in webui for policy fq_name %s " % (api_fq_name))
                rows_detail = rows[
                    match_index + 1].find_element_by_class_name('slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                while(detail < len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'Associated Networks':
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': rows_detail[detail].find_element_by_class_name('span11').text.split()})
                    elif text1 == 'Rules':
                        dom_arry_basic.append({'key': str(text1), 'value': rows_detail[
                                              detail].find_element_by_class_name('span11').text.splitlines()})
                    detail = detail + 2
                policy_api_data = self.webui_common.get_details(
                    policy_list_api['network-policys'][policy]['href'])
                complete_api_data = []
                if policy_api_data.has_key('network-policy'):
                    api_data_basic = policy_api_data.get('network-policy')
                if api_data_basic.has_key('fq_name'):
                    complete_api_data.append(
                        {'key': 'Policy', 'value': api_data_basic['fq_name'][2]})
                if api_data_basic.has_key('virtual_network_back_refs'):
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
                    if  net_list_len > 2 :
                        net_list_grid_row = net_list[:2]
                        more_string = '(' + str(net_list_len-2) + ' more)'
                        net_list_grid_row.append(more_string)
                        complete_api_data.append({'key':'Associated_Networks_grid_row', 'value':net_list_grid_row})
                    else:
                       complete_api_data.append({'key':'Associated_Networks_grid_row', 'value':net_list})
                if api_data_basic.has_key('network_policy_entries'):
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
                        if type(desti_port) is list:
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
                        if type(source_port) is list:
                            source_port = str(source_port)
                            source_port = '[ ' + source_port[1:-1] + ' ]'

                        api_src_vnet = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['src_addresses'][0]['virtual_network']
                        api_dst_vnet = api_data_basic['network_policy_entries'][
                            'policy_rule'][rules]['dst_addresses'][0]['virtual_network']
                        api_vnet_match_list = [
                            'default-domain:default-project:default-virtual-network', 'any',
                            'default-domain:default-project:__link_local__', 'default-domain:default-project:ip-fabric']
                        if api_src_vnet in api_vnet_match_list:
                            source_network = api_src_vnet
                        else:
                            source_network = api_src_vnet.split(':')[2]
                        if api_dst_vnet in api_vnet_match_list:
                            dest_network = api_dst_vnet
                        else:
                            dest_network = api_dst_vnet.split(':')[2]
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
                            policy_text = 'protocol' + ' ' + protocol + ' ' + 'network' + ' ' + source_network + ' ' + 'port' + ' ' + source_port + ' ' + \
                                direction + ' ' + 'network' + ' ' + dest_network + ' ' + 'port' + \
                                ' ' + desti_port + ' ' + \
                                'apply_service' + ' ' + service_string
                            pol_list.append(policy_text)
                        else:

                            policy_text = action_list['simple_action'] + ' ' + 'protocol' + ' ' + protocol + ' ' + 'network' + ' ' + source_network + \
                                ' ' + 'port' + ' ' + source_port + ' ' + direction + ' ' + \
                                'network' + ' ' + dest_network + \
                                ' ' + 'port' + ' ' + desti_port
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
                if self.webui_common.match_ops_with_webui(complete_api_data, dom_arry_basic):
                    self.logger.info("Api policy details matched in webui")
                else:
                    self.logger.error(
                        "Api policy details match failed in webui")
                    result = result and False
        return result
    # end verify_policy_api_basic_data_in_webui

    def verify_ipam_api_data(self):
        self.logger.info("Verifying ipam details in Webui...")
        self.logger.debug(self.dash)
        result = True
        ipam_list_api = self.webui_common.get_ipam_list_api()
        for ipam in range(len(ipam_list_api['network-ipams'])):
            net_list = []
            api_fq_name = ipam_list_api['network-ipams'][ipam]['fq_name'][2]
            project_name = ipam_list_api['network-ipams'][ipam]['fq_name'][1]
            if project_name == 'default-project':
                continue
            self.webui_common.click_configure_ipam()
            self.webui_common.select_project(project_name)
            rows = self.webui_common.get_rows()
            self.logger.info(
                "Ipam fq_name %s exists in api server..checking if exists in webui as well" % (api_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                j = 0
                dom_arry_basic = []
                if rows[i].find_elements_by_tag_name('div')[2].text == api_fq_name:
                    self.logger.info(
                        "Ipam fq_name %s matched in webui..going to match basic view details..." % (api_fq_name))
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
                    "Ipam fq_name exists in apiserver but %s not found in webui..." % (api_fq_name))
                self.logger.debug(self.dash)
            else:
                self.webui_common.click_configure_ipam_basic(match_index)
                rows = self.webui_common.get_rows()
                self.logger.info(
                    "Click and retrieve basic view details in webui for ipam fq_name %s " % (api_fq_name))
                rows_detail = rows[
                    match_index + 1].find_element_by_class_name('slick-row-detail-container').find_element_by_class_name('row-fluid').find_elements_by_class_name('row-fluid')
                for detail in range(len(rows_detail)):
                    text1 = rows_detail[
                        detail].find_element_by_tag_name('label').text
                    if text1 == 'IP Blocks':
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': rows_detail[detail].find_element_by_class_name('span10').text})
                    else:
                        dom_arry_basic.append(
                            {'key': str(text1), 'value': rows_detail[detail].find_element_by_class_name('span10').text})

                ipam_api_data = self.webui_common.get_details(
                    ipam_list_api['network-ipams'][ipam]['href'])
                complete_api_data = []
                if ipam_api_data.has_key('network-ipam'):
                    api_data_basic = ipam_api_data.get('network-ipam')
                if api_data_basic.has_key('fq_name'):
                    complete_api_data.append(
                        {'key': 'IPAM Name', 'value': str(api_data_basic['fq_name'][2])})
                    complete_api_data.append(
                        {'key': 'Name_grid_row', 'value': str(api_data_basic['fq_name'][2])})
                if api_data_basic.get('network_ipam_mgmt'):
                    if api_data_basic['network_ipam_mgmt'].get('ipam_dns_method'):
                        if api_data_basic['network_ipam_mgmt']['ipam_dns_method'] == 'default-dns-server':
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
                                {'key': 'DNS Server', 'value': 'Virtual DNS:' + ' ' + api_data_basic['network_ipam_mgmt']['ipam_dns_server']['virtual_dns_server_name']})
                            complete_api_data.append({'key': 'DNS_grid_row', 'value': 'Virtual DNS:' + ' ' +
                                                     api_data_basic['network_ipam_mgmt']['ipam_dns_server']['virtual_dns_server_name']})
                        elif api_data_basic['network_ipam_mgmt']['ipam_dns_method'] == 'tenant-dns-server':
                            dns_server_value = str(api_data_basic['network_ipam_mgmt']['ipam_dns_method']).split(
                                '-')[0].title() + ' ' + 'Managed' + ' ' + 'DNS' + ':' + ' ' + str(api_data_basic['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'][0])
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
                    if api_data_basic['network_ipam_mgmt'].get('dhcp_option_list'):
                        if api_data_basic['network_ipam_mgmt']['dhcp_option_list'].get('dhcp_option'):
                            if len(api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option']) > 1:
                                ntp_server_value = str(api_data_basic['network_ipam_mgmt']['dhcp_option_list'][
                                                       'dhcp_option'][0]['dhcp_option_value'])
                                complete_api_data.append({'key': 'Domain Name', 'value': str(
                                    api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][1]['dhcp_option_value'])})
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
                                complete_api_data.append({'key': 'Domain Name', 'value': str(
                                    api_data_basic['network_ipam_mgmt']['dhcp_option_list']['dhcp_option'][0]['dhcp_option_value'])})
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
                if api_data_basic.has_key('virtual_network_back_refs'):
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
                                fq + ' - ' + ip_prefix + '/' + ip_prefix_len + '(' + default_gateway + ')')
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
                if self.webui_common.match_ops_with_webui(complete_api_data, dom_arry_basic):
                    self.logger.info(
                        "Api uves ipam  basic view data matched in webui")
                else:
                    self.logger.error(
                        "Api uves ipam  basic view data match failed in webui")
                    result = result and False
        return result
    # end verify_ipam_api_data_in_webui

    def verify_vm_ops_data_in_webui(self, fixture):
        self.logger.info("Verifying VN %s ops-data in Webui..." %
                         (fixture.vn_name))
        vm_list = self.webui_common.get_vm_list_ops()

        if not self.webui_common.click_monitor_instances():
            result = result and False
        rows = self.webui_common.get_rows()
        if len(rows) != len(vm_list):
            self.logger.error(" VM count in webui and opserver not matched  ")
        else:
            self.logger.info(" VM count in webui and opserver matched")
        for i in range(len(vm_list)):
            vm_name = vm_list[i]['name']
    # end verify_vm_ops_data_in_webui

    def verify_vn_ops_data_in_webui(self, fixture):
        vn_list = self.webui_common.get_vn_list_ops(fixture)
        self.logger.info(
            "VN details for %s got from ops server and going to match in webui : " % (vn_list))
        if not self.webui_common.click_configure_networks():
            result = result and False
        rows = self.webui_common.get_rows()
        #rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln = len(vn_list)
        for i in range(ln):
            vn_name = vn_list[i]['name']
            details = self.webui_common.get_vn_details(vn_list[i]['href'])
            UveVirtualNetworkConfig
            if details.has_key('UveVirtualNetwokConfig'):
                total_acl_rules_ops
            if details.has_key('UveVirtualNetworkAgent'):
                UveVirtualNetworkAgent_dict = details['UveVirtualNetworkAgent']
                egress_flow_count_api = details[
                    'UveVirtualNetworkAgent']['egress_flow_count']
                ingress_flow_count_api = details[
                    'UveVirtualNetworkAgent']['ingress_flow_count']
                interface_list_count_api = len(
                    details['UveVirtualNetworkAgent']['interface_list_count'])
                total_acl_rules_count = details[
                    'UveVirtualNetworkAgent']['total_acl_rules']
                if self.webui_common.check_element_exists_by_xpath(row[j + 1], "//label[contains(text(), 'Ingress Flows')]"):
                    for n in range(floating_ip_length_api):
                        fip_api = details[
                            'virtual-network']['floating_ip_pools'][n]['to']
                        if fip_ui[n] == fip_api[3] + ' (' + fip_api[0] + ':' + fip_api[1] + ')':
                            self.logger.info(" Fip matched ")
            if not self.webui_common.click_monitor_networks():
                result = result and False
            for j in range(len(rows)):
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fq_name = rows[j].find_elements_by_tag_name('a')[1].text
                if(fq_name == vn_list[i]['name']):
                    self.logger.info(" %s VN verified in monitor page " %
                                     (fq_name))
                    rows[j].find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('a').click()
                    rows = self.webui_common.get_rows()
                    expanded_row = rows[
                        j + 1].find_element_by_class_name('inline row-fluid position-relative pull-right margin-0-5')
                    expanded_row.find_element_by_class_name(
                        'icon-cog icon-only bigger-110').click()
                    expanded_row.find_elements_by_tag_name('a')[1].click()
                    basicdetails_ui_data = rows[
                        j + 1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name("row-fluid")
                    ingress_ui = basicdetails_ui_data[0].text.split('\n')[1]
                    egress_ui = basicdetails_ui_data[1].text.split('\n')[1]
                    acl_ui = basicdetails_ui_data[2].text.split('\n')[1]
                    intf_ui = basicdetails_ui_data[3].text.split('\n')[1]
                    vrf_ui = basicdetails_ui_data[4].text.split('\n')[1]
                    break
                else:
                    self.logger.error(" %s VN not found in monitor page " %
                                      (fq_name))
            details = self.webui_common.get_vn_details_api(vn_list[i]['href'])
            j = 0
            for j in range(len(rows)):
                if not self.webui_common.click_monitor_networks():
                    result = result and False
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]):
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        self.logger.info("Ip blocks verified ")
                    rows[j].find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('a').click()
                    rows = self.webui_common.get_rows()
                    ui_ip_block = rows[
                        j + 1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(' ')[1] == ip_block and ui_ip_block.split(' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway']):
                        self.logger.info(
                            "Ip block and details matched in webui advance view details ")
                    else:
                        self.logger.error("Ip block not matched")
                    forwarding_mode = rows[
                        j + 1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan = rows[
                        j + 1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = {'l2_l3': 'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        self.logger.info(" Forwarding mode matched ")
                    else:
                        self.logger.error("Forwarding mode not matched ")
                    if details['virtual-network']['virtual_network_properties']['vxlan_network_identifier'] == None:
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
        self.browser.get_screenshot_as_file('vm_verify.png')
        if not self.webui_common.click_configure_networks():
            result = result and False
        time.sleep(2)
        rows = self.webui_common.get_rows()
        ln = len(rows)
        vn_flag = 0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('div')[2].get_attribute('innerHTML') == fixture.vn_name and rows[i].find_elements_by_tag_name(
                    'div')[4].text == fixture.vn_subnets[0]):
                vn_flag = 1
                rows[i].find_elements_by_tag_name(
                    'div')[0].find_element_by_tag_name('i').click()
                rows = self.webui_common.get_rows()
                ip_blocks = rows[
                    i + 1].find_element_by_class_name('span11').text.split('\n')[1]
                if (ip_blocks.split(' ')[0] == ':'.join(fixture.ipam_fq_name) and ip_blocks.split(' ')[1] == fixture.vn_subnets[0]):
                    self.logger.info(
                        "Vn name %s and ip block %s verified in configure page " %
                        (fixture.vn_name, fixture.vn_subnets))
                else:
                    self.logger.error(
                        "Ip block details failed to verify in configure page %s " % (fixture.vn_subnets))
                    self.browser.get_screenshot_as_file(
                        'Verify_vn_configure_page_ip_block.png')
                    vn_flag = 0
                break
        if not self.webui_common.click_monitor_networks():
            result = result and False
        time.sleep(3)
        rows = self.webui_common.get_rows()
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
            self.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
        if vn_entry_flag:
            self.logger.info(
                " VN %s and subnet verified in webui config and monitor pages" %
                (fixture.vn_name))
        # if self.webui_common.verify_uuid_table(fixture.vn_id):
        #     self.logger.info( "VN %s UUID verified in webui table " %(fixture.vn_name))
        # else:
        #     self.logger.error( "VN %s UUID Verification failed in webui table " %(fixture.vn_name))
        # self.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
        fixture.obj = fixture.quantum_fixture.get_vn_obj_if_present(
            fixture.vn_name, fixture.project_id)
        fq_type = 'virtual_network'
        full_fq_name = fixture.vn_fq_name + ':' + fixture.vn_id
        # if self.webui_common.verify_fq_name_table(full_fq_name, fq_type):
        #     self.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        # else:
        #     self.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        # self.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        return True
    # end verify_vn_in_webui

    def svc_instance_delete(self, fixture):
        self.webui_common.delete_element(fixture, 'svc_instance_delete')
    # end svc_instance_delete_in_webui

    def svc_template_delete(self, fixture):
        self.webui_common.delete_element(fixture, 'svc_template_delete')
    # end svc_template_delete_in_webui

    def vn_delete_in_webui(self, fixture):
        self.webui_common.delete_element(fixture, 'vn_delete')
    # end vn_delete_in_webui

    def ipam_delete_in_webui(self, fixture):
        if not self.webui_common.click_configure_ipam():
            result = result and False
        rows = self.webui_common.get_rows()
        for ipam in range(len(rows)):
            tdArry = rows[ipam].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteIpam').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id(
                        'btnCnfRemoveMainPopupOK').click()
                    if not self.webui_common.check_error_msg("Delete ipam"):
                        raise Exception("Ipam deletion failed")
                        break
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s is deleted successfully using webui" % (name))
                    break
    # end ipam_delete_in_webui

    def service_template_delete_in_webui(self, fixture):
        if not self.webui_common.click_configure_service_template():
            result = result and False
        rows = self.webui_common.get_rows()
        for temp in range(len(rows)):
            tdArry = rows[temp].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.st_name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeletesvcTemplate').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id('btnCnfDelPopupOK').click()
                    if not self.webui_common.check_error_msg("Delete service template"):
                        raise Exception("Service template deletion failed")
                        break
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.logger.info("%s is deleted successfully using webui" %
                                     (fixture.st_name))
                    break
    # end service_template_delete_in_webui

    def service_instance_delete_in_webui(self, fixture):
        if not self.webui_common.click_configure_service_instance():
            result = result and False
        rows = self.webui_common.get_rows()
        for inst in range(len(rows)):
            tdArry = rows[inst].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == fixture.si_name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeletesvcInstances').find_element_by_tag_name('i').click()
                    self.browser.find_element_by_id(
                        'btnCnfDelSInstPopupOK').click()
                    if not self.webui_common.check_error_msg("Delete service instance"):
                        raise Exception("Service instance deletion failed")
                        break
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.logger.info("%s is deleted successfully using webui" %
                                     (fixture.si_name))
                    break
    # end service_instance_delete_in_webui

    def dns_server_delete(self, name):
        if not self.webui_common.click_configure_dns_server():
            result = result and False
        rows = self.webui_common.get_rows()
        for server in range(len(rows)):
            tdArry = rows[server].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteDNSServer').click()
                    self.browser.find_element_by_id('btnCnfDelPopupOK').click()
                    if not self.webui_common.check_error_msg("Delete dns server"):
                        raise Exception("Dns server deletion failed")
                        break
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s is deleted successfully using webui" % (name))
                    break
    # end dns_server_delete_in_webui

    def dns_record_delete(self, name):
        if not self.webui_common.click_configure_dns_record():
            result = result and False
        rows = self.webui_common.get_rows()
        for record in range(len(rows)):
            tdArry = rows[record].find_elements_by_class_name('slick-cell')
            if (len(tdArry) > 2):
                if (tdArry[2].text == name):
                    tdArry[1].find_element_by_tag_name('input').click()
                    self.browser.find_element_by_id(
                        'btnDeleteDNSRecord').click()
                    self.browser.find_element_by_id(
                        'btnCnfDelMainPopupOK').click()
                    if not self.webui_common.check_error_msg("Delete dns record"):
                        raise Exception("Dns record deletion failed")
                        break
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.logger.info(
                        "%s is deleted successfully using webui" % (name))
                    break
    # end dns_record_delete_in_webui

    def create_vm_in_openstack(self, fixture):
        try:
            if not self.proj_check_flag:
                WebDriverWait(self.browser_openstack, self.delay).until(
                    lambda a: a.find_element_by_link_text('Project')).click()
                time.sleep(3)
                WebDriverWait(self.browser_openstack, self.delay).until(
                    lambda a: a.find_element_by_css_selector('h4')).click()
                WebDriverWait(self.browser_openstack, self.delay).until(
                    lambda a: a.find_element_by_id('tenant_list')).click()
                current_project = WebDriverWait(self.browser_openstack, self.delay).until(
                    lambda a: a.find_element_by_css_selector('h3')).text
                if not current_project == fixture.project_name:
                    WebDriverWait(self.browser_openstack, self.delay).until(
                        lambda a: a.find_element_by_css_selector('h3')).click()
                    WebDriverWait(self.browser_openstack, self.delay).until(
                        lambda a: a.find_element_by_link_text(fixture.project_name)).click()
                    self.webui_common.wait_till_ajax_done(
                        self.browser_openstack)
                    self.proj_check_flag = 1
            WebDriverWait(self.browser_openstack, self.delay).until(
                lambda a: a.find_element_by_link_text('Project')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            instance = WebDriverWait(self.browser_openstack, self.delay).until(
                lambda a: a.find_element_by_link_text('Instances')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            fixture.image_name = 'ubuntu'
            fixture.nova_fixture.get_image(image_name=fixture.image_name)
            time.sleep(2)
            launch_instance = WebDriverWait(self.browser_openstack, self.delay).until(
                lambda a: a.find_element_by_link_text('Launch Instance')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            self.logger.debug('Creating instance name %s with image name %s using openstack'
                              % (fixture.vm_name, fixture.image_name))
            self.logger.info('Creating instance name %s with image name %s using openstack'
                             % (fixture.vm_name, fixture.image_name))
            time.sleep(3)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='source_type']/option[contains(text(), 'image') or contains(text(),'Image')]").click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='image_id']/option[contains(text(), '" + fixture.image_name + "')]").click()
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id(
                'id_name')).send_keys(fixture.vm_name)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='flavor']/option[text()='m1.small']").click()
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            networks = WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id
                                                                              ('available_network')).find_elements_by_tag_name('li')
            for net in networks:
                vn_match = net.text.split('(')[0]
                if (vn_match == fixture.vn_name):
                    net.find_element_by_class_name('btn').click()
                    break
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            self.logger.debug('VM %s launched using openstack' %
                              (fixture.vm_name))
            self.logger.info('Waiting for VM %s to come into active state' %
                             (fixture.vm_name))
            time.sleep(10)
            rows_os = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows_os)):
                rows_os = self.browser_openstack.find_element_by_tag_name(
                    'form')
                rows_os = WebDriverWait(rows_os, self.delay).until(
                    lambda a: a.find_element_by_tag_name('tbody'))
                rows_os = WebDriverWait(rows_os, self.delay).until(
                    lambda a: a.find_elements_by_tag_name('tr'))
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
                                "%s status changed to Active in openstack" % (fixture.vm_name))
                            vm_active = True
                            time.sleep(5)
                        elif(vm_active_status1 == 'Error' or vm_active_status2 == 'Error'):
                            self.logger.error(
                                "%s state went into Error state in openstack" % (fixture.vm_name))
                            self.browser_openstack.get_screenshot_as_file(
                                'verify_vm_state_openstack_' + 'fixture.vm_name' + '.png')
                            return "Error"
                        else:
                            self.logger.info(
                                "%s state is not yet Active in openstack, waiting for more time..." % (fixture.vm_name))
                            counter = counter + 1
                            time.sleep(3)
                            self.browser_openstack.find_element_by_link_text(
                                'Instances').click()
                            self.webui_common.wait_till_ajax_done(
                                self.browser_openstack)
                            time.sleep(3)
                            if(counter >= 100):
                                fixuture.logger.error(
                                    "VM %s failed to come into active state" % (fixture.vm_name))
                                self.browser_openstack.get_screenshot_as_file(
                                    'verify_vm_not_active_openstack_' + 'fixture.vm_name' + '.png')
                                break
            fixture.vm_obj = fixture.nova_fixture.get_vm_if_present(
                fixture.vm_name, fixture.project_fixture.uuid)
            fixture.vm_objs = fixture.nova_fixture.get_vm_list(
                name_pattern=fixture.vm_name, project_id=fixture.project_fixture.uuid)
        except ValueError:
            self.logger.error('Error while creating VM %s with image name %s failed in openstack'
                              % (fixture.vm_name, fixture.image_name))
            self.browser_openstack.get_screenshot_as_file(
                'verify_vm_error_openstack_' + 'fixture.vm_name' + '.png')
    # end create_vm_in_openstack

    def vm_delete_in_openstack(self, fixture):
        rows = self.browser_openstack.find_element_by_id('instances').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        for instance in rows:
            if fixture.vm_name == instance.find_element_by_tag_name('a').text:
                instance.find_elements_by_tag_name(
                    'td')[0].find_element_by_tag_name('input').click()
                break
        ln = len(rows)
        launch_instance = WebDriverWait(self.browser_openstack, self.delay).until(
            lambda a: a.find_element_by_id('instances__action_terminate')).click()
        WebDriverWait(self.browser_openstack, self.delay).until(
            lambda a: a.find_element_by_link_text('Terminate Instances')).click()
        time.sleep(5)
        self.logger.info("VM %s deleted successfully using openstack" %
                         (fixture.vm_name))
    # end vm_delete_in_openstack

    def verify_vm_in_webui(self, fixture):
        result = True
        try:
            if not self.webui_common.click_monitor_instances():
                result = result and False
            rows = self.webui_common.get_rows()
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
                        "VM %s vm exists..will verify row expansion basic details" % (fixture.vm_name))
                    retry_count = 0
                    while True:
                        self.logger.debug("Count is" + str(retry_count))
                        if retry_count > 20:
                            self.logger.error('Vm details failed to load')
                            break
                        self.browser.find_element_by_xpath(
                            "//*[@id='mon_net_instances']").find_element_by_tag_name('a').click()
                        time.sleep(1)
                        rows = self.webui_common.get_rows()
                        rows[i].find_elements_by_tag_name(
                            'div')[0].find_element_by_tag_name('i').click()
                        try:
                            retry_count = retry_count + 1
                            rows = self.webui_common.get_rows()
                            rows[
                                i + 1].find_elements_by_class_name('row-fluid')[0].click()
                            self.webui_common.wait_till_ajax_done(self.browser)
                            break
                        except WebDriverException:
                            pass
                    rows = self.webui_common.get_rows()
                    row_details = rows[
                        i + 1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')[5]
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
            self.browser.get_screenshot_as_file('vm_create_check.png')
            self.logger.info(
                "Vm name,vm uuid,vm ip and vm status,vm network verification in WebUI for VM %s passed" %
                (fixture.vm_name))
            mon_net_networks = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
                'mon_net_networks')).find_element_by_link_text('Networks').click()
            time.sleep(4)
            self.webui_common.wait_till_ajax_done(self.browser)
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                if(rows[i].find_elements_by_class_name('slick-cell')[1].text == fixture.vn_fq_name.split(':')[0] + ":" + fixture.project_name + ":" + fixture.vn_name):
                    rows[i].find_elements_by_tag_name(
                        'div')[0].find_element_by_tag_name('i').click()
                    time.sleep(2)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    rows = self.webui_common.get_rows()
                    vm_ids = rows[
                        i + 1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')[5].find_elements_by_tag_name('div')[1].text
                    if fixture.vm_id in vm_ids:
                        self.logger.info(
                            "Vm_id matched in webui monitor network basic details page %s" % (fixture.vn_name))
                    else:
                        self.logger.error(
                            "Vm_id not matched in webui monitor network basic details page %s" % (fixture.vm_name))
                        self.browser.get_screenshot_as_file(
                            'monitor_page_vm_id_not_match' + fixture.vm_name + fixture.vm_id + '.png')
                        result = result and False
                    break
            # if self.webui_common.verify_uuid_table(fixture.vm_id):
            #    self.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            # else:
            #    self.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            # fq_type='virtual_machine'
            # full_fq_name=fixture.vm_id+":"+fixture.vm_id
            # if self.webui_common.verify_fq_name_table(full_fq_name,fq_type):
            #   self.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            # else:
            #   self.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            self.logger.info("VM verification in WebUI %s passed" %
                             (fixture.vm_name))
            return result
        except ValueError:
            self.logger.error("vm %s test error " % (fixture.vm_name))
            self.browser.get_screenshot_as_file(
                'verify_vm_test_openstack_error' + 'fixture.vm_name' + '.png')
    # end verify_vm_in_webui

    def create_floatingip_pool_webui(self, fixture, pool_name, vn_name):
        try:
            if not self.webui_common.click_configure_networks():
                result = result and False
            self.webui_common.select_project(fixture.project_name)
            rows = self.webui_common.get_rows()
            self.logger.info("Creating floating ip pool %s using webui" %
                             (pool_name))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')[2].get_attribute('innerHTML') == fixture.vn_name):
                    net.find_element_by_class_name('icon-cog').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    time.sleep(3)
                    self.browser.find_element_by_class_name(
                        'tooltip-success').find_element_by_tag_name('i').click()
                    ip_text = net.find_element_by_xpath(
                        "//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath(
                        '..').find_element_by_tag_name('i').click()
                    route = self.browser.find_element_by_xpath(
                        "//div[@title='Add Floating IP Pool below']")
                    route.find_element_by_class_name('icon-plus').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_xpath(
                        "//input[@placeholder='Pool Name']").send_keys(fixture.pool_name)
                    self.browser.find_element_by_id(
                        'fipTuples').find_elements_by_tag_name('input')[1].click()
                    project_elements = self.browser.find_elements_by_xpath(
                        "//*[@class = 'select2-match']/..")
                    self._click_if_element_found(
                        fixture.project_name, project_elements)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    time.sleep(2)
                    if not self.webui_common.check_error_msg("Creating fip pool"):
                        raise Exception("Create fip pool failed")
                    self.logger.info("Fip pool %s created using webui" %
                                     (fixture.pool_name))
                    break
        except ValueError:
            self.logger.error("Fip %s Error while creating floating ip pool " %
                              (fixture.pool_name))
    # end create_floatingip_pool_webui

    def create_and_assoc_fip_webui(self, fixture, fip_pool_vn_id, vm_id, vm_name, project=None):
        try:
            fixture.vm_name = vm_name
            fixture.vm_id = vm_id
            if not self.webui_common.click_configure_networks():
                result = result and False
            self.webui_common.select_project(fixture.project_name)
            rows = self.webui_common.get_rows()
            self.logger.info("Creating and associating fip %s using webui" %
                             (fip_pool_vn_id))
            for net in rows:
                if (net.find_elements_by_class_name('slick-cell')[2].get_attribute('innerHTML') == fixture.vn_name):
                    self.browser.find_element_by_xpath(
                        "//*[@id='config_net_fip']/a").click()
                    self.browser.get_screenshot_as_file('fip.png')
                    time.sleep(3)
                    self.browser.find_element_by_id('btnCreatefip').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    time.sleep(1)
                    pool = self.browser.find_element_by_xpath("//div[@id='s2id_ddFipPool']").find_element_by_tag_name(
                        'a').click()
                    time.sleep(2)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    fip = self.browser.find_element_by_id(
                        "select2-drop").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].find_element_by_tag_name('div').get_attribute("innerHTML") == fixture.project_name + ':' + fixture.vn_name + ':' + fixture.pool_name:
                            fip[i].click()
                    self.browser.find_element_by_id('btnCreatefipOK').click()
                    if not self.webui_common.check_error_msg("Creating Fip"):
                        raise Exception("Create fip failed")
                    self.webui_common.wait_till_ajax_done(self.browser)
                    rows1 = self.webui_common.get_rows()
                    for element in rows1:
                        if element.find_elements_by_class_name('slick-cell')[3].get_attribute('innerHTML') == fixture.vn_name + ':' + fixture.pool_name:
                            element.find_element_by_class_name(
                                'icon-cog').click()
                            self.webui_common.wait_till_ajax_done(self.browser)
                            element.find_element_by_xpath(
                                "//a[@class='tooltip-success']").click()
                            self.webui_common.wait_till_ajax_done(self.browser)
                            break
                    pool = self.browser.find_element_by_xpath(
                        "//div[@id='s2id_ddAssociate']").find_element_by_tag_name('a').click()
                    time.sleep(1)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    fip = self.browser.find_element_by_id(
                        "select2-drop").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].find_element_by_tag_name('div').get_attribute("innerHTML").split(' ')[1] == vm_id:
                            fip[i].click()
                    self.browser.find_element_by_id(
                        'btnAssociatePopupOK').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    if not self.webui_common.check_error_msg("Fip Associate"):
                        raise Exception("Fip association failed")
                    time.sleep(1)
                    break
        except ValueError:
            self.logger.info(
                "Error while creating floating ip and associating it.")
    # end create_and_assoc_fip_webui

    def verify_fip_in_webui(self, fixture):
        if not self.webui_common.click_configure_networks():
            result = result and False
        rows = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
            'gridVN')).find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            vn_name = rows[i].find_elements_by_tag_name('td')[2].text
            if vn_name == fixture.vn_name:
                rows[i].find_elements_by_tag_name(
                    'td')[0].find_element_by_tag_name('a').click()
                rows = self.webui_common.get_rows()
                fip_check = rows[
                    i + 1].find_elements_by_xpath("//td/div/div/div")[1].text
                if fip_check.split('\n')[1].split(' ')[0] == fixture.pool_name:
                    self.logger.info(
                        "Fip pool %s verified in WebUI configure network page" % (fixture.pool_name))
                    break
        WebDriverWait(self.browser, self.delay).until(
            lambda a: a.find_element_by_xpath("//*[@id='config_net_fip']/a")).click()
        self.webui_common.wait_till_ajax_done(self.browser)
        rows = self.browser.find_element_by_xpath(
            "//div[@id='gridfip']/table/tbody").find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            fip = rows[i].find_elements_by_tag_name('td')[3].text.split(':')[1]
            vn = rows[i].find_elements_by_tag_name('td')[3].text.split(':')[0]
            fip_ip = rows[i].find_elements_by_class_name('slick-cell')[1].text
            if rows[i].find_elements_by_tag_name('td')[2].text == fixture.vm_id:
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
        if not self.webui_common.click_monitor_instances():
            result = result and False
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
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
                self.webui_common.wait_till_ajax_done(self.browser)
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fip_check_vm = rows[i + 1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]"
                                                                 ).find_elements_by_tag_name('div')[0].find_elements_by_tag_name('div')[1].text
                if fip_check_vm.split(' ')[0] == fip_ip and fip_check_vm.split(
                        ' ')[1] == '\(' + 'default-domain' + ':' + fixture.project_name + ':' + fixture.vn_name + '\)':
                    self.logger.info(
                        "FIP verified in monitor instance page for vm %s " % (fixture.vm_name))
                else:
                    self.logger.info(
                        "FIP failed to verify in monitor instance page for vm %s" % (fixture.vm_name))
                    break
    # end verify_fip_in_webui

    def delete_fip_in_webui(self, fixture):
        if not self.webui_common.click_configure_fip():
            result = result and False
        rows = self.browser.find_element_by_id('gridfip').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        for net in rows:
            if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vm_id):
                net.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                    'div').find_element_by_tag_name('div').click()
                self.webui_common.wait_till_ajax_done(self.browser)
                net.find_element_by_xpath(
                    "//a[@class='tooltip-error']").click()
                self.webui_common.wait_till_ajax_done(self.browser)
                WebDriverWait(self.browser, self.delay).until(
                    lambda a: a.find_element_by_id('btnDisassociatePopupOK')).click()
                self.webui_common.wait_till_ajax_done(self.browser)
                self.webui_common.wait_till_ajax_done(self.browser)
            rows = self.browser.find_element_by_id('gridfip').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
            for net in rows:
                if (net.find_elements_by_tag_name('td')[3].get_attribute('innerHTML') == fixture.vn_name + ':' + fixture.pool_name):
                    net.find_elements_by_tag_name(
                        'td')[0].find_element_by_tag_name('input').click()
                    WebDriverWait(self.browser, self.delay).until(
                        lambda a: a.find_element_by_id('btnDeletefip')).click()
                    WebDriverWait(self.browser, self.delay).until(
                        lambda a: a.find_element_by_id('btnCnfReleasePopupOK')).click()
            if not self.webui_common.click_configure_networks():
                result = result and False
            rows = self.webui_common.get_rows()
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name):
                    net.find_element_by_class_name('dropdown-toggle').click()
                    net.find_elements_by_tag_name(
                        'li')[0].find_element_by_tag_name('a').click()
                    ip_text = net.find_element_by_xpath(
                        "//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath(
                        '..').find_element_by_tag_name('i').click()
                    pool_con = self.browser.find_element_by_id('fipTuples')
                    fip = pool_con.find_elements_by_xpath(
                        "//*[contains(@id, 'rule')]")
                    for pool in fip:
                        if(pool.find_element_by_tag_name('input').get_attribute('value') == fixture.pool_name):
                            pool.find_element_by_class_name(
                                'icon-minus').click()
                    self.browser.find_element_by_xpath(
                        "//button[@id = 'btnCreateVNOK']").click()
                    break
    # end delete_fip_in_webui
