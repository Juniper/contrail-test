from builtins import range
from common.k8s.base import BaseK8sTest
from k8s.pod import PodFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.util import skip_because
import test

class TestKubeManagerHA(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestKubeManagerHA, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestKubeManagerHA, cls).tearDownClass()

    def is_test_applicable(self):
        if len(self.inputs.cfgm_ips) < 3 or \
                len(self.inputs.kube_manager_ips) < 3:
            return (False, 'Skipping tests since controller/KM has less than 3 '
                    'nodes')
        else:
            return (True, None)
    # end is_test_applicable

    def setup_my_pods(self, pods_per_compute=None):
        pods_per_compute = pods_per_compute or 5
        n = pods_per_compute * len(self.inputs.compute_ips)
        pods = []
        for i in range(0, n):
            pods.append(self.setup_busybox_pod(name='pod-%s' % (i)))
        return pods
        # end setup_my_pods

    def delete_pods(self, pods):
        for pod in pods:
            pod.delete_only()
            self.remove_from_cleanups(pod.cleanUp)
        # end delete_pods

    def verify_pods_are_not_in_k8s(self, pods):
        for pod in pods:
            assert pod.verify_pod_is_not_in_k8s(), 'Pods still in k8s'
        # end verify_pods_are_not_in_k8s

    def verify_pods_are_deleted(self, pods):
        for pod in pods:
            assert pod.verify_on_cleanup(), 'Pod-delete verification fails'
    # end verify_pods_are_deleted

    def verify_pods(self, pods):
        for pod in pods:
            assert pod.verify_on_setup(), 'Pod verification failed'
    # end verify_pods

    def verify_mesh_ping(self, pods):
        # Do a mesh ping
        n = len(pods)
        for i in range(0, n):
            for j in range(0, n):
                if i == j:
                    continue
                assert pods[i].ping_with_certainty(pods[j].pod_ip)
        return True
        # end verify_mesh_ping

    def get_active_backup_kms(self, refresh=False):
        km_h = self.connections.get_kube_manager_h(refresh=refresh)
        all_kms = self.inputs.kube_manager_ips[:]
        active_km = km_h.ip
        backup_kms = [x for x in all_kms if x != active_km]
        return (active_km, backup_kms)
    # end get_active_backup_kms

    @preposttest_wrapper
    def test_single_node_failover(self):
        '''
        Stop all contrail containers contrail-kube-manager, controller,
        analytics, analyticsdb on one of the HA-enabled controller nodes
        Validate that a new kube-manager from among the other nodes is active
        We should be able to delete and add pods during this time and the pods
        should get their IPs

        '''
        css = ContrailStatusChecker(self.inputs)
        containers = ['contrail-kube-manager', 'api-server', 'schema'
                      'analyticsdb', 'analytics-api', 'collector']
        km_h = self.connections.get_kube_manager_h()
        node = km_h.ip
        # Setup pods
        pods = self.setup_my_pods(2)
        self.verify_pods(pods)

        self.stop_containers(node, containers, wait=2)
        self.delete_pods(pods)
        self.verify_pods_are_not_in_k8s(pods)

        # Setup pods again now
        pods = self.setup_my_pods(2)
        assert css.wait_till_contrail_cluster_stable()[0]
        self.verify_pods(pods)
        self.verify_mesh_ping(pods)
        # Delete the pods now and verify cleanup
        self.delete_pods(pods)
        self.verify_pods_are_deleted(pods)

    # end test_single_node_failover

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_km_active_backup(self):
        '''
        Create a pod A
        Restart an active km, check one of the others becomes active
        Create another pod B. Check B can reach A
        Restart the active km, check one of the others becomes active
        Create another pod C. Check C can reach A, B
        Restart the active km again, check one of the others becomes active
        Create another pod D. Check D can reach A, B, C
        '''
        css = ContrailStatusChecker(self.inputs)
        pod1 = self.setup_busybox_pod()
        assert pod1.wait_till_pod_is_up()

        (active_km, backup_kms) = self.get_active_backup_kms(refresh=True)
        self.restart_kube_manager([active_km])
        css.wait_till_contrail_cluster_stable(nodes=[active_km])
        (active_km_1, backup_kms_1) = self.get_active_backup_kms(refresh=True)
        assert active_km_1 in backup_kms, 'New KM was not chosen as active'
        pod2 = self.setup_busybox_pod()
        assert pod2.wait_till_pod_is_up()
        assert self.verify_reachability(pod2, [pod1])

        self.restart_kube_manager([active_km_1])
        css.wait_till_contrail_cluster_stable(nodes=[active_km])
        (active_km_2, backup_kms_2) = self.get_active_backup_kms(refresh=True)
        assert active_km_2 in backup_kms_1, 'New KM was not chosen as active'
        pod3 = self.setup_busybox_pod()
        assert pod3.wait_till_pod_is_up()
        assert self.verify_reachability(pod3, [pod1, pod2])

        self.restart_kube_manager([active_km_2])
        css.wait_till_contrail_cluster_stable(nodes=[active_km])
        (active_km_3, backup_kms_3) = self.get_active_backup_kms(refresh=True)
        assert active_km_3 in backup_kms_2, 'New KM was not chosen as active'
        pod4 = self.setup_busybox_pod()
        assert pod4.wait_till_pod_is_up()
        assert self.verify_reachability(pod4, [pod1, pod2, pod3])
        # end test_km_active_backup
