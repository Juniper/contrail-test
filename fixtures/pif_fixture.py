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
from cfgm_common.exceptions import NoIdError


class PhysicalInterfaceFixture(fixtures.Fixture):

    '''Fixture to handle Physical Interface object in 
       a phyiscal device
    '''

    def __init__(
            self,
            name,
            device_id,
            project_name='admin',
            cfgm_ip='127.0.0.1',
            username='admin',
            password='contrail123',
            connections=None):
        self.name = name
        self.connections = connections
        self.username = username
        self.password = password
        self.project_name = project_name
        self.cfgm_ip = cfgm_ip
        self.keystone_ip = '127.0.0.1'
        self.device_id = device_id

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
        self.device_obj = self.vnc_api_h.physical_router_read(
            id=self.device_id)

        try:
            self.obj = self.vnc_api_h.physical_interface_read(
                fq_name=['default-global-system-config', self.name])
            self.already_present = True
            self.logger.debug('Physical port %s is already present' % (
                self.name))
        except NoIdError:
            self.logger.info('Creating physical port %s on device %s' % (
                self.name, self.device_obj.name))
            pif_obj = PhysicalInterface(name=self.name,
                                        parent_obj=self.device_obj,
                                        display_name=self.name)
            pif_obj.parent_uuid = self.device_obj.uuid
            self.uuid = self.vnc_api_h.physical_interface_create(pif_obj)
            self.obj = self.vnc_api_h.physical_interface_read(id=self.uuid)

        super(PhysicalInterfaceFixture, self).setUp()
    # end setUp

    def cleanUp(self):
        do_cleanup = True
        if self.already_present:
            do_cleanup = False
            self.logger.debug('Skipping deletion of physical port %s' % (
                self.name))
        if do_cleanup:
            self.logger.info('Deleting physical port %s' % (self.name))
            self.vnc_api_h.physical_interface_delete(id=self.uuid)
        super(PhysicalInterfaceFixture, self).cleanUp()
    # end cleanUp

# end PhysicalInterfaceFixture

if __name__ == "__main__":
    device_id = 'e122f6b2-5d5c-4f2e-b665-d69dba447bdf'
    pif_obj = PhysicalInterfaceFixture(name='ge-0/0/0', device_id=device_id)
    pif_obj.setUp()
    import pdb
    pdb.set_trace()
    pif_obj.cleanUp()
