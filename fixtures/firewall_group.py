import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class FirewallGroupFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Firewall Group object
    Optional:
    :param name : name of the firewall group
    :param uuid : UUID of the firewall group
    :param scope : global or local scope, default local
    :param rules : list of firewall rule uuids and seq_no dict
    '''
    def __init__(self, *args, **kwargs):
        super(FirewallGroupFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.scope = kwargs.get('scope') or 'local'
        self.rules = kwargs.get('rules') or list()
        self.slo = kwargs.get('slo') or None
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(FirewallGroupFixture, self).setUp()
        self.name = self.name or get_random_name(self.project_name)
        if self.scope == 'local':
            self.parent_type = 'project'
            self.fq_name = [self.domain, self.project_name, self.name]
        else:
            self.parent_type = 'group-management'
            self.fq_name = ['default-group-management', self.name]
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Firewall Group %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(FirewallGroupFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_firewall_group(id=self.uuid)

    def get_draft(self):
        return self.vnc_h.read_firewall_group(id=self.uuid, draft=True)

    def read(self):
        obj = self.vnc_h.read_firewall_group(id=self.uuid)
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
                obj = self.vnc_h.read_firewall_group(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_firewall_group(
                                     parent_type=self.parent_type,
                                     fq_name=self.fq_name,
                                     rules=self.rules, slo=self.slo)
                self.created = True
                self.logger.info('Created Firewall Group %s(%s)'%(self.name,
                                                                  self.uuid))
        if not self.created:
            self.read()

    def add_firewall_rules(self, rules):
        self.vnc_h.add_firewall_rules(self.uuid, rules)
        self.rules.extend(rules)

    def remove_firewall_rules(self, rules):
        self.vnc_h.remove_firewall_rules(self.uuid, rules)
        uuids = set(rule['uuid'] for rule in rules)
        self.rules = [rule for rule in self.rules if rule['uuid'] not in uuids]

    def delete(self):
        self.logger.info('Deleting Firewall Group %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_firewall_group(id=self.uuid)
        except NoIdError:
            pass
