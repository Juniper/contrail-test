import os
import openstack
from common.openstack_libs import swift_client as client
from common.openstack_libs import swift_exception as swiftException
from tcutils.util import retry
import hashlib

class SwiftHelper(object):
    '''
       Wrapper around swift client library
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
    # end get_auth_h

    def setUp(self):
        try:
            import pdb; pdb.set_trace()
            self.obj = client.Connection(session=self.auth_h.get_session(scope='project'))
        except:
            pass
    # end setUp

    def create_image(self, file_name, file_path):
        container_name = 'contrail_container'
        sh1 = self.get_sha1(file_path)
        md5 = self.get_md5(file_path)
        try:
            with open(file_path, 'rb') as file_to_upload:
                self.obj.put_object(container=container_name, obj=file_name, contents=file_to_upload, headers={'X-Object-Meta-md5': md5,'X-Object-Meta-sha1': sha1})
        except:
            print "UPLOAD FOR FILE %s TO SWIFT FAILED" %file_name
    # end create_image

    def delete_image(self, file_name):
        container_name = 'contrail_container'
        try:
            self.obj.delete_object(container=container_name, obj=file_name)
        except:
            print "DELETION OF FILE %s FROM SWIFT CONTAINER FAILED" %file_name
    # end delete_image

    def getObjectFileMeta(self, file_name):
        container_name = 'contrail_container'
        return self.obj.head_object(container=container_name, obj=file_name)
    # end getObjectFileMeta

    def get_md5(self, filepath):
        hasher = hashlib.md5()
        with open(filepath, 'rb') as file_to_upload:
            temp_buffer = file_to_upload.read(65536)
            while len(temp_buffer) > 0:
                hasher.update(temp_buffer)
                temp_buffer = file_to_upload.read(65536)
        return hasher.hexdigest()
    # end get_md5

    def get_sha1(self, filepath):
        hasher = hashlib.sha1()
        with open(filepath, 'rb') as file_to_upload:
            temp_buffer = file_to_upload.read(65536)
            while len(temp_buffer) > 0:
                hasher.update(temp_buffer)
                temp_buffer = file_to_upload.read(65536)
        return hasher.hexdigest()     
    # end get_sha1
