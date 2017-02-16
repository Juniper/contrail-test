''' This module provides utils for setting up sdn topology given the ui topo inputs'''
import os
import copy
import fixtures
import topo_steps
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from contrail_fixtures import *
try:
    from webui_test import *
except ImportError:
    pass


def createPort(self, option='contrail'):
    if not hasattr(self.topo, 'port_list'):
        self.logger.info("No port configs found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating port ")
    for port in self.topo.port_list:
        mac = self.topo.port_params[port]['mac']
        net = self.topo.port_params[port]['net']
        fixed_ip = self.topo.port_params[port]['fixed_ip']
        device_owner = self.topo.port_params[port]['device_owner']
        sg = self.topo.port_params[port]['sg']
        fip = self.topo.port_params[port]['fip']
        subnet = self.topo.port_params[port]['subnet']
        state = self.topo.port_params[port]['state']
        port_name = self.topo.port_params[port]['port_name']
        if not self.webui.create_port(
                net,
                subnet,
                mac,
                state,
                port_name,
                fixed_ip,
                fip,
                sg,
                device_owner):
            result = result and False
    return result
# end createPort


def createRouter(self, option='contrail'):
    if not hasattr(self.topo, 'router_list'):
        self.logger.info("No router configs found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating Router")
    for router in self.topo.router_list:
        router_name = router
        state = self.topo.router_list[router]['state']
        gateway = self.topo.router_list[router]['gateway']
        networks = self.topo.router_list[router]['networks']
        snat = self.topo.router_list[router]['snat']
        if not self.webui.create_router(
                router_name,
                networks,
                state,
                gateway,
                snat):
            result = result and False
    return result
    # end createPort


def createDnsServer(self, option='contrail'):
    if not hasattr(self.topo, 'dns_server_list'):
        self.logger.info("No dns server configs found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating DNS Server")
    for dserver in self.topo.dns_server_list:
        server_name = dserver
        domain_name = self.topo.dns_server_params[dserver]['domain_name']
        rr_order = self.topo.dns_server_params[dserver]['rr_order']
        fip_record = self.topo.dns_server_params[dserver]['fip_record']
        ipam_list = self.topo.dns_server_params[dserver]['ipam_list']
        dns_forwarder = self.topo.dns_server_params[dserver]['dns_forwarder']
        ttl = self.topo.dns_server_params[dserver]['ttl']
        if not self.webui.create_dns_server(
                server_name,
                domain_name,
                rr_order,
                fip_record,
                ipam_list,
                ttl,
                dns_forwarder):
            result = result and False
    return result
# end createDnsServer


def createDnsRecord(self, option='contrail'):
    if not hasattr(self.topo, 'dns_record_list'):
        self.logger.info("No DNS record configs found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating DNS Record")
    for dns_record in self.topo.dns_record_list:
        host_name = self.topo.dns_record_params[dns_record]['host_name']
        server_name = self.topo.dns_record_params[dns_record]['server_name']
        ip_address = self.topo.dns_record_params[dns_record]['ip_address']
        record_type = self.topo.dns_record_params[dns_record]['type']
        dns_class = self.topo.dns_record_params[dns_record]['dns_class']
        ttl = self.topo.dns_record_params[dns_record]['ttl']
        if not self.webui.create_dns_record(
                server_name,
                host_name,
                ip_address,
                record_type,
                dns_class,
                ttl):
            result = result and False
    return result
# end createDnsRecord

def createBgpaas(self, option='contrail'):
    if not hasattr(self.topo, 'bgpaas_list'):
        self.logger.info("No bgpaas config found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating bgpaas")
    for bgpaas in self.topo.bgpaas_list:
        autonomous_system = self.topo.bgpaas_params[bgpaas]['autonomous_system']
        ip_addr = self.topo.bgpaas_params[bgpaas]['ip_address']
        hold_time = self.topo.bgpaas_params[bgpaas]['hold_time']
        loop_count = self.topo.bgpaas_params[bgpaas]['loop_count']
        bgpaas_name = bgpaas
        if not self.webui.create_bgpaas(
                bgpaas_name,
                autonomous_system,
                ip_addr,
                hold_time,
                loop_count):
            result = result and False
    return result
# end createBgpaas

def createLinkLocalService(self):
    result = True
    if not hasattr(self.topo, 'link_local_service_list'):
        self.logger.warn("No link local service config in topo file")
        return result
    self.logger.info("Create Link Local Service")
    if not self.webui.create_link_local_service(
               self.topo.link_local_service_list,
               self.topo.link_local_service_params):
        result = False
    return result
# end createLinkLocalService

def createSVCApplianceSet(self):
    result = True
    if not hasattr(self.topo, 'svc_appl_set_list'):
        self.logger.warn("No Service Appliance set in topo file")
        return result
    self.logger.info("Create Service Appliance Set")
    if not self.webui.create_service_appliance_set(
               self.topo.svc_appl_set_list,
               self.topo.svc_appl_set_params):
        result = False
    return result
# end createServApplianceSet

def createSVCAppliances(self):
    result = True
    if not hasattr(self.topo, 'svc_appliances_list'):
        self.logger.warn("No Service Appliance set in topo file")
        return result
    self.logger.info("Create Service Appliance Set")
    if not self.webui.create_service_appliances(
               self.topo.svc_appliances_list,
               self.topo.svc_appliances_params):
        result = False
    return result
# end createServAppliances
