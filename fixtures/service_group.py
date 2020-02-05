import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class ServiceGroupFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle service group object
    Optional:
    :param name : name of the service group
    :param uuid : UUID of the service group
    :param scope : global or local scope, default local
    :param services : list of services tuples
     eg: [(<protocol>, (<sp_start, sp_end>), (<dp_start, dp_end>))]
    '''
    def __init__(self, *args, **kwargs):
        super(ServiceGroupFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name')
        self.uuid = kwargs.get('uuid')
        self.scope = kwargs.get('scope') or 'local'
        self.services = kwargs.get('services') or list()
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(ServiceGroupFixture, self).setUp()
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
            self.logger.info('Skipping deletion of service group %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(ServiceGroupFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_service_group(id=self.uuid)

    def get_draft(self):
        return self.vnc_h.read_service_group(id=self.uuid, draft=True)

    def read(self):
        obj = self.vnc_h.read_service_group(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        self.scope = 'local' if obj.parent_type == 'project' else 'global'
        self.services = list()
        for service in obj.get_service_group_firewall_service_list() or []:
            proto = service.protocol
            sports = (service.src_ports.start_port, service.src_ports.end_port)
            dports = (service.dst_ports.start_port, service.dst_ports.end_port)
            self.services.append((protocol, sports, dports))

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_service_group(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_service_group(
                                     fq_name=self.fq_name,
                                     parent_type=self.parent_type,
                                     services=self.services)
                self.created = True
                self.logger.info('Created Service Group %s(%s)'%(self.name,
                                                                self.uuid))
        if not self.created:
            self.read()

    def add_services(self, services):
        self.vnc_h.update_service_group(self.uuid, services)
        self.services.extend(services)

    def delete_services(self, services):
        self.vnc_h.update_service_group(self.uuid, services, delete=True)
        self.services = list(set(self.services) - set(services))

    def delete(self):
        self.logger.info('Deleting Service Group %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_service_group(id=self.uuid)
        except NoIdError:
            pass
