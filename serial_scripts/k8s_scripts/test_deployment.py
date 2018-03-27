import time
import test
from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status_check import ContrailStatusChecker


class TestDeployment(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestDeployment, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestDeployment, cls).tearDownClass()

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_deployment_with_kube_manager_restart(self):
        ''' Create a deployment object with 3 pod replicas and Verify http service works across the pod replicas
            Verify deletion of the deployment object cleans up all the pods which it had created 
            Restart kube manager on all the control nodes and verify redeploying the deployment object with pod replicas take into effect 
            Re-verify the deployment passes and pods work as expected using http service with new set of replicas
        '''

        client_pod = self.setup_busybox_pod()
        namespace = 'default'
        labels = {'deployment': 'test'}
        dep = self.setup_nginx_deployment(name='dep-test',
                                            replicas=3,
                                            pod_labels=labels)
        assert dep.verify_on_setup()
        service = self.setup_http_service(namespace=namespace,
                                          labels=labels)
        server_pods = dep.get_pods_list()
        s_pod_fixtures = []
        for x in server_pods:
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)
        self.restart_kube_manager()
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)
        self.perform_cleanup(dep)
        self.sleep(1)
        '''After restart of the Kube Manager recreate the deployment obect 
           With additional pod replicas''' 
        dep = self.setup_nginx_deployment(name='dep-test',
                                          replicas=5,
                                          pod_labels=labels)
        
        assert dep.verify_on_setup()
        service = self.setup_http_service(namespace=namespace,
                                          labels=labels)
        server_pods = dep.get_pods_list()
        s_pod_fixtures = []
        for x in server_pods:
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)

    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_deployment_with_agent_restart(self):
        ''' Create a deployment object with 3 pod replicas and Verify http service works across the pod replicas
            Verify deletion of the deployment object cleans up all the pods which it had created 
            Restart vrouter agent on all the nodes and verify redeploying the deployment object with pod replicas take into effect 
            Re-verify the deployment passes and pods work as expected using http service with new set of replicas
        '''
        client_pod = self.setup_busybox_pod()
        namespace = 'default'
        labels = {'deployment': 'test'}
        dep = self.setup_nginx_deployment(name='dep-test',
                                            replicas=3,
                                            pod_labels=labels)
        assert dep.verify_on_setup()
        service = self.setup_http_service(namespace=namespace,
                                          labels=labels)
        server_pods = dep.get_pods_list()
        s_pod_fixtures = []
        for x in server_pods:
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)
        self.restart_vrouter_agent()
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)
        self.perform_cleanup(dep)
        self.sleep(1)
        '''After restart of the vrouter agent recreate the deployment obect 
           With additional pod replicas''' 
        dep = self.setup_nginx_deployment(name='dep-test',
                                          replicas=5,
                                          pod_labels=labels)
        
        assert dep.verify_on_setup()
        service = self.setup_http_service(namespace=namespace,
                                          labels=labels)
        server_pods = dep.get_pods_list()
        s_pod_fixtures = []
        for x in server_pods:
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
                                      test_pod=client_pod)
