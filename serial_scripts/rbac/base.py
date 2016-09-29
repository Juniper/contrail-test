import os
import uuid
import test_v1
from common import isolated_creds
#from contrailapi import ContrailApi
import project_test
from common.connections import ContrailConnections
from tcutils import util
from time import sleep

from common.openstack_libs import ks_client as ksclient
from common.openstack_libs import ks_exceptions
from common.openstack_libs import keystoneclient
from keystone_tests import KeystoneCommands
from vnc_api.vnc_api import *
import keystoneclient.v2_0.client as keystone
from keystonemiddleware import auth_token
import cfgm_common
import keystoneclient.exceptions as kc_exceptions
from tcutils.util import get_random_name
from user_test import UserFixture

class BaseRbac(test_v1.BaseTestCase_v1):
    @classmethod
    def setUpClass(cls):
        super(BaseRbac, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.auth= cls.connections.auth
        cls.orch = cls.connections.orch
        cls.api_s_inspect = cls.connections.api_server_inspect

    def create_role_dict(self, acl_obj, acl_role, acl_crud, perm = []):
        role_dict = {'rule_object': '', 'perms':[]}
        role_dict['rule_object'] = acl_obj
        perm_list = list(self.create_perm_dict(acl_role, acl_crud))
        role_dict = {'rule_object': acl_obj, 'perms':[perm_list]}
        role_dict['perms'] = perm_list
        return role_dict 

    def create_perm_dict(self, acl_role='admin', acl_crud='CRUD'):

        perm = {'role': '', 'crud': ''}
        perm['role'] = acl_role
        perm['crud'] = acl_crud
        return [perm]

    def acl_fq_name(self, tenant, domain, acl_name='default-api-access-list'):
        acl_list = []
        acl_list.append(domain)
        acl_list.append(tenant)
        acl_list.append(acl_name)
        return acl_list 

    def verify_acl_in_api_introp(self, acl_id):
        acl_api = self.api_s_inspect.get_api_introspect_acl(acl_id)
        if not acl_api:
            self.logger.warn("acl with id  %s not found in api server" % (acl_id))
        self.logger.info("acl with id  %s created successfully in api server" % (acl_id))
        return acl_api

    def verify_vn_perms2_in_api_introp(self, vn_id):
        vn_api = self.api_s_inspect.get_cs_vn_by_id(vn_id, refresh=True)
        if not vn_api:
            self.logger.warn("vn id %s not found in api:" % (vn_id)) 
        introp_perms2 = vn_api.perms2()
        self.logger.info("vn with id  %s created successfully in api server" % (vn_id))
        return introp_perms2

    def role_member_objects(obj_nw=None):
        obj_nw = ['*', 'virtual-networks', 'floating-ip', 'virtual-network', 'floating-ips', 'virtual-machines-interfaces',
                 'security-groups', 'fqname-to-id', 'projects', 'security-groups', 'network-ipam',
                 'networks-ipams', 'api-access-list ', 'subnets', 'multi-tenancy-with-rbac ', 'route-target', 
                 'access-control-lists', 'network-policy', 'network-policys', 'ref-update']
        return obj_nw

    def perm2_dict(self, tenant_uuid, global_access_no, share_list=[]):
         perm2_dict = {'owner':tenant_uuid, 'owner_access':7, 'global_access':global_access_no, 'share':share_list}
         return perm2_dict
