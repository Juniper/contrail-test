import base64
import fixtures
import tempfile
from fabric.api import local

from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class TLSSecretFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 data=None,
                 cert=None,
                 key=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('secret')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.data = {} if data is None else data
        self.v1_h = self.k8s_client.v1_h
        self.cert = cert or data.get('tls.crt') or None
        self.key = key or data.get('tls.key') or None

        self.already_exists = None

    def setUp(self):
        super(TLSSecretFixture, self).setUp()
        self.create()

    def cleanUp(self):
        self.delete()
        super(TLSSecretFixture, self).cleanUp()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.metadata_obj = self.obj.metadata
        self.kind = self.obj.kind

    def read(self):
        try:
            self.obj = self.v1_h.read_namespaced_secret(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Secret %s not present' % (self.name))
            return None
    # end read

    def get_cert_key(self):
        if self.cert and self.key:
            return
        key_file = tempfile.NamedTemporaryFile(prefix='key-')
        cert_file = tempfile.NamedTemporaryFile(prefix='cert-')
        cmd = ('openssl req -x509 -nodes -days 365 -newkey rsa:2048 '
               '-keyout %s -out %s -subj "/CN=k8stest/O=k8stest"' % (
                   key_file.name, cert_file.name))
        local(cmd)
        self.cert = open(cert_file.name, 'r').read()
        self.key = open(key_file.name, 'r').read()
    # end get_cert_key

    def create(self):
        secret_exists = self.read()
        if secret_exists:
            return secret_exists
        self.already_exists = False
        self.get_cert_key()
        self.data['tls.crt'] = base64.b64encode(self.cert.encode()).decode()
        self.data['tls.key'] = base64.b64encode(self.key.encode()).decode()

        self.obj = self.k8s_client.create_secret(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            data=self.data)
        self.logger.info('Created Secret %s' % (self.name))
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            result = self.k8s_client.delete_secret(self.namespace, self.name)
    # end delete
