import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry

class ServiceFixture(fixtures.Fixture):
    '''
    '''
    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('service')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.v1_h = self.k8s_client.v1_h

        self.already_exists = None

    def setUp(self):
        super(ServiceFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_service_in_contrail_api():
            self.logger.error('Service %s verification in Contrail api failed'
                              % (self.name))
            return False
        self.logger.info('Service %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        super(ServiceFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.cluster_ip = self.obj.spec.cluster_ip
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        self.kind = self.obj.kind
        self.type = self.obj.spec.type

        # While creating the object it is not getting updated with external IP
        # So reading it again . Will try to read it couple of times
        if self.type == 'LoadBalancer' or 'external_i_ps' in self.spec:
            self.get_external_ips()

    def read(self):
        try:
            self.obj = self.v1_h.read_namespaced_service(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Service %s not present' % (self.name))
            return None
    # end read

    def create(self):
        service_exists = self.read()
        if service_exists:
            return service_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_service(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
        self.logger.info('Created Service %s' % (self.name))
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_service(self.namespace, self.name)
    # end delete

    @retry(delay=1, tries=10)
    def verify_service_in_contrail_api(self):
        try:
            obj = self.vnc_api_h.loadbalancer_read(id=self.uuid)
        except NoIdError:
            self.logger.warn(
                'Service UUID %s not yet found in contrail-api' %
                (self.uuid))
            return False
        exp_name = 'service-%s' % (self.name)
        if obj.name != exp_name:
            self.logger.warn(
                'Service %s name not matching that in contrail-api'
                'Expected : %s, Got : %s' %
                (self.name, exp_name, obj.name))
            return False
        self.logger.info('Validated that Service %s is seen in '
                         'contrail-api' % (self.name))
        return True
    # end verify_service_in_contrail_api

    @retry(delay=1, tries=10)
    def get_external_ips(self):
        self.external_ips = None
        self.new_obj = self.v1_h.read_namespaced_service(
            self.name, self.namespace)
        self.external_ips = self.new_obj.spec.external_i_ps
        if self.external_ips is None:
            self.logger.error('Service %s does not have any external_ip'
                              % (self.name))
            return False
        return True
    # end verify_service_in_contrail_api   
