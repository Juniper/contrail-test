from builtins import object
from common.k8s.base import BaseK8sTest
from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase

from k8s.namespace import NamespaceFixture
from k8s.pod import PodFixture
from tcutils.util import Singleton, skip_because
import test
import time

import gevent
from gevent import greenlet
from future.utils import with_metaclass

class TestNetworkPolicyProjectIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyProjectIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyProjectIsolation, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    def setup_common_namespaces_pods(self):
        operation = self.modify_cluster_project()
        namespace1 = self.setup_namespace(name = "ns1")
        namespace2 = self.setup_namespace(name = "ns2")
        namespace1.set_labels({'test_site': "ns1"})
        namespace2.set_labels({'test_site': "ns2"})
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        if operation=="reset":
            assert namespace1.project_isolation
            assert namespace2.project_isolation
        else:
            assert (namespace1.project_isolation == False)
            assert (namespace2.project_isolation == False)
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
        assert policy1.verify_on_setup()
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
        assert policy1.verify_on_setup()
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

class TestNetworkPolicyRestart(BaseK8sTest):

    class SharedResources (with_metaclass(Singleton, object)):
        def __init__ (self, connections):
            self.connections = connections
            self.setUp()

        def setUp (self):
            try:
                self.ns1 = NamespaceFixture(connections=self.connections, name="new-default")
                self.ns1.setUp()
                self.ns2 = NamespaceFixture(connections=self.connections, name="non-default")
                self.ns2.setUp()
                self.ns3 = NamespaceFixture(connections=self.connections, name="temp-ns")
                self.ns3.setUp()
                self.ns1.set_labels({'site': self.ns1.name})
                self.ns2.set_labels({'site': self.ns2.name})
                self.ns3.set_labels({'new_site': self.ns3.name})
                web_label_ns1, web_label_ns2 = 'webns1', 'webns2'
                client1_label_ns1, client1_label_ns2, client1_label_ns3 = 'client1_ns1', 'client1_ns2', 'client1_ns3'
                client2_label_ns1, client2_label_ns2, client2_label_ns3 = 'client2_ns1', 'client2_ns2', 'client2_ns3'
                client3_label_ns3 = 'client3_ns3'
                nginx_spec_1 = {'containers': [{'image': 'nginx',
                                                'ports': [{'container_port': 80}]}]}
                nginx_spec_2 = {'containers': [{'image': 'nginx',
                                                'ports': [{'container_port': 80}]}]}
                nginx_metadata_ns1 = {'labels': {'app': web_label_ns1}}
                nginx_metadata_ns2 = {'labels': {'app': web_label_ns2}}
                self.web_pod_ns1 = PodFixture(connections=self.connections,
                                            namespace=self.ns1.name,
                                            metadata=nginx_metadata_ns1,
                                            spec=nginx_spec_1)
                self.web_pod_ns1.setUp()
                self.web_pod_ns2 = PodFixture(connections=self.connections,
                                            namespace=self.ns2.name,
                                            metadata=nginx_metadata_ns2,
                                            spec=nginx_spec_2)
                self.web_pod_ns2.setUp()
                busybox_spec_1 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                                'image_pull_policy': 'IfNotPresent',}],
                                            'restart_policy': 'Always'}
                busybox_spec_2 = dict(busybox_spec_1)
                busybox_spec_3 = dict(busybox_spec_1)
                busybox_spec_4 = dict(busybox_spec_1)
                busybox_spec_5 = dict(busybox_spec_1)
                busybox_spec_6 = dict(busybox_spec_1)
                busybox_spec_7 = dict(busybox_spec_1)
                busybox_metadata_c1_ns1 = {'labels': {'app': client1_label_ns1}}
                busybox_metadata_c1_ns2 = {'labels': {'app': client1_label_ns2}}
                busybox_metadata_c1_ns3 = {'labels': {'app': client1_label_ns3}}
                busybox_metadata_c2_ns1 = {'labels': {'app': client2_label_ns1}}
                busybox_metadata_c2_ns2 = {'labels': {'app': client2_label_ns2}}
                busybox_metadata_c2_ns3 = {'labels': {'app': client2_label_ns3}}
                busybox_metadata_c3_ns3 = {'labels': {'app': client3_label_ns3}}
                self.client1_pod_ns1 = PodFixture(connections=self.connections,
                                                namespace=self.ns1.name,
                                                metadata=busybox_metadata_c1_ns1,
                                                spec=busybox_spec_1)
                self.client1_pod_ns1.setUp()
                self.client2_pod_ns1 = PodFixture(connections=self.connections,
                                                namespace=self.ns1.name,
                                                metadata=busybox_metadata_c2_ns1,
                                                spec=busybox_spec_2)
                self.client2_pod_ns1.setUp()
                self.client1_pod_ns2 = PodFixture(connections=self.connections,
                                                namespace=self.ns2.name,
                                                metadata=busybox_metadata_c1_ns2,
                                                spec=busybox_spec_3)
                self.client1_pod_ns2.setUp()
                self.client2_pod_ns2 = PodFixture(connections=self.connections,
                                                namespace=self.ns2.name,
                                                metadata=busybox_metadata_c2_ns2,
                                                spec=busybox_spec_4)
                self.client2_pod_ns2.setUp()
                self.client1_pod_ns3 = PodFixture(connections=self.connections,
                                                namespace=self.ns3.name,
                                                metadata=busybox_metadata_c1_ns3,
                                                spec=busybox_spec_5)
                self.client1_pod_ns3.setUp()
                self.client2_pod_ns3 = PodFixture(connections=self.connections,
                                                namespace=self.ns3.name,
                                                metadata=busybox_metadata_c2_ns3,
                                                spec=busybox_spec_6)
                self.client2_pod_ns3.setUp()
                self.client3_pod_ns3 = PodFixture(connections=self.connections,
                                                namespace=self.ns3.name,
                                                metadata=busybox_metadata_c3_ns3,
                                                spec=busybox_spec_7)
                self.client3_pod_ns3.setUp()
                assert self.ns1.verify_on_setup()
                assert self.ns2.verify_on_setup()
                assert self.ns3.verify_on_setup()
                assert self.web_pod_ns1.verify_on_setup()
                assert self.web_pod_ns2.verify_on_setup()
                assert self.client1_pod_ns1.verify_on_setup()
                assert self.client1_pod_ns2.verify_on_setup()
                assert self.client1_pod_ns3.verify_on_setup()
                assert self.client2_pod_ns1.verify_on_setup()
                assert self.client2_pod_ns2.verify_on_setup()
                assert self.client2_pod_ns3.verify_on_setup()
                assert self.client3_pod_ns3.verify_on_setup()
            except:
                self.cleanUp()
                raise
        
        def cleanUp (self):
            cleanup_list = list()
            if getattr(self, 'web_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.web_pod_ns1.cleanUp))
            if getattr(self, 'web_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.web_pod_ns2.cleanUp))
            if getattr(self, 'client1_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.client1_pod_ns1.cleanUp))
            if getattr(self, 'client2_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.client2_pod_ns1.cleanUp))
            if getattr(self, 'client1_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.client1_pod_ns2.cleanUp))
            if getattr(self, 'client2_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.client2_pod_ns2.cleanUp))
            if getattr(self, 'client1_pod_ns3', None):
                cleanup_list.append(gevent.spawn(self.client1_pod_ns3.cleanUp))
            if getattr(self, 'client2_pod_ns3', None):
                cleanup_list.append(gevent.spawn(self.client2_pod_ns3.cleanUp))
            if getattr(self, 'client3_pod_ns3', None):
                cleanup_list.append(gevent.spawn(self.client3_pod_ns3.cleanUp))
            gevent.joinall(cleanup_list)
            if getattr(self, 'ns1', None):
                self.ns1.cleanUp()
            if getattr(self, 'ns2', None):
                self.ns2.cleanUp()
            if getattr(self, 'ns3', None):
                self.ns3.cleanUp()

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyRestart, cls).setUpClass()

    def setUp (self):
        super(TestNetworkPolicyRestart, self).setUp()
        self._res = self.__class__.SharedResources(self.connections)
        self.__class__._shared_resources = self._res
        self.ns1 = self._res.ns1
        self.ns2 = self._res.ns2
        self.ns3 = self._res.ns3
        self.web_pod_ns1 = self._res.web_pod_ns1
        self.web_pod_ns2 = self._res.web_pod_ns2
        self.client1_pod_ns1 = self._res.client1_pod_ns1
        self.client2_pod_ns1 = self._res.client2_pod_ns1
        self.client1_pod_ns2 = self._res.client1_pod_ns2
        self.client2_pod_ns2 = self._res.client2_pod_ns2
        self.client1_pod_ns3 = self._res.client1_pod_ns3
        self.client2_pod_ns3 = self._res.client2_pod_ns3
        self.client3_pod_ns3 = self._res.client3_pod_ns3

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyRestart, cls).tearDownClass()
        if getattr(cls, '_shared_resources'):
            cls._shared_resources.cleanUp()

    def verify_policy_pre_modification_common(self, pod_list_ns1, pod_list_ns2, pod_list_ns3):
        '''
        Common function to verify connectivity immediately post restart.
        This function is common to all test cases of this class.
        '''
        url = 'http://%s' % (pod_list_ns1[2].pod_ip)
        url2 = 'http://%s' % (pod_list_ns2[2].pod_ip)
        assert pod_list_ns3[1].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns3[1].ping_with_certainty(pod_list_ns3[2].pod_ip)

        assert pod_list_ns2[0].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns2[1].ping_with_certainty(pod_list_ns3[2].pod_ip)
        assert pod_list_ns1[0].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns1[0].ping_with_certainty(pod_list_ns3[2].pod_ip)
        # Verify that other pods which do not match ingress criteria cannot communicate
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns3[0].pod_ip,
                                                        expectation=False)
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns3[2].pod_ip,
                                                        expectation=False)
        assert pod_list_ns1[1].ping_with_certainty(pod_list_ns3[0].pod_ip,
                                                        expectation=False)
        assert pod_list_ns1[1].ping_with_certainty(pod_list_ns3[1].pod_ip,
                                                        expectation=False)
        # Verify that all egress rules are operational
        assert self.validate_wget(pod_list_ns3[0], url)
        assert self.validate_wget(pod_list_ns3[2], url)
        assert self.validate_wget(pod_list_ns3[0], url2)
        assert self.validate_wget(pod_list_ns3[2], url2)
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns3[1].pod_ip)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns3[1].pod_ip)
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns1[2].pod_ip)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns1[2].pod_ip)
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns2[2].pod_ip)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns2[0].pod_ip)
        # Verify that other pods which do not match egress criteria cannot communicate
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns1[0].pod_ip,
                                                        expectation=False)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns1[1].pod_ip,
                                                        expectation=False)
    #end verify_policy_pre_modification_common

    def verify_policy_post_modification_common(self, pod_list_ns1, pod_list_ns2, pod_list_ns3):
        '''
        Common function to verify connectivity post policy modification post restart.
        This function is common to all test cases of this class.
        '''
        url = 'http://%s' % (pod_list_ns1[2].pod_ip)
        url2 = 'http://%s' % (pod_list_ns2[2].pod_ip)
        # Verify that all ingress rules are operational
        assert pod_list_ns3[1].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns2[0].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns2[1].ping_with_certainty(pod_list_ns3[0].pod_ip)
        assert pod_list_ns1[0].ping_with_certainty(pod_list_ns3[0].pod_ip)
        # Verify that other pods which do not match ingress criteria cannot communicate
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns3[0].pod_ip,
                                                        expectation=False)
        assert pod_list_ns1[1].ping_with_certainty(pod_list_ns3[0].pod_ip,
                                                        expectation=False)
        # Verify that all egress rules are operational
        assert self.validate_wget(pod_list_ns3[0], url)
        assert self.validate_wget(pod_list_ns3[0], url2)
        # Verify that all pods which meeet egress criteria fails if port criteria is not met
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns3[1].pod_ip,
                                                        expectation=False) #podSelector
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns2[1].pod_ip,
                                                        expectation=False) #namespaceSelector
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns1[2].pod_ip,
                                                        expectation=False) #ipblock CIDR
        assert pod_list_ns3[0].ping_with_certainty(pod_list_ns1[0].pod_ip,
                                                        expectation=False)
        #Verfiy that other pods of the namespace 3 are not affected because of rule
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns3[1].pod_ip)
        assert pod_list_ns1[1].ping_with_certainty(pod_list_ns3[1].pod_ip)
        assert self.validate_wget(pod_list_ns3[2], url2)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns1[2].pod_ip)
        assert pod_list_ns3[1].ping_with_certainty(pod_list_ns2[2].pod_ip)
        assert pod_list_ns3[2].ping_with_certainty(pod_list_ns3[1].pod_ip)
    #end verify_policy_post_modification_common

    def validate_reachability_pre_policy_common(self, pod_list_ns1, pod_list_ns2, pod_list_ns3):
        """
        This proc just executes pre execution checks to make sure reachability is correct
        """
        url = 'http://%s' % (pod_list_ns1[2].pod_ip)
        url2 = 'http://%s' % (pod_list_ns2[2].pod_ip)
        assert self.validate_wget(pod_list_ns2[0], url)
        assert self.validate_wget(pod_list_ns1[0], url2)
        assert self.validate_wget(pod_list_ns3[0], url)
        assert pod_list_ns2[0].ping_with_certainty(pod_list_ns3[0].pod_ip)
    #end validate_reachability_pre_policy_common

    def create_update_policy_common(self, pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                     update=False, policy_fixture = None):
        """
        This proc is used to create a common policy used across all the test cases of this class
        """
        ingress_allow_cidr = pod_list_ns1[0].pod_ip + "/32"
        ingress_list = [
            {'from': [
                {'pod_selector': pod_list_ns3[1].labels},
                {'namespace_selector': pod_list_ns2[3].labels},
                {'ip_block': { "cidr" : ingress_allow_cidr}}
                    ]
             }
        ]
        egress_allow_cidr = pod_list_ns1[2].pod_ip + "/32"
        egress_list = [
            {'to': [
                {'pod_selector': pod_list_ns3[1].labels},
                {'namespace_selector': pod_list_ns2[3].labels},
                {'ip_block': { "cidr" : egress_allow_cidr}}
                ],
            }
        ]
        policy_types = ["Ingress", "Egress"]
        if update == False:
            policy1 = self.setup_update_policy(name="ingress-egress-policy-on-ns",
                                       namespace = pod_list_ns3[3].name,
                                       policy_types = policy_types,
                                       ingress= ingress_list,
                                       egress= egress_list)
            return policy1
        else:
            egress_list[0]['egress_ports'] = [ 'TCP/80' ]
            self.setup_update_policy(pod_selector = pod_list_ns3[0].labels,
                                 update = True,
                                np_fixture = policy_fixture,
                                egress= egress_list,
                                policy_types = policy_types,
                                ingress= ingress_list)
    #end create_update_policy_common

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_policy_kube_manager_restart(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        contrail-kube-manager restart
        1. Create policy having both ingress and egress rules.
        2. Perform a restart for contrail-kube-manager on all kube-manager nodes.
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart Kube manager
        self.restart_kube_manager()
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_kube_manager_restart

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_policy_vrouter_agent_restart(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        contrail-vrouter-agent restart
        1. Create policy having both ingress and egress rules.
        2. Perform a restart for contrail-vrouter-agent on all agent nodes.
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart Vrouter agent
        self.restart_vrouter_agent()
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_kube_manager_restart

    @preposttest_wrapper
    def test_policy_rule_pod_restart(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        restart of pod used as PodSelector in the policy rule.
        1. Create policy having both ingress and egress rules.
        2. Perform a restart for a podused in INgress and Egress rules
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart POD used as PodSelector in the rule
        assert self.restart_pod(self.client2_pod_ns3)
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_rule_pod_restart

    @preposttest_wrapper
    def test_policy_pod_restart(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        restart of pod used as PodSelector in the policy .
        1. Create policy having both ingress and egress rules.
        2. Perform a restart for a pod used as PodSelector in the Policy
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Restart POD used as PodSelector in the Policy
        assert self.restart_pod(self.client1_pod_ns3)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_pod_restart

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_policy_docker_restart(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        docker engine is restarted on compute node
        1. Create policy having both ingress and egress rules.
        2. Perform a restart for docker engine on compute nodes
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart POD used as PodSelector in the rule
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all contrail service to come up.
        # ToDo : Replace this wait with contrail Status check once it is available
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_docker_restart

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_policy_kubelet_restart_on_slave(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        kubelet is restarted on slave nodes
        1. Create policy having both ingress and egress rules.
        2. Perform a restart of kubelet on slave nodes.
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart POD used as PodSelector in the rule
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_kubelet_restart_on_slave

    @preposttest_wrapper
    def test_policy_kubelet_restart_on_master(self):
        """
        Verify that k8s Network policy and contrail FW policy works fine after
        kubelet is restarted on master nodes
        1. Create policy having both ingress and egress rules.
        2. Perform a restart of kubelet on master nodes.
        3. Verify that all policy rules are followed
        4. Edit the k8s network policy
        5. Verify that all policy rules are followed
        """
        pod_list_ns1 = [self.client1_pod_ns1, self.client2_pod_ns1, self.web_pod_ns1, self.ns1]
        pod_list_ns2 = [self.client1_pod_ns2, self.client2_pod_ns2, self.web_pod_ns2, self.ns2]
        pod_list_ns3 = [self.client1_pod_ns3, self.client2_pod_ns3, self.client3_pod_ns3, self.ns3]
        # Validate reachability across pods before craeteing network policy
        self.validate_reachability_pre_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        # Create a network Policy
        policy1 = self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        assert policy1.verify_on_setup()
        # Restart POD used as PodSelector in the rule
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = [self.inputs.k8s_master_ip])
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        # Verify that policy works fine after restart
        self.verify_policy_pre_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
        #Updating the policy
        self.create_update_policy_common(pod_list_ns1, pod_list_ns2, pod_list_ns3,
                                  update=True, policy_fixture=policy1)
        # Verify that policy works fine after updating
        self.verify_policy_post_modification_common(pod_list_ns1, pod_list_ns2, pod_list_ns3)
    #end test_policy_kubelet_restart_on_master
