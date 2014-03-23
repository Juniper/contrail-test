from netaddr import IPNetwork
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
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
import inspect
import policy_test_utils
import threading
import sys
from verification_util import *
import ConfigParser
import os
import logging
import datetime

def ajax_complete(driver):
        try:
            #print "AJAX:",driver.execute_script("return jQuery.active")
            return 0 == driver.execute_script("return jQuery.active")
        except WebDriverException:
            pass

class webui_common:
    def __init__(self):
        self.jsondrv = JsonDrv(self)

    def get_vn_list_api(self, fixture):
        url = 'http://' + fixture.inputs.openstack_ip + ':8082/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj

    def get_details(self, url):
        obj = self.jsondrv.load(url)
        return obj
    
    def get_vn_list_ops(self, fixture):
        url = 'http://' + fixture.inputs.openstack_ip + ':8081/analytics/uves/virtual-networks'
        obj = self.jsondrv.load(url)
        return obj

    def get_vm_list_ops(self, fixture):
        url = 'http://' + fixture.inputs.openstack_ip + ':8081/analytics/uves/virtual-machines'
        obj = self.jsondrv.load(url)
        return obj

    def log_msg(self, fixture, t, msg):
        if t == 'info' :
            fixture.logger.info(msg)
        elif t == 'error' :
            fixture.logger.error(msg)
        elif t == 'debug' : 
            fixture.logger.debug(msg)
        else:
            fixture.logger.info(msg)
        
        
     
    def click_configure_networks_in_webui(self, fixture):
        WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-configure')).click()
        fixture.browser.get_screenshot_as_file('con1.png')        
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        menu = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_class_name('icon-sitemap').click()
        fixture.browser.get_screenshot_as_file('con2.png')
        #WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        #time.sleep(1)
        config_net_vn = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('config_net_vn'))
        config_net_vn.find_element_by_link_text('Networks').click()
        fixture.browser.get_screenshot_as_file('con3.png')
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        time.sleep(1)

    def __wait_for_networking_items(self, a) :
        if len(a.find_element_by_id('config_net').find_elements_by_tag_name('li')) > 0 :
            return True        

    def click_configure_fip_in_webui(self, fixture):
        fixture.browser.find_element_by_id('btn-configure').click()
        #time.sleep(1)
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        menu = WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        time.sleep(1)
        WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('config_net_fip')).find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        time.sleep(1)
    
    def click_monitor_networks_in_webui(self, fixture):
        monitor = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        #time.sleep(3)
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        children = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu')
		).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        fixture.browser.get_screenshot_as_file('click_btn_mon_span.png')
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        mon_net_networks = WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
       # time.sleep(1)
       # fixture.browser.get_screenshot_as_file('click_btn_mon_net.png')
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        time.sleep(1)

    def click_monitor_instances_in_webui(self, fixture):
        monitor = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        #fixture.browser.get_screenshot_as_file('click_btn_monitor2.png')
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        menu = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        #time.sleep(1)
        mon_net_instances = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                'mon_net_instances'))
        mon_net_instances.find_element_by_link_text('Instances').click()
       # time.sleep(2)
  	WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        time.sleep(1)
         
    def click_monitor_networks_advance_in_webui(self, i, fixture):
        fixture.browser.find_element_by_link_text('Networks').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i+1].find_element_by_class_name('icon-cog').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows[i+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)

    def click_monitor_instances_advance_in_webui(self, i, fixture):
        fixture.browser.find_element_by_link_text('Instances').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i+1].find_element_by_class_name('icon-cog').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        rows[i+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)


    def verify_uuid_table(self, fixture, uuid):
        browser=fixture.browser
        delay=fixture.delay
        browser.find_element_by_id('btn-setting').click()
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        flag=1
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        total_pages=page_length[ln-1].get_attribute('data-page')
        length=int(total_pages)
        for l in range(0, length):
            if flag == 0:
                browser.find_element_by_id("cdb-results").find_element_by_xpath("//a[@title='Go to the next page']").click()
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
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
   
    def verify_fq_name_table(self,fixture,full_fq_name,fq_type) :
        browser=fixture.browser
        delay=fixture.delay
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

    def parse_advanced_view(self, fixture) :
        domArry = json.loads(fixture.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(i = 0; i < eleList.length; i++){if(eleList[i].className == 'key'){if(eleList[i + 1].className != 'preBlock'){dataSet.push({key : eleList[i].innerHTML, value : eleList[i + 1].innerHTML});}}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)        
        return  domArry

    def get_advanced_view_str(self, fixture) :
        domArry = json.loads(fixture.browser.execute_script("var eleList = $('pre').find('span'), dataSet = []; for(var i = 0; i < eleList.length; i++){if(eleList[i].className == 'key' && eleList[i + 4].className == 'string'){ var j = i + 4 , itemArry = [];  while(j < eleList.length && eleList[j].className == 'string' ){ itemArry.push(eleList[j].innerHTML);  j++;}  dataSet.push({key : eleList[i].innerHTML, value :itemArry});}} return JSON.stringify(dataSet);"))
        domArry = self.trim_spl_char(domArry)  
        return domArry

    def trim_spl_char(self, d) :
        data = []    
        for item in d :
            k = item['key'].replace(':','')
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
    def match_ops_with_webui(self, fixture, complete_ops_data, merged_arry) :
        #import pdb;pdb.set_trace()
        no_error_flag = True
        for i in range(len(complete_ops_data)) :
            item_ops_key = complete_ops_data[i]['key']
            item_ops_value = complete_ops_data[i]['value']
            matched_flag = 0
            for j in range(len(merged_arry)) :
                matched_flag = 0
                item_webui_key = merged_arry[j]['key']
                item_webui_value = merged_arry[j]['value']
                if ( item_ops_key == item_webui_key and ( item_ops_value == item_webui_value or (item_ops_value == 'None' and item_webui_value == 'null'))) :
                    fixture.logger.info("ops key %s : value %s matched with webui key %s : value %s" %(
                        item_ops_key,item_ops_value,item_webui_key,item_webui_value))
                   
                    matched_flag = 1
                    break
            if not matched_flag : 
                fixture.logger.error("ops key %s : value %s not matched with webui data"%(item_ops_key, item_ops_value))
                no_error_flag = False
        return no_error_flag
                
                     
    def close_all_popups(self, fixture):
        driver = fixture.browser
        driver.window_handles
        for h in driver.window_handles[1:]:
            driver.switch_to_window(h)
            driver.close()
        driver.switch_to_window(driver.window_handles[0]) 
