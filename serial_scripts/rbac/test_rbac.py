import test
from base import BaseRbac
from tcutils.util import get_random_name
from tcutils.config.vnc_introspect_utils import VNCApiInspect
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vm_test import VMFixture
from vn_test import VNFixture
from project_test import ProjectFixture
from user_test import UserFixture

import os
import unittest
import fixtures
import testtools
from common.servicechain.firewall.verify import VerifySvcFirewall

class TestRbac(BaseRbac):

    @classmethod
    def setUpClass(cls):
        super(TestRbac, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRbac, cls).tearDownClass()

    @preposttest_wrapper

    def test_create_tenant_user_and_acl_entry(self):
        '''
        steps:
           1. create a tenant and user as member
           2. create an acl entry with * and virtual-network with CRUD
           3. with the * object firstACL is created and updtaed the default-acl with the virtual-network
           4 ACL entried should be created for the tenant with the 'acl_role_obj'
        pass : acl creation and update should compelte scucessfully.
        '''

        project_name = get_random_name('rbac-proj')
        first_project = self.auth.create_project(project_name)
        self.logger.info('project uuid is' + first_project)
        self.orch._vnc.project_read(id=first_project)
        # create user
        usr_name = get_random_name('rbac_usr')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        self.logger.info('user name:' + usr_name)
        # add user to project as admin
        self.auth.add_user_to_project(usr_name, project_name, '_member_') 

        self.logger.info('creating acl entires for the project' + project_name)
        fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, 'default-api-access-list')
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['*', 'virtual-networks']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)
        # create acl
      #  acl_entry = self.orch.create_api_access_list(fq_name1, 'project', [role_dict1])
        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'project', [role_dict1])
        self.logger.info(acl_entry)
        if len(acl_role_obj) > 1:
            for role in acl_role_obj[1:]:
                role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
                self.logger.info(role_dict1)
            # update acl-list
                acl_updated = self.admin_connections.orch.vnc_h.update_api_access_list(acl_entry, [role_dict1])
        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('Acl verification in api PASSED')
        return True

    @preposttest_wrapper
    def test_delete_acl_entry(self):
        '''
        steps:
           1. create a tenant and user as member
           2. create an acl entry for virtual-network with CRUD
           3. Delete acl creted on 2nd step
        pass : acl deletion should compelte scucessfully.
        '''

        project_name = get_random_name('rbac-proj')
        first_project = self.auth.create_project(project_name)
        self.logger.info('project uuid is' + first_project)
        # read the project to sync with api
        self.orch._vnc.project_read(id=first_project)
        # create user
        usr_name = get_random_name('rbac_usr')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        self.logger.info('user name:' + usr_name)
        # add user to project as admin
        self.auth.add_user_to_project(usr_name, project_name, '_member_')

        self.logger.info('creating acl entires for the project' + project_name)
        fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, 'default-api-access-list-1')
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['virtual-network']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)
      #  acl_entry = self.orch.create_api_access_list(fq_name1, 'project', [role_dict1])
        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'project', [role_dict1])
        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('Acl is present in api server')
        self.logger.info('Acl going to delete from api server')
        acl_del = self.admin_connections.orch.vnc_h.delete_api_access_list(id=acl_entry)
        try:
            acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)

        except NoIdError:
            self.logger.info('Acl deleted from api server')
        return True

    @preposttest_wrapper
    def test_create_vn_vm_as_member_user(self):
        '''
        steps:
           1. create a tenant and user as member
           2. assign the role as CRUD
           3. create virtual-network  with proper vn acls
        pass : acl creation should scucess after adding objects needed for virtul-network creation to  acl
        '''
        project_name = get_random_name('rbac-proj')
        first_project = self.auth.create_project(project_name)
        self.logger.info('project uuid is' + first_project)
        # read the project to sync with api
        proj_obj = self.orch.vnc_lib.project_read(id=first_project)
        # create user
        usr_name = get_random_name('rbac_usr')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        self.logger.info('user name:' + usr_name)
        self.auth.add_user_to_project(usr_name, project_name, '_member_')

        self.logger.info('creating acl entires for the project' + project_name)
        fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, 'default-api-access-list-2')
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['*']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)
        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'project', [role_dict1])
       # acl_entry = self.orch.vnc_h.create_api_access_list(fq_name1, 'project', [role_dict1])
        self.logger.info(acl_entry)
        if len(acl_role_obj) > 1:
            for role in acl_role_obj[1:]:
                role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
                self.logger.info(role_dict1)
               # acl_entry_lists = self.orch.create_api_access_list(fq_name1, 'project', [role_dict1])
                acl_updated = self.admin_connections.orch.vnc_h.update_api_access_list(acl_entry, [role_dict1])

        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']

        if acl_uuid_from_api == acl_entry:
            self.logger.info('Acl is present in api server')

        vn1_name = get_random_name('vn-acl')
        vm1_name = get_random_name('vm1_vn-acl')
        vn1_subnets = ['22.1.1.0/24']

        project_fixture_obj = self.useFixture(ProjectFixture(
            username=usr_name,
            password=usr_name,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        assert project_fixture_obj.verify_on_setup()

        proj_connection = project_fixture_obj.get_project_connections(
                            username=usr_name, password=usr_name)
        proj_connection.inputs.use_admin_auth = True

        vn1_obj = VNFixture(project_name=project_name,
            connections=proj_connection,
            inputs=self.inputs,
            vn_name=vn1_name,
           # project_obj=proj_obj,
            subnets=vn1_subnets)
        vn1_obj.setUp()
        assert vn1_obj.verify_on_setup()
        vm1_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name,
                    connections=proj_connection,
                    vn_obj=vn1_obj.obj,
                    vm_name=vm1_name))
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        return True

    @preposttest_wrapper
    def test_modify_perm2_global_access_and_share(self):
        '''
        steps:
           1. create two  tenants and user as admin
           2. assign the role as CRUD
           3. change tenant perms2 global_access from 0 (default vlaue) to 5
           4. add tenant2 to the share list.
           5. verify the change of step 3 and 4 in introp.

        '''
        project_name = get_random_name('rbac-proj')
        project_name2 = get_random_name('rbac-proj-2')
        first_project = self.auth.create_project(project_name)
        first_project2 = self.auth.create_project(project_name2)
        self.logger.info('project uuid is: ' + first_project)
        self.logger.info('project2 uuid is: ' + first_project2)
        # read the project to sync with api
        proj_obj = self.orch._vnc.project_read(id=first_project)
        proj_obj2 = self.orch._vnc.project_read(id=first_project2)

        # create user
        usr_name = get_random_name('rbac_usr')
        usr_name2 = get_random_name('rbac_usr-2')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        usr_uuid2 = self.auth.create_user(usr_name2, usr_name2)
        self.logger.info('user name:' + usr_name)
        self.logger.info('user name:' + usr_name2)

        # add user to project as admin
        self.auth.add_user_to_project(usr_name, project_name, 'admin')
        self.auth.add_user_to_project(usr_name2, project_name2, 'admin')

        # create a VN and share with tenant2
        vn1_name = get_random_name('vn-acl')
        vn1_subnets = ['22.1.1.0/24']
        vm1_name = get_random_name('vm1_shared_vn_perms2')

        project_fixture_obj = self.useFixture(ProjectFixture(
            username=usr_name,
            password=usr_name,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        assert project_fixture_obj.verify_on_setup()

        proj_connection = project_fixture_obj.get_project_connections(
                            username=usr_name, password=usr_name)

        proj_connection.inputs.use_admin_auth = True

        vn1_fixture_obj = VNFixture(project_name=project_name,
            connections=proj_connection,
            inputs=self.inputs,
            vn_name=vn1_name,
           # project_obj=proj_obj,
            subnets=vn1_subnets)
        vn1_fixture_obj.setUp()
        assert vn1_fixture_obj.verify_on_setup()
        vn_id = vn1_fixture_obj.uuid
        vn1_obj = vn1_fixture_obj.api_vn_obj
        vn_global_access = 5
        vn_tenant_share_vlaue = 5
        self.logger.info('setting the global access vlaue to 5 for  vn with uuid : %s ' % vn_id)
        global_access_set = self.admin_connections.orch.vnc_h.set_global_access(vn_global_access, vn1_obj)
        set_share_tenant = self.admin_connections.orch.vnc_h.set_share_tenants(first_project2, vn_tenant_share_vlaue, vn1_obj)

        vn_read_introspect = self.verify_vn_perms2_in_api_introp(vn_id)
        vn_introp_global = vn_read_introspect['global_access']
        vn_introp_tenant_share = vn_read_introspect['share'][0]['tenant']

        if vn_introp_global == vn_global_access:
            self.logger.info(('vn %s share access value set properly in api server') % vn_id)
        # verify shared tenant in perms2:
        if vn_introp_tenant_share == first_project2:
            self.logger.info('vn %s shared with tenant %s is present in perms2 tenant shared list' % (vn_id, first_project2))
        else:
            self.logger.error(('shared vn info is missing from %s vn perms2 shared list') % vn_id )

        # create a vm using user2 on shared vn, tenant2
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=usr_name2,
            password=usr_name2,
            project_name=project_name2,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        assert project_fixture_obj.verify_on_setup()

        proj_connection2 = project_fixture_obj.get_project_connections(
                            username=usr_name2, password=usr_name2)

        proj_connection2.inputs.use_admin_auth = True

        vm1_fixture = self.useFixture(
                VMFixture(
                    project_name=project_name2,
                    connections=proj_connection2,
                    vn_obj=vn1_fixture_obj.obj,
                    vm_name=vm1_name))
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        return True

    @preposttest_wrapper

    def test_create_domain_and_global_acl_entry(self):
        '''
        steps:
           1. create a tenant and user as member
           2. create an domain acl entry with * and virtual-network with CRUD
           3. with the * objecti, first ACL is created and updtaed the default-acl with the virtual-network
           4 ACL entries should be created for the domain  with the 'acl_role_obj'
        pass : acl creation and update should compelte scucessfully.
        '''

        project_name = get_random_name('rbac-proj')
        first_project = self.auth.create_project(project_name)
        self.logger.info('project uuid is' + first_project)
        self.orch._vnc.project_read(id=first_project)
        # create user
        usr_name = get_random_name('rbac_usr')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        self.logger.info('user name:' + usr_name)
        # add user to project as admin
        self.auth.add_user_to_project(usr_name, project_name, 'admin')

        self.logger.info('creating acl entires for the project' + project_name)
       # fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, 'default-api-access-list')
        fq_name1 = self.domain_acl_fq_name(self.inputs.domain_name, 'default-api-access-list-3')
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['*']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)
        # create domain acl
        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'domain', [role_dict1])
        #acl_entry = self.orch.vnc_h.create_api_access_list(fq_name1, 'domain', [role_dict1])
        self.logger.info(acl_entry)
        if len(acl_role_obj) > 1:
            for role in acl_role_obj[1:]:
                role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
                self.logger.info(role_dict1)
            # update acl-list
                acl_updated = self.admin_connections.orch.vnc_h.update_api_access_list(acl_entry, [role_dict1])

        vn1_name = get_random_name('vn-acl')
        vm1_name = get_random_name('vm1_vn-acl')
        vn1_subnets = ['22.1.1.0/24']

        project_fixture_obj = self.useFixture(ProjectFixture(
            username=usr_name,
            password=usr_name,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        assert project_fixture_obj.verify_on_setup()


        proj_connection = project_fixture_obj.get_project_connections(
                            username=usr_name, password=usr_name)
        proj_connection.inputs.use_admin_auth = True

        vn1_obj = VNFixture(project_name=project_name,
            connections=proj_connection,
            inputs=self.inputs,
            vn_name=vn1_name,
           # project_obj=proj_obj,
            subnets=vn1_subnets)
        vn1_obj.setUp()
        assert vn1_obj.verify_on_setup()

        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('Domain Acl verification in api PASSED')
        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('domain-acl is present in api server')
        self.logger.info('domain-acl going to delete from api server')
        acl_del = self.admin_connections.orch.vnc_h.delete_api_access_list(id=acl_entry)
        try:
            acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)

        except NoIdError:
            self.logger.info('domain-acl is deleted from api server')

        fq_name1 = self.global_acl_fq_name()
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['*']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)

      # create global-rbac acl rule

