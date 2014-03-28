#from netaddr import IPNetwork
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import time
#import random
#import self.
#from netaddr import *
#from time import sleep
#import ConfigParser
#import os
import logging
#import datetime
from util import *
from vnc_api.vnc_api import *
from verification_util import *

def ajax_complete(driver):
        try:
            #print "AJAX:",driver.execute_script("return jQuery.active")
            return 0 == driver.execute_script("return jQuery.active")
        except WebDriverException:
            pass

class webui_common:
    def __init__(self, webui_test):
        self.jsondrv = JsonDrv(self)
        self.delay = 30
        self.webui = webui_test
        self.inputs= self.webui.inputs
        self.connections= self.webui.connections
        self.browser= self.webui.browser
        self.browser_openstack = self.webui.browser_openstack
        self.delay = 30
        self.frequency = 1
        self.logger= self.inputs.logger

    def get_service_instance_list_api(self):
        url = 'http://' + self.inputs.openstack_ip + ':8082/service-instances'
        obj = self.jsondrv.load(url)
        return obj


    def get_service_chains_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/service-chains'
        obj = self.jsondrv.load(url)
        return obj

    def get_generators_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/generators'
        obj = self.jsondrv.load(url)
        return obj

    def get_bgp_peers_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/bgp-peers'
        obj = self.jsondrv.load(url)
        return obj

    def get_vrouters_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/vrouters'
        obj = self.jsondrv.load(url)
        return obj

    
    def get_dns_nodes_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/dns-nodes'
        obj = self.jsondrv.load(url)
        return obj

    def get_collectors_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/collectors'
        obj = self.jsondrv.load(url)
        return obj


    def get_bgp_routers_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/bgp-routers'
        obj = self.jsondrv.load(url)
        return obj

    def get_config_nodes_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/config-nodes'
        obj = self.jsondrv.load(url)
        return obj

    def get_modules_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/modules'
        obj = self.jsondrv.load(url)
        return obj

    def get_service_instances_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/service-instances'
        obj = self.jsondrv.load(url)
        return obj

    def get_vn_list_api(self):
        url = 'http://' + self.inputs.openstack_ip + ':8082/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj

    def get_details(self, url):
        obj = self.jsondrv.load(url)
        return obj
    
    def get_vn_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj

    def get_xmpp_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/xmpp-peers'
        obj = self.jsondrv.load(url)
        return obj

    def get_vm_list_ops(self):
        url = 'http://' + self.inputs.openstack_ip + ':8081/analytics/uves/virtual-machines'
        obj = self.jsondrv.load(url)
        return obj

    def log_msg(self, t, msg):
        if t == 'info' :
            self.logger.info(msg)
        elif t == 'error' :
            self.logger.error(msg)
        elif t == 'debug' : 
            self.logger.debug(msg)
        else:
            self.logger.info(msg)
    
    def click_monitor_vrouters_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[0].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_compute'))
        mon_net_networks.find_element_by_link_text('Virtual Routers').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)
   
    def click_monitor_config_nodes_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[0].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_config'))
        mon_net_networks.find_element_by_link_text('Config Nodes').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)

    def click_monitor_control_nodes_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[0].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_control'))
        mon_net_networks.find_element_by_link_text('Control Nodes').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)
        
    def click_monitor_analytics_nodes_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
                ).find_elements_by_class_name('item')
        children[0].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_infra_analytics'))
        mon_net_networks.find_element_by_link_text('Analytics Nodes').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)

      
    def click_configure_networks_in_webui(self):
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        self.browser.get_screenshot_as_file('con1.png')        
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        self.browser.get_screenshot_as_file('con2.png')
        #WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        #time.sleep(1)
        config_net_vn = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('config_net_vn'))
        config_net_vn.find_element_by_link_text('Networks').click()
        self.browser.get_screenshot_as_file('con3.png')
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)

    def __wait_for_networking_items(self, a) :
        if len(a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0 :
            return True        

    def click_configure_fip_in_webui(self):
        
        self.browser.find_element_by_id('btn-configure').click()
        #time.sleep(1)
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        menu = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)
        WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('config_net_fip')).find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)
    
    def click_monitor_networks_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        #time.sleep(3)
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        children = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu')
		).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        self.browser.get_screenshot_as_file('click_btn_mon_span.png')
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
       # time.sleep(1)
       # self.browser.get_screenshot_as_file('click_btn_mon_net.png')
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)

    def click_monitor_instances_in_webui(self):
        monitor = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        #self.browser.get_screenshot_as_file('click_btn_monitor2.png')
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        menu = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        #time.sleep(1)
        mon_net_instances = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
                'mon_net_instances'))
        mon_net_instances.find_element_by_link_text('Instances').click()
       # time.sleep(2)
  	WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        time.sleep(1)
         
    def click_monitor_vrouters_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Virtual Routers').click()
        self.click_monitor_common_advance_in_webui(i)

    def click_monitor_config_nodes_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Config Nodes').click()
        self.click_monitor_common_advance_in_webui(i)

    def click_monitor_control_nodes_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Control Nodes').click()
        self.click_monitor_common_advance_in_webui(i)

    def click_monitor_analytics_nodes_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Analytics Nodes').click()
        self.click_monitor_common_advance_in_webui(i)


    def click_monitor_common_advance_in_webui(self, i) : 
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-cog').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        self.browser.find_element_by_class_name('contrail').find_element_by_class_name('icon-code').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
 
    def click_monitor_networks_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Networks').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i+1].find_element_by_class_name('icon-cog').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows[i+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)

    def click_monitor_instances_advance_in_webui(self, i):
        self.browser.find_element_by_link_text('Instances').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i+1].find_element_by_class_name('icon-cog').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows[i+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)


    def verify_uuid_table(self, uuid):
        browser=self.browser
        delay=self.delay
        browser.find_element_by_id('btn-setting').click()
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        flag=1
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        total_pages=page_length[ln-1].get_attribute('data-page')
        length=int(total_pages)
        for l in range(0, length):
            if flag == 0:
                browser.find_element_by_id("cdb-results").find_element_by_xpath("//a[@title='Go to the next page']").click()
                WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
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
   
    def verify_fq_name_table(self, full_fq_name, fq_type) :
        browser=self.browser
        delay=self.delay
        uuid=full_fq_name
        fq_name=fq_type
        btn_setting = WebDriverWait(browser, delay).until(lambda a: a.find_element_by_id('btn-setting')).click()
        WebDriverWait(browser, delay).until(ajax_complete,  "Timeout waiting for settings page to appear")
        #network validation in FQ name table
        row1=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
        obj_fq_name_table='obj_fq_name_table~' + fq_name
        row1.find_element_by_xpath("//*[@id='"+obj_fq_name_table+"']").click()
        WebDriverWait(browser, delay).until(ajax_complete,  "Timeout waiting for page to appear")
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        page_length1=int(page_length[ln-1].get_attribute('data-page'))
        flag=1
        for l in range(page_length1):
           if flag==0:
                page=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_element_by_tag_name("ul")
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

    def check_element_exists_by_xpath(self, webdriver, xpath):
        try:
            webdriver.find_element_by_xpath(xpath)
        except NoSuchElementException:
            return False
        return True   
    
    def get_expanded_api_data_in_webui(self, i) :
        i = 1
        self.click_configure_networks_in_webui()
        import pdb;pdb.set_trace()
        rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr') 
        #rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].click()
        WebDriverWait(self.browser, self.delay, self.frequency).until(ajax_complete)
        rows = self.browser.find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        div_elements = rows[i+1].find_element_by_tag_name('td').find_elements_by_tag_name('label')
        for ele in range(len(div_elements)) :
            print ele
        
        
 
    
    def parse_advanced_view(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className != 'preBlock'){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)        
        return  domArry

    def get_advanced_view_str(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length-4 && eleList[j].className == 'string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)  
        return domArry

    def get_advanced_view_num(self) :
        domArry = json.loads(self.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length-4; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className == 'preBlock' && eleList[i + 4].className == 'number'){dataSet.push({key : eleList[i+3].innerHTML, value : eleList[i + 4].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)
        return  domArry
    def trim_spl_char(self, d) :
        data = []    
        for item in d :
            #import pdb;pdb.set_trace()
            #print item['key']
            #k = item['key'].replace(':','')
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
            else:
                 dictn = {}
                 dictn['key'] = key
                 dictn['value'] = value
                 list_out.append(dictn)
                #dict_out[key] = value
    def match_ops_with_webui(self, complete_ops_data, merged_arry) :
        no_error_flag = True
        match_count = 0 
        not_matched_count = 0 
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
                if ( item_ops_key == item_webui_key and ( item_ops_value == item_webui_value or (item_ops_value == 'None' and item_webui_value == 'null'))) :
                #if ( item_ops_key == item_webui_key ) :
                
                   # self.logger.info("ops key %s :  matched with webui key : %s" %(item_ops_key, item_webui_key)) 
                   # if ( item_ops_value == item_webui_value or (item_ops_value == 'None' and item_webui_value == 'null')) : 
                    self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1 
                    break
                    #else : 
                    #    self.logger.error("key matched but not values :ops key %s : value %s not matched with key : %s value : %s webui data"%(item_ops_key, item_ops_value, item_webui_key, item_webui_value))  
                    #self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                    #    item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    #matched_flag = 1
                    #break
                elif (item_ops_key == item_webui_key and item_ops_value == 'True' and item_webui_value =='true' or item_ops_value == 'False' and item_webui_value =='false') :
                    #self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                    #   item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    self.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
                    #check_type_of_item_ops_value = if not type(item_ops_value) is list
                    
                elif (check_type_of_item_webui_value and item_ops_key == item_webui_key and item_ops_value == (item_webui_value + '.0') ) : 
                    self.logger.info("ops key %s.0 : value %s matched with webui key %s : value %s" %(
                        item_ops_key, item_ops_value, item_webui_key, item_webui_value))
                    matched_flag = 1
                    match_count += 1
                    break
                #else :
                #    self.logger.error("ops key type %s [%s] : not matched with key : type %s [%s]"%(type(item_ops_key),item_ops_key, type(item_webui_key),item_webui_key))
                    #break
            if not matched_flag : 
                #import pdb;pdb.set_trace()
                self.logger.error("ops key %s : value %s not matched with webui data"%(item_ops_key, item_ops_value))
                not_matched_count += 1
                for k in range(len(merged_arry)) :
                    if item_ops_key ==  merged_arry[k]['key'] :
                        #print item_ops_key
                        #print merged_arry[k]['key']
                        webui_key =  merged_arry[k]['key']
                        webui_value =  merged_arry[k]['value']
                        #print item_ops_value 
                        #print webui_value
                        #self.logger.error("ops key [%s] : value [%s] not match with webui key [%s] value [%s] "%(
                        #    item_ops_key, item_ops_value, webui_key, webui_value))
                        #import pdb;pdb.set_trace()
                no_error_flag = False
        print "total ops key-value count is " + str(len(complete_ops_data))
        print "total ops key-value match is " + str(match_count)
        print "total ops not matched count is " + str(not_matched_count)
        return no_error_flag
                
                     
