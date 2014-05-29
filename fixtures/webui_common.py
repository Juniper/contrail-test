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
from util import *
from vnc_api.vnc_api import *
from verification_util import *

def ajax_complete(driver):
        try:
            return 0 == driver.execute_script("return jQuery.active")
        except WebDriverException:
            pass
#end ajax_complete

class WebuiCommon:
    def __init__(self, webui_test):
        self.jsondrv = JsonDrv(self)
        self.delay = 20
        self.webui = webui_test
        self.inputs = self.webui.inputs
        self.connections = self.webui.connections
        self.browser = self.webui.browser
        self.browser_openstack = self.webui.browser_openstack
        self.frequency = 1
        self.logger = self.inputs.logger
        self.dash = "-" * 60

    def wait_till_ajax_done(self, browser):
        #WebDriverWait(browser, self.delay, self.frequency).until(ajax_complete) 
        time.sleep(4)
    #end wait_till_ajax_done
     
    def get_service_instance_list_api(self):
        url = 'http://' + self.inputs.cfgm_ip + ':8082/service-instances'
        obj = self.jsondrv.load(url)
        return obj
    #end get_service_instance_list_api

    def get_service_chains_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/service-chains'
        obj = self.jsondrv.load(url)
        return obj
    #end get_service_instance_list_api

    def get_generators_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/generators'
        obj = self.jsondrv.load(url)
        return obj
    #end get_generators_list_ops

    def get_bgp_peers_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/bgp-peers'
        obj = self.jsondrv.load(url)
        return obj
    #end get_bgp_peers_list_ops

    def get_policy_list_api(self):
        url = 'http://' + self.inputs.collector_ip + ':8082/network-policys'
        obj = self.jsondrv.load(url)
        return obj
    #end get_vn_list_api

    def get_ipam_list_api(self):
        url = 'http://' + self.inputs.collector_ip + ':8082/network-ipams'
        obj = self.jsondrv.load(url)
        return obj
    
    def get_service_template_list_api(self):
        url = 'http://' + self.inputs.collector_ip + ':8082/service-templates'
        obj = self.jsondrv.load(url)
        return obj

    def get_vrouters_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/vrouters'
        obj = self.jsondrv.load(url)
        return obj
    #end get_vrouters_list_ops
  
    def get_dns_nodes_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/dns-nodes'
        obj = self.jsondrv.load(url)
        return obj
    #end get_dns_nodes_list_ops

    def get_collectors_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/analytics-nodes'
        #url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/collectors'
        obj = self.jsondrv.load(url)
        return obj
    #end get_collectors_list_ops

    def get_bgp_routers_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/control-nodes'
        #url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/bgp-routers'
        obj = self.jsondrv.load(url)
        return obj
    #end get_bgp_routers_list_ops

    def get_control_nodes_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/control-nodes'
        obj = self.jsondrv.load(url)
        return obj
    #end get_config_nodes_list_ops

    def get_config_nodes_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/config-nodes'
        obj = self.jsondrv.load(url)
        return obj
    #end get_config_nodes_list_ops

    def get_modules_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/modules'
        obj = self.jsondrv.load(url)
        return obj
    #end get_modules_list_ops

    def get_service_instances_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/service-instances'
        obj = self.jsondrv.load(url)
        return obj
    #end get_service_instances_list_ops

    def get_vn_list_api(self):
        url = 'http://' + self.inputs.collector_ip + ':8082/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj
    #end get_vn_list_api

    def get_details(self, url):
        obj = self.jsondrv.load(url)
        return obj
    #end get_details 
    
    def get_vn_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj
    #end get_vn_list_ops

    def get_xmpp_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/xmpp-peers'
        obj = self.jsondrv.load(url)
        return obj
    #end get_xmpp_list_ops

    def get_vm_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/virtual-machines'
        obj = self.jsondrv.load(url)
        return obj
    #end get_vm_list_ops

    def log_msg(self, t, msg):
        if t == 'info' :
            self.logger.info(msg)
        elif t == 'error' :
            self.logger.error(msg)
        elif t == 'debug' : 
            self.logger.debug(msg)
        else:
            self.logger.info(msg)
    #end log_msg

    def get_memory_string(self, dictn):
        if type(dictn) is dict:
            memory = dictn.get('cpu_info').get('meminfo').get('virt')
        else:
            memory = dictn
            memory = memory/1024.0
        offset = 5
        if memory < 1024:
            offset = 50
            memory = round(memory, 2)
            memory_range = range(int(memory*100)-offset,int(memory*100)+offset)
            memory_range = map(lambda x: x/100.0,memory_range)
            memory_list = [str(memory) + ' KB' for memory in memory_range]
        elif memory/1024.0 < 1024 :
            memory = memory/1024.0
            memory = round(memory, 2)
            memory_range = range(int(memory*100)-offset,int(memory*100)+offset)
            memory_range = map(lambda x: x/100.0,memory_range)
            for memory in memory_range:
                if type(memory) is float and memory == int(memory):
                   index = memory_range.index(memory)
                   memory_range[index] = int(memory)
            memory_list = [str(memory) + ' MB' for memory in memory_range]
        else:
            memory = round(memory/1024, 2)
            memory_range = range(int(memory*100)-offset,int(memory*100)+offset)
            memory_range = map(lambda x: x/100.0,memory_range)
            memory_list = [str(memory) + ' GB' for memory in memory_range]
        return memory_list
    #end get_memory_string

    def get_cpu_string(self, dictn):
        offset = 5
        cpu =float( dictn.get('cpu_info').get('cpu_share'))
        cpu = round(cpu, 2)
        cpu_range = range(int(cpu*100)-offset,int(cpu*100)+offset)
        cpu_range = map(lambda x: x/100.0,cpu_range)
        cpu_list = [str('%.2f' % cpu) + ' %' for cpu in cpu_range]
        return cpu_list
    #end get_cpu_string

    def get_version_string(self, version):
        version = version.split('-')
        version = version[0] + ' (Build ' + version[1] + ')'
        return version
    #end get_version_string
    
    def check_error_msg(self, error_msg):
        try:
            if self.browser.find_element_by_id('infoWindow') :
                error_header = self.browser.find_element_by_class_name('modal-header-title').text
                error_text = self.browser.find_element_by_id('short-msg').text
                self.logger.error('error occured while clicking on %s : %s ' %(error_msg,error_header))
                self.logger.error('error text : msg is %s ' %(error_text))
                
                self.logger.info('Capturing screenshot of error msg .')
                self.browser.get_screenshot_as_file(error_msg + 'click failure' +  self.date_time_string()+'.png')
                self.logger.info('Captured screenshot' + error_msg + 'click failure' + self.date_time_string()+'.png')
                self.browser.find_element_by_id('infoWindowbtn0').click()
                return False
        except NoSuchElementException:
            return True

    def get_rows(self):
        return self.browser.find_elements_by_class_name('ui-widget-content')
    #end get_rows   
   
    def click_monitor_instances_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Instances').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(5)
        rows = self.get_rows()
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        rows[row_index+1].find_element_by_class_name('pull-right').find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
    #end click_monitor_instances_basic_in_webui

    def click_monitor_networks_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        rows = self.get_rows()
        
        rows[row_index].find_elements_by_class_name('slick-cell')[0].find_element_by_tag_name('i').click()
        time.sleep(1) 
        self.wait_till_ajax_done(self.browser)
        rows = self.get_rows()
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser)
        rows[row_index+1].find_element_by_class_name('pull-right').find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
    #end click_monitor_instances_basic_in_webui
    
    def click_monitor_common_basic_in_webui(self, row_index) :
        self.wait_till_ajax_done(self.browser)
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser)
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-list').click()
        self.wait_till_ajax_done(self.browser)
    #end click_monitor_common_advance_in_webui

    
    def click_monitor_vrouters_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_compute'))
        mon_net_networks.find_element_by_link_text('Virtual Routers').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        return self.check_error_msg("monitor vrouters")
    #end click_monitor_vrouters_in_webui

    def click_monitor_dashboard_in_webui(self):
        self.click_monitor_in_webui()
        self.browser.find_element_by_id('mon_infra_dashboard').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        return self.check_error_msg("monitor dashboard")
    #end click_monitor_dashboard_in_webui
   
    def click_monitor_config_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_config'))
        mon_net_networks.find_element_by_link_text('Config Nodes').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(1)
        return self.check_error_msg("monitor config nodes")
    #end click_monitor_config_nodes_in_webui

    def click_monitor_control_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_control'))
        mon_net_networks.find_element_by_link_text('Control Nodes').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        return self.check_error_msg("monitor control nodes")

    #end click_monitor_control_nodes_in_webui
        
    def click_monitor_analytics_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_analytics'))
        mon_net_networks.find_element_by_link_text('Analytics Nodes').click()
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("monitor analytics nodes")
    #end click_monitor_analytics_nodes_in_webui

    def get_service_instance_list_api(self):
        url = 'http://' + self.inputs.cfgm_ip + ':8082/service-instances'
        obj = self.jsondrv.load(url)
        return obj
    #end get_service_instance_list_api

    def click_configure_service_instance_basic_in_webui(self,row_index):
        self.browser.find_element_by_link_text('Service Instances').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("configure service instance")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    #end click_configure_service_instance_basic_in_webui
   
    def click_configure_service_instance_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        self.wait_till_ajax_done(self.browser)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[2].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        config_service_temp = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_sc_svcInstances'))
        config_service_temp.find_element_by_link_text('Service Instances').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        return self.check_error_msg("configure service instances")
    #end click_configure_service_template_in_webui

 
    def click_configure_networks_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        time.sleep(3)
        self.wait_till_ajax_done(self.browser) 
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        time.sleep(2)
        config_net_vn = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_net_vn'))
        config_net_vn.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(1)
        return self.check_error_msg("configure networks")
    #end click_configure_networks_in_webui

    def __wait_for_networking_items(self, a) :
        if len(a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0 :
            return True        
    #end __wait_for_networking_items

    def click_configure_fip_in_webui(self):
        self.browser.find_element_by_id('btn-configure').click()
        self.wait_till_ajax_done(self.browser) 
        menu = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(1)
        WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('config_net_fip')).find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(1)
        return self.check_error_msg("configure fip")
    #end click_configure_fip_in_webui
    
    def click_error(self, name):
            self.logger.error("some error occured whlie clicking on %s"%(name))
            return False
    
    def click_monitor_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        self.wait_till_ajax_done(self.browser)
        return self.check_error_msg("monitor")

    def click_monitor_networking_in_webui(self):
        self.click_monitor_in_webui()
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.browser.get_screenshot_as_file('click_btn_mon_span.png')
        time.sleep(2)
        self.wait_till_ajax_done(self.browser)
    #end click_monitor_in_webui
 
    def click_monitor_networks_in_webui(self):
        self.click_monitor_networking_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(1)
        return self.check_error_msg("monitor networks")
    #end click_monitor_networks_in_webui

    def click_monitor_instances_in_webui(self):
        self.click_monitor_networking_in_webui()
        mon_net_instances = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('mon_net_instances'))
        mon_net_instances.find_element_by_link_text('Instances').click()
  	self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        return self.check_error_msg("monitor_instances")
    #end click_monitor_instances_in_webui

    def click_monitor_vrouters_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Virtual Routers').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor vrouters")
        self.click_monitor_common_basic_in_webui(row_index)
    #end click_monitor_vrouters_basic_in_webui

    def click_monitor_analytics_nodes_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Analytics Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor analytics nodes")
        self.click_monitor_common_basic_in_webui(row_index)
    #end click_monitor_analytics_nodes_basic_in_webui

    def click_monitor_control_nodes_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Control Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor control nodes")
        self.click_monitor_common_basic_in_webui(row_index)
    #end click_monitor_vrouters_basic_in_webui

    def click_monitor_config_nodes_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Config Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor config nodes")
        self.click_monitor_common_basic_in_webui(row_index)
    #end click_monitor_config_nodes_basic_in_webui
         
    def click_monitor_vrouters_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Virtual Routers').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor vrouters")
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_vrouters_advance_in_webui

    def click_monitor_config_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Config Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor config nodes")
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_config_nodes_advance_in_webui

    def click_monitor_control_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Control Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor control nodes")
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_control_nodes_advance_in_webui

    def click_monitor_analytics_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Analytics Nodes').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor analytics nodes")
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_analytics_nodes_advance_in_webui
    
    def click_monitor_common_advance_in_webui(self, row_index) : 
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].click()
        self.wait_till_ajax_done(self.browser) 
        self.browser.find_element_by_id('dashboard-box').find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser) 
        self.browser.find_element_by_id('dashboard-box').find_element_by_class_name('icon-code').click()
        self.wait_till_ajax_done(self.browser) 
    #end click_monitor_common_advance_in_webui

    def click_monitor_common_basic_in_webui(self, row_index) :
        self.wait_till_ajax_done(self.browser)
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].click()
        self.wait_till_ajax_done(self.browser)
        self.browser.find_element_by_id('dashboard-box').find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done(self.browser)
        self.browser.find_element_by_id('dashboard-box').find_element_by_class_name('icon-list').click()
        self.wait_till_ajax_done(self.browser)
    #end click_monitor_common_basic_in_webui

    def click_monitor_networks_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1)
        self.check_error_msg("monitornetworks") 
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].find_element_by_tag_name('i').click()
        time.sleep(1) 
        self.wait_till_ajax_done(self.browser) 
        rows = self.get_rows()
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        time.sleep(1) 
        self.wait_till_ajax_done(self.browser) 
        rows[row_index+1].find_element_by_class_name('pull-right').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(1) 
    #end click_monitor_networks_advance_in_webui

    def click_monitor_instances_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Instances').click()
        time.sleep(2)
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("monitor instances") 
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser) 
        time.sleep(2)
        rows = self.get_rows()
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        time.sleep(2)
        self.wait_till_ajax_done(self.browser) 
        rows[row_index+1].find_element_by_class_name('pull-right').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        time.sleep(2)
        self.wait_till_ajax_done(self.browser) 
    #end click_monitor_instances_advance_in_webui

    def click_configure_networks_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("configure networks")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    #end click_configure_networks_basic_in_webui

    def click_configure_policies_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Policies').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("configure policies")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    #end click_configure_policies_basic_in_webui

    def click_configure_ipam_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('IP Address Management').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("configure ipam")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    #end click_configure_ipam_basic_in_webui

    def click_configure_service_template_basic_in_webui(self,row_index):
        self.browser.find_element_by_link_text('Service Templates').click()
        self.wait_till_ajax_done(self.browser)
        self.check_error_msg("configure service template")
        rows = self.get_rows()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        rows[row_index].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
        self.wait_till_ajax_done(self.browser)
    #end click_configure_service_template_basic_in_webui

    def click_configure_service_template_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        self.wait_till_ajax_done(self.browser)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[2].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        config_service_temp = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_sc_svctemplate'))
        config_service_temp.find_element_by_link_text('Service Templates').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        return self.check_error_msg("configure service template")
    #end click_configure_service_template_in_webui
 
    def click_configure_policies_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        self.wait_till_ajax_done(self.browser)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        config_net_policy = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_net_policies'))
        time.sleep(2)
        config_net_policy.find_element_by_link_text('Policies').click()
        self.browser.get_screenshot_as_file('click policies.png')
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        return self.check_error_msg("configure policies")
    #end click_configure_policies_in_webui

    def click_configure_ipam_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        self.wait_till_ajax_done(self.browser)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        config_net_policy = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_net_ipam'))
        time.sleep(2)
        config_net_policy.find_element_by_link_text('IP Address Management').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(3)
        return self.check_error_msg("configure ipam")
    #end click_configure_ipam_in_webui

    def verify_uuid_table(self, uuid):
        browser=self.browser
        delay=self.delay
        browser.find_element_by_id('btn-setting').click()
        time.sleep(2)
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        self.wait_till_ajax_done(self.browser)
        time.sleep(2)
        flag=1
        element = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('cdb-results'))
        page_length = element.find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        total_pages=page_length[ln-1].get_attribute('data-page')
        length=int(total_pages)
        for l in range(0, length):
            if flag == 0:
                browser.find_element_by_id("cdb-results").find_element_by_xpath("//a[@title='Go to the next page']").click()
                self.wait_till_ajax_done(self.browser)
            row5=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
            row6=row5.find_elements_by_tag_name('a')
            for k in range(len(row6)):
                str2=row6[k].get_attribute("innerHTML")
                num1=str2.find(uuid)
                if num1!=-1:
                    flag=1
                    return True
                    break
                else:
                    flag=0
    #end verify_uuid_table

    def verify_fq_name_table(self, full_fq_name, fq_type) :
        browser=self.browser
        delay=self.delay
        uuid=full_fq_name
        fq_name=fq_type
        btn_setting = WebDriverWait(browser, delay).until(lambda a: a.find_element_by_id('btn-setting')).click()
        WebDriverWait(browser, delay).until(ajax_complete)
        row1=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
        obj_fq_name_table='obj_fq_name_table~' + fq_name
        row1.find_element_by_xpath("//*[@id='"+obj_fq_name_table+"']").click()
        WebDriverWait(browser, delay).until(ajax_complete, "Timeout waiting for page to appear")
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath(
            "//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        page_length1=int(page_length[ln-1].get_attribute('data-page'))
        flag=1
        for l in range(page_length1):
           if flag==0:
                page=browser.find_element_by_id("cdb-results").find_element_by_xpath(
                    "//div[@class='k-pager-wrap k-grid-pager k-widget']").find_element_by_tag_name("ul")
                page1=page.find_elements_by_tag_name('li')
                page2=page1[l].find_element_by_tag_name('a').click()
                WebDriverWait(browser, delay).until(ajax_complete, "Timeout waiting for page to appear")
           row3=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
           row4=row3.find_elements_by_tag_name('td')
           for k in range(len(row4)):
                fq=row4 [k].get_attribute('innerHTML')
                if(fq==uuid):
                    flag=1
                    return True
                    break
                else:
                    flag=0
           if flag==1:
               break
    #end verify_fq_name_table 

    def check_element_exists_by_xpath(self, webdriver, xpath):
        try:
            webdriver.find_element_by_xpath(xpath)
        except NoSuchElementException:
            return False
        return True   
    #end check_element_exists_by_xpath

    #def get_node_status(self, dictn):
       
    
    def get_expanded_api_data_in_webui(self, row_index) :
        i = 1
        self.click_configure_networks_in_webui()
        rows = self.get_rows()
        rows[row_index].find_elements_by_class_name('slick-cell')[0].click()
        self.wait_till_ajax_done(self.browser)
        rows = self.get_rows() 
        div_elements = rows[row_index+1].find_element_by_tag_name('td').find_elements_by_tag_name('label')
    #end get_expanded_api_data_in_webui        
    
    def parse_advanced_view(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className != 'preBlock'){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)        
        return  domArry
    #end parse_advanced_view

    def get_node_status_string(self, time):
        time = str(time)
        offset = 1 
        time_string = json.loads(self.browser.execute_script(" var startTime = new XDate(" + time +"/1000); var status = diffDates(startTime,XDate()); return JSON.stringify(status);"))
        if len(time_string.split()[:-1]) != 0 : 
            days_hrs = ' '.join(time_string.split()[:-1])  + ' '
        else : 
            days_hrs = None 

        minute_range = range(int(time_string.split()[-1][:-1]) - offset, int(time_string.split()[-1][:-1]) + offset + 1 )
        if days_hrs is not None:
            status_time_list = [days_hrs + str(minute) + 'm' for minute in minute_range]
        else : 
            status_time_list = [str(minute) + 'm' for minute in minute_range]
        return status_time_list

    def get_process_status_string(self, item, process_down_stop_time_dict, process_up_start_time_dict):
        offset = 1 
        last_start_time = int(0 if item['last_start_time'] is None else item['last_start_time'])
        last_stop_time = int(0 if item['last_stop_time'] is None else item['last_stop_time'])
        last_exit_time = int(0 if item['last_exit_time'] is None else item['last_exit_time'])
        if item['process_state'] == 'PROCESS_STATE_RUNNING' :
            status_time_list = self.get_node_status_string(last_start_time)
            status_string_list = ['Up since ' + status for status in status_time_list]
            process_up_start_time_dict[item['process_name']] = last_start_time
        else:
            down_time = max(last_stop_time, last_exit_time)
            status_down_time_list = self.get_node_status_string(down_time) 
            process_down_stop_time_dict[item['process_name']] = down_time
            status_string_list  = [ 'Down since ' + status for status in status_down_time_list]             
        return status_string_list

    def get_advanced_view_str(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length && eleList[j].className == 'string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)  
        return domArry
    #end get_advanced_view_str

    def get_advanced_view_str_special(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-2; i++){if(eleList[i].className == 'preBlock' && eleList[i + 2].className == 'expanded'){ var j = i + 2 , itemArry = [];  while(j < eleList.length && eleList[j].className != 'key' ){ if(eleList[j].className == 'string'){itemArry.push(eleList[j].innerHTML);}  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return domArry
    #end get_advanced_view_str

    def get_advanced_view_num(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className == 'preBlock' && eleList[i + 4].className == 'number'){dataSet.push({key : eleList[i+3].innerHTML, value : eleList[i + 4].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return  domArry
    #end get_advanced_view_num
   
    def get_basic_view_details(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('div.widget-main.row-fluid').find('label').find('div'),dataSet = []; for(var i = 0; i < eleList.length; i++){if(eleList[i].className == 'key span5' && eleList[i + 1].className == 'value span7'){dataSet.push({key : eleList[i].innerHTML,value:eleList[i+1].innerHTML.replace(/^\s+|\s+$/g, '')});}} return JSON.stringify(dataSet);"))
        return domArry

    def get_vm_basic_view(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('div.slick-row-detail-container').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className == 'span2' && eleList[i + 1].className == 'span10'){dataSet.push({key : eleList[i].getElementsByTagName('label')[0].innerHTML,value:eleList[i+1].innerHTML});}} return JSON.stringify(dataSet);"))
        return domArry
    def get_basic_view_infra(self):
        domArry = json.loads(self.browser.execute_script("var eleList = $('ul#detail-columns').find('li').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className== 'key span5' && eleList[i + 1].className == 'value span7'){dataSet.push({key : eleList[i].innerHTML.replace(/(&nbsp;)*/g,''),value:eleList[i+1].innerHTML.replace(/^\s+|\s+$/g, '')});}} return JSON.stringify(dataSet);")) 
        return domArry

    def trim_spl_char(self, d) :
        data = []    
        for item in d :
            if item['key'].endswith(':'):
                k = item['key'][:-1]
            else :
                k = item['key']
           
            if type(item['value']) is list:
                l =[]
                for g in range(len(item['value'])):
                    l.append(item['value'][g].replace('"',''))
            else:    
                l = item['value'].replace('"','')
            data.append({'key' : k, 'value' : l})         
        return data
        
    def get_items(self, d, key) :
        data = []    
        for item in d  :
            if item['key'] == key :
                data.append(item)
        return data  
    #end trim_spl_char

    def extract_keyvalue(self, dict_in, list_out):
        for key, value in dict_in.items():
            if isinstance(value, dict): # If value itself is dictionary
                self.extract_keyvalue(value, list_out)
            elif isinstance(value, list): # If value itself is list
                for val in value:
                    if isinstance(val, dict):
                        self.extract_keyvalue(val, list_out)
                    else:
                        dictn = {}
                        dictn['key'] = key
                        dictn['value'] = value
                        list_out.append(dictn)
                        break
            elif value == None :
                dictn = {}
                dictn['key'] = key
                dictn['value'] = None
                list_out.append(dictn)
            else:
                 dictn = {}
                 dictn['key'] = key
                 dictn['value'] = value
                 list_out.append(dictn)
    #end get_items
    def match_ops_values_with_webui(self, complete_ops_data, webui_list):
        error = 0
        for ops_items in complete_ops_data:
            match_flag = 0
            for webui_items in webui_list:
                if ops_items['value'] == webui_items['value'] or ops_items['value'].split(':')[0] == webui_items['value'] or (
                    ops_items['value'] == 'True' and ops_items['key'] == 'active' and webui_items['value'] == 'Active') :
                        self.logger.info("ops_key %s ops_value %s match with %s in webui" %(
                            ops_items['key'],ops_items['value'],webui_items['value'])) 
                        match_flag = 1
                        break
            if not match_flag:
                self.logger.error("ops_key %s ops_value %s not found/matched in webui" %(ops_items['key'],ops_items['value']))
                error = 1 
        return not error
    

    def date_time_string(self):
        current_date_time = str(datetime.datetime.now())
        return '_' + current_date_time.split()[0] + '_' + current_date_time.split()[1]

    def match_ops_with_webui(self, complete_ops_data, merged_arry) :
        self.logger.info("opserver data to be matched : %s"% complete_ops_data)
        self.logger.info("webui data to be matched : %s"%  merged_arry)
        self.logger.info(self.dash)
        no_error_flag = True
        match_count = 0 
        not_matched_count = 0 
        skipped_count = 0

        delete_key_list = ['in_tpkts','out_tpkts','bytes','ds_arp_not_me','in_bytes','out_bytes','in_pkts','out_pkts','sum','cpu_share','exception_packets_allowed','exception_packets','average_bytes','calls','b400000','b0.2','b1000','b0.1','res','b1','five_min_avg','one_min_avg','used','free','buffers','b200000','fifteen_min_avg']
        index_list = []
        for num in range(2):
            for element in complete_ops_data:
                if element['key'] in delete_key_list :
                    index = complete_ops_data.index(element)
                    del complete_ops_data[index]
                    skipped_count += 1
        
        for i in range(len(complete_ops_data)) :
            item_ops_key = complete_ops_data[i]['key']
            item_ops_value = complete_ops_data[i]['value']
            check_type_of_item_ops_value = not type(item_ops_value) is list
            matched_flag = 0
            webui_match_try_list = []
            key_found_flag = 0
            for j in range(len(merged_arry)) :
                matched_flag = 0
                item_webui_key = merged_arry[j]['key']
                item_webui_value = merged_arry[j]['value']
                check_type_of_item_webui_value = not type(item_webui_value) is list
                if ( item_ops_key == item_webui_key and ( item_ops_value == item_webui_value or (
                    item_ops_value == 'None' and item_webui_value == 'null'))) :
                    self.logger.info("ops/api key %s : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif (item_ops_key == item_webui_key and item_ops_value == 'True' and item_webui_value =='true' or item_ops_value == 'False' \
                    and item_webui_value =='false' or item_ops_key == 'build_info') :
                    if item_ops_key == 'build_info' :
                        self.logger.info("Skipping : ops key %s : value %s skipping match with webui key.. %s : value %s" %(
                            item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                        skipped_count =+1
                    else:
                        self.logger.info("ops/api key %s : value %s matched with webui key %s : value %s" %(
                            item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                        match_count += 1
                    matched_flag = 1
                    break
                    
                elif (check_type_of_item_webui_value and item_ops_key == item_webui_key and item_ops_value == (item_webui_value + '.0') ) : 
                    self.logger.info("ops/api key %s.0 : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and type(item_webui_value) is not list and type(item_ops_value) is list and ( item_webui_value in item_ops_value ) :
                    self.logger.info("webui key %s : value : %s matched in ops/api value range list %s " %(
                        item_webui_key, item_webui_value, item_ops_value))
                    matched_flag = 1
                    match_count += 1
                    break
                elif item_ops_key == item_webui_key and type(item_webui_value) is list and type(item_ops_value) is list:
                    count=0
                    if len(item_webui_value)==len(item_ops_value):
                        for item_webui_index in range(len(item_webui_value)):
                            for item_ops_index in range(len(item_ops_value)):
                                if (item_webui_value[item_webui_index] == item_ops_value[item_ops_index]):
                                    count += 1
                                    break 
                        if(count == len(item_webui_value)):
                            self.logger.info("ops key %s.0 : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                            matched_flag = 1
                            match_count += 1 
                    break       
                     
                elif item_ops_key == item_webui_key :
                    webui_match_try_list.append({'key':item_webui_key, 'value':item_webui_value})
                    key_found_flag = 1                    
            if not matched_flag : 
                #self.logger.error("ops key %s : value %s not matched with webui data"%(item_ops_key, item_ops_value))
                if key_found_flag :
                    self.logger.error("ops/api key %s : value %s not matched in webui key-value pairs list %s" %(item_ops_key, item_ops_value, webui_match_try_list))
                else : 
                    self.logger.error("ops/api key %s : value %s not found in webui" %(item_ops_key, item_ops_value ))
                not_matched_count += 1
                for k in range(len(merged_arry)) :
                    if item_ops_key ==  merged_arry[k]['key'] :
                        webui_key =  merged_arry[k]['key']
                        webui_value =  merged_arry[k]['value']
                no_error_flag = False
        self.logger.info("total ops/api key-value count is %s" % (str(len(complete_ops_data))))
        self.logger.info("total ops/api key-value match is %s" % (str(match_count)))
        self.logger.info("total ops/api key-value not matched count is %s" % str(not_matched_count))
        self.logger.info("total ops/api key-value match skipped count is %s" % str(skipped_count))
        return no_error_flag
    #end match_ops_with_webui                
                     
