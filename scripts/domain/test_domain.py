from base import BaseDomainTest
from tcutils.wrappers import preposttest_wrapper
import test
from vn_test import *
from quantum_test import *
from policy_test import *
from vm_test import *
from tcutils.test_lib.test_utils import assertEqual
from tcutils.util import skip_because
from tcutils.util import get_random_name
from keystone_tests import KeystoneCommands
from domain_test import *
from user_test import *

class TestDomain(BaseDomainTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestDomain, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestDomain, cls).tearDownClass()

    @preposttest_wrapper
    @skip_because(domain_isolation=False)
    def test_crud_domain(self):
        ''' Test create read update and delete domain.
        '''
        domain_name=get_random_name('TestDomain-1')
        username = 'admin'
        password = 'contrail123'
        domain_fix = self.useFixture(DomainFixture(connections=self.admin_connections,
                                                   domain_name=domain_name,
                                                   username=username, password=password))
        domain_name_new=get_random_name('TestDomain-New')
        domain_update=domain_fix.update_domain(domain_name_new,
            description='Changed the domain name as part of update.',
            enabled=True)
        domain_found=domain_fix.get_domain()
        if domain_update and domain_found:
            self.logger.info('Domain Create, Read and Update for domain %s PASSED.' %
                (domain_name))
        else:
            self.logger.info('Domain Create, Read and Update for domain %s FAILED.' %
                (domain_name))
        return True
    # end test_crud_domain

    @preposttest_wrapper
    @skip_because(domain_isolation=False)
    def test_domain_sanity(self):
        ''' Sanity Test for domain isolation.
            One full circle of project, user, vm, vn creation 
            with ping traffic between the VM's is tested in a
            newly created domain.
        '''
        username=get_random_name('TestUser-1')
        password=get_random_name('TestUser-1')
        project_name=get_random_name('TestProject-1')
        
        project_fix=self.useFixture(ProjectFixture(
                domain_name = self.connections.domain_name,
                project_name = project_name,
                auth=self.connections.auth,
                username= username,
                password= password,
                connections= self.connections))
        project_fix.set_user_creds(username,password)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_fix,username,password)
        proj_conn = project_fix.get_project_connections()
        ret = self.setup_common_objects(connections=proj_conn)

        if ret == True :
            self.logger.info("Test PASSED")
        else:
            result = False
            self.logger.error("Test FAILED")
        return True
    # end test_domain_sanity

    @preposttest_wrapper
    @skip_because(domain_isolation=False)
    def test_domain_user_group1(self):
        ''' Test user group within a domain
            1) Create project
            2) Create user1 and user2 
            3) Create user_group and attach user to it
            4) Attach user_group to domain and project with admin and member roles
            5) Get project connections with user1 and create projects it should be allowed
            6)Verify user_group by creating vn and vms
        '''
        username=get_random_name('TestUser-1')
        password=get_random_name('TestUser-1')
        project_name=get_random_name('TestProject-1')
        domain_name=self.connections.domain_name
        user_group = get_random_name('TestGroup-1')
        project_fix=self.useFixture(ProjectFixture(
                domain_name = domain_name,
                project_name = project_name,
                auth=self.connections.auth,
                username= username,
                password= password,
                connections= self.connections))
        project_fix.set_user_creds(username,password)
        self.admin_connections.auth.create_user(user=username, password=password,
            project_name=project_name, domain_name=domain_name)
        self.admin_connections.auth.create_user_group(group=user_group,domain_name=domain_name)
        self.admin_connections.auth.add_user_to_group(user=username,group=user_group)
        self.admin_connections.auth.add_user_group_to_tenant(project=project_name, group=user_group,
            role='admin', domain=domain_name)
        self.admin_connections.auth.add_user_group_to_tenant(project=project_name, group=user_group,
            role='_member_', domain=domain_name)
        proj_conn = project_fix.get_project_connections()
        ret = self.setup_common_objects(connections=proj_conn)
        if ret == True :
            self.logger.info("Test PASSED")
        else:
            result = False
            self.logger.error("Test FAILED")
        return True
        
        return True
    # end test_domain_user_group
    
    @preposttest_wrapper
    @skip_because(domain_isolation=False)
    def test_domain_user_group2(self):
        ''' Test user group within a domain
            1) Create project
            2) Create user1 and user2 
            3) Create user_group1 and attach user1 to it 
            4) Create user_group2 and attach user2 to it
            5) Attach user_group1 to project with admin role and user_group2 as __member__ role
            6) Try to create projects with user1 and it should be allowed
            7) Try to create project with user2 and it should fail '''
        
        username1=get_random_name('TestUser-1')
        password1=get_random_name('TestUser-1')
        username2=get_random_name('TestUser-2')
        password2=get_random_name('TestUser-2')
        project_name=get_random_name('TestProject-1')
        user_group1 = get_random_name('TestGroup-1')
        user_group2 = get_random_name('TestGroup-1')
        domain_name=self.connections.domain_name
        project_fix=self.useFixture(ProjectFixture(
                domain_name = domain_name,
                project_name = project_name,
                auth=self.connections.auth,
                username= username1,
                password= password2,
                connections= self.connections))
        self.admin_connections.auth.create_user(user=username1, password=password1,
            project_name=project_name, domain_name=domain_name)
        self.admin_connections.auth.create_user(user=username2, password=password2,
            project_name=project_name, domain_name=domain_name)
        self.admin_connections.auth.create_user_group(group=user_group1,domain_name=domain_name)
        self.admin_connections.auth.create_user_group(group=user_group2,domain_name=domain_name)
        self.admin_connections.auth.add_user_to_group(user=username1,group=user_group1)
        self.admin_connections.auth.add_user_to_group(user=username2,group=user_group2)
        self.admin_connections.auth.add_user_group_to_tenant(project=project_name, group=user_group1,
            role='admin', domain=domain_name)
        self.admin_connections.auth.add_user_group_to_tenant(project=project_name, group=user_group2,
            role='_member_', domain=domain_name)
        project_fix.set_user_creds(username1,password1)
        proj_conn = project_fix.get_project_connections()
        ret1 = self.setup_common_objects(connections=proj_conn)
        project_fix.set_user_creds(username2,password2)
        proj_conn = project_fix.get_project_connections()
        ret2 = self.setup_common_objects(connections=proj_conn)
        if (ret1 and ret2 ) == True :
            self.logger.info("Test PASSED")
        else:
            result = False
            self.logger.error("Test FAILED")
        return True

