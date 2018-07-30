import vnc_api_test
from compute_node_test import ComputeNodeFixture
from tcutils.util import get_random_name, retry
from contrailapi import ContrailVncApi
from vnc_api.vnc_api import *


class LogicalRouterFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Logical Router object
    
    Optional:
    :param name : name of the logical router
    :param uuid : UUID of the logical router
                  One of router name or router id is mandatory
    :param public_vn_id : uuid of the public gateway network
    :param private: dict of list of private vn_ids or subnet_ids or port_ids
                    {'vns': ['...', '...'], 'subnets': ['...'], 'ports':['...']}
    :param api_type     : one of 'neutron'(default) or 'contrail'
    :param vni    : vxlan network identifier 
    :param route_targets      : route targets as list input 
    :param physical_router    : physical router id (uuid)

    Inherited optional parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1


    @staticmethod
    def __new__ (cls, api_type='neutron', **kwargs):
        cls.__bases__ = (eval(api_type), ) + cls.__bases__
        return super(LogicalRouterFixture, cls).__new__(cls, **kwargs)
    '''

    def __init__(self, **kwargs):
        super(LogicalRouterFixture, self).__init__(self, **kwargs)
        self.lr_name = kwargs.get('name', get_random_name('Router'))
        self.uuid = kwargs.get('uuid', None)
        self.public_vn_id = kwargs.get('public_vn_id', None)
        self.private = kwargs.get('private', None)
        self.api_type = kwargs.get('api_type', 'contrail')
        self.already_present = False
        self.ports = []; self.vns = []; self.subnets = []
        self.deleted_vn_ids = []
        self.vn_ids = set()
        self.is_gw_active = False
        self.vni = kwargs.get('vni', None)
        self.route_targets = kwargs.get('route_targets', [])
        self.rt_list = set()
        self.logger.info('VNI to be configured on Logical Router %s'%self.vni)
        self.physical_router = kwargs.get('physical_router', None)

        
        # temporary place till vnc_api_test is re-done
        super(LogicalRouterFixture, self).setUp()
        self.network_h = self.get_network_handle()
        self.vnc_api_h = self.get_handle()
        self.vnc_h = ContrailVncApi(self.vnc_api_h, self.logger)
        if self.uuid:
            self.read(self.uuid)
        self.parent_fq_name = [self.domain, self.project_name]
        self.project_object = self.vnc_h.read_project_obj(project_fq_name=self.parent_fq_name) 
        self.lr_fq_name = self.parent_fq_name + [self.lr_name]
        self.parent_type = 'project'

    def setUp(self):
        super(LogicalRouterFixture, self).setUp()
        self.create()

    def cleanUp(self):
        self.read(self.uuid)
        vmi_ref_list = self.obj.get_virtual_machine_interface_refs()
        #self.delete()
        #if vmi_ref_list:
        #    for each_vmi in vmi_ref_list:
        #        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=each_vmi['uuid'])
        #        ip_refs = vmi_obj.get_instance_ip_back_refs()
        #        ip_obj = self.vnc_api_h.instance_ip_read(id=ip_refs[0]['uuid'])
        #        ip_refs = vmi_obj.get_instance_ip_back_refs()
        #        self.vnc_api_h.instance_ip_delete(id=ip_refs[0]['uuid'])
        #        self.vnc_api_h.virtual_machine_interface_delete(id=each_vmi['uuid'])

        if (self.already_present or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Logical Router %s :'
                              %(self.lr_fq_name))
        else:
            self.delete()
            super(LogicalRouterFixture, self).cleanUp()

    
    def get_network_handle(self):
        if self.api_type == 'contrail':
            return self.get_handle()
        else:
            return self.get_neutron_handle()

    def read(self, uuid):
        self.logger.debug('Fetching information about Logical Router %s'%uuid)


        self.obj = self.vnc_api_h.logical_router_read(fq_name=self.lr_fq_name)
        self.uuid = self.obj.uuid

        #public_vn_id = self.obj.get('external_gateway_info', None) and \
        #               self.obj['external_gateway_info'].get('network_id', None)
        #if public_vn_id:
        #    self.public_vn_id = public_vn_id
            
        # updating vn lists
        vmi_ref_list = self.obj.get_virtual_machine_interface_refs()
        if vmi_ref_list:
            for each_vmi in vmi_ref_list:
                vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=each_vmi['uuid'])
                vn_refs = vmi_obj.get_virtual_network_refs()
                for each_vn in vn_refs:
                    self.vn_ids.add(each_vn['uuid'])
        rt_ref_list = self.obj.get_route_target_refs()
        self.rt_list = set()
        if rt_ref_list:
            for each_rt_ref in rt_ref_list:
                rt_obj = self.vnc_api_h.route_target_read(id=each_rt_ref['uuid'])
                self.rt_list.add(rt_obj.get_fq_name()[0])
        
        self.logger.info('LR: %s, members: %s, gw: %s'%(self.lr_name,
                                   self.get_vn_ids(), self.public_vn_id))

    def create(self):
        if not self.verify_if_lr_already_present(self.lr_fq_name, self.project_object):
            self.logger.info('Creating Logical router %s'%self.lr_name)
            self.obj = self.vnc_h.create_router(self.lr_name, self.project_object)
            self.uuid = self.obj.uuid
        else:
            self.already_present = False
            self.obj = self.vnc_api_h.logical_router_read(fq_name=self.lr_fq_name)
            self.uuid = self.obj.uuid
            self.read(self.uuid)
                    
        pre_vn_ids = self.get_vn_ids()

        # Adding Virtaul Networkds 
        if self.private:
            for vn_id in self.private.get('vns', []):
                if not (pre_vn_ids and (vn_id in pre_vn_ids)):
                    self.add_network(vn_id=vn_id)
        # configuring VxLAN Network Identifier for this Logical Router     
        if self.vni:
            self.set_vni(self.vni)

        self.logger.info('LR: %s, members: %s, gw: %s, vni: %s'%(self.lr_name,
                         self.get_vn_ids(), self.public_vn_id, self.vni))

        if self.route_targets:
           for each_rt in self.route_targets:
               self.add_rt(each_rt)

        if self.physical_router:
               self.add_physical_router(self.physical_router)

        #if self.public_vn_id:
        #    self.set_gw()

    def set_vni(self, vni):
        self.logger.info('Configuring routing VNI %s on Logical Router %s ...'%(vni,self.lr_name))
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        lr_obj.set_vxlan_network_identifier(str(vni))
        self.vni = vni
        self.vnc_api_h.logical_router_update(lr_obj)
        self.logger.info('configured routing VNI: %s'%(vni))
   
    def delete_vni(self):
        self.logger.info('Deleting routing VNI %s on Logical Router %s ...'%(self.vni,self.lr_name))
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        lr_obj.set_vxlan_network_identifier(None)
        self.vni = None
        self.vnc_api_h.logical_router_update(lr_obj)
        self.logger.info('Deleted routing VNI: %s'%(self.vni))

    def refresh(self):
        self.read(self.uuid)

    def add_rt(self, rt):
        if rt in self.rt_list:
            self.logger.info('RT %s is already configured on Logical Router %s ...'%(rt,self.lr_name))
            return True

        self.logger.info('Configuring route-target %s on Logical Router %s ...'%(rt,self.lr_name))
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        rt_obj = RouteTarget(name=rt)
        try:
            rt_obj = self.vnc_api_h.route_target_read(fq_name=[rt])
        except Exception as exp:
            self.vnc_api_h.route_target_create(rt_obj)
        lr_obj.add_route_target(rt_obj)
        self.vnc_api_h.logical_router_update(lr_obj)
        self.rt_list.add(rt)
        self.logger.info('configured route-target %s'%(rt))
        return True

    def delete_rt(self, rt):
        if rt not in self.rt_list:
            self.logger.info('Given RT %s is NOT configured on Logical Router %s ...'%(rt,self.lr_name))
            return True

        self.logger.info('Deleting route-target %s on Logical Router %s ...'%(rt,self.lr_name))
        rt_obj = self.vnc_api_h.route_target_read(fq_name=[rt])
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        lr_obj.del_route_target(rt_obj)
        self.vnc_api_h.logical_router_update(lr_obj)
        self.rt_list.remove(rt)
        self.logger.info('Deleted route-target %s'%(rt))


    def set_configured_rt_list(self, rt_list):
        self.logger.info('Configuring configured rt list  %s on Logical Router %s ...'%(rt_list,self.lr_name))
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        rt_obj_list = []
        for each_rt in rt_list:
            rt_obj_list.append(self.create_rt(each_rt))
        lr_obj.set_configured_route_target_list(rt_obj_list)
        self.vnc_api_h.logical_router_update(lr_obj)
        self.logger.info('configured rt list %s'%(rt_obj_list))

    def create_rt(rt_name):
        rt_obj = RouteTarget(name=rt_name)
        try:
            rt_obj = self.vnc_api_h.route_target_read(fq_name=[rt_name])
        except Exception as exp:
            self.vnc_api_h.route_target_create(rt_obj)
        return rt_obj

    def add_network(self, vn_id):

        self.read(self.uuid)        
        if vn_id in self.get_vn_ids():
            self.logger.info('Network %s is already part of the logical Router: %s'%(vn_id,self.lr_name))
            return True

        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        self.logger.info(lr_obj)
        #self.logger.info('Logical Router Object: %s'%(lr_obj))
        #self.logger.info('Logical Router Object: %s'%(str(dir(lr_obj))))
        vn_obj = self.vnc_api_h.virtual_network_read(id=vn_id)
        vmi_name = self.lr_name+'-'+vn_id
        vmi_fq_name = self.parent_fq_name + [vmi_name]
        if not self.verify_if_vmi_already_present(vmi_fq_name, self.project_object):
            vmi_obj = VirtualMachineInterface(name=vmi_name, 
                                                   parent_obj=self.project_object)
            vmi_obj.add_virtual_network(vn_obj)
            self.vnc_api_h.virtual_machine_interface_create(vmi_obj)
            ip_obj = InstanceIp(name=self.lr_name+'-'+vn_id)
            ip_obj.add_virtual_network(vn_obj)
            ip_obj.add_virtual_machine_interface(vmi_obj)
            self.vnc_api_h.instance_ip_create(ip_obj)
        else:
            vmi_obj = self.vnc_api_h.virtual_machine_interface_read(fq_name=vmi_fq_name)
        lr_obj.add_virtual_machine_interface(vmi_obj)
        self.logger.info('VN Object info: %s'%(dir(lr_obj)))
        self.vnc_api_h.logical_router_update(lr_obj)
        self.vn_ids.add(vn_id)
        return True

    def remove_network(self, vn_id):

        found = False
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        vmi_ref_list = lr_obj.get_virtual_machine_interface_refs()
        if vmi_ref_list:
            for each_vmi in vmi_ref_list:
                vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=each_vmi['uuid'])
                vn_refs = vmi_obj.get_virtual_network_refs()
                for each_vn in vn_refs:
                    if each_vn['uuid'] == vn_id:
                        found = True
                        lr_obj.del_virtual_machine_interface(vmi_obj)
                        self.vnc_api_h.logical_router_update(lr_obj)
                        ip_refs = vmi_obj.get_instance_ip_back_refs()
                        ip_obj = self.vnc_api_h.instance_ip_read(id=ip_refs[0]['uuid'])
                        self.vnc_api_h.instance_ip_delete(id=ip_refs[0]['uuid'])
                        self.vnc_api_h.virtual_machine_interface_delete(id=each_vmi['uuid'])
                        self.vn_ids.discard(vn_id)
                        return True
        if found is False:
            self.logger.info('vn-id %s is not found'%(vn_id))
            return True

    def add_physical_router(self, router_id):
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        phy_router_ref_list = lr_obj.get_physical_router_refs()
        phy_router_obj = self.vnc_api_h.physical_router_read(id=router_id)
        lr_obj.add_physical_router(phy_router_obj)
        self.vnc_api_h.logical_router_update(lr_obj)

    def remove_physical_router(self, router_id):
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        phy_router_ref_list = lr_obj.get_physical_router_refs()
        phy_router_obj = self.vnc_api_h.physical_router_read(id=router_id)
        lr_obj.del_physical_router(phy_router_obj)
        self.vnc_api_h.logical_router_update(lr_obj)

    def set_gw(self, gw=None):
        self.public_vn_id = gw or self.public_vn_id
        self.network_h.router_gateway_set(self.uuid, self.public_vn_id)
        self.dyn_ri_on_left = None
        self.active_vm = None
        self.snat_ip = None
        self.label = None
        self.is_gw_active = True

    def clear_gw(self):
        self.network_h.router_gateway_clear(self.uuid)
        self.is_gw_active = False

    def reset_gw(self, gw=None):
        self.clear_gw()
        self.set_gw(gw)

    def delete(self, verify=False):
        self.logger.info('Deleting LogicalRouter %s(%s)'%(self.lr_name, self.uuid))
        self.read(self.uuid)
        vmi_ref_list = self.obj.get_virtual_machine_interface_refs()
        self.vnc_h.delete_router(self.obj)
        #self.uuid = None
        if vmi_ref_list:
            for each_vmi in vmi_ref_list:
                vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=each_vmi['uuid'])
                ip_refs = vmi_obj.get_instance_ip_back_refs()
                ip_obj = self.vnc_api_h.instance_ip_read(id=ip_refs[0]['uuid'])
                ip_refs = vmi_obj.get_instance_ip_back_refs()
                self.vnc_api_h.instance_ip_delete(id=ip_refs[0]['uuid'])
                self.vnc_api_h.virtual_machine_interface_delete(id=each_vmi['uuid'])

    @retry(6, 10)
    def verify_auto_lr_vn_created_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_vn(self.parent_fq_name[0],
                                self.parent_fq_name[1],
                                self.get_auto_lr_vn_name(),
                                refresh=True):
            self.logger.warn('auto lr internal vn(%s) is created in api server'
                                    %self.get_auto_lr_vn_name())
            return True
        self.logger.debug('auto lr internal vn(%s) is not created yet in api server..'%self.get_auto_lr_vn_name())
        return False

    @retry(6, 10)
    def verify_auto_lr_vn_deleted_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_vn(self.parent_fq_name[0],
                                self.parent_fq_name[1],
                                self.get_auto_lr_vn_name(),
                                refresh=True):
            self.logger.warn('auto lr internal vn(%s) is not deleted yet'
                                    %self.get_auto_lr_vn_name())
            return False
        self.logger.debug('auto lr internal vn(%s) got deleted'%self.get_auto_lr_vn_name())


    @retry(6, 10)
    def verify_auto_lr_vn_created_in_cn(self):
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            ri = cn_inspect.get_cn_routing_instance(self.get_auto_lr_vn_name())
            #self.logger.info(str(ri))
            if ri:
                self.logger.warn('auto lr internal vn(%s) is created in control node'
                                    %self.get_auto_lr_vn_name())
                return True
        self.logger.debug('auto lr internal vn(%s) is not created in control node..'%self.get_auto_lr_vn_name())
        return False

    @retry(6, 10)
    def verify_auto_lr_vn_deleted_in_cn(self):
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            ri = cn_inspect.get_cn_routing_instance(self.get_auto_lr_vn_name())
            #self.logger.info(str(ri))
            if ri:
                self.logger.warn('auto lr internal vn(%s) is still exists in control node'
                                    %self.get_auto_lr_vn_name())
                return False
        self.logger.debug('auto lr internal vn(%s) is not exists  in control node..'%self.get_auto_lr_vn_name())
        return True


    @retry(6, 10)
    def verify_auto_lr_vn_created_in_agent(self, node_ip_list=None ):
        self.logger.info('Node IP List: %s'%str(node_ip_list))
        if not node_ip_list: 
            node_ip_list = []
        return_value = True
        for each_node in node_ip_list:
            inspect_h = self.connections.agent_inspect[each_node]
            vrf_id = inspect_h.get_vna_vrf_id(self.get_auto_lr_vn_fq_name())
            if vrf_id:
                self.logger.warn('auto lr internal vn(%s) is available on vrouter agent(%s)'
                                    % (self.get_auto_lr_vn_name(),each_node ))
                
            else:
                self.logger.warn('auto lr internal vn(%s) is not available on vrouter agent(%s)'
                                    % (self.get_auto_lr_vn_name(),each_node ))
                return_value = False

        return return_value

    @retry(6, 10)
    def verify_auto_lr_vn_deleted_in_agent(self, node_ip_list=None ):
        if not node_ip_list:
            node_ip_list = []
        return_value = True
        for each_node in node_ip_list:
            inspect_h = self.connections.agent_inspect[each_node]
            vrf_id = inspect_h.get_vna_vrf_id(self.get_auto_lr_vn_fq_name())
            if vrf_id:
                self.logger.warn('auto lr internal vn(%s) is still available on vrouter agent(%s)'
                                    % (self.get_auto_lr_vn_name(),each_node ))
                return_value = False

            else:
                self.logger.warn('auto lr internal vn(%s) is not available on vrouter agent(%s)'
                                    % (self.get_auto_lr_vn_name(),each_node ))

        return return_value


    def verify_on_cleanup(self, node_ip_list=None):
        self.verify_auto_lr_vn_deleted_in_api_server()
        self.verify_auto_lr_vn_deleted_in_cn()
        if node_ip_list:
            self.verify_auto_lr_vn_deleted_in_agent(node_ip_list)
        #assert self.verify_not_in_api_server()
        #assert self.verify_not_in_agent()
        #assert self.verify_not_in_control_node()
        self.logger.info('LR(%s): verify_on_cleanup passed'%self.uuid)
        return True

    def verify_on_setup(self, node_ip_list=None):
        self.verify_auto_lr_vn_created_in_api_server()
        self.verify_auto_lr_vn_created_in_cn()
        self.logger.info('Node IP List: %s'%str(node_ip_list))
        if node_ip_list:
            self.verify_auto_lr_vn_created_in_agent(node_ip_list)
        #assert self.verify_in_api_server()
        #assert self.verify_in_agent()
        #assert self.verify_in_control_node()
        self.logger.info('LR(%s): verify_on_setup passed'%self.uuid)
        self.verify_is_run = True
        return True

    '''
    @retry(6, 10)
    def verify_lr_rt_not_in_vns_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for vn in self.deleted_vn_ids:
            rt = list()
            for ri in self.api_h.get_cs_routing_instances(vn,
                                 refresh=True)['routing_instances']:
                rt.extend([x['to'][0] for x in ri['routing-instance']['route_target_refs']])
            if self.route_target in rt:
                self.logger.warn('RT(%s) of LR is not yet deleted from'
                                 ' VN %s'%(self.route_target, vn))
                return False
        self.logger.debug('LR rt refs is removed from all private RIs')
        return True

    @retry(6, 10)
    def verify_auto_vn_deleted_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_vn(self.parent_fq_name[0],
                                self.parent_fq_name[1],
                                self.get_auto_vn_name(),
                                refresh=True):
            self.logger.warn('auto vn(%s) is not deleted yet'
                                    %self.get_auto_vn_name())
            return False
        self.logger.debug('auto vn %s got deleted'%self.get_auto_vn_name())
        return True

    @retry(6, 10)
    def verify_auto_lr_vn_deleted_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        if self.api_h.get_cs_vn(self.parent_fq_name[0],
                                self.parent_fq_name[1],
                                self.get_auto_lr_vn_name(),
                                refresh=True):
            self.logger.warn('auto lr internal vn(%s) is not deleted yet'
                                    %self.get_auto_lr_vn_name())
            return False
        self.logger.debug('auto lr internal vn %s got deleted'%self.get_auto_lr_vn_name())

    @retry(6, 10)
    def verify_dyn_ri_on_public_deleted_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        vn_obj = self.api_h.get_cs_vn_by_id(self.public_vn_id, refresh=True)
        ris = [':'.join(ri) for ri in vn_obj.ri_refs()
                            if ri[-1].endswith('si_%s'%self.uuid)]
        if ris:
            self.logger.warn('Dynamic RI on gateway vn is not deleted')
            return False
        self.logger.debug('Dynamic RI on gateway vn is deleted')
        return True

    def verify_not_in_api_server(self):
        self.logger.info('Verify LR(%s) not in api server'%self.uuid)
        if self.deleted_vn_ids:
            assert self.verify_lr_rt_not_in_vns_in_api_server()
        if self.public_vn_id:
            assert self.verify_auto_vn_deleted_in_api_server()
            assert self.verify_dyn_ri_on_public_deleted_in_api_server()
            assert self.verify_lr_got_deleted_in_api_server()
        return True

    @retry(6, 10)
    def verify_snat_ip_got_deleted_in_agent(self):
        vn_fqname = self.id_to_fq_name(self.public_vn_id)
        active_vr = self.get_active_vrouter()
        inspect_h = self.connections.agent_inspect[active_vr]
        route = inspect_h.get_vna_active_route(ip=self.get_snat_ip(),
                                               prefix='32',
                                               vn_fq_name=':'.join(vn_fqname))
        if route:
            self.logger.warn('snat gw ip is still found on public net')
            return False
        self.logger.debug('snat gw ip %s deleted on public'%self.get_snat_ip())
        return True

    def verify_not_in_agent(self):
        assert self.verify_snat_ip_got_deleted_in_agent()
        return True

    @retry(6, 10)
    def verify_not_in_control_node(self):
        vn_fqname = self.id_to_fq_name(self.public_vn_id)
        ri_fqname = vn_fqname + vn_fqname[-1:]
        for ctrl_node in self.inputs.bgp_ips:
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(
                                                prefix=self.get_snat_ip(),
                                                ri_name=':'.join(ri_fqname))
            if routes:
                self.logger.warn('ctrl node %s: gw ip %s not deleted in RI %s'
                                 %(ctrl_node, self.get_snat_ip(), ri_fqname))
                return False
        return True

    def verify_on_cleanup(self):
        assert self.verify_not_in_api_server()
        if self.public_vn_id:
            assert self.verify_not_in_agent()
            assert self.verify_not_in_control_node()
        self.logger.info('LR(%s): verify_on_cleanup passed'%self.uuid)
        return True

    def verify_on_setup(self):
        assert self.verify_in_api_server()
        if self.is_gw_active:
            assert self.verify_in_agent()
            assert self.verify_in_control_node()
        self.logger.info('LR(%s): verify_on_setup passed'%self.uuid)
        self.verify_is_run = True
        return True
    '''

    def get_si_name(self):
        return 'si_'+self.uuid

    def get_table_name(self):
        return 'rt_'+self.uuid

    def get_auto_vn_name(self):
        return 'snat-si-left_'+self.get_si_name()

    def get_auto_lr_vn_name(self):
        return '__contrail_lr_internal_vn_'+self.uuid+'__'

    def get_auto_lr_vn_fq_name(self):
        fq_name_list = []
        fq_name_list.append(self.domain)
        fq_name_list.append(self.project_name)
        fq_name_list.append(self.get_auto_lr_vn_name())
        return ':'.join(fq_name_list)

    def get_rt(self):
        if not getattr(self, 'route_target', None):
            self.api_h = self.connections.api_server_inspect
            rts = self.api_h.get_lr(uuid=self.uuid, refresh=True).get_rt()
            self.route_target = rts[0] if rts else None
        return self.route_target

    def get_vms(self):
        self.api_h = self.connections.api_server_inspect
        return self.api_h.get_cs_si(self.parent_fq_name[0],
                                    self.parent_fq_name[1],
                                    self.get_si_name(), True).get_vms()

    def get_active_standby_instance(self):
        self.active_vm = None; self.standby_vm = None
        self.api_h = self.connections.api_server_inspect
        for vm_id in self.get_vms():
            vmis = self.api_h.get_cs_vmi_of_vm(vm_id, refresh=True)
            pref = vmis[0].properties('local_preference')
            if pref == 200:
               self.active_vm = vm_id
            else:
               self.standby_vm = vm_id
        return (self.active_vm, self.standby_vm)

    def get_standby_instance(self):
        if not getattr(self, 'standby_vm', None):
            self.get_active_standby_instance()
            if not self.standby_vm:
                self.logger.warn('Unable to get standby vm for LR %s'%self.uuid)
        return self.standby_vm

    def get_active_instance(self):
        if not getattr(self, 'active_vm', None):
            self.get_active_standby_instance()
            if not self.active_vm:
                self.logger.warn('Unable to get active vm for LR %s'%self.uuid)
        return self.active_vm

    def get_vn_ids(self, refresh=False):
        return self.vn_ids

    ''' 
    def get_snat_ip(self):
        if not getattr(self, 'snat_ip', None):
            self.snat_ip = None
            self.api_h = self.connections.api_server_inspect
            active_vm = self.get_active_instance()
            if active_vm:
                for iip in self.api_h.get_cs_instance_ips_of_vm(active_vm):
                    if iip.vn_uuid == self.public_vn_id:
                        self.snat_ip = iip.ip
                        break
                if not self.snat_ip:
                    self.logger.warn('Unable to get gw ip for LR %s'%self.uuid)
        return self.snat_ip

    @retry(6, 10)
    def verify_rt_import_on_private_vns_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        for vn in self.get_vn_ids():
            rt = list()
            for ri in self.api_h.get_cs_routing_instances(vn)['routing_instances']:
                rt.extend([x['to'][0]
                          for x in ri['routing-instance']['route_target_refs']])
            if self.get_rt() not in rt:
                self.logger.warn('RT of LR is not imported by VN %s'%vn)
                self.logger.warn('Expected: %s, actual: %s'%(self.get_rt(), rt))
                return False
        self.logger.debug('Logical router rt is imported by all private RIs')
        return True

    @retry(6, 10)
    def verify_dyn_ri_on_public_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        vn_obj = self.api_h.get_cs_vn_by_id(self.public_vn_id)
        ris = [':'.join(ri) for ri in vn_obj.ri_refs()
                            if ri[-1].endswith('si_%s'%self.uuid)]
        if not ris:
            self.logger.warn('Dynamic RI on gateway vn is not available')
            return False
        self.logger.debug('Dynamic RI on gateway vn is created')
        return True

    def get_dyn_ri_on_auto_vn(self):
        if not getattr(self, 'dyn_ri_on_left', None):
            self.api_h = self.connections.api_server_inspect
            vn_obj = self.api_h.get_cs_vn(self.parent_fq_name[0],
                                          self.parent_fq_name[1],
                                          self.get_auto_vn_name(),
                                          refresh=True)
            ris = [':'.join(ri) for ri in vn_obj.ri_refs()
                   if ri[-1].endswith('si_%s'%self.uuid)]
            self.dyn_ri_on_left = ris[0]
        return self.dyn_ri_on_left

    @retry(6, 10)
    def verify_dyn_ri_on_auto_vn_in_api_server(self):
        try:
            ri = self.get_dyn_ri_on_auto_vn()
            self.logger.debug('Dynamic RI on auto vn is %s'%ri)
        except:
            self.logger.warn('Dynamic RI on auto vn is not available')
            return False
        return True if ri else False

    @retry(6, 10)
    def verify_route_tables_in_api_server(self):
        self.api_h = self.connections.api_server_inspect
        self.route_table_fqname = self.parent_fq_name + [self.get_table_name()]
        if not self.get_vn_ids():
            return True
        for vn_id in self.get_vn_ids():
            route_table = self.api_h.get_cs_vn_by_id(vn_id,
                                     refresh=True).route_table()
            if self.route_table_fqname != route_table['to']:
                self.logger.warn('Route tables attached to VN %s is not as '
                                 'expected. Expecting %s: Got %s'%(vn_id,
                                 self.route_table_fqname, route_table['to']))
                return False
            rt_uuid = route_table['uuid']
        for route in self.api_h.get_route_table(rt_uuid).get_route():
            if route['prefix'] != "0.0.0.0/0":
                self.logger.warn('Dont see a static route under route_table %s'
                                 %(self.route_table_fqname))
                return False
        self.logger.debug('RouteTable with static route is imported by all VNs')
        return True

    def verify_in_api_server(self):
        self.logger.debug('LR: Started verify on api server for %s'%self.lr_name)
        if self.get_vn_ids():
            assert self.verify_rt_import_on_private_vns_in_api_server()
        if self.is_gw_active:
            assert self.verify_route_tables_in_api_server()
            assert self.verify_dyn_ri_on_auto_vn_in_api_server()
            assert self.verify_dyn_ri_on_public_in_api_server()
            assert self.verify_instance_launched()
        self.logger.debug('LR: passed verification in api server')
        return True

    @retry(6, 10)
    def verify_instance_launched(self, refresh=False):
        svc_mon_h = self.connections.get_svc_mon_h(refresh)
        if svc_mon_h.get_service_instance(name=self.get_si_name(),
                                          refresh=refresh).is_launched():
            self.logger.debug('LR: SI got launched')
            return True
        self.logger.warn('LR(%s): SI status is not active in svc-mon'%self.uuid)
        return False

    def get_active_vrouter(self, refresh=False):
        if not getattr(self, 'active_vr', None) or refresh:
            svc_mon_h = self.connections.get_svc_mon_h(refresh)
            try:
                self.active_vr = self.inputs.get_host_ip(
                                 svc_mon_h.get_service_instance(
                                           name=self.get_si_name(),
                                           refresh=refresh).active_vrouter())
                if self.active_vr.lower() == 'none':
                    self.active_vr = None
            except:
                self.logger.warn('Fail to get vrouter for active snat')
                self.active_vr = None
        return self.active_vr

    def get_standby_vrouter(self, refresh=False):
        if not getattr(self, 'standby_vr', None) or refresh:
            svc_mon_h = self.connections.get_svc_mon_h(refresh)
            try:
                self.standby_vr = self.inputs.get_host_ip(
                                  svc_mon_h.get_service_instance(
                                            name=self.get_si_name(),
                                            refresh=refresh).standby_vrouter())
                if self.standby_vr.lower() == 'none':
                    self.standby_vr = None
            except:
                self.logger.warn('Fail to get vrouter for standby snat')
                self.standby_vr = None
        return self.standby_vr

    @retry(6, 10)
    def verify_default_route_on_auto_vn_in_agent(self):
        active_vr = self.get_active_vrouter(refresh=True)
        if not active_vr:
            self.logger.warn('LR(%s): unable to find active vr'%self.uuid)
            return False
        inspect_h = self.connections.agent_inspect[active_vr]
        route = inspect_h.get_vna_active_route(ip='0.0.0.0', prefix='0',
                               vn_fq_name=':'.join(self.parent_fq_name +
                                             [self.get_auto_vn_name()]))
        if not route:
            self.logger.warn('LR: Agent: Unable to find default'
                             ' route in auto created VN')
            return False
        self.logger.debug('Agent: Auto VN has default route')
        return True

    def get_snat_label(self, intf='right'):
        if not getattr(self, 'label', None) or \
           not self.label.get(intf, None):
            self.label = dict()
            right_ip = self.get_snat_ip(); left_ip = '100.64.0.4'
            vm_id = self.get_active_instance()
            active_vr = self.get_active_vrouter()
            if not (right_ip and active_vr and vm_id):
                self.logger.warn('LR: Unable to fetch either of gw_ip '
                                 ' or active vm/vrouter info')
                return None
            inspect_h = self.connections.agent_inspect[active_vr]
            if vm_id:
                vmis = inspect_h.get_vna_tap_interface_by_vm(vm_id)
                if vmis:
                    self.label['right'] = [vmi['label'] for vmi in vmis
                                           if vmi['ip_addr'] ==right_ip][0]
                    self.label['left'] = [vmi['label'] for vmi in vmis
                                          if vmi['ip_addr'] == left_ip][0]
            if not self.label[intf]:
                self.logger.warn('LR: Unable to fetch label of %s intf'%intf)
        return self.label[intf]

    @retry(6, 10)
    def verify_snat_ip_on_public_in_agent(self):
        vn_fqname = self.id_to_fq_name(self.public_vn_id)
        label = self.get_snat_label()
        active_vr = self.get_active_vrouter()
        if not (active_vr and label):
            self.logger.warn('LR: Unable to fetch either of label '
                             ' or active vrouter info')
            return None
        inspect_h = self.connections.agent_inspect[active_vr]
        route = inspect_h.get_vna_active_route(ip=self.get_snat_ip(),
                                               prefix='32',
                                               vn_fq_name=':'.join(vn_fqname))
        if not route or label != route['path_list'][0]['active_label']:
            self.logger.warn('LR: agent: label doesnt match for gw ip %s, '
                             'expected %s: actual %s'%(self.get_snat_ip(),
                             label, route['path_list'][0]['active_label']
                             if route else None))
            return False
        return True
 
    def verify_in_agent(self):
        self.logger.debug('Verifying LR(%s) on agent'%(self.uuid))
        assert self.verify_default_route_on_auto_vn_in_agent()
        assert self.verify_snat_ip_on_public_in_agent()
        self.logger.debug('LR(%s) verfication on agent passed'%(self.uuid))
        return True

    def get_ctrl_nodes(self, ri_name):
        rt_list = []
        peer_list = []
        ri = self.vnc_api_h.routing_instance_read(fq_name=ri_name)
        rt_list = [rt['to'][0] for rt in ri.get_route_target_refs()]
        ctrl_node = ComputeNodeFixture(self.connections,
                                       self.get_active_vrouter()
                                      ).get_active_controller()
        cn_inspect = self.connections.cn_inspect[ctrl_node]
        peer_list.append(ctrl_node)
        for rt in rt_list:
            rt_group_entry = cn_inspect.get_cn_rtarget_group(rt)
            if rt_group_entry['peers_interested'] is not None:
                for peer in rt_group_entry['peers_interested']:
                    if peer in self.inputs.host_names:
                        peer = self.inputs.get_host_ip(peer)
                        peer_list.append(peer)
                    else:
                        self.logger.info('%s is not defined as a control node'
                                         ' in the topology' % peer)
        return list(set(peer_list))

    @retry(6, 10)
    def verify_static_route_in_cn(self):
        ri_fqname = self.parent_fq_name + [self.get_auto_vn_name(),
                                           self.get_auto_vn_name()]
        exp_label = self.get_snat_label(intf='left')
        if not exp_label:
            self.logger.warn('LR: Unable to fetch left intf label')
            return False
        for ctrl_node in self.get_ctrl_nodes(ri_fqname):
            cn_inspect = self.connections.cn_inspect[ctrl_node]
            routes = cn_inspect.get_cn_route_table_entry(prefix='0.0.0.0/0',
                                ri_name=':'.join(ri_fqname))
            if not routes:
                self.logger.warn('LR: Unable to find static route on auto VN')
                return False
            for route in routes:
                if route['label'] != exp_label:
                    self.logger.warn('label(%s) doesnt match expected(%s)'
                                     %(route['label'], exp_label))
                    return False
        return True

    def verify_in_control_node(self):
        self.logger.debug('Verifying LR(%s) in control node'%(self.uuid))
        assert self.verify_static_route_in_cn()
        self.logger.debug('LR(%s) verfication in ctrl node passed'%(self.uuid))
        return True
    '''

    def verify_if_lr_already_present(self, lr_fq_name, project):
        to_be_created_lr_fq_name = lr_fq_name
        lr_list = self.get_lr_list_in_project(project.uuid)
        if not lr_list:
            return False
        else:
            self.logger.info(lr_list) 
            for elem in lr_list['logical-routers']:
                if(elem['fq_name'] == to_be_created_lr_fq_name):
                    return True
        return False

    def get_name(self):
        return self.lr_name

    def get_lr_fq_name(self):
        return self.lr_fq_name

    def get_lr_list_in_project(self, project_uuid):
        return self.vnc_api_h.logical_routers_list(parent_id=project_uuid)

    def verify_if_vmi_already_present(self, vmi_fq_name, project):
        vmi_list = self.vnc_api_h.virtual_machine_interfaces_list(parent_id=project.uuid)
        if not vmi_list:
            return False
        else:
            self.logger.info(vmi_list)
            for elem in vmi_list['virtual-machine-interfaces']:
                if(elem['fq_name'] == vmi_fq_name):
                    return True
        return False

def setup_test_infra():
    import logging
    from common.contrail_test_init import ContrailTestInit
    from common.connections import ContrailConnections
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('event')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit('./instances.yaml', logger=mylogger)
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

if __name__ == "__main__":
   # obj = LogicalRouterFixture(name='Router', connections=setup_test_infra(), public_vn_id='ed8b6b51-1259-4437-a6ab-bf26f5f0276d', private={'vns': ['4b39a2bd-4528-40e8-b848-28084e59c944', 'c92957fb-22df-49ed-a1ea-d766ebbf05ae']})

    vn_1 = '549876c5-7acc-4807-9d43-86bce952a7a1'
    vn_2 = '0e07f26e-9a1d-4449-b41e-8d8d1d121ee5'
    vn_3 = 'e1cc4c64-f0a8-47e5-b0f5-c13e1947dc07'
    obj = LogicalRouterFixture(name='Router', connections=setup_test_infra(), private={'vns': [vn_1, vn_2]}, vni='5001', route_targets=['target:64500:1', 'target:64500:2'])
    obj.setUp()
    obj.verify_on_setup()
    obj.cleanUp()
    obj.verify_on_cleanup()
    stop = str(raw_input('press enter after checking cleanup...'))
    
    #obj = LogicalRouterFixture(api_type='neutron', uuid='a8395987-8882-41b4-898f-e43085c0f889', connections=setup_test_infra())
    obj.add_physical_router('b9b21cfb-ac15-40b7-90e9-4b037d3e4548')
    stop = str(raw_input('press enter after verifying physical router addition...'))
    obj.remove_physical_router('b9b21cfb-ac15-40b7-90e9-4b037d3e4548')
    stop = str(raw_input('press enter after verifying physical router deletion...'))
    obj.add_rt('target:64512:7002')
    stop = str(raw_input('press enter after verifying route target 64512:7002...'))
    obj.delete_rt('target:64512:7002')
    stop = str(raw_input('press enter after deleting  route target 64512:7002...'))
    obj.add_network(vn_3)
    stop = str(raw_input('press enter after verifying addition of vn-3 network..'))
    obj.remove_network(vn_3)
    stop = str(raw_input('press enter after verifying deletion of vn-3 network..'))
    obj.set_vni('7001')
    stop = str(raw_input('press enter after verifying vni vlaue as 7001..'))
    obj.delete_vni()
    stop = str(raw_input('press enter after remove vni value..'))
    obj.set_vni('7002')
    stop = str(raw_input('press enter after verifying vni value as 7002.'))
    obj.cleanUp()
