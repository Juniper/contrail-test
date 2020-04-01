from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import time
import test

class TestPodDeployment(BaseK8sTest):

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
       
    @preposttest_wrapper
    def test_deployment_1(self):
        '''
        Create a deployment and delete it
        Create the same deployment again
        Validate that deployment verification passes and pods work as expected
        This is done by creating a http service out of these pods validating
        with traffic
        '''
        client_pod = self.setup_busybox_pod()
        namespace = 'default'
        labels = {'a': 'b'}

        # Openshift restricts SCC for API-access by default for Replication Controllers, below enables it
        if self.inputs.deployer == 'openshift':
            os_node = self.inputs.k8s_master_ip
            ocad = "oc adm policy add-scc-to-user anyuid system:serviceaccount:%s:default"%(namespace)
            self.inputs.run_cmd_on_server(os_node, ocad)

        dep_1 = self.setup_nginx_deployment(name='dep-test',
                                            replicas=3,
                                            pod_labels=labels)
        assert dep_1.verify_on_setup()
        self.perform_cleanup(dep_1)
        time.sleep(1) # Creation of another deployment with same name instantly result in creation failure
                      # Issue observed when Kub version upgraded to 1.9 and Kube python API version upgraded to 4.0
        dep_2 = self.setup_nginx_deployment(name='dep-test',
                                            replicas=3,
                                            pod_labels=labels)
        assert dep_2.verify_on_setup()

        service = self.setup_http_service(namespace=namespace,
                                          labels=labels)
        server_pods = dep_2.get_pods_list()
        s_pod_fixtures = []
        for x in server_pods:
            # Note that this will not create a new pod, but just reads
            # the pods in the existing deployment
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        # end for
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
            test_pod=client_pod)
    # end test_deployment_1

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_deployment_replica_updation(self):
        '''
        Create a deployment with n replicas
        Update the deployment to have more replicas
        Validate that a service with expected replicas work
        '''
        labels = {'a': 'b'}
        replicas = len(self.inputs.compute_ips)*2
        new_replicas = len(self.inputs.compute_ips)*3
        namespace = self.setup_namespace()

        # By default, Openshift restricts SCC for API-access for Replication Controllers, below enables it
        if self.inputs.deployer == 'openshift':
            os_node = self.inputs.k8s_master_ip
            ocad = "oc adm policy add-scc-to-user anyuid system:serviceaccount:%s:default"%(namespace.name)
            self.inputs.run_cmd_on_server(os_node, ocad)

        client_pod = self.setup_busybox_pod(namespace=namespace.name)
        dep_1 = self.setup_nginx_deployment(namespace=namespace.name,
            replicas=replicas, pod_labels=labels)
        assert dep_1.verify_on_setup()
        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        dep_1.set_replicas(new_replicas)
        assert dep_1.verify_on_setup()

        s_pod_fixtures = []
        server_pods = dep_1.get_pods_list()
        for x in server_pods:
            s_pod_fixture = self.setup_nginx_pod(name=x.metadata.name,
                namespace=namespace.name)
            self.verify_nginx_pod(s_pod_fixture)
            s_pod_fixtures.append(s_pod_fixture)
        # end for
        assert self.validate_nginx_lb(s_pod_fixtures, service.cluster_ip,
            test_pod=client_pod)

    # end test_deployment_replica_updation
