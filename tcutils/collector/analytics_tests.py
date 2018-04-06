# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import fixtures
from tcutils.util import *
import logging as LOG
import re
import json
import urllib2
import requests
import time
import datetime
import threading
import Queue
from subprocess import Popen, PIPE
import shlex
import pprint
from netaddr import *
import random
from tcutils.collector.opserver_introspect_utils import VerificationOpsSrvIntrospect
from physical_router_fixture import PhysicalRouterFixture
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.collector.opserver_util import OpServerUtils

months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun':
          6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
months_number_to_name = {
    '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR', '05': 'MAY',
    '06': 'JUN', '07': 'JUL', '08': 'AUG', '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'}

uve_dict = {
    'xmpp-peer/': ['state_info', 'peer_stats_info', 'event_info', 
                    'send_state', 'identifier'],
    'config-node/': ['module_cpu_info', 'module_id', 'cpu_info', 
                    'build_info', 'config_node_ip', 'process_info'],
    'control-node/': ['uptime', 'build_info', 'cpu_info', 'ifmap_info', 'process_info'],
    'analytics-node/': ['cpu_info', 'ModuleCpuState', 'module_cpu_info', 
                        'process_info', 'contrail-collector', 'contrail-query-engine',
                        'contrail-analytics-nodemgr', 'contrail-analytics-api', 'build_info',
                        'generator_infos'],
    'generator/': ['client_info', 'ModuleServerState', 'session_stats', 'generator_info'],
    'bgp-peer/': ['state_info', 'peer_stats_info', 'families', 'peer_type', 'local_asn',
                  'configured_families', 'event_info', 'peer_address', 'peer_asn', 'send_state'],
    'vrouter/': ['exception_packets', 'cpu_info', 'uptime', 
                    'total_flows', 'drop_stats', 'xmpp_stats_list', 
                    'vhost_stats', 'process_info',
                    'control_ip', 'dns_servers', 
                    'build_info', 'vhost_cfg', 
                    'tunnel_type', 'xmpp_peer_list', 
                    'self_ip_list','process_status',
                    'exception_packets','drop_stats',
                    'phy_if_stats_list',
                    'vhost_stats'],
    'dns-node/': ['start_time', 'build_info', 'self_ip_list'],
    'virtual-machine/': [
                          'interface_list',
                          'vm_name',
                          'uuid']}

uve_list = ['xmpp-peer/', 'config-node/', 'control-node/','virtual-machine/',
            'analytics-node/', 'generator/', 'bgp-peer/', 'dns-node/', 'vrouter/']

exceptions={'device_manager':'contrail-device-manager',
                    'schema':'contrail-schema',
                    'svc-monitor':'contrail-svc-monitor'
                   }
exceptions_flags = {'device_manager':False,
                    'schema' : False,
                    'svc-monitor':False 
                  } 

http_introspect_ports = {'HttpPortConfigNodemgr' : 8100,
                             'HttpPortControlNodemgr' : 8101,
                             'HttpPortVRouterNodemgr' : 8102,
                             'HttpPortDatabaseNodemgr' : 8103,
                             'HttpPortAnalyticsNodemgr' : 8104,
                             'HttpPortStorageStatsmgr' : 8105,
                             'HttpPortControl' : 8083,
                             'HttpPortApiServer' : 8084,
                             'HttpPortAgent' : 8085,
                             'HttpPortSchemaTransformer' : 8087,
                             'HttpPortSvcMonitor' : 8088,
                             'HttpPortCollector' : 8089,
                             'HttpPortOpserver' : 8090,
                             'HttpPortQueryEngine' : 8091,
                             'HttpPortDns' : 8092}

GENERATORS = {'Compute' : ['contrail-vrouter-agent',
                            'contrail-vrouter-nodemgr'
                            ],
              'Analytics' : ['contrail-snmp-collector',
                            'contrail-query-engine',
                            'contrail-analytics-nodemgr',
                            'contrail-topology',
                            'contrail-collector',
                            'contrail-analytics-api'
                            ], 
            'Database' : ['contrail-database-nodemgr'],
            'Config' : ['contrail-api',
                        'contrail-svc-monitor',
                        'contrail-config-nodemgr',
                        'contrail-schema',
                        'contrail-device-manager'],
            'Control' : ['contrail-control',
                        'contrail-control-nodemgr',
                        'contrail-dns'
                        ]
            }

class AnalyticsVerification(fixtures.Fixture):

    def __init__(self, inputs, cn_inspect, agent_inspect, ops_inspect, logger=LOG):

        self.inputs = inputs
        self.ops_inspect = ops_inspect
        self.agent_inspect = agent_inspect
        self.cn_inspect = cn_inspect
        self.logger = logger
        self.get_all_generators()
        self.uve_verification_flags = []
        self.contrail_internal_vip = self.inputs.contrail_internal_vip

    def get_all_generators(self):
        self.generator_hosts = []
        self.bgp_hosts = []
        self.compute_hosts = []
        self.collector_hosts = []

        for collector_ip in self.inputs.collector_ips:
            if collector_ip == self.inputs.contrail_internal_vip:
                continue
            c_host = self.inputs.host_data[collector_ip]['name']
            self.collector_hosts.append(c_host)
            if (c_host not in self.generator_hosts):
                self.generator_hosts.append(c_host)

        for ip in self.inputs.bgp_ips:
            if ip == self.inputs.contrail_internal_vip:
                continue
            bgp_host = self.inputs.host_data[ip]['name']
            self.bgp_hosts.append(bgp_host)
            if (bgp_host not in self.generator_hosts):
                self.generator_hosts.append(bgp_host)
        for ip in self.inputs.compute_ips:
            compute_host = self.inputs.host_data[ip]['name']
            self.compute_hosts.append(compute_host)
            if (compute_host not in self.generator_hosts):
                self.generator_hosts.append(compute_host)

    def get_connection_status(self, collector, generator, moduleid, node_type, instanceid='0'):
        '''Getting connection status with generator:node_type:moduleid:instanceid with collector
        '''
        connobj = self.get_connection_dict(
            collector, generator, moduleid, node_type, instanceid)
        if connobj:
            return connobj['status']
        else:
            return None

    def get_primary_collector(self, opserver, generator, moduleid, node_type, instanceid='0'):
        '''Get primary collector for a generator'''

        connobj = self.get_connection_dict(
            opserver, generator, moduleid, node_type, instanceid)
        if connobj:
            return connobj['primary']
        else:
            return None

    def get_secondary_collector(self, opserver, generator, moduleid, node_type, instanceid='0'):
        '''Get secondary collector for a generator'''

        connobj = self.get_connection_dict(
            opserver, generator, moduleid, node_type, instanceid)
        if connobj:
            return connobj['secondary']
        else:
            return None

    @retry_for_value(delay=2, tries=5)
    def get_ops_generator_from_ops_introspect(self, collector, generator, moduleid, node_type, instanceid):
        obj = self.ops_inspect[collector].get_ops_generator(
            generator=generator, moduleid=moduleid, node_type=node_type, instanceid=instanceid)
        if not obj:
            self.logger.warn("ops generator uve analytics/uves/generator/%s:%s:%s?flat not returned" %
                             (generator, node_type, moduleid))
        return obj

    def get_connection_dict(self, collector, generator, moduleid, node_type, instanceid):
        '''Getting connection dict with generator:moduleid with collector
        '''
        self.opsobj = self.get_ops_generator_from_ops_introspect(collector, generator, moduleid, node_type, instanceid)
        if not self.opsobj:
            self.logger.error("query returned none")
            return None
        self.conoutput = self.opsobj.get_attr('Client', 'client_info')
        if not self.conoutput:
            self.logger.debug("query returned none")
            return None
        return self.conoutput

    def verify_generator_connection_to_collector(self):
        '''Verify the collector connection with different modules'''

        for k,v in GENERATORS.items():
            if (k == 'Compute'):
                for name in self.inputs.compute_names:
                    for elem in v:
                        assert self.verify_connection_status(
                                name,elem,k) 
            if (k == 'Analytics'):
                for name in self.inputs.collector_names:
                    for elem in v:
                        assert self.verify_connection_status(
                                name,elem,k) 
            if (k == 'Database'):
                for name in self.inputs.database_names:
                    for elem in v:
                        assert  self.verify_connection_status(
                                name,elem,k) 
            if (k == 'Config'):
                
                for name in self.inputs.cfgm_names:
                    result = False
                    for elem in v:
                        result = result or self.verify_connection_status(
                                name,elem,k)
                assert result        
                         
            if (k == 'Control'):
                for name in self.inputs.bgp_names:
                    for elem in v:
                        assert self.verify_connection_status(
                                name,elem,k) 

    @retry(delay=5, tries=4)
    def verify_connection_status(self, generator, moduleid, node_type, instanceid='0'):
        '''Verify if connection status with collector and generator:node_type:moduleid:instance
            is established
        '''

        self.g = generator
        self.m = moduleid
        result = True
        for collector_ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in %s" %
                             (collector_ip))
            status = self.get_connection_status(
                collector_ip, self.g, self.m, node_type, instanceid)
            if (status == 'Established'):
                self.logger.info("Validated that %s:%s:%s:%s is connected to \
                    collector %s" %(self.g, node_type, self.m, instanceid, 
                    collector_ip))
                result = result & True
            else:
                self.logger.warn(
                    "%s:%s:%s:%s is NOT connected to collector %s" %
                    (self.g, node_type, self.m, instanceid, collector_ip))
                result = result & False
        return result

    def get_collector_of_gen(self, collector, gen, module, node_type, instance='0'):
        '''Gets the collector node of a generator
        '''
        connobj = self.get_connection_dict(
            collector, gen, module, node_type, instance)
        return connobj['collector_name']

    def get_all_generator_links(self, module=None):
        '''Get all links for a particular generator'''

        ret = []
        try:
            links = self.ops_inspect[self.inputs.collector_ips[
                0]].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='generators')
            if links:
                pattern = '%s(.*)' % module
                compiled = re.compile(pattern)
                for elem in links:
                    if compiled.search(str(elem)):
                        ret.append(elem)
        except Exception as e:
            self.logger.warn("Got exception as %s" % (e))
        finally:
            return ret

    def get_module_instances(self, module):
        '''Return the module instances from analytics/genarators url'''
        ret = []
        try:
            links = self.get_all_generator_links(module=module)
            if links:
                for elem in links:
                    inst = str(elem['name']).split(":")[-1]
                    ret.append(inst)
        except Exception as e:
            self.logger.warn("Got exception as %s" % (e))
        finally:
            return ret

    def get_uve_key(self, uve=None):
        '''{
            href: "http://10.204.216.14:8081/analytics/uves/virtual-machine/292c7779-c085-4079-91f6-440272bd2922?flat",
            name: "292c7779-c085-4079-91f6-440272bd2922"
        }'''
        ret = []
        try:
            links = self.ops_inspect[self.inputs.collector_ips[0]
                                     ].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType=uve)
            if links:
                for elem in links:
                    ret.append(elem['name'])
        except Exception as e:
            self.logger.warn("Got exception as %s" % (e))
        finally:
            return ret


# Collector uve functions#
# ------------------------#

  #  @retry(delay=5, tries=1)
    def verify_collector_uve(self):
        '''Verify that all generators are connected to collector'''
        result = True

        # Verify module-ids correctly shown in the  collector uve for respective generators
         # verify module-id for bgp node in collector uve - should be
         # 'Contrail-Control'
        for ip in self.inputs.bgp_ips:
            assert self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortControl'])
        for ip in self.inputs.cfgm_ips:
            assert self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortApiServer'])
        result = False
        for ip in self.inputs.cfgm_ips:
            if not self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortSchemaTransformer']):
                continue
            else:
                result = result or self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortSchemaTransformer'])
        assert result

        for ip in self.inputs.cfgm_ips:
            result = result or self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortSvcMonitor'])
        assert result
        for ip in self.inputs.collector_ips:
            assert self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortOpserver'])
        for ip in self.inputs.collector_ips:
            assert self.verify_collector_connection_introspect(ip,http_introspect_ports['HttpPortQueryEngine'])
        for ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in %s" % (ip))
            expected_module_id = ['contrail-control', 'contrail-dns']
            expected_node_type = 'Control'
            expected_instance_id = '0'
            for bgp_host in self.bgp_hosts:
                for module in expected_module_id:
                    is_established = self.verify_connection_status(
                        bgp_host, module, expected_node_type, expected_instance_id)
                    # collector=self.output['collector_name']
                    if is_established:
                    #self.logger.info("%s:%s connected to collector %s"%(bgp_host,module,collector))
                        result = result and True
                    else:
                        result = result and False

            expected_module_id = 'contrail-vrouter-agent'
            expected_node_type = 'Compute'
            expected_instance_id = '0'
            for compute_host in self.compute_hosts:
                is_established = self.verify_connection_status(
                    compute_host, expected_module_id, expected_node_type, expected_instance_id)
                # collector=self.output['collector_name']
                if is_established:
                    result = result and True
                else:
                    result = result and False
            # Verifying module_id from ApiServer
            expected_cfgm_modules = 'contrail-schema'
            expected_node_type = 'Config'
            expected_instance_id = '0'
            for cfgm_node in self.inputs.cfgm_names:
                result1 = True
                is_established = self.verify_connection_status(
                    cfgm_node, expected_cfgm_modules, expected_node_type, expected_instance_id)
                if is_established:
                    # collector=self.output['collector_name']
                    result1 = result1 and True
                    break
                else:
                    result1 = result1 and False
            result = result and result1
            #Verifying for ServiceMonitor
            expected_cfgm_modules = 'contrail-svc-monitor'
            expected_node_type = 'Config'
            expected_instance_id = '0'
            for cfgm_node in self.inputs.cfgm_names:
                result1 = True
                is_established = self.verify_connection_status(
                    cfgm_node, expected_cfgm_modules, expected_node_type, expected_instance_id)
                if is_established:
                    # collector=self.output['collector_name']
                    resulti1 = result1 and True
                    break
                else:
                    result1 = result1 and False
            result = result and result1
            # Verifying module_id  ApiServer
            expected_apiserver_module = 'Contrail-Api'
            expected_apiserver_instances = self.get_module_instances(
                expected_apiserver_module)
            expected_node_type = 'Config'
            # expected_cfgm_modules=['Contrail-Schema','contrail-svc-monitor']
            for cfgm_node in self.inputs.cfgm_names:
                for inst in expected_apiserver_instances:
                    result1 = True
                    is_established = self.verify_connection_status(
                        cfgm_node, expected_apiserver_module, expected_node_type, inst)
                    if is_established:
                        result1 = result1 and True
                        break
                    else:
                        result = result and False
                result = result1 and result
            # Verifying module_id Contrail-Analytics-Api
            expected_opserver_module = 'Contrail-Analytics-Api'
            expected_opserver_instances = self.get_module_instances(
                expected_opserver_module)
            expected_node_type = 'Analytics'
            for c_host in self.collector_hosts:
                for inst in expected_opserver_instances:
                    is_established = self.verify_connection_status(
                        c_host, expected_opserver_module, expected_node_type, inst)
                    if is_established:
                        # collector=self.output['collector_name']
                        result = result and True
                    else:
                        result = result and False
            # Verifying collector:moduleid
            expected_collector_module = ['contrail-collector', 'contrail-query-engine']
            expected_node_type = 'Analytics'
            expected_instance_id = '0'
            for c_host in self.collector_hosts:
                for module in expected_collector_module:
                    is_established = self.verify_connection_status(
                        c_host, module, expected_node_type, expected_instance_id)
                    # collector=self.output['collector_name']
                    if is_established:
                        result = result and True
                    else:
                        result = result and False
        return result

    @retry(delay=3, tries=15)
    def verify_hrefs_to_all_uves_of_a_given_uve_type(self):
        '''Verify all analytics links
        '''
        result = True
        for ip in self.inputs.collector_ips:
            self.logger.debug(
                "Verifying the bgp-routers links through opserver %s" % (ip))
            self.links = self.ops_inspect[
                ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='control-nodes')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                gen_list.append(name)
            missing_nodes = set(gen_list) ^ set(self.inputs.bgp_names)
            if not missing_nodes:
                self.logger.info("%s is present in the link" %
                                 (self.inputs.bgp_names))
                result = result and True
            else:
                self.logger.info(
                    "%s is not present in the in the bgp-routers" %
                    (missing_nodes))
                result = result and False

            self.logger.info(
                "Verifying the vrouters links through opserver %s" % (ip))
            self.links = self.ops_inspect[
                ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='vrouters')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                gen_list.append(name)
            for name in self.inputs.compute_names:
                if (name in gen_list):
                    self.logger.info("%s is present in the link" % (name))
                    result = result and True
                else:
                    self.logger.info(
                        "%s is not present in the in the vrouters" % (name))
                    result = result and False

            self.logger.info(
                "Verifying the collector links through opserver %s" % (ip))
            self.links = self.ops_inspect[
                ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='analytics-nodes')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                gen_list.append(name)
            missing_nodes = set(gen_list) ^ set(self.inputs.collector_names)
            if not missing_nodes:
                self.logger.info("%s is present in the link" %
                                 (self.inputs.collector_names))
                result = result and True
            else:
                self.logger.info(
                    "%s is not present in the in the bgp-routers" %
                    (missing_nodes))
                result = result and False

            self.logger.info(
                "Verifying the collector links through opserver %s" % (ip))
            self.links = self.ops_inspect[
                ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='config-nodes')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                gen_list.append(name)
            missing_nodes = set(gen_list) ^ set(self.inputs.cfgm_names)
            if not missing_nodes:
                self.logger.info("%s is present in the link" %
                                 (self.inputs.cfgm_names))
                result = result and True
            else:
                self.logger.info(
                    "%s is not present in the in the bgp-routers" %
                    (missing_nodes))
                result = result and False
        return result
# end collector uve functions

