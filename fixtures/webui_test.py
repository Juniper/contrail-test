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
      self.delay = 10
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
                self.browser.get_screenshot_as_file('createVN'+self.webui_common.date_time_string()+'.png')                
                btnCreateVN = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id(
                        'btnCreateVN')).click()
                self.webui_common.wait_till_ajax_done(self.browser)
            
                txtVNName = WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_id('txtVNName'))
                txtVNName.send_keys(fixture.vn_name)
                if type(fixture.vn_subnets) is list :
                    for subnet in fixture.vn_subnets:
                        self.browser.find_element_by_id('btnCommonAddIpam').click()
                        self.browser.find_element_by_xpath("//input[@placeholder = 'IP Block'] ").send_keys(subnet)
                else:
                    self.browser.find_element_by_id('btnCommonAddIpam').click()
                    self.browser.find_element_by_xpath("//input[@placeholder = 'IP Block'] ").send_keys(fixture.vn_subnets)
                self.browser.find_element_by_id('btnCreateVNOK').click()
                time.sleep(3)
                try:
                    if self.browser.find_element_by_id('infoWindow') :
                        error_header = self.browser.find_element_by_id('modal-header-title').text
                        error_text = self.browser.find_element_by_id('short-msg').text
                        self.logger.error('error occured : %s ' %(error_header))
                        self.logger.error('error occured while creating vn %s msg is %s ' %(fixture.vn_name, error_text))
                        self.logger.info('Capturing screenshot of error msg .')
                        self.browser.get_screenshot_as_file('create_vn_error' + fixture.vn_name + self.webui_common.date_time_string()+'.png')
                        self.logger.info('Captured screenshot create_vn_error' + fixture.vn_name + self.webui_common.date_time_string()+'.png')
                        self.browser.find_element_by_id('infoWindowbtn0').click()
                        self.logger.info(' VN %s creation failed using webui .'% (fixture.vn_name))
                except NoSuchElementException:
                    self.logger.info('created VN %s using webui .'% (fixture.vn_name))
                    pass
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

    def verify_analytics_nodes_ops_basic_data_in_webui(self) :
        self.logger.info("Verifying analytics_node basic ops-data in Webui...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_analytics_nodes_in_webui()
        rows = self.webui_common.get_rows()
        analytics_nodes_list_ops = self.webui_common.get_collectors_list_ops()
        error_flag = 0
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info("vn host name %s exists in op server..checking if exists in webui as well"%(
                ops_analytics_node_name))
            self.webui_common.click_monitor_analytics_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info("analytics_node name %s found in webui..going to match basic details now"%(
                        ops_analytics_node_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("analytics_node name %s did not match in webui...not found in webui"%(
                    ops_analytics_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve analytics_node basic view details in webui for  \
                    analytics_node-name %s "%(ops_analytics_node_name))
                self.webui_common.click_monitor_analytics_nodes_basic_in_webui(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name('p').get_attribute(
                    'innerHTML').split('/span>')[1].replace('\n','').strip()
                for i, item in enumerate(dom_basic_view):
                    if  item.get('key') == 'Overall Node Status' :
                        dom_basic_view[i]['value'] = node_status
                # filter analytics_node basic view details from opserver data
                analytics_nodes_ops_data = self.webui_common.get_details(analytics_nodes_list_ops[n]['href'])
                ops_basic_data = []
                host_name = analytics_nodes_list_ops[n]['name']
                ip_address = analytics_nodes_ops_data.get('CollectorState').get('self_ip_list')
                ip_address = ', '.join(ip_address)
                generators_count = str(len(analytics_nodes_ops_data.get('CollectorState').get('generator_infos')))
                version = json.loads(analytics_nodes_ops_data.get('CollectorState').get('build_info')).get(
                    'build-info')[0].get('build-id')
                version = self.webui_common.get_version_string(version)
                module_cpu_info_len = len(analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                for i in range(module_cpu_info_len):
                    if analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i][
                    'module_id'] == 'Collector':
                        cpu_mem_info_dict = analytics_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i]
                        break
                cpu = self.webui_common.get_cpu_string(cpu_mem_info_dict)
                memory = self.webui_common.get_memory_string(cpu_mem_info_dict)
                modified_ops_data = []
                process_state_list = analytics_nodes_ops_data.get('ModuleCpuState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = ['contrail-config-nodemgr','contrail-analytics-nodemgr','contrail-control-nodemgr','contrail-vrouter-nodemgr','openstack-nova-compute','contrail-svc-monitor','contrail-discovery:0','contrail-zookeeper', 'contrail-schema'] 
                for i,item in enumerate(process_state_list):
                    if item['process_name'] == 'redis-query':
                        redis_query_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)    
                    if item['process_name'] == 'contrail-qe':
                        contrail_qe_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-analytics-nodemgr':
                        contrail_analytics_nodemgr_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'redis-uve':
                        redis_uve_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-opserver':
                        contrail_opserver_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-collector':
                        contrail_collector_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = { k:v for k,v in process_down_stop_time_dict.items() if k not in exclude_process_list }
                if not reduced_process_keys_dict :
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = min(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values()))) 
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(process_down_count) +' Process down'

                modified_ops_data.extend([ {'key': 'Hostname','value':host_name}, {'key': 'Generators','value':generators_count},{'key': 'IP Address','value':ip_address}, {'key': 'CPU','value':cpu}, {'key': 'Memory','value':memory}, {'key': 'Version','value':version}, {'key': 'Collector','value':contrail_collector_string}, {'key': 'Query Engine','value':contrail_qe_string}, {'key': 'OpServer','value':contrail_opserver_string},{'key': 'Redis Query','value':redis_query_string}, {'key': 'Redis UVE','value':redis_uve_string},{'key': 'Overall Node Status','value':overall_node_status_string}])
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info("ops %s uves analytics_nodes basic view details data matched in webui" % (ops_analytics_node_name))
                else :
                    self.logger.error("ops %s uves analytics_nodes basic view details data match failed in webui" % (ops_analytics_node_name))
                    error_flag = 1
        if not error_flag :
            return True
        else :
            return False
    
    def verify_config_nodes_ops_basic_data_in_webui(self) :
        self.logger.info("Verifying config_node basic ops-data in Webui monitor->infra->Config Nodes->details(basic view)...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_config_nodes_in_webui()
        rows = self.webui_common.get_rows()
        config_nodes_list_ops = self.webui_common.get_config_nodes_list_ops()
        error_flag = 0
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info("vn host name %s exists in op server..checking if exists in webui as well"%(
                ops_config_node_name))
            self.webui_common.click_monitor_config_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_config_node_name:
                    self.logger.info("config_node name %s found in webui..going to match basic details now"%(
                        ops_config_node_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("config_node name %s did not match in webui...not found in webui"%(
                    ops_config_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve config_node basic view details in webui for  \
                    config_node-name %s "%(ops_config_node_name))
                # filter config_node basic view details from opserver data
                config_nodes_ops_data = self.webui_common.get_details(config_nodes_list_ops[n]['href'])
                self.webui_common.click_monitor_config_nodes_basic_in_webui(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                ops_basic_data = []
                host_name = config_nodes_list_ops[n]['name']
                ip_address = config_nodes_ops_data.get('ModuleCpuState').get('config_node_ip')
                if not ip_address:
                    ip_address = '--'
                else:
                    ip_address = ', '.join(ip_address)
                process_state_list = config_nodes_ops_data.get('ModuleCpuState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = ['contrail-config-nodemgr','contrail-analytics-nodemgr','contrail-control-nodemgr','contrail-vrouter-nodemgr','openstack-nova-compute','contrail-svc-monitor','contrail-discovery:0','contrail-zookeeper', 'contrail-schema'] 
                for i,item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-api:0':
                        api_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)    
                    if item['process_name'] == 'ifmap':
                        ifmap_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-discovery:0':
                        discovery_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-schema':
                        schema_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-svc-monitor':
                        monitor_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = { k:v for k,v in process_down_stop_time_dict.items() if k not in exclude_process_list }
                if not reduced_process_keys_dict :
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values()))) 
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(process_down_count) +' Process down'
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name('p').get_attribute('innerHTML').split('/span>')[1].replace('\n','').strip()
                for i, item in enumerate(dom_basic_view):
                    if  item.get('key') == 'Overall Node Status' :
                        dom_basic_view[i]['value'] = node_status    

                version = config_nodes_ops_data.get('ModuleCpuState').get('build_info')
                if not version : 
                    version = '--'
                else:
                    version = json.loads(config_nodes_ops_data.get('ModuleCpuState').get('build_info')).get(
                    'build-info')[0].get('build-id')
                    version = self.webui_common.get_version_string(version)
                module_cpu_info_len = len(config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info'))
                cpu_mem_info_dict = {}
                for i in range(module_cpu_info_len):
                    if config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i][
                    'module_id'] == 'ApiServer':
                        cpu_mem_info_dict = config_nodes_ops_data.get('ModuleCpuState').get('module_cpu_info')[i]
                        break
                if not cpu_mem_info_dict:
                    cpu = '--'
                    memory = '--'
                else:
                    cpu = self.webui_common.get_cpu_string(cpu_mem_info_dict)
                    memory = self.webui_common.get_memory_string(cpu_mem_info_dict)
                modified_ops_data = []
                generator_list = self.webui_common.get_generators_list_ops() 
                for element in generator_list:
                    if element['name'] == ops_config_node_name + ':Config:Contrail-Config-Nodemgr:0':
                        analytics_data = element['href']
                        generators_vrouters_data = self.webui_common.get_details(element['href'])
                        analytics_data = generators_vrouters_data.get('ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data['primary'].split(':')[0] + ' (Up)'
                            
                 
                modified_ops_data.extend([ {'key': 'Hostname','value':host_name}, {'key': 'IP Address','value':ip_address}, {'key': 'CPU','value':cpu}, {'key': 'Memory','value':memory}, {'key': 'Version','value':version}, {'key': 'API Server','value':api_string}, {'key': 'Discovery','value':discovery_string}, {'key': 'Service Monitor','value':monitor_string}, {'key': 'Ifmap','value':ifmap_string}, {'key': 'Schema Transformer','value':schema_string}, {'key': 'Overall Node Status','value':overall_node_status_string}])
                self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info("ops %s uves config_nodes basic view details data matched in webui" % (ops_config_node_name))
                else :
                    self.logger.error("ops %s uves config_nodes basic view details data match failed in webui" % (ops_config_node_name))
                    error_flag = 1
        if not error_flag :
            return True
        else :
            return False

    def verify_vrouter_ops_basic_data_in_webui(self) :
        self.logger.info("Verifying vrouter basic ops-data in Webui monitor->infra->Virtual routers->details(basic view)...")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_vrouters_in_webui()
        rows = self.webui_common.get_rows()
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        error_flag = 0
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info("vn host name %s exists in op server..checking if exists in webui as well"%(ops_vrouter_name))
            self.webui_common.click_monitor_vrouters_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info("vrouter name %s found in webui..going to match basic details now"%(ops_vrouter_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("vrouter name %s did not match in webui...not found in webui"%(ops_vrouter_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve vrouter basic view details in webui for vrouter-name %s "%(ops_vrouter_name))
                self.webui_common.click_monitor_vrouters_basic_in_webui(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name('p').get_attribute(
                    'innerHTML').split('/span>')[1].replace('\n','').strip()
                for i, item in enumerate(dom_basic_view):
                    if  item.get('key') == 'Overall Node Status' :
                        dom_basic_view[i]['value'] = node_status
                #special handling for control nodes 
                control_nodes = self.browser.find_element_by_class_name('table-cell').text
                for i, item in enumerate(dom_basic_view):
                    if  item.get('key') == 'Control Nodes' :
                        dom_basic_view[i]['value'] = control_nodes
                # filter vrouter basic view details from opserver data
                vrouters_ops_data = self.webui_common.get_details(vrouters_list_ops[n]['href'])
                ops_basic_data = []
                host_name = vrouters_list_ops[n]['name']
                ip_address = vrouters_ops_data.get('VrouterAgent').get('self_ip_list')[0]
                version = json.loads(vrouters_ops_data.get('VrouterAgent').get('build_info')).get('build-info')[0].get('build-id')
                version = version.split('-')
                version = version[0] + ' (Build ' + version[1] + ')'
                xmpp_messages = vrouters_ops_data.get('VrouterStatsAgent').get('xmpp_stats_list')
                for i, item in enumerate(xmpp_messages):
                    if item['ip'] == ip_address :
                        xmpp_in_msgs = item['in_msgs']
                        xmpp_out_msgs = item['out_msgs'] 
                        xmpp_msgs_string = str(xmpp_in_msgs) + ' In ' + str(xmpp_out_msgs) + ' Out'
                        break
                total_flows = vrouters_ops_data.get('VrouterStatsAgent').get('total_flows')
                active_flows = vrouters_ops_data.get('VrouterStatsAgent').get('active_flows')
                flow_count_string = str(active_flows)+ ' Active, ' + str(total_flows) + ' Total'
                if vrouters_ops_data.get('VrouterAgent').get('connected_networks') :
                    networks = str(len(vrouters_ops_data.get('VrouterAgent').get('connected_networks')))
                else:
                    networks = '--'
                interfaces = str(vrouters_ops_data.get('VrouterAgent').get('total_interface_count'))
                if vrouters_ops_data.get('VrouterAgent').get('virtual_machine_list'):
                    instances = str(len(vrouters_ops_data.get('VrouterAgent').get('virtual_machine_list')))
                else:
                    instances = '--'
                cpu = vrouters_ops_data.get('VrouterStatsAgent').get('cpu_info').get('cpu_share')
                cpu = str(round(cpu, 2))+ ' %'
                memory = vrouters_ops_data.get('VrouterStatsAgent').get('cpu_info').get('meminfo').get('virt')
                memory = memory/1024.0
                if memory < 1024 :
                    memory = str(round(memory, 2)) + ' MB'
                else:
                    memory = str(round(memory/1024), 2) + ' GB'  
                last_log = vrouters_ops_data.get('VrouterAgent').get('total_interface_count')
                modified_ops_data = []
                process_state_list = vrouters_ops_data.get('VrouterStatsAgent').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = ['contrail-config-nodemgr','contrail-analytics-nodemgr','contrail-control-nodemgr','contrail-vrouter-nodemgr','openstack-nova-compute','contrail-svc-monitor','contrail-discovery:0','contrail-zookeeper', 'contrail-schema']
                for i,item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-vrouter':
                        contrail_vrouter_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)    
                    if item['process_name'] == 'contrail-vrouter-nodemgr':
                        contrail_vrouter_nodemgr_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'openstack-nova-compute':
                        openstack_nova_compute_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = { k:v for k,v in process_down_stop_time_dict.items() if k not in exclude_process_list }
                '''
                if not reduced_process_keys_dict :
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values()))) 
                    overall_node_status_string  = ['Down since ' + status for status in overall_node_status_down_time]
                '''
                if not reduced_process_keys_dict :
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values())))
                    process_down_count = len(reduced_process_keys_dict)
                    process_down_list = reduced_process_keys_dict.keys()
                    overall_node_status_string = str(process_down_count) +' Process down'

                generator_list = self.webui_common.get_generators_list_ops()
                for element in generator_list:
                    if element['name'] == ops_vrouter_name + ':Compute:VRouterAgent:0':
                        analytics_data = element['href']
                        break
                generators_vrouters_data = self.webui_common.get_details(element['href'])
                analytics_data = generators_vrouters_data.get('ModuleClientState').get('client_info')
                if analytics_data['status'] == 'Established':
                    analytics_primary_ip = analytics_data['primary'].split(':')[0] + ' (Up)'
                    tx_socket_bytes = analytics_data.get('tx_socket_stats').get('bytes')
                    tx_socket_size = self.webui_common.get_memory_string(int(tx_socket_bytes))
                    analytics_msg_count = generators_vrouters_data.get('ModuleClientState').get('session_stats').get('num_send_msg')
                    offset = 5
                    analytics_msg_count_list  = range(int(analytics_msg_count)-offset,int(analytics_msg_count)+offset)
                    analytics_messages_string = [ str(count) + ' [' + str(size) + ']' for count in analytics_msg_count_list for size in tx_socket_size ]
                control_nodes_list = vrouters_ops_data.get('VrouterAgent').get('xmpp_peer_list') 
                control_nodes_string = ''
                for node in control_nodes_list :
                    if node['status'] == True and node['primary'] == True:
                        control_ip =  node['ip']
                        control_nodes_string = control_ip + '* (Up)'
                        index = control_nodes_list.index(node)
                        del control_nodes_list[index]
                for node in control_nodes_list:
                    node_ip = node['ip']
                    if node['status'] == True :
                        control_nodes_string = control_nodes_string + ', ' + node_ip + ' (Up)'
                    else:
                        control_nodes_string = control_nodes_string + ', ' + node_ip + ' (Down)'
                        
                        
                modified_ops_data.extend([ {'key':'Flow Count','value':flow_count_string}, {'key': 'Hostname','value':host_name}, {'key': 'IP Address','value':ip_address}, {'key': 'Networks','value':networks}, {'key': 'Instances','value':instances}, {'key': 'CPU','value':cpu}, {'key': 'Memory','value':memory}, {'key': 'Version','value':version}, {'key': 'vRouter Agent','value':contrail_vrouter_string}, {'key': 'Overall Node Status','value':overall_node_status_string},  {'key': 'Analytics Node','value':analytics_primary_ip},{'key': 'Analytics Messages','value':analytics_messages_string}, {'key': 'Control Nodes','value':control_nodes_string}])
                self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info("ops %s uves vrouters basic view details data matched in webui" % (ops_vrouter_name))
                else :
                    self.logger.error("ops %s uves vrouters basic view details data match failed in webui" % (ops_vrouter_name))
                    error_flag = 1
        if not error_flag :
            return True
        else :
            return False
    
    def verify_vrouter_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying vrouter ops-data in Webui monitor->infra->Virtual Routers->details(advance view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_vrouters_in_webui()
        rows = self.webui_common.get_rows()
        vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
        error_flag = 0 
        for n in range(len(vrouters_list_ops)):
            ops_vrouter_name = vrouters_list_ops[n]['name']
            self.logger.info("vn host name %s exists in op server..checking if exists in webui as well"%(ops_vrouter_name))
            self.webui_common.click_monitor_vrouters_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_vrouter_name:
                    self.logger.info("vrouter name %s found in webui..going to match advance details now"%(ops_vrouter_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("vrouter name %s did not match in webui...not found in webui"%(ops_vrouter_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve vrouter advance details in webui for vrouter-name %s "%(ops_vrouter_name))
                self.webui_common.click_monitor_vrouters_advance_in_webui(match_index)
                vrouters_ops_data = self.webui_common.get_details(vrouters_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']}) 
                dom_arry_num = dom_arry_num_new   
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if vrouters_ops_data.has_key('VrouterStatsAgent'):
                    ops_data = vrouters_ops_data['VrouterStatsAgent']
                    history_del_list = ['total_in_bandwidth_utilization','cpu_share','used_sys_mem','one_min_avg_cpuload','virt_mem','total_out_bandwidth_utilization']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                                
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
                        self.logger.info("ops %s uves virual networks advance view data matched in webui" % (ops_vrouter_name))
                    else :
                        self.logger.error("ops %s uves virual networks advance data match failed in webui" % (ops_vrouter_name))
                        error_flag = 1
        if not error_flag :
            return True
        else :
            return False               
                        

    #end verify_vrouter_ops_advance_data_in_webui

    def verify_bgp_routers_ops_basic_data_in_webui(self) :
        self.logger.info("Verifying Control Nodes basic ops-data in Webui monitor->infra->Control Nodes->details(basic view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_control_nodes_in_webui()
        rows = self.webui_common.get_rows()
        bgp_routers_list_ops = self.webui_common.get_bgp_routers_list_ops()
        error_flag = 0
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_routers_name = bgp_routers_list_ops[n]['name']
            self.logger.info("control node host name %s exists in op server..checking if exists \
                in webui as well"%(ops_bgp_routers_name))
            self.webui_common.click_monitor_control_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_bgp_routers_name:
                    self.logger.info("bgp_routers name %s found in webui..going to match basic details now"%(
                        ops_bgp_routers_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("bgp_routers name %s did not match in webui...not found in webui"%(
                    ops_bgp_routers_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve control nodes basic view details in webui for \
                    control node name %s "%(ops_bgp_routers_name))
                self.webui_common.click_monitor_control_nodes_basic_in_webui(match_index)
                dom_basic_view = self.webui_common.get_basic_view_infra()
                # special handling for overall node status value
                node_status = self.browser.find_element_by_id('allItems').find_element_by_tag_name(
                    'p').get_attribute(
                    'innerHTML').split('/span>')[1].replace('\n','').strip()
                for i, item in enumerate(dom_basic_view):
                    if  item.get('key') == 'Overall Node Status' :
                        dom_basic_view[i]['value'] = node_status
                # filter bgp_routers basic view details from opserver data
                bgp_routers_ops_data = self.webui_common.get_details(bgp_routers_list_ops[n]['href'])
                ops_basic_data = []
                host_name = bgp_routers_list_ops[n]['name']
                ip_address = bgp_routers_ops_data.get('BgpRouterState').get('bgp_router_ip_list')[0]
                if not ip_address:
                    ip_address = '--'
                version = json.loads(bgp_routers_ops_data.get('BgpRouterState').get('build_info')).get(
                    'build-info')[0].get('build-id')
                version = self.webui_common.get_version_string(version)
                bgp_peers_string = 'BGP Peers: '+ str(bgp_routers_ops_data.get('BgpRouterState').get('num_bgp_peer'))+ ' Total'
                vrouters =  'vRouters: '+ str(bgp_routers_ops_data.get('BgpRouterState').get('num_up_xmpp_peer'))+'  Established in Sync'
                 
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
                        generators_vrouters_data = self.webui_common.get_details(element['href'])
                        analytics_data = generators_vrouters_data.get('ModuleClientState').get('client_info')
                        if analytics_data['status'] == 'Established':
                            analytics_primary_ip = analytics_data['primary'].split(':')[0] + ' (Up)'
                            tx_socket_bytes = analytics_data.get('tx_socket_stats').get('bytes')
                            tx_socket_size = self.webui_common.get_memory_string(int(tx_socket_bytes))
                            analytics_msg_count = generators_vrouters_data.get('ModuleClientState').get('session_stats').get('num_send_msg')
                            offset = 10
                            analytics_msg_count_list  = range(int(analytics_msg_count)-offset,int(analytics_msg_count)+offset)
                            analytics_messages_string = [ str(count) + ' [' + str(size) + ']'  for count in analytics_msg_count_list for size in tx_socket_size ]
                ifmap_ip = bgp_routers_ops_data.get('BgpRouterState').get('ifmap_info').get('url').split(':')[0]
                ifmap_connection_status = bgp_routers_ops_data.get('BgpRouterState').get('ifmap_info').get('connection_status')
                ifmap_connection_status_change = bgp_routers_ops_data.get('BgpRouterState').get('ifmap_info').get('connection_status_change_at')
                ifmap_connection_string = [ ifmap_ip + ' (' + ifmap_connection_status + ' since ' + time + ')' for time in self.webui_common.get_node_status_string(ifmap_connection_status_change)]  
                process_state_list = bgp_routers_ops_data.get('BgpRouterState').get('process_state_list')
                process_down_stop_time_dict = {}
                process_up_start_time_dict = {}
                exclude_process_list = ['contrail-config-nodemgr','contrail-analytics-nodemgr','contrail-control-nodemgr','contrail-vrouter-nodemgr','openstack-nova-compute','contrail-svc-monitor','contrail-discovery:0','contrail-zookeeper', 'contrail-schema'] 
                for i,item in enumerate(process_state_list):
                    if item['process_name'] == 'contrail-control':
                        control_node_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)    
                    if item['process_name'] == 'contrail-control-nodemgr':
                        control_nodemgr_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-dns':
                        contrail_dns_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                    if item['process_name'] == 'contrail-named':
                        contrail_named_string = self.webui_common.get_process_status_string(item, process_down_stop_time_dict, process_up_start_time_dict)
                reduced_process_keys_dict = { k:v for k,v in process_down_stop_time_dict.items() if k not in exclude_process_list }
                if not reduced_process_keys_dict :
                    for process in exclude_process_list:
                        process_up_start_time_dict.pop(process, None)
                    recent_time = max(process_up_start_time_dict.values())
                    overall_node_status_time = self.webui_common.get_node_status_string(str(recent_time))
                    overall_node_status_string  = ['Up since ' + status for status in overall_node_status_time]
                else:
                    overall_node_status_down_time = self.webui_common.get_node_status_string(str(max(reduced_process_keys_dict.values())))
                    process_down_list = reduced_process_keys_dict.keys() 
                    process_down_count = len(reduced_process_keys_dict)
                    overall_node_status_string = str(process_down_count) +' Process down' 
                modified_ops_data = []
                modified_ops_data.extend([{'key': 'Peers','value':bgp_peers_string}, {'key': 'Hostname','value':host_name}, {'key': 'IP Address','value':ip_address}, {'key': 'CPU','value':cpu}, {'key': 'Memory','value':memory}, {'key': 'Version','value':version}, {'key': 'Analytics Node','value':analytics_primary_ip},{'key': 'Analytics Messages','value':analytics_messages_string}, {'key': 'Ifmap Connection','value':ifmap_connection_string},{'key': 'Control Node','value':control_node_string},{'key': 'Overall Node Status','value':overall_node_status_string}])
                self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view)
                if self.webui_common.match_ops_with_webui(modified_ops_data, dom_basic_view):
                    self.logger.info("ops %s uves bgp_routers basic view details data matched in webui" % (ops_bgp_routers_name))
                else :
                    self.logger.error("ops %s uves bgp_routers basic view details data match failed in webui" % (ops_bgp_routers_name))
                    error_flag = 1
        if not error_flag :
            return True
        else :
            return False

    def verify_bgp_routers_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying Control Nodes ops-data in Webui monitor->infra->Control Nodes->details(advance view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_control_nodes_in_webui()
        rows = self.webui_common.get_rows()
        bgp_routers_list_ops = self.webui_common.get_bgp_routers_list_ops()
        error_flag = 0
        for n in range(len(bgp_routers_list_ops)):
            ops_bgp_router_name = bgp_routers_list_ops[n]['name']
            self.logger.info(" bgp router %s exists in op server..checking if exists in webui "%(ops_bgp_router_name))
            self.logger.info("Clicking on bgp_routers in monitor page  in Webui...")
            self.webui_common.click_monitor_control_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_bgp_router_name:
                    self.logger.info("bgp router name %s found in webui..going to match advance details now"%(ops_bgp_router_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("bgp router name %s not found in webui"%(ops_bgp_router_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve bgp advance view details in webui for bgp router-name %s "%(ops_bgp_router_name))
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
                bgp_router_state_ops_data = bgp_routers_ops_data['BgpRouterState']
                history_del_list = ['total_in_bandwidth_utilization','cpu_share','used_sys_mem','one_min_avg_cpuload','virt_mem','total_out_bandwidth_utilization']
                for item in history_del_list:
                    if bgp_router_state_ops_data.get(item):
                        for element in bgp_router_state_ops_data.get(item):
                            if element.get('history-10'):
                                del element['history-10']
                            if element.get('s-3600-topvals'):
                                del element['s-3600-topvals']
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
                        self.logger.info(" ops uves bgp router advanced view data matched in webui")
                    else :
                        self.logger.error(" ops uves bgp router advanced view bgp router match failed in webui")
                        error_flag = 1
        if not error_flag :
            return True
        else :
            return False

    #end verify_bgp_routers_ops_advance_data_in_webui

    def verify_analytics_nodes_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying analytics_nodes(collectors) ops-data in Webui monitor->infra->Analytics Nodes->details(advance view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_analytics_nodes_in_webui()
        rows = self.webui_common.get_rows()
        analytics_nodes_list_ops = self.webui_common.get_collectors_list_ops()
        error_flag = 0 
        for n in range(len(analytics_nodes_list_ops)):
            ops_analytics_node_name = analytics_nodes_list_ops[n]['name']
            self.logger.info(" analytics node %s exists in op server..checking if exists in webui "%(ops_analytics_node_name))
            self.logger.info("Clicking on analytics_nodes in monitor page  in Webui...")
            self.webui_common.click_monitor_analytics_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_analytics_node_name:
                    self.logger.info("analytics node name %s found in webui..going to match advance details now"%(ops_analytics_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("analytics node name %s not found in webui"%(ops_analytics_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve analytics advance view details in webui for analytics node-name %s "%(ops_analytics_node_name))
                self.webui_common.click_monitor_analytics_nodes_advance_in_webui(match_index)
                analytics_nodes_ops_data = self.webui_common.get_details(analytics_nodes_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                modified_query_perf_info_ops_data = []
                modified_module_cpu_state_ops_data = []
                modified_analytics_cpu_state_ops_data = []
                modified_collector_state_ops_data = []
                history_del_list = ['opserver_mem_virt','queryengine_cpu_share','opserver_cpu_share','collector_cpu_share','collector_mem_virt','queryengine_mem_virt','enq_delay']
                if analytics_nodes_ops_data.has_key('QueryPerfInfo'):
                    query_perf_info_ops_data = analytics_nodes_ops_data['QueryPerfInfo']
                    for item in history_del_list:
                        if query_perf_info_ops_data.get(item):
                            for element in query_perf_info_ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                                if element.get('s-3600-summary'):
                                    del element['s-3600-summary']
                    self.webui_common.extract_keyvalue(query_perf_info_ops_data, modified_query_perf_info_ops_data)
                if analytics_nodes_ops_data.has_key('ModuleCpuState'):
                    module_cpu_state_ops_data = analytics_nodes_ops_data['ModuleCpuState']
                    for item in history_del_list:
                        if module_cpu_state_ops_data.get(item):
                            for element in module_cpu_state_ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
                                if element.get('s-3600-summary'):
                                    del element['s-3600-summary']
                                
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
                    self.logger.info(" ops uves analytics node advance view data matched in webui")
                else :
                    self.logger.error("ops uves analytics node match failed in webui")
                    error_flag =1
        if not error_flag :
            return True
        else :
            return False
    #end verify_analytics_nodes_ops_advance_data_in_webui
    
    def verify_vm_ops_basic_data_in_webui(self):
        self.logger.info("Verifying VM basic ops-data in Webui monitor->Networking->instances summary(basic view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_instances_in_webui()
        rows = self.webui_common.get_rows()
        vm_list_ops = self.webui_common.get_vm_list_ops()
        error_flag =0
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            self.webui_common.click_monitor_instances_in_webui()
            rows = self.webui_common.get_rows()
            self.logger.info("vm uuid %s exists in op server..checking if exists in webui as well"%(ops_uuid))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[2].text == ops_uuid:
                    self.logger.info("vm uuid %s matched in webui..going to match basic view details now"%(ops_uuid))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    vm_name = rows[i].find_elements_by_class_name('slick-cell')[1].text
                    break
            if not match_flag :
                self.logger.error("uuid exists in opserver but uuid %s not found in webui..."%(ops_uuid))
                self.logger.info(self.dash)
            else:
                self.webui_common.click_monitor_instances_basic_in_webui(match_index)
                self.logger.info("Click and retrieve basic view details in webui for uuid %s "%(ops_uuid))
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
                        if ops_data_interface_list[k].get('floating_ips'):
                            fip_list = ops_data_interface_list[k].get('floating_ips')
                            floating_ip = None
                            fip_list_len = len(fip_list)
                            for index,element in enumerate(fip_list):
                                if index ==  0:
                                    floating_ip = element.get('ip_address') + ' (' +  element.get('virtual_network') + ')'
                                else:
                                    floating_ip = floating_ip + ' , ' + element.get('ip_address') + ' (' +  element.get('virtual_network') + ')'
                            ops_data_interface_list[k]['floating_ips'] = floating_ip
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
                dom_arry_intf.insert(0,{'key':'vm_name','value':vm_name})
                # insert non interface elements in list
                for i in range(len_dom_arry_basic):
                    element_key = elements[i].find_elements_by_tag_name('div')[0].text
                    element_value = elements[i].find_elements_by_tag_name('div')[1].text
                    dom_arry_intf.append({'key':element_key,'value':element_value})    
                for i in range(len_dom_arry_basic+1,len_elements):
                    elements_key = elements[len_dom_arry_basic].find_elements_by_tag_name('div')
                    elements_value = elements[i].find_elements_by_tag_name('div')
                    for j in range(len(elements_key)):
                        dom_arry_intf.append({'key':elements_key[j].text ,'value':elements_value[j].text})
                for element in complete_ops_data:
                    if element['key'] == 'name':
                        index = complete_ops_data.index(element)
                        del complete_ops_data[index]
                if self.webui_common.match_ops_values_with_webui( complete_ops_data, dom_arry_intf):
                    self.logger.info("ops vm uves basic view data matched in webui")
                else :
                    self.logger.error("ops vm uves basic data match failed in webui")
                    error_flag =1
        if not error_flag :
            return True
        else :
            return False   
    #end verify_vm_ops_basic_data_in_webui

    def verify_dashboard_details_in_webui(self):
       self.logger.info("Verifying dashboard details...")
       self.logger.info(self.dash)
       self.webui_common.click_monitor_dashboard_in_webui()
       dashboard_node_details = self.browser.find_element_by_id('topStats').find_elements_by_class_name('infobox-data-number')
       dashboard_data_details = self.browser.find_element_by_id('sparkLineStats').find_elements_by_class_name('infobox-data-number')
       dashboard_system_details = self.browser.find_element_by_id('system-info-stat').find_elements_by_tag_name('li')
       dom_data = []
       dom_data.append({'key':'vrouters','value':dashboard_node_details[0].text})
       dom_data.append({'key':'control_nodes','value':dashboard_node_details[1].text})
       dom_data.append({'key':'analytics_nodes','value':dashboard_node_details[2].text})
       dom_data.append({'key':'config_nodes','value':dashboard_node_details[3].text})
       dom_data.append({'key':'instances','value':dashboard_data_details[0].text})
       dom_data.append({'key':'interfaces','value':dashboard_data_details[1].text})
       dom_data.append({'key':'virtual_networks','value':dashboard_data_details[2].text})
       dom_data.append({'key':dashboard_system_details[0].find_element_by_class_name('key').text,'value':dashboard_system_details[0].find_element_by_class_name('value').text})
       dom_data.append({'key':dashboard_system_details[1].find_element_by_class_name('key').text,'value':dashboard_system_details[1].find_element_by_class_name('value').text})
       ops_dashborad_data = []
       self.webui_common.click_configure_networks_in_webui()
       rows = self.webui_common.get_rows() 
       vrouter_total_vn = str(len(rows)) 
       vrouter_total_vm  = str(len(self.webui_common.get_vm_list_ops()))
       total_vrouters = str(len(self.webui_common.get_vrouters_list_ops()))
       total_control_nodes = str(len(self.webui_common.get_bgp_routers_list_ops()))
       total_analytics_nodes = str(len(self.webui_common.get_collectors_list_ops()))
       total_config_nodes = str(len(self.webui_common.get_config_nodes_list_ops()))
       vrouters_list_ops = self.webui_common.get_vrouters_list_ops()
       interface_count = 0 
       for index in range(len(vrouters_list_ops)):
           vrouters_ops_data = self.webui_common.get_details(vrouters_list_ops[index]['href'])
           if vrouters_ops_data.get('VrouterAgent').get('total_interface_count'):
               interface_count = interface_count + vrouters_ops_data.get('VrouterAgent').get('total_interface_count')
       ops_dashborad_data.append({'key':'vrouters','value':total_vrouters})
       ops_dashborad_data.append({'key':'control_nodes','value':total_control_nodes})
       ops_dashborad_data.append({'key':'analytics_nodes','value':total_analytics_nodes})
       ops_dashborad_data.append({'key':'config_nodes','value':total_config_nodes})
       ops_dashborad_data.append({'key':'instances','value':vrouter_total_vm})
       ops_dashborad_data.append({'key':'interfaces','value':str(interface_count)})
       ops_dashborad_data.append({'key':'virtual_networks','value':vrouter_total_vn})
       error_flag = False 
       if self.webui_common.match_ops_with_webui(ops_dashborad_data, dom_data):
           self.logger.info("monitor dashborad details matched" )
       else:
           self.logger.error("monitor dashborad details not matched")
           error_flag = True
       if not error_flag :
           return True
       else:
           return False 
    #end verify_dashboard_details_in_webui

    def verify_vn_ops_basic_data_in_webui(self):
        self.logger.info("Verifying VN basic ops-data in Webui...")
        self.logger.info(self.dash)
        error  = 0
        self.webui_common.click_monitor_networks_in_webui()
        rows = self.webui_common.get_rows()
        vn_list_ops = self.webui_common.get_vn_list_ops()
        for k in range(len(vn_list_ops)):
            ops_fq_name = vn_list_ops[k]['name']
            self.webui_common.click_monitor_networks_in_webui()
            rows = self.webui_common.get_rows()
            self.logger.info("vn fq_name %s exists in op server..checking if exists in webui as well"%(ops_fq_name))
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[1].text == ops_fq_name:
                    self.logger.info("vn fq_name %s matched in webui..going to match basic view details now"%(ops_fq_name))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    vn_fq_name = rows[i].find_elements_by_class_name('slick-cell')[1].text
                    break
            if not match_flag :
                self.logger.error("vn fq_name exists in opserver but %s not found in webui..."%(ops_fq_name))
                self.logger.info(self.dash)
            else:
                self.webui_common.click_monitor_networks_basic_in_webui(match_index)
                self.logger.info("Click and retrieve basic view details in webui for VN fq_name %s "%(ops_fq_name))
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
                        complete_ops_data.append(ops_data_vrf)
                    if ops_data_basic.get('acl'):
                        ops_data_acl = {'key':'acl','value':ops_data_basic.get('acl')}
                        complete_ops_data.append(ops_data_acl)
                    if ops_data_basic.get('virtualmachine_list'):
                        ops_data_instances = {'key':'virtualmachine_list', 'value': ', '.join(ops_data_basic.get('virtualmachine_list'))}
                        complete_ops_data.append(ops_data_instances)
                complete_ops_data.extend([ops_data_ingress, ops_data_egress, ops_data_acl_rules,ops_data_interfaces_count])
                if ops_fq_name.find('__link_local__') != -1 or ops_fq_name.find('default-virtual-network') != -1  or ops_fq_name.find('ip-fabric') != -1 :
                    for i,item in enumerate(complete_ops_data):
                        if complete_ops_data[i]['key'] == 'vrf_stats_list':
                            del complete_ops_data[i]
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data_basic = vn_ops_data.get('UveVirtualNetworkConfig')
                    if ops_data_basic.get('attached_policies'):
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
                    self.logger.info("ops uves virutal networks basic view data matched in webui")
                   
                else :
                    self.logger.error("ops uves virutal networks  basic view data match failed in webui")
                    error = 1 
        return not error 
    #end verify_vn_ops_basic_data_in_webui
    
    def verify_config_nodes_ops_advance_data_in_webui(self) :
        self.logger.info("Verifying config_nodes ops-data in Webui monitor->infra->Config Nodes->details(advance view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_config_nodes_in_webui()
        rows = self.webui_common.get_rows()
        config_nodes_list_ops = self.webui_common.get_config_nodes_list_ops()
        error_flag =0 
        for n in range(len(config_nodes_list_ops)):
            ops_config_node_name = config_nodes_list_ops[n]['name']
            self.logger.info(" config node host name %s exists in op server..checking if exists in webui as well"%(ops_config_node_name))
            self.webui_common.click_monitor_config_nodes_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[0].text == ops_config_node_name:
                    self.logger.info("config node name %s found in webui..going to match advance view details now"%(ops_config_node_name))
                    match_flag = 1
                    match_index = i
                    break
            if not match_flag :
                self.logger.error("config node name %s did not match in webui...not found in webui"%(ops_config_node_name))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve config nodes advance view details in webui for config node-name %s "%(ops_config_node_name))
                self.webui_common.click_monitor_config_nodes_advance_in_webui(match_index)
                config_nodes_ops_data = self.webui_common.get_details(config_nodes_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                dom_arry_num = self.webui_common.get_advanced_view_num()
                dom_arry_num_new = []
                for item in dom_arry_num :
                    dom_arry_num_new.append({'key' : item['key'].replace('\\','"').replace(' ','') , 'value' : item['value']})
                dom_arry_num = dom_arry_num_new
                merged_arry = dom_arry + dom_arry_str + dom_arry_num
                if config_nodes_ops_data.has_key('ModuleCpuState'):
                    ops_data = config_nodes_ops_data['ModuleCpuState']
                    history_del_list = ['api_server_mem_virt','service_monitor_cpu_share','schema_xmer_mem_virt','service_monitor_mem_virt','api_server_cpu_share','schema_xmer_cpu_share']
                    for item in history_del_list:
                        if ops_data.get(item):
                            for element in ops_data.get(item):
                                if element.get('history-10'):
                                    del element['history-10']
                                if element.get('s-3600-topvals'):
                                    del element['s-3600-topvals']
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
                        self.logger.info("ops uves config nodes advance view data matched in webui")
                    else :
                        self.logger.error("ops uves config nodes advance view data match failed in webui")
                        error_flag=1
        if not error_flag :
            return True
        else :
            return False
    #end verify_config_nodes_ops_advance_data_in_webui

    def verify_vn_ops_advance_data_in_webui(self):
        
        self.logger.info("Verifying VN advance ops-data in Webui monitor->Networking->Networks Summary(basic view)......")
        self.logger.info(self.dash) 
        self.webui_common.click_monitor_networks_in_webui()
        rows = self.webui_common.get_rows()
        vn_list_ops = self.webui_common.get_vn_list_ops() 
        error_flag = 0
        for n in range(len(vn_list_ops)):
            ops_fqname = vn_list_ops[n]['name']
            self.logger.info("vn fq name %s exists in op server..checking if exists in webui as well"%(ops_fqname))
            self.webui_common.click_monitor_networks_in_webui()
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[1].text == ops_fqname:
                    self.logger.info("vn fq name %s found in webui..going to match advance view details now"%(ops_fqname))
                    self.logger.info(self.dash)
                    match_index = i
                    match_flag = 1
                    break
            if not match_flag :
                self.logger.error("vn fqname %s did not match in webui...not found in webui"%(ops_fqname))
                self.logger.info(self.dash)
            else:
                self.logger.info("Click and retrieve advance view details in webui for fqname %s "%(ops_fqname))
                self.webui_common.click_monitor_networks_advance_in_webui(match_index)
                vn_ops_data = self.webui_common.get_details(vn_list_ops[n]['href'])
                dom_arry = self.webui_common.parse_advanced_view()
                dom_arry_str = self.webui_common.get_advanced_view_str()
                merged_arry = dom_arry + dom_arry_str
                if vn_ops_data.has_key('UveVirtualNetworkConfig'):
                    ops_data = vn_ops_data['UveVirtualNetworkConfig']
                    modified_ops_data = []
                    self.webui_common.extract_keyvalue(ops_data, modified_ops_data)
                 
                if vn_ops_data.has_key('UveVirtualNetworkAgent'):
                    ops_data_agent = vn_ops_data['UveVirtualNetworkAgent']
                    if 'udp_sport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_sport_bitmap']
                    if 'udp_dport_bitmap' in ops_data_agent:
                        del ops_data_agent['udp_dport_bitmap'] 
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
                        self.logger.info("ops uves virtual networks advance view data matched in webui")
                    else :
                        self.logger.error("ops uves virtual networks advance view data match failed in webui")
                        error_flag =1
        if not error_flag :
            return True
        else :
            return False
    #end verify_vn_ops_advance_data_in_webui
 
    def verify_vm_ops_advance_data_in_webui(self):
        self.logger.info("Verifying VM ops-data in Webui monitor->Networking->instances->Instances summary(Advance view)......")
        self.logger.info(self.dash)
        self.webui_common.click_monitor_instances_in_webui()
        rows = self.webui_common.get_rows()
        vm_list_ops = self.webui_common.get_vm_list_ops()
        error_flag =0
        for k in range(len(vm_list_ops)):
            ops_uuid = vm_list_ops[k]['name']
            self.webui_common.click_monitor_instances_in_webui()
            rows = self.webui_common.get_rows()
            self.logger.info("vm uuid %s exists in op server..checking if exists in webui as well"%(ops_uuid)) 
            for i in range(len(rows)):
                match_flag = 0
                if rows[i].find_elements_by_class_name('slick-cell')[2].text == ops_uuid:
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
                self.logger.info("Click and retrieve advance view details in webui for uuid %s "%(ops_uuid))
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
                        self.logger.info("ops vm uves advance view data matched in webui")
                    else :
                        self.logger.error("ops vm uves advance data match failed in webui")
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
        rows = self.webui_common.get_rows()
        if ln != len(rows):
            self.logger.error("vn rows in grid mismatch with VNs in api")
        for i in range(ln):
            details  =  self.webui_common.get_details(vn_list[i]['href'])
            self.logger.info("VN details for %s got from API server and going to match in webui : " %(vn_list[i]))
            j=0
            for j in range(len(rows)):
                self.webui_common.click_configure_networks_in_webui()
                self.browser.get_screenshot_as_file('config_net_verify_api' + self.webui_common.date_time_string()+'.png')
                rows = self.webui_common.get_rows()
                if (rows[j].find_elements_by_tag_name('td')[2].get_attribute('innerHTML') == details['virtual-network']['fq_name'][2]) :
                    vn_name = details['virtual-network']['fq_name'][2]
                    ip_block=details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix']+'/'+ str(
                        details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']['ip_prefix_len'])
                    if rows[j].find_elements_by_tag_name('td')[4].text == ip_block:
                        self.logger.info( "VN %s : ip block matched" %(vn_name))
                    rows[j].find_elements_by_tag_name('td')[0].find_element_by_tag_name('a').click()
                    rows = self.webui_common.get_rows()
                    ui_ip_block=rows[j+1].find_element_by_class_name('span11').text.split('\n')[1]
                    if (ui_ip_block.split(' ')[0] == ':'.join(details['virtual-network']['network_ipam_refs'][0]['to']) and ui_ip_block.split(
                        ' ')[1] == ip_block and ui_ip_block.split(
                            ' ')[2] == details['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['default_gateway'] ):
                        self.logger.info( "VN %s basic details in webui network config page matched with api data " %(vn_name))
                    else:
                        self.logger.error( "VN %s basic details in webui network config page not matched with api data" %(vn_name))
                        self.browser.get_screenshot_as_file('verify_vn_api_data_webui_basic_details_failed' + self.webui_common.date_time_string()+'.png')
                    forwarding_mode=rows[j+1].find_elements_by_class_name('span2')[0].text.split('\n')[1]
                    vxlan=rows[j+1].find_elements_by_class_name('span2')[1].text.split('\n')[1]
                    network_dict = { 'l2_l3':'L2 and L3'}
                    if network_dict[details['virtual-network']['virtual_network_properties']['forwarding_mode']] == forwarding_mode:
                        self.logger.info( " VN %s : forwarding mode matched "  %(vn_name) )
                    else :
                        self.logger.error( "VN %s : forwarding mode not matched" %(vn_name))
                        self.browser.get_screenshot_as_file('verify_vn_api_data_forwarding_mode_match_failed' +self.webui_common.date_time_string()+'.png')

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
        rows=self.webui_common.get_rows()
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
        rows = self.webui_common.get_rows()
        #rows = self.browser.find_element_by_id('gridVN').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
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
                    rows = self.webui_common.get_rows()
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
                    rows = self.webui_common.get_rows()
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
        rows = self.webui_common.get_rows()
        ln = len(rows)
        vn_flag=0
        for i in range(len(rows)):
            if (rows[i].find_elements_by_tag_name('div')[2].get_attribute('innerHTML') == fixture.vn_name and rows[i].find_elements_by_tag_name(
                'div')[4].text==fixture.vn_subnets[0]) :
                vn_flag=1
                rows[i].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
                rows = self.webui_common.get_rows()
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
        rows=self.webui_common.get_rows()
        vn_entry_flag=0
        for i in range(len(rows)):
            fq_name=rows[i].find_elements_by_tag_name('div')[1].find_element_by_tag_name('div').text
            if(fq_name==fixture.ipam_fq_name[0]+":"+fixture.project_name+":"+fixture.vn_name):
                self.logger.info( " %s VN verified in monitor page " %(fq_name))
                vn_entry_flag=1
                break
        if not vn_entry_flag:
            self.logger.error( "VN %s Verification failed in monitor page" %(fixture.vn_name))
            self.browser.get_screenshot_as_file('verify_vn_monitor_page.png')
        if vn_entry_flag:
            self.logger.info( " VN %s and subnet verified in webui config and monitor pages" %(fixture.vn_name))
       # if self.webui_common.verify_uuid_table(fixture.vn_id):
       #     self.logger.info( "VN %s UUID verified in webui table " %(fixture.vn_name))
       # else:
       #     self.logger.error( "VN %s UUID Verification failed in webui table " %(fixture.vn_name))
       #     self.browser.get_screenshot_as_file('verify_vn_configure_page_ip_block.png')
        fixture.obj=fixture.quantum_fixture.get_vn_obj_if_present(fixture.vn_name, fixture.project_name)
        fq_type='virtual_network'
        full_fq_name=fixture.vn_fq_name+':'+fixture.vn_id
       # if self.webui_common.verify_fq_name_table(full_fq_name, fq_type):
       #     self.logger.info( "fq_name %s found in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
       # else:
       #     self.logger.error( "fq_name %s failed in fq Table for %s VN" %(fixture.vn_fq_name,fixture.vn_name))
       #     self.browser.get_screenshot_as_file('setting_page_configure_fq_name_error.png')
        return True
    #end verify_vn_in_webui

    def vn_delete_in_webui(self, fixture):
        self.browser.get_screenshot_as_file('vm_delete.png')
        self.webui_common.click_configure_networks_in_webui()
        rows = self.webui_common.get_rows() 
        ln = len(rows)
        for net in rows :
            if (net.find_elements_by_tag_name('div')[2].text==fixture.vn_name):
                net.find_elements_by_tag_name('div')[1].find_element_by_tag_name('input').click()
                break
        self.browser.find_element_by_id('btnDeleteVN').click()
        self.webui_common.wait_till_ajax_done(self.browser) 
        time.sleep(2)
        self.browser.find_element_by_id('btnCnfRemoveMainPopupOK').click() 
        self.logger.info("%s is deleted successfully using WebUI"%(fixture.vn_name))
    #end vn_delete_in_webui

    def create_vm_in_openstack(self, fixture):
        try:
            if not self.proj_check_flag:
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
                time.sleep(3)
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h4')).click()
                WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_id('tenant_list')).click()
                current_project=WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h3')).text
                if not current_project==fixture.project_name:
                    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_css_selector('h3')).click()
                    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text(fixture.project_name)).click()
                    self.webui_common.wait_till_ajax_done(self.browser_openstack)                    
                    self.proj_check_flag = 1
            
	    WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Project')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            instance = WebDriverWait(self.browser_openstack, self.delay).until(lambda a: a.find_element_by_link_text('Instances')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            fixture.nova_fixture.get_image(image_name=fixture.image_name)
            time.sleep(2)
            launch_instance = WebDriverWait(self.browser_openstack, self.delay).until(
                lambda a: a.find_element_by_link_text('Launch Instance')).click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
            self.logger.debug('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            self.logger.info('creating instance name %s with image name %s using openstack'
                %(fixture.vm_name,fixture.image_name))
            time.sleep(3)
            self.browser_openstack.find_element_by_xpath(
                "//select[@name='source_type']/option[contains(text(), 'image') or contains(text(),'Image')]").click()
            self.webui_common.wait_till_ajax_done(self.browser_openstack) 
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
            self.webui_common.wait_till_ajax_done(self.browser_openstack)
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
                            self.webui_common.wait_till_ajax_done(self.browser_openstack)
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
            rows = self.webui_common.get_rows()       
            ln = len(rows)
            vm_flag=0
            for i in range(len(rows)):
                rows_count = len(rows)
                vm_name=rows[i].find_elements_by_class_name('slick-cell')[1].text 
                vm_uuid=rows[i].find_elements_by_class_name('slick-cell')[2].text
                vm_vn=rows[i].find_elements_by_class_name('slick-cell')[3].text.split(' ')[0]
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
                        rows = self.webui_common.get_rows()
                        rows[i].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
                        try :
                            retry_count = retry_count + 1
                            rows = self.webui_common.get_rows()
                            rows[i+1].find_elements_by_class_name('row-fluid')[0].click()
                            self.webui_common.wait_till_ajax_done(self.browser)
                            break
                        except WebDriverException:
                            pass

                    rows = self.webui_common.get_rows() 
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
            time.sleep(4)
            self.webui_common.wait_till_ajax_done(self.browser)
            rows = self.webui_common.get_rows()
            for i in range(len(rows)):
                if(rows[i].find_elements_by_class_name('slick-cell')[1].text==fixture.vn_fq_name.split(':')[0]+":"+fixture.project_name+":"+fixture.vn_name):
                    rows[i].find_elements_by_tag_name('div')[0].find_element_by_tag_name('i').click()
                    time.sleep(2)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    rows=self.webui_common.get_rows()
                    vm_ids=rows[i+1].find_element_by_xpath("//div[contains(@id, 'basicDetails')]").find_elements_by_class_name('row-fluid')[5].find_elements_by_tag_name('div')[1].text
                    if fixture.vm_id in vm_ids:
                        self.logger.info( "vm_id matched in webui monitor network basic details page %s" %(fixture.vn_name))
                    else :
                        
                        self.logger.error("vm_id not matched in webui monitor network basic details page %s" %(fixture.vm_name)) 
                        self.browser.get_screenshot_as_file('monitor_page_vm_id_not_match'+fixture.vm_name+fixture.vm_id+'.png')
                    break
            #if self.webui_common.verify_uuid_table(fixture.vm_id):
            #    self.logger.info( "UUID %s found in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            #else:
            #    self.logger.error( "UUID %s failed in UUID Table for %s VM" %(fixture.vm_name,fixture.vm_id))
            #fq_type='virtual_machine'
            #full_fq_name=fixture.vm_id+":"+fixture.vm_id
            #if self.webui_common.verify_fq_name_table(full_fq_name,fq_type):
            #   self.logger.info( "fq_name %s found in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
            #else:
            #   self.logger.error( "fq_name %s failed in fq Table for %s VM" %(fixture.vm_id,fixture.vm_name))
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
                    self.webui_common.wait_till_ajax_done(self.browser)
                    net.find_elements_by_tag_name('li')[0].find_element_by_tag_name('a').click()
                    ip_text =  net.find_element_by_xpath("//span[contains(text(), 'Floating IP Pools')]")
                    ip_text.find_element_by_xpath('..').find_element_by_tag_name('i').click()
                    route = self.browser.find_element_by_xpath("//div[@title='Add Floating IP Pool below']")
                    route.find_element_by_class_name('icon-plus').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    self.browser.find_element_by_xpath("//input[@placeholder='Pool Name']").send_keys(fixture.pool_name)
                    pool_con = self.browser.find_element_by_id('fipTuples')
                    pool_con.find_element_by_class_name('k-multiselect-wrap').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    ip_ul= self.browser.find_element_by_xpath("//ul[@aria-hidden = 'false']")
                    ip_ul.find_elements_by_tag_name('li')[0].click()
                    self.browser.find_element_by_xpath("//button[@id = 'btnCreateVNOK']").click()
                    self.webui_common.wait_till_ajax_done(self.browser)
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
                    self.webui_common.wait_till_ajax_done(self.browser)
                    time.sleep(1)
                    pool=self.browser.find_element_by_xpath("//div[@id='windowCreatefip']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(2)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    fip=self.browser.find_element_by_id("ddFipPool_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML")==fixture.vn_name+':'+fixture.pool_name:
                            fip[i].click()
                    self.browser.find_element_by_id('btnCreatefipOK').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
                    rows1=self.browser.find_elements_by_xpath("//tbody/tr")
                    for element in rows1:
                        if element.find_elements_by_tag_name('td')[3].text==fixture.vn_name+':'+fixture.pool_name:
                            element.find_elements_by_tag_name('td')[5].find_element_by_tag_name(
                                'div').find_element_by_tag_name('div').click()
                            element.find_element_by_xpath("//a[@class='tooltip-success']").click()
                            self.webui_common.wait_till_ajax_done(self.browser)
                            break
                    pool=self.browser.find_element_by_xpath("//div[@id='windowAssociate']").find_element_by_class_name(
                        'modal-body').find_element_by_class_name('k-input').click()
                    time.sleep(1)
                    self.webui_common.wait_till_ajax_done(self.browser)
                    fip=self.browser.find_element_by_id("ddAssociate_listbox").find_elements_by_tag_name('li')
                    for i in range(len(fip)):
                        if fip[i].get_attribute("innerHTML").split(' ')[1]==vm_id :
                            fip[i].click()
                    self.browser.find_element_by_id('btnAssociatePopupOK').click()
                    self.webui_common.wait_till_ajax_done(self.browser)
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
                rows = self.webui_common.get_rows()
                fip_check=rows[i+1].find_elements_by_xpath("//td/div/div/div")[1].text
                if fip_check.split('\n')[1].split(' ')[0]==fixture.pool_name:
                    self.logger.info( "fip pool %s verified in WebUI configure network page" %(fixture.pool_name))
                    break
        WebDriverWait(self.browser, self.delay).until(lambda a: a.find_element_by_xpath("//*[@id='config_net_fip']/a")).click()
        self.webui_common.wait_till_ajax_done(self.browser)
        rows = self.browser.find_element_by_xpath("//div[@id='gridfip']/table/tbody").find_elements_by_tag_name('tr')
        for i in range(len(rows)):
            fip=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[1]
            vn=rows[i].find_elements_by_tag_name('td')[3].text.split(':')[0]
            fip_ip=rows[i].find_elements_by_class_name('slick-cell')[1].text
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
                self.webui_common.wait_till_ajax_done(self.browser)
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
                self.webui_common.wait_till_ajax_done(self.browser)
                net.find_element_by_xpath("//a[@class='tooltip-error']").click()      
                self.webui_common.wait_till_ajax_done(self.browser)       
                WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnDisassociatePopupOK')).click()        
                self.webui_common.wait_till_ajax_done(self.browser)
                self.webui_common.wait_till_ajax_done(self.browser)     
            rows = self.browser.find_element_by_id('gridfip').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')       
            for net in rows:
                if (net.find_elements_by_tag_name('td')[3].get_attribute('innerHTML') == fixture.vn_name+':'+fixture.pool_name) :
                    net.find_elements_by_tag_name('td')[0].find_element_by_tag_name('input').click()
                    WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnDeletefip')).click()
                    WebDriverWait(self.browser,self.delay).until(lambda a: a.find_element_by_id('btnCnfReleasePopupOK')).click()                   
                   
            self.webui_common.click_configure_networks_in_webui()
            rows = self.webui_common.get_rows()
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
