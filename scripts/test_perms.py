from keystoneclient.v2_0 import client as ksclient
from vnc_api.vnc_api import *
from vnc_api import common
import uuid
import argparse

import os
import unittest
import fixtures
import testtools
import uuid

from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from keystone_tests import *
from tcutils.wrappers import preposttest_wrapper


class TestPerms(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(TestPerms, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        auth_url = os.getenv('OS_AUTH_URL') or \
                     'http://' + self.inputs.openstack_ip + ':5000/v2.0'
        insecure = bool(os.getenv('OS_INSECURE',True))
        self.key_stone_clients = KeystoneCommands(
            username=self.inputs.stack_user, password=self.inputs.stack_password, tenant=self.inputs.project_name, auth_url=auth_url,
            insecure=insecure)

    # end setUpClass

    def cleanUp(self):
        super(TestSanityFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

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
        admin_tenant = [x for x in tenants if x.name == 'admin'][0]

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
               perms.permissions.owner_access, perms.permissions.group_access, perms.permissions.other_access)
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

    @preposttest_wrapper
    def test_all(
        self, ip='127.0.0.1', port=8082, domain_name='default-domain',
            proj_name='my-proj', subnet='192.168.1.0', prefix=24, vn_name='my-vn'):
        '''
          1.Create 2 users - alice ,bob as staff role
          2.Create a poject - myProj
          3 .Disable write on myProj and try to create a ipam on the project as user alice/bob - should fail ; else test fails
          4.Chage the permission on myProj to 777.Try to create ipam on myProj as bob/alice - should be successful; else test fails
          5.Disable read on myProj and try to read a ipam on the project as user alice/bob - should fail ; else test fails
          6.Disable write on myProj and try to delete a ipam on the project as user alice/bob - should fail ; else test fails
          7.Disable execute on a IPAM and try to link that ipam to a vn as user alice/bob - should fail ; else test fails
          8.On Ipam Set IPAM perms such that only owner has read/write permissions;try to read as other user;should fail;else test fails
          9.Set IPAM perms such that only owner has write permissions;try to update ipam with other user;should fail;else test fails
          10.Set IPAM perms such that owner/group has read/write permissions.try to update/read ipam with other user;should pass;else test fails
         Maintainer: sandipd@juniper.net
        '''
        result = True
        testfail = 0
        testpass = 0
        ip = self.inputs.cfgm_ip

        # create test users and role
        self.keystone_create_users(
            [('alice', 'alice123', 'staff'), ('bob', 'bob123', 'staff')])

        # user=admin, role=admin
        vnc_lib = VncApi(
            username=self.inputs.stack_user, password=self.inputs.stack_password, tenant_name=self.inputs.project_name,
            api_server_host=ip, api_server_port=port)

        # user=bob, role=staff
        vnc_lib_bob = VncApi(
            username='bob', password='bob123', tenant_name=self.inputs.project_name,
            api_server_host=ip, api_server_port=port)

        # user=alice, role=staff
        vnc_lib_alice = VncApi(
            username='alice', password='alice123', tenant_name=self.inputs.project_name,
            api_server_host=ip, api_server_port=port)

#        create domain- commenting out since multiple domain not supported
#        domain = Domain(domain_name)
#        domain_uuid= vnc_lib.domain_create(domain)
#        self.addCleanup( vnc_lib.domain_delete, id= domain_uuid )
#        self.logger.info( 'Created domain %s' %(str(domain)) )
#        create project
        self.logger.info("Creating project..")
        self.key_stone_clients.create_tenant_list([proj_name])
        proj_dct = self.key_stone_clients.get_tenant_dct(proj_name)
        self.logger.info("Created tenant %s" % (proj_dct))
        project_uuid = proj_dct.id
        project_uuid_vnc_api_format = uuid.UUID(project_uuid)
        project_uuid_vnc_api_format = project_uuid_vnc_api_format.get_urn().split(
            ':')[-1:][0]
#       Adding sleep, Api server need 4 sec to sync if add/delete tenant
        import time
        time.sleep(4)
        self.addCleanup(self.key_stone_clients.delete_tenant_list, [proj_name])
        project = self.vnc_lib.project_read(id=project_uuid_vnc_api_format)
        project_fq_name = project.get_fq_name()
        self.logger.info('Created Project  %s ' %
                         (str(project.get_fq_name())))

        # Commenting out since project creation using the api server api not supported
#        project=Project(proj_name, domain)
#        project_uuid= vnc_lib.project_create(project)
#        self.addCleanup( vnc_lib.project_delete, id = project_uuid )
#        project = vnc_lib.project_read(project.get_fq_name())

#        self.logger.info( 'Created Project  %s ' %( str(project.get_fq_name())) )

        # create IPAM
        ipam = NetworkIpam('default-network-ipam', project, IpamType("dhcp"))
        network_ipam_id = vnc_lib.network_ipam_create(ipam)
        self.addCleanup(vnc_lib.network_ipam_delete, id=network_ipam_id)
        self.logger.info('Created network ipam')

        ipam = vnc_lib.network_ipam_read(
            fq_name=[domain_name, proj_name, 'default-network-ipam'])
        self.logger.info('Read network ipam')
        ipam_sn_1 = IpamSubnetType(subnet=SubnetType(subnet, prefix))

        self.logger.info('')
        self.logger.info(
            '############################### CREATE ################################')
        self.logger.info('Disable write in domain/project for others')
        self.set_perms(project, mode='0775')
        vnc_lib.project_update(project)

        self.logger.info(
            'Trying to create network-ipam in project as bob/staff ... should fail')
        try:
            ipam2 = NetworkIpam('default-network-ipam-2',
                                project, IpamType("dhcp"))
            network_ipam_bob_id = vnc_lib_bob.network_ipam_create(ipam2)
            self.logger.error(
                "Succeeded in creating network IPAM which should have failed ")
            testfail += 1
        except PermissionDenied as e:
            self.logger.info('Failed to create network IPAM ... Test passed!')
            testpass += 1

        self.logger.info(
            'Resetting permissions to allow bob/staff to create network IPAM')
        self.set_perms(project, mode='0777')
        vnc_lib.project_update(project)

        self.logger.info(
            'Trying to create network IPAM in project as bob/staff ... should go through')
        try:
            ipam2 = NetworkIpam('default-network-ipam-2',
                                project, IpamType("dhcp"))
            ipam2_id = vnc_lib_bob.network_ipam_create(ipam2)
            self.logger.info(
                'Success in creating network IPAM ... Test passed!')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(" Failed to create a network IPAM as bob/staff ")
            testfail += 1

        ipam2_obj = vnc_lib.network_ipam_read(id=ipam2_id)
        self.set_perms(ipam2_obj, mode='0774',
                       owner='admin', group='foobar')
        vnc_lib.network_ipam_update(ipam2_obj)

        self.logger.info('')
        self.logger.info(
            '############################# READ #######################################')
        self.logger.info(
            'Reading IPAM as bob/staff ... should go through because of other permissions')
        obj = vnc_lib_bob.network_ipam_read(id=ipam2_id)
        self.logger.info('IPAM name=%s, uuid=%s' %
                         (obj.get_fq_name(), obj.uuid))

        self.logger.info(
            'Resetting ownership and permission to disallow others to read IPAM')
        self.set_perms(ipam2_obj, mode='0770',
                       owner='admin', group='foobar')
        vnc_lib.network_ipam_update(ipam2_obj)

        self.logger.info('Reading IPAM as bob/staff ... should fail')
        try:
            obj = vnc_lib_bob.network_ipam_read(id=ipam2_id)
            self.logger.error(
                " Succeeded in reading IPAM which should have failed ")
            testfail += 1
        except PermissionDenied as e:
            self.logger.info('Failed to read IPAM ... Test passed!')
            testpass += 1

        self.logger.info('')
        self.logger.info(
            '############################# DELETE #####################################')
        self.logger.info(
            'Resetting project ownership and permission to disallow delete')
        project = vnc_lib.project_read(project.get_fq_name())
        self.set_perms(project, mode='0775')
        vnc_lib.project_update(project)
        self.logger.info(
            'Trying to delete VN in project as bob/staff ... should fail')
        try:
            vnc_lib_bob.network_ipam_delete(id=ipam2_id)
            self.logger.error(
                " Succeeded in deleting IPAM which should not have been permitted")
            testfail += 1
        except PermissionDenied as e:
            self.logger.info('Failed to delete IPAM ... Test passed!')
            testpass += 1

        self.logger.info(
            'Resetting project ownership and permission to allow delete')
        project = vnc_lib.project_read(project.get_fq_name())
        self.set_perms(project, mode='0777')
        vnc_lib.project_update(project)
        self.logger.info(
            'Trying to delete IPAM in project as bob/staff ... should succeed')
        try:
            vnc_lib_bob.network_ipam_delete(id=ipam2_id)
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                "Failed to delete the IPAM which should have succeeded ")
            testfail += 1

        self.logger.info('Trying to read IPAM as admin ... should fail')
        try:
            obj = vnc_lib.network_ipam_read(id=ipam2_id)
            self.logger.error(
                "Reading a IPAM succeded, which should have failed ")
            testfail += 1
        except HttpError as e:
            self.logger.info('Failed to read IPAM ... Test passed!')
            testpass += 1
        except NoIdError:
            self.logger.info('Failed to read IPAM ... Test passed!')
            testpass += 1

        self.logger.info('')
        self.logger.info(
            '############################### LINK ######################################')
        self.logger.info('Create VN')
        vn = VirtualNetwork(vn_name, project)
        vn_id = vnc_lib.virtual_network_create(vn)
        self.addCleanup(vnc_lib.virtual_network_delete, id=vn_id)
        net_obj = vnc_lib.virtual_network_read(fq_name=vn.get_fq_name())
        self.logger.info('VN name=%s, uuid=%s' %
                         (net_obj.get_fq_name(), net_obj.uuid))
        self.logger.info('Disallow network IPAM from linking by others')
        ipam = vnc_lib.network_ipam_read(
            fq_name=[domain_name, proj_name, 'default-network-ipam'])
        self.set_perms(ipam, mode='776')
        vnc_lib.network_ipam_update(ipam)
        net_obj.set_network_ipam(ipam, VnSubnetsType([ipam_sn_1]))
        try:
            vnc_lib_bob.virtual_network_update(net_obj)
            self.logger.info(
                "Succeeded in linking IPAM which should have failed! ")
            testfail += 1
        except PermissionDenied as e:
            self.logger.info('Failed to link IPAM ... Test passed!')
            testpass += 1

        self.logger.info('Allow network IPAM from linking by others')
        self.set_perms(ipam, mode='777')
        vnc_lib.network_ipam_update(ipam)
        net_obj = vnc_lib.virtual_network_read(fq_name=vn.get_fq_name())
        net_obj.set_network_ipam(ipam, VnSubnetsType([ipam_sn_1]))
        try:
            vnc_lib_bob.virtual_network_update(net_obj)
            self.logger.info('Succeeded in linking IPAM ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                "Failed to link IPAM which should have succeeded ")
            testfail += 1

        self.logger.info('')
        self.logger.info(
            '########################### READ OWNER ##############################')
        self.logger.info(
            'Set IPAM perms such that only owner has read/write permissions')
        self.set_perms(ipam, mode='0700', owner='bob')
        vnc_lib.network_ipam_update(ipam)
        self.logger.info('Trying to read IPAM as Alice')
        try:
            obj = vnc_lib_alice.network_ipam_read(id=ipam.uuid)
            self.logger.error(
                'Read IPAM successfully which should have failed ')
            testfail += 1
        except PermissionDenied as e:
            self.logger.info(' -> Failed to read IPAM ... Test passed!')
            testpass += 1

        self.logger.info('Trying to read VN as bob')
        try:
            obj = vnc_lib_bob.network_ipam_read(id=ipam.uuid)
            self.logger.info(' -> name=%s, perms=%s' %
                             (obj.get_fq_name(), self.print_perms(obj.get_id_perms())))
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                "Failed to read a IPAM as bob which should have passed")
            testfail += 1

        self.logger.info('')
        self.logger.info(
            '########################### UPDATE OWNER ##############################')
        self.logger.info(
            'Set IPAM perms such that only owner has write permissions')
        obj = vnc_lib.network_ipam_read(id=ipam.uuid)
        self.set_perms(obj, mode='0700', owner='bob', group='staff')
        vnc_lib.network_ipam_update(obj)

        try:
            vnc_lib_alice.network_ipam_update(obj)
            self.logger.error(
                ' Was able to update the IPAM as Alice which should have failed ')
            testfail += 1
        except PermissionDenied as e:
            self.logger.info(
                ' unable to update IPAM as Alice. Test successful !')
            testpass += 1

        self.logger.info('')
        self.logger.info(
            '########################### UPDATE GROUP ##############################')
        self.logger.info(
            'Set IPAM perms such that owner/group has read/write permissions')
        obj = vnc_lib.network_ipam_read(id=ipam.uuid)
        self.set_perms(obj, mode='0770', owner='bob', group='staff')
        vnc_lib.network_ipam_update(obj)

        try:
            vnc_lib_alice.network_ipam_update(obj)
            self.logger.info(
                ' Was able to update the IPAM as Alice successfully')
            testpass += 1
        except PermissionDenied as e:
            testfail += 1
            self.logger.error(' unable to update IPAM as Alice. Test failed !')

        self.logger.info('')
        self.logger.info(
            '########################### READ GROUP ##############################')
        self.logger.info(
            'Trying to read IPAM as Alice .. should go through now')
        try:
            obj = vnc_lib_alice.network_ipam_read(id=ipam.uuid)
            self.logger.info(' -> name=%s, perms=%s' %
                             (obj.get_fq_name(), self.print_perms(obj.get_id_perms())))
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to read IPAM as alice which should have gone through')
            testfail += 1

        self.logger.info('')
        self.logger.info('Tests fail=%d, pass=%d' % (testfail, testpass))
        assert testfail == 0, " One or more failures in Perms test... Passed : %s, Failed : %s" % (
            testpass, testfail)
        return True
   # end test_all

    @preposttest_wrapper
    def test_permissions_on_projects(self):

        proj_name = 'projF'
        domain_name = 'default-domain'
        ip = self.inputs.cfgm_ip
        port = '8082'
        result = True
        testpass = 0
        testfail = 0
        self.logger.info("Creating project..")
        self.key_stone_clients.create_tenant_list([proj_name])
        proj_dct = self.key_stone_clients.get_tenant_dct(proj_name)
        self.logger.info("Created tenant %s" % (proj_dct))
        project_uuid = proj_dct.id
        project_uuid_vnc_api_format = uuid.UUID(project_uuid)
        project_uuid_vnc_api_format = project_uuid_vnc_api_format.get_urn().split(
            ':')[-1:][0]
#       Adding sleep, Api server need 4 sec to sync if add/delete tenant
        import time
        time.sleep(4)
        self.addCleanup(self.key_stone_clients.delete_tenant_list, [proj_name])
        project = self.vnc_lib.project_read(id=project_uuid_vnc_api_format)
        project_fq_name = project.get_fq_name()

#        self.logger.info(  'Disable write in domain/project for others')
#        self.set_perms(project, mode = '0775')
#        self.vnc_lib.project_update(project)
#        self.logger.info(  'enable write in domain/project for others')
#        self.set_perms(project, mode = '0777')
#        self.vnc_lib.project_update(project)
#        self.key_stone_clients.add_user_to_tenant(proj_name,'admin' , 'admin')
        # Create user test/test123 and add as admin in projectF
        self.logger.info("Creating user test/test123 in projF as Admin")
        user = 'test'
        password = 'test123'
        email = 'email@example.com'
        try:
            self.key_stone_clients.create_user(
                user, password, email=email, tenant_name=self.inputs.project_name, enabled=True)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(proj_name, user, 'admin')
            self.addCleanup(self.key_stone_clients.delete_user, user)
            # user=test, role=admin
#            vnc_lib_test = VncApi(username='test', password='test123', tenant_name= self.inputs.project_name,
#                            api_server_host = ip, api_server_port = port)
            vnc_lib_test = VncApi(
                username='test', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed for exception %s..." % (e))

        # Create user test1/test123 and add as member in projectF
        try:
            self.logger.info("Creating user test1/test123 in projF as Member")
            user1 = 'test1'
            password1 = 'test123'
            email1 = 'email@example.com'
            self.key_stone_clients.create_user(
                user1, password1, email=email1, tenant_name=self.inputs.project_name, enabled=True)
            self.addCleanup(self.key_stone_clients.delete_user, user1)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(
                proj_name, user1, 'Member')
            # user=test, role=admin
            vnc_lib_test1 = VncApi(
                username='test1', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed as exception %s" % (e))
#
        # create NetworkPolicy
        self.logger.info(
            "Verifying that user %s/%s can create policy in project %s" %
            (user, password, proj_name))
        try:
            for i in range(1, 4):
                policy_name = 'test_policy%s' % i
                policy = NetworkPolicy(policy_name, project)
                policy_id = vnc_lib_test.network_policy_create(policy)
                self.addCleanup(
                    vnc_lib_test.network_policy_delete, id=policy_id)
                self.logger.info('Created network policy %s' %
                                 (str(policy.get_fq_name())))
                testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create policy which should have gone through')
            testfail += 1

        self.logger.info(
            "Verifying that user %s/%s can create policy in project %s as role Member" %
            (user1, password1, proj_name))
        try:
            for i in range(1, 4):
                policy_name = 'test1_policy%s' % i
                policy = NetworkPolicy(policy_name, project)
                policy_id = vnc_lib_test1.network_policy_create(policy)
                self.addCleanup(
                    vnc_lib_test1.network_policy_delete, id=policy_id)
                self.logger.info('Created network policy %s' %
                                 (str(policy.get_fq_name())))
                testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create policy which should have gone through')
            testfail += 1

        self.logger.info("Creating vn in %s as user %s" % (proj_name, user))
        try:
            test_proj_inputs1 = self.useFixture(
                ContrailTestInit(
                    self.ini_file, stack_user=user, stack_password=password,
                    project_fq_name=project_fq_name))
            test_proj_connections1 = ContrailConnections(test_proj_inputs1)
            vn1_fixture = self.useFixture(
                VNFixture(
                    project_name=proj_name, connections=test_proj_connections1,
                    vn_name='vn_1', inputs=test_proj_inputs1, subnets=['192.168.1.0/24']))
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create vn which should have gone through')
            testfail += 1

        self.logger.info("Creating vn in %s as user %s" % (proj_name, user1))
        try:
            test1_proj_inputs1 = self.useFixture(
                ContrailTestInit(
                    self.ini_file, stack_user=user1, stack_password=password1,
                    project_fq_name=project_fq_name))
            test1_proj_connections1 = ContrailConnections(test1_proj_inputs1)
            vn2_fixture = self.useFixture(
                VNFixture(
                    project_name=proj_name, connections=test1_proj_connections1,
                    vn_name='vn_2', inputs=test1_proj_inputs1, subnets=['192.168.2.0/24']))
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create vn which should have gone through')
            testfail += 1

        self.logger.info("Creating vm in %s as user %s" % (proj_name, user))
        try:
            vm1_fixture = VMFixture(connections=test_proj_connections1,
                                    vn_obj=vn1_fixture.obj, vm_name='vm_1', project_name=proj_name)
            vm1_fixture.setUp()
            testpass += 1
            vm1_fixture.cleanUp()
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create vm which should have gone through')
            testfail += 1

        self.logger.info("Creating vm in %s as user %s" % (proj_name, user1))
        try:
            vm2_fixture = VMFixture(connections=test1_proj_connections1,
                                    vn_obj=vn2_fixture.obj, vm_name='vm_2', project_name=proj_name, node_name='disable')
            vm2_fixture.setUp()
            testpass += 1
            vm2_fixture.cleanUp()
        except PermissionDenied as e:
            self.logger.error(
                ' *** Failed to create vm which should have gone through')
            testfail += 1

        try:
            self.logger.info('Disable write in domain/project for others')
            self.set_perms(project, mode='0775')
            self.vnc_lib.project_update(project)

            self.logger.info(
                "Verifying that Admin can still create policy,vn and vm....")
            # create NetworkPolicy
            self.logger.info(
                "Verifying that user %s/%s can create policy in project %s" %
                (user, password, proj_name))
            try:
                policy_name = 'test_policy11'
                policy = NetworkPolicy(policy_name, project)
                policy_id = vnc_lib_test.network_policy_create(policy)
                self.addCleanup(
                    vnc_lib_test.network_policy_delete, id=policy_id)
                self.logger.info('Created network policy %s' %
                                 (str(policy.get_fq_name())))
                testpass += 1
            except PermissionDenied as e:
                self.logger.error(
                    ' *** Failed to create policy which should have gone through')
                testfail += 1
            self.logger.info("Creating vn in %s as user %s" %
                             (proj_name, user))
            try:
                vn11_fixture = self.useFixture(
                    VNFixture(
                        project_name=proj_name, connections=test_proj_connections1,
                        vn_name='vn_11', inputs=test_proj_inputs1, subnets=['192.168.11.0/24']))
                testpass += 1
            except PermissionDenied as e:
                self.logger.error(
                    ' *** Failed to create vn which should have gone through')
                testfail += 1
            self.logger.info("Creating vm in %s as user %s" %
                             (proj_name, user))
            try:
                vm11_fixture = VMFixture(connections=test_proj_connections1,
                                         vn_obj=vn11_fixture.obj, vm_name='vm_11', project_name=proj_name)
                vm11_fixture.setUp()
                testpass += 1
                vm11_fixture.cleanUp()
            except PermissionDenied as e:
                self.logger.error(
                    ' *** Failed to create vm which should have gone through')
                testfail += 1

            self.logger.info(
                "Verifying that %s/%s cannot create policy,vn and vm...." %
                (user1, password1))

            self.logger.info(
                "Trying that user %s/%s to create policy in project %s as role Member" %
                (user1, password1, proj_name))
            try:
                policy_name = 'test1_policy_deny'
                policy = NetworkPolicy(policy_name, project)
                policy_id = vnc_lib_test1.network_policy_create(policy)
                self.addCleanup(
                    vnc_lib_test1.network_policy_delete, id=policy_id)
                self.logger.info('Created network policy %s' %
                                 (str(policy.get_fq_name())))
                testfail += 1
                self.logger.error(
                    ' *** policy creation passed...should have failed')
            except PermissionDenied as e:
                self.logger.info(' Failed to create policy ...')
                testpass += 1

            self.logger.info(
                "Trying that user %s/%s to delete policy in project %s as role Member" %
                (user1, password1, proj_name))
            try:
#                policy_name = 'test1_policy_deny'
#                policy = NetworkPolicy(policy_name, project)
                vnc_lib_test1.network_policy_delete(id=policy_id)
#                self.addCleanup( vnc_lib_test1.network_policy_delete, id = policy_id )
                self.logger.info('Deleted network policy %s' %
                                 (str(policy_id)))
                testfail += 1
                self.logger.error(
                    ' *** policy deletion passed...should have failed')
            except PermissionDenied as e:
                self.logger.info(' Failed to delete policy ...')
                testpass += 1

            self.logger.info("Trying to Create vn in %s as user %s" %
                             (proj_name, user1))
            try:
                vn_name = 'vn_denied'
                vn = VirtualNetwork(vn_name, project)
                vn_id = vnc_lib_test1.virtual_network_create(vn)
#            test1_proj_inputs1=self.useFixture(ContrailTestInit( self.ini_file, stack_user=user1, stack_password=password1,
#                                project_fq_name=project_fq_name))
#            test1_proj_connections1= ContrailConnections(test1_proj_inputs1)
#                vn22_fixture= self.useFixture(VNFixture(project_name= proj_name, connections= test1_proj_connections1,
#                     vn_name='vn_22', inputs= test1_proj_inputs1, subnets= ['192.168.22.0/24']))
#                testfail+= 1
#                self.logger.error( ' *** vn creation passed...should have failed')

            except PermissionDenied as e:
                self.logger.info('  Failed to create vn ')
                testpass += 1

            self.logger.info("Trying to create vm in %s as user %s" %
                             (proj_name, user1))
            try:
                vm22_obj = VMFixture(connections=test1_proj_connections1,
                                     vn_obj=vn11_fixture.obj, vm_name='vm_22', project_name=proj_name, node_name='disable')
                vm22_obj.setUp()
                testfail += 1
                self.logger.error(
                    ' *** vm creation passed...should have failed')
                vm22_obj.cleanUp()
            except PermissionDenied as e:
                self.logger.info('  Failed to create vm..')
                testpass += 1
        except Exception as e:
            self.logger.warn("Exception as %s" % (e))
            testfail += 1
        finally:
            self.logger.info('enable write in domain/project for others')
            self.set_perms(project, mode='0777')
            self.vnc_lib.project_update(project)

        self.logger.info('')
        self.logger.info('Tests fail=%d, pass=%d' % (testfail, testpass))
        assert testfail == 0, " One or more failures in Perms test... Passed : %s, Failed : %s" % (
            testpass, testfail)

        return True

    @preposttest_wrapper
    def test_permissions_on_policy_objects(self):

        proj_name = 'projF'
        domain_name = 'default-domain'
        ip = self.inputs.cfgm_ip
        port = '8082'
        result = True
        testpass = 0
        testfail = 0
        self.logger.info("Creating project..")
        self.key_stone_clients.create_tenant_list([proj_name])
        proj_dct = self.key_stone_clients.get_tenant_dct(proj_name)
        self.logger.info("Created tenant %s" % (proj_dct))
        project_uuid = proj_dct.id
        project_uuid_vnc_api_format = uuid.UUID(project_uuid)
        project_uuid_vnc_api_format = project_uuid_vnc_api_format.get_urn().split(
            ':')[-1:][0]
#       Adding sleep, Api server need 4 sec to sync if add/delete tenant
        import time
        time.sleep(4)
        self.addCleanup(self.key_stone_clients.delete_tenant_list, [proj_name])
        project = self.vnc_lib.project_read(id=project_uuid_vnc_api_format)
        project_fq_name = project.get_fq_name()
        self.logger.info("Creating user test/test123 in projF as Admin")
        user = 'test'
        password = 'test123'
        email = 'email@example.com'
        try:
            self.key_stone_clients.create_user(
                user, password, email=email, tenant_name=self.inputs.project_name, enabled=True)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(proj_name, user, 'admin')
            self.addCleanup(self.key_stone_clients.delete_user, user)
            # user=test, role=admin
#            vnc_lib_test = VncApi(username='test', password='test123', tenant_name= self.inputs.project_name,
#                            api_server_host = ip, api_server_port = port)
            vnc_lib_test = VncApi(
                username='test', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed for exception %s..." % (e))

        # Create user test1/test123 and add as member in projectF
        try:
            self.logger.info("Creating user test1/test123 in projF as Member")
            user1 = 'test1'
            password1 = 'test123'
            email1 = 'email@example.com'
            self.key_stone_clients.create_user(
                user1, password1, email=email1, tenant_name=self.inputs.project_name, enabled=True)
            self.addCleanup(self.key_stone_clients.delete_user, user1)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(
                proj_name, user1, 'Member')
            # user=test, role=admin
            vnc_lib_test1 = VncApi(
                username='test1', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed as exception %s" % (e))

        self.logger.info(
            "Verifying that user %s/%s can create policy in project %s" %
            (user, password, proj_name))
        policy_id = {}
        policy = {}
        try:
            for i in range(1, 4):
                policy_name = 'test_policy%s' % i
                policy[policy_name] = NetworkPolicy(policy_name, project)
                policy_id[policy_name] = vnc_lib_test.network_policy_create(
                    policy[policy_name])
                self.addCleanup(vnc_lib_test.network_policy_delete,
                                id=policy_id[policy_name])
                self.logger.info('Created network policy %s' %
                                 (str(policy[policy_name].get_fq_name())))
                policy[policy_name] = vnc_lib_test.network_policy_read(
                    id=policy_id[policy_name])
        except Exception as e:
            self.logger.error(
                ' *** Failed to create policy which should have gone through')

        self.logger.info("Test policy linking with vn...")
        self.logger.info("Creating vn in %s as user %s" % (proj_name, user))
        try:
            test_proj_inputs1 = self.useFixture(
                ContrailTestInit(
                    self.ini_file, stack_user=user, stack_password=password,
                    project_fq_name=project_fq_name))
            test_proj_connections1 = ContrailConnections(test_proj_inputs1)

            vn_obj = self.useFixture(
                VNFixture(
                    project_name=proj_name, connections=test_proj_connections1,
                    vn_name='vn211', option='api', inputs=test_proj_inputs1, subnets=['200.100.100.0/24', '200.100.101.0/24']))
        except Exception as e:
            self.logger.exception('Got exception as %s' % (e))
            testfail += 1
        self.logger.info("Tryig to attach policy %s to vn %s as user %s" %
                         (policy['test_policy1'].get_fq_name_str(), vn_obj.api_vn_obj.get_fq_name_str(), user1))

        net_obj = vnc_lib_test1.virtual_network_read(
            fq_name=vn_obj.api_vn_obj.get_fq_name())
        net_obj.add_network_policy(policy['test_policy1'], VirtualNetworkPolicyType(
            sequence=SequenceType(major=0, minor=0)))

        try:
            vnc_lib_test1.virtual_network_update(net_obj)
            self.logger.info('Succeeded in linking Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                "Failed to link Policy which should have succeeded ")
            testfail += 1
        finally:
            net_obj.del_network_policy(policy['test_policy1'])
            vnc_lib_test.virtual_network_update(net_obj)

        self.logger.info('Disallow network policy from linking by others')
        self.set_perms(policy['test_policy1'], mode='776')
        vnc_lib_test.network_policy_update(policy['test_policy1'])
        net_obj = vnc_lib_test.virtual_network_read(
            fq_name=vn_obj.api_vn_obj.get_fq_name())
        net_obj.set_network_policy(policy['test_policy1'], VirtualNetworkPolicyType(
            sequence=SequenceType(major=0, minor=0)))
        try:
            self.logger.info("Tryig to attach policy %s to vn %s as user %s" %
                             (policy['test_policy1'].get_fq_name_str(), vn_obj.api_vn_obj.get_fq_name_str(), user1))
            vnc_lib_test1.virtual_network_update(net_obj)
            self.logger.error(
                'Succeeded in linking Policy - should have failed... Test failed !')
            testfail += 1
        except PermissionDenied as e:
            self.logger.info("Failed to link Policy  ")
            net_obj.del_network_policy(policy['test_policy1'])
            testpass += 1

        self.logger.info("Tryig to attach policy %s to vn %s as user %s" %
                         (policy['test_policy2'].get_fq_name_str(), vn_obj.api_vn_obj.get_fq_name_str(), user1))
        net_obj.add_network_policy(policy['test_policy2'], VirtualNetworkPolicyType(
            sequence=SequenceType(major=0, minor=0)))
        try:
            vnc_lib_test1.virtual_network_update(net_obj)
            self.logger.info('Succeeded in linking Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error(
                "Failed to link Policy which should have succeeded ")
            testfail += 1
        finally:
            net_obj.del_network_policy(policy['test_policy2'])
            vnc_lib_test.virtual_network_update(net_obj)

        self.logger.info("Tryig to read policy %s  as user %s" %
                         (policy['test_policy1'].get_fq_name_str(), user1))
        try:
            obj = vnc_lib_test1.network_policy_read(
                id=policy_id['test_policy1'])
            self.logger.info('Succeeded in reading Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error("Failed to read policy...should have succeeded ")
            testfail += 1

        self.logger.info("Tryig to read policy %s  as user %s" %
                         (policy['test_policy2'].get_fq_name_str(), user1))
        try:
            obj = vnc_lib_test1.network_policy_read(
                id=policy_id['test_policy2'])
            self.logger.info('Succeeded in reading Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error("Failed to read policy...should have succeeded ")
            testfail += 1

        self.logger.info('Disallow network policy from reading by others')
        self.set_perms(policy['test_policy3'], mode='773')
        vnc_lib_test.network_policy_update(policy['test_policy3'])

        self.logger.info("Tryig to read policy %s  as user %s" %
                         (policy['test_policy3'].get_fq_name_str(), user1))
        try:
            obj = vnc_lib_test1.network_policy_read(
                id=policy_id['test_policy3'])
            self.logger.info(
                'Succeeded in reading Policy ... should have failed !')
            testfail += 1
        except PermissionDenied as e:
            self.logger.info("Failed to read policy...test passed ")
            testpass += 1

        self.logger.info("Tryig to read policy %s  as user %s" %
                         (policy['test_policy3'].get_fq_name_str(), user))
        try:
            obj = vnc_lib_test.network_policy_read(
                id=policy_id['test_policy3'])
            self.logger.info('Succeeded in reading Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error("Failed to read policy...should have succeeded ")
            testfail += 1

        self.logger.info("Tryig to read policy %s  as user %s" %
                         (policy['test_policy2'].get_fq_name_str(), user1))
        try:
            obj = vnc_lib_test1.network_policy_read(
                id=policy_id['test_policy2'])
            self.logger.info('Succeeded in reading Policy ... Test passed !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.error("Failed to read policy...should have succeeded ")
            testfail += 1

        self.logger.info('')
        self.logger.info('Tests fail=%d, pass=%d' % (testfail, testpass))
        assert testfail == 0, " One or more failures in Perms test... Passed : %s, Failed : %s" % (
            testpass, testfail)

        return True
    # end test_permissions_on_policy_objects

    @preposttest_wrapper
    def test_permissions_on_vn_objects(self):

        proj_name = 'projF'
        domain_name = 'default-domain'
        ip = self.inputs.cfgm_ip
        port = '8082'
        result = True
        testpass = 0
        testfail = 0
        subnet = '192.168.1.0'
        prefix = 24
        self.logger.info("Creating project..")
        self.key_stone_clients.create_tenant_list([proj_name])
        proj_dct = self.key_stone_clients.get_tenant_dct(proj_name)
        self.logger.info("Created tenant %s" % (proj_dct))
        project_uuid = proj_dct.id
        project_uuid_vnc_api_format = uuid.UUID(project_uuid)
        project_uuid_vnc_api_format = project_uuid_vnc_api_format.get_urn().split(
            ':')[-1:][0]
#       Adding sleep, Api server need 4 sec to sync if add/delete tenant
        import time
        time.sleep(4)
        self.addCleanup(self.key_stone_clients.delete_tenant_list, [proj_name])
        project = self.vnc_lib.project_read(id=project_uuid_vnc_api_format)
        project_fq_name = project.get_fq_name()
        self.logger.info("Creating user test/test123 in projF as Admin")
        user = 'test'
        password = 'test123'
        email = 'email@example.com'
        try:
            self.key_stone_clients.create_user(
                user, password, email=email, tenant_name=self.inputs.project_name, enabled=True)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(proj_name, user, 'admin')
            self.addCleanup(self.key_stone_clients.delete_user, user)
            # user=test, role=admin
#            vnc_lib_test = VncApi(username='test', password='test123', tenant_name= self.inputs.project_name,
#                            api_server_host = ip, api_server_port = port)
            vnc_lib_test = VncApi(
                username='test', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed for exception %s..." % (e))

        # Create user test1/test123 and add as member in projectF
        try:
            self.logger.info("Creating user test1/test123 in projF as Member")
            user1 = 'test1'
            password1 = 'test123'
            email1 = 'email@example.com'
            self.key_stone_clients.create_user(
                user1, password1, email=email1, tenant_name=self.inputs.project_name, enabled=True)
            self.addCleanup(self.key_stone_clients.delete_user, user1)
            # Update projF with user test/test123 with member role
            self.key_stone_clients.add_user_to_tenant(
                proj_name, user1, 'Member')
            # user=test, role=admin
            vnc_lib_test1 = VncApi(
                username='test1', password='test123', tenant_name=proj_name,
                api_server_host=ip, api_server_port=port)
        except Exception as e:
            self.logger.warn("User creation failed as exception %s" % (e))

        self.logger.info("Creating vn in %s as user %s" % (proj_name, user))
        try:
            test_proj_inputs1 = self.useFixture(
                ContrailTestInit(
                    self.ini_file, stack_user=user, stack_password=password,
                    project_fq_name=project_fq_name))
            test_proj_connections1 = ContrailConnections(test_proj_inputs1)

            vn_obj = self.useFixture(
                VNFixture(
                    project_name=proj_name, connections=test_proj_connections1,
                    vn_name='vn211', option='api', inputs=test_proj_inputs1, subnets=['200.100.100.0/24', '200.100.101.0/24']))
        except Exception as e:
            self.logger.exception('Got exception as %s' % (e))
            testfail += 1
        vn_api_obj = vn_obj.get_api_obj()
        net_obj = vnc_lib_test1.virtual_network_read(
            fq_name=vn_api_obj.get_fq_name())

        self.logger.info(
            "Changing permissions on vn to disable read for others...")
        self.set_perms(net_obj, mode='0773')
        vnc_lib_test1.virtual_network_update(net_obj)
        try:
            self.logger.info("trying to read vn %s as user %s" %
                             (vn_api_obj.get_fq_name_str(), user1))
            obj = vnc_lib_test1.virtual_network_read(id=vn_obj.vn_id)
            self.logger.error(
                'Succeeded in reading vn ... should have failed !')
            testfail += 1
        except PermissionDenied as e:
            self.logger.info("Failed to read vn...test passed ")
            testpass += 1

        try:
            self.logger.info("trying to read vn %s as user %s" %
                             (vn_api_obj.get_fq_name_str(), user))
            obj = vnc_lib_test.virtual_network_read(id=vn_obj.vn_id)
            self.logger.info('Succeeded in reading vn ... !')
            testpass += 1
        except PermissionDenied as e:
            self.logger.info("Failed to read vn...test failed ")
            testfail += 1

#@        try:
#@            self.logger.info("Creating vm using %s as user %s"%(vn_api_obj.get_fq_name_str(),user))
#@            vm1_fixture= self.useFixture(VMFixture(connections= test_proj_connections1,
#@                            vn_obj=vn_obj.obj, vm_name= 'vm_1', project_name= proj_name,node_name ='disable'))
#@            self.logger.info( 'Succeeded in creating vm ... !')
#@            testpass+= 1
#@        except PermissionDenied as e:
#@            self.logger.error( ' *** Failed to create vm which should have gone through')
#@            testfail += 1
#@
#@        test1_proj_inputs1=self.useFixture(ContrailTestInit( self.ini_file, stack_user=user1, stack_password=password1,
#@                                project_fq_name=project_fq_name))
#@        test1_proj_connections1= ContrailConnections(test1_proj_inputs1)
#@
#@        try:
#@            self.logger.info("Creating vm using %s as user %s"%(vn_api_obj.get_fq_name_str(),user1))
#@            vm2_fixture= self.useFixture(VMFixture(connections= test1_proj_connections1,
#@                            vn_obj=vn_obj.obj, vm_name= 'vm_2', project_name= proj_name,node_name ='disable'))
#@            self.logger.info( 'Succeeded in creating vm ...Test passed !')
#@            testpass+= 1
#@        except PermissionDenied as e:
#@            self.logger.error( '  Failed to create vm .... Test failed')
#@            testfail += 1

        self.logger.info(
            "Changing permissions on vn to disable write for others...")
        self.set_perms(net_obj, mode='0775')
        vnc_lib_test1.virtual_network_update(net_obj)

        # create IPAM
        try:
            ipam = NetworkIpam('ipam1', project, IpamType("dhcp"))
            network_ipam_id = vnc_lib_test.network_ipam_create(ipam)
            self.addCleanup(vnc_lib_test.network_ipam_delete,
                            id=network_ipam_id)
            self.logger.info('Created network ipam')

            ipam = vnc_lib_test.network_ipam_read(fq_name=ipam.get_fq_name())
            self.logger.info('Read network ipam')
            ipam_sn_1 = IpamSubnetType(subnet=SubnetType(subnet, prefix))
            net_obj.add_network_ipam(ipam, VnSubnetsType([ipam_sn_1]))
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        try:
            vnc_lib_test1.virtual_network_update(net_obj)
            self.logger.info(
                "Succeeded in writing into vn.. which should have failed! ")
            testfail += 1
        except PermissionDenied as e:
            self.logger.info('Failed to write to vn ... Test passed!')
            testpass += 1
#        try:
#            self.logger.info("Creating vm using %s as user %s"%(vn_api_obj.get_fq_name_str(),user1))
#            vm2_fixture= self.useFixture(VMFixture(connections= test1_proj_connections1,
#                            vn_obj=vn_obj.obj, vm_name= 'vm_3', project_name= proj_name,node_name ='disable'))
#            self.logger.info( 'Succeeded in creating vm ...Test failed !')
#            testfail+= 1
#        except PermissionDenied as e:
#            self.logger.error( '  Failed to create vm .... Test passed')
#            testpassed += 1

        self.logger.info('')
        self.logger.info('Tests fail=%d, pass=%d' % (testfail, testpass))
        assert testfail == 0, " One or more failures in Perms test... Passed : %s, Failed : %s" % (
            testpass, testfail)

        return True

    # end test_permissions_on_vn_objects
# end Class TestPerms
