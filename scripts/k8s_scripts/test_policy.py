
from common.k8s.base import BaseK8sTest, _GenericTestBaseMethods
from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase

import copy
from k8s.namespace import NamespaceFixture
from k8s.pod import PodFixture


class TestNetworkPolicy(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicy, cls).setUpClass()
        cls.ns1 = NamespaceFixture(connections=cls.connections, name="default")
        #cls.ns1.setUp()
        cls.ns2 = NamespaceFixture(connections=cls.connections, name="non-default")
        cls.ns2.setUp()
        #cls.ns1.set_labels({'project': cls.ns1.name})
        cls.ns1.set_labels({'site': cls.ns1.name})
        cls.ns2.set_labels({'site': cls.ns2.name})
        web_label_ns1, web_label_ns2 = 'webns1', 'webns2'
        client1_label_ns1, client1_label_ns2 = 'client1_ns1', 'client1_ns2'
        client2_label_ns1, client2_label_ns2 = 'client2_ns1', 'client2_ns2'
        nginx_spec_1 = {'containers': [{'image': 'nginx',
                                        'ports': [{'container_port': 80}]}]}
        nginx_spec_2 = {'containers': [{'image': 'nginx',
                                        'ports': [{'container_port': 80}]}]}
        nginx_metadata_ns1 = {'labels': {'app': web_label_ns1}}
        nginx_metadata_ns2 = {'labels': {'app': web_label_ns2}}
        cls.web_pod_ns1 = PodFixture(connections=cls.connections,
                                     namespace=cls.ns1.name,
                                     metadata=nginx_metadata_ns1,
                                     spec=nginx_spec_1)
        cls.web_pod_ns1.setUp()
        cls.web_pod_ns2 = PodFixture(connections=cls.connections,
                                     namespace=cls.ns2.name,
                                     metadata=nginx_metadata_ns2,
                                     spec=nginx_spec_2)
        cls.web_pod_ns2.setUp()
        busybox_spec_1 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                          'image_pull_policy': 'IfNotPresent',}],
                                    'restart_policy': 'Always'}
        busybox_spec_2 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                          'image_pull_policy': 'IfNotPresent',}],
                                    'restart_policy': 'Always'}
        busybox_spec_3 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                          'image_pull_policy': 'IfNotPresent',}],
                                    'restart_policy': 'Always'}
        busybox_spec_4 = {'containers': [{'image': 'busybox','command': ['sleep', '1000000'],
                                          'image_pull_policy': 'IfNotPresent',}],
                                    'restart_policy': 'Always'}
        busybox_metadata_c1_ns1 = {'labels': {'app': client1_label_ns1}}
        busybox_metadata_c1_ns2 = {'labels': {'app': client1_label_ns2}}
        busybox_metadata_c2_ns1 = {'labels': {'app': client2_label_ns1}}
        busybox_metadata_c2_ns2 = {'labels': {'app': client2_label_ns2}}
        cls.client1_pod_ns1 = PodFixture(connections=cls.connections,
                                        namespace=cls.ns1.name,
                                        metadata=busybox_metadata_c1_ns1,
                                        spec=busybox_spec_1)
        cls.client1_pod_ns1.setUp()
        cls.client2_pod_ns1 = PodFixture(connections=cls.connections,
                                         namespace=cls.ns1.name,
                                         metadata=busybox_metadata_c2_ns1,
                                         spec=busybox_spec_2)
        cls.client2_pod_ns1.setUp()
        cls.client1_pod_ns2 = PodFixture(connections=cls.connections,
                                         namespace=cls.ns2.name,
                                         metadata=busybox_metadata_c1_ns2,
                                         spec=busybox_spec_3)
        cls.client1_pod_ns2.setUp()
        cls.client2_pod_ns2 = PodFixture(connections=cls.connections,
                                         namespace=cls.ns2.name,
                                         metadata=busybox_metadata_c2_ns2,
                                         spec=busybox_spec_4)
        cls.client2_pod_ns2.setUp()
        assert cls.web_pod_ns1.verify_on_setup()
        assert cls.web_pod_ns2.verify_on_setup()
        assert cls.client1_pod_ns1.verify_on_setup()
        assert cls.client1_pod_ns2.verify_on_setup()
        assert cls.client2_pod_ns1.verify_on_setup()
        assert cls.client2_pod_ns2.verify_on_setup()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicy, cls).tearDownClass()
        cls.web_pod_ns1.cleanUp()
        cls.web_pod_ns2.cleanUp()
        cls.client1_pod_ns1.cleanUp()
        cls.client2_pod_ns1.cleanUp()
        cls.client1_pod_ns2.cleanUp()
        cls.client2_pod_ns2.cleanUp()
        cls.ns2.cleanUp()

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
        self.setup_update_simple_policy(name="allow-all-ingress",
                                 namespace= self.ns1.name,
                                ingress_all =True)
        # All traffic should still work as it is ingress allow all policy
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_allow_all_ingress

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
        self.setup_update_simple_policy(name="deny-all-ingress",
                            namespace= self.ns1.name,
                            policy_types = policy_types)
        #All ingress traffic to all pods of namespace "default" should be dropped.
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client1_pod_ns2.pod_ip)
    #end test_deny_all_ingress

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
        self.setup_update_simple_policy(name="ingress-pod-to-pod", 
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns1.labels)
        # All ingress traffic to pod cls.web_pod_ns1 will be dropped except from pod self.client1_pod_ns1.labels
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_ingress_podselector_for_pod

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
        self.setup_update_simple_policy(name="ingress-ns-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_namespaces= self.ns2.labels)
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
        self.setup_update_simple_policy(name="ingress-ipblock-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_ipblock= {"cidr" : ingress_allow_cidr,
                                                   "_except" : [deny_cidr]})
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
        self.setup_update_simple_policy(name="ingress-port-to-pod",
                                 pod_selector = self.web_pod_ns1.labels,
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name,
                                 ports=['TCP/80'],
                                 ingress_all =True)
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
        self.setup_update_simple_policy(name="ingress-pod-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns1.labels)
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
        self.setup_update_simple_policy(name="ingress-pod-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_pods= self.client1_pod_ns2.labels)
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
        self.setup_update_simple_policy(name="ingress-ns-to-ns", 
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_namespaces= self.ns2.labels)
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
        self.setup_update_simple_policy(name="ingress-ipblock-to-ns",
                                 policy_types = ["Ingress"],
                                 namespace= self.ns1.name, 
                                 ingress_ipblock= {"cidr" : ingress_allow_cidr,
                                                   "_except" : [deny_cidr]})
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
        self.setup_update_simple_policy(name="ingress-port-to-ns",
                                 policy_types = ["Ingress"],
                                 namespace= self.ns2.name,
                                 ports=['TCP/80'],
                                 ingress_all =True)
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
        assert self.self.validate_wget(self.client2_pod_ns2, url2)
        assert self.self.validate_wget(self.client1_pod_ns2, url2)
        assert self.self.validate_wget(self.client1_pod_ns2, url)
    #end test_ingress_rules_edit

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

    def test_allow_all_engress(self):
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
        self.setup_update_simple_policy(name="allow-all-egress",
                                 namespace= self.ns1.name,
                                egress_all =True)
        # All traffic should still work as it is ingress allow all policy
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip)
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_allow_all_engress

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
        self.setup_update_simple_policy(name="deny-all-egress",
                                 namespace= self.ns1.name,
                                policy_types = policy_types)
        #All egress traffic from all pods of namespace "default" should be dropped.
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client2_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                        expectation=False)
        #All ingress traffic from pods of namespace "non-default" should be allowed.
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns2.ping_with_certainty(self.client2_pod_ns1.pod_ip)
    #end test_deny_all_egress

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
        egress_allow_cidr = self.client1_pod_ns2.pod_ip + "/32"
        self.setup_update_simple_policy(name="egress-ipblock-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr})
        # Egress traffic should be allowed from self.client1_pod_ns1 to self.client1_pod_ns2 only.
        assert self.client1_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # No other egress traffic should be allowed from self.client1_pod_ns1 pod of namespace default
        assert self.client1_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                         expectation = False)
        assert self.client1_pod_ns1.ping_with_certainty(self.client2_pod_ns2.pod_ip,
                                                         expectation = False)
        #Egress traffic from other pods of namespace default should not be affected
        assert self.client2_pod_ns1.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns2.pod_ip)
        # Ingress traffic to self.client1_pod_ns1 should not be affected
        assert self.client1_pod_ns2.ping_with_certainty(self.client1_pod_ns1.pod_ip)
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1.pod_ip)
    #end test_egress_ipblock_for_pod

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
        self.setup_update_simple_policy(name="egress-ipblock-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name, 
                                 egress_ipblock= {"cidr" : egress_allow_cidr})
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
        self.setup_update_simple_policy(name="egress-ports-pod",
                                 pod_selector = self.client1_pod_ns1.labels,
                                 policy_types = ["Egress"],
                                 namespace= self.ns1.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
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
        self.setup_update_simple_policy(name="egress-ports-ns",
                                 policy_types = ["Egress"],
                                 namespace= self.ns2.name,
                                 egress_ports=['TCP/80'],
                                 egress_all =True)
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

    def test_policy_with_multiple_egress_rules(self):
        """
        Verify a network policy with multiple egress rules specified.
        Steps:
        1. Create a network policy with egress "to" rule mentioning "cidr" and "port"
        2. Verify the accessibility between pods as per the rule
        """
        # All traffic between everyone should work
        url = 'http://%s' % (self.web_pod_ns1.pod_ip)
        url2 = 'http://%s' % (self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns1, url2)
        # Enable all traffic to ns1
        policy_types = ["Egress"]
        egress_allow_cidr = self.web_pod_ns1.pod_ip + "/32"
        egress_list = [
            {'to': [{'ip_block': { "cidr" : egress_allow_cidr}}],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]}
        ]
        policy1 = self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                   name="many-selector-egress",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        # Pod client1_pod_ns2 can only reach pods mentioned in cidr 
        assert self.validate_wget(self.client1_pod_ns2, url2, expectation = False)
        assert self.validate_wget(self.client1_pod_ns2, url)
        # Only TCP egress is allowed from client1_pod_ns2 egress_allow_cidr
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
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
    
    def test_egress_rules_edit(self):
        """
        Verify that Contrail FW policies are updated on editing the k8s netwok poliy
        Steps:
        1. Create a netwok policy on one of the podSelector of namespace "non-default" with 
           egress from a particular cidr and ports.
        2. Verify that policy works as expected
        3. Update the netwok policy on same podSelector of namespace "non-default" with 
           updated cidr and updated ports.
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
        policy_types = ["Egress"]
        egress_allow_cidr = self.web_pod_ns1.pod_ip + "/32"
        egress_allow_cidr_2 = self.web_pod_ns2.pod_ip + "/32"
        egress_list = [
            {'to': [{'ip_block': { "cidr" : egress_allow_cidr}}],
             'egress_ports': [ 'TCP/80', 'UDP/53' ]}
        ]
        policy1 = self.setup_update_policy(pod_selector = self.client1_pod_ns2.labels,
                                   name="egress-rule-edit",
                                   namespace = self.ns2.name,
                                   policy_types = policy_types,
                                   egress= egress_list)
        
        # Pod client1_pod_ns2 can only reach pods mentioned in cidr 
        assert self.validate_wget(self.client1_pod_ns2, url2, expectation = False)
        assert self.validate_wget(self.client1_pod_ns2, url)
        # Only TCP egress is allowed from client1_pod_ns2 egress_allow_cidr
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation=False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip,
                                                        expectation=False)
        
        # Update the network policy
        egress_list = [
            {'to': [{'ip_block': { "cidr" : egress_allow_cidr_2}}]}
        ]
        self.setup_update_policy(update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_wget(self.client1_pod_ns2, url, expectation = False)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation = False)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
        
        # Update the network policy podselector
        self.setup_update_policy(pod_selector = self.client2_pod_ns2.labels,
                                update = True, 
                                np_fixture = policy1,
                                egress= egress_list)
        assert self.validate_wget(self.client2_pod_ns2, url, expectation = False)
        assert self.validate_wget(self.client2_pod_ns2, url2)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip,
                                                        expectation = False)
        assert self.client2_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
        assert self.validate_wget(self.client1_pod_ns2, url)
        assert self.validate_wget(self.client1_pod_ns2, url2)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns1.pod_ip)
        assert self.client1_pod_ns2.ping_with_certainty(self.web_pod_ns2.pod_ip)
    #end test_egress_rules_edit
    
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
        assert self.client2_pod_ns1.ping_with_certainty(self.client1_pod_ns1)
        
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
