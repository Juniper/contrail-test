import fixtures
from kubernetes.client.rest import ApiException
from kubernetes import client
from vnc_api.vnc_api import NoIdError

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry

class NamespaceFixture(fixtures.Fixture):
    '''
    '''
    def __init__(self, connections, name=None):
        self.connections = connections
        self.logger = connections.logger or contrail_logging.getLogger(__name__)
        self.name = name or get_random_name('namespace')
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib

        self.already_exists = False

    def setUp(self):
        super(NamespaceFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_namespace_is_active():
            self.logger.error('Namespace %s verification failed' %(
                               self.name))
            return False
        if not self.verify_namespace_in_contrail_api():
            self.logger.error('Namespace %s not seen in Contrail API' %(
                               self.name))
            return False
        self.logger.info('Namespace %s verification passed' % (self.name))
        return True
    # end verify_on_setup 


    @retry(delay=1, tries=10)
    def verify_namespace_is_active(self):
        if self.status != 'Active':
            self.logger.warn('Namespace %s is not Active yet, It is %s' %(
                             self.name, self.status))
            return False
        return True
    # end verify_namespace_is_active

    @retry(delay=1, tries=10)
    def verify_namespace_in_contrail_api(self):
        try:
            # TODO
            # Check for fq name for now until bug 1665233 is resolved
            #self.vnc_api_h.project_read(id=self.uuid)
            self.vnc_api_h.project_read(fq_name=['default-domain', self.name])
        except NoIdError:
            self.logger.warn('Namespace %s UUID %s not in contrail-api' %(
                             self.name, self.uuid))
            return False
        self.logger.info('Namespace %s is seen in contrail-api' % (self.name))
        return True
    # end verify_namespace_in_contrail_api

    def cleanUp(self):
        super(NamespaceFixture, self).cleanUp()
        self.delete()
        self.logger.info('Deleted namespace %s' % (self.name))

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.status = self.obj.status.phase

    def read(self):
        try:
            self.obj = self.k8s_client.v1_h.read_namespace(self.name)
            self._populate_attr()
            self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Namespace %s not present' % (self.name))
            return None
    # end read

    def create(self):
        ns_exists = self.read()
        if ns_exists:
            self.logger.info('Namespace %s already exists' % (self.name))
            return ns_exists
        body = client.V1Namespace()
        body.metadata = client.V1ObjectMeta(name=self.name)
        self.obj = self.k8s_client.v1_h.create_namespace(body)
        self._populate_attr() 
        self.logger.info('Created namespace %s' % (self.name))
    # end create

    def delete(self):
        if not self.already_exists:
            body = client.V1DeleteOptions()
            return self.k8s_client.v1_h.delete_namespace(self.name, body)
    # end delete

