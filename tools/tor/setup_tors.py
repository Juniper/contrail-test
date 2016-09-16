import os
import sys
import json
import ConfigParser
import ast
import logging

from tor_fixture import ToRFixtureFactory
from physical_router_fixture import PhysicalRouterFixture
from common.contrail_test_init import ContrailTestInit
from physical_device_fixture import PhysicalDeviceFixture
from vcpe_router_fixture import VpeRouterFixture
from virtual_router_fixture import VirtualRouterFixture

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
logging.getLogger('paramiko.transport').setLevel(logging.WARN)


if __name__ == "__main__":
    init_obj = ContrailTestInit(sys.argv[1])
    init_obj.read_prov_file()
    for (device, device_dict) in init_obj.physical_routers_data.iteritems():
        if device_dict['type'] == 'tor':
            tor_obj = ToRFixtureFactory.get_tor(
                device_dict['name'],
                device_dict['mgmt_ip'],
                vendor=device_dict['vendor'],
                ssh_username=device_dict['ssh_username'],
                ssh_password=device_dict['ssh_password'],
                tunnel_ip=device_dict['tunnel_ip'],
                ports=device_dict['ports'],
                tor_ovs_port=device_dict['tor_ovs_port'],
                tor_ovs_protocol=device_dict['tor_ovs_protocol'],
                controller_ip=device_dict['controller_ip'],
                cfgm_ip=init_obj.cfgm_ip,
                auth_server_ip=init_obj.auth_ip,
                bringup=True)
            tor_obj.setUp()
        if device_dict['type'] == 'router':
            phy_router_obj = PhysicalRouterFixture(
                device_dict['name'], device_dict['mgmt_ip'],
                model=device_dict['model'],
                vendor=device_dict['vendor'],
                asn=device_dict['asn'],
                ssh_username=device_dict['ssh_username'],
                ssh_password=device_dict['ssh_password'],
                mgmt_ip=device_dict['mgmt_ip'],
                tunnel_ip=device_dict['tunnel_ip'],
                ports=device_dict['ports'],
                cfgm_ip=init_obj.cfgm_ip,
                auth_server_ip=init_obj.auth_ip,
                )
            phy_router_obj.setUp()
        if device_dict['type'] == 'vcenter_gateway':
               vrouter_obj = VirtualRouterFixture(device_dict['name'],
                                      'embedded' )
               vrouter_obj.setUp()

               vcpe_router_obj = VpeRouterFixture(
                   device_dict['name'], device_dict['mgmt_ip'],
                   ssh_username=device_dict['ssh_username'],
                   ssh_password=device_dict['ssh_password'],
                   mgmt_ip=device_dict['mgmt_ip'],
                   ports=device_dict['ports'],
                   )
               vcpe_router_obj.setUp()
               vcpe_router_obj.vrouter_ref_set(vrouter_obj.vr)
               vcpe_router_obj.setup_physical_ports()
               for port in device_dict['ports']:
                   ifup_cmd = 'ifconfig %s up'%port
                   init_obj.run_cmd_on_server(device_dict['mgmt_ip'],ifup_cmd )
    # end for


    
