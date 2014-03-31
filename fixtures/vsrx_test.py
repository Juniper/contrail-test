import fixtures
import re
#from quantumclient.common import exceptions
#from novaclient import exceptions as novaException
from ipam_test import *
from vn_test import *
from util import *
import time
import traceback
from fabric.api import env
from fabric.api import run
from fabric.state import output
from fabric.operations import get, put
from fabric.context_managers import settings, hide
import socket
from contrail_fixtures import *
#from analytics_tests import AnalyticsVerification

env.disable_known_hosts= True
#output.debug= True

#@contrail_fix_ext ()
class vSRXFixture(fixtures.Fixture):
    '''Fixture to handle creation, deletion and verification of the vSRX instance. Also creates the system network and
    project network. Need the project-ID, system network(right nw), project network(left nw), vsrx template name required.
    '''
    def __init__(self, connections, instance_name, vn_fixture, project_name, image_name = 'Juniper vSRX', zone_name = 'default'):
        self.connections = connections
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        #self.ops_inspect = self.connections.ops_inspects
        #self.vnc_lib_h = self.connections.vnc_lib
        self.handler = self.connections.cstack_instance_handle
        self.network_handle = self.connections.cstack_handle
        #self.node_name = node_name
        #self.subnets= subnets
        self.vn_fixture= vn_fixture
        #if vn_obj:
        #    vn_objs=[vn_obj]
        #    self.vn_obj= vn_obj
        #if type(vn_objs) is not list :
        #    self.vn_objs=[vn_objs]
        #else :
        #    self.vn_objs= vn_objs
        self.zone_name = zone_name
        self.project_name = project_name
        self.project_id = self.handler.get_project_id(self.project_name)
        #self.flavor= flavor
        self.image_name= image_name
        self.instance_name= instance_name
        self.vsrxinstance_obj = {}
        self.vm_nics_cs = []
        self.nic_ips = []
        self.routing_instances = []
        self.vm_node_ip = None
        self.control_label = {}
        #self.vm_obj=None
        #self.vm_ip= None
        self.agent_vn_obj= {}
        #self.vn_names= self._get_vn_names( self.vn_objs )
        #self.vn_fq_names= self._get_vn_fq_names( self.vn_objs )
        #if len(vn_objs) == 1 :
        #    self.vn_name= self.vn_names[0]
        #    self.vn_fq_name= self.vn_fq_names[0]
        self.inputs= self.connections.inputs
        self.logger= self.inputs.logger
        self.already_present= False
        self.verify_is_run= False
        #self.analytics_obj=AnalyticsVerification(inputs= self.inputs,connections= self.connections)     
        #self.analytics_obj=self.connections.analytics_obj
        #self.agent_vn_obj= {}
        #self.agent_vrf_obj= {}
        #self.agent_vrf_name = {}
        #self.agent_vrf_id = {}
        #self.agent_path = {}
        #self.tap_intf = {}
        #self.agent_label= {}
        #self.local_ips= {}
        #self.vm_ip_dict={}
        #self.cs_vmi_obj={}
        #self.vm_ips=[]
        #self.project_id= self.vnc_lib_h.fq_name_to_id('project',['default-domain',project_name])
        self.counter = 0
    #end __init__

    def setUp(self):
        super(vSRXFixture, self).setUp()
        self.zoneid = self.handler.get_zone(self.zone_name)
        self.systemnetwork = self.handler.get_system_network('Public') # add this routin to cloudstack_handler.py
        self.offerid = self.handler.create_vsrx_offering()
        self.templateid = self.handler.find_image('Juniper vSRX')
        #need to check for result of vsrxinstance obj to see success..
        self.vsrxinstance_result = self.handler.create_vsrx(self.zoneid, self.project_id, self.instance_name, self.templateid,                                                                            self.offerid, left_network = self.vn_fixture['id'], right_network = self.systemnetwork)
        assert not(self.vsrxinstance_result['queryasyncjobresultresponse']['jobprocstatus']), "Unable to create vSRX instance %s " %( self.instance_name )
        self.vsrxinstance_obj = self.get_vsrx_from_cs()
        self.vm_node_ip= self.inputs.host_data[self.handler.get_host_of_vm(self.vsrxinstance_obj)]['host_ip']
        self.vsrx_id = self.vsrxinstance_obj['id']
    #end setUp

    def verify_on_setup(self):
        #get vsrx status from CS should be active
        self.check_vsrx_state_in_cs()
        #assert check_vsrx_state_in_cs(), "vSRX instance %s is not 'Running' in cloudtsack" %self.instance_name
        self.check_vsrx_nics_in_cs()
        #assert check_vsrx_nics_in_cs(), "all 3 nics not created for vSRX instance %s, check logs" %self.instance_name
        #get vsrx info from api server, only check for service instances as VM verification is done in VM fixture
        self.check_vsrx_ips_in_api_server()  
        #assert check_vsrx_ips_in_api_server(), "verification of vSRX %s ips failed in api server, check logs" %self.instance_name
        self.check_vsrx_si_in_api_server()
        #assert check_vsrx_si_in_api_server(), "verification of vSRX %s failed in api server, check logs" %self.instance_name
        #check vsrx in control node
        self.check_vsrx_in_control_node()
        #assert check_vsrx_in_control_node(), "verification of vSRX %s failed in control node, check logs" %self.instance_name
        self.check_vsrx_in_agent()
        #assert check_vsrx_in_agent(), "verification of vSRX %s failed in one of the agents, check logs" %self.instance_name
        self.verify_is_run = True
    #end verify_on_setup

    def check_vsrx_nics_in_cs(self):
        self.vm_nics_cs = self.get_vsrx_nics() #has all nics from CS (traffictype, network name)
        if len(self.vm_nics_cs) != 3:
            self.logger.error("not all 3 nics are created for vSRX in CS: %s" %self.vm_nics_cs)
            return False
        for nic in self.vm_nics_cs:
            self.nic_ips.append(nic['ipaddress'])
        return True
    #end check_vsrx_nics

    def check_vsrx_in_control_node(self):
        #vn_fqnames = ['default-domain:default-project:__default_Public__', 
        #              'default-domain:' + self.project_name + ':' + self.vn_fixture['name']]
        #RIs = []
        #for vn in vn_fqnames:
        #    RIs.append(vn + ':' + vn.split(':')[-1]) 
        #service_ris = [vn_fqnames[0] + 
        #               ':service-' + 
        #                ('_'.join(vn_fqnames[0].split(':'))) + '-' + 
        #                ('_'.join(vn_fqnames[1].split(':'))) + '-default-domain_' + 
        #                self.project_name + '_' + self.instance_name]
        #service_ris.append(vn_fqnames[1] + 
        #                    ':service-' + 
        #                    ('_'.join(vn_fqnames[1].split(':'))) + '-' + 
        #                    ('_'.join(vn_fqnames[0].split(':'))) + '-default-domain_' +
        #                    self.project_name + '_' + self.instance_name)
        #RIs = RIs + service_ris
        RIs = self.get_ris()
        self.control_label = {}
        for cn in self.inputs.bgp_ips:
            for ri in RIs:
                self.control_label[ri] = {}
                for prefix in self.nic_ips:
                    if self.net_type(prefix) == 'Management':
                        continue
                    routes = self.cn_inspect[cn].get_cn_route_table_entry(ri_name = ri, prefix = prefix + '/32')
                    if not routes:
                        self.logger.error("No route for %s nic found in control node %s" %(prefix, cn))
                        return False
                    if routes[0]['next_hop'] != self.vm_node_ip:
                        self.logger.error( "Next hop for VM %s is not set to %s in Control-node Route table" %(self.vm_name,
                                                                                                          self.vm_node_ip))
                        return False
                    self.control_label[ri][prefix] = routes[0]['label']
        return True
    #end check_vsrx_in_control_node

    def get_ris(self):
        vns = ['default-domain:default-project:__default_Public__',
                      'default-domain:' + self.project_name + ':' + self.vn_fixture['name']]
        for vn in vns:
            self.routing_instances.append(vn + ':' + vn.split(':')[-1])
        service_ris = [vns[0] +
                       ':service-' +
                        ('_'.join(vns[0].split(':'))) + '-' +
                        ('_'.join(vns[1].split(':'))) + '-default-domain_' +
                        self.project_name + '_' + self.instance_name]
        service_ris.append(vns[1] +
                            ':service-' +
                            ('_'.join(vns[1].split(':'))) + '-' +
                            ('_'.join(vns[0].split(':'))) + '-default-domain_' +
                            self.project_name + '_' + self.instance_name)
        self.routing_instances = self.routing_instances + service_ris
        return self.routing_instances
    #end get_ris

    def net_type(self, prefix):
        for nic in self.vm_nics_cs:
            if prefix == nic['ipaddress']:
                return nic['traffictype']
    #end net_type

    def check_vsrx_in_agent(self):
        inspect_h= self.agent_inspect[self.vm_node_ip]
        self.agent_vn_obj[self.vn_fixture['name']]= inspect_h.get_vna_vn('default-domain', self.project_name, self.vn_fixture['name'])
        if not self.agent_vn_obj[self.vn_fixture['name']]:
            self.logger.error('VN %s is not seen in agent %s' %(self.vn_fixture['name'], self.vm_node_ip) )
            return False

        # Check if the VN ID matches between the Orchestration S and Agent
        if self.agent_vn_obj[self.vn_fixture['name']]['uuid'] != self.vn_fixture['id']:
            self.logger.error( "VN UUID %s not created in agent in node %s" %(self.vn_fixture['name'], self.vm_node_ip) )
            return False
        for nic in self.vm_nics_cs:
            if nic['traffictype'] == 'Management':
                continue
            tap_intf = inspect_h.get_vna_tap_interface_by_vmi(vmi_id = nic['id'])[0]
            print tap_intf
            if not tap_intf:
                self.logger.error('tap interface for vsrx nic %s not found in agent' %nic['ipaddress'])
                return False
            if tap_intf['label'] != self.control_label[tap_intf['vrf_name']][nic['ipaddress']]:
                self.logger.error("labels in control node and agent do not match for nic ip %s: label in CN is %s, label in agent is %s" 
                                   %(nic['ipaddress'], self.control_label[tap_intf['vrf_name']][nic['ipaddress']], tap_intf['label']))
                return False
        vrfs_agent = inspect_h.get_vna_vrf_objs(project=self.project_name, vn_name=self.vn_fixture['name'])
        vrfs_agent1 = inspect_h.get_vna_vrf_objs(project='default-project', vn_name='__default_Public__')
        vrfs_agent['vrf_list'] = vrfs_agent['vrf_list'] + vrfs_agent1['vrf_list']
        print vrfs_agent
        for inst in vrfs_agent['vrf_list']:
            if not inst['name'] in self.routing_instances:
                self.logger.error('routing instance %s is not there in agent!' %inst['name'])
                return False
            for ip in self.nic_ips:
                if self.net_type(ip) == 'Management':
                    continue   
                route = inspect_h.get_vna_active_route(vrf_id=inst['ucindex'], ip = ip, prefix = '32')
                if not route:
                    self.logger.error('no route for %s in agent' %ip)
                    return False
        return True
    #end check_vsrx_in_agent

    def get_vsrx_nics(self):
        nics = self.vsrxinstance_obj['nic']
        return nics
    #end get_vsrx_nics

    def check_vsrx_si_in_api_server(self):
        self.SI_policy = self.api_s_inspect.get_si_policy() #TBD check policy in api server
        print self.SI_policy
        self.SI_inspect = self.api_s_inspect.get_service_instances()
        for SI in self.SI_inspect['service-instances']:
            if set([self.project_name, self.instance_name]).issubset(SI['fq_name']):
                self.SI_href = SI['href']
                self.SI_uuid = SI['uuid']
                return True
            #if self.instance_name not in SI['fq_name']:
            #    continue
            #if self.project_name not in SI['fq_name']:
            #    continue
            #self.SI_href = SI['href']
            #self.SI_uuid = SI['uuid'] 
        self.logger.error("vSRX instance %s not found in API server service instance obj %s" 
                                                      %s(self.instance_name, self.SI_inspect_api))
        return False
    #check_vsrx_si_in_api_server
        
    def check_vsrx_ips_in_api_server(self):
        vsrx_ips = self.api_s_inspect.get_cs_instance_ips_of_vm(self.vsrx_id)
        for vsrx_ip in vsrx_ips:
            if vsrx_ip['instance-ip']['instance_ip_address'] not in self.nic_ips:
                self.logger.error("vsrx ip address %s not found in API server" %(vsrx_ip['instance-ip']['instance_ip_address']))
                return False
        return True    
    #end check_vsrx_ips_in_api_server

    def check_vsrx_state_in_cs(self):
        instance_obj = self.get_vsrx_from_cs()
        if instance_obj['state'] != 'Running':
            return False
        else:
            return True
    #end check_vsrx_state_in_cs

    def get_vsrx_from_cs(self):
        vsrxinstance_resp = self.handler.list_vm_in_cs(self.project_id, self.instance_name)
        if not vsrxinstance_resp['listvirtualmachinesresponse']:
            return None
        else:
            return vsrxinstance_resp['listvirtualmachinesresponse']['virtualmachine'][0]
    #end get_vsrx_from_cs

    @retry(delay=8, tries=6)
    def check_vsrx_not_in_cs(self):
        if self.get_vsrx_from_cs():
            self.logger.warn("vsrx instance still seen in CS")
            result = False
        else: 
            self.logger.info("vsrx instance removed from CS")
            result = True
        return result
    #end check_vsrx_not_in_cs

    @retry(delay=5, tries=6)
    def check_vsrx_si_not_in_api_server(self):
        import pdb; pdb.set_trace()
        self.counter += 1
        si_inspect = self.api_s_inspect.get_service_instances()
        print si_inspect
        for SI in si_inspect['service-instances']:
            if set([self.instance_name, self.project_name]).issubset(SI['fq_name']):
                self.logger.warn("vsrx service instance not removed from api server - tried %s times" %self.counter)
                return False
        self.logger.info("vsrx service instance removed from api server")
        return True
    #end check_vsrx_si_not_in_api_server
    
    def check_vsrx_not_in_api_server(self):
        vsrx_inst = self.api_s_inspect.get_cs_vm(self.vsrx_id, refresh = True)
        if vsrx_inst:
            return False
        return True
    #end check_vsrx_not_in_api_server

    def check_vsrx_not_in_agent(self):
        inspect_h= self.agent_inspect[self.vm_node_ip]
        vn_obj[self.vn_fixture['name']] = inspect_h.get_vna_vn('default-domain', self.project_name, self.vn_fixture['name'])
        if vn_obj[self.vn_fixture['name']]:
            self.logger.error('VN %s is seen in agent %s' %(self.vn_fixture['name'], self.vm_node_ip) )
            return False
        for nic in self.vm_nics_cs:
            if nic['traffictype'] == 'Management':
                continue
            tap_intf = inspect_h.get_vna_tap_interface_by_vmi(vmi_id = nic['id'])[0]
            if tap_intf:
                self.logger.error('tap interface for vsrx nic %s found in agent' %nic['ipaddress'])
                return False
        vrfs_agent = inspect_h.get_vna_vrf_objs(project=self.project_name, vn_name=self.vn_fixture['name'])
        vrfs_agent1 = inspect_h.get_vna_vrf_objs(project='default-project', vn_name='__default_Public__')
        vrfs_agent['vrf_list'] = vrfs_agent['vrf_list'] + vrfs_agent1['vrf_list']
        print vrfs_agent
        for inst in vrfs_agent['vrf_list']:
            if self.vn_fixture['name'] in inst:
                self.logger.error('routing instance %s is seen in agent!, vrfs list is %s' %(inst['name'], vrfs_agent))
                return False
    #end check_vsrx_not_in_agent

    def check_vsrx_not_in_control_nodes(self):
        for cn in self.inputs.bgp_ips:        
            ris_cn = self.cn_inspect[cn].get_cn_routing_instance_list()
            for inst in ris_cn:
                if inst in self.routing_instances:
                    self.logger.error("routing instance exists in CN - %s" %inst)
                    return False
    #end check_vsrx_not_in_control_node
        
    def cleanUp(self):
        super(vSRXFixture, self).cleanUp()
        do_cleanup= True
        if self.inputs.fixture_cleanup == 'no' : do_cleanup = False
        if self.already_present : do_cleanup= False
        if self.inputs.fixture_cleanup == 'force' : do_cleanup = True
        if do_cleanup :
            self.logger.info( "Deleting the vsrx instance %s" %(self.instance_name))
            self.handler.delete_vsrx_instance(self.vsrxinstance_obj['id'])
            time.sleep(10)
            if self.verify_is_run:
                import pdb; pdb.set_trace()
                assert self.check_vsrx_not_in_cs(), "vsrx instance not deleted from CS"
                assert self.check_vsrx_si_not_in_api_server(), "vsrx instance not removed from api server"
                assert self.check_vsrx_not_in_api_server(), "vsrx IPs not removed from api server"
                assert self.check_vsrx_not_in_agent(), "vsrx instance not removed from agent"
                assert self.check_vsrx_not_in_control_nodes(), "vsrx instance not removed from control node"
        else:
            self.logger.info('Skipping the deletion of VM %s' %(self.vm_name))
    #end cleanUp


