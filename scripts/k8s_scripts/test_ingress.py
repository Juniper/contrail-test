from common.k8s.base import BaseK8sTest
from k8s.ingress import IngressFixture
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import skip_because

class TestIngress(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestIngress, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestIngress, cls).tearDownClass()

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_1(self):
        ''' Create a service with 2 pods running nginx
            Create an ingress out of this service
            From the local node, do a wget on the ingress public ip
            Validate that service and its loadbalancing works

            For now, do this test only in default project
        '''
        app = 'http_test'
        labels = {'app':app}
        namespace = self.setup_namespace(name='default')
        assert namespace.verify_on_setup()

        service = self.setup_http_service(namespace=namespace.name,
                                          labels=labels)
        pod1 = self.setup_nginx_pod(namespace=namespace.name, 
                                          labels=labels)

        pod2 = self.setup_nginx_pod(namespace=namespace.name, 
                                          labels=labels)

        ingress = self.setup_simple_nginx_ingress(service.name,
                                                  namespace=namespace.name)
        assert ingress.verify_on_setup()

        pod3 = self.setup_busybox_pod(namespace=namespace.name)
        self.verify_nginx_pod(pod1)
        self.verify_nginx_pod(pod2)
        assert pod3.verify_on_setup()

        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([pod1, pod2], ingress.cluster_ip,
                                      test_pod=pod3)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], ingress.external_ips[0])
    # end test_service_1

    @skip_because(mx_gw = False)
    @test.attr(type=['k8s_sanity'])
    @preposttest_wrapper
    def test_ingress_fanout(self):
        '''
        Creating a fanout ingress with 2 different host having 
        2 different path along with a default backend 
        This host are supported by repective service.
        Service has required backend pod with required path 
        mentioned in ingress rule.
        From the local node, do a wget on the ingress public ip
        Validate that service and its loadbalancing works
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

        pod1 = self.setup_nginx_pod(namespace=namespace.name,
                                          labels=labels1)
        pod2 = self.setup_nginx_pod(namespace=namespace.name,
                                          labels=labels1)
        pod3 = self.setup_nginx_pod(namespace=namespace.name,
                                          labels=labels2)
        pod4 = self.setup_nginx_pod(namespace=namespace.name,
                                          labels=labels2)

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
        self.verify_nginx_pod(pod1,path=path1)
        self.verify_nginx_pod(pod2,path=path1)
        self.verify_nginx_pod(pod3,path=path2)
        self.verify_nginx_pod(pod4,path=path2)

        assert pod5.verify_on_setup()

        # Now validate ingress from within the cluster network
        assert self.validate_nginx_lb([pod1, pod2], ingress.cluster_ip,
                                      test_pod=pod5, path=path1, host=host1)
        assert self.validate_nginx_lb([pod3, pod4], ingress.cluster_ip,
                                      test_pod=pod5, path=path2, host=host2)

        # Now validate ingress from public network
        assert self.validate_nginx_lb([pod1, pod2], ingress.external_ips[0], path=path1, host=host1)
        assert self.validate_nginx_lb([pod3, pod4], ingress.external_ips[0], path=path2, host=host2)

        # Validate wget fails on negative cases 
        self.logger.info("Negative Check: Wget should fail. Trying with wrong path")
        assert not self.validate_nginx_lb([pod1, pod2], ingress.cluster_ip,
                                      test_pod=pod5, path='wrongpath', host=host1)

        self.logger.info("Negative Check: Wget should fail. Trying with wrong host")
        assert not self.validate_nginx_lb([pod3, pod4], ingress.cluster_ip,
                                      test_pod=pod5, path=path2, host='wrong.host.com')
    # test_ingress_fanout
   
# Isolated namespace classes follow

class TestIngressVNIsolated(TestIngress):

    @classmethod
    def setUpClass(cls):
        super(TestIngress, cls).setUpClass()
        cls.setup_namespace_isolation = True
