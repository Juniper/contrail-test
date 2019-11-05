from builtins import object
import os
import openstack
from ironicclient import exc as ironic_exc
from common.openstack_libs import ironic_client as client
from common import log_orig as contrail_logging

class IronicHelper(object):
    '''
       Wrapper around ironic client library
       Optional params:
       :param auth_h: OpenstackAuth object
       :param inputs: ContrailTestInit object which has test env details
       :param logger: logger object
       :param auth_url: Identity service endpoint for authorization.
       :param username: Username for authentication.
       :param password: Password for authentication.
       :param project_name: Tenant name for tenant scoping.
       :param region_name: Region name of the endpoints.
       :param certfile: Public certificate file
       :param keyfile: Private Key file
       :param cacert: CA certificate file
       :param verify: Enable or Disable ssl cert verification
    '''
    def __init__(self, auth_h=None, **kwargs):
        self.inputs = kwargs.get('inputs')
        self.logger = kwargs.get('logger') or self.inputs.logger if self.inputs \
                          else contrail_logging.getLogger(__name__)
        self.region_name = kwargs.get('region_name') or \
                           inputs.region_name if self.inputs else None
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def setUp(self):
        if not self.inputs.host_data[self.inputs.openstack_names[0]]['containers'].get('ironic_conductor'):
           return
        self.obj = client.get_client('1',
                       session=self.auth_h.get_session(scope='project'),
                       os_region_name=self.region_name)
        self.obj.http_client.api_version_select_state = self.inputs.ironic_api_config.get('api_version_select_state','user')
        self.obj.http_client.os_ironic_api_version = self.inputs.ironic_api_config.get('os_ironic_api_version','1.31')
    # end setUp

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def delete_ironic_node(self,node_id):

        self.obj.node.delete(node_id)

    def create_ironic_port(self,port,mac_address,node_uuid,portgroup_uuid,pxe_enabled):
        self.obj.port.create(local_link_connection=port,\
            address=mac_address,node_uuid=node_uuid,\
                portgroup_uuid=portgroup_uuid,pxe_enabled=pxe_enabled)

    def create_ironic_portgroup(self,node_id,pg_name,mac_addr):

        try:
          pg_obj = self.obj.portgroup.get(pg_name)
        except ironic_exc.NotFound:
          pg_obj = None
        if not pg_obj:
          try:
             pg_obj = self.obj.portgroup.create(mode="802.3ad",name=pg_name,\
                                       address=mac_addr,\
                                       node_uuid=node_id)
          except ironic_exc.Conflict as ex:
             self.logger.info(ex.message) # TO_FIX: handle so that this is not hit
          except Exception as ex:
             self.logger.info("ERROR: exception in creating PG")
             return

        self.portgroup_uuid = pg_obj.uuid

    def create_ironic_node(self,ironic_node_name,port_list,driver_info,properties):

        port_group_name                   = ironic_node_name + "_pg"

        if self.inputs.get_build_sku() in ['queens','ocata']:
           pxe_driver = "pxe_ipmitool"
        else:
           pxe_driver = "ipmi"
        node_obj = self.obj.node.create(name=ironic_node_name,driver=pxe_driver,\
                                        driver_info=driver_info,properties=properties)

        self.portgroup_uuid = None
        if len(port_list) > 1:
           pg_obj = self.create_ironic_portgroup(node_obj.uuid,port_group_name,\
                                           port_list[0]['mac_addr'])
           if pg_obj:
              self.portgroup_uuid = pg_obj.uuid
        for i,port in enumerate(port_list):
            port_dl = {}
            port_dl['switch_info'] = port['switch_info']
            port_dl['port_id']     = port['port_id']
            port_dl['switch_id']   = port['switch_id']
            self.create_ironic_port(port=port_dl,node_uuid=node_obj.uuid,\
                               mac_address=port['mac_addr'],
                               portgroup_uuid=self.portgroup_uuid,pxe_enabled=port['pxe_enabled'])
        return node_obj

    def set_node_power_state(self,node_id,state,soft=False):

        self.obj.node.set_power_state(node_id,state,soft)

    def set_ironic_node_state(self,node_id,new_state):

        if new_state == "available":
           self.obj.node.set_provision_state(node_id,"manage")
           self.obj.node.set_provision_state(node_id,"provide")

