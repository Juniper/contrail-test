import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class Client():

    def __init__(self, config_file='/etc/kubernetes/admin.conf', logger=None):
        self.api_client = config.new_client_from_config(config_file)
        self.api_client.config.assert_hostname = False
        self.v1_h = client.CoreV1Api(self.api_client)
        self.v1_h.read_namespace('default')
        self.v1_beta_h = client.ExtensionsV1beta1Api(self.api_client)
        self.apps_v1_beta1_h = client.AppsV1beta1Api(self.api_client)

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
        if mdata_dict:
            return client.V1ObjectMeta(**mdata_dict)

    def _get_ingress_backend(self, backend_dict={}):
        return client.V1beta1IngressBackend(backend_dict.get('service_name'),
                backend_dict.get('service_port', 80))

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
                http=client.V1beta1HTTPIngressRuleValue(
                     paths=self._get_ingress_path(rule.get('http'))))

            ing_rules.append(rule_obj)
        return ing_rules
    # end _get_ingress_rules

    def create_ingress(self,
                       namespace='default',
                       name=None,
                       metadata=None,
                       default_backend=None,
                       rules=None,
                       tls=None,
                       spec=None):
        '''
        Returns V1beta1Ingress object
        '''
        if metadata is None: metadata = {}
        if default_backend is None: default_backend = {}
        if rules is None: rules = []
        if tls is None: tls = []
        if spec is None: spec = {}
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name
        spec['backend'] = self._get_ingress_backend(
            default_backend or spec.get('backend', {}))

        spec['rules'] = self._get_ingress_rules(rules or spec.get('rules', []))

        spec['tls'] = self._get_ingress_tls(tls)
        spec_obj = client.V1beta1IngressSpec(**spec)
        body = client.V1beta1Ingress(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Creating Ingress %s' % (metadata_obj.name))
        resp = self.v1_beta_h.create_namespaced_ingress(namespace, body)
        return resp
    # end create_ingress

    def _get_ingress_tls(self, tls):
        tls_obj = []
        for tls_name in tls:
            tls_obj.append(client.V1beta1IngressTLS(secret_name=tls_name))
        return tls_obj
    # end _get_ingress_tls

    def delete_ingress(self,
                       namespace,
                       name):
        self.logger.info('Deleting Ingress : %s' % (name))
        body = client.V1DeleteOptions()
        return self.v1_beta_h.delete_namespaced_ingress(name, namespace, body)
    # end delete_ingress

    def _get_label_selector(self, match_labels={}, match_expressions=[]):
        # TODO match_expressions
        #return client.UnversionedLabelSelector(match_labels=match_labels)
        return client.V1LabelSelector(match_labels=match_labels)

    def _get_network_policy_peer_list(self, _from):
        peer_list = []
        for item in _from:
            pod_selector = item.get('pod_selector') or {}
            namespace_selector = item.get('namespace_selector') or {}
            pod_selector_obj = None
            namespace_selector_obj = None

            if pod_selector:
                pod_selector_obj = self._get_label_selector(**pod_selector)
            if namespace_selector:
                namespace_selector_obj = self._get_label_selector(
                    **namespace_selector)

            peer = client.V1beta1NetworkPolicyPeer(
                namespace_selector=namespace_selector_obj,
                pod_selector=pod_selector_obj)
            peer_list.append(peer)
        return peer_list
    # end _get_network_policy_peer_list

    def _get_network_policy_port(self, protocol, port):
        return client.V1beta1NetworkPolicyPort(port=port, protocol=protocol)

    def _get_network_policy_port_list(self, port_list):
        port_obj_list = []
        for port_dict in port_list:
            port_obj = self._get_network_policy_port(**port_dict)
            port_obj_list.append(port_obj)
        return port_obj_list
    # end _get_network_policy_port_list

    def _get_network_policy_spec(self, spec):
        ''' Return V1beta1NetworkPolicySpec
        '''
        ingress_rules = spec.get('ingress', [])
        ingress_rules_obj = []
        pod_selector = self._get_label_selector(**spec['pod_selector'])
        for rule in ingress_rules:
            _from = self._get_network_policy_peer_list(rule.get('from', []))
            ports = self._get_network_policy_port_list(rule.get('ports', []))
            ingress_rules_obj.append(
                client.V1beta1NetworkPolicyIngressRule(
                    _from=_from, ports=ports))
        return client.V1beta1NetworkPolicySpec(ingress=ingress_rules_obj,
                                               pod_selector=pod_selector)
    # end _get_network_policy_spec

    def update_network_policy(self,
                              policy_name,
                              namespace='default',
                              metadata=None,
                              spec=None):
        '''
        Returns V1beta1NetworkPolicy object
        '''
        if metadata is None: metadata = {}
        if spec is None: spec = {}
        policy_obj = self.v1_beta_h.read_namespaced_network_policy(
            policy_name, namespace)
        metadata_obj = self._get_metadata(metadata)

        spec_obj = self._get_network_policy_spec(spec)

        body = client.V1beta1NetworkPolicy(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Updating Network Policy %s' % (policy_name))
        resp = self.v1_beta_h.patch_namespaced_network_policy(policy_name,
                                                              namespace, body)
        return resp
    # end update_network_policy

    def create_network_policy(self,
                              namespace='default',
                              name=None,
                              metadata=None,
                              spec=None):
        '''
        spec = {
            'ingress' : [ { 'from': [
                                     { 'namespace_selector' :
                                         { 'match_labels' : {'project': 'test'} }
                                     },
                                     { 'pod_selector':
                                         { 'match_labels' : {'role': 'db'} }
                                     }
                                    ],
                            'ports': [
                                      { 'protocol' : 'tcp',
                                        'port' : 70,
                                      }
                                     ]
                          }
                      ]
               }

        Returns V1beta1NetworkPolicy object
        '''
        if metadata is None: metadata = {}
        if spec is None: spec = {}
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name

        spec_obj = self._get_network_policy_spec(spec)

        body = client.V1beta1NetworkPolicy(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Creating Network Policy %s' % (metadata_obj.name))
        resp = self.v1_beta_h.create_namespaced_network_policy(namespace, body)
        return resp
    # end create_network_policy

    def delete_network_policy(self,
                              namespace,
                              name):
        self.logger.info('Deleting Network Policy : %s' % (name))
        body = client.V1DeleteOptions()
        return self.v1_beta_h.delete_namespaced_network_policy(name, namespace,
                                                               body)
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
        #kind = 'Service'
        if metadata is None: metadata = {}
        if spec is None: spec = {}
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
        if metadata is None: metadata = {}
        if spec is None: spec = {}
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
        body = client.V1DeleteOptions()
        self.logger.info('Deleting pod %s:%s' % (namespace, name))
        return self.v1_h.delete_namespaced_pod(name, namespace, body,
                                               grace_period_seconds=grace_period_seconds,
                                               orphan_dependents=orphan_dependents)

    def read_pod(self, name, namespace='default'):
        '''
        exact = Type bool | Should the export be exact.  Exact export maintains 
                            cluster-specific fields like 'Namespace' (optional)
        export = Type bool | Should this value be exported.  Export strips fields 
                            that a user can not specify. (optional)
        '''
        return self.v1_h.read_namespaced_pod(name, namespace)
    # end read_pod

    def _get_container(self, pod_name=None, kwargs=None):
        '''
        return container object
        '''
        kwargs = kwargs or {}
        if not kwargs.get('name'):
            kwargs['name'] = pod_name or get_random_name('container')
        ports_obj = []
        for item in kwargs.get('ports', []):
            ports_obj.append(client.V1ContainerPort(**item))
        kwargs['ports'] = ports_obj
        return client.V1Container(**kwargs)
    # end _get_container

    def _get_pod_spec(self, name=None, spec=None):
        '''
        return V1PodSpec object
        '''
        container_objs = []
        container_name = None
        containers = spec.get('containers', [])
        for item in containers:
            if name:
                container_name = '%s-%s' % (name, containers.index(item))
            container_objs.append(self._get_container(container_name, item))
        spec['containers'] = container_objs
        spec_obj = client.V1PodSpec(**spec)
        return spec
    # end create_spec

    def get_pods(self, namespace='default', **kwargs):
        ''' Returns V1PodList
        '''
        return self.v1_h.list_namespaced_pod(namespace, **kwargs)

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
    # end exec_cmd_on_pod

    def set_isolation(self, namespace, enable=True):
        ns_obj = self.v1_h.read_namespace(namespace)
        if not getattr(ns_obj.metadata, 'annotations', None):
            ns_obj.metadata.annotations = {}
        kv = {'net.beta.kubernetes.io/network-policy': '{"ingress": { "isolation": "DefaultDeny" }}'}
        if enable:
            ns_obj.metadata.annotations.update(kv)
        else:
            ns_obj.metadata.annotations[
                'net.beta.kubernetes.io/network-policy'] = None
        self.v1_h.patch_namespace(namespace, ns_obj)
    # end set_isolation

    def _wa_client_bug_18_for_ingress(self, obj):
        '''
        Dirty WA https://github.com/kubernetes-incubator/client-python/issues/18
        '''
        default_backend = obj.spec.backend
        if default_backend:
            default_backend.service_port = int(default_backend.service_port)
        if obj.spec.rules:
            for rule in obj.spec.rules:
                if not rule or not rule.http or rule.http.paths:
                    continue
                for path in rule.http.paths:
                    path.backend.service_port = int(path.backend.service_port)
        return obj
    # end _wa_client_bug_18_for_ingress

    def set_ingress_tls(self, name, namespace, tls=None):
        '''
        ingress : name of ingress objec
        if tls is None: it will be disabled
        '''
        tls = tls or []
        ing_obj = self.v1_beta_h.read_namespaced_ingress(name, namespace)
        ing_obj.spec.tls = self._get_ingress_tls(tls)
        self._wa_client_bug_18_for_ingress(ing_obj)

        return self.v1_beta_h.patch_namespaced_ingress(ing_obj.metadata.name,
                namespace, ing_obj)
    # end set_ingress_tls

    def set_pod_label(self, namespace, pod_name, label_dict):
        metadata = {'labels': label_dict}
        body = client.V1Pod(metadata=self._get_metadata(metadata))
        return self.v1_h.patch_namespaced_pod(pod_name, namespace, body)
    # end set_pod_label

    def set_namespace_label(self, namespace, label_dict):
        metadata = {'labels': label_dict}
        body = client.V1Namespace(metadata=self._get_metadata(metadata))
        return self.v1_h.patch_namespace(namespace, body)
    # end set_namespace_label

    def is_namespace_present(self, namespace):
        try:
            self.v1_h.read_namespace(namespace)
            return True
        except ApiException:
            return False
    # end is_namespace_present

    def _get_rollback_config(self, rollback_to=None):
        if rollback_to:
            return client.AppsV1beta1RollbackConfig(rollback_to)

    def _get_r_u_deployment(self, rolling_update):
        if rolling_update:
            return client.AppsV1beta1RollingUpdateDeployment(
                max_surge=rolling_update.get('max_surge'),
                max_unavailable=rolling_update.get('max_unavailable'))

    def _get_deploment_strategy(self, strategy):
        if strategy:
            rolling_update_obj = self._get_r_u_deployment(
                strategy.get('rolling_update', {}))
            return rolling_update_obj

    def _get_pod_metadata(self, metadata_dict):
        if metadata_dict:
            return client.V1ObjectMeta(metadata_dict)

    def _get_pod_template(self, template):
        if template:
            metadata = self._get_metadata(template.get('metadata'))
            spec = self._get_pod_spec(spec=template.get('spec', {}))
            return client.V1PodTemplateSpec(metadata=metadata, spec=spec)
    # end _get_pod_template

    def _get_deployment_spec(self, spec_dict):
        if not spec_dict:
            return None
        replicas = spec_dict.get('replicas')
        min_ready_seconds = spec_dict.get('min_ready_seconds')
        paused = spec_dict.get('paused')
        progress_deadline_seconds = spec_dict.get('progress_deadline_seconds')
        revision_history_limit = spec_dict.get('revision_history_limit')
        rollback_to = self._get_rollback_config(spec_dict.get('rollback_to'))
        strategy = self._get_deploment_strategy(spec_dict.get('strategy'))
        template = self._get_pod_template(spec_dict.get('template'))

        spec_obj = client.AppsV1beta1DeploymentSpec(
            min_ready_seconds=min_ready_seconds,
            paused=paused,
            progress_deadline_seconds=progress_deadline_seconds,
            replicas=replicas,
            revision_history_limit=revision_history_limit,
            rollback_to=rollback_to,
            strategy=strategy,
            template=template)
        return spec_obj
    # end _get_deployment_spec

    def create_deployment(self,
                          namespace='default',
                          name=None,
                          metadata=None,
                          spec=None):
        '''
        Returns AppsV1beta1Deployment object
        '''
        if metadata is None: metadata = {}
        if spec is None: spec = {}
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name

        spec_obj = self._get_deployment_spec(spec)
        body = client.AppsV1beta1Deployment(
            metadata=metadata_obj,
            spec=spec_obj)
        self.logger.info('Creating Deployment %s' % (metadata_obj.name))
        resp = self.apps_v1_beta1_h.create_namespaced_deployment(namespace, body)
        return resp
    # end create_deployment

    def delete_deployment(self,
                       namespace,
                       name):
        self.logger.info('Deleting Deployment : %s' % (name))
        body = client.V1DeleteOptions()
        return self.apps_v1_beta1_h.delete_namespaced_deployment(name,
            namespace, body, orphan_dependents=False)
    # end delete_deployment

    def set_deployment_replicas(self, namespace, deployment, count=0):
        self.logger.info('Setting replicas of deployment %s to %s' %(
            deployment, count))
        dep_obj = self.v1_beta_h.read_namespaced_deployment(deployment,
                                                            namespace)
        dep_obj.spec.replicas = count
        return self.v1_beta_h.patch_namespaced_deployment(deployment,
            namespace, dep_obj)
        time.sleep(10)
    # end set_deployment_replicas

    def get_replica_set(self, namespace, deployment=None):
        rs_objs = self.v1_beta_h.list_namespaced_replica_set(namespace)
        ret_list = []
        for rs_obj in rs_objs.items:
            if not deployment:
                ret_list.append(rs_obj)
            elif deployment in rs_obj.metadata.name:
                ret_list.append(rs_obj)
        return ret_list
    # end get_replica_set

    def get_pods_list(self, namespace, replica_set=None, deployment=None):
        '''replica_set : name of the replica set which match with the pods
        '''
        pods = self.v1_h.list_namespaced_pod(namespace)
        ret_list = []
        replica_sets = []
        if deployment:
            rs_objs = self.get_replica_set(namespace, deployment)
            replica_sets = [x.metadata.name for x in rs_objs]
        elif replica_set:
            replica_sets = [replica_set]
        else:
            return pods.items
        for pod in pods.items:
            for rs in replica_sets:
                if rs in pod.metadata.name:
                    ret_list.append(pod)
        return ret_list
    # end get_pods_list


    @retry(delay=3, tries=20)
    def wait_till_pod_cleanup(self, namespace, replica_set=None):
        if self.get_pods_list(namespace, replica_set):
            self.logger.debug('One or more pods still in replica set..waiting')
            return False
        else:
            self.logger.debug('No pods managed by replica set %s' %(replica_set))
            return True
    # end wait_till_pod_cleanup

    def delete_replica_set(self, namespace, deployment=None):
        '''
        Delete a replica set in a deployment
        To ensure cases where pods dont end up being cleaned ,
        this set the replica count of deployment to 0, waits for the pods to 
        go away and then delete the rs
        '''
        self.logger.info('Deleting replica set of deployment %s' %(deployment))
        body = client.V1DeleteOptions()
        self.set_deployment_replicas(namespace, deployment, 0)
        rs_objs = self.get_replica_set(namespace, deployment)
        for rs_obj in rs_objs:
            name = rs_obj.metadata.name
            self.wait_till_pod_cleanup(namespace, name)
            self.v1_beta_h.delete_namespaced_replica_set(name, namespace, body,
                orphan_dependents=False)
    # end delete_replica_set 

    def set_service_isolation(self, namespace, enable=True):
        ns_obj = self.v1_h.read_namespace(namespace)
        if not getattr(ns_obj.metadata, 'annotations', None):
            ns_obj.metadata.annotations = {}
        if enable:
            kv = {'opencontrail.org/isolation.service': 'true'}
        else:
            kv = {'opencontrail.org/isolation.service': 'false'}
        ns_obj.metadata.annotations.update(kv)
        self.v1_h.patch_namespace(namespace, ns_obj)
    # end set_service_isolation


    def create_secret(self,
                       namespace='default',
                       name=None,
                       metadata=None,
                       data=None):
        '''
        Returns V1Secret object
        Ex :
        metadata = {'name': 'xyz', 'namespace' : 'abc' }
        "secret": {
                "data": {
                    'tls.crt' : <>,
                    'tls.key' : <>,
                },
        '''
        kind = 'Secret'
        obj_type = 'kubernetes.io/tls'
        if metadata is None: metadata = {}
        if data is None: data = {}
        metadata_obj = self._get_metadata(metadata)
        if name:
            metadata_obj.name = name
        body = client.V1Secret(
            metadata=metadata_obj,
            data=data,
            kind=kind,
            type=obj_type)
        self.logger.info('Creating secret %s' % (metadata_obj.name))
        resp = self.v1_h.create_namespaced_secret(namespace, body)
        return resp
    # end create_secret

    def delete_secret(self,
                      namespace,
                      name):
        self.logger.info('Deleting secret : %s' % (name))
        body = client.V1DeleteOptions()
        return self.v1_h.delete_namespaced_secret(name, namespace, body)
    # end delete_secret

if __name__ == '__main__':
    c1 = Client()
    pods = c1.get_pods()
    for pod in pods.items:
        print("%s\t%s\t%s" % (pod.metadata.name,
                              pod.status.phase,
                              pod.status.pod_ip))

    import pdb
    pdb.set_trace()
    dep = c1.create_deployment(
        metadata={'name': 'test-deployment'},
        spec={
            'replicas': 3,
            'template': {
                'metadata': {
                    'labels': {
                        'app': 'nginx'
                    }
                },
                'spec': {
                    'containers': [
                        { 'image': 'nginx:1.7.9' }
                    ]
                }
            }
        })
    import pdb; pdb.set_trace()


#    ing1 = c1.create_ingress(name='test1',
#                             default_backend={'service_name': 'my-nginx',
#                                              'service_port': 80})
#    import pdb
#    pdb.set_trace()
#    pol = c1.create_network_policy(
#        name='test4',
#        spec={
#            'pod_selector': {'match_labels': {'role': 'db'}},
#            'ingress': [
#                {
#                    'from': [
#                        {'pod_selector': {'match_labels': {'role': 'frontend'}}
#                         }
#                    ],
#                    'ports': [{'protocol': 'tcp', 'port': '30'}]
#                }
#            ]
#        })

    import pdb
    pdb.set_trace()
