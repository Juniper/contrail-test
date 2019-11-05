from builtins import object
import os
import openstack
from common.openstack_libs import glance_client as client
from common.openstack_libs import glance_exception as glanceException
from tcutils.util import retry

class GlanceHelper(object):
    '''
       Wrapper around glance client library
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
        self.obj = client('2', session=self.auth_h.get_session(scope='project'),
                          region_name=self.region_name)
    # end setUp

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def create_image(self, name, filename=None, public=True, **kwargs):
        if public:
           kwargs.update({'visibility': 'public'})
        obj = self.obj.images.create(name=name, **kwargs)
        if filename:
            self.upload_image(obj['id'], filename)

    def upload_image(self, uuid, filename):
        self.obj.images.upload(uuid, open(filename, 'rb'))

    def get_image(self, image_id=None, image_name=None, check_active=True):
        if not image_id:
            for image in self.obj.images.list():
                if image.name == image_name:
                    image_id = image.id
                    break
            else:
                self.logger.debug('Image by name %s not found'%image_name)
                return False
        if not image_id:
            self.logger.debug('image_id cant be empty')
            return False
        try:
            if check_active:
                return self.is_active(image_id)[1]
            return self.obj.images.get(image_id)
        except glanceException.NotFound:
            return None

    @retry(delay=5, tries=20)
    def is_active(self, image_id):
        image = self.obj.images.get(image_id)
        if image.status.lower() == 'active':
            return (True, image)
        return (False, None)
