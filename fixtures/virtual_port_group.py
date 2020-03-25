import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class VPGFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle VPG object
    Optional:
    :param name : name of the vpg
    :param fabric_name : name of the fabric
    :param uuid : UUID of the fabric
    :param physical interfaces : List of Physical interface FQnames/UUIDs
    '''
    def __init__(self, fabric_name, **kwargs):
        super(VPGFixture, self).__init__(**kwargs)
        self.fabric_name = fabric_name
        self.name = kwargs.get('name') or get_random_name('vpg')
        self.uuid = kwargs.get('uuid')
        self.pifs = kwargs.get('pifs') or list()
        self.pif_uuids = list()
        self.fq_name = ['default-global-system-config',
            self.fabric_name, self.name]
        self.port_profiles = kwargs.get('port_profiles') or list()
        self.security_groups = kwargs.get('security_groups') or list()
        self.created = False

    def setUp(self):
        super(VPGFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(VPGFixture, self).cleanUp()
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of VPG %s:'
                              %(self.name))
        else:
            return self.delete()

    def get_name(self):
        return self.name

    def read(self):
        if self.uuid:
            obj = self.vnc_h.read_virtual_port_group(id=self.uuid)
        else:
            try:
                obj = self.vnc_h.read_virtual_port_group(fq_name=self.fq_name)
            except NoIdError:
                return
        self.name = obj.name
        self.uuid = obj.uuid
        self.fq_name = obj.get_fq_name()
        return obj

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_virtual_port_group(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_virtual_port_group(
                    fq_name=self.fq_name)
                self.created = True
                self.logger.info('Created VPG %s(%s)'%(self.name,
                                                       self.uuid))
        if not self.created:
            self.read()
        self.associate_physical_interfaces(self.pifs)
        self.add_port_profiles(self.port_profiles)
        self.add_security_groups(self.security_groups)

    def add_security_groups(self, security_groups):
        for sg_uuid in security_groups or []:
            self.vnc_h.assoc_security_group_to_vpg(sg_uuid, self.uuid)
        self.security_groups = list(set(self.security_groups).union(
                                  set(security_groups)))

    def delete_security_groups(self, security_groups=None):
        for sg_uuid in security_groups or self.security_groups:
            self.vnc_h.disassoc_security_group_from_vpg(sg_uuid, self.uuid)

    def add_port_profiles(self, port_profiles):
        for pp_uuid in port_profiles:
            self.vnc_h.assoc_port_profile_to_vpg(pp_uuid, self.uuid)
        self.port_profiles = list(set(self.port_profiles).union(
                                  set(port_profiles)))

    def delete_port_profiles(self, port_profiles=None):
        for pp_uuid in port_profiles or self.port_profiles:
            self.vnc_h.disassoc_port_profile_from_vpg(pp_uuid, self.uuid)

    def associate_physical_interfaces(self, pifs):
        for pif in pifs:
            kwargs = dict()
            if type(pif) is list:
                kwargs['fq_name'] = pif
            else:
                kwargs['id'] = pif
            pif_obj = self.vnc_h.read_physical_interface(**kwargs)
            self.vnc_h.associate_physical_interface(self.uuid, pif_obj)
            self.pif_uuids.append(pif_obj.uuid)

    def disassociate_physical_interfaces(self, pifs):
        for pif in pifs:
            kwargs = dict()
            if type(pif) is list:
                kwargs['fq_name'] = pif
            else:
                kwargs['id'] = pif
            pif_obj = self.vnc_h.read_physical_interface(**kwargs)
            self.vnc_h.disassociate_physical_interface(self.uuid, pif_obj)
            self.pif_uuids.remove(pif_obj.uuid)

    def delete(self):
        self.logger.info('Deleting VPG %s(%s)'%(self.name, self.uuid))
        self.disassociate_physical_interfaces(self.pif_uuids)
        self.delete_port_profiles(self.port_profiles)
        try:
            self.vnc_h.delete_virtual_port_group(id=self.uuid)
        except NoIdError:
            pass
