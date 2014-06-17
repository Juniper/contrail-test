import fixtures
from vnc_api.vnc_api import *
from vnc_api.common import exceptions as vncExceptions
from project_test import *
import time
from contrail_fixtures import *
import ast
import sys
from util import retry
from analytics_tests import *
from floating_ip import FloatingIPFixture

#@contrail_fix_ext ()
class CSFloatingIPFixture(fixtures.Fixture):
    def __init__(self, connections, project_name):
        self.connections= connections
        self.inputs= connections.inputs
        self.api_s_inspect= self.connections.api_server_inspect
        self.network_handle= self.connections.network_handle
        self.agent_inspect= self.connections.agent_inspect
        self.cn_inspect= self.connections.cn_inspect
        self.vnc_lib_h= self.connections.vnc_lib
        self.analytics_obj=self.connections.analytics_obj
        self.cs_client = connections.cstack_handle.client

        self.project_name= project_name
        self.logger= self.inputs.logger
        self.already_present= False
        self.verify_is_run= False
        self.fip={}
    #end __init__

    def setUp(self):
        super(CSFloatingIPFixture, self).setUp()
        self.project_fixture= self.useFixture(ProjectFixture(connections=self.connections, vnc_lib_h= self.vnc_lib_h, project_name = self.project_name))
        self.project_obj= self.project_fixture.project_obj
