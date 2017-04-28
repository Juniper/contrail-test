import random

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
        labels = {'app': app}
        namespace = self.setup_namespace()
        #assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        pod1 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)
    # end test_service_1

    @preposttest_wrapper
    def test_service_2(self):
        ''' Create a service type loadbalancer with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            Validate that webservice is load-balanced from outside network
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
        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])
    # end test_service_2

    @preposttest_wrapper
    def test_service_scale_up_down(self):
        ''' Create a service with 10 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            Remove 5 pods from that service
            Validate that web-service is load-balanced among the remaining 5
             only
            Add 3 of the removed pods back
            Validate that web-service is load-balanced among the 8 pods only

        '''
        labels = {'app': 'http_test'}
        new_labels = {'app': 'http_test1'}
        all_pods = []
        barred_pods = []

        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()

        client_pod = self.setup_busybox_pod(namespace=namespace.name)
        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        for i in range(0, 10):
            pod = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
            all_pods.append(pod)
        # end for

        for pod in all_pods:
            assert self.verify_nginx_pod(pod)
        assert client_pod.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb(all_pods, service.cluster_ip,
                                      test_pod=client_pod)
        # Setup barred pods
        barred_pods = all_pods[-5:]
        for pod in barred_pods:
            pod.set_labels(new_labels)

        remaining_pods = [x for x in all_pods if x not in barred_pods]
        # LB should now happen only among the remaining pods
        msg = 'Service Load-balancing checks failed, check logs'
        assert self.validate_nginx_lb(remaining_pods, service.cluster_ip,
                                      test_pod=client_pod,
                                      barred_pods=barred_pods), msg
        self.logger.info('Scaling down of a service seems ok')
        # Add 3 pods back to the service
        for pod in barred_pods[:3]:
            pod.set_labels(labels)
        current_pods = remaining_pods + barred_pods[:3]
        new_barred_pods = barred_pods[-2:]
        assert self.validate_nginx_lb(current_pods, service.cluster_ip,
                                      test_pod=client_pod,
                                      barred_pods=new_barred_pods), msg
        self.logger.info('Scaling up of a service seems ok')

    # end test_service_scale_up_down

    @preposttest_wrapper
    def test_kube_dns_lookup(self):
        namespace = self.setup_namespace()
        client_pod = self.setup_busybox_pod(namespace=namespace.name)
        assert client_pod.verify_on_setup()
        lookup_str = 'nslookup kubernetes.default.svc.cluster.local'
        output = client_pod.run_cmd(lookup_str)
        msg = 'DNS resolution failed'
        assert 'nslookup: can\'t resolve' not in output, msg
        self.logger.info('DNS resolution check : %s passed. Output: %s' % (
            lookup_str, output))
    # end test_kube_dns_lookup
