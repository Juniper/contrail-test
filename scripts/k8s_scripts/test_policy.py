
from common.k8s.base import BaseK8sTest, _GenericTestBaseMethods
from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase


class TestNetworkPolicy(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicy, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicy, cls).tearDownClass()

    def setup_common_pods(self, namespace_fixture):
        web_label = 'web'
        client1_label = 'client1'
        client2_label = 'client2'
        web_pod = self.setup_nginx_pod(namespace=namespace_fixture.name,
                                       labels={'app': web_label})
        client1_pod = self.setup_busybox_pod(namespace=namespace_fixture.name,
                                             labels={'app': client1_label})
        client2_pod = self.setup_busybox_pod(namespace=namespace_fixture.name,
                                             labels={'app1': client2_label})

        assert web_pod.verify_on_setup()
        assert client1_pod.verify_on_setup()
        assert client2_pod.verify_on_setup()
        return (web_pod, client1_pod, client2_pod)
    # end setup_common_pods

    @preposttest_wrapper
    def test_network_policy_1(self):
        '''
            Create 2 pods with labels web, client1 and client2
            Enable namespace isolation
            HTTP get to web server pod should fail
            Create a network policy to allow traffic 'client1' pods to 'web'
                pods on tcp/80
            HTTP GET from client1 pod to web pod should work
            HTTP GET from client2 pod to web pod should fail
        '''
        namespace = self.setup_namespace()
        (web_pod, client1_pod, client2_pod) = self.setup_common_pods(
            namespace)

        url = 'http://%s' % (web_pod.pod_ip)
        assert self.do_wget(url, pod=client1_pod)

        self.setup_isolation(namespace)

        # traffic should fail
        assert self.validate_wget(client1_pod, url, expectation=False)
        assert self.validate_wget(client2_pod, url, expectation=False)

        # Now enable policy
        pod_selector = web_pod.labels
        policy = self.setup_simple_policy(pod_selector,
                                          ingress_pods=client1_pod.labels,
                                          namespace=namespace.name,
                                          ports=['TCP/80'])

        assert self.validate_wget(client1_pod, url)
        assert self.validate_wget(client2_pod, url, expectation=False)
        self.logger.info('Policy test requirement passed')

    # end test_network_policy_1

    @preposttest_wrapper
    def test_with_two_policies(self):
        '''
            Create 3 pods S1, C1, C2 with labels web, client1 and client2
            Create a network policy to allow traffic 'client1' pods to 'web'
                pods on TCP/80
            HTTP GET from only C1 to S1 should work
            Create a new network policy to allow traffic client1, client2 pods
                to web pods on TCP/80
            C1 to S1 and C2 to S1 should fail
            Update label of C2 to have both client1, client2
            C1 to S1 and C2 to S1 should pass
        '''
        namespace = self.setup_namespace('default')
        (web_pod, client1_pod, client2_pod) = self.setup_common_pods(
            namespace)

        url = 'http://%s' % (web_pod.pod_ip)
        self.setup_isolation(namespace)

        # Enable policy
        pod_selector = web_pod.labels
        policy = self.setup_simple_policy(pod_selector,
                                          ingress_pods=client1_pod.labels,
                                          ports=['TCP/80'])

        assert self.validate_wget(client1_pod, url)
        assert self.validate_wget(client2_pod, url, expectation=False)

        # Add another policy to include client2 label also
        labels = dict(client1_pod.labels.items() + client2_pod.labels.items())
        policy1 = self.setup_simple_policy(pod_selector,
                                           ingress_pods=labels,
                                           ports=['TCP/80']
                                           )

        assert self.validate_wget(client1_pod, url)
        assert self.validate_wget(client2_pod, url, expectation=False)
        client2_pod.set_labels(labels)
        assert self.validate_wget(client2_pod, url)
    # end test_with_two_policies

    @preposttest_wrapper
    def test_with_label_change(self):
        '''
            Create 2 pods with labels web, client1 and client2
            Create a network policy to allow traffic client1 pods to 'web'
                pods on TCP/80
            HTTP GET from client1 pod to web pod should work
            Update label of pod with client1 to client3
            HTTP GET from client3 pod to web pod should fail
            Update label of pod with client3 to client1
            HTTP GET from client3 pod to web pod should pass
        '''
        namespace = self.setup_namespace('default')
        (web_pod, client1_pod, client2_pod) = self.setup_common_pods(
            namespace)

        url = 'http://%s' % (web_pod.pod_ip)
        self.setup_isolation(namespace)

        # Enable policy
        policy1 = self.setup_simple_policy(pod_selector=web_pod.labels,
                                           ingress_pods=client1_pod.labels,
                                           ports=['TCP/80']
                                           )
        assert self.validate_wget(client1_pod, url)
        client1_pod.set_labels({'app': 'client3'})
        assert self.validate_wget(client1_pod, url, expectation=False)

        client1_pod.set_labels({'app': 'client1'})
        assert self.validate_wget(client1_pod, url)
    # end test_with_label_change

    @preposttest_wrapper
    def test_policy_with_namespace(self):
        '''
            Create a web-label pod S1 in namespace ns0
            Create a web-label pod S2 in namespace ns1
            Create client pod C1 in namespace ns1
            Create client pod C1 in namespace ns2
            Enable namespace isolation in ns0
            HTTP from C1 to S1 and C2 to S1 should fail
            HTTP from C1 to S2 and C2 to S2 should pass
            Create a network policy in ns0 to allow traffic from namespace ns1
                pods on tcp/80
            HTTP from C1 to S1 should pass
            HTTP from C2 to S1 should fail
        '''
        ns0 = self.setup_namespace()
        ns1 = self.setup_namespace()
        ns2 = self.setup_namespace()
        self.sleep(2)
        s1 = self.setup_nginx_pod(namespace=ns0.name)
        s2 = self.setup_nginx_pod(namespace=ns1.name)
        c1 = self.setup_busybox_pod(namespace=ns1.name)
        c2 = self.setup_busybox_pod(namespace=ns2.name)
        for i in (s1, s2, c1, c2):
            assert i.verify_on_setup()

        s1_url = 'http://%s' % (s1.pod_ip)
        s2_url = 'http://%s' % (s2.pod_ip)
        assert self.do_wget(s1_url, pod=c1)
        assert self.do_wget(s1_url,pod=c2)

        self.setup_isolation(ns0)
        assert self.validate_wget(c1, s1_url, expectation=False)
        assert self.validate_wget(c2, s1_url, expectation=False)
        assert self.validate_wget(c2, s2_url)

        policy = self.setup_simple_policy(
            namespace=ns0.name,
            ingress_namespaces={'project': ns1.name},
            ports=['TCP/80'])
        # traffic should fail
        ns1.set_labels({'project': ns1.name})
        assert self.validate_wget(c1, s1_url)
        assert self.validate_wget(c2, s1_url, expectation=False)
        ns2.set_labels({'project': ns1.name})
        assert self.validate_wget(c2, s1_url)
        assert self.validate_wget(c2, s2_url)

        self.logger.info('Policy test with namespace labels passed')
    # end test_policy_with_namespace

    @preposttest_wrapper
    def test_with_no_pod_selector_and_ports(self):
        '''
        Enable namespace isolation
        Validate that an empty pod_selector matches all pods
        An empty ingress list should not have any effect on the traffic,i.e.
            all traffic should be dropped

        If ports list is not configured, all traffic should match the policy
        If ports list is empty, no traffic should match the policy
        '''
        ns1 = self.setup_namespace()
        ns2 = self.setup_namespace()
        self.setup_isolation(ns1)
        (ns1_s1, ns1_c1, ns1_c2) = self.setup_common_pods(ns1)
        (ns2_s1, ns2_c1, ns2_c2) = self.setup_common_pods(ns2)

        s1_url = 'http://%s' % (ns1_s1.pod_ip)

        # Enable policy with empty pod selector
        policy1 = self.setup_simple_policy(pod_selector=None,
                                           namespace=ns1.name,
                                           ingress_pods=ns1_c1.labels,
                                           ports=['TCP/80']
                                           )
        # tcp/80 Traffic for all pods in ns1 should work
        assert self.validate_wget(ns1_c1, s1_url)
        assert self.validate_wget(ns1_c2, s1_url, expectation=False)
        assert self.validate_wget(ns2_c1, s1_url, expectation=False)
        assert ns1_c1.ping_with_certainty(ns1_s1.pod_ip, expectation=False)

        self.logger.info(
            'Empty pod_selector matched all pods in namespace..OK')
        assert self.validate_wget(ns2_c1, s1_url, expectation=False)
        self.perform_cleanup(policy1)

        # No ports list : should match all traffic
        policy2 = self.setup_simple_policy(pod_selector=ns1_s1.labels,
                                           namespace=ns1.name,
                                           ingress_pods=ns1_c1.labels,
                                           )
        assert self.validate_wget(ns1_c1, s1_url)
        assert ns1_c1.ping_with_certainty(ns1_s1.pod_ip)
        assert self.validate_wget(ns1_c2, s1_url, expectation=False)
        self.perform_cleanup(policy2)

        # Empty ports list : should match all traffic
        # see https://github.com/kubernetes/kubernetes/issues/22469
        # "Both ports: [] and omitting ports mean the same thing, which is
        #    that all ports are selected"
        policy3 = self.setup_simple_policy(pod_selector=ns1_s1.labels,
                                           namespace=ns1.name,
                                           ingress_pods=ns1_c1.labels,
                                           ports=[],
                                           )
        assert self.validate_wget(ns1_c1, s1_url)
        assert ns1_c1.ping_with_certainty(ns1_s1.pod_ip)

        self.perform_cleanup(policy3)
    # end test_with_no_pod_selector_and_ports

    @preposttest_wrapper
    def test_with_no_ingress_rule_selectors(self):
        '''
        In ingress section, if pod_selector is empty, all pods in the ns should
        match

        In ingress section, if namespace_selector is empty, all pods in all
        namespaces should match
        '''
        ns1 = self.setup_namespace()
        ns2 = self.setup_namespace()
        self.setup_isolation(ns1)
        (ns1_s1, ns1_c1, ns1_c2) = self.setup_common_pods(ns1)
        (ns2_s1, ns2_c1, ns2_c2) = self.setup_common_pods(ns2)

        ns1_s1_url = 'http://%s' % (ns1_s1.pod_ip)
        ns2_s1_url = 'http://%s' % (ns2_s1.pod_ip)

        # Enable policy with empty ingress pod selector
        policy1 = self.setup_simple_policy(pod_selector=ns1_s1.labels,
                                           namespace=ns1.name,
                                           ingress_pods={},
                                           ports=['TCP/80']
                                           )
        # tcp/80 Traffic for all pods in ns1 should work
        assert self.validate_wget(ns1_c1, ns1_s1_url)
        assert self.validate_wget(ns1_c2, ns1_s1_url)
        assert self.validate_wget(ns2_c1, ns1_s1_url, expectation=False)
        assert ns1_c1.ping_with_certainty(ns1_s1.pod_ip, expectation=False)
        assert ns1_c1.ping_with_certainty(ns1_c2.pod_ip, expectation=False)
        self.logger.info('Empty ingress pod_selector check passed')
        self.perform_cleanup(policy1)

        # Enable policy with empty ingress namespace selector
        policy2 = self.setup_simple_policy(pod_selector=ns1_s1.labels,
                                           namespace=ns1.name,
                                           ingress_namespaces={},
                                           ports=['TCP/80']
                                           )
        # tcp/80 Traffic for all pods in ns1 should work
        assert self.validate_wget(ns1_c1, ns1_s1_url)
        assert self.validate_wget(ns1_c2, ns1_s1_url)
        assert self.validate_wget(ns2_c1, ns1_s1_url)
        assert ns1_c1.ping_with_certainty(ns1_c2.pod_ip, expectation=False)
        self.logger.info('Empty ingress namespace_selector check passed')
    # end test_with_no_ingress_rule_selectors

    @preposttest_wrapper
    def test_all_access_between_two_namespaces(self):
        '''
        Have two namespaces ns1, ns2
        Enable defaultdeny on ns1
        Apply policy to allow all traffic to pods on ns1 and check with traffic
          from ns2
        Apply policy to allow all traffic to pods on ns2 and check with traffic
          from ns1
        '''
        ns1 = self.setup_namespace()
        ns2 = self.setup_namespace()
        self.setup_isolation(ns1)
        ns2.set_labels({'project': ns2.name})
        (ns1_s1, ns1_c1, ns1_c2) = self.setup_common_pods(ns1)
        (ns2_s1, ns2_c1, ns2_c2) = self.setup_common_pods(ns2)

        ns1_s1_url = 'http://%s' % (ns1_s1.pod_ip)
        ns2_s1_url = 'http://%s' % (ns2_s1.pod_ip)

        # Enable all traffic to ns1
        policy1 = self.setup_simple_policy(pod_selector=None,
                                           namespace=ns1.name,
                                           ingress_namespaces={},
                                           ports=None,
                                           )
        # All Traffic from pods in ns2 to pods in ns1 should work
        assert self.validate_wget(ns1_c1, ns1_s1_url)
        assert self.validate_wget(ns1_c2, ns1_s1_url)
        assert self.validate_wget(ns2_c1, ns1_s1_url)
        assert ns2_c1.ping_with_certainty(ns1_c2.pod_ip)
        assert ns2_c2.ping_with_certainty(ns1_c2.pod_ip)
        self.logger.info('Policy to allow all traffic from ns2 to ns1 is fine')

        # All Traffic from pods in ns1 to pods in ns2 should anyway work
        assert self.validate_wget(ns1_c1, ns2_s1_url)
        assert self.validate_wget(ns1_c2, ns2_s1_url)
        assert self.validate_wget(ns1_c1, ns2_s1_url)
        assert ns1_c1.ping_with_certainty(ns2_c2.pod_ip)
        assert ns1_c2.ping_with_certainty(ns2_c1.pod_ip)
        self.logger.info('Pods from policy-enabled ns can reach a non-policy'
                         ' enabled ns')

        self.setup_isolation(ns2)
        # All Traffic from pods in ns1 to pods in ns2 should fail
        assert self.validate_wget(ns1_c1, ns2_s1_url, expectation=False)
        assert self.validate_wget(ns1_c2, ns2_s1_url, expectation=False)
        assert self.validate_wget(ns1_c1, ns2_s1_url, expectation=False)
        assert ns1_c1.ping_with_certainty(ns2_c2.pod_ip, expectation=False)
        assert ns1_c2.ping_with_certainty(ns2_c1.pod_ip,  expectation=False)
        self.logger.info('Policy to disallow all traffic to ns2 is working OK')

        # Allow all traffic to ns2
        policy2 = self.setup_simple_policy(pod_selector=None,
                                           namespace=ns2.name,
                                           ingress_namespaces={},
                                           ports=None,
                                           )
        # All Traffic from pods in ns1 to pods in ns2 should work
        assert self.validate_wget(ns1_c1, ns2_s1_url)
        assert self.validate_wget(ns1_c2, ns2_s1_url)
        assert self.validate_wget(ns1_c1, ns2_s1_url)
        assert ns1_c1.ping_with_certainty(ns2_c2.pod_ip)
        assert ns1_c2.ping_with_certainty(ns2_c1.pod_ip)
        self.logger.info('Pods from policy-enabled ns can reach a policy'
                         ' enabled ns')
    # end test_with_no_ingress_rule_selectors

    @preposttest_wrapper
    def test_multiple_from_rules(self):
        '''
        Have two namespaces ns1, ns2
        Apply policy on ns1 with one rule to allow traffic from client1 pod
        in ns1 and another rule to allow all from ns2
        Validate both the rules work

        '''
        ns1 = self.setup_namespace()
        ns2 = self.setup_namespace()
        self.setup_isolation(ns1)
        ns2.set_labels({'project': ns2.name})
        (ns1_s1, ns1_c1, ns1_c2) = self.setup_common_pods(ns1)
        (ns2_s1, ns2_c1, ns2_c2) = self.setup_common_pods(ns2)

        ns1_s1_url = 'http://%s' % (ns1_s1.pod_ip)
        ns2_s1_url = 'http://%s' % (ns2_s1.pod_ip)

        # Enable all traffic to ns1
        ingress_list = [
            {'from': [
                {'pod_selector': ns1_c1.labels},
            ],
                'ports': ['TCP/80'],
            },
            {'from': [
                {'namespace_selector': ns2.labels},
            ],
            }
        ]

        policy1 = self.setup_policy(pod_selector=ns1_s1.labels,
                                    namespace=ns1.name,
                                    ingress=ingress_list)

        assert self.validate_wget(ns1_c1, ns1_s1_url)
        assert ns1_c1.ping_with_certainty(ns1_s1.pod_ip, expectation=False)
        assert self.validate_wget(ns1_c2, ns1_s1_url, expectation=False)

        assert self.validate_wget(ns2_c1, ns1_s1_url)
        assert self.validate_wget(ns2_c2, ns1_s1_url)
        assert ns2_c1.ping_with_certainty(ns1_c1.pod_ip, expectation=False)
        assert ns2_c2.ping_with_certainty(ns1_s1.pod_ip, expectation=True)
    # end
