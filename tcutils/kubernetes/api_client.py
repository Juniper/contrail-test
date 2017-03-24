from kubernetes import client, config

from common import log_orig as contrail_logging
from tcutils.util import get_random_name


class Client():

    def __init__(self, config_file='/etc/kubernetes/admin.conf', logger=None):
        self.api_client = config.new_client_from_config(config_file)
        self.api_client.config.assert_hostname = False
        self.v1_h = client.CoreV1Api(self.api_client)
        self.v1_h.read_namespace('default')
        self.v1_beta_h = client.ExtensionsV1beta1Api(self.api_client)

        self.logger = logger or contrail_logging.getLogger(__name__)
    # end __init__

    def create_namespace(self, name):
        '''
        returns instance of class V1Namespace
        '''
        body = client.V1Namespace()
        body.metadata = client.V1ObjectMeta(name=name)
        resp = self.v1_h.create_namespace(body)
        return resp
    # end create_namespace

    def delete_namespace(self, name):
        return self.vn1_h.delete_namespace(name=name, body=client.V1DeleteOptions())
    # end delete_namespace

    def _get_metadata(self, mdata_dict):
        return client.V1ObjectMeta(**mdata_dict)

    def _get_ingress_backend(self, backend_dict={}):
        return client.V1beta1IngressBackend(backend_dict.get('service_name'),
                                            backend_dict.get('service_port'))

    def _get_ingress_path(self, http):
        paths = http.get('paths', [])
        path_objs = []
        for path_dict in paths:
            path_obj = client.V1beta1HTTPIngressPath(
                backend=self._get_ingress_backend(
                    path_dict.get('backend')),
                path=path_dict.get('path'))
            path_objs.append(path_obj)
        return path_objs
    # end _get_ingress_path

    def _get_ingress_rules(self, rules):
        ing_rules = []
        for rule in rules:
            rule_obj = client.V1beta1IngressRule(
                host=rule.get('host'),
                http=self._get_ingress_path(rule.get('http')))
            ing_rules.append(rule_obj)
        return ing_rules
    # end _get_ingress_rules

    def create_ingress(self,
                       namespace='default',
                       name=None,
                       metadata={},
                       default_backend={},
                       rules=[],
                       tls=[],
                       spec={}):
        '''
        Returns V1beta1Ingress object
        '''
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name
        spec['backend'] = self._get_ingress_backend(
            default_backend or spec.get('backend', {}))

        spec['rules'] = self._get_ingress_rules(rules or spec.get('rules', []))

        spec['tls'] = tls
        spec_obj = client.V1beta1IngressSpec(**spec)
        body = client.V1beta1Ingress(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Creating Ingress %s' % (metadata_obj.name))
        resp = self.v1_beta_h.create_namespaced_ingress(namespace, body)
        return resp
    # end create_ingress

    def delete_ingress(self,
                       namespace,
                       name):
        self.logger.info('Deleting Ingress : %s' % (name))
        body = client.V1DeleteOptions()
        return self.v1_beta_h.delete_namespaced_ingress(name, namespace, body)
    # end delete_ingress

    def create_service(self,
                       namespace='default',
                       name=None,
                       metadata={},
                       spec={}):
        '''
                Returns V1Service object
                Ex :
        metadata = {'name': 'xyz', 'namespace' : 'abc' }
                "spec": {
                        "selector": {
                                "app": "MyApp"
                        },
                        "ports": [
                                {
                                        "protocol": "TCP",
                                        "port": 80,
                                        "targetPort": 9376
                                }
                        ]
        '''
        #kind = 'Service'
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name
        spec_obj = client.V1ServiceSpec(**spec)
        body = client.V1Service(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Creating service %s' % (metadata_obj.name))
        resp = self.v1_h.create_namespaced_service(namespace, body)
        return resp
    # end create_service

    def delete_service(self,
                       namespace,
                       name):
        self.logger.info('Deleting service : %s' % (name))
        return self.v1_h.delete_namespaced_service(name, namespace)

    def create_pod(self,
                   namespace='default',
                   name=None,
                   metadata={},
                   spec={}):
        '''
        metadata : dict to create V1ObjectMeta {'name': 'xyz','namespace':'abc'}
        spec : dict to create V1PodSpec object
        Ex :        { 'containers' : [
                        { 'image' : 'busybox',
                          'command': ['sleep', '3600'],
                          'name' : 'busybox_container'
                          'image_pull_policy': 'IfNotPresent',
                        },
                     'restart_policy' : 'Always'
                    }
        namespace: Namespace in which POD to be created
        name: Name of the POD
        containers_list: List of dict specify the details of container.
                         format [{'pod_name':'value','image':'value'}]
        return V1Pod instance

        '''
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name
        spec_obj = self._get_pod_spec(metadata_obj.name, spec)
        body = client.V1Pod(metadata=metadata_obj,
                            spec=spec_obj)
        self.logger.info('Creating Pod %s' % (metadata_obj.name))
        resp = self.v1_h.create_namespaced_pod(namespace, body)
        return resp
    # end create_pod

    def delete_pod(self, namespace, name, grace_period_seconds=0, orphan_dependents=True):
        '''
        grace_period_seconds: Type  int , The duration in seconds before the object 
                              should be deleted. Value must be non-negative integer. 
                              The value zero indicates delete immediately. If this 
                              value is nil, the default grace period for the specified
                              type will be used. Defaults to a per object value if not
                              specified. zero means delete immediately. (optional)

        orphan_dependents:    Type bool | Should the dependent objects be orphaned. 
                              If true/false, the \"orphan\" finalizer will be added 
                              to/removed from the object's finalizers list. (optional)         
        '''
        body = client.V1DeleteOptions()
        self.logger.info('Deleting pod %s:%s' % (namespace, name))
        return self.v1_h.delete_namespaced_pod(name, namespace, body,
                                               grace_period_seconds=grace_period_seconds,
                                               orphan_dependents=orphan_dependents)

    def read_pod(self, name, namespace='default', exact=True, export=True):
        '''
        exact = Type bool | Should the export be exact.  Exact export maintains 
                            cluster-specific fields like 'Namespace' (optional)
        export = Type bool | Should this value be exported.  Export strips fields 
                            that a user can not specify. (optional)
        '''
        return self.v1_h.read_namespaced_pod(name, namespace, exact=exact,
                                             export=export)
    # end read_pod

    def _get_container(self, pod_name=None, kwargs={}):
        '''
        return container object
        '''
        if not kwargs.get('name'):
            kwargs['name'] = pod_name or get_random_name('container')
        ports_obj = []
        for item in kwargs.get('ports', []):
            ports_obj.append(client.V1ContainerPort(**item))
        kwargs['ports'] = ports_obj
        return client.V1Container(**kwargs)
    # end _get_container

    def _get_pod_spec(self, name, spec_dict):
        '''
        return V1PodSpec object
        '''
        container_objs = []
        containers = spec_dict.get('containers', [])
        for item in containers:
            container_name = '%s_%s' % (name, containers.index(item))
            container_objs.append(self._get_container(name, item))
        spec_dict['containers'] = container_objs
        spec = client.V1PodSpec(**spec_dict)
        return spec
    # end create_spec

    def get_pods(self, namespace='default', **kwargs):
        ''' Returns V1PodList
        '''
        return self.v1_h.list_namespaced_pod("default", **kwargs)

    def read_pod_status(self, name, namespace='default', exact=True, export=True):
        '''
        Get the POD status
        '''
        return self.v1_h.read_namespaced_pod_status(name, namespace)

    def exec_cmd_on_pod(self, name, cmd, namespace='default', stderr=True,
                        stdin=True, stdout=True, tty=True,
                        shell='/bin/bash -l -c'):

        cmd_prefix = shell.split()
        cmd_prefix.append(cmd)
        output = self.v1_h.connect_get_namespaced_pod_exec(name, namespace,
                                                           command=cmd_prefix,
                                                           stderr=stderr,
                                                           stdin=stdin,
                                                           stdout=stdout,
                                                           tty=tty)
        return output


if __name__ == '__main__':
    c1 = Client()
    pods = c1.get_pods()
    for pod in pods.items:
        print("%s\t%s\t%s" % (pod.metadata.name,
                              pod.status.phase,
                              pod.status.pod_ip))

    import pdb
    pdb.set_trace()
    ing1 = c1.create_ingress(name='test1',
                             default_backend={'service_name': 'my-nginx',
                                              'service_port': 80})
    import pdb
    pdb.set_trace()
