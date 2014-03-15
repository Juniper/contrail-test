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


def ajax_complete(driver):
        try:
            return 0 == driver.execute_script("return jQuery.active")
        except WebDriverException:
            pass

class webui_common:
    def __init__(self):
        self.jsondrv = JsonDrv(self)
        #self.config = ConfigParser.ConfigParser()
        
        #self.host_name = self.config.get('openstack_host_name','openstack_host_name')
        #if 'PARAMS_FILE' in os.environ :
        #    self.ini_file= os.environ.get('PARAMS_FILE')
        #else:
        #    self.ini_file= 'params.ini'
        #self.config.read(ini_file)
        #self.config= config
        #logging.config.fileConfig(ini_file)
        #self.logger_key='log01'
        #self.logger= logging.getLogger(self.logger_key)

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
        url = 'http://' + fixture.inputs.openstack_ip + ':8081/analytics/uves/virtual-machine'
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
        WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'btn-configure')).click()
        menu = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        time.sleep(1)
        config_net_vn = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'config_net_vn'))
        time.sleep(1)
        config_net_vn.find_element_by_link_text('Networks').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
    
    def click_monitor_networks_in_webui(self, fixture):

        monitor = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        children = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu')
		).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        mon_net_networks = WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)


    def click_monitor_instances_in_webui(self, fixture):
        monitor = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        time.sleep(1)
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        menu = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        time.sleep(1)
        mon_net_instances = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                'mon_net_instances'))
        mon_net_instances.find_element_by_link_text('Instances').click()
  	WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
           
    def click_monitor_networks_advance_in_webui(self, i, fixture):
        fixture.browser.find_element_by_link_text('Networks').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        rows[i+1].find_element_by_class_name('icon-cog').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        rows[i+1].find_element_by_class_name('k-detail-cell').find_elements_by_tag_name('li')[1].find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)

    def verify_uuid_table(self, fixture, uuid):
        browser=fixture.browser
        delay=fixture.delay
        browser.find_element_by_id('btn-setting').click()
        WebDriverWait(browser, delay).until(ajax_complete)
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        flag=1
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        total_pages=page_length[ln-1].get_attribute('data-page')
        length=int(total_pages)
        for l in range(0, length):
            if flag == 0:
                browser.find_element_by_id("cdb-results").find_element_by_xpath("//a[@title='Go to the next page']").click()
                WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        row5=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
        row6=row5.find_elements_by_tag_name('a')
        for k in range(len(row6)):
                str2=row6[k].get_attribute("innerHTML")
                num1=str2.find(uuid)
                if num1!=-1:
                    print("network validated in UUId")
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
            data.append({'key' : k, 'value' : item['value']})         
        return data
   
        
    def get_items(self, d, key) :
        data = []    
        for item in d  :
            if item['key'] == key :
                data.append(item)
        return data  

    def extract_keyvalue(self, dict_in, dict_out):
       
        for key, value in dict_in.items():
            if isinstance(value, dict): # If value itself is dictionary
                self.extract_keyvalue(value, dict_out)
            elif isinstance(value, list): # If value itself is list
                for val in value:
                    if isinstance(val, dict):
                        self.extract_keyvalue(val, dict_out)
                    else:
                        dict_out[key] = value
            else:
                dict_out[key] = value
