from vnc_api_test import *
from tcutils.config.vnc_introspect_utils import *
from tcutils.config.svc_mon_introspect_utils import SvcMonInspect
from tcutils.control.cn_introspect_utils import *
from tcutils.agent.vna_introspect_utils import *
from tcutils.collector.opserver_introspect_utils import *
from tcutils.collector.analytics_tests import *
from vnc_api.vnc_api import *
from tcutils.vdns.dns_introspect_utils import DnsAgentInspect
from tcutils.config.ds_introspect_utils import *
from tcutils.config.discovery_tests import *
from tcutils.util import custom_dict
import os
from openstack import OpenstackAuth, OpenstackOrchestrator
from vcenter import VcenterAuth, VcenterOrchestrator
from common.contrail_test_init import ContrailTestInit

try:
    from webui.ui_login import UILogin
except ImportError:
    pass

class ContrailConnections():
    def __init__(self, inputs=None, logger=None, project_name=None,
                 username=None, password=None, domain_name=None, ini_file=None):
        project_fq_name = [domain_name or 'default-domain', project_name] \
                          if project_name else None
        self.inputs = inputs or ContrailTestInit(ini_file,
                                project_fq_name=project_fq_name)
        self.project_name = project_name or self.inputs.project_name
        self.domain_name = domain_name or self.inputs.domain_name
        self.username = username or self.inputs.stack_user
        self.password = password or self.inputs.stack_password
        self.logger = logger or self.inputs.logger
        self.nova_h = None
        self.quantum_h = None
        self.api_server_inspects = custom_dict(self.get_api_inspect_handle,
                        'api_inspect:'+self.project_name+':'+self.username)
        self.dnsagent_inspect = custom_dict(self.get_dns_agent_inspect_handle,
                                            'dns_inspect')
        self.agent_inspect = custom_dict(self.get_vrouter_agent_inspect_handle,
                                         'agent_inspect')
        self.ops_inspects = custom_dict(self.get_opserver_inspect_handle,
                                        'ops_inspect')
        self.cn_inspect = custom_dict(self.get_control_node_inspect_handle,
                                      'cn_inspect')
        self.ds_inspect = custom_dict(self.get_discovery_service_inspect_handle,
                                      'ds_inspect')

        # ToDo: msenthil/sandipd rest of init needs to be better handled
        self.vnc_lib = self.get_vnc_lib_h()
        self.auth = self.get_auth_h()
        if self.inputs.orchestrator == 'openstack':
            self.project_id = self.get_project_id()
            if self.inputs.verify_thru_gui():
                self.ui_login = UILogin(self, self.inputs, project_name, username, password)
                self.browser = self.ui_login.browser
                self.browser_openstack = self.ui_login.browser_openstack

            self.orch = OpenstackOrchestrator(username=self.username,
                                              password=self.password,
                                              project_id=self.project_id,
                                              project_name=self.project_name,
                                              inputs=self.inputs,
                                              vnclib=self.vnc_lib,
                                              logger=self.logger,
                                             auth_server_ip=self.inputs.auth_ip)
            self.nova_h = self.orch.get_compute_handler()
            self.quantum_h = self.orch.get_network_handler()
        else: # vcenter
            self.orch = VcenterOrchestrator(user=self.username,
                                            pwd=self.password,
                                            host=self.inputs.auth_ip,
                                            port=self.inputs.auth_port,
                                            dc_name=self.inputs.vcenter_dc,
                                            vnc=self.vnc_lib,
                                            inputs=self.inputs,
                                            logger=self.logger)
    # end __init__

    def get_project_id(self, project_name=None):
        project_name = project_name or self.project_name
        auth = self.get_auth_h(project_name)
        return auth.get_project_id(project_name or self.project_name)

    def get_auth_h(self, refresh=False, project_name=None,
                   username=None, password=None):
        project_name = project_name or self.project_name
        username = username or self.username
        password = password or self.password
        attr = '_auth_'+project_name+'_'+username
        if not getattr(env, attr, None) or refresh:
            if self.inputs.orchestrator == 'openstack':
                env[attr] = OpenstackAuth(username, password,
                           project_name, self.inputs, self.logger)
            else:
                env[attr] = VcenterAuth(username, password,
                                       project_name, self.inputs)
        return env[attr]

    def get_vnc_lib_h(self, refresh=False, project_name=None,
                      username=None, password=None):
        project_name = project_name or self.project_name
        username = username or self.username
        password = password or self.password
        attr = '_vnc_lib_'+project_name+'_'+username
        if not getattr(env, attr, None) or refresh:
            self.vnc_lib_fixture = VncLibFixture(
                username=username, password=password,
                domain=self.domain_name, project_name=project_name,
                inputs = self.inputs,
                cfgm_ip=self.inputs.cfgm_ip,
                api_server_port=self.inputs.api_server_port,
                auth_server_ip=self.inputs.auth_ip,
                orchestrator=self.inputs.orchestrator,
                logger=self.logger)
            self.vnc_lib_fixture.setUp()
            self.vnc_lib = self.vnc_lib_fixture.get_handle()
        return self.vnc_lib

    def get_api_inspect_handle(self, host):
        if host not in self.api_server_inspects:
            self.api_server_inspects[host] = VNCApiInspect(host,
                                                           args=self.inputs,
                                                           logger=self.logger)
        return self.api_server_inspects[host]

    def get_control_node_inspect_handle(self, host):
        if host not in self.cn_inspect:
            self.cn_inspect[host] = ControlNodeInspect(host, logger=self.logger)
        return self.cn_inspect[host]

    def get_dns_agent_inspect_handle(self, host):
        if host not in self.dnsagent_inspect:
            self.dnsagent_inspect[host] = DnsAgentInspect(host,
                                            logger=self.logger)
        return self.dnsagent_inspect[host]

    def get_vrouter_agent_inspect_handle(self, host):
        if host not in self.agent_inspect:
            self.agent_inspect[host] = AgentInspect(host, logger=self.logger)
        return self.agent_inspect[host]

    def get_opserver_inspect_handle(self, host):
        #ToDo: WA till scripts are modified to use ip rather than hostname
        ip = host if is_v4(host) else self.inputs.get_host_ip(host)
        if ip not in self.ops_inspects:
            self.ops_inspects[ip] = VerificationOpsSrv(ip, logger=self.logger)
        return self.ops_inspects[ip]

    def get_discovery_service_inspect_handle(self, host):
        if host not in self.ds_inspect:
            self.ds_inspect[host] = VerificationDsSrv(host, logger=self.logger)
        return self.ds_inspect[host]

    def get_svc_mon_h(self, refresh=False):
        if not getattr(self, '_svc_mon_inspect', None) or refresh:
            for cfgm_ip in self.inputs.cfgm_ips:
                #contrail-status would increase run time hence netstat approach
                cmd = 'netstat -antp | grep 8088 | grep LISTEN'
                if self.inputs.run_cmd_on_server(cfgm_ip, cmd) is not None:
                    self._svc_mon_inspect = SvcMonInspect(cfgm_ip,
                                           logger=self.logger)
                    break
        return self._svc_mon_inspect

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

    @property
    def ds_verification_obj(self):
        if not getattr(self, '_ds_verification_obj', None):
            self._ds_verification_obj = DiscoveryVerification(self.inputs,
                                        self.cn_inspect, self.agent_inspect,
                                        self.ops_inspects, self.ds_inspect,
                                        logger=self.logger)
        return self._ds_verification_obj
    @ds_verification_obj.setter
    def ds_verification_obj(self, value):
        self._ds_verification_obj = value

    def update_inspect_handles(self):
        self.api_server_inspects.clear()
        self.cn_inspect.clear()
        self.dnsagent_inspect.clear()
        self.agent_inspect.clear()
        self.ops_inspects.clear()
        self.ds_inspect.clear()
        self.api_server_inspect = None
        self.ops_inspect = None
        self.ds_verification_obj = None
        self._svc_mon_inspect = None
        self._api_server_inspect = None
        self._ops_inspect = None
        self._analytics_obj = None
        self._ds_verification_obj = None
    # end update_inspect_handles

    def update_vnc_lib_fixture(self):
        self.vnc_lib = self.get_vnc_lib_h(refresh=True)
    # end update_vnc_lib_fixture()

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
