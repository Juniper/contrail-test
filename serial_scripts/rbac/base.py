from rbac_test import RbacFixture
from vn_test import VNFixture
from vm_test import VMFixture
from port_fixture import PortFixture
from security_group import SecurityGroupFixture
from svc_template_fixture import SvcTemplateFixture
from project_test import ProjectFixture
from floating_ip import FloatingIPFixture
from lbaasv2_fixture import LBaasV2Fixture
from common.servicechain.firewall.verify import VerifySvcFirewall
from tcutils.util import get_random_name
from cfgm_common.exceptions import PermissionDenied
from common.openstack_libs import neutron_forbidden
from vnc_api.vnc_api import VirtualNetworkType
import test_v1
import os

class BaseRbac(test_v1.BaseTestCase_v1):
    @classmethod
    def setUpClass(cls):
        super(BaseRbac, cls).setUpClass()
        cls.rbac_for_analytics = False
        if cls.inputs.get_analytics_aaa_mode() == 'rbac':
            cls.rbac_for_analytics = True
        try:
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
            if os.getenv('RBAC_USER3') and os.getenv('RBAC_PASS3'):
                cls.user3 = os.getenv('RBAC_USER3')
                cls.pass3 = os.getenv('RBAC_PASS3')
            else:
                cls.pass3 = cls.user3 = get_random_name(cls.__name__)
                cls.admin_connections.auth.create_user(cls.user3, cls.pass3)
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
            if os.getenv('RBAC_ROLE3'):
                cls.role3 = os.getenv('RBAC_ROLE3')
            else:
                cls.role3 = get_random_name(cls.__name__)
                cls.admin_connections.auth.create_role(cls.role3)
            cls.project_fixture = ProjectFixture(connections=cls.admin_connections,
                                                 project_name=cls.inputs.project_name,
                                                 domain_name=cls.inputs.domain_name)
            cls.populate_default_rules_in_global_acl()
        except:
            cls.tearDownClass()
            raise

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
                             {'rule_object': 'project',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'network-ipam',
                              'rule_field': None,
                              'perms': [{'role': '*', 'crud': 'R'}]
                             },
                             {'rule_object': 'routing-instance',
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
        cls.cleanUpObjects()
        super(BaseRbac, cls).tearDownClass()

    @classmethod
    def cleanUpObjects(cls):
        if not os.getenv('RBAC_USER1'):
            cls.admin_connections.auth.delete_user(cls.user1)
        if not os.getenv('RBAC_USER2'):
            cls.admin_connections.auth.delete_user(cls.user2)
        if not os.getenv('RBAC_USER3'):
            cls.admin_connections.auth.delete_user(cls.user3)
        if not os.getenv('RBAC_ROLE1'):
            cls.admin_connections.auth.delete_role(cls.role1)
        if not os.getenv('RBAC_ROLE2'):
            cls.admin_connections.auth.delete_role(cls.role2)
        if not os.getenv('RBAC_ROLE3'):
            cls.admin_connections.auth.delete_role(cls.role3)
        if getattr(cls, 'global_acl', None):
            cls.global_acl.delete_rules(cls.default_rules)

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

    def set_owner(self, obj=None, project=None, connections=None):
        connections = connections or self.connections
        project_id = project.uuid
        vnc_h = connections.orch.vnc_h
        vnc_h.set_owner(obj=obj, tenant=project_id)

    def delete_vn(self, vn_fix, connections=None):
        connections = connections or self.connections
        status = connections.orch.delete_vn(vn_fix.obj)
        if status:
            self.remove_from_cleanups(vn_fix)
        return status

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
                                         image_name='cirros')
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
            st_name=get_random_name(connections.project_name),
            svc_img_name='tiny_nat_fw',
            service_type='firewall',
            if_details={'management': {}, 'left': {}, 'right': {}},
            service_mode='in-network-nat',
            svc_scaling=False)
        if st_fixture and verify:
            assert st_fixture.verify_on_setup(), 'ST verification failed'
        return st_fixture

    def create_sc(self, connections=None, st_version=1, **kwargs):
        connections = connections or self.connections
        svc = self.create_fixture(VerifySvcFirewall,
                                  connections=connections,
                                  use_vnc_api=True, **kwargs)
        if svc:
            assert svc.verify_svc_chain(service_mode='in-network',
                                        svc_img_name='tiny_in_net',
                                        create_svms=True)
        return svc

    def create_lbaas(self, lb_name, network_id, connections=None, verify=True, **kwargs):
        connections = connections or self.connections
        lbaas_fixture = self.create_fixture(LBaasV2Fixture,
                        connections=connections,
                        lb_name=lb_name,
                        network_id=network_id,
                        **kwargs)
        if lbaas_fixture and verify:
            assert lbaas_fixture.verify_lb_in_api_server(), 'LB verificaiton failed'
            lb_fixture = LBaasV2Fixture(connections=self.connections,
                                        lb_uuid=lbaas_fixture.lb_uuid,
                                        listener_uuid=lbaas_fixture.listener_uuid)
            lb_fixture.lb_read()
            lb_fixture.read()
            assert lb_fixture.verify_on_setup(), 'LB verification failed'
        return lbaas_fixture

    def create_sg(self, connections=None, verify=True, option='orch', **kwargs):
        connections = connections or self.connections
        sg = self.create_fixture(SecurityGroupFixture,
                                 connections=connections,
                                 option=option, **kwargs)
        if sg and verify:
            assert sg.verify_on_setup()
        rules = [
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'security_group': 'local'}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        sg.create_sg_rule(sg.uuid, rules)
        return sg

    def associate_sg(self, sg_fixture, vm_fixture, verify=True):
        vm_fixture.add_security_group(sg_fixture.uuid)
        if verify:
            result, msg = vm_fixture.verify_security_group(sg_fixture.secgrp_name)
            assert result, msg

    def create_fip_pool(self, vn_fixture, connections=None, verify=True):
        connections = connections or self.connections
        fip_pool = self.create_fixture(FloatingIPFixture,
                   connections=connections,
                   vn_id=vn_fixture.uuid)
        if fip_pool and verify:
            assert fip_pool.verify_on_setup(), 'FIP Pool verification failed'
        return fip_pool

    def create_fip(self, fip_pool, connections=None, vm_fixture=None,
                   pub_vn_fixture=None, option='contrail', verify=True):
        connections = connections or self.connections
        vnc_h = connections.orch.vnc_h
        vnc_lib_h = connections.vnc_lib_fixture
        if option == 'contrail':
            try:
                project_obj = vnc_lib_h.get_project_obj()
                (fip, fip_id) = vnc_h.create_floating_ip(
                                pool_obj=fip_pool.fip_pool_obj,
                                project_obj=project_obj,
                                owner=project_obj.uuid)
                self.addCleanup(vnc_h.delete_floating_ip, fip_id)
                if vm_fixture:
                    vnc_h.assoc_floating_ip(fip_id=fip_id, vm_id=vm_fixture.uuid)
            except PermissionDenied:
                return (None, None)
        else:
            try:
                (fip, fip_id) = fip_pool.create_floatingip(fip_pool.get_vn_id())
                self.addCleanup(fip_pool.disassoc_and_delete_fip, fip_id)
                if vm_fixture:
                    self.assoc_floatingip(fip_id=fip_id, vm_id=vm_fixture.uuid)
            except PermissionDenied:
                return (None, None)
        if verify and vm_fixture and pub_vn_fixture:
            assert fip_pool.verify_fip(fip_id, vm_fixture, pub_vn_fixture)
        return (fip, fip_id)

    def create_fixture(self, fixturecls, **kwargs):
        try:
            return self.useFixture(fixturecls(**kwargs))
        except (PermissionDenied, neutron_forbidden):
            return None

    def read_fip_pool(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_fip_pool(uuid)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('API Server: Read FIP Pool %s'%uuid)
        else:
            self.logger.info('API Server: Permission Denied to read FIP Pool %s'%uuid)
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
            self.logger.info('API Server: Read VN %s'%uuid)
        else:
            self.logger.info('API Server: Permission Denied to read VN %s'%uuid)
        return obj

    def read_vmi(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_vmi_by_id(uuid, refresh=True)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('API Server: Read VMI %s'%uuid)
        else:
            self.logger.info('API Server: Permission Denied to read VMI %s'%uuid)
        return obj

    def read_st(self, connections, uuid):
        try:
            obj = connections.api_server_inspect.get_cs_st_by_id(uuid, refresh=True)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('API Server: Read Service-Template %s'%uuid)
        else:
            self.logger.info('API Server: Permission Denied to read ST %s'%uuid)
        return obj

    def update_vn(self, connections=None, uuid=None, prop_kv=None, obj=None):
        vnc_h = connections.orch.vnc_h
        if not obj:
            obj = vnc_h.virtual_network_read(id=uuid)
        for k,v in prop_kv.iteritems():
            if '.' in k: #SubField Match
                field = k.split('.')[0]
                subfield = k.split('.')[1]
                prop = eval('obj.get_'+field)() or VirtualNetworkType() #ToDo
                setattr(prop, subfield, v)
                eval('obj.set_'+field)(prop)
            else:
                setattr(obj, k, v)
        try:
            vnc_h.virtual_network_update(obj)
            self.logger.info('Updated VN %s'%uuid)
            return True
        except PermissionDenied:
            self.logger.info('Permission Denied to update VN %s, kv %s'%(uuid, prop_kv))
        return False

    def list_vn(self, connections=None, option='contrail'):
        connections = connections or self.connections
        vn_ids = list()
        try:
            if option == 'contrail':
                vn_ids = connections.api_server_inspect.get_cs_vn_list()
            else:
                vns = connections.orch.list_networks()
                for vn in vns or []:
                    vn_ids.append(vn['id'])
            self.logger.info('API Server: List VN %s'%vn_ids)
        except PermissionDenied:
            self.logger.info('API Server: Permission Denied to list VN')
        return vn_ids

    def list_fip_pool(self, connections=None):
        connections = connections or self.connections
        pool_ids = list()
        try:
            pool_ids = connections.api_server_inspect.get_cs_fip_pool_list()
            self.logger.info('API Server: List FIP Pool %s'%pool_ids)
        except PermissionDenied:
            self.logger.info('API Server: Permission Denied to read FIP Pool')
        return pool_ids

    def list_analytics_nodes_from_analytics(self, connections):
        return connections.ops_inspect.get_hrefs_to_all_UVEs_of_a_given_UVE_type(
               uveType='analytics-nodes')

    def list_vn_from_analytics(self, connections):
        vns = connections.ops_inspect.get_hrefs_to_all_UVEs_of_a_given_UVE_type(
               uveType='virtual-networks') or []
        return [vn['name'] for vn in vns]

    def get_vn_from_analytics(self, connections, fq_name_str):
        return connections.analytics_obj.get_vn_uve(fq_name_str)

    def get_vmi_from_analytics(self, connections, fq_name_str):
        return connections.ops_inspect.get_ops_vm_intf(fq_name_str)

    def remove_from_cleanups(self, fixture):
        for cleanup in self._cleanups:
            if fixture.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