# vrouter uve functions
# ------------------------#

    # Vrouter xmpp connection verification
    @retry(delay=3, tries=15)
    def verify_vrouter_xmpp_connections(self):
        '''Verify that vrouter is connected to the bgp router'''
        result = False
        for compute_host in self.compute_hosts:
            peers = []
            collector = self.get_collector_of_gen(
                self.inputs.collector_ips[0], compute_host, 'contrail-vrouter-agent', 'Compute')
            collector_ip = self.inputs.host_data[collector]['host_ip']
            self.ops_compute_obj = self.ops_inspect[
                collector_ip].get_ops_vrouter(vrouter=compute_host)
            xmpp_peer_list = self.ops_compute_obj.get_attr(
                'Agent', 'xmpp_peer_list')
            for elem in xmpp_peer_list:
                ip = elem['ip']
                peers.append(ip)
            factor = 1
            if len(self.inputs.bgp_control_ips)>1:
                factor = 2 # Xmpp client connects to 2 servers at most when more are available
            missing_peers = set(self.inputs.bgp_control_ips) - set(peers)
            if not len(missing_peers) > len(self.inputs.bgp_control_ips) - factor:
                self.logger.info(
                    "Vrouter %s connected to %s xmpp peers out of %s" %
                    (compute_host, set(peers), set(self.inputs.bgp_control_ips)))
                self.logger.info(
                    "xmpp peer correctly displayed as %s for vrouter %s " %
                    (peers, compute_host))
                result = True
            else:
                self.logger.error("vrouter %s not connected to 2 xmpp peers, should connect to at least one more from %s" %
                                  (compute_host, missing_peers))
                return False
        return result

    @retry(delay=3, tries=15)
    def verify_vm_list_not_in_vrouter_uve(self, vm_uuid=None, vrouter='localhost', tap=None):
        '''Verifies that vm not in the vrouter uve if the vm is deleted'''

        result = True
        result1 = True
        result2 = True
        if not vm_uuid:
            self.logger.warn("vm_uuid not resceived")
            return False
        collector = self.get_collector_of_gen(
            self.inputs.collector_ips[0], vrouter, 'contrail-vrouter-agent', 'Compute')
        collector_ip=self.inputs.get_host_ip(name=collector)
        self.vrouter_ops_obj = self.ops_inspect[
            collector_ip].get_ops_vrouter(vrouter=vrouter)
        # Verifying vm in vrouter uve
        vrouter_ops_vms = self.vrouter_ops_obj.get_attr(
            'Agent', 'virtual_machine_list', match=vm_uuid)
        if not vrouter_ops_vms:
            result = result and True
            self.logger.debug("VM %s is not present in vrouter %s uve " %
                             (vm_uuid, vrouter))
        else:
            result = result and False
            self.logger.debug("VM %s is still present in vrouter %s uve " %
                              (vm_uuid, vrouter))
        self.logger.debug(
            "Verifying if the vm interface deleted from vroter uve...")
        vm_interface_list = self.vrouter_ops_obj.get_attr(
            'Agent', 'interface_list')
        if vm_interface_list:
            for elem in vm_interface_list:
                if re.search(vm_uuid, elem):
                    self.logger.warn(
                        "%s interface NOT yet deleted from vrouter uve ..." % (elem))
                    result1 = result1 and False
                else:
                    result1 = result1 and True
        else:
            self.logger.debug(
                "interface for vm %s deleted from vrouter uve ..." %
                (vm_uuid))
            result1 = result1 and True
        if result1:
            self.logger.debug(
                "interface for vm %s deleted from vrouter uve ..." %
                (vm_uuid))
            result = result and True
            # Verify that deleted interface not in error interface list
            error_interface_list = self.vrouter_ops_obj.get_attr(
                'Agent', 'error_intf_list')
            if error_interface_list:
                for elem in error_interface_list:
                    if (re.search(vm_uuid, elem)):
                        self.logger.warn(
                            "%s deleted interface in error interface list ..." % (elem))
                        result2 = result2 and False
            else:
                self.logger.debug(
                    "Deleted interface not in error interface list ...")
                result2 = result2 and True

        return result and result1 and result2

    @retry(delay=3, tries=15)
    def verify_vm_list_in_vrouter_uve(self, vm_uuid=None, vn_fq_name=None, vrouter='localhost', tap=None):
        '''Verify that vm exists in the vrouter
        ,also verifies that network, in which vm is connected , gets downloaded in vrouter and tap interface of the vm is created'''
        result = False
        result1 = False
        if not vm_uuid:
            self.logger.debug("vm_uuid not resceived")
            return False
        collector = self.get_collector_of_gen(
            self.inputs.collector_ips[0], vrouter, 'contrail-vrouter-agent', 'Compute')
        collector_ip=self.inputs.get_host_ip(name=collector)
        self.vrouter_ops_obj = self.ops_inspect[
            collector_ip].get_ops_vrouter(vrouter=vrouter)
        # Verifying vm in vrouter uve
        vrouter_ops_vms = self.vrouter_ops_obj.get_attr(
            'Agent', 'virtual_machine_list', match=vm_uuid)
        if not vrouter_ops_vms:
            result = False
            self.logger.error("VM %s is not present in vrouter %s uve " %
                              (vm_uuid, vrouter))
        else:
            result = True
            self.logger.debug("VM %s is present in vrouter %s uve " %
                             (vm_uuid, vrouter))
        # Verifying tap interfaces in vrouter uve
        if tap:
            # disabling for the time beeing.Vrouter tap interface name is
            # chenaged..
            result = True
            vm_tap_intf = self.vrouter_ops_obj.get_attr(
                'Agent', 'interface_list', match=tap)
            if not vm_tap_intf:
                result1 = False
                self.logger.debug(
                    "Tap interface %s of vm %s is not present in vrouter %s uve " %
                    (tap, vm_uuid, vrouter))
            else:
                result1 = True
                self.logger.info(
                    "tap interface %s of vm %s is present in vrouter %s uve " %
                    (tap, vm_uuid, vrouter))
        else:
            result1 = True
        # Verify if network created
        if vn_fq_name:
            result2 = False
            uve_vn = self.vrouter_ops_obj.get_attr(
                'Agent', 'connected_networks', match=vn_fq_name)
            if not uve_vn:
                result2 = False
                self.logger.error(
                    "Connected network %s of vm %s is not present in vrouter %s uve " %
                    (vn_fq_name, vm_uuid, vrouter))
            else:
                result2 = True
                self.logger.debug(
                    "Connected network %s of vm %s is present in vrouter %s uve " %
                    (vn_fq_name, vm_uuid, vrouter))
        else:
            result2 = True
        return (result and result1 and result2)
#        return (result and result2)

    def get_flows_vrouter_uve(self, vrouter='localhost', flowType='active_flows'):
        '''flowType=active_flows,aged_flows,total_flows'''
        collector = self.get_collector_of_gen(
            self.inputs.collector_ips[0], vrouter, 'contrail-vrouter-agent', 'Compute')
        collector_ip = self.inputs.host_data[collector]['host_ip']
        self.vrouter_ops_obj = self.ops_inspect[
            collector_ip].get_ops_vrouter(vrouter=vrouter)
        return self.vrouter_ops_obj.get_attr('Stats', 'flow_rate')['active_flows']

    def get_vrouter_mem_stats(self):
        '''compute uve o/p: {u'nodef1': {u'sys_mem_info': 
        {u'total': 197934164, u'used': 4815188, u'free': 193118976, 
        u'buffers': 155812}, u'num_cpu': 32, u'cpu_share': 0.171875, 
        u'meminfo': {u'virt': 2462240, u'peakvirt': 2525360, 
        u'res': 109032}, 
        u'cpuload': {u'fifteen_min_avg': 0.05, u'five_min_avg': 0.03, 
        u'one_min_avg': 0.06}}}
        return u'virt' as dict with node_name as key
        '''
        all_vr_mem_stats = {}
        for compute_host in self.compute_hosts:
            collector = self.get_collector_of_gen(
                self.inputs.collector_ips[0], compute_host, 'contrail-vrouter-agent', 'Compute')
            collector_ip = self.inputs.host_data[collector]['host_ip']
            self.vrouter_ops_obj = self.ops_inspect[
                collector_ip].get_ops_vrouter(vrouter=compute_host)
            if self.vrouter_ops_obj:
                out = self.vrouter_ops_obj.get_attr('Stats', 'cpu_info')
            else:
                return all_vr_mem_stats
            all_vr_mem_stats[compute_host] = out['meminfo']['virt']
        return all_vr_mem_stats

    def get_vrouter_drop_stats(self):
        '''Get data from vrouter uve drop_stats data..
        sample: drop_stats: {ds_flow_no_memory: 0,ds_flow_queue_limit_exceeded: 55426,...}
        '''
        all_vr_drop_stats = {}
        for compute_host in self.compute_hosts:
            collector = self.get_collector_of_gen(
                self.inputs.collector_ips[0], compute_host, 'contrail-vrouter-agent', 'Compute')
            collector_ip = self.inputs.host_data[collector]['host_ip']
            self.vrouter_ops_obj = self.ops_inspect[
                collector_ip].get_ops_vrouter(vrouter=compute_host)
            out = self.vrouter_ops_obj.get_attr('Stats', 'drop_stats')
            all_vr_drop_stats[compute_host] = out
        return all_vr_drop_stats

    def get_agent_introspect_agentstatsreq(self, agent_ip=None):
        inspect_h = self.agent_inspect[agent_ip]
        return inspect_h.get_vna_pkt_agentstatsreq()

    def get_agent_introspect_fetchallflowrecords(self, agent_ip=None):
        inspect_h = self.agent_inspect[agent_ip]
        return inspect_h.get_vna_fetchallflowrecords()
        # self.records=inspect_h.get_vna_fetchallflowrecords()

    def get_agent_introspect_fetchflowrecords(self, agent_ip=None, vrf=None, sip=None, dip=None, sport=None, dport=None, protocol=None):
        inspect_h = self.agent_inspect[agent_ip]
        return inspect_h.get_vna_fetchflowrecord(vrf=vrf, sip=sip, dip=dip, sport=sport, dport=dport, protocol=protocol)

    def get_agent_introspect_Kflowrecords(self, agent_ip=None):
        #self.agent_inspect= self.connections.agent_inspect
        inspect_h = self.agent_inspect[agent_ip]
        return inspect_h.get_vna_kflowresp()

    def get_vrouter_active_xmpp_peer(self, vrouter=None):
        '''Gets the the active xmpp connection from vrouter uve
       [{u'status': u'true', u'ip': u'10.204.216.14', u'setup_time': 
        u'2013-Jun-25 08:43:46.726649'}, {u'status': u'true', 
        u'ip': u'10.204.216.25', u'primary': u'true', 
        u'setup_time': u'2013-Jun-25 08:43:46.725917'}]
        '''
        collector = self.get_collector_of_gen(
            self.inputs.collector_ips[0], vrouter, 'contrail-vrouter-agent', 'Compute')
        collector_ip = self.inputs.host_data[collector]['host_ip']
        self.vrouter_ops_obj = self.ops_inspect[
            collector_ip].get_ops_vrouter(vrouter=vrouter)
        # self.vrouter_ops_obj=self.ops_inspect.get_ops_vrouter(vrouter=vrouter)
        if not self.vrouter_ops_obj:
            self.logger.critical("%s vrouter uve returned none" % (vrouter))
            return None
        xmpp_peer_list = self.vrouter_ops_obj.get_attr(
            'Agent', 'xmpp_peer_list', match=('primary', True))
        if xmpp_peer_list:
            return xmpp_peer_list[0]['ip']
        else:
            return None

    @retry(delay=5, tries=12)
    def verify_active_xmpp_peer_in_vrouter_uve(self):
        '''Verify active vrouter uve for active xmpp connections

        '''
        result = True
        for agent in self.inputs.compute_names:
            # getting active xmpp peer from vrouter uve
            act_xmpp_uve = self.get_vrouter_active_xmpp_peer(vrouter=agent)
            self.logger.info("Active xmpp peer in %s vrouter uve is %s" %
                             (agent, act_xmpp_uve))
            # self.inputs.host_data['nodea19']['host_ip']
            agent_ip = self.inputs.host_data[agent]['host_ip']
            inspect_h = self.agent_inspect[agent_ip]
            xmpp_peer_from_agent_inspect = inspect_h.get_vna_xmpp_connection_status(
            )
            for elem in xmpp_peer_from_agent_inspect:
                if (elem['cfg_controller'] == 'Yes'):
                    active_xmpp = elem['controller_ip']
                    self.logger.info(
                        "Active xmpp peer in %s agent introspect is %s" %
                        (agent, active_xmpp))
                    if (act_xmpp_uve == active_xmpp):
                        result = result & True
                    else:
                        return False
        return result

    def get_vrouter_interface_list(self, collector, vrouter):
        '''Return the interface list from vrouter uve'''
        self.vrouter_ops_obj = self.ops_inspect[
            collector].get_ops_vrouter(vrouter=vrouter)
        return self.vrouter_ops_obj.get_attr('Agent', 'interface_list')

