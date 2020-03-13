from builtins import object
from common.k8s.base import BaseK8sTest
from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase

from k8s.namespace import NamespaceFixture
from k8s.pod import PodFixture
from tcutils.util import get_random_name, get_random_cidr
import time
import test
from tcutils.util import skip_because, Singleton
import gevent
from gevent import greenlet
from future.utils import with_metaclass

class TestNetworkPolicy(BaseK8sTest):

    class SharedResources(with_metaclass(Singleton, object)):
        def __init__ (self, connections):
            self.connections = connections
            self.setUp()
        
        def setUp (self):
            try:
                self.ns1 = NamespaceFixture(connections=self.connections, name="default")
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
            if getattr(self, 'ns2', None):
                self.ns2.cleanUp()
            if getattr(self, 'ns3', None):
                self.ns3.cleanUp()

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicy, cls).setUpClass()

    def setUp(self):
        super(TestNetworkPolicy, self).setUp()
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
        super(TestNetworkPolicy, cls).tearDownClass()
        if getattr(cls, '_shared_resources'):
            cls._shared_resources.cleanUp()

    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
    @preposttest_wrapper
    def test_allow_all_ingress(self):
        """
        Verify a network policy with Ingress rule as allow all.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace
        3. Veify that all pods are still reachable from all namespaces
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        policy = self.setup_update_simple_policy(name="allow-all-ingress",
                                 namespace= self.ns1.name,
                                ingress_all =True)
        assert policy.verify_on_setup()
        # All traffic should still work as it is ingress allow all policy
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_allow_all_ingress
   
    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
    @preposttest_wrapper
    def test_deny_all_ingress(self):
        """
        Verify a network policy with Ingress rule as deny all.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace.
        3. Verify that ingress is not allowed to pods of namespace "default"
        4. Verify that egress is allowed from pods of namespace "default"
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        policy_types = ["Ingress"]
        policy = self.setup_update_simple_policy(name="deny-all-ingress",
                            namespace= self.ns1.name,
                            policy_types = policy_types)
        assert policy.verify_on_setup()
        #All ingress traffic to all pods of namespace "default" should be dropped.
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_deny_all_ingress

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_podselector_for_pod(self):
        """
        Verify a network policy for a Pod with Ingress Podselector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular pod for a particular pod.
        3. Verify that ingress to the pod is allowed from configured PodSelector only.
        4. Verify that ingress from all other pods is dropped.
        5. Verify that other pods of same namespace are not affected by the policy
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        policy = self.setup_update_simple_policy(name="ingress-pod-to-pod", 
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns1.labels)
        assert policy.verify_on_setup()
        # All ingress traffic to pod cls.web_pod_ns1 will be dropped except from pod self.client1_pod_ns1.labels
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_ingress_podselector_for_pod

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_namespaceselector_for_pod(self):
        """
        Verify a network policy for a Pod with Ingress NamespaceSelector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular namespace for a particular pod.
        3. Verify that ingress to the pod is allowed from pods of configured Namespace only.
        4. Verify that ingress from all other pods is dropped.
        5. Verify that other pods of same namespace are not affected by the policy
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        policy = self.setup_update_simple_policy(name="ingress-ns-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_namespaces= self.ns2.labels)
        assert policy.verify_on_setup()
        # All ingress traffic to pod cls.web_pod_ns1 will be allowed only from all pods of namespace "non-default"
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        # Ingress traffic from Pods of same namespace "default" should not be allowed.
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        # Ingress to other pods of namespace "default" should not be affected.
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_ingress_namespaceselector_for_pod

    @preposttest_wrapper
    def test_ingress_ipblock_for_pod(self):
        """
        Verify a network policy for a Pod with Ingress IpBlock rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular IpBlock CIDR for a particular pod.
           Also mention to deny traffic from another cidr towards a particular pod.
        3. Verify that ingress to the pod is allowed from pods lying in the configured cidr
        4. Verify that ingress to other pods of "default" namespac eis not affacted.
        5. Verify that ingress from Pod mentioned in "except" block of policy is not allowed.
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        allowed_ip = self.client1_pod_ns2.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        ingress_allow_cidr = ".".join(allowed_ip)
        deny_cidr = self.client1_pod_ns1.pod_ip + "/32"
        policy = self.setup_update_simple_policy(name="ingress-ipblock-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_ipblock= {"cidr" : ingress_allow_cidr,
                                                   "_except" : [deny_cidr]})
        assert policy.verify_on_setup()
        # INgress traffic should be allowed from pods lying in "ingress_allow_cidr" but not from host ip of self.client1_pod_ns1
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        if self.client2_pod_ns1.pod_ip.split(".")[:3] == self.web_pod_ns1.pod_ip.split(".")[:3]:
            assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        # Ingress to other pods of "default" namespace is not affected
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        # INgress from cidr configured in "except" block of the policy towards self.web_pod_ns1 is not allowed
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
    #end test_ingress_ipblock_for_pod

    @test.attr(type=['openshift_1', 'ci_openshift'])
    @preposttest_wrapper
    def test_ingress_port_for_pod(self):
        """
        Verify a network policy for a Pod with Ingress Port/Protocol rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular port/protocol for a particular pod.
        3. Verify that ingress to the pod of default namespace is allowed from the
           port mentioned in the policy
        4. Verify that ingress from any other port to pods of "default" namespace is not allowed.
        5. Verify that egress from default namespace is not affected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="ingress-port-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name,
                                 ports=['TCP/80'],
                                 ingress_all =True)
        assert policy.verify_on_setup()
        # Ingress TCP traffic should be allowed and ICMP traffic should drop
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        # Egress from Pods of "default" namespace should not be affected
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url2)
    #end test_ingress_port_for_pod

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_podselector_for_namespace(self):
        """
        Verify a network policy for a Namespace with Ingress Podselector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular pod of "default" namespace.
        3. Verify that ingress to the namespace "default" is allowed from configured 
           PodSelector only.
        4. Verify that ingress from all other pods in namespace "default" is dropped.
        5. Verify that egress from namespace "default" to other namespace is not affected
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="ingress-pod-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns1.labels)
        assert policy.verify_on_setup()
        # Traffic should only be allowed from self.client1_pod_ns1 inside namespace default
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        # Traffic from any other Pod inside defaut namespace should not be allowed
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url, expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url, expectation=False)
        # Traffic from pods of "default" namespace should be able to reach pods outside the namespace
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
    #end test_ingress_podselector_for_namespace

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_podselector_for_namespace_negative(self):
        """
        Verify a network policy for a Namespace with Ingress Podselector rule where the
        Pod lies in different namespace. It is a negative test. 
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular pod of "non-default" namespace.
        3. Verify that no ingress is allowed in "default" namespace as it will search for 
           the pod in its own namespace("default") and it will not find it.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="ingress-pod-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns2.labels)
        assert policy.verify_on_setup()
        # Being a negative case where PodSelector "ingress_pods" is from different namespace, this policy is similar as deny all policy on namespace "default"
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url,
                                  expectation=False)
        # Traffic from any other Pod inside defaut namespace should not be allowed
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url, expectation=False)
        # Traffic from any other Pod from "non-default" namespace should not be allowed
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url, expectation=False)
    #end test_ingress_podselector_for_namespace_negative

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_namespaceselector_for_namespace(self):
        """
        Verify a network policy for a Namespace with Ingress NamespaceSelector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular namespace.
        3. Verify that ingress to the pods of "default" namespace is allowed from pods of configured 
           NamespaceSelector only.
        4. Verify that ingress to "default" namespace from pods of same namespace is not allowed.
        5. Verify that egress from "default" namespace to other namespace is not affected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="ingress-ns-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_namespaces= self.ns2.labels)
        assert policy.verify_on_setup()
        # Traffic from "non-default" namespace to "default" namespace should work
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        # Traffic from any other Pod inside default namespace should not be allowed
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url, expectation=False)
        # Traffic from "default" namespace to "non-default" should not be affected
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
    #end test_ingress_namespaceselector_for_namespace

    @preposttest_wrapper
    def test_ingress_ipblock_for_namespace(self):
        """
        Verify a network policy for a Namespace with Ingress IpBlock rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow ingress
           from a particular IpBlock CIDR.
           Also mention to deny traffic from another cidr towards namespace "default".
        3. Verify that ingress to all pods of  namespace "default" is allowed from pods 
           lying in the configured cidr
        4. Verify that ingress to namespace "default" from Pod mentioned in "except" 
           block of policy is not allowed.
        5. Verify that egress from namespace "default" is not affected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        allowed_ip = self.client1_pod_ns2.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        ingress_allow_cidr = ".".join(allowed_ip)
        deny_cidr = self.client2_pod_ns2.pod_ip + "/32"
        policy = self.setup_update_simple_policy(name="ingress-ipblock-to-ns",
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_ipblock= {"cidr" : ingress_allow_cidr,
                                                   "_except" : [deny_cidr]})
        assert policy.verify_on_setup()
        # Ingress traffic should be allowed from pods lying in "ingress_allow_cidr" 
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        # Ingress traffic should not be allowed from host ip of self.client2_pod_ns2
        assert self.validate_wget(self.client2_pod_ns2, url, expectation=False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        # Egress traffic from "default" to "non-default" domain should not be affacetd
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_ingress_ipblock_for_namespace

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_port_for_namespace(self):
        """
        Verify a network policy for a Namespace with Ingress Port/Protocol rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "non-default" namespace to allow ingress
           from a particular port/protocol.
        3. Verify that ingress to all pods of "non-default" namespace is allowed from the
           port mentioned in the policy
        4. Verify that ingress from any other port to pods of "non-default" namespace is not allowed.
        5. Verify that egress from "non-default" namespace is not affected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        policy = self.setup_update_simple_policy(name="ingress-port-to-ns",
                                 policy_types = ["Ingress"],
                                 namespace= self.ns2.name,
                                 ports=['TCP/80'],
                                 ingress_all =True)
        assert policy.verify_on_setup()
        # Ingress TCP traffic should be allowed in namespace "non default"
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # ingress ICMP traffic should drop in namespace "non-default"
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        # Egress ICMP trafic should be allowed from namespace "non-default"
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
    #end test_ingress_port_for_namespace

    @preposttest_wrapper
    def test_policy_with_multiple_ingress_rules(self):
        """
        Verify a network policy with multiple ingress rules specified.
        Steps:
        1. Create a network policy with ingress "from" rule mentioning "podSelector",
           "NamespaceSelector" and "port"
        2. Verify the accessibility between pods as per the rule
        3. Delete the policy and create another policy with ingress "from" rule 
           mentioning "podSelector", "IpBlock" and "port"
        4. Verify the accessibility between pods as per the rule
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': self.client1_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             'ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.web_pod_ns2.labels,
                                   name="many-selector-ingress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Ingress traffic to self.web_pod_ns2 should only be allowed from self.client1_pod_ns2 within namespace "non-defaut"
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        # Ingress traffic to self.web_pod_ns2 should be allowed from pods of namespace "default"
        assert self.validate_wget(self.client2_pod_ns1, url2)
        # INgress traffic from any other protocol than TCP/UDP should be dropped
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        
        self.perform_cleanup(policy1)
        allowed_ip = self.client2_pod_ns1.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        ingress_allow_cidr = ".".join(allowed_ip)
        ingress_list = [
            {'from': [
                    {'pod_selector': self.client1_pod_ns2.labels},
                    {'ip_block': { "cidr" : ingress_allow_cidr,
                             "_except" : [self.client1_pod_ns1.pod_ip + "/32"] }}
                    ],
             'ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy2 = self.setup_update_policy(pod_selector = self.web_pod_ns2.labels,
                                   name="many-selector-ingress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy2.verify_on_setup()
        # INgess traffic to self.web_pod_ns2 should be allowed from self.client2_pod_ns1 as per cidr rule
        assert self.validate_wget(self.client2_pod_ns1, url2)
        # INgess traffic to self.web_pod_ns2 should not be allowed from self.client1_pod_ns1 as per except rule
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation = False)
        #INgress traffic from pod self.client1_pod_ns2 should  be allowed as per podSelector rule
        assert self.validate_wget(self.client1_pod_ns2, url2)
        #INgress traffic from any other pod of non-default namespace should not be allowed until it lies in cidr range
        if self.client2_pod_ns2.pod_ip.split(".")[:3] == ingress_allow_cidr.split(".")[:3]:
            assert self.validate_wget(self.client2_pod_ns2, url2)
        else:
            assert self.validate_wget(self.client2_pod_ns2, url2, expectation=False)
        # INgress traffic from any other protocol than TCP/UDP should be dropped
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        # Ingress Traffic for any other pod of namespace "non-default" should not be affected
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        self.perform_cleanup(policy2)
    #end test_policy_with_multiple_ingress_rules

    @preposttest_wrapper
    def test_ingress_rules_edit(self):
        """
        Verify that Contrail FW policies are updated on editing the k8s netwok poliy
        Steps:
        1. Create a netwok policy on one of the podSelector of namespace "non-default" with 
           ingress from "pdSelector", "namespaceSelector" and ports.
        2. Verify that policy works as expected
        3. Update the netwok policy on same podSelector of namespace "non-default" with 
           updated "podSelector", removing "namespaceSelector", ipblock and updated ports.
        4. Verify that policy works as expected
        5. Again update the network policy with updated PodSelctor which corresponds to
           a different Pod of namespace "non-default"
        6. Verify that policy works as expected
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': self.client1_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             'ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.web_pod_ns2.labels,
                                   name="ingress-rule-edit",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Ingress traffic to self.web_pod_ns2 should only be allowed from self.client1_pod_ns2 within namespace "non-defaut"
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        # Ingress traffic to self.web_pod_ns2 should be allowed from pods of namespace "default"
        assert self.validate_wget(self.client2_pod_ns1, url2)
        # INgress traffic from any other protocol than TCP/UDP should be dropped
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        
        #Updating the same network policy
        allowed_ip = self.client2_pod_ns1.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        ingress_allow_cidr = ".".join(allowed_ip)
        ingress_list = [
            {'from': [
                    {'pod_selector': self.client2_pod_ns2.labels},
                    {'ip_block': { "cidr" : ingress_allow_cidr,
                             "_except" : [self.client1_pod_ns1.pod_ip + "/32"] }}
                    ],
             'ports': [ 'TCP/80' ]
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        
        # INgess traffic to self.web_pod_ns2 should be allowed from self.client2_pod_ns1 as per cidr rule
        assert self.validate_wget(self.client2_pod_ns1, url2)
        # INgess traffic to self.web_pod_ns2 should not be allowed from self.client1_pod_ns1 as per except rule
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation = False)
        #INgress traffic from pod self.client1_pod_ns2 should  be allowed as per podSelector rule
        assert self.validate_wget(self.client2_pod_ns2, url2)
        #INgress traffic from any other pod of non-default namespace should not be allowed until it lies in cidr range
        if self.client1_pod_ns2.pod_ip.split(".")[:3] == ingress_allow_cidr.split(".")[:3]:
            assert self.validate_wget(self.client1_pod_ns2, url2)
        else:
            assert self.validate_wget(self.client1_pod_ns2, url2, expectation=False)
        # INgress traffic from any other protocol than TCP/UDP should be dropped
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        # Ingress Traffic for any other pod of namespace "non-default" should not be affected
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        
        #Updating the policy again:
        ingress_list = [
            {'from': [
                {'namespace_selector': self.ns1.labels}
                    ],
             },
        ]
        self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client1_pod_ns2, url)
    #end test_ingress_rules_edit

    @preposttest_wrapper
    def test_multiple_ingress_policies(self):
        """
        Verify that Contrail FW policies are effective when multiple ingress policies coexist
        Steps:
        1. Create few policies for namespace "default"
        2. Create few policies for namespace "non-default"
        3. Verify that FW rules created are behaving as expected
        4. Start deleting the policies 1 by 1 and verify the reachability
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy1 = self.setup_update_simple_policy(name="ingress-pod-to-pod", 
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns1.labels)
        policy2 = self.setup_update_simple_policy(name="ingress-ns-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_namespaces= self.ns2.labels)
        assert policy1.verify_on_setup()
        assert policy2.verify_on_setup()
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns1.labels},
                    ],
             'ports': ["TCP/80"]
             },
        ]
        policy3 = self.setup_update_policy(pod_selector = self.web_pod_ns1.labels,
                                   name="ingress-port-to-pod",
                                   namespace = self.ns1.name,
                                   policy_types = ["Ingress"],
                                   ingress= ingress_list)
        policy4 = self.setup_update_simple_policy(name="ingress-pod-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns2.name, 
                                 ingress_pods= self.client1_pod_ns2.labels)
        assert policy3.verify_on_setup()
        assert policy4.verify_on_setup()
        allowed_ip = self.client1_pod_ns1.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        ingress_allow_cidr = ".".join(allowed_ip)
        deny_cidr = self.client2_pod_ns1.pod_ip + "/32"
        policy5 = self.setup_update_simple_policy(name="ingress-ipblock-to-ns",
                                 policy_types = ["Ingress"],
                                 namespace= self.ns2.name, 
                                 ingress_ipblock= {"cidr" : ingress_allow_cidr,
                                                   "_except" : [deny_cidr]})
        
        # Verifying ingress behavior on namspace "default" as per 1st 3 policies
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client2_pod_ns1, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        
        # Verifying ingress behavior on namspace "non-default" as per policy 4 and 5
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation = False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation = False)
        
        self.perform_cleanup(policy1)
        assert self.validate_wget(self.client1_pod_ns1, url, expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url)
        
        self.perform_cleanup(policy2)
        assert self.validate_wget(self.client2_pod_ns1, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url, expectation=False)
        
        self.perform_cleanup(policy3)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)

        self.perform_cleanup(policy4)
        self.perform_cleanup(policy5)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_multiple_ingress_policies

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_ingress_rules_label_edit(self):
        """
        Verify that pod reachability takes effect correctly on editing the label of 
        pods and namespace specified in network policy.
        Steps:
        1. Change the label of the pod mentioned in podSelector rule and verify reachability
        2. Change the label of the pod of namespace mentioned in namespaceSelector 
           and verify the reachability.
        3. Change the label of namespace mentioned in namespaceSelector and verify reachability.
        4. Edit the network policy to comply with the podSelector and namespaceSelector
           label and verify the reachability is as expected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': self.client1_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.web_pod_ns2.labels,
                                   name="ingress-policy-test",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Ingress behavior as per the above policy should be as follows:
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        
        # Change the label of the pod mentione in podSelector rule and verify that it cant reach self.web_pod_ns2 anymore
        self.client1_pod_ns2.set_labels({'app': 'client2_ns2'})
        self.addCleanup(self.client1_pod_ns2.set_labels, {'app': 'client1_ns2'})
        assert self.validate_wget(self.client1_pod_ns2, url2, expectation = False)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        
        # Change the label of a pods which is part of namespace mentioned in namespaceSelector. Verify that it does not matter.
        self.client2_pod_ns1.set_labels({'app': 'test'})
        self.addCleanup(self.client2_pod_ns1.set_labels, {'app': 'client2_ns1'})
        assert self.validate_wget(self.client2_pod_ns1, url2)
        
        # Change the label of namespace mentioned in namespaceSelector. Verify that pods of that namespace are not reachable anymore
        self.ns1.set_labels({'site': 'test'})
        self.addCleanup(self.ns1.set_labels, {'site': 'default'})
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation = False)
        self.client2_pod_ns2.set_labels({'app': 'client1_ns2'})
        self.addCleanup(self.client2_pod_ns2.set_labels, {'app': 'client2_ns2'})
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation = False)
        assert self.validate_wget(self.client2_pod_ns2, url2)
        
        # Update the policy corresponding to the labels changed and verify that all reachability is same as before
        ingress_list = [
            {'from': [
                {'pod_selector': {'app': 'client2_ns2'}},
                {'namespace_selector': {'site': 'test'}}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        assert self.validate_wget(self.client2_pod_ns1, url2)
    #end test_ingress_rules_label_edit

    @preposttest_wrapper
    def test_allow_all_egress(self):
        """
        Verify a network policy with Egress rule as allow all.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace
        3. Veify that all pods are still reachable from all namespaces
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        policy_types = ["Egress"]
        egress_list = [{}]
        policy1 = self.setup_update_policy(name="allow-all-egress",
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # All traffic should still work as it is ingress allow all policy
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_allow_all_egress

    def test_deny_all_egress(self):
        """
        Verify a network policy with Egress rule as deny all.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace.
        3. Verify that egress is not allowed from pods of namespace "default"
        4. Verify that ingress is allowed to the pods of namespace "default"
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        policy_types = ["Egress"]
        policy = self.setup_update_simple_policy(name="deny-all-egress",
                                 namespace= self.ns1.name,
                                policy_types = policy_types)
        assert policy.verify_on_setup()
        #All egress traffic from all pods of namespace "default" should be dropped.
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        #All ingress traffic from pods of namespace "non-default" should be allowed.
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_deny_all_egress
    
    @preposttest_wrapper
    def test_egress_podselector_for_pod(self):
        """
        Verify a network policy for a Pod with Egress Podselector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular pod for a podSelector.
        3. Verify that egress from the pod is allowed from configured PodSelector only.
        4. Verify that egress to all other pods is dropped.
        5. Verify that other pods of same namespace are not affected by the policy
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        policy = self.setup_update_simple_policy(name="egress-pod-to-pod", 
                                 pod_selector = self.client2_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_pods= self.client1_pod_ns1.labels)
        assert policy.verify_on_setup()
        # All egress traffic from pod cls.client2_pod_ns1 will be dropped except to pod self.client1_pod_ns1.labels
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)  
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        # Traffic of othe rpods should not be affected
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)  
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        #Ingress to pod cls.client2_pod_ns1 should not be affected
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_egress_podselector_for_pod
    
    @preposttest_wrapper
    def test_egress_podselector_for_namespace(self):
        """
        Verify a network policy for a Namespace with Egress Podselector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular pod of "default" namespace.
        3. Verify that egress from the namespace "default" is allowed to the configured 
           pod only.
        4. Verify that egress to all other pods in namespace "default" is dropped.
        5. Verify that egress from namespace "default" to other namespace is not affected
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="egress-pod-to-ns", 
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_pods= self.client1_pod_ns1.labels)
        assert policy.verify_on_setup()
        # Traffic should only be allowed to self.client1_pod_ns1 inside namespace default
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        # Traffic to any other Pod inside defaut namespace should not be allowed
        assert self.validate_wget(self.client2_pod_ns1, url, expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url, expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        # Traffic to pods of "non-default" namespace should not be allowed as well
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        # Ingress traffic to pods of namespace "default" should not be affected
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_ingress_podselector_for_namespace
    
    @preposttest_wrapper
    def test_egress_namespaceselector_for_pod(self):
        """
        Verify a network policy for a Pod with Egress NamespaceSelector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular namespace for a particular pod.
        3. Verify that egress from the pod is allowed from pods of configured Namespace only.
        4. Verify that egress to all other pods is dropped.
        5. Verify that other pods of same namespace are not affected by the policy
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        policy = self.setup_update_simple_policy(name="egress-ns-to-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_namespaces= self.ns2.labels)
        assert policy.verify_on_setup()
        # All egress traffic from pod cls.client1_pod_ns1 will be allowed only to all pods of namespace "non-default"
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Egress traffic to Pods of same namespace "default" should not be allowed.
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        # Egress traffic from other pods of namespace "default" should not be affected
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
    #end test_egress_namespaceselector_for_pod
    
    @preposttest_wrapper
    def test_egress_namespaceselector_for_namespace(self):
        """
        Verify a network policy for a Namespace with Egress NamespaceSelector rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular namespace.
        3. Verify that egress from the pods of "default" namespace is allowed to pods of configured 
           NamespaceSelector only.
        4. Verify that egress from "default" namespace to pods of same namespace is not allowed.
        5. Verify that ingress to "default" namespace from other namespace is not affected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns2, url)
        policy = self.setup_update_simple_policy(name="egress-ns-to-ns", 
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_namespaces= self.ns2.labels)
        assert policy.verify_on_setup()
        # Traffic to "non-default" namespace from "default" namespace should work
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        # Traffic to any other Pod inside default namespace should not be allowed
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url, expectation=False)
        # Traffic from "non default" namespace to "default" should not be affected
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
    #end test_egress_namespaceselector_for_namespace

    @preposttest_wrapper
    def test_egress_ipblock_for_pod(self):
        """
        Verify a network policy for a Pod with Egress IpBlock rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular IpBlock CIDR for a particular pod.
        3. Verify that egress from the pod is allowed to pods lying in the configured cidr
        4. Verify that egress from the pod is not allowed to any pod with IP not 
           present in configured cidr
        5. Verify that egress from other pods of "default" namespace should not be affected
        6. Verify that ingress to the pod should not be affected
        """
        # All traffic between everyone should work
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        allowed_ip = self.client1_pod_ns2.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        egress_allow_cidr = ".".join(allowed_ip)
        deny_cidr = self.client1_pod_ns1.pod_ip + "/32"
        policy = self.setup_update_simple_policy(name="egress-ipblock-to-pod",
                                 pod_selector = self.client2_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr,
                                                   "_except" : [deny_cidr]})
        assert policy.verify_on_setup()
        # Egress traffic should be allowed from self.client2_pod_ns1 to self.client1_pod_ns2 only.
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Verify egress to other pods:
        if self.web_pod_ns1.pod_ip.split(".")[:3] == self.client1_pod_ns2.pod_ip.split(".")[:3]:
            assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        else:
            assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                            expectation=False)
        #Verify that egress to pod mentioned as "_except" should not be allowed
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Egress traffic from other pods of namespace default should not be affected
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        # Ingress traffic to self.client2_pod_ns1 should not be affected
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_egress_ipblock_for_pod

    @preposttest_wrapper
    def test_egress_ipblock_for_namespace(self):
        """
        Verify a network policy for a Pod with Egress IpBlock rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular IpBlock CIDR.
        3. Verify that egress from the all pods of "default" namespace  is allowed to 
           pods lying in the configured cidr
        4. Verify that egress from the all pods of "default" namespace is not allowed to 
           any pod having IP outside configured cidr
        5. Verify that egress from other pods of "default" namespace should not be affected
        6. Verify that ingress to any pod of "default" namespace should not be affected
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        egress_allow_cidr = self.client1_pod_ns2.pod_ip + "/32"
        policy = self.setup_update_simple_policy(name="egress-ipblock-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr})
        assert policy.verify_on_setup()
        # Egress traffic should be allowed from any pod of namespace "default" to self.client1_pod_ns2 only.
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # No other egress traffic should be allowed from pods of namespace default 
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                         expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                         expectation = False)
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation = False)
        # Ingress traffic to any pod of namespace "default" from namespace "non-default" should not be affected
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_egress_ipblock_for_namespace

    @preposttest_wrapper
    def test_egress_port_for_pod(self):
        """
        Verify a network policy for a Pod with Egress Port/Protocol rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "default" namespace to allow egress
           to a particular port/protocol for a particular pod.
        3. Verify that egress from the pod of default namespace is allowed using the
           port mentioned in the policy
        4. Verify that egress using any other port is not allowed.
        5. Verify that egress from other pods of "default" namespace are not affected
        6. Verify that ingress to the pod in policy should not be affected
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        # All traffic between everyone should work
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        policy = self.setup_update_simple_policy(name="egress-ports-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
        assert policy.verify_on_setup()
        # Only TCP Egress traffic should be allowed from self.client1_pod_ns1 
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # No other egress traffic should be allowed from self.client1_pod_ns1
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation = False)
        #Egress traffic from other pods of namespace default should not be affected
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Ingress traffic to pod self.client1_pod_ns1 should not be affected from anywhere
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_egress_port_for_pod

    @preposttest_wrapper
    def test_egress_port_for_namespace(self):
        """
        Verify a network policy for a Namespace with Egress Port/Protocol rule.
        Steps:
        1. Verify that all pods are reachable from all namespaces
        2. Create a Network policy on "non-default" namespace to allow egress
           using a particular port/protocol.
        3. Verify that egress from any pod of "non-default" namespace is allowed using the
           port mentioned in the policy
        4. Verify that egress using any other port is not allowed.
        6. Verify that ingress to any pod of "non-default" namespace should not be affected
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        # All traffic between everyone should work
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        policy = self.setup_update_simple_policy(name="egress-ports-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns2.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
        assert policy.verify_on_setup()
        # Only TCP Egress traffic should be allowed from any pod of "non-default" namespace
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url)
        # No other egress traffic should be allowed from any pod of "non-default" namespace
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation = False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation = False)
        # Ingress traffic to any pod of namespace "non-default" should not be affected
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
    #end test_egress_port_for_namespace

    @preposttest_wrapper
    def test_policy_with_multiple_egress_rules(self):
        """
        Verify a network policy with multiple egress rules specified.
        Steps:
        1. Create a network policy with egress "to" rule mentioning "podSelector",
           "NamespaceSelector" and "port"
        2. Verify the accessibility between pods as per the rule
        3. Delete the policy and create another policy with egress "to" rule 
           mentioning "podSelector", "IpBlock" and "port"
        4. Verify the accessibility between pods as per the rule
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Egress"]
        egress_list = [
            {'to': [
                {'pod_selector': self.web_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                   name="many-selector-egress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Egress traffic within "non-default" namespace should only be allowed to web_pod_ns2
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Egress traffic to all pods of namespace "default" should be allowe
        assert self.validate_wget(self.client1_pod_ns2, url)
        #Non TCP traffic to anyone should not be allowed
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        self.perform_cleanup(policy1)
        allowed_ip = self.web_pod_ns1.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        egress_allow_cidr = ".".join(allowed_ip)
        egress_list = [
            {'to': [
                    {'pod_selector': self.web_pod_ns2.labels},
                    {'ip_block': { "cidr" : egress_allow_cidr,
                             "_except" : [self.client1_pod_ns1.pod_ip + "/32"] }}
                    ],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy2 = self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                   name="many-selector-egress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy2.verify_on_setup()
        # Pod client1_pod_ns2 can only reach pods mentioned in the rule
        assert self.validate_wget(self.client1_pod_ns2, url2) # podSelector rule
        assert self.validate_wget(self.client1_pod_ns2, url) # ip_block cidr rule
        # Only TCP egress is allowed and icmp would fail from client1_pod_ns2 egress_allow_cidr
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Ingress ICMP traffic should not be affected to client1_pod_ns2
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Other pods of same namespace can reach anyone using any port
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
    #end test_policy_with_multiple_egress_rules

    @preposttest_wrapper
    def test_egress_rules_edit(self):
        """
        Verify that Contrail FW policies are updated on editing the k8s netwok poliy
        Steps:
        1. Create a netwok policy on one of the podSelector of namespace "non-default" with 
           egress to a particular namespaceSelector, podSelector and port
        2. Verify that policy works as expected
        3. Update the netwok policy on same podSelector of namespace "non-default" with 
           updated "podSelector", removing "namespaceSelector", ipblock and updated ports.
        4. Verify that policy works as expected
        5. Again update the network policy with updated PodSelctor which corresponds to
           a different Pod of namespace "non-default"
        6. Verify that policy works as expected
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Egress"]
        egress_list = [
            {'to': [
                {'pod_selector': self.web_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                   name="many-selector-egress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Egress traffic within "non-default" namespace should only be allowed to web_pod_ns2
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Egress traffic to all pods of namespace "default" should be allowe
        assert self.validate_wget(self.client1_pod_ns2, url)
        #Non TCP traffic to anyone should not be allowed
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        allowed_ip = self.web_pod_ns1.pod_ip.split(".")[:3]
        allowed_ip.append("0/24")
        egress_allow_cidr = ".".join(allowed_ip)
        egress_list = [
            {'to': [
                    {'pod_selector': self.web_pod_ns2.labels},
                    {'ip_block': { "cidr" : egress_allow_cidr,
                             "_except" : [self.client1_pod_ns1.pod_ip + "/32"] }}
                    ],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        
        # Pod client1_pod_ns2 can only reach pods mentioned in the rule
        assert self.validate_wget(self.client1_pod_ns2, url2) # podSelector rule
        assert self.validate_wget(self.client1_pod_ns2, url) # ip_block cidr rule
        # Only TCP egress is allowed and icmp would fail from client1_pod_ns2 egress_allow_cidr
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Ingress ICMP traffic should not be affected to client1_pod_ns2
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Other pods of same namespace can reach anyone using any port
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
        
        #Updating the policy again:
        egress_list = [
            {'to': [
                {'namespace_selector': self.ns1.labels}
                    ],
             },
        ]
        self.setup_update_policy(pod_selector = self.client2_pod_ns2.labels,
                                update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url)
    #end test_egress_rules_edit

    @preposttest_wrapper
    def test_multiple_egress_policies(self):
        """
        Verify that Contrail FW policies are effective when multiple egress policies coexist
        Steps:
        1. Create few policies for namespace "default"
        2. Create few policies for namespace "non-default"
        3. Verify that FW rules created are behaving as expected
        4. Start deleting the policies 1 by 1 and verify the reachability
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        egress_allow_cidr = self.web_pod_ns2.pod_ip + "/32"
        policy1 = self.setup_update_simple_policy(name="egress-ipblock-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr})
        policy2 = self.setup_update_simple_policy(name="egress-ports-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
        assert policy1.verify_on_setup()
        assert policy2.verify_on_setup()
        egress_allow_cidr = self.web_pod_ns1.pod_ip + "/32"
        policy3 = self.setup_update_simple_policy(name="egress-ipblock-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns2.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr})
        policy4 = self.setup_update_simple_policy(name="egress-ports-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns2.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
        assert policy3.verify_on_setup()
        assert policy4.verify_on_setup()
        # Verifying egress behavior on namspace "default" as per 1st 2 policies
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                         expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        
        # Verifying egress behavior on namspace "non-default" as per policy 3 and 4
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        
        # Deleting policy 4 and expecting the ping from namespace "non-default" to start working
        self.perform_cleanup(policy4)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns2, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        
        # Deleting policy 3 and all egress traffic from pods of "non-default" should be allowed
        self.perform_cleanup(policy3)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        
        # Deleting policy 2 and expecting that ICMP traffic will start flowing
        self.perform_cleanup(policy2)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url, expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)

        # Deleting policy 1 and all egress traffic from pod of "default" should be allowed
        self.perform_cleanup(policy1)
        assert self.validate_wget(self.client1_pod_ns1, url)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_multiple_egress_policies

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_egress_rules_label_edit(self):
        """
        Verify that pod reachability takes effect correctly on editing the label of 
        pods and namespace specified in network policy.
        Steps:
        1. Change the label of the pod mentioned in podSelector rule and verify reachability
        2. Change the label of the pod of namespace mentioned in namespaceSelector 
           and verify the reachability.
        3. Change the label of namespace mentioned in namespaceSelector and verify reachability.
        4. Edit the network policy to comply with the podSelector and namespaceSelector
           label and verify the reachability is as expected.
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Egress"]
        egress_list = [
            {'to': [
                {'pod_selector': self.client1_pod_ns2.labels},
                {'namespace_selector': self.ns1.labels}
                    ],
             },
        ]
        policy1 = self.setup_update_policy(pod_selector = self.client2_pod_ns2.labels,
                                   name="egress-policy-test",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Egress behavior as per the above policy should be as follows:
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        
        # Change the label of the pod mentioned in podSelector rule and verify that it can't reach self.client1_pod_ns2 anymore
        self.client1_pod_ns2.set_labels({'app': 'newtest'})
        self.addCleanup(self.client1_pod_ns2.set_labels, {'app': 'client1_ns2'})
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url)
        
        # Change the label of a pods which is part of namespace mentioned in namespaceSelector. Verify that it does not matter.
        self.client2_pod_ns1.set_labels({'app': 'test'})
        self.addCleanup(self.client2_pod_ns1.set_labels, {'app': 'client2_ns1'})
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        
        # Change the label of namespace mentioned in namespaceSelector. Verify that pods of that namespace are not reachable anymore
        self.ns1.set_labels({'site': 'test'})
        self.addCleanup(self.ns1.set_labels, {'site': 'default'})
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url, expectation = False)
        
        # Update the policy corresponding to the labels changed and verify that all reachability is same as before
        egress_list = [
            {'to': [
                {'pod_selector': {'app': 'newtest'}},
                {'namespace_selector': {'site': 'test'}}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_wget(self.client2_pod_ns2, url)
        assert self.validate_wget(self.client2_pod_ns2, url2, expectation = False)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_egress_rules_label_edit

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ingress_allow_egress_allow_all(self):
        """
        Verify ingress allow all and Egress allow all policy
        Steps:
        1. Create a network Policy with both ingress and egress rules as allow all and
           apply it over a namespace.
        2. All traffic should be allowed to and from any pod of namespace.
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        policy_types = ["Ingress", "Egress"]
        ingress_list = [{}]
        egress_list = [{}]
        policy1 = self.setup_update_policy(name="ingress-allow-egress-allow",
                                           namespace= self.ns1.name,
                                           ingress= ingress_list,
                                           egress= egress_list,
                                           policy_types= policy_types)
        assert policy1.verify_on_setup()
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
    #end test_ingress_allow_egress_allow_all

    @preposttest_wrapper
    def test_ingress_allow_egress_deny_all(self):
        """
        Verify ingress allow all and Egress deny all policy
        Steps:
        1. Create a network Policy with ingress rule as allow all and egress rule as
           deny all and apply it over a namespace.
        2. All traffic should be allowed to any pod of namespace. No egress traffic
           should be allowed from any pod of the namespace.
        3. Edit the policy and apply it over one of the pod of the same namespace
        4. No traffic should be allowed from that pod to any pod. All ingress traffic to
           the pod should flow without interruption 
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        policy_types = ["Ingress", "Egress"]
        ingress_list = [{}]
        egress_list = []
        policy1 = self.setup_update_policy(name="ingress-allow-egress-deny",
                                           namespace= self.ns1.name,
                                           ingress= ingress_list,
                                           egress= egress_list,
                                           policy_types= policy_types)
        assert policy1.verify_on_setup()
        # Ingress allow all
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        # Egress deny all
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        self.perform_cleanup(policy1)
        #Create a new policy and apply it on a single pod
        policy1 = self.setup_update_policy(pod_selector = self.client2_pod_ns1.labels,
                                           name="ingress-allow-egress-deny",
                                           namespace= self.ns1.name,
                                           ingress= ingress_list,
                                           egress= egress_list,
                                           policy_types= policy_types)
        # Ingress allow all
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        # Egress deny all
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
    #end test_ingress_allow_egress_deny_all

    @preposttest_wrapper
    def test_ingress_deny_egress_allow_all(self):
        """
        Verify ingress allow all and Egress deny all policy
        Steps:
        1. Create a network Policy with ingress rule as deny all and egress rule as
           allow all and apply it over a namespace.
        2. All traffic should be allowed from any pod of namespace. No ingress traffic
           should be allowed to any pod of the namespace.
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        ingress_list = []
        egress_list = [{}]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(name="ingress-deny-egress-allow",
                                           namespace= self.ns1.name,
                                           ingress= ingress_list,
                                           egress= egress_list,
                                           policy_types= policy_types)
        assert policy1.verify_on_setup()
        # Ingress deny all
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Below check will pass as egress all takes priority over ingress deny all
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url, expectation=False)
        # Egress deny all
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
    #end test_ingress_deny_egress_allow_all

    @preposttest_wrapper
    def test_ingress_deny_egress_deny_all(self):
        """
        Verify ingress deny all and Egress deny all policy
        Steps:
        1. Create a network Policy with both ingress and egress rules as deny all and
           apply it over a namespace.
        2. No traffic should be allowed to and from any pod of namespace pods.
        3. Edit the policy and apply it over one of the pod of the same namespaec
        4. No traffic should be allowed to and from that pod of namespace. Other pods 
           should not be affected
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_simple_policy(
                            name="ingress-deny-egress-deny",
                            namespace= self.ns1.name,
                            policy_types = policy_types)
        assert policy1.verify_on_setup()
        # Verify that all ingress traffic is dropped
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url, expectation=False)
        # Verify that all egress traffic is dropped
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        #Update the policy and apply it on a single pod
        self.setup_update_policy(pod_selector = self.client2_pod_ns1.labels,
                                update = True, 
                                namespace= self.ns1.name,
                                np_fixture = policy1)
        #Verify that the updated policy is applicable only on one pod of the namespace
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client2_pod_ns1, url2, expectation = False)
    #end test_ingress_deny_egress_deny_all

    @preposttest_wrapper
    def test_ingress_egress_on_pod(self):
        """
        Create a network Policy with both ingress and egress rules specified for a pod
        and verify corresponding contrail FW policy operations.
        1. Create policy having both ingress and egress rules.
        2. Verify all ingress rules are met. 
        3. Verify no other ingress is allowed other than that mentioned in the rules
        4. Verify all egress rules are met. 
        5. Verify no other egress is allowed other than that mentioned in the rules
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns3, url)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        ingress_allow_cidr = self.client1_pod_ns1.pod_ip + "/32"
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns3.labels},
                {'namespace_selector': self.ns2.labels},
                {'ip_block': { "cidr" : ingress_allow_cidr}}
                    ]
             }
        ]
        egress_allow_cidr = self.web_pod_ns1.pod_ip + "/32"
        egress_list = [
            {'to': [
                {'pod_selector': self.client2_pod_ns3.labels},
                {'namespace_selector': self.ns2.labels},
                {'ip_block': { "cidr" : egress_allow_cidr}}
                ],
                'egress_ports': [ 'TCP/80' ]
            }
        ]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(pod_selector = self.client1_pod_ns3.labels,
                                   name="ingress-egress-policy-on-pod",
                                   namespace = self.ns3.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Verify that all ingress rules are operational
        assert self.client2_pod_ns3.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        # Verify that other pods which do not match ingress criteria cannot communicate
        assert self.client3_pod_ns3.ping_with_certainty(self.client1_pod_ns3.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns3.pod_ip,
                                                        expectation=False)
        # Verify that all egress rules are operational
        assert self.validate_wget(self.client1_pod_ns3, url)
        assert self.validate_wget(self.client1_pod_ns3, url2)
        # Verify that all pods which meeet egress criteria fails if port criteria is not met
        assert self.client1_pod_ns3.ping_with_certainty(self.client2_pod_ns3.pod_ip,
                                                        expectation=False) #podSelector
        assert self.client1_pod_ns3.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False) #namespaceSelector
        assert self.client1_pod_ns3.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False) #ipblock CIDR
        assert self.client1_pod_ns3.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        #Verfiy that other pods of the namespace 3 are not affected because of rule
        assert self.client3_pod_ns3.ping_with_certainty(self.client2_pod_ns3.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns3.pod_ip)
        assert self.validate_wget(self.client3_pod_ns3, url2)
        assert self.client3_pod_ns3.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns3.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client3_pod_ns3.ping_with_certainty(self.client2_pod_ns3.pod_ip)
    #end test_ingress_egress_on_pod

    @preposttest_wrapper
    def test_ingress_egress_on_namespace(self):
        """
        Create a network Policy with both ingress and egress rules specified for a namespace
        and verify corresponding contrail FW policy operations.
        1. Create policy having both ingress and egress rules.
        2. Verify all ingress rules are met. 
        3. Verify no other igress is allowed other than that mentioned in the rules
        4. Verify all egress rules are met. 
        5. Verify no other egress is allowed other than that mentioned in the rules
        """
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns3, url)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        ingress_allow_cidr = self.client1_pod_ns1.pod_ip + "/32"
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns3.labels},
                {'namespace_selector': self.ns2.labels},
                {'ip_block': { "cidr" : ingress_allow_cidr}}
                    ]
             }
        ]
        egress_allow_cidr = self.web_pod_ns1.pod_ip + "/32"
        egress_list = [
            {'to': [
                {'pod_selector': self.client2_pod_ns3.labels},
                {'namespace_selector': self.ns2.labels},
                {'ip_block': { "cidr" : egress_allow_cidr}}
                ],
            }
        ]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(name="ingress-egress-policy-on-ns",
                                   namespace = self.ns3.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Verify that all ingress rules are operational
        # Note that below 2 checks should fail as per egress port policy but they pass
        # as the egress port rule will fall after ingress pod selector rule in priority
        assert self.client2_pod_ns3.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client2_pod_ns3.ping_with_certainty(self.client3_pod_ns3.pod_ip)
        
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns3.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns3.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client3_pod_ns3.pod_ip)
        # Verify that other pods which do not match ingress criteria cannot communicate
        assert self.client3_pod_ns3.ping_with_certainty(self.client1_pod_ns3.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns3.ping_with_certainty(self.client3_pod_ns3.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns3.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns3.pod_ip,
                                                        expectation=False)
        # Verify that all egress rules are operational
        assert self.validate_wget(self.client1_pod_ns3, url)
        assert self.validate_wget(self.client3_pod_ns3, url)
        assert self.validate_wget(self.client1_pod_ns3, url2)
        assert self.validate_wget(self.client3_pod_ns3, url2)
        assert self.client1_pod_ns3.ping_with_certainty(self.client2_pod_ns3.pod_ip)
        assert self.client3_pod_ns3.ping_with_certainty(self.client2_pod_ns3.pod_ip)
        assert self.client1_pod_ns3.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client3_pod_ns3.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns3.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.client3_pod_ns3.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        # Verify that other pods which do not match egress criteria cannot communicate
        assert self.client1_pod_ns3.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client3_pod_ns3.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
    #end test_ingress_egress_on_namespace

class TestNetworkPolicyNSIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyNSIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyNSIsolation, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    def setup_common_namespaces_pods(self):
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        if self.setup_custom_isolation:
            vn_for_namespace = self.setup_vn(vn_name = "TestVNNamespace")
            vn_dict_for_namespace = {"domain": vn_for_namespace.domain_name,
                   "project" : vn_for_namespace.project_name,
                   "name": vn_for_namespace.vn_name}
            namespace3 = self.setup_namespace(name = get_random_name("ns3"), 
                                    custom_isolation = True,
                                    fq_network_name= vn_dict_for_namespace)
        else:
            namespace3 = self.setup_namespace(name = get_random_name("ns3"),
                                               isolation = True)
        namespace1.set_labels({'test_site': "ns1"})
        namespace2.set_labels({'test_site': "ns2"})
        namespace3.set_labels({'test_site': "ns3"})
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        namespace3.verify_on_setup()
        client1_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                             labels={'app': "c1_ns1"})
        client2_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                             labels={'app': "c2_ns1"})
        client3_ns1 = self.setup_nginx_pod(namespace=namespace1.name,
                                             labels={'app': "c3_ns1"})
        client1_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c1_ns2"})
        client2_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c2_ns2"})
        client3_ns2 = self.setup_nginx_pod(namespace=namespace2.name,
                                             labels={'app': "c3_ns2"})
        client1_ns3 = self.setup_busybox_pod(namespace=namespace3.name,
                                             labels={'app': "c1_ns3"})
        client2_ns3 = self.setup_busybox_pod(namespace=namespace3.name,
                                             labels={'app': "c2_ns3"})
        client3_ns3 = self.setup_nginx_pod(namespace=namespace3.name,
                                             labels={'app': "c3_ns3"})
        assert client1_ns1.verify_on_setup()
        assert client2_ns1.verify_on_setup()
        assert client3_ns1.verify_on_setup()
        assert client1_ns2.verify_on_setup()
        assert client2_ns2.verify_on_setup()
        assert client3_ns2.verify_on_setup()
        assert client1_ns3.verify_on_setup()
        assert client2_ns3.verify_on_setup()
        assert client3_ns3.verify_on_setup()
        ns1_clients = [client1_ns1, client2_ns1, client3_ns1, namespace1]
        ns2_clients = [client1_ns2, client2_ns2, client3_ns2, namespace2]
        ns3_clients = [client1_ns3, client2_ns3, client3_ns3, namespace3]
        return (ns1_clients, ns2_clients, ns3_clients)
    #end setup_common_namespaces_pods

    @preposttest_wrapper
    def test_ingress_policy_over_isolated_namespace(self):
        """
        Verify that namespace isolation is not affected by network policy ingress rules and 
        rules work fine within the isolated namespace.
        Steps:
        1. Create some non isolated namespaces and 1 isolated namespace.
        2. Create a Network policy qith INgress rules on isolated namespace and allow traffic
           from pods of different namespaces by using namespaceSleector and cidr.
        3. Verify that precedence of namespace isolation is more than FW policy
        4. Update the network policy and configure a PodSelector of isolated namespace
        5. Verify that precedence of namespace isolation is more than FW policy
        """
        ns1_clients, ns2_clients, ns3_clients = self.setup_common_namespaces_pods()
        url1 = 'http://%s' % (ns1_clients[2].pod_ip)
        url2 = 'http://%s' % (ns2_clients[2].pod_ip)
        url3 = 'http://%s' % (ns3_clients[2].pod_ip)
        #Test isolation works as expected
        assert self.validate_wget(ns1_clients[0], url2)
        assert self.validate_wget(ns2_clients[0], url1)
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns3_clients[0], url1, expectation=False)
        assert self.validate_wget(ns1_clients[0], url3, expectation=False)
        assert self.validate_wget(ns2_clients[0], url3, expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[0].pod_ip)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[1].pod_ip)
        # Verify an ingress policy
        ingress_allow_cidr = ns1_clients[1].pod_ip + "/32"
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': ns3_clients[1].labels},
                {'namespace_selector': ns2_clients[3].labels},
                {'ip_block': { "cidr" : ingress_allow_cidr}}
                    ]
             }
        ]
        policy1 = self.setup_update_policy(name="ingress-policy-over-isolated-ns",
                                   namespace = ns3_clients[3].name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Verify that network policy do not take precedence over network isolation
        assert self.validate_wget(ns3_clients[1], url3)
        assert self.validate_wget(ns3_clients[0], url3, expectation=False)
        assert self.validate_wget(ns2_clients[1], url3, expectation=False)
        assert self.validate_wget(ns1_clients[1], url3, expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[2].pod_ip)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[0].pod_ip)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[2].pod_ip,
                                                  expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        # Verify that egress from pods of isolated namespace is not affected
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns3_clients[1], url1, expectation=False)
        # Update the policy and configure a PodSelector of isolated namespace
        self.setup_update_policy(pod_selector = ns3_clients[2].labels,
                                update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        # Verify that network policy do not take precedence over network isolation
        assert self.validate_wget(ns3_clients[1], url3)
        assert self.validate_wget(ns3_clients[0], url3, expectation=False)
        assert self.validate_wget(ns2_clients[1], url3, expectation=False)
        assert self.validate_wget(ns1_clients[1], url3, expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[2].pod_ip)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[2].pod_ip,
                                                  expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[0].pod_ip)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[1].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns3_clients[1], url1, expectation=False)
        assert self.validate_wget(ns1_clients[0], url2)
        assert self.validate_wget(ns2_clients[0], url1)
    #end test_ingress_policy_over_isolated_namespace

    @preposttest_wrapper
    def test_egress_policy_over_isolated_namespace(self):
        """
        Verify that namespace isolation is not affected by network policy egress rules and 
        rules work fine within the isolated namespace.
        Steps:
        1. Create some non isolated namespaces and 1 isolated namespace.
        2. Create a Network policy with egress rules on isolated namespace and allow traffic
           from pods of different namespaces 
        3. Verify that precedence of namespace isolation is more than FW policy
        4. Update the network policy and configure a PodSelector of isolated namespace
        5. Verify that precedence of namespace isolation is more than FW policy
        """
        ns1_clients, ns2_clients, ns3_clients = self.setup_common_namespaces_pods()
        url1 = 'http://%s' % (ns1_clients[2].pod_ip)
        url2 = 'http://%s' % (ns2_clients[2].pod_ip)
        url3 = 'http://%s' % (ns3_clients[2].pod_ip)
        #Test isolation works as expected
        assert self.validate_wget(ns1_clients[0], url2)
        assert self.validate_wget(ns2_clients[0], url1)
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns3_clients[0], url1, expectation=False)
        assert self.validate_wget(ns1_clients[0], url3, expectation=False)
        assert self.validate_wget(ns2_clients[0], url3, expectation=False)
        # Verify an engress policy
        egress_allow_cidr = ns3_clients[2].pod_ip + "/32"
        egress_list = [
            {'to': [
                {'pod_selector': ns3_clients[2].labels},
                {'namespace_selector': ns2_clients[3].labels}],
                'egress_ports': [ 'TCP/80' ]
            }
        ]
        policy_types = ["Egress"]
        policy1 = self.setup_update_policy(name="egress-policy-over-isolated-ns",
                                   namespace = ns3_clients[3].name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Verify that network policy works as expected
        assert self.validate_wget(ns3_clients[1], url3)
        assert self.validate_wget(ns3_clients[0], url3)
        assert self.validate_wget(ns3_clients[1], url2, expectation=False)
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns2_clients[1], url3, expectation=False)
        assert self.validate_wget(ns1_clients[1], url3, expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[2].pod_ip,
                                                  expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[0].pod_ip,
                                                  expectation=False)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[2].pod_ip,
                                                  expectation=False)
        assert ns1_clients[1].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        # Verify that egress from pods of isolated namespace is affected due to FW policy
        assert self.validate_wget(ns3_clients[0], url1, expectation=False)
        assert self.validate_wget(ns3_clients[1], url1, expectation=False)
        # Update the policy and configure a PodSelector of isolated namespace
        self.setup_update_policy(pod_selector = ns3_clients[1].labels,
                                update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        # Verify that network policy do not take precedence over network isolation
        assert self.validate_wget(ns3_clients[1], url3)
        assert self.validate_wget(ns3_clients[0], url3)
        assert self.validate_wget(ns3_clients[1], url2, expectation=False)
        assert self.validate_wget(ns3_clients[0], url2, expectation=False)
        assert self.validate_wget(ns2_clients[1], url3, expectation=False)
        assert self.validate_wget(ns1_clients[1], url3, expectation=False)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[2].pod_ip,
                                                  expectation=False)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[2].pod_ip)
        assert ns3_clients[1].ping_with_certainty(ns3_clients[0].pod_ip,
                                                  expectation=False)
        assert ns3_clients[0].ping_with_certainty(ns3_clients[1].pod_ip)
        assert ns1_clients[1].ping_with_certainty(ns3_clients[1].pod_ip,
                                                  expectation=False)
        assert self.validate_wget(ns3_clients[0], url1, expectation=False)
        assert self.validate_wget(ns3_clients[1], url1, expectation=False)
    #end test_egress_policy_over_isolated_namespace
    
class TestNetworkPolicyCustomIsolation(TestNetworkPolicyNSIsolation):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyNSIsolation, cls).setUpClass()
        cls.setup_custom_isolation = True
        
class TestNetworkPolicyRandom(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyRandom, cls).setUpClass()
        
    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyRandom, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_k8s_configurations_post_policy_creation(self):
        """
        Verify that if Network policy is created before creation of k8s pods,
        it takes effect correctly post creation of pods.
        Steps:
        1. Create a policy with ingress and egress rules and mention few labels
        2. Create pods and namespaces and label them as per the policy.
        3. Verify that policy is effective on the corresponding namespace and pods
        """
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        ingress_list = [
            {'from': [
                {'pod_selector': {'app': "c2_nss1"}},
                {'namespace_selector': {'test_site': "nss2"}}
                    ]
             }
        ]
        egress_list = [{'egress_ports': [ 'TCP/80' ]}]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(pod_selector={'app': "c1_nss1"},
                                    name="ingress-egress-policy-test",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace2.verify_on_setup()
        namespace1.set_labels({'test_site': "nss1"})
        namespace2.set_labels({'test_site': "nss2"})
        client1_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                            labels={'app': "c1_nss1"})
        client2_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                             labels={'app': "c2_nss1"})
        client3_ns1 = self.setup_nginx_pod(namespace=namespace1.name,
                                             labels={'app': "c3_nss1"})
        client4_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                             labels={'app': "c4_nss1"})
        client1_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c1_nss2"})
        client2_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c2_nss2"})
        client3_ns2 = self.setup_nginx_pod(namespace=namespace2.name,
                                             labels={'app': "c3_nss2"})
        assert client1_ns1.verify_on_setup()
        assert client2_ns1.verify_on_setup()
        assert client3_ns1.verify_on_setup()
        assert client4_ns1.verify_on_setup()
        assert client1_ns2.verify_on_setup()
        assert client2_ns2.verify_on_setup()
        assert client3_ns2.verify_on_setup()
        
        #validate that policy has been applied correctly
        url1 = 'http://%s' % (client3_ns1.pod_ip)
        url2 = 'http://%s' % (client3_ns2.pod_ip)
        # Success cases as per policy :
        assert self.validate_wget(client1_ns2, url1)
        assert self.validate_wget(client1_ns1, url2)
        assert self.validate_wget(client1_ns1, url1)
        assert client2_ns1.ping_with_certainty(client1_ns1.pod_ip)
        assert client1_ns2.ping_with_certainty(client1_ns1.pod_ip)
        assert client2_ns2.ping_with_certainty(client1_ns1.pod_ip)
        # Failure cases as per policy :
        assert client1_ns1.ping_with_certainty(client2_ns1.pod_ip,
                                               expectation=False)
        assert client1_ns1.ping_with_certainty(client3_ns2.pod_ip,
                                                    expectation=False)
        assert client1_ns1.ping_with_certainty(client1_ns2.pod_ip,
                                                    expectation=False)
        assert client4_ns1.ping_with_certainty(client1_ns1.pod_ip,
                                                    expectation=False)
    #end test_k8s_configurations_post_policy_creation
   
    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_policy_negative(self):
        """
        Verify that a policy does not get applied to the pod if Pod is in different namespace
        1. Create a network policy on namespace 1 with podSelector label as pod label of namespace 2.
        2. Verify that the pod of namespace 2 is not affected by the policy 
        """
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        namespace1.set_labels({'test_site': "nss1"})
        namespace2.set_labels({'test_site': "nss2"})
        client1_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                            labels={'app': "c1_nss1"})
        client2_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                             labels={'app': "c2_nss1"})
        client1_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c1_nss2"})
        client2_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                             labels={'app': "c2_nss2"})
        assert client1_ns1.verify_on_setup()
        assert client2_ns1.verify_on_setup()
        assert client1_ns2.verify_on_setup()
        assert client2_ns2.verify_on_setup()
        ingress_list = [{'from': [{'pod_selector': {'app': "c2_nss1"}}]}]
        egress_list = [{'egress_ports': [ 'TCP/80' ]}]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(pod_selector={'app': "c2_nss2"},
                                    name="pod-selector-of-different-namespace",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        #Verify that there is no impact on client2_ns2 due to above policy as it is applied over different namespace
        assert client2_ns2.ping_with_certainty(client1_ns1.pod_ip)
        assert client2_ns2.ping_with_certainty(client1_ns2.pod_ip)
        assert client1_ns1.ping_with_certainty(client2_ns2.pod_ip)
        assert client1_ns2.ping_with_certainty(client2_ns2.pod_ip)
    #end test_policy_negative

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_deployment_replica_updation(self):
        '''
        Verify that policy gets applied on all pods of a deployment when replicas of
         a deployment are increased or decreased.
        Steps:
        1. Create 3 different namespaces and few pods in each namespace
        2. Create a deployment in namesace 1 and label all the pods under the deployment
        3. Create a policy on namespace 1 and podSelector as label of pods under deployment.
        4. Verify that policy works as expected for ingress on pods of deployment
        5. Increase the replicas of the deployment and verify policy still holds correct
        6. Decrease the replicas of the deployment and verify policy still holds correct
        '''
        labels = {'qpp': 'dep'}
        replicas = len(self.inputs.compute_ips)
        new_replicas = len(self.inputs.compute_ips)*2
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace3 = self.setup_namespace(name = get_random_name("ns3"))
        namespace1.set_labels({'site_for': "ns1"})
        namespace2.set_labels({'site_for': "ns2"})
        namespace3.set_labels({'site_for': "ns3"})
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        namespace3.verify_on_setup()
        client1_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app': "c1_ns1"})
        client2_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app': "c2_ns1"})
        client1_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app': "c1_ns2"})
        client2_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app': "c2_ns2"})
        client1_pod_ns3 = self.setup_busybox_pod(namespace=namespace3.name,
                                                labels={'app': "c1_ns3"})
        client1_pod_ns1.verify_on_setup()
        client2_pod_ns1.verify_on_setup()
        client1_pod_ns2.verify_on_setup()
        client2_pod_ns2.verify_on_setup()
        client1_pod_ns3.verify_on_setup()
        deployment = self.setup_nginx_deployment(namespace=namespace1.name,
                                            replicas=replicas, pod_labels=labels)
        
        assert deployment.verify_on_setup()
        ingress_allow_cidr = client1_pod_ns2.pod_ip + "/32"
        policy_types = ["Ingress"]
        ingress_list = [
            {'from': [
                {'pod_selector': client1_pod_ns1.labels},
                {'namespace_selector': namespace3.labels},
                {'ip_block': { "cidr" : ingress_allow_cidr}}
                    ]
             }
        ]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(pod_selector={'qpp': 'dep'},
                                    name="policy-on-all-pods-of-deployment",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        pod_ip_list = []
        for pod in deployment.get_pods_list():
            pod_ip_list.append(pod.status.pod_ip)
        for ip in pod_ip_list:
            assert client1_pod_ns1.ping_with_certainty(ip)
            assert client2_pod_ns1.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns2.ping_with_certainty(ip)
            assert client2_pod_ns2.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns3.ping_with_certainty(ip)
        
        # Creating few more replicas
        deployment.set_replicas(new_replicas)
        assert deployment.verify_on_setup()
        new_pod_ip_list = []
        for pod in deployment.get_pods_list():
            new_pod_ip_list.append(pod.status.pod_ip)
        for ip in new_pod_ip_list:
            assert client1_pod_ns1.ping_with_certainty(ip)
            assert client2_pod_ns1.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns2.ping_with_certainty(ip)
            assert client2_pod_ns2.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns3.ping_with_certainty(ip)
        
        # Reducing the replicas again
        deployment.set_replicas(replicas)
        time.sleep(15) # Delay so that extra replicas are removed
        assert deployment.verify_on_setup()
        new_pod_ip_list = []
        for pod in deployment.get_pods_list():
            new_pod_ip_list.append(pod.status.pod_ip)
        for ip in new_pod_ip_list:
            assert client1_pod_ns1.ping_with_certainty(ip)
            assert client2_pod_ns1.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns2.ping_with_certainty(ip)
            assert client2_pod_ns2.ping_with_certainty(ip, expectation=False)
            assert client1_pod_ns3.ping_with_certainty(ip)
    #end test_deployment_replica_updation
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_multiple_pod_selector(self):
        """
        Verify that Contrail FW policy considers multiple values of pod labels as podSlector
        Steps:
        1. Create 2 different namespaces
        2. Create pods under the anmespaces and mention multiple labels for the pods.
        3. Create a network policy with multiple labels in podSelector
        4. Verify that policy is applicable on pods having all the matching labels. Its a && operation 
        """
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace1.set_labels({'new_site_for': "ns1"})
        namespace2.set_labels({'new_site_for': "ns2"})
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        client1_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2", 'app3': "label3", 'app4': "label4"})
        client2_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2", 'app3': "label3"})
        client3_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2", 'app3': "label3"})
        client4_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2"})
        client5_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app2': "label2", 'app3': "label3"})
        client1_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app1': "c1_ns2"})
        client2_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app2': "c2_ns2"})
        client1_pod_ns1.verify_on_setup()
        client2_pod_ns1.verify_on_setup()
        client3_pod_ns1.verify_on_setup()
        client4_pod_ns1.verify_on_setup()
        client5_pod_ns1.verify_on_setup()
        client1_pod_ns2.verify_on_setup()
        client2_pod_ns2.verify_on_setup()
        ingress_list = [{'from': [{'namespace_selector': namespace2.labels}]}]
        egress_allow_cidr = client1_pod_ns2.pod_ip + "/32"
        egress_list = [{'to': [ {'ip_block': { "cidr" : egress_allow_cidr}}]}]
        policy_types = ["Ingress", "Egress"]
        policy1 = self.setup_update_policy(pod_selector={'app1': "label1", 'app2': "label2", 'app3': "label3"},
                                   name="policy-on-multiple-pods-of-namespace",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        #Verify ingress rules
        assert client4_pod_ns1.ping_with_certainty(client1_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client5_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client4_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client1_pod_ns2.ping_with_certainty(client1_pod_ns1.pod_ip)
        assert client2_pod_ns2.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client1_pod_ns2.ping_with_certainty(client3_pod_ns1.pod_ip)
        #Verify Egress rules
        assert client1_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client1_pod_ns1.ping_with_certainty(client2_pod_ns2.pod_ip,
                                                   expectation=False)
        assert client2_pod_ns1.ping_with_certainty(client2_pod_ns2.pod_ip,
                                                   expectation=False)
        assert client2_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip,
                                                   expectation=False)
        #Verify exceptions with client4 of namespace 1
        assert client4_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client4_pod_ns1.ping_with_certainty(client2_pod_ns2.pod_ip)
        assert client1_pod_ns2.ping_with_certainty(client4_pod_ns1.pod_ip)
        assert client4_pod_ns1.ping_with_certainty(client5_pod_ns1.pod_ip)
        assert client5_pod_ns1.ping_with_certainty(client4_pod_ns1.pod_ip)
    #end test_multiple_pod_selector
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_multiple_values_in_ingress_rule(self):
        """
        Verify the use of multiple values in ingress rule namespaceSelector, podSelector and cidr
        Steps:
        1. Create 3 different namespaces
        2. Create pods under the namespaces and mention multiple labels for the pods.
        3. Create a network policy for a podSelector with more than 1 value in podSelector rule
        4. Create a network policy on another podSelector with more than 1 value in namespaceSelector rule
        5. Verify a network policy on another podSelector with more than 1 value in ipblock cidr rule.
        6. Verify that all policies work as expected
        """
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace3 = self.setup_namespace(name = get_random_name("ns3"))
        namespace4 = self.setup_namespace(name = get_random_name("ns4"))
        namespace1.set_labels({'new_site_for': "ns1"})
        namespace2.set_labels({'new_site_for': "ns2", 'site_for': "ns3"})
        namespace3.set_labels({'new_site_for': "ns2", 'site_for': "ns3"})
        namespace4.set_labels({'new_site_for': "ns2"})
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        namespace3.verify_on_setup()
        namespace4.verify_on_setup()
        client1_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1"})
        client2_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2"})
        client3_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2", 'app3': "label3"})
        client4_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app2': "label2"})
        client1_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app1': "c1_ns2"})
        client2_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app1': "c2_ns2"})
        client1_pod_ns3 = self.setup_busybox_pod(namespace=namespace3.name,
                                                labels={'app2': "c1_ns3"})
        client1_pod_ns4 = self.setup_busybox_pod(namespace=namespace4.name,
                                                labels={'app2': "c1_ns4"})
        client2_pod_ns4 = self.setup_busybox_pod(namespace=namespace4.name,
                                                labels={'app2': "c2_ns4"})
        client1_pod_ns1.verify_on_setup()
        client2_pod_ns1.verify_on_setup()
        client3_pod_ns1.verify_on_setup()
        client4_pod_ns1.verify_on_setup()
        client1_pod_ns2.verify_on_setup()
        client2_pod_ns2.verify_on_setup()
        client1_pod_ns3.verify_on_setup()
        client1_pod_ns4.verify_on_setup()
        client2_pod_ns4.verify_on_setup()
        policy_types = ["Ingress"]
        ingress_list_1 = [{'from': [{'pod_selector': {'app1': "label1", 'app2': "label2"}}]}]
        policy1 = self.setup_update_policy(pod_selector=client1_pod_ns1.labels,
                                   name="ingress-policy-pod-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list_1)
        assert policy1.verify_on_setup()
        ingress_list_2 = [{'from': [{'namespace_selector': {'new_site_for': "ns2", 'site_for': "ns3"}}]}]
        policy2 = self.setup_update_policy(pod_selector=client2_pod_ns1.labels,
                                   name="ingress-policy-ns-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list_2)
        assert policy2.verify_on_setup()
        cidr_1 = client2_pod_ns2.pod_ip + "/32"
        cidr_2 = client2_pod_ns4.pod_ip + "/32"
        ingress_allow_cidr = client1_pod_ns4.pod_ip.split(".")[:1][0] + ".0.0.0/8"
        ingress_deny_cidr_list = [cidr_1, cidr_2]
        ingress_list_3 = [{'from': [ {'ip_block': { "cidr" : ingress_allow_cidr,
                                                     "_except" : ingress_deny_cidr_list}}]}]
        policy3 = self.setup_update_policy(pod_selector=client3_pod_ns1.labels,
                                   name="ingress-policy-cidr-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list_3)
        assert policy3.verify_on_setup()
        #Verify ingress rules for podSelector
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns1.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns1.pod_ip)
        assert client1_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client2_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client4_pod_ns1.ping_with_certainty(client1_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client4_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client4_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip) # This will pass because of cidr allow rule

        #Verify ingress rules for namespaceSelector
        assert client1_pod_ns2.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client1_pod_ns3.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client1_pod_ns2.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client1_pod_ns3.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client1_pod_ns4.ping_with_certainty(client2_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client1_pod_ns4.ping_with_certainty(client3_pod_ns1.pod_ip) # This will pass because of cidr allow rule
        assert client1_pod_ns4.ping_with_certainty(client1_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client1_pod_ns4.ping_with_certainty(client4_pod_ns1.pod_ip)
        assert client1_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip,
                                                   expectation=False)
        
        
        
        #Verify ingress rules for ipblock cidr _except
        assert client2_pod_ns2.ping_with_certainty(client3_pod_ns1.pod_ip)# This will pass because of namespace rule
        assert client1_pod_ns3.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client2_pod_ns4.ping_with_certainty(client3_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client2_pod_ns4.ping_with_certainty(client1_pod_ns1.pod_ip,
                                                   expectation=False) # This will fail because of po rule
        assert client2_pod_ns4.ping_with_certainty(client2_pod_ns1.pod_ip,
                                                   expectation=False) # This will fail because of namespace rule
        assert client2_pod_ns4.ping_with_certainty(client4_pod_ns1.pod_ip)
    #end test_multiple_values_in_ingress_rule

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_multiple_values_in_egress_rule(self):
        """
        Verify the use of multiple values in egress rule namespaceSelector, podSelector and cidr
        Steps:
        1. Create 3 different namespaces
        2. Create pods under the namespaces and mention multiple labels for the pods.
        3. Create a network policy for a podSelector with more than 1 value in podSelector rule
        4. Create a network policy on another podSelector with more than 1 value in namespaceSelector rule
        5. Verify a network policy on another podSelector with more than 1 value in ipblock cidr rule.
        6. Verify that all policies work as expected
        """
        namespace1 = self.setup_namespace(name = get_random_name("ns1"))
        namespace2 = self.setup_namespace(name = get_random_name("ns2"))
        namespace3 = self.setup_namespace(name = get_random_name("ns3"))
        namespace4 = self.setup_namespace(name = get_random_name("ns4"))
        namespace1.set_labels({'new_site_for': "ns1"})
        namespace2.set_labels({'new_site_for': "ns2", 'site_for': "ns3"})
        namespace3.set_labels({'new_site_for': "ns2", 'site_for': "ns3"})
        namespace4.set_labels({'new_site_for': "ns2"})
        namespace1.verify_on_setup()
        namespace2.verify_on_setup()
        namespace3.verify_on_setup()
        namespace4.verify_on_setup()
        client1_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1"})
        client2_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2"})
        client3_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app1': "label1", 'app2': "label2", 'app3': "label3"})
        client4_pod_ns1 = self.setup_busybox_pod(namespace=namespace1.name,
                                                labels={'app2': "label2"})
        client1_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app1': "c1_ns2"})
        client2_pod_ns2 = self.setup_busybox_pod(namespace=namespace2.name,
                                                labels={'app1': "c2_ns2"})
        client1_pod_ns3 = self.setup_busybox_pod(namespace=namespace3.name,
                                                labels={'app2': "c1_ns3"})
        client1_pod_ns4 = self.setup_busybox_pod(namespace=namespace4.name,
                                                labels={'app2': "c1_ns4"})
        client2_pod_ns4 = self.setup_busybox_pod(namespace=namespace4.name,
                                                labels={'app2': "c2_ns4"})
        client1_pod_ns1.verify_on_setup()
        client2_pod_ns1.verify_on_setup()
        client3_pod_ns1.verify_on_setup()
        client4_pod_ns1.verify_on_setup()
        client1_pod_ns2.verify_on_setup()
        client2_pod_ns2.verify_on_setup()
        client1_pod_ns3.verify_on_setup()
        client1_pod_ns4.verify_on_setup()
        client2_pod_ns4.verify_on_setup()
        policy_types = ["Egress"]
        egress_list_1 = [{'to': [{'pod_selector': {'app1': "label1", 'app2': "label2"}}]}]
        policy1 = self.setup_update_policy(pod_selector=client1_pod_ns1.labels,
                                   name="egress-policy-pod-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   egress= egress_list_1)
        assert policy1.verify_on_setup()
        egress_list_2 = [{'to': [{'namespace_selector': {'new_site_for': "ns2", 'site_for': "ns3"}}]}]
        policy2 = self.setup_update_policy(pod_selector=client2_pod_ns1.labels,
                                   name="egress-policy-ns-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   egress= egress_list_2)
        assert policy2.verify_on_setup()
        cidr_1 = client2_pod_ns2.pod_ip + "/32"
        cidr_2 = client2_pod_ns4.pod_ip + "/32"
        egress_allow_cidr = client1_pod_ns4.pod_ip.split(".")[:1][0] + ".0.0.0/8"
        egress_deny_cidr_list = [cidr_1, cidr_2]
        egress_list_3 = [{'to': [ {'ip_block': { "cidr" : egress_allow_cidr,
                                                     "_except" : egress_deny_cidr_list}}]}]
        policy3 = self.setup_update_policy(pod_selector=client3_pod_ns1.labels,
                                   name="egress-policy-cidr-rule-multiple-values",
                                   namespace = namespace1.name,
                                   policy_types = policy_types,
                                   egress= egress_list_3)
        assert policy3.verify_on_setup()
        #Verify egress rules for podSelector
        assert client1_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client1_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client1_pod_ns1.ping_with_certainty(client4_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client2_pod_ns1.ping_with_certainty(client3_pod_ns1.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client2_pod_ns1.pod_ip)
        assert client2_pod_ns1.ping_with_certainty(client4_pod_ns1.pod_ip,
                                                   expectation=False)
        assert client3_pod_ns1.ping_with_certainty(client4_pod_ns1.pod_ip) # This will pass because of cidr allow rule
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns1.pod_ip,
                                                   expectation=False)

        #Verify egress rules for namespaceSelector
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns3.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns3.pod_ip)
        assert client2_pod_ns1.ping_with_certainty(client1_pod_ns4.pod_ip,
                                                   expectation=False)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns4.pod_ip) # This will pass because of cidr allow rule
        assert client1_pod_ns1.ping_with_certainty(client1_pod_ns3.pod_ip,
                                                   expectation=False)

        #Verify egress rules for ipblock cidr _except
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns2.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns3.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client1_pod_ns4.pod_ip)
        assert client3_pod_ns1.ping_with_certainty(client2_pod_ns4.pod_ip,
                                                   expectation=False)
        assert client3_pod_ns1.ping_with_certainty(client2_pod_ns2.pod_ip) # This will pass because of namespace  rule
    #end test_multiple_values_in_egress_rule
    
class TestNetworkPolicyServiceIngress(BaseK8sTest):

    class SharedResources (with_metaclass(Singleton, object)):
        def __init__ (self, connections):
            self.connections = connections
            self.setUp()

        def setUp (self):
            try:
                self.ns1 = NamespaceFixture(connections=self.connections, 
                                        name=get_random_name("new-default"))
                self.ns1.setUp()
                self.ns2 = NamespaceFixture(connections=self.connections,
                                        name=get_random_name("non-default"))
                self.ns2.setUp()
                self.ns1.set_labels({'site_for_ns': self.ns1.name})
                self.ns2.set_labels({'site_for_ns': self.ns2.name})
                web_label_ns1 = 'web_ns1'
                web_label_ns2 = 'web_ns2'
                client1_label_ns1, client1_label_ns2= 'client1_ns1', 'client1_ns2'
                client2_label_ns1, client2_label_ns2 = 'client2_ns1', 'client2_ns2'
                nginx_spec_1 = {'containers': [{'image': 'nginx',
                                                'ports': [{'container_port': 80}]}]}
                nginx_spec_2 = {'containers': [{'image': 'nginx',
                                                'ports': [{'container_port': 80}]}]}
                nginx_spec_3 = {'containers': [{'image': 'nginx',
                                            'ports': [{'container_port': 80}]}]}
                nginx_spec_4 = {'containers': [{'image': 'nginx',
                                                'ports': [{'container_port': 80}]}]}
                nginx1_metadata_ns1 = {'labels': {'app': web_label_ns1, 'app2' : 'common_label'}}
                nginx2_metadata_ns1 = {'labels': {'app': web_label_ns1, 'app2' : 'common_label'}}
                nginx1_metadata_ns2 = {'labels': {'app': web_label_ns2, 'app2' : 'common_label'}}
                nginx2_metadata_ns2 = {'labels': {'app': web_label_ns2, 'app2' : 'common_label'}}
                self.web1_pod_ns1 = PodFixture(connections=self.connections,
                                            namespace=self.ns1.name,
                                            metadata=nginx1_metadata_ns1,
                                            spec=nginx_spec_1)
                self.web1_pod_ns1.setUp()
                self.web2_pod_ns1 = PodFixture(connections=self.connections,
                                            namespace=self.ns1.name,
                                            metadata=nginx2_metadata_ns1,
                                            spec=nginx_spec_2)
                self.web2_pod_ns1.setUp()
                self.web1_pod_ns2 = PodFixture(connections=self.connections,
                                            namespace=self.ns2.name,
                                            metadata=nginx1_metadata_ns2,
                                            spec=nginx_spec_3)
                self.web1_pod_ns2.setUp()
                self.web2_pod_ns2 = PodFixture(connections=self.connections,
                                            namespace=self.ns2.name,
                                            metadata=nginx2_metadata_ns2,
                                            spec=nginx_spec_4)
                self.web2_pod_ns2.setUp()
                busybox_spec_1 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                                'image_pull_policy': 'IfNotPresent',}],
                                            'restart_policy': 'Always'}
                busybox_spec_2 = dict(busybox_spec_1)
                busybox_spec_3 = dict(busybox_spec_1)
                busybox_spec_4 = dict(busybox_spec_1)
                busybox_metadata_c1_ns1 = {'labels': {'app': client1_label_ns1}}
                busybox_metadata_c1_ns2 = {'labels': {'app': client1_label_ns2}}
                busybox_metadata_c2_ns1 = {'labels': {'app': client2_label_ns1}}
                busybox_metadata_c2_ns2 = {'labels': {'app': client2_label_ns2}}
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
                assert self.ns1.verify_on_setup()
                assert self.ns2.verify_on_setup()
                assert self.web1_pod_ns1.verify_on_setup()
                assert self.web2_pod_ns1.verify_on_setup()
                assert self.web1_pod_ns2.verify_on_setup()
                assert self.web2_pod_ns2.verify_on_setup()
                assert self.client1_pod_ns1.verify_on_setup()
                assert self.client1_pod_ns2.verify_on_setup()
                assert self.client2_pod_ns1.verify_on_setup()
                assert self.client2_pod_ns2.verify_on_setup()
            except:
                self.cleanUp()
                raise

        def cleanUp (self):
            cleanup_list = list()
            if getattr(self, 'web1_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.web1_pod_ns1.cleanUp))
            if getattr(self, 'web2_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.web2_pod_ns1.cleanUp))
            if getattr(self, 'web1_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.web1_pod_ns2.cleanUp))
            if getattr(self, 'web2_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.web2_pod_ns2.cleanUp))
            if getattr(self, 'client1_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.client1_pod_ns1.cleanUp))
            if getattr(self, 'client2_pod_ns1', None):
                cleanup_list.append(gevent.spawn(self.client2_pod_ns1.cleanUp))
            if getattr(self, 'client1_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.client1_pod_ns2.cleanUp))
            if getattr(self, 'client2_pod_ns2', None):
                cleanup_list.append(gevent.spawn(self.client2_pod_ns2.cleanUp))
            gevent.joinall(cleanup_list)
            if getattr(self, 'ns2', None):
                self.ns2.cleanUp()
            if getattr(self, 'ns1', None):
                self.ns1.cleanUp()

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicyServiceIngress, cls).setUpClass()

    def setUp(self):
        super(TestNetworkPolicyServiceIngress, self).setUp()
        self._res = self.__class__.SharedResources(self.connections)
        self.__class__._shared_resources = self._res
        self.ns1 = self._res.ns1
        self.ns2 = self._res.ns2
        self.web1_pod_ns1 = self._res.web1_pod_ns1
        self.web2_pod_ns1 = self._res.web2_pod_ns1
        self.web1_pod_ns2 = self._res.web1_pod_ns2
        self.web2_pod_ns2 = self._res.web2_pod_ns2
        self.client1_pod_ns1 = self._res.client1_pod_ns1
        self.client2_pod_ns1 = self._res.client2_pod_ns1
        self.client1_pod_ns2 = self._res.client1_pod_ns2
        self.client2_pod_ns2 = self._res.client2_pod_ns2

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicyServiceIngress, cls).tearDownClass()
        if getattr(cls, '_shared_resources'):
            cls._shared_resources.cleanUp()
        
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_ingress_rule_on_namespace_with_service(self):
        """
        Verify that ingress rules on a namespace work fine when pods are accessed via a servie
        Steps:
        1. Create a service in namespace 1.
        2. Create a network policy to allow 1 pod of namespace 1 as ingress
        3. Verify that service respond correctly to the specified pod in the policy and
           service do not respond to anyone else.
        4. Extend the policy and add the namespaceselector as namespace 2
        5. Verify that service become accessible to the pods of namespace 2
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app': 'web_ns1'})
        assert service_ns1.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        ingress_list = [{'from': [{'pod_selector': self.client2_pod_ns1.labels}]}]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(name="ingress-on-service",
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Verify is policy works as expected
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1, expectation=False)
        # Updating the policy and adding the namespace selector
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns1.labels},
                {'namespace_selector': self.ns2.labels}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1)
    #end test_ingress_rule_on_namespace_with_service
    
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_egress_rule_on_namespace_with_service(self):
        """
        Verify that egress rules on a namespace work fine when pods are accessed via a servie
        Steps:
        1. Create a service in namespace 1.
        2. Create a network policy to allow agress to service IP
        3. Verify that service respond correctly to all pods of namespace.
        4. Extend the policy and add the namespaceselector as namespace 2
        5. Verify that service become accessible to the pods of namespace 2
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        url3 = 'http://%s' % (self.web2_pod_ns2.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app': 'web_ns1'})
        assert service_ns1.verify_on_setup()
        service_ns2 = self.setup_http_service(namespace=self.ns2.name,
                                          labels={'app': 'web_ns2'})
        assert service_ns2.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        egress_allow_cidr = service_ns1.cluster_ip + "/32"
        egress_list = [{'to': [{'ip_block': { "cidr" : egress_allow_cidr}}]}]
        policy_types = ["Egress"]
        policy1 = self.setup_update_policy(name="egress-to-service",
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Verify that policy should fail as the DNAT at VIP of load balancer(Service) wont be resolved
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        egress_endpoint1_cidr = self.web1_pod_ns1.pod_ip + "/32"
        egress_endpoint2_cidr = self.web2_pod_ns1.pod_ip + "/32"
        egress_list = [
            {'to': [
                {'ip_block': { "cidr" : egress_allow_cidr}},
                {'ip_block': { "cidr" : egress_endpoint1_cidr}},
                {'ip_block': { "cidr" : egress_endpoint2_cidr}}
                ]
            }
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url3, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1)
        # Updating the policy and adding the namespace selector
        egress_list = [
            {'to': [
                {'ip_block': { "cidr" : egress_allow_cidr}},
                {'ip_block': { "cidr" : egress_endpoint1_cidr}},
                {'ip_block': { "cidr" : egress_endpoint2_cidr}},
                {'namespace_selector': self.ns2.labels}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url3)
        assert self.validate_wget(self.client2_pod_ns2, url1)
    #end test_egress_rule_on_namespace_with_service
    
    @test.attr(type=['ci_k8s_sanity', 'k8s_sanity'])
    @preposttest_wrapper
    def test_ingress_rule_on_pod_with_service(self):
        """
        Verify that ingress rules on a pod work fine when pods are accessed via a service
        Steps:
        1. Create a service in namespace 1 over a pod which are endpoints of a service
        2. Create a network policy to allow 1 pod of namespace 1 as ingress.
        3. Verify that service respond correctly to the specified pod in the policy and
           service do not respond to anyone else.
        4. Extend the policy and add the namespaceselector as namespace 2.
        5. Verify that service become accessible to the pods of namespace 2.
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app2': 'common_label'})
        assert service_ns1.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        ingress_list = [{'from': [{'pod_selector': self.client2_pod_ns1.labels}]}]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(pod_selector={'app2': 'common_label'},
                                    name="ingress-on-service",
                                    namespace = self.ns1.name,
                                    policy_types = policy_types,
                                    ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Verify is policy works as expected
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1, expectation=False)
        # Updating the policy and adding the namespace selector
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns1.labels},
                {'namespace_selector': self.ns2.labels}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                ingress= ingress_list)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1)
    #end test_ingress_rule_on_pod_with_service

    @preposttest_wrapper
    def test_egress_rule_on_pod_with_service(self):
        """
        Verify that egress rules on a pod work fine when pods are accessed via a servie
        Steps:
        1. Create a service in namespace 1.
        2. Create a network policy to allow egress to pods under the service
        3. Verify that service respond correctly to all pods of namespace.
        4. Extend the policy and add the namespaceselector as namespace 2
        5. Verify that service become accessible to the pods of namespace 2
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        url3 = 'http://%s' % (self.web2_pod_ns2.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app': 'web_ns1'})
        service_ns2 = self.setup_http_service(namespace=self.ns2.name,
                                          labels={'app': 'web_ns2'})
        assert service_ns1.verify_on_setup()
        assert service_ns2.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        egress_allow_cidr = service_ns1.cluster_ip + "/32"
        egress_list = [{'to': [{'pod_selector': {'app2':'common_label'}}]}]
        policy_types = ["Egress"]
        policy1 = self.setup_update_policy(pod_selector= self.client2_pod_ns1.labels,
                                   name="egress-to-service", 
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        assert policy1.verify_on_setup()
        # Verify if policy works as expected
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client2_pod_ns1, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client2_pod_ns1, url3, expectation=False)
        assert self.validate_wget(self.client1_pod_ns1, url3)
        assert self.validate_wget(self.client2_pod_ns2, url1)
        # Updating the policy and adding the namespace selector
        egress_list = [
            {'to': [
                {'pod_selector': {'app2':'common_label'}},
                {'namespace_selector': self.ns2.labels}
                    ],
             },
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns2,self.web2_pod_ns2], 
                                      service_ns2.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client2_pod_ns1, url3)
        assert self.validate_wget(self.client1_pod_ns1, url3)
        assert self.validate_wget(self.client2_pod_ns2, url1)
    #end test_egress_rule_on_pod_with_service

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_rule_on_namespace_with_k8s_ingress(self):
        """
        Verify that ingress rules on a namespace are not effective on pods present 
        under k8s Ingress.
        k8s Ingress is a proxy for traffic originating from internet and should not be
        affected by k8s network policies. In k8s INgress, being a proxy, the source context
        is lost as well. Thus k8singress FW policy in contrail, avoid from traffic drop
        Steps:
        1. Create a service in namespace 1.
        2. Create a k8s-Ingress with service as its backend
        3. Create a network policy with INgress rule to allow traffic only from a podSelector
        4. Verify that access to Ingress via pod of same namespace, pod of different namespace
           or external world should always be allowed.
        5. Verify that policy works as expected for any access other than accessing the k8s-Ingress
           k8s-Ingress has to be the exception.
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app': 'web_ns1'})
        assert service_ns1.verify_on_setup()
        k8s_ingress = self.setup_simple_nginx_ingress(service_ns1.name,
                                                  namespace=self.ns1.name)
        assert k8s_ingress.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns1.labels}
                    ],
             },
        ]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(name="ingress-rule-on-k8s-ingress-ns",
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Verify is policy works as expected
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.external_ips[0], expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1, expectation=False)
    #end test_ingress_rule_on_namespace_with_k8s_ingress
    
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_rule_on_pod_with_k8s_ingress(self):
        """
        Verify that ingress rules on a pod label are not effective on pods present 
        under k8s Ingress.
        k8s Ingress is a proxy for traffic originating from internet and should not be
        affected by k8s network policies, In k8s INgress, being a proxy, the source context
        is lost as well. Thus k8singress FW policy in contrail, avoid from traffic drop
        Steps:
        1. Create a service in namespace 1.
        2. Create a k8s-Ingress with service as its backend
        3. Create a network policy with INgress rule to allow traffic only from a podSelector
        4. Verify that access to Ingress via pod of same namespace, pod of different namespace
           or external world should always be allowed.
        5. Verify that policy works as expected for any access other than accessing the k8s-Ingress
           k8s-Ingress has to be the exception.
        """
        # All traffic between everyone should work
        url1 = 'http://%s' % (self.web1_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web2_pod_ns1.pod_ip)
        self.web1_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns1.name))
        self.web2_pod_ns1.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns1.name))
        self.web1_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web1_pod_ns2.name))
        self.web2_pod_ns2.run_cmd('echo %s > /usr/share/nginx/html/index.html' 
                                  % (self.web2_pod_ns2.name))
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels={'app': 'web_ns1'})
        assert service_ns1.verify_on_setup()
        k8s_ingress = self.setup_simple_nginx_ingress(service_ns1.name,
                                                  namespace=self.ns1.name)
        assert k8s_ingress.verify_on_setup()
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        ingress_list = [
            {'from': [
                {'pod_selector': self.client2_pod_ns1.labels}
                    ],
             },
        ]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(pod_selector={'app2': 'common_label'},
                                    name="ingress-rule-on-k8s-ingress-pod",
                                   namespace = self.ns1.name,
                                   policy_types = policy_types,
                                   ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Verify is policy works as expected
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      k8s_ingress.external_ips[0])
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns1, expectation=False)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client2_pod_ns1)
        assert self.validate_nginx_lb([self.web1_pod_ns1,self.web2_pod_ns1], 
                                      service_ns1.cluster_ip,
                                      test_pod=self.client1_pod_ns2, expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.validate_wget(self.client2_pod_ns1, url1)
        assert self.validate_wget(self.client2_pod_ns1, url2)
        assert self.validate_wget(self.client1_pod_ns1, url2, expectation=False)
        assert self.validate_wget(self.client2_pod_ns2, url1, expectation=False)
    #end test_ingress_rule_on_pod_with_k8s_ingress
   
    @test.attr(type=['k8s_sanity'])
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_rule_on_namespace_with_k8s_ingress_fanout(self):
        """
        Verify that ingress rules on a namespace are not effective on pods present 
        under k8s Ingress.
        Steps:
        1. Create 4 temporary pods and create 2 services with 2 pods as enpoint of each service
        2. Create a Fanout k8s-Ingress with 2 backends as 2 different services
        3. Validate that the k8s-INgress is accessible from all pods and from outer world as well.
        4. Create a network policy over namespace 1 to allowe ingress rule for namespace 2.
        5. Verify that k8s-INgress is not impacted by this rule and is always accessible
           from all pods of all namespaces and from outside world.
        """
        # All traffic between everyone should work
        app1 = 'http_test1'
        app2 = 'http_test2'
        labels1 = {'appl':app1}
        labels2 = {'appl':app2}
        path1 = 'foo'
        path2 = 'bar'
        host1 = 'foo.bar.com'
        host2 = 'bar.foo.com' 
        ingress_name = 'testingress'
        temp_pod1 = self.setup_nginx_pod(namespace=self.ns1.name,
                                          labels=labels1)
        temp_pod2 = self.setup_nginx_pod(namespace=self.ns1.name,
                                          labels=labels1)
        temp_pod3 = self.setup_nginx_pod(namespace=self.ns1.name,
                                          labels=labels2)
        temp_pod4 = self.setup_nginx_pod(namespace=self.ns1.name,
                                          labels=labels2)
        assert self.verify_nginx_pod(temp_pod1,path=path1)
        assert self.verify_nginx_pod(temp_pod2,path=path1)
        assert self.verify_nginx_pod(temp_pod3,path=path2)
        assert self.verify_nginx_pod(temp_pod4,path=path2)
        service_ns1 = self.setup_http_service(namespace=self.ns1.name,
                                          labels=labels1)
        service_ns2 = self.setup_http_service(namespace=self.ns1.name,
                                          labels=labels2)        
        rules = [{'host': host1, 
                  'http': {'paths': [{
                                    'path':'/'+path1,
                                    'backend': { 'service_name': service_ns1.name,
                                                 'service_port': 80
                                               }
                                    }]
                          }
                 },
                 {'host': host2,
                  'http': {'paths': [{
                                    'path': '/'+path2,
                                    'backend': { 'service_name': service_ns2.name,
                                                 'service_port': 80
                                               }
                                    }]    
                         }
                 }]
   
        default_backend = {'service_name': service_ns1.name,
                           'service_port': 80}

        ingress = self.setup_ingress(name=ingress_name,
                                     namespace=self.ns1.name,
                                     rules=rules,
                                     default_backend=default_backend)
        assert ingress.verify_on_setup()
        
        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1, path=path1, host=host1)
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.cluster_ip,
                                      test_pod=self.client2_pod_ns1, path=path1, host=host1)
        assert self.validate_nginx_lb([temp_pod3, temp_pod4], ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2, path=path2, host=host2)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.external_ips[0],
                                       path=path1, host=host1)
        assert self.validate_nginx_lb([temp_pod3, temp_pod4], ingress.external_ips[0],
                                       path=path2, host=host2)
        
        ingress_list = [{'from': [{'namespace_selector': self.ns2.labels}]}]
        policy_types = ["Ingress"]
        policy1 = self.setup_update_policy(name="ingress-on-k8s-ingress-fanout",
                                    namespace = self.ns1.name,
                                    policy_types = policy_types,
                                    ingress= ingress_list)
        assert policy1.verify_on_setup()
        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns1, path=path1, host=host1,
                                      expectation=False)
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.cluster_ip,
                                      test_pod=self.client2_pod_ns1, path=path1, host=host1,
                                      expectation=False)
        assert self.validate_nginx_lb([temp_pod3, temp_pod4], ingress.cluster_ip,
                                      test_pod=self.client1_pod_ns2, path=path2, host=host2)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([temp_pod1, temp_pod2], ingress.external_ips[0],
                                       path=path1, host=host1, expectation=False)
        assert self.validate_nginx_lb([temp_pod3, temp_pod4], ingress.external_ips[0],
                                       path=path2, host=host2, expectation=False)
    #end test_ingress_rule_on_namespace_with_k8s_ingress_fanout
