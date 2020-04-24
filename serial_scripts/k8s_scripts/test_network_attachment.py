from past.builtins import cmp
from builtins import str
from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import test
import re
import json
import time
from pprint import pprint
from tcutils.util import get_random_name
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.util import skip_because
from tcutils.util import get_random_cidr

class TestNetworkAttachment(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkAttachment, cls).setUpClass()
        if cls.inputs.compute_control_ips:
           cls.cn_list = list(cls.inputs.compute_control_ips)
        else:
           cls.cn_list = list(cls.inputs.compute_ips)

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkAttachment, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    def common_setup_for_multi_intf(self,
                     net1 = None,
                     net2 = None,
                     namespace='default',
                     labels = None,
                     isolation = False,
                     ip_fabric_snat = False,
                     ip_fabric_forwarding = False,
                     nginx = False):
        ''' common setup for network attachment definitionsi
            1.Creteates two network attachment definitions namely left_nad and right_nad
            2.Verify the Network attahment are created
            3.Create two Cirros pods by associating the network attachment definitions
              created as part of the step 1.
            4.Verify the pods are created with network attachments
            5. returns the pods and with its ips
        '''
        cidr1 = net1 or get_random_cidr()
        cidr2 = net2 or get_random_cidr()
        left_nad = self.setup_network_attachment(namespace=namespace, cidr=cidr1, ip_fabric_forwarding=ip_fabric_forwarding)
        right_nad = self.setup_network_attachment(namespace=namespace, cidr=cidr2, ip_fabric_snat=ip_fabric_snat)
        #Verify if the Network attachmnets are created
        assert left_nad.verify_on_setup()
        assert right_nad.verify_on_setup()
        #Logs the Network attachments objects for debugging purpose
        pprint(left_nad)
        pprint(right_nad)
        #update the metdata object to use th above created
        #network attachments definitions and create the cirros pods
        metadata={}
        metadata['annotations']={}
        metadata['annotations']['k8s.v1.cni.cncf.io/networks'] = {}
        left_net = {"name": left_nad.metadata["name"]}
        right_net = {"name": right_nad.metadata["name"]}
        nets = [left_net, right_net]
        metadata["annotations"]["k8s.v1.cni.cncf.io/networks"] = str(nets)
        pprint(metadata)
        pod1 = get_random_name('left')
        pod2 = get_random_name('right')
        #setting up a cirros pod by assocating the multiple interfaces#
        metadata['annotations']['k8s.v1.cni.cncf.io/networks'] = \
                json.dumps(eval(metadata['annotations']['k8s.v1.cni.cncf.io/networks']))
        #pod1 = self.setup_pod(name=pod1, metadata=metadata, spec=spec)
        #create a cirros pod with network attachment definitions
        #managent ,left and right
        if nginx:
           pod1 = self.setup_nginx_pod(name=pod1, metadata=metadata, namespace=namespace, labels=labels)
        else:
           pod1 = self.setup_cirros_pod(name=pod1, metadata=metadata,namespace=namespace)
        assert pod1.verify_on_setup()

        pod1_mgmpt_ip = pod1.pod_ip
        pod1_ip1 = pod1.get_pod_ip(left_nad.metadata["name"])
        pod1_ip2 = pod1.get_pod_ip(right_nad.metadata["name"])
        pod1_details = [pod1, pod1_mgmpt_ip, pod1_ip1, pod1_ip2]

        metadata.update({"name" : pod2})
        #checking if the ipod has created with rewreid interfaces
        if nginx:
           pod2 = self.setup_nginx_pod(name=pod2, metadata=metadata, namespace=namespace, labels=labels)
        else:
           pod2 = self.setup_cirros_pod(name=pod2, metadata=metadata, namespace = namespace)
        assert pod2.verify_on_setup()
        #pick the ip address of the pods  from the corresponding network attachment
        pod2_mgmt_ip = pod2.pod_ip
        pod2_ip1 = pod2.get_pod_ip(left_nad.metadata["name"])
        pod2_ip2 = pod2.get_pod_ip(right_nad.metadata["name"])
        pod2_details = [pod2, pod2_mgmt_ip, pod2_ip1, pod2_ip2]
        #self.verify_rechability_between_multi_intf_pods (pod1_details, pod2_details )
        return (pod1_details, pod2_details)

    def verify_rechability_between_multi_intf_pods(self, pod1, pod2, expectation=True):
        ''' Verify the reachability among the pods and its
            network attachments definitions along with managment
            between left pod to right pod
        '''
        #verify the rechability between the management ip of the pods
        assert pod2[0].ping_to_ip(pod1[1], expectation=expectation)
        assert pod2[0].ping_to_ip(pod1[2], expectation=expectation)
        assert pod2[0].ping_to_ip(pod1[3], expectation=expectation)
        #verify the rechability across the left network attachment
        assert pod1[0].ping_to_ip(pod2[1], expectation=expectation)
        assert pod1[0].ping_to_ip(pod2[2], expectation=expectation)
        assert pod1[0].ping_to_ip(pod2[3], expectation=expectation)
    #end verify_rechability_between_multi_intf_pods()

    def verify_default_route(self, pod):
        """ Routine to verify the defult gatway is exists
            and the default route is is through eth0
            param pod: name of the pod
        """
        cmd = 'ip route  | grep default'
        output = pod.run_cmd_on_pod(cmd)
        output = output.strip()
        pprint(output)
        output1 = re.search('default\s+via\s+(\d+.\d+.\d+.\d+)\s+dev\s+eth(\d+)',output)
        default_gw_ips = ["10.47.255.254","10.131.255.254"]
        assert output1.groups()[0] in default_gw_ips
        assert output1.groups()[1] == '0'
        self.logger.info("\nDefault route check is PASSED :%s" %(output))
    #end verify_default_route

    def verify_pod_intf_index(self,pod_details):
        """ Routine to check pod interface indexes
            in the following order
            eth0:management
            eth1:left pods network
            eth2:right pods netowrk
        """
        eth0_ip = self.get_intf_address('eth0',pod_details[0])
        eth1_ip = self.get_intf_address('eth1',pod_details[0])
        eth2_ip = self.get_intf_address('eth2',pod_details[0])
        #check the index of the interfaces
        assert eth0_ip == pod_details[1]
        assert eth1_ip == pod_details[2]
        assert eth2_ip == pod_details[3]
    #end verify_pod_intf_index

    def get_intf_address(self,intf,pod):
        """
           Routine if to derive the ip address of the interface in a multi interface pod
           :param intf: name of the interface for which te ip address needed to be reutrned
           :param pod: name of the pod
           :return: ipv4 address of the interface
        """
        cmd = "ifconfig "+intf+" | grep inet"
        output = pod.run_cmd_on_pod(cmd)
        output = output.strip()
        ip = re.search('inet\s+addr\s*:\s*(\d+.\d+.\d+.\d+)', output)
        ip_addr = ip.group(1)
        return ip_addr
    #end get_intf_address


    @preposttest_wrapper
    def test_pod_with_multi_intf_defualt_route(self):
        """
           :return: None
           Test ping between 2 PODs  created in a given namespace
           Each pod is spawned using multiple interfaces with network attachment definitions
           Ping should pass with corresponding network attachments
           Verify the default route is installe via eth0 and with defualt pod network
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        self.verify_default_route(pod1[0])
    #end test_pod_with_multi_intf_defualt_route

    @test.attr(type=['k8s_sanity','openshift_1'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_basic_pod_with_multi_intf(self):
        """
           :return: None
           Create two corros pods left and right
           Associate the pods with additional two networks
           Verify the pods has the indexes eth0,eth1 and eth2
               eth0 - associated with pod default network
               eth1 - assocated with left network attachment definition
               eth2 - assocated with right netowrk attachment definition
           Verify the pods are installed with default route via eth0
           Verify the reachability among the pods
           Ping should pass from
               pod1:eth0_ip <-> eth0_ip:pod2
               pod1:eth1_ip <-> eth1_ip:pod2
               pod1:eth2_ip <-> eth2_ip:pod2
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        eth0_ip = self.get_intf_address('eth0',pod1[0])
        eth1_ip = self.get_intf_address('eth1',pod1[0])
        eth2_ip = self.get_intf_address('eth2',pod1[0])
        #check the index of the interfaces
        assert eth0_ip == pod1[1]
        assert eth1_ip == pod1[2]
        assert eth2_ip == pod1[3]
        #Check the reachability among the pods . across
        #management to management i.e eth0 of pod1 to eth0 of pod2
        #additional network attachment definitions i.e
        #eth1 of pod1 to eth1 of pod2
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #default route should be installed via eth0
        #which is mapped to default pod network im this case
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
    #end test_basic_pod_with_multi_intf

    @preposttest_wrapper
    def test_dns_pod_with_multi_intf(self):
        """
           :return: None
           Test ping between 2 PODs  created in a given namespace
           Each pod is spawned using multiple interfaces with network attachment definitions
           Ping should pass with corresponding network attachments
           Verify dns resolution using nslookup
           DNS resolution should work
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        cmd = 'nslookup kubernetes.default.svc.cluster.local'
        output = pod1[0].run_cmd(cmd)
        mat1 = re.search("Name:\s+kubernetes.default.svc.cluster.local",output)
        msg = 'DNS resolution failed'
        assert mat1 is not None, msg
        mat2 = re.search("\d+.\d+.\d+.\d+\s+kubernetes.default.svc.cluster.local",output)
        assert mat2 is not None, msg
        self.logger.info('\nDNS resolution check : %s passed.\n\n Output: %s' % (
            cmd, output))
    #end test_dns_pod_with_multi_intf

    @preposttest_wrapper
    def test_basic_pod_with_multi_intf_non_default_namespace(self):
        """
        :return: None
        Test ping between 2 PODs  created in a given namespace
        Each pod is spawned using multiple interfaces with network attachment definitions
        Ping should pass with corresponding network attachments
        Ping should pass
        """
        namespace = self.setup_namespace()
        pod1, pod2 = self.common_setup_for_multi_intf(namespace = namespace.name)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_basic_pod_with_multi_intf_non_default_namespace

    @test.attr(type=['k8s_sanity','openshift_1'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_basic_pod_with_multi_intf_isolated_namespace(self):
        """
        :return: None
        Test ping between 2 PODs  created in a given namespace
        Each pod is spawned using multiple interfaces with network attachment definitions
        Ping should pass with corresponding network attachments
        Ping should pass
        Create an isolated namespace and verify
        Creste two pods with multiple interfaces in the isolated namespace
        verify ping among the same namespace pods
        Ping Should pass
        Now ping across the pods from default to isolated namespace
        Ping should fail
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        namespace = self.setup_namespace(isolation = True)
        iso_pod1, iso_pod2 = self.common_setup_for_multi_intf(namespace=namespace.name)
        self.verify_rechability_between_multi_intf_pods(iso_pod1, iso_pod2)
        #verify the rechability between isolated and default namespace
        self.verify_rechability_between_multi_intf_pods(iso_pod1, pod2 ,expectation = False)
    #end test_basic_pod_with_multi_intf_isolated_namespace

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_pod_with_multi_intf_kube_manager_restart(self):
        """
        :return: None
        Test ping between 2 PODs  created in a given namespace
        Each pod is spawned using multiple interfaces with network attachment definitions
        Ping should pass with corresponding network attachments
        Restart contrail-kube-manager
        Ping between 2 PODs again across management , left and right networks
        contrail components should be stable
        Ping should pass
        """
        self.addCleanup(self.invalidate_kube_manager_inspect)
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #check the cluster status before kube manager restart
        #cluster_status, error_nodes_before = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #Check the default route on both the pods before kube manager restart
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        #check the interface index before kube manager restart
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        #Now restart the kube manager contrainer
        self.restart_kube_manager()
        #cluster_status, error_nodes_after = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cmp(error_nodes_before, error_nodes_after) == 0 , "cluster is not stable after kube manager restart"
        #check if the default route is intact with pod default network
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    # end test_pod_with_multi_intf_kube_manager_restart

    @test.attr(type=['k8s_sanity'])
    @skip_because(slave_orchestrator='kubernetes')
    @preposttest_wrapper
    def test_pod_with_multi_intf_agent_restart(self):
        '''
        Test ping between 2 PODs created in 2 different namespace
        with multiple network attachment definitions
        Ping should pass in default mode
        Ping should fail when namespace isolation enabled
        Restart contrail-vrouter_aget
        Ping between 2 PODs again
        Ping should pass in default mode
        Ping should fail when namespace isolation enabled
        '''
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #check the cluster status before kube manager restart
        #cluster_status, error_nodes_before = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #Check the default route on both the pods before kube manager restart
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        #check the interface index before kube manager restart
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        #restart conrtail vrouter agent
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent',[compute_ip],
                                         container='agent')
        #cluster_status, error_nodes_after = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cmp(error_nodes_before, error_nodes_after) == 0 , "cluster is not stable after kube manager restart"
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        self.verify_rechability_between_multi_intf_pods (pod1, pod2)
    #end  test_pod_with_multi_intf_agent_restart

    @preposttest_wrapper
    def test_pod_multi_intf_with_kube_apiserver_restart(self):
        '''
           Create an isolated namespace
           Spwan the multi interface pods
           Verify the multi interfaces are associated with pods
           Verify the rechability acoss the pods
           Verify teh indexes of the interfaces
           Verify the default route thgouh etho
           perform the kube-apis service restrt
           once the cluster stabilizes
           Verify the pods rechabilyt and their indexes with defult routes
        '''
        namespace = self.setup_namespace(isolation = True)
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #check the cluster status before kube manager restart
        cluster_status, error_nodes_before = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #Check the default route on both the pods before kube manager restart
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        #check the interface index before kube manager restart
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        #restart the contrail kube api service on the masters
        self.inputs.restart_service("kube-apiserver",
                                    [self.inputs.k8s_master_ip],
                                    container = "kube-apiserver",
                                    verify_service = False)
        #Wait till the cluster stabilizes
        cluster_status, error_nodes_after = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        assert cmp(error_nodes_before, error_nodes_after) == 0 , "cluster is not stable after kube manager restart"
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_pod_multi_intf_with_kube_apiserver_restart

    @preposttest_wrapper
    def test_pod_mult_intf_with_kebelet_restart_on_master(self):
        """
            1.verifies multi interface pods can reach to public network when  fabric forwarding is enabled
            2.restart the kubelet service on master
            3.re verify  pods can reach to public network when  fabric forwarding is enabled
        """
        namespace = self.setup_namespace(isolation = True)
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #check the cluster status before kube manager restart
        cluster_status, error_nodes_before = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #Check the default route on both the pods before kube manager restart
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        #check the interface index before kube manager restart
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        #restart the kubelet service on master
        self.inputs.restart_service(service_name = "kubelet",
                                   host_ips = [self.inputs.k8s_master_ip])
        cluster_status, error_nodes_after = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        assert cmp(error_nodes_before, error_nodes_after) == 0 , "cluster is not stable after kube manager restart"
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_pod_mult_intf_with_kebelet_restart_on_master()

    @test.attr(type=['pod_multi_intf'])
    @preposttest_wrapper
    def test_pod_multi_inf_with_contrail_apiserver_restart(self):
        '''
            Verifies that Kube APIs are correctly recieved and processed by Contrail
            API server post contrail-api restart.
            Steps:
               1. Before creating any k8s object, restart the contrail API server
               2. Create a service with 2 pods running cirros
               3. From the local node, do a wget on the ingress public ip
            Validate that service and its loadbalancing works
        '''
        namespace = self.setup_namespace(isolation = True)
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name)
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        cluster_status, error_nodes_before = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        self.inputs.restart_service("contrail-api",
                                    self.inputs.cfgm_ips,
                                    container = "api-server")
        cluster_status, error_nodes_after = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        assert cmp(error_nodes_before, error_nodes_after) == 0 , "cluster is not stable after kube manager restart"
        self.verify_default_route(pod1[0])
        self.verify_default_route(pod2[0])
        self.verify_pod_intf_index(pod1)
        self.verify_pod_intf_index(pod2)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_ingress_with_contrail_apiserver_restart

    @test.attr(type=['pod_multi_intf'])
    @preposttest_wrapper
    def test_pod_multi_intf_with_kubelet_restart_on_slave(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when snat is enabled
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        self.inputs.restart_service(service_name = "kubelet",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(40) # Wait timer for all kubernetes pods to stablise.
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_pod_multi_intf_with_kubelet_restart_on_slave

    @test.attr(type=['pod_multi_intf'])
    @preposttest_wrapper
    def test_pod_multi_intf_with_docker_restart_on_slave(self):
        """
            1.verifies pods can reach to public network when snat is enabled
            2.restart the docker service
            3.re verify  pods can reach to public network when snat is enabled
        """
        pod1, pod2 = self.common_setup_for_multi_intf()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = self.inputs.k8s_slave_ips)
        time.sleep(60) # Wait timer for all kubernetes pods to stablise.
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_pod_multi_intf_with_docker_restart_on_slave

    @preposttest_wrapper
    def test_cluster_ip_service_with_pod_multi_intf(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            both the nginx pods are multi interface pods
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name, labels=labels, nginx=True)
        pod3 = self.setup_busybox_pod(namespace=namespace.name)
        assert self.verify_nginx_pod(pod1[0])
        assert self.verify_nginx_pod(pod2[0])
        assert pod3.verify_on_setup()
        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        assert service.verify_on_setup()
        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1[0], pod2[0]], service.cluster_ip,
                                      test_pod=pod3)
    #end  test_cluster_ip_service_with_pod_multi_intf

    @preposttest_wrapper
    def test_service_type_nodeport_with_pod_multi_intf(self):
        ''' Create a service with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced using NodePort service from with in the cluster
            outside of the cluster
            nginx pods are multi interfaced pods
            
        '''
        app = 'http_nodeport_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()
        service = self.setup_http_service(labels=labels, type="NodePort")
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name, labels=labels, nginx=True)
        pod3 = self.setup_busybox_pod()
        assert self.verify_nginx_pod(pod1[0])
        assert self.verify_nginx_pod(pod2[0])
        assert namespace.verify_on_setup()
        assert pod3.verify_on_setup()
        assert pod4.verify_on_setup()
        assert service.verify_on_setup()
        # validate Service Nodeport functionality with load-balancing on the service
        for node_ip in self.cn_list:
             assert self.validate_nginx_lb([pod1[0], pod2[0]], node_ip,
                                            nodePort=service.nodePort)

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_service_with_type_loadbalancer_with_multi_intf_pods(self):
        ''' Create a service type loadbalancer with 2 pods running nginx
            Create a third busybox pod and validate that webservice is
            load-balanced
            Validate that webservice is load-balanced from outside network
            Please make sure BGP multipath and per packer load balancing
            is enabled on the MX
        '''
        app = 'http_test'
        labels = {'app': app}
        namespace = self.setup_namespace()
        assert namespace.verify_on_setup()
        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels, type='LoadBalancer')
        #pod1 and pod2 are with multi interface pods behind the service
        #service continue to work on the default interface
        #as the default route is through pod management interface
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name, labels=labels, nginx=True)
        pod3 = self.setup_busybox_pod()
        assert self.verify_nginx_pod(pod1[0])
        assert self.verify_nginx_pod(pod2[0])
        assert pod3.verify_on_setup()
        assert service.verify_on_setup()

        # Now validate load-balancing on the service
        assert self.validate_nginx_lb([pod1[0], pod2[0]], service.cluster_ip,
                                      test_pod=pod3)
        # When Isolation enabled we need to change SG to allow traffic
        # from outside. For that we need to disiable service isolation
        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1[0], pod2[0]], service.external_ips[0])
    # end test_service_with_type_loadbalancer
    
    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_fanout_with_multi_intf_backends(self):
        '''
        Creating a fanout ingress with 2 different host having 
        2 different path along with a default backend 
        This host are supported by repective service.
        Service has required backend pod with required path 
        mentioned in ingress rule.
        From the local node, do a wget on the ingress public ip
        Validate that service and its loadbalancing works
        backend pods are with multi interfaces 
        '''
        app1 = 'http_test1'
        app2 = 'http_test2'
        labels1 = {'app':app1}
        labels2 = {'app':app2}
        service_name1 = 's1'
        service_name2 = 's2'
        path1 = 'foo'
        path2 = 'bar'
        host1 = 'foo.bar.com'
        host2 = 'bar.foo.com' 
        ingress_name = 'testingress' 
       
        namespace = self.setup_namespace(name='default')
        assert namespace.verify_on_setup()

        service1 = self.setup_http_service(namespace=namespace.name,
                                          labels=labels1,
                                          name=service_name1)

        service2 = self.setup_http_service(namespace=namespace.name,
                                          labels=labels2,
                                          name=service_name2)
        pod1, pod2 = self.common_setup_for_multi_intf(namespace=namespace.name, labels=labels1, nginx=True)
        pod3, pod4 = self.common_setup_for_multi_intf(namespace=namespace.name, labels=labels2, nginx=True)

        rules = [{'host': host1, 
                  'http': {'paths': [{
                                    'path':'/'+path1,
                                    'backend': { 'service_name': service_name1,
                                                 'service_port': 80
                                               }
                                    }]
                          }
                 },
                 {'host': host2,
                  'http': {'paths': [{
                                    'path': '/'+path2,
                                    'backend': { 'service_name': service_name2,
                                                 'service_port': 80
                                               }
                                    }]    
                         }
                 }]
   
        default_backend = {'service_name': service_name1,
                           'service_port': 80}

        ingress = self.setup_ingress(name=ingress_name,
                                     namespace=namespace.name,
                                     rules=rules,
                                     default_backend=default_backend)
        assert ingress.verify_on_setup()

        pod5 = self.setup_busybox_pod(namespace=namespace.name)
        self.verify_nginx_pod(pod1[0],path=path1)
        self.verify_nginx_pod(pod2[0],path=path1)
        self.verify_nginx_pod(pod3[0],path=path2)
        self.verify_nginx_pod(pod4[0],path=path2)

        assert pod5.verify_on_setup()

        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([pod1[0], pod2[0]], ingress.cluster_ip,
                                      test_pod=pod5, path=path1, host=host1)
        assert self.validate_nginx_lb([pod3[0], pod4[0]], ingress.cluster_ip,
                                      test_pod=pod5, path=path2, host=host2)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1[0], pod2[0]], ingress.external_ips[0], path=path1, host=host1)
        assert self.validate_nginx_lb([pod3[0], pod4[0]], ingress.external_ips[0], path=path2, host=host2)

        # Validate wget fails on negative cases 
        self.logger.info("Negative Check: Wget should fail. Trying with wrong path")
        assert not self.validate_nginx_lb([pod1[0], pod2[0]], ingress.cluster_ip,
                                      test_pod=pod5, path='wrongpath', host=host1)

        self.logger.info("Negative Check: Wget should fail. Trying with wrong host")
        assert not self.validate_nginx_lb([pod3[0], pod4[0]], ingress.cluster_ip,
                                      test_pod=pod5, path=path2, host='wrong.host.com')
    #end test_ingress_fanout_with_multi_intf_backends

    @preposttest_wrapper
    def test_multi_intf_pod_with_fabric_fwd_snat(self):
        """
            1.verifies pods can reach to public network when fabric forwarding is enabled
            3.re verify  pods can reach to public network when fabric forwarding is enabled
        """
        pod1, pod2 = self.common_setup_for_multi_intf(ip_fabric_forwarding=True, ip_fabric_snat=True)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
        #perform the kube manager restart
        #Note:Few more checks need ot be added 
        self.restart_kube_manager()
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)
    #end test_fabric_fwd_with_kube_manager_restart

    @preposttest_wrapper
    def test_multi_intf_pod_with_node_reboot(self):
        pod1, pod2 = self.common_setup_for_multi_intf(ip_fabric_forwarding=True, ip_fabric_snat=True)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)

        self.inputs.reboot(self.inputs.k8s_master_ip)
        for node in self.inputs.k8s_slave_ips:
             self.inputs.reboot(node)
        self.verify_rechability_between_multi_intf_pods(pod1, pod2)

