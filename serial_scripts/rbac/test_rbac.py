from __future__ import absolute_import
from .base import BaseRbac
import test
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
        assert self.create_sc(connections=user1_conn), 'SC creation failed'

    @test.attr(type=['sanity'])
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
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(u1_p1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(u1_p1_conn)
            assert self.get_vn_from_analytics(u1_p2_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(u1_p2_conn)
        vm = self.create_vm(connections=u1_p2_conn, vn_fixture=vn)
        assert vm, 'VM creation failed on shared VN'

    @preposttest_wrapper
    def test_perms2_share_basic(self):
        '''
        Test perms2 shared property of an object
        steps:
            1. Add user1 as role1 in project1 and project2
            2. Create VN as admin in isloated tenant
            3. Make the VN sharable with project1 (access: 7)
            4. List VN with Project1 creds should display VN
            5. List VN with Project2 creds shouldnt display VN
            6. Share the VN with Project2 (access: 4)
            7. user should be able to read VN but
               not update the VN using Project2 creds
            8. List VN with both Projects creds should display VN
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
        vn = self.create_vn(option='quantum')
        self.share_obj(obj=vn.api_vn_obj, project=project1)
        vns = self.list_vn(u1_p1_conn)
        assert vn.uuid in vns
        vns = self.list_vn(u1_p2_conn)
        assert vn.uuid not in vns
        assert not self.read_vn(connections=u1_p2_conn, uuid=vn.uuid), "Able to read non-shared FIP Pool object"
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(u1_p1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(u1_p1_conn)
            assert not self.get_vn_from_analytics(u1_p2_conn, vn.vn_fq_name)
            assert vn.vn_fq_name not in self.list_vn_from_analytics(u1_p2_conn)
        self.share_obj(obj=vn.api_vn_obj, project=project2, perms=4)
        assert self.read_vn(connections=u1_p2_conn, uuid=vn.uuid), "Unable to read non-shared FIP Pool object"
        vns = self.list_vn(u1_p1_conn)
        assert vn.uuid in vns
        vns = self.list_vn(u1_p2_conn)
        assert vn.uuid in vns
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(u1_p1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(u1_p1_conn)
            assert self.get_vn_from_analytics(u1_p2_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(u1_p2_conn)

    @preposttest_wrapper
    def test_perms2_share(self):
        '''
        Test perms2 shared property of an object
        steps:
            1. Add user1 as role1 in project1 and project2
            2. Create VN and FIP-Pool as admin in isloated tenant
            3. Make the FIP Pool sharable with project1 (access: 7)
            4. List fip-pool with Project1 creds should display FIP-Pool
            5. List fip-pool with Project2 creds shouldnt display FIP-Pool
            6. launch VM on project1 and associate FIP from FIP-Pool
            7. create/associate FIP with Project2 should fail
            8. Share the FIP pool with Project2 (access: 4)
            9. user should only be able to read fip-pool but
               not create/associate fip using Project2 creds
            10. List fip-pool with both Projects creds should display FIP-Pool
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
        fip_pools = self.list_fip_pool(u1_p1_conn)
        assert fip_pool.fip_pool_id in fip_pools
        fip_pools = self.list_fip_pool(u1_p2_conn)
        assert fip_pool.fip_pool_id not in fip_pools
        vm1 = self.create_vm(connections=u1_p1_conn, vn_fixture=vn)
        vm2 = self.create_vm(connections=u1_p2_conn, vn_fixture=vn)
        (fip, fip_id) = self.create_fip(connections=u1_p1_conn, fip_pool=fip_pool, vm_fixture=vm1, pub_vn_fixture=vn)
        assert fip and fip_id, "FIP creation failed"
        (fip, fip_id) = self.create_fip(connections=u1_p2_conn, fip_pool=fip_pool, vm_fixture=vm2, pub_vn_fixture=vn)
        assert not fip or not fip_id, "FIP creation should have failed"
        assert not self.read_fip_pool(connections=u1_p2_conn, uuid=fip_pool.fip_pool_id), "Able to read non-shared FIP Pool object"
        self.share_obj(obj=fip_pool.fip_pool_obj, project=project2, perms=4)
        assert self.read_fip_pool(connections=u1_p2_conn, uuid=fip_pool.fip_pool_id), "Unable to read shared FIP Pool object"
        (fip, fip_id) = self.create_fip(connections=u1_p2_conn, fip_pool=fip_pool, vm_fixture=vm2, pub_vn_fixture=vn)
        assert not fip or not fip_id, "FIP creation should have failed"
        fip_pools = self.list_fip_pool(u1_p1_conn)
        assert fip_pool.fip_pool_id in fip_pools
        fip_pools = self.list_fip_pool(u1_p2_conn)
        assert fip_pool.fip_pool_id in fip_pools

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
                                    container='api-server')
        self.populate_default_rules_in_global_acl()
        assert not self.global_acl.created, "Global ACL didnt get auto created upon restart"

    @preposttest_wrapper
    def test_rules_aggregation(self):
        '''
        Validate aggregation of rules against object type
        steps:
            1. Add user1 as role1 and user2 as role2 and user3 as role3
            2. add VN.* R perms for R1 and R2 in global acl
            3. add VN.* U perms for R1 and C perms for R2 in domain acl
            4. add VN.* D perms for R2 and CRUD for R3 in project acl
            5. Validate that user1 can RU the VN object,
               user2 can CRD the VN object and R3 can CRUD the VN object
        '''
        self.add_user_to_project(self.user1, self.role1)
        self.add_user_to_project(self.user2, self.role2)
        self.add_user_to_project(self.user3, self.role3)
        user1_conn = self.get_connections(self.user1, self.pass1)
        user2_conn = self.get_connections(self.user2, self.pass2)
        user3_conn = self.get_connections(self.user3, self.pass3)
        rules = [{'rule_object': 'floating-ip-pool',
                  'rule_field': None,
                  'perms': [{'role': '*', 'crud': 'R'}]
                 }, {'rule_object': 'virtual-network',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'R'},
                            {'role': self.role2, 'crud': 'R'}]
                 }]
        self.global_acl.add_rules(rules=rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': rules}))
        rules = [{'rule_object': 'virtual-network',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'U'},
                            {'role': self.role2, 'crud': 'C'}]
                 }]
        domain_rbac = self.create_rbac_acl(rules=rules, parent_type='domain')
        rules = [{'rule_object': 'virtual-network',
                  'rule_field': None,
                  'perms': [{'role': self.role2, 'crud': 'D'},
                            {'role': self.role3, 'crud': 'CRUD'}]
                 }]
        proj_rbac = self.create_rbac_acl(rules=rules)
        assert not self.create_vn(connections=user1_conn, option='quantum', verify=False)
        user2_vn = self.create_vn(connections=user2_conn, option='quantum')
        assert user2_vn, 'User with CRD perms is not able to create vn'
        user3_vn = self.create_vn(connections=user3_conn, option='quantum')
        assert user3_vn, 'User with CRUD perms is not able to create vn'
        assert self.read_vn(connections=user1_conn, uuid=user2_vn.uuid, option='quantum')
        assert self.read_vn(connections=user2_conn, uuid=user2_vn.uuid, option='quantum')
        assert self.read_vn(connections=user3_conn, uuid=user2_vn.uuid, option='quantum')
        assert self.read_vn(connections=user1_conn, uuid=user3_vn.uuid, option='quantum')
        assert self.read_vn(connections=user2_conn, uuid=user3_vn.uuid, option='quantum')
        assert self.read_vn(connections=user3_conn, uuid=user3_vn.uuid, option='quantum')
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, user2_vn.vn_fq_name)
            assert self.get_vn_from_analytics(user2_conn, user2_vn.vn_fq_name)
            assert self.get_vn_from_analytics(user3_conn, user2_vn.vn_fq_name)
            assert self.get_vn_from_analytics(user1_conn, user3_vn.vn_fq_name)
            assert self.get_vn_from_analytics(user2_conn, user3_vn.vn_fq_name)
            assert self.get_vn_from_analytics(user3_conn, user3_vn.vn_fq_name)
            u1_vn_list = self.list_vn_from_analytics(user1_conn)
            assert user2_vn.vn_fq_name in u1_vn_list and user3_vn.vn_fq_name in u1_vn_list
            u2_vn_list = self.list_vn_from_analytics(user2_conn)
            assert user2_vn.vn_fq_name in u2_vn_list and user3_vn.vn_fq_name in u2_vn_list
            u3_vn_list = self.list_vn_from_analytics(user3_conn)
            assert user2_vn.vn_fq_name in u3_vn_list and user3_vn.vn_fq_name in u3_vn_list
        assert self.update_vn(connections=user1_conn, uuid=user2_vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': True})
        assert self.update_vn(connections=user1_conn, uuid=user3_vn.uuid,
                                  prop_kv={'flood_unknown_unicast': True})
        assert not self.update_vn(connections=user2_conn, uuid=user2_vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': False})
        assert not self.update_vn(connections=user2_conn, uuid=user3_vn.uuid,
                                  prop_kv={'flood_unknown_unicast': False})
        assert self.update_vn(connections=user3_conn, uuid=user2_vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': False})
        assert self.update_vn(connections=user3_conn, uuid=user3_vn.uuid,
                                  prop_kv={'flood_unknown_unicast': False})
        assert not self.delete_vn(user2_vn, connections=user1_conn)

    @preposttest_wrapper
    def test_rbac_rules_hierarchy(self):
        '''
        Validate rules hierarchy and longest acl rule match
        steps:
            1. Add user1 as role1 and user2 as role2
            2. Create VN as admin in isloated tenant
            3. Create global rule '*.* role1:CRUD'
            4. user1 should be able to read VN and user2 shouldnt be
            5. Create domain rule 'VirtualNetwork.* role2:CRUD'
            6. user1 should not be able to read VN and user2 should be
            7. Create project rules
               'VirtualNetwork.flood_unknown_unicast admin:CRUD',
               'VirtualNetwork.* role1:R',
               'VirtualNetwork.virtual_network_properties.forwarding_mode role2:CRUD',
               'VirtualNetwork.port_security_enabled *:CRUD'
            8. user2 shouldnt be able to update flood unknown unicast field
               howerver should be able to update port_security_enabled, allow_transit and forwarding mode
            9. user1 shouldnt be able to update allow_transit subfield
               howerver should be able to update port_security_enabled
            9. admin should be able to update all the fileds
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
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user1_conn)
            assert not self.get_vn_from_analytics(user2_conn, vn.vn_fq_name)
            assert vn.vn_fq_name not in self.list_vn_from_analytics(user2_conn)
        domain_rules = [{'rule_object': 'virtual-network',
                         'rule_field': None,
                         'perms': [{'role': self.role2, 'crud': 'CRUD'}]
                        }]
        domain_rbac = self.create_rbac_acl(rules=domain_rules, parent_type='domain')
        assert self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.read_vn(connections=user1_conn, uuid=vn.uuid)
        if self.rbac_for_analytics:
            assert not self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name not in self.list_vn_from_analytics(user1_conn)
            assert self.get_vn_from_analytics(user2_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user2_conn)
        proj_rules = [{'rule_object': 'virtual-network',
                       'rule_field': 'flood_unknown_unicast',
                       'perms': [{'role': 'admin', 'crud': 'CRUD'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': '*',
                       'perms': [{'role': self.role1, 'crud': 'R'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'VirtualNetwork.virtual_network_properties.forwarding_mode',
                       'perms': [{'role': self.role2, 'crud': 'CRUD'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'port_security_enabled',
                       'perms': [{'role': '*', 'crud': 'CRUD'}]
                      }]
        project_rbac = self.create_rbac_acl(rules=proj_rules)
        #WA to create VN properties before hand since an update
        #of prop for first time creates other subfields too
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': True})
        assert not self.update_vn(connections=user2_conn, uuid=vn.uuid,
                                  prop_kv={'flood_unknown_unicast': True})
        assert self.update_vn(connections=user2_conn, uuid=vn.uuid,
                              prop_kv={'port_security_enabled': True})
        assert self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.forwarding_mode': 'l3'})
        assert self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': False})
        assert not self.update_vn(connections=user1_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': True})
        assert self.update_vn(connections=user1_conn, uuid=vn.uuid,
                              prop_kv={'port_security_enabled': False})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
                              prop_kv={'flood_unknown_unicast': True})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
                              prop_kv={'port_security_enabled': True})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.forwarding_mode': 'l2_l3'})

    # Specifying subfields in ACL is no longer supported disabling the test
    def disabled_test_subfield_match(self):
        '''
        Validate rules hierarchy and longest acl rule match
        steps:
            1. Add user1 as role1 and user2 as role2
            2. Create VN as admin in isloated tenant
            3. Create project rule 'VirtualNetwork.virtual_network_properties *:CRUD',
                                   'VirtualNetwork.virtual_network_properties.allow_transit role1:CRUD'
                                   'VirtualNetwork.virtual_network_properties.forwarding_mode role2:CRUD'
                                   'VirtualNetwork.virtual_network_properties.rpf admin:CRUD'
                                   'VirtualNetwork.* *:R'
            4. user1 should be able to update allow_transit and vxlan_network_identifier
               but not forwarding_mode and rpf subfields
            5. user2 should be able to update forwarding_mode and vxlan_network_identifier
               but not allow_transit and rpf subfields
            6. admin should be able to update all the fileds
        '''
        self.add_user_to_project(self.user1, self.role1)
        self.add_user_to_project(self.user2, self.role2)
        user1_conn = self.get_connections(self.user1, self.pass1)
        user2_conn = self.get_connections(self.user2, self.pass2)
        vn = self.create_vn()
        proj_rules = [{'rule_object': 'virtual-network',
                       'rule_field': '*',
                       'perms': [{'role': '*', 'crud': 'R'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'virtual_network_properties',
                       'perms': [{'role': '*', 'crud': 'CRUD'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'virtual_network_properties.allow_transit',
                       'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'virtual_network_properties.forwarding_mode',
                       'perms': [{'role': self.role2, 'crud': 'CRUD'}]
                      },
                      {'rule_object': 'virtual-network',
                       'rule_field': 'virtual_network_properties.rpf',
                       'perms': [{'role': 'admin', 'crud': 'CRUD'}]
                      }]
        project_rbac = self.create_rbac_acl(rules=proj_rules)
        #WA to create VN properties before hand since an update
        #of prop for first time creates other subfields too
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.rpf': 'enable'})
        assert self.update_vn(connections=user1_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': True})
        assert self.update_vn(connections=user1_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.vxlan_network_identifier': 1111})
        assert not self.update_vn(connections=user1_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.forwarding_mode': 'l3'})
        assert not self.update_vn(connections=user1_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.rpf': 'disable'})
        obj = self.read_vn(connections=user1_conn, uuid=vn.uuid)
        prop = obj.virtual_network_properties
        assert prop['allow_transit'] is True and prop['vxlan_network_identifier'] == 1111
        assert prop['forwarding_mode'] != 'l3' and prop['rpf'] != 'disable'
        assert not self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': False})
        assert self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.vxlan_network_identifier': 2222})
        assert self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.forwarding_mode': 'l3'})
        assert not self.update_vn(connections=user2_conn, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.rpf': 'disable'})
        obj = self.read_vn(connections=user2_conn, uuid=vn.uuid)
        prop = obj.virtual_network_properties
        assert prop['allow_transit'] is True and prop['vxlan_network_identifier'] == 2222
        assert prop['forwarding_mode'] == 'l3' and prop['rpf'] != 'disable'
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.allow_transit': False})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.vxlan_network_identifier': 9999})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.forwarding_mode': 'l2_l3'})
        assert self.update_vn(connections=self.connections, uuid=vn.uuid,
               prop_kv={'virtual_network_properties.rpf': 'disable'})
        obj = self.read_vn(uuid=vn.uuid)
        prop = obj.virtual_network_properties
        assert prop['allow_transit'] is False and prop['vxlan_network_identifier'] == 9999
        assert prop['forwarding_mode'] == 'l2_l3' and prop['rpf'] == 'disable'

class RbacMode(BaseRbac):
    @classmethod
    def setUpClass(cls):
        super(RbacMode, cls).setUpClass()

    # test is disabled, since we don't want to support changing aaa-mode using API 
    @preposttest_wrapper
    def disabled_test_update_aaa_mode(self):
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
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user1_conn)
        self.set_aaa_mode('cloud-admin')
        assert not self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert self.read_vn(connections=self.connections, uuid=vn.uuid)
        if self.rbac_for_analytics:
            assert not self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name not in self.list_vn_from_analytics(user1_conn)
            assert self.get_vn_from_analytics(self.connections, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(self.connections)
        self.set_aaa_mode('rbac')
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                }]
        self.global_acl.add_rules(rules=rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': rules}))
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user1_conn)
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
        vmi_fq_name = vmi.vmi_obj.get_fq_name_str()
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
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user1_conn)
            assert not self.get_vmi_from_analytics(user1_conn, vmi_fq_name)
        domain_rbac.add_rules(rules=vmi_rules)
        domain_rbac.verify_on_setup()
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert self.read_vmi(connections=user1_conn, uuid=vmi.uuid)
        if self.rbac_for_analytics:
            assert self.get_vn_from_analytics(user1_conn, vn.vn_fq_name)
            assert vn.vn_fq_name in self.list_vn_from_analytics(user1_conn)
            assert self.get_vmi_from_analytics(user1_conn, vmi_fq_name)

class TestAnalyticsRbac(BaseRbac):
    @preposttest_wrapper
    def test_analytics_access(self):
        '''
        Check if tenant user is able to access global UVEs
        steps:
            1. Add user1 as role1 in current project
            2. User1 shouldnt be able to access analytics-nodes UVEs
            3. admin user should be able to access analytics-nodes UVEs
        '''
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        rules = [{'rule_object': '*',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 }]
        proj_rbac = self.create_rbac_acl(rules=rules)
        assert self.list_analytics_nodes_from_analytics(self.connections)
        assert not self.list_analytics_nodes_from_analytics(user1_conn)
