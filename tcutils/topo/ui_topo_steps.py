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

def attachQosToVN(self):
    if not hasattr(self.topo, 'vn_qos_list'):
        self.logger.info("No qos config for VN found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing VN to attach QoS config")
    for vn in self.topo.vnet_list:
        if vn in self.topo.vn_qos_params:
            qos_name = self.topo.vn_qos_params[vn]
            if not self.webui.attach_qos_to_vn(
                    qos_name,
                    vn):
                result = result and False
            self.addCleanup(
                self.webui.detach_qos_from_vn(qos_name, vn))
    return result
# end attachQosToVN

def createNetworkRouteTable(self):
    if not hasattr(self.topo, 'nrt_list'):
        self.logger.info("No network route table config found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating Network Route Table")
    for nrt in self.topo.nrt_list:
        nrt_param = self.topo.nrt_params[nrt]
        prefix = nrt_param['prefix']
        nh_type = nrt_param['nh_type']
        nexthop = nrt_param['nexthop']
        nrt_name = nrt
        if not self.webui.create_network_route_table(
                nrt_name,
                prefix,
                nexthop,
                nh_type):
            result = result and False
    return result
# end createNetworkRouteTable

def attachNrtToVN(self):
    if not hasattr(self.topo, 'vn_nrt_list'):
        self.logger.info("No nrt config for VN found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing VN to attach Route table")
    for vn in self.topo.vnet_list:
        if vn in self.topo.vn_nrt_params:
            nrt_name = self.topo.vn_nrt_params[vn]
            if not self.webui.attach_nrt_to_vn(
                    nrt_name,
                    vn):
                result = result and False
            self.addCleanup(
                self.webui.detach_nrt_from_vn(nrt_name, vn))
    return result
# end attachNrtToVN

def createRoutingPolicy(self):
    if not hasattr(self.topo, 'rp_list'):
        self.logger.info("No routing policy config found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating Routing Policy")
    if not self.webui.create_routing_policy(
            self.topo.rp_list,
            self.topo.rp_params):
        result = result and False
    return result
# end createRoutingPolicy

def createRouteAggregate(self):
    if not hasattr(self.topo, 'ragg_list'):
        self.logger.info("No route aggregate config found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Creating Route Aggregate")
    if not self.webui.create_route_aggregate(
            self.topo.ragg_list,
            self.topo.ragg_params):
        result = result and False
    return result
# end createRouteAggregate

def attachRpToSI(self):
    if not hasattr(self.topo, 'si_rp_list'):
        self.logger.info("No rp config for SI found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing SI to attach Routing policy")
    for si in self.topo.si_list:
        if si in self.topo.si_rp_params:
            int_rp = self.topo.si_rp_params[si]
            if not self.webui.attach_detach_rpol_to_si(
                    int_rp,
                    si):
                result = result and False
            self.addCleanup(
                self.webui.attach_detach_rpol_to_si(int_rp, si, attach=False))
    return result
# end attachRpToSI

def attachRaToSI(self):
    if not hasattr(self.topo, 'si_ra_list'):
        self.logger.info("No ra config for SI found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing SI to attach Route aggregate")
    for si in self.topo.si_list:
        if si in self.topo.si_ra_params:
            int_ra = self.topo.si_ra_params[si]
            if not self.webui.attach_detach_ragg_to_si(
                    int_ra,
                    si):
                result = result and False
            self.addCleanup(
                self.webui.attach_detach_ragg_to_si(int_ra, si, attach=False))
    return result
# end attachRaToSI

def attachShcToSI(self):
    if not hasattr(self.topo, 'si_shc_list'):
        self.logger.info("No shc config for SI found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing SI to attach Health Check")
    for si in self.topo.si_list:
        if si in self.topo.si_shc_params:
            int_shc = self.topo.si_shc_params[si]
            if not self.webui.attach_detach_shc_to_si(
                    int_shc,
                    si):
                result = result and False
            self.addCleanup(
                self.webui.attach_detach_shc_to_si(int_shc, si, attach=False))
    return result
# end attachShcToSI

def createLogStatistic(self):
    result = True
    if not hasattr(self.topo, 'log_stat_list'):
        self.logger.warn("No log stat config found in topo file")
        return result
    self.logger.info("Create Log Statistic")
    if not self.webui.create_log_statistic(
               self.topo.log_stat_list,
               self.topo.log_stat_params):
        result = False
    return result
# end createLogStatistic

def createFlowAging(self):
    result = True
    if not hasattr(self.topo, 'flow_age_proto_list'):
        self.logger.warn("No flow aging config found in topo file")
        return result
    self.logger.info("Create Flow aging")
    if not self.webui.create_flow_aging(
               flow_list=self.topo.flow_age_proto_list,
               params=self.topo.flow_age_proto_params):
        result = False
    return result
# end createFlowAging

def attachIntfTabToPort(self):
    if not hasattr(self.topo, 'intf_route_table_list'):
        self.logger.info("No Intf table config for Port found in topo file")
        return True
    result = True
    self.logger.info("Setup step: Editing Port to attach Interface table")
    ports = self.topo.port_intf_params.keys()
    for port in ports:
        if port in self.topo.port_list:
            intf_name = self.topo.port_intf_params[port]
            if not self.webui.attach_and_detach_intf_tab_to_port(
                   intf_name, port):
                result = result and False
            self.addCleanup(
                self.webui.attach_and_detach_intf_tab_to_port(intf_name, port,
                option='detach'))
        else:
            result = result and False
    return result
# end attachIntfTabToPort
