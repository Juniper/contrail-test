import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class FirewallRuleFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Firewall Rule object
    Optional:
    :param name : name of the firewall rule
    :param uuid : UUID of the firewall rule
    :param scope : global or local scope, default local
    :param service_groups : list of uuid of service groups
    :param action : pass or deny
    :param direction : <> or < or >
    :param protocol : protocol to filter (int or one of icmp/tcp/udp/any)
    :param sports : tuple of start,end port
    :param dports : tuple of start,end port
    :param log : to log flow to analytics (bool: default False)
    :param match : list of match tag-types ['deployment', 'site']
                   set to "dont" to not match on tag type
    :param source : dict for endpoint
    :param destination : dict for endpoint
    eg: endpoint dict with atleast one of the keys
        {'subnet': '1.1.1.0/24',
         'virtual_network': vn_fq_name,
         'any': False,
         'address_group': ag_fq_name,
         'tags': ['deployment=prod', 'global:site=us'],
         'firewall_group_id': 'abcd-efgh-ijkl'
        }
    '''
    def __init__(self, *args, **kwargs):
        super(FirewallRuleFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.direction = kwargs.get('direction') or '<>'
        self.protocol = kwargs.get('protocol')
        self.sports = kwargs.get('sports')
        self.dports = kwargs.get('dports')
        self.log = kwargs.get('log') or False
        self.match = kwargs.get('match') or ['deployment']
        self.source = kwargs.get('source') or {'any': True} #endpoint_1
        self.destination = kwargs.get('destination') or {'any': True} #endpoint_2
        self.scope = kwargs.get('scope') or 'local'
        self.service_groups = kwargs.get('service_groups') or list()
        self.api_type = kwargs.get('api_type', 'contrail')
        self.action = kwargs.get('action') or 'pass'
        self.enabled = kwargs.get('enabled', 'True')
        self.shared = kwargs.get('shared', 'False')
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(FirewallRuleFixture, self).setUp()
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
            self.logger.info('Skipping deletion of Firewall Rule %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(FirewallRuleFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_firewall_rule(id=self.uuid)

    def get_draft(self):
        return self.vnc_h.read_firewall_rule(id=self.uuid, draft=True)

    def read(self):
        obj = self.vnc_h.read_firewall_rule(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        self.scope = 'local' if obj.parent_type == 'project' else 'global'
        for sg in obj.get_service_group_refs() or []:
            self.service_groups.append(sg['uuid'])

    def create(self):
        if self.api_type == 'contrail':
            self.create_vnc_api()
        else:
            self.create_orch()
        if not self.created:
            self.read()

    def create_orch(self):
        if not self.uuid:
            # Add a check if the firewall rule already exists
            self.uuid = self.orch.create_fwr_rule(self.name,
                protocol=self.protocol,
                sport=list(self.sports)[0] if self.sports else None,
                dport=list(self.dports)[0] if self.dports else None,
                source=self.source,
                destination=self.destination,
                action=self.action,
                enabled=self.enabled,
                shared=self.shared)
            self.created = True
                 
    def create_vnc_api(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_firewall_rule(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_firewall_rule(
                                     parent_type=self.parent_type,
                                     fq_name=self.fq_name,
                                     action=self.action,
                                     direction=self.direction,
                                     protocol=self.protocol,
                                     sports=self.sports,
                                     dports=self.dports,
                                     log=self.log,
                                     match=self.match,
                                     source=self.source,
                                     destination=self.destination,
                                     service_groups=self.service_groups)
                self.created = True
                self.logger.info('Created Firewall Rule %s(%s)'%(self.name,
                                                                self.uuid))

    def add_service_groups(self, service_groups):
        self.vnc_h.add_service_group(self.uuid, service_groups)
        self.service_groups.extend(service_groups)

    def remove_service_groups(self, service_groups):
        self.vnc_h.remove_service_group(self.uuid, service_groups)
        self.service_groups = list(set(self.service_groups) - set(service_groups))

    def update(self, action=None, direction=None, protocol=None,
               sports=None, dports=None, log=None, source=None,
               destination=None, match=None, service_groups=None):
        self.vnc_h.update_firewall_rule(
                             uuid=self.uuid,
                             action=action,
                             direction=direction,
                             protocol=protocol,
                             sports=sports,
                             dports=dports,
                             log=log,
                             match=match,
                             source=source,
                             destination=destination,
                             service_groups=service_groups)
        if action:
            self.action = action
        if direction:
            self.direction = direction
        if protocol:
            self.protocol = protocol
        if sports:
            self.sports = sports
        if dports:
            self.dports = dports
        if log:
            self.log = log
        if source:
            self.source = source
        if destination:
            self.destination = destination
        if match:
            self.match = match
        if service_groups:
            self.service_groups = service_groups

    def delete(self):
        self.logger.info('Deleting Firewall Rule %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_firewall_rule(id=self.uuid)
        except NoIdError:
            pass
