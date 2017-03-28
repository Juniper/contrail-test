from vnc_api_test import *
from tcutils.config.vnc_introspect_utils import *
from tcutils.control.cn_introspect_utils import *
from tcutils.agent.vna_introspect_utils import *
from tcutils.collector.opserver_introspect_utils import *
from tcutils.collector.analytics_tests import *
from vnc_api.vnc_api import *
from tcutils.vdns.dns_introspect_utils import DnsAgentInspect
from tcutils.config.ds_introspect_utils import *
from tcutils.config.discovery_tests import *
import os
from openstack import OpenstackAuth, OpenstackOrchestrator
from vcenter import VcenterAuth, VcenterOrchestrator

try:
    from webui.ui_login import UILogin
except ImportError:
    pass

class ContrailConnections():
    def __init__(self, inputs, logger,
                 project_name=None,
                 username=None,
                 password=None):
        self.inputs = inputs
        project_name = project_name or self.inputs.project_name
        self.username = username or self.inputs.stack_user
        self.password = password or self.inputs.stack_password
        self.project_name = project_name
        self.logger = logger

        self.nova_h = None
        self.quantum_h = None
        if self.inputs.orchestrator == 'openstack':
            if self.inputs.verify_thru_gui():
                self.ui_login = UILogin(self, self.inputs, self.project_name, self.username, self.password)
                self.browser = self.ui_login.browser
                self.browser_openstack = self.ui_login.browser_openstack

        self.api_server_inspects = {}
        self.dnsagent_inspect = {}
        self.cn_inspect = {}
        self.agent_inspect = {}
        self.ops_inspects = {}
        self.ds_inspect = {}
        # end __init__

    def get_all_handles(self):
        self.get_vnc_lib_h()
        self.get_auth_h()
        self.get_orch_h()
        self.get_inspect_handles()

    def get_vnc_lib_h(self):
        if not getattr(self, 'vnc_lib', None):
            auth_host = self.inputs.get_auth_host()
            self.vnc_lib_fixture = VncLibHelper(
                username=self.username, password=self.password,
                domain=self.inputs.domain_name, project=self.project_name,
                inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip,
                api_port=self.inputs.api_server_port, auth_host=auth_host)
            self.vnc_lib = self.vnc_lib_fixture.get_handle()
        return self.vnc_lib_fixture

    def get_auth_h(self):
        if not getattr(self, 'auth', None):
            if self.inputs.orchestrator == 'openstack':
                self.auth = OpenstackAuth(self.username, self.password, self.project_name, self.inputs, self.logger)
            else: # vcenter
                self.auth = VcenterAuth(self.username, self.password, self.project_name, self.inputs)
        return self.auth

    def get_orch_h(self):
        if not getattr(self, 'orch', None):
            if self.inputs.orchestrator == 'openstack':
                self.orch = OpenstackOrchestrator(username=self.username,
                                                  password=self.password,
                                                  project_name=self.project_name,
                                                  inputs=self.inputs, logger=self.logger)
                self.nova_h = self.orch.get_compute_h()
                self.quantum_h = self.orch.get_network_h()
            else:
                self.get_vnc_lib_h()
                self.orch = VcenterOrchestrator(user=self.username, pwd=self.password,
                                                host=self.inputs.auth_ip,
                                                port=self.inputs.auth_port,
                                                dc_name=self.inputs.vcenter_dc,
                                                vnc=self.vnc_lib,
                                                inputs=self.inputs, logger=self.logger)
        return self.orch

    def get_network_h(self):
        orch = self.get_orch_h()
        return orch.get_network_h()

    def get_compute_h(self):
        orch = self.get_orch_h()
        return orch.get_compute_h()

    def get_project_fq_name(self):
        return [self.inputs.domain_name, self.project_name]

    def get_project_id(self):
        if not getattr(self, 'project_id', None):
            self.get_auth_h()
            self.project_id = self.auth.get_project_id(self.inputs.domain_name,
                                                       self.project_name)
        return self.project_id

    def get_inspect_handles(self):
        self.get_api_server_inspect_handles()
        self.get_control_node_inspect_handles()
        self.get_dns_agent_inspect_handles()
        self.get_opserver_inspect_handles()
        self.get_discovery_service_inspect_handles()
        for compute_ip in self.inputs.compute_ips:
            self.get_vrouter_agent_inspect_handle(compute_ip)
        self.analytics_obj = self.get_analytics_object()
        self.ds_verification_obj = self.get_discovery_service_object()
