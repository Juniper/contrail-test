from builtins import object
import os

from vnc_api_test import *
from tcutils.config.vnc_introspect_utils import *
from tcutils.config.svc_mon_introspect_utils import SvcMonInspect
from tcutils.control.cn_introspect_utils import *
from tcutils.agent.vna_introspect_utils import *
from tcutils.collector.opserver_introspect_utils import *
from tcutils.collector.analytics_tests import *
from tcutils.go.go_server_utils import *
from tcutils.collector.policy_generator_tests import PolicyGeneratorClient

from tcutils.kubernetes.k8s_introspect_utils import KubeManagerInspect
from vnc_api.vnc_api import *
from tcutils.vdns.dns_introspect_utils import DnsAgentInspect
from tcutils.util import custom_dict, get_plain_uuid
from openstack import OpenstackAuth, OpenstackOrchestrator
from vcenter import VcenterAuth, VcenterOrchestrator
from vro import VroWorkflows
from common.contrail_test_init import ContrailTestInit
from vcenter_gateway import VcenterGatewayOrch
from tcutils.util import retry
try:
    from tcutils.kubernetes.api_client import Client as Kubernetes_client
except ImportError:
    pass
try:
    from tcutils.kubernetes.openshift_client import Client as Openshift_client
except ImportError:
    pass

try:
    from webui.ui_login import UILogin
except ImportError:
    pass

class ContrailConnections(object):
    def __init__(self, inputs=None, logger=None, project_name=None,
                 username=None, password=None, domain_name=None, input_file=None, domain_obj=None,scope='domain'):
        self.inputs = inputs or ContrailTestInit(input_file,
                                stack_tenant=project_name)
        self.project_name = project_name or self.inputs.project_name
        self.domain_name = domain_name or self.inputs.domain_name
        self.orch_domain_name = domain_name or self.inputs.domain_name
        if self.orch_domain_name == 'Default':
            self.domain_name = 'default-domain'
        self.scope = scope
        self.username = username or self.inputs.stack_user
        self.password = password or self.inputs.stack_password
        self.logger = logger or self.inputs.logger
        self.nova_h = None
        self.quantum_h = None
        self.vnc_lib_fixture = None
        self.ironic_h = None
        self.api_server_inspects = custom_dict(self.get_api_inspect_handle,
                        'api_inspect:'+self.project_name+':'+self.username)
        self.dnsagent_inspect = custom_dict(self.get_dns_agent_inspect_handle,
                                            'dns_inspect')
        self.agent_inspect = custom_dict(self.get_vrouter_agent_inspect_handle,
                                         'agent_inspect')
        self.ops_inspects = custom_dict(self.get_opserver_inspect_handle,
                                        'ops_inspect:'+self.project_name+':'+self.username)
        self.cn_inspect = custom_dict(self.get_control_node_inspect_handle,
                                      'cn_inspect')
        self.k8s_cluster = self.get_k8s_cluster()
        self.k8s_client = self.get_k8s_api_client_handle()

        # ToDo: msenthil/sandipd rest of init needs to be better handled
        self.domain_id = None
        if self.inputs.domain_isolation:
            #get admin auth to list domains and get domain_id
            auth = self.get_auth_h(username = self.inputs.admin_username,
                                   password=self.inputs.admin_password,
                                   project_name=self.inputs.admin_tenant,
                                   domain_name=self.inputs.admin_domain)
            self.domain_id = auth.get_domain_id(self.domain_name)
        self.auth = self.get_auth_h()
        self.vnc_lib = self.get_vnc_lib_h()
        self.project_id = self.get_project_id()
        if self.inputs.orchestrator == 'openstack':
            if self.inputs.verify_thru_gui():
                self.ui_login = UILogin(self, self.inputs, project_name, username, password)
                self.browser = self.ui_login.browser
                self.browser_openstack = self.ui_login.browser_openstack

            self.orch = OpenstackOrchestrator(inputs=self.inputs,
                                              vnclib=self.vnc_lib,
                                              logger=self.logger,
                                              auth_h=self.auth
                                             )
            self.ironic_h = self.orch.get_ironic_handler()
            self.nova_h = self.orch.get_compute_handler()
            self.quantum_h = self.orch.get_network_handler()
            self.glance_h = self.orch.get_image_handler()
        elif self.inputs.orchestrator == 'vcenter':
            self.orch = VcenterOrchestrator(user=self.inputs.vcenter_username,
                                            pwd= self.inputs.vcenter_password,
                                            host=self.inputs.vcenter_server,
                                            port=self.inputs.vcenter_port,
                                            dc_name=self.inputs.vcenter_dc,
                                            vnc=self.vnc_lib,
                                            inputs=self.inputs,
                                            logger=self.logger)
            if self.inputs.vro_server:
                self.vro_orch = VroWorkflows(user=self.inputs.vcenter_username,
                            pwd= self.inputs.vcenter_password,
                            host=self.inputs.vcenter_server,
                            port=self.inputs.vcenter_port,
                            dc_name=self.inputs.vcenter_dc,
                            vnc=self.vnc_lib,
                            inputs=self.inputs,
                            logger=self.logger)
        elif self.inputs.orchestrator == 'kubernetes':
            self.orch = None
        if self.inputs.vcenter_gw_setup: # vcenter_gateway
            self.slave_orch = VcenterGatewayOrch(user=self.inputs.vcenter_username,
                                            pwd=self.inputs.vcenter_password,
                                            host=self.inputs.vcenter_server,
                                            port=int(self.inputs.vcenter_port),
                                            dc_name=self.inputs.vcenter_dc,
                                            vnc=self.vnc_lib,
                                            inputs=self.inputs,
                                            logger=self.logger)
        self._kube_manager_inspect = None

    # end __init__

    def get_project_id(self, project_name=None):
        project_name = project_name or self.project_name
        auth = self.get_auth_h(project_name=project_name)
        if auth:
            return auth.get_project_id(project_name or self.project_name,
                                       self.domain_id)
        else:
            return self.vnc_lib_fixture.project_id if self.vnc_lib_fixture else None

    def get_auth_h(self, refresh=False, project_name=None,
                   username=None, password=None, domain_name=None):
        project_name = project_name or self.project_name
        username = username or self.username
        password = password or self.password
        attr = '_auth_'+project_name+'_'+username
        if not getattr(env, attr, None) or refresh:
            if self.inputs.orchestrator == 'openstack':
                env[attr] = OpenstackAuth(username, password,
                           project_name, self.inputs, self.logger,
                           domain_name=domain_name or self.orch_domain_name,
                           scope=self.scope)
            elif self.inputs.orchestrator == 'vcenter':
                env[attr] = VcenterAuth(username, password,
                                       project_name, self.inputs)
