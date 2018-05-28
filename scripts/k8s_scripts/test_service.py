from tcutils.util import skip_because
#import random
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from k8s.service import ServiceFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_lock
import test
from tcutils.util import get_random_name



class TestService(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestService, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['openshift_1'])
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
        assert service.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)
    # end test_service_1

    @preposttest_wrapper
    def test_service_type_nodeport_without_namespace_isolation(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced using NodePort service from with in the cluster
            outside of the cluster
        '''
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace = self.setup_namespace("ns1")
        assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()
        # validate Service Nodeport functionality with load-balancing on the service
        for node_ip in self.inputs.k8s_slave_ips:
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                            test_pod=pod3,
                                            nodePort=service.nodePort)
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                      nodePort=service.nodePort)
    # end test_service_type_nodeport__without_namespace_isolation

    @preposttest_wrapper
    def test_service_type_nodeport_with_namespace_isolation(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced using NodePort service using NodePort service from with in the cluster
            outside of the cluster with namespace isolation

        '''
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service = self.setup_http_service(namespace=namespace1.name,
                                          labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()
        # validate Service Nodeport functionality with load-balancing on the service
        for node_ip in self.inputs.k8s_slave_ips:
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                            test_pod=pod3,
                                            nodePort=service.nodePort)
             #access the Nodeport from outside the cluster
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                      nodePort=service.nodePort)
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                            test_pod=pod4,
                                            nodePort=service.nodePort,
                                            expectation=False)
    # end test_service_type_nodeport_with_namespace_isolation

    @preposttest_wrapper
    def test_service_type_nodeport_with_namespace_isolation_with_userdefined_nodeport(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced  NodePort service from with in the cluster 
            outside of the cluster with user defied noport

        '''
        app = 'http_nodeport_test'
        labels = {'app': app}
        user_node_port = 31111
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort", nodePort = user_node_port)
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()
        assert (service.nodePort == user_node_port) , "service should be having the node port which is user provided"
        # validate Service Nodeport functionality with load-balancing on the service
        for node_ip in self.inputs.k8s_slave_ips:
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                            test_pod=pod3,
                                            nodePort=user_node_port)
             #access the Nodeport from outside the cluster
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                      nodePort=user_node_port)
             assert self.validate_nginx_lb([pod1, pod2], node_ip,
                                            test_pod=pod4,
                                            nodePort=user_node_port,
                                            expectation=False)
    # end test_service_type_nodeport_with_namespace_isolation



    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_service_with_type_loadbalancer(self):
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
        assert service.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # When Isolation enabled we need to change SG to allow traffic
        # from outside. For that we need to disiable service isolation
        if self.setup_namespace_isolation:
            namespace.disable_service_isolation()

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])
    # end test_service_with_type_loadbalancer

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_service_access_from_different_ns(self):
        ''' Create a service  in one namespace with 2 pods
            Create a third busybox pod in different namespace
            Validate busybox pod can access the service in
            default mode.
            When isolation is enabled service should not be
            accessible from other namespace
        '''
        expectation = True
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        namespace1 = self.setup_namespace()
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()
        assert service.verify_on_setup()

        if self.setup_namespace_isolation:
            expectation = False
        url = 'http://%s' % (service.cluster_ip)
        assert self.validate_wget(pod3, url, expectation=expectation)
    # end test_service_access_from_different

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
        assert service.verify_on_setup()
        
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

    @test.attr(type=['k8s_sanity'])
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

# Isolated namespace classes follow

class TestServiceExternalIP(BaseK8sTest):
    @classmethod
    def setUpClass(cls):
        super(TestServiceExternalIP, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestServiceExternalIP, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['k8s_sanity'])
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_service_with_external_ip(self):
        ''' Create a service  with 2 pods running nginx
            Add annotation external_ip
            Create a third busybox pod and validate that webservice is
            load-balanced
            Validate that webservice is load-balanced from outside network
            using external_ip
            Please make sure BGP multipath and per packer load balancing
            is enabled on the MX
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        #assert namespace.verify_on_setup()
        # Make sure that no other test can use the external ip by accident
        pub_vn_fixture = self.public_vn.public_vn_fixture
        with get_lock(self.inputs.fip_pool):
            external_ips = pub_vn_fixture.alloc_ips(1)
            assert external_ips, 'No free IP available to use in public VN'
            pub_vn_fixture.free_ips(external_ips)
            service = self.setup_http_service(namespace=namespace.name,
                                              labels=labels,
                                              external_ips=external_ips)
        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()
        assert service.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # When Isolation enabled we need to change SG to allow traffic
        # from outside. For that we need to disiable service isolation
        if self.setup_namespace_isolation:
            namespace.disable_service_isolation()

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])
    # end test_service_with_external_ip

class TestServiceVNIsolated(TestService):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()
        cls.setup_namespace_isolation = True

class TestServiceExternalIPVNIsolated(TestServiceExternalIP):

    @classmethod
    def setUpClass(cls):
        super(TestServiceExternalIPVNIsolated, cls).setUpClass()
        cls.setup_namespace_isolation = True
