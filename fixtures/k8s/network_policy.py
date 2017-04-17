import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class NetworkPolicyFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata={},
                 spec={}):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('service')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = metadata
        self.spec = spec
        self.v1_beta_h = self.k8s_client.v1_beta_h

        self.already_exists = None

    def setUp(self):
        super(NetworkPolicyFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        pass
    # end verify_on_setup

    def cleanUp(self):
        super(NetworkPolicyFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        self.kind = self.obj.kind

    def read(self):
        try:
            self.obj = self.v1_beta_h.read_namespaced_network_policy(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Network policy %s not present' % (self.name))
            return None
    # end read

    def create(self):
        policy_exists = self.read()
        if policy_exists:
            return policy_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_network_policy(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_network_policy(self.namespace,
                                                         self.name)
    # end delete

    def update(self, metadata=None, spec=None):
        self.metadata = metadata or self.metadata
        self.spec = spec or self.spec
        self.obj = self.k8s_client.update_network_policy(
            self.name,
            self.namespace,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end create
