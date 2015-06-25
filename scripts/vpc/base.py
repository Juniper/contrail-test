import test
from common import isolated_creds
from common import create_public_vn
from vn_test import *
from vm_test import *
import fixtures
from vpc_fixture_new import VPCFixture
from vpc_vn_fixture import VPCVNFixture
from vpc_vm_fixture import VPCVMFixture


class VpcBaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(VpcBaseTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.admin_inputs = cls.isolated_creds.get_admin_inputs()
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.public_vn_obj = create_public_vn.PublicVn(
             cls.admin_connections.username,
             cls.admin_connections.password,
             cls.inputs,
             ini_file=cls.ini_file,
             logger=cls.logger)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(VpcBaseTest, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        if not 'ubuntu' in self.inputs.os_type[self.inputs.cfgm_ip]:
            return (False, 'VPC cases are currently valid only on Ubuntu')
        return (True, None)

    def setUp(self):
        super(VpcBaseTest, self).setUp()

    def cleanUp(self):
        super(VpcBaseTest, self).cleanUp()

    def createAcl(self, vpc_fixture):
        acl_id = vpc_fixture.create_acl()
        if not acl_id:
            self.logger.warn('create_network_acl failed')
            return None
        return acl_id
    # end createAcl

    def verifyAclBinding(self, vpc_vn_fixture, acl_id):
        if not vpc_vn_fixture.verify_acl_binding(acl_id):
            self.logger.warn('verify_network_acl %s failed' % (acl_id))
            return False
        return True
    # end verifyAclBinding

    def associateAcl(self, vpc_fixture, subnet_id, defAcl=None):
        if not vpc_fixture.associate_acl(subnet_id, defAcl):
            self.logger.warn('verify_network_acl failed')
            return False
        return True
    # end associateAcl

    def createAclRule(self, vpc_fixture, acl_id, rule):
        if not vpc_fixture.create_acl_rule(acl_id, rule):
            self.logger.warn('add_acl_rule failed')
            return False
        return True
    # end createAclRule

    def replaceAclRule(self, vpc_fixture, acl_id, rule):
        if not vpc_fixture.replace_acl_rule(acl_id, rule):
            self.logger.warn('replace_acl_rule failed')
            return False
        return True
    # end replaceAclRule

    def deleteAclRule(self, vpc_fixture, acl_id, rule):
        if not vpc_fixture.delete_acl_rule(acl_id, rule):
            self.logger.warn('delete_acl_rule failed')
            return False
        return True
    # end deleteAclRule

    def createSecurityGroup(self, vpc_fixture, sg_name):
        sg_id = vpc_fixture.create_security_group(sg_name)
        if not sg_id:
            self.logger.warn('create_security_group of %s failed' % (sg_name))
            return None
        return sg_id
    # end createSecurityGroup

    def deleteSecurityGroup(self, vpc_fixture, sg_id):
        if not vpc_fixture.delete_security_group(sg_id):
            self.logger.warn('delete_security_group of %s failed' % (sg_id))
            return False
        return True
    # end deleteSecurityGroup

    def verifySecurityGroup(self, vpc_fixture, sg_name):
        if not vpc_fixture.verify_security_group(sg_name):
            self.logger.warn('verify_security_group of %s failed' % (sg_name))
            return False
        return True
    # end verifySecurityGroup

    def createSgRule(self, vpc_fixture, sg_id, rule):
        if not vpc_fixture.create_security_group_rule(sg_id, rule):
            self.logger.warn('create_security_group_rule failed for SG ID %s' %
                             (sg_id))
            return False
        return True
    # end createSgRule

    def deleteSgRule(self, vpc_fixture, sg_id, rule):
        if not vpc_fixture.delete_security_group_rule(sg_id, rule):
            self.logger.debug(
                'delete_security_group_rule failed for SG ID %s' % (sg_id))
            return False
        return True
    # end deleteSgRule

    def set_sec_group_for_allow_all(self, project_name, sg_name):
        def_sec_grp = self.vnc_lib.security_group_read(
            fq_name=[u'default-domain', project_name, sg_name])
        project_fq_name = [u'default-domain', project_name]
        sg_fq_name = [u'default-domain', project_name, sg_name]
        try:
            old_rules_list = def_sec_grp.get_security_group_entries(
            ).get_policy_rule()
        except AttributeError:
            old_rules_list = []
            pass
        self.logger.info(
            "Adding rules to the %s security group in Project %s" %
            (sg_name, project_name))
        project = self.vnc_lib.project_read(fq_name=project_fq_name)
        def_sec_grp = self.vnc_lib.security_group_read(fq_name=sg_fq_name)
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        rule1 = [{'direction': '>',
                  'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1
                  },
                 {'direction': '>',
                  'protocol': 'any',
                  'src_addresses': [{'security_group': 'local', 'subnet': None}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_2
                  },
                 ]
        rule_list = PolicyEntriesType(policy_rule=rule1)
        def_sec_grp = SecurityGroup(
            name=sg_name, parent_obj=project, security_group_entries=rule_list)
        def_sec_grp.set_security_group_entries(rule_list)
        self.vnc_lib.security_group_update(def_sec_grp)
        self.addCleanup(self.restore_sec_group, project_name,
                        sg_name, old_rules_list)
    # end set_sec_group_for_allow_all

    def restore_sec_group(self, project_name, sg_name, rules_list):
        self.logger.info("Restoring rules in SG %s in Project %s" %
                         (sg_name, project_name))
        project_fq_name = [u'default-domain', project_name]
        sg_fq_name = [u'default-domain', project_name, sg_name]
        project = self.vnc_lib.project_read(fq_name=project_fq_name)
        def_sec_grp = self.vnc_lib.security_group_read(fq_name=sg_fq_name)
        if (rules_list is None or (len(rules_list) == 0)):
            rules_list = []
        rules_list_obj = PolicyEntriesType(policy_rule=rules_list)
        def_sec_grp = SecurityGroup(
            name=sg_name,
            parent_obj=project,
            security_group_entries=rules_list_obj)
        def_sec_grp.set_security_group_entries(rules_list_obj)
        self.vnc_lib.security_group_update(def_sec_grp)
    # end restore_sec_group
