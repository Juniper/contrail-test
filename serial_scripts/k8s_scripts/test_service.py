import random
import time
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from k8s.service import ServiceFixture
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_lock
import test
from tcutils.util import skip_because
from tcutils.util import get_random_name

lass TestService(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestService, cls).tearDownClass()

    @test.attr(type=['k8s_sanity'])
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_service_with_kube_manager_restart(self):
        ''' Create a service type loadbalancer with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            Validate that webservice is load-balanced from outside network
            Restart kube-manager and verify service
            Please make sure BGP multipath and per packer load balancing
            is enabled on the MX
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        #assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels, type='LoadBalancer')
        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                    labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)

        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # When Isolation enabled we need to change SG to allow traffic
        # from outside. For that we need to disiable service isolation
        if self.setup_namespace_isolation:
            namespace.disable_service_isolation()

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])

        self.restart_kube_manager()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1, pod2], service.cluster_ip,
                                      test_pod=pod3)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], service.external_ips[0])


    def common_checks_for_nodeport_service(self,podlist,s1,s2):
        """commo routine to validate the nodeport service across all the nodes
           with user definned nodeport ad also the auto assigned nodeport
           1.access the mnodeport from outside the cluster
           2.access the odeport from with in the cluster
              a. with in the same namespace
              b. from the different namespace
        """
        for node_ip in self.inputs.k8s_slave_ips:
             assert self.validate_nginx_lb([podlist[0], podlist[1]], node_ip,
                                            test_pod=podlist[2],
                                            nodePort=s1.nodePort)
             assert self.validate_nginx_lb([podlist[4], podlist[5]], node_ip,
                                            test_pod=podlist[3],nodePort=s2.nodePort)
             #access the Nodeport from outside the cluster
             assert self.validate_nginx_lb([podlist[0], podlist[1]], node_ip,
                                     nodePort=s1.nodePort)
             assert self.validate_nginx_lb([podlist[4], podlist[5]], node_ip,nodePort=s2.nodePort)

             #access the Nodeport from outside of the anmespaces
             assert self.validate_nginx_lb([podlist[0], podlist[1]], node_ip,
                                            test_pod=podlist[3],
                                            nodePort=s1.nodePort,
                                            expectation=False)
             assert self.validate_nginx_lb([podlist[4], podlist[5]], node_ip,
                                            test_pod=podlist[2],
                                            nodePort=s2.nodePort,
                                            expectation=False)
    #End of common_checks_for_nodeport_service


    @preposttest_wrapper
    def test_kubelet_restart_on_slaves_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        app1 = 'http_nodeport_test1'
        labels = {'app': app}
        labels1 = {'app': app1}
        user_node_port = 31111
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort", nodePort = user_node_port)
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels1, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels1)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels1)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        assert (service_in_ns1.nodePort == user_node_port) ,"service should be having the node port which is user provided"
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End of test_kubelet_restart_on_slaves_with_multiple_nodeport_servoces_with_namespace_isolation

    @preposttest_wrapper
    def test_docker_restart_on_slaves_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        labels = {'app': app}
        user_node_port = 30001
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort", nodePort = user_node_port)
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        assert (service_in_ns1.nodePort == user_node_port) , "service should be having the node port which is user provided"
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End test_docker_restart_on_slaves_with_multiple_nodeport_servoces_with_namespace_isolation

    @preposttest_wrapper
    def test_vrouter_restart_on_slaves_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort")
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        # Restart Vrouter agent
        self.restart_vrouter_agent()
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End test_vrouter_restart_on_slaves_with_multiple_nodeport_servoces_with_namespace_isolation

    @preposttest_wrapper
    def test_kube_manager_restart_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort")
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        # Restart Kube manager
        self.restart_kube_manager()
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End test_kube_manager_restart_with_multiple_nodeport_servoces_with_namespace_isolation

    @preposttest_wrapper
    def test_reboot_slaves_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort")
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        for node in self.inputs.k8s_slave_ips:
             self.inputs.reboot(node)
        self.verify_ping_between_pods_across_namespaces_and_public_network(client1, client2,client3)
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End test_reboot_slaves_with_multiple_nodeport_servoces_with_namespace_isolation

    @preposttest_wrapper
    def test_docker_restart_on_master_with_multiple_nodeport_services_with_namespace_isolation(self):
        app = 'http_nodeport_test'
        labels = {'app': app}
        user_node_port = 30002
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort", nodePort = user_node_port)
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_busybox_pod(namespace=namespace2.name)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        pod6 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod6)
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        assert (service_in_ns1.nodePort == user_node_port) , "service should be having the node port which is user provided"
        podlist = [pod1,pod2,pod3,pod4,pod5,pod6]
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
        self.inputs.restart_service(service_name = "docker",
                                    host_ips = [self.inputs.k8s_master_ip])
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.common_checks_for_nodeport_service(podlist,service_in_ns1,service_in_ns2)
    #End of test_docker_restart_on_master_with_multiple_nodeport_servoces_with_namespace_isolation
