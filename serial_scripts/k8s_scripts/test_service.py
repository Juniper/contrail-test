import random
import time
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from k8s.service import ServiceFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_lock
import test
import os

class TestService(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestService, cls).tearDownClass()
    
    def is_test_applicable(self):
        if not os.environ.get('MX_GW_TEST') == '1':
            return(False, 'Needs MX_GW_TEST to be set')
        return (True, None)
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_service_with_kube_manager_restart(self):
        ''' Create a service type loadbalancer with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            Validate that webservice is load-balanced from outside network
            Restart kube-manager and verify service 
            Please make sure BGP multipath and per packer load balancing
            is enabled on the MX
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        #assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels, type='LoadBalancer')
        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # When Isolation enabled we need to change SG to allow traffic
        # from outside. For that we need to disiable service isolation
        if self.setup_namespace_isolation:
            namespace.disable_service_isolation()

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])

        self.restart_kube_manager()
        time.sleep(5)
 
        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])

