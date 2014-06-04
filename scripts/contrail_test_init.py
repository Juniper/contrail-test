import os
import re
import sys
import json
import time
import socket
import smtplib
import getpass
import logging 
import ConfigParser
from netaddr import *
import logging.config
from functools import wraps
from email.mime.text import MIMEText

import fixtures
from fabric.api import env, run
from fabric.operations import get, put
from fabric.context_managers import settings, hide 

from util import *
from custom_filehandler import *

#sys.path.append(os.path.realpath("/root/test/scripts/"))
#sys.path.append(os.path.realpath("/root/test/fixtures/"))

BUILD_DIR = {'fc17' : '/cs-shared/builder/',
             'centos_el6' : '/cs-shared/builder/centos64_os/',
             'xenserver'     : '/cs-shared/builder/xen/',
             'ubuntu'     : '/cs-shared/builder/ubuntu/',
            }

def check_state(function):
  @wraps(function)
  def wrapper(self,*args,**kwargs):
    #if not self.inputs.verify_state():
    #    self.inputs.logger.warn( "Pre-Test validation failed.. Skipping test %s" %(function.__name__))
    #    assert False, "Test did not run since Pre-Test validation failed"
    if not self.inputs.verify_control_connection(connections= self.connections):
        self.inputs.logger.warn( "Pre-Test validation failed.. Skipping test %s" %(function.__name__))
        assert False, "Test did not run since Pre-Test validation failed due to BGP/XMPP connection issue"
    else :
        return function(self,*args,**kwargs)
  return wrapper

def log_wrapper( function):
    @wraps(function)
    def wrapper(self, *args,**kwargs): 
        self.inputs.logger.info('=' * 80)
        self.inputs.logger.info('STARTING TEST    : ' + function.__name__ )
        self.inputs.logger.info('TEST DESCRIPTION : ' + function.__doc__ )
        f=None 
        f= function(self,*args,**kwargs) 
        if f :
            result= 'PASSED'
        else:
            result= 'FAILED'
#        except UnboundLocalError, e :
#            self.logger.error('UnboundLocalError during test.  %s' %(e) )
#            result= 'FAILED'
#        except AssertionError,e :
#            self.logger.error('Assertion during test. %s' %(e) )
#            result= 'FAILED'
        self.logger.info('')
        self.inputs.logger.info('END TEST : %s : %s' %(function.__name__, result ))
        self.inputs.logger.info('-' * 80)
        return f
    #end wrapper
    return wrapper
#end log_wrapper