#            elif self.inputs.orchestrator == 'kubernetes':
#                env[attr] = self.get_k8s_api_client_handle()
        return env.get(attr)

    def get_vnc_lib_h(self, refresh=False):
        attr = '_vnc_lib_fixture_' + self.project_name + '_' + self.username
        cfgm_ip = self.inputs.command_server_ip or self.inputs.api_server_ip or \
                  self.inputs.cfgm_ip
        api_server_url = self.go_config_proxy_url
        api_server_port = self.inputs.go_server_port if self.inputs.command_server_ip \
                          else self.inputs.api_server_port
        insecure = True if self.inputs.command_server_ip else self.inputs.insecure
        use_ssl = False
        if self.inputs.command_server_ip:
            use_ssl = True
        if self.inputs.api_protocol == 'https':
            use_ssl = True
        if not getattr(env, attr, None) or refresh:
            if self.inputs.orchestrator == 'openstack' :
                domain = self.orch_domain_name
            else:
                domain = self.domain_name
            env[attr] = VncLibFixture(
                username=self.username, password=self.password,
                domain=domain, project_name=self.project_name,
                inputs=self.inputs,
                cfgm_ip=cfgm_ip,
                project_id=self.get_project_id(),
                api_server_port=api_server_port,
                api_server_url=api_server_url,
                orchestrator=self.inputs.orchestrator,
                certfile = self.inputs.keystonecertfile,
                keyfile = self.inputs.keystonekeyfile,
                cacert = self.inputs.certbundle,
                insecure = insecure,
                use_ssl = use_ssl,
                logger=self.logger)
            env[attr].setUp()
        self.vnc_lib_fixture = env[attr]
        self.vnc_lib = self.vnc_lib_fixture.get_handle()
        return self.vnc_lib

    def get_policy_generator_handle(self):
        if not self.inputs.policy_generator_ips:
            return None
        return PolicyGeneratorClient(inputs=self.inputs, logger=self.logger)

    def get_go_client_handle(self):
        if not self.inputs.command_server_ip:
            return None
        return GoApiInspect(self.inputs.command_server_ip,
                            port=self.inputs.go_server_port,
                            inputs=self.inputs,
                            logger=self.logger)

    def get_api_inspect_handle(self, host):
        cfgm_ip = self.inputs.command_server_ip or self.inputs.api_server_ip
        if cfgm_ip:
            host = cfgm_ip
        api_protocol = 'https' if self.inputs.command_server_ip else self.inputs.api_protocol
        api_server_port = self.inputs.go_server_port if self.inputs.command_server_ip \
                          else self.inputs.api_server_port
        insecure = True if self.inputs.command_server_ip else self.inputs.insecure
        if host not in self.api_server_inspects:
            self.api_server_inspects[host] = VNCApiInspect(host,
                                                           inputs=self.inputs,
                                                           port=api_server_port,
                                                           protocol=api_protocol,
                                                           base_url=self.go_config_proxy_url,
                                                           insecure=insecure,
                                                           logger=self.logger)
        return self.api_server_inspects[host]

    def get_control_node_inspect_handle(self, host):
        if host not in self.cn_inspect:
            self.cn_inspect[host] = ControlNodeInspect(host,
                                        self.inputs.bgp_port,
                                        logger=self.logger,
                                        args=self.inputs,
                                        protocol=self.inputs.introspect_protocol)
        return self.cn_inspect[host]

    def get_dns_agent_inspect_handle(self, host):
        if host not in self.dnsagent_inspect:
            self.dnsagent_inspect[host] = DnsAgentInspect(host,
                                              self.inputs.dns_port,
                                              logger=self.logger,
                                              args=self.inputs,
                                              protocol=self.inputs.introspect_protocol)
        return self.dnsagent_inspect[host]

    def get_vrouter_agent_inspect_handle(self, host):
        if host not in self.agent_inspect:
            self.agent_inspect[host] = AgentInspect(host,
                                           port=self.inputs.agent_port,
                                           logger=self.logger,
                                           inputs=self.inputs,
                                           protocol=self.inputs.introspect_protocol)
        return self.agent_inspect[host]

    def get_opserver_inspect_handle(self, host):
        #ToDo: WA till scripts are modified to use ip rather than hostname
        ip = host if is_v4(host) else self.inputs.get_host_ip(host)
        collector_ip = self.inputs.command_server_ip or self.inputs.analytics_api_ip
        if collector_ip:
            ip = collector_ip
        port = self.inputs.go_server_port if self.inputs.command_server_ip \
               else self.inputs.analytics_api_port
        protocol = 'https' if self.inputs.command_server_ip else \
            self.inputs.analytics_api_protocol
        insecure = True if self.inputs.command_server_ip else self.inputs.insecure
        if ip not in self.ops_inspects:
            self.ops_inspects[ip] = VerificationOpsSrv(ip,
                                        port=port,
                                        protocol=protocol,
                                        base_url=self.go_analytics_proxy_url,
                                        insecure=insecure,
                                        logger=self.logger,
                                        inputs=self.inputs)
        return self.ops_inspects[ip]

    def get_k8s_cluster(self):
        if self.inputs.slave_orchestrator != 'kubernetes':
            return None
        if not getattr(self, 'k8s_cluster', None):
            self.k8s_cluster = None
            for clus in self.inputs.k8s_clusters:
                if clus['name'] == self.project_name:
                    self.k8s_cluster = clus
                    break
        return self.k8s_cluster

    def get_k8s_api_client_handle(self):
        if self.inputs.orchestrator != 'kubernetes' and self.inputs.slave_orchestrator != 'kubernetes':
            return None
        if not getattr(self, 'k8s_client', None):
            if self.inputs.deployer == 'openshift':
                self.k8s_client = Openshift_client(self.inputs.kube_config_file,
                                                self.logger)
            else:
                if self.inputs.slave_orchestrator == 'kubernetes':
                    if self.k8s_cluster:
                        self.k8s_client = Kubernetes_client(
                                                cluster=self.k8s_cluster,
                                                logger=self.logger)
                    else:
                        self.k8s_client = None
                else:
                    self.k8s_client = Kubernetes_client(
                                                self.inputs.kube_config_file,
                                                self.logger)
        return self.k8s_client
    # end get_k8s_api_client_handle

    def get_svc_mon_h(self, refresh=False):
        if not getattr(self, '_svc_mon_inspect', None) or refresh:
            for cfgm_ip in self.inputs.cfgm_ips:
                #contrail-status would increase run time hence netstat approach
                cmd = 'netstat -antp | grep :8088 | grep LISTEN'
                if 'LISTEN' in self.inputs.run_cmd_on_server(cfgm_ip, cmd, container='svc-monitor'):
                    self._svc_mon_inspect = SvcMonInspect(cfgm_ip,
                                           logger=self.logger,
                                           args=self.inputs,
                                           protocol=self.inputs.introspect_protocol)
                    break
        return self._svc_mon_inspect

    @retry(delay=3, tries=10)
    def _get_kube_manager_h(self, refresh=False):
        if self.k8s_cluster:
            self._kube_manager_inspect = KubeManagerInspect(
                                    self.k8s_cluster['master_public_ip'],
                                    logger=self.logger,
                                    args=self.inputs,
                                    protocol=self.inputs.introspect_protocol)
            return True

        for km_ip in self.inputs.kube_manager_ips:
            #contrail-status would increase run time hence netstat approach
            cmd = 'netstat -antp | grep :%s | grep LISTEN' % self.inputs.k8s_port
            if 'LISTEN' in self.inputs.run_cmd_on_server(km_ip, cmd,
                                container='contrail-kube-manager'):
                self._kube_manager_inspect = KubeManagerInspect(km_ip,
                                        logger=self.logger,
                                        args=self.inputs,
                                        protocol=self.inputs.introspect_protocol)
                return True

        return False
    # end get_kube_manager_h

    def get_kube_manager_h(self, refresh=False):
        if not getattr(self, '_kube_manager_inspect', None) or refresh:
            self._kube_manager_inspect = None
            self._get_kube_manager_h(refresh=refresh)
            msg = "Kubernetes manager service is not up"
            assert self._kube_manager_inspect is not None, msg
        return self._kube_manager_inspect

    @property
    def policy_generator_handle(self):
        if not getattr(self, '_policygen', None):
            self._policygen = self.get_policy_generator_handle()
        return self._policygen

    @property
    def go_api_handle(self):
        if not getattr(self, '_go_api_handle', None):
            self._go_api_handle = self.get_go_client_handle()
        return self._go_api_handle

    @property
    def go_cluster_id(self):
        if not self.go_api_handle:
            return None
        if not getattr(self, '_go_cluster_id', None):
            self._go_cluster_id = self.go_api_handle.get_cluster_id()
        return self._go_cluster_id

    @property
    def go_config_proxy_url(self):
        if not self.go_api_handle:
            return '/'
        if not getattr(self, '_config_proxy_url', None):
            self._config_proxy_url = '/proxy/%s/config/'%self.go_cluster_id
        return self._config_proxy_url

    @property
    def go_analytics_proxy_url(self):
        if not self.go_api_handle:
            return '/'
        if not getattr(self, '_analytics_proxy_url', None):
            self._analytics_proxy_url = '/proxy/%s/telemetry/'%self.go_cluster_id
        return self._analytics_proxy_url

    @property
    def api_server_inspect(self):
        if not getattr(self, '_api_server_inspect', None):
            self._api_server_inspect = self.api_server_inspects[
                                        self.inputs.cfgm_ips[0]]
        return self._api_server_inspect
    @api_server_inspect.setter
    def api_server_inspect(self, value):
        self._api_server_inspect = value

    @property
    def ops_inspect(self):
        if not getattr(self, '_ops_inspect', None):
            self._ops_inspect = self.ops_inspects[self.inputs.collector_ips[0]]
        return self._ops_inspect
    @ops_inspect.setter
    def ops_inspect(self, value):
        self._ops_inspect = value

    @property
    def analytics_obj(self):
        if not getattr(self, '_analytics_obj', None):
            self._analytics_obj = AnalyticsVerification(self.inputs,
                                  self.cn_inspect, self.agent_inspect,
                                  self.ops_inspects, logger=self.logger)
        return self._analytics_obj
    @analytics_obj.setter
    def analytics_obj(self, value):
        self._analytics_obj = value

    def update_inspect_handles(self):
        self.api_server_inspects.clear()
        self.cn_inspect.clear()
        self.dnsagent_inspect.clear()
        self.agent_inspect.clear()
        self.ops_inspects.clear()
        self._svc_mon_inspect = None
        self._api_server_inspect = None
        self._ops_inspect = None
        self._analytics_obj = None
        self._kube_manager_inspect = None
    # end update_inspect_handles

    def update_vnc_lib_fixture(self):
        self.vnc_lib = self.get_vnc_lib_h(refresh=True)
    # end update_vnc_lib_fixture()

    def set_vrouter_config_encap(self, encap1=None, encap2=None, encap3=None):
        return self.update_vrouter_config_encap(encap1, encap2, encap3, create=True)
    # end set_vrouter_config_encap

    def update_vrouter_config_encap(self, encap1=None, encap2=None, encap3=None, create=False):
        '''Used to change the existing encapsulation priorities to new values'''
        if not (encap1 and encap2 and encap3):
            return self.delete_vrouter_encap()
        try:
            # Reading Existing config
            current_config = self.vnc_lib.global_vrouter_config_read(
                                    fq_name=['default-global-system-config',
                                             'default-global-vrouter-config'])
        except NoIdError as e:
            self.logger.exception('No config id found. Creating new one')
            if not create:
                raise
            conf_obj = GlobalVrouterConfig()
            self.vnc_lib.global_vrouter_config_create(conf_obj)

        encaps_obj = EncapsulationPrioritiesType(
            encapsulation=[encap1, encap2, encap3])
        confs_obj = GlobalVrouterConfig(encapsulation_priorities=encaps_obj)
        result = self.vnc_lib.global_vrouter_config_update(confs_obj)
        return result
    # end update_vrouter_config_encap

    def delete_vrouter_encap(self):
        try:
            conf_id = self.vnc_lib.get_default_global_vrouter_config_id()
            obj = self.vnc_lib.global_vrouter_config_read(id=conf_id)
            encap_obj = obj.get_encapsulation_priorities()
            if not encap_obj:
                return ['', '', '']
            encaps = encap_obj.encapsulation
            l = len(encaps)
            encaps.extend([''] * (3 - l))
            obj.set_encapsulation_priorities(None)
            self.vnc_lib.global_vrouter_config_update(obj)
            return encaps
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
            return (errmsg)
    # end delete_vrouter_encap

    def read_vrouter_config_encap(self):
        result = None
        try:
            conf_id = self.vnc_lib.get_default_global_vrouter_config_id()
            config_parameters = self.vnc_lib.global_vrouter_config_read(id=conf_id)
            obj = config_parameters.get_encapsulation_priorities()
            if not obj:
               return ['', '', '']
            else:
               return obj.encapsulation
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
        return result
    # end read_vrouter_config_encap

    def set_vrouter_config_evpn(self, evpn_status=True):
        self.obj = self.vnc_lib

        # Check if already configured
        try:
            conf_id = self.obj.get_default_global_vrouter_config_id()
            self.obj.global_vrouter_config_delete(id=conf_id)
        except Exception:
            msg = "No config id found. Configuring new one"
            self.logger.info(msg)
            pass
        if evpn_status == True:
            conf_obj = GlobalVrouterConfig(evpn_status=True)
        else:
            conf_obj = GlobalVrouterConfig(evpn_status=False)
        result = self.obj.global_vrouter_config_create(conf_obj)
        return result
    # end set_vrouter_config_evpn

    def update_vrouter_config_evpn(self, evpn_status=True):
        self.obj = self.vnc_lib
        if evpn_status == True:
            conf_obj = GlobalVrouterConfig(evpn_status=True)
        else:
            conf_obj = GlobalVrouterConfig(evpn_status=False)
        result = self.obj.global_vrouter_config_update(conf_obj)
        return result
    # end update_vrouter_config_evpn

    def delete_vrouter_config_evpn(self):
        try:
            self.obj = self.vnc_lib
            conf_id = self.obj.get_default_global_vrouter_config_id()
            self.obj.global_vrouter_config_delete(id=conf_id)
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
    # end delete_vrouter_config_evpn

    def read_vrouter_config_evpn(self):
        result = False
        try:
            self.obj = self.vnc_lib
            conf_id = self.obj.get_default_global_vrouter_config_id()
            out = self.obj.global_vrouter_config_read(id=conf_id)
            if 'evpn_status' in list(out.__dict__.keys()):
                result = out.evpn_status
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
        return result
    # end read_vrouter_config_evpn
