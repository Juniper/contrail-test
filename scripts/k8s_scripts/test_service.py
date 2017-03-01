
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
                                   app=app,
                                   container_port=10000)
        assert pod1.verify_on_setup()

        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                   app=app,
                                   container_port=10001)
        assert pod2.verify_on_setup()

        pod3 = self.setup_busybox_pod(namespace=namespace.name)
        assert pod3.verify_on_setup()

        # Now fetch URL of service

    # end test_service_1

