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


class LogicalInterfaceFixture(fixtures.Fixture):

    '''Fixture to handle Logical Interface object in 
       a phyiscal port 
    '''

    def __init__(
            self,
            name,
            pif_id,
            vlan_id=0,
            vmi_ids=[],
            project_name='admin',
            cfgm_ip='127.0.0.1',
            username='admin',
            password='contrail123',
            connections=None):
        self.name = name
        self.pif_id = pif_id
        self.connections = connections
        self.username = username
        self.password = password
        self.project_name = project_name
        self.cfgm_ip = cfgm_ip
        self.keystone_ip = '127.0.0.1'
        #self.device_id = device_id
        self.vlan_id = int(vlan_id)
        self.vmi_ids = vmi_ids

        self.already_present = False

        self.vn_obj = None
        if connections:
            self.logger = self.connections.inputs.logger
            self.inputs = self.connections.inputs
            self.vnc_api_h = self.connections.vnc_lib
            self.username = self.connections.username
            self.password = self.connections.password
            self.cfgm_ip = self.inputs.cfgm_ip
            self.keystone_ip = self.inputs.keystone_ip
        else:
            self.logger = logging.getLogger(__name__)
            self.inputs = None
            self.quantum_handle = None
            self.vnc_api_h = VncApi(username=self.username,
                                    password=self.password,
                                    tenant_name=self.project_name,
                                    api_server_host=self.cfgm_ip,
                                    api_server_port='8082')
        self.project_id = self._get_project_id(project_name)

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
        self.pif_obj = self.vnc_api_h.physical_interface_read(id=self.pif_id)
        lif_fq_name = self.pif_obj.fq_name[:]
        lif_fq_name.append(self.name)

        try:
            self.obj = self.vnc_api_h.logical_interface_read(
                fq_name=lif_fq_name)
            self.already_present = True
            self.logger.debug('Logical port %s already present' % (
                lif_fq_name))
        except NoIdError:
            self.logger.info('Creating Logical port %s' % (lif_fq_name))
            lif_obj = LogicalInterface(name=self.name,
                                       parent_obj=self.pif_obj,
                                       display_name=self.name)
            lif_obj.parent_uuid = self.pif_obj.uuid
            lif_obj.set_logical_interface_vlan_tag(self.vlan_id)
            self.uuid = self.vnc_api_h.logical_interface_create(lif_obj)
            self.obj = self.vnc_api_h.logical_interface_read(id=self.uuid)

        if self.vmi_ids:
            for vmi_id in self.vmi_ids:
                vmi_obj = self.vnc_api_h.virtual_machine_interface_read(
                    id=vmi_id)
                self.obj.add_virtual_machine_interface(vmi_obj)
            self.vnc_api_h.logical_interface_update(self.obj)
        super(LogicalInterfaceFixture, self).setUp()
        self.fq_name = self.obj.fq_name

    def cleanUp(self):
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.debug('Skipping deletion of logical port %s' % (
                self.fq_name))
        if do_cleanup:
            self.logger.info('Deleting Logical port %s' % (self.fq_name))
            self.obj.set_virtual_machine_interface_list([])
            self.vnc_api_h.logical_interface_update(self.obj)
            self.vnc_api_h.logical_interface_delete(id=self.uuid)
        super(LogicalInterfaceFixture, self).cleanUp()
    # end cleanUp

    def add_virtual_machine_interface(self, vmi_id):
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_id)
        self.obj.add_virtual_machine_interface(vmi_obj)
        self.vnc_api_h.logical_interface_update(self.obj)

    def delete_virtual_machine_interface(self, vmi_id):
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_id)
        self.obj.delete_virtual_machine_interface(vmi_obj)
        self.vnc_api_h.logical_interface_update(self.obj)

# end LogicalInterfaceFixture

if __name__ == "__main__":
    device_id = 'e122f6b2-5d5c-4f2e-b665-d69dba447bdf'
    from pif_fixture import PhysicalInterfaceFixture
    from port_fixture import PortFixture
    pif_obj = PhysicalInterfaceFixture(name='ge-0/0/0', device_id=device_id)
    pif_obj.setUp()

    vn_id = '1c83bed1-7d24-4414-9aa2-9d92975bc86f'
    subnet_id = '49fea486-57ab-4056-beb3-d311a385814e'
    port_fixture = PortFixture(
        vn_id=vn_id, api_type='contrail', mac_address="00:00:00:00:00:01",
        fixed_ips=[{'subnet_id': subnet_id, 'ip_address': '10.1.1.20'}])
    port_fixture.setUp()
    lif_obj = LogicalInterfaceFixture(
        name='ge-0/0/0.0', pif_id=pif_obj.uuid, vmi_ids=[port_fixture.uuid])
    lif_obj.setUp()
    import pdb
    pdb.set_trace()
