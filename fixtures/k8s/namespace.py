import time
import fixtures
from kubernetes.client.rest import ApiException
from kubernetes import client
from vnc_api.vnc_api import NoIdError

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class NamespaceFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self, connections, name=None, isolation=False):
        self.connections = connections
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or get_random_name('namespace')
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.isolation = isolation

        self.already_exists = False

    def setUp(self):
        super(NamespaceFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_namespace_is_active():
            self.logger.error('Namespace %s verification failed' % (
                self.name))
            return False
        # TODO
        # Update to work in all namespace modes
        # Until then, skip verifications
        return True

        if not self.verify_namespace_in_contrail_api():
            self.logger.error('Namespace %s not seen in Contrail API' % (
                self.name))
            return False
        self.logger.info('Namespace %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    @retry(delay=1, tries=10)
    def verify_namespace_is_active(self):
        if self.status != 'Active':
            self.logger.warn('Namespace %s is not Active yet, It is %s' % (
                             self.name, self.status))
            return False
        return True
    # end verify_namespace_is_active

    @retry(delay=1, tries=10)
    def verify_namespace_in_contrail_api(self):
        try:
            # TODO
            # Check for fq name for now until bug 1665233 is resolved
            # self.vnc_api_h.project_read(id=self.uuid)
            self.vnc_api_h.project_read(fq_name=['default-domain', self.name])
        except NoIdError:
            self.logger.warn('Namespace %s UUID %s not in contrail-api' % (
                             self.name, self.uuid))
            return False
        self.logger.info('Namespace %s is seen in contrail-api' % (self.name))
        return True
    # end verify_namespace_in_contrail_api

    def cleanUp(self):
        super(NamespaceFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.status = self.obj.status.phase
        self.labels = self.obj.metadata.labels

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
        if self.isolation:
            body.metadata.annotations = {"opencontrail.org/isolation": "true"}
        self.obj = self.k8s_client.v1_h.create_namespace(body)
        self._populate_attr()
        self.logger.info('Created namespace %s' % (self.name))
        # TODO
        # Need to remove
        time.sleep(3)
    # end create

    def delete(self):
        if not self.already_exists:
            body = client.V1DeleteOptions()
            self.logger.info('Deleting namespace %s' % (self.name))
            self.k8s_client.v1_h.delete_namespace(self.name, body)
            assert self.verify_on_cleanup()
    # end delete

    def verify_on_cleanup(self):
        assert self.verify_ns_is_not_in_k8s(), ('Namespace deletion '
                                                'verification in k8s failed')
        return True
    # end verify_on_cleanup

    @retry(delay=2, tries=30)
    def verify_ns_is_not_in_k8s(self):
        if self.k8s_client.is_namespace_present(self.name):
            self.logger.debug('Namespace %s still in k8s' % (self.name))
            return False
        else:
            self.logger.debug('Namespace %s is not in k8s' % (self.name))
            return True
    # end verify_ns_is_not_in_k8s

    def enable_isolation(self):
        return self.k8s_client.set_isolation(self.name)

    def disable_isolation(self):
        return self.k8s_client.set_isolation(self.name, False)

    def set_labels(self, label_dict):
        self.obj = self.k8s_client.set_namespace_label(self.name, label_dict)
        self._populate_attr()
    # end set_labels
   
    def enable_service_isolation(self):
        return self.k8s_client.set_service_isolation(self.name, enable=True)

    def disable_service_isolation(self):
        return self.k8s_client.set_service_isolation(self.name, enable=False)