#        if not self.is_fip_pool_present( self.pool_name):
#            self.create_floatingip_pool(self.pool_name, self.vn_id)
#        else :
#            self.logger.debug('FIP pool %s already present, not creating it' %(self.pool_name) )
#            self.already_present= True
    #end setUp

    def verify_on_setup(self):
        result= True
        if not self.verify_fip_pool_in_api_server():
            result &= False
            self.logger.error(' Verification of FIP pool %s in API Server failed' %(self.pool_name) )
        if not self.verify_fip_pool_in_control_node():
            result &= False
            self.logger.error(' Verification of FIP pool %s in Control-node failed' %(self.pool_name) )
        self.verify_is_run= True
        return True
    #end verify_on_setup

    def create_floatingip_pool(self, fip_pool_name, vn_id ) :
        self.logger.info( 'Creating Floating IP pool %s in API Server' %(fip_pool_name) )

        # create floating ip pool from public network
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read( id = vn_id )
        self.pub_vn_name= self.pub_vn_obj.name
        self.fip_pool_obj = FloatingIpPool( fip_pool_name, self.pub_vn_obj )
        self.fip_pool_id= self.vnc_lib_h.floating_ip_pool_create( self.fip_pool_obj )

        # allow current project to pick from pool
        self.project_obj.add_floating_ip_pool( self.fip_pool_obj )
        self.vnc_lib_h.project_update( self.project_obj )
    #end create_floatingip_pool

    def is_fip_pool_present(self, pool_name):
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read( id = self.vn_id )
        self.pub_vn_name= self.pub_vn_obj.name
        try:
            fip_pool_list= self.vnc_lib_h.floating_ip_pools_list( parent_id = self.vn_id )
            #Bug 532
            fip_pool_dict= ast.literal_eval(str(fip_pool_list))
            if not fip_pool_dict['floating-ip-pools']:
                return False
            fip_fq_name= [i for i in fip_pool_dict['floating-ip-pools'] if i['fq_name'][-1]== pool_name][0]['fq_name']
            self.fip_pool_obj = self.vnc_lib_h.floating_ip_pool_read( fq_name= fip_fq_name )
            self.fip_pool_id= self.fip_pool_obj.uuid
        except vncExceptions.HttpError:
            return None
        return True
    #end get_fip_pool_if_present

    def verify_fip_pool_in_api_server(self):
        result= True
        self.cs_fip_pool_obj= self.api_s_inspect.get_cs_alloc_fip_pool(fip_pool_name= self.pool_name,
                               vn_name= self.pub_vn_obj.name, refresh= True)
        if not self.cs_fip_pool_obj:
            self.logger.warn( "Floating IP pool %s not found in API Server " %(self.pool_name) )
            result= result and False
        self.cs_fip_pool_id= self.cs_fip_pool_obj['floating-ip-pool']['uuid']
        self.cs_fvn_obj= self.api_s_inspect.get_cs_vn( vn= self.pub_vn_obj.name , refresh = True)
        if result :
            self.logger.info('FIP Pool verificatioin in API Server passed for Pool %s' %(self.pool_name) )
        return result
    #end verify_fip_pool_in_api_server

    def verify_fip_pool_in_control_node(self):
        result= True
        for cn in self.inputs.bgp_ips:
            cn_object= self.cn_inspect[cn].get_cn_config_fip_pool( vn_name= self.pub_vn_name, fip_pool_name = self.pool_name )
            if not cn_object:
                self.logger.warn( "Control-node ifmap object for FIP pool %s , VN %s not found" %(self.pool_name, self.pub_vn_name))
                result = result and False
            else :
                self.logger.debug( 'Control-node Ifmap-view has FIP pool %s information' %(self.pool_name) )

        return result
    #end verify_fip_pool_in_control_node

    def delete_floatingip_pool(self ) :
        fip_pool_id= self.fip_pool_id
        fip_pool_obj=self.vnc_lib_h.floating_ip_pool_read(id= fip_pool_id)
        self.project_obj.del_floating_ip_pool(fip_pool_obj)
        self.vnc_lib_h.project_update(self.project_obj)
        self.vnc_lib_h.floating_ip_pool_delete(id= fip_pool_id)
    #end delete_floatingip_pool

    @retry(delay=5, tries=3)
    def verify_fip_pool_not_in_control_node(self):
        result= True
        for cn in self.inputs.bgp_ips:
            cn_object= self.cn_inspect[cn].get_cn_config_fip_pool( vn_name= self.pub_vn_name, fip_pool_name = self.pool_name )
            if cn_object:
                self.logger.warn( "Control-node ifmap object for FIP pool %s , VN %s is found!" %(self.pool_name, self.pub_vn_name))
                result = result and False
            else :
                self.logger.debug( 'Control-node Ifmap-view does not have FIP pool %s information' %(self.pool_name) )
        return result
    #end verify_fip_pool_not_in_control_node

    def create_and_assoc_fip(self, vn_id, vm_id):
        '''
        Specific to Cloudstack.
        Create and associate a floating IP to a VM with vm_id bound to a guest VN id vn_id

        Recommended to call verify_fip() after this method to make sure that the floating IP is correctly installed
        '''
        try:
            cs_fip_obj = self.create_floatingip(vn_id)
            response = self.assoc_floatingip( cs_fip_obj['id'], vm_id)
            if response['enablestaticnatresponse']['success'] != 'true':
                self.logger.error('Associating Public IP id %s to VM ID %s failed..Pleas check logs ' %( cs_fip_obj['id'], vm_id ) )
                return None
            return cs_fip_obj
        except :
            self.logger.error('Failed to create or associate FIP. Error: %s' %(sys.exc_info()[0]))
            return None
    #end create_and_assoc_fip

    def verify_fip(self, cs_fip_obj, vm_fixture, vn_fixture ):
        result= True

        fip = cs_fip_obj['ipaddress']
        fip_id = cs_fip_obj['id']
        self.fip[fip_id]= fip
        #For cloudstack, this is the only IP which is using floatingip
        pub_vn_ri = 'default-domain:default-project:__default_Public__:__default_Public__'
        pub_vn_name = '__default_Public__'
        if not self.verify_fip_in_control_node( fip, vm_fixture, pub_vn_ri):
            result&= False
        if not self.verify_fip_in_agent( fip, vm_fixture, pub_vn_name):
            result&= False
        if not self.verify_fip_in_api_server (fip_id):
            result&= False
        if not self.verify_fip_in_uve(fip, vm_fixture, vn_fixture):
            result&= False
        return True
    #end verify_fip

    def verify_no_fip( self, cs_fip_obj):
        result= True
        pub_vn_ri = 'default-domain:default-project:__default_Public__:__default_Public__'
        fip = cs_fip_obj['ipaddress']
        fip_id = cs_fip_obj['id']
        if not self.verify_fip_not_in_control_node( fip, pub_vn_ri):
            self.logger.error('FIP %s absense verification failed on one or more control-nodes' %(fip) )
            result&= False
        pub_vn_name = '__default_Public__'
        if not self.verify_fip_not_in_agent(fip, pub_vn_name) :
            self.logger.error('FIP %s absense verification failed on one or more agents ' %(fip) )
            result&= False
            self.logger.error('FIP %s absense verification failed on API server ' %(fip) )
        if not self.verify_fip_not_in_api_server (fip_id):
            result&= False
        return result
    #end verify_no_fip

    @retry(delay=5, tries=3)
    def verify_fip_in_control_node(self, fip, vm_fixture, pub_vn_ri):
        for cn in self.inputs.bgp_ips:
            cn_routes=self.cn_inspect[cn].get_cn_route_table_entry(ri_name= pub_vn_ri, prefix= fip+'/32')
            if not cn_routes :
                self.logger.warn('No route found for %s in Control-node %s ' %(fip, cn ) )
                return False
            if cn_routes[0]['next_hop'] != vm_fixture.vm_node_ip :
                self.logger.warn( 'Expected next-hop for %s in Control-node %s : %s, Found : %s' %( fip, cn, vm_fixture.vm_node_ip, cn_routes[0]['next_hop'] ) )
                return False
            if cn_routes[0]['label'] != vm_fixture.agent_label[ vm_fixture.vn_fq_name ] :
                self.logger.warn( 'Expected label for %s in Control-node %s : %s, Found : %s' %( fip, cn, vm_fixture.agent_label[ vm_fixture.vn_fq_name ], cn_routes[0]['label'] ) )
                return False
            self.logger.info(' Route for FIP %s is fine on Control-node %s ' %(fip, cn) )
        #end for
        self.logger.info('FIP %s verification for passed on all Control-nodes' %(fip ) )
        return True
    #end verify_fip_in_control_node

    @retry(delay=5, tries=3)
    def verify_fip_not_in_control_node( self, fip, pub_vn_ri ) :
        for cn in self.inputs.bgp_ips:
            cn_routes=self.cn_inspect[cn].get_cn_route_table_entry(ri_name= pub_vn_ri, prefix= fip+'/32')
            if cn_routes:
                self.logger.warn(' FIP %s is still found in route table for Control node %s' %( fip, cn ) )
                return False
            self.logger.info('FIP %s is removed from route table for Control node %s' %( fip, cn ))
        return True
    #verify_fip_not_in_control_node

    @retry(delay=5, tries=3)
    def verify_fip_in_agent(self, fip, vm_fixture, pub_vn_name):
        for compute_ip in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[ compute_ip ]
            vn= inspect_h.get_vna_vn(project='default-project', vn_name= pub_vn_name)
            if vn is None:
                continue
            agent_vrf_objs= inspect_h.get_vna_vrf_objs(domain = 'default-domain',
                project = 'default-project', vn_name= '__default_Public__')
            pub_vrf_name = 'default-domain:default-project:__default_Public__:__default_Public__'
            agent_vrf_obj= self.get_matching_vrf( agent_vrf_objs['vrf_list'], pub_vrf_name )
            agent_vrf_id= agent_vrf_obj['ucindex']
            agent_path= inspect_h.get_vna_active_route( vrf_id= agent_vrf_id, ip= fip, prefix='32')
            agent_label= agent_path['path_list'][0]['label']
            if agent_label != vm_fixture.agent_label[ vm_fixture.vn_fq_name ] :
                self.logger.warn('The route for VM IP %s in Node %s is having incorrect label. Expected : %s, Seen : %s' %( vm_fixture.vm_ip, compute_ip, vm_fixture.agent_label[ vm_fixture.vn_fq_name ], agent_label ) )
                return False

            self.logger.debug('Route for FIP IP %s is present in agent %s ' %( fip, compute_ip ) )
            self.logger.debug('FIP %s verification for VM %s  in Agent %s passed ' %( fip, vm_fixture.vm_name, compute_ip ) )
            return True
        else:
            return False
        #end for
    #end verify_fip_in_agent

    @retry(delay=5, tries=3)
    def verify_fip_in_uve(self, fip, vm_fixture, vn_fixture):
        found_ip = 0
        found_vn = 0
        result = False
        #self.analytics_obj=AnalyticsVerification(inputs= self.inputs,connections= self.connections)
        vm_intf=self.analytics_obj.get_ops_vm_uve_interface(collector=self.inputs.collector_ips[0], uuid=vm_fixture.vm_instance_name)
        for item in vm_intf:
            for item1 in item['floating_ips']:
                if item1['ip_address'] == fip: found_ip = 1
            if item['virtual_network'] == vn_fixture.vn_fq_name:found_vn =1
        if found_ip and found_vn:
            self.logger.info('FIP  %s and Source VN %s found in %s UVE' %( fip,vn_fixture.vn_name,vm_fixture.vm_name))
            result = True
        else:
            self.logger.warn('FIP  %s and/or Source VN %s NOT found in %s UVE' %( fip,vn_fixture.vn_name,vm_fixture.vm_name))
        return result
    # end verify_fip_in_uve

    @retry(delay=5, tries=3)
    def verify_fip_not_in_agent(self, fip, pub_vn_name):
        for compute_ip in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[ compute_ip ]
            vn= inspect_h.get_vna_vn(vn_name= pub_vn_name)
            if vn is None:
                continue
            agent_vrf_objs= inspect_h.get_vna_vrf_objs(vn_name= pub_vn_name)
            agent_vrf_obj= self.get_matching_vrf( agent_vrf_objs['vrf_list'], pub_vn_name )
            agent_vrf_id= agent_vrf_obj['ucindex']
            if inspect_h.get_vna_active_route( vrf_id= agent_vrf_id, ip= fip, prefix='32'):
                self.logger.warn('Route for FIP %s present in Agent %s' %(fip, compute_ip ) )
                return False
            self.logger.info( 'Route for FIP %s is removed from agent %s' %( fip, compute_ip ))
        return True
    #end verify_fip_not_in_agent

    def get_matching_vrf(self, vrf_objs, vrf_name ):
        return [ x for x in vrf_objs if x['name'] == vrf_name ][0]

    def disassoc_and_delete_fip(self, ipaddress_id):
        ''' Disassociate and then delete the Floating IP .
        Strongly recommeded to call verify_no_fip() after this call
        '''
        self.disassoc_floatingip(ipaddress_id)
        self.delete_floatingip(ipaddress_id)
        time.sleep(20)
    #end disassoc_and_delete_fip

    def create_floatingips(self, fip_pool_vn_id, count= 1):
        ''' Creates 1 or more floating ips from a pool.

        '''
        raise NotImplementedError
    #end create_floatingips

    def create_floatingip(self, vn_id):
        ''' Creates a single floating ip from a pool.

        '''
        try:
            response = self.cs_client.request('associateIpAddress', { 'networkid': vn_id })
            self.logger.debug('Response on calling associateIpAddress : %s ' %(response))
            cs_fip_obj = response['queryasyncjobresultresponse']['jobresult']['ipaddress']
            return cs_fip_obj
        except CloudClient.Error,e:
            self.logger.exception("Exception while creating FIP to a Guest VN %s" %(vn_id) )
            return None
    #end create_floatingip

    def verify_fip_in_api_server(self, fip_id ):
        ''' Verify floating ip presence and links in API Server

        '''
        cs_fip_obj= self.api_s_inspect.get_cs_fip( fip_id, refresh = True)
        if not cs_fip_obj:
            return False
        self.logger.info('FIP ID %s verification passed in API server' %(fip_id))
        return True
    #end

    def verify_fip_not_in_api_server(self, fip_id ):
        ''' Verify floating ip removed in API Server
        '''
        cs_fip_obj= self.api_s_inspect.get_cs_fip( fip_id, refresh = True)
        if  cs_fip_obj:
            return False
        self.logger.info('FIP removal verification passed in API server')
        return True
    #end

    def delete_floatingips(self, fip_obj_list ):
        ''' Removes floating ips from a pool. Need to pass a floatingIP object-list

        '''
        raise NotImplementedError
    #end delete_floatingips

    def delete_floatingip(self, ipaddress_id):
        '''
        ipaddress_id is the cloudstack ip-address id
        '''
        try:
            response = self.cs_client.request('disassociateIpAddress',
                {   'id' : ipaddress_id,
                })
            response = response['queryasyncjobresultresponse']
            if not response['jobresult']['success'] :
                self.logger.error('Deleting FIP ID %s seems to have failed ' %(ipaddress_id) )
                self.logger.debug(response)
            self.logger.debug('Response to disassociateIpAddress : %s' %(response))
            return response
        except CloudClient.Error,e:
            self.logger.exception("Exception while disassociating Public IPAddress ID %s from Guest VN " %(ipaddress_id))
            return None
    #end delete_floatingip

    def assoc_floatingip(self, ipaddress_id, vm_id ):
        '''
        ipaddress_id is the Cloudstack IPaddress object id
        vm_id is the VM ID to which floating ip should be associated with
        '''
        try:
            response = self.cs_client.request('enableStaticNat',
                {   'ipaddressid' : ipaddress_id,
                    'virtualmachineid' : vm_id,
                })
            self.logger.debug('Response to enableStaticNat : %s' %(response) )
            return response
        except CloudClient.Error,e:
            self.logger.exception("Exception while associating FIP to a Guest VM %s" %(vm_id) )
            return None
    #end assoc_floatingip

    def disassoc_floatingip(self, ipaddress_id):
        '''
        ipaddress_id is the Cloudstack IPaddress object id
        '''
        try:
            response = self.cs_client.request('disableStaticNat',
                {   'ipaddressid' : ipaddress_id,
                })
            response = response['queryasyncjobresultresponse']
            if not response['jobresult']['success'] :
                self.logger.error('Disassociating FIP ID %s from VM ' %(ipaddress_id) )
            self.logger.debug('Resnpose to disableStaticNat : %s' %(response) )
            return response
        except CloudClient.Error,e:
            self.logger.exception("Exception while disassociating Public IPAddress ID %s to the guest VM")
            return None
    #end

    def cleanUp(self):
        super(CSFloatingIPFixture, self).cleanUp()
        do_cleanup= True
        if self.inputs.fixture_cleanup == 'no' : do_cleanup = False
        if self.already_present : do_cleanup= False
        if self.inputs.fixture_cleanup == 'force' : do_cleanup = True
#        if do_cleanup :
#            self.logger.info('Deleting the FIP pool %s' %(self.pool_name) )
#            self.delete_floatingip_pool()
#            if self.verify_is_run:
#                assert self.verify_fip_pool_not_in_control_node()
#        else :
#            self.logger.info('Skipping deletion of FIP pool %s' %(self.pool_name) )
    #end cleanUp

