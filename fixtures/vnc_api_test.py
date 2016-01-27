import fixtures
import os
import uuid

from vnc_api.vnc_api import *
from cfgm_common.exceptions import NoIdError

from tcutils.util import get_dashed_uuid
from quantum_test import QuantumHelper
from openstack import OpenstackAuth
from openstack import OpenstackAuth, OpenstackOrchestrator
from vcenter import VcenterAuth

class VncLibFixture(fixtures.Fixture):
    ''' Wrapper for VncApi

    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1
    :param logger         : logger object
    '''
    def __init__(self, *args, **kwargs):

        self.username = os.getenv('OS_USERNAME') or \
                        kwargs.get('username', 'admin')
        self.password = os.getenv('OS_PASSWORD') or \
                        kwargs.get('password', 'contrail123')
        self.project_name = kwargs.get('project_name', 'admin')
        self.domain = kwargs.get('domain', 'default-domain')
        self.api_server_port = kwargs.get('api_server_port', '8082')
        self.cfgm_ip = kwargs.get('cfgm_ip', '127.0.0.1')
        self.auth_server_ip = kwargs.get('auth_server_ip', '127.0.0.1')
        self.logger = kwargs.get('logger', logging.getLogger(__name__))
        self.connections = kwargs.get('connections', None)
        self.orchestrator = kwargs.get('orchestrator', 'openstack')
        self.vnc_api_h = None
        self.auth_client_h = None
        self.inputs = kwargs.get('inputs', None) 
        self.neutron_handle = None
        self.auth_url = os.getenv('OS_AUTH_URL')
        if self.auth_server_ip:
            self.auth_url = 'http://' + self.auth_server_ip + ':5000/v2.0'
    
        
    # end __init__

    def setUp(self):
        super(VncLibFixture, self).setUp()
        if self.connections:
            self.logger = self.connections.logger
            self.project_name = self.connections.project_name
            self.inputs = self.connections.inputs
            self.neutron_handle = self.connections.quantum_h
            self.vnc_api_h = self.connections.vnc_lib
            self.username = self.connections.username
            self.password = self.connections.password
            self.cfgm_ip = self.inputs.cfgm_ip
            self.auth_server_ip = self.inputs.auth_ip
            self.project_id = self.connections.project_id
            self.auth_url = 'http://' + self.inputs.auth_ip + ':5000/v2.0'
        else:
            self.vnc_api_h = VncApi(
                              username=self.username,
                              password=self.password,
                              tenant_name=self.project_name,
                              api_server_host=self.cfgm_ip,
                              api_server_port=self.api_server_port,
                              auth_host=self.auth_server_ip)
            if self.orchestrator == 'openstack':
                self.auth_client = OpenstackAuth(
                                self.username,
                                self.password,
                                self.project_name,
                                auth_url=self.auth_url,
                                logger=self.logger)
                self.project_id = self.auth_client.get_project_id()
            elif self.orchestrator == 'vcenter':
                self.auth_client = VcenterAuth(self.username,
                                                self.password,
                                                self.project_name,
                                                self.inputs
                                                ) 
                self.project_id = self.auth_client.get_project_id()
                
    # end setUp

    def cleanUp(self):
        super(VncLibFixture, self).cleanUp()

    def get_handle(self):
        return self.vnc_api_h
    # end get_handle

    def get_neutron_handle(self):
        if self.neutron_handle:
            return self.neutron_handle
        else:
            self.orch = OpenstackOrchestrator(username=self.username,
                  password=self.password,
                  project_id=self.project_id,
                  project_name=self.project_name,
                  auth_server_ip=self.auth_server_ip,
                  vnclib=self.vnc_api_h,
                  logger=self.logger, inputs=None)
            self.neutron_handle = self.orch.get_network_handler()
            return self.neutron_handle
    # end get_neutron_handle

    def get_forwarding_mode(self, vn_fq_name):
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_id=self.project_id)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                vni_obj_properties = vni_obj.get_virtual_network_properties()
                if vni_obj_properties:
                    fw_mode = vni_obj_properties.get_forwarding_mode()
                else:
                    fw_mode = None
                return fw_mode
    # end get_forwarding_mode

    def get_vn_subnet_dhcp_flag(self, vn_fq_name):
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_id=self.project_id)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                subnets = vni_obj.network_ipam_refs[0]['attr']
                ipam = subnets.get_ipam_subnets()
                enable_dhcp = ipam[0].get_enable_dhcp()
                return enable_dhcp

    # get_vn_subnet_dhcp_flag

    def set_rpf_mode(self, vn_fq_name, mode):
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = self.vnc_api_h.virtual_networks_list(
            parent_id=self.project_id)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                vni_obj_properties = vni_obj.get_virtual_network_properties() or VirtualNetworkType()
                vni_obj_properties.set_rpf(mode)
                vni_obj.set_virtual_network_properties(vni_obj_properties)
                vnc_lib.virtual_network_update(vni_obj)

    # end set_rpf_mode

    def id_to_fq_name(self, id):
        return self.vnc_api_h.id_to_fq_name(id)

    def set_vxlan_mode(self, vxlan_mode='automatic'):
        ''' one of automatic or configured
        '''
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        vrouter_config = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        vrouter_config.set_vxlan_network_identifier_mode(vxlan_mode)
        self.vnc_api_h.global_vrouter_config_update(vrouter_config)

    def get_vxlan_mode(self):
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        vrouter_config = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        return vrouter_config.get_vxlan_network_identifier_mode()
    # end 

    def get_global_asn(self, gsc_id=None):
        gsc_id = gsc_id or self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_autonomous_system()
    # end get_global_asn

    def set_global_asn(self, asn, gsc_id=None):
        gsc_id = gsc_id or self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_autonomous_system(int(asn))
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_asn

# end VncLibFixture
