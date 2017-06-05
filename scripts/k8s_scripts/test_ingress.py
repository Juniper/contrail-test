
from common.k8s.base import BaseK8sTest
from k8s.ingress import IngressFixture
from tcutils.wrappers import preposttest_wrapper


class TestIngress(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestIngress, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestIngress, cls).tearDownClass()

    @preposttest_wrapper
    def test_ingress_1(self):
        ''' Create a service with 2 pods running nginx
            Create an ingress out of this service
            From the local node, do a wget on the ingress public ip
            Validate that service and its loadbalancing works

            For now, do this test only in default project
        '''
        app = 'http_test'
        labels = {'app':app}
        namespace = self.setup_namespace(name='default')
        assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        pod1 = self.setup_nginx_pod(namespace=namespace.name, 
                                          labels=labels)

        pod2 = self.setup_nginx_pod(namespace=namespace.name, 
                                          labels=labels)

        ingress = self.setup_simple_nginx_ingress(service.name,
                                                  namespace=namespace.name)
        assert ingress.verify_on_setup()

        pod3 = self.setup_busybox_pod(namespace=namespace.name)
        self.verify_nginx_pod(pod1)
        self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([pod1, pod2], ingress.cluster_ip,
                                      test_pod=pod3)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], ingress.external_ips[0])
    # end test_service_1
