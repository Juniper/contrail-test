import argparse
import ConfigParser

import eventlet
import os
import sys

import uuid
import time
import errno
import socket
import subprocess

from vnc_api.vnc_api import *
import cfgm_common.exceptions
from netaddr import IPNetwork


import json
from pprint import pformat
from common.openstack_libs import neutron_client as client
from common.openstack_libs import neutron_http_client as HTTPClient
from common.openstack_libs import neutron_exception as exceptions

def get_ip(ip_w_pfx):
    return str(IPNetwork(ip_w_pfx).ip)

class VnCfg(object):

    def __init__(self):
        self._quantum = None
        self.parent_fq_name = ['default-domain', 'default-project',
                'ip-fabric', '__default__']
        pass

    def _run(self, args_str=None, oper=''):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        if self._args.oper == 'add-bgp-router' or 'del-bgp-router':
            proj_name = 'admin'
        else:
            proj_name = 'demo'

        if self._quantum == None:
            httpclient = HTTPClient(username='admin',
                                    tenant_name='demo',
                                    password='contrail123',
                                    # region_name=self._region_name,
                                    auth_url='http://%s:5000/v2.0' % (self._args.api_server_ip))
            httpclient.authenticate()

            #OS_URL = httpclient.endpoint_url
            OS_URL = 'http://%s:9696/' % (self._args.api_server_ip)
            OS_TOKEN = httpclient.auth_token
            self._quantum = client.Client(
                '2.0', endpoint_url=OS_URL, token=OS_TOKEN)

	    self._vnc_lib = VncApi(username=self._args.admin_user,
                                   password=self._args.admin_password,
                                   tenant_name=self._args.admin_tenant_name,
                                   api_server_host=self._args.api_server_ip,
                                   api_server_port=self._args.api_server_port,
                                   api_server_url='/',
                                   auth_host=self._args.api_server_ip)
           
            self._proj_obj = self._vnc_lib.project_read(
                fq_name=['default-domain', 'default-project'])
            self._ipam_obj = self._vnc_lib.network_ipam_read(
                fq_name=['default-domain', 'default-project', 'default-network-ipam'])

        if self._args.oper == 'add':
            self._create_vn(self._args.vn_name, self._args.public_subnet)
        elif self._args.oper == 'del':
            self._delete_vn(self._args.vn_name)
        elif self._args.oper == 'add-list':
            self._create_vn_list(self._args.vn_list)
        elif self._args.oper == 'add-bgp-router':
            self._create_bgp_router(self._args.rtr_type, self._args.rtr_name, self._args.rtr_ip, self._args.rtr_asn, 
             [self._args.rtr_peers])
        elif self._args.oper == 'del-bgp-router':
            self._delete_bgp_router(self._args.rtr_name)


    # end __init__

    def _delete_bgp_router(self, router_name):
        vnc_lib = self._vnc_lib

        rt_inst_obj = self._get_rt_inst_obj()

        fq_name = rt_inst_obj.get_fq_name() + [router_name]
        cur_obj = vnc_lib.bgp_router_read(fq_name=fq_name)

        vnc_lib.bgp_router_delete(id=cur_obj.uuid)
        
    def _create_bgp_router(self, router_type, router_name, router_ip,
                       router_asn, peer_list = [], address_families=[], md5=None):
        if not address_families:
            address_families = ['route-target', 'inet-vpn', 'e-vpn', 'erm-vpn',
                                'inet6-vpn']
            if router_type != 'control-node':
                address_families.remove('erm-vpn')

        if router_type != 'control-node':
            if 'erm-vpn' in address_families:
                raise RuntimeError("Only contrail bgp routers can support "
                                   "family 'erm-vpn'")
        bgp_addr_fams = AddressFamilies(address_families)

        bgp_sess_attrs = [
            BgpSessionAttributes(address_families=bgp_addr_fams)]
        bgp_sessions = [BgpSession(attributes=bgp_sess_attrs)]
        bgp_peering_attrs = BgpPeeringAttributes(session=bgp_sessions)

        rt_inst_obj = self._get_rt_inst_obj()

        vnc_lib = self._vnc_lib

        if router_type == 'control-node':
            vendor = 'contrail'
        elif router_type == 'router':
            vendor = 'ixia'
        else:
            vendor = 'unknown'

        router_params = BgpRouterParams(router_type=router_type,
            vendor=vendor, autonomous_system=int(router_asn),
            identifier=get_ip(router_ip),
            address=get_ip(router_ip),
            port=179, address_families=bgp_addr_fams)

        bgp_router_obj = BgpRouter(router_name, rt_inst_obj,
                                   bgp_router_parameters=router_params)

        if peer_list[0]:
            for item in peer_list:
                peer_obj = vnc_lib.bgp_router_read(
                        fq_name = self.parent_fq_name + [item])
                bgp_router_obj.add_bgp_router(peer_obj, bgp_peering_attrs)

        # Return early with a log if it already exists
        try:
            fq_name = bgp_router_obj.get_fq_name()
            existing_obj = vnc_lib.bgp_router_read(fq_name=fq_name)
            if md5:
                bgp_params = existing_obj.get_bgp_router_parameters()
                # set md5
                print "Setting md5 on the existing uuid"
                md5 = {'key_items': [ { 'key': md5 ,"key_id":0 } ], "key_type":"md5"}
                bgp_params.set_auth_data(md5)
                existing_obj.set_bgp_router_parameters(bgp_params)
                vnc_lib.bgp_router_update(existing_obj)
            print ("BGP Router " + pformat(fq_name) +
                   " already exists with uuid " + existing_obj.uuid)
            return
        except NoIdError:
            pass

        cur_id = vnc_lib.bgp_router_create(bgp_router_obj)


    def _get_rt_inst_obj(self):
        vnc_lib = self._vnc_lib

        # TODO pick fqname hardcode from common
        rt_inst_obj = vnc_lib.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])

        return rt_inst_obj


         
    def _delete_vn(self, vn_name):
        vn_fq_name = VirtualNetwork(vn_name, self._proj_obj).get_fq_name()
        try:
            self._vnc_lib.virtual_network_delete(fq_name=vn_fq_name)
        except cfgm_common.exceptions.NoIdError:
            pass
    # end _delete_vn

    def _create_subnet(self, cidr, net_id, ipam_fq_name=None):
        if not ipam_fq_name:
            ipam_fq_name = NetworkIpam().get_fq_name()

        subnet_req = {'network_id': net_id,
                      'cidr': cidr,
                      'ip_version': 4,
                      'contrail:ipam_fq_name': ipam_fq_name}
        subnet_rsp = self._quantum.create_subnet({'subnet': subnet_req})
        subnet_cidr = subnet_rsp['subnet']['cidr']
        return subnet_rsp['subnet']['id']
    # end _create_subnet

    def _create_vn(self, vn_name, vn_subnet):

        vn_obj = VirtualNetwork(vn_name, parent_obj=self._proj_obj)
        pfx = vn_subnet.split('/')[0]
        pfx_len = int(vn_subnet.split('/')[1])
        subnet_vnc = IpamSubnetType(subnet=SubnetType(pfx, pfx_len))
        vnsn_data = VnSubnetsType([subnet_vnc])
        vn_obj.add_network_ipam(self._ipam_obj, vnsn_data)

        try:
            self._vnc_lib.virtual_network_create(vn_obj)
        except RefsExistError:
            pass
    # end _create_vn_list`

    def _add_route_target(self, routing_instance_name=None, router_asn=None,
            route_target_number=None):
        vn_fq_name = VirtualNetwork(routing_instance_name, self._proj_obj).get_fq_name()
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        vn_obj = self._vnc_lib.virtual_network_read(fq_name=vn_fq_name)
        route_targets = vn_obj.get_route_target_list()
        if route_targets and (rtgt_val not in route_targets.get_route_target()):
            route_targets.add_route_target(rtgt_val)
        else:
            route_targets = RouteTargetList([rtgt_val])
        vn_obj.set_route_target_list(route_targets)
        self._vnc_lib.virtual_network_update(vn_obj)
    # end add_route_target

    def _del_route_target(self, routing_instance_name=None, router_asn=None,
            route_target_number=None):
        result = True
        vn_fq_name = VirtualNetwork(routing_instance_name, self._proj_obj).get_fq_name()
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        vn_obj = self._vnc_lib.virtual_network_read(fq_name=vn_fq_name)

        if rtgt_val not in vn_obj.get_route_target_list().get_route_target():
            self.logger.error("%s not configured for VN %s" %
                              (rtgt_val, rt_inst_fq_name[:-1]))
            result = False
        route_targets = vn_obj.get_route_target_list()
        route_targets.delete_route_target(rtgt_val)
        if route_targets.get_route_target():
            vn_obj.set_route_target_list(route_targets)
        else:
            vn_obj.set_route_target_list(None)
        self._vnc_lib.virtual_network_update(vn_obj)
        return result
    # end del_route_target

    def _parse_args(self, args_str):
        '''
        Eg. python demo_cfg.py --api_server_ip 127.0.0.1
                               --api_server_port 8082
                               --public_subnet 10.84.41.0/24
                               --vn_name instance1
                               --oper add|del
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        defaults = {
            'api_server_ip': '127.0.0.1',
            'api_server_port': '8082',
        }
        ksopts = {
            'admin_user': 'admin',
            'admin_password': 'contrail123',
            'admin_tenant_name': 'demo', #'default-domain',
            'vn_name          ': 'public'
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            defaults.update(dict(config.items("DEFAULTS")))
            if 'KEYSTONE' in config.sections():
                ksopts.update(dict(config.items("KEYSTONE")))

        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        parser = argparse.ArgumentParser(
            # Inherit options from config_parser
            parents=[conf_parser],
            # print script description with -h/--help
            description=__doc__,
            # Don't mess with format of description
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        defaults.update(ksopts)
        parser.set_defaults(**defaults)

        parser.add_argument("--api_server_ip",
                            help="IP address of api server")
        parser.add_argument("--api_server_port", help="Port of api server")
        parser.add_argument("--public_subnet", help="Subnet for public VN")
        parser.add_argument(
            "--admin_user", help="Name of keystone admin user")
        parser.add_argument("--admin_password",
                            help="Password of keystone admin user")
        parser.add_argument("--admin_tenant_name",
                            help="Tenamt name for keystone admin user")
        parser.add_argument("--vn_name", help="Name of the virtunal network")
        parser.add_argument("--oper", help="Indicates add-vn|del-vn|bgp-rtr-add|bgp-rtr-del")
        parser.add_argument('--rtr_type', nargs='?', default='', type=str, help='router type')
        parser.add_argument('--rtr_name', nargs='?', default='', type=str, help='router name')
        parser.add_argument('--rtr_ip', nargs='?', default='', type=str, help='router ip')
        parser.add_argument('--rtr_asn', nargs='?', default='64512', type=str, help='router asn')
        parser.add_argument('--rtr_peers', nargs='?', default='', type=str, help='router peers')

        self._args = parser.parse_args(remaining_argv)

    # end _parse_args

# end class VnCfg


def main(args_str=None):
    VnCfg()._run(args_str)
# end main

if __name__ == "__main__":
    main()
