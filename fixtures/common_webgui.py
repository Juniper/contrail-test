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
import inspect
import policy_test_utils
import threading
import sys

def ajax_complete(driver):
        try:
            return 0 == driver.execute_script("return jQuery.active")
        except WebDriverException:
            pass

class common_webgui:
     
    def click_configure_networks_in_contrail_gui(self, fixture):
        WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'btn-configure')).click()
        time.sleep(4)
        menu = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        time.sleep(1)
        config_net_vn = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'config_net_vn'))
        time.sleep(1)
        config_net_vn.find_element_by_link_text('Networks').click()
        #WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        time.sleep(2)

    def click_monitor_networks_in_contrail_gui(self, fixture):

        monitor = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('btn-monitor')).click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        children = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('menu')
		).find_elements_by_class_name('item')
        children[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        mon_net_networks = WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('mon_net_networks'))
        mon_net_networks.find_element_by_link_text('Networks').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)


    def click_monitor_instances_in_contrail_gui(self, fixture):
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

    

    def verify_uuid_table(self, fixture, uuid):
        browser=fixture.browser
        delay=fixture.delay
	    #WebDriverWait(browser, delay).until(lambda a: a.find_element_by_id('btn-setting')).click()
        browser.find_element_by_id('btn-setting').click()	
        WebDriverWait(browser, delay).until(ajax_complete)
        browser.get_screenshot_as_file('test.png')
        uuid_btn=browser.find_element_by_id("setting_configdb_uuid").find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        flag=1
        page_length=browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_elements_by_tag_name('a')
        ln=len(page_length)
        page_length1=page_length[ln-1].get_attribute('data-page')
        length=int(page_length1)
        for l in range(length):
            if flag == 0:
               #import pdb;pdb.set_trace()
                page = browser.find_element_by_id("cdb-results").find_element_by_xpath("//div[@class='k-pager-wrap k-grid-pager k-widget']").find_element_by_tag_name("ul")
                page1 = page.find_elements_by_tag_name('li')
                time.sleep(4)
                page2 = page1[l].find_element_by_tag_name('a').click()
                WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
            row5=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
            row6=row5.find_elements_by_tag_name('a')
            for j in range(len(row6)):
                str2=row6[j].get_attribute("innerHTML")
                num1=str2.find(uuid)
                if num1!=-1:
                    flag=1
                    print str2
                    return True
                    break
                else:
                    flag=0

    def verify_fq_name_table(self,fixture,full_fq_name,fq_type) :
        #import pdb;pdb.set_trace()
        browser=fixture.browser
        delay=fixture.delay
        uuid=full_fq_name
        fq_name=fq_type
        btn_setting = WebDriverWait(browser, delay).until(lambda a: a.find_element_by_id('btn-setting')).click()
        WebDriverWait(browser, delay).until(ajax_complete,  "Timeout waiting for settings page to appear")
        #network validation in FQ name table
        row1=browser.find_element_by_id('main-content').find_element_by_id('cdb-results').find_element_by_tag_name('tbody')
        #import pdb;pdb.set_trace()
	# row2=row1.find_elements_by_tag_name('tr')
        obj_fq_name_table='obj_fq_name_table~' + fq_name
	#print obj_fq_name_table
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
                #fq1=fq.split(":")
                # if(fq1[2]==fixture.input_name and fq1[3]== uuid):       #network name is used and validated
                if(fq==uuid):
		            #print(" FQ validated in FQ Name Table")
                    flag=1
		    return True
                    break
                else:
                    flag=0
           if flag==1:
               break
    
    def launch_browser(self,fixture):
    
        if self.inputs.gui_flag=='True':
            #self.display = Display(visible=0, size=(800, 600))
            #self.display.start()
            fixture.browser = webdriver.Firefox()
            fixture.browser_openstack = webdriver.Firefox()
            fixture.delay=30
            fixture.login_contrail_gui(project_name=project_name,username=username,password=password)
            self.login_openstack_gui(project_name=project_name,username=username,password=password)
