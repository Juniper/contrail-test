import fixtures
from vnc_api.vnc_api import *
from cfgm_common import exceptions as vncExceptions
from project_test import *
import time
from contrail_fixtures import *
import ast
import sys
from tcutils.util import retry
try:
    from webui_test import *
except ImportError:
    pass

#@contrail_fix_ext ()

class FloatingIPFixture(fixtures.Fixture):

    def __init__(self, inputs=None, pool_name=None, vn_id=None,
                 connections=None, vn_name=None, project_name=None,
                 option=None, uuid=None):
        self.connections = connections
        self.inputs = inputs or connections.inputs
        if not project_name:
            project_name = self.inputs.project_name
        self.api_s_inspect = self.connections.api_server_inspect
        self.orch = self.connections.orch
        self.quantum_h = self.connections.quantum_h
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.vnc_lib_h = self.connections.vnc_lib
        self.analytics_obj = self.connections.analytics_obj

        self.project_name = project_name
        self.domain_name = self.inputs.domain_name
        self.vn_id = vn_id
        self.vn_name = vn_name
        self.logger = self.inputs.logger
        self.already_present = False
        self.verify_is_run = False
        self.fip = {}
        self.option = option
        self.fip_pool_id = uuid
        if self.option == 'neutron':
            pool_name = 'floating-ip-pool'
        self.pool_name = pool_name or 'floating-ip-pool'
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
    # end __init__

    def read(self):
        if self.fip_pool_id:
            self.fip_pool_obj = self.vnc_lib_h.floating_ip_pool_read(id=self.fip_pool_id)
            self.fq_name = self.get_fq_name()
            self.pool_name = self.fq_name[-1]
            self.vn_fq_name = self.fq_name[:-1]
            self.vn_id = self.vnc_lib_h.fq_name_to_id('virtual-network', self.vn_fq_name)
            self.pub_vn_name = self.vn_fq_name[-1]
            self.logger.info('Fetched FIP pool %s(%s)' %(self.fq_name, self.fip_pool_id))
            self.already_present = True
    # end read

    def setUp(self):
        super(FloatingIPFixture, self).setUp()
        self.create()
    # end setUp

    def create(self):
        if self.fip_pool_id:
            return self.read()
        self.project_obj = self.get_project_obj()
        if not self.is_fip_pool_present(self.pool_name):
            if self.inputs.is_gui_based_config():
                self.create_floatingip_pool_webui(self.pool_name, self.vn_name)
            else:
                self.create_floatingip_pool(self.pool_name, self.vn_id)
        else:
            self.logger.debug('FIP pool %s already present, not creating it' %
                              (self.pool_name))
            self.already_present = True

    def get_project_obj(self):
        if not getattr(self, 'project_obj', None):
            self.project_obj = self.vnc_lib_h.project_read(fq_name=[self.domain_name, self.project_name])
        return self.project_obj

    def create_floatingip_pool_webui(self, pool_name, vn_name):
        self.webui.create_floatingip_pool(self, pool_name, vn_name)
    # end create_floatingip_pool_webui

    def create_and_assoc_fip_webui(self, fip_pool_vn_id, vm_id, vm_name, project=None):
        self.webui.create_and_assoc_fip(
            self, fip_pool_vn_id, vm_id, vm_name, project=None)
    # end create_and_assoc_fip_webui

    def verify_on_setup(self):
        result = True
        if not self.verify_fip_pool_in_api_server():
            result &= False
            self.logger.error(
                ' Verification of FIP pool %s in API Server failed' %
                (self.pool_name))
        if not self.verify_fip_pool_in_control_node():
            result &= False
            self.logger.error(
                ' Verification of FIP pool %s in Control-node failed' %
                (self.pool_name))
        self.verify_is_run = True
        return result
    # end verify_on_setup

    def create_floatingip_pool(self, fip_pool_name, vn_id):
        self.logger.info('Creating Floating IP pool %s in API Server' %
                         (fip_pool_name))

        # create floating ip pool from public network
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read(id=vn_id)
        self.pub_vn_name = self.pub_vn_obj.name
        self.fip_pool_obj = FloatingIpPool(fip_pool_name, self.pub_vn_obj)
        self.fip_pool_id = self.vnc_lib_h.floating_ip_pool_create(
            self.fip_pool_obj)

        # allow current project to pick from pool
        self.project_obj = self.get_project_obj()
        self.project_obj.add_floating_ip_pool(self.fip_pool_obj)
        self.vnc_lib_h.project_update(self.project_obj)
    # end create_floatingip_pool

    def is_fip_pool_present(self, pool_name):
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
        self.pub_vn_name = self.pub_vn_obj.name
        try:
            fip_pool_dict = self.vnc_lib_h.floating_ip_pools_list(
                parent_id=self.vn_id)
            # Bug 532
            if not fip_pool_dict['floating-ip-pools']:
                return False

            fip_fq_name = None
            for pool in fip_pool_dict['floating-ip-pools']:
                if pool['fq_name'][-1] == pool_name:
                    fip_fq_name = pool['fq_name']
                    break    
            else:
                return False
 
            if fip_fq_name:
                self.fip_pool_obj = self.vnc_lib_h.floating_ip_pool_read(
                    fq_name=fip_fq_name)
                self.fip_pool_id = self.fip_pool_obj.uuid
        except vncExceptions.HttpError:
            return None
        return True
    # end get_fip_pool_if_present

    def get_uuid(self):
        return self.fip_pool_id

    def get_fq_name(self):
        return self.fip_pool_obj.get_fq_name()

    def get_vn_id(self):
        return self.vn_id

    @retry(delay=2, tries=15)
    def verify_fip_pool_in_api_server(self):
        result = True
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
        self.pub_vn_name = self.pub_vn_obj.name
        self.cs_fip_pool_obj = self.api_s_inspect.get_cs_alloc_fip_pool(
            fip_pool_name=self.pool_name,
            vn_name=self.pub_vn_obj.name, project=self.project_name, refresh=True)
        if not self.cs_fip_pool_obj:
            self.logger.warn("Floating IP pool %s not found in API Server " %
                             (self.pool_name))
            result = result and False
            return result
        self.cs_fip_pool_id = self.cs_fip_pool_obj['floating-ip-pool']['uuid']
        self.cs_fvn_obj = self.api_s_inspect.get_cs_vn(
            vn=self.pub_vn_obj.name, refresh=True, project=self.project_name)
        if result:
            self.logger.info(
                'FIP Pool verificatioin in API Server passed for Pool %s' %
                (self.pool_name))
        return result
    # end verify_fip_pool_in_api_server
    
    @retry(delay=2, tries=15)
    def verify_fip_pool_in_control_node(self):
        result = True
        self.pub_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
        self.pub_vn_name = self.pub_vn_obj.name
        for cn in self.inputs.bgp_ips:
            cn_object = self.cn_inspect[cn].get_cn_config_fip_pool(
                vn_name=self.pub_vn_name, fip_pool_name=self.pool_name, project=self.project_name)
            if not cn_object:
                self.logger.warn(
                    "Control-node ifmap object for FIP pool %s , VN %s not found" %
                    (self.pool_name, self.pub_vn_name))
                result = result and False
            else:
                self.logger.debug(
                    'Control-node Ifmap-view has FIP pool %s information' % (self.pool_name))

        return result
    # end verify_fip_pool_in_control_node

    def delete_floatingip_pool(self):
        fip_pool_id = self.fip_pool_id
        fip_pool_obj = self.vnc_lib_h.floating_ip_pool_read(id=fip_pool_id)
        self.project_obj = self.get_project_obj()
        self.project_obj.del_floating_ip_pool(fip_pool_obj)
        self.vnc_lib_h.project_update(self.project_obj)
        self.vnc_lib_h.floating_ip_pool_delete(id=fip_pool_id)
    # end delete_floatingip_pool

    @retry(delay=5, tries=3)
    def verify_fip_pool_not_in_control_node(self):
        result = True
        for cn in self.inputs.bgp_ips:
            cn_object = self.cn_inspect[cn].get_cn_config_fip_pool(
                vn_name=self.pub_vn_name, fip_pool_name=self.pool_name, project=self.project_name)
            if cn_object:
                self.logger.warn(
                    "Control-node ifmap object for FIP pool %s , VN %s is found!" %
                    (self.pool_name, self.pub_vn_name))
                result = result and False
            else:
                self.logger.debug(
                    'Control-node Ifmap-view does not have FIP pool %s information' % (self.pool_name))
        return result
    # end verify_fip_pool_not_in_control_node

    def get_associated_fips(self):
        fips_dict = self.fip_pool_obj.get_floating_ips()
        return [fip['uuid'] for fip in fips_dict]

    def create_and_assoc_fip(self, fip_pool_vn_id=None, vm_id=None, project=None):
        ''' Create and associate a floating IP to a VM with vm_id from VN fip_pool_vn_id

        Recommended to call verify_fip() after this method to make sure that the floating IP is correctly installed
        '''
        fip_pool_vn_id = fip_pool_vn_id or self.vn_id
        try:
            fip_obj = self.create_floatingip(fip_pool_vn_id, project)
            self.logger.debug('Associating FIP %s to %s' %(fip_obj[0], vm_id))
            self.assoc_floatingip(fip_obj[1], vm_id)
            return fip_obj[1]
        except:
            self.logger.error('Failed to create or asscociate FIP. Error: %s' %
                              (sys.exc_info()[0]))
            return None
    # end create_and_assoc_fip

    def verify_fip(self, fip_id, vm_fixture, fip_vn_fixture):
        result = True
        fip = self.orch.get_floating_ip(fip_id)
        self.fip[fip_id] = fip
        if not self.verify_fip_in_control_node(fip, vm_fixture, fip_vn_fixture):
            result &= False
        if not self.verify_fip_in_agent(fip, vm_fixture, fip_vn_fixture):
            result &= False
        if not self.verify_fip_in_api_server(fip_id):
            result &= False
        return result
    # end verify_fip

    def verify_no_fip(self, fip_id, fip_vn_fixture, fip=None):
        result = True
        fip = fip or self.fip[fip_id]
        if not self.verify_fip_not_in_control_node(fip, fip_vn_fixture):
            self.logger.error(
                'FIP %s absense verification failed on one or more control-nodes' % (fip))
            result &= False
        if not self.verify_fip_not_in_agent(fip, fip_vn_fixture):
            self.logger.error(
                'FIP %s absense verification failed on one or more agents ' % (fip))
            result &= False
            self.logger.error(
                'FIP %s absense verification failed on API server ' % (fip))
        if not self.verify_fip_not_in_api_server(fip_id):
            result &= False
        return result
    # end verify_no_fip

    @retry(delay=5, tries=3)
    def verify_fip_in_control_node(self, fip, vm_fixture, fip_vn_fixture):
        self.ctrl_nodes= vm_fixture.get_ctrl_nodes_in_rt_group()
        agent_label = vm_fixture.get_agent_label()
        for cn in self.ctrl_nodes:
            ri_name = fip_vn_fixture.get_vrf_name()
            cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                        ri_name=ri_name, prefix=fip)
            if not cn_routes:
                self.logger.warn('No route found for %s in Control-node %s ' %
                                 (fip, cn))
                return False
            if cn_routes[0]['next_hop'] != vm_fixture.get_compute_host():
                self.logger.warn(
                    'Expected next-hop for %s in Control-node %s : %s, Found : %s' %
                    (fip, cn, vm_node_data_ip, cn_routes[0]['next_hop']))
                return False
            if cn_routes[0]['label'] not in agent_label[vm_fixture.vn_fq_name]:
                self.logger.warn(
                    'Expected label for %s in Control-node %s : %s, Found : %s' %
                    (fip, cn, agent_label[vm_fixture.vn_fq_name], cn_routes[0]['label']))
                return False
            self.logger.info(' Route for FIP %s is fine on Control-node %s ' %
                             (fip, cn))
        # end for
        self.logger.info(
            'FIP %s verification for passed on all Control-nodes' % (fip))
        return True
    # end verify_fip_in_control_node

    @retry(delay=5, tries=3)
    def verify_fip_not_in_control_node(self, fip, fip_vn_fixture):
        for cn in self.inputs.bgp_ips:
            ri_name = fip_vn_fixture.get_vrf_name()
            cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                        ri_name=ri_name, prefix=fip)
            if cn_routes:
                self.logger.warn(
                    ' FIP %s is still found in route table for Control node %s' % (fip, cn))
                return False
            self.logger.info(
                'FIP %s is removed from route table for Control node %s' % (fip, cn))
        return True
    # verify_fip_not_in_control_node

    @retry(delay=5, tries=3)
    def verify_fip_in_agent(self, fip, vm_fixture, fip_vn_fixture):
        label = vm_fixture.get_agent_label()
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(vn_name=fip_vn_fixture.vn_name, project=self.project_name)
            if vn is None:
                continue
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                vn_name=fip_vn_fixture.vn_name, project=self.project_name)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], fip_vn_fixture.get_vrf_name())
            agent_vrf_id = agent_vrf_obj['ucindex']
            agent_path = inspect_h.get_vna_active_route(
                         vrf_id=agent_vrf_id, ip=fip)
            if not agent_path:
                self.logger.debug(
                    'Not able to get active route from agent.Retry...')
                return False
            agent_label = agent_path['path_list'][0]['label']
            self.logger.debug('agent_label query returned:%s' %
                              agent_path['path_list'][0])
            if not agent_label:
                self.logger.debug(
                    'Not able to retrieve label value from agent.Retry...')
                return False
            if agent_label not in label[vm_fixture.vn_fq_name]:
                self.logger.warn(
                    'The route for VM IP %s in Node %s is having incorrect label. Expected : %s, Seen : %s' %
                    (vm_fixture.vm_ip, compute_ip, label[vm_fixture.vn_fq_name], agent_label))
                return False

            self.logger.debug('Route for FIP IP %s is present in agent %s ' %
                              (fip, compute_ip))
            self.logger.debug(
                'FIP %s verification for VM %s  in Agent %s passed ' %
                (fip, vm_fixture.vm_name, compute_ip))
        # end for
        return True
    # end verify_fip_in_agent

    @retry(delay=5, tries=6)
    def verify_fip_in_uve(self, fip, vm_fixture, fip_vn_fixture):
        found_ip = 0
        found_vn = 0
        result = False
        vm_intf = self.analytics_obj.get_ops_vm_uve_interface(
            collector=self.inputs.collector_ip, uuid=vm_fixture.vm_id)
        for item in vm_intf:
            try:
                intf = self.analytics_obj.get_intf_uve(item)
                for item1 in intf['floating_ips']:
                    ip_list = [item1['ip_address']]
                    if item1.has_key('ip6_address'):
                        ip_list.extend([item1['ip6_address']])
                    if fip in ip_list:
                        found_ip = 1
                    if item1['virtual_network'] == fip_vn_fixture.vn_fq_name:
                        found_vn = 1
            except Exception as e:
                self.logger.exception("Exception: %s"%e)
                return False
                            
        if found_ip and found_vn:
            self.logger.info('FIP  %s and Source VN %s found in %s UVE' %
                             (fip, fip_vn_fixture.vn_name, vm_fixture.vm_name))
            result = True
        else:
            self.logger.warn(
                'FIP  %s and/or Source VN %s NOT found in %s UVE' %
                (fip, fip_vn_fixture.vn_name, vm_fixture.vm_name))
        return result
    # end verify_fip_in_uve

    @retry(delay=5, tries=3)
    def verify_fip_not_in_agent(self, fip, fip_vn_fixture):
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(vn_name=fip_vn_fixture.vn_name, project=self.project_name)
            if vn is None:
                continue
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                vn_name=fip_vn_fixture.vn_name, project=self.project_name)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], fip_vn_fixture.get_vrf_name())
            agent_vrf_id = agent_vrf_obj['ucindex']
            if inspect_h.get_vna_active_route(vrf_id=agent_vrf_id, ip=fip):
                self.logger.warn('Route for FIP %s present in Agent %s' %
                                 (fip, compute_ip))
                return False
            self.logger.info('Route for FIP %s is removed from agent %s' %
                             (fip, compute_ip))
        return True
    # end verify_fip_not_in_agent

    def get_matching_vrf(self, vrf_objs, vrf_name):
        return [x for x in vrf_objs if x['name'] == vrf_name][0]

    def disassoc_and_delete_fip(self, fip_id):
        ''' Disassociate and then delete the Floating IP .
        Strongly recommeded to call verify_no_fip() after this call
        '''
        self.disassoc_floatingip(fip_id)
        self.delete_floatingip(fip_id)
