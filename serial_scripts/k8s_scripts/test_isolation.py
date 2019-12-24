from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from time import sleep
from tcutils.util import get_random_name
from tcutils.contrail_status_check import ContrailStatusChecker
import test
from tcutils.util import skip_because

from vn_test import VNFixture

class TestNSIsolationSerial(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNSIsolationSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNSIsolationSerial, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
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

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pods_isolation_post_kube_manager_restart(self):
        """
        This test case verifies the connectivity between pods of different namespaces with
        namespace isolation enabled post restart of contrail-kube-manager
        Verify:
        1. Pods in other namespaces in the Kubernetes cluster will NOT be able to reach pods in the isolated namespace.
        2. Pods created in isolated namespace can reach pods in other namespaces.
        Restart contrail-kube-manager and verify both the points again
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2, client3 = self.setup_common_namespaces_pods()
        #Check 1:
        assert client1[2].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client3[2].ping_to_ip(client2[0].pod_ip, expectation=False)
        #Check 2
        assert client1[2].ping_to_ip(client3[0].pod_ip, expectation=False)
        self.restart_kube_manager()
        #Check 1:
        assert client1[2].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client3[2].ping_to_ip(client2[0].pod_ip, expectation=False)
        #Check 2
        assert client1[2].ping_to_ip(client3[0].pod_ip, expectation=False)
    #end test_pods_isolation_post_kube_manager_restart

    @test.attr(type=['k8s_sanity','openshift_1'])
    @preposttest_wrapper
    def test_service_isolation_post_kube_manager_restart(self):
        """
        This test case verifies the connectivity between pods and service of different namespaces with
        namespace isolation enabled post restart of contrail-kube-manager
        Verify:
        1. Pods in isolated namespace will be able to reach ALL Services created in default namespace in the kubernetes cluster.
        2. Pods in isolated namespace cannot be reached from pods in other namespaces through Kubernetes Service-ip
        Restart contrail-kube-manager and verify both the points again
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True)
        #Check 1:
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2], expectation=False)
        #Check 2:
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client3[2], expectation=False)
        self.restart_kube_manager()
        #Check 1:
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2], expectation=False)
        #Check 2:
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client3[2], expectation=False)
    #end test_service_isolation_post_kube_manager_restart    

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_isolation_post_kube_manager_restart(self):
        """
        Test test case verifies ingress operations post restart of contrail-kube-manager
        Verify:
        1. Verify that k8s INgress existing in isolated namespace is accessible from external world
        2. Verify that k8s INgress existing in non isolated namespace is accessible from external world
        Restart contrail-kube-manager and verify both the points again
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True,
                                                                      prov_ingress = True)
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[5].external_ips[0])
        self.restart_kube_manager()
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[5].external_ips[0])
    #end test_ingress_isolation_post_kube_manager_restart

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_isolation_vrouter_agent_restart(self):
        """
        Test test case verifies ingress operations post restart of vrouter-agent
        Verify:
        1. Verify that k8s INgress existing in isolated namespace is accessible from external world
        2. Verify that k8s INgress existing in non isolated namespace is accessible from external world
        Restart vrouter-agent and verify both the points again
        """
        client1, client2, client3 = self.setup_common_namespaces_pods(prov_service = True,
                                                                      prov_ingress = True)
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[5].external_ips[0])
        self.restart_vrouter_agent()
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
        assert self.validate_nginx_lb([client3[0], client3[1]], client3[5].external_ips[0])
    #end test_ingress_isolation_vrouter_agent_restart

class TestCustomIsolationSerial(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestCustomIsolationSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestCustomIsolationSerial, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    def setup_common_namespaces_pods(self, prov_service = False):
        service_ns1 = None
        service_ns2 = None
        vn_for_namespace = self.setup_vn(vn_name = "TestVNNamespace")
        vn_dict_for_namespace = {"domain": vn_for_namespace.domain_name,
                   "project" : vn_for_namespace.project_name,
                   "name": vn_for_namespace.vn_name}
        vn_for_pod = self.setup_vn(vn_name = "TestVNPod")
        vn_dict_for_pod = {"domain": vn_for_pod.domain_name,
                   "project" : vn_for_pod.project_name,
                   "name": vn_for_pod.vn_name}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name)
        namespace2 = self.setup_namespace(name = namespace2_name, custom_isolation = True,
                                           fq_network_name= vn_dict_for_namespace)
        assert namespace1.verify_on_setup()
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
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1, client4_ns1, client5_ns1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2, client4_ns2, vn_for_namespace]
        return (client1, client2)
    #end setup_common_namespaces_pods
    
    @test.attr(type=['k8s_sanity','openshift_1'])
    @preposttest_wrapper
    def test_pods_custom_isolation_post_kube_manager_restart(self):
        """
        Verify that after restart of contrail-kubemanager, pod reachability to 
        and from custom isolated namespace/pod is not affected
        Verify following reachability:
        1. Verify reachability between pods and namespaces
        2. restart contrail-kube-manager
        3. Verify reachability between pods and namespaces
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2 = self.setup_common_namespaces_pods()
        assert client1[5].ping_to_ip(client1[0].pod_ip, expectation=False)
        assert client1[5].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[5].ping_to_ip(client1[6].pod_ip)
        assert client1[5].ping_to_ip(client2[5].pod_ip)
        assert client2[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client2[5].pod_ip, expectation=False)
        assert client2[5].ping_to_ip(client1[2].pod_ip, expectation=False)
        assert client2[5].ping_to_ip(client1[5].pod_ip)
        self.restart_kube_manager()
        assert client1[5].ping_to_ip(client1[0].pod_ip, expectation=False)
        assert client1[5].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[5].ping_to_ip(client1[6].pod_ip)
        assert client1[5].ping_to_ip(client2[5].pod_ip)
        assert client2[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client2[5].pod_ip, expectation=False)
        assert client2[5].ping_to_ip(client1[2].pod_ip, expectation=False)
        assert client2[5].ping_to_ip(client1[5].pod_ip)
    #end test_pods_custom_isolation_post_kube_manager_restart
    
    @test.attr(type=['k8s_sanity','openshift_1'])
    @preposttest_wrapper
    def test_services_custom_isolation_post_kube_manager_restart(self):
        """
        Verify that after restart of contrail-kubemanager, service reachability to 
        and from custom isolated namespace/pod is not affected
        Verify following reachability:
        1. Verify reachability between pods and services
        2. restart contrail-kube-manager
        3. Verify reachability between pods and services
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True)
        policy_name='allow-btw-custom-ns-and-service'
        if self.inputs.slave_orchestrator == 'kubernetes':
            k8s_default_service_vn_name = self.connections.project_name + '-default-service-network'
        else:
            k8s_default_service_vn_name = "k8s-default-service-network"
        k8s_default_service_vn_fq_name = self.connections.inputs.project_fq_name + \
                                            [k8s_default_service_vn_name]
        k8s_default_service_vn_obj = self.vnc_lib.virtual_network_read(
                                    fq_name = k8s_default_service_vn_fq_name)
        k8s_service_vn_fixt = VNFixture(connections = self.connections,
                                       vn_name = k8s_default_service_vn_name,
                                       option="contrail",
                                       uuid = k8s_default_service_vn_obj.uuid)
        k8s_service_vn_fixt.setUp()
        vn_service_policy = self.setup_policy_between_vns(client2[6],
                                                          k8s_service_vn_fixt,
                                                          api="contrail",
                                                          connections=self.connections)
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
        self.restart_kube_manager()
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
    #end test_services_custom_isolation_post_kube_manager_restart

class TestProjectIsolationSerial(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestProjectIsolationSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestProjectIsolationSerial, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    def setup_common_namespaces_pods(self, prov_service = False,
                                    prov_ingress = False,
                                    isolation = False):
        operation = self.modify_cluster_project()
        service_ns1, ingress_ns1 = None, None
        service_ns2, ingress_ns2 = None, None
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = isolation)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        if operation=="reset":
            assert namespace1.project_isolation
            assert namespace2.project_isolation
        else:
            assert (namespace1.project_isolation == False)
            assert (namespace2.project_isolation == False)
        ns_1_label = "namespace1"
        ns_2_label = "namespace2"
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
        assert self.verify_nginx_pod(client1_ns1)
        assert self.verify_nginx_pod(client2_ns1)
        assert client3_ns1.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns2)
        assert self.verify_nginx_pod(client2_ns2)
        assert client3_ns2.verify_on_setup()
        if prov_service == True:
            service_ns1 = self.setup_http_service(namespace=namespace1.name,
                                          labels={'app': ns_1_label})
            type = "LoadBalancer" if prov_ingress == False else None 
            service_ns2 = self.setup_http_service(namespace=namespace2.name,
                                          labels={'app': ns_2_label},
                                          type=type)
        if prov_ingress == True:
            ingress_ns1 = self.setup_simple_nginx_ingress(service_ns1.name,
                                                  namespace=namespace1.name)
            ingress_ns2 = self.setup_simple_nginx_ingress(service_ns2.name,
                                                  namespace=namespace2.name)
            assert ingress_ns1.verify_on_setup()
            assert ingress_ns2.verify_on_setup()
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1, ingress_ns1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2, ingress_ns2]
        return (client1, client2)
    #end setup_common_namespaces_pods
   
    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_reachability_across_projects(self):
        """
        Check reachability of Pods of different namespaces across different projects
        """
        client1, client2 = self.setup_common_namespaces_pods()
        assert client1[2].ping_to_ip(client1[0].pod_ip)
        assert client1[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client1[0].pod_ip)
    # end  test_pod_reachability_across_ns
    
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_service_reachability_across_projects(self):
        """
        Check reachability of Service of different namespaces across different projects
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True)
        # Service reachability within namespace/project 
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        # Service reachability across namespace/project
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        #External connectivity check
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].external_ips[0])
    # end  test_service_reachability_across_ns
    
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_reachability_across_projects(self):
        """
        Check reachability of Ingress created in project namespace
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True,
                                                             prov_ingress = True)
        # Ingress reachability within namespace/project 
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[5].external_ips[0])
        # Ingress reachability across namespace/project
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[5].external_ips[0])
    # end  test_ingress_reachability_across_ns

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_reachability_across_projects_with_isolated_namespace(self):
        """
        Check reachability between Pods and services created in isolated namespace.
        Note that the namespace should have seperate Project.
        1. Create 2 namespaces. 1 as non isolated and other as isolated.
        2. Create Pods and service under both the namespaces.
        3. Verify reachability
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True,
                                                             isolation = True)
        # Reachability of Pods
        assert client1[2].ping_to_ip(client1[0].pod_ip)
        assert client2[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client1[0].pod_ip, expectation = False)
        assert client1[2].ping_to_ip(client2[0].pod_ip, expectation = False)
        # Reachability of Services   
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2]) 
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2], expectation = False)
    # end  test_reachability_across_projects_with_isolated_namespace
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_reachability_across_projects_with_kube_manager_restart(self):
        """
        Check reachability between Pods and services after kube manager restart
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True)
        # Reachability of Pods
        assert client1[2].ping_to_ip(client1[0].pod_ip)
        assert client1[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client1[0].pod_ip)
        # Reachability of Services   
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
        self.restart_kube_manager()
        # Reachability of Pods
        assert client1[2].ping_to_ip(client1[0].pod_ip)
        assert client1[2].ping_to_ip(client2[0].pod_ip)
        assert client2[2].ping_to_ip(client1[0].pod_ip)
        # Reachability of Services   
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client2[2])
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[3].cluster_ip,
                                      test_pod=client1[2])
        assert self.validate_nginx_lb([client1[0], client1[1]], client1[3].cluster_ip,
                                      test_pod=client2[2])
    # end  test_reachability_across_projects_with_kube_manager_restart
