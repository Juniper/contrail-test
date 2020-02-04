import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class PortProfileFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle port profile object
    Optional:
    :param name : name of the port profile
    :param uuid : UUID of the port profile
    :param action : one of 'shutdown'
    :param recovery_timeout : timeout in seconds to recover the interface from shutdown state
    :param bandwidth : value in int, when to raise the alarm (1-100)
    :param no_unicast : 
    :param no_multicast : 
    :param no_unknown_unicast : 
    :param no_registered_multicast : 
    :param no_unregistered_multicast :
    '''
    def __init__(self, *args, **kwargs):
        super(PortProfileFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name') or get_random_name('pp')
        self.uuid = kwargs.get('uuid')
        self.sc_profiles = kwargs.get('storm_control_profiles') or list()
        self.created = False
        self.verify_is_run = False
        self.fq_name = [self.domain, self.project_name, self.name]

    def setUp(self):
        super(PortProfileFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of port profile %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(PortProfileFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_port_profile(id=self.uuid)

    def read(self):
        obj = self.vnc_h.read_port_profile(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_port_profile(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_port_profile(
                    fq_name=self.fq_name)
                self.created = True
                self.logger.info('Created Port Profile %s(%s)'%(
                    self.name, self.uuid))
        if not self.created:
            self.read()
        self.add_storm_control_profiles(self.sc_profiles)

    def delete(self):
        self.logger.info('Deleting Port Profile %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_port_profile(id=self.uuid)
        except NoIdError:
            pass

    def add_storm_control_profiles(self, sc_profiles):
        for profile in sc_profiles:
            self.vnc_h.assoc_sc_to_port_profile(self.uuid, profile)
        self.sc_profiles = list(set(self.sc_profiles).union(set(sc_profiles)))

    def delete_storm_control_profiles(self, sc_profiles):
        for profile in sc_profiles:
            self.vnc_h.disassoc_sc_from_port_profile(self.uuid, profile)
        self.sc_profiles = list(set(self.sc_profiles) - set(sc_profiles))
