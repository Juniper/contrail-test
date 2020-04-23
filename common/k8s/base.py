from common.base import GenericTestBase
from fabric.api import local, settings
import time
import re
import test
import ipaddress
import vnc_api_test
import uuid
from tcutils.util import get_random_name, retry
from tcutils.gevent_lib import exec_in_parallel
from tcutils.verification_util import *
from lxml import etree
from k8s.pod import PodFixture
from k8s.hbs import HbsFixture
from k8s.service import ServiceFixture
from k8s.ingress import IngressFixture
from k8s.namespace import NamespaceFixture
from k8s.tls_secret import TLSSecretFixture
from k8s.deployment import DeploymentFixture
from k8s.network_policy import NetworkPolicyFixture
from k8s.network_attachment import NetworkAttachmentFixture
from common.connections import ContrailConnections
from common import create_public_vn
from vn_test import VNFixture
import gevent

class BaseK8sTest(GenericTestBase, vnc_api_test.VncLibFixture):

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        """ cls.connections = ContrailConnections(cls.inputs,
                                              project_name=cls.inputs.admin_tenant,
                                              username=cls.inputs.admin_username,
                                              password=cls.inputs.admin_password,
                                              logger=cls.logger) """
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.logger = cls.connections.logger
        cls.setup_namespace_isolation = False
        cls.setup_custom_isolation = False
        cls.public_vn = create_public_vn.PublicVn(connections=cls.connections,
                                                  public_vn=cls.inputs.public_vn,
                                                  public_tenant=cls.inputs.admin_tenant,
                                                  logger=cls.logger,
                                                  fip_pool_name=cls.inputs.fip_pool_name,
                                                  api_option='contrail')
        cls.cluster_connections = []
        if cls.inputs.slave_orchestrator == 'kubernetes':
            for cluster in cls.inputs.k8s_clusters:
                cls.cluster_connections.append(ContrailConnections(
                    project_name=cluster['name'],
                    username=cls.inputs.admin_username,
                    password=cls.inputs.admin_password,
                    logger=cls.logger))
        # Hack: sunil/venky to relook when enabling nested multi-cluster tests
        cls._connections = cls.connections
        del cls.connections
        cls.connections = cls.get_connections
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseK8sTest, cls).tearDownClass()
    # end tearDownClass

    @property
    def get_connections(self):
        if self.cluster_connections:
            return self.cluster_connections[0]
        else:
            return self._connections

    def setup_http_service(self,
                           name=None,
                           namespace='default',
                           labels=None,
                           metadata=None,
                           spec=None,
                           type=None,
                           external_ips=None,
                           frontend_port=80,
                           nodePort=None,
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
        d1 =  {'protocol': 'TCP','port': int(frontend_port),'targetPort': int(backend_port) }
        if nodePort:
            d1['nodePort'] = int(nodePort)
        spec.update({
            'ports': [d1]
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
    #@classmethod
    def setup_namespace(self,
                        name=None,
                        isolation = None,
                        ip_fabric_snat = None,
                        ip_fabric_forwarding = None,
                        custom_isolation = False,
                        fq_network_name = None):
        isolation = isolation or self.setup_namespace_isolation
        if custom_isolation == False:
            vn_fq_name = None
        return self.useFixture(NamespaceFixture(
            connections=self.connections,
            name=name, isolation=isolation,
            ip_fabric_snat=ip_fabric_snat,
            ip_fabric_forwarding=ip_fabric_forwarding,
            custom_isolation = custom_isolation,
            fq_network_name = fq_network_name))
    # end create_namespace

    def setup_hbs(self, name=None,
                 namespace='default',
                 project_name='k8s-default',
                 domain_name='default-domain'):
        fq_name = [domain_name , project_name]
        return self.useFixture(HbsFixture(
                               connections=self.connections,
                               name=name, 
                               fqname=fq_name,
                               namespace=namespace))
    # end create_Hbs_Object
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
			compute_node_selector = None,
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
        if compute_node_selector:
           spec['node_selector'] = compute_node_selector
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
                          fq_network_name = {},
                          compute_node_selector=None):
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
        if compute_node_selector:
           spec['node_selector'] = compute_node_selector

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

    @retry(delay=2, tries=10)
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

    @retry(delay=2, tries=15)
    def validate_nginx_lb(self,
                          lb_pods,
                          service_ip,
                          test_pod=None,
                          host=None,
                          path='',
                          port='80',
                          nodePort=None,
                          barred_pods=None,
                          protocol=None,
                          cert=None,
                          expectation=True):
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
        if nodePort:
            port = nodePort
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

            if 0 not in hit.values() and expectation==True:
                self.logger.info('Responses seen from all pods, lb seems fine.'
                                 'Hits : %s' % (hit))
                return True
        if 0 in hit.values():
            if expectation==False:
                self.logger.info('As expected, responses not seen from pods'
                                 'Hits : %s' % (hit))
                return True
            else:
                self.logger.warn('No http hit seen for one or more pods.'
                   'Pls check. Hits: %s' % (hit))
                return False
        else:
            if expectation==False:
                self.logger.warn('Pods responding even if expectation was False'
                                 'Hits : %s' % (hit))
                return False
            else:
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
                    for k, v in from_item_dict.items():
                        if not ingress_pod_dict:
                            ingress_pod_dict = {'match_labels': {}}
                        ingress_pod_dict['match_labels'].update({k: v})
                        ingress_pod_selector = {
                            'pod_selector': ingress_pod_dict}

                    from_item_dict = from_item.get('namespace_selector') or {}
                    for k, v in from_item_dict.items():
                        if not ingress_ns_dict:
                            ingress_ns_dict = {'match_labels': {}}
                        ingress_ns_dict['match_labels'].update({k: v})
                        ingress_ns_selector = {
                            'namespace_selector': ingress_ns_dict}

                    from_item_dict = from_item.get('ip_block') or {}
                    for k, v in from_item_dict.items():
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
                    for k, v in to_item_dict.items():
                        if not egress_pod_dict:
                            egress_pod_dict = {'match_labels': {}}
                        egress_pod_dict['match_labels'].update({k: v})
                        egress_pod_selector = {
                            'pod_selector': egress_pod_dict}

                    to_item_dict = to_item.get('namespace_selector') or {}
                    for k, v in to_item_dict.items():
                        if not egress_ns_dict:
                            egress_ns_dict = {'match_labels': {}}
                        egress_ns_dict['match_labels'].update({k: v})
                        egress_ns_selector = {
                            'namespace_selector': egress_ns_dict}

                    to_item_dict = to_item.get('ip_block') or {}
                    for k, v in to_item_dict.items():
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
            for k, v in ingress_pods.items():
                ingress_pod_dict['match_labels'].update({k: v})
            ingress_pod_selector = {'pod_selector': ingress_pod_dict}

        if ingress_namespaces is not None:
            ingress_ns_dict = {'match_labels': {}}
            for k, v in ingress_namespaces.items():
                ingress_ns_dict['match_labels'].update({k: v})
            ingress_ns_selector = {'namespace_selector': ingress_ns_dict}

        if ingress_ipblock is not None:
            ingress_ipblock_selector = {'ip_block': ingress_ipblock}

        if egress_pods is not None:
            egress_pod_dict = {'match_labels': {}}
            for k, v in egress_pods.items():
                egress_pod_dict['match_labels'].update({k: v})
            egress_pod_selector = {'pod_selector': egress_pod_dict}

        if egress_namespaces is not None:
            egress_ns_dict = {'match_labels': {}}
            for k, v in egress_namespaces.items():
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
    def setup_daemonset(self,
                         name=None,
                         namespace='default',
                         metadata=None,
                         spec=None,
                         connections=None,
                         min_ready_seconds=None,
                         paused=None,
                         progress_deadline_seconds=None,
                         revision_history_limit=None,
                         rollback_to=None,
                         strategy=None,
                         template=None):
        '''
        A helper method to create a daemonset

        Ref https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1DaemonSet.md 

        '''
        metadata = metadata or {}
        spec = spec or {}
        name = name or get_random_name('ds-')
        metadata.update({'name': name})

        if min_ready_seconds:
            spec.update({'min_ready_seconds': min_ready_seconds})
        if paused:
            spec.update({'paused': paused})
        if progress_deadline_seconds:
            spec.update(
                {'progress_deadline_seconds': progress_deadline_seconds})
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
        if not connections:
           connection = connections
        else:
           connections = self.connections

        obj = self.useFixture(DaemonsetFixture(
            connections=connections,
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

            # below mandatory for Openshift_client and as being part of existing spec should work fine for K8s_client also
            selector_dict = {'match_labels': pod_labels}
            spec.update({'selector': selector_dict})
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
                                     verify_service=True)
        time.sleep(30)#wait time to stabilize the cluster
    # end restart_kube_manager

    def invalidate_kube_manager_inspect(self):
        if getattr(self.connections, '_kube_manager_inspect'):
            del self.connections._kube_manager_inspect

    def restart_vrouter_agent(self, ips=None):
        '''
        Restarts vrouter agent
        If no ips is specified, restarts all agents
        '''
        ips = ips or self.inputs.compute_ips

        self.logger.info('Will restart contrail-vrouter-agent  services now on'
            ' %s' %(ips))
        self.inputs.restart_service('contrail-vrouter-agent', ips,
                                     container='agent',
                                     verify_service=True)
    # end restart_vrouter_agent

    def restart_pod(self, pod_fixture):
        '''
        Restarts a specific container using docker restart
        '''
        host = pod_fixture.compute_ip
        username = self.inputs.host_data[host]['username']
        password = self.inputs.host_data[host]['password']
        cmd = "docker ps -f NAME=%s -f status=running 2>/dev/null | grep -v POD | sed -n 2p | awk '{print $1}'" \
                % (pod_fixture.name + "_" + pod_fixture.namespace)
        self.logger.info('Running %s on %s' %
                             (cmd, self.inputs.host_data[host]['name']))
        container_id = self.inputs.run_cmd_on_server(host, cmd, username, password,
                                                     as_sudo=True)
        if not container_id:
                self.logger.warn('Container cant be found on host')
                return False
        issue_cmd = 'docker restart %s -t 60' % (container_id)
        self.logger.info('Running %s on %s' %
                             (issue_cmd, self.inputs.host_data[host]['name']))
        self.inputs.run_cmd_on_server(host, issue_cmd, username, password, pty=True,
                                      as_sudo=True)
        verify_command = "docker ps -f NAME=%s -f status=running 2>/dev/null | grep -v POD" \
                         % (pod_fixture.name + "_" + pod_fixture.namespace)
        for i in range(3):
            output = self.inputs.run_cmd_on_server(host, verify_command, username,
                                                    password, as_sudo=True)
            if not output or 'Up' not in output:
                self.logger.warn('Container is not up on host %s'%(host))
                return False
            time.sleep(3)
        return True
    # end restart_pod

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
        router_obj = self.create_snat_router(get_random_name("snat_router"))

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
        connections = connections if connections else self.connections
        inputs = inputs if inputs else self.inputs
        #connections = self.connections
        #inputs =  self.inputs
        vn_name = vn_name or get_random_name('vn_test')
        return self.useFixture(VNFixture(
                                        connections=connections,
					project_name=project_name,
                                        inputs=inputs,
                                        vn_name=vn_name,
                                        option=option))

    def modify_cluster_project(self, project_name = None):
        """
        In case project isolation is disabled, it enables it.
        In case project isolation is enabled, it disables it.
        """
        cmd = 'grep "^[ \t]*cluster_project" /etc/contrail/contrail-kubernetes.conf'
        cp_line = self.inputs.run_cmd_on_server(self.inputs.kube_manager_ips[0],
                                                cmd, container='contrail-kube-manager')
        if cp_line:
            m = re.match('[ ]*cluster_project.*project(.*)', cp_line)
            if m:
                self.logger.debug("Cluster_project is set in this sanity run. "
                            "Resetting it for few tests to validate project isolation")
                project = m.group(1).strip("'\": }").split(",")[0].strip("'\"")
                cmd = 'sed -i "/^cluster_project/d" /entrypoint.sh'
                operation = "reset"
                no_match = False
            else:
                no_match = True
        if not cp_line or no_match:
            self.logger.debug("Cluster_project not set in this sanity run. "
                        "Setting it to default project for few tests")
            project = self.inputs.admin_tenant
            cmd = r'crudini --set /entrypoint.sh KUBERNETES cluster_project \\${KUBERNETES_CLUSTER_PROJECT:-\\"{\'domain\':\'default-domain\'\,\'project\':\'%s\'}\\"}'\
                  % project
            operation = "set"
        for kube_manager in self.inputs.kube_manager_ips:
            self.inputs.run_cmd_on_server(kube_manager, cmd,
                                          container='contrail-kube-manager',
                                          shell_prefix = None)
        self.restart_kube_manager()
        self.addCleanup(self.revert_cluster_project,
                         project_name = project,
                         operation = operation)
        return operation
    #end modify_cluster_project

    def revert_cluster_project(self, project_name = None, operation = None):
        """
        This method reverts the value of cluster_project after performing few
        sanity tests.
        """
        if operation =="set":
            self.logger.debug("Cluster_project need to be reverted to Null value"
                            "It was set to default project for few cases")
            cmd = r'crudini --set /entrypoint.sh KUBERNETES cluster_project \\${KUBERNETES_CLUSTER_PROJECT:-\\"{}\\"}'
        else:
            self.logger.debug("Cluster_project need to be reverted to a valid value"
                            "It was set to Null for few cases")
            cmd = r'crudini --set /entrypoint.sh KUBERNETES cluster_project \\${KUBERNETES_CLUSTER_PROJECT:-\\"{\'domain\':\'default-domain\'\,\'project\':\'%s\'}\\"}'\
              % project_name
        for kube_manager in self.inputs.kube_manager_ips:
            self.inputs.run_cmd_on_server(kube_manager, cmd,
                                          container='contrail-kube-manager',
                                          shell_prefix = None)
        self.restart_kube_manager()
        #cmd = r'sed  -i "/KUBERNETES/a cluster_project = {\\"project\\": \\"%s\\", \\"domain\\": \\"default-domain\\"}" /etc/contrail/contrail-kubernetes.conf' \
        #        % project_name
    #end revert_cluster_project
    @classmethod
    def setup_fabric_gw(cls):
        ''' Configures  underlay  Gateway
        '''
        if not cls.inputs.fabric_gw_info:
            return
        if len(cls.inputs.fabric_gw_info[0]) != 2:
            assert False, "Fabric Gateway details are incorrectly mentioned, Check yaml"
        cls.name = cls.inputs.fabric_gw_info[0][0]
        cls.ip = cls.inputs.fabric_gw_info[0][1]
        cls.af = ["inet"]
        assert cls.vnc_h.provision_bgp_router(cls.name, cls.ip, cls.inputs.router_asn, cls.af)
        time.sleep(40)
    #end setup_fabric_gw

    @classmethod
    def cleanup_fabric_gw(cls):
        ''' cleanup  underlay  Gateway
        '''
        if not cls.inputs.fabric_gw_info:
           return
        cls.name = cls.inputs.fabric_gw_info[0][0]
        cls.vnc_h.delete_bgp_router(cls.name)
    #end fabric_fabric_gw

    def delete_in_parallel(self, fixture_type_list):
        ''' Populates list of objects to be deleted parallely based on
            Fixture Type as input like VmFixture
            Then It deletes the objects in the list parallely
        '''
        parallel_cleanup_list = list()
        for fn in self._cleanups[:]:
            try:
                if fn[0].im_self.__class__.__name__ in fixture_type_list:
                    index = self._cleanups.index(fn)
                    parallel_cleanup_list.append(fn)
                    self._cleanups.pop(index)
            except AttributeError:
                pass
        if parallel_cleanup_list:
            greenlets = exec_in_parallel(parallel_cleanup_list)
            gevent.joinall(greenlets)
        else:
            self.logger.warn("Nothing to delete parallely")
            return

    def setup_csrx_pod(self,
                          name=None,
                          namespace='default',
                          metadata=None,
                          spec=None,
                          csrx_version='18.1R1.9',
                          labels=None):

        metadata = metadata or {}
        spec = spec or {}
        labels = labels or {}
        name = name or get_random_name('csrx-pod')

        pullsecret = 'secretcsrx'
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        docker_username = 'JNPR-CSRXFieldUser12'
        docker_password = 'd2VbRJ8xPhSUAwzo7Lym'
        #import pdb;pdb.set_trace()
        cmd = "kubectl create secret docker-registry %s " \
              "--docker-server=hub.juniper.net/security " \
              "--docker-username=%s --docker-password=%s" %(pullsecret , docker_username ,docker_password)
        secretoutput = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip, cmd, username, password,
                                                   as_sudo=True)
        getsecret = "kubectl get secret"
        secretkey = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip,\
                                                  getsecret, username, password, as_sudo=True)
        if pullsecret not in secretkey:
            self.logger.warn("Pull secret can't be created")
            return False

        spec = spec or {
            'containers': [
                {'image':'hub.juniper.net/security/csrx:'+csrx_version,
                 'image_pull_policy': 'IfNotPresent',
                 'stdin': True,
                 'tty': False,
                 'env': [{
                        "name": "CSRX_FORWARD_MODE",
                        "value": "routing" }],
                 'name':'csrx',
                 'security_context': {"privileged": True}
                }
            ],
            "image_pull_secrets": [{ "name": pullsecret}],
            'restart_policy': 'Always'
        }
        #spec['containers']['securityContext'] = {}
        #$spec['containers']['securityContext'].update({'privileged': 'true'})

        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec,
                              labels=labels,
                              shell='/bin/sh')

    def setup_cirros_pod(self,
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
        name = name or get_random_name('cirros')
        cname = get_random_name('container')
        spec = spec or  {
                'containers': [
                    {'image': 'cirros',
                      "name": cname
                    }
              ]
        }
        return self.setup_pod(name=name,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec,
                              labels=labels,
                              shell='/bin/sh',
                              custom_isolation = custom_isolation,
                              fq_network_name = fq_network_name)

    def setup_network_attachment(self,
                                 name=None,
                                 namespace='default',
                                 cidr=None,
                                 annotate=None,
                                 ip_fabric_snat=False,
                                 ip_fabric_forwarding=False,
                                 **kwargs):
        name = name or get_random_name('nad')
        metadata =  {} 
        spec = {}
        metadata["annotations"]={}
        spec["config"]={}
        metadata["name"] = name or get_random_name('net')
        if cidr:
           metadata["annotations"]["opencontrail.org/cidr"] = cidr
        if annotate:
           metadata["annotations"]["opencontrail.org/network"] = annotate
        if ip_fabric_forwarding :
           metadata["annotations"]["opencontrail.org/ip_fabric_forwarding"] = "True"
        if ip_fabric_snat:
           metadata["annotations"]["opencontrail.org/ip_fabric_snat"] = "True"

        spec = {
                "config":  '{ "cniVersion": "0.3.0", "type": "contrail-k8s-cni" }'
        }
        return self.useFixture(NetworkAttachmentFixture(
                              connections=self.connections,
                              namespace=namespace,
                              metadata=metadata,
                              spec=spec))
    # end setup_network_attachment
    def setup_csrx_daemonset(self,
                               name=None,
                               namespace='default',
                               pod_labels=None,
                               connections=None,
                               container_port=80,
                               metadata=None,
                               spec=None,
                               template_metadata=None,
                               template_spec=None):

        metadata = metadata or {}
        spec = spec or {}
        pod_labels = pod_labels or {}
        name = name or get_random_name('csrx-ds')
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
        return self.setup_daemonset(name=name,
                                     namespace=namespace,
                                     connections=connections,
                                     metadata=metadata,
                                     spec=spec)
    # end setup_nginx_deployment

    def verify_daemonset_status(self, namespace=''):
        '''
        Returns 
           True, if Desired and available are same for all daemonsets
           False, otherwise
        '''
        if namespace:
            daemonset_info = self.connections.k8s_client.read_daemonsets(namespace=namespace)
        else:
            daemonset_info = self.connections.k8s_client.read_daemonsets()
        for item in daemonset_info.items:
            item_status = item.status
            if item_status.desiredNumberScheduled == item_status.currentNumberScheduled == \
                item_status.numberReady == item_status.numberAvailable:
                continue
            self.logger.error('One or more daemonsets not in expected state')
            return False
        self.logger.info('All daemonsets are in expected states')
        return True

    def get_daemonset_status(self, namespace=''):
        if namespace:
            daemonset_info = self.connections.k8s_client.read_daemonsets(namespace=namespace)
        else:
            daemonset_info = self.connections.k8s_client.read_daemonsets()
        daemonset_status = {}
        for item in daemonset_info.items:
            daemonset_status[str(item.metadata.name)] = item.status
        return daemonset_status

    def get_daemonset_info(self, namespace='kube-system'):
        return self.connections.k8s_client.read_daemonsets(namespace=namespace)

    def verify_pods_status(self, namespace=''):
        '''
        Returns
          True, if all pods are in Running state
          False, otherwise
        '''
        if namespace:
            pods_info = self.connections.k8s_client.read_pods_namespace(namespace)
        else:
            pods_info = self.connections.k8s_client.read_pods_namespace()
        for pod in pods_info.items:
            if 'Running' in pod.status.phase:
                self.logger.info("Pod {} is in Running state".format(pod.metadata.name))
                continue
            self.logger.error("Pod {} is not in Running state".format(pod.metadata.name))
            return False
        return True

