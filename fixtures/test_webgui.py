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
from common_webgui import *
from test_webgui import *



class webgui_config_test:
    def __init__(self):
      self.common_webgui = common_webgui()
      self.proj_check_flag=0

    def create_vn_in_webgui(self, fixture):
        try:
            fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
            if not fixture.obj:
                fixture.logger.info("Creating VN %s using WebUI"%(fixture.vn_name))
                self.common_webgui.click_configure_networks_in_webui(fixture)
                btnCreateVN = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'btnCreateVN')).click()
                WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                txtVNName = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('txtVNName'))
                txtVNName.send_keys(fixture.vn_name)
                fixture.browser.find_element_by_id('txtIPBlock').send_keys(fixture.vn_subnets)
                fixture.browser.find_element_by_id('btnAddIPBlock').click()
                fixture.browser.find_element_by_id('btnCreateVNOK').click()
            else:
                fixture.already_present= True
                fixture.logger.info('VN %s already exists, skipping creation ' %(fixture.vn_name) )
                fixture.logger.debug('VN %s exists, already there' %(fixture.vn_name) )
            fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
            fixture.vn_id= fixture.obj['network']['id']
            fixture.vn_fq_name=':'.join(fixture.obj['network']['contrail:fq_name'])
        except Exception as e:
            with fixture.lock:
                fixture.logger.exception("Got exception as %s while creating %s"%(e,fixture.vn_name))
                sys.exit(-1)

    def verify_vn_in_webgui(self, fixture):
        self.common_webgui.click_configure_networks_in_webui(fixture)
        rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vn_flag=0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name and rows[i].find_elements_by_tag_name(
                'td')[4].text==fixture.vn_subnets[0]) :
                vn_flag=1
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                ip_blocks=rows[i+1].find_element_by_class_name('span11').text.split('\n')[1]
                if (ip_blocks.split(' ')[0]==':'.join(fixture.ipam_fq_name) and ip_blocks.split(' ')[1]==fixture.vn_subnets[0]):
                    fixture.logger.info( "vn name %s and ip block %s verified in configure page " %(fixture.vn_name,fixture.vn_subnets))
                else:
                    fixture.logger.error( "ip block details failed to verify in configure page %s " %(fixture.vn_subnets))
                    fixture.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
                    vn_flag=0
                break
        assert vn_flag,"Verifications in WebUI for VN name and subnet %s failed in configure page" %(fixture.vn_name)
        self.common_webgui.click_monitor_networks_in_webui(fixture)
        rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vn_entry_flag=0
        for i in range(len(rows)):
            fq_name=rows[i].find_elements_by_tag_name('a')[1].text
            if(fq_name==fixture.ipam_fq_name[0]+":"+fixture.project_name+":"+fixture.vn_name):
                fixture.logger.info( " %s VN verified in monitor page " %(fq_name))
                vn_entry_flag=1
                break
        if not vn_entry_flag:
            fixture.logger.error( "VN %s Verification failed in monitor page %s " %(fixture.vn_name))
            fixture.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
        if vn_entry_flag:
            fixture.logger.info( "Verifications in WebUI for VN %s name and subnet passed in config and monitor pages" %(fixture.vn_name))
        #if self.common_webgui.verify_uuid_table(fixture, fixture.vn_id):
	#    fixture.logger.info( "VN %s UUID verified in table " %(fixture.vn_name))
        #else:
	#    fixture.logger.error( "VN %s UUID Verification failed in table " %(fixture.vn_name))
        #    fixture.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
	fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
        fq_type='virtual_network'
        full_fq_name=fixture.vn_fq_name+':'+fixture.vn_id
        if self.common_webgui.verify_fq_name_table(fixture, full_fq_name, fq_type):
            fixture.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        else:
            fixture.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
            fixture.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        return True

    def vn_delete_in_webgui(self, fixture):

        self.common_webgui.click_configure_networks_in_webui(fixture)
        rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        for net in rows :
            if (net.find_elements_by_tag_name('td')[2].text==fixture.vn_name):
                net.find_elements_by_tag_name('td')[1].find_element_by_tag_name('input').click()
                break
        fixture.browser.find_element_by_id('btnDeleteVN').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        fixture.logger.info("%s is deleted successfully using WebUI"%(fixture.vn_name))
        fixture.browser.find_element_by_id('btnCnfRemoveMainPopupOK').click()

    def create_vm_in_openstack(self, fixture):
        try:
            if not self.proj_check_flag:
                WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
                WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_css_selector('h4')).click()
                WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_id('tenant_list')).click()
                current_project=WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_css_selector('h3')).text
                if not current_project==fixture.project_name:
                    WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_css_selector('h3')).click()
                    WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text(fixture.project_name)).click()
                    WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)                    
                    self.proj_check_flag = 1
            
	    WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
            instance = WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text('Instances')).click()
            #instance.click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
            time.sleep(3)
            launch_instance = WebDriverWait(fixture.browser_openstack, fixture.delay).until(
                lambda a: a.find_element_by_link_text('Launch Instance')).click()
            time.sleep(3)
            fixture.logger.debug('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            fixture.logger.info('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            time.sleep(2)
            fixture.browser_openstack.find_element_by_xpath(
                "//select[@name='image_id']/option[text()='"+fixture.image_name+"']").click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_id(
                'id_name')).send_keys(fixture.vm_name)
            fixture.browser_openstack.find_element_by_xpath(
                "//select[@name='flavor']/option[text()='m1.small']").click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            networks=WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_id
                ('available_network')).find_elements_by_tag_name('li')
            for net in networks:
                vn_match=net.text.split('(')[0]
                if (vn_match==fixture.vn_name) :
                    net.find_element_by_class_name('btn').click()
                    break
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
            #time.sleep(5)
            fixture.logger.debug('VM %s launched using openstack' %(fixture.vm_name) )
            fixture.logger.info('waiting for VM %s to come into active state' %(fixture.vm_name) )
            time.sleep(10)
            rows_os = fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                        'tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows_os)):
                #rows_os = fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                #    'tbody').find_elements_by_tag_name('tr')
                rows_os = fixture.browser_openstack.find_element_by_tag_name('form')
                rows_os = WebDriverWait(rows_os, fixture.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
                rows_os = WebDriverWait(rows_os, fixture.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
                
                if(rows_os[i].find_elements_by_tag_name('td')[1].text==fixture.vm_name):
                    counter=0
                    vm_active=False
                    while not vm_active :
                        if(fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name('td')[5].text=='Active'):
                            fixture.logger.info("%s is Active Now" %(fixture.vm_name))
                            vm_active=True
                        elif(fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name('td')[5].text=='Error'):
                            fixture.logger.error("%s went into Error state" %(fixture.vm_name))
                            fixture.browser_openstack.get_screenshot_as_file('verify_vm_state_openstack_'+'fixture.vm_name'+'.png')
                            return "Error"
                        else:
                            fixture.logger.info("%s is not yet Active Now waiting for more time" %(fixture.vm_name))
                            counter=counter+1
                            time.sleep(3)
                            fixture.browser_openstack.find_element_by_link_text('Instances').click()
                            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
                            time.sleep(3)
                            if(counter>=100):
                                fixuture.logger.error("Vm failed to come in active state %s" %(fixture.vm_name) )
                                fixture.browser_openstack.get_screenshot_as_file('verify_vm_not_active_openstack_'+'fixture.vm_name'+'.png')
                                break
            fixture.vm_obj = fixture.nova_fixture.get_vm_if_present(fixture.vm_name, fixture.project_fixture.uuid)
            fixture.vm_objs = fixture.nova_fixture.get_vm_list(name_pattern=fixture.vm_name,project_id=fixture.project_fixture.uuid)      
        except ValueError :
            fixture.logger.error('Error while creating VM %s with image name %s failed in openstack'
                %(fixture.vm_name,fixture.image_name))
            fixture.browser_openstack.get_screenshot_as_file('verify_vm_error_openstack_'+'fixture.vm_name'+'.png')

    def vm_delete_in_openstack(self, fixture):
        rows = fixture.browser_openstack.find_element_by_id('instances').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        for instance in rows:
            if fixture.vm_name==instance.find_element_by_tag_name('a').text:
                instance.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                break
        ln = len(rows)
        launch_instance = WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_id('instances__action_terminate')).click()
        WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text('Terminate Instances')).click()
        time.sleep(5)
        fixture.logger.info("VM %s deleted successfully using openstack"%(fixture.vm_name))

    def verify_vm_in_webgui(self,fixture):
        try :
            self.common_webgui.click_monitor_instances_in_webui(fixture)        
            #time.sleep(1)
            rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
            ln = len(rows)
            vm_flag=0
            for i in range(len(rows)):
                vm_name=rows[i].find_elements_by_tag_name('td')[1].find_element_by_tag_name('div').text 
                vm_uuid=rows[i].find_elements_by_tag_name('td')[2].text
                vm_vn=rows[i].find_elements_by_tag_name('td')[3].text.split(' ')[0]
       
                if(vm_name == fixture.vm_name and fixture.vm_obj.id==vm_uuid and fixture.vn_name==vm_vn) :
                    rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)             
                    #fixture.browser.find_element_by_xpath("//*[@id='mon_net_instances']").find_element_by_tag_name('a').click()
                    #rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    #    'tbody').find_elements_by_tag_name('tr')
                    #rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows=WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_class_name(
                        'k-grid-content')).find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
 
                    vm_status=rows[i+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_xpath(
                        "//*[@style='width:85px;float:left']")[1].text
                    vm_ip=rows[i+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_xpath(
                        "//*[@style='width:95px;float:left']")[2].text
                    assert vm_status=='Active'
                    assert vm_ip==fixture.vm_ip
                    vm_flag=1
                    break
            assert vm_flag,"vm name or vm uuid or vm ip or vm status verifications in WebUI for VM %s failed" %(fixture.vm_name)
            fixture.browser.get_screenshot_as_file('vm_create_check.png')
            fixture.logger.info("Vm name,vm uuid,vm ip and vm status,vm network verification in WebUI for VM %s passed" %(fixture.vm_name) )
            mon_net_networks = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                'mon_net_networks')).find_element_by_link_text('Networks').click()
            WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
            rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                if(rows[i].find_elements_by_tag_name('a')[1].text==fixture.vn_fq_name.split(':')[0]+":"+fixture.project_name+":"+fixture.vn_name):
                    rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                    rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    vm_ids=rows[i+1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_tag_name('div')[15].text
                    if fixture.vm_id in vm_ids:
                        fixture.logger.info( "vm_id matched in network basic detail monitor pagae %s" %(fixture.vn_name))
                    else :
                        fixture.logger.error("vm_id not matched in network basic detail monitor page %s" %(fixture.vm_name))
                        fixture.browser.get_screenshot_as_file('monitor_page_vm_id_not_match'+fixture.vm_name+fixture.vm_id+'.png')
                    break
            #if self.common_webgui.verify_uuid_table(fixture,fixture.vm_id):
            #    self.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            #else:
            #    self.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            fq_type='virtual_machine'
            full_fq_name=fixture.vm_id+":"+fixture.vm_id
            if self.common_webgui.verify_fq_name_table(fixture,full_fq_name,fq_type):
               fixture.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            else:
               fixture.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            fixture.logger.info("VM verification in WebUI %s passed" %(fixture.vm_name) ) 
            return True
        except ValueError :
                    fixture.logger.error("vm %s test error " %(fixture.vm_name))
                    fixture.browser.get_screenshot_as_file('verify_vm_test_openstack_error'+'fixture.vm_name'+'.png')

    def create_floatingip_pool_webgui(self, fixture, pool_name, vn_name):
        try :
                #Navigate to Configure tab
            self.common_webgui.click_configure_networks_in_webui(fixture)
            #time.sleep(2)
            rows = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('gridVN'))
            rows = WebDriverWait(rows, fixture.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
            rows =  WebDriverWait(rows, fixture.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    net.find_element_by_class_name('dropdown-toggle').click()
                    net.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
                    ip_text =  net.find_element_by_xpath("//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath('..').find_element_by_tag_name('i').click()
                    route = fixture.browser.find_element_by_xpath("//div[@title='Add Floating IP Pool below']")
                    route.find_element_by_class_name('icon-plus').click()
                    fixture.browser.find_element_by_xpath("//input[@placeholder='Pool Name']").send_keys(fixture.pool_name)
                    pool_con = fixture.browser.find_element_by_id('fipTuples')
                    pool_con.find_element_by_class_name('k-multiselect-wrap').click()
                    ip_ul= fixture.browser.find_element_by_xpath("//ul[@aria-hidden = 'false']")
                    ip_ul.find_elements_by_tag_name('li')[0].click()
                    fixture.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    fixture.logger.info( "fip pool %s created using WebUI" %(fixture.pool_name))		   

                    break
        except ValueError :
                    fixture.logger.error("fip %s Error while creating floating ip pool " %(fixture.pool_name))

    def create_and_assoc_fip_webgui(self, fixture, fip_pool_vn_id, vm_id , vm_name,project = None):
        try :
            fixture.vm_name=vm_name
            fixture.vm_id=vm_id
            self.common_webgui.click_configure_networks_in_webui(fixture)
            #time.sleep(3)
            rows = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('gridVN'))
            rows = WebDriverWait(rows, fixture.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
            rows =  WebDriverWait(rows, fixture.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
            #time.sleep(3)
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    fixture.browser.find_element_by_xpath("//*[@id='config_net_fip']/a").click()
                    WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                    fixture.browser.find_element_by_xpath("//button[@id='btnCreatefip']").click()
                    time.sleep(3)
                    pool=fixture.browser.find_element_by_xpath("//div[@id='windowCreatefip']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                    time.sleep(3)
                    fip=fixture.browser.find_element_by_id("ddFipPool_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML")==fixture.vn_name+':'+fixture.pool_name:
                            fip[i].click()
                    fixture.browser.find_element_by_id('btnCreatefipOK').click()
                    time.sleep(2)
                    rows1=fixture.browser.find_elements_by_xpath("//tbody/tr")
                    for element in rows1:
                        if element.find_elements_by_tag_name('td')[3].text==fixture.vn_name+':'+fixture.pool_name:
                            element.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                                'div').find_element_by_tag_name('div').click()
                            element.find_element_by_xpath("//a[@class='tooltip-success']").click()
                            WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                            break
                    pool=fixture.browser.find_element_by_xpath("//div[@id='windowAssociate']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                    time.sleep(3)
                    fip=fixture.browser.find_element_by_id("ddAssociate_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML").split(' ')[1]==vm_id :
                            fip[i].click()
                    fixture.browser.find_element_by_id('btnAssociatePopupOK').click()
                    verify_fip_webgui(self)
                    break
        except ValueError :
            fixture.logger.info("Error while creating floating ip and associating it to a VM Test.")

    def verify_fip_webgui(self, fixture):
        self.common_webgui.click_configure_networks_in_webui(fixture)
        rows = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
            'gridVN')).find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            vn_name=rows[i].find_elements_by_tag_name('td')[2].text
            if vn_name==fixture.vn_name:
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fip_check=rows[i+1].find_elements_by_xpath("//td/div/div/div")[1].text
                if fip_check.split('\n')[1].split(' ')[0]==fixture.pool_name:
                    fixture.logger.info( "fip pool %s verified in WebUI configure network page" %(fixture.pool_name))
                    break
        WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_xpath("//*[@id='config_net_fip']/a")).click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        rows = fixture.browser.find_element_by_xpath("//div[@id='gridfip']/table/tbody").find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            fip=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[1]
            vn=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[0]
            fip_ip=rows[i].find_elements_by_tag_name('td')[1].text
            if rows[i].find_elements_by_tag_name('td')[2].text==fixture.vm_id :
                if vn==fixture.vn_name and fip==fixture.pool_name:
                    fixture.logger.info("FIP  is found attached with vm %s "%(fixture.vm_name))  
                    fixture.logger.info("VM %s is found associated with FIP %s "%(fixture.vm_name,fip))
                else :
                    fixture.logger.info("Association of %s VM failed with FIP %s "%(fixture.vm_name,fip))
                    break
        self.common_webgui.click_monitor_instances_in_webui(fixture)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vm_flag=0
        for i in range(len(rows)):
            vm_name=rows[i].find_elements_by_tag_name('td')[1].find_element_by_tag_name('div').text
            vm_uuid=rows[i].find_elements_by_tag_name('td')[2].text
            vm_vn=rows[i].find_elements_by_tag_name('td')[3].text.split(' ')[0]
            if(vm_name == fixture.vm_name and fixture.vm_id==vm_uuid and vm_vn==fixture.vn_name) :
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
                rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fip_check_vm=rows[i+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]"
	            ).find_elements_by_tag_name('div')[0].find_elements_by_tag_name('div')[1].text
                if fip_check_vm.split(' ')[0]==fip_ip and fip_check_vm.split(
	            ' ')[1]=='\('+'default-domain'+':'+fixture.project_name+':'+fixture.vn_name+'\)' :
                    fixture.logger.info("FIP verified in monitor instance page for vm %s "%(fixture.vm_name))
                else :
                   fixture.logger.info("FIP failed to verify in monitor instance page for vm %s"%(fixture.vm_name))		  	
                   break

    def delete_fip_webgui(self, fixture):
        fixture.browser.find_element_by_id('btn-configure').click()
        menu = WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('menu'))
        children = menu.find_elements_by_class_name('item')[1].find_element_by_class_name('dropdown-toggle').find_element_by_tag_name('span').click()
        WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('config_net_fip')).find_element_by_tag_name('a').click()
        WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)
        rows = fixture.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
             
        for net in rows:
            if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vm_id) :
                net.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                    'div').find_element_by_tag_name('div').click()
                net.find_element_by_xpath("//a[@class='tooltip-error']").click()             
                WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnDisassociatePopupOK')).click()        
                WebDriverWait(fixture.browser, fixture.delay).until(ajax_complete)     
            rows = fixture.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')       
            for net in rows:
                if (net.find_elements_by_tag_name('td')[3].get_attribute('innerHTML') == fixture.vn_name+':'+fixture.pool_name) :
                    net.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                    WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnDeletefip')).click()
                    WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnCnfReleasePopupOK')).click()                   
                   
            self.common_webgui.click_configure_networks_in_webui(fixture)
            rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    net.find_element_by_class_name('dropdown-toggle').click()
                    net.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
                    ip_text =  net.find_element_by_xpath("//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath('..').find_element_by_tag_name('i').click()
                    pool_con = fixture.browser.find_element_by_id('fipTuples')
                    fip=pool_con.find_elements_by_xpath("//*[contains(@id, 'rule')]")
                    for pool in fip:
                        if(pool.find_element_by_tag_name('input').get_attribute('value')==fixture.pool_name):
                            pool.find_element_by_class_name('icon-minus').click()
                    fixture.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    break      