class ContrailTestInit(fixtures.Fixture):
    def __init__(self, ini_file, stack_user=None, stack_password=None, project_fq_name=None  ):
        config = ConfigParser.ConfigParser()
        config.read(ini_file)
        self.config= config
        self.prov_file=config.get('Basic','provFile')
        self.username='root'
        self.password='c0ntrail123'
        self.key=config.get('Basic', 'key')
        self.api_server_port='8082'
        self.bgp_port='8083'
        self.ds_port='5998'
        self.project_fq_name= project_fq_name or ['default-domain', 'admin']
        self.project_name=self.project_fq_name[1]
        self.domain_name=self.project_fq_name[0]
        self.stack_user= stack_user or config.get('Basic','stackUser')
        self.stack_password= stack_password or config.get('Basic','stackPassword')
        self.stack_tenant=config.get('Basic','stackTenant')
        self.multi_tenancy= self.read_config_option( 'Basic', 'multiTenancy', 'False')
        if self.config.get( 'webui', 'webui') == 'False':
            self.webui_verification_flag = False
        else:
            self.webui_verification_flag = self.config.get( 'webui', 'webui')
        self.webui_config_flag = ( self.config.get( 'webui_config', 'webui_config') == 'True')
        self.devstack = ( self.config.get( 'devstack', 'devstack') == 'True')
        self.keystone_ip= self.read_config_option( 'Basic', 'keystone_ip', 'None')
        generate_html_report= config.get('Basic', 'generate_html_report')
        self.log_scenario= self.read_config_option( 'Basic', 'logScenario', 'Sanity')
        logging.config.fileConfig(ini_file)
        self.logger_key='log01'
        self.logger= logging.getLogger(self.logger_key)
        # config to direct logs to console
        console_h= logging.StreamHandler()
        console_h.setLevel(logging.INFO)
        console_log_format= logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_h.setFormatter(console_log_format)
        try:
            self.log_to_console= self.read_config_option( 'log_screen', 'log_to_console', 'no')
            if self.log_to_console == 'yes': self.logger.addHandler(console_h)
        except: 
            pass #no data to direct logs to screen
        if 'BUILD_ID' in os.environ :
            self.build_id= os.environ.get('BUILD_ID')
        else:
            self.build_id= '0000'
        if 'BRANCH' in os.environ :
             self.branch= os.environ.get('BRANCH')
        else:
            self.branch= ''
 
        if 'EMAIL_SUBJECT' in os.environ :
            self.log_scenario= os.environ.get('EMAIL_SUBJECT')
        else:
            self.log_scenario= self.log_scenario

        ts= self.get_os_env('SCRIPT_TS')
        self.ts= ts
        self.single_node= self.get_os_env( 'SINGLE_NODE_IP' )
        self.jenkins_trigger= self.get_os_env( 'JENKINS_TRIGGERED' )
            
        self.build_folder= self.build_id + '_' + ts
        self.log_path=os.environ.get('HOME')+'/logs/'+ self.build_folder
        self.log_file=self.logger.handlers[0].baseFilename
        if generate_html_report == "yes":
            self.generate_html_report= True
        else:
            self.generate_html_report= False
        #Fixture cleanup option
        self.fixture_cleanup = self.read_config_option( 'Basic', 'fixtureCleanup', 'yes')
        # Mx option 
        mx_infos = self.config.items('Mx')
        self.ext_routers = [] #List of (router_name, router_ip) Tuple.
        for mx_info, value in mx_infos:
            if 'router_name' in mx_info:
                self.ext_routers.append((value, 
                    self.read_config_option('Mx', '%s_router_ip' % value, None)))
        self.mx_rt = self.read_config_option('Mx', 'mx_rt', '10003')
        self.router_asn = self.read_config_option('Mx', 'router_asn', '64512')
        self.fip_pool_name = self.read_config_option('Mx', 'fip_pool_name', 'public-pool')
        self.fip_pool = self.read_config_option('Mx', 'fip_pool', None)
        #Mail Setup
        self.smtpServer= config.get('Mail','server')
        self.smtpPort= config.get('Mail','port')
        self.mailSender=config.get('Mail','mailSender')
        self.mailTo=config.get('Mail','mailTo')        
        
        #Web Server to upload files 
        self.web_server= config.get('WebServer','host')
        self.web_server_path= config.get('WebServer', 'path') + '/' + self.build_folder + '/'
        self.web_serverUser= config.get('WebServer', 'username')
        self.web_server_password= config.get('WebServer', 'password')
        self.web_root= config.get('WebServer', 'webRoot')
        
        #Test Revision
        self.test_repo_dir= self.read_config_option( 'Basic', 'testRepoDir', '/root/test/')
        try:
            self.test_revision = config.get('repos', 'test_revision')
        except ConfigParser.NoOptionError:
            self.test_revision = ''
        try:
            self.fab_revision = config.get('repos', 'fab_revision')
        except ConfigParser.NoOptionError:
            self.fab_revision = ''
