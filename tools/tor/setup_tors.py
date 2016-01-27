import os
import sys
import json
import ConfigParser
import ast

from tor_fixture import ToRFixtureFactory
from physical_router_fixture import PhysicalRouterFixture
from common.contrail_test_init import ContrailTestInit

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
                )
            phy_router_obj.setUp()
    # end for


    
