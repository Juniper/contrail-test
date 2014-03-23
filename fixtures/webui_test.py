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
from webui_test import *
from webui_common import *


class webui_test:
    def __init__(self):
      self.webui_common = webui_common()
      self.proj_check_flag=0
      
    def create_vn_in_webui(self, fixture):
        try:
            fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
            if not fixture.obj:
                fixture.logger.info("Creating VN %s using WebUI..."%(fixture.vn_name))
                self.webui_common.click_configure_networks_in_webui(fixture)
                fixture.browser.get_screenshot_as_file('btn_createVN.png')                
                btnCreateVN = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id(
                        'btnCreateVN')).click()
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                txtVNName = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('txtVNName'))
                txtVNName.send_keys(fixture.vn_name)
                fixture.browser.find_element_by_id('txtIPBlock').send_keys(fixture.vn_subnets)
                fixture.browser.find_element_by_id('btnAddIPBlock').click()
                fixture.browser.find_element_by_id('btnCreateVNOK').click()
                time.sleep(3)
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

    def verify_vn_ops_advance_data_in_webui(self, fixture):
        fixture.logger.info("Verifying VN ops-data in Webui...")
        fixture.logger.info("-------------------------------------------------------") 
        self.webui_common.click_monitor_networks_in_webui(fixture)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vn_list_ops = self.webui_common.get_vn_list_ops(fixture) 
        #fixture.logger.info("VN details for %s got from  ops server and going to match in webui : " %(vn_list_ops))
        for n in range(len(vn_list_ops)):
            ops_fqname = vn_list_ops[n]['name']
            fixture.logger.info("vn fq name %s exists in op server..checking if exists in webui as well"%(ops_fqname))
            self.webui_common.click_monitor_networks_in_webui(fixture)
            rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            print ops_fqname
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[1].text == ops_fqname:
                    fixture.logger.info("vn fq name %s found in webui..going to match advance details now"%(ops_fqname))
                    fixture.logger.info("-------------------------------------------------------------------------------")
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                fixture.logger.error("vn fqname %s did not match in webui...not found in webui"%(ops_fqname))
                fixture.logger.info("-------------------------------------------------------------------------------")
            else:
        #for i in range(len(rows)):
                fixture.logger.info("Click and Retrieve advance details in webui for fqname %s "%(ops_fqname))
                self.webui_common.click_monitor_networks_advance_in_webui(match_index, fixture)
                dom_arry = self.webui_common.parse_advanced_view(fixture)
                dom_arry_str = self.webui_common.get_advanced_view_str(fixture)
                print dom_arry
                print dom_arry_str
                merged_arry = dom_arry + dom_arry_str
                fixture.logger.info("VN fqname %s advance details retrieved from webui adavance page %s "%(ops_fqname, merged_arry))
                #dict_arry = {}
                #for item in merged_arry:
            #    dict_arry[ item['key'] ] = item['value']
                vn_ops_data = self.webui_common.get_details(vn_list_ops[n]['href'])   
                #fixture.logger.info("VN advanced details for %s got from ops server and going to match in webui : " %(vn_ops_data ))
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data = vn_ops_data['UveVirtualNetworkConfig']
                    #modified_ops_data = {}
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                 
                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    ops_data_agent = vn_ops_data['UveVirtualNetworkAgent']
                    fixture.logger.info("VN details for %s  got from  ops server and going to match in webui : \n %s \n " %(vn_list_ops[i]['href'],ops_data_agent))
                    modified_ops_data_agent = []
                    self.webui_common.extract_keyvalue(ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list :
                            #print complete_ops_data[k]['key']
                            #print complete_ops_data[k]['value']
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode :
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(fixture, complete_ops_data, merged_arry):
                        fixture.logger.info("ops vn data matched in webui")
                    else :
                        fixture.logger.error("ops vn data match failed in webui") 
                '''
                for key in modified_ops_data_agent :
                    if type(modified_ops_data_agent[key]) is list:
                        for element in modified_ops_data_agent[key]:
                            element = str(element)
                    else:
                        modified_ops_data_agent[key] = str(modified_ops_data_agent[key])

                if self.webui_common.match_ops_with_webui(fixture, complete_ops_data, merged_arry):
                    fixture.logger.info("ops vn data matched in webui")
                else :
                    fixture.logger.error("ops vn data match failed in webui")        
                    
                for key in modified_ops_data_agent:
                    if type(modified_ops_data_agent[key]) is list :
                        for i in range(len(modified_ops_data_agent[key])):
                            modified_ops_data_agent[key][i] = '"'+ str(modified_ops_data_agent[key][i]) + '"'
                    elif type(modified_ops_data_agent[key]) is unicode :
                        modified_ops_data_agent[key] = '"' + modified_ops_data_agent[key] + '"'
                    else:
                        modified_ops_data_agent[key] =  str(modified_ops_data_agent[key])
                for key in modified_ops_data_agent :
                    if type(modified_ops_data_agent[key]) is list:
                        for element in modified_ops_data_agent[key]:
                            element = str(element)
                    else:
                        modified_ops_data_agent[key] = str(modified_ops_data_agent[key])    
                for key in modified_ops_data_agent:
                    if type(modified_ops_data_agent[key]) is list :
                        if not cmp(modified_ops_data_agent[key],dict_arry[key]):
                            print modified_ops_data_agent[key],dict_arry[key]
                            fixture.logger.info(" key : %s - value : %s matched in webui with opserver data" %(key, modified_ops_data_agent[key]))
                        else: 
                            fixture.logger.error("key : %s - value : %s not matched in webui with opserver data" %(key, modified_ops_data_agent[key]))
                    elif modified_ops_data_agent[key] == 'None' :
                        if dict_arry[key]== 'null':
                            fixture.logger.info(" key : %s - value : %s matched in webui with opserver data" %(key,modified_ops_data_agent[key]))
                        else:
                            fixture.logger.error("key : %s - value : %s not matched in webui with opserver data " %(key,modified_ops_data_agent[key]))
                            flag =0
                    else:
                        if modified_ops_data_agent[key] == dict_arry[key]:
                            fixture.logger.info("key : %s - value : %s matched in webui with opserver data for vn " %(key,modified_ops_data_agent[key]))
                        else:
                            fixture.logger.error("key:%s - value:%s not matched in webui with opserver data for vn " %(key,modified_ops_data_agent[key]))
                            flag =0
            else: 
                fixture.logger.info(" opserver has no UveVirtualNetworkAgent for vn %s url "%(vn_list_ops[i]['href']))
            '''
    def verify_vm_ops_advance_data_in_webui(self, fixture):
        fixture.logger.info("Verifying VM ops-data in Webui...")
        fixture.logger.info("-------------------------------------------------------")
        self.webui_common.click_monitor_instances_in_webui(fixture)
        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vm_list_ops = self.webui_common.get_vm_list_ops(fixture)
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            fixture.logger.info("vm uuid %s exists in op server..checking if exists in webui as well"%(ops_uuid)) 
            for i in range(len(rows)):
                match_flag = 0 
                if rows[i].find_elements_by_tag_name('td')[2].text == ops_uuid:
                    fixture.logger.info("vm uuid %s matched in webui..going to match advance details now"%(ops_uuid))
                    fixture.logger.info("-------------------------------------------------------------------------------")
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                fixture.logger.error("uuid exists in opserver but uuid %s not found in webui..."%(ops_uuid))
                fixture.logger.info("-------------------------------------------------------------------------------")
                
            self.webui_common.click_monitor_instances_advance_in_webui(match_index, fixture)
            fixture.logger.info("Click and Retrieve advance details in webui for uuid %s "%(ops_uuid))
            dom_arry = self.webui_common.parse_advanced_view(fixture)
            print dom_arry
            dom_arry_str = []
            #dom_arry_str = self.webui_common.get_advanced_view_str(fixture)
            print dom_arry
            print dom_arry_str
            merged_arry = dom_arry + dom_arry_str
            vm_ops_data = self.webui_common.get_details(vm_list_ops[k]['href'])
            if vm_ops_data.has_key('UveVirtualMachineAgent'):
                ops_data = vm_ops_data['UveVirtualMachineAgent']
                modified_ops_data = []
                self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                complete_ops_data = modified_ops_data
                for t in range(len(complete_ops_data)):
                    if type(complete_ops_data[t]['value']) is list :
                        for m in range(len(complete_ops_data[t]['value'])):
                            complete_ops_data[t]['value'][m] = str(complete_ops_data[t]['value'][m])
                    elif type(complete_ops_data[t]['value']) is unicode :
                        complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
                    else:
                        complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
                if self.webui_common.match_ops_with_webui(fixture, complete_ops_data, merged_arry):
                    fixture.logger.info("ops vm data matched in webui")
                else :
                    fixture.logger.error("ops vm data match failed in webui")
                
    def verify_vn_api_data_in_webui(self, fixture):
        # get VN list from API"
        fixture.logger.info("Verifying VN %s api-data in Webui..."%(fixture.vn_name))
        fixture.logger.info("-------------------------------------------------------")
        vn_list = self.webui_common.get_vn_list_api(fixture)
        fixture.logger.info("VN list got from API server : %s  " %(vn_list))
        vn_list = vn_list['virtual-networks'] 
        ln=len(vn_list)-3
        self.webui_common.click_configure_networks_in_webui(fixture)
        #time.sleep(3)
        #fixture.browser.get_screenshot_as_file('verify_vn_api_data_failed.png')      
        rows = fixture.browser.find_element_by_id('gridVN')
        rows = rows.find_element_by_tag_name('tbody')
        rows = rows.find_elements_by_tag_name('tr')
        if ln != len(rows):
            fixture.logger.error("vn rows in grid mismatch with VNs in api")
        for i in range(ln):
            details  =  self.webui_common.get_details(vn_list[i]['href'])
            fixture.logger.info("VN details for %s got from API server and going to match in webui : " %(vn_list[i]))
            #print ln
            #print details['virtual-network']['fq_name'][2]
            j=0
            for j in range(len(rows)):
                self.webui_common.click_configure_networks_in_webui(fixture)
                fixture.browser.get_screenshot_as_file('config_net_verify_api.png')
                rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]) :
                    #print details['virtual-network']['fq_name'][2]+" matched in UI"
                    #print "---------"
                    ##print rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML')
                    vn_name = details['virtual-network']['fq_name'][2]
                    #print details['virtual-network']['fq_name'][2]
                    ip_block=details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix']+'/'+ str(
                        details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix_len'])
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        fixture.logger.info( "VN %s : ip block matched" %(vn_name))
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    ui_ip_block=rows[j+1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(
                        ' ')[1] == ip_block and ui_ip_block.split(
                            ' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway'] ):
                        fixture.logger.info( "VN %s basic details in webui network config page matched with api data " %(vn_name))
                    else:
                        fixture.logger.error( "VN %s basic details in webui network config page not matched with api data" %(vn_name))
                        fixture.browser.get_screenshot_as_file('verify_vn_api_data_webui_basic_details_failed.png')
                    forwarding_mode=rows[j+1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan=rows[j+1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = { 'l2_l3':'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        fixture.logger.info( " VN %s : forwarding mode matched "  %(vn_name) )
                    else :
                        fixture.logger.error( "VN %s : forwarding mode not matched" %(vn_name))
                        fixture.browser.get_screenshot_as_file('verify_vn_api_data__forwarding_mode_match_failed.png')

                    if details['virtual-network']['virtual_network_properties']['vxlan_network_identifier'] == None :
                        vxlan_api = 'Automatic'
                    else : 
                        vxlan_api = details['virtual-network']['virtual_network_properties']['vxlan_network_identifier']
                    if vxlan_api == vxlan :
                        fixture.logger.info( " VN %s : vxlan matched "  %(vn_name) )
                    else :
                        fixture.logger.error( "VN %s : vxlan not matched" %(vn_name))
                        fixture.browser.get_screenshot_as_file('verify_vn_api_basic_data_vxlan_failed.png')
                    xpath = "//label[contains(text(), 'Floating IP Pools')]"
                    driver = rows[j+1]
               
                    if details['virtual-network'].has_key('floating_ip_pools') : 
                        floating_ip_length_api =  len(details['virtual-network']['floating_ip_pools'])
                        fixture.logger.info(" %s FIP/s exist in api for network %s " %( floating_ip_length_api,vn_name ))

                        if self.webui_common.check_element_exists_by_xpath(driver, xpath):
                            fip_ui = rows[j+1].find_element_by_xpath("//label[contains(text(), 'Floating IP Pools')]/..").text.split('\n')[1:]
                            for n in range(floating_ip_length_api) :
                                fip_api = details['virtual-network']['floating_ip_pools'][n]['to']
                                if fip_ui[n] == fip_api[3] + ' (' + fip_api[0] + ':' + fip_api[1] + ')' :
                                    fixture.logger.info(" %s FIP/s matched in webui with api data " %( fip_api ))
                        else: 
                            fixture.logger.error( "fip element mismatch happened in webui and api ")
                            fixture.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
                    else :
                        fixture.logger.info( "Not verifying FIP as it is not found in API ") 
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    break
                
                elif (j == range(len(rows))):
                    fixture.logger.info( "%s is not matched in webui"%( details['virtual-network']['fq_name'][2]))
                    #print details['virtual-network']['fq_name'][2]+" is not matched in UI"

    def verify_vm_ops_data_in_webui(self, fixture):
        fixture.logger.info("Verifying VN %s ops-data in Webui..." %(fixture.vn_name))
        vm_list = self.webui_common.get_vm_list_ops(fixture)
        
        self.webui_common.click_monitor_instances_in_webui(fixture)
        rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        # verify vm count in webui and opserver
        if len(rows) != len(vm_list) :
            fixture.logger.error( " VM count in webui and opserver not matched  ")    
        else:
            fixture.logger.info( " VM count in webui and opserver matched")
        #compare vm basic data in webui and opserver
        for i in range(len(vm_list)):
            vm_name = vm_list[i]['name']
            
               
    def verify_vn_ops_data_in_webui(self, fixture):
        vn_list = self.webui_common.get_vn_list_ops(fixture)
        fixture.logger.info("VN details for %s got from ops server and going to match in webui : " %(vn_list))
        self.webui_common.click_configure_networks_in_webui(fixture)
        rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln=len(vn_list)
        
        for i in range(ln):
            vn_name = vn_list[i]['name']
            details  =  self.webui_common.get_vn_details(vn_list[i]['href'])
            UveVirtualNetworkConfig
            if details.has_key('UveVirtualNetwokConfig'):
                total_acl_rules_ops
            if details.has_key('UveVirtualNetworkAgent'):
                UveVirtualNetworkAgent_dict = details['UveVirtualNetworkAgent']
                egress_flow_count_api = details['UveVirtualNetworkAgent']['egress_flow_count']
                ingress_flow_count_api = details['UveVirtualNetworkAgent']['ingress_flow_count']    
                interface_list_count_api = len(details['UveVirtualNetworkAgent']['interface_list_count'])
                total_acl_rules_count = details['UveVirtualNetworkAgent']['total_acl_rules']
                #print UveVirtualNetworkAgent_dict
                #print ingress_flow_count_api 
                #print interface_list_count_api
                #print total_acl_rules_count
                if self.webui_common.check_element_exists_by_xpath(row[j+1],"//label[contains(text(), 'Ingress Flows')]" ):
                            #ingress_ui = rows[j+1].find_elements_by_xpath("//label[contains(text(), 'Ingress Flows')]/..")[1].text
                            for n in range(floating_ip_length_api) :
                                fip_api = details['virtual-network']['floating_ip_pools'][n]['to']
                                if fip_ui[n] == fip_api[3] + ' (' + fip_api[0] + ':' + fip_api[1] + ')' :
                                    fixture.logger.info( " fip matched ")
            #print details
            self.webui_common.click_monitor_networks_in_webui(fixture)
            for j in range(len(rows)):
                rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                   'tbody').find_elements_by_tag_name('tr')
                 
        #if ln != len(rows):
        #    fixture.logger.error("vn rows in monitor grid are less than expected")
                fq_name=rows[j].find_elements_by_tag_name('a')[1].text
                if(fq_name==vn_list[i]['name']):
                    fixture.logger.info( " %s VN verified in monitor page " %(fq_name))
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    expanded_row = rows[j+1].find_element_by_class_name('inline row-fluid position-relative pull-right margin-0-5')
                    expanded_row.find_element_by_class_name('icon-cog icon-only bigger-110').click()
                    expanded_row.find_elements_by_tag_name('a')[1].click()
                    #print ingress_flow_ui.find_elements_by_tag_name('div')[1].text
                    basicdetails_ui_data=rows[j+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name("row-fluid")
                    ingress_ui = basicdetails_ui_data[0].text.split('\n')[1]
                    egress_ui = basicdetails_ui_data[1].text.split('\n')[1]
                    acl_ui = basicdetails_ui_data[2].text.split('\n')[1]
                    intf_ui = basicdetails_ui_data[3].text.split('\n')[1]     
                    vrf_ui = basicdetails_ui_data[4].text.split('\n')[1]
                    #print ingress,egress,acl,intf
                   # if details['UveVirtualNetworkConfig']['total_acl_rules'] ==  basicdetails_ui_data[].text
                    #print basicdetails_data
                    break
                else:
                    fixture.logger.error( " %s VN not found in monitor page " %(fq_name))
            details  =  self.webui_common.get_vn_details_api(vn_list[i]['href'])
            #print details
            #print ln
            
            j=0
            for j in range(len(rows)):
                self.webui_common.click_monitor_networks_in_webui(fixture)
                rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]) :
                    #print details['virtual-network']['fq_name'][2]+" verified in WebUI"
                    #print "---------"
                    #print rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML')
                    #print details['virtual-network']['fq_name'][2]
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        fixture.logger.info( "ip blocks verified ") 
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    ui_ip_block=rows[j+1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(' ')[1] == ip_block and ui_ip_block.split(' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway'] ):
                        fixture.logger.info( "ip block and details matched in webui advance details ")
                    else:
                        fixture.logger.error( "not matched")
                    forwarding_mode=rows[j+1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan=rows[j+1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = { 'l2_l3':'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        fixture.logger.info( " forwarding mode matched ")
                    else :
                        fixture.logger.error( "forwarding mode not matched ")

                    if details['virtual-network']['virtual_network_properties']['vxlan_network_identifier'] == None :
                        vxlan_api = 'Automatic'
                    else :
                        vxlan_api = details['virtual-network']['virtual_network_properties']['vxlan_network_identifier']
                    if vxlan_api == vxlan :
                        fixture.logger.info( " vxlan matched ")
                    else :
                        fixture.logger.info( " vxlan not matched ")
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    break

                elif (j == range(len(rows))):
                    #print details['virtual-network']['fq_name'][2]+" is not matched in UI"  
                    fixture.logger.info( "vn name %s : %s is not matched in webui  " %(fixture.vn_name,details['virtual-network']['fq_name'][2]))
  
    def verify_vn_in_webui(self, fixture):
        fixture.browser.get_screenshot_as_file('vm_verify.png')
        self.webui_common.click_configure_networks_in_webui(fixture)
        time.sleep(2)
        rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vn_flag=0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name and rows[i].find_elements_by_tag_name(
                'td')[4].text==fixture.vn_subnets[0]) :
                vn_flag=1
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                time.sleep(2)
                #WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                ip_blocks=rows[i+1].find_element_by_class_name('span11').text.split('\n')[1]
                if (ip_blocks.split(' ')[0]==':'.join(fixture.ipam_fq_name) and ip_blocks.split(' ')[1]==fixture.vn_subnets[0]):
                    fixture.logger.info( "vn name %s and ip block %s verified in configure page " %(fixture.vn_name,fixture.vn_subnets))
                else:
                    fixture.logger.error( "ip block details failed to verify in configure page %s " %(fixture.vn_subnets))
                    fixture.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
                    vn_flag=0
                break
        #assert vn_flag,"Verifications in WebUI for VN name and subnet %s failed in configure page" %(fixture.vn_name)
        self.webui_common.click_monitor_networks_in_webui(fixture) 
        time.sleep(3)
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
            fixture.logger.info( " VN %s and subnet verified in webui config and monitor pages" %(fixture.vn_name))
        if self.webui_common.verify_uuid_table(fixture, fixture.vn_id):
            fixture.logger.info( "VN %s UUID verified in webui table " %(fixture.vn_name))
        else:
            fixture.logger.error( "VN %s UUID Verification failed in webui table " %(fixture.vn_name))
            fixture.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
        fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
        fq_type='virtual_network'
        full_fq_name=fixture.vn_fq_name+':'+fixture.vn_id
        if self.webui_common.verify_fq_name_table(fixture, full_fq_name, fq_type):
            fixture.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        else:
            fixture.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
            fixture.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        #fixture.logger.info( "Verifying VN API data in Webui...")
        #self.verify_vn_api_data_in_webui(fixture)
        return True

    def vn_delete_in_webui(self, fixture):
        fixture.browser.get_screenshot_as_file('vm_delete.png')
        self.webui_common.click_configure_networks_in_webui(fixture)
        
        rows = fixture.browser.find_element_by_id('gridVN').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        for net in rows :
            if (net.find_elements_by_tag_name('td')[2].text==fixture.vn_name):
                net.find_elements_by_tag_name('td')[1].find_element_by_tag_name('input').click()
                break
        fixture.browser.find_element_by_id('btnDeleteVN').click()
        
        #WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
        fixture.logger.info("%s is deleted successfully using WebUI"%(fixture.vn_name))
        fixture.browser.find_element_by_id('btnCnfRemoveMainPopupOK').click()

    def create_vm_in_openstack(self, fixture):
        try:
            if not self.proj_check_flag:
                WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
                time.sleep(1)
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
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
            #time.sleep(3)
            fixture.nova_fixture.get_image(image_name=fixture.image_name)
            time.sleep(2)
            launch_instance = WebDriverWait(fixture.browser_openstack, fixture.delay).until(
                lambda a: a.find_element_by_link_text('Launch Instance')).click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
            #time.sleep(3)
            fixture.logger.debug('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            fixture.logger.info('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            #time.sleep(2)
            fixture.browser_openstack.find_element_by_xpath(
                "//select[@name='source_type']/option[contains(text(), 'image') or contains(text(),'Image')]").click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete) 
            #fixture.browser_openstack.find_element_by_xpath( "//select[@name='image_id']/option[text()='"+fixture.image_name+"']").click()
            fixture.browser_openstack.find_element_by_xpath( "//select[@name='image_id']/option[contains(text(), '" + fixture.image_name + "')]").click()
            WebDriverWait(fixture.browser_openstack, fixture.delay).until(lambda a: a.find_element_by_id(
                'id_name')).send_keys(fixture.vm_name)
            fixture.browser_openstack.find_element_by_xpath(
                "//select[@name='flavor']/option[text()='m1.medium']").click()
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
            fixture.logger.debug('VM %s launched using openstack' %(fixture.vm_name) )
            fixture.logger.info('waiting for VM %s to come into active state' %(fixture.vm_name) )
            time.sleep(5)
            rows_os = fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                        'tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows_os)):
                rows_os = fixture.browser_openstack.find_element_by_tag_name('form')
                rows_os = WebDriverWait(rows_os, fixture.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
                rows_os = WebDriverWait(rows_os, fixture.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
                
                if(rows_os[i].find_elements_by_tag_name('td')[1].text==fixture.vm_name):
                    counter=0
                    vm_active=False
                    while not vm_active :
                        vm_active_status1 = fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name(
                                'td')[6].text  
                        vm_active_status2 = fixture.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                                    'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name('td')[5].text

                        if(vm_active_status1 =='Active' or vm_active_status2 =='Active'):
                            fixture.logger.info("%s status is Active now in openstack" %(fixture.vm_name))
                            vm_active=True
                            time.sleep(5)
                        elif(vm_active_status1 == 'Error' or vm_active_status2 =='Error'):
                            fixture.logger.error("%s state went into Error state in openstack" %(fixture.vm_name))
                            fixture.browser_openstack.get_screenshot_as_file('verify_vm_state_openstack_'+'fixture.vm_name'+'.png')
                            return "Error"
                        else:
                            fixture.logger.info("%s state is not yet Active in openstack, waiting for more time..." %(fixture.vm_name))
                            counter=counter+1
                            time.sleep(3)
                            fixture.browser_openstack.find_element_by_link_text('Instances').click()
                            WebDriverWait(fixture.browser_openstack, fixture.delay).until(ajax_complete)
                            time.sleep(3)
                            if(counter>=100):
                                fixuture.logger.error("VM %s failed to come into active state" %(fixture.vm_name) )
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
    
    def verify_vm_in_webui(self,fixture):
        try :
            self.webui_common.click_monitor_instances_in_webui(fixture)        
            print "click crossed"
            rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
            ln = len(rows)
            vm_flag=0
            for i in range(len(rows)):
                rows_count = len(rows)
                vm_name=rows[i].find_elements_by_tag_name('td')[1].find_element_by_tag_name('div').text 
                vm_uuid=rows[i].find_elements_by_tag_name('td')[2].text
                vm_vn=rows[i].find_elements_by_tag_name('td')[3].text.split(' ')[0]
                if(vm_name == fixture.vm_name and fixture.vm_obj.id==vm_uuid and fixture.vn_name==vm_vn) :
                    print "vm found now will verify basic details"
                    retry_count = 0
                    while True :
                        print "count is" + str(retry_count)
                        if retry_count > 20 : 
                            fixture.logger.error('vm details failed to load')
                            break 
                        fixture.browser.find_element_by_xpath("//*[@id='mon_net_instances']").find_element_by_tag_name('a').click()
                        time.sleep(1)
                        rows = fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                        ##webdriver has issue here 
                        #WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                        #time.sleep(2)
                        try :
                            retry_count = retry_count + 1 
                            WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                            break
                        except WebDriverException:
                            pass

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
            time.sleep(2)
            WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
            rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                if(rows[i].find_elements_by_tag_name('a')[1].text==fixture.vn_fq_name.split(':')[0]+":"+fixture.project_name+":"+fixture.vn_name):
                    rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                    rows=fixture.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    vm_ids=rows[i+1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_tag_name('div')[15].text
                    if fixture.vm_id in vm_ids:
                        fixture.logger.info( "vm_id matched in webui monitor network basic details page %s" %(fixture.vn_name))
                    else :
                        fixture.logger.error("vm_id not matched in webui monitor network basic details page %s" %(fixture.vm_name))
                        fixture.browser.get_screenshot_as_file('monitor_page_vm_id_not_match'+fixture.vm_name+fixture.vm_id+'.png')
                    break
            if self.webui_common.verify_uuid_table(fixture,fixture.vm_id):
                fixture.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            else:
                fixture.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            fq_type='virtual_machine'
            full_fq_name=fixture.vm_id+":"+fixture.vm_id
            if self.webui_common.verify_fq_name_table(fixture,full_fq_name,fq_type):
               fixture.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            else:
               fixture.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            fixture.logger.info("VM verification in WebUI %s passed" %(fixture.vm_name) ) 
            return True
        except ValueError :
                    fixture.logger.error("vm %s test error " %(fixture.vm_name))
                    fixture.browser.get_screenshot_as_file('verify_vm_test_openstack_error'+'fixture.vm_name'+'.png')

    def create_floatingip_pool_webui(self, fixture, pool_name, vn_name):
        try :
            self.webui_common.click_configure_networks_in_webui(fixture)
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
                    WebDriverWait(fixture.browser, fixture.delay,fixture.frequency).until(ajax_complete)
                    fixture.browser.find_element_by_xpath("//input[@placeholder='Pool Name']").send_keys(fixture.pool_name)
                    pool_con = fixture.browser.find_element_by_id('fipTuples')
                    pool_con.find_element_by_class_name('k-multiselect-wrap').click()
                    WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                    ip_ul= fixture.browser.find_element_by_xpath("//ul[@aria-hidden = 'false']")
                    ip_ul.find_elements_by_tag_name('li')[0].click()
                    fixture.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    WebDriverWait(fixture.browser, fixture.delay,fixture.frequency).until(ajax_complete)
                    time.sleep(2)
                    fixture.logger.info( "fip pool %s created using WebUI" %(fixture.pool_name))		   

                    break
        except ValueError :
                    fixture.logger.error("fip %s Error while creating floating ip pool " %(fixture.pool_name))

    def create_and_assoc_fip_webui(self, fixture, fip_pool_vn_id, vm_id , vm_name,project = None):
        try :
            fixture.vm_name=vm_name
            fixture.vm_id=vm_id
            self.webui_common.click_configure_networks_in_webui(fixture)
            rows = WebDriverWait(fixture.browser, fixture.delay).until(lambda a: a.find_element_by_id('gridVN'))
            rows = WebDriverWait(rows, fixture.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
            rows =  WebDriverWait(rows, fixture.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    fixture.browser.find_element_by_xpath("//*[@id='config_net_fip']/a").click()
                    fixture.browser.get_screenshot_as_file('fip.png')
                    time.sleep(3)                    
                    #WebDriverWait(fixture.browser, fixture.delay,fixture.frequency).until(ajax_complete)
                    fixture.browser.find_element_by_xpath("//button[@id='btnCreatefip']").click()
                    #time.sleep(1)
                    WebDriverWait(fixture.browser, fixture.delay,fixture.frequency).until(ajax_complete)
                    time.sleep(1)
                    pool=fixture.browser.find_element_by_xpath("//div[@id='windowCreatefip']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(2)
                    WebDriverWait(fixture.browser, fixture.delay,fixture.frequency).until(ajax_complete)
                    #time.sleep(3)
                    fip=fixture.browser.find_element_by_id("ddFipPool_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML")==fixture.vn_name+':'+fixture.pool_name:
                            fip[i].click()
                    fixture.browser.find_element_by_id('btnCreatefipOK').click()
                    #time.sleep(1)
                    WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                    rows1=fixture.browser.find_elements_by_xpath("//tbody/tr")
                    for element in rows1:
                        if element.find_elements_by_tag_name('td')[3].text==fixture.vn_name+':'+fixture.pool_name:
                            element.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                                'div').find_element_by_tag_name('div').click()
                            element.find_element_by_xpath("//a[@class='tooltip-success']").click()
                            WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                            break
                    pool=fixture.browser.find_element_by_xpath("//div[@id='windowAssociate']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(1)
                    WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                    #time.sleep(3)
                    fip=fixture.browser.find_element_by_id("ddAssociate_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML").split(' ')[1]==vm_id :
                            fip[i].click()
                    fixture.browser.find_element_by_id('btnAssociatePopupOK').click()
                    WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                    time.sleep(1)
                    #self.verify_fip_webui(fixture)
                    break
        except ValueError :
            fixture.logger.info("Error while creating floating ip and associating it to a VM Test.")

    def verify_fip_in_webui(self, fixture):
        self.webui_common.click_configure_networks_in_webui(fixture)
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
        WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
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
        self.webui_common.click_monitor_instances_in_webui(fixture)
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
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
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

    def delete_fip_in_webui(self, fixture):
        self.webui_common.click_configure_fip_in_webui(fixture)
        rows = fixture.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for net in rows:
            if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vm_id) :
                net.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                    'div').find_element_by_tag_name('div').click()
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)
                net.find_element_by_xpath("//a[@class='tooltip-error']").click()      
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)       
                WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnDisassociatePopupOK')).click()        
                WebDriverWait(fixture.browser, fixture.delay, fixture.frequency).until(ajax_complete)     
            rows = fixture.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')       
            for net in rows:
                if (net.find_elements_by_tag_name('td')[3].get_attribute('innerHTML') == fixture.vn_name+':'+fixture.pool_name) :
                    net.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                    WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnDeletefip')).click()
                    WebDriverWait(fixture.browser,fixture.delay).until(lambda a: a.find_element_by_id('btnCnfReleasePopupOK')).click()                   
                   
            self.webui_common.click_configure_networks_in_webui(fixture)
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
