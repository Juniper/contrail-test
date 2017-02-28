import test
from tcutils.util import get_random_name
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
                            backend_port=8000):
        '''
        A simple helper method to create a service
        '''
        name = name or get_random_name('k8s-svc')
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

