from builtins import str
import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class FabricFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Fabric object
    Optional:
    :param name : name of the fabric
    :param uuid : UUID of the fabric
    :param namespaces : namespaces in below format
                        eg: {'management': [{'cidr': '1.1.1.0/24',
                                             'gateway': '1.1.1.254'}],
                             'loopback': ['10.1.1.0/25],
                             'peer': ['172.16.0.0/16'],
                             'asn': [{'max': 64512, 'min': 64512}],
                             'ebgp_asn': [{'max': 64512, 'min': 64512}]}
    :param creds : list of creds in the below format
                   eg: [{'username': 'root', 'password': 'c0ntrail123',
                         'vendor': 'Juniper', 'device_family': 'qfx'}]
    '''
    def __init__(self, *args, **kwargs):
        super(FabricFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name') or get_random_name('fabric')
        self.uuid = kwargs.get('uuid')
        self.namespaces = kwargs.get('namespaces') or dict()
        self.creds = kwargs.get('creds')
        self.created = False
        self.verify_is_run = False
        self._ns_id = dict()
        self.devices = list()

    def setUp(self):
        super(FabricFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(FabricFixture, self).cleanUp()
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Fabric %s:'
                              %(self.name))
        else:
            return self.delete()

    def get_name(self):
        return self.name

    def get_object(self):
        return self.vnc_h.read_fabric(id=self.uuid)

    def read(self):
        if self.uuid:
            obj = self.vnc_h.read_fabric(id=self.uuid)
        else:
            try:
                obj = self.vnc_h.read_fabric(name=self.name)
            except NoIdError:
                return
        self.name = obj.name
        self.uuid = obj.uuid
        self.fq_name = obj.get_fq_name()
        for prouter in obj.get_physical_router_back_refs() or []:
            self.devices.append(prouter['to'][-1])
        for namespace in obj.get_fabric_namespaces() or []:
            ns = self.vnc_h.get_fabric_namespace_value(id=namespace['uuid'])
            self._ns_id[ns] = namespace['uuid']
        return obj

    def create(self):
        if not self.uuid:
            self.fq_name = ['default-global-system-config', self.name]
            try:
                obj = self.vnc_h.read_fabric(name=self.name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_fabric(
                                     name=self.name,
                                     creds=self.creds)
                self.created = True
                self.logger.info('Created Fabric %s(%s)'%(self.name,
                                                          self.uuid))
        if not self.created:
            self.read()
        self.add_namespaces(self.namespaces)

    def add_creds(self, creds):
        self.vnc_h.add_creds_to_fabric(self.name, creds)

    def delete_creds(self, creds):
        self.vnc_h.delete_creds_from_fabric(self.name, creds)

    def add_namespaces(self, namespaces):
        for ns_key, ns_values in namespaces.items():
            ns_type = 'IPV4-CIDR'
            for ns in ns_values:
                if ns_key == 'management':
                    tag = 'fabric-management-ip'
                    namespace = ns['cidr']
                elif ns_key == 'loopback':
                    tag = 'fabric-loopback-ip'
                    namespace = ns
                elif ns_key == 'peer':
                    tag = 'fabric-peer-ip'
                    namespace = ns
                elif ns_key == 'asn':
                    tag = 'fabric-as-number'
                    ns_type = 'ASN'
                    namespace = ns['min']
                elif ns_key == 'ebgp_asn':
                    tag = 'fabric-ebgp-as-number'
                    ns_type = 'ASN'
                    namespace = ns['min']
                fq_name = self.fq_name + [get_random_name('ns')]
                ns_id = self.vnc_h.create_fabric_namespace(
                              fq_name, ns_type, str(namespace))
                self.vnc_h.set_tag('label', tag, True, uuid=ns_id,
                                   object_type='fabric_namespace')
                self._ns_id[namespace] = ns_id

    def delete_namespaces(self, namespaces):
        for namespace in namespaces:
            self.vnc_h.delete_fabric_namespace(id=self._ns_id[namespace])
            del self._ns_id[namespace]

    def get_namespace_id(self, namespace):
        return self._ns_id[namespace]

    def delete(self):
        self.logger.info('Deleting Fabric %s(%s)'%(self.name, self.uuid))
        self.delete_namespaces(list(self._ns_id.keys()))
        try:
            self.vnc_h.delete_fabric(id=self.uuid)
        except NoIdError:
            pass

    def fetch_associated_devices(self):
        self.devices = list()
        obj = self.vnc_h.read_fabric(id=self.uuid)
        for prouter in obj.get_physical_router_back_refs() or []:
            self.devices.append(prouter['to'][-1])
        return self.devices

    def associate_device(self, device_name):
        self.vnc_h.add_device_to_fabric(self.uuid, device_name)
        self.devices.append(device_name)

    def disassociate_device(self, device_name):
        self.vnc_h.delete_device_from_fabric(self.uuid, device_name)
        self.devices.remove(device_name)

    def disassociate_devices(self, devices=None):
        devices = devices or self.devices
        #import pdb; pdb.set_trace()
        for device in devices:
            self.disassociate_device(device)

    @retry(2, 5)
    def verify_on_cleanup(self):
        try:
            self.vnc_h.read_fabric(id=self.uuid)
            self.logger.warn('Fabric %s not yet deleted'%self.name)
            return False
        except NoIdError:
            self.logger.info('Fabric %s got deleted as expected'%self.name)
            return True
