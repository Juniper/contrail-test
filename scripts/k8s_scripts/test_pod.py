from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import skip_because

class TestPod(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestPod, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPod, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_add_delete_pod(self):
        '''
        Test add and delete of  POD
        '''
        pod = self.setup_nginx_pod()
        assert pod.verify_on_setup()
    # end test_add_delete_pod

    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
    @preposttest_wrapper
    def test_ping_between_two_pods(self):
        '''
        Test ping between 2 PODs
        '''
        pod1 = self.setup_busybox_pod()
        assert pod1.verify_on_setup()
        pod2 = self.setup_busybox_pod()
        assert pod2.verify_on_setup()
        assert pod1.ping_with_certainty(pod2.pod_ip)
    # end test_ping_between_two_pods

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_ping_between_pods_accross_namespace(self):
        '''
        Test ping between 2 PODs created in 2 different namespace 
        Ping should pass in default mode
        Ping should fail when namespace isolation enabled 
        '''
        expectation = True
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        if self.setup_namespace_isolation:
            expectation = False
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=expectation)
    # end test_ping_between_pods_accross_namespace

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_change_pod_label(self):
        '''
        Change the label of POD
        '''
        app = 'healthy'
        pod1 = self.setup_busybox_pod(labels={'app': app})
        assert pod1.verify_on_setup()
        pod2 = self.setup_busybox_pod(labels={'app': app})
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip)
        pod1.set_labels({"app": "unhealthy"})
        assert pod1.ping_to_ip(pod2.pod_ip)

    # end test_change_pod_label
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_pod_public_reachability_using_snat(self):
        '''
        Test pod can reach public network using snat
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_ubuntuapp_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        self.configure_snat_for_pod(pod=pod1)
        self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
        assert pod1.ping_with_certainty(self.inputs.public_host)
    # end test_pod_public_reachability_using_snat

# Isolated namespace classes follow

class TestPodVNIsolated(TestPod):

    @classmethod
    def setUpClass(cls):
        super(TestPod, cls).setUpClass()
        cls.setup_namespace_isolation = True
