from vnc_api_test import *
from tcutils.config.vnc_introspect_utils import *
from tcutils.control.cn_introspect_utils import *
from tcutils.agent.vna_introspect_utils import *
from tcutils.collector.opserver_introspect_utils import *
from fixtures import Fixture
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
    def __init__(self, inputs,logger,
                 project_name=None,
                 username=None,
                 password=None):
        self.inputs = inputs
        project_name = project_name or self.inputs.project_name
        username = username or self.inputs.stack_user
        password = password or self.inputs.stack_password
        self.username = username
        self.password = password
        self.project_name = project_name

        self.vnc_lib_fixture = VncLibFixture(
            username=username, password=password,
            domain=self.inputs.domain_name, project=project_name,
            inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip,
            api_port=self.inputs.api_server_port)
        self.vnc_lib_fixture.setUp()
        self.vnc_lib = self.vnc_lib_fixture.get_handle()

        self.nova_h = None
        self.quantum_h = None
        if self.inputs.orchestrator == 'openstack':
            self.auth = OpenstackAuth(username, password, project_name, self.inputs, logger)
            self.project_id = self.auth.get_project_id(self.inputs.domain_name, project_name)

            if self.inputs.verify_thru_gui():
                self.ui_login = UILogin(self, self.inputs, project_name, username, password)
                self.browser = self.ui_login.browser
                self.browser_openstack = self.ui_login.browser_openstack

            self.orch = OpenstackOrchestrator(username=username, password=password,
                           project_id=self.project_id, project_name=project_name,
                           inputs=inputs, vnclib=self.vnc_lib, logger=logger)
            self.nova_h = self.orch.nova_h
            self.quantum_h = self.orch.quantum_h
        else: # vcenter
            self.auth = VcenterAuth(username, password, project_name, self.inputs)
            self.orch = VcenterOrchestrator(user=username, pwd=password,
                           host=self.inputs.auth_ip,
                           port=self.inputs.auth_port,
                           dc_name=self.inputs.vcenter_dc,
                           vnc=self.vnc_lib,
                           inputs=self.inputs, logger=logger)

        self.api_server_inspects = {}
        self.dnsagent_inspect = {}
        self.cn_inspect = {}
        self.agent_inspect = {}
        self.ops_inspects = {}
        self.ds_inspect = {}
        self.update_inspect_handles()
        # end __init__

    def update_inspect_handles(self):
        self.api_server_inspects.clear()
        self.cn_inspect.clear()
        self.dnsagent_inspect.clear()
        self.agent_inspect.clear()
        self.ops_inspects.clear()
        self.ds_inspect.clear()
        for cfgm_ip in self.inputs.cfgm_ips:
            self.api_server_inspects[cfgm_ip] = VNCApiInspect(cfgm_ip,
                                                              args=self.inputs, logger=self.inputs.logger)
            self.api_server_inspect = VNCApiInspect(cfgm_ip,
                                                    args=self.inputs, logger=self.inputs.logger)
        for bgp_ip in self.inputs.bgp_ips:
            self.cn_inspect[bgp_ip] = ControlNodeInspect(bgp_ip,
                                                         logger=self.inputs.logger)
            self.dnsagent_inspect[bgp_ip] = DnsAgentInspect(bgp_ip,
                                                            logger=self.inputs.logger)
        for compute_ip in self.inputs.compute_ips:
            self.agent_inspect[compute_ip] = AgentInspect(compute_ip,
                                                          logger=self.inputs.logger)
        for collector_ip in self.inputs.collector_ips:
            self.ops_inspects[collector_ip] = VerificationOpsSrv(collector_ip,
                                                                 logger=self.inputs.logger)
            self.ops_inspect = VerificationOpsSrv(self.inputs.collector_ip,
                                                  logger=self.inputs.logger)

        for collector_name in self.inputs.collector_names:
            self.ops_inspects[collector_name] = VerificationOpsSrv(
                collector_ip,
                logger=self.inputs.logger)

        self.analytics_obj = AnalyticsVerification(
            self.inputs, self.api_server_inspect, self.cn_inspect, self.agent_inspect, self.ops_inspects, logger=self.inputs.logger)
        for ds_ip in self.inputs.ds_server_ip:
            self.ds_inspect[ds_ip] = VerificationDsSrv(
                ds_ip, logger=self.inputs.logger)
        self.ds_verification_obj = DiscoveryVerification(
            self.inputs, self.api_server_inspect, self.cn_inspect, self.agent_inspect, self.ops_inspects, self.ds_inspect, logger=self.inputs.logger)
    # end update_inspect_handles

    def setUp(self):
        super(ContrailConnections, self).setUp()
        pass
    # end

    def cleanUp(self):
        super(ContrailConnections, self).cleanUp()
        pass
    # end

    def set_vrouter_config_encap(self, encap1=None, encap2=None, encap3=None):
        self.obj = self.vnc_lib

        try:
            # Reading Existing config
            current_config=self.obj.global_vrouter_config_read(
                                    fq_name=['default-global-system-config',
                                             'default-global-vrouter-config'])
            current_linklocal=current_config.get_linklocal_services()
        except NoIdError as e:
            self.inputs.logger.exception('No config id found. Creating new one')
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
            self.inputs.logger.exception('No config id found. Creating new one')
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
            self.inputs.logger.info("Config id found.Deleting it")
            config_parameters = self.obj.global_vrouter_config_read(id=conf_id)
            self.inputs.config.obj = config_parameters.get_encapsulation_priorities(
            )
            if not self.inputs.config.obj:
                # temp workaround,delete default-global-vrouter-config.need to
                # review this testcase
                self.obj.global_vrouter_config_delete(id=conf_id)
                errmsg = "No config id found"
                self.inputs.logger.info(errmsg)
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
            self.inputs.logger.info(errmsg)
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
            self.inputs.logger.info(errmsg)
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
            self.inputs.logger.info(msg)
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
            self.inputs.logger.info(errmsg)
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
            self.inputs.logger.info(errmsg)
        return result
    # end read_vrouter_config_evpn

    def update_vnc_lib_fixture(self):
        self.vnc_lib_fixture.cleanUp()
        self.vnc_lib_fixture = VncLibFixture(
            username=self.username, password=self.password,
            domain=self.inputs.domain_name, project=self.project_name,
            inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip,
            api_port=self.inputs.api_server_port)
        self.vnc_lib_fixture.setUp()
        self.vnc_lib = self.vnc_lib_fixture.get_handle()
    # end update_vnc_lib_fixture()
