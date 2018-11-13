import vnc_api_test
from compute_node_test import ComputeNodeFixture
from tcutils.util import get_random_name, retry
from contrailapi import ContrailVncApi
from port_fixture import PortFixture
from vnc_api.vnc_api import *
import copy

class LogicalRouterFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle Logical Router object
    
    Optional:
    :param name : name of the logical router
    :param uuid : UUID of the logical router
                  One of router name or router id is mandatory
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
    '''

    def __init__(self, **kwargs):
        super(LogicalRouterFixture, self).__init__(self, **kwargs)
        self.name = kwargs.get('name', get_random_name('Router'))
        self.uuid = kwargs.get('uuid', None)
        self.is_public_lr = kwargs.get('is_public_lr', False)
        self.connected_networks = kwargs.get('connected_networks', None)
        self.api_type = kwargs.get('api_type', 'contrail')
        self.created = False
        self.ports = []; self.vns = []; self.subnets = []
        self.deleted_vn_ids = []
        self.vn_ids = set()
        self.is_gw_active = False
        self.vni = kwargs.get('vni', None)
        self.route_targets = kwargs.get('route_targets', [])
        self.rt_list = set()
        self.logger.info('VNI to be configured on Logical Router %s'%self.vni)
        self.physical_routers = kwargs.get('physical_routers', [])
        self.parent_fq_name = [self.domain, self.project_name]
        self.lr_fq_name = self.parent_fq_name + [self.name]
        self.parent_type = 'project'
        self.vmi_fixtures = dict()

    def setUp(self):
        super(LogicalRouterFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if (self.created == False or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Logical Router %s :'
                              %(self.lr_fq_name))
        else:
            self.remove_interface(self.vn_ids) 
            self.delete()
        super(LogicalRouterFixture, self).cleanUp()

    def read(self):
        self.logger.debug('Fetching information about Logical Router %s'%self.uuid)
        obj = self.vnc_api_h.logical_router_read(id=self.uuid)
        self.is_public_lr = obj.logical_router_gateway_external

        # updating vn lists
        vmi_ref_list = obj.get_virtual_machine_interface_refs()
        for each_vmi in vmi_ref_list or []:
            vmi_fixture = PortFixture(connections=self.connections, uuid=each_vmi['uuid'])
            vmi_fixture.read()
            if vmi_fixture.vn_id:
                self.vn_ids.add(vmi_fixture.vn_id)
                self.vmi_fixtures[vmi_fixture.vn_id] = each_vmi['uuid']

        self.rt_list = set()
        rt_ref_list = obj.get_route_target_refs()
        for each_rt_ref in rt_ref_list or []:
            self.rt_list.add(each_rt_ref['to'][0])
        self.logger.info('LR: %s, members: %s'%(self.name, self.vn_ids))

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_api_h.logical_router_read(fq_name=self.lr_fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.logger.info('Creating Logical router %s'%self.name)
                obj = self.vnc_h.create_router(self.name,
                                               parent_fq_name=self.parent_fq_name,
                                               is_public=self.is_public_lr,
                                               vni=self.vni)
                self.created = True
                self.uuid = obj.uuid
        self.read()
        try:
            self.add_interface(self.connected_networks)
            for each_rt in self.route_targets or []:
                self.add_rt(each_rt)
            for router in self.physical_routers or []:
                self.add_physical_router(router)
        except:
            self.cleanUp()
            raise
        self.logger.info('LR: %s, members: %s, vni: %s'%(self.name,
                         self.get_vn_ids(), self.vni))

    def set_vni(self, vni):
        self.logger.debug('Configuring routing VNI %s on Logical Router %s ...'%(vni,self.name))
        self.vnc_h.set_logical_router_vni(lr_id=self.uuid, vni=str(vni))
        self.vni = vni
        self.logger.debug('configured routing VNI: %s'%(vni))
   
    def delete_vni(self):
        self.logger.debug('Deleting routing VNI %s on Logical Router %s ...'%(self.vni,self.name))
        self.vnc_h.delete_logical_router_vni(lr_id=self.uuid)
        self.vni = None
        self.logger.debug('Deleted routing VNI: %s'%(self.vni))

    def refresh(self):
        self.read(self.uuid)

    def add_rt(self, rt):
        if rt in self.rt_list:
            self.logger.info('RT %s is already configured on Logical Router %s ...'%(rt,self.name))
            return True
        self.logger.debug('Configuring route-target %s on Logical Router %s ...'%(rt,self.name))
        try:
            rt_obj = self.vnc_api_h.route_target_read(fq_name=[rt])
        except Exception as exp:
            rt_obj = self.vnc_h.create_rt(rt)
        self.vnc_h.add_route_target_to_lr(lr_id=self.uuid, rt=rt)
        self.rt_list.add(rt)
        self.logger.debug('configured route-target %s'%(rt))
        return True

    def delete_rt(self, rt):
        if rt not in self.rt_list:
            self.logger.info('Given RT %s is NOT configured on Logical Router %s ...'%(rt,self.name))
            return True

        self.logger.debug('Deleting route-target %s on Logical Router %s ...'%(rt,self.name))
        self.vnc_h.remove_route_target_from_lr(lr_id=self.uuid, rt=rt)
        self.rt_list.remove(rt)
        self.logger.debug('Deleted route-target %s'%(rt))

    def set_configured_rt_list(self, rt_list):
        self.logger.debug('Configuring configured rt list  %s on Logical Router %s ...'%(rt_list,self.name))
        for each_rt in rt_list:
            try:
                rt_obj = self.vnc_api_h.route_target_read(fq_name=[each_rt])
            except Exception as exp:
                rt_obj = self.vnc_h.create_rt(rt)
        self.vnc_h.set_lr_configured_rt_list(lr_id=self.uuid, rt_list=rt_list)
        self.logger.debug('configured rt list %s'%(rt_obj_list))

    def add_interface(self, vn_ids):
        if not (set(vn_ids) - self.get_vn_ids()):
            self.logger.info('Network %s is already part of the LR: %s'%(
                vn_ids, self.name))
            return True
        for vn_id in list(set(vn_ids) - self.get_vn_ids()):
            vmi_name = self.name+'-'+vn_id
            vmi = self.useFixture(PortFixture(
                         connections=self.connections,
                         vn_id=vn_id,
                         name=vmi_name,
                         device_owner="network:router_interface",
                         api_type='contrail'))
            self.vmi_fixtures[vn_id] = vmi
            self.vnc_h.add_interface_to_lr(lr_id=self.uuid, vmi_id=vmi.uuid)
            self.vn_ids.add(vn_id)
        return True

    def remove_interface(self, vn_ids):
        for vn_id in list(set(vn_ids).intersection(self.get_vn_ids())):
            vmi_fixture = self.vmi_fixtures[vn_id]
            self.vnc_h.remove_interface_from_lr(lr_id=self.uuid, vmi_id=vmi_fixture.uuid) 
            vmi_fixture.cleanUp(force=True)
            self.vn_ids.remove(vn_id)
            del self.vmi_fixtures[vn_id]

    def add_physical_router(self, router):
        return self.vnc_h.extend_lr_to_physical_router(self.uuid, router)

    def remove_physical_router(self, router):
        return self.vnc_h.remove_physical_router_from_lr(self.uuid, router)

    def delete(self, verify=False):
        self.logger.info('Deleting LogicalRouter %s(%s)'%(self.name, self.uuid))
        self.vnc_h.delete_router(id=self.uuid)

    def get_vn_ids(self, refresh=False):
        return self.vn_ids

    def get_name(self):
        return self.name

    def get_lr_fq_name(self):
        return self.lr_fq_name

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
   # obj = LogicalRouterFixture(name='Router', connections=setup_test_infra(), private={'vns': ['4b39a2bd-4528-40e8-b848-28084e59c944', 'c92957fb-22df-49ed-a1ea-d766ebbf05ae']})

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
    obj.add_interface(vn_3)
    stop = str(raw_input('press enter after verifying addition of vn-3 network..'))
    obj.remove_interface(vn_3)
    stop = str(raw_input('press enter after verifying deletion of vn-3 network..'))
    obj.set_vni('7001')
    stop = str(raw_input('press enter after verifying vni vlaue as 7001..'))
    obj.delete_vni()
    stop = str(raw_input('press enter after remove vni value..'))
    obj.set_vni('7002')
    stop = str(raw_input('press enter after verifying vni value as 7002.'))
    obj.cleanUp()