#        self.test_revision = config.get('repos', 'test_revision')
#        self.fab_revision = config.get('repos', 'fab_revision')

        # debug option 
        self.stop_on_fail = False
        stop_on_fail = config.get( 'debug', 'stop_on_fail')
        if stop_on_fail == "yes":
            self.stop_on_fail = True
        self.is_juniper_intranet = False
        self.check_juniper_intranet()
        
        self.os_type = {}
        
        self.html_report= self.log_path + '/test_report.html'
        log_link= 'http://%s/%s/logs/%s/%s' %(self.web_server, self.web_root, 
                        self.build_folder, self.log_file.split('/')[-1])
        html_log_link= 'http://%s/%s/logs/%s/%s' %(self.web_server, self.web_root, 
                        self.build_folder, self.html_report.split('/')[-1])
        self.html_log_link= '<a href=\"%s\">%s</a>' %(html_log_link , html_log_link)
        self.log_link= '<a href=\"%s\">%s</a>' %(log_link , log_link)
        repo_file = 'repos.html'
        self.html_repos = os.path.join(self.log_path, repo_file) 
        html_repo_link = 'http://%s/%s/logs/%s/%s' % (self.web_server, self.web_root,
                          self.build_folder, repo_file)
        self.html_repo_link = None
        if self.is_juniper_intranet:
            self.html_repo_link = '<a href=\"%s\">%s</a>' %(html_repo_link, html_repo_link)

    #end __init__

    def setUp(self):
        super(ContrailTestInit, self).setUp()
        if self.single_node != '':
            self.prov_data= self._create_prov_data()
        else:
            self.prov_data=self._read_prov_file()
        self.os_type = self.get_os_version()
        self.username= self.host_data[ self.cfgm_ip ]['username']
        self.password= self.host_data[ self.cfgm_ip ]['password']
        # List of service correspond to each module
        self.compute_services=['contrail-vrouter', 'openstack-nova-compute']
        self.control_services=['contrail-control']
        self.cfgm_services=['contrail-api', 'contrail-schema',
                        'contrail-discovery', 'contrail-zookeeper']
        self.webui_services = ['contrail-webui', 'contrail-webui-middleware']
        self.openstack_services = ['openstack-cinder-api', 'openstack-cinder-scheduler',
                             'openstack-cinder-scheduler', 'openstack-glance-api',
                             'openstack-glance-registry', 'openstack-keystone',
                             'openstack-nova-api', 'openstack-nova-scheduler',
                             'openstack-nova-cert']
        self.collector_services= ['redis', 'contrail-collector', 'contrail-opserver', 'contrail-qe']
        if self.devstack :
           self.mysql_token = 'contrail123'
        else : 
            self.mysql_token= self.get_mysql_token()
    #end setUp
    
    def get_repo_version(self):
        if 'BUILD_ID' in os.environ :
            git_file = 'git_build_%s.txt' % self.build_id
            cmd = 'cat %s' %  os.path.join(BUILD_DIR[self.os_type[self.cfgm_ip]],
                                           self.build_id, git_file)
            build_versions = self.run_cmd_on_server(self.web_server, cmd,
                                 self.web_serverUser, self.web_server_password)
            if not 'No such file' in build_versions:
                build_versions = str(build_versions).replace('\r\n', '<br>')
            with open(self.html_repos, 'w+') as repofile:
                repofile.write(build_versions + '<br>')
        test_version = 'ssh://git@github.com:Juniper/contrail-test %s<br>' % self.test_revision
        fab_version = 'ssh://git@github.com:Juniper/contrail-fabric-utils %s<br>' % self.fab_revision
        with open(self.html_repos, 'a') as repofile:
            repofile.write(test_version)
            repofile.write(fab_version)
        self.upload_to_webserver(self.html_repos)

    def get_os_env(self, var):
        if var in os.environ:
            return os.environ.get(var)
        else:
            return ''
    #end get_os_env
    
    def get_os_version(self):
        '''
        Figure out the os type on each node in the cluster
        '''
        os_type = {}
        for host_ip in self.host_ips:
            username= self.host_data[host_ip]['username']
            password= self.host_data[host_ip]['password']
            with settings(host_string= '%s@%s' %(username, host_ip), password= password,
                      warn_only=True,abort_on_prompts=False):
                output = run('uname -a')
                if 'el6' in output:
                    os_type[host_ip] = 'centos_el6'
                if 'fc17' in output:
                    os_type[host_ip] = 'fc17'
                if 'xen' in output:
                    os_type[host_ip] = 'xenserver'
                if 'Ubuntu' in output:
                    os_type[host_ip] = 'ubuntu'
        return os_type
    #end get_os_version
                
    
    def read_config_option( self, section, option, default_option):
        ''' Read the config file. If the option/section is not present, return the default_option
        '''
        try:
            val= self.config.get( section, option )
            return val
        except ConfigParser.NoOptionError: 
            return default_option
    #end read_config_option

    def _read_prov_file(self):
        prov_file = open(self.prov_file, 'r')
        prov_data = prov_file.read()
        json_data=json.loads(prov_data)
        self.cfgm_ip=''
        self.cfgm_ips =[]
        self.cfgm_control_ips =[]
        self.cfgm_names=[]
        self.collector_ips=[]
        self.collector_control_ips=[]
        self.collector_names=[]
        self.compute_ips=[]
        self.compute_names=[]
        self.compute_control_ips=[]
        self.compute_info= {}
        self.bgp_ips=[]
        self.bgp_control_ips=[]
        self.bgp_names=[]
        self.ds_server_ip=[]
        self.ds_server_name=[]
        self.host_ips=[]
        self.host_data= {}
        self.vgw_data= {}
        for host in json_data['hosts'] :
            host_ip=str(IPNetwork(host['ip']).ip)
            host_data_ip=str(IPNetwork(host['data-ip']).ip)
            host_control_ip=str(IPNetwork(host['control-ip']).ip)
            self.host_ips.append(host_ip)
            self.host_data[host_ip] = host
            self.host_data[host_data_ip] = host
            self.host_data[host_control_ip] = host
            self.host_data[ host['name'] ] = host
            self.host_data[ host['name'] ]['host_ip']= host_ip
            self.host_data[ host['name'] ]['host_data_ip']= host_data_ip
            self.host_data[ host['name'] ]['host_control_ip']= host_control_ip
            roles= host["roles"]
            for role in roles :
                if role['type'] == 'openstack':
                    if self.keystone_ip != 'None':
                        self.openstack_ip= self.keystone_ip
                    else:
                        self.openstack_ip= host_ip
                if role['type'] == 'cfgm':
                    self.cfgm_ip= host_ip
                    self.cfgm_ips.append(host_ip)
                    self.cfgm_control_ips.append(host_control_ip)
                    self.cfgm_control_ip= host_control_ip
                    self.cfgm_names.append(host['name'])
                    self.ds_server_ip.append(host_ip)
                    self.ds_server_name.append(host['name'])
                    self.masterhost=self.cfgm_ip
                    self.hostname=host['name']
                if role['type']== 'compute':
                    self.compute_ips.append(host_ip)
                    self.compute_names.append(host['name'])
                    self.compute_info[host['name']]= host_ip
                    self.compute_control_ips.append(host_control_ip)
                if role['type'] == 'bgp':

                    self.bgp_ips.append(host_ip)
                    self.bgp_control_ips.append(host_control_ip)
                    self.bgp_names.append(host['name'])
