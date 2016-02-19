#!/usr/bin/python
#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#

import argparse
import json
import re
import requests
import sys
import os

from keystoneclient.v2_0 import client as ksclient
from novaclient import client as novaclient


class Tenant(object):

    def __init__(self, token=None, server_ip='127.0.0.1',
                 port=8082,
                 username=os.environ.get('OS_USERNAME', 'admin'),
                 password=os.environ.get('OS_PASSWORD', 'admin'),
                 auth_url=os.environ.get('OS_AUTH_URL', 'http://127.0.0.1:5000/v2.0/'),
                 auth_tenant=os.environ.get('OS_TENANT', 'admin')
                 ):
        self._server_ip = server_ip
        self._server_port = port
        self.username = username
        self.password = password
        self.auth_url = auth_url
        self.auth_tenant = auth_tenant
        self.available_tenants = None

        if token:
            self._token = token
        else:
            self._token = self.get_keystone_token()

        self.headers = {'X-Auth-Token': self._token}

    def cleanup(self, tenants):
        for tenant in tenants:
            nova_objects_deleted = self.cleanup_nova_objects(tenant)
            contrail_objects_deleted = self.cleanup_contrail_objects(tenant)
            if not nova_objects_deleted and not contrail_objects_deleted:
                print "No objects found in tenant %s" % tenant
            elif not nova_objects_deleted:
                print "No nova objects found in tenant %s" % tenant
            elif not contrail_objects_deleted:
                print "No contrail objects found in tenant %s" % tenant

    def _get_keystone_client(self):
        ks=ksclient.Client(username=self.username, password=self.password,
                     tenant_name=self.auth_tenant, auth_url=self.auth_url)
        return ks

    def get_keystone_token(self):
        ks=self._get_keystone_client()
        return ks.auth_ref['token']['id']

    def _delete_ref_object(self, url):
        ret = requests.delete(url, headers=self.headers)
        if ret.status_code == 200:
            print "Deleted: %s" %(url)
        if ret.status_code != 200:
            print "Status code is %s" % ret.status_code
            child_urls = re.findall(
                'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                ret.content
            )
            if child_urls:
                print "Deleting children %s" % child_urls
                for child_url in child_urls:
                    self._delete_ref_object(child_url)
                self._delete_ref_object(url)

    def cleanup_nova_objects(self, tenant):
        if isinstance(tenant,list):
            for t in tenant:
                self.cleanup_nova_objects(t)
        elif isinstance(tenant, str):
            with novaclient.Client(2, self.username, self.password, tenant, self.auth_url) as nova:
                objects_deleted = []
                for server in nova.servers.list():
                    print "Deleting Server: %s" % server.name
                    nova.servers.delete(server)
                    objects_deleted.append(server.name)
                return objects_deleted

    def _get_available_tenants(self):
        if not self.available_tenants:
            proj_url = "http://%s:%s/projects" %(self._server_ip, self._server_port)
            ret = requests.get(proj_url, headers=self.headers)
            if ret.status_code != 200:
                print "Cannot get list of projects from %s:%s" %(self._server_ip, self._server_port)
                sys.exit(1)
            self.available_tenants = json.loads(ret.content)['projects']

        return self.available_tenants

    def cleanup_contrail_objects(self, tenant):
        if isinstance(tenant,list):
            for t in tenant:
                self.cleanup_contrail_objects(t)
        elif isinstance(tenant, str):
            tenants_available = self._get_available_tenants()
            for available_tenant in tenants_available:
                if tenant in available_tenant['fq_name']:
                    ret = requests.get(available_tenant['href'], headers = self.headers)
                    if ret.status_code == 200:
                        child_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ret.content)
                        if child_urls:
                            objects_deleted = []
                            for child_url in child_urls:
                                if not re.match(r'.*/(project|domain)/.*',child_url):
                                    self._delete_ref_object(child_url)
                                    objects_deleted.append(child_url)
                            return objects_deleted


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description='Cleanup provided tenants by removing all objects in it.\
It expect openstack credentials from OS_ environment variables in openrc format.\
The credentials can be provided as commandline arguments also')

    parser.add_argument(
        '--user', type=str,
        default=os.environ.get('OS_USERNAME', 'admin'),
        help='Openstack user, if not provided, try to get it from environment \
variable "OS_USERNAME" with default user as "admin"'
    )
    parser.add_argument(
        '--password', type=str,
        default=os.environ.get('OS_PASSWORD', 'admin'),
        help='Openstack password'
    )
    parser.add_argument(
        '--auth-url', type=str,
        default=os.environ.get('OS_AUTH_URL', 'http://127.0.0.1:5000/v2.0/'),
        help='Openstack auth url, by default try to get from environment variable\
OS_AUTH_URL with default of http://127.0.0.1:5000/v2.0/'
    )
    parser.add_argument(
        '--auth-tenant', type=str,
        default=os.environ.get('OS_TENANT', 'admin'),
        help='Openstack tenant to connect to'
    )
    parser.add_argument(
        "--ip", type=str,
        help = "IP Address of the controller"
    )
    parser.add_argument("--port", type=str, default=8082,
                         help = "Port of the controller")
    parser.add_argument(
        'tenant', nargs='+',
        help='List of tenants to be cleaned up \
Note that, the user must have access to the tenants listed'
    )
    args = parser.parse_args()
    tm = Tenant(username=args.user, password=args.password,
                auth_url=args.auth_url, auth_tenant=args.auth_tenant,
                server_ip=args.ip, port=args.port)
    tm.cleanup(args.tenant)
#end main

if __name__ == "__main__":
    sys.exit(not main(sys.argv[1:]))
