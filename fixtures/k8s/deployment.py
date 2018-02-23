import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class DeploymentFixture(fixtures.Fixture):
    '''
    Create a deployment
    Refer https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/docs/AppsV1beta1Deployment.md
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('deployment')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.v1_beta_h = self.k8s_client.v1_beta_h

        self.already_exists = None

    def setUp(self):
        super(DeploymentFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_deployment_in_k8s():
            self.logger.error('Deployment %s verification in kubernetes failed'
                              % (self.name))
            return False
        self.logger.info('Deployment %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        super(DeploymentFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        self.status = self.obj.status
        self.available_replicas = self.status.available_replicas
        self.replicas = self.spec_obj.replicas
    # end _populate_attr

    def read(self):
        try:
            self.obj = self.v1_beta_h.read_namespaced_deployment(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Deployment %s not present' % (self.name))
            return None
    # end read

    def create(self):
        deployment_exists = self.read()
        if deployment_exists:
            return deployment_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_deployment(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            # Delete RS first 
            # https://github.com/kelproject/pykube/issues/87
            self.k8s_client.delete_replica_set(self.namespace, self.name)
            return self.k8s_client.delete_deployment(self.namespace, self.name)
    # end delete

    @retry(delay=5, tries=40)
    def verify_deployment_in_k8s(self):
        self.read()
        self.logger.debug('Replicas: %s, Available: %s' %(
            self.replicas, self.available_replicas))
        if not self.available_replicas:
            self.logger.debug('Replica details not yet seen for dep %s' %(
                self.name))
            return False
        if self.replicas != self.available_replicas:
            self.logger.debug('Deployment %s not fully available' %(self.name))
            return False
        else:
            self.logger.debug('Deployment %s is marked fully available in k8s' %(
                self.name))
        self.logger.info('Verifications in k8s passed for deployment %s' % (
                         self.name))
        return True
    # end verify_deployment_in_k8s

    def get_pods_list(self):
        return self.k8s_client.get_pods_list(self.namespace,
            deployment=self.name)
    # end get_pods_list

    def set_replicas(self, count):
        self.replicas = count
        return self.k8s_client.set_deployment_replicas(self.namespace,
            self.name, count)