# end of class TestDomain
    
    def setup_common_objects(self,connections,):
        vn1_name=get_random_name('TestVN-1')
        vn1_subnet=['10.1.1.0/24']
        vn2_name=get_random_name('TestVN-2')
        vn2_subnet=['10.2.2.0/24']
        vm1_vn1_name=get_random_name('TestVM-1')
        vm2_vn2_name=get_random_name('TestVM-2')
        policy_name=get_random_name('TestPolicy')
        rules = [{'direction': '<>',
                  'protocol': 'icmp',
                  'dest_network': vn2_name,
                  'source_network': vn1_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]
        self.VN1_fixture = self.useFixture(
            VNFixture(
                project_name=project_name,
                connections=proj_con,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnet))

        self.VN2_fixture = self.useFixture(
            VNFixture(
                project_name=project_name,
                connections=proj_conn,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnet))
  
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=proj_conn))

        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=proj_conn,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=[policy_name],
                project_name=project_name))

        self.VM1_fixture = self.useFixture(
            VMFixture(
                connections=proj_conn,
                vn_obj=self.VN1_fixture.obj,
                vm_name=vm1_vn1_name,
                project_name=project_name))
        self.VM2_fixture = self.useFixture(
            VMFixture(
                connections=proj_conn,
                vn_obj=self.VN2_fixture.obj,
                vm_name=vm2_vn2_name,
                project_name=project_name))
        self.VM1_fixture.wait_till_vm_is_up()
        self.VM2_fixture.wait_till_vm_is_up()
        ret = self.VM1_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM2_fixture)
        return ret

