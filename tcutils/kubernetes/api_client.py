from kubernetes import client, config

from common import log_orig as contrail_logging

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

    def create_pod (self, namespace, name, containers_list):
        '''
        namespace: Namespace in which POD to be created 
        name: Name of the POD
        containers_list: List of dict specify the details of container. 
                         format [{'pod_name':'value','image':'value'}]
        return pod instance
        '''

        body = client.V1Pod() 
        body.metadata = client.V1ObjectMeta(name=name)
        
        container_obj_list = []
        for container  in containers_list:
             
            container_obj = self.create_container(container['pod_name'], container['image'])
            container_obj_list.append(container_obj)
        spec = self.create_spec(container_obj_list)
        body.spec = spec
        resp = self.v1_h.create_namespaced_pod(namespace, body) 
        return resp
    # end create_pod

    def delete_pod (self, namespace, name, grace_period_seconds=0, orphan_dependents=True):
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
        return self.v1_h.delete_namespaced_pod(name, namespace, body,
                                               grace_period_seconds=grace_period_seconds,\
                                               orphan_dependents=orphan_dependents)        

    def read_pod (self, name, namespace='default', exact=True, export=True):
        '''
        exact = Type bool | Should the export be exact.  Exact export maintains 
                            cluster-specific fields like 'Namespace' (optional)
        export = Type bool | Should this value be exported.  Export strips fields 
                            that a user can not specify. (optional)
        ''' 
        return self.v1_h.read_namespaced_pod(name, namespace, exact=exact,\
                                      export=export)

    def create_container (self, name,  image): 
        '''
        return container object 
        ''' 
        container = client.V1Container()
        container.image = image 
        container.name = name
        return container 
    # end create_container

    def create_spec (self, container_obj_list):
        '''
        return spec object 
        '''
        spec = client.V1PodSpec()
        spec.containers = container_obj_list
        return spec
    # end create_spec

        
    def get_pods(self, namespace='default', **kwargs):
        ''' Returns V1PodList
        '''
        return self.v1_h.list_namespaced_pod("default", **kwargs)
        

if __name__ == '__main__':
    c1 = Client()
    pods = c1.get_pods()
    for pod in pod_list.items:
        print("%s\t%s\t%s" % (pod.metadata.name,
                              pod.status.phase,
                              pod.status.pod_ip))
