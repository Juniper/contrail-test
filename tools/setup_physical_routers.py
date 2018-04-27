import os
import sys
import json
import ConfigParser
import ast
import logging

from physical_router_fixture import PhysicalRouterFixture
from common.contrail_test_init import ContrailTestInit
from physical_device_fixture import PhysicalDeviceFixture
from vcpe_router_fixture import VpeRouterFixture
from virtual_router_fixture import VirtualRouterFixture

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
logging.getLogger('paramiko.transport').setLevel(logging.WARN)


if __name__ == "__main__":
    init_obj = ContrailTestInit(sys.argv[1])
    for (device, device_dict) in init_obj.physical_routers_data.iteritems():
        if device_dict['type'] in ['router', 'tor']:
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
                dm_managed=device_dict.get('dm_managed', True),
                tsn=device_dict.get('tsn'),
                role=device_dict.get('role'),
                cfgm_ip=init_obj.cfgm_ip,
                auth_server_ip=init_obj.auth_ip,
                inputs=init_obj,
                username=init_obj.admin_username,
                password=init_obj.admin_password,
                project_name=init_obj.admin_tenant,
                domain=init_obj.admin_domain
                )
            phy_router_obj.setUp()
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
