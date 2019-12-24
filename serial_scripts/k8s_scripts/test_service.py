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

class TestService(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestService, cls).setUpClass()
        if cls.inputs.compute_control_ips:
          cls.cn_list = list(cls.inputs.compute_control_ips)
        else:
          cls.cn_list = list(cls.inputs.compute_ips)

    @classmethod
    def tearDownClass(cls):
        super(TestService, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
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
        self.addCleanup(self.invalidate_kube_manager_inspect)
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
        assert service.verify_on_setup()

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


    def common_checks_for_nodeport_service(self, svclist, pdslist) :
        """commo routine to validate the nodeport service across all the nodes
           with user definned nodeport ad also the auto assigned nodeport
           1.access the mnodeport from outside the cluster
           2.access the odeport from with in the cluster
              a. with in the same namespace 
              b. from the different namespace
        """
        for node_ip in self.cn_list :
             assert self.validate_nginx_lb([pdslist[0], pdslist[1]], node_ip,
                                            nodePort=svclist[0].nodePort)
             assert self.validate_nginx_lb([pdslist[0], pdslist[1]], svclist[0].cluster_ip,
                                            test_pod=pdslist[5],
                                            nodePort=svclist[0].nodePort,
                                            expectation=False)
             assert self.validate_nginx_lb([pdslist[3], pdslist[4]], node_ip,
                                            nodePort=svclist[1].nodePort)

             #access the Nodeport from outside the namespace 
             assert self.validate_nginx_lb([pdslist[0], pdslist[1]], node_ip,
                                            test_pod = pdslist[6],
                                            nodePort=svclist[0].nodePort)
     
             assert self.validate_nginx_lb([pdslist[3], pdslist[4]], node_ip,
                                            test_pod = pdslist[6],
                                            nodePort=svclist[1].nodePort)

    #End of common_checks_for_nodeport_service

    def common_setup_for_nodeport(self, userport=None, tag1="http_nodeport_test",
                                  tag2=None, isolation=True):

        labels = {'app': tag1}
        if tag2 is None :
           tag2 = tag1
        labels1 = {'app': tag2}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace3_name = get_random_name("ns3")
        namespace1 = self.setup_namespace(name=namespace1_name, isolation=isolation)
        namespace2 = self.setup_namespace(name=namespace2_name, isolation=isolation)
        namespace3 = self.setup_namespace(name=namespace3_name, isolation=isolation, ip_fabric_forwarding=True)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        assert namespace3.verify_on_setup()
        service_in_ns1 = self.setup_http_service(namespace=namespace1.name,
                                        labels=labels, type="NodePort", nodePort=userport)
        service_in_ns2 = self.setup_http_service(namespace=namespace2.name,
                                        labels=labels1, type="NodePort")
        pod1 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod2 = self.setup_nginx_pod(namespace=namespace1.name, labels=labels)
        pod3 = self.setup_busybox_pod(namespace=namespace1.name)
        pod4 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels1)
        pod5 = self.setup_nginx_pod(namespace=namespace2.name, labels=labels1)
        pod6 = self.setup_busybox_pod(namespace=namespace2.name)
        pod7 = self.setup_busybox_pod(namespace=namespace3.name)
        assert self.verify_nginx_pod(pod1)
        assert self.verify_nginx_pod(pod2)
        assert self.verify_nginx_pod(pod4)
        assert self.verify_nginx_pod(pod5)
        assert self.verify_nginx_pod(pod7)
        assert pod3.verify_on_setup()
        assert pod6.verify_on_setup()
        namespace_list=[namespace1,namespace2]
        service_list=[service_in_ns1,service_in_ns2]
        pod_list=[pod1,pod2,pod3,pod4,pod5,pod6,pod7]
        return  (service_list,pod_list)

    @preposttest_wrapper
    def test_kubelet_restart_on_slaves_with_nodeport_services(self):
        app1 = 'http_nodeport_test1'
        user_node_port = 31111
        (svc,pds) = self.common_setup_for_nodeport(user_node_port, tag2=app1)
        assert (svc[0].nodePort == user_node_port),"nodeport is not refclecting"
        self.common_checks_for_nodeport_service(svc,pds)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(30) # Wait timer for all kubernetes pods to stablise.
        self.common_checks_for_nodeport_service(svc,pds)

    @preposttest_wrapper
    def test_docker_restart_on_slaves_with_nodeport_services(self):
        user_node_port = 30001
        (svc,pds) = self.common_setup_for_nodeport(user_node_port)
        assert (svc[0].nodePort == user_node_port),"nodeport is not refclecting"
        self.common_checks_for_nodeport_service(svc, pds)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.common_checks_for_nodeport_service(svc, pds)

    @preposttest_wrapper
    def test_vrouter_restart_on_slaves_with_nodeports(self):
        (svc,pds) = self.common_setup_for_nodeport()
        self.common_checks_for_nodeport_service(svc, pds)
        # Restart Vrouter agent
        self.restart_vrouter_agent()
        self.common_checks_for_nodeport_service(svc, pds)

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_kube_manager_restart_with_nodeport_services(self):
        (svc,pds) = self.common_setup_for_nodeport()
        self.common_checks_for_nodeport_service(svc, pds)
        # Restart Kube manager
        self.restart_kube_manager()
        self.common_checks_for_nodeport_service(svc, pds)

    @preposttest_wrapper
    def test_reboot_slaves_with_nodeport_services(self):
        (svc,pds) = self.common_setup_for_nodeport()
        self.common_checks_for_nodeport_service(svc, pds)
        for node in self.inputs.k8s_slave_ips:
             self.inputs.reboot(node)
        self.common_checks_for_nodeport_service(svc, pds)

    @preposttest_wrapper
    def test_docker_restart_on_master_with_nodeport_services(self):
        user_node_port = 30002
        (svc,pds) = self.common_setup_for_nodeport(user_node_port)
        assert (svc[0].nodePort == user_node_port),"nodeport is not refclecting"
        self.common_checks_for_nodeport_service(svc, pds)
        self.inputs.restart_service(service_name = "docker",
                                    host_ips = [self.inputs.k8s_master_ip])
        time.sleep(60) # Wait timer for all contrail service to come up.
        self.common_checks_for_nodeport_service(svc,pds)
