from __future__ import absolute_import
from .base import BaseDomainTest
from tcutils.wrappers import preposttest_wrapper
import test
from policy_test import *
from vm_test import *
from tcutils.util import skip_because
from tcutils.util import get_random_name
from domain_test import *


class TestDomain(BaseDomainTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDomain, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestDomain, cls).tearDownClass()

    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_crud_domain(self):
        ''' Test create read update and delete domain.
        '''
        domain_name = get_random_name('TestDomain-1')
        username = 'admin'
        password = 'contrail123'
        domain_fix = self.useFixture(
            DomainFixture(connections=self.admin_connections,
                          domain_name=domain_name,
                          username=username, password=password))
        domain_name_new = get_random_name('TestDomain-New')
        domain_update = domain_fix.update_domain(domain_name_new,
                                                 description='Changed the domain name as part of update.',
                                                 enabled=True)
        domain_found = domain_fix.get_domain()
        assert (domain_update and domain_found)
    # end test_crud_domain

    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_domain_sanity(self):
        ''' Sanity Test for domain isolation.
            One full circle of project, user, vm, vn creation 
            with ping traffic between the VM's is tested in a
            newly created domain.
        '''
        username = get_random_name('TestUser-1')
        password = get_random_name('TestUser-1')
        project_name = get_random_name('TestProject-1')
        domain_name = self.connections.domain_name
        project_fix = self.create_project(
            domain_name,project_name,username,password)
        self.admin_connections.auth.create_user(user=username, password=password,
            tenant_name=project_name, domain_name=domain_name)
        self.admin_connections.auth.add_user_to_domain(username,'admin',domain_name)
        self.admin_connections.auth.add_user_to_project(username,project_name,'admin')
        proj_conn = project_fix.get_project_connections()
        ret = self.setup_common_objects(
            connections=proj_conn, project_fix=project_fix)
        assert ret,'Failed to setup and test common objects'
    # end test_domain_sanity

    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_domain_user_group(self):
        ''' Test user group within a domain
            1) Create project
            2) Create user
            3) Create user_group and attach user to it
            4) Attach user_group to domain and project with admin roles
            5) Get project connections with user and create projects it should be allowed
            6)Verify user_group by creating vn and vms
        '''

        username = get_random_name('TestUser-1')
        password = get_random_name('TestUser-1')
        project_name = get_random_name('TestProject-1')
        domain_name = self.connections.domain_name
        user_group = get_random_name('TestGroup-1')
        project_fix = self.create_project(
            domain_name,project_name,username,password)
        self.admin_connections.auth.create_user(
            user=username, password=password,
            tenant_name=project_name, domain_name=domain_name)
        self.admin_connections.auth.create_user_group(
            group=user_group, domain_name=domain_name)
        self.admin_connections.auth.add_user_to_group(
            user=username, group=user_group)
        self.admin_connections.auth.add_group_to_domain(
            group=user_group,role='admin', domain=domain_name)
        self.admin_connections.auth.add_group_to_tenant(
            project=project_name, group=user_group,role='admin')
        proj_conn = project_fix.get_project_connections()
        ret = self.setup_common_objects(
            connections=proj_conn, project_fix=project_fix)
        assert ret,'Failed to setup and test common objects'
    # end test_domain_user_group
    
    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_domain_with_diff_user_groups(self):
        ''' Test user group within a domain
            1) Create project1 and project2
            2) Create user1 and user2 
            3) Create user_group1 and attach user1 to it 
            4) Create user_group2 and attach user2 to it
            5) Attach user_group1 to project1 with admin role and user_group2 as __member__ role to project2
            6) Try to create objects with user1 and user2 it should be allowed'''

        username1 = get_random_name('TestUser-1')
        password1 = get_random_name('TestUser-1')
        username2 = get_random_name('TestUser-2')
        password2 = get_random_name('TestUser-2')
        project_name1 = get_random_name('TestProject-1')
        project_name2 = get_random_name('TestProject-2')
        user_group1 = get_random_name('TestGroup-1')
        user_group2 = get_random_name('TestGroup-1')
        domain_name = self.connections.domain_name
        project_fix1 = self.create_project(
                                 domain_name,project_name1,username1,password1)
        project_fix2 = self.create_project(
                                 domain_name,project_name2,username2,password2)
        self.admin_connections.auth.create_user(
                                 user=username1, password=password1,
                                 tenant_name=project_name1, domain_name=domain_name)
        self.admin_connections.auth.create_user(
                                 user=username2, password=password2,
                                 tenant_name=project_name2, domain_name=domain_name)
        self.admin_connections.auth.create_user_group(
                                 group=user_group1, domain_name=domain_name)
        self.admin_connections.auth.create_user_group(
                                 group=user_group2, domain_name=domain_name)
        self.admin_connections.auth.add_user_to_group(
                                 user=username1, group=user_group1)
        self.admin_connections.auth.add_user_to_group(
                                 user=username2, group=user_group2)
        self.admin_connections.auth.add_group_to_domain(
                                 group=user_group1,role='admin', domain=domain_name)
        self.admin_connections.auth.add_group_to_domain(
                                 group=user_group2,role='admin', domain=domain_name)
        self.admin_connections.auth.add_group_to_tenant(
                                 project=project_name1, group=user_group1,role='admin')
        self.admin_connections.auth.add_group_to_tenant(
                                project=project_name2, group=user_group2,role='_member_')
        proj_conn = project_fix1.get_project_connections()
        ret1 = self.setup_common_objects(connections=proj_conn, project_fix=project_fix1)
        project_fix2.set_user_creds(username2, password2)
        proj_conn = project_fix2.get_project_connections()
        ret2 = self.setup_common_objects(connections=proj_conn, project_fix=project_fix2)
        assert (ret1 and ret2), 'Failed to setup and test common objects'
    # end test_domain_with_diff_user_groups

    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_perms_with_diff_user_in_diff_projects(self):
        ''' Test user roles across projects in the same domain
            1) Create user1 and user2
            2) Create project1 and project2
            3) Attach user1 to project1 with admin role and user2 as _member_ role to project2
            6) create VN1 under Project1
            7) user2 shouldnt be able to read VN1 using project2 creds'''

        username1 = get_random_name('TestUser-1')
        password1 = get_random_name('TestUser-1')
        username2 = get_random_name('TestUser-2')
        password2 = get_random_name('TestUser-2')
        project_name1 = get_random_name('TestProject-1')
        project_name2 = get_random_name('TestProject-2')
        domain_name = self.connections.domain_name
        project_fix1 = self.create_project(
                                 domain_name,project_name1,username1,password1)
        project_fix2 = self.create_project(
                                 domain_name,project_name2,username2,password2)
        self.admin_connections.auth.create_user(user=username1, password=password1,
                                 tenant_name=project_name1, domain_name=domain_name)
        self.admin_connections.auth.create_user(user=username2, password=password2,
                                 tenant_name=project_name2, domain_name=domain_name)
        self.admin_connections.auth.add_user_to_domain(username1,'admin',domain_name)
        self.admin_connections.auth.add_user_to_domain(username2,'admin',domain_name)
        self.admin_connections.auth.add_user_to_project(username1,project_name1,'admin')
        self.admin_connections.auth.add_user_to_project(username2,project_name2,'_member_')
        proj_conn1 = project_fix1.get_project_connections()
        proj_conn2 = project_fix2.get_project_connections()
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=project_fix1.project_name,
                connections=proj_conn1,
                vn_name='p1-vn1',
                subnets=['10.2.2.0/24']))
        assert not self.read_vn(proj_conn2,vn1_fixture.uuid)
    # end test_perms_with_diff_users_in_diff_projects

    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_perms_with_same_user_in_diff_projects(self):
        ''' Test user roles across projects in the same domain
            1) Create project1 and project2 
            2) Create and Attach user1 to project1 with admin role and as _member_ role to project2
            3) create VN1 under Project1
            4) project2 shouldnt be able to read VN1 using project2 creds'''
        username1 = get_random_name('TestUser-1')
        password1 = get_random_name('TestUser-1')
        project_name1 = get_random_name('TestProject-1')
        project_name2 = get_random_name('TestProject-2')
        domain_name = self.connections.domain_name
        project_fix1 = self.create_project(
            domain_name,project_name1,username1,password1)
        project_fix2 = self.create_project(
            domain_name,project_name2,username1,password1)
        self.admin_connections.auth.create_user(user=username1, password=password1,
            tenant_name=project_name1, domain_name=domain_name)
        self.admin_connections.auth.add_user_to_domain(username1,'admin',domain_name)
        self.admin_connections.auth.add_user_to_project(username1,project_name1,'admin')
        self.admin_connections.auth.add_user_to_project(username1,project_name2,'_member_')
        proj_conn1 = project_fix1.get_project_connections()
        proj_conn2 = project_fix2.get_project_connections()
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=project_fix1.project_name,
                connections=proj_conn1,
                vn_name='p1-vn1',
                subnets=['10.2.2.0/24']))
        assert not self.read_vn(proj_conn2,vn1_fixture.uuid)
    #end test_perms_with_same_user_in_diff_projects
  
    @preposttest_wrapper
    @skip_because(keystone_version = 'v2.0')
    def test_perms_with_diff_users_in_diff_domains(self):
        ''' 1)create domain d1 user1 project1
            2)Attach user1 to d1 and project1 as 'admin'
            2)Try to create domain d2 with d1 creds it should not be allowed
            3)create domain d2 user2 project2
            4)Attach user2 to domain d2 as 'admin' and to project2 as '_member_
            5)create VN1 under Project1 
            6)project2 shouldnt be able to read VN1 using project2 creds'''
        username1 = get_random_name('TestUser-1')
        password1 = get_random_name('TestUser-1')
        username2 = get_random_name('TestUser-2')
        password2 = get_random_name('TestUser-2')
        project_name1 = get_random_name('TestProject-1')
        project_name2 = get_random_name('TestProject-2')
        domain1 = get_random_name('TestDomain-1')
        domain2 = get_random_name('TestDomain-2')
        domain_fix1 = self.create_domain(domain1)
        project_fix1 = self.create_project(
            domain1,project_name1,username1,password1)
        self.admin_connections.auth.create_user(user=username1, password=password1,
            tenant_name=project_name1, domain_name=domain1)
        self.admin_connections.auth.add_user_to_domain(username1,'admin',domain1)
        domain_fix1.set_user_creds(username1,password1)
        self.admin_connections.auth.add_user_to_project(username1,project_name1,'admin')
        domain1_conn = domain_fix1.get_domain_connections(username1,password1,project_name1)
        try:
            obj = domain1_conn.auth.create_domain(domain_name=domain1)
        except:
            obj = None
        assert not obj,'Domain Created with user domain creds ,it should not be allowed.Test Failed'
        domain_fix2 = self.create_domain(domain2)
        project_fix2 = self.create_project(
            domain2,project_name2,username2,password2)
        self.admin_connections.auth.create_user(user=username2, password=password2,
            tenant_name=project_name2, domain_name=domain2)
        self.admin_connections.auth.add_user_to_domain(username2,'admin',domain2)
        self.admin_connections.auth.add_user_to_project(username2,project_name2,'_member_')
        proj_conn1 = project_fix1.get_project_connections()
        proj_conn2 = project_fix2.get_project_connections()
        vn1_fixture = self.create_vn(project_fix1,proj_conn1,'p1-vn1',['10.2.2.0/24'])
        assert not self.read_vn(proj_conn2,vn1_fixture.uuid)
    #end test_perms_with_diff_users_in_diff_domains

    def setup_common_objects(self, connections, project_fix):
        vn1_name = get_random_name('TestVN-1')
        vn1_subnet = ['10.1.1.0/24']
        vn2_name = get_random_name('TestVN-2')
        vn2_subnet = ['10.2.2.0/24']
        vm1_vn1_name = get_random_name('TestVM-1')
        vm2_vn2_name = get_random_name('TestVM-2')
        policy_name = get_random_name('TestPolicy')
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': 'any',
                  'source_network': 'any',
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]
        self.vn1_fixture = self.create_vn(project_fix,connections,vn1_name,vn1_subnet)
        self.vn2_fixture = self.create_vn(project_fix,connections,vn2_name,vn2_subnet)
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=connections))
        policy_fq_name = [policy_fixture.policy_fq_name]
        self.vn1_fixture.bind_policies(
            policy_fq_name, self.vn1_fixture.vn_id)
        self.addCleanup(self.vn1_fixture.unbind_policies,
                        self.vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        self.vn2_fixture.bind_policies(
            policy_fq_name, self.vn2_fixture.vn_id)
        self.addCleanup(self.vn2_fixture.unbind_policies,
                        self.vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        self.vm1_fixture = self.useFixture(
            VMFixture(
                connections=connections,
                vn_obj=self.vn1_fixture.obj,
                vm_name=vm1_vn1_name,
                project_name=project_fix.project_name))
        self.vm2_fixture = self.useFixture(
            VMFixture(
                connections=connections,
                vn_obj=self.vn2_fixture.obj,
                vm_name=vm2_vn2_name,
                project_name=project_fix.project_name))
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()
        ret = self.vm1_fixture.ping_with_certainty(expectation=True,
                                                   dst_vm_fixture=self.vm2_fixture)
        return ret
