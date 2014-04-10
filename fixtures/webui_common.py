from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import time
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

class webui_common:
    def __init__(self, webui_test):
        self.jsondrv = JsonDrv(self)
        self.delay = 90
        self.webui = webui_test
        self.inputs = self.webui.inputs
        self.connections = self.webui.connections
        self.browser = self.webui.browser
        self.browser_openstack = self.webui.browser_openstack
        self.frequency = 1
        self.logger = self.inputs.logger
    
    def wait_till_ajax_done(self):
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete) 
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
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/collectors'
        obj = self.jsondrv.load(url)
        return obj

    #end get_collectors_list_ops

    def get_bgp_routers_list_ops(self):
        url = 'http://' + self.inputs.collector_ip + ':8081/analytics/uves/bgp-routers'
        obj = self.jsondrv.load(url)
        return obj
    #end get_bgp_routers_list_ops

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

    def click_monitor_instances_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Instances').click()
        self.wait_till_ajax_done()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done()
        rows[row_index+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done()
    #end click_monitor_instances_basic_in_webui

    def click_monitor_networks_basic_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done()
        rows[row_index+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done()
    #end click_monitor_instances_basic_in_webui
    
    def click_monitor_common_basic_in_webui(self, row_index) :
        self.wait_till_ajax_done()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done()
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done()
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-list').click()
        self.wait_till_ajax_done()
    #end click_monitor_common_advance_in_webui

    
    def click_monitor_vrouters_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_compute'))
        mon_net_networks.find_element_by_link_text('Virtual Routers').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_monitor_vrouters_in_webui
   
    def click_monitor_config_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_config'))
        mon_net_networks.find_element_by_link_text('Config Nodes').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_monitor_config_nodes_in_webui

    def click_monitor_control_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_control'))
        mon_net_networks.find_element_by_link_text('Control Nodes').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_monitor_control_nodes_in_webui
        
    def click_monitor_analytics_nodes_in_webui(self):
        self.click_monitor_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_analytics'))
        mon_net_networks.find_element_by_link_text('Analytics Nodes').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_monitor_analytics_nodes_in_webui
   
    def click_configure_networks_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        time.sleep(2)
        self.wait_till_ajax_done() 
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        time.sleep(2)
        self.browser.get_screenshot_as_file('click_networks.png') 
        config_net_vn = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_net_vn'))
        config_net_vn.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_configure_networks_in_webui

    def __wait_for_networking_items(self, a) :
        if len(a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0 :
            return True        
    #end __wait_for_networking_items

    def click_configure_fip_in_webui(self):
        self.browser.find_element_by_id('btn-configure').click()
        self.wait_till_ajax_done() 
        menu = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
        WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('config_net_fip')).find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_configure_fip_in_webui
    
    def click_monitor_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        self.wait_till_ajax_done()

    def click_monitor_networking_in_webui(self):
        self.click_monitor_in_webui()
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.browser.get_screenshot_as_file('click_btn_mon_span.png')
        time.sleep(2)
        self.wait_till_ajax_done()
    #end click_monitor_in_webui
 
    def click_monitor_networks_in_webui(self):
        self.click_monitor_networking_in_webui()
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done() 
        time.sleep(1)
    #end click_monitor_networks_in_webui

    def click_monitor_instances_in_webui(self):
        self.click_monitor_networking_in_webui()
        mon_net_instances = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('mon_net_instances'))
        mon_net_instances.find_element_by_link_text('Instances').click()
  	self.wait_till_ajax_done()
        time.sleep(1)
    #end click_monitor_instances_in_webui
         
    def click_monitor_vrouters_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Virtual Routers').click()
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_vrouters_advance_in_webui

    def click_monitor_config_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Config Nodes').click()
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_config_nodes_advance_in_webui

    def click_monitor_control_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Control Nodes').click()
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_control_nodes_advance_in_webui

    def click_monitor_analytics_nodes_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Analytics Nodes').click()
        self.click_monitor_common_advance_in_webui(row_index)
    #end click_monitor_analytics_nodes_advance_in_webui
    
    def click_monitor_common_advance_in_webui(self, row_index) : 
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done() 
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-code').click()
        self.wait_till_ajax_done() 
    #end click_monitor_common_advance_in_webui

    def click_monitor_networks_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Networks').click()
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done() 
        rows[row_index+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
    #end click_monitor_networks_advance_in_webui

    def click_monitor_instances_advance_in_webui(self, row_index):
        self.browser.find_element_by_link_text('Instances').click()
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[row_index+1].find_element_by_class_name('icon-cog').click()
        self.wait_till_ajax_done() 
        rows[row_index+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
    #end click_monitor_instances_advance_in_webui

    def verify_uuid_table(self, uuid):
        browser=self.browser
        delay=self.delay
        browser.find_element_by_id('btn-setting').click()
        time.sleep(2)
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        self.wait_till_ajax_done() 
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
                self.wait_till_ajax_done() 
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
        WebDriverWait(browser, delay).until(ajax_complete,  "Timeout waiting for page to appear")
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
                WebDriverWait(browser, delay).until(ajax_complete,  "Timeout waiting for page to appear")
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
    
    def get_expanded_api_data_in_webui(self, row_index) :
        i = 1
        self.click_configure_networks_in_webui()
        rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr') 
        rows[row_index].find_elements_by_tag_name('td')[0].click()
        self.wait_till_ajax_done() 
        rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        div_elements = rows[row_index+1].find_element_by_tag_name('td').find_elements_by_tag_name('label')
    #end get_expanded_api_data_in_webui        
    
    def parse_advanced_view(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className != 'preBlock'){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)        
        return  domArry
    #end parse_advanced_view

    def get_advanced_view_str(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length && eleList[j].className == 'string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
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
        domArry = json.loads(self.browser.execute_script("var eleList = $('td.k-detail-cell').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className == 'span2' && eleList[i + 1].className == 'span10'){dataSet.push({key : eleList[i].getElementsByTagName('label')[0].innerHTML,value:eleList[i+1].innerHTML});}} return JSON.stringify(dataSet);"))
        return domArry
    def get_basic_view_infra(self):
        domArry = json.loads(self.browser.execute_script("var eleList = $('ul#detail-columns').find('li').find('div'),dataSet = []; for(var i = 0; i < eleList.length-1; i++){if(eleList[i].className== 'key span5' && eleList[i + 1].className == 'value span7'){dataSet.push({key : eleList[i].innerHTML,value:eleList[i+1].innerHTML.replace(/^\s+|\s+$/g, '')});}}")) 
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

    def match_ops_with_webui(self, complete_ops_data, merged_arry) :
        no_error_flag = True
        match_count = 0 
        not_matched_count = 0 
        skipped_count = 0
        for i in range(len(complete_ops_data)) :
            item_ops_key = complete_ops_data[i]['key']
            item_ops_value = complete_ops_data[i]['value']
            check_type_of_item_ops_value = not type(item_ops_value) is list
            matched_flag = 0
            for j in range(len(merged_arry)) :
                matched_flag = 0
                item_webui_key = merged_arry[j]['key']
                item_webui_value = merged_arry[j]['value']
                check_type_of_item_webui_value = not type(item_webui_value) is list
                if ( item_ops_key == item_webui_key and ( item_ops_value == item_webui_value or (
                    item_ops_value == 'None' and item_webui_value == 'null'))) :
                    self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
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
                        self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                            item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                        match_count += 1
                    matched_flag = 1
                    break
                    
                elif (check_type_of_item_webui_value and item_ops_key == item_webui_key and item_ops_value == (item_webui_value + '.0') ) : 
                    self.logger.info("ops key %s.0 : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
            if not matched_flag : 
                self.logger.error("ops key %s : value %s not matched with webui data"%(item_ops_key, item_ops_value))
                not_matched_count += 1
                for k in range(len(merged_arry)) :
                    if item_ops_key ==  merged_arry[k]['key'] :
                        webui_key =  merged_arry[k]['key']
                        webui_value =  merged_arry[k]['value']
                no_error_flag = False
        self.logger.info("total ops key-value count is %s" % (str(len(complete_ops_data))))
        self.logger.info("total ops key-value match is %s" % (str(match_count)))
        self.logger.info("total ops key-value not matched count is %s" % str(not_matched_count))
        self.logger.info("total ops key-value match skipped count is %s" % str(skipped_count))
        return no_error_flag
    #end match_ops_with_webui                
                     
