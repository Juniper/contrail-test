import os
import openstack
from common.openstack_libs import swift_client as client
from common.openstack_libs import swift_exception as swiftException
from tcutils.util import retry
import hashlib
from common import log_orig as contrail_logging
import subprocess

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
    def __init__(self, auth_h=None, container_name='contrail_container', **kwargs):
        inputs = kwargs.get('inputs')
        self.logger = kwargs.get('logger') or inputs.logger if inputs \
                          else contrail_logging.getLogger(__name__)
        self.region_name = kwargs.get('region_name') or \
                           inputs.region_name if inputs else None
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.images_info = parse_cfg_file('configs/images.cfg')
        self.container_name = container_name
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)
    # end get_auth_h

    def setUp(self):
        try:
            self.obj = client.Connection(session=self.auth_h.get_session(scope='project'))
        except:
            pass
    # end setUp

    def create_image(self, image_name=None, file_path='/tmp/'):
        sha1 = self.get_sha1(file_path)
        md5 = self.get_md5(file_path)
        if not image_name:
            self.logger.info('Image Name Empty:')
            return
        try:
            image_info = self.images_info[image_name]
            actual_name_of_file = image_info['name']
            exact_path_to_file = file_path + actual_name_of_file
            self.download_image(image_name)
            with open(exact_path_to_file, 'rb') as file_to_upload:
                self.obj.put_object(container=self.container_name, obj=actual_name_of_file, contents=file_to_upload, headers={'X-Object-Meta-md5': md5,'X-Object-Meta-sha1': sha1})
        except:
            self.logger.info('UPLOAD FOR FILE %s TO SWIFT FAILED' % (file_name))
    # end create_image

    def delete_image(self, file_name):
        try:
            self.obj.delete_object(container=self.container_name, obj=file_name)
        except:
            self.logger.info('DELETION OF FILE %s FROM SWIFT CONTAINER FAILED' % (file_name))
    # end delete_image

    def download_image(self, image_name):
        image_info = self.images_info[image_name]
        webserver = image_info['webserver'] or self.inputs.image_web_server
        location = image_info['location']
        actual_name_of_file = image_info['name']
        full_path = 'http://%s/%s/%s' % (webserver, location, actual_name_of_file)
        command = 'wget -P /tmp/ %s' % (full_path)
        try:
          result = subprocess.check_output( command, stderr=subprocess.STDOUT, shell=True )
          self.logger.info('Executed Command: %s\n' % (command))
          self.logger.info('%s' % (result)) 
        except:
          self.logger.info('Errors while executing the following command: %s\n' % (command))
          self.logger.info('%s' % (stderr))
    # end download_image

    def get_image(self, file_name):
        return self.obj.head_object(container=self.container_name, obj=file_name)
    # end get_image

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
