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


class webui_test:
    def __init__(self, connections, inputs):
      self.proj_check_flag=0
      self.inputs= inputs
      self.connections= connections
      self.logger = self.inputs.logger
      self.browser= self.connections.browser
      self.browser_openstack = self.connections.browser_openstack
      self.delay = 90
      self.frequency = 1
      self.logger= inputs.logger
      self.webui_common = webui_common(self)
      self.dash = "-" * 60 
    def create_vn_in_webui(self, fixture):
        try:
            fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
            if not fixture.obj:
                self.logger.info("Creating VN %s using WebUI..."%(fixture.vn_name))
                self.webui_common.click_configure_networks_in_webui()
                self.browser.get_screenshot_as_file('btn_createVN.png')                
                btnCreateVN = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
                        'btnCreateVN')).click()
                self.webui_common.wait_till_ajax_done()
                txtVNName = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('txtVNName'))
                txtVNName.send_keys(fixture.vn_name)
                self.browser.find_element_by_id('txtIPBlock').send_keys(fixture.vn_subnets)
                self.browser.find_element_by_id('btnAddIPBlock').click()
                self.browser.find_element_by_id('btnCreateVNOK').click()
                time.sleep(3)
            else:
                fixture.already_present= True
                self.logger.info('VN %s already exists, skipping creation ' %(fixture.vn_name) )
                self.logger.debug('VN %s exists, already there' %(fixture.vn_name) )
            fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
            fixture.vn_id= fixture.obj['network']['id']
            fixture.vn_fq_name=':'.join(fixture.obj['network']['contrail:fq_name'])
        except Exception as e:
            with fixture.lock:
                self.logger.exception("Got exception as %s while creating %s"%(e,fixture.vn_name))
                sys.exit(-1)
    #end create_vn_in_webui
    
    def verify_vrouter_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying vrouter ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_vrouters_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        error_flag = 0 
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info("vn host name %s exists in op server..checking if exists in webui as well"%(ops_vrouter_name))
            self.webui_common.click_monitor_vrouters_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[0].text == ops_vrouter_name:
                    self.logger.info("vrouter name %s found in webui..going to match advance details now"%(ops_vrouter_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("vrouter name %s did not match in webui...not found in webui"%(ops_vrouter_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and Retrieve vrouter advance details in webui for vrouter-name %s "%(ops_vrouter_name))
                self.webui_common.click_monitor_vrouters_advance_in_webui(match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']}) 
                dom_arry_num = dom_arry_num_new   
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                vrouters_ops_data = self.webui_common.get_details(vrouters_list_ops[n]['href'])
                if vrouters_ops_data.has_key('VrouterStatsAgent'):
                    ops_data = vrouters_ops_data['VrouterStatsAgent']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                if vrouters_ops_data.has_key('VrouterAgent'):
                    ops_data_agent = vrouters_ops_data['VrouterAgent']
                    modified_ops_data_agent = []
                    self.webui_common.extract_keyvalue(ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list :
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode :
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info("ops %s vn data matched in webui" % (ops_vrouter_name))
                    else :
                        self.logger.error("ops %s vn data match failed in webui" % (ops_vrouter_name))
                        error_flag = 1
        if not error_flag :
            return True
        else :
            return False               
                        

    #end verify_vrouter_ops_advance_data_in_webui

    def verify_bgp_routers_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying bgp_routers ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_control_nodes_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        bgp_routers_list_ops = self.webui_common.get_bgp_routers_list_ops()
        error_flag = 0
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_router_name = bgp_routers_list_ops[n]['name']
            self.logger.info(" bgp router %s exists in op server..checking if exists in webui "%(ops_bgp_router_name))
            self.logger.info("Clicking on bgp_routers in monitor page  in Webui...")
            self.webui_common.click_monitor_control_nodes_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[0].text == ops_bgp_router_name:
                    self.logger.info("bgp router name %s found in webui..going to match advance details now"%(ops_bgp_router_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("bgp router name %s not found in webui"%(ops_bgp_router_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and Retrieve bgp advance view details in webui for bgp router-name %s "%(ops_bgp_router_name))
                self.webui_common.click_monitor_control_nodes_advance_in_webui(match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                bgp_routers_ops_data = self.webui_common.get_details(bgp_routers_list_ops[n]['href'])
                if bgp_routers_ops_data.has_key('BgpRouterState'):
                    bgp_router_state_ops_data = bgp_routers_ops_data['BgpRouterState']
                    modified_bgp_router_state_ops_data = []
                    self.webui_common.extract_keyvalue(bgp_router_state_ops_data, modified_bgp_router_state_ops_data)
                    complete_ops_data = modified_bgp_router_state_ops_data
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list :
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode :
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info(" bgp router data matched in webui")
                    else :
                        self.logger.error("bgp router match failed in webui")
                        error_flag = 1
        if not error_flag :
            return True
        else :
            return False

    #end verify_bgp_routers_ops_advance_data_in_webui

    def verify_analytics_nodes_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying analytics_nodes(collectors) ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_analytics_nodes_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        analytics_nodes_list_ops = self.webui_common.get_collectors_list_ops()
        error_flag = 0 
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info(" analytics node %s exists in op server..checking if exists in webui "%(ops_analytics_node_name))
            self.logger.info("Clicking on analytics_nodes in monitor page  in Webui...")
            self.webui_common.click_monitor_analytics_nodes_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[0].text == ops_analytics_node_name:
                    self.logger.info("analytics node name %s found in webui..going to match advance details now"%(ops_analytics_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("analytics node name %s not found in webui"%(ops_analytics_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and Retrieve analytics advance view details in webui for analytics node-name %s "%(ops_analytics_node_name))
                self.webui_common.click_monitor_analytics_nodes_advance_in_webui(match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                analytics_nodes_ops_data = self.webui_common.get_details(analytics_nodes_list_ops[n]['href'])
                modified_query_perf_info_ops_data = []
                modified_module_cpu_state_ops_data = []
                modified_analytics_cpu_state_ops_data = []
                modified_collector_state_ops_data = [] 
                if analytics_nodes_ops_data.has_key('QueryPerfInfo'):
                    query_perf_info_ops_data = analytics_nodes_ops_data['QueryPerfInfo']
                    self.webui_common.extract_keyvalue(query_perf_info_ops_data, modified_query_perf_info_ops_data)
                if analytics_nodes_ops_data.has_key('ModuleCpuState'):
                    module_cpu_state_ops_data = analytics_nodes_ops_data['ModuleCpuState']
                    self.webui_common.extract_keyvalue(module_cpu_state_ops_data, modified_module_cpu_state_ops_data)
                if analytics_nodes_ops_data.has_key('AnalyticsCpuState'):
                    analytics_cpu_state_ops_data = analytics_nodes_ops_data['AnalyticsCpuState']
                    modified_analytics_cpu_state_ops_data = []
                    self.webui_common.extract_keyvalue(analytics_cpu_state_ops_data, modified_analytics_cpu_state_ops_data)
                if analytics_nodes_ops_data.has_key('CollectorState'):
                    collector_state_ops_data = analytics_nodes_ops_data['CollectorState']
                    self.webui_common.extract_keyvalue(collector_state_ops_data, modified_collector_state_ops_data)
                complete_ops_data = modified_query_perf_info_ops_data + modified_module_cpu_state_ops_data +  modified_analytics_cpu_state_ops_data + modified_collector_state_ops_data
                for k in range(len(complete_ops_data)):
                    if type(complete_ops_data[k]['value']) is list :
                        for m in range(len(complete_ops_data[k]['value'])):
                            complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                    elif type(complete_ops_data[k]['value']) is unicode :
                        complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    else:
                        complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                    self.logger.info(" analytics node data matched in webui")
                else :
                    self.logger.error("analytics node match failed in webui")
                    error_flag =1
        if not error_flag :
            return True
        else :
            return False
    #end verify_analytics_nodes_ops_advance_data_in_webui
    
    def verify_vm_ops_basic_data_in_webui(self):
        self.logger.info("Verifying VM basic ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_instances_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vm_list_ops = self.webui_common.get_vm_list_ops()
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            self.webui_common.click_monitor_instances_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            self.logger.info("vm uuid %s exists in op server..checking if exists in webui as well"%(ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[2].text == ops_uuid:
                    self.logger.info("vm uuid %s matched in webui..going to match basic view details now"%(ops_uuid))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    vm_name = rows[i].find_elements_by_tag_name('td')[1].text
                    break
            if not match_flag :
                self.logger.error("uuid exists in opserver but uuid %s not found in webui..."%(ops_uuid))
                self.logger.info(self.dash)
            else:
                self.webui_common.click_monitor_instances_basic_in_webui(match_index)
                self.logger.info("Click and Retrieve basic view details in webui for uuid %s "%(ops_uuid))
                # get vm basic details excluding basic interface details
                dom_arry_basic = self.webui_common.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                elements = self.browser.find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')
                len_elements = len(elements)
                vm_ops_data = self.webui_common.get_details(vm_list_ops[k]['href'])
                complete_ops_data = []
                if vm_ops_data.has_key('UveVirtualMachineAgent'):
                    #get vm interface basic details from opserver
                    ops_data_interface_list = vm_ops_data['UveVirtualMachineAgent']['interface_list']
                    for k in range(len(ops_data_interface_list)):
                        del ops_data_interface_list[k]['l2_active']
                        modified_ops_data_interface_list = []
                        self.webui_common.extract_keyvalue(ops_data_interface_list[k],modified_ops_data_interface_list)
                        complete_ops_data = complete_ops_data + modified_ops_data_interface_list
                        for t in range(len(complete_ops_data)):
                            if type(complete_ops_data[t]['value']) is list :
                                for m in range(len(complete_ops_data[t]['value'])):
                                    complete_ops_data[t]['value'][m] = str(complete_ops_data[t]['value'][m])
                            elif type(complete_ops_data[t]['value']) is unicode :
                                complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
                            else:
                                complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
                # get vm basic interface details excluding basic interface details
                dom_arry_intf = []
                #dom_arry_intf.insert(0,{'key':'uuid','value':ops_uuid})
                dom_arry_intf.insert(0,{'key':'vm_name','value':vm_name})
                # insert non interface elements in list
                for i in range(len_dom_arry_basic):
                    element_key = elements[i].find_elements_by_tag_name('div')[0].text
                    element_value = elements[i].find_elements_by_tag_name('div')[1].text
                    dom_arry_intf.append({'key':element_key,'value':element_value})    
                # insert interface elements in list
                for i in range(len_dom_arry_basic+1,len_elements):
                    elements_key = elements[len_dom_arry_basic].find_elements_by_tag_name('div')
                    elements_value = elements[i].find_elements_by_tag_name('div')
                    for j in range(len(elements_key)):
                        dom_arry_intf.append({'key':elements_key[j].text ,'value':elements_value[j].text})
                if self.webui_common.match_ops_values_with_webui( complete_ops_data, dom_arry_intf):
                    self.logger.info("ops vm basic data matched in webui")
                    return True
                else :
                    self.logger.error("ops vm basic data match failed in webui")
                    return False
    #end verify_vm_ops_basic_data_in_webui

    def verify_vn_ops_basic_data_in_webui(self):
        self.logger.info("Verifying VN basic ops-data in Webui...")
        self.logger.info(self.dash)
        error  = 0
        self.webui_common.click_monitor_networks_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vn_list_ops = self.webui_common.get_vn_list_ops()
        for k in range(len(vn_list_ops)):
            ops_fq_name = vn_list_ops[k]['name']
            self.webui_common.click_monitor_networks_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            self.logger.info("vn fq_name %s exists in op server..checking if exists in webui as well"%(ops_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[1].text == ops_fq_name:
                    self.logger.info("vn fq_name %s matched in webui..going to match basic view details now"%(ops_fq_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[i].find_elements_by_tag_name('td')[1].text
                    break
            if not match_flag :
                self.logger.error("vn fq_name exists in opserver but %s not found in webui..."%(ops_fq_name))
                self.logger.info(self.dash)
            else:
                self.webui_common.click_monitor_networks_basic_in_webui(match_index)
                self.logger.info("Click and Retrieve basic view details in webui for VN fq_name %s "%(ops_fq_name))
                # get vn basic details excluding basic interface details
                dom_arry_basic = self.webui_common.get_vm_basic_view()
                len_dom_arry_basic = len(dom_arry_basic)
                elements = self.browser.find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')
                len_elements = len(elements)
                vn_ops_data = self.webui_common.get_details(vn_list_ops[k]['href'])
                complete_ops_data = []
                ops_data_ingress ={'key':'ingress_flow_count','value':str(0)}
                ops_data_egress =  {'key':'egress_flow_count','value':str(0)}
                ops_data_acl_rules = {'key':'total_acl_rules','value':str(0)}
                vn_name = ops_fq_name.split(':')[2]
                ops_data_vrf = {'key':'vrf_stats_list','value':ops_fq_name+':'+vn_name }
                ops_data_interfaces_count = {'key':'interface_list_count','value':str(0)}               
                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    # creating a list of basic view items retrieved from opserver
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkAgent')
                    if ops_data_basic.get('ingress_flow_count'):
                        ops_data_ingress = {'key':'ingress_flow_count','value':ops_data_basic.get('ingress_flow_count')}
                    if ops_data_basic.get('egress_flow_count'):
                        ops_data_egress =  {'key':'egress_flow_count','value':ops_data_basic.get('egress_flow_count')}
                    if ops_data_basic.get('total_acl_rules'):
                        ops_data_acl_rules = {'key':'total_acl_rules','value':ops_data_basic.get('total_acl_rules')}
                    if ops_data_basic.get('interface_list'):
                        ops_data_interfaces_count = {'key':'interface_list_count','value':len(ops_data_basic.get('interface_list'))}
                    if ops_data_basic.get('vrf_stats_list'):
                        vrf_stats_list = ops_data_basic['vrf_stats_list']
                        vrf_stats_list_new = [ vrf['name'] for vrf in vrf_stats_list ]
                        vrf_list_joined = ','.join(vrf_stats_list_new)
                        ops_data_vrf = {'key':'vrf_stats_list','value':vrf_list_joined}
                        #complete_ops_data.append(ops_data_vrf)
                    if ops_data_basic.get('acl'):
                        ops_data_acl = {'key':'acl','value':ops_data_basic.get('acl')}
                        complete_ops_data.append(ops_data_acl)
                    #ops_data_vrf = {'key':'egress_flow_count','value':ops_data_basic.get('vrf_stats_list')}
                    if ops_data_basic.get('virtualmachine_list'):
                        ops_data_instances = {'key':'virtualmachine_list', 'value': ', '.join(ops_data_basic.get('virtualmachine_list'))}
                        complete_ops_data.append(ops_data_instances)
                complete_ops_data.extend([ops_data_ingress, ops_data_egress, ops_data_acl_rules,ops_data_interfaces_count, ops_data_vrf])
                if ops_fq_name.find('__link_local__') != -1 or ops_fq_name.find('default-virtual-network') != -1  or ops_fq_name.find('ip-fabric') != -1 :
                    for i,item in enumerate(complete_ops_data):
                        if complete_ops_data[i]['key'] == 'vrf_stats_list':
                            del complete_ops_data[i]
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkConfig')
                    if ops_data_basic.get('attached_policies'):
                        #ops_data_policies = {'key':'attached_policies','value':ops_data_basic.get('attached_policies')}
                        ops_data_policies = ops_data_basic.get('attached_policies')
                        if ops_data_policies:
                           pol_name_list = [ pol['vnp_name'] for pol in ops_data_policies ]
                           pol_list_joined = ', '.join(pol_name_list)
                           ops_data_policies = {'key':'attached_policies','value':pol_list_joined}
                           complete_ops_data.extend([ops_data_policies])
                    for t in range(len(complete_ops_data)):
                        if type(complete_ops_data[t]['value']) is list :
                            for m in range(len(complete_ops_data[t]['value'])):
                                complete_ops_data[t]['value'][m] = str(complete_ops_data[t]['value'][m])
                        elif type(complete_ops_data[t]['value']) is unicode :
                            complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
                        else:
                            complete_ops_data[t]['value'] =  str(complete_ops_data[t]['value'])
          
                if self.webui_common.match_ops_values_with_webui( complete_ops_data, dom_arry_basic):
                    self.logger.info("ops vn basic data matched in webui")
                   
                else :
                    self.logger.error("ops vn basic data match failed in webui")
                    error = 1 
        return not error 
    #end verify_vn_ops_basic_data_in_webui

    
    
    def verify_config_nodes_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying config_nodes ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_config_nodes_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        config_nodes_list_ops = self.webui_common.get_config_nodes_list_ops()
        error_flag =0 
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info(" config node host name %s exists in op server..checking if exists in webui as well"%(ops_config_node_name))
            self.webui_common.click_monitor_config_nodes_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[0].text == ops_config_node_name:
                    self.logger.info("config node name %s found in webui..going to match advance view details now"%(ops_config_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("config node name %s did not match in webui...not found in webui"%(ops_config_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and Retrieve config nodes advance view details in webui for config node-name %s "%(ops_config_node_name))
                self.webui_common.click_monitor_config_nodes_advance_in_webui(match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                config_nodes_ops_data = self.webui_common.get_details(config_nodes_list_ops[n]['href'])
                if config_nodes_ops_data.has_key('ModuleCpuState'):
                    ops_data = config_nodes_ops_data['ModuleCpuState']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                    complete_ops_data = modified_ops_data 
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list :
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode :
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info("ops config nodes data matched in webui")
                    else :
                        self.logger.error("ops config nodes match failed in webui")
                        error_flag=1
        if not error_flag :
            return True
        else :
            return False
    #end verify_config_nodes_ops_advance_data_in_webui

    def verify_vn_ops_advance_data_in_webui(self):
        
        self.logger.info("Verifying VN advance ops-data in Webui...")
        self.logger.info(self.dash) 
        self.webui_common.click_monitor_networks_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vn_list_ops = self.webui_common.get_vn_list_ops() 
        error_flag = 0
        for n in range(len(vn_list_ops)):
            ops_fqname = vn_list_ops[n]['name']
            self.logger.info("vn fq name %s exists in op server..checking if exists in webui as well"%(ops_fqname))
            self.webui_common.click_monitor_networks_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[1].text == ops_fqname:
                    self.logger.info("vn fq name %s found in webui..going to match advance view details now"%(ops_fqname))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("vn fqname %s did not match in webui...not found in webui"%(ops_fqname))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and Retrieve advance view details in webui for fqname %s "%(ops_fqname))
                self.webui_common.click_monitor_networks_advance_in_webui(match_index)
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                print dom_arry_str 
                merged_arry = dom_arry + dom_arry_str
                vn_ops_data = self.webui_common.get_details(vn_list_ops[n]['href'])   
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data = vn_ops_data['UveVirtualNetworkConfig']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                 
                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    ops_data_agent = vn_ops_data['UveVirtualNetworkAgent']
                    self.logger.info("VN details for %s  got from  ops server and going to match in webui : \n %s \n " %(vn_list_ops[i]['href'],ops_data_agent))
                    modified_ops_data_agent = []
                    self.webui_common.extract_keyvalue(ops_data_agent, modified_ops_data_agent)
                    complete_ops_data = modified_ops_data + modified_ops_data_agent
                    for k in range(len(complete_ops_data)):
                        if type(complete_ops_data[k]['value']) is list :
                            for m in range(len(complete_ops_data[k]['value'])):
                                complete_ops_data[k]['value'][m] = str(complete_ops_data[k]['value'][m])
                        elif type(complete_ops_data[k]['value']) is unicode :
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                        else:
                            complete_ops_data[k]['value'] =  str(complete_ops_data[k]['value'])
                    if self.webui_common.match_ops_with_webui(complete_ops_data, merged_arry):
                        self.logger.info("ops vn data matched in webui")
                    else :
                        self.logger.error("ops vn data match failed in webui")
                        error_flag =1
        if not error_flag :
            return True
        else :
            return False
    #end verify_vn_ops_advance_data_in_webui
 
    def verify_vm_ops_advance_data_in_webui(self):
        self.logger.info("Verifying VM ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_instances_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vm_list_ops = self.webui_common.get_vm_list_ops()
        error_flag =0
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            self.webui_common.click_monitor_instances_in_webui()
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            self.logger.info("vm uuid %s exists in op server..checking if exists in webui as well"%(ops_uuid)) 
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_tag_name('td')[2].text == ops_uuid:
                    self.logger.info("vm uuid %s matched in webui..going to match advance view details now"%(ops_uuid))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("uuid exists in opserver but uuid %s not found in webui..."%(ops_uuid))
                self.logger.info(self.dash)
            else:    
                self.webui_common.click_monitor_instances_advance_in_webui(match_index)
                self.logger.info("Click and Retrieve advance view details in webui for uuid %s "%(ops_uuid))
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = []
                dom_arry_str = self.webui_common.get_advanced_view_str()
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
                    if self.webui_common.match_ops_with_webui( complete_ops_data, merged_arry):
                        self.logger.info("ops vm data matched in webui")
                    else :
                        self.logger.error("ops vm data match failed in webui")
                        error_flag =1
        if not error_flag :
            return True
        else :
            return False
    #end verify_vm_ops_advance_data_in_webui
                
    def verify_vn_api_data_in_webui(self):
        self.logger.info("Verifying VN  api-data in Webui...")
        self.logger.info(self.dash)
        vn_list = self.webui_common.get_vn_list_api()
        self.logger.info("VN list got from API server : %s  " %(vn_list))
        vn_list = vn_list['virtual-networks'] 
        ln=len(vn_list)-3
        self.webui_common.click_configure_networks_in_webui()
        rows = self.browser.find_element_by_id('gridVN')
        rows = rows.find_element_by_tag_name('tbody')
        rows = rows.find_elements_by_tag_name('tr')
        if ln != len(rows):
            self.logger.error("vn rows in grid mismatch with VNs in api")
        for i in range(ln):
            details  =  self.webui_common.get_details(vn_list[i]['href'])
            self.logger.info("VN details for %s got from API server and going to match in webui : " %(vn_list[i]))
            j=0
            for j in range(len(rows)):
                self.webui_common.click_configure_networks_in_webui()
                self.browser.get_screenshot_as_file('config_net_verify_api.png')
                rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]) :
                    vn_name = details['virtual-network']['fq_name'][2]
                    ip_block=details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix']+'/'+ str(
                        details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix_len'])
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        self.logger.info( "VN %s : ip block matched" %(vn_name))
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    ui_ip_block=rows[j+1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(
                        ' ')[1] == ip_block and ui_ip_block.split(
                            ' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway'] ):
                        self.logger.info( "VN %s basic details in webui network config page matched with api data " %(vn_name))
                    else:
                        self.logger.error( "VN %s basic details in webui network config page not matched with api data" %(vn_name))
                        self.browser.get_screenshot_as_file('verify_vn_api_data_webui_basic_details_failed.png')
                    forwarding_mode=rows[j+1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan=rows[j+1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = { 'l2_l3':'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        self.logger.info( " VN %s : forwarding mode matched "  %(vn_name) )
                    else :
                        self.logger.error( "VN %s : forwarding mode not matched" %(vn_name))
                        self.browser.get_screenshot_as_file('verify_vn_api_data__forwarding_mode_match_failed.png')

                    if details['virtual-network']['virtual_network_properties']['vxlan_network_identifier'] == None :
                        vxlan_api = 'Automatic'
                    else : 
                        vxlan_api = details['virtual-network']['virtual_network_properties']['vxlan_network_identifier']
                    if vxlan_api == vxlan :
                        self.logger.info( " VN %s : vxlan matched "  %(vn_name) )
                    else :
                        self.logger.error( "VN %s : vxlan not matched" %(vn_name))
                        self.browser.get_screenshot_as_file('verify_vn_api_basic_data_vxlan_failed.png')
                    xpath = "//label[contains(text(), 'Floating IP Pools')]"
                    driver = rows[j+1]
               
                    if details['virtual-network'].has_key('floating_ip_pools') : 
                        floating_ip_length_api =  len(details['virtual-network']['floating_ip_pools'])
                        self.logger.info(" %s FIP/s exist in api for network %s " %( floating_ip_length_api,vn_name ))

                        if self.webui_common.check_element_exists_by_xpath(driver, xpath):
                            fip_ui = rows[j+1].find_element_by_xpath("//label[contains(text(), 'Floating IP Pools')]/..").text.split('\n')[1:]
                            for n in range(floating_ip_length_api) :
                                fip_api = details['virtual-network']['floating_ip_pools'][n]['to']
                                if fip_ui[n] == fip_api[3] + ' (' + fip_api[0] + ':' + fip_api[1] + ')' :
                                    self.logger.info(" %s FIP/s matched in webui with api data " %( fip_api ))
                        else: 
                            self.logger.error( "fip element mismatch happened in webui and api ")
                            self.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
                    else :
                        self.logger.info( "Not verifying FIP as it is not found in API ") 
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    break
                
                elif (j == range(len(rows))):
                    self.logger.info( "%s is not matched in webui"%( details['virtual-network']['fq_name'][2]))
    #end verify_vn_api_data_in_webui

    def verify_vm_ops_data_in_webui(self, fixture):
        self.logger.info("Verifying VN %s ops-data in Webui..." %(fixture.vn_name))
        vm_list = self.webui_common.get_vm_list_ops()
        
        self.webui_common.click_monitor_instances_in_webui()
        rows=self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        if len(rows) != len(vm_list) :
            self.logger.error( " VM count in webui and opserver not matched  ")    
        else:
            self.logger.info( " VM count in webui and opserver matched")
        for i in range(len(vm_list)):
            vm_name = vm_list[i]['name']
    #end verify_vm_ops_data_in_webui           
                
    def verify_vn_ops_data_in_webui(self, fixture):
        vn_list = self.webui_common.get_vn_list_ops(fixture)
        self.logger.info("VN details for %s got from ops server and going to match in webui : " %(vn_list))
        self.webui_common.click_configure_networks_in_webui()
        rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
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
                if self.webui_common.check_element_exists_by_xpath(row[j+1],"//label[contains(text(), 'Ingress Flows')]" ):
                            for n in range(floating_ip_length_api) :
                                fip_api = details['virtual-network']['floating_ip_pools'][n]['to']
                                if fip_ui[n] == fip_api[3] + ' (' + fip_api[0] + ':' + fip_api[1] + ')' :
                                    self.logger.info( " fip matched ")
            self.webui_common.click_monitor_networks_in_webui()
            for j in range(len(rows)):
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                   'tbody').find_elements_by_tag_name('tr')
                 
                fq_name=rows[j].find_elements_by_tag_name('a')[1].text
                if(fq_name==vn_list[i]['name']):
                    self.logger.info( " %s VN verified in monitor page " %(fq_name))
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    expanded_row = rows[j+1].find_element_by_class_name('inline row-fluid position-relative pull-right margin-0-5')
                    expanded_row.find_element_by_class_name('icon-cog icon-only bigger-110').click()
                    expanded_row.find_elements_by_tag_name('a')[1].click()
                    basicdetails_ui_data=rows[j+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]").find_elements_by_class_name("row-fluid")
                    ingress_ui = basicdetails_ui_data[0].text.split('\n')[1]
                    egress_ui = basicdetails_ui_data[1].text.split('\n')[1]
                    acl_ui = basicdetails_ui_data[2].text.split('\n')[1]
                    intf_ui = basicdetails_ui_data[3].text.split('\n')[1]     
                    vrf_ui = basicdetails_ui_data[4].text.split('\n')[1]
                    break
                else:
                    self.logger.error( " %s VN not found in monitor page " %(fq_name))
            details  =  self.webui_common.get_vn_details_api(vn_list[i]['href'])
            
            j=0
            for j in range(len(rows)):
                self.webui_common.click_monitor_networks_in_webui()
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]) :
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        self.logger.info( "ip blocks verified ") 
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    ui_ip_block=rows[j+1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(' ')[1] == ip_block and ui_ip_block.split(' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway'] ):
                        self.logger.info( "ip block and details matched in webui advance view details ")
                    else:
                        self.logger.error( "not matched")
                    forwarding_mode=rows[j+1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan=rows[j+1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = { 'l2_l3':'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        self.logger.info( " forwarding mode matched ")
                    else :
                        self.logger.error( "forwarding mode not matched ")

                    if details['virtual-network']['virtual_network_properties']['vxlan_network_identifier'] == None :
                        vxlan_api = 'Automatic'
                    else :
                        vxlan_api = details['virtual-network']['virtual_network_properties']['vxlan_network_identifier']
                    if vxlan_api == vxlan :
                        self.logger.info( " vxlan matched ")
                    else :
                        self.logger.info( " vxlan not matched ")
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    break

                elif (j == range(len(rows))):
                    self.logger.info( "vn name %s : %s is not matched in webui  " %(fixture.vn_name,details['virtual-network']['fq_name'][2]))
    #end verify_vn_ops_data_in_webui
 
    def verify_vn_in_webui(self, fixture):
        self.browser.get_screenshot_as_file('vm_verify.png')
        self.webui_common.click_configure_networks_in_webui()
        time.sleep(2)
        rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vn_flag=0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name and rows[i].find_elements_by_tag_name(
                'td')[4].text==fixture.vn_subnets[0]) :
                vn_flag=1
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                time.sleep(2)
                rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                ip_blocks=rows[i+1].find_element_by_class_name('span11').text.split('\n')[1]
                if (ip_blocks.split(' ')[0]==':'.join(fixture.ipam_fq_name) and ip_blocks.split(' ')[1]==fixture.vn_subnets[0]):
                    self.logger.info( "vn name %s and ip block %s verified in configure page " %(fixture.vn_name,fixture.vn_subnets))
                else:
                    self.logger.error( "ip block details failed to verify in configure page %s " %(fixture.vn_subnets))
                    self.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
                    vn_flag=0
                break
        self.webui_common.click_monitor_networks_in_webui() 
        time.sleep(3)
        rows=self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        vn_entry_flag=0
        for i in range(len(rows)):
            fq_name=rows[i].find_elements_by_tag_name('a')[1].text
            if(fq_name==fixture.ipam_fq_name[0]+":"+fixture.project_name+":"+fixture.vn_name):
                self.logger.info( " %s VN verified in monitor page " %(fq_name))
                vn_entry_flag=1
                break
        if not vn_entry_flag:
            self.logger.error( "VN %s Verification failed in monitor page" %(fixture.vn_name))
            self.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
        if vn_entry_flag:
            self.logger.info( " VN %s and subnet verified in webui config and monitor pages" %(fixture.vn_name))
        if self.webui_common.verify_uuid_table(fixture.vn_id):
            self.logger.info( "VN %s UUID verified in webui table " %(fixture.vn_name))
        else:
            self.logger.error( "VN %s UUID Verification failed in webui table " %(fixture.vn_name))
            self.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
        fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
        fq_type='virtual_network'
        full_fq_name=fixture.vn_fq_name+':'+fixture.vn_id
        if self.webui_common.verify_fq_name_table(full_fq_name, fq_type):
            self.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
        else:
            self.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
            self.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        return True
    #end verify_vn_in_webui

    def vn_delete_in_webui(self, fixture):
        self.browser.get_screenshot_as_file('vm_delete.png')
        self.webui_common.click_configure_networks_in_webui()
        
        rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        for net in rows :
            if (net.find_elements_by_tag_name('td')[2].text==fixture.vn_name):
                net.find_elements_by_tag_name('td')[1].find_element_by_tag_name('input').click()
                break
        self.browser.find_element_by_id('btnDeleteVN').click()
        self.webui_common.wait_till_ajax_done() 
        self.browser.find_element_by_id('btnCnfRemoveMainPopupOK').click() 
        self.logger.info("%s is deleted successfully using WebUI"%(fixture.vn_name))
    #end vn_delete_in_webui

    def create_vm_in_openstack(self, fixture):
        try:
            if not self.proj_check_flag:
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
                time.sleep(1)
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h4')).click()
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id('tenant_list')).click()
                current_project=WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h3')).text
                if not current_project==fixture.project_name:
                    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h3')).click()
                    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text(fixture.project_name)).click()
                    WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)                    
                    self.proj_check_flag = 1
            
	    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)
            instance = WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Instances')).click()
            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)
            fixture.nova_fixture.get_image(image_name=fixture.image_name)
            time.sleep(2)
            launch_instance = WebDriverWait(self.browser_openstack, self.delay).until(
                lambda a: a.find_element_by_link_text('Launch Instance')).click()
            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)
            self.logger.debug('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            self.logger.info('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='source_type']/option[contains(text(), 'image') or contains(text(),'Image')]").click()
            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete) 
            self.browser_openstack.find_element_by_xpath( "//select[@name='image_id']/option[contains(text(), '" + fixture.image_name + "')]").click()
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id(
                'id_name')).send_keys(fixture.vm_name)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='flavor']/option[text()='m1.medium']").click()
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            networks=WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id
                ('available_network')).find_elements_by_tag_name('li')
            for net in networks:
                vn_match=net.text.split('(')[0]
                if (vn_match==fixture.vn_name) :
                    net.find_element_by_class_name('btn').click()
                    break
            WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_xpath(
                "//input[@value='Launch']")).click()
            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)
            self.logger.debug('VM %s launched using openstack' %(fixture.vm_name) )
            self.logger.info('waiting for VM %s to come into active state' %(fixture.vm_name) )
            time.sleep(10)
            rows_os = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                        'tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows_os)):
                rows_os = self.browser_openstack.find_element_by_tag_name('form')
                rows_os = WebDriverWait(rows_os, self.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
                rows_os = WebDriverWait(rows_os, self.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
                
                if(rows_os[i].find_elements_by_tag_name('td')[1].text==fixture.vm_name):
                    counter=0
                    vm_active=False
                    while not vm_active :
                        vm_active_status1 = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                            'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name(
                                'td')[6].text  
                        vm_active_status2 = self.browser_openstack.find_element_by_tag_name('form').find_element_by_tag_name(
                                    'tbody').find_elements_by_tag_name('tr')[i].find_elements_by_tag_name('td')[5].text

                        if(vm_active_status1 =='Active' or vm_active_status2 =='Active'):
                            self.logger.info("%s status is Active now in openstack" %(fixture.vm_name))
                            vm_active=True
                            time.sleep(5)
                        elif(vm_active_status1 == 'Error' or vm_active_status2 =='Error'):
                            self.logger.error("%s state went into Error state in openstack" %(fixture.vm_name))
                            self.browser_openstack.get_screenshot_as_file('verify_vm_state_openstack_'+'fixture.vm_name'+'.png')
                            return "Error"
                        else:
                            self.logger.info("%s state is not yet Active in openstack, waiting for more time..." %(fixture.vm_name))
                            counter=counter+1
                            time.sleep(3)
                            self.browser_openstack.find_element_by_link_text('Instances').click()
                            WebDriverWait(self.browser_openstack, self.delay).until(ajax_complete)
                            time.sleep(3)
                            if(counter>=100):
                                fixuture.logger.error("VM %s failed to come into active state" %(fixture.vm_name) )
                                self.browser_openstack.get_screenshot_as_file('verify_vm_not_active_openstack_'+'fixture.vm_name'+'.png')
                                break
            fixture.vm_obj = fixture.nova_fixture.get_vm_if_present(fixture.vm_name, fixture.project_fixture.uuid)
            fixture.vm_objs = fixture.nova_fixture.get_vm_list(name_pattern=fixture.vm_name,project_id=fixture.project_fixture.uuid)      
        except ValueError :
            self.logger.error('Error while creating VM %s with image name %s failed in openstack'
                %(fixture.vm_name,fixture.image_name))
            self.browser_openstack.get_screenshot_as_file('verify_vm_error_openstack_'+'fixture.vm_name'+'.png')
    #end create_vm_in_openstack

    def vm_delete_in_openstack(self, fixture):
        rows = self.browser_openstack.find_element_by_id('instances').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        for instance in rows:
            if fixture.vm_name==instance.find_element_by_tag_name('a').text:
                instance.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                break
        ln = len(rows)
        launch_instance = WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id('instances__action_terminate')).click()
        WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Terminate Instances')).click()
        time.sleep(5)
        self.logger.info("VM %s deleted successfully using openstack"%(fixture.vm_name))
    #end vm_delete_in_openstack
    
    def verify_vm_in_webui(self,fixture):
        try :
            self.webui_common.click_monitor_instances_in_webui()        
            rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                'tbody').find_elements_by_tag_name('tr')
            ln = len(rows)
            vm_flag=0
            for i in range(len(rows)):
                rows_count = len(rows)
                vm_name=rows[i].find_elements_by_tag_name('td')[1].find_element_by_tag_name('div').text 
                vm_uuid=rows[i].find_elements_by_tag_name('td')[2].text
                vm_vn=rows[i].find_elements_by_tag_name('td')[3].text.split(' ')[0]
                if(vm_name == fixture.vm_name and fixture.vm_obj.id==vm_uuid and fixture.vn_name==vm_vn) :
                    self.logger.info("VM %s vm found now will verify basic details"%(fixture.vm_name))
                    retry_count = 0
                    while True :
                        self.logger.debug("count is" + str(retry_count))
                        if retry_count > 20 : 
                            self.logger.error('vm details failed to load')
                            break 
                        self.browser.find_element_by_xpath("//*[@id='mon_net_instances']").find_element_by_tag_name('a').click()
                        time.sleep(1)
                        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                        rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                        try :
                            retry_count = retry_count + 1 
                            self.webui_common.wait_till_ajax_done()
                            break
                        except WebDriverException:
                            pass

                    rows=WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_class_name(
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
            self.browser.get_screenshot_as_file('vm_create_check.png')
            self.logger.info("Vm name,vm uuid,vm ip and vm status,vm network verification in WebUI for VM %s passed" %(fixture.vm_name) )
            mon_net_networks = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
                'mon_net_networks')).find_element_by_link_text('Networks').click()
            time.sleep(2)
            self.webui_common.wait_till_ajax_done()
            rows=self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for i in range(len(rows)):
                if(rows[i].find_elements_by_tag_name('a')[1].text==fixture.vn_fq_name.split(':')[0]+":"+fixture.project_name+":"+fixture.vn_name):
                    rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    self.webui_common.wait_till_ajax_done()
                    rows=self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
                    vm_ids=rows[i+1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_tag_name('div')[15].text
                    if fixture.vm_id in vm_ids:
                        self.logger.info( "vm_id matched in webui monitor network basic details page %s" %(fixture.vn_name))
                    else :
                        self.logger.error("vm_id not matched in webui monitor network basic details page %s" %(fixture.vm_name))
                        self.browser.get_screenshot_as_file('monitor_page_vm_id_not_match'+fixture.vm_name+fixture.vm_id+'.png')
                    break
            if self.webui_common.verify_uuid_table(fixture.vm_id):
                self.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            else:
                self.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            fq_type='virtual_machine'
            full_fq_name=fixture.vm_id+":"+fixture.vm_id
            if self.webui_common.verify_fq_name_table(full_fq_name,fq_type):
               self.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            else:
               self.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            self.logger.info("VM verification in WebUI %s passed" %(fixture.vm_name) ) 
            return True
        except ValueError :
                    self.logger.error("vm %s test error " %(fixture.vm_name))
                    self.browser.get_screenshot_as_file('verify_vm_test_openstack_error'+'fixture.vm_name'+'.png')
    #end verify_vm_in_webui

    def create_floatingip_pool_webui(self, fixture, pool_name, vn_name):
        try :
            self.webui_common.click_configure_networks_in_webui()
            rows = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('gridVN'))
            rows = WebDriverWait(rows, self.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
            rows =  WebDriverWait(rows, self.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    net.find_element_by_class_name('dropdown-toggle').click()
                    self.webui_common.wait_till_ajax_done()
                    net.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
                    ip_text =  net.find_element_by_xpath("//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath('..').find_element_by_tag_name('i').click()
                    route = self.browser.find_element_by_xpath("//div[@title='Add Floating IP Pool below']")
                    route.find_element_by_class_name('icon-plus').click()
                    self.webui_common.wait_till_ajax_done()
                    self.browser.find_element_by_xpath("//input[@placeholder='Pool Name']").send_keys(fixture.pool_name)
                    pool_con = self.browser.find_element_by_id('fipTuples')
                    pool_con.find_element_by_class_name('k-multiselect-wrap').click()
                    self.webui_common.wait_till_ajax_done()
                    ip_ul= self.browser.find_element_by_xpath("//ul[@aria-hidden = 'false']")
                    ip_ul.find_elements_by_tag_name('li')[0].click()
                    self.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    self.webui_common.wait_till_ajax_done()
                    time.sleep(2)
                    self.logger.info( "fip pool %s created using WebUI" %(fixture.pool_name))		   

                    break
        except ValueError :
                    self.logger.error("fip %s Error while creating floating ip pool " %(fixture.pool_name))
    #end create_floatingip_pool_webui

    def create_and_assoc_fip_webui(self, fixture, fip_pool_vn_id, vm_id , vm_name,project = None):
        try :
            fixture.vm_name=vm_name
            fixture.vm_id=vm_id
            self.webui_common.click_configure_networks_in_webui()
            rows = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('gridVN'))
            rows = WebDriverWait(rows, self.delay).until(lambda a: a.find_element_by_tag_name('tbody'))
            rows =  WebDriverWait(rows, self.delay).until(lambda a: a.find_elements_by_tag_name('tr'))
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    self.browser.find_element_by_xpath("//*[@id='config_net_fip']/a").click()
                    self.browser.get_screenshot_as_file('fip.png')
                    time.sleep(3)                    
                    self.browser.find_element_by_xpath("//button[@id='btnCreatefip']").click()
                    WebDriverWait(self.browser, self.delay,self.frequency).until(ajax_complete)
                    time.sleep(1)
                    pool=self.browser.find_element_by_xpath("//div[@id='windowCreatefip']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(2)
                    self.webui_common.wait_till_ajax_done()
                    fip=self.browser.find_element_by_id("ddFipPool_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML")==fixture.vn_name+':'+fixture.pool_name:
                            fip[i].click()
                    self.browser.find_element_by_id('btnCreatefipOK').click()
                    self.webui_common.wait_till_ajax_done()
                    rows1=self.browser.find_elements_by_xpath("//tbody/tr")
                    for element in rows1:
                        if element.find_elements_by_tag_name('td')[3].text==fixture.vn_name+':'+fixture.pool_name:
                            element.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                                'div').find_element_by_tag_name('div').click()
                            element.find_element_by_xpath("//a[@class='tooltip-success']").click()
                            self.webui_common.wait_till_ajax_done()
                            break
                    pool=self.browser.find_element_by_xpath("//div[@id='windowAssociate']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(1)
                    self.webui_common.wait_till_ajax_done()
                    fip=self.browser.find_element_by_id("ddAssociate_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML").split(' ')[1]==vm_id :
                            fip[i].click()
                    self.browser.find_element_by_id('btnAssociatePopupOK').click()
                    self.webui_common.wait_till_ajax_done()
                    time.sleep(1)
                    break
        except ValueError :
            self.logger.info("Error while creating floating ip and associating it to a VM Test.")
    #end create_and_assoc_fip_webui

    def verify_fip_in_webui(self, fixture):
        self.webui_common.click_configure_networks_in_webui()
        rows = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
            'gridVN')).find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            vn_name=rows[i].find_elements_by_tag_name('td')[2].text
            if vn_name==fixture.vn_name:
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fip_check=rows[i+1].find_elements_by_xpath("//td/div/div/div")[1].text
                if fip_check.split('\n')[1].split(' ')[0]==fixture.pool_name:
                    self.logger.info( "fip pool %s verified in WebUI configure network page" %(fixture.pool_name))
                    break
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_xpath("//*[@id='config_net_fip']/a")).click()
        self.webui_common.wait_till_ajax_done()
        rows = self.browser.find_element_by_xpath("//div[@id='gridfip']/table/tbody").find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            fip=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[1]
            vn=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[0]
            fip_ip=rows[i].find_elements_by_tag_name('td')[1].text
            if rows[i].find_elements_by_tag_name('td')[2].text==fixture.vm_id :
                if vn==fixture.vn_name and fip==fixture.pool_name:
                    self.logger.info("FIP  is found attached with vm %s "%(fixture.vm_name))  
                    self.logger.info("VM %s is found associated with FIP %s "%(fixture.vm_name,fip))
                else :
                    self.logger.info("Association of %s VM failed with FIP %s "%(fixture.vm_name,fip))
                    break
        self.webui_common.click_monitor_instances_in_webui()
        rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
            'tbody').find_elements_by_tag_name('tr')
        ln = len(rows)
        vm_flag=0
        for i in range(len(rows)):
            vm_name=rows[i].find_elements_by_tag_name('td')[1].find_element_by_tag_name('div').text
            vm_uuid=rows[i].find_elements_by_tag_name('td')[2].text
            vm_vn=rows[i].find_elements_by_tag_name('td')[3].text.split(' ')[0]
            if(vm_name == fixture.vm_name and fixture.vm_id==vm_uuid and vm_vn==fixture.vn_name) :
                rows[i].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                self.webui_common.wait_till_ajax_done()
                rows = self.browser.find_element_by_class_name('k-grid-content').find_element_by_tag_name(
                    'tbody').find_elements_by_tag_name('tr')
                fip_check_vm=rows[i+1].find_element_by_xpath("//*[contains(@id, 'basicDetails')]"
	            ).find_elements_by_tag_name('div')[0].find_elements_by_tag_name('div')[1].text
                if fip_check_vm.split(' ')[0]==fip_ip and fip_check_vm.split(
                    ' ')[1]=='\('+'default-domain'+':'+fixture.project_name+':'+fixture.vn_name+'\)' :
                    self.logger.info("FIP verified in monitor instance page for vm %s "%(fixture.vm_name))
                else :
                   self.logger.info("FIP failed to verify in monitor instance page for vm %s"%(fixture.vm_name))		  	
                   break
    #end verify_fip_in_webui

    def delete_fip_in_webui(self, fixture):
        self.webui_common.click_configure_fip_in_webui()
        rows = self.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        for net in rows:
            if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vm_id) :
                net.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                    'div').find_element_by_tag_name('div').click()
                self.webui_common.wait_till_ajax_done()
                net.find_element_by_xpath("//a[@class='tooltip-error']").click()      
                self.webui_common.wait_till_ajax_done()       
                WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnDisassociatePopupOK')).click()        
                self.webui_common.wait_till_ajax_done()
                self.webui_common.wait_till_ajax_done()     
            rows = self.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')       
            for net in rows:
                if (net.find_elements_by_tag_name('td')[3].get_attribute('innerHTML') == fixture.vn_name+':'+fixture.pool_name) :
                    net.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                    WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnDeletefip')).click()
                    WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnCnfReleasePopupOK')).click()                   
                   
            self.webui_common.click_configure_networks_in_webui()
            rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            for net in rows:
                if (net.find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == fixture.vn_name) :
                    net.find_element_by_class_name('dropdown-toggle').click()
                    net.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
                    ip_text =  net.find_element_by_xpath("//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath('..').find_element_by_tag_name('i').click()
                    pool_con = self.browser.find_element_by_id('fipTuples')
                    fip=pool_con.find_elements_by_xpath("//*[contains(@id, 'rule')]")
                    for pool in fip:
                        if(pool.find_element_by_tag_name('input').get_attribute('value')==fixture.pool_name):
                            pool.find_element_by_class_name('icon-minus').click()
                    self.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    break    
    #end delete_fip_in_webui  
