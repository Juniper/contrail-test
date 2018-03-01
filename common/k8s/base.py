from fabric.api import local, settings

import time
import re
import test
import ipaddress
import vnc_api_test
import uuid
from tcutils.util import get_random_name, retry
from k8s.pod import PodFixture
from k8s.service import ServiceFixture
from k8s.ingress import IngressFixture
from k8s.namespace import NamespaceFixture
from k8s.tls_secret import TLSSecretFixture
from k8s.deployment import DeploymentFixture
from k8s.network_policy import NetworkPolicyFixture
from common.connections import ContrailConnections
from common import create_public_vn
from common.base import _GenericTestBaseMethods
from vn_test import VNFixture


K8S_SERVICE_IPAM = ['default-domain', 'default', 'service-ipam']
K8S_PUBLIC_VN_NAME = '__public__'
K8S_PUBLIC_FIP_POOL_NAME = '__fip_pool_public__'


class BaseK8sTest(test.BaseTestCase, _GenericTestBaseMethods, vnc_api_test.VncLibFixture):

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        cls.connections = ContrailConnections(cls.inputs,
                                              project_name=cls.inputs.admin_tenant,
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
        cls.setup_namespace_isolation = False
        cls.setup_custom_isolation = False
        cls.public_vn = create_public_vn.PublicVn(connections=cls.connections,
                                                  public_vn=K8S_PUBLIC_VN_NAME,
                                                  public_tenant=cls.inputs.admin_tenant,
                                                  logger=cls.logger,
                                                  fip_pool_name=K8S_PUBLIC_FIP_POOL_NAME,
                                                  api_option='contrail')

    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseK8sTest, cls).tearDownClass()
    # end tearDownClass

    def setup_http_service(self,
                           name=None,
                           namespace='default',
                           labels=None,
                           metadata=None,
                           spec=None,
                           type=None,
                           external_ips=None,
                           frontend_port=80,
                           backend_port=80):
        '''
        A simple helper method to create a service

        Noticed that nginx continues to listen on port 80 even if target port
        is different. So, recommended not to change backend_port for now
        '''
        metadata = metadata or {}
        spec = spec or {}
        name = name or get_random_name('nginx-svc')
        metadata.update({'name': name})
        selector_dict = {}
        labels = labels or {}
        spec.update({
            'ports': [
                {
                    'protocol': 'TCP',
                    'port': int(frontend_port),
                    'targetPort': int(backend_port)
                }
            ]
        })
        if labels:
            selector_dict = {'selector': labels}
            spec.update(selector_dict)
        if type:
            type_dict = {'type': type}
            spec.update(type_dict)
        if external_ips:
            external_ips_dict = {'external_i_ps': external_ips}
            spec.update(external_ips_dict)

        return self.useFixture(ServiceFixture(
            connections=self.connections,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec))
    # end setup_http_service

    def setup_simple_nginx_ingress(self,
                                   service_name,
                                   name=None,
                                   namespace='default',
                                   service_port=80,
                                   **kwargs):
        default_backend = {'service_name': service_name,
                           'service_port': service_port}
        return self.setup_ingress(name=name,
                                  namespace=namespace,
                                  default_backend=default_backend,
                                  **kwargs)
    # end setup_simple_nginx_ingress

    def setup_ingress(self,
                      name=None,
                      namespace='default',
                      metadata=None,
                      default_backend=None,
                      rules=None,
                      spec=None,
                      **kwargs):
        '''
        A very basic helper method to create an ingress

        '''
        if metadata is None: metadata = {}
        if spec is None: spec = {}
        if default_backend is None: default_backend = {}
        if rules is None: rules = []
        tls = kwargs.get('tls', None)
        name = name or get_random_name('nginx-ingress')
        metadata.update({'name': name})
        if default_backend:
            spec.update({'backend': default_backend})
        if rules:
            spec.update({'rules': rules})
        if tls:
            spec.update({'tls': tls})

        return self.useFixture(IngressFixture(
            connections=self.connections,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
            tls=tls))
    # end setup_ingress

    def setup_namespace(self,
                        name=None,
                        isolation = None,
                        custom_isolation = False,
                        fq_network_name = None):
        isolation = isolation or self.setup_namespace_isolation
        if custom_isolation == False:
            vn_fq_name = None
        return self.useFixture(NamespaceFixture(
            connections=self.connections,
            name=name, isolation=isolation,
            custom_isolation = custom_isolation,
            fq_network_name = fq_network_name))
    # end create_namespace

    def setup_pod(self,
                  name=None,
                  namespace='default',
                  metadata=None,
                  spec=None,
                  labels=None,
                  custom_isolation = False,
                  fq_network_name = {},
                  **kwargs):
        name = name or get_random_name('pod')
        metadata = metadata or {}
        spec = spec or {}
        labels = labels or {}
        metadata['name'] = metadata.get('name') or name
        if labels:
            metadata['labels'] = metadata.get('labels', {})
            metadata['labels'].update(labels)
        return self.useFixture(PodFixture(
            connections=self.connections,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
            custom_isolation = custom_isolation,
            fq_network_name = fq_network_name,
            **kwargs))
    # end setup_pod

    def setup_nginx_pod(self,
                        name=None,
                        namespace='default',
                        metadata=None,
                        container_port=80,
                        labels=None,
                        spec=None,
                        custom_isolation = False,
                        fq_network_name = {}):
        '''
        Noticed that nginx continues to listen on port 80 even if target port
        (container_port) is different
        '''
        metadata = metadata or {}
        spec = spec or {}
        labels = labels or {}
        name = name or get_random_name('nginx-pod')
        if labels:
            metadata['labels'] = metadata.get('labels', {})
            metadata['labels'].update(labels)
        spec = spec or {
            'containers': [
                {'image': 'nginx',
                 'ports': [
                     {'container_port': int(container_port)}
                 ],
                 }
            ]
        }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec,
                              shell='/bin/bash',
                              custom_isolation = custom_isolation,
                              fq_network_name = fq_network_name)

    # end setup_nginx_pod

    def verify_nginx_pod(self, pod, path=None):
        result = pod.verify_on_setup()
        if result:
            if path:
                pod.run_cmd('echo %s > /usr/share/nginx/html/index.html' % (pod.name)) 
                cmd = "cp /usr/share/nginx/html/index.html /usr/share/nginx/html/%s" %(path)
                pod.run_cmd(cmd)
            else:
                pod.run_cmd('echo %s > /usr/share/nginx/html/index.html' % (
                pod.name))
        return result
    # end verify_nginx_pod

    def setup_busybox_pod(self,
                          name=None,
                          namespace='default',
                          metadata=None,
                          spec=None,
                          labels=None,
                          custom_isolation = False,
                          fq_network_name = {}):
        metadata = metadata or {}
        spec = spec or {}
        labels = labels or {}
        name = name or get_random_name('busybox-pod')
        spec = spec or {
            'containers': [
                {'image': 'busybox',
                 'command': ['sleep', '1000000'],
                 'image_pull_policy': 'IfNotPresent',
                 }
            ],
            'restart_policy': 'Always',
        }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec,
                              labels=labels,
                              shell='/bin/sh',
                              custom_isolation = custom_isolation,
                              fq_network_name = fq_network_name)
    # end setup_busybox_pod

    def setup_ubuntuapp_pod(self,
                          name=None,
                          namespace='default',
                          metadata=None,
                          spec=None,
                          labels=None):
        metadata = metadata or {}
        spec = spec or {}
        labels = labels or {}
        name = name or get_random_name('ubuntuapp-pod')
        spec = spec or {
            'containers': [
                {'image': 'ubuntu-upstart',
                 'command': ['sleep', '1000000'],
                 'image_pull_policy': 'IfNotPresent',
                 }
            ],
            'restart_policy': 'Always',
        }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec,
                              labels=labels,
                              shell='/bin/sh')
    # end setup_ubuntuapp_pod

    @retry(delay=1, tries=5)
    def validate_wget(self, pod, link, expectation=True, **kwargs):
        ret_val = self.do_wget(link, pod=pod, **kwargs)
        result = ret_val == expectation
        if result:
            self.logger.info('wget check of of %s from %s passed' % (link,
                                                                     pod.name))
        else:
            self.logger.warn('wget check of of %s from %s failed' % (link,
                                                                     pod.name))
        return result
    # end validate_wget

    def do_wget(self, link, pod=None, output_file='/dev/null', host='',
                timeout=5, return_output=False, tries=1,
                cert=None):
        '''
        Returns boolean by default
        Returns (boolean, output) if return_output is True
        '''
        host_str = ''
        cert_str = ''
        output = ''
        if host:
            host_str = '--header "Host:%s" ' % (host)
        if 'https' in link and not cert:
            cert_str = ' --no-check-certificate'
        cmd = 'wget %s %s -O %s -T %s -t %s %s' % (link, host_str, output_file,
                                                timeout, tries, cert_str)
        if not pod:
            with settings(warn_only=True):
                output = local(cmd, capture=True)
            pod_str = 'local'
        else:
            output = pod.run_cmd(cmd, shell='/bin/sh -l -c')
            pod_str = 'Pod %s' % (pod.name)
        if '100%' in output:
            self.logger.debug('[Pod %s] Cmd %s passed' % (pod_str, cmd))
            self.logger.debug('[Pod %s] Cmd output: %s' % (pod_str, output))
            result = True
        else:
            self.logger.debug('[Pod %s] Cmd %s failed. Output :%s' % (pod_str,
                                                                      cmd, output))
            self.logger.debug('[Pod %s] Cmd output: %s' % (pod_str, output))
            result = False
        if return_output:
            return (result, output)
        else:
            return result
    # end do_wget

    @retry(delay=1, tries=5)
    def validate_nginx_lb(self,
                          lb_pods,
                          service_ip,
                          test_pod=None,
                          host=None,
                          path='',
                          port='80',
                          barred_pods=None,
                          protocol=None,
                          cert=None):
        '''
        From test_pod , run wget on http://<service_ip>:<port> and check
        if the all the lb_pods respond to atleast one of the requests over
        3*len(lb_pods) attempts

        barred_pods : pods where the http requests should never be seen
        '''
        host_str = ''
        protocol = protocol or 'http'
        barred_pods = barred_pods or []
        attempts = len(lb_pods) * 5
        hit = {}
        hit_me_not = {}
        for x in lb_pods:
            hit[x.name] = 0
        for x in barred_pods:
            hit_me_not[x.name] = 0

        link = '%s://%s:%s/%s' % (protocol, service_ip, port, path)
        for i in range(0, attempts):
            (ret_val, output) = self.do_wget(link, pod=test_pod, host=host,
                                             output_file='-',
                                             return_output=True,
                                             cert=cert)
            for pod in lb_pods:
                if pod.name in output:
                    hit[pod.name] += 1

            for pod in barred_pods:
                if pod.name in output:
                    hit_me_not[pod.name] += 1
            if hit_me_not and 0 not in hit_me_not.values():
                self.logger.warn('HTTP request seem to have hit an unexpected '
                                 ' pod. Stats : %s' % (hit_me_not))
                return False

            if 0 not in hit.values():
                self.logger.info('Responses seen from all pods, lb seems fine.'
                                 'Hits : %s' % (hit))
                return True
        if 0 in hit.values():
            msg = ('No http hit seen for one or more pods.'
                   'Pls check. Hits: %s' % (hit))
            self.logger.warn(msg)
            return False
        self.logger.info('Nginx lb hits seem to be ok: %s' % (hit))
        return True
    # end validate_nginx_lb

    def setup_update_policy(self,
                            pod_selector=None,
                            name=None,
                            namespace='default',
                            metadata=None,
                            spec=None,
                            policy_types=None,
                            ingress=None,
                            egress=None,
                            update=False,
                            np_fixture=None):
        '''
        A helper method to create generic network policy
        Ex :
        ingress = [
            { 'from': [
                        { 'pod_selector': {'role': 'frontend' }
                        },
                        { 'namespace_selector': {'a': 'b' }
                        }
                      ],
              'ports': [ 'tcp/80', 'UDP/53' ]'
            },
            ...
            ...
        ]
        egress = [
            { 'to': 
                [
                    { 'pod_selector': {'role': 'temp' }
                        },
                    {'ip_block': 
                        {"cidr" : "1.2.3.4/24"},
                    },
                ],
            "ports" : [ 'tcp/80', 'UDP/53' ]
            },
            ...
            ...
        ]
        '''
        metadata = metadata or {}
        spec = spec or {}
        ingress = ingress or {}
        egress = egress or {}
        ingress_list = []
        egress_list = []
        name = name or get_random_name('np-')
        metadata.update({'name': name})
        selector_dict = {}
        pod_selector_dict = {}

        if pod_selector is not None:
            pod_selector_dict = {'match_labels': pod_selector}

        if ingress is not None:
            ingress_item_dict = {}
            for ingress_item in ingress:
                from_entries = []
                if ingress_item == {}:
                    ingress_list.append({})
                    break
                for from_item in ingress_item.get('from', {}):
                    ingress_pod_dict = {}
                    ingress_ns_dict = {}
                    ingress_ip_block_dict = {}
                    ingress_pod_selector = None
                    ingress_ns_selector = None
                    ingress_ip_block = None
                    
                    from_item_dict = from_item.get('pod_selector') or {}
                    for k, v in from_item_dict.iteritems():
                        if not ingress_pod_dict:
                            ingress_pod_dict = {'match_labels': {}}
                        ingress_pod_dict['match_labels'].update({k: v})
                        ingress_pod_selector = {
                            'pod_selector': ingress_pod_dict}

                    from_item_dict = from_item.get('namespace_selector') or {}
                    for k, v in from_item_dict.iteritems():
                        if not ingress_ns_dict:
                            ingress_ns_dict = {'match_labels': {}}
                        ingress_ns_dict['match_labels'].update({k: v})
                        ingress_ns_selector = {
                            'namespace_selector': ingress_ns_dict}

                    from_item_dict = from_item.get('ip_block') or {}
                    for k, v in from_item_dict.iteritems():
                        if not ingress_ip_block_dict:
                            ingress_ip_block_dict = {'cidr': ""}
                        if k == "cidr":
                            ingress_ip_block_dict.update({k: v})
                        if k == "_except":
                            ingress_ip_block_dict.update({k: v})
                    ingress_ip_block = {
                            'ip_block': ingress_ip_block_dict}
                    
                    from_entries.append(ingress_pod_selector or
                                        ingress_ns_selector or
                                        ingress_ip_block)
                # end for from_item

                port_list = []
                for port_str in ingress_item.get('ports', {}):
                    protocol, port = port_str.split('/')
                    port_list.append({'protocol': protocol, 'port': int(port)})
                # end for port_str
                if len(from_entries)>0:
                    ingress_item_dict = {'from': from_entries}
                if port_list:
                    ingress_item_dict.update({'ports': port_list})
                ingress_list.append(ingress_item_dict)

            # end for ingress_item
        # end if ingress
        if egress is not None:
            egress_item_dict = {}
            for egress_item in egress:
                to_entries = []
                if egress_item == {}:
                    egress_list.append({})
                    break
                
                for to_item in egress_item.get('to', {}):
                    egress_pod_dict = {}
                    egress_ns_dict = {}
                    egress_ip_block_dict = {}
                    egress_pod_selector = None
                    egress_ns_selector = None
                    egress_ip_block = None
                    
                    to_item_dict = to_item.get('pod_selector') or {}
                    for k, v in to_item_dict.iteritems():
                        if not egress_pod_dict:
                            egress_pod_dict = {'match_labels': {}}
                        egress_pod_dict['match_labels'].update({k: v})
                        egress_pod_selector = {
                            'pod_selector': egress_pod_dict}

                    to_item_dict = to_item.get('namespace_selector') or {}
                    for k, v in to_item_dict.iteritems():
                        if not egress_ns_dict:
                            egress_ns_dict = {'match_labels': {}}
                        egress_ns_dict['match_labels'].update({k: v})
                        egress_ns_selector = {
                            'namespace_selector': egress_ns_dict}
                        
                    to_item_dict = to_item.get('ip_block') or {}
                    for k, v in to_item_dict.iteritems():
                        if not egress_ip_block_dict:
                            egress_ip_block_dict = {'cidr': ""}
                        if k == "cidr":
                            egress_ip_block_dict.update({k: v})
                        if k == "_except":
                            egress_ip_block_dict.update({k: v})
                    egress_ip_block = {
                            'ip_block': egress_ip_block_dict}  
                    
                    to_entries.append(egress_pod_selector or 
                                      egress_ns_selector or
                                      egress_ip_block)
                # end for to_item

                port_list = []
                for port_str in egress_item.get('egress_ports', {}):
                    protocol, port = port_str.split('/')
                    port_list.append({'protocol': protocol, 'port': int(port)})
                # end for port_str
                if len(to_entries) > 0:
                    egress_item_dict = {'to': to_entries}
                if port_list:
                    egress_item_dict.update({'egress_ports': port_list})
                egress_list.append(egress_item_dict)
            # end for egress_item
        # end of egress
        
        if policy_types:
            spec['policy_types'] = policy_types
        if ingress:
            spec['ingress'] = ingress_list
        if egress:
            spec['egress'] = egress_list
        spec['pod_selector'] = pod_selector_dict

        if update == False:
            return self.useFixture(NetworkPolicyFixture(
                connections=self.connections,
                name=name,
                namespace=namespace,
                metadata=metadata,
                spec=spec))
        else:
            return np_fixture.update(metadata=np_fixture.metadata,
                          spec=spec)
    # end setup_policy

    def setup_update_simple_policy(self,
                            pod_selector=None,
                            name=None,
                            namespace='default',
                            metadata=None,
                            spec=None,
                            ingress_pods=None,
                            ingress_namespaces=None,
                            ingress_ipblock=None,
                            egress_pods=None,
                            egress_namespaces=None,
                            egress_ipblock=None,
                            ingress_all = False,
                            egress_all = False,
                            policy_types=None,
                            ports=None,
                            egress_ports=None,
                            update = False,
                            np_fixture = None):
        '''
        A simple helper method to create a network policy with a single
        ingress entry and a single from condition
        Ex :
        ingress_pod : { 'role': 'frontend'}
        ingress_namespace : { 'project': 'mynamespace'}
        ingress_ipblock : { "cidr" : "10.204.217.0/24", "_except" : ["10.204.217.4/30"] }
        egress_pod : { 'role': 'frontend'}
        egress_namespace : { 'project': 'mynamespace'}
        egress_ipblock : { "cidr" : "10.204.217.0/24"}
        ports = ['tcp/80']
        egress_ports = ['tcp/80']
        policy_types = ["Ingress"] or ["Egress"]

        '''
        metadata = metadata or {}
        spec = spec or {}
        
        ingress_pods = ingress_pods
        ingress_namespaces = ingress_namespaces
        ingress_ipblock = ingress_ipblock
        egress_pods = egress_pods
        egress_namespaces = egress_namespaces
        egress_ipblock = egress_ipblock
        ports = ports
        egress_ports = egress_ports
        
        ingress_pod_selector = None
        ingress_ns_selector = None
        ingress_ipblock_selector = None
        egress_pod_selector = None
        egress_ns_selector = None
        egress_ipblock_selector = None
        port_list = []
        egress_port_list = []
        
        name = name or get_random_name('np-')
        metadata.update({'name': name})
        selector_dict = {}
        pod_selector_dict = {}
        policy_types = policy_types

        if pod_selector is not None:
            pod_selector_dict = {'match_labels': pod_selector}

        if ingress_pods is not None:
            ingress_pod_dict = {'match_labels': {}}
            for k, v in ingress_pods.iteritems():
                ingress_pod_dict['match_labels'].update({k: v})
            ingress_pod_selector = {'pod_selector': ingress_pod_dict}

        if ingress_namespaces is not None:
            ingress_ns_dict = {'match_labels': {}}
            for k, v in ingress_namespaces.iteritems():
                ingress_ns_dict['match_labels'].update({k: v})
            ingress_ns_selector = {'namespace_selector': ingress_ns_dict}

        if ingress_ipblock is not None:
            ingress_ipblock_selector = {'ip_block': ingress_ipblock}
        
        if egress_pods is not None:
            egress_pod_dict = {'match_labels': {}}
            for k, v in egress_pods.iteritems():
                egress_pod_dict['match_labels'].update({k: v})
            egress_pod_selector = {'pod_selector': egress_pod_dict}

        if egress_namespaces is not None:
            egress_ns_dict = {'match_labels': {}}
            for k, v in egress_namespaces.iteritems():
                egress_ns_dict['match_labels'].update({k: v})
            egress_ns_selector = {'namespace_selector': egress_ns_dict}
            
        if egress_ipblock is not None:
            egress_ipblock_selector = {'ip_block': egress_ipblock}

        if ports is not None:
            for port_str in ports:
                protocol, port = port_str.split('/')
                port_list.append({'protocol': protocol, 'port': int(port)})
                
        if egress_ports is not None:
            for port_str in egress_ports:
                protocol, port = port_str.split('/')
                egress_port_list.append({'protocol': protocol, 'port': int(port)})

        if ingress_all == True:
            spec.update({
                'ingress': [{}]
                })
        elif ingress_pod_selector or ingress_ns_selector or ingress_ipblock_selector:
            spec.update({
                'ingress': [
                    {'from': [ingress_pod_selector or ingress_ns_selector or ingress_ipblock_selector],
                    }
                ]
            })
        elif egress_all == True:
            spec.update({
                'egress': [{}]
                })
        elif egress_pod_selector or egress_ns_selector or egress_ipblock_selector:
            spec.update({
                'egress': [
                    {'to': [egress_pod_selector or egress_ns_selector or egress_ipblock_selector],
                    }
                ]
            })
        #space
        spec.update({'pod_selector': pod_selector_dict})
        if ports is not None and (policy_types == ["Ingress"] or policy_types == [] ):
            spec['ingress'][0]['ports'] = port_list
        if egress_ports is not None and policy_types == ["Egress"]:
            spec['egress'][0]['egress_ports'] = egress_port_list
        if policy_types:
            spec["policy_types"] = policy_types
        #space
        if update == False:
            return self.useFixture(NetworkPolicyFixture(
                connections=self.connections,
                name=name,
                namespace=namespace,
                metadata=metadata,
                spec=spec))
        else:
            return np_fixture.update(metadata=np_fixture.metadata,
                          spec=spec)
    # end setup_simple_policy

    def setup_isolation(self, namespace_fixture):
        namespace_fixture.enable_isolation()
        self.addCleanup(namespace_fixture.disable_isolation)
    # end self.setup_isolation

    def setup_deployment(self,
                         name=None,
                         namespace='default',
                         metadata=None,
                         spec=None,
                         min_ready_seconds=None,
                         paused=None,
                         progress_deadline_seconds=None,
                         replicas=None,
                         revision_history_limit=None,
                         rollback_to=None,
                         strategy=None,
                         template=None):
        '''
        A helper method to create a deployment

        Ref https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/docs/AppsV1beta1DeploymentSpec.md

        '''
        metadata = metadata or {}
        spec = spec or {}
        name = name or get_random_name('dep-')
        metadata.update({'name': name})

        if min_ready_seconds:
            spec.update({'min_ready_seconds': min_ready_seconds})
        if paused:
            spec.update({'paused': paused})
        if progress_deadline_seconds:
            spec.update(
                {'progress_deadline_seconds': progress_deadline_seconds})
        if replicas:
            spec.update({'replicas': replicas})
        if revision_history_limit:
            spec.update({'revision_history_limit': revision_history_limit})
        if revision_history_limit:
            spec.update({'revision_history_limit': revision_history_limit})
        if rollback_to:
            spec.update({'rollback_to': rollback_to})
        if strategy:
            spec.update({'strategy': strategy})
        if template:
            spec.update({'template': template})

        obj = self.useFixture(DeploymentFixture(
            connections=self.connections,
            namespace=namespace,
            metadata=metadata,
            spec=spec))
        return obj
    # end setup_deployment

    def setup_nginx_deployment(self,
                               name=None,
                               namespace='default',
                               replicas=1,
                               pod_labels=None,
                               container_port=80,
                               metadata=None,
                               spec=None,
                               template_metadata=None,
                               template_spec=None):

        metadata = metadata or {}
        spec = spec or {}
        pod_labels = pod_labels or {}
        name = name or get_random_name('nginx-dep')
        template_metadata = template_metadata or {}

        if pod_labels:
            template_metadata['labels'] = template_metadata.get('labels', {})
            template_metadata['labels'].update(pod_labels)
        template_spec = template_spec or {
            'containers': [
                {'image': 'nginx',
                 'ports': [
                     {'container_port': int(container_port)}
                 ],
                 }
            ]
        }
        if replicas:
            spec.update({'replicas': replicas})
        spec.update({
            'template': {
                'metadata': template_metadata,
                'spec': template_spec
            }
        })
        return self.setup_deployment(name=name,
                                     namespace=namespace,
                                     metadata=metadata,
                                     spec=spec)
    # end setup_nginx_deployment

    def restart_kube_manager(self, ips=None):
        '''
        Restarts kube-managers
        If no ips is specified, restarts all kube-managers on all nodes
        '''
        ips = ips or self.inputs.kube_manager_ips

        self.logger.info('Will restart contrail-kube-manager  services now on'
            ' %s' %(ips))
        self.inputs.restart_service('contrail-kube-manager', ips,
                                     container='contrail-kube-manager',
                                     verify_service=False)
    # end restart_kube_manager

    def create_snat_router(self, name):

        obj =  self.connections.vnc_lib_fixture.vnc_h.create_router(name=name, 
                                          project_obj=self.connections.vnc_lib_fixture.get_project_obj())

        self.addCleanup(self.connections.vnc_lib_fixture.vnc_h.delete_router, obj)
        return obj 

    def connect_vn_with_router(self, router_obj, vn_fq_name):

        # Configure VN name from namespace

        # Read VN from API
        vn_fq_name_str = ':'.join(vn_fq_name)
        vn_obj=self.vnc_lib.virtual_network_read(fq_name_str=vn_fq_name_str)

        # To associate VN to logical router need to create a dummy port
        vmi_id = str(uuid.uuid4())
        vmi_obj = vnc_api_test.VirtualMachineInterface(name=vmi_id,
                                                       parent_obj=self.connections.vnc_lib_fixture.get_project_obj())
        vmi_obj.add_virtual_network(vn_obj)
        self.vnc_lib.virtual_machine_interface_create(vmi_obj)
        self.addCleanup(self.vnc_lib.virtual_machine_interface_delete, id=vmi_obj.uuid)

        # Connect namespace VN to router
        router_obj.add_virtual_machine_interface(vmi_obj)
        self.addCleanup(self._remove_namespace_from_router,router_obj,vmi_obj)

        # Update logical router object
        self.vnc_lib.logical_router_update(router_obj)

        return router_obj

    def _remove_namespace_from_router(self, router_obj, vmi_obj):
        router_obj.del_virtual_machine_interface(vmi_obj)
        # Update logical router object
        self.vnc_lib.logical_router_update(router_obj)
     

    def configure_snat_for_pod (self, pod):
  
        # Create logical router 
        router_obj = self.create_snat_router("snat_router")

        # Connect router with virtual network associated to pod 
        self.connect_vn_with_router(router_obj, pod.vn_fq_names[0])
 
        # Configure external_gateway
        self.connections.vnc_lib_fixture.vnc_h.connect_gateway_with_router(router_obj,\
                                                  self.public_vn.public_vn_fixture.obj)
    # end configure_snat_for_pod

    def verify_reachability(self, source_pod, dest_pods):
        '''
        Returns (boolean, list of booleans)
        '''
        results = []
        for dest_pod in dest_pods:
            result = source_pod.ping_with_certainty(dest_pod.pod_ip)
            results.append(result)
        final_result = all(results)
        return (final_result, results)
    # end verify_reachability

    def setup_tls_secret(self,
                  name=None,
                  namespace='default',
                  metadata=None,
                  data=None,
                  **kwargs):
        name = name or get_random_name('secret')
        metadata = metadata or {}
        data = data or {}
        metadata['name'] = metadata.get('name') or name
        return self.useFixture(TLSSecretFixture(
            connections=self.connections,
            namespace=namespace,
            metadata=metadata,
            data=data,
            **kwargs))
    # end setup_tls_secret
    
    def setup_vn(self, 
                 project_name = None,
                 connections = None,
                 inputs = None,
                 vn_name = None,
                 option = "contrail"):
        project_name = self.inputs.project_name,
        connections = self.connections
        inputs = self.inputs
        vn_name = vn_name or get_random_name('vn_test')
        return self.useFixture(VNFixture(project_name=project_name,
                                        connections=connections,
                                        inputs=inputs, 
                                        vn_name=vn_name,
                                        option=option))

    def delete_cluster_project(self):
        """
        This method is used to enable the project isolation by deleting the 
        definition of cluster_project from kubernetes.conf.
        It also returns the project it is deleting so that the same can be configured
        as part of cleanup
        """
        cmd = 'grep "^[ \t]*cluster_project" /etc/contrail/contrail-kubernetes.conf'
        cp_line = self.inputs.run_cmd_on_server(self.inputs.kube_manager_ips[0],
                                                cmd, container='contrail-kube-manager')
        if 'cluster_project' in cp_line:
            m = re.match('[ ]*cluster_project.*project(.*)', cp_line)
            if m:
                project = m.group(1).strip("'\": ").split(",")[0].strip("'\"")
                cmd = 'sed -i "/^cluster_project/d" /etc/contrail/contrail-kubernetes.conf'
                for kube_manager in self.inputs.kube_manager_ips:
                    self.inputs.run_cmd_on_server(kube_manager, cmd, 
                                              container='contrail-kube-manager')
            else:
                project = None
                return project
        else:
            self.logger.warn("cluster_project not set. Hence skipping delete")
            return
        self.restart_kube_manager()
        time.sleep(10)
        return project
    #end delete_cluster_project
    
    def add_cluster_project(self, project_name = None):
        """
        This method is used to add cluster_project in kubernetes.conf.
        This will inturn disable project level isolation as well.
        """
        if project_name ==None:
            self.logger.warn("No project to be added as cluster_project")
            return
        cmd = 'grep "^[ \t]*cluster_project" /etc/contrail/contrail-kubernetes.conf'
        cp_line = self.inputs.run_cmd_on_server(self.inputs.kube_manager_ips[0],
                                                cmd, container='contrail-kube-manager')
        if 'cluster_project' in cp_line:
            self.logger.warn("cluster_project already present in kubernetes.conf")
            return
        cmd = r'sed  -i "/KUBERNETES/a cluster_project = {\\"project\\": \\"%s\\", \\"domain\\": \\"default-domain\\"}" /etc/contrail/contrail-kubernetes.conf' \
                % project_name
        for kube_manager in self.inputs.kube_manager_ips:
            self.inputs.run_cmd_on_server(kube_manager, cmd, 
                                          container='contrail-kube-manager')
        self.restart_kube_manager()
        time.sleep(10)
    #end add_cluster_project