# end vrouter uve functions
# virtual-network uve functions
# ------------------------#
    def get_vn_uve(self, vn_fq_name):
        '''This function returns entire vn uve.Need this to verify that vn uve does not exists if the vn is deleted'''
        for ip in self.inputs.collector_ips:
            self.opsobj = self.ops_inspect[ip]
            ops_vn = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if ops_vn:
                return ops_vn
        return None

    def verify_vn_uve_tiers(self, vn_fq_name=None):
        '''Verify that when vn is created , vn uve should show info from UveVirtualNetworkConfig and UveVirtualNetworkAgent'''
        result = False
        if not vn_fq_name:
            vn_fq_name='default-domain:%s:default-virtual-network'%self.inputs.stack_tenant
        for ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in  %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.error("%s uve did not return any output " %
                                  vn_fq_name)
                return False
            expected_tiers = ['UveVirtualNetworkAgent',
                              'UveVirtualNetworkConfig']
            tiers = self.ops_vnoutput.keys()
            missing_tier = set(expected_tiers) - set(tiers)
            if not missing_tier:
                self.logger.info(
                    "Tiers correctly shown in vn vue for %s in collector %s" % (vn_fq_name, ip))
                result = True
            else:
                self.logger.error(
                    "uve message did not come from %s for %s in collector %s" %
                    (missing_tier, vn_fq_name, ip))
                return False
        return result

    @retry(delay=5, tries=6)
    def verify_vn_uve_ri(self, vn_fq_name=None, ri_name=None):
        '''Verify  routing instance element when vn  is created by apiserver'''
        result = True
        if not vn_fq_name:
            vn_fq_name='default-domain:%s:default-virtual-network'%self.inputs.stack_tenant
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying through opserver in %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.error("%s uve did not return any output" %
                                  vn_fq_name)
                return False
            ri_list = self.ops_vnoutput.get_attr(
                'Config', 'routing_instance_list')
            if (ri_list == None):
                self.logger.error(
                    "%s uve did not return any routing instance" % vn_fq_name)
                return False

            if not ri_name:
                domain, use, vn_name = vn_fq_name.split(':')
            else:
                vn_name = ri_name
            for elem in ri_list:
                if vn_name in elem:
                    self.logger.info(
                        "routing instance %s correctly showed in  vue for %s" % (vn_fq_name, vn_name))
                    return True
                else:
                    self.logger.error("Routing instance not shown in %s uve" %
                                      (vn_fq_name))
                    result = result and False
        return result

    @retry(delay=5, tries=6)
    def verify_ri_not_in_vn_uve(self, vn_fq_name=None, ri_name=None):
        '''Verify  routing instance element when vn  is created by apiserver'''
        result = True
        if not vn_fq_name:
            vn_fq_name='default-domain:%s:default-virtual-network'%self.inputs.stack_tenant
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying through opserver in %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.error("%s uve did not return any output" %
                                  vn_fq_name)
                return False
            ri_list = self.ops_vnoutput.get_attr(
                'Config', 'routing_instance_list')
            if (ri_list == None):
                self.logger.info("%s uve did not return any routing instance" %
                                 vn_fq_name)
                return True

            if not ri_name:
                domain, use, vn_name = vn_fq_name.split(':')
            else:
                vn_name = ri_name

            for elem in ri_list:
                if vn_name in elem:
                    self.logger.error(
                        "routing instance %s correctly showed in  vue for %s" % (vn_fq_name, vn_name))
                    return False
                else:
                    self.logger.info("Routing instance not shown in %s uve" %
                                     (vn_fq_name))
                    result = result and True
        return result

    @retry(delay=2, tries=30)
    def verify_vn_uve_for_vm_not_in_vn(self, vn_fq_name=None, vm=None):
        '''Verify  vm not in vn uve'''
        result = False
        vm_intf_lst = []
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        if not vm:
            self.logger.debug("vm list name  passed")
            return False
        for ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.warn("%s uve did not return any output" %
                                  vn_fq_name)
                return False
        # Verifying vm list
            vm_uuid_list = self.ops_vnoutput.get_attr(
                'Agent', 'virtualmachine_list', match=vm)
            if not vm_uuid_list:
                self.logger.debug("%s BM not in %s uve " % (vm, vn_fq_name))
                return True
            else:
                self.logger.warn("%s  still in %s uve" %
                                  (vm_uuid_list, vn_fq_name))
                self.logger.error("%s vm still in %s uve" % (vm, vn_fq_name))
                return False
        # Verifying the vm interface deleted in the vn uve
            vm_interface_list = self.ops_vnoutput.get_attr(
                'Agent', 'interface_list')
            if vm_interface_list:
                for elem in vm_interface_list:
                    if (re.search(vm, elem)):
                        self.logger.info("%s vm interface not in %s uve " %
                                         (vm, vn_fq_name))
                        result = result and True
                    else:
                        self.logger.error("%s  interface still in %s uve" %
                                          (elem, vn_fq_name))
                        result = result and False
            else:
                self.logger.info("%s vm interface not in %s uve " %
                                 (vm, vn_fq_name))
                result = result and True
        return result

    @retry(delay=5, tries=10)
    def verify_vn_uve_for_vm(self, vn_fq_name=None, vm=None):
        '''Verify  vm in vn uve'''
        result = False
        vm_intf_lst = []
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        if not vm:
            self.logger.info("vm list name  passed")
            return False
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying through opserver in %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.error("%s uve did not return any output" %
                                  vn_fq_name)
                return False
        # Verifying vm list
            vm_uuid_list = self.ops_vnoutput.get_attr(
                'Agent', 'virtualmachine_list', match=vm)
            if (vm_uuid_list == None):
                self.logger.error("%s uve did not return any output" %
                                  vn_fq_name)
                return False
            else:
                self.logger.debug("expected vm list %s" % (vm))
                self.logger.debug("Extracted vm list %s" % (vm_uuid_list))
                self.logger.info("VM %s is present in %s" % (vm, vn_fq_name))
                return True

    @retry(delay=3, tries=15)
    def verify_vm_list_in_vn_uve(self, vn_fq_name=None, vm_uuid_lst=None):
        '''Verify  vm list for vn uve.'''
        result = True
        vm_intf_lst = []
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        if not vm_uuid_lst:
            self.logger.debug("vm list name  passed")
            return False
        for ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in %s" % (ip))
            self.opsobj = self.ops_inspect[ip]
            self.ops_vnoutput = self.opsobj.get_ops_vn(vn_fq_name=vn_fq_name)
            if not self.ops_vnoutput:
                self.logger.warn("%s uve did not return any output" %
                                  vn_fq_name)
                return False
        # Verifying vm list
            vm_uuid_list = self.ops_vnoutput.get_attr(
                'Agent', 'virtualmachine_list')
            if (vm_uuid_list == None):
                self.logger.warn("%s uve did not return any output" %
                                  vn_fq_name)
                return False
        for uuid in vm_uuid_lst:
            if uuid in vm_uuid_list:
                self.logger.debug("%s vm is present in vn %s" %
                                 (uuid, vn_fq_name))
                result = result and True
            else:
                self.logger.debug("%s vm is NOT present in vn %s" %
                                 (uuid, vn_fq_name))
                result = result and False

        return result

    def get_vn_uve_interface_list(self, collector, vn_fq_name=None):
        '''Returns the list of vm interfaces in the vn'''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        if not vm_uuid:
            self.logger.debug("vm list name  passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        vn_uve_intf_list = self.ops_vnoutput.get_attr(
            'Agent', 'interface_list')
        if vn_uve_intf_list:
            return vn_uve_intf_list
        else:
            self.logger.debug("No interface shown in the vn uve of %s" %
                             (vn_fq_name))
            return None

    def get_vn_uve_vm_interface(self, collector, vn_fq_name=None, vm_uuid=None):
        '''Returns the interface of the vm from vn uve'''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        if not vm_uuid:
            self.logger.debug("vm list name  passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        vn_uve_intf_list = self.ops_vnoutput.get_attr(
            'Agent', 'interface_list')
        result1 = False
        for vm_intf in vn_uve_intf_list:
            vm_uuid_extracted = str(vm_intf).split(':')[:1][0]
            if (vm_uuid == vm_uuid_extracted):
                self.logger.debug(
                    "Interface for vm %s is found in vn uve as %s" %
                    (vm_uuid, vm_intf))
                return vm_intf
        self.logger.debug("Interface for vm %s is not created" % (vm_uuid))
        return None

    def get_vn_uve_vm_list(self, collector, vn_fq_name=None):
        '''Returns the vm list from vn uve'''
        if not vn:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn)
            return False
        vn_uve_vm_list = self.ops_vnoutput.get_attr(
            'Agent', 'virtualmachine_list')
        return vn_uve_vm_list

    def get_vn_uve_attched_policy(self, collector, vn_fq_name=None):
        '''Get attached policy in vn uve

        '''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        self.policy_list = self.ops_vnoutput.get_attr(
            'Config', 'attached_policies')
        if not self.policy_list:
            return None
        self.policy_name_list = []
        for elem in self.policy_list:
            if isinstance(elem, dict):
                self.policy_name_list.append(elem['vnp_name'])
            if isinstance(elem, list):
                self.policy_name_list.append(elem[0][0]['vnp_name'])
        return self.policy_name_list

    def get_vn_uve_num_of_rules_agent(self, collector, vn_fq_name=None):
        '''Get number of rules in  vn uve agent

        '''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        self.num_of_rules = self.ops_vnoutput.get_attr(
            'Agent', 'total_acl_rules')
        return self.num_of_rules

    def get_vn_uve_num_of_rules_config(self, collector, vn_fq_name=None):
        '''Get number of rules in  vn uve-config

        '''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        self.num_of_rules = self.ops_vnoutput.get_attr(
            'Config', 'total_acl_rules')
        return self.num_of_rules

    def get_vn_uve_connected_networks(self, collector, vn_fq_name=None):
        '''Gets connected networks from vn uve when policy is attached
        '''
        res = None
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.error("%s uve did not return any output" % vn_fq_name)
            return False
        try:
            res = self.ops_vnoutput.get_attr('Config', 'connected_networks')
        except Exception as e:
            self.logger.exception(e)
        finally:
            return res

    def get_vn_uve_partially_connected_networks(self, collector, vn_fq_name=None):
        '''Gets partially_connected_networks from vn uve when policy is attached
        '''
        res = None
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        self.ops_vnoutput = self.ops_inspect[
            collector].get_ops_vn(vn_fq_name=vn_fq_name)
        if not self.ops_vnoutput:
            self.logger.warn("%s uve did not return any output" % vn_fq_name)
            return False
        try:
            res = self.ops_vnoutput.get_attr(
                'Config', 'partially_connected_networks')
        except Exception as e:
            self.logger.exception(e)
        finally:
            return res

    def get_inter_vn_stats(self, collector, src_vn, other_vn, direction='out'):
        '''Returns the intervn stats'''

        res = None
        if not src_vn:
            self.logger.debug("vn name not passed")
            return False
        if (direction == 'out'):
            direction = 'out_stats'
        else:
            direction = 'in_stats'
        try:
            self.ops_vnoutput = self.ops_inspect[
                collector].get_ops_vn(vn_fq_name=src_vn)
            if not self.ops_vnoutput:
                self.logger.warn("%s uve did not return any output" % src_vn)
            res = self.ops_vnoutput.get_attr(
                'Agent', direction, match=('other_vn', other_vn))
            if res:
                self.logger.debug("InterVN out stats in %s vn..." % (src_vn))
                self.logger.debug("res = %s" % (res))
                res = res[0]['tpkts']
        except Exception as e:
            self.logger.exception(e)
        finally:
            return res

    def verify_connected_networks_in_vn_uve(self, vn_fq_name, connected_vn_fq_name):
        '''Verify connected networks and partially connected networks in vn uve based on policy
        '''
        if not vn_fq_name:
            self.logger.debug("vn name not passed")
            return False
        result = True
        for ip in self.inputs.collector_ips:
            try:
                c_net = self.get_vn_uve_connected_networks(ip, vn_fq_name)
                if (connected_vn_fq_name in c_net):
                    self.logger.debug(
                        "Connected networks %s present in %s vn uve" %
                        (connected_vn_fq_name, vn_fq_name))
                    result = result & True
                else:
                    result = result & False
                    self.logger.debug("Connected networks %s not in vn uve" %
                                     (connected_vn_fq_name, vn_fq_name))
                pc_net = self.get_vn_uve_partially_connected_networks(
                    ip, vn_fq_name)
                if pc_net:
                    if (connected_vn_fq_name in pc_net):
                        self.logger.warn(
                            "Wrong policy configuration: same vn should not be inconnected networks and partially connected networks")
                        result = result & False
            except Exception as e:
                self.logger.exception(e)
                result = False
        return result

    @retry(delay=3, tries=15)
    def verify_vn_link(self, vn_fq_name):
        '''Verifies that vn is listed in http://nodea18.englab.juniper.net:8081/analytics/virtual-networks when created'''

        # vn='default-domain:'+self.inputs.project_name+':'+vn
        result = False
        for ip in self.inputs.collector_ips:
            self.logger.debug(
                "Verifying the %s virtual network link  through opserver %s" % (vn_fq_name, ip))
            self.links = self.ops_inspect[ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(
                uveType='virtual-networks')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                if name:
                    if (name in vn_fq_name):
                        self.logger.debug("vn link and name as %s" % (elem))
                        result = True
                        break
                    else:
                        result = False
                else:
                    self.logger.debug("VN %s is not found in opserver %s" % (
                        vn_fq_name, ip))
                    return False
        if result:
            self.logger.info('Validated that VN %s is found in opserver' % (
                vn_fq_name))
        return result

    def get_acl(self,collector,vn_fq_name,tier = 'Agent'):
    
        res = None    
        try:
            self.ops_vnoutput = self.ops_inspect[
                collector].get_ops_vn(vn_fq_name = vn_fq_name)
            res = self.ops_vnoutput.get_attr(
                tier , 'total_acl_rules')
        except Exception as e:
            self.logger.exception('Got exception as %s'%(e))
        finally:
            return res 

    @retry_for_value(delay=2, tries=6) 
    def get_bandwidth_usage(self,collector,vn_fq_name,direction = 'out'):
    
        res = None
        direction = '%s_bandwidth_usage'%direction    
        try:
            self.ops_vnoutput = self.ops_inspect[
                collector].get_ops_vn(vn_fq_name = vn_fq_name)
            res = self.ops_vnoutput.get_attr(
                'Agent' , direction)
        except Exception as e:
            self.logger.exception('Got exception as %s'%(e))
        finally:
            return res        

    def get_flow(self,collector,vn_fq_name,direction = 'egress'):
    
        res = None
        direction = '%s_flow_count'%direction    
        try:
            self.ops_vnoutput = self.ops_inspect[
                collector].get_ops_vn(vn_fq_name = vn_fq_name)
            res = self.ops_vnoutput.get_attr(
                'Agent' , direction)
        except Exception as e:
            self.logger.exception('Got exception as %s'%(e))
        finally:
            return res
    
    @retry_for_value(delay=4, tries=10)
    def get_vn_stats(self,collector,vn_fq_name,other_vn ):
    
        res = None
        try:
            self.ops_vnoutput = self.ops_inspect[
                collector].get_ops_vn(vn_fq_name = vn_fq_name)
            res = self.ops_vnoutput.get_attr(
                'Agent' , 'in_stats',match = ('other_vn',\
                                        other_vn))
        except Exception as e:
            self.logger.exception('Got exception as %s'%(e))
        finally:
            return res

    # virtual-machine uve functions
# -------------------------------------#
    def get_vm_uve(self, collector, uuid):
        '''Returns entire vm uve.Need this to verify vm uve does not return anything when vm is deleted'''
        return self.ops_inspect[collector].get_ops_vm(vm=uuid)

    def verify_vm_not_in_opserver(self, uuid, compute, vn_fq_name):
        '''Verify that vm not in opserver after the vm is deleted'''

        assert self.verify_vm_list_not_in_vrouter_uve(
            vrouter=compute, vm_uuid=uuid)
        self.logger.debug('Validated that VM %s is removed in Vrouter UVE' % (
            uuid))

        assert self.verify_vn_uve_for_vm_not_in_vn(
            vn_fq_name=vn_fq_name, vm=uuid)
        self.logger.debug('Validated that VM %s is not present in the VN UVE' %(
            uuid))

        assert self.verify_vm_uve_not_in_opserver(vm=uuid)
        self.logger.info('Validated that VM %s is removed from Opserver' % (
            uuid))


    def get_ops_vm_uve_interface(self, collector, uuid):
        '''Returns: [{u'virtual_network': u'default-domain:admin:vn1', u'ip_address': u'11.1.1.249', u'name': u'111e77ec-c392-4dbf-90bb-d1ab7e0bb476:14bc574b-56fe-4fcb-819b-5f038da34f1a'}] '''

        self.ops_vm_output = self.ops_inspect[collector].get_ops_vm(vm=uuid)
        if not self.ops_vm_output:
            self.logger.warn("vm uve did not return anything")
            return False
        self.vm_intf_dct = self.ops_vm_output.get_attr(
            'Agent', 'interface_list')
        return self.vm_intf_dct

    def get_ops_vm_uve_vm_host(self, collector, uuid):
        '''Retruns vm uve view of vrouter '''

        self.ops_vm_output = self.ops_inspect[collector].get_ops_vm(vm=uuid)
        if not self.ops_vm_output:
            self.logger.warn("vm uve did not return anything")
            return False
        self.uve_vm_host = self.ops_vm_output.get_attr('Agent', 'vrouter')
        return self.uve_vm_host

    def verify_vm_uve_tiers(self, uuid=None):
        '''Verify vm uve tiers as UveVirtualMachineConfig and UveVirtualMachineAgent '''

        result = True
        for ip in self.inputs.collector_ips:
            self.logger.debug("Verifying through opserver in %s" % (ip))
            self.ops_vm_output = self.ops_inspect[ip].get_ops_vm(vm=uuid)
            key_list = self.ops_vm_output.keys()
            # expect_lst=['UveVirtualMachineConfig','UveVirtualMachineAgent']
            expect_lst = ['UveVirtualMachineAgent']
            diff_key = set(expect_lst) ^ set(key_list)
            for uve in expect_lst:
                if uve not in key_list:
                    self.logger.error("%s uve not shown in vm uve %s" %
                                  (uve, uuid))
                    result = result and False
                else:
                    self.logger.debug("%s uve correctly shown in vm uve %s" %
                                 (uve, uuid))
                    result = result and True
        return result

    @retry(delay=4, tries=10)
    def verify_vm_link(self, vm):
        '''Verifies that vm is listed in http://nodea18.englab.juniper.net:8081/analytics/virtual-machines when created'''

        # vn='default-domain:'+self.inputs.project_name+':'+vn
        result = False
        for ip in self.inputs.collector_ips:
            self.logger.debug(
                "Verifying the %s virtual network link  through opserver %s" % (vm, ip))
            self.links = self.ops_inspect[ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(
                uveType='virtual-machines')
            gen_list = []
            for elem in self.links:
                name = elem.get_attr('Name')
                if name:
                    if (name == vm):
                        self.logger.debug("VM link and name as %s" % (elem))
                        result = True
                        break
                    else:
                        result = False
                else:
                    self.logger.warn("not links retuned")
                    return False
        return result

    @retry(delay=4, tries=10)
    def verify_vm_uve_not_in_opserver(self, vm):
        '''Verify that vm uves deleted from opserver on vm delete'''

        result = True
        try:
            for ip in self.inputs.collector_ips:
                self.logger.debug(
                    "Verifying the %s virtual network link  through opserver %s" % (vm, ip))
                links = self.ops_inspect[ip].get_hrefs_to_all_UVEs_of_a_given_UVE_type(
                    uveType='virtual-machines')
                if links:
                    for elem in links:
                        name = elem.get_attr('Name')
                        if name:
                            if (name == vm):
                                self.logger.warn("vm link and name as %s" %
                                                 (elem))
                                self.logger.warn("vm link still in opserver")
                                result = result and False
                                break
                            else:
                                result = result and True
                else:
                    self.logger.debug("No links retuned for %s" % (vm))
                    result = result and True
                if result:
                    self.logger.info("%s vm uve deleted from opserver" % (vm))
                    result = result and True
        except Exception as e:
            self.logger.info("Got exception as %s" % (e))
        finally:
            return result

    def get_intf_uve(self,intf):
        try:
            _intf = self.ops_inspect[self.inputs.collector_ips[0]].get_ops_vm_intf(intf)
            return _intf.get_attr('Agent')  
        except Exception as e:
            return None
  
    def get_vm_attr(self,intf,attr):
        try:
            ops_data = self.get_intf_uve(intf)
            return ops_data[attr]
        except Exception as e:
            return None

# BGP-ROUTER UEE
# -------------------#
    def get_bgp_router_uve_count_xmpp_peer(self, collector):
        '''Get count of xmpp peers from bgp-router uve

        '''
        self.bgp_uve_xmpp_count = []
        for bgp in self.bgp_hosts:
            dct = {}
            self.bgp_ops = self.ops_inspect[
                collector].get_ops_bgprouter(bgprouter=bgp)
            dct[str(bgp)] = str(
                self.bgp_ops.get_attr('Control', 'num_xmpp_peer'))
            self.bgp_uve_xmpp_count.append(dct)
        return self.bgp_uve_xmpp_count

    def get_bgp_router_uve_count_up_xmpp_peer(self, collector, bgp):
        '''Get count of up xmpp peers from bgp-router uve

        '''
        self.bgp_ops = self.ops_inspect[
            collector].get_ops_bgprouter(bgprouter=bgp)
        return str(self.bgp_ops.get_attr('Control', 'num_up_xmpp_peer'))

    def get_bgp_router_uve_count_bgp_peer(self, collector):
        '''Get count of bgp peers from bgp-router uve

        '''
        self.bgp_uve_bgp_count = []
        for bgp in self.bgp_hosts:
            dct = {}
            self.bgp_ops = self.ops_inspect[
                collector].get_ops_bgprouter(bgprouter=bgp)
            dct[str(bgp)] = str(
                self.bgp_ops.get_attr('Control', 'num_bgp_peer'))
            self.bgp_uve_bgp_count.append(dct)
        return self.bgp_uve_bgp_count

    def get_bgp_router_uve_count_up_bgp_peer(self, collector, bgp):
        '''Get count of up bgp peers from bgp-router uve

        '''
        self.bgp_ops = self.ops_inspect[
            collector].get_ops_bgprouter(bgprouter=bgp)
        return str(self.bgp_ops.get_attr('Control', 'num_up_bgp_peer'))

    @retry(delay=4, tries=20)
    def verify_bgp_router_uve_xmpp_and_bgp_count(self):
        '''Verifies the xmpp and bgp peer count in bgp-router uve'''

        result = True
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying through opserver in %s" % (ip))
            count_agents_dct = self.get_bgp_router_uve_count_xmpp_peer(ip)
            total_agent_connections = 0
            count_bgp_nodes_dct = self.get_bgp_router_uve_count_bgp_peer(ip)
            for bgp_host in self.inputs.bgp_names:
                self.logger.debug("Verifying for %s bgp-router uve " %
                                 (bgp_host))
                for elem in count_agents_dct:
                    if bgp_host in elem.keys():
                        total_agent_connections = total_agent_connections + int(elem[bgp_host])

                for elem in count_bgp_nodes_dct:
                    expected_bgp_peers = str(
                        len(self.inputs.bgp_ips) + len(self.inputs.ext_routers) - 1)
                    if bgp_host in elem.keys():
                        if (elem[bgp_host] == expected_bgp_peers):
                            self.logger.info("Bgp peers = %s" %
                                             (elem[bgp_host]))
                            result = result and True
                        else:
                            self.logger.debug("Bgp peers = %s" %
                                             (elem[bgp_host]))
                            self.logger.debug("Expected bgp peers = %s " %
                                             expected_bgp_peers)
                            result = result and False
                        break
            factor = 1
            if len(self.inputs.bgp_names) > 1:
                factor = 2  # Each agent connects to 2 xmpp-servers
            if total_agent_connections  == len(self.inputs.compute_ips)*factor:
                self.logger.info("Total xmpp peer connections found = %s" %(total_agent_connections))
                result = result and True
            else:
                self.logger.info("Total xmpp peer connections found = %s " %(total_agent_connections))
                self.logger.error("Total xmpp peer connections should be = %s " %(len(self.inputs.compute_ips)*factor))
                result = result and False
        return result

    @retry(delay=2, tries=14)
    def verify_bgp_router_uve_up_xmpp_and_bgp_count(self):
        '''Verifies the xmpp and bgp peer count in bgp-router uve'''

        result = True
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying through opserver in %s" % (ip))
            count_agents_dct = self.get_bgp_router_uve_count_xmpp_peer(ip)
            count_bgp_nodes_dct = self.get_bgp_router_uve_count_bgp_peer(ip)
            for bgp_host in self.inputs.bgp_names:
                self.logger.debug("Verifying for %s bgp-router uve " %
                                 (bgp_host))
                for elem in count_agents_dct:
                    if bgp_host in elem.keys():
                        if (elem[bgp_host] >= self.get_bgp_router_uve_count_up_xmpp_peer(ip, bgp_host)):
                            self.logger.debug("xmpp peers = %s" %
                                             (elem[bgp_host]))
                            result = result and True
                        else:
                            self.logger.warn("configured xmpp peers = %s" %
                                             (elem[bgp_host]))
                            self.logger.warn("expected xmpp peers = %s " %
                                             (len(self.inputs.compute_ips)))
                            result = result and False
                        break
                expected_bgp_peers = str(
                    len(self.inputs.bgp_ips) + len(self.inputs.ext_routers) - 1)
                for elem in count_bgp_nodes_dct:
                    if bgp_host in elem.keys():
                        if (elem[bgp_host] >= self.get_bgp_router_uve_count_up_bgp_peer(ip, bgp_host)):
                            self.logger.debug("bgp peers = %s" %
                                             (elem[bgp_host]))
                            result = result and True
                        else:
                            self.logger.debug("configured bgp peers = %s" %
                                             (elem[bgp_host]))
                            self.logger.debug("expected bgp peers = %s " %
                                             expected_bgp_peers)
                            result = result and False
                        break
        return result
# service instance uve functions

    def get_svc_instance(self, collector, project=None, instance=None):
        '''get the svc insance uve our put'''
        if not project:
            project = self.inputs.stack_tenant
        self.svc_obj = self.ops_inspect[
            collector].get_ops_svc_instance(svc_instance=instance)
        return self.svc_obj.get_attr('Config')

    def get_svc_template(self, collector, left_vn=None, right_vn=None):
        '''get the svc insance uve our put'''
        self.svc_obj = self.ops_inspect[collector].get_ops_svc_template(
            left_vn=left_vn, right_vn=right_vn)
        return self.svc_obj.get_attr('Config')

    def get_service_chain_uve(self,collector):    
        sc_obj = self.ops_inspect[collector].get_ops_sc_uve()
        return sc_obj.get_attr('Config')

    def get_specific_service_chain_uve(self,collector,left_vn,
                                        right_vn,
                                        services = [],
                                        protocol = None,
                                        direction = None,
                                        src_port = None,
                                        dst_port = None):
                                        
        sc_uve = self.get_service_chain_uve\
                    (collector)
        for elem in sc_uve:
            if ((elem['value']['UveServiceChainData']['source_virtual_network']\
                         == left_vn) and (elem['value']['UveServiceChainData']['destination_virtual_network']\
                        == right_vn) and (set(elem['value']['UveServiceChainData']['services'])\
                        == set(services))):
                return elem
        return None
        
    def get_service_chain_name(self,left_vn,
                                    right_vn,
                                    services = [],
                                    protocol = None,
                                    direction = None,
                                    src_port = None,
                                    dst_port = None):
        svc_chain = None                                
        svc_chain = self.get_specific_service_chain_uve(self.inputs.collector_ips[0],
                                                left_vn,
                                                right_vn,
                                                services)
        if svc_chain:
            return svc_chain['name']
        else:
            None    
                                    

    def verify_service_chain_uve(self,left_vn,
                                right_vn,
                                services = [],
                                protocol = None,
                                direction = None,
                                src_port = None,
                                dst_port = None):
        if self.get_specific_service_chain_uve(self.inputs.collector_ips[0],
                                                left_vn,
                                                right_vn,
                                                services):                        
            return True
        return False        

    def verify_si_st_uve(self, instance=None, st_name=None, left_vn=None, right_vn=None):

        services_from_st_uve_lst = None
        result = True
        self.si_uve = self.get_svc_instance(
            self.inputs.collector_ips[0], instance=instance)
        if self.si_uve:
            self.logger.debug("Service instance uve shown as %s" %
                             (self.si_uve))
            result = result and True
            if st_name in self.si_uve['st_name']:
                result = result and True
            else:
                self.logger.warn(
                    'Template name not correctly shown in the si uve - should be %s' % (st_name))
        else:
            self.logger.warn("Service instance uve not shown ")
            result = result and False
        # Verifying that internal routing instances, policy,connected_networks
        # in vn uves

        self.st_uve = self.get_svc_template(
            self.inputs.collector_ips[0], left_vn=left_vn, right_vn=right_vn)
        if self.st_uve:
            self.logger.debug("Service template uve shown as %s" %
                             (self.st_uve))
            result = result and True
        else:
            self.logger.warn("Service template uve not shown ")
            result = result and False

        if ((left_vn in self.st_uve['source_virtual_network']) and (right_vn in self.st_uve['destination_virtual_network'])):
            self.logger.debug(
                "left and right vn correctly shown service template uve")
            result = result and True
        else:
            self.logger.debug(
                "left and right vn NOT correctly shown service template uve")
            result = result and False

        services_from_st_uve_lst = self.st_uve['services']
        if services_from_st_uve_lst:
            for elem in services_from_st_uve_lst:
                if (instance in elem):
                    self.logger.debug(
                        "Correct services info shown in the st uve ")
                    result = result and True
                else:
                    self.logger.warn(
                        "Correct services info Not shown in the st uve: %s " % (elem))
                    result = result and True
        if result:
            self.logger.info('Validated SI UVE %s and ST UVE %s' % (instance, st_name))
        else:
            self.logger.error('Validation of SI UVE %s and ST UVE %s failed!' % (
                instance, st_name))
        return result

    def verify_si_uve_not_in_analytics(self, instance=None, st_name=None, left_vn=None, right_vn=None):

        try:
            si_uve = self.get_svc_instance(
                self.inputs.collector_ips[0], instance=instance)
            if si_uve:
                self.logger.info("Service instance uve after deletion %s" %
                             (si_uve))
                return False
            else:
                self.logger.info("Service instance uve deleted") 
        except Exception as e:
            return True

        st_uve = None
        st_uve = self.get_specific_service_chain_uve(
                        self.inputs.collector_ips[0], 
                        left_vn=left_vn, 
                        right_vn=right_vn,
                        services = [instance])
        if st_uve:
            return False
        else:
            return True

    def verify_st_uve_not_in_analytics(self, instance=None, st_name=None, left_vn=None, right_vn=None):

        st_uve = None
        try:
            st_uve = self.get_specific_service_chain_uve(
                        self.inputs.collector_ips[0], 
                        left_vn=left_vn, 
                        right_vn=right_vn,
                        services = [instance])
            if st_uve:
                return False
                self.logger.warn("Service chain NOT deleted from analytics...")
            else:
                return True
                self.logger.debug("Service chain deleted from analytics...")
        except Exception as e:
            self.logger.debug("Service chain deleted from analytics...")
            return True            

# bgp-peer uve functions
    def get_bgp_peers(self, collector):
        '''
            {
            href: "http://nodea18:8081/analytics/uves/bgp-peer/default-domain:default-project:ip-fabric:__default__:nodea19:
            default-domain:default-project:ip-fabric:__default__:nodea18?flat",
            name: "default-domain:default-project:ip-fabric:__default__:nodea19:default-domain:default-project:ip-fabric:__default__:nodea18"
            },
        '''

        peer_tuple = []
        try:
            self.logger.info("Verifying through opserver %s" % (collector))
            self.links = self.ops_inspect[
                collector].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType='bgp-peers')
            for elem in self.links:
                name = elem.get_attr('Name')
                parsed_name = name.split(':')
                bgp_node = parsed_name[4]
                self.logger.debug("bgp-node is %s" % (bgp_node))
                peer = parsed_name[-1]
                self.logger.debug("peer is %s" % (peer))
                touple = (bgp_node, peer)
                peer_tuple.append(touple)
        except Exception as e:
            self.logger.debug(e)
        finally:
            return peer_tuple

    def get_bgp_peer_uve(self, collector, peering_tuple=None):
        '''Return the bgp peer uve'''
        res = None
        try:
            res = self.ops_inspect[collector].get_ops_bgp_peer(peering_tuple)
        except Exception as e:
            self.logger.debug(e)
        finally:
            return res

    def verify_bgp_peers_in_opserver(self, peering_tuple=None):
        '''{
        href: http://10.204.216.25:8081/analytics/uves/bgp-peer/default-domain:default-project:ip-fabric:__default__:10.204.216.14:10.204.216.25?flat,
        name: default-domain:default-project:ip-fabric:__default__:10.204.216.14:10.204.216.25
        },
        {
        href: http://10.204.216.25:8081/analytics/uves/bgp-peer/default-domain:default-project:ip-fabric:__default__:10.204.216.25:10.204.216.14?flat,
        name: default-domain:default-project:ip-fabric:__default__:10.204.216.25:10.204.216.14
        '''

        result = True
        try:
            for ip in self.inputs.collector_ips:
                self.logger.info("Verifying through opserver %s" % (ip))
                self.bgp_peers = self.get_bgp_peers(ip)
                if (peering_tuple in self.bgp_peers):
                    self.logger.debug("Peering uve could be found in opserver")
                    result = result and True
                else:
                    self.logger.debug(
                        "Peering uve could not be found in  opserver")
                    result = result and False
        except Exception as e:
            self.logger.debug(e)
        finally:
            return result

    def get_peer_stats_info_tx_proto_stats(self, collector, peer_toupe=None):
        '''tx_proto_stats: {
            notification: 0,
            update: 33,
            close: 0,
            total: 2794,
            open: 1,
            keepalive: 2760
        '''
        stats = None
        for i in range(20):
            try:
                self.logger.info(
                    "Trying to get the bgp stats from bgp peer uve %s" % (peer_toupe,))
                self.peer_obj = self.ops_inspect[
                    collector].get_ops_bgp_peer(peer_toupe)
                if self.peer_obj:
                    stats = self.peer_obj.get_attr(
                        'Control', 'peer_stats_info')
            except Exception as e:
                self.logger.debug(e)
            finally:
                if stats:
                    return stats['tx_proto_stats']
            time.sleep(5)
        return stats

    def get_peer_stats_info_tx_update_stats(self, collector, peer_toupe=None):
        '''
            tx_update_stats: {
            unreach: 13,
            total: 33,
            reach: 20
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_stats_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats['tx_update_stats']

    def get_peer_stats_info_rx_proto_stats(self, collector, peer_toupe=None):
        '''
            rx_proto_stats: {
            notification: 0,
            update: 33,
            close: 0,
            total: 2795,
            open: 1,
            keepalive: 2761
            },
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_stats_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats['rx_proto_stats']

    def get_peer_stats_info_rx_update_stats(self, collector, peer_toupe=None):
        '''
            rx_update_stats: {
            unreach: 13,
            total: 33,
            reach: 20
            }
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_stats_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats['rx_update_stats']

    def get_peer_state_info(self, collector, peer_toupe=None):
        '''
            state_info: {
            last_state: "OpenConfirm",
            state: "Established",
            last_state_at: 1375774054038293
            },
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'state_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_falp_info(self, collector, peer_toupe=None):
        '''
             flap_info: {
            flap_count: 1,
            flap_time: 1375871293924163
            }


        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'flap_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_families(self, collector, peer_toupe=None):
        '''
             [
            "IPv4:Vpn"
            ],
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'families')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_peer_type(self, collector, peer_toupe=None):
        '''
           peer_type: "internal"

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_type')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_local_asn(self, collector, peer_toupe=None):
        '''
           local_asn: 64512

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'local_asn')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_event_info(self, collector, peer_toupe=None):
        '''
            event_info: {
            last_event_at: 1375856854872047,
            last_event: "fsm::EvBgpKeepalive"
            },
        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'event_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_local_id(self, collector, peer_toupe=None):
        '''
           local_id: 181196825

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'local_id')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_send_state(self, collector, peer_toupe=None):
        '''
           send_state: "in sync"

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'send_state')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_peer_id(self, collector, peer_toupe=None):
        '''
           peer_id: 181196814

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_id')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_peer_peer_asn(self, collector, peer_toupe=None):
        '''
           peer_asn: 64512

        '''
        stats = None
        try:
            self.peer_obj = self.ops_inspect[
                collector].get_ops_bgp_peer(peer_toupe)
            stats = self.peer_obj.get_attr('Control', 'peer_asn')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