#        for collector_name in self.inputs.collector_names:
#            self.ops_inspects[collector_name] = VerificationOpsSrv(
#                collector_ip, logger=self.inputs.logger)

    def get_api_server_inspect_handles(self):
        for cfgm_ip in self.inputs.cfgm_ips:
            self.get_api_inspect_handle(cfgm_ip)
        self.api_server_inspect = self.api_server_inspects.values()[0]
        return self.api_server_inspects

    def get_control_node_inspect_handles(self):
        for bgp_ip in self.inputs.bgp_ips:
            self.get_control_node_inspect_handle(bgp_ip)
        return self.cn_inspect

    def get_dns_agent_inspect_handles(self):
        for bgp_ip in self.inputs.bgp_ips:
            self.get_dns_agent_inspect_handle(bgp_ip)
        return self.dnsagent_inspect

    def get_opserver_inspect_handles(self):
        for collector_ip in self.inputs.collector_ips:
            self.get_opserver_inspect_handle(collector_ip)
        self.ops_inspect = self.ops_inspects.values()[0]
        return self.ops_inspects

    def get_discovery_service_inspect_handles(self):
        for ds_ip in self.inputs.ds_server_ip:
            self.get_discovery_service_inspect_handle(ds_ip)
        return self.ds_inspect

    def get_api_inspect_handle(self, host):
        if host not in self.api_server_inspects:
            self.api_server_inspects[host]= VNCApiInspect(host, args=self.inputs,
                                                      logger=self.logger)
        return self.api_server_inspects[host]

    def get_control_node_inspect_handle(self, host):
        if host not in self.cn_inspect:
            self.cn_inspect[host] = ControlNodeInspect(host,
                                                 logger=self.logger)
        return self.cn_inspect[host]

    def get_dns_agent_inspect_handle(self, host):
        if host not in self.dnsagent_inspect:
            self.dnsagent_inspect[host] = DnsAgentInspect(host,
                                                 logger=self.logger)
        return self.dnsagent_inspect[host]

    def get_vrouter_agent_inspect_handle(self, host):
        if host not in self.agent_inspect:
            self.agent_inspect[host] = AgentInspect(host,
                                                 logger=self.logger)
        return self.agent_inspect[host]

    def get_opserver_inspect_handle(self, host):
        if host not in self.ops_inspects:
            self.ops_inspects[host] = VerificationOpsSrv(host,
                                                 logger=self.logger)
        return self.ops_inspects[host]

    def get_analytics_object(self):
        if not getattr(self, 'analytics_obj', None):
            ops_inspects = self.get_opserver_inspect_handles()
            self.analytics_obj = AnalyticsVerification(
                                 self.inputs, ops_inspects, logger=self.logger)
        return self.analytics_obj

    def get_discovery_service_inspect_handle(self, host):
        if host not in self.ds_inspect:
            self.ds_inspect[host] = VerificationDsSrv(
                                    host, logger=self.logger)
        return self.ds_inspect[host]

    def get_discovery_service_object(self):
        if not getattr(self, 'ds_verification_obj', None):
            self.ds_verification_obj = DiscoveryVerification(self.inputs,
                                       self.api_server_inspect, self.cn_inspect,
                                       self.agent_inspect, self.ops_inspects,
                                       self.ds_inspect, logger=self.logger)
        return self.ds_verification_obj

    def update_inspect_handles(self):
        self.api_server_inspects.clear()
        self.cn_inspect.clear()
        self.dnsagent_inspect.clear()
        self.agent_inspect.clear()
        self.ops_inspects.clear()
        self.ds_inspect.clear()
        self.get_inspect_handles()

    def update_vnc_lib_h(self):
        if getattr(self, 'vnc_lib_fixture', None):
            self.vnc_lib_fixture.cleanUp()
        self.vnc_lib = None
        self.vnc_lib_fixture = None
        self.get_vnc_lib_h()

    # ToDo: msenthil move anything other than connections out of connections.py
    def set_vrouter_config_encap(self, encap1=None, encap2=None, encap3=None):
        self.obj = self.vnc_lib

        try:
            # Reading Existing config
            current_config=self.obj.global_vrouter_config_read(
                                    fq_name=['default-global-system-config',
                                             'default-global-vrouter-config'])
            current_linklocal=current_config.get_linklocal_services()
        except NoIdError as e:
            self.logger.exception('No config id found. Creating new one')
            current_linklocal=''

        encap_obj = EncapsulationPrioritiesType(
            encapsulation=[encap1, encap2, encap3])
        conf_obj = GlobalVrouterConfig(linklocal_services=current_linklocal,encapsulation_priorities=encap_obj)
        result = self.obj.global_vrouter_config_create(conf_obj)
        return result
    # end set_vrouter_config_encap

    def update_vrouter_config_encap(self, encap1=None, encap2=None, encap3=None):
        '''Used to change the existing encapsulation priorities to new values'''
        self.obj = self.vnc_lib
 
        try:
            # Reading Existing config
            current_config=self.obj.global_vrouter_config_read(
                                    fq_name=['default-global-system-config',
                                             'default-global-vrouter-config'])
            current_linklocal=current_config.get_linklocal_services()
        except NoIdError as e:
            self.logger.exception('No config id found. Creating new one')
            current_linklocal=''

        encaps_obj = EncapsulationPrioritiesType(
            encapsulation=[encap1, encap2, encap3])
        confs_obj = GlobalVrouterConfig(linklocal_services=current_linklocal,
                                        encapsulation_priorities=encaps_obj)
        result = self.obj.global_vrouter_config_update(confs_obj)
        return result
    # end update_vrouter_config_encap

    def delete_vrouter_encap(self):
        self.obj = self.vnc_lib
        try:
            conf_id = self.obj.get_default_global_vrouter_config_id()
            self.logger.info("Config id found.Deleting it")
            config_parameters = self.obj.global_vrouter_config_read(id=conf_id)
            self.inputs.config.obj = config_parameters.get_encapsulation_priorities(
            )
            if not self.inputs.config.obj:
                # temp workaround,delete default-global-vrouter-config.need to
                # review this testcase
                self.obj.global_vrouter_config_delete(id=conf_id)
                errmsg = "No config id found"
                self.logger.info(errmsg)
                return (errmsg)
            try:
                encaps1 = self.inputs.config.obj.encapsulation[0]
                encaps2 = self.inputs.config.obj.encapsulation[1]
                try:
                    encaps1 = self.inputs.config.obj.encapsulation[0]
                    encaps2 = self.inputs.config.obj.encapsulation[1]
                    encaps3 = self.inputs.config.obj.encapsulation[2]
                    self.obj.global_vrouter_config_delete(id=conf_id)
                    return (encaps1, encaps2, encaps3)
                except IndexError:
                    self.obj.global_vrouter_config_delete(id=conf_id)
                    return (encaps1, encaps2, None)
            except IndexError:
                self.obj.global_vrouter_config_delete(id=conf_id)
                return (encaps1, None, None)
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
            return (errmsg)
    # end delete_vrouter_encap

    def read_vrouter_config_encap(self):
        result = None
        try:
            self.obj = self.vnc_lib
            conf_id = self.obj.get_default_global_vrouter_config_id()
            config_parameters = self.obj.global_vrouter_config_read(id=conf_id)
            self.inputs.config.obj = config_parameters.get_encapsulation_priorities(
            )
            result = self.inputs.config.obj.encapsulation
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
            if 'evpn_status' in out.__dict__.keys():
                result = out.evpn_status
        except NoIdError:
            errmsg = "No config id found"
            self.logger.info(errmsg)
        return result
    # end read_vrouter_config_evpn
