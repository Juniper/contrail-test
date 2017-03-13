import test
from tcutils.util import get_random_name, retry
from k8s.pod import PodFixture
from k8s.service import ServiceFixture
from k8s.namespace import NamespaceFixture
from common.connections import ContrailConnections

class BaseK8sTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        cls.connections = ContrailConnections(cls.inputs,
                              project_name='default',
                              username=cls.inputs.admin_username,
                              password=cls.inputs.admin_password,
                              logger=cls.logger)
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.logger = cls.connections.logger
        cls.k8s_client = cls.connections.k8s_client

    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseK8sTest, cls).tearDownClass()
    # end tearDownClass

    def setup_http_service(self,
                            name=None,
                            namespace='default',
                            app=None,
                            metadata=None,
                            spec=None,
                            frontend_port=80,
                            backend_port=80):
        '''
        A simple helper method to create a service

        Noticed that nginx continues to listen on port 80 even if target port
        is different. So, recommended not to change backend_port for now
        '''
        name = name or get_random_name('nginx-svc')
        metadata = metadata or {'name' :  name}
        selector_dict = {}
        spec = spec or {
                         'ports' : [
                             {
                                 'protocol' : 'TCP',
                                 'port': int(frontend_port),
                                 'targetPort': int(backend_port)
                             }
                         ]
                       }
        if app:
            selector_dict = { 'selector': { 'app': app } }
            spec.update(selector_dict)

        return self.useFixture(ServiceFixture(
            connections=self.connections,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec))
    # end create_http_service

    def setup_namespace(self,
                         name=None):
        return self.useFixture(NamespaceFixture(
                                   connections=self.connections,
                                   name=name))
    # end create_namespace

    def setup_pod(self,
                  name=None,
                  namespace='default',
                  metadata={},
                  spec={}):
        name = name or get_random_name('pod')
        metadata['name'] = metadata.get('name') or name
        spec = spec
        return self.useFixture(PodFixture(
                                   connections=self.connections,
                                   name=name,
                                   namespace=namespace,
                                   metadata=metadata,
                                   spec=spec))
    # end setup_pod

    def setup_nginx_pod(self,
                        name=None,
                        namespace='default',
                        metadata={},
                        container_port=80,
                        app=None,
                        spec={}):
        '''
        Noticed that nginx continues to listen on port 80 even if target port
        (container_port) is different
        '''
        name = name or get_random_name('nginx-pod')
        if app:
            metadata['labels'] = metadata.get('labels') or { 'app': app }
        spec = spec or {
                    'containers' : [
                        { 'image' : 'nginx',
                            'ports' : [
                                       {'container_port' : int(container_port)}
                                      ],
                        }
                    ]
              }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec)
    # end setup_nginx_pod

    def setup_busybox_pod(self,
                        name=None,
                        namespace='default',
                        metadata={},
                        spec={}):
        name = name or get_random_name('busybox-pod')
        spec = spec or {
                    'containers' : [
                        { 'image' : 'busybox',
                          'command' : ['sleep', '1000000'],
                          'image_pull_policy' : 'IfNotPresent',
                        }
                    ],
                    'restart_policy' : 'Always',
                }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec)
    # end setup_busybox_pod

    @retry(delay=1, tries=5)
    def validate_nginx_lb(self,
                          test_pod,
                          lb_pods,
                          service_ip,
                          port=80):
        '''
        From test_pod , run wget on http://<service_ip>:<port> and check
        if the all the lb_pods respond to atleast one of the requests over
        3*len(lb_pods) attempts
        '''
        for pod in lb_pods:
            pod.run_cmd('echo %s > /usr/share/nginx/html/index.html' %(
                pod.name))
        attempts = len(lb_pods)*5
        hit = {}
        for x in lb_pods:
            hit[x.name] = 0
        for i in range(0, attempts):
            out = test_pod.run_cmd('wget http://%s:%s -O -' %(
                                   service_ip, port), shell='/bin/sh -l -c')
            for pod in lb_pods:
                if pod.name in out:
                    hit[pod.name] += 1
            if 0 not in hit.values():
                self.logger.info('Responses seen from all pods, lb seems fine'
                                 'Hits : %s' %(hit))
                return True
        if 0 in hit.values():
            msg = ('No http hit seen for one or more pods.'
                    'Pls check. Hits: %s' %(hit))
            self.logger.warn(msg)
            return False
        self.logger.info('Nginx lb hits seem to be ok: %s' %(hit))
        return True
    # end validate_nginx_lb