# xmpp-peer uve
# ---------------#

    def get_xmpp_peer_state_info(self, collector, peer_toupe=None):
        '''
            state_info: {
            last_state: "Active",
            state: "Established",
            last_state_at: 1375935156613195
        '''
        stats = None
        try:
            self.xmpp_peer_obj = self.ops_inspect[
                collector].get_ops_bgp_xmpp_peer(peer_toupe)
            stats = self.xmpp_peer_obj.get_attr('Control', 'state_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_xmpp_peer_flap_info(self, collector, peer_toupe=None):
        '''
        flap_info: {
        flap_count: 1,
        flap_time: 1375945111699895
        },
        '''
        stats = None
        try:
            self.xmpp_peer_obj = self.ops_inspect[
                collector].get_ops_bgp_xmpp_peer(peer_toupe)
            stats = self.xmpp_peer_obj.get_attr('Control', 'flap_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    def get_xmpp_peer_event_info(self, collector, peer_toupe=None):
        '''
        flap_info: {
        flap_count: 1,
        flap_time: 1375945111699895
        },
        '''
        stats = None
        try:
            self.xmpp_peer_obj = self.ops_inspect[
                collector].get_ops_bgp_xmpp_peer(peer_toupe)
            stats = self.xmpp_peer_obj.get_attr('Control', 'event_info')
        except Exception as e:
            self.logger.debug(e)
        finally:
            return stats

    # Collector uve verification

    def get_analytics_process_details(self, opserver, collector, process=None):

        res = None
        try:
            obj = self.ops_inspect[opserver].get_ops_collector(
                collector=collector)
            res = obj.get_attr('Node', 'process_info',
                               match=('process_name', process))
        except Exception as e:
            self.logger.debug('Got exception as %s' % (e))
        finally:
            return res

    def get_analytics_process_parameters(self, opserver, collector, process_parameters=None, process=None):

        info = self.get_analytics_process_details(
            opserver, collector, process=process)
        if info:
            self.logger.debug("process deatils : %s" % (info))
            return info[0][process_parameters]
        else:
            return None

    @retry(delay=3, tries=30)
    def verify_collector_uve_module_state(self, opserver, collector, process, expected_process_state='RUNNING'):
        '''Verify http://nodea18:8081/analytics/uves/collector/nodea29?flat'''

        result = True
        try:
            info = self.get_analytics_process_details(
                opserver, collector, process=process)
            if info:
                if expected_process_state in info[0]['process_state']:
                    self.logger.debug("%s process is %s" %
                                     (process, expected_process_state))
                    result = result and True
                else:
                    self.logger.warn("%s process is NOT %s" %
                                     (process, expected_process_state))
                    result = result and False
            else:
                self.logger.warn("No output for %s" % (process))
                if 'RUNNING' in expected_process_state:
                    result = result and False
                else:
                    result = result and True

        except Exception as e:
            self.logger.debug("Got exception as %s" % (e))
        finally:
            return result

    # Verifiation of contrail Alarms generation

    def verify_alarms(self, role, alarm_type='process-status', service=None, verify_alarm_cleared=False):
        result = True
        analytics = self.inputs.collector_ips[0]
        underlay = self.inputs.run_cmd_on_server(analytics, 'contrail-status | grep contrail-snmp-collector',
                                                 container='analytics')
        cfgm_processes = ['contrail-config-nodemgr',
            'contrail-device-manager', 'contrail-schema', 'contrail-svc-monitor']
        db_processes = ['contrail-database-nodemgr', 'kafka']
        analytics_processes = ['contrail-query-engine', 'contrail-collector', 'contrail-analytics-nodemgr']
        if underlay:
            analytics_processes.extend(['contrail-snmp-collector', 'contrail-topology'])
        control_processes = ['contrail-control',
            'contrail-control-nodemgr', 'contrail-dns', 'contrail-named']

        try:
            #WA for #1718856 vcenter sanity: Broken by other commits
            if self.inputs.get_build_sku() not in ['kilo', 'liberty', 'mitaka']:
                vrouter_processes = ['contrail-vrouter-agent']
            else:
                vrouter_processes = ['supervisor-vrouter', 'contrail-vrouter-agent']
        except Exception as e:
            vrouter_processes = ['contrail-vrouter-agent']
             
        self.new_ip_addr = '10.1.1.1'

        if role == 'config-node':
            multi_instances = False
            if len(self.inputs.cfgm_ips) > 1:
                multi_instances = True
            if alarm_type == 'process-status':
                for process in cfgm_processes:
                    if process == 'supervisor-config':
                        if len(self.inputs.cfgm_ips) > 1:
                            self.logger.info("Multi cfgms are found, will stop %s on cfgm[0] and check if alarms are generated for the same" %(process))
                        else:
                            self.logger.info("Single cfgm setup found, skipping %s stop alarm test" %(process))
                            continue
                    if not self._verify_contrail_alarms(process, 'config-node', 'service_stop', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Config alarms were generated after stopping the process  %s " % (role))
            elif alarm_type == 'partial-sysinfo-config':
                    if not self._verify_contrail_alarms(None, 'config-node', 'partial_sysinfo_config', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Partial sysinfo config alarm generated %s " % (role))

        elif role == 'database-node':
            multi_instances = False
            if len(self.inputs.database_ips) > 1:
                multi_instances = True
            if alarm_type == 'process-status':
                for process in db_processes:
                    if process == 'kafka' or process == 'supervisor-database':
                        if len(self.inputs.database_ips) > 1:
                            self.logger.info("Multi DBs are found, will stop %s on Db[0] and check if alarms are generated for the same" %(process))
                        else:
                            self.logger.info("Single db setup found, skipping %s stop alarm test" %(process))
                            continue
                    if not self._verify_contrail_alarms(process, 'database-node','service_stop', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Db alarms were generated after stopping the process  %s " % (role))

        elif role == 'control-node':
            multi_instances = False
            if len(self.inputs.bgp_control_ips) > 1:
                multi_instances = True
            if alarm_type == 'process-status':
                for process in control_processes:
                    if not self._verify_contrail_alarms(process, 'control-node', 'service_stop', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Control alarms were generated after stopping the process  %s " % (role))

            elif alarm_type == 'bgp-connectivity':
                if not self._verify_contrail_alarms(None, 'control-node', 'bgp_peer_mismatch', multi_instances=multi_instances):
                    self.logger.error("Control bgp connectivity alarm verification failed for  %s " % (role))
                    result = result and False
                else:
                    self.logger.info("Control bgp connectivity alarm verified for  %s " % (role))

            elif alarm_type == 'address-mismatch-control':
                if not self._verify_contrail_alarms('contrail-control', 'control-node', 'address_mismatch', multi_instances=multi_instances):
                    self.logger.error("Address mismatch control alarm verification failed for  %s " % (role))
                    result = result and False
                else:
                    self.logger.info("Address mismatch control alarm verified for  %s " % (role))

            elif alarm_type == 'process-connectivity':
                if not self._verify_contrail_alarms('contrail-control', 'control-node', 'process_connectivity',
                        multi_instances=multi_instances):
                    self.logger.error("control node process connectivity alarm verification failed for  %s " % (role))
                    result = result and False
                else:
                    self.logger.info("control node process connectivity alarm verified for  %s " % (role))

        elif role == 'analytics-node':
            multi_instances = False
            if len(self.inputs.collector_ips) > 1:
                multi_instances = True
            if alarm_type == 'process-status':
                for process in analytics_processes:
                    if process == 'contrail-collector' or process == 'supervisor-analytics':
                        if len(self.inputs.collector_ips) > 1:
                            multi_instances = True
                            self.logger.info("Multi analytics are found, will stop %s on cfgm[0] and check if alarms are generated for the same" %(process))
                        else:
                            self.logger.info("Single analytics setup found, skipping %s stop alarm test" %(process))
                            continue

                    if not self._verify_contrail_alarms(process, 'analytics-node', 'service_stop', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Analytics alarms were generated after stopping the process  %s " % (role))
            elif alarm_type == 'process-connectivity' and service == 'contrail-alarm-gen':
                if not self._verify_contrail_alarms('contrail-alarm-gen', 'analytics-node', 'process_connectivity',
                        multi_instances=multi_instances):
                    result = result and False

        elif role == 'vrouter':
            multi_instances = False
            if len(self.inputs.compute_ips) > 1:
                multi_instances = True
            if alarm_type == 'process-status':
                for process in vrouter_processes:
                    if not self._verify_contrail_alarms(process, 'vrouter','service_stop', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Vrouter alarms were generated after stopping the process  %s " % (role))
            elif alarm_type == 'address-mismatch-control':
                if not self._verify_contrail_alarms('contrail-vrouter-agent', 'vrouter', 'address_mismatch',
                        multi_instances=multi_instances):
                    result = result and False
                else:
                    self.logger.info("Address mismatch compute alarm verified for  %s " % (role))
            elif alarm_type == 'process-connectivity':
                if not self._verify_contrail_alarms('contrail-vrouter-agent', 'vrouter', 'process_connectivity',
                        multi_instances=multi_instances):
                    result = result and False
                else:
                    self.logger.info("Process connectivity alarm for vrouter verified for  %s " % (role))
            elif alarm_type == 'vrouter-interface':
                if not self._verify_contrail_alarms(None, 'vrouter', 'vrouter_interface',
                        multi_instances=multi_instances, verify_alarm_cleared=verify_alarm_cleared):
                    result = result and False
                else:
                    self.logger.info("Vrouter-interface alarm for vrouter verified for  %s " % (role))
        elif role == 'all':
            multi_instances = False
            if len(self.inputs.cfgm_ips) > 1:
                multi_instances = True
            if alarm_type == 'conf-incorrect':
                if not self._verify_contrail_alarms(None, 'all','conf_incorrect', multi_instances=multi_instances):
                    result = result and False
                else:
                    self.logger.info("Conf incorrect alarms verified  for %s roles" % (role))
            elif alarm_type == 'disk-usage':
                    if not self._verify_contrail_alarms(None, 'all', 'disk_usage', multi_instances=multi_instances):
                        result = result and False
                    else:
                        self.logger.info("Disk usage config alarm generated %s " % (role))
        elif role == 'prouter':
            multi_instances = False
            if len(self.inputs.compute_ips) > 1:
                multi_instances = True
            if alarm_type == 'prouter-connectivity':
                if not self._verify_contrail_alarms(None, 'prouter', 'prouter_connectivity',
                        multi_instances=multi_instances):
                    result = result and False
                else:
                    self.logger.info("prouter connectivity alarm for prouter verified for  %s " % (role))

        return result
    # end verify_alarms

    def _verify_alarms_prouter_connectivity(self, service_ip, role, alarm_type, multi_instances):
        result = True
        self.logger.info("Verify prouter connectivity alarms..")
        if not self._verify_alarms_by_type(None, service_ip, role, alarm_type, multi_instances=False,
                soak_timer=15, verify_alarm_cleared=True):
            result = result and False
        else:
            self.logger.info("Prouter connectivity alarms not seen when system is stable")
        prouter_data = self.inputs.physical_routers_data
        for prouter in prouter_data:
            tor_agents = []
            if prouter_data[prouter]['mgmt_ip'] == service_ip:
                tagents = prouter_data[prouter]['tor_agents']
                for agent in tagents:
                    tor_data = {}
                    tor = agent.split('@')[1].split(':')
                    tor_id = tor[1]
                    tor_ip = tor[0]
                    service = 'contrail-tor-agent-' + tor_id
                    tor_data['service'] = service
                    tor_data['tor_ip'] = tor_ip
                    tor_agents.append(tor_data)
                break
        for tagent in tor_agents:
            self.inputs.stop_service(tagent['service'], host_ips=[tagent['tor_ip']],
                                     container='agent')
        try:
            if not self._verify_alarms_by_type(None, service_ip, role, alarm_type, multi_instances=False,
                    soak_timer=15):
                result = result and False
        except Exception, e:
            self.logger.exception('Exception occured while verifying alarms %s' % (alarm_type))
        finally:
            for tagent in tor_agents:
                self.inputs.start_service(tagent['service'], host_ips=[tagent['tor_ip']],
                                          container='agent')
            time.sleep(15)
            if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances,
                    soak_timer=15, verify_alarm_cleared=True):
                result = result and False

        return result
    # end _verify_contrail_bgp_connectivity_alarm

    def _verify_alarms_bgp_peer_mismatch(self, service_ip, role, alarm_type, multi_instances):
        result = True
        new_ip = self.new_ip_addr
        bgp_router_fixture = PhysicalRouterFixture('test_bgp_connectivity_alarm', self.new_ip_addr)
        super(PhysicalRouterFixture, bgp_router_fixture).setUp()
        self.bgp_router = bgp_router_fixture.create_bgp_router()
        bgp_router_fixture.bgp_router = self.bgp_router
        if not self._verify_alarms_by_type(None, service_ip, role, alarm_type, multi_instances=False, soak_timer=15):
            result = result and False
        bgp_router_fixture.delete_bgp_router()
        super(PhysicalRouterFixture, bgp_router_fixture).delete_device()
        if not self._verify_alarms_by_type(None, service_ip, role, alarm_type, multi_instances=False,
                soak_timer=15, verify_alarm_cleared=True):
            result = result and False
        return result
    # end _verify_contrail_bgp_connectivity_alarm

    def _verify_alarms_vrouter_interface(self, service_ip, role, alarm_type, multi_instances, verify_alarm_cleared):
        result = True
        # To implement
        if not self._verify_alarms_by_type(None, service_ip, role, alarm_type, multi_instances=False,
                soak_timer=15, verify_alarm_cleared=verify_alarm_cleared):
            result = result and False
        return result
    # end _verify_vrouter_interface_alarm

    def update_contrail_conf(self, node, ip, conf_file_type, section, value, cluster_verify=False,
                             container=None):
        file_loc = '/etc/contrail/' + conf_file_type + '.conf'
        self._update_contrail_conf(file_loc, 'set', section,
            value, node, conf_file_type, ip, cluster_verify,
                       container=container)
    # end update_contrail_conf

    def update_contrail_control_conf_file_and_verify_alarms(self, section, value, service_ip, role,
            alarm_type, multi_instances, service=None):
        result = True
        try:
            len_of_bgp_control_ips = len(self.inputs.bgp_control_ips)
            new_host_ip = self.new_ip_addr
            if multi_instances:
                for ip in self.inputs.bgp_control_ips:
                    self.update_contrail_conf(ip, new_host_ip, 'contrail-control', section, value,
                                              container='controller')
            else:
                self.update_contrail_conf(service_ip, new_host_ip, 'contrail-control', section, value,
                                          container='controller')
            self.wait_for_system_stability()
            if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances=False, soak_timer=15):
                result = result and False
        except Exception, e:
            self.logger.exception('Exception occured while verifying alarms %s' % (alarm_type))
            result = result and False
        finally:
            cluster_verify = False
            if multi_instances:
                for ip in self.inputs.bgp_control_ips:
                    if ip == self.inputs.bgp_control_ips[len_of_bgp_control_ips-1]:
                        cluster_verify = False
                    self.update_contrail_conf(ip, ip, 'contrail-control', section, value, cluster_verify=cluster_verify,
                                              container='controller')
            else:
                self.update_contrail_conf(service_ip, service_ip, 'contrail-control', section, value, cluster_verify=False,
                                          container='controller')
            self.wait_for_system_stability()
            if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances=False,
                    soak_timer=15, verify_alarm_cleared=True):
                result = result and False
        return result
    # end update_conf_file_and_verify_alarms

    def update_host_ip_in_contrail_control_conf_and_verify_alarms(self, service_ip, role, alarm_type,
            multi_instances, service=None):
        return self.update_contrail_control_conf_file_and_verify_alarms('DEFAULT', 'hostip', service_ip,
            role, alarm_type, multi_instances, service)

    def update_discovery_server_ip_in_contrail_api_conf_and_verify_alarms(self, service_ip, role,
            alarm_type, multi_instances, service=None):
        return self.update_contrail_api_conf_file_and_verify_alarms('DEFAULTS', 'disc_server_ip', service_ip, role,
            alarm_type, multi_instances, service)

    def update_ifmap_user_in_contrail_control_conf_and_verify_alarms(self, service_ip, role, alarm_type,
            multi_instances, service=None):
        return self.update_contrail_control_conf_file_and_verify_alarms('IFMAP', 'user', service_ip,
            role, alarm_type, multi_instances, service)

    def wait_for_system_stability(self, wait=60):
        time.sleep(wait)

    def update_contrail_api_conf_file_and_verify_alarms(self, section, value, service_ip,
            role, alarm_type, multi_instances, service=None):
        result = True
        try:
            api_service_ip = service_ip
            if isinstance(service_ip, dict):
                api_service_ip = service_ip['config-node']
            new_host_ip = self.new_ip_addr
            len_of_cfgm_ips = len(self.inputs.cfgm_ips)
            if multi_instances:
                for ip in self.inputs.cfgm_ips:
                    self.update_contrail_conf(ip, new_host_ip, 'contrail-api', section, value,
                                              container='controller')
            else:
                self.update_contrail_conf(api_service_ip, new_host_ip, 'contrail-api', section, value,
                                          container='controller')
            self.wait_for_system_stability()
            if role == 'all':
                for role_type in ['analytics-node', 'config-node', 'vrouter', 'database-node', 'control-node']:
                    if not self._verify_alarms_by_type(service, service_ip[role_type],
                            role_type, alarm_type, multi_instances=False, soak_timer=15):
                        result = result and False
            else:
                if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances=False, soak_timer=15):
                    result = result and False
        except Exception, e:
            self.logger.exception('Exception occured while verifying alarms %s' % (alarm_type))
            result = result and False
        finally:
            cluster_verify = False
            if multi_instances:
                for ip in self.inputs.cfgm_ips:
                    if ip == self.inputs.cfgm_ips[len_of_cfgm_ips-1]:
                        cluster_verify = False
                    self.update_contrail_conf(ip, ip, 'contrail-api', section, value, cluster_verify=cluster_verify,
                                              container='controller')
            else:
                self.update_contrail_conf(api_service_ip, api_service_ip, 'contrail-api', section, value, cluster_verify=True,
                                          container='controller')
            self.wait_for_system_stability()
            if role == 'all':
                for role_type in ['analytics-node', 'config-node', 'vrouter', 'database-node', 'control-node']:
                    if not self._verify_alarms_by_type(service, service_ip[role_type], role, alarm_type, multi_instances=False,
                            soak_timer=15, verify_alarm_cleared=True):
                        result = result and False
            else:
                if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances=False,
                        soak_timer=15, verify_alarm_cleared=True):
                    result = result and False
        return result
    # end update_conf_file_and_verify_alarms


    def _verify_alarms_address_mismatch_control(self, service_ip, role, alarm_type, multi_instances):
        result = True
        if not self.update_host_ip_in_contrail_control_conf_and_verify_alarms(service_ip, role,
                alarm_type, multi_instances):
            result = result and False
        return result
    # end _verify_alarms_address_mismatch_control

    def _verify_alarms_disk_usage(self, service_ip, role, alarm_type, multi_instances, container):
        result = True
        if not self.fill_91_disk_usage_and_verify_alarms(service_ip, role,
            alarm_type, multi_instances, container):
            result = result and False
        return result
    # end _verify_alarms_disk_usage


    def fill_91_disk_usage_and_verify_alarms(self, service_ip, role, alarm_type,
                                             multi_instances, container):
        result = True
        is_file_created = {  'config-node':False, 'analytics-node':False,
            'vrouter':False, 'database-node':False, 'control-node':False }
        try:
            for role in is_file_created:
                svc_ip = service_ip[role]
                contnr = container[role]
                hostname = self.inputs.host_data[svc_ip]['name']
                cmd = "df -h /dev/mapper/" + hostname + "--vg-root"
                cmd1 = cmd + " | awk 'NR==2 {print $2}'"
                cmd2 = cmd + " | awk 'NR==2 {print $3}'"
                total = int(self.inputs.run_cmd_on_server(svc_ip, cmd1,
                            container=contnr).split('G')[0])
                used = int(self.inputs.run_cmd_on_server(svc_ip, cmd2,
                           container=contnr).split('G')[0])
                diff = 0
                limit = 0.91 * total
                if not used > limit:
                    diff = limit - used
                mb = int(diff * 1024 + 1)
                str_mb = str(mb) + 'M'
                dd_cmd = 'fallocate -l ' + str_mb + ' large_test_file.txt'
                self.logger.info('Disk usage alarm verification for role %s' % (role))
                if not is_file_created[role]:
                    status = self.inputs.run_cmd_on_server(svc_ip, cmd, container=contnr)
                    self.logger.debug('Printing df -h before file creation: \n %s \n' % (status))
                    if diff:
                        self.logger.info('Creating a file of size %s GB(%s MB) to fill 91 percent of the disk space on %s' %
                            (str(mb/1024), str(mb), role))
                        self.inputs.run_cmd_on_server(svc_ip, dd_cmd, container=contnr)
                    else:
                        self.logger.info('Disk usage is already more than 91 percent, disk usage alarm expected')
                    status = self.inputs.run_cmd_on_server(svc_ip, cmd, container=contnr)
                    self.logger.debug('Printing df -h after file creation: \n %s \n' % (status))
                    self.wait_for_system_stability(wait=10)
                    for node_role in is_file_created:
                        if svc_ip == service_ip[node_role]:
                            is_file_created[node_role] = True
                else:
                   status = self.inputs.run_cmd_on_server(svc_ip, cmd, container=contnr)
                   self.logger.debug('Printing current disk usage: \n\n %s' % (status))
                   self.logger.debug('Large file already created on %s, skipping creation, disk usage is above 91 percent' % (role))
                if not self._verify_alarms_by_type(None, svc_ip, role, alarm_type, multi_instances=False,
                        soak_timer=15):
                    result = result and False
        except Exception, e:
            self.logger.exception('Exception occured while verifying alarms %s' % (alarm_type))
            result = result and False
        finally:
            for role in is_file_created:
                self.logger.info('Verifying disk usage alarm cleared for role %s' % (role))
                svc_ip = service_ip[role]
                self.logger.debug('Deleting large file from %s' % (role))
                status = self.inputs.run_cmd_on_server(svc_ip, 'rm large_test_file.txt')
                if not self._verify_alarms_by_type(None, svc_ip, role, alarm_type, multi_instances=False,
                        soak_timer=15, verify_alarm_cleared=True):
                    result = result and False
        return result
    # end fill_91_disk_usage_and_verify_alarms


    def _verify_alarms_conf_incorrect(self, service_ip, role, alarm_type, multi_instances):
        result = True
        #Alarm gen verification routines need to use different trigger, after discovery removal in R4.0 
        #if not self.update_discovery_server_ip_in_contrail_api_conf_and_verify_alarms(service_ip, role,
        #        alarm_type, multi_instances):
        #    result = result and False
        return result
    # end _verify_alarms_conf_incorrect

    def _verify_alarms_process_connectivity_alarm_gen(self, service_ip, role, alarm_type, multi_instances):
        result = True
        #Alarm gen verification routines need to use different trigger, after discovery removal in R4.0 
        #if not self.update_discovery_server_ip_in_contrail_api_conf_and_verify_alarms(service_ip, role,
        #        alarm_type, multi_instances, service='contrail-alarm-gen'):
        #    result = result and False
        return result
    # end _verify_alarms_process_connectivity_alarm_gen

    def _verify_alarms_process_connectivity_control(self, service_ip, role, alarm_type, multi_instances):
        result = True
        if not self.update_ifmap_user_in_contrail_control_conf_and_verify_alarms(service_ip, role,
                alarm_type, multi_instances, service='contrail-control'):
            result = result and False
        return result

    # end _verify_alarms_process_connectivity_control

    def _verify_alarms_partial_sysinfo_config(self, service_ip, role, alarm_type, multi_instances):
        result = True
        #Alarm gen verification routines need to use different trigger, after discovery removal in R4.0 
        #if not self.update_discovery_server_ip_in_contrail_api_conf_and_verify_alarms(service_ip, role,
        #        alarm_type, multi_instances):
        #    result = result and False
        return result
    # end _verify_alarms_partial_sys_info_config


    def _verify_alarms_process_connectivity_vrouter_agent(self, service_ip, role, alarm_type, multi_instances):
        result = True
        if not self.update_ifmap_user_in_contrail_control_conf_and_verify_alarms(service_ip, role,
                alarm_type, multi_instances, service='contrail-vrouter-agent'):
            result = result and False
        return result
    # end _verify_alarms_process_connectivity_vrouter_agent

    def _update_contrail_conf(self, conf_file, operation, section, knob, node, service, value, cluster_verify,
                              container=None):
        if operation == 'del':
            cmd = 'openstack-config --del %s %s %s' % (conf_file, section, knob)
            xmpp_status = self.inputs.run_cmd_on_server(node, cmd, container=container)
        if operation == 'set':
            cmd = 'openstack-config --set %s %s %s %s' % (conf_file, section, knob, value)
        status = self.inputs.run_cmd_on_server(node, cmd, container=container)
        self.inputs.restart_service(service, [node], container=container)
        if cluster_verify:
            cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
            assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)

    def verify_prouter_connectivity_alarm(self):
        return self.verify_alarms(role='prouter', alarm_type='prouter-connectivity')
    # end verify_prouter_connectivity_alarm

    def verify_vrouter_intf_alarm(self, verify_alarm_cleared=False):
        return self.verify_alarms(role='vrouter', alarm_type='vrouter-interface',
            verify_alarm_cleared=verify_alarm_cleared)
    # end verify_vrouter_intfalarms

    def verify_cfgm_alarms(self):
        return self.verify_alarms(role='config-node')
    # end cfgm_alarms

    def verify_db_alarms(self):
        return self.verify_alarms(role='database-node')
    # end db_alarms

    def verify_control_alarms(self):
        return self.verify_alarms(role='control-node')
    # end control_alarms

    def verify_vrouter_alarms(self):
        return self.verify_alarms(role='vrouter', verify_alarm_cleared=False)
    # end vrouter_alarms

    def verify_analytics_alarms(self):
        return self.verify_alarms( role='analytics-node')
    # end analytics_alarms

    def verify_bgp_connectivity_alarm(self):
        return self.verify_alarms(role='control-node', alarm_type='bgp-connectivity')
    # end verify_bgp_peer_mismatch_alarm

    def verify_address_mismatch_control_alarm(self):
        return self.verify_alarms(role='control-node', alarm_type='address-mismatch-control')
    # end verify_address_mismatch_control_alarm

    def verify_address_mismatch_compute_alarm(self):
        return self.verify_alarms(role='vrouter', alarm_type='address-mismatch-compute')
    # end verify_address_mismatch_compute_alarm

    def verify_process_connectivity_vrouter_agent_alarm(self):
        return self.verify_alarms(role='vrouter', alarm_type='process-connectivity', service='contrail-vrouter-agent')
    # end verify_address_mismatch_compute_alarm

    def verify_process_connectivity_contrail_control_alarm(self):
        return self.verify_alarms(role='control-node', alarm_type='process-connectivity', service='contrail-control')
    # end verify_process_connectivity_control_alarm

    def verify_process_connectivity_contrail_alarm_gen_alarm(self):
        return self.verify_alarms(role='analytics-node', alarm_type='process-connectivity', service='contrail-alarm-gen')
    # end verify_address_mismatch_compute_alarm

    def verify_partial_sysinfo_config_alarm(self):
        return self.verify_alarms(role='config-node', alarm_type='partial-sysinfo-config')
    # end verify_address_mismatch_compute_alarm

    def verify_conf_incorrect_alarm(self):
        return self.verify_alarms(role='all', alarm_type='conf-incorrect')
    # end verify_conf_incorrect_alarm

    def verify_disk_usage_alarm(self):
        return self.verify_alarms(role='all', alarm_type='disk-usage')
    # end verify_disk_usage_alarm

    def verify_configured_alarm(self,role='virtual-network', alarm_type=None, alarm_name=None, verify_alarm_cleared=False):
        service_ip = self.inputs.collector_ips[0]
        return self._verify_alarms_by_type(service=None, service_ip=service_ip,
                    role=role, alarm_type=alarm_type,
                     verify_alarm_cleared=verify_alarm_cleared, built_in=False, alarm_name=alarm_name)
    # end  verify_configured_alarm

    def _verify_alarms_stop_svc(self, service, service_ip, role, alarm_type, multi_instances=False, soak_timer=15,container='controller'):
        result = True
        self.logger.info("Verify alarms generated after stopping the service %s:" % (service))
        dist = self.inputs.get_os_version(service_ip)
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        cfgm_ndmgr_ctl_required = False
        cfgm_services = ['contrail-config-nodemgr', 'contrail-device-manager']
        try:
            if not self.inputs.verify_state():
                self.logger.error( "All the contrail services are not up")
                result = result and False
            if not self.inputs.is_microservices_env and service in cfgm_services and dist in ['centos', 'fedora', 'redhat']:
                supervisorctl_cfg = 'supervisorctl -s unix:///var/run/supervisord_config.sock'
                issue_stop_cmd = supervisorctl_cfg + ' stop ' + service
                issue_start_cmd = supervisorctl_cfg + ' start ' + service
                cfgm_ndmgr_ctl_required = True
                self.inputs.run_cmd_on_server(service_ip, issue_stop_cmd, username, password, pty=True,
                                              container='controller')
            else:
                self.inputs.stop_service(service, host_ips=[service_ip],
                                         container=container)
            self.logger.info("Process %s stopped" % (service))
            if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances, soak_timer):
                result = result and False
        except Exception, e:
            self.logger.exception('Exception occured while verifying alarms %s' % (alarm_type))
            result = result and False
        finally:
            if cfgm_ndmgr_ctl_required:
                self.inputs.run_cmd_on_server(service_ip, issue_start_cmd, username, password, pty=True,
                                              container='controller')
            else:
                self.inputs.start_service(service, host_ips=[service_ip],
                    container=container)
            time.sleep(10)
            if not self.inputs.verify_state():
                self.logger.error( "All the contrail services are not up")
                result = result and False
            if not self._verify_alarms_by_type(service, service_ip, role, alarm_type, multi_instances,
                    soak_timer=soak_timer, verify_alarm_cleared=True):
                result = result and False
        return result

    def _verify_alarms_by_type(self, service, service_ip, role, alarm_type, multi_instances=False,
            soak_timer=15, verify_alarm_cleared=False, built_in=True, alarm_name=None):
        result = True
        soaking = False
        supervisor = False
        if re.search('supervisor', str(service)) or re.search('nodemgr', str(service)):
            supervisor = True
        if 'process-status' in alarm_type and not supervisor:
            soaking = True
        if soaking:
            self.logger.info("Soaking enabled..waiting %s secs for soak timer to expire" % (soak_timer))
            time.sleep(soak_timer)
        MAX_RETRY_COUNT = 60
        SLEEP_DURATION = 1
        retry = 0
        role_alarms = None
        all_alarms = None
        supervisors = [
            'supervisor-analytics',
            'supervisor-control',
            'supervisor-config',
            'supervisor-database',
            'supervisor-vrouter',
            'contrail-database-nodemgr']

        if service in supervisors:
            alarm_type = ['node-status']
        collector_ip = self.inputs.collector_ips[0]
        if multi_instances and role == 'analytics-node':
            collector_ip = self.inputs.collector_ips[1]
        if role == 'prouter':
            prouters_data = self.inputs.physical_routers_data
            for prouter in prouters_data:
                if prouters_data[prouter]['mgmt_ip'] == service_ip:
                    hostname = prouters_data[prouter]['name']
                    break
        elif not built_in:
            hostname = alarm_name
        else:
            hostname = self.inputs.host_data[service_ip]['name']
            hostname = hostname.split('.')[0]
        if not isinstance(alarm_type, list):
            alarm_type = [alarm_type]
        try:
            for alarm_t in alarm_type:
                if not verify_alarm_cleared:
                    while not role_alarms:
                        all_alarms = None
                        role_alarms = None
                        while not all_alarms:
                            all_alarms = self.ops_inspect[collector_ip].get_ops_alarms()
                            if not all_alarms:
                                time.sleep(SLEEP_DURATION)
                                retry = retry + 1
                                if retry % 5 == 0:
                                    self.logger.debug("No alarms found...Iteration  %s " %(retry))
                            if retry > MAX_RETRY_COUNT:
                                self.logger.error("No alarms have been generated")
                                return False
                        role_alarms = self.get_alarms(all_alarms, hostname, role, alarm_t, service=service, built_in=built_in)
                        if not role_alarms:
                            retry = retry + 1
                            time.sleep(SLEEP_DURATION)
                            if retry % 5 == 0:
                                self.logger.debug("Iteration  %s " %(retry))
                        else:
                            time_taken = retry * SLEEP_DURATION
                            # Display warning if time taken to generate is more than 30 secs
                            if time_taken > 30:
                                self.logger.warn("Time taken %s is > 5 secs" %(time_taken))
                            self.logger.info("Time taken to generate the alarms is %s secs" %(time_taken))
                            dup_alarms = None
                            counter = 0
                            while not dup_alarms:
                                dup_alarms = self.get_alarms(all_alarms, hostname, role, alarm_t,
                                    service=service, built_in=built_in, check_duplicate_alarm=True)
                                time.sleep(1)
                                counter = counter + 1
                                if counter > 5:
                                    self.logger.info("Duplicate alarms verifiation passed")
                                    break
                            if dup_alarms:
                                self.logger.error("Duplicate alarms generated: \n%s" % pprint.pprint(dup_alarms))
                                result = result and False

                        if retry > MAX_RETRY_COUNT:
                            self.logger.error("Alarm type %s not generated for role %s" % (
                                alarm_t, role))
                            self.logger.info("Alarms generated in the system are  \n : %s \n" % (pprint.pprint(all_alarms)))
                            result = result and False
                            break
                else:
                    retry = 0
                    all_alarms = self.ops_inspect[collector_ip].get_ops_alarms()
                    if all_alarms:
                        role_alarms = self.get_alarms(all_alarms, hostname, role, alarm_t, service=service, clear=True, built_in=built_in)
                        if not role_alarms:
                            self.logger.info("Alarm type %s cleared for role %s" % (alarm_t, role))
                    else:
                        self.logger.info("All alarms cleared")
                        continue
                    while role_alarms:
                        all_alarms = self.ops_inspect[collector_ip].get_ops_alarms()
                        role_alarms = None
                        if all_alarms:
                            role_alarms = self.get_alarms(all_alarms, hostname, role, alarm_t, service=service, clear=True, built_in=built_in)
                        retry = retry + 1
                        time.sleep(SLEEP_DURATION)
                        if retry % 10 == 0:
                            self.logger.info("Iteration  %s " %(retry))
                        if not role_alarms:
                            time_taken = retry * SLEEP_DURATION
                            self.logger.info("Time taken to clear the alarm is %s secs" %(time_taken))
                        if retry > MAX_RETRY_COUNT:
                            self.logger.error("Alarm type %s not cleared for role %s" % (
                                alarm_t, role))
                            self.logger.info("Alarms present in the system are  \n : %s \n" % (all_alarms))
                            result = result and False
                            break
                if role_alarms:
                    pprint.pprint(role_alarms)
                    pass
                role_alarms = None
        except Exception, e:
            self.logger.exception('Exception occured while checking for alarms')
            result = result and False
        return result
    # end _verify_alarms_by_type

    def _verify_contrail_alarms(self, service, role, trigger='service_stop',
            multi_instances=False, verify_alarm_cleared=False):
        ''' Verify whether contrail alarms is raised
        multi_instances = True for multi node setup based on the role
        '''
        result = True
        if role == 'config-node':
            service_ip = self.inputs.cfgm_ips[0]
            container = 'controller'
        elif role == 'database-node':
            service_ip = self.inputs.database_ips[0]
            container = 'analyticsdb'
        elif role == 'control-node':
            service_ip = self.inputs.bgp_ips[0]
            container = 'controller'
        elif role == 'vrouter':
            service_ip = self.inputs.compute_ips[0]
            container = 'agent'
        elif role == 'analytics-node':
            service_ip = self.inputs.collector_ips[0]
            container = 'analytics'
        elif role == 'prouter':
            tor_tsn_ips = []
            for pdevice in self.inputs.physical_routers_data:
                if self.inputs.physical_routers_data[pdevice].get('tor_agents'):
                    service_ip = self.inputs.physical_routers_data[pdevice]['mgmt_ip']
                    break
        elif role == 'all':
            service_ip = {
                'config-node': self.inputs.cfgm_ips[0],
                'database-node': self.inputs.database_ips[0],
                'control-node': self.inputs.bgp_control_ips[0],
                'vrouter': self.inputs.compute_ips[0],
                'analytics-node': self.inputs.collector_ips[0]}
            container = {
                'config-node' : 'controller',
                'database-node' : 'analyticsdb',
                'control-node' : 'controller',
                'vrouter' : 'agent',
                'analytics-node' : 'analytics',
            }
        elif isinstance(role, list):
            service_ip = {}
            container = {}
            for r in role:
                if r == 'config-node':
                    service_ip['config-node'] = self.inputs.cfgm_ips[0]
                    container['config-node'] = 'controller'
                elif r == 'database-node':
                    service_ip['database-node']  = self.inputs.database_ips[0]
                    container['config-node'] = 'controller'
                elif r == 'control-node':
                    service_ip['control-node'] = self.inputs.bgp_control_ips[0]
                    container['config-node'] = 'controller'
                elif r == 'vrouter':
                    service_ip['vrouter'] = self.inputs.compute_ips[0]
                    container['config-node'] = 'agent'
                elif r == 'analytics-node':
                    service_ip['analytics-node'] = self.inputs.collector_ips[0]
                    container['config-node'] = 'analytics'

        process_connectivity = ['contrail-api', 'contrail-database']
        if service in process_connectivity:
            alarm_type = ['process-connectivity']
        else:
            alarm_type = ['process-status']

        if trigger == 'service_stop':
            if not self._verify_alarms_stop_svc(service, service_ip, role, alarm_type, multi_instances,container=container):
                result = result and False
        elif trigger == 'bgp_peer_mismatch':
            alarm_type = ['bgp-connectivity']
            if not self._verify_alarms_bgp_peer_mismatch(service_ip, role, alarm_type, multi_instances):
                result = result and False
        elif trigger == 'disk_usage':
            alarm_type = 'disk-usage'
            if not self._verify_alarms_disk_usage(service_ip, role, alarm_type, multi_instances, container):
                result = result and False
        elif role == 'control-node':
             if trigger == 'address_mismatch':
                 alarm_type = 'address-mismatch-control'
                 if not self._verify_alarms_address_mismatch_control(service_ip, role, alarm_type, multi_instances):
                     result = result and False
             elif trigger == 'process_connectivity':
                 alarm_type = 'process-connectivity'
                 if not self._verify_alarms_process_connectivity_control(service_ip, role, alarm_type, multi_instances):
                     result = result and False

        # need verification routines for alarms:-
        # process-connectivity on analytics-node
        # incorrect configuration / conf mismatch
        # partial_sysinfo_config on config_node

        elif trigger == 'address_mismatch' and role == 'vrouter':
            alarm_type = 'address-mismatch-compute'
            if not self._verify_alarms_address_mismatch_compute(service_ip, role, alarm_type, multi_instances):
                result = result and False
        elif trigger == 'vrouter_interface' and role == 'vrouter':
            alarm_type = 'vrouter-interface'
            if not self._verify_alarms_vrouter_interface(service_ip, role, alarm_type, multi_instances, verify_alarm_cleared):
                result = result and False
        elif trigger == 'process_connectivity' and role in ['vrouter', 'analytics-node']:
            alarm_type = 'process-connectivity'
            if role == 'vrouter':
                if not self._verify_alarms_process_connectivity_vrouter_agent(service_ip, role, alarm_type, multi_instances):
                    result = result and False
            elif role == 'analytics-node' and service == 'contrail-alarm-gen':
                if not self._verify_alarms_process_connectivity_alarm_gen(service_ip, role, alarm_type, multi_instances):
                    result = result and False
        elif trigger == 'conf_incorrect' and role == 'all':
            alarm_type = 'conf-incorrect'
            if not self._verify_alarms_conf_incorrect(service_ip, role, alarm_type, multi_instances):
                result = result and False
        elif trigger == 'partial_sysinfo_config' and role == 'config-node':
            alarm_type = 'partial-sysinfo-config'
            if not self._verify_alarms_partial_sysinfo_config(service_ip, role, alarm_type, multi_instances):
                result = result and False
        elif trigger == 'prouter_connectivity' and role == 'prouter':
            alarm_type = 'prouter-connectivity'
            if not self._verify_alarms_prouter_connectivity(service_ip, role, alarm_type, multi_instances):
                result = result and False
        else:
            self.logger.error("No valid alarm-type found")
            result = result and False
        return result
    # end _verify_contrail_alarms

    def get_alarms(self, alarms, hostname, role, alarm_type=None, service=None, clear=False,
            built_in=True, check_duplicate_alarm=False):
        '''To return the dict of alarms based on host, service or alarm type
        hostname = host
        role = analytics-node, vrouter, database-node, config-node, control-node
        alarm_type = ProcessStatus, processConnectivity (http://host:8081/analytics/alarm-types)
        service = process_name

        if alarm_type is not set then all alarms for a host will be returned
        otherwise only specific alarms for the host based on alarm_type
        '''

        supervisor = False
        if re.search('supervisor', str(service)) or re.search('nodemgr', str(service)):
            supervisor = True
        if role in alarms:
            role_alarms = alarms[role]
            if not clear and not check_duplicate_alarm:
                self.logger.info("%s alarms generated for %s " % (role, hostname))
        else:
            return None

        fqname = 'default-global-system-config'
        prefix = 'system-defined-'
        inbuild_alarm_type = fqname + ':' + prefix  + alarm_type

        for nalarms in role_alarms:
            if built_in:
                h_name = nalarms['name'].split('.')[0]
                alarm_type = inbuild_alarm_type
            else:
                h_name = nalarms['name']
            if h_name == hostname:
                if not alarm_type and not service:
                    # return all alarms for a host
                    return nalarms
                else:
                    type_alarms_list = nalarms['value']['UVEAlarms']['alarms']
                    #print type_alarms_list
                    if check_duplicate_alarm:
                        duplicate_alarm = self.check_for_duplicate_alarms(type_alarms_list)
                        if duplicate_alarm:
                            return duplicate_alarm
                        return False
                    for type_alarms in type_alarms_list:
                        #print type_alarms['type']
                        if type_alarms['type'] ==  alarm_type:
                            if not clear:
                                self.logger.info("%s alarms generated" % alarm_type)
                            if not service:
                                return type_alarms
                            else:
                                alarm_rules = type_alarms.get('alarm_rules')
                                if not alarm_rules:
                                    self.logger.error("alarm_rules dict missing ")
                                    return False
                                or_list = alarm_rules.get('or_list')
                                if not or_list:
                                    self.logger.error("or_list not found")
                                    return False
                                for any_alarms in or_list:
                                    and_list = any_alarms.get('and_list')
                                    for and_list_elem in and_list:
                                        condition_dict = and_list_elem.get('condition')
                                        match_list = and_list_elem.get('match')
                                        if not supervisor:
                                            json_vars = match_list[0].get('json_variables')
                                        else:
                                            json_vars = None
                                        if json_vars:
                                            process_name = json_vars.get('NodeStatus.process_info.process_name') or \
                                                json_vars.get('NodeStatus.process_status.module_id')
                                        else:
                                            process_name = None
                                        if not supervisor:
                                            if re.search(service, str(process_name)) or service == str(process_name):
                                                if not clear:
                                                    self.logger.info("And list alarms: %s" % (pprint.pprint(and_list_elem)))
                                                return and_list_elem
                                            else:
                                                if not clear:
                                                    self.logger.warn(" 'and_list' %s alarms not generated yet ..wait .checking again" % (service))
                                                return None
                                        else:
                                            self.logger.info("json operands are null for %s " % (service))
                                            print type_alarms
                                            return type_alarms

        if not clear:
            self.logger.warn("Alarm type %s alarms not generated yet ..wait .checking again" % (alarm_type))
        return None
    # end get_alarms

    def check_for_duplicate_alarms(self, alarms):
        if not alarms:
            return None
        or_list = []
        new_or_list = []
        dup_items = []
        for alarm in alarms:
            or_list.append(alarm.get('alarm_rules').get('or_list'))
        for or_item in or_list:
            if or_item not in new_or_list:
               new_or_list.append(or_item)
            else:
               dup_items.append(or_item)
        return dup_items
    # end check_for_duplicate_alarms



# Config-node uve verification

    def get_cfgm_process_details(self, opserver, cfgm_name, process=None, instanceid='0'):

        res = None
        process_name = '%s:%s' % (process, instanceid)\
            if process == 'contrail-api' else process
        try:
            obj = self.ops_inspect[opserver].get_ops_config(config=cfgm_name)
            res = obj.get_attr('Node', 'process_info',
                               match=('process_name', process_name))
            if not res:
                res = obj.get_attr('Node', 'process_info',
                               match=('process_name', process))
        except Exception as e:
            self.logger.debug('Got exception as %s' % (e))
        finally:
            return res

    def get_cfgm_process_parameters(self, opserver, cfgm, process_parameters=None, process=None):

        info = self.get_cfgm_process_details(opserver, cfgm, process=process)
        if info:
            return info[0][process_parameters]
        else:
            return None

    @retry(delay=5, tries=15)
    def verify_cfgm_uve_module_state(self, opserver, cfgm, process):
        '''Verify http://nodea18:8081/analytics/uves/collector/nodea29?flat'''

        result = True
        try:
            info = self.get_cfgm_process_details(
                opserver, cfgm, process=process)
            if info:
                if (info[0]['process_state'] == 'PROCESS_STATE_RUNNING'):
                    self.logger.debug("%s is running" % (process))
                    result = result and True
                else:
                    self.logger.warn("%s is NOT running" % (process))
                    result = result and False
            else:
                self.logger.warn("Not output for %s" % (process))
                result = result and False

        except Exception as e:
            self.logger.debug("Got exception as %s" % (e))
            result = result and False
        finally:
            return result

# Sending query for FlowSreiesTable
# -------------------------------#

    def getstarttime(self, ip=None):
        '''Getting start time from the system when the test is run'''
        return str(OpServerUtils.utc_timestamp_usec())

    def get_time_since_uptime(self, ip=None):

        uptime = self.inputs.run_cmd_on_server(ip, 'cat /proc/uptime',
                                               self.inputs.host_data[
                                                   ip]['username'],
                                               self.inputs.host_data[ip]['password'])
        utime = uptime.split()
        utime = utime[0]
        current_time = self.inputs.run_cmd_on_server(ip, 'date',
                                                     self.inputs.host_data[
                                                         ip]['username'],
                                                     self.inputs.host_data[ip]['password'])
        day, month, date, time, timezone, year = current_time.split()
        month = months[month]
        h, m, sec = time.split(":")
        current_time_utc = datetime.datetime(
            int(year), int(month), int(date), int(h), int(m), int(sec))
        s_time_utc = current_time_utc - \
            datetime.timedelta(seconds=float(utime))
        s_time_str = s_time_utc.strftime('%Y %m %d %H:%M:%S.0')
        s_time_lst = s_time_str.split()
        yr, mn, d, tm = s_time_lst
        mnth = months_number_to_name[mn]
        start_time = '%s %s %s %s' % (yr, mnth, d, tm)
        return start_time

    @retry(delay=2, tries=50)
    def verify_all_uves(self):

        ret = {}
        self.uve_verification_flags = []
        ret = self.get_all_uves()
        if ret:
            result = self.dict_search_for_values(ret)
        for key in exceptions_flags.keys():
            self.uve_verification_flags.append(exceptions_flags[key])
        if 'False' in str(self.uve_verification_flags):
            result = False
        else:
            result = True
        return result

    def get_schema_from_table(self, lst):

        schema = None
        for el in lst:
            if 'schema' in el:
                schema = el['schema']
        return schema

    def get_source_from_table(self, lst):

        source = None
        for el in lst:
            if 'Source' in el:
                source = el['Source']
        return source

    def get_modules_from_table(self, lst):

        modules = None
        for el in lst:
            if 'ModuleId' in el:
                modules = el['ModuleId']
        return modules

    def get_names_from_table(self, lst):

        names = None
        for el in lst:
            if 'name' in el:
                names = el['name']
        return names

    def verify_message_table(self, start_time=None, end_time='now'):

        result = True
        result1 = True
        res2 = None
        ret = None
        objects = None
        query_table_failed = []
        query_table_passed = []
        message_table = None
        table_name = 'MessageTable'
        source = None
        if not start_time:
            self.logger.warn("start_time must be passed...")
            return
        ret = self.get_all_tables(uve='tables')
        tables = self.get_table_schema(ret)
        for elem in tables:
            for k, v in elem.items():
                if table_name in k:
                    schema = self.get_schema_from_table(v)
                    break
        for elem in tables:
            if 'MessageTable' in str(elem):
                message_table = elem
                break
        if message_table:
            mduleid = None
            for k, v in message_table.items():
                for elem in v:
                    if 'Source' in elem.keys():
                        source = elem['Source']
                    if 'ModuleId' in elem.keys():
                        moduleid = elem['ModuleId']

        if source and moduleid:
            for src in source:
                if src in self.inputs.compute_names:
                    if 'contrail-vrouter-agent' in moduleid:
                        query = '(Source=%s AND ModuleId = contrail-vrouter-agent)' % (
                            src)
                        res = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                            sort=2, limit=5, sort_fields=["MessageTS"])
                        for el in res:
                            if 'Source' not in str(el):
                                self.logger.warn(
                                    "Logs from MessageTable not having source \n%" % (str(el)))
                                return False

                if src in self.inputs.collector_names:
                    if 'contrail-collector' in moduleid:
                        query = '(Source=%s AND ModuleId = contrail-collector)' % (src)
                        res = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                            sort=2, limit=5, sort_fields=["MessageTS"])
                        for el in res:
                            if 'Source' not in str(el):
                                self.logger.warn(
                                    "Logs from MessageTable not having source \n%" % (str(el)))
                                return False

                if src in self.inputs.cfgm_names:
                    if 'contrail-api' in moduleid:
                        query = '(Source=%s AND ModuleId = contrail-api)' % (src)
                        res = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                            sort=2, limit=5, sort_fields=["MessageTS"])
                        for el in res:
                            if 'Source' not in str(el):
                                self.logger.warn(
                                    "Logs from MessageTable not having source \n%" % (str(el)))
                                return False
        return True

    def verify_object_tables(self, table_name=None, start_time=None, end_time='now', skip_tables=[]):

        result = True
        result1 = True
        res2 = None
        ret = None
        objects = None
        query_table_failed = []
        query_table_passed = []
        if not start_time:
            self.logger.warn("start_time must be passed...")
            return
        ret = self.get_all_tables(uve='tables')
        tables = self.get_table_schema(ret)

        if table_name:
            for elem in tables:
                for k, v in elem.items():
                    if table_name in k:
                        schema = self.get_schema_from_table(v)
                        break
            #start_time = '2014 FEB 5 14:10:49.0'
            if 'MessageTable' not in table_name:
                objects = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                    table_name,
                    start_time=start_time, end_time=end_time, select_fields=['ObjectId'])
                if not objects:
                    self.logger.warn(
                        "%s table object id could not be retrieved" %
                        (table_name))
                    result = result and False

                else:
                    for obj in objects:
                        query = '(' + 'ObjectId=' + obj['ObjectId'] + ')'
                        try:
                            res2 = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                                table_name,
                                start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                                sort=2, limit=5, sort_fields=["MessageTS"])

                            if not res2:
                                result1 = result1 and False
                                self.logger.warn("query to table %s between %s and Now did not return any value with objectid %s" % (
                                    table_name, start_time, obj))
                            else:
                                result1 = result1 and True
                                self.logger.info(
                                    "%s table contains data with objectid %s" % (table_name, obj))
                        except Exception as e:
                            self.logger.exception(
                                "Got exception as %s \n while querying %s table" % (e, table_name))
            else:
                self.logger.debug("Querying table %s" % (table_name))
                res2 = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                    table_name,
                    start_time=start_time, end_time=end_time, select_fields=schema,
                    sort=2, limit=5, sort_fields=["MessageTS"])
                if not res2:
                    result1 = result1 and False
                    self.logger.warn(
                        "query to table %s between %s and Now did not return any value" %
                        (table_name, start_time))
                else:
                    result1 = result1 and True
                    self.logger.info("Validated that %s table contains data \n%s" %
                                     (table_name, res2))
        else:
            for el1 in tables:
                for k, v in el1.items():
                    table_name = k.split('/')[-1]
                    if table_name not in skip_tables:
                        pass
                        continue

                    if 'MessageTable' in table_name:
                        schema = self.get_schema_from_table(v)
                        self.logger.info("Querying table %s" % (table_name))
                        res2 = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=schema,
                            sort=2, limit=5, sort_fields=["MessageTS"])
                        if not res2:
                            result1 = result1 and False
                            self.logger.warn(
                                "query to table %s between %s and Now did not return any value" % (table_name, start_time))
                            query_table_failed.append(table_name)
                        else:
                            result1 = result1 and True
                            query_table_passed.append(table_name)
                            continue

                    if 'MessageTable' not in table_name:
                        self.logger.debug("Querying for object_id in table %s" %
                                         (table_name))
                        objects = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=['ObjectId'])
                    if not objects:
                        self.logger.warn(
                            "%s table object id could not be retrieved" % (table_name))
                        result = result and False
                        if table_name not in query_table_failed:
                            query_table_failed.append(table_name)
                        continue
                    else:
                        schema = self.get_schema_from_table(v)

                        for obj in objects:
                            query = '(' + 'ObjectId=' + obj['ObjectId'] + ')'
                            try:
                                self.logger.debug(
                                    "Querying  table %s with objectid as %s\n" % (table_name, obj))
                                res2 = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                                    table_name,
                                    start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                                    sort=2, limit=5, sort_fields=["MessageTS"])
                                if not res2:
                                    result1 = result1 and False
                                    self.logger.warn("query to table %s between %s and Now did not return any value with objectid %s" % (
                                        table_name, start_time, obj))
                                    if table_name not in query_table_failed:
                                        query_table_failed.append(table_name)
                                else:
                                    result1 = result1 and True
                                    self.logger.info(
                                        "%s table contains data with objectid %s\n" % (table_name, obj))
                                    if table_name not in query_table_passed:
                                        query_table_passed.append(table_name)
                            except Exception as e:
                                self.logger.warn(
                                    "Got exception as %s \n while querying %s table" % (e, table_name))

            q_failed = query_table_failed[:]
            for item in q_failed:
                if item in query_table_passed:
                    query_table_failed.remove(item)

            if query_table_failed:
                result = False
            else:
                result = True

            self.logger.debug("Query failed for the follwoing tables \n%s" %
                             (query_table_failed))
            self.logger.debug("Query passed for the follwoing tables \n%s" %
                             (query_table_passed))
        return result

    def verify_stats_tables(self, table_name=None, start_time=None, end_time='now', skip_tables=[]):

        result = True
        result1 = True
        res2 = None
        ret = None
        objects = None
        query_table_failed = []
        query_table_passed = []
        if not start_time:
            self.logger.warn("start_time must be passed...")
            return
        ret = self.get_all_tables(uve='tables')
        tables = self.get_table_schema(ret)

        if table_name:
            for elem in tables:
                for k, v in elem.items():
                    if table_name in k:
                        schema = self.get_schema_from_table(v)
                        schema.remove('T=')
                        names = self.get_names_from_table(v)
                        break
            #start_time = '2014 FEB 5 14:10:49.0'
            for name in names:
                query = '(name = %s)' % name
                objects = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                    table_name,
                    start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                    limit=1500000)
                if not objects:
                    self.logger.warn(
                        "%s table could not be retrieved with name %s" %
                        (table_name, name))
                    result = result and False
                else:
                    self.logger.debug(
                        "%s table could  be retrieved with name %s" %
                        (table_name, name))
                    result = result and True

        else:
            for el1 in tables:
                for k, v in el1.items():
                    table_name = k.split('/')[-1]
                    if 'StatTable' not in table_name:
                        continue
                    if table_name not in skip_tables:
                        pass
                        continue
                    else:
                        schema = self.get_schema_from_table(v)
                        schema.remove('T=')
                        names = self.get_names_from_table(v)

                    for name in names:
                        query = '(name = %s)' % name
                        try:
                            self.logger.info(
                                "Querying  table %s with name as %s\n" % (table_name, name))
                            res2 = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                                table_name,
                                start_time=start_time, end_time=end_time, select_fields=schema, where_clause=query,
                                limit=1500000)
                            if not res2:
                                result1 = result1 and False
                                self.logger.warn("query to table %s between %s and Now did not return any value with name %s" % (
                                    table_name, start_time, name))
                                if table_name not in query_table_failed:
                                    query_table_failed.append(table_name)
                            else:
                                result1 = result1 and True
                                self.logger.info(
                                    "%s table contains data with name %s\n" % (table_name, name))
                                if table_name not in query_table_passed:
                                    query_table_passed.append(table_name)
                        except Exception as e:
                            self.logger.warn(
                                "Got exception as %s \n while querying %s table" % (e, table_name))

            q_failed = query_table_failed[:]
            for item in q_failed:
                if item in query_table_passed:
                    query_table_failed.remove(item)

            if query_table_failed:
                result = False
            else:
                result = True

            self.logger.debug("Query failed for the follwoing tables \n%s" %
                             (query_table_failed))
            self.logger.debug("Query passed for the follwoing tables \n%s" %
                             (query_table_passed))
        return result

    def start_query_threads(self, thread_objects=[]):
        for thread in thread_objects:
            thread.start()
            time.sleep(0.5)

    def join_threads(self, thread_objects=[]):
        for thread in thread_objects:
            thread.join(300)

    def get_value_from_query_threads(self):
        while not self.que.empty():
            self.logger.debug("%%%%%%%%%% Verifying results %%%%%%%%%%%%%%%")
            try:
                assert self.que.get()
            except Exception as e:
                self.logger.debug(e)

    def build_parallel_query_to_object_tables(self, table_name=None, start_time=None, end_time='now', skip_tables=[]):

        threads = []
        self.que = Queue.Queue()
        if not start_time:
            self.logger.debug("start_time must be passed...")
            return
        ret = self.get_all_tables(uve='tables')
        tables = self.get_table_schema(ret)
        try:
            for el1 in tables:
                objects = None
                for k, v in el1.items():
                    table_name = k.split('/')[-1]
                    if table_name in skip_tables:
                        pass
                        continue

                    if 'MessageTable' not in table_name:
                        self.logger.debug("Querying for object_id in table %s" %
                                         (table_name))
                        objects = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                            table_name,
                            start_time=start_time, end_time=end_time, select_fields=['ObjectId'])
                    else:
                        continue

                    if not objects:
                        self.logger.warn(
                            "%s table object id could not be retrieved" % (table_name))
                        result = result and False
                    else:
                        schema = self.get_schema_from_table(v)

                        for obj in objects:
                            query = '(' + 'ObjectId=' + obj['ObjectId'] + ')'
                            self.logger.debug(
                                "Querying  table %s with objectid as %s\n" % (table_name, obj))
                            foo = [0, 1]
                            num = random.choice(foo)

                            t = threading.Thread(
                                target=lambda q, table, start_time, end_time, select_fields, where_clause,
                                sort_fields, sort, limit:
                                q.put(self.ops_inspect[self.inputs.collector_ips[num]].post_query(
                                    table, start_time, end_time, select_fields,
                                    where_clause, sort_fields, sort, limit)),
                                args=(
                                    self.que, table_name, start_time,
                                    end_time, schema, query, ["MessageTS"], 2, 5))
                            threads.append(t)

        except Exception as e:
            self.logger.debug(e)
        finally:
            return threads

    def get_table_schema(self, d):

        tables_lst = []
        for k, v in d.items():
            src_key = None
            mod_key = None
            schema_key = None
            name_key = None
            columns = None
            table_dct = {}
            table_schema_dct = {}
            table_src_dct = {}
            table_mod_dct = {}
            table_name_dct = {}
            column_names = []
            schema_key = '%s/schema' % k
            columns = d[k][schema_key]['columns']
            for elem in columns:
                column_names.append(elem['name'])
            table_schema_dct.update({'schema': column_names})
            if not 'Flow' in k:
                column_value_key = '%s/column-values' % k
            else:
                table_dct.update({k: [table_schema_dct]})
                tables_lst.append(table_dct)
                continue

            if column_value_key:
                try:
                    for elem in d[k][column_value_key].keys():
                        if 'Source' in elem:
                            src_key = '%s/Source' % column_value_key
                        if 'ModuleId' in elem:
                            mod_key = '%s/ModuleId' % column_value_key
                        if 'name' in elem:
                            name_key = '%s/name' % column_value_key
                except Exception as e:
                    self.logger.warn("Got exception as %s " % (e))

            if src_key:
                try:
                    table_src_dct.update(
                        {'Source': d[k][column_value_key][src_key]})
                except Exception as e:
                    self.logger.debug("Got exception as %s " % (e))
            if mod_key:
                try:
                    table_mod_dct.update(
                        {'ModuleId': d[k][column_value_key][mod_key]})
                except Exception as e:
                    self.logger.debug("Got exception as %s " % (e))

            if name_key:
                try:
                    table_name_dct.update(
                        {'name': d[k][column_value_key][name_key]})
                except Exception as e:
                    self.logger.debug("Got exception as %s " % (e))
            table_dct.update(
                {k: [table_schema_dct, table_src_dct, table_mod_dct, table_name_dct]})
            tables_lst.append(table_dct)

        return tables_lst

    def get_table_objects(self, d, table):
        pass

    def get_table_module_ids(self, d, table):
        pass

    def dict_search_for_values(self, d, key_list=uve_list, value_dct=uve_dict):

        result = True
        if isinstance(d, dict):
            for k, v in d.items():
                for uve in key_list:
                    if uve in k:
                        self.search_key_in_uve(uve, k, v, value_dct)

                if (v or isinstance(v, int) or isinstance(v, float)):
                    result = self.dict_search_for_values(v)
                else:
                    pass

        elif isinstance(d, list):
            for item in d:
                result = self.dict_search_for_values(item)
        else:
            return result

    def search_key_in_uve(self, uve, k, dct, v_dct):

        if not dct:
            self.uve_verification_flags.append('False')
            self.logger.warn("Empty dict for %s uve" % (k))

        self.logger.debug("Verifying for %s uve" % (uve))
        for elem in v_dct[uve]:
            if elem not in str(dct):
                for key in exceptions.keys():
                    if exceptions[key] in k:
                        exceptions_flags[key] = exceptions_flags[key] or False 
                        continue
                    else: 
                        self.logger.warn("%s not in %s uve" % (elem, k))
                        self.uve_verification_flags.append('False')
            else:
                for key in exceptions.keys():
                    if exceptions[key] in k:
                        exceptions_flags[key] = True 

    def get_all_uves(self, uve=None):
        ret = {}
        try:
            if not uve:
                links = self.ops_inspect[self.inputs.collector_ips[0]
                                         ].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType=uve)
            else:
                links = self.ops_inspect[self.inputs.collector_ips[0]
                                         ].get_hrefs_to_all_UVEs_of_a_given_UVE_type(uveType=uve)
            if links:
                ret = self.search_links(links)
        except Exception as e:
            self.uve_verification_flags.append('False')
            self.logger.debug(e)
        finally:
            return ret

    def get_all_tables(self, uve='tables'):
        ret = {}
        try:
            if not uve:
                links = self.ops_inspect[self.inputs.collector_ips[0]
                                         ].get_hrefs_to_all_tables(uveType=uve)
            else:
                links = self.ops_inspect[self.inputs.collector_ips[0]
                                         ].get_hrefs_to_all_tables(uveType=uve)
            if links:
                ret = self.search_links(links)
        except Exception as e:
            self.uve_verification_flags.append('False')
            self.logger.exception(e)
        finally:
            return ret

    def search_links(self, link, selected_uve=''):
