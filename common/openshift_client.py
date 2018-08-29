import yaml
import time
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry
from tcutils.kubernetes import api_client
from kubernetes import client, config
from openshift.dynamic import DynamicClient
import os

cwd=os.path.dirname(os.path.realpath(__file__))
Templates = {'namespace': '%s/templates/namespace.yaml'%cwd,
             'pod': '%s/templates/pod.yaml'%cwd
            }

class Client(api_client.Client):
    def __init__(self, config_file='/etc/kubernetes/admin.conf', logger=None):
        super(Client, self).__init__(config_file, logger)
        #Creating Dynamic API client
        k8s_client = config.new_client_from_config(config_file)
        dyn_client = DynamicClient(k8s_client)
        self.pod_h = dyn_client.resources.get(api_version='v1', kind='Pod')
        self.namespace_h = dyn_client.resources.get(api_version='v1', kind='Namespace')
    # end __init__

    def create_namespace(self, name):
        '''
        returns instance of class V1Namespace
        '''
        with open(Templates['namespace'], 'r') as fp:
            body = yaml.load(fp)
        body['metadata']['name'] = name
        resp = self.namespace_h.create(body=body)
        return resp
    # end create_namespace

    def delete_namespace(self, name):
        return self.namespace_h.delete(name=name)
    # end delete_namespace

    def create_pod(self,
                   namespace='default',
                   name=None,
                   metadata=None,
                   spec=None):
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
        with open(Templates['pod'], 'r') as fp:
            body = yaml.load(fp)
        if metadata:
            body['metadata'] = metadata
        if namespace:
            body['metadata']['namespace'] = namespace
        if name:
            body['metadata']['name'] = name
        if spec:
            body['spec'] = spec
        if 'ports' in body['spec']['containers'][0].keys():
            body['spec']['containers'][0]['ports'][0]['containerPort'] = body['spec']['containers'][0]['ports'][0]['container_port']
        self.logger.info('Creating Pod %s' % (name))
        resp = self.pod_h.create(body=body)
        return resp
    # end create_pod

    def delete_pod(self, namespace, name, grace_period_seconds=0, orphan_dependents=False):
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
        self.logger.info('Deleting pod %s:%s' % (namespace, name))
        return self.pod_h.delete(name, namespace,
                                 grace_period_seconds=grace_period_seconds,
                                 orphan_dependents=orphan_dependents)

    def read_pod(self, name, namespace='default'):
        '''
        exact = Type bool | Should the export be exact.  Exact export maintains 
                            cluster-specific fields like 'Namespace' (optional)
        export = Type bool | Should this value be exported.  Export strips fields 
                            that a user can not specify. (optional)
        '''
        return self.pod_h.get(name=name, namespace=namespace)
    # end read_pod

    def get_pods(self, namespace='default', **kwargs):
        ''' Returns V1PodList
        '''
        return self.v1_h.list_namespaced_pod(namespace, **kwargs)

    def read_pod_status(self, name, namespace='default', exact=True, export=True):
        '''
        Get the POD status
        '''
        return self.pod_h.status.get(name, namespace)

