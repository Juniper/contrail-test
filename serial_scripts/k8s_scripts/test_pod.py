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
