from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name
import time
import test
class TestFabricFWDRestarts(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestFabricFWDRestarts, cls).setUpClass()
        cls.ip_to_ping = cls.inputs.bgp_control_ips[0]

    @classmethod
    def tearDownClass(cls):
        super(TestFabricFWDRestarts, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    def setup_namespaces_pods_for_fabric_restart(self, isolation=False,ip_fabric_forwarding=False):
        """ common routine to create the namesapces and the pods  by enabling the fabric forwarding
            1.create 2 namespaces (ns1,ns2:enable fabric forwarding)
            2.create pods in each namespace and verify(ns1:pod1,pod2, ns2:pod1, ns3:pod1 ,default:pod1)
        """
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = isolation,
                                          ip_fabric_forwarding = ip_fabric_forwarding)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = isolation,
                                          ip_fabric_forwarding = ip_fabric_forwarding)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        label = "fabric"
        #create a pod in default namespaces
        pod1_in_default_ns = self.setup_ubuntuapp_pod()
        #create a two pods in fabric forwarding enabled namespace
        pod1_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name,
                                               labels={'app': label})
        pod2_in_ns1 = self.setup_ubuntuapp_pod(namespace=namespace1_name,
                                               labels={'app': label})
        #create a pod in fabric and ip fabric enabled namespace
        pod1_in_ns2 = self.setup_ubuntuapp_pod(namespace=namespace2_name,
                                               labels={'app': label})
        assert pod1_in_default_ns.verify_on_setup()
        assert pod1_in_ns1.verify_on_setup()
        assert pod2_in_ns1.verify_on_setup()
        assert pod1_in_ns2.verify_on_setup()
        client1 = [pod1_in_ns1, pod2_in_ns1,  namespace1]
        client2 = [pod1_in_ns2, namespace2]
        client3 = [pod1_in_default_ns]
        return (client1, client2, client3)
    #end setup_namespaces_pods_for_fabric_restart

    def verify_ping_between_pods_across_namespaces_and_public_network(self, client1, client2, client3):
        """
           1.verifies the ping between pods in the fabric_forwarding enabled namespace
           2.verifies the ping between pods across the fabric_forwarding enabled nnamespaces
           4.verifies the ping between pods acoss fabric forwarding ennabled and default namespaces
           5.verifies the public reachability from the pods in fabric forwarding enabled namespace
        """
        #verifying the rechability with public netork and across namespaces
        assert client1[0].ping_to_ip(self.ip_to_ping)
        assert client1[1].ping_to_ip(self.ip_to_ping)
        assert client2[0].ping_to_ip(self.ip_to_ping)
        assert client1[0].ping_to_ip(client1[1].pod_ip)
        #verifying pods in isolated/default namespaces shoud not reach each other
        #when fabric forwarding is enabled
        assert client1[0].ping_to_ip(client2[0].pod_ip, expectation=False)
        assert client1[0].ping_to_ip(client3[0].pod_ip, expectation=False)

    @preposttest_wrapper
    def test_fabric_fwd_with_kube_manager_restart(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            2.restart the kube manager service
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        #perform the kube manager restart  
        self.restart_kube_manager()
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_kube_manager_restart 

    @preposttest_wrapper
    def test_fabric_fwd_with_vrouter_agent_restart(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            2.restart the vrouter agent on nodes
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        #perform the kube manager restart
        self.restart_vrouter_agent()
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end  test_fabric_fwd_with_vrouter_agent_restart

    @preposttest_wrapper
    def test_fabric_fwd_pod_restart(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            2.restart the pods which are created in fabric forwarding   enabled namespaces
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        assert self.restart_pod(client1[0])
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_pod_restart

    @preposttest_wrapper
    def test_fabric_fwd_with_docker_restart_on_slave(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        self.inputs.restart_service(service_name = "docker",
                                    host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_docker_restart_on_slave

    @preposttest_wrapper
    def test_fabric_fwd_with_kubelet_restart_on_slave(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                                      ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_kubelet_restart_on_slave

    @preposttest_wrapper
    def test_fabric_fwd_with_nodes_reboot(self):
        """
            1.verifies pods can reach to public network when fabric_forwarding is enabled
            2.restart the docker service on master
            3.re verify  pods can reach to public network when fabric_forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                               ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        for node in self.inputs.k8s_slave_ips:
             self.inputs.reboot(node)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_nodes_reboot

    @preposttest_wrapper
    def test_fabric_fwd__with_kubelet_restart_on_master(self):
        """
            1.verifies pods can reach to public network when  fabric forwarding is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when  fabric forwarding is enabled
        """
        client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
                                                              ip_fabric_forwarding=True)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
        self.inputs.restart_service(service_name = "kubelet",
                                   host_ips = [self.inputs.k8s_master_ip])
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd__with_kubelet_restart_on_master

    #@preposttest_wrapper
    #def test_fabric_fwd_with_docker_restart_on_master(self):
    #    """
    #        1.verifies pods can reach to public network when  fabric forwarding is enabled
    #        2.restart the docker service on master
    #        3.re verify  pods can reach to public network when  fabric forwarding is enabled
    #    """
    #    client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
    #                                                           ip_fabric_forwarding=True)
    #    self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #    self.inputs.restart_service(service_name = "docker",
    #                                host_ips = [self.inputs.k8s_master_ip])
    #    time.sleep(60) # Wait timer for all contrail service to come up.
    #    self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_docker_restart_on_master

    ##@preposttest_wrapper
    #def test_fabric_fwd_with_master_reboot(self):
    #    """
    #        1.verifies pods can reach to public network when fabric forwarding is enabled
    #        2.restart the docker service on master
    #        3.re verify  pods can reach to public network when fabric forwarding is enabled
    #    """
    #    client1, client2, client3 = self.setup_namespaces_pods_for_fabric_restart(isolation=True,
    #                                                           ip_fabric_forwarding=True)
    #    self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #    self.inputs.reboot(self.inputs.k8s_master_ip)
    #    self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2, client3)
    #end test_fabric_fwd_with_master_reboot
