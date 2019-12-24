"""Test module for ip fabric snat for k8s
   this module contains the restart and reboot scenario based 
   testcases to verify the behavior of the ip fabric snat with k8s
"""
from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name, skip_because
import test
import time
from tcutils.contrail_status_check import ContrailStatusChecker

class TestFabricSNATRestarts(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestFabricSNATRestarts, cls).setUpClass()
        if cls.inputs.slave_orchestrator == 'kubernetes':
            cls.ip_to_ping = cls.inputs.k8s_clusters[0]['master_ip']
        else:
            cls.ip_to_ping = cls.inputs.bgp_control_ips[0]

    @classmethod
    def tearDownClass(cls):
        super(TestFabricSNATRestarts, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    def setup_common_namespaces_pods(self, isolation=False, ip_fabric_snat=False,
                                     ip_fabric_forwarding=False):
        """ common routine to create the namesapces and the pods  by enabling the fabric snat
            and fabric forwarding
            1.create 3 namespaces (ns1:enable snat,ns2:enable fabric forwarding and snat,ns3:enable snat)
            2.create pods in each namespace and verify(ns1:pod1,pod2, ns2:pod1, ns3:pod1 ,default:pod1)
        """
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace3_name = get_random_name("ns3")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = isolation,
                                                 ip_fabric_snat = ip_fabric_snat,
                                                 ip_fabric_forwarding = False)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = isolation,
                                                 ip_fabric_snat = ip_fabric_snat,
                                                 ip_fabric_forwarding = ip_fabric_forwarding)
        namespace3 = self.setup_namespace(name = namespace3_name, isolation = isolation,
                                                 ip_fabric_snat = ip_fabric_snat,
                                                 ip_fabric_forwarding = False)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        assert namespace3.verify_on_setup()
        label1 = "snat"
        label2 = "snatfabric"
        #create a pod in default namespaces
        pod1_in_default_ns = self.setup_ubuntuapp_pod()
        #create a two pods in snat enabled namespace
        pod1_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name,
                                             labels={'app': label1})
        pod2_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name,
                                             labels={'app': label1})
        #create a pod in snat and ip fabric enabled namespace
        pod1_in_ns2 = self.setup_ubuntuapp_pod(namespace=namespace2_name,
                                             labels={'app': label2})
        #create a pod in snat enabled namespace
        pod1_in_ns3 = self.setup_ubuntuapp_pod(namespace=namespace3_name,
                                             labels={'app': label1})

        assert pod1_in_default_ns.verify_on_setup()
        assert pod1_in_ns1.verify_on_setup()
        assert pod2_in_ns1.verify_on_setup()
        assert pod1_in_ns2.verify_on_setup()
        assert pod1_in_ns3.verify_on_setup()

        client1 = [pod1_in_ns1, pod2_in_ns1,  namespace1]
        client2 = [pod1_in_ns2, namespace2]
        client3 = [pod1_in_ns3, namespace3]
        client4 = [pod1_in_default_ns]
        return (client1, client2, client3, client4)
    #end setup_common_namespaces_pods

    def verify_ping_between_pods_across_namespaces_and_public_network(self, client1, client2,
                                                                      client3, client4):
        """
           1.verifies the ping between pods in the snat enabled nnamespace
           2.verifies the ping between pods across the snat enabled nnamespaces
           3.verifies the ping between pods acoss snat and fabric forwarding enabled namespaces
           4.verifies the ping between pods acoss snat ennabled and default namespaces
           5.verifies the public reachability from the pods in snat enabled namespace
        """
        assert client1[0].ping_to_ip(self.ip_to_ping)
        assert client1[1].ping_to_ip(self.ip_to_ping)
        #assert client2[0].ping_to_ip(self.ip_to_ping)#ip fabric forwaring takes precedence
        assert client1[0].ping_to_ip(client1[1].pod_ip)
        #verifying pods in isolated/default namespaces shoud not reach each other when snat is enabled
        assert client1[0].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[0].ping_to_ip(client3[0].pod_ip, expectation=False)
        assert client1[0].ping_to_ip(client4[0].pod_ip, expectation=False)

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_snat_with_kube_manager_restart(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the kube manager service
            3.re verify  pods can reach to public network when snat is enabled
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        #perform the kube manager restart
        self.restart_kube_manager()
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        
    #end test_snat_with_kube_manager_restart

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_snat_with_vrouter_agent_restart(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the vrouter agent on nodes
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        #perform the kube manager restart
        self.restart_vrouter_agent()
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_vrouter_agent_restart

    @preposttest_wrapper
    def test_snat_pod_restart(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the pods which are created in snat enabled namespaces
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3, client4)
        assert self.restart_pod(client1[0])
        assert self.restart_pod(client2[0])
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_pod_restart

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_snat_with_docker_restart(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service 
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_docker_restart

    @preposttest_wrapper
    def test_snat_with_kubelet_restart_on_slave(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service  
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                               ip_fabric_snat=True,
                                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_kubelet_restart_on_slave

    @preposttest_wrapper
    def test_snat_with_kubelet_restart_on_master(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = [self.inputs.k8s_master_ip])
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_kubelet_restart_on_master

    @preposttest_wrapper
    def test_snat_with_docker_restart_on_master(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service on master
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = [self.inputs.k8s_master_ip])
        time.sleep(30)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
                    error_nodes)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_docker_restart


    @preposttest_wrapper
    def test_snat_with_master_reboot(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service on master
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.reboot(self.inputs.k8s_master_ip)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_master_reboot

    @preposttest_wrapper
    def test_snat_with_nodes_reboot(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service on master
            3.re verify  pods can reach to public network when snat is enabled
        """
        client1, client2, client3, client4 = self.setup_common_namespaces_pods(isolation=True,
                                                                              ip_fabric_snat=True,
                                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
        self.inputs.reboot(self.inputs.k8s_master_ip)
        for node in self.inputs.k8s_slave_ips:
             self.inputs.reboot(node)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,
                                                                           client3, client4)
    #end test_snat_with_nodes_reboot