#
        result = True
        links = self.parse_links(link)
        dct = {}
        for ln in links:
            try:
                data = self.ops_inspect[self.inputs.collector_ips[0]].dict_get(url=ln)
                if selected_uve:
                    if selected_uve in ln:
                        return data
                dct.update({ln: self.search_links(data)})
            except Exception as e:
                self.uve_verification_flags.append('False')
                self.logger.debug( 'not an url %s' % ln)
        if dct:
            return dct
        else:
            return link

    def parse_links(self, links=None):

        try:
            if isinstance(links, dict):
                if 'href' in links:
                    yield links['href']
            if isinstance(links, list):
                for elem in links:
                    for item in self.parse_links(elem):
                        yield item
            if isinstance(links, str):
                if 'http://' in links:
                    yield links

        except Exception as e:
            self.logger.exception(e)

    def provision_static_route(
        self, prefix='111.1.0.0/16', virtual_machine_id='',
        tenant_name=None, api_server_ip='127.0.0.1',
        api_server_port='8082', oper='add',
        virtual_machine_interface_ip='11.1.1.252', route_table_name='my_route_table',
            user='admin', password='contrail123'):

        if not tenant_name:
            tenant_name = self.inputs.stack_tenant
        cmd = "python /usr/share/contrail-utils/provision_static_route.py --prefix %s \
                --virtual_machine_id %s \
                --tenant_name %s  \
                --api_server_ip %s \
                --api_server_port %s\
                --oper %s \
                --virtual_machine_interface_ip %s \
                --user %s\
                --password %s\
                --route_table_name %s" % (prefix, virtual_machine_id, tenant_name, api_server_ip, api_server_port, oper,
                                          virtual_machine_interface_ip, user, password, route_table_name)
        args = shlex.split(cmd)
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn("Route could not be created , err : \n %s" %
                             (stderr))
        else:
            self.logger.debug("Provisioning static route, stdout : %s" % (stdout))

    def start_traffic(self, vm, src_min_ip='', src_mx_ip='', dest_ip='', dest_min_port='', dest_max_port=''):

        self.logger.info("Sending traffic...")
        try:
            cmd = 'sudo /home/ubuntu/pktgen_new.sh %s %s %s %s %s &' % (src_min_ip,
                                                                        src_mx_ip, dest_ip, dest_min_port, dest_max_port)
            vm.run_cmd_on_vm(cmds=[cmd])
        except Exception as e:
            self.logger.exception("Got exception at start_traffic as %s" % (e))

    def stop_traffic(self, vm):
        self.logger.info("Stopping traffic...")
        try:
            cmd = 'killall ~/pktgen_new.sh'
            vm.run_cmd_on_vm([cmd])
        except Exception as e:
            self.logger.exception("Got exception at stop_traffic as %s" % (e))

    def build_query(self, src_vn, dst_vn):

        self.query = '(' + 'sourcevn=' + src_vn + \
            ') AND (destvn=' + dst_vn + ')'

    def get_ip_list_from_prefix(self, prefix):

        ip_list = []
        ip = IPNetwork(prefix)
        ip_netowrk = str(ip.network)
        ip_broadcast = str(ip.broadcast)
        ip_lst = list(ip)
        for ip_addr in ip_lst:
            if ((str(ip_addr) in ip_netowrk) or (str(ip_addr) in ip_broadcast)):
                continue
            ip_list.append(str(ip_addr))
        return ip_list

    def get_min_max_ip_from_prefix(self, prefix):

        ip_list = self.get_ip_list_from_prefix(prefix)
        min_ip = ip_list[0]
        max_ip = ip_list[-1]
        return [min_ip, max_ip]

    def build_flow_query(self, src_vn, dst_vn):

        query = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ')'
        return query

    def run_flow_query(self, src_vn, dst_vn):

        result = True

        query = self.build_flow_query(src_vn, dst_vn)
        for ip in self.inputs.collector_ips:
            try:
                self.logger.debug('setup_time= %s' % (self.start_time))
                # Quering flow sreies table
                self.logger.debug(
                    "Verifying flowSeriesTable through opserver %s" % (ip))
                res1 = self.ops_inspect[ip].post_query(
                    'FlowSeriesTable', start_time=self.start_time, 
                    end_time='now', 
                    select_fields=['sourcevn', \
                    'sourceip', 'destvn', \
                    'destip', 'SUM(packets)', \
                    'sport', 'dport', 'T=1'],
                    where_clause=query, sort=2, 
                    limit=5, sort_fields=['SUM(packets)'])
                assert res1
                self.logger.info("Top 5 flows %s" % (res1))
            except Exception as e:
                self.logger.exception("Got exception as %s" % (e))
                result = result and False
        return result

    @retry(delay=5, tries=4)
    def verify_collector_connection_introspect(self,ip,port):
        conn=None
        ops_inspect= VerificationOpsSrvIntrospect(ip,port)
        conn=ops_inspect.get_collector_connectivity()
        try:
           if (conn['status'] =='Established'):
               self.logger.info("IP %s port %s connected to collector %s "%(ip,port,conn['ip']))
               return True
           else:
               self.logger.info("IP %s NOT connected to collector"%(ip))
               return False
        except Exception as e:
           return False

