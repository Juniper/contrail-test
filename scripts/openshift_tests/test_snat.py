from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name
import test
import time

class TestSNAT(BaseK8sTest):
    @classmethod
    def setUpClass(cls):
        super(TestSNAT, cls).setUpClass()
        cls.ip_to_ping = cls.inputs.cfgm_control_ips[0]

    @classmethod
    def tearDownClass(cls):
        super(TestSNAT, cls).tearDownClass()

    def setup_namespaces_pods_for_snat_test(self, isolation=False ,ip_fabric_snat=False):
        """ common routine to create the namesapces and the pods  by enabling snat
            1.create 2 namespaces (ns1,ns2 enable snat )
            2.create pods in each namespace and verify(ns1:pod1,pod2(c1,c2), ns2:pod1,default:pod1)
        """
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = isolation,
                                          ip_fabric_snat=ip_fabric_snat)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = isolation,
                                          ip_fabric_snat=ip_fabric_snat)
        #verifying namespaces have been created
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        label = "snat"
        #create a pod in default namespaces
        pod1_in_default_ns = self.setup_ubuntuapp_pod()
        #create a two pods in snat enabled namespace
        #pod1 with one container and pod2 with two containers
        pod1_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name,
                                               labels={'app': label})
        spec =  {
                'containers': [
                    {'image': 'ubuntu-upstart',
                      "name": "c1",
                      'command': ['sleep', '1000000'],
                      'image_pull_policy': 'IfNotPresent'
                    },
                    {'image': 'ubuntu-upstart',
                     "name": "c2",
                     'command': ['sleep', '1000000'],
                     'image_pull_policy': 'IfNotPresent'
                    }
              ]
        }
        pod2_in_ns1 = self.setup_pod(namespace=namespace1_name,
                                               spec=spec,
                                               labels={'app': label})
        #create pod 3 without associating any label
        pod3_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name)
        #create a pod in snat forwarding enabled namespace
        pod1_in_ns2 = self.setup_ubuntuapp_pod(namespace=namespace2_name,
                                               labels={'app': label})
        assert pod1_in_default_ns.verify_on_setup()
        assert pod1_in_ns1.verify_on_setup()
        assert pod2_in_ns1.verify_on_setup()
        assert pod3_in_ns1.verify_on_setup()
        assert pod1_in_ns2.verify_on_setup()
        client1 = [pod1_in_ns1, pod2_in_ns1, pod3_in_ns1, namespace1]
        client2 = [pod1_in_ns2, namespace2]
        client3 = [pod1_in_default_ns]
        return (client1, client2, client3)
    #end setup_namespaces_pods_for_snat_test

    @preposttest_wrapper
    def test_isolated_pod_external_reachability_with_snat_enabled(self):
        """
        Verify the pods reachability to public network when ip snat forwarding is enables
           1.create 2 isolated namespaces with snat forwarding enabled
           2.create pods in thos namespaces(ns1:pod1,pod2(c1,c2), ns2:pod1 ,default:pod1)
           3.ping ns1:pod1 to public host dns should PASS
           4.ping from ns1:pod2:c1 and ns1:pod2:c2 to the public dns should PASS
           5.ping from ns1:pod1 to ns2:pod1 should FAIL
           6.ping from ns1:pod1 to dafeult:pod1 should FAIL
           7.ping public_host_url DNS verification from user-defined namespace
        """
        # Setup Pods
        client1, client2, client3 = self.setup_namespaces_pods_for_snat_test(isolation=True, ip_fabric_snat=True)

        # Setup additional busy box pod with nslookup utility to verify dns
        namespace4_name = get_random_name("ns4")
        namespace4 = self.setup_namespace(name = namespace4_name, isolation=True, ip_fabric_snat=True)
        assert namespace4.verify_on_setup()
        client4 = self.setup_busybox_pod(namespace=namespace4_name)
        assert client4.verify_on_setup()

        # Verify Reachability
        assert client1[0].ping_to_ip(self.inputs.public_host)
        assert client1[1].ping_to_ip(self.inputs.public_host,container="c1")
        assert client1[1].ping_to_ip(self.inputs.public_host,container="c2")
        assert client2[0].ping_to_ip(self.inputs.public_host)
        assert client1[0].ping_to_ip(client1[2].pod_ip)
        assert client1[0].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[0].ping_to_ip(client3[0].pod_ip, expectation=False)
        lookup_str = "nslookup %s" % (self.inputs.public_host_url)
        output = client4.run_cmd(lookup_str)
        msg = 'DNS resolution failed'
        assert 'nslookup: can\'t resolve' not in output, msg
        self.logger.info('DNS resolution check : %s passed. Output: %s' % (lookup_str, output))

    #end test_pod_publicreachability_with_snat_enabled

    @preposttest_wrapper
    def test_non_isolated_pod_external_reachability_with_snat_enabled(self):
        """
        Verify the pods reachability to public network when ip snat forwarding is enables
           1.create 2 non isolated namespaces with snat forwarding enabled
           2.create pods in those namespaces(ns1:pod1,pod2(c1,c2), ns2:pod1 ,default:pod1)
           3.ping ns1:pod1 to public host dns should PASS
           4.ping from ns1:pod2:c1 and ns1:pod2:c2 to the public dns should PASS
           5.ping from ns1:pod1 to ns2:pod1 should FAIL
           6.ping from ns1:pod1 to dafeult:pod1 should FAIL
           7.ping public_host_url DNS verification from user-defined namespace
        """
        # Setup Pods
        client1, client2, client3 = self.setup_namespaces_pods_for_snat_test(isolation=False, ip_fabric_snat=True)

        # Setup additional busy box pod with nslookup utility to verify dns
        namespace4_name = get_random_name("ns4")
        namespace4 = self.setup_namespace(name = namespace4_name, isolation=False, ip_fabric_snat=True)
        assert namespace4.verify_on_setup()
        client4 = self.setup_busybox_pod(namespace=namespace4_name)
        assert client4.verify_on_setup()

        # Verify Reachability
        assert client1[0].ping_to_ip(self.inputs.public_host)
        assert client1[1].ping_to_ip(self.inputs.public_host,container="c1")
        assert client1[1].ping_to_ip(self.inputs.public_host,container="c2")
        assert client2[0].ping_to_ip(self.inputs.public_host)
        assert client1[0].ping_to_ip(client1[2].pod_ip)
        assert client1[0].ping_to_ip(client2[0].pod_ip)
        assert client1[0].ping_to_ip(client3[0].pod_ip)
        lookup_str = "nslookup %s" % (self.inputs.public_host_url)
        output = client4.run_cmd(lookup_str)
        msg = 'DNS resolution failed'
        assert 'nslookup: can\'t resolve' not in output, msg
        self.logger.info('DNS resolution check : %s passed. Output: %s' % (lookup_str, output))

    #end test_pod_publicreachability_with_snat_enabled
