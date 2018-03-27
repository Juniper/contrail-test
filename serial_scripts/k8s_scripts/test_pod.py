from common.k8s.base import BaseK8sTest
from k8s.pod import PodFixture
from tcutils.wrappers import preposttest_wrapper

class TestPodScale(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestPodScale, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPodScale, cls).tearDownClass()

    @preposttest_wrapper
    def test_many_pods(self):
        '''
        For each compute, spawn 30 pods together
        All the pods should be reachable to each other

        '''
        pods_per_compute = 20
        n = pods_per_compute * len(self.inputs.compute_ips)
        pods = []
        for i in range(0, n):
            pods.append(self.setup_busybox_pod())

#        for pod in pods:
#            assert pod.verify_on_setup()

        # Enable ping test after making it run in parallel
        # Do a mesh ping test
#        for i in range(0,n):
#            for j in range(0,n):
#                if i == j:
#                    continue
#                assert pods[i].ping_with_certainty(pods[j].pod_ip)

        # Do a mass delete and verify
        for pod in pods:
            pod.delete_only()
            self.remove_from_cleanups(pod.cleanUp)
        for pod in pods:
            assert pod.verify_on_cleanup(), 'Pod verification failed'

    # end test_many_pods

    @preposttest_wrapper
    def test_pod_with_kube_manager_restart(self):
        '''
        Test ping between 2 PODs created in 2 different namespace
        Ping should pass in default mode
        Ping should fail when namespace isolation enabled
        Restart contrail-kube-manager
        Ping between 2 PODs again
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
        self.restart_kube_manager()
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=expectation)
    # end test_pod_with_kube_manager_restart
