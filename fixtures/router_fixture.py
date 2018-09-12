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
        self.connected_networks = kwargs.get('connected_networks', None)
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
            #--temp---
            if self.vni:
                self.obj = self.vnc_h.create_router(self.lr_name, self.project_object, vni=self.vni)
            else:
                self.obj = self.vnc_h.create_router(self.lr_name, self.project_object)
            #self.obj = LogicalRouter(name=self.lr_name, parent_obj=self.project_obj, display_name=self.lr_name)
            #self._vnc.logical_router_create(obj)

            self.uuid = self.obj.uuid
        else:
            self.already_present = False
            self.obj = self.vnc_api_h.logical_router_read(fq_name=self.lr_fq_name)
            self.uuid = self.obj.uuid
            self.read(self.uuid)
                    
        pre_vn_ids = self.get_vn_ids()

        # configuring VxLAN Network Identifier for this Logical Router     
        #if self.vni:
        #    self.set_vni(self.vni)

        # Adding Virtaul Networkds 
        if self.connected_networks:
            for vn_id in self.connected_networks.get('vns', []):
                if not (pre_vn_ids and (vn_id in pre_vn_ids)):
                    self.add_network(vn_id=vn_id)

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
        self.vnc_h.set_logical_router_vni(lr_id=self.uuid, vni=str(vni))
        self.vni = vni
        self.logger.info('configured routing VNI: %s'%(vni))
   
    def delete_vni(self):
        self.logger.info('Deleting routing VNI %s on Logical Router %s ...'%(self.vni,self.lr_name))
        self.vnc_h.delete_logical_router_vni(lr_id=self.uuid)
        self.vni = None
        self.logger.info('Deleted routing VNI: %s'%(self.vni))

    def refresh(self):
        self.read(self.uuid)

    def add_rt(self, rt):
        if rt in self.rt_list:
            self.logger.info('RT %s is already configured on Logical Router %s ...'%(rt,self.lr_name))
            return True
        self.logger.info('Configuring route-target %s on Logical Router %s ...'%(rt,self.lr_name))
        self.vnc_h.add_route_target_to_lr(lr_id=self.uuid, rt=rt)
        self.rt_list.add(rt)
        self.logger.info('configured route-target %s'%(rt))
        return True

    def delete_rt(self, rt):
        if rt not in self.rt_list:
            self.logger.info('Given RT %s is NOT configured on Logical Router %s ...'%(rt,self.lr_name))
            return True

        self.logger.info('Deleting route-target %s on Logical Router %s ...'%(rt,self.lr_name))
        self.vnc_h.remove_route_target_from_lr(lr_id=self.uuid, rt=rt)
        self.rt_list.remove(rt)
        self.logger.info('Deleted route-target %s'%(rt))


    def set_configured_rt_list(self, rt_list):
        self.logger.info('Configuring configured rt list  %s on Logical Router %s ...'%(rt_list,self.lr_name))
        lr_obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        rt_obj_list = []
        for each_rt in rt_list:
            rt_obj_list.append(self.vnc_h.create_rt(each_rt))
        lr_obj.set_configured_route_target_list(rt_obj_list)
        self.vnc_api_h.logical_router_update(lr_obj)
        self.logger.info('configured rt list %s'%(rt_obj_list))

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
                                    parent_obj=self.project_object,
                                    virtual_machine_interface_device_owner="network:router_interface")
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
        return self.vnc_h.extend_lr_to_physical_router(lr_id=self.uuid, router_id=router_id)

    def remove_physical_router(self, router_id):
        return self.vnc_h.remove_physical_router_from_lr(lr_id=self.uuid, router_id=router_id)

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
