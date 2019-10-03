import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class TrunkFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Trunk object
    Optional:
    :param name : name of the trunk
    :param uuid : UUID of the trunk
    :param parent_port : UUID of the parent port
    :param subports : dict of subport uuid and vlan_id
    :param admin_state: True or False
    '''
    def __init__(self, **kwargs):
        super(TrunkFixture, self).__init__(**kwargs)
        self.parent_port = kwargs['parent_port']
        self.name = kwargs.get('name') or get_random_name(self.project_name)
        self.uuid = kwargs.get('uuid')
        self.subports = kwargs.get('subports') or dict()
        self.admin_state = kwargs.get('admin_state')
        self.created = False
        self.verify_is_run = False

    def setUp(self):
        super(TrunkFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Trunk %s:'
                              %(self.name))
        else:
            self.delete()
        super(TrunkFixture, self).cleanUp()

    def read(self):
        obj = self.neutron_handle.read_trunk(id=self.uuid)
        self.name = obj['name']
        self.parent_port = obj['port_id']
        self.subports = dict()
        for sport in obj.get('sub_ports') or []:
            self.subports[str(sport['port_id'])] = int(sport['segmentation_id'])
        self.admin_state = obj['admin_state_up']

    def verify_on_setup(self):
        assert self.validate_vpg_refs()
        assert self.validate_vlan_ids()
        assert self.validate_get_subports()

    def validate_vpg_refs(self):
        vpg = self.vnc_h.read_virtual_port_group(id=self.uuid)
        vmis = [vmi['uuid'] for vmi in vpg.get_virtual_machine_interface_refs()]
        expected_vmis = [self.parent_port] + self.subports.keys()
        if set(vmis).symmetric_difference(set(expected_vmis)):
            return False
        return True

    def validate_vlan_ids(self):
        for subport, vlan_id in self.subports.items():
            vmi = self.vnc_h.read_virtual_machine_interface(id=subport)
            prop = vmi.get_virtual_machine_interface_properties()
            if int(prop.get_sub_interface_vlan_tag()) != int(vlan_id):
                return False
        return True

    def validate_get_subports(self):
        subports = self.get_subports()
        subports_set = set()
        for subport in subports:
            vlan_id = int(subport['segmentation_id'])
            uuid = str(subport['port_id'])
            subports_set.add(uuid)
            if uuid not in self.subports or\
               vlan_id != int(self.subports[uuid]):
                return False
        if subports_set.symmetric_difference(set(self.subports.keys())):
            return False
        return True

    def create(self):
        if not self.uuid:
            for trunk in self.neutron_handle.list_trunks():
                if trunk['name'] == self.name and \
                   self.project_id.replace('-','') == trunk['project_id']:
                    self.uuid = trunk['id']
                    break
            else:
                self.uuid = self.neutron_handle.create_trunk(
                    name=self.name,
                    subports=[{'uuid': subport, 'vlan_id': vlan_id}
                              for subport,vlan_id in self.subports.items()],
                    admin_state=self.admin_state,
                    parent_port=self.parent_port)
                self.created = True
                self.logger.info('Created Trunk %s(%s)'%(self.name, self.uuid))
        if not self.created:
            self.read()

    def update(self, admin_state=None):
        self.logger.info('Update admin_state of %s to %s'%(
                         self.name, admin_state))
        self.neutron_handle.update_trunk(
            uuid=self.uuid,
            admin_state=admin_state)
        if admin_state:
            self.admin_state = admin_state

    def add_subports(self, subports):
        self.logger.info('Adding subports %s to trunk %s'%(subports, self.name))
        self.neutron_handle.trunk_add_subports(self.uuid,
            subports=[{'uuid': subport, 'vlan_id': vlan_id}
                      for subport,vlan_id in subports.items()])
        self.subports.update(subports)

    def delete_subports(self, subports):
        self.logger.info('Removing subports %s from trunk %s'%(
                         subports, self.name))
        self.neutron_handle.trunk_remove_subports(self.uuid,
            subports=[{'uuid': subport, 'vlan_id': vlan_id}
                      for subport,vlan_id in self.subports.items()])
        for subport in list(subports):
            self.subports.pop(subport)

    def delete(self):
        self.logger.info('Deleting Trunk %s(%s)'%(self.name, self.uuid))
        self.delete_subports(self.subports)
        self.neutron_handle.delete_trunk(self.uuid)

    def get_object(self, **kwargs):
        return self.neutron_handle.show_trunk(self.uuid, **kwargs)

    def get_subports(self):
        return self.neutron_handle.trunk_get_subports(self.uuid)
