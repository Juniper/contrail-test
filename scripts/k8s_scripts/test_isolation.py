from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name

class TestNSIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNSIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNSIsolation, cls).tearDownClass()
    
    def setup_common_namespaces_pods(self, prov_service = False, prov_ingress = False):
        service_ns1, ingress_ns1 = None, None
        service_ns2, ingress_ns2 = None, None
        service_ns3, ingress_ns3 = None, None
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace3_name = get_random_name("ns3")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        namespace3 = self.setup_namespace(name = namespace3_name)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        assert namespace3.verify_on_setup()
        ns_1_label = "namespace1"
        ns_2_label = "namespace2"
        ns_3_label = "namespace3"
        client1_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client2_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client3_ns1 = self.setup_busybox_pod(namespace=namespace1_name)
        client1_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client2_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client3_ns2 = self.setup_busybox_pod(namespace=namespace2_name)
        client1_ns3 = self.setup_nginx_pod(namespace=namespace3_name,
                                             labels={'app': ns_3_label})
        client2_ns3 = self.setup_nginx_pod(namespace=namespace3_name,
                                             labels={'app': ns_3_label})
        client3_ns3 = self.setup_busybox_pod(namespace=namespace3_name)
        assert self.verify_nginx_pod(client1_ns1)
        assert self.verify_nginx_pod(client2_ns1)
        assert client3_ns1.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns2)
        assert self.verify_nginx_pod(client2_ns2)
        assert client3_ns2.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns3)
        assert self.verify_nginx_pod(client2_ns3)
        assert client3_ns3.verify_on_setup()
        if prov_service == True:
            service_ns1 = self.setup_http_service(namespace=namespace1.name,
                                          labels={'app': ns_1_label})
            service_ns2 = self.setup_http_service(namespace=namespace2.name,
                                          labels={'app': ns_2_label})
            service_ns3 = self.setup_http_service(namespace=namespace3.name,
                                          labels={'app': ns_3_label})
        if prov_ingress == True:
            ingress_ns1 = self.setup_simple_nginx_ingress(service_ns1.name,
                                                  namespace=namespace1.name)
            ingress_ns3 = self.setup_simple_nginx_ingress(service_ns3.name,
                                                  namespace=namespace3.name)
            assert ingress_ns1.verify_on_setup()
            assert ingress_ns3.verify_on_setup()
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1, ingress_ns1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2]
        client3 = [client1_ns3, client2_ns3, client3_ns3, service_ns3,\
                    namespace3, ingress_ns3]
        return (client1, client2, client3)
    #end setup_common_namespaces_pods

    @preposttest_wrapper
    def test_pods_isolation(self):
        """
        Pods created in isolated namespace can reach pods in other namespaces.
        """
        client1, client2, client3 = self.setup_common_namespaces_pods()
        assert client1[2].ping_to_ip(client3[0].pod_ip)
        assert client2[2].ping_to_ip(client3[0].pod_ip)
    #end test_pods_isolation

    @preposttest_wrapper
    def test_pods_isolation_negative(self):
        """
        Pods in other namespaces in the Kubernetes cluster will NOT be able to reach pods in the isolated namespace.
        Verify 2 combinations here:
        1. Pods of isolated namespace are not able to reach pods in isolated namespace
        2. Pods of non isolated namespace are also not able to reach pods in isolated namespace
        """
        client1, client2, client3 = self.setup_common_namespaces_pods()
        #Check 1:
        assert client1[2].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client2[2].ping_to_ip(client1[0].pod_ip, expectation=False)
        #Check 2:
        assert client3[2].ping_to_ip(client1[0].pod_ip, expectation=False)
        assert client3[2].ping_to_ip(client2[0].pod_ip, expectation=False)
    #end test_pods_isolation_negative

    @preposttest_wrapper
    def test_communication_from_isolated_ns_via_service(self):
        """
        Pods in isolated namespace will be able to reach ALL Services created in any namespace in the kubernetes cluster.
        Verify following as part of this test case:
        1. Pods in isolated namespace should reach pods of non isolated namespace using service.
        2. Pods in isolated namespace should reach pods of other isolated namespace using service.
        """
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True)
        #Check 1:
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[3].cluster_ip,
                                      test_pod=client1[2])
        #Disabling Service Isolation on the isolated namespace
        client2[4].disable_service_isolation()
        #Check 2:
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
    #end test_communication_from_isolated_ns_via_service

    @preposttest_wrapper
    def test_communication_from_non_isolated_to_service_in_isolated(self):
        """
        Pods in isolated namespace can be reached from pods in other namespaces through Kubernetes Service-ip
        """
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True)
        client1[4].disable_service_isolation()
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client3[2])
    #end test_communication_from_non_isolated_to_service_in_isolated

    @preposttest_wrapper
    def test_ingress_isolation(self):
        """
        Verify following as part of this test case:
        1. Pods in isolated namespace should reach pods of non isolated namespace using ingress.
        2. Ingress inside isolated namespace should be reachable from public network
        """
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True,
                                                                      prov_ingress = True)
        #Check 1:
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[5].cluster_ip,
                                      test_pod=client1[2])
        #Disabling Service Isolation on the isolated namespace
        client1[4].disable_service_isolation()
        #Check 2:
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
    #end test_ingress_isolation

class TestCustomIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestCustomIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestCustomIsolation, cls).tearDownClass()

    def setup_common_namespaces_pods(self, prov_service = False, prov_ingress = False):
        service_ns1, ingress_ns1 = None, None
        service_ns2, ingress_ns2 = None, None
        vn_for_namespace = self.setup_vn(vn_name = "TestVNNamespace")
        vn_dict_for_namespace = {"domain": vn_for_namespace.domain_name,
                   "project" : vn_for_namespace.project_name[0],
                   "name": vn_for_namespace.vn_name}
        vn_for_pod = self.setup_vn(vn_name = "TestVNPod")
        vn_dict_for_pod = {"domain": vn_for_pod.domain_name,
                   "project" : vn_for_pod.project_name[0],
                   "name": vn_for_pod.vn_name}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name)
        assert namespace1.verify_on_setup()
        namespace2 = self.setup_namespace(name = namespace2_name, custom_isolation = True,
                                           fq_network_name= vn_dict_for_namespace,
                                           isolation=True)
        assert namespace2.verify_on_setup()
        ns_1_label = "namespace1"
        ns_2_label = "namespace2"
        client1_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client2_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client3_ns1 = self.setup_busybox_pod(namespace=namespace1_name)
        client4_ns1 = self.setup_busybox_pod(namespace=namespace1_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        client5_ns1 = self.setup_busybox_pod(namespace=namespace1_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        client1_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client2_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client3_ns2 = self.setup_busybox_pod(namespace=namespace2_name)
        client4_ns2 = self.setup_busybox_pod(namespace=namespace2_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        assert self.verify_nginx_pod(client1_ns1)
        assert self.verify_nginx_pod(client2_ns1)
        assert client3_ns1.verify_on_setup()
        assert client4_ns1.verify_on_setup()
        assert client5_ns1.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns2)
        assert self.verify_nginx_pod(client2_ns2)
        assert client3_ns2.verify_on_setup()
        assert client4_ns2.verify_on_setup()
        if prov_service == True:
            service_ns1 = self.setup_http_service(namespace=namespace1.name,
                                          labels={'app': ns_1_label})
            service_ns2 = self.setup_http_service(namespace=namespace2.name,
                                          labels={'app': ns_2_label})
        if prov_ingress == True:
            ingress_ns2 = self.setup_simple_nginx_ingress(service_ns2.name,
                                                  namespace=namespace2.name)
            assert ingress_ns2.verify_on_setup()
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1, ingress_ns1, client4_ns1, client5_ns1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2, ingress_ns2, client4_ns2]
        return (client1, client2)
    #end setup_common_namespaces_pods
        
    @preposttest_wrapper
    def test_pod_custom_isolation(self):
        """
        Verify reachability of a custom isolated Pod to other Pods of same namespace
        Verify following reachability:
        1. Custom Isolated Pod of a namespace should not be able to reach to any other pod
        2. Custom Isolated Pod of a namespace should be able to reach another custom Isolated Pod
        """
        client1, client2 = self.setup_common_namespaces_pods()
        #Check 1
        assert client1[6].ping_to_ip(client1[0].pod_ip, expectation=False)
        assert client1[2].ping_to_ip(client1[6].pod_ip, expectation=False)
        assert client1[6].ping_to_ip(client2[0].pod_ip, expectation=False)
        #Check 2
        assert client1[6].ping_to_ip(client1[7].pod_ip)
        assert client1[6].ping_to_ip(client2[6].pod_ip)
    #end test_pod_custom_isolation
    
    @preposttest_wrapper
    def test_namespace_custom_isolation(self):
        """
        Verify reachability of a Pod inside custom isolated network to other Pods
        Verify following reachability:
        1. Pod inside custom isolated namespace should be able to reach other pods of same namespace
        2. Pod inside custom isolated namespace should not be able to reach other pods of other namespace
        """
        client1, client2 = self.setup_common_namespaces_pods()
        #Check 1
        assert client2[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client2[6].pod_ip, expectation=False)
        #Check 2
        assert client2[6].ping_to_ip(client1[2].pod_ip, expectation=False)
        assert client2[6].ping_to_ip(client1[6].pod_ip)
    #end test_namespace_custom_isolation
    
    @preposttest_wrapper
    def test_service_custom_isolation(self):
        """
        Verify reachability of a Service in and out of custom isolated namespace
        Verify following reachability:
        1. Pod inside custom isolated namespace should be able to reach service within same namespace
        2. Pod inside custom isolated namespace should be able to reach service outside this namespace
        3. Pods inside non islatednamespace should be able to reach service inside custom isolated namespace.
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True)
        #check 1
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        #check 2
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2], expectation=False)
        #check 3
        client2[4].disable_service_isolation()
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
    #end test_service_custom_isolation

    @preposttest_wrapper
    def test_ingress_custom_isolation(self):
        """
        Verify that ingress created inside a custom isolated namespace is reachable to public
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True,
                                                             prov_ingress = True)
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[5].external_ips[0])
    #end test_ingress_custom_isolation