#        time.sleep(10)
    # end disassoc_and_delete_fip

    def disassoc_and_delete_fip_webui(self, vm_id):
        self.webui.disassoc_floatingip(self, vm_id)
    # end disassoc_and_delete_fip_webui

    def create_floatingips(self, fip_pool_vn_id, count=1):
        ''' Creates 1 or more floating ips from a pool.

        '''
        # allocate 'count' number of floating ips
        fip_dicts = []
        for i in range(count):
            fip_resp = self.create_floatingip(fip_pool_vn_id)
            if fip_resp:
                fip_dicts.append(fip_resp['floatingip'])
        # end for
        return fip_dicts
    # end create_floatingips

    def create_floatingip(self, fip_pool_vn_id, project_obj=None):
        ''' Creates a single floating ip from a pool.

        '''
        if project_obj is None:
            project_obj = self.get_project_obj()
        fip_resp = self.orch.create_floating_ip(pool_vn_id=fip_pool_vn_id,
                     project_obj=project_obj, pool_obj=self.fip_pool_obj)
        self.logger.debug('Created Floating IP : %s' % str(fip_resp))
        return fip_resp
    # end create_floatingip

    def verify_fip_in_api_server(self, fip_id):
        ''' Verify floating ip presence and links in API Server

        '''
        cs_fip_obj = self.api_s_inspect.get_cs_fip(fip_id, refresh=True)
        if not cs_fip_obj:
            return False
        self.logger.info('FIP verification passed in API server')
        return True
    # end

    def verify_fip_not_in_api_server(self, fip_id):
        ''' Verify floating ip removed in API Server
        '''
        cs_fip_obj = self.api_s_inspect.get_cs_fip(fip_id, refresh=True)
        if cs_fip_obj:
            return False
        self.logger.info('FIP removal verification passed in API server')
        return True
    # end

    def delete_floatingips(self, fip_obj_list):
        ''' Removes floating ips from a pool. Need to pass a floatingIP object-list

        '''
        for i in fip_obj_list:
            index = fip_obj_list.index(i)
            self.delete_floatingip(fip_obj_list[index]['id'])
        # end for
    # end delete_floatingips

    def delete_floatingip(self, fip_id):
        self.logger.debug('Deleting FIP ID %s' %(fip_id))
        self.orch.delete_floating_ip(fip_id)
    # end delete_floatingip

    def assoc_floatingip(self, fip_id, vm_id):
        return self.orch.assoc_floating_ip(fip_id, vm_id)
    # end assoc_floatingip

    def disassoc_floatingip(self, fip_id):
        return self.orch.disassoc_floating_ip(fip_id)
    # end

    def assoc_project(self, project, domain='default-domain'):
        result = True
        self.logger.info('Associting Floting IP with project %s' % (project))

        # Create the project object
        project_fq_name = [domain, project]
        self.new_project_obj = self.vnc_lib_h.project_read(
            fq_name=project_fq_name)

        # Associate project with floating IP pool
        result = self.new_project_obj.add_floating_ip_pool(
            self.fip_pool_obj)
        self.vnc_lib_h.project_update(self.new_project_obj)
        self.new_project_obj = self.vnc_lib_h.project_read(
            fq_name=project_fq_name)
        return self.new_project_obj
    # end assoc_project

    def deassoc_project(self, project, domain='default-domain'):
        result = True
        self.logger.info('De-associting Floting IP with project %s' %
                         (project))

        # Create the project object
        project_fq_name = [domain, project]
        self.new_project_obj = self.vnc_lib_h.project_read(
            fq_name=project_fq_name)

        # Deassociate project with floating IP pool
        result = self.new_project_obj.del_floating_ip_pool(
            self.fip_pool_obj)
        self.vnc_lib_h.project_update(self.new_project_obj)
        self.new_project_obj = self.vnc_lib_h.project_read(
            fq_name=project_fq_name)
        return self.new_project_obj
    # end assoc_project

    def cleanUp(self):
        super(FloatingIPFixture, self).cleanUp()
        self.delete()
    # end cleanUp

    def delete(self, verify=False):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.logger.info('Deleting the FIP pool %s' %
                             (self.pool_name))
            if self.inputs.is_gui_based_config():
                self.webui.delete_floatingip_pool(self)
            else:
                self.delete_floatingip_pool()
            if self.verify_is_run or verify:
                assert self.verify_fip_pool_not_in_control_node()
            else:
                self.logger.info('Skipping deletion of FIP pool %s' %
                                 (self.pool_name))
