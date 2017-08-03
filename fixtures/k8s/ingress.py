import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class IngressFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 default_backend=None,
                 rules=None,
                 tls=None,
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.inputs = connections.inputs
        self.name = name or metadata.get('name') or get_random_name('ingress')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.rules = [] if rules is None else rules
        self.tls = [] if tls is None else tls
        self.default_backend = {} if default_backend is None else default_backend
        self.v1_beta_h = self.k8s_client.v1_beta_h

        self.already_exists = None

    def setUp(self):
        super(IngressFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_ingress_in_k8s():
            self.logger.error('Ingress %s verification in kubernetes failed'
                              % (self.name))
            return False
        if not self.verify_ingress_in_contrail_api():
            self.logger.error('Ingress %s verification in Contrail api failed'
                              % (self.name))
            return False
        self.logger.info('Ingress %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        super(IngressFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        if self.obj.status.load_balancer.ingress:

            lb_ips = []
            # As per software handling all external_ips will be listed first and
            # Cluster IP will be at the end of list. 
            for item in  self.obj.status.load_balancer.ingress: 
                lb_ips.append(item.ip)
            self.cluster_ip =  lb_ips[-1] 
            del lb_ips[-1] 
            self.external_ips = lb_ips
        else:
            self.external_ips = None
            self.cluster_ip = None
    # end _populate_attr

    def read(self):
        try:
            self.obj = self.v1_beta_h.read_namespaced_ingress(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Ingress %s not present' % (self.name))
            return None
    # end read

    def create(self):
        ingress_exists = self.read()
        if ingress_exists:
            return ingress_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_ingress(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            default_backend=self.default_backend,
            rules=self.rules,
            tls=self.tls,
            spec=self.spec)
        self.logger.info('Created Ingress %s' % (self.name))
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_ingress(self.namespace, self.name)
    # end delete

    @retry(delay=1, tries=10)
    def verify_ingress_in_contrail_api(self):
        # TODO
        return True
    # end verify_ingress_in_contrail_api

    @retry(delay=3, tries=20)
    def verify_ingress_in_k8s(self):
        self.read()
        if not self.cluster_ip:
            self.logger.debug('Cluster IP not yet seen for Ingress '
                              '%s' % (self.name))
            return False
        if not self.external_ips:
            self.logger.debug('External IP not yet seen for Ingress '
                              '%s' % (self.name))
            return False
        self.logger.debug('For Ingress %s, Cluster IP: %s, External IPs %s' % (
                          self.name, self.cluster_ip, self.external_ips))
        self.logger.info('Verifications in k8s passed for Ingress %s' % (
                         self.name))
        return True
    # end verify_ingress_in_k8s
