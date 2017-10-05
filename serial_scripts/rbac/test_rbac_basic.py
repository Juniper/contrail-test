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
           3. Create Rbac ACL under project with VN.* role1:CRUD rule
           4. user1 should be able to create VN, but not Service-Template
           5. Create Rbac ACL under domain with ST.* role1:CRUD rule
           6. user1 should be able to create Service-Template
           7. user2 shouldnt be able to read the created VN/ST or create new
           8. Update the acl rule with Read perms for role2
           9. user2 should be able to read created VN but not create new VNs
           10. user2 should be able to read created ST but not create new STs
           11. Delete the acl rule with Read perms for role2
           12. user2 shouldnt be able to read the created ST/VN or create new VN/ST
           13. Update global acl with role2:R for both VN and ST
           14. user2 should be able to read VN and ST
           13. Delete both project and domain acls
           14. user1 shouldnt be able to read/delete VN/ST
           15. Update global acl with role1:CRUD for both VN/ST
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
                    ]
        proj_rbac = self.create_rbac_acl(rules=vn_rules)
        vn = self.create_vn(connections=user1_conn)
        assert vn, 'VN creation failed'
        assert not self.create_st(connections=user1_conn), 'ST creation should have failed'
        st_rules = [{'rule_object': 'service-template',
                     'rule_field': None,
                     'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                    },
                    ]
        domain_rbac = self.create_rbac_acl(rules=st_rules, parent_type='domain')
        st = self.create_st(connections=user1_conn)
        assert st, 'ST creation failed'
        assert not self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.read_st(connections=user2_conn, uuid=st.uuid)
        vn2_rules = [{'rule_object': 'virtual-network',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     },
                     ]
        proj_rbac.add_rules(vn2_rules)
        proj_rbac.verify_on_setup()
        assert self.read_vn(connections=user2_conn, uuid=vn.uuid)
        assert not self.create_vn(connections=user2_conn)
        assert not self.read_st(connections=user2_conn, uuid=st.uuid)
        st2_rules = [{'rule_object': 'service-template',
                      'rule_field': None,
                      'perms': [{'role': self.role2, 'crud': 'R'}]
                     },
                     ]
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
        self.global_acl.add_rules(rules=vn2_rules+st2_rules)
        self._cleanups.insert(0, (self.global_acl.delete_rules, (), {'rules': vn2_rules+st2_rules}))
        assert self.read_st(connections=user2_conn, uuid=st.uuid)
        assert self.read_vn(connections=user2_conn, uuid=vn.uuid)
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
                b. VM.*
                c. VMI.*
                d. IIP.*
                e. SG.*
                f. LR.*
                g. FIP-Pool.*
                h. ACL.*
           3. user1 should be able to create VN and VM via orchestrator
           4. Validate the VN and VM
        pass: user should be able to create and delete VN and VM
        '''
        pub_vn = self.create_vn(option='quantum', router_external=True, shared=True)
        self.add_user_to_project(self.user1, self.role1)
        user1_conn = self.get_connections(self.user1, self.pass1)
        rules = [{'rule_object': 'virtual-network',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'floating-ip-pool',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'floating-ip',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machine',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'CRUD'}]
                 },
                 {'rule_object': 'virtual-machine-interface',
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
                 {'rule_object': 'logical-router',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'R'}]
                 },
                 {'rule_object': 'access-control-list',
                  'rule_field': None,
                  'perms': [{'role': self.role1, 'crud': 'R'}]
                 },
                 ]
        proj_rbac = self.create_rbac_acl(rules=rules)
        vn = self.create_vn(connections=user1_conn, option='neutron')
        assert vn, 'VN creation failed'
        sg = self.create_sg(connections=user1_conn)
        assert sg, 'SG creation failed'
        vm = self.create_vm(connections=user1_conn, vn_fixture=vn)
        assert vm, 'VM creation failed'
        fip_pool = self.create_fip_pool(pub_vn, connections=user1_conn,
                                        verify=False)
        (fip, fip_id) = self.create_fip(connections=user1_conn,
                        fip_pool=fip_pool, vm_fixture=vm, pub_vn_fixture=pub_vn)
        assert fip and fip_id, "fip creation failed"
        self.associate_sg(sg, vm)

    @test.attr(type=['sanity', 'suite1'])
    @preposttest_wrapper
    def test_perms2_owner(self):
        '''
        Validate perms2 tenant ownership
        steps:
            1. Create Project1 and Project2
            2. Add user1 as role1 under project1 and project2
            3. create domain acl rule 'VirtualNetwork.* role1:CRUD'
            4. create VN1 under Project1
            4. create VN2 under Project2
            5. user1 shouldnt be able to read VN1 using project2 creds
            6. admin should be able to read VN1 though he isnt member of the project
            7. Network list with respective project creds should list corresponding VNs
            8. Change ownership of VN1 to Project2
            9. user1 should now be able to read VN1 using Project2 creds
            10. Network list with Project2 creds should list both VNs,
                Project1 creds should list VN1 alone, admin should list both VNs
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
                    ]
        domain_rbac = self.create_rbac_acl(rules=vn_rules, parent_type='domain')
        vn = self.create_vn(connections=u1_p1_conn, verify=False)
        assert vn, 'VN creation failed'
        vn2 = self.create_vn(connections=u1_p2_conn, verify=False)
        assert vn2, 'VN creation failed'
        assert self.read_vn(connections=u1_p1_conn, uuid=vn.uuid)
        assert not self.read_vn(connections=u1_p2_conn, uuid=vn.uuid)
        assert self.read_vn(connections=self.connections, uuid=vn.uuid)
        vns = self.list_vn(connections=u1_p1_conn)
        assert (vn.uuid in vns) and (not vn2.uuid in vns)
        vns = self.list_vn(connections=u1_p2_conn)
        assert (vn2.uuid in vns) and (not vn.uuid in vns)
        self.set_owner(vn.api_vn_obj, project2)
        self._cleanups.append((self.set_owner, (vn.api_vn_obj, project1), {}))
        vns = self.list_vn(connections=u1_p1_conn)
        assert not (vn.uuid in vns or vn2.uuid in vns)
        vns = self.list_vn(connections=u1_p2_conn)
        assert (vn2.uuid in vns) and (vn.uuid in vns)
        vns = self.list_vn()
        assert (vn2.uuid in vns) and (vn.uuid in vns)
