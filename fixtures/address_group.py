import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry
from netaddr import IPNetwork

class AddressGroupFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle address group object
    Optional:
    :param name : name of the address group
    :param uuid : UUID of the address group
    :param scope : global or local scope, default local
    :param subnets : list of subnets in cidr format
    '''
    def __init__(self, *args, **kwargs):
        super(AddressGroupFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.scope = kwargs.get('scope') or 'local'
        self.subnets = kwargs.get('subnets') or list()
        self.created = False
        self.verify_is_run = False

    @property
    def fq_name_str(self):
        return ':'.join(self.fq_name)

    def setUp(self):
        super(AddressGroupFixture, self).setUp()
        self.name = self.name or get_random_name(self.project_name)
        if self.scope == 'local':
            self.parent_type = 'project'
            self.fq_name = [self.domain, self.project_name, self.name]
        else:
            self.parent_type = 'policy-management'
            self.fq_name = ['default-policy-management', self.name]
        self.create()

    def cleanUp(self):
        super(AddressGroupFixture, self).cleanUp()
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of address group %s:'
                              %(self.fq_name))
        else:
            return self.delete()

    def read(self):
        obj = self.vnc_h.read_address_group(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        self.scope = 'local' if obj.parent_type == 'project' else 'global'
        self.subnets = ["%s/%s"%(subnet.ip_prefix, subnet.ip_prefix_len)
                         for subnet in obj.get_address_group_prefix()]

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_address_group(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_address_group(
                                     fq_name=self.fq_name,
                                     parent_type=self.parent_type,
                                     subnets=self.subnets)
                self.created = True
        if not self.created:
            self.read()

    def add_subnets(self, subnets):
        subnets = [str(IPNetwork(subnet)) for subnet in subnets]
        self.vnc_h.update_address_group(self.uuid, subnets)
        self.subnets.extend(subnets)

    def delete_subnets(self, subnets):
        subnets = [str(IPNetwork(subnet)) for subnet in subnets]
        self.vnc_h.update_address_group(self.uuid, subnets, delete=True)
        self.subnets = list(set(self.subnets) - set(subnets))

    def delete(self):
        self.logger.info('Deleting Address Group %s(%s)'%(self.name, self.uuid))
        self.vnc_h.delete_address_group(id=self.uuid)

    def add_labels(self, tags, is_global=False):
        if type(tags[0]) is not str:
            is_global = False if getattr(tags[0], 'parent_type', None) == 'project' else True
            tags = [tag.tag_value for tag in tags]
        self.vnc_h.add_labels(tags, is_global, None, 'address-group', self.uuid)

    def delete_labels(self, tags, is_global=False):
        if type(tags[0]) is not str:
            is_global = False if getattr(tags[0], 'parent_type', None) == 'project' else True
            tags = [tag.tag_value for tag in tags]
        self.vnc_h.delete_labels(tags, is_global, None, 'address-group', self.uuid)
