''' This module provides utils for setting up scale config'''
from vnc_api_test import *
import psutil
import ast
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from collections import defaultdict
from tcutils.util import copy_file_to_server


class ServerHealth(object):

    def __init__(self, inputs, logger, connections, vnc_lib, auth):

        self.inputs = inputs
        self.logger = logger
        self.connections = connections
        self.vnc_lib = vnc_lib
        self.auth = auth

    def get_cpu_memory_usage(self):
       cpu_memory_dict = defaultdict(lambda: defaultdict(str))
       for each_host in self.inputs.host_names:
           self.copy_psutil_file(each_host)
           for i in range (len(self.inputs.host_data[each_host]['roles'])):
               service_name = self.inputs.host_data[each_host]['roles'][i]['type'] +  '_services'
               if service_name.startswith('bgp'): service_name = 'control_services'
               if  hasattr(self.inputs, service_name):
                   for each_service in eval ('self.inputs.' + '%s' %(service_name)):
                       if not each_service.startswith('supervisor') and not each_service.startswith('openstack') and not each_service.endswith('nodemgr'):
                           output = self.get_cpu_memory_usage_for_single_service(each_host,each_service)
                           if output != '':
                               cpu_memory_dict[each_host][each_service] = output
       return cpu_memory_dict         

    def copy_psutil_file (self, host_name):
      
        host_node = {'username': self.inputs.host_data[
                             host_name]['username'],
                         'password': self.inputs.host_data[
                             host_name]['password'],
                         'ip': self.inputs.host_data[
                             host_name]['host_ip']}
        path = os.getcwd() + '/serial_scripts/tor_scale/lib/process_status.py'
        copy_file_to_server(host_node, path, '/tmp', 'process_status.py')

    def get_cpu_memory_usage_for_single_service (self, host_name, service_name):
     
        cmd = "python /tmp/process_status.py %s" %(service_name)
        output = self.inputs.run_cmd_on_server(
                   self.inputs.host_data[host_name]['host_ip'],
                   cmd, username = self.inputs.host_data[host_name]['username'],
                   password = self.inputs.host_data[host_name]['password'])
        output = ast.literal_eval(output)
        return output

       
         

    


