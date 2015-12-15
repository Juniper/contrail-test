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

import json
from pprint import pformat
from common.openstack_libs import neutron_client as client
from common.openstack_libs import neutron_http_client as HTTPClient
from common.openstack_libs import neutron_exception as exceptions


class VnCfg(object):

    def __init__(self):
        self._quantum = None
        pass

    def _run(self, args_str=None, oper=''):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

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

    # end __init__

    # def _create_vn(self, vn_name, vn_subnet):
    #    print "Creating network %s, subnet %s" %(vn_name, vn_subnet)
    #    net_req = {'name': '%s' %(vn_name)}
    #    net_rsp = self._quantum.create_network({'network': net_req})
    #    net1_id = net_rsp['network']['id']
    #    net1_fq_name = net_rsp['network']['contrail:fq_name']
    #    net1_fq_name_str = ':'.join(net1_fq_name)
    #    self._create_subnet(unicode(vn_subnet), net1_id)
    # end _create_vn

    # def _delete_vn(self, vn_name):
    #    print "Deleting network %s" %(vn_name)

    #    net_id = 0
    #    net_rsp = self._quantum.list_networks()
    #    for (x,y) in [(network['name'], network['id']) for network in net_rsp['networks']]:
    #        if vn_name == x :
    #            net_id = y
    #            break
    #    if net_id:
    #        net_rsp = self._quantum.delete_network(net_id)
    #    else:
    #        print "Error deleting network, may not exist.. %s" %(vn_name)

    # end _delete_vn

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
        parser.add_argument("--oper", help="Indicates add|del vn")

        self._args = parser.parse_args(remaining_argv)

    # end _parse_args

# end class VnCfg


def main(args_str=None):
    VnCfg(args_str)
# end main

if __name__ == "__main__":
    main()
