from future import standard_library
standard_library.install_aliases()
import os
import sys
import json
import configparser
import ast
import logging

from physical_router_fixture import PhysicalRouterFixture
from common.contrail_test_init import ContrailTestInit
from physical_device_fixture import PhysicalDeviceFixture
from vcpe_router_fixture import VpeRouterFixture
from virtual_router_fixture import VirtualRouterFixture
from common.device_connection import NetconfConnection

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
logging.getLogger('paramiko.transport').setLevel(logging.WARN)


if __name__ == "__main__":
    init_obj = ContrailTestInit(sys.argv[1])
    as4_ext_routers_dict = dict(init_obj.as4_ext_routers)
    for (device, device_dict) in init_obj.physical_routers_data.items():

        if device in as4_ext_routers_dict:
           continue

        if init_obj.deployer == 'rhosp':
            cfgm_ips = (init_obj.contrail_configs.get('CONTROL_NODES')).split(',')
            stmts = ['set protocols bgp group %s type internal' %device_dict['group_name'],
                    'del protocols bgp group %s' %device_dict['group_name'],
                    'set protocols bgp group %s type internal' %device_dict['group_name'],
                    'set protocols bgp group %s local-address %s' %(device_dict['group_name'], device_dict['control_ip']),
                    'set protocols bgp group %s family inet unicast' %device_dict['group_name'],
                    'set protocols bgp group %s family inet6 unicast' %device_dict['group_name'],
                    'set protocols bgp group %s family inet-vpn unicast' %device_dict['group_name'],
                    'set protocols bgp group %s local-as %s' %(device_dict['group_name'], device_dict['asn']),
                    'set protocols bgp group %s neighbor %s' %(device_dict['group_name'], cfgm_ips[0]),
                    'set protocols bgp group %s neighbor %s' %(device_dict['group_name'], cfgm_ips[1]),
                    'set protocols bgp group %s neighbor %s' %(device_dict['group_name'], cfgm_ips[2])]
            router_netconf = NetconfConnection(device_dict['mgmt_ip'])
            router_netconf.connect()
            router_netconf.config(stmts)
            router_netconf.disconnect()

        if device_dict.get('role') in ['leaf', 'spine', 'pnf']:
            continue
        phy_router_obj = PhysicalRouterFixture(
                device_dict['name'],
                device_dict['mgmt_ip'],
                asn=device_dict['asn'],
                model=device_dict.get('model', 'mx'),
                vendor=device_dict.get('vendor', 'juniper'),
                ssh_username=device_dict.get('ssh_username'),
                ssh_password=device_dict.get('ssh_password'),
                tunnel_ip=device_dict.get('tunnel_ip'),
                ports=device_dict.get('ports'),
                dm_managed=device_dict.get('dm_managed'),
                tsn=device_dict.get('tsn'),
                role=device_dict.get('role'),
                cfgm_ip=init_obj.cfgm_ip,
                auth_server_ip=init_obj.auth_ip,
                inputs=init_obj,
                username=init_obj.admin_username,
                password=init_obj.admin_password,
                project_name=init_obj.admin_tenant,
                domain=init_obj.admin_domain,
                orchestrator=init_obj.orchestrator
                )
        phy_router_obj.setUp()
        phy_router_obj.verify_bgp_peer()

        if device_dict['type'] == 'vcenter_gateway':
               vrouter_obj = VirtualRouterFixture(device_dict['name'],
                                      'embedded', 
                                      cfgm_ip=init_obj.cfgm_ip,
                                      auth_server_ip=init_obj.auth_ip,
                                       )
               vrouter_obj.setUp()

               vcpe_router_obj = VpeRouterFixture(
                   device_dict['name'], device_dict['mgmt_ip'],
                   ssh_username=device_dict['ssh_username'],
                   ssh_password=device_dict['ssh_password'],
                   mgmt_ip=device_dict['mgmt_ip'],
                   ports=device_dict['ports'],
                   cfgm_ip=init_obj.cfgm_ip,
                   auth_server_ip=init_obj.auth_ip,
                   )
               vcpe_router_obj.setUp()
               vcpe_router_obj.vrouter_ref_set(vrouter_obj.vr)
               vcpe_router_obj.setup_physical_ports()
               for port in device_dict['ports']:
                   ifup_cmd = 'ifconfig %s up'%port
                   init_obj.run_cmd_on_server(device_dict['mgmt_ip'],ifup_cmd )
    # end for
