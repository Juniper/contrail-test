import test
import os
from common.connections import ContrailConnections
from vm_test import VMFixture
from vn_test import VNFixture
from common.openstack_libs import ks_client as ksclient
from vnc_api.vnc_api import *
from keystone_tests import KeystoneCommands

class BaseMultitenancyTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseMultitenancyTest, cls).setUpClass()
        cls.connections = ContrailConnections(cls.inputs, project_name = cls.inputs.project_name,
                                            username = cls.inputs.stack_user, 
                                           password = cls.inputs.stack_password,
                                           logger = cls.logger) 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        auth_url = os.getenv('OS_AUTH_URL') or \
                       'http://' + cls.inputs.openstack_ip + ':5000/v2.0'
        insecure = bool(os.getenv('OS_INSECURE',True))
        cls.key_stone_clients = KeystoneCommands(
            username=cls.inputs.stack_user, password = cls.inputs.stack_password, tenant = cls.inputs.project_name, auth_url=auth_url,
            insecure=insecure)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseMultitenancyTest, cls).tearDownClass()
    #end tearDownClass 

    # create users specified as array of tuples (name, password, role)
    # assumes admin user and tenant exists
    def keystone_create_users(self, user_list):

        cleanup_cmds = []
        user_pass = {}
        user_role = {}
        user_set = set()
        role_set = set()
        for (n, p, r) in user_list:
            user_pass[n] = p
            user_role[n] = r
            user_set.add(n)
            role_set.add(r)

        auth_url = os.getenv('OS_AUTH_URL') or \
                             'http://' + self.inputs.openstack_ip + ':5000/v2.0'
        insecure = bool(os.getenv('OS_INSECURE',True))
        kc = ksclient.Client(
            username=self.inputs.stack_user, password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name, auth_url=auth_url, 
            insecure=insecure)
        users = set([user.name for user in kc.users.list()])
        roles = set([user.name for user in kc.roles.list()])
        tenants = kc.tenants.list()
        admin_tenant = [x for x in tenants if x.name == self.inputs.stack_tenant][0]

        create_user_set = user_set - users
        create_role_set = role_set - roles

        # create missing roles
        for rolename in create_role_set:
            created_role = kc.roles.create(rolename)
            self.addCleanup(kc.roles.delete, created_role)

        # rebuild name->role dictionary from keystone
        role_dict = {}
        for role in kc.roles.list():
            role_dict[role.name] = role

        for name in create_user_set:
            user = kc.users.create(
                name, user_pass[name], '', tenant_id=admin_tenant.id)
            self.addCleanup(kc.users.delete,  user)
            kc.roles.add_user_role(
                user, role_dict[user_role[name]], admin_tenant)
            self.addCleanup(kc.roles.remove_user_role, user,
                            role_dict[user_role[name]], admin_tenant)
    # end keystobe_create_users
    
    # display resource id-perms
    def print_perms(self, perms):
        return '%s/%s %d%d%d' \
            % (perms.permissions.owner, perms.permissions.group,
               perms.permissions.owner_access, 
               perms.permissions.group_access, 
               perms.permissions.other_access)
    # end print_perms
    
    # set id perms for object
    def set_perms(self, obj, mode=None, owner=None, group=None):
        perms = obj.get_id_perms()
        self.logger.info('Current perms %s = %s' %
                         (obj.get_fq_name(), self.print_perms(perms)))

        if mode:
            # convert 3 digit octal permissions to owner/group/other bits
            access = list(mode)
            if len(access) == 4:
                access = access[1:]
            perms.permissions.owner_access = int(access[0])
            perms.permissions.group_access = int(access[1])
            perms.permissions.other_access = int(access[2])

        if owner:
            perms.permissions.owner = owner

        if group:
            perms.permissions.group = group

        obj.set_id_perms(perms)
        self.logger.info('New perms %s = %s' %
                         (obj.get_fq_name(), self.print_perms(perms)))
    # end set_perms
