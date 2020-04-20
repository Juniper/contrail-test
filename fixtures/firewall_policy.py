import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry
from common.openstack_libs import neutron_exception

class FirewallPolicyFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Firewall Policy object
    Optional:
    :param name : name of the firewall policy
    :param uuid : UUID of the firewall policy
    :param scope : global or local scope, default local
    :param rules : list of firewall rule uuids and seq_no dict
    '''
    def __init__(self, *args, **kwargs):
        super(FirewallPolicyFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.scope = kwargs.get('scope') or 'local'
        self.rules = kwargs.get('rules') or list()
        self.slo = kwargs.get('slo')
        self.shared = kwargs.get('shared', False)
        self.audited = kwargs.get('audited', True)
        self.api_type = kwargs.get('api_type', 'contrail')
        self.created = False
        self.verify_is_run = False
        self.vnc_h = self.vnc_h if self.vnc_h else kwargs.get('vnc_h', None)
        if self.api_type == 'neutron':
            self.client_h = self.neutron_handle
            self.scope = 'local'
        else:
            self.client_h = self.vnc_h

    def setUp(self):
        super(FirewallPolicyFixture, self).setUp()
        self.name = self.name or get_random_name(self.project_name)
        if self.scope == 'local':
            self.parent_type = 'project'
            self.fq_name = [self.domain, self.project_name, self.name]
        else:
            self.parent_type = 'policy-management'
            self.fq_name = ['default-policy-management', self.name]
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Firewall Policy %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(FirewallPolicyFixture, self).cleanUp()

    def get_object(self):
        return self.client_h.read_firewall_policy(id=self.uuid)

    def get_draft(self):
        return self.vnc_h.read_firewall_policy(id=self.uuid, draft=True)

    def read(self):
        obj = self.vnc_h.read_firewall_policy(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        self.scope = 'local' if obj.parent_type == 'project' else 'global'
        self.rules = list()
        for rule in obj.get_firewall_rule_refs() or []:
            self.rules.append({'uuid': rule['uuid'], 'seq_no': rule['attr'].sequence})

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_firewall_policy(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.client_h.create_firewall_policy(
                                     parent_type=self.parent_type,
                                     fq_name=self.fq_name,
                                     slo=self.slo,
                                     name=self.name,
                                     rules=self.rules,
                                     shared=self.shared,
                                     audited=self.audited)
                self.created = True
                self.logger.info('Created Firewall Policy %s(%s)'%(self.name,
                                                                  self.uuid))
        if not self.created:
            self.read()

    def update(self, name=None, rules=None, shared=None, audited=None):
        self.client_h.update_firewall_policy(
                             name=name,
                             uuid=self.uuid,
                             rules=rules,
                             shared=shared,
                             audited=audited)
        if shared:
            self.shared = shared
        if audited:
            self.audited = audited
        if rules:
            self.rules = rules

    def add_firewall_rules(self, rules):
        self.client_h.add_firewall_rules(self.uuid, rules)
        self.rules.extend(rules)

    def remove_firewall_rules(self, rules):
        try:
            self.client_h.remove_firewall_rules(self.uuid, rules)
        except neutron_exception.BadRequest:
            pass
        uuids = set(rule['uuid'] for rule in rules)
        self.rules = [rule for rule in self.rules if rule['uuid'] not in uuids]

    def insert_firewall_rule(self, rule_uuid, insert_after=None,
                             insert_before=None):
        # if both insert_after and insert_before are specified
        # insert_before takes precedence
        self.neutron_handle.add_firewall_rule(self.uuid, rule_uuid,
            insert_after=insert_after, insert_before=insert_before)

    def delete(self):
        self.logger.info('Deleting Firewall Policy %s(%s)'%(self.name, self.uuid))
        try:
            self.client_h.delete_firewall_policy(id=self.uuid)
        except NoIdError:
            pass
