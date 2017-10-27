import test
from base import BaseRbac
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name, get_random_ip

class TestRbac(BaseRbac):
    @preposttest_wrapper
    def test_create_delete_service_chain(self):
        '''
        Validate creds passed via service-monitor/schema-transformer
        steps:
           1. Add user1 as role1
           2. Update project acl with role1:CRUD perms for *.*
           3. Validate Service-Chain of type Sevice-Template Version-1 as user1
           4. Validate Service-Chain of type Sevice-Template Version-2 as user1
        '''
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        user1_conn.inputs.use_admin_auth = True
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 }]
        proj_rbac = self.create_rbac_acl(rules=rules)
        assert self.create_sc(connections=user1_conn), 'SC v1 creation failed'
        assert self.create_sc(connections=user1_conn, st_version=2), 'SC v2 creation failed'

    @test.attr(type=['sanity', 'vcenter_compute'])
    @preposttest_wrapper
    def test_perms2_global_share(self):
        '''
        Test perms2 global shared property of an object
        steps:
            1. Add user1 as role1 in project1 and project2
            2. Add *.* role1:CRUD to domain acl
            3. Create a Shared virtual-network in project1
            4. Verify global shared flag is set on VN's perms2
            4. Using shared VN try to launch a VM in project2
        '''
        project1 = self.create_project()
        project2 = self.create_project()
        self.add_user_to_project(self.user1, self.role1, project1.project_name)
        self.add_user_to_project(self.user1, self.role1, project2.project_name)
        u1_p1_conn = self.get_connections(self.user1, self.pass1, project1)
        u1_p2_conn = self.get_connections(self.user1, self.pass1, project2)
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                }]
        domain_rbac = self.create_rbac_acl(rules=rules, parent_type='domain')
        vn = self.create_vn(connections=u1_p1_conn, shared=True, verify=False)
        assert vn, 'VN creation failed'
        obj = self.read_vn(connections=u1_p1_conn, uuid=vn.uuid)
        assert obj, 'Unable to read VN using user1/proj1 creds'
        assert obj.is_shared, 'VN is not marked shared'
        assert obj.global_access() == 7
        assert self.read_vn(connections=u1_p2_conn, uuid=vn.uuid)
        vm = self.create_vm(connections=u1_p2_conn, vn_fixture=vn)
        assert vm, 'VM creation failed on shared VN'

    @preposttest_wrapper
    def test_perms2_share(self):
        '''
        Test perms2 shared property of an object
        steps:
            1. Add user1 as role1 in project1 and project2
            2. Create VN and FIP-Pool as admin in isloated tenant
            3. Make the FIP Pool sharable with project1
            4. launch VM on project1 and associate FIP from FIP-Pool
            5. fip create from associate FIP from FIP-Pool
        '''
        project1 = self.create_project()
        project2 = self.create_project()
        self.add_user_to_project(self.user1, self.role1, project1.project_name)
        self.add_user_to_project(self.user1, self.role1, project2.project_name)
        u1_p1_conn = self.get_connections(self.user1, self.pass1, project1)
        u1_p2_conn = self.get_connections(self.user1, self.pass1, project2)
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                }]
        domain_rbac = self.create_rbac_acl(rules=rules, parent_type='domain')
        vn = self.create_vn()
        fip_pool = self.create_fip_pool(vn_fixture=vn)
        self.share_obj(obj=fip_pool.fip_pool_obj, project=project1)
        vm1 = self.create_vm(connections=u1_p1_conn, vn_fixture=vn)
        vm2 = self.create_vm(connections=u1_p2_conn, vn_fixture=vn)
        (fip, fip_id) = self.create_fip(connections=u1_p1_conn, fip_pool=fip_pool, vm_fixture=vm1)
        assert fip and fip_id, "FIP creation failed"
        (fip, fip_id) = self.create_fip(connections=u1_p2_conn, fip_pool=fip_pool, vm_fixture=vm2)
        assert not fip or not fip_id, "FIP creation should have failed"
        self.share_obj(obj=fip_pool.fip_pool_obj, project=project2, perms=4)
        assert self.read_fip_pool(connections=u1_p2_conn, uuid=fip_pool.fip_pool_id), "Unable to read shared FIP Pool object"

    @preposttest_wrapper
    def test_delete_default_acl(self):
        '''
        delete default acl recreation
        steps:
            1. delete default acl
            2. restart contrail-api service
            3. default acl should be recreated on restart
        '''
        self.global_acl.delete()
        # Restart one contrail-api service alone
        self.inputs.restart_service('contrail-api', [self.inputs.cfgm_ip],
                                    container='controller')
        self.populate_default_rules_in_global_acl()
        assert not self.global_acl.created, "Global ACL didnt get auto created upon restart"

    @preposttest_wrapper
    def test_rbac_rules_hierarchy(self):
        '''
        Validate rules hierarchy and longest acl rule match
        steps:
            1. Create global rule '*.* role1:R'
            2. Create domain rule 'VirtualNetwork.* role2:R'
            3. Create project rule 'VirtualNetwork.flood_unknown_unicast admin:CRUD'
            4. Add user1 as role1 and user2 as role2
            5. ToDo: Not sure about the expected results
        '''
        self.add_user_to_project(self.user1, self.role1)
        self.add_user_to_project(self.user2, self.role2)
        user1_conn = self.get_connections(self.user1, self.pass1)
        user2_conn = self.get_connections(self.user2, self.pass2)
        vn = self.create_vn()
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 }]
        self.global_acl.add_rules(rules=rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': rules}))
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert not self.read_vn(connections=user2_conn, uuid=vn.uuid)
        domain_rules = [{'rule_object': 'virtual-network',
                         'rule_field': None,
                         'perms': [{'role': self.role2, 'crud': 'CRUD'}]
                        }]
        domain_rbac = self.create_rbac_acl(rules=domain_rules, parent_type='domain')
        assert self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.read_vn(connections=user1_conn, uuid=vn.uuid)
        proj_rules = [{'rule_object': 'virtual-network',
                       'rule_field': 'flood_unknown_unicast',
                       'perms': [{'role': 'admin', 'crud': 'CRUD'}]
                      }]
        project_rbac = self.create_rbac_acl(rules=proj_rules)
        assert not self.update_vn(connections=user2_conn, uuid=vn.uuid,
                                  prop_kv={'flood_unknown_unicast': True})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
                              prop_kv={'flood_unknown_unicast': True})


