from builtins import range
from common.k8s.base import BaseK8sTest
from k8s.pod import PodFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
import test
import time
import socket
from tcutils.contrail_status_check import ContrailStatusChecker

class TestPodScale(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestPodScale, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPodScale, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
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

    @test.attr(type=['openshift_1'])
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

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_node_reboot_openshiftcontroller(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Reboot Openshift Controller
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        os_node = self.inputs.k8s_master_ip
        # Reboot the node
        self.inputs.reboot(os_node)
        time.sleep(70)
        # Verify after reboot
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
    # end test_pod_with_node_reboot_openshiftcontroller

    @skip_because(slave_orchestrator='kubernetes')
    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_node_reboot_compute(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Reboot Compute
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        compute_node = pod1.nodename
        # Reboot the node
        self.inputs.reboot(compute_node)
        #time.sleep(70)
        # Verify after reboot
        status, svcs = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable(compute_node, refresh=True)
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True)
    # end test_pod_with_node_reboot_compute

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_node_reboot_contrailcontroller(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Reboot Contrail Controller (This test only for HA setup with event on non-test container node)
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        # Avoid rebooting test-container node
        if socket.gethostbyaddr(self.inputs.cfgm_ips[0])[1][0] != socket.gethostname():
           control_node = self.inputs.cfgm_ips[0]
        else:
           control_node = self.inputs.cfgm_ips[1]
        # Reboot the node
        self.inputs.reboot(control_node)
        time.sleep(70)
        # Verify after reboot
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
    # end test_pod_with_node_reboot_contrailcontroller

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_oc_master_restart_controllers(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Restart Controllers
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        os_node = self.inputs.k8s_master_ip

        output = self.inputs.run_cmd_on_server(os_node, '/usr/local/bin/master-restart controllers')
        assert output == '2',  'master-restart controllers failed'
        time.sleep(15)

        # Verify after restart
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
    # end test_pod_with_oc_master_restart_controllers

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_oc_master_restart_api(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Restart api
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        os_node = self.inputs.k8s_master_ip

        output = self.inputs.run_cmd_on_server(os_node, '/usr/local/bin/master-restart api')
        assert output == '2',  'master-restart api failed'
        time.sleep(15)

        # Verify after restart
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
    # end test_pod_with_oc_master_restart_api

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_pod_with_oc_master_restart_etcd(self):
        '''
        Verify setup of 2 PODs created in 2 different namespace
        Test ping between pods
        Ping should pass
        Restart Etcd
        Re-verify setup of 2 PODs across 2 different namespace
        Re-verify test ping between pods
        Ping should pass
        '''
        namespace1 = self.setup_namespace()
        pod1 = self.setup_busybox_pod(namespace=namespace1.name)
        assert pod1.verify_on_setup()
        namespace2 = self.setup_namespace()
        pod2 = self.setup_busybox_pod(namespace=namespace2.name)
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
        os_node = self.inputs.k8s_master_ip

        output = self.inputs.run_cmd_on_server(os_node, '/usr/local/bin/master-restart etcd')
        assert output == '0',  'master-restart etcd failed'
        time.sleep(15)

        # Verify after restart
        assert pod1.verify_on_setup()
        assert pod2.verify_on_setup()
        assert pod1.ping_to_ip(pod2.pod_ip, expectation=True)
    # end test_pod_with_oc_master_restart_etcd
