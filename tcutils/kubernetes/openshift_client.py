import yaml
import time
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry
from tcutils.kubernetes import api_client
from kubernetes import client, config
from openshift.client.apis.oapi_api import OapiApi
from openshift.dynamic import DynamicClient
from openshift.client import ApiClient
from copy import deepcopy
import os

cwd=os.path.dirname(os.path.realpath(__file__))
Templates = {'namespace': '%s/templates/namespace.yaml'%cwd,
             'pod': '%s/templates/pod.yaml'%cwd,
             'network_policy': '%s/templates/network_policy.yaml'%cwd,
             'deployment': '%s/templates/deployment.yaml'%cwd,
             'service': '%s/templates/service.yaml'%cwd
            }
key_mapping = {
    "container_port": "containerPort",
    "ip_block": "ipBlock",
    "ip_allow": "ipAllow",
    "pod_selector": "podSelector",
    "namespace_selector": "namespaceSelector",
    "match_labels": "matchLabels",
    "policy_types": "policyTypes"
}

class Client(api_client.Client):
    def __init__(self, config_file='/etc/kubernetes/admin.conf', logger=None):
        super(Client, self).__init__(config_file, logger)
        #Creating Dynamic API client
        k8s_client = config.new_client_from_config(config_file)
        dyn_client = DynamicClient(k8s_client)
        self.pod_h = dyn_client.resources.get(api_version='v1', kind='Pod')
        self.namespace_h = dyn_client.resources.get(api_version='v1', kind='Namespace')
        self.network_policy_h = dyn_client.resources.get(api_version='v1', kind='NetworkPolicy')
        self.deployment_h = dyn_client.resources.get(api_version='v1', kind='Deployment')
        self.service_h = dyn_client.resources.get(api_version='v1', kind='Service')
        
    # end __init__

    def _replace_key(self, dct):
        if isinstance(dct, dict):
            for key, value in dct.iteritems():
                if key in key_mapping:
                    dct[key_mapping[key]] = self._replace_key(value)
                    del dct[key]
                else:
                    dct[key] = self._replace_key(value)
        elif isinstance(dct, list):
            for item in list(dct):
                dct.append(self._replace_key(item))
                dct.remove(item)
        return dct

    def _convert_unicode_to_ascii(self, str_in):
        return str_in.encode('ascii', 'ignore')

    def create_namespace(self, name, isolation=True):
        '''
        returns instance of class V1Namespace
        '''
        with open(Templates['namespace'], 'r') as fp:
            body = yaml.load(fp)
        if isolation:
            body['metadata']['annotations']={'opencontrail.org/isolation': 'true'}
        else:
            body['metadata']['annotations']={'opencontrail.org/isolation': 'false'}
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
            for container in spec['containers']:
                container['name'] = name
            modified_spec = deepcopy(spec)
            self._replace_key(modified_spec)
        else:
            modified_spec = spec
        self.logger.info('Creating Pod %s' % (name))
        body['spec'] = modified_spec
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

    def read_pod_status(self, name, namespace='default', exact=True, export=True):
        '''
        Get the POD status
        '''
        return self.pod_h.status.get(name, namespace)

    def update_network_policy(self,
                              policy_name,
                              namespace='default',
                              metadata=None,
                              spec=None,
                              **kwargs):
        '''
        Returns V1beta1NetworkPolicy object
        '''
        resp = self.network_policy_h.replace(self,
                              namespace='default',
                              name=None,
                              metadata=None,
                              spec=None,
                              **kwargs)
        return resp
    # end update_network_policy

    def create_network_policy(self,
                              namespace='default',
                              name=None,
                              metadata=None,
                              spec=None,
                              **kwargs):
        '''
        returns instance of class V1Namespace
        '''
       
        with open(Templates['network_policy'], 'r') as fp:
            body = yaml.load(fp)
        if metadata:
            body['metadata'] = metadata
        if namespace:
            body['metadata']['namespace'] = namespace
        if name:
            body['metadata']['name'] = name
        if spec:
            if 'pod_selector' in spec:
                if 'match_labels' in spec['pod_selector']:
                    for key, value in spec['pod_selector']['match_labels']:
                        key = self._convert_unicode_to_ascii(key)
                        value = self._convert_unicode_to_ascii(value)
                        del spec['pod_selector']['match_labels']
                        spec['pod_selector']['match_labels'] = {}
                        spec['pod_selector']['match_labels'][key] = value
                 
        modified_spec = deepcopy(spec)
        self._replace_key(modified_spec)
        body['spec'] = modified_spec 
        resp = self.network_policy_h.create(body=body,
                   namespace=namespace,
                   spec=modified_spec)
        return resp
    # end create_network_policy

    def delete_network_policy(self,
                              namespace,
                              name):
        self.logger.info('Deleting Network Policy : %s' % (name))
        return self.network_policy_h.delete(name=name, namespace=namespace)
    # end delete_network_policy

    def create_deployment(self,
                          namespace='default',
                          name=None,
                          metadata=None,
                          spec=None):
        '''
        Returns AppsV1beta1Deployment object
        '''
        if metadata is None: metadata = {}
        if spec is None:
            spec = {}
        else:
            modified_spec = deepcopy(spec)
            self._replace_key(modified_spec)
        with open(Templates['deployment'], 'r') as fp:
            body = yaml.load(fp)
        body['metadata'] = metadata
        body['spec']['template']['spec']['containers'] = modified_spec['template']['spec']['containers']
        if name:
            for container in  modified_spec['template']['spec']['containers']:
                container['name'] = name
            body['metadata']['name']=name
        self.logger.info('Creating Deployment %s' % (name))
        resp = self.deployment_h.create(body=body, namespace=namespace)
        return resp


    def delete_deployment(self, namespace,name):
        self.logger.info('Deleting Deployment : %s' % (name))
        return self.deployment_h.delete(name=name, namespace=namespace)
    # end delete_network_policy

    def create_service(self,
                       namespace='default',
                       name=None,
                       metadata=None,
                       spec=None):
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

        with open(Templates['service'], 'r') as fp:
            body = yaml.load(fp)
        if metadata:
            body['metadata'] = metadata
        if namespace:
            body['metadata']['namespace'] = namespace
        if name:
            body['metadata']['name'] = name
        if spec:
            modified_spec = deepcopy(spec)
            self._replace_key(modified_spec)
        else:
            modified_spec = spec
        self.logger.info('Creating Service %s' % (name))
        body['spec'] = modified_spec
        resp = self.service_h.create(body=body, namespace=namespace)
        return resp

    def delete_service(self,
                       namespace,
                       name):
        self.logger.info('Deleting service : %s' % (name))
        return self.service_h.delete(name=name, namespace=namespace) 