class RbacMode(BaseRbac):
    @classmethod
    def setUpClass(cls):
        super(RbacMode, cls).setUpClass()
        cls.inputs.api_server_port = '9100'

    @preposttest_wrapper
    def test_update_aaa_mode(self):
        '''
        Validate the aaa_mode rest api
        steps:
            1. Add user1 as role1
            2. change aaa_mode to no-auth
            3. user1 should be able to create VN
            4. change aaa_mode to cloud-admin
            5. user1 shouldnt be able to read/create VNs
            6. Admin should be able to create/read VNs
            7. change aaa_mode to rbac
            8. Add global rule *.* role1:R
            9. user1 should be able to read VN
        '''
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        self.set_aaa_mode('no-auth')
        self._cleanups.insert(0, (self.set_aaa_mode, (), {'aaa_mode': 'rbac'}))
        vn = self.create_vn(connections=user1_conn, verify=False)
        assert vn, 'VN creation failed'
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        self.set_aaa_mode('cloud-admin')
        assert not self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert self.read_vn(connections=self.connections, uuid=vn.uuid)
        self.set_aaa_mode('rbac')
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                }]
        self.global_acl.add_rules(rules=rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': rules}))
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        return True

class RbacLbassv2(BaseRbac):
    def is_test_applicable(self):
        if self.inputs.orchestrator.lower() != 'openstack':
            return (False, 'Skipping Test. Openstack required')
        if self.inputs.get_build_sku().lower()[0] < 'l':
            return (False, 'Skipping Test. LBaasV2 is supported only on liberty and up')
        return (True, None)

    @preposttest_wrapper
    def test_rbac_lbaasv2_plugin(self):
        '''
        Validate contrail neutron lbaasv2 plugin for rbac
        steps:
            1. Add user1 as role1
            2. create project acl rule *.* role1:CRUD
            3. create loadbalancer as user1
        '''
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 }]
        proj_rbac = self.create_rbac_acl(rules=rules)
        vn = self.create_vn(connections=user1_conn)
        vm_ip = get_random_ip(vn.get_cidrs()[0])
        members = {'address': [vm_ip]}
        lb_name = get_random_name('rbac-lb')
        assert self.create_lbaas(connections=user1_conn,
                                 lb_name=lb_name, network_id=vn.uuid,
                                 members=members, hm_probe_type='PING')

class TestRbac2(BaseRbac):
    @preposttest_wrapper
    def test_rbac_multiple_roles(self):
        '''
        validate a user(user1) having multiple roles (role1 and role2)
        steps:
            1. Add user1 as both role1 and role2
            2. Update domain acl with role1:R for VirtualNetwork
            3. Create VN and VMI as admin user
            4. Try reading the VN and VM as user1
            5. Update domain acl with role2:R for VirtualMachineInterface
            6. Try reading the VN and VM as user1
        '''
        vn = self.create_vn()
        vmi = self.create_vmi(vn_fixture=vn)
        self.add_user_to_project(self.user1, self.role1)
        self.add_user_to_project(self.user1, self.role2)
        user1_conn = self.get_connections(self.user1, self.pass1)
        vn_rules = [{'rule_object': 'virtual-network',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'R'}]
                   }]
        vmi_rules = [{'rule_object': 'virtual-machine-interface',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                    }]
        domain_rbac = self.create_rbac_acl(rules=vn_rules, parent_type='domain')
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert not self.read_vmi(connections=user1_conn, uuid=vmi.uuid)
        domain_rbac.add_rules(rules=vmi_rules)
        domain_rbac.verify_on_setup()
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert self.read_vmi(connections=user1_conn, uuid=vmi.uuid)

