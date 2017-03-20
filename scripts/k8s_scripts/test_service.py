
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from k8s.service import ServiceFixture
from tcutils.wrappers import preposttest_wrapper

class TestService(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestService, cls).tearDownClass()

    @preposttest_wrapper
    def test_service_1(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
        '''
        app = 'http_test'
        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          app=app)
        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                   app=app)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                   app=app)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod3.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)
    # end test_service_1

