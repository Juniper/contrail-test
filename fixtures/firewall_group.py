import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class FirewallGroupFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Firewall Group object
    Optional:
    :param name : name of the firewall group
    :param uuid : UUID of the firewall group
    :param ports : list of virtual machine interface UUIDs
    :param ingress_policy_id : Firewall policy UUID
    :param egress_policy_id : Firewall policy UUID
    :param shared : True or False
    :param admin_state: True or False
    '''
    def __init__(self, **kwargs):
        super(FirewallGroupFixture, self).__init__(**kwargs)
        self.name = kwargs.get('name') or get_random_name(self.project_name)
        self.uuid = kwargs.get('uuid')
        self.ports = kwargs.get('ports') or list()
        self.ingress_policy_id = kwargs.get('ingress_policy_id')
        self.egress_policy_id = kwargs.get('egress_policy_id')
        self.shared = kwargs.get('shared')
        self.admin_state = kwargs.get('admin_state')
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(FirewallGroupFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Firewall Group %s:'
                              %(self.name))
        else:
            self.delete()
        super(FirewallGroupFixture, self).cleanUp()

    def get_object(self):
        return self.neutron_handle.read_firewall_group(id=self.uuid)

    def read(self):
        obj = self.neutron_handle.read_firewall_group(id=self.uuid)
        self.name = obj['name']
        self.ports = obj['ports']
        self.shared = obj['shared']
        self.admin_state = obj['admin_state_up']
        self.ingress_policy_id = obj['ingress_firewall_policy_id']
        self.egress_policy_id = obj['egress_firewall_policy_id']

    def verify_on_setup(self):
        assert self.get_aps()
        assert self.get_tag()

    def get_aps(self):
        return self.vnc_h.read_application_policy_set(id=self.uuid)

    def get_tag(self):
        fq_name = [self.domain, self.project_name, 'neutron_fwaas=%s'%self.uuid]
        return self.vnc_h.read_tag(fq_name=fq_name,
                                   fields='virtual_machine_interface_back_refs')

    @retry(tries=24, delay=5)
    def is_port_refs_in_tag(self):
        tag_obj = self.get_tag()
        vmis = tag_obj.get_virtual_machine_interface_back_refs()
        if vmis:
            self.logger.warn('Firewall Group %s still has refs to vmis %s'%(
                              self.uuid, [d['uuid'] for d in vmis]))
            return False
        return True

    def create(self):
        if not self.uuid:
            for group in self.neutron_handle.list_firewall_groups():
                if group['name'] == self.name and \
                   self.project_id.replace('-','') == group['project_id']:
                    self.uuid = group['id']
                    break
            else:
                self.uuid = self.neutron_handle.create_firewall_group(
                    name=self.name,
                    ports=self.ports,
                    admin_state=self.admin_state,
                    shared=self.shared,
                    ingress_policy_id=self.ingress_policy_id,
                    egress_policy_id=self.egress_policy_id)
                self.created = True
                self.logger.info('Created Firewall Group %s(%s)'%(self.name,
                                                                  self.uuid))
        if not self.created:
            self.read()

    def update(self, shared=None, admin_state=None, **kwargs):
        self.neutron_handle.update_firewall_group(
            uuid=self.uuid,
            ports=kwargs.get('ports', self.ports),
            shared=shared,
            admin_state=admin_state,
            ingress_policy_id=kwargs.get('ingress_policy_id',
                                         self.ingress_policy_id),
            egress_policy_id=kwargs.get('egress_policy_id',
                                        self.egress_policy_id))
        if shared:
            self.shared = shared
        if admin_state:
            self.admin_state = admin_state
        if 'ports' in kwargs:
            self.ports = kwargs['ports']
        if 'ingress_policy_id' in kwargs:
            self.ingress_policy_id = kwargs['ingress_policy_id']
        if 'egress_policy_id' in kwargs:
            self.egress_policy_id = kwargs['egress_policy_id']

    def add_ports(self, ports):
        self.update(ports=self.ports + ports)
        self.ports.extend(ports)

    def delete_ports(self, ports):
        self.update(ports=list(set(self.ports) - set(ports)))
        self.ports = list(set(self.ports) - set(ports))

    def delete(self):
        self.update(ports=list())
        assert self.is_port_refs_in_tag()
        self.logger.info('Deleting Firewall Group %s(%s)'%(self.name, self.uuid))
        self.neutron_handle.delete_firewall_group(id=self.uuid)
