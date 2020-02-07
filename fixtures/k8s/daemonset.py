import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry

class DaemonSetFixture(fixtures.Fixture):
    '''
    Create a daemonset 
    Refer https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1SaemonSet.md 
    '''
    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('daemonset')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.v1_beta_h = self.k8s_client.v1_beta_h
        self.apps_v1_h = self.k8s_client.apps_v1_h
        self.already_exists = None

    def setUp(self):
        super(DaemonSetFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_daemonset_in_k8s():
            self.logger.error('Daemonset %s verification in kubernetes failed'
                              % (self.name))
            return False
        self.logger.info('Daemonset %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        self.delete()
        super(DaemonSetFixture, self).cleanUp()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        self.status = self.obj.status
        self.current = self.status.current_number_scheduled
        self.desired = self.status.desired_number_scheduled
        self.available = self.status.number_available
        self.ready = self.status.number_ready
    # end _populate_attr

    def read(self):
        try:
            self.obj = self.apps_v1_h.read_namespaced_daemon_set(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Daemonset %s not present' % (self.name))
            return None
    # end read

    def create(self):
        daemonset_exists = self.read()
        if daemonset_exists:
            return daemonset_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_daemonset(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_daemonset(self.namespace, self.name)
    # end delete

    @retry(delay=5, tries=60)
    def verify_daemonset_in_k8s(self):
        self.read()
        self.logger.debug('Available: %s,Ready:%s , Desire: %s' %(
            self.available, self.ready,self.desired))
        if not self.available:
            self.logger.debug('Replica details not yet seen for dep %s' %(
                self.name))
            return False
        if self.desired != self.ready:
            self.logger.debug('Daemonset %s not fully available' %(self.name))
            return False
        else:
            self.logger.debug('Deployment %s is marked fully available in k8s' %(
                self.name))
        self.logger.info('Verifications in k8s passed for daemonset %s' % (
                         self.name))
        return True
    # end verify_daemonset_in_k8s

    def get_pods_list(self):
        return self.k8s_client.get_pods_list(self.namespace,
            deployment=self.name)
    # end get_pods_list
