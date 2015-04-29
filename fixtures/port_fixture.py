import uuid
from netaddr import *
import os


import fixtures
from neutronclient.neutron import client
from neutronclient.client import HTTPClient
from neutronclient.common.exceptions import NeutronClientException as CommonNetworkClientException
from keystoneclient.v2_0 import client as ks_client

from vnc_api.vnc_api import *
from tcutils.util import get_dashed_uuid
from quantum_test import QuantumFixture


class PortFixture(fixtures.Fixture):

    '''Fixture to handle Port/VMI objects

    api_type : can be one of 'neutron' or 'contrail'

    '''

    def __init__(
            self,
            vn_id,
            project_name='admin',
            mac_address=None,
            fixed_ips=[],
            security_groups=[],
            extra_dhcp_opts=[],
            cfgm_ip='127.0.0.1',
            username='admin',
            password='contrail123',
            api_type='neutron',
            connections=None):
        self.vn_id = vn_id
        self.connections = connections
        self.username = username
        self.password = password
        self.project_name = project_name
        self.cfgm_ip = cfgm_ip
        self.fixed_ips = fixed_ips
        self.mac_address = mac_address
        self.security_groups = security_groups
        self.extra_dhcp_opts = extra_dhcp_opts
        self.api_type = api_type
        self.keystone_ip = '127.0.0.1'

        self.vn_obj = None
        if connections:
            self.project_name = connections.project_name
            self.logger = self.connections.inputs.logger
            self.inputs = self.connections.inputs
            self.neutron_handle = self.connections.quantum_fixture
            self.vnc_api_h = self.connections.vnc_lib
            self.username = self.connections.username
            self.password = self.connections.password
            self.cfgm_ip = self.inputs.cfgm_ip
            self.keystone_ip = self.inputs.keystone_ip
            self.project_id = self._get_project_id(self.project_name)
        else:
            self.logger = logging.getLogger(__name__)
            self.inputs = None
            self.quantum_handle = None
            self.vnc_api_h = VncApi(username=self.username,
                                    password=self.password,
                                    tenant_name=self.project_name,
                                    api_server_host=self.cfgm_ip,
                                    api_server_port='8082')
            self.project_id = self._get_project_id(self.project_name)
            self.neutron_handle = QuantumFixture(
                username=self.username,
                password=self.password,
                project_id=self.project_id,
                inputs=self.inputs,
                cfgm_ip=self.cfgm_ip,
                openstack_ip=self.keystone_ip)
            self.neutron_handle.setUp()

     # end __init__

    def _get_project_id(self, project_name):
        insecure = bool(os.getenv('OS_INSECURE', True))
        self.ks_client = ks_client.Client(
            username=self.username,
            password=self.password,
            tenant_name=self.project_name,
            auth_url=os.getenv('OS_AUTH_URL') or
            'http://' + self.keystone_ip + ':5000/v2.0',
            insecure=insecure)
        return get_dashed_uuid(self.ks_client.tenant_id)

    def setUp(self):
        super(PortFixture, self).setUp()
        self.vn_obj = self.vnc_api_h.virtual_network_read(id=self.vn_id)
        
        if self.api_type == 'neutron':
            self.neutron_obj = self._neutron_create_port()
        else:
            self.vmi_obj = self._contrail_create_port()
        self.obj = self.neutron_handle.get_port(self.uuid)
        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
            id=self.uuid)
        self.logger.info('Created port %s' % (self.uuid))

    def _neutron_create_port(self):
        neutron_obj = self.neutron_handle.create_port(
            self.vn_id,
            fixed_ips=self.fixed_ips,
            mac_address=self.mac_address,
            security_groups=self.security_groups,
            extra_dhcp_opts=self.extra_dhcp_opts)
        self.neutron_obj = neutron_obj
        self.uuid = neutron_obj['id']

    def _contrail_create_port(self):
        proj_obj = self.vnc_api_h.project_read(id=self.project_id)
        vmi_id = str(uuid.uuid4())
        vmi_obj = VirtualMachineInterface(name=vmi_id, parent_obj=proj_obj)
        if self.mac_address:
            mac_address_obj = MacAddressesType()
            mac_address_obj.set_mac_address([str(EUI(self.mac_address))])
            vmi_obj.set_virtual_machine_interface_mac_addresses(
                mac_address_obj)
        vmi_obj.uuid = vmi_id
        vmi_obj.add_virtual_network(self.vn_obj)
        iip_id = str(uuid.uuid4())
        iip_obj = InstanceIp(name=iip_id)
        iip_obj.uuid = iip_id
        iip_obj.add_virtual_machine_interface(vmi_obj)
        iip_obj.add_virtual_network(self.vn_obj)

        if self.security_groups:
            for sg_id in self.security_groups:
                sg_obj = self.vnc_api_h.security_group_read(id=sg_id)
                vmi_obj.add_security_group(sg_obj)
        else:
            # Associate default SG
            default_sg_fq_name = proj_obj.fq_name[:]
            default_sg_fq_name.append('default')
            sg_obj = self.vnc_api_h.security_group_read(
                fq_name=default_sg_fq_name)
            vmi_obj.add_security_group(sg_obj)

        if self.extra_dhcp_opts:
            # TODO
            pass

        self.vmi_obj = self.vnc_api_h.virtual_machine_interface_create(vmi_obj)
        self.uuid = vmi_id

        if self.fixed_ips:
            for fixed_ip in self.fixed_ips:
