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
        cloud_admin_user=self.inputs.cloud_admin_user or 'admin'
        cloud_admin_pswd=self.inputs.cloud_admin_pswd or 'contrail123'
        cloud_admin_domain=self.inputs.cloud_admin_domain or 'default'

        auth_url = 'http://' + self.inputs.openstack_ip + ':5000/v3' or os.getenv('OS_AUTH_URL')
        insecure = bool(os.getenv('OS_INSECURE',True))

        keystone = KeystoneCommands(cloud_admin_user,
                                    cloud_admin_pswd,
                                    domain=cloud_admin_domain,
                                    auth_url=auth_url,
                                    region_name=self.inputs.region_name,
                                    insecure=insecure,
                                    inputs=self.inputs,
                                    logger=self.logger)

        domain_name=get_random_name('TestDomain-1')

        assert domain_id=keystone.create_domain(domain_name)
        domain_handle=keystone.find_domain(domain_name)
        domain_obj=keystone.get_domain(domain_handle)
        domain_name_new=get_random_name('TestDomain-New')
        assert keystone.update_domain(domain_obj, domain_name_new,
            description='Changed the domain name as part of update.',
            enabled=True)
        assert domain_list=keystone.list_domains()
        domain_found=0
        for each_domain in domain_list:
            if domain_name_new in each_domain:
                self.logger.info('Domain Create, Read and Update Passed for domain %s PASSED.' %
                    (domain_name))
                domain_found=1
        if domain_found==0:
            self.logger.info('Domain Create, Read and Update Passed for domain %s FAILED.' %
                (domain_name))
        assert keystone.update_domain(domain_obj, domain_name_new,
            enabled=False)
        assert keystone.delete_domain(domain_name_new, domain_obj)
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
        cloud_admin_user=self.inputs.cloud_admin_user or 'admin'
        cloud_admin_pswd=self.inputs.cloud_admin_pswd or 'c0ntrail123'
        cloud_admin_domain=self.inputs.cloud_admin_domain or 'default'

        auth_url = 'http://' + self.inputs.openstack_ip + ':5000/v3' or os.getenv('OS_AUTH_URL')

        keystone = KeystoneCommands(cloud_admin_user,
                                    cloud_admin_pswd,
                                    domain=cloud_admin_domain,
                                    auth_url=auth_url,
                                    region_name=self.inputs.region_name,
                                    insecure=insecure,
                                    inputs=self.inputs,
                                    logger=self.logger)

        domain_name=get_random_name('TestDomain-1')
        user_name=get_random_name('TestUser-1')
        pswd=get_random_name('TestUser-1')
        project_name=get_random_name('TestProject-1')
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

        assert domain_id=keystone.create_domain(domain_name)
        domain_handle=keystone.find_domain(domain_name)
        domain_obj=keystone.get_domain(domain_handle)
        assert project_id=keystone.create_project(project_name, domain_name)
        assert keystone.create_user(user=user_name, password=pswd,
            project_name=project_name, domain_name=domain_name)
        assert keystone.add_user_role(user_name=user_name, role_name='admin',
            tenant_name=project_name)
        assert keystone.add_user_role(user_name=user_name, role_name='_member_',
            tenant_name=project_name)
        assert keystone.add_user_to_tenant(tenant=project_name, user=user_name,
            role='admin', domain=domain_name)
        assert keystone.add_user_to_tenant(tenant=project_name, user=user_name,
            role='_member_', domain=domain_name)
        assert self.VN1_fixture = self.useFixture(
            VNFixture(
                project_name=project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnet))

        assert self.VN2_fixture = self.useFixture(
            VNFixture(
                project_name=project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnet))
  
        assert policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))

        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.VN1_fixture.vn_name,
                policy_obj={self.VN1_fixture.vn_name : \
                           [policy_fixture.policy_obj]},
                vn_obj={self.VN1_fixture.vn_name : self.VN1_fixture},
                vn_policys=[policy_name],
                project_name=project_name))

        assert self.VM1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN1_fixture.obj,
                vm_name=vm1_vn1_name,
                project_name=project_name))
        assert self.VM2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=self.VN2_fixture.obj,
                vm_name=vm2_vn2_name,
                project_name=project_name))
        self.VM1_fixture.wait_till_vm_is_up()
        self.VM2_fixture.wait_till_vm_is_up()

        ret = self.VM1_fixture.ping_with_certainty(expectation=True,
                                    dst_vm_fixture=self.VM2_fixture)

        if ret == True :
            self.logger.info("Test PASSED")
        else:
            result = False
            self.logger.error("Test FAILED")
        return True
    # end test_domain_sanity

    @preposttest_wrapper
    @skip_because(domain_isolation=False)
    def test_domain_user_group(self):
        ''' Test user group within a domain.
        '''
        cloud_admin_user=self.inputs.cloud_admin_user or 'admin'
        cloud_admin_pswd=self.inputs.cloud_admin_pswd or 'c0ntrail123'
        cloud_admin_domain=self.inputs.cloud_admin_domain or 'default'

        auth_url = 'http://' + self.inputs.openstack_ip + ':5000/v3' or os.getenv('OS_AUTH_URL')



        keystone = KeystoneCommands(cloud_admin_user,
                                    cloud_admin_pswd,
                                    domain=cloud_admin_domain,
                                    auth_url=auth_url,
                                    region_name=self.inputs.region_name,
                                    insecure=insecure,
                                    inputs=self.inputs,
                                    logger=self.logger)

        domain_name=get_random_name('TestDomain-1')
        user_name=get_random_name('TestUser-1')
        pswd=get_random_name('TestUser-1')
        project=get_random_name('TestProject-1')

        assert domain_id=keystone.create_domain(domain_name)
        domain_handle=keystone.find_domain(domain_name)
        domain_obj=keystone.get_domain(domain_handle)
        assert project_id=keystone.create_project(project_name, domain_name)
        assert keystone.create_user(user=user_name, password=pswd,
            project_name=project_name, domain_name=domain_name)
        assert keystone.create_user_group(user_group=user_group, password=pswd,
            project_name=project_name, domain_name=domain_name)
        assert keystone.add_user_group_role(user_group=user_group, role_name='admin',
            tenant_name=project_name)
        assert keystone.add_user_group_role(user_group=user_group, role_name='_member_',
            tenant_name=project_name)
        assert keystone.add_user_group_to_tenant(tenant=project_name, user_group=user_group,
            role='admin', domain=domain_name)
        assert keystone.add_user_group_to_tenant(tenant=project_name, user_group=user_group,
            role='_member_', domain=domain_name)
        

        domain_name_new=get_random_name('TestDomain-New')
        assert keystone.update_domain(domain_obj, domain_name_new,
            description='Changed the domain name as part of update.',
            enabled=True)
        assert domain_list=keystone.list_domains()
        domain_found=0
        for each_domain in domain_list:
            if domain_name_new in each_domain:
                self.logger.info('Domain Create, Read and Update Passed for domain %s PASSED.' %
                    (domain_name))
                domain_found=1
        if domain_found==0:
            self.logger.info('Domain Create, Read and Update Passed for domain %s FAILED.' %
                (domain_name))
        assert keystone.delete_domain(domain_name_new, domain_obj)
        return True
    # end test_domain_user_group
# end of class TestDomain

