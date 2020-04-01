from builtins import str
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

class AttributeDict(dict):
    '''
         To make nested dictionary accessible as object attributes as well 
    '''
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__

    def __deepcopy__(self, memo):
        y = {}
        memo[id(self)] = y
        for key, value in self.items():
            y[deepcopy(key, memo)] = deepcopy(value, memo)
        return y

def convert_to_attrdict(dct):
    if isinstance(dct, dict):
        for key, value in dct.items():
            val = convert_to_attrdict(value)
            if isinstance(val, dict):
                val = AttributeDict(val)
            elif isinstance(val, str):
                val = str(val)
            del dct[key]
            dct[str(key)] = val

    elif isinstance(dct, list):
        for idx,item in enumerate(list(dct)):
            val = convert_to_attrdict(item)
            if isinstance(val, dict):
                dct[idx] = AttributeDict(val)
            else:
                dct[idx] = val
    return dct

class Client(api_client.Client):
    '''
        Openshift API Client class
    '''
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
        self.daemonset_h = dyn_client.resources.get(api_version='v1', kind='DaemonSet')
    # end __init__

    def get_template(self, obj_type):
        with open(Templates[obj_type], 'r') as fp:
            body = yaml.load(fp)
        return body

    def _replace_key(self, dct):
        if isinstance(dct, dict):
            for key, value in dct.items():
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

    def create_namespace(self, name, isolation=False, ip_fabric_forwarding=False,
                         ip_fabric_snat=False, network_fqname=None):
        '''
            Creates new namespace and returns response
            returns: 
                ResourceInstance instance
        '''
        body = self.get_template('namespace')
        if isolation is True:
            body['metadata']['annotations'] = {'opencontrail.org/isolation': 'true'}
        if ip_fabric_forwarding is True:
            body['metadata']['annotations'] = {'opencontrail.org/ip_fabric_forwarding': 'true'}
        if ip_fabric_snat is True:
            body['metadata']['annotations'] = {'opencontrail.org/ip_fabric_snat': 'true'}
        if network_fqname is not None:
            body['metadata']['annotations'] = {'opencontrail.org/network': '%s'%network_fqname}
        body['metadata']['name'] = name
        resp = self.namespace_h.create(body=body)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp
    # end create_namespace

    def read_namespace(self, name):
        '''
        returns: 
            ResourceInstance instance
        '''
        resp = self.namespace_h.get(name=name)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp

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
        returns: 
            ResourceInstance instance

        '''
        body = self.get_template('pod')
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
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
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
        returns: 
            ResourceInstance instance
        '''
        resp = self.pod_h.get(name=name, namespace=namespace)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp
    # end read_pod

    def read_pod_status(self, name, namespace='default', exact=True, export=True):
        '''
        Get the POD status
        returns: 
            ResourceInstance instance
        '''
        resp = self.pod_h.status.get(name, namespace)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp

    def update_network_policy(self,
                              policy_name,
                              namespace='default',
                              metadata=None,
                              spec=None,
                              **kwargs):
        '''
        returns: 
            ResourceInstance instance
        '''
        resp = self.network_policy_h.replace(self,
                              namespace='default',
                              name=None,
                              metadata=None,
                              spec=None,
                              **kwargs)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp
    # end update_network_policy

    def create_network_policy(self,
                              namespace='default',
                              name=None,
                              metadata=None,
                              spec=None,
                              **kwargs):
        '''
        returns: 
            ResourceInstance instance
        '''
        body = self.get_template('network_policy')
        if metadata:
            body['metadata'] = metadata
        if namespace:
            body['metadata']['namespace'] = namespace
        if name:
            body['metadata']['name'] = name
        if spec:
            modified_spec = deepcopy(spec)
            self._replace_key(modified_spec)
            body['spec'] = modified_spec 
        resp = self.network_policy_h.create(body=body,
                   namespace=namespace)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
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
        returns: 
            ResourceInstance instance
        '''
        if metadata is None: metadata = {}
        if spec is None:
            spec = {}
        else:
            modified_spec = deepcopy(spec)
            self._replace_key(modified_spec)
        body = self.get_template('deployment')
        body['metadata'] = metadata
        body['spec']['template']['spec']['containers'] = modified_spec['template']['spec']['containers']

        ## Selector should not be empty and it has to match the template labels
        body['spec']['selector'] = modified_spec['selector']
        body['spec']['template']['metadata'] = modified_spec['template']['metadata']
        body['spec']['replicas'] =  modified_spec['replicas']

        if name:
            for container in  modified_spec['template']['spec']['containers']:
                container['name'] = name
            body['metadata']['name']=name
        self.logger.info('Creating Deployment %s' % (name))
        resp = self.deployment_h.create(body=body, namespace=namespace)
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
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
        returns: 
            ResourceInstance instance
        '''

        body = self.get_template('service')
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
        if resp:
            resp = AttributeDict(convert_to_attrdict(resp.to_dict()))
        return resp

    def delete_service(self,
                       namespace,
                       name):
        self.logger.info('Deleting service : %s' % (name))
        return self.service_h.delete(name=name, namespace=namespace) 

    def read_pods_namespace(self, namespace='default'):
        '''
        Get all pods in a given namespace
        returns: 
            ResourceInstance instance
        '''
        resp = self.pod_h.get(namespace=namespace)
        return resp

    def read_daemonsets(self, namespace=''):
        '''
        Returns daemon sets from the mentioned namespace. 
        returns: 
            ResourceInstance instance
        '''
        if namespace:
            resp = self.daemonset_h.get(namespace=namespace)
        else:
            resp = self.daemonset_h.get()
        return resp
