from common.k8s.base import BaseK8sTest
from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase

from k8s.namespace import NamespaceFixture
from k8s.pod import PodFixture
import test

class TestNetworkPolicyProjectIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyProjectIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyProjectIsolation, cls).tearDownClass()
        
    def setup_common_namespaces_pods(self):
        deleted_project = self.delete_cluster_project()
        self.addCleanup(self.add_cluster_project,
                         project_name = deleted_project)
        namespace1 = self.setup_namespace(name = "ns1")
        namespace2 = self.setup_namespace(name = "ns2")
        namespace1.set_labels({'test_site': "ns1"})
        namespace2.set_labels({'test_site': "ns2"})
        assert namespace1.verify_on_setup()
        assert namespace1.project_isolation
        assert namespace2.verify_on_setup()
        assert namespace2.project_isolation
        client1_ns1 = self.setup_busybox_pod(namespace="ns1",
                                             labels={'app': "c1_ns1"})
        client2_ns1 = self.setup_busybox_pod(namespace="ns1",
                                             labels={'app': "c2_ns1"})
        client3_ns1 = self.setup_nginx_pod(namespace="ns1",
                                             labels={'app': "c3_ns1"})
        client1_ns2 = self.setup_busybox_pod(namespace="ns2",
                                             labels={'app': "c1_ns2"})
        client2_ns2 = self.setup_busybox_pod(namespace="ns2",
                                             labels={'app': "c2_ns2"})
        client3_ns2 = self.setup_nginx_pod(namespace="ns2",
                                             labels={'app': "c3_ns2"})
        assert client1_ns1.verify_on_setup()
        assert client2_ns1.verify_on_setup()
        assert client3_ns1.verify_on_setup()
        assert client1_ns2.verify_on_setup()
        assert client2_ns2.verify_on_setup()
        assert client3_ns2.verify_on_setup()
        client1 = [client1_ns1, client2_ns1, client3_ns1, namespace1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, namespace2]
        return (client1, client2)
    #end setup_common_namespaces_pods

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_ingress_policy_over_project_isolation(self):
        """
        Verify that ingress K8s network policy works correctly when 2 different namespaces
        corresponds to 2 different projects(Project Isolation).
        Steps:
        1. Verify that project isolation works as expected
        2. Create an Ingress policy on namespace and verify all rules are followed as expected
        3. Update the Ingress policy and aply it over a single pod of the namespace.
           Verify that all rules work as expected.
        Note: As policies are at Global level, all policies should apply in a way they 
        apply on normal k8s namespaces and pods
        """
        ns1_clients, ns2_clients = self.setup_common_namespaces_pods()
        url1 = 'http://%s' % (ns1_clients[2].pod_ip)
        url2 = 'http://%s' % (ns2_clients[2].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[0].pod_ip)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        #Create a network policy with ingress rules
        # Verify an ingress policy
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': ns1_clients[1].labels},
                {'namespace_selector': ns2_clients[3].labels},
                    ]
             }
        ]
        policy1 = self.setup_update_policy(name="ingress-policy-over-project-ns",
                                   namespace = ns1_clients[3].name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        
        # Verify that ingress policy works as expected
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns1_clients[0].ping_with_certainty(ns1_clients[1].pod_ip,
                                                  expectation=False)
        assert self.validate_wget(ns1_clients[1], url1)
        assert self.validate_wget(ns1_clients[0], url1, expectation=False)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns2_clients[0].ping_with_certainty(ns1_clients[1].pod_ip)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[2].pod_ip)
        assert self.validate_wget(ns2_clients[1], url1)
        assert self.validate_wget(ns2_clients[0], url1)
        
        # Edit the ingress policy and apply it on a specific pod of ns1
        ingress_list = [
            {'from': [
                {'pod_selector': ns1_clients[1].labels},
                {'namespace_selector': ns2_clients[3].labels},
                    ],
             'ports' : [ 'TCP/80' ],
             }
        ]
        self.setup_update_policy(pod_selector = ns1_clients[2].labels,
                                update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        
        # Verify that ingress policy works as expected
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns1_clients[0].ping_with_certainty(ns1_clients[1].pod_ip)
        assert self.validate_wget(ns1_clients[1], url1)
        assert self.validate_wget(ns1_clients[0], url1, expectation=False)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns2_clients[0].ping_with_certainty(ns1_clients[1].pod_ip)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[2].pod_ip,
                                                  expectation=False)
        assert self.validate_wget(ns2_clients[1], url1)
        assert self.validate_wget(ns2_clients[0], url1)
    #end test_ingress_policy_over_project_isolation

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_egress_policy_over_project_isolation(self):
        """
        Verify that egress K8s network policy works correctly when 2 different namespaces
        corresponds to 2 different projects(Project Isolation).
        Steps:
        1. Verify that project isolation works as expected
        2. Create an Egress policy on namespace and verify all rules are followed as expected
        3. Update the Egress policy and apply it over a single pod of the namespace.
           Verify that all rules work as expected.
        Note: As policies are at Global level, all policies should apply in a way they 
        apply on normal k8s namespaces and pods
        """
        ns1_clients, ns2_clients = self.setup_common_namespaces_pods()
        url1 = 'http://%s' % (ns1_clients[2].pod_ip)
        url2 = 'http://%s' % (ns2_clients[2].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[0].pod_ip)
        assert ns2_clients[1].ping_with_certainty(ns1_clients[0].pod_ip)
        #Create a network policy with ingress rules
        # Verify an ingress policy
        policy_types = ["Egress"]
        egress_allow_cidr = ns2_clients[2].pod_ip + "/32"
        egress_list = [
            {'to': [
                {'ip_block': { "cidr" : egress_allow_cidr}}
                ],
                'egress_ports': [ 'TCP/80' ]
            }
        ]
        policy1 = self.setup_update_policy(name="egress-policy-over-project-ns",
                                   namespace = ns1_clients[3].name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        
        # Verify that egress policy works as expected
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip,
                                                    expectation=False)
        assert self.validate_wget(ns1_clients[1], url1, expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[0].pod_ip,
                                                    expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[2].pod_ip,
                                                    expectation=False)
        assert ns1_clients[0].ping_with_certainty(ns2_clients[2].pod_ip,
                                                    expectation=False)
        assert self.validate_wget(ns1_clients[1], url2)
        assert self.validate_wget(ns1_clients[0], url2)
        assert ns2_clients[0].ping_with_certainty(ns1_clients[0].pod_ip)
        assert self.validate_wget(ns2_clients[0], url1)
        
        # Edit the egress policy and apply it on a specific pod of ns1
        egress_list = [
            {'to': [
                {'ip_block': { "cidr" : egress_allow_cidr}}
                ]
            }
        ]
        self.setup_update_policy(pod_selector = ns1_clients[1].labels,
                                update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        
        # Verify that ingress policy works as expected
        assert ns1_clients[1].ping_with_certainty(ns1_clients[0].pod_ip,
                                                    expectation=False)
        assert self.validate_wget(ns1_clients[1], url1, expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[0].pod_ip,
                                                    expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns2_clients[2].pod_ip)
        assert ns1_clients[0].ping_with_certainty(ns2_clients[2].pod_ip)
        assert ns1_clients[0].ping_with_certainty(ns2_clients[0].pod_ip)
        assert self.validate_wget(ns1_clients[1], url2)
        assert self.validate_wget(ns1_clients[0], url2)
        assert ns2_clients[0].ping_with_certainty(ns1_clients[0].pod_ip)
        assert self.validate_wget(ns2_clients[0], url1)
    #end test_egress_policy_over_project_isolation
