from common.k8s.base import BaseK8sTest
from k8s.ingress import IngressFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
import test

class TestIngressTLS(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestIngressTLS, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestIngressTLS, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['k8s_sanity']) 
    @skip_because(mx_gw = False, slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_ingress_tls_1(self):
        ''' Create a service with 2 pods running nginx
            Create an ingress out of this service
            From the local node, do a wget on the ingress public ip
            Validate that service and its loadbalancing works

            For now, do this test only in default project
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        tls_secret = self.setup_tls_secret(namespace=namespace.name)
        ingress = self.setup_simple_nginx_ingress(service.name,
                                                  namespace=namespace.name,
                                                  tls=[tls_secret.name])

        pod1 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)
        assert ingress.verify_on_setup()

        self.verify_nginx_pod(pod1)
        self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([pod1, pod2], ingress.cluster_ip,
                                      test_pod=pod3, protocol='https',
                                      port='443')

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], ingress.external_ips[0],
                                      protocol='https', port='443')
        ingress.disable_tls()
        link = 'https://%s:443' % (ingress.cluster_ip)
        assert self.validate_wget(pod3, link, expectation=False)

        # Enable it again
        ingress.enable_tls()
        assert self.validate_nginx_lb([pod1, pod2], ingress.external_ips[0],
                                      protocol='https', port='443')
    # end test_ingress_tls_1
