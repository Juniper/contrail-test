from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name, skip_because
import test
import time

class TestSNAT(BaseK8sTest):
    
    @classmethod
    def setUpClass(cls):
        super(TestSNAT, cls).setUpClass()
        if cls.inputs.slave_orchestrator == 'kubernetes':
            cls.ip_to_ping = cls.inputs.k8s_clusters[0]['master_ip']
        else:
            cls.ip_to_ping = cls.inputs.bgp_control_ips[0]

    @classmethod
    def tearDownClass(cls):
        super(TestSNAT, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
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
    def test_pod_publicreachability_with_snat_enabled(self):
        """
        Verify the pods reachability to public network when ip snat forwarding is enables
           1.create 2 isolated namespaces with snat forwarding enabled
           2.create pods in thos namespaces(ns1:pod1,pod2(c1,c2), ns2:pod1 ,default:pod1)
           3.ping ns1:pod1 to public host dns should PASS
           4.ping from ns1:pod2:c1 and ns1:pod2:c2 to the public dns should PASS
           5.ping from ns1:pod1 to ns2:pod1 should FAIL
           6.ping from ns1:pod1 to dafeult:pod1 should FAIL
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_snat_test(isolation=True,
                                                                            ip_fabric_snat=True)
        assert client1[0].ping_to_ip(self.ip_to_ping)
        assert client1[1].ping_to_ip(self.ip_to_ping,container="c1")
        assert client1[1].ping_to_ip(self.ip_to_ping,container="c2")
        assert client2[0].ping_to_ip(self.ip_to_ping)
        assert client1[0].ping_to_ip(client1[2].pod_ip)
        assert client1[0].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[0].ping_to_ip(client3[0].pod_ip, expectation=False)
    #end test_pod_publicreachability_with_snat_enabled

    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_snat_forwarding_disabled_by_default(self):
        """
        IP Fabric Forwaring is disabled by default
           1.create an isolated namespace with out ip snat forwarding enabled and verify
           2.create a pod in the namespace created in step 1 and verify
           3.public reachability should fail
           4.delete the pod and namespace created in step1 and step2
           5.recreate the namespace with snat enabled
           6.create a pod in the namespace created in step 5
           7.now verifu the public reachability ,should PASS
        """
        namespace1_name = "ns1"
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=True)
        assert namespace1.verify_on_setup()
        pod1_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name)
        assert pod1_in_ns1.verify_on_setup()
        assert pod1_in_ns1.ping_to_ip(self.ip_to_ping, expectation=False)
        self.perform_cleanup(pod1_in_ns1)
        self.perform_cleanup(namespace1)
        #recreate the same namespace with ip fabric snat enabled this time
        time.sleep(5)
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=True,
                                                              ip_fabric_snat=True)
        pod1_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name)
        assert pod1_in_ns1.verify_on_setup()
        assert pod1_in_ns1.ping_to_ip(self.ip_to_ping)
    #end test_snat_forwarding_disabled_by_default
    
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_ping_with_jumbo_frame(self):
        """
        IP Fabric Forwaring should support  jumbo frames
            1.create 2 isolated namespaces with snatforwarding enabled
            2.create pods in thos namespaces(ns1:pod1,pod2(c1,c2), ns2:pod1 ,default:pod1)
            3.ping ns1:pod1 to public host dns should PASS with jumbo frame
            4.ping from ns1:pod2:c1 and ns1:pod2:c2 to the public dns should PASS with jumbo frame
            5.ping from ns1:pod1 to ns2:pod1 should FAIL with jumbo frame
            6.ping from ns1:pod1 to dafeult:pod1 should FAIL with jumbo frame
        """
        jumbo_frame_size="4000"
        client1, client2, client3 = self.setup_namespaces_pods_for_snat_test(isolation=True,
                                                                             ip_fabric_snat=True)
        #TODO ping with jumbo frames fails to the outside of juniper network
        assert client1[0].ping_to_ip(self.ip_to_ping, jumboframe=jumbo_frame_size)
        assert client1[0].ping_to_ip(client2[0].pod_ip, jumboframe=jumbo_frame_size,
                                     expectation=False,)
        #assert client1[1].ping_to_ip(client1[0],jumboframe=jumbo_frame_size, container="c1")
        assert client1[1].ping_to_ip(self.ip_to_ping,jumboframe=jumbo_frame_size,
                                     container="c2")
        assert client1[0].ping_to_ip(client3[0].pod_ip, jumboframe=jumbo_frame_size,
                                     expectation=False)
    #end test_ping_with_jumbo_frame

    @preposttest_wrapper
    def test_delete_and_recreate_the_namespace_with_snat_enabled(self):
        """
        Verify deletion and recreation of namespace works fien with  snatenable
            1.create a namespace with ip fabric snnat enabled
            2.create a pod in the namespace created in step1
            3.verify the pubilc reahcability from the pod
            4.delete the namespace and pod
            5.recreate the same namespce names with ip snat enabled
            6.create the pod
            7.verify the pubilc reahcbility
        """
        namespace1_name = "test"
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=True, ip_fabric_snat=True)
        assert namespace1.verify_on_setup()
        pod1 = self.setup_busybox_pod(namespace=namespace1_name)
        assert pod1.verify_on_setup()
        assert pod1.ping_to_ip(self.ip_to_ping)
        self.perform_cleanup(pod1)
        self.perform_cleanup(namespace1)
        time.sleep(5)
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=True, ip_fabric_snat=True)
        assert namespace1.verify_on_setup()
        pod1 = self.setup_busybox_pod(namespace=namespace1_name)
        assert pod1.verify_on_setup()
        assert pod1.ping_to_ip(self.ip_to_ping)

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_deployment_with_replica_update_for_snat(self):
        '''
        Verifies snat forwarding is enabled though deployment object
            1.Create a deployment with n replicas with snat enabled
            2.verify the replicas able to reach the public network
            3.update the pod  replicas
            4.should be able to reach pubic network from each pod
        '''
        labels = {'app': 'test'}
        replicas = len(self.inputs.compute_ips)*1
        new_replicas = len(self.inputs.compute_ips)*2

        namespace1_name = get_random_name("ns1")
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=True,
                                         ip_fabric_snat=True)
        assert namespace1.verify_on_setup()
        metadata = {}
        spec = {}
        name =  get_random_name('ubuntu-dep')
        template_metadata = {}

        template_metadata['labels'] = labels
        template_spec = {
                'containers': [
                    {'image': 'ubuntu-upstart',
                      "name": "c1",
                      'command': ['sleep', '1000000'],
                      'image_pull_policy': 'IfNotPresent',
                    }
              ]
        }
        spec.update({
            'replicas': replicas,
            'template': {
                'metadata': template_metadata,
                'spec': template_spec
            }
        })
        dep_1 =  self.setup_deployment(name=name, namespace=namespace1_name,
                                     metadata=metadata, spec=spec)
        assert dep_1.verify_on_setup()
        s_pod_fixtures = []
        server_pods = dep_1.get_pods_list()
        for x in server_pods:
            s_pod_fixture = self.setup_ubuntuapp_pod(name=x.metadata.name,
                                                  namespace=namespace1_name)
            s_pod_fixture.verify_on_setup()
            assert s_pod_fixture.ping_to_ip(self.ip_to_ping)

        dep_1.set_replicas(new_replicas)
        assert dep_1.verify_on_setup()
        s_pod_fixtures = []
        server_pods = dep_1.get_pods_list()
        for x in server_pods:
            s_pod_fixture = self.setup_ubuntuapp_pod(name=x.metadata.name,
                                                  namespace=namespace1_name)
            assert s_pod_fixture.verify_on_setup()
            assert s_pod_fixture.ping_to_ip(self.ip_to_ping)
        #end test_deployment_with_replica_update_snat

