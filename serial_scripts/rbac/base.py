from rbac_test import RbacFixture
from vn_test import VNFixture
from vm_test import VMFixture
from port_fixture import PortFixture
from svc_template_fixture import SvcTemplateFixture
from project_test import ProjectFixture
from floating_ip import FloatingIPFixture
from lbaasv2_fixture import LBaasV2Fixture
from common.servicechain.firewall.verify import VerifySvcFirewall
from tcutils.util import get_random_name
from cfgm_common.exceptions import PermissionDenied
import test_v1
import os

class BaseRbac(test_v1.BaseTestCase_v1):
    @classmethod
    def setUpClass(cls):
        super(BaseRbac, cls).setUpClass()
        if os.getenv('RBAC_USER1') and os.getenv('RBAC_PASS1'):
            cls.user1 = os.getenv('RBAC_USER1')
            cls.pass1 = os.getenv('RBAC_PASS1')
        else:
            cls.pass1 = cls.user1 = get_random_name(cls.__name__)
            cls.admin_connections.auth.create_user(cls.user1, cls.pass1)
        if os.getenv('RBAC_USER2') and os.getenv('RBAC_PASS2'):
            cls.user2 = os.getenv('RBAC_USER2')
            cls.pass2 = os.getenv('RBAC_PASS2')
        else:
            cls.pass2 = cls.user2 = get_random_name(cls.__name__)
            cls.admin_connections.auth.create_user(cls.user2, cls.pass2)
        if os.getenv('RBAC_ROLE1'):
            cls.role1 = os.getenv('RBAC_ROLE1')
        else:
            cls.role1 = get_random_name(cls.__name__)
            cls.admin_connections.auth.create_role(cls.role1)
        if os.getenv('RBAC_ROLE2'):
            cls.role2 = os.getenv('RBAC_ROLE2')
        else:
            cls.role2 = get_random_name(cls.__name__)
            cls.admin_connections.auth.create_role(cls.role2)
        cls.project_fixture = ProjectFixture(connections=cls.admin_connections,
                                             project_name=cls.inputs.project_name,
                                             domain_name=cls.inputs.domain_name)
        cls.populate_default_rules_in_global_acl()

    def is_test_applicable(self):
        if self.get_aaa_mode() != 'rbac':
            return (False, 'RBAC is not enabled')
        return (True, None)

    def get_aaa_mode(self):
        return self.admin_connections.api_server_inspect.get_aaa_mode()

    def set_aaa_mode(self, aaa_mode):
        for cfgm_ip in self.inputs.cfgm_ips:
            inspect_h = self.connections.api_server_inspects[cfgm_ip]
            inspect_h.set_aaa_mode(aaa_mode)

    @classmethod
    def populate_default_rules_in_global_acl(cls):
        cls.default_rules = [{'rule_object': 'ref-update',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'CRUD'}]
                             },
                             {'rule_object': 'projects',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'project',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'domains',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'network-ipam',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'routing-instances',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'domain',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             }]
        cls.global_acl = RbacFixture(connections=cls.connections,
                                     parent_fqname='default-global-system-config',
                                     parent_type='global-system-config')
        cls.global_acl.setUp()
        cls.global_acl.add_rules(cls.default_rules)

    @classmethod
    def tearDownClass(cls):
        if not os.getenv('RBAC_USER1'):
            cls.admin_connections.auth.delete_user(cls.user1)
        if not os.getenv('RBAC_USER2'):
            cls.admin_connections.auth.delete_user(cls.user2)
        if not os.getenv('RBAC_ROLE1'):
            cls.admin_connections.auth.delete_role(cls.role1)
        if not os.getenv('RBAC_ROLE2'):
            cls.admin_connections.auth.delete_role(cls.role2)
        cls.global_acl.delete_rules(cls.default_rules)
        super(BaseRbac, cls).tearDownClass()

    def add_user_to_project(self, username, role, project_name=None):
        if not project_name:
            project_name = self.inputs.project_name
        auth = self.admin_connections.auth
        auth.add_user_to_project(username, project_name, role)
        self.addCleanup(auth.remove_user_from_project,
                        username, role, project_name)

    def get_connections(self, username, password, project_fixture=None):
        if not project_fixture:
            project_fixture = self.project_fixture
        return project_fixture.get_project_connections(username=username, password=password)

    def create_project(self):
        project_name = get_random_name(self.__class__.__name__)
        project_fixture = self.create_fixture(ProjectFixture,
                          connections=self.admin_connections,
                          project_name=project_name)
        return project_fixture

    def create_rbac_acl(self, connections=None, rules=None,
                        parent_type=None, parent_fqname=None, verify=True):
        connections = connections or self.connections
        parent_type = parent_type or 'project'
        if not parent_fqname:
            if parent_type == 'project':
                parent_fqname = '%s:%s'%(self.inputs.domain_name,
                                         self.inputs.project_name)
            elif parent_type == 'domain':
                parent_fqname = self.inputs.domain_name
            else:
                parent_fqname = 'default-global-system-config'
        rbac_fixture = self.create_fixture(RbacFixture, connections=connections,
                                           parent_type=parent_type, rules=rules,
                                           parent_fqname=parent_fqname)
        assert rbac_fixture, 'RBAC ACL creation failed'
        if verify:
            assert rbac_fixture.verify_on_setup(), 'Rbac verification failed'
        return rbac_fixture

    def share_obj(self, obj=None, project=None, perms=7, connections=None):
        connections = connections or self.connections
        project_id = project.uuid
        vnc_h = connections.orch.vnc_h
        vnc_h.set_share_tenants(obj=obj, tenant=project_id, tenant_access=perms)

    def create_vn(self, connections=None, verify=True, option='contrail', **kwargs):
        connections = connections or self.connections
        vn_fixture = self.create_fixture(VNFixture, connections=connections,
                                         option=option, **kwargs)
        if vn_fixture and verify:
            #WA of verifying using admin creds since RI etal system objects
            #wont be visible to the regular user
            vn_admin_fixture = VNFixture(connections=self.connections,
                                         option=option, uuid=vn_fixture.uuid)
            vn_admin_fixture.read()
            assert vn_admin_fixture.verify_on_setup(), 'VN verification failed'
        return vn_fixture

    def create_vm(self, vn_fixture, connections=None, verify=True):
        connections = connections or self.connections
        vm_fixture = self.create_fixture(VMFixture, connections=connections,
                                         vn_obj=vn_fixture.obj,
                                         image_name='cirros-0.3.0-x86_64-uec')
        if vm_fixture and verify:
            assert vm_fixture.verify_on_setup(), 'VM verification failed'
        return vm_fixture

    def create_vmi(self, vn_fixture, connections=None, verify=True):
        connections = connections or self.connections
        try:
            vmi_fixture = self.useFixture(PortFixture(vn_fixture.uuid,
                                          connections=connections))
        except PermissionDenied:
            return None
        if vmi_fixture and verify:
            assert vmi_fixture.verify_on_setup(), 'VMI verification failed'
        return vmi_fixture

    def create_st(self, connections=None, verify=True):
        connections = connections or self.connections
        st_fixture = self.create_fixture(SvcTemplateFixture,
            connections=connections,
            inputs=connections.inputs,
            domain_name=connections.domain_name,
            st_name=get_random_name(connections.project_name),
            svc_img_name='tiny_nat_fw',
            svc_type='firewall',
            if_list=[['management', False, False],
                     ['left', False, False],
                     ['right', False, False]],
            svc_mode='in-network-nat',
            svc_scaling=False,
            ordered_interfaces=True)
        if st_fixture and verify:
            assert st_fixture.verify_on_setup(), 'ST verification failed'
        return st_fixture

    def create_sc(self, connections=None, st_version=1, **kwargs):
        connections = connections or self.connections
        svc = self.create_fixture(VerifySvcFirewall,
                                  connections=connections,
                                  use_vnc_api=True, **kwargs)
        if svc:
            assert svc.verify_svc_in_network_datapath(svc_mode='in-network',
                                                      st_version=st_version,
                                                      ci=True)
        return svc

    def create_lbaas(self, lb_name, network_id, connections=None, verify=True, **kwargs):
        connections = connections or self.connections
        lbaas_fixture = self.create_fixture(LBaasV2Fixture,
                        connections=connections,
                        lb_name=lb_name,
                        network_id=network_id,
                        **kwargs)
        if lbaas_fixture and verify:
            assert lbaas_fixture.verify_on_setup(), 'LB verification failed'
        return lbaas_fixture

    def create_fip_pool(self, vn_fixture, connections=None, verify=True):
        connections = connections or self.connections
        fip_pool = self.create_fixture(FloatingIPFixture,
                   connections=connections,
                   vn_id=vn_fixture.uuid)
        if fip_pool and verify:
            assert fip_pool.verify_on_setup(), 'FIP Pool verification failed'
        return fip_pool

    def create_fip(self, fip_pool, connections=None, vm_fixture=None):
        connections = connections or self.connections
        vnc_h = connections.orch.vnc_h
        vnc_lib_h = connections.vnc_lib_fixture
        try:
            (fip, fip_id) = vnc_h.create_floating_ip(
                            pool_obj=fip_pool.fip_pool_obj,
                            project_obj=vnc_lib_h.get_project_obj())
            self.addCleanup(vnc_h.delete_floating_ip, fip_id)
        except PermissionDenied:
            return (None, None)
        if vm_fixture:
            vnc_h.assoc_floating_ip(fip_id=fip_id, vm_id=vm_fixture.uuid)
        return (fip, fip_id)

    def create_fixture(self, fixturecls, **kwargs):
        try:
            return self.useFixture(fixturecls(**kwargs))
        except PermissionDenied:
            return None

    def read_fip_pool(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_fip_pool(uuid)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('Read FIP Pool %s'%uuid)
        else:
            self.logger.info('Permission Denied to read FIP Pool %s'%uuid)
        return obj

    def read_vn(self, connections, uuid, option='contrail'):
        try:
            if option == 'contrail':
                obj = connections.api_server_inspect.get_cs_vn_by_id(uuid, refresh=True)
            else:
                obj = connections.orch.get_vn_obj_from_id(uuid)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('Read VN %s'%uuid)
        else:
            self.logger.info('Permission Denied to read VN %s'%uuid)
        return obj

    def update_vn(self, connections, uuid, prop_kv):
        vnc_h = connections.orch.vnc_h
        vn_obj = vnc_h.virtual_network_read(id=uuid)
        for k,v in prop_kv.iteritems():
            setattr(vn_obj, k, v)
        try:
            vnc_h.virtual_network_update(vn_obj)
            self.logger.info('Updated VN %s'%uuid)
            return True
        except PermissionDenied:
            self.logger.info('Permission Denied to update VN %s, kv %s'%(uuid, prop_kv))
        return False

    def read_vmi(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_vmi_by_id(uuid, refresh=True)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('Read VMI %s'%uuid)
        else:
            self.logger.info('Permission Denied to read VMI %s'%uuid)
        return obj

    def read_st(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_st_by_id(uuid, refresh=True)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('Read Service-Template %s'%uuid)
        else:
            self.logger.info('Permission Denied to read ST %s'%uuid)
        return obj

    def remove_from_cleanups(self, fixture):
        for cleanup in self._cleanups:
            if fixture.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
