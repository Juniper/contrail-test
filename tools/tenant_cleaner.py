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
import logging

from tcutils.util import retry
from keystoneclient.v2_0 import client as ksclient
from novaclient import client as novaclient

logging.getLogger().setLevel(logging.WARN)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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
        nova_objects_deleted = self.cleanup_nova_objects(tenants)
        return_value = True
        failed_tenants = []
        for tenant in tenants:
            if self.verify_nova_vms_deleted(tenant):
                is_deleted, contrail_objects_deleted = self.cleanup_contrail_objects(tenant)
                if is_deleted:
                    if not nova_objects_deleted[tenant] and not contrail_objects_deleted:
                        log.info("No objects found in tenant %s" % tenant)
                    elif not nova_objects_deleted[tenant]:
                        log.info("No nova objects found in tenant %s" % tenant)
                    elif not contrail_objects_deleted:
                        log.info("No contrail objects found in tenant %s" % tenant)
                else:
                    log.error("Contrail object cleanup failed for the tenant %s" % tenant)
                    log.debug("Continuing to other tenants")
                    return_value = False
                    failed_tenants.append(tenant)
            else:
                log.error("Nova VMs cleaning failed for the tenant %s" % tenant)
                log.debug("Continuing other tenants")
                return_value = False
                failed_tenants.append(tenant)

        return (return_value, failed_tenants)

    def _get_keystone_client(self):
        ks=ksclient.Client(username=self.username, password=self.password,
                     tenant_name=self.auth_tenant, auth_url=self.auth_url)
        return ks

    def get_keystone_token(self):
        ks=self._get_keystone_client()
        return ks.auth_ref['token']['id']

    def _delete_ref_object(self, url, fresh_delete=True):
        ret = requests.delete(url, headers=self.headers)
        if ret.status_code == 200:
            log.info("Deleted: %s" %(url))
            return True
        if ret.status_code != 200:
            #Avoid infinite loop in case of delete failure, so second
            # delete should cause return anyway
            if not fresh_delete:
                return False
            log.debug("Status code is %s" % ret.status_code)
            child_urls = re.findall(
                'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                ret.content
            )
            if child_urls:
                log.debug("Deleting children %s" % child_urls)
                for child_url in child_urls:
                    self._delete_ref_object(child_url)
                self._delete_ref_object(url, False)

    @retry(delay=5, tries=10)
    def verify_nova_vms_deleted(self, tenant):
        log.debug('Verifying nova VM cleanup on tenant %s' % tenant)
        with novaclient.Client(2, self.username, self.password, tenant, self.auth_url) as nova:
            if not nova.servers.list():
                return True
            else:
                log.debug("Nova VMs are not cleaned up till yet, would retry")
                return False

    def cleanup_nova_objects(self, tenant):
        if isinstance(tenant,list):
            objects_deleted = {}
            for t in tenant:
                objects_deleted[t]=self.cleanup_nova_objects(t)
            return objects_deleted
        elif isinstance(tenant, str):
            with novaclient.Client(2, self.username, self.password, tenant, self.auth_url) as nova:
                objects_deleted = []
                for server in nova.servers.list():
                    log.info("Deleting Server: %s" % server.name)
                    nova.servers.delete(server)
                    objects_deleted.append(server.name)
                return objects_deleted

    def _get_available_tenants(self):
        if not self.available_tenants:
            proj_url = "http://%s:%s/projects" %(self._server_ip, self._server_port)
            ret = requests.get(proj_url, headers=self.headers)
            if ret.status_code != 200:
                log.error("Cannot get list of projects from %s:%s" %(self._server_ip, self._server_port))
                sys.exit(1)
            self.available_tenants = json.loads(ret.content)['projects']

        return self.available_tenants

    def cleanup_contrail_objects(self, tenant):
        if isinstance(tenant,list):
            objects_deleted = {}
            is_deleted = {}
            for t in tenant:
                is_deleted[t], objects_deleted[t] = self.cleanup_contrail_objects(t)

            return (is_deleted, objects_deleted)
        elif isinstance(tenant, str):
            tenants_available = self._get_available_tenants()
            for available_tenant in tenants_available:
                sucessfully_deleted = True
                if tenant in available_tenant['fq_name']:
                    ret = requests.get(available_tenant['href'], headers = self.headers)
                    if ret.status_code == 200:
                        child_urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ret.content)
                        if child_urls:
                            objects_deleted = []
                            for child_url in child_urls:
                                if not re.match(r'.*/(project|domain)/.*',child_url):
                                    if not self._delete_ref_object(child_url):
                                        sucessfully_deleted = False
                                    objects_deleted.append(child_url)
                            return (sucessfully_deleted, objects_deleted)


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
        "-i","--ip", type=str,
        help = "IP Address of the controller"
    )
    parser.add_argument("--port", type=str, default=8082,
                         help = "Port of the controller")
    parser.add_argument("-d", "--debug", action='store_true', default=False,
        help = "Enable debug messages"
    )
    parser.add_argument(
        'tenant', nargs='+',
        help='List of tenants to be cleaned up \
Note that, the user must have access to the tenants listed'
    )
    args = parser.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)
    tm = Tenant(username=args.user, password=args.password,
                auth_url=args.auth_url, auth_tenant=args.auth_tenant,
                server_ip=args.ip, port=args.port)
    rv, failed_tenants = tm.cleanup(args.tenant)
    if not rv:
        raise Exception('Tenant cleanup failed for the tenants - %s' % failed_tenants)
#end main

if __name__ == "__main__":
    sys.exit(not main(sys.argv[1:]))
