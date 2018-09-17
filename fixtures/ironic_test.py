import os
import openstack
from common.openstack_libs import ironic_client as client

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
        inputs = kwargs.get('inputs')
        self.logger = kwargs.get('logger') or inputs.logger if inputs \
                          else contrail_logging.getLogger(__name__)
        self.region_name = kwargs.get('region_name') or \
                           inputs.region_name if inputs else None
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def setUp(self):
        self.obj = client.get_client('1',
                       session=self.auth_h.get_session(scope='project'),
                       os_region_name=self.region_name)
        self.obj.http_client.api_version_select_state='user'
        self.obj.http_client.os_ironic_api_version="1.31"
    # end setUp

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)
