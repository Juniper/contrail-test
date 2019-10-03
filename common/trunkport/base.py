from common.neutron.base import BaseNeutronTest
from tcutils.util import get_random_name, retry
from port_fixture import PortFixture
from vm_test import VMFixture
from trunk import TrunkFixture
import random
import copy

class BaseTrunkportTest(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(BaseTrunkportTest, cls).setUpClass()
        cls.vns = dict(); cls.vms = dict()
        cls.project_name = cls.inputs.project_name
        cls.domain_name = cls.inputs.domain_name
        cls.vnc_h = cls.connections.orch.vnc_h
        try:
            cls.create_common_objects()
        except:
            cls.tearDownClass()
            raise
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_common_objects()
        super(BaseTrunkportTest, cls).tearDownClass()
    # end tearDownClass

    @classmethod
    def create_common_objects(cls):
        ''' Create tags under both global and local scope
            Site: svl, blr
            deployment: prod, dev
            application: hr, eng
            tier: web, logic, db
        '''
        cls.vns['parent'] = cls.create_only_vn()
        for vn in ['subport1', 'subport2']:
            cls.vns[vn] = cls.create_only_vn(disable_gateway=True)

    @classmethod
    def cleanup_common_objects(cls):
        if getattr(cls, 'vns', None):
            for obj in cls.vns.itervalues():
                obj.cleanUp()

    def _get_vmi_uuid(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.get_vmi_ids().values()[0]
        elif type(fixture) == PortFixture:
            return fixture.uuid

    def create_trunk(self, vm, subports=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        parent_port = self._get_vmi_uuid(vm)
        if subports:
            subports = {self._get_vmi_uuid(subport): vlan_id
                        for subport, vlan_id in subports.items()}
        return self.useFixture(TrunkFixture(connections=connections,
               parent_port=parent_port, subports=subports, **kwargs))
