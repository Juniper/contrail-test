from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vnc_introspect_utils import *
from cn_introspect_utils import *
from vna_introspect_utils import *
from opserver_introspect_utils import *
from fixtures import Fixture
from analytics_tests import *
from vnc_api.vnc_api import *
from vdns.dns_introspect_utils import DnsAgentInspect
from ds_introspect_utils import *
from discovery_tests import *

class ContrailConnections():
    
    def __init__(self, inputs):
        self.inputs= inputs
        self.quantum_fixture= QuantumFixture(
            username=self.inputs.stack_user, inputs= self.inputs,
            project_name=self.inputs.project_name,
            password= self.inputs.stack_password, cfgm_ip= self.inputs.cfgm_ip,
            openstack_ip= self.inputs.openstack_ip)
        self.quantum_fixture.setUp() 
        inputs.openstack_ip = self.inputs.openstack_ip
        
        self.vnc_lib_fixture= VncLibFixture(
            username=self.inputs.stack_user, password= self.inputs.stack_password,
            domain=self.inputs.domain_name, project=self.inputs.project_name,
            inputs= self.inputs, cfgm_ip= self.inputs.cfgm_ip,
            api_port= self.inputs.api_server_port)
        self.vnc_lib_fixture.setUp()
        self.vnc_lib=self.vnc_lib_fixture.get_handle()        

        self.nova_fixture= NovaFixture( inputs= inputs, 
                    project_name= self.inputs.project_name )
        self.nova_fixture.setUp()
        
        self.api_server_inspect=VNCApiInspect(self.inputs.cfgm_ip, 
                args=self.inputs, logger=self.inputs.logger)
        self.cn_inspect= {}
        for bgp_ip in self.inputs.bgp_ips:
            self.cn_inspect[bgp_ip]= ControlNodeInspect(bgp_ip,
                                                    logger=self.inputs.logger)
        self.agent_inspect={}
        for compute_ip in self.inputs.compute_ips:
            self.agent_inspect[compute_ip]=AgentInspect(compute_ip,
                                                    logger=self.inputs.logger)
        self.dnsagent_inspect = {}
        for bgp_ip in self.inputs.bgp_ips:
            self.dnsagent_inspect[bgp_ip]= DnsAgentInspect(bgp_ip,logger=self.inputs.logger)
        self.ops_inspects={}
        for collector_ip in self.inputs.collector_ips:
            self.ops_inspects[collector_ip]= VerificationOpsSrv(collector_ip,
                                             logger=self.inputs.logger)
            self.ops_inspect= VerificationOpsSrv(self.inputs.collector_ip,
                                             logger=self.inputs.logger)
        
        for collector_name in self.inputs.collector_names:
            self.ops_inspects[collector_name]= VerificationOpsSrv(collector_ip,
                                             logger=self.inputs.logger)
            
        self.analytics_obj=AnalyticsVerification(self.inputs,self.api_server_inspect,self.cn_inspect,self.agent_inspect,self.ops_inspects,logger=self.inputs.logger)
        self.ds_inspect={}
        for ds_ip in self.inputs.ds_server_ip:
            self.ds_inspect[ds_ip]=VerificationDsSrv(ds_ip,logger=self.inputs.logger) 
        self.ds_verification_obj=DiscoveryVerification(self.inputs,self.api_server_inspect,self.cn_inspect
                                                       ,self.agent_inspect,self.ops_inspects,self.ds_inspect,logger=self.inputs.logger)
    #end __init__
    
    def setUp(self):
        super(ContrailConnections, self).setUp()
        pass
    #end 
    
    def cleanUp(self):
        super(ContrailConnections, self).cleanUp()
        pass
    #end 
    
    def set_vrouter_config_encap(self,encap1=None,encap2=None,encap3=None):
        self.obj = self.vnc_lib
        encap_obj=EncapsulationPrioritiesType(encapsulation=[encap1,encap2,encap3])
        conf_obj=GlobalVrouterConfig(encapsulation_priorities=encap_obj)
        result=self.obj.global_vrouter_config_create(conf_obj)
        return result
    #end set_vrouter_config_encap

    def update_vrouter_config_encap(self,encap1=None,encap2=None,encap3=None):
        '''Used to change the existing encapsulation priorities to new values'''
        self.obj = self.vnc_lib
        encaps_obj=EncapsulationPrioritiesType(encapsulation=[encap1,encap2,encap3])
        confs_obj=GlobalVrouterConfig(encapsulation_priorities=encaps_obj)
        result=self.obj.global_vrouter_config_update(confs_obj)
        return result
    #end update_vrouter_config_encap


    def delete_vrouter_encap(self):
        self.obj = self.vnc_lib
        try:
            conf_id=self.obj.get_default_global_vrouter_config_id()
            self.inputs.logger.info("Config id found.Deleting it")
            config_parameters=self.obj.global_vrouter_config_read(id=conf_id)
            self.inputs.config.obj=config_parameters.get_encapsulation_priorities()
            try:
                encaps1=self.inputs.config.obj.encapsulation[0]
                encaps2=self.inputs.config.obj.encapsulation[1]
                try:
                    encaps1=self.inputs.config.obj.encapsulation[0]
                    encaps2=self.inputs.config.obj.encapsulation[1]
                    encaps3=self.inputs.config.obj.encapsulation[2]
                    self.obj.global_vrouter_config_delete(id=conf_id)
                    return (encaps1,encaps2,encaps3)
                except IndexError:
                    self.obj.global_vrouter_config_delete(id=conf_id)
                    return (encaps1,encaps2,None)
            except IndexError:
                self.obj.global_vrouter_config_delete(id=conf_id)
                return (encaps1,None,None)
        except NoIdError:
            errmsg="No config id found"
            self.inputs.logger.info(errmsg)
            return (errmsg)
    #end delete_vrouter_encap

    def set_vrouter_config_evpn(self,evpn_status=True):
        self.obj = self.vnc_lib

        # Check if already configured
        try:
            conf_id=self.obj.get_default_global_vrouter_config_id()
            self.obj.global_vrouter_config_delete(id=conf_id)
        except Exception:
            msg="No config id found. Configuring new one"
            self.inputs.logger.info(msg)
            pass 
        if evpn_status == True:
            conf_obj=GlobalVrouterConfig(evpn_status=True)
        else:
            conf_obj=GlobalVrouterConfig(evpn_status=False)
        result=self.obj.global_vrouter_config_create(conf_obj)
        return result
    #end set_vrouter_config_evpn
  
    def update_vrouter_config_evpn(self,evpn_status=True):
        self.obj = self.vnc_lib
        if evpn_status == True:
            conf_obj=GlobalVrouterConfig(evpn_status=True) 
        else:
            conf_obj=GlobalVrouterConfig(evpn_status=False)
        result=self.obj.global_vrouter_config_update(conf_obj)
        return result
    #end update_vrouter_config_evpn

    def delete_vrouter_config_evpn(self):
        try:
            self.obj = self.vnc_lib
            conf_id=self.obj.get_default_global_vrouter_config_id()
            self.obj.global_vrouter_config_delete(id=conf_id)
        except NoIdError:
            errmsg="No config id found"
            self.inputs.logger.info(errmsg)
    #end delete_vrouter_config_evpn

    def read_vrouter_config_evpn(self):
        result = False
        try:
            self.obj = self.vnc_lib
            conf_id=self.obj.get_default_global_vrouter_config_id()
            out=self.obj.global_vrouter_config_read(id=conf_id)
            if 'evpn_status' in out.__dict__.keys():
                result= out.evpn_status
        except NoIdError:
            errmsg="No config id found"
            self.inputs.logger.info(errmsg)
        return result 
    #end read_vrouter_config_evpn
 