#                ip_address_obj = IpAddressesType(ip_address=fixed_ip['ip_address'])
                iip_id = str(uuid.uuid4())
                iip_obj = InstanceIp(name=iip_id,
                                     # instance_ip_address=ip_address_obj,
                                     subnet_id=fixed_ip['subnet_id'])
                iip_obj.uuid = iip_id
                iip_obj.add_virtual_machine_interface(vmi_obj)
                iip_obj.add_virtual_network(self.vn_obj)
                iip_obj.set_instance_ip_address(fixed_ip['ip_address'])
                import pdb
                pdb.set_trace()
                self.vnc_api_h.instance_ip_create(iip_obj)
        else:
            iip_id = str(uuid.uuid4())
            iip_obj = InstanceIp(name=iip_id)
            iip_obj.uuid = iip_id
            iip_obj.add_virtual_machine_interface(vmi_obj)
            iip_obj.add_virtual_network(self.vn_obj)
            self.vnc_api_h.instance_ip_create(iip_obj)
    # end _contrail_create_port

    def cleanUp(self):
        if self.api_type == 'neutron':
            self._neutron_delete_port()
        else:
            self._contrail_delete_port()
        super(PortFixture, self).cleanUp()
        self.logger.info('Deleted port %s' % (self.uuid))

    def _neutron_delete_port(self):
        self.neutron_handle.delete_port(self.uuid)

    def _contrail_delete_port(self):
        vmi_iips = self.vmi_obj.get_instance_ip_back_refs()
        for vmi_iip in vmi_iips:
            vmi_iip_uuid = vmi_iip['uuid']
            self.vnc_api_h.instance_ip_delete(id=vmi_iip_uuid)
        self.vnc_api_h.virtual_machine_interface_delete(id=self.uuid)

# end PortFixture

if __name__ == "__main__":
    vn_id = '1c83bed1-7d24-4414-9aa2-9d92975bc86f'
    subnet_id = '49fea486-57ab-4056-beb3-d311a385814e'
    port_fixture = PortFixture(vn_id=vn_id)
#    port_fixture.setUp()
    port_fixture1 = PortFixture(vn_id=vn_id, api_type='contrail')
#    port_fixture1.setUp()
    port_fixture2 = PortFixture(vn_id=vn_id, api_type='contrail', fixed_ips=[
                                {'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture2.setUp()
    import pdb
    pdb.set_trace()