#Common functions
    def verify_process_status(self,obj,module,state = 'Functional'):
        obj1 = None
        try:
            obj1 = obj.get_attr('Node','process_status'
                    ,match = ('module_id',module))

            if (obj1 and isinstance(obj1,list)):
                for elem in obj1:
                    if (elem['state'] == state):
                        return True 
                    else:
                        return False
            elif (obj1 and isinstance(obj1,dict)):            
                if (obj1['state'] == state):
                   return True 
                else:
                   return False
            else:
                self.logger.warn ("No object found for module %s"%(module))
                return False       
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))
            return False  
            
    def verify_connection_infos(self,obj,module,server_addrs,
                                status='Up',
                                t_ype=None,
                                name=None,
                                description=None,
                                node = None): 
        result = True                                                    
        try:
            obj1 = obj.get_attr('Node','process_status'
                    ,match = ('module_id',module))
            if (obj1 and isinstance(obj1,list)):
                for elem in obj1:
                    for el in elem['connection_infos']:
                        check = True
                        if isinstance(server_addrs, list):
                            for s_addr in server_addrs:
                                if not s_addr in el['server_addrs']:
                                    check = check and False
                        else:
                            if not server_addrs in el['server_addrs']:
                                check = check and False
                        #if ((set(el['server_addrs']) == set(server_addrs)) \
                        if ((check or (server_addrs == el['server_addrs']))\
                                    and (el['status'] == status)):
                            self.logger.info("%s:%s module connection to \
                                %s servers UP"%(node,module,str(server_addrs)))
                            return True
                        else:
                            continue
                self.logger.warn("%s:%s module connection to \
                    %s servers NOT UP"%(node,module,str(server_addrs)))
                return False        

            elif (obj1 and isinstance(obj1,dict)):
                for el in obj1['connection_infos']:            
                    if ((set(el['server_addrs']) == set(server_addrs)) \
                                and (el['status'] == status)):
                        self.logger.info("%s module connection to %s \
                                servers UP"%(module,str(server_addrs)))    
                        return True 
                    else:
                        self.logger.warn("%s module connection to %s \
                                servers NOT UP"%(module,str(server_addrs)))    
                        return False
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

    def verify_process_and_connection_infos_agent(self):
        result = True
        port_dict = {'xmpp':'5269',
                     'dns' :'53',
                     'collector':'8086'
                    }
        server_list = []
        for vrouter in self.inputs.compute_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_vrouter(vrouter)
            assert self.verify_process_status(ops_inspect,\
                            'contrail-vrouter-agent')
            xmpp_servers = len(self.inputs.bgp_control_ips)
            count = 0
            for ip in self.inputs.bgp_control_ips:
                server = "%s:%s"%(ip,port_dict['xmpp'])
                if self.verify_connection_infos(ops_inspect,\
                            'contrail-vrouter-agent',\
                            [server],node = vrouter):
                    count = count + 1
                    self.logger.info("%s connected to xmpp %s"%(vrouter, ip))
            if xmpp_servers > 1:
                if not count == 2:
                    result = result and False
                    self.logger.error("%s is not connected to 2 xmpp-servers"%(vrouter))
            else:
               if not count == 1:
                   result = result and False
                   self.logger.error("%s is not connected to any xmpp-server"%(vrouter))
            assert result
            count = 0
            for ip in self.inputs.bgp_control_ips:
                server = "%s:%s"%(ip,port_dict['dns'])
                if self.verify_connection_infos(ops_inspect,\
                            'contrail-vrouter-agent',\
                            [server],node = vrouter):
                    count = count + 1
                    self.logger.info("%s connected to dns %s"%(vrouter, ip))
            if xmpp_servers > 1:
                if not count == 2:
                    result = result and False
                    self.logger.error("%s is not connected to 2 dns servers"%(vrouter))
            else:
               if not count == 1:
                   result = result and False
                   self.logger.error("%s is not connected to any dns-server"%(vrouter))
            assert result
            count = 0
            for ip in self.inputs.collector_control_ips:
                server = "%s:%s"%(ip,port_dict['collector'])
                if self.verify_connection_infos(ops_inspect,\
                                'contrail-vrouter-agent',\
                                [server],node = vrouter):
                    count = count + 1
                    self.logger.info("%s connected to collector %s"%(vrouter, ip))
            if not count > 0:
                self.logger.error("%s is not connected to any collector "%(vrouter))
                result = result and False
            assert result
            return result 

    def verify_process_and_connection_infos_config(self):

        port_dict = {'zookeeper':'2181',
                     'rmq' :'5673',
                     'collector':'8086',
                     'cassandra':'9160',
                     'cfgm_cassandra': '9161',
                     'api':'8082',
                     'ifmap':'8443'
                    }
        module_connection_dict = {'contrail-device-manager':['zookeeper',\
                                                    'rmq',\
                                                    'collector',\
                                                    'cassandra',\
                                                    'api'],\

                                  'contrail-schema':['zookeeper',\
                                                    'collector',\
                                                    'cassandra',\
                                                    'api'],\
                                  'contrail-svc-monitor':['zookeeper',\
                                                    'collector',\
                                                    'cassandra',\
                                                    'api'],\
                                  'contrail-api':['zookeeper',\
                                                    'collector',\
                                                    'cassandra',\
                                                    'api',\
                                                    'ifmap',\
                                                    'rmq'\
                                                    ]
                                 }
        result1 = False
        result_cassandra = False
        for cfgm in self.inputs.cfgm_names:
            result1 = False                                    
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_config(cfgm)
            for k,v in module_connection_dict.items():            
                result1 = result1 or self.verify_process_status(ops_inspect,\
                                            k)
            assert result1
        container_based = False
        cfgm = self.inputs.cfgm_names[0]
        if self.inputs.host_data[cfgm]['containers'].get('config-cassandra'):
            container_based = True
        for cfgm in self.inputs.cfgm_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_config(cfgm)
                        
            result = False    
            for ip in self.inputs.collector_control_ips:
                server = "%s:%s"%(ip,port_dict['collector'])
                result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-api',\
                           server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                server = "%s:%s"%(ip,port_dict['zookeeper'])
                result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-api',\
                            server,node = cfgm)
            assert result   
            result = False
            for ip in self.inputs.cfgm_control_ips:
                if container_based:
                    server = "%s:%s"%(ip,port_dict['cfgm_cassandra'])
                else:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-api',\
                            server,node = cfgm)
            assert result
            result = False    
            for ip in self.inputs.config_amqp_ips:
                server = "%s:%s"%(ip,port_dict['rmq'])
                result = result or self.verify_connection_infos(ops_inspect,\
                                'contrail-api',\
                                server,node = cfgm)
            assert result
             
        for cfgm in self.inputs.cfgm_names:
            result1 = False
            try:
                ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_config(cfgm)
                result1 = result1 or self.verify_process_status(ops_inspect,\
                                            'contrail-device-manager')
                if not result1:
                    raise Exception("No contrail-device-manager found for node %s"%(cfgm))
            except Exception as e:
               continue       
                        
            result = False    
            for ip in self.inputs.collector_control_ips:
               server = "%s:%s"%(ip,port_dict['collector'])
               result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-device-manager',\
                       server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                server = "%s:%s"%(ip,port_dict['zookeeper'])
                result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-device-manager',\
                        server,node = cfgm)
            assert result   
            for ip in self.inputs.cfgm_control_ips:
                if container_based:
                    server = "%s:%s"%(ip,port_dict['cfgm_cassandra'])
                else:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                result_cassandra = result_cassandra or self.verify_connection_infos(ops_inspect,\
                            'contrail-device-manager',\
                            server,node = cfgm)
            result = False    
            for ip in self.inputs.config_amqp_ips:
               server = "%s:%s"%(ip,port_dict['rmq'])
               result = result or self.verify_connection_infos(ops_inspect,\
                                'contrail-device-manager',\
                                server,node = cfgm)
            assert result
        assert result_cassandra,'contrail-device-manager module connection to cfgm_cassandra server not up'
        result_cassandra = False
        for cfgm in self.inputs.cfgm_names:
            result1 = False
            try:
                ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_config(cfgm)
                result1 = result1 or self.verify_process_status(ops_inspect,\
                                            'contrail-schema')
                if not result1:
                    raise Exception("No contrail-schema found for node %s"%(cfgm))
            except Exception as e:
               continue       
                        
            result = False    
            for ip in self.inputs.collector_control_ips:
               server = "%s:%s"%(ip,port_dict['collector'])
               result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-schema',\
                       server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                server = "%s:%s"%(ip,port_dict['zookeeper'])
                result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-schema',\
                        server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                if container_based:
                    server = "%s:%s"%(ip,port_dict['cfgm_cassandra'])
                else:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                result_cassandra = result_cassandra or self.verify_connection_infos(ops_inspect,\
                            'contrail-schema',\
                            server,node = cfgm)
        assert result_cassandra,'contrail-schema module connection to cfgm_cassandra server not up'
        result_cassandra = False
        for cfgm in self.inputs.cfgm_names:
            result1 = False
            try:
                ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_config(cfgm)
                result1 = result1 or self.verify_process_status(ops_inspect,\
                                            'contrail-svc-monitor')
                if not result1:
                    raise Exception("No contrail-svc-monitor found for node %s"%(cfgm))
            except Exception as e:
               continue       
                        
            result = False    
            for ip in self.inputs.collector_control_ips:
               server = "%s:%s"%(ip,port_dict['collector'])
               result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-svc-monitor',\
                       server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                server = "%s:%s"%(ip,port_dict['zookeeper'])
                result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-svc-monitor',\
                        server,node = cfgm)
            assert result   
            result = False    
            for ip in self.inputs.cfgm_control_ips:
                if container_based:
                    server = "%s:%s"%(ip,port_dict['cfgm_cassandra'])
                else:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                result_cassandra = result_cassandra or self.verify_connection_infos(ops_inspect,\
                            'contrail-svc-monitor',\
                            server,node = cfgm)
        assert result_cassandra,'contrail-svc-monitor module connection to cfgm_cassandra server not up'
        return True
    # end verify_process_and_connection_infos_config

    def verify_process_and_connection_infos_control_node(self):

        port_dict = {
                     'cassandra': '9042',
                     'cntl_cassandra': '9041',
                     'rabbitmq': '5673',
                     'collector':'8086'
                    }

        server_list = []            
        container_based = False
        cfgm = self.inputs.cfgm_names[0]
        if self.inputs.host_data[cfgm]['containers'].get('analytics-cassandra'):
            container_based = True
        for bgp in self.inputs.bgp_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_bgprouter(bgp)
            assert self.verify_process_status(ops_inspect,\
                            'contrail-control')
            result = False

            for ip in self.inputs.cfgm_control_ips:
                if container_based:
                    server = "%s:%s"%(ip,port_dict['cntl_cassandra'])
                else:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                result = result or self.verify_connection_infos(ops_inspect,\
                        'contrail-control',\
                        server,node = bgp)
            assert result, 'Control node %s not connected to any cassandra' % (
                            bgp)

            result = False
            for ip in self.inputs.config_amqp_ips:
                server = "%s:%s"%(ip,port_dict['rabbitmq'])
                result = result or self.verify_connection_infos(ops_inspect,\
                                'contrail-control',\
                                server,node = bgp)
            assert result, 'Control node %s not connected to any AMQP' % (
                            bgp)

            result = False    
            for ip in self.inputs.collector_control_ips:
                server = "%s:%s"%(ip,port_dict['collector'])
                result = result or self.verify_connection_infos(ops_inspect,\
                                'contrail-control',\
                                [server],node = bgp)
            assert result    

    def verify_process_and_connection_infos_analytics_node(self):

        port_dict = {
                     'collector':'8086',
                     'cassandra':'9042',
                    }
        module_connection_dict = {'contrail-collector':[
                                                    'collector',\
                                                    'cassandra'\
                                                    ],\

                                  'contrail-analytics-api':[\
                                                    'collector',\
                                                    ],\
                                  'contrail-query-engine':[\
                                                    'collector',\
                                                    'cassandra',\
                                                    ]\
                                                    
                                 }
        for collector in self.inputs.collector_names:
            result1 = True                                    
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_collector(collector)
            for k,v in module_connection_dict.items():
                result1 = result1 and self.verify_process_status(ops_inspect,\
                                            k)
            assert result1        
        for collector in self.inputs.collector_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                        collector_ips[0]].get_ops_collector(collector)
                        
            result = False   
            try: 
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%(ip,port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                           [server],node = collector)
                assert result
            except Exception as e:
               for ip in self.inputs.collector_control_ips:
                   server = "%s:%s"%('127.0.0.1',port_dict['collector'])
                   result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                          [server],node = collector)
               assert result
                      
            result = False
            try:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%(ip,port_dict['redis'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                            [server],node = collector)
                assert result   
            except Exception as e:
               for ip in self.inputs.collector_control_ips:
                   server = "%s:%s"%('127.0.0.1',port_dict['collector'])
                   result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                          [server],node = collector)
               assert result
              
            result = False    
            try:
                for ip in self.inputs.database_control_ips:
                    server = "%s:%s"%(ip,port_dict['cassandra'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                            [server],node = collector)
                assert result
            except Exception as e:
                for ip in self.inputs.database_control_ips:
                    server = "%s:%s"%('127.0.0.1',port_dict['cassandra'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-collector',\
                            [server],node = collector)
                assert result
                
             
        for collector in self.inputs.collector_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                   collector_ips[0]].get_ops_collector(collector)
                        
            result = False
            try:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%(ip,port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-analytics-api',\
                           [server],node = collector)
                assert result
            except Exception as e:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%('127.0.0.1',port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-analytics-api',\
                           [server],node = collector)
                assert result
               
            #To do : Verify Redis connection status once https://bugs.launchpad.net/juniperopenstack/+bug/1459973
            #fixed 
           # try:    
           #     for ip in self.inputs.collector_control_ips:
           #         server = "%s:%s"%(ip,port_dict['redis'])
           #         result = result or self.verify_connection_infos(ops_inspect,\
           #                 'contrail-analytics-api',\
           #                 [server],node = collector)
           #     assert result
           # except Exception as e:    
           #     for ip in self.inputs.collector_control_ips:
           #         server = "%s:%s"%('127.0.0.1',port_dict['redis'])
           #         result = result or self.verify_connection_infos(ops_inspect,\
           #                 'contrail-analytics-api',\
           #                [server],node = collector)
           #     assert result
               
        for collector in self.inputs.collector_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                   collector_ips[0]].get_ops_collector(collector)
                        
            result = False    
            try:
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%(ip,port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-analytics-api',\
                           [server],node = collector)
                assert result 
            except Exception as e:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%('127.0.0.1',port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-analytics-api',\
                           [server],node = collector)
                assert result 
              
            #To do : Verify Redis connection status once https://bugs.launchpad.net/juniperopenstack/+bug/1459973
            #fixed 
            #try:
            #    for ip in self.inputs.collector_control_ips:
            #        server = "%s:%s"%(ip,port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-analytics-api',\
            #                [server],node = collector)
            #    assert result   
            #except Exception as e:    
            #    for ip in self.inputs.collector_control_ips:
            #        server = "%s:%s"%('127.0.0.1',port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-analytics-api',\
            #                [server],node = collector)
            #    assert result   

        for collector in self.inputs.collector_names:
            ops_inspect = self.ops_inspect[self.inputs.\
                   collector_ips[0]].get_ops_collector(collector)
                        
            result = False
            try:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%(ip,port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-query-engine',\
                           [server],node = collector)
                assert result   
            except Exception as e:    
                for ip in self.inputs.collector_control_ips:
                    server = "%s:%s"%('127.0.0.1',port_dict['collector'])
                    result = result or self.verify_connection_infos(ops_inspect,\
                            'contrail-query-engine',\
                           [server],node = collector)
                assert result   
            result = False    
            #To do : Verify Redis connection status once https://bugs.launchpad.net/juniperopenstack/+bug/1459973
            #fixed 
            #try:
            #    for ip in self.inputs.collector_control_ips:
            #        server = "%s:%s"%(ip,port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-query-engine',\
            #                [server],node = collector)
            #    assert result   
            #except Exception as e:    
            #    for ip in self.inputs.collector_control_ips:
            #        server = "%s:%s"%('127.0.0.1',port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-query-engine',\
            #                [server],node = collector)
            #    assert result
            #       
            #result = False
            #try:    
            #    for ip in self.inputs.cfgm_control_ips:
            #        server = "%s:%s"%(ip,port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-query-engine',\
            #                [server],node = collector)
            #    assert result 
            #except Exception as e:    
            #    for ip in self.inputs.cfgm_control_ips:
            #        server = "%s:%s"%('127.0.0.1',port_dict['redis'])
            #        result = result or self.verify_connection_infos(ops_inspect,\
            #                'contrail-query-engine',\
            #                [server],node = collector)
            #    assert result

#Database relaed functions
    def db_purge(self,purge_input):
        resp = None
        try:
            resp = self.ops_inspect[self.inputs.collector_ips[0]].post_db_purge(purge_input)     
        except Exception as e:
            self.logger.error("Got exception as : %s"%(e))
        finally:
            return resp 
            
    def get_purge_id(self,purge_input):
        try:
           resp = self.db_purge(purge_input)
           return resp[0]['purge_id'] 
        except Exception as e:
           return None              
     
    def get_purge_satus(self,resp):
        try:
           resp = self.db_purge(purge_input)
           return resp[0]['status'] 
        except Exception as e:
           return None 
    
    @retry(delay=3, tries=20)
    def verify_database_process_running(self,process):
        self.logger.debug('Verifying if db node_mgr running...')
        result = True
        try:
            for collector in self.inputs.collector_ips:
                for db in self.inputs.database_names:       
                    self.logger.info("Verifying through collector %s for db node %s"%(collector,db))
                    dct = self.ops_inspect[collector].get_ops_db(db)
                    uve = dct.get_attr('Node','process_info',\
                            match = ('process_name', process))
                    if (uve[0]['process_state'] == "PROCESS_STATE_RUNNING"):
                        result = result and True
                    else:
                        result = result and False    
        except Exception as e:
            result = result and False
        finally:
            return result    

    @retry(delay=3, tries=20)
    def verify_database_process_running_status(self,process):
        self.logger.debug('Verifying if db node_mgr is functional...')
        result = True
        try:
            for collector in self.inputs.collector_ips:
                for db in self.inputs.database_names:
                    self.logger.info("Verifying through collector %s for db node %s"%(collector,db))
                    dct = self.ops_inspect[collector].get_ops_db(db)
                    uve = dct.get_attr('Node','process_status',\
                            match = ('module_id', process))
                    if (uve[0]['state'] == "Functional"):
                        result = result and True
                    else:
                        result = result and False
        except Exception as e:
            result = result and False
        finally:
            return result    

    @retry_for_value(delay=3, tries=20)
    def get_purge_info_in_database_uve(self,collector,db):
        dct = self.ops_inspect[collector].get_ops_db(db)
        try:
           uve = dct.get_attr('DatabasePurge','stats')
           return uve
        except Exception as e:
           return None
           
    def get_matched_purge_info(self,collector,db,purge_id):
        try:                      
            dct = self.get_purge_info_in_database_uve(collector,db)
            for elem in dct:
                if (elem['purge_id'] == purge_id):
                        return elem
            return None
        except Exception as e:
            return None        
    
    def get_table(self):    
        stat_table = 'StatTable.DatabasePurgeInfo.stats'
        ret = self.get_all_tables(uve='tables')
        found = False
        tables = self.get_table_schema(ret)
        for elem in tables:
            for k, v in elem.items():
                if stat_table in k:
                    schema = self.get_schema_from_table(v)
                    schema.remove('CLASS(T=)')
                    names = self.get_names_from_table(v)
                    found = True 
                    break
            if found:
               	return stat_table
        return None
           
    #@retry(delay=5, tries=10)
    def verify_purge_info_in_database_uve(self,purge_id,start_time):
        stat_table = self.get_table()
        if stat_table:
            start_time = start_time
            end_time = 'now'
            query = '(stats.purge_id = %s)' % purge_id
            objects = self.ops_inspect[self.inputs.collector_ips[0]].post_query(
                stat_table,
                start_time=start_time, end_time=end_time, select_fields='stats.purge_status', where_clause=query,
                limit=1500000)
        else:
            self.logger.debug("Stat table not found")
               
#    @classmethod
    def setUp(self):
        super(AnalyticsVerification, self).setUp()
        pass
    # end setUpClass

    def cleanUp(self):
        super(AnalyticsVerification, self).cleanUp()
    # end cleanUp

if __name__ == '__main__':

    print 'Need to add'

    # end runTest6
