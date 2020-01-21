import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class ApplicationPolicySetFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle address group object
    Optional:
    :param name : name of the address group
    :param uuid : UUID of the address group
    :param scope : global or local scope, default local
    :param policies : list of dict of firewall policy uuids and seq no
     eg: [{'uuid': uuid, 'seq_no': <int>}]
    '''
    def __init__(self, *args, **kwargs):
        super(ApplicationPolicySetFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.scope = kwargs.get('scope') or 'local'
        self.policies = kwargs.get('policies') or list()
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(ApplicationPolicySetFixture, self).setUp()
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
            self.logger.info('Skipping deletion of address group %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(ApplicationPolicySetFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_application_policy_set(id=self.uuid)

    def get_draft(self):
        return self.vnc_h.read_application_policy_set(id=self.uuid, draft=True)

    def read(self):
        obj = self.vnc_h.read_application_policy_set(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        self.scope = 'local' if obj.parent_type == 'project' else 'global'
        self.policies = [{'uuid': policy['uuid'], 'seq_no': policy['sequence']}
                         for policy in obj.get_firewall_policy_refs() or []]

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_application_policy_set(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_application_policy_set(
                                     fq_name=self.fq_name,
                                     parent_type=self.parent_type,
                                     policies=self.policies)
                self.created = True
                self.logger.info('Created APS %s(%s)'%(self.name,
                                                       self.uuid))
        if not self.created:
            self.read()

    def add_policies(self, policies):
        self.vnc_h.add_firewall_policies(self.uuid, policies)
        self.policies.extend(policies)

    def delete_policies(self, policies):
        self.vnc_h.remove_firewall_policies(self.uuid, policies)
        uuids = set(policy['uuid'] for policy in policies)
        self.policies = [policy for policy in self.policies if policy['uuid'] not in uuids]

    def delete(self):
        self.logger.info('Deleting Application Policy Set %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_application_policy_set(id=self.uuid)
        except NoIdError:
            pass

    def add_tag(self, application):
        is_global = False if getattr(application, 'parent_type', None) == 'project' else True
        self.vnc_h.set_tag('application', application.tag_value,
                           is_global, None, 'application-policy-set', self.uuid)

    def delete_tag(self, application):
        is_global = False if getattr(application, 'parent_type', None) == 'project' else True
        self.vnc_h.unset_tag('application', None, 'application-policy-set', self.uuid)
