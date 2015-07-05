import fixtures
import os
import uuid

from vnc_api.vnc_api import *
from cfgm_common.exceptions import NoIdError
from keystoneclient.v2_0 import client as auth_client
from tcutils.util import get_dashed_uuid
from quantum_test import QuantumFixture

class VncLibFixture(fixtures.Fixture):
    ''' Wrapper for VncApi

    Similar to fixtures/vnc_api_test.py, but can be run independently
    without any testbed details
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth-server_ip : default is 127.0.0.1
    '''
    def __init__(self, *args, **kwargs):

        self.username = kwargs.get('username', 'admin')
        self.password = kwargs.get('password', 'contrail123')
        self.project_name = kwargs.get('project_name', 'admin')
        self.domain = kwargs.get('domain', 'default-domain')
        self.api_server_port = kwargs.get('api_server_port', '8082')
        self.cfgm_ip = kwargs.get('cfgm_ip', '127.0.0.1')
        self.auth_server_ip = kwargs.get('auth_server_ip', '127.0.0.1')
        self.logger = kwargs.get('logger', logging.getLogger(__name__))
        self.connections = kwargs.get('connections', None)
        self.vnc_api_h = None
        self.auth_client_h = None
        self.inputs = None
        self.neutron_handle = None
    # end __init__

    def setUp(self):
        super(VncLibFixture, self).setUp()
        if self.connections:
            self.logger = self.connections.logger
            self.project_name = self.connections.project_name
            self.inputs = self.connections.inputs
            self.neutron_handle = self.connections.quantum_fixture
            self.vnc_api_h = self.connections.vnc_lib
            self.username = self.connections.username
            self.password = self.connections.password
            self.cfgm_ip = self.inputs.cfgm_ip
            self.auth_server_ip = self.connections.keystone_ip
            self.project_id = self._get_project_id(self.project_name)
        else:
            self.vnc_api_h = VncApi(
                              username=self.username,
                              password=self.password,
                              tenant_name=self.project_name,
                              api_server_host=self.cfgm_ip,
                              api_server_port=self.api_server_port,
                              auth_host=self.auth_server_ip)
            self.project_id = self._get_project_id(self.project_name)
    # end setUp

    def cleanUp(self):
        super(VncLibFixture, self).cleanUp()

    def _get_project_id(self, project_name):
        insecure = bool(os.getenv('OS_INSECURE', True))
        if not self.auth_client_h:
            self.auth_client_h = auth_client.Client(
                username=self.username,
                password=self.password,
                tenant_name=self.project_name,
                auth_url=os.getenv('OS_AUTH_URL') or
                'http://' + self.auth_server_ip + ':5000/v2.0',
                insecure=insecure)
        tenant_id = self.auth_client_h.tenant_id
        return get_dashed_uuid(tenant_id)

    def get_handle(self):
        return self.vnc_api_h
    # end get_handle

    def get_neutron_handle(self):
        if self.neutron_handle:
            return self.neutron_handle
        else:
            self.neutron_handle = QuantumFixture(
                username=self.username,
                password=self.password,
                project_id=self.project_id,
                inputs=self.inputs,
                cfgm_ip=self.cfgm_ip,
                openstack_ip=self.auth_server_ip)
            self.neutron_handle.setUp()
    # end get_neutron_handle

    def get_forwarding_mode(self, vn_fq_name):
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=self.project)['virtual-networks']
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
            parent_fq_name=self.project)['virtual-networks']
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
        # Figure out VN
        vni_list = self.vnc_api_h.virtual_networks_list(
            parent_fq_name=self.project)['virtual-networks']
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

# end VncLibFixture1
