import test
from base import BaseRbac
from tcutils.wrappers import preposttest_wrapper

class TestRbacBasic(BaseRbac):

    @test.attr(type=['sanity', 'suite1'])
    @preposttest_wrapper
    def test_rbac_acl_different_roles(self):
        '''
        Validate via vnc_apis CRUD of rbac acl and objects
        steps:
           1. Add user1 as role1 and user2 as role2 to the project
           2. Both user1 and user2 shouldnt be able to create VNs/STs
           3. Create Rbac ACL under project with VN.* and VNs.* role1:CRUD rule
           4. user1 should be able to create VN, but not Service-Template
           5. Create Rbac ACL under domain with ST.* and STs.* role1:CRUD rule
           6. user1 should be able to create Service-Template
           7. user2 shouldnt be able to read the created VN/ST or create new
           8. Update the acl rule with Read perms for role2
           9. user2 should be able to read created VN but not create new VNs
           10. user2 should be able to read created ST but not create new STs
           11. Delete the acl rule with Read perms for role2
           12. user2 shouldnt be able to read the created ST/VN or create new VN/ST
           13. Delete both project and domain acls
           14. user1 shouldnt be able to read/delete VN/ST
           15. Create global acl with role1:CRUD for both VN/ST
           16. user1 should now be able to delete both VN and ST
           17. Delete global acl
        pass : acl creation and update should complete scucessfully.
        '''
        self.add_user_to_project(self.user1, self.role1)
        self.add_user_to_project(self.user2, self.role2)
        user1_conn = self.get_connections(self.user1, self.pass1)
        user2_conn = self.get_connections(self.user2, self.pass2)
        assert not self.create_vn(connections=user1_conn), 'VN creation should have failed'
        assert not self.create_st(connections=user1_conn), 'ST creation should have failed'
        vn_rules = [{'rule_object': 'virtual-network',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    },
                    {'rule_object': 'virtual-networks',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    }]
        proj_rbac = self.create_rbac_acl(rules=vn_rules)
        vn = self.create_vn(connections=user1_conn)
        assert vn, 'VN creation failed'
        assert not self.create_st(connections=user1_conn), 'ST creation should have failed'
        st_rules = [{'rule_object': 'service-template',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    },
                    {'rule_object': 'service-templates',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    }]
        domain_rbac = self.create_rbac_acl(rules=st_rules, parent_type='domain')
        st = self.create_st(connections=user1_conn)
        assert st, 'ST creation failed'
        assert not self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.read_st(connections=user2_conn, uuid=st.uuid)
        vn2_rules = [{'rule_object': 'virtual-network',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     },
                     {'rule_object': 'virtual-networks',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     }]
        proj_rbac.add_rules(vn2_rules)
        proj_rbac.verify_on_setup()
        assert self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.create_vn(connections=user2_conn)
        assert not self.read_st(connections=user2_conn, uuid=st.uuid)
        st2_rules = [{'rule_object': 'service-template',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     },
                     {'rule_object': 'service-templates',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     }]
        domain_rbac.add_rules(st2_rules)
        domain_rbac.verify_on_setup()
        assert self.read_st(connections=user2_conn, uuid=st.uuid)
        assert not self.create_st(connections=user2_conn)
        proj_rbac.delete_rules(vn2_rules)
        proj_rbac.verify_on_setup()
        domain_rbac.delete_rules(st2_rules)
        domain_rbac.verify_on_setup()
        assert not self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.read_st(connections=user2_conn, uuid=st.uuid)
        proj_rbac.cleanUp(); self.remove_from_cleanups(proj_rbac)
        domain_rbac.cleanUp(); self.remove_from_cleanups(domain_rbac)
        assert not self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert not self.read_st(connections=user1_conn, uuid=st.uuid)
        self.global_acl.add_rules(rules=vn_rules+st_rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': vn_rules+st_rules}))
        assert self.read_vn(connections=user1_conn, uuid=vn.uuid)
        assert self.read_st(connections=user1_conn, uuid=st.uuid)
        return True

    @test.attr(type=['sanity', 'suite1'])
    @preposttest_wrapper
    def test_rbac_create_delete_vm(self):
        '''
        Validate creds passed via orchestrator(nova/neutron)
        steps:
           1. Add user1 as role1
           2. Create Rbac ACL under project with role1:CRUD perms for
                a. VN.*
                b. VNs.*
                c. VM.*
                d. VMs.*
                e. VMI.*
                f. VMIs.*
                g. IIP.*
                h. IIPs.*
                i. SG.*
                j. SGs.*
                h. LR.*
           3. user1 should be able to create VN and VM via orchestrator
           4. Validate the VN and VM
        pass: user should be able to create and delete VN and VM
        '''
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        rules = [{'rule_object': 'virtual-network',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-networks',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machines',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machine',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machine-interfaces',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machine-interface',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'instance-ips',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'instance-ip',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'security-group',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'security-groups',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'logical-routers',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'R'}]
                 },
                 ]
        proj_rbac = self.create_rbac_acl(rules=rules)
        vn = self.create_vn(connections=user1_conn, option='neutron')
        assert vn, 'VN creation failed'
        vm = self.create_vm(connections=user1_conn, vn_fixture=vn)
        assert vm, 'VM creation failed'

    @test.attr(type=['sanity', 'suite1'])
    @preposttest_wrapper
    def test_perms2_owner(self):
        '''
        Validate perms2 tenant ownership
        steps:
            1. Create Project1 and Project2
            2. Add user1 as role1 under project1 and project2
            3. create domain acl rule 'VirtualNetwork.* role1:CRUD', 'VNs.* role1:CRUD'
            4. create VN1 under Project1
            5. user1 shouldnt be able to read VN1 using project2 creds
            6. admin should be able to read VN1 though he isnt member of the project
        '''
        project1 = self.create_project()
        project2 = self.create_project()
        self.add_user_to_project(self.user1, self.role1, project1.project_name)
        self.add_user_to_project(self.user1, self.role1, project2.project_name)
        u1_p1_conn = self.get_connections(self.user1, self.pass1, project1)
        u1_p2_conn = self.get_connections(self.user1, self.pass1, project2)
        vn_rules = [{'rule_object': 'virtual-network',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    },
                    {'rule_object': 'virtual-networks',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    }]
        domain_rbac = self.create_rbac_acl(rules=vn_rules, parent_type='domain')
        vn = self.create_vn(connections=u1_p1_conn, verify=False)
        assert vn, 'VN creation failed'
        assert self.read_vn(connections=u1_p1_conn, uuid=vn.uuid)
        assert not self.read_vn(connections=u1_p2_conn, uuid=vn.uuid)
        assert self.read_vn(connections=self.connections, uuid=vn.uuid)