# HERE IT FAILED 'NEED TO DEBUG THE CREATE GLOBAL ACL'

        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'default-global-system-config', [role_dict1])
        self.logger.info(acl_entry)
        if len(acl_role_obj) > 1:
            for role in acl_role_obj[1:]:
                role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
                self.logger.info(role_dict1)
            # update acl-list
                acl_updated = self.admin_connections.orch.vnc_h.update_api_access_list(acl_entry, [role_dict1])
        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('Global Acl verification in api PASSED')
        acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)
        acl_introp_dict = self.verify_acl_in_api_introp(acl_entry)
        acl_uuid_from_api = acl_introp_dict['api-access-list']['uuid']
        if acl_uuid_from_api == acl_entry:
            self.logger.info('Global-acl is present in api server')
        self.logger.info('Global-acl going to delete from api server')
        acl_del = self.admin_connections.orch.vnc_h.delete_api_access_list(id=acl_entry)
        try:
            acl_read = self.admin_connections.orch.vnc_h.get_api_access_list(id=acl_entry)

        except NoIdError:
            self.logger.info('Global-acl is deleted from api server')
        return True

class TestSvcRegrRbac(BaseRbac):

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_svc_in_network_datapath_rbac(self):
        '''
        Service chain: in-network fw v1 test case
        '''
        project_name = get_random_name('rbac-SI-proj')
        first_project = self.auth.create_project(project_name)
        self.logger.info('project uuid is' + first_project)
        self.orch._vnc.project_read(id=first_project)
        # create user
        usr_name = get_random_name('rbac_usr-SI')
        usr_uuid = self.auth.create_user(usr_name, usr_name)
        self.logger.info('user name:' + usr_name)
        # add user to project as admin
        self.auth.add_user_to_project(usr_name, project_name, '_member_')
        # service instance needed admin user in the project
        self.auth.add_user_to_project('admin', project_name, '_member_')
        self.logger.info('creating acl entires for the project' + project_name)
       # fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, 'default-api-access-list')
        access_list_name = get_random_name('default-api-access-list')
        self.logger.info('Access-list created for this test-case is: ' + access_list_name)
        fq_name1 = self.acl_fq_name(project_name, self.inputs.domain_name, access_list_name)
        self.logger.info(fq_name1)
        perm_dict = self.create_perm_dict('_member_', 'CRUD')
        self.logger.info(perm_dict)
        acl_role_obj = ['*']
        role = acl_role_obj[0]
        role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
        self.logger.info(role_dict1)
        # create domain acl
        acl_entry = self.admin_connections.orch.vnc_h.create_api_access_list(fq_name1, 'project', [role_dict1])
        self.logger.info(acl_entry)
        if len(acl_role_obj) > 1:
            for role in acl_role_obj[1:]:
                role_dict1 = self.create_role_dict(role, '_member_', 'CRUD', perm_dict)
                self.logger.info(role_dict1)
            # update acl-list
                acl_updated = self.orch.update_api_access_list(acl_entry, [role_dict1])

        """Validate the service chaining in network  datapath"""
        project_fixture_obj = self.useFixture(ProjectFixture(
            username=usr_name,
            password=usr_name,
            project_name=project_name,
            vnc_lib_h=self.vnc_lib,
            connections=self.connections))
        assert project_fixture_obj.verify_on_setup()

        proj_connection = project_fixture_obj.get_project_connections(
                            username=usr_name, password=usr_name)

        proj_connection.inputs.use_admin_auth = True

        svc_fw_obj = self.useFixture(VerifySvcFirewall(connections=proj_connection, use_vnc_api=True))
        svc_fw_obj.inputs = proj_connection.inputs
        svc_fw_obj.connections = proj_connection
        svc_fw_obj.verify_svc_in_network_datapath(svc_mode='in-network', ci=True)
        return True
