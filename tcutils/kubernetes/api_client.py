from kubernetes import client, config

from common import log_orig as contrail_logging
from tcutils.util import get_random_name


class Client():

    def __init__(self, config_file='/etc/kubernetes/admin.conf', logger=None):
        config.load_kube_config(config_file='/etc/kubernetes/admin.conf')
        self.v1_h = client.CoreV1Api()

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
        self.logger.info('Creating service %s' %(metadata_obj.name))
        resp = self.v1_h.create_namespaced_service(namespace, body)
        return resp
    # end create_service

    def delete_service(self,
                       namespace,
                       name):
        self.logger.info('Deleting service : %s' %(name))
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
        self.logger.info('Deleting pod %s:%s' %(namespace, name))
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

    def read_pod_status (self, name, namespace='default', exact=True, export=True):
        '''
        Get the POD status
        '''
        return self.v1_h.read_namespaced_pod_status(name, namespace)

    def exec_cmd_on_pod (self, name, cmd, namespace='default', stderr=True,
                         stdin=True, stdout=True, tty=True):

        output  = self.v1_h.connect_get_namespaced_pod_exec(name, namespace,  
                                                        command=cmd,
                                                        stderr=stderr,
                                                        stdin=stdin,
                                                        stdout=stdout,
                                                        tty=tty)
        return output


if __name__ == '__main__':
    c1 = Client()
    pods = c1.get_pods()
    for pod in pod_list.items:
        print("%s\t%s\t%s" % (pod.metadata.name,
                              pod.status.phase,
                              pod.status.pod_ip))