#                if role['type'] == 'collector' :
#                    self.collector_ip= host_ip
                if role['type'] == 'webui':
                    self.webui_ip = host_ip
                if role['type'] == 'collector' :
                    self.collector_ip= host_ip
                    self.collector_ips.append(host_ip)
                    self.collector_control_ips.append(host_control_ip)
                    self.collector_names.append(host['name'])
            #end for
        #end for
        if json_data.has_key('vgw'): self.vgw_data = json_data['vgw'] 
        return json.loads(prov_data)
    #end _read_prov_file
    
    def _create_prov_data(self):
        ''' Creates json data for a single node only.
        
        '''
        single_node= self.single_node
        self.cfgm_ip= single_node
        self.cfgm_ips= [single_node]
        self.bgp_ips=[single_node]
        self.compute_ips= [single_node]
        self.host_ips= [single_node]
        self.collector_ip= single_node
        self.collector_ips= [single_node]
        self.webui_ip= single_node
        self.openstack_ip= single_node
        json_data= {}
        self.host_data= {}
        hostname= socket.gethostbyaddr(single_node)[0]
        self.hostname= hostname
        self.compute_names= [self.hostname]
        self.compute_info= {hostname: single_node}
        json_data['hosts']= [{
            'ip' : single_node,
            'name' : hostname,
            'username' : self.username,
            'password' : self.password,
            'roles' : [
            {"params": {"collector": hostname, "cfgm": hostname}, "type": "bgp"},

            {"params": {"bgp": [hostname, hostname],"cfgm": hostname, "collector": hostname}, "type": "compute"},
            {"params": {"collector": hostname}, "type": "cfgm"},
            {"params": {"cfgm": hostname}, "type": "webui"},
            { "type": "collector"}
            ]
            }]
        self.host_data[ single_node ] = json_data[ 'hosts' ][0]
        return json_data
    #end _create_prov_data

    
    def get_pwd(self):
        if 'EMAIL_PWD' in os.environ :
            self.p=os.environ.get('EMAIL_PWD')
        else:
            self.p=getpass.getpass(prompt='Enter password for  '+self.mailSender+' : ')
    #end get_pwd

    
    def verify_state(self):
        result=True
        for host in self.host_ips:
            username= self.host_data[host]['username']
            password= self.host_data[host]['password']
            if host in self.compute_ips:
                for service in self.compute_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled', 
                                active_str1, 'active', active_str2, 'running')
            if host in self.bgp_ips:
                for service in self.control_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled',
                                active_str1, 'active', active_str2, 'running')
            if host == self.cfgm_ips:
                for service in self.cfgm_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled',
                                active_str1, 'active', active_str2, 'running')
            if host in self.collector_ips:
                for service in self.collector_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled',
                                active_str1, 'active', active_str2, 'running')
            if host == self.webui_ip:
                for service in self.webui_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled',
                                active_str1, 'active', active_str2, 'running')
            if host == self.openstack_ip:
                for service in self.openstack_services:
                    (state, active_str1, active_str2)=  self.get_service_status(host,
                                                     service, username, password)
                    result = result and self._compare_service_state( host, service, state, 'enabled',
                                active_str1, 'active', active_str2, 'running')
        if not result :
            self.logger.error('One or more process-states are not correct on nodes')
        return result
    #end verify_state

    def verify_control_connection(self, connections):
        self.connections= connections
        self.agent_inspect= self.connections.agent_inspect
        self.cn_inspect= self.connections.cn_inspect
        result=True
        #return result
        for host in self.host_ips:
            username= self.host_data[host]['username']
            password= self.host_data[host]['password']
            if host in self.compute_ips:
                # Verify the connection between compute to all control nodes 
                inspect_h= self.agent_inspect[host]
                agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()

                # Calculating the the expected list of bgp peer
                expected_bgp_peer = []
                expected_bgp_peer_by_addr = []
                actual_bgp_peer = []
                for item in self.host_data[host]['roles']:
                    if item['type'] == 'compute':
                        expected_bgp_peer = item['params']['bgp']
                for item in expected_bgp_peer: expected_bgp_peer_by_addr.append(self.host_data[item]['host_control_ip'])

                # Get the actual list of controller IP
                for i in xrange(len(agent_xmpp_status)): actual_bgp_peer.append(agent_xmpp_status[i]['controller_ip'])
               
                # Matching the expected and actual bgp contreoller
                # sort the value for list match
                actual_bgp_peer.sort()
                expected_bgp_peer_by_addr.sort()

                if actual_bgp_peer != expected_bgp_peer_by_addr :
                    result = result and False
                    self.logger.error('All the required BGP controller has not found in agent introspect for %s' %(host))
                for entry in agent_xmpp_status:
                    if entry['state'] != 'Established':
                        result = result and False
                        self.logger.info('From agent %s connection to control node %s is not Established' %(host , entry['controller_ip']))
            if host in self.bgp_ips:
                # Verify the connection between all control nodes
                cn_bgp_entry=self.cn_inspect[host].get_cn_bgp_neigh_entry()
                control_node_bgp_peer_list = []
                control_node_bgp_xmpp_peer_list = []
                if type(cn_bgp_entry) == type(dict()):
                    if cn_bgp_entry['peer_address'] in self.bgp_ips:
                        if cn_bgp_entry['state'] != 'Established':
                            self.logger.error('For control node %s, with peer %s peering is not Established. Current State %s ' %(host, cn_bgp_entry['peer_address'] , cn_bgp_entry['state']))
                    if cn_bgp_entry['encoding']== 'BGP':
                        control_node_bgp_peer_list= [cn_bgp_entry['peer_address']]  
                    else:
                        control_node_bgp_xmpp_peer_list= [cn_bgp_entry['peer_address']]   
                     
                else:
                    for entry in cn_bgp_entry:
                        if entry ['peer_address'] in self.bgp_ips:
                            if entry ['state'] != 'Established':
                                result = result and False
                                self.logger.error('For control node %s, with peer %s peering is not Established. Current State %s ' %(host, entry ['peer'] , entry['state']) )
                        if entry['encoding']== 'BGP':
                            control_node_bgp_peer_list.append(entry['peer_address'])
                        else:
                            control_node_bgp_xmpp_peer_list.append(entry['peer_address'])

                # Verify all required xmpp entry is present in control node
                # sort the value for list match
                expected_xmpp_peer_list= []
                for entry in self.compute_ips:
                    expected_xmpp_peer_list.append(self.host_data[entry]['host_control_ip'])
                    
                #self.compute_ips.sort()
                expected_xmpp_peer_list.sort()
                control_node_bgp_xmpp_peer_list.sort()
                if expected_xmpp_peer_list != control_node_bgp_xmpp_peer_list :
                   result = result and False
                   self.logger.error('All the required XMPP entry not present in control node introspect for %s' %(host))
                # Verify all required BGP entry is present in control node
                control_node_bgp_peer_list.append(self.host_data[host]['host_control_ip'])

                
                # sort the value for list match
                control_node_bgp_peer_list.sort()
                expected_cn_bgp_peer_list= []
                for entry in self.bgp_ips:
                    expected_cn_bgp_peer_list.append(self.host_data[entry]['host_control_ip'])
                expected_cn_bgp_peer_list.sort()
                if not set(expected_cn_bgp_peer_list).issubset(control_node_bgp_peer_list) :
                    result = result and False
                    self.logger.error('All the required BGP entry not present in control node introspect for %s' %(host))
        if not result :
            self.logger.error('One or more process-states are not correct on nodes')
        return result
    #end verify_control_connection 
    
    def reboot(self, host_ip):
        i = socket.gethostbyaddr(host_ip)[0]
        print "rebooting %s" %i
        sudo('reboot')
    #end reboot
    
    def restart_service(self,service_name, host_ips= [], contrail_service= True):
        result=True
        if len(host_ips) == 0 : 
            host_ips=self.host_ips
        for host in host_ips:
            username= self.host_data[host]['username']
            password= self.host_data[host]['password']
	    self.logger.info('Restarting %s.service in %s' %(service_name,self.host_data[host]['name']))
            if contrail_service:
                issue_cmd = 'service %s restart' %(service_name)
            else:
                issue_cmd = 'service %s restart' %(service_name)
        self.run_cmd_on_server(host,issue_cmd, username, password,pty=False)
    #end restart_service

    def stop_service(self,service_name, host_ips= [], contrail_service= True):
        result=True
        if len(host_ips) == 0 :
            host_ips=self.host_ips
        for host in host_ips:
            username= self.host_data[host]['username']
            password= self.host_data[host]['password']
            self.logger.info('Stoping %s.service in %s' %(service_name,self.host_data[host]['name']))
            if contrail_service:
   		issue_cmd = 'service %s stop' %(service_name)
 	    else:
   		issue_cmd = 'service %s stop' %(service_name)
            self.run_cmd_on_server(host,issue_cmd, username, password, pty=False)
    #end stop_service

    def start_service(self,service_name, host_ips= [], contrail_service= True):
        result=True
        if len(host_ips) == 0 :
            host_ips=self.host_ips
        for host in host_ips:
            username= self.host_data[host]['username']
            password= self.host_data[host]['password']
            self.logger.info('Starting %s.service in %s' %(service_name,self.host_data[host]['name']))
            if contrail_service:
		issue_cmd = 'service %s start' %(service_name)
            else:
		issue_cmd = 'service %s start' %(service_name)
            self.run_cmd_on_server(host,issue_cmd, username, password, pty=False)
    #end start_service

    
    def _compare_service_state(self, host, service, state, state_val, active_str1, active_str1_val,
                    active_str2, active_str2_val):
        result = False 
        if 'xen' in self.os_type[host] or 'centos' in self.os_type[host]:
            if active_str2 != active_str2_val:
                result= False
                self.logger.warn( 'On host %s,Service %s state is (%s) .. NOT Expected !!' %(host, service ,active_str2) )
        elif 'fc' in self.os_type[host]:
            if (state, active_str1, active_str2) != (state_val, active_str1_val, active_str2_val):
                result= False
                self.logger.warn( 'On host %s,Service %s states are %s, %s, %s .. NOT Expected !!' %(host, service ,
                    state, active_str1, active_str2) )
        return result
    #end _compare_service_state

    def get_service_status(self, server_ip, service_name, username='root',
                            password='contrail123'):
        state=None
        active_str1=None
        active_str2=None
        with hide('everything'):
            with settings(host_string=server_ip, username= username, password= password,
                          warn_only=True,abort_on_prompts=False):
                if 'fc' in self.os_type[server_ip]:
                    output=run('systemctl status %s.service | head ' %(service_name))
                    if service_name not in output:
                        return (None, None, None)
                    match_obj1= re.search(r'Active: (.*) \((.*)\)', output, re.M|re.I)
                    match_obj2= re.search(r'Loaded.* (.*)\)', output, re.M|re.I)
                    if match_obj1:
                        active_str1= match_obj1.group(1)
                        active_str2= match_obj1.group(2)
                    if match_obj2:
                        state= match_obj2.group(1)
                elif 'centos' in self.os_type[server_ip] or 'xen' in self.os_type[server_ip]:
                    output=run('/etc/init.d/%s status' %(service_name) )
                    if 'running' in output.lower():
                        active_str2='running'
                    else :
                        active_str2= output                    
            return (state, active_str1, active_str2)
    #end get_service_status

    def run_provision_control ( self, router_asn, api_server_ip, api_server_port, oper):

        username= self.host_data[self.cfgm_ip]['username']
        password= self.host_data[self.cfgm_ip]['password']
        bgp_ips=set(self.bgp_ips)
        for host in bgp_ips: 
            host_name = self.host_data[host]['name']
            issue_cmd = "python /opt/contrail/utils/provision_control.py --host_name '%s' --host_ip '%s' --router_asn '%s' --api_server_ip '%s' --api_server_port '%s' --oper '%s'" %(host_name,host,router_asn,api_server_ip,api_server_port,oper)
      
            output = self.run_cmd_on_server(self.cfgm_ip, issue_cmd, username, password) 
            if output.return_code != 0:
                self.logger.exception('Fail to execute provision_control.py')
                return output 

    # end run_provision_control
    
    def get_mysql_token(self):
        username= self.host_data[self.openstack_ip]['username']
        password= self.host_data[self.openstack_ip]['password']
        cmd= 'cat /etc/contrail/mysql.token'
        return self.run_cmd_on_server( self.openstack_ip, cmd, username, password) 
    #end get_mysql_token
    
    def run_provision_mx( self, api_server_ip, api_server_port, router_name, router_ip, router_asn, oper):

        username= self.host_data[self.cfgm_ip]['username']
        password= self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /opt/contrail/utils/provision_mx.py --api_server_ip '%s' --api_server_port '%s' --router_name '%s' --router_ip '%s'  --router_asn '%s' --oper '%s'" %(api_server_ip,api_server_port,router_name,router_ip,router_asn, oper) 
        output = self.run_cmd_on_server(self.cfgm_ip, issue_cmd, username, password) 
        if output.return_code != 0:
            self.logger.exception('Fail to execute provision_mx.py')
            return output
    # end run_provision_mx
  
    def config_route_target( self, routing_instance_name, route_target_number, router_asn, api_server_ip, api_server_port): 

        username= self.host_data[self.cfgm_ip]['username']
        password= self.host_data[self.cfgm_ip]['password']
        issue_cmd = "python /opt/contrail/utils/add_route_target.py --routing_instance_name '%s' --route_target_number '%s' --router_asn '%s' --api_server_ip '%s' --api_server_port '%s'" %(routing_instance_name,route_target_number,router_asn,api_server_ip,api_server_port)        
          
        output = self.run_cmd_on_server(self.cfgm_ip, issue_cmd, username, password)
        if output.return_code != 0:
            self.logger.exception('Fail to execute add_route_target.py')
            return output
    # end config_route_target

    def configure_mx( self, tunnel_name, bgp_group, cn_ip, mx_ip, mx_rt, mx_as, mx_user, mx_password, ri_name, intf, vrf_target, ri_gateway ):
       
       host_ip_with_subnet="%s/32" % (cn_ip)

       # Initializing list of command need to be configured in MX
       command_to_push = ['configure']
      
       # Populating the required command
       ##command_to_push.append("set routing-options dynamic-tunnels tunnel_name source-address %s" %(mx_ip.split('/')[0]))
       #command_to_push.append("set routing-options dynamic-tunnels %s source-address %s" %(tunnel_name,mx_ip))
       #command_to_push.append("set routing-options dynamic-tunnels %s gre" % (tunnel_name ) )
       #command_to_push.append("set routing-options dynamic-tunnels %s destination-networks %s" % (tunnel_name,host_ip_with_subnet))
       #command_to_push.append("set protocols bgp group %s type internal" % (bgp_group))
       ##command_to_push.append("set protocols bgp group %s local-address %s" %(bgp_group,mx_ip.split('/')[0]))
       #command_to_push.append("set protocols bgp group %s local-address %s" %(bgp_group,mx_ip))
       #command_to_push.append("set protocols bgp group %s family inet-vpn unicast" % (bgp_group))
       #command_to_push.append("set protocols bgp group %s neighbor %s" % (bgp_group,cn_ip))
       #command_to_push.append("set routing-instances %s instance-type vrf" % (ri_name))
       #command_to_push.append("set routing-instances %s interface %s" %(ri_name, intf))
       #command_to_push.append("set routing-instances %s vrf-target %s:%s:%s" %(ri_name, vrf_target,mx_as,mx_rt))
       #command_to_push.append("set routing-instances %s vrf-table-label" %(ri_name))
       #command_to_push.append("set routing-instances %s routing-options static route 0.0.0.0/0 next-hop %s" %(ri_name, ri_gateway))
       #command_to_push.append("commit")
 
       print "Final commad will be pushed to MX"
       print "%s" % command_to_push 
       
       #for command in command_to_push:
       #    output = self.run_cmd_on_server(mx_ip,command,mx_user,mx_password)
       #    if output.return_code != 0:
       #        self.logger.exception('Fail to configure MX')
       #        return output
       command_to_push_string=";".join(command_to_push)
       output = self.run_cmd_on_server(mx_ip,command_to_push_string,mx_user,mx_password)

    # end configure_mx 
 
    def unconfigure_mx( self, tunnel_name, bgp_group): 

        # Initializing list of command need to be configured in MX
        command_to_push = ['configure']  

        # Populating the required command
        command_to_push.append("delete routing-options dynamic-tunnels %s gre" % (tunnel_name ))
        command_to_push.append("delete protocols bgp group %s" % (bgp_group))
        command_to_push.append("commit")

        print "Final commad will be pushed to MX"
        print "%s" % command_to_push

        for command in command_to_push:
            output = self.run_cmd_on_server(mx_ip,command,mx_user,mx_password)
            if output.return_code != 0:
                self.logger.exception('Fail to unconfigure MX')
                return output
    # end unconfigure_mx
    
    def run_cmd_on_server(self, server_ip,issue_cmd, username='root',
                            password='contrail123', pty=True):
        self.logger.debug("COMMAND: (%s)" % issue_cmd)
        with hide('everything'):
            with settings(host_string= '%s@%s' %(username, server_ip), password= password,
                      warn_only=True,abort_on_prompts=False):
                output=run('%s' %(issue_cmd),pty=pty)
                self.logger.debug(output)
                return output
    #end run_cmd_on_server
    
    def cleanUp(self):
        super(ContrailTestInit, self).cleanUp()
    
    @retry(delay=10, tries= 2)
    def send_mail(self, file):
        textfile=file
        fp = open(textfile, 'rb')
        msg = MIMEText(fp.read(),'html')
        fp.close()
       
        msg['Subject'] = '[%s Build %s] ' %(self.branch, self.build_id)+self.log_scenario+' Report'
        msg['From'] = self.mailSender
        msg['To'] = self.mailTo

        s= None
        try:
            s = smtplib.SMTP(self.smtpServer, self.smtpPort)
        except Exception,e:
            print "Unable to connect to Mail Server"
            return False
        s.ehlo()
        try:
            s.sendmail(self.mailSender, [self.mailTo], msg.as_string())
            s.quit()
        except smtplib.SMTPException, e :
            self.logger.exception('Error while sending mail')
            return False
        return True
    #end send_mail    
    
    def upload_to_webserver(self, elem):
        try:
            with hide('everything'):
                with settings(host_string=self.web_server,
                              user=self.web_serverUser,
                              password=self.web_server_password,
                              warn_only=True, abort_on_prompts=False):
                    run('mkdir -p %s' %( self.web_server_path))
                    output = put(elem, self.web_server_path)
        except Exception:
            self.logger.exception('Error occured while uploading the logs to the Web Server ')
            return False
        return True

    def upload_results(self):
        if self.is_juniper_intranet:
            self.html_repos = self.get_repo_version()
        self.upload_to_webserver(self.log_file)
        if self.generate_html_report:
            self.upload_to_webserver(self.html_report)
    #end upload_results      
    
    def log_any_issues( self, test_result) : 
        ''' Log any issues as seen in test_result (TestResult) object
        '''
        self.logger.info('\n TEST ERRORS AND FAILURES : \n')
        if sys.version_info >= (2,7):
            self.logger.info(str( test_result.printErrors() ) )
            print test_result.printErrors()
        for failure_tuple in test_result.failures:
            for item in failure_tuple:
                self.logger.info(item)
                print item
    #end log_any_issues
    
    def get_node_name(self, ip):
        return self.host_data[ip]['name']
    
    def get_html_description(self): 
        
        compute_nodes= [self.get_node_name(x) for  x in self.compute_ips]
        bgp_nodes= [self.get_node_name(x) for  x in self.bgp_ips]
        collector_nodes= [self.get_node_name(x) for  x in self.collector_ips]
        cfgm_nodes= [self.get_node_name(x) for  x in self.cfgm_ips]
        string = '%s Result of Build %s<br>\
                  Log File : %s<br>\
                  Report   : %s<br>\
                  Git Revision: %s<br>\
                  <br><pre>CFGM          : %s<br>Control Nodes : %s<br>Compute Nodes : %s<br>Collector     : %s<br>WebUI         : %s<br>OpenstackUI   : %s<br></pre>' % (
                  self.log_scenario, self.build_id, self.log_link,
                  self.html_log_link, self.html_repo_link,
                  cfgm_nodes, bgp_nodes, compute_nodes,
                  collector_nodes, self.get_node_name(self.webui_ip), self.get_node_name(self.openstack_ip))
        if self.jenkins_trigger :
            string= string + "<br>All logs/cores will be at \
                              /cs-shared/test_runs/%s/%s on \
                              nodeb10.englab.juniper.net<br>" % (
                              self.host_data[self.cfgm_ips[0]]['name'], self.ts)
        return string
    
    def check_juniper_intranet(self):
        #cmd = 'ping -c 5 www-int.juniper.net'
        cmd = 'ping -c 5 ntp.juniper.net'
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            self.is_juniper_intranet = True
            self.logger.debug('Detected to be inside Juniper Network')
        except subprocess.CalledProcessError:
            self.is_juniper_intranet = False
            self.logger.debug('Detected to be outside of Juniper Network')
    #end check_juniper_intranet
        
    #end get_html_description
