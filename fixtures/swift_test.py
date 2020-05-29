from future import standard_library
from builtins import object
import os
import openstack
import hashlib
from urllib.parse import urlparse
from common.openstack_libs import swift_client
from tcutils.util import *
from fabric.context_managers import settings, hide, cd, shell_env
from fabric.api import run, local, env
from fabric.operations import get, put
from tcutils.cfgparser import parse_cfg_file

class SwiftHelper(object):
    def __init__(self, auth_h=None, **kwargs):
        self.inputs = kwargs.get('inputs')
        self.obj = None
        self.logger = kwargs.get('logger') or self.inputs.logger if self.inputs \
            else contrail_logging.getLogger(__name__)
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h
        self.images_info = parse_cfg_file('configs/device_images.cfg')
        self.images_dir = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), '..', 'images'))
        self.container_name = None
        self.object_hash_values = {}
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def setUp(self):
        try:
            self.obj = swift_client.Connection(
                session=self.auth_h.get_session(scope='project'))
        except:
            self.logger.error("Failed to establish connection to swift")
    # end setUp

    def create_container(self):
        if not self.container_name:
            self.container_name = get_random_name('contrail-container')
            try:
                self.obj.put_container(self.container_name)
                self.logger.info(
                    "Created swift container - {}".format(self.container_name))
            except Exception as e:
                self.logger.error(
                    "Error in creating swift container - {}".format(e))

    def create_object(self, image_name, object_path):
        self.create_container()
        object_name = self.images_info[image_name]['name']
        object_extension = self.get_filetype(object_path)
        content_type = None
        if object_extension == '.tgz':
            content_type = 'application/x-tar'
        sha1 = self.get_sha1(object_path)
        md5 = self.get_md5(object_path)
        try:
            with open(object_path, 'rb') as object_content:
                resp = self.obj.put_object(self.container_name, object_name,
                                           object_content, content_type=content_type,
                                           headers={
                                               'X-Object-Meta-md5': md5,
                                               'X-Object-Meta-sha1': sha1})
            self.logger.info("Created swift object - {}".format(object_name))
            file_uri = "/%s/%s"%(self.container_name, object_name)
            download_url = self.obj.url + file_uri
            device_image_uri = urlparse(download_url).path
            object_info = {'file_name': object_name,
                           'md5': md5,
                           'sha1': sha1,
                           'public_file_uri': device_image_uri,
                           'supported_platforms': \
                                self.images_info[image_name]['supported-platforms'],
                           'device_family': \
                                self.images_info[image_name]['device-family'],
                           'os_version': self.images_info[image_name]['os-version']}
            self.object_hash_values[image_name] = object_info
        except Exception as e:
            self.logger.error(
                "Error in creating swift object - {}".format(e))

    def find_object(self, name):
        object_name = self.images_info[name]['name']
        try:
            resp = self.obj.head_object(self.container_name, object_name)
            self.logger.info("find object response - {}".format(resp))
        except Exception as e:
            self.logger.error(
                "could not find object - {}".format(e))

    def get_filetype(self, abs_file_path):
        _, file_extension = os.path.splitext(abs_file_path)
        return file_extension

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

    def get_object_uri(self, device_image_list):
        for device_image in device_image_list:
            self.get_object(device_image)
        return self.object_hash_values
    # end get_object_uri

    def get_object(self, image_name='junos-qfx-18.4R2.7'):
        if image_name not in self.object_hash_values.keys():
            self._install_image(image_name=image_name)

    def _install_image(self, image_name):
        self.logger.debug('Installing image %s' % image_name)
        image_info = self.images_info[image_name]
        webserver = image_info['webserver'] or self.inputs.image_web_server
        location = image_info['location']
        image = image_info['name']
        if os.path.isfile("%s/%s" % (self.images_dir, image)):
            build_path = "file://%s/%s" % (self.images_dir, image)
        elif re.match(r'^file://', location):
            build_path = '%s/%s' % (location, image)
        else:
            build_path = 'http://%s/%s/%s' % (webserver, location, image)
        img_abs_path = self.download_image(build_path, do_local=True)
        self.create_object(image_name, img_abs_path)

    def download_image(self, image_url, folder='/tmp', do_local=False):
        basename = os.path.basename(image_url)
        filename = '%s/%s'%(folder, basename)
        if re.match(r'^file://', image_url):
            abs_path = re.sub('file://','',image_url)
            if not re.match(r'^/', abs_path):
                abs_path = '/' + abs_path
            if os.path.exists(abs_path):
                if do_local:
                    return abs_path
                put(abs_path, filename)
                return filename
        elif re.match(r'^(http|https)://', image_url):
            local('mkdir -p %s'%folder)
            if not os.path.exists(filename):
                self.execute_cmd_with_proxy(
                    "wget %s -O %s" % (image_url, filename), do_local=do_local)
            return filename

    def execute_cmd_with_proxy(self, cmd, do_local=False):
        if self.inputs.http_proxy:
            with shell_env(http_proxy=self.inputs.http_proxy):
                local(cmd) if do_local else sudo(cmd)
        else:
            local(cmd) if do_local else sudo(cmd)
